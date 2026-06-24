#!/usr/bin/env python3
"""
AATIF S Equation — Core Mathematical Invariants
================================================

Dedicated, property-based test of the S-equation primitives as pure
mathematical objects, independent of any scorer or live-text pipeline.

Why this file exists (coverage gaps filled — Fahes audit 2026-06-24):
    • link_h_to_intent()  had ZERO test coverage anywhere in tests/.
    • The F follow-up signal harm-floor  F = max(D·(1−S), K·H)  was never
      asserted at the equation level.
    • Monotonicity was only spot-checked at 2 points; this file proves it
      across a full H×I×E grid sweep for BOTH classic and gated equations.
    • Gate identities (gate==0.5 at H==θ, quality independent of H) and the
      decision-threshold boundary mapping were not asserted directly.

These are INVARIANTS, not scenarios. test_gated_comparison.py and
test_domain_theta.py cover scenario/profile/domain behaviour; this file
covers the math the whole framework rests on.

Equations under test:
    Classic:  S = σ(w₁·I + w₂·E − w₃·H)
    Gated:    S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))
    Hard override (gated):  H > 0.7 → SAFE_FREEZE (absolute)
    Follow-up signal:       F = max(1·(1−S), K_HARM_FLOOR·H)

Run:
    cd ~/Desktop/AATIF-academic && python -m pytest tests/test_s_equation.py -v

Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic) — Agent فاحص (Fahes)
License: BSL 1.1
"""

import os
import sys
import unittest

# Ensure engine/ is importable even when run directly (conftest also does this).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(os.path.dirname(_THIS_DIR), "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from aatif_math import sigmoid
from aatif_s_equation import (
    compute_s_from_scores,
    compute_s_gated_from_scores,
    link_h_to_intent,
    PROFILES,
    GATED_PROFILES,
    THRESHOLDS,
    K_HARM_FLOOR,
    H_GATED_HARD_OVERRIDE,
    H_GUARD_THRESHOLD,
    H_I_LINK_LAMBDA,
)

# A coarse but exhaustive grid for sweep-based invariants.
_GRID = [i / 10.0 for i in range(0, 11)]  # 0.0, 0.1, ..., 1.0


# ═══════════════════════════════════════════════════════════
#  1. sigmoid — shared math primitive
# ═══════════════════════════════════════════════════════════
class TestSigmoid(unittest.TestCase):
    """σ(x) = 1/(1+e^-x) — the primitive both S and R equations stand on."""

    def test_midpoint(self):
        self.assertAlmostEqual(sigmoid(0.0), 0.5, places=12)

    def test_bounded_open_interval(self):
        # Mathematically σ ∈ (0,1); in IEEE754 the extremes saturate to
        # exactly 0.0 / 1.0, so assert the closed bound here and check the
        # strict open interval on moderate inputs below.
        for x in (-1000, -50, -1, 0, 1, 50, 1000):
            v = sigmoid(x)
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_strict_open_interval_moderate_inputs(self):
        for x in (-30, -5, -1, 0, 1, 5, 30):
            v = sigmoid(x)
            self.assertGreater(v, 0.0)
            self.assertLess(v, 1.0)

    def test_monotonic_increasing(self):
        xs = [-10, -3, -1, 0, 0.5, 1, 3, 10]
        ys = [sigmoid(x) for x in xs]
        for a, b in zip(ys, ys[1:]):
            self.assertLess(a, b)

    def test_odd_symmetry_about_half(self):
        # σ(x) + σ(-x) == 1
        for x in (0.3, 1.0, 4.2, 9.9):
            self.assertAlmostEqual(sigmoid(x) + sigmoid(-x), 1.0, places=12)

    def test_overflow_clamped(self):
        # Must not raise on extreme input (clamped to [-500, 500]).
        self.assertGreater(sigmoid(10_000), 0.999)
        self.assertLess(sigmoid(-10_000), 0.001)


