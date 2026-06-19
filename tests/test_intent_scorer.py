#!/usr/bin/env python3
"""
Intent-scorer (I) aggregation tests for aatif_intent_scorer.py — Agent فاحص (Fahes)

WHY THIS FILE EXISTS
────────────────────
The S equation is  S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))].
I (intent) is one of its two numerators. If I drifts upward incorrectly,
S drifts toward EXECUTE — a high-intent reading is a *brake released*. Yet as
of 2026-06-19 the I scorer (SemanticIntentScorer) had ZERO direct test
coverage. test_intent_scorer.py is the regression wall for the half of the
governance math that decides "what is the person trying to accomplish?".

THE BACKEND PROBLEM (and why these tests don't need Ollama)
───────────────────────────────────────────────────────────
SemanticIntentScorer.score() does two separable things:
  1. ask an embedding backend (bge-m3 via Ollama) for cosine sims to anchors,
  2. aggregate those sims into a single I via top-K softmax + confidence bands.
Step 1 needs a model server we cannot assume in CI. Step 2 is pure,
deterministic numpy and is where the governance-relevant logic lives:
  • top-K selection            (only the K nearest anchors vote)
  • softmax temperature        (how sharply the nearest anchor dominates)
  • convex combination         (I must stay inside the voted anchors' levels)
  • out-of-distribution guard  (max_sim ≈ 0 → I = 0.5 neutral, never a guess)
  • confidence banding         (high ≥ 0.45, medium ≥ 0.30, else low)
  • negative-sim clipping       (cosine < 0 must not pull weight)

So these tests inject a *fake backend* that returns a similarity vector we
choose, and assert on the aggregation contract. This isolates the math from the
model: the scorer is free to swap bge-m3 for anything else as long as the
aggregation behaviour holds.

CONTRACT UNDER TEST (from score() in aatif_intent_scorer.py)
────────────────────────────────────────────────────────────
  sims  = clip(backend.sim(text), 0, None)
  if max(sims) <= 1e-9:  I = 0.5, nearest = []          # OOD → neutral
  else:
      take top_k by sim; w = softmax(sim/temperature); I = Σ w·level
  confidence: max_sim ≥ 0.45 → "high"; ≥ 0.30 → "medium"; else "low"
  return {I (round 3), nearest (≤3), max_similarity (round 4), confidence}

Architect: Abdulmjeed Ibrahim Khenkar. فاحص breaks things on purpose to prove
they work.
"""

import os
import sys
import math
import random
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))

import aatif_intent_scorer as ais
from aatif_intent_scorer import SemanticIntentScorer, INTENT_ANCHORS


# ---------------------------------------------------------------------------
# Test harness: a fake embedding backend so we can drive score() deterministically
# ---------------------------------------------------------------------------
class _FakeBackend:
    """Returns a preset similarity vector regardless of the query text.

    Mimics _OllamaBackend's public surface (.sim(text) -> np.ndarray aligned to
    the anchor list, plus a .emb attribute the self-test probes for)."""
    def __init__(self, sims):
        self.sims = np.asarray(sims, dtype=float)
        self.emb = None

    def sim(self, text):
        return self.sims.copy()


def make_scorer(anchors, sims, temperature=0.05, top_k=3):
    """Construct a SemanticIntentScorer wired to a fake backend (no Ollama).

    We flip the module-level USE_OLLAMA flag off so __init__ does not try to
    reach the local model server, then attach our controlled backend."""
    saved = ais.USE_OLLAMA
    ais.USE_OLLAMA = False
    try:
        s = SemanticIntentScorer(anchors=anchors, temperature=temperature,
                                 top_k=top_k)
    finally:
        ais.USE_OLLAMA = saved
    s.backend = _FakeBackend(sims)
    return s


def manual_I(sims, levels, temperature, top_k):
    """Reference implementation of the aggregation, computed independently of
    the production code, so a test can assert the two agree."""
    sims = np.clip(np.asarray(sims, dtype=float), 0, None)
    if sims.max() <= 1e-9:
        return 0.5
    order = np.argsort(sims)[::-1]
    k_idx = order[:top_k]
    k_sims = sims[k_idx]
    k_levels = np.asarray(levels, dtype=float)[k_idx]
    w = np.exp(k_sims / temperature)
    w = w / w.sum()
    return float((w * k_levels).sum())


# A tiny, fully-known anchor set: (text, level). Index ↔ level is fixed so a
# chosen sims vector maps to known intent levels.
TINY_ANCHORS = [
    ("constructive_A", 1.0),   # 0
    ("constructive_B", 1.0),   # 1
    ("neutral",        0.5),   # 2
    ("questionable",   0.3),   # 3
    ("harmful_A",      0.0),   # 4
    ("harmful_B",      0.0),   # 5
]
TINY_LEVELS = [lvl for _, lvl in TINY_ANCHORS]


