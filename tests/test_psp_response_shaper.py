#!/usr/bin/env python3
"""
FN#070 ResponseShaper PSP integration tests — aatif_response_shaper.py

WHY THIS FILE EXISTS
────────────────────
FN#070 (Possibility Space Preservation) is STYLISTIC, not safety. It binds
through B5 (Behaviour), never B6 (Safety). The ResponseShaper is where a
PSPReading becomes prompt language: it folds clarify_width into G_eff, runs
that through the R equation, and emits the bounded-alternative instruction.

This file is the regression wall for that arithmetic and that instruction:
  1. G_eff = G + κ·clarify_width_pressure — pressure rises with bounded_count,
     so a decision point ALWAYS lifts G_eff above the base G.
  2. R = σ(w₃·T + w₄·V + w₅·G_eff + w₆·D + bias) — stays in [0,1], style only.
  3. bounded alternatives are preserved when is_decision_point is True.
  4. closure_risk > 0.5 → trade-offs required for each path.
  5. user_requested_closure → a single-path recommendation is permitted.
  6. psp_profile is a CONFIG LOOKUP (domain_config), never computed.
  7. a non-decision turn is inert — width 1, G_eff == G, empty instruction.

ISOLATION STRATEGY
──────────────────
Pure offline. PSPReadings come from the real PSPDetector (deterministic tiers,
no embedder, no Ollama). shape() integration is exercised with a duck-typed
FakeReading exposing only the attributes the shaper touches — same approach as
test_response_shaper.py.

Design consensus: Claude × ChatGPT, 2026-06-30 (FN070_DESIGN_CONSENSUS.md)
License: BSL 1.1 — Architect: Abdulmjeed Ibrahim Khenkar
"""

import pytest

from aatif_response_shaper import (
    AATIFResponseShaper,
    PSPShaping,
    ResponseShape,
    PSP_KAPPA,
)
from aatif_psp_detector import (
    PSPDetector,
    PSPReading,
    LivePath,
    DomainPSPConfig,
    BOUNDED_HARD_MAX,
    TRADEOFF_REQUIRED_THRESHOLD,
)


# ═══════════════════════════════════════════════════════════════
#  Fixtures / helpers
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def shaper():
    return AATIFResponseShaper()


@pytest.fixture
def detector():
    return PSPDetector()  # no embedder — tiers 1 & 3 only


def reading_for(detector, text, domain="general"):
    return detector.detect(text, domain_config=DomainPSPConfig.for_domain(domain))


class FakeReading:
    """Duck-typed stand-in for IntentReading — only what shape() touches."""
    def __init__(self, **kw):
        defaults = dict(
            decision="EXECUTE", decision_reason="", mode="NORMAL",
            emotional_state="clear", emotional_confidence=0.8,
            load_bearing=False, dialect_detected="english",
            ambiguity_score=0.1, harm_score=0.0, softening_factor=0.5,
            skills_to_activate=[], deep_intent="",
        )
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(self, k, v)


# ═══════════════════════════════════════════════════════════════
#  TestGEffComputation — clarify_width → G_eff
# ═══════════════════════════════════════════════════════════════

class TestGEffComputation:
    def test_decision_point_lifts_g_eff_above_g(self, shaper, detector):
        r = reading_for(detector, "should I rent or buy a home?")
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("general"))
        assert ps.active is True
        assert ps.g_eff > ps.g_signal, "decision point must raise G_eff"

    def test_g_eff_matches_formula(self, shaper, detector):
        r = reading_for(detector, "should I rent or buy a home?")
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("general"),
                              g_signal=0.45)
        expected = 0.45 + PSP_KAPPA * ps.clarify_width_pressure
        assert ps.g_eff == pytest.approx(min(1.0, expected), abs=1e-4)

    def test_g_eff_clamped_to_unit_interval(self, shaper, detector):
        r = reading_for(detector, "which plot twist should I use?",
                        domain="creative")
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("creative"),
                              g_signal=0.9)
        assert 0.0 <= ps.g_eff <= 1.0

    def test_non_decision_leaves_g_unchanged(self, shaper, detector):
        r = reading_for(detector, "what is the capital of France?")
        ps = shaper.shape_psp(r)
        assert ps.active is False
        assert ps.clarify_width == 1
        assert ps.clarify_width_pressure == 0.0
        assert ps.g_eff == ps.g_signal

    def test_clarify_width_pressure_in_range(self, shaper, detector):
        for text, dom in [("should I rent or buy?", "general"),
                          ("should I have the surgery?", "healthcare"),
                          ("which plot twist?", "creative"),
                          ("hello", "general")]:
            r = reading_for(detector, text, dom)
            ps = shaper.shape_psp(r, DomainPSPConfig.for_domain(dom))
            assert 0.0 <= ps.clarify_width_pressure <= 1.0


