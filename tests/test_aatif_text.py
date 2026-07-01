#!/usr/bin/env python3
"""
Tests for aatif_text.py — shared text utility functions
=========================================================

WHY THIS FILE EXISTS
--------------------
aatif_text consolidates text-processing utilities that were duplicated
across 18+ engine modules: normalize_arabic (18+ copies), negation
detection (11 modules), word boundary matching (11 modules), and
dialect detection (19 modules).

These tests pin the contract so that downstream modules can rely on
consistent behavior. All tests are pure Python — no embeddings,
no model server, fully CI-friendly.

TESTING STRATEGY
----------------
Each function is tested with:
  - Arabic examples (normalized and raw)
  - English examples
  - Edge cases (empty string, mixed language, boundary values)
  - Specific patterns that caused bugs in the duplicated implementations

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.aatif_text import (  # noqa: E402
    normalize_arabic,
    strip_tashkeel,
    strip_tashkeel_nfd,
    arabic_ratio,
    is_arabic,
    detect_negation,
    is_marker_negated,
    word_boundary_match,
    word_boundary_match_en,
    word_boundary_match_ar,
    compile_en_patterns,
    extract_dialect_markers,
    detect_dialect,
    has_dialect_markers,
    NEGATION_AR,
    NEGATION_EN,
    GULF_MARKERS,
    EGYPTIAN_MARKERS,
)


# ═══════════════════════════════════════════════════════════
#  normalize_arabic
# ═══════════════════════════════════════════════════════════

class TestNormalizeArabic:
    """Tests for Arabic text normalization."""

    # --- Alef variants ---

    def test_hamza_above_alef(self):
        """أ → ا"""
        assert normalize_arabic("أحمد") == "احمد"

    def test_hamza_below_alef(self):
        """إ → ا"""
        assert normalize_arabic("إسلام") == "اسلام"

    def test_madda_alef(self):
        """آ → ا"""
        assert normalize_arabic("آمين") == "امين"

    def test_wasla_alef(self):
        """ٱ → ا"""
        assert normalize_arabic("ٱلرَّحمٰن") == "الرحمن"

    def test_all_alef_variants_in_one_string(self):
        """All alef variants normalized in a single string."""
        assert normalize_arabic("أإآٱ") == "اااا"

    # --- Tashkeel (diacritics) ---

    def test_strip_fatha_damma_kasra(self):
        """Remove basic Arabic vowel marks."""
        assert normalize_arabic("بِسْمِ") == "بسم"

    def test_strip_shadda(self):
        """Remove shadda (gemination mark)."""
        assert normalize_arabic("اللَّه") == "الله"

    def test_strip_tanween(self):
        """Remove tanween marks (ً ٌ ٍ)."""
        assert normalize_arabic("كِتَابًا") == "كتابا"

    def test_fully_diacritized_text(self):
        """Full Quran-style diacritization removed."""
        assert normalize_arabic("الإسْلام") == "الاسلام"

    # --- Taa marbuta ---

    def test_taa_marbuta_to_haa(self):
        """ة → ه"""
        assert normalize_arabic("مدرسة") == "مدرسه"

    def test_taa_marbuta_at_end(self):
        """ة at word end → ه."""
        assert normalize_arabic("القاهرة") == "القاهره"

    # --- Hamza on carrier ---

    def test_hamza_on_waw(self):
        """ؤ → و"""
        assert normalize_arabic("مؤمن") == "مومن"

    def test_hamza_on_yaa(self):
        """ئ → ي"""
        assert normalize_arabic("رئيس") == "رييس"

    # --- Alef maqsura ---

    def test_alef_maqsura(self):
        """ى → ي"""
        assert normalize_arabic("على") == "علي"

    def test_alef_maqsura_musa(self):
        """ى in name → ي"""
        assert normalize_arabic("موسى") == "موسي"

    # --- Tatweel ---

    def test_strip_tatweel(self):
        """Remove kashida (decorative stretching)."""
        assert normalize_arabic("كتــاب") == "كتاب"

    # --- Latin text ---

    def test_lowercase_latin(self):
        """Latin characters should be lowercased."""
        assert normalize_arabic("Hello World") == "hello world"

    def test_mixed_arabic_latin(self):
        """Mixed text: Arabic normalized + Latin lowered."""
        assert normalize_arabic("أحمد Hello") == "احمد hello"

    # --- Edge cases ---

    def test_empty_string(self):
        """Empty string → empty string."""
        assert normalize_arabic("") == ""

    def test_numbers_preserved(self):
        """Numbers pass through unchanged."""
        assert normalize_arabic("123") == "123"

    def test_idempotent(self):
        """Normalizing already-normalized text → same result."""
        text = "احمد مبسوط"
        assert normalize_arabic(normalize_arabic(text)) == normalize_arabic(text)

    def test_whitespace_preserved(self):
        """Whitespace structure should be preserved."""
        assert normalize_arabic("كلمة  كلمتين") == "كلمه  كلمتين"


# ═══════════════════════════════════════════════════════════
#  strip_tashkeel
# ═══════════════════════════════════════════════════════════

class TestStripTashkeel:
    """Tests for diacritics-only stripping."""

    def test_removes_vowels(self):
        """Removes fatha/damma/kasra but keeps letter forms."""
        result = strip_tashkeel("بِسْمِ اللَّهِ")
        assert "ِ" not in result
        assert "ْ" not in result
        assert "َ" not in result

    def test_preserves_alef_variants(self):
        """Does NOT normalize أ إ آ — only removes diacritics."""
        assert "أ" in strip_tashkeel("أَحْمَد")

    def test_latin_passthrough(self):
        """Latin text is unchanged."""
        assert strip_tashkeel("Hello") == "Hello"


# ═══════════════════════════════════════════════════════════
#  arabic_ratio
# ═══════════════════════════════════════════════════════════

class TestArabicRatio:
    """Tests for Arabic character ratio calculation."""

    def test_pure_arabic(self):
        """All Arabic → 1.0."""
        assert arabic_ratio("مرحبا") == pytest.approx(1.0)

    def test_pure_english(self):
        """All English → 0.0."""
        assert arabic_ratio("Hello") == pytest.approx(0.0)

    def test_mixed(self):
        """Mixed text → ratio between 0 and 1."""
        ratio = arabic_ratio("مرحبا Hello")
        assert 0.0 < ratio < 1.0

    def test_empty(self):
        """Empty string → 0.0."""
        assert arabic_ratio("") == 0.0

    def test_spaces_only(self):
        """Spaces only → 0.0 (no non-space chars)."""
        assert arabic_ratio("   ") == 0.0

    def test_numbers_not_arabic(self):
        """Numbers are not Arabic characters."""
        assert arabic_ratio("123") == pytest.approx(0.0)


# ═══════════════════════════════════════════════════════════
#  is_arabic
# ═══════════════════════════════════════════════════════════

class TestIsArabic:
    """Tests for is_arabic convenience function."""

    def test_arabic_text(self):
        assert is_arabic("مرحبا بالعالم") is True

    def test_english_text(self):
        assert is_arabic("Hello World") is False

    def test_custom_threshold(self):
        """Higher threshold → stricter."""
        mixed = "مرحبا Hi"
        assert is_arabic(mixed, threshold=0.3) is True
        assert is_arabic(mixed, threshold=0.9) is False


# ═══════════════════════════════════════════════════════════
#  detect_negation
# ═══════════════════════════════════════════════════════════

class TestDetectNegation:
    """Tests for negation detection."""

    # --- Arabic negation ---

    def test_ma_negation(self):
        """ما is a negation word."""
        assert detect_negation("ما أبي") is True

    def test_la_negation(self):
        """لا is a negation word."""
        assert detect_negation("لا أريد") is True

    def test_msh_negation(self):
        """مش is a negation word."""
        assert detect_negation("مش مبسوط") is True

    def test_mo_negation(self):
        """مو is a negation word."""
        assert detect_negation("مو تمام") is True

    def test_mani_negation(self):
        """ماني is a negation word."""
        assert detect_negation("ماني فاهم") is True

    def test_mb_negation(self):
        """مب (Emirati negation)."""
        assert detect_negation("مب زين") is True

    # --- English negation ---

    def test_dont_negation(self):
        assert detect_negation("I don't want this") is True

    def test_not_negation(self):
        assert detect_negation("I am not happy") is True

    def test_never_negation(self):
        assert detect_negation("I never said that") is True

    def test_without_negation(self):
        assert detect_negation("without help") is True

    # --- Non-negated ---

    def test_positive_arabic(self):
        """Positive Arabic → no negation."""
        assert detect_negation("أبي شاي") is False

    def test_positive_english(self):
        """Positive English → no negation."""
        assert detect_negation("I want tea") is False

    def test_empty_string(self):
        """Empty → no negation."""
        assert detect_negation("") is False


# ═══════════════════════════════════════════════════════════
#  is_marker_negated
# ═══════════════════════════════════════════════════════════

class TestIsMarkerNegated:
    """Tests for position-aware negation detection."""

    # --- Arabic ---

    def test_msh_before_marker(self):
        """مش directly before marker → negated."""
        assert is_marker_negated("مش مبسوط", "مبسوط") is True

    def test_la_before_marker(self):
        """لا before marker → negated."""
        assert is_marker_negated("لا أريد", "أريد") is True

    def test_no_negation_before_marker(self):
        """No negation before marker → not negated."""
        assert is_marker_negated("أنا مبسوط", "مبسوط") is False

    # --- English ---

    def test_not_before_english(self):
        """'not' before marker → negated."""
        assert is_marker_negated("I'm not happy", "happy") is True

    def test_dont_before_english(self):
        """'don't' before marker → negated."""
        assert is_marker_negated("I don't want it", "want") is True

    def test_no_negation_english(self):
        """No negation → not negated."""
        assert is_marker_negated("I am happy", "happy") is False

    # --- Edge cases ---

    def test_marker_not_found(self):
        """Marker not in text → False."""
        assert is_marker_negated("hello world", "missing") is False

    def test_negation_far_away(self):
        """Negation too far from marker (beyond lookbehind)."""
        text = "I don't " + "x" * 50 + " like it"
        # With default lookbehind of 20, "don't" is too far
        assert is_marker_negated(text, "like") is False


