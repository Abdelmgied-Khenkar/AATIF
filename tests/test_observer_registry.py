#!/usr/bin/env python3
"""
Tests for aatif_observer_registry — سجل المراقبين

Tests the B-prime observer architecture:
  - Registry registration and phase execution
  - ObserverResult structure
  - Graceful degradation (failing observers don't break the pipeline)
  - B-prime invariant (CAN_BLOCK_RUNTIME always False)
  - auto_register() picks up available modules
  - build_registry() convenience function
  - Observer enrichments reach the GovernedResponse
"""

import os
import sys
import time

import pytest

# ── Importability ──
_ENGINE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_observer_registry import (
    Observer,
    ObserverContext,
    ObserverPhase,
    ObserverRegistry,
    ObserverResult,
    build_registry,
)


# ═══════════════════════════════════════════════════════════
#  Fixtures — minimal stubs that behave like real observers
# ═══════════════════════════════════════════════════════════

class StubPostSObserver(Observer):
    """A minimal POST_S observer that always activates."""
    name = "stub_post_s"
    phase = ObserverPhase.POST_S
    CAN_BLOCK_RUNTIME = False

    def observe(self, ctx: ObserverContext) -> ObserverResult:
        return ObserverResult(
            module_name=self.name,
            phase=self.phase,
            activated=True,
            flags=["stub_flag"],
            prompt_enrichment="stub enrichment text",
        )


class StubPostOutputObserver(Observer):
    """A minimal POST_OUTPUT observer."""
    name = "stub_post_output"
    phase = ObserverPhase.POST_OUTPUT
    CAN_BLOCK_RUNTIME = False

    def observe(self, ctx: ObserverContext) -> ObserverResult:
        return ObserverResult(
            module_name=self.name,
            phase=self.phase,
            activated=ctx.llm_output is not None,
            flags=["output_checked"] if ctx.llm_output else [],
        )


class StubBootObserver(Observer):
    """A minimal BOOT observer."""
    name = "stub_boot"
    phase = ObserverPhase.BOOT
    CAN_BLOCK_RUNTIME = False

    def observe(self, ctx: ObserverContext) -> ObserverResult:
        return ObserverResult(
            module_name=self.name,
            phase=self.phase,
            activated=True,
            flags=["booted"],
        )


class ExplodingObserver(Observer):
    """An observer that always raises — tests graceful degradation."""
    name = "exploding"
    phase = ObserverPhase.POST_S
    CAN_BLOCK_RUNTIME = False

    def observe(self, ctx: ObserverContext) -> ObserverResult:
        raise RuntimeError("deliberate test explosion")


class ContextReadingObserver(Observer):
    """Reads all context fields to verify they are populated."""
    name = "context_reader"
    phase = ObserverPhase.POST_S
    CAN_BLOCK_RUNTIME = False

    def observe(self, ctx: ObserverContext) -> ObserverResult:
        flags = []
        if ctx.message:
            flags.append(f"message={ctx.message}")
        if ctx.s_result:
            flags.append(f"s_decision={ctx.s_result.get('decision')}")
        if ctx.domain != "general":
            flags.append(f"domain={ctx.domain}")
        if ctx.conversation_id:
            flags.append(f"conv={ctx.conversation_id}")
        return ObserverResult(
            module_name=self.name,
            phase=self.phase,
            activated=True,
            flags=flags,
        )


# ═══════════════════════════════════════════════════════════
#  Tests — ObserverPhase
# ═══════════════════════════════════════════════════════════

class TestObserverPhase:
    def test_three_phases_exist(self):
        assert ObserverPhase.POST_S.value == "post_s"
        assert ObserverPhase.POST_OUTPUT.value == "post_output"
        assert ObserverPhase.BOOT.value == "boot"

    def test_phases_are_distinct(self):
        phases = [p for p in ObserverPhase]
        assert len(phases) == len(set(phases)) == 3


# ═══════════════════════════════════════════════════════════
#  Tests — ObserverResult
# ═══════════════════════════════════════════════════════════

class TestObserverResult:
    def test_default_values(self):
        r = ObserverResult(module_name="test", phase=ObserverPhase.POST_S)
        assert r.module_name == "test"
        assert r.phase == ObserverPhase.POST_S
        assert r.reading is None
        assert r.activated is False
        assert r.flags == []
        assert r.prompt_enrichment == ""
        assert r.error == ""
        assert r.elapsed_ms == 0.0

    def test_flags_are_independent(self):
        """Each ObserverResult gets its own flags list — no shared state."""
        r1 = ObserverResult(module_name="a", phase=ObserverPhase.POST_S)
        r2 = ObserverResult(module_name="b", phase=ObserverPhase.POST_S)
        r1.flags.append("x")
        assert r2.flags == []


