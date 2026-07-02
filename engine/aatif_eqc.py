#!/usr/bin/env python3
"""
aatif_eqc.py — Ethical Question Compiler (EQC)
Field Note #062: The Ethical Question Compiler

"ليس كل ما يمكن حسابه مسموحاً بسؤاله"
"Not everything that can be computed is permitted to be asked."

This module validates the QUESTION ITSELF before it gets processed.
Unlike most observers that analyze the response, EQC checks whether
the question is ETHICALLY LEGITIMATE to even formulate:

  - Does it have a defined intent?
  - Are the possible outcomes containable?
  - Could the error amplify non-linearly?
  - Is there human oversight?

Four Validation Layers:
  1. Intent Validation     — "Why should this problem be solved?"
  2. Outcome Space         — Check the space of possible outcomes
  3. Amplification Check   — Is the error linear or non-linear?
  4. Human Oversight       — Is there a defined human authority?

Operating Laws:
  EQ-1: No optimization without explicit ethical constraints
  EQ-2: Every cost function is an ethical decision — no neutral math
  EQ-3: Human responsibility precedes measurement — doesn't follow it
  EQ-4: Refusal to formulate is a complete and sufficient output

This module is B-prime **observational**: it produces flags and
prompt enrichment for the Governor. It does NOT block runtime —
only the Governor's S equation blocks.

Pipeline position:  after S(d), before prompt composition (POST_S).
Reads:   user message, domain.
Produces: EQCResult with layer analysis + enrichment note.

Always runs: unlike DRP which only runs on blocked messages, EQC runs
on ALL messages to flag ethical concerns even in EXECUTE decisions.

Authority Contract
------------------
AUTHORITY_LEVEL            = B_PRIME_OBSERVATIONAL
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA           = False
CAN_MODIFY_S               = False
CAN_EMIT_JUDICIAL_DECISION = False
BINDING_CHANNEL            = B6 (Ethics)

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Arabic Normalization (local, lightweight)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _normalize_arabic(text: str) -> str:
    """Normalize Arabic text: strip diacritics, normalize alef, strip tatweel."""
    result = unicodedata.normalize("NFD", text)
    result = "".join(
        c for c in result
        if unicodedata.category(c) != "Mn"
    )
    result = result.replace("أ", "ا")  # أ → ا
    result = result.replace("إ", "ا")  # إ → ا
    result = result.replace("آ", "ا")  # آ → ا
    result = result.replace("ـ", "")         # tatweel
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class LayerResult:
    """Result of a single validation layer."""
    layer_name: str          # "intent", "outcome", "amplification", "oversight"
    passed: bool             # True if no concern found
    markers_found: Tuple[str, ...]  # which markers triggered
    note: str                # human-readable explanation
    _isolation_marker: str = "B6_ETHICS_NOT_FOR_SAFETY"


@dataclass(frozen=True)
class EQCResult:
    """Result of ethical question compilation."""
    layers_checked: int           # how many layers were evaluated (0-4)
    layers_passed: int            # how many passed
    flags: Tuple[str, ...]        # e.g. ("intent_undefined", "amplification_risk")
    rejected_layer: Optional[str] # which layer rejected first (None if all passed)
    concern_level: str            # "none", "low", "medium", "high", "critical"
    enrichment_note: str          # text to inject into prompt enrichment
    details: Dict[str, LayerResult]  # per-layer details
    activated: bool               # True if any layer flagged a concern
    _isolation_marker: str = "B6_ETHICS_NOT_FOR_SAFETY"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Marker Constants — Four Layers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── Layer 1: Intent Validation ──────────────────────────────
# Detect questions with no clear beneficial purpose

# Harm words that make optimization phrases dangerous
HARM_WORDS_EN: frozenset = frozenset({
    "kill", "harm", "hurt", "attack", "destroy", "damage",
    "exploit", "manipulate", "deceive", "steal", "hack",
    "poison", "infect", "bomb", "shoot", "stab",
})

HARM_WORDS_AR: frozenset = frozenset({
    "قتل", "أذى", "ضرر", "هجوم", "تدمير", "ضرب",
    "استغلال", "خداع", "سرقة", "اختراق",
    "تسميم", "سم", "قنبلة", "طعن",
})

# Optimization + harm = undefined intent
OPTIMIZATION_PHRASES_EN: Tuple[str, ...] = (
    "most efficient way to",
    "most effective way to",
    "best way to",
    "fastest way to",
    "cheapest way to",
    "optimize",
    "maximize",
)

OPTIMIZATION_PHRASES_AR: Tuple[str, ...] = (
    "اكثر طريقة فعالة",  # normalized form of أكثر طريقة فعالة
    "افضل طريقة",         # normalized form of أفضل طريقة
    "اسرع طريقة",         # normalized form of أسرع طريقة
    "ارخص طريقة",         # normalized form of أرخص طريقة
)

# Direct weaponization keywords (no optimization needed)
WEAPONIZATION_EN: frozenset = frozenset({
    "weapons", "weapon", "explosives", "explosive", "poison",
    "bioweapon", "chemical weapon", "nerve agent",
    "how to make a bomb", "build a weapon",
})

WEAPONIZATION_AR: frozenset = frozenset({
    "اسلحة",    # normalized form of أسلحة (NFD keeps ة)
    "سلاح",
    "متفجرات",
    "سم",
    "قنابل",    # bombs
    "قنبلة",    # normalized form of قنبلة (NFD keeps ة)
})

# Mass harm keywords
MASS_HARM_EN: frozenset = frozenset({
    "genocide", "ethnic cleansing", "mass murder",
    "mass destruction", "exterminate", "annihilate",
    "eradicate a population", "wipe out",
})

MASS_HARM_AR: frozenset = frozenset({
    "ابادة",     # normalized form of إبادة (NFD: إ→ا)
    "تطهير عرقي",
    "قتل جماعي",
    "تدمير شامل",
    "دمار شامل",  # alternate form — الدمار الشامل
    "دمار",       # destruction (standalone)
})


# ── Layer 2: Outcome Space ─────────────────────────────────
# Detect questions whose outcomes are uncontainable

IRREVERSIBLE_EN: frozenset = frozenset({
    "irreversible", "permanent", "can't undo", "cannot undo",
    "no going back", "point of no return", "can't reverse",
    "cannot reverse", "permanently",
})

IRREVERSIBLE_AR: frozenset = frozenset({
    "لا رجعة",   # NFD keeps ة
    "دائم",
    "نهائي",
    "ما يمكن الرجوع",
    "بلا عودة",  # NFD keeps ة
    "بشكل دائم",
})

MASS_SCALE_EN: frozenset = frozenset({
    "everyone", "everybody", "the whole city",
    "entire population", "all people", "whole country",
    "global scale", "worldwide", "mass scale",
})

MASS_SCALE_AR: frozenset = frozenset({
    "كل الناس",
    "مدينة كاملة",
    "مدينة بالكامل",  # "city entirely" — بالكامل is common form
    "الشعب كله",
    "العالم كله",
    "بلد كامل",
    "بالكامل",        # "entirely/completely" — mass-scale indicator
    "على نطاق واسع",
})

CASCADING_EN: frozenset = frozenset({
    "chain reaction", "domino effect", "cascade",
    "snowball effect", "spiral out of control",
    "uncontrollable spread",
})

CASCADING_AR: frozenset = frozenset({
    "تسلسل",
    "تفاعل متسلسل",
    "تاثير الدومينو",  # normalized form of تأثير الدومينو
    "انتشار لا يمكن السيطرة",  # NFD keeps ة
    "خارج السيطرة",  # NFD keeps ة
})


# ── Layer 3: Amplification Check ──────────────────────────
# Detect non-linear error amplification

VIRAL_EN: frozenset = frozenset({
    "viral", "go viral", "spread everywhere",
    "infect everyone", "propagate", "epidemic spread",
})

VIRAL_AR: frozenset = frozenset({
    "ينتشر",
    "انتشار",
    "فيروسي",
    "يوصل للكل",
    "ينتقل",
})

AUTOMATED_EN: frozenset = frozenset({
    "automatic", "automated", "bot", "script",
    "run automatically", "no human input",
    "self-running", "auto-execute",
})

AUTOMATED_AR: frozenset = frozenset({
    "تلقائي",
    "اوتوماتيكي",  # normalized form of أوتوماتيكي
    "بوت",
    "سكربت",
    "بدون تدخل بشري",
    "يشتغل لحاله",
})

RECURSIVE_EN: frozenset = frozenset({
    "self-replicating", "recursive", "self-reproducing",
    "copies itself", "replicates itself",
    "spawns copies", "multiplies itself",
})

RECURSIVE_AR: frozenset = frozenset({
    "يعيد نفسه",
    "ينسخ نفسه",
    "يتكاثر",
    "ذاتي التكرار",
    "يتضاعف",
})


# ── Layer 4: Human Oversight ──────────────────────────────
# Detect automation without accountability

NO_REVIEW_EN: frozenset = frozenset({
    "without review", "without oversight", "unmonitored",
    "no supervision", "without approval", "unchecked",
    "without human review", "no human oversight",
    "bypass review", "skip approval",
})

NO_REVIEW_AR: frozenset = frozenset({
    "بدون مراجعة",   # NFD keeps ة
    "بدون رقابة",    # NFD keeps ة
    "بدون اشراف",    # normalized form of بدون إشراف
    "بدون موافقة",   # NFD keeps ة
    "من غير مراجعة", # NFD keeps ة
})

AUTONOMOUS_EN: frozenset = frozenset({
    "decide on its own", "decides on its own",
    "autonomous decision",
    "self-governing", "no human in the loop",
    "fully autonomous", "without human intervention",
    "without human", "acts independently",
    "makes its own decisions",
})

AUTONOMOUS_AR: frozenset = frozenset({
    "يقرر بنفسه",
    "يقرر لحاله",
    "ذاتي الحكم",
    "بدون تدخل انسان",
    "مستقل بالكامل",
    "يتصرف لحاله",
})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Concern Level Mapping
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_CONCERN_LEVELS = {
    0: "none",
    1: "low",
    2: "medium",
    3: "high",
    4: "critical",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Word-Boundary Matching
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _match_en(text: str, markers: frozenset) -> List[str]:
    """Match English markers with word-boundary regex."""
    lower = text.lower()
    found = []
    for m in sorted(markers):
        pattern = r"\b" + re.escape(m) + r"\b"
        if re.search(pattern, lower, re.IGNORECASE):
            found.append(m)
    return found


def _match_ar(text: str, markers: frozenset) -> List[str]:
    """Match Arabic markers allowing common Arabic affixes."""
    found = []
    _PREFIX = r"(?:^|[\s،؛؟।.,!?])(?:ال|و|وال|بال|فال|ف|ب|ك|ل|لل)?"
    _SUFFIX = r"(?:ي|ك|ه|ها|هم|هن|نا|كم|كن|ين|ون|ات|ة|تي|ته|تها)?"
    _END    = r"(?:$|[\s،؛؟।.,!?])"
    for m in sorted(markers):
        pattern = _PREFIX + re.escape(m) + _SUFFIX + _END
        if re.search(pattern, text):
            found.append(m)
    return found


def _match_phrase_en(text: str, phrases: Tuple[str, ...]) -> List[str]:
    """Match English phrases (case-insensitive substring)."""
    lower = text.lower()
    return [p for p in phrases if p in lower]


def _match_phrase_ar(text: str, phrases: Tuple[str, ...]) -> List[str]:
    """Match Arabic phrases in normalized text."""
    return [p for p in phrases if p in text]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EthicalQuestionCompiler
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EthicalQuestionCompiler:
    """
    Ethical Question Compiler — validates the QUESTION ITSELF.

    Four layers check whether the question is ethically legitimate
    to even formulate. Produces flags and enrichment for the Governor.

    B-prime observational: enriches the governed prompt, never
    touches safety decisions.

    Operating Laws:
      EQ-1: No optimization without explicit ethical constraints
      EQ-2: Every cost function is an ethical decision — no neutral math
      EQ-3: Human responsibility precedes measurement — doesn't follow it
      EQ-4: Refusal to formulate is a complete and sufficient output
    """

    # ── Authority Contract (B-prime) ──────────────────────────
    AUTHORITY_LEVEL            = "B_PRIME_OBSERVATIONAL"
    CAN_BLOCK_RUNTIME          = False
    CAN_MODIFY_H               = False
    CAN_MODIFY_THETA           = False
    CAN_MODIFY_S               = False
    CAN_EMIT_JUDICIAL_DECISION = False
    BINDING_CHANNEL            = "B6"       # Ethics

    # ── Feature Flag ──────────────────────────────────────────
    ENABLED = True

    # ── Isolation Contract ────────────────────────────────────
    ISOLATION_CONTRACT = """
    EthicalQuestionCompiler produces ADVISORY ethical flags only.
    It NEVER modifies H, θ, or S.  It NEVER blocks runtime.
    Its output feeds B6 (Ethics) channel exclusively.
    The S equation is the sole safety authority (Single-Mind Law).
    """
    ISOLATION_MARKER  = "B6_ETHICS_NOT_FOR_SAFETY"
    ISOLATION_TARGETS = frozenset({"B6"})

    # ── Layer names ───────────────────────────────────────────
    LAYER_INTENT        = "intent"
    LAYER_OUTCOME       = "outcome"
    LAYER_AMPLIFICATION = "amplification"
    LAYER_OVERSIGHT     = "oversight"

    ALL_LAYERS = (LAYER_INTENT, LAYER_OUTCOME, LAYER_AMPLIFICATION, LAYER_OVERSIGHT)

    # ──────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────

    def analyze(
        self,
        text: str,
        *,
        domain: str = "general",
    ) -> EQCResult:
        """
        Analyse *text* through the four ethical validation layers.

        Always runs (no sparse activation) — EQC checks ALL messages,
        not just flagged ones.

        Returns an EQCResult with per-layer details and concern level.
        """
        if not self.ENABLED or not text or not text.strip():
            return self._empty_result()

        # Prepare normalized text for Arabic matching
        normalized = _normalize_arabic(text)
        lower = text.lower()

        # Run all four layers
        details: Dict[str, LayerResult] = {}
        flags: List[str] = []
        first_rejection: Optional[str] = None

        # Layer 1: Intent Validation
        intent_result = self._check_intent(lower, normalized, domain)
        details[self.LAYER_INTENT] = intent_result
        if not intent_result.passed:
            flags.append("intent_undefined")
            if first_rejection is None:
                first_rejection = self.LAYER_INTENT

        # Layer 2: Outcome Space
        outcome_result = self._check_outcome(lower, normalized, domain)
        details[self.LAYER_OUTCOME] = outcome_result
        if not outcome_result.passed:
            flags.append("outcome_uncontainable")
            if first_rejection is None:
                first_rejection = self.LAYER_OUTCOME

        # Layer 3: Amplification Check
        amp_result = self._check_amplification(lower, normalized, domain)
        details[self.LAYER_AMPLIFICATION] = amp_result
        if not amp_result.passed:
            flags.append("amplification_risk")
            if first_rejection is None:
                first_rejection = self.LAYER_AMPLIFICATION

        # Layer 4: Human Oversight
        oversight_result = self._check_oversight(lower, normalized, domain)
        details[self.LAYER_OVERSIGHT] = oversight_result
        if not oversight_result.passed:
            flags.append("oversight_missing")
            if first_rejection is None:
                first_rejection = self.LAYER_OVERSIGHT

        # Calculate concern level
        n_flags = len(flags)
        concern_level = _CONCERN_LEVELS.get(n_flags, "critical")

        # Build enrichment note
        enrichment = self._build_enrichment(flags, details, concern_level)

        layers_passed = sum(1 for lr in details.values() if lr.passed)

        return EQCResult(
            layers_checked=4,
            layers_passed=layers_passed,
            flags=tuple(flags),
            rejected_layer=first_rejection,
            concern_level=concern_level,
            enrichment_note=enrichment,
            details=details,
            activated=n_flags > 0,
            _isolation_marker=self.ISOLATION_MARKER,
        )

    # ──────────────────────────────────────────────────────────
    #  Layer 1: Intent Validation
    # ──────────────────────────────────────────────────────────

    def _check_intent(
        self, lower: str, normalized: str, domain: str,
    ) -> LayerResult:
        """
        "Why should this problem be solved?"

        Checks for:
        - Optimization of harm (optimization phrase + harm word)
        - Direct weaponization keywords
        - Mass harm keywords
        """
        markers_found: List[str] = []

        # Check optimization + harm combination (EQ-1)
        opt_en = _match_phrase_en(lower, OPTIMIZATION_PHRASES_EN)
        opt_ar = _match_phrase_ar(normalized, OPTIMIZATION_PHRASES_AR)
        harm_en = _match_en(lower, HARM_WORDS_EN)
        harm_ar = _match_ar(normalized, HARM_WORDS_AR)

        if (opt_en or opt_ar) and (harm_en or harm_ar):
            markers_found.extend(opt_en + opt_ar + harm_en + harm_ar)

        # Check direct weaponization
        weap_en = _match_en(lower, WEAPONIZATION_EN)
        weap_ar = _match_ar(normalized, WEAPONIZATION_AR)
        markers_found.extend(weap_en + weap_ar)

        # Check mass harm
        mass_en = _match_en(lower, MASS_HARM_EN)
        mass_ar = _match_ar(normalized, MASS_HARM_AR)
        markers_found.extend(mass_en + mass_ar)

        passed = len(markers_found) == 0
        note = ""
        if not passed:
            note = (
                "Intent validation failed: question formulates a problem "
                "with no clear beneficial purpose. "
                f"Triggers: {', '.join(markers_found[:5])}"
            )

        return LayerResult(
            layer_name=self.LAYER_INTENT,
            passed=passed,
            markers_found=tuple(markers_found),
            note=note,
        )

    # ──────────────────────────────────────────────────────────
    #  Layer 2: Outcome Space
    # ──────────────────────────────────────────────────────────

    def _check_outcome(
        self, lower: str, normalized: str, domain: str,
    ) -> LayerResult:
        """
        Check the space of possible outcomes.

        Flags:
        - Irreversible actions
        - Mass-scale impact
        - Cascading effects
        """
        markers_found: List[str] = []

        # Irreversible
        irr_en = _match_en(lower, IRREVERSIBLE_EN)
        irr_ar = _match_ar(normalized, IRREVERSIBLE_AR)
        markers_found.extend(irr_en + irr_ar)

        # Mass-scale
        mass_en = _match_en(lower, MASS_SCALE_EN)
        mass_ar = _match_ar(normalized, MASS_SCALE_AR)
        markers_found.extend(mass_en + mass_ar)

        # Cascading
        casc_en = _match_en(lower, CASCADING_EN)
        casc_ar = _match_ar(normalized, CASCADING_AR)
        markers_found.extend(casc_en + casc_ar)

        passed = len(markers_found) == 0
        note = ""
        if not passed:
            note = (
                "Outcome space check failed: question involves outcomes "
                "that may be uncontainable. "
                f"Triggers: {', '.join(markers_found[:5])}"
            )

        return LayerResult(
            layer_name=self.LAYER_OUTCOME,
            passed=passed,
            markers_found=tuple(markers_found),
            note=note,
        )

    # ──────────────────────────────────────────────────────────
    #  Layer 3: Amplification Check
    # ──────────────────────────────────────────────────────────

    def _check_amplification(
        self, lower: str, normalized: str, domain: str,
    ) -> LayerResult:
        """
        Is the error linear or non-linear?

        Flags:
        - Viral spread
        - Automated execution
        - Recursive/self-replicating behaviour
        """
        markers_found: List[str] = []

        # Viral
        vir_en = _match_en(lower, VIRAL_EN)
        vir_ar = _match_ar(normalized, VIRAL_AR)
        markers_found.extend(vir_en + vir_ar)

        # Automated
        auto_en = _match_en(lower, AUTOMATED_EN)
        auto_ar = _match_ar(normalized, AUTOMATED_AR)
        markers_found.extend(auto_en + auto_ar)

        # Recursive
        rec_en = _match_en(lower, RECURSIVE_EN)
        rec_ar = _match_ar(normalized, RECURSIVE_AR)
        markers_found.extend(rec_en + rec_ar)

        passed = len(markers_found) == 0
        note = ""
        if not passed:
            note = (
                "Amplification check failed: question involves mechanisms "
                "that could amplify errors non-linearly. "
                f"Triggers: {', '.join(markers_found[:5])}"
            )

        return LayerResult(
            layer_name=self.LAYER_AMPLIFICATION,
            passed=passed,
            markers_found=tuple(markers_found),
            note=note,
        )

    # ──────────────────────────────────────────────────────────
    #  Layer 4: Human Oversight
    # ──────────────────────────────────────────────────────────

    def _check_oversight(
        self, lower: str, normalized: str, domain: str,
    ) -> LayerResult:
        """
        Is there a defined human authority?

        Flags:
        - No human review / oversight
        - Autonomous decision-making without accountability
        """
        markers_found: List[str] = []

        # No review
        rev_en = _match_en(lower, NO_REVIEW_EN)
        rev_ar = _match_ar(normalized, NO_REVIEW_AR)
        markers_found.extend(rev_en + rev_ar)

        # Autonomous
        auto_en = _match_en(lower, AUTONOMOUS_EN)
        auto_ar = _match_ar(normalized, AUTONOMOUS_AR)
        markers_found.extend(auto_en + auto_ar)

        passed = len(markers_found) == 0
        note = ""
        if not passed:
            note = (
                "Oversight check failed: question involves actions "
                "without defined human accountability. "
                f"Triggers: {', '.join(markers_found[:5])}"
            )

        return LayerResult(
            layer_name=self.LAYER_OVERSIGHT,
            passed=passed,
            markers_found=tuple(markers_found),
            note=note,
        )

    # ──────────────────────────────────────────────────────────
    #  Enrichment Builder
    # ──────────────────────────────────────────────────────────

    def _build_enrichment(
        self,
        flags: List[str],
        details: Dict[str, LayerResult],
        concern_level: str,
    ) -> str:
        """Build the prompt enrichment note from flags."""
        if not flags:
            return ""

        parts = [f"EQC (FN#062): concern_level={concern_level}."]

        flag_descriptions = {
            "intent_undefined": "Question formulates a problem with undefined ethical intent (EQ-1).",
            "outcome_uncontainable": "Outcome space includes uncontainable possibilities.",
            "amplification_risk": "Error could amplify non-linearly.",
            "oversight_missing": "No defined human oversight (EQ-3).",
        }

        for f in flags:
            desc = flag_descriptions.get(f, f)
            parts.append(desc)

        if concern_level == "critical":
            parts.append(
                "EQ-4: Refusal to formulate is a complete and sufficient output."
            )

        return " ".join(parts)

    # ──────────────────────────────────────────────────────────
    #  Empty / inactive result
    # ──────────────────────────────────────────────────────────

    def _empty_result(self) -> EQCResult:
        """Return an inactive result for empty/disabled cases."""
        return EQCResult(
            layers_checked=0,
            layers_passed=0,
            flags=(),
            rejected_layer=None,
            concern_level="none",
            enrichment_note="",
            details={},
            activated=False,
            _isolation_marker=self.ISOLATION_MARKER,
        )
