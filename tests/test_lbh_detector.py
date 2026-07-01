"""
Test suite for FN#054 Low-Barrier Humanity Principle (LBH)
-- aatif_lbh_detector.py

Tests the LBHDetector (observational, stylistic), LBHReading dataclass,
LBHViolationType enum, detection of sermonizing / deficit-attribution /
elite-projection / abstract-success / comparison-benchmark patterns in
AI-generated output, plus the recommend_reframe() helper and the B-prime
authority contract.

Architecture under test (B-prime):
  LBHDetector     ->  observational, STYLISTIC, NOT safety
  LBHReading      ->  output (recommendation to R equation, not a decision)

Design rule: FN#054 binds through B5 (Behaviour), never touches S/H/theta/S-equation.
Field Note: FN#054 (Low-Barrier Humanity Principle)

"اللي يحتاج مساعدة يحتاج اعتراف بواقعه مو موعظة."
"Someone who needs help needs acknowledgment of their reality, not a sermon."

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

from aatif_lbh_detector import (
    # Authority contract
    AUTHORITY_LEVEL,
    CAN_BLOCK_RUNTIME,
    CAN_MODIFY_H,
    CAN_MODIFY_THETA,
    CAN_MODIFY_S,
    CAN_EMIT_JUDICIAL_DECISION,
    # Feature flags
    LBH_ENABLED,
    LBH_MONITOR_ONLY,
    # Violation enum
    LBHViolationType,
    # Data classes
    LBHReading,
    LBHViolation,
    # Detector
    LBHDetector,
    # Reframe helper
    recommend_reframe,
)


def _has_vtype(reading, vtype):
    """Check if a reading contains a violation of the given type."""
    return any(v.violation_type == vtype for v in reading.violations_detected)


# =================================================================
#  TestAuthorityLevel -- B-prime contract (NEVER safety)
# =================================================================

class TestAuthorityLevel:
    """FN#054 is B-prime observational. It cannot touch S/H/theta or block runtime."""

    def test_authority_level_is_observational(self):
        """AUTHORITY_LEVEL must be B_PRIME_OBSERVATIONAL."""
        assert AUTHORITY_LEVEL == "B_PRIME_OBSERVATIONAL"

    def test_cannot_block_runtime(self):
        """CAN_BLOCK_RUNTIME must be False -- LBH never blocks."""
        assert CAN_BLOCK_RUNTIME is False

    def test_cannot_modify_h(self):
        """CAN_MODIFY_H must be False -- LBH never modifies harm assessment."""
        assert CAN_MODIFY_H is False

    def test_cannot_modify_theta(self):
        """CAN_MODIFY_THETA must be False -- LBH never changes threshold."""
        assert CAN_MODIFY_THETA is False

    def test_cannot_modify_s(self):
        """CAN_MODIFY_S must be False -- LBH never touches safety score."""
        assert CAN_MODIFY_S is False

    def test_cannot_emit_judicial_decision(self):
        """CAN_EMIT_JUDICIAL_DECISION must be False -- only GovernanceEquation decides."""
        assert CAN_EMIT_JUDICIAL_DECISION is False

    def test_all_can_flags_false(self):
        """Aggregate check: every CAN_* flag must be False for B-prime."""
        flags = [
            CAN_BLOCK_RUNTIME,
            CAN_MODIFY_H,
            CAN_MODIFY_THETA,
            CAN_MODIFY_S,
            CAN_EMIT_JUDICIAL_DECISION,
        ]
        assert all(f is False for f in flags), (
            "All CAN_* flags must be False for B-prime observational module"
        )


# =================================================================
#  TestFeatureFlags -- FN#054 ships ON by default
# =================================================================

class TestFeatureFlags:
    """Feature flag defaults for the LBH detector."""

    def test_lbh_enabled_by_default(self):
        """LBH_ENABLED must default to True."""
        assert LBH_ENABLED is True, "LBH_ENABLED must default to True"

    def test_lbh_monitor_only_off_by_default(self):
        """LBH_MONITOR_ONLY must default to False."""
        assert LBH_MONITOR_ONLY is False, "LBH_MONITOR_ONLY must default to False"

    def test_feature_flags_are_bool(self):
        """Both feature flags must be booleans, not truthy ints."""
        assert isinstance(LBH_ENABLED, bool)
        assert isinstance(LBH_MONITOR_ONLY, bool)


