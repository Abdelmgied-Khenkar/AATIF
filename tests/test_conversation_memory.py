"""
Tests for aatif_conversation_memory.py — عاطف يتذكر

Covers:
  - Turn storage and max_turns enforcement
  - Emotional arc tracking (shifted, escalated, dominant)
  - Context retrieval (last user/assistant, recent turns, tone)
  - Privacy: text in RAM, NOT on disk (H5 regression)
  - Persistence: save/load cycle preserves arcs, not text
  - Clear removes all data
  - Context prompt formatting
  - Edge cases (empty, first message, unknown emotions)

License: BSL 1.1
"""

import json
import os
import tempfile
import pytest

from aatif_conversation_memory import (
    AATIFConversationMemory,
    ConversationTurn,
    EmotionalArc,
    ConversationContext,
)


# ── Helpers ──────────────────────────────────────────────

class FakeReading:
    """Mimics IntentReading for testing."""
    def __init__(self, emotion="clear", dialect="", load=False, decision="EXECUTE", mode="NORMAL"):
        self.emotional_state = emotion
        self.dialect_detected = dialect
        self.load_bearing = load
        self.decision = decision
        self.mode = mode


@pytest.fixture
def mem():
    """Fresh in-memory conversation memory."""
    return AATIFConversationMemory(max_turns=20)


@pytest.fixture
def persist_mem():
    """Memory with temporary persist directory."""
    with tempfile.TemporaryDirectory() as d:
        yield AATIFConversationMemory(max_turns=20, persist_dir=d), d


KEY = "966501234567"


# ═══════════════════════════════════════════════════════════
#  Turn storage
# ═══════════════════════════════════════════════════════════

class TestTurnStorage:

    def test_add_turn_stores_text_in_ram(self, mem):
        """add_turn stores full text in the turn object."""
        mem.add_turn(KEY, "user", "السلام عليكم")
        turns = mem._turns[KEY]
        assert len(turns) == 1
        assert turns[0].text == "السلام عليكم"
        assert turns[0].role == "user"

    def test_add_turn_with_reading(self, mem):
        """add_turn enriches the turn from an IntentReading."""
        reading = FakeReading(emotion="frustrated", dialect="saudi",
                              load=True, decision="CLARIFY")
        mem.add_turn(KEY, "user", "تعبت", reading=reading)
        turn = mem._turns[KEY][0]
        assert turn.emotional_state == "frustrated"
        assert turn.dialect == "saudi"
        assert turn.load_bearing is True
        assert turn.decision == "CLARIFY"

    def test_max_turns_enforced(self, mem):
        """Only the last max_turns turns are kept."""
        small_mem = AATIFConversationMemory(max_turns=5)
        for i in range(10):
            small_mem.add_turn(KEY, "user", f"message {i}")
        turns = small_mem._turns[KEY]
        assert len(turns) == 5
        assert turns[0].text == "message 5"
        assert turns[-1].text == "message 9"

    def test_multiple_conversations_isolated(self, mem):
        """Different relationship keys are isolated."""
        mem.add_turn("user_a", "user", "hello")
        mem.add_turn("user_b", "user", "مرحبا")
        assert len(mem._turns["user_a"]) == 1
        assert len(mem._turns["user_b"]) == 1
        assert mem._turns["user_a"][0].text == "hello"
        assert mem._turns["user_b"][0].text == "مرحبا"

    def test_auto_timestamp(self, mem):
        """Timestamp is auto-generated when not provided."""
        mem.add_turn(KEY, "user", "test")
        turn = mem._turns[KEY][0]
        assert turn.timestamp > 0

    def test_explicit_timestamp(self, mem):
        """Explicit timestamp is respected."""
        mem.add_turn(KEY, "user", "test", timestamp=1000.0)
        assert mem._turns[KEY][0].timestamp == 1000.0


# ═══════════════════════════════════════════════════════════
#  Emotional arc tracking
# ═══════════════════════════════════════════════════════════

