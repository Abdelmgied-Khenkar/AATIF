#!/usr/bin/env python3
"""
AATIF المُحاجج — Anticipatory Logic + Audience-Adapted Justification
(Field Notes #026 + #060)
======================================================================

FN#026 — The Anticipatory Logic Protocol (ULP):
  "Don't react to the argument. Anticipate it — and keep all paths open."
  When a user argues or challenges, the system keeps multiple response paths
  and can elevate the frame rather than defending a single position.

FN#060 — The Universal Debate & Justification Engine (UDJE):
  "UDJE is not persuasion. UDJE is structured clarity."
  The same truth presented through 5 audience channels without changing
  the content — only the form.
  "Never compromise content for palatability. Never hide structure to
  appear simpler."

Together they form المُحاجج: the layer that:
  (1) generates alternative response paths when blocking/clarifying, and
  (2) adapts the explanation style to the audience without changing the
      underlying truth.

KEY DESIGN CONSTRAINTS
──────────────────────
  • Pure logic — no embeddings, no LLM, no I/O.  Template-based, deterministic.
  • Content invariance: the TRUTH does not change across channels — only
    the presentation.  All channels for the same decision reference the same
    core facts (H score, threshold, reason).
  • Frame elevation is NOT manipulation: it provides a broader perspective.
    It never hides or distorts the underlying reason.
  • Alternative paths must ALL be safe — never suggest paths that bypass safety.
  • Bounded: never more than 3 alternative paths (_MAX_PATHS).
  • Persuasion boundary: per FN#060, we explain — we do not sell.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import os
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
#  Constants
# ═══════════════════════════════════════════════════════════

# Threshold mirrors — calibrated to match S-equation defaults.
# These are cited in templates so users understand the numeric basis.
_THETA_SAFE_STOP = 0.40    # default harm threshold for SAFE_STOP
_THETA_SAFE_FREEZE = 0.70  # maximum-caution threshold for SAFE_FREEZE

# Bounded: never more than 3 alternative paths (spec requirement).
_MAX_PATHS = 3

# Argumentative language signals — any match triggers frame elevation.
# FN#026: "Don't react to the argument. Anticipate it."
_ARGUMENT_SIGNALS: list[str] = [
    # English
    "but why", "that's wrong", "you're wrong", "i disagree",
    "why not", "unfair", "this is unfair", "this is wrong",
    "explain yourself", "not right", "wrong decision", "incorrect",
    "i don't accept", "don't accept", "i refuse", "unreasonable",
    "this makes no sense", "doesn't make sense",
    # Arabic
    "بس ليش", "ليش ما", "هذا غلط", "مو صح", "ما أوافق",
    "لماذا لا", "هذا مو عدل", "غلط", "مو صحيح", "غير صحيح",
    "اشرح لي", "أثبت", "مو منطقي", "غير منطقي",
    "لماذا ترفض", "مو عادل", "رافض", "مش صح", "مش عادل",
]


# ═══════════════════════════════════════════════════════════
#  AudienceChannel — the 5 explanation channels (FN#060)
# ═══════════════════════════════════════════════════════════

class AudienceChannel(Enum):
    """The five audience channels from FN#060.

    Each channel presents the SAME truth in a different form:
      - SCIENTIFIC_TECHNICAL: researchers, developers, analysts
      - HUMANITARIAN_ETHICAL: values-oriented, care-focused audiences
      - ARCHITECTURAL_CONCEPTUAL: designers, system thinkers, architects
      - PRACTICAL_APPLIED: managers, businesses, operations
      - CULTURAL_SOCIAL: general public, community members, officials
    """
    SCIENTIFIC_TECHNICAL = "scientific_technical"
    HUMANITARIAN_ETHICAL = "humanitarian_ethical"
    ARCHITECTURAL_CONCEPTUAL = "architectural_conceptual"
    PRACTICAL_APPLIED = "practical_applied"
    CULTURAL_SOCIAL = "cultural_social"


# ═══════════════════════════════════════════════════════════
#  ResponsePath — one alternative response approach (FN#026)
# ═══════════════════════════════════════════════════════════

@dataclass
class ResponsePath:
    """One possible alternative approach the user could take.

    All paths are ALWAYS safe (is_safe=True) — the system never suggests
    alternatives that would bypass safety. is_active tracks whether this
    path is currently viable (e.g., not already tried / not blocked by context).
    """
    path_id: int
    approach: str   # brief description of the approach
    frame: str      # the framing / perspective used
    is_safe: bool = True    # MUST always be True — safety invariant
    is_active: bool = True  # currently viable


# ═══════════════════════════════════════════════════════════
#  JustificationResult — the full justification output
# ═══════════════════════════════════════════════════════════

@dataclass
class JustificationResult:
    """The audience-adapted justification for one AATIF governance decision.

    Fields:
        decision: the S decision being justified (SAFE_STOP, CLARIFY, etc.)
        primary_justification: main explanation text in the selected channel's form
        audience_channel: which of the 5 channels was selected
        alternative_paths: 0–3 safe alternative approaches the user could take
        frame_elevation: when the user is arguing, the elevated principle-level
            frame (None when no argumentative language detected)
        constitutional_basis: FN article numbers that support this justification
    """
    decision: str
    primary_justification: str
    audience_channel: AudienceChannel
    alternative_paths: List[ResponsePath] = field(default_factory=list)
    frame_elevation: Optional[str] = None
    constitutional_basis: List[int] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
#  Justification templates
# ═══════════════════════════════════════════════════════════
#
# CONTENT INVARIANCE (FN#060): all channels for the same decision reference
# the same core facts (H score, threshold, same reason for stopping).
# The form differs; the truth does not.
#
# Slot variables available in each template:
#   {h}     — harm score (float, formatted by caller)
#   {theta} — threshold (float, derived from decision type)
#
# Format specifiers used:
#   {h:.2f}  — harm score to 2 decimal places   (SCIENTIFIC, ARCHITECTURAL, PRACTICAL)
#   {h:.0%}  — harm score as percentage          (HUMANITARIAN, CULTURAL_SOCIAL)
#             These are the SAME value, different presentations — not different truths.

_TEMPLATES: dict[str, dict[AudienceChannel, str]] = {
    # ── SAFE_STOP ──────────────────────────────────────────
    "SAFE_STOP": {
        AudienceChannel.SCIENTIFIC_TECHNICAL: (
            "The harm score (H={h:.2f}) exceeded the threshold θ={theta:.2f}. "
            "The request contains patterns matching high-harm safety anchors. "
            "The multiplicative safety gate activates SAFE_STOP when H ≥ θ, "
            "overriding permissive intent/emotion scores. "
            "Consider rephrasing to separate the informational component from "
            "the operational application that triggered the flag."
        ),
        AudienceChannel.HUMANITARIAN_ETHICAL: (
            "This request raised safety concerns because it touches on content "
            "that could lead to harm (risk level: {h:.0%}). "
            "Stopping here is the most merciful response — it protects both you "
            "and others. This is not a judgment about you. "
            "We want to help: here are some ways to rephrase."
        ),
        AudienceChannel.ARCHITECTURAL_CONCEPTUAL: (
            "The governance equation S(d) produced a SAFE_STOP signal. "
            "H={h:.2f} exceeded threshold θ={theta:.2f}. "
            "The multiplicative gate structure ensures that an elevated H score "
            "overrides permissive I/E scores — this is constitutional design "
            "(FN#029): safety is a hard constraint, not a factor to be balanced."
        ),
        AudienceChannel.PRACTICAL_APPLIED: (
            "Request paused. Harm score: {h:.2f} (threshold: {theta:.2f}). "
            "Available actions: "
            "(1) Rephrase to clarify your specific informational need. "
            "(2) Provide more context about your use case and purpose. "
            "(3) Ask about a related but more specific aspect."
        ),
        AudienceChannel.CULTURAL_SOCIAL: (
            "وقفنا هذا الطلب لأن مستوى المخاطر وصل {h:.0%}. "
            "مو رفض ليك — هو حماية للجميع. "
            "حاول تعيد صياغة سؤالك بطريقة أوضح، "
            "أو أخبرنا أكثر عن هدفك الحقيقي."
        ),
    },
    # ── SAFE_FREEZE ────────────────────────────────────────
    "SAFE_FREEZE": {
        AudienceChannel.SCIENTIFIC_TECHNICAL: (
            "The harm score (H={h:.2f}) exceeded the maximum-caution threshold "
            "(θ={theta:.2f}). Full pipeline halt executed (SAFE_FREEZE). "
            "No partial path through the pipeline is safe at this harm level. "
            "A completely rephrased request is required."
        ),
        AudienceChannel.HUMANITARIAN_ETHICAL: (
            "This request reached the highest safety level ({h:.0%} risk). "
            "A full stop was necessary to prevent serious harm. "
            "This is not a personal judgment — it is a protection for everyone. "
            "A completely new approach is needed."
        ),
        AudienceChannel.ARCHITECTURAL_CONCEPTUAL: (
            "SAFE_FREEZE is the terminal state of the three-tier safety escalation "
            "(FN#029). H={h:.2f} exceeded the maximum threshold θ={theta:.2f}. "
            "The architecture makes no provision for partial processing at this level. "
            "Safety sovereignty is absolute above this threshold."
        ),
        AudienceChannel.PRACTICAL_APPLIED: (
            "Full stop. Harm level: {h:.2f} (maximum threshold: {theta:.2f}). "
            "Required action: submit a completely new request that removes "
            "all high-harm content patterns."
        ),
        AudienceChannel.CULTURAL_SOCIAL: (
            "وقفنا هذا الطلب بالكامل. مستوى الخطر ({h:.0%}) عالٍ جداً. "
            "هذا مو رفض شخصي — هو حماية ضرورية للجميع. "
            "نحتاج طلباً جديداً كلياً بصياغة مختلفة تماماً."
        ),
    },
    # ── BLOCKED ────────────────────────────────────────────
    "BLOCKED": {
        AudienceChannel.SCIENTIFIC_TECHNICAL: (
            "A domain protocol issued a BLOCK action (H={h:.2f}). "
            "The governing authority rule overrides the S(d) score. "
            "This block is non-negotiable per the constitutional hierarchy (FN#014). "
            "Rephrasing to address only the permitted aspects may be viable."
        ),
        AudienceChannel.HUMANITARIAN_ETHICAL: (
            "This request was blocked by a governance rule designed to protect "
            "people in this domain (risk level: {h:.0%}). "
            "The rule exists because similar requests have caused real harm. "
            "We can help with related questions that stay within safe boundaries."
        ),
        AudienceChannel.ARCHITECTURAL_CONCEPTUAL: (
            "A domain protocol action BLOCK was enforced by the Governor (FN#014). "
            "P(d) BLOCK overrides S(d) EXECUTE/CLARIFY at H={h:.2f} — "
            "the protocol authority is above the S-equation in the constitutional "
            "hierarchy. No exception path exists in the architecture."
        ),
        AudienceChannel.PRACTICAL_APPLIED: (
            "Request blocked by domain governance rules (harm score: {h:.2f}). "
            "Options: (1) Rephrase to focus on the permitted aspects. "
            "(2) Contact support for special authorization. "
            "(3) Review the domain guidelines for what is allowed."
        ),
        AudienceChannel.CULTURAL_SOCIAL: (
            "هذا الطلب محظور حسب قواعد هذا المجال (مستوى الخطر: {h:.0%}). "
            "القاعدة موجودة لحماية الجميع. "
            "يمكنك المحاولة بصياغة مختلفة تركز على الجانب المسموح به."
        ),
    },
    # ── CLARIFY ────────────────────────────────────────────
    # FN#001: "The cheapest correct response is a clear question."
    "CLARIFY": {
        AudienceChannel.SCIENTIFIC_TECHNICAL: (
            "Input ambiguity detected. Proceeding on an unclear input risks "
            "generating a response calibrated to an incorrect interpretation. "
            "Required for disambiguation: (1) specific intent, "
            "(2) domain or context, (3) expected output format or scope. "
            "One clarifying question is the constitutionally correct action (FN#001)."
        ),
        AudienceChannel.HUMANITARIAN_ETHICAL: (
            "We want to help you fully, and a little more information will "
            "let us do that well. There is no judgment here — "
            "we just want to understand what you actually need "
            "so we can give a response that genuinely helps."
        ),
        AudienceChannel.ARCHITECTURAL_CONCEPTUAL: (
            "The SFC (Successful Fail Closure) protocol activated (FN#001). "
            "Ambiguous inputs route to the CLARIFY path — "
            "one targeted question is cheaper than a wrong full response. "
            "Required context: goal, constraints, domain."
        ),
        AudienceChannel.PRACTICAL_APPLIED: (
            "Clarification needed before proceeding. Please specify: "
            "(1) exactly what you need, "
            "(2) the context or use case, "
            "(3) any constraints or requirements."
        ),
        AudienceChannel.CULTURAL_SOCIAL: (
            "نحتاج نفهم أكثر عشان نساعدك صح. "
            "ما فيه رفض — فقط محتاجين نعرف: ما هو بالضبط اللي تريده؟ "
            "وش هو هدفك؟"
        ),
    },
    # ── EXECUTE ────────────────────────────────────────────
    # Minimal justification — no explanation needed for normal flow.
    "EXECUTE": {
        AudienceChannel.SCIENTIFIC_TECHNICAL: (
            "Request cleared all safety thresholds. Proceeding."
        ),
        AudienceChannel.HUMANITARIAN_ETHICAL: (
            "Request cleared. Proceeding."
        ),
        AudienceChannel.ARCHITECTURAL_CONCEPTUAL: (
            "S(d) EXECUTE: all governance gates passed. Proceeding."
        ),
        AudienceChannel.PRACTICAL_APPLIED: (
            "Request cleared. Proceeding."
        ),
        AudienceChannel.CULTURAL_SOCIAL: (
            "طلبك وصل. جاري المعالجة."
        ),
    },
}


# ═══════════════════════════════════════════════════════════
#  Alternative paths by decision type
# ═══════════════════════════════════════════════════════════
#
# All paths are SAFE (is_safe=True invariant).
# Maximum _MAX_PATHS = 3 (spec requirement).
# Never suggest paths that could bypass safety.

_ALTERNATIVE_PATHS: dict[str, list[dict]] = {
    "SAFE_STOP": [
        {
            "approach": (
                "Rephrase to focus on the informational aspect, "
                "removing operational application details."
            ),
            "frame": "information_only",
        },
        {
            "approach": (
                "Provide more context about your specific use case, "
                "purpose, and intended audience."
            ),
            "frame": "context_provision",
        },
        {
            "approach": (
                "Break your question into smaller, more specific parts "
                "that address one aspect at a time."
            ),
            "frame": "decomposition",
        },
    ],
    "SAFE_FREEZE": [
        {
            "approach": (
                "Submit a completely new request that addresses a different, "
                "safer aspect of your underlying need."
            ),
            "frame": "fresh_start",
        },
        {
            "approach": (
                "Contact a qualified professional or relevant authority "
                "for this type of request."
            ),
            "frame": "expert_referral",
        },
    ],
    "BLOCKED": [
        {
            "approach": (
                "Rephrase to focus only on the permitted aspects of the topic."
            ),
            "frame": "permitted_scope",
        },
        {
            "approach": (
                "Reach out to support for guidance on what is allowed "
                "in this domain."
            ),
            "frame": "support_escalation",
        },
    ],
    "CLARIFY": [
        {
            "approach": (
                "Add specific details: who needs this, what for, "
                "in what context, and with what constraints."
            ),
            "frame": "specificity",
        },
        {
            "approach": (
                "Specify the domain or field you are asking about "
                "and the audience you are addressing."
            ),
            "frame": "domain_context",
        },
        {
            "approach": (
                "Tell us the outcome you are trying to achieve, "
                "not just the question you are asking."
            ),
            "frame": "goal_clarification",
        },
    ],
    "EXECUTE": [],
}


# ═══════════════════════════════════════════════════════════
#  Frame elevation templates (FN#026)
# ═══════════════════════════════════════════════════════════
#
# Used when user is arguing / challenging.
# Rule-level  → "the policy says X"
# Principle-level → "the underlying principle is X because..."
#
# Frame elevation is NOT manipulation — it provides a broader perspective
# without hiding or distorting the underlying reason.

_FRAME_ELEVATION: dict[str, Optional[str]] = {
    "SAFE_STOP": (
        "The underlying principle here is not an arbitrary policy — "
        "it is that content with elevated harm potential (H={h:.2f}) "
        "requires human oversight before any action is taken. "
        "This protects real people in ways that cannot be undone. "
        "The system is not refusing you; it is preserving the space "
        "where both of us can operate safely."
    ),
    "SAFE_FREEZE": (
        "The principle is absolute: some harm levels are too high for "
        "automated processing, regardless of stated intent. "
        "H={h:.2f} exceeded the maximum threshold. "
        "This is not a judgment about you — it is a structural commitment "
        "that the architecture was designed never to negotiate around, "
        "because the cost of a mistake at this level is irreversible."
    ),
    "BLOCKED": (
        "The underlying principle is that some domains have hard governance "
        "boundaries because experience showed what happens when those "
        "boundaries are not consistently enforced. "
        "The rule exists to protect, not to restrict arbitrarily. "
        "The governing authority defines those boundaries; this system "
        "enforces them with full fidelity."
    ),
    "CLARIFY": (
        "The principle here is: a system that acts on an ambiguous request "
        "and gets it wrong causes more harm than one that pauses to ask. "
        "One clarifying question is not a failure — it is the responsible "
        "path, and it keeps all possibilities open until we understand "
        "exactly what you need."
    ),
    "EXECUTE": None,
}


# ═══════════════════════════════════════════════════════════
#  Constitutional basis by decision and channel
# ═══════════════════════════════════════════════════════════
#
# FN#026 (Anticipatory Logic) and FN#060 (UDJE) are always cited —
# they are the foundational articles for this module itself.

_BASIS_BY_DECISION: dict[str, list[int]] = {
    "SAFE_STOP":   [26, 60, 29, 5],
    "SAFE_FREEZE": [26, 60, 29, 17, 52],
    "BLOCKED":     [26, 60, 14, 67],
    "CLARIFY":     [26, 60, 1, 5],
    "EXECUTE":     [26, 60, 16],
}

# Additional articles activated by specific audience channels.
_BASIS_BY_CHANNEL: dict[AudienceChannel, list[int]] = {
    AudienceChannel.SCIENTIFIC_TECHNICAL:    [69],       # Bounded Claim Law
    AudienceChannel.HUMANITARIAN_ETHICAL:    [5],        # Mercy as Operating Principle
    AudienceChannel.ARCHITECTURAL_CONCEPTUAL: [44, 34],  # Architecture + Trace Artifact
    AudienceChannel.PRACTICAL_APPLIED:       [],
    AudienceChannel.CULTURAL_SOCIAL:         [79],       # Tailor Principle
}


# ═══════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════

def _is_argumentative(message: str) -> bool:
    """Return True if the message contains argumentative language signals.

    Used by AlMuhajij.justify() to decide whether to add frame elevation.
    Case-insensitive substring match — quick and dependency-free.
    """
    if not message:
        return False
    msg_lower = message.lower()
    return any(signal in msg_lower for signal in _ARGUMENT_SIGNALS)


def _build_basis(decision_upper: str, channel: AudienceChannel) -> list[int]:
    """Merge constitutional basis from decision type + channel, deduplicated."""
    basis = list(_BASIS_BY_DECISION.get(decision_upper, [26, 60]))
    for n in _BASIS_BY_CHANNEL.get(channel, []):
        if n not in basis:
            basis.append(n)
    # Deduplicate while preserving order
    seen: set[int] = set()
    deduped: list[int] = []
    for n in basis:
        if n not in seen:
            seen.add(n)
            deduped.append(n)
    return deduped


# ═══════════════════════════════════════════════════════════
#  AlMuhajij — المُحاجج
# ═══════════════════════════════════════════════════════════

class AlMuhajij:
    """
    المُحاجج — The Arguer.

    Implements FN#026 (Anticipatory Logic Protocol) + FN#060 (Universal Debate
    & Justification Engine). Produces audience-adapted justification for AATIF
    governance decisions without changing the underlying truth.

    Design principles:
      • Structured clarity, NOT persuasion — same truth, different form.
      • Content invariance — all channels reference the same core facts.
      • Frame elevation — when user argues, elevate from rule-level to
        principle-level. Never hide or distort.
      • Alternative paths — always safe, bounded to _MAX_PATHS.
      • Lightweight — template-based, no I/O, negligible overhead.

    Usage:
        muhajij = AlMuhajij()
        result = muhajij.justify(
            decision="SAFE_STOP",
            h=0.55,
            s=0.55,
            domain="general",
            user_message="but why can't you help me?",
        )
        print(result.primary_justification)
        print(result.frame_elevation)
    """

    def __init__(self, articles: list = None) -> None:
        """
        Args:
            articles: optional list of ConstitutionalArticle objects (e.g. from
                ReasoningTrace). When present, their article numbers are available
                for cross-referencing. The module works without them.
        """
        self._articles = articles or []
        # Extract known article numbers for cross-reference (duck-typed, no import)
        self._known_numbers: set[int] = {
            getattr(a, "number", None) for a in self._articles
        } - {None}

    def justify(
        self,
        decision: str,
        h: float,
        s: float,
        domain: str = "general",
        user_message: str = "",
        protocol_action: str = None,
        audience: AudienceChannel = None,
    ) -> JustificationResult:
        """
        Generate a JustificationResult for an AATIF governance decision.

        Args:
            decision: EXECUTE | CLARIFY | SAFE_STOP | SAFE_FREEZE | BLOCKED
            h: harm score from S(d)
            s: final S(d) score
            domain: request domain (for context only — not alters logic)
            user_message: the original user message, used for argument detection
            protocol_action: the highest P(d) protocol action (optional)
            audience: target audience channel. When None, defaults to
                CULTURAL_SOCIAL — the safest, most accessible channel.

        Returns:
            JustificationResult. Never raises; graceful on unknown decisions.
        """
        # Default audience: CULTURAL_SOCIAL (safest, most accessible)
        if audience is None:
            audience = AudienceChannel.CULTURAL_SOCIAL

        # Normalize decision — defensive; graceful fallback for unexpected values.
        decision_upper = (decision or "EXECUTE").upper()
        if decision_upper not in _TEMPLATES:
            decision_upper = "SAFE_STOP"  # conservative fallback

        # Derive threshold from decision type.
        theta = (
            _THETA_SAFE_FREEZE if decision_upper == "SAFE_FREEZE" else _THETA_SAFE_STOP
        )

        # ── EXECUTE: minimal justification, no alternatives, no frame ──
        if decision_upper == "EXECUTE":
            return JustificationResult(
                decision=decision,
                primary_justification=_TEMPLATES["EXECUTE"][audience],
                audience_channel=audience,
                alternative_paths=[],
                frame_elevation=None,
                constitutional_basis=_build_basis("EXECUTE", audience),
            )

        # ── Primary justification — slot-fill the channel template ──
        template = _TEMPLATES[decision_upper][audience]
        primary = template.format(h=h, theta=theta)

        # ── Alternative paths — all safe, bounded to _MAX_PATHS ──
        paths_data = _ALTERNATIVE_PATHS.get(decision_upper, [])
        alternative_paths: list[ResponsePath] = [
            ResponsePath(
                path_id=i + 1,
                approach=p["approach"],
                frame=p["frame"],
                is_safe=True,   # safety invariant — never False
                is_active=True,
            )
            for i, p in enumerate(paths_data[:_MAX_PATHS])
        ]

        # ── Frame elevation (FN#026) — triggers on argumentative language ──
        frame_elevation: Optional[str] = None
        if user_message and _is_argumentative(user_message):
            fe_template = _FRAME_ELEVATION.get(decision_upper)
            if fe_template:
                frame_elevation = fe_template.format(h=h, theta=theta)

        # ── Constitutional basis ──
        constitutional_basis = _build_basis(decision_upper, audience)

        return JustificationResult(
            decision=decision,
            primary_justification=primary,
            audience_channel=audience,
            alternative_paths=alternative_paths,
            frame_elevation=frame_elevation,
            constitutional_basis=constitutional_basis,
        )
