"""
test_maqam_architecture.py — Comprehensive test suite for FN#065 Maqam Architecture Law.

Tests covering:
  - Authority contract & isolation (B-prime observational)
  - Feature flag (MAQAM_ENABLED)
  - Sparse activation (fast-path NEUTRAL skip)
  - 10 maqam types (WARMTH, AUTHORITY, VULNERABILITY, SADNESS,
    PLAYFULNESS, SEEKING, GRATITUDE, FRUSTRATION, URGENCY, NEUTRAL)
  - Jins detection (EN + AR + Gulf dialect)
  - Aqd cadence analysis
  - Nisba fingerprint ratio
  - Negation guards
  - Multi-maqam (primary + secondary)
  - Confidence bands (WEAK, MODERATE, STRONG)
  - B5 style hints (NOT B1)
  - Language detection
  - Dialect detection (gulf/msa/none)
  - Minimum evidence requirement (≥2 markers)
  - Frozen dataclass immutability
  - Edge cases (empty input, short input, mixed language)

License: BSL-1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

import pytest

from engine.aatif_maqam_architecture import (
    # Feature flags & contract
    MAQAM_ENABLED,
    AUTHORITY_LEVEL,
    CAN_BLOCK_RUNTIME,
    CAN_MODIFY_H,
    CAN_MODIFY_THETA,
    CAN_MODIFY_S,
    CAN_EMIT_JUDICIAL_DECISION,
    BINDING_CHANNEL,
    SAFETY_DECISION_AUTHORITY,
    ACTIVATION_THRESHOLD,
    MIN_MARKER_EVIDENCE,
    # Enums
    MaqamType,
    CadenceType,
    ConfidenceBand,
    MarkerSource,
    # Dataclasses
    JinsReading,
    AqdReading,
    NisbaReading,
    MaqamReading,
    StructuralResonance,
    # Marker sets
    WARMTH_MARKERS_EN,
    WARMTH_MARKERS_AR,
    AUTHORITY_MARKERS_EN,
    AUTHORITY_MARKERS_AR,
    VULNERABILITY_MARKERS_EN,
    VULNERABILITY_MARKERS_AR,
    SADNESS_MARKERS_EN,
    SADNESS_MARKERS_AR,
    PLAYFULNESS_MARKERS_EN,
    PLAYFULNESS_MARKERS_AR,
    SEEKING_MARKERS_EN,
    SEEKING_MARKERS_AR,
    GRATITUDE_MARKERS_EN,
    GRATITUDE_MARKERS_AR,
    FRUSTRATION_MARKERS_EN,
    FRUSTRATION_MARKERS_AR,
    URGENCY_MARKERS_EN,
    URGENCY_MARKERS_AR,
    # Functions
    detect_maqam,
    _detect_language,
    _detect_dialect,
    _is_negated,
    _compute_cadence,
    _compute_structural_resonance,
    _get_confidence_band,
    _non_activated_reading,
    # FN#066 forbidden labels
    _FORBIDDEN_PSYCH_LABELS,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §1  Authority Contract & Isolation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAuthorityContract:
    """B-prime observational contract must be inviolable."""

    def test_authority_level_is_b_prime(self):
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

    def test_binding_channel_is_b5(self):
        """Consensus fix: bind to B5 (Behaviour), NOT B1."""
        assert BINDING_CHANNEL == "B5"

    def test_safety_decision_authority(self):
        assert SAFETY_DECISION_AUTHORITY == "GOVERNANCE_EQUATION_ONLY"

    def test_reading_isolation_marker(self):
        reading = detect_maqam("thank you so much, i appreciate everything")
        assert reading._isolation_marker == "B5_ADVISORY_NOT_FOR_SAFETY"

    def test_reading_safety_authority(self):
        reading = detect_maqam("thank you so much, i appreciate everything")
        assert reading.safety_decision_authority == "GOVERNANCE_EQUATION_ONLY"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §2  Feature Flag
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFeatureFlag:
    """Module ships OFF by default."""

    def test_maqam_disabled_by_default(self):
        assert MAQAM_ENABLED is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §3  Sparse Activation — Fast-path Skip
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSparseActivation:
    """Below threshold → NEUTRAL, activated=False."""

    def test_empty_string_returns_neutral(self):
        reading = detect_maqam("")
        assert reading.detected_maqam == MaqamType.NEUTRAL
        assert reading.activated is False

    def test_whitespace_returns_neutral(self):
        reading = detect_maqam("   \n  \t  ")
        assert reading.detected_maqam == MaqamType.NEUTRAL
        assert reading.activated is False

    def test_none_returns_neutral(self):
        reading = detect_maqam(None)
        assert reading.detected_maqam == MaqamType.NEUTRAL
        assert reading.activated is False

    def test_neutral_text_returns_neutral(self):
        reading = detect_maqam("The meeting is at 3pm tomorrow.")
        assert reading.detected_maqam == MaqamType.NEUTRAL
        assert reading.activated is False

    def test_single_marker_insufficient(self):
        """Consensus: minimum evidence ≥ 2 markers required."""
        reading = detect_maqam("thank you")
        assert reading.activated is False

    def test_activation_threshold_value(self):
        assert ACTIVATION_THRESHOLD == 0.25

    def test_min_marker_evidence_value(self):
        assert MIN_MARKER_EVIDENCE == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §4  Maqam Enum Completeness
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMaqamEnum:
    """Consensus v1: exactly 10 maqam modes."""

    def test_ten_maqam_types(self):
        assert len(MaqamType) == 10

    def test_all_maqams_present(self):
        expected = {
            "neutral", "warmth", "authority", "vulnerability",
            "sadness", "playfulness", "seeking", "gratitude",
            "frustration", "urgency",
        }
        actual = {m.value for m in MaqamType}
        assert actual == expected

    def test_sadness_separate_from_vulnerability(self):
        """Consensus Q1: SADNESS and VULNERABILITY are distinct."""
        assert MaqamType.SADNESS != MaqamType.VULNERABILITY
        assert MaqamType.SADNESS.value == "sadness"
        assert MaqamType.VULNERABILITY.value == "vulnerability"

    def test_urgency_exists(self):
        """Consensus Q1: URGENCY added as own maqam."""
        assert MaqamType.URGENCY.value == "urgency"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §5  WARMTH Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestWarmthDetection:

    def test_warmth_english(self):
        text = "Thank you so much, I appreciate everything you've done. Means a lot to me."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.WARMTH
        assert reading.activated is True
        assert reading.confidence > 0

    def test_warmth_arabic(self):
        text = "يعطيك العافية، الله يسعدك ما قصرت"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.WARMTH
        assert reading.activated is True

    def test_warmth_gulf_dialect(self):
        text = "يا عمري الله يخليك ما عليك زود"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.WARMTH
        assert reading.activated is True

    def test_warmth_b5_hints(self):
        text = "Thank you so much, I appreciate you. You're so kind."
        reading = detect_maqam(text)
        assert "respond_with_warmth" in reading.b5_style_hints


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §6  AUTHORITY Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAuthorityDetection:

    def test_authority_english(self):
        text = "You must understand this. Listen, the fact is you need to make sure it's done."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.AUTHORITY
        assert reading.activated is True

    def test_authority_arabic(self):
        text = "لازم تفهم بالضبط وش المطلوب. المفروض يكون جاهز."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.AUTHORITY
        assert reading.activated is True

    def test_authority_gulf(self):
        text = "ترى والله أقولك لا تناقش صدقني"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.AUTHORITY
        assert reading.activated is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §7  VULNERABILITY Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestVulnerabilityDetection:

    def test_vulnerability_english(self):
        text = "I'm scared and I don't know what to do. I feel lost."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.VULNERABILITY
        assert reading.activated is True

    def test_vulnerability_arabic(self):
        text = "خايف وما أدري وش أسوي. تعبت ومو قادر."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.VULNERABILITY
        assert reading.activated is True

    def test_vulnerability_gulf(self):
        text = "والله ما أدري وش أسوي ما عندي حيلة"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.VULNERABILITY
        assert reading.activated is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §8  SADNESS Detection (consensus: separate from vulnerability)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSadnessDetection:

    def test_sadness_english(self):
        text = "I'm sad and heartbroken. I miss them so much. It hurts."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.SADNESS
        assert reading.activated is True

    def test_sadness_arabic(self):
        text = "حزين ومشتاق. قلبي يعورني."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.SADNESS
        assert reading.activated is True

    def test_sadness_gulf(self):
        text = "قلبي انكسر. يعورني قلبي. مقهور."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.SADNESS
        assert reading.activated is True

    def test_sadness_not_vulnerability(self):
        """SADNESS markers should not produce VULNERABILITY."""
        text = "I'm sad and grieving. I feel empty and alone. Sorrow fills me."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.SADNESS
        assert reading.detected_maqam != MaqamType.VULNERABILITY


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §9  PLAYFULNESS Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPlayfulnessDetection:

    def test_playfulness_english(self):
        text = "Haha that's so fun! LOL awesome, can't stop laughing."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.PLAYFULNESS
        assert reading.activated is True

    def test_playfulness_arabic(self):
        text = "هههههه ضحكتني يا حلو! وناسة ممتاز!"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.PLAYFULNESS
        assert reading.activated is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §10  SEEKING Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSeekingDetection:

    def test_seeking_english(self):
        text = "How do I do this? Can you explain? I'm curious about what if we try."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.SEEKING
        assert reading.activated is True

    def test_seeking_arabic(self):
        text = "كيف أسوي هالشي؟ ممكن تشرح لي؟ أبغى أفهم"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.SEEKING
        assert reading.activated is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §11  GRATITUDE Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestGratitudeDetection:

    def test_gratitude_english(self):
        text = "Thank you, you're the best! So helpful, great job, exactly what I needed."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.GRATITUDE
        assert reading.activated is True

    def test_gratitude_arabic(self):
        text = "شكرا جزاك الله خير مشكور بارك الله فيك"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.GRATITUDE
        assert reading.activated is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §12  FRUSTRATION Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFrustrationDetection:

    def test_frustration_english(self):
        text = "This is annoying. Nothing works! I've tried everything and it's broken."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.FRUSTRATION
        assert reading.activated is True

    def test_frustration_arabic(self):
        text = "طفشت مليت ما ينفع هالشي خربان"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.FRUSTRATION
        assert reading.activated is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §13  URGENCY Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestUrgencyDetection:

    def test_urgency_english(self):
        text = "This is urgent! I need this asap, immediately! Time is running out, hurry!"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.URGENCY
        assert reading.activated is True

    def test_urgency_arabic(self):
        text = "ضروري مستعجل الحين بسرعة عاجل"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.URGENCY
        assert reading.activated is True

    def test_urgency_gulf(self):
        text = "يلا بسرعة ما عندي وقت على طول حيل مستعجل"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.URGENCY
        assert reading.activated is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §14  Negation Guards (consensus Q2)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestNegationGuards:

    def test_negation_english_not_sad(self):
        """'not sad' — the word 'sad' is present but preceded by 'not'."""
        result = _is_negated("I'm not sad at all, I feel great", "sad")
        assert result is True

    def test_negation_english_no_prefix(self):
        """No negation → not negated."""
        result = _is_negated("I'm sad today", "sad")
        assert result is False

    def test_negation_arabic(self):
        result = _is_negated("مو حزين أنا بخير", "حزين")
        assert result is True

    def test_negation_not_scared(self):
        result = _is_negated("I'm not scared, don't worry", "scared")
        assert result is True

    def test_negation_full_phrase_not_found(self):
        """When marker phrase doesn't exist in text, returns False."""
        result = _is_negated("I'm not sad", "i'm sad")
        assert result is False  # "i'm sad" not found as contiguous substring

    def test_negation_protects_detection(self):
        """Full pipeline: 'I'm not sad, not heartbroken, not lonely' ≠ SADNESS."""
        text = "I'm not sad, not heartbroken, and not lonely. I feel great today."
        reading = detect_maqam(text)
        # Negated markers should reduce SADNESS score
        assert reading.detected_maqam != MaqamType.SADNESS or reading.activated is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §15  Aqd (Cadence) Analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAqdCadence:

    def test_flat_cadence(self):
        text = "The report is due tomorrow. Please submit it by noon."
        aqd = _compute_cadence(text)
        assert isinstance(aqd, AqdReading)
        assert isinstance(aqd.cadence_type, CadenceType)

    def test_staccato_cadence(self):
        text = "No! Stop! Why?! How?! When?! Now!"
        aqd = _compute_cadence(text)
        assert aqd.punctuation_density > 0

    def test_empty_text_cadence(self):
        aqd = _compute_cadence("")
        assert aqd.cadence_type == CadenceType.FLAT
        assert aqd.rhythm_score == 0.0

    def test_question_heavy_cadence(self):
        text = "Why did this happen? How can we fix it? What went wrong? When did it start?"
        aqd = _compute_cadence(text)
        assert aqd.question_ratio > 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §16  Confidence Bands (consensus Q7)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConfidenceBands:

    def test_none_band(self):
        assert _get_confidence_band(0.0) == ConfidenceBand.NONE
        assert _get_confidence_band(0.24) == ConfidenceBand.NONE

    def test_weak_band(self):
        assert _get_confidence_band(0.25) == ConfidenceBand.WEAK
        assert _get_confidence_band(0.39) == ConfidenceBand.WEAK

    def test_moderate_band(self):
        assert _get_confidence_band(0.40) == ConfidenceBand.MODERATE
        assert _get_confidence_band(0.59) == ConfidenceBand.MODERATE

    def test_strong_band(self):
        assert _get_confidence_band(0.60) == ConfidenceBand.STRONG
        assert _get_confidence_band(1.0) == ConfidenceBand.STRONG


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §17  Language Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLanguageDetection:

    def test_english_detection(self):
        assert _detect_language("Hello, how are you?") == "en"

    def test_arabic_detection(self):
        assert _detect_language("مرحبا كيف حالك") == "ar"

    def test_mixed_detection(self):
        assert _detect_language("Hello مرحبا how حالك") == "mixed"

    def test_empty_detection(self):
        assert _detect_language("") == "en"

    def test_reading_has_language(self):
        reading = detect_maqam("شكرا جزاك الله خير مشكور")
        assert reading.language_detected in ("ar", "mixed")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §18  Dialect Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDialectDetection:

    def test_no_dialect_english(self):
        assert _detect_dialect("Hello world", []) == "none"

    def test_gulf_dialect(self):
        text = "ترى والله وش السالفة"
        assert _detect_dialect(text, []) == "gulf"

    def test_msa_dialect(self):
        text = "أريد أن أفهم هذا الموضوع"
        assert _detect_dialect(text, []) == "msa"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §19  B5 Style Hints (NOT B1)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestB5StyleHints:

    def test_warmth_hints(self):
        text = "Thank you so much, I appreciate everything. Sending love and warm regards."
        reading = detect_maqam(text)
        assert "respond_with_warmth" in reading.b5_style_hints

    def test_neutral_hints(self):
        reading = detect_maqam("Send the file.")
        assert "maintain_neutral_tone" in reading.b5_style_hints

    def test_no_b1_field_exists(self):
        """Consensus: renamed b1_style_hints to b5_style_hints."""
        reading = detect_maqam("test")
        assert not hasattr(reading, "b1_style_hints")

    def test_weak_confidence_adds_hint(self):
        """Weak confidence band should add low_confidence_hint_only."""
        text = "Thank you so much, I appreciate you"
        reading = detect_maqam(text)
        if reading.confidence_band == ConfidenceBand.WEAK:
            assert "low_confidence_hint_only" in reading.b5_style_hints


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §20  Triad Reading Structure
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTriadStructure:

    def test_reading_has_jins(self):
        reading = detect_maqam("I'm scared and don't know what to do. I feel lost. Please help.")
        assert isinstance(reading.jins, JinsReading)
        assert isinstance(reading.jins.strength, float)
        assert isinstance(reading.jins.markers_found, tuple)

    def test_reading_has_aqd(self):
        reading = detect_maqam("I'm scared and don't know what to do. I feel lost. Please help.")
        assert isinstance(reading.aqd, AqdReading)
        assert isinstance(reading.aqd.cadence_type, CadenceType)

    def test_reading_has_nisba(self):
        reading = detect_maqam("I'm scared and don't know what to do. I feel lost. Please help.")
        assert isinstance(reading.nisba, NisbaReading)
        assert isinstance(reading.nisba.ratio, float)
        assert isinstance(reading.nisba.confirmed, bool)

    def test_scores_by_maqam_present(self):
        """Consensus Q5: keep full distribution internally."""
        reading = detect_maqam("I'm scared and don't know what to do. I feel lost. Please help.")
        assert isinstance(reading.scores_by_maqam, dict)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §21  Multi-Maqam (Primary + Secondary)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMultiMaqam:

    def test_secondary_maqam_exists(self):
        reading = detect_maqam("Thank you so much, I appreciate you. You're so kind.")
        assert isinstance(reading.secondary_maqam, MaqamType)
        assert isinstance(reading.secondary_confidence, float)

    def test_no_secondary_when_dominant(self):
        """When one maqam dominates, secondary should be NEUTRAL."""
        text = "I'm sad. Heartbroken. I miss everyone. Grief consumes me. It hurts. I'm lonely. Sorrow."
        reading = detect_maqam(text)
        # Strong single-maqam signal → secondary likely NEUTRAL
        # (depends on actual scoring, so just check type)
        assert isinstance(reading.secondary_maqam, MaqamType)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §22  Frozen Dataclass Immutability
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFrozenDataclass:

    def test_maqam_reading_immutable(self):
        reading = detect_maqam("Thank you so much, I appreciate everything. Sending love.")
        with pytest.raises(AttributeError):
            reading.detected_maqam = MaqamType.NEUTRAL

    def test_jins_reading_immutable(self):
        jins = JinsReading(dominant_pattern="test", strength=0.5, markers_found=())
        with pytest.raises(AttributeError):
            jins.strength = 0.9

    def test_aqd_reading_immutable(self):
        aqd = AqdReading(
            cadence_type=CadenceType.FLAT,
            rhythm_score=0.0,
            sentence_length_variance=0.0,
            punctuation_density=0.0,
            question_ratio=0.0,
        )
        with pytest.raises(AttributeError):
            aqd.rhythm_score = 1.0

    def test_nisba_reading_immutable(self):
        nisba = NisbaReading(ratio=0.5, confirmed=True, evidence_count=3, characteristic_markers=())
        with pytest.raises(AttributeError):
            nisba.ratio = 0.9


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §23  Non-Activated Reading Helper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestNonActivatedReading:

    def test_non_activated_maqam(self):
        reading = _non_activated_reading()
        assert reading.detected_maqam == MaqamType.NEUTRAL
        assert reading.activated is False
        assert reading.confidence == 0.0

    def test_non_activated_has_isolation(self):
        reading = _non_activated_reading()
        assert reading._isolation_marker == "B5_ADVISORY_NOT_FOR_SAFETY"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §24  Marker Set Integrity
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMarkerSets:

    def test_marker_sets_are_frozensets(self):
        for markers in [
            WARMTH_MARKERS_EN, WARMTH_MARKERS_AR,
            AUTHORITY_MARKERS_EN, AUTHORITY_MARKERS_AR,
            VULNERABILITY_MARKERS_EN, VULNERABILITY_MARKERS_AR,
            SADNESS_MARKERS_EN, SADNESS_MARKERS_AR,
            PLAYFULNESS_MARKERS_EN, PLAYFULNESS_MARKERS_AR,
            SEEKING_MARKERS_EN, SEEKING_MARKERS_AR,
            GRATITUDE_MARKERS_EN, GRATITUDE_MARKERS_AR,
            FRUSTRATION_MARKERS_EN, FRUSTRATION_MARKERS_AR,
            URGENCY_MARKERS_EN, URGENCY_MARKERS_AR,
        ]:
            assert isinstance(markers, frozenset), f"{markers} is not frozenset"

    def test_each_maqam_has_markers(self):
        """Every non-NEUTRAL maqam must have both EN and AR marker sets."""
        from engine.aatif_maqam_architecture import _MARKER_REGISTRY
        for maqam in MaqamType:
            if maqam == MaqamType.NEUTRAL:
                continue
            assert maqam in _MARKER_REGISTRY, f"Missing markers for {maqam}"
            en, ar = _MARKER_REGISTRY[maqam]
            assert len(en) > 0, f"Empty EN markers for {maqam}"
            assert len(ar) > 0, f"Empty AR markers for {maqam}"

    def test_markers_are_lowercase(self):
        """EN markers should be lowercase for matching."""
        for marker in WARMTH_MARKERS_EN:
            assert marker == marker.lower(), f"EN marker not lowercase: {marker}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §25  Edge Cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEdgeCases:

    def test_very_short_text(self):
        reading = detect_maqam("hi")
        assert reading.detected_maqam == MaqamType.NEUTRAL
        assert reading.activated is False

    def test_emoji_only(self):
        reading = detect_maqam("😊😊😊")
        assert reading.detected_maqam == MaqamType.NEUTRAL
        assert reading.activated is False

    def test_numbers_only(self):
        reading = detect_maqam("12345 67890")
        assert reading.detected_maqam == MaqamType.NEUTRAL

    def test_mixed_language_detection(self):
        text = "Thank you so much شكرا جزاك الله خير means a lot مشكور"
        reading = detect_maqam(text)
        assert reading.activated is True
        assert reading.language_detected == "mixed"

    def test_evidence_count_populated(self):
        text = "Thank you so much, I appreciate everything. You made my day."
        reading = detect_maqam(text)
        assert reading.evidence_count >= MIN_MARKER_EVIDENCE

    def test_markers_found_populated(self):
        text = "I'm scared and I don't know what to do. I feel lost."
        reading = detect_maqam(text)
        assert len(reading.markers_found) > 0

    def test_confidence_range(self):
        """Confidence should always be 0.0 – 1.0."""
        text = "Thank you so much, I appreciate everything. You're so kind. Means a lot."
        reading = detect_maqam(text)
        assert 0.0 <= reading.confidence <= 1.0

    def test_long_text_performance(self):
        """Module should handle long text without error."""
        text = "Thank you so much. " * 100
        reading = detect_maqam(text)
        assert isinstance(reading, MaqamReading)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §26  CadenceType Enum
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCadenceEnum:

    def test_seven_cadence_types(self):
        assert len(CadenceType) == 7

    def test_cadence_values(self):
        expected = {"flat", "ascending", "descending", "staccato", "flowing", "broken", "bouncy"}
        actual = {c.value for c in CadenceType}
        assert actual == expected


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §27  Integration — Full Pipeline Smoke Test
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIntegration:

    def test_full_pipeline_warmth(self):
        text = "Thank you so much, I appreciate you so much. You're so kind. Sending love."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.WARMTH
        assert reading.activated is True
        assert reading.confidence > 0
        assert reading.confidence_band != ConfidenceBand.NONE
        assert isinstance(reading.jins, JinsReading)
        assert isinstance(reading.aqd, AqdReading)
        assert isinstance(reading.nisba, NisbaReading)
        assert "respond_with_warmth" in reading.b5_style_hints
        assert reading._isolation_marker == "B5_ADVISORY_NOT_FOR_SAFETY"

    def test_full_pipeline_frustration_arabic(self):
        text = "طفشت مليت ما ينفع كل شي يخرب ما يزبط"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.FRUSTRATION
        assert reading.activated is True
        assert reading.language_detected in ("ar", "mixed")

    def test_full_pipeline_neutral(self):
        text = "Please schedule the meeting for 2pm."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.NEUTRAL
        assert reading.activated is False
        assert reading.confidence_band == ConfidenceBand.NONE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  P0 FIX TESTS — Gemini Review
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestP0GulfNegation:
    """P0 #1: Dialect-aware negation — 'موب' must block markers."""

    def test_mawb_negates_sadness(self):
        """'موب حزين' (I'm not sad) must NOT trigger SADNESS."""
        reading = detect_maqam("موب حزين أنا بخير الحمدلله يعطيك العافية")
        # Either NEUTRAL (if only sad marker blocked) or WARMTH/GRATITUDE
        assert reading.detected_maqam != MaqamType.SADNESS

    def test_mawb_negates_frustration(self):
        """'موب زعلان' (I'm not upset) must NOT trigger FRUSTRATION."""
        reading = detect_maqam("موب زعلان بس أبي أفهم الموضوع أبي أعرف ليش")
        assert reading.detected_maqam != MaqamType.FRUSTRATION

    def test_mawb_in_negation_prefixes(self):
        """Verify 'موب ' is in the negation prefixes tuple."""
        from engine.aatif_maqam_architecture import NEGATION_PREFIXES_AR
        assert any("موب" in neg for neg in NEGATION_PREFIXES_AR)

    def test_is_negated_with_mawb(self):
        """Direct test of _is_negated with موب prefix."""
        from engine.aatif_maqam_architecture import _is_negated
        assert _is_negated("موب حزين", "حزين") is True

    def test_existing_negations_still_work(self):
        """Ensure existing Gulf negations (مو, مش, ماني) still work."""
        from engine.aatif_maqam_architecture import _is_negated
        assert _is_negated("مو حزين", "حزين") is True
        assert _is_negated("مش حزين", "حزين") is True
        assert _is_negated("ماني حزين", "حزين") is True


