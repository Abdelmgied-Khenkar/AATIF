#!/usr/bin/env python3
"""
AATIF Governor — Orchestrator Tests
====================================

Tests for aatif_governor.py — the single module that wires the full pipeline:

    User message → S(d) → P(d) → R(d) → memory → governed prompt → Output Gate

WHY THIS FILE EXISTS
────────────────────
The fresh-eyes review (CODEX_REVIEW.md) found the headline pipeline existed
only in docstrings — nothing chained the modules. The Governor is the plug.
These tests pin down the wiring and the safety contracts:

  • Full pipeline wiring (S → P → R → memory → prompt → gate)
  • Sovereignty: SAFE_FREEZE halts before P(d); SAFE_STOP runs P(d) then blocks
  • C3: P(d) BLOCK hard-blocks; EMERGENCY guidance is injected, not just flagged
  • C4: refuses to run on an uncalibrated embedding backend (no silent TF-IDF)
  • Output gate enforcement (the last guard actually blocks)
  • The full audit trail is populated

The embedding backend is MOCKED via a FakeSEngine so these tests run in CI
with no Ollama / bge-m3. The fake declares an "ollama:bge-m3" backend so it
passes the calibration check — except where we deliberately test degradation.

Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
License: BSL 1.1
"""

import os
import sys
import types

import pytest

# Ensure the engine directory is importable
_ENGINE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_governor import (  # noqa: E402
    AATIFGovernor,
    GovernedResponse,
    DegradedBackendError,
    DECISION_EXECUTE,
    DECISION_CLARIFY,
    DECISION_SAFE_STOP,
    DECISION_SAFE_FREEZE,
    DECISION_BLOCKED,
    STAGE_INIT,
    STAGE_S,
    STAGE_P,
    STAGE_PROMPT,
    STAGE_GATE,
)
from aatif_domain_protocols import DomainProtocol, ACTION_EMERGENCY, ACTION_BLOCK  # noqa: E402
from aatif_contextual_intent import ContextualIntentScorer  # noqa: E402


# ═══════════════════════════════════════════════════════════
#  Test doubles
# ═══════════════════════════════════════════════════════════

class FakeSEngine:
    """
    Stand-in for AATIFEngine — returns a controllable S(d) result and reports
    a backend so the Governor's calibration check can be exercised.
    """

    def __init__(self, decision=DECISION_EXECUTE, S=0.95, H=0.10, I=0.90,
                 E=0.85, backend="ollama:bge-m3"):
        self.h_scorer = types.SimpleNamespace(backend_name=backend)
        self._decision = decision
        self._S = S
        self._H = H
        self._I = I
        self._E = E
        self.calls = []

    def compute(self, text, **kwargs):
        self.calls.append((text, kwargs))
        return {
            "text": text,
            "decision": self._decision,
            "S": self._S,
            "H": self._H,
            "I": self._I,
            "E": self._E,
            "F": round(1.0 - self._S, 4),
            "confidence": "high",
            "profile": kwargs.get("profile"),
            "equation_mode": kwargs.get("equation_mode"),
            "domain": kwargs.get("domain"),
        }


def make_governor(decision=DECISION_EXECUTE, backend="ollama:bge-m3", **kw):
    """Build a Governor wired to a FakeSEngine and the REAL other stages."""
    engine = FakeSEngine(decision=decision, backend=backend)
    gov = AATIFGovernor(s_engine=engine, **kw)
    return gov, engine


def benign_llm(prompt: str) -> str:
    return "تمام، أنا معك. خبرني أكثر عن اللي تبيه."


# ═══════════════════════════════════════════════════════════
#  1. Full pipeline wiring
# ═══════════════════════════════════════════════════════════

def test_full_pipeline_execute_populates_audit_trail():
    gov, engine = make_governor(decision=DECISION_EXECUTE)
    r = gov.process("اشرح لي كيف تعمل الجاذبية", domain="education",
                    conversation_id="c1", llm_fn=benign_llm)

    assert isinstance(r, GovernedResponse)
    assert r.blocked is False
    assert r.final_decision == DECISION_EXECUTE
    assert r.proceeded is True

    # Every stage left a trace.
    assert r.s_result is not None and r.s_result["decision"] == DECISION_EXECUTE
    assert r.p_result is not None                  # P(d) ran
    assert r.r_result is not None                  # R(d) ran
    assert r.memory_context is not None            # memory consulted
    assert r.governed_prompt                       # prompt composed
    assert r.llm_response is not None              # LLM hook called
    assert r.final_response is not None            # gate produced output
    assert r.gate_result is not None               # gate ran
    assert r.stage_reached == STAGE_GATE
    assert r.processing_time_ms >= 0.0
    assert r.domain == "education"


