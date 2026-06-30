#!/usr/bin/env python3
"""
test_five_layer_intent.py — نية بخمس طبقات (FN#024)
=====================================================
Covers ``engine/aatif_five_layer_intent.py`` — the Five-Layer Intent Model that
reads the five simultaneous layers of intent (Primary, Secondary, Hidden,
Protective, Emotional) from a message.

This module is PURE LOGIC (no embeddings, no LLM), so every test here runs
WITHOUT Ollama.  Two layers:

  1. Unit tests on FiveLayerIntentAnalyzer.analyze — driving the analyzer with
     controlled Arabic/English inputs and pinning that each layer detects its
     own signals, that the dominant layer is identified correctly, that the
     ambiguity score behaves, and that safety-relevant intents are flagged.

  2. Governor integration tests — with a mocked S engine (FakeSEngine, same
     pattern as test_reasoning_trace.py) asserting that intent_layers is
     attached to GovernedResponse when the analyzer is wired.

License: BSL 1.1
"""
import os
import sys
import types

import pytest

# Ensure the engine directory is importable (same pattern as the other tests).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_THIS_DIR, "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_five_layer_intent import (  # noqa: E402
    FiveLayerIntentAnalyzer,
    FiveLayerResult,
    LayerReading,
    IntentLayer,
    recommend_approach,
)


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _analyzer() -> FiveLayerIntentAnalyzer:
    return FiveLayerIntentAnalyzer()


# ═══════════════════════════════════════════════════════════
#  CONTRACT TESTS — shape of the result
# ═══════════════════════════════════════════════════════════

class TestContract:
    def test_result_has_all_five_layers(self):
        r = _analyzer().analyze("كيف أنظم ملفاتي؟")
        assert isinstance(r, FiveLayerResult)
        for reading in r.as_list():
            assert isinstance(reading, LayerReading)
        layers = {reading.layer for reading in r.as_list()}
        assert layers == set(IntentLayer)

    def test_each_reading_layer_matches_field(self):
        r = _analyzer().analyze("test")
        assert r.primary.layer is IntentLayer.PRIMARY
        assert r.secondary.layer is IntentLayer.SECONDARY
        assert r.hidden.layer is IntentLayer.HIDDEN
        assert r.protective.layer is IntentLayer.PROTECTIVE
        assert r.emotional.layer is IntentLayer.EMOTIONAL

    def test_confidence_in_range(self):
        r = _analyzer().analyze("تعبت مرة من المشروع، ما عدت أقدر أكمل!")
        for reading in r.as_list():
            assert 0.0 <= reading.confidence <= 1.0

    def test_ambiguity_in_range(self):
        r = _analyzer().analyze("بس... مش متأكد")
        assert 0.0 <= r.ambiguity_score <= 1.0


# ═══════════════════════════════════════════════════════════
#  LAYER DETECTION
# ═══════════════════════════════════════════════════════════

class TestLayerDetection:
    def test_secondary_always_detected(self):
        for text in ["", "x", "كيف أسوي؟", "نظّم ملفاتي", "hello"]:
            r = _analyzer().analyze(text)
            assert r.secondary.detected, f"secondary missing for {text!r}"

    def test_primary_always_detected(self):
        r = _analyzer().analyze("anything at all")
        assert r.primary.detected

    def test_secondary_classifies_question(self):
        r = _analyzer().analyze("كيف أنظم ملفاتي؟")
        assert r.secondary.description == "question"

    def test_secondary_classifies_command(self):
        r = _analyzer().analyze("نظّم لي الملفات")
        assert r.secondary.description == "command"

    def test_secondary_classifies_greeting(self):
        r = _analyzer().analyze("السلام عليكم")
        assert r.secondary.description == "greeting"

    def test_secondary_classifies_complaint(self):
        r = _analyzer().analyze("عندي مشكلة، البرنامج ما يشتغل")
        assert r.secondary.description == "complaint"

    def test_hidden_detected_from_internal_conflict(self):
        r = _analyzer().analyze("بس... مش متأكد لو أسأل")
        assert r.hidden.detected
        assert r.hidden.signals

    def test_protective_detected_from_external_avoidance(self):
        r = _analyzer().analyze("صاحبي يبي يعرف، مو أنا")
        assert r.protective.detected

    def test_emotional_detected_from_vocab(self):
        r = _analyzer().analyze("تعبت من كل شي")
        assert r.emotional.detected

    def test_emotional_not_detected_in_neutral_text(self):
        r = _analyzer().analyze("نظّم لي الجدول")
        assert not r.emotional.detected

    def test_hidden_not_detected_in_direct_text(self):
        r = _analyzer().analyze("نظّم لي الجدول")
        assert not r.hidden.detected

    def test_protective_not_detected_in_direct_text(self):
        r = _analyzer().analyze("كيف أنظم ملفاتي؟")
        assert not r.protective.detected


