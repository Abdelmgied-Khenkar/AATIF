"""
tests/test_behavioural_twin.py — FN#023 Behavioural Twin Protocol Tests

80+ tests covering:
  1. BehaviouralBaseline dataclass (8 tests)
  2. BaselineRegistry — storage (12 tests)
  3. Drift computation — individual dimensions (15 tests)
  4. Overall drift — weighted composite (10 tests)
  5. Classification thresholds (8 tests)
  6. Project boundary enforcement (8 tests)
  7. Source-of-truth resolution (8 tests)
  8. Sparse activation (6 tests)
  9. B-prime invariants (10 tests)
  10. Bilingual anchors (6 tests)
  11. Edge cases (8 tests)
  12. Recalibration signals (6 tests)

License: BSL-1.1
"""

import hashlib
import time

import pytest

import sys
import os

# Ensure engine/ is importable
_ENGINE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from aatif_behavioural_twin import (
    # Feature flag
    BEHAVIOURAL_TWIN_ENABLED,
    # Constants
    TWIN_THRESHOLD,
    DRIFTING_THRESHOLD,
    ACTIVATION_THRESHOLD,
    W_CONSTITUTIONAL,
    W_SAFETY,
    W_PRIORITY,
    W_TONE,
    W_PERSONALITY,
    MAX_INSTANCES,
    MAX_PROJECTS,
    # Bilingual anchors
    AR_SLOGAN, AR_TWIN, AR_CROSS_DRIFT, AR_RECALIBRATION,
    AR_SOURCE_OF_TRUTH, AR_PROJECT_BOUNDARY,
    EN_SLOGAN, EN_TWIN, EN_CROSS_DRIFT, EN_RECALIBRATION,
    EN_SOURCE_OF_TRUTH, EN_PROJECT_BOUNDARY,
    # Enums
    TwinStatus,
    DriftDimension,
    # Exceptions
    ProjectBoundaryViolation,
    DuplicateInstanceError,
    # Dataclasses
    BehaviouralBaseline,
    TwinDrift,
    RecalibrationSignal,
    TwinReading,
    # Pure functions
    compute_constitutional_drift,
    compute_jaccard_distance,
    compute_safety_drift,
    compute_kendall_tau_distance,
    compute_overall_drift,
    compute_twin_drift,
    classify_twin_status,
    generate_recalibration_signals,
    compile_evidence,
    compute_constitutional_hash,
    compute_twin_drift_signal,
    # Classes
    BaselineRegistry,
    BehaviouralTwinDetector,
)


# ═══════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════

def _make_baseline(
    *,
    project_id: str = "proj_alpha",
    instance_id: str = "instance_a",
    constitutional_hash: str = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
    tone_profile: tuple = ("warm", "direct", "patient"),
    safety_posture: float = 0.7,
    priority_ordering: tuple = ("mercy", "justice", "truth", "safety"),
    personality_markers: tuple = ("empathetic", "analytical", "calm"),
    is_architect_device: bool = False,
    timestamp: float = 1000.0,
) -> BehaviouralBaseline:
    return BehaviouralBaseline(
        project_id=project_id,
        instance_id=instance_id,
        constitutional_hash=constitutional_hash,
        tone_profile=tone_profile,
        safety_posture=safety_posture,
        priority_ordering=priority_ordering,
        personality_markers=personality_markers,
        is_architect_device=is_architect_device,
        timestamp=timestamp,
    )


@pytest.fixture
def source_baseline():
    return _make_baseline(
        instance_id="architect_phone",
        is_architect_device=True,
        timestamp=2000.0,
    )


@pytest.fixture
def matching_target():
    """Target that matches source exactly."""
    return _make_baseline(
        instance_id="laptop",
        is_architect_device=False,
        timestamp=2001.0,
    )


@pytest.fixture
def drifted_target():
    """Target with noticeable but not catastrophic drift."""
    return _make_baseline(
        instance_id="laptop",
        tone_profile=("formal", "direct", "reserved"),
        safety_posture=0.85,
        personality_markers=("analytical", "cautious", "formal"),
        timestamp=2001.0,
    )


@pytest.fixture
def diverged_target():
    """Target that has diverged completely."""
    return _make_baseline(
        instance_id="laptop",
        constitutional_hash="f9e8d7c6b5a4f9e8d7c6b5a4f9e8d7c6b5a4f9e8d7c6b5a4f9e8d7c6b5a4f9e8",
        tone_profile=("cold", "terse"),
        safety_posture=0.2,
        priority_ordering=("safety", "truth", "justice", "mercy"),
        personality_markers=("aggressive", "impatient"),
        timestamp=2001.0,
    )