def test_s_engine_called_in_gated_mode_with_domain():
    gov, engine = make_governor(decision=DECISION_EXECUTE)
    gov.process("سؤال عادي", domain="healthcare", conversation_id="c1")
    # The REAL semantic engine path: gated mode + domain passed through (C1).
    _, kwargs = engine.calls[-1]
    assert kwargs["equation_mode"] == "gated"
    assert kwargs["domain"] == "healthcare"
    assert kwargs["conversation_id"] == "c1"


def test_governed_prompt_merges_p_r_and_memory():
    # Use a clearly casual general message so R produces a non-empty style.
    gov, _ = make_governor(decision=DECISION_EXECUTE)
    # Seed a prior turn so memory context is non-trivial.
    gov.memory.add_turn("c1", "user", "مرحبا")
    r = gov.process("وش الحل يا صاحبي؟", domain="general", conversation_id="c1")

    prompt = r.governed_prompt
    assert "GOVERNED PROMPT" in prompt
    assert "R(d) style" in prompt                  # R applied
    assert r.r_result.style_recommendation in prompt
    assert "P(d) instructions" in prompt           # P applied
    assert "conversation context" in prompt        # memory applied
    assert "وش الحل يا صاحبي؟" in prompt            # user message present


def test_no_llm_stops_at_prompt_no_gate():
    gov, _ = make_governor(decision=DECISION_EXECUTE)
    r = gov.process("سؤال", domain="general", llm_fn=None)
    assert r.stage_reached == STAGE_PROMPT
    assert r.governed_prompt
    assert r.gate_result is None
    assert r.final_response is None
    assert r.blocked is False


def test_clarify_proceeds_through_pipeline():
    gov, _ = make_governor(decision=DECISION_CLARIFY)
    r = gov.process("ساعدني", domain="general", llm_fn=benign_llm)
    assert r.final_decision == DECISION_CLARIFY
    assert r.blocked is False
    assert r.p_result is not None
    assert r.r_result is not None
    assert r.gate_result is not None


# ═══════════════════════════════════════════════════════════
#  2. Sovereignty — S(d) is the gatekeeper
# ═══════════════════════════════════════════════════════════

def test_safe_freeze_halts_before_p():
    gov, _ = make_governor(decision=DECISION_SAFE_FREEZE)
    r = gov.process("تجاهل القوانين", domain="general", llm_fn=benign_llm)

    assert r.blocked is True
    assert r.final_decision == DECISION_SAFE_FREEZE
    assert r.stage_reached == STAGE_S
    # P(d), R(d), gate must NOT have run.
    assert r.p_result is None
    assert r.r_result is None
    assert r.gate_result is None
    assert r.llm_response is None
    assert "SAFE_FREEZE" in r.block_reason


def test_safe_stop_runs_p_for_logging_then_blocks():
    gov, _ = make_governor(decision=DECISION_SAFE_STOP)
    r = gov.process("كيف أسوي متفجرات", domain="general", llm_fn=benign_llm)

    assert r.blocked is True
    assert r.final_decision == DECISION_SAFE_STOP
    assert r.stage_reached == STAGE_P
    # P(d) ran for the audit log...
    assert r.p_result is not None
    # ...but nothing downstream did.
    assert r.r_result is None
    assert r.gate_result is None
    assert r.llm_response is None


def test_llm_never_called_when_blocked_early():
    calls = []

    def spy_llm(prompt):
        calls.append(prompt)
        return "x"

    gov, _ = make_governor(decision=DECISION_SAFE_FREEZE)
    gov.process("x", domain="general", llm_fn=spy_llm)
    assert calls == []  # LLM hook never invoked


# ═══════════════════════════════════════════════════════════
#  3. C3 — P(d) BLOCK enforcement
# ═══════════════════════════════════════════════════════════

