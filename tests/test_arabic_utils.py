#!/usr/bin/env python3
"""
Arabic text utility tests for aatif_arabic_utils.py — أدوات النص العربي
=======================================================================

WHY THIS FILE EXISTS
--------------------
aatif_arabic_utils is the SHARED normalization layer beneath the
understanding triad:
  I scorer = اللحظة (single turn)
  Fingerprint = النمط (patterns over time)
  Temporal Memory = الحقائق (what happened)
  Contextual Intent = اللحظة (the moment)

"One function, one truth — not three half-implementations." If
normalization drifts, every module that compares Arabic text drifts
with it. Before this file, the module had ZERO dedicated test coverage
despite feeding three downstream modules. These tests pin the contract.

TESTING STRATEGY
----------------
The module is pure Python — no embeddings, no model server, fully
deterministic. We feed controlled inputs and assert on exact outputs
where the behavior is contractual, and on bounds/properties where the
exact value is an implementation detail. Every test is CI-friendly.

These tests document ACTUAL behavior (including the deliberately
aggressive single-char clitic stripping, e.g. كيف → يف), so a future
change to that behavior trips a test and forces an intentional decision.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.aatif_arabic_utils import (  # noqa: E402
    normalize_arabic,
    tokenize_arabic,
    jaccard_similarity,
    ngram_overlap,
    combined_similarity,
)


# ═══════════════════════════════════════════════════════════
#  normalize_arabic
# ═══════════════════════════════════════════════════════════

class TestNormalizeContract:
    """The documented examples must hold — they are the public contract."""

    def test_docstring_example_islam(self):
        assert normalize_arabic("الإسْلام") == "الاسلام"

    def test_docstring_example_madrasa(self):
        assert normalize_arabic("مَدْرَسَة") == "مدرسه"

    def test_idempotent(self):
        """Normalizing already-normalized text changes nothing."""
        once = normalize_arabic("الإسْلام")
        twice = normalize_arabic(once)
        assert once == twice

    def test_deterministic(self):
        """Same input → same output, always."""
        text = "السَّلامُ عَلَيْكُمْ"
        assert normalize_arabic(text) == normalize_arabic(text)

    def test_empty_string(self):
        assert normalize_arabic("") == ""


class TestNormalizeAlef:
    @pytest.mark.parametrize("variant", ["أ", "إ", "آ", "ٱ"])
    def test_all_alef_variants_collapse_to_bare(self, variant):
        assert normalize_arabic(variant) == "ا"

    def test_mixed_alef_run(self):
        assert normalize_arabic("أإآٱ") == "اااا"

    def test_bare_alef_unchanged(self):
        assert normalize_arabic("ا") == "ا"


class TestNormalizeTaaAndHamza:
    def test_taa_marbuta_to_haa(self):
        assert normalize_arabic("مدرسة") == "مدرسه"

    def test_hamza_on_waw(self):
        assert normalize_arabic("مؤمن") == "مومن"

    def test_hamza_on_yaa(self):
        assert normalize_arabic("قائد") == "قايد"

    def test_standalone_hamza_is_preserved(self):
        """ء is NOT in the carrier map — it must survive untouched."""
        assert normalize_arabic("ء") == "ء"

    def test_alef_maqsura_is_preserved(self):
        """ى is intentionally NOT normalized to ي here."""
        assert normalize_arabic("مستشفى") == "مستشفى"


class TestNormalizeStripping:
    def test_tatweel_removed(self):
        assert normalize_arabic("كــتــاب") == "كتاب"

    def test_tashkeel_removed(self):
        # fatha/damma/kasra/sukun all stripped, letters retained
        assert normalize_arabic("كَتَبَ") == "كتب"

    def test_latin_lowercased(self):
        assert normalize_arabic("Hello WORLD") == "hello world"

    def test_does_not_strip_prefixes(self):
        """normalize is NOT tokenization — the definite article stays."""
        assert normalize_arabic("الكتاب") == "الكتاب"


# ═══════════════════════════════════════════════════════════
#  tokenize_arabic
# ═══════════════════════════════════════════════════════════

class TestTokenizeBasics:
    def test_returns_a_set(self):
        assert isinstance(tokenize_arabic("سلام عليكم"), set)

    def test_empty_text_empty_set(self):
        assert tokenize_arabic("") == set()

    def test_whitespace_only_empty_set(self):
        assert tokenize_arabic("   \t\n ") == set()

    def test_single_char_tokens_filtered(self):
        """Tokens shorter than 2 chars are noise and dropped."""
        # 'و' and 'a' are single chars → dropped; 'به' (2 chars) kept
        assert tokenize_arabic("و a به") == {"به"}

    def test_punctuation_becomes_separator(self):
        toks = tokenize_arabic("سلام،عليكم")
        assert "سلام" in toks


class TestTokenizePrefixStripping:
    def test_compound_prefix_wal_stripped(self):
        assert tokenize_arabic("والكتاب") == {"كتاب"}

    def test_no_strip_keeps_whole_token(self):
        assert tokenize_arabic("والكتاب", strip_prefixes=False) == {"والكتاب"}

    def test_definite_article_stripped(self):
        assert tokenize_arabic("الحال") == {"حال"}

    def test_single_char_clitic_is_aggressively_stripped(self):
        """
        DOCUMENTS a sharp edge: a leading single-char clitic is removed
        even from a content word. كيف → يف because ك is treated as a
        clitic. If this behavior is ever revisited, this test must be
        updated intentionally.
        """
        assert tokenize_arabic("كيف") == {"يف"}

    def test_strip_skipped_when_remainder_too_short(self):
        """
        If stripping a prefix would leave < 2 chars, the original token
        is kept instead. 'في' → stripping 'ف' leaves 'ي' (1 char), so
        the whole 'في' is retained.
        """
        assert tokenize_arabic("في") == {"في"}


class TestTokenizeRealSentence:
    def test_known_sentence_tokens(self):
        # Verified empirically: كيف→يف, الحال→حال, سلام kept
        toks = tokenize_arabic("سلام، كيف الحال؟")
        assert toks == {"سلام", "يف", "حال"}


# ═══════════════════════════════════════════════════════════
#  jaccard_similarity
# ═══════════════════════════════════════════════════════════

class TestJaccard:
    def test_both_empty_is_zero(self):
        assert jaccard_similarity(set(), set()) == 0.0

    def test_one_empty_is_zero(self):
        assert jaccard_similarity({"a"}, set()) == 0.0

    def test_identical_is_one(self):
        assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_is_zero(self):
        assert jaccard_similarity({"a"}, {"b"}) == 0.0

    def test_half_overlap(self):
        # |∩|=1 (a), |∪|=3 (a,b,c) → 1/3
        assert jaccard_similarity({"a", "b"}, {"a", "c"}) == pytest.approx(1 / 3)

    def test_symmetric(self):
        a, b = {"x", "y"}, {"y", "z"}
        assert jaccard_similarity(a, b) == jaccard_similarity(b, a)

    def test_bounded_unit_interval(self):
        val = jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert 0.0 <= val <= 1.0


# ═══════════════════════════════════════════════════════════
#  ngram_overlap
# ═══════════════════════════════════════════════════════════

class TestNgramOverlap:
    def test_too_short_returns_zero(self):
        # default n=3; "ab" has < 3 chars
        assert ngram_overlap("ab", "abc") == 0.0

    def test_identical_is_one(self):
        assert ngram_overlap("كتاب", "كتاب") == 1.0

    def test_disjoint_is_zero(self):
        assert ngram_overlap("قطط", "خيل") == 0.0

    def test_morphological_partial_match(self):
        """
        The reason n-grams exist: shared root yields partial overlap
        even across different word forms.
        """
        val = ngram_overlap("يتعلمون", "يتعلم")
        assert 0.0 < val < 1.0

    def test_normalization_applied_before_grams(self):
        """Diacritics must not break the match — normalize runs first."""
        assert ngram_overlap("كَتَبَ", "كتب") == 1.0

    def test_spaces_ignored(self):
        """Spaces are removed before gramming, so they don't dilute."""
        assert ngram_overlap("اب جد", "ابجد") == 1.0

    def test_bounded_unit_interval(self):
        val = ngram_overlap("مرحبا", "مرحبتين")
        assert 0.0 <= val <= 1.0

    def test_custom_n(self):
        # With n=2, "اب"/"اب" identical bigram sets → 1.0
        assert ngram_overlap("اب", "اب", n=2) == 1.0


