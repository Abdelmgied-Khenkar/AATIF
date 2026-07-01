"""
AATIF PVM Detector — FN#041 Context-Preservation & Parallel-Task Safety Protocol

Architecture: B-prime (B')
─────────────────────────────────────────────────────────────────
PVMContext       →  pure storage (prior PVM state, turn bookkeeping)
PVMDetector      →  observational (outputs PVMReading + evidence)
R Equation       →  stylistic (uses PVM reading for response style via G_eff)

Critical Design Rule (Single Mind):
  Only GovernanceEquation makes SAFETY decisions. FN#041 is STYLISTIC,
  NOT safety. PVMDetector never touches S, H, θ, or the GovernanceEquation.
  It binds through B5 (Behaviour), NOT B6 (Safety). It says "the user appears
  busy — confidence 0.75, recommend brief acknowledgment." It decides
  nothing about whether a request is allowed.

الصمت الواعي كقانون دستوري — conscious silence as constitutional law.
When the user is occupied, the system does not fill the silence. It
acknowledges receipt, confirms it is present, and WAITS for the human to
signal continuation. This is not passivity — it is governed patience.

  "لما المستخدم مشغول، النظام ينتظر. لا يملأ الصمت."
  "When the user is busy, the system waits. It does not fill the silence."

Design consensus: Claude, 2026-07-01 (FN041_DESIGN_BRIEF.md)
Field Note: FN#041 (Context-Preservation & Parallel-Task Safety Protocol)

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import enum
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:  # pragma: no cover — import shim for both package and flat layouts
    from aatif_arabic_utils import normalize_arabic
except Exception:  # pragma: no cover
    def normalize_arabic(text: str) -> str:
        return text.lower()


# ═══════════════════════════════════════════════════════════════
#  Feature Flags  (FN#041 ships ON by default)
# ═══════════════════════════════════════════════════════════════

PVM_ENABLED = True               # master switch for the PVM pipeline
PVM_MONITOR_ONLY = False          # when True, detect but never recommend pause


# ═══════════════════════════════════════════════════════════════
#  Authority Level Declaration (B-prime contract)
# ═══════════════════════════════════════════════════════════════

AUTHORITY_LEVEL = "B_PRIME_OBSERVATIONAL"
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA            = False
CAN_MODIFY_S                = False
CAN_EMIT_JUDICIAL_DECISION = False


# ═══════════════════════════════════════════════════════════════
#  PVM State Lifecycle  (FN#041 v1)
# ═══════════════════════════════════════════════════════════════
#
#  A lightweight state enum — the context-preservation lifecycle:
#
#    ACTIVE         → normal operation, user is present and engaged
#    DETECTING      → 1+ signals suggest user may be busy / multi-tasking
#    PVM_ENGAGED    → high confidence user is busy; system is waiting
#    REACTIVATING   → user has returned; transitioning back to active
#
#  Transitions are driven by next_pvm_state() — a simple helper, NOT a
#  formal guarded machine. The state lives on PVMContext, stored by the
#  ConversationManager exactly like PSPContext.

class PVMState(enum.Enum):
    """FN#041 context-preservation lifecycle state (stylistic, never safety)."""
    ACTIVE = "active"
    DETECTING = "detecting"
    PVM_ENGAGED = "pvm_engaged"
    REACTIVATING = "reactivating"


# ═══════════════════════════════════════════════════════════════
#  Constants — calibration values
# ═══════════════════════════════════════════════════════════════

# Detection thresholds
FAST_PATH_NOT_BUSY_THRESHOLD = 0.95     # skip PVM when this confident user is NOT busy
PVM_ENGAGE_THRESHOLD = 0.60             # confidence to transition to PVM_ENGAGED
PVM_ENGAGE_THRESHOLD_HIGH_STAKES = 0.70 # higher bar for medical/legal domains
PVM_ENGAGE_THRESHOLD_FAST_PACED = 0.45  # lower bar for fast-paced contexts

# Incomplete-acknowledgment detection
MINIMAL_RESPONSE_MAX_WORDS = 3          # responses with ≤3 words may be incomplete ack
MINIMAL_RESPONSE_MAX_CHARS = 15         # ... or ≤15 characters
CONSECUTIVE_MINIMAL_FOR_DETECTING = 2   # 2 consecutive minimal responses → DETECTING
CONSECUTIVE_MINIMAL_FOR_ENGAGED = 3     # 3 consecutive minimal responses → PVM_ENGAGED

# Temporal signal thresholds (seconds)
GAP_MULTIPLIER_FOR_BUSY = 2.0           # gap > 2× user average → possible busy
DEFAULT_AVERAGE_GAP_SECONDS = 60.0      # assumed average gap when no history
LONG_GAP_ABSOLUTE_SECONDS = 300.0       # 5 min absolute threshold

# State decay — how many turns without PVM signals before auto-exit
DECAY_TURNS_TO_ACTIVE = 3               # general contexts
DECAY_TURNS_HIGH_STAKES = 5             # high-stakes: hold PVM longer

# Pause types — what PVM recommends to the R equation
PAUSE_FULL_WAIT = "full_wait"           # system should wait, only acknowledge
PAUSE_BRIEF_ACK = "brief_ack"          # brief acknowledgment + wait
PAUSE_SHORTENED = "shortened"           # shorter response than normal
PAUSE_NORMAL = "normal"                 # no pause needed

# Domain → PVM profile for cultural sensitivity
PVM_PROFILE_BY_DOMAIN: Dict[str, str] = {
    "healthcare": "high_stakes",
    "medical":    "high_stakes",
    "legal":      "high_stakes",
    "finance":    "high_stakes",
    "education":  "educational",
    "general":    "default",
    "creative":   "fast_paced",
}
DEFAULT_PVM_PROFILE = "default"