# ═══════════════════════════════════════════════════════════════
#  TestClarifyWidth — 1 normal / 2-3 PSP-aware / >3 category choice
# ═══════════════════════════════════════════════════════════════

class TestClarifyWidth:
    def test_normal_width_for_non_decision(self, shaper, detector):
        r = reading_for(detector, "what time is it in Tokyo?")
        ps = shaper.shape_psp(r)
        assert ps.clarify_width == 1

    def test_default_decision_is_psp_aware(self, shaper, detector):
        r = reading_for(detector, "should I rent or buy?")
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("general"))
        assert ps.clarify_width == 3              # bounded_count default
        assert 2 <= ps.clarify_width <= 3         # PSP-aware band

    def test_creative_is_category_choice(self, shaper, detector):
        r = reading_for(detector, "which plot twist should I use?",
                        domain="creative")
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("creative"))
        assert ps.clarify_width == 5              # category choice (>3)
        assert ps.clarify_width_pressure == pytest.approx(1.0)

    def test_width_never_exceeds_hard_max(self, shaper, detector):
        for dom in ["healthcare", "creative", "education", "general"]:
            r = reading_for(detector, "which one should I choose?", dom)
            ps = shaper.shape_psp(r, DomainPSPConfig.for_domain(dom))
            assert ps.clarify_width <= BOUNDED_HARD_MAX


# ═══════════════════════════════════════════════════════════════
#  TestRComputation — R stays a style score in [0,1]
# ═══════════════════════════════════════════════════════════════

class TestRComputation:
    def test_r_in_unit_interval(self, shaper, detector):
        for text, dom in [("should I rent or buy?", "general"),
                          ("should I have the surgery?", "healthcare"),
                          ("hello", "general")]:
            r = reading_for(detector, text, dom)
            ps = shaper.shape_psp(r, DomainPSPConfig.for_domain(dom))
            assert 0.0 <= ps.r_score <= 1.0

    def test_higher_pressure_raises_r_all_else_equal(self, shaper):
        """A wider clarify_width → higher G_eff → higher R (same T/V/D)."""
        narrow = PSPReading(is_decision_point=True, decision_confidence=0.8,
                            closure_risk=0.4, bounded_count=2)
        wide = PSPReading(is_decision_point=True, decision_confidence=0.8,
                          closure_risk=0.4, bounded_count=5)
        ps_n = shaper.shape_psp(narrow, DomainPSPConfig.for_domain("general"))
        ps_w = shaper.shape_psp(wide, DomainPSPConfig.for_domain("general"))
        assert ps_w.g_eff > ps_n.g_eff
        assert ps_w.r_score > ps_n.r_score


# ═══════════════════════════════════════════════════════════════
#  TestBoundedAlternatives — preserved on decision points
# ═══════════════════════════════════════════════════════════════

class TestBoundedAlternatives:
    def test_instruction_present_on_decision(self, shaper, detector):
        r = reading_for(detector, "should I rent or buy?")
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("general"))
        assert ps.instruction != ""
        assert "خيارات" in ps.instruction        # "options"
        assert "نحصر" in ps.instruction           # "bound the realistic set"

    def test_instruction_empty_when_not_decision(self, shaper, detector):
        r = reading_for(detector, "define photosynthesis")
        ps = shaper.shape_psp(r)
        assert ps.instruction == ""

    def test_instruction_names_live_paths(self, shaper):
        r = PSPReading(
            is_decision_point=True, decision_confidence=0.8, closure_risk=0.4,
            bounded_count=3,
            live_paths=[LivePath("Option A"), LivePath("Option B")],
        )
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("general"))
        assert "Option A" in ps.instruction
        assert "Option B" in ps.instruction


# ═══════════════════════════════════════════════════════════════
#  TestClosureHandling — trade-offs & single-path permission
# ═══════════════════════════════════════════════════════════════

class TestClosureHandling:
    def test_high_closure_risk_requires_tradeoffs(self, shaper, detector):
        r = reading_for(detector, "should I have the surgery or wait?",
                        domain="healthcare")
        assert r.closure_risk > TRADEOFF_REQUIRED_THRESHOLD
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("healthcare"))
        assert ps.require_tradeoffs is True
        assert "ميزة" in ps.instruction and "عيب" in ps.instruction

    def test_low_closure_risk_allows_lightweight(self, shaper, detector):
        r = reading_for(detector, "should I get the blue or red shirt?")
        assert r.closure_risk <= TRADEOFF_REQUIRED_THRESHOLD
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("general"))
        assert ps.require_tradeoffs is False
        assert "مبسّط" in ps.instruction

    def test_user_requested_closure_allows_single_path(self, shaper, detector):
        r = reading_for(detector,
                        "which one is best — surgery or therapy? just tell me one.",
                        domain="healthcare")
        assert r.user_requested_closure is True
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("healthcare"))
        assert ps.allow_single_path is True
        assert "ترشّح" in ps.instruction          # may recommend one

    def test_unprompted_forbids_premature_single_path(self, shaper, detector):
        r = reading_for(detector, "should I rent or buy a home?")
        assert r.user_requested_closure is False
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("general"))
        assert ps.allow_single_path is False
        assert "القرار النهائي للشخص" in ps.instruction


