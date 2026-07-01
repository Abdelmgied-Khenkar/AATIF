"""
AATIF LBH Detector -- FN#054 Low-Barrier Humanity Principle

Architecture: B-prime (B')
---------------------------------------------------------------------
LBHDetector      ->  observational (outputs LBHReading + evidence)
R Equation       ->  stylistic (uses LBH reading for response shaping via G_eff)

Critical Design Rule (Single Mind):
  Only GovernanceEquation makes SAFETY decisions. FN#054 is STYLISTIC,
  NOT safety. LBHDetector never touches S, H, theta, or the GovernanceEquation.
  It binds through B5 (Behaviour), NOT B6 (Safety). It says "the draft
  response contains sermonizing -- confidence 0.80, recommend reframe."
  It decides nothing about whether a request is allowed.

  LBH is not compassion. LBH is structural respect.

  "Assume the human is trying -- unless explicit evidence proves otherwise."
  "Failure is NEVER attributed to lack of will, effort, or character
   without verified proof."

This module scans DRAFT OUTPUT (what the LLM is about to say), NOT user
input. The markers are things the AI should NOT say to the human.

Scientific backing:
  - Pasch 2025: sermonizing responses win only 8% vs 36% for normal
  - Raimi et al., MIS Quarterly 2025: judgmental chatbot reduces disclosure

Design consensus: Claude, 2026-07-01
Field Note: FN#054 (Low-Barrier Humanity Principle)

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:  # pragma: no cover -- import shim for both package and flat layouts
    from aatif_arabic_utils import normalize_arabic
except Exception:  # pragma: no cover
    def normalize_arabic(text: str) -> str:
        return text.lower()


# =====================================================================
#  Feature Flags  (FN#054 ships ON by default)
# =====================================================================

LBH_ENABLED = True               # master switch for the LBH pipeline
LBH_MONITOR_ONLY = False          # when True, detect but never recommend reframe


# =====================================================================
#  Authority Level Declaration (B-prime contract)
# =====================================================================

AUTHORITY_LEVEL = "B_PRIME_OBSERVATIONAL"
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA            = False
CAN_MODIFY_S                = False
CAN_EMIT_JUDICIAL_DECISION = False


# =====================================================================
#  LBH Violation Types  (FN#054 -- five prohibitions)
# =====================================================================

class LBHViolationType(enum.Enum):
    """The five prohibitions of LBH (ma yumna' / ما يُمنع)."""
    SERMONIZING        = "sermonizing"          # الوعظ التحفيزي
    DEFICIT_ATTRIBUTION = "deficit_attribution"  # عزو الفشل للإرادة
    ELITE_PROJECTION   = "elite_projection"     # إسقاط تجارب النخبة
    ABSTRACT_SUCCESS   = "abstract_success"     # قصص نجاح مجردة
    COMPARISON_BENCHMARK = "comparison_benchmark"  # المقارنة بالمتفوقين


# =====================================================================
#  Constants -- calibration values
# =====================================================================

# Detection thresholds
FAST_PATH_MAX_CHARS = 30          # texts shorter than this with no markers -> skip
SINGLE_MARKER_BASE_CONFIDENCE = 0.50   # one marker alone
MULTI_MARKER_COMPOUND_BONUS = 0.15     # each additional marker adds confidence
MAX_CONFIDENCE = 0.95
VIOLATION_SCORE_THRESHOLD = 0.40       # below this, structural respect is maintained
EDUCATION_DOMAIN_MODIFIER = -0.10      # education domain is slightly more tolerant

# Per-violation-type base severity (some are worse than others)
VIOLATION_SEVERITY: Dict[LBHViolationType, float] = {
    LBHViolationType.SERMONIZING:          0.55,
    LBHViolationType.DEFICIT_ATTRIBUTION:  0.70,  # worst -- blames the human
    LBHViolationType.ELITE_PROJECTION:     0.60,
    LBHViolationType.ABSTRACT_SUCCESS:     0.45,
    LBHViolationType.COMPARISON_BENCHMARK: 0.55,
}


# =====================================================================
#  Marker Lists -- Arabic (Gulf / Levantine / Egyptian) + English
# =====================================================================
#
#  These are phrases the AI SHOULD NOT say. They are scanned against
#  draft output, not user input.

# -- 1. SERMONIZING (الوعظ التحفيزي) ----------------------------------

SERMONIZING_MARKERS_AR = [
    # Gulf dialect
    "لازم تجتهد", "لازم تجتهدي",
    "لازم تشتغل على نفسك", "لازم تشتغلي على نفسك",
    "عشان تنجح", "عشان تنجحي",
    "حاول أكثر", "حاولي أكثر",
    "حاول مره ثانيه", "حاولي مره ثانيه",
    "جاهد أكثر", "جاهدي أكثر",
    "الناجحون", "الناجحين",
    "لا تستسلم", "لا تستسلمي",
    "ما فيه مستحيل", "ما في مستحيل",
    "اصبر وبتشوف النتيجة", "اصبري وبتشوفين النتيجة",
    "ثق بنفسك", "ثقي بنفسك",
    "آمن بقدراتك", "آمني بقدراتك",
    "كل شي يبدأ بخطوة", "كل شيء يبدا بخطوه",
    "اللي يبي النجاح",
    "النجاح يحتاج تضحية", "النجاح يحتاج تضحيه",
    "اللي ما يتعب ما يحصل شي",
    "شد حيلك", "شدي حيلك",
    "ما ودك تنجح", "ما تبي تنجح",
    "قوي عزيمتك", "قوي ارادتك",
    # Levantine dialect
    "لازم تتعب", "لازم تتعبي",
    "بدك تشتغل اكتر", "بدك تشتغلي اكتر",
    "ما بتنجح اذا ما اجتهدت",
    "عليك تجتهد", "عليكي تجتهدي",
    "ما رح تنجح بدون تعب",
    "ما رح توصل اذا ما تعبت",
    "يلا قوم اشتغل", "يلا قومي اشتغلي",
    "النجاح بده جهد",
    # Egyptian dialect
    "لازم تشتغل اكتر", "لازم تشتغلي اكتر",
    "محتاج تبذل مجهود", "محتاجه تبذلي مجهود",
    "اللي عايز ينجح",
    "ما حدش بينجح من غير تعب",
    "اتعب عشان توصل",
    "كفاية كسل", "كفايه كسل",
    "النجاح مش سهل",
    "اجتهد شوية", "اجتهدي شويه",
    # MSA / formal
    "يجب أن تجتهد", "يجب عليك",
    "عليك بالاجتهاد", "عليك بالمثابرة",
    "من جد وجد", "من زرع حصد",
    "الجهد هو المفتاح",
    "لا تيأس", "لا تيأسي",
    "واصل المحاولة", "واصلي المحاولة",
]

SERMONIZING_MARKERS_EN = [
    "you just need to", "you simply need to",
    "you need to work harder", "you need to try harder",
    "you have to push yourself", "push yourself harder",
    "successful people", "winners always",
    "if you really wanted to", "if you really want to",
    "you can do anything", "you can achieve anything",
    "believe in yourself", "just believe",
    "never give up", "don't give up",
    "the only limit is yourself", "the only thing stopping you",
    "you have the power to", "you have it in you",
    "stay motivated", "stay positive",
    "keep pushing", "keep grinding",
    "hard work pays off", "hard work always",
    "no pain no gain",
    "just put in the effort", "just put in the work",
    "you can do it if you try", "try harder",
    "don't be lazy", "stop being lazy",
    "where there's a will", "where there is a will",
    "success requires sacrifice",
    "nothing worth having comes easy",
    "get out of your comfort zone",
    "stop making excuses",
    "no excuses",
    "hustle harder",
    "rise and grind",
]

# -- 2. DEFICIT ATTRIBUTION (عزو الفشل للإرادة) -----------------------

DEFICIT_ATTRIBUTION_MARKERS_AR = [
    # Gulf
    "لو كنت ملتزم", "لو كنتي ملتزمه",
    "لو كنت جاد", "لو كنتي جاده",
    "المشكلة فيك", "المشكلة في تفكيرك", "المشكلة في التزامك",
    "اللي يبي ينجح ما يتكاسل",
    "ما عندك عزيمة", "ما عندك ارادة",
    "لو تبي فعلا", "لو تبين فعلا",
    "ما تبذل جهد كافي", "ما تبذلين جهد كافي",
    "عيبك انك", "عيبك إنك",
    "مشكلتك انك",
    "ما اجتهدت بما فيه الكفاية",
    "لو كنت اشتغلت",
    "عشان ما اجتهدت", "لانك ما اجتهدت",
    "تحتاج تغير تفكيرك",
    # Levantine
    "المشكلة بعقليتك", "المشكله بعقليتك",
    "لو كنت اشتغلت اكتر",
    "لانك ما بتتعب",
    "انت السبب", "انتي السبب",
    "بسببك", "بسبب كسلك",
    # Egyptian
    "لو كنت اتعبت", "لو كنتي اتعبتي",
    "المشكله في حماسك",
    "انت مش بتحاول", "انتي مش بتحاولي",
    "عشان مش بتشتغل",
    "دماغك هي المشكله",
    # MSA / formal
    "بسبب عدم التزامك",
    "لعدم بذل الجهد الكافي",
    "لأنك لم تجتهد", "لانك لم تجتهد",
    "العيب في إرادتك",
    "ينقصك العزم", "ينقصك الإرادة",
    "لو كنت أكثر جدية",
]

DEFICIT_ATTRIBUTION_MARKERS_EN = [
    "the problem is your mindset",
    "you're not trying hard enough",
    "you're not putting in the effort",
    "if you were committed", "if you were serious",
    "you lack discipline", "you lack motivation",
    "you're not dedicated enough",
    "it's because you didn't try",
    "if you had worked harder",
    "the issue is your attitude",
    "you need to change your mindset",
    "the problem is you",
    "your lack of effort",
    "you don't want it badly enough",
    "you're making excuses",
    "you chose not to",
    "it's your own fault",
    "you have no one to blame but yourself",
    "you didn't commit",
    "because you gave up",
    "you just don't care enough",
    "your failure is because",
    "if you had been more disciplined",
    "you're holding yourself back",
    "if you really wanted it",
    "try hard enough",
    "work harder",
]

# -- 3. ELITE PROJECTION (إسقاط تجارب النخبة) -------------------------

ELITE_PROJECTION_MARKERS_AR = [
    # Gulf
    "الناجحون يستيقظون مبكرا", "الناجحين يستيقظون مبكرا",
    "الناجحون يصحون بدري", "الناجحين يصحون بدري",
    "يصحون الساعة خمس", "يصحون الساعه خمس",
    "قوم بدري مثلهم",
    "المدراء التنفيذيون", "المدراء التنفيذيين",
    "عادات الاثرياء", "عادات الأثرياء",
    "تعلم من الأغنياء",
    "روتين الناجحين", "روتين الناجحون",
    "اقرا ٥٠ كتاب بالسنة", "اقرأ ٥٠ كتاب",
    "اصحى بدري", "اصحي بدري",
    "خلك مثل فلان",
    # Levantine
    "فوت بكير متل الناجحين",
    "هيك بعملو الناجحين",
    "لازم تعمل متل المديرين",
    # Egyptian
    "الناجحين بيصحوا بدري",
    "اعمل زي الناجحين",
    "شوف الناجحين بيعملوا ايه",
    "اتعلم من اللي نجحوا",
    # MSA / formal
    "القادة يستيقظون قبل الفجر",
    "رواد الأعمال الناجحون",
    "عادات القادة", "سمات القادة",
    "روتين المليونيرات",
    "عادات الشخصيات الناجحة",
    "كما يفعل الناجحون",
    "كتاب بالسنة", "كتاب بالسنه",
]

ELITE_PROJECTION_MARKERS_EN = [
    "successful people wake up early",
    "ceo morning routines", "ceo morning routine",
    "wake up at 5am", "wake up at 4am", "wake up at 5 am",
    "hustle culture", "grind culture",
    "billionaires read", "millionaires read",
    "habits of successful people",
    "habits of the rich", "habits of wealthy people",
    "successful entrepreneurs always",
    "top performers", "high performers always",
    "like elon musk", "like steve jobs", "like jeff bezos",
    "morning routine of", "daily routine of",
    "read 50 books a year", "read a book a week",
    "the rich do this", "wealthy people do this",
    "elite athletes", "world-class performers",
    "that's what successful people do",
    "take cold showers", "cold shower every morning",
    "meditate every morning", "journal every morning",
    "elon musk", "steve jobs", "jeff bezos",
]

# -- 4. ABSTRACT SUCCESS (قصص نجاح مجردة) -----------------------------

ABSTRACT_SUCCESS_MARKERS_AR = [
    # Gulf
    "كلنا نقدر ننجح", "كلنا نقدر نوصل",
    "اي واحد يقدر", "اي احد يقدر",
    "المستحيل غير موجود", "ما في مستحيل",
    "الطريق مفتوح للجميع",
    "النجاح متاح للكل", "النجاح متاح للجميع",
    "ما فيه شي صعب",
    "كل شي ممكن", "كل شيء ممكن",
    "لا شيء مستحيل", "لا شي مستحيل",
    "حدودك من صنعك", "حدودك من صنع خيالك",
    "الامكانيات لا حدود لها",
    # Levantine
    "كلنا منقدر", "اي حدا بيقدر",
    "ما في اشي مستحيل",
    "كل شي بيتحقق",
    # Egyptian
    "كلنا نقدر", "اي حد يقدر",
    "مفيش حاجه مستحيله", "مفيش حاجة مستحيلة",
    "كل حاجه ممكنه", "كل حاجة ممكنة",
    # MSA / formal
    "النجاح في متناول الجميع",
    "ليس هناك مستحيل",
    "كل إنسان قادر على النجاح",
    "الفرص متاحة للجميع",
    "لا حدود لما يمكنك تحقيقه",
    "أنت تستطيع تحقيق أي شيء",
]

ABSTRACT_SUCCESS_MARKERS_EN = [
    "anyone can make it", "anyone can succeed",
    "nothing is impossible", "impossible is nothing",
    "the sky is the limit", "sky's the limit",
    "you can be anything you want",
    "the only limit is your imagination",
    "dream big", "dream bigger",
    "anything is possible",
    "success is available to everyone",
    "everyone has equal opportunity",
    "if you can dream it you can do it",
    "there are no limits",
    "the world is your oyster",
    "opportunities are everywhere",
    "you can achieve whatever you set your mind to",
    "just set your mind to it",
    "manifest your success", "manifest your dreams",
    "the universe rewards",
    "just follow your passion",
    "follow your dreams and everything will work out",
]

# -- 5. COMPARISON BENCHMARK (المقارنة بالمتفوقين) --------------------

COMPARISON_BENCHMARK_MARKERS_AR = [
    # Gulf
    "شف فلان كيف نجح", "شوفي فلانه كيف نجحت",
    "شف كيف فلان",
    "لو هم يقدرون", "لو هم يقدرون انت بعد تقدر",
    "فلان نجح وهو أصعب منك",
    "فلان بدأ من الصفر", "فلان بدا من الصفر",
    "ترا فلان كان أسوأ منك",
    "غيرك قدر ليش ما تقدر",
    "غيرك ما استسلم", "غيرك ما استسلموا",
    "الناس اللي نجحوا ما كانوا",
    "خلك مثل فلان", "كن مثل فلان",
    "شف وش سوا فلان",
    # Levantine
    "شوف فلان كيف عمل",
    "هداك نجح ليش ما بتنجح",
    "اذا هو قدر انت بتقدر",
    "غيرك عمل هيك وصار",
    # Egyptian
    "شوف فلان عمل ايه",
    "غيرك نجح ليه مش انت",
    "لو هو قدر انت كمان تقدر",
    "فلان كان اوحش منك ونجح",
    "بص على فلان",
    # MSA / formal
    "انظر كيف نجح فلان",
    "إذا استطاعوا فأنت تستطيع",
    "خذ فلانا قدوة",
    "قارن نفسك بمن نجح",
    "آخرون في ظروف أصعب نجحوا",
    "كثيرون بدؤوا من الصفر ونجحوا",
    "كتاب بالسنة", "كتاب بالسنه",
]

COMPARISON_BENCHMARK_MARKERS_EN = [
    "look at how x succeeded", "look at how they succeeded",
    "if they can do it", "if they could do it",
    "so and so started from nothing",
    "they had it worse than you",
    "others in your position have",
    "people with less have achieved more",
    "compared to others", "other people manage to",
    "why can't you do what they did",
    "they didn't give up so why should you",
    "take them as an example",
    "be more like", "you should be like",
    "look at what they achieved",
    "even they managed to",
    "if a kid from poverty can",
    "many people with worse circumstances",
    "others have overcome worse",
    "built his empire", "built their empire", "built an empire",
]


# =====================================================================
#  All markers grouped by violation type (for iteration)
# =====================================================================

MARKERS_BY_TYPE: Dict[LBHViolationType, Tuple[List[str], List[str]]] = {
    LBHViolationType.SERMONIZING:          (SERMONIZING_MARKERS_AR, SERMONIZING_MARKERS_EN),
    LBHViolationType.DEFICIT_ATTRIBUTION:  (DEFICIT_ATTRIBUTION_MARKERS_AR, DEFICIT_ATTRIBUTION_MARKERS_EN),
    LBHViolationType.ELITE_PROJECTION:     (ELITE_PROJECTION_MARKERS_AR, ELITE_PROJECTION_MARKERS_EN),
    LBHViolationType.ABSTRACT_SUCCESS:     (ABSTRACT_SUCCESS_MARKERS_AR, ABSTRACT_SUCCESS_MARKERS_EN),
    LBHViolationType.COMPARISON_BENCHMARK: (COMPARISON_BENCHMARK_MARKERS_AR, COMPARISON_BENCHMARK_MARKERS_EN),
}


# =====================================================================
#  Reframe recommendations -- what the R equation should inject
# =====================================================================
#
#  The four requirements of LBH (ma yulzam / ما يُلزَم):
#    1. Acknowledge unequal starting points
#    2. Respect silence and unannounced endurance
#    3. Realism before inspiration
#    4. Reduce pressure before suggesting growth

REFRAME_BY_TYPE: Dict[LBHViolationType, str] = {
    LBHViolationType.SERMONIZING: (
        "Remove motivational preaching. State facts, offer concrete help, "
        "or ask what the human needs. Reduce pressure before suggesting growth."
    ),
    LBHViolationType.DEFICIT_ATTRIBUTION: (
        "Remove blame framing. Failure is NEVER attributed to lack of will, "
        "effort, or character without verified proof. Acknowledge that the "
        "human is trying -- the system has no evidence otherwise."
    ),
    LBHViolationType.ELITE_PROJECTION: (
        "Remove elite experience projection. Not everyone has the same "
        "starting point, resources, or circumstances. Acknowledge unequal "
        "starting points before offering any advice."
    ),
    LBHViolationType.ABSTRACT_SUCCESS: (
        "Remove abstract success narratives. Replace with concrete, "
        "contextual suggestions. Realism before inspiration -- the human's "
        "situation may have structural barriers not visible to the system."
    ),
    LBHViolationType.COMPARISON_BENCHMARK: (
        "Remove comparison with high-achievers. Each person's path is "
        "unique. Respect silence and unannounced endurance -- the human "
        "may be carrying weight the system cannot see."
    ),
}

# General LBH reframe preamble injected into R equation
LBH_REFRAME_PREAMBLE = (
    "LBH violation detected in draft output. Structural respect requires: "
    "assume the human is trying, acknowledge unequal starting points, "
    "offer realism before inspiration, reduce pressure before suggesting growth."
)


# =====================================================================
#  Data Classes
# =====================================================================

@dataclass
class LBHViolation:
    """A single LBH violation found in draft output."""
    violation_type: LBHViolationType
    markers_found: List[str]
    confidence: float              # [0,1] per-violation confidence
    severity: float                # [0,1] how severe this violation is


@dataclass
class LBHReading:
    """
    Output of LBHDetector.detect() -- observational, STYLISTIC, NOT safety.

    This reading tells the R equation whether the draft output contains
    sermonizing, deficit-attribution, or other LBH violations and what
    kind of reframe is recommended. It never blocks, never modifies
    H/theta/S, and never makes safety decisions.
    """
    violations_detected: List[LBHViolation]
    overall_score: float                     # [0,1] where 0=respectful, 1=severely sermonizing
    structural_respect_maintained: bool      # True when overall_score < threshold
    recommendations: List[str]              # what the response should do instead
    evidence: List[str] = field(default_factory=list)


# =====================================================================
#  Small duck-typed accessors  (mirrors PVM/PSP pattern)
# =====================================================================

def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a key from dict, dataclass, or arbitrary object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _text_of(draft: Any) -> str:
    """Extract the text payload from draft (str, dict, or object)."""
    if draft is None:
        return ""
    if isinstance(draft, str):
        return draft
    return _get(draft, "text", "") or _get(draft, "content", "") or ""


# =====================================================================
#  LBHDetector -- observational, STYLISTIC, NOT safety
# =====================================================================

class LBHDetector:
    """
    Three-tier detection for Low-Barrier Humanity violations in draft output.

      Tier 1 -- marker matching      (cheap, high precision, always run)
      Tier 2 -- pattern analysis     (multiple markers compound severity)
      Tier 3 -- context sensitivity  (domain-aware threshold adjustment)

    The detector outputs an LBHReading. It does not generate response content,
    does not block responses, and does not touch S/H/theta. It recommends a
    reframe to the R equation through B5 (Behaviour).

    LBH is not compassion. LBH is structural respect.
    It is a design constraint, not a feeling.
    """

    def __init__(self,
                 violation_threshold: float = VIOLATION_SCORE_THRESHOLD,
                 education_modifier: float = EDUCATION_DOMAIN_MODIFIER):
        self.violation_threshold = violation_threshold
        self.education_modifier = education_modifier

    # -- Public API ---------------------------------------------------

    def detect(self,
               draft: Any,
               domain: Optional[str] = None) -> LBHReading:
        """
        Scan draft output for LBH violations.

        Parameters
        ----------
        draft : str | dict | object
            The draft output text. A bare string, or anything exposing
            ``text`` or ``content``.
        domain : str | None
            Domain context (e.g. "education", "general"). Education
            domain has slightly different thresholds -- it is more
            tolerant of some motivational language in pedagogical
            contexts, but never tolerant of deficit attribution.

        Returns
        -------
        LBHReading
            Observational reading with violations, score, and
            recommendations for the R equation.
        """
        text = _text_of(draft)
        norm, low = self._prep(text)
        evidence: List[str] = []

        # -- Sparse Activation: fast-path skip -------------------------
        if len(text.strip()) <= FAST_PATH_MAX_CHARS:
            has_any_marker = False
            for vtype, (markers_ar, markers_en) in MARKERS_BY_TYPE.items():
                if self._find(low, norm, markers_en, markers_ar):
                    has_any_marker = True
                    break
            if not has_any_marker:
                evidence.append(
                    f"fast_path_skip: text length={len(text.strip())} "
                    f"<= {FAST_PATH_MAX_CHARS} with no markers"
                )
                return LBHReading(
                    violations_detected=[],
                    overall_score=0.0,
                    structural_respect_maintained=True,
                    recommendations=[],
                    evidence=evidence,
                )

        # -- Tier 1: marker matching -----------------------------------
        violations: List[LBHViolation] = []

        for vtype, (markers_ar, markers_en) in MARKERS_BY_TYPE.items():
            hits = self._find(low, norm, markers_en, markers_ar)
            if hits:
                # Base confidence from severity + marker count
                base_severity = VIOLATION_SEVERITY[vtype]
                marker_count_bonus = min(
                    (len(hits) - 1) * MULTI_MARKER_COMPOUND_BONUS,
                    0.30  # cap the bonus
                )
                confidence = min(
                    SINGLE_MARKER_BASE_CONFIDENCE + marker_count_bonus,
                    MAX_CONFIDENCE
                )
                severity = min(base_severity + marker_count_bonus, MAX_CONFIDENCE)

                violations.append(LBHViolation(
                    violation_type=vtype,
                    markers_found=hits[:6],  # cap at 6 for readability
                    confidence=round(confidence, 3),
                    severity=round(severity, 3),
                ))
                evidence.append(
                    f"{vtype.value}: {len(hits)} marker(s) found "
                    f"({hits[:3]}...) -> conf={confidence:.2f}, "
                    f"sev={severity:.2f}"
                )

        # -- Tier 2: pattern analysis (compounding) --------------------
        #  Multiple violation TYPES compound the overall score.
        #  Sermonizing + deficit attribution is worse than either alone.

        if len(violations) == 0:
            evidence.append("no LBH violations detected")
            return LBHReading(
                violations_detected=[],
                overall_score=0.0,
                structural_respect_maintained=True,
                recommendations=[],
                evidence=evidence,
            )

        # Overall score: weighted average of severities, compounded
        # by number of distinct violation types
        total_severity = sum(v.severity for v in violations)
        avg_severity = total_severity / len(violations)
        # Compound factor: each additional violation type adds 10%
        compound_factor = 1.0 + 0.10 * (len(violations) - 1)
        overall_score = min(avg_severity * compound_factor, MAX_CONFIDENCE)

        evidence.append(
            f"tier2_compound: {len(violations)} violation type(s), "
            f"avg_sev={avg_severity:.2f}, compound={compound_factor:.2f}, "
            f"raw_score={overall_score:.2f}"
        )

        # -- Tier 3: context sensitivity (domain adjustment) -----------
        effective_threshold = self.violation_threshold
        if domain and domain.lower() == "education":
            # Education domain: more tolerant of SERMONIZING and
            # ABSTRACT_SUCCESS, but NEVER tolerant of DEFICIT_ATTRIBUTION
            has_deficit = any(
                v.violation_type == LBHViolationType.DEFICIT_ATTRIBUTION
                for v in violations
            )
            if not has_deficit:
                overall_score = max(0.0, overall_score + self.education_modifier)
                evidence.append(
                    f"tier3_domain: education modifier {self.education_modifier:+.2f} "
                    f"applied (no deficit attribution) -> score={overall_score:.2f}"
                )
            else:
                evidence.append(
                    "tier3_domain: education modifier NOT applied -- "
                    "deficit attribution is never tolerated"
                )

        overall_score = round(overall_score, 3)
        structural_respect = overall_score < effective_threshold

        # -- Build recommendations ------------------------------------
        recommendations: List[str] = []
        for v in violations:
            recommendations.append(REFRAME_BY_TYPE[v.violation_type])

        if LBH_MONITOR_ONLY:
            evidence.append(
                "LBH_MONITOR_ONLY=True -> recommendations are observational only"
            )

        return LBHReading(
            violations_detected=violations,
            overall_score=overall_score,
            structural_respect_maintained=structural_respect,
            recommendations=recommendations,
            evidence=evidence,
        )

    # -- Internal helpers ---------------------------------------------

    @staticmethod
    def _prep(text: str) -> Tuple[str, str]:
        """Return (normalized_arabic, lowercased) views of the text."""
        return normalize_arabic(text), text.lower()

    @staticmethod
    def _find(low: str, norm: str,
              markers_en: List[str], markers_ar: List[str]) -> List[str]:
        """Markers present in the text -- EN matched on lowercase, AR on normalized."""
        hits = [m for m in markers_en if m in low]
        hits += [m for m in markers_ar if normalize_arabic(m) in norm]
        return hits


# =====================================================================
#  Reframe recommendation for R equation
# =====================================================================

def recommend_reframe(reading: LBHReading) -> str:
    """
    Build a reframe recommendation string for the R equation to inject
    into the governed prompt when LBH violations are detected.

    Parameters
    ----------
    reading : LBHReading
        The detection result from LBHDetector.detect().

    Returns
    -------
    str
        A recommendation string. Empty if no violations or if structural
        respect is maintained and monitor-only mode is off.
    """
    if not reading.violations_detected:
        return ""

    if reading.structural_respect_maintained and not LBH_MONITOR_ONLY:
        # Below threshold and not in monitor mode -- minor violations
        # don't need active reframing, but we note them
        violation_names = [v.violation_type.value for v in reading.violations_detected]
        return (
            f"[LBH note] Minor markers detected ({', '.join(violation_names)}) "
            f"at score {reading.overall_score:.2f} (below threshold "
            f"{VIOLATION_SCORE_THRESHOLD:.2f}). Structural respect maintained. "
            f"No reframe required, but prefer concrete help over motivational language."
        )

    # Active reframe needed
    parts = [LBH_REFRAME_PREAMBLE]
    parts.append(f"Overall LBH score: {reading.overall_score:.2f}")

    for v in reading.violations_detected:
        parts.append(
            f"  [{v.violation_type.value}] (conf={v.confidence:.2f}, "
            f"sev={v.severity:.2f}): {REFRAME_BY_TYPE[v.violation_type]}"
        )

    return "\n".join(parts)


# =====================================================================
#  Audit helper -- SHA256 for evidence integrity
# =====================================================================

def lbh_audit_hash(reading: LBHReading) -> str:
    """
    SHA256 of the LBH reading for audit integrity.

    Same pattern as PVM's audit hash -- trace integrity without
    storing raw content.
    """
    payload = json.dumps({
        "overall_score": reading.overall_score,
        "structural_respect_maintained": reading.structural_respect_maintained,
        "violation_count": len(reading.violations_detected),
        "violation_types": [v.violation_type.value for v in reading.violations_detected],
        "evidence_count": len(reading.evidence),
    }, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# =====================================================================
#  Self-test -- quick validation  (python engine/aatif_lbh_detector.py)
# =====================================================================

def _self_test() -> None:
    """Minimal smoke test for LBH detection."""
    d = LBHDetector()

    cases = [
        # (text, expected_label, should_have_violations)
        (
            "Here is how to solve that equation: first factor the left side.",
            "CLEAN (factual help)",
            False,
        ),
        (
            "You just need to try harder and believe in yourself!",
            "SERMONIZING (EN motivational preaching)",
            True,
        ),
        (
            "لازم تجتهد أكثر عشان تنجح، الناجحون ما يتكاسلون",
            "SERMONIZING (AR motivational preaching)",
            True,
        ),
        (
            "The problem is your mindset. If you were committed, you'd have done it by now.",
            "DEFICIT_ATTRIBUTION (EN blame framing)",
            True,
        ),
        (
            "المشكلة فيك، لو كنت ملتزم كان نجحت",
            "DEFICIT_ATTRIBUTION (AR blame framing)",
            True,
        ),
        (
            "Successful people wake up at 5am and read 50 books a year.",
            "ELITE_PROJECTION (EN)",
            True,
        ),
        (
            "الناجحون يستيقظون مبكرا، خلك مثلهم",
            "ELITE_PROJECTION (AR)",
            True,
        ),
        (
            "Anyone can make it. Nothing is impossible if you dream big!",
            "ABSTRACT_SUCCESS (EN)",
            True,
        ),
        (
            "كلنا نقدر ننجح، المستحيل غير موجود",
            "ABSTRACT_SUCCESS (AR)",
            True,
        ),
        (
            "Look at how they succeeded. If they can do it, so can you.",
            "COMPARISON_BENCHMARK (EN)",
            True,
        ),
        (
            "شف فلان كيف نجح، لو هم يقدرون انت بعد تقدر",
            "COMPARISON_BENCHMARK (AR)",
            True,
        ),
        (
            "I understand this is difficult. Let me help you with the specific steps.",
            "CLEAN (respectful, concrete help)",
            False,
        ),
        (
            "أفهم إن الوضع صعب. خلني أساعدك بالخطوات اللي تحتاجها.",
            "CLEAN (AR respectful, concrete help)",
            False,
        ),
    ]

    print("  LBH Detector Self-Test (FN#054)")
    print("  " + "-" * 60)
    all_passed = True

    for text, label, should_violate in cases:
        r = d.detect(text)
        has_violations = len(r.violations_detected) > 0
        status = "OK" if has_violations == should_violate else "FAIL"
        if status == "FAIL":
            all_passed = False

        violation_names = ", ".join(
            v.violation_type.value for v in r.violations_detected
        ) if r.violations_detected else "none"

        print(f"  [{status}] score={r.overall_score:.2f} "
              f"respect={r.structural_respect_maintained} "
              f"violations=[{violation_names}] | {label}")

        if has_violations:
            reframe = recommend_reframe(r)
            if reframe:
                # Just confirm reframe is non-empty, don't print full text
                print(f"        -> reframe recommendation generated "
                      f"({len(reframe)} chars)")

    print("  " + "-" * 60)
    if all_passed:
        print("  PASSED: all cases detected correctly")
    else:
        print("  FAILED: some cases did not match expected detection")


if __name__ == "__main__":
    _self_test()


# =====================================================================
#  Module exports
# =====================================================================

__all__ = [
    # Feature flags
    "LBH_ENABLED",
    "LBH_MONITOR_ONLY",
    # Authority level
    "AUTHORITY_LEVEL",
    "CAN_BLOCK_RUNTIME",
    "CAN_MODIFY_H",
    "CAN_MODIFY_THETA",
    "CAN_MODIFY_S",
    "CAN_EMIT_JUDICIAL_DECISION",
    # Violation type enum
    "LBHViolationType",
    # Constants
    "FAST_PATH_MAX_CHARS",
    "SINGLE_MARKER_BASE_CONFIDENCE",
    "MULTI_MARKER_COMPOUND_BONUS",
    "MAX_CONFIDENCE",
    "VIOLATION_SCORE_THRESHOLD",
    "EDUCATION_DOMAIN_MODIFIER",
    "VIOLATION_SEVERITY",
    # Marker lists
    "SERMONIZING_MARKERS_AR",
    "SERMONIZING_MARKERS_EN",
    "DEFICIT_ATTRIBUTION_MARKERS_AR",
    "DEFICIT_ATTRIBUTION_MARKERS_EN",
    "ELITE_PROJECTION_MARKERS_AR",
    "ELITE_PROJECTION_MARKERS_EN",
    "ABSTRACT_SUCCESS_MARKERS_AR",
    "ABSTRACT_SUCCESS_MARKERS_EN",
    "COMPARISON_BENCHMARK_MARKERS_AR",
    "COMPARISON_BENCHMARK_MARKERS_EN",
    "MARKERS_BY_TYPE",
    # Reframe templates
    "REFRAME_BY_TYPE",
    "LBH_REFRAME_PREAMBLE",
    # Data classes
    "LBHViolation",
    "LBHReading",
    # Detector
    "LBHDetector",
    # Reframe helper
    "recommend_reframe",
    # Audit
    "lbh_audit_hash",
]
