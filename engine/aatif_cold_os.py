"""
aatif_cold_os.py — Tri-Engine Decision Protocol (COLD-OS)
Field Note #072: The Tri-Engine Decision Protocol

Three internal voices work before every output:

    Ideal (المثالي)  — "What is the absolute right?"      → conscience
    Real  (الواقعي)  — "What is humanly possible + merciful?" → **announced voice**
    COLD            — "What do the raw numbers say?"      → internal analysis only

Rule: Real speaks.  Ideal teaches.  COLD sets boundaries.
All three work *before* speech — never after.

This module is B-prime **observational**: it analyses the user's message
through the three-voice lens and produces *framing guidance* for the
response composer (R equation / response shaper).  It does NOT make
safety decisions — that is the S equation's exclusive jurisdiction.

Pipeline position:  after S(d), before prompt composition.
Reads:   user message, S decision, H score, domain.
Produces: ColdOSReading with voice analysis + framing strategy.

Novel contribution (FN#072):
    First architecture that splits the internal decision on *content of
    intent* (ideal / realistic / cold-numerical) rather than on processing
    speed (Stanovich) or ethical theory (Levine et al.).

Authority Contract
------------------
AUTHORITY_LEVEL            = B_PRIME_OBSERVATIONAL
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA            = False
CAN_MODIFY_S               = False
CAN_EMIT_JUDICIAL_DECISION = False
BINDING_CHANNEL            = B5 (Behaviour)

License: BSL-1.1 (code) | CC BY 4.0 (field note)
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DecisionContext(Enum):
    """Type of decision the user is navigating."""
    MORAL      = "moral"
    PERSONAL   = "personal"
    PRACTICAL  = "practical"
    MEDICAL    = "medical"
    SPIRITUAL  = "spiritual"
    FINANCIAL  = "financial"
    GENERAL    = "general"


class TensionType(Enum):
    """Where the three voices disagree."""
    NONE           = "none"
    IDEAL_VS_REAL  = "ideal_vs_real"
    IDEAL_VS_COLD  = "ideal_vs_cold"
    REAL_VS_COLD   = "real_vs_cold"
    THREE_WAY      = "three_way"


class FramingStrategy(Enum):
    """How the response should be framed based on voice analysis."""
    REAL_LEADS_IDEAL_TEACHES = "real_leads_ideal_teaches"
    IDEAL_LEADS_REAL_SOFTENS = "ideal_leads_real_softens"
    COLD_INFORMS_REAL_SPEAKS = "cold_informs_real_speaks"
    UNIFIED                  = "unified"
    DEFER_TO_CLARIFICATION   = "defer_to_clarification"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class VoiceSignal:
    """Signal strength for one of the three voices."""
    voice: str                    # "ideal", "real", "cold"
    strength: float               # 0.0 – 1.0
    markers_found: Tuple[str, ...]


@dataclass(frozen=True)
class TensionReading:
    """Analysis of tension between the three voices."""
    tension_type: TensionType
    tension_level: float          # 0.0 (agreement) – 1.0 (max conflict)
    description: str


@dataclass(frozen=True)
class ColdOSReading:
    """Complete Tri-Engine analysis of a decision context."""
    decision_context: DecisionContext
    ideal_signal: VoiceSignal
    real_signal: VoiceSignal
    cold_signal: VoiceSignal
    tension: TensionReading
    framing_strategy: FramingStrategy
    recommendations: Tuple[str, ...]
    evidence: Tuple[str, ...]
    activated: bool               # False ⇒ fast-path skip
    _isolation_marker: str = "B5_ADVISORY_NOT_FOR_SAFETY"
    lbh_interaction_note: str = ""  # P0-C: warns when strategy may conflict with LBH


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Marker Constants
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── Ideal voice: principled / moral / duty-based ──────────────
IDEAL_MARKERS_EN: frozenset = frozenset({
    "should i", "ought to", "right thing", "duty", "obligation",
    "principle", "morally", "ethically", "justice", "virtue",
    "integrity", "conscience", "ethical dilemma", "right or wrong",
    "supposed to", "the right", "moral duty", "responsible thing",
})

IDEAL_MARKERS_AR: frozenset = frozenset({
    "المفروض", "الصح", "الواجب", "الحق", "العدل",
    "الأخلاق", "المبدأ", "الضمير", "يجب", "ينبغي",
    "حرام", "حلال", "صح ولا غلط", "من حقي", "واجبي",
    "لازم", "الصح إني",
})

# ── Real voice: circumstantial / mercy / practical reality ────
REAL_MARKERS_EN: frozenset = frozenset({
    "but my situation", "circumstances", "reality", "practical",
    "afford", "family", "responsibility", "difficult", "struggle",
    "trying", "hard to", "unable", "real life", "in practice",
    "stuck", "trapped", "no choice", "what can i do",
    "honestly", "truth is", "can't just",
})

REAL_MARKERS_AR: frozenset = frozenset({
    "ظروفي", "لكن", "الواقع", "صعب", "ما أقدر",
    "عائلتي", "مسؤولية", "المشكلة", "الحقيقة", "تعبت",
    "مو سهل", "ما عندي خيار", "ايش أسوي", "محتار",
    "مو قادر", "ما أعرف", "بس", "تحت ضغط", "مضغوط",
})

# ── COLD voice: data / evidence / numerical ───────────────────
COLD_MARKERS_EN: frozenset = frozenset({
    "statistics", "data", "evidence", "probability", "percentage",
    "research shows", "studies show", "numbers", "risk", "chance",
    "rate", "analysis", "survey", "according to", "on average",
    "likelihood", "outcome", "success rate", "failure rate",
})

COLD_MARKERS_AR: frozenset = frozenset({
    "إحصائيات", "بيانات", "أرقام", "نسبة", "احتمال",
    "دراسات", "أبحاث", "خطر", "نسبة نجاح", "حسب الأرقام",
    "حقائق", "معدل", "تحليل", "نتائج",
})

# ── Decision-context markers ──────────────────────────────────

CONTEXT_MORAL_EN: frozenset = frozenset({
    "right or wrong", "ethical", "moral", "dilemma", "conscience",
    "sin", "guilt", "forgive", "betray", "honest",
})
CONTEXT_MORAL_AR: frozenset = frozenset({
    "حلال", "حرام", "ذنب", "حق", "باطل",
    "ضمير", "مغفرة", "توبة", "خيانة", "أمانة",
})

CONTEXT_PERSONAL_EN: frozenset = frozenset({
    "my life", "relationship", "career", "marriage", "divorce",
    "partner", "decision", "choice", "future", "quit",
    "leave", "stay", "move", "break up",
})
CONTEXT_PERSONAL_AR: frozenset = frozenset({
    "حياتي", "علاقتي", "شغلي", "زواج", "طلاق",
    "شريك", "قرار", "خيار", "مستقبلي",
    "وظيفة", "أترك", "أبقى", "أغير",
})

CONTEXT_MEDICAL_EN: frozenset = frozenset({
    "health", "diagnosis", "treatment", "medication", "doctor",
    "symptom", "condition", "therapy", "surgery", "prognosis",
})
CONTEXT_MEDICAL_AR: frozenset = frozenset({
    "صحتي", "مرض", "علاج", "دواء", "دكتور",
    "أعراض", "حالة", "عملية", "تشخيص",
})

CONTEXT_SPIRITUAL_EN: frozenset = frozenset({
    "god", "faith", "prayer", "purpose", "meaning",
    "soul", "spirit", "believe", "divine", "worship",
})
CONTEXT_SPIRITUAL_AR: frozenset = frozenset({
    "الله", "إيمان", "صلاة", "معنى", "روح",
    "قدر", "دعاء", "تقوى", "دين", "آخرة",
})

CONTEXT_FINANCIAL_EN: frozenset = frozenset({
    "money", "investment", "salary", "budget", "debt",
    "loan", "income", "expense", "saving", "financial",
    "profit", "loss",
})
CONTEXT_FINANCIAL_AR: frozenset = frozenset({
    "فلوس", "استثمار", "راتب", "ميزانية", "دين",
    "قرض", "دخل", "مصروف", "ادخار", "مالي",
    "ربح", "خسارة",
})

# ── Practical decision context (P0-B: was unreachable) ───────
CONTEXT_PRACTICAL_EN: frozenset = frozenset({
    "how to", "steps", "plan", "method", "strategy",
    "approach", "way to", "solution", "fix", "optimize",
    "schedule", "organize", "manage", "process", "build",
})
CONTEXT_PRACTICAL_AR: frozenset = frozenset({
    "كيف", "خطوات", "طريقة", "حل", "خطة",
    "عملي", "أنظم", "أرتب", "أحسن", "أبني",
})

# All context-marker pairs for iteration
_CONTEXT_MARKER_MAP = {
    DecisionContext.MORAL:     (CONTEXT_MORAL_EN,     CONTEXT_MORAL_AR),
    DecisionContext.PERSONAL:  (CONTEXT_PERSONAL_EN,  CONTEXT_PERSONAL_AR),
    DecisionContext.PRACTICAL: (CONTEXT_PRACTICAL_EN, CONTEXT_PRACTICAL_AR),
    DecisionContext.MEDICAL:   (CONTEXT_MEDICAL_EN,   CONTEXT_MEDICAL_AR),
    DecisionContext.SPIRITUAL: (CONTEXT_SPIRITUAL_EN, CONTEXT_SPIRITUAL_AR),
    DecisionContext.FINANCIAL: (CONTEXT_FINANCIAL_EN, CONTEXT_FINANCIAL_AR),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Arabic Normalization (P0-E/F)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _normalize_arabic(text: str) -> str:
    """Normalize Arabic text: strip diacritics, normalize alef, strip tatweel."""
    # Strip tashkeel (diacritics)
    result = unicodedata.normalize("NFD", text)
    result = "".join(
        c for c in result
        if unicodedata.category(c) != "Mn"  # non-spacing marks = diacritics
    )
    # Normalize alef variants: أ إ آ → ا
    result = result.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    # Strip tatweel
    result = result.replace("ـ", "")
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Word-Boundary Matching (P0-E)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _compile_en_patterns(markers: frozenset) -> list:
    """Pre-compile English markers with word boundaries."""
    return [re.compile(r"\b" + re.escape(m) + r"\b", re.IGNORECASE) for m in markers]


def _match_en_markers(text: str, patterns: list, markers: frozenset) -> list:
    """Match English markers with word-boundary regex."""
    found = []
    markers_list = sorted(markers)
    for pattern, marker in zip(patterns, markers_list):
        if pattern.search(text):
            found.append(marker)
    return found


def _match_ar_markers(text: str, markers: frozenset) -> list:
    """Match Arabic markers allowing common Arabic affixes.

    Arabic has prefixes (ال، و، ب، ف، ك، ل) and suffixes (ي، ك، ه، ها، هم، نا، كم).
    Instead of strict word boundaries, we match the marker as a STEM:
    preceded by start-of-string, space/punctuation, or a known prefix;
    followed by end-of-string, space/punctuation, or a known suffix.
    """
    found = []
    # Common prefixes (1-2 chars) and suffixes that attach to Arabic words
    _PREFIX = r"(?:^|[\s،؛؟।.,!?])(?:ال|و|وال|بال|فال|ف|ب|ك|ل|لل)?"
    _SUFFIX = r"(?:ي|ك|ه|ها|هم|هن|نا|كم|كن|ين|ون|ات|ة|تي|ته|تها)?"
    _END    = r"(?:$|[\s،؛؟।.,!?])"
    for m in markers:
        pattern = _PREFIX + re.escape(m) + _SUFFIX + _END
        if re.search(pattern, text):
            found.append(m)
    return found


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Marker Strength Categories (P0-F)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Weak markers: common words that need corroboration (2+ other markers)
WEAK_MARKERS: frozenset = frozenset({
    "بس",          # very common Arabic filler meaning "but"/"just"
    "data",        # extremely common in non-ethical contexts
    "risk",        # common in non-ethical contexts
    "rate",        # common in non-ethical contexts
    "trying",      # very common
    "honestly",    # very common
})

# Religious terms: only activate as voice markers in first-person decision context
RELIGIOUS_MARKERS: frozenset = frozenset({
    "حلال", "حرام",
})

# First-person decision phrases that make religious terms relevant
_FIRST_PERSON_DECISION_AR: frozenset = frozenset({
    "هل يجوز", "يجوز لي", "أقدر أسوي", "ممكن أسوي",
    "المفروض أسوي", "حكم", "ينفع",
})


# Pre-compile English word-boundary patterns
_IDEAL_EN_PATTERNS = _compile_en_patterns(IDEAL_MARKERS_EN)
_REAL_EN_PATTERNS  = _compile_en_patterns(REAL_MARKERS_EN)
_COLD_EN_PATTERNS  = _compile_en_patterns(COLD_MARKERS_EN)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ColdOSEngine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ColdOSEngine:
    """
    Tri-Engine Decision Protocol — analyses user messages through
    three internal voices (Ideal, Real, COLD) and recommends a
    framing strategy for response composition.

    B-prime observational: enriches the governed prompt, never
    touches safety decisions.
    """

    # ── Authority Contract (B-prime) ──────────────────────────
    AUTHORITY_LEVEL            = "B_PRIME_OBSERVATIONAL"
    CAN_BLOCK_RUNTIME          = False
    CAN_MODIFY_H               = False
    CAN_MODIFY_THETA           = False
    CAN_MODIFY_S               = False
    CAN_EMIT_JUDICIAL_DECISION = False
    BINDING_CHANNEL            = "B5"       # Behaviour

    # ── Feature Flag ──────────────────────────────────────────
    ENABLED = True

    # ── Isolation Contract (P0-G) ─────────────────────────────
    ISOLATION_CONTRACT = """
    ColdOSEngine produces ADVISORY framing recommendations only.
    It NEVER modifies H, θ, or S.  It NEVER blocks runtime.
    Its output feeds B5 (Behaviour) channel exclusively.
    The S equation is the sole safety authority (Single-Mind Law).
    """
    ISOLATION_MARKER  = "B5_ADVISORY_NOT_FOR_SAFETY"
    ISOLATION_TARGETS = frozenset({"B5"})

    # ── Sparse Activation ─────────────────────────────────────
    _MIN_TEXT_LENGTH      = 15     # CALIBRATION_NEEDED
    _ACTIVATION_THRESHOLD = 0.25   # P0-A: raised from 0.15 (1 marker=0.20 < 0.25, no auto-activate)

    # ──────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────

    def analyze(
        self,
        text: str,
        *,
        s_decision: str = "",
        h_score: float = 0.0,
        domain: str = "general",
    ) -> ColdOSReading:
        """
        Analyse *text* through the Tri-Engine lens.

        Returns a ``ColdOSReading`` with ``activated=False`` when no
        decision-context is detected (fast-path skip).
        """
        if not self.ENABLED or not text or len(text.strip()) < self._MIN_TEXT_LENGTH:
            return self._inactive_reading()

        # 1. Decision context (P0-E: word-boundary matching)
        context = self._detect_context(text)

        # 2. Voice signals (P0-E: word-boundary, P0-F: strong/weak split)
        ideal = self._measure_voice("ideal", text,
                                    IDEAL_MARKERS_EN, IDEAL_MARKERS_AR)
        real  = self._measure_voice("real",  text,
                                    REAL_MARKERS_EN,  REAL_MARKERS_AR)
        cold  = self._measure_voice("cold",  text,
                                    COLD_MARKERS_EN,  COLD_MARKERS_AR)

        # P0-A: Context-gated activation — require BOTH context AND voice evidence
        max_strength = max(ideal.strength, real.strength, cold.strength)
        has_context = context != DecisionContext.GENERAL
        has_voice   = max_strength >= self._ACTIVATION_THRESHOLD
        if not has_context and not has_voice:
            return self._inactive_reading()

        # 3. Tension
        tension = self._detect_tension(ideal, real, cold)

        # 4. Framing strategy
        strategy = self._determine_strategy(ideal, real, cold,
                                            tension, context)

        # 5. Recommendations
        recommendations = self._generate_recommendations(
            context, ideal, real, cold, tension, strategy,
            s_decision, domain,
        )

        # 6. Evidence trail
        evidence = self._compile_evidence(context, ideal, real, cold, tension)

        # 7. P0-C: LBH interaction note
        lbh_note = ""
        if strategy == FramingStrategy.IDEAL_LEADS_REAL_SOFTENS:
            lbh_note = (
                "COLD-OS chose IDEAL_LEADS_REAL_SOFTENS. If LBH detects "
                "sermonising patterns in the resulting draft, this is a "
                "known tension — prioritise LBH feedback in B5 channel."
            )

        return ColdOSReading(
            decision_context=context,
            ideal_signal=ideal,
            real_signal=real,
            cold_signal=cold,
            tension=tension,
            framing_strategy=strategy,
            recommendations=tuple(recommendations),
            evidence=tuple(evidence),
            activated=True,
            _isolation_marker=self.ISOLATION_MARKER,
            lbh_interaction_note=lbh_note,
        )

    # ──────────────────────────────────────────────────────────
    #  Context Detection
    # ──────────────────────────────────────────────────────────

    def _detect_context(self, text: str) -> DecisionContext:
        """Classify the decision type from linguistic markers (P0-E: word-boundary)."""
        lower = text.lower()
        normalized = _normalize_arabic(text)
        scores: dict[DecisionContext, int] = {}

        for ctx, (en_markers, ar_markers) in _CONTEXT_MARKER_MAP.items():
            # English: word-boundary regex
            count = sum(
                1 for m in en_markers
                if re.search(r"\b" + re.escape(m) + r"\b", lower, re.IGNORECASE)
            )
            # Arabic: space/punctuation boundary on normalized text
            count += len(_match_ar_markers(normalized, ar_markers))
            if count > 0:
                scores[ctx] = count

        if not scores:
            return DecisionContext.GENERAL

        return max(scores, key=scores.get)          # type: ignore[arg-type]

    # ──────────────────────────────────────────────────────────
    #  Voice Measurement
    # ──────────────────────────────────────────────────────────

    def _measure_voice(
        self,
        voice_name: str,
        text: str,
        en_markers: frozenset,
        ar_markers: frozenset,
    ) -> VoiceSignal:
        """Measure strength of a voice from marker presence.

        P0-E: Uses word-boundary matching instead of substring.
        P0-F: Discounts WEAK_MARKERS unless corroborated by 2+ strong markers.
               RELIGIOUS_MARKERS only count in first-person decision context.
        """
        lower = text.lower()
        normalized = _normalize_arabic(text)

        # English: word-boundary regex
        en_found: list[str] = []
        for m in en_markers:
            if re.search(r"\b" + re.escape(m) + r"\b", lower, re.IGNORECASE):
                en_found.append(m)

        # Arabic: space/punctuation boundary on normalized text
        ar_found = _match_ar_markers(normalized, ar_markers)

        all_found = en_found + ar_found

        # ── P0-F: Split into STRONG and WEAK ──
        strong = [m for m in all_found if m not in WEAK_MARKERS and m not in RELIGIOUS_MARKERS]
        weak   = [m for m in all_found if m in WEAK_MARKERS]
        religious = [m for m in all_found if m in RELIGIOUS_MARKERS]

        # Religious markers only count in first-person decision context
        has_first_person = any(
            fp in normalized for fp in _FIRST_PERSON_DECISION_AR
        )
        if has_first_person:
            strong.extend(religious)

        # Weak markers only count if corroborated by ≥2 strong markers
        if len(strong) >= 2:
            strong.extend(weak)
        # else: weak markers are silently dropped

        effective_found = strong

        # Diminishing-returns strength curve
        # CALIBRATION_NEEDED: breakpoints are intuition-based, not empirically calibrated
        n = len(effective_found)
        if n == 0:
            strength = 0.0
        elif n == 1:
            strength = 0.20
        elif n == 2:
            strength = 0.40
        elif n == 3:
            strength = 0.60
        elif n <= 5:
            strength = 0.75
        else:
            strength = min(1.0, 0.75 + 0.05 * (n - 5))

        return VoiceSignal(
            voice=voice_name,
            strength=round(strength, 2),
            markers_found=tuple(sorted(effective_found)),
        )

    # ──────────────────────────────────────────────────────────
    #  Tension Detection
    # ──────────────────────────────────────────────────────────

    _VOICE_ACTIVE_THRESHOLD = 0.20  # CALIBRATION_NEEDED

    def _detect_tension(
        self,
        ideal: VoiceSignal,
        real: VoiceSignal,
        cold: VoiceSignal,
    ) -> TensionReading:
        """Detect tension between the three voices."""
        t = self._VOICE_ACTIVE_THRESHOLD
        ideal_on = ideal.strength >= t
        real_on  = real.strength  >= t
        cold_on  = cold.strength  >= t
        active   = sum([ideal_on, real_on, cold_on])

        if active <= 1:
            return TensionReading(
                tension_type=TensionType.NONE,
                tension_level=0.0,
                description="Single voice or none active — no tension.",
            )

        strengths = [ideal.strength, real.strength, cold.strength]
        spread = max(strengths) - min(strengths)

        if active == 3:
            if spread < 0.20:
                return TensionReading(
                    tension_type=TensionType.NONE,
                    tension_level=round(spread, 2),
                    description="All three voices balanced — unified.",
                )
            return TensionReading(
                tension_type=TensionType.THREE_WAY,
                tension_level=round(min(1.0, spread + 0.3), 2),  # CALIBRATION_NEEDED: 0.3 offset
                description="Three-way tension — significant spread.",
            )

        # Exactly two active — identify the pair
        if ideal_on and real_on:
            lvl = round(min(1.0, abs(ideal.strength - real.strength) + 0.3), 2)  # CALIBRATION_NEEDED: 0.3 offset
            return TensionReading(
                tension_type=TensionType.IDEAL_VS_REAL,
                tension_level=lvl,
                description="Ideal vs Real — principle conflicts with circumstances.",
            )
        if ideal_on and cold_on:
            lvl = round(min(1.0, abs(ideal.strength - cold.strength) + 0.3), 2)  # CALIBRATION_NEEDED: 0.3 offset
            return TensionReading(
                tension_type=TensionType.IDEAL_VS_COLD,
                tension_level=lvl,
                description="Ideal vs COLD — principle conflicts with data.",
            )
        # real_on and cold_on
        lvl = round(min(1.0, abs(real.strength - cold.strength) + 0.3), 2)  # CALIBRATION_NEEDED: 0.3 offset
        return TensionReading(
            tension_type=TensionType.REAL_VS_COLD,
            tension_level=lvl,
            description="Real vs COLD — circumstances conflict with data.",
        )

    # ──────────────────────────────────────────────────────────
    #  Framing Strategy
    # ──────────────────────────────────────────────────────────

    def _determine_strategy(
        self,
        ideal: VoiceSignal,
        real: VoiceSignal,
        cold: VoiceSignal,
        tension: TensionReading,
        context: DecisionContext,
    ) -> FramingStrategy:
        """Select the optimal framing strategy."""

        if tension.tension_type == TensionType.NONE:
            return FramingStrategy.UNIFIED

        if tension.tension_type == TensionType.THREE_WAY:
            return FramingStrategy.DEFER_TO_CLARIFICATION

        # Context-sensitive overrides
        if context in (DecisionContext.MEDICAL, DecisionContext.FINANCIAL):
            return FramingStrategy.COLD_INFORMS_REAL_SPEAKS

        if context == DecisionContext.MORAL and ideal.strength > real.strength:
            return FramingStrategy.IDEAL_LEADS_REAL_SOFTENS

        # Voice-dominance logic
        strongest_name = max(
            [("ideal", ideal.strength),
             ("real",  real.strength),
             ("cold",  cold.strength)],
            key=lambda x: x[1],
        )[0]

        if strongest_name == "cold":
            return FramingStrategy.COLD_INFORMS_REAL_SPEAKS

        if strongest_name == "ideal" and ideal.strength > real.strength + 0.15:  # CALIBRATION_NEEDED: 0.15 dominance gap
            return FramingStrategy.IDEAL_LEADS_REAL_SOFTENS

        # Default: mercy speaks
        return FramingStrategy.REAL_LEADS_IDEAL_TEACHES

    # ──────────────────────────────────────────────────────────
    #  Recommendations
    # ──────────────────────────────────────────────────────────

    def _generate_recommendations(
        self,
        context: DecisionContext,
        ideal: VoiceSignal,
        real: VoiceSignal,
        cold: VoiceSignal,
        tension: TensionReading,
        strategy: FramingStrategy,
        s_decision: str,
        domain: str,
    ) -> List[str]:
        """Produce framing guidance for the response composer."""
        recs: list[str] = []

        # Strategy-based
        _STRAT_RECS = {
            FramingStrategy.UNIFIED: [
                "All voices aligned — respond directly with confidence.",
            ],
            FramingStrategy.REAL_LEADS_IDEAL_TEACHES: [
                "Lead with the Real voice: practical, merciful, "
                "acknowledging circumstances.",
                "Reference the Ideal as aspiration, not judgment.",
            ],
            FramingStrategy.IDEAL_LEADS_REAL_SOFTENS: [
                "Lead with the Ideal voice: state the principle clearly.",
                "Soften with the Real voice: acknowledge the human difficulty.",
            ],
            FramingStrategy.COLD_INFORMS_REAL_SPEAKS: [
                "Lead with the Real voice but ground in data.",
                "Use COLD data to inform — contextualise, "
                "don't dump raw numbers.",
            ],
            FramingStrategy.DEFER_TO_CLARIFICATION: [
                "Three-way tension — respond with extra care.",
                "Present multiple perspectives; let the human decide.",
                "Preserve the possibility space; hold options open.",
            ],
        }
        recs.extend(_STRAT_RECS.get(strategy, []))

        # Context-specific
        _CTX_RECS = {
            DecisionContext.MEDICAL:   "Medical context: facts matter, "
                                       "deliver with compassion.",
            DecisionContext.SPIRITUAL: "Spiritual context: respect the faith "
                                       "dimension — don't reduce to logic.",
            DecisionContext.MORAL:     "Moral context: acknowledge complexity "
                                       "— avoid binary right/wrong framing.",
            DecisionContext.FINANCIAL: "Financial context: ground in numbers "
                                       "but respect human anxiety.",
        }
        if context in _CTX_RECS:
            recs.append(_CTX_RECS[context])

        # Tension-specific
        if tension.tension_type == TensionType.IDEAL_VS_REAL:
            recs.append(
                "Ideal and possible conflict — name both "
                "without forcing resolution."
            )

        # Invariant: this module is advisory only
        recs.append(
            "COLD-OS is advisory — the S equation's decision "
            "stands unchanged."
        )

        return recs

    # ──────────────────────────────────────────────────────────
    #  Evidence Trail
    # ──────────────────────────────────────────────────────────

    def _compile_evidence(
        self,
        context: DecisionContext,
        ideal: VoiceSignal,
        real: VoiceSignal,
        cold: VoiceSignal,
        tension: TensionReading,
    ) -> List[str]:
        ev: list[str] = [f"decision_context={context.value}"]

        if ideal.markers_found:
            ev.append(f"ideal_markers={list(ideal.markers_found)[:5]}")
        if real.markers_found:
            ev.append(f"real_markers={list(real.markers_found)[:5]}")
        if cold.markers_found:
            ev.append(f"cold_markers={list(cold.markers_found)[:5]}")

        ev.append(f"ideal_strength={ideal.strength}")
        ev.append(f"real_strength={real.strength}")
        ev.append(f"cold_strength={cold.strength}")
        ev.append(f"tension={tension.tension_type.value}|{tension.tension_level}")

        return ev

    # ──────────────────────────────────────────────────────────
    #  Inactive (fast-path) Reading
    # ──────────────────────────────────────────────────────────

    def _inactive_reading(self) -> ColdOSReading:
        empty = VoiceSignal(voice="none", strength=0.0, markers_found=())
        return ColdOSReading(
            decision_context=DecisionContext.GENERAL,
            ideal_signal=empty,
            real_signal=empty,
            cold_signal=empty,
            tension=TensionReading(
                tension_type=TensionType.NONE,
                tension_level=0.0,
                description="Not activated.",
            ),
            framing_strategy=FramingStrategy.UNIFIED,
            recommendations=(),
            evidence=(),
            activated=False,
            _isolation_marker=self.ISOLATION_MARKER,
            lbh_interaction_note="",
        )

    # ──────────────────────────────────────────────────────────
    #  Audit Hash
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def cold_os_audit_hash(reading: ColdOSReading) -> str:
        """SHA-256 digest of a ColdOSReading for audit trails."""
        parts = [
            reading.decision_context.value,
            str(reading.ideal_signal.strength),
            str(reading.real_signal.strength),
            str(reading.cold_signal.strength),
            reading.tension.tension_type.value,
            str(reading.tension.tension_level),
            reading.framing_strategy.value,
            str(reading.activated),
        ]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Self-Test
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    engine = ColdOSEngine()

    cases = [
        ("hi", False),
        ("The weather is nice today and I like it", False),
        (
            "Should I forgive my brother? He betrayed my trust "
            "but he's family and I feel guilty",
            True,
        ),
        (
            "I know I should leave this job — it's the right thing "
            "— but my family depends on my salary and I can't afford to quit",
            True,
        ),
        (
            "My doctor says the treatment has a 70% success rate "
            "but the risk of side effects is high",
            True,
        ),
        ("المفروض أسامح أخوي لكن الظروف صعبة وما أقدر", True),
        (
            "I'm thinking about investment but the statistics show "
            "high risk and my budget is limited",
            True,
        ),
        (
            "I pray every day but I've lost faith and "
            "can't find meaning anymore",
            True,
        ),
    ]

    passed = 0
    for text, expected in cases:
        r = engine.analyze(text)
        ok = r.activated == expected
        passed += ok
        tag = "✓" if ok else "✗"
        print(f"  {tag}  activated={r.activated} (exp {expected}): "
              f"{text[:55]}...")
        if r.activated:
            print(f"      ctx={r.decision_context.value}  "
                  f"strat={r.framing_strategy.value}")
            print(f"      I={r.ideal_signal.strength}  "
                  f"R={r.real_signal.strength}  "
                  f"C={r.cold_signal.strength}  "
                  f"tension={r.tension.tension_type.value}"
                  f"({r.tension.tension_level})")

    print(f"\nSelf-test: {passed}/{len(cases)} passed")
