"""
aatif_behavioural_twin.py — Behavioural Twin Protocol (URRL + UDDS)
Field Note #023: The Behavioural Twin Protocol

"Same values. Same behaviour. Different memory."
"نفس القيم. نفس السلوك. ذاكرة مختلفة."

Cross-instance drift detection: multiple AATIF instances running across
different devices (phone + laptop, two browser tabs) must behave identically
— same constitutional baseline, same safety posture, same personality —
while maintaining **separate** conversation memories.

This module DETECTS drift between instances.  It does NOT enforce
synchronization, does NOT make safety decisions, and does NOT persist
memory.  It is a pure observer that emits B5 advisory readings.

Important distinction from FN#058 (DriftDetector):
    FN#058 detects within-conversation drift (user gradually steering
    toward harmful content → safety concern).
    FN#023 detects cross-instance drift (two sessions diverging in
    behavioural baseline → consistency concern).
    Completely different scope, different inputs, different outputs.

Pipeline position:  after S(d), before prompt composition.
Reads:   instance baselines (constitutional hash, tone, safety posture,
         priority ordering, personality markers).
Produces: TwinReading with drift magnitude and recalibration signals.

Architecture: B-prime (B')
─────────────────────────────────────────────────────────────────
BaselineRegistry       →  pure storage (get / register / evict)
BehaviouralTwinDetector →  observational (outputs TwinReading + evidence)
GovernanceEquation      →  judicial (computes H_eff, decides S)

Critical Design Rule (Single Mind):
  Only GovernanceEquation can transform inputs into final safety.
  BehaviouralTwinDetector is NOT judicial — it says "tone drift is 0.35
  between instance A and instance B." The equation decides what to do.

Design consensus: Claude × ChatGPT, 2026-07-01
Field Note: FN#023 (URRL + UDDS)

"التوأم السلوكي لا يحكم. يُراقب فقط."
"The behavioural twin does not judge. It only observes."

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
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple


# ═══════════════════════════════════════════════════════════════
#  Feature Flag
# ═══════════════════════════════════════════════════════════════

BEHAVIOURAL_TWIN_ENABLED = True


# ═══════════════════════════════════════════════════════════════
#  Constants — calibration values
# ═══════════════════════════════════════════════════════════════

# Drift thresholds
TWIN_THRESHOLD     = 0.15   # overall_drift < this → twins (in sync)
DRIFTING_THRESHOLD = 0.40   # overall_drift < this → drifting (needs attention)
                            # overall_drift >= this → diverged (broken)

# Sparse activation
ACTIVATION_THRESHOLD = 0.05  # minimum drift to produce an active reading

# Drift dimension weights — sum to 1.0
W_CONSTITUTIONAL = 0.40    # most important — binary, must match
W_SAFETY         = 0.25    # safety posture must be close
W_PRIORITY       = 0.15    # priority ordering
W_TONE           = 0.10    # tone profile
W_PERSONALITY    = 0.10    # personality markers

# Registry limits
MAX_INSTANCES = 100        # LRU eviction threshold per project
MAX_PROJECTS  = 50         # max projects tracked simultaneously

# Bilingual anchors — Arabic
AR_SLOGAN            = "نفس القيم. نفس السلوك. ذاكرة مختلفة."
AR_TWIN              = "التوأم السلوكي"
AR_CROSS_DRIFT       = "الانجراف عبر الأجهزة"
AR_RECALIBRATION     = "إعادة المعايرة"
AR_SOURCE_OF_TRUTH   = "مصدر الحقيقة"
AR_PROJECT_BOUNDARY  = "حدود المشروع"

# Bilingual anchors — English
EN_SLOGAN            = "Same values. Same behaviour. Different memory."
EN_TWIN              = "Behavioural Twin"
EN_CROSS_DRIFT       = "Cross-instance drift"
EN_RECALIBRATION     = "Re-calibration signal"
EN_SOURCE_OF_TRUTH   = "Source of truth"
EN_PROJECT_BOUNDARY  = "Project boundary"


# ═══════════════════════════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════════════════════════

class TwinStatus(Enum):
    """Classification of twin relationship."""
    IN_SYNC   = "in_sync"     # overall_drift < TWIN_THRESHOLD
    DRIFTING  = "drifting"    # TWIN_THRESHOLD <= overall_drift < DRIFTING_THRESHOLD
    DIVERGED  = "diverged"   # overall_drift >= DRIFTING_THRESHOLD


class DriftDimension(Enum):
    """Which dimension of behaviour drifted."""
    CONSTITUTIONAL = "constitutional"
    TONE           = "tone"
    SAFETY         = "safety"
    PRIORITY       = "priority"
    PERSONALITY    = "personality"


# ═══════════════════════════════════════════════════════════════
#  Exceptions
# ═══════════════════════════════════════════════════════════════

class ProjectBoundaryViolation(Exception):
    """Raised when attempting to compare baselines across projects."""
    pass


class DuplicateInstanceError(Exception):
    """Raised when registering an instance that already exists."""
    pass


# ═══════════════════════════════════════════════════════════════
#  Dataclasses
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BehaviouralBaseline:
    """Snapshot of an instance's behavioural identity.

    This is the fingerprint we compare across devices.
    What syncs: values, behaviour, priorities, safety posture, tone.
    What stays separate: personal memory, conversation history, device context.
    """
    project_id: str                       # Project boundary enforcement
    instance_id: str                      # Unique instance identifier
    constitutional_hash: str              # SHA-256 of core values + rules
    tone_profile: Tuple[str, ...]         # Ordered tone descriptors
    safety_posture: float                 # 0.0 (permissive) to 1.0 (strict)
    priority_ordering: Tuple[str, ...]    # Constitutional priority hierarchy
    personality_markers: Tuple[str, ...]  # Key personality traits
    is_architect_device: bool             # Source-of-truth flag
    timestamp: float                      # When this baseline was captured


@dataclass(frozen=True)
class TwinDrift:
    """Measured drift between two baselines — per-dimension breakdown."""
    constitutional_drift: float   # 0.0 = identical hash, 1.0 = different
    tone_drift: float             # Jaccard distance between tone sets
    safety_drift: float           # Absolute difference in safety_posture
    priority_drift: float         # Normalized Kendall tau distance
    personality_drift: float      # Jaccard distance between personality sets
    overall_drift: float          # Weighted composite


@dataclass(frozen=True)
class RecalibrationSignal:
    """Specific recalibration recommendation for a drifted dimension."""
    dimension: DriftDimension
    drift_value: float
    source_value: str             # What the source (truth) has
    target_value: str             # What the drifted instance has
    recommendation: str           # Human-readable recalibration advice


@dataclass(frozen=True)
class TwinReading:
    """Output of BehaviouralTwinDetector — observational, NOT judicial.

    This reading is ADVISORY ONLY. It tells the governor how much two
    instances have drifted. It does NOT decide what to do about it.
    The GovernanceEquation (S) remains sole safety authority.
    """
    drift: TwinDrift
    source_baseline: BehaviouralBaseline   # The reference (architect or first)
    target_baseline: BehaviouralBaseline   # The instance being compared
    status: TwinStatus                     # in_sync / drifting / diverged
    recalibration_needed: bool
    recalibration_signals: Tuple[RecalibrationSignal, ...]
    evidence: Tuple[str, ...]              # Human-readable evidence trail
    activated: bool                        # False = sparse-activation skip
    _isolation_marker: str = "B5_BEHAVIOURAL_ADVISORY_NOT_SAFETY"


# ═══════════════════════════════════════════════════════════════
#  Drift Computation — pure functions
# ═══════════════════════════════════════════════════════════════

def compute_constitutional_drift(hash_a: str, hash_b: str) -> float:
    """Binary drift: 0.0 if hashes match, 1.0 if different.

    Constitutional values are non-negotiable — either they're identical
    or they've diverged completely.  No partial matching.

    Security hardening (Gemini P0): rejects hashes shorter than 32
    characters to prevent trivially-matched short strings from
    masquerading as valid constitutional identity.
    """
    if not hash_a or not hash_b:
        return 1.0
    # P0 fix: reject suspiciously short hashes (valid SHA-256 = 64 hex chars)
    if len(hash_a) < 32 or len(hash_b) < 32:
        return 1.0
    return 0.0 if hash_a == hash_b else 1.0


def compute_jaccard_distance(set_a: Sequence[str], set_b: Sequence[str]) -> float:
    """Jaccard distance between two sets: 1 - |A∩B|/|A∪B|.

    Returns 0.0 for identical sets, 1.0 for completely disjoint sets.
    Returns 0.0 if both sets are empty (no information → no drift).
    """
    a = set(set_a)
    b = set(set_b)
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    intersection = a & b
    return round(1.0 - len(intersection) / len(union), 6)


def compute_safety_drift(posture_a: float, posture_b: float) -> float:
    """Absolute difference in safety posture values.

    Both values should be in [0.0, 1.0].
    Result is clamped to [0.0, 1.0].
    """
    return round(min(1.0, abs(posture_a - posture_b)), 6)


def compute_kendall_tau_distance(
    ordering_a: Sequence[str],
    ordering_b: Sequence[str],
) -> float:
    """Normalized Kendall tau distance between two orderings.

    Counts the number of pairwise disagreements (inversions) between
    two rankings, normalized to [0.0, 1.0].

    Only compares items present in BOTH orderings.
    If fewer than 2 shared items: returns 1.0 if the sets differ
    (total divergence), 0.0 if both are identical or both empty.

    Fix applied from Gemini P0 review: previously returned 0.0 for
    disjoint orderings, falsely reporting perfect sync.
    """
    # Find shared items preserving order
    shared = [x for x in ordering_a if x in set(ordering_b)]
    if len(shared) < 2:
        # P0 fix: disjoint orderings = total divergence, not sync
        if set(ordering_a) != set(ordering_b):
            return 1.0
        return 0.0

    # Get positions in ordering_b for shared items
    b_positions = {item: i for i, item in enumerate(ordering_b)}
    b_order = [b_positions[item] for item in shared]

    # Count inversions (pairwise disagreements)
    inversions = 0
    n = len(b_order)
    for i in range(n):
        for j in range(i + 1, n):
            if b_order[i] > b_order[j]:
                inversions += 1

    # Normalize: max inversions = n*(n-1)/2
    max_inversions = n * (n - 1) / 2
    if max_inversions == 0:
        return 0.0

    return round(inversions / max_inversions, 6)


def compute_overall_drift(drift: TwinDrift) -> float:
    """Weighted composite of all drift dimensions.

    Weights sum to 1.0:
        constitutional=0.40, safety=0.25, priority=0.15,
        tone=0.10, personality=0.10
    """
    result = (
        W_CONSTITUTIONAL * drift.constitutional_drift
        + W_SAFETY * drift.safety_drift
        + W_PRIORITY * drift.priority_drift
        + W_TONE * drift.tone_drift
        + W_PERSONALITY * drift.personality_drift
    )
    return round(min(1.0, max(0.0, result)), 6)


def compute_twin_drift(
    source: BehaviouralBaseline,
    target: BehaviouralBaseline,
) -> TwinDrift:
    """Compute full drift profile between two baselines."""
    const_drift = compute_constitutional_drift(
        source.constitutional_hash, target.constitutional_hash
    )
    tone_drift = compute_jaccard_distance(
        source.tone_profile, target.tone_profile
    )
    safety_drift = compute_safety_drift(
        source.safety_posture, target.safety_posture
    )
    priority_drift = compute_kendall_tau_distance(
        source.priority_ordering, target.priority_ordering
    )
    personality_drift = compute_jaccard_distance(
        source.personality_markers, target.personality_markers
    )

    # Create without overall first, then compute
    partial = TwinDrift(
        constitutional_drift=const_drift,
        tone_drift=tone_drift,
        safety_drift=safety_drift,
        priority_drift=priority_drift,
        personality_drift=personality_drift,
        overall_drift=0.0,  # placeholder
    )
    overall = compute_overall_drift(partial)

    return TwinDrift(
        constitutional_drift=const_drift,
        tone_drift=tone_drift,
        safety_drift=safety_drift,
        priority_drift=priority_drift,
        personality_drift=personality_drift,
        overall_drift=overall,
    )


def classify_twin_status(overall_drift: float) -> TwinStatus:
    """Classify the relationship based on drift magnitude."""
    if overall_drift < TWIN_THRESHOLD:
        return TwinStatus.IN_SYNC
    elif overall_drift < DRIFTING_THRESHOLD:
        return TwinStatus.DRIFTING
    else:
        return TwinStatus.DIVERGED


# ═══════════════════════════════════════════════════════════════
#  Recalibration Signal Generation
# ═══════════════════════════════════════════════════════════════

def generate_recalibration_signals(
    source: BehaviouralBaseline,
    target: BehaviouralBaseline,
    drift: TwinDrift,
) -> Tuple[RecalibrationSignal, ...]:
    """Generate specific recalibration recommendations for drifted dimensions.

    Only emits signals for dimensions that exceed their individual thresholds.
    """
    signals: List[RecalibrationSignal] = []

    if drift.constitutional_drift > 0.0:
        signals.append(RecalibrationSignal(
            dimension=DriftDimension.CONSTITUTIONAL,
            drift_value=drift.constitutional_drift,
            source_value=f"hash={source.constitutional_hash[:16]}...",
            target_value=f"hash={target.constitutional_hash[:16]}...",
            recommendation=(
                "Constitutional hash mismatch — core values or rules differ. "
                "Target instance must reload constitutional baseline from source of truth."
            ),
        ))

    if drift.tone_drift > 0.10:
        signals.append(RecalibrationSignal(
            dimension=DriftDimension.TONE,
            drift_value=drift.tone_drift,
            source_value=str(source.tone_profile),
            target_value=str(target.tone_profile),
            recommendation=(
                f"Tone drift {drift.tone_drift:.2f} — "
                f"source uses {source.tone_profile}, target uses {target.tone_profile}. "
                "Align tone profile to source of truth."
            ),
        ))

    if drift.safety_drift > 0.05:
        signals.append(RecalibrationSignal(
            dimension=DriftDimension.SAFETY,
            drift_value=drift.safety_drift,
            source_value=f"{source.safety_posture:.2f}",
            target_value=f"{target.safety_posture:.2f}",
            recommendation=(
                f"Safety posture drift {drift.safety_drift:.2f} — "
                f"source={source.safety_posture:.2f}, target={target.safety_posture:.2f}. "
                "Re-align safety posture to source of truth."
            ),
        ))

    if drift.priority_drift > 0.10:
        signals.append(RecalibrationSignal(
            dimension=DriftDimension.PRIORITY,
            drift_value=drift.priority_drift,
            source_value=str(source.priority_ordering),
            target_value=str(target.priority_ordering),
            recommendation=(
                f"Priority ordering drift {drift.priority_drift:.2f} — "
                "re-align constitutional priority hierarchy to source of truth."
            ),
        ))

    if drift.personality_drift > 0.10:
        signals.append(RecalibrationSignal(
            dimension=DriftDimension.PERSONALITY,
            drift_value=drift.personality_drift,
            source_value=str(source.personality_markers),
            target_value=str(target.personality_markers),
            recommendation=(
                f"Personality drift {drift.personality_drift:.2f} — "
                "re-align personality markers to source of truth."
            ),
        ))

    return tuple(signals)


# ═══════════════════════════════════════════════════════════════
#  Evidence Compilation
# ═══════════════════════════════════════════════════════════════

def compile_evidence(
    source: BehaviouralBaseline,
    target: BehaviouralBaseline,
    drift: TwinDrift,
    status: TwinStatus,
) -> Tuple[str, ...]:
    """Compile human-readable evidence trail for the drift reading."""
    evidence: List[str] = []

    evidence.append(
        f"Comparing instance '{target.instance_id}' against "
        f"source '{source.instance_id}' in project '{source.project_id}'"
    )

    if source.is_architect_device:
        evidence.append(
            f"Source is Architect's device (مصدر الحقيقة)"
        )

    evidence.append(f"Overall drift: {drift.overall_drift:.4f}")
    evidence.append(f"Status: {status.value}")

    if drift.constitutional_drift > 0.0:
        evidence.append("CRITICAL: Constitutional hash MISMATCH")
    else:
        evidence.append("Constitutional hash: MATCH")

    evidence.append(f"Tone drift: {drift.tone_drift:.4f}")
    evidence.append(f"Safety drift: {drift.safety_drift:.4f}")
    evidence.append(f"Priority drift: {drift.priority_drift:.4f}")
    evidence.append(f"Personality drift: {drift.personality_drift:.4f}")

    return tuple(evidence)


# ═══════════════════════════════════════════════════════════════
#  Constitutional Hash Helper
# ═══════════════════════════════════════════════════════════════

def compute_constitutional_hash(
    values: Sequence[str],
    rules: Sequence[str],
    *,
    safety_thresholds: Sequence[str] = (),
) -> str:
    """Compute SHA-256 hash of constitutional identity.

    Sorts all inputs to ensure order-independence.
    """
    combined = sorted(values) + sorted(rules) + sorted(safety_thresholds)
    raw = "|".join(combined)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════
#  BaselineRegistry — pure storage, no logic
# ═══════════════════════════════════════════════════════════════

class BaselineRegistry:
    """
    Pure storage for BehaviouralBaselines, keyed by (project_id, instance_id).
    Follows ConversationManager pattern from FN#058 drift_detector.
    Owns NO decision logic — storage only.

    Project-scoped: get_baselines(project_id) returns only that project's instances.
    """

    def __init__(
        self,
        max_instances_per_project: int = MAX_INSTANCES,
        max_projects: int = MAX_PROJECTS,
    ):
        self._baselines: Dict[str, Dict[str, BehaviouralBaseline]] = {}
        self._project_access_order: List[str] = []
        self._max_instances = max_instances_per_project
        self._max_projects = max_projects

    def register(self, baseline: BehaviouralBaseline) -> None:
        """Register or update an instance baseline."""
        pid = baseline.project_id
        iid = baseline.instance_id

        if pid not in self._baselines:
            self._evict_projects_if_needed()
            self._baselines[pid] = {}

        # LRU for projects
        if pid in self._project_access_order:
            self._project_access_order.remove(pid)
        self._project_access_order.append(pid)

        project_baselines = self._baselines[pid]

        # LRU eviction for instances within project
        if iid not in project_baselines and len(project_baselines) >= self._max_instances:
            self._evict_oldest_instance(pid)

        project_baselines[iid] = baseline

    def get(self, project_id: str, instance_id: str) -> Optional[BehaviouralBaseline]:
        """Retrieve a specific instance baseline."""
        project = self._baselines.get(project_id)
        if project is None:
            return None
        return project.get(instance_id)

    def get_baselines(self, project_id: str) -> List[BehaviouralBaseline]:
        """Get all baselines for a project."""
        project = self._baselines.get(project_id)
        if project is None:
            return []
        return list(project.values())

    def get_source_of_truth(self, project_id: str) -> Optional[BehaviouralBaseline]:
        """Get the Architect's device baseline (source of truth) for a project.

        If multiple Architect devices exist, returns the most recent.
        If none, returns the most recently registered baseline.
        """
        baselines = self.get_baselines(project_id)
        if not baselines:
            return None

        architect_baselines = [b for b in baselines if b.is_architect_device]
        if architect_baselines:
            return max(architect_baselines, key=lambda b: b.timestamp)

        return max(baselines, key=lambda b: b.timestamp)

    def remove(self, project_id: str, instance_id: str) -> bool:
        """Remove an instance baseline. Returns True if it existed."""
        project = self._baselines.get(project_id)
        if project is None:
            return False
        removed = project.pop(instance_id, None)
        if not project:
            self._baselines.pop(project_id, None)
            if project_id in self._project_access_order:
                self._project_access_order.remove(project_id)
        return removed is not None

    def remove_project(self, project_id: str) -> int:
        """Remove all baselines for a project. Returns count removed."""
        project = self._baselines.pop(project_id, None)
        if project_id in self._project_access_order:
            self._project_access_order.remove(project_id)
        return len(project) if project else 0

    @property
    def instance_count(self) -> int:
        """Total instances across all projects."""
        return sum(len(p) for p in self._baselines.values())

    @property
    def project_count(self) -> int:
        """Number of tracked projects."""
        return len(self._baselines)

    def _evict_projects_if_needed(self) -> None:
        """LRU eviction when at project capacity."""
        while len(self._baselines) >= self._max_projects and self._project_access_order:
            oldest = self._project_access_order.pop(0)
            self._baselines.pop(oldest, None)

    def _evict_oldest_instance(self, project_id: str) -> None:
        """Remove oldest instance from a project (by timestamp)."""
        project = self._baselines.get(project_id)
        if not project:
            return
        oldest = min(project.values(), key=lambda b: b.timestamp)
        project.pop(oldest.instance_id, None)


# ═══════════════════════════════════════════════════════════════
#  BehaviouralTwinDetector — observational, NOT judicial
# ═══════════════════════════════════════════════════════════════

class BehaviouralTwinDetector:
    """
    Cross-instance drift detection — FN#023 B-prime architecture.

    This class is NOT judicial. It computes drift between two behavioural
    baselines and provides evidence. The GovernanceEquation decides what
    to do with it.

    "التوأم السلوكي لا يحكم. يُراقب فقط."
    "The behavioural twin does not judge. It only observes."
    """

    # ── Authority Contract (B-prime) ──────────────────────────
    AUTHORITY_LEVEL            = "B_PRIME_OBSERVATIONAL"
    CAN_BLOCK_RUNTIME          = False
    CAN_MODIFY_H               = False
    CAN_MODIFY_THETA           = False
    CAN_MODIFY_S               = False
    CAN_EMIT_JUDICIAL_DECISION = False
    BINDING_CHANNEL            = "B5"       # Behaviour
    SAFETY_DECISION_AUTHORITY  = "GOVERNANCE_EQUATION_ONLY"

    # ── Feature Flag ──────────────────────────────────────────
    ENABLED = BEHAVIOURAL_TWIN_ENABLED

    # ── Isolation Contract ────────────────────────────────────
    ISOLATION_CONTRACT = """
    BehaviouralTwinDetector produces ADVISORY drift observations only.
    It NEVER modifies H, θ, or S.  It NEVER blocks runtime.
    Its output feeds B5 (Behaviour) channel exclusively.
    The S equation is the sole safety authority (Single-Mind Law).
    This module DETECTS drift — it does NOT enforce synchronization.
    """
    ISOLATION_MARKER  = "B5_BEHAVIOURAL_ADVISORY_NOT_SAFETY"
    ISOLATION_TARGETS = frozenset({"B5"})

    def __init__(
        self,
        registry: Optional[BaselineRegistry] = None,
    ):
        self._registry = registry or BaselineRegistry()

    # ── Public API — observe/detect naming ────────────────────

    @property
    def registry(self) -> BaselineRegistry:
        """Access the baseline registry (read-only intent)."""
        return self._registry

    def register_instance(self, baseline: BehaviouralBaseline) -> None:
        """Register a new instance baseline."""
        self._registry.register(baseline)

    def observe(
        self,
        source: BehaviouralBaseline,
        target: BehaviouralBaseline,
    ) -> TwinReading:
        """
        Compare two baselines and produce an observational TwinReading.

        Enforces project boundary: source and target must be in the same project.
        Returns activated=False if drift is below ACTIVATION_THRESHOLD (sparse skip).

        Raises:
            ProjectBoundaryViolation: if source and target are in different projects.
        """
        if not self.ENABLED:
            return self._inactive_reading(source, target)

        # Project boundary enforcement — hard rule
        if source.project_id != target.project_id:
            raise ProjectBoundaryViolation(
                f"Cannot compare across projects: "
                f"'{source.project_id}' vs '{target.project_id}' "
                f"(حدود المشروع — twins never cross project boundaries)"
            )

        # Compute drift
        drift = compute_twin_drift(source, target)

        # Sparse activation: if drift is negligible, skip
        if drift.overall_drift < ACTIVATION_THRESHOLD:
            return self._inactive_reading(source, target)

        # Classify status
        status = classify_twin_status(drift.overall_drift)

        # Generate recalibration signals
        recal_signals = generate_recalibration_signals(source, target, drift)

        # Compile evidence
        evidence = compile_evidence(source, target, drift, status)

        return TwinReading(
            drift=drift,
            source_baseline=source,
            target_baseline=target,
            status=status,
            recalibration_needed=status != TwinStatus.IN_SYNC,
            recalibration_signals=recal_signals,
            evidence=evidence,
            activated=True,
            _isolation_marker=self.ISOLATION_MARKER,
        )

    def detect_all(self, project_id: str) -> List[TwinReading]:
        """
        Compare all instances in a project against the source of truth.

        Returns a list of TwinReadings — one per non-source instance.
        """
        source = self._registry.get_source_of_truth(project_id)
        if source is None:
            return []

        baselines = self._registry.get_baselines(project_id)
        readings = []
        for target in baselines:
            if target.instance_id == source.instance_id:
                continue
            readings.append(self.observe(source, target))
        return readings

    def create_baseline(
        self,
        *,
        project_id: str,
        instance_id: str,
        values: Sequence[str],
        rules: Sequence[str],
        safety_thresholds: Sequence[str] = (),
        tone_profile: Sequence[str] = (),
        safety_posture: float = 0.7,
        priority_ordering: Sequence[str] = (),
        personality_markers: Sequence[str] = (),
        is_architect_device: bool = False,
    ) -> BehaviouralBaseline:
        """
        Factory method: create a baseline from raw constitutional data.

        Computes constitutional_hash from values + rules + safety_thresholds.
        """
        const_hash = compute_constitutional_hash(
            values, rules, safety_thresholds=safety_thresholds
        )
        return BehaviouralBaseline(
            project_id=project_id,
            instance_id=instance_id,
            constitutional_hash=const_hash,
            tone_profile=tuple(tone_profile),
            safety_posture=max(0.0, min(1.0, safety_posture)),
            priority_ordering=tuple(priority_ordering),
            personality_markers=tuple(personality_markers),
            is_architect_device=is_architect_device,
            timestamp=time.time(),
        )

    # ── Private helpers ───────────────────────────────────────

    def _inactive_reading(
        self,
        source: BehaviouralBaseline,
        target: BehaviouralBaseline,
    ) -> TwinReading:
        """Fast-path skip — drift below activation threshold or feature disabled."""
        zero_drift = TwinDrift(
            constitutional_drift=0.0,
            tone_drift=0.0,
            safety_drift=0.0,
            priority_drift=0.0,
            personality_drift=0.0,
            overall_drift=0.0,
        )
        return TwinReading(
            drift=zero_drift,
            source_baseline=source,
            target_baseline=target,
            status=TwinStatus.IN_SYNC,
            recalibration_needed=False,
            recalibration_signals=(),
            evidence=("Not activated — drift below threshold or feature disabled.",),
            activated=False,
            _isolation_marker=self.ISOLATION_MARKER,
        )

    # ── Audit Hash ────────────────────────────────────────────

    @staticmethod
    def audit_hash(reading: TwinReading) -> str:
        """
        Deterministic hash of a TwinReading for audit trail.
        Uses source/target instance IDs + drift values + status.
        """
        data = (
            f"{reading.source_baseline.instance_id}|"
            f"{reading.target_baseline.instance_id}|"
            f"{reading.drift.overall_drift:.6f}|"
            f"{reading.status.value}|"
            f"{reading.activated}"
        )
        return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════
#  Bridge Function — compute_twin_drift_for_h_eff
# ═══════════════════════════════════════════════════════════════
#
#  NOTE: This function DOES NOT feed the S equation directly.
#  It provides an optional advisory signal that the Governor may
#  choose to include in context.  The GovernanceEquation remains
#  the sole authority for safety decisions.
#

def compute_twin_drift_signal(
    reading: TwinReading,
    *,
    drift_lambda: float = 0.1,
) -> float:
    """
    Convert a TwinReading into a scalar advisory signal [0.0, 1.0].

    This is NOT a safety decision.  It is an informational signal that
    tells the system "cross-instance consistency pressure is X."

    drift_lambda scales the signal:
        signal = min(1.0, drift_lambda * overall_drift)
    """
    if not reading.activated:
        return 0.0
    return round(min(1.0, drift_lambda * reading.drift.overall_drift), 6)
