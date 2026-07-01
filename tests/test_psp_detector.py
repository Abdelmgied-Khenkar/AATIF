"""
Test suite for FN#070 Possibility Space Preservation — aatif_psp_detector.py

Tests the PSPDetector (observational, stylistic), PSPReading/LivePath
dataclasses, the bounded-set policy, domain-specific behaviour, multi-intent
per-sub-intent PSP, prompted-closure detection, and — critically — the
false-positive rate on factual queries (Sparse Activation fast-path).

Architecture under test (B-prime):
  PSPContext     →  pure storage (prior live paths, rejected paths)
  PSPDetector    →  observational, STYLISTIC, NOT safety
  PSPReading     →  output (no psp_mode — that is config, not computation)

Design rule: FN#070 binds through B5 (Behaviour), never touches S/H/θ/S-equation.
Design consensus: Claude × ChatGPT, 2026-06-30
"""

import pytest

from aatif_psp_detector import (
    PSPDetector,
    PSPReading,
    LivePath,
    PSPContext,
    DomainPSPConfig,
    PSP_ENABLED,
    PSP_GATE_CHECK_ENABLED,
    PSP_GATE_MODE,
    FAST_PATH_SKIP_THRESHOLD,
    DECISION_CONFIDENCE_THRESHOLD,
    BOUNDED_SIMPLE,
    BOUNDED_DEFAULT,
    BOUNDED_HIGH_STAKES,
    BOUNDED_CREATIVE,
    BOUNDED_HARD_MAX,
    TRADEOFF_REQUIRED_THRESHOLD,
    PSP_PROFILE_BY_DOMAIN,
    PSPState,
    next_psp_state,
    psp_should_deactivate,
    DEACTIVATION_TURNS_GENERAL,
    DEACTIVATION_TURNS_HIGH_STAKES,
)


# ═══════════════════════════════════════════════════════════════
#  TestFeatureFlags — FN#070 ships OFF by default
# ═══════════════════════════════════════════════════════════════

class TestFeatureFlags:
    def test_psp_disabled_by_default(self):
        assert PSP_ENABLED is False, "PSP_ENABLED must default to False"

    def test_gate_check_disabled_by_default(self):
        assert PSP_GATE_CHECK_ENABLED is False, \
            "PSP_GATE_CHECK_ENABLED must default to False"

    def test_gate_mode_monitor_by_default(self):
        assert PSP_GATE_MODE == "monitor", \
            'PSP_GATE_MODE must default to "monitor" (log, never block)'


# ═══════════════════════════════════════════════════════════════
#  TestDataclasses — PSPReading / LivePath / PSPContext defaults
# ═══════════════════════════════════════════════════════════════

class TestDataclasses:
    def test_live_path_minimal(self):
        p = LivePath(label="surgery")
        assert p.label == "surgery"
        assert p.summary == ""
        assert p.tradeoff is None

    def test_psp_reading_defaults(self):
        r = PSPReading(is_decision_point=False, decision_confidence=0.0,
                       closure_risk=0.0)
        assert r.live_paths == []
        assert r.bounded_count == 0
        assert r.user_requested_closure is False
        assert r.evidence == []

    def test_psp_reading_has_no_psp_mode(self):
        """psp_mode is config, not detector output — it must NOT be a field."""
        r = PSPReading(is_decision_point=True, decision_confidence=0.8,
                       closure_risk=0.7)
        assert not hasattr(r, "psp_mode"), \
            "PSPReading must not carry psp_mode — it comes from domain config"

    def test_tradeoffs_required_property(self):
        low = PSPReading(is_decision_point=True, decision_confidence=0.8,
                         closure_risk=0.4)
        high = PSPReading(is_decision_point=True, decision_confidence=0.8,
                          closure_risk=0.7)
        assert low.tradeoffs_required is False
        assert high.tradeoffs_required is True

    def test_psp_context_defaults(self):
        ctx = PSPContext()
        assert ctx.live_paths == []
        assert ctx.rejected_paths == []
        assert ctx.prior_decision_active is False

    def test_domain_config_for_domain(self):
        cfg = DomainPSPConfig.for_domain("healthcare")
        assert cfg.psp_profile == "high"
        assert cfg.high_stakes is True
        cfg2 = DomainPSPConfig.for_domain("general")
        assert cfg2.psp_profile == "medium"
        assert cfg2.high_stakes is False


