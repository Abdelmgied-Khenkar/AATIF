"""
AATIF DomainConfig — Phase 3 Frozen Dataclass Tests
====================================================

Tests for the Phase 3 Codex improvements:
  1. DomainConfig frozen dataclass — immutable domain configuration
  2. GatedProfile frozen dataclass — immutable gated equation profiles
  3. SafetyDecision + EquationMode enums — typed constants
  4. Per-domain alpha — domain overrides gate steepness
  5. Backward compatibility — old dict-style access still works

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

import sys
import os
import pytest

# Ensure engine directory is importable
_ENGINE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_domain_config import (
    DomainConfig,
    GatedProfile,
    SafetyDecision,
    EquationMode,
    DOMAIN_CONFIGS,
    GATED_PROFILE_CONFIGS,
    get_domain_config,
    get_domain_alpha,
    get_gated_profile,
)
from aatif_s_equation import (
    DOMAIN_CONFIG,
    GATED_PROFILES,
    compute_s_gated_from_scores,
    get_domain_theta,
)


# ═══════════════════════════════════════════════════════════════
# 1. DomainConfig frozen dataclass
# ═══════════════════════════════════════════════════════════════

class TestDomainConfigDataclass:
    """Verify DomainConfig is properly frozen and validated."""

    def test_frozen_cannot_mutate_theta(self):
        """DomainConfig is frozen — cannot change theta at runtime."""
        dc = DomainConfig(theta=0.40, desc="test")
        with pytest.raises(AttributeError):
            dc.theta = 0.99

    def test_frozen_cannot_mutate_alpha(self):
        dc = DomainConfig(theta=0.40, alpha_override=10, desc="test")
        with pytest.raises(AttributeError):
            dc.alpha_override = 99

    def test_validation_theta_out_of_range(self):
        """theta must be in (0, 1)."""
        with pytest.raises(ValueError, match="theta must be in"):
            DomainConfig(theta=0.0)
        with pytest.raises(ValueError, match="theta must be in"):
            DomainConfig(theta=1.0)
        with pytest.raises(ValueError, match="theta must be in"):
            DomainConfig(theta=-0.1)

    def test_validation_alpha_must_be_positive(self):
        """alpha_override must be > 0 or None."""
        with pytest.raises(ValueError, match="alpha_override must be"):
            DomainConfig(theta=0.40, alpha_override=0)
        with pytest.raises(ValueError, match="alpha_override must be"):
            DomainConfig(theta=0.40, alpha_override=-5)

    def test_validation_strictness_range(self):
        with pytest.raises(ValueError, match="strictness must be in"):
            DomainConfig(theta=0.40, strictness=1.5)

    def test_validation_max_length_positive(self):
        with pytest.raises(ValueError, match="max_length must be"):
            DomainConfig(theta=0.40, max_length=0)

    def test_validation_D_range(self):
        with pytest.raises(ValueError, match="D must be in"):
            DomainConfig(theta=0.40, D=1.5)

    def test_alpha_override_none_is_valid(self):
        """None alpha_override means 'use profile alpha'."""
        dc = DomainConfig(theta=0.40, alpha_override=None)
        assert dc.alpha_override is None

    def test_to_dict_roundtrip(self):
        """to_dict produces the legacy dict format."""
        dc = DomainConfig(theta=0.25, desc="test domain")
        d = dc.to_dict()
        assert d["theta"] == 0.25
        assert d["desc"] == "test domain"
        assert "alpha_override" not in d  # None is omitted

    def test_to_dict_includes_alpha_when_set(self):
        dc = DomainConfig(theta=0.25, alpha_override=15)
        d = dc.to_dict()
        assert d["alpha_override"] == 15


# ═══════════════════════════════════════════════════════════════
# 2. GatedProfile frozen dataclass
# ═══════════════════════════════════════════════════════════════

class TestGatedProfileDataclass:
    """Verify GatedProfile is properly frozen and validated."""

    def test_frozen_cannot_mutate(self):
        gp = GatedProfile(w1=2.0, w2=1.5, alpha=10, theta=0.40)
        with pytest.raises(AttributeError):
            gp.alpha = 99

    def test_validation_w1_positive(self):
        with pytest.raises(ValueError, match="w1 must be"):
            GatedProfile(w1=0, w2=1.5, alpha=10, theta=0.40)

    def test_validation_w2_positive(self):
        with pytest.raises(ValueError, match="w2 must be"):
            GatedProfile(w1=2.0, w2=-1, alpha=10, theta=0.40)

    def test_validation_alpha_positive(self):
        with pytest.raises(ValueError, match="alpha must be"):
            GatedProfile(w1=2.0, w2=1.5, alpha=0, theta=0.40)

    def test_validation_theta_range(self):
        with pytest.raises(ValueError, match="theta must be in"):
            GatedProfile(w1=2.0, w2=1.5, alpha=10, theta=0.0)

    def test_to_dict_roundtrip(self):
        gp = GatedProfile(w1=2.0, w2=1.5, alpha=10, theta=0.40, desc="test")
        d = gp.to_dict()
        assert d["w1"] == 2.0
        assert d["w2"] == 1.5
        assert d["alpha"] == 10
        assert d["theta"] == 0.40
        assert d["desc"] == "test"


# ═══════════════════════════════════════════════════════════════
# 3. Enum constants
# ═══════════════════════════════════════════════════════════════

class TestEnums:
    """Verify SafetyDecision and EquationMode enums."""

    def test_safety_decision_values(self):
        assert SafetyDecision.SAFE_FREEZE.value == "SAFE_FREEZE"
        assert SafetyDecision.SAFE_STOP.value == "SAFE_STOP"
        assert SafetyDecision.CLARIFY.value == "CLARIFY"
        assert SafetyDecision.EXECUTE.value == "EXECUTE"

    def test_safety_decision_str(self):
        """str() returns the value for backward compat with string comparisons."""
        assert str(SafetyDecision.EXECUTE) == "EXECUTE"
        assert str(SafetyDecision.SAFE_FREEZE) == "SAFE_FREEZE"

    def test_equation_mode_values(self):
        assert EquationMode.CLASSIC.value == "classic"
        assert EquationMode.GATED.value == "gated"

    def test_safety_decision_is_unique(self):
        """All values must be unique (enforced by @unique)."""
        values = [d.value for d in SafetyDecision]
        assert len(values) == len(set(values))


# ═══════════════════════════════════════════════════════════════
# 4. DOMAIN_CONFIGS — canonical frozen instances
# ═══════════════════════════════════════════════════════════════

class TestDomainConfigs:
    """Verify canonical DOMAIN_CONFIGS match design spec."""

    def test_all_six_domains_present(self):
        expected = {"healthcare", "education", "general", "tech",
                    "ecommerce", "creative"}
        assert set(DOMAIN_CONFIGS.keys()) == expected

    def test_all_frozen(self):
        for name, dc in DOMAIN_CONFIGS.items():
            assert isinstance(dc, DomainConfig), f"{name} is not DomainConfig"
            with pytest.raises(AttributeError):
                dc.theta = 0.99

    def test_healthcare_config(self):
        dc = DOMAIN_CONFIGS["healthcare"]
        assert dc.theta == 0.25
        assert dc.alpha_override == 15
        assert dc.strictness == 1.0
        assert dc.D == 0.90

    def test_education_config(self):
        dc = DOMAIN_CONFIGS["education"]
        assert dc.theta == 0.30
        assert dc.alpha_override == 12

    def test_general_config(self):
        dc = DOMAIN_CONFIGS["general"]
        assert dc.theta == 0.40
        assert dc.alpha_override is None  # uses profile alpha

    def test_creative_config(self):
        dc = DOMAIN_CONFIGS["creative"]
        assert dc.theta == 0.50
        assert dc.alpha_override == 8
        assert dc.strictness == 0.3

    def test_theta_ordering(self):
        """healthcare ≤ education ≤ general ≤ creative (stricter → looser)."""
        assert DOMAIN_CONFIGS["healthcare"].theta <= DOMAIN_CONFIGS["education"].theta
        assert DOMAIN_CONFIGS["education"].theta <= DOMAIN_CONFIGS["general"].theta
        assert DOMAIN_CONFIGS["general"].theta <= DOMAIN_CONFIGS["creative"].theta


# ═══════════════════════════════════════════════════════════════
# 5. GATED_PROFILE_CONFIGS — canonical frozen instances
# ═══════════════════════════════════════════════════════════════

class TestGatedProfileConfigs:
    """Verify canonical GATED_PROFILE_CONFIGS."""

    def test_all_profiles_present(self):
        expected = {"default", "high_sensitivity", "relaxed", "balanced_strict"}
        assert set(GATED_PROFILE_CONFIGS.keys()) == expected

    def test_all_frozen(self):
        for name, gp in GATED_PROFILE_CONFIGS.items():
            assert isinstance(gp, GatedProfile), f"{name} is not GatedProfile"

    def test_default_profile(self):
        gp = GATED_PROFILE_CONFIGS["default"]
        assert gp.w1 == 2.0
        assert gp.w2 == 1.5
        assert gp.alpha == 10
        assert gp.theta == 0.40

    def test_theta_ordering(self):
        """high_sensitivity ≤ default ≤ relaxed."""
        hs = GATED_PROFILE_CONFIGS["high_sensitivity"].theta
        df = GATED_PROFILE_CONFIGS["default"].theta
        rx = GATED_PROFILE_CONFIGS["relaxed"].theta
        assert hs <= df <= rx


# ═══════════════════════════════════════════════════════════════
# 6. Accessor functions
# ═══════════════════════════════════════════════════════════════

class TestAccessors:
    """Verify get_domain_config, get_domain_alpha, get_gated_profile."""

    def test_get_domain_config_valid(self):
        dc = get_domain_config("healthcare")
        assert dc.theta == 0.25
        assert isinstance(dc, DomainConfig)

    def test_get_domain_config_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown domain"):
            get_domain_config("nonexistent")

    def test_get_domain_alpha_with_override(self):
        """Healthcare has alpha_override=15 — should override profile's alpha."""
        alpha = get_domain_alpha("healthcare", profile_alpha=10)
        assert alpha == 15

    def test_get_domain_alpha_without_override(self):
        """General has no alpha_override — should use profile's alpha."""
        alpha = get_domain_alpha("general", profile_alpha=10)
        assert alpha == 10

    def test_get_domain_alpha_none_domain(self):
        """None domain — always use profile alpha."""
        alpha = get_domain_alpha(None, profile_alpha=10)
        assert alpha == 10

    def test_get_gated_profile_valid(self):
        gp = get_gated_profile("default")
        assert isinstance(gp, GatedProfile)
        assert gp.alpha == 10

    def test_get_gated_profile_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown gated profile"):
            get_gated_profile("nonexistent")


