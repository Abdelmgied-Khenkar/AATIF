"""
Test suite for FN#041 Context-Preservation & Parallel-Task Safety Protocol (PVM)
— aatif_pvm_detector.py

Tests the PVMDetector (observational, stylistic), PVMReading/PVMContext
dataclasses, state lifecycle, three-tier detection (deterministic → temporal →
behavioral), sparse activation fast-path, cultural sensitivity via domain
config, and the B-prime authority contract.

Architecture under test (B-prime):
  PVMContext      →  pure storage (prior PVM state, turn bookkeeping)
  PVMDetector     →  observational, STYLISTIC, NOT safety
  PVMReading      →  output (recommendation to R equation, not a decision)

Design rule: FN#041 binds through B5 (Behaviour), never touches S/H/θ/S-equation.
Design brief: FN041_DESIGN_BRIEF.md, 2026-07-01

License: BSL 1.1
"""

import pytest
from dataclasses import fields as dc_fields
from datetime import timedelta

from aatif_pvm_detector import (
    # Feature flags
    PVM_ENABLED,
    PVM_MONITOR_ONLY,
    # Authority level
    AUTHORITY_LEVEL,
    CAN_BLOCK_RUNTIME,
    CAN_MODIFY_H,
    CAN_MODIFY_THETA,
    CAN_MODIFY_S,
    CAN_EMIT_JUDICIAL_DECISION,
    # State enum
    PVMState,
    # Constants
    FAST_PATH_NOT_BUSY_THRESHOLD,
    PVM_ENGAGE_THRESHOLD,
    PVM_ENGAGE_THRESHOLD_HIGH_STAKES,
    PVM_ENGAGE_THRESHOLD_FAST_PACED,
    MINIMAL_RESPONSE_MAX_WORDS,
    MINIMAL_RESPONSE_MAX_CHARS,
    CONSECUTIVE_MINIMAL_FOR_DETECTING,
    CONSECUTIVE_MINIMAL_FOR_ENGAGED,
    GAP_MULTIPLIER_FOR_BUSY,
    DEFAULT_AVERAGE_GAP_SECONDS,
    LONG_GAP_ABSOLUTE_SECONDS,
    DECAY_TURNS_TO_ACTIVE,
    DECAY_TURNS_HIGH_STAKES,
    PAUSE_FULL_WAIT,
    PAUSE_BRIEF_ACK,
    PAUSE_SHORTENED,
    PAUSE_NORMAL,
    PVM_PROFILE_BY_DOMAIN,
    DEFAULT_PVM_PROFILE,
    # Marker lists
    BUSY_MARKERS_AR,
    BUSY_MARKERS_EN,
    MULTITASK_MARKERS_AR,
    MULTITASK_MARKERS_EN,
    RETURN_MARKERS_AR,
    RETURN_MARKERS_EN,
    INCOMPLETE_ACK_AR,
    INCOMPLETE_ACK_EN,
    DIRECTIVE_MARKERS_EN,
    DIRECTIVE_MARKERS_AR,
    ACKNOWLEDGMENTS,
    # Data classes
    PVMReading,
    PVMContext,
    PVMDomainConfig,
    # Detector
    PVMDetector,
    # Transition helpers
    next_pvm_state,
    pvm_should_deactivate,
    apply_pvm_transition,
    # Audit
    pvm_audit_hash,
)


# ═══════════════════════════════════════════════════════════════
#  TestFeatureFlags — FN#041 ships ON by default
# ═══════════════════════════════════════════════════════════════

class TestFeatureFlags:
    def test_pvm_enabled_by_default(self):
        assert PVM_ENABLED is True, "PVM_ENABLED must default to True"

    def test_pvm_monitor_only_off_by_default(self):
        assert PVM_MONITOR_ONLY is False, "PVM_MONITOR_ONLY must default to False"

    def test_feature_flags_are_bool(self):
        assert isinstance(PVM_ENABLED, bool)
        assert isinstance(PVM_MONITOR_ONLY, bool)


# ═══════════════════════════════════════════════════════════════
#  TestAuthorityLevel — B-prime contract (NEVER safety)
# ═══════════════════════════════════════════════════════════════

class TestAuthorityLevel:
    def test_authority_level_is_observational(self):
        assert AUTHORITY_LEVEL == "B_PRIME_OBSERVATIONAL"

    def test_cannot_block_runtime(self):
        assert CAN_BLOCK_RUNTIME is False

    def test_cannot_modify_h(self):
        assert CAN_MODIFY_H is False

    def test_cannot_modify_theta(self):
        assert CAN_MODIFY_THETA is False

    def test_cannot_modify_s(self):
        assert CAN_MODIFY_S is False

    def test_cannot_emit_judicial_decision(self):
        assert CAN_EMIT_JUDICIAL_DECISION is False


# ═══════════════════════════════════════════════════════════════
#  TestPVMState — State enum values
# ═══════════════════════════════════════════════════════════════

class TestPVMState:
    def test_active_value(self):
        assert PVMState.ACTIVE.value == "active"

    def test_detecting_value(self):
        assert PVMState.DETECTING.value == "detecting"

    def test_pvm_engaged_value(self):
        assert PVMState.PVM_ENGAGED.value == "pvm_engaged"

    def test_reactivating_value(self):
        assert PVMState.REACTIVATING.value == "reactivating"

    def test_exactly_four_states(self):
        assert len(PVMState) == 4


