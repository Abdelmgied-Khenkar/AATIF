#!/usr/bin/env python3
"""
AATIF Binding Map — FN#044 Eight-Channel Binding Architecture

Architecture: B-prime (B')
─────────────────────────────────────────────────────────────────
BindingMap       →  structural/observational (declares, validates, audits)
Governor         →  orchestrator (routes signals through direct method calls)
GovernanceEq (S) →  judicial (computes H_eff, decides S)

Critical Design Rule (Single Mind):
  Only GovernanceEquation can transform inputs into final safety.
  BindingMap is NOT judicial — it declares lawful communication paths
  and annotates what happened.  It never routes, intercepts, blocks,
  or transforms runtime signals.

Design consensus: Claude × ChatGPT, 2026-07-01
Field Note: FN#044 (SBM-5.01 — Binding Channels B1-B8)

"الطبقات لا تتحدث بحرية. كل إشارة تسلك سلكها الخاص."
"Layers do not talk freely. Each signal travels its own wire."

"FN#044 binds the architecture, not the runtime.
 It verifies the legality of channels without becoming a channel itself."

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Tuple

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


# ═══════════════════════════════════════════════════════════════
#  Feature Flag
# ═══════════════════════════════════════════════════════════════

BINDING_MAP_ENABLED = True


# ═══════════════════════════════════════════════════════════════
#  Authority Level Declaration (B-prime contract)
# ═══════════════════════════════════════════════════════════════

AUTHORITY_LEVEL = "B_PRIME_STRUCTURAL_OBSERVATIONAL"
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_PAYLOAD         = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA            = False
CAN_MODIFY_S                = False
CAN_EMIT_JUDICIAL_DECISION = False
CAN_RAISE_BOOT_INTEGRITY_ERROR = True
CAN_EMIT_RUNTIME_AUDIT     = True


# ═══════════════════════════════════════════════════════════════
#  ChannelType — the 8 typed channels (B1-B8)
# ═══════════════════════════════════════════════════════════════

class ChannelType(Enum):
    """Eight communication channels — each carries one type of signal only."""
    B1_IDENTITY       = "B1_IDENTITY"
    B2_CONSTITUTIONAL = "B2_CONSTITUTIONAL"
    B3_MEANING        = "B3_MEANING"
    B4_INTENT         = "B4_INTENT"
    B5_BEHAVIOUR      = "B5_BEHAVIOUR"
    B6_SAFETY         = "B6_SAFETY"
    B7_DRIFT          = "B7_DRIFT"
    B8_EXECUTION      = "B8_EXECUTION"


# ═══════════════════════════════════════════════════════════════
#  Signal type sets — what each channel is allowed to carry
# ═══════════════════════════════════════════════════════════════

CHANNEL_ALLOWED_SIGNALS: Dict[ChannelType, FrozenSet[str]] = {
    ChannelType.B1_IDENTITY: frozenset({
        "FingerprintReading", "TemporalContext", "AuthorityId",
        "RepetitionContext", "UserContext",
    }),
    ChannelType.B2_CONSTITUTIONAL: frozenset({
        "ConstitutionalLaw", "DomainConfig", "GatedProfile",
        "BootVerification", "AuthorityDoctrine",
    }),
    ChannelType.B3_MEANING: frozenset({
        "FiveLayerReading", "LogicProfile", "CollisionResult",
        "ReasoningTrace", "Justification", "MeaningTrace",
        "IntentCandidate",
    }),
    ChannelType.B4_INTENT: frozenset({
        "IntentScore", "IntentVector", "ContextualIntent",
    }),
    ChannelType.B5_BEHAVIOUR: frozenset({
        "StyleRecommendation", "ResponseShape", "RReading",
        "ToneGuidance",
    }),
    ChannelType.B6_SAFETY: frozenset({
        "SafetyDecision", "HScore", "ProtocolAction", "GateVerdict",
        "CoherenceVerdict", "FalseGoodnessBoost", "CalibrationSignal",
        "BindingViolation",
    }),
    ChannelType.B7_DRIFT: frozenset({
        "DriftRisk", "PSPDetection", "UncertaintySignal",
    }),
    ChannelType.B8_EXECUTION: frozenset({
        "GovernedPrompt", "CleanedOutput", "LLMResponse",
    }),
}


# ═══════════════════════════════════════════════════════════════
#  ChannelBinding — one permitted communication path
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ChannelBinding:
    """
    One binding: source_module → target_module through a specific channel.
    Frozen so the canonical map is immutable once constructed.
    """
    source_module: str
    target_module: str
    channel: ChannelType
    signal_types: FrozenSet[str]
    required: bool = True           # required for full integrity
    description: str = ""


# ═══════════════════════════════════════════════════════════════
#  ChannelAuditEntry — what flowed through which channel
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ChannelAuditEntry:
    """
    Records one observed signal on the audit trail.
    Frozen (immutable) — once recorded, cannot be tampered with.

    Fields per design consensus (Q4):
    - sequence_number: monotonic counter (timestamps alone insufficient)
    - timestamp: wall clock for human readability
    - channel: which B1-B8 channel
    - source_module: who sent
    - target_module: who received (may be None for broadcast)
    - signal_type: type name of the payload
    - payload_hash: SHA256 for trace integrity without storing content
    - payload_size_bytes: size tracking
    - binding_status: classification of this signal
    - severity: info / warning / violation / critical_observation
    - runtime_phase: when in the pipeline this occurred
    - duration_ms: BindingMap observation overhead only
    """
    sequence_number: int
    timestamp: float
    channel: ChannelType
    source_module: str
    target_module: Optional[str]
    signal_type: str
    payload_hash: Optional[str] = None
    payload_size_bytes: Optional[int] = None
    binding_status: str = "allowed"     # allowed|unknown|wrong_channel|wrong_type|deprecated
    severity: str = "info"              # info|warning|violation|critical_observation
    runtime_phase: str = "execution"    # boot|pre_s|s_eval|post_s|execution|shutdown
    duration_ms: Optional[float] = None


# ═══════════════════════════════════════════════════════════════
#  BindingIntegrityReport — boot-time validation result
# ═══════════════════════════════════════════════════════════════

@dataclass
class BindingIntegrityReport:
    """Result of boot-time binding validation."""
    valid: bool
    total_bindings: int
    active_bindings: int
    inactive_bindings: int
    missing_channels: List[ChannelType] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
#  Canonical Bindings — the architectural truth
# ═══════════════════════════════════════════════════════════════
#  "What SHOULD exist" — hardcoded per consensus Q6.
#  The canonical map defines lawful architecture.
#  Introspection reports actual architecture.
#  Runtime overlay explains allowed deviations.

def _build_canonical_bindings() -> Tuple[ChannelBinding, ...]:
    """
    Build the complete canonical binding map.

    This is the architectural truth of AATIF OS — every module's
    producer/consumer relationship mapped to the 8 channels.
    """
    return (
        # ── B1: Identity ──
        ChannelBinding(
            source_module="aatif_fingerprint",
            target_module="aatif_governor",
            channel=ChannelType.B1_IDENTITY,
            signal_types=frozenset({"FingerprintReading", "RepetitionContext"}),
            description="User fingerprint → Governor for prompt composition",
        ),
        ChannelBinding(
            source_module="aatif_temporal_memory",
            target_module="aatif_governor",
            channel=ChannelType.B1_IDENTITY,
            signal_types=frozenset({"TemporalContext"}),
            description="Temporal memory context → Governor for time-aware prompts",
        ),
        ChannelBinding(
            source_module="aatif_authority_doctrine",
            target_module="aatif_governor",
            channel=ChannelType.B1_IDENTITY,
            signal_types=frozenset({"AuthorityId"}),
            description="Authority identity → Governor for role-based context",
        ),

        # ── B2: Constitutional ──
        ChannelBinding(
            source_module="aatif_s_equation",
            target_module="aatif_governor",
            channel=ChannelType.B2_CONSTITUTIONAL,
            signal_types=frozenset({"ConstitutionalLaw", "GatedProfile", "DomainConfig"}),
            description="Constitutional constants → Governor",
        ),
        ChannelBinding(
            source_module="aatif_boot_sequence",
            target_module="aatif_governor",
            channel=ChannelType.B2_CONSTITUTIONAL,
            signal_types=frozenset({"BootVerification"}),
            description="Boot integrity result → Governor",
        ),
        ChannelBinding(
            source_module="aatif_authority_doctrine",
            target_module="aatif_governor",
            channel=ChannelType.B2_CONSTITUTIONAL,
            signal_types=frozenset({"AuthorityDoctrine"}),
            description="Authority doctrine rules → Governor",
        ),

        # ── B3: Meaning ──
        ChannelBinding(
            source_module="aatif_five_layer_intent",
            target_module="aatif_governor",
            channel=ChannelType.B3_MEANING,
            signal_types=frozenset({"FiveLayerReading"}),
            description="Five-layer intent analysis → Governor for prompt enrichment",
        ),
        ChannelBinding(
            source_module="aatif_logic_profile_scanner",
            target_module="aatif_governor",
            channel=ChannelType.B3_MEANING,
            signal_types=frozenset({"LogicProfile"}),
            description="Logic profile → Governor for tone adaptation",
        ),
        ChannelBinding(
            source_module="aatif_multi_intent_collision",
            target_module="aatif_governor",
            channel=ChannelType.B3_MEANING,
            signal_types=frozenset({"CollisionResult"}),
            description="Multi-intent collision result → Governor",
        ),
        ChannelBinding(
            source_module="aatif_reasoning_trace",
            target_module="aatif_governor",
            channel=ChannelType.B3_MEANING,
            signal_types=frozenset({"ReasoningTrace"}),
            description="Constitutional reasoning trace → Governor",
        ),
        ChannelBinding(
            source_module="aatif_muhajij",
            target_module="aatif_governor",
            channel=ChannelType.B3_MEANING,
            signal_types=frozenset({"Justification"}),
            description="Audience-adapted justification → Governor",
        ),

        # ── B4: Intent ──
        ChannelBinding(
            source_module="aatif_intent_scorer",
            target_module="aatif_s_equation",
            channel=ChannelType.B4_INTENT,
            signal_types=frozenset({"IntentScore"}),
            description="Intent score (I) → S equation for safety computation",
        ),
        ChannelBinding(
            source_module="aatif_contextual_intent",
            target_module="aatif_governor",
            channel=ChannelType.B4_INTENT,
            signal_types=frozenset({"ContextualIntent"}),
            description="Contextual intent → Governor for enriched I scoring",
        ),

        # ── B5: Behaviour ──
        ChannelBinding(
            source_module="aatif_r_equation",
            target_module="aatif_governor",
            channel=ChannelType.B5_BEHAVIOUR,
            signal_types=frozenset({"RReading", "StyleRecommendation"}),
            description="R equation style result → Governor for prompt style",
        ),
        ChannelBinding(
            source_module="aatif_response_shaper",
            target_module="aatif_governor",
            channel=ChannelType.B5_BEHAVIOUR,
            signal_types=frozenset({"ResponseShape", "ToneGuidance"}),
            description="Response shape → Governor for meaning instructions",
        ),

        # ── B6: Safety ──
        ChannelBinding(
            source_module="aatif_s_equation",
            target_module="aatif_governor",
            channel=ChannelType.B6_SAFETY,
            signal_types=frozenset({"SafetyDecision", "HScore"}),
            description="S decision + H score → Governor for sovereignty",
        ),
        ChannelBinding(
            source_module="aatif_domain_protocols",
            target_module="aatif_governor",
            channel=ChannelType.B6_SAFETY,
            signal_types=frozenset({"ProtocolAction"}),
            description="Protocol action → Governor for P(d) enforcement",
        ),
        ChannelBinding(
            source_module="aatif_output_gate",
            target_module="aatif_governor",
            channel=ChannelType.B6_SAFETY,
            signal_types=frozenset({"GateVerdict"}),
            description="Output gate verdict → Governor for final guard",
        ),
        ChannelBinding(
            source_module="aatif_meta_oversight",
            target_module="aatif_governor",
            channel=ChannelType.B6_SAFETY,
            signal_types=frozenset({"CoherenceVerdict"}),
            description="Meta-oversight coherence → Governor for contradiction check",
        ),
        ChannelBinding(
            source_module="aatif_false_goodness_detector",
            target_module="aatif_s_equation",
            channel=ChannelType.B6_SAFETY,
            signal_types=frozenset({"FalseGoodnessBoost"}),
            description="False goodness H-boost → S equation pre-decision",
        ),

        # ── B7: Drift ──
        ChannelBinding(
            source_module="aatif_drift_detector",
            target_module="aatif_governor",
            channel=ChannelType.B7_DRIFT,
            signal_types=frozenset({"DriftRisk"}),
            description="Drift risk signal → Governor for H_eff computation",
        ),
        ChannelBinding(
            source_module="aatif_psp_detector",
            target_module="aatif_governor",
            channel=ChannelType.B7_DRIFT,
            signal_types=frozenset({"PSPDetection"}),
            description="Prompt-splitting detection → Governor",
        ),
        ChannelBinding(
            source_module="aatif_uncertainty_detector",
            target_module="aatif_governor",
            channel=ChannelType.B7_DRIFT,
            signal_types=frozenset({"UncertaintySignal"}),
            description="Uncertainty signal → Governor",
        ),

        # ── B8: Execution ──
        ChannelBinding(
            source_module="aatif_governor",
            target_module="runtime",
            channel=ChannelType.B8_EXECUTION,
            signal_types=frozenset({"GovernedPrompt", "CleanedOutput"}),
            description="Governed prompt / cleaned output → Runtime (LLM hook)",
        ),
        ChannelBinding(
            source_module="aatif_output_gate",
            target_module="aatif_governor",
            channel=ChannelType.B8_EXECUTION,
            signal_types=frozenset({"CleanedOutput"}),
            description="Gate-cleaned text → Governor for final assembly",
        ),
    )


# The canonical spec — global and immutable (consensus Q5 + Q6)
AATIF_CANONICAL_BINDINGS: Tuple[ChannelBinding, ...] = _build_canonical_bindings()


# ═══════════════════════════════════════════════════════════════
#  Helper — payload hashing
# ═══════════════════════════════════════════════════════════════

def _hash_payload(payload: Any) -> Optional[str]:
    """
    SHA256 hash of payload for trace integrity without storing content.
    Returns None if payload cannot be serialized.
    """
    try:
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    except (TypeError, ValueError):
        try:
            return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()[:16]
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════
#  BindingMap — the per-Governor instance
# ═══════════════════════════════════════════════════════════════

class BindingMap:
    """
    Per-Governor binding map instance (consensus Q5: per-Governor, not singleton).

    Constructed from the global immutable canonical spec plus an optional
    domain/profile overlay.  Provides:
      - validate()           → boot-time structural integrity check
      - validate_signal()    → check if a signal is allowed
      - record_signal()      → record a signal on the audit trail
      - get_audit_trail()    → retrieve the trail
      - get_channel_for()    → find which channel connects two modules
      - get_integrity_report() → boot-time report

    NEVER intercepts, blocks, or transforms signals.
    """

    def __init__(
        self,
        canonical_bindings: Sequence[ChannelBinding] = AATIF_CANONICAL_BINDINGS,
        loaded_modules: Optional[FrozenSet[str]] = None,
        governor_id: str = "default",
    ):
        self._canonical = tuple(canonical_bindings)
        self._loaded_modules = loaded_modules or frozenset()
        self._governor_id = governor_id
        self._audit_trail: List[ChannelAuditEntry] = []
        self._sequence_counter = 0

        # Index: (source, target, channel) → binding
        self._binding_index: Dict[Tuple[str, str, ChannelType], ChannelBinding] = {}
        # Index: source_module → list of bindings
        self._source_index: Dict[str, List[ChannelBinding]] = {}
        # Index: channel → list of bindings
        self._channel_index: Dict[ChannelType, List[ChannelBinding]] = {}

        self._build_indices()

    def _build_indices(self) -> None:
        """Build lookup indices from the canonical bindings."""
        for binding in self._canonical:
            key = (binding.source_module, binding.target_module, binding.channel)
            self._binding_index[key] = binding

            if binding.source_module not in self._source_index:
                self._source_index[binding.source_module] = []
            self._source_index[binding.source_module].append(binding)

            if binding.channel not in self._channel_index:
                self._channel_index[binding.channel] = []
            self._channel_index[binding.channel].append(binding)

    @classmethod
    def from_canonical(
        cls,
        loaded_modules: Optional[FrozenSet[str]] = None,
        governor_id: str = "default",
    ) -> "BindingMap":
        """Factory: construct from the global canonical spec."""
        return cls(
            canonical_bindings=AATIF_CANONICAL_BINDINGS,
            loaded_modules=loaded_modules,
            governor_id=governor_id,
        )

    # ───────────────────────────────────────────────────────────
    #  Boot-time validation (Q2: hard enforcement at boot)
    # ───────────────────────────────────────────────────────────

    def validate(self) -> BindingIntegrityReport:
        """
        Validate structural integrity of the binding map.

        Boot-time check (hard enforcement):
        1. Every ChannelType B1-B8 has at least one binding
        2. All signal types in bindings are allowed for their channel
        3. Required bindings have their source modules loaded (if loaded_modules provided)

        Returns BindingIntegrityReport.
        """
        violations: List[str] = []
        warnings: List[str] = []
        missing_channels: List[ChannelType] = []
        active_count = 0
        inactive_count = 0

        # Check 1: every channel has at least one binding
        for ch in ChannelType:
            if ch not in self._channel_index or not self._channel_index[ch]:
                missing_channels.append(ch)
                violations.append(f"Channel {ch.value} has no bindings")

        # Check 2: signal types match channel's allowed set
        for binding in self._canonical:
            allowed = CHANNEL_ALLOWED_SIGNALS.get(binding.channel, frozenset())
            invalid_types = binding.signal_types - allowed
            if invalid_types:
                violations.append(
                    f"Binding {binding.source_module}→{binding.target_module} "
                    f"on {binding.channel.value}: signal types {invalid_types} "
                    f"not allowed on this channel"
                )

        # Check 3: module availability (only if loaded_modules provided)
        if self._loaded_modules:
            for binding in self._canonical:
                source_loaded = binding.source_module in self._loaded_modules
                target_loaded = (
                    binding.target_module in self._loaded_modules
                    or binding.target_module == "runtime"
                )
                if source_loaded and target_loaded:
                    active_count += 1
                else:
                    inactive_count += 1
                    if binding.required and not source_loaded:
                        warnings.append(
                            f"Required binding source {binding.source_module} "
                            f"not in loaded modules"
                        )
        else:
            # No module list → all are conceptually active
            active_count = len(self._canonical)

        valid = len(violations) == 0 and len(missing_channels) == 0
        return BindingIntegrityReport(
            valid=valid,
            total_bindings=len(self._canonical),
            active_bindings=active_count,
            inactive_bindings=inactive_count,
            missing_channels=missing_channels,
            violations=violations,
            warnings=warnings,
        )

    # ───────────────────────────────────────────────────────────
    #  Channel lookup
    # ───────────────────────────────────────────────────────────

    def get_channel_for(
        self, source_module: str, target_module: str
    ) -> Optional[ChannelType]:
        """
        Find which channel connects source to target.

        Returns ChannelType if a binding exists, None otherwise.
        Does NOT raise — callers decide what to do with None.
        """
        for binding in self._canonical:
            if (binding.source_module == source_module
                    and binding.target_module == target_module):
                return binding.channel
        return None

    def get_bindings_for_channel(self, channel: ChannelType) -> List[ChannelBinding]:
        """Return all bindings registered on a channel."""
        return list(self._channel_index.get(channel, []))

    def get_bindings_for_source(self, source_module: str) -> List[ChannelBinding]:
        """Return all bindings from a source module."""
        return list(self._source_index.get(source_module, []))

    # ───────────────────────────────────────────────────────────
    #  Signal validation (Q2: soft at runtime)
    # ───────────────────────────────────────────────────────────

    def validate_signal(
        self,
        source_module: str,
        target_module: str,
        signal_type: str,
        channel: Optional[ChannelType] = None,
    ) -> Tuple[bool, str]:
        """
        Check if a signal is allowed by the binding map.

        Returns (is_valid, binding_status) where binding_status is one of:
          "allowed"       — matches a canonical binding
          "wrong_channel" — binding exists but on a different channel
          "wrong_type"    — binding exists but signal type not allowed
          "unknown"       — no binding found for this source→target pair

        NEVER raises. NEVER blocks. Pure observation.
        """
        # Find any binding for this source→target pair
        found_binding = None
        for binding in self._canonical:
            if (binding.source_module == source_module
                    and binding.target_module == target_module):
                found_binding = binding
                break

        if found_binding is None:
            return (False, "unknown")

        # Check channel match (if channel specified)
        if channel is not None and found_binding.channel != channel:
            return (False, "wrong_channel")

        # Check signal type
        if signal_type not in found_binding.signal_types:
            # Check if this signal type is allowed on any channel
            channel_allowed = CHANNEL_ALLOWED_SIGNALS.get(
                found_binding.channel, frozenset()
            )
            if signal_type not in channel_allowed:
                return (False, "wrong_type")

        return (True, "allowed")

    # ───────────────────────────────────────────────────────────
    #  Audit trail (runtime annotation)
    # ───────────────────────────────────────────────────────────

    def record_signal(
        self,
        channel: ChannelType,
        source_module: str,
        signal_type: str,
        target_module: Optional[str] = None,
        payload: Any = None,
        runtime_phase: str = "execution",
    ) -> ChannelAuditEntry:
        """
        Record a signal on the audit trail.

        NEVER blocks. NEVER intercepts. Pure observation.
        Returns the created ChannelAuditEntry.
        """
        self._sequence_counter += 1

        # Validate the signal (soft — for classification only)
        is_valid, binding_status = self.validate_signal(
            source_module=source_module,
            target_module=target_module or "",
            signal_type=signal_type,
            channel=channel,
        )

        # Determine severity
        if is_valid:
            severity = "info"
        elif binding_status == "unknown":
            severity = "warning"
        else:
            severity = "violation"

        # Hash payload if provided
        p_hash = _hash_payload(payload) if payload is not None else None
        p_size = None
        if payload is not None:
            try:
                p_size = len(json.dumps(payload, default=str).encode("utf-8"))
            except (TypeError, ValueError):
                try:
                    p_size = len(repr(payload).encode("utf-8"))
                except Exception:
                    pass

        t0 = time.perf_counter()
        entry = ChannelAuditEntry(
            sequence_number=self._sequence_counter,
            timestamp=time.time(),
            channel=channel,
            source_module=source_module,
            target_module=target_module,
            signal_type=signal_type,
            payload_hash=p_hash,
            payload_size_bytes=p_size,
            binding_status=binding_status,
            severity=severity,
            runtime_phase=runtime_phase,
            duration_ms=round((time.perf_counter() - t0) * 1000, 4),
        )

        self._audit_trail.append(entry)
        return entry

    def get_audit_trail(self) -> List[ChannelAuditEntry]:
        """Return the complete audit trail, ordered by sequence number."""
        return list(self._audit_trail)

    def get_violations(self) -> List[ChannelAuditEntry]:
        """Return only violation entries from the audit trail."""
        return [e for e in self._audit_trail if e.severity == "violation"]

    def clear_audit_trail(self) -> int:
        """Clear the audit trail. Returns number of entries cleared."""
        count = len(self._audit_trail)
        self._audit_trail.clear()
        self._sequence_counter = 0
        return count

    # ───────────────────────────────────────────────────────────
    #  Summary / diagnostics
    # ───────────────────────────────────────────────────────────

    def channel_summary(self) -> Dict[str, int]:
        """Count of bindings per channel."""
        return {
            ch.value: len(self._channel_index.get(ch, []))
            for ch in ChannelType
        }

    def __repr__(self) -> str:
        report = self.validate()
        return (
            f"BindingMap(governor={self._governor_id!r}, "
            f"bindings={report.total_bindings}, "
            f"active={report.active_bindings}, "
            f"valid={report.valid})"
        )


# ═══════════════════════════════════════════════════════════════
#  Boot integration helper
# ═══════════════════════════════════════════════════════════════

def validate_binding_map_at_boot(
    loaded_modules: Optional[FrozenSet[str]] = None,
    governor_id: str = "boot",
) -> Tuple[bool, BindingIntegrityReport, Optional[BindingMap]]:
    """
    Boot-time validation entry point.

    Called by the boot sequence (FN#045). Returns:
      (passed, report, binding_map_or_None)

    Consensus Q3: Optional for safety boot. If validation fails,
    Governor boots in degraded observability mode.
    """
    if not BINDING_MAP_ENABLED:
        return (True, BindingIntegrityReport(
            valid=True, total_bindings=0, active_bindings=0,
            inactive_bindings=0,
        ), None)

    try:
        bmap = BindingMap.from_canonical(
            loaded_modules=loaded_modules,
            governor_id=governor_id,
        )
        report = bmap.validate()
        return (report.valid, report, bmap)
    except Exception as exc:
        return (False, BindingIntegrityReport(
            valid=False, total_bindings=0, active_bindings=0,
            inactive_bindings=0, violations=[str(exc)],
        ), None)