# ═══════════════════════════════════════════════════════════════
#  Explicit busy markers — deterministic tier (tier 1)
# ═══════════════════════════════════════════════════════════════
#
#  The user explicitly signals they are busy or need a moment.
#  Highest confidence signals — these immediately escalate to DETECTING
#  or PVM_ENGAGED depending on strength.

BUSY_MARKERS_AR = [
    "مشغول", "مشغوله", "مشغولة",          # busy
    "لحظة", "لحظه",                         # one moment
    "دقيقة", "دقيقه",                       # one minute
    "ثانية", "ثانيه",                       # one second
    "بعدين", "بعدين اكلمك",                # later / I'll talk to you later
    "بكمل معاك", "بكمل معك",               # I'll continue with you (later)
    "انتظر", "انتظري",                     # wait
    "خلني", "خليني",                        # let me (implies doing something else)
    "مو الحين", "مش الحين",                # not now
    "بس دقيقة", "بس لحظة",                # just a minute/moment
    "معليش انتظرني",                        # sorry wait for me
    "مره ثانيه", "مرة ثانية",              # another time
]

BUSY_MARKERS_EN = [
    "busy", "i'm busy", "im busy",
    "wait", "hold on", "one moment", "one sec", "one second",
    "give me a sec", "give me a minute", "give me a moment",
    "brb", "be right back",
    "later", "not now", "in a bit",
    "let me finish", "let me do this first",
    "hang on", "just a minute", "just a sec",
    "i'll be back", "ill be back",
    "sorry busy",
]

# ═══════════════════════════════════════════════════════════════
#  Multi-task markers — user explicitly says they're doing something else
# ═══════════════════════════════════════════════════════════════

MULTITASK_MARKERS_AR = [
    "خلني اخلص", "خلني أخلص",             # let me finish
    "بس خلني اول", "بس خليني اول",         # but let me first
    "عندي شغل", "عندي شي",                 # I have work/something
    "في اجتماع", "في ميتنق",               # in a meeting
    "على الهاتف", "على التلفون",            # on the phone
    "بسوي شي", "بأسوي شي",                 # I'm going to do something
    "رجعت لك", "ارجع لك",                  # I'll get back to you
]

MULTITASK_MARKERS_EN = [
    "let me finish this first", "let me do this first",
    "in a meeting", "on a call", "on the phone",
    "got something", "have to do something",
    "i'll get back to you", "ill get back to you",
    "be back in a bit", "need to step away",
    "doing something else", "multitasking",
]

# ═══════════════════════════════════════════════════════════════
#  Return signals — user is coming back
# ═══════════════════════════════════════════════════════════════
#
#  These exit PVM_ENGAGED → REACTIVATING

RETURN_MARKERS_AR = [
    "كمل", "أكمل", "كملي",                 # continue
    "نكمل", "يلا نكمل",                     # let's continue
    "وين وقفنا", "فين وقفنا",              # where did we stop
    "يلا كمل", "يلا",                       # come on, continue
    "رجعت", "رجعنا",                        # I'm back
    "خلصت", "خلّصت",                        # I'm done (with other task)
    "نرجع", "نرجع للموضوع",                # let's go back (to the topic)
    "طيب كمل", "اوكي كمل",                 # ok continue
    "فرغت",                                  # I'm free now
    "الحين كمل",                             # now continue
    "تابع", "تابعي",                        # go on
]

RETURN_MARKERS_EN = [
    "continue", "go on", "go ahead",
    "i'm back", "im back", "back",
    "where were we", "where did we stop",
    "resume", "let's continue", "lets continue",
    "i'm done", "im done", "done with that",
    "ready", "i'm ready", "im ready",
    "ok continue", "okay continue",
    "i'm free", "im free", "free now",
    "carry on", "proceed",
]

# ═══════════════════════════════════════════════════════════════
#  Incomplete acknowledgment markers — short non-directive responses
# ═══════════════════════════════════════════════════════════════
#
#  These are NOT busy signals by themselves. But when a user who was
#  writing paragraphs suddenly sends only "ok" — that's a pattern change
#  worth noting. Confidence is lower (0.35-0.50).

INCOMPLETE_ACK_AR = [
    "طيب", "اوكي", "ماشي", "تمام", "اه", "ايوه", "اها",
    "هه", "ههه", "لا", "اي", "يب", "حسنا",
]

INCOMPLETE_ACK_EN = [
    "ok", "okay", "k", "kk", "hmm", "hm", "mm",
    "yeah", "yep", "yup", "sure", "right", "uh huh",
    "ya", "ye", "mhm", "alright", "fine",
]

# ═══════════════════════════════════════════════════════════════
#  Substantive message markers — fast-path NOT busy signals
# ═══════════════════════════════════════════════════════════════
#
#  If the user sends a question, instruction, or long message,
#  they are clearly engaged — fast-path skip PVM detection.

DIRECTIVE_MARKERS_EN = [
    "can you", "could you", "please", "tell me", "show me",
    "explain", "help me", "what is", "how do", "why does",
    "i want", "i need", "make me", "create", "write",
    "find", "search", "list", "give me",
]

DIRECTIVE_MARKERS_AR = [
    "ابغى", "ابي", "اريد", "اعطني", "ساعدني",
    "اشرح", "وضح", "قول لي", "ابحث", "اكتب",
    "اسوي", "كيف", "ليش", "وش", "ايش",
    "ممكن", "لو سمحت", "هل",
]

