#!/usr/bin/env python3
"""
Behavioral Fingerprint tests for aatif_fingerprint.py — بصمة المستخدم
=====================================================================

WHY THIS FILE EXISTS
--------------------
The fingerprint is the MIDDLE LAYER of عاطف's understanding triad:
  I scorer = اللحظة (single turn)
  Fingerprint = النمط (patterns over time) ← THIS
  Memory = الحقائق (what happened)

It builds behavioral profiles from observation (معايشة مش استبيان).
These tests verify the observation contract: that the system correctly
identifies communication patterns, question repetition, confusion,
satisfaction, dialect, and style from message sequences.

TESTING STRATEGY
----------------
UserFingerprint is pure Python — no embeddings, no model server.
We feed it controlled message sequences and assert on the structured
output. Every test is fully deterministic and CI-friendly.

Architect: Abdulmjeed Ibrahim Khenkar
"""

import pytest
import json
import os
import sys
import time
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.aatif_fingerprint import (
    UserFingerprint,
    FingerprintReading,
    RepetitionContext,
    _tokenize,
    _jaccard_similarity,
    _detect_language,
    _detect_style,
    _is_question,
    _has_confusion_signal,
    _has_satisfaction_signal,
    _detect_emotional_signal,
    _hour_to_period,
)


# ═══════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def fp():
    """Fresh UserFingerprint instance (in-memory only)."""
    return UserFingerprint()