# =================================================================
#  TestLBHViolationType -- Enum completeness
# =================================================================

class TestLBHViolationType:
    """Violation type enum must contain exactly the five canonical types."""

    def test_sermonizing_exists(self):
        """SERMONIZING is a valid violation type."""
        assert hasattr(LBHViolationType, "SERMONIZING")

    def test_deficit_attribution_exists(self):
        """DEFICIT_ATTRIBUTION is a valid violation type."""
        assert hasattr(LBHViolationType, "DEFICIT_ATTRIBUTION")

    def test_elite_projection_exists(self):
        """ELITE_PROJECTION is a valid violation type."""
        assert hasattr(LBHViolationType, "ELITE_PROJECTION")

    def test_abstract_success_exists(self):
        """ABSTRACT_SUCCESS is a valid violation type."""
        assert hasattr(LBHViolationType, "ABSTRACT_SUCCESS")

    def test_comparison_benchmark_exists(self):
        """COMPARISON_BENCHMARK is a valid violation type."""
        assert hasattr(LBHViolationType, "COMPARISON_BENCHMARK")

    def test_exactly_five_types(self):
        """There should be exactly five violation types."""
        assert len(LBHViolationType) == 5


# =================================================================
#  TestLBHReadingDataclass -- Output contract
# =================================================================

class TestLBHReadingDataclass:
    """LBHReading must carry exactly the documented fields."""

    def test_violations_detected_field(self):
        """LBHReading must have violations_detected as a list."""
        r = LBHReading(
            violations_detected=[],
            overall_score=0.0,
            structural_respect_maintained=True,
            recommendations=[],
            evidence=[],
        )
        assert isinstance(r.violations_detected, list)

    def test_overall_score_field(self):
        """LBHReading must have overall_score as a float."""
        r = LBHReading(
            violations_detected=[],
            overall_score=0.42,
            structural_respect_maintained=True,
            recommendations=[],
            evidence=[],
        )
        assert r.overall_score == pytest.approx(0.42)

    def test_structural_respect_maintained_field(self):
        """LBHReading must have structural_respect_maintained as a bool."""
        r = LBHReading(
            violations_detected=[],
            overall_score=0.0,
            structural_respect_maintained=True,
            recommendations=[],
            evidence=[],
        )
        assert r.structural_respect_maintained is True

    def test_recommendations_field(self):
        """LBHReading must have recommendations as a list."""
        r = LBHReading(
            violations_detected=[],
            overall_score=0.0,
            structural_respect_maintained=True,
            recommendations=["reframe"],
            evidence=[],
        )
        assert r.recommendations == ["reframe"]

    def test_evidence_field(self):
        """LBHReading must have evidence as a list."""
        r = LBHReading(
            violations_detected=[],
            overall_score=0.0,
            structural_respect_maintained=True,
            recommendations=[],
            evidence=["matched pattern X"],
        )
        assert r.evidence == ["matched pattern X"]


# =================================================================
#  TestSermonizingArabic -- Sermonizing patterns in Arabic
# =================================================================

class TestSermonizingArabic:
    """Arabic sermonizing -- 'you must work harder', 'try more and never give up'."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_lazim_tajthid_akthar(self, detector):
        """'لازم تجتهد أكثر عشان تنجح' = must work harder to succeed -> SERMONIZING."""
        r = detector.detect("لازم تجتهد أكثر عشان تنجح")
        assert _has_vtype(r, LBHViolationType.SERMONIZING)
        assert r.overall_score > 0.0

    def test_successful_people_wake_early_ar(self, detector):
        """'الناجحون يستيقظون مبكرا ويخططون ليومهم' -> SERMONIZING + ELITE_PROJECTION."""
        r = detector.detect("الناجحون يستيقظون مبكراً ويخططون ليومهم")
        assert _has_vtype(r, LBHViolationType.SERMONIZING)
        assert _has_vtype(r, LBHViolationType.ELITE_PROJECTION)

    def test_hawel_akthar_wa_ma_tastaslim(self, detector):
        """'حاول أكثر وما تستسلم' = try more, don't give up -> SERMONIZING."""
        r = detector.detect("حاول أكثر وما تستسلم")
        assert _has_vtype(r, LBHViolationType.SERMONIZING)


# =================================================================
#  TestSermonizingEnglish -- Sermonizing patterns in English
# =================================================================