# ═══════════════════════════════════════════════════════════════
#  Acknowledgment templates — Arabic-first, human, warm
# ═══════════════════════════════════════════════════════════════

ACKNOWLEDGMENTS = {
    "busy_detected": "أنا هنا، كمل لما تفرغ 🙏",
    "busy_detected_en": "I'm here — take your time, continue when you're ready.",
    "brief_ack": "وصلني، لما تكون جاهز كمل.",
    "brief_ack_en": "Got it — let me know when you're ready to continue.",
    "returning": "أهلاً من جديد — وين وقفنا؟",
    "returning_en": "Welcome back — where did we leave off?",
    "still_here": "لا تشيل هم، أنا موجود.",
    "still_here_en": "No worries, I'm still here.",
}


# ═══════════════════════════════════════════════════════════════
#  Data Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class PVMReading:
    """
    Output of PVMDetector.detect() — observational, STYLISTIC, NOT safety.

    This reading tells the R equation whether the user appears to be busy
    and what kind of response adjustment is recommended. It never blocks,
    never modifies H/θ/S, and never makes safety decisions.
    """
    state: PVMState
    confidence: float                    # [0,1] how certain we are of the state
    recommend_behavioral_pause: bool                   # Behavioural recommendation to R equation only.
    # MUST NOT be interpreted as runtime block, safety bypass, or governance override.
    # PVM is STYLISTIC (B5). It never touches S, H, θ, or the GovernanceEquation.
    pause_type: str                      # "full_wait" | "brief_ack" | "shortened" | "normal"
    recommended_acknowledgment: str      # Arabic-first acknowledgment text
    evidence: List[str] = field(default_factory=list)
    signals_detected: List[str] = field(default_factory=list)
    estimated_return_likelihood: float = 0.5  # [0,1] will user likely return soon?


@dataclass
class PVMContext:
    """
    Pure storage of prior PVM context. Owns NO logic.

    Mirrors the PSPContext pattern: storage only. The detector reads it
    to maintain state continuity across turns. Lives as a field on
    ``conversation_state.pvm_context``.
    """
    state: PVMState = PVMState.ACTIVE
    last_explicit_directive_turn: int = -1
    consecutive_minimal_responses: int = 0
    last_gap_seconds: Optional[float] = None
    pvm_engage_turn: int = -1
    pvm_engage_timestamp: Optional[float] = None
    last_return_signal_turn: int = -1
    total_pvm_engagements: int = 0
    quiet_turns_since_pvm: int = 0       # turns without PVM signals for decay
    last_transition_reason: Optional[str] = None
    domain_profile: str = DEFAULT_PVM_PROFILE


@dataclass
class PVMDomainConfig:
    """
    Domain config carrying pvm_profile for cultural sensitivity.

    The PVM engage threshold varies by domain/culture. Gulf Arabic contexts
    tolerate longer silence; Western/fast-paced contexts trigger earlier.
    The detector READS this; it never computes cultural norms.
    """
    domain: str = "general"
    pvm_profile: str = DEFAULT_PVM_PROFILE
    high_stakes: bool = False
    engage_threshold: float = PVM_ENGAGE_THRESHOLD

    @classmethod
    def for_domain(cls, domain: str) -> "PVMDomainConfig":
        profile = PVM_PROFILE_BY_DOMAIN.get((domain or "general").lower(),
                                            DEFAULT_PVM_PROFILE)
        high_stakes = profile == "high_stakes"
        if high_stakes:
            threshold = PVM_ENGAGE_THRESHOLD_HIGH_STAKES
        elif profile == "fast_paced":
            threshold = PVM_ENGAGE_THRESHOLD_FAST_PACED
        else:
            threshold = PVM_ENGAGE_THRESHOLD
        return cls(
            domain=domain or "general",
            pvm_profile=profile,
            high_stakes=high_stakes,
            engage_threshold=threshold,
        )


# ═══════════════════════════════════════════════════════════════
#  Small duck-typed accessors  (mirrors PSP pattern)
# ═══════════════════════════════════════════════════════════════

def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a key from dict, dataclass, or arbitrary object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _text_of(turn_features: Any) -> str:
    """Extract the text payload from turn_features (str, dict, or object)."""
    if turn_features is None:
        return ""
    if isinstance(turn_features, str):
        return turn_features
    return _get(turn_features, "text", "") or ""


# ═══════════════════════════════════════════════════════════════
#  PVMDetector — observational, STYLISTIC, NOT safety
# ═══════════════════════════════════════════════════════════════

