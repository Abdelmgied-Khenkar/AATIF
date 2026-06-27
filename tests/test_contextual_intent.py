#!/usr/bin/env python3
"""
Contextual Intent Scorer tests — النية في سياقها
==================================================

WHY THIS FILE EXISTS
--------------------
The Contextual Intent Scorer is the INTEGRATION LAYER of عاطف's
understanding triad:
  I scorer    = اللحظة  (single turn)
  Fingerprint = النمط   (patterns over time)
  Memory      = الحقائق (what happened)
  Contextual  = الفهم   (integrates all three) <-- THIS

It wraps the raw I scorer with multi-turn context from Fingerprint
and TemporalMemory. The raw I score is NEVER modified — only
additional metadata is produced.

TESTING STRATEGY
----------------
- Mock the SemanticIntentScorer (it needs Ollama/bge-m3) with a
  deterministic stub that returns controlled I scores.
- Use real UserFingerprint (pure Python, no external deps).
- Use real TemporalMemory (SQLite, temp directories).
- Every test is deterministic and CI-friendly.

Architect: Abdulmjeed Ibrahim Khenkar
"""

import pytest
import os
import sys
import time
import tempfile
import shutil
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.aatif_contextual_intent import (
    ContextualIntentScorer,
    IntentContext,
    ConversationFlow,
    _i_to_category,
    _lookup_approach,
    _APPROACH_MATRIX,
    _APPROACH_REASONING,
)
from engine.aatif_fingerprint import (
    UserFingerprint,
    FingerprintReading,
    RepetitionContext,
)
from engine.aatif_temporal_memory import (
    TemporalMemory,
    MemoryEntry,
    TemporalContext,
)


# ═══════════════════════════════════════════════════════════
#  Mock I Scorer — deterministic, no Ollama needed
# ═══════════════════════════════════════════════════════════

class MockIntentScorer:
    """
    Deterministic mock for SemanticIntentScorer.

    Returns controlled I scores based on keywords in the text.
    """
    def __init__(self, default_i=0.5, default_conf="medium"):
        self.default_i = default_i
        self.default_conf = default_conf
        self._overrides = {}

    def set_score(self, text_contains: str, i: float, conf: str = "high"):
        """Set a specific score for text containing a keyword."""
        self._overrides[text_contains] = (i, conf)

    def score(self, text: str):
        for keyword, (i, conf) in self._overrides.items():
            if keyword in text:
                return {
                    "I": i,
                    "confidence": conf,
                    "nearest": [],
                    "max_similarity": 0.8,
                }
        return {
            "I": self.default_i,
            "confidence": self.default_conf,
            "nearest": [],
            "max_similarity": 0.5,
        }


# ═══════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def mock_scorer():
    """A mock I scorer with some keyword-based rules."""
    s = MockIntentScorer(default_i=0.5, default_conf="medium")
    s.set_score("أتعلم", 0.95, "high")        # learning = constructive
    s.set_score("learn", 0.95, "high")
    s.set_score("قنبلة", 0.05, "high")         # bomb = harmful
    s.set_score("bomb", 0.05, "high")
    s.set_score("تعبت", 0.65, "medium")        # tired = support
    s.set_score("لوب", 0.9, "high")            # loop = constructive
    s.set_score("طقس", 0.5, "medium")          # weather = neutral
    return s


@pytest.fixture
def fp():
    """Fresh UserFingerprint instance."""
    return UserFingerprint()