# ═══════════════════════════════════════════════════════════
#  combined_similarity
# ═══════════════════════════════════════════════════════════

class TestCombinedSimilarity:
    def test_identical_is_one(self):
        assert combined_similarity("السلام عليكم", "السلام عليكم") == pytest.approx(1.0)

    def test_disjoint_is_zero(self):
        assert combined_similarity("قطة", "حصان") == 0.0

    def test_bounded_unit_interval(self):
        val = combined_similarity("ذكاء اصطناعي", "ذكاء صناعي")
        assert 0.0 <= val <= 1.0

    def test_weighting_is_40_60(self):
        """
        combined = 0.4*jaccard(tokens) + 0.6*ngram(text). Reconstruct it
        from the parts to lock the published formula.

        The input is deliberately chosen so jaccard != ngram (0.333 vs
        ~0.182). That asymmetry is what makes this test a true detector:
        if the weights were ever swapped to 0.6/0.4, the expected value
        would change and this assertion would fail. (An input where the
        two components are equal could not catch a weight swap.)
        """
        a, b = "تعلم الالة", "تعلم عميق"
        j = jaccard_similarity(tokenize_arabic(a), tokenize_arabic(b))
        n = ngram_overlap(a, b, n=3)
        # Guard the guard: the components must differ, or the weight test
        # below would be vacuous against a 0.6/0.4 swap.
        assert j != pytest.approx(n)
        assert combined_similarity(a, b) == pytest.approx(0.4 * j + 0.6 * n)
        # And the swapped weighting must give a materially different value.
        assert combined_similarity(a, b) != pytest.approx(0.6 * j + 0.4 * n)

    def test_partial_more_than_disjoint(self):
        """A shared word should score above totally unrelated text."""
        shared = combined_similarity("القطة سوداء", "القطة بيضاء")
        none = combined_similarity("القطة سوداء", "السيارة سريعة")
        assert shared > none

    def test_symmetric(self):
        a, b = "تعلم الآلة", "تعلم عميق"
        assert combined_similarity(a, b) == pytest.approx(combined_similarity(b, a))


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
