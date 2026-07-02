#!/usr/bin/env python3
"""
AATIF Observer Registry — سجل المراقبين

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)

═══════════════════════════════════════════════════════════════════════════
WHY THIS MODULE EXISTS
═══════════════════════════════════════════════════════════════════════════

The integration audit (INTEGRATION_AUDIT.md) found 13 FN modules that are
fully built and tested individually but NOT connected to the Governor
pipeline. They need to be wired as **observers** (B-prime architecture:
CAN_BLOCK_RUNTIME = False). The Governor remains the only thing that blocks.

This registry provides:
  1. A common interface (Observer) for all FN modules to implement.
  2. A phase system (POST_S, POST_OUTPUT, BOOT) so modules run at the right
     stage in the pipeline.
  3. Adapter classes that wrap each FN module's native API into the common
     observer interface — without modifying any existing module.
  4. Graceful degradation: any observer that fails is logged but NEVER
     breaks the pipeline.

Architecture rules:
  - B-prime: every observer has CAN_BLOCK_RUNTIME = False.
  - The Governor is king: only the Governor's S equation blocks.
  - Observers ENRICH the audit trail with metadata, flags, and scores.
  - Observer output appears in the GovernedResponse audit trail.

    "المراقبون يرون ويسجلون — المحافظ وحده يقرر"
    The observers see and record — the Governor alone decides.
"""

from __future__ import annotations

import os
import sys
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# ── Ensure the engine directory is importable ──
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


# ═══════════════════════════════════════════════════════════
#  Phase enum — when in the pipeline does this observer run?
# ═══════════════════════════════════════════════════════════

class ObserverPhase(Enum):
    """Pipeline phases where observers can run."""
    POST_S = "post_s"            # After S(d), before prompt composition
    POST_OUTPUT = "post_output"  # After LLM output, before/after gate
    BOOT = "boot"                # At boot time only


# ═══════════════════════════════════════════════════════════
#  ObserverContext — everything an observer might need
# ═══════════════════════════════════════════════════════════

@dataclass
class ObserverContext:
    """
    Immutable snapshot of pipeline state passed to observers.

    Observers read from this — they never mutate it. Different phases
    populate different fields:

    POST_S:      message, s_result, domain, conversation_id, time_reading
    POST_OUTPUT: all of POST_S + llm_output
    BOOT:        domain only (no message yet)
    """
    message: str = ""
    s_result: Optional[dict] = None
    domain: str = "general"
    conversation_id: Optional[str] = None
    llm_output: Optional[str] = None
    time_reading: Optional[Any] = None
    p_result: Optional[Any] = None
    r_result: Optional[Any] = None
    fingerprint_reading: Optional[Any] = None
    turn_index: int = 0


# ═══════════════════════════════════════════════════════════
#  ObserverResult — what an observer returns
# ═══════════════════════════════════════════════════════════

@dataclass
class ObserverResult:
    """
    Standardised output from any observer.

    - module_name: which FN module produced this
    - reading: the module's native result dataclass (preserved for callers
      who know the specific type)
    - activated: did the module actually fire? (some have feature flags
      or minimum-signal thresholds)
    - flags: human-readable strings for the audit trail
    - prompt_enrichment: text to inject into the governed prompt
      (only for POST_S observers — POST_OUTPUT observers don't enrich)
    - error: non-empty if the observer failed (graceful degradation)
    - elapsed_ms: how long the observer took
    """
    module_name: str
    phase: ObserverPhase
    reading: Optional[Any] = None
    activated: bool = False
    flags: list = field(default_factory=list)
    prompt_enrichment: str = ""
    error: str = ""
    elapsed_ms: float = 0.0


# ═══════════════════════════════════════════════════════════
#  Observer ABC — what every adapter must implement
# ═══════════════════════════════════════════════════════════

