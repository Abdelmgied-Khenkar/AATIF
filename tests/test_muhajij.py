#!/usr/bin/env python3
"""
test_muhajij.py — المُحاجج (FN#026 + FN#060)
==============================================
Covers ``engine/aatif_muhajij.py`` — the Anticipatory Logic + Audience-Adapted
Justification module that combines:
  FN#026 (Anticipatory Logic Protocol / ULP) — multiple response paths,
          frame elevation when user argues
  FN#060 (Universal Debate & Justification Engine / UDJE) — same truth
          presented through 5 audience channels

This module is PURE LOGIC (no embeddings, no LLM), so every test runs
WITHOUT Ollama.  Two layers:

  1. Unit tests on AlMuhajij.justify — driving the engine with controlled
     inputs and pinning: decision type handling, audience channels,
     alternative paths, frame elevation, constitutional basis, and
     content invariance.

  2. Governor integration tests — with a mocked S engine (FakeSEngine,
     same pattern as test_reasoning_trace.py) asserting that justification
     is attached to GovernedResponse when AlMuhajij is wired.

License: BSL 1.1
"""
import os
import sys
import types

import pytest

# Ensure the engine directory is importable (same pattern as the other tests).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_THIS_DIR, "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_muhajij import (  # noqa: E402
    AlMuhajij,
    AudienceChannel,
    ResponsePath,
    JustificationResult,
    _is_argumentative,
    _ARGUMENT_SIGNALS,
    _MAX_PATHS,
    _THETA_SAFE_STOP,
    _THETA_SAFE_FREEZE,
    _TEMPLATES,
    _ALTERNATIVE_PATHS,
)


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _muhajij() -> AlMuhajij:
    return AlMuhajij()


ALL_DECISIONS = ("EXECUTE", "CLARIFY", "SAFE_STOP", "SAFE_FREEZE", "BLOCKED")
ALL_CHANNELS = list(AudienceChannel)
NON_EXECUTE = ("CLARIFY", "SAFE_STOP", "SAFE_FREEZE", "BLOCKED")
BLOCKING_DECISIONS = ("SAFE_STOP", "SAFE_FREEZE", "BLOCKED")


# ═══════════════════════════════════════════════════════════
#  CONTRACT TESTS — module-level constants and dataclass shapes
# ═══════════════════════════════════════════════════════════

class TestContract:
    def test_audience_channel_has_five_values(self):
        assert len(AudienceChannel) == 5

    def test_audience_channel_names_correct(self):
        names = {c.name for c in AudienceChannel}
        assert "SCIENTIFIC_TECHNICAL" in names
        assert "HUMANITARIAN_ETHICAL" in names
        assert "ARCHITECTURAL_CONCEPTUAL" in names
        assert "PRACTICAL_APPLIED" in names
        assert "CULTURAL_SOCIAL" in names

    def test_max_paths_is_bounded(self):
        assert 1 <= _MAX_PATHS <= 3, "_MAX_PATHS must be 1–3 (spec: never more than 3)"

    def test_theta_safe_stop_reasonable(self):
        assert 0 < _THETA_SAFE_STOP < 1

    def test_theta_safe_freeze_greater_than_safe_stop(self):
        assert _THETA_SAFE_FREEZE > _THETA_SAFE_STOP

    def test_templates_cover_all_decisions(self):
        for decision in ALL_DECISIONS:
            assert decision in _TEMPLATES, f"Missing template for {decision}"

    def test_templates_cover_all_channels(self):
        for decision in ALL_DECISIONS:
            for channel in AudienceChannel:
                assert channel in _TEMPLATES[decision], (
                    f"Missing template for {decision}/{channel.name}"
                )

    def test_response_path_defaults_to_safe(self):
        path = ResponsePath(path_id=1, approach="test", frame="test_frame")
        assert path.is_safe is True
        assert path.is_active is True

    def test_justification_result_fields(self):
        result = _muhajij().justify("EXECUTE", h=0.1, s=0.6)
        assert isinstance(result, JustificationResult)
        assert result.decision
        assert result.primary_justification
        assert isinstance(result.audience_channel, AudienceChannel)
        assert isinstance(result.alternative_paths, list)
        assert isinstance(result.constitutional_basis, list)

    def test_argument_signals_non_empty(self):
        assert len(_ARGUMENT_SIGNALS) >= 10