# ═══════════════════════════════════════════════════════════
#  2. link_h_to_intent — the H↔I link (previously UNTESTED)
# ═══════════════════════════════════════════════════════════
class TestLinkHtoIntent(unittest.TestCase):
    """
    H_eff = H · (1 − λ · clip((I − 0.5)/0.5, 0, 1))
    HIGH I = benign; the link discounts H toward 0 as intent gets benign.
    """

    def test_lambda_zero_is_identity(self):
        # λ=0 → no change, for any H, I.
        for H in _GRID:
            for I in _GRID:
                self.assertEqual(link_h_to_intent(H, I, lam=0.0), H)

    def test_lambda_one_benign_zeroes_h(self):
        # Fully benign intent (I=1.0) with λ=1 collapses H to 0.
        self.assertAlmostEqual(link_h_to_intent(0.9, 1.0, lam=1.0), 0.0, places=12)

    def test_neutral_intent_no_relief(self):
        # I at neutral (0.5) → frac=0 → H unchanged regardless of λ.
        self.assertAlmostEqual(link_h_to_intent(0.6, 0.5, lam=1.0), 0.6, places=12)

    def test_harmful_intent_clipped_no_negative_relief(self):
        # I below neutral must NOT inflate H (frac clipped at 0).
        self.assertAlmostEqual(link_h_to_intent(0.6, 0.0, lam=1.0), 0.6, places=12)
        self.assertAlmostEqual(link_h_to_intent(0.6, 0.2, lam=0.5), 0.6, places=12)

    def test_partial_relief_half_benign(self):
        # I=0.75 → frac=(0.75-0.5)/0.5=0.5; λ=0.5 → H·(1-0.25)=0.75·H.
        self.assertAlmostEqual(
            link_h_to_intent(0.8, 0.75, lam=0.5), 0.8 * 0.75, places=12
        )

    def test_relief_monotonic_in_intent(self):
        # As I increases above neutral, effective H is non-increasing.
        prev = float("inf")
        for I in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            cur = link_h_to_intent(0.7, I, lam=1.0)
            self.assertLessEqual(cur, prev + 1e-12)
            prev = cur

    def test_result_never_exceeds_h_or_goes_negative(self):
        for H in _GRID:
            for I in _GRID:
                eff = link_h_to_intent(H, I, lam=H_I_LINK_LAMBDA)
                self.assertGreaterEqual(eff, 0.0)
                self.assertLessEqual(eff, H + 1e-12)


# ═══════════════════════════════════════════════════════════
#  3. Classic equation — bounds, monotonicity, harm floor
# ═══════════════════════════════════════════════════════════
class TestClassicInvariants(unittest.TestCase):
    """S = σ(w₁·I + w₂·E − w₃·H), with F = max(1−S, K·H)."""

    def test_s_bounded_open_interval_full_grid(self):
        for H in _GRID:
            for I in _GRID:
                for E in _GRID:
                    S = compute_s_from_scores(H, I, E)["S"]
                    self.assertGreater(S, 0.0)
                    self.assertLess(S, 1.0)

    def test_s_nonincreasing_in_harm(self):
        # Holding I,E fixed, S must not increase as H rises.
        for I in _GRID:
            for E in _GRID:
                prev = float("inf")
                for H in _GRID:
                    cur = compute_s_from_scores(H, I, E)["S"]
                    self.assertLessEqual(cur, prev + 1e-9)
                    prev = cur

    def test_s_nondecreasing_in_intent(self):
        for H in _GRID:
            for E in _GRID:
                prev = -1.0
                for I in _GRID:
                    cur = compute_s_from_scores(H, I, E)["S"]
                    self.assertGreaterEqual(cur, prev - 1e-9)
                    prev = cur

    def test_s_nondecreasing_in_emotion(self):
        for H in _GRID:
            for I in _GRID:
                prev = -1.0
                for E in _GRID:
                    cur = compute_s_from_scores(H, I, E)["S"]
                    self.assertGreaterEqual(cur, prev - 1e-9)
                    prev = cur

    def test_matches_closed_form(self):
        # Spot-check the exact arithmetic against the documented formula.
        p = PROFILES["default"]
        H, I, E = 0.3, 0.8, 0.6
        z = p["w1"] * I + p["w2"] * E - p["w3"] * H
        self.assertAlmostEqual(
            compute_s_from_scores(H, I, E)["S"], round(sigmoid(z), 4), places=4
        )

    def test_follow_up_harm_floor(self):
        # F = max(1−S, K·H); must never drop below the harm floor K·H.
        for H in _GRID:
            for I in _GRID:
                for E in _GRID:
                    r = compute_s_from_scores(H, I, E)
                    self.assertGreaterEqual(r["F"], round(K_HARM_FLOOR * H, 4) - 1e-9)
                    self.assertGreaterEqual(r["F"], r["F_prime"] - 1e-9)

    def test_creative_guard_blocks_high_harm(self):
        # creative w3 is gentle; guard must force ≥ SAFE_STOP when H>0.7.
        r = compute_s_from_scores(0.85, 1.0, 1.0, profile="creative")
        self.assertIn(r["decision"], ("SAFE_STOP", "SAFE_FREEZE"))
        self.assertTrue(r["guard_applied"])

    def test_guard_flag_off_when_harm_low(self):
        r = compute_s_from_scores(0.1, 0.9, 0.9, profile="creative")
        self.assertFalse(r["guard_applied"])

    def test_all_profiles_present_and_weighted(self):
        for name, p in PROFILES.items():
            for key in ("w1", "w2", "w3"):
                self.assertIn(key, p)
                self.assertGreater(p[key], 0)


