#!/usr/bin/env python3
"""
test_meta_oversight.py — المُراجع (FN#031)
==========================================
Covers ``engine/aatif_meta_oversight.py`` — the Meta-Oversight Engine that
detects CONTRADICTIONS among the S(d), P(d), and R(d) outputs before a response
is composed, plus its integration into the Governor pipeline.

The module is PURE LOGIC (no embeddings, no LLM), so every test here runs
WITHOUT Ollama. Two layers:

  1. Unit tests on MetaOversightEngine.check_coherence — driving the engine with
     constructed S/P/R outputs and pinning each contradiction rule, its
     severity, and its resolution.

  2. Integration tests on the Governor — with a mocked S engine (FakeSEngine,
     same pattern as test_governor.py) and the REAL P/R stages, asserting that
     the reviewer runs every pass and that CRITICAL contradictions escalate the
     decision / tighten the style.

License: BSL 1.1
"""
import os
import sys
import types

import pytest

# Ensure the engine directory is importable (same pattern as the other tests).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_THIS_DIR, "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_meta_oversight import (  # noqa: E402
    MetaOversightEngine,
    MetaOversightResult,
    Contradiction,
    SEVERITY_NONE,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    SEVERITY_CRITICAL,
    RESOLUTION_NONE,
    RESOLUTION_LOG_ONLY,
    RESOLUTION_ADJUST_STYLE,
    RESOLUTION_OVERRIDE_DECISION,
    DECISION_EXECUTE,
    DECISION_CLARIFY,
    DECISION_SAFE_STOP,
    DECISION_SAFE_FREEZE,
    _stricter,
)
from aatif_domain_protocols import (  # noqa: E402
    ProtocolResult,
    TriggeredProtocol,
    ACTION_NONE,
    ACTION_GUIDE,
    ACTION_DISCLAIMER,
    ACTION_ESCALATE,
    ACTION_EMERGENCY,
    ACTION_BLOCK,
)
from aatif_r_equation import RReading  # noqa: E402


# ═══════════════════════════════════════════════════════════
#  Fixtures — build realistic P(d) and R(d) outputs
# ═══════════════════════════════════════════════════════════

def make_p(highest_action=ACTION_NONE, names=None):
    """Build a ProtocolResult with the given highest action + triggered names.

    ``names`` is a list of (name, action) pairs for the triggered protocols.
    """
    triggered = []
    if names:
        for name, action in names:
            triggered.append(TriggeredProtocol(
                name=name, action=action, instruction="...", domain="test",
            ))
    return ProtocolResult(
        triggered=triggered,
        highest_action=highest_action,
        combined_instructions="..." if triggered else "",
        has_protocols=bool(triggered),
    )


def make_r(style):
    """Build an RReading with a given style recommendation."""
    return RReading(
        r_score=0.5,
        t_signal=0.5, v_signal=0.5, g_signal=0.5, d_signal=0.5,
        style_recommendation=style,
    )


EMERGENCY_P = make_p(ACTION_EMERGENCY, [("EMERGENCY_PROTOCOL", ACTION_EMERGENCY)])
BLOCK_P = make_p(ACTION_BLOCK, [("DANGEROUS_COMMAND", ACTION_BLOCK)])
CARE_P = make_p(ACTION_ESCALATE, [("MENTAL_HEALTH_CARE", ACTION_ESCALATE)])
CLEAN_P = make_p(ACTION_NONE)
DISCLAIMER_P = make_p(ACTION_DISCLAIMER, [("MEDICATION_DISCLAIMER", ACTION_DISCLAIMER)])


@pytest.fixture
def reviewer():
    return MetaOversightEngine()


# ═══════════════════════════════════════════════════════════
#  1. No-contradiction cases — coherent outputs pass clean
# ═══════════════════════════════════════════════════════════

def test_coherent_execute_no_contradictions(reviewer):
    res = reviewer.check_coherence(
        DECISION_EXECUTE, CLEAN_P, make_r("balanced"),
        h_score=0.10, i_score=0.90, e_score=0.20,
    )
    assert isinstance(res, MetaOversightResult)
    assert res.is_coherent
    assert res.contradictions_found == []
    assert res.severity == SEVERITY_NONE
    assert res.resolution_action == RESOLUTION_NONE
    assert res.corrected_values == {}
    assert res.requires_override is False
    assert res.has_critical is False


def test_coherent_warm_low_harm_passes(reviewer):
    # Warm tone is fine when there is no harm and no emergency.
    res = reviewer.check_coherence(
        DECISION_EXECUTE, CLEAN_P, make_r("warm"),
        h_score=0.05, i_score=0.95, e_score=0.60,
    )
    assert res.is_coherent
    assert res.corrected_decision is None
    assert res.corrected_style is None