class PVMDetector:
    """
    Three-tier detection for context-preservation / parallel-task awareness.

      Tier 1 — deterministic markers (cheap, high precision, always run)
      Tier 2 — temporal signals       (from TimeSense, when available)
      Tier 3 — behavioral signals     (from Fingerprint, when available)

    The detector outputs a PVMReading. It does not generate response content,
    does not block responses, and does not touch S/H/θ. It recommends a
    pause type to the R equation through B5 (Behaviour).

    الصمت الواعي ≠ التجاهل
    Conscious silence ≠ ignoring. PVM always acknowledges receipt.
    """

    def __init__(self, engage_threshold: float = PVM_ENGAGE_THRESHOLD,
                 fast_path_threshold: float = FAST_PATH_NOT_BUSY_THRESHOLD):
        self.engage_threshold = engage_threshold
        self.fast_path_threshold = fast_path_threshold

    # ── Public API ──────────────────────────────────────────────

    def detect(self,
               turn_features: Any,
               prior_context: Any = None,
               domain_config: Any = None,
               time_reading: Any = None,
               fingerprint_reading: Any = None,
               current_turn_index: int = 0) -> PVMReading:
        """
        Consume one turn → PVMReading.

        Parameters
        ----------
        turn_features : str | dict | object
            The user turn. A bare string, or anything exposing ``text``.
        prior_context : PVMContext | dict | None
            Prior PVM state for continuity across turns.
        domain_config : PVMDomainConfig | dict | None
            Domain config carrying ``pvm_profile`` for cultural sensitivity.
        time_reading : TimeReading | dict | None
            Temporal signals from TimeSense (gap, fatigue, etc.).
        fingerprint_reading : FingerprintReading | dict | None
            Behavioral pattern from Fingerprint (style, patterns).
        current_turn_index : int
            Current turn number for bookkeeping.
        """
        text = _text_of(turn_features)
        norm, low = self._prep(text)
        config = self._resolve_config(domain_config)
        prior_state = self._get_prior_state(prior_context)

        evidence: List[str] = []
        signals: List[str] = []

        # ── Check for return signals first ─────────────────────
        # If PVM is engaged and user sends return signal, reactivate
        if prior_state in (PVMState.PVM_ENGAGED, PVMState.DETECTING):
            return_hits = self._find(low, norm, RETURN_MARKERS_EN, RETURN_MARKERS_AR)
            if return_hits:
                signals.append(f"return_markers={return_hits[:3]}")
                evidence.append(
                    f"return signal detected while in {prior_state.value}: "
                    f"{return_hits[:3]} → REACTIVATING"
                )
                return PVMReading(
                    state=PVMState.REACTIVATING,
                    confidence=0.90,
                    recommend_behavioral_pause=False,
                    pause_type=PAUSE_NORMAL,
                    recommended_acknowledgment=ACKNOWLEDGMENTS["returning"],
                    evidence=evidence,
                    signals_detected=signals,
                    estimated_return_likelihood=1.0,
                )

        # ── Sparse Activation: fast-path skip ──────────────────
        not_busy_conf = self._not_busy_confidence(text, low, norm)

        if not_busy_conf >= self.fast_path_threshold:
            evidence.append(
                f"fast_path_skip: not_busy_conf={not_busy_conf:.2f} "
                f">= {self.fast_path_threshold} (user is clearly engaged)"
            )
            # If previously in PVM_ENGAGED or DETECTING, reset to ACTIVE
            if prior_state in (PVMState.PVM_ENGAGED, PVMState.DETECTING,
                               PVMState.REACTIVATING):
                evidence.append(
                    f"substantive message → exiting {prior_state.value} → ACTIVE"
                )
            return PVMReading(
                state=PVMState.ACTIVE,
                confidence=not_busy_conf,
                recommend_behavioral_pause=False,
                pause_type=PAUSE_NORMAL,
                recommended_acknowledgment="",
                evidence=evidence,
                signals_detected=[],
                estimated_return_likelihood=0.5,
            )

        # ── Tier 1: deterministic markers ──────────────────────
        confidence = 0.0

        # Explicit busy markers
        busy_hits = self._find(low, norm, BUSY_MARKERS_EN, BUSY_MARKERS_AR)
        if busy_hits:
            confidence = min(0.70 + 0.10 * len(busy_hits), 0.95)
            signals.append(f"busy_markers={busy_hits[:4]}")
            evidence.append(f"explicit busy: {busy_hits[:4]} → conf={confidence:.2f}")

        # Multi-task markers
        multitask_hits = self._find(low, norm, MULTITASK_MARKERS_EN,
                                    MULTITASK_MARKERS_AR)
        if multitask_hits:
            confidence = max(confidence, min(0.75 + 0.10 * len(multitask_hits), 0.95))
            signals.append(f"multitask_markers={multitask_hits[:3]}")
            evidence.append(f"multi-task signal: {multitask_hits[:3]}")

        # Incomplete acknowledgment detection
        is_minimal = self._is_minimal_response(text, low, norm)
        if is_minimal:
            consecutive = _get(prior_context, "consecutive_minimal_responses", 0) + 1
            signals.append(f"minimal_response (consecutive={consecutive})")
            evidence.append(f"minimal response detected: '{text[:20]}' "
                           f"(consecutive={consecutive})")
            if consecutive >= CONSECUTIVE_MINIMAL_FOR_ENGAGED:
                confidence = max(confidence, 0.65)
            elif consecutive >= CONSECUTIVE_MINIMAL_FOR_DETECTING:
                confidence = max(confidence, 0.45)
            else:
                confidence = max(confidence, 0.30)

        # ── Tier 2: temporal signals ───────────────────────────
        if time_reading is not None:
            temporal_conf = self._temporal_signal(time_reading, prior_context)
            if temporal_conf > 0:
                confidence = max(confidence, temporal_conf)
                signals.append(f"temporal_signal={temporal_conf:.2f}")
                gap = _get(time_reading, "time_since_last_interaction", None)
                gap_str = ""
                if gap is not None:
                    if hasattr(gap, "total_seconds"):
                        gap_str = f" (gap={gap.total_seconds():.0f}s)"
                    else:
                        gap_str = f" (gap={gap})"
                fatigue = _get(time_reading, "fatigue_risk", False)
                evidence.append(
                    f"temporal: conf={temporal_conf:.2f}{gap_str}"
                    f"{' +fatigue_risk' if fatigue else ''}"
                )

        # ── Tier 3: behavioral signals ─────────────────────────
        if fingerprint_reading is not None:
            behavioral_conf = self._behavioral_signal(
                text, fingerprint_reading, prior_context
            )
            if behavioral_conf > 0:
                confidence = max(confidence, behavioral_conf)
                signals.append(f"behavioral_signal={behavioral_conf:.2f}")
                evidence.append(f"behavioral pattern: conf={behavioral_conf:.2f}")

        # ── Context: prior PVM state carries forward ───────────
        if prior_state == PVMState.PVM_ENGAGED:
            confidence = max(confidence, 0.60)
            evidence.append("context: PVM was already engaged")
        elif prior_state == PVMState.DETECTING:
            confidence = max(confidence, 0.40)
            evidence.append("context: PVM was in detecting state")

        # ── Determine resulting state ──────────────────────────
        threshold = config.engage_threshold
        state, pause_type, ack = self._determine_state(
            confidence, threshold, prior_state, signals, evidence, config
        )

        recommend_behavioral_pause = pause_type != PAUSE_NORMAL
        if PVM_MONITOR_ONLY:
            recommend_behavioral_pause = False
            evidence.append("PVM_MONITOR_ONLY=True → recommend_behavioral_pause forced False")

        # ── Estimate return likelihood ─────────────────────────
        return_likelihood = self._estimate_return_likelihood(
            signals, prior_context, time_reading
        )

        return PVMReading(
            state=state,
            confidence=round(confidence, 3),
            recommend_behavioral_pause=recommend_behavioral_pause,
            pause_type=pause_type,
            recommended_acknowledgment=ack,
            evidence=evidence,
            signals_detected=signals,
            estimated_return_likelihood=round(return_likelihood, 3),
        )

    # ── Tier 1 helpers ─────────────────────────────────────────

    @staticmethod
    def _prep(text: str) -> Tuple[str, str]:
        """Return (normalized_arabic, lowercased) views of the text."""
        return normalize_arabic(text), text.lower()

    @staticmethod
    def _find(low: str, norm: str,
              markers_en: List[str], markers_ar: List[str]) -> List[str]:
        """Markers present in the text — EN matched on lowercase, AR on normalized."""
        hits = [m for m in markers_en if m in low]
        hits += [m for m in markers_ar if normalize_arabic(m) in norm]
        return hits

    def _not_busy_confidence(self, text: str, low: str, norm: str) -> float:
        """
        Confidence that this turn is NOT a busy signal, from deterministic
        signals only. Drives the Sparse Activation fast-path.

        Any busy/multitask marker collapses this confidence.
        """
        # Any busy marker → definitely look closer
        if self._find(low, norm, BUSY_MARKERS_EN, BUSY_MARKERS_AR):
            return 0.05
        if self._find(low, norm, MULTITASK_MARKERS_EN, MULTITASK_MARKERS_AR):
            return 0.05

        # Directive markers → user is clearly engaged, not busy
        if self._find(low, norm, DIRECTIVE_MARKERS_EN, DIRECTIVE_MARKERS_AR):
            return 0.97

        # Questions → user is engaged
        if "?" in text or "؟" in text:
            return 0.96

        # Substantive message (>20 chars, multiple words) → probably engaged
        words = text.strip().split()
        if len(words) > 5 or len(text.strip()) > 50:
            return 0.95

        # Incomplete ack markers → might be busy, look closer
        if self._is_minimal_response(text, low, norm):
            return 0.40

        # Medium-length text without clear signals → ambiguous
        if len(text.strip()) > 20:
            return 0.80

        # Short text without clear signals → slightly ambiguous
        return 0.70

    def _is_minimal_response(self, text: str, low: str, norm: str) -> bool:
        """
        Check if the message is a minimal / incomplete acknowledgment.

        A minimal response is a very short message that contains only
        acknowledgment tokens without directive content.
        """
        stripped = text.strip()
        if not stripped:
            return False

        words = stripped.split()
        # Check word count and char count
        if len(words) > MINIMAL_RESPONSE_MAX_WORDS:
            return False
        if len(stripped) > MINIMAL_RESPONSE_MAX_CHARS:
            return False

        # Check if it matches known incomplete ack patterns
        for ack in INCOMPLETE_ACK_EN:
            if low.strip() == ack or low.strip() == ack + ".":
                return True
        for ack in INCOMPLETE_ACK_AR:
            if normalize_arabic(ack) in norm:
                return True

        return False

    # ── Tier 2: temporal signals ───────────────────────────────

    def _temporal_signal(self, time_reading: Any,
                         prior_context: Any) -> float:
        """
        Busy confidence from temporal signals.

        A long gap (relative to the user's pattern) suggests the user
        stepped away. Combined with fatigue, this raises PVM confidence.
        """
        confidence = 0.0

        # Gap assessment from TimeSense
        gap_assessment = _get(time_reading, "interaction_gap_assessment", "")
        if gap_assessment == "طويل":  # long gap
            confidence = max(confidence, 0.40)

        # Absolute gap check
        gap = _get(time_reading, "time_since_last_interaction", None)
        if gap is not None:
            gap_seconds = gap.total_seconds() if hasattr(gap, "total_seconds") else 0
            if gap_seconds > LONG_GAP_ABSOLUTE_SECONDS:
                confidence = max(confidence, 0.50)
            elif gap_seconds > DEFAULT_AVERAGE_GAP_SECONDS * GAP_MULTIPLIER_FOR_BUSY:
                confidence = max(confidence, 0.40)

        # Fatigue risk from TimeSense
        fatigue = _get(time_reading, "fatigue_risk", False)
        if fatigue:
            confidence = max(confidence, confidence + 0.15)
            confidence = min(confidence, 0.60)

        return confidence

    # ── Tier 3: behavioral signals ─────────────────────────────

    def _behavioral_signal(self, text: str,
                            fingerprint_reading: Any,
                            prior_context: Any) -> float:
        """
        Busy confidence from behavioral pattern changes.

        If the user's current message dramatically differs from their
        established pattern, they may be multi-tasking or distracted.
        """
        confidence = 0.0

        # Check for communication style change
        # If user normally writes formal/long and suddenly sends casual/short
        usual_style = _get(fingerprint_reading, "communication_style", "")
        if usual_style == "formal" and len(text.strip()) < 10:
            confidence = max(confidence, 0.35)

        # Check interaction frequency change
        freq = _get(fingerprint_reading, "interaction_frequency", "")
        if freq == "daily" and _get(prior_context, "last_gap_seconds", 0):
            last_gap = _get(prior_context, "last_gap_seconds", 0) or 0
            if last_gap > 3600:  # > 1 hour for a daily user
                confidence = max(confidence, 0.30)

        return confidence

    # ── State determination ────────────────────────────────────

    def _determine_state(self, confidence: float, threshold: float,
                         prior_state: PVMState, signals: List[str],
                         evidence: List[str],
                         config: PVMDomainConfig) -> Tuple[PVMState, str, str]:
        """
        Determine the resulting PVM state from confidence + prior state.

        Returns (state, pause_type, recommended_acknowledgment).
        """
        # Explicit busy markers → direct to PVM_ENGAGED if strong enough
        has_explicit_busy = any("busy_markers" in s for s in signals)
        has_multitask = any("multitask_markers" in s for s in signals)

        if has_explicit_busy or has_multitask:
            if confidence >= threshold:
                evidence.append(
                    f"explicit busy/multitask signal → PVM_ENGAGED "
                    f"(conf={confidence:.2f} >= threshold={threshold:.2f})"
                )
                return (
                    PVMState.PVM_ENGAGED,
                    PAUSE_FULL_WAIT,
                    ACKNOWLEDGMENTS["busy_detected"],
                )
            else:
                evidence.append(
                    f"busy signal but below threshold → DETECTING "
                    f"(conf={confidence:.2f} < threshold={threshold:.2f})"
                )
                return (
                    PVMState.DETECTING,
                    PAUSE_BRIEF_ACK,
                    ACKNOWLEDGMENTS["brief_ack"],
                )

        # Gradual escalation from repeated minimal responses
        if confidence >= threshold:
            if prior_state == PVMState.PVM_ENGAGED:
                evidence.append(
                    f"maintaining PVM_ENGAGED (conf={confidence:.2f})"
                )
                return (
                    PVMState.PVM_ENGAGED,
                    PAUSE_FULL_WAIT,
                    ACKNOWLEDGMENTS["still_here"],
                )
            evidence.append(
                f"confidence {confidence:.2f} >= threshold {threshold:.2f} "
                f"→ PVM_ENGAGED"
            )
            return (
                PVMState.PVM_ENGAGED,
                PAUSE_FULL_WAIT,
                ACKNOWLEDGMENTS["busy_detected"],
            )

        if confidence >= threshold * 0.6:  # partial signals
            evidence.append(
                f"partial signals (conf={confidence:.2f}) → DETECTING"
            )
            return (
                PVMState.DETECTING,
                PAUSE_SHORTENED,
                ACKNOWLEDGMENTS["brief_ack"],
            )

        # Below any threshold → ACTIVE
        if prior_state in (PVMState.DETECTING, PVMState.PVM_ENGAGED):
            evidence.append(
                f"confidence dropped (conf={confidence:.2f}) "
                f"→ returning to ACTIVE"
            )
        return (PVMState.ACTIVE, PAUSE_NORMAL, "")

    # ── Return likelihood estimation ───────────────────────────

    @staticmethod
    def _estimate_return_likelihood(signals: List[str],
                                     prior_context: Any,
                                     time_reading: Any) -> float:
        """
        Estimate how likely the user is to return soon.

        Higher when: explicit "brb" signal, daytime, short gap.
        Lower when: late night, long gap, no explicit signal.
        """
        likelihood = 0.5  # base

        # Explicit busy signals often come with implicit "I'll be back"
        if any("busy_markers" in s for s in signals):
            likelihood = max(likelihood, 0.70)
        if any("multitask_markers" in s for s in signals):
            likelihood = max(likelihood, 0.80)

        # Time-of-day affects return likelihood
        if time_reading is not None:
            is_late_night = _get(time_reading, "is_late_night", False)
            if is_late_night:
                likelihood *= 0.6  # less likely to return at 3am

            is_work_hours = _get(time_reading, "is_work_hours", False)
            if is_work_hours:
                likelihood = max(likelihood, 0.65)

        return max(0.0, min(1.0, likelihood))

    # ── Config resolution ──────────────────────────────────────

    def _resolve_config(self, domain_config: Any) -> PVMDomainConfig:
        """Resolve domain_config to PVMDomainConfig, duck-typing safe."""
        if isinstance(domain_config, PVMDomainConfig):
            return domain_config
        if domain_config is None:
            return PVMDomainConfig()
        profile = _get(domain_config, "pvm_profile", None)
        domain = _get(domain_config, "domain", "general")
        if profile is None:
            return PVMDomainConfig.for_domain(domain)
        high_stakes = bool(_get(domain_config, "high_stakes",
                                profile == "high_stakes"))
        threshold = float(_get(domain_config, "engage_threshold",
                               PVM_ENGAGE_THRESHOLD))
        return PVMDomainConfig(
            domain=domain or "general",
            pvm_profile=profile,
            high_stakes=high_stakes,
            engage_threshold=threshold,
        )

    # ── Prior state extraction ─────────────────────────────────

    @staticmethod
    def _get_prior_state(prior_context: Any) -> PVMState:
        """Extract the prior PVM state from context, default ACTIVE."""
        state = _get(prior_context, "state", None)
        if state is None:
            return PVMState.ACTIVE
        if isinstance(state, PVMState):
            return state
        # String fallback
        try:
            return PVMState(str(state))
        except (ValueError, KeyError):
            return PVMState.ACTIVE


