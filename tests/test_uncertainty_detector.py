"""
Test suite for AATIF Uncertainty/Calibration Detector

Tests the UncertaintyDetector, UncertaintyReading, UncertaintyDisclosure,
and all component computations.

Architecture under test (B-prime Safety-Observational):
  UncertaintyDetector  →  observational (computes calibration_confidence)
  GovernanceEquation   →  judicial (uses calibration_confidence in gate)

Design consensus: Claude x ChatGPT, 2026-06-30
"""

import pytest

import aatif_uncertainty_detector as uc_mod
from aatif_uncertainty_detector import (
    UncertaintyDetector,
    UncertaintyReading,
    UncertaintyDisclosure,
    UNCERTAINTY_ENABLED,
    UNCERTAINTY_GATE_ENABLED,
    UNCERTAINTY_OUTPUT_CHECK_ENABLED,
    UNCERTAINTY_TRACE_ENABLED,
    UNCERTAINTY_MONITOR_ONLY,
    CONFIDENCE_THRESHOLD_BY_DOMAIN,
    CONFIDENCE_STRING_MAP,
    ABSTENTION_THRESHOLD_BY_DOMAIN,
    ABSTENTION_BASELINE,
    ARABIC_CONFIDENCE_PENALTIES,
    COVERAGE_MIN_SIM,
    COVERAGE_RANGE,
    W_H, W_I, W_E, W_COV, W_AGR,
    H_FLOOR_CAP_RULES,
    TRACE_LAMBDA,
)


# ═══════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def detector():
    """Fresh UncertaintyDetector instance."""
    return UncertaintyDetector()


@pytest.fixture
def enable_uncertainty():
    """Enable uncertainty detection for test, restore after."""
    old_enabled = uc_mod.UNCERTAINTY_ENABLED
    old_gate = uc_mod.UNCERTAINTY_GATE_ENABLED
    uc_mod.UNCERTAINTY_ENABLED = True
    uc_mod.UNCERTAINTY_GATE_ENABLED = True
    yield
    uc_mod.UNCERTAINTY_ENABLED = old_enabled
    uc_mod.UNCERTAINTY_GATE_ENABLED = old_gate


@pytest.fixture
def enable_trace():
    """Enable uncertainty trace for test, restore after."""
    old = uc_mod.UNCERTAINTY_TRACE_ENABLED
    uc_mod.UNCERTAINTY_TRACE_ENABLED = True
    yield
    uc_mod.UNCERTAINTY_TRACE_ENABLED = old


def _high_confidence_result():
    """Simulated engine result with high confidence."""
    return {
        "H": 0.1, "I": 0.9, "E": 0.3,
        "scorer_confidence": {"H": "high", "I": "high", "E": "high"},
        "scorer_max_sim": {"H": 0.55, "I": 0.60, "E": 0.50},
        "unknown_territory": False,
    }


def _low_confidence_result():
    """Simulated engine result with low confidence."""
    return {
        "H": 0.5, "I": 0.7, "E": 0.4,
        "scorer_confidence": {"H": "low", "I": "medium", "E": "low"},
        "scorer_max_sim": {"H": 0.15, "I": 0.25, "E": 0.12},
        "unknown_territory": True,
    }


def _mixed_confidence_result():
    """Simulated result with mixed confidence and H-I divergence."""
    return {
        "H": 0.6, "I": 0.8, "E": 0.5,
        "scorer_confidence": {"H": "medium", "I": "high", "E": "medium"},
        "scorer_max_sim": {"H": 0.40, "I": 0.55, "E": 0.35},
        "unknown_territory": False,
    }


# ═══════════════════════════════════════════════════════════════
#  TestFeatureFlags — disabled by default
# ═══════════════════════════════════════════════════════════════

