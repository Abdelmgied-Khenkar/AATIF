#!/usr/bin/env python3
"""
AATIF Meta-Oversight Engine — المُراجع  (Field Note #031)
=========================================================

The Governor runs the engines in sequence — S(d) decides WHETHER, P(d) decides
UNDER WHAT CONDITIONS, R(d) decides IN WHAT STYLE — but until now NOTHING
checked that the three outputs actually agree with each other. Each engine is
correct on its own and yet the *combination* can be incoherent:

    R(d) says "casual / warm — جاري لهجة الشخص واطبع"
    P(d) says "EMERGENCY — طوارئ، اتصل بالإسعاف فوراً"

Both fired honestly. Together they are a contradiction: nobody answers a
chest-pain emergency in a breezy, joking tone. FN#031 calls the missing layer
المُراجع — "the self-reviewer": a meta-engine that watches the other engines,
detects contradictions among their outputs BEFORE the response is composed, and
resolves them toward the safer / more coherent reading.

    "المُراجع لا يُنشئ — هو فقط يراقب ويصحّح"
    The reviewer does not generate — it only observes and corrects.

This module is PURE LOGIC. No embeddings, no LLM, no I/O, no external state. It
takes the three already-computed engine outputs (plus the raw H/I/E scores) and
applies a small set of deterministic rules. It is meant to run after EVERY
pipeline pass, so it must be fast and side-effect-free.

WHAT IT CHECKS
──────────────
Cross-engine contradictions, each with a severity and a resolution:

  1. DECISION ↔ PROTOCOL (safety) — S proceeds (EXECUTE/CLARIFY) but P returned
     BLOCK, or S says EXECUTE while P flagged an EMERGENCY. The engines disagree
     on the gravity of the situation. → CRITICAL → the decision is overridden to
     the stricter reading (safety always wins).

  2. STYLE ↔ HARM (safety/style) — R recommends a casual/warm tone while the
     harm score H is elevated. Being light about a harmful-leaning request is
     incoherent and, at high H, unsafe. → WARNING (CRITICAL when H is high) →
     the style is tightened to "formal".

  3. STYLE ↔ PROTOCOL (style) — the tone does not match the protocol context: a
     casual tone over an EMERGENCY, or a cold/formal tone over a care protocol
     (mental-health support). → WARNING → the style is adjusted to fit.

  4. WASTED STYLE (coherence) — S blocked the message (SAFE_STOP/SAFE_FREEZE)
     yet a full response style was computed. Not harmful, just incoherent. →
     INFO → logged for the audit trail, no action taken.

RESOLUTION PRINCIPLES
─────────────────────
  • Safety always wins — if ANY engine reads danger, the danger is honoured.
  • The stricter interpretation prevails — overrides only ever move toward
    caution, never away from it.
  • Everything is logged — every contradiction is preserved in the result so the
    audit trail (GovernedResponse) can reconstruct exactly what was corrected
    and why.

The output is a `MetaOversightResult`: the contradictions found, the highest
severity, the resolution action, and the original vs. corrected values. The
Governor applies `corrected_values` (a stricter decision and/or a tightened
style) before composing the governed prompt.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Ensure the engine directory is importable (same pattern as the other modules)
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# P(d) action constants — the protocol severity vocabulary المُراجع reasons over.
from aatif_domain_protocols import (
    ACTION_NONE,
    ACTION_ESCALATE,
    ACTION_EMERGENCY,
    ACTION_BLOCK,
)


# ═══════════════════════════════════════════════════════════
#  Severity levels — درجة الخطورة
# ═══════════════════════════════════════════════════════════
#
# Ordered: CRITICAL > WARNING > INFO > NONE. The result's overall severity is
# the maximum over all contradictions found.

SEVERITY_NONE = "NONE"
SEVERITY_INFO = "INFO"          # minor inconsistency — logged, not acted on
SEVERITY_WARNING = "WARNING"    # style contradiction — R is adjusted
SEVERITY_CRITICAL = "CRITICAL"  # safety contradiction — decision is overridden

_SEVERITY_RANK = {
    SEVERITY_NONE: 0,
    SEVERITY_INFO: 1,
    SEVERITY_WARNING: 2,
    SEVERITY_CRITICAL: 3,
}


# ═══════════════════════════════════════════════════════════
#  Resolution actions — الإجراء التصحيحي
# ═══════════════════════════════════════════════════════════

RESOLUTION_NONE = "NONE"                      # coherent — nothing to do
RESOLUTION_LOG_ONLY = "LOG_ONLY"             # logged for audit, no change
RESOLUTION_ADJUST_STYLE = "ADJUST_STYLE"     # tighten / warm the R style
RESOLUTION_OVERRIDE_DECISION = "OVERRIDE_DECISION"  # escalate S decision

# When two resolutions compete, the more forceful one wins (mirrors the
# severity ordering — a decision override outranks a style tweak).
_RESOLUTION_RANK = {
    RESOLUTION_NONE: 0,
    RESOLUTION_LOG_ONLY: 1,
    RESOLUTION_ADJUST_STYLE: 2,
    RESOLUTION_OVERRIDE_DECISION: 3,
}


# ═══════════════════════════════════════════════════════════
#  Decision strictness ladder — سُلّم الصرامة
# ═══════════════════════════════════════════════════════════
#
# Strictest → most permissive. "Stricter always wins": an override may only
# raise a decision's strictness, never lower it. BLOCKED is treated as the
# strictest (it is the Governor-level "do not respond" verdict).

DECISION_EXECUTE = "EXECUTE"
DECISION_CLARIFY = "CLARIFY"
DECISION_SAFE_STOP = "SAFE_STOP"
DECISION_SAFE_FREEZE = "SAFE_FREEZE"
DECISION_BLOCKED = "BLOCKED"

_DECISION_STRICTNESS = {
    DECISION_EXECUTE: 0,
    DECISION_CLARIFY: 1,
    DECISION_SAFE_STOP: 2,
    DECISION_SAFE_FREEZE: 3,
    DECISION_BLOCKED: 3,
}

# Decisions that proceed through the rest of the pipeline.
_PROCEED_DECISIONS = {DECISION_EXECUTE, DECISION_CLARIFY}

# Style bands (from R(d), aatif_r_equation.py): formal < balanced < warm < casual.
_STYLE_CASUAL = "casual"
_STYLE_WARM = "warm"
_STYLE_BALANCED = "balanced"
_STYLE_FORMAL = "formal"

# Styles considered "light" — too informal to carry harm or an emergency.
_LIGHT_STYLES = {_STYLE_CASUAL, _STYLE_WARM}

# P(d) protocol names whose context calls for WARMTH (a cold/formal tone is the
# contradiction there). Mental-health support is the canonical case.
_CARE_PROTOCOL_NAMES = {"MENTAL_HEALTH_CARE", "CHILD_PATIENT"}


def _stricter(decision_a: str, decision_b: str) -> str:
    """Return whichever decision is stricter (safety wins on ties → a)."""
    ra = _DECISION_STRICTNESS.get(decision_a, 3)
    rb = _DECISION_STRICTNESS.get(decision_b, 3)
    return decision_a if ra >= rb else decision_b


# ═══════════════════════════════════════════════════════════
#  Contradiction — a single cross-engine conflict
# ═══════════════════════════════════════════════════════════

@dataclass
class Contradiction:
    """One detected conflict between two engine outputs — for the audit log.

    code:        stable identifier (e.g. "DECISION_VS_EMERGENCY").
    severity:    one of SEVERITY_INFO / WARNING / CRITICAL.
    engines:     the engines in conflict, e.g. ["S", "P"] or ["R", "H"].
    description: plain-language reading of the contradiction.
    resolution:  the per-contradiction action (RESOLUTION_*).
    """
    code: str
    severity: str
    engines: list
    description: str
    resolution: str = RESOLUTION_LOG_ONLY


# ═══════════════════════════════════════════════════════════
#  MetaOversightResult — نتيجة المُراجع
# ═══════════════════════════════════════════════════════════

@dataclass
class MetaOversightResult:
    """The verdict of a coherence check — every field is for the audit trail.

    contradictions_found:
        list of Contradiction objects. Empty when the engines are coherent.
    severity:
        the highest severity across all contradictions (SEVERITY_NONE when
        none were found).
    resolution_action:
        the dominant action taken (RESOLUTION_*) — the most forceful resolution
        among the contradictions found.
    original_values:
        snapshot of the engine outputs as they came in (decision, style, H, I,
        E, highest protocol action).
    corrected_values:
        only the values المُراجع changed — a stricter "decision" and/or a
        tightened "style". Empty when nothing was overridden.
    """
    contradictions_found: list = field(default_factory=list)
    severity: str = SEVERITY_NONE
    resolution_action: str = RESOLUTION_NONE
    original_values: dict = field(default_factory=dict)
    corrected_values: dict = field(default_factory=dict)

    # ── Convenience flags ──
    @property
    def is_coherent(self) -> bool:
        """True when no contradiction was found."""
        return not self.contradictions_found

    @property
    def has_critical(self) -> bool:
        """True when at least one CRITICAL (safety) contradiction fired."""
        return self.severity == SEVERITY_CRITICAL

    @property
    def requires_override(self) -> bool:
        """True when المُراجع changed a decision or a style."""
        return bool(self.corrected_values)

    @property
    def corrected_decision(self) -> Optional[str]:
        """The overridden decision, or None if the decision was untouched."""
        return self.corrected_values.get("decision")

    @property
    def corrected_style(self) -> Optional[str]:
        """The adjusted style, or None if the style was untouched."""
        return self.corrected_values.get("style")


# ═══════════════════════════════════════════════════════════
#  MetaOversightEngine — المُراجع
# ═══════════════════════════════════════════════════════════

class MetaOversightEngine:
    """Cross-engine coherence checker (FN#031).

    Pure logic — no embeddings, no LLM, no I/O. Build once, then call
    ``check_coherence(...)`` after S, P, and R are computed.

    Args:
        harm_style_floor: H at/above which a casual/warm style is incoherent
            (the θ region — the harm starts to matter). Drives STYLE_VS_HARM.
        harm_critical: H at/above which a casual/warm style is a CRITICAL
            safety contradiction (not just a style one).
    """

    def __init__(self, harm_style_floor: float = 0.40,
                 harm_critical: float = 0.60):
        self.harm_style_floor = float(harm_style_floor)
        self.harm_critical = float(harm_critical)

    # ───────────────────────────────────────────────────
    #  The main check
    # ───────────────────────────────────────────────────

    def check_coherence(
        self,
        s_decision: str,
        p_response,
        r_style,
        h_score: float,
        i_score: float,
        e_score: float,
    ) -> MetaOversightResult:
        """Detect contradictions among the S / P / R outputs and resolve them.

        Args:
            s_decision: the S(d) decision string (EXECUTE / CLARIFY /
                SAFE_STOP / SAFE_FREEZE).
            p_response: the P(d) ProtocolResult (duck-typed: .highest_action,
                .triggered). May be None when P(d) never ran (e.g. the message
                was frozen at S).
            r_style: the R(d) RReading (duck-typed: .style_recommendation).
                May be None when R(d) never ran.
            h_score, i_score, e_score: the raw H/I/E scores from the scorers.

        Returns:
            MetaOversightResult — contradictions, severity, resolution, and the
            original vs. corrected values.

        The resolution NEVER lowers strictness: a decision can only be
        escalated and a style can only be tightened/warmed. When the engines
        already agree, the result is empty and coherent.
        """
        h_score = float(h_score)
        i_score = float(i_score)
        e_score = float(e_score)

        highest_action = getattr(p_response, "highest_action", ACTION_NONE) \
            if p_response is not None else ACTION_NONE
        style = getattr(r_style, "style_recommendation", None) \
            if r_style is not None else None

        original_values = {
            "decision": s_decision,
            "style": style,
            "H": round(h_score, 4),
            "I": round(i_score, 4),
            "E": round(e_score, 4),
            "highest_action": highest_action,
        }

        contradictions: list = []
        corrected: dict = {}

        proceeds = s_decision in _PROCEED_DECISIONS

        # ── Rule 1a — DECISION ↔ BLOCK (CRITICAL safety) ──
        # S wants to proceed but a protocol said BLOCK. The engines disagree on
        # whether to respond at all; safety wins — the decision is forced to the
        # stricter blocking reading.
        if proceeds and highest_action == ACTION_BLOCK:
            target = _stricter(s_decision, DECISION_SAFE_STOP)
            corrected["decision"] = target
            contradictions.append(Contradiction(
                code="DECISION_VS_BLOCK",
                severity=SEVERITY_CRITICAL,
                engines=["S", "P"],
                description=(
                    f"S(d)={s_decision} would proceed, but P(d) returned BLOCK. "
                    f"Safety wins — decision overridden to {target}."
                ),
                resolution=RESOLUTION_OVERRIDE_DECISION,
            ))

        # ── Rule 1b — DECISION ↔ EMERGENCY (CRITICAL safety) ──
        # S read the message as a routine EXECUTE while P flagged an EMERGENCY.
        # S under-rated the gravity. Escalate EXECUTE → CLARIFY: still proceeds
        # (so the emergency guidance is injected downstream) but no longer treats
        # the situation as ordinary. CLARIFY already carries due caution, so this
        # only fires on EXECUTE.
        elif s_decision == DECISION_EXECUTE and highest_action == ACTION_EMERGENCY:
            target = _stricter(corrected.get("decision", s_decision),
                               DECISION_CLARIFY)
            corrected["decision"] = target
            contradictions.append(Contradiction(
                code="DECISION_VS_EMERGENCY",
                severity=SEVERITY_CRITICAL,
                engines=["S", "P"],
                description=(
                    f"S(d)=EXECUTE treats the message as routine, but P(d) "
                    f"flagged EMERGENCY. Decision escalated to {target} so the "
                    f"gravity is honoured."
                ),
                resolution=RESOLUTION_OVERRIDE_DECISION,
            ))

        # ── Rule 2 — STYLE ↔ HARM (style / safety) ──
        # A light (casual/warm) tone over an elevated harm score is incoherent.
        # WARNING in the θ region; CRITICAL once harm is high (being breezy about
        # genuinely harmful content is a safety problem). Either way the style is
        # tightened to "formal".
        if style in _LIGHT_STYLES and h_score >= self.harm_style_floor:
            is_high = h_score >= self.harm_critical
            sev = SEVERITY_CRITICAL if is_high else SEVERITY_WARNING
            corrected["style"] = self._tighten(corrected.get("style"), _STYLE_FORMAL)
            contradictions.append(Contradiction(
                code="STYLE_VS_HARM",
                severity=sev,
                engines=["R", "H"],
                description=(
                    f"R(d) recommends a '{style}' tone, but H={h_score:.3f} is "
                    f"elevated (≥{self.harm_style_floor}). A light tone over "
                    f"harmful-leaning content is incoherent — style tightened to "
                    f"'{_STYLE_FORMAL}'."
                ),
                resolution=RESOLUTION_ADJUST_STYLE,
            ))

        # ── Rule 3a — STYLE ↔ EMERGENCY tone (style) ──
        # A casual tone over an EMERGENCY protocol. The decision is handled by
        # rule 1b; this fixes the TONE: an emergency is answered seriously, not
        # breezily. Tighten casual → formal.
        if style == _STYLE_CASUAL and highest_action == ACTION_EMERGENCY:
            corrected["style"] = self._tighten(corrected.get("style"), _STYLE_FORMAL)
            contradictions.append(Contradiction(
                code="STYLE_VS_EMERGENCY",
                severity=SEVERITY_WARNING,
                engines=["R", "P"],
                description=(
                    "R(d) recommends a 'casual' tone, but P(d) flagged "
                    "EMERGENCY. An emergency is answered seriously — style "
                    f"tightened to '{_STYLE_FORMAL}'."
                ),
                resolution=RESOLUTION_ADJUST_STYLE,
            ))

        # ── Rule 3b — STYLE ↔ CARE tone (style) ──
        # A cold/formal tone over a care protocol (mental-health support). Here
        # the contradiction runs the OTHER way: the context needs warmth, and a
        # clinical/cold tone is the mismatch. Warm the style up.
        if style == _STYLE_FORMAL and self._is_care_context(p_response):
            care_name = self._care_protocol_name(p_response)
            corrected["style"] = self._warm(corrected.get("style"), _STYLE_WARM)
            contradictions.append(Contradiction(
                code="STYLE_VS_CARE",
                severity=SEVERITY_WARNING,
                engines=["R", "P"],
                description=(
                    f"R(d) recommends a cold 'formal' tone, but P(d) flagged a "
                    f"care context ({care_name}). Care needs warmth — style "
                    f"adjusted to '{_STYLE_WARM}'."
                ),
                resolution=RESOLUTION_ADJUST_STYLE,
            ))

        # ── Rule 4 — WASTED STYLE (coherence, INFO) ──
        # S blocked the message (SAFE_STOP/SAFE_FREEZE) yet a full response style
        # was computed. Not harmful — just incoherent effort. Logged only.
        if not proceeds and style is not None:
            contradictions.append(Contradiction(
                code="WASTED_STYLE",
                severity=SEVERITY_INFO,
                engines=["S", "R"],
                description=(
                    f"S(d)={s_decision} blocks the message, yet R(d) computed a "
                    f"'{style}' style that will never be used. Incoherent but "
                    f"harmless — logged for the audit trail."
                ),
                resolution=RESOLUTION_LOG_ONLY,
            ))

        # ── Aggregate severity + dominant resolution ──
        severity = SEVERITY_NONE
        resolution_action = RESOLUTION_NONE
        for c in contradictions:
            if _SEVERITY_RANK[c.severity] > _SEVERITY_RANK[severity]:
                severity = c.severity
            if _RESOLUTION_RANK[c.resolution] > _RESOLUTION_RANK[resolution_action]:
                resolution_action = c.resolution

        # Drop a "corrected" value that ended up identical to the original
        # (defensive — _tighten/_warm/_stricter never weaken, but never claim a
        # change that didn't happen).
        if corrected.get("decision") == s_decision:
            corrected.pop("decision", None)
        if corrected.get("style") == style:
            corrected.pop("style", None)

        return MetaOversightResult(
            contradictions_found=contradictions,
            severity=severity,
            resolution_action=resolution_action,
            original_values=original_values,
            corrected_values=corrected,
        )

    # ───────────────────────────────────────────────────
    #  Style-resolution helpers
    # ───────────────────────────────────────────────────

    @staticmethod
    def _tighten(current: Optional[str], target: str) -> str:
        """Tighten toward a more formal style — never loosen.

        ``current`` is any style already chosen by an earlier rule this pass.
        Returns the MORE formal of (current, target).
        """
        order = {_STYLE_FORMAL: 0, _STYLE_BALANCED: 1, _STYLE_WARM: 2,
                 _STYLE_CASUAL: 3}
        if current is None:
            return target
        return current if order.get(current, 3) <= order.get(target, 3) else target

    @staticmethod
    def _warm(current: Optional[str], target: str) -> str:
        """Warm a cold tone up to ``target`` unless an earlier rule already
        tightened it (a harm/emergency correction outranks a warmth nudge)."""
        # If a formal-ward correction already ran this pass, respect it — harm
        # and emergencies dominate the "needs warmth" nudge.
        order = {_STYLE_FORMAL: 0, _STYLE_BALANCED: 1, _STYLE_WARM: 2,
                 _STYLE_CASUAL: 3}
        if current is None:
            return target
        # current is a deliberate formal-ward choice → keep it.
        if order.get(current, 3) < order.get(target, 3):
            return current
        return target

    @staticmethod
    def _is_care_context(p_response) -> bool:
        """True when P(d) flagged a context that calls for warmth (care)."""
        if p_response is None:
            return False
        for t in getattr(p_response, "triggered", []) or []:
            if getattr(t, "name", "") in _CARE_PROTOCOL_NAMES:
                return True
            if getattr(t, "action", "") == ACTION_ESCALATE:
                return True
        return False

    @staticmethod
    def _care_protocol_name(p_response) -> str:
        """Name of the care protocol that fired (for the audit message)."""
        if p_response is None:
            return "care"
        for t in getattr(p_response, "triggered", []) or []:
            if getattr(t, "name", "") in _CARE_PROTOCOL_NAMES:
                return t.name
        for t in getattr(p_response, "triggered", []) or []:
            if getattr(t, "action", "") == ACTION_ESCALATE:
                return getattr(t, "name", "ESCALATE")
        return "care"


# ═══════════════════════════════════════════════════════════
#  Self-test (pure logic — no Ollama needed)
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":  # pragma: no cover - manual smoke test
    from dataclasses import dataclass as _dc

    @_dc
    class _FakeProto:
        highest_action: str
        triggered: list = field(default_factory=list)

    @_dc
    class _FakeTrig:
        name: str
        action: str

    @_dc
    class _FakeStyle:
        style_recommendation: str

    reviewer = MetaOversightEngine()

    emergency_p = _FakeProto(
        ACTION_EMERGENCY,
        [_FakeTrig("EMERGENCY_PROTOCOL", ACTION_EMERGENCY)],
    )
    care_p = _FakeProto(
        ACTION_ESCALATE,
        [_FakeTrig("MENTAL_HEALTH_CARE", ACTION_ESCALATE)],
    )
    clean_p = _FakeProto(ACTION_NONE, [])

    cases = [
        ("coherent EXECUTE", DECISION_EXECUTE, clean_p,
         _FakeStyle("balanced"), 0.10, 0.90, 0.20),
        ("EXECUTE + EMERGENCY (safety)", DECISION_EXECUTE, emergency_p,
         _FakeStyle("casual"), 0.20, 0.80, 0.70),
        ("casual + high harm (safety)", DECISION_CLARIFY, clean_p,
         _FakeStyle("casual"), 0.65, 0.50, 0.30),
        ("cold tone + care context (style)", DECISION_EXECUTE, care_p,
         _FakeStyle("formal"), 0.15, 0.85, 0.60),
        ("blocked but style computed (info)", DECISION_SAFE_STOP, clean_p,
         _FakeStyle("warm"), 0.55, 0.20, 0.30),
    ]

    print("=" * 72)
    print("  AATIF Meta-Oversight — المُراجع  (FN#031)")
    print("=" * 72)
    for note, dec, p, r, h, i, e in cases:
        res = reviewer.check_coherence(dec, p, r, h, i, e)
        print(f"\n📝 {note}")
        print(f"   severity={res.severity}  resolution={res.resolution_action}")
        print(f"   corrected={res.corrected_values or '—'}")
        for c in res.contradictions_found:
            print(f"   ↳ [{c.severity}] {c.code}: {c.description}")
    print("\n✅ Meta-Oversight smoke test complete.")
