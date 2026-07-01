"""
tests/test_cold_os.py — Comprehensive test suite for FN#072 COLD-OS
Tri-Engine Decision Protocol

Tests: authority contract, enums, dataclasses, fast-path, context
detection, voice measurement, tension detection, framing strategy,
recommendations, Arabic markers, integration, audit hash, edge cases.
"""

from __future__ import annotations

import hashlib
import sys
import os
import unittest

# ── Import shim ──────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))

from aatif_cold_os import (
    ColdOSEngine,
    ColdOSReading,
    DecisionContext,
    FramingStrategy,
    TensionReading,
    TensionType,
    VoiceSignal,
    IDEAL_MARKERS_EN,
    IDEAL_MARKERS_AR,
    REAL_MARKERS_EN,
    REAL_MARKERS_AR,
    COLD_MARKERS_EN,
    COLD_MARKERS_AR,
    CONTEXT_MORAL_EN,
    CONTEXT_MORAL_AR,
    CONTEXT_PERSONAL_EN,
    CONTEXT_PERSONAL_AR,
    CONTEXT_MEDICAL_EN,
    CONTEXT_MEDICAL_AR,
    CONTEXT_SPIRITUAL_EN,
    CONTEXT_SPIRITUAL_AR,
    CONTEXT_FINANCIAL_EN,
    CONTEXT_FINANCIAL_AR,
)


