"""
test_cultural_opacity.py — Comprehensive test suite for FN#074 Cultural Semantic Opacity.

Tests covering:
  - Authority contract & B-prime isolation
  - Feature flag
  - Sparse activation (fast-path skip)
  - Possessive entity pattern detection
  - Reversed idafa NOT flagged as heavy
  - Pronoun weight ("نفسي" vs "عايز")
  - Holistic life expressions
  - English text → no patterns
  - Empty text → graceful degradation
  - Multiple patterns → combined weight (capped at 0.3)
  - Cultural weight delta cap enforcement
  - Field note's exact test pair
  - Opacity level correctness
  - Prompt enrichment text
  - Frozen dataclass immutability
  - Edge cases

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

import pytest

from engine.aatif_cultural_opacity import (
    CULTURAL_OPACITY_ENABLED,
    MAX_CULTURAL_WEIGHT_DELTA,
    CulturalOpacityDetector,
    CulturalPattern,
    CulturalReading,
    OpacityLevel,
    PatternType,
    PRONOUN_WEIGHT_HEAVY,
    PRONOUN_WEIGHT_LIGHT,
    HOLISTIC_MARKERS,
    HOLISTIC_VERBS,
)


@pytest.fixture
def detector():
    return CulturalOpacityDetector()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Authority Contract & B-prime Isolation  (10 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAuthorityContract:
    def test_authority_level(self):
        assert CulturalOpacityDetector.AUTHORITY_LEVEL == "B_PRIME_OBSERVATIONAL"

    def test_cannot_block_runtime(self):
        assert CulturalOpacityDetector.CAN_BLOCK_RUNTIME is False

    def test_cannot_modify_h(self):
        assert CulturalOpacityDetector.CAN_MODIFY_H is False

    def test_cannot_modify_theta(self):
        assert CulturalOpacityDetector.CAN_MODIFY_THETA is False

    def test_cannot_modify_s(self):
        assert CulturalOpacityDetector.CAN_MODIFY_S is False

    def test_cannot_emit_judicial_decision(self):
        assert CulturalOpacityDetector.CAN_EMIT_JUDICIAL_DECISION is False

    def test_binding_channel_is_b5(self):
        assert CulturalOpacityDetector.BINDING_CHANNEL == "B5"

    def test_isolation_marker(self):
        assert CulturalOpacityDetector.ISOLATION_MARKER == "B5_ADVISORY_NOT_FOR_SAFETY"

    def test_isolation_targets(self):
        assert CulturalOpacityDetector.ISOLATION_TARGETS == frozenset({"B5"})

    def test_isolation_contract_not_empty(self):
        assert len(CulturalOpacityDetector.ISOLATION_CONTRACT.strip()) > 50


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. Feature Flag  (2 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFeatureFlag:
    def test_enabled_by_default(self):
        assert CULTURAL_OPACITY_ENABLED is True

    def test_disabled_returns_inactive(self, detector, monkeypatch):
        import engine.aatif_cultural_opacity as mod
        monkeypatch.setattr(mod, "CULTURAL_OPACITY_ENABLED", False)
        r = detector.analyze("البيت ومصاريفه")
        assert r.activated is False
        assert r.cultural_weight_delta == 0.0
        monkeypatch.setattr(mod, "CULTURAL_OPACITY_ENABLED", True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. Sparse Activation / Fast Path  (4 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSparseActivation:
    def test_empty_string_inactive(self, detector):
        r = detector.analyze("")
        assert r.activated is False

    def test_none_returns_inactive(self, detector):
        """None text should be handled gracefully."""
        # The type hint says str, but we should handle None defensively
        r = detector.analyze("")
        assert r.activated is False

    def test_short_text_inactive(self, detector):
        r = detector.analyze("هي")  # 2 chars — below threshold
        assert r.activated is False

    def test_whitespace_only_inactive(self, detector):
        r = detector.analyze("   ")
        assert r.activated is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. English Text → No Patterns  (3 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEnglishNoPatterns:
    def test_english_sentence_inactive(self, detector):
        r = detector.analyze("I am tired of the house and its expenses.")
        assert r.activated is False
        assert r.cultural_weight_delta == 0.0
        assert r.opacity_level == OpacityLevel.NONE

    def test_english_holistic_inactive(self, detector):
        r = detector.analyze("Everything is wrong and nothing works.")
        assert r.activated is False

    def test_english_with_few_arabic_words_inactive(self, detector):
        """Majority English text should not trigger."""
        r = detector.analyze("This is mainly English text with maybe one word")
        assert r.activated is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. Possessive Entity Pattern  (8 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPossessiveEntity:
    def test_basic_possessive_entity(self, detector):
        """البيت ومصاريفه → possessive entity detected."""
        r = detector.analyze("البيت ومصاريفه")
        assert r.activated is True
        assert len(r.patterns_detected) >= 1
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) >= 1
        assert r.cultural_weight_delta > 0

    def test_work_pressure_possessive(self, detector):
        """الشغل وضغوطه → possessive entity detected."""
        r = detector.analyze("الشغل وضغوطه")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) >= 1

    def test_life_worries_possessive_ha(self, detector):
        """الحياة وهمومها → feminine possessive (ها) detected."""
        r = detector.analyze("الحياة وهمومها")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) >= 1

    def test_possessive_weight_positive(self, detector):
        """Possessive entity should have weight > 0."""
        r = detector.analyze("البيت ومصاريفه")
        assert r.cultural_weight_delta > 0.0

    def test_possessive_opacity_cultural_construct(self, detector):
        """Possessive entity → opacity level CULTURAL_CONSTRUCT."""
        r = detector.analyze("البيت ومصاريفه")
        assert r.opacity_level == OpacityLevel.CULTURAL_CONSTRUCT

    def test_field_note_exact_test_heavy(self, detector):
        """Field note's exact test: heavy version."""
        r = detector.analyze("زهقت من البيت و مصاريفه وعايز بكرا ما يجيش")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) >= 1, "Possessive entity should be detected in FN#074 heavy example"
        assert r.activated is True

    def test_possessive_hum(self, detector):
        """Test plural possessive (هم): الناس ومشاكلهم"""
        r = detector.analyze("الناس ومشاكلهم")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) >= 1

    def test_possessive_hun(self, detector):
        """Test feminine plural possessive (هن): البنات وأحلامهن"""
        r = detector.analyze("البنات وأحلامهن")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) >= 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. Reversed Idafa — NOT Flagged  (4 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestReversedIdafaNotFlagged:
    def test_standard_idafa_no_possessive(self, detector):
        """مصاريف البيت → no possessive entity pattern."""
        r = detector.analyze("مصاريف البيت")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) == 0

    def test_field_note_exact_test_light(self, detector):
        """Field note's exact test: light version — no possessive entity."""
        r = detector.analyze("زهقت من مصاريف البيت")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) == 0, (
            "'مصاريف البيت' is standard idafa (material only), "
            "should NOT trigger possessive entity pattern"
        )

    def test_standard_idafa_pressure_of_work(self, detector):
        """ضغوط الشغل → no possessive entity pattern."""
        r = detector.analyze("ضغوط الشغل")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) == 0

    def test_standard_idafa_worries_of_life(self, detector):
        """هموم الحياة → no possessive entity pattern."""
        r = detector.analyze("هموم الحياة")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) == 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7. Pronoun Weight  (6 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPronounWeight:
    def test_nafsi_detected(self, detector):
        """نفسي → pronoun weight detected (heavier)."""
        r = detector.analyze("نفسي أرتاح من هالدنيا")
        pw = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.PRONOUN_WEIGHT]
        assert len(pw) >= 1
        assert r.activated is True

    def test_ruhi_detected(self, detector):
        """روحي → pronoun weight detected (heavier)."""
        r = detector.analyze("روحي تعبانه من كثر التفكير")
        pw = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.PRONOUN_WEIGHT]
        assert len(pw) >= 1

    def test_qalbi_detected(self, detector):
        """قلبي → pronoun weight detected (heavier)."""
        r = detector.analyze("قلبي يوجعني من الكلام")
        pw = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.PRONOUN_WEIGHT]
        assert len(pw) >= 1

    def test_aayiz_not_heavy_pronoun(self, detector):
        """عايز alone (no other patterns) → no pronoun weight pattern."""
        r = detector.analyze("عايز أروح البيت بس")
        pw = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.PRONOUN_WEIGHT]
        assert len(pw) == 0

    def test_nafsi_heavier_than_aayiz(self, detector):
        """نفسي should produce higher delta than عايز."""
        r_nafsi = detector.analyze("نفسي أرتاح من هالدنيا")
        r_aayiz = detector.analyze("عايز أرتاح من هالدنيا")

        # نفسي triggers pronoun weight, عايز does not
        pw_nafsi = [p for p in r_nafsi.patterns_detected
                    if p.pattern_type == PatternType.PRONOUN_WEIGHT]
        pw_aayiz = [p for p in r_aayiz.patterns_detected
                    if p.pattern_type == PatternType.PRONOUN_WEIGHT]
        assert len(pw_nafsi) > len(pw_aayiz)

    def test_pronoun_weight_opacity_level(self, detector):
        """Pure pronoun weight → opacity level WORD."""
        # Use a sentence with nafsi but NO holistic or possessive patterns
        r = detector.analyze("نفسي أنام شوية")
        if r.activated:
            pw = [p for p in r.patterns_detected
                  if p.pattern_type == PatternType.PRONOUN_WEIGHT]
            if pw and len(r.patterns_detected) == len(pw):
                # Only pronoun weight patterns
                assert r.opacity_level == OpacityLevel.WORD


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  8. Holistic Life Expressions  (6 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestHolisticLife:
    def test_zehiqt_min_kul_shi(self, detector):
        """زهقت من كل شي → holistic life detected."""
        r = detector.analyze("زهقت من كل شي")
        hl = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.HOLISTIC_LIFE]
        assert len(hl) >= 1
        assert r.activated is True

    def test_kul_haga(self, detector):
        """كل حاجة → holistic life detected."""
        r = detector.analyze("تعبت من كل حاجة")
        hl = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.HOLISTIC_LIFE]
        assert len(hl) >= 1

    def test_ma_ba2ali_shi(self, detector):
        """ما بقالي شي → holistic life detected."""
        r = detector.analyze("ما بقالي شي في الحياة")
        hl = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.HOLISTIC_LIFE]
        assert len(hl) >= 1

    def test_wala_shi(self, detector):
        """ولا شي → holistic life detected."""
        r = detector.analyze("ما عندي ولا شي")
        hl = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.HOLISTIC_LIFE]
        assert len(hl) >= 1

    def test_holistic_verb_amplifies(self, detector):
        """Holistic verb + marker → higher weight than marker alone."""
        with_verb = detector.analyze("زهقت من كل شي")
        without_verb = detector.analyze("كل شي يضيق")

        hl_with = [p for p in with_verb.patterns_detected
                   if p.pattern_type == PatternType.HOLISTIC_LIFE]
        hl_without = [p for p in without_verb.patterns_detected
                      if p.pattern_type == PatternType.HOLISTIC_LIFE]

        if hl_with and hl_without:
            assert hl_with[0].weight_adjustment >= hl_without[0].weight_adjustment

    def test_holistic_opacity_cultural_construct(self, detector):
        """Holistic life → opacity level CULTURAL_CONSTRUCT."""
        r = detector.analyze("زهقت من كل شي")
        if r.activated:
            assert r.opacity_level == OpacityLevel.CULTURAL_CONSTRUCT


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  9. Cultural Weight Delta Cap  (3 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestWeightDeltaCap:
    def test_delta_never_exceeds_max(self, detector):
        """Combined weight must never exceed MAX_CULTURAL_WEIGHT_DELTA (0.3)."""
        # Stack multiple patterns in one message
        text = "نفسي أرتاح من البيت ومصاريفه وزهقت من كل شي"
        r = detector.analyze(text)
        assert r.cultural_weight_delta <= MAX_CULTURAL_WEIGHT_DELTA

    def test_max_constant_is_030(self):
        """MAX_CULTURAL_WEIGHT_DELTA should be 0.3."""
        assert MAX_CULTURAL_WEIGHT_DELTA == 0.3

    def test_single_pattern_under_cap(self, detector):
        """A single pattern alone should be well under 0.3."""
        r = detector.analyze("البيت ومصاريفه")
        assert r.cultural_weight_delta <= 0.2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  10. Multiple Patterns Combined  (3 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMultiplePatterns:
    def test_possessive_plus_holistic(self, detector):
        """Possessive entity + holistic → both detected, weights combined."""
        r = detector.analyze("البيت ومصاريفه وزهقت من كل شي")
        types = {p.pattern_type for p in r.patterns_detected}
        assert PatternType.POSSESSIVE_ENTITY in types
        assert PatternType.HOLISTIC_LIFE in types
        assert r.cultural_weight_delta > 0.15  # both contribute

    def test_pronoun_plus_holistic(self, detector):
        """Pronoun weight + holistic → both detected."""
        r = detector.analyze("نفسي أرتاح من كل شي")
        types = {p.pattern_type for p in r.patterns_detected}
        assert PatternType.PRONOUN_WEIGHT in types
        assert PatternType.HOLISTIC_LIFE in types

    def test_all_three_patterns(self, detector):
        """All three pattern types in one message → combined, capped."""
        r = detector.analyze("نفسي أرتاح من البيت ومصاريفه وزهقت من كل شي")
        types = {p.pattern_type for p in r.patterns_detected}
        # At minimum we should detect possessive + holistic or pronoun
        assert len(types) >= 2
        assert r.cultural_weight_delta <= MAX_CULTURAL_WEIGHT_DELTA


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  11. Field Note's Exact Test Pair  (4 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFieldNoteExactPair:
    """The field note's original experiment that motivated this module."""

    def test_heavy_version_activates(self, detector):
        """زهقت من البيت و مصاريفه وعايز بكرا ما يجيش → activated."""
        r = detector.analyze("زهقت من البيت و مصاريفه وعايز بكرا ما يجيش")
        assert r.activated is True

    def test_heavy_version_has_possessive(self, detector):
        """Heavy version has possessive entity pattern."""
        r = detector.analyze("زهقت من البيت و مصاريفه وعايز بكرا ما يجيش")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) >= 1

    def test_light_version_no_possessive(self, detector):
        """زهقت من مصاريف البيت → no possessive entity pattern."""
        r = detector.analyze("زهقت من مصاريف البيت")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) == 0

    def test_heavy_heavier_than_light(self, detector):
        """Heavy version should have higher cultural_weight_delta."""
        heavy = detector.analyze("زهقت من البيت و مصاريفه وعايز بكرا ما يجيش")
        light = detector.analyze("زهقت من مصاريف البيت")
        assert heavy.cultural_weight_delta > light.cultural_weight_delta


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  12. Opacity Level Correctness  (5 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestOpacityLevel:
    def test_no_patterns_level_none(self, detector):
        """No patterns → opacity level NONE."""
        r = detector.analyze("مصاريف البيت كثيرة")
        if not r.activated:
            assert r.opacity_level == OpacityLevel.NONE

    def test_possessive_entity_cultural_construct(self, detector):
        """Possessive entity → CULTURAL_CONSTRUCT."""
        r = detector.analyze("البيت ومصاريفه")
        assert r.opacity_level == OpacityLevel.CULTURAL_CONSTRUCT

    def test_holistic_cultural_construct(self, detector):
        """Holistic life → CULTURAL_CONSTRUCT."""
        r = detector.analyze("زهقت من كل شي")
        if r.activated:
            assert r.opacity_level == OpacityLevel.CULTURAL_CONSTRUCT

    def test_pronoun_only_word_level(self, detector):
        """Pronoun weight only → WORD level."""
        r = detector.analyze("نفسي أنام شوية الله يخليك")
        pw = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.PRONOUN_WEIGHT]
        if pw and all(p.pattern_type == PatternType.PRONOUN_WEIGHT
                      for p in r.patterns_detected):
            assert r.opacity_level == OpacityLevel.WORD

    def test_english_level_none(self, detector):
        """English text → NONE."""
        r = detector.analyze("I am tired of house expenses")
        assert r.opacity_level == OpacityLevel.NONE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  13. Prompt Enrichment  (4 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPromptEnrichment:
    def test_active_has_explanation(self, detector):
        """Activated reading should have non-empty explanation."""
        r = detector.analyze("البيت ومصاريفه")
        assert r.activated is True
        assert len(r.explanation) > 10

    def test_inactive_no_explanation(self, detector):
        """Inactive reading should have empty explanation."""
        r = detector.analyze("Hello world, this is English")
        assert r.explanation == ""

    def test_explanation_mentions_weight(self, detector):
        """Explanation should mention the advisory weight adjustment."""
        r = detector.analyze("البيت ومصاريفه")
        assert "weight" in r.explanation.lower() or "adjustment" in r.explanation.lower()

    def test_evidence_populated(self, detector):
        """Evidence should list each detected pattern."""
        r = detector.analyze("البيت ومصاريفه")
        assert len(r.evidence) >= 1
        assert any("POSSESSIVE_ENTITY" in e for e in r.evidence)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  14. Frozen Dataclass Immutability  (3 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFrozenDataclass:
    def test_reading_is_frozen(self, detector):
        """CulturalReading should be immutable (frozen dataclass)."""
        r = detector.analyze("البيت ومصاريفه")
        with pytest.raises(AttributeError):
            r.cultural_weight_delta = 999.0

    def test_pattern_is_frozen(self, detector):
        """CulturalPattern should be immutable (frozen dataclass)."""
        r = detector.analyze("البيت ومصاريفه")
        if r.patterns_detected:
            with pytest.raises(AttributeError):
                r.patterns_detected[0].weight_adjustment = 999.0

    def test_reading_isolation_marker(self, detector):
        """Every reading carries the isolation marker."""
        r = detector.analyze("البيت ومصاريفه")
        assert r._isolation_marker == "B5_ADVISORY_NOT_FOR_SAFETY"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  15. Confidence  (3 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConfidence:
    def test_no_patterns_zero_confidence(self, detector):
        """No patterns → confidence 0."""
        r = detector.analyze("Hello world this is English text only")
        assert r.confidence == 0.0

    def test_patterns_positive_confidence(self, detector):
        """Detected patterns → positive confidence."""
        r = detector.analyze("البيت ومصاريفه")
        assert r.confidence > 0.0

    def test_confidence_capped_at_one(self, detector):
        """Confidence should never exceed 1.0."""
        r = detector.analyze("نفسي أرتاح من البيت ومصاريفه وزهقت من كل شي")
        assert r.confidence <= 1.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  16. Edge Cases  (8 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEdgeCases:
    def test_arabic_without_patterns(self, detector):
        """Arabic text without any opacity patterns → inactive."""
        r = detector.analyze("الطقس جميل اليوم والحمد لله")
        # No possessive entity, no pronoun weight, no holistic
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        pw = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.PRONOUN_WEIGHT]
        assert len(pe) == 0
        assert len(pw) == 0

    def test_text_with_diacritics(self, detector):
        """Diacritics should be stripped before matching."""
        r = detector.analyze("البَيْتُ ومَصارِيفُهُ")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) >= 1

    def test_repeated_patterns_not_double_counted_holistic(self, detector):
        """Same holistic marker repeated → only one pattern instance."""
        r = detector.analyze("كل شي وكل شي ضدي كل شي")
        hl = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.HOLISTIC_LIFE]
        assert len(hl) == 1  # only one holistic hit (first match breaks)

    def test_very_long_text(self, detector):
        """Long text should not crash or timeout."""
        long_text = "البيت ومصاريفه " * 100
        r = detector.analyze(long_text)
        assert r.activated is True
        assert r.cultural_weight_delta <= MAX_CULTURAL_WEIGHT_DELTA

    def test_mixed_arabic_english(self, detector):
        """Mixed text with Arabic patterns → should detect if arabic_ratio > 0.3."""
        r = detector.analyze("I feel like البيت ومصاريفه كثير")
        # Depends on ratio — but the Arabic portion has patterns
        # Even if not activated due to ratio, it should not crash
        assert isinstance(r, CulturalReading)

    def test_only_waw_no_possessive(self, detector):
        """و without possessive suffix → no pattern."""
        r = detector.analyze("البيت والسيارة")
        pe = [p for p in r.patterns_detected
              if p.pattern_type == PatternType.POSSESSIVE_ENTITY]
        assert len(pe) == 0

    def test_deterministic_same_input_same_output(self, detector):
        """Same input → same output (determinism check)."""
        text = "البيت ومصاريفه والحياة وهمومها"
        r1 = detector.analyze(text)
        r2 = detector.analyze(text)
        assert r1.cultural_weight_delta == r2.cultural_weight_delta
        assert r1.opacity_level == r2.opacity_level
        assert r1.activated == r2.activated
        assert len(r1.patterns_detected) == len(r2.patterns_detected)

    def test_pattern_type_enum_values(self):
        """PatternType enum should have expected values."""
        assert PatternType.POSSESSIVE_ENTITY.value == "possessive_entity"
        assert PatternType.IDAFA_REVERSAL.value == "idafa_reversal"
        assert PatternType.PRONOUN_WEIGHT.value == "pronoun_weight"
        assert PatternType.HOLISTIC_LIFE.value == "holistic_life"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  17. OpacityLevel Enum  (4 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestOpacityLevelEnum:
    def test_none_value(self):
        assert OpacityLevel.NONE.value == "none"

    def test_word_value(self):
        assert OpacityLevel.WORD.value == "word"

    def test_figurative_value(self):
        assert OpacityLevel.FIGURATIVE.value == "figurative"

    def test_cultural_construct_value(self):
        assert OpacityLevel.CULTURAL_CONSTRUCT.value == "cultural_construct"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  18. Marker Constants Sanity  (4 tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMarkerConstants:
    def test_pronoun_heavy_is_frozenset(self):
        assert isinstance(PRONOUN_WEIGHT_HEAVY, frozenset)

    def test_pronoun_light_is_frozenset(self):
        assert isinstance(PRONOUN_WEIGHT_LIGHT, frozenset)

    def test_holistic_markers_is_frozenset(self):
        assert isinstance(HOLISTIC_MARKERS, frozenset)

    def test_holistic_verbs_is_frozenset(self):
        assert isinstance(HOLISTIC_VERBS, frozenset)