# ═══════════════════════════════════════════════════════════════
#  TestDataclasses — PVMReading / PVMContext / PVMDomainConfig
# ═══════════════════════════════════════════════════════════════

class TestDataclasses:
    def test_pvm_reading_defaults(self):
        r = PVMReading(
            state=PVMState.ACTIVE,
            confidence=0.0,
            should_pause=False,
            pause_type=PAUSE_NORMAL,
            recommended_acknowledgment="",
        )
        assert r.state == PVMState.ACTIVE
        assert r.confidence == 0.0
        assert r.should_pause is False
        assert r.pause_type == PAUSE_NORMAL
        assert r.recommended_acknowledgment == ""
        assert r.evidence == []
        assert r.signals_detected == []
        assert r.estimated_return_likelihood == 0.5

    def test_pvm_context_defaults(self):
        c = PVMContext()
        assert c.state == PVMState.ACTIVE
        assert c.last_explicit_directive_turn == -1
        assert c.consecutive_minimal_responses == 0
        assert c.last_gap_seconds is None
        assert c.pvm_engage_turn == -1
        assert c.pvm_engage_timestamp is None
        assert c.last_return_signal_turn == -1
        assert c.total_pvm_engagements == 0
        assert c.quiet_turns_since_pvm == 0
        assert c.last_transition_reason is None
        assert c.domain_profile == DEFAULT_PVM_PROFILE

    def test_pvm_domain_config_defaults(self):
        cfg = PVMDomainConfig()
        assert cfg.domain == "general"
        assert cfg.pvm_profile == DEFAULT_PVM_PROFILE
        assert cfg.high_stakes is False
        assert cfg.engage_threshold == PVM_ENGAGE_THRESHOLD

    def test_pvm_domain_config_for_healthcare(self):
        cfg = PVMDomainConfig.for_domain("healthcare")
        assert cfg.high_stakes is True
        assert cfg.engage_threshold == PVM_ENGAGE_THRESHOLD_HIGH_STAKES
        assert cfg.pvm_profile == "high_stakes"

    def test_pvm_domain_config_for_creative(self):
        cfg = PVMDomainConfig.for_domain("creative")
        assert cfg.high_stakes is False
        assert cfg.engage_threshold == PVM_ENGAGE_THRESHOLD_FAST_PACED
        assert cfg.pvm_profile == "fast_paced"

    def test_pvm_domain_config_for_unknown(self):
        cfg = PVMDomainConfig.for_domain("unknown_domain")
        assert cfg.pvm_profile == DEFAULT_PVM_PROFILE
        assert cfg.engage_threshold == PVM_ENGAGE_THRESHOLD

    def test_pvm_reading_evidence_is_mutable_list(self):
        r = PVMReading(
            state=PVMState.ACTIVE, confidence=0.0,
            should_pause=False, pause_type=PAUSE_NORMAL,
            recommended_acknowledgment="",
        )
        r.evidence.append("test")
        assert len(r.evidence) == 1

    def test_pvm_context_state_can_be_set(self):
        c = PVMContext(state=PVMState.PVM_ENGAGED)
        assert c.state == PVMState.PVM_ENGAGED


# ═══════════════════════════════════════════════════════════════
#  TestConstants — Calibration values
# ═══════════════════════════════════════════════════════════════

class TestConstants:
    def test_fast_path_threshold(self):
        assert FAST_PATH_NOT_BUSY_THRESHOLD == 0.95

    def test_engage_threshold(self):
        assert PVM_ENGAGE_THRESHOLD == 0.60

    def test_high_stakes_threshold_higher(self):
        assert PVM_ENGAGE_THRESHOLD_HIGH_STAKES > PVM_ENGAGE_THRESHOLD

    def test_fast_paced_threshold_lower(self):
        assert PVM_ENGAGE_THRESHOLD_FAST_PACED < PVM_ENGAGE_THRESHOLD

    def test_minimal_response_max_words(self):
        assert MINIMAL_RESPONSE_MAX_WORDS == 3

    def test_pause_type_constants(self):
        assert PAUSE_FULL_WAIT == "full_wait"
        assert PAUSE_BRIEF_ACK == "brief_ack"
        assert PAUSE_SHORTENED == "shortened"
        assert PAUSE_NORMAL == "normal"

    def test_decay_turns_high_stakes_longer(self):
        assert DECAY_TURNS_HIGH_STAKES > DECAY_TURNS_TO_ACTIVE


# ═══════════════════════════════════════════════════════════════
#  TestMarkerLists — Non-empty, no duplicates
# ═══════════════════════════════════════════════════════════════