class TestFeatureFlags:
    """Verify all feature flags default to OFF."""

    def test_uncertainty_disabled_by_default(self):
        assert not UNCERTAINTY_ENABLED, "UNCERTAINTY_ENABLED must default to False"

    def test_gate_disabled_by_default(self):
        assert not UNCERTAINTY_GATE_ENABLED, "UNCERTAINTY_GATE_ENABLED must default to False"

    def test_output_check_disabled_by_default(self):
        assert not UNCERTAINTY_OUTPUT_CHECK_ENABLED, "UNCERTAINTY_OUTPUT_CHECK_ENABLED must default to False"

    def test_trace_disabled_by_default(self):
        assert not UNCERTAINTY_TRACE_ENABLED, "UNCERTAINTY_TRACE_ENABLED must default to False"

    def test_monitor_only_default_true(self):
        assert UNCERTAINTY_MONITOR_ONLY, "UNCERTAINTY_MONITOR_ONLY must default to True"

    def test_disabled_returns_high_confidence(self, detector):
        """When disabled, detector returns calibration_confidence=1.0 (pass-through)."""
        result = _high_confidence_result()
        reading = detector.detect(result, domain="healthcare")
        assert reading.calibration_confidence == 1.0
        assert not reading.should_gate
        assert not reading.should_abstain
        assert not reading.enabled


# ═══════════════════════════════════════════════════════════════
#  TestConfidenceConversion — Phase 1 string→numeric
# ═══════════════════════════════════════════════════════════════

class TestConfidenceConversion:
    """Verify string-to-numeric confidence mapping."""

    def test_high(self):
        assert UncertaintyDetector._convert_confidence("high") == 0.9

    def test_medium(self):
        assert UncertaintyDetector._convert_confidence("medium") == 0.6

    def test_low(self):
        assert UncertaintyDetector._convert_confidence("low") == 0.3

    def test_numeric_passthrough(self):
        assert UncertaintyDetector._convert_confidence(0.75) == 0.75

    def test_unknown_string_returns_medium(self):
        """Unknown strings get medium confidence (0.6) as safe default."""
        assert UncertaintyDetector._convert_confidence("unknown") == 0.6


# ═══════════════════════════════════════════════════════════════
#  TestCoverage — from max_sim values
# ═══════════════════════════════════════════════════════════════

class TestCoverage:
    """Verify coverage computation from max_sim."""

    def test_full_coverage(self, detector):
        """max_sim >= 0.60 → coverage = 1.0"""
        result = {"scorer_max_sim": {"H": 0.60, "I": 0.60, "E": 0.60}}
        overall, h, i, e = detector._compute_coverage(result)
        assert h == 1.0
        assert i == 1.0
        assert e == 1.0
        assert overall == 1.0

    def test_zero_coverage(self, detector):
        """max_sim <= 0.10 → coverage = 0.0"""
        result = {"scorer_max_sim": {"H": 0.05, "I": 0.10, "E": 0.08}}
        overall, h, i, e = detector._compute_coverage(result)
        assert h == 0.0
        assert i == 0.0
        assert e == 0.0
        assert overall == 0.0

    def test_partial_coverage(self, detector):
        """max_sim = 0.35 → coverage = (0.35-0.10)/0.50 = 0.50"""
        result = {"scorer_max_sim": {"H": 0.35, "I": 0.35, "E": 0.35}}
        overall, h, i, e = detector._compute_coverage(result)
        assert h == 0.5
        assert i == 0.5
        assert e == 0.5

    def test_missing_max_sim_is_zero(self, detector):
        """When max_sim is None (missing), coverage is 0.0"""
        result = {"scorer_max_sim": {"H": None, "I": 0.50, "E": None}}
        overall, h, i, e = detector._compute_coverage(result)
        assert h == 0.0
        assert e == 0.0
        assert i > 0.0

    def test_no_scorer_max_sim(self, detector):
        """When scorer_max_sim is missing entirely, all coverage is 0.0"""
        result = {}
        overall, h, i, e = detector._compute_coverage(result)
        assert overall == 0.0

    def test_h_weighted_more(self, detector):
        """H coverage is weighted 0.5 (most important for safety)."""
        # Only H has coverage
        result = {"scorer_max_sim": {"H": 0.60, "I": 0.10, "E": 0.10}}
        overall, h, i, e = detector._compute_coverage(result)
        assert h == 1.0
        assert i == 0.0
        assert e == 0.0
        # overall = 0.5*1.0 + 0.3*0.0 + 0.2*0.0 = 0.5
        assert overall == 0.5