def test_coherent_casual_general_passes(reviewer):
    # Casual general chit-chat, no protocol, no harm → coherent.
    res = reviewer.check_coherence(
        DECISION_EXECUTE, CLEAN_P, make_r("casual"),
        h_score=0.08, i_score=0.88, e_score=0.30,
    )
    assert res.is_coherent


def test_original_values_always_snapshotted(reviewer):
    res = reviewer.check_coherence(
        DECISION_EXECUTE, CLEAN_P, make_r("balanced"),
        h_score=0.123, i_score=0.456, e_score=0.789,
    )
    ov = res.original_values
    assert ov["decision"] == DECISION_EXECUTE
    assert ov["style"] == "balanced"
    assert ov["H"] == 0.123
    assert ov["I"] == 0.456
    assert ov["E"] == 0.789
    assert ov["highest_action"] == ACTION_NONE


# ═══════════════════════════════════════════════════════════
#  2. Safety contradictions — S says safe but P says danger
# ═══════════════════════════════════════════════════════════

def test_execute_plus_emergency_is_critical(reviewer):
    # S=EXECUTE (routine) but P=EMERGENCY → CRITICAL, decision escalated.
    res = reviewer.check_coherence(
        DECISION_EXECUTE, EMERGENCY_P, make_r("balanced"),
        h_score=0.20, i_score=0.80, e_score=0.70,
    )
    assert res.has_critical
    assert res.severity == SEVERITY_CRITICAL
    assert res.resolution_action == RESOLUTION_OVERRIDE_DECISION
    # Escalated toward caution, but still a proceeding decision so emergency
    # guidance still flows downstream.
    assert res.corrected_decision == DECISION_CLARIFY
    codes = [c.code for c in res.contradictions_found]
    assert "DECISION_VS_EMERGENCY" in codes


def test_execute_plus_block_is_critical_and_blocks(reviewer):
    # S would proceed but P=BLOCK → CRITICAL, decision forced to a blocking one.
    res = reviewer.check_coherence(
        DECISION_EXECUTE, BLOCK_P, make_r("balanced"),
        h_score=0.30, i_score=0.50, e_score=0.20,
    )
    assert res.has_critical
    assert res.corrected_decision == DECISION_SAFE_STOP
    assert res.resolution_action == RESOLUTION_OVERRIDE_DECISION
    codes = [c.code for c in res.contradictions_found]
    assert "DECISION_VS_BLOCK" in codes


def test_clarify_plus_block_still_blocks(reviewer):
    # Even CLARIFY (already cautious) must yield to a P=BLOCK.
    res = reviewer.check_coherence(
        DECISION_CLARIFY, BLOCK_P, make_r("formal"),
        h_score=0.35, i_score=0.40, e_score=0.20,
    )
    assert res.corrected_decision == DECISION_SAFE_STOP
    assert res.has_critical


def test_casual_plus_high_harm_is_critical(reviewer):
    # Casual tone over genuinely high harm is a safety contradiction.
    res = reviewer.check_coherence(
        DECISION_CLARIFY, CLEAN_P, make_r("casual"),
        h_score=0.65, i_score=0.40, e_score=0.30,
    )
    assert res.has_critical
    assert res.corrected_style == "formal"
    codes = [c.code for c in res.contradictions_found]
    assert "STYLE_VS_HARM" in codes


def test_casual_plus_moderate_harm_is_warning(reviewer):
    # In the θ region (0.40–0.60) the same mismatch is a WARNING, not CRITICAL.
    res = reviewer.check_coherence(
        DECISION_CLARIFY, CLEAN_P, make_r("casual"),
        h_score=0.45, i_score=0.55, e_score=0.30,
    )
    assert res.severity == SEVERITY_WARNING
    assert res.has_critical is False
    assert res.corrected_style == "formal"


def test_harm_just_below_floor_does_not_fire(reviewer):
    # H below the style floor (0.40) leaves a casual tone untouched.
    res = reviewer.check_coherence(
        DECISION_EXECUTE, CLEAN_P, make_r("casual"),
        h_score=0.39, i_score=0.60, e_score=0.30,
    )
    assert res.is_coherent
    assert res.corrected_style is None


# ═══════════════════════════════════════════════════════════
#  3. Style contradictions — tone doesn't match the context
# ═══════════════════════════════════════════════════════════

def test_casual_plus_emergency_flags_style(reviewer):
    # The field-note headline case: casual tone over an EMERGENCY.
    res = reviewer.check_coherence(
        DECISION_CLARIFY, EMERGENCY_P, make_r("casual"),
        h_score=0.20, i_score=0.70, e_score=0.65,
    )
    codes = [c.code for c in res.contradictions_found]
    assert "STYLE_VS_EMERGENCY" in codes
    assert res.corrected_style == "formal"


