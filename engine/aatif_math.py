#!/usr/bin/env python3
"""
AATIF Shared Math Utilities — الأدوات الرياضية المشتركة

Single source of truth for mathematical functions used across
multiple AATIF engine modules.

M7 fix: sigmoid was defined identically in aatif_s_equation.py,
aatif_r_equation.py, and aatif_intent_engine.py. Three copies → one.

Usage:
    from aatif_math import sigmoid

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
"""

import math


def sigmoid(x: float) -> float:
    """Standard sigmoid σ(x) = 1 / (1 + e^(-x)).

    Clamped to [-500, 500] to prevent overflow in math.exp.
    Used by both S equation (safety) and R equation (style).
    """
    x = max(-500.0, min(500.0, x))
    return 1.0 / (1.0 + math.exp(-x))


# ═══════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    assert abs(sigmoid(0.0) - 0.5) < 1e-10
    assert sigmoid(500) > 0.999
    assert sigmoid(-500) < 0.001
    print("sigmoid — shared math module OK")
    print(f"  σ(0)  = {sigmoid(0.0)}")
    print(f"  σ(5)  = {sigmoid(5.0):.6f}")
    print(f"  σ(-5) = {sigmoid(-5.0):.6f}")
