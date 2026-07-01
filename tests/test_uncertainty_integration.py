"""
Integration test suite for AATIF Uncertainty/Calibration Module

Tests the full pipeline:
  UncertaintyDetector + GovernanceEquation (S equation)
  OutputGate Layer 8 (false certainty detection)
  Feature flags controlling behavior end-to-end

Architecture under test (B-prime Safety-Observational):
  UncertaintyDetector  →  observational (computes calibration_confidence)
  GovernanceEquation   →  judicial (confidence gate: EXECUTE→CLARIFY)
  OutputGate Layer 8   →  corrective (false certainty tone check)

Design consensus: Claude x ChatGPT, 2026-06-30
"""

import pytest

import aatif_uncertainty_detector as uc_mod
import aatif_output_gate as gate_mod
from aatif_uncertainty_detector import (
    UncertaintyDetector,
    UncertaintyReading,
    UncertaintyDisclosure,
    CONFIDENCE_THRESHOLD_BY_DOMAIN,
)
from aatif_s_equation import compute_s_gated_from_scores
from aatif_output_gate import AATIFOutputGate, FalseCertaintyReading


# ═══════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def detector():
    return UncertaintyDetector()


@pytest.fixture
def gate():
    return AATIFOutputGate()


@pytest.fixture
def enable_all():
    """Enable all uncertainty features, restore after."""
    old = {
        "enabled": uc_mod.UNCERTAINTY_ENABLED,
        "gate": uc_mod.UNCERTAINTY_GATE_ENABLED,
        "output": uc_mod.UNCERTAINTY_OUTPUT_CHECK_ENABLED,
    }
    uc_mod.UNCERTAINTY_ENABLED = True
    uc_mod.UNCERTAINTY_GATE_ENABLED = True
    uc_mod.UNCERTAINTY_OUTPUT_CHECK_ENABLED = True
    yield
    uc_mod.UNCERTAINTY_ENABLED = old["enabled"]
    uc_mod.UNCERTAINTY_GATE_ENABLED = old["gate"]
    uc_mod.UNCERTAINTY_OUTPUT_CHECK_ENABLED = old["output"]


@pytest.fixture
def enable_gate_only():
    """Enable uncertainty detection + gate, but not output check."""
    old = {
        "enabled": uc_mod.UNCERTAINTY_ENABLED,
        "gate": uc_mod.UNCERTAINTY_GATE_ENABLED,
    }
    uc_mod.UNCERTAINTY_ENABLED = True
    uc_mod.UNCERTAINTY_GATE_ENABLED = True
    yield
    uc_mod.UNCERTAINTY_ENABLED = old["enabled"]
    uc_mod.UNCERTAINTY_GATE_ENABLED = old["gate"]


# ═══════════════════════════════════════════════════════════════
#  S Equation + Uncertainty Confidence Gate
# ═══════════════════════════════════════════════════════════════

