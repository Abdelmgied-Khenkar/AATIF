#!/usr/bin/env python3
"""
AATIF Runtime — Tests
=====================

Tests for engine/aatif_runtime.py — الباب الأمامي (the front door).

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic) — Agent حسّاب

WHY THIS FILE EXISTS
────────────────────
`aatif_runtime.py` is the ignition: it wires a production `llm_fn`, boots one
Governor per process, flattens a `GovernedResponse` into a JSON-ready audit
trail (`_audit_dict`), and exposes a CLI + optional FastAPI front door. Before
this file it had NO dedicated test — only a single tangential import of
`_audit_dict` from `test_observer_registry.py`. That is a real coverage gap for
the one module every external caller passes through.

THE TESTING STRATEGY
────────────────────
The runtime is glue, and glue is exactly where silent breakage hides. None of
these tests touch a real model, a real socket, or boot a real Governor:

  1. `_audit_dict` — pure transform. Fed hand-built `GovernedResponse` objects
     (minimal, blocked, rich P/R/gate, observer flattening incl. enum-vs-str
     phase) and asserted key-by-key. Must stay JSON-serialisable.
  2. `make_ollama_llm_fn` — `requests.post` is monkeypatched, so we assert the
     payload it sends, that it strips whitespace, tolerates a missing
     "response" key, and calls `raise_for_status`.
  3. `govern` — `get_governor` and `make_ollama_llm_fn` are monkeypatched, so we
     assert it threads the llm_fn through and returns `_audit_dict`'s output.
  4. `get_governor` — `AATIFGovernor.boot` is monkeypatched to count calls,
     proving the "one Governor per process (cached)" contract.
  5. `_run_cli` — `govern`/`_serve` are monkeypatched; arg parsing, stdin
     piping, --json, and the empty-text error path are covered.
  6. `_print_human` — capsys, both blocked and proceed branches.
  7. FastAPI degradation — with fastapi/pydantic absent, `app` and
     `GovernRequest` degrade to None gracefully; when present, the request model
     carries its defaults. Both environments pass.

Every test is deterministic and CI-friendly. The runtime must never call an LLM
just to be imported or audited.
"""

import importlib
import json
import os
import sys

import pytest

# Ensure engine/ is importable (mirrors the other test modules + root conftest).
_ENGINE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

runtime = pytest.importorskip("aatif_runtime")
from aatif_governor import GovernedResponse  # noqa: E402
from aatif_observer_registry import ObserverPhase, ObserverResult  # noqa: E402


# ═══════════════════════════════════════════════════════════
#  Small helpers — hand-built stage results (no real Governor)
# ═══════════════════════════════════════════════════════════

class _NS:
    """Tiny attribute bag — stands in for ProtocolResult / RReading / GateReading
    without importing their real (heavier) constructors."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


def _s_result():
    """A representative S(d) dict, matching AATIFEngine.compute's shape."""
    return {
        "S": 0.12,
        "H": 0.31,
        "I": 0.44,
        "E": 0.10,
        "theta_effective": 0.40,
        "decision": "EXECUTE",
        "decision_reason": "below threshold",
    }


# ═══════════════════════════════════════════════════════════
#  1. _audit_dict — the pure transform (the heart of the module)
# ═══════════════════════════════════════════════════════════