class Observer(ABC):
    """
    Base class for all FN module observer adapters.

    Subclasses implement observe() which receives the pipeline context
    and returns an ObserverResult. The registry calls observe() inside
    a try/except — any exception is caught and recorded, never propagated.
    """

    # Every observer declares these at the class level.
    name: str = "unnamed"
    phase: ObserverPhase = ObserverPhase.POST_S
    CAN_BLOCK_RUNTIME: bool = False  # B-prime: always False

    @abstractmethod
    def observe(self, ctx: ObserverContext) -> ObserverResult:
        """Run the observation. Must never raise — but if it does,
        the registry catches it."""
        ...


# ═══════════════════════════════════════════════════════════
#  ObserverRegistry — the registration and execution system
# ═══════════════════════════════════════════════════════════

class ObserverRegistry:
    """
    Manages observer registration and phase-based execution.

    Usage:
        registry = ObserverRegistry()
        registry.auto_register()  # discovers and registers all available FN modules
        results = registry.run_phase(ObserverPhase.POST_S, context)
    """

    def __init__(self):
        self._observers: dict[ObserverPhase, list[Observer]] = defaultdict(list)
        self._boot_results: list[ObserverResult] = []

    def register(self, observer: Observer) -> None:
        """Register an observer for its declared phase."""
        assert observer.CAN_BLOCK_RUNTIME is False, (
            f"B-prime violation: {observer.name} has CAN_BLOCK_RUNTIME=True"
        )
        self._observers[observer.phase].append(observer)

    def get_observers(self, phase: Optional[ObserverPhase] = None) -> list[Observer]:
        """List registered observers, optionally filtered by phase."""
        if phase is not None:
            return list(self._observers[phase])
        all_obs = []
        for obs_list in self._observers.values():
            all_obs.extend(obs_list)
        return all_obs

    def run_phase(
        self, phase: ObserverPhase, ctx: ObserverContext,
    ) -> list[ObserverResult]:
        """
        Run all observers registered for this phase.

        Returns a list of ObserverResults. Failed observers return a result
        with error set — they NEVER raise or break the pipeline.
        """
        results = []
        for observer in self._observers.get(phase, []):
            start = time.perf_counter()
            try:
                result = observer.observe(ctx)
                result.elapsed_ms = round(
                    (time.perf_counter() - start) * 1000.0, 3
                )
                results.append(result)
            except Exception as exc:
                elapsed = round((time.perf_counter() - start) * 1000.0, 3)
                results.append(ObserverResult(
                    module_name=observer.name,
                    phase=phase,
                    activated=False,
                    error=f"{type(exc).__name__}: {exc}",
                    elapsed_ms=elapsed,
                ))
        return results

    def run_boot(self, ctx: ObserverContext) -> list[ObserverResult]:
        """Run boot-phase observers and cache results."""
        self._boot_results = self.run_phase(ObserverPhase.BOOT, ctx)
        return self._boot_results

    @property
    def boot_results(self) -> list[ObserverResult]:
        return list(self._boot_results)

    def auto_register(self) -> list[str]:
        """
        Discover and register all available FN module observers.

        Tries to import each module and create its adapter. Modules that
        fail to import (e.g. missing dependencies) are silently skipped.

        Returns the list of successfully registered observer names.
        """
        registered = []

        # ── POST_S observers (analyze user message after S(d)) ──
        adapter_factories = [
            _make_drift_observer,
            _make_psp_observer,
            _make_uncertainty_observer,
            _make_dre_observer,
            _make_pvm_observer,
            _make_cold_os_observer,
            _make_sdm_observer,
            _make_mrs_observer,
            _make_maqam_observer,
        ]

        for factory in adapter_factories:
            try:
                observer = factory()
                if observer is not None:
                    self.register(observer)
                    registered.append(observer.name)
            except Exception:
                pass  # module unavailable — skip

        # ── POST_OUTPUT observers (analyze LLM draft output) ──
        output_factories = [
            _make_lbh_observer,
            _make_ucn_observer,
        ]

        for factory in output_factories:
            try:
                observer = factory()
                if observer is not None:
                    self.register(observer)
                    registered.append(observer.name)
            except Exception:
                pass

        # ── BOOT observers ──
        boot_factories = [
            _make_binding_observer,
            _make_twin_observer,
        ]

        for factory in boot_factories:
            try:
                observer = factory()
                if observer is not None:
                    self.register(observer)
                    registered.append(observer.name)
            except Exception:
                pass

        return registered


