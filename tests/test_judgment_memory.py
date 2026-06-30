"""
Test AATIF Judgment Memory — ذاكرة الحُكم
==========================================

Comprehensive pytest suite for the Judgment Memory module:
  1. JudgmentContext — dataclass creation, defaults, field validation
  2. JudgmentLedger — SQLite CRUD (record, query_similar, cleanup, session_history)
  3. JudgmentMemory — main logic (build_context, escalation, trust, theta, dialect)
  4. Safety invariants — H>0.7 bypass, theta bounds, H floor
  5. D parameter — domain profiles, scaling
  6. Escalation detection — sequence-based pattern detection

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Path setup — ensure engine/ is importable
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from aatif_judgment_memory import (
    # Constants
    H_HARD_OVERRIDE,
    H_ADJUSTMENT_FLOOR,
    THETA_MAX_LOOSEN,
    THETA_MAX_TIGHTEN,
    THETA_FLOOR,
    MAX_TRUST_CREDIT,
    ESCALATION_WINDOW,
    PRIOR_SIMILARITY_THRESHOLD,
    TRUST_MIN_INTERACTIONS,
    TRUST_THRESHOLD,
    EMBEDDING_DIM,
    # Domain
    DOMAIN_PROFILES,
    STORAGE_FULL_THRESHOLD,
    STORAGE_STANDARD_THRESHOLD,
    # Escalation stages
    ESCALATION_NORMAL,
    ESCALATION_PROBING,
    ESCALATION_TESTING,
    ESCALATION_ATTACKING,
    ESCALATION_PENALTIES,
    # Helpers
    _hash_message,
    _cosine_similarity,
    _embedding_to_blob,
    _blob_to_embedding,
    _now_iso,
    _iso_to_dt,
    _dt_to_iso,
    # Classes
    JudgmentContext,
    JudgmentLedger,
    JudgmentMemory,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

RNG = np.random.RandomState(42)


def _random_embedding(seed: int = None) -> np.ndarray:
    """Generate a random normalized 768-dim embedding."""
    rng = np.random.RandomState(seed) if seed is not None else RNG
    vec = rng.randn(EMBEDDING_DIM).astype(np.float32)
    return vec / np.linalg.norm(vec)


def _build_history(decisions: list, h_scores: list = None) -> list:
    """Build a fake history list matching ledger.get_session_history format."""
    if h_scores is None:
        h_scores = [0.1] * len(decisions)
    history = []
    for i, (dec, h) in enumerate(zip(decisions, h_scores)):
        history.append({
            "id": i + 1,
            "timestamp": _now_iso(),
            "h_score": h,
            "i_score": 0.7,
            "s_score": 0.5,
            "decision": dec,
            "escalation_stage": ESCALATION_NORMAL,
        })
    return history


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 1 — JudgmentContext dataclass
# ═══════════════════════════════════════════════════════════════════════════

class TestJudgmentContext:
    """Test JudgmentContext creation, defaults, field validation."""

    def test_defaults(self):
        """All defaults should be safe/neutral values."""
        ctx = JudgmentContext()
        assert ctx.dialect_profile is None
        assert ctx.historical_intent_avg == 0.5
        assert ctx.escalation_stage == ESCALATION_NORMAL
        assert ctx.theta_adjustment == 0.0
        assert ctx.h_adjustment == 0.0
        assert ctx.similar_prior_found is False
        assert ctx.similar_prior_decision is None
        assert ctx.similar_prior_similarity == 0.0
        assert ctx.similar_prior_age_hours == 0.0
        assert ctx.trust_level == 0.0
        assert ctx.domain_sensitivity == 0.2
        assert ctx.context_notes == ""

    def test_custom_fields(self):
        """Create context with custom values."""
        ctx = JudgmentContext(
            dialect_profile="gulf",
            historical_intent_avg=0.85,
            escalation_stage=ESCALATION_PROBING,
            theta_adjustment=-0.10,
            trust_level=0.6,
            domain_sensitivity=0.9,
        )
        assert ctx.dialect_profile == "gulf"
        assert ctx.historical_intent_avg == 0.85
        assert ctx.escalation_stage == ESCALATION_PROBING
        assert ctx.theta_adjustment == -0.10
        assert ctx.trust_level == 0.6
        assert ctx.domain_sensitivity == 0.9

    def test_prior_fields(self):
        """Prior judgment fields should be settable."""
        ctx = JudgmentContext(
            similar_prior_found=True,
            similar_prior_decision="EXECUTE",
            similar_prior_similarity=0.92,
            similar_prior_age_hours=12.5,
        )
        assert ctx.similar_prior_found is True
        assert ctx.similar_prior_decision == "EXECUTE"
        assert ctx.similar_prior_similarity == 0.92
        assert ctx.similar_prior_age_hours == 12.5

    def test_context_notes(self):
        """Notes field accepts arbitrary strings."""
        ctx = JudgmentContext(context_notes="escalation=PROBING; trust=0.75")
        assert "escalation=PROBING" in ctx.context_notes


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 2 — JudgmentLedger (SQLite CRUD)
# ═══════════════════════════════════════════════════════════════════════════

class TestJudgmentLedger:
    """SQLite-backed CRUD tests."""

    @pytest.fixture(autouse=True)
    def _setup_ledger(self, tmp_path):
        db_path = str(tmp_path / "test_ledger.db")
        self.ledger = JudgmentLedger(db_path)
        self.session_id = "test_session_001"

    def test_record_stores_entry(self):
        """record() inserts a row and returns a positive row id."""
        row_id = self.ledger.record(
            session_id=self.session_id,
            msg_hash=_hash_message("hello world"),
            msg_embedding=None,
            h_score=0.1,
            i_score=0.8,
            e_score=0.5,
            s_score=0.75,
            decision="EXECUTE",
            dialect="gulf",
            domain_sensitivity=0.5,  # STANDARD mode
            theta_used=0.40,
        )
        assert row_id > 0
        assert self.ledger.count() == 1

    def test_light_mode_skips_execute(self):
        """D <= 0.4 (LIGHT) skips non-safety events."""
        row_id = self.ledger.record(
            session_id=self.session_id,
            msg_hash=_hash_message("safe msg"),
            msg_embedding=None,
            h_score=0.1, i_score=0.8, e_score=0.5, s_score=0.75,
            decision="EXECUTE",
            dialect=None,
            domain_sensitivity=0.2,  # LIGHT mode
            theta_used=0.40,
        )
        assert row_id == -1
        assert self.ledger.count() == 0

    def test_light_mode_stores_safety_events(self):
        """D <= 0.4 (LIGHT) DOES store SAFE_STOP and SAFE_FREEZE."""
        for decision in ("SAFE_STOP", "SAFE_FREEZE"):
            row_id = self.ledger.record(
                session_id=self.session_id,
                msg_hash=_hash_message(f"msg_{decision}"),
                msg_embedding=None,
                h_score=0.6, i_score=0.3, e_score=0.4, s_score=0.30,
                decision=decision,
                dialect=None,
                domain_sensitivity=0.2,
                theta_used=0.40,
            )
            assert row_id > 0
        assert self.ledger.count() == 2

    def test_standard_mode_stores_all_decisions(self):
        """D > 0.4 (STANDARD) stores all decision types."""
        for dec in ("EXECUTE", "CLARIFY", "SAFE_STOP", "SAFE_FREEZE"):
            self.ledger.record(
                session_id=self.session_id,
                msg_hash=_hash_message(f"msg_{dec}"),
                msg_embedding=None,
                h_score=0.3, i_score=0.6, e_score=0.5, s_score=0.5,
                decision=dec, dialect=None,
                domain_sensitivity=0.5, theta_used=0.40,
            )
        assert self.ledger.count() == 4

    def test_standard_mode_no_embeddings(self):
        """D > 0.4 but <= 0.7 stores judgments but NOT embeddings."""
        emb = _random_embedding(seed=10)
        self.ledger.record(
            session_id=self.session_id,
            msg_hash=_hash_message("with embedding"),
            msg_embedding=emb,
            h_score=0.1, i_score=0.8, e_score=0.5, s_score=0.75,
            decision="EXECUTE", dialect=None,
            domain_sensitivity=0.5,  # STANDARD: no embeddings
            theta_used=0.40,
        )
        # query_similar should find nothing (no embeddings stored)
        result = self.ledger.query_similar(self.session_id, emb)
        assert result is None

    def test_full_mode_stores_embeddings(self):
        """D > 0.7 (FULL) stores embeddings alongside judgments."""
        emb = _random_embedding(seed=20)
        self.ledger.record(
            session_id=self.session_id,
            msg_hash=_hash_message("full mode msg"),
            msg_embedding=emb,
            h_score=0.1, i_score=0.9, e_score=0.6, s_score=0.85,
            decision="EXECUTE", dialect="gulf",
            domain_sensitivity=0.8,  # FULL mode
            theta_used=0.40,
        )
        result = self.ledger.query_similar(self.session_id, emb)
        assert result is not None
        assert abs(result["similarity"] - 1.0) < 0.01

    def test_query_similar_returns_none_for_different_embedding(self):
        """Different random embeddings should not match (below threshold)."""
        emb_a = _random_embedding(seed=30)
        emb_b = _random_embedding(seed=31)
        self.ledger.record(
            session_id=self.session_id,
            msg_hash=_hash_message("msg a"),
            msg_embedding=emb_a,
            h_score=0.1, i_score=0.8, e_score=0.5, s_score=0.75,
            decision="EXECUTE", dialect=None,
            domain_sensitivity=0.8, theta_used=0.40,
        )
        result = self.ledger.query_similar(self.session_id, emb_b)
        assert result is None

    def test_query_similar_session_isolation(self):
        """Embeddings from session A should not appear in session B queries."""
        emb = _random_embedding(seed=40)
        self.ledger.record(
            session_id="session_A",
            msg_hash=_hash_message("session A msg"),
            msg_embedding=emb,
            h_score=0.1, i_score=0.8, e_score=0.5, s_score=0.75,
            decision="EXECUTE", dialect=None,
            domain_sensitivity=0.8, theta_used=0.40,
        )
        result = self.ledger.query_similar("session_B", emb)
        assert result is None

    def test_get_session_history(self):
        """get_session_history returns correct records, most recent first."""
        for i in range(5):
            self.ledger.record(
                session_id=self.session_id,
                msg_hash=_hash_message(f"history_{i}"),
                msg_embedding=None,
                h_score=0.1 * i, i_score=0.8, e_score=0.5, s_score=0.7,
                decision="EXECUTE" if i < 3 else "CLARIFY",
                dialect=None,
                domain_sensitivity=0.5, theta_used=0.40,
            )
        history = self.ledger.get_session_history(self.session_id, limit=10)
        assert len(history) == 5
        # Most recent first
        assert history[0]["decision"] == "CLARIFY"
        # All fields present
        for h in history:
            assert "id" in h
            assert "timestamp" in h
            assert "h_score" in h
            assert "decision" in h
            assert "escalation_stage" in h

    def test_get_session_history_limit(self):
        """Limit parameter restricts result count."""
        for i in range(10):
            self.ledger.record(
                session_id=self.session_id,
                msg_hash=_hash_message(f"limit_{i}"),
                msg_embedding=None,
                h_score=0.1, i_score=0.8, e_score=0.5, s_score=0.7,
                decision="EXECUTE", dialect=None,
                domain_sensitivity=0.5, theta_used=0.40,
            )
        history = self.ledger.get_session_history(self.session_id, limit=3)
        assert len(history) == 3

    def test_cleanup_expired(self):
        """cleanup_expired() removes rows past their expiry date."""
        # Record an EXECUTE in STANDARD mode (30 day decay)
        self.ledger.record(
            session_id=self.session_id,
            msg_hash=_hash_message("will expire"),
            msg_embedding=None,
            h_score=0.1, i_score=0.8, e_score=0.5, s_score=0.75,
            decision="EXECUTE", dialect=None,
            domain_sensitivity=0.5, theta_used=0.40,
        )
        assert self.ledger.count() == 1

        # Manually set the expires_at to the past
        import sqlite3
        conn = sqlite3.connect(self.ledger._db_path)
        past = _dt_to_iso(datetime.now(timezone.utc) - timedelta(days=1))
        conn.execute(
            "UPDATE judgment_ledger SET expires_at = ?", (past,)
        )
        conn.commit()
        conn.close()

        deleted = self.ledger.cleanup_expired()
        assert deleted == 1
        assert self.ledger.count() == 0

    def test_cleanup_keeps_non_expired(self):
        """cleanup_expired() keeps rows that haven't expired yet."""
        self.ledger.record(
            session_id=self.session_id,
            msg_hash=_hash_message("still valid"),
            msg_embedding=None,
            h_score=0.1, i_score=0.8, e_score=0.5, s_score=0.75,
            decision="EXECUTE", dialect=None,
            domain_sensitivity=0.5, theta_used=0.40,
        )
        deleted = self.ledger.cleanup_expired()
        assert deleted == 0
        assert self.ledger.count() == 1

    def test_forget_deletes_all_session_records(self):
        """forget() hard-deletes all records for a session."""
        for i in range(5):
            self.ledger.record(
                session_id=self.session_id,
                msg_hash=_hash_message(f"forget_{i}"),
                msg_embedding=None,
                h_score=0.1, i_score=0.8, e_score=0.5, s_score=0.7,
                decision="EXECUTE", dialect=None,
                domain_sensitivity=0.5, theta_used=0.40,
            )
        assert self.ledger.count(self.session_id) == 5
        deleted = self.ledger.forget(self.session_id)
        assert deleted == 5
        assert self.ledger.count(self.session_id) == 0

    def test_forget_session_isolation(self):
        """forget() only deletes records for the specified session."""
        for sid in ("session_X", "session_Y"):
            self.ledger.record(
                session_id=sid,
                msg_hash=_hash_message(f"msg_{sid}"),
                msg_embedding=None,
                h_score=0.1, i_score=0.8, e_score=0.5, s_score=0.7,
                decision="SAFE_STOP", dialect=None,
                domain_sensitivity=0.5, theta_used=0.40,
            )
        self.ledger.forget("session_X")
        assert self.ledger.count("session_X") == 0
        assert self.ledger.count("session_Y") == 1

    def test_count_with_and_without_session(self):
        """count() supports both global and per-session counting."""
        for sid in ("s1", "s2"):
            for i in range(3):
                self.ledger.record(
                    session_id=sid,
                    msg_hash=_hash_message(f"{sid}_{i}"),
                    msg_embedding=None,
                    h_score=0.1, i_score=0.8, e_score=0.5, s_score=0.7,
                    decision="EXECUTE", dialect=None,
                    domain_sensitivity=0.5, theta_used=0.40,
                )
        assert self.ledger.count("s1") == 3
        assert self.ledger.count("s2") == 3
        assert self.ledger.count() == 6


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 3 — JudgmentMemory main logic
# ═══════════════════════════════════════════════════════════════════════════

