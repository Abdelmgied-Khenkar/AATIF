#!/usr/bin/env python3
"""
Temporal Memory tests for aatif_temporal_memory.py — الذاكرة الزمنية
=====================================================================

WHY THIS FILE EXISTS
--------------------
The Temporal Memory is the FIRST LAYER of عاطف's understanding triad:
  Memory      = الحقائق  (what happened and when) ← THIS
  Fingerprint = النمط    (behavioral patterns)
  I scorer    = اللحظة   (single turn)

It stores interaction history with temporal awareness, bridging
TimeSense (NOW) with persistent storage (BEFORE).

TESTING STRATEGY
----------------
TemporalMemory uses SQLite — each test gets a fresh temp directory.
We test storage, retrieval, context building, pattern detection,
greeting logic, emotional trajectories, cleanup, and the bridge
to fingerprint. Every test is deterministic and CI-friendly.

Architect: Abdulmjeed Ibrahim Khenkar
"""

import pytest
import os
import sys
import tempfile
import shutil
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.aatif_temporal_memory import (
    TemporalMemory,
    MemoryEntry,
    TemporalContext,
    GREETING_FIRST_TIME,
    GREETING_SAME_SESSION,
    GREETING_SAME_DAY,
    GREETING_SHORT_GAP,
    GREETING_MEDIUM_GAP,
    GREETING_LONG_GAP,
    _dt_to_iso,
    _iso_to_dt,
)

# ═══════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="aatif_mem_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)

@pytest.fixture
def mem(tmp_dir):
    return TemporalMemory(tmp_dir)

BASE_DT = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
USER_A = "user_alpha"
USER_B = "user_beta"

def _make_entry(user_id=USER_A, timestamp=None, time_period="صباح",
                message_role="user", message_summary="test message",
                topic="general", intent_score=None, harm_score=None,
                emotion_score=None, s_decision=None,
                was_repeat_question=False, confusion_detected=False,
                resolution_achieved=False, entry_id=""):
    return MemoryEntry(
        entry_id=entry_id, user_id=user_id,
        timestamp=timestamp or BASE_DT,
        time_period=time_period, message_role=message_role,
        message_summary=message_summary, topic=topic,
        intent_score=intent_score, harm_score=harm_score,
        emotion_score=emotion_score, s_decision=s_decision,
        was_repeat_question=was_repeat_question,
        confusion_detected=confusion_detected,
        resolution_achieved=resolution_achieved,
    )

# ═══════════════════════════════════════════════════════════
#  1. ISO DATETIME HELPERS
# ═══════════════════════════════════════════════════════════

class TestDatetimeHelpers:
    def test_dt_to_iso_with_tz(self):
        dt = datetime(2026, 6, 20, 10, 30, 0, tzinfo=timezone.utc)
        iso = _dt_to_iso(dt)
        assert "2026-06-20" in iso and "10:30" in iso

    def test_dt_to_iso_naive_gets_utc(self):
        dt = datetime(2026, 6, 20, 10, 30, 0)
        assert "+00:00" in _dt_to_iso(dt)

    def test_iso_to_dt_roundtrip(self):
        original = datetime(2026, 6, 20, 10, 30, 0, tzinfo=timezone.utc)
        assert _iso_to_dt(_dt_to_iso(original)) == original

    def test_iso_to_dt_naive_string_gets_utc(self):
        assert _iso_to_dt("2026-06-20T10:30:00").tzinfo == timezone.utc

# ═══════════════════════════════════════════════════════════
#  2. STORE AND RECALL
# ═══════════════════════════════════════════════════════════

class TestStoreAndRecall:
    def test_store_single_entry(self, mem):
        eid = mem.store(_make_entry())
        assert eid and mem.count(USER_A) == 1

    def test_store_auto_generates_id(self, mem):
        assert len(mem.store(_make_entry(entry_id=""))) == 36

    def test_store_preserves_custom_id(self, mem):
        assert mem.store(_make_entry(entry_id="custom-id-123")) == "custom-id-123"

    def test_store_none_timestamp_raises(self, mem):
        e = _make_entry(); e.timestamp = None
        with pytest.raises(ValueError, match="timestamp"):
            mem.store(e)

    def test_recall_single_entry(self, mem):
        mem.store(_make_entry(topic="python", message_summary="learning python"))
        r = mem.recall(USER_A)
        assert len(r) == 1 and r[0].topic == "python"

    def test_recall_preserves_all_fields(self, mem):
        mem.store(_make_entry(intent_score=0.8, harm_score=0.1, emotion_score=0.6,
                              s_decision="EXECUTE", was_repeat_question=True,
                              confusion_detected=True, resolution_achieved=True))
        r = mem.recall(USER_A)[0]
        assert r.intent_score == pytest.approx(0.8)
        assert r.harm_score == pytest.approx(0.1)
        assert r.emotion_score == pytest.approx(0.6)
        assert r.s_decision == "EXECUTE"
        assert r.was_repeat_question is True
        assert r.confusion_detected is True
        assert r.resolution_achieved is True

    def test_recall_multiple_entries(self, mem):
        for i in range(5):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), topic=f"t{i}"))
        assert len(mem.recall(USER_A, limit=10)) == 5

    def test_recall_most_recent_first(self, mem):
        for i in range(5):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), topic=f"t{i}"))
        r = mem.recall(USER_A)
        assert r[0].topic == "t4" and r[-1].topic == "t0"

    def test_recall_with_limit(self, mem):
        for i in range(10):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i)))
        assert len(mem.recall(USER_A, limit=3)) == 3

    def test_recall_with_since_filter(self, mem):
        for i in range(10):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i)))
        assert len(mem.recall(USER_A, since=BASE_DT + timedelta(hours=7))) == 3

    def test_recall_with_topic_filter(self, mem):
        mem.store(_make_entry(topic="python", timestamp=BASE_DT))
        mem.store(_make_entry(topic="javascript", timestamp=BASE_DT + timedelta(hours=1)))
        mem.store(_make_entry(topic="python_loops", timestamp=BASE_DT + timedelta(hours=2)))
        assert len(mem.recall(USER_A, topic="python")) == 2

    def test_recall_combined_filters(self, mem):
        for i in range(10):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i),
                                  topic="python" if i % 2 == 0 else "javascript"))
        assert len(mem.recall(USER_A, since=BASE_DT + timedelta(hours=5), topic="python")) == 2

    def test_recall_empty_db(self, mem):
        assert mem.recall(USER_A) == []

    def test_recall_wrong_user(self, mem):
        mem.store(_make_entry(user_id=USER_A))
        assert mem.recall(USER_B) == []

    def test_store_upsert_on_same_id(self, mem):
        mem.store(_make_entry(entry_id="fixed-id", topic="old_topic"))
        mem.store(_make_entry(entry_id="fixed-id", topic="new_topic"))
        assert mem.count(USER_A) == 1
        assert mem.recall(USER_A)[0].topic == "new_topic"

