"""
AATIF θ(d) — Domain-Parameterized Harm Threshold Tests
=======================================================

Tests for the domain-parameterized θ feature added 2026-06-22.

Core principle: "الاذي مالوش توقيت" refined —
    TIME doesn't change θ. DOMAIN does.
    Healthcare harm is more dangerous than e-commerce harm.

Design:
    θ("healthcare")  = 0.25  — gate closes early
    θ("education")   = 0.30  — gate closes early
    θ("general")     = 0.40  — default calibrated value
    θ("tech")        = 0.40  — same as general
    θ("ecommerce")   = 0.40  — same as general
    θ("creative")    = 0.50  — wider tolerance

Hard override: H > 0.7 → SAFE_FREEZE regardless of domain.

Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

import sys
import os
import pytest

# Ensure engine directory is importable
_ENGINE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_s_equation import (
    compute_s_gated_from_scores,
    get_domain_theta,
    DOMAIN_CONFIG,
    H_GATED_HARD_OVERRIDE,
    sigmoid,
    AATIFEngine,
)


# ═══════════════════════════════════════════════════════════════
# Test 1: Domain theta values are correct
# ═══════════════════════════════════════════════════════════════

class TestDomainConfig:
    """Verify DOMAIN_CONFIG has correct θ values."""

    def test_healthcare_theta(self):
        assert DOMAIN_CONFIG["healthcare"]["theta"] == 0.25

    def test_education_theta(self):
        assert DOMAIN_CONFIG["education"]["theta"] == 0.30

    def test_general_theta(self):
        assert DOMAIN_CONFIG["general"]["theta"] == 0.40

    def test_tech_theta(self):
        assert DOMAIN_CONFIG["tech"]["theta"] == 0.40

    def test_ecommerce_theta(self):
        assert DOMAIN_CONFIG["ecommerce"]["theta"] == 0.40

    def test_creative_theta(self):
        assert DOMAIN_CONFIG["creative"]["theta"] == 0.50

    def test_get_domain_theta_returns_value(self):
        assert get_domain_theta("healthcare") == 0.25
        assert get_domain_theta("education") == 0.30
        assert get_domain_theta("general") == 0.40

    def test_get_domain_theta_none_returns_none(self):
        assert get_domain_theta(None) is None

    def test_get_domain_theta_unknown_raises_error(self):
        """Unknown domain must raise ValueError — typos are safety-critical."""
        with pytest.raises(ValueError, match="Unknown domain"):
            get_domain_theta("unknown_domain")

    def test_get_domain_theta_typo_raises_error(self):
        """Typo 'heathcare' must not silently fall back to profile θ."""
        with pytest.raises(ValueError, match="Unknown domain"):
            get_domain_theta("heathcare")


# ═══════════════════════════════════════════════════════════════
# Test 2: Domain overrides profile theta
# ═══════════════════════════════════════════════════════════════

class TestDomainOverridesProfile:
    """When domain is specified, θ comes from domain, not profile."""

    # Fixed test scores: moderate harm, good intent, positive emotion
    H = 0.35
    I = 0.7
    E = 0.6

    def test_no_domain_uses_profile_theta(self):
        """Without domain, profile theta is used (default = 0.40)."""
        r = compute_s_gated_from_scores(self.H, self.I, self.E,
                                         profile="default", domain=None)
        assert r["theta_source"] == "profile"
        assert r["theta_effective"] == 0.40
        assert r["domain"] is None

    def test_healthcare_domain_overrides(self):
        """Healthcare domain uses θ=0.25, not profile's θ=0.40."""
        r = compute_s_gated_from_scores(self.H, self.I, self.E,
                                         profile="default", domain="healthcare")
        assert r["theta_source"] == "domain"
        assert r["theta_effective"] == 0.25
        assert r["domain"] == "healthcare"

    def test_education_domain_overrides(self):
        """Education domain uses θ=0.30."""
        r = compute_s_gated_from_scores(self.H, self.I, self.E,
                                         profile="default", domain="education")
        assert r["theta_source"] == "domain"
        assert r["theta_effective"] == 0.30

    def test_general_domain_same_as_default_profile(self):
        """General domain θ=0.40 matches default profile θ=0.40."""
        r_domain = compute_s_gated_from_scores(self.H, self.I, self.E,
                                                profile="default", domain="general")
        r_no_domain = compute_s_gated_from_scores(self.H, self.I, self.E,
                                                   profile="default", domain=None)
        assert r_domain["S"] == r_no_domain["S"]
        assert r_domain["decision"] == r_no_domain["decision"]

    def test_unknown_domain_raises_error(self):
        """Unknown domain must raise ValueError, not silently fall back."""
        with pytest.raises(ValueError, match="Unknown domain"):
            compute_s_gated_from_scores(self.H, self.I, self.E,
                                         profile="default", domain="unknown_xyz")


