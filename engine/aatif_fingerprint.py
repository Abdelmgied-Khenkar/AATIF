#!/usr/bin/env python3
"""
AATIF Behavioral Fingerprint — بصمة المستخدم
=============================================

The MIDDLE LAYER of عاطف's understanding triad:

    I scorer   = اللحظة  (THIS message's intent — single-turn)
    Fingerprint = النمط   (the user's PATTERN over time — THIS MODULE)
    Memory      = الحقائق (what happened and when — future)

Why this exists:
  The I scorer reads one message. It doesn't know if this is the third
  time someone asked the same question, or whether they usually write
  in Gulf dialect, or that they always show up at 2am.

  The Fingerprint builds a behavioral profile over time by observing
  communication patterns — not by asking (معايشة مش استبيان).
  It provides CONTEXT to the S equation, not OVERRIDE. It informs,
  doesn't decide.

Design principles:
  - Stateless scoring, stateful context: S stays stateless (تربية مش ذاكرة).
    The fingerprint provides context alongside, never overrides safety.
  - Privacy-aware: stores PATTERNS, not raw messages. No PII beyond user_id.
  - Incremental: updates with each message, no full history reprocessing.
  - Lightweight: no embeddings, no ML — pattern matching and counters.
  - Arabic-aware: detects Gulf, Egyptian, MSA dialect markers.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ── Arabic text utilities — shared across the triad ──
try:
    from aatif_arabic_utils import (
        normalize_arabic, tokenize_arabic,
        jaccard_similarity as _jaccard_norm,
        combined_similarity,
    )
    HAS_ARABIC_UTILS = True
except ImportError:
    try:
        from engine.aatif_arabic_utils import (
            normalize_arabic, tokenize_arabic,
            jaccard_similarity as _jaccard_norm,
            combined_similarity,
        )
        HAS_ARABIC_UTILS = True
    except ImportError:
        HAS_ARABIC_UTILS = False


# ═══════════════════════════════════════════════════════════
#  Constants — dialect markers, signal phrases
# ═══════════════════════════════════════════════════════════

# Gulf dialect markers (Saudi, UAE, Kuwait, Qatar, Bahrain, Oman)
_GULF_MARKERS = [
    "وش", "ايش", "ابي", "ابغى", "عشان", "يعني", "خلاص", "طيب",
    "كذا", "يبيله", "حيل", "مره", "وشلون", "يالله", "تراني",
    "اللحين", "الحين", "هالشي", "ذا", "ودي",
]

# Egyptian dialect markers
_EGYPTIAN_MARKERS = [
    "عايز", "ازاي", "كده", "ايه", "ماشي", "حاجه", "حاجة",
    "بتاع", "دي", "ده", "مش", "يعني", "هو", "كمان",
    "عاوز", "فين", "ليه", "بقي", "بقى",
]

# MSA (Modern Standard Arabic) markers
_MSA_MARKERS = [
    "أريد", "أرغب", "يرجى", "لذلك", "بناءً", "حيث",
    "إضافةً", "علاوةً", "من ثم", "وفقاً", "تحديداً",
]

# Interrogative words (for question detection)
_INTERROGATIVES = [
    "ايش", "وش", "هل", "كيف", "ليش", "ليه", "ازاي", "شلون",
    "وين", "فين", "متى", "كم", "مين", "لماذا", "ما هو", "ما هي",
    "شنو", "كيفاش", "واش",
    # English
    "what", "how", "why", "when", "where", "who", "which",
    "can you", "could you", "do you", "is there",
]

# Confusion signals — phrases indicating the user didn't understand
_CONFUSION_SIGNALS = [
    "مش فاهم", "ما فهمت", "يعني ايش", "وضح أكثر", "مرة ثانية",
    "مش واضح", "ما وضحت", "ما فهمتش", "مش فاهمه", "اشرح لي",
    "يعني شو", "مش مستوعب", "وضحلي", "فسرلي", "مش قادر أفهم",
    "ما عرفت", "وش تقصد", "شو يعني", "اعد",
    # English
    "i don't understand", "what do you mean", "can you explain",
    "i'm confused", "not clear", "please clarify", "say again",
    "what does that mean",
]

# Satisfaction signals — phrases indicating positive reception
_SATISFACTION_SIGNALS = [
    "تمام", "فهمت", "حلو", "شكراً", "ممتاز", "واضح", "مشكور",
    "الله يعطيك العافية", "يسلمو", "فاهم", "اوكي", "طيب",
    "بالضبط", "صح", "عين العقل", "يعطيك الف عافية", "جميل",
    "اكيد", "زين", "مضبوط", "أحسنت",
    # English
    "thanks", "got it", "perfect", "great", "understood",
    "makes sense", "clear", "exactly", "wonderful",
]

# Time period names → standard names for active_periods tracking
_HOUR_TO_PERIOD = {
    range(5, 12): "morning",      # 5-11
    range(12, 17): "afternoon",   # 12-16
    range(17, 21): "evening",     # 17-20
}
# 21-4 = late_night (wraps)

# Profile mapping: fingerprint patterns → GATED_PROFILES keys
# This maps user behavioral patterns to suggested governance profiles.
_PROFILE_SUGGESTIONS = {
    ("formal", "quick"):      "default",
    ("formal", "needs_step_by_step"): "high_sensitivity",
    ("casual", "quick"):      "relaxed",
    ("casual", "needs_examples"):     "default",
    ("mixed", "quick"):       "default",
    ("mixed", "needs_step_by_step"):  "high_sensitivity",
    ("mixed", "needs_examples"):      "default",
}


# ═══════════════════════════════════════════════════════════
#  RepetitionContext — what detect_repetition returns
# ═══════════════════════════════════════════════════════════

@dataclass
class RepetitionContext:
    """
    Context about a repeated question.

    When a user asks something similar to a previous question,
    this tells us WHY they might be repeating — so the system
    can respond differently each time.
    """
    is_repeat: bool
    times_asked: int
    previous_questions: List[str]     # the similar questions found
    likely_reason: str                # "confirmation", "confusion", "contradiction", "forgot", "none"
    similarity_score: float           # Jaccard similarity to closest match
    suggested_action: str             # what to do about it


# ═══════════════════════════════════════════════════════════
#  FingerprintReading — snapshot of a user's behavioral profile
# ═══════════════════════════════════════════════════════════

@dataclass
class FingerprintReading:
    """
    A fingerprint snapshot for a specific user — بصمة المستخدم.

    This is what the pipeline receives: structured context about
    who this person IS behaviorally, built from observation over time.
    """
    user_id: str
    communication_style: str          # "formal", "casual", "mixed"
    question_pattern: str             # "asks_once", "repeats_to_confirm",
                                      # "repeats_when_confused", "asks_to_challenge"
    comprehension_level: str          # "quick", "needs_examples", "needs_step_by_step"
    emotional_baseline: str           # "calm", "anxious", "enthusiastic", "variable"
    active_periods: List[str]         # ["morning", "evening", "late_night"]
    interaction_frequency: str        # "daily", "weekly", "occasional", "first_time"
    language_preference: str          # "msa", "gulf_dialect", "egyptian_dialect", "mixed"
    repeat_question_count: int        # how many times they've asked similar questions
    last_interaction: Optional[float] # unix timestamp of last interaction
    total_interactions: int
    trust_level: float                # 0.0 to 1.0 — built over time
    confusion_signals: int            # count of detected confusion moments
    satisfaction_signals: int         # count of positive responses

    # Computed fields
    suggested_profile: str            # maps to GATED_PROFILES key
    suggested_approach: str           # human-readable suggestion for response strategy
    confidence: float                 # how reliable this fingerprint is (more data = higher)


# ═══════════════════════════════════════════════════════════
#  Internal storage dataclass — what we persist per user
# ═══════════════════════════════════════════════════════════

@dataclass
class _UserData:
    """Internal mutable state for one user. Not exposed externally."""
    user_id: str
    # Style counts
    formal_count: int = 0
    casual_count: int = 0
    # Language counts
    gulf_count: int = 0
    egyptian_count: int = 0
    msa_count: int = 0
    other_lang_count: int = 0
    # Interaction tracking
    total_interactions: int = 0
    first_interaction: Optional[float] = None
    last_interaction: Optional[float] = None
    # Period tracking — count messages per period
    period_counts: Dict[str, int] = field(default_factory=dict)
    # Question tracking
    questions_asked: List[str] = field(default_factory=list)
    repeat_question_count: int = 0
    # Comprehension tracking
    confusion_signals: int = 0
    satisfaction_signals: int = 0
    # Emotional signal counts
    calm_count: int = 0
    anxious_count: int = 0
    enthusiastic_count: int = 0
    # Trust accumulates over time
    trust_level: float = 0.0

    # H2 FIX: cap stored questions to prevent unbounded growth
    MAX_STORED_QUESTIONS: int = 200


# ═══════════════════════════════════════════════════════════
#  Helper functions
# ═══════════════════════════════════════════════════════════

def _tokenize(text: str) -> set:
    """
    Simple word tokenizer for Jaccard similarity.

    Strips punctuation, lowercases, splits on whitespace.
    Works for both Arabic and English.
    """
    # Remove common punctuation (keep Arabic characters)
    cleaned = re.sub(r'[؟?!.,;:،؛\-\(\)\[\]{}"\'`]', ' ', text)
    tokens = cleaned.lower().split()
    # Filter very short tokens (likely noise)
    return {t for t in tokens if len(t) > 1}


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """Jaccard similarity between two sets of tokens."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def _detect_language(text: str) -> str:
    """
    Detect language preference from text.

    Returns: "gulf_dialect", "egyptian_dialect", "msa", "other"
    """
    t = text.strip().lower()

    gulf_hits = sum(1 for m in _GULF_MARKERS if m in t)
    egyptian_hits = sum(1 for m in _EGYPTIAN_MARKERS if m in t)
    msa_hits = sum(1 for m in _MSA_MARKERS if m in t)

    # Threshold: at least 1 marker hit
    if gulf_hits > egyptian_hits and gulf_hits > msa_hits and gulf_hits >= 1:
        return "gulf_dialect"
    if egyptian_hits > gulf_hits and egyptian_hits > msa_hits and egyptian_hits >= 1:
        return "egyptian_dialect"
    if msa_hits >= 1 and msa_hits >= gulf_hits and msa_hits >= egyptian_hits:
        return "msa"
    return "other"