# ═══════════════════════════════════════════════════════════════
#  TestDetectReturnShape
# ═══════════════════════════════════════════════════════════════

class TestDetectReturnShape:
    def test_returns_psp_reading(self):
        det = PSPDetector()
        r = det.detect("should I take the job or not?")
        assert isinstance(r, PSPReading)
        assert isinstance(r.is_decision_point, bool)
        assert isinstance(r.decision_confidence, float)
        assert isinstance(r.closure_risk, float)
        assert isinstance(r.live_paths, list)
        assert isinstance(r.bounded_count, int)
        assert isinstance(r.evidence, list)

    def test_confidence_in_range(self):
        det = PSPDetector()
        for text in ["should I quit?", "ما هو الماء", "محتار", "hello", ""]:
            r = det.detect(text)
            assert 0.0 <= r.decision_confidence <= 1.0
            assert 0.0 <= r.closure_risk <= 1.0


# ═══════════════════════════════════════════════════════════════
#  TestDecisionDetectionEnglish
# ═══════════════════════════════════════════════════════════════

class TestDecisionDetectionEnglish:
    @pytest.mark.parametrize("text", [
        "Should I accept the offer?",
        "Which one is better for me?",
        "What's best for a beginner?",
        "Help me decide between Python and Rust",
        "Can you give me the pros and cons?",
        "I'm torn between two apartments",
        "Should I rent or buy?",
    ])
    def test_english_decision_points(self, text):
        det = PSPDetector()
        r = det.detect(text, domain_config=DomainPSPConfig.for_domain("general"))
        assert r.is_decision_point is True, f"should detect decision: {text!r}"
        assert r.decision_confidence >= DECISION_CONFIDENCE_THRESHOLD


# ═══════════════════════════════════════════════════════════════
#  TestDecisionDetectionArabic
# ═══════════════════════════════════════════════════════════════

class TestDecisionDetectionArabic:
    @pytest.mark.parametrize("text", [
        "أبغى أستخير بخصوص الزواج",
        "ودي أستشير أحد في القرار",
        "تنصحني أسافر ولا أكمل دراستي؟",
        "ايش الأفضل لي أبدأ بالعمل ولا الماجستير؟",
        "أنا محتار بين وظيفتين",
        "كيف أختار التخصص المناسب؟",
        "وش رايك أتوكل وأبدأ المشروع؟",
    ])
    def test_arabic_decision_points(self, text):
        det = PSPDetector()
        r = det.detect(text, domain_config=DomainPSPConfig.for_domain("general"))
        assert r.is_decision_point is True, f"should detect decision: {text!r}"
        assert r.decision_confidence >= DECISION_CONFIDENCE_THRESHOLD

    def test_arabic_normalization_robustness(self):
        """Diacritics / alef variants must not defeat marker matching."""
        det = PSPDetector()
        r = det.detect("أنا مُحتار بين خيارين")  # diacritic on محتار
        assert r.is_decision_point is True


# ═══════════════════════════════════════════════════════════════
#  TestFastPathSkip — Sparse Activation
# ═══════════════════════════════════════════════════════════════

class TestFastPathSkip:
    def test_factual_query_skips(self):
        det = PSPDetector()
        r = det.detect("What is the capital of France?")
        assert r.is_decision_point is False
        assert any("fast_path_skip" in e for e in r.evidence)

    def test_arabic_factual_skips(self):
        det = PSPDetector()
        r = det.detect("ما هو الذكاء الاصطناعي؟")
        assert r.is_decision_point is False
        assert any("fast_path_skip" in e for e in r.evidence)

    def test_greeting_skips(self):
        det = PSPDetector()
        for g in ["hello", "مرحبا", "thanks", "good morning"]:
            r = det.detect(g)
            assert r.is_decision_point is False, f"greeting should skip: {g!r}"

    def test_fast_path_skips_embedding(self):
        """When deterministic confidence is high, the embedder must NOT run."""
        class SpyEmbedder:
            def __init__(self):
                self.called = False

            def decision_similarity(self, text):
                self.called = True
                return 0.99

        spy = SpyEmbedder()
        det = PSPDetector(embedder=spy)
        det.detect("What is the boiling point of water?")
        assert spy.called is False, "embedder must be skipped on the fast path"

    def test_decision_marker_defeats_fast_path(self):
        """A factual-looking question that is actually a decision must NOT skip."""
        det = PSPDetector()
        r = det.detect("What is best: surgery or therapy?")
        assert r.is_decision_point is True


