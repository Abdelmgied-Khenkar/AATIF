"""
AATIF Dual-Root Reconstruction Engine — محرك إعادة البناء ثنائي الجذر  (Field Note #050)
========================================================================================

Architecture: B-prime post-S (Response Enrichment)
──────────────────────────────────────────────────
DualRootDetector  →  observational (detects dual psychological+ethical root signals)
ResponseShaper    →  enrichment (adds empathy to safety responses)
GovernanceEquation →  judicial (S decision is FINAL — DRE never touches it)

Critical Design Rule (Single Mind):
  Only GovernanceEquation makes SAFETY decisions. DRE is RESPONSE ENRICHMENT,
  NOT safety. DualRootDetector never touches S, H, θ, I, E, or the
  GovernanceEquation. It enriches AFTER the governance equation has decided.

  DRE does not perform therapy, diagnosis, or causal psychology. It performs
  bounded dual-root signal reconstruction for safer response shaping after
  the governance equation has already made its decision.

  9 Invariants:
    1. S-decision immutability — never modify S_decision, H, I, E, θ, α
    2. No downgrade — BLOCK→CLARIFY, CLARIFY→EXECUTE prohibited
    3. Boundary preservation — acknowledgment + refusal + alternative
    4. No causal certainty — no "because of your trauma..."
    5. Meta-Oversight audit — response_contains_refusal, no clinical labels
    6. False Goodness guard — if FN#049 fires, DRE must not activate
    7. Malicious intent exclusion — deliberate malice → no empathic reconstruction
    8. Authority Preservation — enrichment must not increase probability of user bypass
    9. Fiction/Roleplay exclusion — fiction context → DRE does not activate

Clinical Boundary:
  "No Diagnosis, No Treatment, No Root-Certainty."
  SAFE: "I notice distress signals in what you're describing"
  UNSAFE: "Your trauma is causing..." (PROHIBITED)

Design consensus: Claude × ChatGPT, 2026-06-30 (FN050_DESIGN_CONSENSUS.md)
Field Note: FN#050 (Dual-Root Reconstruction Engine)

"الألم ما يبرر الأذى — لكن فهمه يساعدنا نوجّه الإنسان لمكان أأمن."
"Pain does not justify harm — but understanding it helps us guide a person to a safer place."

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:  # pragma: no cover — import shim for both package and flat layouts
    from aatif_arabic_utils import normalize_arabic
except Exception:  # pragma: no cover
    def normalize_arabic(text: str) -> str:
        return text.lower()


# ═══════════════════════════════════════════════════════════════
#  Feature Flags  (FN#050 ships OFF by default)
# ═══════════════════════════════════════════════════════════════

DRE_ENABLED = False              # master switch for the DRE pipeline
DRE_MONITOR_ONLY = True          # log only, no response enrichment


# ═══════════════════════════════════════════════════════════════
#  Constants — activation thresholds
# ═══════════════════════════════════════════════════════════════

# Stage 1: Safety relevance
ELIGIBLE_S_DECISIONS = {"CLARIFY", "BLOCK_SOFT", "EXECUTE_WITH_CAUTION"}
EXCLUDED_S_DECISIONS = {"SAFE_FREEZE", "CBRN_BLOCK"}
H_RANGE_MIN = 0.20
H_RANGE_MAX = 0.55

# Stage 2: Distress authenticity
STRONG_DISTRESS_THRESHOLD = 1   # ≥1 strong marker
WEAK_DISTRESS_THRESHOLD = 2     # ≥2 weak markers

# Stage 3: Malicious intent exclusion
MALICIOUS_INTENT_THRESHOLD = 0.70

# Co-occurrence confidence
CO_OCCURRENCE_MIN_EVIDENCE = 1

# Root signal strength ranges
ROOT_STRONG_SIGNAL_WEIGHT = 0.80
ROOT_WEAK_SIGNAL_WEIGHT = 0.40

# Factual query types — DRE does not activate on these
FACTUAL_QUERY_TYPES = {"factual", "objective", "academic", "news", "definition"}

# Five-layer intent layers that indicate DRE relevance
DRE_RELEVANT_LAYERS = {"HIDDEN", "PROTECTIVE", "EMOTIONAL"}


# ═══════════════════════════════════════════════════════════════
#  Clinical boundary — prohibited claims
# ═══════════════════════════════════════════════════════════════

CLINICAL_PROHIBITED_TERMS = [
    "trauma", "traumatic", "ptsd", "diagnosis", "disorder", "syndrome",
    "therapy", "treatment", "condition", "pathology", "clinical",
    "because of your trauma", "your wound is", "your trauma is causing",
    "صدمة", "صدمه", "اضطراب", "تشخيص", "علاج نفسي", "مرض نفسي",
    "الصدمة اللي عندك", "الصدمة سبب", "عقدة",
    # Fix 7: مرادفات سريرية إضافية — additional clinical boundary synonyms
    "استشارة", "دكتور نفسي", "حالة نفسية", "جلسة علاج",
]

DEFAULT_PROHIBITED_CLAIMS = [
    "do not diagnose",
    "do not say trauma",
    "do not imply violence is justified",
    "do not provide harmful instructions",
]


# ═══════════════════════════════════════════════════════════════
#  Root A — Psychological / distress-origin signal markers
# ═══════════════════════════════════════════════════════════════
#
#  Root A captures DISTRESS signals — pain, fear, humiliation, flooding.
#  These are signal markers, NOT diagnoses. "signal_type" is a label
#  for the KIND of distress signal, not a clinical category.

# Strong distress markers (1 is enough for Stage 2)
ROOT_A_STRONG_MARKERS_AR = [
    # Category A: قهر / كسر / وجع — dignity-pain
    "مقهور", "مقهوره", "مقهورة",
    "منكسر", "منكسره", "منكسرة",
    "متوجع", "موجوع",
    "قهرني", "كسرني", "وجعني", "ذبحني", "دمرني",
    # Category D: الصبر نفد / طفح الكيل — emotional threshold exceeded
    "الصبر نفد", "طفح الكيل", "ما عاد اتحمل", "وصلت حدي",
    "ما اقدر اصبر", "بنفجر", "خلاص ما اقدر",
    # Pain intensity
    "ابغى اموت", "ابي اموت", "أبي اموت",  # Fix 3: Gulf variants
    "تمنيت الموت", "ودي اختفي", "ما ابغى اعيش",
    "كرهت حياتي", "ضايق صدري",
    "مخنوق", "مخنوقه", "مخنوقة",
]

ROOT_A_STRONG_MARKERS_EN = [
    "i can't take it anymore", "i want to die", "i wish i was dead",
    "i want to disappear", "i hate my life", "i'm suffocating",
    "i feel broken", "destroyed me", "crushed me", "shattered me",
    "i've reached my limit", "at my breaking point", "can't breathe",
    "unbearable pain", "excruciating", "i'm drowning",
]

# Weak distress markers (need ≥2 for Stage 2)
ROOT_A_WEAK_MARKERS_AR = [
    "تعبان", "تعبانه", "تعبانة",
    "زعلان", "زعلانه", "زعلانة",
    "حزين", "حزينه", "حزينة",
    "متضايق", "متضايقه", "مجروح", "مجروحه",
    "مظلوم", "مظلومه", "مظلومة",
    "مهان", "مهانه", "ذليل", "ذليله", "مكسور", "متألم", "متألمه",
    "مهموم", "مهمومه", "قلقان", "قلقانه",
    "خايف", "خايفه", "خايفة",
    "محروق", "محبط", "محبطه", "يائس", "يائسه",
    # Category C (as Root A): كرامة / إهانة / ذل — honor/dignity-pain context
    "كرامتي", "إهانة", "اهانه", "ذل", "اذلني", "اذلوني",
    # Fix 8: عيب/عار — shame as distress signal (both ة and ه forms)
    "عيب", "عار", "فضيحة علينا", "فضيحه علينا",
    "يا عيبنا", "حشمة", "حشمه",
]

ROOT_A_WEAK_MARKERS_EN = [
    "tired", "exhausted", "sad", "upset", "hurt", "humiliated",
    "depressed", "anxious", "scared", "afraid", "hopeless",
    "frustrated", "disappointed", "betrayed", "abandoned",
    "lonely", "isolated", "overwhelmed", "helpless", "ashamed",
    "embarrassed", "discouraged", "miserable",
]

# Root A signal types
ROOT_A_TYPES = {
    "pain": ["متوجع", "موجوع", "وجعني", "pain", "hurts", "aching", "suffering"],
    "fear": ["خايف", "خايفه", "خايفة", "اخاف", "أخاف",
             "scared", "afraid", "terrified", "fear"],
    "humiliation_pain": ["مقهور", "مقهوره", "مقهورة",
                         "منكسر", "منكسره", "منكسرة",
                         "مهان", "مهانه",
                         "اذلني", "اذلوني", "كرامتي", "إهانة", "اهانه", "اهانوني",
                         "humiliated", "degraded", "shamed", "disgraced"],
    "injustice_pain": ["مظلوم", "مظلومه", "مظلومة",
                       "ظلموني", "ظلم", "injustice", "unfair",
                       "wronged", "unjust"],
    "avoidance_loop": ["ما اقدر اواجه", "مش قادر اواجه", "can't face", "avoiding",
                       "i keep running", "can't confront"],
    "flooding": ["بنفجر", "مخنوق", "مخنوقه", "مخنوقة", "ضايق صدري",
                 "overwhelmed", "flooding", "can't think straight", "spiraling"],
    "emotional_threshold_exceeded": ["الصبر نفد", "طفح الكيل", "ما عاد اتحمل",
                                     "وصلت حدي", "خلاص ما اقدر",
                                     "at my limit", "breaking point",
                                     "i can't take it anymore", "reached my limit"],
    # Fix 8: عيب/عار — shame as distress driver
    # Note: include both ة and ه forms for normalize_arabic compat
    "shame_pain": ["عيب", "عار", "فضيحة علينا", "فضيحه علينا",
                   "يا عيبنا", "حشمة", "حشمه"],
}


# ═══════════════════════════════════════════════════════════════
#  Root B — Ethical-drift / justification signal markers
# ═══════════════════════════════════════════════════════════════
#
#  Root B captures MORAL DRIFT signals — justification, normalization,
#  moral inversion, retaliatory justice. These are behavioral signals
#  of how pain is being channeled, NOT moral judgments.

ROOT_B_MARKERS_AR = [
    # Category B: حقي / أخذ حقي / أربيه — retaliatory justice
    "حقي", "اخذ حقي", "أخذ حقي", "اربيه", "أربّيه", "الحق لي",
    "لازم يتأدب", "لازم يتعلم", "ياخذ درس", "يتلقن درس",
    # Category E: الدعاء / اللعن / الشماتة — moral displacement
    "الله ينتقم منه", "الله يذله", "الله يهده", "يستاهل",
    "ما يستاهل رحمه", "الله ياخذه", "الله يعاقبه",
    # Category F: الطيبة ما تنفع — moral inversion
    "الطيبه ما تنفع", "الطيبة ما تنفع", "الطيب يندعس",
    "اللي يرحم ما احد يرحمه", "الحق ضاع",
    # Category G: فضيحة / سمعة / تشهير — reputation harm
    "افضحه", "أفضحه", "اشهّر فيه", "اشهر فيه", "اخرب سمعته",
    "أخرب سمعته", "فضيحه", "فضيحة", "انشر صوره", "أنشر صوره",
    # Category H: عين بعين / الرد بالمثل — reciprocal harm
    "عين بعين", "الرد بالمثل", "زي ما سوى فيني", "زي ما عملي",
    "بسوي فيه زي ما سوى", "بعامله زي ما عاملني",
    # Category C (as Root B): كرامة / إهانة — honor-retaliation context
    "رد كرامتي", "استرجع كرامتي", "اهينه زي ما اهانني",
    # Fix 8: عيب/عار — defiance against shame (both hamza and no-hamza forms)
    "بس ما أقدر أوقف", "بس ما اقدر اوقف",
    "أعرف عيب بس", "اعرف عيب بس",
    "مش قادر أوقف", "مش قادر اوقف",
]

ROOT_B_MARKERS_EN = [
    # Retaliatory justice
    "teach him a lesson", "teach her a lesson", "make him pay",
    "make her pay", "get my revenge", "get even", "payback",
    "he deserves it", "she deserves it", "they deserve it",
    "take my right", "get what's mine",
    # Moral displacement / dehumanizing wishes
    "i hope he suffers", "i hope she suffers", "karma will get",
    "he doesn't deserve mercy", "she doesn't deserve mercy",
    "rot in hell", "burn in hell", "deserves to die",
    # Moral inversion
    "being kind gets you nowhere", "nice guys finish last",
    "kindness is weakness", "mercy is weakness",
    "no point being good", "being good doesn't pay",
    # Reputation harm
    "expose him", "expose her", "ruin his reputation",
    "ruin her reputation", "share his photos", "tell everyone",
    "post it online", "destroy his image",
    # Reciprocal harm
    "eye for an eye", "do to him what he did", "taste of his own medicine",
    "treat her like she treated me", "an eye for an eye",
    # Justification / normalization
    "he had it coming", "she asked for it", "they brought it on themselves",
    "i have the right to", "justified in", "anyone would do the same",
    # Fix 8: shame defiance (English)
    "I know it's wrong but",
]

# Root B signal types
ROOT_B_TYPES = {
    "justification": ["يستاهل", "he deserves it", "she deserves it",
                      "they deserve it", "justified", "he had it coming",
                      "she asked for it", "anyone would do the same"],
    "normalization": ["عادي", "مو غلط", "not wrong", "it's normal",
                      "everyone does it", "nothing wrong with"],
    "moral_inversion": ["الطيبه ما تنفع", "الطيبة ما تنفع", "الطيب يندعس",
                        "kindness is weakness", "nice guys finish last",
                        "being good doesn't pay", "mercy is weakness"],
    "retaliatory_justice": ["حقي", "اخذ حقي", "أخذ حقي", "اربيه", "أربّيه",
                            "لازم يتأدب", "لازم يتعلم",
                            "رد كرامتي", "استرجع كرامتي",
                            "teach him a lesson", "make him pay", "get my revenge",
                            "get even", "payback", "take my right"],
    "dehumanizing_or_punitive_wish": ["الله ينتقم منه", "الله يذله", "ما يستاهل رحمه",
                                      "الله ياخذه", "الله يعاقبه",
                                      "i hope he suffers", "rot in hell",
                                      "deserves to die", "burn in hell"],
    "reputation_harm": ["افضحه", "أفضحه", "اشهّر فيه", "اخرب سمعته", "أخرب سمعته",
                        "انشر صوره", "أنشر صوره",
                        "expose him", "expose her", "ruin his reputation",
                        "share his photos", "post it online"],
    "reciprocal_harm_justification": ["عين بعين", "الرد بالمثل",
                                      "بسوي فيه زي ما سوى",
                                      "eye for an eye", "taste of his own medicine",
                                      "do to him what he did"],
    # Fix 8: عيب/عار — shame and social defiance
    # Note: markers stored in normalized form (no hamza) for normalize_arabic compat
    "shame_defiance": ["بس ما اقدر اوقف", "اعرف عيب بس", "مش قادر اوقف",
                       "i know it's wrong but"],
}

# Fix 8: عيب/عار — shame and social defiance category (9th Arabic-specific)
ROOT_A_SHAME_MARKERS_AR = [
    "عيب", "عار", "فضيحة علينا", "فضيحه علينا",
    "يا عيبنا", "حشمة", "حشمه",
]

ROOT_B_SHAME_DEFIANCE_MARKERS_AR = [
    "بس ما أقدر أوقف", "بس ما اقدر اوقف",
    "أعرف عيب بس", "اعرف عيب بس",
    "مش قادر أوقف", "مش قادر اوقف",
]

ROOT_B_SHAME_DEFIANCE_MARKERS_EN = [
    "I know it's wrong but",
]

# Ethical drift phrases that need a target to count
ETHICAL_DRIFT_PHRASES_AR = [
    "ابغى اضربه", "أبغى أضربه", "ابغى اذبحه", "ابغى اقتله",
    "ابي اضربه", "أبي أضربه", "ابي اذبحه", "ابي اقتله",  # Fix 3: Gulf variants
    "بكسره", "بدمره", "بخرب عليه", "بأذيه",
]

ETHICAL_DRIFT_PHRASES_EN = [
    "i want to hit", "i want to hurt", "i want to kill",
    "i'll destroy", "i'll break", "i'll ruin",
    "going to hurt", "going to hit",
]

# Harm targets (when drift phrase + target co-occur → Stage 3 passes)
HARM_TARGET_MARKERS = [
    "him", "her", "them", "my husband", "my wife", "my boss",
    "my father", "my mother", "my brother", "my sister", "my neighbor",
    "my ex", "my colleague", "the teacher", "the doctor",
    "زوجي", "زوجتي", "ابوي", "امي", "أمي", "أبوي",
    "اخوي", "أخوي", "اختي", "أختي", "جاري", "مديري",
    "المعلم", "المعلمه", "الدكتور", "حبيبي السابق", "طليقي",
]


# ═══════════════════════════════════════════════════════════════
#  Co-occurrence markers — evidence-bounded direction signals
#  (Fix 1: renamed from cross-causal; direction is observational,
#   not a causal claim)
# ═══════════════════════════════════════════════════════════════

CO_OCCURRENCE_A_PRECEDES_B_AR = [
    "من كثر", "من شدة", "عشان", "لأنه", "لانه", "بسبب",
    "من الألم", "من القهر", "من الظلم", "الوجع خلاني",
    "الألم خلاني", "من كثر ما تألمت",
]

CO_OCCURRENCE_A_PRECEDES_B_EN = [
    "because of the pain", "the pain made me", "the hurt drove me",
    "out of pain", "out of anger", "suffering made me",
    "because i was hurt", "because i suffered", "the humiliation led me",
    "the injustice pushed me",
]

CO_OCCURRENCE_B_PRECEDES_A_AR = [
    "ندمت", "ندمان", "احس بذنب", "أحس بذنب", "تأنيب ضمير",
    "عذاب ضمير", "ضميري يأنبني", "الانتقام ما ارتحت",
]

CO_OCCURRENCE_B_PRECEDES_A_EN = [
    "i feel guilty", "my conscience", "regretting", "i regret",
    "revenge didn't help", "it made me feel worse",
    "the guilt is eating me", "i can't live with what i did",
]

# Allowed co-occurrence values (Fix 1: renamed enum values)
CO_OCCURRENCE_VALUES = {
    "a_precedes_b",
    "b_precedes_a",
    "co_present_direction_unclear",
    "independent",
    "none",
}

# Backward compatibility aliases
CROSS_CAUSAL_VALUES = CO_OCCURRENCE_VALUES


# ═══════════════════════════════════════════════════════════════
#  Response guidance templates
# ═══════════════════════════════════════════════════════════════

GUIDANCE_TEMPLATES = {
    "dual_root": (
        "Acknowledge distress without validating harm. "
        "Reject violence clearly. "
        "Separate pain from retaliation. "
        "Offer protective, non-harmful next steps."
    ),
    "distress_boundary": (
        "Acknowledge distress signals compassionately. "
        "Validate the emotion without endorsing harmful action. "
        "Offer constructive alternatives."
    ),
    "ethical_boundary": (
        "Name the ethical concern directly. "
        "Do not validate the harmful impulse. "
        "Offer non-harmful alternatives that address the underlying need."
    ),
}

# ═══════════════════════════════════════════════════════════════
#  Fix 5: False Goodness indicators (Invariant 6 implementation)
# ═══════════════════════════════════════════════════════════════

FALSE_GOODNESS_INDICATORS = [
    "عادي ما عليك", "مو مشكلة", "it's fine really", "no worries at all",
    "لا تهتم", "don't worry about it", "it's nothing", "كله تمام",
    "no problem at all", "i'm totally fine", "مافي شي", "عادي عادي",
]


# ═══════════════════════════════════════════════════════════════
#  Fix 6: Fiction / roleplay context indicators (Stage 0)
# ═══════════════════════════════════════════════════════════════

FICTION_ROLEPLAY_INDICATORS = [
    # Arabic (both ة and ه forms for normalize_arabic compatibility)
    "قصة", "قصه", "رواية", "روايه", "مسرحية", "مسرحيه",
    "فيلم", "مسلسل", "شخصية", "شخصيه",
    # English
    "fiction", "story", "screenplay", "roleplay", "character",
    "novel", "imagine", "pretend", "let's say",
]


# ═══════════════════════════════════════════════════════════════
#  Fix 9: Authority Preservation — max enrichment sentences by S_decision
# ═══════════════════════════════════════════════════════════════

MAX_ENRICHMENT_SENTENCES = {
    "BLOCK": 2,
    "BLOCK_SOFT": 3,
    "CLARIFY": 5,
    "EXECUTE_WITH_CAUTION": 0,  # 0 = unlimited
}


# ═══════════════════════════════════════════════════════════════
#  Fix 4: Negation prefixes — negated markers should not trigger distress
# ═══════════════════════════════════════════════════════════════

NEGATION_PREFIXES = ["ما", "لا", "مش", "ماني", "مو"]


# ═══════════════════════════════════════════════════════════════
#  Fix 10: Causal language terms (Invariant 4 enforcement)
# ═══════════════════════════════════════════════════════════════

CAUSAL_LANGUAGE_TERMS = [
    "feeds", "causes", "leads to", "because of",
    "يسبب", "يؤدي إلى", "بسبب أن",
]


GUIDANCE_ARABIC_TEMPLATES = {
    "violence": (
        "أفهم إنك متألم من اللي صار، والغضب هنا مفهوم. "
        "لكن إيذاءه مش حل آمن..."
    ),
    "reputation_harm": (
        "أفهم إنك حاسس بالظلم، لكن فضحه أو نشر شيء عنه "
        "ممكن يضرّك قانونيًا وأخلاقيًا..."
    ),
    "self_harm_adjacent": (
        "أسمع إنك وصلت لمرحلة ألم شديد. "
        "ما أبغى أخليك وحدك مع هذا الشعور..."
    ),
}


# ═══════════════════════════════════════════════════════════════
#  Data Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class RootSignal:
    """A single detected root signal — signal analysis, not diagnosis."""
    signal_type: str
    evidence: List[str] = field(default_factory=list)
    strength: float = 0.0


@dataclass
class DualRootAnalysis:
    """
    Output of analyze_dual_root() — observational, NOT clinical.

    Single Mind: DRE NEVER touches S, H, θ, I, E, or safety decisions.
    This is response enrichment AFTER the governance equation has decided.
    """
    # Activation
    dre_active: bool = False
    activation_reason: str = ""
    activation_confidence: float = 0.0

    # Root A — Psychological / distress-origin signals
    root_a_signal_detected: bool = False
    root_a_signal_type: str = ""
    root_a_evidence: List[str] = field(default_factory=list)
    root_a_strength: float = 0.0

    # Root B — ethical-drift / justification signals
    root_b_signal_detected: bool = False
    root_b_signal_type: str = ""
    root_b_evidence: List[str] = field(default_factory=list)
    root_b_strength: float = 0.0

    # Pattern status
    dual_root_pattern_detected: bool = False
    pattern_confidence: float = 0.0

    # Co-occurrence — evidence-bounded only (Fix 1: renamed from cross_causal)
    co_occurrence_type: str = "none"
    co_occurrence_evidence: List[str] = field(default_factory=list)

    # POM signal trace — not clinical
    pom_trace: Dict[str, str] = field(default_factory=dict)

    # Response shaping only
    response_guidance: str = ""
    enrichment_mode: str = ""  # "dual_root", "distress_boundary", "ethical_boundary", ""
    prohibited_claims: List[str] = field(default_factory=list)

    # Fix 5: False Goodness detection
    false_goodness_flag: bool = False

    # Fix 6: Fiction/roleplay exclusion
    fiction_or_roleplay_context: bool = False

    # Fix 9: Authority Preservation — max enrichment sentence limit applied
    max_enrichment_sentences: int = 0  # 0 = unlimited

    # Feature flag state at time of analysis
    enabled: bool = False
    monitor_only: bool = True


@dataclass
class DREContext:
    """
    Context for DRE activation gate — passed by the pipeline.

    DRE reads these values; it NEVER modifies them.
    """
    text: str = ""
    s_decision: str = ""
    H: float = 0.0
    false_goodness_detected: bool = False
    intent_malicious_confidence: float = 0.0
    query_type: str = ""
    five_layer_detected: Optional[List[str]] = None


# ═══════════════════════════════════════════════════════════════
#  Fix 4: Negation prefix detection helper
# ═══════════════════════════════════════════════════════════════

def _has_negation_prefix(text: str, marker_position: int) -> bool:
    """
    Check if a marker at the given position is preceded by a negation prefix.

    Looks at the 1-3 words before the marker position for negation words:
    "ما", "لا", "مش", "ماني", "مو".
    Returns True if negation is found → marker should NOT trigger.
    """
    # Extract the text before the marker (up to 30 chars for 1-3 words)
    prefix_start = max(0, marker_position - 30)
    prefix_text = text[prefix_start:marker_position].strip()
    if not prefix_text:
        return False

    # Split into words and check last 1-3 words
    words_before = prefix_text.split()
    check_words = words_before[-3:] if len(words_before) >= 3 else words_before

    for word in check_words:
        if word in NEGATION_PREFIXES:
            return True
    return False


# ═══════════════════════════════════════════════════════════════
#  Fix 6: Fiction / roleplay context check (Stage 0)
# ═══════════════════════════════════════════════════════════════

def _check_fiction_context(text: str) -> bool:
    """
    Stage 0: Check if text contains fiction/roleplay context indicators.

    If fiction context detected, DRE should not activate — distress
    markers in fiction are not real distress signals.
    """
    norm = normalize_arabic(text)
    for indicator in FICTION_ROLEPLAY_INDICATORS:
        if indicator.lower() in norm:
            return True
    return False


# ═══════════════════════════════════════════════════════════════
#  Fix 5: False Goodness detection (Invariant 6 implementation)
# ═══════════════════════════════════════════════════════════════

def _check_false_goodness(text: str, s_decision: str) -> bool:
    """
    Invariant 6: detect excessive politeness/compliance that may mask
    manipulative intent.

    If false goodness indicators are present AND S_decision was
    EXECUTE or EXECUTE_WITH_CAUTION, flag as potential false goodness.
    DRE should NOT activate in this case.
    """
    if s_decision not in ("EXECUTE", "EXECUTE_WITH_CAUTION"):
        return False

    norm = normalize_arabic(text)
    for indicator in FALSE_GOODNESS_INDICATORS:
        if indicator.lower() in norm:
            return True
    return False


# ═══════════════════════════════════════════════════════════════
#  Fix 10: Causal language check (Invariant 4 enforcement)
# ═══════════════════════════════════════════════════════════════

class InvariantViolation(Exception):
    """Raised when a DRE invariant is violated."""
    pass


def _check_no_causal_language(text: str) -> List[str]:
    """
    Scan text for causal language terms that violate Invariant 4.

    Returns list of found causal terms. Empty list = no violations.
    DRE output must never claim causal certainty.
    """
    found: List[str] = []
    text_lower = text.lower()
    for term in CAUSAL_LANGUAGE_TERMS:
        if term.lower() in text_lower:
            found.append(term)
    return found


# ═══════════════════════════════════════════════════════════════
#  Fix 9: Authority Preservation — sentence limiting
# ═══════════════════════════════════════════════════════════════

def _apply_authority_preservation(guidance: str, s_decision: str) -> Tuple[str, int]:
    """
    Invariant 8: Limit enrichment output length based on S_decision severity.

    BLOCK → max 2 sentences, BLOCK_SOFT → 3, CLARIFY → 5,
    EXECUTE_WITH_CAUTION → unlimited (0).

    Returns (truncated_guidance, max_sentences_applied).
    """
    max_sentences = MAX_ENRICHMENT_SENTENCES.get(s_decision, 0)
    if max_sentences == 0 or not guidance:
        return (guidance, max_sentences)

    # Split on sentence boundaries (., !, ?, Arabic period)
    sentences = re.split(r'(?<=[.!?。])\s+', guidance)
    if len(sentences) <= max_sentences:
        return (guidance, max_sentences)

    truncated = " ".join(sentences[:max_sentences])
    return (truncated, max_sentences)


# ═══════════════════════════════════════════════════════════════
#  Root A Signal Detection
# ═══════════════════════════════════════════════════════════════

def detect_root_a_signals(text: str) -> List[RootSignal]:
    """
    Detect psychological / distress-origin signals in text.

    Returns list of (signal_type, evidence, strength) as RootSignal objects.
    Pure keyword/pattern detection — no embeddings, no LLM.
    """
    norm = normalize_arabic(text)
    signals: List[RootSignal] = []
    seen_types: set = set()

    for signal_type, markers in ROOT_A_TYPES.items():
        matched_evidence = []
        for marker in markers:
            marker_lower = marker.lower()
            if marker_lower in norm:
                matched_evidence.append(marker)

        if matched_evidence:
            is_strong = any(
                m.lower() in norm
                for m_list in [ROOT_A_STRONG_MARKERS_AR, ROOT_A_STRONG_MARKERS_EN]
                for m in m_list
                if m.lower() in [e.lower() for e in matched_evidence]
            )
            strength = ROOT_STRONG_SIGNAL_WEIGHT if is_strong else ROOT_WEAK_SIGNAL_WEIGHT

            if signal_type not in seen_types:
                signals.append(RootSignal(
                    signal_type=signal_type,
                    evidence=matched_evidence,
                    strength=strength,
                ))
                seen_types.add(signal_type)

    return signals


# ═══════════════════════════════════════════════════════════════
#  Root B Signal Detection
# ═══════════════════════════════════════════════════════════════

def detect_root_b_signals(text: str) -> List[RootSignal]:
    """
    Detect ethical-drift / justification signals in text.

    Returns list of (signal_type, evidence, strength) as RootSignal objects.
    Pure keyword/pattern detection — no embeddings, no LLM.
    """
    norm = normalize_arabic(text)
    signals: List[RootSignal] = []
    seen_types: set = set()

    for signal_type, markers in ROOT_B_TYPES.items():
        matched_evidence = []
        for marker in markers:
            marker_lower = marker.lower()
            if marker_lower in norm:
                matched_evidence.append(marker)

        if matched_evidence:
            is_explicit = any(
                m.lower() in norm
                for m_list in [ROOT_B_MARKERS_AR, ROOT_B_MARKERS_EN]
                for m in m_list
                if m.lower() in [e.lower() for e in matched_evidence]
            )
            strength = ROOT_STRONG_SIGNAL_WEIGHT if is_explicit else ROOT_WEAK_SIGNAL_WEIGHT

            if signal_type not in seen_types:
                signals.append(RootSignal(
                    signal_type=signal_type,
                    evidence=matched_evidence,
                    strength=strength,
                ))
                seen_types.add(signal_type)

    return signals


# ═══════════════════════════════════════════════════════════════
#  Co-Occurrence Detection (Fix 1: renamed from Cross-Causal)
# ═══════════════════════════════════════════════════════════════

def detect_co_occurrence(
    text: str,
    root_a: List[RootSignal],
    root_b: List[RootSignal],
) -> Tuple[str, List[str]]:
    """
    Detect co-occurrence relationship between Root A and Root B.

    Evidence-bounded: only claims a temporal direction when explicit language
    supports it. NOT a causal claim — observational co-occurrence only.
    Default: "co_present_direction_unclear" when both present.

    Returns (co_occurrence_value, evidence_list).
    """
    if not root_a or not root_b:
        return ("none", [])

    norm = normalize_arabic(text)
    evidence: List[str] = []

    # Check A precedes B direction (distress preceded the harmful impulse)
    a_precedes_found = False
    for marker in CO_OCCURRENCE_A_PRECEDES_B_AR + CO_OCCURRENCE_A_PRECEDES_B_EN:
        if marker.lower() in norm:
            evidence.append(f"a→b: {marker}")
            a_precedes_found = True

    if a_precedes_found:
        return ("a_precedes_b", evidence)

    # Check B precedes A direction (harmful action preceded distress)
    b_precedes_found = False
    for marker in CO_OCCURRENCE_B_PRECEDES_A_AR + CO_OCCURRENCE_B_PRECEDES_A_EN:
        if marker.lower() in norm:
            evidence.append(f"b→a: {marker}")
            b_precedes_found = True

    if b_precedes_found:
        return ("b_precedes_a", evidence)

    return ("co_present_direction_unclear", [])


# Backward compatibility alias
def detect_cross_causal(
    text: str,
    root_a: List[RootSignal],
    root_b: List[RootSignal],
) -> Tuple[str, List[str]]:
    """Backward compatibility wrapper — calls detect_co_occurrence."""
    return detect_co_occurrence(text, root_a, root_b)


# ═══════════════════════════════════════════════════════════════
#  POM Trace Construction
# ═══════════════════════════════════════════════════════════════

def build_pom_trace(
    text: str,
    root_a: List[RootSignal],
    root_b: List[RootSignal],
) -> Dict[str, str]:
    """
    Build the Pain-Origin Mapper trace — signal semantics, NOT clinical.

    Keys: event_signal, meaning_signal, distress_signal, belief_signal,
          behavior_signal.

    Values are extracted from the text evidence. Empty string when
    no signal is found for that slot.
    """
    trace: Dict[str, str] = {
        "event_signal": "",
        "meaning_signal": "",
        "distress_signal": "",
        "belief_signal": "",
        "behavior_signal": "",
    }

    if root_a:
        best_a = max(root_a, key=lambda s: s.strength)
        if best_a.evidence:
            trace["event_signal"] = best_a.evidence[0]
        trace["distress_signal"] = best_a.signal_type

    if root_b:
        best_b = max(root_b, key=lambda s: s.strength)
        if best_b.evidence:
            trace["behavior_signal"] = best_b.evidence[0]
        trace["belief_signal"] = best_b.signal_type

    # meaning_signal: bridge between distress and behavior
    if root_a and root_b:
        trace["meaning_signal"] = "distress_channeled_to_harmful_impulse"
    elif root_a:
        trace["meaning_signal"] = "distress_without_harmful_channeling"
    elif root_b:
        trace["meaning_signal"] = "harmful_impulse_without_visible_distress"

    return trace


# ═══════════════════════════════════════════════════════════════
#  Response Guidance Generation
# ═══════════════════════════════════════════════════════════════

def generate_response_guidance(analysis: DualRootAnalysis) -> str:
    """
    Generate response guidance string based on enrichment mode.

    This is a TEMPLATE — the response shaper decides actual wording.
    """
    mode = analysis.enrichment_mode
    if mode in GUIDANCE_TEMPLATES:
        return GUIDANCE_TEMPLATES[mode]
    return ""


# ═══════════════════════════════════════════════════════════════
#  Distress Authenticity Check (Stage 2)
# ═══════════════════════════════════════════════════════════════

def _check_distress_authenticity(text: str) -> bool:
    """
    Stage 2 of the activation gate: distress authenticity.

    Returns True if ≥1 strong distress marker OR ≥2 weak distress markers.
    Fix 4: negated markers (e.g. "ما ابغى اموت") are skipped.
    """
    norm = normalize_arabic(text)
    strong_count = 0
    weak_count = 0

    for marker in ROOT_A_STRONG_MARKERS_AR + ROOT_A_STRONG_MARKERS_EN:
        marker_lower = marker.lower()
        pos = norm.find(marker_lower)
        if pos != -1:
            # Fix 4: skip if preceded by negation
            if _has_negation_prefix(norm, pos):
                continue
            strong_count += 1
            if strong_count >= STRONG_DISTRESS_THRESHOLD:
                return True

    for marker in ROOT_A_WEAK_MARKERS_AR + ROOT_A_WEAK_MARKERS_EN:
        marker_lower = marker.lower()
        pos = norm.find(marker_lower)
        if pos != -1:
            if _has_negation_prefix(norm, pos):
                continue
            weak_count += 1
            if weak_count >= WEAK_DISTRESS_THRESHOLD:
                return True

    return False


# ═══════════════════════════════════════════════════════════════
#  Harmful Moral Drift Check (Stage 3)
# ═══════════════════════════════════════════════════════════════

def _check_harmful_moral_drift(text: str) -> bool:
    """
    Stage 3 of the activation gate: harmful moral drift signal.

    Returns True if explicit harm intent/request OR ethical drift phrase + target.
    """
    norm = normalize_arabic(text)

    # Check explicit Root B markers
    for marker in ROOT_B_MARKERS_AR + ROOT_B_MARKERS_EN:
        if marker.lower() in norm:
            return True

    # Arabic drift phrases are self-contained (pronoun suffix = target)
    for phrase in ETHICAL_DRIFT_PHRASES_AR:
        if phrase.lower() in norm:
            return True

    # English drift phrases need a separate target co-occurrence
    has_en_drift = False
    for phrase in ETHICAL_DRIFT_PHRASES_EN:
        if phrase.lower() in norm:
            has_en_drift = True
            break

    if has_en_drift:
        for target in HARM_TARGET_MARKERS:
            if target.lower() in norm:
                return True

    return False


# ═══════════════════════════════════════════════════════════════
#  Three-Stage Activation Gate
# ═══════════════════════════════════════════════════════════════

def should_activate_dre(ctx: DREContext) -> Tuple[bool, str]:
    """
    Four-stage activation gate for DRE.

    Stage 0: Fiction/roleplay exclusion (Fix 6)
    Stage 1: Safety relevance (S_decision, H range, false goodness, malicious)
    Stage 2: Distress authenticity (strong/weak distress markers)
    Stage 3: Harmful moral drift (Root B markers or drift+target)

    Returns (should_activate, reason).
    DRE activates when all stages pass: Stage 0 clean, Stage 1 passes,
    AND (Stage 2 OR Stage 3 passes).
    Graceful degradation: single-root enrichment when only one stage passes.
    """
    # ── Stage 0: Fiction/roleplay exclusion (Fix 6) ─────────
    if _check_fiction_context(ctx.text):
        return (False, "fiction_or_roleplay_context")

    # ── Stage 1: Safety relevance ────────────────────────────
    if ctx.s_decision in EXCLUDED_S_DECISIONS:
        return (False, f"excluded_s_decision:{ctx.s_decision}")

    if ctx.false_goodness_detected:
        return (False, "false_goodness_guard")

    # Fix 5: Enhanced false goodness detection — check indicators in text
    if _check_false_goodness(ctx.text, ctx.s_decision):
        return (False, "false_goodness_indicators_detected")

    if ctx.intent_malicious_confidence >= MALICIOUS_INTENT_THRESHOLD:
        return (False, "malicious_intent_exclusion")

    if ctx.query_type in FACTUAL_QUERY_TYPES:
        return (False, f"factual_query:{ctx.query_type}")

    if not (H_RANGE_MIN <= ctx.H <= H_RANGE_MAX):
        return (False, f"H_out_of_range:{ctx.H:.2f}")

    if ctx.s_decision not in ELIGIBLE_S_DECISIONS:
        return (False, f"ineligible_s_decision:{ctx.s_decision}")

    # Five-layer check (if available)
    if ctx.five_layer_detected is not None:
        has_relevant = any(
            layer in DRE_RELEVANT_LAYERS
            for layer in ctx.five_layer_detected
        )
        if not has_relevant:
            return (False, "no_relevant_five_layer")

    # ── Stage 2: Distress authenticity ───────────────────────
    has_distress = _check_distress_authenticity(ctx.text)

    # ── Stage 3: Harmful moral drift ────────────────────────
    has_drift = _check_harmful_moral_drift(ctx.text)

    if not has_distress and not has_drift:
        return (False, "no_distress_and_no_drift")

    # At least one stage passed — DRE activates
    if has_distress and has_drift:
        return (True, "dual_root_both_stages")
    elif has_distress:
        return (True, "distress_only")
    else:
        return (True, "drift_only")


# ═══════════════════════════════════════════════════════════════
#  Single Mind Invariant Validation
# ═══════════════════════════════════════════════════════════════

def validate_single_mind(
    analysis: DualRootAnalysis,
    s_decision: str,
    original_H: Optional[float] = None,
    original_I: Optional[float] = None,
    original_E: Optional[float] = None,
) -> List[str]:
    """
    Meta-Oversight integration: validate all 7 Single Mind invariants.

    Returns list of violation descriptions. Empty list = all invariants hold.
    """
    violations: List[str] = []

    # Invariant 1: S-decision immutability — DRE should not have modified anything
    # (checked externally by comparing before/after, but we validate the analysis)

    # Invariant 3: Boundary preservation — if DRE is active, guidance must exist
    if analysis.dre_active and analysis.enrichment_mode == "dual_root":
        if not analysis.response_guidance:
            violations.append("invariant_3: active dual_root but no response_guidance")

    # Invariant 4: No causal certainty — check prohibited_claims populated
    if analysis.dre_active and not analysis.prohibited_claims:
        violations.append("invariant_4: active but prohibited_claims empty")

    # Fix 10: Invariant 4 extended — scan all output fields for causal language
    if analysis.dre_active:
        fields_to_check = [
            ("response_guidance", analysis.response_guidance),
            ("enrichment_mode", analysis.enrichment_mode),
            ("co_occurrence_type", analysis.co_occurrence_type),
        ]
        for field_name, field_value in fields_to_check:
            causal_terms = _check_no_causal_language(field_value)
            if causal_terms:
                violations.append(
                    f"invariant_4: causal language {causal_terms} in {field_name}"
                )

    # Invariant 5: Meta-Oversight audit — clinical labels check
    guidance_lower = analysis.response_guidance.lower()
    for term in CLINICAL_PROHIBITED_TERMS:
        if term.lower() in guidance_lower:
            violations.append(
                f"invariant_5: clinical term '{term}' in response_guidance"
            )

    # Invariant 6: False Goodness guard
    # (enforced in activation gate, but double-check)

    # Invariant 7: Malicious intent exclusion
    # (enforced in activation gate, but double-check)

    # Invariant 8: Authority Preservation (Fix 9)
    if analysis.dre_active and s_decision in ("BLOCK", "BLOCK_SOFT"):
        max_s = MAX_ENRICHMENT_SENTENCES.get(s_decision, 0)
        if max_s > 0 and analysis.response_guidance:
            sentences = re.split(r'(?<=[.!?。])\s+', analysis.response_guidance)
            if len(sentences) > max_s:
                violations.append(
                    f"invariant_8: guidance has {len(sentences)} sentences, "
                    f"max {max_s} for {s_decision}"
                )

    return violations


# ═══════════════════════════════════════════════════════════════
#  Main Entry Point
# ═══════════════════════════════════════════════════════════════

def analyze_dual_root(text: str, ctx: DREContext) -> DualRootAnalysis:
    """
    Main entry point for Dual-Root Reconstruction Engine.

    Detects dual psychological+ethical root patterns and generates
    response enrichment guidance. NEVER touches S/H/θ/I/E.

    Args:
        text: the user message to analyze.
        ctx: DREContext with pipeline state (S_decision, H, etc.).

    Returns:
        DualRootAnalysis with all detected signals and guidance.
    """
    analysis = DualRootAnalysis(
        enabled=DRE_ENABLED,
        monitor_only=DRE_MONITOR_ONLY,
        prohibited_claims=list(DEFAULT_PROHIBITED_CLAIMS),
    )

    # Feature flag guard
    if not DRE_ENABLED:
        analysis.activation_reason = "DRE_ENABLED=False"
        return analysis

    # ── Three-stage activation gate ──────────────────────────
    should_activate, reason = should_activate_dre(ctx)
    analysis.activation_reason = reason

    if not should_activate:
        return analysis

    analysis.dre_active = True

    # ── Root A detection ─────────────────────────────────────
    root_a_signals = detect_root_a_signals(text)
    if root_a_signals:
        analysis.root_a_signal_detected = True
        best_a = max(root_a_signals, key=lambda s: s.strength)
        analysis.root_a_signal_type = best_a.signal_type
        analysis.root_a_evidence = [
            e for s in root_a_signals for e in s.evidence
        ]
        analysis.root_a_strength = best_a.strength

    # ── Root B detection ─────────────────────────────────────
    root_b_signals = detect_root_b_signals(text)
    if root_b_signals:
        analysis.root_b_signal_detected = True
        best_b = max(root_b_signals, key=lambda s: s.strength)
        analysis.root_b_signal_type = best_b.signal_type
        analysis.root_b_evidence = [
            e for s in root_b_signals for e in s.evidence
        ]
        analysis.root_b_strength = best_b.strength

    # ── Enrichment mode (graceful degradation) ───────────────
    if analysis.root_a_signal_detected and analysis.root_b_signal_detected:
        analysis.enrichment_mode = "dual_root"
        analysis.dual_root_pattern_detected = True
        analysis.pattern_confidence = min(
            1.0,
            (analysis.root_a_strength + analysis.root_b_strength) / 2.0,
        )
    elif analysis.root_a_signal_detected:
        analysis.enrichment_mode = "distress_boundary"
        analysis.pattern_confidence = analysis.root_a_strength * 0.6
    elif analysis.root_b_signal_detected:
        analysis.enrichment_mode = "ethical_boundary"
        analysis.pattern_confidence = analysis.root_b_strength * 0.6
    else:
        analysis.enrichment_mode = ""
        analysis.dre_active = False
        analysis.activation_reason = "no_signals_after_detection"
        return analysis

    analysis.activation_confidence = analysis.pattern_confidence

    # ── Co-occurrence detection (Fix 1: renamed from cross-causal) ──
    analysis.co_occurrence_type, analysis.co_occurrence_evidence = detect_co_occurrence(
        text, root_a_signals, root_b_signals,
    )

    # ── POM trace construction ───────────────────────────────
    analysis.pom_trace = build_pom_trace(text, root_a_signals, root_b_signals)

    # ── Response guidance generation ─────────────────────────
    analysis.response_guidance = generate_response_guidance(analysis)

    # ── Fix 6: Mark fiction context in result ────────────────
    analysis.fiction_or_roleplay_context = _check_fiction_context(text)

    # ── Fix 5: Mark false goodness in result ─────────────────
    analysis.false_goodness_flag = _check_false_goodness(text, ctx.s_decision)

    # ── Fix 9: Apply authority preservation sentence limits ──
    analysis.response_guidance, analysis.max_enrichment_sentences = (
        _apply_authority_preservation(analysis.response_guidance, ctx.s_decision)
    )

    # ── Fix 10: Invariant 4 enforcement — raise on causal language ──
    causal_in_guidance = _check_no_causal_language(analysis.response_guidance)
    if causal_in_guidance:
        raise InvariantViolation(
            f"invariant_4: causal language {causal_in_guidance} in response_guidance"
        )

    return analysis