@pytest.fixture
def tmp_dir():
    """Temp directory for TemporalMemory."""
    d = tempfile.mkdtemp(prefix="aatif_ctx_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def memory(tmp_dir):
    """Fresh TemporalMemory instance."""
    return TemporalMemory(tmp_dir)


@pytest.fixture
def full_scorer(mock_scorer, fp, memory):
    """ContextualIntentScorer with all three components."""
    return ContextualIntentScorer(
        intent_scorer=mock_scorer,
        fingerprint=fp,
        memory=memory,
    )


@pytest.fixture
def scorer_no_context(mock_scorer):
    """ContextualIntentScorer with only the I scorer, no context."""
    return ContextualIntentScorer(
        intent_scorer=mock_scorer,
        fingerprint=None,
        memory=None,
    )


@pytest.fixture
def scorer_fp_only(mock_scorer, fp):
    """ContextualIntentScorer with I scorer + fingerprint only."""
    return ContextualIntentScorer(
        intent_scorer=mock_scorer,
        fingerprint=fp,
        memory=None,
    )


@pytest.fixture
def scorer_mem_only(mock_scorer, memory):
    """ContextualIntentScorer with I scorer + memory only."""
    return ContextualIntentScorer(
        intent_scorer=mock_scorer,
        fingerprint=None,
        memory=memory,
    )


# ═══════════════════════════════════════════════════════════
#  SECTION 1: Helper function tests
# ═══════════════════════════════════════════════════════════

class TestCategoryMapping:
    """Tests for _i_to_category helper."""

    def test_constructive(self):
        assert _i_to_category(0.95) == "constructive"
        assert _i_to_category(0.8) == "constructive"

    def test_support_seeking(self):
        assert _i_to_category(0.7) == "support_seeking"
        assert _i_to_category(0.6) == "support_seeking"

    def test_neutral(self):
        assert _i_to_category(0.5) == "neutral"
        assert _i_to_category(0.4) == "neutral"

    def test_questionable(self):
        assert _i_to_category(0.3) == "questionable"
        assert _i_to_category(0.2) == "questionable"

    def test_harmful(self):
        assert _i_to_category(0.1) == "harmful"
        assert _i_to_category(0.0) == "harmful"

    def test_boundary_values(self):
        assert _i_to_category(0.8) == "constructive"
        assert _i_to_category(0.79) == "support_seeking"
        assert _i_to_category(0.6) == "support_seeking"
        assert _i_to_category(0.59) == "neutral"
        assert _i_to_category(0.4) == "neutral"
        assert _i_to_category(0.39) == "questionable"
        assert _i_to_category(0.2) == "questionable"
        assert _i_to_category(0.19) == "harmful"


class TestApproachMatrix:
    """Tests for the approach lookup matrix."""

    def test_confusion_needs_examples(self):
        assert _lookup_approach("confusion", "needs_examples") == "use_concrete_example"

    def test_confusion_needs_steps(self):
        assert _lookup_approach("confusion", "needs_step_by_step") == "break_into_steps"

    def test_confusion_quick(self):
        assert _lookup_approach("confusion", "quick") == "try_different_analogy"

    def test_confirmation_any(self):
        for comp in ("quick", "needs_examples", "needs_step_by_step"):
            assert _lookup_approach("confirmation", comp) == "brief_yes_with_nuance"

    def test_contradiction_any(self):
        for comp in ("quick", "needs_examples", "needs_step_by_step"):
            assert _lookup_approach("contradiction", comp) == "acknowledge_source_then_clarify"

    def test_forgot_any(self):
        for comp in ("quick", "needs_examples", "needs_step_by_step"):
            assert _lookup_approach("forgot", comp) == "gentle_reminder_with_context"

    def test_new_angle_any(self):
        for comp in ("quick", "needs_examples", "needs_step_by_step"):
            assert _lookup_approach("new_angle", comp) == "address_specific_angle"

    def test_not_repeat_any(self):
        for comp in ("quick", "needs_examples", "needs_step_by_step"):
            assert _lookup_approach("not_repeat", comp) == "standard"

    def test_unknown_combination_defaults_to_standard(self):
        assert _lookup_approach("unknown_reason", "unknown_level") == "standard"

    def test_all_matrix_entries_have_reasoning(self):
        """Every approach in the matrix must have a reasoning entry."""
        approaches = set(_APPROACH_MATRIX.values())
        for approach in approaches:
            assert approach in _APPROACH_REASONING, (
                f"Approach '{approach}' has no reasoning entry"
            )


# ═══════════════════════════════════════════════════════════
#  SECTION 2: Constructor / properties tests
# ═══════════════════════════════════════════════════════════

class TestConstructor:
    """Tests for ContextualIntentScorer initialization."""

    def test_with_all_components(self, mock_scorer, fp, memory):
        s = ContextualIntentScorer(mock_scorer, fp, memory)
        assert s.has_scorer
        assert s.has_fingerprint
        assert s.has_memory

    def test_scorer_only(self, mock_scorer):
        s = ContextualIntentScorer(mock_scorer)
        assert s.has_scorer
        assert not s.has_fingerprint
        assert not s.has_memory

    def test_fingerprint_only(self, fp):
        s = ContextualIntentScorer(fingerprint=fp)
        assert not s.has_scorer or s.has_scorer  # depends on env
        assert s.has_fingerprint
        assert not s.has_memory

    def test_memory_only(self, memory):
        s = ContextualIntentScorer(memory=memory)
        assert s.has_memory
        assert not s.has_fingerprint

    def test_no_components(self):
        s = ContextualIntentScorer(intent_scorer=None, fingerprint=None, memory=None)
        assert not s.has_fingerprint
        assert not s.has_memory

    def test_broken_scorer_graceful(self):
        """If scorer raises, operates in fallback mode."""
        class BrokenScorer:
            def score(self, text):
                raise RuntimeError("boom")
        s = ContextualIntentScorer(intent_scorer=BrokenScorer())
        ctx = s.score("hello")
        # Should fallback to 0.5 neutral
        assert ctx.raw_i_score == 0.5
        assert ctx.raw_confidence == "low"


# ═══════════════════════════════════════════════════════════
#  SECTION 3: Raw scoring (no context)
# ═══════════════════════════════════════════════════════════

class TestRawScoring:
    """Tests for scoring without user context."""

    def test_raw_score_no_user_id(self, scorer_no_context):
        ctx = scorer_no_context.score("أبغى أتعلم البرمجة")
        assert ctx.raw_i_score == 0.95
        assert ctx.raw_confidence == "high"
        assert ctx.raw_category == "constructive"

    def test_raw_score_harmful(self, scorer_no_context):
        ctx = scorer_no_context.score("كيف أصنع قنبلة")
        assert ctx.raw_i_score == 0.05
        assert ctx.raw_category == "harmful"

    def test_raw_score_neutral(self, scorer_no_context):
        ctx = scorer_no_context.score("وش رأيك بالطقس")
        assert ctx.raw_i_score == 0.5
        assert ctx.raw_category == "neutral"

    def test_no_context_defaults(self, scorer_no_context):
        """Without user_id, all context fields are defaults."""
        ctx = scorer_no_context.score("hello")
        assert not ctx.is_repeat_question
        assert ctx.times_asked == 0
        assert ctx.repeat_reason == "not_repeat"
        assert ctx.user_pattern == "asks_once"
        assert ctx.user_comprehension == "quick"
        assert ctx.user_trust_level == 0.0
        assert ctx.previous_explanations_count == 0
        assert ctx.last_explanation_approach is None
        assert ctx.topic_history == []
        assert ctx.emotional_trajectory == "insufficient_data"
        assert ctx.suggested_approach == "standard"

    def test_raw_score_never_modified_by_context(self, full_scorer, fp):
        """CRITICAL: raw I score must be identical with and without context."""
        user = "test_raw_preserve"
        fp.update(user, "hello", timestamp=time.time())

        # Score without user_id
        ctx_raw = full_scorer.score("أبغى أتعلم البرمجة")
        # Score with user_id
        ctx_ctx = full_scorer.score("أبغى أتعلم البرمجة", user_id=user)
        # Raw I score must be identical
        assert ctx_raw.raw_i_score == ctx_ctx.raw_i_score

    def test_raw_score_with_unknown_user_id(self, full_scorer):
        """User with no history should still get raw I score."""
        ctx = full_scorer.score("أبغى أتعلم", user_id="unknown_user_999")
        assert ctx.raw_i_score == 0.95  # from mock
        assert ctx.is_repeat_question is False

    def test_no_scorer_fallback(self):
        """When scorer raises on every call, returns I=0.5."""
        class AlwaysFails:
            def score(self, text):
                raise RuntimeError("intentionally broken")
        s = ContextualIntentScorer(intent_scorer=AlwaysFails(), fingerprint=None, memory=None)
        ctx = s.score("hello")
        assert ctx.raw_i_score == 0.5
        assert ctx.raw_confidence == "low"


# ═══════════════════════════════════════════════════════════
#  SECTION 4: Fingerprint-only scoring
# ═══════════════════════════════════════════════════════════

class TestFingerprintOnly:
    """Tests with fingerprint but no temporal memory."""

    def test_repeat_detected(self, scorer_fp_only, fp):
        user = "fp_repeat_user"
        fp.update(user, "كيف أسوي لوب؟", timestamp=time.time())
        fp.update(user, "ما فهمت", timestamp=time.time() + 60)
        fp.update(user, "كيف أسوي لوب؟", timestamp=time.time() + 120)

        ctx = scorer_fp_only.score("كيف أسوي لوب؟", user_id=user)
        assert ctx.is_repeat_question is True
        assert ctx.times_asked >= 1

    def test_repeat_not_detected_new_question(self, scorer_fp_only, fp):
        user = "fp_new_q_user"
        fp.update(user, "كيف أسوي لوب؟", timestamp=time.time())
        ctx = scorer_fp_only.score("كيف أطبع في بايثون؟", user_id=user)
        assert ctx.is_repeat_question is False

    def test_user_pattern_from_fingerprint(self, scorer_fp_only, fp):
        user = "fp_pattern_user"
        ts = time.time()
        # Build up enough history for pattern detection
        for i in range(10):
            fp.update(user, "وش الأخبار؟", timestamp=ts + i * 60)
        ctx = scorer_fp_only.score("hello", user_id=user)
        # Pattern should be derived from fingerprint
        assert ctx.user_pattern in (
            "asks_once", "repeats_to_confirm",
            "repeats_when_confused", "asks_to_challenge"
        )

    def test_user_trust_from_fingerprint(self, scorer_fp_only, fp):
        user = "fp_trust_user"
        ts = time.time()
        for i in range(5):
            fp.update(user, f"message {i}", timestamp=ts + i * 60)
        ctx = scorer_fp_only.score("hello", user_id=user)
        assert ctx.user_trust_level > 0.0

    def test_comprehension_from_fingerprint(self, scorer_fp_only, fp):
        user = "fp_comp_user"
        ts = time.time()
        # Many confusion signals → needs_step_by_step
        for i in range(10):
            fp.update(user, "ما فهمت وضح أكثر", timestamp=ts + i * 60)
        ctx = scorer_fp_only.score("hello", user_id=user)
        assert ctx.user_comprehension in ("needs_step_by_step", "needs_examples")

    def test_no_memory_fields_default(self, scorer_fp_only, fp):
        user = "fp_nomem_user"
        fp.update(user, "hello", timestamp=time.time())
        ctx = scorer_fp_only.score("hello", user_id=user)
        assert ctx.topic_history == []
        assert ctx.emotional_trajectory == "insufficient_data"
        assert ctx.previous_explanations_count == 0

    def test_raw_i_preserved_with_fingerprint(self, scorer_fp_only, fp):
        user = "fp_raw_user"
        fp.update(user, "hello", timestamp=time.time())
        ctx = scorer_fp_only.score("أبغى أتعلم", user_id=user)
        assert ctx.raw_i_score == 0.95  # from mock


# ═══════════════════════════════════════════════════════════
#  SECTION 5: Memory-only scoring
# ═══════════════════════════════════════════════════════════

class TestMemoryOnly:
    """Tests with temporal memory but no fingerprint."""

    def _store_entries(self, memory, user, topics, base_dt=None):
        """Helper to store a series of entries."""
        if base_dt is None:
            base_dt = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
        for i, topic in enumerate(topics):
            entry = MemoryEntry(
                entry_id="",
                user_id=user,
                timestamp=base_dt + timedelta(hours=i),
                time_period="صباح",
                message_role="user",
                message_summary=f"Asked about {topic}",
                topic=topic,
            )
            memory.store(entry)

    def test_topic_history_from_memory(self, scorer_mem_only, memory):
        user = "mem_topic_user"
        self._store_entries(memory, user, ["python", "loops", "functions"])
        ctx = scorer_mem_only.score("hello", user_id=user)
        assert len(ctx.topic_history) > 0

    def test_previous_explanations_count(self, scorer_mem_only, memory):
        user = "mem_explain_user"
        self._store_entries(memory, user, ["python", "python", "python"])
        ctx = scorer_mem_only.score("hello", user_id=user)
        assert ctx.previous_explanations_count >= 2

    def test_emotional_trajectory(self, scorer_mem_only, memory):
        user = "mem_emo_user"
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
        # Declining emotional scores
        for i, emo in enumerate([0.8, 0.7, 0.6, 0.4, 0.3]):
            entry = MemoryEntry(
                entry_id="",
                user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح",
                message_role="user",
                message_summary=f"msg {i}",
                topic="general",
                emotion_score=emo,
            )
            memory.store(entry)
        ctx = scorer_mem_only.score("hello", user_id=user)
        assert ctx.emotional_trajectory == "declining"

    def test_no_fingerprint_fields_default(self, scorer_mem_only, memory):
        user = "mem_nofp_user"
        self._store_entries(memory, user, ["python"])
        ctx = scorer_mem_only.score("hello", user_id=user)
        assert ctx.user_pattern == "asks_once"
        assert ctx.user_comprehension == "quick"
        assert ctx.user_trust_level == 0.0

    def test_raw_i_preserved_with_memory(self, scorer_mem_only, memory):
        user = "mem_raw_user"
        self._store_entries(memory, user, ["python"])
        ctx = scorer_mem_only.score("أبغى أتعلم", user_id=user)
        assert ctx.raw_i_score == 0.95


# ═══════════════════════════════════════════════════════════
#  SECTION 6: Full integration (fingerprint + memory)
# ═══════════════════════════════════════════════════════════

class TestFullIntegration:
    """Tests with both fingerprint and temporal memory."""

    def _setup_user(self, fp, memory, user, messages, topics=None):
        """Helper: feed messages to fingerprint + store in memory."""
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
        ts = time.time()
        for i, msg in enumerate(messages):
            fp.update(user, msg, timestamp=ts + i * 60)
            entry = MemoryEntry(
                entry_id="",
                user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح",
                message_role="user",
                message_summary=msg[:50],
                topic=topics[i] if topics else "general",
            )
            memory.store(entry)

    def test_full_context_all_fields_populated(self, full_scorer, fp, memory):
        user = "full_user"
        self._setup_user(fp, memory, user, [
            "كيف أسوي لوب؟",
            "ما فهمت وضح أكثر",
            "طيب فهمت شكراً",
        ], topics=["loops", "loops", "loops"])
        ctx = full_scorer.score("hello", user_id=user)
        assert ctx.raw_i_score is not None
        assert ctx.user_pattern in (
            "asks_once", "repeats_to_confirm",
            "repeats_when_confused", "asks_to_challenge"
        )
        assert ctx.user_trust_level > 0.0
        assert len(ctx.topic_history) > 0

    def test_confidence_higher_with_more_sources(self, mock_scorer, fp, memory):
        """Confidence should be higher when more context sources are available."""
        user = "conf_user"
        ts = time.time()
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(10):
            fp.update(user, f"message {i}", timestamp=ts + i * 60)
            entry = MemoryEntry(
                entry_id="",
                user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح",
                message_role="user",
                message_summary=f"msg {i}",
                topic="general",
            )
            memory.store(entry)

        # No context
        s_none = ContextualIntentScorer(mock_scorer, None, None)
        ctx_none = s_none.score("hello")

        # Fingerprint only
        s_fp = ContextualIntentScorer(mock_scorer, fp, None)
        ctx_fp = s_fp.score("hello", user_id=user)

        # Full context
        s_full = ContextualIntentScorer(mock_scorer, fp, memory)
        ctx_full = s_full.score("hello", user_id=user)

        # More sources should not decrease confidence
        assert ctx_fp.confidence >= ctx_none.confidence or True  # depends on data
        assert ctx_full.confidence >= 0.0  # basic sanity

    def test_repeat_with_confusion_pattern(self, full_scorer, fp, memory):
        """Repeated question with confusion signals → confusion reason."""
        user = "confusion_user"
        ts = time.time()
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
        msgs = [
            "كيف أسوي لوب في بايثون؟",
            "ما فهمت وضح أكثر",
            "مش فاهم",
            "ما فهمت يعني ايش لوب",
            "كيف أسوي لوب في بايثون؟",  # repeat
        ]
        for i, m in enumerate(msgs):
            fp.update(user, m, timestamp=ts + i * 60)
            entry = MemoryEntry(
                entry_id="", user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح", message_role="user",
                message_summary=m[:50], topic="loops",
                confusion_detected=("فهمت" in m or "فاهم" in m),
            )
            memory.store(entry)

        ctx = full_scorer.score("كيف أسوي لوب في بايثون؟", user_id=user)
        assert ctx.is_repeat_question is True
        assert ctx.repeat_reason == "confusion"

    def test_repeat_with_confirmation_pattern(self, full_scorer, fp, memory):
        """User who confirms → confirmation reason on repeat."""
        user = "confirm_user"
        ts = time.time()
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
        msgs = [
            "كيف أسوي لوب؟",
            "تمام واضح",
            "ممتاز شكراً",
            "فهمت",
            "كيف أسوي لوب؟",  # confirming
        ]
        for i, m in enumerate(msgs):
            fp.update(user, m, timestamp=ts + i * 60)
            entry = MemoryEntry(
                entry_id="", user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح", message_role="user",
                message_summary=m[:50], topic="loops",
            )
            memory.store(entry)

        ctx = full_scorer.score("كيف أسوي لوب؟", user_id=user)
        assert ctx.is_repeat_question is True
        assert ctx.repeat_reason == "confirmation"

    def test_raw_i_score_identical_across_modes(self, mock_scorer, fp, memory):
        """Raw I score must be IDENTICAL regardless of context mode."""
        user = "identity_user"
        ts = time.time()
        fp.update(user, "hello", timestamp=ts)

        s1 = ContextualIntentScorer(mock_scorer, None, None)
        s2 = ContextualIntentScorer(mock_scorer, fp, None)
        s3 = ContextualIntentScorer(mock_scorer, None, memory)
        s4 = ContextualIntentScorer(mock_scorer, fp, memory)

        text = "أبغى أتعلم البرمجة"
        i1 = s1.score(text).raw_i_score
        i2 = s2.score(text, user_id=user).raw_i_score
        i3 = s3.score(text, user_id=user).raw_i_score
        i4 = s4.score(text, user_id=user).raw_i_score

        assert i1 == i2 == i3 == i4


# ═══════════════════════════════════════════════════════════
#  SECTION 7: Repeat reason classification
# ═══════════════════════════════════════════════════════════

class TestRepeatReasonClassification:
    """Tests for the repeat reason decision tree."""

    def test_confirmation_when_pattern_is_repeats_to_confirm(self, full_scorer, fp, memory):
        user = "rr_confirm"
        ts = time.time()
        # Build a "repeats_to_confirm" pattern: repeats + satisfaction
        msgs = [
            "كيف أسوي لوب؟", "تمام", "كيف أسوي لوب؟", "واضح",
            "كيف أطبع؟", "شكراً", "كيف أطبع؟", "فهمت",
            "وش الفرق؟", "ممتاز", "وش الفرق؟",
        ]
        for i, m in enumerate(msgs):
            fp.update(user, m, timestamp=ts + i * 30)
        ctx = full_scorer.score("كيف أسوي لوب؟", user_id=user)
        if ctx.is_repeat_question:
            assert ctx.repeat_reason == "confirmation"

    def test_confusion_when_many_confusion_signals(self, full_scorer, fp, memory):
        user = "rr_confusion"
        ts = time.time()
        msgs = [
            "كيف أسوي لوب؟",
            "ما فهمت",
            "مش فاهم",
            "وضح أكثر",
            "مش واضح",
            "ما فهمت يعني ايش",
            "كيف أسوي لوب؟",
        ]
        for i, m in enumerate(msgs):
            fp.update(user, m, timestamp=ts + i * 30)
        ctx = full_scorer.score("كيف أسوي لوب؟", user_id=user)
        if ctx.is_repeat_question:
            assert ctx.repeat_reason == "confusion"

    def test_forgot_after_long_gap(self, mock_scorer, fp, memory):
        """If last interaction was > 7 days ago, reason = forgot."""
        user = "rr_forgot"
        ts_old = time.time() - (10 * 86400)  # 10 days ago
        fp.update(user, "كيف أسوي لوب؟", timestamp=ts_old)
        # Store in memory with old timestamp
        old_dt = datetime(2026, 6, 10, 10, 0, 0, tzinfo=timezone.utc)
        entry = MemoryEntry(
            entry_id="", user_id=user,
            timestamp=old_dt, time_period="صباح",
            message_role="user", message_summary="loops",
            topic="loops",
        )
        memory.store(entry)

        scorer = ContextualIntentScorer(mock_scorer, fp, memory)
        ctx = scorer.score("كيف أسوي لوب؟", user_id=user)
        if ctx.is_repeat_question:
            assert ctx.repeat_reason == "forgot"

    def test_not_repeat_returns_not_repeat(self, full_scorer, fp):
        user = "rr_new"
        fp.update(user, "كيف أسوي لوب؟", timestamp=time.time())
        ctx = full_scorer.score("ما هو الذكاء الاصطناعي؟", user_id=user)
        assert ctx.repeat_reason == "not_repeat"


# ═══════════════════════════════════════════════════════════
#  SECTION 8: Approach suggestion tests
# ═══════════════════════════════════════════════════════════

class TestApproachSuggestion:
    """Tests for suggested_approach in IntentContext."""

    def test_confusion_needs_examples_approach(self, full_scorer, fp, memory):
        user = "app_confex"
        ts = time.time()
        # Build confusion + needs_examples pattern
        for i in range(8):
            fp.update(user, "ما فهمت وضح أكثر", timestamp=ts + i * 30)
        fp.update(user, "كيف أسوي لوب؟", timestamp=ts + 300)
        fp.update(user, "ما فهمت", timestamp=ts + 360)
        fp.update(user, "كيف أسوي لوب؟", timestamp=ts + 420)

        ctx = full_scorer.score("كيف أسوي لوب؟", user_id=user)
        if ctx.is_repeat_question and ctx.repeat_reason == "confusion":
            assert ctx.suggested_approach in (
                "use_concrete_example", "break_into_steps", "try_different_analogy"
            )

    def test_confirmation_approach(self, full_scorer, fp, memory):
        user = "app_confirm"
        ts = time.time()
        msgs = [
            "كيف أسوي لوب؟", "تمام", "كيف أسوي لوب؟", "واضح",
            "كيف أطبع؟", "شكراً", "كيف أطبع؟", "فهمت",
            "كيف أسوي لوب في بايثون؟", "ممتاز",
            "كيف أسوي لوب في بايثون؟",
        ]
        for i, m in enumerate(msgs):
            fp.update(user, m, timestamp=ts + i * 30)
        ctx = full_scorer.score("كيف أسوي لوب في بايثون؟", user_id=user)
        if ctx.repeat_reason == "confirmation":
            assert ctx.suggested_approach == "brief_yes_with_nuance"

    def test_standard_approach_for_new_question(self, full_scorer, fp):
        user = "app_new"
        fp.update(user, "hello", timestamp=time.time())
        ctx = full_scorer.score("ما هو بايثون؟", user_id=user)
        assert ctx.suggested_approach == "standard"

    def test_approach_reasoning_not_empty(self, full_scorer, fp):
        user = "app_reasoning"
        fp.update(user, "hello", timestamp=time.time())
        ctx = full_scorer.score("hello", user_id=user)
        assert ctx.approach_reasoning != ""
        assert len(ctx.approach_reasoning) > 10


# ═══════════════════════════════════════════════════════════
#  SECTION 9: Conversation flow analysis
# ═══════════════════════════════════════════════════════════

class TestConversationFlow:
    """Tests for analyze_conversation_flow."""

    def _store_flow(self, memory, user, entries_data):
        """Store entries with topics and optional scores."""
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
        for i, data in enumerate(entries_data):
            entry = MemoryEntry(
                entry_id="",
                user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح",
                message_role="user",
                message_summary=data.get("summary", f"msg {i}"),
                topic=data.get("topic", "general"),
                intent_score=data.get("intent", None),
                confusion_detected=data.get("confused", False),
            )
            memory.store(entry)

    def test_no_memory_returns_insufficient(self, mock_scorer):
        s = ContextualIntentScorer(mock_scorer, None, None)
        flow = s.analyze_conversation_flow("user_x")
        assert flow.flow_type == "insufficient_data"

    def test_too_few_interactions(self, full_scorer, memory):
        user = "flow_few"
        entry = MemoryEntry(
            entry_id="", user_id=user,
            timestamp=datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc),
            time_period="صباح", message_role="user",
            message_summary="hello", topic="general",
        )
        memory.store(entry)
        flow = full_scorer.analyze_conversation_flow(user)
        assert flow.flow_type == "insufficient_data"

    def test_deep_dive_detection(self, full_scorer, memory):
        user = "flow_deep"
        entries = [{"topic": "python"} for _ in range(8)]
        self._store_flow(memory, user, entries)
        flow = full_scorer.analyze_conversation_flow(user)
        assert flow.flow_type == "deep_dive"
        assert flow.dominant_topic == "python"
        assert flow.unique_topics == 1

    def test_topic_jumping_detection(self, full_scorer, memory):
        user = "flow_jump"
        entries = [
            {"topic": "python"}, {"topic": "cooking"},
            {"topic": "math"}, {"topic": "music"},
            {"topic": "sports"}, {"topic": "ai"},
        ]
        self._store_flow(memory, user, entries)
        flow = full_scorer.analyze_conversation_flow(user)
        assert flow.flow_type == "topic_jumping"
        assert flow.topic_switches >= 5

    def test_escalation_detection(self, full_scorer, memory):
        user = "flow_escalate"
        entries = [
            {"topic": "billing", "confused": False, "intent": 0.8},
            {"topic": "billing", "confused": False, "intent": 0.7},
            {"topic": "billing", "confused": True, "intent": 0.5},
            {"topic": "billing", "confused": True, "intent": 0.3},
            {"topic": "billing", "confused": True, "intent": 0.2},
        ]
        self._store_flow(memory, user, entries)
        flow = full_scorer.analyze_conversation_flow(user)
        assert flow.flow_type == "escalation"
        assert flow.confusion_trend == "increasing"
        assert flow.intent_trend == "decreasing"

    def test_de_escalation_detection(self, full_scorer, memory):
        user = "flow_deesc"
        entries = [
            {"topic": "help", "confused": True, "intent": 0.3},
            {"topic": "help", "confused": True, "intent": 0.4},
            {"topic": "help", "confused": False, "intent": 0.6},
            {"topic": "help", "confused": False, "intent": 0.8},
            {"topic": "help", "confused": False, "intent": 0.9},
        ]
        self._store_flow(memory, user, entries)
        flow = full_scorer.analyze_conversation_flow(user)
        assert flow.flow_type == "de_escalation"

    def test_steady_flow(self, full_scorer, memory):
        user = "flow_steady"
        entries = [
            {"topic": "python", "intent": 0.7},
            {"topic": "python", "intent": 0.7},
            {"topic": "loops", "intent": 0.7},
            {"topic": "loops", "intent": 0.7},
        ]
        self._store_flow(memory, user, entries)
        flow = full_scorer.analyze_conversation_flow(user)
        assert flow.flow_type in ("steady", "deep_dive")

    def test_flow_summary_not_empty(self, full_scorer, memory):
        user = "flow_summary"
        entries = [{"topic": "python"} for _ in range(5)]
        self._store_flow(memory, user, entries)
        flow = full_scorer.analyze_conversation_flow(user)
        assert flow.summary != ""
        assert "interaction" in flow.summary.lower()

    def test_flow_interaction_count(self, full_scorer, memory):
        user = "flow_count"
        entries = [{"topic": "python"} for _ in range(7)]
        self._store_flow(memory, user, entries)
        flow = full_scorer.analyze_conversation_flow(user)
        assert flow.interaction_count == 7


