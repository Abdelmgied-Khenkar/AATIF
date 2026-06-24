#!/usr/bin/env python3
"""
AATIF Shared Embedding Backend — المحرك المشترك للتضمينات

Single source of truth for the Ollama embedding backend used by
the H scorer (aatif_semantic_scorer), I scorer (aatif_intent_scorer),
and E scorer (aatif_emotion_scorer).

M7 fix: Previously each scorer had its own identical copy of this class.
Three copies → one. Any bug fix or improvement now lands once.

Usage:
    from aatif_embeddings import OllamaBackend, OLLAMA_EMBED_MODEL, USE_OLLAMA

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
"""

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
#  Self-test
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("OllamaBackend — shared embedding module loaded OK")
    print(f"  Model: {OLLAMA_EMBED_MODEL}")
    print(f"  URL:   {OLLAMA_URL}")
    print(f"  USE_OLLAMA: {USE_OLLAMA}")
