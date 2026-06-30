#!/usr/bin/env python3
"""
AATIF Reasoning Trace Engine — طبقة التعليل الذاتي  (Field Note #082)
======================================================================

"إذا عُرِف السبب بطل العجب."
"If the reason is known, the wonder ceases."

A system that cannot explain WHY it made a decision is not governed — it is
just programmed.  Every AATIF decision should trace back to the constitutional
articles (field notes) that justify it.  This module is المحاجج: the Arguer.
It does not generate text.  It connects decisions to their constitutional basis.

HOW IT WORKS
────────────
The engine applies a small set of deterministic rules — PURE LOGIC, no
embeddings, no LLM — that map three kinds of signal to constitutional articles:

  1. Score thresholds — H/I/E/S values above or below key boundaries activate
     specific articles (e.g. elevated H invokes FN#029 Three-Tier Safety).

  2. Decision type — SAFE_FREEZE, SAFE_STOP, BLOCKED, EXECUTE, CLARIFY each
     have a canonical set of articles that justify them.

  3. Context modifiers — domain, protocol_action (EMERGENCY/BLOCK/GUIDE), and
     meta_oversight contradictions each add domain- or situation-specific
     articles.

Output is a ReasoningTrace: the decision, the scores, a list of
ReasoningLinks (each citing one article and explaining WHY it applies here),
and a plain-language summary a human can read without technical knowledge.

BOUNDED CLAIM LAW (FN#069)
───────────────────────────
Per FN#069, the trace ONLY cites articles it can concretely link to the
current decision.  It never cites speculatively.  Maximum 5 articles per
trace — the Bounded Claim Law: every guarantee is testable and bounded.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

# ---------------------------------------------------------------------------
# Ensure the engine directory is importable (same pattern as the other modules)
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


# ═══════════════════════════════════════════════════════════
#  ConstitutionalArticle — a single field note as a constitution article
# ═══════════════════════════════════════════════════════════

@dataclass
class ConstitutionalArticle:
    """One field note encoded as a constitutional article."""
    number: int          # FN number (e.g. 5 for FN#005)
    title: str           # full English title
    slogan: str          # the core principle / slogan
    domain: str          # safety | governance | philosophy | linguistics | architecture
    keywords: List[str]  # for rule-based matching


# ═══════════════════════════════════════════════════════════
#  CONSTITUTIONAL_ARTICLES — the built-in constitution
# ═══════════════════════════════════════════════════════════
#
# Key field notes encoded in canonical form.  Ordered by FN number.
# The Governor cites these; external callers may inject a custom list.

CONSTITUTIONAL_ARTICLES: List[ConstitutionalArticle] = [
    # ── Architecture layer ──────────────────────────────────
    ConstitutionalArticle(
        number=1,
        title="The Successful Failure Principle",
        slogan="The cheapest correct response is a clear question.",
        domain="architecture",
        keywords=["clarify", "ambiguous", "stop_mode", "question"],
    ),
    # ── Safety layer ────────────────────────────────────────
    ConstitutionalArticle(
        number=3,
        title="The Compass Principle (Reverse-LLM)",
        slogan="Intelligence is not constrained — it is directed.",
        domain="philosophy",
        keywords=["direction", "values", "compass", "reverse_llm"],
    ),
    ConstitutionalArticle(
        number=5,
        title="Mercy as the Operating Principle",
        slogan="Mercy is not kindness. Mercy is the truth that actually helps.",
        domain="safety",
        keywords=["mercy", "harm", "emotion", "vulnerability", "care"],
    ),
    # ── Governance layer ────────────────────────────────────
    ConstitutionalArticle(
        number=14,
        title="The Responsible Authority Doctrine",
        slogan="The system acts. The authority decides.",
        domain="governance",
        keywords=["authority", "governance", "block", "sovereignty"],
    ),
    # ── Safety layer ────────────────────────────────────────
    ConstitutionalArticle(
        number=16,
        title="Truth With Mercy Delivery",
        slogan="Truth stays intact. Delivery adapts.",
        domain="safety",
        keywords=["truth", "style", "delivery", "adapts", "tone"],
    ),
    # ── Governance layer ────────────────────────────────────
    ConstitutionalArticle(
        number=17,
        title="The Constitutional Priority Hierarchy",
        slogan="When everything conflicts, the hierarchy decides.",
        domain="governance",
        keywords=["priority", "hierarchy", "conflict", "decision"],
    ),
    # ── Safety layer ────────────────────────────────────────
    ConstitutionalArticle(
        number=29,
        title="The Three-Tier Safety Escalation System",
        slogan="Safety is not a switch. It is a scale.",
        domain="safety",
        keywords=["safe_freeze", "safe_stop", "escalation", "harm", "threshold"],
    ),
    ConstitutionalArticle(
        number=30,
        title="The Reality-First Principle",
        slogan="Theoretically correct is not enough. Humanly useful is the standard.",
        domain="safety",
        keywords=["reality", "emergency", "healthcare", "practical", "useful"],
    ),
    # ── Governance layer ────────────────────────────────────
    ConstitutionalArticle(
        number=31,
        title="The Meta-Oversight Engine",
        slogan="Every engine thinks. The Meta Engine watches the thinking.",
        domain="governance",
        keywords=["meta_oversight", "contradiction", "self_review", "coherence"],
    ),
    ConstitutionalArticle(
        number=34,
        title="The Governance Trace Artifact",
        slogan="Every output leaves a trace of how it was made.",
        domain="governance",
        keywords=["trace", "audit", "record", "governance", "accountability"],
    ),
    # ── Architecture layer ──────────────────────────────────
    ConstitutionalArticle(
        number=44,
        title="The Eight-Channel Binding Architecture",
        slogan="Layers do not talk freely. Each signal travels its own wire.",
        domain="architecture",
        keywords=["binding", "architecture", "layers", "channels"],
    ),
    # ── Governance layer ────────────────────────────────────
    ConstitutionalArticle(
        number=45,
        title="The Safety-First Boot Sequence",
        slogan="Nothing outputs until initialization completes — in order.",
        domain="governance",
        keywords=["boot", "initialization", "sequence", "order", "safety_first"],
    ),
    # ── Safety layer ────────────────────────────────────────
    ConstitutionalArticle(
        number=49,
        title="The False Goodness Detector (FGD)",
        slogan="Not everything that sounds like care — is.",
        domain="safety",
        keywords=["false_goodness", "disguised", "virtue", "caring", "deceptive"],
    ),
    ConstitutionalArticle(
        number=52,
        title="The Moral Drift Prevention Engine",
        slogan="Drift is not a single wrong turn. It is a thousand small compromises.",
        domain="safety",
        keywords=["drift", "moral", "gradual", "accumulation", "safe_stop"],
    ),
    # ── Architecture layer ──────────────────────────────────
    ConstitutionalArticle(
        number=55,
        title="The Architected Scientific Framing Layer (ASF)",
        slogan="Results first. Definitions before debate. Ontology last.",
        domain="architecture",
        keywords=["scientific", "framing", "claims", "bounded", "evidence"],
    ),
    # ── Governance layer ────────────────────────────────────
    ConstitutionalArticle(
        number=67,
        title="The Pressure-Reveal Principle (Non-Compressible Honesty)",
        slogan="Understanding emerges only through exposure to failure, refusal, and reset.",
        domain="governance",
        keywords=["pressure", "honesty", "refusal", "non_compressible", "block"],
    ),
    ConstitutionalArticle(
        number=69,
        title="The Bounded Claim Law (ACN-01)",
        slogan="No metaphysical absolutes. All guarantees are system-bounded and testable.",
        domain="governance",
        keywords=["bounded", "claims", "testable", "audit", "guarantees"],
    ),
    # ── Linguistics layer ────────────────────────────────────
    ConstitutionalArticle(
        number=75,
        title="Lexical Anchor Contamination Effect",
        slogan="The anchor matched the word, not the meaning.",
        domain="linguistics",
        keywords=["anchor", "lexical", "semantic", "arabic", "overlap"],
    ),
    ConstitutionalArticle(
        number=78,
        title="Arabic-First Embedding Hypothesis",
        slogan="Arabic is the origin of meaning. Other languages are translations.",
        domain="linguistics",
        keywords=["arabic", "embedding", "arabic_first", "dialect", "language"],
    ),
    ConstitutionalArticle(
        number=79,
        title="The Tailor Principle: Fixed Design, Variable Fit",
        slogan="The design is fixed. The fit adjusts.",
        domain="linguistics",
        keywords=["tailor", "dialect", "fit", "adapt", "style", "arabic"],
    ),
    # ── Governance / constitution layer ─────────────────────
    ConstitutionalArticle(
        number=82,
        title="Field Notes as Living Constitution",
        slogan="If the reason is known, the wonder ceases.",
        domain="governance",
        keywords=["constitution", "reasoning", "trace", "why", "justification"],
    ),
]

# Fast lookup by article number.
_ARTICLE_BY_NUMBER = {a.number: a for a in CONSTITUTIONAL_ARTICLES}


# ═══════════════════════════════════════════════════════════
#  ReasoningLink — one link in a reasoning chain
# ═══════════════════════════════════════════════════════════

@dataclass
class ReasoningLink:
    """One field note cited in a reasoning trace, with WHY it applies."""
    article_number: int
    article_title: str
    relevance: str   # why this article applies to this specific decision
    confidence: float  # 0-1, how strongly the article applies


# ═══════════════════════════════════════════════════════════
#  ReasoningTrace — the full trace for one decision
# ═══════════════════════════════════════════════════════════

@dataclass
class ReasoningTrace:
    """
    Full constitutional basis for one AATIF decision.

    constitutional_basis is ordered: highest-confidence articles first.
    reasoning_summary is plain language — a human should understand it
    without knowing any AATIF internals.
    """
    decision: str           # EXECUTE | CLARIFY | SAFE_STOP | SAFE_FREEZE | BLOCKED
    h_score: float
    i_score: float
    e_score: float
    s_score: float
    constitutional_basis: List[ReasoningLink]
    reasoning_summary: str
    timestamp: str          # ISO-8601 UTC


# ═══════════════════════════════════════════════════════════
#  Score thresholds — mirrors the Governor / S-equation calibration
# ═══════════════════════════════════════════════════════════

_H_HIGH = 0.70     # H ≥ this → SAFE_FREEZE territory
_H_ELEVATED = 0.40 # H ≥ this → elevated harm signal (SAFE_STOP territory)
_E_HIGH = 0.65     # E ≥ this → strong emotional signal

# Maximum articles per trace — Bounded Claim Law (FN#069).
_MAX_ARTICLES = 5


# ═══════════════════════════════════════════════════════════
#  ReasoningTraceEngine — المحاجج
# ═══════════════════════════════════════════════════════════

class ReasoningTraceEngine:
    """
    Connects AATIF decisions to their constitutional basis in the field notes.

    Pure logic — no embeddings, no LLM, no I/O.  Deterministic and fast.

    Usage:
        engine = ReasoningTraceEngine()
        trace = engine.trace(
            decision="SAFE_FREEZE",
            h=0.85, i=0.30, e=0.20, s=0.85,
            domain="healthcare",
        )
        print(trace.reasoning_summary)
    """

    def __init__(
        self,
        articles: Optional[List[ConstitutionalArticle]] = None,
    ) -> None:
        src = articles if articles is not None else CONSTITUTIONAL_ARTICLES
        self._by_number = {a.number: a for a in src}

    # ───────────────────────────────────────────────────
    #  Public API
    # ───────────────────────────────────────────────────

    def trace(
        self,
        decision: str,
        h: float,
        i: float,
        e: float,
        s: float,
        domain: str = "general",
        protocol_action: Optional[str] = None,
        meta_oversight_result=None,
    ) -> ReasoningTrace:
        """
        Build a constitutional reasoning trace for a Governor decision.

        Args:
            decision: the final decision string (EXECUTE, CLARIFY, SAFE_STOP,
                SAFE_FREEZE, BLOCKED).
            h, i, e, s: the H, I, E, S scores from S(d).
            domain: the request domain (healthcare, education, general, …).
            protocol_action: the highest P(d) protocol action (None, ACTION_NONE,
                ACTION_EMERGENCY, ACTION_BLOCK, …).
            meta_oversight_result: the MetaOversightResult (or None).  When
                present, contradictions it found add relevant articles.

        Returns:
            ReasoningTrace with up to _MAX_ARTICLES constitutional links,
            ordered by confidence (highest first).
        """
        # Each rule returns (article_number, relevance_text, confidence).
        # We collect all candidates and keep the top-N unique articles.
        candidates: list[tuple[int, str, float]] = []

        # Rule set — order doesn't affect the final result because we sort by
        # confidence and deduplicate, but we organise them logically.

        # 1. This trace itself cites FN#082 (the constitution principle).
        candidates.append((
            82,
            "Every AATIF decision is traceable to its constitutional basis (FN#082).",
            0.95,
        ))

        # 2. Decision type → primary safety articles.
        candidates.extend(self._rules_decision(decision, h, i, e, s))

        # 3. Score thresholds → score-specific articles.
        candidates.extend(self._rules_scores(h, i, e, s))

        # 4. Domain → domain-specific articles.
        candidates.extend(self._rules_domain(domain, decision))

        # 5. Protocol action → protocol-specific articles.
        if protocol_action:
            candidates.extend(self._rules_protocol(protocol_action))

        # 6. Meta-oversight contradictions → oversight-specific articles.
        if meta_oversight_result is not None:
            candidates.extend(self._rules_oversight(meta_oversight_result))

        # Bounded Claim Law: deduplicate by article number, keep highest
        # confidence for each, then take the top-N.
        seen: dict[int, tuple[str, float]] = {}
        for num, relevance, conf in candidates:
            if num not in self._by_number:
                continue  # article not in this engine's corpus
            if num not in seen or conf > seen[num][1]:
                seen[num] = (relevance, conf)

        # Sort by confidence descending, then apply the hard cap.
        ranked = sorted(seen.items(), key=lambda kv: kv[1][1], reverse=True)
        ranked = ranked[:_MAX_ARTICLES]

        links: List[ReasoningLink] = []
        for num, (relevance, conf) in ranked:
            art = self._by_number[num]
            links.append(ReasoningLink(
                article_number=num,
                article_title=art.title,
                relevance=relevance,
                confidence=round(conf, 3),
            ))

        summary = self._build_summary(decision, h, i, e, s, domain, links)

        return ReasoningTrace(
            decision=decision,
            h_score=round(h, 4),
            i_score=round(i, 4),
            e_score=round(e, 4),
            s_score=round(s, 4),
            constitutional_basis=links,
            reasoning_summary=summary,
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

    # ───────────────────────────────────────────────────
    #  Rule sets — each returns a list of (number, relevance, confidence)
    # ───────────────────────────────────────────────────

    def _rules_decision(
        self, decision: str, h: float, i: float, e: float, s: float,
    ) -> list[tuple[int, str, float]]:
        """Articles that apply based on the decision type alone."""
        out = []

        if decision == "SAFE_FREEZE":
            out.append((
                29,
                "H score crossed the maximum-caution threshold; the three-tier "
                "escalation system mandates SAFE_FREEZE — full halt, no LLM.",
                0.95,
            ))
            out.append((
                17,
                "Constitutional priority hierarchy: when safety and utility "
                "conflict, safety wins.  SAFE_FREEZE is the highest-safety tier.",
                0.85,
            ))
            out.append((
                52,
                "Moral Drift Prevention: once the harm threshold is crossed the "
                "system must stop immediately, not negotiate.",
                0.70,
            ))

        elif decision == "SAFE_STOP":
            out.append((
                29,
                "H score elevated; the three-tier safety system escalates to "
                "SAFE_STOP — human guidance required before proceeding.",
                0.90,
            ))
            out.append((
                5,
                "Mercy operates at the safety tier: stopping is the most merciful "
                "response when the request approaches harm.",
                0.75,
            ))

        elif decision == "BLOCKED":
            out.append((
                14,
                "The Responsible Authority Doctrine: the governing authority "
                "(domain protocol) has issued a BLOCK — the system must enforce it.",
                0.90,
            ))
            out.append((
                67,
                "Non-Compressible Honesty: when a block is warranted, the system "
                "does not compress or soften the refusal — it enforces it.",
                0.80,
            ))

        elif decision == "CLARIFY":
            out.append((
                1,
                "Successful Failure Principle: the input is ambiguous.  The "
                "cheapest correct response is a clear clarifying question.",
                0.90,
            ))
            out.append((
                5,
                "Mercy requires not acting on misunderstood intent — one question "
                "now prevents a wrong response later.",
                0.70,
            ))

        elif decision == "EXECUTE":
            out.append((
                16,
                "Truth With Mercy: the request cleared safety thresholds; the "
                "system responds with truth adapted to the context.",
                0.80,
            ))
            out.append((
                17,
                "Constitutional hierarchy satisfied: safety, governance, and style "
                "layers all cleared.  Execution is authorised.",
                0.75,
            ))

        return out

    def _rules_scores(
        self, h: float, i: float, e: float, s: float,
    ) -> list[tuple[int, str, float]]:
        """Articles triggered by specific score ranges."""
        out = []

        if h >= _H_HIGH:
            out.append((
                29,
                f"H={h:.2f} exceeds the SAFE_FREEZE threshold ({_H_HIGH}).  "
                f"Three-Tier Safety Escalation mandates maximum caution.",
                0.95,
            ))
            out.append((
                49,
                f"High H score ({h:.2f}) may indicate harm disguised as care — "
                f"False Goodness Detector flags are relevant at this level.",
                0.65,
            ))

        elif h >= _H_ELEVATED:
            out.append((
                29,
                f"H={h:.2f} is elevated (above {_H_ELEVATED}).  "
                f"Three-Tier Safety Escalation activates precautionary protocols.",
                0.80,
            ))

        if e >= _E_HIGH:
            out.append((
                5,
                f"E={e:.2f} shows high emotional intensity.  Mercy requires "
                f"acknowledging emotional state before any substantive response.",
                0.75,
            ))
            out.append((
                30,
                f"Reality-First Principle: high emotional load ({e:.2f}) means "
                f"the humanly useful response must address the emotion, not just the facts.",
                0.65,
            ))

        # Governance trace is always relevant — every output leaves a trace.
        out.append((
            34,
            f"Governance Trace Artifact: this trace documents how decision "
            f"'{s:.2f}' was reached so it can be audited and reproduced.",
            0.85,
        ))

        return out

    def _rules_domain(
        self, domain: str, decision: str,
    ) -> list[tuple[int, str, float]]:
        """Articles triggered by specific domains."""
        out = []
        domain_lower = domain.lower()

        if domain_lower == "healthcare":
            out.append((
                30,
                "Reality-First Principle: healthcare requests require humanly "
                "useful responses.  Emergency signals must be surfaced immediately.",
                0.85,
            ))
            out.append((
                5,
                "Mercy as Operating Principle: in healthcare, mercy means surfacing "
                "truth that protects the person, not comfortable approximations.",
                0.80,
            ))

        elif domain_lower == "education":
            out.append((
                5,
                "Mercy in education: the system protects students' safety while "
                "respecting their right to learn.",
                0.75,
            ))
            out.append((
                55,
                "Architected Scientific Framing: educational responses must be "
                "accurate, bounded, and not overstate confidence.",
                0.65,
            ))

        elif domain_lower in ("creative", "general"):
            out.append((
                16,
                "Truth With Mercy: in open-ended domains, style adapts to context "
                "while substantive accuracy is preserved.",
                0.65,
            ))

        # Arabic / dialect-heavy contexts.
        if domain_lower in ("general", "creative", "ecommerce"):
            out.append((
                79,
                "Tailor Principle: the design is fixed but the linguistic fit "
                "adjusts to the user's dialect and register.",
                0.60,
            ))

        return out

    def _rules_protocol(
        self, protocol_action: str,
    ) -> list[tuple[int, str, float]]:
        """Articles triggered by domain protocol actions."""
        out = []
        action_upper = (protocol_action or "").upper()

        if "EMERGENCY" in action_upper:
            out.append((
                30,
                "Reality-First Principle: an EMERGENCY protocol is active — the "
                "response MUST open with immediate, humanly useful safety guidance.",
                0.95,
            ))
            out.append((
                5,
                "Mercy requires prioritising the person's immediate safety above "
                "all other response quality concerns.",
                0.85,
            ))

        if "BLOCK" in action_upper:
            out.append((
                14,
                "Responsible Authority Doctrine: a protocol BLOCK represents an "
                "authoritative governance decision that the system must enforce.",
                0.90,
            ))
            out.append((
                67,
                "Non-Compressible Honesty: the refusal is non-negotiable — "
                "pressure does not compress a legitimate block.",
                0.80,
            ))

        if "GUIDE" in action_upper or "DISCLAIMER" in action_upper:
            out.append((
                16,
                "Truth With Mercy: the protocol requires a clarifying guide or "
                "disclaimer — truth is delivered with appropriate context.",
                0.75,
            ))

        return out

    def _rules_oversight(
        self, oversight_result,
    ) -> list[tuple[int, str, float]]:
        """Articles triggered by meta-oversight contradictions."""
        out = []

        # Always cite FN#031 when the Meta-Oversight Engine ran.
        out.append((
            31,
            "Meta-Oversight Engine ran and detected a cross-engine signal — "
            "self-review is part of every governed pipeline pass.",
            0.85,
        ))

        # Check for contradictions or overrides.
        contradictions = getattr(oversight_result, "contradictions", None) or []
        requires_override = getattr(oversight_result, "requires_override", False)
        severity = getattr(oversight_result, "severity", "")

        if requires_override:
            out.append((
                17,
                "Constitutional Priority Hierarchy: meta-oversight escalated the "
                "decision because a cross-engine contradiction demanded resolution.",
                0.80,
            ))

        if contradictions:
            # Style contradiction → FN#016 (Truth With Mercy Delivery).
            style_contradictions = [
                c for c in contradictions
                if "style" in str(getattr(c, "description", "")).lower()
                or "style" in str(getattr(c, "contradiction_type", "")).lower()
            ]
            if style_contradictions:
                out.append((
                    16,
                    "Truth With Mercy Delivery: meta-oversight found a style "
                    "contradiction — tone must be coherent with the safety context.",
                    0.75,
                ))

            # Safety contradictions → FN#029 (Three-Tier Safety).
            safety_contradictions = [
                c for c in contradictions
                if "safety" in str(getattr(c, "description", "")).lower()
                or "safety" in str(getattr(c, "contradiction_type", "")).lower()
                or "CRITICAL" in str(getattr(c, "severity", "")).upper()
            ]
            if safety_contradictions or severity == "CRITICAL":
                out.append((
                    29,
                    "Three-Tier Safety Escalation: meta-oversight identified a "
                    "CRITICAL safety contradiction and escalated toward caution.",
                    0.90,
                ))

        return out

    # ───────────────────────────────────────────────────
    #  Plain-language summary
    # ───────────────────────────────────────────────────

    def _build_summary(
        self,
        decision: str,
        h: float,
        i: float,
        e: float,
        s: float,
        domain: str,
        links: List[ReasoningLink],
    ) -> str:
        """
        One-sentence plain-language explanation of the decision.

        A human should understand this without knowing AATIF internals.
        """
        top_articles = ", ".join(
            f"FN#{ln.article_number}" for ln in links[:3]
        )

        if decision == "SAFE_FREEZE":
            return (
                f"The request was halted immediately (harm score {h:.2f} exceeded "
                f"the maximum-caution threshold) — constitutional articles "
                f"{top_articles} require a full stop with no response generated."
            )

        if decision == "SAFE_STOP":
            return (
                f"The request was stopped for human review (harm score {h:.2f} is "
                f"elevated) — constitutional articles {top_articles} require "
                f"human guidance before proceeding."
            )

        if decision == "BLOCKED":
            return (
                f"The request was blocked by a domain governance rule — "
                f"constitutional articles {top_articles} authorise the governing "
                f"authority to issue non-negotiable refusals."
            )

        if decision == "CLARIFY":
            return (
                f"The request was ambiguous — constitutional articles {top_articles} "
                f"prescribe asking one clarifying question rather than acting on "
                f"incomplete information."
            )

        # EXECUTE
        return (
            f"The request cleared all safety and governance thresholds in the "
            f"{domain} domain — constitutional articles {top_articles} authorise "
            f"a response calibrated to truth, mercy, and context."
        )