# ═══════════════════════════════════════════════════════════════
#  TestFalsePositiveRate — factual questions must not trigger PSP
# ═══════════════════════════════════════════════════════════════

class TestFalsePositiveRate:
    FACTUAL_QUERIES = [
        "What is the capital of Japan?",
        "Who wrote Hamlet?",
        "When did World War II end?",
        "How many planets are in the solar system?",
        "Define photosynthesis",
        "Explain how a transistor works",
        "What time is it in Tokyo?",
        "Tell me about the Roman Empire",
        "ما هو عدد سكان مصر؟",
        "متى تأسست الدولة السعودية؟",
        "وش معنى كلمة استدامة؟",
        "اشرح لي كيف يعمل المحرك",
        "من هو مخترع الهاتف؟",
        "كم يبعد القمر عن الأرض؟",
        "hello there",
        "thank you so much",
        "صباح الخير",
        "السلام عليكم",
    ]

    def test_false_positive_rate_under_5_percent(self):
        det = PSPDetector()
        false_positives = []
        for q in self.FACTUAL_QUERIES:
            r = det.detect(q, domain_config=DomainPSPConfig.for_domain("general"))
            if r.is_decision_point:
                false_positives.append(q)
        rate = len(false_positives) / len(self.FACTUAL_QUERIES)
        assert rate < 0.05, \
            f"false-positive rate {rate:.2%} exceeds 5%: {false_positives}"


# ═══════════════════════════════════════════════════════════════
#  TestBoundedSet — system proposes, human closes (Schwartz paradox)
# ═══════════════════════════════════════════════════════════════

class TestBoundedSet:
    def test_default_count(self):
        det = PSPDetector()
        r = det.detect("should I rent or buy?",
                       domain_config=DomainPSPConfig.for_domain("general"))
        assert r.bounded_count == BOUNDED_DEFAULT == 3

    def test_simple_count(self):
        det = PSPDetector()
        cfg = DomainPSPConfig(domain="general", psp_profile="medium",
                              complexity="simple")
        r = det.detect("should I, yes or no?", domain_config=cfg)
        assert r.bounded_count == BOUNDED_SIMPLE == 2

    def test_high_stakes_count(self):
        det = PSPDetector()
        r = det.detect("should I have the surgery?",
                       domain_config=DomainPSPConfig.for_domain("healthcare"))
        assert r.bounded_count == BOUNDED_HIGH_STAKES
        assert 3 <= r.bounded_count <= 4

    def test_creative_count(self):
        det = PSPDetector()
        r = det.detect("which plot twist should I use?",
                       domain_config=DomainPSPConfig.for_domain("creative"))
        assert r.bounded_count == BOUNDED_CREATIVE == 5

    def test_hard_max_never_exceeded(self):
        det = PSPDetector()
        for domain in ["healthcare", "creative", "education", "general", "legal"]:
            r = det.detect("which one should I choose?",
                           domain_config=DomainPSPConfig.for_domain(domain))
            assert r.bounded_count <= BOUNDED_HARD_MAX == 5

    def test_turn_complexity_overrides_config(self):
        det = PSPDetector()
        cfg = DomainPSPConfig.for_domain("general")
        r = det.detect({"text": "which one?", "complexity": "creative"},
                       domain_config=cfg)
        assert r.bounded_count == BOUNDED_CREATIVE


# ═══════════════════════════════════════════════════════════════
#  TestDomainBehaviour — psp_profile drives closure_risk
# ═══════════════════════════════════════════════════════════════