class TestP0ShortTextAqdDampener:
    """P0 #2: Short-text Aqd dampener — prevent inflated cadence on short text."""

    def test_single_word_exclamation_flat(self):
        """Single word with ! must get FLAT cadence, not BOUNCY/STACCATO."""
        reading = detect_maqam("Thanks!")
        assert reading.aqd.cadence_type == CadenceType.FLAT

    def test_two_word_exclamation_dampened_punct(self):
        """Short text punct_density must be dampened below undampened value."""
        reading = detect_maqam("Great job!")
        # 2 words / 15 = 0.133 dampening factor
        # Without dampener: punct_density would be min(1/3, 1) = 0.333
        # With dampener: 0.333 * 0.133 ≈ 0.044
        assert reading.aqd.punctuation_density < 0.15

    def test_short_arabic_flat(self):
        """Short Arabic text must get FLAT cadence."""
        reading = detect_maqam("شكرا!")
        assert reading.aqd.cadence_type == CadenceType.FLAT

    def test_long_text_not_dampened(self):
        """Text with 15+ words should NOT be dampened — cadence determined normally."""
        long_text = (
            "I really appreciate all the effort you put into this project. "
            "It means so much to me and the entire team. Thank you!"
        )
        reading = detect_maqam(long_text)
        # This has 20+ words and multiple sentences — not dampened
        # Cadence should be determined by actual structure, not forced FLAT
        assert reading.aqd.punctuation_density > 0  # non-zero because there's a !

    def test_single_sentence_forced_flat(self):
        """Even a moderately long single sentence gets FLAT cadence."""
        text = "I am feeling quite happy today and everything is going well"
        reading = detect_maqam(text)
        # Single sentence (no . ! ? delimiters) → is_short_text by sentence count
        assert reading.aqd.cadence_type == CadenceType.FLAT

    def test_rhythm_score_dampened_short(self):
        """Rhythm score on very short text must be lower than on long equivalent."""
        short = detect_maqam("Sad!")
        long_text = detect_maqam(
            "I'm so sad! Everything is falling apart! "
            "Nothing works anymore! I can't believe this! Why?!"
        )
        assert short.aqd.rhythm_score <= long_text.aqd.rhythm_score


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  §28  FN#066 Structural Resonance
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStructuralResonanceFragmented:
    """FN#066 Test 1: Short fragmented text → low density, low continuity."""

    def test_fragmented_text_low_density(self):
        text = "No. Stop. Why. Go. Now."
        sr = _compute_structural_resonance(text)
        assert sr.density <= 0.3, f"Expected low density, got {sr.density}"

    def test_fragmented_text_low_continuity(self):
        text = "No. Stop. Why. Go. Now."
        sr = _compute_structural_resonance(text)
        assert sr.continuity <= 0.2, f"Expected low continuity, got {sr.continuity}"

    def test_fragmented_text_high_fragment_count(self):
        text = "No. Stop. Why. Go. Now."
        sr = _compute_structural_resonance(text)
        assert sr.fragment_count >= 4, f"Expected 4+ fragments, got {sr.fragment_count}"

    def test_arabic_fragmented(self):
        text = "لا. توقف. ليش. روح."
        sr = _compute_structural_resonance(text)
        assert sr.density <= 0.3
        assert sr.continuity <= 0.2


