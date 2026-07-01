#!/usr/bin/env python3
"""
Tests for aatif_embeddings.py — embedding utility functions
=============================================================

WHY THIS FILE EXISTS
--------------------
aatif_embeddings consolidates embedding-related utilities that were
duplicated across 8+ engine modules: cosine_similarity, top_k_matches,
softmax_weighted_score, confidence_label, normalize_vectors, and
cosine_similarity_matrix.

These tests pin the contract for each utility. All tests are pure
numpy — no Ollama or model server required, fully CI-friendly.

TESTING STRATEGY
----------------
  - cosine_similarity: identity, orthogonal, anti-parallel, zero-norm,
    empty, mixed-sign vectors
  - cosine_similarity_matrix: 1-D query, 2-D query, zero rows
  - top_k_matches: ordering, k truncation, edge cases
  - softmax_weighted_score: single anchor, multiple, temperature effect
  - confidence_label: threshold boundaries
  - normalize_vectors: unit norm, zero rows, 1-D input

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.aatif_embeddings import (  # noqa: E402
    cosine_similarity,
    cosine_similarity_matrix,
    top_k_matches,
    softmax_weighted_score,
    confidence_label,
    normalize_vectors,
)


# ═══════════════════════════════════════════════════════════
#  cosine_similarity
# ═══════════════════════════════════════════════════════════

class TestCosineSimilarity:
    """Tests for the cosine_similarity function."""

    def test_identical_vectors(self):
        """Same vector → similarity = 1.0."""
        v = np.array([1.0, 2.0, 3.0])
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Perpendicular vectors → similarity = 0.0."""
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        """Anti-parallel vectors → similarity = -1.0."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([-1.0, 0.0, 0.0])
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector_first(self):
        """Zero first vector → 0.0 (degenerate)."""
        assert cosine_similarity(np.zeros(3), np.array([1, 2, 3])) == 0.0

    def test_zero_vector_second(self):
        """Zero second vector → 0.0 (degenerate)."""
        assert cosine_similarity(np.array([1, 2, 3]), np.zeros(3)) == 0.0

    def test_both_zero(self):
        """Both zero → 0.0."""
        assert cosine_similarity(np.zeros(3), np.zeros(3)) == 0.0

    def test_empty_vectors(self):
        """Empty arrays → 0.0."""
        assert cosine_similarity(np.array([]), np.array([])) == 0.0

    def test_returns_float(self):
        """Result should always be a Python float."""
        v = np.array([1.0, 2.0])
        result = cosine_similarity(v, v)
        assert isinstance(result, float)

    def test_scale_invariance(self):
        """Cosine similarity is invariant to vector magnitude."""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([100.0, 200.0, 300.0])
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_negative_components(self):
        """Vectors with negative components."""
        a = np.array([1.0, -1.0])
        b = np.array([-1.0, 1.0])
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_accepts_list_like(self):
        """Should accept list-like inputs (converted internally)."""
        assert cosine_similarity(
            np.array([1, 0, 0]), np.array([1, 0, 0])
        ) == pytest.approx(1.0)

    def test_high_dimensional(self):
        """Works with high-dimensional vectors (like embeddings)."""
        rng = np.random.RandomState(42)
        a = rng.randn(1024)
        # Similarity with itself should be 1.0
        assert cosine_similarity(a, a) == pytest.approx(1.0)


# ═══════════════════════════════════════════════════════════
#  cosine_similarity_matrix
# ═══════════════════════════════════════════════════════════

class TestCosineSimilarityMatrix:
    """Tests for the cosine_similarity_matrix function."""

    def test_identity_matrix(self):
        """Query against identity matrix → one-hot result."""
        m = np.eye(3)
        result = cosine_similarity_matrix(np.array([1, 0, 0]), m)
        np.testing.assert_array_almost_equal(result, [1.0, 0.0, 0.0])

    def test_2d_query(self):
        """2-D query (1, D) should be handled correctly."""
        m = np.eye(3)
        result = cosine_similarity_matrix(np.array([[0, 1, 0]]), m)
        np.testing.assert_array_almost_equal(result, [0.0, 1.0, 0.0])

    def test_zero_query(self):
        """Zero query → all zeros."""
        m = np.eye(3)
        result = cosine_similarity_matrix(np.zeros(3), m)
        np.testing.assert_array_equal(result, [0.0, 0.0, 0.0])

    def test_zero_row_in_matrix(self):
        """Zero row in matrix → zero similarity for that row."""
        m = np.array([[1.0, 0.0], [0.0, 0.0], [0.0, 1.0]])
        result = cosine_similarity_matrix(np.array([1.0, 0.0]), m)
        assert result[0] == pytest.approx(1.0)
        assert result[1] == pytest.approx(0.0)
        assert result[2] == pytest.approx(0.0)

    def test_returns_correct_length(self):
        """Result length matches number of rows in matrix."""
        m = np.random.randn(10, 5)
        result = cosine_similarity_matrix(np.random.randn(5), m)
        assert len(result) == 10

    def test_no_nan_or_inf(self):
        """Result should never contain NaN or inf."""
        m = np.random.randn(5, 3)
        result = cosine_similarity_matrix(np.random.randn(3), m)
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))


# ═══════════════════════════════════════════════════════════
#  top_k_matches
# ═══════════════════════════════════════════════════════════

class TestTopKMatches:
    """Tests for the top_k_matches function."""

    def test_basic_ordering(self):
        """Top-K should return indices in descending similarity order."""
        sims = np.array([0.1, 0.9, 0.5, 0.3])
        texts = ["a", "b", "c", "d"]
        levels = np.array([0.0, 1.0, 0.5, 0.3])
        idx, s, l, info = top_k_matches(sims, texts, levels, k=2)
        assert list(idx) == [1, 2]  # b (0.9), c (0.5)
        assert s[0] == pytest.approx(0.9)
        assert s[1] == pytest.approx(0.5)

    def test_k_larger_than_array(self):
        """K larger than array length → return all."""
        sims = np.array([0.1, 0.9])
        texts = ["a", "b"]
        levels = np.array([0.0, 1.0])
        idx, s, l, info = top_k_matches(sims, texts, levels, k=10)
        assert len(idx) == 2

    def test_k_equals_one(self):
        """K=1 → only the best match."""
        sims = np.array([0.3, 0.7, 0.5])
        texts = ["x", "y", "z"]
        levels = np.array([0.1, 0.9, 0.5])
        idx, s, l, info = top_k_matches(sims, texts, levels, k=1)
        assert len(idx) == 1
        assert idx[0] == 1  # "y" has highest sim

    def test_info_format(self):
        """top_info should be a list of (text, sim, level) tuples."""
        sims = np.array([0.5, 0.8])
        texts = ["hello", "world"]
        levels = np.array([0.3, 0.7])
        _, _, _, info = top_k_matches(sims, texts, levels, k=2)
        assert len(info) == 2
        assert info[0][0] == "world"  # highest sim first
        assert isinstance(info[0][1], float)  # rounded sim
        assert isinstance(info[0][2], float)  # level

    def test_levels_match_indices(self):
        """Returned levels should correspond to the correct indices."""
        sims = np.array([0.1, 0.4, 0.9, 0.2])
        texts = ["a", "b", "c", "d"]
        levels = np.array([0.0, 0.3, 1.0, 0.1])
        idx, s, l, info = top_k_matches(sims, texts, levels, k=3)
        # Top 3: c(0.9), b(0.4), d(0.2)
        assert l[0] == pytest.approx(1.0)  # c's level
        assert l[1] == pytest.approx(0.3)  # b's level


# ═══════════════════════════════════════════════════════════
#  softmax_weighted_score
# ═══════════════════════════════════════════════════════════

class TestSoftmaxWeightedScore:
    """Tests for the softmax_weighted_score function."""

    def test_single_anchor(self):
        """Single anchor → returns its level directly."""
        score = softmax_weighted_score(
            np.array([0.9]), np.array([0.7]), temperature=0.05
        )
        assert score == pytest.approx(0.7)

    def test_dominant_anchor(self):
        """When one similarity is much higher, score → its level."""
        score = softmax_weighted_score(
            np.array([0.9, 0.1]), np.array([1.0, 0.0]), temperature=0.05
        )
        # With temp=0.05, exp(0.9/0.05)=exp(18) >> exp(0.1/0.05)=exp(2)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_equal_similarities(self):
        """Equal similarities → average of levels."""
        score = softmax_weighted_score(
            np.array([0.5, 0.5]), np.array([0.0, 1.0]), temperature=0.05
        )
        assert score == pytest.approx(0.5)

    def test_result_bounded(self):
        """Score should be between min and max levels."""
        rng = np.random.RandomState(42)
        sims = rng.rand(10)
        levels = rng.rand(10)
        score = softmax_weighted_score(sims, levels, temperature=0.05)
        assert levels.min() <= score <= levels.max() + 1e-9

    def test_temperature_effect(self):
        """Lower temperature → more peaked distribution."""
        sims = np.array([0.6, 0.5])
        levels = np.array([1.0, 0.0])
        score_low_temp = softmax_weighted_score(sims, levels, temperature=0.01)
        score_high_temp = softmax_weighted_score(sims, levels, temperature=1.0)
        # Low temp should be closer to 1.0 (favors highest sim)
        assert score_low_temp > score_high_temp

    def test_zero_similarities(self):
        """Zero similarities → degenerate, returns 0.5."""
        score = softmax_weighted_score(
            np.zeros(3), np.array([0.0, 0.5, 1.0]), temperature=0.05
        )
        # exp(0/0.05)=1.0 for all → equal weights → average
        assert score == pytest.approx(0.5)


# ═══════════════════════════════════════════════════════════
#  confidence_label
# ═══════════════════════════════════════════════════════════

class TestConfidenceLabel:
    """Tests for the confidence_label function."""

    def test_high_confidence(self):
        """Above high threshold → 'high'."""
        assert confidence_label(0.50) == "high"
        assert confidence_label(0.45) == "high"

    def test_medium_confidence(self):
        """Between thresholds → 'medium'."""
        assert confidence_label(0.35) == "medium"
        assert confidence_label(0.30) == "medium"

    def test_low_confidence(self):
        """Below medium threshold → 'low'."""
        assert confidence_label(0.20) == "low"
        assert confidence_label(0.0) == "low"

    def test_custom_thresholds(self):
        """Custom thresholds should be respected."""
        assert confidence_label(0.8, high_threshold=0.9) == "medium"
        assert confidence_label(0.95, high_threshold=0.9) == "high"

    def test_boundary_values(self):
        """Exact boundary values: >= means inclusive."""
        assert confidence_label(0.45) == "high"   # exactly at high threshold
        assert confidence_label(0.30) == "medium"  # exactly at medium threshold
        assert confidence_label(0.2999) == "low"   # just below medium


# ═══════════════════════════════════════════════════════════
#  normalize_vectors
# ═══════════════════════════════════════════════════════════

class TestNormalizeVectors:
    """Tests for the normalize_vectors function."""

    def test_unit_norm_rows(self):
        """Each row should have unit L2 norm after normalization."""
        m = np.array([[3.0, 4.0], [5.0, 12.0]])
        result = normalize_vectors(m)
        norms = np.linalg.norm(result, axis=1)
        np.testing.assert_array_almost_equal(norms, [1.0, 1.0])

    def test_zero_row_stays_zero(self):
        """Zero row should remain zero (not NaN/inf)."""
        m = np.array([[1.0, 0.0], [0.0, 0.0]])
        result = normalize_vectors(m)
        np.testing.assert_array_almost_equal(result[1], [0.0, 0.0])

    def test_1d_input(self):
        """1-D vector should be normalized."""
        v = np.array([3.0, 4.0])
        result = normalize_vectors(v)
        assert np.linalg.norm(result) == pytest.approx(1.0)

    def test_no_nan_or_inf(self):
        """Result should never contain NaN or inf."""
        m = np.random.randn(10, 5)
        result = normalize_vectors(m)
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))

    def test_direction_preserved(self):
        """Normalization should preserve direction."""
        m = np.array([[3.0, 4.0]])
        result = normalize_vectors(m)
        np.testing.assert_array_almost_equal(result[0], [0.6, 0.8])

    def test_already_normalized(self):
        """Already unit-norm vectors should stay unchanged."""
        m = np.array([[1.0, 0.0], [0.0, 1.0]])
        result = normalize_vectors(m)
        np.testing.assert_array_almost_equal(result, m)