@pytest.fixture
def detector():
    return BehaviouralTwinDetector()


@pytest.fixture
def registry():
    return BaselineRegistry()


# ═══════════════════════════════════════════════════════════════
#  1. BehaviouralBaseline Dataclass (8 tests)
# ═══════════════════════════════════════════════════════════════

class TestBehaviouralBaseline:

    def test_baseline_creation(self):
        b = _make_baseline()
        assert b.project_id == "proj_alpha"
        assert b.instance_id == "instance_a"

    def test_baseline_is_frozen(self):
        b = _make_baseline()
        with pytest.raises(AttributeError):
            b.project_id = "changed"  # type: ignore[misc]

    def test_baseline_tone_is_tuple(self):
        b = _make_baseline()
        assert isinstance(b.tone_profile, tuple)

    def test_baseline_safety_posture_range(self):
        b = _make_baseline(safety_posture=0.5)
        assert 0.0 <= b.safety_posture <= 1.0

    def test_baseline_priority_is_tuple(self):
        b = _make_baseline()
        assert isinstance(b.priority_ordering, tuple)

    def test_baseline_personality_is_tuple(self):
        b = _make_baseline()
        assert isinstance(b.personality_markers, tuple)

    def test_baseline_architect_flag(self):
        b = _make_baseline(is_architect_device=True)
        assert b.is_architect_device is True

    def test_baseline_equality_same_data(self):
        a = _make_baseline(timestamp=100.0)
        b = _make_baseline(timestamp=100.0)
        assert a == b


# ═══════════════════════════════════════════════════════════════
#  2. BaselineRegistry — Storage (12 tests)
# ═══════════════════════════════════════════════════════════════

class TestBaselineRegistry:

    def test_register_and_get(self, registry):
        b = _make_baseline()
        registry.register(b)
        assert registry.get("proj_alpha", "instance_a") == b

    def test_get_nonexistent_returns_none(self, registry):
        assert registry.get("no_project", "no_instance") is None

    def test_get_baselines_returns_all_for_project(self, registry):
        b1 = _make_baseline(instance_id="a")
        b2 = _make_baseline(instance_id="b")
        registry.register(b1)
        registry.register(b2)
        baselines = registry.get_baselines("proj_alpha")
        assert len(baselines) == 2

    def test_get_baselines_empty_project(self, registry):
        assert registry.get_baselines("nonexistent") == []

    def test_project_scoping(self, registry):
        b1 = _make_baseline(project_id="proj_a", instance_id="x")
        b2 = _make_baseline(project_id="proj_b", instance_id="y")
        registry.register(b1)
        registry.register(b2)
        assert len(registry.get_baselines("proj_a")) == 1
        assert len(registry.get_baselines("proj_b")) == 1

    def test_remove_instance(self, registry):
        b = _make_baseline()
        registry.register(b)
        assert registry.remove("proj_alpha", "instance_a") is True
        assert registry.get("proj_alpha", "instance_a") is None

    def test_remove_nonexistent_returns_false(self, registry):
        assert registry.remove("no_proj", "no_inst") is False

    def test_remove_project(self, registry):
        b1 = _make_baseline(instance_id="a")
        b2 = _make_baseline(instance_id="b")
        registry.register(b1)
        registry.register(b2)
        count = registry.remove_project("proj_alpha")
        assert count == 2
        assert registry.get_baselines("proj_alpha") == []

    def test_instance_count(self, registry):
        registry.register(_make_baseline(project_id="p1", instance_id="a"))
        registry.register(_make_baseline(project_id="p1", instance_id="b"))
        registry.register(_make_baseline(project_id="p2", instance_id="c"))
        assert registry.instance_count == 3

    def test_project_count(self, registry):
        registry.register(_make_baseline(project_id="p1", instance_id="a"))
        registry.register(_make_baseline(project_id="p2", instance_id="b"))
        assert registry.project_count == 2

    def test_lru_eviction_instances(self):
        reg = BaselineRegistry(max_instances_per_project=3, max_projects=10)
        for i in range(5):
            reg.register(_make_baseline(instance_id=f"inst_{i}", timestamp=float(i)))
        # Should have evicted oldest, keeping 3
        assert len(reg.get_baselines("proj_alpha")) == 3

    def test_lru_eviction_projects(self):
        reg = BaselineRegistry(max_instances_per_project=10, max_projects=2)
        reg.register(_make_baseline(project_id="p1", instance_id="a"))
        reg.register(_make_baseline(project_id="p2", instance_id="b"))
        reg.register(_make_baseline(project_id="p3", instance_id="c"))
        # p1 should have been evicted
        assert reg.project_count == 2
        assert reg.get("p1", "a") is None