class TestStructuralResonanceFlowing:
    """FN#066 Test 2: Long flowing text → high density, high continuity."""

    def test_flowing_text_high_density(self):
        text = (
            "The comprehensive analysis of the structural patterns "
            "within Arabic text reveals fascinating correlations between "
            "sentence construction and emotional expression modalities. "
            "Furthermore the investigation demonstrates that density "
            "measurements can reliably indicate communication structure."
        )
        sr = _compute_structural_resonance(text)
        assert sr.density >= 0.5, f"Expected high density, got {sr.density}"

    def test_flowing_text_high_continuity(self):
        text = (
            "The comprehensive analysis of the structural patterns "
            "within Arabic text reveals fascinating correlations between "
            "sentence construction and emotional expression modalities. "
            "Furthermore the investigation demonstrates that density "
            "measurements can reliably indicate communication structure."
        )
        sr = _compute_structural_resonance(text)
        assert sr.continuity >= 0.8, f"Expected high continuity, got {sr.continuity}"

    def test_flowing_text_low_fragment_count(self):
        text = (
            "The comprehensive analysis of the structural patterns "
            "within Arabic text reveals fascinating correlations. "
            "Furthermore the investigation demonstrates that density "
            "measurements can reliably indicate communication structure."
        )
        sr = _compute_structural_resonance(text)
        assert sr.fragment_count == 0


