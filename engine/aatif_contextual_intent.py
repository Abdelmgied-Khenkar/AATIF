#!/usr/bin/env python3
"""
AATIF Contextual Intent Scorer — النية في سياقها
==================================================

The THIRD LAYER integration of عاطف's understanding triad:

    I scorer    = اللحظة   (THIS message's intent — single-turn)
    Fingerprint = النمط    (the user's PATTERN over time)
    Memory      = الحقائق  (what happened and when)

    Contextual  = الفهم    (THIS MODULE — integrates all three)

Why this exists:
  The raw I scorer reads ONE message. It cannot distinguish:
    - "asking because confused" vs "asking for confirmation"
    - "heard contradictory info" vs "forgot the answer"

  All four look identical in a single message. The distinction
  requires conversation history (Memory) + behavioral pattern
  (Fingerprint).

Design principles:
  - WRAPPER, not modification: the raw I score is NEVER changed.
    It stays as the base safety signal for the S equation.
  - This module produces ADDITIONAL METADATA that helps the
    Governor choose the right RESPONSE STRATEGY, not the right
    safety decision.
  - Graceful degradation: works without Fingerprint, without
    Memory, or without both (falls back to raw I score only).
  - No embeddings of its own — delegates to SemanticIntentScorer.
  - Deterministic context logic — no ML, pure decision tree.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════
#  Soft imports — all three dependencies are OPTIONAL
# ═══════════════════════════════════════════════════════════

# SemanticIntentScorer — the base I scorer
try:
    from aatif_intent_scorer import SemanticIntentScorer
except ImportError:
    try:
        from engine.aatif_intent_scorer import SemanticIntentScorer
    except ImportError:
        SemanticIntentScorer = None  # type: ignore

# UserFingerprint + dataclasses
try:
    from aatif_fingerprint import (
        UserFingerprint, FingerprintReading, RepetitionContext,
    )
except ImportError:
    try:
        from engine.aatif_fingerprint import (
            UserFingerprint, FingerprintReading, RepetitionContext,
        )
    except ImportError:
        UserFingerprint = None  # type: ignore
        FingerprintReading = None  # type: ignore
        RepetitionContext = None  # type: ignore

# TemporalMemory + dataclasses
try:
    from aatif_temporal_memory import (
        TemporalMemory, TemporalContext, MemoryEntry,
    )
except ImportError:
    try:
        from engine.aatif_temporal_memory import (
            TemporalMemory, TemporalContext, MemoryEntry,
        )
    except ImportError:
        TemporalMemory = None  # type: ignore
        TemporalContext = None  # type: ignore
        MemoryEntry = None  # type: ignore

# Arabic text utilities — shared normalization
try:
    from aatif_arabic_utils import normalize_arabic
except ImportError:
    try:
        from engine.aatif_arabic_utils import normalize_arabic
    except ImportError:
        def normalize_arabic(text: str) -> str:  # type: ignore[misc]
            return text  # passthrough if unavailable


# ═══════════════════════════════════════════════════════════
#  APPROACH MATRIX — maps (repeat_reason, comprehension) to strategy
# ═══════════════════════════════════════════════════════════

# Each entry: (repeat_reason, user_comprehension) -> suggested_approach
# "any" matches all comprehension levels
_APPROACH_MATRIX: Dict[Tuple[str, str], str] = {
    ("confusion", "needs_examples"):    "use_concrete_example",
    ("confusion", "needs_step_by_step"): "break_into_steps",
    ("confusion", "quick"):             "try_different_analogy",
    ("confirmation", "needs_examples"): "brief_yes_with_nuance",
    ("confirmation", "needs_step_by_step"): "brief_yes_with_nuance",
    ("confirmation", "quick"):          "brief_yes_with_nuance",
    ("contradiction", "needs_examples"): "acknowledge_source_then_clarify",
    ("contradiction", "needs_step_by_step"): "acknowledge_source_then_clarify",
    ("contradiction", "quick"):         "acknowledge_source_then_clarify",
    ("forgot", "needs_examples"):       "gentle_reminder_with_context",
    ("forgot", "needs_step_by_step"):   "gentle_reminder_with_context",
    ("forgot", "quick"):                "gentle_reminder_with_context",
    ("new_angle", "needs_examples"):    "address_specific_angle",
    ("new_angle", "needs_step_by_step"): "address_specific_angle",
    ("new_angle", "quick"):             "address_specific_angle",
    ("not_repeat", "needs_examples"):   "standard",
    ("not_repeat", "needs_step_by_step"): "standard",
    ("not_repeat", "quick"):            "standard",
}

def _lookup_approach(repeat_reason: str, comprehension: str) -> str:
    """Look up suggested approach from the matrix."""
    key = (repeat_reason, comprehension)
    return _APPROACH_MATRIX.get(key, "standard")


# Human-readable reasoning templates
_APPROACH_REASONING: Dict[str, str] = {
    "use_concrete_example": (
        "User is confused and learns best with examples. "
        "Previous explanation did not land — try a concrete, "
        "relatable example instead of abstract description."
    ),
    "break_into_steps": (
        "User is confused and needs step-by-step guidance. "
        "Break the answer into numbered steps with clear transitions."
    ),
    "try_different_analogy": (
        "User is confused but usually grasps things quickly. "
        "The current framing is not clicking — try a completely "
        "different analogy or perspective."
    ),
    "brief_yes_with_nuance": (
        "User is confirming, not re-asking. A brief confirmation "
        "with optional nuance is sufficient — do not re-explain."
    ),
    "acknowledge_source_then_clarify": (
        "User received contradictory information. Acknowledge that "
        "different sources may say different things, then clarify "
        "what is accurate and why."
    ),
    "gentle_reminder_with_context": (
        "User forgot a previous answer. Gently re-explain without "
        "making them feel bad about forgetting. Add context about "
        "when and what was discussed before."
    ),
    "address_specific_angle": (
        "User is approaching the same topic from a new angle. "
        "Address the specific variation in their question rather "
        "than repeating the full original answer."
    ),
    "standard": (
        "No special contextual adjustment needed. Respond normally "
        "according to the user's communication style."
    ),
}


# ═══════════════════════════════════════════════════════════
#  IntentContext — the enriched output
# ═══════════════════════════════════════════════════════════

@dataclass
class IntentContext:
    """
    Enhanced intent reading with multi-turn context.

    The raw I score is PRESERVED — it feeds the S equation unchanged.
    Everything else here is ADDITIONAL metadata for the Governor's
    response strategy.
    """
    # --- From base I scorer (unchanged) ---
    raw_i_score: float          # original I score from SemanticIntentScorer
    raw_confidence: str         # "high", "medium", "low"
    raw_category: str           # "constructive", "harmful", etc.

    # --- From repetition analysis ---
    is_repeat_question: bool
    times_asked: int            # how many times similar question was asked
    repeat_reason: str          # "confirmation", "confusion", "contradiction",
                                # "forgot", "new_angle", "not_repeat"

    # --- From fingerprint ---
    user_pattern: str           # "asks_once", "repeats_to_confirm",
                                # "repeats_when_confused"
    user_comprehension: str     # "quick", "needs_examples", "needs_step_by_step"
    user_trust_level: float     # 0.0-1.0

    # --- From temporal memory ---
    previous_explanations_count: int    # how many times we explained this topic
    last_explanation_approach: Optional[str]  # what approach was used last time
    topic_history: List[str]            # recent topics
    emotional_trajectory: str           # "improving", "stable", "declining"

    # --- Computed recommendations ---
    suggested_approach: str     # "use_concrete_example", "brief_yes_with_nuance", etc.
    approach_reasoning: str     # human-readable why
    confidence: float           # overall confidence in this contextual reading


# ═══════════════════════════════════════════════════════════
#  ConversationFlow — flow analysis output
# ═══════════════════════════════════════════════════════════

@dataclass
class ConversationFlow:
    """
    Analysis of conversation flow over recent interactions.

    Detects patterns like escalation, de-escalation, topic jumping,
    or deep dive into a single topic.
    """
    user_id: str
    interaction_count: int          # how many interactions analyzed
    flow_type: str                  # "escalation", "de_escalation",
                                    # "topic_jumping", "deep_dive",
                                    # "steady", "insufficient_data"
    topic_switches: int             # how many times the topic changed
    unique_topics: int              # distinct topics in the window
    dominant_topic: Optional[str]   # most frequent topic, if any
    confusion_trend: str            # "increasing", "decreasing", "stable",
                                    # "insufficient_data"
    intent_trend: str               # "improving", "declining", "stable",
                                    # "insufficient_data"
    summary: str                    # human-readable summary


# ═══════════════════════════════════════════════════════════
#  Category helper — I score to human-readable category
# ═══════════════════════════════════════════════════════════

def _i_to_category(i_score: float) -> str:
    """Map an I score to a human-readable intent category."""
    if i_score >= 0.8:
        return "constructive"
    if i_score >= 0.6:
        return "support_seeking"
    if i_score >= 0.4:
        return "neutral"
    if i_score >= 0.2:
        return "questionable"
    return "harmful"


# ═══════════════════════════════════════════════════════════
#  ContextualIntentScorer — the main class
# ═══════════════════════════════════════════════════════════

class ContextualIntentScorer:
    """
    Wraps SemanticIntentScorer with multi-turn context from
    Fingerprint + TemporalMemory.

    The base I scorer gives a raw intent score (0-1) from text alone.
    This module adds:
    - WHY is the user asking? (repetition context from fingerprint)
    - WHAT happened before? (interaction history from temporal memory)
    - HOW does this user typically behave? (pattern from fingerprint)

    The raw I score is NOT changed — it stays as the base safety signal.
    Instead, this module produces additional metadata that helps the
    Governor choose the right RESPONSE STRATEGY, not the right
    safety decision.

    Usage:
        # Full integration
        scorer = ContextualIntentScorer(
            intent_scorer=SemanticIntentScorer(),
            fingerprint=UserFingerprint(),
            memory=TemporalMemory("/path/to/db"),
        )
        ctx = scorer.score("كيف أسوي لوب؟", user_id="user_123")
        print(ctx.raw_i_score)           # base I score (unchanged)
        print(ctx.suggested_approach)    # contextual suggestion
        print(ctx.approach_reasoning)    # why this approach

        # Minimal — no context, raw I only
        scorer = ContextualIntentScorer()
        ctx = scorer.score("hello")
        print(ctx.raw_i_score)  # works, context fields are defaults
    """

    def __init__(
        self,
        intent_scorer: Optional[object] = None,
        fingerprint: Optional[object] = None,
        memory: Optional[object] = None,
    ):
        """
        Args:
            intent_scorer: a SemanticIntentScorer instance.
                If None, creates one (requires Ollama/bge-m3).
                If that fails, operates in "no-scorer" mode
                (returns I=0.5 for everything).
            fingerprint: a UserFingerprint instance. Optional.
            memory: a TemporalMemory instance. Optional.
        """
        self._scorer = intent_scorer
        self._fingerprint = fingerprint
        self._memory = memory
        self._scorer_available = True

        # Try to create scorer if not provided
        if self._scorer is None and SemanticIntentScorer is not None:
            try:
                self._scorer = SemanticIntentScorer()
            except Exception:
                self._scorer_available = False
        elif self._scorer is None:
            self._scorer_available = False

    # ───────────────────────────────────────────────────
    #  Properties — introspection
    # ───────────────────────────────────────────────────

    @property
    def has_scorer(self) -> bool:
        """Whether the base I scorer is available."""
        return self._scorer is not None and self._scorer_available

    @property
    def has_fingerprint(self) -> bool:
        """Whether a fingerprint module is connected."""
        return self._fingerprint is not None

    @property
    def has_memory(self) -> bool:
        """Whether a temporal memory module is connected."""
        return self._memory is not None

    # ───────────────────────────────────────────────────
    #  score() — the main method
    # ───────────────────────────────────────────────────

    def score(
        self,
        text: str,
        user_id: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
    ) -> IntentContext:
        """
        Score a message with full contextual awareness.

        Args:
            text: the message text to score.
            user_id: optional user identifier. If provided and
                fingerprint/memory are connected, context is enriched.
            conversation_history: optional list of prior messages as
                dicts with keys "role" and "content". Not used yet
                but reserved for future in-session context.

        Returns:
            IntentContext with raw I score + contextual metadata.
        """
        # Step 1: Get raw I score from base scorer
        raw_result = self._get_raw_score(text)
        raw_i = raw_result["I"]
        raw_conf = raw_result["confidence"]
        raw_cat = _i_to_category(raw_i)

        # Step 2: If no user_id, return raw-only context
        if user_id is None:
            return self._raw_only_context(raw_i, raw_conf, raw_cat)

        # Step 3: Get fingerprint context (if available)
        fp_reading = None
        rep_context = None
        if self._fingerprint is not None:
            try:
                fp_reading = self._fingerprint.read(user_id)
                rep_context = self._fingerprint.detect_repetition(
                    user_id, text
                )
            except Exception:
                pass  # graceful degradation

        # Step 4: Get temporal memory context (if available)
        mem_context = None
        if self._memory is not None:
            try:
                mem_context = self._memory.get_context(user_id)
            except Exception:
                pass  # graceful degradation

        # Step 5: Determine repetition context
        is_repeat = False
        times_asked = 0
        repeat_reason = "not_repeat"
        if rep_context is not None and rep_context.is_repeat:
            is_repeat = True
            times_asked = rep_context.times_asked
            repeat_reason = self._classify_repeat_reason(
                rep_context, fp_reading, mem_context
            )

        # Step 6: Extract fingerprint fields
        user_pattern = "asks_once"
        user_comp = "quick"
        user_trust = 0.0
        if fp_reading is not None:
            user_pattern = fp_reading.question_pattern
            user_comp = fp_reading.comprehension_level
            user_trust = fp_reading.trust_level

        # Step 7: Extract temporal memory fields
        prev_explanations = 0
        last_approach = None
        topic_hist: List[str] = []
        emo_trajectory = "insufficient_data"
        if mem_context is not None:
            topic_hist = mem_context.recent_topics
            emo_trajectory = mem_context.emotional_trajectory
            # Count explanations on the current dominant topic
            if topic_hist:
                current_topic = topic_hist[0] if topic_hist else None
                if current_topic and current_topic in mem_context.topic_frequency:
                    prev_explanations = mem_context.topic_frequency[current_topic]

        # Step 8: Determine suggested approach
        suggested = _lookup_approach(repeat_reason, user_comp)
        reasoning = _APPROACH_REASONING.get(suggested, "")

        # Step 9: Compute overall confidence
        confidence = self._compute_confidence(
            raw_conf, fp_reading, mem_context
        )

        return IntentContext(
            raw_i_score=raw_i,
            raw_confidence=raw_conf,
            raw_category=raw_cat,
            is_repeat_question=is_repeat,
            times_asked=times_asked,
            repeat_reason=repeat_reason,
            user_pattern=user_pattern,
            user_comprehension=user_comp,
            user_trust_level=user_trust,
            previous_explanations_count=prev_explanations,
            last_explanation_approach=last_approach,
            topic_history=topic_hist,
            emotional_trajectory=emo_trajectory,
            suggested_approach=suggested,
            approach_reasoning=reasoning,
            confidence=confidence,
        )

    # ───────────────────────────────────────────────────
    #  analyze_conversation_flow()
    # ───────────────────────────────────────────────────

    def analyze_conversation_flow(
        self,
        user_id: str,
        last_n: int = 10,
    ) -> ConversationFlow:
        """
        Analyze the recent conversation flow for a user.

        Looks at the last N interactions and detects patterns:
        - escalation: confusion increasing, intent declining
        - de_escalation: confusion decreasing, satisfaction increasing
        - topic_jumping: frequent topic switches (> 50% of interactions)
        - deep_dive: single topic dominates (> 70% of interactions)
        - steady: none of the above

        Args:
            user_id: the user to analyze.
            last_n: how many interactions to look at (default 10).

        Returns:
            ConversationFlow with flow analysis.
        """
        if self._memory is None:
            return ConversationFlow(
                user_id=user_id,
                interaction_count=0,
                flow_type="insufficient_data",
                topic_switches=0,
                unique_topics=0,
                dominant_topic=None,
                confusion_trend="insufficient_data",
                intent_trend="insufficient_data",
                summary="No temporal memory connected.",
            )

        try:
            entries = self._memory.recall(user_id, limit=last_n)
        except Exception:
            return ConversationFlow(
                user_id=user_id,
                interaction_count=0,
                flow_type="insufficient_data",
                topic_switches=0,
                unique_topics=0,
                dominant_topic=None,
                confusion_trend="insufficient_data",
                intent_trend="insufficient_data",
                summary="Failed to retrieve interaction history.",
            )

        if len(entries) < 2:
            return ConversationFlow(
                user_id=user_id,
                interaction_count=len(entries),
                flow_type="insufficient_data",
                topic_switches=0,
                unique_topics=len(set(e.topic for e in entries if e.topic)),
                dominant_topic=entries[0].topic if entries else None,
                confusion_trend="insufficient_data",
                intent_trend="insufficient_data",
                summary="Not enough interactions to analyze flow.",
            )

        # Reverse to chronological order (recall returns newest first)
        entries = list(reversed(entries))
        n = len(entries)

        # --- Topic analysis ---
        topics = [e.topic for e in entries if e.topic]
        unique_topics = list(set(topics))
        topic_switches = 0
        for i in range(1, len(topics)):
            if topics[i] != topics[i - 1]:
                topic_switches += 1

        # Dominant topic
        topic_counts: Dict[str, int] = {}
        for t in topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1
        dominant_topic = None
        if topic_counts:
            dominant_topic = max(topic_counts, key=topic_counts.get)

        # --- Confusion trend ---
        confusion_trend = self._analyze_trend(
            [1 if e.confusion_detected else 0 for e in entries]
        )

        # --- Intent trend ---
        i_scores = [e.intent_score for e in entries if e.intent_score is not None]
        intent_trend = self._analyze_trend(i_scores) if len(i_scores) >= 2 else "insufficient_data"

        # --- Flow type classification ---
        flow_type = "steady"
        if n > 0 and topics:
            topic_switch_ratio = topic_switches / max(len(topics) - 1, 1)
            dominant_ratio = (
                topic_counts.get(dominant_topic, 0) / max(len(topics), 1)
                if dominant_topic else 0
            )

            if confusion_trend == "increasing" and intent_trend == "decreasing":
                flow_type = "escalation"
            elif confusion_trend == "decreasing" or intent_trend == "increasing":
                flow_type = "de_escalation"
            elif topic_switch_ratio > 0.5:
                flow_type = "topic_jumping"
            elif dominant_ratio >= 0.7:
                flow_type = "deep_dive"

        # --- Build summary ---
        summary = self._build_flow_summary(
            flow_type, n, topic_switches, len(unique_topics),
            dominant_topic, confusion_trend, intent_trend,
        )

        return ConversationFlow(
            user_id=user_id,
            interaction_count=n,
            flow_type=flow_type,
            topic_switches=topic_switches,
            unique_topics=len(unique_topics),
            dominant_topic=dominant_topic,
            confusion_trend=confusion_trend,
            intent_trend=intent_trend,
            summary=summary,
        )

    # ───────────────────────────────────────────────────
    #  predict_next_need()
    # ───────────────────────────────────────────────────

    def predict_next_need(self, user_id: str) -> str:
        """
        Predict what the user will likely need next.

        Based on:
        - Fingerprint patterns (how they typically behave)
        - Temporal memory (what topics they've been exploring)
        - Common learning progressions

        Args:
            user_id: the user to predict for.

        Returns:
            Human-readable prediction, or "insufficient_data".
        """
        fp_reading = None
        mem_context = None

        if self._fingerprint is not None:
            try:
                fp_reading = self._fingerprint.read(user_id)
            except Exception:
                pass

        if self._memory is not None:
            try:
                mem_context = self._memory.get_context(user_id)
            except Exception:
                pass

        # Need at least one source of data
        if fp_reading is None and mem_context is None:
            return "insufficient_data"

        # Need some interaction history
        total = 0
        if fp_reading is not None:
            total = max(total, fp_reading.total_interactions)
        if mem_context is not None:
            total = max(total, mem_context.total_interactions)

        if total < 3:
            return "insufficient_data"

        predictions = []

        # Pattern-based predictions from fingerprint
        if fp_reading is not None:
            if fp_reading.comprehension_level == "needs_examples":
                predictions.append(
                    "User typically asks for examples after conceptual explanation"
                )
            elif fp_reading.comprehension_level == "needs_step_by_step":
                predictions.append(
                    "User typically needs step-by-step walkthrough after overview"
                )

            if fp_reading.question_pattern == "repeats_to_confirm":
                predictions.append(
                    "User will likely ask a confirmation question next"
                )

        # Topic-based predictions from memory
        if mem_context is not None and mem_context.recent_topics:
            topics = mem_context.recent_topics

            # Unresolved topics often come back
            if mem_context.unresolved_topics:
                predictions.append(
                    f"User may revisit unresolved topic: "
                    f"{mem_context.unresolved_topics[0]}"
                )

            # High-frequency topic likely continues
            if mem_context.topic_frequency:
                top = max(
                    mem_context.topic_frequency,
                    key=mem_context.topic_frequency.get,
                )
                count = mem_context.topic_frequency[top]
                if count >= 3:
                    predictions.append(
                        f"User is deeply engaged with '{top}' "
                        f"({count} interactions) — likely to continue"
                    )

        if not predictions:
            return "insufficient_data"

        return predictions[0]

    # ───────────────────────────────────────────────────
    #  Internal helpers
    # ───────────────────────────────────────────────────

    def _get_raw_score(self, text: str) -> Dict:
        """Get raw I score from base scorer, or fallback."""
        if self._scorer is not None:
            try:
                return self._scorer.score(text)
            except Exception:
                pass
        # Fallback: no scorer available → neutral
        return {
            "I": 0.5,
            "confidence": "low",
            "nearest": [],
            "max_similarity": 0.0,
        }

    def _raw_only_context(
        self, raw_i: float, raw_conf: str, raw_cat: str
    ) -> IntentContext:
        """Build IntentContext with raw I score only (no user context)."""
        return IntentContext(
            raw_i_score=raw_i,
            raw_confidence=raw_conf,
            raw_category=raw_cat,
            is_repeat_question=False,
            times_asked=0,
            repeat_reason="not_repeat",
            user_pattern="asks_once",
            user_comprehension="quick",
            user_trust_level=0.0,
            previous_explanations_count=0,
            last_explanation_approach=None,
            topic_history=[],
            emotional_trajectory="insufficient_data",
            suggested_approach="standard",
            approach_reasoning=_APPROACH_REASONING["standard"],
            confidence=self._raw_confidence_to_float(raw_conf),
        )

    def _classify_repeat_reason(
        self,
        rep_context: object,
        fp_reading: Optional[object],
        mem_context: Optional[object],
    ) -> str:
        """
        Classify WHY the user is repeating a question.

        Decision tree:
        1. If fingerprint says "repeats_to_confirm" → "confirmation"
        2. If fingerprint shows confusion > satisfaction → "confusion"
        3. If temporal memory shows different info was given → "contradiction"
        4. If days since last > 7 → "forgot"
        5. If slight variation in question → "new_angle"
        6. Default → "confusion" (safest assumption)
        """
        # Use fingerprint reason if available (it has its own logic)
        fp_reason = getattr(rep_context, "likely_reason", None)

        if fp_reading is not None:
            pattern = getattr(fp_reading, "question_pattern", "asks_once")
            confusion_count = getattr(fp_reading, "confusion_signals", 0)
            satisfaction_count = getattr(fp_reading, "satisfaction_signals", 0)

            # Rule 1: known confirmation pattern
            if pattern == "repeats_to_confirm":
                return "confirmation"

            # Rule 2: confusion signals dominate
            if confusion_count > satisfaction_count:
                return "confusion"

        # Rule 3: check temporal gap → forgot
        if mem_context is not None:
            days_since = getattr(mem_context, "days_since_last", None)
            if days_since is not None and days_since > 7:
                return "forgot"

        # Rule 4: check similarity score — high but not exact → new angle
        sim = getattr(rep_context, "similarity_score", 1.0)
        if 0.6 <= sim < 0.85:
            return "new_angle"

        # Rule 5: use fingerprint's own reasoning if available
        if fp_reason and fp_reason != "none":
            return fp_reason

        # Default: assume confusion (safest — triggers different approach)
        return "confusion"

    def _compute_confidence(
        self,
        raw_conf: str,
        fp_reading: Optional[object],
        mem_context: Optional[object],
    ) -> float:
        """
        Compute overall confidence in the contextual reading.

        Sources of confidence:
        - Raw I scorer confidence (high=0.9, medium=0.6, low=0.3)
        - Fingerprint confidence (if available)
        - Memory total interactions (more = higher)

        Final confidence = weighted average of available sources.
        """
        raw_c = self._raw_confidence_to_float(raw_conf)

        sources = [raw_c]
        weights = [1.0]

        if fp_reading is not None:
            fp_conf = getattr(fp_reading, "confidence", 0.0)
            sources.append(fp_conf)
            weights.append(0.7)

        if mem_context is not None:
            total = getattr(mem_context, "total_interactions", 0)
            # More interactions = higher memory confidence
            if total >= 20:
                mem_conf = 0.9
            elif total >= 10:
                mem_conf = 0.7
            elif total >= 5:
                mem_conf = 0.5
            elif total >= 1:
                mem_conf = 0.3
            else:
                mem_conf = 0.1
            sources.append(mem_conf)
            weights.append(0.5)

        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(sources, weights))
        return round(weighted_sum / total_weight, 4)

    @staticmethod
    def _raw_confidence_to_float(conf: str) -> float:
        """Convert raw confidence string to float."""
        return {"high": 0.9, "medium": 0.6, "low": 0.3}.get(conf, 0.3)

    @staticmethod
    def _analyze_trend(values: list) -> str:
        """
        Analyze a trend in a list of numeric values.

        Returns: "increasing", "decreasing", "stable", "insufficient_data"
        """
        if len(values) < 2:
            return "insufficient_data"

        # Compare first half average to second half average
        mid = len(values) // 2
        if mid == 0:
            mid = 1
        first_half = values[:mid]
        second_half = values[mid:]

        if not first_half or not second_half:
            return "insufficient_data"

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        diff = second_avg - first_avg
        if diff > 0.1:
            return "increasing"
        if diff < -0.1:
            return "decreasing"
        return "stable"

    @staticmethod
    def _build_flow_summary(
        flow_type: str,
        n: int,
        topic_switches: int,
        unique_topics: int,
        dominant_topic: Optional[str],
        confusion_trend: str,
        intent_trend: str,
    ) -> str:
        """Build a human-readable summary of conversation flow."""
        parts = [f"Analyzed {n} interactions."]

        if flow_type == "escalation":
            parts.append(
                "Conversation is escalating: confusion increasing "
                "and intent quality declining. Consider changing approach."
            )
        elif flow_type == "de_escalation":
            parts.append(
                "Conversation is de-escalating: things are improving."
            )
        elif flow_type == "topic_jumping":
            parts.append(
                f"User is jumping between topics "
                f"({topic_switches} switches across {unique_topics} topics). "
                f"May indicate restlessness or searching behavior."
            )
        elif flow_type == "deep_dive":
            parts.append(
                f"User is deeply focused on '{dominant_topic}'. "
                f"Support their deep exploration."
            )
        else:
            parts.append("Conversation flow is steady.")

        return " ".join(parts)


# ═══════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import time as _time
    import tempfile
    import shutil

    print("=" * 60)
    print("  النية في سياقها — AATIF Contextual Intent Scorer")
    print("=" * 60)

    # Test 1: Raw-only mode (no fingerprint, no memory)
    try:
        scorer = ContextualIntentScorer()
        ctx = scorer.score("وش رأيك بالطقس اليوم")
        print(f"\n  [Raw only] I={ctx.raw_i_score:.3f}")
        print(f"  Category: {ctx.raw_category}")
        print(f"  Approach: {ctx.suggested_approach}")
        print(f"  Repeat: {ctx.is_repeat_question}")
    except Exception as e:
        print(f"\n  [Raw only] Scorer unavailable: {e}")
        print("  (This is expected without Ollama/bge-m3)")

    # Test 2: With fingerprint only
    if UserFingerprint is not None:
        fp = UserFingerprint()
        user = "test_user_001"
        msgs = [
            "كيف أسوي لوب في بايثون؟",
            "ما فهمت وضح أكثر",
            "كيف أسوي لوب في بايثون؟",  # repeat
        ]
        ts = _time.time()
        for i, m in enumerate(msgs):
            fp.update(user, m, timestamp=ts + i * 60)

        scorer2 = ContextualIntentScorer(
            intent_scorer=None,
            fingerprint=fp,
        )
        ctx2 = scorer2.score("كيف أسوي لوب في بايثون؟", user_id=user)
        print(f"\n  [With fingerprint]")
        print(f"  Repeat: {ctx2.is_repeat_question}")
        print(f"  Reason: {ctx2.repeat_reason}")
        print(f"  Pattern: {ctx2.user_pattern}")
        print(f"  Approach: {ctx2.suggested_approach}")

    print(f"\n{'=' * 60}")
    print(f"  عاطف يفهم ليش تسأل — مش بس وش تسأل")
    print(f"{'=' * 60}")