class TestDomainBehaviour:
    def test_profile_lookup_table(self):
        assert PSP_PROFILE_BY_DOMAIN["healthcare"] == "high"
        assert PSP_PROFILE_BY_DOMAIN["education"] == "high"
        assert PSP_PROFILE_BY_DOMAIN["general"] == "medium"
        assert PSP_PROFILE_BY_DOMAIN["creative"] == "adaptive"

    def test_healthcare_high_closure_risk(self):
        det = PSPDetector()
        r = det.detect("should I have the surgery or wait?",
                       domain_config=DomainPSPConfig.for_domain("healthcare"))
        assert r.closure_risk > TRADEOFF_REQUIRED_THRESHOLD
        assert r.tradeoffs_required is True

    def test_general_lower_closure_risk(self):
        det = PSPDetector()
        r = det.detect("should I get the blue or red shirt?",
                       domain_config=DomainPSPConfig.for_domain("general"))
        assert r.closure_risk <= TRADEOFF_REQUIRED_THRESHOLD
        assert r.tradeoffs_required is False

    def test_healthcare_higher_than_general(self):
        det = PSPDetector()
        hc = det.detect("which one should I choose?",
                        domain_config=DomainPSPConfig.for_domain("healthcare"))
        gen = det.detect("which one should I choose?",
                         domain_config=DomainPSPConfig.for_domain("general"))
        assert hc.closure_risk > gen.closure_risk

    def test_psp_mode_not_computed(self):
        """The detector reads psp_profile; it must never invent psp_mode."""
        det = PSPDetector()
        r = det.detect("which one should I pick?",
                       domain_config=DomainPSPConfig.for_domain("healthcare"))
        assert not hasattr(r, "psp_mode")
        # evidence should attribute the profile to config lookup
        assert any("config lookup" in e for e in r.evidence)


# ═══════════════════════════════════════════════════════════════
#  TestUserRequestedClosure — prompted closure is allowed
# ═══════════════════════════════════════════════════════════════

class TestUserRequestedClosure:
    @pytest.mark.parametrize("text", [
        "Which one should I pick? Just tell me.",
        "Stop listing options, just pick one for me.",
        "Decide for me — which is best?",
        "Give me your recommendation, one answer only.",
    ])
    def test_english_prompted_closure(self, text):
        det = PSPDetector()
        r = det.detect(text, domain_config=DomainPSPConfig.for_domain("general"))
        assert r.user_requested_closure is True

    @pytest.mark.parametrize("text", [
        "محتار، اختار لي وحدة بس",
        "خلاص قرر لي وش الأفضل",
        "عطني توصيتك المباشرة",
    ])
    def test_arabic_prompted_closure(self, text):
        det = PSPDetector()
        r = det.detect(text, domain_config=DomainPSPConfig.for_domain("general"))
        assert r.user_requested_closure is True

    def test_unprompted_does_not_request_closure(self):
        det = PSPDetector()
        r = det.detect("should I rent or buy a home?",
                       domain_config=DomainPSPConfig.for_domain("general"))
        assert r.user_requested_closure is False

    def test_prompted_closure_dampens_closure_risk(self):
        """Prompted closure is sanctioned → lowers *premature*-closure risk."""
        det = PSPDetector()
        prompted = det.detect("which one is best — surgery or therapy? just tell me one.",
                              domain_config=DomainPSPConfig.for_domain("healthcare"))
        unprompted = det.detect("which one is best — surgery or therapy for me?",
                                domain_config=DomainPSPConfig.for_domain("healthcare"))
        assert prompted.is_decision_point and unprompted.is_decision_point
        assert prompted.closure_risk < unprompted.closure_risk


# ═══════════════════════════════════════════════════════════════
#  TestLivePaths — mutable bounded set
# ═══════════════════════════════════════════════════════════════