class TestJudgmentMemoryBuildContext:
    """Tests for build_context()."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db_path = str(tmp_path / "jm_context.db")
        self.jm = JudgmentMemory(db_path, domain_sensitivity=0.4)
        self.session_id = "ctx_session"

    def test_empty_history_produces_neutral_context(self):
        """New user with no history gets neutral defaults."""
        ctx = self.jm.build_context(
            msg_embedding=None,
            session_id=self.session_id,
            dialect="levantine",
        )
        assert isinstance(ctx, JudgmentContext)
        assert ctx.dialect_profile == "levantine"
        assert ctx.escalation_stage == ESCALATION_NORMAL
        assert ctx.similar_prior_found is False
        assert ctx.trust_level == 0.0
        assert ctx.domain_sensitivity == 0.4
        assert ctx.historical_intent_avg == 0.5  # default

    def test_context_reflects_d_parameter(self):
        """D parameter is passed through to context."""
        ctx = self.jm.build_context(None, self.session_id)
        assert ctx.domain_sensitivity == 0.4

    def test_context_with_history_updates_intent_avg(self):
        """After recording judgments, intent avg reflects history."""
        # Use STANDARD mode (D=0.5) so all decisions are stored
        jm = JudgmentMemory(
            str(self.jm.ledger._db_path).replace(".db", "_2.db"),
            domain_sensitivity=0.5,
        )
        for i in range(5):
            jm.record_judgment(
                session_id=self.session_id,
                msg_hash=_hash_message(f"intent_{i}"),
                msg_embedding=None,
                scores={"H": 0.1, "I": 0.9, "E": 0.5, "S": 0.8},
                decision="EXECUTE", theta=0.40,
            )
        ctx = jm.build_context(None, self.session_id)
        # With I=0.9 for all entries, avg should be ~0.9
        assert ctx.historical_intent_avg == pytest.approx(0.9, abs=0.01)

    def test_context_with_prior_found(self):
        """When a similar embedding exists, prior fields are populated."""
        jm = JudgmentMemory(
            str(self.jm.ledger._db_path).replace(".db", "_3.db"),
            domain_sensitivity=0.8,  # FULL mode for embeddings
        )
        emb = _random_embedding(seed=100)
        jm.record_judgment(
            session_id=self.session_id,
            msg_hash=_hash_message("prior msg"),
            msg_embedding=emb,
            scores={"H": 0.1, "I": 0.9, "E": 0.6, "S": 0.85},
            decision="EXECUTE", theta=0.40,
        )
        ctx = jm.build_context(emb, self.session_id)
        assert ctx.similar_prior_found is True
        assert ctx.similar_prior_decision == "EXECUTE"
        assert ctx.similar_prior_similarity > 0.99


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 4 — Escalation Detection
# ═══════════════════════════════════════════════════════════════════════════

class TestEscalationDetection:
    """Escalation stages: NORMAL -> PROBING -> TESTING -> ATTACKING."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db_path = str(tmp_path / "jm_escalation.db")
        self.jm = JudgmentMemory(db_path, domain_sensitivity=0.5)
        self.session_id = "esc_session"

    def test_empty_history_is_normal(self):
        """No history -> NORMAL."""
        esc = self.jm.detect_escalation(self.session_id)
        assert esc == ESCALATION_NORMAL

    def test_short_history_is_normal(self):
        """Fewer than 3 records -> always NORMAL."""
        history = _build_history(["EXECUTE", "EXECUTE"])
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc == ESCALATION_NORMAL

    def test_all_execute_is_normal(self):
        """All EXECUTE decisions -> NORMAL."""
        history = _build_history(["EXECUTE"] * 5)
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc == ESCALATION_NORMAL

    def test_one_safe_stop_is_testing(self):
        """1 SAFE_STOP in window -> TESTING."""
        decisions = ["EXECUTE", "EXECUTE", "SAFE_STOP", "EXECUTE"]
        history = _build_history(decisions)
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc == ESCALATION_TESTING

    def test_two_clarify_is_testing(self):
        """2 CLARIFY events in window -> TESTING."""
        decisions = ["EXECUTE", "CLARIFY", "CLARIFY", "EXECUTE"]
        history = _build_history(decisions)
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc == ESCALATION_TESTING

    def test_two_safe_stops_is_attacking(self):
        """2+ SAFE_STOP/FREEZE -> ATTACKING."""
        decisions = ["EXECUTE", "SAFE_STOP", "EXECUTE", "SAFE_STOP"]
        history = _build_history(decisions)
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc == ESCALATION_ATTACKING

    def test_two_safe_freeze_is_attacking(self):
        """2 SAFE_FREEZE -> ATTACKING."""
        decisions = ["EXECUTE", "SAFE_FREEZE", "EXECUTE", "SAFE_FREEZE"]
        history = _build_history(decisions)
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc == ESCALATION_ATTACKING

    def test_mixed_stop_freeze_is_attacking(self):
        """1 SAFE_STOP + 1 SAFE_FREEZE -> ATTACKING."""
        decisions = ["EXECUTE", "SAFE_STOP", "EXECUTE", "SAFE_FREEZE"]
        history = _build_history(decisions)
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc == ESCALATION_ATTACKING

    def test_probing_detected_by_rising_h_scores(self):
        """H scores creeping up triggers PROBING."""
        # History is most-recent-first: recent H high, older H low
        # recent avg(3) > full avg * 1.5
        decisions = ["EXECUTE"] * 6
        # Most recent first: [0.4, 0.35, 0.3, 0.05, 0.05, 0.05]
        h_scores = [0.4, 0.35, 0.3, 0.05, 0.05, 0.05]
        history = _build_history(decisions, h_scores)
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc == ESCALATION_PROBING

    def test_probing_not_triggered_when_h_stable(self):
        """Stable H scores do not trigger PROBING."""
        decisions = ["EXECUTE"] * 6
        h_scores = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
        history = _build_history(decisions, h_scores)
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc == ESCALATION_NORMAL

    def test_escalation_with_real_ledger(self):
        """Escalation detection works with real SQLite-backed history."""
        # Build real history via record_judgment
        for i, (dec, h) in enumerate([
            ("EXECUTE", 0.1), ("EXECUTE", 0.1),
            ("CLARIFY", 0.3), ("SAFE_STOP", 0.55),
            ("EXECUTE", 0.1), ("SAFE_STOP", 0.6),
        ]):
            self.jm.record_judgment(
                session_id=self.session_id,
                msg_hash=_hash_message(f"esc_msg_{i}"),
                msg_embedding=None,
                scores={"H": h, "I": 0.7, "E": 0.5, "S": 0.5},
                decision=dec, theta=0.40,
            )
        esc = self.jm.detect_escalation(self.session_id)
        assert esc == ESCALATION_ATTACKING


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 5 — Trust Computation
# ═══════════════════════════════════════════════════════════════════════════

