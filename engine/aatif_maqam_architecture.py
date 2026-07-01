"""
aatif_maqam_architecture.py — Maqam Architecture Law Detector (LAW BEH-01)
Field Note #065: The Maqam Architecture Law

Slogan: "Scale = Physical pitch set. Maqam = Living temporal–emotional architecture."
        السلّم = مجموعة أصوات فيزيائية. المقام = بنية زمنية-عاطفية حية.

Operating Law:
    "Tone follows Maqam. Content follows Truth."
    النبرة تتبع المقام الفعّال. المحتوى يتبع الحقيقة — لا المزاج ولا الجمهور.

Core concept:
    Detects the emotional "maqam" (mode) of user input text using a
    diagnostic triad borrowed by analogy from Arabic musical maqam theory:

    1. Jins  (الجنس)  — the structural emotional unit
    2. Aqd   (العقد)  — cadence and transition behaviour
    3. Nisba (النسبة) — the distinctive fingerprint ratio

    IMPORTANT: This is NOT music theory. The Architect (a singer/musician)
    observed that emotional text has "modes" analogous to musical maqams.
    This module operationalises that observation computationally.

This module is B-prime **observational**: it DETECTS the emotional
architecture of user text.  It does NOT decide response tone — it provides
maqam readings so the R equation can adapt style.

It does NOT make safety decisions — that is the S equation's exclusive
jurisdiction.  It does NOT decide whether a request is allowed.

Pipeline position:  after S(d), before prompt composition.
Reads:   user message.
Produces: MaqamReading with triad analysis + B5 style hints.

Novel contribution (FN#065):
    First B-prime module that detects emotional mode architecture using
    a triad model (jins/aqd/nisba), enabling the R equation to adapt
    response style based on the user's emotional modality.

Scientific support:
    - Touma 1971: Maqam as temporal-spatial free structure
    - Marcus 1992/1993: Sayr, qaflah, ghammaz
    - Abu Shumays 2013: Ajnas as governing structural units
    - Yaghmour et al. 2021: EEG signatures per maqam

Constitutional Invariants
-------------------------
Invariant 1: FN#065 never modifies H, θ, S, H_eff, or safety verdicts.
Invariant 2: Maqam detection never lowers harm classification.
Invariant 3: Emotional mode detection is ADVISORY — safety handled by S equation.
Invariant 4: DEFIANCE markers are non-judicial and context-sensitive.
Invariant 5: Gulf Arabic idioms must not be over-escalated.
Invariant 6: The GovernanceEquation remains the only judicial authority.

Authority Contract
------------------
AUTHORITY_LEVEL            = B_PRIME_OBSERVATIONAL
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA           = False
CAN_MODIFY_S               = False
CAN_EMIT_JUDICIAL_DECISION = False
BINDING_CHANNEL            = B5 (Behaviour)

Design consensus: Claude × ChatGPT, 2026-07-01 (FN065_DESIGN_CONSENSUS.md)

License: BSL-1.1 (code) | CC BY 4.0 (field note)
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

try:  # pragma: no cover — import shim for both package and flat layouts
    from aatif_arabic_utils import normalize_arabic
except Exception:  # pragma: no cover
    def normalize_arabic(text: str) -> str:
        """Fallback: strip tashkeel, normalize alef/taa marbouta, lowercase."""
        _TASHKEEL = set(range(0x0610, 0x061B)) | set(range(0x064B, 0x0660)) | {0x0670}
        out = []
        for ch in text:
            if ord(ch) in _TASHKEEL:
                continue
            out.append(ch)
        result = "".join(out)
        result = result.replace("آ", "ا")  # آ → ا
        result = result.replace("أ", "ا")  # أ → ا
        result = result.replace("إ", "ا")  # إ → ا
        result = result.replace("ة", "ه")  # ة → ه
        return result.lower()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Feature Flags  (FN#065 ships OFF by default)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAQAM_ENABLED = False              # master switch
MAQAM_MONITOR_ONLY = True          # when True, detect but do not emit style hints


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Authority Level Declaration (B-prime contract)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AUTHORITY_LEVEL = "B_PRIME_OBSERVATIONAL"
CAN_BLOCK_RUNTIME = False
CAN_MODIFY_H = False
CAN_MODIFY_THETA = False
CAN_MODIFY_S = False
CAN_EMIT_JUDICIAL_DECISION = False
BINDING_CHANNEL = "B5"
SAFETY_DECISION_AUTHORITY = "GOVERNANCE_EQUATION_ONLY"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Constants — activation thresholds
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ACTIVATION_THRESHOLD = 0.25          # below this → fast-path NEUTRAL skip
MIN_MARKER_EVIDENCE = 2             # require at least 2 markers for activation
NISBA_CONFIRMATION_THRESHOLD = 0.35  # weighted ratio for primary maqam
SECONDARY_MIN_CONFIDENCE = 0.30     # secondary must exceed this
SECONDARY_MAX_DISTANCE = 0.25       # primary - secondary must be < this

# Confidence bands (ChatGPT consensus Q7)
BAND_WEAK = (0.25, 0.39)
BAND_MODERATE = (0.40, 0.59)
BAND_STRONG = (0.60, 1.0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MaqamType(Enum):
    """Emotional maqam modes (consensus: 10 modes for v1)."""
    NEUTRAL       = "neutral"         # informational, transactional
    WARMTH        = "warmth"          # دفء — care, empathy, gentleness
    AUTHORITY     = "authority"       # هيبة — command, certainty, expertise
    VULNERABILITY = "vulnerability"   # انكسار — openness, fragility, exposure
    SADNESS       = "sadness"         # حزن — grief, loss, low mood
    PLAYFULNESS   = "playfulness"     # مرح — humour, lightness, energy
    SEEKING       = "seeking"         # بحث — curiosity, questioning, exploration
    GRATITUDE     = "gratitude"       # شكر — appreciation, acknowledgment
    FRUSTRATION   = "frustration"     # إحباط — blocked energy, impatience
    URGENCY       = "urgency"         # عجلة — time pressure, compressed cadence


class CadenceType(Enum):
    """Detected textual cadence/rhythm pattern (aqd)."""
    FLAT          = "flat"            # even, no emotional curve
    ASCENDING     = "ascending"       # building, escalating
    DESCENDING    = "descending"      # winding down, resolving
    STACCATO      = "staccato"        # short bursts, sharp
    FLOWING       = "flowing"         # long, smooth, reflective
    BROKEN        = "broken"          # hesitant, fragmented
    BOUNCY        = "bouncy"          # quick rhythm, energetic


class ConfidenceBand(Enum):
    """Strength of the maqam detection signal."""
    NONE     = "none"
    WEAK     = "weak"        # 0.25–0.39
    MODERATE = "moderate"    # 0.40–0.59
    STRONG   = "strong"      # 0.60+


class MarkerSource(Enum):
    """Provenance of a matched marker (consensus Q6)."""
    EN      = "en"
    MSA_AR  = "msa_ar"
    GULF_AR = "gulf_ar"
    MIXED   = "mixed"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class JinsReading:
    """Structural emotional unit analysis."""
    dominant_pattern: str                # human-readable pattern description
    strength: float                      # 0.0 – 1.0
    markers_found: Tuple[str, ...]       # which jins markers matched


@dataclass(frozen=True)
class AqdReading:
    """Cadence and transition behaviour analysis."""
    cadence_type: CadenceType
    rhythm_score: float                  # 0.0 – 1.0 (how pronounced the cadence)
    sentence_length_variance: float      # normalised variance
    punctuation_density: float           # special punctuation per sentence
    question_ratio: float                # questions / total sentences


@dataclass(frozen=True)
class NisbaReading:
    """Distinctive fingerprint ratio analysis."""
    ratio: float                         # weighted_maqam_score / total_weighted_score
    confirmed: bool                      # ratio >= NISBA_CONFIRMATION_THRESHOLD
    evidence_count: int                  # number of markers contributing
    characteristic_markers: Tuple[str, ...]  # the fingerprint markers found


@dataclass(frozen=True)
class MaqamReading:
    """Complete Maqam Architecture reading.

    This reading is ADVISORY — it feeds the B5 (Behaviour) channel
    exclusively.  It NEVER modifies H, θ, or S.  It NEVER blocks
    runtime.  The S equation remains the sole safety authority.
    """
    # ── Primary detection ──
    detected_maqam: MaqamType
    confidence: float                    # 0.0 – 1.0
    confidence_band: ConfidenceBand

    # ── Triad ──
    jins: JinsReading
    aqd: AqdReading
    nisba: NisbaReading

    # ── Secondary maqam ──
    secondary_maqam: MaqamType           # NEUTRAL if none
    secondary_confidence: float          # 0.0 if none

    # ── Audit trail ──
    markers_found: Tuple[str, ...]       # all matched markers
    evidence_count: int                  # total marker count
    language_detected: str               # "en", "ar", "mixed"
    dialect_hint: str                    # "gulf", "msa", "mixed", "none"
    scores_by_maqam: Dict[str, float]    # full distribution (internal trace)

    # ── B5 advisory ──
    b5_style_hints: Tuple[str, ...]      # advisory hints for R equation
    activated: bool                      # False ⇒ fast-path skip

    # ── B-prime contract ──
    safety_decision_authority: str = SAFETY_DECISION_AUTHORITY
    _isolation_marker: str = "B5_ADVISORY_NOT_FOR_SAFETY"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Marker Constants — Jins (structural emotional markers)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Weight: each marker has a base weight of 1.0 unless overridden.
# High-confidence phrases get weight 2.0.

# ── WARMTH (دفء) ─────────────────────────────────────────────

WARMTH_MARKERS_EN: frozenset = frozenset({
    "thank you so much", "i appreciate", "you're so kind",
    "means a lot", "grateful for you", "bless you",
    "you made my day", "so sweet", "that's lovely",
    "warm regards", "take care", "sending love",
    "i care about", "thinking of you", "you matter",
})

WARMTH_MARKERS_AR: frozenset = frozenset({
    "يعطيك العافية", "الله يسعدك", "ما قصرت",
    "الله يجزاك خير", "من قلبي", "حبيبي",
    "يا قلبي", "ما شاء الله عليك", "الله يوفقك",
    "الله يحفظك", "تسلم", "تسلمين",
    # Gulf dialect
    "يا عمري", "الله يخليك", "ما عليك زود",
    "يا حياتي", "يا روحي",
})

# ── AUTHORITY (هيبة) ──────────────────────────────────────────

AUTHORITY_MARKERS_EN: frozenset = frozenset({
    "you must", "you need to", "it is essential",
    "clearly", "obviously", "without question",
    "the fact is", "undeniably", "i'm certain",
    "absolutely", "definitely", "you should",
    "make sure", "listen", "understand this",
    "the truth is", "let me be clear",
})

AUTHORITY_MARKERS_AR: frozenset = frozenset({
    "لازم", "المفروض", "بالضبط", "أكيد",
    "واضح", "بدون شك", "الحقيقة", "يجب",
    "افهم", "اسمع", "انتبه", "خلي بالك",
    # Gulf dialect
    "ترى", "والله", "أقولك", "صدقني",
    "خلاص كذا", "لا تناقش",
})

# ── VULNERABILITY (انكسار) ────────────────────────────────────

VULNERABILITY_MARKERS_EN: frozenset = frozenset({
    "i'm scared", "im scared", "i'm afraid",
    "i don't know what to do", "i feel lost",
    "i need help", "i'm confused", "i'm overwhelmed",
    "it's too much", "i can't handle",
    "i'm struggling", "i'm trying",
    "please help", "i feel exposed", "i feel raw",
})

VULNERABILITY_MARKERS_AR: frozenset = frozenset({
    "خايف", "خايفة", "ما أدري وش أسوي",
    "ضايع", "ضايعة", "محتاج مساعدة", "محتاجة مساعدة",
    "تعبت", "مو قادر", "مو قادرة",
    "ما أقدر أتحمل", "كثير علي",
    # Gulf dialect
    "والله ما أدري", "وش أسوي", "ضاع علي",
    "ما عندي حيلة", "ما بيدي شي",
})

# ── SADNESS (حزن) — separate from vulnerability (consensus Q1) ─

SADNESS_MARKERS_EN: frozenset = frozenset({
    "i'm sad", "im sad", "i feel sad",
    "i'm heartbroken", "im heartbroken",
    "i miss", "i lost", "grief", "mourning",
    "it hurts", "i'm in pain", "im in pain",
    "i'm grieving", "i feel empty", "i feel hollow",
    "i feel alone", "i'm lonely", "im lonely",
    "it's painful", "sorrow",
})

SADNESS_MARKERS_AR: frozenset = frozenset({
    "حزين", "حزينة", "قلبي يعورني",
    "مشتاق", "مشتاقة", "فقدت", "وحشني",
    "يوجعني", "متألم", "متألمة",
    "أحس بفراغ", "وحيد", "وحيدة",
    # Gulf dialect
    "قلبي انكسر", "محد معي", "ما حولي أحد",
    "يعورني قلبي", "مقهور", "مقهورة",
    "زعلان", "زعلانة",
})

# ── PLAYFULNESS (مرح) ─────────────────────────────────────────

PLAYFULNESS_MARKERS_EN: frozenset = frozenset({
    "haha", "lol", "lmao", "rofl", "just kidding",
    "joking", "funny", "hilarious",
    "that's so fun", "so cool", "awesome",
    "let's go", "yay", "woohoo", "omg",
    "can't stop laughing", "dying of laughter",
})

PLAYFULNESS_MARKERS_AR: frozenset = frozenset({
    "هههههه", "هههه", "ههه",
    "خخخخ", "خخخ", "ياويلي",
    "يا حلو", "ضحكتني", "يموت من الضحك",
    "وناسة", "حلو", "ممتاز",
    # Gulf dialect
    "يا سلام", "يا شين", "والله مضحك",
    "خلني أضحك", "واي", "أموت ضحك",
})

# ── SEEKING (بحث) ─────────────────────────────────────────────

SEEKING_MARKERS_EN: frozenset = frozenset({
    "how do i", "how can i", "what is",
    "can you explain", "i'm wondering", "im wondering",
    "i'm curious", "im curious", "tell me about",
    "what do you think", "what if", "is it possible",
    "i want to learn", "i want to understand",
    "could you help me understand", "why does",
})

SEEKING_MARKERS_AR: frozenset = frozenset({
    "كيف", "ليش", "ليه", "وش يعني",
    "ممكن تشرح", "ممكن تفسر", "أبغى أفهم",
    "عندي سؤال", "وش رايك", "ايش رايك",
    "يعني ايش", "ابغى اعرف",
    # Gulf dialect
    "وش السالفة", "كيف الطريقة", "وش القصة",
    "علمني", "فهمني", "وضح لي",
})

# ── GRATITUDE (شكر) ───────────────────────────────────────────

GRATITUDE_MARKERS_EN: frozenset = frozenset({
    "thank you", "thanks", "much appreciated",
    "i'm grateful", "im grateful", "grateful",
    "you're the best", "so helpful", "great job",
    "well done", "perfect", "exactly what i needed",
    "couldn't have done it without", "that helped a lot",
})

GRATITUDE_MARKERS_AR: frozenset = frozenset({
    "شكرا", "شكراً", "مشكور", "مشكورة",
    "جزاك الله خير", "جزاكم الله خير",
    "يعطيك العافيه", "ما قصرت",
    "الله يعطيك العافية", "بارك الله فيك",
    # Gulf dialect
    "تسلم يمينك", "ما عليك زود", "يسلمو",
    "الله يرضى عليك", "ما قصرتي",
})

# ── FRUSTRATION (إحباط) ──────────────────────────────────────

FRUSTRATION_MARKERS_EN: frozenset = frozenset({
    "this is annoying", "so frustrating", "i'm fed up",
    "im fed up", "sick of this", "tired of this",
    "nothing works", "it's broken", "keeps failing",
    "why isn't this working", "i've tried everything",
    "this makes no sense", "ridiculous",
    "i can't believe", "i cant believe", "unacceptable",
})

FRUSTRATION_MARKERS_AR: frozenset = frozenset({
    "طفشت", "زهقت", "مليت",
    "ما ينفع", "ما يشتغل", "خربان",
    "مو معقول", "يا أخي", "يا اخي",
    "تعبت من هالشي", "ما فيه فايدة",
    # Gulf dialect
    "طفران", "طفرانة", "مقرف",
    "والله ملّيت", "زهقت من هالسوالف",
    "كل شي يخرب", "ما يزبط",
})

# ── URGENCY (عجلة) — consensus Q1: add as own maqam ──────────

URGENCY_MARKERS_EN: frozenset = frozenset({
    "asap", "urgent", "immediately", "right now",
    "hurry", "quickly", "as soon as possible",
    "deadline", "time is running out", "emergency",
    "i need this now", "can't wait", "rush",
    "time-sensitive", "critical", "pressing",
})

URGENCY_MARKERS_AR: frozenset = frozenset({
    "ضروري", "مستعجل", "الحين", "بسرعة",
    "فوري", "عاجل", "ما يستنى",
    "الوقت ضيق", "قبل يفوت الوقت",
    # Gulf dialect
    "يلا بسرعة", "ما عندي وقت", "على طول",
    "لا تتأخر", "بأسرع وقت", "حيل مستعجل",
})

# ── Negation patterns (consensus Q2: negation guards) ─────────

NEGATION_PREFIXES_EN: tuple = (
    "i'm not ", "im not ", "i am not ", "not really ",
    "don't ", "dont ", "do not ", "isn't ", "isnt ",
    "wasn't ", "wasnt ", "no ", "never ",
)

NEGATION_PREFIXES_AR: tuple = (
    "مو ", "مش ", "ما ", "لا ", "ماني ",
    "مب ", "مهو ", "مهي ", "موب ",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Marker Registry — maps MaqamType to (EN markers, AR markers)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MARKER_REGISTRY: Dict[MaqamType, Tuple[frozenset, frozenset]] = {
    MaqamType.WARMTH:        (WARMTH_MARKERS_EN, WARMTH_MARKERS_AR),
    MaqamType.AUTHORITY:     (AUTHORITY_MARKERS_EN, AUTHORITY_MARKERS_AR),
    MaqamType.VULNERABILITY: (VULNERABILITY_MARKERS_EN, VULNERABILITY_MARKERS_AR),
    MaqamType.SADNESS:       (SADNESS_MARKERS_EN, SADNESS_MARKERS_AR),
    MaqamType.PLAYFULNESS:   (PLAYFULNESS_MARKERS_EN, PLAYFULNESS_MARKERS_AR),
    MaqamType.SEEKING:       (SEEKING_MARKERS_EN, SEEKING_MARKERS_AR),
    MaqamType.GRATITUDE:     (GRATITUDE_MARKERS_EN, GRATITUDE_MARKERS_AR),
    MaqamType.FRUSTRATION:   (FRUSTRATION_MARKERS_EN, FRUSTRATION_MARKERS_AR),
    MaqamType.URGENCY:       (URGENCY_MARKERS_EN, URGENCY_MARKERS_AR),
}

# B5 style hint map — what the R equation should do for each maqam
_STYLE_HINTS: Dict[MaqamType, Tuple[str, ...]] = {
    MaqamType.NEUTRAL:       ("maintain_neutral_tone",),
    MaqamType.WARMTH:        ("respond_with_warmth", "match_personal_tone"),
    MaqamType.AUTHORITY:     ("be_precise_and_direct", "match_confident_tone"),
    MaqamType.VULNERABILITY: ("be_gentle_and_patient", "avoid_dismissal"),
    MaqamType.SADNESS:       ("acknowledge_grief", "do_not_rush_positivity"),
    MaqamType.PLAYFULNESS:   ("allow_lightness", "match_energy"),
    MaqamType.SEEKING:       ("be_explanatory", "encourage_exploration"),
    MaqamType.GRATITUDE:     ("acknowledge_warmly", "brief_graceful_response"),
    MaqamType.FRUSTRATION:   ("validate_frustration", "be_solution_oriented"),
    MaqamType.URGENCY:       ("be_concise_and_fast", "prioritise_actionable"),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helper Functions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _detect_language(text: str) -> str:
    """Detect dominant language: 'en', 'ar', or 'mixed'."""
    arabic_chars = sum(1 for ch in text if '؀' <= ch <= 'ۿ' or 'ݐ' <= ch <= 'ݿ')
    latin_chars = sum(1 for ch in text if 'a' <= ch.lower() <= 'z')
    total = arabic_chars + latin_chars
    if total == 0:
        return "en"
    ar_ratio = arabic_chars / total
    if ar_ratio > 0.7:
        return "ar"
    elif ar_ratio < 0.3:
        return "en"
    return "mixed"


def _detect_dialect(text: str, markers_found: List[str]) -> str:
    """Detect dialect hint from matched markers."""
    # Simple heuristic: check if Gulf-specific words appear
    gulf_indicators = {
        "ترى", "وش", "ايش", "يلا", "حيل", "طفران", "طفرانة",
        "هالشي", "هالسوالف", "يزبط", "مالي فايدة", "أقولك",
        "والله", "صدقني", "يا عمري",
    }
    text_lower = normalize_arabic(text)
    gulf_count = sum(1 for g in gulf_indicators if g in text_lower)
    if gulf_count >= 2:
        return "gulf"
    elif gulf_count == 1:
        return "mixed"
    # Check if any Arabic at all
    if any('؀' <= ch <= 'ۿ' for ch in text):
        return "msa"
    return "none"


def _is_negated(text: str, marker: str) -> bool:
    """Check if a marker is preceded by a negation (consensus Q2)."""
    text_lower = text.lower()
    marker_lower = marker.lower()
    idx = text_lower.find(marker_lower)
    if idx < 0:
        return False
    prefix = text_lower[max(0, idx - 20):idx]
    for neg in NEGATION_PREFIXES_EN:
        if prefix.endswith(neg) or prefix.rstrip().endswith(neg.rstrip()):
            return True
    for neg in NEGATION_PREFIXES_AR:
        if neg in prefix:
            return True
    return False


def _compute_cadence(text: str) -> AqdReading:
    """Analyse textual cadence (aqd) from structural features."""
    # Split into sentences (rough: period, ?, !, newline)
    sentences = re.split(r'[.!?؟\n]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return AqdReading(
            cadence_type=CadenceType.FLAT,
            rhythm_score=0.0,
            sentence_length_variance=0.0,
            punctuation_density=0.0,
            question_ratio=0.0,
        )

    # Sentence lengths
    lengths = [len(s.split()) for s in sentences]
    total_words = sum(lengths)
    mean_len = sum(lengths) / len(lengths) if lengths else 0
    variance = (sum((l - mean_len) ** 2 for l in lengths) / len(lengths)) ** 0.5 if lengths else 0
    # Normalise variance (0–1 scale, cap at 10)
    norm_variance = min(variance / 10.0, 1.0)

    # Punctuation density
    special_punct = sum(1 for ch in text if ch in '!?؟…')
    ellipsis_count = text.count('...')
    special_punct += ellipsis_count
    punct_density = special_punct / max(len(sentences), 1)
    norm_punct = min(punct_density / 3.0, 1.0)

    # Question ratio
    question_count = sum(1 for s in text if s in '?؟')
    q_ratio = question_count / max(len(sentences), 1)

    # ── Short-text Aqd dampener (Gemini P0 #2) ──────────────
    # When text is too short to establish cadence reliably,
    # dampen punctuation_density and force FLAT cadence.
    # Prevents a single "!" on a 2-word message from producing
    # an inflated rhythm_score.
    is_short_text = total_words < 15 or len(sentences) == 1
    if is_short_text:
        dampening = min(total_words / 15.0, 1.0)
        norm_punct *= dampening
        norm_variance *= dampening

    # Determine cadence type
    short_threshold = 4  # words
    short_sentences = sum(1 for l in lengths if l <= short_threshold)
    short_ratio = short_sentences / len(lengths) if lengths else 0

    # Short text cannot establish reliable cadence patterns
    if is_short_text:
        cadence = CadenceType.FLAT
    elif q_ratio > 0.5:
        cadence = CadenceType.ASCENDING
    elif short_ratio > 0.6 and norm_punct > 0.3:
        cadence = CadenceType.STACCATO
    elif norm_variance > 0.5:
        cadence = CadenceType.BROKEN
    elif mean_len > 15 and norm_variance < 0.3:
        cadence = CadenceType.FLOWING
    elif '!' in text and text.count('!') >= 2:
        cadence = CadenceType.BOUNCY
    elif len(lengths) >= 3 and lengths[-1] < lengths[0]:
        cadence = CadenceType.DESCENDING
    else:
        cadence = CadenceType.FLAT

    rhythm_score = min((norm_variance + norm_punct + abs(q_ratio - 0.5)) / 2.0, 1.0)

    return AqdReading(
        cadence_type=cadence,
        rhythm_score=rhythm_score,
        sentence_length_variance=round(norm_variance, 3),
        punctuation_density=round(norm_punct, 3),
        question_ratio=round(q_ratio, 3),
    )


def _get_confidence_band(confidence: float) -> ConfidenceBand:
    """Map confidence to band (consensus Q7)."""
    if confidence < ACTIVATION_THRESHOLD:
        return ConfidenceBand.NONE
    elif confidence < 0.40:
        return ConfidenceBand.WEAK
    elif confidence < 0.60:
        return ConfidenceBand.MODERATE
    else:
        return ConfidenceBand.STRONG


def _non_activated_reading() -> MaqamReading:
    """Return a cheap non-activated reading (fast-path skip)."""
    empty_jins = JinsReading(dominant_pattern="none", strength=0.0, markers_found=())
    empty_aqd = AqdReading(
        cadence_type=CadenceType.FLAT, rhythm_score=0.0,
        sentence_length_variance=0.0, punctuation_density=0.0, question_ratio=0.0,
    )
    empty_nisba = NisbaReading(ratio=0.0, confirmed=False, evidence_count=0, characteristic_markers=())
    return MaqamReading(
        detected_maqam=MaqamType.NEUTRAL,
        confidence=0.0,
        confidence_band=ConfidenceBand.NONE,
        jins=empty_jins,
        aqd=empty_aqd,
        nisba=empty_nisba,
        secondary_maqam=MaqamType.NEUTRAL,
        secondary_confidence=0.0,
        markers_found=(),
        evidence_count=0,
        language_detected="en",
        dialect_hint="none",
        scores_by_maqam={},
        b5_style_hints=("maintain_neutral_tone",),
        activated=False,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Main Detection Function
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_maqam(text: str) -> MaqamReading:
    """Detect the emotional maqam (mode) of user input text.

    Returns a MaqamReading with the detected triad (jins/aqd/nisba),
    primary and secondary maqam, confidence, and B5 style hints.

    This function is OBSERVATIONAL ONLY.  It NEVER modifies H, θ, S,
    blocks runtime, or emits judicial decisions.
    """
    if not text or not text.strip():
        return _non_activated_reading()

    # Normalise for matching
    text_norm_en = text.lower()
    text_norm_ar = normalize_arabic(text)

    # ── Phase 1: Jins detection — scan all marker sets ────────
    scores: Dict[MaqamType, float] = {}
    all_markers: List[str] = []
    markers_by_maqam: Dict[MaqamType, List[str]] = {}

    for maqam, (en_markers, ar_markers) in _MARKER_REGISTRY.items():
        matched: List[str] = []
        score = 0.0

        # English markers
        for marker in en_markers:
            if marker in text_norm_en:
                if not _is_negated(text, marker):
                    matched.append(marker)
                    score += 1.0

        # Arabic markers
        for marker in ar_markers:
            marker_norm = normalize_arabic(marker)
            if marker_norm in text_norm_ar:
                if not _is_negated(text_norm_ar, marker_norm):
                    matched.append(marker)
                    score += 1.0

        scores[maqam] = score
        markers_by_maqam[maqam] = matched
        all_markers.extend(matched)

    # ── Phase 2: Check activation threshold ───────────────────
    total_score = sum(scores.values())
    if total_score == 0 or len(all_markers) < MIN_MARKER_EVIDENCE:
        reading = _non_activated_reading()
        # Still compute language/dialect for completeness
        lang = _detect_language(text)
        dialect = _detect_dialect(text, [])
        return MaqamReading(
            detected_maqam=MaqamType.NEUTRAL,
            confidence=0.0,
            confidence_band=ConfidenceBand.NONE,
            jins=reading.jins,
            aqd=_compute_cadence(text),
            nisba=reading.nisba,
            secondary_maqam=MaqamType.NEUTRAL,
            secondary_confidence=0.0,
            markers_found=tuple(all_markers),
            evidence_count=len(all_markers),
            language_detected=lang,
            dialect_hint=dialect,
            scores_by_maqam={m.value: round(s, 3) for m, s in scores.items()},
            b5_style_hints=("maintain_neutral_tone",),
            activated=False,
        )

    # ── Phase 3: Compute nisba ratios ─────────────────────────
    nisba_ratios: Dict[MaqamType, float] = {}
    for maqam, score in scores.items():
        nisba_ratios[maqam] = score / total_score if total_score > 0 else 0.0

    # ── Phase 4: Rank maqams ──────────────────────────────────
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary_maqam = ranked[0][0]
    primary_score = ranked[0][1]
    primary_ratio = nisba_ratios[primary_maqam]

    # Compute confidence: combine ratio and absolute score
    # Confidence = ratio * min(score / 3.0, 1.0) — normalised
    raw_confidence = primary_ratio * min(primary_score / 3.0, 1.0)
    confidence = min(max(raw_confidence, 0.0), 1.0)

    # Check if confidence meets activation threshold
    if confidence < ACTIVATION_THRESHOLD:
        lang = _detect_language(text)
        dialect = _detect_dialect(text, all_markers)
        return MaqamReading(
            detected_maqam=MaqamType.NEUTRAL,
            confidence=round(confidence, 3),
            confidence_band=ConfidenceBand.NONE,
            jins=JinsReading(
                dominant_pattern="weak_signal",
                strength=round(primary_ratio, 3),
                markers_found=tuple(markers_by_maqam.get(primary_maqam, [])),
            ),
            aqd=_compute_cadence(text),
            nisba=NisbaReading(
                ratio=round(primary_ratio, 3),
                confirmed=False,
                evidence_count=len(markers_by_maqam.get(primary_maqam, [])),
                characteristic_markers=tuple(markers_by_maqam.get(primary_maqam, [])),
            ),
            secondary_maqam=MaqamType.NEUTRAL,
            secondary_confidence=0.0,
            markers_found=tuple(all_markers),
            evidence_count=len(all_markers),
            language_detected=lang,
            dialect_hint=dialect,
            scores_by_maqam={m.value: round(s, 3) for m, s in scores.items()},
            b5_style_hints=("maintain_neutral_tone",),
            activated=False,
        )

    # ── Phase 5: Secondary maqam ──────────────────────────────
    secondary_maqam = MaqamType.NEUTRAL
    secondary_confidence = 0.0

    if len(ranked) >= 2 and ranked[1][1] > 0:
        sec_maqam = ranked[1][0]
        sec_score = ranked[1][1]
        sec_ratio = nisba_ratios[sec_maqam]
        sec_conf = sec_ratio * min(sec_score / 3.0, 1.0)
        sec_conf = min(max(sec_conf, 0.0), 1.0)

        if (sec_conf >= SECONDARY_MIN_CONFIDENCE
                and (confidence - sec_conf) < SECONDARY_MAX_DISTANCE):
            secondary_maqam = sec_maqam
            secondary_confidence = round(sec_conf, 3)

    # ── Phase 6: Build triad readings ─────────────────────────
    primary_markers = markers_by_maqam.get(primary_maqam, [])

    jins = JinsReading(
        dominant_pattern=primary_maqam.value,
        strength=round(primary_ratio, 3),
        markers_found=tuple(primary_markers),
    )

    aqd = _compute_cadence(text)

    nisba = NisbaReading(
        ratio=round(primary_ratio, 3),
        confirmed=primary_ratio >= NISBA_CONFIRMATION_THRESHOLD,
        evidence_count=len(primary_markers),
        characteristic_markers=tuple(primary_markers),
    )

    # ── Phase 7: B5 style hints ───────────────────────────────
    band = _get_confidence_band(confidence)
    hints = list(_STYLE_HINTS.get(primary_maqam, ("maintain_neutral_tone",)))
    if band == ConfidenceBand.WEAK:
        hints.append("low_confidence_hint_only")
    if secondary_maqam != MaqamType.NEUTRAL:
        sec_hints = _STYLE_HINTS.get(secondary_maqam, ())
        if sec_hints:
            hints.append(f"secondary_{sec_hints[0]}")

    lang = _detect_language(text)
    dialect = _detect_dialect(text, all_markers)

    return MaqamReading(
        detected_maqam=primary_maqam,
        confidence=round(confidence, 3),
        confidence_band=band,
        jins=jins,
        aqd=aqd,
        nisba=nisba,
        secondary_maqam=secondary_maqam,
        secondary_confidence=secondary_confidence,
        markers_found=tuple(all_markers),
        evidence_count=len(all_markers),
        language_detected=lang,
        dialect_hint=dialect,
        scores_by_maqam={m.value: round(s, 3) for m, s in scores.items()},
        b5_style_hints=tuple(hints),
        activated=True,
    )
