"""
aatif_arabizi_transliterator.py — Arabizi → Arabic Script Transliterator

Slogan: "The attacker writes Arabic in Latin. The scorer must read it back."
        المهاجم يكتب العربية بحروف لاتينية. المُقيِّم لازم يقرأها عربي.

Core concept
------------
Arabizi (also: Franco-Arabic, Arabish, 3arabizi) is Arabic written with
Latin letters and digits, where digits stand in for Arabic letters that
have no Latin equivalent:

    "9tl"        → "قتل"   (kill)
    "7rg"        → "حرق"   (burn)
    "3adi"       → "عادي"  (normal / it's fine)
    "ya 7abiibi" → "يا حبيبي" (my love)

This is a CRITICAL security blind spot.  When harmful Arabic intent is
written in Arabizi, the semantic scorer only sees Latin noise — cosine
similarity with the Arabic harm anchors collapses (~0.38 vs ~0.70 for
Arabic script).  Maghrebi / North-African users lean on Arabizi most
heavily, and an attacker can exploit the gap to smuggle harmful intent
past a scorer that only speaks Arabic script.

This module closes the gap by DETECTING Arabizi and TRANSLITERATING it
back to Arabic script, so the Governor/scorer can evaluate BOTH the
original and the transliterated form.  The transliteration does not need
to be perfect: even ~70% skeleton accuracy lifts cosine similarity from
~0.38 into the 0.55–0.70 range, and the anchors do the rest.

Authority contract
------------------
This is a B-prime **preprocessor**.  It never makes a safety decision.
It hands the Governor/scorer a second string to look at — nothing more.

    AUTHORITY_LEVEL            = B_PRIME_OBSERVATIONAL
    CAN_BLOCK_RUNTIME          = False
    CAN_MODIFY_H               = False
    CAN_MODIFY_THETA           = False
    CAN_MODIFY_S               = False
    CAN_EMIT_JUDICIAL_DECISION = False
    BINDING_CHANNEL            = B1 (Input preprocessing)

Constitutional invariants
-------------------------
Invariant 1: This module never modifies H, θ, S, H_eff, or verdicts.
Invariant 2: It only ADDS a transliterated view; it discards nothing.
Invariant 3: The GovernanceEquation remains the only judicial authority.
Invariant 4: Text already in Arabic script → passed through untouched.
Invariant 5: Deterministic — same input always gives the same output.

Dialect note (why 9 → ق here)
-----------------------------
Arabizi digit conventions vary by region:
    Levantine/Gulf:  9 → ص,  8 → ق
    Maghrebi:        9 → ق  ("9tl" = قتل, "9alb" = قلب)
Because the harm-critical examples ("9tl", "7rg") and the heaviest
Arabizi users are Maghrebi, and because a safety scorer must fail
towards *catching* "kill", we map 9 → ق (Maghrebi reading).  The ص
reading is the main precision cost of that choice; it is accepted
deliberately (safety-first, per the 70%-is-enough design principle).

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ── Shared Arabic ratio helper; fall back to a local copy in standalone mode ──
try:
    from aatif_text import arabic_ratio
except ImportError:  # pragma: no cover - standalone fallback
    _ARABIC_CHAR_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]")

    def arabic_ratio(text: str) -> float:
        if not text:
            return 0.0
        ac = len(_ARABIC_CHAR_RE.findall(text))
        total = len(text.replace(" ", ""))
        return ac / total if total else 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Feature flags & thresholds
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ARABIZI_ENABLED = True           # master switch
_MIN_TEXT_LENGTH = 2             # sparse activation threshold

# A token scoring at/above this is treated as Arabizi (used by both the
# detector and the token-aware transliterator).
TOKEN_ARABIZI_THRESHOLD = 0.5

# process()/is_arabizi(): confidence at/above this flips the boolean flag.
DETECT_THRESHOLD = 0.5

# If the input is already mostly Arabic script, it is not Arabizi.
_ARABIC_SCRIPT_CUTOFF = 0.30


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Transliteration maps  (longest-match wins)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Two-character sequences — checked BEFORE single characters so that
# digit+apostrophe combos and Latin digraphs are not split apart.
TWO_CHAR_MAP: Dict[str, str] = {
    # digit + apostrophe (dotted / emphatic variants)
    "3'": "غ",   # ghayn
    "7'": "خ",   # khaa (alt. of 5)
    "6'": "ظ",   # zaa (emphatic)
    "9'": "ض",   # daad (emphatic)
    "2'": "ء",   # hamza variant
    # Latin digraphs
    "kh": "خ",
    "gh": "غ",
    "sh": "ش",
    "ch": "ش",   # Maghrebi/loanword sheen
    "th": "ث",
    "dh": "ذ",
    # long vowels (doubled Latin vowels)
    "aa": "ا",
    "ee": "ي",
    "ii": "ي",
    "oo": "و",
    "ou": "و",
    "uu": "و",
}

# Single characters — digits first (Arabic number-letter substitutions),
# then Latin consonants and vowels.
ONE_CHAR_MAP: Dict[str, str] = {
    # ── Arabizi digits ──
    "2": "ء",   # hamza / alif-hamza
    "3": "ع",   # ayn
    "5": "خ",   # khaa
    "6": "ط",   # taa (emphatic)
    "7": "ح",   # haa
    "8": "ق",   # qaf (Levantine/Gulf reading)
    "9": "ق",   # qaf (Maghrebi reading — see module docstring)
    # ── Latin consonants ──
    "b": "ب",
    "c": "ك",
    "d": "د",
    "f": "ف",
    "g": "ق",   # required for "7rg" → "حرق"; ج in Egyptian usage (accepted cost)
    "h": "ه",
    "j": "ج",
    "k": "ك",
    "l": "ل",
    "m": "م",
    "n": "ن",
    "p": "ب",
    "q": "ق",
    "r": "ر",
    "s": "س",
    "t": "ت",
    "v": "ف",
    "w": "و",
    "x": "كس",
    "y": "ي",
    "z": "ز",
    # ── Latin vowels (matres lectionis) ──
    "a": "ا",
    "e": "ي",
    "i": "ي",
    "o": "و",
    "u": "و",
    # apostrophe on its own is decorative — drop it
    "'": "",
}

# Digits that carry Arabic-letter meaning in Arabizi (0/1/4 do not).
_ARABIZI_DIGITS = frozenset("2356789")

# Latin digraphs that strongly signal Arabizi.
_ARABIZI_DIGRAPHS = ("kh", "gh", "sh", "ch", "th", "dh")

_LATIN_VOWELS = frozenset("aeiou")

# Common Arabizi function/filler words with no digits and normal vowel
# ratios — they would otherwise read as plain English.
KNOWN_ARABIZI_WORDS: frozenset = frozenset({
    "ya", "wallah", "walla", "yalla", "yallah", "khalas", "khlas",
    "habibi", "habibti", "habib", "inshallah", "mashallah", "hamdillah",
    "ana", "enta", "inta", "enti", "inti", "howa", "heya", "ehna", "ento",
    "wesh", "wach", "chno", "chnou", "kifak", "kifik", "keef", "kif",
    "shu", "esh", "eish", "laish", "leh", "bezaf", "bzaf", "wa", "wu",
    "meya", "safi", "bara", "brra", "labas", "hna", "hnaya", "mzyan",
    "shukran", "shukrun", "shokran", "sahbi", "sa7bi", "khoya", "sadi9",
})

# Low-vowel / consonant-cluster tokens that are English or chat noise,
# NOT Arabizi.  Guards the low-vowel heuristic against false positives.
ENGLISH_DENYLIST: frozenset = frozenset({
    "lol", "lmao", "rofl", "omg", "wtf", "fyi", "btw", "tbh", "idk",
    "brb", "smh", "imo", "imho", "ngl", "tldr", "afaik", "hmm", "mmm",
    "hmmm", "grr", "ugh", "pfft", "psst", "shh", "tsk", "pls", "plz",
    "thx", "gym", "why", "shy", "spy", "cry", "dry", "fly", "sky",
    "fry", "myth", "hymn", "crypt", "nymph", "html", "css", "sql",
    "png", "jpg", "gif", "pdf", "url", "http", "https", "www",
    "by", "my", "try", "thy", "wry", "sly", "ply", "sty", "psst",
})

# Technical / brand tokens where an Arabizi digit is incidental.
TECH_DENYLIST: frozenset = frozenset({
    "mp3", "mp3s", "h2o", "o2", "co2", "3d", "2d", "3g", "4g", "5g",
    "b2b", "b2c", "p2p", "24x7", "24x365", "mp4", "log2",
})

# URLs / emails / @mentions — stripped before scoring so their Latin
# letters and digits do not masquerade as Arabizi.
_STRIP_RE = re.compile(
    r"(https?://\S+|www\.\S+|\S+@\S+\.\S+|[@#][A-Za-z0-9_]+)"
)

# Word tokens: Latin letters, Arabizi digits, and the apostrophe.
_TOKEN_RE = re.compile(r"[A-Za-z0-9']+")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Result dataclass
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class ArabiziResult:
    """The output of :func:`process`.

    Both ``original`` and ``transliterated`` are handed to the scorer so
    it can evaluate whichever gives the stronger anchor similarity.  This
    dataclass is a *view*, never a verdict — the Governor decides.
    """
    is_arabizi: bool          # confidence >= DETECT_THRESHOLD
    confidence: float         # 0.0 – 1.0
    original: str             # input, unchanged
    transliterated: str       # Arabic-script rendering of Arabizi tokens

    # ── Isolation marker (B-prime contract) ──
    _isolation_marker: str = "B1_PREPROCESS_NOT_FOR_SAFETY"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Transliterator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ArabiziTransliterator:
    """Detect Arabizi and transliterate it to Arabic script.

    All logic is deterministic and rule-based — no embeddings, no LLM,
    no network.  The class is stateless; every call is self-contained.
    """

    # ── Authority contract (B-prime preprocessor) ──
    AUTHORITY_LEVEL            = "B_PRIME_OBSERVATIONAL"
    CAN_BLOCK_RUNTIME          = False
    CAN_MODIFY_H               = False
    CAN_MODIFY_THETA           = False
    CAN_MODIFY_S               = False
    CAN_EMIT_JUDICIAL_DECISION = False
    BINDING_CHANNEL            = "B1"

    ISOLATION_MARKER  = "B1_PREPROCESS_NOT_FOR_SAFETY"
    ISOLATION_CONTRACT = (
        "Arabizi transliteration is a B-prime input preprocessor. "
        "It detects Latin-script Arabic and produces an Arabic-script "
        "view for the scorer. It NEVER modifies H, θ, S, or verdicts. "
        "It NEVER blocks runtime. The GovernanceEquation remains the "
        "only judicial authority."
    )

    def __init__(self) -> None:
        pass  # stateless

    # ─────────────────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────────────────

    def is_arabizi(self, text: str) -> float:
        """Return a 0.0–1.0 confidence that ``text`` is Arabizi.

        0.0  → not Arabizi (pure English, pure Arabic script, empty).
        1.0  → unmistakably Arabizi.

        The score combines two signals: the *fraction* of word tokens
        that look Arabizi, and the *strongest* single Arabizi token.
        """
        if not ARABIZI_ENABLED:
            return 0.0
        if not text or len(text.strip()) < _MIN_TEXT_LENGTH:
            return 0.0

        # Already Arabic script → by definition not Arabizi.
        if arabic_ratio(text) >= _ARABIC_SCRIPT_CUTOFF:
            return 0.0

        cleaned = _STRIP_RE.sub(" ", text)
        tokens = [t for t in _TOKEN_RE.findall(cleaned) if _has_latin(t)]
        if not tokens:
            return 0.0

        scores = [self._token_score(t) for t in tokens]
        arabizi_count = sum(1 for s in scores if s >= TOKEN_ARABIZI_THRESHOLD)
        fraction = arabizi_count / len(scores)
        strongest = max(scores)

        confidence = 0.5 * fraction + 0.5 * strongest
        return round(min(confidence, 1.0), 4)

    def transliterate(self, text: str) -> str:
        """Transliterate the Arabizi tokens in ``text`` to Arabic script.

        Tokens that read as plain English (or that are already Arabic
        script) are passed through unchanged, so mixed input stays
        readable while the Arabic content is surfaced for the scorer.
        """
        if not ARABIZI_ENABLED or not text:
            return text

        def _repl(match: "re.Match[str]") -> str:
            token = match.group(0)
            if self._token_score(token) >= TOKEN_ARABIZI_THRESHOLD:
                return transliterate_token(token)
            return token

        return _TOKEN_RE.sub(_repl, text)

    def process(self, text: str) -> ArabiziResult:
        """Full analysis: detect + transliterate in one pass.

        Returns an :class:`ArabiziResult` carrying both the original and
        the transliterated text for the scorer to evaluate.
        """
        original = text if text is not None else ""
        confidence = self.is_arabizi(original)
        transliterated = (
            self.transliterate(original)
            if confidence >= DETECT_THRESHOLD
            else original
        )
        return ArabiziResult(
            is_arabizi=confidence >= DETECT_THRESHOLD,
            confidence=confidence,
            original=original,
            transliterated=transliterated,
        )

    # ─────────────────────────────────────────────────────
    #  Internal scoring
    # ─────────────────────────────────────────────────────

    def _token_score(self, token: str) -> float:
        """Score one token 0.0–1.0 for how Arabizi it looks."""
        t = token.lower()
        letters = [c for c in t if c.isalpha()]

        # Pure-digit / empty token (e.g. "911", "2024") — not a word.
        if not letters:
            return 0.0

        if t in TECH_DENYLIST:
            return 0.0
        if t in ENGLISH_DENYLIST:
            return 0.0

        # Known Arabizi function word (no digits, normal vowels).
        if t in KNOWN_ARABIZI_WORDS:
            return 0.9

        # Arabizi digit glued to a letter — the strongest single signal.
        if any(ch in _ARABIZI_DIGITS for ch in t):
            return 0.9

        has_digraph = any(dg in t for dg in _ARABIZI_DIGRAPHS)
        vowels = sum(1 for c in letters if c in _LATIN_VOWELS)

        # Consonant skeleton (Arabic drops short vowels): "sm", "mkhdr".
        # We require ZERO Latin vowels — a deliberately strict bar, because
        # English words with a single vowel (call, world, the, night) would
        # otherwise flood the detector with false positives. Vowel-carrying
        # Arabizi is caught instead by digits or the known-word list above.
        if vowels == 0 and "'" not in t and 2 <= len(letters) <= 6:
            return 0.6 if has_digraph else 0.5

        return 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Module-level helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _has_latin(token: str) -> bool:
    """True if the token contains at least one Latin letter."""
    return any("a" <= c.lower() <= "z" for c in token)


def transliterate_token(token: str) -> str:
    """Greedily transliterate a single token to Arabic script.

    Longest-match first: two-character keys (digraphs, digit+apostrophe,
    doubled vowels) are tried before single characters, so combos are
    never split apart.  Characters with no mapping are kept verbatim.
    """
    t = token.lower()
    out: List[str] = []
    i = 0
    n = len(t)
    while i < n:
        pair = t[i:i + 2]
        if len(pair) == 2 and pair in TWO_CHAR_MAP:
            out.append(TWO_CHAR_MAP[pair])
            i += 2
            continue
        ch = t[i]
        if ch in ONE_CHAR_MAP:
            out.append(ONE_CHAR_MAP[ch])
        else:
            out.append(ch)
        i += 1
    return "".join(out)


# ── Singleton + thin functional wrappers (match the module API spec) ──

_DEFAULT = ArabiziTransliterator()


def is_arabizi(text: str) -> float:
    """Return a 0.0–1.0 confidence that ``text`` is Arabizi."""
    return _DEFAULT.is_arabizi(text)


def transliterate(text: str) -> str:
    """Transliterate Arabizi tokens in ``text`` to Arabic script."""
    return _DEFAULT.transliterate(text)


def process(text: str) -> ArabiziResult:
    """Detect and transliterate ``text`` in one pass."""
    return _DEFAULT.process(text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Self-test
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("Arabizi Transliterator — self-test\n")

    samples = [
        "9tl",              # kill
        "7rg",              # burn
        "sm",               # poison
        "mkhdr",            # drugs
        "3adi",             # normal
        "ya 7abiibi",       # my love
        "shukran",          # thanks
        "wesh rak sa7bi",   # Maghrebi: how are you my friend
        "hello how are you",# pure English
        "قتل حرق سم",       # already Arabic
    ]
    for s in samples:
        r = process(s)
        print(f"{s!r:22} conf={r.confidence:.2f} "
              f"arabizi={r.is_arabizi!s:5} → {r.transliterated!r}")

    print("\nSelf-test complete.")
