#!/usr/bin/env python3
"""
test_boot_sequence.py — تسلسل الإقلاع الآمن (FN#045)
======================================================
Covers ``engine/aatif_boot_sequence.py`` — the safe boot sequence that
verifies each AATIF engine stage in order before the Governor is allowed
to serve requests, and ``AATIFGovernor.boot()`` — the factory classmethod
that uses the boot sequence.

Two layers of tests:

  1. Deterministic unit tests — run WITHOUT Ollama by injecting a FakeSEngine
     that reports ``backend_name="ollama:bge-m3"``. These exercise the stage
     ordering, fail-fast behavior on required stages, graceful handling of
     optional module failures, timing recording, and the Governor.boot()
     factory. Fast CI: no Ollama needed.

  2. The Governor.boot() integration test verifies that a booted Governor
     produces the same decision as a manually-constructed one (using the
     same injected FakeSEngine).

License: BSL 1.1
"""

import os
import sys
import types
from unittest.mock import patch

import pytest

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_THIS_DIR, "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

import aatif_boot_sequence  # noqa: E402 — must come after sys.path setup
from aatif_boot_sequence import (  # noqa: E402
    BootResult,
    StageResult,
    boot_aatif,
    REQUIRED_STAGES,
    STAGE_CORE_ENGINE,
    STAGE_DOMAIN_PROTOCOLS,
    STAGE_RESPONSE_SHAPER,
    STAGE_CONVERSATION_MEMORY,
    STAGE_TIME_SENSE,
    STAGE_OUTPUT_GATE,
    STAGE_OPTIONAL_MODULES,
    STAGE_SYSTEM_READY,
    OPT_FALSE_GOODNESS,
    OPT_META_OVERSIGHT,
    OPT_JUDGMENT_MEMORY,
    OPT_RESPONSE_SHAPER,
    OPT_FINGERPRINT,
    OPT_TEMPORAL_MEMORY,
    OPT_CONTEXTUAL_INTENT,
)
from aatif_governor import (  # noqa: E402
    AATIFGovernor,
    DegradedBackendError,
    DECISION_EXECUTE,
)


# ═══════════════════════════════════════════════════════════
#  Test doubles
# ═══════════════════════════════════════════════════════════

def _make_fake_engine(backend_name: str = "ollama:bge-m3",
                      decision: str = DECISION_EXECUTE):
    """Return a minimal stand-in for AATIFEngine.

    Satisfies _backend_is_calibrated() when backend_name starts with 'ollama'.
    FakeSEngine.compute() is deterministic so integration tests are stable.
    """
    engine = types.SimpleNamespace(
        h_scorer=types.SimpleNamespace(backend_name=backend_name),
    )

    def _compute(text, **kwargs):
        return {
            "text": text,
            "decision": decision,
            "S": 0.95,
            "H": 0.10,
            "I": 0.90,
            "E": 0.85,
            "F": 0.05,
            "confidence": "high",
            "profile": kwargs.get("profile"),
            "equation_mode": kwargs.get("equation_mode"),
            "domain": kwargs.get("domain"),
        }

    engine.compute = _compute
    return engine


# ═══════════════════════════════════════════════════════════
#  1. Successful full boot
# ═══════════════════════════════════════════════════════════