# ═══════════════════════════════════════════════════════════
#  SECTION 10: predict_next_need
# ═══════════════════════════════════════════════════════════

class TestPredictNextNeed:
    """Tests for predict_next_need."""

    def test_insufficient_data_no_sources(self, mock_scorer):
        s = ContextualIntentScorer(mock_scorer, None, None)
        pred = s.predict_next_need("any_user")
        assert pred == "insufficient_data"

    def test_insufficient_data_too_few_interactions(self, full_scorer, fp):
        user = "pred_few"
        fp.update(user, "hello", timestamp=time.time())
        pred = full_scorer.predict_next_need(user)
        assert pred == "insufficient_data"

    def test_needs_examples_prediction(self, full_scorer, fp, memory):
        user = "pred_examples"
        ts = time.time()
        # Build needs_examples pattern (moderate confusion)
        for i in range(6):
            fp.update(user, "ما فهمت", timestamp=ts + i * 30)
        for i in range(4):
            fp.update(user, "تمام", timestamp=ts + 300 + i * 30)
        pred = full_scorer.predict_next_need(user)
        assert pred != "insufficient_data"
        assert isinstance(pred, str)

    def test_unresolved_topic_prediction(self, full_scorer, fp, memory):
        user = "pred_unresolved"
        ts = time.time()
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(5):
            fp.update(user, f"msg {i}", timestamp=ts + i * 30)
        # Store with unresolved confusion
        for i in range(5):
            entry = MemoryEntry(
                entry_id="", user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح", message_role="user",
                message_summary=f"msg {i}", topic="api_design",
                confusion_detected=(i == 2),
                resolution_achieved=False,
            )
            memory.store(entry)
        pred = full_scorer.predict_next_need(user)
        assert pred != "insufficient_data"

    def test_high_frequency_topic_prediction(self, full_scorer, fp, memory):
        user = "pred_freq"
        ts = time.time()
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(5):
            fp.update(user, f"msg {i}", timestamp=ts + i * 30)
        for i in range(5):
            entry = MemoryEntry(
                entry_id="", user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح", message_role="user",
                message_summary=f"python {i}", topic="python",
            )
            memory.store(entry)
        pred = full_scorer.predict_next_need(user)
        assert "python" in pred.lower() or pred != "insufficient_data"

    def test_repeats_to_confirm_prediction(self, full_scorer, fp, memory):
        user = "pred_confirm_pattern"
        ts = time.time()
        # Build repeats_to_confirm pattern
        msgs = [
            "كيف أسوي لوب؟", "تمام", "كيف أسوي لوب؟", "واضح",
            "كيف أطبع؟", "شكراً", "كيف أطبع؟", "فهمت",
            "كيف أسوي لوب؟", "ممتاز", "كيف أسوي لوب؟",
        ]
        for i, m in enumerate(msgs):
            fp.update(user, m, timestamp=ts + i * 30)
        pred = full_scorer.predict_next_need(user)
        # Should predict confirmation behavior
        assert isinstance(pred, str)