# ═══════════════════════════════════════════════════════════
#  word_boundary_match
# ═══════════════════════════════════════════════════════════

class TestWordBoundaryMatch:
    """Tests for word boundary matching."""

    # --- English ---

    def test_english_whole_word(self):
        """English term as whole word → match."""
        assert word_boundary_match("I am happy today", "happy") is True

    def test_english_substring_no_match(self):
        """English term as substring → no match."""
        assert word_boundary_match("unhappy", "happy") is False

    def test_english_case_insensitive(self):
        """English matching is case-insensitive."""
        assert word_boundary_match("HAPPY days", "happy") is True

    def test_english_at_start(self):
        """Term at start of string."""
        assert word_boundary_match("happy days", "happy") is True

    def test_english_at_end(self):
        """Term at end of string."""
        assert word_boundary_match("I am happy", "happy") is True

    # --- Arabic ---

    def test_arabic_standalone_word(self):
        """Arabic term as standalone word → match."""
        assert word_boundary_match("هذا سم خطير", "سم") is True

    def test_arabic_inside_word_no_match(self):
        """Arabic term inside another word → no match."""
        assert word_boundary_match("اسمي أحمد", "سم") is False

    def test_arabic_at_start(self):
        """Arabic term at start of text."""
        assert word_boundary_match("سم خطير", "سم") is True

    def test_arabic_at_end(self):
        """Arabic term at end of text."""
        assert word_boundary_match("هذا سم", "سم") is True

    # --- Auto-dispatch ---

    def test_dispatches_ascii(self):
        """ASCII terms go through English path."""
        assert word_boundary_match("test word here", "word") is True

    def test_dispatches_arabic(self):
        """Arabic terms go through Arabic path."""
        assert word_boundary_match("كلام جميل", "جميل") is True