# ═══════════════════════════════════════════════════════════
#  HIDDEN vs PROTECTIVE — the key distinction
# ═══════════════════════════════════════════════════════════

class TestHiddenVsProtective:
    """FN#024's core distinction: internal conflict vs external avoidance."""

    def test_internal_fear_is_hidden_not_protective(self):
        r = _analyzer().analyze("أخاف أسأل، مش متأكد من نفسي")
        assert r.hidden.detected
        assert not r.protective.detected

    def test_external_deflection_is_protective_not_hidden(self):
        r = _analyzer().analyze("قالوا لي أسأل، مو موضوعي أنا")
        assert r.protective.detected
        assert not r.hidden.detected

    def test_distinct_descriptions(self):
        hidden = _analyzer().analyze("بس مش متأكد")
        protective = _analyzer().analyze("صاحبي يسأل مو أنا")
        assert "internal" in hidden.hidden.description
        assert "external" in protective.protective.description


# ═══════════════════════════════════════════════════════════
#  ARABIC PATTERNS
# ═══════════════════════════════════════════════════════════

class TestArabicPatterns:
    def test_arabic_hedging(self):
        r = _analyzer().analyze("بس يمكن مدري")
        assert r.hidden.detected

    def test_arabic_emotional_vocab(self):
        r = _analyzer().analyze("زهقت وقهر")
        assert r.emotional.detected

    def test_arabic_intensity_amplifies_emotion(self):
        plain = _analyzer().analyze("تعبت")
        intense = _analyzer().analyze("تعبت مرة بزاف")
        assert intense.emotional.confidence >= plain.emotional.confidence

    def test_arabic_authority_citing_is_protective(self):
        r = _analyzer().analyze("قالوا لي أعمل كذا")
        assert r.protective.detected

    def test_diacritics_normalized(self):
        # Diacritized form should still detect the emotional vocab.
        r = _analyzer().analyze("تَعِبْت")
        assert r.emotional.detected


# ═══════════════════════════════════════════════════════════
#  ENGLISH PATTERNS
# ═══════════════════════════════════════════════════════════

class TestEnglishPatterns:
    def test_english_hedging_is_hidden(self):
        r = _analyzer().analyze("I'm not sure, maybe I guess")
        assert r.hidden.detected

    def test_english_asking_for_a_friend_is_protective(self):
        r = _analyzer().analyze("asking for a friend, not about me")
        assert r.protective.detected

    def test_english_emotional_vocab(self):
        r = _analyzer().analyze("I'm so frustrated and exhausted")
        assert r.emotional.detected

    def test_english_caps_is_emotional(self):
        r = _analyzer().analyze("this is RIDICULOUS")
        assert r.emotional.detected
        assert "caps" in r.emotional.signals

    def test_english_question_surface(self):
        r = _analyzer().analyze("how do I do this?")
        assert r.secondary.description == "question"


# ═══════════════════════════════════════════════════════════
#  DOMINANT LAYER
# ═══════════════════════════════════════════════════════════

class TestDominantLayer:
    def test_plain_question_dominant_secondary(self):
        r = _analyzer().analyze("كيف أنظم ملفاتي؟")
        assert r.dominant_layer is IntentLayer.SECONDARY

    def test_hidden_wins_when_strong(self):
        r = _analyzer().analyze("بس... مش متأكد، أخاف أسأل، مدري")
        assert r.dominant_layer is IntentLayer.HIDDEN

    def test_protective_dominant(self):
        r = _analyzer().analyze("صاحبي يبي يعرف، مو موضوعي، قالوا لي")
        assert r.dominant_layer is IntentLayer.PROTECTIVE

    def test_emotional_dominant(self):
        r = _analyzer().analyze("تعبت مرة مرة، زهقت، ما عدت أقدر!")
        assert r.dominant_layer is IntentLayer.EMOTIONAL

    def test_dominant_is_member_of_enum(self):
        r = _analyzer().analyze("random text here")
        assert isinstance(r.dominant_layer, IntentLayer)