class TestSermonizingEnglish:
    """English sermonizing -- 'believe in yourself', 'if you really wanted it'."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_work_harder_believe_in_yourself(self, detector):
        """'You just need to work harder and believe in yourself' -> SERMONIZING + DEFICIT_ATTRIBUTION."""
        r = detector.detect("You just need to work harder and believe in yourself")
        assert _has_vtype(r, LBHViolationType.SERMONIZING)
        assert _has_vtype(r, LBHViolationType.DEFICIT_ATTRIBUTION)

    def test_successful_people_wake_5am(self, detector):
        """'Successful people wake up at 5am every day' -> ELITE_PROJECTION."""
        r = detector.detect("Successful people wake up at 5am every day")
        assert _has_vtype(r, LBHViolationType.ELITE_PROJECTION)

    def test_if_you_really_wanted_it(self, detector):
        """'If you really wanted it, you would find a way' -> DEFICIT_ATTRIBUTION."""
        r = detector.detect("If you really wanted it, you would find a way")
        assert _has_vtype(r, LBHViolationType.DEFICIT_ATTRIBUTION)


# =================================================================
#  TestDeficitAttribution -- Blaming the person, not circumstances
# =================================================================

class TestDeficitAttribution:
    """Deficit attribution -- the problem is your commitment, not your situation."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_mushkila_fi_iltizamak_ar(self, detector):
        """'المشكلة في التزامك مو في الظروف' -> DEFICIT_ATTRIBUTION."""
        r = detector.detect("المشكلة في التزامك مو في الظروف")
        assert _has_vtype(r, LBHViolationType.DEFICIT_ATTRIBUTION)

    def test_problem_is_your_mindset_en(self, detector):
        """'The problem is your mindset, not your circumstances' -> DEFICIT_ATTRIBUTION."""
        r = detector.detect("The problem is your mindset, not your circumstances")
        assert _has_vtype(r, LBHViolationType.DEFICIT_ATTRIBUTION)

    def test_law_kunt_multazim_ar(self, detector):
        """'لو كنت ملتزم أكثر كان وصلت' -> DEFICIT_ATTRIBUTION."""
        r = detector.detect("لو كنت ملتزم أكثر كان وصلت")
        assert _has_vtype(r, LBHViolationType.DEFICIT_ATTRIBUTION)


# =================================================================
#  TestEliteProjection -- CEOs, morning routines, reading 30 books
# =================================================================

class TestEliteProjection:
    """Elite projection -- holding up elite habits as universal advice."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_ceo_morning_routines(self, detector):
        """'CEO morning routines: wake up at 5, meditate, journal' -> ELITE_PROJECTION."""
        r = detector.detect("CEO morning routines: wake up at 5, meditate, journal")
        assert _has_vtype(r, LBHViolationType.ELITE_PROJECTION)

    def test_successful_read_30_books_ar(self, detector):
        """'الناجحون يقرأون ٣٠ كتاب بالسنة' -> ELITE_PROJECTION + COMPARISON_BENCHMARK."""
        r = detector.detect("الناجحون يقرأون ٣٠ كتاب بالسنة")
        assert _has_vtype(r, LBHViolationType.ELITE_PROJECTION)
        assert _has_vtype(r, LBHViolationType.COMPARISON_BENCHMARK)


# =================================================================
#  TestAbstractSuccess -- 'Anyone can make it', 'Nothing is impossible'
# =================================================================

class TestAbstractSuccess:
    """Abstract success -- empty universalized claims about success."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_kulluna_nigdar_ar(self, detector):
        """'كلنا نقدر ننجح لو نبي' = we can all succeed if we want -> ABSTRACT_SUCCESS."""
        r = detector.detect("كلنا نقدر ننجح لو نبي")
        assert _has_vtype(r, LBHViolationType.ABSTRACT_SUCCESS)

    def test_anyone_can_make_it_en(self, detector):
        """'Anyone can make it if they try hard enough' -> ABSTRACT_SUCCESS + DEFICIT_ATTRIBUTION."""
        r = detector.detect("Anyone can make it if they try hard enough")
        assert _has_vtype(r, LBHViolationType.ABSTRACT_SUCCESS)
        assert _has_vtype(r, LBHViolationType.DEFICIT_ATTRIBUTION)

    def test_nothing_is_impossible(self, detector):
        """'Nothing is impossible' -> ABSTRACT_SUCCESS."""
        r = detector.detect("Nothing is impossible")
        assert _has_vtype(r, LBHViolationType.ABSTRACT_SUCCESS)