# ═══════════════════════════════════════════════════════════
#  3. GET_CONTEXT
# ═══════════════════════════════════════════════════════════

class TestGetContext:
    def test_context_for_new_user(self, mem):
        ctx = mem.get_context("unknown")
        assert ctx.total_interactions == 0
        assert ctx.interaction_gap_assessment == "first_time"
        assert ctx.suggested_greeting == GREETING_FIRST_TIME
        assert ctx.emotional_trajectory == "insufficient_data"

    def test_context_total_interactions(self, mem):
        for i in range(7):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i)))
        assert mem.get_context(USER_A).total_interactions == 7

    def test_context_first_and_last_interaction(self, mem):
        mem.store(_make_entry(timestamp=BASE_DT))
        mem.store(_make_entry(timestamp=BASE_DT + timedelta(days=3)))
        ctx = mem.get_context(USER_A)
        assert ctx.first_interaction == BASE_DT
        assert ctx.last_interaction == BASE_DT + timedelta(days=3)

    def test_context_days_since_last(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(days=2)))
        ctx = mem.get_context(USER_A)
        assert ctx.days_since_last is not None and 1.9 < ctx.days_since_last < 2.1

    def test_context_recent_topics(self, mem):
        for i, t in enumerate(["python", "loops", "funcs", "classes", "testing", "deploy"]):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), topic=t))
        ctx = mem.get_context(USER_A)
        assert len(ctx.recent_topics) == 5
        assert "deploy" in ctx.recent_topics
        assert "python" not in ctx.recent_topics

    def test_context_topic_frequency(self, mem):
        for i in range(3):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), topic="python"))
        mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=5), topic="js"))
        ctx = mem.get_context(USER_A)
        assert ctx.topic_frequency["python"] == 3 and ctx.topic_frequency["js"] == 1

    def test_context_time_pattern(self, mem):
        for i, p in enumerate(["صباح", "صباح", "صباح", "ليل", "مساء"]):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), time_period=p))
        ctx = mem.get_context(USER_A)
        assert ctx.time_pattern["صباح"] == 3

    def test_context_recent_decisions(self, mem):
        for i, d in enumerate(["EXECUTE", "CLARIFY", "SAFE_STOP", "EXECUTE", "EXECUTE"]):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), s_decision=d))
        ctx = mem.get_context(USER_A)
        assert len(ctx.recent_decisions) == 5
        assert ctx.recent_decisions[0]["decision"] == "EXECUTE"

    def test_context_recent_decisions_max_5(self, mem):
        for i in range(10):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), s_decision=f"D{i}"))
        assert len(mem.get_context(USER_A).recent_decisions) == 5

    def test_context_decisions_skip_empty(self, mem):
        mem.store(_make_entry(s_decision=None))
        mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=1), s_decision="EXECUTE"))
        assert len(mem.get_context(USER_A).recent_decisions) == 1

# ═══════════════════════════════════════════════════════════
#  4. UNRESOLVED TOPICS
# ═══════════════════════════════════════════════════════════

class TestUnresolvedTopics:
    def test_no_confusion_no_unresolved(self, mem):
        mem.store(_make_entry(topic="python"))
        assert mem.get_context(USER_A).unresolved_topics == []

    def test_confusion_without_resolution(self, mem):
        mem.store(_make_entry(topic="python", confusion_detected=True))
        assert "python" in mem.get_context(USER_A).unresolved_topics

    def test_confusion_then_resolution(self, mem):
        mem.store(_make_entry(timestamp=BASE_DT, topic="python", confusion_detected=True))
        mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=1),
                              topic="python", resolution_achieved=True))
        assert "python" not in mem.get_context(USER_A).unresolved_topics

    def test_resolution_before_confusion_still_unresolved(self, mem):
        mem.store(_make_entry(timestamp=BASE_DT, topic="python", resolution_achieved=True))
        mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=1),
                              topic="python", confusion_detected=True))
        assert "python" in mem.get_context(USER_A).unresolved_topics

    def test_multiple_unresolved(self, mem):
        mem.store(_make_entry(topic="python", confusion_detected=True, timestamp=BASE_DT))
        mem.store(_make_entry(topic="js", confusion_detected=True,
                              timestamp=BASE_DT + timedelta(hours=1)))
        assert set(mem.get_context(USER_A).unresolved_topics) == {"python", "js"}

    def test_mixed_resolved_and_unresolved(self, mem):
        mem.store(_make_entry(topic="python", confusion_detected=True, timestamp=BASE_DT))
        mem.store(_make_entry(topic="python", resolution_achieved=True,
                              timestamp=BASE_DT + timedelta(hours=1)))
        mem.store(_make_entry(topic="js", confusion_detected=True,
                              timestamp=BASE_DT + timedelta(hours=2)))
        ctx = mem.get_context(USER_A)
        assert "js" in ctx.unresolved_topics
        assert "python" not in ctx.unresolved_topics