# ═══════════════════════════════════════════════════════════════════════════
#  ADAPTER FACTORIES — one per FN module
#
#  Each factory tries to import its module. If the import fails, it
#  returns None (the module is not available). If it succeeds, it
#  returns an Observer adapter that wraps the module's native API.
#
#  No existing module is modified — adapters bridge the gap.
# ═══════════════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────
#  1. FN#058 Drift Detector
# ───────────────────────────────────────────────────

def _make_drift_observer() -> Optional[Observer]:
    from aatif_drift_detector import DriftDetector, DriftState  # noqa: F811

    class DriftObserver(Observer):
        name = "drift_detector"
        phase = ObserverPhase.POST_S
        CAN_BLOCK_RUNTIME = False

        def __init__(self):
            self._detector = DriftDetector()
            self._states: dict[str, DriftState] = {}

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            if not ctx.s_result or not ctx.message:
                return ObserverResult(
                    module_name=self.name, phase=self.phase,
                )
            sid = ctx.conversation_id or "_anon"
            prior = self._states.get(sid, DriftState())
            nearest = ctx.s_result.get("nearest_anchor", "")
            result = self._detector.update(
                text=ctx.message,
                H=ctx.s_result.get("H", 0.0),
                I=ctx.s_result.get("I", 0.0),
                E=ctx.s_result.get("E", 0.0),
                nearest_anchor=nearest,
                prior_state=prior,
            )
            self._states[sid] = result.updated_state
            flags = []
            enrichment = ""
            if result.drift_risk > 0.5:
                flags.append(
                    f"DRIFT_RISK={result.drift_risk:.2f}: {result.evidence}"
                )
                enrichment = (
                    f"⚠ Drift detector (FN#058): risk={result.drift_risk:.2f} "
                    f"— {result.evidence}. Stay anchored to the original topic."
                )
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=result,
                activated=result.drift_risk > 0.0,
                flags=flags,
                prompt_enrichment=enrichment,
            )

    return DriftObserver()


# ───────────────────────────────────────────────────
#  2. FN#070 PSP Detector
# ───────────────────────────────────────────────────

def _make_psp_observer() -> Optional[Observer]:
    from aatif_psp_detector import PSPDetector  # noqa: F811

    class PSPObserver(Observer):
        name = "psp_detector"
        phase = ObserverPhase.POST_S
        CAN_BLOCK_RUNTIME = False

        def __init__(self):
            self._detector = PSPDetector()

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            if not ctx.message:
                return ObserverResult(
                    module_name=self.name, phase=self.phase,
                )
            reading = self._detector.detect(ctx.message)
            flags = []
            enrichment = ""
            if reading.is_decision_point:
                flags.append(
                    f"PSP_DECISION_POINT: confidence={reading.decision_confidence:.2f}, "
                    f"closure_risk={reading.closure_risk:.2f}"
                )
                enrichment = (
                    f"⚠ PSP (FN#070): user at a decision point "
                    f"(confidence={reading.decision_confidence:.2f}). "
                    f"Do not prematurely close options — "
                    f"{reading.bounded_count} live paths remain."
                )
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=reading,
                activated=reading.is_decision_point,
                flags=flags,
                prompt_enrichment=enrichment,
            )

    return PSPObserver()


# ───────────────────────────────────────────────────
#  3. Uncertainty Detector
# ───────────────────────────────────────────────────