# ═══════════════════════════════════════════════════════════
#  TEST 1: Each decision type gets appropriate justification
# ═══════════════════════════════════════════════════════════

class TestDecisionTypeJustification:
    def test_execute_returns_justification(self):
        result = _muhajij().justify("EXECUTE", h=0.1, s=0.6)
        assert result.decision == "EXECUTE"
        assert result.primary_justification

    def test_clarify_returns_justification(self):
        result = _muhajij().justify("CLARIFY", h=0.15, s=0.3)
        assert result.decision == "CLARIFY"
        assert result.primary_justification

    def test_safe_stop_returns_justification(self):
        result = _muhajij().justify("SAFE_STOP", h=0.55, s=0.55)
        assert result.decision == "SAFE_STOP"
        assert result.primary_justification

    def test_safe_freeze_returns_justification(self):
        result = _muhajij().justify("SAFE_FREEZE", h=0.85, s=0.85)
        assert result.decision == "SAFE_FREEZE"
        assert result.primary_justification

    def test_blocked_returns_justification(self):
        result = _muhajij().justify("BLOCKED", h=0.3, s=0.3)
        assert result.decision == "BLOCKED"
        assert result.primary_justification

    def test_unknown_decision_is_handled_gracefully(self):
        result = _muhajij().justify("UNKNOWN_DECISION", h=0.5, s=0.5)
        assert result.primary_justification  # graceful fallback

    def test_all_decisions_produce_non_empty_justification(self):
        m = _muhajij()
        for decision in ALL_DECISIONS:
            result = m.justify(decision, h=0.3, s=0.3)
            assert result.primary_justification, (
                f"{decision} produced empty justification"
            )


# ═══════════════════════════════════════════════════════════
#  TEST 2: Each audience channel produces different form, same content truth
# ═══════════════════════════════════════════════════════════

class TestAudienceChannels:
    def test_each_channel_produces_different_text(self):
        """Different channels must produce different primary_justification text."""
        m = _muhajij()
        texts = set()
        for channel in AudienceChannel:
            result = m.justify(
                "SAFE_STOP", h=0.55, s=0.55, audience=channel
            )
            texts.add(result.primary_justification)
        # At least 2 distinct texts (some may be similar but the set should not collapse to 1)
        assert len(texts) > 1, "All channels produced identical text — channels not differentiated"

    def test_each_channel_returns_correct_channel_enum(self):
        m = _muhajij()
        for channel in AudienceChannel:
            result = m.justify("SAFE_STOP", h=0.55, s=0.55, audience=channel)
            assert result.audience_channel == channel

    def test_scientific_channel_references_score(self):
        """SCIENTIFIC channel must reference the H score numerically."""
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            audience=AudienceChannel.SCIENTIFIC_TECHNICAL,
        )
        assert "0.55" in result.primary_justification, (
            "SCIENTIFIC channel must reference H score"
        )

    def test_cultural_channel_contains_arabic(self):
        """CULTURAL_SOCIAL channel must contain Arabic text."""
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            audience=AudienceChannel.CULTURAL_SOCIAL,
        )
        # Arabic Unicode range: U+0600–U+06FF
        has_arabic = any("؀" <= c <= "ۿ" for c in result.primary_justification)
        assert has_arabic, "CULTURAL_SOCIAL channel must contain Arabic text"

    def test_humanitarian_channel_mentions_protection_or_care(self):
        """HUMANITARIAN channel must reflect care/protection framing."""
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            audience=AudienceChannel.HUMANITARIAN_ETHICAL,
        )
        text_lower = result.primary_justification.lower()
        assert any(
            word in text_lower
            for word in ("protect", "harm", "safe", "help", "care", "mercy")
        )

    def test_practical_channel_provides_action_items(self):
        """PRACTICAL_APPLIED channel must include numbered actions."""
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            audience=AudienceChannel.PRACTICAL_APPLIED,
        )
        # Should have numbered options (1), (2), etc.
        assert "(1)" in result.primary_justification or "1)" in result.primary_justification

    def test_architectural_channel_references_governance_concepts(self):
        """ARCHITECTURAL_CONCEPTUAL channel must reference system-level concepts."""
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            audience=AudienceChannel.ARCHITECTURAL_CONCEPTUAL,
        )
        text_lower = result.primary_justification.lower()
        assert any(
            word in text_lower
            for word in ("gate", "equation", "s(d)", "governance", "constitutional", "fn#")
        )


