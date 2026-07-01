#!/usr/bin/env python3
"""
Unit tests for aatif_pipeline_connector — the production entry point that the
WhatsApp pipeline calls (build_intent_result).

Before this file, the connector had ONLY integration coverage (test_pipeline.py),
which — with no Ollama/bge-m3 in CI — exercises just the regex-fallback path and
leaves the semantic-path translation logic untested. That is the exact code the
paper's S→P→R→Gate story rides on, so it deserves guard tests.

These are unit + guard tests. No Ollama required: the Governor path is exercised
with a hand-built GovernedResponse (a fake Governor), so the translation logic
(GovernedResponse → IntentReading → plan_dict) and the fail-closed high-risk
behaviour are pinned deterministically.

تربية check: these tests protect trajectory-shaping behaviour — they assert that
when the semantic backend is DOWN, high-risk domains fail CLOSED (SAFE_STOP) and
degraded domains carry a LOUD warning. They pin the path, they do not add a filter.

Run:
    python3 -m pytest tests/test_pipeline_connector.py -q
    python3 -m unittest tests.test_pipeline_connector -v
"""

import os
import sys
import unittest
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "engine")
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

import aatif_pipeline_connector as pc  # noqa: E402
from aatif_pipeline_connector import (  # noqa: E402
    build_intent_result,
    IntentResult,
    IntentLayers,
    AnalysisMatrix,
    HIGH_RISK_DOMAINS,
    normalize_text,
    _emotion_from_E,
    _governed_to_reading,
    _detect_surface_intent,
    _detect_hidden_intent,
    _detect_greeting,
    _detect_dialect_simple,
    _assess_risk,
    _assess_confidence,
)
from aatif_governor import GovernedResponse  # noqa: E402
from aatif_intent_engine import IntentReading  # noqa: E402


# ── helpers ──────────────────────────────────────────────────

def make_reading(**kw) -> IntentReading:
    """Minimal IntentReading with sane defaults; override via kwargs."""
    base = dict(
        surface_request="msg",
        deep_intent="none",
        emotional_state="clear",
        emotional_confidence=0.6,
        load_bearing=False,
        cbrn_flag=False,
        override_flag=False,
        governance_intact=True,
        mode="ANSWER",
        ambiguity_score=0.1,
        harm_score=0.1,
        softening_factor=0.8,
        directness=0.9,
        skills_to_activate=[],
        activation_evidence="test",
        dialect_detected="msa",
        time_context="",
        decision="EXECUTE",
        decision_reason="test",
    )
    base.update(kw)
    return IntentReading(**base)


def make_gov(**kw) -> GovernedResponse:
    """Hand-built GovernedResponse for exercising the Governor path."""
    base = dict(final_decision="EXECUTE", blocked=False)
    base.update(kw)
    return GovernedResponse(**base)


class FakeGovernor:
    """Stand-in for AATIFGovernor: .process returns a preset GovernedResponse
    and records the call so we can assert the connector forwards kwargs."""

    def __init__(self, gov_result):
        self._gov_result = gov_result
        self.calls = []

    def process(self, text, *, domain="general", llm_fn=None,
                conversation_id=None):
        self.calls.append(
            dict(text=text, domain=domain, llm_fn=llm_fn,
                 conversation_id=conversation_id)
        )
        return self._gov_result


# ═══════════════════════════════════════════════════════════
#  _emotion_from_E — E band → (state, confidence)
# ═══════════════════════════════════════════════════════════

class TestEmotionFromE(unittest.TestCase):
    def test_bands(self):
        cases = [
            (0.05, "carrying_weight", 0.85),
            (0.15, "carrying_weight", 0.85),   # boundary
            (0.25, "frustrated", 0.70),
            (0.35, "frustrated", 0.70),        # boundary
            (0.45, "clear", 0.60),
            (0.55, "clear", 0.60),             # boundary
            (0.65, "clear", 0.55),
            (0.75, "clear", 0.55),             # boundary
            (0.95, "excited", 0.70),
        ]
        for E, state, conf in cases:
            with self.subTest(E=E):
                got_state, got_conf = _emotion_from_E(E)
                self.assertEqual(got_state, state)
                self.assertAlmostEqual(got_conf, conf)