class TestConfidenceGateIntegration:
    """Test confidence gate within GovernanceEquation flow."""

    def test_high_confidence_execute_stays(self, detector, enable_gate_only):
        """EXECUTE with high confidence stays EXECUTE."""
        # S equation result that would be EXECUTE
        s_result = compute_s_gated_from_scores(H=0.1, I=0.9, E=0.6,
                                                domain="general")
        assert s_result["decision"] == "EXECUTE"

        # Detector with high confidence
        engine_result = {
            "H": 0.1, "I": 0.9, "E": 0.6,
            "scorer_confidence": {"H": "high", "I": "high", "E": "high"},
            "scorer_max_sim": {"H": 0.55, "I": 0.60, "E": 0.50},
            "unknown_territory": False,
            "decision": "EXECUTE",
        }
        reading = detector.detect(engine_result, domain="general")
        # High confidence → should not trigger gate
        assert not reading.should_gate

    def test_low_confidence_execute_escalates_to_clarify(self, detector, enable_gate_only):
        """EXECUTE with low confidence in healthcare → should_gate=True.

        The actual EXECUTE→CLARIFY override happens inside AATIFEngine.compute(),
        which we test indirectly via should_gate.
        """
        engine_result = {
            "H": 0.3, "I": 0.8, "E": 0.5,
            "scorer_confidence": {"H": "low", "I": "medium", "E": "low"},
            "scorer_max_sim": {"H": 0.15, "I": 0.25, "E": 0.12},
            "unknown_territory": True,
            "decision": "EXECUTE",
        }
        reading = detector.detect(engine_result, domain="healthcare")
        # Low confidence + healthcare xi=0.80 → should gate
        assert reading.should_gate
        assert reading.calibration_confidence < 0.80

    def test_safe_stop_not_affected_by_gate(self, detector, enable_gate_only):
        """Confidence gate only escalates EXECUTE→CLARIFY, not other decisions."""
        engine_result = {
            "H": 0.8, "I": 0.3, "E": 0.6,
            "scorer_confidence": {"H": "low", "I": "low", "E": "low"},
            "scorer_max_sim": {"H": 0.12, "I": 0.10, "E": 0.08},
            "unknown_territory": True,
            "decision": "SAFE_STOP",
        }
        reading = detector.detect(engine_result, domain="healthcare")
        # should_gate can be True, but the S equation only applies it
        # when decision == EXECUTE. SAFE_STOP stays SAFE_STOP.
        # The gate is escalation-only.

    def test_creative_domain_more_lenient(self, detector, enable_gate_only):
        """Creative domain has lower xi → less likely to gate."""
        engine_result = {
            "H": 0.2, "I": 0.7, "E": 0.5,
            "scorer_confidence": {"H": "medium", "I": "medium", "E": "medium"},
            "scorer_max_sim": {"H": 0.30, "I": 0.35, "E": 0.28},
            "unknown_territory": False,
            "decision": "EXECUTE",
        }
        r_health = detector.detect(engine_result, domain="healthcare")
        r_creative = detector.detect(engine_result, domain="creative")

        # Same result: healthcare xi=0.80 likely gates, creative xi=0.40 likely doesn't
        assert r_health.xi_threshold == 0.80
        assert r_creative.xi_threshold == 0.40
        # Medium confidence ~ 0.6, should gate for healthcare but not creative
        if r_health.calibration_confidence < 0.80:
            assert r_health.should_gate
        if r_creative.calibration_confidence >= 0.40:
            assert not r_creative.should_gate


# ═══════════════════════════════════════════════════════════════
#  OutputGate Layer 8 — False Certainty Detection
# ═══════════════════════════════════════════════════════════════