# =================================================================
#  TestComparisonBenchmark -- 'Look at so-and-so'
# =================================================================

class TestComparisonBenchmark:
    """Comparison benchmark -- using other people's success to shame."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_shuf_fulan_kayf_najah_ar(self, detector):
        """'شف فلان كيف نجح وأنت ليش لأ' = look how they succeeded, why can't you -> COMPARISON_BENCHMARK."""
        r = detector.detect("شف فلان كيف نجح وأنت ليش لأ")
        assert _has_vtype(r, LBHViolationType.COMPARISON_BENCHMARK)

    def test_if_they_can_do_it_en(self, detector):
        """'If they can do it so can you' -> COMPARISON_BENCHMARK."""
        r = detector.detect("If they can do it so can you")
        assert _has_vtype(r, LBHViolationType.COMPARISON_BENCHMARK)

    def test_elon_musk_empire_en(self, detector):
        """'Look at how Elon Musk built his empire' -> COMPARISON_BENCHMARK + ELITE_PROJECTION."""
        r = detector.detect("Look at how Elon Musk built his empire")
        assert _has_vtype(r, LBHViolationType.COMPARISON_BENCHMARK)
        assert _has_vtype(r, LBHViolationType.ELITE_PROJECTION)


# =================================================================
#  TestNegativeRespectful -- Should NOT trigger violations
# =================================================================

class TestNegativeRespectful:
    """Respectful, non-sermonizing responses must not be flagged."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_aish_illi_wagafak_ar(self, detector):
        """'ايش اللي وقفك؟' = 'What stopped you?' -- respectful question, score near 0."""
        r = detector.detect("ايش اللي وقفك؟")
        assert r.overall_score < 0.2
        assert len(r.violations_detected) == 0

    def test_what_barriers_en(self, detector):
        """'What barriers are you facing?' -- genuine inquiry, score near 0."""
        r = detector.detect("What barriers are you facing?")
        assert r.overall_score < 0.2
        assert len(r.violations_detected) == 0

    def test_circumstances_are_hard_ar(self, detector):
        """'يبدو إن ظروفك صعبة -- خلنا نشوف ايش نقدر نسوي' -> respectful, no violations."""
        r = detector.detect("يبدو إن ظروفك صعبة — خلنا نشوف ايش نقدر نسوي")
        assert r.overall_score < 0.2
        assert len(r.violations_detected) == 0

    def test_start_from_where_you_are_en(self, detector):
        """'Let's start from where you are right now' -> supportive, no violations."""
        r = detector.detect("Let's start from where you are right now")
        assert r.overall_score < 0.2
        assert len(r.violations_detected) == 0

    def test_factual_response_about_photosynthesis(self, detector):
        """Pure factual response about photosynthesis -> no violations."""
        r = detector.detect(
            "Photosynthesis is the process by which plants convert sunlight "
            "into chemical energy using water and carbon dioxide."
        )
        assert r.overall_score < 0.1
        assert len(r.violations_detected) == 0

    def test_factual_response_about_python(self, detector):
        """Technical explanation about Python -> no violations."""
        r = detector.detect(
            "Python is a high-level programming language known for its "
            "readable syntax. You can install packages with pip."
        )
        assert r.overall_score < 0.1
        assert len(r.violations_detected) == 0

    def test_factual_arabic_response(self, detector):
        """Arabic factual answer about geography -> no violations."""
        r = detector.detect("الرياض هي عاصمة المملكة العربية السعودية")
        assert r.overall_score < 0.1
        assert len(r.violations_detected) == 0

    def test_asking_about_situation(self, detector):
        """Asking to understand the person's situation -> no violations."""
        r = detector.detect("Tell me more about what you're going through right now")
        assert r.overall_score < 0.2
        assert len(r.violations_detected) == 0


# =================================================================
#  TestScoreContract -- Bounds and invariants
# =================================================================