# ═══════════════════════════════════════════════════════════
#  TEST 3: CLARIFY decisions offer rephrasing guidance
# ═══════════════════════════════════════════════════════════

class TestClarifyRephrasing:
    def test_clarify_has_alternative_paths(self):
        result = _muhajij().justify("CLARIFY", h=0.15, s=0.3)
        assert len(result.alternative_paths) > 0, (
            "CLARIFY must provide at least one alternative path"
        )

    def test_clarify_alternative_paths_are_safe(self):
        result = _muhajij().justify("CLARIFY", h=0.15, s=0.3)
        for path in result.alternative_paths:
            assert path.is_safe, "CLARIFY alternative paths must all be safe"

    def test_clarify_guidance_across_channels(self):
        """All channels for CLARIFY should offer rephrasing guidance."""
        m = _muhajij()
        for channel in AudienceChannel:
            result = m.justify("CLARIFY", h=0.15, s=0.3, audience=channel)
            assert result.primary_justification, (
                f"CLARIFY/{channel.name} must have non-empty justification"
            )
            assert result.alternative_paths, (
                f"CLARIFY/{channel.name} must have alternative paths"
            )

    def test_clarify_paths_mention_clarification_action(self):
        """CLARIFY alternatives should suggest concrete actions."""
        result = _muhajij().justify("CLARIFY", h=0.15, s=0.3)
        approaches = " ".join(p.approach.lower() for p in result.alternative_paths)
        assert any(
            word in approaches
            for word in ("detail", "specific", "context", "goal", "domain", "specify")
        )


# ═══════════════════════════════════════════════════════════
#  TEST 4: SAFE_STOP/FREEZE include alternative paths
# ═══════════════════════════════════════════════════════════

class TestAlternativePaths:
    def test_safe_stop_has_alternative_paths(self):
        result = _muhajij().justify("SAFE_STOP", h=0.55, s=0.55)
        assert len(result.alternative_paths) > 0, (
            "SAFE_STOP must include alternative paths"
        )

    def test_safe_freeze_has_alternative_paths(self):
        result = _muhajij().justify("SAFE_FREEZE", h=0.85, s=0.85)
        assert len(result.alternative_paths) > 0, (
            "SAFE_FREEZE must include alternative paths"
        )

    def test_blocked_has_alternative_paths(self):
        result = _muhajij().justify("BLOCKED", h=0.3, s=0.3)
        assert len(result.alternative_paths) > 0, (
            "BLOCKED must include alternative paths"
        )

    def test_all_alternative_paths_have_required_fields(self):
        m = _muhajij()
        for decision in NON_EXECUTE:
            result = m.justify(decision, h=0.5, s=0.5)
            for path in result.alternative_paths:
                assert isinstance(path, ResponsePath)
                assert path.path_id >= 1
                assert path.approach
                assert path.frame


# ═══════════════════════════════════════════════════════════
#  TEST 5: EXECUTE decisions have minimal justification
# ═══════════════════════════════════════════════════════════

class TestExecuteMinimal:
    def test_execute_has_no_alternative_paths(self):
        result = _muhajij().justify("EXECUTE", h=0.1, s=0.6)
        assert result.alternative_paths == [], (
            "EXECUTE must have no alternative paths (normal flow)"
        )

    def test_execute_has_no_frame_elevation(self):
        result = _muhajij().justify(
            "EXECUTE", h=0.1, s=0.6,
            user_message="but why can't you do more?",  # argumentative
        )
        assert result.frame_elevation is None, (
            "EXECUTE must not produce frame elevation even with argumentative language"
        )

    def test_execute_justification_is_short(self):
        result = _muhajij().justify("EXECUTE", h=0.1, s=0.6)
        # Should be brief — "Proceeding." level, not a full explanation
        assert len(result.primary_justification) < 200, (
            "EXECUTE justification should be minimal (under 200 chars)"
        )

    def test_execute_all_channels_minimal(self):
        m = _muhajij()
        for channel in AudienceChannel:
            result = m.justify("EXECUTE", h=0.1, s=0.6, audience=channel)
            assert result.alternative_paths == []
            assert result.frame_elevation is None


# ═══════════════════════════════════════════════════════════
#  TEST 6: Frame elevation triggers on argumentative language
# ═══════════════════════════════════════════════════════════

