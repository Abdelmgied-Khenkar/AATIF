"""
aatif_cultural_opacity.py — Cultural Semantic Opacity Detector
Field Note #074: Cultural Semantic Opacity

Slogan: "The model reads the words. The culture reads the weight."
        النموذج يقرأ الكلمات. الثقافة تقرأ الثقل.

Core concept:
    Arabic grammatical constructions carry cultural meaning that
    embedding models miss.  "البيت ومصاريفه" is a living entity
    (family + marriage + children + responsibilities + costs).
    "مصاريف البيت" is material only (just financial expenses).
    The model sees both as similar (~same words), but culturally
    the first is MUCH heavier because the possessive pronoun (ه)
    turns "البيت" into a living entity.

This module is B-prime **observational**: it DETECTS and TAGS
cultural opacity patterns in Arabic text.  It does NOT modify
scores — it enriches the prompt with advisory context.

It does NOT make safety decisions — that is the S equation's
exclusive jurisdiction.

Pipeline position:  after S(d), before prompt composition (POST_S).
Reads:   user message.
Produces: CulturalReading with pattern detection + weight advisory.

Three-level opacity scale:
    Word level:       "نفسي" vs "عايز" — partially readable
    Figurative level: "أموت فيك" = love — readable after anchors
    Cultural construct: "البيت ومصاريفه" vs "مصاريف البيت" — missed

Novel contribution (FN#074):
    First module that detects when Arabic grammar carries cultural
    weight that embedding models systematically miss — possessive
    entity patterns, reversed idafa, pronoun weight, and holistic
    life expressions.

Constitutional Invariants
-------------------------
Invariant 1: FN#074 never modifies H, θ, S, H_eff, or safety verdicts.
Invariant 2: Cultural weight delta is ADVISORY only (max 0.3).
Invariant 3: The GovernanceEquation remains the only judicial authority.
Invariant 4: English text → no patterns detected (Arabic-specific).
Invariant 5: Deterministic — same input always gives same output.

Authority Contract
------------------
AUTHORITY_LEVEL            = B_PRIME_OBSERVATIONAL
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA           = False
CAN_MODIFY_S               = False
CAN_EMIT_JUDICIAL_DECISION = False
BINDING_CHANNEL            = B5 (Behaviour)

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

# ── Try to import shared text utilities; fall back to local copy ──
try:
    from aatif_text import normalize_arabic, arabic_ratio, is_arabic
except ImportError:
    # Standalone mode — minimal implementations
    _TASHKEEL_RE = re.compile(
        "[" "ؐ-ؚ" "ً-ٟ" "ٰ" "ۖ-ۜ" "۟-ۤ" "ۧ-ۨ" "۪-ۭ" "]"
    )
    _ALEF_VARIANTS = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"}
    _TAA_MARBUTA = {"ة": "ه"}
    _HAMZA_ON_CARRIER = {"ؤ": "و", "ئ": "ي"}
    _ALEF_MAQSURA = {"ى": "ي"}
    _ARABIC_CHAR_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]")

    def normalize_arabic(text: str) -> str:
        text = _TASHKEEL_RE.sub("", text)
        text = text.replace("ـ", "")
        for src, dst in _ALEF_VARIANTS.items():
            text = text.replace(src, dst)
        for src, dst in _TAA_MARBUTA.items():
            text = text.replace(src, dst)
        for src, dst in _HAMZA_ON_CARRIER.items():
            text = text.replace(src, dst)
        for src, dst in _ALEF_MAQSURA.items():
            text = text.replace(src, dst)
        return text.lower()

    def arabic_ratio(text: str) -> float:
        if not text:
            return 0.0
        ac = len(_ARABIC_CHAR_RE.findall(text))
        total = len(text.replace(" ", ""))
        return ac / total if total else 0.0

    def is_arabic(text: str, threshold: float = 0.5) -> bool:
        return arabic_ratio(text) >= threshold


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Feature Flags  (FN#074 ships ON by default)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CULTURAL_OPACITY_ENABLED = True       # master switch
_MIN_TEXT_LENGTH = 3                  # sparse activation threshold


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class OpacityLevel(Enum):
    """Three-level opacity scale from FN#074."""
    NONE               = "none"
    WORD               = "word"                 # e.g. "نفسي" vs "عايز"
    FIGURATIVE         = "figurative"           # e.g. "أموت فيك" = love
    CULTURAL_CONSTRUCT = "cultural_construct"   # e.g. "البيت ومصاريفه"