# ═══════════════════════════════════════════════════════════════
# Test 3: Healthcare is stricter than general
# ═══════════════════════════════════════════════════════════════

class TestHealthcareStricter:
    """Healthcare domain (θ=0.25) blocks more than general (θ=0.40)."""

    def test_moderate_harm_blocked_in_healthcare_not_general(self):
        """
        H=0.35 with good intent: general says EXECUTE, healthcare may block.

        With θ=0.40: H=0.35 is BELOW threshold → gate mostly open
        With θ=0.25: H=0.35 is ABOVE threshold → gate closes
        """
        H, I, E = 0.35, 0.8, 0.7

        r_general = compute_s_gated_from_scores(H, I, E,
                                                 domain="general")
        r_health = compute_s_gated_from_scores(H, I, E,
                                                domain="healthcare")

        # Healthcare S should be LOWER (gate closes more)
        assert r_health["S"] < r_general["S"], \
            f"Healthcare S={r_health['S']} should be < general S={r_general['S']}"

        # Healthcare gate should be more closed
        assert r_health["gate"] < r_general["gate"], \
            f"Healthcare gate={r_health['gate']} should be < general gate={r_general['gate']}"

    def test_domain_ordering_at_moderate_harm(self):
        """
        At H=0.35: S(healthcare) < S(education) < S(general) < S(creative)
        Because θ ordering: 0.25 < 0.30 < 0.40 < 0.50
        Lower θ → gate closes earlier → lower S.
        """
        H, I, E = 0.35, 0.8, 0.7

        s_health = compute_s_gated_from_scores(H, I, E, domain="healthcare")["S"]
        s_edu = compute_s_gated_from_scores(H, I, E, domain="education")["S"]
        s_gen = compute_s_gated_from_scores(H, I, E, domain="general")["S"]
        s_cre = compute_s_gated_from_scores(H, I, E, domain="creative")["S"]

        assert s_health < s_edu < s_gen < s_cre, \
            f"Expected ordering: {s_health:.4f} < {s_edu:.4f} < {s_gen:.4f} < {s_cre:.4f}"


# ═══════════════════════════════════════════════════════════════
# Test 4: Hard override ignores domain
# ═══════════════════════════════════════════════════════════════

class TestHardOverrideIgnoresDomain:
    """H > 0.7 → SAFE_FREEZE regardless of domain. Always. No exception."""

    @pytest.mark.parametrize("domain", [
        "healthcare", "education", "general", "tech", "ecommerce", "creative", None
    ])
    def test_hard_override_all_domains(self, domain):
        """H=0.85 → SAFE_FREEZE in every domain."""
        r = compute_s_gated_from_scores(0.85, 0.9, 0.9, domain=domain)
        assert r["decision"] == "SAFE_FREEZE"
        assert r["hard_override"] is True


# ═══════════════════════════════════════════════════════════════
# Test 5: Low harm — domain doesn't matter
# ═══════════════════════════════════════════════════════════════