# ═══════════════════════════════════════════════════════════
#  _governed_to_reading — GovernedResponse → IntentReading
# ═══════════════════════════════════════════════════════════

class TestGovernedToReading(unittest.TestCase):
    def test_clean_execute(self):
        gov = make_gov(
            final_decision="EXECUTE", blocked=False,
            s_result={"H": 0.12, "I": 0.4, "E": 0.5, "S": 0.82},
        )
        r = _governed_to_reading("hello", gov)
        self.assertEqual(r.decision, "EXECUTE")
        self.assertEqual(r.mode, "ANSWER")
        self.assertEqual(r.harm_score, 0.12)
        self.assertEqual(r.softening_factor, 0.82)
        self.assertEqual(r.ambiguity_score, 0.0)
        self.assertIn("cleared by Governor", r.decision_reason)

    def test_clarify_sets_ambiguity_and_stop_mode(self):
        gov = make_gov(
            final_decision="CLARIFY", blocked=False,
            s_result={"H": 0.2, "I": 0.3, "E": 0.5, "S": 0.6},
        )
        r = _governed_to_reading("huh?", gov)
        self.assertEqual(r.decision, "CLARIFY")
        self.assertEqual(r.mode, "STOP")
        self.assertAlmostEqual(r.ambiguity_score, 0.4)
        self.assertIn("clarification", r.decision_reason.lower())

    def test_ambiguity_override_wins(self):
        gov = make_gov(
            final_decision="CLARIFY", blocked=False,
            s_result={"H": 0.2, "S": 0.6, "ambiguity_override": True},
        )
        r = _governed_to_reading("x", gov)
        self.assertAlmostEqual(r.ambiguity_score, 0.6)

    def test_unknown_territory_ambiguity(self):
        gov = make_gov(
            final_decision="EXECUTE", blocked=False,
            s_result={"H": 0.2, "S": 0.6, "unknown_territory": True},
        )
        r = _governed_to_reading("x", gov)
        self.assertAlmostEqual(r.ambiguity_score, 0.5)

    def test_blocked_uses_block_reason_and_flags(self):
        gov = make_gov(
            final_decision="SAFE_FREEZE", blocked=True,
            block_reason="hard override: CBRN",
            s_result={"H": 0.95, "S": 0.02,
                      "hard_override": True, "jailbreak_escalated": True},
        )
        r = _governed_to_reading("bad", gov)
        self.assertEqual(r.mode, "STOP")
        self.assertEqual(r.decision_reason, "hard override: CBRN")
        self.assertTrue(r.cbrn_flag)
        self.assertTrue(r.override_flag)

    def test_load_bearing_from_low_E(self):
        gov = make_gov(s_result={"E": 0.1, "H": 0.1, "S": 0.8})
        r = _governed_to_reading("tired", gov)
        self.assertTrue(r.load_bearing)
        self.assertEqual(r.emotional_state, "carrying_weight")

    def test_missing_s_result_defaults(self):
        gov = make_gov(s_result=None)
        r = _governed_to_reading("x", gov)
        # defaults H=I=E=S=0.5 → clear, not load-bearing
        self.assertEqual(r.harm_score, 0.5)
        self.assertFalse(r.load_bearing)


# ═══════════════════════════════════════════════════════════
#  surface / hidden / risk / confidence classifiers
# ═══════════════════════════════════════════════════════════

