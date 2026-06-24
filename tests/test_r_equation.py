#!/usr/bin/env python3
"""
R Equation tests for aatif_r_equation.py — أسلوب الرد
=====================================================

WHY THIS FILE EXISTS
────────────────────
R governs response STYLE — how formal vs casual عاطف should be.
S (safety) decides WHETHER to respond. R decides HOW.

This test suite ensures the style contract holds:
  • Each signal (T, V, G, D) computes correctly in isolation
  • The R equation combines signals correctly through sigmoid
  • R is always bounded in [0, 1]
  • Gate review lowers R for sensitive domains (never raises)
  • Style mapping follows the defined thresholds
  • Domain sensitivity ordering is preserved:
      healthcare ≤ education ≤ general ≤ creative
  • Edge cases: no time reading, no gap, unknown domain, empty text

THE TESTING STRATEGY
────────────────────
R equation is pure Python — no model, no embeddings.
We construct specific inputs and verify structured output.
Every test is deterministic and CI-friendly.

Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
License: BSL 1.1
"""

import sys
import os
import math

# Ensure engine directory is importable
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_TESTS_DIR)
_ENGINE_DIR = os.path.join(_ROOT_DIR, "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from aatif_r_equation import (
    REquation, RReading, sigmoid, r_to_style,
    DEFAULT_WEIGHTS, DOMAIN_D_SIGNALS, GATE_CEILINGS,
    DEFAULT_D_SIGNAL, STYLE_MAP,
)


# ═══════════════════════════════════════════════════════════
#  Fake TimeReading for testing
# ═══════════════════════════════════════════════════════════

class FakeTimeReading:
    """Mimics the TimeReading dataclass for controlled testing."""
    def __init__(self, period="صباح", is_late_night=False, fatigue_risk=False,
                 hour=10, interaction_gap_assessment="عادي"):
        self.period = period
        self.is_late_night = is_late_night
        self.fatigue_risk = fatigue_risk
        self.hour = hour
        self.interaction_gap_assessment = interaction_gap_assessment


# ═══════════════════════════════════════════════════════════
#  1. Sigmoid function tests
# ═══════════════════════════════════════════════════════════

def test_sigmoid_zero():
    """σ(0) = 0.5 exactly."""
    assert sigmoid(0) == 0.5


def test_sigmoid_positive():
    """σ(x) > 0.5 for positive x."""
    assert sigmoid(1.0) > 0.5
    assert sigmoid(5.0) > 0.5
    assert sigmoid(100.0) > 0.5


def test_sigmoid_negative():
    """σ(x) < 0.5 for negative x."""
    assert sigmoid(-1.0) < 0.5
    assert sigmoid(-5.0) < 0.5
    assert sigmoid(-100.0) < 0.5


def test_sigmoid_bounds():
    """σ(x) is always in [0, 1] (at float precision, extremes may touch 0 or 1)."""
    assert 0.0 <= sigmoid(-500) <= 1.0
    assert 0.0 <= sigmoid(500) <= 1.0
    assert 0 < sigmoid(0) < 1
    # Moderate inputs stay strictly in (0, 1)
    assert 0 < sigmoid(-10) < 1
    assert 0 < sigmoid(10) < 1


def test_sigmoid_symmetry():
    """σ(x) + σ(-x) = 1."""
    for x in [0.5, 1.0, 2.0, 5.0, 10.0]:
        assert abs(sigmoid(x) + sigmoid(-x) - 1.0) < 1e-10


# ═══════════════════════════════════════════════════════════
#  2. T signal (time) tests
# ═══════════════════════════════════════════════════════════

def test_t_signal_none():
    """No time reading → neutral T = 0.5."""
    r_eq = REquation()
    assert r_eq.compute_t_signal(None) == 0.5


def test_t_signal_morning_high():
    """Morning (صباح) → T ≈ 0.75 (highest energy)."""
    r_eq = REquation()
    tr = FakeTimeReading(period="صباح")
    t = r_eq.compute_t_signal(tr)
    assert t == 0.75