class TestAuditDictMinimal:
    def test_minimal_proceed_response(self):
        """A bare proceed response should still produce every documented key."""
        r = GovernedResponse(
            final_decision="EXECUTE",
            blocked=False,
            final_response="hello",
            stage_reached="gate",
            processing_time_ms=12.5,
        )
        a = runtime._audit_dict("hi", "general", "aatif:latest", r)

        assert a["input"] == "hi"
        assert a["domain"] == "general"
        assert a["model"] == "aatif:latest"
        assert a["response"] == "hello"
        assert a["decision"] == "EXECUTE"
        assert a["blocked"] is False
        assert a["block_reason"] is None  # "" falls back to None
        assert a["stage_reached"] == "gate"
        assert a["processing_time_ms"] == 12.5
        assert a["observers"] == []

    def test_all_documented_keys_present(self):
        """Guards the audit contract: reviewers rely on these keys existing."""
        r = GovernedResponse(final_decision="EXECUTE", blocked=False)
        a = runtime._audit_dict("x", "general", "m", r)
        expected = {
            "input", "domain", "model", "response", "governed_prompt",
            "decision", "blocked", "block_reason", "stage_reached",
            "processing_time_ms", "S", "H", "I", "E", "theta_effective",
            "s_decision", "s_reason", "protocol_action", "protocols_triggered",
            "emergency_injected", "style", "gate_blocked", "gate_flags",
            "observers",
        }
        assert expected.issubset(set(a.keys()))

    def test_none_s_result_yields_none_numbers(self):
        """No S(d) computed → the S/H/I/E fields must be None, not crash."""
        r = GovernedResponse(final_decision="SAFE_STOP", blocked=True,
                             s_result=None)
        a = runtime._audit_dict("x", "general", "m", r)
        for k in ("S", "H", "I", "E", "theta_effective",
                  "s_decision", "s_reason"):
            assert a[k] is None

    def test_output_is_json_serialisable(self):
        """The whole point is a JSON-ready dict — it must actually serialise."""
        r = GovernedResponse(
            final_decision="EXECUTE", blocked=False,
            final_response="ok", s_result=_s_result(),
            observer_results=[
                ObserverResult(module_name="m", phase=ObserverPhase.POST_S,
                               activated=True, flags=["f"], elapsed_ms=0.5),
            ],
        )
        a = runtime._audit_dict("x", "general", "mdl", r)
        # Should not raise:
        dumped = json.dumps(a, ensure_ascii=False)
        assert "observers" in dumped


class TestAuditDictBlocked:
    def test_blocked_surfaces_reason(self):
        r = GovernedResponse(
            final_decision="SAFE_FREEZE",
            blocked=True,
            block_reason="H over hard override",
            stage_reached="s_equation",
        )
        a = runtime._audit_dict("bad", "general", "m", r)
        assert a["blocked"] is True
        assert a["decision"] == "SAFE_FREEZE"
        assert a["block_reason"] == "H over hard override"

    def test_empty_block_reason_becomes_none(self):
        """`block_reason or None` — an empty string must not leak through."""
        r = GovernedResponse(final_decision="EXECUTE", blocked=False,
                             block_reason="")
        a = runtime._audit_dict("x", "general", "m", r)
        assert a["block_reason"] is None


class TestAuditDictStageResults:
    def test_s_result_fields_are_flattened(self):
        r = GovernedResponse(final_decision="EXECUTE", blocked=False,
                             s_result=_s_result())
        a = runtime._audit_dict("x", "general", "m", r)
        assert a["S"] == 0.12
        assert a["H"] == 0.31
        assert a["I"] == 0.44
        assert a["E"] == 0.10
        assert a["theta_effective"] == 0.40
        assert a["s_decision"] == "EXECUTE"
        assert a["s_reason"] == "below threshold"

    def test_protocol_and_style_and_gate(self):
        p = _NS(highest_action="EMERGENCY",
                triggered=[_NS(name="self_harm"), _NS(name="crisis")])
        r_style = _NS(style_recommendation="gentle")
        gate = _NS(blocked=True, flags=["identity_leak", "too_long"])
        r = GovernedResponse(
            final_decision="EXECUTE", blocked=False,
            p_result=p, r_result=r_style, gate_result=gate,
            emergency_injected=True,
        )
        a = runtime._audit_dict("x", "healthcare", "m", r)
        assert a["protocol_action"] == "EMERGENCY"
        assert a["protocols_triggered"] == ["self_harm", "crisis"]
        assert a["emergency_injected"] is True
        assert a["style"] == "gentle"
        assert a["gate_blocked"] is True
        assert a["gate_flags"] == ["identity_leak", "too_long"]

    def test_missing_stage_objects_degrade_to_defaults(self):
        """p/r/gate all None — getattr fallbacks must produce safe defaults."""
        r = GovernedResponse(final_decision="EXECUTE", blocked=False,
                             p_result=None, r_result=None, gate_result=None)
        a = runtime._audit_dict("x", "general", "m", r)
        assert a["protocol_action"] is None
        assert a["protocols_triggered"] == []
        assert a["style"] is None
        assert a["gate_blocked"] is None
        assert a["gate_flags"] == []

    def test_gate_flags_none_becomes_empty_list(self):
        """A gate that reports flags=None must flatten to [] (list(... or []))."""
        gate = _NS(blocked=False, flags=None)
        r = GovernedResponse(final_decision="EXECUTE", blocked=False,
                             gate_result=gate)
        a = runtime._audit_dict("x", "general", "m", r)
        assert a["gate_flags"] == []