class TestBootSuccess:

    def test_returns_boot_result(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake)
        assert isinstance(result, BootResult)

    def test_ready_true_on_success(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake)
        assert result.success is True
        assert result.ready is True

    def test_no_failed_stage_on_success(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake)
        assert result.failed_stage is None

    def test_all_required_stages_pass(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake)
        for stage in REQUIRED_STAGES:
            assert stage in result.stage_results, f"Stage {stage} missing"
            sr = result.stage_results[stage]
            assert isinstance(sr, StageResult)
            assert sr.passed is True
            assert sr.error is None

    def test_optional_and_system_ready_stages_present(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake)
        assert STAGE_OPTIONAL_MODULES in result.stage_results
        assert STAGE_SYSTEM_READY in result.stage_results
        assert result.stage_results[STAGE_OPTIONAL_MODULES].passed is True
        assert result.stage_results[STAGE_SYSTEM_READY].passed is True

    def test_optional_modules_dict_has_all_keys(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake)
        expected_keys = {
            OPT_FALSE_GOODNESS, OPT_META_OVERSIGHT, OPT_JUDGMENT_MEMORY,
            OPT_RESPONSE_SHAPER, OPT_FINGERPRINT, OPT_TEMPORAL_MEMORY,
            OPT_CONTEXTUAL_INTENT,
        }
        assert expected_keys.issubset(result.optional_modules.keys())

    def test_optional_modules_values_are_booleans(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake)
        for name, available in result.optional_modules.items():
            assert isinstance(available, bool), f"{name} value is not bool"

    def test_domain_parameter_respected(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake, domain="healthcare")
        assert result.ready is True

    def test_unknown_domain_fails_at_domain_protocols(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake, domain="not_a_real_domain")
        assert result.success is False
        assert result.failed_stage == STAGE_DOMAIN_PROTOCOLS


# ═══════════════════════════════════════════════════════════
#  2. Boot failure at each required stage
# ═══════════════════════════════════════════════════════════

class TestBootFailurePerStage:

    def test_core_engine_fails_on_uncalibrated_backend(self):
        """An injected engine with backend_name='tfidf' must fail CORE_ENGINE."""
        bad_engine = _make_fake_engine(backend_name="tfidf")
        result = boot_aatif(backend=bad_engine)
        assert result.success is False
        assert result.ready is False
        assert result.failed_stage == STAGE_CORE_ENGINE
        sr = result.stage_results[STAGE_CORE_ENGINE]
        assert sr.passed is False
        assert sr.error is not None
        assert "tfidf" in sr.error or "calibrat" in sr.error.lower()

    def test_core_engine_fails_on_missing_h_scorer(self):
        """An engine with no h_scorer attribute fails CORE_ENGINE."""
        engine_no_h = types.SimpleNamespace()  # no h_scorer
        result = boot_aatif(backend=engine_no_h)
        assert result.failed_stage == STAGE_CORE_ENGINE

    def test_domain_protocols_fails_on_constructor_error(self):
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "DomainProtocol",
                          side_effect=RuntimeError("dp init failed")):
            result = boot_aatif(backend=fake)
        assert result.success is False
        assert result.failed_stage == STAGE_DOMAIN_PROTOCOLS
        assert result.stage_results[STAGE_DOMAIN_PROTOCOLS].passed is False
        assert "dp init failed" in result.stage_results[STAGE_DOMAIN_PROTOCOLS].error

    def test_response_shaper_fails_on_r_equation_error(self):
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "REquation",
                          side_effect=RuntimeError("req init failed")):
            result = boot_aatif(backend=fake)
        assert result.failed_stage == STAGE_RESPONSE_SHAPER

    def test_conversation_memory_fails_on_constructor_error(self):
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "AATIFConversationMemory",
                          side_effect=RuntimeError("memory init failed")):
            result = boot_aatif(backend=fake)
        assert result.failed_stage == STAGE_CONVERSATION_MEMORY

    def test_time_sense_fails_on_constructor_error(self):
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "TimeSense",
                          side_effect=RuntimeError("time_sense init failed")):
            result = boot_aatif(backend=fake)
        assert result.failed_stage == STAGE_TIME_SENSE

    def test_output_gate_fails_on_constructor_error(self):
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "AATIFOutputGate",
                          side_effect=RuntimeError("gate init failed")):
            result = boot_aatif(backend=fake)
        assert result.failed_stage == STAGE_OUTPUT_GATE

    def test_failure_halts_before_later_stages(self):
        """Failure at DOMAIN_PROTOCOLS means RESPONSE_SHAPER is never recorded."""
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "DomainProtocol",
                          side_effect=RuntimeError("dp fail")):
            result = boot_aatif(backend=fake)
        assert STAGE_DOMAIN_PROTOCOLS in result.stage_results
        # No stage after DOMAIN_PROTOCOLS should appear in results.
        assert STAGE_RESPONSE_SHAPER not in result.stage_results
        assert STAGE_CONVERSATION_MEMORY not in result.stage_results
        assert STAGE_SYSTEM_READY not in result.stage_results

    def test_stage_result_includes_error_message_on_failure(self):
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "AATIFOutputGate",
                          side_effect=RuntimeError("gate exploded")):
            result = boot_aatif(backend=fake)
        sr = result.stage_results[STAGE_OUTPUT_GATE]
        assert sr.error == "gate exploded"
        assert sr.passed is False