# ═══════════════════════════════════════════════════════════════
#  TestAmbiguity — H-I divergence and signals
# ═══════════════════════════════════════════════════════════════

class TestAmbiguity:
    """Verify ambiguity / H-I divergence computation."""

    def test_no_ambiguity_clear_benign(self, detector):
        """Low H + high I = clear benign → no ambiguity."""
        result = {
            "H": 0.1, "I": 0.9, "E": 0.3,
            "scorer_confidence": {"H": "high", "I": "high", "E": "high"},
            "unknown_territory": False,
        }
        amb, n = detector._compute_ambiguity(result)
        assert amb == 0.0
        assert n == 0

    def test_ambiguity_h_i_divergence(self, detector):
        """Large H-I gap (>0.3) with non-trivial H → ambiguity signal."""
        result = {
            "H": 0.7, "I": 0.2, "E": 0.5,
            "scorer_confidence": {"H": "high", "I": "high", "E": "high"},
            "unknown_territory": False,
        }
        amb, n = detector._compute_ambiguity(result)
        assert amb > 0.0
        assert n >= 1

    def test_ambiguity_low_intent_confidence(self, detector):
        """Low intent confidence → ambiguity signal."""
        result = {
            "H": 0.2, "I": 0.5, "E": 0.4,
            "scorer_confidence": {"H": "high", "I": "low", "E": "high"},
            "unknown_territory": False,
        }
        amb, n = detector._compute_ambiguity(result)
        assert amb > 0.0
        assert n >= 1

    def test_ambiguity_unknown_territory(self, detector):
        """Unknown territory flag → ambiguity signal."""
        result = {
            "H": 0.1, "I": 0.9, "E": 0.3,
            "scorer_confidence": {"H": "high", "I": "high", "E": "high"},
            "unknown_territory": True,
        }
        amb, n = detector._compute_ambiguity(result)
        assert amb > 0.0
        assert n >= 1

    def test_ambiguity_capped_at_1(self, detector):
        """Ambiguity score never exceeds 1.0."""
        result = {
            "H": 0.9, "I": 0.9, "E": 0.5,
            "scorer_confidence": {"H": "low", "I": "low", "E": "low"},
            "unknown_territory": True,
        }
        amb, n = detector._compute_ambiguity(result)
        assert amb <= 1.0


# ═══════════════════════════════════════════════════════════════
#  TestAgreement — inter-scorer coherence
# ═══════════════════════════════════════════════════════════════

class TestAgreement:
    """Verify inter-scorer agreement computation."""

    def test_coherent_benign(self, detector):
        """Low H + high I = coherent → high agreement."""
        result = {"H": 0.1, "I": 0.9, "E": 0.5}
        agr = detector._compute_agreement(result)
        assert agr > 0.7

    def test_coherent_harmful(self, detector):
        """High H + low I = coherent → high agreement."""
        result = {"H": 0.9, "I": 0.1, "E": 0.5}
        agr = detector._compute_agreement(result)
        assert agr > 0.7

    def test_incoherent_mixed(self, detector):
        """High H + high I = incoherent → lower agreement."""
        result = {"H": 0.8, "I": 0.8, "E": 0.5}
        agr = detector._compute_agreement(result)
        # Should be lower than coherent cases
        agr_benign = detector._compute_agreement({"H": 0.1, "I": 0.9, "E": 0.5})
        assert agr < agr_benign

    def test_agreement_in_range(self, detector):
        """Agreement is always in [0, 1]."""
        for h in [0.0, 0.3, 0.5, 0.7, 1.0]:
            for i in [0.0, 0.3, 0.5, 0.7, 1.0]:
                for e in [0.0, 0.5, 1.0]:
                    agr = detector._compute_agreement({"H": h, "I": i, "E": e})
                    assert 0.0 <= agr <= 1.0, f"Agreement out of range for H={h} I={i} E={e}: {agr}"


