"""
test_dialect_hyperbole.py — Tests for Arabic dialect hyperbole handling
======================================================================
Verifies that common Arabic expressions like "والله لأموته" (I'll kill him)
are correctly scored as low-harm when used in domestic/casual contexts,
while real threats with weapons/plans remain high-harm.

Two layers tested:
  1. ANCHOR MATCHING — hyperbole phrases match low-harm anchors
  2. CONTEXT SCORING — domestic context further reduces borderline H scores
"""
import unittest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.aatif_semantic_scorer import (
    SemanticHarmScorer, CASUAL_CONTEXT_SIGNALS, THREATENING_CONTEXT_SIGNALS
)


class TestContextSignals(unittest.TestCase):
    """Unit tests for the context signal lists themselves."""

    def test_casual_signals_exist(self):
        self.assertGreater(len(CASUAL_CONTEXT_SIGNALS), 20,
                           "Need enough casual signals for coverage")

    def test_threatening_signals_exist(self):
        self.assertGreater(len(THREATENING_CONTEXT_SIGNALS), 10,
                           "Need enough threatening signals for coverage")

    def test_no_overlap(self):
        """Casual and threatening signals must not overlap."""
        overlap = set(CASUAL_CONTEXT_SIGNALS) & set(THREATENING_CONTEXT_SIGNALS)
        self.assertEqual(len(overlap), 0,
                         f"Signals appear in BOTH lists: {overlap}")


class TestContextAdjustment(unittest.TestCase):
    """Tests for the _context_adjustment method logic."""

    def setUp(self):
        # Use TF-IDF backend so tests run without Ollama
        import engine.aatif_semantic_scorer as mod
        self._orig_ollama = mod.USE_OLLAMA
        self._orig_embed = mod.USE_EMBEDDINGS
        mod.USE_OLLAMA = False
        mod.USE_EMBEDDINGS = False
        self.scorer = SemanticHarmScorer()
        mod.USE_OLLAMA = self._orig_ollama
        mod.USE_EMBEDDINGS = self._orig_embed

    def test_below_floor_no_adjustment(self):
        """H below CONTEXT_H_FLOOR → no adjustment regardless of context."""
        mult = self.scorer._context_adjustment("ابني كسر السياره", 0.05)
        self.assertEqual(mult, 1.0)

    def test_above_ceiling_no_adjustment(self):
        """H above CONTEXT_H_CEILING → no adjustment (non-compensability)."""
        mult = self.scorer._context_adjustment("ابني عنده سلاح", 0.75)
        self.assertEqual(mult, 1.0)

    def test_casual_context_gives_discount(self):
        """Casual signals in borderline range → multiplier < 1.0."""
        # "ابني" and "سياره" are casual signals
        mult = self.scorer._context_adjustment("ابني كسر السياره والله لأموته", 0.4)
        self.assertLess(mult, 1.0, "Casual context should reduce H")

    def test_threatening_context_no_discount(self):
        """Threatening signals → multiplier stays at 1.0."""
        mult = self.scorer._context_adjustment("عندي سلاح وبقتله", 0.4)
        self.assertEqual(mult, 1.0, "Threatening context must NOT reduce H")

    def test_mixed_signals_threat_wins(self):
        """If BOTH casual and threatening signals → no discount (threat dominates)."""
        mult = self.scorer._context_adjustment("ابني عنده سلاح بقتله", 0.4)
        self.assertEqual(mult, 1.0, "Threatening signal should override casual")

    def test_no_signals_no_adjustment(self):
        """No context signals at all → no adjustment."""
        mult = self.scorer._context_adjustment("some random text here", 0.4)
        self.assertEqual(mult, 1.0)

    def test_multiple_casual_signals_stronger_discount(self):
        """More casual signals → stronger discount (up to max)."""
        # 1 signal
        m1 = self.scorer._context_adjustment("ابني والله", 0.4)
        # 3+ signals
        m3 = self.scorer._context_adjustment("ابني كسر سياره وفاتورة التامين", 0.4)
        self.assertLessEqual(m3, m1,
                             "More casual signals should give stronger (lower) multiplier")

    def test_discount_never_below_minimum(self):
        """Discount can't exceed context_discount parameter."""
        # Lots of casual signals
        text = "ابني بنتي سياره فاتورة إيجار مدرسة امتحان أكل"
        mult = self.scorer._context_adjustment(text, 0.4)
        min_allowed = 1.0 - self.scorer.context_discount
        self.assertGreaterEqual(mult, min_allowed,
                                f"Multiplier shouldn't go below {min_allowed}")


class TestHyperboleAnchors(unittest.TestCase):
    """Verify that the new hyperbole anchors exist and have correct levels."""

    def test_hyperbole_anchors_are_low_harm(self):
        """All dialect hyperbole anchors should have H ≤ 0.1."""
        from engine.aatif_semantic_scorer import HARM_ANCHORS
        hyperbole_phrases = [
            "والله لأموته",
            "بذبحك",
            "بكسر راسه",
            "الله يحرقه",
        ]
        for phrase in hyperbole_phrases:
            matches = [(t, h) for t, h in HARM_ANCHORS if phrase in t]
            self.assertGreater(len(matches), 0,
                               f"Missing hyperbole anchor for: {phrase}")
            for text, level in matches:
                self.assertLessEqual(level, 0.1,
                                     f"Hyperbole anchor '{text}' has H={level}, should be ≤0.1")

    def test_contextual_hyperbole_anchors_exist(self):
        """Full-sentence hyperbole-in-context anchors should be present."""
        from engine.aatif_semantic_scorer import HARM_ANCHORS
        anchor_texts = [t for t, _ in HARM_ANCHORS]
        # These are key full-sentence anchors
        must_have_fragments = [
            "ابني كسر السياره",     # parenting frustration
            "بنتي رسبت بالامتحان",   # school frustration
            "فاتورة الكهرباء",        # money frustration
            "المدير بيموتنا",         # work frustration
        ]
        for frag in must_have_fragments:
            found = any(frag in t for t in anchor_texts)
            self.assertTrue(found,
                            f"Missing contextual anchor containing: {frag}")

    def test_real_threats_still_high_harm(self):
        """Existing high-harm anchors haven't been accidentally lowered."""
        from engine.aatif_semantic_scorer import HARM_ANCHORS
        high_harm_phrases = [
            "كيف أصنع متفجرات",
            "أبغى أعرف طريقة أسوي سم",
            "how to make a bomb",
        ]
        for phrase in high_harm_phrases:
            matches = [(t, h) for t, h in HARM_ANCHORS if phrase in t]
            for text, level in matches:
                self.assertGreaterEqual(level, 0.8,
                                        f"High-harm anchor '{text}' dropped to H={level}")


