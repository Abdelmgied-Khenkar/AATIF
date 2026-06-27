"""
test_hysteresis_deescalation.py — coverage for the *relaxation* half of γ+.

WHY THIS FILE EXISTS
====================
The existing test_hysteresis.py guards the first-turn pass-through (H1),
the escalation buffer (Rule 4), fail-closed locking, and clarify
exhaustion. It does NOT exercise the controller's *de-escalation* path —
the logic that decides how reluctantly the system is allowed to relax a
safety state once it has entered one.

That reluctance is not an implementation detail; it is تربية behaviour.
A فلتر flips back the instant a score crosses a line. A تربية layer is
asymmetric: quick to tighten, slow to loosen, and unwilling to lower its
guard while the harm signal H is still elevated — even if the surface
score S looks fine again. This file pins that asymmetry so it cannot
silently regress.

Specifically it covers the previously-untested branches:
  * Rule 5 / `_can_deescalate` — the S>threshold+ε buffer on the way UP
  * the H-based safety hold (SAFE_STOP stays locked while H > 0.5)
  * de-escalation is NEVER immediate, even across multiple levels
    (the mirror image of escalation_major_immediate)
  * clear_freeze → SAFE_STOP recovery, then a normal de-escalation
  * LRU session eviction (H2 fix) and transition-history capping

Thresholds under test (must match aatif_s_equation.py):
  EXECUTE > 0.70   CLARIFY > 0.50   SAFE_STOP > 0.30   ε = 0.05

البطء في رفع الحَذَر رحمةٌ، لا عيب — slowness to lower the guard
is mercy, not a defect.
"""

import pytest

from aatif_hysteresis import (
    HysteresisController,
    HysteresisState,
    S_THRESHOLDS,
    EPSILON_S,
    SEVERITY,
)


# Helper: drive a conversation into a known steady state.
# The first turn always passes through (Rule 0), so a single apply()
# with a matching raw_decision establishes that state cleanly.
def _seed(controller, cid, decision, S, H=0.1):
    r = controller.apply(cid, S=S, H=H, raw_decision=decision)
    assert r["decision"] == decision, "seed turn should pass through"
    return r


# ════════════════════════════════════════════════════════════════
#  DE-ESCALATION BUFFER — Rule 5 / _can_deescalate
# ════════════════════════════════════════════════════════════════
class TestDeescalationBuffer:
    """Relaxing a state requires crossing the threshold PLUS epsilon."""

    def test_safe_stop_to_clarify_held_inside_buffer(self):
        # SAFE_STOP -> CLARIFY needs S > 0.50 + 0.05 = 0.55.
        c = HysteresisController()
        _seed(c, "a", "SAFE_STOP", S=0.35)
        r = c.apply("a", S=0.52, H=0.1, raw_decision="CLARIFY")
        assert r["decision"] == "SAFE_STOP"
        assert r["held"] is True
        assert r["reason"] == "hysteresis_held"

    def test_safe_stop_to_clarify_released_past_buffer(self):
        c = HysteresisController()
        _seed(c, "a", "SAFE_STOP", S=0.35)
        r = c.apply("a", S=0.58, H=0.1, raw_decision="CLARIFY")
        assert r["decision"] == "CLARIFY"
        assert r["held"] is False
        assert r["reason"] == "deescalation_cleared"

    def test_clarify_to_execute_held_inside_buffer(self):
        # CLARIFY -> EXECUTE needs S > 0.70 + 0.05 = 0.75.
        c = HysteresisController()
        _seed(c, "d", "CLARIFY", S=0.60)
        r = c.apply("d", S=0.72, H=0.1, raw_decision="EXECUTE")
        assert r["decision"] == "CLARIFY"
        assert r["held"] is True

    def test_clarify_to_execute_released_past_buffer(self):
        c = HysteresisController()
        _seed(c, "d", "CLARIFY", S=0.60)
        r = c.apply("d", S=0.78, H=0.1, raw_decision="EXECUTE")
        assert r["decision"] == "EXECUTE"
        assert r["held"] is False
        assert r["reason"] == "deescalation_cleared"

    def test_exact_buffer_boundary_is_held(self):
        # S == threshold + ε exactly. `_can_deescalate` uses S <= required
        # -> hold. الشك لصالح السلامة: equality must not relax the state.
        c = HysteresisController()
        _seed(c, "b", "SAFE_STOP", S=0.35)
        boundary = S_THRESHOLDS["CLARIFY"] + EPSILON_S  # 0.55
        r = c.apply("b", S=boundary, H=0.1, raw_decision="CLARIFY")
        assert r["decision"] == "SAFE_STOP", "exact boundary must hold, not release"
        assert r["held"] is True

    def test_just_above_boundary_releases(self):
        c = HysteresisController()
        _seed(c, "b", "SAFE_STOP", S=0.35)
        boundary = S_THRESHOLDS["CLARIFY"] + EPSILON_S
        r = c.apply("b", S=boundary + 1e-3, H=0.1, raw_decision="CLARIFY")
        assert r["decision"] == "CLARIFY"


