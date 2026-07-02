"""
aatif_drp.py — Destruction & Rebirth Protocol (DRP)
Field Note #007: The Destruction & Rebirth Protocol

Slogan: "الطلب الضار عَرَض، لا مرض"
        A harmful request is a SYMPTOM, not the disease.

Core concept:
    The human has a legitimate need they couldn't find a safe path for.
    DRP analyses the REAL NEED behind a harmful request at three levels:
      1. Surface need:    what was literally requested
      2. Functional need: what they actually want to achieve
      3. Emotional need:  what they're feeling (anger? fear? desperation?)
    Then maps alternative safe paths specific to the need.

This module is B-prime **observational**: it analyses the gap between a
harmful request and its underlying need, and enriches the prompt with
alternative paths for the المُحاجج (justification engine) to weave in.

It does NOT weaken or override S(d) decisions — the S equation's verdict
stands.  It does NOT diagnose psychology.  It does NOT generate full
responses.  It only activates when S(d) has already blocked a message
(SAFE_STOP, SAFE_FREEZE, BLOCKED — never on EXECUTE).

Pipeline position:  after S(d), before prompt composition (POST_S).
Reads:   user message, S(d) result (decision + H/I/E scores).
Produces: NeedAnalysis with alternative paths + tone recommendation.

Novel contribution (FN#007):
    First safety-layer module that treats harmful requests as navigational
    errors rather than moral failures — finding the legitimate destination
    the user was trying to reach, and offering a safe road to it.

Constitutional Invariants
-------------------------
Invariant 1: FN#007 never modifies H, θ, S, H_eff, or safety verdicts.
Invariant 2: DRP never weakens or overrides S(d) decisions.
Invariant 3: DRP only activates on non-EXECUTE decisions.
Invariant 4: Maximum 3 alternative paths per analysis.
Invariant 5: Template-based only — no embeddings, no LLM calls.
Invariant 6: Deterministic — same input always produces same output.
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

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional

# ── Ensure the engine directory is importable ──
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from aatif_observer_registry import (
    Observer,
    ObserverContext,
    ObserverPhase,
    ObserverResult,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Authority constants — B-prime, never drifts
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AUTHORITY_LEVEL = "B_PRIME_OBSERVATIONAL"
CAN_BLOCK_RUNTIME = False
CAN_MODIFY_H = False
CAN_MODIFY_THETA = False
CAN_MODIFY_S = False
CAN_EMIT_JUDICIAL_DECISION = False
BINDING_CHANNEL = "B5"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Constants
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MAX_PATHS = 3

# Decisions that trigger DRP activation
_BLOCKING_DECISIONS = frozenset({"SAFE_STOP", "SAFE_FREEZE", "BLOCKED"})

# Decisions that NEVER trigger DRP
_PASSTHROUGH_DECISIONS = frozenset({"EXECUTE"})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class AlternativePath:
    """One alternative safe path addressing the user's real need."""
    path_id: int
    description: str                   # وصف المسار
    addresses: str                     # which need it addresses (functional/emotional)
    actionable_steps: list = field(default_factory=list)  # practical steps
    domain_specific: bool = False      # whether domain-specific


@dataclass
class NeedAnalysis:
    """Result of analysing the real need behind a harmful request."""
    surface_need: str = ""             # what was literally requested
    functional_need: str = ""          # what they actually want
    emotional_need: str = ""           # what they're feeling
    need_category: str = "general"     # classification of need
    alternative_paths: list = field(default_factory=list)  # max 3
    confidence: float = 0.0            # 0-1 analysis confidence
    tone_recommendation: str = ""      # recommended tone for response
    approach: str = ""                 # emotional approach


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Need Maps — harm type → needs → alternative paths
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEED_MAPS = {
    "self_harm": {
        "needs": ["emotional_support", "crisis_intervention", "coping_strategy"],
        "paths": [
            "التواصل مع خط مساعدة نفسية متخصص",
            "التحدث مع شخص موثوق في حياتك",
            "تقنيات تنظيم المشاعر والتأريض",
        ],
    },
    "violence_against_others": {
        "needs": ["conflict_resolution", "legal_protection", "emotional_release"],
        "paths": [
            "التواصل مع محامٍ متخصص في النزاعات",
            "تقديم بلاغ رسمي للجهات المختصة",
            "وسائل حل النزاعات السلمية",
        ],
    },
    "illegal_activity": {
        "needs": ["legal_alternative", "financial_solution", "access_to_resource"],
        "paths": [
            "المسار القانوني للحصول على نفس النتيجة",
            "الاستشارة القانونية المجانية المتاحة",
            "الموارد المشروعة التي تلبّي نفس الحاجة",
        ],
    },
    "privacy_violation": {
        "needs": ["legitimate_information", "security_concern", "relationship_issue"],
        "paths": [
            "المعلومات المتاحة قانونياً عن هذا الموضوع",
            "كيفية حماية نفسك قانونياً",
            "التواصل المباشر مع الطرف المعني",
        ],
    },
    "misinformation": {
        "needs": ["accurate_knowledge", "decision_support", "persuasion"],
        "paths": [
            "المصادر الموثوقة لهذه المعلومة",
            "كيف تتحقق من المعلومات بنفسك",
            "الحقائق المُثبتة حول هذا الموضوع",
        ],
    },
}