def _detect_style(text: str) -> str:
    """
    Detect communication style from a single message.

    Returns: "formal", "casual", "mixed"
    """
    t = text.strip()
    if not t:
        return "mixed"

    words = t.split()
    word_count = len(words)

    casual_signals = 0
    formal_signals = 0

    # Emoji presence → casual
    if re.search(r'[\U0001F300-\U0001F9FF]', t):
        casual_signals += 2

    # Short messages (< 5 words) → casual
    if word_count < 5:
        casual_signals += 1

    # Dialect markers → casual
    t_lower = t.lower()
    for m in _GULF_MARKERS + _EGYPTIAN_MARKERS:
        if m in t_lower:
            casual_signals += 1
            break

    # MSA markers → formal
    for m in _MSA_MARKERS:
        if m in t_lower:
            formal_signals += 1
            break

    # Complete sentences (period/full stop) → formal
    if "." in t or "." in t:
        formal_signals += 1

    # Long messages (> 15 words) → slightly formal
    if word_count > 15:
        formal_signals += 1

    if casual_signals > formal_signals:
        return "casual"
    if formal_signals > casual_signals:
        return "formal"
    return "mixed"


def _is_question(text: str) -> bool:
    """Check if a message is a question."""
    t = text.strip().lower()
    # Explicit question marks
    if "?" in t or "؟" in t:
        return True
    # Interrogative words
    for word in _INTERROGATIVES:
        if word in t:
            return True
    return False