# ═══════════════════════════════════════════════════════════
#  3. Optional module gracefully absent
# ═══════════════════════════════════════════════════════════

class TestOptionalModuleAbsent:

    def test_false_goodness_absent_does_not_halt_boot(self):
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "HAS_FALSE_GOODNESS", False):
            result = boot_aatif(backend=fake)
        assert result.ready is True
        assert result.optional_modules[OPT_FALSE_GOODNESS] is False

    def test_meta_oversight_absent_does_not_halt_boot(self):
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "HAS_META_OVERSIGHT", False):
            result = boot_aatif(backend=fake)
        assert result.ready is True
        assert result.optional_modules[OPT_META_OVERSIGHT] is False

    def test_judgment_memory_absent_does_not_halt_boot(self):
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "HAS_JUDGMENT_MEMORY", False):
            result = boot_aatif(backend=fake)
        assert result.ready is True
        assert result.optional_modules[OPT_JUDGMENT_MEMORY] is False

    def test_all_optional_absent_still_boots(self):
        """All optional modules unavailable → boot succeeds, all marked False."""
        fake = _make_fake_engine()
        with (
            patch.object(aatif_boot_sequence, "HAS_FALSE_GOODNESS", False),
            patch.object(aatif_boot_sequence, "HAS_META_OVERSIGHT", False),
            patch.object(aatif_boot_sequence, "HAS_JUDGMENT_MEMORY", False),
            patch.object(aatif_boot_sequence, "HAS_RESPONSE_SHAPER_MODULE", False),
            patch.object(aatif_boot_sequence, "HAS_FINGERPRINT", False),
            patch.object(aatif_boot_sequence, "HAS_TEMPORAL_MEMORY", False),
            patch.object(aatif_boot_sequence, "HAS_CONTEXTUAL_INTENT", False),
        ):
            result = boot_aatif(backend=fake)
        assert result.ready is True
        for name in (OPT_FALSE_GOODNESS, OPT_META_OVERSIGHT, OPT_JUDGMENT_MEMORY,
                     OPT_RESPONSE_SHAPER, OPT_FINGERPRINT, OPT_TEMPORAL_MEMORY,
                     OPT_CONTEXTUAL_INTENT):
            assert result.optional_modules[name] is False, f"{name} should be False"


# ═══════════════════════════════════════════════════════════
#  4. Optional module present but broken — boot continues
# ═══════════════════════════════════════════════════════════

