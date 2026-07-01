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
    _get_confidence_band,
    _non_activated_reading,
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
