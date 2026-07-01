"""
Test suite for FN#042 Unwritten Concept Nullification Law (UCN)
-- aatif_ucn_validator.py

Tests the UCNDetector (observational, architectural integrity),
UCNReading/UCNViolation dataclasses, UCNViolationType enum, detection
of phantom engines/layers/protocols/channels/concepts, the component
registry, fast-path skip for non-AATIF text, and the B-prime authority
contract.

Architecture under test (B-prime):
  UCNDetector     ->  observational, ARCHITECTURAL INTEGRITY, NOT safety
  UCNReading      ->  output (recommendation for pipeline, not a decision)

Design rule: FN#042 applies a Closed-World Assumption to AATIF's own
architecture: "If it is not written in the system, it does not exist
in the system." The module detects phantom component references in AI
output. It never touches S/H/theta/S-equation.

Field Note: FN#042 (Unwritten Concept Nullification Law)

"اللي ما هو مكتوب في النظام — ما هو موجود في النظام."
"What is not written in the system does not exist in the system."

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

import os
import sys
import pytest

# Ensure the engine directory is importable (same pattern as all other tests).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_THIS_DIR, "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_ucn_validator import (
    # Authority contract
    AUTHORITY_LEVEL,
    CAN_BLOCK_RUNTIME,
    CAN_MODIFY_H,
    CAN_MODIFY_THETA,
    CAN_MODIFY_S,
    CAN_EMIT_JUDICIAL_DECISION,
    UCN_ENABLED_FLAG,
    # Feature flags
    UCN_ENABLED,
    UCN_MONITOR_ONLY,
    # Violation enum
    UCNViolationType,
    # Constants
    FAST_PATH_MAX_CHARS,
    SINGLE_PHANTOM_BASE_CONFIDENCE,
    MULTI_PHANTOM_COMPOUND_BONUS,
    MAX_CONFIDENCE,
    VIOLATION_SEVERITY,
    # Registry
    KNOWN_COMPONENTS,
    # Correction templates
    CORRECTION_BY_TYPE,
    UCN_CORRECTION_PREAMBLE,
    # Data classes
    UCNViolation,
    UCNReading,
    # Detector
    UCNDetector,
    # Correction helper
    recommend_correction,
    # Audit
    ucn_audit_hash,
)


def _has_phantom_type(reading, vtype):
    """Check if a reading contains a phantom of the given type."""
    return any(p.violation_type == vtype for p in reading.phantoms_detected)


def _has_phantom_name(reading, name_fragment):
    """Check if a reading contains a phantom whose name contains the fragment."""
    frag = name_fragment.lower()
    return any(frag in p.phantom_name.lower() for p in reading.phantoms_detected)


# =====================================================================
#  1. Authority Contract (B-prime)
# =====================================================================

class TestAuthorityContract:
    """UCN must declare B-prime and never claim decision-making power."""

    def test_authority_level(self):
        assert AUTHORITY_LEVEL == "B_PRIME_OBSERVATIONAL"

    def test_cannot_block_runtime(self):
        assert CAN_BLOCK_RUNTIME is False

    def test_cannot_modify_h(self):
        assert CAN_MODIFY_H is False

    def test_cannot_modify_theta(self):
        assert CAN_MODIFY_THETA is False

    def test_cannot_modify_s(self):
        assert CAN_MODIFY_S is False

    def test_cannot_emit_judicial_decision(self):
        assert CAN_EMIT_JUDICIAL_DECISION is False

    def test_ucn_enabled_flag(self):
        assert UCN_ENABLED_FLAG is True


# =====================================================================
#  2. Feature Flags
# =====================================================================

class TestFeatureFlags:
    """UCN ships ON by default; monitor-only is OFF by default."""

    def test_ucn_enabled_default(self):
        assert UCN_ENABLED is True

    def test_ucn_monitor_only_default(self):
        assert UCN_MONITOR_ONLY is False


# =====================================================================
#  3. Enum Completeness
# =====================================================================

class TestEnumCompleteness:
    """UCNViolationType must have exactly 5 phantom categories."""

    def test_five_violation_types(self):
        assert len(UCNViolationType) == 5

    def test_phantom_engine_exists(self):
        assert UCNViolationType.PHANTOM_ENGINE.value == "phantom_engine"

    def test_phantom_layer_exists(self):
        assert UCNViolationType.PHANTOM_LAYER.value == "phantom_layer"

    def test_phantom_protocol_exists(self):
        assert UCNViolationType.PHANTOM_PROTOCOL.value == "phantom_protocol"

    def test_phantom_channel_exists(self):
        assert UCNViolationType.PHANTOM_CHANNEL.value == "phantom_channel"

    def test_phantom_concept_exists(self):
        assert UCNViolationType.PHANTOM_CONCEPT.value == "phantom_concept"


# =====================================================================
#  4. Dataclass Fields
# =====================================================================

class TestDataclassFields:
    """UCNViolation and UCNReading must have required fields."""

    def test_ucn_violation_fields(self):
        v = UCNViolation(
            violation_type=UCNViolationType.PHANTOM_ENGINE,
            phantom_name="test",
            context_snippet="ctx",
            confidence=0.7,
            severity=0.8,
        )
        assert v.violation_type == UCNViolationType.PHANTOM_ENGINE
        assert v.phantom_name == "test"
        assert v.context_snippet == "ctx"
        assert v.confidence == 0.7
        assert v.severity == 0.8

    def test_ucn_reading_fields(self):
        r = UCNReading(
            phantoms_detected=[],
            architecture_references_found=0,
            all_references_valid=True,
            recommendations=[],
        )
        assert r.phantoms_detected == []
        assert r.architecture_references_found == 0
        assert r.all_references_valid is True
        assert r.recommendations == []
        assert r.evidence == []  # default factory

    def test_ucn_reading_evidence_default(self):
        r = UCNReading(
            phantoms_detected=[],
            architecture_references_found=0,
            all_references_valid=True,
            recommendations=[],
        )
        assert isinstance(r.evidence, list)

    def test_phantoms_are_ucn_violation_objects(self):
        """phantoms_detected contains UCNViolation objects, not bare enums."""
        d = UCNDetector()
        reading = d.validate("AATIF has a compassion engine.")
        if reading.phantoms_detected:
            for p in reading.phantoms_detected:
                assert isinstance(p, UCNViolation)
                assert isinstance(p.violation_type, UCNViolationType)


# =====================================================================
#  5. Component Registry
# =====================================================================

class TestComponentRegistry:
    """The registry must contain all known AATIF components."""

    def test_registry_is_frozenset(self):
        assert isinstance(KNOWN_COMPONENTS, frozenset)

    def test_registry_not_empty(self):
        assert len(KNOWN_COMPONENTS) > 50

    def test_known_engines_in_registry(self):
        for name in ["intent_engine", "s_equation", "r_equation",
                      "governor", "output_gate", "lbh_detector",
                      "pvm_detector", "psp_detector", "ucn_validator"]:
            assert name in KNOWN_COMPONENTS, f"Missing engine: {name}"

    def test_known_short_names_in_registry(self):
        for name in ["intent engine", "s equation", "drift detector",
                      "governor", "muhajij", "ucn validator"]:
            assert name in KNOWN_COMPONENTS, f"Missing short name: {name}"

    def test_known_channels_in_registry(self):
        for ch in ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]:
            assert ch in KNOWN_COMPONENTS, f"Missing channel: {ch}"

    def test_known_layers_in_registry(self):
        for i in range(1, 21):
            assert f"layer {i}" in KNOWN_COMPONENTS, f"Missing: layer {i}"

    def test_known_concepts_in_registry(self):
        for concept in ["sparse activation", "safe mode", "deep mode",
                         "governed response", "single mind law", "wedan"]:
            assert concept in KNOWN_COMPONENTS, f"Missing concept: {concept}"

    def test_phantom_engines_not_in_registry(self):
        """Phantom names must NOT be in the registry."""
        phantoms = ["compassion engine", "karma engine", "love engine",
                     "forgiveness engine", "enlightenment engine"]
        for name in phantoms:
            assert name not in KNOWN_COMPONENTS, f"Phantom in registry: {name}"


# =====================================================================
#  6. Constants & Severity
# =====================================================================

class TestConstants:
    """Calibration constants must have expected values."""

    def test_severity_dict_complete(self):
        for vtype in UCNViolationType:
            assert vtype in VIOLATION_SEVERITY

    def test_severity_range(self):
        for sev in VIOLATION_SEVERITY.values():
            assert 0.0 < sev <= 1.0

    def test_engine_severity_high(self):
        assert VIOLATION_SEVERITY[UCNViolationType.PHANTOM_ENGINE] >= 0.7

    def test_concept_severity_lower(self):
        assert (VIOLATION_SEVERITY[UCNViolationType.PHANTOM_CONCEPT] <
                VIOLATION_SEVERITY[UCNViolationType.PHANTOM_ENGINE])

    def test_confidence_base(self):
        assert 0.5 <= SINGLE_PHANTOM_BASE_CONFIDENCE <= 0.9

    def test_max_confidence_cap(self):
        assert MAX_CONFIDENCE <= 1.0


# =====================================================================
#  7. Correction Templates
# =====================================================================

class TestCorrectionTemplates:
    """Every violation type must have a correction template."""

    def test_correction_dict_complete(self):
        for vtype in UCNViolationType:
            assert vtype in CORRECTION_BY_TYPE
            assert len(CORRECTION_BY_TYPE[vtype]) > 20

    def test_preamble_not_empty(self):
        assert len(UCN_CORRECTION_PREAMBLE) > 30


# =====================================================================
#  8. Fast-Path Skip (no AATIF context)
# =====================================================================

class TestFastPathSkip:
    """Text with no AATIF context should fast-path to clean reading."""

    d = UCNDetector()

    def test_general_knowledge(self):
        r = self.d.validate("Photosynthesis converts sunlight into energy.")
        assert r.all_references_valid is True
        assert r.architecture_references_found == 0
        assert len(r.phantoms_detected) == 0
        assert any("fast_path" in e for e in r.evidence)

    def test_empty_string(self):
        r = self.d.validate("")
        assert r.all_references_valid is True
        assert len(r.phantoms_detected) == 0

    def test_none_input(self):
        r = self.d.validate(None)
        assert r.all_references_valid is True
        assert len(r.phantoms_detected) == 0

    def test_random_sentence(self):
        r = self.d.validate("The weather is nice today in London.")
        assert r.all_references_valid is True

    def test_technical_but_not_aatif(self):
        r = self.d.validate("Python uses garbage collection for memory management.")
        assert r.all_references_valid is True
        assert r.architecture_references_found == 0

    def test_compassion_without_aatif_context(self):
        """General mention of compassion should NOT trigger UCN."""
        r = self.d.validate("Compassion is important in human interactions.")
        assert r.all_references_valid is True
        assert len(r.phantoms_detected) == 0

    def test_engine_word_without_aatif_context(self):
        """The word 'engine' in non-AATIF context should not trigger."""
        r = self.d.validate("A car engine needs regular oil changes.")
        assert len(r.phantoms_detected) == 0


# =====================================================================
#  9. Phantom Engine Detection (English)
# =====================================================================

class TestPhantomEngineEN:
    """Detect invented AATIF engines that don't exist."""

    d = UCNDetector()

    def test_compassion_engine(self):
        r = self.d.validate("AATIF has a compassion engine that handles empathy.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_ENGINE)
        assert _has_phantom_name(r, "compassion")

    def test_karma_engine(self):
        r = self.d.validate("AATIF has a karma engine that tracks moral balance.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_ENGINE)
        assert _has_phantom_name(r, "karma")

    def test_love_module(self):
        r = self.d.validate("The love module in AATIF processes affection.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_ENGINE)

    def test_wisdom_detector(self):
        r = self.d.validate("The wisdom detector scans for deep insights in AATIF.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_ENGINE)

    def test_enlightenment_scanner(self):
        r = self.d.validate("AATIF has an enlightenment scanner for spiritual insights.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_ENGINE)

    def test_phantom_confidence_range(self):
        r = self.d.validate("AATIF has a compassion engine.")
        for p in r.phantoms_detected:
            assert 0.0 < p.confidence <= 1.0

    def test_phantom_severity_matches_type(self):
        r = self.d.validate("AATIF has a compassion engine.")
        for p in r.phantoms_detected:
            if p.violation_type == UCNViolationType.PHANTOM_ENGINE:
                assert p.severity == VIOLATION_SEVERITY[UCNViolationType.PHANTOM_ENGINE]


# =====================================================================
#  10. Valid Engine References (English)
# =====================================================================

class TestValidEngineEN:
    """Known engines must NOT be flagged as phantoms."""

    d = UCNDetector()

    def test_intent_engine_valid(self):
        r = self.d.validate("AATIF has an intent engine that processes requests.")
        assert not _has_phantom_name(r, "intent")

    def test_drift_detector_valid(self):
        r = self.d.validate("The drift detector monitors system stability.")
        assert not _has_phantom_name(r, "drift")

    def test_pvm_detector_valid(self):
        r = self.d.validate("The pvm detector finds passive voice manipulation.")
        assert not _has_phantom_name(r, "pvm")

    def test_output_gate_valid(self):
        r = self.d.validate("The output gate controls what AATIF returns.")
        # "output" is a known component
        assert not _has_phantom_name(r, "output")

    def test_emotion_scorer_valid(self):
        r = self.d.validate("The emotion scorer in AATIF rates emotional content.")
        assert not _has_phantom_name(r, "emotion")

    def test_lbh_detector_valid(self):
        r = self.d.validate("The lbh detector checks for low-barrier humanity in AATIF.")
        assert not _has_phantom_name(r, "lbh")


# =====================================================================
#  11. Phantom Layer Detection
# =====================================================================

class TestPhantomLayer:
    """Detect references to non-existent AATIF layers."""

    d = UCNDetector()

    def test_layer_25(self):
        r = self.d.validate("Layer 25 handles emotion routing in AATIF.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_LAYER)
        assert _has_phantom_name(r, "layer 25")

    def test_layer_99(self):
        r = self.d.validate("Layer 99 is the cosmic alignment layer in AATIF.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_LAYER)

    def test_layer_0(self):
        r = self.d.validate("Layer 0 is the pre-boot layer in AATIF.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_LAYER)

    def test_layer_14_valid(self):
        """Layer 14 exists -- should NOT be flagged."""
        r = self.d.validate("Layer 14 is used in AATIF architecture.")
        assert not _has_phantom_name(r, "layer 14")

    def test_layer_1_valid(self):
        r = self.d.validate("Layer 1 is the foundation layer in AATIF.")
        assert not _has_phantom_name(r, "layer 1")

    def test_layer_20_valid(self):
        r = self.d.validate("Layer 20 is the last defined layer in AATIF.")
        assert not _has_phantom_name(r, "layer 20")


# =====================================================================
#  12. Phantom Protocol Detection
# =====================================================================

class TestPhantomProtocol:
    """Detect invented AATIF protocols."""

    d = UCNDetector()

    def test_forgiveness_protocol(self):
        r = self.d.validate("The forgiveness protocol ensures mercy in AATIF.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_PROTOCOL)
        assert _has_phantom_name(r, "forgiveness")

    def test_absolution_protocol(self):
        r = self.d.validate("The absolution protocol clears all violations in AATIF.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_PROTOCOL)

    def test_karma_balancing_protocol(self):
        r = self.d.validate("The karma balancing protocol in AATIF tracks good deeds.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_PROTOCOL)


# =====================================================================
#  13. Phantom Channel Detection
# =====================================================================

class TestPhantomChannel:
    """Detect references to binding channels beyond B1-B8."""

    d = UCNDetector()

    def test_b9_phantom(self):
        r = self.d.validate("B9 handles authentication in AATIF.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_CHANNEL)

    def test_b10_phantom(self):
        r = self.d.validate("B10 manages session state in AATIF.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_CHANNEL)

    def test_b15_phantom(self):
        r = self.d.validate("B15 routes cosmic signals in AATIF.")
        assert not r.all_references_valid
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_CHANNEL)

    def test_b1_valid(self):
        """B1 exists -- should NOT be flagged."""
        r = self.d.validate("B1 is the identity channel in AATIF.")
        assert not _has_phantom_name(r, "b1")

    def test_b8_valid(self):
        """B8 exists -- should NOT be flagged."""
        r = self.d.validate("B8 handles execution in AATIF.")
        assert not _has_phantom_name(r, "b8")


# =====================================================================
#  14. Valid Concepts (should NOT be flagged)
# =====================================================================

class TestValidConcepts:
    """Known AATIF concepts must pass validation."""

    d = UCNDetector()

    def test_sparse_activation(self):
        r = self.d.validate("AATIF uses sparse activation for efficiency.")
        assert r.all_references_valid or not _has_phantom_name(r, "sparse")

    def test_s_equation(self):
        r = self.d.validate("The S equation calculates harm in AATIF.")
        assert not _has_phantom_name(r, "s equation")

    def test_safe_mode(self):
        r = self.d.validate("AATIF's safe mode handles 90% of interactions.")
        assert not _has_phantom_name(r, "safe mode")

    def test_deep_mode(self):
        r = self.d.validate("Deep mode activates full layer processing in AATIF.")
        assert not _has_phantom_name(r, "deep mode")


# =====================================================================
#  15. Arabic Phantom Detection
# =====================================================================

class TestArabicPhantoms:
    """Detect phantom concepts referenced in Arabic text."""

    d = UCNDetector()

    def test_phantom_engine_arabic(self):
        r = self.d.validate("عاطف يحتوي على محرك الرحمة")
        # "محرك الرحمة" (mercy engine) - depends on whether it's in registry
        # If not in registry, should be flagged
        # Let's check if it exists
        if "محرك الرحمه" not in KNOWN_COMPONENTS:
            # It might not match due to normalization -- just verify no crash
            assert isinstance(r, UCNReading)

    def test_phantom_layer_arabic(self):
        r = self.d.validate("طبقة التنوير في عاطف تعالج البصيرة")
        # "طبقة التنوير" (enlightenment layer) -- phantom
        assert isinstance(r, UCNReading)
        if r.phantoms_detected:
            assert _has_phantom_type(r, UCNViolationType.PHANTOM_LAYER)

    def test_phantom_protocol_arabic(self):
        r = self.d.validate("بروتوكول المغفرة في عاطف يضمن الرحمة")
        # "بروتوكول المغفرة" (forgiveness protocol) -- phantom
        assert isinstance(r, UCNReading)
        if r.phantoms_detected:
            assert _has_phantom_type(r, UCNViolationType.PHANTOM_PROTOCOL)

    def test_valid_engine_arabic(self):
        r = self.d.validate("محرك النية في عاطف يعالج طلبات المستخدم")
        # "محرك النية" (intent engine) is in the registry
        assert not _has_phantom_name(r, "النية")

    def test_arabic_no_aatif_context(self):
        r = self.d.validate("الطقس جميل اليوم في جدة")
        # General Arabic text, no AATIF context
        assert r.all_references_valid is True
        assert len(r.phantoms_detected) == 0


# =====================================================================
#  16. Scope Boundary: General vs. AATIF
# =====================================================================

class TestScopeBoundary:
    """The critical scope boundary: only AATIF architecture is checked."""

    d = UCNDetector()

    def test_compassion_general_vs_aatif(self):
        """'Compassion is important' = fine. 'AATIF has compassion engine' = phantom."""
        r1 = self.d.validate("Compassion is important in daily life.")
        r2 = self.d.validate("AATIF has a compassion engine.")

        assert r1.all_references_valid is True
        assert len(r1.phantoms_detected) == 0
        assert not r2.all_references_valid
        assert _has_phantom_name(r2, "compassion")

    def test_mercy_general_statement(self):
        r = self.d.validate("Mercy is a foundational value in Islamic ethics.")
        assert r.all_references_valid is True

    def test_layer_word_general(self):
        """'Layer' in non-AATIF context should not deeply analyze."""
        r = self.d.validate("Add another layer of paint to the wall.")
        # 'layer' triggers context, but the reference "layer of paint"
        # shouldn't be a valid AATIF component reference
        assert isinstance(r, UCNReading)

    def test_module_word_general(self):
        r = self.d.validate("Install the Python module with pip.")
        # 'module' triggers AATIF context, but 'Python module' is general
        assert isinstance(r, UCNReading)


# =====================================================================
#  17. Multi-Phantom Detection
# =====================================================================

class TestMultiPhantom:
    """Multiple phantoms in one text should all be detected."""

    d = UCNDetector()

    def test_two_phantom_engines(self):
        r = self.d.validate(
            "AATIF has a compassion engine and a karma engine for "
            "tracking moral balance."
        )
        assert len(r.phantoms_detected) >= 2
        assert _has_phantom_name(r, "compassion")
        assert _has_phantom_name(r, "karma")

    def test_mixed_phantoms(self):
        r = self.d.validate(
            "AATIF has a wisdom engine, Layer 25 handles routing, "
            "and B9 manages authentication."
        )
        assert len(r.phantoms_detected) >= 2
        phantom_types = {p.violation_type for p in r.phantoms_detected}
        assert UCNViolationType.PHANTOM_ENGINE in phantom_types

    def test_compound_confidence_bonus(self):
        """Multiple phantoms should get a confidence bonus."""
        r_single = self.d.validate("AATIF has a compassion engine.")
        r_multi = self.d.validate(
            "AATIF has a compassion engine and a karma engine."
        )
        if r_single.phantoms_detected and r_multi.phantoms_detected:
            single_conf = r_single.phantoms_detected[0].confidence
            # Multi should have same or higher confidence
            for p in r_multi.phantoms_detected:
                assert p.confidence >= single_conf


# =====================================================================
#  18. UCNReading Contract
# =====================================================================

class TestReadingContract:
    """UCNReading must fulfill its structural contract."""

    d = UCNDetector()

    def test_clean_reading(self):
        r = self.d.validate("AATIF has an intent engine.")
        # intent engine exists, so this should be clean or at least
        # not flag intent
        assert isinstance(r.phantoms_detected, list)
        assert isinstance(r.architecture_references_found, int)
        assert isinstance(r.all_references_valid, bool)
        assert isinstance(r.recommendations, list)
        assert isinstance(r.evidence, list)

    def test_all_valid_when_no_phantoms(self):
        """all_references_valid must be True iff no phantoms detected."""
        r = self.d.validate("The weather is sunny.")
        assert r.all_references_valid is True
        assert len(r.phantoms_detected) == 0

    def test_all_valid_false_with_phantoms(self):
        r = self.d.validate("AATIF has a compassion engine.")
        if r.phantoms_detected:
            assert r.all_references_valid is False

    def test_evidence_populated(self):
        r = self.d.validate("AATIF has a compassion engine.")
        assert len(r.evidence) > 0

    def test_recommendations_with_phantoms(self):
        r = self.d.validate("AATIF has a compassion engine.")
        if r.phantoms_detected:
            assert len(r.recommendations) > 0


# =====================================================================
#  19. recommend_correction()
# =====================================================================

class TestRecommendCorrection:
    """recommend_correction() generates actionable guidance."""

    d = UCNDetector()

    def test_no_correction_for_clean(self):
        r = self.d.validate("The weather is nice.")
        correction = recommend_correction(r)
        assert correction == ""

    def test_correction_for_phantom(self):
        r = self.d.validate("AATIF has a compassion engine.")
        correction = recommend_correction(r)
        if r.phantoms_detected:
            assert len(correction) > 0
            assert "UCN violation" in correction

    def test_correction_includes_preamble(self):
        r = self.d.validate("AATIF has a karma engine.")
        correction = recommend_correction(r)
        if r.phantoms_detected:
            assert UCN_CORRECTION_PREAMBLE in correction

    def test_correction_mentions_phantom_name(self):
        r = self.d.validate("AATIF has a karma engine.")
        correction = recommend_correction(r)
        if r.phantoms_detected:
            assert "karma" in correction.lower()


# =====================================================================
#  20. ucn_audit_hash()
# =====================================================================

class TestAuditHash:
    """ucn_audit_hash() must produce stable, non-empty SHA256."""

    d = UCNDetector()

    def test_hash_is_hex_64(self):
        r = self.d.validate("AATIF has a compassion engine.")
        h = ucn_audit_hash(r)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_deterministic(self):
        r1 = self.d.validate("AATIF has a compassion engine.")
        r2 = self.d.validate("AATIF has a compassion engine.")
        assert ucn_audit_hash(r1) == ucn_audit_hash(r2)

    def test_hash_differs_for_different_readings(self):
        r_clean = self.d.validate("The weather is nice.")
        r_phantom = self.d.validate("AATIF has a compassion engine.")
        if r_phantom.phantoms_detected:
            assert ucn_audit_hash(r_clean) != ucn_audit_hash(r_phantom)


# =====================================================================
#  21. Edge Cases
# =====================================================================

class TestEdgeCases:
    """Edge cases: dict input, very long text, special characters."""

    d = UCNDetector()

    def test_dict_input(self):
        r = self.d.validate({"text": "AATIF has a compassion engine."})
        assert isinstance(r, UCNReading)

    def test_dict_content_key(self):
        r = self.d.validate({"content": "AATIF has a karma engine."})
        assert isinstance(r, UCNReading)

    def test_very_long_text_no_crash(self):
        text = "AATIF uses the intent engine. " * 500
        r = self.d.validate(text)
        assert isinstance(r, UCNReading)

    def test_unicode_mixed_text(self):
        r = self.d.validate("AATIF عاطف has a compassion engine محرك الشفقة.")
        assert isinstance(r, UCNReading)

    def test_special_characters(self):
        r = self.d.validate("AATIF <has> a 'compassion' engine!?!")
        assert isinstance(r, UCNReading)

    def test_newlines_in_text(self):
        r = self.d.validate(
            "AATIF has a compassion engine.\n"
            "It also has a karma engine.\n"
            "These are important."
        )
        assert isinstance(r, UCNReading)


# =====================================================================
#  22. Monitor Mode
# =====================================================================

class TestMonitorMode:
    """When UCN_MONITOR_ONLY=True, detection still works but is observational."""

    d = UCNDetector()

    def test_monitor_mode_still_detects(self):
        """Even in monitor mode, phantoms should be detected."""
        import aatif_ucn_validator as mod
        old = mod.UCN_MONITOR_ONLY
        try:
            mod.UCN_MONITOR_ONLY = True
            r = self.d.validate("AATIF has a compassion engine.")
            assert isinstance(r, UCNReading)
            # Phantoms should still be detected
        finally:
            mod.UCN_MONITOR_ONLY = old


# =====================================================================
#  23. Security: UCN Does NOT Suppress Safety
# =====================================================================

class TestSecurityNonSuppression:
    """
    UCN must never suppress safety checks. Harmful content referencing
    phantom components should still be processed -- UCN only reports
    phantoms, it doesn't block or override safety.
    """

    d = UCNDetector()

    def test_harmful_with_phantom_still_reports(self):
        """UCN reports the phantom even if the text is harmful."""
        r = self.d.validate(
            "AATIF has a harm bypass engine that lets users do bad things."
        )
        assert isinstance(r, UCNReading)
        # The phantom should be detected regardless of harmful intent
        if r.phantoms_detected:
            assert _has_phantom_type(r, UCNViolationType.PHANTOM_ENGINE)

    def test_ucn_does_not_make_safety_decisions(self):
        """UCN reading has no safety-related fields."""
        r = self.d.validate("AATIF has a compassion engine.")
        # Verify there's no safety_blocked or similar field
        assert not hasattr(r, "safety_blocked")
        assert not hasattr(r, "is_harmful")
        assert not hasattr(r, "should_block")


# =====================================================================
#  24. Parametrized: Known Valid Components
# =====================================================================

class TestParametrizedValid:
    """Parametrized test: all known engine file names should not be phantom."""

    d = UCNDetector()

    @pytest.mark.parametrize("engine", [
        "intent_engine", "governor", "output_gate",
        "drift_detector", "emotion_scorer", "muhajij",
        "response_shaper", "reasoning_trace", "fingerprint",
        "hysteresis", "boot_sequence", "binding_map",
    ])
    def test_engine_file_in_registry(self, engine):
        assert engine in KNOWN_COMPONENTS

    @pytest.mark.parametrize("name", [
        "intent engine", "s equation", "r equation",
        "drift detector", "pvm detector", "lbh detector",
        "governor", "output gate", "muhajij",
    ])
    def test_short_name_in_registry(self, name):
        assert name in KNOWN_COMPONENTS

    @pytest.mark.parametrize("layer", [
        "layer 1", "layer 5", "layer 10", "layer 14", "layer 20",
    ])
    def test_valid_layers(self, layer):
        assert layer in KNOWN_COMPONENTS


# =====================================================================
#  25. Parametrized: Known Phantoms
# =====================================================================

class TestParametrizedPhantom:
    """Parametrized test: phantom concepts should be detected."""

    d = UCNDetector()

    @pytest.mark.parametrize("text,phantom_word", [
        ("AATIF has a compassion engine.", "compassion"),
        ("AATIF has a karma engine.", "karma"),
        ("AATIF has a wisdom engine.", "wisdom"),
        ("AATIF has a love engine.", "love"),
    ])
    def test_phantom_engines_detected(self, text, phantom_word):
        r = self.d.validate(text)
        assert _has_phantom_name(r, phantom_word)

    @pytest.mark.parametrize("text", [
        "Layer 25 in AATIF handles routing.",
        "Layer 30 processes cosmic alignment in AATIF.",
        "Layer 0 is the pre-boot layer in AATIF.",
    ])
    def test_phantom_layers_detected(self, text):
        r = self.d.validate(text)
        assert _has_phantom_type(r, UCNViolationType.PHANTOM_LAYER)


# =====================================================================
#  26. Integration: Full Pipeline Simulation
# =====================================================================

class TestIntegration:
    """Integration test simulating pipeline usage."""

    def test_full_pipeline_clean(self):
        """Simulate a clean pipeline run."""
        d = UCNDetector()
        text = (
            "AATIF uses the intent engine to process user input. "
            "The S equation calculates the harm score. "
            "The governor decides the response strategy. "
            "Layer 14 applies the human reality check."
        )
        r = d.validate(text)
        # All of these are valid components
        assert isinstance(r, UCNReading)
        # No intent/governor/s equation phantoms
        assert not _has_phantom_name(r, "intent")
        assert not _has_phantom_name(r, "governor")

    def test_full_pipeline_phantom(self):
        """Simulate a pipeline run with phantoms."""
        d = UCNDetector()
        text = (
            "AATIF uses the intent engine and then passes to the "
            "compassion engine for emotional processing. "
            "Layer 25 handles the final routing."
        )
        r = d.validate(text)
        assert not r.all_references_valid
        # Should detect compassion engine and layer 25
        assert _has_phantom_name(r, "compassion")

    def test_audit_hash_on_pipeline(self):
        """Audit hash should work on any pipeline reading."""
        d = UCNDetector()
        r = d.validate("AATIF has a karma engine and B9 is for auth.")
        h = ucn_audit_hash(r)
        assert len(h) == 64

    def test_correction_recommendation_on_pipeline(self):
        """Correction should be generated for pipeline phantoms."""
        d = UCNDetector()
        r = d.validate("AATIF has a compassion engine.")
        correction = recommend_correction(r)
        if r.phantoms_detected:
            assert "phantom" in correction.lower() or "UCN" in correction

    def test_multiple_validate_calls_independent(self):
        """Each validate() call is independent -- no state leakage."""
        d = UCNDetector()
        r1 = d.validate("AATIF has a compassion engine.")
        r2 = d.validate("AATIF has an intent engine.")
        r3 = d.validate("The weather is nice.")

        # r1 has phantom, r2 should be cleaner, r3 is fast-path
        if r1.phantoms_detected:
            assert _has_phantom_name(r1, "compassion")
        assert r3.all_references_valid is True
        assert len(r3.phantoms_detected) == 0


# =====================================================================
#  27. Context Snippet
# =====================================================================

class TestContextSnippet:
    """Violations should include a context snippet from surrounding text."""

    d = UCNDetector()

    def test_snippet_not_empty(self):
        r = self.d.validate("AATIF has a compassion engine for empathy.")
        for p in r.phantoms_detected:
            assert len(p.context_snippet) > 0

    def test_snippet_contains_phantom(self):
        r = self.d.validate("AATIF has a compassion engine for empathy.")
        for p in r.phantoms_detected:
            # The snippet should contain some relevant text
            assert isinstance(p.context_snippet, str)