class TestOptionalModuleBroken:

    def _ensure_has_flag(self, flag_name: str) -> bool:
        """Return True only if the HAS_* flag is currently True in the module."""
        return getattr(aatif_boot_sequence, flag_name, False)

    def test_meta_oversight_broken_init_does_not_halt_boot(self):
        """MetaOversightEngine present (pure logic) but raises on __init__."""
        if not self._ensure_has_flag("HAS_META_OVERSIGHT"):
            pytest.skip("MetaOversightEngine not available in this environment")
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "MetaOversightEngine",
                          side_effect=RuntimeError("meta_oversight broken")):
            result = boot_aatif(backend=fake)
        assert result.ready is True
        assert result.optional_modules[OPT_META_OVERSIGHT] is False

    def test_response_shaper_broken_init_does_not_halt_boot(self):
        if not self._ensure_has_flag("HAS_RESPONSE_SHAPER_MODULE"):
            pytest.skip("AATIFResponseShaper not available in this environment")
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "AATIFResponseShaper",
                          side_effect=RuntimeError("shaper broken")):
            result = boot_aatif(backend=fake)
        assert result.ready is True
        assert result.optional_modules[OPT_RESPONSE_SHAPER] is False

    def test_fingerprint_broken_init_does_not_halt_boot(self):
        if not self._ensure_has_flag("HAS_FINGERPRINT"):
            pytest.skip("UserFingerprint not available in this environment")
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "UserFingerprint",
                          side_effect=RuntimeError("fingerprint broken")):
            result = boot_aatif(backend=fake)
        assert result.ready is True
        assert result.optional_modules[OPT_FINGERPRINT] is False

    def test_contextual_intent_broken_init_does_not_halt_boot(self):
        if not self._ensure_has_flag("HAS_CONTEXTUAL_INTENT"):
            pytest.skip("ContextualIntentScorer not available in this environment")
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "ContextualIntentScorer",
                          side_effect=RuntimeError("intent scorer broken")):
            result = boot_aatif(backend=fake)
        assert result.ready is True
        assert result.optional_modules[OPT_CONTEXTUAL_INTENT] is False

    def test_broken_optional_with_all_required_passes_marks_system_ready(self):
        if not self._ensure_has_flag("HAS_META_OVERSIGHT"):
            pytest.skip("MetaOversightEngine not available in this environment")
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "MetaOversightEngine",
                          side_effect=RuntimeError("broken")):
            result = boot_aatif(backend=fake)
        assert result.stage_results[STAGE_SYSTEM_READY].passed is True
        assert result.success is True


# ═══════════════════════════════════════════════════════════
#  5. Boot timing recorded
# ═══════════════════════════════════════════════════════════

class TestBootTiming:

    def test_boot_time_ms_is_non_negative(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake)
        assert isinstance(result.boot_time_ms, float)
        assert result.boot_time_ms >= 0.0

    def test_all_stage_results_have_non_negative_duration(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake)
        for stage_name, sr in result.stage_results.items():
            assert sr.duration_ms >= 0.0, (
                f"Stage {stage_name} has negative duration_ms"
            )

    def test_failed_boot_still_records_timing(self):
        bad = _make_fake_engine(backend_name="tfidf")
        result = boot_aatif(backend=bad)
        assert result.boot_time_ms >= 0.0
        sr = result.stage_results[STAGE_CORE_ENGINE]
        assert sr.duration_ms >= 0.0

    def test_stage_results_are_stage_result_instances(self):
        fake = _make_fake_engine()
        result = boot_aatif(backend=fake)
        for name, sr in result.stage_results.items():
            assert isinstance(sr, StageResult), f"{name} is not a StageResult"
            assert isinstance(sr.stage, str)
            assert isinstance(sr.passed, bool)
            assert isinstance(sr.duration_ms, float)


# ═══════════════════════════════════════════════════════════
#  6. Governor.boot() factory method
# ═══════════════════════════════════════════════════════════