def test_t_signal_night_low():
    """Night (ليل) → T ≈ 0.30 (low energy)."""
    r_eq = REquation()
    tr = FakeTimeReading(period="ليل")
    t = r_eq.compute_t_signal(tr)
    assert t == 0.30


def test_t_signal_fajr_low():
    """Pre-dawn (فجر) → T ≈ 0.30 (unusual hour)."""
    r_eq = REquation()
    tr = FakeTimeReading(period="فجر")
    t = r_eq.compute_t_signal(tr)
    assert t == 0.30


def test_t_signal_late_night_override():
    """Late night (is_late_night=True) → T ≤ 0.25."""
    r_eq = REquation()
    tr = FakeTimeReading(period="ليل", is_late_night=True, hour=3)
    t = r_eq.compute_t_signal(tr)
    assert t <= 0.25


def test_t_signal_fatigue_lowers():
    """Fatigue risk → T ≤ 0.20."""
    r_eq = REquation()
    tr = FakeTimeReading(period="ليل", is_late_night=True, fatigue_risk=True, hour=3)
    t = r_eq.compute_t_signal(tr)
    assert t <= 0.20


def test_t_signal_morning_not_late_night():
    """Morning with no late night → T is not pulled down."""
    r_eq = REquation()
    tr = FakeTimeReading(period="صباح", is_late_night=False, fatigue_risk=False)
    t = r_eq.compute_t_signal(tr)
    assert t == 0.75


def test_t_signal_all_periods_in_range():
    """Every period produces T in [0, 1]."""
    r_eq = REquation()
    for period in ["فجر", "صباح", "ظهر", "عصر", "مساء", "ليل"]:
        tr = FakeTimeReading(period=period)
        t = r_eq.compute_t_signal(tr)
        assert 0.0 <= t <= 1.0, f"T={t} for period={period}"


# ═══════════════════════════════════════════════════════════
#  3. V signal (voice) tests
# ═══════════════════════════════════════════════════════════

def test_v_signal_empty():
    """Empty text → neutral V = 0.5."""
    r_eq = REquation()
    assert r_eq.compute_v_signal("") == 0.5
    assert r_eq.compute_v_signal("  ") == 0.5


def test_v_signal_arabic_dialect_higher():
    """Arabic dialect markers → higher V than plain English."""
    r_eq = REquation()
    v_dialect = r_eq.compute_v_signal("وش الحل يا صاحبي طيب")
    v_english = r_eq.compute_v_signal("What is the solution my friend")
    assert v_dialect > v_english


def test_v_signal_terse_lower():
    """Very short message (1-2 words) → lower V."""
    r_eq = REquation()
    v_terse = r_eq.compute_v_signal("ساعدني")
    v_normal = r_eq.compute_v_signal("ممكن تساعدني في موضوع مهم عندي")
    assert v_terse < v_normal


def test_v_signal_english_formal():
    """English text → slightly lower V (more formal)."""
    r_eq = REquation()
    v_en = r_eq.compute_v_signal("Please help me with this issue")
    # V should be around 0.45 (neutral minus English formality)
    assert 0.3 <= v_en <= 0.6


def test_v_signal_with_emoji():
    """Emoji presence → slight V boost."""
    r_eq = REquation()
    v_no_emoji = r_eq.compute_v_signal("أنا فرحان اليوم")
    v_emoji = r_eq.compute_v_signal("أنا فرحان اليوم 🎉")
    assert v_emoji >= v_no_emoji


def test_v_signal_exclamation():
    """Exclamation/question marks → slight V boost."""
    r_eq = REquation()
    v_plain = r_eq.compute_v_signal("أنا فرحان اليوم")
    v_exclaim = r_eq.compute_v_signal("أنا فرحان اليوم!")
    assert v_exclaim >= v_plain


def test_v_signal_always_in_range():
    """V is always in [0, 1]."""
    r_eq = REquation()
    texts = [
        "", "hi", "وش", "Hello world! 🎉🎉🎉!!!", "x" * 1000,
        "كيف حالك يا صديقي العزيز",
        "a",
    ]
    for text in texts:
        v = r_eq.compute_v_signal(text)
        assert 0.0 <= v <= 1.0, f"V={v} for text={text!r}"


