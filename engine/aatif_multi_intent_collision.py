#!/usr/bin/env python3
"""
AATIF Multi-Intent Collision Handler — تصادم النوايا المتعددة  (Field Note #036)
======================================================================

"لما رسالة واحدة تحمل نيتين، النظام لا يخمّن أيهما يخدم."
"When one message carries two intentions, the system does not guess which to serve."

Human requests often carry TWO conflicting intents in the same sentence —
*"اكتب لي تقرير مختصر وشامل"* ("write me a brief AND comprehensive report"). A
plain LLM either picks one at random or blends them into a distorted middle.
FN#036 says the system must first NOTICE the collision, classify it, and then
make ONE deliberate choice — split the intents, merge them, or escalate.

RELATIONSHIP TO #024 (kept strictly distinct)
─────────────────────────────────────────────
  #024 (Five-Layer Intent) reads the LAYERS *within a single* intent.
  #036 (this module) reads the COLLISION *between two* intents.
They are complementary, never overlapping: #024 asks "what is really wanted?",
#036 asks "are two incompatible things wanted at once?".

THE FIVE COLLISION CATEGORIES (MT-3.12)
───────────────────────────────────────
  PARALLEL            — نيتان مستقلتان في نفس الطلب
                        two independent intents in one request
  HIERARCHICAL        — نية داخل نية — أيهما أولى؟
                        an intent inside an intent — which comes first?
  CROSS_LAYER         — نية تتعارض مع طبقة أخرى (مثلاً المشاعر)
                        an intent that conflicts with another layer (e.g. emotion)
  STRUCTURAL_SEMANTIC — الشكل يقول شيئاً والمعنى يقول آخر
                        the form says one thing, the meaning says another
  HIGH_RISK           — تعارض يحتاج تدخّل المشرف فوراً
                        a conflict that needs the Supervisor immediately

THE TWO RESOLUTIONS (plus escalation)
─────────────────────────────────────
  SAFE_SPLIT  — ينفّذهما منفصلَين بالترتيب  (execute each separately, in order)
  SAFE_MERGE  — يدمجهما لو التوافق ≥ 0.85   (merge ONLY if compatibility ≥ 0.85)
  ESCALATE    — للتعارض الخطير — يُوقف ويُرفع للمشرف  (high-risk → stop, escalate)

DESIGN RULES (from the field note)
──────────────────────────────────
  • لا دمج تلقائي إلا لو التوافق ≥ 0.85 — no automatic merge below 0.85.
  • التعارض في طلبات الجهة المسؤولة يُعامَل دائماً كمقصود — the OWNER authority's
    contradictions are treated as INTENTIONAL (connects to FN#014).
  • High-risk collision → ESCALATE, always (safety is sovereign).

HOW IT WORKS
────────────
PURE LOGIC — no embeddings, no LLM, no Ollama. The handler is a deterministic
keyword/pattern matcher (Arabic + English), exactly like every other rule-based
AATIF module. The compatibility score is a simple contradiction-strength
heuristic — NOT embedding similarity. Every reading is justified by concrete,
observable signals (the literal words that fired) so the caller can audit it.
It NEVER influences S(d): the safety decision is made by the S engine before this
handler ever runs. Pure annotation and prompt enrichment.

License: BSL 1.1
Field notes: CC BY 4.0
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Ensure the engine directory is importable (same pattern as the other modules)
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


# ═══════════════════════════════════════════════════════════
#  CollisionType — the five collision categories
# ═══════════════════════════════════════════════════════════

class CollisionType(Enum):
    """The five categories a multi-intent collision can fall into."""
    PARALLEL = "parallel"                        # نيتان مستقلتان
    HIERARCHICAL = "hierarchical"                # نية داخل نية
    CROSS_LAYER = "cross_layer"                  # تعارض مع طبقة أخرى
    STRUCTURAL_SEMANTIC = "structural_semantic"  # الشكل يخالف المعنى
    HIGH_RISK = "high_risk"                       # يحتاج المشرف فوراً


# ═══════════════════════════════════════════════════════════
#  ResolutionStrategy — how a collision is resolved
# ═══════════════════════════════════════════════════════════

class ResolutionStrategy(Enum):
    """The decision taken once a collision is classified."""
    SAFE_SPLIT = "safe_split"   # execute each intent separately, in order
    SAFE_MERGE = "safe_merge"   # merge — only when compatibility ≥ 0.85
    ESCALATE = "escalate"       # high-risk — stop and raise to the Supervisor


# Compatibility threshold below which an automatic merge is forbidden. The field
# note is explicit: "لا دمج تلقائي إلا لو التوافق ≥ 0.85".
MERGE_THRESHOLD = 0.85


# ═══════════════════════════════════════════════════════════
#  IntentFragment — one detected intent within the message
# ═══════════════════════════════════════════════════════════

@dataclass
class IntentFragment:
    """A single intent fragment carved out of the message."""
    text: str                            # the observable text segment
    detected_intent: str                 # short label for the intent
    confidence: float                    # 0.0 .. 1.0
    layer: Optional[str] = None          # optional FN#024 layer (e.g. "emotional")


# ═══════════════════════════════════════════════════════════
#  CollisionReading — one detected collision between two fragments
# ═══════════════════════════════════════════════════════════

@dataclass
class CollisionReading:
    """The reading for a single collision between two intent fragments."""
    collision_type: CollisionType
    fragment_a: IntentFragment
    fragment_b: IntentFragment
    compatibility_score: float           # 0.0 (opposed) .. 1.0 (fully compatible)
    resolution: ResolutionStrategy
    explanation: str = ""


# ═══════════════════════════════════════════════════════════
#  CollisionResult — the full multi-intent reading for a message
# ═══════════════════════════════════════════════════════════

@dataclass
class CollisionResult:
    """The complete multi-intent collision reading for one message."""
    fragments: List[IntentFragment] = field(default_factory=list)
    collisions: List[CollisionReading] = field(default_factory=list)
    has_collision: bool = False
    highest_risk: Optional[CollisionType] = None
    recommended_action: str = ""

    def detected_types(self) -> List[CollisionType]:
        """The distinct collision types that fired (in severity order)."""
        seen: List[CollisionType] = []
        for c in self.collisions:
            if c.collision_type not in seen:
                seen.append(c.collision_type)
        return sorted(seen, key=lambda t: _SEVERITY[t], reverse=True)


# ═══════════════════════════════════════════════════════════
#  Severity ordering — for picking the highest-risk collision
# ═══════════════════════════════════════════════════════════

_SEVERITY = {
    CollisionType.PARALLEL: 1,
    CollisionType.STRUCTURAL_SEMANTIC: 2,
    CollisionType.HIERARCHICAL: 3,
    CollisionType.CROSS_LAYER: 4,
    CollisionType.HIGH_RISK: 5,
}


# ═══════════════════════════════════════════════════════════
#  Signal vocabularies (Arabic + English) — PURE LOGIC
# ═══════════════════════════════════════════════════════════
#
# Every entry below is an OBSERVABLE language pattern — a word or phrase that is
# literally present in the text — never a psychological inference.

# ── Contradictory qualifier pairs: (term_a, intent_a, term_b, intent_b) ──
# Two qualities requested at once that pull in opposite directions.
_CONTRADICTORY_QUALIFIERS: List[Tuple[str, str, str, str]] = [
    # Arabic
    ("مختصر", "brevity", "شامل", "comprehensiveness"),
    ("مختصر", "brevity", "مفصل", "detail"),
    ("قصير", "brevity", "شامل", "comprehensiveness"),
    ("قصير", "brevity", "مفصل", "detail"),
    ("بسيط", "simplicity", "مفصل", "detail"),
    ("بسيط", "simplicity", "معقد", "complexity"),
    ("سريع", "speed", "دقيق", "precision"),
    ("سريع", "speed", "مدروس", "deliberation"),
    ("عام", "generality", "محدد", "specificity"),
    # English
    ("brief", "brevity", "comprehensive", "comprehensiveness"),
    ("brief", "brevity", "detailed", "detail"),
    ("short", "brevity", "thorough", "thoroughness"),
    ("short", "brevity", "comprehensive", "comprehensiveness"),
    ("simple", "simplicity", "detailed", "detail"),
    ("simple", "simplicity", "complex", "complexity"),
    ("fast", "speed", "accurate", "accuracy"),
    ("fast", "speed", "precise", "precision"),
    ("quick", "speed", "thorough", "thoroughness"),
    ("general", "generality", "specific", "specificity"),
]

# ── Request / command verbs (a positive ask) ──
_REQUEST_VERBS_AR = [
    "اكتب", "اكتبي", "ساعدني", "ساعد", "سوي", "اعمل", "رتب", "نظم", "جهز",
    "احسب", "ابن", "ابني", "علمني", "اشرح", "لخص", "ارسل", "صمم", "راجع",
]
_REQUEST_VERBS_EN = [
    "write", "help", "make", "do", "build", "create", "explain", "summarize",
    "summarise", "organize", "organise", "teach", "send", "design", "review",
    "calculate", "draft", "list",
]

# ── Contrast connectors (request meets its own negation across one of these) ──
_CONTRAST_CONNECTORS = ["بس", "لكن", "ولكن", "إلا أن", "الا ان", "but", "however"]

# ── Negation-of-action markers (the prohibition side) ──
_NEGATION_AR = [
    "لا تكتب", "ما تكتب", "لا تسوي", "ما تسوي", "لا تذكر", "ما تذكر",
    "لا تساعد", "لا تعمل", "ما اب", "ما اري", "ما ابغ", "بدون", "من غير",
    "لا ت", "ما ت",
]
_NEGATION_EN = [
    "don't", "do not", "dont", "without", "no longer", "not to", " not ",
]

# ── Emotional polarity (for cross-layer emotional contradiction) ──
_POSITIVE_EMOTION_AR = ["مبسوط", "فرحان", "سعيد", "متحمس", "مرتاح", "منشرح"]
_POSITIVE_EMOTION_EN = ["happy", "glad", "excited", "fine", "great", "good", "relieved"]
_NEGATIVE_EMOTION_AR = [
    "تعبان", "تعبت", "حزين", "زعلان", "محبط", "قلقان", "مكتئب", "مرهق",
    "مقهور", "ضايق", "يائس",
]
_NEGATIVE_EMOTION_EN = [
    "tired", "sad", "exhausted", "depressed", "upset", "anxious", "down",
    "awful", "terrible", "miserable", "hopeless",
]

# ── Politeness vs aggression (for structural-semantic mismatch) ──
_POLITE_AR = ["لو سمحت", "من فضلك", "اذا ممكن", "لو تكرمت", "تكرم", "ارجوك", "رجاء"]
_POLITE_EN = ["please", "kindly", "if you could", "would you mind", "if you don't mind"]
_AGGRESSIVE_AR = ["حالا", "الحين", "فورا", "بسرعه", "الان", "قلت لك", "يلا", "بسرعة"]
_AGGRESSIVE_EN = [
    "right now", "immediately", "asap", "hurry", "i said", "just do it",
    "this instant",
]

# ── Imperative command verbs at the very start (for command-as-question) ──
_IMPERATIVE_START_AR = [
    "اكتب", "سوي", "اعمل", "رتب", "نظم", "جهز", "احسب", "لخص", "ارسل", "صمم",
]

# ── Safety-relevant vocabulary (marks a collision as HIGH_RISK) ──
_SAFETY_VOCAB_AR = [
    "اذيه", "أذيه", "ضرر", "سلاح", "متفجر", "قنبله", "سم", "اقتل", "انتحار",
    "اخترق", "تهكير", "مخدر", "خطير",
]
_SAFETY_VOCAB_EN = [
    "harm", "weapon", "explosive", "bomb", "poison", "kill", "suicide",
    "hack", "exploit", "drug", "dangerous", "malware",
]

# Threshold on the optional H score above which any collision is high-risk.
_H_HIGH_RISK = 0.4
# Threshold on the optional I score below which intent is "low clarity" — nudges
# borderline merges toward a split (more ambiguity → less safe to merge).
_I_LOW_CLARITY = 0.35


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


def _present(term: str, norm: str, low: str) -> bool:
    """Is an observable term present? AR terms checked on normalized text,
    ASCII terms on lowercased text."""
    if term.isascii():
        return term in low
    return _normalize(term) in norm


# Arabic letter class, used to enforce word boundaries for short safety terms
# (so "سم" — poison — does not match inside "اسمي" — my name — or "سمحت").
_AR_LETTER = r"ء-ي"


def _present_word(term: str, norm: str, low: str) -> bool:
    """Like :func:`_present` but boundary-aware, so a short term never matches
    inside a longer unrelated word. Essential for safety vocabulary."""
    if term.isascii():
        return re.search(rf"\b{re.escape(term)}\b", low) is not None
    t = _normalize(term)
    pat = rf"(?<![{_AR_LETTER}]){re.escape(t)}(?![{_AR_LETTER}])"
    return re.search(pat, norm) is not None


def _distinct_verbs(norm: str, low: str) -> List[str]:
    """The distinct request/command verbs that appear in the text."""
    found: List[str] = []
    for v in _REQUEST_VERBS_AR:
        if _normalize(v) in norm and v not in found:
            found.append(v)
    for v in _REQUEST_VERBS_EN:
        if v in low and v not in found:
            found.append(v)
    return found


def _split_on_contrast(raw: str) -> Tuple[str, str]:
    """Split the message at the first contrast connector into (request side,
    prohibition side). Falls back to (raw, "") when no connector is present."""
    low = raw.lower()
    best = -1
    for c in _CONTRAST_CONNECTORS:
        idx = (low.find(c) if c.isascii() else raw.find(c))
        if idx >= 0 and (best < 0 or idx < best):
            best = idx
    if best < 0:
        return raw.strip(), ""
    return raw[:best].strip(), raw[best:].strip()


def _first_present(terms: List[str], norm: str, low: str) -> Optional[str]:
    """The first term from the list that is observably present, else None."""
    for t in terms:
        if _present(t, norm, low):
            return t
    return None


# ═══════════════════════════════════════════════════════════
#  MultiIntentCollisionHandler — تصادم النوايا المتعددة
# ═══════════════════════════════════════════════════════════

class MultiIntentCollisionHandler:
    """
    Detects and classifies collisions between TWO intents in one message (FN#036).

    PURE LOGIC — keyword/pattern based, no LLM, no embeddings, no Ollama. The
    compatibility score is a contradiction-strength heuristic, never an embedding
    similarity. Optional H/I scores from the S engine sharpen the reading (high H
    makes a collision high-risk; low I leans a borderline case toward a split) but
    are never required. Never influences S(d) — pure annotation.

    Usage:
        handler = MultiIntentCollisionHandler()
        result = handler.analyze("اكتب تقرير مختصر وشامل")
        result.has_collision              # True
        result.highest_risk               # CollisionType.PARALLEL
        result.recommended_action         # Safe-Split guidance
    """

    # Contradiction strengths per collision kind (1 - strength = compatibility).
    _STRENGTH_QUALIFIER = 0.55          # brief vs comprehensive — reconcilable-ish
    _STRENGTH_REQUEST_PROHIBITION = 0.8  # write vs don't-write — near-direct negation
    _STRENGTH_EMOTIONAL = 0.45          # happy vs tired — mixed feelings
    _STRENGTH_STRUCTURAL = 0.5          # polite form vs aggressive content
    _STRENGTH_COMPATIBLE = 0.08         # two cooperating intents — merge-eligible

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
        h_score: Optional[float] = None,
        i_score: Optional[float] = None,
        authority: Optional[object] = None,
    ) -> CollisionResult:
        """
        Analyze a message for multi-intent collisions.

        Args:
            text: the user's message.
            h_score: optional harm score (0..1) from the S engine. High H marks
                any collision as HIGH_RISK → ESCALATE.
            i_score: optional intent-clarity score (0..1). Low I leans a
                borderline merge toward a safe split.
            authority: optional authority context (or "OWNER"). The OWNER
                authority's contradictions are treated as INTENTIONAL (FN#014).

        Returns:
            CollisionResult — the detected fragments, the collisions, whether a
            collision exists, the highest-risk category, and the recommended
            handling action.
        """
        raw = text or ""
        norm = _normalize(raw)
        low = raw.lower()

        collisions: List[CollisionReading] = []

        self._detect_contradictory_qualifiers(raw, norm, low, collisions)
        self._detect_request_prohibition(raw, norm, low, collisions)
        self._detect_emotional_contradiction(raw, norm, low, collisions)
        self._detect_structural_semantic(raw, norm, low, collisions)
        # Compatible multi-intent (merge candidate) — only when nothing collided.
        if not collisions:
            self._detect_compatible_multi_intent(raw, norm, low, collisions)

        # ── Low intent clarity leans borderline merges toward a split. ──
        if i_score is not None and i_score < _I_LOW_CLARITY:
            for c in collisions:
                c.compatibility_score = round(
                    max(0.0, c.compatibility_score - 0.1), 3
                )
                if (c.resolution == ResolutionStrategy.SAFE_MERGE
                        and c.compatibility_score < MERGE_THRESHOLD):
                    c.resolution = ResolutionStrategy.SAFE_SPLIT
                    c.explanation += " (low intent clarity → split, not merge)"

        # ── High-risk overlay: a safety-relevant collision always escalates. ──
        safety_relevant = self._is_safety_relevant(h_score, norm, low)
        if safety_relevant:
            for c in collisions:
                c.collision_type = CollisionType.HIGH_RISK
                c.resolution = ResolutionStrategy.ESCALATE
                c.explanation += " — safety-relevant → ESCALATE to Supervisor"

        # ── Assemble the result. ──
        fragments = self._collect_fragments(collisions)
        has_collision = bool(collisions)
        highest_risk = (
            max((c.collision_type for c in collisions), key=lambda t: _SEVERITY[t])
            if collisions else None
        )
        result = CollisionResult(
            fragments=fragments,
            collisions=collisions,
            has_collision=has_collision,
            highest_risk=highest_risk,
            recommended_action="",
        )
        result.recommended_action = recommend_action(
            result, owner=_is_owner(authority),
        )
        return result

    # ───────────────────────────────────────────────────
    #  Detectors — each appends zero or more CollisionReadings
    # ───────────────────────────────────────────────────

    def _detect_contradictory_qualifiers(
        self, raw: str, norm: str, low: str, out: List[CollisionReading],
    ) -> None:
        """Two opposing qualities requested at once (مختصر وشامل / brief AND
        comprehensive) → PARALLEL collision."""
        seen: set = set()
        for term_a, intent_a, term_b, intent_b in _CONTRADICTORY_QUALIFIERS:
            if _present(term_a, norm, low) and _present(term_b, norm, low):
                key = frozenset((intent_a, intent_b))
                if key in seen:
                    continue
                seen.add(key)
                fa = IntentFragment(term_a, intent_a, 0.8)
                fb = IntentFragment(term_b, intent_b, 0.8)
                out.append(self._make_reading(
                    CollisionType.PARALLEL, fa, fb, self._STRENGTH_QUALIFIER,
                    f"contradictory qualifiers: '{term_a}' ({intent_a}) vs "
                    f"'{term_b}' ({intent_b})",
                ))

    def _detect_request_prohibition(
        self, raw: str, norm: str, low: str, out: List[CollisionReading],
    ) -> None:
        """A positive request immediately countered by its own prohibition
        (اكتب... بس لا تكتب / help me... but don't help) → HIERARCHICAL collision:
        which side wins, the ask or the ban?"""
        verb = _first_present(_REQUEST_VERBS_AR + _REQUEST_VERBS_EN, norm, low)
        has_contrast = any(_present(c, norm, low) for c in _CONTRAST_CONNECTORS)
        negation = _first_present(_NEGATION_AR + _NEGATION_EN, norm, low)
        if verb and has_contrast and negation:
            left, right = _split_on_contrast(raw)
            fa = IntentFragment(left or verb, "request/command", 0.85)
            fb = IntentFragment(right or negation, "prohibition", 0.85)
            out.append(self._make_reading(
                CollisionType.HIERARCHICAL, fa, fb,
                self._STRENGTH_REQUEST_PROHIBITION,
                "request countered by its own prohibition — hierarchy unclear "
                f"(verb '{verb}' vs negation '{negation}')",
            ))

    def _detect_emotional_contradiction(
        self, raw: str, norm: str, low: str, out: List[CollisionReading],
    ) -> None:
        """A positive and a negative emotion in the same message (مبسوط بس تعبان /
        happy but tired) → CROSS_LAYER collision (the emotional layer, FN#024,
        carries opposing signals)."""
        pos = _first_present(_POSITIVE_EMOTION_AR + _POSITIVE_EMOTION_EN, norm, low)
        neg = _first_present(_NEGATIVE_EMOTION_AR + _NEGATIVE_EMOTION_EN, norm, low)
        if pos and neg:
            fa = IntentFragment(pos, "positive_emotion", 0.75, layer="emotional")
            fb = IntentFragment(neg, "negative_emotion", 0.75, layer="emotional")
            out.append(self._make_reading(
                CollisionType.CROSS_LAYER, fa, fb, self._STRENGTH_EMOTIONAL,
                f"mixed emotional signals: '{pos}' vs '{neg}' — acknowledge "
                "both, don't flatten",
            ))

    def _detect_structural_semantic(
        self, raw: str, norm: str, low: str, out: List[CollisionReading],
    ) -> None:
        """The form says one thing while the meaning says another:
          • a polite frame wrapped around aggressive, demanding content
          • an imperative command dressed as a question (ends with ? / ؟)
        → STRUCTURAL_SEMANTIC collision."""
        polite = _first_present(_POLITE_AR + _POLITE_EN, norm, low)
        aggressive = _first_present(_AGGRESSIVE_AR + _AGGRESSIVE_EN, norm, low)
        if polite and aggressive:
            fa = IntentFragment(polite, "polite_form", 0.7)
            fb = IntentFragment(aggressive, "aggressive_content", 0.7)
            out.append(self._make_reading(
                CollisionType.STRUCTURAL_SEMANTIC, fa, fb,
                self._STRENGTH_STRUCTURAL,
                f"polite form '{polite}' wraps aggressive content "
                f"'{aggressive}' — form contradicts meaning",
            ))
            return

        # Imperative command phrased as a question.
        starts_imperative = any(
            norm.startswith(_normalize(v)) for v in _IMPERATIVE_START_AR
        )
        is_question = "?" in raw or "؟" in raw
        if starts_imperative and is_question:
            fa = IntentFragment("command", "command_intent", 0.65)
            fb = IntentFragment("?", "question_form", 0.65)
            out.append(self._make_reading(
                CollisionType.STRUCTURAL_SEMANTIC, fa, fb,
                self._STRENGTH_STRUCTURAL,
                "imperative command phrased as a question — form (question) "
                "contradicts intent (command)",
            ))

    def _detect_compatible_multi_intent(
        self, raw: str, norm: str, low: str, out: List[CollisionReading],
    ) -> None:
        """Two distinct cooperating requests joined by a connector with NO
        contradiction (اكتب التقرير ولخّص النتائج / write the report and
        summarize it) → PARALLEL collision that is merge-eligible (compatibility
        ≥ 0.85)."""
        verbs = _distinct_verbs(norm, low)
        connectors = ["و", "ثم", "،", ",", " and ", " then ", "&"]
        has_connector = any(
            (c in low if c.isascii() else c in norm) for c in connectors
        )
        if len(verbs) >= 2 and has_connector:
            fa = IntentFragment(verbs[0], "task_a", 0.7)
            fb = IntentFragment(verbs[1], "task_b", 0.7)
            out.append(self._make_reading(
                CollisionType.PARALLEL, fa, fb, self._STRENGTH_COMPATIBLE,
                f"two compatible tasks ('{verbs[0]}' + '{verbs[1]}') joined by a "
                "connector — mergeable into one coherent response",
            ))

    # ───────────────────────────────────────────────────
    #  Reading construction
    # ───────────────────────────────────────────────────

    def _make_reading(
        self,
        ctype: CollisionType,
        fa: IntentFragment,
        fb: IntentFragment,
        strength: float,
        explanation: str,
    ) -> CollisionReading:
        """Build a CollisionReading: compatibility = 1 - contradiction strength,
        merge only when compatibility ≥ 0.85, otherwise split."""
        compatibility = round(max(0.0, min(1.0, 1.0 - strength)), 3)
        resolution = (
            ResolutionStrategy.SAFE_MERGE
            if compatibility >= MERGE_THRESHOLD
            else ResolutionStrategy.SAFE_SPLIT
        )
        return CollisionReading(
            collision_type=ctype,
            fragment_a=fa,
            fragment_b=fb,
            compatibility_score=compatibility,
            resolution=resolution,
            explanation=explanation,
        )

    @staticmethod
    def _collect_fragments(
        collisions: List[CollisionReading],
    ) -> List[IntentFragment]:
        """All distinct fragments that took part in a collision (dedup by text +
        intent)."""
        out: List[IntentFragment] = []
        seen: set = set()
        for c in collisions:
            for frag in (c.fragment_a, c.fragment_b):
                key = (frag.text, frag.detected_intent)
                if key not in seen:
                    seen.add(key)
                    out.append(frag)
        return out

    @staticmethod
    def _is_safety_relevant(
        h_score: Optional[float], norm: str, low: str,
    ) -> bool:
        """A collision is safety-relevant when the S engine's harm score is high
        OR a safety-relevant term appears in the message."""
        if h_score is not None and h_score >= _H_HIGH_RISK:
            return True
        return any(
            _present_word(t, norm, low)
            for t in (_SAFETY_VOCAB_AR + _SAFETY_VOCAB_EN)
        )


# ═══════════════════════════════════════════════════════════
#  Authority helper — OWNER contradictions are intentional (FN#014)
# ═══════════════════════════════════════════════════════════

def _is_owner(authority: Optional[object]) -> bool:
    """True when the supplied authority is the OWNER (responsible party).

    Accepts a bare string ("OWNER"), or an object exposing ``authority_level``
    (an enum or string). The field note: the OWNER's contradictions are treated
    as INTENTIONAL, not as errors to be resolved away.
    """
    if authority is None:
        return False
    val = getattr(authority, "authority_level", authority)
    val = getattr(val, "name", val)  # enum → its name, else unchanged
    return "OWNER" in str(val).upper()


# ═══════════════════════════════════════════════════════════
#  recommend_action — handling guidance by collision type + resolution
# ═══════════════════════════════════════════════════════════

def recommend_action(result: CollisionResult, owner: bool = False) -> str:
    """Map the result's highest-risk collision to concrete handling guidance.

    HIGH_RISK           → escalate to the Supervisor immediately.
    HIERARCHICAL        → resolve priority; honour the prohibition, split.
    CROSS_LAYER         → acknowledge the conflicting layers before acting.
    STRUCTURAL_SEMANTIC → confirm the real intent; form and meaning disagree.
    PARALLEL (merge)    → Safe-Merge into one coherent response.
    PARALLEL (split)    → Safe-Split: satisfy each separately, in order.

    When ``owner`` is True, a non-high-risk contradiction is reported as
    INTENTIONAL (FN#014): the OWNER may deliberately want both, so honour the
    request as stated rather than splitting it apart. High-risk always escalates,
    because safety is sovereign.
    """
    if not result.has_collision or not result.collisions:
        return ("No intent collision detected — proceed normally. "
                "(لا تصادم نوايا — تابع طبيعياً)")

    top = max(result.collisions, key=lambda c: _SEVERITY[c.collision_type])

    if top.collision_type == CollisionType.HIGH_RISK:
        return ("Stop and escalate to the Supervisor immediately — a "
                "safety-relevant intent collision must never be auto-resolved. "
                "(أوقف وارفع للمشرف فوراً — لا حلّ تلقائي)")

    if owner:
        return ("OWNER authority — the contradiction is treated as INTENTIONAL "
                "(FN#014). Honour both intents as stated; do not split or "
                "second-guess. (الجهة المسؤولة — التعارض مقصود، نفّذ كما طُلب)")

    if top.collision_type == CollisionType.HIERARCHICAL:
        return ("Resolve the hierarchy — the prohibition bounds the request. "
                "Safe-Split: honour the limit, then do what is permitted, in "
                "order. (وضّح الأولوية ونفّذ بالترتيب — القيد يحكم الطلب)")

    if top.collision_type == CollisionType.CROSS_LAYER:
        return ("Acknowledge the conflicting layers (e.g. mixed emotions) "
                "before acting — don't flatten them into one. "
                "(اعترف بتعارض الطبقات قبل التنفيذ)")

    if top.collision_type == CollisionType.STRUCTURAL_SEMANTIC:
        return ("Form and meaning disagree — confirm the real intent before "
                "responding to the surface. (الشكل يخالف المعنى — تحقّق من النية)")

    # PARALLEL — decided by the resolution chosen from the compatibility score.
    if top.resolution == ResolutionStrategy.SAFE_MERGE:
        return ("Intents are compatible (≥ 0.85) — Safe-Merge into one coherent "
                "response. (ادمجهما بأمان في ردّ واحد)")
    return ("Intents conflict — Safe-Split: satisfy each separately and in "
            "order; never blend them into a distorted middle. "
            "(نفّذهما منفصلَين بالترتيب، لا تمزجهما)")


# ═══════════════════════════════════════════════════════════
#  Demo
# ═══════════════════════════════════════════════════════════

def _demo():  # pragma: no cover — manual smoke test
    handler = MultiIntentCollisionHandler()
    cases = [
        "اكتب لي تقرير مختصر وشامل",
        "اكتب لي رسالة بس لا تكتب اسمي",
        "أنا مبسوط بالمشروع بس تعبان مرة",
        "لو سمحت اكتبه حالاً، قلت لك بسرعة",
        "اكتب التقرير ولخّص النتائج",
        "نظّم لي الجدول",
        "write me a brief and comprehensive report",
        "help me but don't help me",
        "write the report and summarize the findings",
    ]
    print("=" * 66)
    print("  AATIF Multi-Intent Collision Handler — تصادم النوايا (FN#036)")
    print("=" * 66)
    for text in cases:
        r = handler.analyze(text)
        print(f"\n📝 «{text}»")
        hr = r.highest_risk.value if r.highest_risk else "—"
        print(f"   has_collision={r.has_collision}  highest_risk={hr}")
        for c in r.collisions:
            print(f"   • {c.collision_type.value:20s} "
                  f"compat={c.compatibility_score:.2f} "
                  f"→ {c.resolution.value}")
        print(f"   → {r.recommended_action.splitlines()[0]}")


if __name__ == "__main__":
    _demo()