class TestFrameElevation:
    def test_frame_elevation_triggers_on_english_argument(self):
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            user_message="but why can't you help me with this?",
        )
        assert result.frame_elevation is not None, (
            "frame_elevation must trigger on 'but why'"
        )

    def test_frame_elevation_triggers_on_arabic_argument(self):
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            user_message="بس ليش ما تساعدني؟",
        )
        assert result.frame_elevation is not None, (
            "frame_elevation must trigger on Arabic argument signal"
        )

    def test_frame_elevation_not_triggered_on_neutral_message(self):
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            user_message="كيف أحصل على مساعدة؟",
        )
        assert result.frame_elevation is None, (
            "frame_elevation must NOT trigger on neutral message"
        )

    def test_frame_elevation_not_triggered_when_no_message(self):
        result = _muhajij().justify("SAFE_STOP", h=0.55, s=0.55, user_message="")
        assert result.frame_elevation is None

    def test_frame_elevation_is_principle_level_text(self):
        """Frame elevation must reference principles, not just rules."""
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            user_message="that's wrong, you should help",
        )
        assert result.frame_elevation is not None
        text_lower = result.frame_elevation.lower()
        # Must mention principle-level concept, not just "policy"
        assert any(
            word in text_lower
            for word in ("principle", "protect", "harm", "structural", "commitment")
        )

    def test_frame_elevation_references_h_score(self):
        """Frame elevation must mention the H score — same truth, elevated frame."""
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            user_message="i disagree with this decision",
        )
        assert result.frame_elevation is not None
        assert "0.55" in result.frame_elevation, (
            "frame_elevation must reference the H score — content invariance"
        )

    def test_is_argumentative_helper(self):
        """Unit-test the _is_argumentative helper directly."""
        assert _is_argumentative("but why won't you help") is True
        assert _is_argumentative("i disagree with this") is True
        assert _is_argumentative("هذا غلط") is True
        assert _is_argumentative("بس ليش") is True
        assert _is_argumentative("كيف أساعدك؟") is False
        assert _is_argumentative("") is False
        assert _is_argumentative("hello how are you") is False

    def test_frame_elevation_multiple_argument_signals(self):
        """Multiple argument signals in one message still triggers once."""
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            user_message="that's wrong and unfair",
        )
        assert result.frame_elevation is not None


# ═══════════════════════════════════════════════════════════
#  TEST 7: Constitutional basis is populated
# ═══════════════════════════════════════════════════════════

class TestConstitutionalBasis:
    def test_fn026_always_in_basis(self):
        """FN#026 (Anticipatory Logic) must always be cited — it's this module."""
        m = _muhajij()
        for decision in ALL_DECISIONS:
            result = m.justify(decision, h=0.3, s=0.3)
            assert 26 in result.constitutional_basis, (
                f"{decision} must cite FN#026 (Anticipatory Logic)"
            )

    def test_fn060_always_in_basis(self):
        """FN#060 (UDJE) must always be cited — it's this module."""
        m = _muhajij()
        for decision in ALL_DECISIONS:
            result = m.justify(decision, h=0.3, s=0.3)
            assert 60 in result.constitutional_basis, (
                f"{decision} must cite FN#060 (UDJE)"
            )

    def test_safe_stop_cites_fn029(self):
        result = _muhajij().justify("SAFE_STOP", h=0.55, s=0.55)
        assert 29 in result.constitutional_basis, "SAFE_STOP must cite FN#029 (Three-Tier Safety)"

    def test_safe_freeze_cites_fn029(self):
        result = _muhajij().justify("SAFE_FREEZE", h=0.85, s=0.85)
        assert 29 in result.constitutional_basis, "SAFE_FREEZE must cite FN#029"

    def test_blocked_cites_fn014(self):
        result = _muhajij().justify("BLOCKED", h=0.3, s=0.3)
        assert 14 in result.constitutional_basis, "BLOCKED must cite FN#014 (Responsible Authority)"

    def test_clarify_cites_fn001(self):
        result = _muhajij().justify("CLARIFY", h=0.15, s=0.3)
        assert 1 in result.constitutional_basis, "CLARIFY must cite FN#001 (Successful Failure)"

    def test_constitutional_basis_is_list_of_ints(self):
        result = _muhajij().justify("SAFE_STOP", h=0.55, s=0.55)
        assert all(isinstance(n, int) for n in result.constitutional_basis)

    def test_constitutional_basis_no_duplicates(self):
        m = _muhajij()
        for decision in ALL_DECISIONS:
            result = m.justify(decision, h=0.3, s=0.3)
            assert len(result.constitutional_basis) == len(set(result.constitutional_basis)), (
                f"{decision} constitutional_basis has duplicates"
            )

    def test_channel_adds_specific_articles(self):
        """SCIENTIFIC channel should add FN#069 (Bounded Claim Law)."""
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            audience=AudienceChannel.SCIENTIFIC_TECHNICAL,
        )
        assert 69 in result.constitutional_basis, (
            "SCIENTIFIC_TECHNICAL channel must add FN#069"
        )

    def test_humanitarian_channel_adds_mercy_article(self):
        """HUMANITARIAN channel should add FN#005 (Mercy)."""
        result = _muhajij().justify(
            "SAFE_STOP", h=0.55, s=0.55,
            audience=AudienceChannel.HUMANITARIAN_ETHICAL,
        )
        assert 5 in result.constitutional_basis, (
            "HUMANITARIAN_ETHICAL channel must add FN#005"
        )


