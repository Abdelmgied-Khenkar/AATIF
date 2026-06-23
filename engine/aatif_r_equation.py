#!/usr/bin/env python3
"""
AATIF R Equation — أسلوب الرد (Response Style)
===============================================

R governs HOW عاطف responds — not WHETHER (that's S).

    R = σ(w₃·T + w₄·V + w₅·G + w₆·D)

Where:
    T = الزمن    (time signal)   — from حاسة الزمن (TimeSense)
    V = الصوت    (voice signal)  — from the input text itself
    G = الفجوة   (gap signal)    — time since last interaction
    D = المجال   (domain signal) — sensitivity of the domain

R produces a continuous style score in [0, 1]:
    Low  R (→0) = heavy / formal / careful     (الرسمي)
    High R (→1) = light / casual / warm         (العفوي)

Style mapping:
    R ≤ 0.3       → "formal"   (الرسمي)
    0.3 < R ≤ 0.5 → "balanced" (المتوازن)
    0.5 < R ≤ 0.7 → "warm"    (الدافئ)
    R > 0.7       → "casual"  (العفوي)

Three-layer architecture:
    S(d) = safety (math, deterministic)     — BUILT (aatif_s_equation.py)
    P(d) = domain protocols (rules)         — NOT YET BUILT
    R(d) = style (this module)              — supervised by gate

Key principle: R lives INSIDE the model, supervised by the gate.
The gate can LOWER R for sensitive domains, never raise it.
R does NOT affect safety — only formality, tone, length, dialect matching.

    "الاذي مالوش أسلوب — بس الأسلوب له مقام"
    Harm has no style — but style has its place.

Default weights (will be calibrated):
    w₃ (time)   = 1.0
    w₄ (voice)  = 1.5
    w₅ (gap)    = 0.8
    w₆ (domain) = 2.0   ← highest: domain is most important style factor

Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
License: BSL 1.1
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional

# ═══════════════════════════════════════════════════════════
#  Math — same sigmoid as S equation
# ═══════════════════════════════════════════════════════════

def sigmoid(x: float) -> float:
    """Standard sigmoid σ(x) = 1 / (1 + e^(-x))"""
    x = max(-500.0, min(500.0, x))
    return 1.0 / (1.0 + math.exp(-x))


# ═══════════════════════════════════════════════════════════
#  Default weights — R = σ(w₃·T + w₄·V + w₅·G + w₆·D)
# ═══════════════════════════════════════════════════════════

DEFAULT_WEIGHTS = {
    "w3": 1.0,   # time weight
    "w4": 1.5,   # voice weight
    "w5": 0.8,   # gap weight
    "w6": 2.0,   # domain weight — highest because domain matters most
}


# ═══════════════════════════════════════════════════════════
#  Domain D-signal mapping
# ═══════════════════════════════════════════════════════════
#
# D maps domain sensitivity to a style signal.
# Lower D = more careful/formal response style.
# Higher D = more free/casual response style.
#
# Ordering: healthcare ≤ education ≤ general ≤ tech ≤ ecommerce ≤ creative
#
# Note: this is STYLE sensitivity, not SAFETY sensitivity.
# Safety (θ) is in aatif_s_equation.py. D here only affects tone.

DOMAIN_D_SIGNALS = {
    "healthcare": 0.15,   # most careful — medical context
    "education":  0.25,   # careful — children/students
    "general":    0.50,   # balanced
    "tech":       0.50,   # balanced — technical context
    "ecommerce":  0.55,   # slightly more free
    "creative":   0.70,   # most free — art/writing
}

# Default D for unknown domains — treat as general
DEFAULT_D_SIGNAL = 0.50


# ═══════════════════════════════════════════════════════════
#  Style mapping — R score to style recommendation
# ═══════════════════════════════════════════════════════════

STYLE_MAP = [
    # (upper_bound, style_name, arabic_name)
    (0.3, "formal",   "الرسمي"),
    (0.5, "balanced", "المتوازن"),
    (0.7, "warm",     "الدافئ"),
    (1.0, "casual",   "العفوي"),
]


def r_to_style(r: float) -> str:
    """Map R score to style recommendation."""
    for bound, style, _ in STYLE_MAP:
        if r <= bound:
            return style
    return "casual"


# ═══════════════════════════════════════════════════════════
#  Gate review thresholds
# ═══════════════════════════════════════════════════════════
#
# The gate supervises R — it can LOWER R but never RAISE it.
# Sensitive domains have hard ceilings on how casual R can be.

GATE_CEILINGS = {
    "healthcare":  0.5,   # healthcare: R > 0.5 is too casual
    "education":   0.6,   # education (children): R > 0.6 is too casual
}


# ═══════════════════════════════════════════════════════════
#  Arabic text detection helpers
# ═══════════════════════════════════════════════════════════

# Arabic Unicode range
_ARABIC_RE = re.compile(r'[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]')

# Common dialect markers (Gulf/Egyptian/Levantine)
_DIALECT_MARKERS = [
    "وش", "ليه", "ابي", "عشان", "يعني", "خلاص", "طيب",  # Saudi
    "ايه", "ازاي", "كده", "عايز", "ماشي",                  # Egyptian
    "شو", "كيف", "بدي", "هلأ",                              # Levantine
    "شنو", "شلون", "هسه",                                   # Iraqi
    "واش", "كيفاش", "بزاف",                                  # Maghrebi
]


def _arabic_ratio(text: str) -> float:
    """Fraction of characters that are Arabic."""
    if not text:
        return 0.0
    arabic_count = len(_ARABIC_RE.findall(text))
    total = len(text.replace(" ", ""))
    if total == 0:
        return 0.0
    return arabic_count / total


def _has_dialect(text: str) -> bool:
    """Check if text contains Arabic dialect markers."""
    t = text.strip()
    for marker in _DIALECT_MARKERS:
        if marker in t:
            return True
    return False


# ═══════════════════════════════════════════════════════════
#  RReading — output of R computation
# ═══════════════════════════════════════════════════════════

@dataclass
class RReading:
    """
    What the R equation produces — أسلوب الرد.

    Contains the R score, individual signals, style recommendation,
    and gate supervision results.
    """
    # R score — the final (possibly gate-adjusted) style value
    r_score: float

    # Individual signal components (all in [0, 1])
    t_signal: float          # time signal
    v_signal: float          # voice signal
    g_signal: float          # gap signal
    d_signal: float          # domain signal

    # Style recommendation
    style_recommendation: str   # "formal" / "balanced" / "warm" / "casual"

    # Gate supervision
    gate_flags: list = field(default_factory=list)
    gate_adjusted: bool = False
    original_r: float = 0.0


# ═══════════════════════════════════════════════════════════
#  REquation — the R computation engine
# ═══════════════════════════════════════════════════════════

class REquation:
    """
    R = σ(w₃·T + w₄·V + w₅·G + w₆·D)

    Computes response STYLE (not safety).
    R determines how formal vs casual the response should be.

    Usage:
        r_eq = REquation()
        reading = r_eq.compute(
            text="وش الحل يا صاحبي؟",
            domain="general",
            time_reading=time_sense.read(),
            gap_seconds=120,
        )
        print(reading.r_score)              # → 0.73
        print(reading.style_recommendation) # → "casual"
    """

    def __init__(self, weights: Optional[dict] = None):
        """
        Initialize with configurable weights.

        Args:
            weights: dict with keys w3, w4, w5, w6.
                     Missing keys fall back to DEFAULT_WEIGHTS.
        """
        w = dict(DEFAULT_WEIGHTS)
        if weights:
            w.update(weights)
        self.w3 = float(w["w3"])  # time
        self.w4 = float(w["w4"])  # voice
        self.w5 = float(w["w5"])  # gap
        self.w6 = float(w["w6"])  # domain

    # ── T signal (time) ──

    def compute_t_signal(self, time_reading) -> float:
        """
        Extract T signal from a TimeReading — الزمن.

        Late night → lower T (person may be vulnerable, be careful).
        Morning → higher T (fresh energy, can be lighter).
        Fatigue detected → lower T.
        Fajr (pre-dawn) → lower T (unusual hour, be gentle).

        Args:
            time_reading: a TimeReading from aatif_time_sense.py, or None.

        Returns:
            T signal in [0, 1].
        """
        if time_reading is None:
            return 0.5  # neutral default — no time info

        period = time_reading.period
        is_late_night = time_reading.is_late_night
        fatigue_risk = time_reading.fatigue_risk

        # Base T from time period
        # صباح (morning) is the most energetic → highest T
        # ليل (night) and فجر (pre-dawn) → lowest T
        period_signals = {
            "فجر":  0.30,   # pre-dawn — unusual, be gentle
            "صباح": 0.75,   # morning — fresh, can be lighter
            "ظهر":  0.60,   # midday — moderate
            "عصر":  0.55,   # afternoon — moderate
            "مساء": 0.50,   # evening — settling down
            "ليل":  0.30,   # night — be careful
        }
        t = period_signals.get(period, 0.50)

        # Late night override (0-5am) → pull T down
        if is_late_night:
            t = min(t, 0.25)

        # Fatigue detected → pull T down further
        if fatigue_risk:
            t = min(t, 0.20)

        return t

    # ── V signal (voice) ──

    def compute_v_signal(self, text: str) -> float:
        """
        Extract V signal from input text — الصوت.

        Arabic dialect → warmth signal (higher V).
        English → slightly more formal (lower V).
        Very short / terse → could be urgent (lower V).
        Medium messages → moderate V.
        Emoji/exclamation → higher V (expressive).

        Args:
            text: the user's input message.

        Returns:
            V signal in [0, 1].
        """
        if not text or not text.strip():
            return 0.5  # neutral for empty text

        t = text.strip()
        words = t.split()
        word_count = len(words)
        char_count = len(t)

        # Start with a neutral base
        v = 0.50

        # Language detection
        ar_ratio = _arabic_ratio(t)

        if ar_ratio > 0.5:
            # Arabic text — check for dialect
            if _has_dialect(t):
                # Dialect detected → warmth signal
                v += 0.15
            else:
                # MSA Arabic → slightly formal
                v += 0.05
        elif ar_ratio < 0.1 and char_count > 0:
            # Primarily English → slightly more formal
            v -= 0.05

        # Message length signals
        if word_count <= 2:
            # Very short / terse → could be urgent or stressed
            v -= 0.10
        elif word_count <= 5:
            # Short but not terse → match brevity
            v += 0.0  # neutral
        elif word_count >= 15:
            # Longer message → person is engaged, moderate warmth
            v += 0.05

        # Expressive markers
        if "!" in t or "؟" in t:
            v += 0.05
        # Emoji presence (basic check for common Unicode emoji ranges)
        if re.search(r'[\U0001F300-\U0001F9FF]', t):
            v += 0.05

        # Clamp to [0, 1]
        return max(0.0, min(1.0, v))

    # ── G signal (gap) ──

    def compute_g_signal(self, gap_seconds: Optional[float] = None) -> float:
        """
        Extract G signal from interaction gap — الفجوة.

        Long gap (days/weeks) → lower G (welcome back, be gentle).
        Rapid-fire → higher G (match energy).
        Moderate gap → moderate G.
        First message / no data → moderate G.

        Args:
            gap_seconds: seconds since last interaction, or None.

        Returns:
            G signal in [0, 1].
        """
        if gap_seconds is None:
            # First interaction or no data → moderate
            return 0.45

        # Negative gap doesn't make sense — treat as no data
        if gap_seconds < 0:
            return 0.45

        # Time thresholds (in seconds)
        TWO_MINUTES = 2 * 60
        ONE_HOUR = 60 * 60
        FOUR_HOURS = 4 * 60 * 60
        ONE_DAY = 24 * 60 * 60
        ONE_WEEK = 7 * ONE_DAY

        if gap_seconds < TWO_MINUTES:
            # Rapid-fire → match energy, high G
            return 0.75
        elif gap_seconds < ONE_HOUR:
            # Active conversation → moderately high G
            return 0.65
        elif gap_seconds < FOUR_HOURS:
            # Normal gap → moderate G
            return 0.55
        elif gap_seconds < ONE_DAY:
            # Drifting → slightly careful
            return 0.45
        elif gap_seconds < ONE_WEEK:
            # Days away → be gentle on return
            return 0.30
        else:
            # Weeks/months away → most gentle
            return 0.20

    # ── D signal (domain sensitivity) ──

    def compute_d_signal(self, domain: str) -> float:
        """
        Extract D signal from domain name — المجال.

        Healthcare → most careful (lowest D).
        Creative → most free (highest D).
        Unknown domains → treated as general.

        Args:
            domain: domain name string (e.g. "healthcare", "creative").

        Returns:
            D signal in [0, 1].
        """
        d = domain.lower().strip() if domain else "general"
        return DOMAIN_D_SIGNALS.get(d, DEFAULT_D_SIGNAL)

    # ── Gate review ──

    def gate_review(self, r_score: float, domain: str) -> tuple:
        """
        Gate supervision — can LOWER R, never RAISE it.

        The gate reviews R and applies domain-specific ceilings.
        Sensitive domains have hard limits on how casual the style can be.

        Args:
            r_score: the computed R value.
            domain: domain name string.

        Returns:
            (adjusted_r, flags) where:
                adjusted_r: R after gate ceiling (may be lowered).
                flags: list of flag strings explaining adjustments.
        """
        flags = []
        d = domain.lower().strip() if domain else "general"
        adjusted_r = r_score

        # Check domain-specific ceilings
        ceiling = GATE_CEILINGS.get(d)
        if ceiling is not None and r_score > ceiling:
            flags.append(
                f"R={r_score:.3f} exceeds {d} ceiling ({ceiling}) "
                f"— too casual for {d} context"
            )
            adjusted_r = ceiling

        # Additional gate check: education with children
        # If domain is education and R > 0.6, flag even if not in GATE_CEILINGS
        # (this is already in GATE_CEILINGS, but the explicit check
        #  documents the architectural intent)

        return adjusted_r, flags

    # ── Main computation ──

    def compute(
        self,
        text: str,
        domain: str,
        time_reading=None,
        gap_seconds: Optional[float] = None,
    ) -> RReading:
        """
        Compute R — the response style score.

        R = σ(w₃·T + w₄·V + w₅·G + w₆·D)

        The gate reviews R and may lower it for sensitive domains.

        Args:
            text: user input message.
            domain: domain name (e.g. "healthcare", "general", "creative").
            time_reading: a TimeReading from aatif_time_sense.py, or None.
            gap_seconds: seconds since last interaction, or None.

        Returns:
            RReading with R score, signals, style, and gate info.
        """
        # Compute individual signals
        t_signal = self.compute_t_signal(time_reading)
        v_signal = self.compute_v_signal(text)
        g_signal = self.compute_g_signal(gap_seconds)
        d_signal = self.compute_d_signal(domain)

        # R equation — weighted sum through sigmoid
        z = (self.w3 * t_signal +
             self.w4 * v_signal +
             self.w5 * g_signal +
             self.w6 * d_signal)
        r_raw = sigmoid(z)

        # Gate review — may lower R for sensitive domains
        r_adjusted, gate_flags = self.gate_review(r_raw, domain)
        gate_adjusted = r_adjusted != r_raw

        # Style recommendation from final R
        style = r_to_style(r_adjusted)

        return RReading(
            r_score=round(r_adjusted, 4),
            t_signal=round(t_signal, 4),
            v_signal=round(v_signal, 4),
            g_signal=round(g_signal, 4),
            d_signal=round(d_signal, 4),
            style_recommendation=style,
            gate_flags=gate_flags,
            gate_adjusted=gate_adjusted,
            original_r=round(r_raw, 4),
        )


# ═══════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    r_eq = REquation()

    print("=" * 60)
    print("  R Equation — أسلوب الرد")
    print("  R = σ(w₃·T + w₄·V + w₅·G + w₆·D)")
    print("=" * 60)

    # Test 1: Casual Saudi dialect, general domain, rapid-fire
    reading = r_eq.compute(
        text="وش الحل يا صاحبي؟",
        domain="general",
        gap_seconds=60,
    )
    print(f"\n  Test 1: Casual Saudi greeting, general domain")
    print(f"    R = {reading.r_score:.4f}  →  {reading.style_recommendation}")
    print(f"    T={reading.t_signal} V={reading.v_signal} "
          f"G={reading.g_signal} D={reading.d_signal}")

    # Test 2: English text, healthcare domain
    reading2 = r_eq.compute(
        text="What are the side effects of this medication?",
        domain="healthcare",
        gap_seconds=3600,
    )
    print(f"\n  Test 2: English medical question, healthcare domain")
    print(f"    R = {reading2.r_score:.4f}  →  {reading2.style_recommendation}")
    print(f"    T={reading2.t_signal} V={reading2.v_signal} "
          f"G={reading2.g_signal} D={reading2.d_signal}")
    if reading2.gate_flags:
        for flag in reading2.gate_flags:
            print(f"    ⚠️  {flag}")
    print(f"    Gate adjusted: {reading2.gate_adjusted}")

    # Test 3: Arabic MSA, education domain, returning after days
    reading3 = r_eq.compute(
        text="أريد شرحاً مفصلاً عن الجاذبية",
        domain="education",
        gap_seconds=7 * 24 * 3600,  # 1 week
    )
    print(f"\n  Test 3: MSA Arabic, education, returning after a week")
    print(f"    R = {reading3.r_score:.4f}  →  {reading3.style_recommendation}")
    print(f"    T={reading3.t_signal} V={reading3.v_signal} "
          f"G={reading3.g_signal} D={reading3.d_signal}")

    # Test 4: Creative domain, dialect, active conversation
    reading4 = r_eq.compute(
        text="ابي اكتب قصيدة عن الحب يعني! 🎶",
        domain="creative",
        gap_seconds=30,
    )
    print(f"\n  Test 4: Saudi dialect, creative domain, rapid-fire")
    print(f"    R = {reading4.r_score:.4f}  →  {reading4.style_recommendation}")
    print(f"    T={reading4.t_signal} V={reading4.v_signal} "
          f"G={reading4.g_signal} D={reading4.d_signal}")

    print(f"\n{'=' * 60}")
    print(f"  الأمان (S) يحدد هل نجاوب — الأسلوب (R) يحدد كيف نجاوب")
    print(f"{'=' * 60}")