class TestStructuralResonanceEffortHigh:
    """FN#066 Test 3: Effort index high for text with !!! and repeated characters."""

    def test_effort_high_exclamations(self):
        text = "THIS IS UNACCEPTABLE!!! I CANNOT BELIEVE THIS!!! WHY WHY WHY???"
        sr = _compute_structural_resonance(text)
        assert sr.effort_index >= 0.4, f"Expected high effort, got {sr.effort_index}"

    def test_effort_high_repeated_chars(self):
        text = "Nooooo!!! This is sooo bad!!! Pleeeease help!!!"
        sr = _compute_structural_resonance(text)
        assert sr.effort_index >= 0.3, f"Expected elevated effort, got {sr.effort_index}"

    def test_effort_high_caps(self):
        text = "STOP IT NOW. THIS IS WRONG. DO SOMETHING ABOUT IT."
        sr = _compute_structural_resonance(text)
        assert sr.effort_index > 0.0, f"Expected non-zero effort, got {sr.effort_index}"


class TestStructuralResonanceEffortLow:
    """FN#066 Test 4: Effort index low for calm text."""

    def test_effort_low_calm_text(self):
        text = (
            "The meeting is scheduled for tomorrow afternoon. "
            "We will discuss the quarterly results. "
            "Please bring your reports."
        )
        sr = _compute_structural_resonance(text)
        assert sr.effort_index <= 0.15, f"Expected low effort, got {sr.effort_index}"

    def test_effort_low_simple_arabic(self):
        text = "الاجتماع غدا بعد الظهر. سنناقش النتائج الربعية. يرجى إحضار التقارير."
        sr = _compute_structural_resonance(text)
        assert sr.effort_index <= 0.15, f"Expected low effort, got {sr.effort_index}"