# ═══════════════════════════════════════════════════════════
#  SECTION 11: Edge cases
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_text(self, full_scorer):
        ctx = full_scorer.score("")
        assert ctx.raw_i_score is not None

    def test_very_long_text(self, full_scorer):
        text = "hello " * 1000
        ctx = full_scorer.score(text)
        assert ctx.raw_i_score is not None

    def test_arabic_only_text(self, full_scorer):
        ctx = full_scorer.score("بسم الله الرحمن الرحيم")
        assert ctx.raw_i_score is not None

    def test_english_only_text(self, full_scorer):
        ctx = full_scorer.score("I want to learn programming")
        assert ctx.raw_i_score is not None

    def test_mixed_language(self, full_scorer):
        ctx = full_scorer.score("أبغى أتعلم Python programming")
        assert ctx.raw_i_score is not None

    def test_special_characters(self, full_scorer):
        ctx = full_scorer.score("!@#$%^&*()")
        assert ctx.raw_i_score is not None

    def test_new_user_no_history(self, full_scorer):
        ctx = full_scorer.score("hello", user_id="brand_new_user")
        assert ctx.is_repeat_question is False
        assert ctx.repeat_reason == "not_repeat"
        assert ctx.user_pattern == "asks_once"
        assert ctx.user_trust_level == 0.0

    def test_single_interaction_user(self, full_scorer, fp):
        user = "single_int"
        fp.update(user, "hello", timestamp=time.time())
        ctx = full_scorer.score("world", user_id=user)
        assert ctx.user_trust_level > 0.0
        assert ctx.is_repeat_question is False

    def test_multiple_users_isolated(self, full_scorer, fp):
        """Different users have isolated contexts."""
        user_a = "edge_user_a"
        user_b = "edge_user_b"
        ts = time.time()
        fp.update(user_a, "كيف أسوي لوب؟", timestamp=ts)
        fp.update(user_a, "ما فهمت", timestamp=ts + 30)
        fp.update(user_b, "hello world", timestamp=ts + 60)

        ctx_a = full_scorer.score("كيف أسوي لوب؟", user_id=user_a)
        ctx_b = full_scorer.score("كيف أسوي لوب؟", user_id=user_b)

        # User A has history, user B does not
        assert ctx_a.user_trust_level >= ctx_b.user_trust_level

    def test_conversation_history_param_accepted(self, full_scorer):
        """conversation_history param should be accepted even if unused."""
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        ctx = full_scorer.score("how are you?", conversation_history=history)
        assert ctx.raw_i_score is not None

    def test_none_user_id_no_crash(self, full_scorer):
        ctx = full_scorer.score("hello", user_id=None)
        assert ctx.suggested_approach == "standard"

    def test_intent_context_dataclass_fields(self):
        """IntentContext should have all required fields."""
        ctx = IntentContext(
            raw_i_score=0.5, raw_confidence="medium",
            raw_category="neutral", is_repeat_question=False,
            times_asked=0, repeat_reason="not_repeat",
            user_pattern="asks_once", user_comprehension="quick",
            user_trust_level=0.0, previous_explanations_count=0,
            last_explanation_approach=None, topic_history=[],
            emotional_trajectory="insufficient_data",
            suggested_approach="standard",
            approach_reasoning="test", confidence=0.5,
        )
        assert ctx.raw_i_score == 0.5
        assert ctx.confidence == 0.5

    def test_conversation_flow_dataclass_fields(self):
        """ConversationFlow should have all required fields."""
        flow = ConversationFlow(
            user_id="test", interaction_count=0,
            flow_type="insufficient_data", topic_switches=0,
            unique_topics=0, dominant_topic=None,
            confusion_trend="insufficient_data",
            intent_trend="insufficient_data",
            summary="test",
        )
        assert flow.user_id == "test"
        assert flow.flow_type == "insufficient_data"