class TestEmotionalArc:

    def test_single_emotion_dominant(self, mem):
        """Single emotion state → dominant."""
        mem.add_turn(KEY, "user", "msg", reading=FakeReading(emotion="excited"))
        arc = mem._arcs[KEY]
        assert arc.dominant_emotion == "excited"
        assert arc.shifted is False

    def test_shifted_on_multiple_emotions(self, mem):
        """Multiple different emotions → shifted=True."""
        mem.add_turn(KEY, "user", "msg1", reading=FakeReading(emotion="clear"))
        mem.add_turn(KEY, "user", "msg2", reading=FakeReading(emotion="frustrated"))
        arc = mem._arcs[KEY]
        assert arc.shifted is True

    def test_escalated_when_heavier(self, mem):
        """Emotion gets heavier → escalated=True."""
        mem.add_turn(KEY, "user", "msg1", reading=FakeReading(emotion="clear"))
        mem.add_turn(KEY, "user", "msg2", reading=FakeReading(emotion="carrying_weight"))
        arc = mem._arcs[KEY]
        assert arc.escalated is True

    def test_not_escalated_when_lighter(self, mem):
        """Emotion gets lighter → escalated=False."""
        mem.add_turn(KEY, "user", "msg1", reading=FakeReading(emotion="frustrated"))
        mem.add_turn(KEY, "user", "msg2", reading=FakeReading(emotion="clear"))
        arc = mem._arcs[KEY]
        assert arc.escalated is False

    def test_load_bearing_count(self, mem):
        """Load-bearing moments are counted."""
        mem.add_turn(KEY, "user", "msg1", reading=FakeReading(load=True))
        mem.add_turn(KEY, "user", "msg2", reading=FakeReading(load=False))
        mem.add_turn(KEY, "user", "msg3", reading=FakeReading(load=True))
        arc = mem._arcs[KEY]
        assert arc.load_bearing_count == 2

    def test_dominant_emotion_most_frequent(self, mem):
        """Dominant emotion is the most frequent."""
        for _ in range(3):
            mem.add_turn(KEY, "user", "a", reading=FakeReading(emotion="clear"))
        for _ in range(1):
            mem.add_turn(KEY, "user", "b", reading=FakeReading(emotion="frustrated"))
        arc = mem._arcs[KEY]
        assert arc.dominant_emotion == "clear"


# ═══════════════════════════════════════════════════════════
#  Context retrieval
# ═══════════════════════════════════════════════════════════

