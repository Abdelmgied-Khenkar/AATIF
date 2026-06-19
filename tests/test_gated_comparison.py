#!/usr/bin/env python3
"""
AATIF S Equation — Classic vs Gated Comparison
===============================================

Side-by-side comparison of the classic and gated S equations
across key adversarial and benign scenarios.

Classic:  S = σ(w₁·I + w₂·E − w₃·H)
Gated:    S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))

The gated equation is designed to resist "toxic positivity" attacks
where high I and E try to compensate for moderate-to-high H.

Run:
    cd ~/Desktop/AATIF-academic && python -m pytest tests/test_gated_comparison.py -v -s
    (or) python tests/test_gated_comparison.py

Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

import sys
import os
import unittest

# Ensure engine is importable
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(os.path.dirname(_THIS_DIR), "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from aatif_s_equation import (
    compute_s_from_scores,
    compute_s_gated_from_scores,
    PROFILES,
    GATED_PROFILES,
)

# ═══════════════════════════════════════════════════════════
# Test scenarios: (name, H, I, E)
# ═══════════════════════════════════════════════════════════
COMPARISON_SCENARIOS = [
    ("Toxic Positivity",            0.80, 1.0, 1.0),
    ("Sugar-Coated Harm",           0.90, 0.9, 0.8),
    ("Very harmful + max disguise", 0.95, 1.0, 1.0),
    ("Pure Harm",                   1.00, 0.0, 0.0),
    ("Benign Request",              0.00, 1.0, 0.8),
    ("Moderate harm + good intent", 0.50, 0.8, 0.6),
    ("Creative but edgy",           0.30, 0.9, 0.7),
    ("Ambiguous religious text",    0.35, 0.7, 0.4),
]


def _decision_emoji(d: str) -> str:
    return {
        "EXECUTE": "✅",
        "CLARIFY": "🟡",
        "SAFE_STOP": "🟠",
        "SAFE_FREEZE": "🔴",
    }.get(d, "❓")


def run_comparison():
    """Print side-by-side results for classic vs gated equations."""
    print("=" * 90)
    print("AATIF S Equation — Classic vs Gated Comparison")
    print("Classic:  S = σ(w₁·I + w₂·E − w₃·H)")
    print("Gated:    S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))")
    print("=" * 90)

    for name, H, I, E in COMPARISON_SCENARIOS:
        print(f"\n{'─' * 90}")
        print(f"  {name}:  H={H:.2f}  I={I:.2f}  E={E:.2f}")
        print(f"{'─' * 90}")

        # Classic — default profile
        c = compute_s_from_scores(H, I, E, profile="default")
        # Gated — default profile
        g = compute_s_gated_from_scores(H, I, E, profile="default")

        print(f"  Classic  │ S={c['S']:.4f}  z={c['z']:.4f}  "
              f"→ {_decision_emoji(c['decision'])} {c['decision']:<12}  "
              f"F={c['F']:.3f}")
        override_tag = " [HARD OVERRIDE]" if g.get("hard_override") else ""
        print(f"  Gated    │ S={g['S']:.4f}  "
              f"quality={g['quality']:.4f}  gate={g['gate']:.4f}  "
              f"→ {_decision_emoji(g['decision'])} {g['decision']:<12}  "
              f"F={g['F']:.3f}{override_tag}")

    # Profile comparison for toxic positivity
    print(f"\n{'=' * 90}")
    print("Profile Comparison — Toxic Positivity (H=0.8, I=1.0, E=1.0)")
    print("=" * 90)

    H, I, E = 0.8, 1.0, 1.0

    print("\n  Classic profiles:")
    for pname in ["high_sensitivity", "default", "casual",
                  "safe_environment", "creative"]:
        c = compute_s_from_scores(H, I, E, profile=pname)
        guard = " ⚠️GUARD" if c.get("guard_applied") else ""
        print(f"    {pname:<20} S={c['S']:.4f}  "
              f"→ {_decision_emoji(c['decision'])} {c['decision']}{guard}")

    print("\n  Gated profiles:")
    for pname in ["high_sensitivity", "default", "creative"]:
        g = compute_s_gated_from_scores(H, I, E, profile=pname)
        override = " [HARD OVERRIDE]" if g.get("hard_override") else ""
        print(f"    {pname:<20} S={g['S']:.4f}  gate={g['gate']:.4f}  "
              f"→ {_decision_emoji(g['decision'])} {g['decision']}{override}")

    print(f"\n{'=' * 90}")
    print("✅ Comparison complete.")
    print("=" * 90)


# ═══════════════════════════════════════════════════════════
# Unit tests: verify gated equation properties
# ═══════════════════════════════════════════════════════════

class TestGatedEquationProperties(unittest.TestCase):
    """Verify mathematical properties of the gated S equation."""

    def test_s_bounded_zero_one(self):
        """S must always be in (0, 1) for any inputs."""
        test_vals = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        for H in test_vals:
            for I in test_vals:
                for E in test_vals:
                    r = compute_s_gated_from_scores(H, I, E)
                    self.assertGreaterEqual(r["S"], 0.0,
                        f"S < 0 for H={H}, I={I}, E={E}")
                    self.assertLessEqual(r["S"], 1.0,
                        f"S > 1 for H={H}, I={I}, E={E}")

    def test_hard_override_above_0_7(self):
        """H > 0.7 must always produce SAFE_FREEZE in gated mode."""
        for H in [0.71, 0.8, 0.9, 1.0]:
            for profile in GATED_PROFILES:
                r = compute_s_gated_from_scores(H, 1.0, 1.0, profile=profile)
                self.assertEqual(r["decision"], "SAFE_FREEZE",
                    f"H={H}, profile={profile}: expected SAFE_FREEZE, "
                    f"got {r['decision']}")
                self.assertTrue(r["hard_override"],
                    f"H={H}: hard_override should be True")

    def test_no_hard_override_at_0_7(self):
        """H = 0.7 exactly should NOT trigger hard override."""
        r = compute_s_gated_from_scores(0.7, 1.0, 1.0)
        self.assertFalse(r["hard_override"])

    def test_benign_request_executes(self):
        """H=0, high I and E → should EXECUTE."""
        r = compute_s_gated_from_scores(0.0, 1.0, 0.8)
        self.assertEqual(r["decision"], "EXECUTE")

    def test_gate_closes_with_high_harm(self):
        """Gate value should be near 0 when H >> theta."""
        r = compute_s_gated_from_scores(0.9, 1.0, 1.0)
        self.assertLess(r["gate"], 0.05,
            f"Gate should be near 0 for H=0.9, got {r['gate']}")

    def test_gate_open_with_low_harm(self):
        """Gate value should be near 1 when H << theta."""
        r = compute_s_gated_from_scores(0.0, 1.0, 1.0)
        self.assertGreater(r["gate"], 0.99,
            f"Gate should be near 1 for H=0.0, got {r['gate']}")

    def test_toxic_positivity_blocked(self):
        """H=0.8, I=1.0, E=1.0 must NOT be EXECUTE in gated mode.
        This is the key attack the gated equation is designed to stop."""
        r = compute_s_gated_from_scores(0.8, 1.0, 1.0)
        self.assertEqual(r["decision"], "SAFE_FREEZE",
            f"Toxic positivity attack: expected SAFE_FREEZE, got {r['decision']}")

    def test_sugar_coated_harm_blocked(self):
        """H=0.9, I=0.9, E=0.8 must be SAFE_FREEZE."""
        r = compute_s_gated_from_scores(0.9, 0.9, 0.8)
        self.assertEqual(r["decision"], "SAFE_FREEZE")

    def test_quality_increases_with_intent(self):
        """Higher I → higher quality signal."""
        r_low = compute_s_gated_from_scores(0.0, 0.3, 0.5)
        r_high = compute_s_gated_from_scores(0.0, 0.9, 0.5)
        self.assertGreater(r_high["quality"], r_low["quality"])

    def test_s_decreases_with_harm(self):
        """Holding I+E constant, higher H → lower S."""
        r_low_harm = compute_s_gated_from_scores(0.1, 0.8, 0.6)
        r_high_harm = compute_s_gated_from_scores(0.6, 0.8, 0.6)
        self.assertGreater(r_low_harm["S"], r_high_harm["S"])

    def test_all_gated_profiles_exist(self):
        """All three gated profiles should compute without error."""
        for profile in ["default", "high_sensitivity", "creative"]:
            r = compute_s_gated_from_scores(0.5, 0.5, 0.5, profile=profile)
            self.assertEqual(r["profile"], profile)
            self.assertEqual(r["equation_mode"], "gated")

    def test_high_sensitivity_stricter_than_creative(self):
        """Same scores: high_sensitivity should produce lower S than creative."""
        H, I, E = 0.4, 0.7, 0.5
        r_hs = compute_s_gated_from_scores(H, I, E, profile="high_sensitivity")
        r_cr = compute_s_gated_from_scores(H, I, E, profile="creative")
        self.assertLess(r_hs["S"], r_cr["S"],
            f"high_sensitivity S={r_hs['S']} should be < creative S={r_cr['S']}")


class TestClassicEquationUnchanged(unittest.TestCase):
    """Verify the classic equation still produces the same results."""

    def test_classic_benign_executes(self):
        r = compute_s_from_scores(0.0, 1.0, 0.8, profile="default")
        self.assertEqual(r["decision"], "EXECUTE")

    def test_classic_harmful_stops(self):
        r = compute_s_from_scores(1.0, 0.0, 0.0, profile="default")
        self.assertIn(r["decision"], ("SAFE_STOP", "SAFE_FREEZE"))

    def test_classic_profiles_still_exist(self):
        for profile in ["default", "high_sensitivity", "safe_environment",
                        "creative", "casual"]:
            r = compute_s_from_scores(0.5, 0.5, 0.5, profile=profile)
            self.assertEqual(r["profile"], profile)

    def test_classic_guard_applied(self):
        """H > 0.7 + creative → guard_applied should be True in classic."""
        r = compute_s_from_scores(0.8, 1.0, 1.0, profile="creative")
        self.assertTrue(r.get("guard_applied"))
        self.assertEqual(r["decision"], "SAFE_STOP")


if __name__ == "__main__":
    # Run comparison first
    run_comparison()
    print("\n")

    # Then run unit tests
    unittest.main(verbosity=2)