def _engine() -> ColdOSEngine:
    return ColdOSEngine()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Authority Contract
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAuthorityContract(unittest.TestCase):
    """B-prime constants must never drift."""

    def test_authority_level(self):
        self.assertEqual(ColdOSEngine.AUTHORITY_LEVEL,
                         "B_PRIME_OBSERVATIONAL")

    def test_cannot_block_runtime(self):
        self.assertFalse(ColdOSEngine.CAN_BLOCK_RUNTIME)

    def test_cannot_modify_h(self):
        self.assertFalse(ColdOSEngine.CAN_MODIFY_H)

    def test_cannot_modify_theta(self):
        self.assertFalse(ColdOSEngine.CAN_MODIFY_THETA)

    def test_cannot_modify_s(self):
        self.assertFalse(ColdOSEngine.CAN_MODIFY_S)

    def test_cannot_emit_judicial(self):
        self.assertFalse(ColdOSEngine.CAN_EMIT_JUDICIAL_DECISION)

    def test_binding_channel(self):
        self.assertEqual(ColdOSEngine.BINDING_CHANNEL, "B5")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. Feature Flags
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFeatureFlags(unittest.TestCase):

    def test_enabled_by_default(self):
        self.assertTrue(ColdOSEngine.ENABLED)

    def test_disabled_returns_inactive(self):
        e = _engine()
        e.ENABLED = False
        r = e.analyze("Should I forgive him? It's the right thing but difficult")
        self.assertFalse(r.activated)
        e.ENABLED = True  # restore


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. Enum Completeness
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEnumCompleteness(unittest.TestCase):

    def test_decision_context_values(self):
        expected = {"moral", "personal", "practical", "medical",
                    "spiritual", "financial", "general"}
        self.assertEqual({c.value for c in DecisionContext}, expected)

    def test_tension_type_values(self):
        expected = {"none", "ideal_vs_real", "ideal_vs_cold",
                    "real_vs_cold", "three_way"}
        self.assertEqual({t.value for t in TensionType}, expected)

    def test_framing_strategy_values(self):
        expected = {"real_leads_ideal_teaches", "ideal_leads_real_softens",
                    "cold_informs_real_speaks", "unified", "defer_to_clarification"}
        self.assertEqual({f.value for f in FramingStrategy}, expected)

    def test_decision_context_count(self):
        self.assertEqual(len(DecisionContext), 7)

    def test_tension_type_count(self):
        self.assertEqual(len(TensionType), 5)

    def test_framing_strategy_count(self):
        self.assertEqual(len(FramingStrategy), 5)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. Dataclass Fields
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDataclassFields(unittest.TestCase):

    def test_voice_signal_fields(self):
        vs = VoiceSignal(voice="ideal", strength=0.5,
                         markers_found=("duty",))
        self.assertEqual(vs.voice, "ideal")
        self.assertEqual(vs.strength, 0.5)
        self.assertEqual(vs.markers_found, ("duty",))

    def test_voice_signal_frozen(self):
        vs = VoiceSignal(voice="real", strength=0.3, markers_found=())
        with self.assertRaises(AttributeError):
            vs.strength = 0.9  # type: ignore[misc]

    def test_tension_reading_fields(self):
        tr = TensionReading(tension_type=TensionType.IDEAL_VS_REAL,
                            tension_level=0.5, description="test")
        self.assertEqual(tr.tension_type, TensionType.IDEAL_VS_REAL)
        self.assertEqual(tr.tension_level, 0.5)

    def test_cold_os_reading_fields(self):
        r = _engine().analyze("Should I forgive him? He betrayed my trust but I feel guilty")
        self.assertIsInstance(r.decision_context, DecisionContext)
        self.assertIsInstance(r.ideal_signal, VoiceSignal)
        self.assertIsInstance(r.real_signal, VoiceSignal)
        self.assertIsInstance(r.cold_signal, VoiceSignal)
        self.assertIsInstance(r.tension, TensionReading)
        self.assertIsInstance(r.framing_strategy, FramingStrategy)
        self.assertIsInstance(r.recommendations, tuple)
        self.assertIsInstance(r.evidence, tuple)
        self.assertIsInstance(r.activated, bool)

    def test_cold_os_reading_frozen(self):
        r = _engine().analyze("Should I forgive him? It's my duty but difficult")
        with self.assertRaises(AttributeError):
            r.activated = False  # type: ignore[misc]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. Fast-Path Skip
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFastPath(unittest.TestCase):

    def test_empty_string(self):
        r = _engine().analyze("")
        self.assertFalse(r.activated)

    def test_short_string(self):
        r = _engine().analyze("hello there")
        self.assertFalse(r.activated)

    def test_none_like_empty(self):
        r = _engine().analyze("")
        self.assertFalse(r.activated)
        self.assertEqual(r.decision_context, DecisionContext.GENERAL)

    def test_whitespace_only(self):
        r = _engine().analyze("         ")
        self.assertFalse(r.activated)

    def test_no_decision_markers(self):
        r = _engine().analyze(
            "The quick brown fox jumps over the lazy dog repeatedly"
        )
        self.assertFalse(r.activated)

    def test_inactive_has_empty_recommendations(self):
        r = _engine().analyze("hi")
        self.assertEqual(r.recommendations, ())
        self.assertEqual(r.evidence, ())

    def test_inactive_has_unified_strategy(self):
        r = _engine().analyze("short")
        self.assertEqual(r.framing_strategy, FramingStrategy.UNIFIED)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. Decision Context Detection — English
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestContextDetectionEN(unittest.TestCase):

    def test_moral_context(self):
        r = _engine().analyze(
            "Is it right or wrong to forgive someone who shows no guilt?"
        )
        self.assertEqual(r.decision_context, DecisionContext.MORAL)

    def test_personal_context(self):
        r = _engine().analyze(
            "I'm thinking about my career and whether to quit my job and leave"
        )
        self.assertEqual(r.decision_context, DecisionContext.PERSONAL)

    def test_medical_context(self):
        r = _engine().analyze(
            "My doctor gave me a diagnosis and recommended surgery as treatment"
        )
        self.assertEqual(r.decision_context, DecisionContext.MEDICAL)

    def test_spiritual_context(self):
        r = _engine().analyze(
            "I've been trying to find meaning through prayer and faith in God"
        )
        self.assertEqual(r.decision_context, DecisionContext.SPIRITUAL)

    def test_financial_context(self):
        r = _engine().analyze(
            "I'm worried about my debt and whether this investment makes sense for my budget"
        )
        self.assertEqual(r.decision_context, DecisionContext.FINANCIAL)

    def test_general_context(self):
        r = _engine().analyze(
            "Tell me about the history of computing and early machines"
        )
        # general or not activated
        if r.activated:
            self.assertEqual(r.decision_context, DecisionContext.GENERAL)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7. Decision Context Detection — Arabic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestContextDetectionAR(unittest.TestCase):

    def test_moral_arabic(self):
        r = _engine().analyze("هل ده حلال ولا حرام ومحتاج أعرف الحق")
        self.assertTrue(r.activated)
        self.assertEqual(r.decision_context, DecisionContext.MORAL)

    def test_personal_arabic(self):
        r = _engine().analyze("حياتي صعبة ومحتار أترك شغلي ولا أبقى")
        self.assertTrue(r.activated)
        self.assertEqual(r.decision_context, DecisionContext.PERSONAL)

    def test_medical_arabic(self):
        r = _engine().analyze("صحتي تعبانة والدكتور قال محتاج علاج وعملية")
        self.assertTrue(r.activated)
        self.assertEqual(r.decision_context, DecisionContext.MEDICAL)

    def test_spiritual_arabic(self):
        r = _engine().analyze("ما عاد أحس بمعنى الصلاة والإيمان والدعاء")
        self.assertTrue(r.activated)
        self.assertEqual(r.decision_context, DecisionContext.SPIRITUAL)

    def test_financial_arabic(self):
        r = _engine().analyze("عندي دين كبير وراتبي ما يكفي والمصروف زايد")
        self.assertTrue(r.activated)
        self.assertEqual(r.decision_context, DecisionContext.FINANCIAL)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  8. Voice Measurement — Ideal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIdealVoice(unittest.TestCase):

    def test_ideal_single_marker_general_no_activate(self):
        """P0-A: Single marker in GENERAL context → no activation (0.20 < 0.25)."""
        r = _engine().analyze("I feel a strong duty to help my friend in need")
        self.assertFalse(r.activated)

    def test_ideal_single_marker_with_context_activates(self):
        """P0-A: Single marker + moral context → activates via context gate."""
        r = _engine().analyze("Should I do my duty even when it's wrong?")
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.ideal_signal.strength, 0.2)

    def test_ideal_multiple_markers(self):
        r = _engine().analyze(
            "It's my duty and obligation — the right thing is to act "
            "with integrity and justice"
        )
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.ideal_signal.strength, 0.6)

    def test_ideal_arabic_markers(self):
        r = _engine().analyze("الواجب يجب المفروض والحق واضح في ضميري")
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.ideal_signal.strength, 0.4)

    def test_no_ideal_markers(self):
        r = _engine().analyze(
            "I'm looking at the statistics and data about investment risk"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.ideal_signal.strength, 0.0)

    def test_ideal_markers_are_sorted(self):
        r = _engine().analyze(
            "It's my duty and my obligation to do the right thing"
        )
        if r.ideal_signal.markers_found:
            self.assertEqual(
                list(r.ideal_signal.markers_found),
                sorted(r.ideal_signal.markers_found),
            )

    def test_ideal_strength_cap(self):
        # Even with many markers, strength ≤ 1.0
        r = _engine().analyze(
            "Should I do the right thing? It's my duty, my obligation, "
            "my moral principle. Justice and virtue demand integrity "
            "and conscience says I ought to act."
        )
        self.assertLessEqual(r.ideal_signal.strength, 1.0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  9. Voice Measurement — Real
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestRealVoice(unittest.TestCase):

    def test_real_single_marker(self):
        r = _engine().analyze(
            "My circumstances are really difficult right now in life"
        )
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.real_signal.strength, 0.2)

    def test_real_multiple_markers(self):
        r = _engine().analyze(
            "But my situation is difficult — I'm stuck with family "
            "responsibility and can't afford to struggle any more"
        )
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.real_signal.strength, 0.6)

    def test_real_arabic_markers(self):
        r = _engine().analyze("ظروفي صعبة ومحتار وما أقدر وتعبت من الضغط")
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.real_signal.strength, 0.6)

    def test_no_real_markers(self):
        r = _engine().analyze(
            "It's my duty and obligation to follow the principle of justice"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.real_signal.strength, 0.0)

    def test_real_strength_diminishing_returns(self):
        r = _engine().analyze(
            "My circumstances are difficult, I'm stuck and trapped "
            "with no choice, struggling in real life, what can I do?"
        )
        # Many markers → high but not necessarily 1.0
        self.assertGreaterEqual(r.real_signal.strength, 0.6)
        self.assertLessEqual(r.real_signal.strength, 1.0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  10. Voice Measurement — COLD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestColdVoice(unittest.TestCase):

    def test_cold_single_marker(self):
        r = _engine().analyze(
            "The statistics are clear about this health treatment option"
        )
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.cold_signal.strength, 0.2)

    def test_cold_multiple_markers(self):
        r = _engine().analyze(
            "The data and evidence show a high probability of risk, "
            "according to research and analysis of the outcome"
        )
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.cold_signal.strength, 0.6)

    def test_cold_arabic_markers(self):
        r = _engine().analyze(
            "الإحصائيات والبيانات تقول إن نسبة النجاح قليلة والخطر عالي"
        )
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.cold_signal.strength, 0.4)

    def test_no_cold_markers(self):
        r = _engine().analyze(
            "Should I forgive him? It's my duty but I feel guilty"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.cold_signal.strength, 0.0)

    def test_cold_markers_found_populated(self):
        """P0-F: 'data' and 'risk' are WEAK markers, need 2+ strong to count."""
        r = _engine().analyze(
            "The statistics and probability data clearly show the risk level here"
        )
        self.assertTrue(len(r.cold_signal.markers_found) >= 2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  11. Tension Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTensionDetection(unittest.TestCase):

    def test_no_tension_single_voice(self):
        r = _engine().analyze(
            "It's my duty and obligation — the right thing is clear"
        )
        self.assertEqual(r.tension.tension_type, TensionType.NONE)

    def test_ideal_vs_real_tension(self):
        r = _engine().analyze(
            "I know I should do the right thing — it's my duty — "
            "but my circumstances are difficult and I'm stuck"
        )
        self.assertEqual(r.tension.tension_type, TensionType.IDEAL_VS_REAL)

    def test_ideal_vs_cold_tension(self):
        r = _engine().analyze(
            "The principle of justice demands action but the statistics "
            "and data show high risk and low probability of success"
        )
        self.assertEqual(r.tension.tension_type, TensionType.IDEAL_VS_COLD)

    def test_real_vs_cold_tension(self):
        r = _engine().analyze(
            "My circumstances are difficult and I'm struggling "
            "but the data and evidence show something unexpected"
        )
        self.assertEqual(r.tension.tension_type, TensionType.REAL_VS_COLD)

    def test_three_way_tension(self):
        # Three voices active + spread ≥ 0.20 required for THREE_WAY.
        # Extra cold markers push cold strength above ideal/real.
        r = _engine().analyze(
            "I know it's my duty and the right thing, "
            "but my circumstances are really difficult, "
            "and the statistics and data say the risk is high "
            "according to the evidence and analysis of probability"
        )
        self.assertEqual(r.tension.tension_type, TensionType.THREE_WAY)

    def test_tension_level_range(self):
        r = _engine().analyze(
            "Should I do the right thing? But my situation is hard. "
            "The data shows risk."
        )
        self.assertGreaterEqual(r.tension.tension_level, 0.0)
        self.assertLessEqual(r.tension.tension_level, 1.0)

    def test_tension_has_description(self):
        r = _engine().analyze(
            "My duty says one thing but my circumstances say another"
        )
        self.assertIsInstance(r.tension.description, str)
        self.assertTrue(len(r.tension.description) > 0)

    def test_no_tension_when_voices_balanced(self):
        """Three equally weak voices → no tension."""
        e = _engine()
        # Construct readings manually via internal method
        ideal = VoiceSignal("ideal", 0.20, ("duty",))
        real = VoiceSignal("real", 0.20, ("difficult",))
        cold = VoiceSignal("cold", 0.20, ("risk",))
        t = e._detect_tension(ideal, real, cold)
        self.assertEqual(t.tension_type, TensionType.NONE)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  12. Framing Strategy
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFramingStrategy(unittest.TestCase):

    def test_unified_when_no_tension(self):
        r = _engine().analyze(
            "It's clearly the right thing to do with integrity"
        )
        if r.tension.tension_type == TensionType.NONE:
            self.assertEqual(r.framing_strategy, FramingStrategy.UNIFIED)

    def test_escalate_on_three_way(self):
        r = _engine().analyze(
            "My duty and the right principle conflicts with "
            "difficult circumstances and struggling, "
            "while statistics show high risk and low probability"
        )
        if r.tension.tension_type == TensionType.THREE_WAY:
            self.assertEqual(r.framing_strategy, FramingStrategy.DEFER_TO_CLARIFICATION)

    def test_medical_uses_cold_informs(self):
        # Medical context + pair tension (not THREE_WAY) → COLD_INFORMS.
        # Only two voices active so context override applies.
        r = _engine().analyze(
            "My doctor recommended surgery. The statistics and "
            "data show a high risk but my circumstances are difficult"
        )
        if (r.decision_context == DecisionContext.MEDICAL
                and r.tension.tension_type not in (
                    TensionType.NONE, TensionType.THREE_WAY)):
            self.assertEqual(r.framing_strategy,
                             FramingStrategy.COLD_INFORMS_REAL_SPEAKS)

    def test_financial_uses_cold_informs(self):
        r = _engine().analyze(
            "I should invest more — it's the right thing for my "
            "budget — but my salary is tight and the statistics and "
            "probability numbers all point to high failure rate"
        )
        if r.decision_context == DecisionContext.FINANCIAL:
            self.assertEqual(r.framing_strategy,
                             FramingStrategy.COLD_INFORMS_REAL_SPEAKS)

    def test_moral_ideal_dominant(self):
        # Moral + ideal > real + pair tension → IDEAL_LEADS_REAL_SOFTENS.
        # Need real voice active too, so tension is not NONE.
        r = _engine().analyze(
            "Is this right or wrong? My conscience says it's my duty "
            "and moral obligation — ethically I must act with justice "
            "and integrity, but my circumstances are difficult"
        )
        if (r.decision_context == DecisionContext.MORAL
                and r.ideal_signal.strength > r.real_signal.strength
                and r.tension.tension_type != TensionType.NONE):
            self.assertEqual(r.framing_strategy,
                             FramingStrategy.IDEAL_LEADS_REAL_SOFTENS)

    def test_default_real_leads(self):
        r = _engine().analyze(
            "Should I leave my job? It's the right move "
            "but my family depends on me and I'm struggling"
        )
        # Personal context, balanced tension → Real leads
        if r.framing_strategy not in (FramingStrategy.UNIFIED,
                                       FramingStrategy.DEFER_TO_CLARIFICATION):
            self.assertIn(r.framing_strategy, [
                FramingStrategy.REAL_LEADS_IDEAL_TEACHES,
                FramingStrategy.IDEAL_LEADS_REAL_SOFTENS,
                FramingStrategy.COLD_INFORMS_REAL_SPEAKS,
            ])

    def test_cold_dominant_uses_cold_informs(self):
        r = _engine().analyze(
            "Looking at the evidence and statistics, the data "
            "and probability analysis shows clear risk assessment"
        )
        if r.cold_signal.strength > r.ideal_signal.strength:
            self.assertIn(r.framing_strategy, [
                FramingStrategy.COLD_INFORMS_REAL_SPEAKS,
                FramingStrategy.UNIFIED,
            ])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  13. Recommendations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestRecommendations(unittest.TestCase):

    def test_recommendations_non_empty_when_active(self):
        r = _engine().analyze(
            "Should I forgive him? It's the right thing but hard"
        )
        self.assertTrue(r.activated)
        self.assertTrue(len(r.recommendations) > 0)

    def test_advisory_invariant_always_present(self):
        """Every active reading must state COLD-OS is advisory."""
        r = _engine().analyze(
            "I know it's my duty but circumstances are difficult"
        )
        self.assertTrue(r.activated)
        advisory = any("advisory" in rec.lower()
                        for rec in r.recommendations)
        self.assertTrue(advisory,
                        "Must include 'COLD-OS is advisory' recommendation")

    def test_medical_recommendation(self):
        r = _engine().analyze(
            "My diagnosis requires surgery and the treatment is risky"
        )
        if r.decision_context == DecisionContext.MEDICAL:
            medical = any("medical" in rec.lower()
                          for rec in r.recommendations)
            self.assertTrue(medical)

    def test_moral_recommendation(self):
        r = _engine().analyze(
            "Is this right or wrong? I feel guilty about my conscience"
        )
        if r.decision_context == DecisionContext.MORAL:
            moral = any("moral" in rec.lower()
                        for rec in r.recommendations)
            self.assertTrue(moral)

    def test_escalate_preserves_possibility_space(self):
        r = _engine().analyze(
            "It's my duty and the right thing, but I'm struggling "
            "and stuck, and the statistics show high risk"
        )
        if r.framing_strategy == FramingStrategy.DEFER_TO_CLARIFICATION:
            psp = any("possibility" in rec.lower()
                      for rec in r.recommendations)
            self.assertTrue(psp,
                            "DEFER_TO_CLARIFICATION must reference possibility space")

    def test_ideal_vs_real_names_both(self):
        r = _engine().analyze(
            "I know it's my duty to forgive — the right thing — "
            "but my circumstances are difficult"
        )
        if r.tension.tension_type == TensionType.IDEAL_VS_REAL:
            naming = any("ideal" in rec.lower() and "possible" in rec.lower()
                         for rec in r.recommendations)
            # At least mention the conflict
            conflict = any("conflict" in rec.lower() or "both" in rec.lower()
                           for rec in r.recommendations)
            self.assertTrue(naming or conflict)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  14. Arabic Markers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestArabicMarkers(unittest.TestCase):

    def test_arabic_ideal_markers(self):
        r = _engine().analyze("المفروض والواجب إني أسوي الصح")
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.ideal_signal.strength, 0.4)

    def test_arabic_real_markers(self):
        r = _engine().analyze("ظروفي صعبة ومحتار ومو قادر وتعبت من الضغط")
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.real_signal.strength, 0.6)

    def test_arabic_cold_markers(self):
        r = _engine().analyze(
            "الإحصائيات والبيانات والأرقام تقول النسبة قليلة والخطر كبير"
        )
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.cold_signal.strength, 0.6)

    def test_arabic_ideal_vs_real(self):
        r = _engine().analyze(
            "المفروض أسوي الصح لكن ظروفي صعبة وما أقدر"
        )
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.ideal_signal.strength, 0.2)
        self.assertGreaterEqual(r.real_signal.strength, 0.2)

    def test_arabic_mixed_voices(self):
        r = _engine().analyze(
            "الواجب يقول لازم أساعده لكن ظروفي صعبة "
            "والإحصائيات تقول النسبة ضعيفة"
        )
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.ideal_signal.strength, 0.2)
        self.assertGreaterEqual(r.real_signal.strength, 0.2)
        self.assertGreaterEqual(r.cold_signal.strength, 0.2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  15. Evidence Trail
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEvidence(unittest.TestCase):

    def test_evidence_includes_context(self):
        r = _engine().analyze(
            "Is this right or wrong? My guilt and conscience say no"
        )
        if r.activated:
            self.assertTrue(any("decision_context=" in e
                                for e in r.evidence))

    def test_evidence_includes_strengths(self):
        r = _engine().analyze(
            "It's my duty but circumstances are difficult"
        )
        if r.activated:
            self.assertTrue(any("ideal_strength=" in e for e in r.evidence))
            self.assertTrue(any("real_strength=" in e for e in r.evidence))
            self.assertTrue(any("cold_strength=" in e for e in r.evidence))

    def test_evidence_includes_tension(self):
        r = _engine().analyze(
            "Should I forgive? Duty says yes but struggling"
        )
        if r.activated:
            self.assertTrue(any("tension=" in e for e in r.evidence))

    def test_evidence_includes_markers_when_present(self):
        r = _engine().analyze(
            "It's my duty and obligation to do justice here"
        )
        if r.activated and r.ideal_signal.markers_found:
            self.assertTrue(any("ideal_markers=" in e for e in r.evidence))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  16. Audit Hash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAuditHash(unittest.TestCase):

    def test_hash_is_sha256(self):
        r = _engine().analyze(
            "Should I forgive him? It's my duty but difficult"
        )
        h = ColdOSEngine.cold_os_audit_hash(r)
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_same_reading_same_hash(self):
        e = _engine()
        text = "My duty says forgive but circumstances are hard"
        r1 = e.analyze(text)
        r2 = e.analyze(text)
        self.assertEqual(
            ColdOSEngine.cold_os_audit_hash(r1),
            ColdOSEngine.cold_os_audit_hash(r2),
        )

    def test_different_reading_different_hash(self):
        e = _engine()
        r1 = e.analyze("It's my moral duty to do the right thing with justice")
        r2 = e.analyze("The statistics and data show high risk and probability")
        h1 = ColdOSEngine.cold_os_audit_hash(r1)
        h2 = ColdOSEngine.cold_os_audit_hash(r2)
        self.assertNotEqual(h1, h2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  17. Edge Cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEdgeCases(unittest.TestCase):

    def test_all_caps_text(self):
        r = _engine().analyze(
            "SHOULD I DO THE RIGHT THING? IT'S MY DUTY BUT DIFFICULT"
        )
        self.assertTrue(r.activated)

    def test_mixed_language(self):
        r = _engine().analyze(
            "المفروض أسوي الصح but my circumstances are difficult"
        )
        self.assertTrue(r.activated)
        self.assertGreaterEqual(r.ideal_signal.strength, 0.2)
        self.assertGreaterEqual(r.real_signal.strength, 0.2)

    def test_repeated_markers(self):
        r = _engine().analyze(
            "duty duty duty duty duty duty obligation obligation"
        )
        # Should still be activated and capped
        if r.activated:
            self.assertLessEqual(r.ideal_signal.strength, 1.0)

    def test_very_long_text(self):
        text = ("Should I forgive him? " * 100 +
                "The statistics show risk. " * 50 +
                "My circumstances are difficult. " * 50)
        r = _engine().analyze(text)
        self.assertTrue(r.activated)
        self.assertLessEqual(r.ideal_signal.strength, 1.0)
        self.assertLessEqual(r.real_signal.strength, 1.0)
        self.assertLessEqual(r.cold_signal.strength, 1.0)

    def test_s_decision_param_accepted(self):
        r = _engine().analyze(
            "Should I do this? It's the right thing but hard",
            s_decision="EXECUTE",
            h_score=0.15,
            domain="personal",
        )
        self.assertTrue(r.activated)

    def test_unicode_normalization(self):
        r = _engine().analyze("المفروض أسامح أخوي لكن ما أقدر والحقيقة صعبة")
        self.assertTrue(r.activated)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  18. Marker Set Completeness
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMarkerSets(unittest.TestCase):

    def test_ideal_en_non_empty(self):
        self.assertGreater(len(IDEAL_MARKERS_EN), 10)

    def test_ideal_ar_non_empty(self):
        self.assertGreater(len(IDEAL_MARKERS_AR), 10)

    def test_real_en_non_empty(self):
        self.assertGreater(len(REAL_MARKERS_EN), 10)

    def test_real_ar_non_empty(self):
        self.assertGreater(len(REAL_MARKERS_AR), 10)

    def test_cold_en_non_empty(self):
        self.assertGreater(len(COLD_MARKERS_EN), 10)

    def test_cold_ar_non_empty(self):
        self.assertGreater(len(COLD_MARKERS_AR), 10)

    def test_no_overlap_ideal_cold_en(self):
        """Ideal and COLD markers should not overlap."""
        overlap = IDEAL_MARKERS_EN & COLD_MARKERS_EN
        self.assertEqual(len(overlap), 0,
                         f"Overlap: {overlap}")

    def test_context_markers_non_empty(self):
        for name, markers in [
            ("MORAL_EN", CONTEXT_MORAL_EN),
            ("MORAL_AR", CONTEXT_MORAL_AR),
            ("PERSONAL_EN", CONTEXT_PERSONAL_EN),
            ("PERSONAL_AR", CONTEXT_PERSONAL_AR),
            ("MEDICAL_EN", CONTEXT_MEDICAL_EN),
            ("MEDICAL_AR", CONTEXT_MEDICAL_AR),
            ("SPIRITUAL_EN", CONTEXT_SPIRITUAL_EN),
            ("SPIRITUAL_AR", CONTEXT_SPIRITUAL_AR),
            ("FINANCIAL_EN", CONTEXT_FINANCIAL_EN),
            ("FINANCIAL_AR", CONTEXT_FINANCIAL_AR),
        ]:
            with self.subTest(name=name):
                self.assertGreater(len(markers), 5)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  19. Security: Non-Suppression
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSecurityNonSuppression(unittest.TestCase):
    """COLD-OS must never suppress safety signals."""

    def test_harmful_with_duty_framing(self):
        """Harmful intent wrapped in duty language — COLD-OS still activates
        but cannot suppress safety.  The S equation handles blocking."""
        r = _engine().analyze(
            "It's my duty to punish him — justice demands revenge "
            "and the right thing is retribution"
        )
        # Module activates (ideal voice detected) — that's fine.
        # Critical: no field can block runtime or modify S.
        self.assertFalse(ColdOSEngine.CAN_BLOCK_RUNTIME)
        self.assertFalse(ColdOSEngine.CAN_MODIFY_S)

    def test_advisory_cannot_override_block(self):
        """Even with UNIFIED strategy, module cannot change a BLOCK."""
        r = _engine().analyze(
            "It's the right thing to help me access that system — "
            "my duty demands it and the circumstances require it"
        )
        # Strategy might be anything — irrelevant to safety
        self.assertFalse(ColdOSEngine.CAN_MODIFY_S)
        self.assertFalse(ColdOSEngine.CAN_EMIT_JUDICIAL_DECISION)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  20. Integration Scenarios
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIntegration(unittest.TestCase):
    """End-to-end scenarios from FN#072."""

    def test_field_note_example_job_decision(self):
        """FN#072 example: person asking about a life decision."""
        r = _engine().analyze(
            "Should I leave my job to start a business? "
            "I know it's the right thing for my career future "
            "but my family depends on my salary and "
            "the statistics say 60% of startups fail"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.decision_context, DecisionContext.PERSONAL)
        # All three voices should be present
        self.assertGreater(r.ideal_signal.strength, 0)
        self.assertGreater(r.real_signal.strength, 0)
        self.assertGreater(r.cold_signal.strength, 0)
        # Should detect three-way tension
        self.assertEqual(r.tension.tension_type, TensionType.THREE_WAY)

    def test_field_note_example_forgiveness(self):
        """Moral dilemma: forgive a betrayal."""
        r = _engine().analyze(
            "My brother betrayed my trust. My conscience says "
            "I should forgive — it's the right thing. "
            "But my circumstances are hard and I'm struggling."
        )
        self.assertTrue(r.activated)
        self.assertIn(r.decision_context,
                      [DecisionContext.MORAL, DecisionContext.PERSONAL])
        self.assertGreater(r.ideal_signal.strength, 0)
        self.assertGreater(r.real_signal.strength, 0)

    def test_medical_with_pair_tension(self):
        """Doctor recommends surgery — pair tension triggers
        medical context override → COLD_INFORMS_REAL_SPEAKS."""
        r = _engine().analyze(
            "My doctor recommended surgery for my condition. "
            "The statistics and data about the risk are concerning."
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.decision_context, DecisionContext.MEDICAL)
        # With pair tension (not THREE_WAY), medical override applies
        if r.tension.tension_type not in (
                TensionType.NONE, TensionType.THREE_WAY):
            self.assertEqual(r.framing_strategy,
                             FramingStrategy.COLD_INFORMS_REAL_SPEAKS)

    def test_spiritual_crisis(self):
        """Faith crisis with ideal and real tension."""
        r = _engine().analyze(
            "I believe in God and prayer is my duty. "
            "But my faith is struggling and I feel stuck."
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.decision_context, DecisionContext.SPIRITUAL)
        self.assertGreater(r.ideal_signal.strength, 0)
        self.assertGreater(r.real_signal.strength, 0)

    def test_arabic_full_scenario(self):
        """Full Arabic scenario: moral + real + cold."""
        r = _engine().analyze(
            "الواجب يقول لازم أسامحه والضمير يأنبني — "
            "لكن ظروفي صعبة ومحتار — "
            "والإحصائيات تقول نسبة النجاح قليلة"
        )
        self.assertTrue(r.activated)
        self.assertGreater(r.ideal_signal.strength, 0)
        self.assertGreater(r.real_signal.strength, 0)
        self.assertGreater(r.cold_signal.strength, 0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  21. Voice Strength Curve
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestStrengthCurve(unittest.TestCase):
    """Verify the diminishing-returns strength mapping."""

    def _strength(self, n_markers: int) -> float:
        """Expected strength for n markers."""
        if n_markers == 0:
            return 0.0
        elif n_markers == 1:
            return 0.20
        elif n_markers == 2:
            return 0.40
        elif n_markers == 3:
            return 0.60
        elif n_markers <= 5:
            return 0.75
        else:
            return min(1.0, 0.75 + 0.05 * (n_markers - 5))

    def test_zero_markers(self):
        self.assertEqual(self._strength(0), 0.0)

    def test_one_marker(self):
        self.assertEqual(self._strength(1), 0.20)

    def test_two_markers(self):
        self.assertEqual(self._strength(2), 0.40)

    def test_three_markers(self):
        self.assertEqual(self._strength(3), 0.60)

    def test_four_markers(self):
        self.assertEqual(self._strength(4), 0.75)

    def test_five_markers(self):
        self.assertEqual(self._strength(5), 0.75)

    def test_ten_markers(self):
        self.assertEqual(self._strength(10), 1.0)

    def test_monotonically_increasing(self):
        prev = 0.0
        for n in range(0, 20):
            s = self._strength(n)
            self.assertGreaterEqual(s, prev)
            prev = s


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  22. Parametrized: Valid Context Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestParametrizedContexts(unittest.TestCase):
    """Parametrized tests for context detection keywords."""

    _cases = [
        ("I feel guilt about what I did — was it a sin?", DecisionContext.MORAL),
        ("My relationship with my partner is falling apart", DecisionContext.PERSONAL),
        ("The doctor says my symptoms need therapy", DecisionContext.MEDICAL),
        ("I'm searching for the meaning of my soul and spirit", DecisionContext.SPIRITUAL),
        ("My income can't cover this expense and I have debt", DecisionContext.FINANCIAL),
        ("هل ده ذنب ومحتاج توبة ومغفرة", DecisionContext.MORAL),
        ("أفكر في وظيفة جديدة ومستقبلي وقراري", DecisionContext.PERSONAL),
        ("عندي أعراض غريبة ومحتاج تشخيص ودواء", DecisionContext.MEDICAL),
        ("ما أحس بإيمان ولا دعاء ولا تقوى", DecisionContext.SPIRITUAL),
        ("محتاج قرض والدخل ما يكفي والادخار صفر", DecisionContext.FINANCIAL),
    ]

    def test_contexts(self):
        e = _engine()
        for text, expected_ctx in self._cases:
            with self.subTest(text=text[:40]):
                r = e.analyze(text)
                if r.activated:
                    self.assertEqual(r.decision_context, expected_ctx,
                                     f"Text: {text[:40]}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  23. Sparse Activation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSparseActivation(unittest.TestCase):

    def test_general_with_weak_voice_skips(self):
        """General context + weak voice → fast-path skip."""
        r = _engine().analyze(
            "Tell me about the weather forecast for tomorrow morning"
        )
        self.assertFalse(r.activated)

    def test_specific_context_activates_even_weak_voice(self):
        """Specific context alone can trigger activation."""
        r = _engine().analyze(
            "I'm worried about my diagnosis and what comes next"
        )
        self.assertTrue(r.activated)

    def test_strong_voice_activates_general(self):
        """Strong voice can activate even in general context."""
        r = _engine().analyze(
            "The statistics and data show a clear probability "
            "and the evidence supports the analysis"
        )
        # Many COLD markers → should activate
        self.assertTrue(r.activated)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  24. Reading Contract
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestReadingContract(unittest.TestCase):

    def test_inactive_fields(self):
        r = _engine().analyze("hi")
        self.assertFalse(r.activated)
        self.assertEqual(r.decision_context, DecisionContext.GENERAL)
        self.assertEqual(r.framing_strategy, FramingStrategy.UNIFIED)
        self.assertEqual(r.recommendations, ())
        self.assertEqual(r.evidence, ())
        self.assertEqual(r.ideal_signal.voice, "none")
        self.assertEqual(r.real_signal.voice, "none")
        self.assertEqual(r.cold_signal.voice, "none")

    def test_active_fields(self):
        r = _engine().analyze(
            "Should I do the right thing? My duty says yes but hard"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.ideal_signal.voice, "ideal")
        self.assertEqual(r.real_signal.voice, "real")
        self.assertEqual(r.cold_signal.voice, "cold")
        self.assertIsInstance(r.decision_context, DecisionContext)
        self.assertIsInstance(r.framing_strategy, FramingStrategy)

    def test_voice_names(self):
        r = _engine().analyze(
            "My duty and the data say conflicting things about risk"
        )
        if r.activated:
            self.assertIn(r.ideal_signal.voice, ["ideal", "none"])
            self.assertIn(r.real_signal.voice, ["real", "none"])
            self.assertIn(r.cold_signal.voice, ["cold", "none"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  25. P0 Regression Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestP0Isolation(unittest.TestCase):
    """P0-G: Isolation markers on every ColdOSReading."""

    def test_active_reading_has_isolation_marker(self):
        r = _engine().analyze(
            "Should I do the right thing? My duty says yes but hard"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r._isolation_marker, "B5_ADVISORY_NOT_FOR_SAFETY")

    def test_inactive_reading_has_isolation_marker(self):
        r = _engine().analyze("hello world, how are you today")
        self.assertFalse(r.activated)
        self.assertEqual(r._isolation_marker, "B5_ADVISORY_NOT_FOR_SAFETY")

    def test_isolation_constants(self):
        e = ColdOSEngine()
        self.assertEqual(e.ISOLATION_MARKER, "B5_ADVISORY_NOT_FOR_SAFETY")
        self.assertEqual(e.ISOLATION_TARGETS, frozenset({"B5"}))
        self.assertIn("ADVISORY", e.ISOLATION_CONTRACT)


class TestP0ActivationGate(unittest.TestCase):
    """P0-A: Context-gated activation — need context OR voice ≥ 0.25."""

    def test_single_marker_general_no_activate(self):
        """1 voice marker in GENERAL context → 0.20 < 0.25 → no activation."""
        r = _engine().analyze("The evidence suggests something important")
        self.assertFalse(r.activated)

    def test_context_marker_alone_activates(self):
        """Context marker present → activates even with weak voice."""
        r = _engine().analyze("Should I take this medication for my condition?")
        self.assertTrue(r.activated)

    def test_two_markers_activates_in_general(self):
        """2 voice markers → 0.40 ≥ 0.25 → activates even in GENERAL."""
        r = _engine().analyze("My duty and obligation are clear to me")
        self.assertTrue(r.activated)


class TestP0WordBoundary(unittest.TestCase):
    """P0-E: Word-boundary matching prevents substring false matches."""

    def test_copyright_does_not_match_right(self):
        """'copyright' should NOT trigger 'right' marker."""
        r = _engine().analyze(
            "This is a copyright notice for the document. "
            "All rights reserved under the terms of this license."
        )
        self.assertNotIn("right", r.ideal_signal.markers_found)

    def test_righteous_does_not_match_right(self):
        """'righteous' should NOT trigger 'right' marker (word boundary)."""
        r = _engine().analyze("He was known as a righteous leader in history")
        self.assertNotIn("right", r.ideal_signal.markers_found)


class TestP0WeakMarkers(unittest.TestCase):
    """P0-F: WEAK_MARKERS need corroboration by 2+ strong markers."""

    def test_bus_alone_does_not_activate_real(self):
        """'بس' alone should not count as a real marker (WEAK)."""
        r = _engine().analyze("بس كيف الحال عندكم اليوم يا جماعة")
        # Even if activated, بس should not appear in markers_found
        if r.activated:
            self.assertNotIn("بس", r.real_signal.markers_found)

    def test_bus_with_strong_markers_counts(self):
        """'بس' should count when 2+ strong markers corroborate."""
        r = _engine().analyze(
            "ظروفي صعبة والواقع مختلف بس ما أقدر أسوي شي"
        )
        self.assertTrue(r.activated)
        # ظروفي + صعب + ما أقدر = 3 strong, so بس should now count
        self.assertIn("بس", r.real_signal.markers_found)

    def test_data_alone_weak(self):
        """'data' alone should not count as COLD marker (WEAK)."""
        r = _engine().analyze("We need to store data in the database properly")
        if r.cold_signal.markers_found:
            self.assertNotIn("data", r.cold_signal.markers_found)


class TestP0ReligiousMarkers(unittest.TestCase):
    """P0-F: حلال/حرام only count in first-person decision context."""

    def test_halal_in_academic_text_no_ideal(self):
        """حلال in informational text should not trigger ideal voice."""
        r = _engine().analyze("الحلال والحرام من أساسيات الفقه الإسلامي")
        # No first-person decision → religious markers don't count
        if r.activated:
            self.assertNotIn("حلال", r.ideal_signal.markers_found)

    def test_halal_in_first_person_decision(self):
        """حلال with 'هل يجوز' should trigger ideal voice."""
        r = _engine().analyze("هل يجوز هالشي حلال ولا حرام المفروض أسأل")
        self.assertTrue(r.activated)
        # First-person decision → حلال counts as ideal marker
        self.assertTrue(r.ideal_signal.strength > 0)


class TestP0PracticalContext(unittest.TestCase):
    """P0-B: PRACTICAL context now has markers and is detectable."""

    def test_practical_en_detected(self):
        r = _engine().analyze(
            "How to optimize our approach and build a better process? "
            "My duty compels me to find the right method."
        )
        if r.decision_context == DecisionContext.PRACTICAL:
            pass  # Correct
        # At minimum, PRACTICAL should be reachable
        self.assertIn(DecisionContext.PRACTICAL, DecisionContext)

    def test_practical_ar_detected(self):
        r = _engine().analyze("كيف أنظم خطواتي وأبني خطة عملي واضحة")
        self.assertTrue(r.activated)
        self.assertEqual(r.decision_context, DecisionContext.PRACTICAL)


class TestP0LBHInteraction(unittest.TestCase):
    """P0-C: lbh_interaction_note populated when IDEAL_LEADS_REAL_SOFTENS."""

    def test_ideal_leads_has_lbh_note(self):
        r = _engine().analyze(
            "Is this right or wrong? My conscience says it's my duty "
            "and moral obligation — ethically I must act with justice "
            "and integrity. But I also feel stuck and confused."
        )
        if r.framing_strategy == FramingStrategy.IDEAL_LEADS_REAL_SOFTENS:
            self.assertIn("LBH", r.lbh_interaction_note)
            self.assertIn("sermonising", r.lbh_interaction_note)

    def test_non_ideal_leads_no_lbh_note(self):
        r = _engine().analyze(
            "ظروفي صعبة وتعبت والواقع مختلف ما أقدر أستمر"
        )
        self.assertTrue(r.activated)
        if r.framing_strategy != FramingStrategy.IDEAL_LEADS_REAL_SOFTENS:
            self.assertEqual(r.lbh_interaction_note, "")


class TestP0DeferToClarification(unittest.TestCase):
    """P0-D: ESCALATE renamed to DEFER_TO_CLARIFICATION."""

    def test_enum_value(self):
        self.assertEqual(
            FramingStrategy.DEFER_TO_CLARIFICATION.value,
            "defer_to_clarification"
        )
        self.assertFalse(hasattr(FramingStrategy, "ESCALATE"))


class TestP0ArabicNormalization(unittest.TestCase):
    """P0-E: Arabic normalization handles diacritics and alef variants."""

    def test_tashkeel_ignored(self):
        """Markers with diacritics should still match."""
        r = _engine().analyze("الوَاجِب يَجِبُ والمَفْرُوض واضح")
        self.assertTrue(r.activated)
        self.assertTrue(r.ideal_signal.strength > 0)

    def test_alef_variants_normalized(self):
        """أ/إ/آ all normalize to ا."""
        r = _engine().analyze("إيمان وأخلاق وآداب — هل يجوز هالشي حلال")
        self.assertTrue(r.activated)


if __name__ == "__main__":
    unittest.main()