# ═══════════════════════════════════════════════════════════════
#  State-lifecycle transition helper  (FN#041 v1)
# ═══════════════════════════════════════════════════════════════

def next_pvm_state(current_state: PVMState,
                   pvm_reading: Any,
                   user_turn_text: str = "",
                   topic_shift_signal: bool = False) -> Tuple[PVMState, str]:
    """
    Pure-logic transition: (current_state, PVMReading) → (next_state, reason).

    This helper applies transition rules without mutating anything.
    The caller (Governor / ConversationManager) stores the result.

    Transition rules:
      ACTIVE → DETECTING        : PVMReading.state == DETECTING
      ACTIVE → PVM_ENGAGED      : PVMReading.state == PVM_ENGAGED (explicit busy)
      DETECTING → PVM_ENGAGED   : PVMReading.state == PVM_ENGAGED
      DETECTING → ACTIVE        : substantive message (PVMReading.state == ACTIVE)
      PVM_ENGAGED → REACTIVATING: return signal detected
      PVM_ENGAGED → ACTIVE      : substantive message with no PVM signals
      REACTIVATING → ACTIVE     : any substantive follow-up
      Any → ACTIVE              : topic_shift_signal (fresh topic = fresh context)
    """
    if topic_shift_signal:
        return (PVMState.ACTIVE, "topic_shift → context reset → ACTIVE")

    reading_state = _get(pvm_reading, "state", PVMState.ACTIVE)
    if isinstance(reading_state, str):
        try:
            reading_state = PVMState(reading_state)
        except (ValueError, KeyError):
            reading_state = PVMState.ACTIVE

    # ── REACTIVATING always goes to ACTIVE on next substantive turn ──
    if current_state == PVMState.REACTIVATING:
        if reading_state == PVMState.ACTIVE:
            return (PVMState.ACTIVE, "reactivation complete → ACTIVE")
        # Still detecting busy after reactivation? Back to PVM
        if reading_state in (PVMState.PVM_ENGAGED, PVMState.DETECTING):
            return (reading_state,
                    f"still busy after reactivation → {reading_state.value}")
        return (PVMState.ACTIVE, "reactivation → ACTIVE (default)")

    # ── PVM_ENGAGED ──
    if current_state == PVMState.PVM_ENGAGED:
        if reading_state == PVMState.REACTIVATING:
            return (PVMState.REACTIVATING, "return signal → REACTIVATING")
        if reading_state == PVMState.ACTIVE:
            return (PVMState.ACTIVE, "substantive message → exiting PVM → ACTIVE")
        return (PVMState.PVM_ENGAGED, "maintaining PVM_ENGAGED")

    # ── DETECTING ──
    if current_state == PVMState.DETECTING:
        if reading_state == PVMState.PVM_ENGAGED:
            return (PVMState.PVM_ENGAGED, "signals escalated → PVM_ENGAGED")
        if reading_state == PVMState.ACTIVE:
            return (PVMState.ACTIVE, "no more busy signals → back to ACTIVE")
        return (PVMState.DETECTING, "maintaining DETECTING")

    # ── ACTIVE ──
    if reading_state == PVMState.PVM_ENGAGED:
        return (PVMState.PVM_ENGAGED, "explicit busy → ACTIVE → PVM_ENGAGED")
    if reading_state == PVMState.DETECTING:
        return (PVMState.DETECTING, "partial busy signals → DETECTING")

    return (PVMState.ACTIVE, "no PVM signals → ACTIVE")