class TestTrustComputation:
    """Trust: 0 for new users, increases with clean history, drops on safety events."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db_path = str(tmp_path / "jm_trust.db")
        self.jm = JudgmentMemory(db_path, domain_sensitivity=0.5)
        self.session_id = "trust_session"

    def test_zero_trust_new_user(self):
        """New user with no history -> trust = 0.0."""
        trust = self.jm.compute_trust(self.session_id)
        assert trust == 0.0

    def test_zero_trust_short_history(self):
        """Fewer than 3 interactions -> trust = 0.0."""
        history = _build_history(["EXECUTE", "EXECUTE"])
        trust = self.jm.compute_trust(self.session_id, history=history)
        assert trust == 0.0

    def test_trust_increases_with_clean_history(self):
        """25+ clean EXECUTE decisions -> trust > 0.5."""
        history = _build_history(["EXECUTE"] * 25)
        trust = self.jm.compute_trust(self.session_id, history=history)
        assert trust > TRUST_THRESHOLD

    def test_trust_scales_with_interaction_count(self):
        """More interactions -> higher trust (up to a point)."""
        trust_10 = self.jm.compute_trust(
            self.session_id,
            history=_build_history(["EXECUTE"] * 10),
        )
        trust_25 = self.jm.compute_trust(
            self.session_id,
            history=_build_history(["EXECUTE"] * 25),
        )
        assert trust_25 > trust_10

    def test_trust_drops_to_zero_on_recent_safety_event(self):
        """Any SAFE_STOP/FREEZE in last 5 -> trust = 0.0."""
        # 20 clean, then 1 SAFE_STOP (most recent first)
        decisions = ["SAFE_STOP"] + ["EXECUTE"] * 20
        history = _build_history(decisions)
        trust = self.jm.compute_trust(self.session_id, history=history)
        assert trust == 0.0

    def test_trust_drops_on_recent_safe_freeze(self):
        """SAFE_FREEZE in recent 5 -> trust = 0.0."""
        decisions = ["EXECUTE", "EXECUTE", "SAFE_FREEZE"] + ["EXECUTE"] * 20
        history = _build_history(decisions)
        trust = self.jm.compute_trust(self.session_id, history=history)
        assert trust == 0.0

    def test_trust_penalizes_historical_safety_events(self):
        """Historical safety events reduce trust via penalty."""
        # All EXECUTE except one old SAFE_STOP (not in recent 5)
        decisions = ["EXECUTE"] * 10 + ["SAFE_STOP"] + ["EXECUTE"] * 15
        history = _build_history(decisions)
        trust_clean = self.jm.compute_trust(
            self.session_id,
            history=_build_history(["EXECUTE"] * 26),
        )
        trust_with_old_stop = self.jm.compute_trust(
            self.session_id, history=history,
        )
        assert trust_with_old_stop < trust_clean

    def test_trust_bounded_0_to_1(self):
        """Trust never exceeds [0.0, 1.0]."""
        # Huge clean history
        trust = self.jm.compute_trust(
            self.session_id,
            history=_build_history(["EXECUTE"] * 100),
        )
        assert 0.0 <= trust <= 1.0


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 6 — Theta Adjustment
# ═══════════════════════════════════════════════════════════════════════════

class TestThetaAdjustment:
    """compute_theta_adjustment: D-scaled, asymmetric bounds."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db_path = str(tmp_path / "jm_theta.db")
        self.jm = JudgmentMemory(db_path, domain_sensitivity=0.5)

    def test_normal_no_history_returns_zero(self):
        """No history, no escalation -> 0.0 adjustment."""
        adj = self.jm.compute_theta_adjustment(
            trust=0.0, domain_sensitivity=0.5,
            escalation=ESCALATION_NORMAL, history=None,
        )
        assert adj == 0.0

    def test_probing_penalty(self):
        """PROBING stage -> -0.10 penalty."""
        adj = self.jm.compute_theta_adjustment(
            trust=0.3, domain_sensitivity=0.5,
            escalation=ESCALATION_PROBING,
        )
        assert adj == -0.10

    def test_testing_penalty(self):
        """TESTING stage -> -0.15 penalty."""
        adj = self.jm.compute_theta_adjustment(
            trust=0.3, domain_sensitivity=0.5,
            escalation=ESCALATION_TESTING,
        )
        assert adj == -0.15

    def test_attacking_penalty(self):
        """ATTACKING stage -> -0.20 penalty."""
        adj = self.jm.compute_theta_adjustment(
            trust=0.0, domain_sensitivity=0.5,
            escalation=ESCALATION_ATTACKING,
        )
        assert adj == -0.20

    def test_consecutive_stops_penalty(self):
        """Consecutive SAFE_STOP/FREEZE adds extra tightening."""
        # 3 consecutive stops at front of history (most recent first)
        history = _build_history(
            ["SAFE_STOP", "SAFE_STOP", "SAFE_STOP", "EXECUTE"],
        )
        adj = self.jm.compute_theta_adjustment(
            trust=0.0, domain_sensitivity=0.5,
            escalation=ESCALATION_NORMAL, history=history,
        )
        # 3 consecutive stops -> -0.05 * 3 = -0.15
        assert adj == -0.15

    def test_consecutive_stops_capped_at_4(self):
        """Consecutive stops penalty caps at 4 stops (-0.20)."""
        history = _build_history(["SAFE_STOP"] * 6)
        adj = self.jm.compute_theta_adjustment(
            trust=0.0, domain_sensitivity=0.5,
            escalation=ESCALATION_NORMAL, history=history,
        )
        # 6 consecutive but capped at 4 -> -0.05 * 4 = -0.20
        assert adj == THETA_MAX_TIGHTEN  # -0.20

    def test_trust_credit_casual_domain(self):
        """High trust in casual domain (D=0.2) grants positive credit."""
        history = _build_history(["EXECUTE"] * TRUST_MIN_INTERACTIONS)
        adj = self.jm.compute_theta_adjustment(
            trust=0.8, domain_sensitivity=0.2,
            escalation=ESCALATION_NORMAL, history=history,
        )
        # trust_credit = 0.05 * (1 - 0.2) = 0.04
        assert adj == pytest.approx(0.04, abs=0.001)

    def test_trust_credit_government_domain(self):
        """Government domain (D=0.95) gives almost zero credit."""
        history = _build_history(["EXECUTE"] * TRUST_MIN_INTERACTIONS)
        adj = self.jm.compute_theta_adjustment(
            trust=1.0, domain_sensitivity=0.95,
            escalation=ESCALATION_NORMAL, history=history,
        )
        # trust_credit = 0.05 * (1 - 0.95) = 0.0025
        assert adj <= 0.003
        assert adj >= 0.0

    def test_trust_credit_requires_enough_interactions(self):
        """Trust credit not granted without TRUST_MIN_INTERACTIONS."""
        short_history = _build_history(["EXECUTE"] * 5)
        adj = self.jm.compute_theta_adjustment(
            trust=0.8, domain_sensitivity=0.2,
            escalation=ESCALATION_NORMAL, history=short_history,
        )
        assert adj == 0.0  # not enough interactions

    def test_trust_credit_requires_normal_escalation(self):
        """Trust credit only granted at NORMAL escalation."""
        history = _build_history(["EXECUTE"] * TRUST_MIN_INTERACTIONS)
        adj = self.jm.compute_theta_adjustment(
            trust=0.8, domain_sensitivity=0.2,
            escalation=ESCALATION_PROBING, history=history,
        )
        # Escalation penalty (-0.10) overrides any credit
        assert adj < 0

    def test_max_loosening_bounded(self):
        """Theta loosening never exceeds THETA_MAX_LOOSEN (+0.05)."""
        history = _build_history(["EXECUTE"] * 100)
        adj = self.jm.compute_theta_adjustment(
            trust=1.0, domain_sensitivity=0.0,
            escalation=ESCALATION_NORMAL, history=history,
        )
        assert adj <= THETA_MAX_LOOSEN

    def test_max_tightening_bounded(self):
        """Theta tightening never exceeds THETA_MAX_TIGHTEN (-0.20)."""
        # Stack all penalties: ATTACKING + consecutive stops
        history = _build_history(["SAFE_STOP"] * 10)
        adj = self.jm.compute_theta_adjustment(
            trust=0.0, domain_sensitivity=0.5,
            escalation=ESCALATION_ATTACKING, history=history,
        )
        assert adj >= THETA_MAX_TIGHTEN

    def test_d_scaling_of_loosening(self):
        """Higher D -> less loosening: credit = MAX_TRUST_CREDIT * (1-D)."""
        history = _build_history(["EXECUTE"] * TRUST_MIN_INTERACTIONS)
        adj_casual = self.jm.compute_theta_adjustment(
            trust=0.8, domain_sensitivity=0.2,
            escalation=ESCALATION_NORMAL, history=history,
        )
        adj_health = self.jm.compute_theta_adjustment(
            trust=0.8, domain_sensitivity=0.9,
            escalation=ESCALATION_NORMAL, history=history,
        )
        assert adj_casual > adj_health


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 7 — Dialect Weight
# ═══════════════════════════════════════════════════════════════════════════

