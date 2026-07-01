#!/usr/bin/env python3
"""
AATIF Shared Embedding Backend & Utilities — المحرك المشترك للتضمينات

Single source of truth for:
  1. OllamaBackend — the Ollama embedding class used by H, I, E scorers
  2. Embedding utilities — cosine_similarity, top_k_matches,
     softmax_weighted_score, confidence_label — patterns that were
     duplicated across 8+ engine modules.

These utilities are B-prime (خدمية): they serve the governance layers
but carry no governance logic themselves.

M7 fix: Previously each scorer had its own identical copy of OllamaBackend.
Three copies → one. Any bug fix or improvement now lands once.

Consolidation: cosine_similarity was implemented independently in
aatif_judgment_memory, aatif_semantic_scorer, aatif_false_goodness_detector,
and others. top_k weighted scoring was copy-pasted across intent_scorer,
emotion_scorer, semantic_scorer, and false_goodness_detector. Now one copy.

Usage:
    from aatif_embeddings import OllamaBackend, OLLAMA_EMBED_MODEL, USE_OLLAMA
    from aatif_embeddings import cosine_similarity, top_k_matches

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

from typing import List, Sequence, Tuple, Union

import numpy as np

# ─── Configuration ─────────────────────────────────────────
USE_OLLAMA = True
OLLAMA_EMBED_MODEL = "bge-m3"  # best Arabic on Ollama; run once: ollama pull bge-m3
OLLAMA_URL = "http://127.0.0.1:11434/api/embed"


class OllamaBackend:
    """Local Ollama embeddings — shared across H, I, and E scorers.

    Setup once:  ollama pull bge-m3

    Handles:
      - Batch embedding via Ollama /api/embed
      - L2 normalization (safe: zero-norm → kept as zeros)
      - NaN/inf sanitization
      - Cosine similarity via dot product on unit vectors
    """

    def __init__(self, texts: list[str],
                 model: str = OLLAMA_EMBED_MODEL,
                 url: str = OLLAMA_URL):
        self.url = url
        self.model = model
        self.emb = self._embed(texts)

    def _embed(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts → normalized matrix (N × D)."""
        import json
        import urllib.request

        body = json.dumps({"model": self.model, "input": texts}).encode()
        req = urllib.request.Request(
            self.url, data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())

        m = np.array(data["embeddings"], dtype=float)

        # Safe normalization: avoid divide-by-zero for empty embeddings
        norms = np.linalg.norm(m, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        m = m / norms

        # Replace any NaN/inf from bad embeddings with zeros
        m = np.nan_to_num(m, nan=0.0, posinf=0.0, neginf=0.0)
        return m

    def sim(self, text: str) -> np.ndarray:
        """Cosine similarity of *text* against all anchors.

        Returns a 1-D array of similarities, one per anchor.
        """
        q = self._embed([text])[0]

        # Defensive: clean and unit-normalize the QUERY vector BEFORE the
        # dot product, so a genuinely bad embedding (inf/NaN/zero norm)
        # can't poison the result.
        q = np.nan_to_num(q, nan=0.0, posinf=0.0, neginf=0.0)
        qn = np.linalg.norm(q)
        if qn != 0:
            q = q / qn

        # NOTE: even with finite, unit-normalized inputs, NumPy's matmul
        # ufunc can raise SPURIOUS "divide by zero / overflow / invalid
        # value encountered in matmul" RuntimeWarnings on some BLAS
        # builds — the result is still correct and finite.
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            sims = self.emb @ q

        return np.nan_to_num(sims, nan=0.0, posinf=0.0, neginf=0.0)


# ═══════════════════════════════════════════════════════════
#  Standalone embedding utilities
#  (no Ollama dependency — pure numpy)
# ═══════════════════════════════════════════════════════════


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors.

    Returns 0.0 on degenerate input (zero-norm vectors, empty arrays).

    This consolidates the pattern found in:
      - aatif_judgment_memory._cosine_similarity
      - aatif_semantic_scorer (sklearn import)
      - aatif_false_goodness_detector (sklearn import)

    Args:
        a: First vector (1-D numpy array).
        b: Second vector (1-D numpy array).

    Returns:
        Cosine similarity as a float in [-1.0, 1.0].

    Examples:
        >>> cosine_similarity(np.array([1, 0, 0]), np.array([1, 0, 0]))
        1.0
        >>> cosine_similarity(np.array([1, 0]), np.array([0, 1]))
        0.0
        >>> cosine_similarity(np.zeros(3), np.array([1, 2, 3]))
        0.0
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0:
        return 0.0
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def cosine_similarity_matrix(
    query: np.ndarray, matrix: np.ndarray
) -> np.ndarray:
    """Cosine similarity of a single query vector against a matrix of vectors.

    Replaces the sklearn.metrics.pairwise.cosine_similarity import pattern
    found in aatif_semantic_scorer and aatif_false_goodness_detector.

    Args:
        query: 1-D vector (D,) or 2-D row (1, D).
        matrix: 2-D matrix (N, D) — each row is a vector.

    Returns:
        1-D array of N similarity scores.

    Examples:
        >>> m = np.eye(3)
        >>> cosine_similarity_matrix(np.array([1, 0, 0]), m)
        array([1., 0., 0.])
    """
    query = np.asarray(query, dtype=float)
    matrix = np.asarray(matrix, dtype=float)

    if query.ndim == 2:
        query = query[0]

    # Normalize query
    qn = np.linalg.norm(query)
    if qn < 1e-9:
        return np.zeros(matrix.shape[0])
    q = query / qn

    # Normalize each row of the matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms < 1e-9, 1.0, norms)
    m = matrix / norms

    sims = m @ q
    return np.nan_to_num(sims, nan=0.0, posinf=0.0, neginf=0.0)


def top_k_matches(
    sims: np.ndarray,
    texts: Sequence[str],
    levels: np.ndarray,
    k: int = 3,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[Tuple[str, float, float]]]:
    """Extract the top-K nearest anchors from a similarity array.

    This consolidates the identical argsort/slice pattern found in:
      - aatif_intent_scorer.IntentScorer.score()
      - aatif_emotion_scorer.EmotionScorer.score()
      - aatif_semantic_scorer.HarmScorer.score()
      - aatif_false_goodness_detector.VirtueScorer.score()

    Args:
        sims: 1-D array of cosine similarities (one per anchor).
        texts: Sequence of anchor texts (same length as sims).
        levels: 1-D array of anchor level values (same length as sims).
        k: How many top matches to return.

    Returns:
        Tuple of (k_indices, k_similarities, k_levels, top_info) where:
          - k_indices: indices of top-K anchors (descending similarity)
          - k_similarities: similarity values for those indices
          - k_levels: level values for those indices
          - top_info: list of (text, similarity, level) for display

    Examples:
        >>> sims = np.array([0.1, 0.9, 0.5])
        >>> texts = ["a", "b", "c"]
        >>> levels = np.array([0.0, 1.0, 0.5])
        >>> idx, s, l, info = top_k_matches(sims, texts, levels, k=2)
        >>> list(idx)
        [1, 2]
    """
    order = np.argsort(sims)[::-1]
    k_idx = order[:k]
    k_sims = sims[k_idx]
    k_levels = levels[k_idx]
    top_info = [
        (texts[i], round(float(sims[i]), 2), float(levels[i]))
        for i in order[:k]
    ]
    return k_idx, k_sims, k_levels, top_info


def softmax_weighted_score(
    similarities: np.ndarray,
    levels: np.ndarray,
    temperature: float = 0.05,
) -> float:
    """Compute a softmax-weighted score from similarity/level pairs.

    This is the core scoring math shared by I, E, H, and V scorers:
      w = exp(sim / temperature)
      w = w / sum(w)
      score = sum(w * levels)

    Args:
        similarities: 1-D array of cosine similarities (top-K).
        levels: 1-D array of corresponding level values.
        temperature: Softmax temperature (lower = more peaked).

    Returns:
        Weighted score as a float.

    Examples:
        >>> softmax_weighted_score(np.array([0.9]), np.array([1.0]), 0.05)
        1.0
        >>> 0.0 <= softmax_weighted_score(np.array([0.5, 0.3]), np.array([0.8, 0.2]), 0.05) <= 1.0
        True
    """
    w = np.exp(similarities / temperature)
    total = w.sum()
    if total < 1e-12:
        return 0.5  # degenerate → neutral
    w = w / total
    return float((w * levels).sum())


def confidence_label(
    max_similarity: float,
    high_threshold: float = 0.45,
    medium_threshold: float = 0.30,
) -> str:
    """Classify confidence based on max cosine similarity.

    Shared threshold logic used by I, E, and H scorers.

    Args:
        max_similarity: The highest cosine similarity in the result.
        high_threshold: Above this → "high".
        medium_threshold: Above this → "medium". Below → "low".

    Returns:
        One of "high", "medium", or "low".

    Examples:
        >>> confidence_label(0.50)
        'high'
        >>> confidence_label(0.35)
        'medium'
        >>> confidence_label(0.20)
        'low'
    """
    if max_similarity >= high_threshold:
        return "high"
    elif max_similarity >= medium_threshold:
        return "medium"
    else:
        return "low"


def normalize_vectors(matrix: np.ndarray) -> np.ndarray:
    """L2-normalize each row of a matrix, safely handling zero-norm rows.

    Args:
        matrix: 2-D array (N, D).

    Returns:
        Normalized matrix where each row has unit L2 norm
        (zero rows remain zero).

    Examples:
        >>> m = np.array([[3.0, 4.0], [0.0, 0.0]])
        >>> result = normalize_vectors(m)
        >>> np.allclose(result[0], [0.6, 0.8])
        True
        >>> np.allclose(result[1], [0.0, 0.0])
        True
    """
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim == 1:
        n = np.linalg.norm(matrix)
        return matrix / n if n > 1e-9 else matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms < 1e-9, 1.0, norms)
    result = matrix / norms
    return np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)


# ═══════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("OllamaBackend — shared embedding module loaded OK")
    print(f"  Model: {OLLAMA_EMBED_MODEL}")
    print(f"  URL:   {OLLAMA_URL}")
    print(f"  USE_OLLAMA: {USE_OLLAMA}")
    print()
    # Quick smoke test of utilities
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.0, 1.0, 0.0])
    print(f"  cosine_similarity([1,0,0], [0,1,0]) = {cosine_similarity(a, b)}")
    print(f"  confidence_label(0.5) = {confidence_label(0.5)}")
    print("  All utilities loaded OK.")