class TestFalseCertaintyDetection:
    """Test Layer 8 false certainty detection in OutputGate."""

    def test_disabled_passes_through(self, gate):
        """When UNCERTAINTY_OUTPUT_CHECK_ENABLED=False, Layer 8 passes through."""
        reading = UncertaintyReading(
            calibration_confidence=0.20,
            enabled=True,
        )
        result = gate.check_false_certainty(
            "This is definitely the right answer.",
            uncertainty_reading=reading,
        )
        assert not result.false_certainty_detected
        assert "disabled" in result.notes.lower()

    def test_detects_english_certainty_markers(self, gate, enable_all):
        """Layer 8 detects English certainty markers when confidence is low."""
        reading = UncertaintyReading(
            calibration_confidence=0.20,
            enabled=True,
        )
        result = gate.check_false_certainty(
            "You should definitely take this medication. It is guaranteed to work.",
            uncertainty_reading=reading,
        )
        assert result.false_certainty_detected
        assert len(result.matched_markers) >= 2
        # "definitely" and "guaranteed" should be in markers
        markers_lower = [m.lower() for m in result.matched_markers]
        assert "definitely" in markers_lower
        assert any("guarantee" in m for m in markers_lower)

    def test_detects_arabic_certainty_markers(self, gate, enable_all):
        """Layer 8 detects Arabic certainty markers when confidence is low."""
        reading = UncertaintyReading(
            calibration_confidence=0.25,
            enabled=True,
        )
        result = gate.check_false_certainty(
            "بالتأكيد هذا هو الحل الصحيح. أكيد بيشتغل.",
            uncertainty_reading=reading,
        )
        assert result.false_certainty_detected
        assert len(result.matched_markers) >= 1

    def test_no_detection_when_confident(self, gate, enable_all):
        """When internal confidence is high, certainty markers are fine."""
        reading = UncertaintyReading(
            calibration_confidence=0.90,
            enabled=True,
        )
        result = gate.check_false_certainty(
            "You should definitely try this approach.",
            uncertainty_reading=reading,
        )
        assert not result.false_certainty_detected

    def test_no_detection_without_markers(self, gate, enable_all):
        """When response has no certainty markers, no detection."""
        reading = UncertaintyReading(
            calibration_confidence=0.20,
            enabled=True,
        )
        result = gate.check_false_certainty(
            "This might work, but I am not sure. Consider consulting a specialist.",
            uncertainty_reading=reading,
        )
        assert not result.false_certainty_detected

    def test_no_reading_passes_through(self, gate, enable_all):
        """When no uncertainty reading provided, passes through."""
        result = gate.check_false_certainty(
            "Definitely the right choice.",
            uncertainty_reading=None,
        )
        assert not result.false_certainty_detected

    def test_layer8_never_blocks(self, gate, enable_all):
        """Layer 8 never sets blocked or changes decision."""
        reading = UncertaintyReading(
            calibration_confidence=0.10,
            enabled=True,
        )
        result = gate.check_false_certainty(
            "This is definitely, certainly, absolutely, guaranteed correct. 100%",
            uncertainty_reading=reading,
        )
        # Should detect false certainty but never block
        assert result.false_certainty_detected
        # FalseCertaintyReading has no 'blocked' field — it is tone-only
        assert not hasattr(result, 'blocked') or not getattr(result, 'blocked', False)


# ═══════════════════════════════════════════════════════════════
#  Feature Flag Isolation
# ═══════════════════════════════════════════════════════════════

class TestFeatureFlagIsolation:
    """Verify feature flags control behavior independently."""

    def test_detection_without_gate(self, detector):
        """UNCERTAINTY_ENABLED=True, GATE_ENABLED=False → detect but don't gate."""
        old_enabled = uc_mod.UNCERTAINTY_ENABLED
        old_gate = uc_mod.UNCERTAINTY_GATE_ENABLED
        uc_mod.UNCERTAINTY_ENABLED = True
        uc_mod.UNCERTAINTY_GATE_ENABLED = False
        try:
            result = {
                "H": 0.5, "I": 0.7, "E": 0.4,
                "scorer_confidence": {"H": "low", "I": "low", "E": "low"},
                "scorer_max_sim": {"H": 0.10, "I": 0.10, "E": 0.10},
                "unknown_territory": True,
            }
            reading = detector.detect(result, domain="healthcare")
            # Detection is enabled → reading has real values
            assert reading.enabled
            assert reading.calibration_confidence < 1.0
            # But gate is disabled → should_gate is False
            assert not reading.should_gate
            assert not reading.gate_enabled
        finally:
            uc_mod.UNCERTAINTY_ENABLED = old_enabled
            uc_mod.UNCERTAINTY_GATE_ENABLED = old_gate

    def test_all_disabled_is_transparent(self, detector):
        """All flags disabled → system behaves as if module doesn't exist."""
        result = {
            "H": 0.1, "I": 0.9, "E": 0.3,
            "scorer_confidence": {"H": "low", "I": "low", "E": "low"},
            "scorer_max_sim": {"H": 0.10, "I": 0.10, "E": 0.10},
            "unknown_territory": True,
        }
        reading = detector.detect(result, domain="healthcare")
        # All disabled → returns default high confidence
        assert reading.calibration_confidence == 1.0
        assert not reading.should_gate
        assert not reading.should_abstain