# ═══════════════════════════════════════════════════════════════
#  TestAggregation — weighted mean + H-floor cap
# ═══════════════════════════════════════════════════════════════

class TestAggregation:
    """Verify aggregation with H-floor cap."""

    def test_weights_sum_to_1(self):
        """Aggregation weights must sum to 1.0."""
        total = W_H + W_I + W_E + W_COV + W_AGR
        assert abs(total - 1.0) < 1e-6, f"Weights sum to {total}, expected 1.0"

    def test_all_high(self, detector):
        """All components at 0.9 → high calibration_confidence."""
        cc = detector._aggregate(0.9, 0.9, 0.9, 0.9, 0.9)
        assert cc == 0.9

    def test_all_low(self, detector):
        """All components at 0.3 → low calibration_confidence."""
        cc = detector._aggregate(0.3, 0.3, 0.3, 0.3, 0.3)
        assert cc == 0.3

    def test_h_floor_cap_strict(self, detector):
        """When h_conf < 0.35, overall is capped at 0.45."""
        # Even with all other components at 0.9
        cc = detector._aggregate(0.30, 0.9, 0.9, 0.9, 0.9)
        assert cc <= 0.45

    def test_h_floor_cap_moderate(self, detector):
        """When h_conf < 0.50, overall is capped at 0.60."""
        cc = detector._aggregate(0.45, 0.9, 0.9, 0.9, 0.9)
        assert cc <= 0.60

    def test_h_floor_cap_not_applied_when_high(self, detector):
        """When h_conf >= 0.50, no cap is applied."""
        cc = detector._aggregate(0.9, 0.9, 0.9, 0.9, 0.9)
        assert cc == 0.9  # no cap

    def test_in_range(self, detector):
        """Aggregated value is always in [0, 1]."""
        for h in [0.0, 0.3, 0.6, 0.9]:
            for rest in [0.0, 0.5, 1.0]:
                cc = detector._aggregate(h, rest, rest, rest, rest)
                assert 0.0 <= cc <= 1.0


# ═══════════════════════════════════════════════════════════════
#  TestDomainThresholds — ξ(d) lookup
# ═══════════════════════════════════════════════════════════════

class TestDomainThresholds:
    """Verify domain threshold lookup."""

    def test_healthcare(self):
        assert UncertaintyDetector._get_xi("healthcare") == 0.80

    def test_legal(self):
        assert UncertaintyDetector._get_xi("legal") == 0.75

    def test_finance(self):
        assert UncertaintyDetector._get_xi("finance") == 0.75

    def test_education(self):
        assert UncertaintyDetector._get_xi("education") == 0.65

    def test_general(self):
        assert UncertaintyDetector._get_xi("general") == 0.55

    def test_creative(self):
        assert UncertaintyDetector._get_xi("creative") == 0.40

    def test_unknown_domain_falls_back_to_general(self):
        """Unknown domains get the general threshold (0.55)."""
        assert UncertaintyDetector._get_xi("unknown_domain") == 0.55

    def test_healthcare_stricter_than_general(self):
        """Healthcare requires higher confidence than general."""
        assert CONFIDENCE_THRESHOLD_BY_DOMAIN["healthcare"] > CONFIDENCE_THRESHOLD_BY_DOMAIN["general"]

    def test_creative_most_lenient(self):
        """Creative has the lowest confidence threshold."""
        creative = CONFIDENCE_THRESHOLD_BY_DOMAIN["creative"]
        for domain, threshold in CONFIDENCE_THRESHOLD_BY_DOMAIN.items():
            assert creative <= threshold, f"creative ({creative}) > {domain} ({threshold})"


# ═══════════════════════════════════════════════════════════════
#  TestArabicPenalties — confidence reduction only
# ═══════════════════════════════════════════════════════════════

