"""
test_hysteresis.py — regression suite for the hysteresis controller.

PRIMARY PURPOSE — guard Codex review fix **H1** (first-turn fail-open).

  Before H1: HysteresisState initialised current_decision="EXECUTE",
  so a brand-new conversation whose FIRST message scored a borderline
  CLARIFY (S in 0.65-0.70) was silently held → EXECUTE, because Rule 4
  single-level escalation requires S < 0.70-ε = 0.65 to leave EXECUTE.
  A genuine first-turn CLARIFY was suppressed by a phantom prior state.

  Fix: the initial state is the sentinel `None` ("unset"). The first
  real turn (Rule 0) passes the raw scored decision through untouched.

The fix shipped in commit ef1366c but had NO test guarding it, and there
was no dedicated test_hysteresis.py at all. This file closes that gap:
it pins the first-turn pass-through AND the core thermostat invariants
so the fix cannot silently regress.

الشك لصالح السلامة — but never at the cost of suppressing a real
first-turn signal. The thermostat must not invent a state it never had.
"""

import pytest

from aatif_hysteresis import HysteresisController, MAX_CLARIFY_TURNS


# ════════════════════════════════════════════════════════════════
#  H1 REGRESSION — first-turn pass-through (the core bug)
# ════════════════════════════════════════════════════════════════

class TestH1FirstTurnPassThrough:
    """A fresh conversation has no prior state to hold."""

    def test_initial_state_is_unset_sentinel(self):
        """Before any apply(), current_decision must be None — not EXECUTE.

        This is the root of H1: a phantom EXECUTE initial state is what
        suppressed first-turn escalations.
        """
        c = HysteresisController()
        assert c.get_state("fresh")["current_decision"] is None

    def test_first_turn_borderline_clarify_not_suppressed(self):
        """THE H1 BUG SCENARIO.

        First message scores a borderline CLARIFY at S=0.67 (inside the
        0.65-0.70 window that the old phantom-EXECUTE state would have
        swallowed). It must surface as CLARIFY, not be held to EXECUTE.
        """
        c = HysteresisController()
        r = c.apply("conv_new", S=0.67, H=0.20, raw_decision="CLARIFY")
        assert r["decision"] == "CLARIFY"
        assert r["held"] is False
        assert r["reason"] == "first_turn"
        assert r["previous_state"] is None

    def test_first_turn_safe_stop_passes_through(self):
        c = HysteresisController()
        r = c.apply("c", S=0.35, H=0.20, raw_decision="SAFE_STOP")
        assert r["decision"] == "SAFE_STOP"
        assert r["held"] is False
        assert r["reason"] == "first_turn"

    def test_first_turn_safe_freeze_passes_through(self):
        c = HysteresisController()
        r = c.apply("c", S=0.10, H=0.80, raw_decision="SAFE_FREEZE")
        assert r["decision"] == "SAFE_FREEZE"
        assert r["held"] is False
        assert r["reason"] == "first_turn"

    def test_first_turn_execute_passes_through(self):
        c = HysteresisController()
        r = c.apply("c", S=0.90, H=0.05, raw_decision="EXECUTE")
        assert r["decision"] == "EXECUTE"
        assert r["reason"] == "first_turn"

    def test_first_turn_sets_turns_in_state_to_one(self):
        c = HysteresisController()
        r = c.apply("c", S=0.55, H=0.15, raw_decision="CLARIFY")
        assert r["turns_in_state"] == 1
        assert c.get_state("c")["current_decision"] == "CLARIFY"

    @pytest.mark.parametrize("raw,S,H", [
        ("EXECUTE", 0.90, 0.05),
        ("CLARIFY", 0.67, 0.20),   # borderline window
        ("CLARIFY", 0.55, 0.15),
        ("SAFE_STOP", 0.35, 0.30),
        ("SAFE_FREEZE", 0.10, 0.80),
    ])
    def test_first_turn_any_decision_passes_through(self, raw, S, H):
        """No raw decision is ever altered on turn one, for any S/H."""
        c = HysteresisController()
        r = c.apply("conv", S=S, H=H, raw_decision=raw)
        assert r["decision"] == raw
        assert r["held"] is False
        assert r["reason"] == "first_turn"


# ════════════════════════════════════════════════════════════════
#  CORE THERMOSTAT — prove the fix did not break hysteresis itself
# ════════════════════════════════════════════════════════════════

