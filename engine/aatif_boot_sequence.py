#!/usr/bin/env python3
"""
AATIF Safe Boot Sequence — تسلسل الإقلاع الآمن  (Field Note #045)
==================================================================

FN#045 core principle: "Nothing outputs until initialization completes — in order."

Ordered, gated initialization for the AATIF governance engine. Required stages
fail-fast: if stage N cannot be verified, boot halts and returns a BootResult
with ready=False. Optional modules that fail are logged and marked unavailable;
boot continues.

Fail-safe default (Saltzer & Schroeder 1975 — principle of fail-safe defaults):
if boot has not completed successfully, the default is DENY.

Boot stages (required → halt on failure):
  1. CORE_ENGINE         — AATIFEngine + calibrated embedding backend
  2. DOMAIN_PROTOCOLS    — DomainProtocol can instantiate and evaluate
  3. RESPONSE_SHAPER     — REquation can compute (pure math)
  4. CONVERSATION_MEMORY — AATIFConversationMemory can instantiate
  5. TIME_SENSE          — TimeSense can instantiate
  6. OUTPUT_GATE         — AATIFOutputGate can instantiate

  7. OPTIONAL_MODULES    — enrichment modules checked; failures do not halt boot
  8. SYSTEM_READY        — all required stages passed

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Optional

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# ── Required modules — always present; their constructors are exercised in
#    each stage's try-except. Import failure here IS a hard error.
from aatif_s_equation import AATIFEngine, DOMAIN_CONFIG
from aatif_domain_protocols import DomainProtocol
from aatif_r_equation import REquation
from aatif_conversation_memory import AATIFConversationMemory
from aatif_time_sense import TimeSense
from aatif_output_gate import AATIFOutputGate

# ── Optional modules — checked but never blocking ──
try:
    from aatif_false_goodness_detector import FalseGoodnessDetector
    HAS_FALSE_GOODNESS = True
except ImportError:
    FalseGoodnessDetector = None  # type: ignore[assignment,misc]
    HAS_FALSE_GOODNESS = False

try:
    from aatif_meta_oversight import MetaOversightEngine
    HAS_META_OVERSIGHT = True
except ImportError:
    MetaOversightEngine = None  # type: ignore[assignment,misc]
    HAS_META_OVERSIGHT = False

try:
    from aatif_judgment_memory import JudgmentMemory
    HAS_JUDGMENT_MEMORY = True
except ImportError:
    JudgmentMemory = None  # type: ignore[assignment,misc]
    HAS_JUDGMENT_MEMORY = False

try:
    from aatif_response_shaper import AATIFResponseShaper
    HAS_RESPONSE_SHAPER_MODULE = True
except ImportError:
    AATIFResponseShaper = None  # type: ignore[assignment,misc]
    HAS_RESPONSE_SHAPER_MODULE = False

try:
    from aatif_fingerprint import UserFingerprint
    HAS_FINGERPRINT = True
except ImportError:
    UserFingerprint = None  # type: ignore[assignment,misc]
    HAS_FINGERPRINT = False

try:
    from aatif_temporal_memory import TemporalMemory
    HAS_TEMPORAL_MEMORY = True
except ImportError:
    TemporalMemory = None  # type: ignore[assignment,misc]
    HAS_TEMPORAL_MEMORY = False

try:
    from aatif_contextual_intent import ContextualIntentScorer
    HAS_CONTEXTUAL_INTENT = True
except ImportError:
    ContextualIntentScorer = None  # type: ignore[assignment,misc]
    HAS_CONTEXTUAL_INTENT = False


# ═══════════════════════════════════════════════════════════
#  Stage name constants
# ═══════════════════════════════════════════════════════════

STAGE_CORE_ENGINE         = "CORE_ENGINE"
STAGE_DOMAIN_PROTOCOLS    = "DOMAIN_PROTOCOLS"
STAGE_RESPONSE_SHAPER     = "RESPONSE_SHAPER"
STAGE_CONVERSATION_MEMORY = "CONVERSATION_MEMORY"
STAGE_TIME_SENSE          = "TIME_SENSE"
STAGE_OUTPUT_GATE         = "OUTPUT_GATE"
STAGE_OPTIONAL_MODULES    = "OPTIONAL_MODULES"
STAGE_SYSTEM_READY        = "SYSTEM_READY"

# Required stages — failure at any of these halts the sequence immediately.
REQUIRED_STAGES = (
    STAGE_CORE_ENGINE,
    STAGE_DOMAIN_PROTOCOLS,
    STAGE_RESPONSE_SHAPER,
    STAGE_CONVERSATION_MEMORY,
    STAGE_TIME_SENSE,
    STAGE_OUTPUT_GATE,
)

# Optional module keys used in BootResult.optional_modules.
OPT_FALSE_GOODNESS    = "FalseGoodnessDetector"
OPT_META_OVERSIGHT    = "MetaOversightEngine"
OPT_JUDGMENT_MEMORY   = "JudgmentMemory"
OPT_RESPONSE_SHAPER   = "AATIFResponseShaper"
OPT_FINGERPRINT       = "UserFingerprint"
OPT_TEMPORAL_MEMORY   = "TemporalMemory"
OPT_CONTEXTUAL_INTENT = "ContextualIntentScorer"


# ═══════════════════════════════════════════════════════════
#  Dataclasses
# ═══════════════════════════════════════════════════════════

@dataclass
class StageResult:
    """Result of a single boot stage."""
    stage: str
    passed: bool
    error: Optional[str]
    duration_ms: float


@dataclass
class BootResult:
    """
    Complete result of the AATIF safe boot sequence.

    Fail-safe contract: only send requests through a Governor if ``ready is
    True``. An unverified or partially-initialized engine must default to DENY
    (Saltzer & Schroeder 1975).
    """
    success: bool               # True when every required stage passed
    stage_results: dict         # stage_name → StageResult
    failed_stage: Optional[str] # first required stage that failed, else None
    ready: bool                 # True iff success (explicit alias for clarity)
    optional_modules: dict      # module_name → bool (importable AND constructable)
    boot_time_ms: float         # total wall-clock boot time in milliseconds


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 3)


def _backend_is_calibrated(engine) -> bool:
    """True iff the engine's H scorer runs on the calibrated bge-m3 backend.

    Mirrors AATIFGovernor._backend_is_calibrated — kept local to avoid
    a circular import between governor and boot_sequence.
    """
    h = getattr(engine, "h_scorer", None)
    name = getattr(h, "backend_name", "") if h is not None else ""
    return isinstance(name, str) and name.startswith("ollama")


# ═══════════════════════════════════════════════════════════
#  boot_aatif — the safe boot function
# ═══════════════════════════════════════════════════════════

def boot_aatif(
    backend=None,
    domain: str = "general",
    llm_fn=None,
) -> BootResult:
    """
    Run the AATIF safe boot sequence.

    Verifies each required engine stage in order. If any required stage fails
    the boot halts immediately and returns a BootResult with ``ready=False``.
    Optional modules that fail are logged in ``optional_modules`` but do not
    halt the sequence.

    Args:
        backend: Optional pre-constructed AATIFEngine (or compatible object
            with an ``h_scorer.backend_name`` attribute). When None the real
            AATIFEngine is constructed — requires a live Ollama/bge-m3. Inject
            a FakeSEngine (``h_scorer.backend_name = "ollama:bge-m3"``) for
            tests that run without Ollama.
        domain: Domain to exercise during DOMAIN_PROTOCOLS verification.
            Must be a key in DOMAIN_CONFIG (default ``"general"``).
        llm_fn: Reserved for future compatibility; not used during boot.

    Returns:
        BootResult — treat ``ready=False`` as DENY (fail-safe default).
    """
    boot_start = time.perf_counter()
    stage_results: dict = {}
    optional_modules: dict = {}

    # ── Local helpers captured from the outer scope ──

    def _record(stage: str, passed: bool, error: Optional[str],
                duration_ms: float) -> None:
        stage_results[stage] = StageResult(
            stage=stage, passed=passed, error=error, duration_ms=duration_ms,
        )

    def _halt(stage: str, error: str, duration_ms: float) -> BootResult:
        """Record failure and return a halted BootResult immediately."""
        _record(stage, False, error, duration_ms)
        return BootResult(
            success=False,
            stage_results=stage_results,
            failed_stage=stage,
            ready=False,
            optional_modules=optional_modules,
            boot_time_ms=_elapsed_ms(boot_start),
        )

    def _try_optional(name: str, fn) -> None:
        """Call fn() to construct an optional module; log success or failure."""
        try:
            fn()
            optional_modules[name] = True
        except Exception:
            optional_modules[name] = False

    # ═══════════════════════════════════════════════════════
    #  Stage 1 — CORE_ENGINE
    #  S equation + H/I/E scorers must be constructable and
    #  the embedding backend must be calibrated (ollama:bge-m3).
    # ═══════════════════════════════════════════════════════
    t0 = time.perf_counter()
    try:
        s_engine = backend if backend is not None else AATIFEngine()
        if not _backend_is_calibrated(s_engine):
            bname = getattr(
                getattr(s_engine, "h_scorer", None), "backend_name", "unknown"
            )
            raise RuntimeError(
                f"H scorer backend '{bname}' is not calibrated (expected "
                f"ollama:bge-m3). AATIF thresholds are calibrated for the "
                f"bge-m3 cosine distribution — refusing an uncalibrated engine."
            )
        _record(STAGE_CORE_ENGINE, True, None, _elapsed_ms(t0))
    except Exception as exc:
        return _halt(STAGE_CORE_ENGINE, str(exc), _elapsed_ms(t0))

    # ═══════════════════════════════════════════════════════
    #  Stage 2 — DOMAIN_PROTOCOLS
    #  DomainProtocol must instantiate and evaluate the boot domain.
    # ═══════════════════════════════════════════════════════
    t0 = time.perf_counter()
    try:
        if domain not in DOMAIN_CONFIG:
            raise ValueError(
                f"Boot domain '{domain}' not in DOMAIN_CONFIG. "
                f"Valid: {sorted(DOMAIN_CONFIG.keys())}"
            )
        proto = DomainProtocol()
        proto.evaluate("boot-check", domain=domain, s_decision="EXECUTE")
        _record(STAGE_DOMAIN_PROTOCOLS, True, None, _elapsed_ms(t0))
    except Exception as exc:
        return _halt(STAGE_DOMAIN_PROTOCOLS, str(exc), _elapsed_ms(t0))

    # ═══════════════════════════════════════════════════════
    #  Stage 3 — RESPONSE_SHAPER (REquation — pure math)
    #  Must instantiate and compute a non-None style result.
    #  REquation.compute() accepts time_reading=None so we
    #  do NOT call TimeSense here; that is Stage 5's concern.
    # ═══════════════════════════════════════════════════════
    t0 = time.perf_counter()
    try:
        req = REquation()
        result = req.compute(text="boot-check", domain=domain, time_reading=None)
        if result is None:
            raise RuntimeError("REquation.compute() returned None")
        _record(STAGE_RESPONSE_SHAPER, True, None, _elapsed_ms(t0))
    except Exception as exc:
        return _halt(STAGE_RESPONSE_SHAPER, str(exc), _elapsed_ms(t0))

    # ═══════════════════════════════════════════════════════
    #  Stage 4 — CONVERSATION_MEMORY
    # ═══════════════════════════════════════════════════════
    t0 = time.perf_counter()
    try:
        AATIFConversationMemory()
        _record(STAGE_CONVERSATION_MEMORY, True, None, _elapsed_ms(t0))
    except Exception as exc:
        return _halt(STAGE_CONVERSATION_MEMORY, str(exc), _elapsed_ms(t0))

    # ═══════════════════════════════════════════════════════
    #  Stage 5 — TIME_SENSE
    # ═══════════════════════════════════════════════════════
    t0 = time.perf_counter()
    try:
        TimeSense()
        _record(STAGE_TIME_SENSE, True, None, _elapsed_ms(t0))
    except Exception as exc:
        return _halt(STAGE_TIME_SENSE, str(exc), _elapsed_ms(t0))

    # ═══════════════════════════════════════════════════════
    #  Stage 6 — OUTPUT_GATE
    # ═══════════════════════════════════════════════════════
    t0 = time.perf_counter()
    try:
        AATIFOutputGate()
        _record(STAGE_OUTPUT_GATE, True, None, _elapsed_ms(t0))
    except Exception as exc:
        return _halt(STAGE_OUTPUT_GATE, str(exc), _elapsed_ms(t0))

    # ═══════════════════════════════════════════════════════
    #  Stage 7 — OPTIONAL_MODULES
    #  Each module is attempted; failures are logged and boot continues.
    #  Modules that require constructor args (JudgmentMemory, TemporalMemory)
    #  are exercised with a temporary directory.
    # ═══════════════════════════════════════════════════════
    t0 = time.perf_counter()

    if HAS_FALSE_GOODNESS and FalseGoodnessDetector is not None:
        _try_optional(OPT_FALSE_GOODNESS, FalseGoodnessDetector)
    else:
        optional_modules[OPT_FALSE_GOODNESS] = False

    if HAS_META_OVERSIGHT and MetaOversightEngine is not None:
        _try_optional(OPT_META_OVERSIGHT, MetaOversightEngine)
    else:
        optional_modules[OPT_META_OVERSIGHT] = False

    if HAS_JUDGMENT_MEMORY and JudgmentMemory is not None:
        def _mk_jm():
            with tempfile.TemporaryDirectory(prefix="aatif_boot_") as d:
                JudgmentMemory(db_path=os.path.join(d, "boot.db"))
        _try_optional(OPT_JUDGMENT_MEMORY, _mk_jm)
    else:
        optional_modules[OPT_JUDGMENT_MEMORY] = False

    if HAS_RESPONSE_SHAPER_MODULE and AATIFResponseShaper is not None:
        _try_optional(OPT_RESPONSE_SHAPER, AATIFResponseShaper)
    else:
        optional_modules[OPT_RESPONSE_SHAPER] = False

    if HAS_FINGERPRINT and UserFingerprint is not None:
        _try_optional(OPT_FINGERPRINT, UserFingerprint)
    else:
        optional_modules[OPT_FINGERPRINT] = False

    if HAS_TEMPORAL_MEMORY and TemporalMemory is not None:
        def _mk_tm():
            with tempfile.TemporaryDirectory(prefix="aatif_boot_") as d:
                TemporalMemory(storage_dir=d)
        _try_optional(OPT_TEMPORAL_MEMORY, _mk_tm)
    else:
        optional_modules[OPT_TEMPORAL_MEMORY] = False

    if HAS_CONTEXTUAL_INTENT and ContextualIntentScorer is not None:
        _try_optional(OPT_CONTEXTUAL_INTENT, ContextualIntentScorer)
    else:
        optional_modules[OPT_CONTEXTUAL_INTENT] = False

    _record(STAGE_OPTIONAL_MODULES, True, None, _elapsed_ms(t0))

    # ═══════════════════════════════════════════════════════
    #  Stage 8 — SYSTEM_READY
    #  All required stages verified. Engine is safe to accept requests.
    # ═══════════════════════════════════════════════════════
    t0 = time.perf_counter()
    _record(STAGE_SYSTEM_READY, True, None, _elapsed_ms(t0))

    return BootResult(
        success=True,
        stage_results=stage_results,
        failed_stage=None,
        ready=True,
        optional_modules=optional_modules,
        boot_time_ms=_elapsed_ms(boot_start),
    )