class TestArabicPenalties:
    """Verify Arabic-specific confidence penalties."""

    def test_arabizi_penalty(self, detector, enable_uncertainty):
        """Arabizi detected → -0.10 confidence penalty."""
        result = _high_confidence_result()
        # Without penalty
        r1 = detector.detect(result, domain="general")
        # With penalty
        r2 = detector.detect(result, domain="general",
                             arabic_signals={"arabizi_detected": True})
        assert r2.calibration_confidence < r1.calibration_confidence
        assert r2.total_arabic_penalty == -0.10

    def test_dialect_switch_penalty(self, detector, enable_uncertainty):
        """Dialect switch → -0.08 confidence penalty."""
        result = _high_confidence_result()
        reading = detector.detect(result, domain="general",
                                  arabic_signals={"dialect_switch": True})
        assert reading.total_arabic_penalty == -0.08

    def test_multiple_penalties_stack(self, detector, enable_uncertainty):
        """Multiple Arabic signals stack their penalties."""
        result = _high_confidence_result()
        reading = detector.detect(result, domain="general",
                                  arabic_signals={
                                      "arabizi_detected": True,
                                      "dialect_switch": True,
                                  })
        expected = -0.10 + -0.08
        assert abs(reading.total_arabic_penalty - expected) < 1e-6

    def test_inactive_signals_no_penalty(self, detector, enable_uncertainty):
        """Inactive signals (False) apply no penalty."""
        result = _high_confidence_result()
        reading = detector.detect(result, domain="general",
                                  arabic_signals={
                                      "arabizi_detected": False,
                                      "dialect_switch": False,
                                  })
        assert reading.total_arabic_penalty == 0.0

    def test_penalties_never_negative_confidence(self, detector, enable_uncertainty):
        """Penalties cannot make calibration_confidence negative."""
        result = _low_confidence_result()
        reading = detector.detect(result, domain="general",
                                  arabic_signals={
                                      "arabizi_detected": True,
                                      "dialect_switch": True,
                                      "tashkeel_ambiguous": True,
                                      "cultural_indirection": True,
                                  })
        assert reading.calibration_confidence >= 0.0

    def test_penalty_values_match_consensus(self):
        """Penalty values match the design consensus document."""
        assert ARABIC_CONFIDENCE_PENALTIES["arabizi_detected"] == -0.10
        assert ARABIC_CONFIDENCE_PENALTIES["dialect_switch"] == -0.08
        assert ARABIC_CONFIDENCE_PENALTIES["tashkeel_ambiguous"] == -0.05
        assert ARABIC_CONFIDENCE_PENALTIES["cultural_indirection"] == -0.08


# ═══════════════════════════════════════════════════════════════
#  TestDetection — main detect() method
# ═══════════════════════════════════════════════════════════════

class TestDetection:
    """Verify full detection pipeline."""

    def test_high_confidence_no_gate(self, detector, enable_uncertainty):
        """High confidence result → should_gate=False."""
        result = _high_confidence_result()
        reading = detector.detect(result, domain="general")
        assert not reading.should_gate
        assert not reading.should_abstain
        assert reading.calibration_confidence > 0.5

    def test_low_confidence_gates(self, detector, enable_uncertainty):
        """Low confidence result in healthcare → should_gate=True."""
        result = _low_confidence_result()
        reading = detector.detect(result, domain="healthcare")
        # Low scorer confidence + low coverage + unknown territory
        # should produce low calibration_confidence
        assert reading.calibration_confidence < 0.80  # below healthcare xi
        assert reading.should_gate

    def test_domain_affects_gating(self, detector, enable_uncertainty):
        """Same result can gate in healthcare but not in creative."""
        result = _mixed_confidence_result()
        r_health = detector.detect(result, domain="healthcare")
        r_creative = detector.detect(result, domain="creative")
        # Healthcare xi=0.80 (stricter), creative xi=0.40 (lenient)
        assert r_health.xi_threshold > r_creative.xi_threshold

    def test_evidence_populated(self, detector, enable_uncertainty):
        """Evidence list is populated with diagnostic information."""
        result = _high_confidence_result()
        reading = detector.detect(result, domain="general")
        assert len(reading.evidence) > 0
        # Should contain scorer_conf entry
        assert any("scorer_conf" in e for e in reading.evidence)

    def test_reading_components_populated(self, detector, enable_uncertainty):
        """All component values are populated in the reading."""
        result = _high_confidence_result()
        reading = detector.detect(result, domain="general")
        assert reading.h_confidence == 0.9
        assert reading.i_confidence == 0.9
        assert reading.e_confidence == 0.9
        assert reading.coverage >= 0.0
        assert reading.agreement >= 0.0


