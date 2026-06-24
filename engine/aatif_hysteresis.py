#!/usr/bin/env python3
"""
AATIF Hysteresis Controller — γ+ (Law γ Extension)
===================================================

Prevents the governance engine from oscillating between decisions.

Problem without hysteresis:
    Turn 1: S = 0.71 → EXECUTE
    Turn 2: S = 0.69 → CLARIFY
    Turn 3: S = 0.71 → EXECUTE
    Turn 4: S = 0.70 → CLARIFY
    → The system can't make up its mind. User experience: chaotic.

With hysteresis (ε = 0.05):
    Turn 1: S = 0.71 → EXECUTE (entered EXECUTE state)
    Turn 2: S = 0.69 → EXECUTE (still above 0.65 exit threshold)
    Turn 3: S = 0.71 → EXECUTE (steady)
    Turn 4: S = 0.64 → CLARIFY (crossed below 0.65 — now transition)
    → Stable. Like the AC thermostat: turns on at 25°, off at 23°.

From v9.7 spec:
    Entry to REWRITE: H ≥ τ_rewrite
    Exit from REWRITE: H ≤ (τ_rewrite − ε_rw)
    STOP is Fail-Closed: requires explicit clearance to exit
    SAFE_FREEZE: never auto-exits — requires human clearance

This module extends γ+ to cover ALL four decision transitions,
not just REWRITE/STOP. Every boundary gets a buffer zone.

Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import time


# ═══════════════════════════════════════════════════════════
#  ε (epsilon) — buffer width for each transition boundary
# ═══════════════════════════════════════════════════════════
#
#  Threshold map (from aatif_s_equation.py):
#    EXECUTE:     S > 0.70
#    CLARIFY:     S > 0.50
#    SAFE_STOP:   S > 0.30
#    SAFE_FREEZE: S ≤ 0.30
#
#  With hysteresis, exiting a state requires crossing further
#  than just the boundary. Going UP (safer) needs S > threshold + ε.
#  Going DOWN (riskier) needs S < threshold - ε.
#
#  Example: currently EXECUTE (S > 0.70).
#    Without hysteresis: drops to CLARIFY at S = 0.699
#    With hysteresis:    drops to CLARIFY at S = 0.649 (0.70 - 0.05)
#
#  Example: currently SAFE_STOP (S > 0.30).
#    Without hysteresis: rises to CLARIFY at S = 0.501
#    With hysteresis:    rises to CLARIFY at S = 0.551 (0.50 + 0.05)
#
EPSILON_S = 0.05       # buffer for S-based transitions
EPSILON_H = 0.05       # buffer for H-based harm gate (γ+ original)

# Fail-closed states — these never auto-exit
FAIL_CLOSED = {"SAFE_FREEZE"}

# Maximum consecutive turns in CLARIFY before escalating to SAFE_STOP.
# If the system asks for clarification and the user keeps being vague
# (لف ودار), evasion is itself a signal — الشك لصالح السلامة.
# After MAX_CLARIFY_TURNS in CLARIFY state, the next CLARIFY → SAFE_STOP.
MAX_CLARIFY_TURNS = 2

# Decision severity ordering (higher index = more restrictive)
SEVERITY = {
    "EXECUTE": 0,
    "CLARIFY": 1,
    "SAFE_STOP": 2,
    "SAFE_FREEZE": 3,
}

# Original thresholds (must match aatif_s_equation.py)
S_THRESHOLDS = {
    "EXECUTE": 0.70,
    "CLARIFY": 0.50,
    "SAFE_STOP": 0.30,
    # SAFE_FREEZE is everything below 0.30
}


@dataclass
class HysteresisState:
    """
    Tracks the current governance state for hysteresis decisions.

    Stored per conversation (keyed by conversation_id).
    """
    current_decision: Optional[str] = None  # None = first turn (no prior state)
    current_S: float = 1.0              # last S value
    current_H: float = 0.0              # last H value
    turns_in_state: int = 0             # how long in this state
    entered_at: float = 0.0             # timestamp of state entry
    cleared: bool = False               # explicit clearance for fail-closed
    history: list = field(default_factory=list)  # last N transitions

    def record_transition(self, from_state: str, to_state: str,
                          S: float, H: float, reason: str):
        """Log a state transition for audit trail."""
        self.history.append({
            "from": from_state,
            "to": to_state,
            "S": round(S, 4),
            "H": round(H, 4),
            "reason": reason,
            "time": time.time(),
        })
        # Keep only last 20 transitions
        if len(self.history) > 20:
            self.history = self.history[-20:]


class HysteresisController:
    """
    Applies hysteresis to AATIF governance decisions.

    Usage:
        controller = HysteresisController()

        # First turn — no prior state, returns raw decision
        result = controller.apply("conv_123", S=0.72, H=0.1,
                                  raw_decision="EXECUTE")
        # result == "EXECUTE"

        # Second turn — S dipped slightly but stays in buffer
        result = controller.apply("conv_123", S=0.68, H=0.1,
                                  raw_decision="CLARIFY")
        # result == "EXECUTE" (hysteresis held!)

        # Third turn — S dropped below buffer
        result = controller.apply("conv_123", S=0.63, H=0.15,
                                  raw_decision="CLARIFY")
        # result == "CLARIFY" (genuine transition)
    """

    def __init__(self, epsilon_s: float = EPSILON_S,
                 epsilon_h: float = EPSILON_H):
        self.epsilon_s = epsilon_s
        self.epsilon_h = epsilon_h
        self.states: dict[str, HysteresisState] = {}

    def _get_state(self, conversation_id: str) -> HysteresisState:
        """Get or create state for a conversation."""
        if conversation_id not in self.states:
            self.states[conversation_id] = HysteresisState(
                entered_at=time.time()
            )
        return self.states[conversation_id]

    def apply(self, conversation_id: str, S: float, H: float,
              raw_decision: str) -> dict:
        """
        Apply hysteresis to a raw decision from the S equation engine.

        Args:
            conversation_id: unique conversation identifier
            S: current S score from the engine
            H: current H (harm) score
            raw_decision: the decision the engine would make without hysteresis

        Returns:
            dict with:
                decision: the final (hysteresis-adjusted) decision
                raw_decision: what the engine said before hysteresis
                held: True if hysteresis prevented a transition
                reason: why hysteresis held or released
                state: current hysteresis state info
        """
        state = self._get_state(conversation_id)
        prev = state.current_decision

        # ─── Rule 0: First turn — no prior state, pass through ──
        # On the very first turn of a conversation, current_decision
        # is None (sentinel). The system has no prior state to hold,
        # so the raw scored decision passes through without hysteresis.
        # This prevents a phantom "EXECUTE" initial state from
        # suppressing a genuine first-turn CLARIFY.
        if prev is None:
            state.current_decision = raw_decision
            state.turns_in_state = 1
            state.entered_at = time.time()
            state.current_S = S
            state.current_H = H
            return {
                "decision": raw_decision,
                "raw_decision": raw_decision,
                "held": False,
                "reason": "first_turn",
                "turns_in_state": 1,
                "previous_state": None,
            }

        prev_severity = SEVERITY.get(prev, 0)
        raw_severity = SEVERITY.get(raw_decision, 0)

        final_decision = raw_decision
        held = False
        reason = "no_change"

        # ─── Rule 1: Fail-closed states never auto-exit ─────────
        if prev in FAIL_CLOSED and not state.cleared:
            final_decision = prev
            held = (raw_decision != prev)
            reason = "fail_closed_locked" if held else "fail_closed_steady"

        # ─── Rule 2: Jump to SAFE_FREEZE — always immediate ────
        # Jailbreak or extreme danger bypasses all buffers.
        elif raw_decision == "SAFE_FREEZE":
            final_decision = raw_decision
            held = False
            reason = "freeze_immediate"

        # ─── Rule 3: Multi-level escalation — immediate ─────────
        # Jumping 2+ severity levels (e.g. EXECUTE → SAFE_STOP)
        # means the situation changed dramatically. No buffer.
        elif raw_severity > prev_severity and (raw_severity - prev_severity) >= 2:
            final_decision = raw_decision
            held = False
            reason = "escalation_major_immediate"

        # ─── Rule 4: Single-level escalation — hysteresis ───────
        # EXECUTE → CLARIFY or CLARIFY → SAFE_STOP:
        # Apply buffer. S must cross below (threshold - ε).
        # This is the thermostat: don't flicker at the boundary.
        elif raw_severity > prev_severity:
            if self._can_escalate(prev, raw_decision, S, H):
                final_decision = raw_decision
                held = False
                reason = "escalation_cleared"
            else:
                final_decision = prev
                held = True
                reason = "hysteresis_held"

        # ─── Rule 5: De-escalation — hysteresis ─────────────────
        # S must cross above (threshold + ε) to de-escalate.
        elif raw_severity < prev_severity:
            if self._can_deescalate(prev, raw_decision, S, H):
                final_decision = raw_decision
                held = False
                reason = "deescalation_cleared"
            else:
                final_decision = prev
                held = True
                reason = "hysteresis_held"

        # ─── Rule 6: Same decision — just update tracking ───────
        else:
            final_decision = raw_decision
            held = False
            reason = "steady_state"

        # ─── Rule 7: CLARIFY EXHAUSTION ─────────────────────────
        # If the system has been asking for clarification for too many
        # consecutive turns and the user still hasn't provided clarity,
        # escalate to SAFE_STOP. Evasion is itself a signal.
        # "اللف نفسه إشارة" — dodging IS the red flag.
        if (final_decision == "CLARIFY" and
                state.current_decision == "CLARIFY" and
                state.turns_in_state >= MAX_CLARIFY_TURNS):
            final_decision = "SAFE_STOP"
            held = False
            reason = "clarify_exhausted"

        # ─── Update state ────────────────────────────────────────
        if final_decision != prev:
            state.record_transition(prev, final_decision, S, H, reason)
            state.current_decision = final_decision
            state.turns_in_state = 1
            state.entered_at = time.time()
            state.cleared = False
        else:
            state.turns_in_state += 1

        state.current_S = S
        state.current_H = H

        return {
            "decision": final_decision,
            "raw_decision": raw_decision,
            "held": held,
            "reason": reason,
            "turns_in_state": state.turns_in_state,
            "previous_state": prev,
        }

    def _can_escalate(self, current: str, proposed: str,
                       S: float, H: float) -> bool:
        """
        Check if single-level escalation is justified past the buffer.

        For escalation from EXECUTE to CLARIFY, S must be below
        the EXECUTE threshold minus epsilon (0.70 - 0.05 = 0.65).

        For escalation from CLARIFY to SAFE_STOP, S must be below
        the CLARIFY threshold minus epsilon (0.50 - 0.05 = 0.45).
        """
        # Find the threshold of the CURRENT state (the one we'd leave)
        current_threshold = S_THRESHOLDS.get(current)
        if current_threshold is None:
            # Current is SAFE_FREEZE — shouldn't be here, but allow
            return True

        required_S = current_threshold - self.epsilon_s

        # S must be BELOW the buffered threshold to escalate
        return S < required_S

    def _can_deescalate(self, current: str, proposed: str,
                        S: float, H: float) -> bool:
        """
        Check if de-escalation is justified given hysteresis buffers.

        For de-escalation from X to Y, S must be above
        Y's threshold + epsilon (not just above Y's threshold).

        Also checks H-based hysteresis for harm-triggered states.
        """
        # SAFE_STOP → CLARIFY: S must be above 0.50 + ε = 0.55
        # SAFE_STOP → EXECUTE: S must be above 0.70 + ε = 0.75
        # CLARIFY → EXECUTE: S must be above 0.70 + ε = 0.75

        target_threshold = S_THRESHOLDS.get(proposed)
        if target_threshold is None:
            # Proposed is SAFE_FREEZE — can't de-escalate TO freeze
            return False

        required_S = target_threshold + self.epsilon_s

        if S <= required_S:
            return False

        # H-based check (γ+ original spec):
        # If we're in SAFE_STOP and H is still high, don't de-escalate
        # even if S looks ok. H needs to drop below its entry threshold - ε.
        if current == "SAFE_STOP" and H > 0.5:
            # H is still elevated — hold the safety state
            return False

        return True

    def clear_freeze(self, conversation_id: str) -> dict:
        """
        Explicitly clear a SAFE_FREEZE state (human override).

        SAFE_FREEZE is fail-closed — this is the ONLY way out.
        In production: this would require authenticated human action.

        Returns:
            dict with clearance result
        """
        state = self._get_state(conversation_id)

        if state.current_decision != "SAFE_FREEZE":
            return {
                "cleared": False,
                "reason": f"not_frozen (current: {state.current_decision})"
            }

        state.cleared = True
        state.record_transition(
            "SAFE_FREEZE", "CLEARED",
            state.current_S, state.current_H,
            "explicit_human_clearance"
        )
        # Reset to SAFE_STOP — the next turn's S score will determine
        # whether to de-escalate further
        state.current_decision = "SAFE_STOP"
        state.turns_in_state = 0

        return {
            "cleared": True,
            "reason": "human_clearance_accepted",
            "new_state": "SAFE_STOP"
        }

    def get_state(self, conversation_id: str) -> dict:
        """Get current state for inspection/debugging."""
        state = self._get_state(conversation_id)
        return {
            "current_decision": state.current_decision,
            "current_S": state.current_S,
            "current_H": state.current_H,
            "turns_in_state": state.turns_in_state,
            "cleared": state.cleared,
            "history": state.history[-5:],  # last 5 transitions
        }

    def reset(self, conversation_id: str):
        """Reset state for a conversation (new conversation)."""
        if conversation_id in self.states:
            del self.states[conversation_id]


# ═══════════════════════════════════════════════════════════
#  TESTS
# ═══════════════════════════════════════════════════════════

def _run_tests():
    """Verify hysteresis behavior — the AC thermostat test."""
    print("=" * 65)
    print("AATIF Hysteresis Controller — γ+ Tests")
    print("=" * 65)

    controller = HysteresisController()
    passed = 0
    failed = 0

    def check(name: str, result: dict, expected_decision: str,
              expected_held: bool):
        nonlocal passed, failed
        ok = (result["decision"] == expected_decision and
              result["held"] == expected_held)
        status = "✅" if ok else "❌"
        held_str = "HELD" if result["held"] else "pass"
        print(f"  {status} {name}: {result['raw_decision']} → "
              f"{result['decision']} ({held_str}) "
              f"[{result['reason']}]")
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"     EXPECTED: decision={expected_decision}, "
                  f"held={expected_held}")

    # ─── Test 1: Basic stability ────────────────────────────
    print("\n📝 Test 1: Basic stability — small S dip stays EXECUTE")
    conv = "test_1"
    r = controller.apply(conv, S=0.75, H=0.1, raw_decision="EXECUTE")
    check("T1a: Enter EXECUTE", r, "EXECUTE", False)

    r = controller.apply(conv, S=0.68, H=0.1, raw_decision="CLARIFY")
    check("T1b: S=0.68 dip (in buffer)", r, "EXECUTE", True)

    r = controller.apply(conv, S=0.66, H=0.1, raw_decision="CLARIFY")
    check("T1c: S=0.66 still in buffer", r, "EXECUTE", True)

    r = controller.apply(conv, S=0.64, H=0.1, raw_decision="CLARIFY")
    check("T1d: S=0.64 below buffer → CLARIFY", r, "CLARIFY", False)

    # ─── Test 2: Escalation is immediate ────────────────────
    print("\n📝 Test 2: Escalation is always immediate (no buffer)")
    conv = "test_2"
    r = controller.apply(conv, S=0.75, H=0.1, raw_decision="EXECUTE")
    check("T2a: Enter EXECUTE", r, "EXECUTE", False)

    r = controller.apply(conv, S=0.35, H=0.6, raw_decision="SAFE_STOP")
    check("T2b: Sudden drop → SAFE_STOP immediate", r, "SAFE_STOP", False)

    # ─── Test 3: SAFE_FREEZE is fail-closed ─────────────────
    print("\n📝 Test 3: SAFE_FREEZE never auto-exits")
    conv = "test_3"
    r = controller.apply(conv, S=0.20, H=0.9, raw_decision="SAFE_FREEZE")
    check("T3a: Enter SAFE_FREEZE", r, "SAFE_FREEZE", False)

    r = controller.apply(conv, S=0.80, H=0.05, raw_decision="EXECUTE")
    check("T3b: S=0.80 but FREEZE holds", r, "SAFE_FREEZE", True)

    r = controller.apply(conv, S=0.90, H=0.01, raw_decision="EXECUTE")
    check("T3c: S=0.90 still locked", r, "SAFE_FREEZE", True)

    # Now clear it
    clear_result = controller.clear_freeze(conv)
    assert clear_result["cleared"] is True
    print(f"  🔓 Freeze cleared: {clear_result['reason']}")

    r = controller.apply(conv, S=0.80, H=0.05, raw_decision="EXECUTE")
    check("T3d: After clearance, S=0.80 → can de-escalate",
          r, "EXECUTE", False)

    # ─── Test 4: SAFE_STOP holds when H still high ──────────
    print("\n📝 Test 4: SAFE_STOP holds while H is elevated")
    conv = "test_4"
    r = controller.apply(conv, S=0.35, H=0.7, raw_decision="SAFE_STOP")
    check("T4a: Enter SAFE_STOP (high H)", r, "SAFE_STOP", False)

    r = controller.apply(conv, S=0.60, H=0.6, raw_decision="CLARIFY")
    check("T4b: S=0.60 but H=0.6 still high → hold", r, "SAFE_STOP", True)

    r = controller.apply(conv, S=0.60, H=0.3, raw_decision="CLARIFY")
    check("T4c: S=0.60, H=0.3 low → CLARIFY ok", r, "CLARIFY", False)

    # ─── Test 5: CLARIFY → EXECUTE needs buffer ─────────────
    print("\n📝 Test 5: CLARIFY to EXECUTE needs ε buffer")
    conv = "test_5"
    r = controller.apply(conv, S=0.55, H=0.2, raw_decision="CLARIFY")
    check("T5a: Enter CLARIFY", r, "CLARIFY", False)

    r = controller.apply(conv, S=0.72, H=0.1, raw_decision="EXECUTE")
    check("T5b: S=0.72 not enough (need >0.75)", r, "CLARIFY", True)

    r = controller.apply(conv, S=0.76, H=0.1, raw_decision="EXECUTE")
    check("T5c: S=0.76 above 0.75 → EXECUTE", r, "EXECUTE", False)

    # ─── Test 6: Independent conversations ──────────────────
    print("\n📝 Test 6: Different conversations are independent")
    r1 = controller.apply("conv_A", S=0.25, H=0.8, raw_decision="SAFE_FREEZE")
    r2 = controller.apply("conv_B", S=0.80, H=0.1, raw_decision="EXECUTE")
    check("T6a: Conv A frozen", r1, "SAFE_FREEZE", False)
    check("T6b: Conv B executing", r2, "EXECUTE", False)

    # ─── Test 7: Oscillation prevention (the AC test) ───────
    print("\n📝 Test 7: Oscillation prevention — the thermostat")
    conv = "test_7"
    decisions = []
    # Simulate S bouncing around 0.70 boundary
    s_values = [0.72, 0.69, 0.71, 0.68, 0.72, 0.67, 0.66, 0.64, 0.70, 0.76]
    for s in s_values:
        raw = "EXECUTE" if s > 0.70 else "CLARIFY"
        r = controller.apply(conv, S=s, H=0.1, raw_decision=raw)
        decisions.append(r["decision"])

    # Without hysteresis: [E,C,E,C,E,C,C,C,C,E] — 5 transitions
    # With hysteresis:    [E,E,E,E,E,E,E,C,C,E] — 2 transitions
    transitions = sum(1 for i in range(1, len(decisions))
                      if decisions[i] != decisions[i-1])
    print(f"  S values:  {s_values}")
    print(f"  Decisions: {decisions}")
    print(f"  Transitions: {transitions} (without hysteresis: ~5)")
    check("T7: ≤ 3 transitions (was ~5 without γ+)",
          {"decision": "PASS" if transitions <= 3 else "FAIL",
           "raw_decision": "PASS", "held": transitions > 3,
           "reason": f"{transitions} transitions"},
          "PASS", False)

    # ─── Test 8: CLARIFY exhaustion — لف ودار ────────────────
    print("\n📝 Test 8: CLARIFY exhaustion — evasion escalates to SAFE_STOP")
    conv = "test_8"
    controller.reset(conv)

    r = controller.apply(conv, S=0.55, H=0.15, raw_decision="CLARIFY")
    check("T8a: Enter CLARIFY (turn 1)", r, "CLARIFY", False)

    r = controller.apply(conv, S=0.58, H=0.12, raw_decision="CLARIFY")
    check("T8b: Still CLARIFY (turn 2)", r, "CLARIFY", False)

    r = controller.apply(conv, S=0.56, H=0.14, raw_decision="CLARIFY")
    check("T8c: 3rd CLARIFY → SAFE_STOP (exhausted)", r, "SAFE_STOP", False)

    # ─── Test 9: CLARIFY resets if user provides clear input ──
    print("\n📝 Test 9: CLARIFY resets when user clarifies properly")
    conv = "test_9"
    controller.reset(conv)

    r = controller.apply(conv, S=0.55, H=0.15, raw_decision="CLARIFY")
    check("T9a: Enter CLARIFY", r, "CLARIFY", False)

    r = controller.apply(conv, S=0.55, H=0.15, raw_decision="CLARIFY")
    check("T9b: Still CLARIFY (turn 2)", r, "CLARIFY", False)

    # User provides a clear message → EXECUTE
    r = controller.apply(conv, S=0.80, H=0.05, raw_decision="EXECUTE")
    check("T9c: User clarifies → EXECUTE (need >0.75 due to ε)", r, "EXECUTE", False)

    # ─── Summary ────────────────────────────────────────────
    print(f"\n{'=' * 65}")
    total = passed + failed
    print(f"Results: {passed}/{total} passed", end="")
    if failed:
        print(f" — {failed} FAILED ❌")
    else:
        print(" ✅ All clear.")
    print(f"{'=' * 65}")

    return failed == 0


if __name__ == "__main__":
    success = _run_tests()
    exit(0 if success else 1)