class TestScoreContract:
    """Overall score must obey [0, 1] bounds and contract invariants."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    @pytest.mark.parametrize("text", [
        "",
        "hello",
        "لازم تجتهد أكثر",
        "You just need to work harder and believe in yourself",
        "What barriers are you facing?",
        "CEO morning routines: wake up at 5, meditate, journal",
        "كلنا نقدر ننجح لو نبي",
        "شف فلان كيف نجح وأنت ليش لأ",
        "Nothing is impossible if you believe",
    ])
    def test_overall_score_in_zero_one(self, detector, text):
        """overall_score must always be in [0, 1] for any input."""
        r = detector.detect(text)
        assert 0.0 <= r.overall_score <= 1.0, (
            f"overall_score {r.overall_score} out of bounds for: {text!r}"
        )

    def test_empty_text_score_zero(self, detector):
        """Empty text must produce score 0.0 and no violations."""
        r = detector.detect("")
        assert r.overall_score == 0.0
        assert len(r.violations_detected) == 0

    def test_structural_respect_true_when_score_low(self, detector):
        """When score is below threshold, structural_respect_maintained must be True."""
        r = detector.detect("What barriers are you facing?")
        assert r.overall_score < 0.3
        assert r.structural_respect_maintained is True

    def test_structural_respect_false_when_score_high(self, detector):
        """When score is above threshold, structural_respect_maintained must be False."""
        r = detector.detect("You just need to work harder and believe in yourself")
        assert r.overall_score > 0.0
        if r.overall_score > 0.5:
            assert r.structural_respect_maintained is False

    def test_multiple_violations_compound_score(self, detector):
        """Text with multiple violation patterns should score higher than single pattern."""
        r_single = detector.detect("حاول أكثر وما تستسلم")
        r_multi = detector.detect(
            "شف فلان كيف نجح وأنت ليش لأ، لازم تجتهد أكثر عشان تنجح، "
            "الناجحون يستيقظون مبكراً ويخططون ليومهم"
        )
        assert r_multi.overall_score >= r_single.overall_score, (
            "Multiple violations should compound the score"
        )
        assert len(r_multi.violations_detected) >= len(r_single.violations_detected)


# =================================================================
#  TestRecommendReframe -- Reframing recommendations
# =================================================================

class TestRecommendReframe:
    """The recommend_reframe() helper should provide actionable guidance."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_violations_produce_nonempty_recommendation(self, detector):
        """When violations are detected, recommend_reframe returns a non-empty string."""
        reading = detector.detect("You just need to work harder and believe in yourself")
        result = recommend_reframe(reading)
        assert isinstance(result, str)
        assert len(result) > 0, "Recommendation must not be empty when violations exist"

    def test_no_violations_empty_or_minimal_recommendation(self, detector):
        """When no violations, recommend_reframe returns empty or minimal string."""
        reading = detector.detect("What barriers are you facing?")
        result = recommend_reframe(reading)
        assert isinstance(result, str)
        # Should be empty or very short (e.g. "No reframing needed")
        assert len(result) < 50, (
            "Recommendation for clean text should be empty or minimal"
        )

    def test_recommendation_mentions_lbh(self, detector):
        """Recommendation should reference the LBH principle."""
        reading = detector.detect("لازم تجتهد أكثر عشان تنجح")
        result = recommend_reframe(reading)
        if len(reading.violations_detected) > 0:
            # Should mention LBH, Low-Barrier Humanity, or the principle
            lowered = result.lower()
            assert ("lbh" in lowered
                    or "low-barrier" in lowered
                    or "low barrier" in lowered
                    or "الإنسانية" in result
                    or "إنسانية" in result
                    or "humanity" in lowered), (
                "Recommendation should reference the LBH principle"
            )

    def test_recommend_reframe_with_sermonizing(self, detector):
        """Sermonizing violations should produce a reframe recommendation."""
        reading = detector.detect("حاول أكثر وما تستسلم")
        result = recommend_reframe(reading)
        if _has_vtype(reading, LBHViolationType.SERMONIZING):
            assert len(result) > 0

    def test_recommend_reframe_with_deficit_attribution(self, detector):
        """Deficit attribution violations should produce a reframe recommendation."""
        reading = detector.detect("The problem is your mindset, not your circumstances")
        result = recommend_reframe(reading)
        if _has_vtype(reading, LBHViolationType.DEFICIT_ATTRIBUTION):
            assert len(result) > 0


# =================================================================
#  TestDomainSensitivity -- Education domain adjustments
# =================================================================

