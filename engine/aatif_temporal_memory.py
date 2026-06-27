#!/usr/bin/env python3
"""
AATIF Temporal Memory — الذاكرة الزمنية
========================================

The FIRST LAYER of عاطف's understanding triad:

    Memory      = الحقائق  (what happened and when — THIS MODULE)
    Fingerprint = النمط    (behavioral patterns over time)
    I scorer    = اللحظة   (this message's intent — single-turn)

Why this exists:
  The model must stay clean — الموديل المفروض يكون نظيف مش متأثر بأي بايوس.
  Memory lives OUTSIDE the model. This module provides the external storage
  of what happened with each user, when, with timestamps.

  TimeSense knows NOW — what time it is, what period, fatigue risk.
  TemporalMemory knows BEFORE — what happened last time, last week,
  what topics keep coming up, what was left unresolved.

  Together they form the full temporal picture.

Design principles:
  - SQLite not JSON: unlike Fingerprint (lightweight counters), Memory grows.
    SQLite handles scale without loading everything into RAM.
  - Summaries not raw text: store topic summaries, not full messages. Privacy.
  - Time is first-class: every query is time-aware.
  - Bridges TimeSense: TimeSense knows NOW, TemporalMemory knows BEFORE.
  - No ML, no embeddings: SQLite queries, counters, averages.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════
#  Optional TimeSense import — soft dependency
# ═══════════════════════════════════════════════════════════

try:
    from aatif_time_sense import TimeSense, TimeReading
except ImportError:
    try:
        from engine.aatif_time_sense import TimeSense, TimeReading
    except ImportError:
        TimeSense = None  # type: ignore
        TimeReading = None  # type: ignore

# ── Arabic text utilities — shared across the triad ──
try:
    from aatif_arabic_utils import normalize_arabic
except ImportError:
    try:
        from engine.aatif_arabic_utils import normalize_arabic
    except ImportError:
        def normalize_arabic(text: str) -> str:  # type: ignore[misc]
            return text  # passthrough if utils unavailable


# ═══════════════════════════════════════════════════════════
#  Greeting templates — Arabic, temporal-aware
# ═══════════════════════════════════════════════════════════

# Gap-based greeting logic:
#   First time ever        → "مرحبا، أهلا وسهلا"
#   Same session (< 30m)   → "" (no greeting needed)
#   Same day               → "أهلا مرة ثانية"
#   1-3 days               → "أهلاً، كيف الحال؟"
#   4-14 days              → "وحشتنا! كيف حالك؟"
#   15+ days               → "وحشتنا كثير! عساك بخير"

GREETING_FIRST_TIME = "مرحبا، أهلا وسهلا"
GREETING_SAME_SESSION = ""
GREETING_SAME_DAY = "أهلا مرة ثانية"
GREETING_SHORT_GAP = "أهلاً، كيف الحال؟"
GREETING_MEDIUM_GAP = "وحشتنا! كيف حالك؟"
GREETING_LONG_GAP = "وحشتنا كثير! عساك بخير"


# ═══════════════════════════════════════════════════════════
#  MemoryEntry — a single stored interaction
# ═══════════════════════════════════════════════════════════

@dataclass
class MemoryEntry:
    """
    A single stored interaction — حدث مسجل.

    Stores SUMMARIES, not full text (privacy).
    Every entry is timestamped — time is first-class.
    """
    entry_id: str              # UUID
    user_id: str
    timestamp: datetime
    time_period: str           # from TimeSense: "فجر", "صباح", etc.
    message_role: str          # "user" or "assistant"
    message_summary: str       # brief summary/topic — NOT full text
    topic: str                 # extracted topic/category
    intent_score: Optional[float] = None    # I score at time of interaction
    harm_score: Optional[float] = None      # H score at time of interaction
    emotion_score: Optional[float] = None   # E score at time of interaction
    s_decision: Optional[str] = None        # what S equation decided
    was_repeat_question: bool = False       # flagged by fingerprint
    confusion_detected: bool = False        # was confusion signal present
    resolution_achieved: bool = False       # did we resolve their issue
    session_id: Optional[str] = None        # session boundary marker


# ═══════════════════════════════════════════════════════════
#  TemporalContext — context retrieved for current interaction
# ═══════════════════════════════════════════════════════════

@dataclass
class TemporalContext:
    """
    Context built from memory for a current interaction — السياق الزمني.

    This is what the Governor receives: a structured summary of
    everything we know about this user's history, enriched with
    temporal patterns.
    """
    user_id: str
    total_interactions: int
    first_interaction: Optional[datetime]
    last_interaction: Optional[datetime]
    days_since_last: Optional[float]
    interaction_gap_assessment: str   # "returning_after_absence", "continuing_session", "regular", "first_time"
    recent_topics: List[str]          # last 5 topics discussed
    unresolved_topics: List[str]      # topics with confusion but no resolution
    topic_frequency: Dict[str, int]   # how often each topic comes up
    time_pattern: Dict[str, int]      # which time periods they interact in
    recent_decisions: List[Dict]       # last 5 S-equation decisions with timestamps
    emotional_trajectory: str          # "improving", "stable", "declining", "insufficient_data"
    suggested_greeting: str            # based on gap


# ═══════════════════════════════════════════════════════════
#  SQL schema
# ═══════════════════════════════════════════════════════════

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS interactions (
    entry_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    time_period TEXT,
    message_role TEXT,
    message_summary TEXT,
    topic TEXT,
    intent_score REAL,
    harm_score REAL,
    emotion_score REAL,
    s_decision TEXT,
    was_repeat_question INTEGER DEFAULT 0,
    confusion_detected INTEGER DEFAULT 0,
    resolution_achieved INTEGER DEFAULT 0,
    session_id TEXT
);
"""

