#!/usr/bin/env python3
"""
Response-shaper tests for aatif_response_shaper.py — Agent فاحص (Fahes)

WHY THIS FILE EXISTS
────────────────────
The Response Shaper is the last governance hop before the LLM speaks. The
intent engine produces a number — S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))] — and a
decision (EXECUTE/CLARIFY/SAFE_STOP/SAFE_FREEZE). None of that is language yet.
The shaper is "where math becomes tone": it turns the decision into a response
mode, the softening factor S into a firmness number, the dialect tag into a word
choice, and the emotional reading into a forbidden-phrase list.

As of 2026-06-22 this module had ZERO direct test coverage (alongside
aatif_conversation_memory.py). This file closes the shaper gap. It does NOT
touch the LLM — the shaper never generates text, it builds the meaning
instruction — so every assertion here is deterministic and needs no model.

WHAT IS GOVERNANCE-RELEVANT HERE (and therefore worth a regression wall)
───────────────────────────────────────────────────────────────────────
  1. decision → mode mapping must be total and must fail SAFE.
     An unknown/garbled decision must NOT map to "answer". It maps to "clarify"
     (ask, don't guess) — the same fail-safe philosophy as the S equation.
  2. firmness F = max(D·(1−S), k·H) — the harm floor.
     Mercy (high S) releases the brake, BUT the k·H floor guarantees that a
     harmful request can never be answered with zero firmness no matter how
     warm the person sounds. This is the shaper's echo of the toxic-positivity
     defence: warmth must not dissolve firmness on harm.
  3. the always-forbidden list — the "no robotic AI phrasing" constitutional
     rule, made mechanical. "as an AI", "كنموذج لغوي", "governance layer",
     and false-comfort "لا تقلق" must ALWAYS be blocked, every mode, every turn.
  4. context-sensitive forbidden phrases — when someone is carrying weight,
     dismissive words ("just", "it's easy", "ما عليك") must be added to the
     block list. Compassion is enforced, not hoped for.
  5. tone/length de-escalation — load_bearing and an escalated memory arc must
     pull tone to "gentle" and length to "short". A person in collapse should
     not get a long, breezy answer.

ISOLATION STRATEGY
──────────────────
The shaper consumes a duck-typed `reading` object (the real one is the intent
engine's IntentReading). We inject a FakeReading exposing exactly the attributes
shape() touches — identical strategy to the demo() block in the module itself
and to the fake-backend approach in test_emotion_scorer.py. No engine wiring,
no Ollama, no sklearn. Pure contract tests on the shaper's logic.
"""

import unittest

from aatif_response_shaper import (
    AATIFResponseShaper,
    ResponseShape,
    _ALWAYS_FORBIDDEN,
    _DIALECT_INSTRUCTIONS,
)