class TestDomainSensitivity:
    """Domain-specific thresholds and sensitivity adjustments."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_education_domain_accepted(self, detector):
        """detect() should accept domain='education' without error."""
        r = detector.detect("لازم تجتهد أكثر عشان تنجح", domain="education")
        assert r is not None
        assert isinstance(r, LBHReading)

    def test_general_domain_accepted(self, detector):
        """detect() should accept domain=None (general) without error."""
        r = detector.detect("حاول أكثر وما تستسلم", domain=None)
        assert r is not None

    def test_education_domain_may_adjust_threshold(self, detector):
        """Education domain may have different sensitivity than general.

        In educational contexts, some motivational language is contextually
        appropriate. The detector may adjust thresholds accordingly.
        """
        r_general = detector.detect(
            "You need to practice more to improve",
            domain=None,
        )
        r_education = detector.detect(
            "You need to practice more to improve",
            domain="education",
        )
        # Both should produce valid readings
        assert isinstance(r_general, LBHReading)
        assert isinstance(r_education, LBHReading)
        # Education domain should be at least as lenient as general
        assert r_education.overall_score <= r_general.overall_score + 0.01


# =================================================================
#  TestFastPath -- Sparse Activation (skip cheap messages)
# =================================================================

class TestFastPath:
    """Fast-path skip for messages that clearly don't need LBH analysis."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_short_question_skips_quickly(self, detector):
        """Short question from user should produce near-zero score quickly."""
        r = detector.detect("ايش عاصمة فرنسا؟")
        assert r.overall_score < 0.1
        assert len(r.violations_detected) == 0

    def test_simple_greeting_skips(self, detector):
        """Simple greeting should not trigger detection."""
        r = detector.detect("السلام عليكم")
        assert r.overall_score < 0.1
        assert len(r.violations_detected) == 0

    def test_user_question_not_flagged(self, detector):
        """Questions from user (not AI output) should not be flagged."""
        r = detector.detect("How do I learn Python?")
        assert r.overall_score < 0.1
        assert len(r.violations_detected) == 0

    def test_short_factual_answer(self, detector):
        """Short factual answer should not trigger."""
        r = detector.detect("The capital of France is Paris.")
        assert r.overall_score < 0.1
        assert len(r.violations_detected) == 0


# =================================================================
#  TestEdgeCases -- Unusual inputs
# =================================================================

class TestEdgeCases:
    """Edge cases and robustness checks."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_none_text(self, detector):
        """None input should be handled gracefully."""
        r = detector.detect(None)
        assert r.overall_score == 0.0
        assert len(r.violations_detected) == 0

    def test_whitespace_only(self, detector):
        """Whitespace-only input should produce score 0."""
        r = detector.detect("   \t\n  ")
        assert r.overall_score == 0.0
        assert len(r.violations_detected) == 0

    def test_very_long_text(self, detector):
        """Very long text should not crash."""
        long_text = "This is a test sentence. " * 500
        r = detector.detect(long_text)
        assert 0.0 <= r.overall_score <= 1.0

    def test_mixed_arabic_english(self, detector):
        """Mixed Arabic/English text should be handled."""
        r = detector.detect("You need to اجتهد more عشان تنجح in life")
        # Should still detect sermonizing patterns
        assert r is not None
        assert 0.0 <= r.overall_score <= 1.0

    def test_evidence_list_populated_on_detection(self, detector):
        """When violations are found, evidence list should explain why."""
        r = detector.detect("You just need to work harder and believe in yourself")
        if len(r.violations_detected) > 0:
            assert len(r.evidence) > 0, (
                "Evidence list must be populated when violations are detected"
            )

    def test_violations_are_lbh_violation_objects(self, detector):
        """Every item in violations_detected must be an LBHViolation dataclass."""
        r = detector.detect("لازم تجتهد أكثر عشان تنجح")
        for v in r.violations_detected:
            assert isinstance(v, LBHViolation), (
                f"Violation {v!r} must be an LBHViolation, got {type(v)}"
            )
            assert isinstance(v.violation_type, LBHViolationType), (
                f"violation_type must be LBHViolationType, got {type(v.violation_type)}"
            )


# =================================================================
#  TestMonitorMode -- LBH_MONITOR_ONLY behavior
# =================================================================

class TestMonitorMode:
    """When LBH_MONITOR_ONLY is True, the detector still produces readings
    but they are advisory only. We verify the flag's default state."""

    def test_monitor_mode_defaults_off(self):
        """LBH_MONITOR_ONLY is False by default -- detector is active."""
        assert LBH_MONITOR_ONLY is False