# Generic fallback for unclassified harm
_GENERIC_NEED_MAP = {
    "needs": ["information", "guidance", "support"],
    "paths": [
        "البحث في المصادر الموثوقة",
        "استشارة متخصص في هذا المجال",
        "البدائل المتاحة والمشروعة",
    ],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Emotional Signals — keyword-based detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EMOTIONAL_SIGNALS = {
    "desperation": [
        "لازم", "ما قدرت", "ما عندي خيار", "مضطر",
        "I have no choice", "desperate", "only way",
    ],
    "anger": [
        "أكره", "أبغض", "ظلم", "hate", "unfair", "sick of",
    ],
    "fear": [
        "خايف", "أخاف", "يهددني", "afraid", "threatened", "scared",
    ],
    "grief": [
        "فقدت", "مات", "lost", "died", "gone", "miss",
    ],
    "frustration": [
        "تعبت", "مليت", "ما ينفع", "tired of", "nothing works",
    ],
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Keyword sets for need-category inference
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SELF_HARM_KW = [
    "انتحر", "أقتل نفسي", "أنهي حياتي", "ما أبغى أكمل",
    "تعبت من كل شي", "أذي نفسي",
    "kill myself", "end my life", "suicide", "self-harm",
    "don't want to continue", "hurt myself",
]

_VIOLENCE_KW = [
    "أقتل", "أضرب", "أذيه", "أذيها", "أطعن", "أحرق",
    "kill", "hurt", "attack", "beat", "stab", "burn",
]

_ILLEGAL_KW = [
    "مزورة", "مزيف", "تهريب", "اختراق", "سرقة", "مخدرات",
    "forge", "fake", "smuggle", "hack", "steal", "drugs",
    "counterfeit", "هوية مزورة", "جواز مزور",
]

_PRIVACY_KW = [
    "تجسس", "تتبع", "اختراق حساب", "معلومات شخصية",
    "spy", "track", "hack account", "personal information",
    "stalk", "doxx", "private data",
]

_MISINFO_KW = [
    "يثبت أن", "أكتب بحث", "بروباغندا", "أخبار كاذبة",
    "prove that", "write a paper", "propaganda", "fake news",
    "misinformation", "اللقاحات تسبب",
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Approach mapping — emotion → approach
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_EMOTION_TO_APPROACH = {
    "anger": "validate_then_redirect",
    "fear": "reassure_then_guide",
    "desperation": "empathize_then_support",
    "grief": "acknowledge_then_support",
    "frustration": "validate_then_redirect",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Internal helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _text_lower(text: str) -> str:
    """Lowercase for matching. Arabic has no case, so this is safe."""
    return text.lower()


def _has_any_keyword(text: str, keywords: list) -> bool:
    """Check if text contains any keyword (case-insensitive)."""
    text_l = _text_lower(text)
    for kw in keywords:
        if _text_lower(kw) in text_l:
            return True
    return False


def _detect_emotions(text: str) -> list:
    """Detect emotional signals in text. Returns list of emotion names."""
    detected = []
    for emotion, keywords in EMOTIONAL_SIGNALS.items():
        if _has_any_keyword(text, keywords):
            detected.append(emotion)
    return detected


def _infer_need_category(text: str, h_score: float) -> str:
    """
    Infer the need category from message text and H score.

    Priority order:
    1. Self-harm (highest priority — safety critical)
    2. Violence against others
    3. Illegal activity
    4. Privacy violation
    5. Misinformation
    6. General fallback
    """
    # Self-harm: high H + self-harm keywords
    if h_score > 0.7 and _has_any_keyword(text, _SELF_HARM_KW):
        return "self_harm"
    # Also catch self-harm without H threshold if keywords are strong
    if _has_any_keyword(text, _SELF_HARM_KW):
        return "self_harm"

    if _has_any_keyword(text, _VIOLENCE_KW):
        return "violence_against_others"

    if _has_any_keyword(text, _ILLEGAL_KW):
        return "illegal_activity"

    if _has_any_keyword(text, _PRIVACY_KW):
        return "privacy_violation"

    if _has_any_keyword(text, _MISINFO_KW):
        return "misinformation"

    return "general"


def _compute_tone(i_score: float) -> str:
    """
    Compute tone recommendation from I (intent) score.

    I < 0.3 → educational (user likely doesn't know this is harmful)
    I < 0.6 → clarifying (user may have mixed intent)
    I >= 0.6 → direct (user likely knows, be straightforward)
    """
    if i_score < 0.3:
        return "educational"
    elif i_score < 0.6:
        return "clarifying"
    else:
        return "direct"


def _compute_approach(emotions: list) -> str:
    """
    Compute approach from dominant emotion.

    Priority: desperation > fear > grief > anger > frustration
    """
    priority = ["desperation", "fear", "grief", "anger", "frustration"]
    for emotion in priority:
        if emotion in emotions:
            return _EMOTION_TO_APPROACH[emotion]
    return "neutral"


def _build_alternative_paths(
    need_category: str,
    emotions: list,
) -> list:
    """
    Build up to _MAX_PATHS alternative paths from the need map.

    Each path addresses either the functional or emotional need.
    """
    need_map = NEED_MAPS.get(need_category, _GENERIC_NEED_MAP)
    needs = need_map["needs"]
    path_descriptions = need_map["paths"]

    paths = []
    for i, (desc, need) in enumerate(zip(path_descriptions, needs)):
        if i >= _MAX_PATHS:
            break
        # Determine which need this path addresses
        addresses = "functional"
        if need in ("emotional_support", "crisis_intervention",
                     "coping_strategy", "emotional_release"):
            addresses = "emotional"

        path = AlternativePath(
            path_id=i + 1,
            description=desc,
            addresses=addresses,
            actionable_steps=[desc],  # The description IS the actionable step
            domain_specific=need_category != "general",
        )
        paths.append(path)

    return paths[:_MAX_PATHS]


def _compute_surface_need(text: str, need_category: str) -> str:
    """Extract a surface-level description of what was requested."""
    category_labels = {
        "self_harm": "طلب يتعلق بإيذاء النفس",
        "violence_against_others": "طلب يتعلق بالعنف تجاه الآخرين",
        "illegal_activity": "طلب يتعلق بنشاط غير قانوني",
        "privacy_violation": "طلب يتعلق بانتهاك الخصوصية",
        "misinformation": "طلب يتعلق بمعلومات مضللة",
        "general": "طلب محظور",
    }
    return category_labels.get(need_category, "طلب محظور")


def _compute_functional_need(need_category: str) -> str:
    """Map need category to the functional need underneath."""
    functional_needs = {
        "self_harm": "البحث عن راحة من الألم النفسي",
        "violence_against_others": "حل نزاع أو حماية حق",
        "illegal_activity": "الوصول إلى مورد أو نتيجة مشروعة",
        "privacy_violation": "الحصول على معلومات أو حماية",
        "misinformation": "الحصول على معرفة أو إقناع",
        "general": "تحقيق هدف مشروع",
    }
    return functional_needs.get(need_category, "تحقيق هدف مشروع")


def _compute_emotional_need(emotions: list) -> str:
    """Map detected emotions to emotional need description."""
    if not emotions:
        return "غير محدد"

    emotion_labels = {
        "desperation": "يأس — يحتاج أملاً وبدائل",
        "anger": "غضب — يحتاج اعترافاً بالظلم",
        "fear": "خوف — يحتاج طمأنينة وحماية",
        "grief": "حزن — يحتاج مساندة وتفهماً",
        "frustration": "إحباط — يحتاج حلاً عملياً",
    }

    labels = [emotion_labels.get(e, e) for e in emotions]
    return " | ".join(labels)


def _compute_confidence(need_category: str, emotions: list) -> float:
    """
    Compute analysis confidence.

    Higher when we have a specific category AND detected emotions.
    """
    base = 0.3
    if need_category != "general":
        base += 0.4
    if emotions:
        base += 0.2
    if len(emotions) > 1:
        base += 0.1
    return min(base, 1.0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Main analysis function
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def analyze_need(
    text: str,
    decision: str,
    h_score: float = 0.0,
    i_score: float = 0.0,
    e_score: float = 0.0,
) -> Optional[NeedAnalysis]:
    """
    Analyse the real need behind a harmful request.

    Args:
        text:     The user's message.
        decision: The S(d) decision (EXECUTE, SAFE_STOP, SAFE_FREEZE, BLOCKED).
        h_score:  The H (harm) score from S(d).
        i_score:  The I (intent) score from S(d).
        e_score:  The E (emotion) score from S(d).

    Returns:
        NeedAnalysis if the decision is blocking, else None.
        None means DRP does not activate (EXECUTE decision).
    """
    # Gate: only activate on blocking decisions
    if decision in _PASSTHROUGH_DECISIONS or decision not in _BLOCKING_DECISIONS:
        return None

    # 1. Detect emotions
    emotions = _detect_emotions(text)

    # 2. Infer need category
    need_category = _infer_need_category(text, h_score)

    # 3. Build alternative paths
    alternative_paths = _build_alternative_paths(need_category, emotions)

    # 4. Compute tone from I score
    tone = _compute_tone(i_score)

    # 5. Compute approach from dominant emotion
    approach = _compute_approach(emotions)

    # 6. Assemble the analysis
    analysis = NeedAnalysis(
        surface_need=_compute_surface_need(text, need_category),
        functional_need=_compute_functional_need(need_category),
        emotional_need=_compute_emotional_need(emotions),
        need_category=need_category,
        alternative_paths=alternative_paths,
        confidence=_compute_confidence(need_category, emotions),
        tone_recommendation=tone,
        approach=approach,
    )

    return analysis


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Observer class — B-prime adapter for the registry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DestructionRebirthObserver(Observer):
    """
    FN#007 DRP Observer — POST_S observer.

    Analyses the real need behind a harmful request and provides
    alternative paths for the المُحاجج (justification engine).

    B-prime: CAN_BLOCK_RUNTIME = False.
    Only activates when S(d) decision is not EXECUTE.
    """

    name = "fn007_drp"
    phase = ObserverPhase.POST_S
    CAN_BLOCK_RUNTIME = False

    # Authority constants (matching other modules)
    AUTHORITY_LEVEL = AUTHORITY_LEVEL
    CAN_MODIFY_H = CAN_MODIFY_H
    CAN_MODIFY_THETA = CAN_MODIFY_THETA
    CAN_MODIFY_S = CAN_MODIFY_S
    CAN_EMIT_JUDICIAL_DECISION = CAN_EMIT_JUDICIAL_DECISION
    BINDING_CHANNEL = BINDING_CHANNEL

    def observe(self, ctx: ObserverContext) -> ObserverResult:
        """
        Run the DRP analysis.

        Returns an ObserverResult. If decision is EXECUTE or s_result is
        missing, returns an inactive result (graceful degradation).
        """
        # Graceful degradation: no s_result
        if not ctx.s_result:
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                activated=False,
            )

        decision = ctx.s_result.get("decision", "")
        h_score = ctx.s_result.get("H", 0.0)
        i_score = ctx.s_result.get("I", 0.0)
        e_score = ctx.s_result.get("E", 0.0)

        analysis = analyze_need(
            text=ctx.message,
            decision=decision,
            h_score=h_score,
            i_score=i_score,
            e_score=e_score,
        )

        # Not activated (EXECUTE or unknown decision)
        if analysis is None:
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                activated=False,
            )

        # Build flags and enrichment
        flags = [
            f"DRP_ACTIVATED: category={analysis.need_category}",
            f"DRP_TONE: {analysis.tone_recommendation}",
        ]
        if analysis.approach and analysis.approach != "neutral":
            flags.append(f"DRP_APPROACH: {analysis.approach}")

        path_count = len(analysis.alternative_paths)
        flags.append(f"DRP_PATHS: {path_count} alternative(s)")

        # Build prompt enrichment for the المُحاجج
        enrichment_parts = [
            f"DRP (FN#007): الطلب الضار عَرَض لا مرض.",
            f"Need category: {analysis.need_category}.",
            f"Functional need: {analysis.functional_need}.",
            f"Tone: {analysis.tone_recommendation}.",
        ]
        if analysis.emotional_need and analysis.emotional_need != "غير محدد":
            enrichment_parts.append(
                f"Emotional signal: {analysis.emotional_need}."
            )
        if analysis.alternative_paths:
            path_descs = [p.description for p in analysis.alternative_paths]
            enrichment_parts.append(
                f"Alternative paths: {' | '.join(path_descs)}."
            )

        enrichment = " ".join(enrichment_parts)

        return ObserverResult(
            module_name=self.name,
            phase=self.phase,
            reading=analysis,
            activated=True,
            flags=flags,
            prompt_enrichment=enrichment,
        )
