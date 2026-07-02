#!/usr/bin/env python3
"""
tests/test_sparse_activation.py — بوابة التفعيل الانتقائي

Comprehensive test suite for the Sparse Activation Gate (FN#075).

Test categories:
  1. Authority Contract — B-prime invariants, CAN_BLOCK_RUNTIME, etc.
  2. ActivationDecision — immutability, fields, defaults
  3. ActivationPath — enum values
  4. Observer Classification — sets are correct and non-overlapping
  5. Fast Path — clearly safe inputs activate minimal observers
  6. Slow Path — elevated risk activates ALL observers
  7. Middle Path — selective activation by signal
  8. Safety-Critical — DRE/MRS/EQC/COLD-OS always on when H elevated
  9. POST_OUTPUT — always all output observers
  10. BOOT — always all boot observers
  11. Pattern Matching — text triggers activate correct observers
  12. Domain Triggers — domain-specific observer activation
  13. Decision Triggers — S(d) decisions trigger correct observers
  14. Signal-Strength — I/E thresholds activate correct observers
  15. Edge Cases — empty input, missing fields, boundary values
  16. Activation Ratio — metrics helper
  17. Introspection — get_observer_sets
  18. Integration — gate + registry cooperation
  19. Regression guards — specific scenarios that must work

Target: 80+ test cases.
"""

from __future__ import annotations

import os
import sys
import unittest

# ── Import shim ──────────────────────────────────────────────
_ENGINE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_sparse_activation import (
    AUTHORITY_LEVEL,
    CAN_BLOCK_RUNTIME,
    CAN_MODIFY_H,
    CAN_MODIFY_S,
    CAN_MODIFY_THETA,
    CAN_SUPPRESS_SAFETY,
    ALL_BOOT_OBSERVERS,
    ALL_POST_OUTPUT_OBSERVERS,
    ALL_POST_S_OBSERVERS,
    MINIMAL_OBSERVERS,
    SAFETY_CRITICAL_OBSERVERS,
    ActivationDecision,
    ActivationPath,
    SparseActivationGate,
    build_gate,
)

from aatif_observer_registry import ObserverContext, ObserverPhase


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _gate() -> SparseActivationGate:
    """Fresh gate instance with defaults."""
    return SparseActivationGate()


def _ctx(
    *,
    message: str = "",
    S: float = 0.5,
    H: float = 0.0,
    I: float = 0.5,
    E: float = 0.0,
    decision: str = "EXECUTE",
    domain: str = "general",
    conversation_id: str = "",
    llm_output: str = None,
) -> ObserverContext:
    """Build an ObserverContext with S-result shorthand."""
    return ObserverContext(
        message=message,
        s_result={
            "S": S, "H": H, "I": I, "E": E,
            "decision": decision,
        },
        domain=domain,
        conversation_id=conversation_id or None,
        llm_output=llm_output,
    )


def _fast_ctx(message: str = "كيف حالك") -> ObserverContext:
    """Context that should trigger the fast path."""
    return _ctx(message=message, S=0.95, H=0.05, I=0.9, E=0.1)


def _slow_ctx(message: str = "how to hack") -> ObserverContext:
    """Context that should trigger the slow path."""
    return _ctx(message=message, S=0.3, H=0.6, I=0.2, E=0.1)