# ════════════════════════════════════════════════════════════════
#  H-BASED SAFETY HOLD — γ+ original spec
# ════════════════════════════════════════════════════════════════
class TestHBasedSafetyHold:
    """In SAFE_STOP, an elevated harm score blocks relaxation even
    when S has recovered past its buffer. Harm has its own memory."""

    def test_high_H_blocks_deescalation_despite_recovered_S(self):
        c = HysteresisController()
        _seed(c, "h", "SAFE_STOP", S=0.35, H=0.9)
        # S is well past the 0.55 buffer, but H is still 0.9.
        r = c.apply("h", S=0.58, H=0.9, raw_decision="CLARIFY")
        assert r["decision"] == "SAFE_STOP"
        assert r["held"] is True

    def test_deescalation_proceeds_once_H_drops(self):
        c = HysteresisController()
        _seed(c, "h", "SAFE_STOP", S=0.35, H=0.9)
        # held while H high
        assert c.apply("h", S=0.58, H=0.9, raw_decision="CLARIFY")["decision"] == "SAFE_STOP"
        # H falls below 0.5 -> now allowed
        r = c.apply("h", S=0.58, H=0.4, raw_decision="CLARIFY")
        assert r["decision"] == "CLARIFY"

    def test_H_exactly_half_does_not_hold(self):
        # The guard is `H > 0.5` (strict). H == 0.5 should NOT block.
        c = HysteresisController()
        _seed(c, "h", "SAFE_STOP", S=0.35, H=0.5)
        r = c.apply("h", S=0.58, H=0.5, raw_decision="CLARIFY")
        assert r["decision"] == "CLARIFY"

    def test_H_hold_only_applies_from_safe_stop(self):
        # The H>0.5 hold is scoped to current == SAFE_STOP. From CLARIFY,
        # a high H should not itself block a purely S-driven de-escalation.
        c = HysteresisController()
        _seed(c, "h", "CLARIFY", S=0.60, H=0.9)
        r = c.apply("h", S=0.78, H=0.9, raw_decision="EXECUTE")
        assert r["decision"] == "EXECUTE"


