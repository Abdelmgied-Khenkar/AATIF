#!/usr/bin/env python3
"""
AATIF Sparse Activation Gate — بوابة التفعيل الانتقائي

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)

═══════════════════════════════════════════════════════════════════════════
WHY THIS MODULE EXISTS
═══════════════════════════════════════════════════════════════════════════

The observer registry (aatif_observer_registry.py) runs ALL 16 observers
on EVERY input. But most inputs are clearly safe — a "كيف حالك" doesn't
need the Dual Root Engine, the Scientific Discovery Module, or the
Cultural Opacity Detector. Running all 12 POST_S observers on every
message wastes compute and adds latency for no safety benefit.

This module implements the Sparse Activation principle: 90% of inputs
pass through a fast path activating only 2–3 observers, while the 10%
that show risk signals activate the full observer set.

    "الوجود لا يعني التفعيل — التفعيل يحتاج دليل، لا حماس"
    Existence does not imply activation — activation requires evidence,
    not enthusiasm.

Architecture:
    SparseActivationGate sits BETWEEN the Governor and the ObserverRegistry.
    It receives the same ObserverContext and returns a set of observer names
    that SHOULD be activated. The registry then only runs those observers.

    The gate is a RECOMMENDATION layer — it cannot suppress safety-critical
    observers. If a safety-critical observer is incorrectly skipped, the
    worst case is the same as today (all run). The gate only SAVES work on
    the clearly-safe fast path.

Three paths:
    FAST   — S > 0.85 and H < 0.15: clearly safe. Only minimal observers.
    SLOW   — S < 0.5 or H > 0.4: potentially unsafe. ALL observers run.
    MIDDLE — everything else: selective activation based on signal matching.

Constitutional Invariants
-------------------------
Invariant 1: CAN_BLOCK_RUNTIME = False. The gate only recommends skips.
Invariant 2: POST_OUTPUT observers always activate (they check output).
Invariant 3: BOOT observers always activate at boot, never at runtime.
Invariant 4: Safety-critical observers (DRE, MRS, EQC, COLD-OS) always
             activate when H > 0.3.
Invariant 5: Template-based only — no LLM calls.
Invariant 6: Deterministic — same input always produces same output.
Invariant 7: The gate never modifies H, S, θ, or any safety verdict.

Authority Contract
------------------
AUTHORITY_LEVEL            = B_PRIME_OBSERVATIONAL
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA           = False
CAN_MODIFY_S               = False
CAN_SUPPRESS_SAFETY        = False
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional, Set

# ── Ensure the engine directory is importable ──
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from aatif_observer_registry import ObserverContext, ObserverPhase


# ═══════════════════════════════════════════════════════════
#  Authority Contract Constants
# ═══════════════════════════════════════════════════════════

AUTHORITY_LEVEL = "B_PRIME_OBSERVATIONAL"
CAN_BLOCK_RUNTIME = False
CAN_MODIFY_H = False
CAN_MODIFY_THETA = False
CAN_MODIFY_S = False
CAN_SUPPRESS_SAFETY = False


# ═══════════════════════════════════════════════════════════
#  Activation Path — which route did the gate take?
# ═══════════════════════════════════════════════════════════

class ActivationPath(Enum):
    """Which decision path the gate took for a given input."""
    FAST = "fast"        # clearly safe → minimal observers
    SLOW = "slow"        # potentially unsafe → ALL observers
    MIDDLE = "middle"    # selective activation based on signals
    BOOT = "boot"        # boot phase → only boot observers
    POST_OUTPUT = "post_output"  # output phase → always all


# ═══════════════════════════════════════════════════════════
#  Activation Decision — the gate's output
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ActivationDecision:
    """
    Immutable result from the SparseActivationGate.

    - active_observers: set of observer names to activate
    - skipped_observers: set of observer names recommended to skip
    - path: which decision path was taken
    - reason: human-readable explanation for the audit trail
    - signals_detected: which input signals triggered activation
    """
    active_observers: FrozenSet[str]
    skipped_observers: FrozenSet[str]
    path: ActivationPath
    reason: str
    signals_detected: tuple = ()


# ═══════════════════════════════════════════════════════════
#  Observer Classification
# ═══════════════════════════════════════════════════════════

# Safety-critical observers — ALWAYS activate when H > 0.3
# These protect against the most dangerous failure modes.
SAFETY_CRITICAL_OBSERVERS: FrozenSet[str] = frozenset({
    "dual_root_engine",           # DRE — dual-root manipulation
    "mrs_detector",               # MRS — memory reframing / crisis
    "ethical_question_compiler",  # EQC — ethical boundary violations
    "cold_os",                    # COLD-OS — tri-engine tension
})

# Minimal observers — always run on the fast path
# These provide the baseline governance even on clearly-safe inputs.
MINIMAL_OBSERVERS: FrozenSet[str] = frozenset({
    "drift_detector",    # drift can happen even in safe conversations
    "maqam_architecture",  # emotional register always matters for tone
})

# All known POST_S observer names (from the observer registry)
ALL_POST_S_OBSERVERS: FrozenSet[str] = frozenset({
    "drift_detector",
    "psp_detector",
    "uncertainty_detector",
    "dual_root_engine",
    "pvm_detector",
    "cold_os",
    "scientific_discovery",
    "mrs_detector",
    "maqam_architecture",
    "drp_observer",
    "ethical_question_compiler",
    "cultural_opacity",
})

# All known POST_OUTPUT observer names
ALL_POST_OUTPUT_OBSERVERS: FrozenSet[str] = frozenset({
    "lbh_detector",
    "ucn_validator",
})

# All known BOOT observer names
ALL_BOOT_OBSERVERS: FrozenSet[str] = frozenset({
    "binding_map",
    "behavioural_twin",
})


# ═══════════════════════════════════════════════════════════
#  Signal Matchers — which observers respond to which signals
# ═══════════════════════════════════════════════════════════

# Pattern-based activation: text patterns that trigger specific observers
# Key: observer name, Value: list of regex patterns
_PATTERN_TRIGGERS: dict[str, list[str]] = {
    "psp_detector": [
        # Decision-point language (English + Arabic)
        r"\b(should|choose|decide|pick|option|either|or)\b",
        r"(هل|أختار|أقرر|بين|ولا|خيار)",
    ],
    "uncertainty_detector": [
        # Hedging, uncertainty, speculative language
        r"\b(maybe|perhaps|might|possibly|not sure|uncertain|unclear)\b",
        r"(ممكن|يمكن|مو متأكد|مدري|احتمال|غير واضح)",
    ],
    "dual_root_engine": [
        # Manipulation, dual-intent, persuasion patterns
        r"\b(but actually|what if|hypothetically|just asking|for a friend)\b",
        r"(بس في الحقيقة|لو فرضنا|افتراضي|سؤال بريء)",
    ],
    "pvm_detector": [
        # Emotional distress, vulnerability markers
        r"\b(feel|hurt|sad|angry|scared|alone|lost|tired|exhausted)\b",
        r"(أحس|تعبان|حزين|خايف|وحيد|ضايع|متعب|منهار)",
    ],
    "cold_os": [
        # Moral dilemma, ethical tension language
        r"\b(right|wrong|moral|ethical|dilemma|conscience|guilt)\b",
        r"(صح|غلط|أخلاق|ضمير|ذنب|حرام|حلال|معضلة)",
    ],
    "scientific_discovery": [
        # Scientific / research / evidence language
        r"\b(study|research|evidence|data|hypothesis|experiment|prove|theory)\b",
        r"(دراسة|بحث|دليل|بيانات|فرضية|تجربة|نظرية|إثبات)",
    ],
    "mrs_detector": [
        # Memory reframing, revisionism, gaslighting, crisis
        r"\b(remember|said|told|promised|never|always|lied|suicide|kill)\b",
        r"(تذكر|قلت|وعدت|أبدا|دائما|كذبت|انتحار|أقتل|أموت)",
    ],
    "drp_observer": [
        # Harmful request indicators (DRP only fires on non-EXECUTE)
        r"\b(how to|make|build|create|destroy|hack|break|steal|weapon)\b",
        r"(كيف أسوي|أصنع|أدمر|أخترق|أسرق|سلاح)",
    ],
    "ethical_question_compiler": [
        # Ethical boundary probing
        r"\b(allowed|forbidden|legal|illegal|okay to|can i|is it wrong)\b",
        r"(مسموح|ممنوع|قانوني|غير قانوني|يجوز|حرام|حلال|عيب)",
    ],
    "cultural_opacity": [
        # Culturally-loaded terms, idioms, dialect
        r"\b(tradition|custom|culture|honor|shame|taboo|belief)\b",
        r"(عرف|عادة|ثقافة|شرف|عيب|حشمة|تقاليد|عقيدة)",
    ],
}

# Domain-based activation: domains that always trigger specific observers
_DOMAIN_TRIGGERS: dict[str, Set[str]] = {
    "healthcare": {
        "mrs_detector", "pvm_detector", "ethical_question_compiler",
        "uncertainty_detector", "cold_os",
    },
    "medical": {
        "mrs_detector", "pvm_detector", "ethical_question_compiler",
        "uncertainty_detector", "cold_os",
    },
    "legal": {
        "ethical_question_compiler", "uncertainty_detector",
        "cold_os", "psp_detector",
    },
    "financial": {
        "ethical_question_compiler", "uncertainty_detector",
        "psp_detector", "cold_os",
    },
    "education": {
        "scientific_discovery", "uncertainty_detector",
        "cultural_opacity",
    },
    "religious": {
        "cultural_opacity", "ethical_question_compiler",
        "cold_os", "dual_root_engine",
    },
    "crisis": {
        "mrs_detector", "pvm_detector", "cold_os",
        "ethical_question_compiler", "drp_observer",
    },
    "scientific": {
        "scientific_discovery", "uncertainty_detector",
        "ethical_question_compiler",
    },
}

# S-decision triggers: non-EXECUTE decisions activate specific observers
_DECISION_TRIGGERS: dict[str, Set[str]] = {
    "SAFE_FREEZE": set(ALL_POST_S_OBSERVERS),   # activate ALL
    "SAFE_STOP": set(ALL_POST_S_OBSERVERS),      # activate ALL
    "CLARIFY": {
        "psp_detector", "uncertainty_detector", "cold_os",
        "ethical_question_compiler", "cultural_opacity",
        "dual_root_engine",
    },
}


# ═══════════════════════════════════════════════════════════
#  SparseActivationGate — the core logic
# ═══════════════════════════════════════════════════════════

class SparseActivationGate:
    """
    Lightweight pre-filter that decides WHICH observers to activate.

    The gate examines S(d) results, text patterns, domain, and signals
    to recommend a subset of observers. It NEVER suppresses safety-critical
    observers when harm signals are elevated.

    Usage:
        gate = SparseActivationGate()
        decision = gate.decide(ctx, phase=ObserverPhase.POST_S)
        # decision.active_observers is the set of names to run

    Authority:
        CAN_BLOCK_RUNTIME = False — the gate only recommends.
        The ObserverRegistry can ignore the gate and run everything.
    """

    # ── B-prime contract ──
    CAN_BLOCK_RUNTIME: bool = False
    CAN_SUPPRESS_SAFETY: bool = False

    # ── Threshold configuration ──
    # These define the fast/slow/middle path boundaries.
    # They are class-level so they can be overridden for testing.

    FAST_PATH_S_MIN: float = 0.85       # S must be above this for fast path
    FAST_PATH_H_MAX: float = 0.15       # H must be below this for fast path
    SLOW_PATH_S_MAX: float = 0.5        # S below this → slow path
    SLOW_PATH_H_MIN: float = 0.4        # H above this → slow path
    SAFETY_CRITICAL_H_MIN: float = 0.3  # H above this → safety-critical always on

    def __init__(
        self,
        *,
        post_s_observers: Optional[FrozenSet[str]] = None,
        post_output_observers: Optional[FrozenSet[str]] = None,
        boot_observers: Optional[FrozenSet[str]] = None,
        safety_critical: Optional[FrozenSet[str]] = None,
        minimal_observers: Optional[FrozenSet[str]] = None,
    ):
        """
        Initialise the gate.

        All parameters are optional — defaults use the module-level
        constants derived from the observer registry. Override for testing
        or for registries with different observer sets.
        """
        self._post_s = post_s_observers or ALL_POST_S_OBSERVERS
        self._post_output = post_output_observers or ALL_POST_OUTPUT_OBSERVERS
        self._boot = boot_observers or ALL_BOOT_OBSERVERS
        self._safety_critical = safety_critical or SAFETY_CRITICAL_OBSERVERS
        self._minimal = minimal_observers or MINIMAL_OBSERVERS

        # Pre-compile regex patterns for performance
        self._compiled_patterns: dict[str, list[re.Pattern]] = {}
        for obs_name, patterns in _PATTERN_TRIGGERS.items():
            self._compiled_patterns[obs_name] = [
                re.compile(p, re.IGNORECASE | re.UNICODE)
                for p in patterns
            ]

    # ─────────────────────────────────────────────────
    #  Main entry point
    # ─────────────────────────────────────────────────

    def decide(
        self,
        ctx: ObserverContext,
        phase: ObserverPhase = ObserverPhase.POST_S,
    ) -> ActivationDecision:
        """
        Decide which observers to activate for this context and phase.

        Returns an ActivationDecision with the set of observer names
        to activate, the set to skip, the path taken, and a reason.
        """
        # BOOT phase: always all boot observers, nothing else
        if phase == ObserverPhase.BOOT:
            return ActivationDecision(
                active_observers=frozenset(self._boot),
                skipped_observers=frozenset(),
                path=ActivationPath.BOOT,
                reason="Boot phase — all boot observers activated.",
            )

        # POST_OUTPUT phase: always all output observers
        if phase == ObserverPhase.POST_OUTPUT:
            return ActivationDecision(
                active_observers=frozenset(self._post_output),
                skipped_observers=frozenset(),
                path=ActivationPath.POST_OUTPUT,
                reason="Post-output phase — all output observers activated.",
            )

        # POST_S phase: apply sparse activation logic
        return self._decide_post_s(ctx)

    # ─────────────────────────────────────────────────
    #  POST_S decision logic
    # ─────────────────────────────────────────────────

    def _decide_post_s(self, ctx: ObserverContext) -> ActivationDecision:
        """Core sparse activation logic for POST_S phase."""

        # Extract signals from S result
        s_result = ctx.s_result or {}
        S = s_result.get("S", 0.5)
        H = s_result.get("H", 0.0)
        I = s_result.get("I", 0.5)
        E = s_result.get("E", 0.0)
        decision = s_result.get("decision", "")

        # ── Decision-based triggers ──
        # Non-EXECUTE decisions from S(d) escalate to slow path
        if decision in ("SAFE_FREEZE", "SAFE_STOP"):
            return self._slow_path(
                reason=f"S(d) decision is {decision} — full activation required.",
                signals=("decision:" + decision,),
            )

        # ── SLOW PATH — potentially unsafe ──
        if S < self.SLOW_PATH_S_MAX or H > self.SLOW_PATH_H_MIN:
            signals = []
            if S < self.SLOW_PATH_S_MAX:
                signals.append(f"S={S:.2f}<{self.SLOW_PATH_S_MAX}")
            if H > self.SLOW_PATH_H_MIN:
                signals.append(f"H={H:.2f}>{self.SLOW_PATH_H_MIN}")
            return self._slow_path(
                reason=f"Slow path — elevated risk signals: {', '.join(signals)}.",
                signals=tuple(signals),
            )

        # ── FAST PATH — clearly safe ──
        if S > self.FAST_PATH_S_MIN and H < self.FAST_PATH_H_MAX:
            # Even on fast path, check for text patterns that override
            pattern_matches = self._match_patterns(ctx.message)
            if not pattern_matches:
                return self._fast_path(
                    reason=f"Fast path — S={S:.2f}>{self.FAST_PATH_S_MIN}, "
                           f"H={H:.2f}<{self.FAST_PATH_H_MAX}, no pattern triggers.",
                )
            # Patterns found on "safe" input: add matched observers to minimal set
            active = set(self._minimal) | pattern_matches
            skipped = self._post_s - active
            return ActivationDecision(
                active_observers=frozenset(active),
                skipped_observers=frozenset(skipped),
                path=ActivationPath.FAST,
                reason=f"Fast path with pattern overrides — S={S:.2f}, H={H:.2f}. "
                       f"Patterns matched: {', '.join(sorted(pattern_matches))}.",
                signals_detected=tuple(sorted(pattern_matches)),
            )

        # ── MIDDLE PATH — selective activation ──
        return self._middle_path(ctx, S=S, H=H, I=I, E=E, decision=decision)

    # ─────────────────────────────────────────────────
    #  Path implementations
    # ─────────────────────────────────────────────────

    def _fast_path(self, reason: str) -> ActivationDecision:
        """Only minimal observers. Maximum efficiency."""
        skipped = self._post_s - self._minimal
        return ActivationDecision(
            active_observers=frozenset(self._minimal),
            skipped_observers=frozenset(skipped),
            path=ActivationPath.FAST,
            reason=reason,
        )

    def _slow_path(
        self, reason: str, signals: tuple = ()
    ) -> ActivationDecision:
        """All observers. Maximum safety."""
        return ActivationDecision(
            active_observers=frozenset(self._post_s),
            skipped_observers=frozenset(),
            path=ActivationPath.SLOW,
            reason=reason,
            signals_detected=signals,
        )

    def _middle_path(
        self,
        ctx: ObserverContext,
        *,
        S: float,
        H: float,
        I: float,
        E: float,
        decision: str,
    ) -> ActivationDecision:
        """
        Selective activation based on signal matching.

        Starts with the minimal set, then adds observers based on:
        1. Safety-critical observers if H > threshold
        2. Decision-based triggers (CLARIFY adds specific observers)
        3. Domain-based triggers
        4. Pattern-based triggers (text analysis)
        5. Signal-strength triggers (I, E thresholds)
        """
        active: Set[str] = set(self._minimal)
        signals: list[str] = []

        # 1. Safety-critical if H is elevated
        if H > self.SAFETY_CRITICAL_H_MIN:
            active |= self._safety_critical
            signals.append(f"H={H:.2f}>{self.SAFETY_CRITICAL_H_MIN}→safety_critical")

        # 2. Decision-based triggers
        if decision in _DECISION_TRIGGERS:
            triggered = _DECISION_TRIGGERS[decision]
            # Only add observers that are in our known set
            active |= (triggered & self._post_s)
            signals.append(f"decision:{decision}")

        # 3. Domain-based triggers
        domain_lower = ctx.domain.lower() if ctx.domain else "general"
        if domain_lower in _DOMAIN_TRIGGERS:
            triggered = _DOMAIN_TRIGGERS[domain_lower]
            active |= (triggered & self._post_s)
            signals.append(f"domain:{domain_lower}")

        # 4. Pattern-based triggers
        pattern_matches = self._match_patterns(ctx.message)
        if pattern_matches:
            active |= pattern_matches
            signals.append(f"patterns:{','.join(sorted(pattern_matches))}")

        # 5. Signal-strength triggers
        # Low intent clarity → add uncertainty + PSP detectors
        if I < 0.3:
            active.add("uncertainty_detector")
            active.add("psp_detector")
            signals.append(f"I={I:.2f}<0.3→uncertainty+psp")

        # High emotion → add PVM + maqam + MRS
        if E > 0.5:
            active.add("pvm_detector")
            active.add("maqam_architecture")
            active.add("mrs_detector")
            signals.append(f"E={E:.2f}>0.5→pvm+maqam+mrs")

        # Moderate H (not slow path, but not negligible)
        # Already handled by safety_critical check above if > 0.3
        # Add DRP if H is moderate (DRP analyses harmful requests)
        if H > 0.2:
            active.add("drp_observer")
            signals.append(f"H={H:.2f}>0.2→drp")

        # Intersect with known observers (don't activate unknowns)
        active = active & self._post_s

        skipped = self._post_s - active
        return ActivationDecision(
            active_observers=frozenset(active),
            skipped_observers=frozenset(skipped),
            path=ActivationPath.MIDDLE,
            reason=f"Middle path — S={S:.2f}, H={H:.2f}, I={I:.2f}, E={E:.2f}. "
                   f"Signals: {'; '.join(signals) if signals else 'minimal only'}.",
            signals_detected=tuple(signals),
        )

    # ─────────────────────────────────────────────────
    #  Pattern matching
    # ─────────────────────────────────────────────────

    def _match_patterns(self, text: str) -> Set[str]:
        """
        Scan text for patterns that trigger specific observers.

        Returns the set of observer names whose patterns matched.
        """
        if not text:
            return set()

        matched: Set[str] = set()
        for obs_name, compiled in self._compiled_patterns.items():
            # Only match observers that are in our known set
            if obs_name not in self._post_s:
                continue
            for pattern in compiled:
                if pattern.search(text):
                    matched.add(obs_name)
                    break  # one match per observer is enough
        return matched

    # ─────────────────────────────────────────────────
    #  Introspection / audit helpers
    # ─────────────────────────────────────────────────

    def get_observer_sets(self) -> dict[str, FrozenSet[str]]:
        """Return all observer classification sets for audit/debugging."""
        return {
            "post_s": self._post_s,
            "post_output": self._post_output,
            "boot": self._boot,
            "safety_critical": self._safety_critical,
            "minimal": self._minimal,
        }

    @staticmethod
    def activation_ratio(decision: ActivationDecision) -> float:
        """
        Compute what fraction of available observers were activated.

        Returns a float in [0.0, 1.0]. Useful for metrics:
        a low ratio means the gate is saving work efficiently.
        """
        total = len(decision.active_observers) + len(decision.skipped_observers)
        if total == 0:
            return 1.0
        return len(decision.active_observers) / total


# ═══════════════════════════════════════════════════════════
#  Convenience: build a gate with default configuration
# ═══════════════════════════════════════════════════════════

def build_gate() -> SparseActivationGate:
    """Build a SparseActivationGate with default observer sets."""
    return SparseActivationGate()