def test_cold_tone_over_care_context_warms_up(reviewer):
    # P flagged mental-health care but R is cold/formal → warm it up.
    res = reviewer.check_coherence(
        DECISION_EXECUTE, CARE_P, make_r("formal"),
        h_score=0.15, i_score=0.85, e_score=0.55,
    )
    codes = [c.code for c in res.contradictions_found]
    assert "STYLE_VS_CARE" in codes
    assert res.corrected_style == "warm"
    assert res.severity == SEVERITY_WARNING


def test_balanced_tone_over_care_is_fine(reviewer):
    # Only a COLD (formal) tone is the care-context contradiction; a balanced
    # tone is acceptable.
    res = reviewer.check_coherence(
        DECISION_EXECUTE, CARE_P, make_r("balanced"),
        h_score=0.15, i_score=0.85, e_score=0.55,
    )
    assert res.is_coherent


# ═══════════════════════════════════════════════════════════
#  4. Resolution — stricter always wins / safety dominates
# ═══════════════════════════════════════════════════════════

def test_stricter_helper_orders_decisions():
    assert _stricter(DECISION_EXECUTE, DECISION_CLARIFY) == DECISION_CLARIFY
    assert _stricter(DECISION_CLARIFY, DECISION_SAFE_STOP) == DECISION_SAFE_STOP
    assert _stricter(DECISION_SAFE_STOP, DECISION_SAFE_FREEZE) == DECISION_SAFE_FREEZE
    # Ties resolve to the first argument (both equally strict).
    assert _stricter(DECISION_SAFE_STOP, DECISION_SAFE_STOP) == DECISION_SAFE_STOP


def test_override_never_loosens_decision(reviewer):
    # A SAFE_STOP decision is never lowered, even if a protocol is benign.
    res = reviewer.check_coherence(
        DECISION_SAFE_STOP, CLEAN_P, None,
        h_score=0.55, i_score=0.20, e_score=0.30,
    )
    # No proceed → no decision override; SAFE_STOP stays as-is.
    assert res.corrected_decision is None


def test_combined_emergency_and_casual_overrides_both(reviewer):
    # EXECUTE + EMERGENCY + casual → decision escalated AND style tightened.
    res = reviewer.check_coherence(
        DECISION_EXECUTE, EMERGENCY_P, make_r("casual"),
        h_score=0.20, i_score=0.80, e_score=0.70,
    )
    assert res.corrected_decision == DECISION_CLARIFY  # safety
    assert res.corrected_style == "formal"             # tone
    # Decision override is the dominant (most forceful) resolution.
    assert res.resolution_action == RESOLUTION_OVERRIDE_DECISION
    assert res.severity == SEVERITY_CRITICAL


def test_harm_correction_dominates_care_warmth(reviewer):
    # If a request both needs warmth (care) and carries high harm, the harm
    # correction (→ formal) must win over the warmth nudge — safety dominates.
    res = reviewer.check_coherence(
        DECISION_CLARIFY, CARE_P, make_r("casual"),
        h_score=0.65, i_score=0.40, e_score=0.55,
    )
    # casual + high harm → formal (care rule only fires on a formal start).
    assert res.corrected_style == "formal"


# ═══════════════════════════════════════════════════════════
#  5. Edge cases — blocked decisions, missing P/R, INFO only
# ═══════════════════════════════════════════════════════════

def test_safe_freeze_with_no_p_or_r_is_coherent(reviewer):
    # SAFE_FREEZE halts before P/R run — passing None for both is fine.
    res = reviewer.check_coherence(
        DECISION_SAFE_FREEZE, None, None,
        h_score=0.90, i_score=0.10, e_score=0.20,
    )
    assert res.is_coherent
    assert res.corrected_values == {}


def test_safe_stop_with_wasted_style_is_info(reviewer):
    # If a style was computed for a blocked decision, that's INFO (wasteful, not
    # harmful) — logged, no action.
    res = reviewer.check_coherence(
        DECISION_SAFE_STOP, CLEAN_P, make_r("formal"),
        h_score=0.30, i_score=0.30, e_score=0.20,
    )
    codes = [c.code for c in res.contradictions_found]
    assert "WASTED_STYLE" in codes
    info = [c for c in res.contradictions_found if c.code == "WASTED_STYLE"][0]
    assert info.severity == SEVERITY_INFO
    assert info.resolution == RESOLUTION_LOG_ONLY
    # An INFO-only verdict makes no corrections.
    assert res.corrected_values == {}


