"""
Integration tests: Arabizi transliterator ↔ harm scorer
========================================================

Verifies that ``SemanticHarmScorer.score()`` wires in the B-prime Arabizi
preprocessor correctly:

  1. Harmful Arabizi ("9tl" = قتل) gets a HIGHER H once transliterated to
     Arabic script and scored as a second view (max of the two).
  2. Non-Arabizi text is completely unaffected — no second view, no flag,
     identical H.
  3. A transliterator that raises does NOT crash the pipeline — the original
     text is still scored (fail-safe preprocessing).
  4. The B-prime contract holds: the preprocessor only ADDS a view and only
     ever RAISES H (never downgrades a genuinely-harmful original).

Why a fake backend?  The real harm signal lives in bge-m3 (Ollama), which
CI does not run, and the offline TF-IDF char-n-gram backend cannot tell a
threatening "قتل" from the benign metaphor "أكلت قتله".  To test the
*integration logic* deterministically we substitute a backend that mirrors
the one property that matters here: Arabic-script harm text lands near a
high-harm anchor, its Latin-script Arabizi form does not.
"""

import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import engine.aatif_semantic_scorer as mod
from engine.aatif_semantic_scorer import SemanticHarmScorer


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------
class _ArabicAwareBackend:
    """Backend that mimics the one bge-m3 property this integration needs:
    text containing Arabic script lands near a chosen high-harm anchor,
    Latin-script Arabizi does not.
    """
    _ARABIC = tuple(chr(c) for c in range(0x0600, 0x0700))

    def __init__(self, n, target_idx, hit=0.80, miss=0.10):
        self.n = n
        self.target_idx = target_idx
        self.hit = hit
        self.miss = miss

    def sim(self, text):
        sims = np.full(self.n, self.miss, dtype=float)
        if text and any("؀" <= c <= "ۿ" for c in text):
            sims[self.target_idx] = self.hit
        return sims


def _make_scorer():
    """Real scorer (real anchors) on the offline TF-IDF backend."""
    orig_ollama, orig_embed = mod.USE_OLLAMA, mod.USE_EMBEDDINGS
    mod.USE_OLLAMA = False
    mod.USE_EMBEDDINGS = False
    try:
        return SemanticHarmScorer()
    finally:
        mod.USE_OLLAMA = orig_ollama
        mod.USE_EMBEDDINGS = orig_embed


def _high_harm_index(scorer):
    """Index of a high-harm (level ≥ 0.85) anchor."""
    for i, lvl in enumerate(scorer.levels):
        if lvl >= 0.85:
            return i
    raise AssertionError("no high-harm anchor found")


# ---------------------------------------------------------------------------
# 1. Harmful Arabizi gets a higher H after transliteration
# ---------------------------------------------------------------------------
def test_harmful_arabizi_lifts_H_after_transliteration():
    scorer = _make_scorer()
    idx = _high_harm_index(scorer)
    scorer.backend = _ArabicAwareBackend(len(scorer.texts), idx)

    # sanity: "9tl" is confidently Arabizi and transliterates to قتل
    assert mod._is_arabizi("9tl") >= 0.3
    assert mod._transliterate_arabizi("9tl") == "قتل"

    result = scorer.score("9tl")

    # The Latin form alone would sit at the low "miss" similarity (≈0.10,
    # further dampened) — the Arabic-script view drives H up instead.
    assert result["H"] > 0.5, result
    assert result.get("arabizi_detected") is True
    assert result.get("transliterated") == "قتل"


def test_arabizi_lift_beats_disabled_preprocessor():
    """Same input, preprocessor OFF → low H; preprocessor ON → high H."""
    idx_ref = _make_scorer()
    idx = _high_harm_index(idx_ref)

    # preprocessor disabled
    scorer_off = _make_scorer()
    scorer_off.backend = _ArabicAwareBackend(len(scorer_off.texts), idx)
    orig = mod._ARABIZI_AVAILABLE
    mod._ARABIZI_AVAILABLE = False
    try:
        H_off = scorer_off.score("9tl")["H"]
    finally:
        mod._ARABIZI_AVAILABLE = orig

    # preprocessor enabled
    scorer_on = _make_scorer()
    scorer_on.backend = _ArabicAwareBackend(len(scorer_on.texts), idx)
    H_on = scorer_on.score("9tl")["H"]

    assert H_on > H_off