# ═══════════════════════════════════════════════════════════
#  4. G signal (gap) tests
# ═══════════════════════════════════════════════════════════

def test_g_signal_none():
    """No gap data → moderate G = 0.45."""
    r_eq = REquation()
    assert r_eq.compute_g_signal(None) == 0.45


def test_g_signal_rapid_fire():
    """< 2 minutes → high G (match energy)."""
    r_eq = REquation()
    g = r_eq.compute_g_signal(60)  # 1 minute
    assert g == 0.75


def test_g_signal_active_conversation():
    """2 min to 1 hour → moderately high G."""
    r_eq = REquation()
    g = r_eq.compute_g_signal(30 * 60)  # 30 minutes
    assert g == 0.65


def test_g_signal_normal_gap():
    """1 to 4 hours → moderate G."""
    r_eq = REquation()
    g = r_eq.compute_g_signal(2 * 3600)  # 2 hours
    assert g == 0.55


def test_g_signal_drifting():
    """4 hours to 1 day → slightly careful G."""
    r_eq = REquation()
    g = r_eq.compute_g_signal(12 * 3600)  # 12 hours
    assert g == 0.45


def test_g_signal_days_away():
    """1 day to 1 week → gentle G."""
    r_eq = REquation()
    g = r_eq.compute_g_signal(3 * 24 * 3600)  # 3 days
    assert g == 0.30


def test_g_signal_weeks_away():
    """> 1 week → most gentle G."""
    r_eq = REquation()
    g = r_eq.compute_g_signal(14 * 24 * 3600)  # 2 weeks
    assert g == 0.20


def test_g_signal_negative():
    """Negative gap → treated as no data."""
    r_eq = REquation()
    g = r_eq.compute_g_signal(-100)
    assert g == 0.45


def test_g_signal_monotonic_decreasing():
    """G should generally decrease as gap increases."""
    r_eq = REquation()
    gaps = [30, 300, 3600, 14400, 86400, 604800]
    g_values = [r_eq.compute_g_signal(gap) for gap in gaps]
    # Not strictly monotonic at every step due to bucketing,
    # but overall trend should be decreasing
    assert g_values[0] >= g_values[-1]


# ═══════════════════════════════════════════════════════════
#  5. D signal (domain) tests
# ═══════════════════════════════════════════════════════════

def test_d_signal_healthcare():
    """Healthcare → D = 0.15 (most careful)."""
    r_eq = REquation()
    assert r_eq.compute_d_signal("healthcare") == 0.15


def test_d_signal_education():
    """Education → D = 0.25."""
    r_eq = REquation()
    assert r_eq.compute_d_signal("education") == 0.25


def test_d_signal_general():
    """General → D = 0.50."""
    r_eq = REquation()
    assert r_eq.compute_d_signal("general") == 0.50


def test_d_signal_creative():
    """Creative → D = 0.70 (most free)."""
    r_eq = REquation()
    assert r_eq.compute_d_signal("creative") == 0.70


def test_d_signal_unknown():
    """Unknown domain → default D = 0.50."""
    r_eq = REquation()
    assert r_eq.compute_d_signal("unknown_domain") == DEFAULT_D_SIGNAL
    assert r_eq.compute_d_signal("xyz") == DEFAULT_D_SIGNAL


def test_d_signal_case_insensitive():
    """Domain matching is case-insensitive."""
    r_eq = REquation()
    assert r_eq.compute_d_signal("Healthcare") == 0.15
    assert r_eq.compute_d_signal("CREATIVE") == 0.70


def test_d_signal_ordering():
    """Domain sensitivity ordering: healthcare ≤ education ≤ general ≤ tech ≤ ecommerce ≤ creative."""
    r_eq = REquation()
    d_health = r_eq.compute_d_signal("healthcare")
    d_edu = r_eq.compute_d_signal("education")
    d_gen = r_eq.compute_d_signal("general")
    d_tech = r_eq.compute_d_signal("tech")
    d_ecom = r_eq.compute_d_signal("ecommerce")
    d_creative = r_eq.compute_d_signal("creative")

    assert d_health <= d_edu <= d_gen <= d_tech <= d_ecom <= d_creative