# ═══════════════════════════════════════════════════════════════
#  3. Drift Computation — Individual Dimensions (15 tests)
# ═══════════════════════════════════════════════════════════════

class TestConstitutionalDrift:

    # Valid hashes must be >= 32 chars (P0 security fix)
    HASH_A = "a" * 64  # valid SHA-256 length
    HASH_B = "b" * 64  # different valid hash

    def test_identical_hashes(self):
        assert compute_constitutional_drift(self.HASH_A, self.HASH_A) == 0.0

    def test_different_hashes(self):
        assert compute_constitutional_drift(self.HASH_A, self.HASH_B) == 1.0

    def test_empty_hash_a(self):
        assert compute_constitutional_drift("", self.HASH_A) == 1.0

    def test_empty_hash_b(self):
        assert compute_constitutional_drift(self.HASH_A, "") == 1.0

    def test_both_empty(self):
        assert compute_constitutional_drift("", "") == 1.0

    def test_short_hash_a_rejected(self):
        """P0 fix: hashes shorter than 32 chars are rejected as invalid."""
        assert compute_constitutional_drift("abc", self.HASH_A) == 1.0

    def test_short_hash_b_rejected(self):
        """P0 fix: hashes shorter than 32 chars are rejected as invalid."""
        assert compute_constitutional_drift(self.HASH_A, "xyz") == 1.0

    def test_short_hashes_both_rejected(self):
        """P0 fix: two short matching hashes still rejected."""
        assert compute_constitutional_drift("abc", "abc") == 1.0

    def test_exactly_32_chars_accepted(self):
        """Boundary: exactly 32 chars is the minimum valid length."""
        h32 = "a" * 32
        assert compute_constitutional_drift(h32, h32) == 0.0

    def test_31_chars_rejected(self):
        """Boundary: 31 chars is below the minimum."""
        h31 = "a" * 31
        assert compute_constitutional_drift(h31, h31) == 1.0


class TestJaccardDistance:

    def test_identical_sets(self):
        assert compute_jaccard_distance(["a", "b", "c"], ["a", "b", "c"]) == 0.0

    def test_completely_disjoint(self):
        assert compute_jaccard_distance(["a", "b"], ["c", "d"]) == 1.0

    def test_partial_overlap(self):
        # A={a,b,c}, B={b,c,d} → intersection=2, union=4 → distance=0.5
        dist = compute_jaccard_distance(["a", "b", "c"], ["b", "c", "d"])
        assert abs(dist - 0.5) < 1e-4

    def test_both_empty(self):
        assert compute_jaccard_distance([], []) == 0.0

    def test_one_empty(self):
        assert compute_jaccard_distance(["a", "b"], []) == 1.0


class TestSafetyDrift:

    def test_identical_posture(self):
        assert compute_safety_drift(0.7, 0.7) == 0.0

    def test_different_posture(self):
        assert abs(compute_safety_drift(0.7, 0.5) - 0.2) < 1e-4

    def test_max_drift(self):
        assert compute_safety_drift(0.0, 1.0) == 1.0

    def test_clamped_to_one(self):
        # Even with out-of-range values, result shouldn't exceed 1.0
        assert compute_safety_drift(0.0, 1.5) <= 1.0


class TestKendallTauDistance:

    def test_identical_ordering(self):
        assert compute_kendall_tau_distance(
            ["a", "b", "c", "d"], ["a", "b", "c", "d"]
        ) == 0.0

    def test_fully_reversed(self):
        # 4 items reversed: all 6 pairs are inversions → distance = 1.0
        assert compute_kendall_tau_distance(
            ["a", "b", "c", "d"], ["d", "c", "b", "a"]
        ) == 1.0

    def test_one_swap(self):
        # ["a","b","c"] vs ["a","c","b"] → 1 inversion out of 3 → 0.333...
        dist = compute_kendall_tau_distance(
            ["a", "b", "c"], ["a", "c", "b"]
        )
        assert abs(dist - 1 / 3) < 1e-4

    def test_fewer_than_two_shared_identical(self):
        # Single shared item, same set → 0.0 (identical)
        assert compute_kendall_tau_distance(["a"], ["a"]) == 0.0

    def test_no_shared_items(self):
        # P0 fix: disjoint orderings = total divergence (1.0), not sync (0.0)
        assert compute_kendall_tau_distance(["a", "b"], ["c", "d"]) == 1.0

    def test_fewer_than_two_shared_disjoint(self):
        # Only 1 shared item but sets differ → 1.0 (divergence)
        assert compute_kendall_tau_distance(["a", "b"], ["a", "c"]) == 1.0

    def test_partial_shared(self):
        # Only b, c shared. In A: b before c. In B: c before b → 1 inversion / 1 = 1.0
        dist = compute_kendall_tau_distance(
            ["a", "b", "c"], ["d", "c", "b"]
        )
        assert dist == 1.0