# ═══════════════════════════════════════════════════════════════
#  TestAbstention — "والله أعلم"
# ═══════════════════════════════════════════════════════════════

class TestAbstention:
    """Verify abstention threshold behavior."""

    def test_very_low_confidence_abstains(self, detector, enable_uncertainty):
        """Very low confidence → should_abstain=True."""
        # Fabricate an extremely low confidence result:
        # All scorer confidences low (0.3), zero coverage (max_sim < 0.10),
        # high H + high I for low agreement (incoherent), plus Arabic penalties.
        result = {
            "H": 0.8, "I": 0.8, "E": 0.5,
            "scorer_confidence": {"H": "low", "I": "low", "E": "low"},
            "scorer_max_sim": {"H": 0.05, "I": 0.05, "E": 0.05},
            "unknown_territory": True,
        }
        reading = detector.detect(
            result, domain="general",
            arabic_signals={
                "arabizi_detected": True,
                "cultural_indirection": True,
            },
        )
        assert reading.calibration_confidence < ABSTENTION_BASELINE, (
            f"Expected cc < {ABSTENTION_BASELINE}, got {reading.calibration_confidence}"
        )
        assert reading.should_abstain

    def test_high_confidence_no_abstention(self, detector, enable_uncertainty):
        """High confidence → should_abstain=False."""
        result = _high_confidence_result()
        reading = detector.detect(result, domain="general")
        assert not reading.should_abstain

    def test_healthcare_abstention_threshold(self):
        """Healthcare abstention threshold is 0.30 (stricter)."""
        assert ABSTENTION_THRESHOLD_BY_DOMAIN["healthcare"] == 0.30

    def test_creative_abstention_threshold(self):
        """Creative abstention threshold is 0.15 (most lenient)."""
        assert ABSTENTION_THRESHOLD_BY_DOMAIN["creative"] == 0.15

    def test_general_abstention_threshold(self):
        """General abstention threshold is 0.20 (baseline)."""
        assert ABSTENTION_THRESHOLD_BY_DOMAIN["general"] == ABSTENTION_BASELINE


# ═══════════════════════════════════════════════════════════════
#  TestMultiTurnTrace — decay tracking
# ═══════════════════════════════════════════════════════════════

class TestMultiTurnTrace:
    """Verify multi-turn uncertainty trace."""

    def test_trace_when_enabled(self, detector, enable_uncertainty, enable_trace):
        """When trace is enabled, uncertainty_trace is computed."""
        result = _low_confidence_result()
        reading = detector.detect(result, domain="general")
        assert reading.uncertainty_trace > 0.0

    def test_trace_accumulates(self, detector, enable_uncertainty, enable_trace):
        """Consecutive low-confidence detections accumulate trace."""
        result = _low_confidence_result()
        r1 = detector.detect(result, domain="general")
        r2 = detector.detect(result, domain="general")
        # Second reading should have higher trace (current + lambda * previous)
        assert r2.uncertainty_trace > r1.uncertainty_trace

    def test_trace_zero_when_disabled(self, detector, enable_uncertainty):
        """When trace is disabled, uncertainty_trace is 0.0."""
        result = _low_confidence_result()
        reading = detector.detect(result, domain="general")
        assert reading.uncertainty_trace == 0.0


# ═══════════════════════════════════════════════════════════════
#  TestDisclosure — UncertaintyDisclosure generation
# ═══════════════════════════════════════════════════════════════

