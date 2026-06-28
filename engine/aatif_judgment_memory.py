#!/usr/bin/env python3
"""
AATIF Judgment Memory — ذاكرة الحُكم
======================================

The THIRD LAYER of عاطف's understanding triad:

    TemporalMemory = الحقائق  (facts — what happened when)
    Fingerprint    = النمط    (patterns — who this person is)
    JudgmentMemory = الحُكم   (judgment — how to weigh what they say)

Philosophy — ميزان مش فهرس:

    This is NOT a retrieval index (فهرس). It is a judgment support
    system (ميزان / scale) that INFORMS the S equation.

    Same tools (cosine similarity, embeddings) as MemPalace, but
    different purpose:
      MemPalace:       "find me memories similar to X" → retrieval
      JudgmentMemory:  "given what I know about this user,
                        adjust my judgment of X" → governance

    The approach is تربية (nurturing / tarbiyah) not تعليم (teaching):
      - Memory helps AATIF build contextual judgment over time
      - It does NOT override safety — it INFORMS the equation
      - Like a parent who knows their child: not less cautious,
        but more accurate

    Key constraint: Judgment Memory NEVER overrides the hard floor.
    If H > 0.7, the hard override to SAFE_FREEZE stays absolute.
    "الاذي مالوش توقيت" — and it has no user history either
    at the extreme.

Safety invariants (NEVER violated regardless of user history):

    1. H > 0.7 hard override is absolute.
       No dialect prior, no intent history, no trust level can prevent
       SAFE_FREEZE when H exceeds the hard threshold.

    2. H_adj floor is 0.15.
       Even for a user with perfect history, adjusted H cannot go
       below 0.15. The system always maintains minimum caution.

    3. Theta can only rise by 0.05 maximum.
       Memory can tighten theta by up to 0.20 but can loosen it by
       at most 0.05. Asymmetric by design.

    4. CBRN and jailbreak detection bypass JudgmentMemory entirely.
       The regex layers (Law Omega, Law Xi) override any equation-level
       decision. Judgment Memory cannot soften a CBRN match.

    5. No raw text storage.
       Only hashes and embeddings. Embeddings cannot be reversed.

    6. Judgment Memory INFORMS, never OVERRIDES.
       It adjusts inputs to the equation. It does not change the
       decision after the equation produces it. Sovereignty holds.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np


# ═══════════════════════════════════════════════════════════
#  Constants — Safety Invariants (ثوابت الأمان)
# ═══════════════════════════════════════════════════════════

# Hard override: if H > this, bypass memory entirely.
# "الاذي مالوش توقيت" — at the extreme, history is irrelevant.
H_HARD_OVERRIDE = 0.70

# Floor: adjusted H can NEVER go below this.
# "I don't know" is not "safe".
H_ADJUSTMENT_FLOOR = 0.15

# Theta adjustment bounds — asymmetric by design.
# Trust is earned slowly, lost quickly.
THETA_MAX_LOOSEN = 0.05    # memory can loosen theta by at most +0.05
THETA_MAX_TIGHTEN = -0.20  # memory can tighten theta by up to -0.20
THETA_FLOOR = 0.20         # absolute minimum theta (same as Dynamic Theta)

# Maximum trust credit (before D scaling).
# This is the ONE case where memory makes theta more lenient.
MAX_TRUST_CREDIT = 0.05

# Escalation detection window — last N decisions to analyze.
ESCALATION_WINDOW = 10

# Prior judgment lookup — similarity threshold.
PRIOR_SIMILARITY_THRESHOLD = 0.85

# Prior judgment lookup — max age for prior to be considered.
PRIOR_MAX_AGE_HOURS = 168  # 7 days

# Maximum embeddings to scan for prior lookup (per-user).
# At 768-dim, 50 cosine similarities = microseconds.
MAX_PRIOR_SCAN = 50

# Trust computation thresholds.
TRUST_MIN_INTERACTIONS = 20  # need this many interactions for trust credit
TRUST_THRESHOLD = 0.5        # trust_level must exceed this for credit

# Embedding dimensionality (bge-m3).
EMBEDDING_DIM = 768


# ═══════════════════════════════════════════════════════════
#  Domain Profiles — D parameter (حساسية الدومين)
# ═══════════════════════════════════════════════════════════
#
# D is a scalar (0-1) capturing deployment domain sensitivity.
# Like theta, D is a CONFIG parameter — set at deployment time,
# requires no fine-tuning or model training.
#
# D is the gravitational constant of the domain (الذكازمكان):
#   G (gravitational constant) -> D (domain sensitivity)
#   The SAME word has the same mass everywhere. But in healthcare
#   (D=0.9), that mass produces MORE curvature than in casual
#   chat (D=0.2). The word didn't change. The space changed.
#
# "الدومين يقرر — مش قاعدة واحدة للكل."

DOMAIN_PROFILES: Dict[str, float] = {
    "casual": 0.20,       # Low stakes — flexible, dialect-aware, light storage
    "education": 0.40,    # Moderate — allow exploration, standard storage
    "banking": 0.80,      # High stakes — strict, minimal dialect adjustment
    "healthcare": 0.90,   # Critical — near-maximum caution
    "government": 0.95,   # Maximum — almost zero flexibility
}

# Storage depth policies (controlled by D).
#   D > 0.7  -> FULL: store embeddings + all judgments (audit trail)
#   D > 0.4  -> STANDARD: store judgments with tiered decay
#   D <= 0.4 -> LIGHT: only safety-relevant events stored
STORAGE_FULL_THRESHOLD = 0.7
STORAGE_STANDARD_THRESHOLD = 0.4

# Decay policies — how long judgments live (in days).
# STANDARD policy decay tiers:
DECAY_EXECUTE_STANDARD = 30
DECAY_CLARIFY_STANDARD = 60
DECAY_SAFETY_STANDARD = 180  # SAFE_STOP / SAFE_FREEZE

# FULL policy decay tiers (D > 0.7 — audit trail):
DECAY_EXECUTE_FULL = 90
DECAY_CLARIFY_FULL = 180
DECAY_SAFETY_FULL = 365


# ═══════════════════════════════════════════════════════════
#  Escalation stages (مراحل التصعيد)
# ═══════════════════════════════════════════════════════════

ESCALATION_NORMAL = "NORMAL"       # All recent decisions EXECUTE
ESCALATION_PROBING = "PROBING"     # H scores creeping up, intent still ok
ESCALATION_TESTING = "TESTING"     # Triggered CLARIFY/STOP, now avoiding
ESCALATION_ATTACKING = "ATTACKING" # 2+ SAFE_STOP/FREEZE, persistent probing

# Theta penalties per escalation stage.
ESCALATION_PENALTIES = {
    ESCALATION_NORMAL: 0.0,
    ESCALATION_PROBING: -0.10,
    ESCALATION_TESTING: -0.15,
    ESCALATION_ATTACKING: -0.20,
}


# ═══════════════════════════════════════════════════════════
#  Helper: datetime <-> ISO 8601
# ═══════════════════════════════════════════════════════════

def _now_iso() -> str:
    """Current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _iso_to_dt(s: str) -> datetime:
    """Parse ISO 8601 string to datetime."""
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _dt_to_iso(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _hash_message(text: str) -> str:
    """SHA-256 hash of normalized text. No raw text stored."""
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _embedding_to_blob(embedding: np.ndarray) -> bytes:
    """Convert numpy float32 array to bytes for SQLite BLOB storage."""
    return embedding.astype(np.float32).tobytes()


def _blob_to_embedding(blob: bytes) -> np.ndarray:
    """Convert SQLite BLOB back to numpy float32 array."""
    return np.frombuffer(blob, dtype=np.float32).copy()


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors. Returns 0.0 on degenerate input."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ═══════════════════════════════════════════════════════════
#  JudgmentContext — produced BEFORE S equation runs
# ═══════════════════════════════════════════════════════════

@dataclass
class JudgmentContext:
    """Context that informs (not overrides) the S equation.

    Produced by JudgmentMemory.build_context() and consumed by
    AATIFEngine.compute(). Adjusts inputs to the equation, never
    changes the decision after the equation produces it.
    """

    # ── Dialect Prior ──
    dialect_profile: Optional[str] = None  # "gulf", "egyptian", "levantine", etc.

    # ── Intent Prior ──
    historical_intent_avg: float = 0.5  # running average of past I scores

    # ── Escalation Signal ──
    escalation_stage: str = ESCALATION_NORMAL

    # ── Theta Adjustment ──
    theta_adjustment: float = 0.0  # negative = stricter, positive = lenient

    # ── H Adjustment ──
    h_adjustment: float = 0.0  # multiplicative factor applied to H

    # ── Prior Judgment Cache ──
    similar_prior_found: bool = False
    similar_prior_decision: Optional[str] = None
    similar_prior_similarity: float = 0.0
    similar_prior_age_hours: float = 0.0

    # ── Trust Signal ──
    trust_level: float = 0.0  # 0.0-1.0

    # ── Domain Sensitivity ──
    domain_sensitivity: float = 0.2  # D parameter (0.0-1.0)

    # ── Notes ──
    context_notes: str = ""


# ═══════════════════════════════════════════════════════════
#  SQL Schema — judgment_ledger
# ═══════════════════════════════════════════════════════════

_CREATE_LEDGER = """
CREATE TABLE IF NOT EXISTS judgment_ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    msg_hash        TEXT NOT NULL,
    msg_embedding   BLOB,
    h_score         REAL,
    i_score         REAL,
    e_score         REAL,
    s_score         REAL,
    decision        TEXT,
    dialect_detected TEXT,
    domain_sensitivity REAL,
    theta_used      REAL,
    escalation_stage TEXT,
    expires_at      TEXT
);
"""

_CREATE_IDX_SESSION_TIME = """
CREATE INDEX IF NOT EXISTS idx_jl_session_time
ON judgment_ledger(session_id, timestamp);
"""

_CREATE_IDX_SESSION_DECISION = """
CREATE INDEX IF NOT EXISTS idx_jl_session_decision
ON judgment_ledger(session_id, decision);
"""

_CREATE_IDX_HASH = """
CREATE INDEX IF NOT EXISTS idx_jl_hash
ON judgment_ledger(msg_hash);
"""

_CREATE_IDX_EXPIRES = """
CREATE INDEX IF NOT EXISTS idx_jl_expires
ON judgment_ledger(expires_at);
"""


# ═══════════════════════════════════════════════════════════
#  JudgmentLedger — SQLite storage class
# ═══════════════════════════════════════════════════════════

class JudgmentLedger:
    """SQLite-backed storage for judgment records.

    Stores judgments (not raw text) with tiered decay. The ledger
    is the forensic record of what AATIF decided and why.

    Storage depth is controlled by the D parameter:
      D > 0.7 (FULL):     all judgments + embeddings (audit trail)
      D > 0.4 (STANDARD): judgments + decisions (tiered decay)
      D <= 0.4 (LIGHT):   only safety-relevant events
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Create tables and indices if they don't exist."""
        with self._get_conn() as conn:
            conn.execute(_CREATE_LEDGER)
            conn.execute(_CREATE_IDX_SESSION_TIME)
            conn.execute(_CREATE_IDX_SESSION_DECISION)
            conn.execute(_CREATE_IDX_HASH)
            conn.execute(_CREATE_IDX_EXPIRES)
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a new SQLite connection with WAL mode."""
        conn = sqlite3.connect(self._db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def record(
        self,
        session_id: str,
        msg_hash: str,
        msg_embedding: Optional[np.ndarray],
        h_score: float,
        i_score: float,
        e_score: float,
        s_score: float,
        decision: str,
        dialect: Optional[str],
        domain_sensitivity: float,
        theta_used: float,
        escalation_stage: str = ESCALATION_NORMAL,
    ) -> int:
        """Record a judgment in the ledger.

        Args:
            session_id: opaque session/user identifier.
            msg_hash: SHA-256 hash of the message (no raw text).
            msg_embedding: bge-m3 embedding (768-dim) or None.
            h_score: harm score at time of judgment.
            i_score: intent score.
            e_score: emotion score.
            s_score: final S score.
            decision: EXECUTE / CLARIFY / SAFE_STOP / SAFE_FREEZE.
            dialect: detected dialect or None.
            domain_sensitivity: D parameter value used.
            theta_used: effective theta at time of judgment.
            escalation_stage: current escalation stage.

        Returns:
            The row id of the inserted record.
        """
        now = _now_iso()
        expires_at = self._compute_expiry(decision, domain_sensitivity, now)

        # Storage depth: D <= 0.4 (LIGHT) -> only safety events
        if domain_sensitivity <= STORAGE_STANDARD_THRESHOLD:
            if decision not in ("SAFE_STOP", "SAFE_FREEZE"):
                return -1  # skip non-safety events in LIGHT mode

        # Storage depth: D <= 0.7 (STANDARD) -> no embeddings
        embedding_blob = None
        if msg_embedding is not None and domain_sensitivity > STORAGE_FULL_THRESHOLD:
            embedding_blob = _embedding_to_blob(msg_embedding)

        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO judgment_ledger
                    (timestamp, session_id, msg_hash, msg_embedding,
                     h_score, i_score, e_score, s_score,
                     decision, dialect_detected, domain_sensitivity,
                     theta_used, escalation_stage, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        now, session_id, msg_hash, embedding_blob,
                        h_score, i_score, e_score, s_score,
                        decision, dialect, domain_sensitivity,
                        theta_used, escalation_stage, expires_at,
                    ),
                )
                conn.commit()
                return cursor.lastrowid

    def query_similar(
        self,
        session_id: str,
        query_embedding: np.ndarray,
        limit: int = MAX_PRIOR_SCAN,
    ) -> Optional[Dict]:
        """Find the most similar prior judgment for this session.

        Scans the last `limit` embeddings and computes cosine similarity.
        This is NOT a vector database — it is a small per-user scan.

        Args:
            session_id: session/user identifier.
            query_embedding: embedding of the current message.
            limit: max rows to scan.

        Returns:
            Dict with prior judgment info if similarity > threshold,
            or None if no similar prior found.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, timestamp, msg_embedding, h_score, i_score,
                       s_score, decision, dialect_detected
                FROM judgment_ledger
                WHERE session_id = ? AND msg_embedding IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

        if not rows:
            return None

        best_sim = -1.0
        best_row = None
        now = datetime.now(timezone.utc)

        for row in rows:
            row_id, ts_str, emb_blob, h, i, s, dec, dialect = row
            if emb_blob is None:
                continue
            stored_emb = _blob_to_embedding(emb_blob)
            sim = _cosine_similarity(query_embedding, stored_emb)
            if sim > best_sim:
                best_sim = sim
                best_row = row

        if best_row is None or best_sim < PRIOR_SIMILARITY_THRESHOLD:
            return None

        row_id, ts_str, emb_blob, h, i, s, dec, dialect = best_row
        ts_dt = _iso_to_dt(ts_str)
        age_hours = (now - ts_dt).total_seconds() / 3600.0

        if age_hours > PRIOR_MAX_AGE_HOURS:
            return None

        return {
            "id": row_id,
            "similarity": round(best_sim, 4),
            "age_hours": round(age_hours, 2),
            "h_score": h,
            "i_score": i,
            "s_score": s,
            "decision": dec,
            "dialect": dialect,
        }

    def get_session_history(
        self,
        session_id: str,
        limit: int = ESCALATION_WINDOW,
    ) -> List[Dict]:
        """Get recent judgment history for a session.

        Args:
            session_id: session/user identifier.
            limit: max rows to return.

        Returns:
            List of dicts with judgment info, most recent first.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, timestamp, h_score, i_score, s_score,
                       decision, escalation_stage
                FROM judgment_ledger
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "h_score": r[2],
                "i_score": r[3],
                "s_score": r[4],
                "decision": r[5],
                "escalation_stage": r[6],
            }
            for r in rows
        ]

    def cleanup_expired(self) -> int:
        """Remove expired judgments from the ledger.

        Runs the decay policy: delete rows where expires_at < now.
        Same pattern as TemporalMemory.cleanup().

        Returns:
            Number of rows deleted.
        """
        now = _now_iso()
        with self._lock:
            with self._get_conn() as conn:
                result = conn.execute(
                    "DELETE FROM judgment_ledger WHERE expires_at < ?",
                    (now,),
                )
                deleted = result.rowcount
                conn.commit()
        return deleted

    def forget(self, session_id: str) -> int:
        """Right to forget — delete ALL records for a session/user.

        Hard delete, no tombstones, no archives.
        When someone asks to be forgotten, they are forgotten.

        Returns:
            Number of rows deleted.
        """
        with self._lock:
            with self._get_conn() as conn:
                result = conn.execute(
                    "DELETE FROM judgment_ledger WHERE session_id = ?",
                    (session_id,),
                )
                deleted = result.rowcount
                conn.commit()
        return deleted

    def count(self, session_id: Optional[str] = None) -> int:
        """Count records in the ledger.

        Args:
            session_id: if specified, count only that session's records.

        Returns:
            Total count of matching records.
        """
        with self._get_conn() as conn:
            if session_id:
                return conn.execute(
                    "SELECT COUNT(*) FROM judgment_ledger WHERE session_id = ?",
                    (session_id,),
                ).fetchone()[0]
            return conn.execute(
                "SELECT COUNT(*) FROM judgment_ledger",
            ).fetchone()[0]

    def _compute_expiry(
        self, decision: str, domain_sensitivity: float, now_iso: str,
    ) -> str:
        """Compute expiry timestamp based on decision type and D parameter.

        Tiered decay:
          EXECUTE   -> 30d (STANDARD) or 90d (FULL)
          CLARIFY   -> 60d (STANDARD) or 180d (FULL)
          SAFE_STOP / SAFE_FREEZE -> 180d (STANDARD) or 365d (FULL)
        """
        now_dt = _iso_to_dt(now_iso)
        is_full = domain_sensitivity > STORAGE_FULL_THRESHOLD

        if decision == "EXECUTE":
            days = DECAY_EXECUTE_FULL if is_full else DECAY_EXECUTE_STANDARD
        elif decision == "CLARIFY":
            days = DECAY_CLARIFY_FULL if is_full else DECAY_CLARIFY_STANDARD
        else:  # SAFE_STOP, SAFE_FREEZE
            days = DECAY_SAFETY_FULL if is_full else DECAY_SAFETY_STANDARD

        expires_dt = now_dt + timedelta(days=days)
        return _dt_to_iso(expires_dt)


# ═══════════════════════════════════════════════════════════
#  JudgmentMemory — main class (ذاكرة الحُكم)
# ═══════════════════════════════════════════════════════════

class JudgmentMemory:
    """Judgment memory for AATIF — ميزان مش فهرس.

    Builds JudgmentContext before the S equation runs and records
    outcomes after. Detects escalation patterns, computes trust,
    and adjusts theta within safety bounds.

    Usage:
        jm = JudgmentMemory("/path/to/judgment_memory.db")

        # Before S equation:
        ctx = jm.build_context(msg_embedding, session_id, dialect="levantine")

        # After S equation:
        jm.record_judgment(session_id, msg_hash, msg_embedding,
                           scores, decision, dialect, D, theta)
    """

    def __init__(
        self,
        db_path: str,
        domain_sensitivity: float = 0.2,
    ):
        """Initialize JudgmentMemory.

        Args:
            db_path: path to the SQLite database file.
            domain_sensitivity: D parameter (0.0-1.0). Default 0.2 (casual).
                Set per deployment domain. Higher = more dangerous domain
                = stricter behavior.
        """
        self.domain_sensitivity = max(0.0, min(1.0, domain_sensitivity))
        self.ledger = JudgmentLedger(db_path)

    # ───────────────────────────────────────────────────
    #  build_context() — produce JudgmentContext for S equation
    # ───────────────────────────────────────────────────

    def build_context(
        self,
        msg_embedding: Optional[np.ndarray],
        session_id: str,
        dialect: Optional[str] = None,
    ) -> JudgmentContext:
        """Build judgment context for the current message.

        This runs BEFORE the S equation. It reads the ledger to
        produce adjustments that make the scorers more accurate.

        Args:
            msg_embedding: bge-m3 embedding of the current message,
                or None if embeddings are unavailable.
            session_id: session/user identifier.
            dialect: detected dialect, or None.

        Returns:
            JudgmentContext with all fields computed.
        """
        D = self.domain_sensitivity

        # 1. Get session history for escalation + trust.
        history = self.ledger.get_session_history(session_id)

        # 2. Compute trust level from history.
        trust = self.compute_trust(session_id, history=history)

        # 3. Detect escalation pattern.
        escalation = self.detect_escalation(session_id, history=history)

        # 4. Compute historical intent average.
        intent_avg = self._compute_intent_avg(history)

        # 5. Look up similar prior judgment.
        prior = None
        if msg_embedding is not None:
            prior = self.ledger.query_similar(session_id, msg_embedding)

        # 6. Compute theta adjustment.
        theta_adj = self.compute_theta_adjustment(
            trust, D, escalation, history,
        )

        # 7. Build context notes.
        notes_parts = []
        if escalation != ESCALATION_NORMAL:
            notes_parts.append(f"escalation={escalation}")
        if prior:
            notes_parts.append(
                f"prior={prior['decision']} sim={prior['similarity']}"
            )
        if trust > TRUST_THRESHOLD:
            notes_parts.append(f"trust={trust:.2f}")

        return JudgmentContext(
            dialect_profile=dialect,
            historical_intent_avg=intent_avg,
            escalation_stage=escalation,
            theta_adjustment=theta_adj,
            h_adjustment=0.0,  # Phase 1: no direct H adjustment yet
            similar_prior_found=prior is not None,
            similar_prior_decision=prior["decision"] if prior else None,
            similar_prior_similarity=prior["similarity"] if prior else 0.0,
            similar_prior_age_hours=prior["age_hours"] if prior else 0.0,
            trust_level=trust,
            domain_sensitivity=D,
            context_notes="; ".join(notes_parts) if notes_parts else "",
        )

    # ───────────────────────────────────────────────────
    #  record_judgment() — write outcome to ledger
    # ───────────────────────────────────────────────────

    def record_judgment(
        self,
        session_id: str,
        msg_hash: str,
        msg_embedding: Optional[np.ndarray],
        scores: Dict[str, float],
        decision: str,
        dialect: Optional[str] = None,
        domain_sensitivity: Optional[float] = None,
        theta: float = 0.40,
    ) -> int:
        """Record a judgment outcome in the ledger.

        Called AFTER the S equation produces a decision.

        Args:
            session_id: session/user identifier.
            msg_hash: SHA-256 hash of the message.
            msg_embedding: bge-m3 embedding or None.
            scores: dict with keys "H", "I", "E", "S".
            decision: EXECUTE / CLARIFY / SAFE_STOP / SAFE_FREEZE.
            dialect: detected dialect or None.
            domain_sensitivity: D override (uses instance default if None).
            theta: effective theta used for this judgment.

        Returns:
            Row id of the inserted record, or -1 if skipped (LIGHT mode).
        """
        D = domain_sensitivity if domain_sensitivity is not None else self.domain_sensitivity

        # Detect current escalation for recording.
        escalation = self.detect_escalation(session_id)

        return self.ledger.record(
            session_id=session_id,
            msg_hash=msg_hash,
            msg_embedding=msg_embedding,
            h_score=scores.get("H", 0.0),
            i_score=scores.get("I", 0.0),
            e_score=scores.get("E", 0.0),
            s_score=scores.get("S", 0.0),
            decision=decision,
            dialect=dialect,
            domain_sensitivity=D,
            theta_used=theta,
            escalation_stage=escalation,
        )

    # ───────────────────────────────────────────────────
    #  detect_escalation() — sequence analysis over history
    # ───────────────────────────────────────────────────

    def detect_escalation(
        self,
        session_id: str,
        history: Optional[List[Dict]] = None,
    ) -> str:
        """Detect escalation patterns in the session's judgment history.

        Analyzes the last N decisions for patterns that are invisible
        in single-turn scoring:

          NORMAL    -> all recent decisions are EXECUTE
          PROBING   -> H scores creeping up, intent still constructive
          TESTING   -> triggered CLARIFY/STOP, now asking related questions
          ATTACKING -> 2+ SAFE_STOP/FREEZE, persistent probing

        Args:
            session_id: session/user identifier.
            history: pre-fetched history (optimization). If None, fetched.

        Returns:
            One of: NORMAL, PROBING, TESTING, ATTACKING.
        """
        if history is None:
            history = self.ledger.get_session_history(session_id)

        if len(history) < 3:
            return ESCALATION_NORMAL

        # Count safety events (SAFE_STOP / SAFE_FREEZE).
        safety_events = sum(
            1 for h in history
            if h["decision"] in ("SAFE_STOP", "SAFE_FREEZE")
        )

        # Count CLARIFY events.
        clarify_events = sum(
            1 for h in history if h["decision"] == "CLARIFY"
        )

        # ATTACKING: 2+ safety events in the window.
        if safety_events >= 2:
            return ESCALATION_ATTACKING

        # TESTING: at least 1 CLARIFY or SAFE_STOP, user continues.
        if safety_events >= 1 or clarify_events >= 2:
            return ESCALATION_TESTING

        # PROBING: H scores are creeping upward.
        # avg(H, last 3) > avg(H, all) * 1.5
        h_scores = [
            h["h_score"] for h in history
            if h["h_score"] is not None
        ]
        if len(h_scores) >= 3:
            recent_avg = sum(h_scores[:3]) / 3.0  # history is most-recent-first
            full_avg = sum(h_scores) / len(h_scores)
            if full_avg > 0.01 and recent_avg > full_avg * 1.5:
                return ESCALATION_PROBING

        return ESCALATION_NORMAL

    # ───────────────────────────────────────────────────
    #  compute_trust() — trust level from history
    # ───────────────────────────────────────────────────

    def compute_trust(
        self,
        session_id: str,
        history: Optional[List[Dict]] = None,
    ) -> float:
        """Compute trust level for a session based on judgment history.

        Trust is a value in [0.0, 1.0] derived from:
          - Number of interactions (need >= TRUST_MIN_INTERACTIONS)
          - Ratio of EXECUTE decisions (constructive history)
          - Absence of recent safety events

        Trust is earned slowly, lost quickly (asymmetric).

        Args:
            session_id: session/user identifier.
            history: pre-fetched history (optimization).

        Returns:
            Trust level in [0.0, 1.0].
        """
        if history is None:
            history = self.ledger.get_session_history(
                session_id, limit=100,
            )

        if len(history) < 3:
            return 0.0

        total = len(history)
        execute_count = sum(
            1 for h in history if h["decision"] == "EXECUTE"
        )
        safety_count = sum(
            1 for h in history
            if h["decision"] in ("SAFE_STOP", "SAFE_FREEZE")
        )

        # Any recent safety event (in last 5) kills trust immediately.
        recent_5 = history[:5]
        recent_safety = sum(
            1 for h in recent_5
            if h["decision"] in ("SAFE_STOP", "SAFE_FREEZE")
        )
        if recent_safety > 0:
            return 0.0

        # Base trust from EXECUTE ratio.
        execute_ratio = execute_count / total if total > 0 else 0.0

        # Scale by interaction count (ramp up slowly).
        # At TRUST_MIN_INTERACTIONS, full weight. Below, proportional.
        interaction_scale = min(total / TRUST_MIN_INTERACTIONS, 1.0)

        # Penalize any historical safety events.
        safety_penalty = min(safety_count * 0.15, 0.5)

        trust = execute_ratio * interaction_scale - safety_penalty
        return max(0.0, min(1.0, trust))

    # ───────────────────────────────────────────────────
    #  compute_theta_adjustment() — D-scaled theta change
    # ───────────────────────────────────────────────────

    def compute_theta_adjustment(
        self,
        trust: float,
        domain_sensitivity: float,
        escalation: str = ESCALATION_NORMAL,
        history: Optional[List[Dict]] = None,
    ) -> float:
        """Compute theta adjustment from trust, D, and escalation.

        This replaces the simple Dynamic Theta (block count -> decay).
        Richer: considers trust, escalation, and consecutive stops.

        Asymmetry is intentional:
          Memory can tighten theta by up to -0.20
          Memory can loosen theta by at most +0.05 (before D scaling)

        Args:
            trust: trust level (0.0-1.0).
            domain_sensitivity: D parameter (0.0-1.0).
            escalation: current escalation stage.
            history: pre-fetched history (for consecutive stops).

        Returns:
            Theta adjustment (negative = stricter, positive = lenient).
        """
        delta = 0.0

        # 1. Escalation penalty (always negative — tighter).
        escalation_penalty = ESCALATION_PENALTIES.get(escalation, 0.0)
        delta += escalation_penalty

        # 2. Consecutive stops penalty (always negative).
        if history:
            consecutive_stops = 0
            for h in history:  # most recent first
                if h["decision"] in ("SAFE_STOP", "SAFE_FREEZE"):
                    consecutive_stops += 1
                else:
                    break
            if consecutive_stops >= 2:
                delta -= 0.05 * min(consecutive_stops, 4)  # max -0.20

        # 3. Trust credit (can be positive — D-scaled).
        #    Requires: high trust, enough interactions, stable constructive,
        #    zero recent stops.
        if (trust > TRUST_THRESHOLD
                and escalation == ESCALATION_NORMAL
                and history and len(history) >= TRUST_MIN_INTERACTIONS):
            # Check no consecutive stops (already checked but explicit).
            has_recent_stops = any(
                h["decision"] in ("SAFE_STOP", "SAFE_FREEZE")
                for h in (history[:5] if history else [])
            )
            if not has_recent_stops:
                # D-scaled trust credit:
                #   trust_adjustment = MAX_TRUST_CREDIT * (1 - D)
                trust_credit = MAX_TRUST_CREDIT * (1.0 - domain_sensitivity)
                delta += trust_credit

        # Clamp to safety bounds.
        # Memory can tighten by up to THETA_MAX_TIGHTEN (-0.20)
        # and loosen by at most THETA_MAX_LOOSEN (+0.05).
        delta = max(THETA_MAX_TIGHTEN, min(THETA_MAX_LOOSEN, delta))

        return round(delta, 4)

    # ───────────────────────────────────────────────────
    #  compute_dialect_weight() — D-scaled dialect factor
    # ───────────────────────────────────────────────────

    @staticmethod
    def compute_dialect_weight(domain_sensitivity: float) -> float:
        """Compute how much weight to give dialect priors.

        dialect_weight = (1 - D)

        Casual (D=0.2): 0.80 -> dialect fully recognized
        Healthcare (D=0.9): 0.10 -> dialect almost ignored

        Args:
            domain_sensitivity: D parameter (0.0-1.0).

        Returns:
            Dialect weight in [0.0, 1.0].
        """
        return round(1.0 - domain_sensitivity, 4)

    # ───────────────────────────────────────────────────
    #  forget() — right to forget
    # ───────────────────────────────────────────────────

    def forget(self, session_id: str) -> int:
        """Erase all judgment records for a session/user.

        Hard delete — no tombstones, no archives.
        Does NOT touch TemporalMemory or Fingerprint.

        Args:
            session_id: session/user identifier.

        Returns:
            Number of records deleted.
        """
        return self.ledger.forget(session_id)

    # ───────────────────────────────────────────────────
    #  cleanup() — remove expired judgments
    # ───────────────────────────────────────────────────

    def cleanup(self) -> int:
        """Remove expired judgments from the ledger.

        Should run on Governor startup and periodically.
        Same pattern as TemporalMemory.cleanup().

        Returns:
            Number of records deleted.
        """
        return self.ledger.cleanup_expired()

    # ───────────────────────────────────────────────────
    #  Internal helpers
    # ───────────────────────────────────────────────────

    @staticmethod
    def _compute_intent_avg(history: List[Dict]) -> float:
        """Compute running average of historical I scores.

        Args:
            history: list of judgment records (most recent first).

        Returns:
            Average I score, or 0.5 if insufficient data.
        """
        i_scores = [
            h["i_score"] for h in history
            if h.get("i_score") is not None
        ]
        if not i_scores:
            return 0.5
        return round(sum(i_scores) / len(i_scores), 4)


# ═══════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════

def _run_tests():
    """Verify JudgmentMemory behavior."""
    import tempfile
    import shutil

    print("=" * 65)
    print("AATIF Judgment Memory — Tests")
    print("=" * 65)

    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}")

    tmp = tempfile.mkdtemp(prefix="aatif_jm_")
    db_path = os.path.join(tmp, "judgment_memory.db")

    try:
        # ── Test 1: Basic initialization ──
        print("\nTest 1: Basic initialization")
        jm = JudgmentMemory(db_path, domain_sensitivity=0.2)
        check("T1a: JudgmentMemory created", jm is not None)
        check("T1b: D parameter set", jm.domain_sensitivity == 0.2)
        check("T1c: Ledger initialized", jm.ledger.count() == 0)

        # ── Test 2: Record judgment ──
        print("\nTest 2: Record judgment")
        session = "test_session_1"
        msg_hash = _hash_message("test message")
        scores = {"H": 0.1, "I": 0.8, "E": 0.5, "S": 0.75}

        row_id = jm.record_judgment(
            session_id=session,
            msg_hash=msg_hash,
            msg_embedding=None,
            scores=scores,
            decision="EXECUTE",
            dialect="gulf",
            theta=0.40,
        )

        # D=0.2 is LIGHT mode -> only safety events stored.
        check("T2a: EXECUTE skipped in LIGHT mode", row_id == -1)

        # Record a safety event — should be stored.
        scores_stop = {"H": 0.6, "I": 0.3, "E": 0.4, "S": 0.35}
        row_id = jm.record_judgment(
            session_id=session,
            msg_hash=_hash_message("harmful message"),
            msg_embedding=None,
            scores=scores_stop,
            decision="SAFE_STOP",
            dialect="gulf",
            theta=0.40,
        )
        check("T2b: SAFE_STOP stored in LIGHT mode", row_id > 0)
        check("T2c: Ledger has 1 record", jm.ledger.count() == 1)

        # ── Test 3: STANDARD mode (D=0.5) stores more ──
        print("\nTest 3: STANDARD mode storage")
        db_path_std = os.path.join(tmp, "jm_standard.db")
        jm_std = JudgmentMemory(db_path_std, domain_sensitivity=0.5)

        jm_std.record_judgment(
            session_id=session,
            msg_hash=_hash_message("standard msg"),
            msg_embedding=None,
            scores=scores,
            decision="EXECUTE",
            dialect="egyptian",
            theta=0.40,
        )
        check("T3a: EXECUTE stored in STANDARD", jm_std.ledger.count() == 1)

        # ── Test 4: Escalation detection ──
        print("\nTest 4: Escalation detection")
        db_path_esc = os.path.join(tmp, "jm_escalation.db")
        jm_esc = JudgmentMemory(db_path_esc, domain_sensitivity=0.5)
        esc_session = "escalation_test"

        # Build history: normal -> CLARIFY -> SAFE_STOP -> ...
        for i, (dec, h) in enumerate([
            ("EXECUTE", 0.1), ("EXECUTE", 0.12),
            ("EXECUTE", 0.15), ("CLARIFY", 0.35),
            ("SAFE_STOP", 0.55), ("EXECUTE", 0.1),
        ]):
            jm_esc.record_judgment(
                session_id=esc_session,
                msg_hash=_hash_message(f"msg_{i}"),
                msg_embedding=None,
                scores={"H": h, "I": 0.7, "E": 0.5, "S": 0.5},
                decision=dec,
                theta=0.40,
            )

        esc = jm_esc.detect_escalation(esc_session)
        check("T4a: Escalation detected (TESTING expected)",
              esc == ESCALATION_TESTING)

        # Add another SAFE_STOP -> should become ATTACKING.
        jm_esc.record_judgment(
            session_id=esc_session,
            msg_hash=_hash_message("msg_attack"),
            msg_embedding=None,
            scores={"H": 0.65, "I": 0.2, "E": 0.3, "S": 0.25},
            decision="SAFE_STOP",
            theta=0.40,
        )
        esc2 = jm_esc.detect_escalation(esc_session)
        check("T4b: ATTACKING after 2+ SAFE_STOP",
              esc2 == ESCALATION_ATTACKING)

        # ── Test 5: Trust computation ──
        print("\nTest 5: Trust computation")
        db_path_trust = os.path.join(tmp, "jm_trust.db")
        jm_trust = JudgmentMemory(db_path_trust, domain_sensitivity=0.5)
        trust_session = "trust_test"

        # Build 25 clean EXECUTE history.
        for i in range(25):
            jm_trust.record_judgment(
                session_id=trust_session,
                msg_hash=_hash_message(f"clean_{i}"),
                msg_embedding=None,
                scores={"H": 0.05, "I": 0.85, "E": 0.6, "S": 0.80},
                decision="EXECUTE",
                theta=0.40,
            )

        trust = jm_trust.compute_trust(trust_session)
        check("T5a: Trust > 0.5 after 25 clean", trust > 0.5)

        # Add a SAFE_STOP -> trust should drop to 0.
        jm_trust.record_judgment(
            session_id=trust_session,
            msg_hash=_hash_message("bad_msg"),
            msg_embedding=None,
            scores={"H": 0.6, "I": 0.2, "E": 0.3, "S": 0.30},
            decision="SAFE_STOP",
            theta=0.40,
        )
        trust_after = jm_trust.compute_trust(trust_session)
        check("T5b: Trust = 0 after recent SAFE_STOP", trust_after == 0.0)

        # ── Test 6: Theta adjustment ──
        print("\nTest 6: Theta adjustment")

        # Normal with high trust, casual domain (D=0.2).
        adj_normal = jm_trust.compute_theta_adjustment(
            trust=0.8, domain_sensitivity=0.2,
            escalation=ESCALATION_NORMAL,
        )
        # Should not grant credit (no history passed, so no check).
        check("T6a: Normal adjustment >= 0", adj_normal >= 0.0)

        # Escalation penalty.
        adj_probing = jm_trust.compute_theta_adjustment(
            trust=0.5, domain_sensitivity=0.5,
            escalation=ESCALATION_PROBING,
        )
        check("T6b: Probing penalty = -0.10", adj_probing == -0.10)

        adj_attacking = jm_trust.compute_theta_adjustment(
            trust=0.0, domain_sensitivity=0.5,
            escalation=ESCALATION_ATTACKING,
        )
        check("T6c: Attacking penalty = -0.20", adj_attacking == -0.20)

        # Max loosening bounded.
        adj_max = jm_trust.compute_theta_adjustment(
            trust=1.0, domain_sensitivity=0.0,
            escalation=ESCALATION_NORMAL,
        )
        check("T6d: Max loosening <= 0.05", adj_max <= THETA_MAX_LOOSEN)

        # Government domain (D=0.95): almost zero credit.
        adj_gov = jm_trust.compute_theta_adjustment(
            trust=1.0, domain_sensitivity=0.95,
            escalation=ESCALATION_NORMAL,
        )
        check("T6e: Government credit near zero",
              adj_gov <= 0.003)  # 0.05 * 0.05 = 0.0025

        # ── Test 7: Dialect weight ──
        print("\nTest 7: Dialect weight (D-scaled)")
        check("T7a: Casual (D=0.2) -> 0.80",
              JudgmentMemory.compute_dialect_weight(0.2) == 0.80)
        check("T7b: Healthcare (D=0.9) -> 0.10",
              JudgmentMemory.compute_dialect_weight(0.9) == 0.10)
        check("T7c: Government (D=0.95) -> 0.05",
              JudgmentMemory.compute_dialect_weight(0.95) == 0.05)

        # ── Test 8: Safety invariants ──
        print("\nTest 8: Safety invariants")
        check("T8a: H_ADJUSTMENT_FLOOR = 0.15",
              H_ADJUSTMENT_FLOOR == 0.15)
        check("T8b: H_HARD_OVERRIDE = 0.70",
              H_HARD_OVERRIDE == 0.70)
        check("T8c: THETA_MAX_LOOSEN = 0.05",
              THETA_MAX_LOOSEN == 0.05)
        check("T8d: THETA_MAX_TIGHTEN = -0.20",
              THETA_MAX_TIGHTEN == -0.20)
        check("T8e: THETA_FLOOR = 0.20",
              THETA_FLOOR == 0.20)

        # ── Test 9: Build context (empty history) ──
        print("\nTest 9: Build context")
        db_path_ctx = os.path.join(tmp, "jm_context.db")
        jm_ctx = JudgmentMemory(db_path_ctx, domain_sensitivity=0.4)

        ctx = jm_ctx.build_context(
            msg_embedding=None,
            session_id="new_user",
            dialect="levantine",
        )
        check("T9a: Context created", ctx is not None)
        check("T9b: Dialect set", ctx.dialect_profile == "levantine")
        check("T9c: Escalation = NORMAL",
              ctx.escalation_stage == ESCALATION_NORMAL)
        check("T9d: No prior found", ctx.similar_prior_found is False)
        check("T9e: Trust = 0 (new user)", ctx.trust_level == 0.0)
        check("T9f: D parameter passed through",
              ctx.domain_sensitivity == 0.4)

        # ── Test 10: Forget (right to erasure) ──
        print("\nTest 10: Right to forget")
        deleted = jm_esc.forget(esc_session)
        check("T10a: Records deleted", deleted > 0)
        check("T10b: Ledger empty for session",
              jm_esc.ledger.count(esc_session) == 0)

        # ── Test 11: Embedding similarity ──
        print("\nTest 11: Embedding similarity (prior lookup)")
        db_path_emb = os.path.join(tmp, "jm_embed.db")
        jm_emb = JudgmentMemory(db_path_emb, domain_sensitivity=0.8)
        emb_session = "embed_test"

        # Create a known embedding.
        rng = np.random.RandomState(42)
        emb_a = rng.randn(EMBEDDING_DIM).astype(np.float32)
        emb_a = emb_a / np.linalg.norm(emb_a)  # normalize

        # Record with embedding (D=0.8 > 0.7 -> FULL mode stores embeddings).
        jm_emb.record_judgment(
            session_id=emb_session,
            msg_hash=_hash_message("embed test msg"),
            msg_embedding=emb_a,
            scores={"H": 0.1, "I": 0.9, "E": 0.6, "S": 0.85},
            decision="EXECUTE",
            dialect="gulf",
            theta=0.40,
        )

        # Query with same embedding -> should find prior.
        prior = jm_emb.ledger.query_similar(emb_session, emb_a)
        check("T11a: Prior found (same embedding)", prior is not None)
        if prior:
            check("T11b: Similarity = 1.0",
                  abs(prior["similarity"] - 1.0) < 0.01)
            check("T11c: Decision = EXECUTE",
                  prior["decision"] == "EXECUTE")

        # Query with a different embedding -> should not find prior.
        emb_b = rng.randn(EMBEDDING_DIM).astype(np.float32)
        emb_b = emb_b / np.linalg.norm(emb_b)
        prior_diff = jm_emb.ledger.query_similar(emb_session, emb_b)
        check("T11d: No prior for different embedding",
              prior_diff is None)

        # ── Test 12: Domain profiles ──
        print("\nTest 12: Domain profiles")
        check("T12a: Casual = 0.2",
              DOMAIN_PROFILES["casual"] == 0.2)
        check("T12b: Healthcare = 0.9",
              DOMAIN_PROFILES["healthcare"] == 0.9)
        check("T12c: Government = 0.95",
              DOMAIN_PROFILES["government"] == 0.95)

        # ── Summary ──
        print(f"\n{'=' * 65}")
        total = passed + failed
        print(f"Results: {passed}/{total} passed", end="")
        if failed:
            print(f" -- {failed} FAILED")
        else:
            print(" -- All clear.")
        print(f"{'=' * 65}")

        return failed == 0

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    success = _run_tests()
    exit(0 if success else 1)