class PatternType(Enum):
    """Types of cultural patterns detected."""
    POSSESSIVE_ENTITY   = "possessive_entity"    # "X و Y-ه"
    IDAFA_REVERSAL      = "idafa_reversal"       # "مصاريف البيت" (lighter form)
    PRONOUN_WEIGHT      = "pronoun_weight"       # "نفسي" vs "عايز"
    HOLISTIC_LIFE       = "holistic_life"        # "كل شي" / "ما بقالي شي"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class CulturalPattern:
    """A cultural construct that carries meaning beyond words.

    Each detected pattern is one instance of cultural opacity —
    a place where the embedding model misses weight that a native
    speaker would feel.
    """
    pattern_id: str                     # unique identifier for this pattern
    pattern_type: PatternType           # which category
    description: str                    # what this pattern culturally means
    weight_adjustment: float            # 0.0 to 0.3 advisory adjustment
    matched_text: str                   # the actual text that matched
    examples: Tuple[str, ...]           # example phrases for reference


@dataclass(frozen=True)
class CulturalReading:
    """Complete cultural opacity analysis reading.

    This reading is ADVISORY — it feeds the B5 (Behaviour) channel
    exclusively.  It NEVER modifies H, θ, or S.  It NEVER blocks
    runtime.  The S equation remains the sole safety authority.
    """
    # ── Detection results ──
    patterns_detected: Tuple[CulturalPattern, ...]
    cultural_weight_delta: float        # total advisory adjustment (capped at 0.3)
    opacity_level: OpacityLevel         # highest level detected
    explanation: str                    # why this reading matters
    confidence: float                   # 0.0 – 1.0

    # ── B5 advisory ──
    activated: bool                     # False ⇒ no patterns found
    evidence: Tuple[str, ...]           # audit trail entries

    # ── Isolation marker (B-prime contract) ──
    _isolation_marker: str = "B5_ADVISORY_NOT_FOR_SAFETY"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Pattern Definitions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Arabic letter class for boundary matching
_AR_LETTER = r"ء-يٮ-ٯٱ-ۓ"

# ── Possessive Entity Pattern ──
# "البيت ومصاريفه" — noun + و + noun + possessive pronoun
# The possessive pronoun turns the whole expression into a living entity.
# Possessive pronoun suffixes: ه (his/its), ها (her/its), هم (their-m),
# هن (their-f), ي (my), نا (our), ك (your-m), كم (your-pl)
_POSSESSIVE_SUFFIXES = (
    "ه", "ها", "هم", "هن",
)

# Pre-compiled regex for the possessive entity pattern:
# (Arabic-word) + space + و + space + (Arabic-word + possessive-suffix)
# We look for: [arabic]+ و [arabic]+[possessive]
_POSSESSIVE_ENTITY_RE = re.compile(
    r"([" + _AR_LETTER + r"]{2,})"      # noun 1 (at least 2 Arabic letters)
    r"\s+و\s*"                           # و (and)
    r"([" + _AR_LETTER + r"]{2,}"        # noun 2 (at least 2 Arabic letters)
    r"(?:" + "|".join(_POSSESSIVE_SUFFIXES) + r"))"  # ending with possessive suffix
)