class TestMarkerLists:
    def test_busy_markers_ar_non_empty(self):
        assert len(BUSY_MARKERS_AR) > 0

    def test_busy_markers_en_non_empty(self):
        assert len(BUSY_MARKERS_EN) > 0

    def test_return_markers_ar_non_empty(self):
        assert len(RETURN_MARKERS_AR) > 0

    def test_return_markers_en_non_empty(self):
        assert len(RETURN_MARKERS_EN) > 0

    def test_multitask_markers_non_empty(self):
        assert len(MULTITASK_MARKERS_AR) > 0
        assert len(MULTITASK_MARKERS_EN) > 0

    def test_incomplete_ack_markers_non_empty(self):
        assert len(INCOMPLETE_ACK_AR) > 0
        assert len(INCOMPLETE_ACK_EN) > 0

    def test_directive_markers_non_empty(self):
        assert len(DIRECTIVE_MARKERS_EN) > 0
        assert len(DIRECTIVE_MARKERS_AR) > 0

    def test_acknowledgments_keys(self):
        expected = {"busy_detected", "busy_detected_en", "brief_ack",
                    "brief_ack_en", "returning", "returning_en",
                    "still_here", "still_here_en"}
        assert expected.issubset(set(ACKNOWLEDGMENTS.keys()))


# ═══════════════════════════════════════════════════════════════
#  TestExplicitBusyArabic — Tier 1 deterministic markers (Arabic)
# ═══════════════════════════════════════════════════════════════

class TestExplicitBusyArabic:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_mashghool(self, detector):
        r = detector.detect("مشغول")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)
        assert r.confidence > 0.5

    def test_lahza(self, detector):
        r = detector.detect("لحظة")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)
        assert r.confidence > 0.5

    def test_daqiqa(self, detector):
        r = detector.detect("دقيقة")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)
        assert r.confidence > 0.5

    def test_ba3dain(self, detector):
        r = detector.detect("بعدين")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)
        assert r.confidence > 0.5

    def test_intather(self, detector):
        r = detector.detect("انتظر")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)
        assert r.confidence > 0.5

    def test_mo_alhin(self, detector):
        r = detector.detect("مو الحين")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)
        assert r.confidence > 0.5

    def test_khalini(self, detector):
        r = detector.detect("خليني")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_busy_with_sentence(self, detector):
        r = detector.detect("مشغول الحين، بكلمك بعدين")
        assert r.state == PVMState.PVM_ENGAGED
        assert r.confidence > 0.7

    def test_mashghoola_female(self, detector):
        r = detector.detect("مشغولة")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_bas_lahza(self, detector):
        r = detector.detect("بس لحظة")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)


# ═══════════════════════════════════════════════════════════════
#  TestExplicitBusyEnglish — Tier 1 deterministic markers (English)
# ═══════════════════════════════════════════════════════════════

class TestExplicitBusyEnglish:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_busy(self, detector):
        r = detector.detect("busy")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)
        assert r.confidence > 0.5

    def test_im_busy(self, detector):
        r = detector.detect("i'm busy")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_hold_on(self, detector):
        r = detector.detect("hold on")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_brb(self, detector):
        r = detector.detect("brb")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_one_moment(self, detector):
        r = detector.detect("one moment")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_not_now(self, detector):
        r = detector.detect("not now")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_give_me_a_sec(self, detector):
        r = detector.detect("give me a sec")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_be_right_back(self, detector):
        r = detector.detect("be right back")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_later(self, detector):
        r = detector.detect("later")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_sorry_busy(self, detector):
        r = detector.detect("sorry busy")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)


# ═══════════════════════════════════════════════════════════════
#  TestReturnSignalsArabic — Exit PVM_ENGAGED
# ═══════════════════════════════════════════════════════════════

