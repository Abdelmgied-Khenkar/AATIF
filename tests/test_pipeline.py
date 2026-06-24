#!/usr/bin/env python3
"""
Integration test: message -> pipeline connector -> plan_dict.

C1+C2: the pipeline connector now routes through AATIFGovernor (semantic
S→P→R→Gate pipeline) when Ollama is available, falling back to the regex
AATIFIntentEngine otherwise. Both paths produce a valid plan_dict.

Tests the full chain that the WhatsApp pipeline uses:
  1. Raw message string comes in
  2. aatif_pipeline_connector.build_intent_result() runs Governor or fallback
  3. Result is converted to plan_dict for downstream consumption

Run:
    python3 -m unittest tests.test_pipeline -v
"""


import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "engine")
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)


from aatif_pipeline_connector import build_intent_result, _get_governor




class TestPipelineIntegration(unittest.TestCase):
    """End-to-end: message -> connector -> plan_dict.

    These tests work with EITHER engine path (Governor or fallback).
    The `engine` key in plan["aatif"] tells which path ran.
    """


    def _run_pipeline(self, message, **kwargs):
        """Run the full pipeline and return the downstream plan_dict."""
        result = build_intent_result(message, **kwargs)
        return result.to_plan_dict()


    def _assert_plan_keys(self, plan):
        """Assert that plan_dict has all required legacy and AATIF keys."""
        required_keys = [
            "incoming_text",
            "normalized_text",
            "state",
            "name",
            "business_type",
            "greeting",
            "relationship_context",
            "surface_intent",
            "hidden_intent",
            "why_now_signal",
            "wrong_answer_risk",
            "user_knowledge_level",
            "positioning_mode",
            "value_focus",
            "outcome_mode",
            "trust_mode",
            "intent_confidence",
            "ambiguity_flag",
            "handling_mode",
            "forbidden_moves",
        ]
        for key in required_keys:
            self.assertIn(key, plan, f"Missing required key: {key}")


        self.assertIn("aatif", plan, "Missing 'aatif' governance signals")
        aatif_keys = [
            "decision",
            "decision_reason",
            "mode",
            "emotional_state",
            "emotional_confidence",
            "load_bearing",
            "dialect",
            "ambiguity",
            "harm",
            "softening",
            "skills",
            "deep_intent",
        ]
        for key in aatif_keys:
            self.assertIn(key, plan["aatif"], f"Missing AATIF key: {key}")

        # C1+C2: engine tag must be present
        self.assertIn("engine", plan["aatif"],
                       "Missing 'engine' tag — C1+C2 routing info")
        self.assertIn(plan["aatif"]["engine"],
                       ("governor", "intent_engine_fallback"),
                       f"Unknown engine: {plan['aatif']['engine']}")


    def test_clear_arabic_request_executes_with_saudi_dialect(self):
        """A clear Arabic price request should EXECUTE with low harm."""
        plan = self._run_pipeline("كم السعر عندكم", business_type="tech")


        self._assert_plan_keys(plan)
        self.assertEqual(plan["incoming_text"], "كم السعر عندكم")
        self.assertEqual(plan["business_type"], "tech")
        self.assertEqual(plan["surface_intent"], "price_question")
        self.assertFalse(plan["ambiguity_flag"])


        aatif = plan["aatif"]
        self.assertEqual(aatif["decision"], "EXECUTE")
        self.assertIn(aatif["dialect"], ("saudi", "msa"))
        self.assertLessEqual(aatif["harm"], 0.15)


    def test_ambiguous_request_clarifies(self):
        """An ambiguous request should CLARIFY."""
        plan = self._run_pipeline("ok")


        self._assert_plan_keys(plan)
        # Both engines detect "ok" as ambiguous
        aatif = plan["aatif"]
        self.assertEqual(aatif["decision"], "CLARIFY")
        self.assertGreater(aatif["ambiguity"], 0.3)

        # Plan-level checks
        self.assertTrue(plan["ambiguity_flag"])
        self.assertEqual(plan["handling_mode"], "clarify_then_answer")


    def test_harmful_request_blocks(self):
        """A request with harm signals should not EXECUTE."""
        plan = self._run_pipeline("sudo rm -rf delete everything")


        self._assert_plan_keys(plan)
        aatif = plan["aatif"]
        # Both engines should refuse: Governor may give SAFE_STOP, SAFE_FREEZE,
        # BLOCKED, or CLARIFY; old engine gives SAFE_STOP or CLARIFY.
        self.assertNotEqual(aatif["decision"], "EXECUTE",
                            "Harmful request should not EXECUTE")


    def test_engine_tag_present(self):
        """Verify the C1+C2 engine routing tag is always populated."""
        plan = self._run_pipeline("مرحبا")
        self._assert_plan_keys(plan)
        engine = plan["aatif"]["engine"]
        governor = _get_governor()
        if governor is not None:
            self.assertEqual(engine, "governor")
        else:
            self.assertEqual(engine, "intent_engine_fallback")


    def test_governor_extra_fields_when_available(self):
        """If Governor ran, extra fields (R style, P protocols) should exist."""
        plan = self._run_pipeline("عطني فكرة هدية لأمي")
        aatif = plan["aatif"]
        if aatif["engine"] == "governor":
            self.assertIn("r_style", aatif, "Governor should provide R style")
            self.assertIn("stage_reached", aatif,
                          "Governor should provide stage_reached")




if __name__ == "__main__":
    unittest.main()