# ═══════════════════════════════════════════════════════════
#  TEST 8: Alternative paths are all marked safe
# ═══════════════════════════════════════════════════════════

class TestPathSafetyInvariant:
    def test_all_paths_safe_for_all_decisions(self):
        """is_safe must be True for every alternative path, always."""
        m = _muhajij()
        for decision in ALL_DECISIONS:
            result = m.justify(decision, h=0.5, s=0.5)
            for path in result.alternative_paths:
                assert path.is_safe is True, (
                    f"{decision}: path {path.path_id} has is_safe=False — "
                    "safety invariant violated"
                )

    def test_all_paths_safe_across_channels(self):
        m = _muhajij()
        for decision in NON_EXECUTE:
            for channel in AudienceChannel:
                result = m.justify(decision, h=0.5, s=0.5, audience=channel)
                for path in result.alternative_paths:
                    assert path.is_safe is True

    def test_paths_have_non_empty_approaches(self):
        m = _muhajij()
        for decision in NON_EXECUTE:
            result = m.justify(decision, h=0.5, s=0.5)
            for path in result.alternative_paths:
                assert path.approach.strip(), (
                    f"{decision}: path {path.path_id} has empty approach"
                )


# ═══════════════════════════════════════════════════════════
#  TEST 9: Default audience is CULTURAL_SOCIAL
# ═══════════════════════════════════════════════════════════

class TestDefaultAudience:
    def test_default_audience_is_cultural_social(self):
        """When audience=None, AlMuhajij must use CULTURAL_SOCIAL."""
        result = _muhajij().justify("SAFE_STOP", h=0.55, s=0.55, audience=None)
        assert result.audience_channel == AudienceChannel.CULTURAL_SOCIAL

    def test_default_audience_matches_explicit_cultural(self):
        """Explicit CULTURAL_SOCIAL must match the default (None) result."""
        m = _muhajij()
        default_result = m.justify("SAFE_STOP", h=0.55, s=0.55, audience=None)
        explicit_result = m.justify(
            "SAFE_STOP", h=0.55, s=0.55,
            audience=AudienceChannel.CULTURAL_SOCIAL,
        )
        assert default_result.primary_justification == explicit_result.primary_justification
        assert default_result.audience_channel == explicit_result.audience_channel

    def test_default_applies_for_all_decisions(self):
        m = _muhajij()
        for decision in ALL_DECISIONS:
            result = m.justify(decision, h=0.3, s=0.3)  # no audience kwarg
            assert result.audience_channel == AudienceChannel.CULTURAL_SOCIAL


# ═══════════════════════════════════════════════════════════
#  TEST 11: Content invariance — all channels reference same core facts
# ═══════════════════════════════════════════════════════════