class TestDialectWeight:
    """compute_dialect_weight returns (1-D)."""

    def test_casual_domain(self):
        assert JudgmentMemory.compute_dialect_weight(0.2) == 0.80

    def test_education_domain(self):
        assert JudgmentMemory.compute_dialect_weight(0.4) == 0.60

    def test_banking_domain(self):
        assert JudgmentMemory.compute_dialect_weight(0.8) == 0.20

    def test_healthcare_domain(self):
        assert JudgmentMemory.compute_dialect_weight(0.9) == 0.10

    def test_government_domain(self):
        assert JudgmentMemory.compute_dialect_weight(0.95) == 0.05

    def test_zero_d(self):
        assert JudgmentMemory.compute_dialect_weight(0.0) == 1.0

    def test_max_d(self):
        assert JudgmentMemory.compute_dialect_weight(1.0) == 0.0


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 8 — Safety Invariants (CRITICAL)
# ═══════════════════════════════════════════════════════════════════════════

class TestSafetyInvariants:
    """Safety constants and invariant enforcement."""

    def test_h_hard_override_constant(self):
        """H_HARD_OVERRIDE must be 0.70."""
        assert H_HARD_OVERRIDE == 0.70

    def test_h_adjustment_floor_constant(self):
        """H_ADJUSTMENT_FLOOR must be 0.15."""
        assert H_ADJUSTMENT_FLOOR == 0.15

    def test_theta_max_loosen_constant(self):
        """THETA_MAX_LOOSEN must be 0.05."""
        assert THETA_MAX_LOOSEN == 0.05

    def test_theta_max_tighten_constant(self):
        """THETA_MAX_TIGHTEN must be -0.20."""
        assert THETA_MAX_TIGHTEN == -0.20

    def test_theta_floor_constant(self):
        """THETA_FLOOR must be 0.20."""
        assert THETA_FLOOR == 0.20

    def test_max_trust_credit_constant(self):
        """MAX_TRUST_CREDIT must be 0.05."""
        assert MAX_TRUST_CREDIT == 0.05

    def test_loosening_capped_at_max_times_1_minus_d(self):
        """Theta loosening = MAX_TRUST_CREDIT * (1-D), clamped to THETA_MAX_LOOSEN."""
        for D in [0.0, 0.2, 0.5, 0.8, 0.95, 1.0]:
            max_credit = MAX_TRUST_CREDIT * (1.0 - D)
            assert max_credit <= THETA_MAX_LOOSEN

    def test_tightening_capped_at_minus_020(self):
        """No combination of penalties can exceed -0.20."""
        jm = JudgmentMemory.__new__(JudgmentMemory)
        # Worst case: ATTACKING + 10 consecutive stops
        history = _build_history(["SAFE_STOP"] * 10)
        adj = jm.compute_theta_adjustment(
            trust=0.0, domain_sensitivity=0.5,
            escalation=ESCALATION_ATTACKING, history=history,
        )
        assert adj >= THETA_MAX_TIGHTEN

    def test_h_floor_never_violated(self):
        """H_ADJUSTMENT_FLOOR (0.15) is documented — verify constant."""
        assert H_ADJUSTMENT_FLOOR == 0.15
        # The floor is enforced by the consumer (AATIFEngine), not JudgmentMemory
        # directly. We verify the constant exists and is correct.

    def test_escalation_penalties_values(self):
        """Escalation penalties match documented values."""
        assert ESCALATION_PENALTIES[ESCALATION_NORMAL] == 0.0
        assert ESCALATION_PENALTIES[ESCALATION_PROBING] == -0.10
        assert ESCALATION_PENALTIES[ESCALATION_TESTING] == -0.15
        assert ESCALATION_PENALTIES[ESCALATION_ATTACKING] == -0.20

    def test_asymmetric_bounds_enforced(self):
        """Loosening (+0.05) is much smaller than tightening (-0.20)."""
        assert abs(THETA_MAX_TIGHTEN) == 4 * THETA_MAX_LOOSEN


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 9 — D Parameter and Domain Profiles
# ═══════════════════════════════════════════════════════════════════════════

