"""
aatif_mrs_detector.py — Memory Reframing System Detector (MRS Detector)
Field Note #051: The Memory Reframing System

Slogan: "The memory stays. Its power to imprison — does not."
        الذكرى تبقى. قدرتها على السجن — لا.

Core concept:
    Separates event/fact from harmful self-interpretation.
    "فشلت في امتحان" = event → "أنا فاشل" = harmful interpretation.
    MRS Detector identifies when the user is trapped in a harmful
    self-interpretation pattern.

This module is B-prime **observational**: it DETECTS and TAGS harmful
self-interpretation patterns in user text.  It does NOT reframe — the
LLM's own compassion handles response naturally.

It does NOT make safety decisions — that is the S equation's exclusive
jurisdiction.  It does NOT decide whether a request is allowed.
It detects *meaning patterns* that trap users in harmful identity loops.

Pipeline position:  after S(d), before prompt composition.
Reads:   user message.
Produces: MRSReading with pattern detection + B5 style hints.

Novel contribution (FN#051):
    First B-prime module that detects harmful self-interpretation
    patterns — separating event from identity fusion, overgeneralization,
    catastrophizing, self-blame, and permanence bias — while remaining
    strictly observational.

Scientific support:
    - Cognitive Reappraisal (Gross 1998)
    - Narrative Therapy (White & Epston 1990)
    - Post-Traumatic Growth (Tedeschi & Calhoun 1996)

Constitutional Invariants
-------------------------
Invariant 1: FN#051 never modifies H, θ, S, H_eff, or safety verdicts.
Invariant 2: Pattern detection never lowers harm classification.
Invariant 3: Crisis signals are ADVISORY — safety handled by S equation.
Invariant 4: The module detects patterns, never prescribes reframes.
Invariant 5: Gulf Arabic idioms must not be over-escalated.
Invariant 6: Event-interpretation split required for confident detection.
Invariant 7: The GovernanceEquation remains the only judicial authority.

Authority Contract
------------------
AUTHORITY_LEVEL            = B_PRIME_OBSERVATIONAL
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA           = False
CAN_MODIFY_S               = False
CAN_EMIT_JUDICIAL_DECISION = False
BINDING_CHANNEL            = B5 (Behaviour)

Design consensus: Claude × ChatGPT, 2026-07-01 (FN051_DESIGN_CONSENSUS.md)

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
from typing import List, Tuple


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Feature Flags  (FN#051 ships ON by default)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MRS_ENABLED = True               # master switch


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class InterpretationType(Enum):
    """Primary harmful self-interpretation categories."""
    NONE                = "none"
    IDENTITY_FUSION     = "identity_fusion"        # event → permanent identity label
    OVERGENERALIZATION  = "overgeneralization"      # single event → universal pattern
    CATASTROPHIZING     = "catastrophizing"         # bad outcome → worst possible future
    SELF_BLAME          = "self_blame"              # external event → personal fault
    PERMANENCE_BIAS     = "permanence_bias"         # temporary state → permanent condition


class SecondaryPattern(Enum):
    """Secondary subpatterns (ChatGPT consensus Q2)."""
    ASSUMED_NEGATIVE_JUDGMENT  = "assumed_negative_judgment"   # "everyone thinks I'm stupid"
    PUNITIVE_SHOULD_STATEMENT  = "punitive_should_statement"  # "I should have known better"
    POSITIVE_DISQUALIFICATION  = "positive_disqualification"  # "it doesn't count"
    EMOTIONAL_REASONING        = "emotional_reasoning"         # "I feel worthless so I am"


class Severity(Enum):
    """Severity of the detected harmful self-interpretation."""
    NONE     = "none"
    MILD     = "mild"          # light self-criticism, recoverable tone
    MODERATE = "moderate"      # repeated patterns, emotional weight
    SEVERE   = "severe"        # deep identity fusion, hopelessness
    CRISIS   = "crisis"        # self-harm/suicide signals → referral flag


class LBHRiskType(Enum):
    """Types of patronizing response risk (ChatGPT consensus Q5)."""
    NONE                    = "none"
    TOXIC_POSITIVITY_RISK   = "toxic_positivity_risk"       # "you're amazing!"
    DISMISSAL_RISK          = "dismissal_risk"               # "that's not true!"
    MINIMIZATION_RISK       = "minimization_risk"            # "it's not that bad!"
    MORALIZING_RISK         = "moralizing_risk"              # "you need to take responsibility"
    UNEARNED_REASSURANCE_RISK = "unearned_reassurance_risk"  # "you'll definitely recover"
    PREMATURE_FIXING_RISK   = "premature_fixing_risk"        # "here are 5 solutions"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class MRSReading:
    """Complete MRS pattern detection reading.

    This reading is ADVISORY — it feeds the B5 (Behaviour) channel
    exclusively.  It NEVER modifies H, θ, or S.  It NEVER blocks
    runtime.  The S equation remains the sole safety authority.
    """
    # ── Primary detection ──
    primary_interpretation_type: InterpretationType
    severity: Severity
    signal_strength: float                       # 0.0 – 1.0
    markers_found: Tuple[str, ...]               # which markers matched
    language: str                                # "en", "ar", "mixed"

    # ── Compound pattern support (ChatGPT consensus Q6) ──
    secondary_interpretation_types: Tuple[InterpretationType, ...]
    compound_pattern: bool                       # True when multiple types detected
    compound_signature: str                      # e.g. "identity_fusion+permanence_bias"

    # ── Secondary subpatterns (ChatGPT consensus Q2) ──
    secondary_patterns: Tuple[SecondaryPattern, ...]

    # ── Event-interpretation split ──
    event_interpretation_split: bool             # did we detect event vs interpretation?

    # ── Crisis handling (ChatGPT consensus Q3) ──
    professional_referral_required: bool         # True for CRISIS level
    crisis_signal_observed: bool                 # separate from severity
    crisis_markers_found: Tuple[str, ...]        # specific crisis markers
    requires_independent_safety_evaluation: bool  # must be checked by S equation
    safety_decision_authority: str               # always "GOVERNANCE_EQUATION_ONLY"

    # ── Arabic idiom handling (ChatGPT consensus Q4) ──
    idiomatic_distress_possible: bool            # Gulf Arabic hyperbolic expression
    literal_crisis_confidence: float             # 0.0 – 1.0

    # ── B5 advisory ──
    b5_style_hints: Tuple[str, ...]              # renamed from recommendations (Q1)
    evidence: Tuple[str, ...]                    # audit trail
    activated: bool                              # False ⇒ fast-path skip

    # ── LBH interaction (expanded per Q5) ──
    lbh_risk_type: LBHRiskType
    lbh_interaction_note: str                    # human-readable warning

    # ── Isolation marker (B-prime contract) ──
    _isolation_marker: str = "B5_ADVISORY_NOT_FOR_SAFETY"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Marker Constants — Identity Fusion
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IDENTITY_FUSION_MARKERS_EN: frozenset = frozenset({
    "i am a failure", "i'm a failure", "im a failure",
    "i'm worthless", "im worthless", "i am worthless",
    "i'm nothing", "im nothing", "i am nothing",
    "i'm broken", "im broken", "i am broken",
    "i am the problem", "i'm the problem",
    "i'm damaged", "im damaged", "i am damaged",
    "i'm defective", "im defective",
    "i'm useless", "im useless", "i am useless",
    "i'm a loser", "im a loser", "i am a loser",
    "i'm stupid", "im stupid", "i am stupid",
    "i'm pathetic", "im pathetic",
    "i'm a burden", "im a burden",
    "i'm not good enough", "im not good enough",
    "i'm inadequate", "im inadequate",
})

IDENTITY_FUSION_MARKERS_AR: frozenset = frozenset({
    "أنا فاشل", "أنا فاشله", "أنا لا شيء", "أنا السبب",
    "أنا مكسور", "أنا مكسوره", "أنا معطوب", "أنا ضايع", "أنا ضايعه",
    # Gulf dialect (ChatGPT consensus Q4)
    "أنا مالي فايدة", "أنا مالي فايده", "ما مني فايدة", "ما مني فايده",
    "أنا خيبة", "أنا خيبه", "أنا مو قدها",
    "أنا دايم أخربها", "دايم اخربها",
    "أنا ما أنفع", "ما انفع", "أنا غلطة", "أنا غلطه",
    "أنا حقير", "أنا حقيره", "أنا تافه", "أنا تافهه",
})

# ── Overgeneralization ──

OVERGENERALIZATION_MARKERS_EN: frozenset = frozenset({
    "nothing ever works", "nothing works",
    "always fail", "i always fail", "i always mess up",
    "never works", "it never works",
    "everyone hates me", "everyone hates",
    "nobody cares", "no one cares",
    "everything goes wrong", "everything always goes wrong",
    "i can never do anything right", "can't do anything right",
    "always happens to me", "it always happens",
    "i never get it right", "never get anything right",
})

OVERGENERALIZATION_MARKERS_AR: frozenset = frozenset({
    "ما في شي ينفع", "مافي شي ينفع",
    "دايم أفشل", "دايم افشل",
    "كل شي غلط", "كلشي غلط",
    "محد يهتم", "ما حد يهتم",
    "كلهم يكرهوني", "كلهم يكرهونني",
    # Gulf dialect
    "كل شي يخرب معي", "كلشي يخرب معي",
    "ولا شي يزبط معي", "ولا شي يزبط",
    "دايم تصير لي", "عمري ما ضبطت معي",
    "كل مرة نفس الشي", "كل مره نفس الشي",
    "ما في شي يمشي معاي", "ما فيه شي يمشي معي",
})

# ── Catastrophizing ──

CATASTROPHIZING_MARKERS_EN: frozenset = frozenset({
    "my life is over", "life is over",
    "everything is ruined", "it's all ruined",
    "there's no hope", "there is no hope", "no hope left",
    "it's the end", "this is the end",
    "can never come back", "i can never come back",
    "my future is gone", "no future",
    "it's all over", "everything is over",
    "the worst has happened", "worst case scenario",
    "i'm doomed", "im doomed",
})

CATASTROPHIZING_MARKERS_AR: frozenset = frozenset({
    "حياتي انتهت", "حياتي خلصت",
    "كل شي خرب", "كلشي خرب", "كل شيء خرب",
    "ما في أمل", "مافي أمل", "ما فيه أمل",
    "انتهى كل شي", "انتهى كل شيء",
    "ما راح ترجع", "ما بترجع",
    # Gulf dialect
    "خلاص انتهيت", "خلاص خلصت",
    "مستقبلي راح", "راحت علي", "راحت عليي",
    "خربت حياتي", "خربت كل شي",
    "ما عاد فيه أمل", "ماعاد فيه امل",
})

# ── Self-Blame ──

SELF_BLAME_MARKERS_EN: frozenset = frozenset({
    "it's all my fault", "its all my fault",
    "i ruined everything", "i've ruined everything",
    "i caused this", "i caused it all",
    "because of me", "it's because of me",
    "i'm to blame", "im to blame", "i am to blame",
    "i destroyed everything", "i messed everything up",
    "i'm the reason", "im the reason",
    "if it weren't for me", "if it wasn't for me",
})

SELF_BLAME_MARKERS_AR: frozenset = frozenset({
    "كلها غلطتي", "كلها غلطي",
    "أنا خربت كل شي", "أنا خربت كل شيء",
    "بسببي", "كله بسببي",
    "أنا السبب في كل شي", "أنا السبب في كل شيء",
    # Gulf dialect
    "أنا اللي جبتها لنفسي", "انا اللي جبتها لنفسي",
    "غلطتي أنا", "غلطي انا",
    "لو إني ما سويت كذا", "لو اني ما سويت كذا",
    "كله مني", "كلها مني",
})

# ── Permanence Bias ──

PERMANENCE_BIAS_MARKERS_EN: frozenset = frozenset({
    "i'll never recover", "ill never recover", "i will never recover",
    "it will always be like this", "always be this way",
    "nothing will change", "nothing ever changes",
    "forever broken", "broken forever",
    "permanently damaged", "permanently broken",
    "i'll never get better", "ill never get better",
    "things will never improve", "it won't get better",
    "i'm stuck forever", "im stuck forever",
    "no way out", "there's no way out",
})

PERMANENCE_BIAS_MARKERS_AR: frozenset = frozenset({
    "ما راح أتعافى", "ما راح اتعافى",
    "بتظل كذا على طول", "بتضل كذا على طول",
    "ما راح يتغير شي", "ما راح يتغير شيء",
    "مكسور للأبد", "مكسوره للأبد",
    # Gulf dialect
    "ما راح أتغير", "ما راح اتغير",
    "بظل كذا", "بضل كذا",
    "عمري ما بتعداها", "عمري ما بعداها",
    "مستحيل أرجع طبيعي", "مستحيل ارجع طبيعي",
    "ما راح أتحسن", "ما راح اتحسن",
})

# ── Crisis markers (professional referral gate) ──

CRISIS_MARKERS_EN: frozenset = frozenset({
    "want to die", "i want to die",
    "end it all", "i want to end it all",
    "no reason to live", "no reason to be alive",
    "kill myself", "i want to kill myself",
    "better off dead", "i'd be better off dead",
    "can't go on", "i can't go on", "i cant go on",
    "want to disappear", "i want to disappear",
    "not worth living", "life is not worth living",
    "end my life", "i want to end my life",
    "wish i was dead", "wish i were dead",
    "i don't want to be here", "dont want to be here",
    "suicide", "self-harm", "self harm", "hurt myself",
})

CRISIS_MARKERS_AR: frozenset = frozenset({
    "أبغى أموت", "ابغى اموت",
    "ما أبغى أعيش", "ما ابغى اعيش",
    "ما في سبب أعيش", "مافي سبب اعيش",
    "أنهي حياتي", "انهي حياتي",
    "أحسن لو ما كنت موجود", "احسن لو ما كنت موجود",
    "أحسن لو ما كنت موجوده", "احسن لو ما كنت موجوده",
    "ودي أموت", "ودي اموت",
    "ما أبغى أكمل", "ما ابغى اكمل",
    "أبغى أختفي", "ابغى اختفي",
    "انتحار", "أأذي نفسي", "اأذي نفسي", "أذية النفس",
})

# ── Arabic idiomatic expressions (NOT crisis — ChatGPT consensus Q4) ──

ARABIC_IDIOMATIC_DISTRESS: frozenset = frozenset({
    "خلاص متّ", "خلاص مت", "بموت من القهر", "بموت من الضحك",
    "قاتلني", "تقتلني", "ميت من التعب", "ميته من التعب",
    "راحت علي", "طقّت مخي", "طقت مخي",
    "والله ودي أموت", "ودي اموت من الحرج",
    "مجنون", "مجنونه", "جنني", "جننتني",
    "خلاص ما اقدر", "خلاص ماني قادر",
})

# ── Secondary pattern markers ──

ASSUMED_JUDGMENT_MARKERS_EN: frozenset = frozenset({
    "everyone thinks", "they all think", "people think i'm",
    "they know i'm", "everyone can see", "they see me as",
    "they all know", "everyone knows i'm",
})

ASSUMED_JUDGMENT_MARKERS_AR: frozenset = frozenset({
    "أكيد كلهم شايفيني", "كلهم يشوفوني",
    "الناس تشوفني", "كلهم يعرفون إني",
    "كلهم شايفيني فاشل", "الناس شايفتني",
})

PUNITIVE_SHOULD_MARKERS_EN: frozenset = frozenset({
    "i should have", "i should've", "i must be stronger",
    "i ought to have", "i need to be better",
    "i have to be perfect", "why can't i just",
    "i'm supposed to", "i should know better",
})

PUNITIVE_SHOULD_MARKERS_AR: frozenset = frozenset({
    "المفروض أكون أحسن", "المفروض اكون احسن",
    "لازم أكون أقوى", "لازم اكون اقوى",
    "المفروض عرفت", "كان لازم أسوي",
    "ليش ما أقدر", "ليش ما اقدر",
})

POSITIVE_DISQUALIFICATION_MARKERS_EN: frozenset = frozenset({
    "it doesn't count", "it doesnt count",
    "anyone could have done that", "it's not a big deal",
    "doesn't matter", "it was just luck",
    "that's nothing", "so what", "big deal",
})

POSITIVE_DISQUALIFICATION_MARKERS_AR: frozenset = frozenset({
    "حتى لو نجحت، مو مهم", "مو مهم حتى لو",
    "ما يعتبر", "أي واحد يقدر يسويها",
    "ما يستاهل", "مو شي كبير",
})

EMOTIONAL_REASONING_MARKERS_EN: frozenset = frozenset({
    "i feel worthless so i must be", "i feel like a failure so i am",
    "i feel stupid so i must be stupid",
    "if i feel this way it must be true",
    "i feel it so it's true", "i feel like i'm",
})

EMOTIONAL_REASONING_MARKERS_AR: frozenset = frozenset({
    "حاسس إني فاشل يعني أكيد أنا فاشل",
    "حاسس اني فاشل",
    "أحس إني ما أنفع", "احس اني ما انفع",
    "إحساسي يقول إني", "احساسي يقول اني",
})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Arabic Normalization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _normalize_arabic(text: str) -> str:
    """Normalize Arabic text: strip diacritics, normalize alef, strip tatweel."""
    result = unicodedata.normalize("NFD", text)
    result = "".join(
        c for c in result
        if unicodedata.category(c) != "Mn"
    )
    result = result.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    result = result.replace("ـ", "")  # tatweel
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Matching Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _compile_en_patterns(markers: frozenset) -> list:
    """Pre-compile English markers with word boundaries."""
    return [
        (m, re.compile(r"\b" + re.escape(m) + r"\b", re.IGNORECASE))
        for m in sorted(markers)
    ]


def _match_en_markers(text: str, compiled: list) -> List[str]:
    """Match English markers using pre-compiled word-boundary regex."""
    return [m for m, pat in compiled if pat.search(text)]


def _match_ar_markers(text: str, markers: frozenset) -> List[str]:
    """Match Arabic markers using substring matching with normalization."""
    normalized = _normalize_arabic(text)
    found = []
    for m in markers:
        norm_marker = _normalize_arabic(m)
        if norm_marker in normalized:
            found.append(m)
    return found


# Pre-compile English patterns
_IDENTITY_EN_COMPILED = _compile_en_patterns(IDENTITY_FUSION_MARKERS_EN)
_OVERGEN_EN_COMPILED = _compile_en_patterns(OVERGENERALIZATION_MARKERS_EN)
_CATASTROPHIZE_EN_COMPILED = _compile_en_patterns(CATASTROPHIZING_MARKERS_EN)
_SELF_BLAME_EN_COMPILED = _compile_en_patterns(SELF_BLAME_MARKERS_EN)
_PERMANENCE_EN_COMPILED = _compile_en_patterns(PERMANENCE_BIAS_MARKERS_EN)
_CRISIS_EN_COMPILED = _compile_en_patterns(CRISIS_MARKERS_EN)
_ASSUMED_JUDGMENT_EN_COMPILED = _compile_en_patterns(ASSUMED_JUDGMENT_MARKERS_EN)
_PUNITIVE_SHOULD_EN_COMPILED = _compile_en_patterns(PUNITIVE_SHOULD_MARKERS_EN)
_POSITIVE_DISQUAL_EN_COMPILED = _compile_en_patterns(POSITIVE_DISQUALIFICATION_MARKERS_EN)
_EMOTIONAL_REASONING_EN_COMPILED = _compile_en_patterns(EMOTIONAL_REASONING_MARKERS_EN)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LBH Risk Mapping
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_LBH_RISK_MAP = {
    InterpretationType.IDENTITY_FUSION:    (LBHRiskType.TOXIC_POSITIVITY_RISK,
                                            "Avoid toxic positivity — do not counter identity fusion "
                                            "with unearned praise ('you're amazing!'). Validate the "
                                            "experience, separate event from identity."),
    InterpretationType.OVERGENERALIZATION: (LBHRiskType.DISMISSAL_RISK,
                                            "Avoid dismissal — do not counter overgeneralization "
                                            "with 'that's not true!'. Acknowledge the pattern the "
                                            "user sees before widening perspective."),
    InterpretationType.CATASTROPHIZING:    (LBHRiskType.MINIMIZATION_RISK,
                                            "Avoid minimizing — do not counter catastrophizing "
                                            "with 'it's not that bad!'. Validate distress before "
                                            "offering perspective."),
    InterpretationType.SELF_BLAME:         (LBHRiskType.MORALIZING_RISK,
                                            "Avoid moralizing — do not amplify guilt with "
                                            "'you need to take responsibility'. Separate "
                                            "accountability from self-punishment."),
    InterpretationType.PERMANENCE_BIAS:    (LBHRiskType.UNEARNED_REASSURANCE_RISK,
                                            "Avoid unearned reassurance — do not counter permanence "
                                            "bias with 'you'll definitely recover'. Acknowledge "
                                            "uncertainty honestly."),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  B5 Style Hints (non-prescriptive tags)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_B5_HINTS_BY_TYPE = {
    InterpretationType.IDENTITY_FUSION: (
        "avoid_identity_reinforcement",
        "separate_event_from_self_label",
        "use_low_certainty_language",
        "avoid_forced_positivity",
    ),
    InterpretationType.OVERGENERALIZATION: (
        "acknowledge_pattern_user_sees",
        "avoid_blanket_contradiction",
        "introduce_specific_counterexample_gently",
        "avoid_forced_positivity",
    ),
    InterpretationType.CATASTROPHIZING: (
        "validate_distress_before_options",
        "avoid_minimization",
        "use_temporal_language",
        "avoid_premature_problem_solving",
    ),
    InterpretationType.SELF_BLAME: (
        "avoid_moralizing_or_fault_amplification",
        "separate_accountability_from_punishment",
        "acknowledge_pain_before_perspective",
        "avoid_forced_positivity",
    ),
    InterpretationType.PERMANENCE_BIAS: (
        "avoid_unearned_reassurance",
        "acknowledge_current_difficulty",
        "use_temporal_language",
        "avoid_dismissive_optimism",
    ),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MRSDetector Engine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MRSDetector:
    """
    Memory Reframing System Detector — detects harmful self-interpretation
    patterns in user text and produces advisory MRSReadings for B5.

    B-prime observational: produces ADVISORY readings only.
    Never touches safety decisions — that is the S equation's jurisdiction.

    "The memory stays. Its power to imprison — does not."
    """

    # ── Authority Contract (B-prime) ──────────────────────────
    AUTHORITY_LEVEL            = "B_PRIME_OBSERVATIONAL"
    CAN_BLOCK_RUNTIME          = False
    CAN_MODIFY_H               = False
    CAN_MODIFY_THETA           = False
    CAN_MODIFY_S               = False
    CAN_EMIT_JUDICIAL_DECISION = False
    BINDING_CHANNEL            = "B5"       # Behaviour

    # ── Isolation Contract ────────────────────────────────────
    ISOLATION_CONTRACT = """
    MRSDetector produces ADVISORY pattern-detection readings only.
    It NEVER modifies H, θ, or S.  It NEVER blocks runtime.
    Its output feeds B5 (Behaviour) channel exclusively.
    The S equation is the sole safety authority (Single-Mind Law).
    Crisis signals are ADVISORY — the GovernanceEquation independently
    evaluates safety.  MRS does not decide, it detects.
    """
    ISOLATION_MARKER  = "B5_ADVISORY_NOT_FOR_SAFETY"
    ISOLATION_TARGETS = frozenset({"B5"})

    # ── Sparse Activation (ChatGPT consensus Q7: raised to 0.35) ──
    _MIN_TEXT_LENGTH      = 10
    _ACTIVATION_THRESHOLD = 0.35

    # ── Severity thresholds ──
    _MILD_THRESHOLD     = 0.35
    _MODERATE_THRESHOLD = 0.55
    _SEVERE_THRESHOLD   = 0.75

    # ──────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────

    def analyze(self, text: str) -> MRSReading:
        """
        Analyse *text* for harmful self-interpretation patterns.

        Returns an ``MRSReading`` with ``activated=False``
        when no interpretation signals are detected (fast-path skip).
        """
        if not MRS_ENABLED or not text or len(text.strip()) < self._MIN_TEXT_LENGTH:
            return self._inactive_reading()

        text_clean = text.strip()

        # 1. Crisis check first (always, regardless of activation)
        crisis_en = _match_en_markers(text_clean, _CRISIS_EN_COMPILED)
        crisis_ar = _match_ar_markers(text_clean, CRISIS_MARKERS_AR)
        crisis_markers = crisis_en + crisis_ar

        # 2. Check Arabic idiomatic expressions
        idiomatic_matches = _match_ar_markers(text_clean, ARABIC_IDIOMATIC_DISTRESS)
        idiomatic_distress = len(idiomatic_matches) > 0

        # If only idiomatic matches (no real crisis markers), lower crisis confidence
        literal_crisis_confidence = 0.0
        if crisis_markers:
            if idiomatic_distress:
                # Some crisis markers may be idiomatic
                non_idiomatic_crisis = [m for m in crisis_markers if m not in idiomatic_matches]
                if non_idiomatic_crisis:
                    literal_crisis_confidence = 0.9
                else:
                    literal_crisis_confidence = 0.3
            else:
                literal_crisis_confidence = 0.9

        # 3. Detect primary interpretation types
        type_scores = self._detect_all_types(text_clean)

        # 4. Detect secondary subpatterns
        secondary_patterns = self._detect_secondary_patterns(text_clean)

        # 5. Find the strongest primary type
        all_markers = []
        primary_type = InterpretationType.NONE
        best_score = 0.0
        detected_types = []

        for itype, (score, markers) in type_scores.items():
            all_markers.extend(markers)
            if score > 0:
                detected_types.append((itype, score, markers))
            if score > best_score:
                best_score = score
                primary_type = itype

        # 6. Compute signal strength
        signal_strength = min(1.0, best_score)

        # 7. Handle CRISIS — overrides everything
        crisis_detected = len(crisis_markers) > 0 and literal_crisis_confidence >= 0.5
        if crisis_detected:
            signal_strength = max(signal_strength, 0.85)

        # 8. Sparse activation gate (ChatGPT Q7: raised threshold)
        if signal_strength < self._ACTIVATION_THRESHOLD and not crisis_detected:
            return self._inactive_reading()

        # 9. Determine language
        language = self._detect_language(text_clean)

        # 10. Event-interpretation split detection
        event_split = self._detect_event_split(text_clean, all_markers)

        # 11. Compound pattern support (ChatGPT Q6)
        secondary_types = tuple(
            itype for itype, score, _ in detected_types
            if itype != primary_type and score >= self._ACTIVATION_THRESHOLD
        )
        compound = len(secondary_types) > 0
        compound_sig = "+".join(
            [primary_type.value] + [t.value for t in secondary_types]
        ) if compound else primary_type.value

        # 12. Severity assessment
        severity = self._assess_severity(
            signal_strength, crisis_detected, compound,
            len(all_markers), idiomatic_distress,
        )

        # 13. LBH risk
        lbh_risk, lbh_note = _LBH_RISK_MAP.get(
            primary_type,
            (LBHRiskType.NONE, ""),
        )

        # Compound pattern → add premature fixing risk
        if compound and severity in (Severity.MODERATE, Severity.SEVERE):
            lbh_note += " Compound pattern detected — also avoid premature fixing."
            if lbh_risk == LBHRiskType.NONE:
                lbh_risk = LBHRiskType.PREMATURE_FIXING_RISK

        # 14. B5 style hints
        b5_hints = list(_B5_HINTS_BY_TYPE.get(primary_type, ()))
        if crisis_detected:
            b5_hints.append("crisis_signal_present")
            b5_hints.append("prioritize_safety_and_connection")
        if idiomatic_distress:
            b5_hints.append("arabic_idiomatic_expression_possible")

        # 15. Evidence trail
        evidence = self._compile_evidence(
            primary_type, secondary_types, signal_strength,
            all_markers, crisis_markers, secondary_patterns,
        )

        return MRSReading(
            primary_interpretation_type=primary_type,
            severity=severity,
            signal_strength=round(signal_strength, 2),
            markers_found=tuple(all_markers),
            language=language,
            secondary_interpretation_types=secondary_types,
            compound_pattern=compound,
            compound_signature=compound_sig,
            secondary_patterns=tuple(secondary_patterns),
            event_interpretation_split=event_split,
            professional_referral_required=(severity == Severity.CRISIS),
            crisis_signal_observed=crisis_detected,
            crisis_markers_found=tuple(crisis_markers),
            requires_independent_safety_evaluation=crisis_detected,
            safety_decision_authority="GOVERNANCE_EQUATION_ONLY",
            idiomatic_distress_possible=idiomatic_distress,
            literal_crisis_confidence=round(literal_crisis_confidence, 2),
            b5_style_hints=tuple(b5_hints),
            evidence=tuple(evidence),
            activated=True,
            lbh_risk_type=lbh_risk,
            lbh_interaction_note=lbh_note,
            _isolation_marker=self.ISOLATION_MARKER,
        )

    # ──────────────────────────────────────────────────────────
    #  Detection — Primary Types
    # ──────────────────────────────────────────────────────────

    def _detect_all_types(self, text: str) -> dict:
        """Detect all primary interpretation types and return scores."""
        return {
            InterpretationType.IDENTITY_FUSION: self._score_type(
                text, _IDENTITY_EN_COMPILED, IDENTITY_FUSION_MARKERS_AR,
            ),
            InterpretationType.OVERGENERALIZATION: self._score_type(
                text, _OVERGEN_EN_COMPILED, OVERGENERALIZATION_MARKERS_AR,
            ),
            InterpretationType.CATASTROPHIZING: self._score_type(
                text, _CATASTROPHIZE_EN_COMPILED, CATASTROPHIZING_MARKERS_AR,
            ),
            InterpretationType.SELF_BLAME: self._score_type(
                text, _SELF_BLAME_EN_COMPILED, SELF_BLAME_MARKERS_AR,
            ),
            InterpretationType.PERMANENCE_BIAS: self._score_type(
                text, _PERMANENCE_EN_COMPILED, PERMANENCE_BIAS_MARKERS_AR,
            ),
        }

    def _score_type(
        self,
        text: str,
        en_compiled: list,
        ar_markers: frozenset,
    ) -> tuple:
        """Score a single interpretation type. Returns (score, markers_found)."""
        en_found = _match_en_markers(text, en_compiled)
        ar_found = _match_ar_markers(text, ar_markers)
        all_found = en_found + ar_found
        count = len(all_found)
        if count == 0:
            return (0.0, [])
        # Score: 0.40 for first marker, +0.15 for each additional
        score = min(1.0, 0.40 + (count - 1) * 0.15)
        return (score, all_found)

    # ──────────────────────────────────────────────────────────
    #  Detection — Secondary Subpatterns
    # ──────────────────────────────────────────────────────────

    def _detect_secondary_patterns(self, text: str) -> List[SecondaryPattern]:
        """Detect secondary subpatterns (ChatGPT consensus Q2)."""
        patterns = []

        if (_match_en_markers(text, _ASSUMED_JUDGMENT_EN_COMPILED)
                or _match_ar_markers(text, ASSUMED_JUDGMENT_MARKERS_AR)):
            patterns.append(SecondaryPattern.ASSUMED_NEGATIVE_JUDGMENT)

        if (_match_en_markers(text, _PUNITIVE_SHOULD_EN_COMPILED)
                or _match_ar_markers(text, PUNITIVE_SHOULD_MARKERS_AR)):
            patterns.append(SecondaryPattern.PUNITIVE_SHOULD_STATEMENT)

        if (_match_en_markers(text, _POSITIVE_DISQUAL_EN_COMPILED)
                or _match_ar_markers(text, POSITIVE_DISQUALIFICATION_MARKERS_AR)):
            patterns.append(SecondaryPattern.POSITIVE_DISQUALIFICATION)

        if (_match_en_markers(text, _EMOTIONAL_REASONING_EN_COMPILED)
                or _match_ar_markers(text, EMOTIONAL_REASONING_MARKERS_AR)):
            patterns.append(SecondaryPattern.EMOTIONAL_REASONING)

        return patterns

    # ──────────────────────────────────────────────────────────
    #  Language Detection
    # ──────────────────────────────────────────────────────────

    def _detect_language(self, text: str) -> str:
        """Detect whether text is English, Arabic, or mixed."""
        has_arabic = bool(re.search(r'[؀-ۿ]', text))
        has_english = bool(re.search(r'[a-zA-Z]{2,}', text))
        if has_arabic and has_english:
            return "mixed"
        if has_arabic:
            return "ar"
        return "en"

    # ──────────────────────────────────────────────────────────
    #  Event-Interpretation Split
    # ──────────────────────────────────────────────────────────

    def _detect_event_split(self, text: str, markers: List[str]) -> bool:
        """
        Detect if we can identify both an event AND an interpretation.

        Higher confidence when both are present (ChatGPT consensus Q7).
        """
        if not markers:
            return False

        # Look for event markers — things that happened
        event_markers_en = [
            "failed", "lost", "rejected", "fired", "broke up",
            "didn't get", "couldn't", "was denied", "got rejected",
            "exam", "job", "interview", "relationship", "test",
        ]
        event_markers_ar = [
            "فشلت", "رسبت", "خسرت", "طردوني", "انفصلنا",
            "ما قبلوني", "ما قدرت", "رفضوني", "امتحان",
        ]

        text_lower = text.lower()
        has_event_en = any(m in text_lower for m in event_markers_en)
        text_norm = _normalize_arabic(text)
        has_event_ar = any(_normalize_arabic(m) in text_norm for m in event_markers_ar)

        return has_event_en or has_event_ar

    # ──────────────────────────────────────────────────────────
    #  Severity Assessment
    # ──────────────────────────────────────────────────────────

    def _assess_severity(
        self,
        signal_strength: float,
        crisis_detected: bool,
        compound: bool,
        marker_count: int,
        idiomatic: bool,
    ) -> Severity:
        """Assess severity level based on signal strength and context."""
        if crisis_detected:
            return Severity.CRISIS

        # Compound patterns boost severity slightly
        effective_strength = signal_strength
        if compound:
            effective_strength = min(1.0, effective_strength + 0.10)

        # Idiomatic Arabic dampens severity
        if idiomatic:
            effective_strength = max(0.0, effective_strength - 0.15)

        if effective_strength >= self._SEVERE_THRESHOLD:
            return Severity.SEVERE
        if effective_strength >= self._MODERATE_THRESHOLD:
            return Severity.MODERATE
        if effective_strength >= self._MILD_THRESHOLD:
            return Severity.MILD
        return Severity.NONE

    # ──────────────────────────────────────────────────────────
    #  Evidence Trail
    # ──────────────────────────────────────────────────────────

    def _compile_evidence(
        self,
        primary: InterpretationType,
        secondary_types: tuple,
        strength: float,
        markers: list,
        crisis_markers: list,
        secondary_patterns: list,
    ) -> List[str]:
        """Compile audit evidence trail."""
        evidence = [
            f"primary_type:{primary.value}",
            f"signal_strength:{strength:.2f}",
            f"marker_count:{len(markers)}",
        ]
        if secondary_types:
            evidence.append(
                f"compound_types:{'+'.join(t.value for t in secondary_types)}"
            )
        if secondary_patterns:
            evidence.append(
                f"secondary_patterns:{','.join(p.value for p in secondary_patterns)}"
            )
        if crisis_markers:
            evidence.append(f"crisis_markers:{len(crisis_markers)}")
        for m in markers[:5]:  # cap at 5 for readability
            evidence.append(f"marker:'{m}'")
        return evidence

    # ──────────────────────────────────────────────────────────
    #  Inactive Reading (fast-path skip)
    # ──────────────────────────────────────────────────────────

    def _inactive_reading(self) -> MRSReading:
        """Return a fast-path inactive reading."""
        return MRSReading(
            primary_interpretation_type=InterpretationType.NONE,
            severity=Severity.NONE,
            signal_strength=0.0,
            markers_found=(),
            language="en",
            secondary_interpretation_types=(),
            compound_pattern=False,
            compound_signature="none",
            secondary_patterns=(),
            event_interpretation_split=False,
            professional_referral_required=False,
            crisis_signal_observed=False,
            crisis_markers_found=(),
            requires_independent_safety_evaluation=False,
            safety_decision_authority="GOVERNANCE_EQUATION_ONLY",
            idiomatic_distress_possible=False,
            literal_crisis_confidence=0.0,
            b5_style_hints=(),
            evidence=(),
            activated=False,
            lbh_risk_type=LBHRiskType.NONE,
            lbh_interaction_note="",
            _isolation_marker=self.ISOLATION_MARKER,
        )

    # ──────────────────────────────────────────────────────────
    #  Audit Hash
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def audit_hash(reading: MRSReading) -> str:
        """SHA-256 digest of an MRSReading for audit trails."""
        parts = [
            reading.primary_interpretation_type.value,
            reading.severity.value,
            str(reading.signal_strength),
            str(reading.compound_pattern),
            reading.compound_signature,
            str(reading.crisis_signal_observed),
            str(reading.activated),
        ]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Self-Test
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    engine = MRSDetector()

    # Quick smoke tests
    tests = [
        "I failed the exam and I'm a complete failure",
        "أنا فاشل وما راح أتغير",
        "I feel sad today",
        "I want to die",
        "بموت من القهر",
        "Nothing ever works and I'll never recover",
    ]

    for t in tests:
        r = engine.analyze(t)
        print(f"\n{'='*60}")
        print(f"Text: {t}")
        print(f"Activated: {r.activated}")
        if r.activated:
            print(f"Primary: {r.primary_interpretation_type.value}")
            print(f"Severity: {r.severity.value}")
            print(f"Signal: {r.signal_strength}")
            print(f"Compound: {r.compound_pattern} ({r.compound_signature})")
            print(f"Crisis: {r.crisis_signal_observed}")
            print(f"LBH Risk: {r.lbh_risk_type.value}")
            print(f"Hash: {MRSDetector.audit_hash(r)[:16]}...")