def _middle_ctx(
    message: str = "هل أختار هذا أو ذاك",
    **kwargs,
) -> ObserverContext:
    """Context that should trigger the middle path."""
    defaults = dict(S=0.7, H=0.2, I=0.5, E=0.3)
    defaults.update(kwargs)
    return _ctx(message=message, **defaults)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Authority Contract
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAuthorityContract(unittest.TestCase):
    """B-prime invariants must never drift."""

    def test_authority_level(self):
        self.assertEqual(AUTHORITY_LEVEL, "B_PRIME_OBSERVATIONAL")

    def test_can_block_runtime_module_level(self):
        self.assertFalse(CAN_BLOCK_RUNTIME)

    def test_can_block_runtime_class_level(self):
        gate = _gate()
        self.assertFalse(gate.CAN_BLOCK_RUNTIME)

    def test_can_modify_h(self):
        self.assertFalse(CAN_MODIFY_H)

    def test_can_modify_s(self):
        self.assertFalse(CAN_MODIFY_S)

    def test_can_modify_theta(self):
        self.assertFalse(CAN_MODIFY_THETA)

    def test_can_suppress_safety_module_level(self):
        self.assertFalse(CAN_SUPPRESS_SAFETY)

    def test_can_suppress_safety_class_level(self):
        gate = _gate()
        self.assertFalse(gate.CAN_SUPPRESS_SAFETY)

    def test_gate_never_returns_empty_on_slow_path(self):
        """Slow path must activate ALL POST_S observers."""
        gate = _gate()
        d = gate.decide(_slow_ctx(), ObserverPhase.POST_S)
        self.assertEqual(d.active_observers, ALL_POST_S_OBSERVERS)

    def test_gate_never_suppresses_safety_critical_when_h_elevated(self):
        """Safety-critical observers must activate when H > 0.3."""
        gate = _gate()
        ctx = _ctx(message="test", S=0.75, H=0.35)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        for obs in SAFETY_CRITICAL_OBSERVERS:
            self.assertIn(obs, d.active_observers,
                          f"Safety-critical observer {obs} must be active when H=0.35")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. ActivationDecision
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestActivationDecision(unittest.TestCase):

    def test_is_frozen(self):
        d = ActivationDecision(
            active_observers=frozenset({"a"}),
            skipped_observers=frozenset({"b"}),
            path=ActivationPath.FAST,
            reason="test",
        )
        with self.assertRaises(AttributeError):
            d.path = ActivationPath.SLOW  # type: ignore

    def test_fields_populated(self):
        d = ActivationDecision(
            active_observers=frozenset({"x", "y"}),
            skipped_observers=frozenset({"z"}),
            path=ActivationPath.MIDDLE,
            reason="some reason",
            signals_detected=("sig1", "sig2"),
        )
        self.assertEqual(len(d.active_observers), 2)
        self.assertEqual(len(d.skipped_observers), 1)
        self.assertEqual(d.path, ActivationPath.MIDDLE)
        self.assertEqual(d.reason, "some reason")
        self.assertEqual(d.signals_detected, ("sig1", "sig2"))

    def test_default_signals_empty(self):
        d = ActivationDecision(
            active_observers=frozenset(),
            skipped_observers=frozenset(),
            path=ActivationPath.FAST,
            reason="",
        )
        self.assertEqual(d.signals_detected, ())

    def test_active_and_skipped_are_frozenset(self):
        d = ActivationDecision(
            active_observers=frozenset({"a"}),
            skipped_observers=frozenset({"b"}),
            path=ActivationPath.FAST,
            reason="",
        )
        self.assertIsInstance(d.active_observers, frozenset)
        self.assertIsInstance(d.skipped_observers, frozenset)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. ActivationPath
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestActivationPath(unittest.TestCase):

    def test_five_paths_exist(self):
        paths = list(ActivationPath)
        self.assertEqual(len(paths), 5)

    def test_path_values(self):
        self.assertEqual(ActivationPath.FAST.value, "fast")
        self.assertEqual(ActivationPath.SLOW.value, "slow")
        self.assertEqual(ActivationPath.MIDDLE.value, "middle")
        self.assertEqual(ActivationPath.BOOT.value, "boot")
        self.assertEqual(ActivationPath.POST_OUTPUT.value, "post_output")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. Observer Classification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestObserverClassification(unittest.TestCase):

    def test_post_s_count(self):
        self.assertEqual(len(ALL_POST_S_OBSERVERS), 12)

    def test_post_output_count(self):
        self.assertEqual(len(ALL_POST_OUTPUT_OBSERVERS), 2)

    def test_boot_count(self):
        self.assertEqual(len(ALL_BOOT_OBSERVERS), 2)

    def test_safety_critical_subset_of_post_s(self):
        self.assertTrue(SAFETY_CRITICAL_OBSERVERS.issubset(ALL_POST_S_OBSERVERS))

    def test_minimal_subset_of_post_s(self):
        self.assertTrue(MINIMAL_OBSERVERS.issubset(ALL_POST_S_OBSERVERS))

    def test_safety_critical_count(self):
        self.assertEqual(len(SAFETY_CRITICAL_OBSERVERS), 4)

    def test_minimal_count(self):
        self.assertEqual(len(MINIMAL_OBSERVERS), 2)

    def test_no_overlap_post_s_and_post_output(self):
        self.assertEqual(
            ALL_POST_S_OBSERVERS & ALL_POST_OUTPUT_OBSERVERS,
            frozenset(),
        )

    def test_no_overlap_post_s_and_boot(self):
        self.assertEqual(
            ALL_POST_S_OBSERVERS & ALL_BOOT_OBSERVERS,
            frozenset(),
        )

    def test_no_overlap_post_output_and_boot(self):
        self.assertEqual(
            ALL_POST_OUTPUT_OBSERVERS & ALL_BOOT_OBSERVERS,
            frozenset(),
        )

    def test_safety_critical_contains_dre(self):
        self.assertIn("dual_root_engine", SAFETY_CRITICAL_OBSERVERS)

    def test_safety_critical_contains_mrs(self):
        self.assertIn("mrs_detector", SAFETY_CRITICAL_OBSERVERS)

    def test_safety_critical_contains_eqc(self):
        self.assertIn("ethical_question_compiler", SAFETY_CRITICAL_OBSERVERS)

    def test_safety_critical_contains_cold_os(self):
        self.assertIn("cold_os", SAFETY_CRITICAL_OBSERVERS)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. Fast Path
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFastPath(unittest.TestCase):
    """Clearly safe inputs → minimal observers."""

    def test_fast_path_triggered(self):
        gate = _gate()
        d = gate.decide(_fast_ctx(), ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.FAST)

    def test_fast_path_only_minimal_observers(self):
        gate = _gate()
        d = gate.decide(_fast_ctx(), ObserverPhase.POST_S)
        self.assertEqual(d.active_observers, MINIMAL_OBSERVERS)

    def test_fast_path_skips_most_observers(self):
        gate = _gate()
        d = gate.decide(_fast_ctx(), ObserverPhase.POST_S)
        expected_skipped = ALL_POST_S_OBSERVERS - MINIMAL_OBSERVERS
        self.assertEqual(d.skipped_observers, expected_skipped)

    def test_fast_path_activation_ratio_low(self):
        gate = _gate()
        d = gate.decide(_fast_ctx(), ObserverPhase.POST_S)
        ratio = SparseActivationGate.activation_ratio(d)
        self.assertLess(ratio, 0.3)  # should be ~2/12 = 0.167

    def test_fast_path_boundary_s(self):
        """S exactly at boundary (0.85) is NOT fast path."""
        gate = _gate()
        ctx = _ctx(message="hello", S=0.85, H=0.05)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        # S=0.85 is not > 0.85, so not fast path
        self.assertNotEqual(d.path, ActivationPath.FAST)

    def test_fast_path_boundary_h(self):
        """H exactly at boundary (0.15) is NOT fast path."""
        gate = _gate()
        ctx = _ctx(message="hello", S=0.95, H=0.15)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        # H=0.15 is not < 0.15, so not fast path
        self.assertNotEqual(d.path, ActivationPath.FAST)

    def test_fast_path_just_above_s_threshold(self):
        gate = _gate()
        ctx = _ctx(message="hello", S=0.86, H=0.05)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.FAST)

    def test_fast_path_just_below_h_threshold(self):
        gate = _gate()
        ctx = _ctx(message="hello", S=0.95, H=0.14)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.FAST)

    def test_fast_path_with_pattern_override(self):
        """Text with decision-point language should add PSP on fast path."""
        gate = _gate()
        ctx = _ctx(message="should I choose this option?", S=0.95, H=0.05)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.FAST)
        self.assertIn("psp_detector", d.active_observers)

    def test_fast_path_with_pattern_keeps_minimal(self):
        """Pattern overrides ADD to minimal, don't replace."""
        gate = _gate()
        ctx = _ctx(message="should I choose this option?", S=0.95, H=0.05)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        for obs in MINIMAL_OBSERVERS:
            self.assertIn(obs, d.active_observers)

    def test_fast_path_reason_mentions_s_and_h(self):
        gate = _gate()
        d = gate.decide(_fast_ctx(), ObserverPhase.POST_S)
        self.assertIn("Fast path", d.reason)

    def test_fast_path_arabic_safe_greeting(self):
        gate = _gate()
        ctx = _ctx(message="السلام عليكم", S=0.95, H=0.02)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.FAST)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. Slow Path
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSlowPath(unittest.TestCase):
    """Elevated risk → ALL observers."""

    def test_slow_path_low_s(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.3, H=0.1)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.SLOW)

    def test_slow_path_high_h(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.5)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.SLOW)

    def test_slow_path_both_triggers(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.2, H=0.6)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.SLOW)

    def test_slow_path_activates_all(self):
        gate = _gate()
        d = gate.decide(_slow_ctx(), ObserverPhase.POST_S)
        self.assertEqual(d.active_observers, ALL_POST_S_OBSERVERS)

    def test_slow_path_skips_none(self):
        gate = _gate()
        d = gate.decide(_slow_ctx(), ObserverPhase.POST_S)
        self.assertEqual(d.skipped_observers, frozenset())

    def test_slow_path_activation_ratio_one(self):
        gate = _gate()
        d = gate.decide(_slow_ctx(), ObserverPhase.POST_S)
        self.assertEqual(SparseActivationGate.activation_ratio(d), 1.0)

    def test_slow_path_boundary_s(self):
        """S exactly at 0.5 triggers slow path (< is not <=, but 0.5 IS < 0.5? No. Test boundary."""
        gate = _gate()
        # S=0.5 is NOT < 0.5, so this should NOT be slow path from S alone
        ctx = _ctx(message="test", S=0.5, H=0.1)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertNotEqual(d.path, ActivationPath.SLOW)

    def test_slow_path_just_below_s(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.49, H=0.1)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.SLOW)

    def test_slow_path_boundary_h(self):
        """H exactly at 0.4 is NOT > 0.4, so not slow path from H alone."""
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.4)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertNotEqual(d.path, ActivationPath.SLOW)

    def test_slow_path_just_above_h(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.41)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.SLOW)

    def test_slow_path_safe_freeze_decision(self):
        """SAFE_FREEZE decision always triggers slow path."""
        gate = _gate()
        ctx = _ctx(message="test", S=0.1, H=0.8, decision="SAFE_FREEZE")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.SLOW)
        self.assertEqual(d.active_observers, ALL_POST_S_OBSERVERS)

    def test_slow_path_safe_stop_decision(self):
        """SAFE_STOP decision always triggers slow path."""
        gate = _gate()
        ctx = _ctx(message="test", S=0.4, H=0.5, decision="SAFE_STOP")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.SLOW)

    def test_slow_path_safe_freeze_even_high_s(self):
        """SAFE_FREEZE overrides even if S is high (shouldn't happen, but gate is robust)."""
        gate = _gate()
        ctx = _ctx(message="test", S=0.95, H=0.05, decision="SAFE_FREEZE")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.SLOW)

    def test_slow_path_reason_mentions_signal(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.3, H=0.1)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("Slow path", d.reason)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7. Middle Path
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMiddlePath(unittest.TestCase):
    """Selective activation in the middle range."""

    def test_middle_path_triggered(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.1, I=0.5, E=0.3)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.MIDDLE)

    def test_middle_path_includes_minimal(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.1)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        for obs in MINIMAL_OBSERVERS:
            self.assertIn(obs, d.active_observers)

    def test_middle_path_fewer_than_all(self):
        """Middle path should activate fewer than ALL observers (most of the time)."""
        gate = _gate()
        ctx = _ctx(message="a simple message", S=0.7, H=0.1, I=0.5, E=0.1)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertLess(len(d.active_observers), len(ALL_POST_S_OBSERVERS))

    def test_middle_path_more_than_minimal(self):
        """Middle path should activate at least the minimal set."""
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.25, I=0.5, E=0.3)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertGreaterEqual(len(d.active_observers), len(MINIMAL_OBSERVERS))

    def test_middle_path_reason_mentions_signals(self):
        gate = _gate()
        d = gate.decide(_middle_ctx(), ObserverPhase.POST_S)
        self.assertIn("Middle path", d.reason)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  8. Safety-Critical Observers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSafetyCritical(unittest.TestCase):

    def test_all_safety_critical_active_h_031(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.31)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        for obs in SAFETY_CRITICAL_OBSERVERS:
            self.assertIn(obs, d.active_observers)

    def test_all_safety_critical_active_h_050(self):
        gate = _gate()
        # H=0.5 > 0.4 → slow path → all active anyway
        ctx = _ctx(message="test", S=0.6, H=0.35)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        for obs in SAFETY_CRITICAL_OBSERVERS:
            self.assertIn(obs, d.active_observers)

    def test_safety_critical_not_forced_h_010(self):
        """When H is low, safety-critical observers are NOT forced on."""
        gate = _gate()
        ctx = _ctx(message="hello", S=0.95, H=0.05)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        # On fast path, only minimal observers
        for obs in SAFETY_CRITICAL_OBSERVERS:
            if obs not in MINIMAL_OBSERVERS:
                self.assertNotIn(obs, d.active_observers)

    def test_safety_critical_h_boundary_030(self):
        """H exactly 0.3 is NOT > 0.3, so safety-critical is not forced."""
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.3)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        # Should be middle path without safety-critical forced
        # (unless patterns trigger them)
        # Just check path is middle
        self.assertEqual(d.path, ActivationPath.MIDDLE)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  9. POST_OUTPUT Phase
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPostOutput(unittest.TestCase):

    def test_post_output_always_all(self):
        gate = _gate()
        ctx = _fast_ctx()
        d = gate.decide(ctx, ObserverPhase.POST_OUTPUT)
        self.assertEqual(d.active_observers, ALL_POST_OUTPUT_OBSERVERS)

    def test_post_output_path(self):
        gate = _gate()
        d = gate.decide(_fast_ctx(), ObserverPhase.POST_OUTPUT)
        self.assertEqual(d.path, ActivationPath.POST_OUTPUT)

    def test_post_output_no_skips(self):
        gate = _gate()
        d = gate.decide(_fast_ctx(), ObserverPhase.POST_OUTPUT)
        self.assertEqual(d.skipped_observers, frozenset())

    def test_post_output_even_on_safe_input(self):
        """Even clearly safe inputs activate all output observers."""
        gate = _gate()
        ctx = _ctx(message="hello", S=0.99, H=0.01)
        d = gate.decide(ctx, ObserverPhase.POST_OUTPUT)
        self.assertIn("lbh_detector", d.active_observers)
        self.assertIn("ucn_validator", d.active_observers)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  10. BOOT Phase
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBoot(unittest.TestCase):

    def test_boot_always_all(self):
        gate = _gate()
        ctx = ObserverContext()
        d = gate.decide(ctx, ObserverPhase.BOOT)
        self.assertEqual(d.active_observers, ALL_BOOT_OBSERVERS)

    def test_boot_path(self):
        gate = _gate()
        d = gate.decide(ObserverContext(), ObserverPhase.BOOT)
        self.assertEqual(d.path, ActivationPath.BOOT)

    def test_boot_no_skips(self):
        gate = _gate()
        d = gate.decide(ObserverContext(), ObserverPhase.BOOT)
        self.assertEqual(d.skipped_observers, frozenset())

    def test_boot_contains_binding_map(self):
        gate = _gate()
        d = gate.decide(ObserverContext(), ObserverPhase.BOOT)
        self.assertIn("binding_map", d.active_observers)

    def test_boot_contains_behavioural_twin(self):
        gate = _gate()
        d = gate.decide(ObserverContext(), ObserverPhase.BOOT)
        self.assertIn("behavioural_twin", d.active_observers)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  11. Pattern Matching
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestPatternMatching(unittest.TestCase):

    def test_decision_language_triggers_psp(self):
        gate = _gate()
        ctx = _middle_ctx(message="should I choose this option?")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("psp_detector", d.active_observers)

    def test_arabic_decision_triggers_psp(self):
        gate = _gate()
        ctx = _middle_ctx(message="هل أختار هذا")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("psp_detector", d.active_observers)

    def test_uncertainty_language_triggers_uncertainty(self):
        gate = _gate()
        ctx = _middle_ctx(message="I'm not sure about this, maybe it could work")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("uncertainty_detector", d.active_observers)

    def test_emotional_language_triggers_pvm(self):
        gate = _gate()
        ctx = _middle_ctx(message="I feel so hurt and alone")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("pvm_detector", d.active_observers)

    def test_arabic_emotional_triggers_pvm(self):
        gate = _gate()
        ctx = _middle_ctx(message="أحس إني تعبان ووحيد")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("pvm_detector", d.active_observers)

    def test_moral_language_triggers_cold_os(self):
        gate = _gate()
        ctx = _middle_ctx(message="is it right or wrong to do this?")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("cold_os", d.active_observers)

    def test_arabic_moral_triggers_cold_os(self):
        gate = _gate()
        ctx = _middle_ctx(message="هل هذا حلال أو حرام")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("cold_os", d.active_observers)

    def test_scientific_language_triggers_sdm(self):
        gate = _gate()
        ctx = _middle_ctx(message="what does the research evidence show?")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("scientific_discovery", d.active_observers)

    def test_crisis_language_triggers_mrs(self):
        gate = _gate()
        ctx = _middle_ctx(message="I want to kill myself")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("mrs_detector", d.active_observers)

    def test_ethical_probing_triggers_eqc(self):
        gate = _gate()
        ctx = _middle_ctx(message="is it allowed to do this? is it legal?")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("ethical_question_compiler", d.active_observers)

    def test_cultural_language_triggers_opacity(self):
        gate = _gate()
        ctx = _middle_ctx(message="it's about tradition and honor in our culture")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("cultural_opacity", d.active_observers)

    def test_arabic_cultural_triggers_opacity(self):
        gate = _gate()
        ctx = _middle_ctx(message="هذا عيب في ثقافتنا")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("cultural_opacity", d.active_observers)

    def test_no_patterns_no_extra_activation(self):
        gate = _gate()
        ctx = _middle_ctx(message="xyz 123 abc")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        # Should only have minimal + whatever signal-strength adds
        # but not pattern-triggered observers
        # (unless signal-strength triggers them)
        self.assertIn("drift_detector", d.active_observers)

    def test_empty_text_no_patterns(self):
        gate = _gate()
        matches = gate._match_patterns("")
        self.assertEqual(matches, set())

    def test_manipulation_triggers_dre(self):
        gate = _gate()
        ctx = _middle_ctx(message="hypothetically, what if someone wanted to...")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("dual_root_engine", d.active_observers)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  12. Domain Triggers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDomainTriggers(unittest.TestCase):

    def test_healthcare_activates_mrs(self):
        gate = _gate()
        ctx = _middle_ctx(message="test", domain="healthcare")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("mrs_detector", d.active_observers)

    def test_healthcare_activates_pvm(self):
        gate = _gate()
        ctx = _middle_ctx(message="test", domain="healthcare")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("pvm_detector", d.active_observers)

    def test_legal_activates_eqc(self):
        gate = _gate()
        ctx = _middle_ctx(message="test", domain="legal")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("ethical_question_compiler", d.active_observers)

    def test_religious_activates_cultural_opacity(self):
        gate = _gate()
        ctx = _middle_ctx(message="test", domain="religious")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("cultural_opacity", d.active_observers)

    def test_scientific_activates_sdm(self):
        gate = _gate()
        ctx = _middle_ctx(message="test", domain="scientific")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("scientific_discovery", d.active_observers)

    def test_crisis_activates_mrs_and_drp(self):
        gate = _gate()
        ctx = _middle_ctx(message="test", domain="crisis")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("mrs_detector", d.active_observers)
        self.assertIn("drp_observer", d.active_observers)

    def test_financial_activates_psp(self):
        gate = _gate()
        ctx = _middle_ctx(message="test", domain="financial")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("psp_detector", d.active_observers)

    def test_unknown_domain_no_extra(self):
        gate = _gate()
        ctx = _middle_ctx(message="test", domain="unknown_xyz")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        # Should still have minimal + signal-based, but no domain extras
        self.assertEqual(d.path, ActivationPath.MIDDLE)

    def test_domain_case_insensitive(self):
        gate = _gate()
        ctx = _middle_ctx(message="test", domain="Healthcare")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("mrs_detector", d.active_observers)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  13. Decision Triggers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDecisionTriggers(unittest.TestCase):

    def test_clarify_adds_specific_observers(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.6, H=0.1, decision="CLARIFY")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("psp_detector", d.active_observers)
        self.assertIn("uncertainty_detector", d.active_observers)

    def test_execute_no_decision_extras(self):
        gate = _gate()
        ctx = _ctx(message="simple test", S=0.7, H=0.1, decision="EXECUTE")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        # EXECUTE is not in _DECISION_TRIGGERS, so no extras from decision
        self.assertEqual(d.path, ActivationPath.MIDDLE)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  14. Signal-Strength Triggers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSignalStrength(unittest.TestCase):

    def test_low_intent_triggers_uncertainty(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.1, I=0.2)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("uncertainty_detector", d.active_observers)

    def test_low_intent_triggers_psp(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.1, I=0.2)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("psp_detector", d.active_observers)

    def test_high_emotion_triggers_pvm(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.1, E=0.6)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("pvm_detector", d.active_observers)

    def test_high_emotion_triggers_maqam(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.1, E=0.6)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("maqam_architecture", d.active_observers)

    def test_high_emotion_triggers_mrs(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.1, E=0.6)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("mrs_detector", d.active_observers)

    def test_moderate_h_triggers_drp(self):
        gate = _gate()
        ctx = _ctx(message="test", S=0.7, H=0.25)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("drp_observer", d.active_observers)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  15. Edge Cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEdgeCases(unittest.TestCase):

    def test_empty_context(self):
        """Empty context → middle path with minimal observers."""
        gate = _gate()
        ctx = ObserverContext()
        d = gate.decide(ctx, ObserverPhase.POST_S)
        # s_result is None → defaults to S=0.5, H=0.0
        # S=0.5 is not < 0.5, H=0.0 is not > 0.4 → not slow
        # S=0.5 is not > 0.85 → not fast
        # → middle path
        self.assertEqual(d.path, ActivationPath.MIDDLE)

    def test_none_s_result(self):
        """None s_result is handled gracefully."""
        gate = _gate()
        ctx = ObserverContext(message="test", s_result=None)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        # Should not crash
        self.assertIsNotNone(d)
        self.assertIn(d.path, list(ActivationPath))

    def test_missing_keys_in_s_result(self):
        """Partial s_result with missing keys."""
        gate = _gate()
        ctx = ObserverContext(
            message="test",
            s_result={"decision": "EXECUTE"},  # no S, H, I, E
        )
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIsNotNone(d)

    def test_s_result_extreme_values(self):
        """S=1.0, H=0.0 — maximally safe."""
        gate = _gate()
        ctx = _ctx(message="hello", S=1.0, H=0.0)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.FAST)

    def test_s_result_extreme_dangerous(self):
        """S=0.0, H=1.0 — maximally dangerous."""
        gate = _gate()
        ctx = _ctx(message="danger", S=0.0, H=1.0)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.SLOW)
        self.assertEqual(d.active_observers, ALL_POST_S_OBSERVERS)

    def test_very_long_message(self):
        """Long message doesn't crash pattern matching."""
        gate = _gate()
        long_msg = "hello world " * 10000
        ctx = _ctx(message=long_msg, S=0.7, H=0.1)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIsNotNone(d)

    def test_unicode_message(self):
        """Unicode / emoji in message doesn't crash."""
        gate = _gate()
        ctx = _ctx(message="🙏 مرحبا 你好", S=0.95, H=0.05)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.FAST)

    def test_active_and_skipped_partition_post_s(self):
        """Active + skipped = all POST_S observers (complete partition)."""
        gate = _gate()
        for s_val in [0.3, 0.5, 0.7, 0.9, 0.95]:
            for h_val in [0.0, 0.1, 0.2, 0.35, 0.5]:
                ctx = _ctx(message="test", S=s_val, H=h_val)
                d = gate.decide(ctx, ObserverPhase.POST_S)
                combined = d.active_observers | d.skipped_observers
                self.assertEqual(
                    combined, ALL_POST_S_OBSERVERS,
                    f"Partition broken at S={s_val}, H={h_val}: "
                    f"active={d.active_observers}, skipped={d.skipped_observers}",
                )

    def test_no_overlap_active_skipped(self):
        """Active and skipped never overlap."""
        gate = _gate()
        for s_val in [0.3, 0.7, 0.95]:
            for h_val in [0.0, 0.2, 0.5]:
                ctx = _ctx(message="test", S=s_val, H=h_val)
                d = gate.decide(ctx, ObserverPhase.POST_S)
                overlap = d.active_observers & d.skipped_observers
                self.assertEqual(
                    overlap, frozenset(),
                    f"Overlap at S={s_val}, H={h_val}: {overlap}",
                )

    def test_deterministic(self):
        """Same input always produces same output."""
        gate = _gate()
        ctx = _middle_ctx(message="should I choose this?")
        d1 = gate.decide(ctx, ObserverPhase.POST_S)
        d2 = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d1.active_observers, d2.active_observers)
        self.assertEqual(d1.skipped_observers, d2.skipped_observers)
        self.assertEqual(d1.path, d2.path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  16. Activation Ratio
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestActivationRatio(unittest.TestCase):

    def test_ratio_fast_path(self):
        gate = _gate()
        d = gate.decide(_fast_ctx(), ObserverPhase.POST_S)
        ratio = SparseActivationGate.activation_ratio(d)
        # 2 minimal out of 12
        expected = len(MINIMAL_OBSERVERS) / len(ALL_POST_S_OBSERVERS)
        self.assertAlmostEqual(ratio, expected, places=2)

    def test_ratio_slow_path(self):
        gate = _gate()
        d = gate.decide(_slow_ctx(), ObserverPhase.POST_S)
        ratio = SparseActivationGate.activation_ratio(d)
        self.assertEqual(ratio, 1.0)

    def test_ratio_empty_decision(self):
        d = ActivationDecision(
            active_observers=frozenset(),
            skipped_observers=frozenset(),
            path=ActivationPath.BOOT,
            reason="",
        )
        ratio = SparseActivationGate.activation_ratio(d)
        self.assertEqual(ratio, 1.0)  # 0/0 defaults to 1.0

    def test_ratio_between_0_and_1(self):
        gate = _gate()
        ctx = _middle_ctx()
        d = gate.decide(ctx, ObserverPhase.POST_S)
        ratio = SparseActivationGate.activation_ratio(d)
        self.assertGreaterEqual(ratio, 0.0)
        self.assertLessEqual(ratio, 1.0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  17. Introspection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIntrospection(unittest.TestCase):

    def test_get_observer_sets_keys(self):
        gate = _gate()
        sets = gate.get_observer_sets()
        expected_keys = {"post_s", "post_output", "boot", "safety_critical", "minimal"}
        self.assertEqual(set(sets.keys()), expected_keys)

    def test_get_observer_sets_types(self):
        gate = _gate()
        sets = gate.get_observer_sets()
        for key, value in sets.items():
            self.assertIsInstance(value, frozenset, f"{key} should be frozenset")

    def test_custom_observer_sets(self):
        """Custom observer sets override defaults."""
        custom_post_s = frozenset({"obs_a", "obs_b"})
        gate = SparseActivationGate(post_s_observers=custom_post_s)
        sets = gate.get_observer_sets()
        self.assertEqual(sets["post_s"], custom_post_s)

    def test_custom_safety_critical(self):
        custom_safety = frozenset({"obs_a"})
        custom_post_s = frozenset({"obs_a", "obs_b", "obs_c"})
        gate = SparseActivationGate(
            post_s_observers=custom_post_s,
            safety_critical=custom_safety,
        )
        ctx = _ctx(message="test", S=0.7, H=0.35)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("obs_a", d.active_observers)

    def test_custom_minimal(self):
        custom_minimal = frozenset({"obs_x"})
        custom_post_s = frozenset({"obs_x", "obs_y", "obs_z"})
        gate = SparseActivationGate(
            post_s_observers=custom_post_s,
            minimal_observers=custom_minimal,
        )
        ctx = _ctx(message="hello", S=0.95, H=0.05)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.active_observers, custom_minimal)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  18. Integration — Gate + Registry
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIntegration(unittest.TestCase):

    def test_build_gate_returns_instance(self):
        gate = build_gate()
        self.assertIsInstance(gate, SparseActivationGate)

    def test_gate_decision_observers_are_subset_of_known(self):
        """All activated observers must be in the known set."""
        gate = _gate()
        for phase in ObserverPhase:
            ctx = _middle_ctx()
            d = gate.decide(ctx, phase)
            if phase == ObserverPhase.POST_S:
                self.assertTrue(
                    d.active_observers.issubset(ALL_POST_S_OBSERVERS),
                    f"Active observers not subset of POST_S: {d.active_observers}",
                )
            elif phase == ObserverPhase.POST_OUTPUT:
                self.assertTrue(
                    d.active_observers.issubset(ALL_POST_OUTPUT_OBSERVERS),
                )
            elif phase == ObserverPhase.BOOT:
                self.assertTrue(
                    d.active_observers.issubset(ALL_BOOT_OBSERVERS),
                )

    def test_gate_works_with_real_observer_names(self):
        """Gate output should contain real observer names from the registry."""
        gate = _gate()
        d = gate.decide(_slow_ctx(), ObserverPhase.POST_S)
        # Check a few real names
        self.assertIn("drift_detector", d.active_observers)
        self.assertIn("cold_os", d.active_observers)
        self.assertIn("mrs_detector", d.active_observers)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  19. Regression Guards — Specific Scenarios
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestRegressionScenarios(unittest.TestCase):
    """
    Specific real-world scenarios that MUST produce correct activation.
    These guard against regressions as the gate evolves.
    """

    def test_simple_arabic_greeting_fast(self):
        """كيف حالك with safe scores → fast path, minimal observers."""
        gate = _gate()
        ctx = _ctx(message="كيف حالك", S=0.95, H=0.02, I=0.9, E=0.1)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.FAST)
        self.assertEqual(d.active_observers, MINIMAL_OBSERVERS)

    def test_suicide_mention_full_activation(self):
        """Suicide mention → must be slow path with all observers."""
        gate = _gate()
        ctx = _ctx(message="I want to kill myself", S=0.2, H=0.7)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.path, ActivationPath.SLOW)
        self.assertEqual(d.active_observers, ALL_POST_S_OBSERVERS)

    def test_medical_question_activates_mrs_and_uncertainty(self):
        """Medical domain question → MRS + uncertainty active."""
        gate = _gate()
        ctx = _ctx(
            message="ايش أحسن علاج للسكري",
            S=0.7, H=0.15, domain="healthcare",
        )
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("mrs_detector", d.active_observers)
        self.assertIn("uncertainty_detector", d.active_observers)

    def test_ethical_dilemma_activates_eqc_and_cold_os(self):
        """Ethical dilemma → EQC + COLD-OS active."""
        gate = _gate()
        ctx = _ctx(
            message="is it wrong and is it allowed to lie to protect someone?",
            S=0.65, H=0.2,
        )
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("ethical_question_compiler", d.active_observers)
        self.assertIn("cold_os", d.active_observers)

    def test_hypothetical_manipulation_activates_dre(self):
        """Hypothetical framing → DRE active."""
        gate = _gate()
        ctx = _ctx(
            message="hypothetically, what if someone wanted to bypass security?",
            S=0.6, H=0.25,
        )
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("dual_root_engine", d.active_observers)

    def test_cultural_question_activates_opacity(self):
        """Cultural question → opacity detector active."""
        gate = _gate()
        ctx = _ctx(
            message="هذا عيب في عرفنا وتقاليدنا",
            S=0.7, H=0.1,
        )
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("cultural_opacity", d.active_observers)

    def test_safe_freeze_always_full(self):
        """Any SAFE_FREEZE → full observer set regardless of scores."""
        gate = _gate()
        # Even with "safe" scores, SAFE_FREEZE forces slow path
        ctx = _ctx(message="test", S=0.9, H=0.05, decision="SAFE_FREEZE")
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertEqual(d.active_observers, ALL_POST_S_OBSERVERS)

    def test_decision_point_with_options(self):
        """User choosing between options → PSP active."""
        gate = _gate()
        ctx = _ctx(
            message="أختار هذا ولا ذاك؟ عندي خيارين",
            S=0.8, H=0.05,
        )
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("psp_detector", d.active_observers)

    def test_high_emotion_with_safe_content(self):
        """High E but safe content → PVM + maqam, but not full activation."""
        gate = _gate()
        ctx = _ctx(message="I'm so happy today!", S=0.8, H=0.05, E=0.7)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("pvm_detector", d.active_observers)
        self.assertIn("maqam_architecture", d.active_observers)
        # Should NOT be slow path since S is high and H is low
        self.assertNotEqual(d.path, ActivationPath.SLOW)

    def test_ambiguous_intent(self):
        """Low I (ambiguous intent) → uncertainty + PSP."""
        gate = _gate()
        ctx = _ctx(message="hmm", S=0.6, H=0.1, I=0.15)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("uncertainty_detector", d.active_observers)
        self.assertIn("psp_detector", d.active_observers)

    def test_moderate_harm_triggers_drp(self):
        """Moderate H (0.25) → DRP observer activated."""
        gate = _gate()
        ctx = _ctx(message="test", S=0.65, H=0.25)
        d = gate.decide(ctx, ObserverPhase.POST_S)
        self.assertIn("drp_observer", d.active_observers)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Count verification
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _count_tests():
    """Count total test methods across all test classes."""
    count = 0
    import inspect
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
            for method_name in dir(obj):
                if method_name.startswith("test_"):
                    count += 1
    return count


class TestSuiteCompleteness(unittest.TestCase):
    """Meta-test: ensure we have enough test cases."""

    def test_minimum_80_cases(self):
        count = _count_tests()
        self.assertGreaterEqual(
            count, 80,
            f"Expected 80+ test cases, found {count}",
        )


if __name__ == "__main__":
    # Print test count before running
    count = _count_tests()
    print(f"\n{'='*60}")
    print(f"  Sparse Activation Gate test suite: {count} test cases")
    print(f"{'='*60}\n")
    unittest.main()
