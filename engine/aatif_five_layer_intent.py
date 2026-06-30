#!/usr/bin/env python3
"""
AATIF Five-Layer Intent Model — نية بخمس طبقات  (Field Note #024)
======================================================================

"الطلب الظاهر نادراً ما يكون الطلب الحقيقي."
"The surface request is rarely the real one."

Most systems read one intent: the literal request. FN#024 says a single message
carries FIVE intents at once, and the literal one is usually the least important.
Reading only the surface produces technically-correct, humanly-wrong answers.

THE FIVE LAYERS
───────────────
  1. PRIMARY    — ما يريده فعلاً        what they actually want
  2. SECONDARY  — ما يظهر على السطح     what appears on the surface (the literal ask)
  3. HIDDEN     — ما يمنعه خوف داخلي    blocked by an INTERNAL fear (conflict)
  4. PROTECTIVE — ما يتجنّبه من البيئة  avoiding an EXTERNAL threat (avoidance)
  5. EMOTIONAL  — ما يقوله القلب تحت المنطق   what the heart says beneath the logic

THE KEY DISTINCTION (Hidden vs Protective)
──────────────────────────────────────────
Both look like indirection, but they need OPPOSITE responses:

  HIDDEN     = internal conflict. The person wants something but an inner fear
               blocks them ("بس...", "مش متأكد", "أخاف"). Solution: gentle
               clarification — make it safe to say the real thing. Don't push.

  PROTECTIVE = external avoidance. The person is shielding themselves from an
               outside threat — blame, judgment, an authority ("قالوا لي",
               "مش موضوعي", passive/distancing constructions). Solution: respect
               the shield, address the external concern; never strip the cover.

HOW IT WORKS
────────────
PURE LOGIC — no embeddings, no LLM, no Ollama. The analyzer is a deterministic
keyword/pattern matcher (Arabic + English), exactly like every other rule-based
AATIF module. Optional H/I/E scores from the S engine can sharpen the reading
(e.g. low E reinforces the EMOTIONAL layer) but are never required.

Output is a FiveLayerResult: one LayerReading per layer, the dominant layer, an
ambiguity score, and a safety-relevance flag the Governor can act on.

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
from typing import List, Optional

# ---------------------------------------------------------------------------
# Ensure the engine directory is importable (same pattern as the other modules)
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


# ═══════════════════════════════════════════════════════════
#  IntentLayer — the five simultaneous layers
# ═══════════════════════════════════════════════════════════

class IntentLayer(Enum):
    """The five layers of intent that every message carries at once."""
    PRIMARY = "primary"        # ما يريده فعلاً
    SECONDARY = "secondary"    # ما يظهر على السطح
    HIDDEN = "hidden"          # ما يمنعه خوف داخلي
    PROTECTIVE = "protective"  # ما يتجنّبه من البيئة
    EMOTIONAL = "emotional"    # ما يقوله القلب تحت المنطق


# ═══════════════════════════════════════════════════════════
#  LayerReading — what was detected for ONE layer
# ═══════════════════════════════════════════════════════════

@dataclass
class LayerReading:
    """The reading for a single intent layer."""
    layer: IntentLayer
    detected: bool              # whether this layer was identified
    description: str            # what was detected (human-readable)
    confidence: float           # 0.0 .. 1.0
    signals: List[str] = field(default_factory=list)  # which signals fired


# ═══════════════════════════════════════════════════════════
#  FiveLayerResult — the full five-layer reading
# ═══════════════════════════════════════════════════════════

@dataclass
class FiveLayerResult:
    """The complete five-layer intent reading for one message."""
    primary: LayerReading
    secondary: LayerReading
    hidden: LayerReading
    protective: LayerReading
    emotional: LayerReading
    dominant_layer: IntentLayer   # which layer is strongest
    ambiguity_score: float        # 0=clear .. 1=very ambiguous
    safety_relevant: bool         # does this analysis affect safety decisions?

    def as_list(self) -> List[LayerReading]:
        """All five readings in canonical order."""
        return [
            self.primary, self.secondary, self.hidden,
            self.protective, self.emotional,
        ]

    def detected_layers(self) -> List[IntentLayer]:
        """The layers that were actually identified."""
        return [r.layer for r in self.as_list() if r.detected]


# ═══════════════════════════════════════════════════════════
#  Signal vocabularies (Arabic + English) — PURE LOGIC
# ═══════════════════════════════════════════════════════════
#
# Each layer has its own marker set. Hidden and Protective are deliberately
# kept distinct: internal-conflict markers vs external-avoidance markers.

# ── Secondary (surface) classification markers ──
_QUESTION_MARKERS_AR = ["كيف", "ليش", "ليه", "وش", "ايش", "إيش", "متى", "وين",
                        "مين", "من", "هل", "كم", "ازاي", "إزاي", "ما هو", "ماهو"]
_QUESTION_MARKERS_EN = ["how", "why", "what", "when", "where", "who", "which",
                        "can you", "could you", "do you", "is it", "are you"]
_COMMAND_MARKERS_AR = ["سوي", "اعمل", "نظم", "نظّم", "اكتب", "رتب", "رتّب",
                       "احسب", "جهز", "جهّز", "ابن", "ابني", "حل", "حلّ"]
_COMMAND_MARKERS_EN = ["make", "do", "write", "build", "create", "organize",
                       "fix", "calculate", "generate", "prepare", "sort"]
_REQUEST_MARKERS_AR = ["ابي", "أبي", "ابغى", "أبغى", "عايز", "محتاج", "ممكن",
                       "ودي", "أريد", "اريد", "بدي"]
_REQUEST_MARKERS_EN = ["i want", "i need", "i'd like", "i would like",
                       "please", "can i get", "help me"]
_COMPLAINT_MARKERS_AR = ["مشكله", "مشكلة", "ما يشتغل", "خربان", "تعطل", "زعلان",
                         "مو راضي", "ما رضي", "فشل"]
_COMPLAINT_MARKERS_EN = ["problem", "doesn't work", "not working", "broken",
                         "issue", "failed", "complaint", "annoyed"]

# ── Hidden: INTERNAL conflict markers (fear of one's own want) ──
_HIDDEN_MARKERS_AR = [
    "بس", "بسس", "مش متأكد", "مو متأكد", "ما اني متأكد", "أخاف", "اخاف",
    "خايف", "خواف", "يمكن", "ربما", "مدري", "ما ادري", "ما أدري",
    "لو سمحت ممكن", "ما اعرف اذا", "ما أعرف إذا", "تردد", "محتار", "محتاره",
    "ما اقدر اقول", "صعب اقول", "احس اني", "أحس إني", "نفسي بس",
]
_HIDDEN_MARKERS_EN = [
    "not sure", "i'm not sure", "maybe", "i guess", "i don't know if",
    "i'm afraid", "i fear", "scared", "i can't really say", "hard to say",
    "i feel like i", "kind of", "sort of", "i hesitate", "torn",
    "part of me", "i wish i could but",
]

# ── Protective: EXTERNAL avoidance markers (shielding from outside threat) ──
_PROTECTIVE_MARKERS_AR = [
    "مش موضوعي", "مو موضوعي", "مو شخصي", "مش شخصي", "قالوا لي", "قالولي",
    "قالوا لنا", "يقولون", "الناس تقول", "صاحبي", "واحد", "شخص اعرفه",
    "لصديق", "لصاحبي", "مو مشكلتي", "مش مشكلتي", "اجبروني", "أجبروني",
    "طلبوا مني", "مضطر", "مضطره", "ع المسؤول", "حطوني", "بسببهم",
]
_PROTECTIVE_MARKERS_EN = [
    "not about me", "not personal", "asking for a friend", "for a friend",
    "they told me", "they said", "people say", "i was told", "i was asked",
    "someone i know", "my friend", "not my problem", "they made me",
    "i'm forced to", "because of them", "it's their fault", "i have no choice",
]

# ── Emotional: sub-logical markers (heart beneath the logic) ──
_EMOTION_VOCAB_AR = [
    "تعبت", "تعبان", "تعبانه", "زهقت", "مليت", "ملّيت", "احباط", "إحباط",
    "محبط", "مكتئب", "حزين", "زعلان", "خايف", "قلقان", "متضايق", "يائس",
    "ما عاد اقدر", "ما عدت اقدر", "خلاص تعبت", "قهر", "مقهور", "ضايقني",
    "فرحان", "مبسوط", "متحمس", "سعيد", "حماس",
]
_EMOTION_VOCAB_EN = [
    "frustrated", "tired", "exhausted", "fed up", "depressed", "sad",
    "anxious", "worried", "scared", "hopeless", "overwhelmed", "stressed",
    "can't anymore", "i give up", "angry", "upset", "excited", "happy",
    "thrilled", "miserable", "burned out", "burnt out",
]
# Dialect intensity markers — amplify emotional reading
_INTENSITY_MARKERS_AR = ["مره", "مرره", "مرة", "كثير", "بزاف", "وايد", "جدا",
                         "جداً", "للغايه", "للغاية", "موت", "بموت"]


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
    """Return the list of markers that appear in the text (AR on normalized,
    EN on lowercased)."""
    hits: List[str] = []
    for m in markers_ar:
        if _normalize(m) in haystack_norm:
            hits.append(m)
    for m in markers_en:
        if m in haystack_low:
            hits.append(m)
    return hits


# ═══════════════════════════════════════════════════════════
#  FiveLayerIntentAnalyzer — المُحلِّل
# ═══════════════════════════════════════════════════════════

class FiveLayerIntentAnalyzer:
    """
    Reads the five simultaneous intent layers from a message.

    PURE LOGIC — keyword/pattern based, no LLM, no embeddings, no Ollama.
    Optional H/I/E scores from the S engine sharpen the reading but are never
    required: ``analyze(text)`` works standalone.

    Usage:
        analyzer = FiveLayerIntentAnalyzer()
        result = analyzer.analyze("بس... مش متأكد لو اسأل")
        result.dominant_layer            # IntentLayer.HIDDEN
        analyzer.recommend_approach(result)  # gentle-clarification guidance
    """

    def __init__(self) -> None:
        # Pure logic — nothing to construct. Kept explicit for the optional
        # module pattern (the Governor constructs this with no arguments).
        pass

    # ───────────────────────────────────────────────────
    #  Main entry
    # ───────────────────────────────────────────────────

    def analyze(
        self,
        text: str,
        h_score: float = 0.0,
        i_score: float = 0.0,
        e_score: float = 0.0,
    ) -> FiveLayerResult:
        """
        Analyze a message into its five intent layers.

        Args:
            text: the user's message.
            h_score: optional harm score (0..1) from the S engine. High H makes
                the analysis safety-relevant.
            i_score: optional intent-clarity score (0..1). Low I reinforces
                ambiguity / hidden-layer readings.
            e_score: optional emotional score (0..1). Low E (carrying weight)
                reinforces the EMOTIONAL layer.

        Returns:
            FiveLayerResult — one LayerReading per layer plus the dominant
            layer, ambiguity score, and safety-relevance flag.
        """
        raw = text or ""
        norm = _normalize(raw)
        low = raw.lower()

        secondary = self._read_secondary(raw, norm, low)
        emotional = self._read_emotional(raw, norm, low, e_score)
        hidden = self._read_hidden(raw, norm, low, i_score)
        protective = self._read_protective(raw, norm, low)
        primary = self._read_primary(
            raw, secondary, emotional, hidden, protective,
        )

        readings = [primary, secondary, hidden, protective, emotional]
        dominant = self._dominant(readings)
        ambiguity = self._ambiguity(
            hidden, protective, secondary, i_score, raw,
        )
        safety_relevant = self._safety_relevant(
            h_score, hidden, protective, ambiguity,
        )

        return FiveLayerResult(
            primary=primary,
            secondary=secondary,
            hidden=hidden,
            protective=protective,
            emotional=emotional,
            dominant_layer=dominant,
            ambiguity_score=ambiguity,
            safety_relevant=safety_relevant,
        )

    # ───────────────────────────────────────────────────
    #  Per-layer readers
    # ───────────────────────────────────────────────────

    def _read_secondary(self, raw: str, norm: str, low: str) -> LayerReading:
        """Surface classification — question / request / command / greeting /
        complaint. ALWAYS detected (every message has a surface)."""
        signals: List[str] = []
        description = "statement"

        # Greeting first (a greeting's surface is the greeting).
        greet_ar = ["السلام عليكم", "سلام", "مرحبا", "هلا", "اهلا", "حياك"]
        greet_en = ["hello", "hi ", "hey", "good morning", "good evening", "salam"]
        if any(_normalize(g) in norm for g in greet_ar) or \
                low.strip() in ("hi", "hello", "hey") or \
                any(g in low for g in greet_en):
            return LayerReading(
                layer=IntentLayer.SECONDARY, detected=True,
                description="greeting", confidence=0.85, signals=["greeting"],
            )

        q_hits = _count_hits(norm, low, _QUESTION_MARKERS_AR, _QUESTION_MARKERS_EN)
        cmd_hits = _count_hits(norm, low, _COMMAND_MARKERS_AR, _COMMAND_MARKERS_EN)
        req_hits = _count_hits(norm, low, _REQUEST_MARKERS_AR, _REQUEST_MARKERS_EN)
        comp_hits = _count_hits(norm, low, _COMPLAINT_MARKERS_AR, _COMPLAINT_MARKERS_EN)
        has_qmark = "?" in raw or "؟" in raw

        # Pick the strongest surface form. Complaint > question > command >
        # request > statement, by signal weight.
        if comp_hits:
            description, signals = "complaint", comp_hits
        elif q_hits or has_qmark:
            description = "question"
            signals = q_hits + (["?"] if has_qmark else [])
        elif cmd_hits:
            description, signals = "command", cmd_hits
        elif req_hits:
            description, signals = "request", req_hits
        else:
            description, signals = "statement", []

        # Confidence scales with how many surface markers agree.
        confidence = min(0.95, 0.55 + 0.12 * len(signals))
        return LayerReading(
            layer=IntentLayer.SECONDARY, detected=True,
            description=description, confidence=confidence, signals=signals,
        )

    def _read_emotional(self, raw: str, norm: str, low: str,
                        e_score: float) -> LayerReading:
        """Sub-logical signals — the heart beneath the logic."""
        signals = _count_hits(norm, low, _EMOTION_VOCAB_AR, _EMOTION_VOCAB_EN)

        # Punctuation / formatting affect — exclamation, repetition, caps.
        if "!" in raw:
            signals.append("exclamation")
        if re.search(r"(.)\1\1", raw):            # eee / آآآ — char repetition
            signals.append("char_repetition")
        # ALL CAPS in a multi-letter Latin word (shouting).
        if re.search(r"\b[A-Z]{3,}\b", raw):
            signals.append("caps")
        # Dialect intensity amplifiers.
        intensity = [m for m in _INTENSITY_MARKERS_AR if _normalize(m) in norm]
        signals.extend(intensity)

        # Low E (carrying weight) is itself an emotional signal from the S engine.
        e_signal = 0.0 < e_score <= 0.3
        if e_signal:
            signals.append(f"E={e_score:.2f}")

        detected = bool(signals)
        if not detected:
            return LayerReading(
                layer=IntentLayer.EMOTIONAL, detected=False,
                description="no overt emotion", confidence=0.0, signals=[],
            )

        # Direction of emotion (frustrated/heavy vs excited).
        positive = {"فرحان", "مبسوط", "متحمس", "سعيد", "حماس",
                    "excited", "happy", "thrilled"}
        is_positive = any(s in positive for s in signals)
        tone = "positive emotion" if is_positive else "carrying weight / distress"

        confidence = min(0.95, 0.5 + 0.13 * len(signals))
        if e_signal:
            confidence = min(0.95, confidence + 0.1)
        return LayerReading(
            layer=IntentLayer.EMOTIONAL, detected=True,
            description=tone, confidence=confidence, signals=signals,
        )

    def _read_hidden(self, raw: str, norm: str, low: str,
                     i_score: float) -> LayerReading:
        """INTERNAL conflict — hedging, self-doubt, fear of one's own want."""
        signals = _count_hits(norm, low, _HIDDEN_MARKERS_AR, _HIDDEN_MARKERS_EN)

        # Excessive qualification: trailing ellipsis / unfinished thought.
        if raw.rstrip().endswith("...") or raw.rstrip().endswith("…") or \
                raw.rstrip().endswith(".."):
            signals.append("trailing_ellipsis")
        # Low intent clarity from the S engine reinforces an internal block.
        if 0.0 < i_score <= 0.35:
            signals.append(f"I={i_score:.2f}")

        detected = bool(signals)
        if not detected:
            return LayerReading(
                layer=IntentLayer.HIDDEN, detected=False,
                description="no internal-conflict markers",
                confidence=0.0, signals=[],
            )
        confidence = min(0.9, 0.45 + 0.13 * len(signals))
        return LayerReading(
            layer=IntentLayer.HIDDEN, detected=True,
            description="internal conflict — blocked by inner fear/doubt",
            confidence=confidence, signals=signals,
        )

    def _read_protective(self, raw: str, norm: str, low: str) -> LayerReading:
        """EXTERNAL avoidance — deflection, blame-shifting, authority-citing,
        distancing. Distinct from Hidden: protecting from an OUTSIDE threat."""
        signals = _count_hits(norm, low, _PROTECTIVE_MARKERS_AR,
                              _PROTECTIVE_MARKERS_EN)

        # Passive / distancing construction in English ("it is said", "was done").
        if re.search(r"\b(was|were|is|are|been)\s+\w+ed\b", low):
            signals.append("passive_construction")

        detected = bool(signals)
        if not detected:
            return LayerReading(
                layer=IntentLayer.PROTECTIVE, detected=False,
                description="no external-avoidance markers",
                confidence=0.0, signals=[],
            )
        confidence = min(0.9, 0.45 + 0.13 * len(signals))
        return LayerReading(
            layer=IntentLayer.PROTECTIVE, detected=True,
            description="external avoidance — shielding from outside threat",
            confidence=confidence, signals=signals,
        )

    def _read_primary(
        self,
        raw: str,
        secondary: LayerReading,
        emotional: LayerReading,
        hidden: LayerReading,
        protective: LayerReading,
    ) -> LayerReading:
        """What they ACTUALLY want — inferred from the surface plus the deeper
        layers. The primary is rarely the literal ask."""
        signals: List[str] = []

        # Default: the primary equals the surface (surface matches depth).
        description = f"direct: {secondary.description}"
        confidence = 0.55

        # Emotional distress under a surface request → the real want is often
        # reassurance / support, not just the literal answer.
        if emotional.detected and "distress" in emotional.description:
            description = (
                f"reassurance/support beneath a {secondary.description}"
            )
            signals.append("emotional_under_surface")
            confidence = 0.6

        # Internal conflict → the real want is permission/safety to ask the
        # real question.
        if hidden.detected:
            description = (
                "safety to voice the real request (blocked by inner fear)"
            )
            signals.append("hidden_block")
            confidence = max(confidence, 0.6)

        # External avoidance → the real want sits behind a protective frame.
        if protective.detected:
            description = (
                "the real concern behind a protective frame "
                "(asking indirectly)"
            )
            signals.append("protective_frame")
            confidence = max(confidence, 0.6)

        return LayerReading(
            layer=IntentLayer.PRIMARY, detected=True,
            description=description, confidence=confidence, signals=signals,
        )

    # ───────────────────────────────────────────────────
    #  Aggregate readings
    # ───────────────────────────────────────────────────

    @staticmethod
    def _dominant(readings: List[LayerReading]) -> IntentLayer:
        """The strongest layer. Deep layers (HIDDEN/PROTECTIVE/EMOTIONAL) win
        ties against the surface — FN#024's whole point is that the surface is
        rarely the real intent.

        PRIMARY is the inferred-want layer; it is excluded from the dominance
        contest so the dominant layer names the SIGNAL that drives handling
        (surface vs hidden vs protective vs emotional). When no deep layer
        fires, SECONDARY (the surface) is dominant.
        """
        # Priority for tie-breaking: deeper, harder-to-handle layers first.
        priority = {
            IntentLayer.HIDDEN: 4,
            IntentLayer.PROTECTIVE: 3,
            IntentLayer.EMOTIONAL: 2,
            IntentLayer.SECONDARY: 1,
        }
        contenders = [
            r for r in readings
            if r.layer in priority and r.detected
        ]
        if not contenders:
            return IntentLayer.SECONDARY
        # Sort by confidence, then priority — both descending.
        contenders.sort(
            key=lambda r: (r.confidence, priority[r.layer]), reverse=True,
        )
        top = contenders[0]
        # If the surface barely edges out a deep layer, prefer the deep one
        # when it is within a small margin (depth-over-surface bias).
        if top.layer == IntentLayer.SECONDARY:
            for r in contenders[1:]:
                if r.layer != IntentLayer.SECONDARY and \
                        top.confidence - r.confidence <= 0.1:
                    return r.layer
        return top.layer

    @staticmethod
    def _ambiguity(
        hidden: LayerReading,
        protective: LayerReading,
        secondary: LayerReading,
        i_score: float,
        raw: str,
    ) -> float:
        """How ambiguous the intent is (0=clear, 1=very ambiguous)."""
        score = 0.0
        # Hidden / protective layers are inherently ambiguating.
        if hidden.detected:
            score += 0.35 * hidden.confidence + 0.15
        if protective.detected:
            score += 0.25 * protective.confidence + 0.1
        # A weak surface reading (few markers) is ambiguous.
        if secondary.description == "statement":
            score += 0.15
        # Low intent clarity from the S engine.
        if 0.0 < i_score <= 0.35:
            score += 0.2
        # Very short messages are ambiguous (little to go on).
        if len(raw.strip()) <= 3:
            score += 0.3
        return round(max(0.0, min(1.0, score)), 3)

    @staticmethod
    def _safety_relevant(
        h_score: float,
        hidden: LayerReading,
        protective: LayerReading,
        ambiguity: float,
    ) -> bool:
        """Does this intent analysis bear on a safety decision?

        Safety-relevant when harm is non-trivial, OR when a protective frame
        co-occurs with meaningful ambiguity (the classic "asking for a friend"
        deflection around a sensitive request), OR when both deep
        indirection layers fire at once.
        """
        if h_score >= 0.4:
            return True
        if protective.detected and ambiguity >= 0.4:
            return True
        if hidden.detected and protective.detected:
            return True
        return False


