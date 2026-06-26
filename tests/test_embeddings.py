"""
Tests for aatif_embeddings.py — المحرك المشترك للتضمينات

Tests the shared OllamaBackend class (M7 consolidation).
Since Ollama may not be available in CI, these tests focus on:
  - Module-level configuration constants
  - Import paths (M7: single source of truth)
  - OllamaBackend class interface
  - Error handling for unavailable backends

License: BSL 1.1
"""

import numpy as np
import pytest

from aatif_embeddings import OllamaBackend, OLLAMA_EMBED_MODEL, USE_OLLAMA, OLLAMA_URL


class TestConfiguration:
    """Module-level constants are correctly set."""

    def test_model_is_bge_m3(self):
        """Default model is bge-m3 (best Arabic on Ollama)."""
        assert OLLAMA_EMBED_MODEL == "bge-m3"

    def test_url_is_localhost(self):
        """Default URL points to local Ollama."""
        assert "127.0.0.1" in OLLAMA_URL or "localhost" in OLLAMA_URL
        assert "11434" in OLLAMA_URL

    def test_use_ollama_default_true(self):
        """USE_OLLAMA defaults to True."""
        assert USE_OLLAMA is True


class TestM7SingleSource:
    """M7 regression: OllamaBackend is the single source of truth."""

    def test_import_from_shared_module(self):
        """OllamaBackend is importable from aatif_embeddings."""
        from aatif_embeddings import OllamaBackend as OB
        assert OB is OllamaBackend

    def test_class_has_sim_method(self):
        """OllamaBackend exposes a sim() method for cosine similarity."""
        assert hasattr(OllamaBackend, 'sim')
        assert callable(getattr(OllamaBackend, 'sim'))

    def test_class_has_embed_method(self):
        """OllamaBackend has the private _embed method."""
        assert hasattr(OllamaBackend, '_embed')


class TestOllamaBackendOffline:
    """Tests that work without a running Ollama instance."""

    def test_backend_init_fails_gracefully_without_ollama(self):
        """Constructing OllamaBackend without Ollama raises, not hangs."""
        # With a bad URL, it should raise a connection error
        with pytest.raises(Exception):
            OllamaBackend(
                texts=["test"],
                url="http://127.0.0.1:99999/api/embed",  # bad port
            )

    def test_nan_to_num_in_sim_docstring(self):
        """sim() docs mention NaN/inf handling — verify method exists."""
        import inspect
        source = inspect.getsource(OllamaBackend.sim)
        assert "nan_to_num" in source, (
            "sim() should sanitize NaN/inf values"
        )

    def test_normalization_in_embed_docstring(self):
        """_embed() should perform L2 normalization."""
        import inspect
        source = inspect.getsource(OllamaBackend._embed)
        assert "norm" in source, (
            "_embed() should L2-normalize embeddings"
        )