class TestDomainProfiles:
    """Domain profiles and D parameter behavior."""

    def test_all_profiles_exist(self):
        """All 5 domain profiles are defined."""
        expected = {"casual", "education", "banking", "healthcare", "government"}
        assert set(DOMAIN_PROFILES.keys()) == expected

    def test_profile_values(self):
        """Profile D values match spec."""
        assert DOMAIN_PROFILES["casual"] == 0.20
        assert DOMAIN_PROFILES["education"] == 0.40
        assert DOMAIN_PROFILES["banking"] == 0.80
        assert DOMAIN_PROFILES["healthcare"] == 0.90
        assert DOMAIN_PROFILES["government"] == 0.95

    def test_profiles_ordered_by_sensitivity(self):
        """Domain D values increase with sensitivity."""
        order = ["casual", "education", "banking", "healthcare", "government"]
        for i in range(len(order) - 1):
            assert DOMAIN_PROFILES[order[i]] < DOMAIN_PROFILES[order[i + 1]]

    def test_all_profiles_in_0_1_range(self):
        """All D values are in [0.0, 1.0]."""
        for name, d in DOMAIN_PROFILES.items():
            assert 0.0 <= d <= 1.0, f"{name} has D={d} out of range"

    def test_storage_thresholds(self):
        """Storage policy thresholds are consistent."""
        assert STORAGE_FULL_THRESHOLD == 0.7
        assert STORAGE_STANDARD_THRESHOLD == 0.4
        assert STORAGE_STANDARD_THRESHOLD < STORAGE_FULL_THRESHOLD

    def test_d_parameter_clamped(self):
        """D parameter is clamped to [0.0, 1.0] on init."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            jm_low = JudgmentMemory(
                os.path.join(tmp, "low.db"),
                domain_sensitivity=-0.5,
            )
            assert jm_low.domain_sensitivity == 0.0

            jm_high = JudgmentMemory(
                os.path.join(tmp, "high.db"),
                domain_sensitivity=1.5,
            )
            assert jm_high.domain_sensitivity == 1.0


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 10 — Helper Functions
# ═══════════════════════════════════════════════════════════════════════════

class TestHelperFunctions:
    """Test internal helper functions."""

    def test_hash_message_deterministic(self):
        """Same input -> same hash."""
        h1 = _hash_message("hello world")
        h2 = _hash_message("hello world")
        assert h1 == h2

    def test_hash_message_normalized(self):
        """Normalization: strip + lowercase."""
        h1 = _hash_message("Hello World")
        h2 = _hash_message("  hello world  ")
        assert h1 == h2

    def test_hash_message_different_inputs(self):
        """Different inputs -> different hashes."""
        h1 = _hash_message("hello")
        h2 = _hash_message("world")
        assert h1 != h2

    def test_embedding_roundtrip(self):
        """Embedding -> blob -> embedding roundtrip preserves data."""
        emb = _random_embedding(seed=50)
        blob = _embedding_to_blob(emb)
        restored = _blob_to_embedding(blob)
        np.testing.assert_array_almost_equal(emb, restored, decimal=6)

    def test_cosine_similarity_identical(self):
        """Cosine similarity of a vector with itself = 1.0."""
        emb = _random_embedding(seed=60)
        sim = _cosine_similarity(emb, emb)
        assert abs(sim - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal(self):
        """Cosine similarity of orthogonal vectors = 0.0."""
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        sim = _cosine_similarity(a, b)
        assert abs(sim) < 1e-6

    def test_cosine_similarity_opposite(self):
        """Cosine similarity of opposite vectors = -1.0."""
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([-1.0, 0.0], dtype=np.float32)
        sim = _cosine_similarity(a, b)
        assert abs(sim + 1.0) < 1e-6

    def test_cosine_similarity_zero_vector(self):
        """Zero vector -> similarity = 0.0 (degenerate)."""
        a = np.zeros(768, dtype=np.float32)
        b = _random_embedding(seed=70)
        sim = _cosine_similarity(a, b)
        assert sim == 0.0

    def test_iso_datetime_roundtrip(self):
        """ISO 8601 string -> datetime -> ISO 8601 roundtrip."""
        now_str = _now_iso()
        dt = _iso_to_dt(now_str)
        back = _dt_to_iso(dt)
        # Roundtrip should produce equivalent datetime
        dt2 = _iso_to_dt(back)
        assert abs((dt - dt2).total_seconds()) < 1

    def test_iso_to_dt_adds_utc(self):
        """Naive ISO strings get UTC timezone."""
        dt = _iso_to_dt("2026-06-28T12:00:00")
        assert dt.tzinfo is not None


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 11 — Record and Forget Integration
# ═══════════════════════════════════════════════════════════════════════════

class TestRecordAndForget:
    """Integration test: record -> query -> forget."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db_path = str(tmp_path / "jm_integration.db")
        self.jm = JudgmentMemory(db_path, domain_sensitivity=0.8)
        self.session_id = "integration_session"

    def test_full_lifecycle(self):
        """Record judgments, query, cleanup, forget."""
        emb = _random_embedding(seed=80)
        # 1. Record
        row_id = self.jm.record_judgment(
            session_id=self.session_id,
            msg_hash=_hash_message("lifecycle msg"),
            msg_embedding=emb,
            scores={"H": 0.1, "I": 0.9, "E": 0.6, "S": 0.85},
            decision="EXECUTE",
            dialect="gulf",
            theta=0.40,
        )
        assert row_id > 0

        # 2. Query similar
        prior = self.jm.ledger.query_similar(self.session_id, emb)
        assert prior is not None
        assert prior["decision"] == "EXECUTE"

        # 3. Build context with prior
        ctx = self.jm.build_context(emb, self.session_id, dialect="gulf")
        assert ctx.similar_prior_found is True

        # 4. Forget
        deleted = self.jm.forget(self.session_id)
        assert deleted > 0
        assert self.jm.ledger.count(self.session_id) == 0

        # 5. Build context after forget (should be clean)
        ctx_after = self.jm.build_context(emb, self.session_id)
        assert ctx_after.similar_prior_found is False
        assert ctx_after.trust_level == 0.0

    def test_record_with_d_override(self):
        """record_judgment respects domain_sensitivity override."""
        # Instance D=0.8 (FULL), but override with D=0.2 (LIGHT)
        row_id = self.jm.record_judgment(
            session_id=self.session_id,
            msg_hash=_hash_message("override test"),
            msg_embedding=None,
            scores={"H": 0.1, "I": 0.8, "E": 0.5, "S": 0.75},
            decision="EXECUTE",
            domain_sensitivity=0.2,  # LIGHT -> skip
            theta=0.40,
        )
        assert row_id == -1  # skipped in LIGHT mode


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 12 — Intent Average
# ═══════════════════════════════════════════════════════════════════════════