# ═══════════════════════════════════════════════════════════════
# 7. Backward compatibility — old dict-style DOMAIN_CONFIG
# ═══════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """Old code that does DOMAIN_CONFIG['healthcare']['theta'] must still work."""

    def test_domain_config_dict_has_theta(self):
        assert DOMAIN_CONFIG["healthcare"]["theta"] == 0.25
        assert DOMAIN_CONFIG["general"]["theta"] == 0.40
        assert DOMAIN_CONFIG["creative"]["theta"] == 0.50

    def test_gated_profiles_dict_has_alpha(self):
        assert GATED_PROFILES["default"]["alpha"] == 10
        assert GATED_PROFILES["high_sensitivity"]["alpha"] == 15

    def test_get_domain_theta_still_works(self):
        """get_domain_theta from aatif_s_equation still works."""
        assert get_domain_theta("healthcare") == 0.25
        assert get_domain_theta(None) is None

    def test_domain_config_keys_match(self):
        """Dict keys match frozen config keys."""
        assert set(DOMAIN_CONFIG.keys()) == set(DOMAIN_CONFIGS.keys())

    def test_gated_profiles_keys_match(self):
        assert set(GATED_PROFILES.keys()) == set(GATED_PROFILE_CONFIGS.keys())


# ═══════════════════════════════════════════════════════════════
# 8. Per-domain alpha in the S equation
# ═══════════════════════════════════════════════════════════════