class TestDisclosure:
    """Verify disclosure generation from readings."""

    def test_no_disclosure_when_confident(self):
        """High confidence → disclosure_level='none'."""
        reading = UncertaintyReading(
            calibration_confidence=0.90,
            xi_threshold=0.55,
        )
        disc = UncertaintyDetector.build_disclosure(reading, {"H": 0.1, "I": 0.9})
        assert disc.disclosure_level == "none"

    def test_mild_disclosure(self):
        """Confidence slightly below xi → mild disclosure."""
        # xi=0.55, cc=0.50 → 0.50 >= 0.8*0.55=0.44 → mild
        reading = UncertaintyReading(
            calibration_confidence=0.50,
            xi_threshold=0.55,
        )
        disc = UncertaintyDetector.build_disclosure(reading, {"H": 0.1, "I": 0.9})
        assert disc.disclosure_level == "mild"

    def test_moderate_disclosure(self):
        """Confidence well below xi → moderate disclosure."""
        # xi=0.55, cc=0.35 → 0.35 >= 0.5*0.55=0.275 → moderate
        reading = UncertaintyReading(
            calibration_confidence=0.35,
            xi_threshold=0.55,
            h_confidence=0.3,
            coverage=0.2,
        )
        disc = UncertaintyDetector.build_disclosure(reading, {"H": 0.1, "I": 0.9})
        assert disc.disclosure_level == "moderate"

    def test_significant_disclosure(self):
        """Very low confidence → significant disclosure."""
        # xi=0.80, cc=0.20 → 0.20 < 0.5*0.80=0.40 → significant
        reading = UncertaintyReading(
            calibration_confidence=0.20,
            xi_threshold=0.80,
            h_confidence=0.3,
            i_confidence=0.3,
            coverage=0.1,
        )
        disc = UncertaintyDetector.build_disclosure(reading, {"H": 0.5, "I": 0.4})
        assert disc.disclosure_level == "significant"
        assert disc.what_unknown != ""
        assert disc.why_unknown != ""

    def test_disclosure_what_known_populated(self):
        """When H is high, what_known mentions sensitivity."""
        reading = UncertaintyReading(
            calibration_confidence=0.30,
            xi_threshold=0.80,
        )
        disc = UncertaintyDetector.build_disclosure(reading, {"H": 0.6, "I": 0.8})
        assert disc.what_known != ""


# ═══════════════════════════════════════════════════════════════
#  TestEdgeCases
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_result(self, detector, enable_uncertainty):
        """Empty result dict doesn't crash."""
        reading = detector.detect({}, domain="general")
        assert reading.calibration_confidence >= 0.0
        assert reading.calibration_confidence <= 1.0

    def test_missing_scorer_confidence(self, detector, enable_uncertainty):
        """Missing scorer_confidence defaults to 'high'."""
        result = {"H": 0.1, "I": 0.9, "E": 0.3}
        reading = detector.detect(result, domain="general")
        assert reading.h_confidence == 0.9  # default 'high' → 0.9

    def test_calibration_confidence_range(self, detector, enable_uncertainty):
        """calibration_confidence is always in [0, 1]."""
        for result_fn in [_high_confidence_result, _low_confidence_result,
                          _mixed_confidence_result]:
            for domain in CONFIDENCE_THRESHOLD_BY_DOMAIN:
                reading = detector.detect(result_fn(), domain=domain)
                assert 0.0 <= reading.calibration_confidence <= 1.0, (
                    f"cc={reading.calibration_confidence} out of range "
                    f"for domain={domain}"
                )

    def test_dataclass_defaults(self):
        """UncertaintyReading defaults are safe."""
        reading = UncertaintyReading()
        assert reading.calibration_confidence == 1.0
        assert reading.xi_threshold == 0.55
        assert not reading.should_gate
        assert not reading.should_abstain
        assert not reading.enabled

    def test_disclosure_defaults(self):
        """UncertaintyDisclosure defaults to 'none'."""
        disc = UncertaintyDisclosure()
        assert disc.disclosure_level == "none"
        assert disc.what_unknown == ""


# ═══════════════════════════════════════════════════════════════
#  TestAdversarial — bugs found by 4-model external review
#  (ChatGPT, Gemini, Grok, DeepSeek — unanimous on all 4)
# ═══════════════════════════════════════════════════════════════

