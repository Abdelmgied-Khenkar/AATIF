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

import math
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

from aatif_s_equation import (
    AATIFEngine, DOMAIN_CONFIG, GATED_PROFILES,
    DYNAMIC_THETA_ENABLED, compute_dynamic_theta, get_domain_theta,
)
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

# ---------------------------------------------------------------------------
# Triad modules — optional.  When present the Governor enriches style and
# prompt composition with fingerprint + temporal-memory context.  When absent
# (ImportError, or simply not injected) the Governor works exactly as before.
# ---------------------------------------------------------------------------
try:
    from aatif_fingerprint import UserFingerprint, FingerprintReading, RepetitionContext
    from aatif_temporal_memory import TemporalMemory, MemoryEntry, TemporalContext
    HAS_TRIAD = True
except ImportError:
    HAS_TRIAD = False

try:
    from aatif_contextual_intent import ContextualIntentScorer, IntentContext
    HAS_CONTEXTUAL_INTENT = True
except ImportError:
    try:
        from engine.aatif_contextual_intent import ContextualIntentScorer, IntentContext
        HAS_CONTEXTUAL_INTENT = True
    except ImportError:
        HAS_CONTEXTUAL_INTENT = False

# ---------------------------------------------------------------------------
# Judgment memory — optional.  When present the Governor records every S(d)
# outcome to a forensic ledger, enabling judgment-context-aware θ adjustment
# in future interactions.  When absent the Governor works exactly as before.
# ---------------------------------------------------------------------------
try:
    from aatif_judgment_memory import JudgmentMemory, _hash_message as _jm_hash
    from aatif_judgment_integration import (
        JudgmentAwareGovernor,
        JudgmentAwareResult,
        create_judgment_governor,
    )
    HAS_JUDGMENT = True
except ImportError:
    HAS_JUDGMENT = False

# ---------------------------------------------------------------------------
# Response shaper — optional.  Converts engine decisions into rich
# meaning_instructions for the LLM (dialect, tone, firmness, forbidden
# phrases).  When absent the Governor uses its built-in style guidance.
# ---------------------------------------------------------------------------
try:
    from aatif_response_shaper import AATIFResponseShaper, ResponseShape
    HAS_RESPONSE_SHAPER = True
except ImportError:
    HAS_RESPONSE_SHAPER = False


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
#  _ShaperReading — lightweight adapter for the response shaper
# ═══════════════════════════════════════════════════════════
#
# The response shaper expects an IntentReading-like object, but the Governor
# works with raw s_result dicts. This adapter bridges the gap by mapping
# available pipeline data into the attributes the shaper accesses. Fields
# not available from the S engine (emotional_state, load_bearing, etc.)
# get sensible defaults.