class TestHysteresisBuffer:
    """Single-level transitions respect the ε buffer from turn two on."""

    def test_within_buffer_holds(self):
        """EXECUTE then borderline CLARIFY inside the buffer → held.

        S=0.68 is below the 0.70 EXECUTE threshold but above the buffered
        0.65, so the thermostat holds EXECUTE rather than flickering.
        """
        c = HysteresisController()
        c.apply("a", S=0.72, H=0.10, raw_decision="EXECUTE")
        r = c.apply("a", S=0.68, H=0.10, raw_decision="CLARIFY")
        assert r["decision"] == "EXECUTE"
        assert r["held"] is True
        assert r["reason"] == "hysteresis_held"

    def test_below_buffer_releases(self):
        """Once S crosses below 0.70-ε=0.65 the genuine transition fires."""
        c = HysteresisController()
        c.apply("b", S=0.72, H=0.10, raw_decision="EXECUTE")
        r = c.apply("b", S=0.63, H=0.15, raw_decision="CLARIFY")
        assert r["decision"] == "CLARIFY"
        assert r["held"] is False


class TestImmediateEscalation:
    """Danger bypasses buffers."""

    def test_safe_freeze_is_immediate(self):
        c = HysteresisController()
        c.apply("d", S=0.90, H=0.05, raw_decision="EXECUTE")
        r = c.apply("d", S=0.10, H=0.80, raw_decision="SAFE_FREEZE")
        assert r["decision"] == "SAFE_FREEZE"
        assert r["held"] is False
        assert r["reason"] == "freeze_immediate"

    def test_multi_level_escalation_is_immediate(self):
        """EXECUTE → SAFE_STOP (2 levels) skips the buffer."""
        c = HysteresisController()
        c.apply("e", S=0.90, H=0.05, raw_decision="EXECUTE")
        r = c.apply("e", S=0.35, H=0.20, raw_decision="SAFE_STOP")
        assert r["decision"] == "SAFE_STOP"
        assert r["reason"] == "escalation_major_immediate"


class TestFailClosed:
    """SAFE_FREEZE is the one state that never auto-exits."""

    def test_freeze_locks_against_execute(self):
        c = HysteresisController()
        c.apply("f", S=0.10, H=0.80, raw_decision="SAFE_FREEZE")
        r = c.apply("f", S=0.90, H=0.05, raw_decision="EXECUTE")
        assert r["decision"] == "SAFE_FREEZE"
        assert r["held"] is True
        assert r["reason"] == "fail_closed_locked"

    def test_explicit_clearance_allows_recovery(self):
        """Human clearance drops freeze to SAFE_STOP, then S can de-escalate."""
        c = HysteresisController()
        c.apply("g", S=0.10, H=0.80, raw_decision="SAFE_FREEZE")
        cleared = c.clear_freeze("g")
        assert cleared["cleared"] is True
        assert cleared["new_state"] == "SAFE_STOP"
        # With S above 0.70+ε and low H, recovery to EXECUTE is allowed.
        r = c.apply("g", S=0.80, H=0.05, raw_decision="EXECUTE")
        assert r["decision"] == "EXECUTE"

    def test_clear_freeze_when_not_frozen_is_noop(self):
        c = HysteresisController()
        c.apply("h", S=0.90, H=0.05, raw_decision="EXECUTE")
        res = c.clear_freeze("h")
        assert res["cleared"] is False


class TestClarifyExhaustion:
    """Persistent CLARIFY (لف ودار) is itself a signal → SAFE_STOP."""

    def test_repeated_clarify_escalates_to_safe_stop(self):
        c = HysteresisController()
        decisions = [
            c.apply("i", S=0.55, H=0.15, raw_decision="CLARIFY")
            for _ in range(MAX_CLARIFY_TURNS + 1)
        ]
        # First MAX_CLARIFY_TURNS turns stay in CLARIFY...
        for r in decisions[:MAX_CLARIFY_TURNS]:
            assert r["decision"] == "CLARIFY"
        # ...the turn after exhaustion escalates.
        assert decisions[MAX_CLARIFY_TURNS]["decision"] == "SAFE_STOP"
        assert decisions[MAX_CLARIFY_TURNS]["reason"] == "clarify_exhausted"


class TestStateIsolation:
    """State is per-conversation and resettable."""

    def test_conversations_are_independent(self):
        c = HysteresisController()
        c.apply("x", S=0.10, H=0.80, raw_decision="SAFE_FREEZE")
        # A different conversation's first turn is unaffected by x's freeze.
        r = c.apply("y", S=0.67, H=0.20, raw_decision="CLARIFY")
        assert r["decision"] == "CLARIFY"
        assert r["reason"] == "first_turn"

    def test_reset_returns_to_unset_sentinel(self):
        c = HysteresisController()
        c.apply("z", S=0.55, H=0.15, raw_decision="CLARIFY")
        c.reset("z")
        assert c.get_state("z")["current_decision"] is None
        # After reset the next turn is again treated as a first turn.
        r = c.apply("z", S=0.67, H=0.20, raw_decision="CLARIFY")
        assert r["reason"] == "first_turn"