class TestPerDomainAlpha:
    """
    Phase 3: per-domain alpha — domain overrides gate steepness.

    Healthcare (α=15) produces sharper gate than creative (α=8).
    At the same H, the sharper gate drops more aggressively.
    """

    H = 0.35
    I = 0.7
    E = 0.6

    def test_healthcare_uses_domain_alpha(self):
        """Healthcare should use alpha=15 (from domain), not profile default 10."""
        r = compute_s_gated_from_scores(self.H, self.I, self.E,
                                         profile="default", domain="healthcare")
        assert r["alpha_effective"] == 15
        assert r["alpha_source"] == "domain"

    def test_general_uses_profile_alpha(self):
        """General has no alpha_override — uses profile alpha."""
        r = compute_s_gated_from_scores(self.H, self.I, self.E,
                                         profile="default", domain="general")
        assert r["alpha_effective"] == 10
        assert r["alpha_source"] == "profile"

    def test_creative_uses_domain_alpha(self):
        """Creative should use alpha=8 (from domain)."""
        r = compute_s_gated_from_scores(self.H, self.I, self.E,
                                         profile="default", domain="creative")
        assert r["alpha_effective"] == 8
        assert r["alpha_source"] == "domain"

    def test_no_domain_uses_profile_alpha(self):
        """No domain → profile alpha."""
        r = compute_s_gated_from_scores(self.H, self.I, self.E,
                                         profile="default", domain=None)
        assert r["alpha_effective"] == 10
        assert r["alpha_source"] == "profile"

    def test_sharper_alpha_blocks_more(self):
        """
        At the same H, higher alpha (sharper gate) produces lower S.
        Healthcare (α=15, θ=0.25) vs creative (α=8, θ=0.50) at H=0.35.
        """
        r_health = compute_s_gated_from_scores(self.H, self.I, self.E,
                                                domain="healthcare")
        r_creative = compute_s_gated_from_scores(self.H, self.I, self.E,
                                                  domain="creative")
        # Healthcare: H=0.35 > θ=0.25 with sharp α=15 → gate closes hard
        # Creative:  H=0.35 < θ=0.50 with gentle α=8 → gate stays open
        assert r_health["S"] < r_creative["S"]

    def test_education_uses_domain_alpha(self):
        """Education should use alpha=12 (from domain)."""
        r = compute_s_gated_from_scores(self.H, self.I, self.E,
                                         profile="default", domain="education")
        assert r["alpha_effective"] == 12
        assert r["alpha_source"] == "domain"