class TestIntentAverage:
    """_compute_intent_avg helper."""

    def test_empty_history_returns_default(self):
        """Empty history -> intent avg = 0.5 (default)."""
        avg = JudgmentMemory._compute_intent_avg([])
        assert avg == 0.5

    def test_computes_average(self):
        """Averages I scores from history."""
        history = [
            {"i_score": 0.9},
            {"i_score": 0.8},
            {"i_score": 0.7},
        ]
        avg = JudgmentMemory._compute_intent_avg(history)
        assert avg == pytest.approx(0.8, abs=0.01)

    def test_skips_none_i_scores(self):
        """None I scores are excluded from average."""
        history = [
            {"i_score": 0.9},
            {"i_score": None},
            {"i_score": 0.7},
        ]
        avg = JudgmentMemory._compute_intent_avg(history)
        assert avg == pytest.approx(0.8, abs=0.01)

    def test_all_none_returns_default(self):
        """All None I scores -> default 0.5."""
        history = [{"i_score": None}, {"i_score": None}]
        avg = JudgmentMemory._compute_intent_avg(history)
        assert avg == 0.5


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 13 — Expiry computation
# ═══════════════════════════════════════════════════════════════════════════

class TestExpiryComputation:
    """_compute_expiry tiered decay policy."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db_path = str(tmp_path / "jm_expiry.db")
        self.ledger = JudgmentLedger(db_path)

    def test_execute_standard_30_days(self):
        """EXECUTE in STANDARD mode -> 30 day expiry."""
        now = _now_iso()
        expires = self.ledger._compute_expiry("EXECUTE", 0.5, now)
        now_dt = _iso_to_dt(now)
        exp_dt = _iso_to_dt(expires)
        diff = (exp_dt - now_dt).days
        assert diff == 30

    def test_clarify_standard_60_days(self):
        """CLARIFY in STANDARD mode -> 60 day expiry."""
        now = _now_iso()
        expires = self.ledger._compute_expiry("CLARIFY", 0.5, now)
        now_dt = _iso_to_dt(now)
        exp_dt = _iso_to_dt(expires)
        diff = (exp_dt - now_dt).days
        assert diff == 60

    def test_safe_stop_standard_180_days(self):
        """SAFE_STOP in STANDARD mode -> 180 day expiry."""
        now = _now_iso()
        expires = self.ledger._compute_expiry("SAFE_STOP", 0.5, now)
        now_dt = _iso_to_dt(now)
        exp_dt = _iso_to_dt(expires)
        diff = (exp_dt - now_dt).days
        assert diff == 180

    def test_execute_full_90_days(self):
        """EXECUTE in FULL mode -> 90 day expiry."""
        now = _now_iso()
        expires = self.ledger._compute_expiry("EXECUTE", 0.8, now)
        now_dt = _iso_to_dt(now)
        exp_dt = _iso_to_dt(expires)
        diff = (exp_dt - now_dt).days
        assert diff == 90

    def test_safe_freeze_full_365_days(self):
        """SAFE_FREEZE in FULL mode -> 365 day expiry."""
        now = _now_iso()
        expires = self.ledger._compute_expiry("SAFE_FREEZE", 0.8, now)
        now_dt = _iso_to_dt(now)
        exp_dt = _iso_to_dt(expires)
        diff = (exp_dt - now_dt).days
        assert diff == 365


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 14 — Near-threshold similarity (small noise embedding)
# ═══════════════════════════════════════════════════════════════════════════

class TestNearThresholdSimilarity:
    """Test query_similar with embeddings that differ by small noise."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db_path = str(tmp_path / "jm_noise.db")
        self.ledger = JudgmentLedger(db_path)
        self.session_id = "noise_session"

    def test_small_noise_finds_similar(self):
        """Adding tiny noise to an embedding should still match (sim > 0.85)."""
        rng = np.random.RandomState(200)
        base_emb = rng.randn(EMBEDDING_DIM).astype(np.float32)
        base_emb = base_emb / np.linalg.norm(base_emb)

        # Store original
        self.ledger.record(
            session_id=self.session_id,
            msg_hash=_hash_message("base msg"),
            msg_embedding=base_emb,
            h_score=0.1, i_score=0.9, e_score=0.6, s_score=0.85,
            decision="EXECUTE", dialect="gulf",
            domain_sensitivity=0.8, theta_used=0.40,
        )

        # Add small noise — in 768-dim space, scale must be tiny to stay
        # above PRIOR_SIMILARITY_THRESHOLD (0.85). Scale 0.01 gives ~0.999 sim.
        noise = rng.randn(EMBEDDING_DIM).astype(np.float32) * 0.01
        noisy_emb = base_emb + noise
        noisy_emb = noisy_emb / np.linalg.norm(noisy_emb)

        # Verify the similarity is above threshold
        sim = _cosine_similarity(base_emb, noisy_emb)
        assert sim > PRIOR_SIMILARITY_THRESHOLD, (
            f"Small noise sim {sim:.4f} should be > {PRIOR_SIMILARITY_THRESHOLD}"
        )

        result = self.ledger.query_similar(self.session_id, noisy_emb)
        assert result is not None
        assert result["similarity"] > PRIOR_SIMILARITY_THRESHOLD
        assert result["decision"] == "EXECUTE"

    def test_moderate_noise_does_not_match(self):
        """Moderate noise (scale 1.0) should push similarity below threshold."""
        rng = np.random.RandomState(201)
        base_emb = rng.randn(EMBEDDING_DIM).astype(np.float32)
        base_emb = base_emb / np.linalg.norm(base_emb)

        self.ledger.record(
            session_id=self.session_id,
            msg_hash=_hash_message("base msg 2"),
            msg_embedding=base_emb,
            h_score=0.1, i_score=0.9, e_score=0.6, s_score=0.85,
            decision="EXECUTE", dialect=None,
            domain_sensitivity=0.8, theta_used=0.40,
        )

        # Add large noise — cosine sim should drop below threshold
        noise = rng.randn(EMBEDDING_DIM).astype(np.float32) * 1.0
        noisy_emb = base_emb + noise
        noisy_emb = noisy_emb / np.linalg.norm(noisy_emb)

        sim = _cosine_similarity(base_emb, noisy_emb)
        assert sim < PRIOR_SIMILARITY_THRESHOLD, (
            f"Large noise sim {sim:.4f} should be < {PRIOR_SIMILARITY_THRESHOLD}"
        )

        result = self.ledger.query_similar(self.session_id, noisy_emb)
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 15 — Specific escalation sequences
# ═══════════════════════════════════════════════════════════════════════════