class TestGovernorBootFactory:

    def test_returns_governor_and_boot_result(self):
        fake = _make_fake_engine()
        gov, result = AATIFGovernor.boot(backend=fake)
        assert isinstance(gov, AATIFGovernor)
        assert isinstance(result, BootResult)

    def test_boot_result_is_ready(self):
        fake = _make_fake_engine()
        _, result = AATIFGovernor.boot(backend=fake)
        assert result.ready is True

    def test_returned_governor_is_not_degraded(self):
        fake = _make_fake_engine()
        gov, _ = AATIFGovernor.boot(backend=fake)
        assert gov.is_degraded is False

    def test_raises_degraded_backend_error_on_failed_boot(self):
        bad = _make_fake_engine(backend_name="tfidf")
        with pytest.raises(DegradedBackendError) as exc_info:
            AATIFGovernor.boot(backend=bad)
        assert "CORE_ENGINE" in str(exc_info.value)

    def test_error_message_includes_failed_stage_name(self):
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "AATIFConversationMemory",
                          side_effect=RuntimeError("no mem")):
            with pytest.raises(DegradedBackendError) as exc_info:
                AATIFGovernor.boot(backend=fake)
        assert "CONVERSATION_MEMORY" in str(exc_info.value)

    def test_error_message_includes_original_error(self):
        fake = _make_fake_engine()
        with patch.object(aatif_boot_sequence, "AATIFOutputGate",
                          side_effect=RuntimeError("gate exploded")):
            with pytest.raises(DegradedBackendError) as exc_info:
                AATIFGovernor.boot(backend=fake)
        assert "gate exploded" in str(exc_info.value)

    def test_boot_passes_domain_to_sequence(self):
        """Domain 'healthcare' must be accepted during boot."""
        fake = _make_fake_engine()
        gov, result = AATIFGovernor.boot(backend=fake, domain="healthcare")
        assert result.ready is True
        assert isinstance(gov, AATIFGovernor)

    def test_boot_rejects_unknown_domain(self):
        fake = _make_fake_engine()
        with pytest.raises(DegradedBackendError):
            AATIFGovernor.boot(backend=fake, domain="not_a_domain")


# ═══════════════════════════════════════════════════════════
#  7. Integration — booted Governor matches manually-constructed one
# ═══════════════════════════════════════════════════════════

class TestGovernorBootIntegration:

    def _make_consistent_engine(self):
        """FakeSEngine shared between booted and manual Governor instances."""
        # Build ONE engine and share it — ensures both instances use the same
        # deterministic compute() so results are trivially equal.
        return _make_fake_engine(decision=DECISION_EXECUTE)

    def test_booted_governor_accepts_requests(self):
        fake = self._make_consistent_engine()
        gov, _ = AATIFGovernor.boot(backend=fake)
        result = gov.process("سؤال اختبار", domain="general")
        assert result is not None
        assert result.final_decision == DECISION_EXECUTE
        assert result.blocked is False

    def test_booted_governor_same_decision_as_manual(self):
        """boot() and manual construction with the same engine yield identical decisions."""
        fake = _make_fake_engine(decision=DECISION_EXECUTE)

        booted_gov, _ = AATIFGovernor.boot(backend=fake)
        manual_gov = AATIFGovernor(s_engine=fake, verify_backend=False)

        msg = "وش الأخبار؟"
        r_booted = booted_gov.process(msg, domain="general")
        r_manual = manual_gov.process(msg, domain="general")

        assert r_booted.final_decision == r_manual.final_decision
        assert r_booted.blocked == r_manual.blocked

    def test_booted_governor_populates_audit_trail(self):
        """Booted governor runs the full pipeline and fills the audit trail."""
        fake = _make_fake_engine(decision=DECISION_EXECUTE)
        gov, _ = AATIFGovernor.boot(backend=fake)
        result = gov.process("كيف حالك؟", domain="general", conversation_id="boot-test")

        assert result.s_result is not None
        assert result.p_result is not None
        assert result.r_result is not None
        assert result.governed_prompt

    def test_boot_result_audit_trail_covers_all_required_stages(self):
        """The BootResult from Governor.boot() records all eight stages."""
        fake = _make_fake_engine()
        _, result = AATIFGovernor.boot(backend=fake)

        all_stages = list(REQUIRED_STAGES) + [STAGE_OPTIONAL_MODULES, STAGE_SYSTEM_READY]
        for stage in all_stages:
            assert stage in result.stage_results, f"Stage {stage!r} missing from audit"

    def test_existing_governor_init_still_works_after_adding_boot(self):
        """Governor.__init__ must work exactly as before — no regression."""
        fake = _make_fake_engine()
        gov = AATIFGovernor(s_engine=fake, verify_backend=False)
        assert isinstance(gov, AATIFGovernor)
        assert not gov.is_degraded
        result = gov.process("اختبار", domain="general")
        assert result.final_decision == DECISION_EXECUTE
