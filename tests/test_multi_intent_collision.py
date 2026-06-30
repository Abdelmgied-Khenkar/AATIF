#!/usr/bin/env python3
"""
test_multi_intent_collision.py — تصادم النوايا المتعددة (FN#036)
================================================================
Covers ``engine/aatif_multi_intent_collision.py`` — the Multi-Intent Collision
Handler that detects when one message carries TWO conflicting intents, classifies
the collision into one of five categories, and recommends a resolution
(Safe-Split, Safe-Merge, or Escalate).

This module is PURE LOGIC (no embeddings, no LLM), so every test here runs
WITHOUT Ollama. Two layers:

  1. Unit tests on MultiIntentCollisionHandler.analyze — driving the handler with
     controlled Arabic/English inputs and pinning that each collision type is
     detected, that the right resolution is chosen, that the compatibility
     threshold (0.85) is respected, and that safety-relevant collisions always
     escalate.

  2. Governor integration tests — with a mocked S engine (FakeSEngine, same
     pattern as test_logic_profile_scanner.py) asserting that intent_collisions
     is attached to GovernedResponse and that ESCALATE/SAFE_SPLIT guidance is
     injected into the governed prompt, without ever changing the S(d) decision.

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

from aatif_multi_intent_collision import (  # noqa: E402
    MultiIntentCollisionHandler,
    CollisionResult,
    CollisionReading,
    IntentFragment,
    CollisionType,
    ResolutionStrategy,
    recommend_action,
    MERGE_THRESHOLD,
)


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _handler() -> MultiIntentCollisionHandler:
    return MultiIntentCollisionHandler()


def _top(result: CollisionResult) -> CollisionReading:
    """The highest-severity collision in a result (assumes at least one)."""
    from aatif_multi_intent_collision import _SEVERITY
    return max(result.collisions, key=lambda c: _SEVERITY[c.collision_type])


# ═══════════════════════════════════════════════════════════
#  CONTRACT — shape of the result
# ═══════════════════════════════════════════════════════════

class TestContract:
    def test_returns_collision_result(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        assert isinstance(r, CollisionResult)

    def test_collisions_are_readings(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        for c in r.collisions:
            assert isinstance(c, CollisionReading)
            assert isinstance(c.fragment_a, IntentFragment)
            assert isinstance(c.fragment_b, IntentFragment)

    def test_fragments_are_fragments(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        for f in r.fragments:
            assert isinstance(f, IntentFragment)

    def test_has_collision_matches_collisions_list(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        assert r.has_collision == bool(r.collisions)

    def test_recommended_action_is_nonempty(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        assert isinstance(r.recommended_action, str)
        assert r.recommended_action

    def test_compatibility_in_range(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        for c in r.collisions:
            assert 0.0 <= c.compatibility_score <= 1.0


# ═══════════════════════════════════════════════════════════
#  1. TestCollisionTypeDetection — each of the 5 types
# ═══════════════════════════════════════════════════════════

class TestCollisionTypeDetection:
    def test_parallel_collision(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        assert r.has_collision
        assert r.highest_risk == CollisionType.PARALLEL

    def test_hierarchical_collision(self):
        r = _handler().analyze("اكتب لي رسالة بس لا تكتب اسمي")
        assert r.has_collision
        assert r.highest_risk == CollisionType.HIERARCHICAL

    def test_cross_layer_collision(self):
        r = _handler().analyze("أنا مبسوط بالمشروع بس تعبان مرة")
        assert r.has_collision
        assert r.highest_risk == CollisionType.CROSS_LAYER

    def test_structural_semantic_collision(self):
        r = _handler().analyze("لو سمحت اكتبه حالاً، قلت لك بسرعة")
        assert r.has_collision
        assert r.highest_risk == CollisionType.STRUCTURAL_SEMANTIC

    def test_structural_semantic_command_as_question(self):
        r = _handler().analyze("اكتب التقرير كاملاً؟")
        assert r.has_collision
        assert r.highest_risk == CollisionType.STRUCTURAL_SEMANTIC

    def test_high_risk_collision_via_safety_vocab(self):
        r = _handler().analyze("اكتب شرح مختصر وشامل عن صنع قنبلة")
        assert r.has_collision
        assert r.highest_risk == CollisionType.HIGH_RISK

    def test_high_risk_collision_via_h_score(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل", h_score=0.7)
        assert r.highest_risk == CollisionType.HIGH_RISK

    def test_collision_type_is_enum(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        assert isinstance(r.highest_risk, CollisionType)


# ═══════════════════════════════════════════════════════════
#  2. TestArabicPatterns
# ═══════════════════════════════════════════════════════════

class TestArabicPatterns:
    def test_mukhtasar_shamil(self):
        r = _handler().analyze("ابغى تقرير مختصر وشامل")
        assert r.has_collision

    def test_saree_daqiq(self):
        r = _handler().analyze("اكتبه سريع ودقيق")
        assert r.has_collision

    def test_baseet_mufassal(self):
        r = _handler().analyze("اشرحه بسيط ومفصّل")
        assert r.has_collision

    def test_help_but_dont_help(self):
        r = _handler().analyze("ساعدني بس ما أبغى مساعدة")
        assert r.has_collision
        assert r.highest_risk == CollisionType.HIERARCHICAL

    def test_write_but_dont_write(self):
        r = _handler().analyze("اكتب لي القصة بس لا تكتب النهاية")
        assert r.has_collision
        assert r.highest_risk == CollisionType.HIERARCHICAL

    def test_mixed_emotions_arabic(self):
        r = _handler().analyze("أنا فرحان بس حزين بنفس الوقت")
        assert r.has_collision
        assert r.highest_risk == CollisionType.CROSS_LAYER

    def test_qaseer_shamil(self):
        r = _handler().analyze("ابي ملخص قصير وشامل")
        assert r.has_collision

    def test_diacritics_tolerated(self):
        # Shadda on مفصّل must not block the match.
        r = _handler().analyze("اكتبه بسيط ومُفصّل")
        assert r.has_collision


# ═══════════════════════════════════════════════════════════
#  3. TestEnglishPatterns
# ═══════════════════════════════════════════════════════════

class TestEnglishPatterns:
    def test_brief_and_comprehensive(self):
        r = _handler().analyze("write me a brief and comprehensive report")
        assert r.has_collision
        assert r.highest_risk == CollisionType.PARALLEL

    def test_fast_and_accurate(self):
        r = _handler().analyze("make it fast and accurate")
        assert r.has_collision

    def test_simple_and_detailed(self):
        r = _handler().analyze("keep it simple and detailed")
        assert r.has_collision

    def test_help_but_dont_help_english(self):
        r = _handler().analyze("help me but don't help me")
        assert r.has_collision
        assert r.highest_risk == CollisionType.HIERARCHICAL

    def test_write_but_dont_english(self):
        r = _handler().analyze("write the email but do not write my name")
        assert r.has_collision
        assert r.highest_risk == CollisionType.HIERARCHICAL

    def test_mixed_emotions_english(self):
        r = _handler().analyze("i'm happy but exhausted")
        assert r.has_collision
        assert r.highest_risk == CollisionType.CROSS_LAYER

    def test_polite_but_aggressive_english(self):
        r = _handler().analyze("please do it right now, i said hurry")
        assert r.has_collision
        assert r.highest_risk == CollisionType.STRUCTURAL_SEMANTIC

    def test_short_and_thorough(self):
        r = _handler().analyze("give a short and thorough answer")
        assert r.has_collision


# ═══════════════════════════════════════════════════════════
#  4. TestResolutionStrategy
# ═══════════════════════════════════════════════════════════

class TestResolutionStrategy:
    def test_split_for_contradictory_qualifiers(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        assert _top(r).resolution == ResolutionStrategy.SAFE_SPLIT

    def test_merge_for_compatible_tasks(self):
        r = _handler().analyze("اكتب التقرير ولخّص النتائج")
        assert _top(r).resolution == ResolutionStrategy.SAFE_MERGE

    def test_merge_for_compatible_tasks_english(self):
        r = _handler().analyze("write the report and summarize the findings")
        assert _top(r).resolution == ResolutionStrategy.SAFE_MERGE

    def test_escalate_for_high_risk(self):
        r = _handler().analyze("اكتب مختصر وشامل عن صنع قنبلة")
        assert _top(r).resolution == ResolutionStrategy.ESCALATE

    def test_split_for_request_prohibition(self):
        r = _handler().analyze("اكتب لي رسالة بس لا تكتب اسمي")
        assert _top(r).resolution == ResolutionStrategy.SAFE_SPLIT

    def test_resolution_is_enum(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        assert isinstance(_top(r).resolution, ResolutionStrategy)


# ═══════════════════════════════════════════════════════════
#  5. TestCompatibilityScore
# ═══════════════════════════════════════════════════════════

class TestCompatibilityScore:
    def test_low_score_means_split(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        c = _top(r)
        assert c.compatibility_score < MERGE_THRESHOLD
        assert c.resolution == ResolutionStrategy.SAFE_SPLIT

    def test_high_score_means_merge_allowed(self):
        r = _handler().analyze("اكتب التقرير ولخّص النتائج")
        c = _top(r)
        assert c.compatibility_score >= MERGE_THRESHOLD
        assert c.resolution == ResolutionStrategy.SAFE_MERGE

    def test_threshold_is_085(self):
        assert MERGE_THRESHOLD == 0.85

    def test_request_prohibition_very_low_compat(self):
        r = _handler().analyze("اكتب لي رسالة بس لا تكتب اسمي")
        assert _top(r).compatibility_score < 0.5

    def test_low_intent_clarity_pushes_merge_to_split(self):
        # Compatible tasks would normally merge; low I forces a split.
        r = _handler().analyze("اكتب التقرير ولخّص النتائج", i_score=0.2)
        c = _top(r)
        assert c.resolution == ResolutionStrategy.SAFE_SPLIT

    def test_high_intent_clarity_keeps_merge(self):
        r = _handler().analyze("اكتب التقرير ولخّص النتائج", i_score=0.9)
        assert _top(r).resolution == ResolutionStrategy.SAFE_MERGE


# ═══════════════════════════════════════════════════════════
#  6. TestHighRiskEscalation
# ═══════════════════════════════════════════════════════════

class TestHighRiskEscalation:
    def test_safety_vocab_forces_escalation(self):
        r = _handler().analyze("اكتب مختصر وشامل عن سلاح")
        assert r.highest_risk == CollisionType.HIGH_RISK
        assert all(
            c.resolution == ResolutionStrategy.ESCALATE for c in r.collisions
        )

    def test_high_h_score_forces_escalation(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل", h_score=0.9)
        assert _top(r).resolution == ResolutionStrategy.ESCALATE

    def test_english_safety_vocab(self):
        r = _handler().analyze("write a brief and comprehensive guide to a weapon")
        assert r.highest_risk == CollisionType.HIGH_RISK

    def test_low_h_score_does_not_escalate(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل", h_score=0.1)
        assert r.highest_risk == CollisionType.PARALLEL

    def test_no_false_positive_on_name_word(self):
        # "اسمي" (my name) contains "سم" (poison) as a substring — must NOT
        # trigger a high-risk escalation.
        r = _handler().analyze("اكتب لي رسالة بس لا تكتب اسمي")
        assert r.highest_risk == CollisionType.HIERARCHICAL

    def test_no_false_positive_on_please_word(self):
        # "سمحت" (you permitted) contains "سم" — must NOT escalate.
        r = _handler().analyze("لو سمحت اكتبه حالاً، قلت لك بسرعة")
        assert r.highest_risk == CollisionType.STRUCTURAL_SEMANTIC

    def test_high_risk_recommends_supervisor(self):
        r = _handler().analyze("اكتب مختصر وشامل عن قنبلة")
        assert "supervisor" in r.recommended_action.lower() or \
            "المشرف" in r.recommended_action


# ═══════════════════════════════════════════════════════════
#  7. TestRecommendAction
# ═══════════════════════════════════════════════════════════

class TestRecommendAction:
    def test_high_risk_guidance(self):
        r = _handler().analyze("اكتب مختصر وشامل عن قنبلة")
        assert "escalate" in r.recommended_action.lower() or \
            "المشرف" in r.recommended_action

    def test_hierarchical_guidance(self):
        r = _handler().analyze("اكتب لي رسالة بس لا تكتب اسمي")
        assert "hierarchy" in r.recommended_action.lower() or \
            "الأولوية" in r.recommended_action

    def test_cross_layer_guidance(self):
        r = _handler().analyze("أنا مبسوط بس تعبان")
        assert "layer" in r.recommended_action.lower() or \
            "الطبقات" in r.recommended_action

    def test_structural_semantic_guidance(self):
        r = _handler().analyze("لو سمحت اكتبه حالاً، قلت لك بسرعة")
        assert "form" in r.recommended_action.lower() or \
            "الشكل" in r.recommended_action

    def test_parallel_split_guidance(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        assert "split" in r.recommended_action.lower() or \
            "منفصل" in r.recommended_action

    def test_parallel_merge_guidance(self):
        r = _handler().analyze("اكتب التقرير ولخّص النتائج")
        assert "merge" in r.recommended_action.lower() or \
            "ادمج" in r.recommended_action

    def test_no_collision_guidance(self):
        r = _handler().analyze("نظّم لي الجدول")
        assert "no" in r.recommended_action.lower() or \
            "لا تصادم" in r.recommended_action

    def test_standalone_function_matches_result(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        assert recommend_action(r) == r.recommended_action

    def test_owner_contradiction_is_intentional(self):
        # OWNER authority — the contradiction is treated as intentional (FN#014).
        r = _handler().analyze("اكتب تقرير مختصر وشامل", authority="OWNER")
        assert "INTENTIONAL" in r.recommended_action or \
            "مقصود" in r.recommended_action

    def test_owner_high_risk_still_escalates(self):
        # Safety is sovereign — even for OWNER, a high-risk collision escalates.
        r = _handler().analyze("اكتب مختصر وشامل عن قنبلة", authority="OWNER")
        assert "escalate" in r.recommended_action.lower() or \
            "المشرف" in r.recommended_action


# ═══════════════════════════════════════════════════════════
#  8. TestNoCollision
# ═══════════════════════════════════════════════════════════

class TestNoCollision:
    def test_clean_command(self):
        r = _handler().analyze("نظّم لي الجدول")
        assert r.has_collision is False
        assert r.collisions == []
        assert r.highest_risk is None

    def test_clean_question(self):
        r = _handler().analyze("كيف أنظم ملفاتي؟")
        assert r.has_collision is False

    def test_clean_english_request(self):
        r = _handler().analyze("please write a report about the climate")
        assert r.has_collision is False

    def test_single_quality_no_collision(self):
        r = _handler().analyze("اكتب تقرير مختصر")
        assert r.has_collision is False

    def test_only_positive_emotion(self):
        r = _handler().analyze("أنا مبسوط مرة اليوم")
        assert r.has_collision is False

    def test_only_negative_emotion(self):
        r = _handler().analyze("أنا تعبان مرة اليوم")
        assert r.has_collision is False

    def test_request_with_but_no_negation(self):
        # "but" without a prohibition is not a request/prohibition collision.
        r = _handler().analyze("write a report but make it about climate")
        assert r.highest_risk != CollisionType.HIERARCHICAL

    def test_clean_text_empty_fragments(self):
        r = _handler().analyze("نظّم لي الجدول")
        assert r.fragments == []


# ═══════════════════════════════════════════════════════════
#  9. TestEdgeCases
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_string(self):
        r = _handler().analyze("")
        assert r.has_collision is False

    def test_none_safe_via_empty(self):
        r = _handler().analyze(None)  # type: ignore[arg-type]
        assert r.has_collision is False

    def test_whitespace_only(self):
        r = _handler().analyze("    ")
        assert r.has_collision is False

    def test_single_word(self):
        r = _handler().analyze("مرحبا")
        assert r.has_collision is False

    def test_single_char(self):
        r = _handler().analyze("a")
        assert r.has_collision is False

    def test_very_long_text(self):
        long = ("اكتب تقرير " * 400) + "مختصر وشامل"
        r = _handler().analyze(long)
        assert r.has_collision  # the contradiction is still found

    def test_mixed_arabic_english(self):
        r = _handler().analyze("اكتب report يكون brief and comprehensive")
        assert r.has_collision

    def test_h_score_none_is_safe(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل", h_score=None)
        assert r.highest_risk == CollisionType.PARALLEL

    def test_deterministic(self):
        h = _handler()
        a = h.analyze("اكتب تقرير مختصر وشامل")
        b = h.analyze("اكتب تقرير مختصر وشامل")
        assert a.highest_risk == b.highest_risk
        assert len(a.collisions) == len(b.collisions)

    def test_punctuation_only(self):
        r = _handler().analyze("؟!،.")
        assert r.has_collision is False


# ═══════════════════════════════════════════════════════════
#  OBSERVABLE-ONLY — every reading is backed by literal signals
# ═══════════════════════════════════════════════════════════

class TestObservableOnly:
    def test_fragments_text_present_in_message(self):
        msg = "اكتب تقرير مختصر وشامل"
        r = _handler().analyze(msg)
        norm_msg = msg  # raw — qualifier terms appear literally
        for f in r.fragments:
            # Each fragment's text is either a literal term or a split segment of
            # the message (request/prohibition sides), or the '?' marker.
            assert f.text == "?" or f.text in norm_msg or f.text.strip() in msg

    def test_explanations_describe_language(self):
        r = _handler().analyze("اكتب تقرير مختصر وشامل")
        for c in r.collisions:
            assert c.explanation  # non-empty, concrete justification


# ═══════════════════════════════════════════════════════════
#  10. TestGovernorIntegration
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

    def test_collision_attached_on_execute(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("اكتب تقرير مختصر وشامل", domain="general")
        assert result.intent_collisions is not None
        assert isinstance(result.intent_collisions, CollisionResult)
        assert result.intent_collisions.has_collision

    def test_split_guidance_injected_into_prompt(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("اكتب تقرير مختصر وشامل", domain="general")
        assert "FN#036" in result.governed_prompt

    def test_no_section_when_no_collision(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("نظّم لي الجدول", domain="general")
        assert "FN#036" not in result.governed_prompt
        # But the reading is still attached for the audit trail.
        assert result.intent_collisions is not None

    def test_merge_not_injected(self):
        # SAFE_MERGE is the natural default — no special prompt guidance.
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("اكتب التقرير ولخّص النتائج", domain="general")
        assert "FN#036" not in result.governed_prompt
        assert result.intent_collisions.has_collision

    def test_collision_attached_on_clarify(self):
        gov = self._make_governor(decision="CLARIFY", I=0.3)
        result = gov.process("اكتب تقرير مختصر وشامل", domain="general")
        assert result.intent_collisions is not None

    def test_collision_attached_on_safe_freeze(self):
        gov = self._make_governor(decision="SAFE_FREEZE", H=0.9, S=0.9)
        result = gov.process("اكتب مختصر وشامل", domain="general")
        assert result.blocked
        assert result.final_decision == "SAFE_FREEZE"
        # Reading runs after S compute, so it is still attached on blocked paths.
        assert result.intent_collisions is not None

    def test_collision_attached_on_safe_stop(self):
        gov = self._make_governor(decision="SAFE_STOP", H=0.7, S=0.7)
        result = gov.process("اكتب مختصر وشامل", domain="general")
        assert result.blocked
        assert result.intent_collisions is not None

    def test_governor_works_with_explicit_none_handler(self):
        from aatif_governor import AATIFGovernor, HAS_MULTI_INTENT
        fake_s = FakeSEngine(decision="EXECUTE")
        gov = AATIFGovernor(
            s_engine=fake_s,
            on_degraded="safe_stop",
            verify_backend=False,
            multi_intent_handler=None,
        )
        result = gov.process("hello", domain="general")
        assert result.final_decision == "EXECUTE"
        if HAS_MULTI_INTENT:
            # Auto-constructed when the module is importable.
            assert result.intent_collisions is not None
        else:
            assert result.intent_collisions is None

    def test_collision_never_changes_decision(self):
        # A contradictory request must not flip an EXECUTE into a block.
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process(
            "اكتب تقرير مختصر وشامل بس لا تكتب شيء", domain="general"
        )
        assert result.final_decision == "EXECUTE"
        assert not result.blocked

    def test_clean_text_decision_unchanged(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("نظّم لي الجدول", domain="general")
        assert result.final_decision == "EXECUTE"
        assert not result.blocked


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