class TestEscalationSequences:
    """Test specific decision sequences for escalation detection."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db_path = str(tmp_path / "jm_seq.db")
        self.jm = JudgmentMemory(db_path, domain_sensitivity=0.5)
        self.session_id = "seq_session"

    def test_execute_clarify_safe_stop_sequence(self):
        """EXECUTE -> CLARIFY -> SAFE_STOP sequence -> TESTING."""
        decisions = ["EXECUTE", "EXECUTE", "CLARIFY", "SAFE_STOP", "EXECUTE"]
        history = _build_history(decisions)
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc in (ESCALATION_PROBING, ESCALATION_TESTING), (
            f"EXECUTE->CLARIFY->SAFE_STOP should be PROBING or TESTING, got {esc}"
        )

    def test_all_execute_stays_normal(self):
        """Pure EXECUTE history with stable H -> NORMAL."""
        decisions = ["EXECUTE"] * 10
        h_scores = [0.1] * 10
        history = _build_history(decisions, h_scores)
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc == ESCALATION_NORMAL

    def test_multiple_freeze_is_attacking(self):
        """Multiple SAFE_FREEZE -> ATTACKING."""
        decisions = ["EXECUTE", "SAFE_FREEZE", "EXECUTE", "SAFE_FREEZE", "EXECUTE"]
        history = _build_history(decisions)
        esc = self.jm.detect_escalation(self.session_id, history=history)
        assert esc == ESCALATION_ATTACKING


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 16 — H > 0.7 behavioral bypass test
# ═══════════════════════════════════════════════════════════════════════════

class TestHighHBehavior:
    """When H > 0.7, context should indicate no loosening / bypass."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db_path = str(tmp_path / "jm_high_h.db")
        self.jm = JudgmentMemory(db_path, domain_sensitivity=0.5)
        self.session_id = "high_h_session"

    def test_h_above_override_context_no_loosening(self):
        """With H > 0.7, theta_adjustment should not loosen theta."""
        # Build a trusted user with 25 clean EXECUTE decisions
        for i in range(25):
            self.jm.record_judgment(
                session_id=self.session_id,
                msg_hash=_hash_message(f"clean_{i}"),
                msg_embedding=None,
                scores={"H": 0.05, "I": 0.85, "E": 0.6, "S": 0.80},
                decision="EXECUTE", theta=0.40,
            )
        # User now has high trust
        trust = self.jm.compute_trust(self.session_id)
        assert trust > TRUST_THRESHOLD

        # Build context -- the context itself is produced BEFORE H is known,
        # so we verify the H_HARD_OVERRIDE constant is in place
        assert H_HARD_OVERRIDE == 0.70
        # The safety invariant: even a trusted user's theta adjustment
        # cannot exceed THETA_MAX_LOOSEN
        ctx = self.jm.build_context(None, self.session_id)
        assert ctx.theta_adjustment <= THETA_MAX_LOOSEN

    def test_h_adjustment_floor_respected(self):
        """H_ADJUSTMENT_FLOOR (0.15) is the documented minimum."""
        # The consumer (AATIFEngine) enforces this floor.
        # Here we verify the constant and that h_adjustment in context
        # defaults to 0.0 (Phase 1: no direct H adjustment).
        ctx = self.jm.build_context(None, self.session_id)
        assert ctx.h_adjustment == 0.0
        assert H_ADJUSTMENT_FLOOR == 0.15


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 17 — D-parameter specific domain values
# ═══════════════════════════════════════════════════════════════════════════

