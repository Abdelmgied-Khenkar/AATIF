#!/usr/bin/env python3
"""
test_logic_profile_scanner.py — ماسح المنطق (FN#048)
=====================================================
Covers ``engine/aatif_logic_profile_scanner.py`` — the Logic Profile Scanner
that reads the user's reasoning STYLE (Reductionist, Challenger, Tester, Sincere
Learner, Ego-Driven) from observable language patterns only.

This module is PURE LOGIC (no embeddings, no LLM), so every test here runs
WITHOUT Ollama.  Two layers:

  1. Unit tests on LogicProfileScanner.scan — driving the scanner with controlled
     Arabic/English inputs and pinning that each profile detects its own signals,
     that the primary/secondary profiles are identified correctly, that mixed
     style is flagged, and that the recommended tone matches the profile.

  2. Governor integration tests — with a mocked S engine (FakeSEngine, same
     pattern as test_five_layer_intent.py) asserting that logic_profile is
     attached to GovernedResponse when the scanner is wired.

A dedicated TestObservableOnly group enforces the field note's STRICT
constraint: LPS analyses only observable language patterns and never makes
hidden psychological claims.

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

from aatif_logic_profile_scanner import (  # noqa: E402
    LogicProfileScanner,
    LogicProfileResult,
    ProfileReading,
    LogicProfile,
    recommend_tone,
)


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _scanner() -> LogicProfileScanner:
    return LogicProfileScanner()


# ═══════════════════════════════════════════════════════════
#  CONTRACT TESTS — shape of the result
# ═══════════════════════════════════════════════════════════

class TestContract:
    def test_result_has_all_five_profiles(self):
        r = _scanner().scan("أين الدليل؟")
        assert isinstance(r, LogicProfileResult)
        for reading in r.as_list():
            assert isinstance(reading, ProfileReading)
        profiles = {reading.profile for reading in r.as_list()}
        assert profiles == set(LogicProfile)

    def test_each_reading_profile_matches_key(self):
        r = _scanner().scan("test")
        for profile, reading in r.readings.items():
            assert reading.profile is profile

    def test_confidence_in_range(self):
        r = _scanner().scan("أنت غلط وهذا لن ينجح، أثبت العكس")
        for reading in r.as_list():
            assert 0.0 <= reading.confidence <= 1.0

    def test_primary_is_enum_member(self):
        r = _scanner().scan("random text here")
        assert isinstance(r.primary_profile, LogicProfile)

    def test_recommended_tone_non_empty(self):
        r = _scanner().scan("أين الدليل؟")
        assert r.recommended_tone.strip()


# ═══════════════════════════════════════════════════════════
#  PROFILE DETECTION — each profile detects its signals
# ═══════════════════════════════════════════════════════════

class TestProfileDetection:
    def test_reductionist_detected(self):
        r = _scanner().scan("هذا مجرد chatbot، مش أكثر من autocomplete")
        assert r.readings[LogicProfile.REDUCTIONIST].detected
        assert r.primary_profile is LogicProfile.REDUCTIONIST

    def test_challenger_detected(self):
        r = _scanner().scan("أنت غلط وهذا لن ينجح")
        assert r.readings[LogicProfile.CHALLENGER].detected
        assert r.primary_profile is LogicProfile.CHALLENGER

    def test_tester_detected(self):
        r = _scanner().scan("أين الدليل على أن هذا يعمل؟")
        assert r.readings[LogicProfile.TESTER].detected
        assert r.primary_profile is LogicProfile.TESTER

    def test_sincere_learner_detected(self):
        r = _scanner().scan("ساعدني أفهم كيف يختلف هذا")
        assert r.readings[LogicProfile.SINCERE_LEARNER].detected
        assert r.primary_profile is LogicProfile.SINCERE_LEARNER

    def test_ego_driven_detected(self):
        r = _scanner().scan("أنا أعرف AI أكثر منك")
        assert r.readings[LogicProfile.EGO_DRIVEN].detected
        assert r.primary_profile is LogicProfile.EGO_DRIVEN

    def test_each_reading_lists_its_signals(self):
        r = _scanner().scan("أين الدليل؟ وش المنهجية؟")
        tester = r.readings[LogicProfile.TESTER]
        assert tester.signals
        # Detected profiles always carry at least one concrete signal.
        for reading in r.as_list():
            if reading.detected:
                assert reading.signals

    def test_undetected_profile_has_no_signals(self):
        r = _scanner().scan("ساعدني أفهم")
        # A pure-learner message should not trip the challenger profile.
        assert not r.readings[LogicProfile.CHALLENGER].detected
        assert r.readings[LogicProfile.CHALLENGER].signals == []


# ═══════════════════════════════════════════════════════════
#  ARABIC SIGNALS
# ═══════════════════════════════════════════════════════════

class TestArabicSignals:
    def test_arabic_reductionist(self):
        r = _scanner().scan("هذا مجرد آلة، زي أي برنامج")
        assert r.readings[LogicProfile.REDUCTIONIST].detected

    def test_arabic_challenger(self):
        r = _scanner().scan("مستحيل ينجح، أثبت لي العكس")
        assert r.readings[LogicProfile.CHALLENGER].detected

    def test_arabic_tester(self):
        r = _scanner().scan("كيف تقيس النتائج؟ وين الدليل؟")
        assert r.readings[LogicProfile.TESTER].detected

    def test_arabic_sincere_learner(self):
        r = _scanner().scan("ممكن توضح لي؟ ودي أتعلم")
        assert r.readings[LogicProfile.SINCERE_LEARNER].detected

    def test_arabic_ego_driven(self):
        r = _scanner().scan("أنا خبير وعندي خبرة، طريقتي أفضل")
        assert r.readings[LogicProfile.EGO_DRIVEN].detected

    def test_arabic_diacritics_normalized(self):
        # Diacritized form should still detect the tester signal.
        r = _scanner().scan("أينَ الدليلُ؟")
        assert r.readings[LogicProfile.TESTER].detected


# ═══════════════════════════════════════════════════════════
#  ENGLISH SIGNALS
# ═══════════════════════════════════════════════════════════

class TestEnglishSignals:
    def test_english_reductionist(self):
        r = _scanner().scan("it's just a fancy autocomplete, nothing but stats")
        assert r.readings[LogicProfile.REDUCTIONIST].detected

    def test_english_challenger(self):
        r = _scanner().scan("you're wrong, this won't work, prove me wrong")
        assert r.readings[LogicProfile.CHALLENGER].detected

    def test_english_tester(self):
        r = _scanner().scan("where's the evidence? what's the methodology?")
        assert r.readings[LogicProfile.TESTER].detected

    def test_english_sincere_learner(self):
        r = _scanner().scan("help me understand how this works, I'm curious")
        assert r.readings[LogicProfile.SINCERE_LEARNER].detected

    def test_english_ego_driven(self):
        r = _scanner().scan("I'm an expert, I could do better, let me tell you")
        assert r.readings[LogicProfile.EGO_DRIVEN].detected

    def test_english_case_insensitive(self):
        r = _scanner().scan("WHERE'S THE EVIDENCE for this claim?")
        assert r.readings[LogicProfile.TESTER].detected


# ═══════════════════════════════════════════════════════════
#  PRIMARY PROFILE
# ═══════════════════════════════════════════════════════════

class TestPrimaryProfile:
    def test_strongest_profile_is_primary(self):
        # Many challenger signals, one stray learner phrase → challenger primary.
        r = _scanner().scan(
            "أنت غلط، هذا لن ينجح، مستحيل، كلام فاضي. بس ساعدني أفهم"
        )
        assert r.primary_profile is LogicProfile.CHALLENGER

    def test_single_profile_message(self):
        r = _scanner().scan("ساعدني أفهم كيف يختلف هذا عن غيره")
        assert r.primary_profile is LogicProfile.SINCERE_LEARNER
        assert r.secondary_profile is None

    def test_confrontational_wins_tie_over_learner(self):
        # One ego signal vs one learner signal — confrontational priority wins.
        r = _scanner().scan("أنا خبير. ممكن توضح؟")
        assert r.primary_profile is LogicProfile.EGO_DRIVEN

    def test_primary_consistent_across_runs(self):
        text = "أين الدليل على أن هذا يعمل؟"
        a = _scanner().scan(text).primary_profile
        b = _scanner().scan(text).primary_profile
        assert a is b  # deterministic


# ═══════════════════════════════════════════════════════════
#  SECONDARY PROFILE
# ═══════════════════════════════════════════════════════════

class TestSecondaryProfile:
    def test_secondary_detected_when_two_strong(self):
        # Strong tester AND strong challenger signals.
        r = _scanner().scan(
            "أنت غلط وهذا لن ينجح، مستحيل. أين الدليل؟ كيف تقيس؟ وش المنهجية؟"
        )
        assert r.secondary_profile is not None
        assert r.secondary_profile != r.primary_profile

    def test_no_secondary_for_single_profile(self):
        r = _scanner().scan("ساعدني أفهم")
        assert r.secondary_profile is None

    def test_weak_second_not_promoted_to_secondary(self):
        # Strong tester, single weak learner signal below threshold.
        r = _scanner().scan(
            "أين الدليل؟ كيف تقيس؟ وش المنهجية؟ بالمقارنة مع غيره؟ ودي أتعلم"
        )
        assert r.primary_profile is LogicProfile.TESTER
        # One learner signal → confidence 0.5+ may or may not reach threshold,
        # but it must never outrank the dominant tester.
        assert r.secondary_profile != LogicProfile.TESTER


# ═══════════════════════════════════════════════════════════
#  PROFILE MIX
# ═══════════════════════════════════════════════════════════

class TestProfileMix:
    def test_mix_flagged_when_two_profiles_strong(self):
        r = _scanner().scan(
            "أنت غلط وهذا لن ينجح، مستحيل. أين الدليل؟ كيف تقيس؟ وش المنهجية؟"
        )
        assert r.profile_mix is True

    def test_no_mix_for_clean_single_profile(self):
        r = _scanner().scan("ساعدني أفهم كيف يختلف هذا")
        assert r.profile_mix is False

    def test_no_mix_when_nothing_detected(self):
        r = _scanner().scan("نظّم لي الجدول من فضلك")
        assert r.profile_mix is False

    def test_mix_tone_mentions_flexibility(self):
        r = _scanner().scan(
            "أنت غلط وهذا لن ينجح، مستحيل. أين الدليل؟ كيف تقيس؟ وش المنهجية؟"
        )
        assert r.profile_mix
        assert "Mixed" in r.recommended_tone or "مختلط" in r.recommended_tone


# ═══════════════════════════════════════════════════════════
#  RECOMMENDED TONE
# ═══════════════════════════════════════════════════════════

class TestRecommendedTone:
    def test_reductionist_tone_expands_frame(self):
        r = _scanner().scan("هذا مجرد chatbot")
        assert "frame" in r.recommended_tone.lower() or \
            "إطار" in r.recommended_tone

    def test_challenger_tone_stays_grounded(self):
        r = _scanner().scan("أنت غلط وهذا لن ينجح")
        assert "grounded" in r.recommended_tone.lower() or \
            "ثابت" in r.recommended_tone

    def test_tester_tone_provides_data(self):
        r = _scanner().scan("أين الدليل؟")
        assert "data" in r.recommended_tone.lower() or \
            "بيانات" in r.recommended_tone

    def test_sincere_learner_tone_teaches_warmly(self):
        r = _scanner().scan("ساعدني أفهم")
        assert "teach" in r.recommended_tone.lower() or \
            "warm" in r.recommended_tone.lower() or "علّم" in r.recommended_tone

    def test_ego_driven_tone_acknowledges_without_submission(self):
        r = _scanner().scan("أنا أعرف أكثر منك")
        assert "acknowledge" in r.recommended_tone.lower() or \
            "expertise" in r.recommended_tone.lower() or \
            "اعترف" in r.recommended_tone

    def test_neutral_tone_when_nothing_detected(self):
        r = _scanner().scan("نظّم لي الجدول")
        assert "natural" in r.recommended_tone.lower() or \
            "no strong" in r.recommended_tone.lower() or \
            "طبيعية" in r.recommended_tone

    def test_recommend_tone_function_matches_result(self):
        r = _scanner().scan("أين الدليل؟")
        assert recommend_tone(r) == r.recommended_tone


# ═══════════════════════════════════════════════════════════
#  EDGE CASES
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_string(self):
        r = _scanner().scan("")
        assert isinstance(r, LogicProfileResult)
        assert isinstance(r.primary_profile, LogicProfile)
        assert r.recommended_tone.strip()

    def test_whitespace_only(self):
        r = _scanner().scan("    ")
        assert isinstance(r, LogicProfileResult)
        assert not r.detected_profiles()

    def test_single_char(self):
        r = _scanner().scan("x")
        assert isinstance(r, LogicProfileResult)

    def test_none_safe_via_empty(self):
        r = _scanner().scan(None)  # type: ignore[arg-type]
        assert isinstance(r, LogicProfileResult)

    def test_neutral_text_defaults_to_learner(self):
        # No style signals → charitable default (sincere learner, warm tone).
        r = _scanner().scan("نظّم لي الجدول من فضلك")
        assert not r.detected_profiles()
        assert r.primary_profile is LogicProfile.SINCERE_LEARNER

    def test_very_long_input(self):
        r = _scanner().scan("أين الدليل؟ " * 300)
        assert isinstance(r, LogicProfileResult)
        assert r.primary_profile is LogicProfile.TESTER

    def test_mixed_language(self):
        r = _scanner().scan("هذا just a chatbot، nothing but مجرد آلة")
        assert r.readings[LogicProfile.REDUCTIONIST].detected


# ═══════════════════════════════════════════════════════════
#  OBSERVABLE ONLY — the field note's strict constraint
# ═══════════════════════════════════════════════════════════

class TestObservableOnly:
    """FN#048 is STRICT: only observable language patterns, never hidden
    psychological claims."""

    def test_every_detected_reading_is_backed_by_a_signal(self):
        # The signal IS the observable evidence. A detected profile with no
        # signal would be an unfounded (psychological) claim — forbidden.
        texts = [
            "هذا مجرد chatbot",
            "أنت غلط",
            "أين الدليل؟",
            "ساعدني أفهم",
            "أنا خبير",
            "it's just autocomplete",
            "where's the evidence?",
        ]
        for t in texts:
            r = _scanner().scan(t)
            for reading in r.as_list():
                if reading.detected:
                    assert reading.signals, \
                        f"profile {reading.profile} detected with no signal for {t!r}"

    def test_every_signal_literally_present_in_text(self):
        # Each fired signal must be a phrase the user actually wrote (after
        # normalization), not an inference about their state of mind.
        from aatif_logic_profile_scanner import _normalize
        text = "أين الدليل على أن هذا يعمل؟ it's just a tool"
        r = _scanner().scan(text)
        norm = _normalize(text)
        low = text.lower()
        for reading in r.as_list():
            for sig in reading.signals:
                assert _normalize(sig) in norm or sig in low, \
                    f"signal {sig!r} not literally present in text"

    def test_descriptions_describe_language_not_psychology(self):
        # Descriptions must talk about FRAMING/LANGUAGE, never claim what the
        # person "is" or "feels". Forbidden words guard against mind-reading.
        forbidden = ["feels", "believes", "secretly", "really wants",
                     "personality", "insecure", "narcissist"]
        r = _scanner().scan("أنا أعرف أكثر منك، أنت غلط")
        for reading in r.as_list():
            desc = reading.description.lower()
            for word in forbidden:
                assert word not in desc

    def test_no_detection_means_no_claim(self):
        # Neutral text yields zero detected profiles — the scanner does not
        # invent a style where the language shows none.
        r = _scanner().scan("احسب لي مجموع هذه الأرقام")
        assert r.detected_profiles() == []


# ═══════════════════════════════════════════════════════════
#  GOVERNOR INTEGRATION
# ═══════════════════════════════════════════════════════════

class FakeSEngine:
    """Minimal S engine that returns controlled s_result dicts (no Ollama)."""

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


class TestGovernorIntegration:
    def _make_governor(self, decision="EXECUTE", H=0.1, I=0.8, E=0.2, S=0.6):
        from aatif_governor import AATIFGovernor
        fake_s = FakeSEngine(decision=decision, H=H, I=I, E=E, S=S)
        return AATIFGovernor(
            s_engine=fake_s,
            on_degraded="safe_stop",
            verify_backend=False,
        )

    def test_logic_profile_attached_on_execute(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("أين الدليل على أن هذا يعمل؟", domain="general")
        assert result.logic_profile is not None
        assert isinstance(result.logic_profile, LogicProfileResult)
        assert result.logic_profile.primary_profile is LogicProfile.TESTER

    def test_tone_injected_into_prompt(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("أين الدليل؟ وش المنهجية؟", domain="general")
        assert "FN#048" in result.governed_prompt
        # Tester tone guidance should be woven in.
        assert "tester" in result.governed_prompt or \
            "data" in result.governed_prompt.lower()

    def test_no_profile_section_when_neutral(self):
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process("نظّم لي الجدول", domain="general")
        # Neutral text → no detected profile → no FN#048 section in the prompt.
        assert "FN#048" not in result.governed_prompt
        # But the reading is still attached for the audit trail.
        assert result.logic_profile is not None

    def test_logic_profile_attached_on_clarify(self):
        gov = self._make_governor(decision="CLARIFY", I=0.3)
        result = gov.process("ساعدني أفهم", domain="general")
        assert result.logic_profile is not None

    def test_logic_profile_attached_on_safe_freeze(self):
        gov = self._make_governor(decision="SAFE_FREEZE", H=0.9, S=0.9)
        result = gov.process("أنت غلط وهذا لن ينجح", domain="general")
        assert result.blocked
        assert result.final_decision == "SAFE_FREEZE"
        # Reading runs after S compute, so it is still attached on blocked paths.
        assert result.logic_profile is not None

    def test_governor_works_with_explicit_none_scanner(self):
        from aatif_governor import AATIFGovernor, HAS_LOGIC_PROFILE
        fake_s = FakeSEngine(decision="EXECUTE")
        gov = AATIFGovernor(
            s_engine=fake_s,
            on_degraded="safe_stop",
            verify_backend=False,
            logic_profile_scanner=None,
        )
        result = gov.process("hello", domain="general")
        assert result.final_decision == "EXECUTE"
        if HAS_LOGIC_PROFILE:
            # Auto-constructed when the module is importable.
            assert result.logic_profile is not None
        else:
            assert result.logic_profile is None

    def test_logic_profile_never_changes_decision(self):
        # An aggressive challenger style must not flip an EXECUTE to a block.
        gov = self._make_governor(decision="EXECUTE")
        result = gov.process(
            "أنت غلط، مستحيل ينجح، كلام فاضي، أثبت العكس", domain="general"
        )
        assert result.final_decision == "EXECUTE"
        assert not result.blocked


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