# ═══════════════════════════════════════════════════════════
#  AMBIGUITY SCORE
# ═══════════════════════════════════════════════════════════

class TestAmbiguityScore:
    def test_clear_request_low_ambiguity(self):
        r = _analyzer().analyze("نظّم لي الجدول")
        assert r.ambiguity_score < 0.3

    def test_hidden_raises_ambiguity(self):
        clear = _analyzer().analyze("نظّم لي الجدول")
        hedged = _analyzer().analyze("بس... مش متأكد، مدري")
        assert hedged.ambiguity_score > clear.ambiguity_score

    def test_very_short_input_is_ambiguous(self):
        r = _analyzer().analyze("؟")
        assert r.ambiguity_score >= 0.3

    def test_low_i_score_raises_ambiguity(self):
        baseline = _analyzer().analyze("نظّم الملفات")
        lowi = _analyzer().analyze("نظّم الملفات", i_score=0.2)
        assert lowi.ambiguity_score > baseline.ambiguity_score


# ═══════════════════════════════════════════════════════════
#  SAFETY RELEVANCE
# ═══════════════════════════════════════════════════════════

class TestSafetyRelevance:
    def test_high_harm_is_safety_relevant(self):
        r = _analyzer().analyze("سؤال عادي", h_score=0.7)
        assert r.safety_relevant

    def test_protective_plus_ambiguity_is_safety_relevant(self):
        r = _analyzer().analyze("asking for a friend, not sure if it's okay")
        assert r.safety_relevant

    def test_hidden_plus_protective_is_safety_relevant(self):
        r = _analyzer().analyze("بس مش متأكد، صاحبي قالوا لي مو أنا")
        assert r.safety_relevant

    def test_plain_benign_not_safety_relevant(self):
        r = _analyzer().analyze("كيف أنظم ملفاتي؟")
        assert not r.safety_relevant


# ═══════════════════════════════════════════════════════════
#  RECOMMEND APPROACH
# ═══════════════════════════════════════════════════════════

class TestRecommendApproach:
    def test_secondary_recommends_literal_answer(self):
        r = _analyzer().analyze("كيف أنظم ملفاتي؟")
        approach = recommend_approach(r)
        assert "asked" in approach or "literal" in approach

    def test_hidden_recommends_gentle_clarification(self):
        r = _analyzer().analyze("بس... مش متأكد، أخاف أسأل، مدري")
        approach = recommend_approach(r)
        assert "clarif" in approach.lower() or "push" in approach.lower()

    def test_protective_recommends_respect_protection(self):
        r = _analyzer().analyze("صاحبي يبي يعرف، مو موضوعي، قالوا لي")
        approach = recommend_approach(r)
        assert "protect" in approach.lower() or "external" in approach.lower()

    def test_emotional_recommends_acknowledge_first(self):
        r = _analyzer().analyze("تعبت مرة مرة، زهقت، ما عدت أقدر!")
        approach = recommend_approach(r)
        assert "emotion" in approach.lower() or "acknowledge" in approach.lower()

    def test_approach_always_non_empty(self):
        for text in ["", "hi", "نظّم", "بس مدري", "تعبت!"]:
            r = _analyzer().analyze(text)
            assert recommend_approach(r).strip()


# ═══════════════════════════════════════════════════════════
#  EDGE CASES
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_string(self):
        r = _analyzer().analyze("")
        assert r.secondary.detected
        assert r.primary.detected
        assert isinstance(r.dominant_layer, IntentLayer)

    def test_whitespace_only(self):
        r = _analyzer().analyze("    ")
        assert isinstance(r, FiveLayerResult)

    def test_single_char(self):
        r = _analyzer().analyze("x")
        assert isinstance(r, FiveLayerResult)
        assert r.ambiguity_score >= 0.3

    def test_mixed_language(self):
        r = _analyzer().analyze("بس I'm not sure honestly مدري")
        assert r.hidden.detected

    def test_none_safe_via_empty(self):
        # The analyzer treats None-ish input gracefully (text or "").
        r = _analyzer().analyze(None)  # type: ignore[arg-type]
        assert isinstance(r, FiveLayerResult)

    def test_very_long_input(self):
        r = _analyzer().analyze("نظّم " * 500)
        assert isinstance(r, FiveLayerResult)


# ═══════════════════════════════════════════════════════════
#  INTEGRATION WITH H/I/E SCORES
# ═══════════════════════════════════════════════════════════

