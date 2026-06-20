#!/usr/bin/env python3
"""
Emotion-scorer (E) aggregation tests for aatif_emotion_scorer.py — Agent فاحص (Fahes)

WHY THIS FILE EXISTS
────────────────────
The S equation is  S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))].
E (emotion) is the OTHER numerator beside I. With w₂ = 1.5, E pushes directly
on the brake: a HIGH E (joy, w₂·E large) helps release the brake toward
EXECUTE, while a LOW E (despair → E≈0) starves the numerator and pulls S down
toward SAFE_STOP/SAFE_FREEZE. That is the governance point of reading emotion at
all: a person in collapse should not get a freely-released brake.

As of 2026-06-19 the I scorer got its regression wall (test_intent_scorer.py),
but the E scorer (SemanticEmotionScorer) still had ZERO direct test coverage —
the documented coverage gap in فاحص's task. This file closes it.

THE BACKEND PROBLEM (and why these tests don't need Ollama)
───────────────────────────────────────────────────────────
SemanticEmotionScorer.score() does two separable things:
  1. ask an embedding backend (bge-m3 via Ollama) for cosine sims to anchors,
  2. aggregate those sims into a single E via top-K softmax + confidence bands.
Step 1 needs a model server we cannot assume in CI. Step 2 is pure,
deterministic numpy and is where the governance-relevant logic lives:
  • top-K selection            (only the K nearest anchors vote)
  • softmax temperature        (how sharply the nearest anchor dominates)
  • convex combination         (E must stay inside the voted anchors' levels)
  • out-of-distribution guard  (max_sim ≈ 0 → E = 0.5 neutral, never a guess)
  • confidence banding         (high ≥ 0.45, medium ≥ 0.30, else low)
  • negative-sim clipping       (cosine < 0 must not pull weight)

So these tests inject a *fake backend* that returns a similarity vector we
choose, and assert on the aggregation contract — identical isolation strategy to
test_intent_scorer.py. The scorer is free to swap bge-m3 for anything else as
long as the aggregation behaviour holds.

E SEMANTICS (what makes E different from I, and why direction matters)
──────────────────────────────────────────────────────────────────────
E reads the speaker's FEELING, not danger (H) or purpose (I):
  E → 1.0  positive  (joy, gratitude, relief, love)
  E → 0.5  neutral
  E → 0.0  intense negative (despair, rage, terror, hopelessness)
Because E feeds the numerator with weight w₂=1.5, the *direction* is
governance-critical: a dominant despair anchor MUST drive E toward 0 (brake
tightens), a dominant joy anchor toward 1 (brake loosens). The aggregation
tests below pin both directions, not just "E stayed in [0,1]".

CONTRACT UNDER TEST (from score() in aatif_emotion_scorer.py)
────────────────────────────────────────────────────────────
  sims  = clip(backend.sim(text), 0, None)
  if max(sims) <= 1e-9:  E = 0.5, nearest = []          # OOD → neutral
  else:
      take top_k by sim; w = softmax(sim/temperature); E = Σ w·level
  confidence: max_sim ≥ 0.45 → "high"; ≥ 0.30 → "medium"; else "low"
  return {E (round 3), nearest (≤3), max_similarity (round 4), confidence}

Architect: Abdulmjeed Ibrahim Khenkar. فاحص breaks things on purpose to prove
they work.
"""

import os
import sys
import random
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))

import aatif_emotion_scorer as aes
from aatif_emotion_scorer import SemanticEmotionScorer, EMOTION_ANCHORS


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
    """Construct a SemanticEmotionScorer wired to a fake backend (no Ollama).

    We flip the module-level USE_OLLAMA flag off so __init__ does not try to
    reach the local model server, then attach our controlled backend."""
    saved = aes.USE_OLLAMA
    aes.USE_OLLAMA = False
    try:
        s = SemanticEmotionScorer(anchors=anchors, temperature=temperature,
                                  top_k=top_k)
    finally:
        aes.USE_OLLAMA = saved
    s.backend = _FakeBackend(sims)
    return s


def manual_E(sims, levels, temperature, top_k):
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
# chosen sims vector maps to known emotion levels. Mirrors the E scale:
# 1.0 positive · 0.5 neutral · 0.0 intense-negative.
TINY_ANCHORS = [
    ("joy_A",       1.0),   # 0  positive
    ("joy_B",       1.0),   # 1  positive
    ("neutral",     0.5),   # 2  neutral
    ("mild_neg",    0.3),   # 3  mild negative
    ("despair_A",   0.0),   # 4  intense negative
    ("despair_B",   0.0),   # 5  intense negative
]
TINY_LEVELS = [lvl for _, lvl in TINY_ANCHORS]