# ═══════════════════════════════════════════════════════════
#  5. EMOTIONAL TRAJECTORY
# ═══════════════════════════════════════════════════════════

class TestEmotionalTrajectory:
    def test_insufficient_data(self, mem):
        mem.store(_make_entry(emotion_score=0.5, timestamp=BASE_DT))
        mem.store(_make_entry(emotion_score=0.6, timestamp=BASE_DT + timedelta(hours=1)))
        assert mem.get_context(USER_A).emotional_trajectory == "insufficient_data"

    def test_improving(self, mem):
        for i, s in enumerate([0.3, 0.4, 0.5, 0.6, 0.7]):
            mem.store(_make_entry(emotion_score=s, timestamp=BASE_DT + timedelta(hours=i)))
        assert mem.get_context(USER_A).emotional_trajectory == "improving"

    def test_declining(self, mem):
        for i, s in enumerate([0.7, 0.6, 0.5, 0.4, 0.3]):
            mem.store(_make_entry(emotion_score=s, timestamp=BASE_DT + timedelta(hours=i)))
        assert mem.get_context(USER_A).emotional_trajectory == "declining"

    def test_stable(self, mem):
        for i in range(5):
            mem.store(_make_entry(emotion_score=0.5, timestamp=BASE_DT + timedelta(hours=i)))
        assert mem.get_context(USER_A).emotional_trajectory == "stable"

    def test_stable_small_variance(self, mem):
        for i, s in enumerate([0.50, 0.51, 0.49, 0.50, 0.52]):
            mem.store(_make_entry(emotion_score=s, timestamp=BASE_DT + timedelta(hours=i)))
        assert mem.get_context(USER_A).emotional_trajectory == "stable"

    def test_none_scores_excluded(self, mem):
        mem.store(_make_entry(emotion_score=0.3, timestamp=BASE_DT))
        mem.store(_make_entry(emotion_score=None, timestamp=BASE_DT + timedelta(hours=1)))
        mem.store(_make_entry(emotion_score=0.5, timestamp=BASE_DT + timedelta(hours=2)))
        mem.store(_make_entry(emotion_score=0.7, timestamp=BASE_DT + timedelta(hours=3)))
        assert mem.get_context(USER_A).emotional_trajectory == "improving"

    def test_all_none_insufficient(self, mem):
        for i in range(5):
            mem.store(_make_entry(emotion_score=None, timestamp=BASE_DT + timedelta(hours=i)))
        assert mem.get_context(USER_A).emotional_trajectory == "insufficient_data"

# ═══════════════════════════════════════════════════════════
#  6. GREETING LOGIC
# ═══════════════════════════════════════════════════════════

class TestGreetingLogic:
    def test_first_time(self, mem):
        assert mem.get_context("new").suggested_greeting == GREETING_FIRST_TIME

    def test_same_session(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(minutes=5)))
        assert mem.get_context(USER_A).suggested_greeting == GREETING_SAME_SESSION

    def test_same_day(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(hours=2)))
        assert mem.get_context(USER_A).suggested_greeting == GREETING_SAME_DAY

    def test_short_gap(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(days=2)))
        assert mem.get_context(USER_A).suggested_greeting == GREETING_SHORT_GAP

    def test_medium_gap(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(days=7)))
        assert mem.get_context(USER_A).suggested_greeting == GREETING_MEDIUM_GAP

    def test_long_gap(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(days=20)))
        assert mem.get_context(USER_A).suggested_greeting == GREETING_LONG_GAP

    def test_boundary_29min(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(minutes=29)))
        assert mem.get_context(USER_A).suggested_greeting == GREETING_SAME_SESSION

    def test_boundary_31min(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(minutes=31)))
        assert mem.get_context(USER_A).suggested_greeting == GREETING_SAME_DAY

# ═══════════════════════════════════════════════════════════
#  7. GAP ASSESSMENT
# ═══════════════════════════════════════════════════════════

class TestGapAssessment:
    def test_first_time(self, mem):
        assert mem.get_context("ghost").interaction_gap_assessment == "first_time"

    def test_continuing_session(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(minutes=10)))
        assert mem.get_context(USER_A).interaction_gap_assessment == "continuing_session"

    def test_regular(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(days=1)))
        assert mem.get_context(USER_A).interaction_gap_assessment == "regular"

    def test_returning_after_absence(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(days=10)))
        assert mem.get_context(USER_A).interaction_gap_assessment == "returning_after_absence"

# ═══════════════════════════════════════════════════════════
#  8. SUMMARIZE PERIOD
# ═══════════════════════════════════════════════════════════

