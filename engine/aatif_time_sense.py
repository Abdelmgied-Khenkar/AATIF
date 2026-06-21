#!/usr/bin/env python3
"""
AATIF Time Sense — حاسة الزمن
==============================

Fourth perception channel of عاطف:  T (time / temporal awareness)

    H = حرارة الكلمة  (harm)     — surface danger
    I = النية          (intent)   — what the person wants
    E = الشعور         (emotion)  — what the person is feeling
    T = الزمن          (time)     — WHEN the person is speaking

Why this exists:
  الذكاء بلا استيعاب للوقت مجرد محرك بحث دقيق فقط.
  Intelligence without temporal awareness is just a precise search engine.

  A person writing at 3am carries different weight than the same message
  at 10am. A person who returns after 3 weeks of silence is in a different
  emotional place than someone in rapid-fire conversation. A greeting at
  فجر should feel different from a greeting at عصر.

  This is not a utility — it is a SENSE. عاطف perceives time the way
  a compassionate human does: not as data, but as context that shapes
  how to respond.

Design:
  - Pure Python (datetime + zoneinfo from stdlib, no external deps)
  - Arabic-first: time periods use Arabic cultural divisions
    (فجر، صباح، ظهر، عصر، مساء، ليل)
  - Dual weekend awareness: Islamic (Fri-Sat) and Western (Sat-Sun)
  - Fatigue detection: late night + long session = care more
  - Interaction gap assessment: returning after silence vs rapid-fire

Integration:
  - Callable from the main pipeline alongside H, I, E
  - Conversation memory can feed previous_timestamp for gap assessment
  - Returns a TimeReading dataclass consumable by the response shaper

Architect: Abdulmjeed Ibrahim Khenkar
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

# zoneinfo is stdlib since Python 3.9
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python 3.8 fallback (unlikely in modern deployments)
    from backports.zoneinfo import ZoneInfo  # type: ignore


# ═══════════════════════════════════════════════════════════
#  Time periods — Arabic cultural divisions of the day
# ═══════════════════════════════════════════════════════════

# These aren't arbitrary — they map to how Arabic speakers naturally
# divide their day, anchored to prayer times and daily rhythms.
#
#   فجر    (fajr)    = pre-dawn to sunrise    (~4:00 - 6:00)
#   صباح   (sabah)   = morning               (~6:00 - 12:00)
#   ظهر    (dhuhr)   = midday / noon         (~12:00 - 14:00)
#   عصر    (asr)     = afternoon             (~14:00 - 17:00)
#   مساء   (masa')   = evening               (~17:00 - 21:00)
#   ليل    (layl)    = night                 (~21:00 - 4:00)

TIME_PERIODS = [
    # (start_hour, end_hour, name, greeting)
    (4,  6,  "فجر",  "صباح الخير — بدري عليك"),
    (6,  12, "صباح", "صباح النور"),
    (12, 14, "ظهر",  "يسعد وقتك"),
    (14, 17, "عصر",  "مساء الخير"),
    (17, 21, "مساء", "مساء النور"),
    (21, 4,  "ليل",  "أهلاً — الله يسهل ليلتك"),
]

# Greetings adjust for context
LATE_NIGHT_GREETING = "أهلاً — متأخر الوقت، إن شاء الله كل شي بخير"
RETURNING_GREETING = "أهلاً من جديد — وحشتنا"
FIRST_INTERACTION_GREETING = "أهلاً وسهلاً"


# ═══════════════════════════════════════════════════════════
#  TimeReading — what the sense produces
# ═══════════════════════════════════════════════════════════

@dataclass
class TimeReading:
    """
    What حاسة الزمن perceives at a given moment.

    This is the temporal equivalent of what E returns for emotion
    or I returns for intent — structured context the pipeline can use.
    """
    # Current time awareness
    hour: int                          # 0-23
    minute: int                        # 0-59
    period: str                        # فجر / صباح / ظهر / عصر / مساء / ليل
    greeting: str                      # appropriate Arabic greeting
    day_of_week: str                   # Monday, Tuesday, etc.
    day_of_week_ar: str                # الاثنين، الثلاثاء، etc.

    # Contextual flags
    is_late_night: bool                # midnight-5am — possible fatigue/stress
    is_work_hours: bool                # 9am-5pm
    is_weekend: bool                   # True if weekend in EITHER calendar
    is_islamic_weekend: bool           # Friday-Saturday
    is_western_weekend: bool           # Saturday-Sunday

    # Interaction dynamics (require previous_timestamp)
    time_since_last_interaction: Optional[timedelta]
    interaction_gap_assessment: str    # "طويل" / "عادي" / "سريع" / "أول_تواصل"
    fatigue_risk: bool                 # late night + long session or long active time

    # Timezone info
    timezone: str                      # timezone name used for this reading
    timestamp: float                   # the unix timestamp that was read


# ═══════════════════════════════════════════════════════════
#  TimeSense — the sense itself
# ═══════════════════════════════════════════════════════════

class TimeSense:
    """
    حاسة الزمن — عاطف's temporal awareness.

    A sense, not a utility. It reads the temporal environment
    the way E reads emotional state or H reads danger proximity.

    Usage:
        sense = TimeSense()
        reading = sense.read()                    # now, default timezone
        reading = sense.read(user_timezone="Asia/Riyadh")
        reading = sense.read(previous_timestamp=last_turn_ts)
    """

    # Day names in Arabic
    DAYS_AR = {
        "Monday": "الاثنين",
        "Tuesday": "الثلاثاء",
        "Wednesday": "الأربعاء",
        "Thursday": "الخميس",
        "Friday": "الجمعة",
        "Saturday": "السبت",
        "Sunday": "الأحد",
    }

    # Interaction gap thresholds
    GAP_RAPID = timedelta(minutes=2)       # < 2 min = rapid-fire
    GAP_NORMAL_MAX = timedelta(hours=4)    # < 4 hours = normal
    GAP_LONG = timedelta(days=1)           # > 1 day = long gap
    # between 4h and 1d = also "عادي" (normal but drifting)

    def read(
        self,
        timestamp: Optional[float] = None,
        user_timezone: str = "US/Eastern",
        previous_timestamp: Optional[float] = None,
        session_start_timestamp: Optional[float] = None,
    ) -> TimeReading:
        """
        Read the current temporal context.

        Args:
            timestamp: Unix timestamp to read (None = now)
            user_timezone: IANA timezone string (e.g. "Asia/Riyadh", "US/Eastern")
            previous_timestamp: Unix timestamp of previous interaction (for gap assessment)
            session_start_timestamp: When this session began (for fatigue detection)

        Returns:
            TimeReading with full temporal context
        """
        ts = timestamp if timestamp is not None else time.time()

        # Convert to user's local time
        tz = ZoneInfo(user_timezone)
        dt = datetime.fromtimestamp(ts, tz=tz)

        hour = dt.hour
        minute = dt.minute
        day_name = dt.strftime("%A")  # English day name
        day_name_ar = self.DAYS_AR.get(day_name, day_name)

        # Determine time period
        period = self._get_period(hour)

        # Weekend detection
        is_islamic_weekend = day_name in ("Friday", "Saturday")
        is_western_weekend = day_name in ("Saturday", "Sunday")
        is_weekend = is_islamic_weekend or is_western_weekend

        # Late night: midnight to 5am
        is_late_night = 0 <= hour < 5

        # Work hours: 9am to 5pm
        is_work_hours = 9 <= hour < 17

        # Interaction gap
        gap = None
        gap_assessment = "أول_تواصل"  # first interaction
        if previous_timestamp is not None:
            gap = timedelta(seconds=ts - previous_timestamp)
            gap_assessment = self._assess_gap(gap)

        # Fatigue risk: late night AND (long session OR rapid interaction after gap)
        fatigue_risk = self._assess_fatigue(
            hour=hour,
            gap=gap,
            session_start_timestamp=session_start_timestamp,
            current_timestamp=ts,
        )

        # Greeting (context-aware)
        greeting = self._select_greeting(
            hour=hour,
            period=period,
            is_late_night=is_late_night,
            gap_assessment=gap_assessment,
        )

        return TimeReading(
            hour=hour,
            minute=minute,
            period=period,
            greeting=greeting,
            day_of_week=day_name,
            day_of_week_ar=day_name_ar,
            is_late_night=is_late_night,
            is_work_hours=is_work_hours,
            is_weekend=is_weekend,
            is_islamic_weekend=is_islamic_weekend,
            is_western_weekend=is_western_weekend,
            time_since_last_interaction=gap,
            interaction_gap_assessment=gap_assessment,
            fatigue_risk=fatigue_risk,
            timezone=user_timezone,
            timestamp=ts,
        )

    def get_greeting(
        self,
        timestamp: Optional[float] = None,
        user_timezone: str = "US/Eastern",
        previous_timestamp: Optional[float] = None,
    ) -> str:
        """
        Convenience: just get the appropriate greeting.

        For quick use when you only need the greeting string
        without the full TimeReading.
        """
        reading = self.read(
            timestamp=timestamp,
            user_timezone=user_timezone,
            previous_timestamp=previous_timestamp,
        )
        return reading.greeting

    # ── Internal perception methods ──

    def _get_period(self, hour: int) -> str:
        """Map hour to Arabic time period."""
        # ليل wraps around midnight: 21-4
        if hour >= 21 or hour < 4:
            return "ليل"
        for start, end, name, _ in TIME_PERIODS:
            if start <= hour < end:
                return name
        # Fallback (should never reach)
        return "ليل"

    def _get_period_greeting(self, period: str) -> str:
        """Get the default greeting for a time period."""
        for _, _, name, greeting in TIME_PERIODS:
            if name == period:
                return greeting
        return FIRST_INTERACTION_GREETING

    def _assess_gap(self, gap: timedelta) -> str:
        """
        Assess the interaction gap.

        Returns:
            "سريع"  — rapid-fire (< 2 min), might indicate urgency
            "عادي"  — normal conversational rhythm
            "طويل"  — long gap (> 1 day), person is returning
        """
        if gap <= self.GAP_RAPID:
            return "سريع"
        elif gap <= self.GAP_LONG:
            return "عادي"
        else:
            return "طويل"

    def _assess_fatigue(
        self,
        hour: int,
        gap: Optional[timedelta],
        session_start_timestamp: Optional[float],
        current_timestamp: float,
    ) -> bool:
        """
        Detect fatigue risk.

        Fatigue is flagged when:
          - It's late night (0-5am) AND either:
            a) Session has been running > 2 hours, OR
            b) Interaction is rapid-fire (person can't stop)

        This is compassionate detection — not judgment.
        عاطف notices when someone might be running on fumes.
        """
        is_late = 0 <= hour < 5

        if not is_late:
            return False

        # Long session check
        if session_start_timestamp is not None:
            session_duration = timedelta(
                seconds=current_timestamp - session_start_timestamp
            )
            if session_duration > timedelta(hours=2):
                return True

        # Rapid interaction at a late hour
        if gap is not None and gap <= self.GAP_RAPID:
            return True

        # Late night alone is a mild signal — flag it
        return True

    def _select_greeting(
        self,
        hour: int,
        period: str,
        is_late_night: bool,
        gap_assessment: str,
    ) -> str:
        """
        Select the most appropriate greeting based on full context.

        Priority:
          1. Returning after long gap → welcome-back greeting
          2. Late night → gentle concern
          3. First interaction → neutral welcome
          4. Default → time-appropriate greeting
        """
        if gap_assessment == "طويل":
            return RETURNING_GREETING
        if is_late_night:
            return LATE_NIGHT_GREETING
        if gap_assessment == "أول_تواصل":
            return FIRST_INTERACTION_GREETING
        return self._get_period_greeting(period)


# ═══════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    sense = TimeSense()

    print("=" * 60)
    print("  حاسة الزمن — AATIF Time Sense")
    print("=" * 60)

    # Current time reading
    reading = sense.read(user_timezone="Asia/Riyadh")
    print(f"\n  الآن في الرياض:")
    print(f"    الوقت: {reading.hour:02d}:{reading.minute:02d}")
    print(f"    الفترة: {reading.period}")
    print(f"    التحية: {reading.greeting}")
    print(f"    اليوم: {reading.day_of_week_ar} ({reading.day_of_week})")
    print(f"    نهاية أسبوع: {reading.is_weekend}")
    print(f"    ساعات عمل: {reading.is_work_hours}")
    print(f"    ليل متأخر: {reading.is_late_night}")

    # Simulate someone returning after 3 days
    three_days_ago = time.time() - (3 * 24 * 60 * 60)
    reading2 = sense.read(
        user_timezone="Asia/Riyadh",
        previous_timestamp=three_days_ago,
    )
    print(f"\n  شخص راجع بعد 3 أيام:")
    print(f"    تقييم الفجوة: {reading2.interaction_gap_assessment}")
    print(f"    التحية: {reading2.greeting}")

    # Simulate 3am rapid-fire
    from datetime import datetime as dt_cls
    late_night_ts = datetime(2026, 6, 21, 3, 15, 0,
                            tzinfo=ZoneInfo("Asia/Riyadh")).timestamp()
    two_min_ago = late_night_ts - 90  # 1.5 min ago
    reading3 = sense.read(
        timestamp=late_night_ts,
        user_timezone="Asia/Riyadh",
        previous_timestamp=two_min_ago,
        session_start_timestamp=late_night_ts - 7200,  # 2h session
    )
    print(f"\n  الساعة 3 الفجر + جلسة طويلة:")
    print(f"    خطر إرهاق: {reading3.fatigue_risk}")
    print(f"    التحية: {reading3.greeting}")
    print(f"    تقييم الفجوة: {reading3.interaction_gap_assessment}")

    print(f"\n{'=' * 60}")
    print(f"  عاطف يحس بالوقت — مش بس يقرأه")
    print(f"{'=' * 60}")