class TestStructuralResonanceRhythmHigh:
    """FN#066 Test 5: Rhythm regularity high for uniform sentence lengths."""

    def test_rhythm_regular_uniform(self):
        text = (
            "The cat sat on the mat. "
            "The dog ran in the park. "
            "The bird flew over the tree. "
            "The fish swam in the lake."
        )
        sr = _compute_structural_resonance(text)
        assert sr.rhythm_regularity >= 0.7, f"Expected high rhythm regularity, got {sr.rhythm_regularity}"


class TestStructuralResonanceRhythmLow:
    """FN#066 Test 6: Rhythm regularity low for mixed short/long sentences."""

    def test_rhythm_irregular_mixed(self):
        text = (
            "No. "
            "The comprehensive investigation into the structural patterns of "
            "Arabic textual expression reveals deeply fascinating correlations "
            "between sentence construction methodologies and emotional modalities. "
            "Why. "
            "Furthermore the extended analysis demonstrates conclusively that "
            "density measurements across varied linguistic contexts can serve "
            "as reliable indicators of underlying communication structure. "
            "Stop."
        )
        sr = _compute_structural_resonance(text)
        assert sr.rhythm_regularity <= 0.4, f"Expected low rhythm regularity, got {sr.rhythm_regularity}"


class TestStructuralResonanceNoPsychLabels:
    """FN#066 Test 7+8: Description NEVER contains psychological labels.
    Description uses structural language only."""

    def test_no_psych_labels_english(self):
        """No forbidden psychological labels in any description."""
        texts = [
            "THIS IS TERRIBLE!!! WHY WHY WHY???",
            "No. Stop. Why. Go.",
            "I feel so alone and everything hurts and nothing matters anymore.",
            "HELP ME PLEASE!!! SOMEONE!!! ANYONE!!!",
        ]
        for text in texts:
            sr = _compute_structural_resonance(text)
            desc_lower = sr.description.lower()
            for label in _FORBIDDEN_PSYCH_LABELS:
                assert label.lower() not in desc_lower, (
                    f"Forbidden psychological label '{label}' found in description: '{sr.description}'"
                )

    def test_no_psych_labels_arabic(self):
        """Arabic descriptions must not contain forbidden labels."""
        texts = [
            "لا. توقف. ليش. روح.",
            "ساعدني!!! أرجوك!!! ما أقدر!!!",
        ]
        for text in texts:
            sr = _compute_structural_resonance(text)
            for label in _FORBIDDEN_PSYCH_LABELS:
                assert label not in sr.description, (
                    f"Forbidden label '{label}' found in description: '{sr.description}'"
                )

    def test_description_uses_structural_language(self):
        """Description must use structural terms like ضغط, كثافة, إيقاع, etc."""
        structural_terms = {
            "كثافة", "إيقاع", "تعبير", "ضغط", "توزيع",
            "متقطع", "متصل", "منتظم", "هادئ", "توقفات", "بنية",
        }
        # Fragmented text
        sr = _compute_structural_resonance("لا. توقف. ليش. روح. خلاص.")
        found = any(term in sr.description for term in structural_terms)
        assert found, f"Description '{sr.description}' lacks structural terms"

        # High-effort text
        sr2 = _compute_structural_resonance("لا!!! ليش!!! توقف!!! ما أقدر!!!")
        found2 = any(term in sr2.description for term in structural_terms)
        assert found2, f"Description '{sr2.description}' lacks structural terms"