# ===========================================================================
# 1. STATIC ANCHOR HEALTH — no backend required
# ===========================================================================
class TestAnchorHealth(unittest.TestCase):
    def test_all_levels_in_unit_interval(self):
        for text, lvl in EMOTION_ANCHORS:
            self.assertTrue(0.0 <= lvl <= 1.0,
                            f"anchor level out of [0,1]: {lvl} for «{text}»")

    def test_anchor_count_floor(self):
        # Skill doc records 32 emotion anchors (2026-06-19). Guard a floor so
        # nobody silently guts the bank — a thin bank degrades E to noise.
        self.assertGreaterEqual(len(EMOTION_ANCHORS), 32)

    def test_anchor_texts_unique(self):
        texts = [t for t, _ in EMOTION_ANCHORS]
        self.assertEqual(len(texts), len(set(texts)),
                         "duplicate anchor texts dilute the softmax vote")

    def test_both_extremes_represented(self):
        levels = {lvl for _, lvl in EMOTION_ANCHORS}
        self.assertIn(0.0, levels, "no intense-negative (E=0.0) anchor present")
        self.assertIn(1.0, levels, "no clearly-positive (E=1.0) anchor present")

    def test_neutral_anchor_present(self):
        # E uses 0.5 as both the OOD fallback AND a real anchor level. Without a
        # genuine 0.5 anchor, neutral inputs can only be reached by averaging,
        # never by a confident match.
        levels = {lvl for _, lvl in EMOTION_ANCHORS}
        self.assertIn(0.5, levels, "no neutral (E=0.5) anchor present")

    def test_levels_are_floats(self):
        for _, lvl in EMOTION_ANCHORS:
            self.assertIsInstance(lvl, float)

    def test_contamination_guard_no_H_overlap_tokens(self):
        # Documented design invariant (module docstring): E anchors deliberately
        # avoid "نفسي" and "أبغى" because those live in H/I anchors and bge-m3
        # matches WORDS not MEANINGS. If they creep back in, E starts echoing H.
        texts = [t for t, _ in EMOTION_ANCHORS]
        self.assertFalse(any("نفسي" in t for t in texts),
                         "contamination: 'نفسي' leaked into an emotion anchor")
        self.assertFalse(any("أبغى" in t for t in texts),
                         "contamination: 'أبغى' leaked into an emotion anchor")


# ===========================================================================
# 2. BOUNDING INVARIANT — E must always land in [0, 1]
# ===========================================================================
class TestBounding(unittest.TestCase):
    def test_E_bounded_for_random_sims(self):
        rng = random.Random(20260620)
        for _ in range(500):
            sims = [rng.uniform(-1.0, 1.0) for _ in TINY_ANCHORS]
            s = make_scorer(TINY_ANCHORS, sims)
            E = s.score("x")["E"]
            self.assertGreaterEqual(E, 0.0)
            self.assertLessEqual(E, 1.0)

    def test_E_within_voted_anchor_levels(self):
        # A convex combination of the top-K levels can never exceed their range.
        sims = [0.9, 0.2, 0.8, 0.1, 0.05, 0.0]   # top-3 → idx 0,2,1 (levels 1.0,0.5,1.0)
        s = make_scorer(TINY_ANCHORS, sims, top_k=3)
        E = s.score("x")["E"]
        self.assertGreaterEqual(E, 0.5 - 1e-3)
        self.assertLessEqual(E, 1.0 + 1e-3)


