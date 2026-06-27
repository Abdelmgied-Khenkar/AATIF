#!/usr/bin/env python3
"""
AATIF Arabic Text Utilities — أدوات النص العربي
=================================================

Shared Arabic text normalization and similarity utilities used by:
  - Fingerprint (النمط)
  - Temporal Memory (الحقائق)
  - Contextual Intent (اللحظة)

Why this exists:
  Arabic morphology is complex — clitics, prefixes, alef variants,
  taa marbuta, hamza forms. Each triad module was doing its own
  ad-hoc text processing (or none at all). This module provides a
  single, consistent normalization pipeline so the same text
  produces the same tokens everywhere.

  One function, one truth — not three half-implementations.

Design principles:
  - Lightweight: no ML, no embeddings. Pure string operations.
  - Deterministic: same input always produces same output.
  - Composable: normalize_arabic() is the main entry point;
    internal steps are exposed for testing but not for daily use.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import re
from typing import List, Set


# ═══════════════════════════════════════════════════════════
#  Normalization maps
# ═══════════════════════════════════════════════════════════

# Alef variants → bare alef
_ALEF_VARIANTS = {
    "أ": "ا",  # أ → ا
    "إ": "ا",  # إ → ا
    "آ": "ا",  # آ → ا
    "ٱ": "ا",  # ٱ → ا  (alef wasla)
}

# Taa marbuta → haa
_TAA_MARBUTA = {
    "ة": "ه",  # ة → ه
}

# Hamza variants → plain hamza or remove
_HAMZA_VARIANTS = {
    "ؤ": "و",  # ؤ → و
    "ئ": "ي",  # ئ → ي
}

# Diacritics (tashkeel) to strip — fatha, damma, kasra, shadda, sukun, tanween
_TASHKEEL = re.compile(
    "[ؐ-ًؚ-ٰٟۖ-ۜ۟-ۤ"
    "ۧ-۪ۨ-ۭ]"
)

# Tatweel (kashida) — decorative stretching character
_TATWEEL = "ـ"  # ـ

# Punctuation (Arabic + Latin) to replace with spaces
_PUNCTUATION = re.compile(r'[؟?!.,;:،؛\-\(\)\[\]{}"\'`…–—/\\@#$%^&*+=<>|~]')

# Common Arabic prefixes (clitics): و ف ب ك ل لل ال
# We strip leading single-char clitics and definite article "ال"
_PREFIX_PATTERN = re.compile(r"^(?:وال|فال|بال|كال|لل|ال|و|ف|ب|ك|ل)")


# ═══════════════════════════════════════════════════════════
#  Core normalization
# ═══════════════════════════════════════════════════════════

def normalize_arabic(text: str) -> str:
    """
    Normalize Arabic text for consistent comparison.

    Steps:
      1. Strip diacritics (tashkeel)
      2. Remove tatweel (kashida)
      3. Normalize alef variants (أ إ آ ٱ → ا)
      4. Normalize taa marbuta (ة → ه)
      5. Normalize hamza-on-carrier (ؤ → و, ئ → ي)
      6. Lowercase (for any Latin mixed in)

    Does NOT strip prefixes — that's a separate step for tokenization.
    Normalization is about making the same word match itself regardless
    of encoding or diacritical variation.

    Args:
        text: raw Arabic (or mixed) text.

    Returns:
        Normalized text — same structure, consistent characters.

    Example:
        >>> normalize_arabic("الإسْلام")
        'الاسلام'
        >>> normalize_arabic("مَدْرَسَة")
        'مدرسه'
    """
    # Step 1: strip diacritics
    text = _TASHKEEL.sub("", text)

    # Step 2: remove tatweel
    text = text.replace(_TATWEEL, "")

    # Step 3: normalize alef variants
    for src, dst in _ALEF_VARIANTS.items():
        text = text.replace(src, dst)

    # Step 4: normalize taa marbuta
    for src, dst in _TAA_MARBUTA.items():
        text = text.replace(src, dst)

    # Step 5: normalize hamza-on-carrier
    for src, dst in _HAMZA_VARIANTS.items():
        text = text.replace(src, dst)

    # Step 6: lowercase (for Latin chars)
    text = text.lower()

    return text


def tokenize_arabic(text: str, strip_prefixes: bool = True) -> Set[str]:
    """
    Tokenize Arabic text into a set of normalized tokens.

    Steps:
      1. Normalize the text (normalize_arabic)
      2. Replace punctuation with spaces
      3. Split on whitespace
      4. Optionally strip common prefixes (clitics)
      5. Filter out single-character tokens (noise)

    Args:
        text: raw text to tokenize.
        strip_prefixes: if True, strip leading clitics/articles.

    Returns:
        Set of normalized tokens (at least 2 chars each).
    """
    normalized = normalize_arabic(text)
    cleaned = _PUNCTUATION.sub(" ", normalized)
    raw_tokens = cleaned.split()

    tokens: Set[str] = set()
    for token in raw_tokens:
        token = token.strip()
        if strip_prefixes:
            stripped = _PREFIX_PATTERN.sub("", token)
            # Only use stripped version if it leaves something meaningful
            if len(stripped) >= 2:
                token = stripped
        if len(token) >= 2:
            tokens.add(token)

    return tokens


# ═══════════════════════════════════════════════════════════
#  Similarity functions
# ═══════════════════════════════════════════════════════════

def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """
    Jaccard similarity: |A ∩ B| / |A ∪ B|.

    Args:
        set_a: first token set.
        set_b: second token set.

    Returns:
        Float in [0.0, 1.0]. Returns 0.0 if both sets are empty.
    """
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def ngram_overlap(text_a: str, text_b: str, n: int = 3) -> float:
    """
    Character n-gram overlap between two normalized texts.

    Better than word-level Jaccard for Arabic because it captures
    partial morphological matches — "يتعلمون" and "يتعلم" share
    most of their character n-grams even though they're different
    word tokens.

    Args:
        text_a: first text (will be normalized).
        text_b: second text (will be normalized).
        n: n-gram size (default 3 — trigrams).

    Returns:
        Float in [0.0, 1.0]. Returns 0.0 if either text is too short.
    """
    a = normalize_arabic(text_a).replace(" ", "")
    b = normalize_arabic(text_b).replace(" ", "")

    if len(a) < n or len(b) < n:
        return 0.0

    grams_a = {a[i:i + n] for i in range(len(a) - n + 1)}
    grams_b = {b[i:i + n] for i in range(len(b) - n + 1)}

    intersection = grams_a & grams_b
    union = grams_a | grams_b

    if not union:
        return 0.0
    return len(intersection) / len(union)


def combined_similarity(text_a: str, text_b: str) -> float:
    """
    Combined similarity score using both Jaccard (word-level)
    and n-gram overlap (character-level).

    Formula: 0.4 * jaccard + 0.6 * ngram_overlap
    The n-gram component is weighted higher because it handles
    Arabic morphological variation better.

    Args:
        text_a: first text (raw).
        text_b: second text (raw).

    Returns:
        Float in [0.0, 1.0].
    """
    tokens_a = tokenize_arabic(text_a)
    tokens_b = tokenize_arabic(text_b)
    j_sim = jaccard_similarity(tokens_a, tokens_b)
    n_sim = ngram_overlap(text_a, text_b, n=3)
    return 0.4 * j_sim + 0.6 * n_sim