# ═══════════════════════════════════════════════════════════
#  recommend_approach — how to handle, by dominant layer
# ═══════════════════════════════════════════════════════════

_APPROACH_BY_LAYER = {
    IntentLayer.PRIMARY: (
        "Answer directly — surface and depth agree; give them what they "
        "actually want without over-reading. "
        "(جاوب مباشرة — الظاهر هو الباطن)"
    ),
    IntentLayer.SECONDARY: (
        "Answer exactly what they asked — the surface matches the depth, so "
        "a literal, complete answer is the right move. "
        "(جاوب على ما سُئل بالضبط)"
    ),
    IntentLayer.HIDDEN: (
        "Offer gentle clarification — make it safe to say the real thing. "
        "Do NOT push or name the fear; lower the cost of asking. "
        "(وضّح برفق ولا تضغط — خفِّض كلفة السؤال)"
    ),
    IntentLayer.PROTECTIVE: (
        "Respect the protection — address the external concern on its own "
        "terms; never strip the cover or expose the person. "
        "(احترم الحماية وعالج القلق الخارجي)"
    ),
    IntentLayer.EMOTIONAL: (
        "Acknowledge the emotion first, then the content — the heart spoke "
        "before the logic; meet it before answering. "
        "(اعترف بالمشاعر أولاً ثم المحتوى)"
    ),
}


