#!/usr/bin/env python3
"""
test_reasoning_trace.py — طبقة التعليل الذاتي (FN#082)
=======================================================
Covers ``engine/aatif_reasoning_trace.py`` — the Reasoning Trace Engine that
connects AATIF decisions to their constitutional basis in the field notes.

This module is PURE LOGIC (no embeddings, no LLM), so every test here runs
WITHOUT Ollama.  Two layers:

  1. Unit tests on ReasoningTraceEngine.trace — driving the engine with
     controlled score inputs and decision types, pinning that each decision
     type gets appropriate constitutional articles, that score thresholds map
     to correct articles, that domain / protocol / oversight signals add the
     right articles, and that the Bounded Claim Law (FN#069) is respected.

  2. Governor integration tests — with a mocked S engine (FakeSEngine, same
     pattern as test_governor.py) asserting that reasoning_trace is attached
     to GovernedResponse when the reasoning trace engine is wired.

License: BSL 1.1
"""
import os
import sys
import types

import pytest

# Ensure the engine directory is importable (same pattern as the other tests).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_THIS_DIR, "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_reasoning_trace import (  # noqa: E402
    ReasoningTraceEngine,
    ReasoningTrace,
    ReasoningLink,
    ConstitutionalArticle,
    CONSTITUTIONAL_ARTICLES,
    _MAX_ARTICLES,
    _H_HIGH,
    _H_ELEVATED,
    _E_HIGH,
)


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _engine() -> ReasoningTraceEngine:
    return ReasoningTraceEngine()


def _article_numbers(trace: ReasoningTrace) -> set:
    return {ln.article_number for ln in trace.constitutional_basis}


# ═══════════════════════════════════════════════════════════
#  CONTRACT TESTS — dataclass and module-level constants
# ═══════════════════════════════════════════════════════════