@dataclass
class _ShaperReading:
    """Minimal reading adapter built from Governor pipeline data."""
    decision: str = "EXECUTE"
    decision_reason: str = ""
    mode: str = "NORMAL"
    emotional_state: str = "clear"
    emotional_confidence: float = 0.8
    load_bearing: bool = False
    dialect_detected: str = "unknown"
    ambiguity_score: float = 0.0
    harm_score: float = 0.0
    softening_factor: float = 0.5
    skills_to_activate: list = field(default_factory=list)
    deep_intent: str = ""
    directness: Optional[float] = None


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

    # ── Triad context (fingerprint + temporal memory) ──
    # Present only when triad modules are injected into the Governor.
    # Contains: fingerprint reading, repetition context, suggested approach,
    # temporal context, merged insights.  NEVER influences S(d).
    triad_context: Optional[dict] = None

    # ── Judgment memory (when wired) ──
    judgment_recorded: bool = False  # True if this decision was recorded to the ledger

    # ── Response shaper (when wired) ──
    response_shape: Optional[object] = None  # ResponseShape from aatif_response_shaper

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
        fingerprint: Optional[object] = None,
        temporal_memory: Optional[object] = None,
        contextual_intent: Optional[object] = None,
        judgment_memory: Optional[object] = None,
        response_shaper: Optional[object] = None,
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

        # ── Law Γ: governance integrity ──
        # Verify that GATED_PROFILES and DOMAIN_CONFIG are structurally
        # sound. If not, mark degraded — the Governor should not score
        # with corrupted governance parameters.
        if not self._degraded:
            gamma_ok, gamma_reason = self._check_governance_integrity()
            if not gamma_ok:
                self._mark_degraded(
                    f"Law Γ: governance integrity failed — {gamma_reason}"
                )
                if self.on_degraded == "raise":
                    raise DegradedBackendError(self._degraded_reason)

        # ── The remaining stages are pure / Ollama-free; safe to build ──
        self.protocol_engine = protocol_engine or DomainProtocol()
        self.r_equation = r_equation or REquation()
        self.memory = memory if memory is not None else AATIFConversationMemory()
        self.output_gate = output_gate or AATIFOutputGate()
        self.time_sense = time_sense or TimeSense()

        # ── Triad modules — optional enrichment layers ──
        # These NEVER influence S(d). They enrich R(d) style, prompt
        # composition, and the result's triad_context for callers.
        self.fingerprint = fingerprint      # Optional[UserFingerprint]
        self.temporal_memory = temporal_memory  # Optional[TemporalMemory]

        # ── Contextual Intent Scorer — integrates the full triad ──
        # Wraps the base I scorer with fingerprint + memory context.
        # Wired in here so it's no longer dead code (consensus fix #1).
        self.contextual_intent = contextual_intent  # Optional[ContextualIntentScorer]

        # ── Judgment memory — optional forensic ledger ──
        # When present, the Governor records every S(d) outcome so the
        # JudgmentMemory accumulates context for future θ adjustments.
        # NEVER influences S(d) directly — it only observes and records.
        self.judgment_memory = judgment_memory  # Optional[JudgmentMemory]

        # ── Response shaper — optional meaning_instruction builder ──
        # Converts decisions into rich LLM instructions with dialect,
        # tone, firmness, and forbidden phrases.
        self.response_shaper = response_shaper  # Optional[AATIFResponseShaper]

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
    #  Law Γ — governance integrity
    # ───────────────────────────────────────────────────

    @staticmethod
    def _check_governance_integrity() -> tuple:
        """Law Γ — verify that governance configuration is structurally intact.

        Validates:
          1. GATED_PROFILES entries have required keys (w1, w2, alpha, theta)
             with finite positive numeric values.
          2. Profile theta ordering: high_sensitivity ≤ default ≤ relaxed.
          3. DOMAIN_CONFIG entries have valid theta in (0, 1).

        Returns:
            (True, "")          if governance is valid.
            (False, reason_str) if corrupted / missing.

        This check is cheap (dict lookups, no I/O) and can be called at
        init and at the start of each process() call to guard against
        runtime tampering.
        """
        try:
            # ── 1. Gated profiles ──
            if not GATED_PROFILES:
                return (False, "GATED_PROFILES is empty")

            required_keys = ("w1", "w2", "alpha", "theta")
            for name, profile in GATED_PROFILES.items():
                for key in required_keys:
                    if key not in profile:
                        return (False,
                                f"GATED_PROFILES['{name}'] missing '{key}'")
                    val = profile[key]
                    if not isinstance(val, (int, float)):
                        return (False,
                                f"GATED_PROFILES['{name}']['{key}'] not numeric")
                    if not math.isfinite(val):
                        return (False,
                                f"GATED_PROFILES['{name}']['{key}'] not finite")
                # alpha must be positive (gate steepness)
                if profile["alpha"] <= 0:
                    return (False,
                            f"GATED_PROFILES['{name}']['alpha'] must be > 0")
                # theta must be in (0, 1) (harm threshold)
                if not (0 < profile["theta"] < 1):
                    return (False,
                            f"GATED_PROFILES['{name}']['theta'] must be in (0,1)")
                # quality weights must be positive
                for w in ("w1", "w2"):
                    if profile[w] <= 0:
                        return (False,
                                f"GATED_PROFILES['{name}']['{w}'] must be > 0")

            # ── 2. Profile theta ordering ──
            # high_sensitivity ≤ default ≤ relaxed  (more sensitive = lower θ)
            ordering_profiles = ("high_sensitivity", "default", "relaxed")
            if all(p in GATED_PROFILES for p in ordering_profiles):
                hs = GATED_PROFILES["high_sensitivity"]["theta"]
                df = GATED_PROFILES["default"]["theta"]
                rx = GATED_PROFILES["relaxed"]["theta"]
                if not (hs <= df <= rx):
                    return (False,
                            f"Profile theta ordering violated: "
                            f"high_sensitivity({hs}) ≤ default({df}) "
                            f"≤ relaxed({rx})")

            # ── 3. Domain configs ──
            if not DOMAIN_CONFIG:
                return (False, "DOMAIN_CONFIG is empty")
            for name, cfg in DOMAIN_CONFIG.items():
                if "theta" not in cfg:
                    return (False,
                            f"DOMAIN_CONFIG['{name}'] missing 'theta'")
                if not (0 < cfg["theta"] < 1):
                    return (False,
                            f"DOMAIN_CONFIG['{name}']['theta'] must be in (0,1)")

            return (True, "")
        except Exception as exc:
            return (False, f"Governance integrity error: {exc}")

    # ───────────────────────────────────────────────────
    #  Judgment memory — forensic recording
    # ───────────────────────────────────────────────────

    def _record_judgment(
        self,
        message: str,
        s_result: dict,
        conversation_id: Optional[str],
        domain: str,
    ) -> bool:
        """Record the S(d) outcome to the judgment memory ledger.

        Returns True if recording succeeded, False otherwise.
        This is a forensic record — it observes and records but NEVER
        influences S(d). The judgment memory accumulates data that can
        inform future θ adjustments via JudgmentAwareGovernor.
        """
        if self.judgment_memory is None or not HAS_JUDGMENT:
            return False
        try:
            msg_hash = _jm_hash(message) if message else "empty"
            scores = {
                "H": s_result.get("H", 0.0),
                "I": s_result.get("I", 0.0),
                "E": s_result.get("E", 0.0),
                "S": s_result.get("S", 0.0),
            }
            self.judgment_memory.record_judgment(
                session_id=conversation_id or "anonymous",
                msg_hash=msg_hash,
                msg_embedding=None,
                scores=scores,
                decision=s_result.get("decision", "SAFE_FREEZE"),
                theta=s_result.get("theta_effective", 0.40),
            )
            return True
        except Exception:
            return False  # graceful degradation — never break the pipeline

    # ───────────────────────────────────────────────────
    #  Response shaper — optional meaning_instruction layer
    # ───────────────────────────────────────────────────

    def _shape_response(
        self,
        s_result: dict,
        memory_context: Optional[dict],
    ) -> Optional[object]:
        """Build a ResponseShape from pipeline data if a shaper is configured.

        Returns None if no response shaper is available. Uses _ShaperReading
        as an adapter to map s_result fields into the attributes the shaper
        expects.
        """
        if self.response_shaper is None or not HAS_RESPONSE_SHAPER:
            return None
        try:
            reading = _ShaperReading(
                decision=s_result.get("decision", "EXECUTE"),
                decision_reason=s_result.get("decision_reason", ""),
                harm_score=s_result.get("H", 0.0),
                ambiguity_score=(
                    0.8 if s_result.get("ambiguity_override") else 0.0
                ),
                softening_factor=s_result.get("F_prime", 0.5),
                directness=1.0 - s_result.get("F_prime", 0.5),
            )
            return self.response_shaper.shape(
                reading, memory_context or {},
            )
        except Exception:
            return None  # graceful degradation — never break the pipeline

    # ───────────────────────────────────────────────────
    #  Triad context (fingerprint + temporal memory)
    # ───────────────────────────────────────────────────

    def _get_triad_context(
        self, message: str, user_id: str, timestamp: Optional[float] = None,
    ) -> Optional[dict]:
        """Get combined fingerprint + temporal memory context for this user.

        Returns None if no triad module is available. The result
        enriches prompt composition and the GovernedResponse audit trail
        but NEVER feeds into S(d).

        When ContextualIntentScorer is wired in (consensus fix #1),
        it produces an IntentContext that the Governor includes in the
        triad_context dict under the key "intent_context".
        """
        if (
            not self.fingerprint
            and not self.temporal_memory
            and not self.contextual_intent
        ):
            return None

        context: dict = {}

        if self.fingerprint:
            fp = self.fingerprint.read(user_id)
            rep = self.fingerprint.detect_repetition(user_id, message)
            approach = self.fingerprint.suggest_approach(fp, rep)
            context["fingerprint"] = fp
            context["repetition"] = rep
            context["suggested_approach"] = approach

        if self.temporal_memory:
            tc = self.temporal_memory.get_context(user_id)
            context["temporal"] = tc

        # Merge when both layers are present — the full picture.
        if self.fingerprint and self.temporal_memory:
            context["merged"] = self.temporal_memory.merge_with_fingerprint(
                user_id, context["fingerprint"]
            )

        # ContextualIntentScorer integration (consensus fix #1).
        # This was dead code — now it's wired in. The scorer wraps the
        # base I score with fingerprint + memory context to produce
        # response-strategy metadata. The raw I score stays untouched
        # for S(d) — this only adds strategy hints.
        if self.contextual_intent and HAS_CONTEXTUAL_INTENT:
            try:
                intent_ctx = self.contextual_intent.score(
                    message, user_id=user_id
                )
                context["intent_context"] = intent_ctx
                # If contextual intent provides a more specific approach
                # than the fingerprint alone, prefer it.
                if (
                    intent_ctx.suggested_approach != "standard"
                    and "suggested_approach" in context
                ):
                    context["suggested_approach"] = intent_ctx.suggested_approach
            except Exception:
                pass  # graceful degradation

        return context

    def _update_triad(
        self,
        user_id: str,
        message: str,
        timestamp: Optional[float],
        s_result: Optional[dict],
        triad_context: Optional[dict],
    ) -> None:
        """Update triad modules after processing a message.

        Called regardless of whether the message was blocked — the
        fingerprint and memory need to know about every interaction.
        """
        ts = timestamp if timestamp is not None else time.time()

        if self.fingerprint:
            self.fingerprint.update(user_id, message, timestamp=ts)

        if self.temporal_memory and HAS_TRIAD:
            # Build a MemoryEntry from whatever we know.
            is_repeat = False
            confusion = False
            if triad_context and "repetition" in triad_context:
                is_repeat = triad_context["repetition"].is_repeat
            # Confusion detection via fingerprint signals
            if triad_context and "fingerprint" in triad_context:
                fp = triad_context["fingerprint"]
                confusion = getattr(fp, "confusion_signals", 0) > 0

            from datetime import datetime as _dt, timezone as _tz
            entry = MemoryEntry(
                entry_id="",
                user_id=user_id,
                timestamp=_dt.fromtimestamp(ts, tz=_tz.utc),
                time_period="",
                message_role="user",
                message_summary=message[:200],  # truncate for privacy
                topic="",
                intent_score=s_result.get("I") if s_result else None,
                harm_score=s_result.get("H") if s_result else None,
                emotion_score=s_result.get("E") if s_result else None,
                s_decision=s_result.get("decision") if s_result else None,
                was_repeat_question=is_repeat,
                confusion_detected=confusion,
            )
            self.temporal_memory.store(entry)

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

        # ── Dynamic θ — حساسية الأمان المتكيّفة ──
        # If enabled, compute θ_eff from user's blocked-decision history.
        # θ_eff replaces the domain θ — stricter for repeat offenders.
        theta_override = None
        if (
            DYNAMIC_THETA_ENABLED
            and self.equation_mode == "gated"
            and self.temporal_memory is not None
            and HAS_TRIAD
            and conversation_id is not None
        ):
            domain_theta = get_domain_theta(domain)
            if domain_theta is not None:
                blocked = self.temporal_memory.get_recent_blocks(
                    conversation_id, n=20
                )
                if blocked:
                    theta_override = compute_dynamic_theta(
                        domain_theta, blocked
                    )

        # ════════════════════════════════════════════════
        #  STAGE 1 — S(d): is it safe?
        # ════════════════════════════════════════════════
        s_result = self.s_engine.compute(
            message,
            profile=self.profile,
            equation_mode=self.equation_mode,
            domain=domain,
            conversation_id=conversation_id,
            theta_override=theta_override,
        )
        s_decision = s_result["decision"]

        # ── Judgment memory: record every S(d) outcome ──
        # Forensic only — does NOT influence S(d). Graceful on failure.
        judgment_recorded = self._record_judgment(
            message, s_result, conversation_id, domain,
        )

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
                judgment_recorded=judgment_recorded,
            )
            self._remember(conversation_id, remember, message, None, timestamp)
            # Dynamic θ: record blocked decision for future θ adjustment
            if (DYNAMIC_THETA_ENABLED and self.temporal_memory is not None
                    and HAS_TRIAD and conversation_id is not None):
                self.temporal_memory.record_blocked_decision(
                    conversation_id, DECISION_SAFE_FREEZE)
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
                judgment_recorded=judgment_recorded,
            )
            self._remember(conversation_id, remember, message, None, timestamp)
            # Dynamic θ: record blocked decision for future θ adjustment
            if (DYNAMIC_THETA_ENABLED and self.temporal_memory is not None
                    and HAS_TRIAD and conversation_id is not None):
                self.temporal_memory.record_blocked_decision(
                    conversation_id, DECISION_SAFE_STOP)
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
                judgment_recorded=judgment_recorded,
            )
            self._remember(conversation_id, remember, message, None, timestamp)
            resp.processing_time_ms = self._elapsed_ms(start)
            return resp

        # ════════════════════════════════════════════════
        #  Triad context (fingerprint + temporal memory)
        # ════════════════════════════════════════════════
        # Gathered AFTER S(d) so the safety decision is never influenced.
        # The user_id for triad is conversation_id (which identifies a user).
        triad_context: Optional[dict] = None
        if conversation_id is not None:
            triad_context = self._get_triad_context(
                message, conversation_id, timestamp=timestamp,
            )

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
        #  Response shaper (optional — meaning_instruction layer)
        # ════════════════════════════════════════════════
        response_shape = self._shape_response(s_result, memory_context)

        # ════════════════════════════════════════════════
        #  Compose the governed prompt (P instructions + R style + memory
        #  + triad context + response shape)
        # ════════════════════════════════════════════════
        governed_prompt = self._compose_prompt(
            message=message,
            domain=domain,
            s_result=s_result,
            p_result=p_result,
            r_result=r_result,
            memory_prompt=memory_prompt,
            emergency=emergency,
            triad_context=triad_context,
            response_shape=response_shape,
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
            triad_context=triad_context,
            judgment_recorded=judgment_recorded,
            response_shape=response_shape,
        )

        # ── No LLM hook: stop at the governed prompt. The output gate only
        #    runs on a real response, so gate_result stays None. ──
        if llm_fn is None:
            self._remember(conversation_id, remember, message, None, timestamp)
            # Update triad modules even without LLM response.
            if conversation_id is not None:
                self._update_triad(
                    conversation_id, message, timestamp,
                    s_result, triad_context,
                )
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
        # Update triad modules after full pipeline processing.
        if conversation_id is not None:
            self._update_triad(
                conversation_id, message, timestamp,
                s_result, triad_context,
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
        triad_context: Optional[dict] = None,
        response_shape: Optional[object] = None,
    ) -> str:
        """
        Build the governed prompt the LLM would receive.

        This is where P(d)'s instructions, R(d)'s style, the conversation
        memory context, and triad enrichment are actually MERGED — the
        integration the review found missing. The Governor never calls a
        model; it prepares this text.
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

        # ── Triad context (fingerprint + temporal memory + intent) ──
        if triad_context:
            lines.append("")
            lines.append("## بصمة المستخدم — triad context")
            if "suggested_approach" in triad_context:
                lines.append(
                    f"Suggested approach: {triad_context['suggested_approach']}"
                )
            # Intent context from ContextualIntentScorer (consensus fix #1)
            if "intent_context" in triad_context:
                ictx = triad_context["intent_context"]
                reasoning = getattr(ictx, "approach_reasoning", "")
                if reasoning:
                    lines.append(f"Approach reasoning: {reasoning}")
            if "repetition" in triad_context:
                rep = triad_context["repetition"]
                if getattr(rep, "is_repeat", False):
                    lines.append(
                        f"⚠ Repeat question detected (reason: {rep.likely_reason}, "
                        f"action: {rep.suggested_action})"
                    )
            if "temporal" in triad_context:
                tc = triad_context["temporal"]
                greeting = getattr(tc, "suggested_greeting", "")
                if greeting:
                    lines.append(f"Suggested greeting: {greeting}")
                trajectory = getattr(tc, "emotional_trajectory", "")
                if trajectory and trajectory != "insufficient_data":
                    lines.append(f"Emotional trajectory: {trajectory}")
                unresolved = getattr(tc, "unresolved_topics", [])
                if unresolved:
                    lines.append(
                        f"Unresolved topics: {', '.join(unresolved)}"
                    )
            if "merged" in triad_context:
                insights = triad_context["merged"].get("insights", [])
                if insights:
                    lines.append("Cross-layer insights:")
                    for insight in insights:
                        lines.append(f"  - {insight}")

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

        # ── Response shape (meaning_instruction from shaper) ──
        if response_shape is not None:
            meaning = getattr(response_shape, "meaning_instruction", "")
            if meaning:
                lines.append("")
                lines.append("## تعليمات المعنى — response shape")
                lines.append(meaning)
            forbidden = getattr(response_shape, "forbidden_phrases", None)
            if forbidden:
                lines.append(
                    f"Forbidden phrases: {', '.join(forbidden)}"
                )

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
