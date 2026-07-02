#!/usr/bin/env python3
"""
AATIF Runtime — الباب الأمامي (the front door)

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)

═══════════════════════════════════════════════════════════════════════════
WHY THIS FILE EXISTS
═══════════════════════════════════════════════════════════════════════════

The integration audit (engine/INTEGRATION_AUDIT.md) found that عاطف is a fully
built car with no ignition: `AATIFGovernor` genuinely chains
S(d) → P(d) → R(d) → memory → governed prompt → Output Gate, 94 pipeline tests
pass, and Ollama/bge-m3 is up — but there was NO entry point and NO production
`llm_fn`. You could not hand عاطف a string from outside the test suite.

This module is the ignition. It:
  1. Boots the Governor via `AATIFGovernor.boot()` (the FN#045 safe boot).
  2. Wires a real `llm_fn` that calls a local Ollama chat model.
  3. Exposes TWO front doors:
       a. CLI:  python3 engine/aatif_runtime.py "your text"
       b. HTTP: POST /govern  {"text": "..."}  (FastAPI, if installed)
  4. Surfaces the full audit trail (S/H/I/E, decision, gate, stage, timing)
     alongside the governed response.

It CREATES nothing new in the engine — it only calls the existing public API
(`AATIFGovernor.boot()` and `.process(..., llm_fn=...)`). The Governor still
composes the governed prompt before the model speaks and runs the Output Gate
after it speaks, so the model is boxed on both sides.

    "S يقرر هل نجاوب — P يقرر بأي شروط — R يقرر بأي أسلوب — والبوابة آخر حارس"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

import requests

# ── Make the engine directory importable (same pattern as the scorers) ──
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from aatif_governor import AATIFGovernor, GovernedResponse  # noqa: E402

# ═══════════════════════════════════════════════════════════
#  Configuration (override via environment)
# ═══════════════════════════════════════════════════════════

# The chat model that generates the user-facing reply. bge-m3 is the EMBEDDING
# backend the safety math is calibrated on (never a chat model) — this is a
# separate generation model. `aatif:latest` is fast (~4s) and Arabic-aware on
# this Mac; qwen2.5:32b is stronger but much slower. Override with AATIF_LLM_MODEL.
OLLAMA_CHAT_MODEL = os.environ.get("AATIF_LLM_MODEL", "aatif:latest")
OLLAMA_GENERATE_URL = os.environ.get(
    "AATIF_OLLAMA_URL", "http://127.0.0.1:11434/api/generate"
)
# Generation is only reached AFTER S/P/R clear, so a generous timeout is fine.
LLM_TIMEOUT_SECONDS = float(os.environ.get("AATIF_LLM_TIMEOUT", "180"))


# ═══════════════════════════════════════════════════════════
#  The production llm_fn — the missing hook (audit blocker #2)
# ═══════════════════════════════════════════════════════════

def make_ollama_llm_fn(model: str = OLLAMA_CHAT_MODEL):
    """Build an `llm_fn(governed_prompt) -> str` backed by a local Ollama model.

    The Governor feeds this the ALREADY-GOVERNED prompt (P instructions +
    R style + memory + the user message) and gates whatever text it returns.
    So this callable only has to turn a prompt into a string — safety is the
    Governor's job on both sides of it.
    """

    def llm_fn(prompt: str) -> str:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.4, "num_predict": 512},
            },
            timeout=LLM_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        # /api/generate returns {"response": "...", ...}. Reasoning models
        # (e.g. gpt-oss) put chain-of-thought in "thinking" and the answer in
        # "response" — we deliberately only surface "response".
        return (resp.json().get("response") or "").strip()

    return llm_fn


# ═══════════════════════════════════════════════════════════
#  Boot — one Governor per process (cached)
# ═══════════════════════════════════════════════════════════

_GOVERNOR: Optional[AATIFGovernor] = None


def get_governor(domain: str = "general") -> AATIFGovernor:
    """Boot the Governor once and reuse it. Raises DegradedBackendError if the
    calibrated bge-m3 backend is not reachable — a safety refusal, not a bug."""
    global _GOVERNOR
    if _GOVERNOR is None:
        _GOVERNOR, _boot = AATIFGovernor.boot(domain=domain)
    return _GOVERNOR


# ═══════════════════════════════════════════════════════════
#  govern() — send text in, get a governed response + audit out
# ═══════════════════════════════════════════════════════════

def govern(
    text: str,
    domain: str = "general",
    conversation_id: Optional[str] = None,
    model: str = OLLAMA_CHAT_MODEL,
) -> dict:
    """Run one message through the full pipeline and return a JSON-ready dict
    containing the user-facing response AND the audit trail."""
    governor = get_governor(domain=domain)
    llm_fn = make_ollama_llm_fn(model=model)
    result = governor.process(
        text, domain=domain, conversation_id=conversation_id, llm_fn=llm_fn
    )
    return _audit_dict(text, domain, model, result)


def _audit_dict(
    text: str, domain: str, model: str, r: GovernedResponse
) -> dict:
    """Flatten the rich GovernedResponse into a compact, JSON-serialisable
    audit trail — the numbers a reviewer needs to see WHY, next to the WHAT."""
    s = r.s_result or {}
    p = r.p_result
    gate = r.gate_result
    return {
        "input": text,
        "domain": domain,
        "model": model,
        # ── the answer ──
        "response": r.final_response,
        "governed_prompt": r.governed_prompt,
        # ── the verdict ──
        "decision": r.final_decision,
        "blocked": r.blocked,
        "block_reason": r.block_reason or None,
        "stage_reached": r.stage_reached,
        "processing_time_ms": r.processing_time_ms,
        # ── S(d): the safety math ──
        "S": s.get("S"),
        "H": s.get("H"),   # harm proximity  — حرارة الكلمة
        "I": s.get("I"),   # intent          — النية
        "E": s.get("E"),   # emotion         — الشعور
        "theta_effective": s.get("theta_effective"),
        "s_decision": s.get("decision"),
        "s_reason": s.get("decision_reason"),
        # ── P(d): domain protocols ──
        "protocol_action": getattr(p, "highest_action", None),
        "protocols_triggered": [t.name for t in getattr(p, "triggered", [])],
        "emergency_injected": r.emergency_injected,
        # ── R(d): response style ──
        "style": getattr(r.r_result, "style_recommendation", None),
        # ── Output Gate: the last guard ──
        "gate_blocked": getattr(gate, "blocked", None),
        "gate_flags": list(getattr(gate, "flags", []) or []),
        # ── Observer results (B-prime: observe-only, never block) ──
        "observers": [
            {
                "module": getattr(obs, "module_name", "?"),
                "phase": getattr(obs, "phase", "?").value
                    if hasattr(getattr(obs, "phase", None), "value")
                    else str(getattr(obs, "phase", "?")),
                "activated": getattr(obs, "activated", False),
                "flags": list(getattr(obs, "flags", []) or []),
                "elapsed_ms": getattr(obs, "elapsed_ms", 0.0),
                "error": getattr(obs, "error", "") or None,
            }
            for obs in getattr(r, "observer_results", [])
        ],
    }


# ═══════════════════════════════════════════════════════════
#  CLI front door
# ═══════════════════════════════════════════════════════════

def _print_human(a: dict) -> None:
    flag = "🔴 BLOCKED" if a["blocked"] else "🟢 OK"
    print("=" * 70)
    print("  عاطف — AATIF Governed Response")
    print("=" * 70)
    print(f"📝 input   : {a['input']}   [{a['domain']}]")
    print(f"{flag}  decision={a['decision']}  stage={a['stage_reached']}  "
          f"({a['processing_time_ms']} ms)")
    print("-" * 70)
    print("AUDIT TRAIL")
    print(f"  S(d)  S={a['S']}  H={a['H']}  I={a['I']}  E={a['E']}  "
          f"θ_eff={a['theta_effective']}")
    print(f"  S decision : {a['s_decision']}  ({a['s_reason']})")
    print(f"  P(d)  action={a['protocol_action']}  "
          f"triggered={a['protocols_triggered']}  "
          f"emergency_injected={a['emergency_injected']}")
    print(f"  R(d)  style={a['style']}")
    print(f"  Gate  blocked={a['gate_blocked']}  flags={a['gate_flags']}")
    print("-" * 70)
    if a["blocked"]:
        print(f"⛔ reason : {a['block_reason']}")
        print("💬 response: (none — عاطف declined to produce a reply)")
    else:
        print(f"💬 response:\n{a['response']}")
    print("=" * 70)


def _run_cli(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="عاطف runtime — send text through the AATIF Governor."
    )
    parser.add_argument("text", nargs="?", help="the user message to govern")
    parser.add_argument("--domain", default="general",
                        help="domain (general/healthcare/education/tech/...)")
    parser.add_argument("--conversation-id", default=None,
                        help="conversation id for memory/hysteresis")
    parser.add_argument("--model", default=OLLAMA_CHAT_MODEL,
                        help="Ollama chat model (default: %(default)s)")
    parser.add_argument("--json", action="store_true",
                        help="print the raw audit JSON instead of a report")
    parser.add_argument("--serve", action="store_true",
                        help="start the HTTP server (POST /govern) instead")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    if args.serve:
        return _serve(args.host, args.port)

    text = args.text
    if not text:  # allow piping: echo "..." | python3 aatif_runtime.py
        text = sys.stdin.read().strip()
    if not text:
        parser.error("no text supplied (pass an argument or pipe via stdin)")

    audit = govern(text, domain=args.domain,
                   conversation_id=args.conversation_id, model=args.model)
    if args.json:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        _print_human(audit)
    return 0


# ═══════════════════════════════════════════════════════════
#  HTTP front door (FastAPI) — optional
# ═══════════════════════════════════════════════════════════

# The request model lives at MODULE scope on purpose: with
# `from __future__ import annotations` in effect, FastAPI resolves the endpoint's
# type hints against the module globals. A class defined inside _build_app()
# would be invisible there and FastAPI would mistake the body for a query param.
try:  # pragma: no cover - pydantic ships with fastapi
    from pydantic import BaseModel

    class GovernRequest(BaseModel):
        text: str
        domain: str = "general"
        conversation_id: Optional[str] = None
        model: str = OLLAMA_CHAT_MODEL
except ImportError:  # pragma: no cover - fastapi/pydantic not installed
    GovernRequest = None  # type: ignore


def _build_app():
    """Build the FastAPI app. Imported lazily so the CLI works without
    fastapi/uvicorn installed."""
    from fastapi import FastAPI

    app = FastAPI(title="عاطف — AATIF Runtime", version="1.0")

    @app.get("/health")
    def health():
        gov = get_governor()
        return {"status": "ok", "degraded": gov.is_degraded,
                "model": OLLAMA_CHAT_MODEL}

    @app.post("/govern")
    def govern_endpoint(req: GovernRequest):
        return govern(req.text, domain=req.domain,
                      conversation_id=req.conversation_id, model=req.model)

    return app


def _serve(host: str, port: int) -> int:
    import uvicorn
    print(f"🚪 عاطف front door up on http://{host}:{port}  "
          f"(POST /govern, model={OLLAMA_CHAT_MODEL})")
    uvicorn.run(_build_app(), host=host, port=port)
    return 0


# Expose `app` for `uvicorn engine.aatif_runtime:app` deployments.
try:  # pragma: no cover - only when fastapi is present
    app = _build_app()
except Exception:  # pragma: no cover - fastapi not installed / boot deferred
    app = None


if __name__ == "__main__":
    raise SystemExit(_run_cli())