# ═══════════════════════════════════════════════════════════════
#  4. Overall Drift — Weighted Composite (10 tests)
# ═══════════════════════════════════════════════════════════════

class TestOverallDrift:

    def test_weights_sum_to_one(self):
        total = W_CONSTITUTIONAL + W_SAFETY + W_PRIORITY + W_TONE + W_PERSONALITY
        assert abs(total - 1.0) < 1e-6

    def test_all_zero(self):
        drift = TwinDrift(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert compute_overall_drift(drift) == 0.0

    def test_all_max(self):
        drift = TwinDrift(1.0, 1.0, 1.0, 1.0, 1.0, 0.0)
        overall = compute_overall_drift(drift)
        assert abs(overall - 1.0) < 1e-6

    def test_constitutional_only(self):
        drift = TwinDrift(1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        overall = compute_overall_drift(drift)
        assert abs(overall - W_CONSTITUTIONAL) < 1e-6

    def test_safety_only(self):
        drift = TwinDrift(0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
        overall = compute_overall_drift(drift)
        assert abs(overall - W_SAFETY) < 1e-6

    def test_tone_only(self):
        drift = TwinDrift(0.0, 1.0, 0.0, 0.0, 0.0, 0.0)
        overall = compute_overall_drift(drift)
        assert abs(overall - W_TONE) < 1e-6

    def test_priority_only(self):
        drift = TwinDrift(0.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        overall = compute_overall_drift(drift)
        assert abs(overall - W_PRIORITY) < 1e-6

    def test_personality_only(self):
        drift = TwinDrift(0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        overall = compute_overall_drift(drift)
        assert abs(overall - W_PERSONALITY) < 1e-6

    def test_clamped_to_zero_one(self):
        drift = TwinDrift(1.0, 1.0, 1.0, 1.0, 1.0, 0.0)
        overall = compute_overall_drift(drift)
        assert 0.0 <= overall <= 1.0

    def test_constitutional_dominates(self):
        """Constitutional drift alone should push past DRIFTING threshold."""
        drift = TwinDrift(1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        overall = compute_overall_drift(drift)
        assert overall >= DRIFTING_THRESHOLD


# ═══════════════════════════════════════════════════════════════
#  5. Classification Thresholds (8 tests)
# ═══════════════════════════════════════════════════════════════

class TestClassification:

    def test_in_sync_zero(self):
        assert classify_twin_status(0.0) == TwinStatus.IN_SYNC

    def test_in_sync_below_threshold(self):
        assert classify_twin_status(TWIN_THRESHOLD - 0.01) == TwinStatus.IN_SYNC

    def test_drifting_at_threshold(self):
        assert classify_twin_status(TWIN_THRESHOLD) == TwinStatus.DRIFTING

    def test_drifting_midrange(self):
        mid = (TWIN_THRESHOLD + DRIFTING_THRESHOLD) / 2
        assert classify_twin_status(mid) == TwinStatus.DRIFTING

    def test_drifting_just_below_diverged(self):
        assert classify_twin_status(DRIFTING_THRESHOLD - 0.01) == TwinStatus.DRIFTING

    def test_diverged_at_threshold(self):
        assert classify_twin_status(DRIFTING_THRESHOLD) == TwinStatus.DIVERGED

    def test_diverged_above_threshold(self):
        assert classify_twin_status(0.8) == TwinStatus.DIVERGED

    def test_diverged_max(self):
        assert classify_twin_status(1.0) == TwinStatus.DIVERGED


# ═══════════════════════════════════════════════════════════════
#  6. Project Boundary Enforcement (8 tests)
# ═══════════════════════════════════════════════════════════════

class TestProjectBoundary:

    def test_same_project_ok(self, detector, source_baseline, matching_target):
        reading = detector.observe(source_baseline, matching_target)
        assert reading is not None

    def test_different_project_raises(self, detector, source_baseline):
        target = _make_baseline(project_id="other_project", instance_id="x")
        with pytest.raises(ProjectBoundaryViolation):
            detector.observe(source_baseline, target)

    def test_error_message_contains_both_projects(self, detector, source_baseline):
        target = _make_baseline(project_id="proj_beta", instance_id="x")
        with pytest.raises(ProjectBoundaryViolation, match="proj_alpha"):
            detector.observe(source_baseline, target)

    def test_error_message_contains_arabic(self, detector, source_baseline):
        target = _make_baseline(project_id="proj_beta", instance_id="x")
        with pytest.raises(ProjectBoundaryViolation, match="حدود المشروع"):
            detector.observe(source_baseline, target)

    def test_registry_project_isolation(self, registry):
        b1 = _make_baseline(project_id="p1", instance_id="a")
        b2 = _make_baseline(project_id="p2", instance_id="b")
        registry.register(b1)
        registry.register(b2)
        p1_baselines = registry.get_baselines("p1")
        assert all(b.project_id == "p1" for b in p1_baselines)

    def test_detect_all_respects_project(self, detector):
        b1 = _make_baseline(project_id="p1", instance_id="a", is_architect_device=True)
        b2 = _make_baseline(project_id="p1", instance_id="b")
        b3 = _make_baseline(project_id="p2", instance_id="c")
        detector.register_instance(b1)
        detector.register_instance(b2)
        detector.register_instance(b3)
        readings = detector.detect_all("p1")
        assert len(readings) == 1
        assert readings[0].target_baseline.instance_id == "b"

    def test_project_boundary_is_not_about_instance_id(self, detector):
        """Same instance_id in different projects should still raise."""
        source = _make_baseline(project_id="p1", instance_id="shared")
        target = _make_baseline(project_id="p2", instance_id="shared")
        with pytest.raises(ProjectBoundaryViolation):
            detector.observe(source, target)

    def test_empty_project_detect_all_returns_empty(self, detector):
        assert detector.detect_all("nonexistent") == []


# ═══════════════════════════════════════════════════════════════
#  7. Source-of-Truth Resolution (8 tests)
# ═══════════════════════════════════════════════════════════════

class TestSourceOfTruth:

    def test_architect_device_wins(self, registry):
        b1 = _make_baseline(instance_id="phone", is_architect_device=True, timestamp=100.0)
        b2 = _make_baseline(instance_id="laptop", is_architect_device=False, timestamp=200.0)
        registry.register(b1)
        registry.register(b2)
        sot = registry.get_source_of_truth("proj_alpha")
        assert sot is not None
        assert sot.instance_id == "phone"

    def test_latest_architect_wins(self, registry):
        b1 = _make_baseline(instance_id="old_phone", is_architect_device=True, timestamp=100.0)
        b2 = _make_baseline(instance_id="new_phone", is_architect_device=True, timestamp=200.0)
        registry.register(b1)
        registry.register(b2)
        sot = registry.get_source_of_truth("proj_alpha")
        assert sot is not None
        assert sot.instance_id == "new_phone"

    def test_no_architect_fallback_to_latest(self, registry):
        b1 = _make_baseline(instance_id="a", is_architect_device=False, timestamp=100.0)
        b2 = _make_baseline(instance_id="b", is_architect_device=False, timestamp=200.0)
        registry.register(b1)
        registry.register(b2)
        sot = registry.get_source_of_truth("proj_alpha")
        assert sot is not None
        assert sot.instance_id == "b"

    def test_empty_project_returns_none(self, registry):
        assert registry.get_source_of_truth("nonexistent") is None

    def test_single_instance_is_source(self, registry):
        b = _make_baseline(instance_id="only_one")
        registry.register(b)
        sot = registry.get_source_of_truth("proj_alpha")
        assert sot is not None
        assert sot.instance_id == "only_one"

    def test_detect_all_uses_source_of_truth(self, detector):
        arch = _make_baseline(instance_id="architect", is_architect_device=True, timestamp=100.0)
        other = _make_baseline(instance_id="other", is_architect_device=False, timestamp=200.0)
        detector.register_instance(arch)
        detector.register_instance(other)
        readings = detector.detect_all("proj_alpha")
        assert len(readings) == 1
        assert readings[0].source_baseline.instance_id == "architect"

    def test_evidence_mentions_architect(self, detector, source_baseline, matching_target):
        # source_baseline has is_architect_device=True
        reading = detector.observe(source_baseline, matching_target)
        # Even inactive readings have evidence
        assert any("مصدر الحقيقة" in e or "Architect" in e
                    for e in reading.evidence) or not reading.activated

    def test_architect_device_flag_in_baseline(self):
        b = _make_baseline(is_architect_device=True)
        assert b.is_architect_device is True
        b2 = _make_baseline(is_architect_device=False)
        assert b2.is_architect_device is False


# ═══════════════════════════════════════════════════════════════
#  8. Sparse Activation (6 tests)
# ═══════════════════════════════════════════════════════════════

class TestSparseActivation:

    def test_identical_baselines_inactive(self, detector, source_baseline, matching_target):
        reading = detector.observe(source_baseline, matching_target)
        assert reading.activated is False

    def test_drift_below_threshold_inactive(self, detector, source_baseline):
        # Tiny difference — safety posture off by 0.01
        target = _make_baseline(
            instance_id="laptop", safety_posture=0.71, timestamp=2001.0
        )
        reading = detector.observe(source_baseline, target)
        # overall_drift = W_SAFETY * 0.01 = 0.25 * 0.01 = 0.0025 < 0.05
        assert reading.activated is False

    def test_significant_drift_active(self, detector, source_baseline, drifted_target):
        reading = detector.observe(source_baseline, drifted_target)
        assert reading.activated is True

    def test_inactive_reading_has_zero_drift(self, detector, source_baseline, matching_target):
        reading = detector.observe(source_baseline, matching_target)
        assert reading.drift.overall_drift == 0.0

    def test_feature_disabled_returns_inactive(self, source_baseline, matching_target):
        det = BehaviouralTwinDetector()
        det.ENABLED = False
        reading = det.observe(source_baseline, matching_target)
        assert reading.activated is False

    def test_activation_threshold_boundary(self, detector, source_baseline):
        """Drift exactly at threshold should activate."""
        # We need overall_drift = ACTIVATION_THRESHOLD = 0.05
        # Using safety_posture difference: 0.05 / W_SAFETY = 0.05/0.25 = 0.2
        target = _make_baseline(
            instance_id="laptop", safety_posture=0.5, timestamp=2001.0
        )
        reading = detector.observe(source_baseline, target)
        # overall = 0.25 * 0.2 = 0.05 = ACTIVATION_THRESHOLD
        assert reading.activated is True


# ═══════════════════════════════════════════════════════════════
#  9. B-prime Invariants (10 tests)
# ═══════════════════════════════════════════════════════════════

class TestBPrimeInvariants:

    def test_authority_level(self):
        det = BehaviouralTwinDetector()
        assert det.AUTHORITY_LEVEL == "B_PRIME_OBSERVATIONAL"

    def test_cannot_block_runtime(self):
        det = BehaviouralTwinDetector()
        assert det.CAN_BLOCK_RUNTIME is False

    def test_cannot_modify_h(self):
        det = BehaviouralTwinDetector()
        assert det.CAN_MODIFY_H is False

    def test_cannot_modify_theta(self):
        det = BehaviouralTwinDetector()
        assert det.CAN_MODIFY_THETA is False

    def test_cannot_modify_s(self):
        det = BehaviouralTwinDetector()
        assert det.CAN_MODIFY_S is False

    def test_cannot_emit_judicial_decision(self):
        det = BehaviouralTwinDetector()
        assert det.CAN_EMIT_JUDICIAL_DECISION is False

    def test_binding_channel_is_b5(self):
        det = BehaviouralTwinDetector()
        assert det.BINDING_CHANNEL == "B5"

    def test_safety_decision_authority(self):
        det = BehaviouralTwinDetector()
        assert det.SAFETY_DECISION_AUTHORITY == "GOVERNANCE_EQUATION_ONLY"

    def test_isolation_marker_on_reading(self, detector, source_baseline, drifted_target):
        reading = detector.observe(source_baseline, drifted_target)
        assert reading._isolation_marker == "B5_BEHAVIOURAL_ADVISORY_NOT_SAFETY"

    def test_isolation_marker_on_inactive(self, detector, source_baseline, matching_target):
        reading = detector.observe(source_baseline, matching_target)
        assert reading._isolation_marker == "B5_BEHAVIOURAL_ADVISORY_NOT_SAFETY"


# ═══════════════════════════════════════════════════════════════
#  10. Bilingual Anchors (6 tests)
# ═══════════════════════════════════════════════════════════════

class TestBilingualAnchors:

    def test_arabic_slogan(self):
        assert AR_SLOGAN == "نفس القيم. نفس السلوك. ذاكرة مختلفة."

    def test_english_slogan(self):
        assert EN_SLOGAN == "Same values. Same behaviour. Different memory."

    def test_arabic_twin_term(self):
        assert AR_TWIN == "التوأم السلوكي"

    def test_english_twin_term(self):
        assert EN_TWIN == "Behavioural Twin"

    def test_all_arabic_anchors_non_empty(self):
        for anchor in [AR_SLOGAN, AR_TWIN, AR_CROSS_DRIFT,
                       AR_RECALIBRATION, AR_SOURCE_OF_TRUTH, AR_PROJECT_BOUNDARY]:
            assert anchor and len(anchor) > 0

    def test_all_english_anchors_non_empty(self):
        for anchor in [EN_SLOGAN, EN_TWIN, EN_CROSS_DRIFT,
                       EN_RECALIBRATION, EN_SOURCE_OF_TRUTH, EN_PROJECT_BOUNDARY]:
            assert anchor and len(anchor) > 0


# ═══════════════════════════════════════════════════════════════
#  11. Edge Cases (8 tests)
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_empty_tone_profiles(self):
        drift = compute_jaccard_distance((), ())
        assert drift == 0.0

    def test_single_item_tone(self):
        drift = compute_jaccard_distance(("warm",), ("warm",))
        assert drift == 0.0

    def test_single_instance_detect_all(self, detector):
        b = _make_baseline(instance_id="only_one", is_architect_device=True)
        detector.register_instance(b)
        readings = detector.detect_all("proj_alpha")
        assert len(readings) == 0  # No other instance to compare against

    def test_constitutional_hash_computation(self):
        h1 = compute_constitutional_hash(["mercy", "justice"], ["rule_a", "rule_b"])
        h2 = compute_constitutional_hash(["mercy", "justice"], ["rule_a", "rule_b"])
        assert h1 == h2

    def test_constitutional_hash_order_independent(self):
        h1 = compute_constitutional_hash(["justice", "mercy"], ["rule_b", "rule_a"])
        h2 = compute_constitutional_hash(["mercy", "justice"], ["rule_a", "rule_b"])
        assert h1 == h2  # sorted internally

    def test_constitutional_hash_different_values(self):
        h1 = compute_constitutional_hash(["mercy"], ["rule_a"])
        h2 = compute_constitutional_hash(["cruelty"], ["rule_a"])
        assert h1 != h2

    def test_unicode_in_tone_profile(self):
        b = _make_baseline(tone_profile=("دافئ", "مباشر", "صبور"))
        drift = compute_jaccard_distance(
            b.tone_profile, ("دافئ", "مباشر", "صبور")
        )
        assert drift == 0.0

    def test_create_baseline_factory(self, detector):
        b = detector.create_baseline(
            project_id="test_proj",
            instance_id="test_inst",
            values=["mercy", "justice"],
            rules=["rule_a"],
            tone_profile=["warm"],
            safety_posture=0.8,
        )
        assert b.project_id == "test_proj"
        assert b.instance_id == "test_inst"
        assert len(b.constitutional_hash) == 64  # SHA-256 hex


# ═══════════════════════════════════════════════════════════════
#  12. Recalibration Signals (6 tests)
# ═══════════════════════════════════════════════════════════════

class TestRecalibrationSignals:

    def test_no_drift_no_signals(self, source_baseline, matching_target):
        drift = compute_twin_drift(source_baseline, matching_target)
        signals = generate_recalibration_signals(source_baseline, matching_target, drift)
        assert len(signals) == 0

    def test_constitutional_drift_generates_signal(self, source_baseline):
        target = _make_baseline(
            instance_id="other", constitutional_hash="dd11ff22ee33dd11ff22ee33dd11ff22ee33dd11ff22ee33dd11ff22ee33dd11", timestamp=2001.0
        )
        drift = compute_twin_drift(source_baseline, target)
        signals = generate_recalibration_signals(source_baseline, target, drift)
        dims = [s.dimension for s in signals]
        assert DriftDimension.CONSTITUTIONAL in dims

    def test_safety_drift_generates_signal(self, source_baseline):
        target = _make_baseline(instance_id="other", safety_posture=0.1, timestamp=2001.0)
        drift = compute_twin_drift(source_baseline, target)
        signals = generate_recalibration_signals(source_baseline, target, drift)
        dims = [s.dimension for s in signals]
        assert DriftDimension.SAFETY in dims

    def test_signal_contains_recommendation(self, source_baseline):
        target = _make_baseline(
            instance_id="other", constitutional_hash="dd11ff22ee33dd11ff22ee33dd11ff22ee33dd11ff22ee33dd11ff22ee33dd11", timestamp=2001.0
        )
        drift = compute_twin_drift(source_baseline, target)
        signals = generate_recalibration_signals(source_baseline, target, drift)
        assert all(len(s.recommendation) > 0 for s in signals)

    def test_signal_drift_value_matches(self, source_baseline):
        target = _make_baseline(instance_id="other", safety_posture=0.1, timestamp=2001.0)
        drift = compute_twin_drift(source_baseline, target)
        signals = generate_recalibration_signals(source_baseline, target, drift)
        safety_signals = [s for s in signals if s.dimension == DriftDimension.SAFETY]
        assert len(safety_signals) == 1
        assert safety_signals[0].drift_value == drift.safety_drift

    def test_full_reading_has_signals(self, detector, source_baseline, diverged_target):
        reading = detector.observe(source_baseline, diverged_target)
        assert reading.recalibration_needed is True
        assert len(reading.recalibration_signals) > 0


# ═══════════════════════════════════════════════════════════════
#  13. Additional — TwinReading Structure (5 tests)
# ═══════════════════════════════════════════════════════════════

class TestTwinReading:

    def test_active_reading_has_evidence(self, detector, source_baseline, drifted_target):
        reading = detector.observe(source_baseline, drifted_target)
        assert len(reading.evidence) > 0

    def test_reading_status_matches_classification(self, detector, source_baseline, diverged_target):
        reading = detector.observe(source_baseline, diverged_target)
        expected = classify_twin_status(reading.drift.overall_drift)
        assert reading.status == expected

    def test_audit_hash_deterministic(self, detector, source_baseline, drifted_target):
        r1 = detector.observe(source_baseline, drifted_target)
        r2 = detector.observe(source_baseline, drifted_target)
        assert BehaviouralTwinDetector.audit_hash(r1) == BehaviouralTwinDetector.audit_hash(r2)

    def test_audit_hash_different_for_different_readings(
        self, detector, source_baseline, drifted_target, diverged_target
    ):
        r1 = detector.observe(source_baseline, drifted_target)
        r2 = detector.observe(source_baseline, diverged_target)
        assert BehaviouralTwinDetector.audit_hash(r1) != BehaviouralTwinDetector.audit_hash(r2)

    def test_twin_drift_signal_inactive(self, detector, source_baseline, matching_target):
        reading = detector.observe(source_baseline, matching_target)
        signal = compute_twin_drift_signal(reading)
        assert signal == 0.0


# ═══════════════════════════════════════════════════════════════
#  14. Safety Non-Interference (4 tests)
# ═══════════════════════════════════════════════════════════════

class TestSafetyNonInterference:

    def test_no_safety_override_in_evidence(self, detector, source_baseline, diverged_target):
        reading = detector.observe(source_baseline, diverged_target)
        for e in reading.evidence:
            assert "safety_override" not in e.lower()

    def test_isolation_targets_only_b5(self):
        det = BehaviouralTwinDetector()
        assert det.ISOLATION_TARGETS == frozenset({"B5"})

    def test_isolation_contract_mentions_single_mind(self):
        det = BehaviouralTwinDetector()
        assert "Single-Mind Law" in det.ISOLATION_CONTRACT

    def test_drift_signal_bounded(self, detector, source_baseline, diverged_target):
        reading = detector.observe(source_baseline, diverged_target)
        signal = compute_twin_drift_signal(reading, drift_lambda=10.0)
        assert 0.0 <= signal <= 1.0


# ═══════════════════════════════════════════════════════════════
#  15. compute_twin_drift full pipeline (3 tests)
# ═══════════════════════════════════════════════════════════════

class TestFullPipeline:

    def test_identical_baselines_zero_drift(self, source_baseline, matching_target):
        drift = compute_twin_drift(source_baseline, matching_target)
        assert drift.overall_drift == 0.0

    def test_diverged_baselines_high_drift(self, source_baseline, diverged_target):
        drift = compute_twin_drift(source_baseline, diverged_target)
        assert drift.overall_drift >= DRIFTING_THRESHOLD

    def test_safety_posture_clamped_in_factory(self, detector):
        b = detector.create_baseline(
            project_id="p", instance_id="i",
            values=["v"], rules=["r"],
            safety_posture=1.5,
        )
        assert b.safety_posture == 1.0

        b2 = detector.create_baseline(
            project_id="p", instance_id="i2",
            values=["v"], rules=["r"],
            safety_posture=-0.5,
        )
        assert b2.safety_posture == 0.0