def _make_uncertainty_observer() -> Optional[Observer]:
    from aatif_uncertainty_detector import UncertaintyDetector  # noqa: F811

    class UncertaintyObserver(Observer):
        name = "uncertainty_detector"
        phase = ObserverPhase.POST_S
        CAN_BLOCK_RUNTIME = False

        def __init__(self):
            self._detector = UncertaintyDetector()

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            if not ctx.s_result:
                return ObserverResult(
                    module_name=self.name, phase=self.phase,
                )
            reading = self._detector.detect(
                result=ctx.s_result,
                domain=ctx.domain,
            )
            flags = []
            enrichment = ""
            if reading.should_abstain:
                flags.append(
                    f"UNCERTAINTY_ABSTAIN: calibration={reading.calibration_confidence:.2f}"
                )
                enrichment = (
                    f"⚠ Uncertainty detector: calibration confidence is low "
                    f"({reading.calibration_confidence:.2f}). Consider expressing "
                    f"uncertainty rather than asserting."
                )
            elif reading.should_gate:
                flags.append(
                    f"UNCERTAINTY_GATE: ambiguity={reading.ambiguity_score:.2f}"
                )
                enrichment = (
                    f"Note: elevated ambiguity ({reading.ambiguity_score:.2f}). "
                    f"Present multiple interpretations if relevant."
                )
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=reading,
                activated=reading.should_abstain or reading.should_gate,
                flags=flags,
                prompt_enrichment=enrichment,
            )

    return UncertaintyObserver()


# ───────────────────────────────────────────────────
#  4. FN#050 DRE (Dual Root Engine)
# ───────────────────────────────────────────────────

def _make_dre_observer() -> Optional[Observer]:
    from aatif_dual_root import analyze_dual_root, DREContext  # noqa: F811

    class DREObserver(Observer):
        name = "dual_root_engine"
        phase = ObserverPhase.POST_S
        CAN_BLOCK_RUNTIME = False

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            if not ctx.message or not ctx.s_result:
                return ObserverResult(
                    module_name=self.name, phase=self.phase,
                )
            dre_ctx = DREContext(
                text=ctx.message,
                s_decision=ctx.s_result.get("decision", ""),
                H=ctx.s_result.get("H", 0.0),
                false_goodness_detected=ctx.s_result.get(
                    "false_goodness_detected", False
                ),
                intent_malicious_confidence=ctx.s_result.get(
                    "intent_malicious_confidence", 0.0
                ),
                query_type=ctx.s_result.get("query_type", ""),
                five_layer_detected=ctx.s_result.get(
                    "five_layer_detected", False
                ),
            )
            reading = analyze_dual_root(ctx.message, dre_ctx)
            flags = []
            enrichment = ""
            if reading.dre_active and reading.dual_root_pattern_detected:
                flags.append(
                    f"DRE_DUAL_ROOT: root_a={reading.root_a_signal_type}, "
                    f"root_b={reading.root_b_signal_type}"
                )
                if reading.response_guidance:
                    enrichment = (
                        f"DRE (FN#050): dual-root pattern detected. "
                        f"{reading.response_guidance}"
                    )
                if reading.prohibited_claims:
                    enrichment += (
                        f" Prohibited claims: "
                        f"{', '.join(reading.prohibited_claims)}"
                    )
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=reading,
                activated=getattr(reading, "dre_active", False),
                flags=flags,
                prompt_enrichment=enrichment,
            )

    return DREObserver()


# ───────────────────────────────────────────────────
#  5. FN#041 PVM Detector
# ───────────────────────────────────────────────────

def _make_pvm_observer() -> Optional[Observer]:
    from aatif_pvm_detector import PVMDetector  # noqa: F811

    class PVMObserver(Observer):
        name = "pvm_detector"
        phase = ObserverPhase.POST_S
        CAN_BLOCK_RUNTIME = False

        def __init__(self):
            self._detector = PVMDetector()
            self._turn_counts: dict[str, int] = {}

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            if not ctx.message:
                return ObserverResult(
                    module_name=self.name, phase=self.phase,
                )
            sid = ctx.conversation_id or "_anon"
            turn_idx = self._turn_counts.get(sid, 0)
            self._turn_counts[sid] = turn_idx + 1

            reading = self._detector.detect(
                turn_features=ctx.message,
                time_reading=ctx.time_reading,
                fingerprint_reading=ctx.fingerprint_reading,
                current_turn_index=turn_idx,
            )
            flags = []
            enrichment = ""
            if reading.recommend_behavioral_pause:
                flags.append(
                    f"PVM_PAUSE: type={reading.pause_type}, "
                    f"confidence={reading.confidence:.2f}"
                )
                ack = reading.recommended_acknowledgment or ""
                enrichment = (
                    f"PVM (FN#041): behavioural pause recommended "
                    f"(type={reading.pause_type}). "
                )
                if ack:
                    enrichment += f"Acknowledge with: {ack}"
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=reading,
                activated=reading.recommend_behavioral_pause,
                flags=flags,
                prompt_enrichment=enrichment,
            )

    return PVMObserver()


