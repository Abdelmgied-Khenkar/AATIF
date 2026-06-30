#!/usr/bin/env python3
"""
AATIF Logic Profile Scanner — ماسح المنطق  (Field Note #048)
======================================================================

"اقرأ كيف يُفكّرون قبل أن تُقرر كيف تُجيب."
"Read how they think before deciding how to respond."

Every AATIF scorer so far reads the CONTENT of a message — what is asked. FN#048
says the system also misses the STYLE of a message — HOW it is asked. A tester
and a sincere learner can use the same words and need completely different
responses. The Logic Profile Scanner reads the reasoning style so the response
can be tuned to the person, not just the question.

THE FIVE PROFILES
─────────────────
  REDUCTIONIST    — shrinks the frame, reduces the system to one part
                    ("هذا مجرد chatbot متقدم", "it's just a fancy autocomplete")
  CHALLENGER      — pushes and pressures, wants to bring the idea down
                    ("أنت غلط وهذا لن ينجح", "this won't work, prove me wrong")
  TESTER          — methodically asks "where's the evidence?"
                    ("أين الدليل على أن هذا يعمل؟", "what's the methodology?")
  SINCERE_LEARNER — seeks understanding, searches for meaning
                    ("ساعدني أفهم كيف يختلف هذا", "help me understand how…")
  EGO_DRIVEN      — competes or asserts presence, not seeking understanding
                    ("أنا أعرف AI أكثر منك", "I'm an expert, I could do better")

STRICT CONSTITUTIONAL CONSTRAINT (from the field note)
──────────────────────────────────────────────────────
LPS analyses ONLY observable language patterns — it NEVER makes hidden
psychological claims. Every reading is justified by concrete surface signals
(words, phrases, punctuation) that the caller can inspect in `signals`. There is
no inference about who the person "really is" — only about how their language
reads. This keeps LPS honest and auditable.

HOW IT WORKS
────────────
PURE LOGIC — no embeddings, no LLM, no Ollama. The scanner is a deterministic
keyword/pattern matcher (Arabic + English), exactly like every other rule-based
AATIF module. Output is a LogicProfileResult: one ProfileReading per profile, the
primary (strongest) profile, an optional secondary, a profile-mix flag for
ambiguous style, and a recommended tone for the response.

LPS NEVER influences S(d). It is pure annotation and prompt enrichment — the
safety decision is made by the S engine before LPS ever runs.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Ensure the engine directory is importable (same pattern as the other modules)
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


# ═══════════════════════════════════════════════════════════
#  LogicProfile — the five reasoning styles
# ═══════════════════════════════════════════════════════════

class LogicProfile(Enum):
    """The five observable reasoning styles a message can carry."""
    REDUCTIONIST = "reductionist"        # يُصغّر الإطار
    CHALLENGER = "challenger"            # يضغط ويهاجم
    TESTER = "tester"                    # يطلب الدليل
    SINCERE_LEARNER = "sincere_learner"  # يطلب الفهم
    EGO_DRIVEN = "ego_driven"            # يفرض حضوره


# ═══════════════════════════════════════════════════════════
#  ProfileReading — what was detected for ONE profile
# ═══════════════════════════════════════════════════════════

@dataclass
class ProfileReading:
    """The reading for a single logic profile."""
    profile: LogicProfile
    confidence: float                   # 0.0 .. 1.0
    signals: List[str] = field(default_factory=list)  # observable signals that fired
    description: str = ""               # brief description of what was detected

    @property
    def detected(self) -> bool:
        """True when at least one observable signal fired for this profile."""
        return bool(self.signals)


# ═══════════════════════════════════════════════════════════
#  LogicProfileResult — the full five-profile reading
# ═══════════════════════════════════════════════════════════

@dataclass
class LogicProfileResult:
    """The complete logic-profile reading for one message."""
    primary_profile: LogicProfile             # strongest detected profile
    secondary_profile: Optional[LogicProfile]  # second strongest (if strong enough)
    readings: Dict[LogicProfile, ProfileReading]  # all five readings
    profile_mix: bool                          # multiple profiles detected (ambiguous)
    recommended_tone: str                      # how to adjust response tone

    def as_list(self) -> List[ProfileReading]:
        """All five readings in canonical profile order."""
        return [self.readings[p] for p in LogicProfile]

    def detected_profiles(self) -> List[LogicProfile]:
        """The profiles that were actually identified (had observable signals)."""
        return [r.profile for r in self.as_list() if r.detected]


# ═══════════════════════════════════════════════════════════
#  Signal vocabularies (Arabic + English) — PURE LOGIC
# ═══════════════════════════════════════════════════════════
#
# Each profile has its own marker set. These are OBSERVABLE language patterns —
# words and phrases that actually appear in the text — never psychological
# inferences. The field note is strict: LPS reads language, not minds.

# ── Reductionist: shrinks the frame, reduces to one part ──
_REDUCTIONIST_MARKERS_AR = [
    "مجرد", "فقط", "بس هو", "مش اكثر من", "ما هو الا", "ماهو الا",
    "زي اي", "مثل اي", "نفس اي", "لا يعدو", "ليس الا", "ليس اكثر من",
    "كله عباره عن", "مجرد اله", "شي بسيط",
]
_REDUCTIONIST_MARKERS_EN = [
    "just a", "merely", "nothing but", "nothing more than", "only a",
    "it's just", "its just", "same as any", "like every other",
    "like any other", "no different from", "at the end of the day it's just",
    "basically just", "simply a",
]

# ── Challenger: pushes, pressures, predicts failure ──
_CHALLENGER_MARKERS_AR = [
    "غلط", "خطا", "انت غلط", "هذا خطا", "لن ينجح", "ما راح يشتغل",
    "ما بينفع", "مستحيل", "اثبت العكس", "اثبت لي", "ورني حاله وحده",
    "هذا فاشل", "كلام فاضي", "ما له معنى", "ما يصير", "تحداك",
    "اتحداك", "ما اقتنع",
]
_CHALLENGER_MARKERS_EN = [
    "wrong", "incorrect", "flawed", "won't work", "wont work",
    "will fail", "this will fail", "impossible", "prove me wrong",
    "show me one case", "show me a single", "that's nonsense",
    "thats nonsense", "makes no sense", "you're wrong", "youre wrong",
    "i'm not convinced", "im not convinced", "this is broken",
]

# ── Tester: methodically requests evidence / methodology ──
_TESTER_MARKERS_AR = [
    "اين الدليل", "وين الدليل", "ما هو الدليل", "الدليل", "اثبات",
    "كيف تقيس", "كيف تقيسون", "وش المنهجيه", "ما المنهجيه", "المنهجيه",
    "مقارنه بـ", "مقارنه ب", "بالمقارنه مع", "كيف يختلف عن",
    "وش الفرق عن", "وين النتائج", "ورني النتائج", "بياناتك", "وش بياناتك",
    "معيار", "معايير",
]
_TESTER_MARKERS_EN = [
    "where's the evidence", "wheres the evidence", "what's the evidence",
    "whats the evidence", "what data", "show me results", "show me the data",
    "how do you measure", "what's the methodology", "whats the methodology",
    "methodology", "compared to", "how does this differ from",
    "how is this different from", "benchmark", "what's the proof",
    "whats the proof", "any data", "peer reviewed", "peer-reviewed",
]

# ── Sincere Learner: seeks understanding, collaborative curiosity ──
_LEARNER_MARKERS_AR = [
    "ساعدني افهم", "ساعدني اني افهم", "ابي افهم", "ابغى افهم",
    "اريد ان افهم", "وضح لي", "ممكن توضح", "ممكن تشرح", "اشرح لي",
    "كيف يختلف هذا", "ليش", "ليه", "وش يخلي", "ما الذي يجعل",
    "اخبرني اكثر", "قل لي اكثر", "ودي اتعلم", "ابغى اتعلم", "فضولي",
    "متشوق افهم",
]
_LEARNER_MARKERS_EN = [
    "help me understand", "explain how", "explain to me", "i want to learn",
    "i'd like to understand", "id like to understand", "i want to understand",
    "can you clarify", "can you explain", "could you explain", "tell me more",
    "i'm curious", "im curious", "why does", "what makes", "how come",
    "i'm trying to understand", "im trying to understand", "walk me through",
]

# ── Ego-Driven: asserts presence, cites credentials, competes ──
_EGO_MARKERS_AR = [
    "انا اعرف", "انا اعلم منك", "اعرف اكثر منك", "انا خبير", "انا متخصص",
    "عندي خبره", "لي سنين", "اشتغل في هذا من", "واضح انك", "واضح انك ما",
    "انت واضح ما", "خليني اقول لك", "دعني اخبرك", "اقدر اسوي احسن",
    "طريقتي افضل", "انا نشرت", "عندي دكتوراه", "انا دكتور", "صدقني انا",
    "انا افهم اكثر",
]
_EGO_MARKERS_EN = [
    "i know more", "i know better", "i've been doing this for",
    "ive been doing this for", "in my experience", "i'm an expert",
    "im an expert", "let me tell you", "obviously you", "you clearly don't",
    "you clearly dont", "you obviously don't", "i could do better",
    "my approach is superior", "my approach is better", "i have a phd",
    "i've published", "ive published", "trust me, i", "trust me i",
    "i know ai better than you",
]


# ═══════════════════════════════════════════════════════════
#  Per-profile metadata (descriptions + recommended tones)
# ═══════════════════════════════════════════════════════════

_PROFILE_DESCRIPTION = {
    LogicProfile.REDUCTIONIST: (
        "minimizing/reductive framing — shrinking the system to one part"
    ),
    LogicProfile.CHALLENGER: (
        "confrontational pressure — pushing to bring the idea down"
    ),
    LogicProfile.TESTER: (
        "methodical evidence-seeking — asking for proof, data, methodology"
    ),
    LogicProfile.SINCERE_LEARNER: (
        "understanding-seeking — collaborative, curious questions"
    ),
    LogicProfile.EGO_DRIVEN: (
        "self-asserting — credential-citing, competitive framing"
    ),
}

_TONE_BY_PROFILE = {
    LogicProfile.REDUCTIONIST: (
        "Expand the frame — show depth and nuance without defensiveness. "
        "Don't argue the reduction; reveal what it leaves out. "
        "(وسّع الإطار وأظهر العمق بلا دفاعية)"
    ),
    LogicProfile.CHALLENGER: (
        "Stay grounded — present evidence calmly and don't match the "
        "aggression. Engage the substance, not the pressure. "
        "(ابقَ ثابتاً، قدّم الدليل بهدوء ولا تجارِ الحدّة)"
    ),
    LogicProfile.TESTER: (
        "Provide data and cite sources — respect the methodical approach. "
        "Answer the evidence question directly and precisely. "
        "(قدّم البيانات واذكر المصادر واحترم المنهجية)"
    ),
    LogicProfile.SINCERE_LEARNER: (
        "Teach warmly — explain step by step and encourage more questions. "
        "Meet the curiosity with clarity and patience. "
        "(علّم بدفء، اشرح خطوة بخطوة وشجّع الأسئلة)"
    ),
    LogicProfile.EGO_DRIVEN: (
        "Acknowledge the expertise without submission — redirect to "
        "substance. Respect the person, stay on the merits. "
        "(اعترف بالخبرة دون خضوع وأعِد التوجيه إلى الجوهر)"
    ),
}

# Neutral tone when no profile is clearly detected.
_TONE_NEUTRAL = (
    "No strong reasoning style detected — respond naturally and clearly. "
    "(لا نمط واضح — أجب بوضوح وطبيعية)"
)

# Tone when the style is genuinely mixed/ambiguous.
_TONE_MIXED = (
    "Mixed reasoning style detected — lead with the primary profile's tone "
    "but stay flexible; the style is ambiguous. "
    "(نمط مختلط — اتبع الأقوى مع مرونة)"
)


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    """Lightweight Arabic normalization (matches the other rule-based modules)."""
    t = text.strip()
    t = re.sub(r"[ًٌٍَُِّْ]", "", t)            # strip diacritics
    t = t.replace("ة", "ه").replace("ى", "ي")    # normalize endings
    t = re.sub(r"[أإآ]", "ا", t)                  # normalize alef
    return t


def _count_hits(haystack_norm: str, haystack_low: str,
                markers_ar: List[str], markers_en: List[str]) -> List[str]:
    """Return the markers that appear in the text (AR on normalized text, EN on
    lowercased text). Each hit is an OBSERVABLE signal — a phrase that is
    literally present, never an inference."""
    hits: List[str] = []
    for m in markers_ar:
        if _normalize(m) in haystack_norm:
            hits.append(m)
    for m in markers_en:
        if m in haystack_low:
            hits.append(m)
    return hits


# ═══════════════════════════════════════════════════════════
#  LogicProfileScanner — ماسح المنطق
# ═══════════════════════════════════════════════════════════

class LogicProfileScanner:
    """
    Reads the reasoning STYLE of a message (FN#048).

    PURE LOGIC — keyword/pattern based, no LLM, no embeddings, no Ollama.
    Analyses ONLY observable language patterns; it never makes hidden
    psychological claims. Every reading lists the concrete signals that fired.

    Usage:
        scanner = LogicProfileScanner()
        result = scanner.scan("أين الدليل على أن هذا يعمل؟")
        result.primary_profile           # LogicProfile.TESTER
        result.recommended_tone          # data/source guidance
    """

    # Confidence threshold above which a second profile is reported as secondary,
    # and above which the style is considered a genuine "mix".
    _SECONDARY_THRESHOLD = 0.4

    def __init__(self) -> None:
        # Pure logic — nothing to construct. Kept explicit for the optional
        # module pattern (the Governor constructs this with no arguments).
        pass

    # ───────────────────────────────────────────────────
    #  Main entry
    # ───────────────────────────────────────────────────

    def scan(self, text: str) -> LogicProfileResult:
        """
        Scan a message and classify its reasoning style.

        Args:
            text: the user's message.

        Returns:
            LogicProfileResult — one ProfileReading per profile, the primary and
            (optional) secondary profile, a profile-mix flag, and the recommended
            response tone.
        """
        raw = text or ""
        norm = _normalize(raw)
        low = raw.lower()

        readings: Dict[LogicProfile, ProfileReading] = {
            LogicProfile.REDUCTIONIST: self._read(
                LogicProfile.REDUCTIONIST, norm, low,
                _REDUCTIONIST_MARKERS_AR, _REDUCTIONIST_MARKERS_EN,
            ),
            LogicProfile.CHALLENGER: self._read(
                LogicProfile.CHALLENGER, norm, low,
                _CHALLENGER_MARKERS_AR, _CHALLENGER_MARKERS_EN,
            ),
            LogicProfile.TESTER: self._read(
                LogicProfile.TESTER, norm, low,
                _TESTER_MARKERS_AR, _TESTER_MARKERS_EN,
            ),
            LogicProfile.SINCERE_LEARNER: self._read(
                LogicProfile.SINCERE_LEARNER, norm, low,
                _LEARNER_MARKERS_AR, _LEARNER_MARKERS_EN,
            ),
            LogicProfile.EGO_DRIVEN: self._read(
                LogicProfile.EGO_DRIVEN, norm, low,
                _EGO_MARKERS_AR, _EGO_MARKERS_EN,
            ),
        }

        primary, secondary, profile_mix = self._rank(readings)
        result = LogicProfileResult(
            primary_profile=primary,
            secondary_profile=secondary,
            readings=readings,
            profile_mix=profile_mix,
            recommended_tone="",  # filled in below
        )
        result.recommended_tone = recommend_tone(result)
        return result

    # ───────────────────────────────────────────────────
    #  Per-profile reader
    # ───────────────────────────────────────────────────

    def _read(
        self,
        profile: LogicProfile,
        norm: str,
        low: str,
        markers_ar: List[str],
        markers_en: List[str],
    ) -> ProfileReading:
        """Build the reading for one profile from its observable signals."""
        signals = _count_hits(norm, low, markers_ar, markers_en)
        if not signals:
            return ProfileReading(
                profile=profile, confidence=0.0, signals=[],
                description=f"no {profile.value} signals",
            )
        # Confidence scales with how many distinct signals agree (capped).
        confidence = min(0.95, 0.5 + 0.15 * len(signals))
        return ProfileReading(
            profile=profile, confidence=confidence, signals=signals,
            description=_PROFILE_DESCRIPTION[profile],
        )

    # ───────────────────────────────────────────────────
    #  Ranking — primary / secondary / mix
    # ───────────────────────────────────────────────────

    def _rank(
        self, readings: Dict[LogicProfile, ProfileReading],
    ) -> tuple:
        """Determine the primary profile, optional secondary, and mix flag.

        When no profile fires, the primary defaults to SINCERE_LEARNER — the
        most charitable reading (assume good faith) and the safest default tone
        (teach warmly). A genuine "mix" requires at least two profiles both
        above the secondary threshold.

        Profiles are tie-broken by a fixed priority that favours the readings
        the response must handle most carefully (challenger/ego over the
        cooperative learner) so an aggressive co-signal is never masked.
        """
        # Tie-break priority — higher means "wins ties". Confrontational and
        # ego styles outrank the cooperative ones so they are never hidden by a
        # tie with a softer profile.
        priority = {
            LogicProfile.CHALLENGER: 5,
            LogicProfile.EGO_DRIVEN: 4,
            LogicProfile.REDUCTIONIST: 3,
            LogicProfile.TESTER: 2,
            LogicProfile.SINCERE_LEARNER: 1,
        }
        detected = [r for r in readings.values() if r.detected]
        if not detected:
            # No observable style signals — assume sincere good faith.
            return LogicProfile.SINCERE_LEARNER, None, False

        detected.sort(
            key=lambda r: (r.confidence, priority[r.profile]), reverse=True,
        )
        primary = detected[0].profile

        secondary: Optional[LogicProfile] = None
        profile_mix = False
        if len(detected) >= 2:
            second = detected[1]
            if second.confidence >= self._SECONDARY_THRESHOLD:
                secondary = second.profile
                # A genuine mix: both top profiles cleared the threshold.
                if detected[0].confidence >= self._SECONDARY_THRESHOLD:
                    profile_mix = True

        return primary, secondary, profile_mix


# ═══════════════════════════════════════════════════════════
#  recommend_tone — response tone adjustment, by profile
# ═══════════════════════════════════════════════════════════

def recommend_tone(result: LogicProfileResult) -> str:
    """Suggest how to adjust the response tone based on the detected profile.

    REDUCTIONIST    → expand the frame, show depth without defensiveness.
    CHALLENGER      → stay grounded, present evidence calmly.
    TESTER          → provide data, cite sources, respect the method.
    SINCERE_LEARNER → teach warmly, step by step, encourage questions.
    EGO_DRIVEN      → acknowledge expertise without submission, redirect to substance.

    When nothing was detected, returns a neutral guidance. When the style is a
    genuine mix, leads with the primary profile's tone plus a flexibility note.
    """
    # Nothing detected at all → neutral.
    if not result.detected_profiles():
        return _TONE_NEUTRAL

    primary_tone = _TONE_BY_PROFILE.get(result.primary_profile, _TONE_NEUTRAL)
    if result.profile_mix:
        return f"{_TONE_MIXED}\n{primary_tone}"
    return primary_tone


# ═══════════════════════════════════════════════════════════
#  Demo
# ═══════════════════════════════════════════════════════════

def _demo():  # pragma: no cover — manual smoke test
    scanner = LogicProfileScanner()
    cases = [
        "هذا مجرد chatbot متقدم، مش أكثر من autocomplete",
        "أنت غلط وهذا لن ينجح، أثبت العكس",
        "أين الدليل على أن هذا يعمل؟ وش المنهجية؟",
        "ساعدني أفهم كيف يختلف هذا عن غيره",
        "أنا أعرف AI أكثر منك، أقدر أسوي أحسن",
        "it's just a fancy autocomplete, nothing but statistics",
        "where's the evidence? show me the data compared to baselines",
        "help me understand how this works, I'm curious",
    ]
    print("=" * 66)
    print("  AATIF Logic Profile Scanner — ماسح المنطق (FN#048)")
    print("=" * 66)
    for text in cases:
        r = scanner.scan(text)
        print(f"\n📝 «{text}»")
        sec = r.secondary_profile.value if r.secondary_profile else "—"
        print(f"   primary: {r.primary_profile.value}  secondary: {sec}  "
              f"mix={r.profile_mix}")
        for reading in r.as_list():
            if reading.detected:
                print(f"   • {reading.profile.value:16s} "
                      f"({reading.confidence:.2f}) signals={reading.signals}")
        print(f"   → {r.recommended_tone.splitlines()[0]}")


if __name__ == "__main__":
    _demo()
