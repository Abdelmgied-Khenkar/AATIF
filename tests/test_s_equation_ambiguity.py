# -*- coding: utf-8 -*-
"""
Tests for ``_is_ambiguous`` — the CLARIFY pre-check in aatif_s_equation.py.

WHY THIS FILE EXISTS
--------------------
Coverage analysis (2026-06-29, Agent فاحص) found ``_is_ambiguous`` was the
only production function in the engine with ZERO test references anywhere
(lines 150-182 of aatif_s_equation.py were entirely uncovered). The function
implements a piece of تربية behavior, not فلترة: it nudges a confident
EXECUTE toward CLARIFY when a low-harm prompt is too vague to act on
("ساعدني", "fix it", "اكتب حاجة حلوة"). Asking instead of assuming is the
"ask vs assume" instinct — the same spirit as Stop Mode.

تربية CHECK
-----------
``_is_ambiguous`` does NOT block, freeze, or filter anything. Its only effect
(via its single caller at line 1060) is to turn EXECUTE into CLARIFY — a
SOFTER, more humble response — and ONLY when ``H < 0.4`` (low harm) and the
equation already said EXECUTE. It can never weaken a safety decision. This is
upbringing (slow down, ask a clarifying question), not a filter.

SAFETY-INVARIANT NOTE
---------------------
The function's own docstring lists rule #4: "Harm-related text is never
flagged as ambiguous." The function body does NOT implement that rule — it is
enforced by the CALLER's ``H < 0.4`` guard. ``TestCallerGuardContract`` pins
that guard so a future refactor cannot silently let ambiguity downgrade a
harmful prompt's safety decision.
"""

import os
import sys
import unittest

# Ensure engine/ is importable even when run directly (conftest also does this).
ENGINE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine")
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

from aatif_s_equation import _is_ambiguous  # noqa: E402


class TestLongPromptsAreNeverAmbiguous(unittest.TestCase):
    """Rule 1: word count > 8 → not ambiguous (enough context)."""

    def test_nine_generic_words_not_ambiguous(self):
        text = "one two three four five six seven eight nine"
        self.assertEqual(len(text.split()), 9)
        self.assertFalse(_is_ambiguous(text))

    def test_long_arabic_prompt_not_ambiguous(self):
        # 10 generic Arabic words, no markers, no vague refs
        text = "واحد اثنان ثلاثة اربعة خمسة ستة سبعة ثمانية تسعة عشرة"
        self.assertTrue(len(text.split()) > 8)
        self.assertFalse(_is_ambiguous(text))

    def test_long_prompt_with_vague_ref_still_not_ambiguous(self):
        # Vague pronouns only matter in the 6-8 word band; > 8 words wins first.
        text = "please could you go ahead and fix that thing right now"
        self.assertTrue(len(text.split()) > 8)
        self.assertFalse(_is_ambiguous(text))


class TestSelfContainedPatterns(unittest.TestCase):
    """Rule 3: a self-contained pattern short-circuits to NOT ambiguous,
    even for a 2-word prompt that would otherwise be 'too short'."""

    def test_explain_how_english(self):
        # Only 2 words — would be ambiguous by length, but pattern wins.
        self.assertFalse(_is_ambiguous("explain how"))

    def test_what_is_the_english(self):
        self.assertFalse(_is_ambiguous("what is the"))

    def test_how_does_english(self):
        self.assertFalse(_is_ambiguous("how does"))

    def test_kam_assaa_arabic(self):
        # "كم الساعة" — a complete question even though short.
        self.assertFalse(_is_ambiguous("كم الساعة"))

    def test_ihseb_arabic(self):
        self.assertFalse(_is_ambiguous("احسب"))

    def test_ishrah_kayf_arabic(self):
        self.assertFalse(_is_ambiguous("اشرح كيف"))