class TestIntegrationWithScores:
    def test_low_e_reinforces_emotional(self):
        without = _analyzer().analyze("ساعدني")
        withe = _analyzer().analyze("ساعدني", e_score=0.15)
        assert withe.emotional.detected
        assert not without.emotional.detected

    def test_low_i_adds_hidden_signal(self):
        r = _analyzer().analyze("نظّم الملفات", i_score=0.2)
        assert r.hidden.detected
        assert any("I=" in s for s in r.hidden.signals)

    def test_high_h_makes_safety_relevant(self):
        r = _analyzer().analyze("سؤال", h_score=0.6)
        assert r.safety_relevant

    def test_scores_default_to_zero(self):
        # No scores supplied → neutral, no E/I-derived signals.
        r = _analyzer().analyze("ساعدني")
        assert not any("E=" in s for s in r.emotional.signals)
        assert not any("I=" in s for s in r.hidden.signals)


# ═══════════════════════════════════════════════════════════
#  GOVERNOR INTEGRATION
# ═══════════════════════════════════════════════════════════

class FakeSEngine:
    """Minimal S engine that returns controlled s_result dicts (no Ollama)."""

    def __init__(self, decision="EXECUTE", H=0.1, I=0.8, E=0.2, S=0.6):
        self._decision = decision
        self._H = H
        self._I = I
        self._E = E
        self._S = S
        self.h_scorer = types.SimpleNamespace(backend_name="ollama:bge-m3")

    def compute(self, text, **kwargs):
        return {
            "decision": self._decision,
            "H": self._H,
            "I": self._I,
            "E": self._E,
            "S": self._S,
            "confidence": "high",
            "theta_effective": 0.40,
            "ambiguity_override": False,
            "F_prime": 0.5,
        }


class TestGovernorIntegration:
    def _make_governor(self, decision="EXECUTE", H=0.1, I=0.8, E=0.2, S=0.6):
        from aatif_governor import AATIFGovernor
        fake_s = FakeSEngine(decision=decision, H=H, I=I, E=E, S=S)
        return AATIFGovernor(
            s_engine=fake_s,
            on_degraded="safe_stop",
            verify_backend=False,
        )

    def test_intent_layers_attached_on_execute(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("كيف أنظم ملفاتي؟", domain="general")
        assert result.intent_layers is not None
        assert isinstance(result.intent_layers, FiveLayerResult)

    def test_intent_layers_present_on_clarify(self):
        gov = self._make_governor(decision="CLARIFY", I=0.3)
        result = gov.process("بس... مش متأكد", domain="general")
        assert result.intent_layers is not None

    def test_intent_layers_dominant_is_enum(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("نظّم لي الجدول", domain="general")
        assert isinstance(result.intent_layers.dominant_layer, IntentLayer)

    def test_clarify_hidden_enriches_prompt(self):
        gov = self._make_governor(decision="CLARIFY", I=0.3)
        result = gov.process(
            "بس... مش متأكد، أخاف أسأل، مدري", domain="general"
        )
        assert result.intent_layers is not None
        assert result.intent_layers.dominant_layer in (
            IntentLayer.HIDDEN, IntentLayer.PROTECTIVE,
        )
        # The clarification guidance should be woven into the governed prompt.
        assert "FN#024" in result.governed_prompt or \
               "طبقات" in result.governed_prompt

    def test_governor_works_with_explicit_none_analyzer(self):
        from aatif_governor import AATIFGovernor, HAS_FIVE_LAYER_INTENT
        fake_s = FakeSEngine(decision="EXECUTE")
        gov = AATIFGovernor(
            s_engine=fake_s,
            on_degraded="safe_stop",
            verify_backend=False,
            five_layer_intent=None,
        )
        result = gov.process("hello", domain="general")
        assert result.final_decision == "EXECUTE"
        if HAS_FIVE_LAYER_INTENT:
            assert result.intent_layers is not None
        else:
            assert result.intent_layers is None

    def test_safe_freeze_still_works(self):
        # Blocked path should not crash even though intent analysis runs early.
        gov = self._make_governor(decision="SAFE_FREEZE", H=0.9, S=0.9)
        result = gov.process("محتوى خطير", domain="general")
        assert result.blocked
        # intent_layers may still be attached (analysis runs after S compute).
        assert result.final_decision == "SAFE_FREEZE"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