# ═══════════════════════════════════════════════════════════
#  4. Gated equation — gate identities, hard override, toxic positivity
# ═══════════════════════════════════════════════════════════
class TestGatedInvariants(unittest.TestCase):
    """S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))."""

    def test_s_bounded_open_interval_full_grid(self):
        # Stay strictly below the 0.7 hard-override band so the gate is live.
        for H in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
            for I in _GRID:
                for E in _GRID:
                    S = compute_s_gated_from_scores(H, I, E)["S"]
                    self.assertGreater(S, 0.0)
                    self.assertLess(S, 1.0)

    def test_gate_half_at_theta(self):
        # At H == θ exactly, the harm gate is precisely 0.5.
        theta = GATED_PROFILES["default"]["theta"]
        r = compute_s_gated_from_scores(theta, 0.5, 0.5)
        self.assertAlmostEqual(r["gate"], 0.5, places=4)

    def test_gate_open_far_below_theta(self):
        r = compute_s_gated_from_scores(0.0, 0.5, 0.5)
        self.assertGreater(r["gate"], 0.97)  # gate ≈ 1 (open)

    def test_gate_closed_far_above_theta(self):
        # Just under the hard override, gate should be near-shut.
        r = compute_s_gated_from_scores(0.69, 0.5, 0.5)
        self.assertLess(r["gate"], 0.10)  # gate ≈ 0 (closed)

    def test_quality_independent_of_harm(self):
        # The quality term σ(w₁I + w₂E) must not move with H.
        q_low = compute_s_gated_from_scores(0.0, 0.8, 0.6)["quality"]
        q_mid = compute_s_gated_from_scores(0.5, 0.8, 0.6)["quality"]
        self.assertAlmostEqual(q_low, q_mid, places=4)

    def test_gate_nonincreasing_in_harm(self):
        prev = float("inf")
        for H in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.69]:
            cur = compute_s_gated_from_scores(H, 0.5, 0.5)["gate"]
            self.assertLessEqual(cur, prev + 1e-9)
            prev = cur

    def test_hard_override_forces_freeze(self):
        # Any H > 0.7 → SAFE_FREEZE, flagged, regardless of I, E.
        for I in _GRID:
            for E in _GRID:
                r = compute_s_gated_from_scores(0.71, I, E)
                self.assertEqual(r["decision"], "SAFE_FREEZE")
                self.assertTrue(r["hard_override"])

    def test_hard_override_still_reports_diagnostic_s(self):
        # Decision is forced, but S is still computed for diagnostics.
        r = compute_s_gated_from_scores(0.9, 1.0, 1.0)
        self.assertIn("S", r)
        self.assertLess(r["S"], 0.3)  # tiny S — gate is essentially shut

    def test_no_hard_override_exactly_at_threshold(self):
        # Boundary is strict: H == 0.7 does NOT trigger the override.
        r = compute_s_gated_from_scores(H_GATED_HARD_OVERRIDE, 0.5, 0.5)
        self.assertFalse(r["hard_override"])

    def test_toxic_positivity_blocked(self):
        # THE key attack: H=0.8, I=1.0, E=1.0 must SAFE_FREEZE, not pass.
        r = compute_s_gated_from_scores(0.8, 1.0, 1.0)
        self.assertEqual(r["decision"], "SAFE_FREEZE")

    def test_perfect_intent_cannot_open_a_shut_gate(self):
        # Even max quality leaves S small once H sits well past θ.
        r = compute_s_gated_from_scores(0.65, 1.0, 1.0)
        self.assertLess(r["S"], 0.3)

    def test_matches_closed_form(self):
        p = GATED_PROFILES["default"]
        H, I, E = 0.3, 0.8, 0.6
        quality = sigmoid(p["w1"] * I + p["w2"] * E)
        gate = 1.0 - sigmoid(p["alpha"] * (H - p["theta"]))
        self.assertAlmostEqual(
            compute_s_gated_from_scores(H, I, E)["S"],
            round(quality * gate, 4),
            places=4,
        )