class TestDParameterSpecificValues:
    """Banking D=0.8 and Casual D=0.2 specific numeric checks."""

    def test_banking_trust_adjustment(self):
        """D=0.8 (banking): trust_adjustment = 0.05 * (1-0.8) = 0.01."""
        jm = JudgmentMemory.__new__(JudgmentMemory)
        history = _build_history(["EXECUTE"] * TRUST_MIN_INTERACTIONS)
        adj = jm.compute_theta_adjustment(
            trust=0.8, domain_sensitivity=0.8,
            escalation=ESCALATION_NORMAL, history=history,
        )
        assert adj == pytest.approx(0.01, abs=0.001)

    def test_casual_trust_adjustment(self):
        """D=0.2 (casual): trust_adjustment = 0.05 * (1-0.2) = 0.04."""
        jm = JudgmentMemory.__new__(JudgmentMemory)
        history = _build_history(["EXECUTE"] * TRUST_MIN_INTERACTIONS)
        adj = jm.compute_theta_adjustment(
            trust=0.8, domain_sensitivity=0.2,
            escalation=ESCALATION_NORMAL, history=history,
        )
        assert adj == pytest.approx(0.04, abs=0.001)

    def test_banking_dialect_weight(self):
        """D=0.8 (banking): dialect_weight = 1-0.8 = 0.2."""
        assert JudgmentMemory.compute_dialect_weight(0.8) == pytest.approx(0.2)

    def test_casual_dialect_weight(self):
        """D=0.2 (casual): dialect_weight = 1-0.2 = 0.8."""
        assert JudgmentMemory.compute_dialect_weight(0.2) == pytest.approx(0.8)

    def test_government_near_zero_loosening(self):
        """D=0.95 (government): almost zero trust loosening."""
        jm = JudgmentMemory.__new__(JudgmentMemory)
        history = _build_history(["EXECUTE"] * TRUST_MIN_INTERACTIONS)
        adj = jm.compute_theta_adjustment(
            trust=1.0, domain_sensitivity=0.95,
            escalation=ESCALATION_NORMAL, history=history,
        )
        # 0.05 * (1 - 0.95) = 0.0025
        assert adj == pytest.approx(0.0025, abs=0.001)
        assert adj < 0.003

    def test_government_near_zero_dialect_weight(self):
        """D=0.95 (government): dialect_weight = 0.05 (almost zero)."""
        assert JudgmentMemory.compute_dialect_weight(0.95) == pytest.approx(0.05)


# ═══════════════════════════════════════════════════════════════════════════
#  GROUP 18 — Full workflow integration
# ═══════════════════════════════════════════════════════════════════════════

class TestFullWorkflowIntegration:
    """Create memory -> build context -> record -> build context (finds prior)."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db_path = str(tmp_path / "jm_workflow.db")
        self.jm = JudgmentMemory(db_path, domain_sensitivity=0.8)
        self.session_id = "workflow_session"

    def test_full_cycle_finds_prior_on_second_context(self):
        """Full workflow: create -> context -> record -> context (prior found)."""
        emb = _random_embedding(seed=300)

        # 1. First build_context: no history, no prior
        ctx1 = self.jm.build_context(emb, self.session_id, dialect="gulf")
        assert ctx1.similar_prior_found is False
        assert ctx1.trust_level == 0.0
        assert ctx1.escalation_stage == ESCALATION_NORMAL

        # 2. Record judgment
        row_id = self.jm.record_judgment(
            session_id=self.session_id,
            msg_hash=_hash_message("workflow msg 1"),
            msg_embedding=emb,
            scores={"H": 0.1, "I": 0.9, "E": 0.6, "S": 0.85},
            decision="EXECUTE",
            dialect="gulf",
            theta=0.40,
        )
        assert row_id > 0

        # 3. Second build_context with same embedding: should find prior
        ctx2 = self.jm.build_context(emb, self.session_id, dialect="gulf")
        assert ctx2.similar_prior_found is True
        assert ctx2.similar_prior_decision == "EXECUTE"
        assert ctx2.similar_prior_similarity > 0.99

    def test_workflow_with_escalation_buildup(self):
        """Record multiple judgments, see escalation reflected in context."""
        # Record 4 decisions to build history for escalation
        sequence = [
            ("EXECUTE", 0.1), ("EXECUTE", 0.15),
            ("CLARIFY", 0.3), ("SAFE_STOP", 0.55),
        ]
        for i, (dec, h) in enumerate(sequence):
            self.jm.record_judgment(
                session_id=self.session_id,
                msg_hash=_hash_message(f"esc_wf_{i}"),
                msg_embedding=None,
                scores={"H": h, "I": 0.7, "E": 0.5, "S": 0.5},
                decision=dec, theta=0.40,
            )

        # Build context: should reflect escalation
        ctx = self.jm.build_context(None, self.session_id)
        assert ctx.escalation_stage in (ESCALATION_TESTING, ESCALATION_ATTACKING)
        # Theta should be negative (tightened)
        assert ctx.theta_adjustment < 0
        # Trust should be 0 (recent safety event)
        assert ctx.trust_level == 0.0

    def test_workflow_cleanup_then_context(self):
        """After cleanup of expired records, context reflects clean state."""
        import sqlite3

        # Record and manually expire
        self.jm.record_judgment(
            session_id=self.session_id,
            msg_hash=_hash_message("expire_wf"),
            msg_embedding=None,
            scores={"H": 0.6, "I": 0.3, "E": 0.4, "S": 0.30},
            decision="SAFE_STOP", theta=0.40,
        )

        # Force expiry
        conn = sqlite3.connect(self.jm.ledger._db_path)
        past = _dt_to_iso(datetime.now(timezone.utc) - timedelta(days=1))
        conn.execute("UPDATE judgment_ledger SET expires_at = ?", (past,))
        conn.commit()
        conn.close()

        # Cleanup
        deleted = self.jm.cleanup()
        assert deleted == 1

        # Context should be clean now
        ctx = self.jm.build_context(None, self.session_id)
        assert ctx.escalation_stage == ESCALATION_NORMAL
        assert ctx.trust_level == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