class TestAuditDictObservers:
    def test_observer_with_enum_phase(self):
        """Real ObserverResult carries an ObserverPhase enum → use .value."""
        r = GovernedResponse(
            final_decision="EXECUTE", blocked=False,
            observer_results=[
                ObserverResult(module_name="drift", phase=ObserverPhase.POST_S,
                               activated=True, flags=["a", "b"],
                               elapsed_ms=2.0, error=""),
            ],
        )
        a = runtime._audit_dict("x", "general", "m", r)
        assert len(a["observers"]) == 1
        obs = a["observers"][0]
        assert obs["module"] == "drift"
        assert obs["phase"] == "post_s"   # enum resolved to its .value
        assert obs["activated"] is True
        assert obs["flags"] == ["a", "b"]
        assert obs["elapsed_ms"] == 2.0
        assert obs["error"] is None       # "" → None

    def test_observer_with_plain_string_phase(self):
        """A phase that is already a plain string must hit the str() branch."""
        obs_in = _NS(module_name="lite", phase="post_output",
                     activated=False, flags=[], elapsed_ms=0.0, error="boom")
        r = GovernedResponse(final_decision="EXECUTE", blocked=False,
                             observer_results=[obs_in])
        a = runtime._audit_dict("x", "general", "m", r)
        obs = a["observers"][0]
        assert obs["phase"] == "post_output"
        assert obs["activated"] is False
        assert obs["error"] == "boom"

    def test_multiple_observers_preserve_order(self):
        r = GovernedResponse(
            final_decision="EXECUTE", blocked=False,
            observer_results=[
                ObserverResult(module_name="first", phase=ObserverPhase.POST_S),
                ObserverResult(module_name="second",
                               phase=ObserverPhase.POST_OUTPUT),
            ],
        )
        a = runtime._audit_dict("x", "general", "m", r)
        assert [o["module"] for o in a["observers"]] == ["first", "second"]


# ═══════════════════════════════════════════════════════════
#  2. make_ollama_llm_fn — the production hook (requests mocked)
# ═══════════════════════════════════════════════════════════

class _FakeResp:
    def __init__(self, payload, raise_exc=None):
        self._payload = payload
        self._raise = raise_exc
        self.raise_for_status_called = False

    def raise_for_status(self):
        self.raise_for_status_called = True
        if self._raise:
            raise self._raise

    def json(self):
        return self._payload


class TestMakeOllamaLlmFn:
    def test_posts_expected_payload_and_returns_response(self, monkeypatch):
        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["timeout"] = timeout
            return _FakeResp({"response": "  مرحبا  "})

        monkeypatch.setattr(runtime.requests, "post", fake_post)
        fn = runtime.make_ollama_llm_fn(model="test-model")
        out = fn("GOVERNED PROMPT")

        assert out == "مرحبا"  # stripped
        assert captured["json"]["model"] == "test-model"
        assert captured["json"]["prompt"] == "GOVERNED PROMPT"
        assert captured["json"]["stream"] is False
        assert "options" in captured["json"]
        assert captured["url"] == runtime.OLLAMA_GENERATE_URL

    def test_missing_response_key_yields_empty_string(self, monkeypatch):
        monkeypatch.setattr(runtime.requests, "post",
                            lambda *a, **k: _FakeResp({}))
        fn = runtime.make_ollama_llm_fn(model="m")
        assert fn("p") == ""

    def test_null_response_value_yields_empty_string(self, monkeypatch):
        monkeypatch.setattr(runtime.requests, "post",
                            lambda *a, **k: _FakeResp({"response": None}))
        fn = runtime.make_ollama_llm_fn(model="m")
        assert fn("p") == ""

    def test_raise_for_status_is_called(self, monkeypatch):
        holder = {}

        def fake_post(*a, **k):
            r = _FakeResp({"response": "x"})
            holder["resp"] = r
            return r

        monkeypatch.setattr(runtime.requests, "post", fake_post)
        runtime.make_ollama_llm_fn(model="m")("p")
        assert holder["resp"].raise_for_status_called is True