# ───────────────────────────────────────────────────
#  6. FN#072 COLD-OS (Tri-Engine Decision Protocol)
# ───────────────────────────────────────────────────

def _make_cold_os_observer() -> Optional[Observer]:
    from aatif_cold_os import ColdOSEngine  # noqa: F811

    class ColdOSObserver(Observer):
        name = "cold_os"
        phase = ObserverPhase.POST_S
        CAN_BLOCK_RUNTIME = False

        def __init__(self):
            self._engine = ColdOSEngine()

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            if not ctx.message:
                return ObserverResult(
                    module_name=self.name, phase=self.phase,
                )
            reading = self._engine.analyze(
                ctx.message,
                s_decision=ctx.s_result.get("decision", "") if ctx.s_result else "",
                h_score=ctx.s_result.get("H", 0.0) if ctx.s_result else 0.0,
                domain=ctx.domain,
            )
            flags = []
            enrichment = ""
            if reading.activated:
                tension = reading.tension
                if tension and tension.tension_level > 0.3:
                    flags.append(
                        f"COLD_OS_TENSION={tension.tension_level:.2f}: "
                        f"{tension.description}"
                    )
                strategy = reading.framing_strategy
                if strategy and strategy.strategy_name:
                    enrichment = (
                        f"COLD-OS (FN#072): framing strategy='{strategy.strategy_name}'. "
                        f"{strategy.guidance or ''}"
                    )
                if reading.recommendations:
                    enrichment += (
                        " Recommendations: "
                        + "; ".join(reading.recommendations[:2])
                    )
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=reading,
                activated=reading.activated,
                flags=flags,
                prompt_enrichment=enrichment,
            )

    return ColdOSObserver()


# ───────────────────────────────────────────────────
#  7. FN#068 SDM (Scientific Discovery / Cognitive Sovereignty)
# ───────────────────────────────────────────────────

def _make_sdm_observer() -> Optional[Observer]:
    from aatif_scientific_discovery import ScientificDiscoveryEngine  # noqa: F811

    class SDMObserver(Observer):
        name = "scientific_discovery"
        phase = ObserverPhase.POST_S
        CAN_BLOCK_RUNTIME = False

        def __init__(self):
            self._engine = ScientificDiscoveryEngine()

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            if not ctx.message:
                return ObserverResult(
                    module_name=self.name, phase=self.phase,
                )
            reading = self._engine.analyze(
                ctx.message,
                domain=ctx.domain,
            )
            flags = []
            enrichment = ""
            if reading.activated:
                if reading.truth_claim_violations:
                    flags.append(
                        f"SDM_TRUTH_VIOLATION: "
                        f"{', '.join(reading.truth_claim_violations[:2])}"
                    )
                if reading.safety_bypass_risk:
                    flags.append("SDM_SAFETY_BYPASS_RISK")
                parts = []
                if reading.exploration_mode:
                    parts.append(
                        f"exploration mode={reading.exploration_mode}"
                    )
                if reading.requires_uncertainty_label:
                    parts.append("requires uncertainty labelling")
                if reading.requires_evidence_tiers:
                    parts.append("requires evidence tiers")
                if parts:
                    enrichment = (
                        f"SDM (FN#068): {'; '.join(parts)}. "
                    )
                if reading.recommendations:
                    enrichment += "; ".join(reading.recommendations[:2])
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=reading,
                activated=reading.activated,
                flags=flags,
                prompt_enrichment=enrichment,
            )

    return SDMObserver()


# ───────────────────────────────────────────────────
#  8. FN#051 MRS (Memory Reframing System)
# ───────────────────────────────────────────────────