class FakeReading:
    """Duck-typed stand-in for the engine's IntentReading.

    Defaults mirror the demo() FakeReading: a calm, clear, safe EXECUTE.
    Every test overrides only the fields it cares about.
    """

    def __init__(self, **kwargs):
        defaults = {
            "decision": "EXECUTE",
            "decision_reason": "",
            "mode": "NORMAL",
            "emotional_state": "clear",
            "emotional_confidence": 0.8,
            "load_bearing": False,
            "dialect_detected": "saudi",
            "ambiguity_score": 0.1,
            "harm_score": 0.0,
            "softening_factor": 0.5,
            "skills_to_activate": [],
            "deep_intent": "",
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


# ═══════════════════════════════════════════════════════════
#  1. decision → mode mapping (must be total + fail-safe)
# ═══════════════════════════════════════════════════════════
class TestDecisionToMode(unittest.TestCase):
    def setUp(self):
        self.shaper = AATIFResponseShaper()

    def test_execute_maps_to_answer(self):
        self.assertEqual(self.shaper._decision_to_mode("EXECUTE"), "answer")

    def test_clarify_maps_to_clarify(self):
        self.assertEqual(self.shaper._decision_to_mode("CLARIFY"), "clarify")

    def test_safe_stop_maps_to_stop(self):
        self.assertEqual(self.shaper._decision_to_mode("SAFE_STOP"), "stop")

    def test_safe_freeze_maps_to_freeze(self):
        self.assertEqual(self.shaper._decision_to_mode("SAFE_FREEZE"), "freeze")

    def test_unknown_decision_fails_safe_to_clarify(self):
        # Garbage in must NOT become "answer". Ask, don't guess.
        for junk in ["", "GO", "EXECUTE_NOW", "yes", None, "execute"]:
            self.assertEqual(
                self.shaper._decision_to_mode(junk), "clarify",
                f"unknown decision {junk!r} must fail-safe to clarify",
            )

    def test_shape_propagates_mode(self):
        shape = self.shaper.shape(FakeReading(decision="SAFE_FREEZE"))
        self.assertEqual(shape.response_mode, "freeze")


# ═══════════════════════════════════════════════════════════
#  2. compute_firmness — F = max(D·(1−S), k·H)
# ═══════════════════════════════════════════════════════════
class TestComputeFirmness(unittest.TestCase):
    def setUp(self):
        self.shaper = AATIFResponseShaper()

    def test_pre_floor_formula_when_harm_zero(self):
        # H = 0 ⇒ floor = 0 ⇒ F = D·(1−S). D defaults to 1.0.
        self.assertAlmostEqual(self.shaper.compute_firmness(0.5, harm_score=0.0), 0.5)
        self.assertAlmostEqual(self.shaper.compute_firmness(0.0, harm_score=0.0), 1.0)
        self.assertAlmostEqual(self.shaper.compute_firmness(1.0, harm_score=0.0), 0.0)

    def test_directness_scales_pre_floor(self):
        # D = 2.0, S = 0.5 ⇒ F' = 2*(0.5) = 1.0
        self.assertAlmostEqual(
            self.shaper.compute_firmness(0.5, directness=2.0, harm_score=0.0), 1.0
        )

    def test_harm_floor_dominates_when_mercy_high(self):
        # The toxic-positivity echo: S = 1.0 would give F' = 0, but harm = 0.8
        # forces F ≥ k*H = 0.3*0.8 = 0.24. Warmth cannot zero out firmness on harm.
        f = self.shaper.compute_firmness(1.0, harm_score=0.8, k=0.3)
        self.assertAlmostEqual(f, 0.24)
        self.assertGreater(f, 0.0)

    def test_pre_floor_wins_when_larger_than_floor(self):
        # S = 0.2 ⇒ F' = 0.8; floor = 0.3*0.5 = 0.15 ⇒ max picks 0.8.
        self.assertAlmostEqual(
            self.shaper.compute_firmness(0.2, harm_score=0.5, k=0.3), 0.8
        )

    def test_softening_clamped_to_unit_interval(self):
        # S below 0 and above 1 must be clamped before use.
        self.assertAlmostEqual(self.shaper.compute_firmness(-5.0, harm_score=0.0), 1.0)
        self.assertAlmostEqual(self.shaper.compute_firmness(5.0, harm_score=0.0), 0.0)

    def test_harm_clamped_to_unit_interval(self):
        # H above 1 clamps to 1 ⇒ floor = k*1 = 0.3 (with S=1 so F'=0).
        self.assertAlmostEqual(
            self.shaper.compute_firmness(1.0, harm_score=5.0, k=0.3), 0.3
        )

    def test_monotonic_decreasing_in_softening(self):
        # More mercy ⇒ less firmness (when harm is held at 0).
        vals = [self.shaper.compute_firmness(s, harm_score=0.0)
                for s in (0.0, 0.25, 0.5, 0.75, 1.0)]
        self.assertTrue(all(a >= b for a, b in zip(vals, vals[1:])),
                        f"firmness must be non-increasing in S, got {vals}")

    def test_monotonic_nondecreasing_in_harm(self):
        # More harm ⇒ floor rises ⇒ firmness cannot drop (held S = 1.0).
        vals = [self.shaper.compute_firmness(1.0, harm_score=h)
                for h in (0.0, 0.25, 0.5, 0.75, 1.0)]
        self.assertTrue(all(a <= b for a, b in zip(vals, vals[1:])),
                        f"firmness must be non-decreasing in H, got {vals}")

    def test_firmness_is_nonnegative(self):
        for s in (0.0, 0.5, 1.0):
            for h in (0.0, 0.5, 1.0):
                self.assertGreaterEqual(self.shaper.compute_firmness(s, harm_score=h), 0.0)

    def test_shape_rounds_firmness_to_three_places(self):
        # The public ResponseShape rounds firmness to 3 dp. 1/3 ≈ 0.333.
        shape = self.shaper.shape(FakeReading(softening_factor=2.0 / 3.0, harm_score=0.0))
        self.assertEqual(shape.firmness, round(1.0 - 2.0 / 3.0, 3))


# ═══════════════════════════════════════════════════════════
#  3. forbidden phrases — the robotic-phrasing constitutional ban
# ═══════════════════════════════════════════════════════════
class TestForbiddenPhrases(unittest.TestCase):
    def setUp(self):
        self.shaper = AATIFResponseShaper()

    def test_always_forbidden_present_every_mode(self):
        # The block list must survive in answer/clarify/stop/freeze alike.
        for decision in ("EXECUTE", "CLARIFY", "SAFE_STOP", "SAFE_FREEZE"):
            shape = self.shaper.shape(FakeReading(decision=decision))
            for phrase in _ALWAYS_FORBIDDEN:
                self.assertIn(phrase, shape.forbidden_phrases,
                              f"{phrase!r} missing in {decision} mode")

    def test_robotic_ai_phrasing_blocked(self):
        # Core collaboration rule: no "as an AI" / "كنموذج لغوي".
        shape = self.shaper.shape(FakeReading())
        self.assertIn("as an AI", shape.forbidden_phrases)
        self.assertIn("كنموذج لغوي", shape.forbidden_phrases)

    def test_load_bearing_adds_dismissive_blocks(self):
        # Carrying weight ⇒ dismissive words must be added to the wall.
        shape = self.shaper.shape(FakeReading(load_bearing=True))
        for phrase in ("just", "don't worry", "ما عليك", "عادي"):
            self.assertIn(phrase, shape.forbidden_phrases)

    def test_frustrated_adds_minimizing_blocks(self):
        shape = self.shaper.shape(FakeReading(emotional_state="frustrated"))
        for phrase in ("simply", "بس", "مجرد"):
            self.assertIn(phrase, shape.forbidden_phrases)

    def test_calm_reading_has_no_context_extras(self):
        # A clear, non-load-bearing reading only carries the always-forbidden set.
        shape = self.shaper.shape(FakeReading(emotional_state="clear", load_bearing=False))
        extras = [p for p in shape.forbidden_phrases if p not in _ALWAYS_FORBIDDEN]
        self.assertEqual(extras, [])

    def test_forbidden_list_is_a_copy_not_the_module_global(self):
        # shape() must not mutate the module-level _ALWAYS_FORBIDDEN.
        before = list(_ALWAYS_FORBIDDEN)
        self.shaper.shape(FakeReading(load_bearing=True))
        self.assertEqual(_ALWAYS_FORBIDDEN, before,
                         "shape() leaked context phrases into the global block list")


# ═══════════════════════════════════════════════════════════
#  4. tone selection + de-escalation
# ═══════════════════════════════════════════════════════════
class TestToneSelection(unittest.TestCase):
    def setUp(self):
        self.shaper = AATIFResponseShaper()

    def test_load_bearing_forces_gentle(self):
        # load_bearing overrides any emotional_state mapping.
        shape = self.shaper.shape(FakeReading(load_bearing=True, emotional_state="excited"))
        self.assertEqual(shape.tone, "gentle")

    def test_emotional_state_mapping(self):
        cases = {
            "frustrated": "acknowledge",
            "lost": "orient",
            "excited": "match",
            "clear": "direct",
        }
        for state, expected in cases.items():
            shape = self.shaper.shape(FakeReading(emotional_state=state, load_bearing=False))
            self.assertEqual(shape.tone, expected, f"{state} ⇒ {expected}")

    def test_unknown_emotion_defaults_to_warm(self):
        shape = self.shaper.shape(FakeReading(emotional_state="serene", load_bearing=False))
        self.assertEqual(shape.tone, "warm")

    def test_escalated_memory_arc_forces_gentle(self):
        # Even a "clear" reading goes gentle if the conversation escalated.
        shape = self.shaper.shape(
            FakeReading(emotional_state="clear"),
            memory_context={"emotional_arc": {"escalated": True}},
        )
        self.assertEqual(shape.tone, "gentle")

    def test_heavy_conversation_tone_forces_gentle(self):
        shape = self.shaper.shape(
            FakeReading(emotional_state="excited"),
            memory_context={"conversation_tone": "heavy"},
        )
        self.assertEqual(shape.tone, "gentle")


# ═══════════════════════════════════════════════════════════
#  5. length selection
# ═══════════════════════════════════════════════════════════
class TestLengthSelection(unittest.TestCase):
    def setUp(self):
        self.shaper = AATIFResponseShaper()

    def test_load_bearing_is_short(self):
        self.assertEqual(self.shaper.shape(FakeReading(load_bearing=True)).max_length, "short")

    def test_frustrated_is_short(self):
        self.assertEqual(
            self.shaper.shape(FakeReading(emotional_state="frustrated")).max_length, "short"
        )

    def test_clarify_decision_is_short(self):
        self.assertEqual(
            self.shaper.shape(FakeReading(decision="CLARIFY")).max_length, "short"
        )

    def test_long_conversation_trims_to_short(self):
        shape = self.shaper.shape(FakeReading(), memory_context={"turn_count": 6})
        self.assertEqual(shape.max_length, "short")

    def test_default_is_medium(self):
        self.assertEqual(self.shaper.shape(FakeReading()).max_length, "medium")


# ═══════════════════════════════════════════════════════════
#  6. should_ask_question
# ═══════════════════════════════════════════════════════════
class TestShouldAsk(unittest.TestCase):
    def setUp(self):
        self.shaper = AATIFResponseShaper()

    def test_clarify_mode_asks(self):
        self.assertTrue(self.shaper.shape(FakeReading(decision="CLARIFY")).should_ask_question)

    def test_high_ambiguity_asks_even_when_executing(self):
        shape = self.shaper.shape(FakeReading(decision="EXECUTE", ambiguity_score=0.7))
        self.assertTrue(shape.should_ask_question)

    def test_clear_execute_does_not_ask(self):
        shape = self.shaper.shape(FakeReading(decision="EXECUTE", ambiguity_score=0.1))
        self.assertFalse(shape.should_ask_question)


# ═══════════════════════════════════════════════════════════
#  7. dialect instruction resolution
# ═══════════════════════════════════════════════════════════
class TestDialectInstruction(unittest.TestCase):
    def setUp(self):
        self.shaper = AATIFResponseShaper()

    def test_known_dialect_resolves(self):
        shape = self.shaper.shape(FakeReading(dialect_detected="egyptian"))
        self.assertEqual(shape.dialect_instruction, _DIALECT_INSTRUCTIONS["egyptian"])

    def test_unknown_dialect_falls_back(self):
        shape = self.shaper.shape(FakeReading(dialect_detected="klingon"))
        self.assertEqual(shape.dialect_instruction, _DIALECT_INSTRUCTIONS["unknown"])

    def test_none_dialect_falls_back_to_unknown(self):
        shape = self.shaper.shape(FakeReading(dialect_detected=None))
        self.assertEqual(shape.dialect_instruction, _DIALECT_INSTRUCTIONS["unknown"])

    def test_english_dialect_resolves(self):
        shape = self.shaper.shape(FakeReading(dialect_detected="english"))
        self.assertEqual(shape.dialect_instruction, _DIALECT_INSTRUCTIONS["english"])


# ═══════════════════════════════════════════════════════════
#  8. ResponseShape return contract + meaning instruction
# ═══════════════════════════════════════════════════════════
class TestShapeContract(unittest.TestCase):
    def setUp(self):
        self.shaper = AATIFResponseShaper()

    def test_returns_response_shape(self):
        self.assertIsInstance(self.shaper.shape(FakeReading()), ResponseShape)

    def test_all_fields_typed(self):
        shape = self.shaper.shape(FakeReading())
        self.assertIsInstance(shape.meaning_instruction, str)
        self.assertIsInstance(shape.response_mode, str)
        self.assertIsInstance(shape.dialect_instruction, str)
        self.assertIsInstance(shape.tone, str)
        self.assertIsInstance(shape.forbidden_phrases, list)
        self.assertIsInstance(shape.max_length, str)
        self.assertIsInstance(shape.should_ask_question, bool)
        self.assertIsInstance(shape.firmness, float)

    def test_meaning_instruction_nonempty_and_has_identity(self):
        shape = self.shaper.shape(FakeReading())
        self.assertTrue(shape.meaning_instruction.strip())
        self.assertIn("عاطف", shape.meaning_instruction)

    def test_meaning_instruction_carries_dialect(self):
        shape = self.shaper.shape(FakeReading(dialect_detected="egyptian"))
        self.assertIn(_DIALECT_INSTRUCTIONS["egyptian"], shape.meaning_instruction)

    def test_stop_mode_includes_decision_reason(self):
        shape = self.shaper.shape(
            FakeReading(decision="SAFE_STOP", decision_reason="potential_harm")
        )
        self.assertIn("potential_harm", shape.meaning_instruction)

    def test_skills_appear_in_instruction(self):
        shape = self.shaper.shape(FakeReading(skills_to_activate=["code", "math"]))
        self.assertIn("code", shape.meaning_instruction)
        self.assertIn("math", shape.meaning_instruction)

    def test_memory_context_none_is_safe(self):
        # Passing no memory must not raise and must yield an empty context note.
        shape = self.shaper.shape(FakeReading(), memory_context=None)
        self.assertEqual(shape.context_note, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