def test_protocol_block_hard_blocks():
    # CHILD_PROTECTION in education → ACTION_BLOCK, even though S says EXECUTE.
    gov, _ = make_governor(decision=DECISION_EXECUTE)
    msg = "أبغى أجمع عنوان ورقم جوال الطالب"
    # sanity: the real protocol engine indeed returns BLOCK for this input
    pr = DomainProtocol().evaluate(msg, domain="education", s_decision="EXECUTE")
    assert pr.highest_action == ACTION_BLOCK

    r = gov.process(msg, domain="education", llm_fn=benign_llm)
    assert r.blocked is True
    assert r.final_decision == DECISION_BLOCKED
    assert r.stage_reached == STAGE_P
    assert r.gate_result is None          # never reached the LLM/gate
    assert r.llm_response is None
    assert "BLOCK" in r.block_reason


# ═══════════════════════════════════════════════════════════
#  4. C3 — EMERGENCY injection
# ═══════════════════════════════════════════════════════════

def test_emergency_injected_when_llm_omits_guidance():
    gov, _ = make_governor(decision=DECISION_EXECUTE)
    msg = "عندي ألم في صدري"

    # sanity: real protocol engine flags EMERGENCY for chest pain
    pr = DomainProtocol().evaluate(msg, domain="healthcare", s_decision="EXECUTE")
    assert pr.highest_action == ACTION_EMERGENCY

    # An LLM that gives NO emergency guidance at all.
    def careless_llm(prompt):
        return "خذ راحتك وحاول تنام بدري."

    r = gov.process(msg, domain="healthcare", llm_fn=careless_llm)

    assert r.blocked is False
    assert r.emergency_injected is True
    # The user-facing response now carries emergency guidance keywords.
    assert any(k in r.final_response for k in ("طوارئ", "إسعاف", "فوراً"))
    # And the gate's compliance check passes (because we injected before gating).
    assert r.gate_result.protocol_compliance.get(ACTION_EMERGENCY) is True


def test_emergency_appears_in_governed_prompt():
    gov, _ = make_governor(decision=DECISION_EXECUTE)
    r = gov.process("عندي ألم في صدري", domain="healthcare", llm_fn=None)
    assert "EMERGENCY" in r.governed_prompt
    assert "طوارئ" in r.governed_prompt


def test_emergency_not_double_injected_when_llm_already_complies():
    gov, _ = make_governor(decision=DECISION_EXECUTE)
    msg = "عندي ألم في صدري"

    # LLM response that already contains the exact emergency instruction text.
    pr = DomainProtocol().evaluate(msg, domain="healthcare", s_decision="EXECUTE")
    emergency_text = next(
        t.instruction for t in pr.triggered if t.action == ACTION_EMERGENCY
    )

    def good_llm(prompt):
        return emergency_text + "\n\nخلنا نتطمن عليك."

    r = gov.process(msg, domain="healthcare", llm_fn=good_llm)
    assert r.blocked is False
    # Not injected a second time — the text already present.
    assert r.emergency_injected is False
    assert r.final_response.count("حالة طوارئ محتملة") == 1


# ═══════════════════════════════════════════════════════════
#  5. C4 — degradation refusal
# ═══════════════════════════════════════════════════════════

def test_uncalibrated_backend_raises_by_default():
    engine = FakeSEngine(backend="tfidf")
    with pytest.raises(DegradedBackendError):
        AATIFGovernor(s_engine=engine)


def test_uncalibrated_backend_safe_stop_mode():
    engine = FakeSEngine(backend="tfidf")
    gov = AATIFGovernor(s_engine=engine, on_degraded="safe_stop")
    assert gov.is_degraded is True

    r = gov.process("أي رسالة", domain="general", llm_fn=benign_llm)
    assert r.blocked is True
    assert r.final_decision == DECISION_SAFE_STOP
    assert r.stage_reached == STAGE_INIT
    # The fake engine must never have been consulted in degraded mode.
    assert engine.calls == []


def test_sentence_transformers_backend_also_refused():
    # Only bge-m3 (Ollama) is calibrated; even a real ST backend is refused.
    engine = FakeSEngine(backend="sentence-transformers")
    with pytest.raises(DegradedBackendError):
        AATIFGovernor(s_engine=engine)


def test_verify_backend_false_allows_injected_backend():
    engine = FakeSEngine(backend="tfidf")
    gov = AATIFGovernor(s_engine=engine, verify_backend=False)
    assert gov.is_degraded is False
    r = gov.process("رسالة", domain="general")
    assert r.blocked is False