# ════════════════════════════════════════════════════════════════
#  ASYMMETRY — tighten fast, loosen slow
# ════════════════════════════════════════════════════════════════
class TestEscalationDeescalationAsymmetry:
    """The defining property of γ+: escalation can be immediate across
    multiple levels; de-escalation is always buffered, never immediate."""

    def test_multilevel_deescalation_is_buffered_not_immediate(self):
        # SAFE_STOP -> EXECUTE is a 2-level drop. There is no
        # "deescalation_major_immediate" rule — it must still respect
        # EXECUTE's threshold + ε = 0.75.
        c = HysteresisController()
        _seed(c, "x", "SAFE_STOP", S=0.20)
        r = c.apply("x", S=0.72, H=0.1, raw_decision="EXECUTE")
        assert r["decision"] == "SAFE_STOP"
        assert r["held"] is True

    def test_multilevel_deescalation_releases_past_buffer(self):
        c = HysteresisController()
        _seed(c, "x", "SAFE_STOP", S=0.20)
        r = c.apply("x", S=0.80, H=0.1, raw_decision="EXECUTE")
        assert r["decision"] == "EXECUTE"

    def test_multilevel_escalation_is_immediate(self):
        # The mirror image: EXECUTE -> SAFE_STOP (2 levels up) bypasses
        # all buffers. This is the asymmetry that makes the layer تربية.
        c = HysteresisController()
        _seed(c, "y", "EXECUTE", S=0.90)
        r = c.apply("y", S=0.20, H=0.1, raw_decision="SAFE_STOP")
        assert r["decision"] == "SAFE_STOP"
        assert r["held"] is False
        assert r["reason"] == "escalation_major_immediate"

    def test_deescalation_threshold_strictly_exceeds_escalation_threshold(self):
        # Property check: for the CLARIFY boundary, the S needed to ENTER
        # CLARIFY from above (escalate out of EXECUTE) is lower than the S
        # needed to LEAVE CLARIFY back to EXECUTE (de-escalate). The gap is
        # exactly 2ε — that gap is the dead-band that kills oscillation.
        c = HysteresisController()
        leave_execute = S_THRESHOLDS["EXECUTE"] - c.epsilon_s   # 0.65
        leave_clarify = S_THRESHOLDS["EXECUTE"] + c.epsilon_s   # 0.75
        assert leave_clarify - leave_execute == pytest.approx(2 * c.epsilon_s)
        assert leave_clarify > leave_execute


# ════════════════════════════════════════════════════════════════
#  THERMOSTAT — the docstring scenario, end to end
# ════════════════════════════════════════════════════════════════
class TestThermostatCycle:
    """The AC-thermostat example from the module docstring must hold:
    a value that dips into the dead-band and comes back does not flicker."""

    def test_dip_into_deadband_does_not_flicker(self):
        c = HysteresisController()
        # Turn 1: EXECUTE (first turn pass-through)
        assert c.apply("t", S=0.71, H=0.1, raw_decision="EXECUTE")["decision"] == "EXECUTE"
        # Turn 2: S=0.69 — inside the dead-band (>0.65), raw says CLARIFY,
        # hysteresis holds EXECUTE.
        assert c.apply("t", S=0.69, H=0.1, raw_decision="CLARIFY")["decision"] == "EXECUTE"
        # Turn 3: S=0.71 again — still EXECUTE, steady.
        assert c.apply("t", S=0.71, H=0.1, raw_decision="EXECUTE")["decision"] == "EXECUTE"
        # Turn 4: S=0.64 — crosses below 0.65, genuine transition.
        r = c.apply("t", S=0.64, H=0.1, raw_decision="CLARIFY")
        assert r["decision"] == "CLARIFY"

    def test_no_transition_recorded_while_held(self):
        # While hysteresis holds, no state transition should be logged.
        c = HysteresisController()
        c.apply("t", S=0.71, H=0.1, raw_decision="EXECUTE")
        c.apply("t", S=0.69, H=0.1, raw_decision="CLARIFY")  # held
        st = c.states["t"]
        assert st.history == [], "a held turn must not record a transition"
        assert st.turns_in_state == 2


# ════════════════════════════════════════════════════════════════
#  FREEZE RECOVERY then DE-ESCALATION
# ════════════════════════════════════════════════════════════════
class TestFreezeRecoveryThenDeescalation:
    def test_clear_freeze_lands_in_safe_stop_then_obeys_buffer(self):
        c = HysteresisController()
        _seed(c, "z", "SAFE_FREEZE", S=0.10, H=0.9)
        # Locked against escape until cleared.
        assert c.apply("z", S=0.9, H=0.0, raw_decision="EXECUTE")["decision"] == "SAFE_FREEZE"
        out = c.clear_freeze("z")
        assert out["cleared"] is True
        assert out["new_state"] == "SAFE_STOP"
        # After clearance we are in SAFE_STOP with turns_in_state reset to 0.
        # A modest S inside the 0.55 buffer must still hold SAFE_STOP.
        r = c.apply("z", S=0.52, H=0.1, raw_decision="CLARIFY")
        assert r["decision"] == "SAFE_STOP"

    def test_clear_freeze_records_clearance_in_history(self):
        c = HysteresisController()
        _seed(c, "z", "SAFE_FREEZE", S=0.10, H=0.9)
        c.clear_freeze("z")
        hist = c.states["z"].history
        assert any(h["to"] == "CLEARED" for h in hist)