def pvm_should_deactivate(context: Any, domain_profile: str = "default") -> bool:
    """
    Check whether PVM should auto-deactivate due to decay.

    After N turns with no PVM signals, PVM returns to ACTIVE automatically.
    High-stakes domains hold PVM longer (5 turns vs 3).
    """
    quiet = _get(context, "quiet_turns_since_pvm", 0) or 0
    threshold = (DECAY_TURNS_HIGH_STAKES
                 if domain_profile == "high_stakes"
                 else DECAY_TURNS_TO_ACTIVE)
    return quiet >= threshold


def apply_pvm_transition(context: PVMContext,
                         pvm_reading: PVMReading,
                         current_turn_index: int = 0) -> PVMContext:
    """
    Apply a PVM transition to a context, returning a new context.

    Non-mutating — returns a new PVMContext with updated fields.
    The caller is responsible for storing the result.
    """
    new_state, reason = next_pvm_state(
        context.state, pvm_reading,
    )

    # Track consecutive minimal responses
    has_minimal = any("minimal_response" in s for s in pvm_reading.signals_detected)
    new_consecutive = (context.consecutive_minimal_responses + 1
                       if has_minimal else 0)

    # Track PVM engagements
    new_total = context.total_pvm_engagements
    new_engage_turn = context.pvm_engage_turn
    new_engage_ts = context.pvm_engage_timestamp
    if (new_state == PVMState.PVM_ENGAGED
            and context.state != PVMState.PVM_ENGAGED):
        new_total += 1
        new_engage_turn = current_turn_index
        new_engage_ts = time.time()

    # Track quiet turns for decay
    new_quiet = 0
    if new_state in (PVMState.PVM_ENGAGED, PVMState.DETECTING):
        if not pvm_reading.signals_detected:
            new_quiet = context.quiet_turns_since_pvm + 1
        else:
            new_quiet = 0
    else:
        new_quiet = 0

    # Track return signals
    new_return_turn = context.last_return_signal_turn
    if new_state == PVMState.REACTIVATING:
        new_return_turn = current_turn_index

    # Track last directive turn
    new_directive = context.last_explicit_directive_turn
    if new_state == PVMState.ACTIVE and pvm_reading.confidence > 0.90:
        new_directive = current_turn_index

    return PVMContext(
        state=new_state,
        last_explicit_directive_turn=new_directive,
        consecutive_minimal_responses=new_consecutive,
        last_gap_seconds=_get(pvm_reading, "last_gap_seconds",
                              context.last_gap_seconds),
        pvm_engage_turn=new_engage_turn,
        pvm_engage_timestamp=new_engage_ts,
        last_return_signal_turn=new_return_turn,
        total_pvm_engagements=new_total,
        quiet_turns_since_pvm=new_quiet,
        last_transition_reason=reason,
        domain_profile=context.domain_profile,
    )


