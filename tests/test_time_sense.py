#!/usr/bin/env python3
"""
Time Sense (T) tests for aatif_time_sense.py — حاسة الزمن
==========================================================

WHY THIS FILE EXISTS
────────────────────
T (time) is عاطف's fourth perception channel. Unlike H, I, and E which
read the MESSAGE, T reads the MOMENT — when a person speaks matters as
much as what they say. Someone writing "تعبت" at 3am is not the same
as someone writing it at 10am.

This test suite ensures the temporal perception contract holds:
  • Arabic time periods map correctly across all 24 hours
  • Late night detection (0-5am) is accurate
  • Weekend detection covers both Islamic (Fri-Sat) and Western (Sat-Sun)
  • Interaction gaps are assessed correctly (rapid / normal / long / first)
  • Fatigue risk fires only when evidence warrants it
  • Greetings adapt to context (time, gap, late night)
  • Timezones shift the reading correctly
  • Edge cases: midnight, noon, period transitions

THE TESTING STRATEGY
────────────────────
TimeSense is pure stdlib — no embedding backend, no model server.
We inject specific unix timestamps (computed from known datetimes)
and assert on the structured output. This makes every test fully
deterministic and CI-friendly.

Architect: Abdulmjeed Ibrahim Khenkar
"""

import pytest
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from engine.aatif_time_sense import TimeSense, TimeReading


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _ts(year, month, day, hour, minute=0, tz="Asia/Riyadh"):
    """Create a unix timestamp from components in a given timezone."""
    dt = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz))
    return dt.timestamp()


@pytest.fixture
def sense():
    """Fresh TimeSense instance."""
    return TimeSense()


# ═══════════════════════════════════════════════════════════
#  1. TIME PERIOD MAPPING — Arabic cultural divisions
# ═══════════════════════════════════════════════════════════