class TestContentInvariance:
    """FN#060: 'Never compromise content for palatability.'
    All channels for the same decision must reference the same underlying
    facts (H score value, same decision, same core reason for stopping).
    The FORM differs; the TRUTH does not.
    """

    def test_all_channels_same_decision(self):
        """All channels for SAFE_STOP must report decision=SAFE_STOP."""
        m = _muhajij()
        for channel in AudienceChannel:
            result = m.justify("SAFE_STOP", h=0.55, s=0.55, audience=channel)
            assert result.decision == "SAFE_STOP", (
                f"Channel {channel.name} changed the decision — content invariance violated"
            )

    def test_all_channels_reference_same_h_score(self):
        """All channels must reference the H score (in any format)."""
        m = _muhajij()
        h = 0.73
        for channel in AudienceChannel:
            result = m.justify("SAFE_STOP", h=h, s=h, audience=channel)
            text = result.primary_justification
            # The H value must appear either as decimal (0.73) or as percent (73%)
            has_score = "0.73" in text or "73%" in text
            assert has_score, (
                f"Channel {channel.name} does not reference H={h} — "
                "content invariance violated"
            )

    def test_all_channels_same_constitutional_basis_core(self):
        """FN#026 and FN#060 must appear in every channel's constitutional basis."""
        m = _muhajij()
        for channel in AudienceChannel:
            result = m.justify("SAFE_STOP", h=0.55, s=0.55, audience=channel)
            assert 26 in result.constitutional_basis, (
                f"Channel {channel.name} missing FN#026"
            )
            assert 60 in result.constitutional_basis, (
                f"Channel {channel.name} missing FN#060"
            )

    def test_clarify_all_channels_offer_alternatives(self):
        """All channels for CLARIFY must provide alternative paths."""
        m = _muhajij()
        for channel in AudienceChannel:
            result = m.justify("CLARIFY", h=0.15, s=0.3, audience=channel)
            assert result.alternative_paths, (
                f"Channel {channel.name} for CLARIFY has no alternatives"
            )


# ═══════════════════════════════════════════════════════════
#  TEST 12: Bounded — never more than 3 alternative paths
# ═══════════════════════════════════════════════════════════

class TestBoundedPaths:
    def test_never_more_than_max_paths(self):
        """No decision/channel combination may produce more than _MAX_PATHS paths."""
        m = _muhajij()
        for decision in ALL_DECISIONS:
            for channel in AudienceChannel:
                result = m.justify(decision, h=0.5, s=0.5, audience=channel)
                assert len(result.alternative_paths) <= _MAX_PATHS, (
                    f"{decision}/{channel.name}: {len(result.alternative_paths)} paths "
                    f"exceeds _MAX_PATHS={_MAX_PATHS}"
                )

    def test_execute_has_exactly_zero_paths(self):
        m = _muhajij()
        for channel in AudienceChannel:
            result = m.justify("EXECUTE", h=0.1, s=0.6, audience=channel)
            assert len(result.alternative_paths) == 0

    def test_path_ids_are_sequential(self):
        """Path IDs must be 1, 2, 3... (sequential from 1)."""
        m = _muhajij()
        for decision in NON_EXECUTE:
            result = m.justify(decision, h=0.5, s=0.5)
            for expected_id, path in enumerate(result.alternative_paths, start=1):
                assert path.path_id == expected_id, (
                    f"{decision}: expected path_id={expected_id}, got {path.path_id}"
                )


# ═══════════════════════════════════════════════════════════
#  Articles injection via __init__
# ═══════════════════════════════════════════════════════════

class TestArticlesInjection:
    def test_init_without_articles(self):
        m = AlMuhajij()
        result = m.justify("SAFE_STOP", h=0.55, s=0.55)
        assert result.primary_justification  # works without articles

    def test_init_with_duck_typed_articles(self):
        """Should accept any object with a .number attribute."""
        articles = [
            types.SimpleNamespace(number=26, title="ULP"),
            types.SimpleNamespace(number=60, title="UDJE"),
        ]
        m = AlMuhajij(articles=articles)
        result = m.justify("SAFE_STOP", h=0.55, s=0.55)
        assert result.primary_justification

    def test_init_with_empty_articles(self):
        m = AlMuhajij(articles=[])
        result = m.justify("CLARIFY", h=0.15, s=0.3)
        assert result.constitutional_basis


# ═══════════════════════════════════════════════════════════
#  TEST 10: Governor integration
# ═══════════════════════════════════════════════════════════