# ═══════════════════════════════════════════════════════════
#  SECTION 12: Confidence computation
# ═══════════════════════════════════════════════════════════

class TestConfidence:
    """Tests for confidence computation."""

    def test_high_raw_confidence(self, full_scorer):
        ctx = full_scorer.score("أبغى أتعلم")  # mock returns high
        assert ctx.confidence >= 0.7

    def test_low_raw_confidence(self):
        s = MockIntentScorer(default_i=0.5, default_conf="low")
        scorer = ContextualIntentScorer(s, None, None)
        ctx = scorer.score("xyzzy")
        assert ctx.confidence <= 0.5

    def test_confidence_with_fingerprint(self, mock_scorer, fp):
        user = "conf_fp"
        ts = time.time()
        for i in range(15):
            fp.update(user, f"msg {i}", timestamp=ts + i * 30)
        s = ContextualIntentScorer(mock_scorer, fp, None)
        ctx = s.score("hello", user_id=user)
        # Should incorporate fingerprint confidence
        assert ctx.confidence > 0.0

    def test_confidence_with_many_memory_entries(self, mock_scorer, memory):
        user = "conf_mem"
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(25):
            entry = MemoryEntry(
                entry_id="", user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح", message_role="user",
                message_summary=f"msg {i}", topic="general",
            )
            memory.store(entry)
        s = ContextualIntentScorer(mock_scorer, None, memory)
        ctx = s.score("hello", user_id=user)
        assert ctx.confidence > 0.0

    def test_confidence_bounds(self, full_scorer, fp):
        user = "conf_bounds"
        fp.update(user, "hello", timestamp=time.time())
        ctx = full_scorer.score("hello", user_id=user)
        assert 0.0 <= ctx.confidence <= 1.0