def test_d_signal_empty_domain():
    """Empty domain string → treated as general."""
    r_eq = REquation()
    assert r_eq.compute_d_signal("") == DOMAIN_D_SIGNALS.get("", DEFAULT_D_SIGNAL)


# ═══════════════════════════════════════════════════════════
#  6. R equation end-to-end tests
# ═══════════════════════════════════════════════════════════

def test_r_always_in_range():
    """R is always in [0, 1] regardless of inputs."""
    r_eq = REquation()
    test_cases = [
        ("hi", "general", None, None),
        ("وش الحل يا صاحبي", "healthcare", None, 60),
        ("", "creative", None, 604800),
        ("x" * 500, "education", None, 0),
        ("Help me!", "tech", None, -100),
    ]
    for text, domain, tr, gap in test_cases:
        reading = r_eq.compute(text, domain, tr, gap)
        assert 0.0 <= reading.r_score <= 1.0, (
            f"R={reading.r_score} for text={text!r}, domain={domain}"
        )
        assert 0.0 <= reading.original_r <= 1.0


def test_r_creative_higher_than_healthcare():
    """Same text/time/gap: creative domain → higher R than healthcare."""
    r_eq = REquation()
    text = "ممكن تساعدني في موضوع"
    r_creative = r_eq.compute(text, "creative", gap_seconds=3600)
    r_health = r_eq.compute(text, "healthcare", gap_seconds=3600)
    assert r_creative.r_score >= r_health.r_score


def test_r_domain_ordering_end_to_end():
    """End-to-end: healthcare style ≤ education ≤ general ≤ creative."""
    r_eq = REquation()
    text = "ممكن تساعدني في موضوع"
    gap = 3600

    r_health = r_eq.compute(text, "healthcare", gap_seconds=gap)
    r_edu = r_eq.compute(text, "education", gap_seconds=gap)
    r_gen = r_eq.compute(text, "general", gap_seconds=gap)
    r_creative = r_eq.compute(text, "creative", gap_seconds=gap)

    assert r_health.r_score <= r_edu.r_score <= r_gen.r_score <= r_creative.r_score


def test_r_reading_has_all_fields():
    """RReading contains all required fields."""
    r_eq = REquation()
    reading = r_eq.compute("test", "general")
    assert hasattr(reading, 'r_score')
    assert hasattr(reading, 't_signal')
    assert hasattr(reading, 'v_signal')
    assert hasattr(reading, 'g_signal')
    assert hasattr(reading, 'd_signal')
    assert hasattr(reading, 'style_recommendation')
    assert hasattr(reading, 'gate_flags')
    assert hasattr(reading, 'gate_adjusted')
    assert hasattr(reading, 'original_r')


def test_r_signals_in_range():
    """All individual signals are in [0, 1]."""
    r_eq = REquation()
    reading = r_eq.compute("وش الحل", "general", gap_seconds=120)
    assert 0.0 <= reading.t_signal <= 1.0
    assert 0.0 <= reading.v_signal <= 1.0
    assert 0.0 <= reading.g_signal <= 1.0
    assert 0.0 <= reading.d_signal <= 1.0


# ═══════════════════════════════════════════════════════════
#  7. Gate review tests
# ═══════════════════════════════════════════════════════════

def test_gate_healthcare_lowers_r():
    """Gate lowers R > 0.5 for healthcare domain."""
    r_eq = REquation()
    adjusted, flags = r_eq.gate_review(0.7, "healthcare")
    assert adjusted == 0.5
    assert len(flags) > 0
    assert "healthcare" in flags[0].lower()


def test_gate_education_lowers_r():
    """Gate lowers R > 0.6 for education domain."""
    r_eq = REquation()
    adjusted, flags = r_eq.gate_review(0.8, "education")
    assert adjusted == 0.6
    assert len(flags) > 0


def test_gate_healthcare_no_change_below_ceiling():
    """Gate does NOT change R ≤ 0.5 for healthcare."""
    r_eq = REquation()
    adjusted, flags = r_eq.gate_review(0.4, "healthcare")
    assert adjusted == 0.4
    assert len(flags) == 0


