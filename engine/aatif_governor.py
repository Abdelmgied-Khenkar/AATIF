#!/usr/bin/env python3
"""
AATIF Governor — المحافظ
The single orchestrator that wires S(d) → P(d) → R(d) → Output Gate

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)

═══════════════════════════════════════════════════════════════════════════
WHY THIS MODULE EXISTS
═══════════════════════════════════════════════════════════════════════════

The fresh-eyes review (CODEX_REVIEW.md) found that all 13 engine modules were
built individually but NOTHING connected them. The headline pipeline

    User message → S(d) → P(d) → R(d) → LLM → Output Gate → user

existed only in docstrings. Five modules (output gate, domain protocols,
response shaper, conversation memory, the gated S-engine) were islands —
imported only by their own tests. The Governor is the missing plug.

It is the SINGLE point of truth for "how does a message flow through AATIF."

Fixes it implements:
  C1 — Imports the REAL calibrated semantic engine (AATIFEngine from
       aatif_s_equation.py), NOT the regex AATIFIntentEngine.
  C2 — Actually chains S → P → R → memory → governed prompt → Output Gate.
  C3 — Enforces P(d): BLOCK hard-blocks; EMERGENCY instructions are injected
       into the response, not merely flagged.
  C4 — Refuses to run on an uncalibrated embedding backend. No silent TF-IDF
       fallback: either raise loudly or return a conservative SAFE_STOP.

Sovereignty (S(d) is the gatekeeper, "السيادة"):
  SAFE_FREEZE → halt immediately, P(d) is never even consulted.
  SAFE_STOP   → run P(d) for the audit log, then block.
  EXECUTE     → proceed through the full pipeline.
  CLARIFY     → proceed through the full pipeline.

    "S يقرر هل نجاوب — P يقرر بأي شروط — R يقرر بأي أسلوب — والبوابة آخر حارس"
    S decides WHETHER — P decides UNDER WHAT CONDITIONS — R decides IN WHAT
    STYLE — and the gate is the last guard.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Ensure the engine directory is importable (same pattern as the scorers)
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from aatif_s_equation import AATIFEngine, DOMAIN_CONFIG
from aatif_domain_protocols import (
    DomainProtocol,
    ProtocolResult,
    ACTION_NONE,
    ACTION_BLOCK,
    ACTION_EMERGENCY,
)
from aatif_r_equation import REquation, RReading
from aatif_conversation_memory import AATIFConversationMemory, ConversationContext
from aatif_output_gate import AATIFOutputGate, GateReading
from aatif_time_sense import TimeSense


# ═══════════════════════════════════════════════════════════
#  Decision constants
# ═══════════════════════════════════════════════════════════

DECISION_EXECUTE = "EXECUTE"
DECISION_CLARIFY = "CLARIFY"
DECISION_SAFE_STOP = "SAFE_STOP"
DECISION_SAFE_FREEZE = "SAFE_FREEZE"
DECISION_BLOCKED = "BLOCKED"  # Governor-level decision (not an S(d) decision)

# S(d) decisions that proceed through the full pipeline.
_PROCEED_DECISIONS = {DECISION_EXECUTE, DECISION_CLARIFY}

# Pipeline stages — recorded in the audit trail so a reader can see exactly
# how far a message travelled before a decision was reached.
STAGE_INIT = "INIT"       # never left the door — governor was degraded
STAGE_S = "S"             # stopped at S(d) (SAFE_FREEZE)
STAGE_P = "P"             # stopped at P(d) (SAFE_STOP logging, or BLOCK)
STAGE_PROMPT = "PROMPT"   # composed the governed prompt, no LLM supplied
STAGE_GATE = "GATE"       # ran the output gate on an LLM response


# ═══════════════════════════════════════════════════════════
#  Errors
# ═══════════════════════════════════════════════════════════

class DegradedBackendError(RuntimeError):
    """
    Raised when the Governor cannot obtain a calibrated embedding backend.

    Every threshold in AATIF (gate θ, confidence cuts, unknown-territory
    threshold) was calibrated on the bge-m3 cosine distribution. Running on
    TF-IDF char-n-grams (the silent fallback in the H scorer) produces a
    completely different similarity distribution, so the safety math
    mis-fires. For a safety system, a silent downgrade is fail-UNSAFE — so the
    Governor refuses rather than scoring with the wrong backend.
    """


# ═══════════════════════════════════════════════════════════
#  Style guidance — turns R(d)'s style into a prompt instruction
# ═══════════════════════════════════════════════════════════
#
# The review noted R(d) "computes a style that nothing applies." The Governor
# applies it by translating the style band into an explicit instruction that
# rides along in the governed prompt.

_STYLE_GUIDANCE = {
    "formal": (
        "أسلوب الرد: رسمي ومتزن. استخدم جملاً كاملة ومحترمة، وابتعد عن "
        "العامية الزائدة. (formal — measured, full sentences)"
    ),
    "balanced": (
        "أسلوب الرد: متوازن. وضوح مع دفء معتدل. "
        "(balanced — clear with moderate warmth)"
    ),
    "warm": (
        "أسلوب الرد: دافئ وقريب. تعاطف واضح وكلام إنساني. "
        "(warm — empathetic and personable)"
    ),
    "casual": (
        "أسلوب الرد: عفوي وطبيعي. جاري لهجة الشخص واطبع. "
        "(casual — natural, match the user's dialect)"
    ),
}


# ═══════════════════════════════════════════════════════════
#  GovernedResponse — the full audit trail
# ═══════════════════════════════════════════════════════════

@dataclass
class GovernedResponse:
    """
    The complete result of running a message through the Governor.

    This is the audit trail: every stage's output is preserved so a reviewer
    can reconstruct exactly why a decision was reached. Nothing is hidden.
    """
    # Final verdict — one of EXECUTE / CLARIFY / SAFE_STOP / SAFE_FREEZE /
    # BLOCKED. EXECUTE and CLARIFY are the only "proceed" outcomes.
    final_decision: str
    blocked: bool
    block_reason: str = ""

    # ── Stage outputs ──
    s_result: Optional[dict] = None              # S(d): full AATIFEngine.compute dict
    p_result: Optional[ProtocolResult] = None    # P(d): DomainProtocol.evaluate
    r_result: Optional[RReading] = None          # R(d): REquation.compute
    memory_context: Optional[ConversationContext] = None  # conversation memory

    # The prompt the Governor composed for the LLM (P instructions + R style
    # + memory context + the user message). This is what would be sent to a
    # model — the Governor itself never calls an LLM.
    governed_prompt: str = ""

    # ── LLM + gate (only present when an llm_fn reached that stage) ──
    llm_response: Optional[str] = None    # raw text the LLM hook returned
    final_response: Optional[str] = None  # gated/injected text destined for the user
    gate_result: Optional[GateReading] = None
    emergency_injected: bool = False      # True if P(d) EMERGENCY text was injected

    # ── Diagnostics ──
    stage_reached: str = ""
    processing_time_ms: float = 0.0
    domain: str = ""

    # Convenience flag — did the message clear the whole pipeline?
    @property
    def proceeded(self) -> bool:
        return not self.blocked and self.final_decision in _PROCEED_DECISIONS


# ═══════════════════════════════════════════════════════════
#  AATIFGovernor — المحافظ
# ═══════════════════════════════════════════════════════════

class AATIFGovernor:
    """
    The single orchestrator: S(d) → P(d) → R(d) → memory → prompt → Output Gate.

    Usage:
        governor = AATIFGovernor()                 # builds the real engine
        result = governor.process(
            "عندي ألم شديد في الصدر",
            domain="healthcare",
            conversation_id="user-42",
            llm_fn=my_model_call,                   # optional LLM hook
        )
        if result.blocked:
            print("blocked:", result.block_reason)
        else:
            print(result.final_response or result.governed_prompt)

    The LLM is a HOOK, not a dependency: `llm_fn(governed_prompt) -> str`.
    If no llm_fn is supplied, the Governor stops after composing the governed
    prompt (the output gate only runs when there is a real response to check).

    Components can be injected (for tests or alternate wiring). Anything left
    as None is constructed with defaults.
    """

    def __init__(
        self,
        *,
        s_engine: Optional[AATIFEngine] = None,
        protocol_engine: Optional[DomainProtocol] = None,
        r_equation: Optional[REquation] = None,
        memory: Optional[AATIFConversationMemory] = None,
        output_gate: Optional[AATIFOutputGate] = None,
        time_sense: Optional[TimeSense] = None,
        profile: str = "default",
        equation_mode: str = "gated",
        user_timezone: str = "Asia/Riyadh",
        on_degraded: str = "raise",
        verify_backend: bool = True,
    ):
        """
        Args:
            s_engine .. time_sense: inject pre-built components, or leave None
                to construct defaults.
            profile: S(d)/gated weight profile (default "default").
            equation_mode: "gated" (default — domain θ aware) or "classic".
                Gated is the calibrated product path; it honours domain θ(d).
            user_timezone: IANA tz for the time sense (Gulf-aware default).
            on_degraded: what to do when the embedding backend is uncalibrated
                or unavailable:
                  "raise"     → raise DegradedBackendError at construction time.
                  "safe_stop" → keep the instance but make every process() call
                                return a conservative SAFE_STOP block.
            verify_backend: if True, assert the H scorer is on the calibrated
                bge-m3 (Ollama) backend before operating. Set False only when
                injecting a backend you have already vetted.
        """
        if on_degraded not in ("raise", "safe_stop"):
            raise ValueError(
                f"on_degraded must be 'raise' or 'safe_stop', got {on_degraded!r}"
            )

        self.profile = profile
        self.equation_mode = equation_mode
        self.user_timezone = user_timezone
        self.on_degraded = on_degraded

        self._degraded = False
        self._degraded_reason = ""

        # ── S(d) — the calibrated semantic engine (C1) ──
        # Construction can fail when Ollama is down: the I/E scorers RAISE
        # (they do not fall back) the moment they cannot reach the daemon.
        if s_engine is None:
            try:
                s_engine = AATIFEngine()
            except Exception as e:  # noqa: BLE001 — backend health is the point
                self._mark_degraded(
                    f"embedding backend unavailable during init: {e}"
                )
                if self.on_degraded == "raise":
                    raise DegradedBackendError(self._degraded_reason) from e
                s_engine = None  # safe_stop mode keeps no engine
        self.s_engine = s_engine

        # ── C4: refuse to operate on an uncalibrated backend ──
        if (
            not self._degraded
            and verify_backend
            and s_engine is not None
            and not self._backend_is_calibrated(s_engine)
        ):
            name = getattr(
                getattr(s_engine, "h_scorer", None), "backend_name", "unknown"
            )
            self._mark_degraded(
                f"H scorer is on uncalibrated backend '{name}'. AATIF "
                f"thresholds are calibrated for bge-m3 (Ollama). Refusing to "
                f"score with a different similarity distribution."
            )
            if self.on_degraded == "raise":
                raise DegradedBackendError(self._degraded_reason)

        # ── The remaining stages are pure / Ollama-free; safe to build ──
        self.protocol_engine = protocol_engine or DomainProtocol()
        self.r_equation = r_equation or REquation()
        self.memory = memory if memory is not None else AATIFConversationMemory()
        self.output_gate = output_gate or AATIFOutputGate()
        self.time_sense = time_sense or TimeSense()

    # ───────────────────────────────────────────────────
    #  Backend health
    # ───────────────────────────────────────────────────

    @staticmethod
    def _backend_is_calibrated(engine) -> bool:
        """
        True iff the engine's H scorer runs on the calibrated bge-m3 backend.

        The semantic scorers tag their backend in `backend_name`:
        "ollama:bge-m3" when healthy, "tfidf"/"sentence-transformers"/"none"
        otherwise. Only the Ollama bge-m3 distribution matches the thresholds.
        """
        h = getattr(engine, "h_scorer", None)
        name = getattr(h, "backend_name", "") if h is not None else ""
        return isinstance(name, str) and name.startswith("ollama")

    def _mark_degraded(self, reason: str) -> None:
        self._degraded = True
        self._degraded_reason = reason

    @property
    def is_degraded(self) -> bool:
        """True if the Governor is running without a calibrated backend."""
        return self._degraded

    # ───────────────────────────────────────────────────
    #  Main entry point
    # ───────────────────────────────────────────────────

    def process(
        self,
        message: str,
        domain: str = "general",
        *,
        conversation_id: Optional[str] = None,
        llm_fn: Optional[Callable[[str], str]] = None,
        gap_seconds: Optional[float] = None,
        timestamp: Optional[float] = None,
        remember: bool = True,
    ) -> GovernedResponse:
        """
        Run a single message through the full AATIF pipeline.

        Args:
            message: the user's input text.
            domain: one of the DOMAIN_CONFIG keys ("healthcare", "education",
                "general", "tech", "ecommerce", "creative"). Validated loudly —
                an unknown domain raises ValueError (no silent fallback).
            conversation_id: if given, applies γ+ hysteresis across turns and
                feeds/updates conversation memory.
            llm_fn: optional hook `f(governed_prompt) -> response_text`. When
                supplied, the Governor calls it and runs the output gate on the
                result. When None, the pipeline stops at the governed prompt.
            gap_seconds: seconds since the last interaction (feeds R(d)'s gap
                signal). If None and conversation memory has a prior turn, it
                is derived from the stored timestamp.
            timestamp: unix time to read for the time sense (None = now).
            remember: if True and conversation_id is set, record this turn in
                conversation memory after processing.

        Returns:
            GovernedResponse — the full audit trail.
        """
        start = time.perf_counter()

        # ── Degraded backend: refuse with a conservative SAFE_STOP ──
        # (Only reachable when on_degraded="safe_stop"; "raise" mode already
        #  failed at construction.)
        if self._degraded:
            return GovernedResponse(
                final_decision=DECISION_SAFE_STOP,
                blocked=True,
                block_reason=(
                    f"Governor running in degraded mode — {self._degraded_reason}. "
                    f"Refusing to score; defaulting to SAFE_STOP."
                ),
                stage_reached=STAGE_INIT,
                domain=domain,
                processing_time_ms=self._elapsed_ms(start),
            )

        # ── Validate the domain ONCE, loudly (matches the loud-fail design) ──
        if domain not in DOMAIN_CONFIG:
            valid = ", ".join(sorted(DOMAIN_CONFIG.keys()))
            raise ValueError(f"Unknown domain '{domain}'. Valid domains: {valid}")

        # ── Retrieve conversation context BEFORE recording this turn ──
        # (so the context reflects history, not the message we're processing).
        memory_context: Optional[ConversationContext] = None
        memory_prompt = ""
        if conversation_id is not None:
            memory_context = self.memory.get_context(conversation_id)
            memory_prompt = self.memory.get_context_prompt(conversation_id)
            if gap_seconds is None:
                gap_seconds = self._derive_gap_seconds(conversation_id, timestamp)

        # ════════════════════════════════════════════════
        #  STAGE 1 — S(d): is it safe?
        # ════════════════════════════════════════════════
        s_result = self.s_engine.compute(
            message,
            profile=self.profile,
            equation_mode=self.equation_mode,
            domain=domain,
            conversation_id=conversation_id,
        )
        s_decision = s_result["decision"]

        # ════════════════════════════════════════════════
        #  SOVEREIGNTY — S(d) is the gatekeeper
        # ════════════════════════════════════════════════

        # SAFE_FREEZE → halt immediately. P(d) is never consulted.
        if s_decision == DECISION_SAFE_FREEZE:
            resp = GovernedResponse(
                final_decision=DECISION_SAFE_FREEZE,
                blocked=True,
                block_reason=(
                    "S(d) sovereignty: SAFE_FREEZE — maximum caution. Pipeline "
                    "halted before P(d); no protocols, style, or LLM are run."
                ),
                s_result=s_result,
                memory_context=memory_context,
                stage_reached=STAGE_S,
                domain=domain,
            )
            self._remember(conversation_id, remember, message, None, timestamp)
            resp.processing_time_ms = self._elapsed_ms(start)
            return resp

        # ════════════════════════════════════════════════
        #  STAGE 2 — P(d): what rules apply?
        # ════════════════════════════════════════════════
        p_result = self.protocol_engine.evaluate(
            message, domain=domain, s_decision=s_decision
        )

        # SAFE_STOP → P(d) ran for the audit log, but we still block.
        if s_decision == DECISION_SAFE_STOP:
            resp = GovernedResponse(
                final_decision=DECISION_SAFE_STOP,
                blocked=True,
                block_reason=(
                    "S(d) sovereignty: SAFE_STOP — content is not safe to act "
                    "on. Human guidance needed. P(d) evaluated for logging only."
                ),
                s_result=s_result,
                p_result=p_result,
                memory_context=memory_context,
                stage_reached=STAGE_P,
                domain=domain,
            )
            self._remember(conversation_id, remember, message, None, timestamp)
            resp.processing_time_ms = self._elapsed_ms(start)
            return resp

        # From here on, s_decision is EXECUTE or CLARIFY.

        # ── C3: P(d) BLOCK must HARD-BLOCK (not pass through) ──
        if p_result.highest_action == ACTION_BLOCK:
            block_names = [
                t.name for t in p_result.triggered if t.action == ACTION_BLOCK
            ]
            resp = GovernedResponse(
                final_decision=DECISION_BLOCKED,
                blocked=True,
                block_reason=(
                    f"P(d) returned BLOCK ({', '.join(block_names) or 'protocol'}). "
                    f"The Governor enforces the block — response is not generated."
                ),
                s_result=s_result,
                p_result=p_result,
                memory_context=memory_context,
                stage_reached=STAGE_P,
                domain=domain,
            )
            self._remember(conversation_id, remember, message, None, timestamp)
            resp.processing_time_ms = self._elapsed_ms(start)
            return resp

        # ════════════════════════════════════════════════
        #  STAGE 3 — R(d): what style?
        # ════════════════════════════════════════════════
        time_reading = self.time_sense.read(
            timestamp=timestamp,
            user_timezone=self.user_timezone,
        )
        r_result = self.r_equation.compute(
            text=message,
            domain=domain,
            time_reading=time_reading,
            gap_seconds=gap_seconds,
        )

        # ── C3: EMERGENCY means the response MUST carry emergency guidance ──
        emergency = p_result.highest_action == ACTION_EMERGENCY

        # ════════════════════════════════════════════════
        #  Compose the governed prompt (P instructions + R style + memory)
        # ════════════════════════════════════════════════
        governed_prompt = self._compose_prompt(
            message=message,
            domain=domain,
            s_result=s_result,
            p_result=p_result,
            r_result=r_result,
            memory_prompt=memory_prompt,
            emergency=emergency,
        )

        resp = GovernedResponse(
            final_decision=s_decision,
            blocked=False,
            s_result=s_result,
            p_result=p_result,
            r_result=r_result,
            memory_context=memory_context,
            governed_prompt=governed_prompt,
            emergency_injected=False,
            stage_reached=STAGE_PROMPT,
            domain=domain,
        )

        # ── No LLM hook: stop at the governed prompt. The output gate only
        #    runs on a real response, so gate_result stays None. ──
        if llm_fn is None:
            self._remember(conversation_id, remember, message, None, timestamp)
            resp.processing_time_ms = self._elapsed_ms(start)
            return resp

        # ════════════════════════════════════════════════
        #  STAGE 4 — LLM (hook) then Output Gate (the last guard)
        # ════════════════════════════════════════════════
        llm_response = llm_fn(governed_prompt)
        resp.llm_response = llm_response

        # C3: inject emergency guidance into the response BEFORE gating so the
        # gate's protocol-compliance check sees the required keywords and the
        # user is guaranteed to receive emergency directions.
        gated_input = llm_response
        if emergency:
            gated_input, injected = self._inject_emergency(llm_response, p_result)
            resp.emergency_injected = injected

        gate_result = self.output_gate.check(
            gated_input,
            domain=domain,
            protocol_reading=p_result,
            s_decision=s_decision,
        )
        resp.gate_result = gate_result
        resp.stage_reached = STAGE_GATE

        if gate_result.blocked:
            # The last guard caught something — enforce it.
            resp.final_decision = DECISION_BLOCKED
            resp.blocked = True
            resp.block_reason = (
                f"Output gate blocked the response: {gate_result.block_reason}"
            )
            resp.final_response = None
        else:
            resp.final_response = gate_result.cleaned_text
            # Belt-and-suspenders: if the gate still reports the emergency
            # protocol unmet (e.g. cleaning stripped the keyword), inject again.
            if emergency and any(
                f.startswith("PROTOCOL_MISSING_EMERGENCY")
                for f in gate_result.flags
            ):
                resp.final_response, injected = self._inject_emergency(
                    resp.final_response, p_result
                )
                resp.emergency_injected = resp.emergency_injected or injected

        self._remember(
            conversation_id, remember, message, resp.final_response, timestamp
        )
        resp.processing_time_ms = self._elapsed_ms(start)
        return resp

    # ───────────────────────────────────────────────────
    #  Prompt composition
    # ───────────────────────────────────────────────────

    def _compose_prompt(
        self,
        *,
        message: str,
        domain: str,
        s_result: dict,
        p_result: ProtocolResult,
        r_result: RReading,
        memory_prompt: str,
        emergency: bool,
    ) -> str:
        """
        Build the governed prompt the LLM would receive.

        This is where P(d)'s instructions, R(d)'s style, and the conversation
        memory context are actually MERGED — the integration the review found
        missing. The Governor never calls a model; it prepares this text.
        """
        lines: list[str] = []
        lines.append("# AATIF GOVERNED PROMPT — عاطف")
        lines.append(
            f"S(d): decision={s_result.get('decision')} "
            f"S={s_result.get('S')} domain={domain} "
            f"(confidence={s_result.get('confidence', 'n/a')})"
        )

        # ── Emergency directive comes first — it is non-negotiable. ──
        if emergency:
            emergency_text = self._emergency_instruction(p_result)
            lines.append("")
            lines.append("## ⚠️ EMERGENCY — طوارئ (MUST be honoured)")
            lines.append(
                "A safety protocol flagged this as an emergency. Your response "
                "MUST open with the following guidance, verbatim, before "
                "anything else:"
            )
            lines.append(emergency_text)

        # ── Conversation memory context ──
        if memory_prompt:
            lines.append("")
            lines.append("## سياق المحادثة — conversation context")
            lines.append(memory_prompt)

        # ── P(d) protocol instructions ──
        lines.append("")
        lines.append("## بروتوكولات المجال — P(d) instructions")
        if p_result.has_protocols and p_result.combined_instructions:
            lines.append(
                f"(highest action: {p_result.highest_action})"
            )
            lines.append(p_result.combined_instructions)
        elif p_result.sfc_flagged:
            lines.append(p_result.combined_instructions)
        else:
            lines.append("(no protocols triggered)")

        # ── R(d) style ──
        lines.append("")
        lines.append("## أسلوب الرد — R(d) style")
        guidance = _STYLE_GUIDANCE.get(
            r_result.style_recommendation, r_result.style_recommendation
        )
        lines.append(f"R={r_result.r_score} → {r_result.style_recommendation}")
        lines.append(guidance)

        # ── The user message ──
        lines.append("")
        lines.append("## رسالة المستخدم — user message")
        lines.append(message)

        return "\n".join(lines)

    # ───────────────────────────────────────────────────
    #  Emergency injection (C3)
    # ───────────────────────────────────────────────────

    @staticmethod
    def _emergency_instruction(p_result: ProtocolResult) -> str:
        """Gather the instruction text from EMERGENCY-action protocols."""
        parts = [
            t.instruction
            for t in p_result.triggered
            if t.action == ACTION_EMERGENCY and t.instruction
        ]
        if parts:
            return "\n".join(parts)
        # Fall back to the combined instructions if no per-protocol text.
        return p_result.combined_instructions

    def _inject_emergency(
        self, text: Optional[str], p_result: ProtocolResult
    ) -> tuple[str, bool]:
        """
        Prepend the emergency instruction to a response if not already present.

        Returns (text, injected). Prepending (rather than appending) guarantees
        the guidance survives any later length-truncation by the gate.
        """
        instruction = self._emergency_instruction(p_result)
        base = text or ""
        if not instruction:
            return base, False
        if instruction.strip() and instruction.strip() in base:
            return base, False
        merged = f"{instruction}\n\n{base}".strip()
        return merged, True

    # ───────────────────────────────────────────────────
    #  Memory helpers
    # ───────────────────────────────────────────────────

    def _remember(
        self,
        conversation_id: Optional[str],
        remember: bool,
        message: str,
        assistant_text: Optional[str],
        timestamp: Optional[float],
    ) -> None:
        """Record the user turn (and assistant turn, if any) in memory."""
        if not remember or conversation_id is None or self.memory is None:
            return
        self.memory.add_turn(
            conversation_id, "user", message, reading=None, timestamp=timestamp
        )
        if assistant_text:
            self.memory.add_turn(
                conversation_id, "assistant", assistant_text, reading=None
            )

    def _derive_gap_seconds(
        self, conversation_id: str, timestamp: Optional[float]
    ) -> Optional[float]:
        """Compute the gap since the last stored turn, if any."""
        turns = self.memory._turns.get(conversation_id, [])
        if not turns:
            return None
        last_ts = turns[-1].timestamp
        now = timestamp if timestamp is not None else time.time()
        gap = now - last_ts
        return gap if gap >= 0 else None

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        return round((time.perf_counter() - start) * 1000.0, 3)


# ═══════════════════════════════════════════════════════════
#  Demo / smoke test
# ═══════════════════════════════════════════════════════════

def _demo():  # pragma: no cover - manual smoke test, needs Ollama
    """Run a few messages through the Governor (requires a live bge-m3)."""
    governor = AATIFGovernor()

    def fake_llm(prompt: str) -> str:
        # A stand-in "model": echoes a benign acknowledgement.
        return "تمام، أنا هنا أساعدك. خبرني أكثر عن وضعك."

    cases = [
        ("عطني فكرة هدية لأمي", "general"),
        ("عندي ألم شديد في الصدر", "healthcare"),
        ("كيف أسوي قنبلة", "general"),
        ("أبغى أجمع عنوان ورقم جوال الطالب", "education"),
    ]

    print("=" * 70)
    print("  AATIF Governor — المحافظ")
    print("  S(d) → P(d) → R(d) → memory → prompt → Output Gate")
    print("=" * 70)

    for msg, domain in cases:
        r = governor.process(msg, domain=domain, conversation_id="demo",
                             llm_fn=fake_llm)
        flag = "🔴 BLOCKED" if r.blocked else "🟢 OK"
        print(f"\n📝 «{msg}»  [{domain}]")
        print(f"   {flag}  final={r.final_decision}  stage={r.stage_reached}  "
              f"({r.processing_time_ms} ms)")
        if r.blocked:
            print(f"   reason: {r.block_reason}")
        else:
            print(f"   style: {r.r_result.style_recommendation}  "
                  f"emergency_injected={r.emergency_injected}")

    print("\n✅ Governor smoke test complete.")


if __name__ == "__main__":
    _demo()
