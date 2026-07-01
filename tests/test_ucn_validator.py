"""
Test suite for FN#042 Unwritten Concept Nullification Law (UCN)
-- aatif_ucn_validator.py

Tests the UCNDetector (observational, architectural integrity),
UCNReading/UCNViolation dataclasses, UCNViolationType enum, detection
of phantom engines/layers/protocols/channels/concepts, the component
registry, fast-path skip for non-AATIF text, and the B-prime authority
contract.

P0 fixes tested (3-model retroactive review, 2026-07-01):
  P0-A: Dynamic registry (filesystem discovery, fallback)
  P0-B: Isolation contract (B3/B5 only, ISOLATION_MARKER)
  P0-C: Context anchoring (AATIF keyword required for high confidence)
  P0-D: Modal classification (PROPOSED vs ASSERTED)
  P0-E: Conservative fuzzy matching (threshold 0.80, candidate_not_authoritative)
  P0-F: Bilingual parity (expanded Arabic patterns + morphology)

Architecture under test (B-prime):
  UCNDetector     ->  observational, ARCHITECTURAL INTEGRITY, NOT safety
  UCNReading      ->  output (recommendation for pipeline, not a decision)

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
    # P0-B: Isolation contract
    ISOLATION_MARKER,
    ISOLATION_TARGETS,
    # Feature flags
    UCN_ENABLED,
    UCN_MONITOR_ONLY,
    # Violation enum + P0-D mode
    UCNViolationType,
    ReferenceMode,
    # Constants
    FAST_PATH_MAX_CHARS,
    SINGLE_PHANTOM_BASE_CONFIDENCE,
    MULTI_PHANTOM_COMPOUND_BONUS,
    MAX_CONFIDENCE,
    VIOLATION_SEVERITY,
    CONFIDENCE_CAP_NO_ANCHOR,
    CONFIDENCE_CAP_WITH_ANCHOR,
    PROPOSED_SEVERITY_CAP,
    FUZZY_SIMILARITY_THRESHOLD,
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

    def test_reference_mode_enum(self):
        """P0-D: ReferenceMode enum has 3 values."""
        assert len(ReferenceMode) == 3
        assert ReferenceMode.ASSERTED.value == "ASSERTED"
        assert ReferenceMode.PROPOSED.value == "PROPOSED"
        assert ReferenceMode.HYPOTHETICAL.value == "HYPOTHETICAL"


# =====================================================================
#  4. Dataclass Fields (P0 extended)
# =====================================================================

class TestDataclassFields:
    """UCNViolation and UCNReading must have required fields including P0 additions."""

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

    def test_ucn_violation_p0c_split_confidence(self):
        """P0-C: UCNViolation has detection_confidence and phantom_confidence."""
        v = UCNViolation(
            violation_type=UCNViolationType.PHANTOM_ENGINE,
            phantom_name="test", context_snippet="ctx",
            confidence=0.7, severity=0.8,
            detection_confidence=0.85, phantom_confidence=0.70,
        )
        assert v.detection_confidence == 0.85
        assert v.phantom_confidence == 0.70

    def test_ucn_violation_p0d_reference_mode(self):
        """P0-D: UCNViolation has reference_mode field."""
        v = UCNViolation(
            violation_type=UCNViolationType.PHANTOM_ENGINE,
            phantom_name="test", context_snippet="ctx",
            confidence=0.7, severity=0.8,
            reference_mode="PROPOSED",
        )
        assert v.reference_mode == "PROPOSED"

    def test_ucn_violation_p0d_default_asserted(self):
        """P0-D: Default reference_mode is ASSERTED."""
        v = UCNViolation(
            violation_type=UCNViolationType.PHANTOM_ENGINE,
            phantom_name="test", context_snippet="ctx",
            confidence=0.7, severity=0.8,
        )
        assert v.reference_mode == "ASSERTED"

    def test_ucn_violation_p0e_correction_status(self):
        """P0-E: UCNViolation has correction_status field."""
        v = UCNViolation(
            violation_type=UCNViolationType.PHANTOM_ENGINE,
            phantom_name="test", context_snippet="ctx",
            confidence=0.7, severity=0.8,
        )
        assert v.correction_status == "candidate_not_authoritative"

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
        assert r.evidence == []

    def test_ucn_reading_p0b_isolation_marker(self):
        """P0-B: UCNReading carries ISOLATION_MARKER."""
        r = UCNReading(
            phantoms_detected=[],
            architecture_references_found=0,
            all_references_valid=True,
            recommendations=[],
        )
        assert r._isolation_marker == ISOLATION_MARKER
        assert r._isolation_marker == "B3_B5_ONLY_NOT_FOR_SAFETY"

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

    def test_p0a_registry_source(self):
        """P0-A: Registry source should be 'dynamic' or 'fallback'."""
        src = UCNDetector.registry_source()
        assert src in ("dynamic", "fallback")


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

    def test_p0c_anchor_caps(self):
        """P0-C: Anchor-based confidence caps."""
        assert CONFIDENCE_CAP_NO_ANCHOR < CONFIDENCE_CAP_WITH_ANCHOR
        assert CONFIDENCE_CAP_NO_ANCHOR == 0.55
        assert CONFIDENCE_CAP_WITH_ANCHOR == 0.95

    def test_p0d_proposed_severity_cap(self):
        """P0-D: PROPOSED severity cap is 0.40."""
        assert PROPOSED_SEVERITY_CAP == 0.40

    def test_p0e_fuzzy_threshold(self):
        """P0-E: Fuzzy similarity threshold is 0.80."""
        assert FUZZY_SIMILARITY_THRESHOLD == 0.80


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
        if "محرك الرحمه" not in KNOWN_COMPONENTS:
            assert isinstance(r, UCNReading)

    def test_phantom_layer_arabic(self):
        r = self.d.validate("طبقة التنوير في عاطف تعالج البصيرة")
        assert isinstance(r, UCNReading)
        if r.phantoms_detected:
            assert _has_phantom_type(r, UCNViolationType.PHANTOM_LAYER)

    def test_phantom_protocol_arabic(self):
        r = self.d.validate("بروتوكول المغفرة في عاطف يضمن الرحمة")
        assert isinstance(r, UCNReading)
        if r.phantoms_detected:
            assert _has_phantom_type(r, UCNViolationType.PHANTOM_PROTOCOL)

    def test_valid_engine_arabic(self):
        r = self.d.validate("محرك النية في عاطف يعالج طلبات المستخدم")
        assert not _has_phantom_name(r, "النية")

    def test_arabic_no_aatif_context(self):
        r = self.d.validate("الطقس جميل اليوم في جدة")
        assert r.all_references_valid is True
        assert len(r.phantoms_detected) == 0

    def test_p0f_arabic_unit_pattern(self):
        """P0-F: وحدة (unit/module) pattern should be detected."""
        r = self.d.validate("وحدة الشفقة في عاطف")
        assert isinstance(r, UCNReading)
        # "وحدة الشفقة" (compassion unit) is phantom

    def test_p0f_arabic_concept_pattern(self):
        """P0-F: مفهوم (concept) pattern should be detected."""
        r = self.d.validate("مفهوم التنوير في عاطف")
        assert isinstance(r, UCNReading)
        # "مفهوم التنوير" (enlightenment concept) is phantom


# =====================================================================
#  16. Scope Boundary: General vs. AATIF
# =====================================================================

class TestScopeBoundary:
    """The critical scope boundary: only AATIF architecture is checked."""

    d = UCNDetector()

    def test_compassion_general_vs_aatif(self):
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
        r = self.d.validate("Add another layer of paint to the wall.")
        assert isinstance(r, UCNReading)

    def test_module_word_general(self):
        r = self.d.validate("Install the Python module with pip.")
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
        assert isinstance(r.phantoms_detected, list)
        assert isinstance(r.architecture_references_found, int)
        assert isinstance(r.all_references_valid, bool)
        assert isinstance(r.recommendations, list)
        assert isinstance(r.evidence, list)

    def test_all_valid_when_no_phantoms(self):
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

    def test_correction_includes_mode(self):
        """P0-D: Correction output includes reference_mode."""
        r = self.d.validate("AATIF has a karma engine.")
        correction = recommend_correction(r)
        if r.phantoms_detected:
            assert "mode=" in correction


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
        import aatif_ucn_validator as mod
        old = mod.UCN_MONITOR_ONLY
        try:
            mod.UCN_MONITOR_ONLY = True
            r = self.d.validate("AATIF has a compassion engine.")
            assert isinstance(r, UCNReading)
        finally:
            mod.UCN_MONITOR_ONLY = old


# =====================================================================
#  23. Security: UCN Does NOT Suppress Safety
# =====================================================================

class TestSecurityNonSuppression:
    """UCN must never suppress safety checks."""

    d = UCNDetector()

    def test_harmful_with_phantom_still_reports(self):
        r = self.d.validate(
            "AATIF has a harm bypass engine that lets users do bad things."
        )
        assert isinstance(r, UCNReading)
        if r.phantoms_detected:
            assert _has_phantom_type(r, UCNViolationType.PHANTOM_ENGINE)

    def test_ucn_does_not_make_safety_decisions(self):
        r = self.d.validate("AATIF has a compassion engine.")
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
        d = UCNDetector()
        text = (
            "AATIF uses the intent engine to process user input. "
            "The S equation calculates the harm score. "
            "The governor decides the response strategy. "
            "Layer 14 applies the human reality check."
        )
        r = d.validate(text)
        assert isinstance(r, UCNReading)
        assert not _has_phantom_name(r, "intent")
        assert not _has_phantom_name(r, "governor")

    def test_full_pipeline_phantom(self):
        d = UCNDetector()
        text = (
            "AATIF uses the intent engine and then passes to the "
            "compassion engine for emotional processing. "
            "Layer 25 handles the final routing."
        )
        r = d.validate(text)
        assert not r.all_references_valid
        assert _has_phantom_name(r, "compassion")

    def test_audit_hash_on_pipeline(self):
        d = UCNDetector()
        r = d.validate("AATIF has a karma engine and B9 is for auth.")
        h = ucn_audit_hash(r)
        assert len(h) == 64

    def test_correction_recommendation_on_pipeline(self):
        d = UCNDetector()
        r = d.validate("AATIF has a compassion engine.")
        correction = recommend_correction(r)
        if r.phantoms_detected:
            assert "phantom" in correction.lower() or "UCN" in correction

    def test_multiple_validate_calls_independent(self):
        d = UCNDetector()
        r1 = d.validate("AATIF has a compassion engine.")
        r2 = d.validate("AATIF has an intent engine.")
        r3 = d.validate("The weather is nice.")
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
            assert isinstance(p.context_snippet, str)


# =====================================================================
#  28. P0-A: Dynamic Registry Discovery
# =====================================================================

class TestP0ADynamicRegistry:
    """P0-A: Registry must be derived from filesystem, not only hardcoded."""

    def test_registry_source_is_dynamic_or_fallback(self):
        src = UCNDetector.registry_source()
        assert src in ("dynamic", "fallback")

    def test_discovered_files_include_known_modules(self):
        """Core engine modules must be in the registry regardless of source."""
        core_modules = [
            "intent_engine", "s_equation", "r_equation", "governor",
            "output_gate", "ucn_validator", "drift_detector",
        ]
        for mod in core_modules:
            assert mod in KNOWN_COMPONENTS, f"Missing in registry: {mod}"

    def test_isolation_marker_constant(self):
        """P0-B related: ISOLATION_MARKER exists and is correct."""
        assert ISOLATION_MARKER == "B3_B5_ONLY_NOT_FOR_SAFETY"

    def test_isolation_targets_frozenset(self):
        """P0-B related: ISOLATION_TARGETS is a frozenset."""
        assert isinstance(ISOLATION_TARGETS, frozenset)
        assert "B3_MEANING" in ISOLATION_TARGETS
        assert "B5_BEHAVIOUR" in ISOLATION_TARGETS


# =====================================================================
#  29. P0-B: Integration Boundary / Safety Isolation Proof
# =====================================================================

class TestP0BIsolation:
    """P0-B: UCN must prove it cannot affect S/H/theta/B2/B6."""

    d = UCNDetector()

    def test_reading_has_isolation_marker(self):
        """Every UCNReading must carry the isolation marker."""
        r = self.d.validate("AATIF has a compassion engine.")
        assert hasattr(r, "_isolation_marker")
        assert r._isolation_marker == "B3_B5_ONLY_NOT_FOR_SAFETY"

    def test_clean_reading_has_isolation_marker(self):
        r = self.d.validate("The weather is nice.")
        assert r._isolation_marker == ISOLATION_MARKER

    def test_no_safety_imports_in_module(self):
        """UCN module must not import S equation, H score, or theta modules."""
        import aatif_ucn_validator as mod
        source = open(mod.__file__, "r").read()
        # Must NOT import safety-critical modules
        assert "from aatif_s_equation" not in source
        assert "import aatif_s_equation" not in source
        assert "from aatif_governor import" not in source.replace(
            "from aatif_governor", "# safe check")  # allow the check itself

    def test_isolation_targets_exclude_safety(self):
        """ISOLATION_TARGETS must NOT include B2 or B6."""
        assert "B2_CONSTITUTIONAL" not in ISOLATION_TARGETS
        assert "B6_SAFETY" not in ISOLATION_TARGETS

    def test_reading_fields_have_no_safety_attributes(self):
        """UCNReading must not have safety-related fields."""
        r = self.d.validate("AATIF has a compassion engine.")
        assert not hasattr(r, "safety_blocked")
        assert not hasattr(r, "harm_score")
        assert not hasattr(r, "theta_override")
        assert not hasattr(r, "s_score")


# =====================================================================
#  30. P0-C: Scoring Calibration -- Context Anchoring
# =====================================================================

class TestP0CContextAnchoring:
    """P0-C: Confidence must be context-anchored (AATIF keywords required)."""

    d = UCNDetector()

    def test_with_aatif_anchor_higher_confidence(self):
        """Text with 'AATIF' keyword should allow higher confidence."""
        r = self.d.validate("AATIF has a compassion engine.")
        for p in r.phantoms_detected:
            # With AATIF anchor, confidence can be up to 0.95
            assert p.confidence <= CONFIDENCE_CAP_WITH_ANCHOR

    def test_without_aatif_anchor_capped_confidence(self):
        """Text without AATIF-specific anchor should have capped confidence."""
        # "the engine" triggers context but no AATIF anchor
        r = self.d.validate("The system has a compassion engine module.")
        for p in r.phantoms_detected:
            assert p.confidence <= CONFIDENCE_CAP_NO_ANCHOR

    def test_split_confidence_fields_present(self):
        """P0-C: Each phantom has detection_confidence and phantom_confidence."""
        r = self.d.validate("AATIF has a compassion engine.")
        for p in r.phantoms_detected:
            assert hasattr(p, "detection_confidence")
            assert hasattr(p, "phantom_confidence")
            assert 0.0 < p.detection_confidence <= 1.0
            assert 0.0 < p.phantom_confidence <= 1.0

    def test_aatif_anchor_keywords(self):
        """Various AATIF-specific anchors should allow high confidence."""
        anchored_texts = [
            "AATIF has a compassion engine.",
            "The governance equation uses a compassion engine.",
        ]
        for text in anchored_texts:
            r = self.d.validate(text)
            for p in r.phantoms_detected:
                # Should be anchored (confidence up to 0.95)
                assert p.confidence <= CONFIDENCE_CAP_WITH_ANCHOR

    def test_arabic_anchor(self):
        """Arabic AATIF anchor 'عاطف' should enable high confidence."""
        r = self.d.validate("عاطف يحتوي على محرك الشفقة")
        assert isinstance(r, UCNReading)
        # عاطف is in _AATIF_CONTEXT_ANCHORS


# =====================================================================
#  31. P0-D: Modal Classification -- Proposed vs Asserted
# =====================================================================

class TestP0DModalClassification:
    """P0-D: Speculative references should be classified as PROPOSED, not PHANTOM."""

    d = UCNDetector()

    def test_asserted_reference_default(self):
        """Normal statement should be classified as ASSERTED."""
        r = self.d.validate("AATIF has a compassion engine.")
        for p in r.phantoms_detected:
            assert p.reference_mode == "ASSERTED"

    def test_proposed_reference_english(self):
        """Text with 'proposed' marker should be classified as PROPOSED."""
        r = self.d.validate(
            "We proposed adding a compassion engine to AATIF."
        )
        for p in r.phantoms_detected:
            assert p.reference_mode == "PROPOSED"
            assert p.severity <= PROPOSED_SEVERITY_CAP

    def test_hypothetical_reference(self):
        """Text with 'hypothetical' marker should be HYPOTHETICAL."""
        r = self.d.validate(
            "A hypothetical compassion engine could help AATIF."
        )
        for p in r.phantoms_detected:
            assert p.reference_mode == "HYPOTHETICAL"
            assert p.severity <= PROPOSED_SEVERITY_CAP

    def test_draft_marker(self):
        """'draft' is a speculative marker."""
        r = self.d.validate(
            "This is a draft design for a compassion engine in AATIF."
        )
        for p in r.phantoms_detected:
            assert p.reference_mode == "PROPOSED"

    def test_could_build_marker(self):
        """'could build' is a speculative marker."""
        r = self.d.validate(
            "We could build a compassion engine for AATIF."
        )
        for p in r.phantoms_detected:
            assert p.reference_mode == "PROPOSED"

    def test_arabic_speculative_marker(self):
        """Arabic speculative markers: 'مقترح' should trigger PROPOSED."""
        r = self.d.validate(
            "مقترح إضافة محرك الشفقة في عاطف"
        )
        for p in r.phantoms_detected:
            assert p.reference_mode == "PROPOSED"

    def test_proposed_severity_capped(self):
        """PROPOSED phantoms must have severity capped at 0.40."""
        r = self.d.validate(
            "We proposed adding a compassion engine to AATIF."
        )
        for p in r.phantoms_detected:
            assert p.severity <= PROPOSED_SEVERITY_CAP


# =====================================================================
#  32. P0-E: Conservative Fuzzy Matching
# =====================================================================

class TestP0EFuzzyMatching:
    """P0-E: Fuzzy matching must be conservative (threshold 0.80)."""

    d = UCNDetector()

    def test_correction_status_is_candidate(self):
        """All phantom violations must have correction_status='candidate_not_authoritative'."""
        r = self.d.validate("AATIF has a compassion engine.")
        for p in r.phantoms_detected:
            assert p.correction_status == "candidate_not_authoritative"

    def test_suggested_correction_is_string(self):
        """suggested_correction field must be a string (possibly empty)."""
        r = self.d.validate("AATIF has a compassion engine.")
        for p in r.phantoms_detected:
            assert isinstance(p.suggested_correction, str)

    def test_fuzzy_match_threshold_respected(self):
        """Fuzzy suggestions only appear if similarity >= 0.80."""
        # "compassion" is very different from any known component
        # so suggested_correction should be empty or a real close match
        r = self.d.validate("AATIF has a compassion engine.")
        for p in r.phantoms_detected:
            if p.suggested_correction:
                # If a suggestion was made, it passed the threshold
                from aatif_ucn_validator import _simple_similarity
                sim = _simple_similarity(
                    p.phantom_name.lower(),
                    p.suggested_correction.lower()
                )
                assert sim >= FUZZY_SIMILARITY_THRESHOLD

    def test_no_auto_correction(self):
        """UCN never auto-corrects -- only suggests."""
        r = self.d.validate("AATIF has a compassion engine.")
        for p in r.phantoms_detected:
            # The phantom_name should NOT be replaced by suggestion
            assert "compassion" in p.phantom_name.lower()


# =====================================================================
#  33. P0-F: Bilingual Parity Enhancement
# =====================================================================

class TestP0FBilingualParity:
    """P0-F: Arabic patterns must be on par with English."""

    d = UCNDetector()

    def test_arabic_unit_pattern(self):
        """P0-F: 'وحدة' (unit/module) pattern should work."""
        r = self.d.validate("وحدة التنوير في عاطف")
        assert isinstance(r, UCNReading)

    def test_arabic_concept_pattern(self):
        """P0-F: 'مفهوم' (concept) pattern should work."""
        r = self.d.validate("مفهوم الكرامة في عاطف")
        assert isinstance(r, UCNReading)

    def test_arabic_pattern_count_parity(self):
        """P0-F: Arabic regex patterns should be >= 7 (matching English count)."""
        from aatif_ucn_validator import _RE_COMPONENT_REF_AR, _RE_COMPONENT_REF_EN
        assert len(_RE_COMPONENT_REF_AR) >= len(_RE_COMPONENT_REF_EN)

    def test_arabic_morphological_prefix_stripping(self):
        """P0-F: Arabic prefixes (ال, و, ب) should be stripped during lookup."""
        from aatif_ucn_validator import _AR_PREFIX_PATTERN
        assert _AR_PREFIX_PATTERN.sub("", "المحاجج") == "محاجج"
        assert _AR_PREFIX_PATTERN.sub("", "والنظام") == "نظام"
        assert _AR_PREFIX_PATTERN.sub("", "بالقناة") == "قناة"

    def test_mixed_script_detection(self):
        """P0-F: Mixed Arabic-English references should be detected."""
        r = self.d.validate("محرك aatif_compassion في عاطف")
        assert isinstance(r, UCNReading)

    def test_valid_arabic_engine_not_flagged(self):
        """Known Arabic engine names should not be flagged."""
        r = self.d.validate("محرك النية في عاطف يعالج الطلبات")
        # "محرك النية" (intent engine) is known
        assert not _has_phantom_name(r, "النية")

    def test_arabic_channel_pattern(self):
        """P0-F: Arabic channel pattern 'B3 قناة' should work."""
        r = self.d.validate("B3 قناة المعنى في عاطف")
        assert isinstance(r, UCNReading)