class TestGetContext:

    def test_empty_context(self, mem):
        """No turns → turn_count=0, empty context."""
        ctx = mem.get_context(KEY)
        assert ctx.turn_count == 0
        assert ctx.last_user_text == ""
        assert ctx.last_assistant_text == ""

    def test_last_user_and_assistant(self, mem):
        """Last user and assistant messages are found."""
        mem.add_turn(KEY, "user", "first question")
        mem.add_turn(KEY, "assistant", "first answer")
        mem.add_turn(KEY, "user", "second question")
        mem.add_turn(KEY, "assistant", "second answer")
        ctx = mem.get_context(KEY)
        assert ctx.last_user_text == "second question"
        assert ctx.last_assistant_text == "second answer"

    def test_recent_turns_limited_to_5(self, mem):
        """recent_turns returns at most 5."""
        for i in range(10):
            mem.add_turn(KEY, "user", f"msg {i}")
        ctx = mem.get_context(KEY)
        assert len(ctx.recent_turns) == 5

    def test_recent_turns_text_truncated(self, mem):
        """Text in recent_turns is truncated to 200 chars."""
        long_text = "A" * 500
        mem.add_turn(KEY, "user", long_text)
        ctx = mem.get_context(KEY)
        assert len(ctx.recent_turns[0]["text"]) == 200

    def test_turn_count(self, mem):
        """Turn count matches number of added turns."""
        mem.add_turn(KEY, "user", "a")
        mem.add_turn(KEY, "assistant", "b")
        mem.add_turn(KEY, "user", "c")
        ctx = mem.get_context(KEY)
        assert ctx.turn_count == 3

    def test_tone_heavy_on_load_bearing(self, mem):
        """Multiple load-bearing moments → heavy tone."""
        for _ in range(3):
            mem.add_turn(KEY, "user", "x",
                         reading=FakeReading(emotion="carrying_weight", load=True))
        ctx = mem.get_context(KEY)
        assert ctx.conversation_tone == "heavy"

    def test_tone_tense_on_escalation(self, mem):
        """Escalation → tense tone."""
        mem.add_turn(KEY, "user", "a", reading=FakeReading(emotion="clear"))
        mem.add_turn(KEY, "user", "b", reading=FakeReading(emotion="frustrated"))
        ctx = mem.get_context(KEY)
        assert ctx.conversation_tone == "tense"

    def test_dominant_dialect(self, mem):
        """Most frequent dialect is reported."""
        for _ in range(3):
            mem.add_turn(KEY, "user", "x", reading=FakeReading(dialect="saudi"))
        mem.add_turn(KEY, "user", "y", reading=FakeReading(dialect="egyptian"))
        ctx = mem.get_context(KEY)
        assert ctx.dominant_dialect == "saudi"

    def test_last_decision(self, mem):
        """last_decision reflects the most recent user turn's decision."""
        mem.add_turn(KEY, "user", "a", reading=FakeReading(decision="EXECUTE"))
        mem.add_turn(KEY, "user", "b", reading=FakeReading(decision="CLARIFY"))
        ctx = mem.get_context(KEY)
        assert ctx.last_decision == "CLARIFY"


# ═══════════════════════════════════════════════════════════
#  Context dict and prompt
# ═══════════════════════════════════════════════════════════

class TestContextFormats:

    def test_get_context_dict_is_dict(self, mem):
        """get_context_dict returns a plain dict."""
        mem.add_turn(KEY, "user", "test")
        d = mem.get_context_dict(KEY)
        assert isinstance(d, dict)
        assert "turn_count" in d

    def test_context_prompt_first_message(self, mem):
        """First message → specific Arabic string."""
        prompt = mem.get_context_prompt(KEY)
        assert "أول رسالة" in prompt

    def test_context_prompt_with_history(self, mem):
        """With history → prompt includes turn count."""
        mem.add_turn(KEY, "user", "test")
        mem.add_turn(KEY, "assistant", "reply")
        prompt = mem.get_context_prompt(KEY)
        assert "2" in prompt  # 2 messages

    def test_context_prompt_escalation_warning(self, mem):
        """Escalated emotional arc → warning in prompt."""
        mem.add_turn(KEY, "user", "a", reading=FakeReading(emotion="clear"))
        mem.add_turn(KEY, "user", "b", reading=FakeReading(emotion="carrying_weight"))
        prompt = mem.get_context_prompt(KEY)
        assert "عطف" in prompt or "تثاقلت" in prompt

    def test_context_prompt_last_message_truncated(self, mem):
        """Last message in prompt is truncated to 100 chars."""
        long_msg = "ب" * 200
        mem.add_turn(KEY, "user", long_msg)
        prompt = mem.get_context_prompt(KEY)
        # The prompt should contain a truncated version
        assert long_msg not in prompt  # full 200 chars not present


# ═══════════════════════════════════════════════════════════
#  H5 regression: Privacy — text in RAM, NOT on disk
# ═══════════════════════════════════════════════════════════