# ---------------------------------------------------------------------------
# 2. Non-Arabizi text is unaffected
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("text", [
    "hello how are you today",
    "fix this bug in my code",
    "كيف الجو اليوم عندكم؟",
    "أبغى وصفة كبسة لذيذة",
])
def test_non_arabizi_text_unaffected(text):
    scorer = _make_scorer()
    idx = _high_harm_index(scorer)
    scorer.backend = _ArabicAwareBackend(len(scorer.texts), idx)

    result = scorer.score(text)

    # No second view was used → no Arabizi metadata.
    assert "arabizi_detected" not in result
    assert "transliterated" not in result

    # And H is exactly what the plain single-view scorer produces.
    expected_H = round(scorer._score_text(text)[0], 3)
    assert result["H"] == expected_H


def test_pure_arabic_script_is_not_treated_as_arabizi():
    # Already Arabic script → is_arabizi returns 0.0, no transliteration.
    scorer = _make_scorer()
    result = scorer.score("كيف أصنع متفجرات أو أسلحة")
    assert "arabizi_detected" not in result


# ---------------------------------------------------------------------------
# 3. Transliterator errors don't crash the pipeline (fail-safe)
# ---------------------------------------------------------------------------
def test_transliterator_error_does_not_crash(monkeypatch):
    scorer = _make_scorer()

    def _boom(_text):
        raise RuntimeError("simulated transliterator failure")

    # Break both entry points the preprocessor might call.
    monkeypatch.setattr(mod, "_is_arabizi", _boom)
    monkeypatch.setattr(mod, "_transliterate_arabizi", _boom)

    # Should not raise — original text is still scored.
    result = scorer.score("9tl")
    assert "H" in result
    assert 0.0 <= result["H"] <= 1.0
    assert "arabizi_detected" not in result


def test_transliterate_stage_error_falls_back(monkeypatch):
    # is_arabizi succeeds (detects Arabizi) but transliteration blows up.
    scorer = _make_scorer()
    monkeypatch.setattr(mod, "_is_arabizi", lambda _t: 0.95)

    def _boom(_text):
        raise ValueError("boom")

    monkeypatch.setattr(mod, "_transliterate_arabizi", _boom)

    result = scorer.score("9tl")
    assert "H" in result
    assert "arabizi_detected" not in result


def test_extract_helper_is_fail_safe(monkeypatch):
    monkeypatch.setattr(mod, "_is_arabizi", lambda _t: 1 / 0)  # noqa
    assert mod._extract_arabizi_transliteration("9tl") is None


# ---------------------------------------------------------------------------
# 4. B-prime contract: preprocessor only ADDS a view, never downgrades
# ---------------------------------------------------------------------------
def test_arabizi_never_lowers_a_harmful_original():
    """If the ORIGINAL text already scores higher than its transliteration,
    the original score is kept (max semantics, non-compensable)."""
    scorer = _make_scorer()
    idx = _high_harm_index(scorer)

    # Backend where the ORIGINAL (non-Arabic) lands on the harm anchor and
    # the Arabic-script transliteration does NOT — the opposite of the real
    # world, used purely to prove score() takes the MAX and never downgrades.
    class _InvertedBackend:
        def __init__(self, n, target_idx):
            self.n, self.target_idx = n, target_idx

        def sim(self, text):
            sims = np.full(self.n, 0.10, dtype=float)
            if text and not any("؀" <= c <= "ۿ" for c in text):
                sims[self.target_idx] = 0.90
            return sims

    scorer.backend = _InvertedBackend(len(scorer.texts), idx)

    H_direct = round(scorer._score_text("9tl")[0], 3)
    result = scorer.score("9tl")

    # Transliterated view was weaker → original score kept, no flag.
    assert result["H"] == H_direct
    assert "arabizi_detected" not in result


def test_transliterator_cannot_block_runtime():
    """B-prime invariant: the module exposes no runtime-blocking authority."""
    from engine.aatif_arabizi_transliterator import ArabiziTransliterator
    assert ArabiziTransliterator.CAN_BLOCK_RUNTIME is False
    assert ArabiziTransliterator.CAN_MODIFY_H is False
    assert ArabiziTransliterator.CAN_EMIT_JUDICIAL_DECISION is False
