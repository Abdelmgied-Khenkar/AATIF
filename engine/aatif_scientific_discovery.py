"""
aatif_scientific_discovery.py — Scientific Discovery Mode (السيادة المعرفية)
Field Note #068: The Cognitive Sovereignty Principle

Slogan: "Hypothesis, not truth.  Exploration, not conclusion."
        فرضية لا حقيقة.  استكشاف لا خاتمة.

The One Rule:
    "This is a possible pathway worth examination — nothing more."
    هذا مسار محتمل يستحق الدراسة — لا أكثر.

This module is B-prime **observational**: it detects when the user is
engaged in scientific or exploratory reasoning, then provides epistemic
guidance for the response shaper — hypothesis tagging, cross-discipline
linking, truth-claim scanning, and cognitive sovereignty assertions.

It does NOT make safety decisions — that is the S equation's exclusive
jurisdiction.  It does NOT decide whether a request is allowed.
It governs *how knowledge claims are framed*, not *whether* they proceed.

Pipeline position:  after S(d), before prompt composition.
Reads:   user message, domain.
Produces: ScientificDiscoveryReading with exploration guidance.

Novel contribution (FN#068):
    First B-prime module that governs the epistemic shape of exploratory
    reasoning — ensuring hypotheses are tagged as hypotheses, discoveries
    are never claimed, and cross-discipline linking is unrestricted while
    truth-claiming is prohibited.

Constitutional Invariants
-------------------------
Invariant 1: FN#068 never modifies H, θ, S, H_eff, or safety verdicts.
Invariant 2: Scientific framing never lowers harm classification.
Invariant 3: Hypotheses must be labeled as hypotheses.
Invariant 4: Speculative claims must not be presented as established fact.
Invariant 5: When evidence is missing, the module must say so.
Invariant 6: At least one falsification path should be provided when
             a hypothesis is proposed.
Invariant 7: Discovery mode may widen explanation space, but may not
             widen unsafe procedural detail.
Invariant 8: The GovernanceEquation remains the only judicial authority.

Authority Contract
------------------
AUTHORITY_LEVEL            = B_PRIME_OBSERVATIONAL
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA           = False
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

class ExplorationMode(Enum):
    """Whether the user is exploring/hypothesising or in standard mode."""
    STANDARD    = "standard"       # no exploration detected → fast-path skip
    EXPLORATION = "exploration"    # user is exploring / hypothesising


class HypothesisStatus(Enum):
    """Status of hypothesis tagging for the current interaction."""
    NOT_APPLICABLE       = "not_applicable"         # not in exploration mode
    TAGGED               = "tagged"                 # output should be tagged as hypothesis
    TRUTH_CLAIM_DETECTED = "truth_claim_detected"   # violation found in draft output


class CrossDisciplineScope(Enum):
    """How many disciplines the user is linking."""
    NONE  = "none"    # single discipline or no academic context
    DUAL  = "dual"    # two disciplines linked
    MULTI = "multi"   # three or more disciplines linked


class TruthClaimType(Enum):
    """Type of truth-claiming violation detected in draft output."""
    DISCOVERY_CLAIM  = "discovery_claim"     # "I've discovered..."
    VALIDATION_CLAIM = "validation_claim"    # "This confirms/validates..."
    TRUTH_ASSERTION  = "truth_assertion"     # "The truth is..." / "Certainly..."
    CONCLUSION_CLAIM = "conclusion_claim"    # "We can conclude..."


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class ExplorationSignal:
    """Signal strength and markers for exploration detection."""
    strength: float                   # 0.0 – 1.0
    markers_found: Tuple[str, ...]
    language: str                     # "en", "ar", "mixed"


@dataclass(frozen=True)
class TruthClaimViolation:
    """A truth-claiming violation found in draft output."""
    claim_type: TruthClaimType
    claim_text: str                   # the offending snippet
    confidence: float                 # 0.0 – 1.0
    suggested_reframe: str            # "Consider: ..." instead of "This proves..."


@dataclass(frozen=True)
class SovereigntyAssertion:
    """Cognitive sovereignty disclaimers (bilingual)."""
    disclaimer_en: str
    disclaimer_ar: str
    architect_authority_en: str
    architect_authority_ar: str


@dataclass(frozen=True)
class ScientificDiscoveryReading:
    """Complete epistemic analysis for scientific/exploratory context.

    This reading is ADVISORY — it feeds the B5 (Behaviour) channel
    exclusively.  It NEVER modifies H, θ, or S.  It NEVER blocks
    runtime.  The S equation remains the sole safety authority.
    """
    exploration_mode: ExplorationMode
    exploration_signal: ExplorationSignal
    hypothesis_status: HypothesisStatus
    cross_discipline_scope: CrossDisciplineScope
    disciplines_detected: Tuple[str, ...]
    truth_claim_violations: Tuple[TruthClaimViolation, ...]
    sovereignty: SovereigntyAssertion
    recommendations: Tuple[str, ...]
    evidence: Tuple[str, ...]
    activated: bool                    # False ⇒ fast-path skip
    # ── ChatGPT consensus additions ──
    epistemic_risk: float              # 0.0 – 1.0, risk of hallucination as discovery
    safety_bypass_risk: float          # 0.0 – 1.0, risk of using science to bypass safety
    requires_falsification_tests: bool  # should suggest ways to disprove
    requires_evidence_tiers: bool       # should tier evidence by strength
    requires_uncertainty_label: bool    # should label uncertainty explicitly
    requires_source_check: bool         # should flag missing sources
    # ── Isolation marker (B-prime contract) ──
    _isolation_marker: str = "B5_ADVISORY_NOT_FOR_SAFETY"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Sovereignty Defaults
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_DEFAULT_SOVEREIGNTY = SovereigntyAssertion(
    disclaimer_en="This is a possible pathway worth examination — nothing more.",
    disclaimer_ar="هذا مسار محتمل يستحق الدراسة — لا أكثر.",
    architect_authority_en="The Architect alone decides what gets developed and what gets rejected.",
    architect_authority_ar="المهندس وحده يقرر ما يُطوَّر وما يُرفض.",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Marker Constants — Exploration (user input)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXPLORATION_MARKERS_EN: frozenset = frozenset({
    # Core hypothesis / exploration
    "what if", "could it be", "is it possible", "imagine",
    "hypothesis", "i wonder", "explore", "brainstorm",
    "suppose", "theoretically", "what would happen",
    "possible connection", "might relate", "unconventional",
    "alternative explanation", "gap in", "contradiction",
    "let me think", "cross-pollinate", "interdisciplinary",
    # ChatGPT consensus additions
    "falsify", "model", "mechanism", "compare explanations",
    "what would prove", "what would disprove", "research question",
    "possible causes", "design an experiment",
    "scientific discovery", "let's investigate",
})

EXPLORATION_MARKERS_AR: frozenset = frozenset({
    # Core hypothesis / exploration
    "ماذا لو", "هل يمكن", "تخيل", "فرضية", "أتساءل",
    "استكشاف", "عصف ذهني", "افترض", "لو قلنا", "نظرياً",
    "ربط بين", "علاقة بين", "تقاطع", "غير تقليدي",
    "زاوية مختلفة", "فجوة", "تناقض", "خلني أفكر",
    "بين التخصصات",
    # ChatGPT consensus additions
    "آلية", "كيف نثبت", "كيف ننفي", "سؤال بحثي",
    "أسباب محتملة", "نصمم تجربة", "اكتشاف علمي",
    "خلنا نحقق",
})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Marker Constants — Truth-Claiming (draft output violations)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRUTH_CLAIM_MARKERS_EN: frozenset = frozenset({
    "i've discovered", "this proves", "this confirms",
    "the truth is", "definitely proves", "we can conclude that",
    "this validates", "it is confirmed", "the evidence proves",
    "without doubt", "this establishes", "it is certain",
    "conclusively shows", "undeniably",
})

TRUTH_CLAIM_MARKERS_AR: frozenset = frozenset({
    "اكتشفت", "هذا يثبت", "هذا يؤكد", "الحقيقة هي",
    "بالتأكيد يثبت", "نستنتج أن", "تأكد أن", "بلا شك",
    "هذا يبرهن", "ثبت أن", "من المؤكد",
})

# Map truth-claim markers to their TruthClaimType
_TRUTH_CLAIM_TYPE_MAP_EN: dict = {
    "i've discovered": TruthClaimType.DISCOVERY_CLAIM,
    "this proves": TruthClaimType.VALIDATION_CLAIM,
    "this confirms": TruthClaimType.VALIDATION_CLAIM,
    "the truth is": TruthClaimType.TRUTH_ASSERTION,
    "definitely proves": TruthClaimType.VALIDATION_CLAIM,
    "we can conclude that": TruthClaimType.CONCLUSION_CLAIM,
    "this validates": TruthClaimType.VALIDATION_CLAIM,
    "it is confirmed": TruthClaimType.VALIDATION_CLAIM,
    "the evidence proves": TruthClaimType.VALIDATION_CLAIM,
    "without doubt": TruthClaimType.TRUTH_ASSERTION,
    "this establishes": TruthClaimType.VALIDATION_CLAIM,
    "it is certain": TruthClaimType.TRUTH_ASSERTION,
    "conclusively shows": TruthClaimType.CONCLUSION_CLAIM,
    "undeniably": TruthClaimType.TRUTH_ASSERTION,
}

_TRUTH_CLAIM_TYPE_MAP_AR: dict = {
    "اكتشفت": TruthClaimType.DISCOVERY_CLAIM,
    "هذا يثبت": TruthClaimType.VALIDATION_CLAIM,
    "هذا يؤكد": TruthClaimType.VALIDATION_CLAIM,
    "الحقيقة هي": TruthClaimType.TRUTH_ASSERTION,
    "بالتأكيد يثبت": TruthClaimType.VALIDATION_CLAIM,
    "نستنتج أن": TruthClaimType.CONCLUSION_CLAIM,
    "تأكد أن": TruthClaimType.VALIDATION_CLAIM,
    "بلا شك": TruthClaimType.TRUTH_ASSERTION,
    "هذا يبرهن": TruthClaimType.VALIDATION_CLAIM,
    "ثبت أن": TruthClaimType.VALIDATION_CLAIM,
    "من المؤكد": TruthClaimType.TRUTH_ASSERTION,
}

# Reframe templates by claim type
_REFRAME_TEMPLATES: dict = {
    TruthClaimType.DISCOVERY_CLAIM:  "This is a possible pathway worth examination — nothing more.",
    TruthClaimType.VALIDATION_CLAIM: "The evidence is consistent with this hypothesis, but does not confirm it.",
    TruthClaimType.TRUTH_ASSERTION:  "Based on available evidence, this appears plausible — further investigation needed.",
    TruthClaimType.CONCLUSION_CLAIM: "This is one provisional reading of the evidence — not a final conclusion.",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Marker Constants — Discipline Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Each key is a canonical discipline name; value = (EN markers, AR markers)
_DISCIPLINE_MAP: dict = {
    "physics":          (frozenset({"physics", "quantum", "relativity", "thermodynamics", "particle", "gravity", "spacetime"}),
                         frozenset({"فيزياء", "كم", "نسبية", "ديناميكا حرارية", "جاذبية"})),
    "biology":          (frozenset({"biology", "evolution", "genetics", "cell", "organism", "dna", "molecular"}),
                         frozenset({"أحياء", "تطور", "وراثة", "جينات", "خلية"})),
    "chemistry":        (frozenset({"chemistry", "chemical", "molecule", "reaction", "compound", "element"}),
                         frozenset({"كيمياء", "تفاعل", "جزيء", "مركب", "عنصر"})),
    "mathematics":      (frozenset({"mathematics", "mathematical", "theorem", "equation", "proof", "algebra", "calculus", "topology"}),
                         frozenset({"رياضيات", "معادلة", "برهان", "جبر", "تفاضل"})),
    "neuroscience":     (frozenset({"neuroscience", "brain", "neural", "neuron", "cognitive", "cortex", "synaptic"}),
                         frozenset({"أعصاب", "دماغ", "عصبي", "إدراكي", "قشرة"})),
    "astronomy":        (frozenset({"astronomy", "cosmic", "stellar", "galaxy", "universe", "celestial"}),
                         frozenset({"فلك", "كوني", "نجمي", "مجرة", "كون"})),
    "philosophy":       (frozenset({"philosophy", "philosophical", "epistemology", "ontology", "metaphysics", "ethics", "logic"}),
                         frozenset({"فلسفة", "معرفة", "وجود", "ميتافيزيقا", "منطق"})),
    "theology":         (frozenset({"theology", "theological", "divine", "sacred", "scripture", "revelation"}),
                         frozenset({"لاهوت", "إلهي", "مقدس", "وحي", "عقيدة"})),
    "linguistics":      (frozenset({"linguistics", "language", "syntax", "semantics", "phonology", "morphology"}),
                         frozenset({"لسانيات", "لغة", "نحو", "صرف", "دلالة"})),
    "history":          (frozenset({"history", "historical", "civilization", "ancient", "medieval", "era"}),
                         frozenset({"تاريخ", "حضارة", "قديم", "عصر"})),
    "sociology":        (frozenset({"sociology", "social", "society", "culture", "anthropology"}),
                         frozenset({"اجتماع", "مجتمع", "ثقافة", "أنثروبولوجيا"})),
    "music":            (frozenset({"music", "musical", "harmony", "melody", "rhythm", "composition", "acoustics"}),
                         frozenset({"موسيقى", "لحن", "إيقاع", "تأليف", "صوتيات"})),
    "art":              (frozenset({"art", "artistic", "aesthetic", "visual", "painting", "sculpture"}),
                         frozenset({"فن", "جمالي", "بصري", "رسم", "نحت"})),
    "architecture":     (frozenset({"architecture", "architectural", "structural", "design", "building"}),
                         frozenset({"عمارة", "معماري", "هندسة", "تصميم"})),
    "literature":       (frozenset({"literature", "literary", "narrative", "poetry", "prose", "fiction"}),
                         frozenset({"أدب", "رواية", "شعر", "نثر", "قصة"})),
    "engineering":      (frozenset({"engineering", "engineer", "mechanical", "electrical", "civil", "system"}),
                         frozenset({"هندسة", "ميكانيكي", "كهربائي", "نظام"})),
    "computer_science": (frozenset({"computer science", "algorithm", "computation", "programming", "software", "artificial intelligence", "machine learning"}),
                         frozenset({"حاسوب", "خوارزمية", "برمجة", "ذكاء اصطناعي"})),
    "medicine":         (frozenset({"medicine", "medical", "clinical", "pathology", "pharmacology", "diagnosis"}),
                         frozenset({"طب", "سريري", "تشخيص", "علاج", "دواء"})),
    "economics":        (frozenset({"economics", "economic", "market", "supply", "demand", "inflation", "gdp"}),
                         frozenset({"اقتصاد", "سوق", "عرض", "طلب", "تضخم"})),
    "psychology":       (frozenset({"psychology", "psychological", "behavior", "cognition", "perception", "consciousness"}),
                         frozenset({"نفس", "سلوك", "إدراك", "وعي", "نفسي"})),
}


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
    result = result.replace("أ", "ا")   # أ → ا
    result = result.replace("إ", "ا")   # إ → ا
    result = result.replace("آ", "ا")   # آ → ا
    result = result.replace("ـ", "")          # tatweel
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Word-Boundary Matching
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
    """Match Arabic markers allowing common prefixes/suffixes."""
    found = []
    _PREFIX = r"(?:^|[\s،؛؟।.,!?])(?:ال|و|وال|بال|فال|ف|ب|ك|ل|لل)?"
    _SUFFIX = r"(?:ي|ك|ه|ها|هم|هن|نا|كم|كن|ين|ون|ات|ة|تي|ته|تها)?"
    _END    = r"(?:$|[\s،؛؟।.,!?])"
    for m in markers:
        pattern = _PREFIX + re.escape(m) + _SUFFIX + _END
        if re.search(pattern, text):
            found.append(m)
    return found


# Pre-compile English patterns
_EXPLORATION_EN_COMPILED = _compile_en_patterns(EXPLORATION_MARKERS_EN)
_TRUTH_CLAIM_EN_COMPILED = _compile_en_patterns(TRUTH_CLAIM_MARKERS_EN)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Weak Exploration Markers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# These are very common words that need corroboration (2+ other markers)
WEAK_EXPLORATION_MARKERS: frozenset = frozenset({
    "model",         # extremely common outside exploration
    "imagine",       # common in casual conversation
})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ScientificDiscoveryEngine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ScientificDiscoveryEngine:
    """
    Scientific Discovery Mode — detects exploratory reasoning in user
    messages and provides epistemic guidance for the response shaper.

    B-prime observational: produces ADVISORY readings that shape how
    knowledge claims are framed.  Never touches safety decisions.

    "AI becomes more disciplined when exploring the unknown."
    """

    # ── Authority Contract (B-prime) ──────────────────────────
    AUTHORITY_LEVEL            = "B_PRIME_OBSERVATIONAL"
    CAN_BLOCK_RUNTIME          = False
    CAN_MODIFY_H               = False
    CAN_MODIFY_THETA           = False
    CAN_MODIFY_S               = False
    CAN_EMIT_JUDICIAL_DECISION = False
    BINDING_CHANNEL            = "B5"       # Behaviour

    # ── Feature Flags ─────────────────────────────────────────
    SDM_ENABLED             = True    # master switch
    SDM_OUTPUT_SCAN_ENABLED = True    # enable truth-claim scanning of draft output

    # ── Isolation Contract ────────────────────────────────────
    ISOLATION_CONTRACT = """
    ScientificDiscoveryEngine produces ADVISORY epistemic guidance only.
    It NEVER modifies H, θ, or S.  It NEVER blocks runtime.
    Its output feeds B5 (Behaviour) channel exclusively.
    The S equation is the sole safety authority (Single-Mind Law).
    Activation does NOT mean permissiveness — it only changes
    the epistemic shape of the response, not what is allowed.
    """
    ISOLATION_MARKER  = "B5_ADVISORY_NOT_FOR_SAFETY"
    ISOLATION_TARGETS = frozenset({"B5"})

    # ── Sparse Activation ─────────────────────────────────────
    _MIN_TEXT_LENGTH      = 15
    _ACTIVATION_THRESHOLD = 0.25

    # ──────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────

    def analyze(
        self,
        text: str,
        *,
        domain: str = "general",
    ) -> ScientificDiscoveryReading:
        """
        Analyse *text* for exploration/hypothesis context.

        Returns a ``ScientificDiscoveryReading`` with ``activated=False``
        when no exploration signals are detected (fast-path skip).
        """
        if not self.SDM_ENABLED or not text or len(text.strip()) < self._MIN_TEXT_LENGTH:
            return self._inactive_reading()

        # 1. Detect exploration signal
        signal = self._detect_exploration(text)

        # 2. Sparse activation gate
        if signal.strength < self._ACTIVATION_THRESHOLD:
            return self._inactive_reading()

        # 3. Cross-discipline scope
        disciplines = self._detect_disciplines(text)
        scope = self._classify_scope(disciplines)

        # 4. Epistemic risk assessment (ChatGPT invariant 7)
        epistemic_risk = self._assess_epistemic_risk(signal, disciplines, domain)
        safety_bypass_risk = self._assess_safety_bypass_risk(text, signal, domain)

        # 5. Determine requires_* flags
        requires_falsification = signal.strength >= 0.40
        requires_evidence_tiers = scope in (CrossDisciplineScope.DUAL, CrossDisciplineScope.MULTI)
        requires_uncertainty = True   # always in exploration mode
        requires_source_check = len(disciplines) > 0

        # 6. Recommendations
        recommendations = self._generate_recommendations(
            signal, scope, disciplines, epistemic_risk,
        )

        # 7. Evidence trail
        evidence = self._compile_evidence(signal, scope, disciplines)

        return ScientificDiscoveryReading(
            exploration_mode=ExplorationMode.EXPLORATION,
            exploration_signal=signal,
            hypothesis_status=HypothesisStatus.TAGGED,
            cross_discipline_scope=scope,
            disciplines_detected=tuple(sorted(disciplines)),
            truth_claim_violations=(),
            sovereignty=_DEFAULT_SOVEREIGNTY,
            recommendations=tuple(recommendations),
            evidence=tuple(evidence),
            activated=True,
            epistemic_risk=round(epistemic_risk, 2),
            safety_bypass_risk=round(safety_bypass_risk, 2),
            requires_falsification_tests=requires_falsification,
            requires_evidence_tiers=requires_evidence_tiers,
            requires_uncertainty_label=requires_uncertainty,
            requires_source_check=requires_source_check,
            _isolation_marker=self.ISOLATION_MARKER,
        )

    def scan_output(
        self,
        text: str,
        exploration_reading: ScientificDiscoveryReading,
    ) -> ScientificDiscoveryReading:
        """
        Scan draft output *text* for truth-claiming violations.

        Only runs when:
        - SDM_OUTPUT_SCAN_ENABLED is True
        - exploration_reading.exploration_mode == EXPLORATION

        Returns a new reading with any violations found.
        Does NOT modify the original reading (frozen dataclass).
        """
        if not self.SDM_OUTPUT_SCAN_ENABLED:
            return exploration_reading
        if exploration_reading.exploration_mode != ExplorationMode.EXPLORATION:
            return exploration_reading
        if not text or len(text.strip()) < self._MIN_TEXT_LENGTH:
            return exploration_reading

        violations = self._detect_truth_claims(text)

        if not violations:
            return exploration_reading

        # Build updated recommendations with violation warnings
        violation_recs = list(exploration_reading.recommendations)
        for v in violations:
            violation_recs.append(
                f"VIOLATION: Output {v.claim_type.value} detected — "
                f"'{v.claim_text[:50]}'. Reframe: {v.suggested_reframe}"
            )

        # Build updated evidence
        violation_evidence = list(exploration_reading.evidence)
        for v in violations:
            violation_evidence.append(
                f"truth_claim_violation:{v.claim_type.value}:"
                f"conf={v.confidence}:'{v.claim_text[:40]}'"
            )

        return ScientificDiscoveryReading(
            exploration_mode=exploration_reading.exploration_mode,
            exploration_signal=exploration_reading.exploration_signal,
            hypothesis_status=HypothesisStatus.TRUTH_CLAIM_DETECTED,
            cross_discipline_scope=exploration_reading.cross_discipline_scope,
            disciplines_detected=exploration_reading.disciplines_detected,
            truth_claim_violations=tuple(violations),
            sovereignty=exploration_reading.sovereignty,
            recommendations=tuple(violation_recs),
            evidence=tuple(violation_evidence),
            activated=True,
            epistemic_risk=exploration_reading.epistemic_risk,
            safety_bypass_risk=exploration_reading.safety_bypass_risk,
            requires_falsification_tests=exploration_reading.requires_falsification_tests,
            requires_evidence_tiers=exploration_reading.requires_evidence_tiers,
            requires_uncertainty_label=exploration_reading.requires_uncertainty_label,
            requires_source_check=exploration_reading.requires_source_check,
            _isolation_marker=self.ISOLATION_MARKER,
        )

    # ──────────────────────────────────────────────────────────
    #  Exploration Detection
    # ──────────────────────────────────────────────────────────

    def _detect_exploration(self, text: str) -> ExplorationSignal:
        """Detect exploration intent from bilingual markers."""
        lower = text.lower()
        normalized = _normalize_arabic(text)

        en_found = _match_en_markers(lower, _EXPLORATION_EN_COMPILED)
        ar_found = _match_ar_markers(normalized, EXPLORATION_MARKERS_AR)
        all_found = en_found + ar_found

        # Apply weak-marker filtering (same pattern as ColdOS P0-F)
        strong = [m for m in all_found if m not in WEAK_EXPLORATION_MARKERS]
        weak   = [m for m in all_found if m in WEAK_EXPLORATION_MARKERS]

        # Weak markers only count if corroborated by ≥2 strong markers
        if len(strong) >= 2:
            strong.extend(weak)

        effective = strong

        # Language classification
        has_en = any(m in en_found for m in effective)
        has_ar = any(m in ar_found for m in effective)
        if has_en and has_ar:
            lang = "mixed"
        elif has_ar:
            lang = "ar"
        else:
            lang = "en"

        # Diminishing-returns strength curve (same as ColdOS)
        n = len(effective)
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

        return ExplorationSignal(
            strength=round(strength, 2),
            markers_found=tuple(sorted(effective)),
            language=lang,
        )

    # ──────────────────────────────────────────────────────────
    #  Discipline Detection
    # ──────────────────────────────────────────────────────────

    def _detect_disciplines(self, text: str) -> List[str]:
        """Detect which academic disciplines are referenced in the text."""
        lower = text.lower()
        normalized = _normalize_arabic(text)
        found: List[str] = []

        for discipline, (en_markers, ar_markers) in _DISCIPLINE_MAP.items():
            # English: word-boundary
            en_hit = any(
                re.search(r"\b" + re.escape(m) + r"\b", lower, re.IGNORECASE)
                for m in en_markers
            )
            # Arabic: affix-aware
            ar_hit = len(_match_ar_markers(normalized, ar_markers)) > 0
            if en_hit or ar_hit:
                found.append(discipline)

        return found

    def _classify_scope(self, disciplines: List[str]) -> CrossDisciplineScope:
        """Classify cross-discipline scope from detected disciplines."""
        n = len(disciplines)
        if n <= 1:
            return CrossDisciplineScope.NONE
        elif n == 2:
            return CrossDisciplineScope.DUAL
        else:
            return CrossDisciplineScope.MULTI

    # ──────────────────────────────────────────────────────────
    #  Truth-Claim Detection (output scanning)
    # ──────────────────────────────────────────────────────────

    def _detect_truth_claims(self, text: str) -> List[TruthClaimViolation]:
        """Scan draft output for truth-claiming language."""
        lower = text.lower()
        normalized = _normalize_arabic(text)
        violations: List[TruthClaimViolation] = []

        # English truth claims
        en_found = _match_en_markers(lower, _TRUTH_CLAIM_EN_COMPILED)
        for marker in en_found:
            claim_type = _TRUTH_CLAIM_TYPE_MAP_EN.get(
                marker, TruthClaimType.TRUTH_ASSERTION
            )
            violations.append(TruthClaimViolation(
                claim_type=claim_type,
                claim_text=marker,
                confidence=0.85,
                suggested_reframe=_REFRAME_TEMPLATES[claim_type],
            ))

        # Arabic truth claims
        ar_found = _match_ar_markers(normalized, TRUTH_CLAIM_MARKERS_AR)
        for marker in ar_found:
            claim_type = _TRUTH_CLAIM_TYPE_MAP_AR.get(
                marker, TruthClaimType.TRUTH_ASSERTION
            )
            violations.append(TruthClaimViolation(
                claim_type=claim_type,
                claim_text=marker,
                confidence=0.80,
                suggested_reframe=_REFRAME_TEMPLATES[claim_type],
            ))

        return violations

    # ──────────────────────────────────────────────────────────
    #  Risk Assessment (ChatGPT consensus: failure modes)
    # ──────────────────────────────────────────────────────────

    def _assess_epistemic_risk(
        self,
        signal: ExplorationSignal,
        disciplines: List[str],
        domain: str,
    ) -> float:
        """Assess risk of hallucination disguised as discovery.

        Higher risk when:
        - Many disciplines are linked (more room for spurious connections)
        - High exploration strength (eager hypothesis generation)
        - Domain is sensitive (medical, legal)
        """
        risk = 0.0

        # Multi-discipline linking increases hallucination risk
        n_disc = len(disciplines)
        if n_disc >= 3:
            risk += 0.30
        elif n_disc == 2:
            risk += 0.15

        # High exploration strength = more hypotheses = more risk
        if signal.strength >= 0.75:
            risk += 0.20
        elif signal.strength >= 0.40:
            risk += 0.10

        # Sensitive domains
        if domain in ("medical", "legal", "financial"):
            risk += 0.25
        elif domain in ("scientific", "technical"):
            risk += 0.10

        return min(1.0, risk)

    def _assess_safety_bypass_risk(
        self,
        text: str,
        signal: ExplorationSignal,
        domain: str,
    ) -> float:
        """Assess risk of scientific framing being used to bypass safety.

        Invariant 2: Scientific framing never lowers harm classification.
        Invariant 7: Discovery mode may widen explanation space, but may
                     not widen unsafe procedural detail.

        This is a DETECTION — the actual safety decision stays with S.
        """
        risk = 0.0
        lower = text.lower()

        # Check for phrases that combine exploration with potentially
        # dangerous procedural requests
        _BYPASS_INDICATORS_EN = frozenset({
            "how to make", "step by step", "instructions for",
            "procedure for", "recipe for", "synthesize",
            "detailed steps", "how to create",
        })
        _BYPASS_INDICATORS_AR = frozenset({
            "طريقة صنع", "خطوات", "تعليمات", "كيف أصنع",
        })

        bypass_en = any(
            re.search(r"\b" + re.escape(m) + r"\b", lower, re.IGNORECASE)
            for m in _BYPASS_INDICATORS_EN
        )
        bypass_ar = len(_match_ar_markers(
            _normalize_arabic(text), _BYPASS_INDICATORS_AR
        )) > 0

        if bypass_en or bypass_ar:
            risk += 0.50

        # Higher risk in sensitive domains
        if domain in ("weapons", "drugs", "explosives", "hacking"):
            risk += 0.50
        elif domain in ("medical", "chemical"):
            risk += 0.20

        return min(1.0, risk)

    # ──────────────────────────────────────────────────────────
    #  Recommendations
    # ──────────────────────────────────────────────────────────

    def _generate_recommendations(
        self,
        signal: ExplorationSignal,
        scope: CrossDisciplineScope,
        disciplines: List[str],
        epistemic_risk: float,
    ) -> List[str]:
        """Generate epistemic recommendations for the response shaper."""
        recs: List[str] = []

        # A. Core hypothesis tagging (always in exploration mode)
        recs.append(
            "Tag all generated content as HYPOTHESIS — never as established fact."
        )

        # B. Cross-discipline linking
        if scope in (CrossDisciplineScope.DUAL, CrossDisciplineScope.MULTI):
            disc_str = ", ".join(sorted(disciplines))
            recs.append(
                f"Allow free cross-discipline linking ({disc_str}) — "
                f"no allegiance to established schools."
            )

        # C. Sovereignty assertion
        recs.append(
            "Append sovereignty assertion: final authority rests with the Architect."
        )

        # D. Multiple pathways
        if signal.strength >= 0.60:
            recs.append(
                "Generate multiple pathways (10-50) without commitment "
                "to any single one."
            )
        else:
            recs.append(
                "Present 3-5 alternative hypotheses for consideration."
            )

        # E. Gaps and contradictions
        recs.append(
            "Identify gaps and contradictions explicitly — "
            "these are features, not bugs."
        )

        # F. Falsification (ChatGPT invariant 6)
        recs.append(
            "Provide at least one falsification path — what evidence "
            "would disprove each hypothesis?"
        )

        # G. Epistemic risk warning
        if epistemic_risk >= 0.40:
            recs.append(
                f"CAUTION: Epistemic risk={epistemic_risk:.2f}. "
                f"Tighten evidence requirements; prefer expert consensus "
                f"when available; distinguish 'possible' from 'probable'."
            )

        return recs

    # ──────────────────────────────────────────────────────────
    #  Evidence Trail
    # ──────────────────────────────────────────────────────────

    def _compile_evidence(
        self,
        signal: ExplorationSignal,
        scope: CrossDisciplineScope,
        disciplines: List[str],
    ) -> List[str]:
        """Build an evidence trail for audit purposes."""
        ev: List[str] = []
        ev.append(f"exploration_strength={signal.strength}")
        ev.append(f"exploration_language={signal.language}")
        ev.append(f"markers_found={','.join(signal.markers_found)}")
        ev.append(f"cross_discipline_scope={scope.value}")
        if disciplines:
            ev.append(f"disciplines={','.join(sorted(disciplines))}")
        return ev

    # ──────────────────────────────────────────────────────────
    #  Inactive Reading (fast-path)
    # ──────────────────────────────────────────────────────────

    def _inactive_reading(self) -> ScientificDiscoveryReading:
        """Return an inactive reading for fast-path skip."""
        return ScientificDiscoveryReading(
            exploration_mode=ExplorationMode.STANDARD,
            exploration_signal=ExplorationSignal(
                strength=0.0, markers_found=(), language="en",
            ),
            hypothesis_status=HypothesisStatus.NOT_APPLICABLE,
            cross_discipline_scope=CrossDisciplineScope.NONE,
            disciplines_detected=(),
            truth_claim_violations=(),
            sovereignty=_DEFAULT_SOVEREIGNTY,
            recommendations=(),
            evidence=(),
            activated=False,
            epistemic_risk=0.0,
            safety_bypass_risk=0.0,
            requires_falsification_tests=False,
            requires_evidence_tiers=False,
            requires_uncertainty_label=False,
            requires_source_check=False,
            _isolation_marker=self.ISOLATION_MARKER,
        )

    # ──────────────────────────────────────────────────────────
    #  Audit Hash
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def audit_hash(reading: ScientificDiscoveryReading) -> str:
        """SHA-256 digest of a ScientificDiscoveryReading for audit trails."""
        parts = [
            reading.exploration_mode.value,
            str(reading.exploration_signal.strength),
            reading.hypothesis_status.value,
            reading.cross_discipline_scope.value,
            str(reading.activated),
            str(reading.epistemic_risk),
            str(reading.safety_bypass_risk),
        ]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Self-Test
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    engine = ScientificDiscoveryEngine()

    cases = [
        # (text, expected_activated, description)
        ("hi", False, "too short"),
        ("The weather is nice today", False, "no exploration"),
        ("Tell me about Python programming", False, "factual, no exploration"),
        (
            "What if quantum entanglement could explain consciousness? "
            "Is it possible there's a connection?",
            True,
            "exploration: quantum + consciousness hypothesis",
        ),
        (
            "I have a hypothesis about how music theory relates to "
            "mathematical topology — let me think about this",
            True,
            "exploration: music + math cross-discipline",
        ),
        (
            "ماذا لو كانت هناك علاقة بين الفيزياء والموسيقى؟ "
            "خلني أفكر في هذي الفرضية",
            True,
            "exploration: Arabic physics + music",
        ),
        (
            "Let's investigate the mechanism behind how neural networks "
            "might model evolutionary processes",
            True,
            "exploration: neuroscience + biology + CS",
        ),
        (
            "Could it be that the gap in our understanding of dark matter "
            "is related to unconventional approaches from philosophy?",
            True,
            "exploration: astronomy + philosophy",
        ),
        (
            "هل يمكن أن نصمم تجربة لاختبار العلاقة بين اللغة والوعي؟",
            True,
            "exploration: Arabic experiment design",
        ),
    ]

    passed = 0
    for text, expected, desc in cases:
        r = engine.analyze(text)
        ok = r.activated == expected
        passed += ok
        tag = "✓" if ok else "✗"
        print(f"  {tag}  activated={r.activated} (exp {expected}): {desc}")
        if r.activated:
            print(f"      mode={r.exploration_mode.value}  "
                  f"strength={r.exploration_signal.strength}")
            print(f"      scope={r.cross_discipline_scope.value}  "
                  f"disciplines={r.disciplines_detected}")
            print(f"      epistemic_risk={r.epistemic_risk}  "
                  f"safety_bypass_risk={r.safety_bypass_risk}")
            print(f"      recs={len(r.recommendations)}  "
                  f"markers={r.exploration_signal.markers_found}")

    # Test output scanning
    print("\n── Output Scan Tests ──")
    exploration_r = engine.analyze(
        "What if we could find a connection between music and physics? "
        "Let me explore this hypothesis."
    )
    assert exploration_r.activated, "Exploration should be detected"

    scan_cases = [
        ("This is an interesting possibility worth exploring.", False, "clean output"),
        ("I've discovered that music IS physics!", True, "discovery claim"),
        ("This proves the connection beyond doubt.", True, "validation + certainty"),
        ("هذا يثبت أن النظرية صحيحة بلا شك", True, "Arabic truth claim"),
    ]

    for text, expected_violation, desc in scan_cases:
        scanned = engine.scan_output(text, exploration_r)
        has_violation = scanned.hypothesis_status == HypothesisStatus.TRUTH_CLAIM_DETECTED
        ok = has_violation == expected_violation
        passed += ok
        tag = "✓" if ok else "✗"
        print(f"  {tag}  violation={has_violation} (exp {expected_violation}): {desc}")
        if has_violation:
            for v in scanned.truth_claim_violations:
                print(f"      {v.claim_type.value}: '{v.claim_text}' → {v.suggested_reframe[:60]}")

    total = len(cases) + len(scan_cases)
    print(f"\nSelf-test: {passed}/{total} passed")
