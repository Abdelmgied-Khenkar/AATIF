#!/usr/bin/env python3
"""
AATIF Conversation Memory — عاطف يتذكر

Makes عاطف remember conversations — not just what was said,
but how the person was feeling and where the conversation went.

Two levels of memory:
  1. Session memory — current conversation turns (in RAM)
  2. Persistent memory — emotional arcs + key facts (JSON on disk)

What gets remembered:
  - Last N turns (configurable, default 20)
  - Emotional arc: how emotions shifted across the conversation
  - Dialect detected (and consistency)
  - Load-bearing moments: when someone was carrying weight
  - Topics discussed
  - What عاطف decided and why (EXECUTE/CLARIFY/STOP)

Privacy note:
  - Session turns store message text in RAM for context window
  - Text is NOT persisted to disk — only emotional arcs and metadata
    are saved to persistent memory (JSON)
  - Personal data beyond what's needed for the conversation is not stored

Philosophy:
  Memory in AATIF is not a database — it's حافظة (a keeper).
  It keeps what matters for compassionate response,
  and lets go of what doesn't serve the person.

Usage:
    memory = AATIFConversationMemory()
    memory.add_turn("user", "تعبت من المشروع", reading=intent_reading)
    memory.add_turn("assistant", "فاهمك، خلنا نشوف وش نقدر نسوي")
    context = memory.get_context("relationship_key_123")

Architect: Abdulmjeed Ibrahim Khenkar
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import defaultdict


# ═══════════════════════════════════════════════════════════
#  Data structures
# ═══════════════════════════════════════════════════════════

@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str                    # "user" or "assistant"
    text: str                    # the message
    timestamp: float = 0.0       # unix timestamp
    emotional_state: str = ""    # from IntentReading
    dialect: str = ""            # detected dialect
    load_bearing: bool = False   # was this a heavy moment?
    decision: str = ""           # EXECUTE/CLARIFY/STOP (for user turns)
    mode: str = ""               # governance mode active


@dataclass
class EmotionalArc:
    """Tracks how emotions shifted across the conversation."""
    states: list = field(default_factory=list)      # list of emotional states in order
    load_bearing_count: int = 0                      # how many heavy moments
    dominant_emotion: str = "clear"                   # most frequent emotion
    shifted: bool = False                             # did emotion change?
    escalated: bool = False                           # did it get heavier?

    # H2 FIX: max states per arc (prevents unbounded list growth)
    MAX_STATES = 100

    def update(self, state: str, load_bearing: bool):
        self.states.append(state)
        # H2 FIX: cap states list
        if len(self.states) > self.MAX_STATES:
            self.states = self.states[-self.MAX_STATES:]
        if load_bearing:
            self.load_bearing_count += 1

        # Dominant = most common
        if self.states:
            counts = {}
            for s in self.states:
                counts[s] = counts.get(s, 0) + 1
            self.dominant_emotion = max(counts, key=counts.get)

        # Shifted = more than one unique state
        unique = set(self.states)
        self.shifted = len(unique) > 1

        # Escalated = last state is heavier than first
        weight = {
            "clear": 0, "excited": 1, "lost": 2,
            "frustrated": 3, "carrying_weight": 4,
        }
        if len(self.states) >= 2:
            first_w = weight.get(self.states[0], 0)
            last_w = weight.get(self.states[-1], 0)
            self.escalated = last_w > first_w


@dataclass
class ConversationContext:
    """What memory gives back to the engine — context for the next response."""
    turn_count: int = 0
    last_user_text: str = ""
    last_assistant_text: str = ""
    emotional_arc: dict = field(default_factory=dict)
    dominant_dialect: str = ""
    topics_mentioned: list = field(default_factory=list)
    load_bearing_moments: int = 0
    last_decision: str = ""
    conversation_tone: str = "neutral"    # neutral/warm/tense/heavy
    recent_turns: list = field(default_factory=list)  # last 5 turns as dicts


# ═══════════════════════════════════════════════════════════
#  Conversation Memory
# ═══════════════════════════════════════════════════════════

class AATIFConversationMemory:
    """
    عاطف يتذكر — Conversation memory for AATIF.

    Manages per-relationship conversation history with emotional tracking.
    """

    # H2 FIX: Maximum number of conversations to keep in memory.
    # Beyond this, the least-recently-used conversation is evicted.
    # Single-threaded contract: no locking — callers are assumed sequential.
    MAX_CONVERSATIONS = 10_000
    # H2 FIX: Maximum emotional states per arc (prevents unbounded list).
    MAX_ARC_STATES = 100

    def __init__(self, max_turns=20, persist_dir=None,
                 max_conversations=None):
        """
        Args:
            max_turns: Max turns to keep in session memory per conversation
            persist_dir: Directory for persistent memory (None = RAM only)
            max_conversations: Max conversations to track (default: MAX_CONVERSATIONS)
        """
        self.max_turns = max_turns
        self.persist_dir = persist_dir
        self.max_conversations = max_conversations or self.MAX_CONVERSATIONS

        # Session memory: relationship_key → list of ConversationTurn
        self._turns: dict[str, list] = defaultdict(list)

        # Emotional arcs: relationship_key → EmotionalArc
        self._arcs: dict[str, EmotionalArc] = defaultdict(EmotionalArc)

        # Dialect tracking: relationship_key → list of detected dialects
        self._dialects: dict[str, list] = defaultdict(list)

        # Topic tracking: relationship_key → set of topics
        self._topics: dict[str, set] = defaultdict(set)

        # H2 FIX: LRU tracking for conversation eviction
        self._conv_access_order: list[str] = []

        # Load persistent memory if available
        if persist_dir:
            os.makedirs(persist_dir, exist_ok=True)
            self._load_persistent()

    # ── Add a turn ──

    def add_turn(self, relationship_key: str, role: str, text: str,
                 reading=None, timestamp=None):
        """
        Record a conversation turn.

        Args:
            relationship_key: Who this conversation is with
            role: "user" or "assistant"
            text: The message text
            reading: IntentReading from the engine (optional, for user turns)
            timestamp: Unix timestamp (auto-generated if None)
        """
        ts = timestamp or time.time()

        turn = ConversationTurn(
            role=role,
            text=text,
            timestamp=ts,
        )

        # Enrich from IntentReading if available
        if reading:
            turn.emotional_state = getattr(reading, 'emotional_state', '')
            turn.dialect = getattr(reading, 'dialect_detected', '')
            turn.load_bearing = getattr(reading, 'load_bearing', False)
            turn.decision = getattr(reading, 'decision', '')
            turn.mode = getattr(reading, 'mode', '')

            # Track emotional arc
            if turn.emotional_state:
                self._arcs[relationship_key].update(
                    turn.emotional_state, turn.load_bearing
                )

            # Track dialect
            if turn.dialect:
                self._dialects[relationship_key].append(turn.dialect)

            # Extract topics (simple keyword extraction)
            self._extract_topics(relationship_key, text)

        # H2 FIX: track access and evict LRU if over capacity
        self._touch_conversation(relationship_key)

        # Add turn and enforce max
        self._turns[relationship_key].append(turn)
        if len(self._turns[relationship_key]) > self.max_turns:
            self._turns[relationship_key] = self._turns[relationship_key][-self.max_turns:]

    # ── H2 FIX: LRU conversation management ──

    def _touch_conversation(self, key: str):
        """Mark conversation as recently used; evict LRU if over capacity."""
        if key not in self._turns and key not in self._arcs:
            # New conversation — check capacity
            active = set(self._turns) | set(self._arcs) | set(self._dialects) | set(self._topics)
            if len(active) >= self.max_conversations:
                self._evict_lru_conversation()
        # Update access order
        if key in self._conv_access_order:
            self._conv_access_order.remove(key)
        self._conv_access_order.append(key)

    def _evict_lru_conversation(self):
        """Evict the least-recently-used conversation from all dicts."""
        if self._conv_access_order:
            oldest = self._conv_access_order.pop(0)
            self._turns.pop(oldest, None)
            self._arcs.pop(oldest, None)
            self._dialects.pop(oldest, None)
            self._topics.pop(oldest, None)

    # ── Get context ──

    def get_context(self, relationship_key: str) -> ConversationContext:
        """
        Get conversation context for the engine to use.

        Returns a ConversationContext with:
        - Recent turns (last 5)
        - Emotional arc summary
        - Dominant dialect
        - Topics mentioned
        - Conversation tone assessment
        """
        turns = self._turns.get(relationship_key, [])
        arc = self._arcs.get(relationship_key, EmotionalArc())
        dialects = self._dialects.get(relationship_key, [])
        topics = self._topics.get(relationship_key, set())

        # Find last user and assistant messages
        last_user = ""
        last_assistant = ""
        last_decision = ""
        for turn in reversed(turns):
            if turn.role == "user" and not last_user:
                last_user = turn.text
                last_decision = turn.decision
            if turn.role == "assistant" and not last_assistant:
                last_assistant = turn.text
            if last_user and last_assistant:
                break

        # Dominant dialect (most common)
        dominant_dialect = ""
        if dialects:
            counts = {}
            for d in dialects:
                counts[d] = counts.get(d, 0) + 1
            dominant_dialect = max(counts, key=counts.get)

        # Conversation tone
        tone = self._assess_tone(arc)

        # Recent turns as dicts (for context injection)
        recent = []
        for turn in turns[-5:]:
            recent.append({
                "role": turn.role,
                "text": turn.text[:200],  # truncate for context window
                "emotion": turn.emotional_state,
                "load": turn.load_bearing,
            })

        return ConversationContext(
            turn_count=len(turns),
            last_user_text=last_user,
            last_assistant_text=last_assistant,
            emotional_arc={
                "dominant": arc.dominant_emotion,
                "shifted": arc.shifted,
                "escalated": arc.escalated,
                "load_bearing_count": arc.load_bearing_count,
                "recent_states": arc.states[-5:] if arc.states else [],
            },
            dominant_dialect=dominant_dialect,
            topics_mentioned=list(topics),
            load_bearing_moments=arc.load_bearing_count,
            last_decision=last_decision,
            conversation_tone=tone,
            recent_turns=recent,
        )

    # ── Context as dict (for pipeline integration) ──

    def get_context_dict(self, relationship_key: str) -> dict:
        """Get context as a plain dict — easy to merge into pipeline payloads."""
        ctx = self.get_context(relationship_key)
        return asdict(ctx)

    # ── For the LLM: format context as natural language ──

    def get_context_prompt(self, relationship_key: str) -> str:
        """
        Format conversation context as a natural language prompt section.
        This gets injected into the LLM's meaning_instruction.
        """
        ctx = self.get_context(relationship_key)

        if ctx.turn_count == 0:
            return "هذي أول رسالة من هالشخص. ما عندنا تاريخ سابق."

        parts = []

        # Turn count
        parts.append(f"هذي المحادثة فيها {ctx.turn_count} رسالة.")

        # Emotional arc
        arc = ctx.emotional_arc
        if arc.get("escalated"):
            parts.append("الشخص حالته النفسية تثاقلت خلال المحادثة — انتبه وتعامل بعطف.")
        elif arc.get("shifted"):
            parts.append("مشاعر الشخص تغيرت خلال المحادثة.")

        if arc.get("load_bearing_count", 0) > 0:
            parts.append(f"مرّ بـ {arc['load_bearing_count']} لحظات ثقيلة في المحادثة.")

        dominant = arc.get("dominant", "clear")
        emotion_map = {
            "carrying_weight": "يحمل ثقل",
            "frustrated": "محبط",
            "lost": "تايه",
            "excited": "متحمس",
            "clear": "واضح ومرتاح",
        }
        if dominant in emotion_map:
            parts.append(f"الحالة الغالبة: {emotion_map[dominant]}.")

        # Dialect
        if ctx.dominant_dialect:
            parts.append(f"اللهجة: {ctx.dominant_dialect}.")

        # Tone
        tone_map = {
            "heavy": "المحادثة ثقيلة — تعامل بلطف زيادة.",
            "tense": "في توتر — اهدي الجو قبل ما تجاوب.",
            "warm": "المحادثة دافية ومريحة.",
            "neutral": "",
        }
        tone_note = tone_map.get(ctx.conversation_tone, "")
        if tone_note:
            parts.append(tone_note)

        # Last exchange
        if ctx.last_user_text:
            parts.append(f"آخر شي قال: \"{ctx.last_user_text[:100]}\"")
        if ctx.last_assistant_text:
            parts.append(f"آخر شي قلنا: \"{ctx.last_assistant_text[:100]}\"")

        return "\n".join(parts)

    # ── Clear ──

    def clear(self, relationship_key: str):
        """Clear all memory for a relationship."""
        self._turns.pop(relationship_key, None)
        self._arcs.pop(relationship_key, None)
        self._dialects.pop(relationship_key, None)
        self._topics.pop(relationship_key, None)

    # ── Internal helpers ──

    def _assess_tone(self, arc: EmotionalArc) -> str:
        """Assess overall conversation tone from emotional arc."""
        if arc.load_bearing_count >= 2 or arc.dominant_emotion == "carrying_weight":
            return "heavy"
        if arc.escalated or arc.dominant_emotion == "frustrated":
            return "tense"
        if arc.dominant_emotion == "excited":
            return "warm"
        return "neutral"

    def _extract_topics(self, relationship_key: str, text: str):
        """Simple topic extraction from text."""
        import re
        low = text.lower()
        norm = re.sub(r'[ًٌٍَُِّْ]', '', text)

        # Arabic topic markers
        topic_patterns = {
            "مشروع": "project",
            "سعر": "pricing",
            "فلوس": "money",
            "تصميم": "design",
            "مشكل": "problem",
            "مساعد": "help",
            "نظام": "system",
            "تطبيق": "app",
            "موقع": "website",
            "تسويق": "marketing",
            "بيع": "sales",
            "عميل": "client",
        }

        # English topic markers
        en_topics = {
            "project": "project",
            "price": "pricing",
            "design": "design",
            "problem": "problem",
            "help": "help",
            "system": "system",
            "app": "app",
            "website": "website",
            "marketing": "marketing",
            "sales": "sales",
            "client": "client",
        }

        topics = self._topics[relationship_key]
        for marker, topic in topic_patterns.items():
            if marker in norm:
                topics.add(topic)
        for marker, topic in en_topics.items():
            if marker in low:
                topics.add(topic)

    # ── Persistence ──

    def _get_persist_path(self, relationship_key: str) -> str:
        safe_key = relationship_key.replace("/", "_").replace("\\", "_")
        return os.path.join(self.persist_dir, f"{safe_key}.json")

    def save(self, relationship_key: str):
        """Save conversation memory to disk."""
        if not self.persist_dir:
            return

        data = {
            "relationship_key": relationship_key,
            "saved_at": time.time(),
            "turn_count": len(self._turns.get(relationship_key, [])),
            "emotional_arc": {
                "states": self._arcs.get(relationship_key, EmotionalArc()).states,
                "load_bearing_count": self._arcs.get(relationship_key, EmotionalArc()).load_bearing_count,
            },
            "dialects": self._dialects.get(relationship_key, []),
            "topics": list(self._topics.get(relationship_key, set())),
            # We save meaning, not raw text (privacy)
            "turns_summary": [
                {
                    "role": t.role,
                    "emotion": t.emotional_state,
                    "load": t.load_bearing,
                    "decision": t.decision,
                    "ts": t.timestamp,
                }
                for t in self._turns.get(relationship_key, [])
            ],
        }

        path = self._get_persist_path(relationship_key)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_persistent(self):
        """Load all persistent memories from disk."""
        if not self.persist_dir or not os.path.exists(self.persist_dir):
            return

        for fname in os.listdir(self.persist_dir):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(self.persist_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                key = data.get("relationship_key", fname.replace(".json", ""))

                # Restore emotional arc
                arc_data = data.get("emotional_arc", {})
                arc = EmotionalArc()
                arc.states = arc_data.get("states", [])
                arc.load_bearing_count = arc_data.get("load_bearing_count", 0)
                if arc.states:
                    counts = {}
                    for s in arc.states:
                        counts[s] = counts.get(s, 0) + 1
                    arc.dominant_emotion = max(counts, key=counts.get)
                    arc.shifted = len(set(arc.states)) > 1
                self._arcs[key] = arc

                # Restore dialect tracking
                self._dialects[key] = data.get("dialects", [])

                # Restore topics
                self._topics[key] = set(data.get("topics", []))
            except Exception:
                continue  # skip corrupted files


# ═══════════════════════════════════════════════════════════
#  Demo
# ═══════════════════════════════════════════════════════════

def demo():
    """Simulate a conversation and show memory in action."""

    # Fake IntentReading for demo (mimics the real dataclass)
    class FakeReading:
        def __init__(self, emotion, dialect, load, decision):
            self.emotional_state = emotion
            self.dialect_detected = dialect
            self.load_bearing = load
            self.decision = decision
            self.mode = "NORMAL"

    memory = AATIFConversationMemory()
    key = "966501234567"

    print("=" * 60)
    print("  AATIF Conversation Memory — عاطف يتذكر")
    print("=" * 60)

    # Turn 1: User greets
    reading1 = FakeReading("clear", "saudi", False, "EXECUTE")
    memory.add_turn(key, "user", "السلام عليكم، كيف الحال؟", reading=reading1)
    memory.add_turn(key, "assistant", "وعليكم السلام! الحمدلله، كيف أقدر أساعدك؟")
    print("\n  Turn 1: سلام عادي")

    # Turn 2: User asks about project
    reading2 = FakeReading("excited", "saudi", False, "EXECUTE")
    memory.add_turn(key, "user", "ابي أعرف عن المشروع اللي عندكم", reading=reading2)
    memory.add_turn(key, "assistant", "أكيد! خلني أشرح لك بالتفصيل")
    print("  Turn 2: سؤال عن المشروع")

    # Turn 3: User gets frustrated
    reading3 = FakeReading("frustrated", "saudi", False, "CLARIFY")
    memory.add_turn(key, "user", "ما فهمت شي من الكلام اللي قلته", reading=reading3)
    memory.add_turn(key, "assistant", "حقك، خلني أبسطها أكثر")
    print("  Turn 3: إحباط")

    # Turn 4: User shares something heavy
    reading4 = FakeReading("carrying_weight", "saudi", True, "EXECUTE")
    memory.add_turn(key, "user", "تعبت من المشروع صراحة مش عارف أكمل", reading=reading4)
    print("  Turn 4: لحظة ثقيلة")

    # Now get context
    ctx = memory.get_context(key)
    prompt = memory.get_context_prompt(key)

    print(f"\n{'─' * 60}")
    print(f"  Context Summary:")
    print(f"  Turns: {ctx.turn_count}")
    print(f"  Dialect: {ctx.dominant_dialect}")
    print(f"  Tone: {ctx.conversation_tone}")
    print(f"  Load-bearing moments: {ctx.load_bearing_moments}")
    print(f"  Emotional arc: {ctx.emotional_arc}")
    print(f"  Topics: {ctx.topics_mentioned}")

    print(f"\n{'─' * 60}")
    print(f"  LLM Context Prompt (يتحقن في meaning_instruction):")
    print(f"{'─' * 60}")
    print(prompt)

    print(f"\n{'=' * 60}")
    print(f"  عاطف يتذكر — مش بس الكلام، يتذكر المشاعر")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    demo()