class TestAdversarial:
    """Adversarial tests targeting confirmed bugs from external review."""

    def test_trace_never_exceeds_1_after_100_updates(self, enable_uncertainty, enable_trace):
        """BUG 1 regression: trace must stay bounded in [0, 1] after
        100 consecutive max-uncertainty updates (EMA fix)."""
        detector = UncertaintyDetector()
        # Max uncertainty: all low confidence, zero coverage
        worst_result = {
            "H": 0.0, "I": 0.0, "E": 0.0,
            "scorer_confidence": {"H": "low", "I": "low", "E": "low"},
            "scorer_max_sim": {"H": 0.05, "I": 0.05, "E": 0.05},
            "unknown_territory": True,
        }
        for turn in range(100):
            reading = detector.detect(worst_result, domain="general")
            assert reading.uncertainty_trace <= 1.0, (
                f"Trace overflowed at turn {turn+1}: {reading.uncertainty_trace}"
            )
            assert reading.uncertainty_trace >= 0.0, (
                f"Trace went negative at turn {turn+1}: {reading.uncertainty_trace}"
            )

    def test_hi_divergence_fires_on_accidental_harm(self, detector, enable_uncertainty):
        """BUG 2 regression: H=0.9, I=0.1 (accidental harm) must
        trigger divergence signal — old code required I > 0.6."""
        result = {
            "H": 0.9, "I": 0.1, "E": 0.5,
            "scorer_confidence": {"H": "high", "I": "high", "E": "high"},
            "scorer_max_sim": {"H": 0.55, "I": 0.55, "E": 0.55},
            "unknown_territory": False,
        }
        ambiguity, n_signals = detector._compute_ambiguity(result)
        assert n_signals >= 1, (
            "Divergence did not fire for H=0.9, I=0.1 (accidental harm)"
        )
        assert ambiguity > 0.0, (
            f"Ambiguity should be > 0 for accidental harm, got {ambiguity}"
        )

    def test_nan_input_produces_safe_fallback(self, detector, enable_uncertainty):
        """BUG 4 regression: NaN in scorer confidence must produce
        safe fallback (low calibration_confidence → CLARIFY/ABSTAIN)."""
        result = {
            "H": float('nan'), "I": 0.5, "E": 0.5,
            "scorer_confidence": {"H": float('nan'), "I": "high", "E": "high"},
            "scorer_max_sim": {"H": float('nan'), "I": 0.50, "E": 0.50},
            "unknown_territory": False,
        }
        reading = detector.detect(result, domain="healthcare")
        # Must not be NaN
        import math
        assert not math.isnan(reading.calibration_confidence), (
            "calibration_confidence is NaN — NaN guard failed"
        )
        assert not math.isinf(reading.calibration_confidence), (
            "calibration_confidence is Inf — Inf guard failed"
        )
        # Should be low enough to trigger gate or abstention in healthcare
        assert reading.calibration_confidence <= 1.0
        assert reading.calibration_confidence >= 0.0

    def test_abstention_triggers_when_below_threshold(self, enable_uncertainty):
        """BUG 3 regression: abstention must set should_gate=True
        (abstention is connected to gate, not floating independently)."""
        detector = UncertaintyDetector()
        # Fabricate result that produces cc < abstention_threshold (0.30 for healthcare)
        result = {
            "H": 0.8, "I": 0.8, "E": 0.5,
            "scorer_confidence": {"H": "low", "I": "low", "E": "low"},
            "scorer_max_sim": {"H": 0.05, "I": 0.05, "E": 0.05},
            "unknown_territory": True,
        }
        reading = detector.detect(
            result, domain="healthcare",
            arabic_signals={"arabizi_detected": True, "cultural_indirection": True},
        )
        assert reading.should_abstain, (
            f"Expected abstention for cc={reading.calibration_confidence} "
            f"< threshold=0.30"
        )
        assert reading.should_gate, (
            "Abstention must imply should_gate=True (gate connected to abstention)"
        )
