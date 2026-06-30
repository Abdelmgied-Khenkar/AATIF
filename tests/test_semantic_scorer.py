"""
test_semantic_scorer.py — Unit tests for the H (harm) scorer
============================================================
Covers ``engine/aatif_semantic_scorer.py`` — the 171-anchor semantic harm
scorer that drives the gated S-equation. Previously this module had NO
dedicated test file; it was only exercised indirectly by
``test_held_out_validation.py`` (which skips entirely without Ollama) and
``test_dialect_hyperbole.py`` (context-signal logic only).

These tests run WITHOUT Ollama by forcing the TF-IDF development backend
(and, for the core scoring math, an injected deterministic fake backend so
the assertions are independent of any embedding calibration).

What is covered here (and was previously untested in isolation):
  * Anchor-curation integrity — count, level ranges, no duplicates, structure
  * ``score()`` output contract — keys, value bounds, rounding, nearest list
  * Core scoring math — top-K softmax blend, confidence bands, empty input
  * Context-adjustment integration through the public ``score()`` API
  * C4 FAIL-SAFE — the scorer must RAISE (never silently fall back to the
    uncalibrated TF-IDF backend) when Ollama is requested but unavailable.
  * ``EngineHealthStatus`` enum

License: BSL 1.1
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np

import engine.aatif_semantic_scorer as mod
from engine.aatif_semantic_scorer import (
    SemanticHarmScorer,
    HARM_ANCHORS,
    EngineHealthStatus,
)


def make_tfidf_scorer(**kwargs):
    """Build a scorer on the offline TF-IDF backend (no Ollama needed)."""
    orig_ollama, orig_embed = mod.USE_OLLAMA, mod.USE_EMBEDDINGS
    mod.USE_OLLAMA = False
    mod.USE_EMBEDDINGS = False
    try:
        return SemanticHarmScorer(**kwargs)
    finally:
        mod.USE_OLLAMA = orig_ollama
        mod.USE_EMBEDDINGS = orig_embed


class _FakeBackend:
    """Deterministic backend returning a fixed similarity vector.

    Lets us test score() math (top-K softmax, confidence bands, context)
    with full control and zero dependence on any embedding calibration.
    """
    def __init__(self, sims):
        self._sims = np.asarray(sims, dtype=float)

    def sim(self, text):
        return self._sims


# ---------------------------------------------------------------------------
# Anchor curation integrity
# ---------------------------------------------------------------------------
class TestAnchorCuration(unittest.TestCase):

    def test_anchor_count(self):
        # Guards against accidental deletion/duplication of anchors.
        # If anchors are intentionally added, update this number.
        self.assertEqual(len(HARM_ANCHORS), 255,
                         "Anchor count changed — update intentionally")

    def test_every_anchor_is_text_level_pair(self):
        for a in HARM_ANCHORS:
            self.assertEqual(len(a), 2, f"Anchor not a 2-tuple: {a!r}")
            text, level = a
            self.assertIsInstance(text, str)
            self.assertTrue(text.strip(), "Anchor text must be non-empty")
            self.assertIsInstance(level, (int, float))

    def test_levels_in_unit_interval(self):
        for text, level in HARM_ANCHORS:
            self.assertGreaterEqual(level, 0.0, f"level<0 for {text!r}")
            self.assertLessEqual(level, 1.0, f"level>1 for {text!r}")

    def test_no_duplicate_anchor_texts(self):
        texts = [t for t, _ in HARM_ANCHORS]
        dups = {t for t in texts if texts.count(t) > 1}
        self.assertEqual(dups, set(), f"Duplicate anchor texts: {dups}")

    def test_covers_full_harm_spectrum(self):
        levels = [l for _, l in HARM_ANCHORS]
        self.assertLessEqual(min(levels), 0.05, "Need benign anchors near 0")
        self.assertGreaterEqual(max(levels), 0.85, "Need high-harm anchors near 0.9")

    def test_has_benign_and_highharm_examples(self):
        benign = [t for t, l in HARM_ANCHORS if l <= 0.05]
        high = [t for t, l in HARM_ANCHORS if l >= 0.8]
        self.assertGreater(len(benign), 10, "Too few benign/hyperbole anchors")
        self.assertGreater(len(high), 10, "Too few high-harm anchors")


# ---------------------------------------------------------------------------
# score() output contract (TF-IDF backend, real anchors)
# ---------------------------------------------------------------------------
class TestScoreContract(unittest.TestCase):

    def setUp(self):
        self.scorer = make_tfidf_scorer()

    def test_result_has_required_keys(self):
        r = self.scorer.score("كم الساعة الحين؟")
        for key in ("H", "nearest", "max_similarity", "confidence"):
            self.assertIn(key, r)

    def test_H_in_unit_interval(self):
        for msg in ["كم الساعة؟", "كيف أصنع متفجرات", "fix this bug", ""]:
            H = self.scorer.score(msg)["H"]
            self.assertGreaterEqual(H, 0.0)
            self.assertLessEqual(H, 1.0)

    def test_max_similarity_in_unit_interval(self):
        for msg in ["كم الساعة؟", "كيف أصنع متفجرات", "random text here"]:
            ms = self.scorer.score(msg)["max_similarity"]
            self.assertGreaterEqual(ms, 0.0)
            self.assertLessEqual(ms, 1.0)

    def test_confidence_is_valid_label(self):
        for msg in ["كم الساعة؟", "كيف أصنع متفجرات", "zzz qqq"]:
            self.assertIn(self.scorer.score(msg)["confidence"],
                          {"high", "medium", "low"})

    def test_nearest_is_capped_at_three(self):
        r = self.scorer.score("كيف أصنع متفجرات أو أسلحة")
        self.assertLessEqual(len(r["nearest"]), 3)
        for entry in r["nearest"]:
            self.assertEqual(len(entry), 3)  # (text, sim, level)

    def test_H_rounded_to_three_decimals(self):
        H = self.scorer.score("أحس بضغط كبير من الدراسة والشغل")["H"]
        self.assertEqual(round(H, 3), H)

    def test_determinism(self):
        msg = "أبغى طريقة أأذي فيها شخص ضايقني"
        self.assertEqual(self.scorer.score(msg), self.scorer.score(msg))


# ---------------------------------------------------------------------------
# Core scoring math via deterministic fake backend
# ---------------------------------------------------------------------------
class TestScoreMath(unittest.TestCase):

    def setUp(self):
        self.scorer = make_tfidf_scorer()
        self.n = len(self.scorer.levels)

    def _inject(self, sims):
        self.scorer.backend = _FakeBackend(sims)

    def test_empty_match_gives_zero_H(self):
        self._inject(np.zeros(self.n))
        r = self.scorer.score("anything")
        self.assertEqual(r["H"], 0.0)
        self.assertEqual(r["nearest"], [])
        self.assertEqual(r["confidence"], "low")

    def test_strong_match_to_highharm_anchor(self):
        # Put a dominant similarity on a level-0.9 anchor.
        idx = int(np.argmax(self.scorer.levels))  # a 0.9 anchor
        sims = np.full(self.n, 0.01)
        sims[idx] = 0.95
        self._inject(sims)
        r = self.scorer.score("some harmful request")
        self.assertGreater(r["H"], 0.8, "Dominant 0.9 anchor should drive H high")
        self.assertEqual(r["confidence"], "high")

    def test_strong_match_to_benign_anchor(self):
        # Dominant similarity on a level-0.0 anchor.
        idx = int(np.argmin(self.scorer.levels))  # a 0.0 anchor
        sims = np.full(self.n, 0.01)
        sims[idx] = 0.95
        self._inject(sims)
        r = self.scorer.score("a benign request")
        self.assertLess(r["H"], 0.1, "Dominant benign anchor should keep H low")

    def test_confidence_bands_follow_max_similarity(self):
        idx = 0
        for sim_val, expected in [
            (0.60, "high"),    # >= CONFIDENCE_HIGH (0.45)
            (0.45, "high"),
            (0.35, "medium"),  # >= CONFIDENCE_MEDIUM (0.30)
            (0.30, "medium"),
            (0.10, "low"),     # < CONFIDENCE_MEDIUM
        ]:
            sims = np.zeros(self.n)
            sims[idx] = sim_val
            self._inject(sims)
            r = self.scorer.score("x")
            self.assertEqual(r["confidence"], expected,
                             f"max_sim={sim_val} should be {expected}")

    def test_negative_similarities_are_clipped(self):
        # Cosine can be negative; score() clips to >=0 before use.
        sims = np.full(self.n, -0.5)
        self._inject(sims)
        r = self.scorer.score("x")
        self.assertEqual(r["H"], 0.0)
        self.assertEqual(r["max_similarity"], 0.0)

    def test_top_k_limits_anchor_influence(self):
        # Many weak benign anchors must NOT drown a strong harmful match
        # because only the top_k nearest are blended.
        sims = np.full(self.n, 0.05)            # everything weakly benign-ish
        idx = int(np.argmax(self.scorer.levels))  # a 0.9 anchor
        sims[idx] = 0.9
        self._inject(sims)
        r = self.scorer.score("x")
        self.assertGreater(r["H"], 0.7,
                           "top-K should let the strong harmful anchor dominate")


# ---------------------------------------------------------------------------
# Context-adjustment integration through score()
# ---------------------------------------------------------------------------
class TestContextIntegration(unittest.TestCase):

    def setUp(self):
        self.scorer = make_tfidf_scorer()
        self.n = len(self.scorer.levels)

    def _inject_borderline(self):
        # Build a borderline raw_H (~0.45) inside the context window
        # (FLOOR 0.15 .. CEILING 0.70) by matching a 0.6 and a 0.3 anchor.
        levels = self.scorer.levels
        i6 = int(np.argmin(np.abs(levels - 0.6)))
        i3 = int(np.argmin(np.abs(levels - 0.3)))
        sims = np.zeros(self.n)
        sims[i6] = 0.5
        sims[i3] = 0.5
        self.scorer.backend = _FakeBackend(sims)

    def test_casual_context_reduces_and_flags(self):
        self._inject_borderline()
        # Casual/domestic signal present (ابني/سياره) → discount applied.
        r = self.scorer.score("ابني كسر السياره")
        self.assertTrue(r.get("context_adjusted", False),
                        "casual borderline message should be context-adjusted")
        self.assertIn("raw_H", r)
        self.assertLess(r["H"], r["raw_H"])

    def test_threatening_context_keeps_H(self):
        self._inject_borderline()
        # Threatening signal (سلاح) → no discount even if casual words present.
        r = self.scorer.score("عندي سلاح وبستخدمه على ابني")
        self.assertFalse(r.get("context_adjusted", False),
                         "threatening signal must block the casual discount")

    def test_context_multiplier_bounds(self):
        # Multiplier never below (1 - context_discount), never above 1.
        lo = 1.0 - self.scorer.context_discount
        for text in ["ابني بنتي سياره فاتورة مدرسة", "neutral", ""]:
            m = self.scorer._context_adjustment(text, 0.4)
            self.assertGreaterEqual(m, lo - 1e-9)
            self.assertLessEqual(m, 1.0 + 1e-9)


# ---------------------------------------------------------------------------
# C4 FAIL-SAFE — never silently fall back to uncalibrated TF-IDF
# ---------------------------------------------------------------------------
class TestFailSafeC4(unittest.TestCase):

    def test_raises_when_ollama_requested_but_unavailable(self):
        """If USE_OLLAMA=True and the Ollama backend cannot init, the scorer
        MUST raise RuntimeError — not quietly switch to TF-IDF, whose cosine
        distribution invalidates every calibrated threshold (θ, confidence,
        unknown-territory). This is the core C4 safety property."""

        class _BoomBackend:
            def __init__(self, texts):
                raise ConnectionError("ollama down")

        orig_flag = mod.USE_OLLAMA
        orig_backend = mod._OllamaBackend
        mod.USE_OLLAMA = True
        mod._OllamaBackend = _BoomBackend
        try:
            with self.assertRaises(RuntimeError):
                SemanticHarmScorer()
        finally:
            mod.USE_OLLAMA = orig_flag
            mod._OllamaBackend = orig_backend

    def test_tfidf_only_used_when_explicitly_disabled(self):
        """With both embedding backends disabled, TF-IDF is allowed (dev mode)."""
        s = make_tfidf_scorer()
        self.assertEqual(s.backend_name, "tfidf")


# ---------------------------------------------------------------------------
# EngineHealthStatus enum
# ---------------------------------------------------------------------------
class TestEngineHealthStatus(unittest.TestCase):

    def test_members(self):
        self.assertEqual(
            {e.name for e in EngineHealthStatus},
            {"FULL", "DEGRADED", "OFFLINE"},
        )

    def test_values_match_names(self):
        for e in EngineHealthStatus:
            self.assertEqual(e.value, e.name)


if __name__ == "__main__":
    unittest.main()
