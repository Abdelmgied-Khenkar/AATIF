#!/usr/bin/env python3
"""
FN#070 OutputGate Layer 7 PSP check tests — aatif_output_gate.py

WHY THIS FILE EXISTS
────────────────────
Layer 7 is the post-generation half of FN#070. It is CORRECTIVE / REGENERATIVE,
NOT safety-judicial. It must never block, never set GateReading.blocked, and
never touch S/H/θ or the GovernanceEquation (Single Mind). It is inert unless a
caller opts in, and defaults to MONITORING (log violations, pass through).

This file is the regression wall for that contract:
  1. disabled by default → pure pass-through (text unchanged, no flags).
  2. monitor mode + unprompted premature closure → LOG the violation, but
     still pass the original text through (never block).
  3. monitor mode + a response that presents alternatives → no violation.
  4. block mode + premature closure → re-open the space (regenerate).
  5. block mode + a good response → unchanged.
  6. PROMPTED closure (user_requested_closure) is never a violation.
  7. non-decision turns are never checked.
  8. Layer 7 never blocks and never disturbs the six-layer safety check().

ISOLATION STRATEGY
──────────────────
Pure offline regex/string logic — no model, no embeddings. PSPReadings come
from the real PSPDetector (deterministic tiers) or are hand-built for the
prompted-closure case.

Design consensus: Claude × ChatGPT, 2026-06-30 (FN070_DESIGN_CONSENSUS.md)
License: BSL 1.1 — Architect: Abdulmjeed Ibrahim Khenkar
"""

import sys
import os
import pytest

_ENGINE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_output_gate import (
    AATIFOutputGate,
    GateReading,
    PSPGateConfig,
    PSPGateReading,
)
from aatif_psp_detector import (
    PSPDetector,
    PSPReading,
    LivePath,
    DomainPSPConfig,
    PSP_GATE_CHECK_ENABLED,
    PSP_GATE_MODE,
)


# ═══════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def gate():
    return AATIFOutputGate()


@pytest.fixture
def detector():
    return PSPDetector()


# An unprompted decision point (healthcare, high closure_risk).
@pytest.fixture
def decision_reading(detector):
    return detector.detect("should I have the surgery or wait?",
                           domain_config=DomainPSPConfig.for_domain("healthcare"))


ON_MONITOR = PSPGateConfig(PSP_GATE_CHECK_ENABLED=True, PSP_GATE_MODE="monitor")
ON_BLOCK = PSPGateConfig(PSP_GATE_CHECK_ENABLED=True, PSP_GATE_MODE="block")

PREMATURE = "You should definitely get the surgery. It's the right call."
OPEN_RESPONSE = (
    "You could consider surgery or physical therapy. "
    "Option 1: surgery — faster but riskier. "
    "Option 2: therapy — slower but safer."
)


# ═══════════════════════════════════════════════════════════════
#  TestFeatureFlagDefaults
# ═══════════════════════════════════════════════════════════════

class TestFeatureFlagDefaults:
    def test_config_defaults_match_flags(self):
        cfg = PSPGateConfig()
        assert cfg.PSP_GATE_CHECK_ENABLED is False
        assert cfg.PSP_GATE_CHECK_ENABLED == PSP_GATE_CHECK_ENABLED
        assert cfg.PSP_GATE_MODE == "monitor"
        assert cfg.PSP_GATE_MODE == PSP_GATE_MODE


# ═══════════════════════════════════════════════════════════════
#  TestDisabledPassThrough — OFF by default
# ═══════════════════════════════════════════════════════════════

class TestDisabledPassThrough:
    def test_disabled_returns_text_unchanged(self, gate, decision_reading):
        r = gate.check_psp(PREMATURE, decision_reading)   # default config = OFF
        assert isinstance(r, PSPGateReading)
        assert r.enabled is False
        assert r.text == PREMATURE
        assert r.flags == []
        assert r.regenerated is False

    def test_disabled_does_not_inspect(self, gate, decision_reading):
        r = gate.check_psp(PREMATURE, decision_reading)
        assert r.premature_closure is False   # never even checked
        assert "disabled" in r.notes


# ═══════════════════════════════════════════════════════════════
#  TestMonitorMode — log, never block
# ═══════════════════════════════════════════════════════════════

class TestMonitorMode:
    def test_logs_premature_closure(self, gate, decision_reading, caplog):
        import logging
        with caplog.at_level(logging.INFO, logger="aatif.psp_gate"):
            r = gate.check_psp(PREMATURE, decision_reading, ON_MONITOR)
        assert r.premature_closure is True
        assert r.log_messages, "monitor mode must record the violation"
        assert "PSP_CLOSURE_VIOLATION_LOGGED" in r.flags
        assert any("closure violation" in m for m in caplog.messages)

    def test_passes_text_through_unchanged(self, gate, decision_reading):
        r = gate.check_psp(PREMATURE, decision_reading, ON_MONITOR)
        assert r.text == PREMATURE          # monitoring NEVER mutates output
        assert r.regenerated is False

    def test_open_response_not_flagged(self, gate, decision_reading):
        r = gate.check_psp(OPEN_RESPONSE, decision_reading, ON_MONITOR)
        assert r.premature_closure is False
        assert r.log_messages == []
        assert "PSP_CLOSURE_VIOLATION_LOGGED" not in r.flags