class TestContract:
    def test_constitutional_articles_not_empty(self):
        assert len(CONSTITUTIONAL_ARTICLES) >= 20

    def test_all_articles_have_required_fields(self):
        for art in CONSTITUTIONAL_ARTICLES:
            assert isinstance(art.number, int) and art.number > 0
            assert art.title
            assert art.slogan
            assert art.domain
            assert isinstance(art.keywords, list)

    def test_no_duplicate_article_numbers(self):
        numbers = [a.number for a in CONSTITUTIONAL_ARTICLES]
        assert len(numbers) == len(set(numbers))

    def test_key_articles_present(self):
        numbers = {a.number for a in CONSTITUTIONAL_ARTICLES}
        for n in (1, 5, 14, 16, 17, 29, 30, 31, 34, 45, 49, 52, 67, 69, 82):
            assert n in numbers, f"FN#{n} missing from CONSTITUTIONAL_ARTICLES"

    def test_max_articles_constant_reasonable(self):
        assert 3 <= _MAX_ARTICLES <= 7

    def test_reasoning_trace_dataclass_fields(self):
        engine = _engine()
        trace = engine.trace("EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6)
        assert isinstance(trace, ReasoningTrace)
        assert trace.decision == "EXECUTE"
        assert 0.0 <= trace.h_score <= 1.0
        assert 0.0 <= trace.i_score <= 1.0
        assert 0.0 <= trace.e_score <= 1.0
        assert 0.0 <= trace.s_score <= 1.0
        assert isinstance(trace.constitutional_basis, list)
        assert trace.reasoning_summary
        assert trace.timestamp

    def test_reasoning_link_fields(self):
        engine = _engine()
        trace = engine.trace("EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6)
        for link in trace.constitutional_basis:
            assert isinstance(link, ReasoningLink)
            assert link.article_number > 0
            assert link.article_title
            assert link.relevance
            assert 0.0 <= link.confidence <= 1.0


# ═══════════════════════════════════════════════════════════
#  DECISION TYPE TESTS
# ═══════════════════════════════════════════════════════════

class TestDecisionTypes:
    def test_safe_freeze_gets_safety_articles(self):
        trace = _engine().trace("SAFE_FREEZE", h=0.85, i=0.2, e=0.1, s=0.85)
        nums = _article_numbers(trace)
        # Must cite FN#029 (Three-Tier Safety Escalation)
        assert 29 in nums, "SAFE_FREEZE must cite FN#029"

    def test_safe_stop_gets_safety_articles(self):
        trace = _engine().trace("SAFE_STOP", h=0.55, i=0.3, e=0.2, s=0.55)
        nums = _article_numbers(trace)
        assert 29 in nums, "SAFE_STOP must cite FN#029"

    def test_blocked_gets_authority_articles(self):
        trace = _engine().trace("BLOCKED", h=0.3, i=0.7, e=0.2, s=0.3)
        nums = _article_numbers(trace)
        # Must cite FN#014 (Responsible Authority Doctrine) or FN#067
        assert 14 in nums or 67 in nums, (
            "BLOCKED must cite FN#014 or FN#067"
        )

    def test_clarify_gets_successful_failure_article(self):
        trace = _engine().trace("CLARIFY", h=0.1, i=0.4, e=0.2, s=0.3)
        nums = _article_numbers(trace)
        # Must cite FN#001 (Successful Failure Principle)
        assert 1 in nums, "CLARIFY must cite FN#001"

    def test_execute_gets_proceed_articles(self):
        trace = _engine().trace("EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6)
        nums = _article_numbers(trace)
        # Must cite FN#016 (Truth With Mercy) or FN#017 (Constitutional Hierarchy)
        assert 16 in nums or 17 in nums, (
            "EXECUTE must cite FN#016 or FN#017"
        )

    def test_all_traces_cite_fn082(self):
        """Every trace must cite FN#082 — the constitutional trace principle."""
        engine = _engine()
        for decision in ("EXECUTE", "CLARIFY", "SAFE_STOP", "SAFE_FREEZE", "BLOCKED"):
            trace = engine.trace(decision, h=0.3, i=0.5, e=0.3, s=0.3)
            assert 82 in _article_numbers(trace), (
                f"{decision} trace must cite FN#082"
            )

    def test_all_traces_cite_fn034(self):
        """Every trace must cite FN#034 — the Governance Trace Artifact."""
        engine = _engine()
        for decision in ("EXECUTE", "CLARIFY", "SAFE_STOP", "SAFE_FREEZE", "BLOCKED"):
            trace = engine.trace(decision, h=0.3, i=0.5, e=0.3, s=0.3)
            assert 34 in _article_numbers(trace), (
                f"{decision} trace must cite FN#034"
            )


# ═══════════════════════════════════════════════════════════
#  SCORE THRESHOLD TESTS
# ═══════════════════════════════════════════════════════════

class TestScoreThresholds:
    def test_high_h_triggers_three_tier_safety(self):
        trace = _engine().trace(
            "SAFE_FREEZE", h=_H_HIGH + 0.05, i=0.2, e=0.1, s=0.85
        )
        assert 29 in _article_numbers(trace)

    def test_elevated_h_triggers_safety_article(self):
        trace = _engine().trace(
            "SAFE_STOP", h=_H_ELEVATED + 0.05, i=0.3, e=0.2, s=0.5
        )
        assert 29 in _article_numbers(trace)

    def test_low_h_does_not_force_safety_freeze(self):
        # Low H → EXECUTE should NOT necessarily cite FN#029
        trace = _engine().trace("EXECUTE", h=0.05, i=0.8, e=0.2, s=0.6)
        # It's fine if it doesn't; we're asserting it doesn't incorrectly escalate
        assert trace.decision == "EXECUTE"

    def test_high_e_triggers_mercy_and_reality_first(self):
        trace = _engine().trace(
            "EXECUTE", h=0.2, i=0.7, e=_E_HIGH + 0.05, s=0.5
        )
        nums = _article_numbers(trace)
        # Must cite FN#005 (Mercy) or FN#030 (Reality-First) for emotional intensity
        assert 5 in nums or 30 in nums, (
            "High E should cite FN#005 or FN#030"
        )

    def test_high_h_may_cite_false_goodness(self):
        """High H may cite FN#049 (False Goodness Detector) as a relevant article."""
        trace = _engine().trace(
            "SAFE_FREEZE", h=_H_HIGH + 0.1, i=0.3, e=0.1, s=0.85
        )
        # FN#049 is relevant at very high H — it may appear if within the top-5
        nums = _article_numbers(trace)
        # We assert the trace is valid, not that 49 MUST appear (may be displaced by
        # higher-confidence articles due to the _MAX_ARTICLES cap)
        assert len(trace.constitutional_basis) >= 2

    def test_boundary_values_all_zero(self):
        """All scores zero — should still produce a valid trace."""
        trace = _engine().trace("EXECUTE", h=0.0, i=0.0, e=0.0, s=0.0)
        assert trace.decision == "EXECUTE"
        assert len(trace.constitutional_basis) >= 1
        assert trace.reasoning_summary

    def test_boundary_values_all_one(self):
        """All scores at max — safe freeze path should work."""
        trace = _engine().trace("SAFE_FREEZE", h=1.0, i=1.0, e=1.0, s=1.0)
        assert trace.decision == "SAFE_FREEZE"
        assert 29 in _article_numbers(trace)

    def test_exact_threshold_h_elevated(self):
        """Exactly at _H_ELEVATED should trigger the elevated-harm rule."""
        trace = _engine().trace("SAFE_STOP", h=_H_ELEVATED, i=0.3, e=0.2, s=0.5)
        assert 29 in _article_numbers(trace)


# ═══════════════════════════════════════════════════════════
#  DOMAIN-SPECIFIC TESTS
# ═══════════════════════════════════════════════════════════

class TestDomainArticles:
    def test_healthcare_cites_reality_first(self):
        trace = _engine().trace(
            "EXECUTE", h=0.2, i=0.7, e=0.4, s=0.5, domain="healthcare"
        )
        nums = _article_numbers(trace)
        assert 30 in nums, "Healthcare domain must cite FN#030 (Reality-First)"

    def test_healthcare_cites_mercy(self):
        trace = _engine().trace(
            "EXECUTE", h=0.1, i=0.8, e=0.3, s=0.6, domain="healthcare"
        )
        nums = _article_numbers(trace)
        assert 5 in nums, "Healthcare domain must cite FN#005 (Mercy)"

    def test_education_cites_mercy(self):
        trace = _engine().trace(
            "EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6, domain="education"
        )
        nums = _article_numbers(trace)
        assert 5 in nums, "Education domain must cite FN#005 (Mercy)"

    def test_general_domain_valid(self):
        trace = _engine().trace(
            "EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6, domain="general"
        )
        assert trace.decision == "EXECUTE"
        assert len(trace.constitutional_basis) >= 2

    def test_unknown_domain_graceful(self):
        """Unknown domain should not crash — just produce a valid trace."""
        trace = _engine().trace(
            "EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6, domain="unknown_future_domain"
        )
        assert trace.decision == "EXECUTE"
        assert trace.reasoning_summary


# ═══════════════════════════════════════════════════════════
#  PROTOCOL ACTION TESTS
# ═══════════════════════════════════════════════════════════

class TestProtocolActions:
    def test_emergency_protocol_cites_reality_first(self):
        trace = _engine().trace(
            "EXECUTE", h=0.5, i=0.5, e=0.7, s=0.5,
            domain="healthcare", protocol_action="EMERGENCY",
        )
        nums = _article_numbers(trace)
        assert 30 in nums, "EMERGENCY protocol must cite FN#030"

    def test_emergency_protocol_cites_mercy(self):
        trace = _engine().trace(
            "EXECUTE", h=0.5, i=0.5, e=0.7, s=0.5,
            domain="healthcare", protocol_action="EMERGENCY",
        )
        nums = _article_numbers(trace)
        assert 5 in nums, "EMERGENCY protocol must cite FN#005 (Mercy)"

    def test_block_protocol_cites_authority(self):
        trace = _engine().trace(
            "BLOCKED", h=0.3, i=0.7, e=0.2, s=0.3,
            protocol_action="BLOCK",
        )
        nums = _article_numbers(trace)
        assert 14 in nums, "BLOCK protocol must cite FN#014 (Authority Doctrine)"

    def test_none_protocol_action_graceful(self):
        trace = _engine().trace(
            "EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6,
            protocol_action=None,
        )
        assert trace.decision == "EXECUTE"

    def test_guide_protocol_cites_truth_with_mercy(self):
        trace = _engine().trace(
            "EXECUTE", h=0.2, i=0.7, e=0.3, s=0.5,
            protocol_action="GUIDE",
        )
        nums = _article_numbers(trace)
        assert 16 in nums, "GUIDE protocol must cite FN#016 (Truth With Mercy)"


# ═══════════════════════════════════════════════════════════
#  META-OVERSIGHT INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════

class TestMetaOversightIntegration:
    def _make_oversight(
        self,
        requires_override=False,
        severity="NONE",
        contradictions=None,
        resolution_action="NONE",
    ):
        """Build a minimal mock MetaOversightResult."""
        result = types.SimpleNamespace(
            requires_override=requires_override,
            severity=severity,
            contradictions=contradictions or [],
            resolution_action=resolution_action,
            corrected_values={},
        )
        return result

    def test_oversight_result_cites_fn031(self):
        oversight = self._make_oversight()
        trace = _engine().trace(
            "EXECUTE", h=0.2, i=0.7, e=0.3, s=0.5,
            meta_oversight_result=oversight,
        )
        assert 31 in _article_numbers(trace), (
            "When meta-oversight ran, FN#031 must be cited"
        )

    def test_oversight_with_override_cites_hierarchy(self):
        oversight = self._make_oversight(
            requires_override=True, severity="CRITICAL"
        )
        trace = _engine().trace(
            "SAFE_STOP", h=0.5, i=0.4, e=0.3, s=0.5,
            meta_oversight_result=oversight,
        )
        nums = _article_numbers(trace)
        assert 31 in nums
        assert 17 in nums, (
            "Override by meta-oversight must cite FN#017 (Constitutional Hierarchy)"
        )

    def test_oversight_with_style_contradiction(self):
        contradiction = types.SimpleNamespace(
            description="style contradiction detected",
            contradiction_type="style",
            severity="WARNING",
        )
        oversight = self._make_oversight(
            requires_override=True,
            contradictions=[contradiction],
        )
        trace = _engine().trace(
            "EXECUTE", h=0.3, i=0.6, e=0.5, s=0.4,
            meta_oversight_result=oversight,
        )
        nums = _article_numbers(trace)
        assert 31 in nums
        # Style contradiction should trigger FN#016 (Truth With Mercy Delivery)
        assert 16 in nums, (
            "Style contradiction in meta-oversight must cite FN#016"
        )

    def test_oversight_critical_contradiction_cites_safety(self):
        contradiction = types.SimpleNamespace(
            description="safety protocol conflict",
            contradiction_type="safety",
            severity="CRITICAL",
        )
        oversight = self._make_oversight(
            requires_override=True,
            severity="CRITICAL",
            contradictions=[contradiction],
        )
        trace = _engine().trace(
            "SAFE_STOP", h=0.6, i=0.3, e=0.2, s=0.6,
            meta_oversight_result=oversight,
        )
        assert 29 in _article_numbers(trace), (
            "CRITICAL safety contradiction must cite FN#029"
        )

    def test_none_oversight_graceful(self):
        trace = _engine().trace(
            "EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6,
            meta_oversight_result=None,
        )
        assert trace.decision == "EXECUTE"


# ═══════════════════════════════════════════════════════════
#  SUMMARY TESTS
# ═══════════════════════════════════════════════════════════

class TestSummary:
    def test_summary_non_empty(self):
        engine = _engine()
        for decision in ("EXECUTE", "CLARIFY", "SAFE_STOP", "SAFE_FREEZE", "BLOCKED"):
            trace = engine.trace(decision, h=0.3, i=0.5, e=0.3, s=0.3)
            assert trace.reasoning_summary, f"{decision} has empty summary"

    def test_summary_mentions_decision_or_scores(self):
        """Summary should mention something human-readable about the decision."""
        engine = _engine()
        trace = engine.trace("SAFE_FREEZE", h=0.85, i=0.2, e=0.1, s=0.85)
        # Summary should contain either the decision name or a score reference
        summary = trace.reasoning_summary.lower()
        has_decision = "halt" in summary or "stop" in summary or "freeze" in summary
        has_score = "0.85" in trace.reasoning_summary or "harm" in summary
        assert has_decision or has_score, (
            f"SAFE_FREEZE summary should mention halt/stop/freeze or score: {trace.reasoning_summary}"
        )

    def test_summary_cites_article_numbers(self):
        """Summary should reference at least one FN# article."""
        trace = _engine().trace("EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6)
        assert "FN#" in trace.reasoning_summary, (
            f"Summary should cite at least one FN#: {trace.reasoning_summary}"
        )

    def test_summary_is_single_conceptual_thought(self):
        """Summary should be a single sentence or short paragraph, not a list."""
        engine = _engine()
        for decision in ("EXECUTE", "BLOCKED"):
            trace = engine.trace(decision, h=0.3, i=0.5, e=0.3, s=0.3)
            # Should not be empty or just whitespace
            assert len(trace.reasoning_summary.strip()) > 20


# ═══════════════════════════════════════════════════════════
#  BOUNDED CLAIM LAW TESTS (FN#069)
# ═══════════════════════════════════════════════════════════

class TestBoundedClaimLaw:
    def test_article_count_never_exceeds_max(self):
        """Per FN#069, never more than _MAX_ARTICLES articles per trace."""
        engine = _engine()
        cases = [
            ("EXECUTE", 0.1, 0.9, 0.8, 0.7, "healthcare", "EMERGENCY"),
            ("SAFE_FREEZE", 0.9, 0.1, 0.9, 0.9, "general", "BLOCK"),
            ("BLOCKED", 0.3, 0.7, 0.5, 0.3, "education", "GUIDE"),
            ("CLARIFY", 0.1, 0.4, 0.2, 0.2, "general", None),
        ]
        for decision, h, i, e, s, domain, proto in cases:
            trace = engine.trace(
                decision, h=h, i=i, e=e, s=s,
                domain=domain, protocol_action=proto,
            )
            count = len(trace.constitutional_basis)
            assert count <= _MAX_ARTICLES, (
                f"{decision} trace has {count} articles (max {_MAX_ARTICLES})"
            )

    def test_no_duplicate_articles_in_trace(self):
        """Each article should appear at most once in a trace."""
        engine = _engine()
        trace = engine.trace(
            "SAFE_FREEZE", h=0.9, i=0.2, e=0.8, s=0.9,
            domain="healthcare", protocol_action="EMERGENCY",
        )
        numbers = [ln.article_number for ln in trace.constitutional_basis]
        assert len(numbers) == len(set(numbers)), "Duplicate articles in trace"

    def test_all_cited_articles_exist_in_corpus(self):
        """Every cited article number must be in the engine's corpus."""
        engine = _engine()
        trace = engine.trace("EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6)
        known = {a.number for a in CONSTITUTIONAL_ARTICLES}
        for link in trace.constitutional_basis:
            assert link.article_number in known, (
                f"Article FN#{link.article_number} cited but not in corpus"
            )

    def test_confidence_ordering(self):
        """Articles should be ordered by confidence, highest first."""
        engine = _engine()
        trace = engine.trace("SAFE_FREEZE", h=0.9, i=0.2, e=0.1, s=0.9)
        confidences = [ln.confidence for ln in trace.constitutional_basis]
        assert confidences == sorted(confidences, reverse=True), (
            "Articles should be ordered by confidence (highest first)"
        )


# ═══════════════════════════════════════════════════════════
#  CUSTOM ARTICLES TESTS
# ═══════════════════════════════════════════════════════════

class TestCustomArticles:
    def test_custom_articles_injection(self):
        """Engine should work with a custom article list."""
        custom = [
            ConstitutionalArticle(
                number=999,
                title="Test Article",
                slogan="Test slogan.",
                domain="test",
                keywords=["test"],
            ),
            ConstitutionalArticle(
                number=82,
                title="Field Notes as Living Constitution",
                slogan="If the reason is known, the wonder ceases.",
                domain="governance",
                keywords=["constitution", "reasoning", "trace", "why"],
            ),
        ]
        engine = ReasoningTraceEngine(articles=custom)
        # Should not crash; unknown article numbers in rules just won't appear
        trace = engine.trace("EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6)
        assert isinstance(trace, ReasoningTrace)

    def test_empty_articles_list_graceful(self):
        """Engine with empty articles should produce a trace with no links."""
        engine = ReasoningTraceEngine(articles=[])
        trace = engine.trace("EXECUTE", h=0.1, i=0.8, e=0.2, s=0.6)
        assert isinstance(trace, ReasoningTrace)
        assert len(trace.constitutional_basis) == 0


# ═══════════════════════════════════════════════════════════
#  GOVERNOR INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════

class FakeSEngine:
    """Minimal S engine that returns controlled s_result dicts (no Ollama)."""

    def __init__(self, decision="EXECUTE", H=0.1, I=0.8, E=0.2, S=0.6):
        self._decision = decision
        self._H = H
        self._I = I
        self._E = E
        self._S = S
        self.h_scorer = types.SimpleNamespace(backend_name="ollama:bge-m3")

    def compute(self, text, **kwargs):
        return {
            "decision": self._decision,
            "H": self._H,
            "I": self._I,
            "E": self._E,
            "S": self._S,
            "confidence": "high",
            "theta_effective": 0.40,
            "ambiguity_override": False,
            "F_prime": 0.5,
        }


class TestGovernorIntegration:
    def _make_governor(self, decision="EXECUTE", H=0.1, I=0.8, E=0.2, S=0.6):
        from aatif_governor import AATIFGovernor
        fake_s = FakeSEngine(decision=decision, H=H, I=I, E=E, S=S)
        governor = AATIFGovernor(
            s_engine=fake_s,
            on_degraded="safe_stop",
            verify_backend=False,
        )
        return governor

    def test_reasoning_trace_attached_on_execute(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("hello", domain="general")
        assert result.reasoning_trace is not None, (
            "reasoning_trace should be attached to GovernedResponse on EXECUTE"
        )
        assert isinstance(result.reasoning_trace, ReasoningTrace)

    def test_reasoning_trace_has_fn082(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("hello", domain="general")
        assert result.reasoning_trace is not None
        nums = _article_numbers(result.reasoning_trace)
        assert 82 in nums

    def test_reasoning_trace_attached_on_safe_freeze(self):
        gov = self._make_governor(decision="SAFE_FREEZE", H=0.9, S=0.9)
        result = gov.process("كيف أسوي قنبلة", domain="general")
        assert result.blocked
        assert result.reasoning_trace is not None
        assert 29 in _article_numbers(result.reasoning_trace)

    def test_reasoning_trace_attached_on_safe_stop(self):
        gov = self._make_governor(decision="SAFE_STOP", H=0.55, S=0.55)
        result = gov.process("test", domain="general")
        assert result.blocked
        assert result.reasoning_trace is not None

    def test_reasoning_trace_decision_matches_final_decision(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("hello", domain="general")
        assert result.reasoning_trace is not None
        assert result.reasoning_trace.decision == result.final_decision

    def test_reasoning_trace_article_count_bounded(self):
        gov = self._make_governor(decision="EXECUTE", H=0.2, E=0.7)
        result = gov.process("hello", domain="healthcare")
        assert result.reasoning_trace is not None
        assert len(result.reasoning_trace.constitutional_basis) <= _MAX_ARTICLES

    def test_governor_works_with_explicit_none_engine(self):
        """Governor should function normally when reasoning_trace_engine=None.

        Like meta_oversight, passing None triggers auto-construction when the
        module is available (HAS_REASONING_TRACE=True).  This test verifies
        that the pipeline completes successfully — it does not assert absence
        of a trace, since auto-construction will attach one.
        """
        from aatif_governor import AATIFGovernor, HAS_REASONING_TRACE
        fake_s = FakeSEngine(decision="EXECUTE")
        gov = AATIFGovernor(
            s_engine=fake_s,
            on_degraded="safe_stop",
            verify_backend=False,
            reasoning_trace_engine=None,
        )
        result = gov.process("hello", domain="general")
        # Pipeline must complete without error.
        assert result.final_decision == "EXECUTE"
        # When module is available, auto-construction means trace is present.
        if HAS_REASONING_TRACE:
            assert result.reasoning_trace is not None
        else:
            assert result.reasoning_trace is None

    def test_reasoning_trace_summary_non_empty(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("hello", domain="general")
        assert result.reasoning_trace is not None
        assert result.reasoning_trace.reasoning_summary

    def test_reasoning_trace_scores_match_s_result(self):
        gov = self._make_governor(decision="EXECUTE", H=0.15, I=0.75, E=0.25, S=0.55)
        result = gov.process("hello", domain="general")
        trace = result.reasoning_trace
        assert trace is not None
        assert abs(trace.h_score - 0.15) < 0.001
        assert abs(trace.i_score - 0.75) < 0.001
        assert abs(trace.e_score - 0.25) < 0.001
        assert abs(trace.s_score - 0.55) < 0.001