# ═══════════════════════════════════════════════════════════════
#  TestProfileLookup — psp_profile is config, not computation
# ═══════════════════════════════════════════════════════════════

class TestProfileLookup:
    def test_profile_from_domain_config(self, shaper, detector):
        r = reading_for(detector, "which one should I pick?", domain="healthcare")
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("healthcare"))
        assert ps.psp_profile == "high"

    def test_profile_general_medium(self, shaper, detector):
        r = reading_for(detector, "which one should I pick?")
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("general"))
        assert ps.psp_profile == "medium"

    def test_profile_read_from_dict_config(self, shaper, detector):
        r = reading_for(detector, "which one should I pick?")
        ps = shaper.shape_psp(r, {"domain": "x", "psp_profile": "high"})
        assert ps.psp_profile == "high"

    def test_profile_falls_back_to_domain_table(self, shaper, detector):
        """No explicit psp_profile → mapped from the domain name."""
        r = reading_for(detector, "which one should I pick?")
        ps = shaper.shape_psp(r, {"domain": "legal"})
        assert ps.psp_profile == "high"

    def test_high_profile_adds_advisor_framing(self, shaper, detector):
        r = reading_for(detector, "which one should I pick?", domain="healthcare")
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("healthcare"))
        assert "مستشار" in ps.instruction          # advisor, not decider


# ═══════════════════════════════════════════════════════════════
#  TestShapeIntegration — PSP folds into the meaning instruction
# ═══════════════════════════════════════════════════════════════

class TestShapeIntegration:
    def test_shape_attaches_psp_shaping(self, shaper, detector):
        psp = reading_for(detector, "should I rent or buy?")
        shape = shaper.shape(
            FakeReading(deep_intent="housing decision"),
            psp_reading=psp,
            psp_domain_config=DomainPSPConfig.for_domain("general"),
        )
        assert isinstance(shape, ResponseShape)
        assert isinstance(shape.psp_shaping, PSPShaping)
        assert shape.psp_shaping.active is True

    def test_shape_appends_psp_instruction_to_meaning(self, shaper, detector):
        psp = reading_for(detector, "should I rent or buy?")
        shape = shaper.shape(FakeReading(), psp_reading=psp,
                             psp_domain_config=DomainPSPConfig.for_domain("general"))
        assert "نحصر الخيارات" in shape.meaning_instruction

    def test_shape_without_psp_is_unchanged(self, shaper):
        """Backwards-compatible: no psp_reading → no psp_shaping, no PSP text."""
        shape = shaper.shape(FakeReading(deep_intent="greeting"))
        assert shape.psp_shaping is None
        assert "نحصر الخيارات" not in shape.meaning_instruction

    def test_shape_non_decision_psp_adds_no_instruction(self, shaper, detector):
        psp = reading_for(detector, "what is the capital of France?")
        shape = shaper.shape(FakeReading(), psp_reading=psp,
                             psp_domain_config=DomainPSPConfig.for_domain("general"))
        # shaping computed but inert — no bounded-alternative text appended
        assert shape.psp_shaping is not None
        assert shape.psp_shaping.active is False
        assert "نحصر الخيارات" not in shape.meaning_instruction


# ═══════════════════════════════════════════════════════════════
#  TestSafetyIsolation — PSP shaping never touches S/H/θ
# ═══════════════════════════════════════════════════════════════

class TestSafetyIsolation:
    def test_psp_shaping_has_no_safety_fields(self, shaper, detector):
        r = reading_for(detector, "which one should I choose?", domain="healthcare")
        ps = shaper.shape_psp(r, DomainPSPConfig.for_domain("healthcare"))
        for forbidden in ("S", "H", "theta", "θ", "harm_score",
                          "decision", "blocked", "psp_mode"):
            assert not hasattr(ps, forbidden), \
                f"PSPShaping must not carry safety field {forbidden!r}"

    def test_firmness_unaffected_by_psp(self, shaper, detector):
        """PSP must not change the firmness (safety-side) value."""
        base = shaper.shape(FakeReading(softening_factor=0.5, harm_score=0.0))
        psp = reading_for(detector, "should I rent or buy?")
        withpsp = shaper.shape(FakeReading(softening_factor=0.5, harm_score=0.0),
                               psp_reading=psp,
                               psp_domain_config=DomainPSPConfig.for_domain("general"))
        assert base.firmness == withpsp.firmness
