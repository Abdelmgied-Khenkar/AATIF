#!/usr/bin/env python3
"""
AATIF Judgment Integration — ربط ذاكرة الحُكم بالمحافظ
========================================================

Clean integration layer that connects JudgmentMemory to the existing
S equation pipeline WITHOUT modifying the production governor or
S equation modules.

Design philosophy:
    This is a WRAPPER, not a replacement. The existing AATIFGovernor
    handles the full S → P → R → Gate pipeline. This module adds the
    judgment memory layer around the S equation computation specifically:

    1. Before S: build_context() to get JudgmentContext
    2. Adjust H and θ based on JudgmentContext (respecting safety invariants)
    3. After S: record_judgment() to write outcome to ledger

    Belt AND suspenders: safety checks are duplicated here even though
    JudgmentMemory already enforces them. Two guards > one.

Safety invariants (duplicated from JudgmentMemory — belt AND suspenders):
    1. H > 0.7 → bypass memory entirely, go straight to compute_s()
    2. CBRN/jailbreak detected → bypass memory entirely
    3. H_adj floor = 0.15 — adjusted H never goes below this
    4. θ adjustments bounded: loosen ≤ +0.05, tighten ≥ -0.20
    5. θ floor = 0.20 — effective θ never drops below this

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Ensure the engine directory is importable
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from aatif_s_equation import (
    compute_s_gated_from_scores,
    compute_s_from_scores,
    GATED_PROFILES,
    DOMAIN_CONFIG,
    H_GATED_HARD_OVERRIDE,
    _has_cbrn_match,
    _has_jailbreak_markers,
    _has_override_attempt,
)
from aatif_judgment_memory import (
    JudgmentMemory,
    JudgmentContext,
    DOMAIN_PROFILES,
    H_HARD_OVERRIDE,
    H_ADJUSTMENT_FLOOR,
    THETA_MAX_LOOSEN,
    THETA_MAX_TIGHTEN,
    THETA_FLOOR,
    _hash_message,
)


# ═══════════════════════════════════════════════════════════
#  JudgmentAwareResult — extended result with judgment context
# ═══════════════════════════════════════════════════════════

@dataclass
class JudgmentAwareResult:
    """Result from JudgmentAwareGovernor.process().

    Extends the standard S equation result dict with judgment context,
    effective parameters, and safety bypass information.
    """
    # The raw S equation result dict (H, I, E, S, decision, etc.)
    s_result: dict = field(default_factory=dict)

    # Judgment context produced by JudgmentMemory.build_context()
    judgment_context: Optional[JudgmentContext] = None

    # Effective parameters after adjustment
    theta_effective: float = 0.40
    h_original: float = 0.0
    h_adjusted: float = 0.0

    # Safety bypass flags
    memory_bypassed: bool = False
    bypass_reason: str = ""

    # Convenience accessors
    @property
    def decision(self) -> str:
        return self.s_result.get("decision", "SAFE_FREEZE")

    @property
    def S(self) -> float:
        return self.s_result.get("S", 0.0)

    @property
    def H(self) -> float:
        return self.s_result.get("H", 0.0)

    @property
    def blocked(self) -> bool:
        return self.decision in ("SAFE_STOP", "SAFE_FREEZE")



# ═══════════════════════════════════════════════════════════
#  JudgmentAwareGovernor — wraps S equation with judgment memory
# ═══════════════════════════════════════════════════════════

class JudgmentAwareGovernor:
    """Wraps the S equation computation with JudgmentMemory context.

    This does NOT replace the full AATIFGovernor pipeline (S → P → R → Gate).
    It wraps specifically the S equation scoring step, adding judgment memory
    context before and recording results after.

    Usage:
        gov = JudgmentAwareGovernor(
            judgment_memory=JudgmentMemory("/path/to/db"),
            domain_sensitivity=0.4,
        )
        result = gov.process(
            H=0.2, I=0.8, E=0.6,
            text="عطني فكرة هدية",
            session_id="user-42",
        )
        print(result.decision)       # "EXECUTE"
        print(result.judgment_context.theta_adjustment)  # e.g. 0.0

    Belt AND suspenders safety:
        Safety checks are duplicated here even though JudgmentMemory
        already enforces them internally. The integration layer adds
        an OUTER ring of protection:
          - H > 0.7 check before calling build_context()
          - CBRN/jailbreak check before calling build_context()
          - θ bounds verification after receiving theta_adjustment
          - H floor enforcement after h_adjustment
    """

    def __init__(
        self,
        judgment_memory: JudgmentMemory,
        domain_sensitivity: float = 0.2,
        profile: str = "default",
        equation_mode: str = "gated",
        domain: Optional[str] = None,
    ):
        """Initialize JudgmentAwareGovernor.

        Args:
            judgment_memory: JudgmentMemory instance (manages the ledger).
            domain_sensitivity: D parameter (0.0-1.0). Passed through to
                JudgmentMemory for context building.
            profile: S equation weight profile ("default", "high_sensitivity",
                "relaxed" for gated; all classic profiles for classic).
            equation_mode: "gated" (default) or "classic".
            domain: AATIF domain for theta override ("healthcare", "general",
                etc.). Only used in gated mode.
        """
        self.judgment_memory = judgment_memory
        self.domain_sensitivity = max(0.0, min(1.0, domain_sensitivity))
        self.profile = profile
        self.equation_mode = equation_mode
        self.domain = domain

    def process(
        self,
        H: float,
        I: float,
        E: float,
        text: str = "",
        session_id: str = "default",
        msg_embedding: Optional[np.ndarray] = None,
        dialect: Optional[str] = None,
    ) -> JudgmentAwareResult:
        """Process scores through the judgment-aware S equation pipeline.

        Pipeline:
            a. Check safety bypasses (H > 0.7, CBRN, jailbreak)
            b. Build JudgmentContext from memory
            c. Apply context adjustments to H and θ
            d. Call compute_s() with adjusted values
            e. Record judgment to ledger
            f. Return full result with context

        Args:
            H: harm score (0.0-1.0).
            I: intent score (0.0-1.0).
            E: emotion score (0.0-1.0).
            text: original message text (used for CBRN/jailbreak detection
                and message hashing; empty string skips detection).
            session_id: session/user identifier for memory lookup.
            msg_embedding: bge-m3 embedding for similarity lookup.
            dialect: detected dialect for context.

        Returns:
            JudgmentAwareResult with full audit trail.
        """
        result = JudgmentAwareResult(h_original=H)

        # ── SAFETY BYPASS 1: H > 0.7 (hard override) ──
        # Belt: check here BEFORE touching memory.
        # Suspenders: JudgmentMemory also checks internally.
        if H > H_HARD_OVERRIDE:
            result.memory_bypassed = True
            result.bypass_reason = (
                f"H={H:.4f} > H_HARD_OVERRIDE={H_HARD_OVERRIDE} — "
                f"memory bypassed (الاذي مالوش توقيت)"
            )
            result.h_adjusted = H
            s_result = self._compute_s(H, I, E)
            result.s_result = s_result
            result.theta_effective = s_result.get("theta_effective", 0.40)
            self._record(session_id, text, msg_embedding, s_result,
                         dialect, bypassed=True)
            return result

        # ── SAFETY BYPASS 2: CBRN / jailbreak detection ──
        # If text triggers CBRN regex or jailbreak markers, skip memory.
        if text:
            cbrn_detected, _ = _has_cbrn_match(text)
            jailbreak_detected = _has_jailbreak_markers(text)
            override_detected = _has_override_attempt(text)

            if cbrn_detected or jailbreak_detected or override_detected:
                reasons = []
                if cbrn_detected:
                    reasons.append("CBRN")
                if jailbreak_detected:
                    reasons.append("jailbreak")
                if override_detected:
                    reasons.append("override")

                result.memory_bypassed = True
                result.bypass_reason = (
                    f"Safety bypass: {', '.join(reasons)} detected — "
                    f"memory bypassed entirely"
                )
                result.h_adjusted = H
                s_result = self._compute_s(H, I, E)
                result.s_result = s_result
                result.theta_effective = s_result.get(
                    "theta_effective", 0.40
                )
                self._record(session_id, text, msg_embedding, s_result,
                             dialect, bypassed=True)
                return result

        # ── STEP b: Build JudgmentContext ──
        ctx = self.judgment_memory.build_context(
            msg_embedding=msg_embedding,
            session_id=session_id,
            dialect=dialect,
        )
        result.judgment_context = ctx

        # ── STEP c: Apply adjustments ──

        # c1. Adjust H (currently Phase 1: h_adjustment is always 0.0
        #     but the machinery is in place for Phase 2).
        h_adj = H + ctx.h_adjustment
        # Belt: enforce H floor (suspenders: JudgmentMemory also does this)
        h_adj = max(H_ADJUSTMENT_FLOOR, h_adj)
        # H cannot exceed 1.0
        h_adj = min(1.0, h_adj)
        result.h_adjusted = round(h_adj, 4)

        # c2. Compute effective θ with context adjustment.
        # Start from the profile/domain theta.
        if self.equation_mode == "gated":
            if self.domain and self.domain in DOMAIN_CONFIG:
                base_theta = DOMAIN_CONFIG[self.domain]["theta"]
            elif self.profile in GATED_PROFILES:
                base_theta = GATED_PROFILES[self.profile]["theta"]
            else:
                base_theta = GATED_PROFILES["default"]["theta"]
        else:
            # Classic mode has no theta parameter
            base_theta = 0.40  # placeholder, not used in classic

        # Apply theta adjustment from judgment context.
        theta_adj = ctx.theta_adjustment
        # Belt: clamp adjustment to safety bounds
        theta_adj = max(THETA_MAX_TIGHTEN, min(THETA_MAX_LOOSEN, theta_adj))

        theta_eff = base_theta + theta_adj
        # Belt: enforce theta floor
        theta_eff = max(THETA_FLOOR, theta_eff)
        # Theta cannot exceed 1.0
        theta_eff = min(1.0, theta_eff)
        theta_eff = round(theta_eff, 4)
        result.theta_effective = theta_eff

        # ── STEP d: Call compute_s() with adjusted values ──
        s_result = self._compute_s(h_adj, I, E, theta_override=theta_eff)
        result.s_result = s_result

        # ── STEP e: Record judgment to ledger ──
        self._record(
            session_id, text, msg_embedding, s_result,
            dialect, bypassed=False, theta=theta_eff,
        )

        return result

    # ───────────────────────────────────────────────────
    #  Internal: compute S equation
    # ───────────────────────────────────────────────────

    def _compute_s(
        self,
        H: float,
        I: float,
        E: float,
        theta_override: Optional[float] = None,
    ) -> dict:
        """Compute S equation with the configured mode and profile.

        Args:
            H: harm score (possibly adjusted).
            I: intent score.
            E: emotion score.
            theta_override: if provided, overrides domain/profile theta.

        Returns:
            S equation result dict.
        """
        if self.equation_mode == "gated":
            return compute_s_gated_from_scores(
                H, I, E,
                profile=self.profile,
                domain=self.domain,
                theta_override=theta_override,
            )
        else:
            return compute_s_from_scores(H, I, E, profile=self.profile)

    # ───────────────────────────────────────────────────
    #  Internal: record judgment to ledger
    # ───────────────────────────────────────────────────

    def _record(
        self,
        session_id: str,
        text: str,
        msg_embedding: Optional[np.ndarray],
        s_result: dict,
        dialect: Optional[str],
        bypassed: bool = False,
        theta: float = 0.40,
    ) -> None:
        """Record the judgment outcome in the memory ledger.

        Records the outcome regardless of whether memory was bypassed.
        The ledger is a forensic record — it records everything.

        Args:
            session_id: session/user identifier.
            text: original message text (hashed for storage).
            msg_embedding: embedding or None.
            s_result: S equation result dict.
            dialect: detected dialect.
            bypassed: whether memory was bypassed (recorded in notes).
            theta: effective theta used.
        """
        msg_hash = _hash_message(text) if text else "empty"
        scores = {
            "H": s_result.get("H", 0.0),
            "I": s_result.get("I", 0.0),
            "E": s_result.get("E", 0.0),
            "S": s_result.get("S", 0.0),
        }
        decision = s_result.get("decision", "SAFE_FREEZE")

        self.judgment_memory.record_judgment(
            session_id=session_id,
            msg_hash=msg_hash,
            msg_embedding=msg_embedding,
            scores=scores,
            decision=decision,
            dialect=dialect,
            domain_sensitivity=self.domain_sensitivity,
            theta=theta,
        )



# ═══════════════════════════════════════════════════════════
#  Factory — create_judgment_governor()
# ═══════════════════════════════════════════════════════════

def create_judgment_governor(
    db_path: str,
    domain: str = "casual",
    profile: str = "default",
    equation_mode: str = "gated",
    s_equation_domain: Optional[str] = None,
) -> JudgmentAwareGovernor:
    """Convenience factory for creating a JudgmentAwareGovernor.

    Creates a JudgmentMemory with the appropriate D from DOMAIN_PROFILES
    and returns a configured JudgmentAwareGovernor.

    Args:
        db_path: path to the SQLite database for the judgment ledger.
        domain: JudgmentMemory domain for D parameter lookup.
            One of: "casual", "education", "banking", "healthcare",
            "government". Default "casual" (D=0.2).
        profile: S equation weight profile.
        equation_mode: "gated" (default) or "classic".
        s_equation_domain: AATIF domain for theta override in S equation
            (e.g. "healthcare", "general"). Different from `domain` which
            controls the D parameter. If None, no domain theta override.

    Returns:
        Configured JudgmentAwareGovernor instance.
    """
    # Look up D from DOMAIN_PROFILES, default to casual if unknown.
    D = DOMAIN_PROFILES.get(domain, DOMAIN_PROFILES["casual"])

    # Create JudgmentMemory with the appropriate D.
    jm = JudgmentMemory(db_path, domain_sensitivity=D)

    return JudgmentAwareGovernor(
        judgment_memory=jm,
        domain_sensitivity=D,
        profile=profile,
        equation_mode=equation_mode,
        domain=s_equation_domain,
    )