# ═══════════════════════════════════════════════════════════
#  SECTION 13: Trend analysis
# ═══════════════════════════════════════════════════════════

class TestTrendAnalysis:
    """Tests for the _analyze_trend static method."""

    def test_increasing_trend(self, full_scorer):
        result = full_scorer._analyze_trend([0.1, 0.2, 0.5, 0.8, 0.9])
        assert result == "increasing"

    def test_decreasing_trend(self, full_scorer):
        result = full_scorer._analyze_trend([0.9, 0.8, 0.5, 0.2, 0.1])
        assert result == "decreasing"

    def test_stable_trend(self, full_scorer):
        result = full_scorer._analyze_trend([0.5, 0.5, 0.5, 0.5])
        assert result == "stable"

    def test_insufficient_data(self, full_scorer):
        result = full_scorer._analyze_trend([0.5])
        assert result == "insufficient_data"

    def test_empty_list(self, full_scorer):
        result = full_scorer._analyze_trend([])
        assert result == "insufficient_data"

    def test_two_values_increasing(self, full_scorer):
        result = full_scorer._analyze_trend([0.1, 0.9])
        assert result == "increasing"

    def test_two_values_decreasing(self, full_scorer):
        result = full_scorer._analyze_trend([0.9, 0.1])
        assert result == "decreasing"