def _has_confusion_signal(text: str) -> bool:
    """Check if a message contains confusion indicators."""
    t = text.strip().lower()
    for signal in _CONFUSION_SIGNALS:
        if signal in t:
            return True
    return False


def _has_satisfaction_signal(text: str) -> bool:
    """
    Check if a message contains satisfaction indicators.

    Important: negated satisfaction words are NOT satisfaction.
    "مش فاهم" contains "فاهم" but is confusion, not satisfaction.
    We check confusion signals first — if the text is confused,
    any satisfaction word that's part of a negation is skipped.
    """
    t = text.strip().lower()

    # Arabic negation prefixes that flip meaning
    _NEGATIONS = ["مش ", "ما ", "مو ", "لا "]

    for signal in _SATISFACTION_SIGNALS:
        if signal in t:
            # Check if this signal word is preceded by a negation
            idx = t.find(signal)
            negated = False
            for neg in _NEGATIONS:
                # Check if negation immediately precedes the signal
                neg_start = idx - len(neg)
                if neg_start >= 0 and t[neg_start:idx] == neg:
                    negated = True
                    break
            if not negated:
                return True
    return False


def _detect_emotional_signal(text: str) -> str:
    """
    Detect emotional tone from a message.

    Returns: "calm", "anxious", "enthusiastic"
    Light heuristic — not a replacement for the E scorer.
    """
    t = text.strip().lower()

    # Enthusiastic signals
    enthusiastic_markers = ["!", "ممتاز", "رهيب", "حلو", "يا سلام", "واو",
                           "amazing", "awesome", "great", "love", "excited"]
    for m in enthusiastic_markers:
        if m in t:
            return "enthusiastic"

    # Anxious signals
    anxious_markers = ["قلقان", "خايف", "محتار", "ضاغط", "مضغوط", "مش عارف",
                       "worried", "anxious", "stressed", "nervous", "scared"]
    for m in anxious_markers:
        if m in t:
            return "anxious"

    return "calm"


def _hour_to_period(hour: int) -> str:
    """Map hour (0-23) to interaction period name."""
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "late_night"


# ═══════════════════════════════════════════════════════════
#  UserFingerprint — the main engine
# ═══════════════════════════════════════════════════════════