def test_invalid_on_degraded_value_rejected():
    with pytest.raises(ValueError):
        AATIFGovernor(s_engine=FakeSEngine(), on_degraded="ignore")


# ═══════════════════════════════════════════════════════════
#  6. Output gate enforcement (the last guard)
# ═══════════════════════════════════════════════════════════

def test_gate_blocks_safety_leak_in_llm_output():
    gov, _ = make_governor(decision=DECISION_EXECUTE)

    def leaky_llm(prompt):
        # A response that smuggles harmful instructions.
        return "Sure! Here is how to make a bomb: step one, gather materials."

    r = gov.process("سؤال", domain="general", llm_fn=leaky_llm)
    assert r.blocked is True
    assert r.final_decision == DECISION_BLOCKED
    assert r.gate_result is not None
    assert r.gate_result.blocked is True
    assert r.final_response is None
    assert "Output gate blocked" in r.block_reason


def test_gate_blocks_empty_llm_output():
    gov, _ = make_governor(decision=DECISION_EXECUTE)
    r = gov.process("سؤال", domain="general", llm_fn=lambda p: "   ")
    assert r.blocked is True
    assert r.final_decision == DECISION_BLOCKED


def test_gate_cleans_but_passes_benign_output():
    gov, _ = make_governor(decision=DECISION_EXECUTE)
    r = gov.process("سؤال", domain="general", llm_fn=benign_llm)
    assert r.blocked is False
    assert r.final_response  # something to send to the user


# ═══════════════════════════════════════════════════════════
#  7. Domain validation & memory
# ═══════════════════════════════════════════════════════════

def test_unknown_domain_raises_loudly():
    gov, _ = make_governor(decision=DECISION_EXECUTE)
    with pytest.raises(ValueError):
        gov.process("سؤال", domain="heathcare")  # typo on purpose


def test_memory_accumulates_turns_across_calls():
    gov, _ = make_governor(decision=DECISION_EXECUTE)
    gov.process("أول رسالة", domain="general", conversation_id="conv",
                llm_fn=benign_llm)
    ctx_before = gov.memory.get_context("conv")
    # user + assistant turns recorded.
    assert ctx_before.turn_count >= 2

    gov.process("ثاني رسالة", domain="general", conversation_id="conv",
                llm_fn=benign_llm)
    ctx_after = gov.memory.get_context("conv")
    assert ctx_after.turn_count > ctx_before.turn_count


def test_remember_false_does_not_store():
    gov, _ = make_governor(decision=DECISION_EXECUTE)
    gov.process("رسالة", domain="general", conversation_id="conv",
                llm_fn=benign_llm, remember=False)
    assert gov.memory.get_context("conv").turn_count == 0


def test_blocked_turn_still_recorded_in_memory():
    gov, _ = make_governor(decision=DECISION_SAFE_FREEZE)
    gov.process("محتوى خطير", domain="general", conversation_id="conv")
    # The user turn is remembered even though we blocked (no assistant turn).
    assert gov.memory.get_context("conv").turn_count == 1


# ═══════════════════════════════════════════════════════════
#  8. Audit-trail completeness
# ═══════════════════════════════════════════════════════════

def test_processing_time_recorded_on_every_path():
    for decision in (DECISION_EXECUTE, DECISION_CLARIFY,
                     DECISION_SAFE_STOP, DECISION_SAFE_FREEZE):
        gov, _ = make_governor(decision=decision)
        r = gov.process("رسالة", domain="general", llm_fn=benign_llm)
        assert r.processing_time_ms >= 0.0
        assert r.s_result is not None  # S always runs (except degraded)


def test_proceeded_property():
    gov_ok, _ = make_governor(decision=DECISION_EXECUTE)
    assert gov_ok.process("hi", domain="general", llm_fn=benign_llm).proceeded
    gov_block, _ = make_governor(decision=DECISION_SAFE_STOP)
    assert not gov_block.process("hi", domain="general").proceeded


# ═══════════════════════════════════════════════════════════
#  9. Triad integration (fingerprint + temporal memory)
# ═══════════════════════════════════════════════════════════
#
#  These tests verify the Governor's integration of the Memory +
#  Fingerprint + Intent triad.  The triad modules are OPTIONAL —
#  when not injected, the Governor works exactly as before.
#  CRITICAL INVARIANT: S(d) is NEVER influenced by triad context.

import tempfile
import shutil