class TestClassifiers(unittest.TestCase):
    def test_surface_greeting(self):
        self.assertEqual(
            _detect_surface_intent("مرحبا", make_reading()), "greeting")

    def test_surface_price(self):
        self.assertEqual(
            _detect_surface_intent("كم السعر", make_reading()),
            "price_question")

    def test_surface_identity(self):
        self.assertEqual(
            _detect_surface_intent("من انت", make_reading()),
            "identity_question")
        self.assertEqual(
            _detect_surface_intent("who are you?", make_reading()),
            "identity_question")

    def test_surface_value(self):
        self.assertEqual(
            _detect_surface_intent("وش الفايده", make_reading()),
            "value_question")

    def test_surface_stop_mode_is_ambiguous(self):
        self.assertEqual(
            _detect_surface_intent("xyzzy", make_reading(mode="STOP")),
            "ambiguous")

    def test_surface_default(self):
        self.assertEqual(
            _detect_surface_intent("tell me about widgets", make_reading()),
            "default")

    def test_hidden_needs_support(self):
        self.assertEqual(
            _detect_hidden_intent("x", make_reading(load_bearing=True)),
            "needs_support")

    def test_hidden_trust_check(self):
        self.assertEqual(
            _detect_hidden_intent(
                "x", make_reading(emotional_state="frustrated")),
            "trust_check")

    def test_hidden_ready_to_engage(self):
        self.assertEqual(
            _detect_hidden_intent(
                "x", make_reading(emotional_state="excited")),
            "ready_to_engage")

    def test_hidden_needs_orientation(self):
        self.assertEqual(
            _detect_hidden_intent(
                "x", make_reading(emotional_state="lost")),
            "needs_orientation")

    def test_hidden_none(self):
        self.assertEqual(
            _detect_hidden_intent("x", make_reading()), "none")

    def test_assess_risk_bands(self):
        self.assertEqual(_assess_risk(make_reading(harm_score=0.7)), "high")
        self.assertEqual(_assess_risk(make_reading(harm_score=0.4)), "medium")
        self.assertEqual(_assess_risk(make_reading(harm_score=0.1)), "low")

    def test_assess_confidence_bands(self):
        self.assertEqual(
            _assess_confidence(make_reading(ambiguity_score=0.1)), "high")
        self.assertEqual(
            _assess_confidence(make_reading(ambiguity_score=0.4)), "medium")
        self.assertEqual(
            _assess_confidence(make_reading(ambiguity_score=0.8)), "low")

    def test_dialect_detection(self):
        self.assertEqual(_detect_dialect_simple("ابي أفهم وش السالفة"), "saudi")
        self.assertEqual(_detect_dialect_simple("عايز افهم ازاي"), "egyptian")
        self.assertEqual(_detect_dialect_simple("I want to understand"), "msa")


# ═══════════════════════════════════════════════════════════
#  to_plan_dict — Governor audit-trail attachment
# ═══════════════════════════════════════════════════════════

class TestToPlanDict(unittest.TestCase):
    def test_governor_audit_trail_attached(self):
        gov = make_gov(
            final_decision="EXECUTE", blocked=False,
            stage_reached="STAGE_GATE",
            governed_prompt="PROMPT",
            r_result=SimpleNamespace(
                style_recommendation="warm", r_score=0.42),
            p_result=SimpleNamespace(
                highest_action="ANSWER", has_protocols=True),
            gate_result=SimpleNamespace(
                blocked=False, flags=["OK"], block_reason=""),
            final_response="final text",
            emergency_injected=True,
        )
        reading = make_reading()
        res = IntentResult(
            incoming_text="x", normalized_text="x",
            aatif_reading=reading,
            intent_layers=IntentLayers("default", "none"),
            analysis_matrix=None,
        )
        res._gov_result = gov
        plan = res.to_plan_dict()
        a = plan["aatif"]
        self.assertEqual(a["engine"], "governor")
        self.assertEqual(a["stage_reached"], "STAGE_GATE")
        self.assertFalse(a["blocked"])
        self.assertEqual(a["r_style"], "warm")
        self.assertEqual(a["r_score"], 0.42)
        self.assertEqual(a["p_highest_action"], "ANSWER")
        self.assertTrue(a["p_has_protocols"])
        self.assertEqual(a["governed_prompt"], "PROMPT")
        self.assertFalse(a["gate_blocked"])
        self.assertEqual(a["gate_flags"], ["OK"])
        self.assertEqual(a["final_response"], "final text")
        self.assertTrue(a["emergency_injected"])

    def test_gate_block_reason_surfaced(self):
        gov = make_gov(
            gate_result=SimpleNamespace(
                blocked=True, flags=["X"], block_reason="gate said no"),
        )
        res = IntentResult(
            incoming_text="x", normalized_text="x",
            aatif_reading=make_reading(),
        )
        res._gov_result = gov
        a = res.to_plan_dict()["aatif"]
        self.assertTrue(a["gate_blocked"])
        self.assertEqual(a["gate_block_reason"], "gate said no")

    def test_fallback_engine_marker_when_no_gov(self):
        res = IntentResult(
            incoming_text="x", normalized_text="x",
            aatif_reading=make_reading(),
        )
        # no _gov_result attribute set
        a = res.to_plan_dict()["aatif"]
        self.assertEqual(a["engine"], "intent_engine_fallback")

    def test_degradation_warning_surfaced_top_level(self):
        res = IntentResult(
            incoming_text="x", normalized_text="x",
            aatif_reading=make_reading(),
            degradation_warning="WARN: degraded",
        )
        plan = res.to_plan_dict()
        self.assertEqual(plan["degradation_warning"], "WARN: degraded")