# ===========================================================================
# 1. STATIC ANCHOR HEALTH — no backend required
# ===========================================================================
class TestAnchorHealth(unittest.TestCase):
    def test_all_levels_in_unit_interval(self):
        for text, lvl in INTENT_ANCHORS:
            self.assertTrue(0.0 <= lvl <= 1.0,
                            f"anchor level out of [0,1]: {lvl} for «{text}»")

    def test_anchor_count_is_a_meaningful_set(self):
        # The skill doc references "30 probes"; the live set is larger. Guard a
        # floor so nobody silently guts the anchor bank.
        self.assertGreaterEqual(len(INTENT_ANCHORS), 30)

    def test_anchor_texts_unique(self):
        texts = [t for t, _ in INTENT_ANCHORS]
        self.assertEqual(len(texts), len(set(texts)),
                         "duplicate anchor texts dilute the softmax vote")

    def test_both_extremes_represented(self):
        levels = {lvl for _, lvl in INTENT_ANCHORS}
        self.assertIn(0.0, levels, "no clearly-harmful (I=0.0) anchor present")
        self.assertIn(1.0, levels, "no clearly-constructive (I=1.0) anchor present")

    def test_levels_are_floats(self):
        for _, lvl in INTENT_ANCHORS:
            self.assertIsInstance(lvl, float)


# ===========================================================================
# 2. BOUNDING INVARIANT — I must always land in [0, 1]
# ===========================================================================
class TestBounding(unittest.TestCase):
    def test_I_bounded_for_random_sims(self):
        rng = random.Random(20260619)
        for _ in range(500):
            sims = [rng.uniform(-1.0, 1.0) for _ in TINY_ANCHORS]
            s = make_scorer(TINY_ANCHORS, sims)
            I = s.score("x")["I"]
            self.assertGreaterEqual(I, 0.0)
            self.assertLessEqual(I, 1.0)

    def test_I_within_voted_anchor_levels(self):
        # A convex combination of the top-K levels can never exceed their range.
        sims = [0.9, 0.2, 0.8, 0.1, 0.05, 0.0]   # top-3 → idx 0,2,1 (levels 1.0,0.5,1.0)
        s = make_scorer(TINY_ANCHORS, sims, top_k=3)
        I = s.score("x")["I"]
        self.assertGreaterEqual(I, 0.5 - 1e-3)
        self.assertLessEqual(I, 1.0 + 1e-3)


# ===========================================================================
# 3. OUT-OF-DISTRIBUTION GUARD — unknown input must NOT be guessed
# ===========================================================================
class TestOODFallback(unittest.TestCase):
    def test_all_zero_sims_returns_neutral_half(self):
        s = make_scorer(TINY_ANCHORS, [0.0] * len(TINY_ANCHORS))
        r = s.score("totally novel input")
        self.assertEqual(r["I"], 0.5)

    def test_all_zero_sims_empty_nearest(self):
        s = make_scorer(TINY_ANCHORS, [0.0] * len(TINY_ANCHORS))
        self.assertEqual(s.score("x")["nearest"], [])

    def test_all_zero_sims_confidence_low(self):
        s = make_scorer(TINY_ANCHORS, [0.0] * len(TINY_ANCHORS))
        self.assertEqual(s.score("x")["confidence"], "low")

    def test_all_negative_sims_clip_to_ood(self):
        # Pure negative cosine → clipped to 0 → treated as OOD neutral, not a
        # confident harmful/constructive call.
        s = make_scorer(TINY_ANCHORS, [-0.3, -0.9, -0.1, -0.5, -0.2, -0.4])
        r = s.score("x")
        self.assertEqual(r["I"], 0.5)
        self.assertEqual(r["confidence"], "low")

    def test_sub_epsilon_sims_are_ood(self):
        s = make_scorer(TINY_ANCHORS, [1e-12] * len(TINY_ANCHORS))
        self.assertEqual(s.score("x")["I"], 0.5)


# ===========================================================================
# 4. CONFIDENCE BANDING — exact threshold boundaries (0.45, 0.30)
# ===========================================================================
class TestConfidenceBands(unittest.TestCase):
    def _conf_for_max(self, max_sim):
        # Put the max at index 0, everything else well below.
        sims = [max_sim, 0.01, 0.0, 0.0, 0.0, 0.0]
        return make_scorer(TINY_ANCHORS, sims).score("x")["confidence"]

    def test_exactly_high_threshold_is_high(self):
        self.assertEqual(self._conf_for_max(0.45), "high")

    def test_just_below_high_is_medium(self):
        self.assertEqual(self._conf_for_max(0.4499), "medium")

    def test_exactly_medium_threshold_is_medium(self):
        self.assertEqual(self._conf_for_max(0.30), "medium")

    def test_just_below_medium_is_low(self):
        self.assertEqual(self._conf_for_max(0.2999), "low")

    def test_high_similarity_is_high(self):
        self.assertEqual(self._conf_for_max(0.95), "high")