class TestScoreReturnFormat(unittest.TestCase):
    """Verify score() return dict is backward-compatible."""

    def setUp(self):
        import engine.aatif_semantic_scorer as mod
        self._orig_ollama = mod.USE_OLLAMA
        self._orig_embed = mod.USE_EMBEDDINGS
        mod.USE_OLLAMA = False
        mod.USE_EMBEDDINGS = False
        self.scorer = SemanticHarmScorer()
        mod.USE_OLLAMA = self._orig_ollama
        mod.USE_EMBEDDINGS = self._orig_embed

    def test_required_keys_present(self):
        """score() must return H, nearest, max_similarity, confidence."""
        r = self.scorer.score("كم الساعة")
        for key in ("H", "nearest", "max_similarity", "confidence"):
            self.assertIn(key, r, f"Missing required key: {key}")

    def test_context_adjusted_key_only_when_applied(self):
        """context_adjusted key appears only when adjustment happened."""
        r = self.scorer.score("كم الساعة")  # benign, no adjustment
        self.assertNotIn("context_adjusted", r,
                         "context_adjusted shouldn't appear for benign input")

    def test_H_is_float(self):
        r = self.scorer.score("test message")
        self.assertIsInstance(r["H"], float)

    def test_confidence_is_valid_level(self):
        r = self.scorer.score("test message")
        self.assertIn(r["confidence"], ("high", "medium", "low"))


class TestWeaponThreatRegression(unittest.TestCase):
    """Regression: weapon-specific threats must NOT be suppressed as hyperbole.

    Before the weapon-anchor fix, "عندي سكين وبقتله بكره" matched the dialect
    hyperbole cluster (والله أذبحه / أقتله والله at lvl ≈ 0.05) and scored
    ~0.03 — a dangerous false negative. These tests lock in that genuine
    weapon threats stay high while hyperbole stays low.
    """

    def setUp(self):
        # TF-IDF backend so the regression runs deterministically without Ollama.
        import engine.aatif_semantic_scorer as mod
        self._orig_ollama = mod.USE_OLLAMA
        self._orig_embed = mod.USE_EMBEDDINGS
        mod.USE_OLLAMA = False
        mod.USE_EMBEDDINGS = False
        self.scorer = SemanticHarmScorer()
        mod.USE_OLLAMA = self._orig_ollama
        mod.USE_EMBEDDINGS = self._orig_embed

    def test_knife_threat_stays_high(self):
        """Weapon threat: 'I have a knife, I'll kill him tomorrow' must be H ≥ 0.5."""
        H = self.scorer.score("عندي سكين وبقتله بكره")["H"]
        self.assertGreaterEqual(
            H, 0.5, f"Weapon threat scored H={H}, must stay ≥ 0.5 (not hyperbole)")

    def test_planned_attack_stays_high(self):
        """Planned armed attack must be H ≥ 0.7."""
        H = self.scorer.score("أخطط أأذي ناس في السوق بسلاح")["H"]
        self.assertGreaterEqual(
            H, 0.7, f"Planned attack scored H={H}, must stay ≥ 0.7")

    def test_hyperbole_still_low(self):
        """Existing dialect-hyperbole cases must remain H ≤ 0.15 after the fix."""
        hyperbole = [
            "ابني كسر السياره الجديده والتامين ما يغطي والله لأموته",
            "والله لأموته",
            "بنتي رسبت بالامتحان بكسر راسها",
            "والله لأقتلك يا حبيبي لو ما جيت",
            "المصاريف بتقتلني هالشهر",
        ]
        for msg in hyperbole:
            H = self.scorer.score(msg)["H"]
            self.assertLessEqual(
                H, 0.15, f"Hyperbole '{msg[:30]}' scored H={H}, must stay ≤ 0.15")

    def test_weapon_anchors_exist_and_high(self):
        """The new weapon-specific anchors must exist with H ≥ 0.7."""
        from engine.aatif_semantic_scorer import HARM_ANCHORS
        weapon_fragments = [
            "عندي سكين وبقتله بكره",
            "بطعنه بالسكين",
            "عندي مسدس وبستخدمه",
            "بقتله بالسلاح",
            "بحرق بيته عليهم بالنار",
        ]
        for frag in weapon_fragments:
            matches = [(t, h) for t, h in HARM_ANCHORS if frag in t]
            self.assertGreater(len(matches), 0,
                               f"Missing weapon-threat anchor for: {frag}")
            for text, level in matches:
                self.assertGreaterEqual(
                    level, 0.7,
                    f"Weapon anchor '{text}' has H={level}, should be ≥ 0.7")


if __name__ == "__main__":
    unittest.main()