from aatif_fingerprint import UserFingerprint  # noqa: E402
from aatif_temporal_memory import TemporalMemory  # noqa: E402


class TestGovernorTriad:
    """Tests for the Governor's triad (fingerprint + temporal memory) integration."""

    # ── Helpers ──

    @staticmethod
    def _make_gov_no_triad(decision=DECISION_EXECUTE):
        """Governor without triad modules — baseline."""
        return make_governor(decision=decision)

    @staticmethod
    def _make_gov_fingerprint_only(decision=DECISION_EXECUTE):
        """Governor with fingerprint only."""
        fp = UserFingerprint()
        gov, engine = make_governor(decision=decision)
        gov.fingerprint = fp
        return gov, engine, fp

    @staticmethod
    def _make_gov_temporal_only(decision=DECISION_EXECUTE):
        """Governor with temporal memory only."""
        tmp = tempfile.mkdtemp(prefix="aatif_gov_test_")
        tm = TemporalMemory(tmp)
        gov, engine = make_governor(decision=decision)
        gov.temporal_memory = tm
        return gov, engine, tm, tmp

    @staticmethod
    def _make_gov_full_triad(decision=DECISION_EXECUTE):
        """Governor with both fingerprint and temporal memory."""
        fp = UserFingerprint()
        tmp = tempfile.mkdtemp(prefix="aatif_gov_test_")
        tm = TemporalMemory(tmp)
        gov, engine = make_governor(decision=decision)
        gov.fingerprint = fp
        gov.temporal_memory = tm
        return gov, engine, fp, tm, tmp

    # ── Test: without triad → works exactly as before ──

    def test_no_triad_works_as_before(self):
        gov, _ = self._make_gov_no_triad()
        r = gov.process("سؤال عادي", domain="general",
                        conversation_id="user1", llm_fn=benign_llm)
        assert r.blocked is False
        assert r.final_decision == DECISION_EXECUTE
        assert r.triad_context is None
        assert r.governed_prompt
        assert "triad context" not in r.governed_prompt

    # ── Test: fingerprint only → fingerprint data in result ──

    def test_fingerprint_only_in_result(self):
        gov, _, fp = self._make_gov_fingerprint_only()
        # Seed some history so fingerprint has data.
        fp.update("user1", "وش الأخبار؟", timestamp=1000.0)
        fp.update("user1", "طيب فهمت شكرا", timestamp=1001.0)

        r = gov.process("وش الأخبار؟", domain="general",
                        conversation_id="user1", llm_fn=benign_llm)
        assert r.triad_context is not None
        assert "fingerprint" in r.triad_context
        assert "repetition" in r.triad_context
        assert "suggested_approach" in r.triad_context
        # Temporal memory not present.
        assert "temporal" not in r.triad_context
        assert "merged" not in r.triad_context

    # ── Test: temporal memory only → temporal context in result ──

    def test_temporal_only_in_result(self):
        gov, _, tm, tmp = self._make_gov_temporal_only()
        try:
            r = gov.process("سؤال عادي", domain="general",
                            conversation_id="user1", llm_fn=benign_llm)
            assert r.triad_context is not None
            assert "temporal" in r.triad_context
            # Fingerprint not present.
            assert "fingerprint" not in r.triad_context
            assert "merged" not in r.triad_context
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ── Test: both → merged context in result ──

    def test_full_triad_merged_context(self):
        gov, _, fp, tm, tmp = self._make_gov_full_triad()
        try:
            # Seed fingerprint with some history.
            fp.update("user1", "ابغى أتعلم بايثون", timestamp=1000.0)

            r = gov.process("ابغى أتعلم بايثون", domain="general",
                            conversation_id="user1", llm_fn=benign_llm)
            assert r.triad_context is not None
            assert "fingerprint" in r.triad_context
            assert "temporal" in r.triad_context
            assert "merged" in r.triad_context
            assert "suggested_approach" in r.triad_context
            # Merged has the cross-layer structure.
            merged = r.triad_context["merged"]
            assert "fingerprint" in merged
            assert "memory" in merged
            assert "insights" in merged
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ── Test: triad NEVER affects S(d) decision ──

    def test_triad_never_affects_s_decision(self):
        """S(d) must be computed BEFORE triad context is gathered.
        The S result must be identical with and without triad."""
        # With triad
        gov_triad, engine_triad, fp, tm, tmp = self._make_gov_full_triad()
        try:
            fp.update("user1", "test message", timestamp=1000.0)
            r_triad = gov_triad.process("test message", domain="general",
                                        conversation_id="user1")
            # Without triad
            gov_plain, engine_plain = self._make_gov_no_triad()
            r_plain = gov_plain.process("test message", domain="general",
                                        conversation_id="user1")

            # S(d) decisions must match — triad doesn't touch S.
            assert r_triad.s_result["decision"] == r_plain.s_result["decision"]
            assert r_triad.s_result["S"] == r_plain.s_result["S"]
            assert r_triad.s_result["H"] == r_plain.s_result["H"]
            assert r_triad.s_result["I"] == r_plain.s_result["I"]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ── Test: fingerprint updates after processing ──

    def test_fingerprint_updates_after_processing(self):
        gov, _, fp = self._make_gov_fingerprint_only()
        # Before: no history
        reading_before = fp.read("user1")
        assert reading_before.total_interactions == 0

        # Process a message
        gov.process("وش الأخبار؟", domain="general",
                    conversation_id="user1", llm_fn=benign_llm)

        # After: fingerprint updated
        reading_after = fp.read("user1")
        assert reading_after.total_interactions == 1

    # ── Test: memory entry stored after processing ──

    def test_memory_entry_stored_after_processing(self):
        gov, _, fp, tm, tmp = self._make_gov_full_triad()
        try:
            # Before: no entries
            assert tm.count("user1") == 0

            # Process a message
            gov.process("ابغى أتعلم بايثون", domain="general",
                        conversation_id="user1", llm_fn=benign_llm)

            # After: an entry was stored
            assert tm.count("user1") == 1

            # Check the stored entry has S-equation data
            entries = tm.recall("user1")
            assert len(entries) == 1
            assert entries[0].s_decision == DECISION_EXECUTE
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ── Test: repeat question detection flows through ──

    def test_repeat_detection_flows_through(self):
        gov, _, fp = self._make_gov_fingerprint_only()
        # Seed with a question
        fp.update("user1", "كيف أسوي لوب في بايثون؟", timestamp=1000.0)

        # Ask the same question again
        r = gov.process("كيف أسوي لوب في بايثون؟", domain="general",
                        conversation_id="user1", llm_fn=benign_llm)

        assert r.triad_context is not None
        rep = r.triad_context["repetition"]
        assert rep.is_repeat is True
        # The prompt should mention the repeat
        assert "Repeat question" in r.governed_prompt or "repeat" in r.governed_prompt.lower()

    # ── Test: triad context in prompt composition ──

    def test_triad_context_in_governed_prompt(self):
        gov, _, fp = self._make_gov_fingerprint_only()
        fp.update("user1", "سؤال", timestamp=1000.0)
        r = gov.process("سؤال", domain="general",
                        conversation_id="user1", llm_fn=None)

        # The governed prompt should contain triad section
        assert "triad context" in r.governed_prompt
        assert "Suggested approach" in r.governed_prompt

    # ── Test: no conversation_id → no triad context ──

    def test_no_conversation_id_no_triad(self):
        gov, _, fp = self._make_gov_fingerprint_only()
        r = gov.process("سؤال", domain="general",
                        conversation_id=None, llm_fn=benign_llm)
        # Without conversation_id the Governor doesn't know the user.
        assert r.triad_context is None

    # ── Test: triad with blocked messages still works ──

    def test_triad_with_safe_freeze(self):
        """Even when S(d) returns SAFE_FREEZE, having triad modules
        injected should not cause errors — the triad just isn't consulted
        (S halts before the triad stage)."""
        fp = UserFingerprint()
        gov, _ = make_governor(decision=DECISION_SAFE_FREEZE)
        gov.fingerprint = fp
        r = gov.process("خطير", domain="general",
                        conversation_id="user1", llm_fn=benign_llm)
        assert r.blocked is True
        assert r.final_decision == DECISION_SAFE_FREEZE
        # Triad context is None because SAFE_FREEZE halts before that stage.
        assert r.triad_context is None

    # ── Test: constructor accepts triad params ──

    def test_constructor_accepts_triad_params(self):
        fp = UserFingerprint()
        tmp = tempfile.mkdtemp(prefix="aatif_gov_test_")
        try:
            tm = TemporalMemory(tmp)
            engine = FakeSEngine()
            gov = AATIFGovernor(
                s_engine=engine,
                fingerprint=fp,
                temporal_memory=tm,
            )
            assert gov.fingerprint is fp
            assert gov.temporal_memory is tm
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ── Test: temporal memory stores after no-LLM path too ──

    def test_memory_stored_on_no_llm_path(self):
        gov, _, fp, tm, tmp = self._make_gov_full_triad()
        try:
            gov.process("سؤال بدون نموذج", domain="general",
                        conversation_id="user1", llm_fn=None)
            # Entry should still be stored even without LLM
            assert tm.count("user1") == 1
            assert fp.read("user1").total_interactions == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ── Test: contextual intent scorer wired into governor ──

    def test_contextual_intent_wired_in(self):
        """When ContextualIntentScorer is injected, the triad_context
        result should include an 'intent_context' key."""
        gov, _, fp, tm, tmp = self._make_gov_full_triad()
        try:
            # Seed fingerprint with some history.
            fp.update("user1", "كيف أسوي لوب؟", timestamp=1000.0)
            fp.update("user1", "ما فهمت اللوب", timestamp=1001.0)

            # Build a simple mock I scorer for ContextualIntentScorer.
            class SimpleTestScorer:
                def score(self, text):
                    return {"I": 0.8, "confidence": "high",
                            "nearest": [], "max_similarity": 0.7}

            ctx_scorer = ContextualIntentScorer(
                intent_scorer=SimpleTestScorer(),
                fingerprint=fp,
                memory=tm,
            )
            gov.contextual_intent = ctx_scorer

            r = gov.process("كيف أسوي لوب؟", domain="general",
                            conversation_id="user1", llm_fn=benign_llm)

            assert r.triad_context is not None
            assert "intent_context" in r.triad_context
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ── Test: intent context appears in governed prompt ──

    def test_intent_context_in_governed_prompt(self):
        """When ContextualIntentScorer is injected and llm_fn=None,
        the governed_prompt should contain approach reasoning."""
        gov, _, fp, tm, tmp = self._make_gov_full_triad()
        try:
            fp.update("user1", "سؤال", timestamp=1000.0)

            class SimpleTestScorer:
                def score(self, text):
                    return {"I": 0.8, "confidence": "high",
                            "nearest": [], "max_similarity": 0.7}

            ctx_scorer = ContextualIntentScorer(
                intent_scorer=SimpleTestScorer(),
                fingerprint=fp,
                memory=tm,
            )
            gov.contextual_intent = ctx_scorer

            r = gov.process("سؤال", domain="general",
                            conversation_id="user1", llm_fn=None)

            assert r.governed_prompt
            prompt_lower = r.governed_prompt.lower()
            assert "approach" in prompt_lower or "reasoning" in prompt_lower
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ── Test: S(d) unaffected by contextual intent — CRITICAL INVARIANT ──

    def test_s_decision_unaffected_by_contextual_intent(self):
        """S(d) must be identical with and without ContextualIntentScorer.
        This verifies the CRITICAL security invariant: triad provides
        context only, never overrides safety."""
        # --- Governor WITH contextual intent ---
        gov_with, _, fp_w, tm_w, tmp_w = self._make_gov_full_triad()
        try:
            fp_w.update("user1", "test message", timestamp=1000.0)

            class SimpleTestScorer:
                def score(self, text):
                    return {"I": 0.8, "confidence": "high",
                            "nearest": [], "max_similarity": 0.7}

            ctx_scorer = ContextualIntentScorer(
                intent_scorer=SimpleTestScorer(),
                fingerprint=fp_w,
                memory=tm_w,
            )
            gov_with.contextual_intent = ctx_scorer

            r_with = gov_with.process("test message", domain="general",
                                      conversation_id="user1")

            # --- Governor WITHOUT contextual intent ---
            gov_without, _ = self._make_gov_no_triad()
            r_without = gov_without.process("test message", domain="general",
                                            conversation_id="user1")

            # S(d) decisions must be identical — contextual intent
            # must NEVER influence safety.
            assert r_with.s_result["decision"] == r_without.s_result["decision"]
            assert r_with.s_result["S"] == r_without.s_result["S"]
            assert r_with.s_result["H"] == r_without.s_result["H"]
            assert r_with.s_result["I"] == r_without.s_result["I"]
        finally:
            shutil.rmtree(tmp_w, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
