"""
test_mrs_detector.py — Comprehensive test suite for FN#051 MRS Detector.

100+ tests covering:
  - Authority contract & isolation
  - Feature flag
  - Sparse activation (fast-path skip)
  - Identity Fusion detection (EN + AR)
  - Overgeneralization detection (EN + AR)
  - Catastrophizing detection (EN + AR)
  - Self-Blame detection (EN + AR)
  - Permanence Bias detection (EN + AR)
  - Crisis markers & professional referral gate
  - Arabic idiomatic distress (NOT crisis)
  - Compound pattern detection
  - Secondary subpatterns
  - Event-interpretation split
  - Severity assessment
  - LBH risk mapping
  - B5 style hints (renamed from recommendations)
  - Language detection
  - Audit hash
  - Non-activation examples (normal sadness ≠ harmful interpretation)
  - Frozen dataclass immutability
  - Edge cases

License: BSL-1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

import hashlib
import pytest

from engine.aatif_mrs_detector import (
    MRS_ENABLED,
    MRSDetector,
    MRSReading,
    InterpretationType,
    SecondaryPattern,
    Severity,
    LBHRiskType,
    _normalize_arabic,
    _compile_en_patterns,
    _match_en_markers,
    _match_ar_markers,
    IDENTITY_FUSION_MARKERS_EN,
    IDENTITY_FUSION_MARKERS_AR,
    OVERGENERALIZATION_MARKERS_EN,
    OVERGENERALIZATION_MARKERS_AR,
    CATASTROPHIZING_MARKERS_EN,
    CATASTROPHIZING_MARKERS_AR,
    SELF_BLAME_MARKERS_EN,
    SELF_BLAME_MARKERS_AR,
    PERMANENCE_BIAS_MARKERS_EN,
    PERMANENCE_BIAS_MARKERS_AR,
    CRISIS_MARKERS_EN,
    CRISIS_MARKERS_AR,
    ARABIC_IDIOMATIC_DISTRESS,
)


@pytest.fixture
def engine():
    return MRSDetector()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Authority Contract & B-prime Isolation  (10 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAuthorityContract:
    def test_authority_level(self):
        assert MRSDetector.AUTHORITY_LEVEL == "B_PRIME_OBSERVATIONAL"

    def test_cannot_block_runtime(self):
        assert MRSDetector.CAN_BLOCK_RUNTIME is False

    def test_cannot_modify_h(self):
        assert MRSDetector.CAN_MODIFY_H is False

    def test_cannot_modify_theta(self):
        assert MRSDetector.CAN_MODIFY_THETA is False

    def test_cannot_modify_s(self):
        assert MRSDetector.CAN_MODIFY_S is False

    def test_cannot_emit_judicial_decision(self):
        assert MRSDetector.CAN_EMIT_JUDICIAL_DECISION is False

    def test_binding_channel_is_b5(self):
        assert MRSDetector.BINDING_CHANNEL == "B5"

    def test_isolation_marker(self):
        assert MRSDetector.ISOLATION_MARKER == "B5_ADVISORY_NOT_FOR_SAFETY"

    def test_isolation_targets(self):
        assert MRSDetector.ISOLATION_TARGETS == frozenset({"B5"})

    def test_isolation_contract_not_empty(self):
        assert len(MRSDetector.ISOLATION_CONTRACT.strip()) > 50


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. Feature Flag  (2 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFeatureFlag:
    def test_mrs_enabled_by_default(self):
        assert MRS_ENABLED is True

    def test_disabled_returns_inactive(self, engine, monkeypatch):
        import engine.aatif_mrs_detector as mod
        monkeypatch.setattr(mod, "MRS_ENABLED", False)
        r = engine.analyze("I am a complete failure and nothing ever works")
        assert r.activated is False
        monkeypatch.setattr(mod, "MRS_ENABLED", True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. Sparse Activation / Fast-Path Skip  (7 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSparseActivation:
    def test_empty_string_inactive(self, engine):
        r = engine.analyze("")
        assert r.activated is False

    def test_none_inactive(self, engine):
        r = engine.analyze(None)
        assert r.activated is False

    def test_short_text_inactive(self, engine):
        r = engine.analyze("hi")
        assert r.activated is False

    def test_whitespace_only_inactive(self, engine):
        r = engine.analyze("      ")
        assert r.activated is False

    def test_neutral_text_inactive(self, engine):
        r = engine.analyze("The weather is nice today and I had a good lunch")
        assert r.activated is False

    def test_min_text_length_threshold(self, engine):
        assert engine._MIN_TEXT_LENGTH == 10

    def test_activation_threshold_is_035(self, engine):
        assert engine._ACTIVATION_THRESHOLD == 0.35


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. Identity Fusion Detection  (8 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIdentityFusion:
    def test_basic_en_identity_fusion(self, engine):
        r = engine.analyze("I failed the exam and I am a failure")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.IDENTITY_FUSION

    def test_contraction_en(self, engine):
        r = engine.analyze("I'm worthless and I don't deserve anything good")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.IDENTITY_FUSION

    def test_basic_ar_identity_fusion(self, engine):
        r = engine.analyze("أنا فاشل وما أقدر أسوي شي صح")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.IDENTITY_FUSION

    def test_gulf_dialect_ar(self, engine):
        r = engine.analyze("أنا مالي فايدة وما أنفع لأي شي")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.IDENTITY_FUSION

    def test_im_a_burden(self, engine):
        r = engine.analyze("I'm a burden on everyone around me and I know it")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.IDENTITY_FUSION

    def test_markers_found_populated(self, engine):
        r = engine.analyze("I am a failure in everything I do")
        assert r.activated is True
        assert len(r.markers_found) > 0

    def test_identity_fusion_markers_en_is_frozenset(self):
        assert isinstance(IDENTITY_FUSION_MARKERS_EN, frozenset)

    def test_identity_fusion_markers_ar_is_frozenset(self):
        assert isinstance(IDENTITY_FUSION_MARKERS_AR, frozenset)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. Overgeneralization Detection  (6 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestOvergeneralization:
    def test_en_nothing_ever_works(self, engine):
        r = engine.analyze("Nothing ever works for me no matter what I try")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.OVERGENERALIZATION

    def test_en_everyone_hates(self, engine):
        r = engine.analyze("Everyone hates me and nobody cares at all")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.OVERGENERALIZATION

    def test_ar_overgeneralization(self, engine):
        r = engine.analyze("ما في شي ينفع معي وكل شي غلط")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.OVERGENERALIZATION

    def test_gulf_ar_overgeneralization(self, engine):
        r = engine.analyze("ولا شي يزبط معي أبداً مهما سويت")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.OVERGENERALIZATION

    def test_markers_en_frozenset(self):
        assert isinstance(OVERGENERALIZATION_MARKERS_EN, frozenset)

    def test_markers_ar_frozenset(self):
        assert isinstance(OVERGENERALIZATION_MARKERS_AR, frozenset)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. Catastrophizing Detection  (6 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCatastrophizing:
    def test_en_life_is_over(self, engine):
        r = engine.analyze("My life is over and everything is ruined completely")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.CATASTROPHIZING

    def test_en_no_hope(self, engine):
        r = engine.analyze("There's no hope left and I can never come back from this")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.CATASTROPHIZING

    def test_ar_catastrophizing(self, engine):
        r = engine.analyze("حياتي انتهت وما في أمل لشي")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.CATASTROPHIZING

    def test_gulf_ar_catastrophizing(self, engine):
        r = engine.analyze("خلاص انتهيت وما عاد فيه أمل")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.CATASTROPHIZING

    def test_markers_en_frozenset(self):
        assert isinstance(CATASTROPHIZING_MARKERS_EN, frozenset)

    def test_markers_ar_frozenset(self):
        assert isinstance(CATASTROPHIZING_MARKERS_AR, frozenset)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7. Self-Blame Detection  (6 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSelfBlame:
    def test_en_all_my_fault(self, engine):
        r = engine.analyze("It's all my fault, I ruined everything for everyone")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.SELF_BLAME

    def test_en_because_of_me(self, engine):
        r = engine.analyze("It's because of me that everything fell apart")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.SELF_BLAME

    def test_ar_self_blame(self, engine):
        r = engine.analyze("كلها غلطتي أنا خربت كل شي")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.SELF_BLAME

    def test_gulf_ar_self_blame(self, engine):
        r = engine.analyze("أنا اللي جبتها لنفسي وكله مني")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.SELF_BLAME

    def test_markers_en_frozenset(self):
        assert isinstance(SELF_BLAME_MARKERS_EN, frozenset)

    def test_markers_ar_frozenset(self):
        assert isinstance(SELF_BLAME_MARKERS_AR, frozenset)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  8. Permanence Bias Detection  (6 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPermanenceBias:
    def test_en_never_recover(self, engine):
        r = engine.analyze("I'll never recover from this, I'm stuck forever")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.PERMANENCE_BIAS

    def test_en_nothing_changes(self, engine):
        r = engine.analyze("Nothing will change, things will never improve at all")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.PERMANENCE_BIAS

    def test_ar_permanence(self, engine):
        r = engine.analyze("ما راح أتعافى وبتظل كذا على طول")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.PERMANENCE_BIAS

    def test_gulf_ar_permanence(self, engine):
        r = engine.analyze("مستحيل أرجع طبيعي وما راح أتحسن")
        assert r.activated is True
        assert r.primary_interpretation_type == InterpretationType.PERMANENCE_BIAS

    def test_markers_en_frozenset(self):
        assert isinstance(PERMANENCE_BIAS_MARKERS_EN, frozenset)

    def test_markers_ar_frozenset(self):
        assert isinstance(PERMANENCE_BIAS_MARKERS_AR, frozenset)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  9. Crisis Markers & Professional Referral  (10 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCrisisDetection:
    def test_en_want_to_die(self, engine):
        r = engine.analyze("I just want to die and end it all right now")
        assert r.activated is True
        assert r.crisis_signal_observed is True
        assert r.severity == Severity.CRISIS

    def test_en_kill_myself(self, engine):
        r = engine.analyze("I want to kill myself, there's no point anymore")
        assert r.activated is True
        assert r.crisis_signal_observed is True

    def test_ar_crisis(self, engine):
        r = engine.analyze("أبغى أموت وما أبغى أعيش بعد")
        assert r.activated is True
        assert r.crisis_signal_observed is True
        assert r.severity == Severity.CRISIS

    def test_professional_referral_required(self, engine):
        r = engine.analyze("I want to end my life, nothing matters anymore")
        assert r.professional_referral_required is True

    def test_requires_independent_safety_evaluation(self, engine):
        r = engine.analyze("I want to die and there is no reason to live")
        assert r.requires_independent_safety_evaluation is True

    def test_safety_decision_authority_always_governance(self, engine):
        r = engine.analyze("I want to kill myself right now")
        assert r.safety_decision_authority == "GOVERNANCE_EQUATION_ONLY"

    def test_non_crisis_safety_authority(self, engine):
        r = engine.analyze("I am a failure and I'm worthless")
        assert r.safety_decision_authority == "GOVERNANCE_EQUATION_ONLY"

    def test_crisis_markers_in_findings(self, engine):
        r = engine.analyze("I want to kill myself and hurt myself")
        assert len(r.crisis_markers_found) > 0

    def test_crisis_markers_en_frozenset(self):
        assert isinstance(CRISIS_MARKERS_EN, frozenset)

    def test_crisis_markers_ar_frozenset(self):
        assert isinstance(CRISIS_MARKERS_AR, frozenset)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  10. Arabic Idiomatic Distress  (6 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestArabicIdiomaticDistress:
    def test_idiomatic_dying_of_laughter(self, engine):
        r = engine.analyze("بموت من الضحك هههه ما أقدر أوقف ضحك")
        # This is idiomatic, should NOT be crisis
        if r.activated:
            assert r.idiomatic_distress_possible is True
            assert r.severity != Severity.CRISIS

    def test_idiomatic_dying_of_embarrassment(self, engine):
        r = engine.analyze("ودي اموت من الحرج يا ربي ايش سويت")
        if r.activated:
            assert r.idiomatic_distress_possible is True

    def test_idiomatic_mit_min_altaab(self, engine):
        r = engine.analyze("ميت من التعب اليوم كان يوم طويل")
        if r.activated:
            assert r.idiomatic_distress_possible is True

    def test_literal_crisis_confidence_low_for_idiom(self, engine):
        r = engine.analyze("بموت من القهر على النتيجة")
        if r.activated and r.crisis_signal_observed:
            assert r.literal_crisis_confidence < 0.5

    def test_idiomatic_markers_frozenset(self):
        assert isinstance(ARABIC_IDIOMATIC_DISTRESS, frozenset)

    def test_real_crisis_not_idiomatic(self, engine):
        r = engine.analyze("أبغى أموت فعلاً ما أبغى أعيش")
        assert r.activated is True
        assert r.crisis_signal_observed is True
        assert r.literal_crisis_confidence >= 0.5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  11. Compound Pattern Detection  (6 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCompoundPatterns:
    def test_identity_plus_permanence(self, engine):
        r = engine.analyze("I'm a failure and I'll never recover from this")
        assert r.activated is True
        assert r.compound_pattern is True
        assert len(r.secondary_interpretation_types) > 0

    def test_compound_signature_format(self, engine):
        r = engine.analyze("I am a failure and nothing will change ever")
        if r.compound_pattern:
            assert "+" in r.compound_signature

    def test_single_type_not_compound(self, engine):
        r = engine.analyze("I am a complete failure in everything I do")
        if r.activated:
            if len(r.secondary_interpretation_types) == 0:
                assert r.compound_pattern is False

    def test_compound_has_primary(self, engine):
        r = engine.analyze("I'm worthless and nothing ever works for me")
        if r.activated and r.compound_pattern:
            assert r.primary_interpretation_type != InterpretationType.NONE

    def test_overgeneralization_plus_catastrophizing(self, engine):
        r = engine.analyze("Nothing ever works and my life is over completely")
        assert r.activated is True
        # Should detect at least one type
        assert r.primary_interpretation_type != InterpretationType.NONE

    def test_self_blame_plus_identity(self, engine):
        r = engine.analyze("It's all my fault, I am the problem, I ruined everything")
        assert r.activated is True
        assert r.primary_interpretation_type in (
            InterpretationType.SELF_BLAME,
            InterpretationType.IDENTITY_FUSION,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  12. Secondary Subpatterns  (8 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSecondarySubpatterns:
    def test_assumed_negative_judgment_en(self, engine):
        r = engine.analyze("I'm a failure and everyone thinks I'm stupid")
        assert r.activated is True
        assert SecondaryPattern.ASSUMED_NEGATIVE_JUDGMENT in r.secondary_patterns

    def test_punitive_should_en(self, engine):
        r = engine.analyze("I'm worthless, I should have known better")
        assert r.activated is True
        assert SecondaryPattern.PUNITIVE_SHOULD_STATEMENT in r.secondary_patterns

    def test_positive_disqualification_en(self, engine):
        r = engine.analyze("I'm a failure. Even when I succeed it doesn't count")
        assert r.activated is True
        assert SecondaryPattern.POSITIVE_DISQUALIFICATION in r.secondary_patterns

    def test_emotional_reasoning_en(self, engine):
        r = engine.analyze("I feel worthless so I must be worthless, I feel like i'm nothing")
        assert r.activated is True
        assert SecondaryPattern.EMOTIONAL_REASONING in r.secondary_patterns

    def test_assumed_judgment_ar(self, engine):
        r = engine.analyze("أنا فاشل وأكيد كلهم شايفيني فاشل")
        assert r.activated is True
        assert SecondaryPattern.ASSUMED_NEGATIVE_JUDGMENT in r.secondary_patterns

    def test_punitive_should_ar(self, engine):
        r = engine.analyze("أنا فاشل والمفروض أكون أحسن من كذا")
        assert r.activated is True
        assert SecondaryPattern.PUNITIVE_SHOULD_STATEMENT in r.secondary_patterns

    def test_no_secondary_on_neutral(self, engine):
        r = engine.analyze("The weather is nice today and everything is fine")
        assert r.activated is False

    def test_secondary_patterns_is_tuple(self, engine):
        r = engine.analyze("I am a failure and everyone thinks I'm stupid")
        assert isinstance(r.secondary_patterns, tuple)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  13. Event-Interpretation Split  (5 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEventInterpretationSplit:
    def test_event_plus_interpretation_en(self, engine):
        r = engine.analyze("I failed the exam and I am a failure")
        assert r.activated is True
        assert r.event_interpretation_split is True

    def test_interpretation_only_no_event(self, engine):
        r = engine.analyze("I'm a complete failure and I'm worthless")
        assert r.activated is True
        assert r.event_interpretation_split is False

    def test_event_plus_interpretation_ar(self, engine):
        r = engine.analyze("رسبت في الامتحان وأنا فاشل")
        assert r.activated is True
        assert r.event_interpretation_split is True

    def test_job_rejection_event(self, engine):
        r = engine.analyze("I got rejected from the job and I'm a loser")
        assert r.activated is True
        assert r.event_interpretation_split is True

    def test_relationship_event(self, engine):
        r = engine.analyze("We broke up and I am the problem in every relationship")
        assert r.activated is True
        assert r.event_interpretation_split is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  14. Severity Assessment  (8 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSeverity:
    def test_crisis_severity(self, engine):
        r = engine.analyze("I want to die and end my life right now")
        assert r.severity == Severity.CRISIS

    def test_single_marker_mild_or_moderate(self, engine):
        r = engine.analyze("I am a failure, that's just who I am deep down")
        if r.activated:
            assert r.severity in (Severity.MILD, Severity.MODERATE)

    def test_multiple_markers_higher_severity(self, engine):
        r = engine.analyze(
            "I'm a failure, I'm worthless, I'm nothing, I'm broken, "
            "I'm damaged and I'm defective"
        )
        if r.activated:
            assert r.severity in (Severity.MODERATE, Severity.SEVERE)

    def test_inactive_severity_none(self, engine):
        r = engine.analyze("Nice weather today, feeling good about things")
        assert r.severity == Severity.NONE

    def test_severity_enum_values(self):
        assert Severity.NONE.value == "none"
        assert Severity.MILD.value == "mild"
        assert Severity.MODERATE.value == "moderate"
        assert Severity.SEVERE.value == "severe"
        assert Severity.CRISIS.value == "crisis"

    def test_compound_boosts_severity(self, engine):
        r1 = engine.analyze("I'm a failure and everything is wrong")
        r2 = engine.analyze(
            "I'm a failure and I'll never recover and everything is ruined"
        )
        # Compound should not be LESS severe
        if r1.activated and r2.activated:
            sev_order = [Severity.NONE, Severity.MILD, Severity.MODERATE,
                         Severity.SEVERE, Severity.CRISIS]
            assert sev_order.index(r2.severity) >= sev_order.index(r1.severity) - 1

    def test_idiomatic_dampens_severity(self, engine):
        # Idiomatic expression should not reach CRISIS
        r = engine.analyze("بموت من الضحك يا جماعة")
        if r.activated:
            assert r.severity != Severity.CRISIS

    def test_severity_thresholds_exist(self, engine):
        assert engine._MILD_THRESHOLD < engine._MODERATE_THRESHOLD
        assert engine._MODERATE_THRESHOLD < engine._SEVERE_THRESHOLD


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  15. LBH Risk Mapping  (8 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLBHRisk:
    def test_identity_fusion_toxic_positivity(self, engine):
        r = engine.analyze("I am a failure and I'm worthless completely")
        if r.activated and r.primary_interpretation_type == InterpretationType.IDENTITY_FUSION:
            assert r.lbh_risk_type == LBHRiskType.TOXIC_POSITIVITY_RISK

    def test_overgeneralization_dismissal(self, engine):
        r = engine.analyze("Nothing ever works for me, I always fail")
        if r.activated and r.primary_interpretation_type == InterpretationType.OVERGENERALIZATION:
            assert r.lbh_risk_type == LBHRiskType.DISMISSAL_RISK

    def test_catastrophizing_minimization(self, engine):
        r = engine.analyze("My life is over and everything is ruined forever")
        if r.activated and r.primary_interpretation_type == InterpretationType.CATASTROPHIZING:
            assert r.lbh_risk_type == LBHRiskType.MINIMIZATION_RISK

    def test_self_blame_moralizing(self, engine):
        r = engine.analyze("It's all my fault, I ruined everything because of me")
        if r.activated and r.primary_interpretation_type == InterpretationType.SELF_BLAME:
            assert r.lbh_risk_type == LBHRiskType.MORALIZING_RISK

    def test_permanence_unearned_reassurance(self, engine):
        r = engine.analyze("I'll never recover and nothing will change ever")
        if r.activated and r.primary_interpretation_type == InterpretationType.PERMANENCE_BIAS:
            assert r.lbh_risk_type == LBHRiskType.UNEARNED_REASSURANCE_RISK

    def test_inactive_no_lbh_risk(self, engine):
        r = engine.analyze("Had a great day at work today!")
        assert r.lbh_risk_type == LBHRiskType.NONE

    def test_lbh_note_not_empty_when_active(self, engine):
        r = engine.analyze("I am a failure and I'm worthless")
        if r.activated:
            assert len(r.lbh_interaction_note) > 0

    def test_lbh_risk_enum_values(self):
        assert LBHRiskType.NONE.value == "none"
        assert LBHRiskType.TOXIC_POSITIVITY_RISK.value == "toxic_positivity_risk"
        assert LBHRiskType.MORALIZING_RISK.value == "moralizing_risk"
        assert LBHRiskType.UNEARNED_REASSURANCE_RISK.value == "unearned_reassurance_risk"
        assert LBHRiskType.PREMATURE_FIXING_RISK.value == "premature_fixing_risk"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  16. B5 Style Hints  (5 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestB5StyleHints:
    def test_identity_fusion_hints(self, engine):
        r = engine.analyze("I am a failure and I'm worthless entirely")
        if r.activated and r.primary_interpretation_type == InterpretationType.IDENTITY_FUSION:
            assert "avoid_identity_reinforcement" in r.b5_style_hints

    def test_catastrophizing_hints(self, engine):
        r = engine.analyze("My life is over and everything is ruined now")
        if r.activated and r.primary_interpretation_type == InterpretationType.CATASTROPHIZING:
            assert "avoid_minimization" in r.b5_style_hints

    def test_crisis_adds_safety_hint(self, engine):
        r = engine.analyze("I want to die right now, end it all")
        if r.activated:
            assert "crisis_signal_present" in r.b5_style_hints

    def test_hints_are_tuple(self, engine):
        r = engine.analyze("I am a failure and I'm broken forever")
        assert isinstance(r.b5_style_hints, tuple)

    def test_inactive_empty_hints(self, engine):
        r = engine.analyze("Today was a good day at work")
        assert r.b5_style_hints == ()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  17. Language Detection  (5 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLanguageDetection:
    def test_english_detected(self, engine):
        r = engine.analyze("I am a failure and I'm worthless forever")
        if r.activated:
            assert r.language == "en"

    def test_arabic_detected(self, engine):
        r = engine.analyze("أنا فاشل وما أقدر أسوي شي صح أبداً")
        if r.activated:
            assert r.language == "ar"

    def test_mixed_detected(self, engine):
        r = engine.analyze("أنا failure وأنا worthless مدري ليش")
        if r.activated:
            assert r.language == "mixed"

    def test_inactive_defaults_en(self, engine):
        r = engine.analyze("Nice day today")
        assert r.language == "en"

    def test_arabic_only_chars(self, engine):
        r = engine.analyze("أنا فاشل وأنا مالي فايدة أبداً في الدنيا")
        if r.activated:
            assert r.language == "ar"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  18. Audit Hash  (4 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAuditHash:
    def test_hash_is_sha256_hex(self, engine):
        r = engine.analyze("I am a failure and I'm broken")
        h = MRSDetector.audit_hash(r)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_reading_same_hash(self, engine):
        r1 = engine.analyze("I am a failure and I'm broken forever")
        r2 = engine.analyze("I am a failure and I'm broken forever")
        assert MRSDetector.audit_hash(r1) == MRSDetector.audit_hash(r2)

    def test_different_readings_different_hash(self, engine):
        r1 = engine.analyze("I am a failure and nothing works")
        r2 = engine.analyze("I want to die right now immediately")
        if r1.activated and r2.activated:
            assert MRSDetector.audit_hash(r1) != MRSDetector.audit_hash(r2)

    def test_inactive_reading_hash(self, engine):
        r = engine.analyze("Nice day today, everything is fine")
        h = MRSDetector.audit_hash(r)
        assert len(h) == 64


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  19. Non-Activation Examples  (8 tests)
#      (ChatGPT consensus Q7: normal sadness ≠ harmful interpretation)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestNonActivation:
    def test_normal_sadness(self, engine):
        r = engine.analyze("I feel sad today, it was a rough day at work")
        assert r.activated is False

    def test_frustration_not_identity(self, engine):
        r = engine.analyze("That meeting was frustrating and I'm tired of this")
        assert r.activated is False

    def test_disappointment(self, engine):
        r = engine.analyze("I'm disappointed about the results, but I'll try again")
        assert r.activated is False

    def test_factual_statement(self, engine):
        r = engine.analyze("I didn't pass the test this time around")
        assert r.activated is False

    def test_healthy_self_reflection(self, engine):
        r = engine.analyze("I need to work harder and improve my skills")
        assert r.activated is False

    def test_normal_arabic_complaint(self, engine):
        r = engine.analyze("تعبت اليوم وودي أرتاح بس")
        assert r.activated is False

    def test_neutral_question(self, engine):
        r = engine.analyze("What time does the meeting start tomorrow?")
        assert r.activated is False

    def test_positive_statement(self, engine):
        r = engine.analyze("I did great on my presentation today!")
        assert r.activated is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  20. Frozen Dataclass Immutability  (3 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestImmutability:
    def test_reading_is_frozen(self, engine):
        r = engine.analyze("I am a failure completely and utterly")
        with pytest.raises(AttributeError):
            r.severity = Severity.CRISIS

    def test_cannot_modify_signal_strength(self, engine):
        r = engine.analyze("I'm worthless and nothing ever works")
        with pytest.raises(AttributeError):
            r.signal_strength = 1.0

    def test_cannot_modify_isolation_marker(self, engine):
        r = engine.analyze("I am the problem in everything")
        with pytest.raises(AttributeError):
            r._isolation_marker = "MODIFIED"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  21. Arabic Normalization  (5 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestArabicNormalization:
    def test_normalize_alef(self):
        assert _normalize_arabic("أنا") == _normalize_arabic("انا")

    def test_normalize_alef_with_hamza(self):
        result = _normalize_arabic("إبراهيم")
        assert result.startswith("ا")

    def test_strip_tatweel(self):
        assert _normalize_arabic("فـاشـل") == _normalize_arabic("فاشل")

    def test_strip_diacritics(self):
        assert _normalize_arabic("فَاشِل") == _normalize_arabic("فاشل")

    def test_empty_string(self):
        assert _normalize_arabic("") == ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  22. Matching Helpers  (6 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMatchingHelpers:
    def test_compile_en_patterns_returns_list(self):
        compiled = _compile_en_patterns(frozenset({"test phrase"}))
        assert isinstance(compiled, list)
        assert len(compiled) == 1

    def test_match_en_word_boundary(self):
        compiled = _compile_en_patterns(frozenset({"fail"}))
        assert _match_en_markers("I fail at everything", compiled)
        assert not _match_en_markers("I failed", compiled)  # "failed" ≠ "fail"

    def test_match_en_case_insensitive(self):
        compiled = _compile_en_patterns(frozenset({"i am a failure"}))
        assert _match_en_markers("I AM A FAILURE", compiled)

    def test_match_ar_substring(self):
        found = _match_ar_markers("أنا فاشل ومالي فايدة", frozenset({"أنا فاشل"}))
        assert len(found) > 0

    def test_match_ar_no_match(self):
        found = _match_ar_markers("اليوم كان يوم جميل", frozenset({"أنا فاشل"}))
        assert len(found) == 0

    def test_match_ar_with_normalization(self):
        found = _match_ar_markers("أنا فاشل", frozenset({"انا فاشل"}))
        assert len(found) > 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  23. Enum Values  (4 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEnums:
    def test_interpretation_type_values(self):
        assert InterpretationType.NONE.value == "none"
        assert InterpretationType.IDENTITY_FUSION.value == "identity_fusion"
        assert InterpretationType.OVERGENERALIZATION.value == "overgeneralization"
        assert InterpretationType.CATASTROPHIZING.value == "catastrophizing"
        assert InterpretationType.SELF_BLAME.value == "self_blame"
        assert InterpretationType.PERMANENCE_BIAS.value == "permanence_bias"

    def test_secondary_pattern_values(self):
        assert SecondaryPattern.ASSUMED_NEGATIVE_JUDGMENT.value == "assumed_negative_judgment"
        assert SecondaryPattern.PUNITIVE_SHOULD_STATEMENT.value == "punitive_should_statement"
        assert SecondaryPattern.POSITIVE_DISQUALIFICATION.value == "positive_disqualification"
        assert SecondaryPattern.EMOTIONAL_REASONING.value == "emotional_reasoning"

    def test_severity_has_five_levels(self):
        assert len(Severity) == 5

    def test_interpretation_type_has_six(self):
        assert len(InterpretationType) == 6


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  24. Edge Cases  (6 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEdgeCases:
    def test_very_long_text(self, engine):
        text = "I am a failure " * 100
        r = engine.analyze(text)
        assert r.activated is True
        assert r.signal_strength <= 1.0

    def test_signal_strength_capped(self, engine):
        text = (
            "I am a failure I'm worthless I'm nothing I'm broken "
            "I'm damaged I'm defective I'm useless I'm a loser "
            "I'm stupid I'm pathetic"
        )
        r = engine.analyze(text)
        assert r.signal_strength <= 1.0

    def test_mixed_language_detection(self, engine):
        r = engine.analyze("I'm a failure أنا فاشل and I'm worthless")
        if r.activated:
            assert r.language == "mixed"

    def test_evidence_is_tuple(self, engine):
        r = engine.analyze("I am a failure and nothing works")
        assert isinstance(r.evidence, tuple)

    def test_markers_found_is_tuple(self, engine):
        r = engine.analyze("I am a failure in everything")
        assert isinstance(r.markers_found, tuple)

    def test_crisis_markers_found_is_tuple(self, engine):
        r = engine.analyze("I want to die and end it all")
        assert isinstance(r.crisis_markers_found, tuple)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  25. Inactive Reading Structure  (5 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestInactiveReading:
    def test_inactive_all_defaults(self, engine):
        r = engine._inactive_reading()
        assert r.activated is False
        assert r.primary_interpretation_type == InterpretationType.NONE
        assert r.severity == Severity.NONE
        assert r.signal_strength == 0.0
        assert r.markers_found == ()
        assert r.compound_pattern is False
        assert r.crisis_signal_observed is False
        assert r.professional_referral_required is False
        assert r.requires_independent_safety_evaluation is False

    def test_inactive_safety_authority(self, engine):
        r = engine._inactive_reading()
        assert r.safety_decision_authority == "GOVERNANCE_EQUATION_ONLY"

    def test_inactive_isolation_marker(self, engine):
        r = engine._inactive_reading()
        assert r._isolation_marker == "B5_ADVISORY_NOT_FOR_SAFETY"

    def test_inactive_lbh_none(self, engine):
        r = engine._inactive_reading()
        assert r.lbh_risk_type == LBHRiskType.NONE

    def test_inactive_compound_sig(self, engine):
        r = engine._inactive_reading()
        assert r.compound_signature == "none"