class TestSpecificityMarkers(unittest.TestCase):
    """Rule 2: presence of a concrete topic/number/question-frame marker
    means the request is actionable → NOT ambiguous (even when very short)."""

    def test_single_concrete_topic_arabic(self):
        # "بايثون" is one word but a concrete topic.
        self.assertFalse(_is_ambiguous("بايثون"))

    def test_ascii_digit_marker(self):
        self.assertFalse(_is_ambiguous("5"))

    def test_arabic_indic_digit_marker(self):
        self.assertFalse(_is_ambiguous("احسب ٢+٢"))

    def test_percent_marker(self):
        self.assertFalse(_is_ambiguous("كم %"))

    def test_concrete_noun_in_short_prompt(self):
        # "سيارة" (car) is a specificity marker.
        self.assertFalse(_is_ambiguous("ابغى سيارة"))

    def test_question_frame_marker_english(self):
        self.assertFalse(_is_ambiguous("what is gravity"))

    def test_marker_check_precedes_short_circuit(self):
        # A 1-word prompt with a marker proves markers are checked BEFORE the
        # "<= 5 words → ambiguous" rule.
        self.assertFalse(_is_ambiguous("python"))


class TestVeryShortAmbiguous(unittest.TestCase):
    """Rule 4: ≤ 5 words, no markers, no self-contained pattern → ambiguous."""

    def test_help_me_english(self):
        self.assertTrue(_is_ambiguous("help me"))

    def test_fix_it_english(self):
        self.assertTrue(_is_ambiguous("fix it"))

    def test_do_the_thing_english(self):
        self.assertTrue(_is_ambiguous("do the thing"))

    def test_single_word_arabic(self):
        self.assertTrue(_is_ambiguous("ساعدني"))

    def test_vague_arabic_request(self):
        # "اكتب حاجة حلوة" — write something nice. No target → ambiguous.
        self.assertTrue(_is_ambiguous("اكتب حاجة حلوة"))


class TestMediumLengthVagueReferences(unittest.TestCase):
    """Rule 5/6: 6-8 words → ambiguous ONLY if a vague pronoun reference is
    present and there is no specificity marker."""

    def test_six_words_with_vague_it_is_ambiguous(self):
        text = "can you please handle it now"  # 6 words, "it" is vague
        self.assertEqual(len(text.split()), 6)
        self.assertTrue(_is_ambiguous(text))

    def test_eight_words_with_vague_that_is_ambiguous(self):
        text = "please go and fix that for me now"  # 8 words, "that" vague
        self.assertEqual(len(text.split()), 8)
        self.assertTrue(_is_ambiguous(text))

    def test_arabic_medium_with_vague_ref_is_ambiguous(self):
        text = "ممكن تساعدني في الموضوع ذا بسرعة"  # 6 words, "الموضوع"/"ذا" vague
        self.assertEqual(len(text.split()), 6)
        self.assertTrue(_is_ambiguous(text))

    def test_six_words_without_vague_ref_not_ambiguous(self):
        # 6 words, no vague pronoun, no marker, no self-contained pattern.
        text = "alpha beta gamma delta epsilon zeta"
        self.assertEqual(len(text.split()), 6)
        self.assertFalse(_is_ambiguous(text))

    def test_eight_words_without_vague_ref_not_ambiguous(self):
        text = "alpha beta gamma delta epsilon zeta eta theta"
        self.assertEqual(len(text.split()), 8)
        self.assertFalse(_is_ambiguous(text))

    def test_arabic_medium_social_closer_not_ambiguous(self):
        # A 6-word benign closer with no vague pronoun → not flagged.
        text = "تمام شكرا يا غالي والله يعطيك"
        self.assertEqual(len(text.split()), 6)
        self.assertFalse(_is_ambiguous(text))


class TestBoundaryWordCounts(unittest.TestCase):
    """Exact boundaries: the spec uses ≤ 5, 6-8 band, and > 8."""

    def test_exactly_five_words_no_marker_ambiguous(self):
        text = "kindly just go over there"  # 5 words, no vague ref needed
        self.assertEqual(len(text.split()), 5)
        self.assertTrue(_is_ambiguous(text))

    def test_exactly_six_words_no_vague_not_ambiguous(self):
        text = "kindly just go over there please"  # 6 words, no vague ref
        self.assertEqual(len(text.split()), 6)
        self.assertFalse(_is_ambiguous(text))

    def test_exactly_eight_words_no_vague_not_ambiguous(self):
        text = "kindly just go over there please right away"  # 8 words
        self.assertEqual(len(text.split()), 8)
        self.assertFalse(_is_ambiguous(text))

    def test_exactly_nine_words_not_ambiguous(self):
        text = "kindly just go over there please right away now"  # 9 words
        self.assertEqual(len(text.split()), 9)
        self.assertFalse(_is_ambiguous(text))