class TestSummarizePeriod:
    def test_no_interactions(self, mem):
        s = mem.summarize_period(USER_A, BASE_DT, BASE_DT + timedelta(days=7))
        assert "No interactions" in s

    def test_with_interactions(self, mem):
        for i in range(5):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), topic="python"))
        s = mem.summarize_period(USER_A, BASE_DT - timedelta(hours=1), BASE_DT + timedelta(days=1))
        assert "5 interactions" in s and "python" in s

    def test_with_unresolved(self, mem):
        mem.store(_make_entry(timestamp=BASE_DT, topic="delivery", confusion_detected=True))
        s = mem.summarize_period(USER_A, BASE_DT - timedelta(hours=1), BASE_DT + timedelta(days=1))
        assert "1 unresolved question" in s

    def test_multiple_topics(self, mem):
        for i, t in enumerate(["pricing", "features", "delivery"]):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), topic=t))
        s = mem.summarize_period(USER_A, BASE_DT - timedelta(hours=1), BASE_DT + timedelta(days=1))
        assert "pricing" in s and "features" in s

    def test_plural_unresolved(self, mem):
        mem.store(_make_entry(timestamp=BASE_DT, topic="a", confusion_detected=True))
        mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=1), topic="b",
                              confusion_detected=True))
        s = mem.summarize_period(USER_A, BASE_DT - timedelta(hours=1), BASE_DT + timedelta(days=1))
        assert "2 unresolved questions" in s

# ═══════════════════════════════════════════════════════════
#  9. PATTERN CHANGE DETECTION
# ═══════════════════════════════════════════════════════════

class TestPatternChange:
    def test_no_change_few_entries(self, mem):
        for i in range(3):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i)))
        assert mem.detect_pattern_change(USER_A) is None

    def test_time_period_shift(self, mem):
        for i in range(5):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i),
                                  time_period="صباح", entry_id=f"a{i}"))
        for i in range(5):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(days=1, hours=i),
                                  time_period="ليل", entry_id=f"b{i}"))
        change = mem.detect_pattern_change(USER_A)
        assert change is not None and "صباح" in change and "ليل" in change

    def test_no_change_same_period(self, mem):
        for i in range(10):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i),
                                  time_period="صباح", emotion_score=0.5, entry_id=f"e{i}"))
        assert mem.detect_pattern_change(USER_A) is None

    def test_emotional_decline_detected(self, mem):
        # Evenly spaced, same period — only emotional trajectory should trigger.
        # Scores decline across entries so the last 5 show a clear downward trend.
        scores = [0.9, 0.85, 0.8, 0.75, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]
        for i, s in enumerate(scores):
            mem.store(_make_entry(
                timestamp=BASE_DT + timedelta(hours=i),
                time_period="صباح",
                emotion_score=s,
                entry_id=f"emo_{i}",
            ))
        change = mem.detect_pattern_change(USER_A)
        assert change is not None
        assert "declining" in change.lower() or "Emotional" in change

    def test_frequency_drop_detected(self, mem):
        # Older: dense (10 entries in 1 hour)
        for i in range(10):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(minutes=i * 5),
                                  time_period="صباح", emotion_score=0.5, entry_id=f"d{i}"))
        # Newer: sparse
        mem.store(_make_entry(timestamp=BASE_DT + timedelta(days=5),
                              time_period="صباح", emotion_score=0.5, entry_id="s1"))
        mem.store(_make_entry(timestamp=BASE_DT + timedelta(days=10),
                              time_period="صباح", emotion_score=0.5, entry_id="s2"))
        change = mem.detect_pattern_change(USER_A)
        assert change is not None and "frequency" in change.lower()

    def test_no_change_unknown_user(self, mem):
        assert mem.detect_pattern_change("ghost") is None

# ═══════════════════════════════════════════════════════════
#  10. CLEANUP
# ═══════════════════════════════════════════════════════════

class TestCleanup:
    def test_cleanup_old(self, mem):
        old = datetime.now(timezone.utc) - timedelta(days=100)
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        mem.store(_make_entry(timestamp=old, entry_id="old"))
        mem.store(_make_entry(timestamp=recent, entry_id="new"))
        assert mem.cleanup(older_than_days=90) == 1
        assert mem.count(USER_A) == 1

    def test_cleanup_by_user(self, mem):
        old = datetime.now(timezone.utc) - timedelta(days=100)
        mem.store(_make_entry(user_id=USER_A, timestamp=old, entry_id="a"))
        mem.store(_make_entry(user_id=USER_B, timestamp=old, entry_id="b"))
        assert mem.cleanup(user_id=USER_A, older_than_days=90) == 1
        assert mem.count(USER_A) == 0 and mem.count(USER_B) == 1

    def test_cleanup_all_users(self, mem):
        old = datetime.now(timezone.utc) - timedelta(days=100)
        mem.store(_make_entry(user_id=USER_A, timestamp=old, entry_id="a"))
        mem.store(_make_entry(user_id=USER_B, timestamp=old, entry_id="b"))
        assert mem.cleanup(older_than_days=90) == 2

    def test_cleanup_nothing(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(days=1)))
        assert mem.cleanup(older_than_days=90) == 0 and mem.count(USER_A) == 1

    def test_cleanup_custom_threshold(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(days=8)))
        assert mem.cleanup(older_than_days=7) == 1

# ═══════════════════════════════════════════════════════════
#  11. MERGE WITH FINGERPRINT
# ═══════════════════════════════════════════════════════════

