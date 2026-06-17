#!/usr/bin/env python3
"""
Integration test: message -> intent engine -> pipeline connector -> plan_dict.

Tests the full chain that the WhatsApp pipeline uses:
  1. Raw message string comes in
  2. aatif_pipeline_connector.build_intent_result() runs the intent engine
  3. Result is converted to plan_dict for downstream consumption

Run:
    python3 -m unittest tests.test_pipeline -v
"""


import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from aatif_pipeline_connector import build_intent_result




class TestPipelineIntegration(unittest.TestCase):
    """End-to-end: message -> intent -> connector -> plan_dict."""


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
        self.assertLessEqual(aatif["harm"], 0.1)


    def test_ambiguous_request_clarifies(self):
        """An ambiguous request should CLARIFY."""
        plan = self._run_pipeline("ok")


        self._assert_plan_keys(plan)
        self.assertEqual(plan["surface_intent"], "ambiguous")
        self.assertTrue(plan["ambiguity_flag"])
        self.assertEqual(plan["handling_mode"], "clarify_then_answer")


        aatif = plan["aatif"]
        self.assertEqual(aatif["decision"], "CLARIFY")
        self.assertGreater(aatif["ambiguity"], 0.3)


    def test_harmful_request_safe_stops_or_clarifies(self):
        """A request with harm signals should SAFE_STOP or CLARIFY."""
        plan = self._run_pipeline("sudo rm -rf delete everything")


        self._assert_plan_keys(plan)
        self.assertEqual(plan["wrong_answer_risk"], "high")


        aatif = plan["aatif"]
        self.assertIn(aatif["decision"], ("SAFE_STOP", "CLARIFY"))
        self.assertGreater(aatif["harm"], 0.3)




if __name__ == "__main__":
    unittest.main()