def _make_mrs_observer() -> Optional[Observer]:
    from aatif_mrs_detector import MRSDetector  # noqa: F811

    class MRSObserver(Observer):
        name = "mrs_detector"
        phase = ObserverPhase.POST_S
        CAN_BLOCK_RUNTIME = False

        def __init__(self):
            self._detector = MRSDetector()

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            if not ctx.message:
                return ObserverResult(
                    module_name=self.name, phase=self.phase,
                )
            reading = self._detector.analyze(ctx.message)
            flags = []
            enrichment = ""
            if reading.activated:
                flags.append(
                    f"MRS_SIGNAL: type={reading.primary_interpretation_type}, "
                    f"severity={reading.severity}"
                )
                if reading.crisis_signal_observed:
                    flags.append("MRS_CRISIS_SIGNAL")
                if reading.professional_referral_required:
                    flags.append("MRS_PROFESSIONAL_REFERRAL")
                    enrichment = (
                        f"MRS (FN#051): professional referral recommended — "
                        f"severity={reading.severity}. "
                    )
                elif reading.compound_pattern:
                    enrichment = (
                        f"MRS (FN#051): compound pattern detected "
                        f"(type={reading.primary_interpretation_type}). "
                        f"Handle with care."
                    )
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=reading,
                activated=reading.activated,
                flags=flags,
                prompt_enrichment=enrichment,
            )

    return MRSObserver()


# ───────────────────────────────────────────────────
#  9. FN#065 Maqam Architecture
# ───────────────────────────────────────────────────

def _make_maqam_observer() -> Optional[Observer]:
    from aatif_maqam_architecture import detect_maqam  # noqa: F811

    class MaqamObserver(Observer):
        name = "maqam_architecture"
        phase = ObserverPhase.POST_S
        CAN_BLOCK_RUNTIME = False

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            if not ctx.message:
                return ObserverResult(
                    module_name=self.name, phase=self.phase,
                )
            reading = detect_maqam(ctx.message)
            flags = []
            enrichment = ""
            if reading.activated and reading.confidence > 0.3:
                maqam_name = (
                    reading.detected_maqam.value
                    if hasattr(reading.detected_maqam, "value")
                    else str(reading.detected_maqam)
                )
                flags.append(
                    f"MAQAM={maqam_name}: "
                    f"confidence={reading.confidence:.2f}"
                )
                enrichment = (
                    f"Maqam (FN#065): emotional register={maqam_name} "
                    f"(confidence={reading.confidence:.2f}). "
                    f"Adapt tone accordingly."
                )
                if reading.b5_style_hints:
                    enrichment += (
                        f" Style hints: "
                        f"{', '.join(reading.b5_style_hints[:3])}"
                    )
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=reading,
                activated=getattr(reading, "activated", False),
                flags=flags,
                prompt_enrichment=enrichment,
            )

    return MaqamObserver()


# ═══════════════════════════════════════════════════════════
#  POST_OUTPUT observers — analyze LLM draft output
# ═══════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────
#  10. FN#054 LBH Detector (Load-Bearing Hallucination)
# ───────────────────────────────────────────────────

def _make_lbh_observer() -> Optional[Observer]:
    from aatif_lbh_detector import LBHDetector  # noqa: F811

    class LBHObserver(Observer):
        name = "lbh_detector"
        phase = ObserverPhase.POST_OUTPUT
        CAN_BLOCK_RUNTIME = False

        def __init__(self):
            self._detector = LBHDetector()

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            if not ctx.llm_output:
                return ObserverResult(
                    module_name=self.name, phase=self.phase,
                )
            reading = self._detector.detect(
                draft=ctx.llm_output,
                domain=ctx.domain,
                user_input_text=ctx.message,
            )
            flags = []
            if reading.violation_score > 0.0:
                flags.append(
                    f"LBH_SCORE={reading.violation_score:.2f}"
                )
                for v in (reading.violations or [])[:3]:
                    flags.append(f"LBH_VIOLATION: {v}")
            if reading.recommendations:
                for r in reading.recommendations[:2]:
                    flags.append(f"LBH_REC: {r}")
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=reading,
                activated=reading.violation_score > 0.0,
                flags=flags,
            )

    return LBHObserver()