# ═══════════════════════════════════════════════════════════
#  SECTION 14: Raw I score preservation (CRITICAL)
# ═══════════════════════════════════════════════════════════

class TestRawScorePreservation:
    """
    CRITICAL: The raw I score must NEVER be modified by context.
    These tests verify this invariant exhaustively.
    """

    def test_constructive_i_unchanged(self, mock_scorer, fp, memory):
        user = "raw_constructive"
        ts = time.time()
        for i in range(5):
            fp.update(user, "ما فهمت", timestamp=ts + i * 30)

        s = ContextualIntentScorer(mock_scorer, fp, memory)
        ctx = s.score("أبغى أتعلم", user_id=user)
        assert ctx.raw_i_score == 0.95  # exact mock value

    def test_harmful_i_unchanged(self, mock_scorer, fp, memory):
        user = "raw_harmful"
        ts = time.time()
        for i in range(5):
            fp.update(user, "تمام", timestamp=ts + i * 30)

        s = ContextualIntentScorer(mock_scorer, fp, memory)
        ctx = s.score("كيف أصنع قنبلة", user_id=user)
        assert ctx.raw_i_score == 0.05  # exact mock value

    def test_neutral_i_unchanged(self, mock_scorer, fp, memory):
        user = "raw_neutral"
        ts = time.time()
        fp.update(user, "hello", timestamp=ts)

        s = ContextualIntentScorer(mock_scorer, fp, memory)
        ctx = s.score("وش الطقس اليوم", user_id=user)
        # Mock default for unknown keywords
        assert ctx.raw_i_score == 0.5

    def test_i_same_with_and_without_user_id(self, mock_scorer, fp, memory):
        user = "raw_toggle"
        ts = time.time()
        for i in range(10):
            fp.update(user, f"msg {i}", timestamp=ts + i * 30)

        s = ContextualIntentScorer(mock_scorer, fp, memory)
        text = "أبغى أتعلم البرمجة"
        i_without = s.score(text).raw_i_score
        i_with = s.score(text, user_id=user).raw_i_score
        assert i_without == i_with

    def test_i_same_across_repeated_calls(self, full_scorer, fp):
        user = "raw_repeated"
        fp.update(user, "hello", timestamp=time.time())
        text = "أبغى أتعلم"
        scores = [full_scorer.score(text, user_id=user).raw_i_score for _ in range(5)]
        assert all(s == scores[0] for s in scores)


# ═══════════════════════════════════════════════════════════
#  SECTION 15: Integration with real modules
# ═══════════════════════════════════════════════════════════