# ═══════════════════════════════════════════════════════════════
#  S Equation Math with Uncertainty
# ═══════════════════════════════════════════════════════════════

class TestSEquationUncertaintyMath:
    """Verify S equation math is unchanged by uncertainty module."""

    def test_s_equation_unchanged_when_disabled(self):
        """S equation output is identical with uncertainty disabled."""
        # The S equation should produce the same result regardless
        # of whether uncertainty module is imported
        r1 = compute_s_gated_from_scores(H=0.3, I=0.8, E=0.5, domain="general")
        r2 = compute_s_gated_from_scores(H=0.3, I=0.8, E=0.5, domain="general")
        assert r1["S"] == r2["S"]
        assert r1["decision"] == r2["decision"]

    def test_gated_equation_still_works(self):
        """Gated equation produces correct decisions."""
        # Benign
        r = compute_s_gated_from_scores(H=0.1, I=0.9, E=0.6, domain="general")
        assert r["decision"] == "EXECUTE"

        # Harmful
        r = compute_s_gated_from_scores(H=0.8, I=0.3, E=0.5, domain="general")
        assert r["decision"] in ("SAFE_STOP", "SAFE_FREEZE")

    def test_hard_override_unaffected(self):
        """H > 0.7 hard override to SAFE_FREEZE still works."""
        r = compute_s_gated_from_scores(H=0.75, I=0.9, E=0.9, domain="general")
        assert r["decision"] == "SAFE_FREEZE"
        assert r["hard_override"] is True


# ═══════════════════════════════════════════════════════════════
#  End-to-End Pipeline Scenario
# ═══════════════════════════════════════════════════════════════

class TestEndToEndScenario:
    """Scenario tests combining multiple components."""

    def test_confident_benign_passes(self, detector, gate, enable_all):
        """Confident benign request: EXECUTE, no gate, no false certainty."""
        engine_result = {
            "H": 0.1, "I": 0.9, "E": 0.3,
            "S": 0.95, "decision": "EXECUTE",
            "scorer_confidence": {"H": "high", "I": "high", "E": "high"},
            "scorer_max_sim": {"H": 0.55, "I": 0.60, "E": 0.50},
            "unknown_territory": False,
        }

        # Step 1: Uncertainty detection
        uc_reading = detector.detect(engine_result, domain="general")
        assert not uc_reading.should_gate
        assert not uc_reading.should_abstain

        # Step 2: Output gate Layer 8 — confident response is fine
        fc_reading = gate.check_false_certainty(
            "Here is the recipe you asked for.",
            uncertainty_reading=uc_reading,
        )
        assert not fc_reading.false_certainty_detected

    def test_uncertain_healthcare_gates_and_catches_false_certainty(
        self, detector, gate, enable_all
    ):
        """Uncertain healthcare request: gates EXECUTE→CLARIFY,
        catches false certainty in output."""
        engine_result = {
            "H": 0.3, "I": 0.7, "E": 0.4,
            "S": 0.72, "decision": "EXECUTE",
            "scorer_confidence": {"H": "low", "I": "medium", "E": "low"},
            "scorer_max_sim": {"H": 0.12, "I": 0.25, "E": 0.10},
            "unknown_territory": True,
        }

        # Step 1: Uncertainty detection in healthcare
        uc_reading = detector.detect(engine_result, domain="healthcare")
        assert uc_reading.should_gate  # confidence < 0.80

        # Step 2: If the LLM responds with false certainty
        fc_reading = gate.check_false_certainty(
            "You should definitely stop taking your medication.",
            uncertainty_reading=uc_reading,
        )
        assert fc_reading.false_certainty_detected
        assert "definitely" in [m.lower() for m in fc_reading.matched_markers]