class _MockFingerprint:
    def __init__(self, **kw):
        self.communication_style = kw.get("communication_style", "casual")
        self.comprehension_level = kw.get("comprehension_level", "quick")
        self.emotional_baseline = kw.get("emotional_baseline", "calm")
        self.trust_level = kw.get("trust_level", 0.5)
        self.confusion_signals = kw.get("confusion_signals", 0)
        self.satisfaction_signals = kw.get("satisfaction_signals", 3)
        self.suggested_approach = kw.get("suggested_approach", "be direct")

class TestMergeWithFingerprint:
    def test_basic_structure(self, mem):
        mem.store(_make_entry())
        merged = mem.merge_with_fingerprint(USER_A, _MockFingerprint())
        assert all(k in merged for k in ("fingerprint", "memory", "insights"))
        assert merged["user_id"] == USER_A

    def test_fingerprint_fields(self, mem):
        mem.store(_make_entry())
        merged = mem.merge_with_fingerprint(USER_A,
                    _MockFingerprint(communication_style="formal", trust_level=0.8))
        assert merged["fingerprint"]["style"] == "formal"
        assert merged["fingerprint"]["trust_level"] == 0.8

    def test_memory_fields(self, mem):
        mem.store(_make_entry(topic="python"))
        merged = mem.merge_with_fingerprint(USER_A, _MockFingerprint())
        assert merged["memory"]["total_interactions"] == 1
        assert "python" in merged["memory"]["recent_topics"]

    def test_insight_unresolved_steps(self, mem):
        mem.store(_make_entry(topic="python", confusion_detected=True))
        merged = mem.merge_with_fingerprint(USER_A,
                    _MockFingerprint(comprehension_level="needs_step_by_step"))
        assert any("unresolved" in i.lower() for i in merged["insights"])

    def test_insight_declining_calm(self, mem):
        for i, s in enumerate([0.7, 0.6, 0.5, 0.4, 0.3]):
            mem.store(_make_entry(emotion_score=s, timestamp=BASE_DT + timedelta(hours=i)))
        merged = mem.merge_with_fingerprint(USER_A,
                    _MockFingerprint(emotional_baseline="calm"))
        assert any("declining" in i.lower() for i in merged["insights"])

    def test_insight_returning_low_trust(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(days=10)))
        merged = mem.merge_with_fingerprint(USER_A, _MockFingerprint(trust_level=0.1))
        assert any("returning" in i.lower() or "trust" in i.lower()
                    for i in merged["insights"])

    def test_insight_frequent_topic(self, mem):
        for i in range(6):
            mem.store(_make_entry(topic="python", timestamp=BASE_DT + timedelta(hours=i)))
        merged = mem.merge_with_fingerprint(USER_A, _MockFingerprint())
        assert any("python" in i.lower() and "6 times" in i for i in merged["insights"])

    def test_no_insights_clean(self, mem):
        mem.store(_make_entry(emotion_score=0.5))
        merged = mem.merge_with_fingerprint(USER_A, _MockFingerprint(trust_level=0.8))
        assert merged["insights"] == []

    def test_merge_empty_db(self, mem):
        merged = mem.merge_with_fingerprint("nobody", _MockFingerprint())
        assert merged["memory"]["total_interactions"] == 0

# ═══════════════════════════════════════════════════════════
#  12. PERSISTENCE
# ═══════════════════════════════════════════════════════════

class TestPersistence:
    def test_data_persists(self, tmp_dir):
        m1 = TemporalMemory(tmp_dir)
        m1.store(_make_entry(topic="python"))
        m1.store(_make_entry(topic="js", timestamp=BASE_DT + timedelta(hours=1), entry_id="j1"))
        m2 = TemporalMemory(tmp_dir)
        assert len(m2.recall(USER_A)) == 2

    def test_context_from_new_instance(self, tmp_dir):
        m1 = TemporalMemory(tmp_dir)
        for i in range(5):
            m1.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i),
                                 topic=f"t{i}", emotion_score=0.5))
        assert TemporalMemory(tmp_dir).get_context(USER_A).total_interactions == 5

    def test_db_file_exists(self, tmp_dir):
        TemporalMemory(tmp_dir)
        assert os.path.exists(os.path.join(tmp_dir, "temporal_memory.db"))

    def test_custom_db_name(self, tmp_dir):
        TemporalMemory(tmp_dir, db_name="custom.db")
        assert os.path.exists(os.path.join(tmp_dir, "custom.db"))

# ═══════════════════════════════════════════════════════════
#  13. MULTIPLE USERS
# ═══════════════════════════════════════════════════════════

class TestMultipleUsers:
    def test_separate_data(self, mem):
        mem.store(_make_entry(user_id=USER_A, topic="python"))
        mem.store(_make_entry(user_id=USER_B, topic="js", entry_id="b1"))
        assert mem.count(USER_A) == 1 and mem.count(USER_B) == 1

    def test_recall_isolation(self, mem):
        mem.store(_make_entry(user_id=USER_A, topic="python"))
        mem.store(_make_entry(user_id=USER_B, topic="js", entry_id="b1"))
        assert mem.recall(USER_A)[0].topic == "python"
        assert mem.recall(USER_B)[0].topic == "js"

    def test_context_per_user(self, mem):
        for i in range(5):
            mem.store(_make_entry(user_id=USER_A, timestamp=BASE_DT + timedelta(hours=i),
                                  entry_id=f"a{i}"))
        for i in range(3):
            mem.store(_make_entry(user_id=USER_B, timestamp=BASE_DT + timedelta(hours=i),
                                  entry_id=f"b{i}"))
        assert mem.get_context(USER_A).total_interactions == 5
        assert mem.get_context(USER_B).total_interactions == 3

    def test_total_count(self, mem):
        mem.store(_make_entry(user_id=USER_A, entry_id="a1"))
        mem.store(_make_entry(user_id=USER_B, entry_id="b1"))
        assert mem.count() == 2