class TestLivePaths:
    def test_prior_paths_carried_forward(self):
        det = PSPDetector()
        ctx = PSPContext(
            live_paths=[LivePath("Option A"), LivePath("Option B")],
            prior_decision_active=True,
        )
        r = det.detect("hmm not sure which to choose", prior_context=ctx)
        labels = [p.label for p in r.live_paths]
        assert "Option A" in labels and "Option B" in labels

    def test_user_introduces_new_path(self):
        """When the human raises a new path, the reading updates."""
        det = PSPDetector()
        ctx = PSPContext(
            live_paths=[LivePath("Option A"), LivePath("Option B")],
            prior_decision_active=True,
        )
        r = det.detect("which one? what about Option C", prior_context=ctx)
        labels = [p.label.lower() for p in r.live_paths]
        assert any("option c" in lab for lab in labels), \
            f"new user path should be tracked, got {labels}"

    def test_rejected_path_dropped(self):
        det = PSPDetector()
        ctx = PSPContext(
            live_paths=[LivePath("Option A"), LivePath("Option B")],
            rejected_paths=["Option A"],
            prior_decision_active=True,
        )
        r = det.detect("which of these should I choose?", prior_context=ctx)
        labels = [p.label for p in r.live_paths]
        assert "Option A" not in labels
        assert "Option B" in labels

    def test_live_paths_capped_at_hard_max(self):
        det = PSPDetector()
        ctx = PSPContext(
            live_paths=[LivePath(f"Opt{i}") for i in range(8)],
            prior_decision_active=True,
        )
        r = det.detect("which one should I choose?", prior_context=ctx)
        assert len(r.live_paths) <= BOUNDED_HARD_MAX

    def test_context_alone_activates_psp(self):
        """An active prior decision keeps PSP live even without fresh markers."""
        det = PSPDetector()
        ctx = PSPContext(prior_decision_active=True)
        r = det.detect("hmm, I really am not sure here", prior_context=ctx)
        assert r.is_decision_point is True
        assert any("context" in e for e in r.evidence)


# ═══════════════════════════════════════════════════════════════
#  TestMultiIntent — FN#036 first, PSP per sub-intent
# ═══════════════════════════════════════════════════════════════

class TestMultiIntent:
    def test_per_sub_intent_readings(self):
        det = PSPDetector()
        turn = {
            "text": "combined",
            "sub_intents": [
                "What is the capital of France?",   # factual → no PSP
                "Should I move to Paris or Lyon?",  # decision → PSP
            ],
        }
        readings = det.detect_multi(
            turn, domain_config=DomainPSPConfig.for_domain("general"))
        assert len(readings) == 2
        assert readings[0].is_decision_point is False
        assert readings[1].is_decision_point is True

    def test_multi_falls_back_to_single(self):
        det = PSPDetector()
        readings = det.detect_multi("should I rent or buy?")
        assert len(readings) == 1
        assert isinstance(readings[0], PSPReading)

    def test_mixed_intent_not_all_or_nothing(self):
        """A decision sub-intent activates PSP without dragging the factual one in."""
        det = PSPDetector()
        turn = {
            "text": "x",
            "sub_intents": ["define osmosis", "which textbook should I buy?"],
        }
        readings = det.detect_multi(
            turn, domain_config=DomainPSPConfig.for_domain("education"))
        decision_flags = [r.is_decision_point for r in readings]
        assert decision_flags == [False, True]


# ═══════════════════════════════════════════════════════════════
#  TestEmbeddingTier — Tier 2 only when deterministic is inconclusive
# ═══════════════════════════════════════════════════════════════

class TestEmbeddingTier:
    def test_embedding_runs_when_ambiguous(self):
        """No deterministic marker, ambiguous text → embedder consulted."""
        class Embedder:
            def __init__(self):
                self.called = False

            def decision_similarity(self, text):
                self.called = True
                return 0.80

        emb = Embedder()
        det = PSPDetector(embedder=emb)
        # ambiguous: no decision/factual markers, long enough to dodge skip
        r = det.detect("I keep going back and forth on this whole situation lately")
        assert emb.called is True
        assert r.is_decision_point is True
        assert any("embedding" in e for e in r.evidence)

    def test_works_without_embedder(self):
        """CI without Ollama: detector must function on tiers 1 & 3 alone."""
        det = PSPDetector(embedder=None)
        r = det.detect("should I take the job or stay?")
        assert r.is_decision_point is True


# ═══════════════════════════════════════════════════════════════
#  TestSafetyIsolation — FN#070 is stylistic, never safety
# ═══════════════════════════════════════════════════════════════