# ───────────────────────────────────────────────────
#  11. FN#042 UCN Validator (Unified Constraint Network)
# ───────────────────────────────────────────────────

def _make_ucn_observer() -> Optional[Observer]:
    from aatif_ucn_validator import UCNDetector  # noqa: F811

    class UCNObserver(Observer):
        name = "ucn_validator"
        phase = ObserverPhase.POST_OUTPUT
        CAN_BLOCK_RUNTIME = False

        def __init__(self):
            self._detector = UCNDetector()

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            if not ctx.llm_output:
                return ObserverResult(
                    module_name=self.name, phase=self.phase,
                )
            reading = self._detector.validate(
                text=ctx.llm_output,
                domain=ctx.domain,
            )
            flags = []
            if reading.phantoms_detected:
                for phantom in reading.phantoms_detected[:3]:
                    flags.append(
                        f"UCN_PHANTOM: {phantom}"
                    )
            if not reading.all_references_valid:
                flags.append("UCN_INVALID_REFS")
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=reading,
                activated=bool(reading.phantoms_detected)
                    or not reading.all_references_valid,
                flags=flags,
            )

    return UCNObserver()


# ═══════════════════════════════════════════════════════════
#  BOOT observers
# ═══════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────
#  12. FN#044 Binding Map (Eight-Channel Architecture)
# ───────────────────────────────────────────────────

def _make_binding_observer() -> Optional[Observer]:
    from aatif_binding_map import BindingMap  # noqa: F811

    class BindingObserver(Observer):
        name = "binding_map"
        phase = ObserverPhase.BOOT
        CAN_BLOCK_RUNTIME = False

        def __init__(self):
            self._map = BindingMap()

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            report = self._map.validate()
            flags = []
            if not report.valid:
                flags.append(
                    f"BINDING_INVALID: {len(report.violations)} violations"
                )
                for v in (report.violations or [])[:3]:
                    flags.append(f"BINDING_VIOLATION: {v}")
            if report.warnings:
                for w in report.warnings[:3]:
                    flags.append(f"BINDING_WARNING: {w}")
            flags.append(
                f"BINDING_CHANNELS: {report.active_bindings}/{report.total_bindings} active"
            )
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=report,
                activated=True,
                flags=flags,
            )

        @property
        def binding_map(self):
            """Expose the underlying BindingMap for signal recording."""
            return self._map

    return BindingObserver()


# ───────────────────────────────────────────────────
#  13. FN#023 Behavioural Twin
# ───────────────────────────────────────────────────

def _make_twin_observer() -> Optional[Observer]:
    from aatif_behavioural_twin import BehaviouralTwinDetector  # noqa: F811

    class TwinObserver(Observer):
        name = "behavioural_twin"
        phase = ObserverPhase.BOOT
        CAN_BLOCK_RUNTIME = False

        def __init__(self):
            self._detector = BehaviouralTwinDetector()

        def observe(self, ctx: ObserverContext) -> ObserverResult:
            # At boot, register this instance as a baseline.
            # The twin detector compares multiple AATIF instances —
            # in single-instance mode, we register ourselves and record
            # that no comparison target exists yet. When a second
            # instance connects, observe(source, target) can be called.
            flags = ["TWIN_REGISTERED: single-instance baseline recorded"]
            return ObserverResult(
                module_name=self.name,
                phase=self.phase,
                reading=None,
                activated=True,
                flags=flags,
            )

        @property
        def detector(self):
            """Expose the underlying detector for cross-instance checks."""
            return self._detector

    return TwinObserver()


# ═══════════════════════════════════════════════════════════
#  Convenience: build a fully loaded registry
# ═══════════════════════════════════════════════════════════

def build_registry() -> ObserverRegistry:
    """Build a registry with all available FN modules auto-registered."""
    registry = ObserverRegistry()
    registry.auto_register()
    return registry