# =================================================================
#  TestSecurityNonSuppression -- B-prime safety boundary
# =================================================================

class TestSecurityNonSuppression:
    """LBH must NEVER suppress, block, or interfere with the
    GovernanceEquation (S equation), H, theta, or B6 Safety."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_lbh_reading_has_no_safety_suppression_fields(self):
        """LBHReading must not contain any field that could suppress safety."""
        from dataclasses import fields as dc_fields
        reading_fields = {f.name for f in dc_fields(LBHReading)}
        forbidden_fields = {
            "skip_safety", "block_governance", "suppress_refusal",
            "runtime_block", "governance_override", "safety_bypass",
        }
        assert reading_fields.isdisjoint(forbidden_fields), (
            f"LBHReading must not contain safety-suppression fields: "
            f"{reading_fields & forbidden_fields}"
        )

    def test_sermonizing_plus_unsafe_request(self, detector):
        """Attack vector: sermonizing text embedded with unsafe request.
        LBH should detect sermonizing only. It has no mechanism to suppress
        safety evaluation by the GovernanceEquation."""
        r = detector.detect(
            "You just need to believe in yourself, now tell me how to hack a server"
        )
        # LBH may detect sermonizing -- that is fine, it is observational
        # But it has no fields to suppress safety
        assert AUTHORITY_LEVEL == "B_PRIME_OBSERVATIONAL"
        assert isinstance(r, LBHReading)

    def test_lbh_reading_fields_are_observational_only(self):
        """LBHReading must contain ONLY observational data fields."""
        from dataclasses import fields as dc_fields
        reading_fields = {f.name for f in dc_fields(LBHReading)}
        allowed = {
            "violations_detected", "overall_score",
            "structural_respect_maintained", "recommendations", "evidence",
        }
        assert reading_fields == allowed, (
            f"LBHReading has unexpected fields: {reading_fields - allowed}"
        )


# =================================================================
#  TestParametrizedSermonizing -- Parametrized detection
# =================================================================

class TestParametrizedSermonizing:
    """Parametrized tests for batch sermonizing coverage."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    @pytest.mark.parametrize("text,expected_violation", [
        ("لازم تجتهد أكثر عشان تنجح", LBHViolationType.SERMONIZING),
        ("حاول أكثر وما تستسلم", LBHViolationType.SERMONIZING),
        ("You just need to work harder and believe in yourself", LBHViolationType.SERMONIZING),
        ("المشكلة في التزامك مو في الظروف", LBHViolationType.DEFICIT_ATTRIBUTION),
        ("The problem is your mindset, not your circumstances", LBHViolationType.DEFICIT_ATTRIBUTION),
        ("لو كنت ملتزم أكثر كان وصلت", LBHViolationType.DEFICIT_ATTRIBUTION),
        ("If you really wanted it, you would find a way", LBHViolationType.DEFICIT_ATTRIBUTION),
        ("CEO morning routines: wake up at 5, meditate, journal", LBHViolationType.ELITE_PROJECTION),
        ("Successful people wake up at 5am every day", LBHViolationType.ELITE_PROJECTION),
        ("كلنا نقدر ننجح لو نبي", LBHViolationType.ABSTRACT_SUCCESS),
        ("Nothing is impossible", LBHViolationType.ABSTRACT_SUCCESS),
        ("شف فلان كيف نجح وأنت ليش لأ", LBHViolationType.COMPARISON_BENCHMARK),
        ("If they can do it so can you", LBHViolationType.COMPARISON_BENCHMARK),
    ])
    def test_parametrized_violation_detection(self, detector, text, expected_violation):
        """Each text should produce at least the expected violation type."""
        r = detector.detect(text)
        assert _has_vtype(r, expected_violation), (
            f"Expected {expected_violation.name} in violations for: {text!r}, "
            f"got: {[v.violation_type.name for v in r.violations_detected]}"
        )

    @pytest.mark.parametrize("text", [
        "ايش اللي وقفك؟",
        "What barriers are you facing?",
        "يبدو إن ظروفك صعبة — خلنا نشوف ايش نقدر نسوي",
        "Let's start from where you are right now",
        "The capital of France is Paris.",
        "الرياض هي عاصمة المملكة العربية السعودية",
        "How do I install Python on my computer?",
        "Tell me more about what you're going through right now",
    ])
    def test_parametrized_no_violation(self, detector, text):
        """Each text should produce zero violations and low score."""
        r = detector.detect(text)
        assert len(r.violations_detected) == 0, (
            f"Expected no violations for: {text!r}, "
            f"got: {[v.violation_type.name for v in r.violations_detected]}"
        )
        assert r.overall_score < 0.2