class TestSafetyIsolation:
    def test_reading_has_no_safety_fields(self):
        """PSPReading must not expose S/H/θ-like safety fields."""
        det = PSPDetector()
        r = det.detect("which one should I choose?")
        for forbidden in ("S", "H", "theta", "θ", "harm_score", "gate",
                          "decision_safety", "psp_mode"):
            assert not hasattr(r, forbidden), \
                f"PSPReading must not carry safety field {forbidden!r}"

    def test_detection_is_pure_no_state_mutation(self):
        """detect() must not mutate the prior_context it is handed."""
        det = PSPDetector()
        ctx = PSPContext(live_paths=[LivePath("A")], prior_decision_active=True)
        before = len(ctx.live_paths)
        det.detect("which one? what about B", prior_context=ctx)
        assert len(ctx.live_paths) == before, \
            "detect() must not mutate the caller's context"


# ═══════════════════════════════════════════════════════════════
#  TestConstants — calibration values match the consensus
# ═══════════════════════════════════════════════════════════════

class TestConstants:
    def test_fast_path_threshold(self):
        assert FAST_PATH_SKIP_THRESHOLD == 0.95

    def test_bounded_values(self):
        assert BOUNDED_SIMPLE == 2
        assert BOUNDED_DEFAULT == 3
        assert 3 <= BOUNDED_HIGH_STAKES <= 4
        assert BOUNDED_CREATIVE == 5
        assert BOUNDED_HARD_MAX == 5

    def test_tradeoff_threshold(self):
        assert TRADEOFF_REQUIRED_THRESHOLD == 0.5


# ═══════════════════════════════════════════════════════════════
#  TestPSPState — the decision-space lifecycle enum (FN#070 v1)
# ═══════════════════════════════════════════════════════════════

class TestPSPState:
    def test_all_states_present(self):
        names = {s.name for s in PSPState}
        assert names == {
            "DORMANT", "DETECTED", "EXPLORING",
            "NARROWING", "CLOSURE_REQUESTED", "CLOSED",
        }

    def test_context_defaults_to_dormant(self):
        ctx = PSPContext()
        assert ctx.state is PSPState.DORMANT
        assert ctx.decision_topic is None
        assert ctx.user_requested_closure is False
        assert ctx.last_psp_turn_index == -1
        assert ctx.last_decision_marker_turn_index == -1
        assert ctx.last_transition_reason is None

    def test_context_minimum_v1_fields_exist(self):
        """The consensus minimum v1 field set must all be present."""
        ctx = PSPContext()
        for f in ("state", "decision_topic", "live_paths", "rejected_paths",
                  "user_requested_closure", "last_psp_turn_index",
                  "last_decision_marker_turn_index", "domain_profile",
                  "last_transition_reason"):
            assert hasattr(ctx, f), f"PSPContext missing v1 field {f!r}"


# ═══════════════════════════════════════════════════════════════
#  TestStateTransitions — next_psp_state() covers every valid edge
# ═══════════════════════════════════════════════════════════════

def _reading(is_dp=False, requested_closure=False):
    return PSPReading(
        is_decision_point=is_dp,
        decision_confidence=0.8 if is_dp else 0.0,
        closure_risk=0.5 if is_dp else 0.0,
        user_requested_closure=requested_closure,
    )