# ===========================================================================
# 3. OUT-OF-DISTRIBUTION GUARD — unknown input must NOT be guessed
# ===========================================================================
class TestOODFallback(unittest.TestCase):
    def test_all_zero_sims_returns_neutral_half(self):
        s = make_scorer(TINY_ANCHORS, [0.0] * len(TINY_ANCHORS))
        r = s.score("totally novel input")
        self.assertEqual(r["E"], 0.5)

    def test_all_zero_sims_empty_nearest(self):
        s = make_scorer(TINY_ANCHORS, [0.0] * len(TINY_ANCHORS))
        self.assertEqual(s.score("x")["nearest"], [])

    def test_all_zero_sims_confidence_low(self):
        s = make_scorer(TINY_ANCHORS, [0.0] * len(TINY_ANCHORS))
        self.assertEqual(s.score("x")["confidence"], "low")

    def test_all_negative_sims_clip_to_ood(self):
        # Pure negative cosine → clipped to 0 → treated as OOD neutral, not a
        # confident positive/despair call.
        s = make_scorer(TINY_ANCHORS, [-0.3, -0.9, -0.1, -0.5, -0.2, -0.4])
        r = s.score("x")
        self.assertEqual(r["E"], 0.5)
        self.assertEqual(r["confidence"], "low")

    def test_sub_epsilon_sims_are_ood(self):
        s = make_scorer(TINY_ANCHORS, [1e-12] * len(TINY_ANCHORS))
        self.assertEqual(s.score("x")["E"], 0.5)


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
# 5. TOP-K + SOFTMAX AGGREGATION — the core math (with E-direction asserts)
# ===========================================================================
class TestAggregation(unittest.TestCase):
    def test_matches_independent_reference(self):
        sims = [0.81, 0.42, 0.77, 0.15, 0.66, 0.30]
        for tk in (1, 2, 3, 5):
            s = make_scorer(TINY_ANCHORS, sims, temperature=0.05, top_k=tk)
            got = s.score("x")["E"]
            exp = round(manual_E(sims, TINY_LEVELS, 0.05, tk), 3)
            self.assertAlmostEqual(got, exp, places=3,
                                   msg=f"top_k={tk}: {got} != {exp}")

    def test_low_temperature_picks_dominant_joy(self):
        # One positive anchor far ahead + sharp temperature → E collapses to 1.0.
        sims = [0.95, 0.20, 0.18, 0.10, 0.05, 0.0]   # idx0 level 1.0 dominates
        s = make_scorer(TINY_ANCHORS, sims, temperature=0.02, top_k=3)
        self.assertAlmostEqual(s.score("x")["E"], 1.0, places=2)

    def test_dominant_despair_anchor_drives_E_to_zero(self):
        # GOVERNANCE-CRITICAL: a dominant despair anchor (level 0.0) must pull E
        # toward 0, which starves the σ(w₁·I + w₂·E) numerator and tightens the
        # brake. Despair must never read as a released brake.
        sims = [0.10, 0.05, 0.18, 0.20, 0.95, 0.0]   # idx4 level 0.0 dominates
        s = make_scorer(TINY_ANCHORS, sims, temperature=0.02, top_k=3)
        self.assertAlmostEqual(s.score("x")["E"], 0.0, places=2)

    def test_topk_excludes_outliers(self):
        # An extreme-level anchor OUTSIDE the top-K must not move E at all.
        base = [0.80, 0.78, 0.76, 0.0, 0.0, 0.0]      # top-3 are idx 0,1,2
        s_base = make_scorer(TINY_ANCHORS, base, top_k=3)
        bumped = [0.80, 0.78, 0.76, 0.0, 0.0, 0.05]   # idx5 still below top-3
        s_bump = make_scorer(TINY_ANCHORS, bumped, top_k=3)
        self.assertEqual(s_base.score("x")["E"], s_bump.score("x")["E"])

    def test_monotonic_in_dominant_level(self):
        # Same sim shape; only the dominant anchor's level changes 1.0→0.5→0.0.
        # E must move the same direction (emotion reading tracks the anchor).
        results = []
        for dom_level in (1.0, 0.5, 0.0):
            anchors = [("dom", dom_level), ("b", 0.5), ("c", 0.5),
                       ("d", 0.5), ("e", 0.5), ("f", 0.5)]
            sims = [0.95, 0.10, 0.10, 0.10, 0.10, 0.10]
            results.append(make_scorer(anchors, sims, temperature=0.02).score("x")["E"])
        self.assertGreater(results[0], results[1])
        self.assertGreater(results[1], results[2])

    def test_negative_sim_does_not_pull_weight(self):
        # A negative cosine on a despair anchor must be clipped to 0, so it
        # cannot drag E down. Compare against the same vector with that entry
        # already zeroed: results must be identical.
        with_neg = [0.80, 0.20, 0.10, 0.05, -0.90, 0.0]   # idx4 despair, negative
        zeroed   = [0.80, 0.20, 0.10, 0.05, 0.0,  0.0]
        s1 = make_scorer(TINY_ANCHORS, with_neg, top_k=3)
        s2 = make_scorer(TINY_ANCHORS, zeroed, top_k=3)
        self.assertEqual(s1.score("x")["E"], s2.score("x")["E"])


# ===========================================================================
# 6. RETURN FORMAT — the dict contract pipeline code depends on
# ===========================================================================
class TestReturnFormat(unittest.TestCase):
    def setUp(self):
        self.r = make_scorer(TINY_ANCHORS, [0.7, 0.5, 0.3, 0.2, 0.1, 0.0]).score("x")

    def test_required_keys_present(self):
        for k in ("E", "nearest", "max_similarity", "confidence"):
            self.assertIn(k, self.r)

    def test_E_is_float(self):
        self.assertIsInstance(self.r["E"], float)

    def test_E_rounded_to_3dp(self):
        self.assertEqual(self.r["E"], round(self.r["E"], 3))

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