def test_gate_general_no_ceiling():
    """General domain has no gate ceiling."""
    r_eq = REquation()
    adjusted, flags = r_eq.gate_review(0.9, "general")
    assert adjusted == 0.9
    assert len(flags) == 0


def test_gate_creative_no_ceiling():
    """Creative domain has no gate ceiling."""
    r_eq = REquation()
    adjusted, flags = r_eq.gate_review(0.95, "creative")
    assert adjusted == 0.95
    assert len(flags) == 0


def test_gate_never_raises_r():
    """Gate can only LOWER R, never raise it."""
    r_eq = REquation()
    for domain in ["healthcare", "education", "general", "creative", "tech"]:
        for r in [0.1, 0.3, 0.5, 0.7, 0.9]:
            adjusted, _ = r_eq.gate_review(r, domain)
            assert adjusted <= r, (
                f"Gate raised R from {r} to {adjusted} for domain={domain}"
            )


def test_gate_integrated_in_compute():
    """Gate adjustment is reflected in compute() output."""
    r_eq = REquation()
    # Use creative text in healthcare to trigger high R that gets gated
    reading = r_eq.compute(
        text="ابي اكتب قصيدة عن الحب يعني! 🎶",
        domain="healthcare",
        gap_seconds=30,
    )
    # If gate adjusted, original_r should be higher than r_score
    if reading.gate_adjusted:
        assert reading.original_r > reading.r_score
        assert len(reading.gate_flags) > 0


# ═══════════════════════════════════════════════════════════
#  8. Style mapping tests
# ═══════════════════════════════════════════════════════════

def test_style_formal():
    """R ≤ 0.3 → "formal"."""
    assert r_to_style(0.0) == "formal"
    assert r_to_style(0.1) == "formal"
    assert r_to_style(0.3) == "formal"


def test_style_balanced():
    """0.3 < R ≤ 0.5 → "balanced"."""
    assert r_to_style(0.31) == "balanced"
    assert r_to_style(0.4) == "balanced"
    assert r_to_style(0.5) == "balanced"


def test_style_warm():
    """0.5 < R ≤ 0.7 → "warm"."""
    assert r_to_style(0.51) == "warm"
    assert r_to_style(0.6) == "warm"
    assert r_to_style(0.7) == "warm"


def test_style_casual():
    """R > 0.7 → "casual"."""
    assert r_to_style(0.71) == "casual"
    assert r_to_style(0.9) == "casual"
    assert r_to_style(1.0) == "casual"


def test_style_boundary_0_3():
    """Exact boundary: R=0.3 is "formal", R=0.300001 is "balanced"."""
    assert r_to_style(0.3) == "formal"
    assert r_to_style(0.300001) == "balanced"


def test_style_boundary_0_5():
    """Exact boundary: R=0.5 is "balanced", R=0.500001 is "warm"."""
    assert r_to_style(0.5) == "balanced"
    assert r_to_style(0.500001) == "warm"


def test_style_boundary_0_7():
    """Exact boundary: R=0.7 is "warm", R=0.700001 is "casual"."""
    assert r_to_style(0.7) == "warm"
    assert r_to_style(0.700001) == "casual"


# ═══════════════════════════════════════════════════════════
#  9. Custom weights tests
# ═══════════════════════════════════════════════════════════

def test_custom_weights():
    """Custom weights are applied correctly."""
    r_eq = REquation(weights={"w3": 0.0, "w4": 0.0, "w5": 0.0, "w6": 10.0})
    # With only domain weight, healthcare (D=0.15) should give lower R
    # than creative (D=0.70)
    r_health = r_eq.compute("test", "healthcare")
    r_creative = r_eq.compute("test", "creative")
    assert r_health.r_score < r_creative.r_score


def test_zero_weights_gives_sigmoid_zero():
    """All weights zero AND bias zero → R = σ(0) = 0.5."""
    r_eq = REquation(weights={"w3": 0.0, "w4": 0.0, "w5": 0.0, "w6": 0.0, "bias": 0.0})
    reading = r_eq.compute("anything", "general")
    assert abs(reading.r_score - 0.5) < 0.001