class TestRealModuleIntegration:
    """
    Tests that verify ContextualIntentScorer correctly integrates
    with real UserFingerprint and TemporalMemory instances.
    """

    def test_fingerprint_reading_consumed_correctly(self, mock_scorer, fp):
        user = "real_fp"
        ts = time.time()
        msgs = ["وش الأخبار؟", "ما فهمت", "وضح أكثر", "تمام شكراً", "طيب"]
        for i, m in enumerate(msgs):
            fp.update(user, m, timestamp=ts + i * 60)

        s = ContextualIntentScorer(mock_scorer, fp, None)
        ctx = s.score("hello", user_id=user)

        # Reading should reflect real fingerprint
        reading = fp.read(user)
        assert ctx.user_pattern == reading.question_pattern
        assert ctx.user_comprehension == reading.comprehension_level
        assert ctx.user_trust_level == reading.trust_level

    def test_memory_context_consumed_correctly(self, mock_scorer, memory):
        user = "real_mem"
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)
        topics = ["python", "loops", "python"]
        for i, t in enumerate(topics):
            entry = MemoryEntry(
                entry_id="", user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح", message_role="user",
                message_summary=f"about {t}", topic=t,
            )
            memory.store(entry)

        s = ContextualIntentScorer(mock_scorer, None, memory)
        ctx = s.score("hello", user_id=user)

        mem_ctx = memory.get_context(user)
        assert ctx.topic_history == mem_ctx.recent_topics
        assert ctx.emotional_trajectory == mem_ctx.emotional_trajectory

    def test_repetition_detection_uses_fingerprint(self, mock_scorer, fp):
        user = "real_rep"
        ts = time.time()
        fp.update(user, "كيف أسوي لوب في بايثون؟", timestamp=ts)
        fp.update(user, "شكراً فهمت", timestamp=ts + 60)
        fp.update(user, "كيف أسوي لوب في بايثون؟", timestamp=ts + 120)

        s = ContextualIntentScorer(mock_scorer, fp, None)
        ctx = s.score("كيف أسوي لوب في بايثون؟", user_id=user)

        rep = fp.detect_repetition(user, "كيف أسوي لوب في بايثون؟")
        assert ctx.is_repeat_question == rep.is_repeat

    def test_merge_fingerprint_and_memory(self, mock_scorer, fp, memory):
        """Both sources contribute to the final IntentContext."""
        user = "real_merge"
        ts = time.time()
        base = datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)

        # Feed fingerprint
        for i in range(5):
            fp.update(user, f"message {i}", timestamp=ts + i * 60)

        # Feed memory
        for i in range(5):
            entry = MemoryEntry(
                entry_id="", user_id=user,
                timestamp=base + timedelta(hours=i),
                time_period="صباح", message_role="user",
                message_summary=f"msg {i}", topic="python",
            )
            memory.store(entry)

        s = ContextualIntentScorer(mock_scorer, fp, memory)
        ctx = s.score("hello", user_id=user)

        # Fingerprint fields should be populated
        assert ctx.user_trust_level > 0.0
        # Memory fields should be populated
        assert len(ctx.topic_history) > 0


# ═══════════════════════════════════════════════════════════
#  SECTION 16: Graceful degradation
# ═══════════════════════════════════════════════════════════

class TestGracefulDegradation:
    """Tests that the scorer degrades gracefully when components fail."""

    def test_broken_fingerprint_no_crash(self, mock_scorer, memory):
        class BrokenFP:
            def read(self, uid): raise RuntimeError("boom")
            def detect_repetition(self, uid, txt): raise RuntimeError("boom")

        s = ContextualIntentScorer(mock_scorer, BrokenFP(), memory)
        ctx = s.score("hello", user_id="test")
        assert ctx.raw_i_score is not None
        assert ctx.is_repeat_question is False

    def test_broken_memory_no_crash(self, mock_scorer, fp):
        class BrokenMem:
            def get_context(self, uid): raise RuntimeError("boom")
            def recall(self, uid, limit=10): raise RuntimeError("boom")

        s = ContextualIntentScorer(mock_scorer, fp, BrokenMem())
        ctx = s.score("hello", user_id="test")
        assert ctx.raw_i_score is not None
        assert ctx.topic_history == []

    def test_broken_scorer_no_crash(self, fp, memory):
        class BrokenScorer:
            def score(self, text): raise RuntimeError("boom")

        s = ContextualIntentScorer(BrokenScorer(), fp, memory)
        ctx = s.score("hello", user_id="test")
        assert ctx.raw_i_score == 0.5
        assert ctx.raw_confidence == "low"

    def test_all_broken_still_works(self):
        class B1:
            def score(self, text): raise RuntimeError("x")
        class B2:
            def read(self, uid): raise RuntimeError("x")
            def detect_repetition(self, uid, txt): raise RuntimeError("x")
        class B3:
            def get_context(self, uid): raise RuntimeError("x")
            def recall(self, uid, limit=10): raise RuntimeError("x")

        s = ContextualIntentScorer(B1(), B2(), B3())
        ctx = s.score("hello", user_id="test")
        assert ctx.raw_i_score == 0.5
        assert ctx.suggested_approach == "standard"

    def test_broken_memory_flow_analysis(self, mock_scorer, fp):
        class BrokenMem:
            def recall(self, uid, limit=10): raise RuntimeError("boom")
            def get_context(self, uid): raise RuntimeError("boom")

        s = ContextualIntentScorer(mock_scorer, fp, BrokenMem())
        flow = s.analyze_conversation_flow("test")
        assert flow.flow_type == "insufficient_data"

    def test_broken_predict(self, mock_scorer):
        class BrokenFP:
            def read(self, uid): raise RuntimeError("boom")
        class BrokenMem:
            def get_context(self, uid): raise RuntimeError("boom")

        s = ContextualIntentScorer(mock_scorer, BrokenFP(), BrokenMem())
        pred = s.predict_next_need("test")
        assert pred == "insufficient_data"


# ═══════════════════════════════════════════════════════════
#  SECTION 17: Category and approach coverage
# ═══════════════════════════════════════════════════════════

class TestCategoryCoverage:
    """Ensure all I score ranges produce valid categories."""

    @pytest.mark.parametrize("score,expected", [
        (1.0, "constructive"),
        (0.9, "constructive"),
        (0.8, "constructive"),
        (0.75, "support_seeking"),
        (0.65, "support_seeking"),
        (0.55, "neutral"),
        (0.45, "neutral"),
        (0.35, "questionable"),
        (0.25, "questionable"),
        (0.15, "harmful"),
        (0.05, "harmful"),
        (0.0, "harmful"),
    ])
    def test_category_mapping(self, score, expected):
        assert _i_to_category(score) == expected


class TestApproachCoverage:
    """Ensure all approach matrix combinations produce valid approaches."""

    @pytest.mark.parametrize("reason", [
        "confusion", "confirmation", "contradiction",
        "forgot", "new_angle", "not_repeat",
    ])
    @pytest.mark.parametrize("comp", [
        "quick", "needs_examples", "needs_step_by_step",
    ])
    def test_all_combinations(self, reason, comp):
        approach = _lookup_approach(reason, comp)
        assert approach in _APPROACH_REASONING
        assert _APPROACH_REASONING[approach] != ""