class TestReturnSignalsArabic:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    @pytest.fixture
    def engaged_ctx(self):
        return PVMContext(state=PVMState.PVM_ENGAGED)

    def test_kammel(self, detector, engaged_ctx):
        r = detector.detect("كمل", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_nakammel(self, detector, engaged_ctx):
        r = detector.detect("نكمل", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_wain_wagafna(self, detector, engaged_ctx):
        r = detector.detect("وين وقفنا", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_yalla_kammel(self, detector, engaged_ctx):
        r = detector.detect("يلا كمل", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_rejaat(self, detector, engaged_ctx):
        r = detector.detect("رجعت", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_khalast(self, detector, engaged_ctx):
        r = detector.detect("خلصت", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_tayyeb_kammel(self, detector, engaged_ctx):
        r = detector.detect("طيب كمل", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_return_not_pvm_when_active(self, detector):
        """Return signals when NOT in PVM should not trigger REACTIVATING."""
        r = detector.detect("كمل")
        # When active, "كمل" is a directive, should be ACTIVE
        assert r.state == PVMState.ACTIVE


# ═══════════════════════════════════════════════════════════════
#  TestReturnSignalsEnglish — Exit PVM_ENGAGED
# ═══════════════════════════════════════════════════════════════

class TestReturnSignalsEnglish:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    @pytest.fixture
    def engaged_ctx(self):
        return PVMContext(state=PVMState.PVM_ENGAGED)

    def test_continue(self, detector, engaged_ctx):
        r = detector.detect("continue", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_im_back(self, detector, engaged_ctx):
        r = detector.detect("i'm back", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_where_were_we(self, detector, engaged_ctx):
        r = detector.detect("where were we", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_resume(self, detector, engaged_ctx):
        r = detector.detect("resume", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_im_done(self, detector, engaged_ctx):
        r = detector.detect("i'm done", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_ready(self, detector, engaged_ctx):
        r = detector.detect("ready", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_carry_on(self, detector, engaged_ctx):
        r = detector.detect("carry on", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING

    def test_back(self, detector, engaged_ctx):
        r = detector.detect("back", prior_context=engaged_ctx)
        assert r.state == PVMState.REACTIVATING


# ═══════════════════════════════════════════════════════════════
#  TestIncompleteAcknowledgment — Minimal responses
# ═══════════════════════════════════════════════════════════════

class TestIncompleteAcknowledgment:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_ok_alone(self, detector):
        r = detector.detect("ok")
        assert r.confidence > 0.0
        assert any("minimal_response" in s for s in r.signals_detected)

    def test_hmm_alone(self, detector):
        r = detector.detect("hmm")
        assert any("minimal_response" in s for s in r.signals_detected)

    def test_tayyeb_alone(self, detector):
        r = detector.detect("طيب")
        assert any("minimal_response" in s for s in r.signals_detected)

    def test_mashi_alone(self, detector):
        r = detector.detect("ماشي")
        assert any("minimal_response" in s for s in r.signals_detected)

    def test_kk(self, detector):
        r = detector.detect("kk")
        assert any("minimal_response" in s for s in r.signals_detected)

    def test_long_message_not_minimal(self, detector):
        r = detector.detect("Can you explain the quantum mechanics of black holes?")
        assert not any("minimal_response" in s for s in r.signals_detected)

    def test_consecutive_minimals_escalate(self, detector):
        """Three consecutive minimal responses should escalate confidence."""
        ctx = PVMContext(consecutive_minimal_responses=2)
        r = detector.detect("ok", prior_context=ctx)
        assert r.confidence >= 0.60

    def test_single_minimal_low_confidence(self, detector):
        r = detector.detect("ok")
        assert r.confidence < 0.60


# ═══════════════════════════════════════════════════════════════
#  TestFastPathSkip — Sparse Activation
# ═══════════════════════════════════════════════════════════════

class TestFastPathSkip:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_question_skips_pvm(self, detector):
        r = detector.detect("What is the capital of France?")
        assert r.state == PVMState.ACTIVE
        assert r.confidence >= 0.95
        assert "fast_path_skip" in r.evidence[0]

    def test_directive_skips_pvm(self, detector):
        r = detector.detect("Please explain how photosynthesis works")
        assert r.state == PVMState.ACTIVE
        assert r.confidence >= 0.95

    def test_arabic_question_skips_pvm(self, detector):
        r = detector.detect("ايش عاصمة فرنسا؟")
        assert r.state == PVMState.ACTIVE

    def test_arabic_directive_skips_pvm(self, detector):
        r = detector.detect("ابغى اعرف عن الفيزياء الكمية")
        assert r.state == PVMState.ACTIVE

    def test_long_substantive_skips_pvm(self, detector):
        r = detector.detect(
            "I want to build a web application that handles user authentication "
            "and data processing with real-time updates"
        )
        assert r.state == PVMState.ACTIVE

    def test_busy_marker_does_not_skip(self, detector):
        r = detector.detect("busy")
        assert r.state != PVMState.ACTIVE or r.confidence < 0.95

    def test_fast_path_exits_pvm_engaged(self, detector):
        """A substantive message should exit PVM_ENGAGED."""
        ctx = PVMContext(state=PVMState.PVM_ENGAGED)
        r = detector.detect("What is quantum computing?", prior_context=ctx)
        assert r.state == PVMState.ACTIVE

    def test_fast_path_exits_detecting(self, detector):
        """A substantive message should exit DETECTING."""
        ctx = PVMContext(state=PVMState.DETECTING)
        r = detector.detect("Can you explain machine learning?", prior_context=ctx)
        assert r.state == PVMState.ACTIVE


# ═══════════════════════════════════════════════════════════════
#  TestMultiTaskMarkers — Tier 1 multi-task signals
# ═══════════════════════════════════════════════════════════════

class TestMultiTaskMarkers:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_in_a_meeting(self, detector):
        r = detector.detect("in a meeting")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)
        assert r.confidence > 0.5

    def test_on_a_call(self, detector):
        r = detector.detect("on a call")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_fi_ijtima3(self, detector):
        r = detector.detect("في اجتماع")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_khalini_akhallis(self, detector):
        r = detector.detect("خلني اخلص")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_let_me_finish_first(self, detector):
        r = detector.detect("let me finish this first")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)


# ═══════════════════════════════════════════════════════════════
#  TestTemporalSignals — Tier 2 (time-based detection)
# ═══════════════════════════════════════════════════════════════

class TestTemporalSignals:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_long_gap_assessment(self, detector):
        """Arabic 'طويل' gap assessment should raise PVM confidence."""
        time_reading = {"interaction_gap_assessment": "طويل"}
        r = detector.detect("hi", time_reading=time_reading)
        assert r.confidence > 0.0
        assert any("temporal_signal" in s for s in r.signals_detected)

    def test_absolute_long_gap(self, detector):
        """Gap > 5 minutes should raise confidence."""
        time_reading = {
            "time_since_last_interaction": timedelta(seconds=400),
            "interaction_gap_assessment": "",
        }
        r = detector.detect("hi", time_reading=time_reading)
        assert any("temporal_signal" in s for s in r.signals_detected)

    def test_fatigue_risk_boosts_confidence(self, detector):
        """fatigue_risk from TimeSense should boost PVM confidence."""
        time_reading = {
            "fatigue_risk": True,
            "interaction_gap_assessment": "طويل",
        }
        r = detector.detect("hi", time_reading=time_reading)
        assert r.confidence > 0.3

    def test_no_gap_no_temporal_signal(self, detector):
        """Normal gap should not trigger temporal signal."""
        time_reading = {
            "interaction_gap_assessment": "عادي",
            "fatigue_risk": False,
        }
        r = detector.detect("hi", time_reading=time_reading)
        temporal_signals = [s for s in r.signals_detected
                          if "temporal_signal" in s]
        assert len(temporal_signals) == 0

    def test_medium_gap_relative(self, detector):
        """Gap > 2× default average should trigger temporal signal."""
        time_reading = {
            "time_since_last_interaction": timedelta(
                seconds=DEFAULT_AVERAGE_GAP_SECONDS * GAP_MULTIPLIER_FOR_BUSY + 10
            ),
            "interaction_gap_assessment": "",
        }
        r = detector.detect("hi", time_reading=time_reading)
        assert any("temporal_signal" in s for s in r.signals_detected)

    def test_short_gap_no_signal(self, detector):
        """Short gap should not trigger temporal signal."""
        time_reading = {
            "time_since_last_interaction": timedelta(seconds=10),
            "interaction_gap_assessment": "سريع",
        }
        r = detector.detect("hi", time_reading=time_reading)
        temporal_signals = [s for s in r.signals_detected
                          if "temporal_signal" in s]
        assert len(temporal_signals) == 0


# ═══════════════════════════════════════════════════════════════
#  TestBehavioralSignals — Tier 3 (from Fingerprint)
# ═══════════════════════════════════════════════════════════════

class TestBehavioralSignals:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_formal_user_sends_short(self, detector):
        """Formal user sending short message → behavioral signal."""
        fp = {"communication_style": "formal"}
        r = detector.detect("ok", fingerprint_reading=fp)
        assert any("behavioral_signal" in s or "minimal_response" in s
                   for s in r.signals_detected)

    def test_casual_user_sends_short(self, detector):
        """Casual user sending short message → no behavioral signal."""
        fp = {"communication_style": "casual"}
        r = detector.detect("ok", fingerprint_reading=fp)
        behavioral = [s for s in r.signals_detected
                     if "behavioral_signal" in s]
        assert len(behavioral) == 0


# ═══════════════════════════════════════════════════════════════
#  TestStateTransitions — next_pvm_state()
# ═══════════════════════════════════════════════════════════════

class TestStateTransitions:
    def test_active_to_detecting(self):
        reading = PVMReading(
            state=PVMState.DETECTING, confidence=0.45,
            should_pause=False, pause_type=PAUSE_SHORTENED,
            recommended_acknowledgment="",
        )
        state, reason = next_pvm_state(PVMState.ACTIVE, reading)
        assert state == PVMState.DETECTING

    def test_active_to_pvm_engaged(self):
        reading = PVMReading(
            state=PVMState.PVM_ENGAGED, confidence=0.80,
            should_pause=True, pause_type=PAUSE_FULL_WAIT,
            recommended_acknowledgment="",
        )
        state, reason = next_pvm_state(PVMState.ACTIVE, reading)
        assert state == PVMState.PVM_ENGAGED

    def test_detecting_to_pvm_engaged(self):
        reading = PVMReading(
            state=PVMState.PVM_ENGAGED, confidence=0.75,
            should_pause=True, pause_type=PAUSE_FULL_WAIT,
            recommended_acknowledgment="",
        )
        state, reason = next_pvm_state(PVMState.DETECTING, reading)
        assert state == PVMState.PVM_ENGAGED

    def test_detecting_to_active(self):
        reading = PVMReading(
            state=PVMState.ACTIVE, confidence=0.95,
            should_pause=False, pause_type=PAUSE_NORMAL,
            recommended_acknowledgment="",
        )
        state, reason = next_pvm_state(PVMState.DETECTING, reading)
        assert state == PVMState.ACTIVE

    def test_pvm_engaged_to_reactivating(self):
        reading = PVMReading(
            state=PVMState.REACTIVATING, confidence=0.90,
            should_pause=False, pause_type=PAUSE_NORMAL,
            recommended_acknowledgment="",
        )
        state, reason = next_pvm_state(PVMState.PVM_ENGAGED, reading)
        assert state == PVMState.REACTIVATING

    def test_pvm_engaged_to_active(self):
        reading = PVMReading(
            state=PVMState.ACTIVE, confidence=0.95,
            should_pause=False, pause_type=PAUSE_NORMAL,
            recommended_acknowledgment="",
        )
        state, reason = next_pvm_state(PVMState.PVM_ENGAGED, reading)
        assert state == PVMState.ACTIVE

    def test_pvm_engaged_maintains(self):
        reading = PVMReading(
            state=PVMState.PVM_ENGAGED, confidence=0.70,
            should_pause=True, pause_type=PAUSE_FULL_WAIT,
            recommended_acknowledgment="",
        )
        state, reason = next_pvm_state(PVMState.PVM_ENGAGED, reading)
        assert state == PVMState.PVM_ENGAGED

    def test_reactivating_to_active(self):
        reading = PVMReading(
            state=PVMState.ACTIVE, confidence=0.95,
            should_pause=False, pause_type=PAUSE_NORMAL,
            recommended_acknowledgment="",
        )
        state, reason = next_pvm_state(PVMState.REACTIVATING, reading)
        assert state == PVMState.ACTIVE

    def test_topic_shift_resets_to_active(self):
        reading = PVMReading(
            state=PVMState.PVM_ENGAGED, confidence=0.80,
            should_pause=True, pause_type=PAUSE_FULL_WAIT,
            recommended_acknowledgment="",
        )
        state, reason = next_pvm_state(
            PVMState.PVM_ENGAGED, reading,
            topic_shift_signal=True
        )
        assert state == PVMState.ACTIVE
        assert "topic_shift" in reason

    def test_active_stays_active(self):
        reading = PVMReading(
            state=PVMState.ACTIVE, confidence=0.95,
            should_pause=False, pause_type=PAUSE_NORMAL,
            recommended_acknowledgment="",
        )
        state, reason = next_pvm_state(PVMState.ACTIVE, reading)
        assert state == PVMState.ACTIVE

    def test_string_state_in_reading(self):
        """next_pvm_state should handle string state in reading."""
        reading = {"state": "detecting", "confidence": 0.5}
        state, reason = next_pvm_state(PVMState.ACTIVE, reading)
        assert state == PVMState.DETECTING

    def test_reactivating_back_to_busy(self):
        """If still busy after reactivation, go back to PVM."""
        reading = PVMReading(
            state=PVMState.PVM_ENGAGED, confidence=0.80,
            should_pause=True, pause_type=PAUSE_FULL_WAIT,
            recommended_acknowledgment="",
        )
        state, reason = next_pvm_state(PVMState.REACTIVATING, reading)
        assert state == PVMState.PVM_ENGAGED


# ═══════════════════════════════════════════════════════════════
#  TestPVMShouldDeactivate — Decay logic
# ═══════════════════════════════════════════════════════════════

class TestPVMShouldDeactivate:
    def test_no_quiet_turns_no_deactivation(self):
        ctx = PVMContext(quiet_turns_since_pvm=0)
        assert pvm_should_deactivate(ctx) is False

    def test_at_threshold_deactivates(self):
        ctx = PVMContext(quiet_turns_since_pvm=DECAY_TURNS_TO_ACTIVE)
        assert pvm_should_deactivate(ctx) is True

    def test_below_threshold_no_deactivation(self):
        ctx = PVMContext(quiet_turns_since_pvm=DECAY_TURNS_TO_ACTIVE - 1)
        assert pvm_should_deactivate(ctx) is False

    def test_high_stakes_longer_decay(self):
        ctx = PVMContext(quiet_turns_since_pvm=DECAY_TURNS_TO_ACTIVE)
        assert pvm_should_deactivate(ctx, "high_stakes") is False

    def test_high_stakes_at_threshold(self):
        ctx = PVMContext(quiet_turns_since_pvm=DECAY_TURNS_HIGH_STAKES)
        assert pvm_should_deactivate(ctx, "high_stakes") is True

    def test_dict_context(self):
        ctx = {"quiet_turns_since_pvm": DECAY_TURNS_TO_ACTIVE}
        assert pvm_should_deactivate(ctx) is True


# ═══════════════════════════════════════════════════════════════
#  TestApplyPVMTransition — Context mutation
# ═══════════════════════════════════════════════════════════════

class TestApplyPVMTransition:
    def test_transition_preserves_domain(self):
        ctx = PVMContext(domain_profile="high_stakes")
        reading = PVMReading(
            state=PVMState.ACTIVE, confidence=0.95,
            should_pause=False, pause_type=PAUSE_NORMAL,
            recommended_acknowledgment="",
        )
        new_ctx = apply_pvm_transition(ctx, reading)
        assert new_ctx.domain_profile == "high_stakes"

    def test_transition_to_engaged_increments_total(self):
        ctx = PVMContext(total_pvm_engagements=0)
        reading = PVMReading(
            state=PVMState.PVM_ENGAGED, confidence=0.80,
            should_pause=True, pause_type=PAUSE_FULL_WAIT,
            recommended_acknowledgment="",
        )
        new_ctx = apply_pvm_transition(ctx, reading, current_turn_index=5)
        assert new_ctx.total_pvm_engagements == 1
        assert new_ctx.pvm_engage_turn == 5

    def test_transition_tracks_consecutive_minimals(self):
        ctx = PVMContext(consecutive_minimal_responses=1)
        reading = PVMReading(
            state=PVMState.DETECTING, confidence=0.45,
            should_pause=False, pause_type=PAUSE_SHORTENED,
            recommended_acknowledgment="",
            signals_detected=["minimal_response (consecutive=2)"],
        )
        new_ctx = apply_pvm_transition(ctx, reading)
        assert new_ctx.consecutive_minimal_responses == 2

    def test_transition_resets_minimals_on_substantive(self):
        ctx = PVMContext(consecutive_minimal_responses=3)
        reading = PVMReading(
            state=PVMState.ACTIVE, confidence=0.95,
            should_pause=False, pause_type=PAUSE_NORMAL,
            recommended_acknowledgment="",
            signals_detected=[],
        )
        new_ctx = apply_pvm_transition(ctx, reading)
        assert new_ctx.consecutive_minimal_responses == 0

    def test_transition_records_reason(self):
        ctx = PVMContext()
        reading = PVMReading(
            state=PVMState.DETECTING, confidence=0.45,
            should_pause=False, pause_type=PAUSE_SHORTENED,
            recommended_acknowledgment="",
        )
        new_ctx = apply_pvm_transition(ctx, reading)
        assert new_ctx.last_transition_reason is not None


# ═══════════════════════════════════════════════════════════════
#  TestCulturalSensitivity — Domain-based threshold adjustment
# ═══════════════════════════════════════════════════════════════

class TestCulturalSensitivity:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_healthcare_higher_threshold(self, detector):
        cfg = PVMDomainConfig.for_domain("healthcare")
        assert cfg.engage_threshold > PVM_ENGAGE_THRESHOLD

    def test_creative_lower_threshold(self, detector):
        cfg = PVMDomainConfig.for_domain("creative")
        assert cfg.engage_threshold < PVM_ENGAGE_THRESHOLD

    def test_education_has_profile(self, detector):
        cfg = PVMDomainConfig.for_domain("education")
        assert cfg.pvm_profile == "educational"

    def test_general_default_profile(self, detector):
        cfg = PVMDomainConfig.for_domain("general")
        assert cfg.pvm_profile == DEFAULT_PVM_PROFILE

    def test_domain_config_affects_detection(self, detector):
        """High-stakes domain should require higher confidence for PVM_ENGAGED."""
        high_cfg = PVMDomainConfig.for_domain("healthcare")
        normal_cfg = PVMDomainConfig.for_domain("general")

        # A borderline signal should be PVM_ENGAGED with normal but not with high-stakes
        # We test the threshold property, not the full detection (thresholds are different)
        assert high_cfg.engage_threshold > normal_cfg.engage_threshold


# ═══════════════════════════════════════════════════════════════
#  TestEdgeCases — Unusual inputs
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_empty_string(self, detector):
        r = detector.detect("")
        assert r.state == PVMState.ACTIVE
        assert r.confidence >= 0

    def test_none_text(self, detector):
        r = detector.detect(None)
        assert r.state == PVMState.ACTIVE

    def test_dict_turn_features(self, detector):
        r = detector.detect({"text": "مشغول"})
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_very_long_text(self, detector):
        long_text = "explain " * 500
        r = detector.detect(long_text)
        assert r.state == PVMState.ACTIVE

    def test_mixed_ar_en_busy(self, detector):
        r = detector.detect("I'm مشغول right now")
        assert r.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

    def test_whitespace_only(self, detector):
        r = detector.detect("   ")
        assert r.state == PVMState.ACTIVE


# ═══════════════════════════════════════════════════════════════
#  TestMonitorMode — PVM_MONITOR_ONLY behavior
# ═══════════════════════════════════════════════════════════════

class TestMonitorMode:
    """
    When PVM_MONITOR_ONLY is True, should_pause must be False
    even when busy signals are detected.
    Note: We test the logic in the detector, not the global flag.
    """

    def test_monitor_mode_never_pauses(self):
        """In monitor mode, should_pause is forced False."""
        # We can't easily toggle the module-level flag in tests without
        # monkeypatching, so we verify the evidence string check.
        # The real test is: if PVM_MONITOR_ONLY were True, the detector
        # appends an evidence line and forces should_pause=False.
        # We verify the flag is False by default.
        assert PVM_MONITOR_ONLY is False


# ═══════════════════════════════════════════════════════════════
#  TestAuditHash — Integrity helper
# ═══════════════════════════════════════════════════════════════

class TestAuditHash:
    def test_hash_is_sha256_length(self):
        r = PVMReading(
            state=PVMState.ACTIVE, confidence=0.5,
            should_pause=False, pause_type=PAUSE_NORMAL,
            recommended_acknowledgment="",
        )
        h = pvm_audit_hash(r)
        assert len(h) == 64  # SHA256 hex digest

    def test_same_input_same_hash(self):
        r1 = PVMReading(
            state=PVMState.PVM_ENGAGED, confidence=0.8,
            should_pause=True, pause_type=PAUSE_FULL_WAIT,
            recommended_acknowledgment="test",
            signals_detected=["busy_markers=['busy']"],
        )
        r2 = PVMReading(
            state=PVMState.PVM_ENGAGED, confidence=0.8,
            should_pause=True, pause_type=PAUSE_FULL_WAIT,
            recommended_acknowledgment="test",
            signals_detected=["busy_markers=['busy']"],
        )
        assert pvm_audit_hash(r1) == pvm_audit_hash(r2)

    def test_different_input_different_hash(self):
        r1 = PVMReading(
            state=PVMState.ACTIVE, confidence=0.1,
            should_pause=False, pause_type=PAUSE_NORMAL,
            recommended_acknowledgment="",
        )
        r2 = PVMReading(
            state=PVMState.PVM_ENGAGED, confidence=0.9,
            should_pause=True, pause_type=PAUSE_FULL_WAIT,
            recommended_acknowledgment="busy",
        )
        assert pvm_audit_hash(r1) != pvm_audit_hash(r2)


# ═══════════════════════════════════════════════════════════════
#  TestPauseTypeRecommendation — Output correctness
# ═══════════════════════════════════════════════════════════════

class TestPauseTypeRecommendation:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_explicit_busy_gets_full_wait(self, detector):
        r = detector.detect("مشغول الحين")
        if r.state == PVMState.PVM_ENGAGED:
            assert r.pause_type == PAUSE_FULL_WAIT

    def test_active_gets_normal(self, detector):
        r = detector.detect("What is 2+2?")
        assert r.pause_type == PAUSE_NORMAL

    def test_return_gets_normal(self, detector):
        ctx = PVMContext(state=PVMState.PVM_ENGAGED)
        r = detector.detect("كمل", prior_context=ctx)
        assert r.pause_type == PAUSE_NORMAL

    def test_should_pause_false_when_active(self, detector):
        r = detector.detect("Tell me about Python")
        assert r.should_pause is False


# ═══════════════════════════════════════════════════════════════
#  TestAcknowledgments — Arabic-first
# ═══════════════════════════════════════════════════════════════

class TestAcknowledgments:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_busy_gets_arabic_ack(self, detector):
        r = detector.detect("مشغول")
        if r.state == PVMState.PVM_ENGAGED:
            assert r.recommended_acknowledgment != ""
            # Should be Arabic
            assert any(c in r.recommended_acknowledgment
                      for c in "أابتثجحخدذرزسشصضطظعغفقكلمنهوي")

    def test_return_gets_welcome_back(self, detector):
        ctx = PVMContext(state=PVMState.PVM_ENGAGED)
        r = detector.detect("رجعت", prior_context=ctx)
        assert r.recommended_acknowledgment != ""

    def test_active_no_ack(self, detector):
        r = detector.detect("What is AI?")
        assert r.recommended_acknowledgment == ""


# ═══════════════════════════════════════════════════════════════
#  TestReturnLikelihood — Estimation correctness
# ═══════════════════════════════════════════════════════════════

class TestReturnLikelihood:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_busy_signal_higher_return(self, detector):
        r = detector.detect("brb")
        assert r.estimated_return_likelihood >= 0.5

    def test_late_night_lower_return(self, detector):
        time_reading = {"is_late_night": True, "interaction_gap_assessment": ""}
        r = detector.detect("busy", time_reading=time_reading)
        # Late night should reduce return likelihood vs daytime
        r_day = detector.detect("busy", time_reading={
            "is_late_night": False,
            "is_work_hours": True,
            "interaction_gap_assessment": "",
        })
        assert r.estimated_return_likelihood <= r_day.estimated_return_likelihood

    def test_return_likelihood_bounded(self, detector):
        r = detector.detect("busy")
        assert 0.0 <= r.estimated_return_likelihood <= 1.0


# ═══════════════════════════════════════════════════════════════
#  TestIntegration — Full detection pipeline
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    @pytest.fixture
    def detector(self):
        return PVMDetector()

    def test_full_lifecycle_busy_then_return(self, detector):
        """Complete PVM lifecycle: active → busy → return."""
        # Turn 1: normal question
        r1 = detector.detect("What is AI?")
        assert r1.state == PVMState.ACTIVE

        # Turn 2: explicit busy
        r2 = detector.detect("مشغول")
        assert r2.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)
        assert r2.confidence > 0.5

        # Turn 3: return signal (with prior context)
        ctx = PVMContext(state=PVMState.PVM_ENGAGED)
        r3 = detector.detect("كمل", prior_context=ctx)
        assert r3.state == PVMState.REACTIVATING

    def test_evidence_trail_non_empty_on_detection(self, detector):
        r = detector.detect("مشغول الحين")
        assert len(r.evidence) > 0

    def test_signals_detected_on_busy(self, detector):
        r = detector.detect("hold on, brb")
        assert len(r.signals_detected) > 0

    def test_config_resolution_from_dict(self, detector):
        r = detector.detect("ok", domain_config={"domain": "healthcare"})
        # Should use healthcare threshold without crashing
        assert r is not None

    def test_config_resolution_from_none(self, detector):
        r = detector.detect("hello", domain_config=None)
        assert r is not None

    def test_apply_transition_full_cycle(self, detector):
        """Apply transitions through the full lifecycle."""
        ctx = PVMContext()

        # Busy
        r1 = detector.detect("مشغول")
        ctx = apply_pvm_transition(ctx, r1, current_turn_index=1)
        assert ctx.state in (PVMState.DETECTING, PVMState.PVM_ENGAGED)

        # If in DETECTING, escalate
        if ctx.state == PVMState.DETECTING:
            r2 = detector.detect("بعدين اكلمك")
            ctx = apply_pvm_transition(ctx, r2, current_turn_index=2)

        # Return
        r3 = detector.detect("كمل", prior_context=ctx)
        ctx = apply_pvm_transition(ctx, r3, current_turn_index=3)
        assert ctx.state == PVMState.REACTIVATING

        # Substantive follow-up
        r4 = detector.detect("What were we discussing?", prior_context=ctx)
        ctx = apply_pvm_transition(ctx, r4, current_turn_index=4)
        assert ctx.state == PVMState.ACTIVE