# ===========================================================================
# 5. TOP-K + SOFTMAX AGGREGATION — the core math
# ===========================================================================
class TestAggregation(unittest.TestCase):
    def test_matches_independent_reference(self):
        sims = [0.81, 0.42, 0.77, 0.15, 0.66, 0.30]
        for tk in (1, 2, 3, 5):
            s = make_scorer(TINY_ANCHORS, sims, temperature=0.05, top_k=tk)
            got = s.score("x")["I"]
            exp = round(manual_I(sims, TINY_LEVELS, 0.05, tk), 3)
            self.assertAlmostEqual(got, exp, places=3,
                                   msg=f"top_k={tk}: {got} != {exp}")

    def test_low_temperature_picks_dominant_anchor(self):
        # One anchor far ahead + sharp temperature → I collapses to its level.
        sims = [0.95, 0.20, 0.18, 0.10, 0.05, 0.0]   # idx0 level 1.0 dominates
        s = make_scorer(TINY_ANCHORS, sims, temperature=0.02, top_k=3)
        self.assertAlmostEqual(s.score("x")["I"], 1.0, places=2)

    def test_dominant_harmful_anchor_drives_I_down(self):
        sims = [0.10, 0.05, 0.18, 0.20, 0.95, 0.0]   # idx4 level 0.0 dominates
        s = make_scorer(TINY_ANCHORS, sims, temperature=0.02, top_k=3)
        self.assertAlmostEqual(s.score("x")["I"], 0.0, places=2)

    def test_topk_excludes_outliers(self):
        # An extreme-level anchor OUTSIDE the top-K must not move I at all.
        base = [0.80, 0.78, 0.76, 0.0, 0.0, 0.0]      # top-3 are idx 0,1,2
        # idx5 is harmful (level 0.0) but has the lowest sim → excluded at top_k=3
        s_base = make_scorer(TINY_ANCHORS, base, top_k=3)
        bumped = [0.80, 0.78, 0.76, 0.0, 0.0, 0.05]   # idx5 still below top-3
        s_bump = make_scorer(TINY_ANCHORS, bumped, top_k=3)
        self.assertEqual(s_base.score("x")["I"], s_bump.score("x")["I"])

    def test_monotonic_in_dominant_level(self):
        # Same sim shape; only the dominant anchor's level changes 1.0→0.5→0.0.
        # I must move the same direction (intent reading tracks the anchor).
        results = []
        for dom_level in (1.0, 0.5, 0.0):
            anchors = [("dom", dom_level), ("b", 0.5), ("c", 0.5),
                       ("d", 0.5), ("e", 0.5), ("f", 0.5)]
            sims = [0.95, 0.10, 0.10, 0.10, 0.10, 0.10]
            results.append(make_scorer(anchors, sims, temperature=0.02).score("x")["I"])
        self.assertGreater(results[0], results[1])
        self.assertGreater(results[1], results[2])

    def test_negative_sim_does_not_pull_weight(self):
        # A negative cosine on a harmful anchor must be clipped to 0, so it
        # cannot drag I down. Compare against the same vector with that entry
        # already zeroed: results must be identical.
        with_neg = [0.80, 0.20, 0.10, 0.05, -0.90, 0.0]   # idx4 harmful, negative
        zeroed   = [0.80, 0.20, 0.10, 0.05, 0.0,  0.0]
        s1 = make_scorer(TINY_ANCHORS, with_neg, top_k=3)
        s2 = make_scorer(TINY_ANCHORS, zeroed, top_k=3)
        self.assertEqual(s1.score("x")["I"], s2.score("x")["I"])


# ===========================================================================
# 6. RETURN FORMAT — the dict contract pipeline code depends on
# ===========================================================================
class TestReturnFormat(unittest.TestCase):
    def setUp(self):
        self.r = make_scorer(TINY_ANCHORS, [0.7, 0.5, 0.3, 0.2, 0.1, 0.0]).score("x")

    def test_required_keys_present(self):
        for k in ("I", "nearest", "max_similarity", "confidence"):
            self.assertIn(k, self.r)

    def test_I_is_float(self):
        self.assertIsInstance(self.r["I"], float)

    def test_I_rounded_to_3dp(self):
        self.assertEqual(self.r["I"], round(self.r["I"], 3))

    def test_max_similarity_rounded_to_4dp(self):
        self.assertEqual(self.r["max_similarity"], round(self.r["max_similarity"], 4))

    def test_nearest_capped_at_three(self):
        self.assertLessEqual(len(self.r["nearest"]), 3)

    def test_confidence_is_valid_level(self):
        self.assertIn(self.r["confidence"], {"high", "medium", "low"})

    def test_nearest_entries_are_text_sim_level(self):
        for entry in self.r["nearest"]:
            self.assertEqual(len(entry), 3)
            text, sim, level = entry
            self.assertIsInstance(text, str)
            self.assertTrue(0.0 <= level <= 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