class TestLowHarmDomainIrrelevant:
    """When H is very low, all domains produce similar results."""

    def test_benign_request_all_domains_execute(self):
        """H=0.05 with strong intent → EXECUTE everywhere."""
        H, I, E = 0.05, 0.9, 0.8

        for domain in ["healthcare", "education", "general", "creative"]:
            r = compute_s_gated_from_scores(H, I, E, domain=domain)
            assert r["decision"] == "EXECUTE", \
                f"Domain {domain}: expected EXECUTE, got {r['decision']} (S={r['S']})"


# ═══════════════════════════════════════════════════════════════
# Test 6: Result dict contains domain metadata
# ═══════════════════════════════════════════════════════════════

class TestResultMetadata:
    """Verify the result dict carries domain information."""

    def test_domain_in_result(self):
        r = compute_s_gated_from_scores(0.3, 0.7, 0.6, domain="healthcare")
        assert "domain" in r
        assert r["domain"] == "healthcare"
        assert "theta_effective" in r
        assert r["theta_effective"] == 0.25
        assert "theta_source" in r
        assert r["theta_source"] == "domain"

    def test_no_domain_in_result(self):
        r = compute_s_gated_from_scores(0.3, 0.7, 0.6, domain=None)
        assert r["domain"] is None
        assert r["theta_source"] == "profile"

    def test_hard_override_has_domain_metadata(self):
        """Even hard override results carry domain info."""
        r = compute_s_gated_from_scores(0.85, 0.9, 0.9, domain="education")
        assert r["domain"] == "education"
        assert r["theta_effective"] == 0.30
        assert r["hard_override"] is True


# ═══════════════════════════════════════════════════════════════
# Test 7: Mathematical verification
# ═══════════════════════════════════════════════════════════════

class TestMathVerification:
    """Verify the gate math with domain theta matches hand calculations."""

    def test_gate_value_healthcare(self):
        """Manually verify gate = 1 - σ(α·(H - θ)) with healthcare θ and per-domain α."""
        H, alpha, theta = 0.35, 15, 0.25  # healthcare (Phase 3: α=15 per-domain)
        expected_gate = 1.0 - sigmoid(alpha * (H - theta))

        r = compute_s_gated_from_scores(H, 0.7, 0.6, domain="healthcare")
        assert abs(r["gate"] - round(expected_gate, 4)) < 0.0001

    def test_gate_value_general(self):
        """Manually verify gate with general θ."""
        H, alpha, theta = 0.35, 10, 0.40  # general
        expected_gate = 1.0 - sigmoid(alpha * (H - theta))

        r = compute_s_gated_from_scores(H, 0.7, 0.6, domain="general")
        assert abs(r["gate"] - round(expected_gate, 4)) < 0.0001

    def test_healthcare_gate_much_lower_at_h035(self):
        """
        At H=0.35 (Phase 3: per-domain alpha):
          healthcare: gate = 1 - σ(15·(0.35 - 0.25)) = 1 - σ(1.5) ≈ 0.182
          general:    gate = 1 - σ(10·(0.35 - 0.40)) = 1 - σ(-0.5) ≈ 0.622

        Healthcare gate is ~0.18, general gate is ~0.62.
        That's an even larger difference with per-domain α — healthcare is 3.4× more restrictive.
        """
        H = 0.35
        gate_health = 1.0 - sigmoid(15 * (H - 0.25))   # α=15 per-domain
        gate_general = 1.0 - sigmoid(10 * (H - 0.40))   # α=10 (profile default)

        assert gate_health < 0.30, f"Healthcare gate should be < 0.30, got {gate_health:.4f}"
        assert gate_general > 0.60, f"General gate should be > 0.60, got {gate_general:.4f}"
        assert gate_health < gate_general