# ═══════════════════════════════════════════════════════════
#  14. EDGE CASES
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_strings(self, mem):
        mem.store(_make_entry(time_period="", message_role="", message_summary="", topic=""))
        r = mem.recall(USER_A)[0]
        assert r.time_period == "" and r.topic == ""

    def test_unicode(self, mem):
        mem.store(_make_entry(topic="البرمجة بايثون", message_summary="سأل عن البرمجة"))
        r = mem.recall(USER_A)[0]
        assert r.topic == "البرمجة بايثون"

    def test_very_long_summary(self, mem):
        mem.store(_make_entry(message_summary="x" * 10000))
        assert len(mem.recall(USER_A)[0].message_summary) == 10000

    def test_future_timestamp(self, mem):
        mem.store(_make_entry(timestamp=datetime(2030, 1, 1, tzinfo=timezone.utc)))
        assert mem.recall(USER_A)[0].timestamp.year == 2030

    def test_very_old_timestamp(self, mem):
        mem.store(_make_entry(timestamp=datetime(2000, 1, 1, tzinfo=timezone.utc)))
        assert mem.recall(USER_A)[0].timestamp.year == 2000

    def test_score_extremes(self, mem):
        mem.store(_make_entry(intent_score=0.0, harm_score=1.0, emotion_score=0.0))
        r = mem.recall(USER_A)[0]
        assert r.intent_score == 0.0 and r.harm_score == 1.0

    def test_negative_score(self, mem):
        mem.store(_make_entry(emotion_score=-0.5))
        assert mem.recall(USER_A)[0].emotion_score == pytest.approx(-0.5)

    def test_count_empty(self, mem):
        assert mem.count() == 0 and mem.count(USER_A) == 0

    def test_recall_limit_zero(self, mem):
        mem.store(_make_entry())
        assert mem.recall(USER_A, limit=0) == []

    def test_recall_large_limit(self, mem):
        for i in range(5):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), entry_id=f"e{i}"))
        assert len(mem.recall(USER_A, limit=1000)) == 5

# ═══════════════════════════════════════════════════════════
#  15. CONCURRENT ACCESS
# ═══════════════════════════════════════════════════════════

class TestConcurrentAccess:
    def test_concurrent_writes(self, tmp_dir):
        mem = TemporalMemory(tmp_dir)
        errors = []
        def writer(tid):
            try:
                for i in range(20):
                    mem.store(_make_entry(user_id=f"u{tid}",
                        timestamp=BASE_DT + timedelta(hours=tid * 100 + i),
                        entry_id=f"t{tid}_e{i}"))
            except Exception as e:
                errors.append(str(e))
        threads = [threading.Thread(target=writer, args=(t,)) for t in range(5)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=30)
        assert errors == []
        assert mem.count() == 100

    def test_concurrent_read_write(self, tmp_dir):
        mem = TemporalMemory(tmp_dir)
        for i in range(10):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), entry_id=f"p{i}"))
        read_results, errors = [], []
        def reader():
            try:
                for _ in range(20):
                    read_results.append(mem.get_context(USER_A).total_interactions)
            except Exception as e:
                errors.append(str(e))
        def writer():
            try:
                for i in range(10):
                    mem.store(_make_entry(timestamp=BASE_DT + timedelta(days=1, hours=i),
                                          entry_id=f"n{i}"))
            except Exception as e:
                errors.append(str(e))
        tr, tw = threading.Thread(target=reader), threading.Thread(target=writer)
        tr.start(); tw.start(); tr.join(30); tw.join(30)
        assert errors == [] and all(r >= 10 for r in read_results)

# ═══════════════════════════════════════════════════════════
#  16. TIMESTAMP HANDLING
# ═══════════════════════════════════════════════════════════

class TestTimestampHandling:
    def test_utc_roundtrip(self, mem):
        dt = datetime(2026, 6, 20, 15, 30, 45, tzinfo=timezone.utc)
        mem.store(_make_entry(timestamp=dt))
        assert mem.recall(USER_A)[0].timestamp == dt

    def test_naive_treated_as_utc(self, mem):
        mem.store(_make_entry(timestamp=datetime(2026, 6, 20, 15, 30, 45)))
        assert mem.recall(USER_A)[0].timestamp.tzinfo == timezone.utc

    def test_ordering_microseconds(self, mem):
        dt1 = datetime(2026, 6, 20, 10, 0, 0, 0, tzinfo=timezone.utc)
        dt2 = datetime(2026, 6, 20, 10, 0, 0, 500000, tzinfo=timezone.utc)
        mem.store(_make_entry(timestamp=dt1, entry_id="e1", topic="first"))
        mem.store(_make_entry(timestamp=dt2, entry_id="e2", topic="second"))
        assert mem.recall(USER_A)[0].topic == "second"

# ═══════════════════════════════════════════════════════════
#  17. DIRECTORY CREATION
# ═══════════════════════════════════════════════════════════

class TestDirectoryCreation:
    def test_creates_nested(self):
        d = tempfile.mkdtemp(prefix="aatif_par_")
        try:
            sub = os.path.join(d, "nested", "deep")
            mem = TemporalMemory(sub)
            assert os.path.isdir(sub)
            mem.store(_make_entry())
            assert mem.count(USER_A) == 1
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_existing_dir(self, tmp_dir):
        TemporalMemory(tmp_dir).store(_make_entry())