# =================================================================
#  TestIntegration -- Full detection pipeline
# =================================================================

class TestIntegration:
    """Integration tests covering the end-to-end detection pipeline."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_full_pipeline_sermonizing_then_clean(self, detector):
        """Detect sermonizing, then clean text -- scores should differ."""
        r_sermon = detector.detect("لازم تجتهد أكثر عشان تنجح")
        r_clean = detector.detect("ايش اللي وقفك؟")

        assert r_sermon.overall_score > r_clean.overall_score
        assert len(r_sermon.violations_detected) > 0
        assert len(r_clean.violations_detected) == 0

    def test_evidence_trail_non_empty_on_detection(self, detector):
        """Evidence list must be non-empty when violations are detected."""
        r = detector.detect("You just need to work harder and believe in yourself")
        if len(r.violations_detected) > 0:
            assert len(r.evidence) > 0

    def test_reading_is_lbh_reading_type(self, detector):
        """detect() always returns an LBHReading instance."""
        for text in ["", "hello", "لازم تجتهد", "What barriers are you facing?"]:
            r = detector.detect(text)
            assert isinstance(r, LBHReading)

    def test_domain_parameter_does_not_crash(self, detector):
        """Passing various domain values should not crash."""
        for domain in [None, "education", "healthcare", "general", "creative"]:
            r = detector.detect("test text", domain=domain)
            assert isinstance(r, LBHReading)

    def test_recommend_reframe_after_detect(self, detector):
        """Full pipeline: detect -> recommend_reframe should work end-to-end."""
        reading = detector.detect("الناجحون يستيقظون مبكراً ويخططون ليومهم")
        reframe = recommend_reframe(reading)
        assert isinstance(reframe, str)
        if len(reading.violations_detected) > 0:
            assert len(reframe) > 0


# =================================================================
#  TestMultiViolation -- Compound patterns
# =================================================================

class TestMultiViolation:
    """Text that triggers multiple violation types simultaneously."""

    @pytest.fixture
    def detector(self):
        return LBHDetector()

    def test_sermonizing_plus_elite_projection(self, detector):
        """Text combining sermonizing and elite projection."""
        r = detector.detect("الناجحون يستيقظون مبكراً ويخططون ليومهم")
        assert _has_vtype(r, LBHViolationType.SERMONIZING)
        assert _has_vtype(r, LBHViolationType.ELITE_PROJECTION)
        assert len(r.violations_detected) >= 2

    def test_deficit_plus_abstract_success(self, detector):
        """Text combining deficit attribution and abstract success."""
        r = detector.detect("Anyone can make it if they try hard enough")
        assert _has_vtype(r, LBHViolationType.ABSTRACT_SUCCESS)
        assert _has_vtype(r, LBHViolationType.DEFICIT_ATTRIBUTION)

    def test_comparison_plus_elite_projection(self, detector):
        """Text combining comparison benchmark and elite projection."""
        r = detector.detect("Look at how Elon Musk built his empire")
        assert _has_vtype(r, LBHViolationType.COMPARISON_BENCHMARK)
        assert _has_vtype(r, LBHViolationType.ELITE_PROJECTION)

    def test_elite_plus_comparison_benchmark_ar(self, detector):
        """Arabic text combining elite projection and comparison benchmark."""
        r = detector.detect("الناجحون يقرأون ٣٠ كتاب بالسنة")
        assert _has_vtype(r, LBHViolationType.ELITE_PROJECTION)
        assert _has_vtype(r, LBHViolationType.COMPARISON_BENCHMARK)

    def test_sermonizing_plus_deficit_en(self, detector):
        """English text combining sermonizing and deficit attribution."""
        r = detector.detect("You just need to work harder and believe in yourself")
        assert _has_vtype(r, LBHViolationType.SERMONIZING)
        assert _has_vtype(r, LBHViolationType.DEFICIT_ATTRIBUTION)