# ═══════════════════════════════════════════════════════════
#  3. govern() — orchestration (governor + llm_fn mocked)
# ═══════════════════════════════════════════════════════════

class _FakeGovernor:
    def __init__(self):
        self.calls = []

    def process(self, text, domain=None, conversation_id=None, llm_fn=None):
        self.calls.append(
            {"text": text, "domain": domain,
             "conversation_id": conversation_id, "llm_fn": llm_fn}
        )
        # Prove the llm_fn was threaded through by invoking it.
        produced = llm_fn("prompt") if llm_fn else None
        return GovernedResponse(
            final_decision="EXECUTE", blocked=False,
            final_response=produced, s_result=_s_result(),
            stage_reached="gate", processing_time_ms=3.0,
        )


class TestGovern:
    def test_threads_llm_fn_and_returns_audit(self, monkeypatch):
        fake_gov = _FakeGovernor()
        monkeypatch.setattr(runtime, "get_governor", lambda domain="general": fake_gov)
        monkeypatch.setattr(runtime, "make_ollama_llm_fn",
                            lambda model: (lambda p: "LLM SAID"))

        audit = runtime.govern("hello", domain="education",
                               conversation_id="c1", model="mmm")

        # Governor was called with our args + a real llm_fn.
        assert fake_gov.calls[0]["text"] == "hello"
        assert fake_gov.calls[0]["domain"] == "education"
        assert fake_gov.calls[0]["conversation_id"] == "c1"
        assert callable(fake_gov.calls[0]["llm_fn"])
        # And the audit reflects the flattened response.
        assert audit["response"] == "LLM SAID"
        assert audit["decision"] == "EXECUTE"
        assert audit["domain"] == "education"
        assert audit["model"] == "mmm"

    def test_defaults_are_general_domain(self, monkeypatch):
        fake_gov = _FakeGovernor()
        monkeypatch.setattr(runtime, "get_governor", lambda domain="general": fake_gov)
        monkeypatch.setattr(runtime, "make_ollama_llm_fn",
                            lambda model: (lambda p: "x"))
        audit = runtime.govern("hi")
        assert audit["domain"] == "general"


# ═══════════════════════════════════════════════════════════
#  4. get_governor() — one boot per process, then cached
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def reset_governor_cache():
    """Isolate the module-level _GOVERNOR singleton for caching tests."""
    saved = runtime._GOVERNOR
    runtime._GOVERNOR = None
    yield
    runtime._GOVERNOR = saved


class TestGetGovernor:
    def test_boots_once_and_caches(self, monkeypatch, reset_governor_cache):
        boot_count = {"n": 0}
        sentinel = object()

        def fake_boot(domain="general"):
            boot_count["n"] += 1
            return sentinel, {"booted": True}

        monkeypatch.setattr(runtime.AATIFGovernor, "boot",
                            staticmethod(fake_boot))

        g1 = runtime.get_governor()
        g2 = runtime.get_governor()
        g3 = runtime.get_governor(domain="healthcare")

        assert g1 is sentinel
        assert g2 is sentinel
        assert g3 is sentinel
        assert boot_count["n"] == 1  # cached after the first boot

    def test_first_call_uses_supplied_domain(self, monkeypatch,
                                             reset_governor_cache):
        seen = {}

        def fake_boot(domain="general"):
            seen["domain"] = domain
            return object(), {}

        monkeypatch.setattr(runtime.AATIFGovernor, "boot",
                            staticmethod(fake_boot))
        runtime.get_governor(domain="tech")
        assert seen["domain"] == "tech"


# ═══════════════════════════════════════════════════════════
#  5. _run_cli — argument parsing (govern / _serve mocked)
# ═══════════════════════════════════════════════════════════

def _fake_audit(**over):
    base = {
        "input": "x", "domain": "general", "model": "m", "response": "hi",
        "governed_prompt": "gp", "decision": "EXECUTE", "blocked": False,
        "block_reason": None, "stage_reached": "gate",
        "processing_time_ms": 1.0, "S": 0.1, "H": 0.2, "I": 0.3, "E": 0.0,
        "theta_effective": 0.4, "s_decision": "EXECUTE", "s_reason": "ok",
        "protocol_action": None, "protocols_triggered": [],
        "emergency_injected": False, "style": "neutral",
        "gate_blocked": False, "gate_flags": [], "observers": [],
    }
    base.update(over)
    return base