def test_clarify_with_normal_protocol_is_coherent(reviewer):
    # CLARIFY + a mild disclaimer protocol + balanced tone → coherent.
    res = reviewer.check_coherence(
        DECISION_CLARIFY, DISCLAIMER_P, make_r("balanced"),
        h_score=0.25, i_score=0.55, e_score=0.30,
    )
    assert res.is_coherent
    assert res.corrected_values == {}


def test_contradiction_dataclass_shape(reviewer):
    res = reviewer.check_coherence(
        DECISION_EXECUTE, EMERGENCY_P, make_r("balanced"),
        h_score=0.20, i_score=0.80, e_score=0.70,
    )
    c = res.contradictions_found[0]
    assert isinstance(c, Contradiction)
    assert c.code and c.severity and c.engines and c.description
    assert "S" in c.engines and "P" in c.engines


# ═══════════════════════════════════════════════════════════
#  6. Governor integration — المُراجع runs every pass
# ═══════════════════════════════════════════════════════════

from aatif_governor import (  # noqa: E402
    AATIFGovernor,
    HAS_META_OVERSIGHT,
)
from aatif_governor import (  # noqa: E402
    DECISION_EXECUTE as G_EXECUTE,
    DECISION_CLARIFY as G_CLARIFY,
)


class FakeSEngine:
    """Stand-in for AATIFEngine (same pattern as test_governor.py)."""

    def __init__(self, decision=G_EXECUTE, S=0.95, H=0.10, I=0.90, E=0.85,
                 backend="ollama:bge-m3"):
        self.h_scorer = types.SimpleNamespace(backend_name=backend)
        self._decision = decision
        self._S, self._H, self._I, self._E = S, H, I, E

    def compute(self, text, **kwargs):
        return {
            "text": text, "decision": self._decision, "S": self._S,
            "H": self._H, "I": self._I, "E": self._E,
            "F": round(1.0 - self._S, 4), "confidence": "high",
            "profile": kwargs.get("profile"),
            "equation_mode": kwargs.get("equation_mode"),
            "domain": kwargs.get("domain"),
        }


def _benign_llm(prompt: str) -> str:
    return "تمام، أنا معك."


def make_governor(decision=G_EXECUTE, H=0.10):
    engine = FakeSEngine(decision=decision, H=H)
    return AATIFGovernor(s_engine=engine)


def test_meta_oversight_module_is_available():
    assert HAS_META_OVERSIGHT is True


def test_governor_auto_wires_meta_oversight():
    gov = make_governor()
    assert gov.meta_oversight is not None


def test_oversight_runs_and_records_on_clean_message():
    # A benign EXECUTE message: the reviewer runs, finds nothing, records a
    # coherent verdict — and nothing is overridden (zero regression).
    gov = make_governor(decision=G_EXECUTE)
    r = gov.process("اشرح لي كيف تعمل الجاذبية", domain="education",
                    conversation_id="c1", llm_fn=_benign_llm)
    assert r.oversight_result is not None
    assert r.oversight_result.is_coherent
    assert r.oversight_overridden is False
    assert r.final_decision == G_EXECUTE
    assert r.blocked is False


def test_oversight_escalates_execute_emergency_to_clarify():
    # FakeSEngine says EXECUTE; the REAL protocol engine flags EMERGENCY for a
    # chest-pain message → المُراجع escalates EXECUTE → CLARIFY.
    gov = make_governor(decision=G_EXECUTE)
    r = gov.process("عندي ألم في صدري", domain="healthcare",
                    conversation_id="c1", llm_fn=_benign_llm)
    # Sanity: P really did flag EMERGENCY.
    assert r.p_result.highest_action == ACTION_EMERGENCY
    # The reviewer caught the safety contradiction and escalated.
    assert r.oversight_result is not None
    assert r.oversight_result.has_critical
    assert r.oversight_overridden is True
    assert r.final_decision == G_CLARIFY
    # Still proceeded — emergency guidance is injected, not blocked.
    assert r.blocked is False
    assert r.emergency_injected is True


def test_oversight_does_not_disturb_normal_clarify():
    gov = make_governor(decision=G_CLARIFY)
    r = gov.process("ساعدني في موضوع", domain="general",
                    conversation_id="c1", llm_fn=_benign_llm)
    assert r.final_decision == G_CLARIFY
    assert r.oversight_overridden is False
    assert r.blocked is False


def test_oversight_present_in_audit_trail_without_llm():
    # Even when stopping at the governed prompt, the oversight verdict is on the
    # audit trail.
    gov = make_governor(decision=G_EXECUTE)
    r = gov.process("سؤال عادي", domain="general", llm_fn=None)
    assert r.oversight_result is not None