# ═══════════════════════════════════════════════════════════
#  18. COUNT METHOD
# ═══════════════════════════════════════════════════════════

class TestCount:
    def test_count_by_user(self, mem):
        for i in range(3):
            mem.store(_make_entry(timestamp=BASE_DT + timedelta(hours=i), entry_id=f"e{i}"))
        assert mem.count(USER_A) == 3

    def test_count_all(self, mem):
        mem.store(_make_entry(user_id=USER_A, entry_id="a1"))
        mem.store(_make_entry(user_id=USER_B, entry_id="b1"))
        assert mem.count() == 2

    def test_count_empty(self, mem):
        assert mem.count() == 0

# ═══════════════════════════════════════════════════════════
#  19. TIME PERIOD CONTEXT
# ═══════════════════════════════════════════════════════════

class TestTimePeriodContext:
    def test_single_period(self, mem):
        mem.store(_make_entry(time_period="فجر"))
        assert mem.get_context(USER_A).time_pattern == {"فجر": 1}

    def test_mixed_periods(self, mem):
        for i, p in enumerate(["فجر", "صباح", "صباح", "مساء"]):
            mem.store(_make_entry(time_period=p, timestamp=BASE_DT + timedelta(hours=i),
                                  entry_id=f"e{i}"))
        assert mem.get_context(USER_A).time_pattern["صباح"] == 2

    def test_empty_excluded(self, mem):
        mem.store(_make_entry(time_period=""))
        assert mem.get_context(USER_A).time_pattern == {}

# ═══════════════════════════════════════════════════════════
#  20. MESSAGE ROLE
# ═══════════════════════════════════════════════════════════

class TestMessageRole:
    def test_user_role(self, mem):
        mem.store(_make_entry(message_role="user"))
        assert mem.recall(USER_A)[0].message_role == "user"

    def test_assistant_role(self, mem):
        mem.store(_make_entry(message_role="assistant"))
        assert mem.recall(USER_A)[0].message_role == "assistant"

    def test_both_roles(self, mem):
        mem.store(_make_entry(message_role="user", entry_id="u1", timestamp=BASE_DT))
        mem.store(_make_entry(message_role="assistant", entry_id="a1",
                              timestamp=BASE_DT + timedelta(seconds=5)))
        assert mem.count(USER_A) == 2

# ═══════════════════════════════════════════════════════════
#  21. CONTEXT + GREETING CONSISTENCY
# ═══════════════════════════════════════════════════════════

class TestContextGreetingConsistency:
    def test_first_time(self, mem):
        ctx = mem.get_context("newbie")
        assert ctx.interaction_gap_assessment == "first_time"
        assert ctx.suggested_greeting == GREETING_FIRST_TIME

    def test_session(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(minutes=5)))
        ctx = mem.get_context(USER_A)
        assert ctx.interaction_gap_assessment == "continuing_session"
        assert ctx.suggested_greeting == GREETING_SAME_SESSION

    def test_absence(self, mem):
        mem.store(_make_entry(timestamp=datetime.now(timezone.utc) - timedelta(days=20)))
        ctx = mem.get_context(USER_A)
        assert ctx.interaction_gap_assessment == "returning_after_absence"
        assert ctx.suggested_greeting == GREETING_LONG_GAP

# ═══════════════════════════════════════════════════════════
#  22. DATACLASS DEFAULTS
# ═══════════════════════════════════════════════════════════

class TestMemoryEntryDefaults:
    def test_default_scores_none(self):
        e = MemoryEntry(entry_id="x", user_id="u", timestamp=BASE_DT,
                        time_period="", message_role="user",
                        message_summary="", topic="")
        assert e.intent_score is None and e.harm_score is None
        assert e.emotion_score is None and e.s_decision is None

    def test_default_booleans_false(self):
        e = MemoryEntry(entry_id="x", user_id="u", timestamp=BASE_DT,
                        time_period="", message_role="user",
                        message_summary="", topic="")
        assert not e.was_repeat_question
        assert not e.confusion_detected
        assert not e.resolution_achieved

# ═══════════════════════════════════════════════════════════
#  23. TEMPORAL CONTEXT FIELDS
# ═══════════════════════════════════════════════════════════

class TestTemporalContextDataclass:
    def test_all_fields_populated(self, mem):
        for i in range(5):
            mem.store(_make_entry(
                timestamp=datetime.now(timezone.utc) - timedelta(hours=5 - i),
                time_period="صباح", topic="python", emotion_score=0.5,
                s_decision="EXECUTE", entry_id=f"e{i}"))
        ctx = mem.get_context(USER_A)
        assert ctx.user_id == USER_A
        assert ctx.total_interactions == 5
        assert ctx.first_interaction is not None
        assert ctx.last_interaction is not None
        assert ctx.days_since_last is not None and ctx.days_since_last < 1.0
        assert isinstance(ctx.recent_topics, list)
        assert isinstance(ctx.unresolved_topics, list)
        assert isinstance(ctx.topic_frequency, dict)
        assert isinstance(ctx.time_pattern, dict)
        assert isinstance(ctx.recent_decisions, list)
        assert ctx.emotional_trajectory in ("improving", "stable", "declining", "insufficient_data")
        assert isinstance(ctx.suggested_greeting, str)


# ═══════════════════════════════════════════════════════════
#  24. SESSION BOUNDARY DETECTION
# ═══════════════════════════════════════════════════════════