# ── Pronoun Weight Markers ──
# "نفسي" (my soul/self) = deeper emotional involvement
# vs "عايز" / "أبغى" (want) = more distant/functional
PRONOUN_WEIGHT_HEAVY: frozenset = frozenset({
    "نفسي",       # nafsi — my soul/self, deep personal desire
    "روحي",       # ruhi — my spirit
    "قلبي",       # qalbi — my heart
})

PRONOUN_WEIGHT_LIGHT: frozenset = frozenset({
    "عايز",       # aayiz — want (Egyptian)
    "ابي",         # abi — want (Gulf)
    "ابغى",       # abgha — want (Gulf)
    "بدي",         # biddi — want (Levantine)
    "عاوز",       # aawiz — want (Egyptian variant)
    "اريد",       # ureed — want (MSA)
    "اود",         # awaddu — would like (MSA)
})

# ── Holistic Life Expression Markers ──
# "كل شي" / "كل حاجة" — "everything" (implies totality of life)
# "ما بقالي شي" — "nothing left for me" (implies complete depletion)
HOLISTIC_MARKERS: frozenset = frozenset({
    "كل شي",           # kul shay — everything (Gulf)
    "كل شيء",         # kul shay' — everything (MSA)
    "كل حاجه",       # kul haga — everything (Egyptian)
    "كل حاجة",       # kul haga — everything (Egyptian with taa)
    "ما بقالي شي",  # ma ba'ali shay — nothing left for me
    "ما بقالي شيء", # ma ba'ali shay' — nothing left (MSA)
    "ما عاد فيه شي", # ma aad fih shay — nothing left anymore
    "ما بقي لي شي", # ma baqi li shay — nothing left for me
    "ما بقى لي شيء", # ma baqa li shay' — nothing left (MSA)
    "ولا شي",         # wala shay — nothing at all
    "ولا شيء",       # wala shay' — nothing at all (MSA)
})

# Holistic verbs that amplify when combined with holistic markers
HOLISTIC_VERBS: frozenset = frozenset({
    "زهقت",       # zahaqt — fed up
    "تعبت",       # ta'ibt — tired/exhausted
    "مليت",       # maleet — bored/fed up
    "سئمت",       # sa'imt — sick of
    "طفشت",       # tafasht — fed up (Gulf)
    "زهقانه",    # zahqana-f
    "زهقان",      # zahqan-m
    "تعبانه",    # ta'bana-f
    "تعبان",      # ta'ban-m
})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Constants
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAX_CULTURAL_WEIGHT_DELTA = 0.3

# Tashkeel regex (for partial normalization that preserves taa marbuta)
_TASHKEEL_STRIP_RE = re.compile(
    "[" "ؐ-ؚ" "ً-ٟ" "ٰ" "ۖ-ۜ" "۟-ۤ" "ۧ-ۨ" "۪-ۭ" "]"
)
_ALEF_NORM = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"}