class UserFingerprint:
    """
    بصمة المستخدم — builds and maintains behavioral profiles.

    Observes communication patterns over time (معايشة مش استبيان).
    Provides context to the pipeline — never overrides safety decisions.

    Usage:
        fp = UserFingerprint()
        fp.update("user_123", "وش الأخبار؟", timestamp=time.time())
        fp.update("user_123", "ما فهمت وضح أكثر", timestamp=time.time())
        reading = fp.read("user_123")
        print(reading.communication_style)   # → "casual"
        print(reading.confusion_signals)     # → 1

        rep = fp.detect_repetition("user_123", "وش الأخبار؟")
        print(rep.is_repeat)                 # → True
        print(rep.likely_reason)             # → "confirmation"
    """

    # Jaccard similarity threshold for repeat detection
    REPEAT_THRESHOLD = 0.6

    # Trust increment per interaction (asymptotic toward 1.0)
    TRUST_INCREMENT = 0.02

    # Maximum trust level
    TRUST_MAX = 1.0

    # Trust decay: fraction lost per day of inactivity
    TRUST_DECAY_PER_DAY = 0.01

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        *,
        repeat_threshold: Optional[float] = None,
        trust_increment: Optional[float] = None,
        trust_max: Optional[float] = None,
        trust_decay_per_day: Optional[float] = None,
    ):
        """
        Args:
            storage_dir: directory for persisting fingerprints to JSON.
                If None, fingerprints stay in memory only.
            repeat_threshold: override REPEAT_THRESHOLD (default 0.6).
            trust_increment: override TRUST_INCREMENT (default 0.02).
            trust_max: override TRUST_MAX (default 1.0).
            trust_decay_per_day: override TRUST_DECAY_PER_DAY (default 0.01).
        """
        self._users: Dict[str, _UserData] = {}
        self.storage_dir = storage_dir
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)

        # Apply overrides — configurable thresholds (consensus fix #6)
        if repeat_threshold is not None:
            self.REPEAT_THRESHOLD = repeat_threshold
        if trust_increment is not None:
            self.TRUST_INCREMENT = trust_increment
        if trust_max is not None:
            self.TRUST_MAX = trust_max
        if trust_decay_per_day is not None:
            self.TRUST_DECAY_PER_DAY = trust_decay_per_day

    # ───────────────────────────────────────────────────
    #  update() — process a new message
    # ───────────────────────────────────────────────────

    def update(
        self,
        user_id: str,
        message: str,
        timestamp: Optional[float] = None,
        role: str = "user",
    ) -> None:
        """
        Process a new message and update the user's fingerprint.

        Only user messages update the fingerprint — assistant messages
        are ignored (we observe the person, not ourselves).

        Args:
            user_id: unique identifier for the user.
            message: the message text.
            timestamp: unix timestamp (None = now).
            role: "user" or "assistant". Only "user" updates the fingerprint.
        """
        if role != "user":
            return

        if not message or not message.strip():
            return

        ts = timestamp if timestamp is not None else time.time()

        # Get or create user data
        if user_id not in self._users:
            self._users[user_id] = _UserData(user_id=user_id)
        data = self._users[user_id]

        # --- Update interaction tracking ---
        data.total_interactions += 1
        if data.first_interaction is None:
            data.first_interaction = ts
        prev_interaction = data.last_interaction  # save for trust decay
        data.last_interaction = ts

        # --- Update communication style ---
        style = _detect_style(message)
        if style == "formal":
            data.formal_count += 1
        elif style == "casual":
            data.casual_count += 1
        # "mixed" doesn't increment either — it's the default

        # --- Update language preference ---
        lang = _detect_language(message)
        if lang == "gulf_dialect":
            data.gulf_count += 1
        elif lang == "egyptian_dialect":
            data.egyptian_count += 1
        elif lang == "msa":
            data.msa_count += 1
        else:
            data.other_lang_count += 1

        # --- Track active periods ---
        dt = datetime.fromtimestamp(ts)
        period = _hour_to_period(dt.hour)
        data.period_counts[period] = data.period_counts.get(period, 0) + 1

        # --- Track questions ---
        if _is_question(message):
            # Check for repetition before adding (consensus fix #2, #4)
            for prev_q in data.questions_asked:
                if HAS_ARABIC_UTILS:
                    sim = combined_similarity(message, prev_q)
                else:
                    tokens = _tokenize(message)
                    prev_tokens = _tokenize(prev_q)
                    sim = _jaccard_similarity(tokens, prev_tokens)
                if sim >= self.REPEAT_THRESHOLD:
                    data.repeat_question_count += 1
                    break

            data.questions_asked.append(message)
            # Cap stored questions (H2 pattern)
            if len(data.questions_asked) > data.MAX_STORED_QUESTIONS:
                data.questions_asked = data.questions_asked[-data.MAX_STORED_QUESTIONS:]

        # --- Track confusion/satisfaction signals ---
        if _has_confusion_signal(message):
            data.confusion_signals += 1
        if _has_satisfaction_signal(message):
            data.satisfaction_signals += 1

        # --- Track emotional signals ---
        emotion = _detect_emotional_signal(message)
        if emotion == "calm":
            data.calm_count += 1
        elif emotion == "anxious":
            data.anxious_count += 1
        elif emotion == "enthusiastic":
            data.enthusiastic_count += 1

        # --- Apply trust decay based on inactivity (consensus fix #3) ---
        # Trust decays linearly with days since last interaction.
        # Decay happens BEFORE the new increment so returning users
        # see their trust drop then partially recover this turn.
        if prev_interaction is not None and data.total_interactions > 1:
            days_inactive = (ts - prev_interaction) / 86400.0
            if days_inactive > 0:
                decay = self.TRUST_DECAY_PER_DAY * days_inactive
                data.trust_level = max(0.0, data.trust_level - decay)

        # --- Update trust level ---
        # Trust grows logarithmically — fast early, asymptotic later.
        # Each interaction adds less trust as total grows.
        if data.total_interactions <= 1:
            data.trust_level = 0.1
        else:
            data.trust_level = min(
                self.TRUST_MAX,
                data.trust_level + self.TRUST_INCREMENT * (1.0 - data.trust_level)
            )

    # ───────────────────────────────────────────────────
    #  read() — return current fingerprint snapshot
    # ───────────────────────────────────────────────────

    def read(self, user_id: str) -> FingerprintReading:
        """
        Return the current fingerprint snapshot for a user.

        If the user has no history, returns a default "unknown"
        fingerprint with low confidence.

        Args:
            user_id: unique identifier for the user.

        Returns:
            FingerprintReading with all computed fields.
        """
        if user_id not in self._users:
            return self._default_reading(user_id)

        data = self._users[user_id]
        if data.total_interactions == 0:
            return self._default_reading(user_id)

        # --- Compute communication style ---
        comm_style = self._compute_comm_style(data)

        # --- Compute language preference ---
        lang_pref = self._compute_language_pref(data)

        # --- Compute question pattern ---
        question_pattern = self._compute_question_pattern(data)

        # --- Compute comprehension level ---
        comp_level = self._compute_comprehension_level(data)

        # --- Compute emotional baseline ---
        emo_baseline = self._compute_emotional_baseline(data)

        # --- Compute active periods ---
        active = self._compute_active_periods(data)

        # --- Compute interaction frequency ---
        freq = self._compute_interaction_frequency(data)

        # --- Compute confidence ---
        confidence = self._compute_confidence(data)

        # --- Compute suggested profile ---
        suggested_profile = _PROFILE_SUGGESTIONS.get(
            (comm_style, comp_level), "default"
        )

        # --- Compute suggested approach ---
        approach = self._compute_suggested_approach(
            comm_style, comp_level, question_pattern, emo_baseline
        )

        return FingerprintReading(
            user_id=user_id,
            communication_style=comm_style,
            question_pattern=question_pattern,
            comprehension_level=comp_level,
            emotional_baseline=emo_baseline,
            active_periods=active,
            interaction_frequency=freq,
            language_preference=lang_pref,
            repeat_question_count=data.repeat_question_count,
            last_interaction=data.last_interaction,
            total_interactions=data.total_interactions,
            trust_level=round(data.trust_level, 4),
            confusion_signals=data.confusion_signals,
            satisfaction_signals=data.satisfaction_signals,
            suggested_profile=suggested_profile,
            suggested_approach=approach,
            confidence=round(confidence, 4),
        )

    # ───────────────────────────────────────────────────
    #  detect_repetition() — the KEY differentiator
    # ───────────────────────────────────────────────────

    def detect_repetition(
        self, user_id: str, current_message: str
    ) -> RepetitionContext:
        """
        Check if this question has been asked before by this user.

        Uses Jaccard similarity (word overlap) — lightweight, no embeddings.

        Args:
            user_id: unique identifier for the user.
            current_message: the message to check.

        Returns:
            RepetitionContext with is_repeat, times_asked, likely_reason,
            and suggested_action.
        """
        if user_id not in self._users:
            return RepetitionContext(
                is_repeat=False, times_asked=0,
                previous_questions=[], likely_reason="none",
                similarity_score=0.0, suggested_action="respond_normally",
            )

        data = self._users[user_id]

        # Use Arabic-aware tokenization if available (consensus fix #2, #4)
        if HAS_ARABIC_UTILS:
            current_tokens = tokenize_arabic(current_message)
        else:
            current_tokens = _tokenize(current_message)

        if not current_tokens:
            return RepetitionContext(
                is_repeat=False, times_asked=0,
                previous_questions=[], likely_reason="none",
                similarity_score=0.0, suggested_action="respond_normally",
            )

        matches = []
        best_sim = 0.0

        for prev_q in data.questions_asked:
            # Use combined similarity (Jaccard + n-gram) when available
            if HAS_ARABIC_UTILS:
                sim = combined_similarity(current_message, prev_q)
            else:
                prev_tokens = _tokenize(prev_q)
                sim = _jaccard_similarity(current_tokens, prev_tokens)
            if sim >= self.REPEAT_THRESHOLD:
                matches.append(prev_q)
                best_sim = max(best_sim, sim)

        if not matches:
            return RepetitionContext(
                is_repeat=False, times_asked=0,
                previous_questions=[], likely_reason="none",
                similarity_score=best_sim, suggested_action="respond_normally",
            )

        times = len(matches)
        reason = self._infer_repetition_reason(data, times)
        action = self._suggest_repetition_action(reason)

        return RepetitionContext(
            is_repeat=True,
            times_asked=times,
            previous_questions=matches,
            likely_reason=reason,
            similarity_score=round(best_sim, 4),
            suggested_action=action,
        )

    # ───────────────────────────────────────────────────
    #  suggest_approach() — how to respond given context
    # ───────────────────────────────────────────────────

    def suggest_approach(
        self,
        fingerprint: FingerprintReading,
        repetition_context: Optional[RepetitionContext] = None,
    ) -> str:
        """
        Suggest how to respond given fingerprint + repetition context.

        This is the integration point — it combines pattern knowledge
        (who they are) with situational knowledge (what just happened).

        Args:
            fingerprint: the user's behavioral profile.
            repetition_context: optional repetition info for this message.

        Returns:
            Human-readable suggestion for response strategy.
        """
        parts = []

        # Base approach from fingerprint
        if fingerprint.communication_style == "formal":
            parts.append("use formal, respectful tone")
        elif fingerprint.communication_style == "casual":
            parts.append("match their casual dialect")
        else:
            parts.append("balanced tone")

        if fingerprint.comprehension_level == "needs_step_by_step":
            parts.append("break down into numbered steps")
        elif fingerprint.comprehension_level == "needs_examples":
            parts.append("include concrete examples")
        elif fingerprint.comprehension_level == "quick":
            parts.append("be direct and concise")

        # Repetition-specific adjustments
        if repetition_context and repetition_context.is_repeat:
            reason = repetition_context.likely_reason
            if reason == "confusion":
                parts.append("try a DIFFERENT explanation approach")
            elif reason == "confirmation":
                parts.append("brief confirmation, don't re-explain")
            elif reason == "contradiction":
                parts.append("acknowledge conflicting info, clarify")
            elif reason == "forgot":
                parts.append("gently re-explain without judgment")

        return "; ".join(parts)

    # ───────────────────────────────────────────────────
    #  save() / load() — persistence
    # ───────────────────────────────────────────────────

    def save(self, path: Optional[str] = None) -> None:
        """
        Persist all fingerprints to JSON files.

        Creates one JSON file per user, plus an _index.json.
        Stores PATTERNS, not raw messages (privacy-aware).

        Args:
            path: directory to save to (overrides self.storage_dir).
        """
        save_dir = path or self.storage_dir
        if not save_dir:
            raise ValueError(
                "No storage directory specified. Pass path= or set storage_dir."
            )
        os.makedirs(save_dir, exist_ok=True)

        index = {}
        for user_id, data in self._users.items():
            filename = f"user_{user_id}.json"
            filepath = os.path.join(save_dir, filename)

            # Convert to serializable dict — exclude raw questions for privacy
            save_data = {
                "user_id": data.user_id,
                "formal_count": data.formal_count,
                "casual_count": data.casual_count,
                "gulf_count": data.gulf_count,
                "egyptian_count": data.egyptian_count,
                "msa_count": data.msa_count,
                "other_lang_count": data.other_lang_count,
                "total_interactions": data.total_interactions,
                "first_interaction": data.first_interaction,
                "last_interaction": data.last_interaction,
                "period_counts": data.period_counts,
                "repeat_question_count": data.repeat_question_count,
                "confusion_signals": data.confusion_signals,
                "satisfaction_signals": data.satisfaction_signals,
                "calm_count": data.calm_count,
                "anxious_count": data.anxious_count,
                "enthusiastic_count": data.enthusiastic_count,
                "trust_level": data.trust_level,
                # Store question hashes, not raw text (privacy)
                "question_count": len(data.questions_asked),
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            index[user_id] = {
                "file": filename,
                "last_updated": data.last_interaction,
                "total_interactions": data.total_interactions,
            }

        # Write index
        index_path = os.path.join(save_dir, "_index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def load(self, path: Optional[str] = None) -> int:
        """
        Load fingerprints from JSON files.

        Args:
            path: directory to load from (overrides self.storage_dir).

        Returns:
            Number of users loaded.
        """
        load_dir = path or self.storage_dir
        if not load_dir:
            raise ValueError(
                "No storage directory specified. Pass path= or set storage_dir."
            )
        if not os.path.exists(load_dir):
            return 0

        index_path = os.path.join(load_dir, "_index.json")
        if not os.path.exists(index_path):
            return 0

        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)

        loaded = 0
        for user_id, meta in index.items():
            filepath = os.path.join(load_dir, meta["file"])
            if not os.path.exists(filepath):
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                save_data = json.load(f)

            data = _UserData(user_id=user_id)
            data.formal_count = save_data.get("formal_count", 0)
            data.casual_count = save_data.get("casual_count", 0)
            data.gulf_count = save_data.get("gulf_count", 0)
            data.egyptian_count = save_data.get("egyptian_count", 0)
            data.msa_count = save_data.get("msa_count", 0)
            data.other_lang_count = save_data.get("other_lang_count", 0)
            data.total_interactions = save_data.get("total_interactions", 0)
            data.first_interaction = save_data.get("first_interaction")
            data.last_interaction = save_data.get("last_interaction")
            data.period_counts = save_data.get("period_counts", {})
            data.repeat_question_count = save_data.get("repeat_question_count", 0)
            data.confusion_signals = save_data.get("confusion_signals", 0)
            data.satisfaction_signals = save_data.get("satisfaction_signals", 0)
            data.calm_count = save_data.get("calm_count", 0)
            data.anxious_count = save_data.get("anxious_count", 0)
            data.enthusiastic_count = save_data.get("enthusiastic_count", 0)
            data.trust_level = save_data.get("trust_level", 0.0)

            self._users[user_id] = data
            loaded += 1

        return loaded

    # ───────────────────────────────────────────────────
    #  Internal computation methods
    # ───────────────────────────────────────────────────

    def _default_reading(self, user_id: str) -> FingerprintReading:
        """Return a default fingerprint for unknown users."""
        return FingerprintReading(
            user_id=user_id,
            communication_style="mixed",
            question_pattern="asks_once",
            comprehension_level="quick",
            emotional_baseline="calm",
            active_periods=[],
            interaction_frequency="first_time",
            language_preference="mixed",
            repeat_question_count=0,
            last_interaction=None,
            total_interactions=0,
            trust_level=0.0,
            confusion_signals=0,
            satisfaction_signals=0,
            suggested_profile="default",
            suggested_approach="respond naturally, observe patterns",
            confidence=0.0,
        )

    @staticmethod
    def _compute_comm_style(data: _UserData) -> str:
        """Determine dominant communication style."""
        if data.formal_count > data.casual_count * 1.5:
            return "formal"
        if data.casual_count > data.formal_count * 1.5:
            return "casual"
        return "mixed"

    @staticmethod
    def _compute_language_pref(data: _UserData) -> str:
        """Determine dominant language preference."""
        counts = {
            "gulf_dialect": data.gulf_count,
            "egyptian_dialect": data.egyptian_count,
            "msa": data.msa_count,
        }
        total_arabic = sum(counts.values())
        if total_arabic == 0:
            return "mixed"
        best = max(counts, key=counts.get)
        # Need at least 40% dominance to call it
        if counts[best] / max(total_arabic, 1) >= 0.4:
            return best
        return "mixed"

    @staticmethod
    def _compute_question_pattern(data: _UserData) -> str:
        """Determine how the user asks questions."""
        if data.total_interactions < 3:
            return "asks_once"

        repeat_ratio = data.repeat_question_count / max(len(data.questions_asked), 1)
        confusion_ratio = data.confusion_signals / max(data.total_interactions, 1)

        if repeat_ratio > 0.3 and confusion_ratio > 0.2:
            return "repeats_when_confused"
        if repeat_ratio > 0.3:
            return "repeats_to_confirm"
        return "asks_once"

    @staticmethod
    def _compute_comprehension_level(data: _UserData) -> str:
        """Determine comprehension level from confusion/satisfaction ratio."""
        total = data.confusion_signals + data.satisfaction_signals
        if total < 3:
            return "quick"  # not enough data — assume quick

        confusion_ratio = data.confusion_signals / max(data.total_interactions, 1)
        if confusion_ratio > 0.3:
            return "needs_step_by_step"
        if confusion_ratio > 0.15:
            return "needs_examples"
        return "quick"

    @staticmethod
    def _compute_emotional_baseline(data: _UserData) -> str:
        """Determine emotional baseline from observed signals."""
        total = data.calm_count + data.anxious_count + data.enthusiastic_count
        if total < 3:
            return "calm"  # default

        # Check for variability
        counts = [data.calm_count, data.anxious_count, data.enthusiastic_count]
        max_count = max(counts)
        if max_count / max(total, 1) < 0.5:
            return "variable"  # no single emotion dominates

        if data.anxious_count == max_count:
            return "anxious"
        if data.enthusiastic_count == max_count:
            return "enthusiastic"
        return "calm"

    @staticmethod
    def _compute_active_periods(data: _UserData) -> List[str]:
        """Determine when the user is most active."""
        if not data.period_counts:
            return []
        total = sum(data.period_counts.values())
        if total == 0:
            return []
        # Include periods with > 20% of interactions
        threshold = total * 0.2
        active = [p for p, c in data.period_counts.items() if c >= threshold]
        return sorted(active)

    @staticmethod
    def _compute_interaction_frequency(data: _UserData) -> str:
        """Determine interaction frequency from history."""
        if data.total_interactions <= 1:
            return "first_time"

        if data.first_interaction is None or data.last_interaction is None:
            return "occasional"

        span_seconds = data.last_interaction - data.first_interaction
        if span_seconds <= 0:
            return "first_time"

        span_days = span_seconds / (24 * 3600)
        if span_days < 1:
            # All interactions in one day
            return "daily"

        interactions_per_day = data.total_interactions / max(span_days, 1)
        if interactions_per_day >= 1.0:
            return "daily"
        if interactions_per_day >= 0.14:  # at least once a week
            return "weekly"
        return "occasional"

    @staticmethod
    def _compute_confidence(data: _UserData) -> float:
        """
        Compute confidence in this fingerprint.

        More interactions = higher confidence. Logarithmic growth.
        """
        n = data.total_interactions
        if n == 0:
            return 0.0
        if n == 1:
            return 0.1
        if n <= 5:
            return 0.3
        if n <= 10:
            return 0.5
        if n <= 20:
            return 0.7
        if n <= 50:
            return 0.85
        return 0.95

    @staticmethod
    def _compute_suggested_approach(
        comm_style: str,
        comp_level: str,
        question_pattern: str,
        emo_baseline: str,
    ) -> str:
        """Generate a human-readable approach suggestion."""
        parts = []

        if comm_style == "formal":
            parts.append("respond formally")
        elif comm_style == "casual":
            parts.append("match their casual style")
        else:
            parts.append("balanced approach")

        if comp_level == "needs_step_by_step":
            parts.append("use step-by-step explanations")
        elif comp_level == "needs_examples":
            parts.append("include examples")

        if question_pattern == "repeats_when_confused":
            parts.append("vary explanation methods on repeats")
        elif question_pattern == "repeats_to_confirm":
            parts.append("give brief confirmations")

        if emo_baseline == "anxious":
            parts.append("extra reassurance")
        elif emo_baseline == "enthusiastic":
            parts.append("match their energy")

        return "; ".join(parts) if parts else "respond naturally"

    @staticmethod
    def _infer_repetition_reason(data: _UserData, times: int) -> str:
        """
        Infer WHY a user is repeating a question.

        Logic:
          - High confusion signals → "confusion" (they didn't get it)
          - Low confusion + satisfaction before repeat → "confirmation"
          - Long gap since original → "forgot"
          - Default → "contradiction" (they heard something different)
        """
        confusion_ratio = data.confusion_signals / max(data.total_interactions, 1)

        if confusion_ratio > 0.2:
            return "confusion"
        if data.satisfaction_signals > data.confusion_signals:
            return "confirmation"
        if times >= 3:
            return "confusion"  # asking 3+ times = something's wrong
        return "forgot"

    @staticmethod
    def _suggest_repetition_action(reason: str) -> str:
        """Map repetition reason to suggested action."""
        actions = {
            "confusion": "try_different_approach",
            "confirmation": "brief_confirmation",
            "contradiction": "acknowledge_and_clarify",
            "forgot": "gentle_reexplain",
            "none": "respond_normally",
        }
        return actions.get(reason, "respond_normally")


# ═══════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    fp = UserFingerprint()

    print("=" * 60)
    print("  بصمة المستخدم — AATIF Behavioral Fingerprint")
    print("=" * 60)

    # Simulate a Gulf-dialect casual user
    user = "user_966501234567"
    messages = [
        "وش الأخبار يا صاحبي؟",
        "ابغى أتعلم بايثون وين أبدأ",
        "ما فهمت وضح أكثر",
        "طيب فهمت شكراً",
        "كيف أسوي لوب في بايثون؟",
        "يعني ايش الفرق بين for و while",
        "تمام واضح ممتاز",
        "كيف أسوي لوب في بايثون؟",  # repeat!
    ]

    ts = time.time() - (len(messages) * 300)  # spread over time
    for i, msg in enumerate(messages):
        fp.update(user, msg, timestamp=ts + i * 300)

    reading = fp.read(user)
    print(f"\n  User: {reading.user_id}")
    print(f"  Style: {reading.communication_style}")
    print(f"  Language: {reading.language_preference}")
    print(f"  Pattern: {reading.question_pattern}")
    print(f"  Level: {reading.comprehension_level}")
    print(f"  Emotion: {reading.emotional_baseline}")
    print(f"  Interactions: {reading.total_interactions}")
    print(f"  Trust: {reading.trust_level}")
    print(f"  Confusion: {reading.confusion_signals}")
    print(f"  Satisfaction: {reading.satisfaction_signals}")
    print(f"  Repeats: {reading.repeat_question_count}")
    print(f"  Confidence: {reading.confidence}")
    print(f"  Profile: {reading.suggested_profile}")
    print(f"  Approach: {reading.suggested_approach}")

    # Test repetition detection
    rep = fp.detect_repetition(user, "كيف أسوي لوب في بايثون؟")
    print(f"\n  Repetition check: 'كيف أسوي لوب في بايثون؟'")
    print(f"    is_repeat: {rep.is_repeat}")
    print(f"    times: {rep.times_asked}")
    print(f"    reason: {rep.likely_reason}")
    print(f"    action: {rep.suggested_action}")
    print(f"    similarity: {rep.similarity_score}")

    print(f"\n{'=' * 60}")
    print(f"  عاطف يعرفك من نمطك — مش من سؤالك")
    print(f"{'=' * 60}")
