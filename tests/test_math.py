"""
Tests for aatif_math.py — الأدوات الرياضية المشتركة

Covers:
  - sigmoid properties (σ(0)=0.5, monotonic, range (0,1))
  - Overflow clamping (extreme inputs don't crash)
  - Symmetry: σ(x) + σ(-x) = 1
  - M7 regression: this is the single source of truth sigmoid

License: BSL 1.1
"""

import math
import pytest

from aatif_math import sigmoid


class TestSigmoidProperties:
    """Mathematical properties of the sigmoid function."""

    def test_sigmoid_at_zero(self):
        """σ(0) = 0.5 — the midpoint."""
        assert abs(sigmoid(0.0) - 0.5) < 1e-10

    def test_sigmoid_positive_above_half(self):
        """σ(x) > 0.5 for x > 0."""
        for x in [0.1, 1.0, 5.0, 10.0]:
            assert sigmoid(x) > 0.5

    def test_sigmoid_negative_below_half(self):
        """σ(x) < 0.5 for x < 0."""
        for x in [-0.1, -1.0, -5.0, -10.0]:
            assert sigmoid(x) < 0.5

    def test_sigmoid_monotonic_increasing(self):
        """σ is strictly monotonically increasing."""
        values = [-10, -5, -1, 0, 1, 5, 10]
        results = [sigmoid(x) for x in values]
        for i in range(len(results) - 1):
            assert results[i] < results[i + 1], (
                f"Not monotonic: σ({values[i]})={results[i]} >= "
                f"σ({values[i+1]})={results[i+1]}"
            )

    def test_sigmoid_range_strictly_0_to_1(self):
        """σ(x) ∈ (0, 1) for all finite x within float64 precision.

        Note: for |x| > ~36, float64 rounds σ to exactly 0 or 1,
        so we only test strict inequality for representable values.
        """
        for x in [-30, -10, -1, 0, 1, 10, 30]:
            s = sigmoid(x)
            assert 0.0 < s < 1.0, f"σ({x})={s} outside open interval (0,1)"

    def test_sigmoid_symmetry(self):
        """σ(x) + σ(-x) = 1 for all x."""
        for x in [0, 0.5, 1.0, 3.0, 10.0, 50.0]:
            assert abs(sigmoid(x) + sigmoid(-x) - 1.0) < 1e-10

    def test_sigmoid_known_values(self):
        """Known sigmoid values match expected."""
        # σ(1) ≈ 0.7311
        assert abs(sigmoid(1.0) - 0.7310585786) < 1e-6
        # σ(-1) ≈ 0.2689
        assert abs(sigmoid(-1.0) - 0.2689414214) < 1e-6
        # σ(5) ≈ 0.9933
        assert abs(sigmoid(5.0) - 0.9933071491) < 1e-6


class TestSigmoidOverflow:
    """Overflow protection — extreme inputs should not crash."""

    def test_large_positive_no_overflow(self):
        """Very large positive x → σ close to 1, no exception."""
        s = sigmoid(1000)
        assert s > 0.999

    def test_large_negative_no_overflow(self):
        """Very large negative x → σ close to 0, no exception."""
        s = sigmoid(-1000)
        assert s < 0.001

    def test_clamp_boundary_500(self):
        """Values are clamped at ±500."""
        # σ(500) and σ(1000) should be effectively the same
        assert abs(sigmoid(500) - sigmoid(1000)) < 1e-10
        assert abs(sigmoid(-500) - sigmoid(-1000)) < 1e-10

    def test_no_nan_or_inf(self):
        """No NaN or inf for any input."""
        for x in [-1e6, -500, -100, 0, 100, 500, 1e6]:
            s = sigmoid(x)
            assert not math.isnan(s)
            assert not math.isinf(s)


class TestSigmoidIntegration:
    """M7 regression: sigmoid is the shared source of truth."""

    def test_import_path(self):
        """sigmoid is importable from aatif_math (the shared module)."""
        from aatif_math import sigmoid as s
        assert callable(s)
        assert abs(s(0) - 0.5) < 1e-10