# ═══════════════════════════════════════════════════════════════
# Test 8: Backward compatibility
# ═══════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """Existing code that doesn't pass domain should work exactly as before."""

    def test_no_domain_no_change(self):
        """compute_s_gated_from_scores without domain = same as old behavior."""
        H, I, E = 0.40, 0.7, 0.6

        # Old way (no domain parameter)
        r = compute_s_gated_from_scores(H, I, E, profile="default")

        # Verify it uses profile theta (0.40)
        assert r["theta_effective"] == 0.40
        assert r["theta_source"] == "profile"

        # At H=θ=0.40: gate = 1 - σ(0) = 0.5
        assert abs(r["gate"] - 0.5) < 0.001

    def test_all_existing_profiles_still_work(self):
        """All gated profiles work without domain."""
        for profile in ["default", "high_sensitivity", "relaxed", "balanced_strict"]:
            r = compute_s_gated_from_scores(0.3, 0.7, 0.6, profile=profile)
            assert "decision" in r
            assert "S" in r


# ═══════════════════════════════════════════════════════════════
# Test 9: Fail-loud hardening — the unknown-domain guard must hold
#         under every adversarial spelling AND under hard override.
#         (Added 2026-06-22 by Agent حسّاب — locks the governance
#          guarantee that a typo'd domain can never silently change
#          the safety threshold, even when H is in the freeze band.)
# ═══════════════════════════════════════════════════════════════

class TestUnknownDomainFailsLoud:
    """A non-None domain not in DOMAIN_CONFIG must ALWAYS raise ValueError."""

    @pytest.mark.parametrize("bad_domain", [
        "",               # empty string is not None → must raise, not fall back
        "Healthcare",     # wrong case
        "HEALTHCARE",     # wrong case
        " healthcare",    # leading whitespace
        "healthcare ",    # trailing whitespace
        "heathcare",      # typo
        "medical",        # plausible synonym that is NOT configured
        "health-care",    # hyphenated variant
    ])
    def test_invalid_domain_raises(self, bad_domain):
        with pytest.raises(ValueError, match="Unknown domain"):
            get_domain_theta(bad_domain)

    @pytest.mark.parametrize("bad_domain", ["", "Healthcare", "heathcare", "medical"])
    def test_invalid_domain_raises_in_compute(self, bad_domain):
        """Same guard must fire through compute_s_gated_from_scores."""
        with pytest.raises(ValueError, match="Unknown domain"):
            compute_s_gated_from_scores(0.30, 0.7, 0.6, domain=bad_domain)

    @pytest.mark.parametrize("bad_domain", ["heathcare", "Healthcare", "", "medical"])
    def test_invalid_domain_not_masked_by_hard_override(self, bad_domain):
        """
        SAFETY-CRITICAL: when H is in the hard-override band (H > 0.7),
        an invalid domain must STILL raise — the SAFE_FREEZE path must
        not swallow a configuration typo. Fail loud beats fail safe-looking.
        """
        assert 0.85 > H_GATED_HARD_OVERRIDE  # sanity: 0.85 is in freeze band
        with pytest.raises(ValueError, match="Unknown domain"):
            compute_s_gated_from_scores(0.85, 0.9, 0.9, domain=bad_domain)

    def test_error_message_lists_valid_domains(self):
        """The failure must be actionable — it names the valid domains."""
        with pytest.raises(ValueError) as exc:
            get_domain_theta("medical")
        msg = str(exc.value)
        for d in DOMAIN_CONFIG:
            assert d in msg, f"valid domain {d!r} missing from error message"


# ═══════════════════════════════════════════════════════════════
# Test 10: DOMAIN_CONFIG structural invariants
#          (Every domain must carry a usable θ in [0,1] and a desc;
#           the design ordering must hold at the config level so a
#           future edit to θ values can't silently invert sensitivity.)
# ═══════════════════════════════════════════════════════════════