# ═══════════════════════════════════════════════════════════
#  Tests — ObserverContext
# ═══════════════════════════════════════════════════════════

class TestObserverContext:
    def test_default_context(self):
        ctx = ObserverContext()
        assert ctx.message == ""
        assert ctx.s_result is None
        assert ctx.domain == "general"
        assert ctx.conversation_id is None
        assert ctx.llm_output is None
        assert ctx.turn_index == 0

    def test_context_populated(self):
        ctx = ObserverContext(
            message="test msg",
            s_result={"decision": "EXECUTE", "S": 0.1},
            domain="healthcare",
            conversation_id="conv-123",
            llm_output="some llm response",
            turn_index=5,
        )
        assert ctx.message == "test msg"
        assert ctx.s_result["decision"] == "EXECUTE"
        assert ctx.domain == "healthcare"
        assert ctx.conversation_id == "conv-123"
        assert ctx.llm_output == "some llm response"
        assert ctx.turn_index == 5


# ═══════════════════════════════════════════════════════════
#  Tests — Observer ABC
# ═══════════════════════════════════════════════════════════

class TestObserverABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Observer()

    def test_subclass_must_implement_observe(self):
        class Incomplete(Observer):
            name = "incomplete"
        with pytest.raises(TypeError):
            Incomplete()

    def test_complete_subclass_works(self):
        obs = StubPostSObserver()
        assert obs.name == "stub_post_s"
        assert obs.phase == ObserverPhase.POST_S
        assert obs.CAN_BLOCK_RUNTIME is False


# ═══════════════════════════════════════════════════════════
#  Tests — ObserverRegistry
# ═══════════════════════════════════════════════════════════

class TestRegistryBasics:
    def test_empty_registry(self):
        reg = ObserverRegistry()
        assert reg.get_observers() == []
        assert reg.get_observers(ObserverPhase.POST_S) == []

    def test_register_and_retrieve(self):
        reg = ObserverRegistry()
        obs = StubPostSObserver()
        reg.register(obs)
        assert reg.get_observers(ObserverPhase.POST_S) == [obs]
        assert reg.get_observers(ObserverPhase.POST_OUTPUT) == []

    def test_multiple_phases(self):
        reg = ObserverRegistry()
        reg.register(StubPostSObserver())
        reg.register(StubPostOutputObserver())
        reg.register(StubBootObserver())
        assert len(reg.get_observers(ObserverPhase.POST_S)) == 1
        assert len(reg.get_observers(ObserverPhase.POST_OUTPUT)) == 1
        assert len(reg.get_observers(ObserverPhase.BOOT)) == 1
        assert len(reg.get_observers()) == 3

    def test_bprime_violation_rejected(self):
        """A CAN_BLOCK_RUNTIME=True observer is rejected at registration."""
        class BadObserver(Observer):
            name = "bad"
            phase = ObserverPhase.POST_S
            CAN_BLOCK_RUNTIME = True

            def observe(self, ctx):
                return ObserverResult(module_name=self.name, phase=self.phase)

        reg = ObserverRegistry()
        with pytest.raises(AssertionError, match="B-prime violation"):
            reg.register(BadObserver())