# ════════════════════════════════════════════════════════════════
#  _can_escalate / _can_deescalate EDGES
# ════════════════════════════════════════════════════════════════
class TestTransitionPredicateEdges:
    def test_can_escalate_from_freeze_is_permissive(self):
        # current == SAFE_FREEZE has no entry in S_THRESHOLDS -> returns True.
        c = HysteresisController()
        assert c._can_escalate("SAFE_FREEZE", "CLARIFY", S=0.9, H=0.0) is True

    def test_cannot_deescalate_to_freeze(self):
        # proposed == SAFE_FREEZE is not a valid de-escalation target.
        c = HysteresisController()
        assert c._can_deescalate("SAFE_STOP", "SAFE_FREEZE", S=0.9, H=0.0) is False

    def test_custom_epsilon_widens_deadband(self):
        # A larger epsilon should make de-escalation harder.
        c = HysteresisController(epsilon_s=0.15)
        _seed(c, "w", "SAFE_STOP", S=0.35)
        # 0.60 would clear with ε=0.05 (needs >0.55) but not with ε=0.15
        # (needs > 0.65).
        r = c.apply("w", S=0.60, H=0.1, raw_decision="CLARIFY")
        assert r["decision"] == "SAFE_STOP"


# ════════════════════════════════════════════════════════════════
#  LRU EVICTION (H2 fix) + HISTORY CAP
# ════════════════════════════════════════════════════════════════
class TestSessionMemoryManagement:
    def test_lru_eviction_removes_oldest_untouched(self):
        c = HysteresisController(max_sessions=3)
        for cid in ("c1", "c2", "c3"):
            c.apply(cid, S=0.8, H=0.0, raw_decision="EXECUTE")
        assert set(c.states) == {"c1", "c2", "c3"}
        # Touch c1 so c2 becomes the least-recently-used.
        c.apply("c1", S=0.8, H=0.0, raw_decision="EXECUTE")
        # Adding c4 must evict c2.
        c.apply("c4", S=0.8, H=0.0, raw_decision="EXECUTE")
        assert set(c.states) == {"c1", "c3", "c4"}
        assert "c2" not in c.states

    def test_capacity_never_exceeded(self):
        c = HysteresisController(max_sessions=5)
        for i in range(50):
            c.apply(f"conv_{i}", S=0.8, H=0.0, raw_decision="EXECUTE")
        assert len(c.states) <= 5

    def test_transition_history_capped_at_20(self):
        c = HysteresisController()
        c.apply("osc", S=0.8, H=0.0, raw_decision="EXECUTE")
        # Force many real transitions by alternating immediate escalation
        # and cleared de-escalation.
        for i in range(40):
            if i % 2 == 0:
                c.apply("osc", S=0.20, H=0.0, raw_decision="SAFE_STOP")
            else:
                c.apply("osc", S=0.90, H=0.0, raw_decision="EXECUTE")
        assert len(c.states["osc"].history) <= 20

    def test_record_transition_directly_caps_history(self):
        # Unit-level guard on HysteresisState.record_transition itself.
        st = HysteresisState(current_decision="EXECUTE")
        for i in range(25):
            st.record_transition("EXECUTE", "CLARIFY", 0.6, 0.1, "test")
        assert len(st.history) == 20


# ════════════════════════════════════════════════════════════════
#  MUTATION GUARD — these must FAIL if the buffer is removed
# ════════════════════════════════════════════════════════════════
class TestMutationSensitivity:
    """If someone replaced `S < threshold - ε` / `S > threshold + ε`
    with a bare threshold comparison (no buffer), at least one of these
    in-band cases would flip. They are deliberately placed inside the
    dead-band so the buffer is the only thing keeping them held."""

    def test_in_band_value_would_break_without_buffer(self):
        c = HysteresisController()
        _seed(c, "m", "SAFE_STOP", S=0.35)
        # 0.53 is ABOVE the raw 0.50 CLARIFY line but BELOW 0.55 buffer.
        # With a buffer -> held. Without -> would wrongly release.
        r = c.apply("m", S=0.53, H=0.1, raw_decision="CLARIFY")
        assert r["decision"] == "SAFE_STOP"