class TestH5Privacy:
    """
    H5 regression tests: The privacy boundary is RAM vs disk.
    Text lives in session memory (RAM) for context window use.
    Text is NOT persisted to disk — only emotional arcs and metadata.
    """

    def test_save_strips_text_from_disk(self, persist_mem):
        """GOVERNANCE: save() must NOT write message text to disk."""
        mem, d = persist_mem
        mem.add_turn(KEY, "user", "هذا نص سري لا يجب حفظه على الديسك")
        mem.add_turn(KEY, "assistant", "هذا رد سري أيضاً")
        mem.save(KEY)

        # Read the persisted JSON
        path = mem._get_persist_path(KEY)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check no text field anywhere in turns_summary
        for turn_data in data.get("turns_summary", []):
            assert "text" not in turn_data, (
                "H5 VIOLATION: raw text found in persisted turns_summary"
            )

        # Also verify the full JSON string doesn't contain the secret text
        raw_json = json.dumps(data, ensure_ascii=False)
        assert "هذا نص سري" not in raw_json
        assert "هذا رد سري" not in raw_json

    def test_save_preserves_metadata(self, persist_mem):
        """save() preserves emotional arc, dialects, and topics."""
        mem, d = persist_mem
        reading = FakeReading(emotion="frustrated", dialect="saudi", load=True)
        mem.add_turn(KEY, "user", "تعبت من المشروع", reading=reading)
        mem.save(KEY)

        path = mem._get_persist_path(KEY)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert "emotional_arc" in data
        assert data["emotional_arc"]["load_bearing_count"] == 1
        assert "frustrated" in data["emotional_arc"]["states"]
        assert "saudi" in data.get("dialects", [])

    def test_load_restores_arcs_not_text(self, persist_mem):
        """Loading from disk restores arcs but NOT text."""
        mem, d = persist_mem
        reading = FakeReading(emotion="excited", dialect="egyptian")
        mem.add_turn(KEY, "user", "نص سري", reading=reading)
        mem.save(KEY)

        # Create a new memory instance pointing at the same directory
        mem2 = AATIFConversationMemory(max_turns=20, persist_dir=d)

        # Arcs should be restored
        assert KEY in mem2._arcs
        assert mem2._arcs[KEY].dominant_emotion == "excited"

        # But no turns (text) should be restored from disk
        assert KEY not in mem2._turns or len(mem2._turns[KEY]) == 0


# ═══════════════════════════════════════════════════════════
#  Clear
# ═══════════════════════════════════════════════════════════

class TestClear:

    def test_clear_removes_all_data(self, mem):
        """clear() removes all data for the relationship key."""
        reading = FakeReading(emotion="excited", dialect="saudi")
        mem.add_turn(KEY, "user", "test msg", reading=reading)
        mem.add_turn(KEY, "assistant", "reply")

        mem.clear(KEY)

        assert KEY not in mem._turns
        assert KEY not in mem._arcs
        assert KEY not in mem._dialects
        assert KEY not in mem._topics

    def test_clear_doesnt_affect_other_keys(self, mem):
        """clear() for one key doesn't affect others."""
        mem.add_turn("key_a", "user", "hello")
        mem.add_turn("key_b", "user", "مرحبا")
        mem.clear("key_a")
        assert "key_a" not in mem._turns
        assert len(mem._turns["key_b"]) == 1


# ═══════════════════════════════════════════════════════════
#  Topic extraction
# ═══════════════════════════════════════════════════════════

class TestTopics:

    def test_arabic_topic_extraction(self, mem):
        """Arabic topic markers are detected."""
        mem.add_turn(KEY, "user", "ابي تصميم للمشروع",
                     reading=FakeReading())
        topics = mem._topics[KEY]
        assert "design" in topics or "project" in topics

    def test_english_topic_extraction(self, mem):
        """English topic markers are detected."""
        mem.add_turn(KEY, "user", "I need help with the project design",
                     reading=FakeReading())
        topics = mem._topics[KEY]
        assert "project" in topics
        assert "design" in topics

    def test_topics_accumulate(self, mem):
        """Topics accumulate across turns."""
        mem.add_turn(KEY, "user", "مشروع", reading=FakeReading())
        mem.add_turn(KEY, "user", "تصميم", reading=FakeReading())
        topics = mem._topics[KEY]
        assert len(topics) >= 2