class TestRegistryExecution:
    def test_run_phase_returns_results(self):
        reg = ObserverRegistry()
        reg.register(StubPostSObserver())
        ctx = ObserverContext(message="test")
        results = reg.run_phase(ObserverPhase.POST_S, ctx)
        assert len(results) == 1
        assert results[0].module_name == "stub_post_s"
        assert results[0].activated is True
        assert results[0].flags == ["stub_flag"]
        assert results[0].prompt_enrichment == "stub enrichment text"

    def test_run_empty_phase_returns_empty(self):
        reg = ObserverRegistry()
        reg.register(StubPostSObserver())
        ctx = ObserverContext()
        results = reg.run_phase(ObserverPhase.POST_OUTPUT, ctx)
        assert results == []

    def test_elapsed_ms_populated(self):
        reg = ObserverRegistry()
        reg.register(StubPostSObserver())
        ctx = ObserverContext(message="test")
        results = reg.run_phase(ObserverPhase.POST_S, ctx)
        assert results[0].elapsed_ms >= 0.0

    def test_context_flows_to_observers(self):
        reg = ObserverRegistry()
        reg.register(ContextReadingObserver())
        ctx = ObserverContext(
            message="hello world",
            s_result={"decision": "EXECUTE"},
            domain="healthcare",
            conversation_id="conv-42",
        )
        results = reg.run_phase(ObserverPhase.POST_S, ctx)
        assert len(results) == 1
        flags = results[0].flags
        assert "message=hello world" in flags
        assert "s_decision=EXECUTE" in flags
        assert "domain=healthcare" in flags
        assert "conv=conv-42" in flags

    def test_post_output_receives_llm_output(self):
        reg = ObserverRegistry()
        reg.register(StubPostOutputObserver())
        ctx_with = ObserverContext(llm_output="hello from LLM")
        results = reg.run_phase(ObserverPhase.POST_OUTPUT, ctx_with)
        assert results[0].activated is True
        assert "output_checked" in results[0].flags

        ctx_without = ObserverContext(llm_output=None)
        results2 = reg.run_phase(ObserverPhase.POST_OUTPUT, ctx_without)
        assert results2[0].activated is False


class TestGracefulDegradation:
    def test_exploding_observer_does_not_crash_registry(self):
        reg = ObserverRegistry()
        reg.register(ExplodingObserver())
        ctx = ObserverContext(message="trigger explosion")
        results = reg.run_phase(ObserverPhase.POST_S, ctx)
        assert len(results) == 1
        r = results[0]
        assert r.module_name == "exploding"
        assert r.activated is False
        assert "RuntimeError" in r.error
        assert "deliberate test explosion" in r.error
        assert r.elapsed_ms >= 0.0

    def test_good_observer_still_runs_after_bad_one(self):
        """An exploding observer does not prevent subsequent observers from running."""
        reg = ObserverRegistry()
        reg.register(ExplodingObserver())
        reg.register(StubPostSObserver())
        ctx = ObserverContext(message="test")
        results = reg.run_phase(ObserverPhase.POST_S, ctx)
        assert len(results) == 2
        assert results[0].error != ""       # exploding
        assert results[1].activated is True  # stub still ran

    def test_multiple_explosions_all_caught(self):
        reg = ObserverRegistry()
        for _ in range(3):
            reg.register(ExplodingObserver())
        reg.register(StubPostSObserver())
        ctx = ObserverContext(message="test")
        results = reg.run_phase(ObserverPhase.POST_S, ctx)
        assert len(results) == 4
        errors = [r for r in results if r.error]
        successes = [r for r in results if r.activated]
        assert len(errors) == 3
        assert len(successes) == 1


class TestBootPhase:
    def test_run_boot_caches_results(self):
        reg = ObserverRegistry()
        reg.register(StubBootObserver())
        ctx = ObserverContext(domain="general")
        results = reg.run_boot(ctx)
        assert len(results) == 1
        assert results[0].flags == ["booted"]
        # cached
        assert reg.boot_results == results

    def test_boot_results_empty_before_run(self):
        reg = ObserverRegistry()
        assert reg.boot_results == []


# ═══════════════════════════════════════════════════════════
#  Tests — auto_register() and build_registry()
# ═══════════════════════════════════════════════════════════

class TestAutoRegister:
    def test_auto_register_returns_list_of_names(self):
        """auto_register() should return a list of strings (names of
        successfully registered observers). The exact list depends on which
        FN modules are importable in this environment."""
        reg = ObserverRegistry()
        names = reg.auto_register()
        assert isinstance(names, list)
        for name in names:
            assert isinstance(name, str)
            assert len(name) > 0

    def test_auto_register_all_bprime(self):
        """Every auto-registered observer must have CAN_BLOCK_RUNTIME=False."""
        reg = ObserverRegistry()
        reg.auto_register()
        for obs in reg.get_observers():
            assert obs.CAN_BLOCK_RUNTIME is False, (
                f"{obs.name} violates B-prime"
            )

    def test_auto_register_idempotent_names(self):
        """Calling auto_register twice should double-register (by design
        the registry allows multiple of the same), but the returned names
        should be consistent."""
        reg1 = ObserverRegistry()
        names1 = reg1.auto_register()
        reg2 = ObserverRegistry()
        names2 = reg2.auto_register()
        assert names1 == names2

    def test_build_registry_convenience(self):
        """build_registry() returns a populated registry."""
        reg = build_registry()
        assert isinstance(reg, ObserverRegistry)
        # It should have at least as many observers as auto_register finds
        all_obs = reg.get_observers()
        assert isinstance(all_obs, list)