class TestRunCli:
    def test_text_arg_calls_govern(self, monkeypatch, capsys):
        seen = {}

        def fake_govern(text, domain="general", conversation_id=None, model=None):
            seen.update(text=text, domain=domain,
                        conversation_id=conversation_id, model=model)
            return _fake_audit(input=text)

        monkeypatch.setattr(runtime, "govern", fake_govern)
        rc = runtime._run_cli(["مرحبا", "--domain", "education"])
        assert rc == 0
        assert seen["text"] == "مرحبا"
        assert seen["domain"] == "education"
        out = capsys.readouterr().out
        assert "AATIF Governed Response" in out

    def test_json_flag_emits_valid_json(self, monkeypatch, capsys):
        monkeypatch.setattr(runtime, "govern",
                            lambda *a, **k: _fake_audit(response="J"))
        rc = runtime._run_cli(["hello", "--json"])
        assert rc == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["response"] == "J"

    def test_reads_stdin_when_no_text_arg(self, monkeypatch, capsys):
        seen = {}
        monkeypatch.setattr(sys, "stdin",
                            type("S", (), {"read": staticmethod(lambda: "  piped  ")})())
        monkeypatch.setattr(runtime, "govern",
                            lambda text, **k: seen.update(text=text) or _fake_audit())
        rc = runtime._run_cli([])
        assert rc == 0
        assert seen["text"] == "piped"  # stripped

    def test_empty_input_errors(self, monkeypatch):
        # No arg and empty stdin → argparse error → SystemExit(2).
        monkeypatch.setattr(sys, "stdin",
                            type("S", (), {"read": staticmethod(lambda: "   ")})())
        monkeypatch.setattr(runtime, "govern",
                            lambda *a, **k: pytest.fail("govern must not run"))
        with pytest.raises(SystemExit):
            runtime._run_cli([])

    def test_serve_flag_delegates_to_serve(self, monkeypatch):
        called = {}
        monkeypatch.setattr(runtime, "_serve",
                            lambda host, port: called.update(host=host, port=port) or 0)
        rc = runtime._run_cli(["--serve", "--host", "0.0.0.0", "--port", "9999"])
        assert rc == 0
        assert called == {"host": "0.0.0.0", "port": 9999}


# ═══════════════════════════════════════════════════════════
#  6. _print_human — the human-readable report
# ═══════════════════════════════════════════════════════════

class TestPrintHuman:
    def test_proceed_shows_response_and_green(self, capsys):
        runtime._print_human(_fake_audit(response="the answer"))
        out = capsys.readouterr().out
        assert "🟢 OK" in out
        assert "the answer" in out
        assert "🔴 BLOCKED" not in out

    def test_blocked_hides_response_and_shows_reason(self, capsys):
        runtime._print_human(_fake_audit(
            blocked=True, block_reason="refused",
            response=None, decision="SAFE_FREEZE"))
        out = capsys.readouterr().out
        assert "🔴 BLOCKED" in out
        assert "refused" in out
        assert "declined to produce a reply" in out

    def test_audit_numbers_are_rendered(self, capsys):
        runtime._print_human(_fake_audit(H=0.55, I=0.66, E=0.07))
        out = capsys.readouterr().out
        assert "0.55" in out
        assert "0.66" in out


# ═══════════════════════════════════════════════════════════
#  7. FastAPI front door — graceful degradation both ways
# ═══════════════════════════════════════════════════════════

class TestFastAPIDegradation:
    def test_module_import_never_boots_a_governor(self, reset_governor_cache):
        """Importing the runtime must not have booted a Governor as a side
        effect — the cache stays empty until get_governor() is called."""
        # reset_governor_cache set it to None; a fresh import must not repopulate.
        importlib.reload(runtime)
        # After reload the cache is a fresh None (module top-level default).
        assert runtime._GOVERNOR is None

    def test_govern_request_and_app_are_consistent(self):
        """If FastAPI/pydantic are absent both degrade to None; if present the
        request model exposes its defaults. Either way must be internally
        consistent — no half-built HTTP door."""
        if runtime.GovernRequest is None:
            # pydantic not installed → app must also be None.
            assert runtime.app is None
        else:
            req = runtime.GovernRequest(text="hi")
            assert req.text == "hi"
            assert req.domain == "general"
            assert req.conversation_id is None