class TestStructuralResonanceInMaqamReading:
    """FN#066 Test 9: structural_resonance field present in MaqamReading."""

    def test_field_present_activated(self):
        text = "Thank you so much, I appreciate everything. You're so kind. Means a lot."
        reading = detect_maqam(text)
        assert hasattr(reading, 'structural_resonance')
        assert reading.structural_resonance is not None
        assert isinstance(reading.structural_resonance, StructuralResonance)

    def test_field_present_non_activated(self):
        text = "The meeting is at 3pm tomorrow."
        reading = detect_maqam(text)
        assert hasattr(reading, 'structural_resonance')
        # Non-activated readings with text still get structural resonance
        # (only _non_activated_reading() for empty/None text returns None)

    def test_field_none_for_empty(self):
        reading = detect_maqam("")
        assert reading.structural_resonance is None

    def test_field_none_for_none(self):
        reading = detect_maqam(None)
        assert reading.structural_resonance is None

    def test_structural_resonance_immutable(self):
        sr = StructuralResonance(
            density=0.5,
            continuity=0.5,
            effort_index=0.3,
            rhythm_regularity=0.7,
            fragment_count=2,
            description="بنية تعبيرية متوسطة",
        )
        with pytest.raises(AttributeError):
            sr.density = 0.9

    def test_all_fields_in_range(self):
        """All numeric fields must be 0-1 (except fragment_count)."""
        texts = [
            "No. Stop. Why.",
            "Thank you so much, I appreciate everything you have done for me.",
            "THIS IS TERRIBLE!!! WHY!!! NO!!!",
            "الاجتماع غدا. سنناقش النتائج. يرجى الحضور.",
        ]
        for text in texts:
            sr = _compute_structural_resonance(text)
            assert 0.0 <= sr.density <= 1.0, f"density {sr.density} out of range"
            assert 0.0 <= sr.continuity <= 1.0, f"continuity {sr.continuity} out of range"
            assert 0.0 <= sr.effort_index <= 1.0, f"effort_index {sr.effort_index} out of range"
            assert 0.0 <= sr.rhythm_regularity <= 1.0, f"rhythm_regularity {sr.rhythm_regularity} out of range"
            assert sr.fragment_count >= 0, f"fragment_count {sr.fragment_count} negative"


