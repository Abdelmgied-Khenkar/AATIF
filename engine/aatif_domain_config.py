"""
AATIF Domain Config — هيكل المجال
==================================

Frozen dataclasses for domain configuration and gated profiles.

Phase 3 Codex improvement: consolidates scattered dict lookups into
typed, immutable, validated structures.

Design principles:
  - Frozen dataclasses: immutable after creation — no runtime tampering
  - Per-domain alpha: healthcare needs sharper gate than creative
  - Enum constants: decisions and actions are typed, not stringly-typed
  - Backward compatible: old dict-style access still works via helpers

Architecture:
  DomainConfig holds theta (harm threshold) AND alpha_override (gate
  steepness override). When alpha_override is not None, it replaces
  the profile's alpha for that domain — just like theta already
  replaces the profile's theta.

  "الدومين يقرر — θ AND α are properties of the CONTEXT."

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import Optional


# ═══════════════════════════════════════════════════════════
#  SafetyDecision — the four possible S(d) outcomes
# ═══════════════════════════════════════════════════════════

@unique
class SafetyDecision(Enum):
    """
    S(d) decision levels — from safest to most permissive.

    SAFE_FREEZE  (S ≤ 0.3)   — freeze, maximum caution
    SAFE_STOP    (0.3 < S ≤ 0.5) — stop, seek human guidance
    CLARIFY      (0.5 < S ≤ 0.7) — ask for clarification
    EXECUTE      (S > 0.7)   — safe to respond
    """
    SAFE_FREEZE = "SAFE_FREEZE"
    SAFE_STOP = "SAFE_STOP"
    CLARIFY = "CLARIFY"
    EXECUTE = "EXECUTE"

    def __str__(self) -> str:
        return self.value


# ═══════════════════════════════════════════════════════════
#  EquationMode — classic vs gated S equation
# ═══════════════════════════════════════════════════════════

@unique
class EquationMode(Enum):
    """Which S equation variant to use."""
    CLASSIC = "classic"
    GATED = "gated"

    def __str__(self) -> str:
        return self.value


# ═══════════════════════════════════════════════════════════
#  GatedProfile — frozen dataclass for gated equation profiles
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GatedProfile:
    """
    Immutable gated equation profile.

    w1:    intent weight in quality sigmoid
    w2:    emotion weight in quality sigmoid
    alpha: gate steepness (how sharply the gate closes around θ)
    theta: harm threshold (center of the gate sigmoid)
    desc:  human-readable description
    """
    w1: float
    w2: float
    alpha: float
    theta: float
    desc: str = ""

    def __post_init__(self) -> None:
        """Validate invariants at construction time."""
        if self.w1 <= 0:
            raise ValueError(f"w1 must be > 0, got {self.w1}")
        if self.w2 <= 0:
            raise ValueError(f"w2 must be > 0, got {self.w2}")
        if self.alpha <= 0:
            raise ValueError(f"alpha must be > 0, got {self.alpha}")
        if not (0 < self.theta < 1):
            raise ValueError(f"theta must be in (0,1), got {self.theta}")

    def to_dict(self) -> dict:
        """Convert to legacy dict format for backward compatibility."""
        return {
            "w1": self.w1,
            "w2": self.w2,
            "alpha": self.alpha,
            "theta": self.theta,
            "desc": self.desc,
        }


# ═══════════════════════════════════════════════════════════
#  DomainConfig — frozen dataclass for domain configuration
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DomainConfig:
    """
    Immutable domain configuration.

    theta:          harm threshold — lower = stricter (gate closes earlier)
    alpha_override: per-domain gate steepness override (None = use profile's α)
    strictness:     output gate strictness level [0.0, 1.0]
    max_length:     maximum response length in characters
    D:              domain sensitivity for judgment memory (الذكازمكان)
    desc:           human-readable description

    Per-domain alpha rationale:
      Healthcare needs a sharper gate (higher α) — the transition from
      "safe" to "blocked" should be narrow. Creative writing can use a
      gentler slope (lower α) — grey areas are acceptable.
    """
    theta: float
    alpha_override: Optional[float] = None
    strictness: float = 0.5
    max_length: int = 2000
    D: float = 0.5
    desc: str = ""

    def __post_init__(self) -> None:
        """Validate invariants at construction time."""
        if not (0 < self.theta < 1):
            raise ValueError(f"theta must be in (0,1), got {self.theta}")
        if self.alpha_override is not None and self.alpha_override <= 0:
            raise ValueError(
                f"alpha_override must be > 0 or None, got {self.alpha_override}"
            )
        if not (0.0 <= self.strictness <= 1.0):
            raise ValueError(
                f"strictness must be in [0,1], got {self.strictness}"
            )
        if self.max_length <= 0:
            raise ValueError(
                f"max_length must be > 0, got {self.max_length}"
            )
        if not (0.0 <= self.D <= 1.0):
            raise ValueError(f"D must be in [0,1], got {self.D}")

    def to_dict(self) -> dict:
        """Convert to legacy dict format for backward compatibility."""
        d = {"theta": self.theta, "desc": self.desc}
        if self.alpha_override is not None:
            d["alpha_override"] = self.alpha_override
        return d


# ═══════════════════════════════════════════════════════════
#  Canonical domain configs — frozen instances
# ═══════════════════════════════════════════════════════════
#
# θ determines where the harm gate closes.
# α_override (when set) overrides the profile's α for this domain.
#
# Design session 2026-06-22: "θ varies by domain, not by time"
# Phase 3: α also varies by domain — healthcare needs sharper gate

DOMAIN_CONFIGS = {
    "healthcare": DomainConfig(
        theta=0.25,
        alpha_override=15,
        strictness=1.0,
        max_length=2000,
        D=0.90,
        desc="Medical/health context — gate closes early, harm is physical",
    ),
    "education": DomainConfig(
        theta=0.30,
        alpha_override=12,
        strictness=0.8,
        max_length=2500,
        D=0.40,
        desc="Children/students — gate closes early, harm is developmental",
    ),
    "general": DomainConfig(
        theta=0.40,
        alpha_override=None,  # uses profile alpha
        strictness=0.5,
        max_length=2000,
        D=0.20,
        desc="Default — balanced gate (same as calibrated default profile)",
    ),
    "tech": DomainConfig(
        theta=0.40,
        alpha_override=None,
        strictness=0.5,
        max_length=3000,
        D=0.20,
        desc="Technical support — same as general",
    ),
    "ecommerce": DomainConfig(
        theta=0.40,
        alpha_override=None,
        strictness=0.5,
        max_length=2000,
        D=0.20,
        desc="Commercial/shopping — same as general",
    ),
    "creative": DomainConfig(
        theta=0.50,
        alpha_override=8,
        strictness=0.3,
        max_length=4000,
        D=0.20,
        desc="Creative writing/art — wider tolerance for sensitive topics",
    ),
}


# ═══════════════════════════════════════════════════════════
#  Canonical gated profiles — frozen instances
# ═══════════════════════════════════════════════════════════

GATED_PROFILE_CONFIGS = {
    "default": GatedProfile(
        w1=2.0, w2=1.5, alpha=10, theta=0.40,
        desc="Balanced gate — moderate steepness, gate center at H=0.40 "
             "(calibrated 2026-06-19)",
    ),
    "high_sensitivity": GatedProfile(
        w1=2.0, w2=1.0, alpha=15, theta=0.30,
        desc="Conservative gate — triggers earlier (θ=0.30), sharper cutoff",
    ),
    "relaxed": GatedProfile(
        w1=3.0, w2=2.5, alpha=8, theta=0.55,
        desc="Permissive gate — intent-driven, wider tolerance",
    ),
    "balanced_strict": GatedProfile(
        w1=2.0, w2=1.5, alpha=10, theta=0.40,
        desc="Calibrated via A/B test (2026-06-19) — identical to default, "
             "kept as named reference",
    ),
}


# ═══════════════════════════════════════════════════════════
#  Accessor helpers — backward-compatible with dict API
# ═══════════════════════════════════════════════════════════

def get_domain_config(domain: str) -> DomainConfig:
    """
    Return the DomainConfig for a domain.

    Raises ValueError if domain is unknown — typos are safety-critical.
    """
    cfg = DOMAIN_CONFIGS.get(domain)
    if cfg is None:
        valid = ", ".join(sorted(DOMAIN_CONFIGS.keys()))
        raise ValueError(
            f"Unknown domain '{domain}'. Valid domains: {valid}"
        )
    return cfg


def get_domain_alpha(domain: str | None, profile_alpha: float) -> float:
    """
    Return the effective α for a domain.

    If the domain has an alpha_override, use it.
    Otherwise, use the profile's alpha.

    This mirrors how get_domain_theta works: domain overrides profile.
    """
    if domain is None:
        return profile_alpha
    cfg = get_domain_config(domain)
    if cfg.alpha_override is not None:
        return cfg.alpha_override
    return profile_alpha


def get_gated_profile(name: str) -> GatedProfile:
    """
    Return a GatedProfile by name.

    Raises KeyError if profile name is unknown.
    """
    if name not in GATED_PROFILE_CONFIGS:
        valid = ", ".join(sorted(GATED_PROFILE_CONFIGS.keys()))
        raise KeyError(
            f"Unknown gated profile '{name}'. Valid profiles: {valid}"
        )
    return GATED_PROFILE_CONFIGS[name]