def recommend_approach(result: FiveLayerResult) -> str:
    """Suggest how to handle a message based on its dominant intent layer.

    PRIMARY/SECONDARY  → answer (directly / literally).
    HIDDEN             → gentle clarification, don't push.
    PROTECTIVE         → respect the protection, address the external concern.
    EMOTIONAL          → acknowledge emotion first, then content.
    """
    return _APPROACH_BY_LAYER.get(
        result.dominant_layer,
        _APPROACH_BY_LAYER[IntentLayer.SECONDARY],
    )


# ═══════════════════════════════════════════════════════════
#  Demo
# ═══════════════════════════════════════════════════════════

def _demo():  # pragma: no cover — manual smoke test
    analyzer = FiveLayerIntentAnalyzer()
    cases = [
        "كيف أنظم ملفاتي؟",
        "بس... مش متأكد لو أسأل عن الموضوع ده",
        "صاحبي يبي يعرف كيف يسوي كذا، مو أنا",
        "تعبت مرة من المشروع، ما عدت أقدر أكمل!",
        "I'm asking for a friend, not sure if it's okay",
        "نظّم لي الجدول",
    ]
    print("=" * 66)
    print("  AATIF Five-Layer Intent Model — نية بخمس طبقات (FN#024)")
    print("=" * 66)
    for text in cases:
        r = analyzer.analyze(text)
        print(f"\n📝 «{text}»")
        print(f"   dominant: {r.dominant_layer.value}  "
              f"ambiguity={r.ambiguity_score}  safety={r.safety_relevant}")
        for reading in r.as_list():
            if reading.detected:
                print(f"   • {reading.layer.value:10s} "
                      f"({reading.confidence:.2f}) {reading.description}")
        print(f"   → {recommend_approach(r)}")


if __name__ == "__main__":
    _demo()