class FakeSEngine:
    """Minimal S engine returning controlled results (no Ollama)."""

    def __init__(self, decision="EXECUTE", H=0.1, I=0.8, E=0.2, S=0.6):
        self._decision = decision
        self._H = H
        self._I = I
        self._E = E
        self._S = S
        self.h_scorer = types.SimpleNamespace(backend_name="ollama:bge-m3")

    def compute(self, text, **kwargs):
        return {
            "decision": self._decision,
            "H": self._H,
            "I": self._I,
            "E": self._E,
            "S": self._S,
            "confidence": "high",
            "theta_effective": 0.40,
            "ambiguity_override": False,
            "F_prime": 0.5,
        }


def _make_governor(decision="EXECUTE", H=0.1, I=0.8, E=0.2, S=0.6):
    from aatif_governor import AATIFGovernor
    fake_s = FakeSEngine(decision=decision, H=H, I=I, E=E, S=S)
    return AATIFGovernor(
        s_engine=fake_s,
        on_degraded="safe_stop",
        verify_backend=False,
    )


class TestGovernorIntegration:
    def test_justification_attached_on_execute(self):
        gov = _make_governor(decision="EXECUTE")
        result = gov.process("hello", domain="general")
        assert result.justification is not None, (
            "justification should be attached to GovernedResponse on EXECUTE"
        )

    def test_justification_attached_on_clarify(self):
        gov = _make_governor(decision="CLARIFY")
        result = gov.process("something vague", domain="general")
        assert result.justification is not None, (
            "justification should be attached on CLARIFY"
        )

    def test_justification_attached_on_safe_stop(self):
        gov = _make_governor(decision="SAFE_STOP", H=0.55, S=0.55)
        result = gov.process("risky message", domain="general")
        assert result.blocked
        assert result.justification is not None, (
            "justification should be attached on SAFE_STOP"
        )

    def test_justification_attached_on_safe_freeze(self):
        gov = _make_governor(decision="SAFE_FREEZE", H=0.9, S=0.9)
        result = gov.process("very risky", domain="general")
        assert result.blocked
        assert result.justification is not None, (
            "justification should be attached on SAFE_FREEZE"
        )

    def test_justification_decision_matches_final_decision(self):
        gov = _make_governor(decision="EXECUTE")
        result = gov.process("hello", domain="general")
        assert result.justification is not None
        assert result.justification.decision == result.final_decision

    def test_clarify_governed_prompt_includes_justification(self):
        """For CLARIFY, the governed prompt should include justification text."""
        gov = _make_governor(decision="CLARIFY")
        result = gov.process("vague question", domain="general")
        assert not result.blocked
        # The governed prompt should contain the justification guidance
        assert result.governed_prompt, "governed_prompt must be built for CLARIFY"
        # Justification should be woven in for CLARIFY
        assert result.justification is not None
        assert result.justification.primary_justification in result.governed_prompt, (
            "CLARIFY governed_prompt must include justification text"
        )

    def test_justification_audience_defaults_to_cultural_social(self):
        """Default audience (not specified in governor) must be CULTURAL_SOCIAL."""
        gov = _make_governor(decision="SAFE_STOP", H=0.55, S=0.55)
        result = gov.process("test", domain="general")
        assert result.justification is not None
        assert result.justification.audience_channel == AudienceChannel.CULTURAL_SOCIAL

    def test_governor_works_without_muhajij_injected_as_none(self):
        """Governor should function normally when muhajij=None (auto-constructs)."""
        from aatif_governor import AATIFGovernor, HAS_MUHAJIJ
        fake_s = FakeSEngine(decision="EXECUTE")
        gov = AATIFGovernor(
            s_engine=fake_s,
            on_degraded="safe_stop",
            verify_backend=False,
            muhajij=None,  # trigger auto-construction
        )
        result = gov.process("hello", domain="general")
        assert result.final_decision == "EXECUTE"
        if HAS_MUHAJIJ:
            assert result.justification is not None

    def test_safe_stop_justification_has_alternative_paths(self):
        gov = _make_governor(decision="SAFE_STOP", H=0.55, S=0.55)
        result = gov.process("test", domain="general")
        assert result.justification is not None
        assert len(result.justification.alternative_paths) > 0

    def test_all_justification_paths_are_safe_in_governor(self):
        """Safety invariant: no alternative path may have is_safe=False."""
        gov = _make_governor(decision="SAFE_STOP", H=0.55, S=0.55)
        result = gov.process("test", domain="general")
        assert result.justification is not None
        for path in result.justification.alternative_paths:
            assert path.is_safe is True