_CREATE_INDEX_USER_TIME = """
CREATE INDEX IF NOT EXISTS idx_user_time
ON interactions(user_id, timestamp);
"""

_CREATE_INDEX_USER_TOPIC = """
CREATE INDEX IF NOT EXISTS idx_user_topic
ON interactions(user_id, topic);
"""

_CREATE_INDEX_SESSION = """
CREATE INDEX IF NOT EXISTS idx_user_session
ON interactions(user_id, session_id);
"""

# ── Dynamic θ: blocked decisions tracking (حساسية الأمان المتكيّفة) ──
_CREATE_BLOCKED_TABLE = """
CREATE TABLE IF NOT EXISTS blocked_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
"""

_CREATE_INDEX_BLOCKED = """
CREATE INDEX IF NOT EXISTS idx_blocked_user_time
ON blocked_decisions(user_id, timestamp);
"""


# ═══════════════════════════════════════════════════════════
#  Helper: datetime ↔ ISO 8601 string
# ═══════════════════════════════════════════════════════════

def _dt_to_iso(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string for storage."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _iso_to_dt(s: str) -> datetime:
    """Parse ISO 8601 string back to datetime."""
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ═══════════════════════════════════════════════════════════
#  TemporalMemory — الذاكرة الزمنية
# ═══════════════════════════════════════════════════════════

class TemporalMemory:
    """
    الذاكرة الزمنية — external temporal storage for عاطف.

    Stores interaction history with temporal awareness. Bridges
    TimeSense (which knows NOW) with persistent storage (which
    knows BEFORE).

    The model stays clean. Memory lives here.

    Usage:
        memory = TemporalMemory("/path/to/storage")
        memory.store(MemoryEntry(...))
        context = memory.get_context("user_123")
        print(context.suggested_greeting)
        print(context.unresolved_topics)
    """

    # Gap thresholds for greeting logic
    GAP_SAME_SESSION = timedelta(minutes=30)
    GAP_SAME_DAY = timedelta(hours=24)
    GAP_SHORT = timedelta(days=3)
    GAP_MEDIUM = timedelta(days=14)
    # > 14 days = long gap

    def __init__(
        self,
        storage_dir: str,
        time_sense: Optional[object] = None,
        db_name: str = "temporal_memory.db",
    ):
        """
        Args:
            storage_dir: directory for the SQLite database file.
            time_sense: optional TimeSense instance for current time awareness.
            db_name: database filename (default: temporal_memory.db).
        """
        self.storage_dir = storage_dir
        self.time_sense = time_sense
        self._db_path = os.path.join(storage_dir, db_name)
        self._lock = threading.Lock()

        # Ensure directory exists
        os.makedirs(storage_dir, exist_ok=True)

        # Initialize the database
        self._init_db()

    # ───────────────────────────────────────────────────
    #  Database initialization
    # ───────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create tables and indices if they don't exist."""
        with self._get_conn() as conn:
            conn.execute(_CREATE_TABLE)
            conn.execute(_CREATE_INDEX_USER_TIME)
            conn.execute(_CREATE_INDEX_USER_TOPIC)
            conn.execute(_CREATE_INDEX_SESSION)
            # Dynamic θ: blocked decisions table
            conn.execute(_CREATE_BLOCKED_TABLE)
            conn.execute(_CREATE_INDEX_BLOCKED)
            # Migration: add session_id column if upgrading from older schema
            try:
                conn.execute(
                    "ALTER TABLE interactions ADD COLUMN session_id TEXT"
                )
            except sqlite3.OperationalError:
                pass  # column already exists
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """
        Get a new SQLite connection.

        Each call creates a fresh connection — SQLite handles
        file-level locking internally. We use a threading lock
        on top for write safety in multi-threaded Python code.
        """
        conn = sqlite3.connect(self._db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ───────────────────────────────────────────────────
    #  store() — persist an interaction entry
    # ───────────────────────────────────────────────────

    def store(self, entry: MemoryEntry) -> str:
        """
        Store an interaction entry.

        Args:
            entry: the MemoryEntry to store.

        Returns:
            The entry_id (generated if not provided).
        """
        # Auto-generate entry_id if empty
        if not entry.entry_id:
            entry.entry_id = str(uuid.uuid4())

        # Validate timestamp
        if entry.timestamp is None:
            raise ValueError("MemoryEntry.timestamp cannot be None")

        ts_iso = _dt_to_iso(entry.timestamp)

        with self._lock:
            with self._get_conn() as conn:
                # Auto-assign session_id if not set (consensus fix #5)
                session_id = entry.session_id
                if session_id is None:
                    session_id = self._resolve_session_id(
                        conn, entry.user_id, entry.timestamp
                    )
                    entry.session_id = session_id

                conn.execute(
                    """
                    INSERT OR REPLACE INTO interactions
                    (entry_id, user_id, timestamp, time_period, message_role,
                     message_summary, topic, intent_score, harm_score,
                     emotion_score, s_decision, was_repeat_question,
                     confusion_detected, resolution_achieved, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.entry_id,
                        entry.user_id,
                        ts_iso,
                        entry.time_period or "",
                        entry.message_role or "",
                        entry.message_summary or "",
                        entry.topic or "",
                        entry.intent_score,
                        entry.harm_score,
                        entry.emotion_score,
                        entry.s_decision,
                        1 if entry.was_repeat_question else 0,
                        1 if entry.confusion_detected else 0,
                        1 if entry.resolution_achieved else 0,
                        session_id or "",
                    ),
                )
                conn.commit()

        return entry.entry_id

    # ───────────────────────────────────────────────────
    #  _row_to_entry() — convert a DB row to MemoryEntry
    # ───────────────────────────────────────────────────

    @staticmethod
    def _row_to_entry(row: tuple) -> MemoryEntry:
        """Convert a database row tuple to a MemoryEntry."""
        return MemoryEntry(
            entry_id=row[0],
            user_id=row[1],
            timestamp=_iso_to_dt(row[2]),
            time_period=row[3] or "",
            message_role=row[4] or "",
            message_summary=row[5] or "",
            topic=row[6] or "",
            intent_score=row[7],
            harm_score=row[8],
            emotion_score=row[9],
            s_decision=row[10],
            was_repeat_question=bool(row[11]),
            confusion_detected=bool(row[12]),
            resolution_achieved=bool(row[13]),
            session_id=row[14] if len(row) > 14 else None,
        )

    # ───────────────────────────────────────────────────
    #  recall() — retrieve past interactions
    # ───────────────────────────────────────────────────

    def recall(
        self,
        user_id: str,
        limit: int = 10,
        since: Optional[datetime] = None,
        topic: Optional[str] = None,
    ) -> List[MemoryEntry]:
        """
        Retrieve past interactions for a user.

        Args:
            user_id: the user to query.
            limit: maximum entries to return (default 10).
            since: only entries after this datetime.
            topic: filter by topic (substring match).

        Returns:
            List of MemoryEntry, ordered by timestamp descending
            (most recent first).
        """
        query = "SELECT * FROM interactions WHERE user_id = ?"
        params: list = [user_id]

        if since is not None:
            query += " AND timestamp >= ?"
            params.append(_dt_to_iso(since))

        if topic is not None:
            query += " AND topic LIKE ?"
            params.append(f"%{topic}%")

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_entry(row) for row in rows]

    # ───────────────────────────────────────────────────
    #  get_context() — build full temporal context
    # ───────────────────────────────────────────────────

    def get_context(self, user_id: str) -> TemporalContext:
        """
        Build the full temporal context for a current interaction.

        This is the main method the Governor will call. It computes
        all TemporalContext fields from stored data.

        Args:
            user_id: the user to build context for.

        Returns:
            TemporalContext with all fields computed.
        """
        with self._get_conn() as conn:
            # Total interactions
            total = conn.execute(
                "SELECT COUNT(*) FROM interactions WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

            if total == 0:
                return self._empty_context(user_id)

            # First and last interaction timestamps
            row = conn.execute(
                "SELECT MIN(timestamp), MAX(timestamp) FROM interactions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            first_dt = _iso_to_dt(row[0]) if row[0] else None
            last_dt = _iso_to_dt(row[1]) if row[1] else None

            # Days since last interaction
            now = datetime.now(timezone.utc)
            days_since = None
            if last_dt is not None:
                delta = now - last_dt
                days_since = delta.total_seconds() / 86400.0

            # Gap assessment
            gap_assessment = self._assess_gap(last_dt, now)

            # Recent topics (last 5 unique)
            recent_rows = conn.execute(
                """SELECT DISTINCT topic FROM interactions
                   WHERE user_id = ? AND topic != ''
                   ORDER BY timestamp DESC LIMIT 5""",
                (user_id,),
            ).fetchall()
            recent_topics = [r[0] for r in recent_rows]

            # Unresolved topics: confusion detected but no subsequent resolution
            unresolved = self._find_unresolved_topics(conn, user_id)

            # Topic frequency
            freq_rows = conn.execute(
                """SELECT topic, COUNT(*) as cnt FROM interactions
                   WHERE user_id = ? AND topic != ''
                   GROUP BY topic ORDER BY cnt DESC""",
                (user_id,),
            ).fetchall()
            topic_frequency = {r[0]: r[1] for r in freq_rows}

            # Time pattern: count by period
            period_rows = conn.execute(
                """SELECT time_period, COUNT(*) as cnt FROM interactions
                   WHERE user_id = ? AND time_period != ''
                   GROUP BY time_period ORDER BY cnt DESC""",
                (user_id,),
            ).fetchall()
            time_pattern = {r[0]: r[1] for r in period_rows}

            # Recent S-equation decisions (last 5)
            decision_rows = conn.execute(
                """SELECT timestamp, s_decision FROM interactions
                   WHERE user_id = ? AND s_decision IS NOT NULL
                   AND s_decision != ''
                   ORDER BY timestamp DESC LIMIT 5""",
                (user_id,),
            ).fetchall()
            recent_decisions = [
                {"timestamp": r[0], "decision": r[1]}
                for r in decision_rows
            ]

            # Emotional trajectory
            emotional_trajectory = self._compute_emotional_trajectory(
                conn, user_id
            )

            # Suggested greeting
            suggested_greeting = self._select_greeting(last_dt, now)

        return TemporalContext(
            user_id=user_id,
            total_interactions=total,
            first_interaction=first_dt,
            last_interaction=last_dt,
            days_since_last=round(days_since, 4) if days_since is not None else None,
            interaction_gap_assessment=gap_assessment,
            recent_topics=recent_topics,
            unresolved_topics=unresolved,
            topic_frequency=topic_frequency,
            time_pattern=time_pattern,
            recent_decisions=recent_decisions,
            emotional_trajectory=emotional_trajectory,
            suggested_greeting=suggested_greeting,
        )

    # ───────────────────────────────────────────────────
    #  summarize_period() — summarize a time range
    # ───────────────────────────────────────────────────

    def summarize_period(
        self,
        user_id: str,
        start: datetime,
        end: datetime,
    ) -> str:
        """
        Summarize interactions over a time range.

        Args:
            user_id: the user to summarize.
            start: start of the period.
            end: end of the period.

        Returns:
            Human-readable summary string.
        """
        start_iso = _dt_to_iso(start)
        end_iso = _dt_to_iso(end)

        with self._get_conn() as conn:
            # Count interactions
            count = conn.execute(
                """SELECT COUNT(*) FROM interactions
                   WHERE user_id = ? AND timestamp >= ? AND timestamp <= ?""",
                (user_id, start_iso, end_iso),
            ).fetchone()[0]

            if count == 0:
                return f"No interactions recorded between {start.date()} and {end.date()}."

            # Main topics
            topics = conn.execute(
                """SELECT topic, COUNT(*) as cnt FROM interactions
                   WHERE user_id = ? AND timestamp >= ? AND timestamp <= ?
                   AND topic != ''
                   GROUP BY topic ORDER BY cnt DESC LIMIT 5""",
                (user_id, start_iso, end_iso),
            ).fetchall()
            topic_list = [f"{t[0]}" for t in topics]

            # Unresolved questions in period
            unresolved_count = conn.execute(
                """SELECT COUNT(*) FROM interactions
                   WHERE user_id = ? AND timestamp >= ? AND timestamp <= ?
                   AND confusion_detected = 1 AND resolution_achieved = 0""",
                (user_id, start_iso, end_iso),
            ).fetchone()[0]

        # Build summary
        days = max((end - start).days, 1)
        parts = [f"In the last {days} days: {count} interactions"]
        if topic_list:
            parts.append(f"main topics: {', '.join(topic_list)}")
        if unresolved_count > 0:
            parts.append(
                f"{unresolved_count} unresolved question"
                + ("s" if unresolved_count > 1 else "")
            )
        return ", ".join(parts) + "."

    # ───────────────────────────────────────────────────
    #  detect_pattern_change() — behavioral shifts
    # ───────────────────────────────────────────────────

    def detect_pattern_change(self, user_id: str) -> Optional[str]:
        """
        Detect notable behavioral shifts for a user.

        Checks:
          - Time period shift (normally morning, now late night)
          - Frequency change (daily → weekly or vice versa)
          - Emotional trajectory declining

        Returns:
            Description of the change, or None if nothing notable.
        """
        with self._get_conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM interactions WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

            if total < 5:
                return None  # need enough data

            # --- Time period shift ---
            # Compare older half vs newer half
            midpoint_row = conn.execute(
                """SELECT timestamp FROM interactions
                   WHERE user_id = ?
                   ORDER BY timestamp ASC LIMIT 1 OFFSET ?""",
                (user_id, total // 2),
            ).fetchone()

            if midpoint_row:
                midpoint_ts = midpoint_row[0]

                # Dominant period in older half
                old_period = conn.execute(
                    """SELECT time_period, COUNT(*) as cnt FROM interactions
                       WHERE user_id = ? AND timestamp < ?
                       AND time_period != ''
                       GROUP BY time_period ORDER BY cnt DESC LIMIT 1""",
                    (user_id, midpoint_ts),
                ).fetchone()

                # Dominant period in newer half
                new_period = conn.execute(
                    """SELECT time_period, COUNT(*) as cnt FROM interactions
                       WHERE user_id = ? AND timestamp >= ?
                       AND time_period != ''
                       GROUP BY time_period ORDER BY cnt DESC LIMIT 1""",
                    (user_id, midpoint_ts),
                ).fetchone()

                if old_period and new_period and old_period[0] != new_period[0]:
                    return (
                        f"Time pattern shift: was mostly active during "
                        f"{old_period[0]}, now active during {new_period[0]}"
                    )

            # --- Frequency change ---
            # Compare interaction density: older half vs newer half
            if total >= 6 and midpoint_row:
                older_count = total // 2
                newer_count = total - older_count

                first_ts = conn.execute(
                    "SELECT MIN(timestamp) FROM interactions WHERE user_id = ?",
                    (user_id,),
                ).fetchone()[0]
                last_ts = conn.execute(
                    "SELECT MAX(timestamp) FROM interactions WHERE user_id = ?",
                    (user_id,),
                ).fetchone()[0]

                if first_ts and last_ts and midpoint_ts:
                    first_dt = _iso_to_dt(first_ts)
                    mid_dt = _iso_to_dt(midpoint_ts)
                    last_dt = _iso_to_dt(last_ts)

                    old_span = max((mid_dt - first_dt).total_seconds(), 1)
                    new_span = max((last_dt - mid_dt).total_seconds(), 1)

                    old_rate = older_count / old_span
                    new_rate = newer_count / new_span

                    if old_rate > 0 and new_rate > 0:
                        ratio = new_rate / old_rate
                        if ratio < 0.33:
                            return "Interaction frequency dropped significantly"
                        if ratio > 3.0:
                            return "Interaction frequency increased significantly"

            # --- Emotional trajectory check ---
            trajectory = self._compute_emotional_trajectory(conn, user_id)
            if trajectory == "declining":
                return "Emotional trajectory declining over recent interactions"

        return None

    # ───────────────────────────────────────────────────
    #  cleanup() — remove old entries
    # ───────────────────────────────────────────────────

    def cleanup(
        self,
        user_id: Optional[str] = None,
        older_than_days: int = 90,
    ) -> int:
        """
        Remove entries older than a threshold.

        Privacy principle: don't keep data forever.

        Args:
            user_id: if specified, clean only that user.
            older_than_days: remove entries older than this many days.

        Returns:
            Number of entries deleted.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        cutoff_iso = _dt_to_iso(cutoff)

        with self._lock:
            with self._get_conn() as conn:
                if user_id:
                    result = conn.execute(
                        """DELETE FROM interactions
                           WHERE user_id = ? AND timestamp < ?""",
                        (user_id, cutoff_iso),
                    )
                else:
                    result = conn.execute(
                        "DELETE FROM interactions WHERE timestamp < ?",
                        (cutoff_iso,),
                    )
                deleted = result.rowcount
                conn.commit()

        return deleted

    # ───────────────────────────────────────────────────
    #  merge_with_fingerprint() — bridge Layer 1 + Layer 2
    # ───────────────────────────────────────────────────

    def merge_with_fingerprint(
        self,
        user_id: str,
        fingerprint_reading: object,
    ) -> Dict:
        """
        Combine temporal memory with a fingerprint reading.

        This is the bridge between Layer 1 (Memory = الحقائق)
        and Layer 2 (Fingerprint = النمط). Returns enriched context
        that the Governor can use for the full picture.

        The fingerprint tells us WHO this person is behaviorally.
        The memory tells us WHAT happened and WHEN.
        Together: pattern + facts = understanding.

        Args:
            user_id: the user.
            fingerprint_reading: a FingerprintReading from UserFingerprint.

        Returns:
            Dict with merged context:
              - fingerprint: the behavioral pattern
              - memory: the temporal facts
              - insights: computed cross-layer observations
        """
        context = self.get_context(user_id)

        # Extract fingerprint fields safely via getattr
        fp_style = getattr(fingerprint_reading, "communication_style", "mixed")
        fp_comp = getattr(fingerprint_reading, "comprehension_level", "quick")
        fp_emo = getattr(fingerprint_reading, "emotional_baseline", "calm")
        fp_trust = getattr(fingerprint_reading, "trust_level", 0.0)
        fp_confusion = getattr(fingerprint_reading, "confusion_signals", 0)
        fp_satisfaction = getattr(fingerprint_reading, "satisfaction_signals", 0)
        fp_approach = getattr(fingerprint_reading, "suggested_approach", "")

        # Cross-layer insights
        insights = []

        # Insight 1: unresolved topics + confusion pattern
        if context.unresolved_topics and fp_comp in ("needs_step_by_step", "needs_examples"):
            insights.append(
                f"User has {len(context.unresolved_topics)} unresolved topics "
                f"and needs {fp_comp.replace('_', ' ')} — "
                f"try a different explanation approach"
            )

        # Insight 2: emotional trajectory + baseline mismatch
        if context.emotional_trajectory == "declining" and fp_emo == "calm":
            insights.append(
                "Emotional trajectory declining despite calm baseline — "
                "something may be wrong"
            )

        # Insight 3: returning after absence + low trust
        if context.interaction_gap_assessment == "returning_after_absence" and fp_trust < 0.3:
            insights.append(
                "User returning after absence with low trust — "
                "be extra welcoming and patient"
            )

        # Insight 4: high frequency topic may need proactive help
        if context.topic_frequency:
            top_topic = max(context.topic_frequency, key=context.topic_frequency.get)
            top_count = context.topic_frequency[top_topic]
            if top_count >= 5:
                insights.append(
                    f"Topic '{top_topic}' has come up {top_count} times — "
                    f"consider proactive guidance"
                )

        return {
            "user_id": user_id,
            "fingerprint": {
                "style": fp_style,
                "comprehension": fp_comp,
                "emotional_baseline": fp_emo,
                "trust_level": fp_trust,
                "confusion_signals": fp_confusion,
                "satisfaction_signals": fp_satisfaction,
                "suggested_approach": fp_approach,
            },
            "memory": {
                "total_interactions": context.total_interactions,
                "days_since_last": context.days_since_last,
                "gap_assessment": context.interaction_gap_assessment,
                "recent_topics": context.recent_topics,
                "unresolved_topics": context.unresolved_topics,
                "emotional_trajectory": context.emotional_trajectory,
                "suggested_greeting": context.suggested_greeting,
            },
            "insights": insights,
        }

    # ───────────────────────────────────────────────────
    #  count() — total entries for a user
    # ───────────────────────────────────────────────────

    def count(self, user_id: Optional[str] = None) -> int:
        """
        Count stored entries.

        Args:
            user_id: if specified, count only that user's entries.

        Returns:
            Total count of matching entries.
        """
        with self._get_conn() as conn:
            if user_id:
                return conn.execute(
                    "SELECT COUNT(*) FROM interactions WHERE user_id = ?",
                    (user_id,),
                ).fetchone()[0]
            else:
                return conn.execute(
                    "SELECT COUNT(*) FROM interactions",
                ).fetchone()[0]

    # ───────────────────────────────────────────────────
    #  Dynamic θ — blocked decision tracking
    #  حساسية الأمان المتكيّفة
    # ───────────────────────────────────────────────────

    def record_blocked_decision(self, user_id: str, decision_type: str) -> None:
        """Record a SAFE_STOP or SAFE_FREEZE event for Dynamic θ computation.

        Only SAFE_STOP and SAFE_FREEZE are recorded; other decision types
        are silently ignored.
        """
        if decision_type not in ("SAFE_STOP", "SAFE_FREEZE"):
            return
        ts_iso = _dt_to_iso(datetime.now(timezone.utc))
        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO blocked_decisions (user_id, decision_type, timestamp) "
                    "VALUES (?, ?, ?)",
                    (user_id, decision_type, ts_iso),
                )
                conn.commit()

    def get_recent_blocks(self, user_id: str, n: int = 20) -> list:
        """Return the last N blocked decisions for Dynamic θ computation.

        Returns:
            List of dicts with 'decision_type' and 'timestamp' keys,
            ordered most-recent-first.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT decision_type, timestamp FROM blocked_decisions "
                "WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, n),
            ).fetchall()
        return [{"decision_type": r[0], "timestamp": r[1]} for r in rows]

    # ───────────────────────────────────────────────────
    #  Internal helper methods
    # ───────────────────────────────────────────────────

    def _resolve_session_id(
        self,
        conn: sqlite3.Connection,
        user_id: str,
        current_ts: datetime,
    ) -> str:
        """
        Determine which session this interaction belongs to.

        Session boundary = gap > 30 minutes since last interaction
        for the same user (consensus fix #5).

        If the gap is <= 30 minutes, reuse the previous session_id.
        If the gap is > 30 minutes (or first interaction), start a new session.

        Args:
            conn: active database connection.
            user_id: the user.
            current_ts: timestamp of the current interaction.

        Returns:
            A session_id string (UUID for new sessions, or reused).
        """
        import uuid as _uuid

        current_iso = _dt_to_iso(current_ts)

        # Find the most recent interaction for this user
        row = conn.execute(
            """SELECT timestamp, session_id FROM interactions
               WHERE user_id = ?
               ORDER BY timestamp DESC LIMIT 1""",
            (user_id,),
        ).fetchone()

        if row is None:
            # First interaction — new session
            return str(_uuid.uuid4())

        last_ts = _iso_to_dt(row[0])
        last_session = row[1] or ""

        gap = current_ts - last_ts
        if gap <= self.GAP_SAME_SESSION and last_session:
            # Same session — reuse
            return last_session
        else:
            # New session
            return str(_uuid.uuid4())

    def _empty_context(self, user_id: str) -> TemporalContext:
        """Return an empty context for a user with no history."""
        return TemporalContext(
            user_id=user_id,
            total_interactions=0,
            first_interaction=None,
            last_interaction=None,
            days_since_last=None,
            interaction_gap_assessment="first_time",
            recent_topics=[],
            unresolved_topics=[],
            topic_frequency={},
            time_pattern={},
            recent_decisions=[],
            emotional_trajectory="insufficient_data",
            suggested_greeting=GREETING_FIRST_TIME,
        )

    def _assess_gap(
        self,
        last_interaction: Optional[datetime],
        now: datetime,
    ) -> str:
        """
        Assess the gap between last interaction and now.

        Returns one of:
          "first_time"              — no previous interaction
          "continuing_session"      — < 30 minutes
          "regular"                 — < 3 days
          "returning_after_absence" — 3+ days
        """
        if last_interaction is None:
            return "first_time"

        gap = now - last_interaction
        if gap < self.GAP_SAME_SESSION:
            return "continuing_session"
        if gap < self.GAP_SHORT:
            return "regular"
        return "returning_after_absence"

    def _select_greeting(
        self,
        last_interaction: Optional[datetime],
        now: datetime,
    ) -> str:
        """
        Select Arabic greeting based on gap duration.

        Arabic, temporal-aware, compassionate.
        """
        if last_interaction is None:
            return GREETING_FIRST_TIME

        gap = now - last_interaction
        if gap < self.GAP_SAME_SESSION:
            return GREETING_SAME_SESSION
        if gap < self.GAP_SAME_DAY:
            return GREETING_SAME_DAY
        if gap < self.GAP_SHORT:
            return GREETING_SHORT_GAP
        if gap < self.GAP_MEDIUM:
            return GREETING_MEDIUM_GAP
        return GREETING_LONG_GAP

    def _find_unresolved_topics(
        self,
        conn: sqlite3.Connection,
        user_id: str,
    ) -> List[str]:
        """
        Find topics where confusion was detected but never resolved.

        Logic: find topics that have at least one entry with
        confusion_detected=1, but NO entry with resolution_achieved=1
        on the same topic that comes AFTER the confusion.
        """
        # Get topics with confusion
        confused_rows = conn.execute(
            """SELECT DISTINCT topic, MAX(timestamp) as last_confused
               FROM interactions
               WHERE user_id = ? AND confusion_detected = 1
               AND topic != ''
               GROUP BY topic""",
            (user_id,),
        ).fetchall()

        unresolved = []
        for topic, last_confused_ts in confused_rows:
            # Check if any resolution exists after the confusion
            resolved = conn.execute(
                """SELECT COUNT(*) FROM interactions
                   WHERE user_id = ? AND topic = ?
                   AND resolution_achieved = 1
                   AND timestamp >= ?""",
                (user_id, topic, last_confused_ts),
            ).fetchone()[0]
            if resolved == 0:
                unresolved.append(topic)

        return unresolved

    def _compute_emotional_trajectory(
        self,
        conn: sqlite3.Connection,
        user_id: str,
    ) -> str:
        """
        Compute emotional trajectory from last 5 E scores.

        Returns:
          "improving"         — trending up
          "stable"            — variance < 0.1
          "declining"         — trending down
          "insufficient_data" — fewer than 3 data points
        """
        rows = conn.execute(
            """SELECT emotion_score FROM interactions
               WHERE user_id = ? AND emotion_score IS NOT NULL
               ORDER BY timestamp DESC LIMIT 5""",
            (user_id,),
        ).fetchall()

        scores = [r[0] for r in rows if r[0] is not None]

        if len(scores) < 3:
            return "insufficient_data"

        # Reverse so chronological order (oldest first)
        scores = list(reversed(scores))

        # Check variance for stability
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        if variance < 0.01:  # very stable (0.1^2 = 0.01)
            return "stable"

        # Simple trend: compare first half avg to second half avg
        mid = len(scores) // 2
        first_half = scores[:mid] if mid > 0 else scores[:1]
        second_half = scores[mid:] if mid > 0 else scores[1:]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        diff = second_avg - first_avg
        if diff > 0.05:
            return "improving"
        if diff < -0.05:
            return "declining"
        return "stable"


# ═══════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile
    import shutil

    print("=" * 60)
    print("  الذاكرة الزمنية — AATIF Temporal Memory")
    print("=" * 60)

    tmp = tempfile.mkdtemp(prefix="aatif_mem_")
    try:
        mem = TemporalMemory(tmp)
        user = "user_test_001"
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)

        # Store a few interactions
        topics = ["python", "loops", "python", "functions", "python"]
        for i, topic in enumerate(topics):
            entry = MemoryEntry(
                entry_id="",
                user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح",
                message_role="user",
                message_summary=f"Asked about {topic}",
                topic=topic,
                emotion_score=0.5 + i * 0.05,
                confusion_detected=(i == 2),
            )
            mem.store(entry)

        ctx = mem.get_context(user)
        print(f"\n  User: {ctx.user_id}")
        print(f"  Total: {ctx.total_interactions}")
        print(f"  Recent topics: {ctx.recent_topics}")
        print(f"  Unresolved: {ctx.unresolved_topics}")
        print(f"  Topic frequency: {ctx.topic_frequency}")
        print(f"  Emotional trajectory: {ctx.emotional_trajectory}")
        print(f"  Greeting: {ctx.suggested_greeting}")
        print(f"  Gap: {ctx.interaction_gap_assessment}")

        summary = mem.summarize_period(user, base, base + timedelta(days=1))
        print(f"\n  Summary: {summary}")

        change = mem.detect_pattern_change(user)
        print(f"  Pattern change: {change}")

        print(f"\n{'=' * 60}")
        print(f"  عاطف يتذكر — الذاكرة الزمنية شغالة")
        print(f"{'=' * 60}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