class TestWordBoundaryMatchEn:
    """Specific tests for English word boundary matching."""

    def test_phrase_match(self):
        """Multi-word phrases can match."""
        assert word_boundary_match_en("do not worry", "do not") is True

    def test_empty_text(self):
        """Empty text → no match."""
        assert word_boundary_match_en("", "word") is False

    def test_empty_term(self):
        """Empty term → matches (empty regex matches everywhere)."""
        # This is technically regex behavior — document it
        assert word_boundary_match_en("hello", "") is True


class TestWordBoundaryMatchAr:
    """Specific tests for Arabic word boundary matching."""

    def test_poison_not_in_name(self):
        """سم (poison) must NOT match inside اسمي (my name)."""
        assert word_boundary_match_ar("اسمي أحمد", "سم") is False

    def test_poison_standalone(self):
        """سم (poison) standalone → match."""
        assert word_boundary_match_ar("هذا سم", "سم") is True

    def test_normalized_matching(self):
        """Matching should work on normalized text."""
        assert word_boundary_match_ar("هذا أحمد", "احمد") is True


class TestCompileEnPatterns:
    """Tests for compile_en_patterns utility."""

    def test_returns_correct_count(self):
        """Should return one pattern per marker."""
        patterns = compile_en_patterns(frozenset(["help", "decide"]))
        assert len(patterns) == 2

    def test_sorted_order(self):
        """Patterns should be sorted by marker text."""
        patterns = compile_en_patterns(frozenset(["zebra", "apple"]))
        assert patterns[0][1] == "apple"
        assert patterns[1][1] == "zebra"

    def test_pattern_matches(self):
        """Compiled patterns should match correctly."""
        patterns = compile_en_patterns(frozenset(["help"]))
        pat, text = patterns[0]
        assert pat.search("please help me") is not None
        assert pat.search("helpful") is None  # boundary check