class TestSessionBoundary:
    """
    Tests for the session_id auto-assignment via _resolve_session_id().

    Session boundary logic (consensus fix #5):
      - Gap <= 30 minutes → same session (reuse session_id)
      - Gap > 30 minutes  → new session (new UUID)
      - Explicit session_id on entry → preserved, not overwritten
    """

    def test_same_session_within_30min(self, mem):
        """Two entries 10 min apart should share the same session_id."""
        mem.store(_make_entry(timestamp=BASE_DT, entry_id="s1"))
        mem.store(_make_entry(timestamp=BASE_DT + timedelta(minutes=10), entry_id="s2"))
        entries = mem.recall(USER_A, limit=10)
        assert len(entries) == 2
        sid_1 = entries[0].session_id
        sid_2 = entries[1].session_id
        assert sid_1 is not None and sid_1 != ""
        assert sid_2 is not None and sid_2 != ""
        assert sid_1 == sid_2

    def test_new_session_after_30min_gap(self, mem):
        """Two entries 45 min apart should get different session_ids."""
        mem.store(_make_entry(timestamp=BASE_DT, entry_id="g1"))
        mem.store(_make_entry(timestamp=BASE_DT + timedelta(minutes=45), entry_id="g2"))
        entries = mem.recall(USER_A, limit=10)
        assert len(entries) == 2
        sids = {e.session_id for e in entries}
        assert all(s is not None and s != "" for s in sids)
        assert len(sids) == 2, "Expected 2 distinct session_ids for 45-min gap"

    def test_session_id_is_uuid_format(self, mem):
        """Auto-assigned session_id should be a valid UUID (36 chars, hyphens at positions 8,13,18,23)."""
        mem.store(_make_entry(timestamp=BASE_DT, entry_id="u1"))
        entries = mem.recall(USER_A, limit=1)
        sid = entries[0].session_id
        assert sid is not None
        assert len(sid) == 36, f"UUID should be 36 chars, got {len(sid)}"
        assert sid[8] == "-" and sid[13] == "-" and sid[18] == "-" and sid[23] == "-"
        # Verify it's parseable as a UUID
        parsed = uuid.UUID(sid)
        assert str(parsed) == sid

    def test_explicit_session_id_preserved(self, mem):
        """When session_id is set explicitly, store() should NOT overwrite it."""
        entry = _make_entry(timestamp=BASE_DT, entry_id="ex1")
        entry.session_id = "my-custom-session"
        mem.store(entry)
        recalled = mem.recall(USER_A, limit=1)
        assert recalled[0].session_id == "my-custom-session"

    def test_multiple_sessions_across_gap(self, mem):
        """3 entries 5 min apart (session A), then 3 entries 60 min later (session B).
        Should produce exactly 2 distinct session_ids."""
        # Session A: entries at t+0, t+5, t+10
        for i in range(3):
            mem.store(_make_entry(
                timestamp=BASE_DT + timedelta(minutes=i * 5),
                entry_id=f"sa{i}",
            ))
        # Session B: entries at t+70, t+75, t+80 (60 min gap from t+10)
        for i in range(3):
            mem.store(_make_entry(
                timestamp=BASE_DT + timedelta(minutes=70 + i * 5),
                entry_id=f"sb{i}",
            ))
        entries = mem.recall(USER_A, limit=20)
        assert len(entries) == 6
        sids = {e.session_id for e in entries}
        assert all(s is not None and s != "" for s in sids)
        assert len(sids) == 2, f"Expected 2 distinct sessions, got {len(sids)}: {sids}"

    def test_different_users_independent_sessions(self, mem):
        """Entries for USER_A and USER_B at the same time should get independent session_ids."""
        mem.store(_make_entry(user_id=USER_A, timestamp=BASE_DT, entry_id="ua1"))
        mem.store(_make_entry(user_id=USER_B, timestamp=BASE_DT, entry_id="ub1"))
        entries_a = mem.recall(USER_A, limit=1)
        entries_b = mem.recall(USER_B, limit=1)
        sid_a = entries_a[0].session_id
        sid_b = entries_b[0].session_id
        assert sid_a is not None and sid_a != ""
        assert sid_b is not None and sid_b != ""
        # Each user's first entry starts its own session — different UUIDs
        assert sid_a != sid_b, "Different users should get independent session_ids"


# ═══════════════════════════════════════════════════════════
#  25. SCHEMA MIGRATION
# ═══════════════════════════════════════════════════════════

class TestSchemaMigration:
    """
    Tests for the idempotent schema migration in _init_db().

    The ALTER TABLE for session_id is wrapped in try/except so it's safe
    to run on both fresh databases and existing ones.
    """

    def test_existing_db_without_session_id(self, tmp_dir):
        """Re-opening the same database should be idempotent — migration runs safely
        on a DB that already has the session_id column. Both old and new entries
        should be accessible."""
        # First instance: store an entry
        m1 = TemporalMemory(tmp_dir)
        m1.store(_make_entry(timestamp=BASE_DT, entry_id="mig1", topic="before"))

        # Second instance on the same directory — _init_db() runs again,
        # ALTER TABLE hits the "column already exists" path
        m2 = TemporalMemory(tmp_dir)
        m2.store(_make_entry(timestamp=BASE_DT + timedelta(hours=1),
                             entry_id="mig2", topic="after"))

        # Both entries should be accessible
        entries = m2.recall(USER_A, limit=10)
        assert len(entries) == 2
        topics = {e.topic for e in entries}
        assert "before" in topics and "after" in topics

        # Both should have session_ids
        for e in entries:
            assert e.session_id is not None and e.session_id != ""