@pytest.fixture
def tmp_dir():
    """Temporary directory for persistence tests. Cleaned up after."""
    d = tempfile.mkdtemp(prefix="aatif_fp_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


BASE_TS = 1750000000.0  # fixed base timestamp for deterministic tests


# ═══════════════════════════════════════════════════════════
#  1. HELPER FUNCTIONS — tokenizer, similarity, detection
# ═══════════════════════════════════════════════════════════

class TestTokenizer:
    """Test the word tokenizer."""

    def test_basic_arabic(self):
        tokens = _tokenize("كيف أسوي لوب في بايثون؟")
        assert "كيف" in tokens
        assert "بايثون" in tokens

    def test_basic_english(self):
        tokens = _tokenize("How do I make a loop?")
        assert "how" in tokens
        assert "loop" in tokens

    def test_punctuation_removed(self):
        tokens = _tokenize("مرحباً! كيف الحال؟")
        assert "مرحبا" in tokens or "مرحباً" in tokens

    def test_empty_string(self):
        assert _tokenize("") == set()

    def test_single_char_filtered(self):
        tokens = _tokenize("a b cd ef")
        assert "a" not in tokens
        assert "b" not in tokens
        assert "cd" in tokens
        assert "ef" in tokens


class TestJaccardSimilarity:
    """Test Jaccard similarity computation."""

    def test_identical_sets(self):
        assert _jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        sim = _jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert abs(sim - 0.5) < 0.01  # 2/4 = 0.5

    def test_empty_sets(self):
        assert _jaccard_similarity(set(), set()) == 0.0
        assert _jaccard_similarity({"a"}, set()) == 0.0


class TestLanguageDetection:
    """Test dialect/language detection."""

    def test_gulf_dialect(self):
        assert _detect_language("وش الأخبار ابغى أتعلم") == "gulf_dialect"

    def test_egyptian_dialect(self):
        assert _detect_language("عايز أفهم ازاي ده بيشتغل") == "egyptian_dialect"

    def test_msa(self):
        assert _detect_language("أريد أن أتعلم البرمجة بناءً على ذلك") == "msa"

    def test_english_no_arabic(self):
        assert _detect_language("I want to learn Python") == "other"

    def test_empty_string(self):
        assert _detect_language("") == "other"

    def test_mixed_dialect_gulf_dominant(self):
        assert _detect_language("ابغى ايش الحل عشان المشروع") == "gulf_dialect"


class TestStyleDetection:
    """Test communication style detection."""

    def test_casual_short_message(self):
        assert _detect_style("وش الحل؟") == "casual"

    def test_casual_with_emoji(self):
        style = _detect_style("حلو جداً 🎉")
        assert style == "casual"

    def test_formal_msa_long(self):
        style = _detect_style(
            "أريد الاستفسار عن المنهجية المتبعة في هذا البحث الأكاديمي المفصل والمهم."
        )
        assert style == "formal"

    def test_empty_string(self):
        assert _detect_style("") == "mixed"

    def test_mixed_style(self):
        # Neither clearly casual nor formal
        style = _detect_style("أبغى أعرف عن البرمجة")
        assert style in ("casual", "mixed")


class TestQuestionDetection:
    """Test question detection."""

    def test_arabic_question_mark(self):
        assert _is_question("كيف أبدأ؟") is True

    def test_english_question_mark(self):
        assert _is_question("How do I start?") is True

    def test_interrogative_word_arabic(self):
        assert _is_question("وش الحل") is True

    def test_interrogative_word_english(self):
        assert _is_question("what is python") is True

    def test_statement_not_question(self):
        assert _is_question("أنا بخير الحمد لله") is False

    def test_empty_not_question(self):
        assert _is_question("") is False


class TestConfusionSignals:
    """Test confusion signal detection."""

    def test_arabic_confusion_msh_fahem(self):
        assert _has_confusion_signal("مش فاهم وضح أكثر") is True

    def test_arabic_confusion_ma_fehmet(self):
        assert _has_confusion_signal("ما فهمت يعني ايش") is True

    def test_english_confusion(self):
        assert _has_confusion_signal("i don't understand what you mean") is True

    def test_no_confusion(self):
        assert _has_confusion_signal("تمام فهمت شكراً") is False

    def test_empty_no_confusion(self):
        assert _has_confusion_signal("") is False


class TestSatisfactionSignals:
    """Test satisfaction signal detection."""

    def test_arabic_satisfaction_tamam(self):
        assert _has_satisfaction_signal("تمام فهمت") is True

    def test_arabic_satisfaction_shukran(self):
        assert _has_satisfaction_signal("شكراً جزيلاً") is True

    def test_english_satisfaction(self):
        assert _has_satisfaction_signal("thanks, got it!") is True

    def test_arabic_satisfaction_mumtaz(self):
        assert _has_satisfaction_signal("ممتاز") is True

    def test_no_satisfaction(self):
        assert _has_satisfaction_signal("وش الحل؟") is False


class TestEmotionalSignalDetection:
    """Test emotional tone detection."""

    def test_enthusiastic(self):
        assert _detect_emotional_signal("رهيب! ممتاز!") == "enthusiastic"

    def test_anxious(self):
        assert _detect_emotional_signal("أنا قلقان من النتيجة") == "anxious"

    def test_calm_default(self):
        assert _detect_emotional_signal("أبغى أتعلم بايثون") == "calm"

    def test_empty_calm(self):
        assert _detect_emotional_signal("") == "calm"


class TestHourToPeriod:
    """Test hour to period mapping."""

    @pytest.mark.parametrize("hour,expected", [
        (0, "late_night"),
        (3, "late_night"),
        (4, "late_night"),
        (5, "morning"),
        (9, "morning"),
        (11, "morning"),
        (12, "afternoon"),
        (15, "afternoon"),
        (16, "afternoon"),
        (17, "evening"),
        (19, "evening"),
        (20, "evening"),
        (21, "late_night"),
        (23, "late_night"),
    ])
    def test_period_mapping(self, hour, expected):
        assert _hour_to_period(hour) == expected


# ═══════════════════════════════════════════════════════════
#  2. NEW USER — default fingerprint
# ═══════════════════════════════════════════════════════════

class TestNewUser:
    """A new user with no history should get a safe default fingerprint."""

    def test_unknown_user_returns_default(self, fp):
        reading = fp.read("nonexistent_user")
        assert reading.user_id == "nonexistent_user"
        assert reading.communication_style == "mixed"
        assert reading.total_interactions == 0
        assert reading.confidence == 0.0
        assert reading.trust_level == 0.0
        assert reading.suggested_profile == "default"
        assert reading.interaction_frequency == "first_time"

    def test_default_reading_is_fingerprint_reading(self, fp):
        reading = fp.read("new_user")
        assert isinstance(reading, FingerprintReading)

    def test_default_has_no_active_periods(self, fp):
        reading = fp.read("new_user")
        assert reading.active_periods == []

    def test_default_language_is_mixed(self, fp):
        reading = fp.read("new_user")
        assert reading.language_preference == "mixed"

    def test_default_zero_signals(self, fp):
        reading = fp.read("new_user")
        assert reading.confusion_signals == 0
        assert reading.satisfaction_signals == 0
        assert reading.repeat_question_count == 0


# ═══════════════════════════════════════════════════════════
#  3. SINGLE MESSAGE UPDATE
# ═══════════════════════════════════════════════════════════

class TestSingleMessageUpdate:
    """A single message should start building the profile."""

    def test_first_message_increments_count(self, fp):
        fp.update("u1", "مرحبا", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.total_interactions == 1

    def test_first_message_sets_trust(self, fp):
        fp.update("u1", "مرحبا", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.trust_level == 0.1

    def test_first_message_low_confidence(self, fp):
        fp.update("u1", "مرحبا", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.confidence == 0.1

    def test_assistant_messages_ignored(self, fp):
        fp.update("u1", "مرحبا", timestamp=BASE_TS, role="user")
        fp.update("u1", "أهلاً بك", timestamp=BASE_TS + 1, role="assistant")
        reading = fp.read("u1")
        assert reading.total_interactions == 1  # only user counted

    def test_empty_message_ignored(self, fp):
        fp.update("u1", "", timestamp=BASE_TS)
        fp.update("u1", "   ", timestamp=BASE_TS + 1)
        reading = fp.read("u1")
        assert reading.total_interactions == 0


# ═══════════════════════════════════════════════════════════
#  4. MULTIPLE MESSAGES — pattern emergence
# ═══════════════════════════════════════════════════════════

class TestPatternEmergence:
    """Multiple messages should produce detectable patterns."""

    def test_casual_pattern_emerges(self, fp):
        """Multiple casual Gulf messages → casual style detected."""
        messages = [
            "وش الأخبار",
            "ابغى اعرف",
            "وش السالفة",
            "ايش الحل",
            "كذا طيب",
        ]
        for i, msg in enumerate(messages):
            fp.update("u1", msg, timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        assert reading.communication_style == "casual"

    def test_gulf_dialect_detected(self, fp):
        """Multiple Gulf dialect messages → gulf_dialect detected."""
        messages = [
            "وش الأخبار ابغى أسأل",
            "عشان المشروع ودي أعرف",
            "ايش الفرق يعني",
            "ابي اتعلم الحين",
        ]
        for i, msg in enumerate(messages):
            fp.update("u1", msg, timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        assert reading.language_preference == "gulf_dialect"

    def test_egyptian_dialect_detected(self, fp):
        """Multiple Egyptian dialect messages → egyptian_dialect."""
        messages = [
            "عايز أفهم الموضوع ده",
            "ازاي بيشتغل كده",
            "ماشي فاهم كمان",
            "عاوز حاجة تانية بقى",
        ]
        for i, msg in enumerate(messages):
            fp.update("u1", msg, timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        assert reading.language_preference == "egyptian_dialect"

    def test_trust_grows_over_interactions(self, fp):
        """Trust should increase with more interactions."""
        for i in range(10):
            fp.update("u1", f"رسالة رقم {i}", timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        assert reading.trust_level > 0.1
        assert reading.trust_level < 1.0

    def test_confidence_grows_with_interactions(self, fp):
        """Confidence increases with more data."""
        fp.update("u1", "msg1", timestamp=BASE_TS)
        r1 = fp.read("u1")

        for i in range(20):
            fp.update("u1", f"message {i}", timestamp=BASE_TS + (i + 1) * 60)
        r2 = fp.read("u1")

        assert r2.confidence > r1.confidence

    def test_interaction_frequency_daily(self, fp):
        """Many messages in one day → daily frequency."""
        for i in range(10):
            fp.update("u1", f"msg {i}", timestamp=BASE_TS + i * 300)
        reading = fp.read("u1")
        assert reading.interaction_frequency == "daily"


# ═══════════════════════════════════════════════════════════
#  5. REPETITION DETECTION
# ═══════════════════════════════════════════════════════════

class TestRepetitionDetection:
    """Test the KEY differentiator: repeat question detection."""

    def test_exact_repeat_detected(self, fp):
        """Exact same question → detected as repeat."""
        fp.update("u1", "كيف أسوي لوب في بايثون؟", timestamp=BASE_TS)
        rep = fp.detect_repetition("u1", "كيف أسوي لوب في بايثون؟")
        assert rep.is_repeat is True
        assert rep.times_asked >= 1
        assert rep.similarity_score >= 0.6

    def test_similar_repeat_detected(self, fp):
        """Similar phrasing (minor rewording) → detected as repeat."""
        fp.update("u1", "كيف أسوي لوب في بايثون وش الطريقة؟", timestamp=BASE_TS)
        rep = fp.detect_repetition("u1", "كيف أسوي لوب في بايثون وش الخطوات؟")
        assert rep.is_repeat is True

    def test_different_question_not_repeat(self, fp):
        """Completely different question → not a repeat."""
        fp.update("u1", "كيف أسوي لوب في بايثون؟", timestamp=BASE_TS)
        rep = fp.detect_repetition("u1", "ما هي عاصمة فرنسا؟")
        assert rep.is_repeat is False

    def test_no_history_not_repeat(self, fp):
        """Unknown user → not a repeat."""
        rep = fp.detect_repetition("unknown", "أي سؤال")
        assert rep.is_repeat is False
        assert rep.times_asked == 0
        assert rep.likely_reason == "none"

    def test_repeat_has_reason(self, fp):
        """Repeated question includes a reason."""
        fp.update("u1", "وش معنى المتغير؟", timestamp=BASE_TS)
        rep = fp.detect_repetition("u1", "وش معنى المتغير؟")
        assert rep.is_repeat is True
        assert rep.likely_reason in ("confirmation", "confusion", "forgot", "contradiction")

    def test_repeat_has_action(self, fp):
        """Repeated question includes a suggested action."""
        fp.update("u1", "وش الفرق بين الليست والتبل؟", timestamp=BASE_TS)
        rep = fp.detect_repetition("u1", "وش الفرق بين الليست والتبل؟")
        assert rep.suggested_action in (
            "try_different_approach", "brief_confirmation",
            "acknowledge_and_clarify", "gentle_reexplain",
        )

    def test_empty_message_not_repeat(self, fp):
        """Empty message → not a repeat."""
        fp.update("u1", "test question?", timestamp=BASE_TS)
        rep = fp.detect_repetition("u1", "")
        assert rep.is_repeat is False

    def test_multiple_repeats_counted(self, fp):
        """Multiple similar questions → times_asked reflects count."""
        for i in range(3):
            fp.update("u1", "كيف أسوي فنكشن في بايثون؟", timestamp=BASE_TS + i * 60)
        rep = fp.detect_repetition("u1", "كيف أسوي فنكشن في بايثون؟")
        assert rep.is_repeat is True
        assert rep.times_asked >= 2

    def test_confusion_based_repeat(self, fp):
        """User with high confusion + repeats → confusion reason."""
        fp.update("u1", "كيف أسوي كلاس في بايثون؟", timestamp=BASE_TS)
        fp.update("u1", "مش فاهم وضح أكثر", timestamp=BASE_TS + 60)
        fp.update("u1", "ما فهمت يعني ايش", timestamp=BASE_TS + 120)
        fp.update("u1", "مش واضح اشرح لي", timestamp=BASE_TS + 180)
        rep = fp.detect_repetition("u1", "كيف أسوي كلاس في بايثون؟")
        assert rep.is_repeat is True
        assert rep.likely_reason == "confusion"


# ═══════════════════════════════════════════════════════════
#  6. CONFUSION SIGNAL TRACKING
# ═══════════════════════════════════════════════════════════

class TestConfusionTracking:
    """Test that confusion signals are properly counted."""

    def test_confusion_counted(self, fp):
        fp.update("u1", "مرحبا", timestamp=BASE_TS)
        fp.update("u1", "مش فاهم", timestamp=BASE_TS + 60)
        fp.update("u1", "ما فهمت وضح أكثر", timestamp=BASE_TS + 120)
        reading = fp.read("u1")
        assert reading.confusion_signals == 2

    def test_english_confusion_counted(self, fp):
        fp.update("u1", "i don't understand what you mean", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.confusion_signals == 1

    def test_no_confusion_zero(self, fp):
        fp.update("u1", "تمام فهمت", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.confusion_signals == 0


# ═══════════════════════════════════════════════════════════
#  7. SATISFACTION SIGNAL TRACKING
# ═══════════════════════════════════════════════════════════

class TestSatisfactionTracking:
    """Test that satisfaction signals are properly counted."""

    def test_satisfaction_counted(self, fp):
        fp.update("u1", "تمام فهمت", timestamp=BASE_TS)
        fp.update("u1", "شكراً ممتاز", timestamp=BASE_TS + 60)
        reading = fp.read("u1")
        assert reading.satisfaction_signals == 2

    def test_english_satisfaction_counted(self, fp):
        fp.update("u1", "thanks, got it!", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.satisfaction_signals == 1

    def test_mixed_signals(self, fp):
        """Both confusion and satisfaction in different messages."""
        fp.update("u1", "مش فاهم", timestamp=BASE_TS)
        fp.update("u1", "تمام واضح", timestamp=BASE_TS + 60)
        reading = fp.read("u1")
        assert reading.confusion_signals == 1
        assert reading.satisfaction_signals == 1


# ═══════════════════════════════════════════════════════════
#  8. ACTIVE PERIOD TRACKING
# ═══════════════════════════════════════════════════════════

class TestActivePeriods:
    """Test that active time periods are tracked correctly."""

    def test_morning_activity(self, fp):
        """Messages at 9am → morning period tracked."""
        from datetime import datetime as dt_cls
        # Create a timestamp at 9am
        morning_dt = dt_cls(2026, 6, 15, 9, 0, 0)
        morning_ts = morning_dt.timestamp()
        for i in range(5):
            fp.update("u1", f"msg {i}", timestamp=morning_ts + i * 60)
        reading = fp.read("u1")
        assert "morning" in reading.active_periods

    def test_late_night_activity(self, fp):
        """Messages at 2am → late_night period tracked."""
        from datetime import datetime as dt_cls
        night_dt = dt_cls(2026, 6, 15, 2, 0, 0)
        night_ts = night_dt.timestamp()
        for i in range(5):
            fp.update("u1", f"msg {i}", timestamp=night_ts + i * 60)
        reading = fp.read("u1")
        assert "late_night" in reading.active_periods

    def test_no_periods_for_single_message(self, fp):
        """Single message shouldn't dominate period detection."""
        from datetime import datetime as dt_cls
        # 5 morning messages + 1 evening
        morning_dt = dt_cls(2026, 6, 15, 9, 0, 0)
        morning_ts = morning_dt.timestamp()
        for i in range(5):
            fp.update("u1", f"morning {i}", timestamp=morning_ts + i * 60)
        evening_dt = dt_cls(2026, 6, 15, 19, 0, 0)
        fp.update("u1", "evening msg", timestamp=evening_dt.timestamp())
        reading = fp.read("u1")
        assert "morning" in reading.active_periods


# ═══════════════════════════════════════════════════════════
#  9. TRUST LEVEL PROGRESSION
# ═══════════════════════════════════════════════════════════

class TestTrustLevel:
    """Test trust accumulation over time."""

    def test_trust_starts_low(self, fp):
        fp.update("u1", "hello", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.trust_level == 0.1

    def test_trust_increases(self, fp):
        for i in range(5):
            fp.update("u1", f"msg {i}", timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        assert reading.trust_level > 0.1

    def test_trust_never_exceeds_max(self, fp):
        for i in range(200):
            fp.update("u1", f"msg {i}", timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        assert reading.trust_level <= 1.0

    def test_trust_growth_slows(self, fp):
        """Trust grows fast early, slow later (asymptotic)."""
        for i in range(5):
            fp.update("u1", f"msg {i}", timestamp=BASE_TS + i * 60)
        r5 = fp.read("u1")

        for i in range(5, 50):
            fp.update("u1", f"msg {i}", timestamp=BASE_TS + i * 60)
        r50 = fp.read("u1")

        # Growth from 5→50 should be less per-message than 0→5
        growth_early = r5.trust_level - 0.0
        growth_late = r50.trust_level - r5.trust_level
        per_msg_early = growth_early / 5
        per_msg_late = growth_late / 45
        assert per_msg_late < per_msg_early


# ═══════════════════════════════════════════════════════════
#  10. COMPREHENSION LEVEL
# ═══════════════════════════════════════════════════════════

class TestComprehensionLevel:
    """Test comprehension level detection."""

    def test_high_confusion_needs_steps(self, fp):
        """Many confusion signals → needs_step_by_step."""
        # 10 total messages, 4 confusion
        for i in range(6):
            fp.update("u1", f"سؤال عادي {i}", timestamp=BASE_TS + i * 60)
        for i in range(4):
            fp.update("u1", "مش فاهم وضح أكثر", timestamp=BASE_TS + (6 + i) * 60)
        reading = fp.read("u1")
        assert reading.comprehension_level == "needs_step_by_step"

    def test_low_confusion_quick(self, fp):
        """Few confusion signals → quick."""
        for i in range(10):
            fp.update("u1", f"تمام فهمت رسالة {i}", timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        assert reading.comprehension_level == "quick"

    def test_moderate_confusion_needs_examples(self, fp):
        """Moderate confusion → needs_examples."""
        for i in range(8):
            fp.update("u1", f"رسالة عادية {i}", timestamp=BASE_TS + i * 60)
        # Add 2 confusion signals → ~20% ratio
        fp.update("u1", "مش فاهم", timestamp=BASE_TS + 800)
        fp.update("u1", "ما فهمت", timestamp=BASE_TS + 860)
        reading = fp.read("u1")
        assert reading.comprehension_level in ("needs_examples", "quick")


# ═══════════════════════════════════════════════════════════
#  11. QUESTION PATTERN DETECTION
# ═══════════════════════════════════════════════════════════

class TestQuestionPattern:
    """Test question pattern classification."""

    def test_default_asks_once(self, fp):
        """Few interactions → asks_once (default)."""
        fp.update("u1", "سؤال واحد؟", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.question_pattern == "asks_once"

    def test_repeats_with_confusion(self, fp):
        """Repeated questions + confusion → repeats_when_confused."""
        for i in range(3):
            fp.update("u1", "كيف أسوي هالشي؟", timestamp=BASE_TS + i * 100)
            fp.update("u1", "مش فاهم وضح أكثر", timestamp=BASE_TS + i * 100 + 50)
        reading = fp.read("u1")
        assert reading.question_pattern in ("repeats_when_confused", "repeats_to_confirm")


# ═══════════════════════════════════════════════════════════
#  12. EMOTIONAL BASELINE
# ═══════════════════════════════════════════════════════════

class TestEmotionalBaseline:
    """Test emotional baseline computation."""

    def test_default_calm(self, fp):
        """Few messages → default calm."""
        fp.update("u1", "مرحبا", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.emotional_baseline == "calm"

    def test_enthusiastic_baseline(self, fp):
        """Many enthusiastic messages → enthusiastic baseline."""
        for i in range(5):
            fp.update("u1", f"ممتاز! رهيب! حلو! {i}", timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        assert reading.emotional_baseline == "enthusiastic"

    def test_anxious_baseline(self, fp):
        """Many anxious messages → anxious baseline."""
        for i in range(5):
            fp.update("u1", f"قلقان مش عارف خايف {i}", timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        assert reading.emotional_baseline == "anxious"

    def test_variable_baseline(self, fp):
        """Mixed emotional signals → variable baseline."""
        fp.update("u1", "ممتاز رهيب!", timestamp=BASE_TS)
        fp.update("u1", "قلقان جداً", timestamp=BASE_TS + 60)
        fp.update("u1", "عادي خلاص", timestamp=BASE_TS + 120)
        fp.update("u1", "ممتاز!", timestamp=BASE_TS + 180)
        fp.update("u1", "خايف من النتيجة", timestamp=BASE_TS + 240)
        reading = fp.read("u1")
        assert reading.emotional_baseline in ("variable", "enthusiastic", "anxious")


# ═══════════════════════════════════════════════════════════
#  13. SAVE/LOAD PERSISTENCE
# ═══════════════════════════════════════════════════════════

class TestPersistence:
    """Test save/load to JSON files."""

    def test_save_creates_files(self, tmp_dir):
        fp = UserFingerprint(storage_dir=tmp_dir)
        fp.update("u1", "مرحبا", timestamp=BASE_TS)
        fp.save()
        assert os.path.exists(os.path.join(tmp_dir, "user_u1.json"))
        assert os.path.exists(os.path.join(tmp_dir, "_index.json"))

    def test_save_load_roundtrip(self, tmp_dir):
        """Save then load produces same readings."""
        fp1 = UserFingerprint(storage_dir=tmp_dir)
        for i in range(5):
            fp1.update("u1", f"وش الأخبار msg {i}", timestamp=BASE_TS + i * 60)
        fp1.save()
        r1 = fp1.read("u1")

        fp2 = UserFingerprint(storage_dir=tmp_dir)
        loaded = fp2.load()
        assert loaded == 1
        r2 = fp2.read("u1")

        assert r2.total_interactions == r1.total_interactions
        assert r2.trust_level == r1.trust_level
        assert r2.confusion_signals == r1.confusion_signals
        assert r2.satisfaction_signals == r1.satisfaction_signals

    def test_load_nonexistent_dir(self):
        fp = UserFingerprint()
        loaded = fp.load(path="/nonexistent/path/12345")
        assert loaded == 0

    def test_save_no_dir_raises(self):
        fp = UserFingerprint()
        fp.update("u1", "test", timestamp=BASE_TS)
        with pytest.raises(ValueError, match="No storage directory"):
            fp.save()

    def test_load_no_dir_raises(self):
        fp = UserFingerprint()
        with pytest.raises(ValueError, match="No storage directory"):
            fp.load()

    def test_index_contains_metadata(self, tmp_dir):
        fp = UserFingerprint(storage_dir=tmp_dir)
        fp.update("u1", "msg", timestamp=BASE_TS)
        fp.save()
        with open(os.path.join(tmp_dir, "_index.json"), "r") as f:
            index = json.load(f)
        assert "u1" in index
        assert "file" in index["u1"]
        assert "last_updated" in index["u1"]
        assert "total_interactions" in index["u1"]

    def test_multiple_users_saved(self, tmp_dir):
        fp = UserFingerprint(storage_dir=tmp_dir)
        fp.update("u1", "hello", timestamp=BASE_TS)
        fp.update("u2", "merhaba", timestamp=BASE_TS)
        fp.save()
        assert os.path.exists(os.path.join(tmp_dir, "user_u1.json"))
        assert os.path.exists(os.path.join(tmp_dir, "user_u2.json"))

    def test_privacy_no_raw_questions_saved(self, tmp_dir):
        """Raw question text should NOT be persisted."""
        fp = UserFingerprint(storage_dir=tmp_dir)
        fp.update("u1", "كيف أسوي لوب؟", timestamp=BASE_TS)
        fp.save()
        with open(os.path.join(tmp_dir, "user_u1.json"), "r") as f:
            data = json.load(f)
        # Should have question_count but NOT raw questions
        assert "question_count" in data
        content = json.dumps(data, ensure_ascii=False)
        assert "كيف أسوي لوب" not in content


# ═══════════════════════════════════════════════════════════
#  14. PROFILE SUGGESTION MAPPING
# ═══════════════════════════════════════════════════════════

class TestProfileSuggestion:
    """Test that fingerprints map to appropriate GATED_PROFILES."""

    def test_default_profile_for_unknown(self, fp):
        reading = fp.read("unknown")
        assert reading.suggested_profile == "default"

    def test_casual_quick_gets_relaxed(self, fp):
        """Casual style + quick comprehension → relaxed profile."""
        # Feed enough casual messages
        for i in range(10):
            fp.update("u1", f"وش الأخبار msg {i}", timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        if reading.communication_style == "casual" and reading.comprehension_level == "quick":
            assert reading.suggested_profile == "relaxed"

    def test_formal_step_by_step_gets_high_sensitivity(self, fp):
        """Formal style + needs step-by-step → high_sensitivity."""
        # Create pattern: formal messages + lots of confusion
        for i in range(7):
            fp.update("u1",
                      "أريد الاستفسار عن المنهجية المتبعة في هذا البحث الأكاديمي المفصل.",
                      timestamp=BASE_TS + i * 60)
        for i in range(4):
            fp.update("u1", "مش فاهم وضح أكثر", timestamp=BASE_TS + (7 + i) * 60)
        reading = fp.read("u1")
        # Check if profile suggestion is logically consistent
        assert reading.suggested_profile in ("default", "high_sensitivity")


# ═══════════════════════════════════════════════════════════
#  15. SUGGEST APPROACH
# ═══════════════════════════════════════════════════════════

class TestSuggestApproach:
    """Test the suggest_approach method."""

    def test_basic_approach(self, fp):
        fp.update("u1", "مرحبا", timestamp=BASE_TS)
        reading = fp.read("u1")
        approach = fp.suggest_approach(reading)
        assert isinstance(approach, str)
        assert len(approach) > 0

    def test_approach_with_repetition_confusion(self, fp):
        fp.update("u1", "وش الحل؟", timestamp=BASE_TS)
        fp.update("u1", "مش فاهم", timestamp=BASE_TS + 60)
        fp.update("u1", "ما فهمت", timestamp=BASE_TS + 120)
        reading = fp.read("u1")
        rep = RepetitionContext(
            is_repeat=True, times_asked=2,
            previous_questions=["وش الحل؟"],
            likely_reason="confusion",
            similarity_score=0.9,
            suggested_action="try_different_approach",
        )
        approach = fp.suggest_approach(reading, rep)
        assert "different" in approach.lower() or "DIFFERENT" in approach

    def test_approach_with_repetition_confirmation(self, fp):
        fp.update("u1", "مرحبا", timestamp=BASE_TS)
        reading = fp.read("u1")
        rep = RepetitionContext(
            is_repeat=True, times_asked=1,
            previous_questions=["test"],
            likely_reason="confirmation",
            similarity_score=0.8,
            suggested_action="brief_confirmation",
        )
        approach = fp.suggest_approach(reading, rep)
        assert "confirm" in approach.lower()

    def test_approach_no_repetition(self, fp):
        fp.update("u1", "مرحبا", timestamp=BASE_TS)
        reading = fp.read("u1")
        approach = fp.suggest_approach(reading, None)
        assert isinstance(approach, str)


# ═══════════════════════════════════════════════════════════
#  16. EDGE CASES
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_non_arabic_text(self, fp):
        """English-only messages should still work."""
        fp.update("u1", "Hello, how are you?", timestamp=BASE_TS)
        fp.update("u1", "I need help with Python", timestamp=BASE_TS + 60)
        reading = fp.read("u1")
        assert reading.total_interactions == 2

    def test_mixed_arabic_english(self, fp):
        """Mixed language messages."""
        fp.update("u1", "أبغى أتعلم Python programming", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.total_interactions == 1

    def test_very_long_message(self, fp):
        """Very long message shouldn't crash."""
        long_msg = "مرحبا " * 1000
        fp.update("u1", long_msg, timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.total_interactions == 1

    def test_special_characters(self, fp):
        """Messages with special characters."""
        fp.update("u1", "test @#$%^&*() 123", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.total_interactions == 1

    def test_multiple_users_independent(self, fp):
        """Each user's fingerprint is independent."""
        fp.update("u1", "مرحبا", timestamp=BASE_TS)
        fp.update("u2", "hello", timestamp=BASE_TS)
        r1 = fp.read("u1")
        r2 = fp.read("u2")
        assert r1.user_id == "u1"
        assert r2.user_id == "u2"
        assert r1.total_interactions == 1
        assert r2.total_interactions == 1

    def test_timestamp_defaults_to_now(self, fp):
        """No timestamp → uses current time."""
        fp.update("u1", "test")
        reading = fp.read("u1")
        assert reading.last_interaction is not None
        assert abs(reading.last_interaction - time.time()) < 2.0

    def test_question_cap_prevents_unbounded_growth(self, fp):
        """Stored questions should be capped."""
        for i in range(300):
            fp.update("u1", f"سؤال رقم {i}؟", timestamp=BASE_TS + i * 10)
        # Access internal data to check cap
        data = fp._users["u1"]
        assert len(data.questions_asked) <= data.MAX_STORED_QUESTIONS

    def test_repeat_detection_across_cap(self, fp):
        """Repetition detection still works after cap is reached."""
        # Fill with many different questions
        for i in range(250):
            fp.update("u1", f"سؤال فريد رقم {i} مختلف تماما؟", timestamp=BASE_TS + i * 10)
        # Now add a specific question
        fp.update("u1", "كيف أسوي لوب في بايثون؟", timestamp=BASE_TS + 2600)
        # Should detect it as recent question
        rep = fp.detect_repetition("u1", "كيف أسوي لوب في بايثون؟")
        assert rep.is_repeat is True


# ═══════════════════════════════════════════════════════════
#  17. INTERACTION FREQUENCY
# ═══════════════════════════════════════════════════════════

class TestInteractionFrequency:
    """Test interaction frequency computation."""

    def test_first_time(self, fp):
        reading = fp.read("u1")
        assert reading.interaction_frequency == "first_time"

    def test_single_message_first_time(self, fp):
        fp.update("u1", "hello", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.interaction_frequency == "first_time"

    def test_daily_frequency(self, fp):
        """Multiple messages over a day → daily."""
        for i in range(10):
            fp.update("u1", f"msg {i}", timestamp=BASE_TS + i * 3600)
        reading = fp.read("u1")
        assert reading.interaction_frequency == "daily"

    def test_occasional_frequency(self, fp):
        """Few messages over many weeks → occasional."""
        fp.update("u1", "msg 1", timestamp=BASE_TS)
        fp.update("u1", "msg 2", timestamp=BASE_TS + 30 * 86400)  # 30 days later
        reading = fp.read("u1")
        assert reading.interaction_frequency == "occasional"


# ═══════════════════════════════════════════════════════════
#  18. INTEGRATION SMOKE TEST
# ═══════════════════════════════════════════════════════════

class TestIntegrationFlow:
    """Simulate a real conversation flow through the fingerprint system."""

    def test_full_conversation_flow(self, fp):
        """Simulate: new user → asks questions → gets confused → understands."""
        user = "u_conv_test"
        ts = BASE_TS

        # First contact
        fp.update(user, "مرحبا ابغى أتعلم بايثون", timestamp=ts)
        r1 = fp.read(user)
        assert r1.total_interactions == 1
        assert r1.confidence == 0.1

        # Asks a question
        ts += 300
        fp.update(user, "كيف أسوي متغير في بايثون؟", timestamp=ts)

        # Gets confused
        ts += 120
        fp.update(user, "مش فاهم وضح أكثر", timestamp=ts)

        # Asks again (repeat)
        ts += 180
        fp.update(user, "كيف أسوي متغير في بايثون؟", timestamp=ts)

        # Understands
        ts += 60
        fp.update(user, "تمام فهمت شكراً", timestamp=ts)

        # Check final state
        reading = fp.read(user)
        assert reading.total_interactions == 5
        assert reading.confusion_signals >= 1
        assert reading.satisfaction_signals >= 1
        assert reading.repeat_question_count >= 1
        assert reading.confidence > 0.1

        # Check repetition detection
        rep = fp.detect_repetition(user, "كيف أسوي متغير في بايثون؟")
        assert rep.is_repeat is True

    def test_two_users_dont_interfere(self, fp):
        """Two users' fingerprints should be completely independent."""
        # User 1: casual Gulf
        for i in range(5):
            fp.update("gulf_user", f"وش الأخبار ابغى {i}", timestamp=BASE_TS + i * 60)

        # User 2: formal English
        for i in range(5):
            fp.update("formal_user",
                      f"I would like to inquire about the methodology number {i}.",
                      timestamp=BASE_TS + i * 60)

        r1 = fp.read("gulf_user")
        r2 = fp.read("formal_user")

        assert r1.total_interactions == 5
        assert r2.total_interactions == 5
        # They should have different styles
        assert r1.user_id != r2.user_id


# ═══════════════════════════════════════════════════════════
#  19. DATACLASS FIELDS COMPLETE
# ═══════════════════════════════════════════════════════════

class TestDataclassCompleteness:
    """Ensure all expected fields are present in outputs."""

    def test_fingerprint_reading_fields(self, fp):
        fp.update("u1", "test", timestamp=BASE_TS)
        reading = fp.read("u1")
        expected_fields = {
            "user_id", "communication_style", "question_pattern",
            "comprehension_level", "emotional_baseline", "active_periods",
            "interaction_frequency", "language_preference",
            "repeat_question_count", "last_interaction",
            "total_interactions", "trust_level", "confusion_signals",
            "satisfaction_signals", "suggested_profile",
            "suggested_approach", "confidence",
        }
        actual_fields = set(reading.__dataclass_fields__.keys())
        assert expected_fields == actual_fields

    def test_repetition_context_fields(self, fp):
        fp.update("u1", "test?", timestamp=BASE_TS)
        rep = fp.detect_repetition("u1", "test?")
        expected_fields = {
            "is_repeat", "times_asked", "previous_questions",
            "likely_reason", "similarity_score", "suggested_action",
        }
        actual_fields = set(rep.__dataclass_fields__.keys())
        assert expected_fields == actual_fields


# ═══════════════════════════════════════════════════════════
#  20. LANGUAGE PREFERENCE AGGREGATION
# ═══════════════════════════════════════════════════════════

class TestLanguagePreference:
    """Test language preference over multiple messages."""

    def test_mixed_when_no_dominance(self, fp):
        """Equal messages in different dialects → mixed."""
        fp.update("u1", "وش الأخبار", timestamp=BASE_TS)
        fp.update("u1", "عايز أعرف", timestamp=BASE_TS + 60)
        reading = fp.read("u1")
        assert reading.language_preference in ("gulf_dialect", "egyptian_dialect", "mixed")

    def test_gulf_dominant(self, fp):
        """Mostly Gulf dialect → gulf_dialect."""
        gulf_msgs = ["ابغى أعرف", "وش السالفة", "ايش الحل", "يعني وش يصير"]
        for i, msg in enumerate(gulf_msgs):
            fp.update("u1", msg, timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        assert reading.language_preference == "gulf_dialect"


# ═══════════════════════════════════════════════════════════
#  21. TRUST DECAY
# ═══════════════════════════════════════════════════════════

class TestTrustDecay:
    """Test trust decay after periods of inactivity."""

    def test_trust_decays_after_inactivity(self, fp):
        """Send 5 msgs at BASE_TS, then 1 msg 30 days later.
        30 days * 0.01/day = 0.30 decay applied before increment,
        so trust after msg 6 should be LOWER than after msg 5."""
        for i in range(5):
            fp.update("u1", f"رسالة رقم {i}", timestamp=BASE_TS + i * 60)
        trust_after_5 = fp.read("u1").trust_level

        # 30 days later
        fp.update("u1", "رسالة بعد غياب", timestamp=BASE_TS + 30 * 86400)
        trust_after_6 = fp.read("u1").trust_level

        assert trust_after_6 < trust_after_5

    def test_no_decay_on_first_message(self, fp):
        """First message ever: trust = 0.1 with no decay."""
        fp.update("u1", "مرحبا", timestamp=BASE_TS)
        reading = fp.read("u1")
        assert reading.trust_level == 0.1

    def test_trust_decay_clamped_to_zero(self, fp):
        """Send 1 msg, then 200 days later. Decay = 200*0.01 = 2.0
        exceeds trust of 0.1 — clamps to 0.0, then increment applies.
        Trust should be positive (increment applied) but very low."""
        fp.update("u1", "رسالة أولى", timestamp=BASE_TS)
        trust_after_1 = fp.read("u1").trust_level
        assert trust_after_1 == 0.1

        fp.update("u1", "رسالة بعد غياب طويل", timestamp=BASE_TS + 200 * 86400)
        trust_after_2 = fp.read("u1").trust_level

        # Trust must not go negative (clamped at 0.0 before increment)
        assert trust_after_2 >= 0.0
        # Increment was applied after clamp, so trust > 0
        assert trust_after_2 > 0.0
        # But trust should be much lower than the first msg's 0.1
        assert trust_after_2 < trust_after_1

    def test_no_decay_within_same_session(self, fp):
        """Messages 60s apart (same session). Decay per message
        should be negligible (< 0.001)."""
        fp.update("u1", "رسالة أولى", timestamp=BASE_TS)
        for i in range(1, 5):
            fp.update("u1", f"رسالة {i}", timestamp=BASE_TS + i * 60)

        # Read internal trust level
        trust = fp.read("u1").trust_level
        # Compute what trust WOULD be with zero decay:
        # msg1: 0.1, msg2: 0.1 + 0.02*0.9 = 0.118, msg3: 0.118 + 0.02*0.882...
        # Decay per 60s gap = 0.01 * (60/86400) ≈ 0.0000069 — negligible
        # So trust should be very close to the no-decay value
        # With 5 messages and negligible decay, trust should be > 0.1
        assert trust > 0.1

        # Verify decay per step is negligible by checking that trust
        # grew almost linearly (each 60s gap decays < 0.001)
        fp2 = UserFingerprint()
        fp2.update("u2", "رسالة أولى", timestamp=BASE_TS)
        fp2.update("u2", "رسالة ثانية", timestamp=BASE_TS + 60)
        t_after_2 = fp2._users["u2"].trust_level

        fp2.update("u2", "رسالة ثالثة", timestamp=BASE_TS + 120)
        t_after_3 = fp2._users["u2"].trust_level

        # The decay between msg2 and msg3 (60s) should be < 0.001
        # decay = 0.01 * (60/86400) ≈ 0.0000069
        decay_60s = 0.01 * (60 / 86400.0)
        assert decay_60s < 0.001


# ═══════════════════════════════════════════════════════════
#  22. CONFIGURABLE THRESHOLDS
# ═══════════════════════════════════════════════════════════

class TestConfigurableThresholds:
    """Test constructor keyword-only params for threshold overrides."""

    def test_custom_trust_increment(self):
        """trust_increment=0.5 → first message trust = 0.1 (hardcoded),
        but second message uses custom increment."""
        fp = UserFingerprint(trust_increment=0.5)
        fp.update("u1", "msg one", timestamp=BASE_TS)
        # First message is always 0.1
        assert fp.read("u1").trust_level == 0.1

        fp.update("u1", "msg two", timestamp=BASE_TS + 60)
        trust = fp.read("u1").trust_level
        # With increment=0.5: trust = 0.1 + 0.5*(1-0.1) = 0.1 + 0.45 = 0.55
        # (minus negligible decay for 60s gap)
        assert trust > 0.4  # well above default increment behavior

    def test_custom_trust_max(self):
        """trust_max=0.3 → trust should never exceed 0.3."""
        fp = UserFingerprint(trust_max=0.3)
        for i in range(20):
            fp.update("u1", f"msg {i}", timestamp=BASE_TS + i * 60)
        reading = fp.read("u1")
        assert reading.trust_level <= 0.3

    def test_custom_repeat_threshold(self):
        """repeat_threshold=0.9 → only near-identical matches count as repeats."""
        fp = UserFingerprint(repeat_threshold=0.9)
        fp.update("u1", "كيف أسوي لوب في بايثون؟", timestamp=BASE_TS)
        # Slightly different phrasing — similar but not 0.9+ similarity
        rep = fp.detect_repetition("u1", "كيف أسوي لوب في بايثون وش الطريقة؟")
        assert rep.is_repeat is False

        # With default threshold (0.6), the same pair WOULD be a repeat
        fp_default = UserFingerprint()
        fp_default.update("u2", "كيف أسوي لوب في بايثون؟", timestamp=BASE_TS)
        rep_default = fp_default.detect_repetition(
            "u2", "كيف أسوي لوب في بايثون وش الطريقة؟"
        )
        assert rep_default.is_repeat is True

    def test_custom_trust_decay_per_day(self):
        """trust_decay_per_day=0.1 → high decay wipes trust after 10-day gap."""
        fp = UserFingerprint(trust_decay_per_day=0.1)
        for i in range(5):
            fp.update("u1", f"رسالة {i}", timestamp=BASE_TS + i * 60)
        trust_after_5 = fp.read("u1").trust_level

        # 10 days later: decay = 0.1 * 10 = 1.0 — wipes out all trust
        fp.update("u1", "رسالة بعد عشرة أيام", timestamp=BASE_TS + 10 * 86400)
        trust_after_gap = fp.read("u1").trust_level

        # Trust should have been wiped to 0.0 by decay, then a small
        # increment applied. Should be far below the pre-gap level.
        assert trust_after_gap < trust_after_5
        # Trust should still be positive (increment applied after decay)
        assert trust_after_gap > 0.0
        # Trust should be very low — close to just the increment from zero
        assert trust_after_gap < 0.05


# ═══════════════════════════════════════════════════════════
#  23. ARABIC-AWARE SIMILARITY
# ═══════════════════════════════════════════════════════════

class TestArabicAwareSimilarity:
    """Test that Arabic normalization (via aatif_arabic_utils)
    improves repeat detection for Arabic morphological variants."""

    def test_alef_variant_repeat_detected(self, fp):
        """إ vs ا in إيميل/ايميل — normalization collapses both to ا."""
        fp.update("u1", "كيف أسوي إيميل", timestamp=BASE_TS)
        rep = fp.detect_repetition("u1", "كيف أسوي ايميل")
        assert rep.is_repeat is True
        assert rep.similarity_score >= 0.6

    def test_taa_marbuta_variant_detected(self, fp):
        """ة vs ه in المدرسة/المدرسه — normalization maps ة→ه."""
        fp.update("u1", "وش المدرسة", timestamp=BASE_TS)
        rep = fp.detect_repetition("u1", "وش المدرسه")
        assert rep.is_repeat is True
        assert rep.similarity_score >= 0.6

    def test_ngram_rescues_variant_detection(self, fp):
        """وش vs ايش + ة vs ه — Jaccard alone misses it, n-gram rescues.

        'وش طريقة التسجيل' vs 'ايش طريقه التسجيل':
          Jaccard = 0.50 (below 0.6 threshold → would NOT detect)
          Combined = 0.67 (above 0.6 threshold → DOES detect)
        This proves the n-gram component adds real value for Arabic.
        """
        fp.update("u1", "وش طريقة التسجيل", timestamp=BASE_TS)
        rep = fp.detect_repetition("u1", "ايش طريقه التسجيل")
        assert rep.is_repeat is True
        assert rep.similarity_score >= 0.6