# ═══════════════════════════════════════════════════════════
#  extract_dialect_markers
# ═══════════════════════════════════════════════════════════

class TestExtractDialectMarkers:
    """Tests for dialect marker extraction."""

    def test_gulf_markers(self):
        """Gulf dialect markers detected."""
        result = extract_dialect_markers("وش تبي يالله")
        assert "gulf" in result
        assert "وش" in result["gulf"]

    def test_egyptian_markers(self):
        """Egyptian dialect markers detected."""
        result = extract_dialect_markers("عايز ايه يا باشا")
        assert "egyptian" in result
        assert "عايز" in result["egyptian"]

    def test_levantine_markers(self):
        """Levantine dialect markers detected."""
        result = extract_dialect_markers("شو بدي أعمل")
        assert "levantine" in result

    def test_iraqi_markers(self):
        """Iraqi dialect markers detected."""
        result = extract_dialect_markers("شنو هسه")
        assert "iraqi" in result

    def test_maghrebi_markers(self):
        """Maghrebi dialect markers detected."""
        result = extract_dialect_markers("واش كيفاش")
        assert "maghrebi" in result

    def test_msa_markers(self):
        """MSA markers detected."""
        result = extract_dialect_markers("يرجى التواصل وفقاً للسياسة")
        assert "msa" in result

    def test_no_markers_english(self):
        """English text → empty result."""
        result = extract_dialect_markers("Hello World")
        assert result == {}

    def test_empty_string(self):
        """Empty string → empty result."""
        result = extract_dialect_markers("")
        assert result == {}

    def test_multiple_dialects(self):
        """Text with markers from multiple dialects."""
        # Gulf + Egyptian (يعني is in Gulf)
        result = extract_dialect_markers("عايز ايه يعني")
        assert len(result) >= 1


# ═══════════════════════════════════════════════════════════
#  detect_dialect
# ═══════════════════════════════════════════════════════════

class TestDetectDialect:
    """Tests for dialect detection."""

    def test_clear_gulf(self):
        """Multiple Gulf markers → 'gulf'."""
        assert detect_dialect("وش تبي يالله خلاص") == "gulf"

    def test_clear_egyptian(self):
        """Multiple Egyptian markers → 'egyptian'."""
        assert detect_dialect("عايز ايه كده ماشي") == "egyptian"

    def test_english_text(self):
        """English text → 'none'."""
        assert detect_dialect("Hello World") == "none"

    def test_msa_arabic(self):
        """Arabic without dialect markers → 'msa'."""
        assert detect_dialect("الحمد لله رب العالمين") == "msa"

    def test_empty_string(self):
        """Empty → 'none'."""
        assert detect_dialect("") == "none"


# ═══════════════════════════════════════════════════════════
#  has_dialect_markers
# ═══════════════════════════════════════════════════════════

class TestHasDialectMarkers:
    """Tests for quick dialect presence check."""

    def test_gulf(self):
        assert has_dialect_markers("وش الأخبار") is True

    def test_egyptian(self):
        assert has_dialect_markers("عايز حاجه") is True

    def test_english(self):
        assert has_dialect_markers("Hello") is False

    def test_msa_no_dialect(self):
        """MSA without colloquial markers → False."""
        assert has_dialect_markers("السلام عليكم") is False

    def test_empty(self):
        assert has_dialect_markers("") is False


# ═══════════════════════════════════════════════════════════
#  Constants validation
# ═══════════════════════════════════════════════════════════

class TestConstants:
    """Validate that exported constants are well-formed."""

    def test_negation_ar_is_tuple(self):
        assert isinstance(NEGATION_AR, tuple)
        assert len(NEGATION_AR) >= 5

    def test_negation_en_is_tuple(self):
        assert isinstance(NEGATION_EN, tuple)
        assert len(NEGATION_EN) >= 10

    def test_gulf_markers_is_tuple(self):
        assert isinstance(GULF_MARKERS, tuple)
        assert len(GULF_MARKERS) >= 15

    def test_egyptian_markers_is_tuple(self):
        assert isinstance(EGYPTIAN_MARKERS, tuple)
        assert len(EGYPTIAN_MARKERS) >= 10

    def test_no_duplicate_negation_ar(self):
        """No duplicate entries in Arabic negation list."""
        assert len(NEGATION_AR) == len(set(NEGATION_AR))

    def test_no_duplicate_gulf_markers(self):
        """No duplicate entries in Gulf markers."""
        assert len(GULF_MARKERS) == len(set(GULF_MARKERS))