class TestDomainConfigInvariants:
    """Structural guarantees about DOMAIN_CONFIG itself."""

    @pytest.mark.parametrize("domain", list(DOMAIN_CONFIG.keys()))
    def test_theta_is_float_in_unit_interval(self, domain):
        theta = DOMAIN_CONFIG[domain]["theta"]
        assert isinstance(theta, float)
        assert 0.0 <= theta <= 1.0

    @pytest.mark.parametrize("domain", list(DOMAIN_CONFIG.keys()))
    def test_theta_below_hard_override(self, domain):
        """No domain θ may sit at/above the absolute freeze line."""
        assert DOMAIN_CONFIG[domain]["theta"] < H_GATED_HARD_OVERRIDE

    @pytest.mark.parametrize("domain", list(DOMAIN_CONFIG.keys()))
    def test_every_domain_has_nonempty_desc(self, domain):
        desc = DOMAIN_CONFIG[domain].get("desc", "")
        assert isinstance(desc, str) and desc.strip()

    def test_sensitivity_ordering_holds(self):
        """
        Design intent: stricter (lower θ) → more permissive (higher θ).
        healthcare ≤ education ≤ general = tech = ecommerce ≤ creative.
        Locking this prevents an accidental inversion of safety posture.
        """
        cfg = DOMAIN_CONFIG
        assert cfg["healthcare"]["theta"] <= cfg["education"]["theta"]
        assert cfg["education"]["theta"] <= cfg["general"]["theta"]
        assert cfg["general"]["theta"] == cfg["tech"]["theta"] == cfg["ecommerce"]["theta"]
        assert cfg["general"]["theta"] <= cfg["creative"]["theta"]


# ═══════════════════════════════════════════════════════════════
# Test: M1 — domain is rejected (not silently ignored) in classic mode
# ═══════════════════════════════════════════════════════════════
#
# Codex review 2026-06-22 (M1): compute() accepted `domain` in both
# equation modes, but the classic equation S = σ(w₁·I + w₂·E − w₃·H)
# has no θ parameter for domain to override. Passing domain in classic
# mode silently dropped it — the same "silent fallback" failure mode that
# get_domain_theta() guards against for unknown domains. The fix raises
# ValueError. These tests bypass __init__ (AATIFEngine.__new__) because
# the guard fires before any scorer is constructed, so they run without
# the bge-m3 / Ollama backend.

class TestDomainRejectedInClassicMode:
    """domain in classic mode must fail loudly, not be silently ignored."""

    def _bare_engine(self):
        # Bypass __init__ — the M1 guard runs before scorers are touched.
        return AATIFEngine.__new__(AATIFEngine)

    def test_classic_with_known_domain_raises(self):
        eng = self._bare_engine()
        with pytest.raises(ValueError, match="only supported in gated mode"):
            eng.compute("مرحبا", equation_mode="classic", domain="healthcare")

    def test_classic_with_unknown_domain_raises(self):
        """Even a typo'd domain must be rejected in classic mode."""
        eng = self._bare_engine()
        with pytest.raises(ValueError, match="only supported in gated mode"):
            eng.compute("مرحبا", equation_mode="classic", domain="banana")

    @pytest.mark.parametrize("domain", list(DOMAIN_CONFIG.keys()))
    def test_classic_rejects_every_valid_domain(self, domain):
        eng = self._bare_engine()
        with pytest.raises(ValueError):
            eng.compute("مرحبا", equation_mode="classic", domain=domain)

    def test_classic_default_domain_none_does_not_raise_on_guard(self):
        """domain=None in classic mode must pass the M1 guard (no ValueError
        from the guard itself). We stop before scorers by patching them out."""
        eng = self._bare_engine()

        class _StubScorer:
            def score(self, text):
                return {"H": 0.0, "I": 0.0, "E": 0.0,
                        "confidence": "high", "max_similarity": 0.9}

        eng.h_scorer = _StubScorer()
        eng.i_scorer = _StubScorer()
        eng.e_scorer = _StubScorer()
        from aatif_hysteresis import HysteresisController
        eng.hysteresis = HysteresisController()
        # Should not raise — domain is None, classic mode is valid.
        result = eng.compute("مرحبا", equation_mode="classic")
        assert result["equation_mode"] == "classic"
        assert result["domain"] is None if "domain" in result else True