# ═══════════════════════════════════════════════════════════════
#  TestBlockMode — regenerate on premature closure
# ═══════════════════════════════════════════════════════════════

class TestBlockMode:
    def test_regenerates_on_premature_closure(self, gate, decision_reading):
        r = gate.check_psp(PREMATURE, decision_reading, ON_BLOCK)
        assert r.premature_closure is True
        assert r.regenerated is True
        assert r.text != PREMATURE
        assert "PSP_PREMATURE_CLOSURE_REGENERATED" in r.flags

    def test_regenerated_text_reopens_space(self, gate, decision_reading):
        r = gate.check_psp(PREMATURE, decision_reading, ON_BLOCK)
        # re-opening names the realistic set and hands the choice back
        assert "القرار النهائي لك" in r.text
        assert "خيارات" in r.text

    def test_regenerated_text_preserves_original(self, gate, decision_reading):
        r = gate.check_psp(PREMATURE, decision_reading, ON_BLOCK)
        assert PREMATURE.rstrip() in r.text   # appends, does not discard

    def test_block_mode_uses_live_path_labels(self, gate):
        reading = PSPReading(
            is_decision_point=True, decision_confidence=0.8, closure_risk=0.8,
            bounded_count=3,
            live_paths=[LivePath("Surgery"), LivePath("Therapy")],
        )
        r = gate.check_psp("You should go with surgery.", reading, ON_BLOCK)
        assert r.regenerated is True
        assert "Surgery" in r.text and "Therapy" in r.text

    def test_good_response_not_regenerated(self, gate, decision_reading):
        r = gate.check_psp(OPEN_RESPONSE, decision_reading, ON_BLOCK)
        assert r.regenerated is False
        assert r.text == OPEN_RESPONSE


# ═══════════════════════════════════════════════════════════════
#  TestPromptedClosure — sanctioned, never a violation
# ═══════════════════════════════════════════════════════════════

class TestPromptedClosure:
    @pytest.fixture
    def prompted_reading(self):
        return PSPReading(
            is_decision_point=True, decision_confidence=0.8, closure_risk=0.35,
            bounded_count=3, user_requested_closure=True,
        )

    def test_prompted_closure_not_flagged_monitor(self, gate, prompted_reading):
        r = gate.check_psp(PREMATURE, prompted_reading, ON_MONITOR)
        assert r.premature_closure is False
        assert r.log_messages == []

    def test_prompted_closure_not_regenerated_block(self, gate, prompted_reading):
        r = gate.check_psp(PREMATURE, prompted_reading, ON_BLOCK)
        assert r.regenerated is False
        assert r.text == PREMATURE


# ═══════════════════════════════════════════════════════════════
#  TestNonDecision — nothing to check
# ═══════════════════════════════════════════════════════════════

class TestNonDecision:
    def test_non_decision_reading_skipped(self, gate, detector):
        factual = detector.detect("what is the capital of France?")
        r = gate.check_psp(PREMATURE, factual, ON_MONITOR)
        assert r.premature_closure is False
        assert "no decision point" in r.notes

    def test_none_reading_skipped(self, gate):
        r = gate.check_psp(PREMATURE, None, ON_MONITOR)
        assert r.premature_closure is False
        assert "no decision point" in r.notes


# ═══════════════════════════════════════════════════════════════
#  TestConfigResolution — dict / object / None
# ═══════════════════════════════════════════════════════════════

class TestConfigResolution:
    def test_dict_config(self, gate, decision_reading):
        cfg = {"PSP_GATE_CHECK_ENABLED": True, "PSP_GATE_MODE": "block"}
        r = gate.check_psp(PREMATURE, decision_reading, cfg)
        assert r.enabled is True
        assert r.mode == "block"
        assert r.regenerated is True

    def test_object_config(self, gate, decision_reading):
        class Cfg:
            PSP_GATE_CHECK_ENABLED = True
            PSP_GATE_MODE = "monitor"
        r = gate.check_psp(PREMATURE, decision_reading, Cfg())
        assert r.enabled is True
        assert r.premature_closure is True

    def test_none_config_defaults_off(self, gate, decision_reading):
        r = gate.check_psp(PREMATURE, decision_reading, None)
        assert r.enabled is False


# ═══════════════════════════════════════════════════════════════
#  TestSafetyIsolation — Layer 7 is NOT safety-judicial
# ═══════════════════════════════════════════════════════════════

class TestSafetyIsolation:
    def test_reading_has_no_blocked_field(self, gate, decision_reading):
        """Layer 7 never blocks — PSPGateReading carries no block machinery."""
        r = gate.check_psp(PREMATURE, decision_reading, ON_BLOCK)
        assert not hasattr(r, "blocked")
        assert not hasattr(r, "block_reason")

    def test_layer7_does_not_disturb_safety_check(self, gate):
        """The six-layer safety check() is independent of Layer 7."""
        safe = gate.check("Here are a few options to weigh, take your time.",
                          domain="general")
        assert isinstance(safe, GateReading)
        assert safe.blocked is False
        assert safe.passed is True

    def test_empty_response_no_violation(self, gate, decision_reading):
        r = gate.check_psp("", decision_reading, ON_BLOCK)
        assert r.premature_closure is False
        assert r.regenerated is False