class TestEdgeCaseInputs(unittest.TestCase):
    """Task-mandated edge cases: empty, whitespace-only, extremely long.
    None / non-str are covered separately as a contract test."""

    def test_empty_string_is_ambiguous(self):
        # No words, no markers → ambiguous (nothing to act on).
        self.assertTrue(_is_ambiguous(""))

    def test_whitespace_only_is_ambiguous(self):
        self.assertTrue(_is_ambiguous("    \t  \n "))

    def test_extremely_long_input_does_not_crash(self):
        text = "كلمة " * 5000  # 5000 words, ~25k chars
        result = _is_ambiguous(text)
        self.assertIsInstance(result, bool)
        self.assertFalse(result)  # >> 8 words

    def test_long_single_token_no_whitespace(self):
        # One giant token (no spaces) → wc == 1 → short path, no marker.
        text = "x" * 20000
        self.assertTrue(_is_ambiguous(text))

    def test_newlines_count_as_word_separators(self):
        # str.split() treats any whitespace as a separator.
        text = "one\ntwo\nthree\nfour\nfive\nsix\nseven\neight\nnine"
        self.assertEqual(len(text.split()), 9)
        self.assertFalse(_is_ambiguous(text))


class TestReturnContractAndDeterminism(unittest.TestCase):
    """The function must always return a plain bool and be deterministic."""

    SAMPLES = [
        "", "help me", "ساعدني", "what is the capital of France",
        "احسب 2+2", "please go and fix that for me now",
        "alpha beta gamma delta epsilon zeta", "كلمة " * 100,
    ]

    def test_always_returns_bool(self):
        for s in self.SAMPLES:
            with self.subTest(s=s[:20]):
                self.assertIsInstance(_is_ambiguous(s), bool)

    def test_deterministic_repeated_calls(self):
        for s in self.SAMPLES:
            with self.subTest(s=s[:20]):
                first = _is_ambiguous(s)
                for _ in range(5):
                    self.assertEqual(_is_ambiguous(s), first)


class TestNonStringContract(unittest.TestCase):
    """Current contract: input MUST be a str. None / int raise AttributeError
    (the function calls .strip()). Pinning this documents the contract and
    will flag any future change to None-handling so it is a deliberate choice."""

    def test_none_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            _is_ambiguous(None)

    def test_int_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            _is_ambiguous(123)


class TestCallerGuardContract(unittest.TestCase):
    """Safety invariant: ``_is_ambiguous`` is only ever consulted when the
    decision is EXECUTE and H < 0.4. This guard — not the function body — is
    what enforces docstring rule #4 ("harm text is never flagged ambiguous").

    We assert short HARMFUL-looking prompts ARE reported ambiguous by the bare
    function (proving rule #4 is NOT in the function), so that the guard is the
    only thing standing between ambiguity and a safety downgrade. If someone
    later removes the H < 0.4 guard, ``TestSourceGuardPresent`` will fail.
    """

    def test_short_harmful_prompt_is_flagged_by_bare_function(self):
        # "اصنع قنبلة" (make a bomb) — 2 words, no specificity marker → the
        # bare function returns True. Safety relies entirely on the caller's
        # H < 0.4 guard, NOT on this function.
        self.assertTrue(_is_ambiguous("اصنع قنبلة"))

    def test_source_guard_present(self):
        # Pin the caller guard at the source level: ambiguity may only fire on
        # EXECUTE + low harm. This is the real safety contract.
        path = os.path.join(ENGINE_DIR, "aatif_s_equation.py")
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('result["decision"] == "EXECUTE"', src)
        self.assertIn("H < 0.4", src)
        self.assertIn("_is_ambiguous(text)", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