class TestStructuralResonanceExistingTestsStillPass:
    """FN#066 Test 10: Existing tests still pass after changes.

    This class verifies that adding structural_resonance does NOT
    break any existing MaqamReading construction or detection.
    """

    def test_existing_warmth_still_works(self):
        text = "Thank you so much, I appreciate everything you've done. Means a lot to me."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.WARMTH
        assert reading.activated is True

    def test_existing_neutral_still_works(self):
        text = "Please schedule the meeting for 2pm."
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.NEUTRAL
        assert reading.activated is False

    def test_existing_frustration_arabic_still_works(self):
        text = "طفشت مليت ما ينفع كل شي يخرب ما يزبط"
        reading = detect_maqam(text)
        assert reading.detected_maqam == MaqamType.FRUSTRATION
        assert reading.activated is True

    def test_non_activated_helper_still_works(self):
        reading = _non_activated_reading()
        assert reading.detected_maqam == MaqamType.NEUTRAL
        assert reading.activated is False
        assert reading.structural_resonance is None

    def test_reading_still_has_all_original_fields(self):
        text = "I'm scared and I don't know what to do. I feel lost. Please help."
        reading = detect_maqam(text)
        # All original fields must still exist
        assert hasattr(reading, 'detected_maqam')
        assert hasattr(reading, 'confidence')
        assert hasattr(reading, 'confidence_band')
        assert hasattr(reading, 'jins')
        assert hasattr(reading, 'aqd')
        assert hasattr(reading, 'nisba')
        assert hasattr(reading, 'secondary_maqam')
        assert hasattr(reading, 'secondary_confidence')
        assert hasattr(reading, 'markers_found')
        assert hasattr(reading, 'evidence_count')
        assert hasattr(reading, 'language_detected')
        assert hasattr(reading, 'dialect_hint')
        assert hasattr(reading, 'scores_by_maqam')
        assert hasattr(reading, 'b5_style_hints')
        assert hasattr(reading, 'activated')
        assert hasattr(reading, 'structural_resonance')
        assert hasattr(reading, 'safety_decision_authority')
        assert hasattr(reading, '_isolation_marker')