def _normalize_preserve_taa_marbuta(text: str) -> str:
    """Normalize Arabic text but keep ة as ة (not → ه).

    For possessive entity detection we must NOT convert taa marbuta
    to haa, because that creates false positives: "السيارة" → "السياره"
    would incorrectly match the possessive suffix "ه".
    """
    text = _TASHKEEL_STRIP_RE.sub("", text)
    text = text.replace("ـ", "")
    for src, dst in _ALEF_NORM.items():
        text = text.replace(src, dst)
    # Deliberately NOT normalizing ة → ه
    # Deliberately NOT normalizing ؤ → و or ئ → ي (not needed here)
    return text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Detector
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CulturalOpacityDetector:
    """
    Detects cultural semantic opacity patterns in Arabic text.

    The detector identifies grammatical constructions that carry
    cultural weight invisible to embedding models:

    1. Possessive entity:  "البيت ومصاريفه" — the noun becomes
       a living entity through the possessive pronoun.
    2. Reversed idafa:     "مصاريف البيت" — the lighter, material-only
       form (detected but NOT flagged as culturally heavy).
    3. Pronoun weight:     "نفسي" carries deeper personal involvement
       than "عايز" (want).
    4. Holistic life:      "زهقت من كل شي" — totality expressions
       amplify emotional severity.

    All detection is template/regex-based — no LLM calls, no embeddings.
    Deterministic: same input always gives same output.
    """

    # ── Authority Contract (7 constants) ──
    AUTHORITY_LEVEL            = "B_PRIME_OBSERVATIONAL"
    CAN_BLOCK_RUNTIME          = False
    CAN_MODIFY_H               = False
    CAN_MODIFY_THETA           = False
    CAN_MODIFY_S               = False
    CAN_EMIT_JUDICIAL_DECISION = False
    BINDING_CHANNEL            = "B5"

    # ── Isolation Contract ──
    ISOLATION_MARKER  = "B5_ADVISORY_NOT_FOR_SAFETY"
    ISOLATION_TARGETS = frozenset({"B5"})
    ISOLATION_CONTRACT = (
        "FN#074 Cultural Semantic Opacity is B-prime observational. "
        "It detects cultural weight patterns that embedding models miss. "
        "It NEVER modifies H, θ, S, or safety verdicts. "
        "It NEVER blocks runtime. "
        "cultural_weight_delta is ADVISORY ONLY — capped at 0.3. "
        "The GovernanceEquation remains the only judicial authority."
    )

    def __init__(self):
        """Initialize the Cultural Opacity Detector."""
        pass  # stateless — all detection is per-call

    def analyze(self, text: str) -> CulturalReading:
        """Analyze text for cultural semantic opacity patterns.

        Args:
            text: User message (any language).

        Returns:
            CulturalReading with detected patterns and advisory weight.
        """
        # ── Feature flag check ──
        if not CULTURAL_OPACITY_ENABLED:
            return self._inactive_reading()

        # ── Empty / short text → fast path ──
        if not text or len(text.strip()) < _MIN_TEXT_LENGTH:
            return self._inactive_reading()

        # ── Non-Arabic text → no patterns ──
        if not is_arabic(text, threshold=0.3):
            return self._inactive_reading()

        # ── Normalize for matching ──
        norm = normalize_arabic(text)

        # ── Detect all pattern types ──
        patterns: List[CulturalPattern] = []
        evidence: List[str] = []

        # 1. Possessive entity patterns
        pe_patterns = self._detect_possessive_entity(text, norm)
        patterns.extend(pe_patterns)
        for p in pe_patterns:
            evidence.append(
                f"POSSESSIVE_ENTITY: '{p.matched_text}' — {p.description}"
            )

        # 2. Pronoun weight patterns
        pw_patterns = self._detect_pronoun_weight(text, norm)
        patterns.extend(pw_patterns)
        for p in pw_patterns:
            evidence.append(
                f"PRONOUN_WEIGHT: '{p.matched_text}' — {p.description}"
            )

        # 3. Holistic life expression patterns
        hl_patterns = self._detect_holistic_life(text, norm)
        patterns.extend(hl_patterns)
        for p in hl_patterns:
            evidence.append(
                f"HOLISTIC_LIFE: '{p.matched_text}' — {p.description}"
            )

        # ── Calculate combined weight ──
        total_weight = sum(p.weight_adjustment for p in patterns)
        total_weight = min(total_weight, MAX_CULTURAL_WEIGHT_DELTA)

        # ── Determine opacity level ──
        opacity_level = self._determine_opacity_level(patterns)

        # ── Compute confidence ──
        confidence = self._compute_confidence(patterns)

        # ── Build explanation ──
        explanation = self._build_explanation(patterns, total_weight)

        activated = len(patterns) > 0

        return CulturalReading(
            patterns_detected=tuple(patterns),
            cultural_weight_delta=round(total_weight, 4),
            opacity_level=opacity_level,
            explanation=explanation,
            confidence=round(confidence, 4),
            activated=activated,
            evidence=tuple(evidence),
        )

    # ── Pattern detection methods ──

    def _detect_possessive_entity(
        self, raw_text: str, norm_text: str,
    ) -> List[CulturalPattern]:
        """Detect possessive entity patterns: noun + و + noun+possessive.

        "البيت ومصاريفه" → the house is a living entity with its own costs.

        IMPORTANT: We use _normalize_preserve_taa_marbuta here instead
        of full normalize_arabic, because converting ة → ه would create
        false positives (e.g. "السيارة" → "السياره" matching suffix "ه").
        """
        patterns: List[CulturalPattern] = []

        # Use taa-marbuta-preserving normalization to avoid false positives
        pe_norm = _normalize_preserve_taa_marbuta(raw_text)

        for match in _POSSESSIVE_ENTITY_RE.finditer(pe_norm):
            noun1 = match.group(1)
            noun2_with_pron = match.group(2)
            matched_span = match.group(0)

            patterns.append(CulturalPattern(
                pattern_id=f"pe_{noun1}_{noun2_with_pron}",
                pattern_type=PatternType.POSSESSIVE_ENTITY,
                description=(
                    f"'{matched_span}' — the noun becomes a living entity "
                    f"through the possessive pronoun. Culturally heavier "
                    f"than the standard idafa (مضاف إليه) form."
                ),
                weight_adjustment=0.15,
                matched_text=matched_span,
                examples=(
                    "البيت ومصاريفه",
                    "الشغل وضغوطه",
                    "الحياة وهمومها",
                ),
            ))

        return patterns

    def _detect_pronoun_weight(
        self, raw_text: str, norm_text: str,
    ) -> List[CulturalPattern]:
        """Detect pronoun weight patterns: "نفسي" vs "عايز".

        "نفسي" = reflexive, deeper personal involvement.
        "عايز" = functional want, more distant.
        """
        patterns: List[CulturalPattern] = []

        for marker in PRONOUN_WEIGHT_HEAVY:
            marker_norm = normalize_arabic(marker)
            # Use word-boundary-aware search
            pat = rf"(?<![{_AR_LETTER}]){re.escape(marker_norm)}(?![{_AR_LETTER}])"
            if re.search(pat, norm_text):
                patterns.append(CulturalPattern(
                    pattern_id=f"pw_{marker_norm}",
                    pattern_type=PatternType.PRONOUN_WEIGHT,
                    description=(
                        f"'{marker}' — reflexive/personal pronoun carrying "
                        f"deeper emotional involvement than functional want "
                        f"words (عايز/أبغى)."
                    ),
                    weight_adjustment=0.10,
                    matched_text=marker,
                    examples=("نفسي أرتاح", "روحي تعبانه", "قلبي يوجعني"),
                ))

        return patterns

    def _detect_holistic_life(
        self, raw_text: str, norm_text: str,
    ) -> List[CulturalPattern]:
        """Detect holistic life expression patterns.

        "كل شي" / "ما بقالي شي" — totality implies suffering
        across ALL of life, amplifying severity.
        """
        patterns: List[CulturalPattern] = []

        for marker in HOLISTIC_MARKERS:
            marker_norm = normalize_arabic(marker)
            if marker_norm in norm_text:
                # Check if a holistic verb is also present for amplification
                has_verb = False
                for verb in HOLISTIC_VERBS:
                    verb_norm = normalize_arabic(verb)
                    if verb_norm in norm_text:
                        has_verb = True
                        break

                weight = 0.15 if has_verb else 0.10

                patterns.append(CulturalPattern(
                    pattern_id=f"hl_{marker_norm[:10]}",
                    pattern_type=PatternType.HOLISTIC_LIFE,
                    description=(
                        f"'{marker}' — totality expression implying "
                        f"suffering across all of life, not a single domain."
                        + (" Amplified by distress verb." if has_verb else "")
                    ),
                    weight_adjustment=weight,
                    matched_text=marker,
                    examples=(
                        "زهقت من كل شي",
                        "ما بقالي شي",
                        "تعبت من كل حاجة",
                    ),
                ))
                # Only match the first holistic marker to avoid double-counting
                # overlapping phrases (e.g. "كل شي" inside "كل شيء")
                break

        return patterns

    # ── Helpers ──

    def _determine_opacity_level(
        self, patterns: List[CulturalPattern],
    ) -> OpacityLevel:
        """Determine the highest opacity level from detected patterns."""
        if not patterns:
            return OpacityLevel.NONE

        types = {p.pattern_type for p in patterns}

        if PatternType.POSSESSIVE_ENTITY in types:
            return OpacityLevel.CULTURAL_CONSTRUCT
        if PatternType.HOLISTIC_LIFE in types:
            return OpacityLevel.CULTURAL_CONSTRUCT
        if PatternType.PRONOUN_WEIGHT in types:
            return OpacityLevel.WORD

        return OpacityLevel.NONE

    def _compute_confidence(
        self, patterns: List[CulturalPattern],
    ) -> float:
        """Compute detection confidence based on pattern count and type."""
        if not patterns:
            return 0.0

        # Base confidence from pattern count
        base = min(0.5 + 0.15 * len(patterns), 1.0)

        # Boost for cultural_construct-level patterns
        types = {p.pattern_type for p in patterns}
        if PatternType.POSSESSIVE_ENTITY in types:
            base = min(base + 0.2, 1.0)

        return base

    def _build_explanation(
        self, patterns: List[CulturalPattern], total_weight: float,
    ) -> str:
        """Build human-readable explanation of the cultural reading."""
        if not patterns:
            return ""

        types = {p.pattern_type for p in patterns}
        parts: List[str] = []

        if PatternType.POSSESSIVE_ENTITY in types:
            parts.append(
                "possessive entity pattern makes the expression "
                "culturally heavier than the model perceives"
            )
        if PatternType.PRONOUN_WEIGHT in types:
            parts.append(
                "reflexive pronoun carries deeper personal involvement "
                "than functional want-words"
            )
        if PatternType.HOLISTIC_LIFE in types:
            parts.append(
                "totality expression implies suffering across all of life"
            )

        explanation = (
            f"Cultural opacity detected ({len(patterns)} pattern(s)): "
            + "; ".join(parts) + ". "
            f"Advisory weight adjustment: +{total_weight:.2f}."
        )

        return explanation

    def _inactive_reading(self) -> CulturalReading:
        """Return an inactive (no-op) reading."""
        return CulturalReading(
            patterns_detected=(),
            cultural_weight_delta=0.0,
            opacity_level=OpacityLevel.NONE,
            explanation="",
            confidence=0.0,
            activated=False,
            evidence=(),
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Self-test
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("FN#074 Cultural Semantic Opacity — self-test")
    print()

    detector = CulturalOpacityDetector()

    # The field note's original test pair
    heavy = "زهقت من البيت و مصاريفه وعايز بكرا ما يجيش"
    light = "زهقت من مصاريف البيت"

    r1 = detector.analyze(heavy)
    r2 = detector.analyze(light)

    print(f"Heavy: '{heavy}'")
    print(f"  activated={r1.activated}, delta={r1.cultural_weight_delta}")
    print(f"  patterns={len(r1.patterns_detected)}, level={r1.opacity_level.value}")
    print()
    print(f"Light: '{light}'")
    print(f"  activated={r2.activated}, delta={r2.cultural_weight_delta}")
    print(f"  patterns={len(r2.patterns_detected)}, level={r2.opacity_level.value}")
    print()

    # Pronoun weight test
    nafsi = "نفسي أرتاح من كل شي"
    r3 = detector.analyze(nafsi)
    print(f"Pronoun: '{nafsi}'")
    print(f"  activated={r3.activated}, delta={r3.cultural_weight_delta}")
    print(f"  patterns={len(r3.patterns_detected)}")
    print()

    print("Self-test complete.")