class TestStateTransitions:
    def test_dormant_to_detected(self):
        state, reason = next_psp_state(PSPState.DORMANT, _reading(is_dp=True))
        assert state is PSPState.DETECTED
        assert reason == "decision_markers_found"

    def test_dormant_stays_dormant(self):
        state, reason = next_psp_state(PSPState.DORMANT, _reading(is_dp=False))
        assert state is PSPState.DORMANT

    def test_detected_to_exploring(self):
        state, reason = next_psp_state(PSPState.DETECTED, _reading(is_dp=True))
        assert state is PSPState.EXPLORING
        assert reason == "alternatives_presented"

    def test_exploring_to_narrowing_on_rejection(self):
        state, reason = next_psp_state(
            PSPState.EXPLORING, _reading(is_dp=True),
            user_turn_features="I prefer the first one, drop the others")
        assert state is PSPState.NARROWING
        assert reason == "user_rejecting_or_preferring"

    def test_narrowing_to_closure_requested(self):
        state, reason = next_psp_state(
            PSPState.NARROWING, _reading(is_dp=True, requested_closure=True),
            user_turn_features="ok just pick one for me")
        assert state is PSPState.CLOSURE_REQUESTED
        assert reason == "user_requested_closure"

    def test_closure_requested_to_closed(self):
        """After closure is requested, the next turn delivers closure → CLOSED."""
        state, reason = next_psp_state(
            PSPState.CLOSURE_REQUESTED, _reading(is_dp=False))
        assert state is PSPState.CLOSED
        assert reason == "closure_delivered"

    def test_any_to_closed_on_topic_shift(self):
        for s in PSPState:
            state, reason = next_psp_state(
                s, _reading(is_dp=True), topic_shift_signal=True)
            assert state is PSPState.CLOSED
            assert reason == "topic_shift"

    def test_any_to_closed_on_user_decided(self):
        state, reason = next_psp_state(
            PSPState.EXPLORING, _reading(is_dp=False),
            user_turn_features="thanks, I decided — I'll go with option B")
        assert state is PSPState.CLOSED
        assert reason == "user_decided"

    def test_arabic_user_decided_closes(self):
        state, reason = next_psp_state(
            PSPState.EXPLORING, _reading(is_dp=False),
            user_turn_features="خلاص قررت بروح على الطب")
        assert state is PSPState.CLOSED
        assert reason == "user_decided"

    def test_closed_reopens_on_new_decision(self):
        state, reason = next_psp_state(PSPState.CLOSED, _reading(is_dp=True))
        assert state is PSPState.DETECTED
        assert reason == "new_decision_after_close"

    def test_single_quiet_turn_does_not_close(self):
        """A single non-decision turn must NOT drop an active decision context."""
        for s in (PSPState.DETECTED, PSPState.EXPLORING, PSPState.NARROWING):
            state, _ = next_psp_state(s, _reading(is_dp=False),
                                      user_turn_features="hmm let me think")
            assert state is s, f"{s} should hold on a single quiet turn"

    def test_none_current_state_treated_as_dormant(self):
        state, _ = next_psp_state(None, _reading(is_dp=True))
        assert state is PSPState.DETECTED


# ═══════════════════════════════════════════════════════════════
#  TestDeactivation — hybrid N-turn policy (consensus §Q4)
# ═══════════════════════════════════════════════════════════════

class TestDeactivation:
    def test_general_deactivates_after_three_quiet_turns(self):
        assert psp_should_deactivate(2, "medium") is False
        assert psp_should_deactivate(3, "medium") is True
        assert DEACTIVATION_TURNS_GENERAL == 3

    def test_high_stakes_holds_longer(self):
        assert psp_should_deactivate(3, "high") is False
        assert psp_should_deactivate(5, "high") is True
        assert DEACTIVATION_TURNS_HIGH_STAKES == 5

    def test_creative_holds_like_high_stakes(self):
        """Creative (adaptive) keeps ideation open longer."""
        assert psp_should_deactivate(3, "adaptive") is False
        assert psp_should_deactivate(5, "adaptive") is True

    def test_closure_answered_deactivates_immediately(self):
        assert psp_should_deactivate(0, "high", closure_answered=True) is True

    def test_topic_shift_deactivates_immediately(self):
        assert psp_should_deactivate(0, "medium", topic_shift=True) is True


# ═══════════════════════════════════════════════════════════════
#  TestObjectiveSuppression — factual spec comparisons are NOT PSP
# ═══════════════════════════════════════════════════════════════

class TestObjectiveSuppression:
    @pytest.mark.parametrize("text", [
        "Which one is cheaper and faster?",
        "Which is faster, the M2 or the M3?",
        "Which phone has more RAM?",
        "Compare the specs of the two laptops",
        "Which one has a bigger battery life?",
    ])
    def test_objective_comparisons_not_flagged(self, text):
        det = PSPDetector()
        r = det.detect(text, domain_config=DomainPSPConfig.for_domain("general"))
        assert r.is_decision_point is False, \
            f"objective comparison must not be a decision point: {text!r}"

    def test_suppressor_leaves_evidence(self):
        det = PSPDetector()
        r = det.detect("Which one is cheaper and faster?",
                       domain_config=DomainPSPConfig.for_domain("general"))
        assert any("objective_comparison_suppressor" in e for e in r.evidence)

    def test_personal_marker_overrides_suppressor(self):
        """'for my family' turns a spec comparison back into a decision."""
        det = PSPDetector()
        r = det.detect("Which laptop is cheaper for my family?",
                       domain_config=DomainPSPConfig.for_domain("general"))
        assert r.is_decision_point is True
        assert any("personal_choice_markers" in e for e in r.evidence)

    def test_strong_decision_plus_objective_reduces_not_suppresses(self):
        """Two decision markers + objective → reduced confidence, still a decision."""
        det = PSPDetector()
        r = det.detect(
            "Should I buy it? Which one do you recommend — the cheaper one?",
            domain_config=DomainPSPConfig.for_domain("general"))
        assert r.is_decision_point is True


