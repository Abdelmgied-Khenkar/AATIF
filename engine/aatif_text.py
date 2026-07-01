#!/usr/bin/env python3
"""
AATIF Shared Text Utilities — أدوات النص المشتركة
====================================================

Consolidated text-processing utilities used across 18+ engine modules.

This module is B-prime (خدمية): it provides shared text operations
but carries no governance logic. Governance modules should import
these utilities instead of re-implementing them.

Consolidates patterns from:
  - normalize_arabic: 18+ independent implementations across engine/
  - detect_negation: 11 modules with varying negation word lists
  - word_boundary_match: 11 modules with Arabic-aware boundary logic
  - extract_dialect_markers: 19 modules with dialect detection
  - arabic_ratio: multiple modules checking if text is Arabic

Design principles:
  - Lightweight: no ML, no embeddings. Pure string / regex operations.
  - Deterministic: same input always produces same output.
  - Composable: each function is independent, can be used standalone.
  - Unicode-safe: handles Arabic diacritics, hamza variants, etc.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════
#  Normalization constants
# ═══════════════════════════════════════════════════════════

# Alef variants → bare alef
ALEF_VARIANTS: Dict[str, str] = {
    "أ": "ا",  # أ → ا  (hamza above)
    "إ": "ا",  # إ → ا  (hamza below)
    "آ": "ا",  # آ → ا  (madda above)
    "ٱ": "ا",  # ٱ → ا  (alef wasla)
}

# Taa marbuta → haa
TAA_MARBUTA: Dict[str, str] = {
    "ة": "ه",  # ة → ه
}

# Hamza on carrier → carrier
HAMZA_ON_CARRIER: Dict[str, str] = {
    "ؤ": "و",  # ؤ → و
    "ئ": "ي",  # ئ → ي
}

# Alef maqsura → yaa
ALEF_MAQSURA: Dict[str, str] = {
    "ى": "ي",  # ى → ي
}

# Diacritics (tashkeel) to strip — comprehensive regex
# Covers: fatha, damma, kasra, shadda, sukun, tanween, superscript alef,
# and other Arabic combining marks
_TASHKEEL_RE = re.compile(
    "["
    "ؐ-ؚ"   # Arabic sign range
    "ً-ٟ"   # Fathatan through Wavy Hamza Below
    "ٰ"          # Superscript Alef
    "ۖ-ۜ"   # Small High Ligature markers
    "۟-ۤ"   # Small High Rounded Zero etc.
    "ۧ-ۨ"   # Small High Yeh/Noon
    "۪-ۭ"   # Empty/Filled Centre marks
    "]"
)

# Tatweel (kashida) — decorative stretching character
_TATWEEL = "ـ"

# Arabic character detection
_ARABIC_CHAR_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]")

# Arabic letter class for word boundary matching
_AR_LETTER_CLASS = r"ء-يٮ-ٯٱ-ۓ"


# ═══════════════════════════════════════════════════════════
#  Negation constants
# ═══════════════════════════════════════════════════════════

# Arabic negation words — union of all lists found across 11 modules
NEGATION_AR: Tuple[str, ...] = (
    "ما",      # ما
    "لا",      # لا
    "مش",      # مش
    "ماني",  # ماني
    "مو",      # مو
    "مب",      # مب
    "مهو",  # مهو
    "مهي",  # مهي
    "موب",  # موب
)

# English negation prefixes — union of patterns from maqam_architecture etc.
NEGATION_EN: Tuple[str, ...] = (
    "i'm not ", "im not ", "i am not ", "not really ",
    "don't ", "dont ", "do not ", "doesn't ", "doesnt ", "does not ",
    "isn't ", "isnt ", "is not ",
    "wasn't ", "wasnt ", "was not ",
    "can't ", "cant ", "cannot ",
    "won't ", "wont ", "will not ",
    "no ", "never ", "not ", "without ",
)


# ═══════════════════════════════════════════════════════════
#  Dialect marker constants
# ═══════════════════════════════════════════════════════════

# Gulf dialect markers (Saudi, UAE, Kuwait, Qatar, Bahrain, Oman)
GULF_MARKERS: Tuple[str, ...] = (
    "وش", "ايش", "ابي", "ابغى", "عشان", "يعني", "خلاص", "طيب",
    "كذا", "يبيله", "حيل", "مره", "وشلون", "يالله", "تراني",
    "اللحين", "الحين", "هالشي", "ذا", "ودي", "ترى",
    "يلا", "طفران", "طفرانة", "يزبط", "أقولك",
)

# Egyptian dialect markers
EGYPTIAN_MARKERS: Tuple[str, ...] = (
    "عايز", "ازاي", "كده", "ايه", "ماشي", "حاجه", "حاجة",
    "بتاع", "دي", "ده", "مش", "كمان", "عاوز", "فين", "ليه",
    "بقي", "بقى",
)

# Levantine dialect markers
LEVANTINE_MARKERS: Tuple[str, ...] = (
    "شو", "كيف", "بدي", "هلأ", "منيح", "هيك",
)

# Iraqi dialect markers
IRAQI_MARKERS: Tuple[str, ...] = (
    "شنو", "شلون", "هسه",
)

# Maghrebi dialect markers
MAGHREBI_MARKERS: Tuple[str, ...] = (
    "واش", "كيفاش", "بزاف",
)

# MSA (Modern Standard Arabic) markers
MSA_MARKERS: Tuple[str, ...] = (
    "أريد", "أرغب", "يرجى", "لذلك", "بناءً", "حيث",
    "إضافةً", "علاوةً", "من ثم", "وفقاً", "تحديداً",
)

# All dialect markers combined (for simple presence check)
ALL_DIALECT_MARKERS: Tuple[str, ...] = (
    GULF_MARKERS + EGYPTIAN_MARKERS + LEVANTINE_MARKERS
    + IRAQI_MARKERS + MAGHREBI_MARKERS
)


# ═══════════════════════════════════════════════════════════
#  Core normalization
# ═══════════════════════════════════════════════════════════


def normalize_arabic(text: str) -> str:
    """Normalize Arabic text for consistent comparison.

    Steps:
      1. Strip diacritics (tashkeel)
      2. Remove tatweel (kashida)
      3. Normalize alef variants (أ إ آ ٱ → ا)
      4. Normalize taa marbuta (ة → ه)
      5. Normalize hamza-on-carrier (ؤ → و, ئ → ي)
      6. Normalize alef maqsura (ى → ي)
      7. Lowercase (for any Latin mixed in)

    Compatible with the canonical implementation in aatif_arabic_utils.
    Does NOT strip prefixes — that's tokenization, not normalization.

    This consolidates 18+ independent implementations across engine/.

    Args:
        text: Raw Arabic (or mixed) text.

    Returns:
        Normalized text — same structure, consistent characters.

    Examples:
        >>> normalize_arabic("الإسْلام")
        'الاسلام'
        >>> normalize_arabic("مَدْرَسَة")
        'مدرسه'
        >>> normalize_arabic("Hello World")
        'hello world'
    """
    # Step 1: strip diacritics
    text = _TASHKEEL_RE.sub("", text)

    # Step 2: remove tatweel
    text = text.replace(_TATWEEL, "")

    # Step 3: normalize alef variants
    for src, dst in ALEF_VARIANTS.items():
        text = text.replace(src, dst)

    # Step 4: normalize taa marbuta
    for src, dst in TAA_MARBUTA.items():
        text = text.replace(src, dst)

    # Step 5: normalize hamza-on-carrier
    for src, dst in HAMZA_ON_CARRIER.items():
        text = text.replace(src, dst)

    # Step 6: normalize alef maqsura
    for src, dst in ALEF_MAQSURA.items():
        text = text.replace(src, dst)

    # Step 7: lowercase (for Latin chars)
    text = text.lower()

    return text


def strip_tashkeel(text: str) -> str:
    """Remove Arabic diacritical marks (tashkeel) only.

    Unlike normalize_arabic, this does NOT change letter forms —
    just removes the vowel marks.

    Args:
        text: Arabic text potentially with diacritics.

    Returns:
        Text with diacritics removed.

    Examples:
        >>> strip_tashkeel("بِسْمِ اللَّهِ")
        'بسم الله'
        >>> strip_tashkeel("Hello")
        'Hello'
    """
    return _TASHKEEL_RE.sub("", text)


def strip_tashkeel_nfd(text: str) -> str:
    """Remove diacritics using Unicode NFD decomposition.

    Alternative approach used by aatif_cold_os — decomposes characters
    and removes non-spacing marks (Mn category). Slightly broader than
    the regex approach.

    Args:
        text: Arabic text potentially with diacritics.

    Returns:
        Text with all combining marks removed.

    Examples:
        >>> strip_tashkeel_nfd("بِسْمِ اللَّهِ")
        'بسم الله'
    """
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


# ═══════════════════════════════════════════════════════════
#  Arabic text analysis
# ═══════════════════════════════════════════════════════════


def arabic_ratio(text: str) -> float:
    """Fraction of non-space characters that are Arabic script.

    Consolidates the _arabic_ratio pattern from aatif_r_equation,
    aatif_fingerprint, and others.

    Args:
        text: Any text.

    Returns:
        Float in [0.0, 1.0]. Returns 0.0 for empty text.

    Examples:
        >>> arabic_ratio("مرحبا")
        1.0
        >>> arabic_ratio("Hello")
        0.0
        >>> arabic_ratio("")
        0.0
    """
    if not text:
        return 0.0
    arabic_count = len(_ARABIC_CHAR_RE.findall(text))
    total = len(text.replace(" ", ""))
    if total == 0:
        return 0.0
    return arabic_count / total


def is_arabic(text: str, threshold: float = 0.5) -> bool:
    """Check if text is predominantly Arabic.

    Args:
        text: Any text.
        threshold: Minimum Arabic character ratio.

    Returns:
        True if Arabic ratio exceeds threshold.

    Examples:
        >>> is_arabic("مرحبا بالعالم")
        True
        >>> is_arabic("Hello World")
        False
    """
    return arabic_ratio(text) >= threshold


# ═══════════════════════════════════════════════════════════
#  Negation detection
# ═══════════════════════════════════════════════════════════


def detect_negation(text: str) -> bool:
    """Check if text contains a negation word (Arabic or English).

    Simple presence check — does any negation word appear in the text?
    For position-aware negation (checking if a specific marker is negated),
    use is_marker_negated() instead.

    Consolidates negation lists from 11+ modules.

    Args:
        text: Input text to check.

    Returns:
        True if any negation word is found.

    Examples:
        >>> detect_negation("ما أبي")
        True
        >>> detect_negation("I don't want this")
        True
        >>> detect_negation("أبي شاي")
        False
        >>> detect_negation("I want tea")
        False
    """
    norm = normalize_arabic(text)
    low = text.lower()

    # Check Arabic negation in normalized text
    for neg in NEGATION_AR:
        neg_norm = normalize_arabic(neg)
        if neg_norm in norm:
            return True

    # Check English negation in lowered text
    for neg in NEGATION_EN:
        if neg in low:
            return True

    return False


def is_marker_negated(
    text: str,
    marker: str,
    lookbehind_chars: int = 20,
) -> bool:
    """Check if a specific marker/keyword is preceded by negation.

    Looks at the text before the marker position for negation words.
    Consolidates _is_negated from aatif_maqam_architecture and
    _has_negation_prefix from aatif_dual_root.

    Args:
        text: Full text to search in.
        marker: The marker/keyword to check for negation.
        lookbehind_chars: How many characters before the marker to search.

    Returns:
        True if the marker is preceded by a negation.

    Examples:
        >>> is_marker_negated("مش مبسوط", "مبسوط")
        True
        >>> is_marker_negated("أنا مبسوط", "مبسوط")
        False
        >>> is_marker_negated("I'm not happy", "happy")
        True
        >>> is_marker_negated("I am happy", "happy")
        False
    """
    text_lower = text.lower()
    marker_lower = marker.lower()
    idx = text_lower.find(marker_lower)
    if idx < 0:
        # Also try normalized Arabic
        norm = normalize_arabic(text)
        marker_norm = normalize_arabic(marker)
        idx = norm.find(marker_norm)
        if idx < 0:
            return False
        prefix = norm[max(0, idx - lookbehind_chars):idx]
        for neg in NEGATION_AR:
            neg_norm = normalize_arabic(neg)
            if neg_norm in prefix:
                return True
        return False

    prefix = text_lower[max(0, idx - lookbehind_chars):idx]

    # Check English negation
    for neg in NEGATION_EN:
        if prefix.endswith(neg) or prefix.rstrip().endswith(neg.rstrip()):
            return True

    # Check Arabic negation (on original text prefix)
    ar_prefix = text[max(0, idx - lookbehind_chars):idx]
    for neg in NEGATION_AR:
        if neg in ar_prefix:
            return True

    return False


# ═══════════════════════════════════════════════════════════
#  Word boundary matching
# ═══════════════════════════════════════════════════════════


def word_boundary_match_en(text: str, term: str) -> bool:
    r"""Check if an English term appears as a whole word in text.

    Uses \b word boundaries with case-insensitive matching.

    Args:
        text: Text to search in.
        term: English word/phrase to find.

    Returns:
        True if term appears as a whole word.

    Examples:
        >>> word_boundary_match_en("I am happy today", "happy")
        True
        >>> word_boundary_match_en("unhappy", "happy")
        False
        >>> word_boundary_match_en("HAPPY days", "happy")
        True
    """
    return re.search(
        r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE
    ) is not None


def word_boundary_match_ar(text: str, term: str) -> bool:
    """Check if an Arabic term appears with word boundaries in text.

    Arabic doesn't use \\b word boundaries the same way as Latin text.
    Instead, we check that the term is not surrounded by Arabic letters,
    preventing "سم" (poison) from matching inside "اسمي" (my name).

    Consolidates _present_word from aatif_multi_intent_collision.

    Args:
        text: Arabic text to search in (should be normalized).
        term: Arabic word to find.

    Returns:
        True if term appears as a standalone word.

    Examples:
        >>> word_boundary_match_ar("هذا سم خطير", "سم")
        True
        >>> word_boundary_match_ar("اسمي أحمد", "سم")
        False
    """
    norm_text = normalize_arabic(text)
    norm_term = normalize_arabic(term)
    pat = rf"(?<![{_AR_LETTER_CLASS}]){re.escape(norm_term)}(?![{_AR_LETTER_CLASS}])"
    return re.search(pat, norm_text) is not None


def word_boundary_match(text: str, term: str) -> bool:
    """Check if a term appears as a whole word, auto-detecting language.

    Dispatches to word_boundary_match_en or word_boundary_match_ar
    based on whether the term contains ASCII or Arabic characters.

    Args:
        text: Text to search in.
        term: Word/phrase to find.

    Returns:
        True if the term appears as a bounded word.

    Examples:
        >>> word_boundary_match("I am happy", "happy")
        True
        >>> word_boundary_match("هذا سم خطير", "سم")
        True
        >>> word_boundary_match("unhappy", "happy")
        False
    """
    if term.isascii():
        return word_boundary_match_en(text, term)
    return word_boundary_match_ar(text, term)


def compile_en_patterns(
    markers: frozenset,
) -> List[Tuple[re.Pattern, str]]:
    """Pre-compile English markers with word-boundary regexes.

    Consolidates _compile_en_patterns from aatif_cold_os.

    Args:
        markers: Frozenset of English marker strings.

    Returns:
        List of (compiled_pattern, marker_text) tuples, sorted by marker.

    Examples:
        >>> patterns = compile_en_patterns(frozenset(["help", "decide"]))
        >>> len(patterns)
        2
    """
    return [
        (re.compile(r"\b" + re.escape(m) + r"\b", re.IGNORECASE), m)
        for m in sorted(markers)
    ]


# ═══════════════════════════════════════════════════════════
#  Dialect detection
# ═══════════════════════════════════════════════════════════


def extract_dialect_markers(text: str) -> Dict[str, List[str]]:
    """Extract dialect markers found in text, grouped by dialect.

    Scans text for known dialect markers across Gulf, Egyptian,
    Levantine, Iraqi, and Maghrebi Arabic. Also checks MSA markers.

    Consolidates dialect detection from 19 modules.

    Args:
        text: Arabic text to analyze.

    Returns:
        Dict mapping dialect names to lists of found markers.
        Only dialects with at least one match are included.

    Examples:
        >>> result = extract_dialect_markers("وش تبي يا حبيبي")
        >>> "gulf" in result
        True
        >>> "وش" in result["gulf"]
        True
    """
    norm = normalize_arabic(text)
    result: Dict[str, List[str]] = {}

    dialect_map = {
        "gulf": GULF_MARKERS,
        "egyptian": EGYPTIAN_MARKERS,
        "levantine": LEVANTINE_MARKERS,
        "iraqi": IRAQI_MARKERS,
        "maghrebi": MAGHREBI_MARKERS,
        "msa": MSA_MARKERS,
    }

    for dialect_name, markers in dialect_map.items():
        found = []
        for m in markers:
            m_norm = normalize_arabic(m)
            if m_norm in norm:
                found.append(m)
        if found:
            result[dialect_name] = found

    return result


def detect_dialect(text: str) -> str:
    """Detect the primary dialect of Arabic text.

    Returns the dialect with the most markers found, or "msa" if
    Arabic text with no dialect markers, or "none" if not Arabic.

    Consolidates _detect_dialect from aatif_maqam_architecture,
    _has_dialect from aatif_r_equation, and dialect detection in
    aatif_fingerprint.

    Args:
        text: Text to analyze.

    Returns:
        One of: "gulf", "egyptian", "levantine", "iraqi",
        "maghrebi", "msa", "mixed", "none".

    Examples:
        >>> detect_dialect("وش تبي يالله خلاص")
        'gulf'
        >>> detect_dialect("Hello world")
        'none'
    """
    markers = extract_dialect_markers(text)

    # Remove MSA from competition (it's the fallback)
    dialects_found = {k: v for k, v in markers.items() if k != "msa"}

    if not dialects_found:
        # No colloquial markers found
        if arabic_ratio(text) > 0.3:
            return "msa"
        return "none"

    # Find the dialect with the most markers
    best_dialect = max(dialects_found, key=lambda k: len(dialects_found[k]))
    best_count = len(dialects_found[best_dialect])

    # Check for mixed — if another dialect also has matches
    other_counts = [
        len(v) for k, v in dialects_found.items()
        if k != best_dialect
    ]
    if other_counts and max(other_counts) >= best_count:
        return "mixed"

    if best_count >= 2:
        return best_dialect
    elif best_count == 1:
        return "mixed"

    return "msa" if arabic_ratio(text) > 0.3 else "none"


def has_dialect_markers(text: str) -> bool:
    """Quick check: does text contain any Arabic dialect markers?

    Consolidates _has_dialect from aatif_r_equation.

    Args:
        text: Text to check.

    Returns:
        True if any dialect marker is found.

    Examples:
        >>> has_dialect_markers("وش الأخبار")
        True
        >>> has_dialect_markers("Hello")
        False
    """
    norm = normalize_arabic(text)
    for marker in ALL_DIALECT_MARKERS:
        m_norm = normalize_arabic(marker)
        if m_norm in norm:
            return True
    return False


# ═══════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("aatif_text — shared text utilities loaded OK")
    print()

    # Quick smoke tests
    print("normalize_arabic('الإسْلام') =", repr(normalize_arabic("الإسْلام")))
    print("arabic_ratio('مرحبا') =", arabic_ratio("مرحبا"))
    print("detect_negation('ما أبي') =", detect_negation("ما أبي"))
    print("detect_dialect('وش تبي يالله') =", detect_dialect("وش تبي يالله"))
    print("word_boundary_match('I am happy', 'happy') =",
          word_boundary_match("I am happy", "happy"))
    print()
    print("All utilities loaded OK.")