# ═══════════════════════════════════════════════════════════
#  Tests — Governor integration contract
# ═══════════════════════════════════════════════════════════

class TestGovernorContract:
    """Tests the contract between the registry and AATIFGovernor.
    Uses a FakeSEngine so no live Ollama is needed."""

    @pytest.fixture
    def governor(self):
        """Build a Governor with FakeSEngine + observer registry."""
        import types
        try:
            from aatif_governor import AATIFGovernor
        except ImportError:
            pytest.skip("Cannot import AATIFGovernor")

        class FakeSEngine:
            def __init__(self):
                self.h_scorer = types.SimpleNamespace(backend_name="ollama:bge-m3")
                self.calls = []

            def compute(self, text, **kwargs):
                self.calls.append((text, kwargs))
                return {
                    "text": text, "decision": "EXECUTE",
                    "S": 0.95, "H": 0.10, "I": 0.90, "E": 0.85,
                    "F": 0.05, "confidence": "high",
                    "profile": kwargs.get("profile"),
                    "equation_mode": kwargs.get("equation_mode"),
                    "domain": kwargs.get("domain"),
                }
        fake = FakeSEngine()
        gov = AATIFGovernor(
            s_engine=fake, on_degraded="raise", verify_backend=False
        )
        return gov

    def test_governor_has_observer_registry(self, governor):
        """The Governor should auto-construct an observer registry."""
        assert hasattr(governor, "observer_registry")
        # It may be None if the import failed in this env, but the attr exists

    def test_governed_response_has_observer_results(self, governor):
        """GovernedResponse should have an observer_results field."""
        result = governor.process(
            "مرحبا", domain="general", conversation_id="test-obs"
        )
        assert hasattr(result, "observer_results")
        assert isinstance(result.observer_results, list)

    def test_observer_results_are_observer_result_instances(self, governor):
        """Each item in observer_results should be an ObserverResult."""
        if governor.observer_registry is None:
            pytest.skip("No observer registry available")
        result = governor.process(
            "كيف حالك", domain="general", conversation_id="test-obs-2"
        )
        for obs_r in result.observer_results:
            assert isinstance(obs_r, ObserverResult), (
                f"Expected ObserverResult, got {type(obs_r)}"
            )
            assert obs_r.CAN_BLOCK_RUNTIME is False if hasattr(obs_r, 'CAN_BLOCK_RUNTIME') else True

    def test_observers_never_block(self, governor):
        """No observer should cause the Governor to block when S says EXECUTE."""
        result = governor.process(
            "عطني فكرة هدية", domain="general", conversation_id="test-obs-3"
        )
        # A benign message with FakeSEngine should not be blocked
        # (FakeSEngine defaults to EXECUTE)
        assert result.final_decision == "EXECUTE"
        assert result.blocked is False


# ═══════════════════════════════════════════════════════════
#  Tests — Runtime audit trail
# ═══════════════════════════════════════════════════════════

class TestAuditTrailIntegration:
    def test_audit_dict_has_observers_key(self):
        """The runtime's _audit_dict should include an 'observers' key."""
        try:
            from aatif_runtime import _audit_dict
            from aatif_governor import GovernedResponse
        except ImportError:
            pytest.skip("Cannot import runtime modules")

        # Build a minimal GovernedResponse with observer_results
        resp = GovernedResponse(
            final_response="test",
            final_decision="EXECUTE",
            blocked=False,
            observer_results=[
                ObserverResult(
                    module_name="test_obs",
                    phase=ObserverPhase.POST_S,
                    activated=True,
                    flags=["flag1"],
                    elapsed_ms=1.23,
                ),
            ],
        )
        audit = _audit_dict("input", "general", "test-model", resp)
        assert "observers" in audit
        assert len(audit["observers"]) == 1
        obs = audit["observers"][0]
        assert obs["module"] == "test_obs"
        assert obs["phase"] == "post_s"
        assert obs["activated"] is True
        assert obs["flags"] == ["flag1"]
        assert obs["elapsed_ms"] == 1.23