class TestTimePeriods:
    """Arabic time periods must map correctly for all 24 hours."""

    @pytest.mark.parametrize("hour,expected_period", [
        # فجر: 4-6
        (4,  "فجر"),
        (5,  "فجر"),
        # صباح: 6-12
        (6,  "صباح"),
        (9,  "صباح"),
        (11, "صباح"),
        # ظهر: 12-14
        (12, "ظهر"),
        (13, "ظهر"),
        # عصر: 14-17
        (14, "عصر"),
        (16, "عصر"),
        # مساء: 17-21
        (17, "مساء"),
        (20, "مساء"),
        # ليل: 21-4 (wraps midnight)
        (21, "ليل"),
        (23, "ليل"),
        (0,  "ليل"),
        (1,  "ليل"),
        (3,  "ليل"),
    ])
    def test_period_mapping(self, sense, hour, expected_period):
        """Each hour maps to the correct Arabic period."""
        ts = _ts(2026, 6, 15, hour, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.period == expected_period, (
            f"Hour {hour} → expected '{expected_period}', got '{reading.period}'"
        )

    def test_all_24_hours_have_a_period(self, sense):
        """Every hour from 0-23 produces a valid period."""
        valid_periods = {"فجر", "صباح", "ظهر", "عصر", "مساء", "ليل"}
        for hour in range(24):
            ts = _ts(2026, 6, 15, hour, tz="Asia/Riyadh")
            reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
            assert reading.period in valid_periods, (
                f"Hour {hour} produced invalid period: '{reading.period}'"
            )

    def test_period_transitions(self, sense):
        """Boundary hours transition correctly between periods."""
        transitions = [
            (3,  4,  "ليل",  "فجر"),   # night → pre-dawn
            (5,  6,  "فجر",  "صباح"),  # pre-dawn → morning
            (11, 12, "صباح", "ظهر"),   # morning → noon
            (13, 14, "ظهر",  "عصر"),   # noon → afternoon
            (16, 17, "عصر",  "مساء"),  # afternoon → evening
            (20, 21, "مساء", "ليل"),   # evening → night
        ]
        for h_before, h_after, p_before, p_after in transitions:
            ts1 = _ts(2026, 6, 15, h_before, tz="Asia/Riyadh")
            ts2 = _ts(2026, 6, 15, h_after, tz="Asia/Riyadh")
            r1 = sense.read(timestamp=ts1, user_timezone="Asia/Riyadh")
            r2 = sense.read(timestamp=ts2, user_timezone="Asia/Riyadh")
            assert r1.period == p_before, f"Hour {h_before}: expected {p_before}"
            assert r2.period == p_after, f"Hour {h_after}: expected {p_after}"


# ═══════════════════════════════════════════════════════════
#  2. LATE NIGHT DETECTION
# ═══════════════════════════════════════════════════════════

class TestLateNight:
    """Late night (0-5am) should be detected — user might be tired/stressed."""

    @pytest.mark.parametrize("hour,expected", [
        (0,  True),   # midnight
        (1,  True),
        (2,  True),
        (3,  True),   # deep night
        (4,  True),
        (5,  False),  # 5am is no longer late night
        (6,  False),
        (12, False),
        (18, False),
        (23, False),  # 11pm is night but not "late night"
    ])
    def test_late_night_flag(self, sense, hour, expected):
        ts = _ts(2026, 6, 15, hour, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.is_late_night == expected, (
            f"Hour {hour}: expected is_late_night={expected}"
        )


# ═══════════════════════════════════════════════════════════
#  3. WORK HOURS DETECTION
# ═══════════════════════════════════════════════════════════

class TestWorkHours:
    """Work hours (9am-5pm) detection."""

    @pytest.mark.parametrize("hour,expected", [
        (8,  False),
        (9,  True),   # start of work
        (12, True),
        (16, True),
        (17, False),  # end of work
        (18, False),
        (3,  False),
    ])
    def test_work_hours(self, sense, hour, expected):
        ts = _ts(2026, 6, 15, hour, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.is_work_hours == expected


# ═══════════════════════════════════════════════════════════
#  4. WEEKEND DETECTION (dual calendar)
# ═══════════════════════════════════════════════════════════

class TestWeekend:
    """Weekend detection must cover both Islamic (Fri-Sat) and Western (Sat-Sun)."""

    def test_friday_is_islamic_weekend(self, sense):
        """Friday is weekend in Islamic calendar."""
        # 2026-06-19 is a Friday
        ts = _ts(2026, 6, 19, 10, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.day_of_week == "Friday"
        assert reading.is_islamic_weekend is True
        assert reading.is_weekend is True

    def test_saturday_is_both_weekends(self, sense):
        """Saturday is weekend in BOTH calendars."""
        # 2026-06-20 is a Saturday
        ts = _ts(2026, 6, 20, 10, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.day_of_week == "Saturday"
        assert reading.is_islamic_weekend is True
        assert reading.is_western_weekend is True
        assert reading.is_weekend is True

    def test_sunday_is_western_weekend_only(self, sense):
        """Sunday is weekend in Western calendar but workday in Islamic."""
        # 2026-06-21 is a Sunday
        ts = _ts(2026, 6, 21, 10, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.day_of_week == "Sunday"
        assert reading.is_western_weekend is True
        assert reading.is_islamic_weekend is False
        assert reading.is_weekend is True

    def test_wednesday_is_no_weekend(self, sense):
        """Wednesday is a workday in both calendars."""
        # 2026-06-17 is a Wednesday
        ts = _ts(2026, 6, 17, 10, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.day_of_week == "Wednesday"
        assert reading.is_weekend is False
        assert reading.is_islamic_weekend is False
        assert reading.is_western_weekend is False

    def test_arabic_day_names(self, sense):
        """Arabic day names are set correctly."""
        # 2026-06-19 is Friday
        ts = _ts(2026, 6, 19, 10, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.day_of_week_ar == "الجمعة"

        # 2026-06-21 is Sunday
        ts = _ts(2026, 6, 21, 10, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.day_of_week_ar == "الأحد"


# ═══════════════════════════════════════════════════════════
#  5. INTERACTION GAP ASSESSMENT
# ═══════════════════════════════════════════════════════════

class TestInteractionGap:
    """Assess how long since last interaction — urgency vs. returning vs. normal."""

    def test_first_interaction(self, sense):
        """No previous timestamp → 'أول_تواصل'."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.interaction_gap_assessment == "أول_تواصل"
        assert reading.time_since_last_interaction is None

    def test_rapid_fire(self, sense):
        """Message within 2 minutes → 'سريع' (might be urgent)."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        prev = ts - 60  # 1 minute ago
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev,
        )
        assert reading.interaction_gap_assessment == "سريع"
        assert reading.time_since_last_interaction == timedelta(seconds=60)

    def test_normal_gap(self, sense):
        """Message after 30 minutes → 'عادي'."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        prev = ts - (30 * 60)  # 30 min ago
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev,
        )
        assert reading.interaction_gap_assessment == "عادي"

    def test_normal_gap_hours(self, sense):
        """Message after 3 hours → still 'عادي'."""
        ts = _ts(2026, 6, 15, 14, tz="Asia/Riyadh")
        prev = ts - (3 * 3600)
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev,
        )
        assert reading.interaction_gap_assessment == "عادي"

    def test_long_gap_days(self, sense):
        """Message after 3 days → 'طويل' (person is returning)."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        prev = ts - (3 * 24 * 3600)  # 3 days ago
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev,
        )
        assert reading.interaction_gap_assessment == "طويل"

    def test_long_gap_boundary(self, sense):
        """Exactly 1 day is still 'عادي'; just over 1 day is 'طويل'."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")

        # Exactly 1 day: timedelta(days=1) is the boundary
        prev_exact = ts - (24 * 3600)
        reading_exact = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev_exact,
        )
        assert reading_exact.interaction_gap_assessment == "عادي"

        # Just over 1 day
        prev_over = ts - (24 * 3600 + 1)
        reading_over = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev_over,
        )
        assert reading_over.interaction_gap_assessment == "طويل"

    def test_rapid_boundary(self, sense):
        """Exactly 2 minutes is still 'سريع'; just over is 'عادي'."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")

        # Exactly 2 minutes
        prev_exact = ts - 120
        reading_exact = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev_exact,
        )
        assert reading_exact.interaction_gap_assessment == "سريع"

        # Just over 2 minutes
        prev_over = ts - 121
        reading_over = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev_over,
        )
        assert reading_over.interaction_gap_assessment == "عادي"


# ═══════════════════════════════════════════════════════════
#  6. FATIGUE RISK
# ═══════════════════════════════════════════════════════════

class TestFatigueRisk:
    """Fatigue risk: late night conditions warrant compassionate awareness."""

    def test_late_night_alone_flags_fatigue(self, sense):
        """Being up at 3am at all is a fatigue signal."""
        ts = _ts(2026, 6, 15, 3, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.fatigue_risk is True

    def test_late_night_long_session(self, sense):
        """3am + session running > 2 hours → definite fatigue."""
        ts = _ts(2026, 6, 15, 3, tz="Asia/Riyadh")
        session_start = ts - (3 * 3600)  # started 3 hours ago (midnight)
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            session_start_timestamp=session_start,
        )
        assert reading.fatigue_risk is True

    def test_late_night_rapid_fire(self, sense):
        """3am + rapid-fire messages → fatigue."""
        ts = _ts(2026, 6, 15, 3, tz="Asia/Riyadh")
        prev = ts - 30  # 30 seconds ago
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev,
        )
        assert reading.fatigue_risk is True

    def test_daytime_no_fatigue(self, sense):
        """10am with a long session is NOT fatigue."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        session_start = ts - (4 * 3600)  # 4 hour session
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            session_start_timestamp=session_start,
        )
        assert reading.fatigue_risk is False

    def test_evening_no_fatigue(self, sense):
        """8pm is fine even with rapid-fire messages."""
        ts = _ts(2026, 6, 15, 20, tz="Asia/Riyadh")
        prev = ts - 30
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev,
        )
        assert reading.fatigue_risk is False


# ═══════════════════════════════════════════════════════════
#  7. GREETINGS
# ═══════════════════════════════════════════════════════════

class TestGreetings:
    """Greetings should adapt to temporal and interaction context."""

    def test_morning_greeting(self, sense):
        """Morning (صباح) → 'صباح النور'."""
        ts = _ts(2026, 6, 15, 9, tz="Asia/Riyadh")
        # Previous interaction 1 hour ago (normal gap, not first)
        prev = ts - 3600
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev,
        )
        assert "صباح" in reading.greeting

    def test_late_night_greeting_overrides(self, sense):
        """Late night greeting shows gentle concern regardless of period."""
        ts = _ts(2026, 6, 15, 2, tz="Asia/Riyadh")
        prev = ts - 3600  # 1 hour ago (normal gap)
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev,
        )
        assert "متأخر" in reading.greeting or "بخير" in reading.greeting

    def test_returning_greeting_overrides(self, sense):
        """Returning after 3 days → welcome-back greeting overrides time."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        prev = ts - (3 * 24 * 3600)
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev,
        )
        assert "وحشتنا" in reading.greeting

    def test_first_interaction_greeting(self, sense):
        """First interaction gets a neutral welcome."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert "أهلاً" in reading.greeting

    def test_returning_overrides_late_night(self, sense):
        """Returning after long gap at 3am → returning greeting takes priority."""
        ts = _ts(2026, 6, 15, 3, tz="Asia/Riyadh")
        prev = ts - (5 * 24 * 3600)  # 5 days ago
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=prev,
        )
        assert "وحشتنا" in reading.greeting

    def test_convenience_get_greeting(self, sense):
        """get_greeting() returns just the string."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        greeting = sense.get_greeting(timestamp=ts, user_timezone="Asia/Riyadh")
        assert isinstance(greeting, str)
        assert len(greeting) > 0


# ═══════════════════════════════════════════════════════════
#  8. TIMEZONE HANDLING
# ═══════════════════════════════════════════════════════════

class TestTimezone:
    """The same unix timestamp should produce different readings in different zones."""

    def test_riyadh_vs_london(self, sense):
        """Riyadh is UTC+3; London is UTC+1 (BST in summer).
        Same instant, different local hour."""
        # Use a fixed UTC timestamp: 2026-06-15 12:00:00 UTC
        utc_dt = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        ts = utc_dt.timestamp()

        riyadh = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        london = sense.read(timestamp=ts, user_timezone="Europe/London")

        # Riyadh = UTC+3 → 15:00 (عصر)
        assert riyadh.hour == 15
        assert riyadh.period == "عصر"

        # London = UTC+1 (BST) → 13:00 (ظهر)
        assert london.hour == 13
        assert london.period == "ظهر"

    def test_timezone_stored_in_reading(self, sense):
        """The reading records which timezone was used."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.timezone == "Asia/Riyadh"

    def test_timestamp_preserved(self, sense):
        """The original unix timestamp is preserved in the reading."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.timestamp == ts

    def test_default_timezone(self, sense):
        """Default timezone is US/Eastern."""
        ts = _ts(2026, 6, 15, 10, tz="US/Eastern")
        reading = sense.read(timestamp=ts)  # no timezone specified
        assert reading.timezone == "US/Eastern"


# ═══════════════════════════════════════════════════════════
#  9. EDGE CASES
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_midnight_exactly(self, sense):
        """Midnight (hour=0) → ليل + is_late_night."""
        ts = _ts(2026, 6, 15, 0, 0, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.hour == 0
        assert reading.period == "ليل"
        assert reading.is_late_night is True

    def test_noon_exactly(self, sense):
        """Noon (hour=12) → ظهر, not صباح."""
        ts = _ts(2026, 6, 15, 12, 0, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.hour == 12
        assert reading.period == "ظهر"

    def test_hour_4_is_fajr_not_layl(self, sense):
        """4am is فجر, not ليل — the boundary."""
        ts = _ts(2026, 6, 15, 4, 0, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        assert reading.period == "فجر"
        assert reading.is_late_night is True  # 4am is still late night (0-5)

    def test_no_timestamp_uses_now(self, sense):
        """Passing no timestamp uses current time."""
        reading = sense.read(user_timezone="Asia/Riyadh")
        # Should be close to now
        import time
        assert abs(reading.timestamp - time.time()) < 2.0

    def test_zero_gap(self, sense):
        """Same timestamp for current and previous → سريع."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        reading = sense.read(
            timestamp=ts, user_timezone="Asia/Riyadh",
            previous_timestamp=ts,
        )
        assert reading.interaction_gap_assessment == "سريع"
        assert reading.time_since_last_interaction == timedelta(0)

    def test_dataclass_fields_complete(self, sense):
        """TimeReading has all expected fields."""
        ts = _ts(2026, 6, 15, 10, tz="Asia/Riyadh")
        reading = sense.read(timestamp=ts, user_timezone="Asia/Riyadh")
        expected_fields = {
            "hour", "minute", "period", "greeting",
            "day_of_week", "day_of_week_ar",
            "is_late_night", "is_work_hours",
            "is_weekend", "is_islamic_weekend", "is_western_weekend",
            "time_since_last_interaction", "interaction_gap_assessment",
            "fatigue_risk", "timezone", "timestamp",
        }
        actual_fields = set(reading.__dataclass_fields__.keys())
        assert expected_fields == actual_fields


# ═══════════════════════════════════════════════════════════
#  10. INTEGRATION SMOKE TEST
# ═══════════════════════════════════════════════════════════

class TestIntegration:
    """Simulate a real conversation flow through the time sense."""

    def test_conversation_flow(self, sense):
        """Simulate: first contact → rapid reply → long gap → return."""
        tz = "Asia/Riyadh"

        # First contact at 10am Sunday
        ts1 = _ts(2026, 6, 21, 10, tz=tz)
        r1 = sense.read(timestamp=ts1, user_timezone=tz)
        assert r1.interaction_gap_assessment == "أول_تواصل"
        assert r1.period == "صباح"
        assert r1.is_work_hours is True

        # Rapid reply 30 seconds later
        ts2 = ts1 + 30
        r2 = sense.read(timestamp=ts2, user_timezone=tz, previous_timestamp=ts1)
        assert r2.interaction_gap_assessment == "سريع"

        # Normal reply 45 minutes later
        ts3 = ts2 + (45 * 60)
        r3 = sense.read(timestamp=ts3, user_timezone=tz, previous_timestamp=ts2)
        assert r3.interaction_gap_assessment == "عادي"

        # Return after 5 days
        ts4 = ts3 + (5 * 24 * 3600)
        r4 = sense.read(timestamp=ts4, user_timezone=tz, previous_timestamp=ts3)
        assert r4.interaction_gap_assessment == "طويل"
        assert "وحشتنا" in r4.greeting

    def test_late_session_fatigue_arc(self, sense):
        """Simulate: start at 11pm, still going at 3am → fatigue."""
        tz = "Asia/Riyadh"

        # Start at 11pm
        session_start = _ts(2026, 6, 15, 23, tz=tz)
        ts_start = session_start
        r_start = sense.read(
            timestamp=ts_start, user_timezone=tz,
            session_start_timestamp=session_start,
        )
        assert r_start.fatigue_risk is False  # 11pm is not late-night (23 >= 5)
        assert r_start.period == "ليل"

        # Still going at 3am (4 hours later)
        ts_late = ts_start + (4 * 3600)
        r_late = sense.read(
            timestamp=ts_late, user_timezone=tz,
            previous_timestamp=ts_start + (3.5 * 3600),  # recent message
            session_start_timestamp=session_start,
        )
        assert r_late.fatigue_risk is True
        assert r_late.is_late_night is True