# ═══════════════════════════════════════════════════════════════
#  TestPersonalDecisionDetection — personal-choice markers ARE PSP
# ═══════════════════════════════════════════════════════════════

class TestPersonalDecisionDetection:
    @pytest.mark.parametrize("text", [
        "Based on my situation, which laptop should I get?",
        "Which fits me better, the SUV or the sedan?",
        "Do you recommend the job offer for me?",
        "Help me decide what's best for my family.",
    ])
    def test_personal_decisions_flagged(self, text):
        det = PSPDetector()
        r = det.detect(text, domain_config=DomainPSPConfig.for_domain("general"))
        assert r.is_decision_point is True, f"personal decision missed: {text!r}"


# ═══════════════════════════════════════════════════════════════
#  TestArabicDialectMarkers — dialectal PSP coverage (consensus §A4)
# ═══════════════════════════════════════════════════════════════

class TestArabicDialectMarkers:
    @pytest.mark.parametrize("text", [
        "ايش تشوف اسافر ولا اكمل؟",
        "احترت بين وظيفتين",
        "ايهم افضل الطب ولا الهندسه؟",
        "اكمل ولا اوقف؟",
        "مدري اسوي كذا ولا كذا",
        "وش تشوف اختار ايش؟",
    ])
    def test_dialect_decision_points(self, text):
        det = PSPDetector()
        r = det.detect(text, domain_config=DomainPSPConfig.for_domain("general"))
        assert r.is_decision_point is True, f"dialect decision missed: {text!r}"

    @pytest.mark.parametrize("text", [
        "قررلي وش اسوي",
        "خلاص اختار لي وحده",
    ])
    def test_dialect_prompted_closure(self, text):
        det = PSPDetector()
        r = det.detect(text, domain_config=DomainPSPConfig.for_domain("general"))
        assert r.user_requested_closure is True, \
            f"dialect closure request missed: {text!r}"


# ═══════════════════════════════════════════════════════════════
#  TestPromptedClosureBypass — prompted closure allowed, not violation
# ═══════════════════════════════════════════════════════════════

class TestPromptedClosureBypass:
    def test_prompted_closure_flag_and_damping(self):
        det = PSPDetector()
        r = det.detect("which is best — surgery or therapy? just pick one for me.",
                       domain_config=DomainPSPConfig.for_domain("healthcare"))
        assert r.user_requested_closure is True
        assert r.is_decision_point is True

    def test_prompted_closure_transitions_state(self):
        state, reason = next_psp_state(
            PSPState.EXPLORING,
            _reading(is_dp=True, requested_closure=True),
            user_turn_features="just tell me which one")
        assert state is PSPState.CLOSURE_REQUESTED


# ═══════════════════════════════════════════════════════════════
#  TestFeatureFlagBehaviour — PSP inert unless explicitly enabled
# ═══════════════════════════════════════════════════════════════

class TestFeatureFlagBehaviour:
    def test_flags_off_by_default(self):
        assert PSP_ENABLED is False
        assert PSP_GATE_CHECK_ENABLED is False
        assert PSP_GATE_MODE == "monitor"

    def test_detector_runs_independently_of_master_flag(self):
        """PSP_ENABLED gates the pipeline wiring, not the pure detector — the
        detector stays callable and deterministic for tests regardless."""
        det = PSPDetector()
        r = det.detect("should I rent or buy?",
                       domain_config=DomainPSPConfig.for_domain("general"))
        assert isinstance(r, PSPReading)