# ═══════════════════════════════════════════════════════════
#  5. Decision-threshold mapping — boundary correctness
# ═══════════════════════════════════════════════════════════
class TestDecisionThresholds(unittest.TestCase):
    """
    THRESHOLDS map S → decision:
        S > 0.7        → EXECUTE
        0.5 < S ≤ 0.7  → CLARIFY
        0.3 < S ≤ 0.5  → SAFE_STOP
        S ≤ 0.3        → SAFE_FREEZE
    Verified through the same banding logic used in compute_s_from_scores.
    """

    @staticmethod
    def _decision(S: float) -> str:
        decision = "SAFE_FREEZE"
        for threshold, label in THRESHOLDS:
            if S > threshold:
                return label
        return decision

    def test_band_centers(self):
        self.assertEqual(self._decision(0.95), "EXECUTE")
        self.assertEqual(self._decision(0.60), "CLARIFY")
        self.assertEqual(self._decision(0.40), "SAFE_STOP")
        self.assertEqual(self._decision(0.10), "SAFE_FREEZE")

    def test_boundaries_are_exclusive_upper(self):
        # Exactly on a boundary falls into the LOWER band (strict >).
        self.assertEqual(self._decision(0.70), "CLARIFY")     # not EXECUTE
        self.assertEqual(self._decision(0.50), "SAFE_STOP")   # not CLARIFY
        self.assertEqual(self._decision(0.30), "SAFE_FREEZE") # not SAFE_STOP

    def test_just_above_boundary_flips_band(self):
        self.assertEqual(self._decision(0.7001), "EXECUTE")
        self.assertEqual(self._decision(0.5001), "CLARIFY")
        self.assertEqual(self._decision(0.3001), "SAFE_STOP")

    def test_thresholds_descending_and_complete(self):
        vals = [t for t, _ in THRESHOLDS]
        self.assertEqual(vals, sorted(vals, reverse=True))
        self.assertEqual(THRESHOLDS[-1][0], 0.0)  # floor band covers everything


# ═══════════════════════════════════════════════════════════
#  6. Cross-equation safety contract
# ═══════════════════════════════════════════════════════════
class TestCrossEquationSafety(unittest.TestCase):
    """Properties that BOTH equations must honour for governance to hold."""

    def test_high_harm_never_executes_either_equation(self):
        # With H above the hard-override line, neither equation may EXECUTE.
        for H in [0.71, 0.8, 0.9, 1.0]:
            classic = compute_s_from_scores(H, 1.0, 1.0)["decision"]
            gated = compute_s_gated_from_scores(H, 1.0, 1.0)["decision"]
            self.assertNotEqual(classic, "EXECUTE")
            self.assertEqual(gated, "SAFE_FREEZE")

    def test_pure_benign_executes_either_equation(self):
        # No harm, strong intent + emotion → EXECUTE in both.
        self.assertEqual(compute_s_from_scores(0.0, 1.0, 1.0)["decision"], "EXECUTE")
        self.assertEqual(
            compute_s_gated_from_scores(0.0, 1.0, 1.0)["decision"], "EXECUTE"
        )

    def test_guard_threshold_aligns_with_hard_override(self):
        # Classic guard line and gated hard-override line share the 0.7 floor.
        self.assertEqual(H_GUARD_THRESHOLD, H_GATED_HARD_OVERRIDE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