def test_partial_custom_weights():
    """Partial weights: unspecified keys fall back to default."""
    r_eq = REquation(weights={"w6": 5.0})
    assert r_eq.w3 == DEFAULT_WEIGHTS["w3"]
    assert r_eq.w4 == DEFAULT_WEIGHTS["w4"]
    assert r_eq.w5 == DEFAULT_WEIGHTS["w5"]
    assert r_eq.w6 == 5.0


# ═══════════════════════════════════════════════════════════
#  10. Edge case tests
# ═══════════════════════════════════════════════════════════

def test_no_time_no_gap():
    """No time reading and no gap → R still computes."""
    r_eq = REquation()
    reading = r_eq.compute("مرحبا", "general")
    assert 0.0 <= reading.r_score <= 1.0
    assert reading.t_signal == 0.5   # neutral time
    assert reading.g_signal == 0.45  # moderate gap


def test_empty_text():
    """Empty text → R still computes with neutral V."""
    r_eq = REquation()
    reading = r_eq.compute("", "general")
    assert 0.0 <= reading.r_score <= 1.0
    assert reading.v_signal == 0.5


def test_very_long_text():
    """Very long text → R computes without error."""
    r_eq = REquation()
    long_text = "كلمة " * 500
    reading = r_eq.compute(long_text, "general")
    assert 0.0 <= reading.r_score <= 1.0


def test_unknown_domain_handled():
    """Unknown domain gets default D, no crash."""
    r_eq = REquation()
    reading = r_eq.compute("test", "unknown_domain_xyz")
    assert reading.d_signal == DEFAULT_D_SIGNAL
    assert 0.0 <= reading.r_score <= 1.0


def test_with_time_reading():
    """Time reading integrates correctly into R computation."""
    r_eq = REquation()
    tr_morning = FakeTimeReading(period="صباح", is_late_night=False)
    tr_night = FakeTimeReading(period="ليل", is_late_night=True, hour=3)

    r_morning = r_eq.compute("مرحبا", "general", time_reading=tr_morning)
    r_night = r_eq.compute("مرحبا", "general", time_reading=tr_night)

    # Morning should produce higher R (lighter style) than late night
    assert r_morning.r_score >= r_night.r_score
    assert r_morning.t_signal > r_night.t_signal


def test_style_recommendation_matches_score():
    """style_recommendation is consistent with r_score."""
    r_eq = REquation()
    for domain in ["healthcare", "general", "creative"]:
        for gap in [30, 3600, 604800]:
            reading = r_eq.compute("ممكن تساعدني", domain, gap_seconds=gap)
            expected_style = r_to_style(reading.r_score)
            assert reading.style_recommendation == expected_style, (
                f"Score {reading.r_score} → expected {expected_style}, "
                f"got {reading.style_recommendation}"
            )


def test_gate_adjusted_flag_consistency():
    """gate_adjusted=True ↔ original_r != r_score."""
    r_eq = REquation()
    for domain in ["healthcare", "education", "general", "creative"]:
        reading = r_eq.compute("ابي اكتب قصيدة يعني", domain, gap_seconds=30)
        if reading.gate_adjusted:
            assert reading.original_r != reading.r_score
        else:
            assert reading.original_r == reading.r_score


def test_r_equation_is_monotonic_in_domain():
    """Holding other inputs constant, higher D → higher R."""
    r_eq = REquation()
    text = "ممكن تساعدني"
    gap = 3600

    readings = {}
    for domain in DOMAIN_D_SIGNALS:
        # Use original_r (before gate) for monotonicity test
        reading = r_eq.compute(text, domain, gap_seconds=gap)
        readings[domain] = reading.original_r

    # Sorted by D signal value
    sorted_domains = sorted(DOMAIN_D_SIGNALS.keys(),
                            key=lambda d: DOMAIN_D_SIGNALS[d])
    for i in range(len(sorted_domains) - 1):
        d1 = sorted_domains[i]
        d2 = sorted_domains[i + 1]
        assert readings[d1] <= readings[d2], (
            f"original_r({d1})={readings[d1]} > original_r({d2})={readings[d2]}"
        )