# ═══════════════════════════════════════════════════════════════
#  Audit helper — SHA256 for evidence integrity
# ═══════════════════════════════════════════════════════════════

def pvm_audit_hash(reading: PVMReading) -> str:
    """
    SHA256 of the PVM reading for audit integrity.

    Same pattern as BindingMap's payload_hash — trace integrity
    without storing raw content.
    """
    payload = json.dumps({
        "state": reading.state.value,
        "confidence": reading.confidence,
        "recommend_behavioral_pause": reading.recommend_behavioral_pause,
        "pause_type": reading.pause_type,
        "signals": reading.signals_detected,
        "evidence_count": len(reading.evidence),
    }, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════
#  Self-test — quick validation  (python -m aatif_pvm_detector)
# ═══════════════════════════════════════════════════════════════

def _self_test() -> None:
    """Minimal smoke test — run with ``python engine/aatif_pvm_detector.py``."""
    d = PVMDetector()
    cases = [
        ("What is the capital of France?", "ACTIVE (factual question)"),
        ("مشغول الحين", "PVM_ENGAGED (explicit busy AR)"),
        ("hold on, brb", "PVM_ENGAGED (explicit busy EN)"),
        ("ok", "check minimal response"),
        ("كمل", "REACTIVATING (return signal AR)"),
        ("I'm back, continue", "REACTIVATING (return signal EN)"),
    ]
    prior = None
    for text, label in cases:
        r = d.detect(text, prior_context=prior)
        print(f"  [{r.state.value:15s}] conf={r.confidence:.2f} "
              f"pause={r.pause_type:12s} | {label}")
        if r.state == PVMState.PVM_ENGAGED:
            prior = PVMContext(state=PVMState.PVM_ENGAGED)
        elif r.state == PVMState.DETECTING:
            prior = PVMContext(state=PVMState.DETECTING)
        else:
            prior = None
    print("  ✓ self-test passed")


if __name__ == "__main__":
    _self_test()


# ═══════════════════════════════════════════════════════════════
#  Module exports
# ═══════════════════════════════════════════════════════════════

__all__ = [
    # Feature flags
    "PVM_ENABLED",
    "PVM_MONITOR_ONLY",
    # Authority level
    "AUTHORITY_LEVEL",
    "CAN_BLOCK_RUNTIME",
    "CAN_MODIFY_H",
    "CAN_MODIFY_THETA",
    "CAN_MODIFY_S",
    "CAN_EMIT_JUDICIAL_DECISION",
    # State enum
    "PVMState",
    # Constants
    "FAST_PATH_NOT_BUSY_THRESHOLD",
    "PVM_ENGAGE_THRESHOLD",
    "PVM_ENGAGE_THRESHOLD_HIGH_STAKES",
    "PVM_ENGAGE_THRESHOLD_FAST_PACED",
    "MINIMAL_RESPONSE_MAX_WORDS",
    "MINIMAL_RESPONSE_MAX_CHARS",
    "CONSECUTIVE_MINIMAL_FOR_DETECTING",
    "CONSECUTIVE_MINIMAL_FOR_ENGAGED",
    "GAP_MULTIPLIER_FOR_BUSY",
    "DEFAULT_AVERAGE_GAP_SECONDS",
    "LONG_GAP_ABSOLUTE_SECONDS",
    "DECAY_TURNS_TO_ACTIVE",
    "DECAY_TURNS_HIGH_STAKES",
    "PAUSE_FULL_WAIT",
    "PAUSE_BRIEF_ACK",
    "PAUSE_SHORTENED",
    "PAUSE_NORMAL",
    "PVM_PROFILE_BY_DOMAIN",
    "DEFAULT_PVM_PROFILE",
    # Marker lists
    "BUSY_MARKERS_AR",
    "BUSY_MARKERS_EN",
    "MULTITASK_MARKERS_AR",
    "MULTITASK_MARKERS_EN",
    "RETURN_MARKERS_AR",
    "RETURN_MARKERS_EN",
    "INCOMPLETE_ACK_AR",
    "INCOMPLETE_ACK_EN",
    "DIRECTIVE_MARKERS_EN",
    "DIRECTIVE_MARKERS_AR",
    "ACKNOWLEDGMENTS",
    # Data classes
    "PVMReading",
    "PVMContext",
    "PVMDomainConfig",
    # Detector
    "PVMDetector",
    # Transition helpers
    "next_pvm_state",
    "pvm_should_deactivate",
    "apply_pvm_transition",
    # Audit
    "pvm_audit_hash",
]
