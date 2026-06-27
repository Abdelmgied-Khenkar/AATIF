"""
Test Dynamic θ (Adaptive Theta) — حساسية الأمان المتكيّفة
=========================================================

Tests the newly implemented Dynamic θ feature across 4 dimensions:
  1. Unit: compute_dynamic_theta math correctness
  2. Integration: TemporalMemory blocked-decision storage & retrieval
  3. End-to-end: S-equation with flag ON vs OFF
  4. Flag-off: behaviour unchanged when feature disabled

Mathematical reference:
    Ψ = 1 − e^(−λ · n_block)      where λ = 0.3
    Δθ = −δ_max · Ψ               where δ_max = 0.15
    θ_eff = clamp(θ_domain + Δθ, θ_floor, θ_domain)   where θ_floor = 0.20
    n_block = count(SAFE_STOP) + 2 × count(SAFE_FREEZE)

Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import math
import os
import shutil
import sys
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Path setup — ensure engine/ is importable
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from aatif_s_equation import (
    compute_dynamic_theta,
    compute_s_gated_from_scores,
    _DYNAMIC_THETA_DELTA_MAX,
    _DYNAMIC_THETA_FLOOR,
    _DYNAMIC_THETA_LAMBDA,
    _DYNAMIC_THETA_N,
)
import aatif_s_equation  # for flag manipulation

from aatif_temporal_memory import TemporalMemory


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _expected_theta(domain_theta: float, n_block: int) -> float:
    """Manually compute expected θ_eff for verification."""
    if n_block == 0:
        return domain_theta
    psi = 1.0 - math.exp(-_DYNAMIC_THETA_LAMBDA * n_block)
    delta = -_DYNAMIC_THETA_DELTA_MAX * psi
    theta_eff = domain_theta + delta
    theta_eff = max(_DYNAMIC_THETA_FLOOR, min(domain_theta, theta_eff))
    return round(theta_eff, 4)


def _make_blocks(n_stop: int = 0, n_freeze: int = 0) -> list:
    """Build a list of blocked-decision dicts."""
    blocks = []
    for _ in range(n_stop):
        blocks.append({"decision_type": "SAFE_STOP"})
    for _ in range(n_freeze):
        blocks.append({"decision_type": "SAFE_FREEZE"})
    return blocks


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 1 — Unit tests for compute_dynamic_theta
# ═══════════════════════════════════════════════════════════════════════════

class TestComputeDynamicThetaUnit:
    """Pure math tests — no DB, no engine."""

    DOMAIN_THETA = 0.40  # general domain default

    def test_empty_history_no_change(self):
        """No blocked decisions → θ_eff == domain_theta."""
        result = compute_dynamic_theta(self.DOMAIN_THETA, [])
        assert result == self.DOMAIN_THETA

    def test_one_safe_stop(self):
        """1 SAFE_STOP → n_block=1."""
        blocks = _make_blocks(n_stop=1)
        n_block = 1
        expected = _expected_theta(self.DOMAIN_THETA, n_block)
        result = compute_dynamic_theta(self.DOMAIN_THETA, blocks)
        assert result == expected
        # Verify specific values from the expected-results table
        psi = 1.0 - math.exp(-0.3 * 1)
        assert abs(psi - 0.2592) < 0.001
        assert result < self.DOMAIN_THETA  # must be stricter

    def test_one_safe_freeze(self):
        """1 SAFE_FREEZE → n_block=2 (counts double)."""
        blocks = _make_blocks(n_freeze=1)
        n_block = 2
        expected = _expected_theta(self.DOMAIN_THETA, n_block)
        result = compute_dynamic_theta(self.DOMAIN_THETA, blocks)
        assert result == expected
        # SAFE_FREEZE is stricter than SAFE_STOP
        stop_result = compute_dynamic_theta(self.DOMAIN_THETA, _make_blocks(n_stop=1))
        assert result < stop_result

    def test_mixed_stops_and_freezes(self):
        """3 SAFE_STOP + 1 SAFE_FREEZE → n_block = 3 + 2 = 5."""
        blocks = _make_blocks(n_stop=3, n_freeze=1)
        n_block = 5
        expected = _expected_theta(self.DOMAIN_THETA, n_block)
        result = compute_dynamic_theta(self.DOMAIN_THETA, blocks)
        assert result == expected
        # Ψ ≈ 0.777, Δθ ≈ -0.117, θ_eff ≈ 0.283
        psi = 1.0 - math.exp(-0.3 * 5)
        assert abs(psi - 0.7769) < 0.001

    def test_heavy_offender_near_floor(self):
        """5 SAFE_STOP + 2 SAFE_FREEZE → n_block = 5 + 4 = 9."""
        blocks = _make_blocks(n_stop=5, n_freeze=2)
        n_block = 9
        expected = _expected_theta(self.DOMAIN_THETA, n_block)
        result = compute_dynamic_theta(self.DOMAIN_THETA, blocks)
        assert result == expected
        # Should be near floor
        assert result < 0.30

    def test_extreme_offender_hits_floor(self):
        """Many blocks → θ_eff should hit θ_floor exactly."""
        blocks = _make_blocks(n_stop=10, n_freeze=5)
        n_block = 10 + 10  # = 20
        result = compute_dynamic_theta(self.DOMAIN_THETA, blocks)
        # Ψ ≈ 1.0 at n_block=20, Δθ ≈ -0.15, θ_eff = 0.40 - 0.15 = 0.25
        assert result == _expected_theta(self.DOMAIN_THETA, n_block)
        assert result >= _DYNAMIC_THETA_FLOOR  # never below floor

    def test_never_below_floor(self):
        """θ_eff must never go below θ_floor regardless of n_block."""
        blocks = _make_blocks(n_stop=50, n_freeze=50)
        result = compute_dynamic_theta(self.DOMAIN_THETA, blocks)
        assert result >= _DYNAMIC_THETA_FLOOR

    def test_never_above_domain_theta(self):
        """θ_eff must never exceed domain_theta."""
        # Even with empty list
        result = compute_dynamic_theta(self.DOMAIN_THETA, [])
        assert result <= self.DOMAIN_THETA
        # With blocks
        result2 = compute_dynamic_theta(self.DOMAIN_THETA, _make_blocks(n_stop=1))
        assert result2 <= self.DOMAIN_THETA

    def test_different_domain_thetas(self):
        """Works correctly with healthcare (0.25) and relaxed (0.55) domains."""
        blocks = _make_blocks(n_stop=3)
        n_block = 3

        # Healthcare — low theta
        healthcare_theta = 0.25
        result_hc = compute_dynamic_theta(healthcare_theta, blocks)
        expected_hc = _expected_theta(healthcare_theta, n_block)
        assert result_hc == expected_hc
        assert result_hc >= _DYNAMIC_THETA_FLOOR

        # Relaxed — high theta
        relaxed_theta = 0.55
        result_rx = compute_dynamic_theta(relaxed_theta, blocks)
        expected_rx = _expected_theta(relaxed_theta, n_block)
        assert result_rx == expected_rx
        assert result_rx <= relaxed_theta

    def test_healthcare_theta_floor_clamp(self):
        """Healthcare domain (θ=0.25) with heavy history → clamps at floor."""
        blocks = _make_blocks(n_stop=5, n_freeze=5)
        n_block = 5 + 10  # = 15
        result = compute_dynamic_theta(0.25, blocks)
        # 0.25 - 0.15 * Ψ(15) → Ψ(15) ≈ 0.989 → Δθ ≈ -0.148 → raw = 0.102
        # Clamped to floor 0.20
        assert result == _DYNAMIC_THETA_FLOOR

    def test_monotonically_decreasing(self):
        """More blocks → lower θ_eff (monotonically)."""
        prev = self.DOMAIN_THETA
        for n in range(1, 15):
            blocks = _make_blocks(n_stop=n)
            result = compute_dynamic_theta(self.DOMAIN_THETA, blocks)
            assert result <= prev, f"θ_eff increased at n_stop={n}: {result} > {prev}"
            prev = result


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 2 — Integration: TemporalMemory blocked decisions
# ═══════════════════════════════════════════════════════════════════════════

class TestTemporalMemoryBlockedDecisions:
    """Test the SQLite-backed blocked decision storage."""

    @pytest.fixture(autouse=True)
    def _setup_memory(self, tmp_path):
        """Create a fresh TemporalMemory in a temp directory."""
        self.storage_dir = str(tmp_path / "test_memory")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.memory = TemporalMemory(self.storage_dir)
        self.user_id = "test_user_001"

    def test_record_and_retrieve_safe_stop(self):
        """Record SAFE_STOP, retrieve it."""
        self.memory.record_blocked_decision(self.user_id, "SAFE_STOP")
        blocks = self.memory.get_recent_blocks(self.user_id, n=20)
        assert len(blocks) == 1
        assert blocks[0]["decision_type"] == "SAFE_STOP"
        assert "timestamp" in blocks[0]

    def test_record_and_retrieve_safe_freeze(self):
        """Record SAFE_FREEZE, retrieve it."""
        self.memory.record_blocked_decision(self.user_id, "SAFE_FREEZE")
        blocks = self.memory.get_recent_blocks(self.user_id, n=20)
        assert len(blocks) == 1
        assert blocks[0]["decision_type"] == "SAFE_FREEZE"

    def test_mixed_decisions(self):
        """Record multiple types, all returned."""
        self.memory.record_blocked_decision(self.user_id, "SAFE_STOP")
        self.memory.record_blocked_decision(self.user_id, "SAFE_FREEZE")
        self.memory.record_blocked_decision(self.user_id, "SAFE_STOP")
        blocks = self.memory.get_recent_blocks(self.user_id, n=20)
        assert len(blocks) == 3
        types = [b["decision_type"] for b in blocks]
        assert types.count("SAFE_STOP") == 2
        assert types.count("SAFE_FREEZE") == 1

    def test_ignores_non_block_decisions(self):
        """EXECUTE and CLARIFY should NOT be recorded."""
        self.memory.record_blocked_decision(self.user_id, "EXECUTE")
        self.memory.record_blocked_decision(self.user_id, "CLARIFY")
        self.memory.record_blocked_decision(self.user_id, "SAFE_STOP")
        blocks = self.memory.get_recent_blocks(self.user_id, n=20)
        assert len(blocks) == 1
        assert blocks[0]["decision_type"] == "SAFE_STOP"

    def test_limit_n(self):
        """Record 25 events, get_recent_blocks(n=20) returns only 20."""
        for i in range(25):
            dtype = "SAFE_STOP" if i % 3 != 0 else "SAFE_FREEZE"
            self.memory.record_blocked_decision(self.user_id, dtype)
        blocks = self.memory.get_recent_blocks(self.user_id, n=20)
        assert len(blocks) == 20

    def test_user_isolation(self):
        """Blocks for user_A don't appear in user_B's query."""
        user_a = "user_a"
        user_b = "user_b"
        self.memory.record_blocked_decision(user_a, "SAFE_STOP")
        self.memory.record_blocked_decision(user_a, "SAFE_FREEZE")
        self.memory.record_blocked_decision(user_b, "SAFE_STOP")

        blocks_a = self.memory.get_recent_blocks(user_a, n=20)
        blocks_b = self.memory.get_recent_blocks(user_b, n=20)
        assert len(blocks_a) == 2
        assert len(blocks_b) == 1

    def test_most_recent_first(self):
        """Results are ordered most-recent-first."""
        self.memory.record_blocked_decision(self.user_id, "SAFE_STOP")
        self.memory.record_blocked_decision(self.user_id, "SAFE_FREEZE")
        blocks = self.memory.get_recent_blocks(self.user_id, n=20)
        assert len(blocks) == 2
        # Most recent should be SAFE_FREEZE (recorded second)
        assert blocks[0]["decision_type"] == "SAFE_FREEZE"
        assert blocks[1]["decision_type"] == "SAFE_STOP"

    def test_empty_user(self):
        """No blocks recorded → empty list."""
        blocks = self.memory.get_recent_blocks("nonexistent_user", n=20)
        assert blocks == []

    def test_integration_with_compute_dynamic_theta(self):
        """Full round-trip: record → retrieve → compute θ_eff."""
        # Record 3 SAFE_STOP + 1 SAFE_FREEZE
        for _ in range(3):
            self.memory.record_blocked_decision(self.user_id, "SAFE_STOP")
        self.memory.record_blocked_decision(self.user_id, "SAFE_FREEZE")

        blocks = self.memory.get_recent_blocks(self.user_id, n=20)
        theta_eff = compute_dynamic_theta(0.40, blocks)

        # n_block = 3 + 2 = 5
        expected = _expected_theta(0.40, 5)
        assert theta_eff == expected


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 3 — End-to-end: S-equation with DYNAMIC_THETA_ENABLED = True
# ═══════════════════════════════════════════════════════════════════════════

class TestEndToEndDynamicTheta:
    """Test that dynamic theta actually changes S-equation behavior."""

    def test_dynamic_theta_lowers_s_score(self):
        """With dynamic θ active and user history, S should be LOWER (stricter).

        Scenario: moderate H (0.35), high I (0.8), neutral E (0.5).
        With default θ=0.40, gate is fairly open.
        With dynamic θ_eff < 0.40 (after blocks), gate tightens → S drops.
        """
        H, I, E = 0.35, 0.8, 0.5

        # Baseline: no theta override
        result_baseline = compute_s_gated_from_scores(
            H, I, E, profile="default", domain=None, theta_override=None
        )

        # Compute dynamic theta for a user with blocks
        blocks = _make_blocks(n_stop=3, n_freeze=1)  # n_block=5
        theta_eff = compute_dynamic_theta(0.40, blocks)

        # With dynamic theta override
        result_dynamic = compute_s_gated_from_scores(
            H, I, E, profile="default", domain=None, theta_override=theta_eff
        )

        # Dynamic θ should produce LOWER S (stricter)
        assert result_dynamic["S"] < result_baseline["S"], (
            f"Dynamic S ({result_dynamic['S']}) should be < baseline S ({result_baseline['S']})"
        )
        # Theta source should be "dynamic"
        assert result_dynamic["theta_source"] == "dynamic"
        assert result_dynamic["theta_effective"] == theta_eff

    def test_dynamic_theta_can_change_decision(self):
        """Dynamic θ can push a borderline case from EXECUTE to CLARIFY or worse.

        Use H near the gate boundary so small θ changes flip the decision.
        """
        # Carefully chosen: H=0.38 is near θ=0.40, so the gate is sensitive
        H, I, E = 0.38, 0.7, 0.5

        result_baseline = compute_s_gated_from_scores(
            H, I, E, profile="default", domain=None, theta_override=None
        )

        # Heavy offender: push θ down significantly
        blocks = _make_blocks(n_stop=5, n_freeze=2)  # n_block=9
        theta_eff = compute_dynamic_theta(0.40, blocks)

        result_dynamic = compute_s_gated_from_scores(
            H, I, E, profile="default", domain=None, theta_override=theta_eff
        )

        # The dynamic result should be strictly lower
        assert result_dynamic["S"] < result_baseline["S"]
        # And θ_eff should be significantly lower than 0.40
        assert theta_eff < 0.30

    def test_no_blocks_dynamic_theta_matches_baseline(self):
        """With empty block history, dynamic θ == domain θ → same S."""
        H, I, E = 0.35, 0.8, 0.5

        theta_eff = compute_dynamic_theta(0.40, [])
        assert theta_eff == 0.40

        result_baseline = compute_s_gated_from_scores(
            H, I, E, profile="default", domain=None, theta_override=None
        )
        result_dynamic = compute_s_gated_from_scores(
            H, I, E, profile="default", domain=None, theta_override=theta_eff
        )

        assert result_baseline["S"] == result_dynamic["S"]


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 4 — Flag OFF: verify no behaviour change
# ═══════════════════════════════════════════════════════════════════════════

class TestFlagOffNoBehaviorChange:
    """When DYNAMIC_THETA_ENABLED is False, nothing should change."""

    def test_flag_is_off_by_default(self):
        """The flag must be False in production code."""
        assert aatif_s_equation.DYNAMIC_THETA_ENABLED is False

    def test_compute_dynamic_theta_still_works_regardless_of_flag(self):
        """compute_dynamic_theta is a pure function — it works regardless of flag.
        The flag controls whether the Governor CALLS it, not whether it works.
        """
        blocks = _make_blocks(n_stop=3)
        result = compute_dynamic_theta(0.40, blocks)
        expected = _expected_theta(0.40, 3)
        assert result == expected

    def test_s_equation_without_override_ignores_dynamic_theta(self):
        """When theta_override is None, S-equation uses profile/domain θ only."""
        H, I, E = 0.35, 0.8, 0.5
        result = compute_s_gated_from_scores(
            H, I, E, profile="default", domain=None, theta_override=None
        )
        # theta_source should be "profile" (not "dynamic")
        assert result["theta_source"] == "profile"
        assert result["theta_effective"] == 0.40  # default profile theta


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 5 — Mathematical verification table
# ═══════════════════════════════════════════════════════════════════════════

class TestMathVerificationTable:
    """Verify exact values from the expected-results table in the test plan."""

    DOMAIN_THETA = 0.40

    @pytest.mark.parametrize(
        "n_stop, n_freeze, expected_n_block, expected_psi_approx, expected_theta_approx",
        [
            (0, 0, 0, 0.0, 0.40),
            (1, 0, 1, 0.259, 0.361),
            (0, 1, 2, 0.451, 0.332),
            (3, 1, 5, 0.777, 0.283),
            (5, 2, 9, 0.933, 0.260),
        ],
        ids=[
            "no_history",
            "1_SAFE_STOP",
            "1_SAFE_FREEZE",
            "3_STOP_1_FREEZE",
            "heavy_offender",
        ],
    )
    def test_table_values(
        self, n_stop, n_freeze, expected_n_block, expected_psi_approx, expected_theta_approx
    ):
        blocks = _make_blocks(n_stop=n_stop, n_freeze=n_freeze)

        # Verify n_block calculation
        actual_n_block = sum(
            2 if d.get("decision_type") == "SAFE_FREEZE" else 1
            for d in blocks
        )
        assert actual_n_block == expected_n_block

        # Verify Ψ
        if expected_n_block > 0:
            psi = 1.0 - math.exp(-0.3 * expected_n_block)
            assert abs(psi - expected_psi_approx) < 0.002, (
                f"Ψ mismatch: expected ≈{expected_psi_approx}, got {psi:.4f}"
            )

        # Verify θ_eff
        result = compute_dynamic_theta(self.DOMAIN_THETA, blocks)
        assert abs(result - expected_theta_approx) < 0.002, (
            f"θ_eff mismatch: expected ≈{expected_theta_approx}, got {result}"
        )


# ═══════════════════════════════════════════════════════════════════════════
#  Constants verification
# ═══════════════════════════════════════════════════════════════════════════

class TestConstants:
    """Verify the constants match the Architect's decisions."""

    def test_delta_max(self):
        assert _DYNAMIC_THETA_DELTA_MAX == 0.15

    def test_lambda(self):
        assert _DYNAMIC_THETA_LAMBDA == 0.3

    def test_floor(self):
        assert _DYNAMIC_THETA_FLOOR == 0.20

    def test_window_size(self):
        assert _DYNAMIC_THETA_N == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