# ═══════════════════════════════════════════════════════════
#  build_intent_result — Governor path (fake) + fallback paths
# ═══════════════════════════════════════════════════════════

class TestBuildIntentResultGovernorPath(unittest.TestCase):
    def setUp(self):
        self._orig = pc._get_governor

    def tearDown(self):
        pc._get_governor = self._orig

    def test_governor_path_forwards_kwargs_and_builds_plan(self):
        gov = make_gov(
            final_decision="EXECUTE", blocked=False,
            stage_reached="STAGE_PROMPT",
            governed_prompt="P",
            s_result={"H": 0.1, "I": 0.4, "E": 0.5, "S": 0.85},
        )
        fake = FakeGovernor(gov)
        pc._get_governor = lambda: fake

        res = build_intent_result(
            "كم السعر", business_type="tech",
            domain="general", conversation_id="c1")
        plan = res.to_plan_dict()

        # kwargs forwarded to the Governor
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0]["domain"], "general")
        self.assertEqual(fake.calls[0]["conversation_id"], "c1")
        # translated plan fields
        self.assertEqual(plan["surface_intent"], "price_question")
        self.assertEqual(plan["aatif"]["engine"], "governor")
        self.assertIsNone(plan.get("degradation_warning"))


class TestBuildIntentResultFallback(unittest.TestCase):
    def setUp(self):
        self._orig = pc._get_governor
        pc._get_governor = lambda: None   # simulate Governor unavailable

    def tearDown(self):
        pc._get_governor = self._orig

    def test_high_risk_domain_fails_closed_safe_stop(self):
        for domain in ("health", "banking", "children", "legal", "emergency"):
            with self.subTest(domain=domain):
                res = build_intent_result(
                    "أحتاج مساعدة", domain=domain)
                plan = res.to_plan_dict()
                self.assertEqual(plan["aatif"]["decision"], "SAFE_STOP")
                self.assertEqual(plan["handling_mode"], "refuse_safely")
                self.assertIn("BLOCKED", plan["degradation_warning"])
                self.assertFalse(res.aatif_reading.governance_intact)

    def test_non_high_risk_domain_degrades_with_warning(self):
        res = build_intent_result("مرحبا", domain="general")
        plan = res.to_plan_dict()
        # regex fallback ran (not a hard SAFE_STOP block)
        self.assertEqual(plan["aatif"]["engine"], "intent_engine_fallback")
        self.assertIn("degraded", plan["degradation_warning"].lower())
        self.assertEqual(plan["surface_intent"], "greeting")

    def test_high_risk_membership_is_frozen(self):
        self.assertIn("healthcare", HIGH_RISK_DOMAINS)
        self.assertIsInstance(HIGH_RISK_DOMAINS, frozenset)


class TestNormalizeTextPublic(unittest.TestCase):
    def test_public_wrapper_matches_private(self):
        raw = "أهلاً بِكَ"
        self.assertEqual(normalize_text(raw), pc._normalize_text(raw))
        # diacritics stripped, alef normalized
        self.assertNotIn("ً", normalize_text(raw))


if __name__ == "__main__":
    unittest.main(verbosity=2)
