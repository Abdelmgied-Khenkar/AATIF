"""
Test suite for FN#050 Dual-Root Reconstruction Engine — aatif_dual_root.py

Tests the DualRootDetector (observational, post-S response enrichment),
DualRootAnalysis/DREContext dataclasses, the three-stage activation gate,
8 Arabic-specific root categories, graceful degradation, cross-causal
detection, POM trace construction, clinical boundary enforcement, and
— critically — the Single Mind invariants (DRE never touches S/H/θ/I/E).

Architecture under test (B-prime post-S):
  DualRootDetector  →  observational, RESPONSE ENRICHMENT, NOT safety
  GovernanceEquation →  judicial (S decision FINAL — DRE never touches it)

Design rule: DRE enriches AFTER the governance equation decides.
Design consensus: Claude × ChatGPT, 2026-06-30
"""

import pytest

import aatif_dual_root as dre_mod
from aatif_dual_root import (
    DualRootAnalysis,
    DREContext,
    RootSignal,
    DRE_ENABLED,
    DRE_MONITOR_ONLY,
    detect_root_a_signals,
    detect_root_b_signals,
    detect_cross_causal,
    build_pom_trace,
    generate_response_guidance,
    should_activate_dre,
    analyze_dual_root,
    validate_single_mind,
    ELIGIBLE_S_DECISIONS,
    EXCLUDED_S_DECISIONS,
    H_RANGE_MIN,
    H_RANGE_MAX,
    MALICIOUS_INTENT_THRESHOLD,
    FACTUAL_QUERY_TYPES,
    DRE_RELEVANT_LAYERS,
    CLINICAL_PROHIBITED_TERMS,
    DEFAULT_PROHIBITED_CLAIMS,
    ROOT_A_TYPES,
    ROOT_B_TYPES,
    CROSS_CAUSAL_VALUES,
    GUIDANCE_TEMPLATES,
    ROOT_STRONG_SIGNAL_WEIGHT,
    ROOT_WEAK_SIGNAL_WEIGHT,
)


# ═══════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def enable_dre():
    """Enable DRE for test, restore after."""
    old_enabled = dre_mod.DRE_ENABLED
    old_monitor = dre_mod.DRE_MONITOR_ONLY
    dre_mod.DRE_ENABLED = True
    dre_mod.DRE_MONITOR_ONLY = False
    yield
    dre_mod.DRE_ENABLED = old_enabled
    dre_mod.DRE_MONITOR_ONLY = old_monitor


def _eligible_ctx(**overrides) -> DREContext:
    """Create a DREContext that passes Stage 1 by default."""
    defaults = dict(
        text="",
        s_decision="CLARIFY",
        H=0.35,
        false_goodness_detected=False,
        intent_malicious_confidence=0.0,
        query_type="personal",
        five_layer_detected=["HIDDEN", "EMOTIONAL"],
    )
    defaults.update(overrides)
    return DREContext(**defaults)


# ═══════════════════════════════════════════════════════════════
#  TestFeatureFlags — FN#050 ships OFF by default
# ═══════════════════════════════════════════════════════════════

class TestFeatureFlags:
    def test_dre_disabled_by_default(self):
        assert DRE_ENABLED is False, "DRE_ENABLED must default to False"

    def test_monitor_only_by_default(self):
        assert DRE_MONITOR_ONLY is True, "DRE_MONITOR_ONLY must default to True"

    def test_disabled_returns_inactive(self):
        ctx = _eligible_ctx(text="مقهور ابغى اخذ حقي")
        result = analyze_dual_root("مقهور ابغى اخذ حقي", ctx)
        assert result.dre_active is False
        assert result.activation_reason == "DRE_ENABLED=False"

    def test_disabled_preserves_flag_state(self):
        ctx = _eligible_ctx(text="test")
        result = analyze_dual_root("test", ctx)
        assert result.enabled is False
        assert result.monitor_only is True


# ═══════════════════════════════════════════════════════════════
#  TestDataclasses — DualRootAnalysis / DREContext defaults
# ═══════════════════════════════════════════════════════════════

class TestDataclasses:
    def test_dual_root_analysis_defaults(self):
        a = DualRootAnalysis()
        assert a.dre_active is False
        assert a.root_a_signal_detected is False
        assert a.root_b_signal_detected is False
        assert a.dual_root_pattern_detected is False
        assert a.cross_causal == "none"
        assert a.pom_trace == {}
        assert a.enrichment_mode == ""
        assert a.response_guidance == ""
        assert a.prohibited_claims == []

    def test_dre_context_defaults(self):
        c = DREContext()
        assert c.text == ""
        assert c.s_decision == ""
        assert c.H == 0.0
        assert c.false_goodness_detected is False
        assert c.intent_malicious_confidence == 0.0

    def test_root_signal_defaults(self):
        s = RootSignal(signal_type="pain")
        assert s.signal_type == "pain"
        assert s.evidence == []
        assert s.strength == 0.0


# ═══════════════════════════════════════════════════════════════
#  TestRootADetection — Psychological / distress-origin signals
# ═══════════════════════════════════════════════════════════════

class TestRootADetection:
    def test_arabic_pain_signal(self):
        signals = detect_root_a_signals("أنا متوجع من اللي صار")
        assert len(signals) > 0
        types = [s.signal_type for s in signals]
        assert "pain" in types

    def test_arabic_fear_signal(self):
        signals = detect_root_a_signals("أنا خايف من المستقبل")
        assert len(signals) > 0
        types = [s.signal_type for s in signals]
        assert "fear" in types

    def test_arabic_humiliation_pain(self):
        signals = detect_root_a_signals("أنا مقهور ومهان")
        types = [s.signal_type for s in signals]
        assert "humiliation_pain" in types

    def test_arabic_injustice_pain(self):
        signals = detect_root_a_signals("أنا مظلوم وما أحد ساعدني")
        types = [s.signal_type for s in signals]
        assert "injustice_pain" in types

    def test_arabic_emotional_threshold(self):
        signals = detect_root_a_signals("الصبر نفد ما عاد اتحمل")
        types = [s.signal_type for s in signals]
        assert "emotional_threshold_exceeded" in types

    def test_arabic_flooding(self):
        signals = detect_root_a_signals("مخنوق وضايق صدري")
        types = [s.signal_type for s in signals]
        assert "flooding" in types

    def test_english_pain_signal(self):
        signals = detect_root_a_signals("I'm suffering and it hurts so much")
        assert len(signals) > 0
        types = [s.signal_type for s in signals]
        assert "pain" in types

    def test_english_fear_signal(self):
        signals = detect_root_a_signals("I'm scared and afraid of what's next")
        types = [s.signal_type for s in signals]
        assert "fear" in types

    def test_english_humiliation(self):
        signals = detect_root_a_signals("I was humiliated in front of everyone")
        types = [s.signal_type for s in signals]
        assert "humiliation_pain" in types

    def test_english_injustice(self):
        signals = detect_root_a_signals("This is so unfair, I was wronged")
        types = [s.signal_type for s in signals]
        assert "injustice_pain" in types

    def test_english_flooding(self):
        signals = detect_root_a_signals("I'm overwhelmed and spiraling")
        types = [s.signal_type for s in signals]
        assert "flooding" in types

    def test_english_emotional_threshold(self):
        signals = detect_root_a_signals("I can't take it anymore, at my breaking point")
        types = [s.signal_type for s in signals]
        assert "emotional_threshold_exceeded" in types

    def test_english_avoidance_loop(self):
        signals = detect_root_a_signals("I keep running away, I can't face it")
        types = [s.signal_type for s in signals]
        assert "avoidance_loop" in types

    def test_no_signals_on_neutral_text(self):
        signals = detect_root_a_signals("What is the weather today?")
        assert signals == []

    def test_no_signals_on_empty_text(self):
        signals = detect_root_a_signals("")
        assert signals == []

    def test_multiple_signal_types(self):
        text = "مقهور ومظلوم وخايف"
        signals = detect_root_a_signals(text)
        types = {s.signal_type for s in signals}
        assert len(types) >= 2

    def test_signal_strength_strong(self):
        signals = detect_root_a_signals("مقهور")
        if signals:
            has_strong = any(s.strength == ROOT_STRONG_SIGNAL_WEIGHT for s in signals)
            assert has_strong

    def test_signal_evidence_populated(self):
        signals = detect_root_a_signals("I'm scared and afraid")
        for s in signals:
            assert len(s.evidence) > 0


# ═══════════════════════════════════════════════════════════════
#  TestRootBDetection — Ethical-drift / justification signals
# ═══════════════════════════════════════════════════════════════

class TestRootBDetection:
    def test_arabic_retaliatory_justice(self):
        signals = detect_root_b_signals("لازم اخذ حقي ولازم يتأدب")
        types = [s.signal_type for s in signals]
        assert "retaliatory_justice" in types

    def test_arabic_dehumanizing_wish(self):
        signals = detect_root_b_signals("الله ينتقم منه ما يستاهل رحمه")
        types = [s.signal_type for s in signals]
        assert "dehumanizing_or_punitive_wish" in types

    def test_arabic_moral_inversion(self):
        signals = detect_root_b_signals("الطيبه ما تنفع في هالزمن")
        types = [s.signal_type for s in signals]
        assert "moral_inversion" in types

    def test_arabic_reputation_harm(self):
        signals = detect_root_b_signals("بأفضحه وأخرب سمعته")
        types = [s.signal_type for s in signals]
        assert "reputation_harm" in types

    def test_arabic_reciprocal_harm(self):
        signals = detect_root_b_signals("عين بعين بسوي فيه زي ما سوى")
        types = [s.signal_type for s in signals]
        assert "reciprocal_harm_justification" in types

    def test_english_retaliatory_justice(self):
        signals = detect_root_b_signals("I'm going to teach him a lesson and make him pay")
        types = [s.signal_type for s in signals]
        assert "retaliatory_justice" in types

    def test_english_justification(self):
        signals = detect_root_b_signals("He deserves it, he had it coming")
        types = [s.signal_type for s in signals]
        assert "justification" in types

    def test_english_moral_inversion(self):
        signals = detect_root_b_signals("Kindness is weakness, nice guys finish last")
        types = [s.signal_type for s in signals]
        assert "moral_inversion" in types

    def test_english_dehumanizing_wish(self):
        signals = detect_root_b_signals("I hope he suffers, he deserves to die")
        types = [s.signal_type for s in signals]
        assert "dehumanizing_or_punitive_wish" in types

    def test_english_reputation_harm(self):
        signals = detect_root_b_signals("I'll expose him and ruin his reputation")
        types = [s.signal_type for s in signals]
        assert "reputation_harm" in types

    def test_english_reciprocal_harm(self):
        signals = detect_root_b_signals("An eye for an eye, taste of his own medicine")
        types = [s.signal_type for s in signals]
        assert "reciprocal_harm_justification" in types

    def test_no_signals_on_neutral_text(self):
        signals = detect_root_b_signals("The weather is nice today")
        assert signals == []

    def test_no_signals_on_empty_text(self):
        signals = detect_root_b_signals("")
        assert signals == []

    def test_signal_evidence_populated(self):
        signals = detect_root_b_signals("I'll teach him a lesson")
        for s in signals:
            assert len(s.evidence) > 0


# ═══════════════════════════════════════════════════════════════
#  TestArabicCategories — The 8 Arabic-specific root categories
# ═══════════════════════════════════════════════════════════════

class TestArabicCategories:
    """Q5 consensus: 8 Arabic-specific root categories."""

    def test_category_a_dignity_pain(self):
        """قهر / كسر / وجع → root_a humiliation_pain or injustice_pain"""
        for text in ["مقهور", "منكسر", "متوجع"]:
            signals = detect_root_a_signals(text)
            assert len(signals) > 0, f"Category A failed for: {text}"

    def test_category_b_retaliatory_justice(self):
        """حقي / أخذ حقي / أربيه → root_b retaliatory_justice"""
        signals = detect_root_b_signals("ابغى اخذ حقي واربيه")
        types = [s.signal_type for s in signals]
        assert "retaliatory_justice" in types

    def test_category_c_honor_as_root_a(self):
        """كرامة / إهانة / ذل → root_a when expressing pain"""
        signals = detect_root_a_signals("كرامتي انداست واهانوني")
        assert len(signals) > 0

    def test_category_c_honor_as_root_b(self):
        """كرامة → root_b when seeking retaliation"""
        signals = detect_root_b_signals("لازم استرجع كرامتي")
        assert len(signals) > 0

    def test_category_d_threshold_exceeded(self):
        """الصبر نفد / طفح الكيل → root_a emotional_threshold_exceeded"""
        signals = detect_root_a_signals("طفح الكيل والصبر نفد")
        types = [s.signal_type for s in signals]
        assert "emotional_threshold_exceeded" in types

    def test_category_e_moral_displacement(self):
        """الدعاء / اللعن / الشماتة → root_b dehumanizing_or_punitive_wish"""
        signals = detect_root_b_signals("الله ينتقم منه والله يذله")
        types = [s.signal_type for s in signals]
        assert "dehumanizing_or_punitive_wish" in types

    def test_category_f_moral_inversion(self):
        """الطيبة ما تنفع → root_b moral_inversion"""
        signals = detect_root_b_signals("الطيبه ما تنفع والطيب يندعس")
        types = [s.signal_type for s in signals]
        assert "moral_inversion" in types

    def test_category_g_reputation_harm(self):
        """فضيحة / سمعة / تشهير → root_b reputation_harm"""
        signals = detect_root_b_signals("بأفضحه وأخرب سمعته وأنشر صوره")
        types = [s.signal_type for s in signals]
        assert "reputation_harm" in types

    def test_category_h_reciprocal_harm(self):
        """عين بعين / الرد بالمثل → root_b reciprocal_harm_justification"""
        signals = detect_root_b_signals("عين بعين والرد بالمثل")
        types = [s.signal_type for s in signals]
        assert "reciprocal_harm_justification" in types


# ═══════════════════════════════════════════════════════════════
#  TestActivationGate — Three-stage gate (all conditions)
# ═══════════════════════════════════════════════════════════════

class TestActivationGate:
    # ── Stage 1: Safety relevance ────────────────────────────

    def test_excluded_safe_freeze(self):
        ctx = _eligible_ctx(s_decision="SAFE_FREEZE")
        ok, reason = should_activate_dre(ctx)
        assert ok is False
        assert "excluded_s_decision" in reason

    def test_excluded_cbrn_block(self):
        ctx = _eligible_ctx(s_decision="CBRN_BLOCK")
        ok, reason = should_activate_dre(ctx)
        assert ok is False
        assert "excluded_s_decision" in reason

    def test_false_goodness_guard(self):
        ctx = _eligible_ctx(
            text="مقهور ابغى اخذ حقي",
            false_goodness_detected=True,
        )
        ok, reason = should_activate_dre(ctx)
        assert ok is False
        assert reason == "false_goodness_guard"

    def test_malicious_intent_exclusion(self):
        ctx = _eligible_ctx(
            text="مقهور ابغى اخذ حقي",
            intent_malicious_confidence=0.80,
        )
        ok, reason = should_activate_dre(ctx)
        assert ok is False
        assert reason == "malicious_intent_exclusion"

    def test_malicious_intent_at_threshold(self):
        ctx = _eligible_ctx(
            text="مقهور ابغى اخذ حقي",
            intent_malicious_confidence=0.70,
        )
        ok, reason = should_activate_dre(ctx)
        assert ok is False
        assert reason == "malicious_intent_exclusion"

    def test_malicious_intent_below_threshold(self):
        ctx = _eligible_ctx(
            text="مقهور ابغى اخذ حقي",
            intent_malicious_confidence=0.69,
        )
        ok, reason = should_activate_dre(ctx)
        assert ok is True

    def test_factual_query_excluded(self):
        for qtype in FACTUAL_QUERY_TYPES:
            ctx = _eligible_ctx(
                text="مقهور ابغى اخذ حقي",
                query_type=qtype,
            )
            ok, reason = should_activate_dre(ctx)
            assert ok is False
            assert "factual_query" in reason

    def test_h_below_range(self):
        ctx = _eligible_ctx(text="مقهور ابغى اخذ حقي", H=0.19)
        ok, reason = should_activate_dre(ctx)
        assert ok is False
        assert "H_out_of_range" in reason

    def test_h_above_range(self):
        ctx = _eligible_ctx(text="مقهور ابغى اخذ حقي", H=0.56)
        ok, reason = should_activate_dre(ctx)
        assert ok is False
        assert "H_out_of_range" in reason

    def test_h_at_min_boundary(self):
        ctx = _eligible_ctx(text="مقهور ابغى اخذ حقي", H=0.20)
        ok, _ = should_activate_dre(ctx)
        assert ok is True

    def test_h_at_max_boundary(self):
        ctx = _eligible_ctx(text="مقهور ابغى اخذ حقي", H=0.55)
        ok, _ = should_activate_dre(ctx)
        assert ok is True

    def test_ineligible_s_decision(self):
        ctx = _eligible_ctx(text="مقهور ابغى اخذ حقي", s_decision="EXECUTE")
        ok, reason = should_activate_dre(ctx)
        assert ok is False
        assert "ineligible_s_decision" in reason

    def test_eligible_clarify(self):
        ctx = _eligible_ctx(text="مقهور ابغى اخذ حقي", s_decision="CLARIFY")
        ok, _ = should_activate_dre(ctx)
        assert ok is True

    def test_eligible_block_soft(self):
        ctx = _eligible_ctx(text="مقهور ابغى اخذ حقي", s_decision="BLOCK_SOFT")
        ok, _ = should_activate_dre(ctx)
        assert ok is True

    def test_eligible_execute_with_caution(self):
        ctx = _eligible_ctx(text="مقهور ابغى اخذ حقي", s_decision="EXECUTE_WITH_CAUTION")
        ok, _ = should_activate_dre(ctx)
        assert ok is True

    def test_no_relevant_five_layer(self):
        ctx = _eligible_ctx(
            text="مقهور ابغى اخذ حقي",
            five_layer_detected=["PRIMARY", "SECONDARY"],
        )
        ok, reason = should_activate_dre(ctx)
        assert ok is False
        assert reason == "no_relevant_five_layer"

    def test_five_layer_hidden_passes(self):
        ctx = _eligible_ctx(
            text="مقهور ابغى اخذ حقي",
            five_layer_detected=["HIDDEN"],
        )
        ok, _ = should_activate_dre(ctx)
        assert ok is True

    def test_five_layer_protective_passes(self):
        ctx = _eligible_ctx(
            text="مقهور ابغى اخذ حقي",
            five_layer_detected=["PROTECTIVE"],
        )
        ok, _ = should_activate_dre(ctx)
        assert ok is True

    def test_five_layer_emotional_passes(self):
        ctx = _eligible_ctx(
            text="مقهور ابغى اخذ حقي",
            five_layer_detected=["EMOTIONAL"],
        )
        ok, _ = should_activate_dre(ctx)
        assert ok is True

    def test_five_layer_none_skips_check(self):
        ctx = _eligible_ctx(
            text="مقهور ابغى اخذ حقي",
            five_layer_detected=None,
        )
        ok, _ = should_activate_dre(ctx)
        assert ok is True

    # ── Stage 2 + 3: Distress and drift ─────────────────────

    def test_no_distress_no_drift(self):
        ctx = _eligible_ctx(text="hello how are you")
        ok, reason = should_activate_dre(ctx)
        assert ok is False
        assert reason == "no_distress_and_no_drift"

    def test_distress_only_activates(self):
        ctx = _eligible_ctx(text="مقهور ومنكسر")
        ok, reason = should_activate_dre(ctx)
        assert ok is True
        assert reason == "distress_only"

    def test_drift_only_activates(self):
        ctx = _eligible_ctx(text="I'll teach him a lesson and make him pay")
        ok, reason = should_activate_dre(ctx)
        assert ok is True
        assert reason == "drift_only"

    def test_both_stages_activate(self):
        ctx = _eligible_ctx(text="مقهور ومنكسر ولازم اخذ حقي")
        ok, reason = should_activate_dre(ctx)
        assert ok is True
        assert reason == "dual_root_both_stages"


# ═══════════════════════════════════════════════════════════════
#  TestGracefulDegradation — dual_root / distress / ethical
# ═══════════════════════════════════════════════════════════════

class TestGracefulDegradation:
    def test_dual_root_mode(self, enable_dre):
        text = "مقهور ومنكسر ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        assert result.dre_active is True
        assert result.enrichment_mode == "dual_root"
        assert result.dual_root_pattern_detected is True

    def test_distress_boundary_mode(self, enable_dre):
        text = "مقهور ومنكسر وتعبان"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        assert result.dre_active is True
        assert result.enrichment_mode == "distress_boundary"
        assert result.root_a_signal_detected is True

    def test_ethical_boundary_mode(self, enable_dre):
        text = "I'll teach him a lesson and make him pay for what he did"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        assert result.dre_active is True
        assert result.enrichment_mode == "ethical_boundary"
        assert result.root_b_signal_detected is True

    def test_pattern_confidence_dual_root(self, enable_dre):
        text = "مقهور ومنكسر ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        assert result.pattern_confidence > 0.0
        assert result.pattern_confidence <= 1.0

    def test_pattern_confidence_single_root_lower(self, enable_dre):
        text_single = "مقهور ومنكسر وتعبان"
        ctx = _eligible_ctx(text=text_single)
        result_single = analyze_dual_root(text_single, ctx)

        text_dual = "مقهور ومنكسر ولازم اخذ حقي"
        ctx2 = _eligible_ctx(text=text_dual)
        result_dual = analyze_dual_root(text_dual, ctx2)

        assert result_single.pattern_confidence <= result_dual.pattern_confidence


# ═══════════════════════════════════════════════════════════════
#  TestCrossCausal — Evidence-bounded cross-causal detection
# ═══════════════════════════════════════════════════════════════

class TestCrossCausal:
    def test_no_roots_returns_none(self):
        cc, evidence = detect_cross_causal("test", [], [])
        assert cc == "none"
        assert evidence == []

    def test_one_root_only_returns_none(self):
        root_a = [RootSignal(signal_type="pain", evidence=["hurt"], strength=0.8)]
        cc, evidence = detect_cross_causal("hurt me", root_a, [])
        assert cc == "none"

    def test_both_roots_no_direction_returns_unclear(self):
        root_a = [RootSignal(signal_type="pain", evidence=["hurt"], strength=0.8)]
        root_b = [RootSignal(signal_type="justification", evidence=["deserves"], strength=0.8)]
        cc, evidence = detect_cross_causal("hurt and deserves it", root_a, root_b)
        assert cc == "co_present_direction_unclear"

    def test_explicit_a_feeds_b_arabic(self):
        root_a = [RootSignal(signal_type="pain", evidence=["وجع"], strength=0.8)]
        root_b = [RootSignal(signal_type="retaliatory_justice", evidence=["حقي"], strength=0.8)]
        cc, evidence = detect_cross_causal(
            "من كثر الألم ابغى اخذ حقي",
            root_a, root_b,
        )
        assert cc == "explicit_a_feeds_b"
        assert any("a→b" in e for e in evidence)

    def test_explicit_a_feeds_b_english(self):
        root_a = [RootSignal(signal_type="pain", evidence=["pain"], strength=0.8)]
        root_b = [RootSignal(signal_type="retaliatory_justice", evidence=["revenge"], strength=0.8)]
        cc, evidence = detect_cross_causal(
            "Because of the pain I want revenge",
            root_a, root_b,
        )
        assert cc == "explicit_a_feeds_b"

    def test_explicit_b_feeds_a_arabic(self):
        root_a = [RootSignal(signal_type="pain", evidence=["تعب"], strength=0.8)]
        root_b = [RootSignal(signal_type="retaliatory_justice", evidence=["انتقام"], strength=0.8)]
        cc, evidence = detect_cross_causal(
            "ندمت بعد الانتقام وتعبت",
            root_a, root_b,
        )
        assert cc == "explicit_b_feeds_a"
        assert any("b→a" in e for e in evidence)

    def test_explicit_b_feeds_a_english(self):
        root_a = [RootSignal(signal_type="pain", evidence=["guilt"], strength=0.8)]
        root_b = [RootSignal(signal_type="retaliatory_justice", evidence=["revenge"], strength=0.8)]
        cc, evidence = detect_cross_causal(
            "I feel guilty about getting revenge, it made me feel worse",
            root_a, root_b,
        )
        assert cc == "explicit_b_feeds_a"

    def test_cross_causal_values_valid(self):
        for val in CROSS_CAUSAL_VALUES:
            assert isinstance(val, str)
        assert "none" in CROSS_CAUSAL_VALUES
        assert "co_present_direction_unclear" in CROSS_CAUSAL_VALUES
        assert "explicit_a_feeds_b" in CROSS_CAUSAL_VALUES
        assert "explicit_b_feeds_a" in CROSS_CAUSAL_VALUES
        assert "independent" in CROSS_CAUSAL_VALUES


# ═══════════════════════════════════════════════════════════════
#  TestPOMTrace — Pain-Origin Mapper signal trace
# ═══════════════════════════════════════════════════════════════

class TestPOMTrace:
    def test_empty_roots_all_empty(self):
        trace = build_pom_trace("test", [], [])
        assert trace["event_signal"] == ""
        assert trace["meaning_signal"] == ""
        assert trace["distress_signal"] == ""
        assert trace["belief_signal"] == ""
        assert trace["behavior_signal"] == ""

    def test_root_a_only_trace(self):
        root_a = [RootSignal(signal_type="pain", evidence=["hurt"], strength=0.8)]
        trace = build_pom_trace("hurt", root_a, [])
        assert trace["event_signal"] == "hurt"
        assert trace["distress_signal"] == "pain"
        assert trace["meaning_signal"] == "distress_without_harmful_channeling"
        assert trace["behavior_signal"] == ""

    def test_root_b_only_trace(self):
        root_b = [RootSignal(signal_type="retaliatory_justice", evidence=["حقي"], strength=0.8)]
        trace = build_pom_trace("حقي", [], root_b)
        assert trace["behavior_signal"] == "حقي"
        assert trace["belief_signal"] == "retaliatory_justice"
        assert trace["meaning_signal"] == "harmful_impulse_without_visible_distress"
        assert trace["event_signal"] == ""

    def test_both_roots_trace(self):
        root_a = [RootSignal(signal_type="pain", evidence=["hurt"], strength=0.8)]
        root_b = [RootSignal(signal_type="retaliatory_justice", evidence=["revenge"], strength=0.8)]
        trace = build_pom_trace("hurt revenge", root_a, root_b)
        assert trace["event_signal"] == "hurt"
        assert trace["distress_signal"] == "pain"
        assert trace["behavior_signal"] == "revenge"
        assert trace["belief_signal"] == "retaliatory_justice"
        assert trace["meaning_signal"] == "distress_channeled_to_harmful_impulse"

    def test_pom_trace_keys(self):
        trace = build_pom_trace("test", [], [])
        expected_keys = {"event_signal", "meaning_signal", "distress_signal",
                         "belief_signal", "behavior_signal"}
        assert set(trace.keys()) == expected_keys


# ═══════════════════════════════════════════════════════════════
#  TestResponseGuidance — Response guidance generation
# ═══════════════════════════════════════════════════════════════

class TestResponseGuidance:
    def test_dual_root_guidance(self):
        a = DualRootAnalysis(enrichment_mode="dual_root")
        guidance = generate_response_guidance(a)
        assert "Acknowledge distress" in guidance
        assert "Reject violence" in guidance

    def test_distress_boundary_guidance(self):
        a = DualRootAnalysis(enrichment_mode="distress_boundary")
        guidance = generate_response_guidance(a)
        assert "compassionately" in guidance

    def test_ethical_boundary_guidance(self):
        a = DualRootAnalysis(enrichment_mode="ethical_boundary")
        guidance = generate_response_guidance(a)
        assert "ethical concern" in guidance

    def test_empty_mode_no_guidance(self):
        a = DualRootAnalysis(enrichment_mode="")
        guidance = generate_response_guidance(a)
        assert guidance == ""

    def test_unknown_mode_no_guidance(self):
        a = DualRootAnalysis(enrichment_mode="unknown_mode")
        guidance = generate_response_guidance(a)
        assert guidance == ""


# ═══════════════════════════════════════════════════════════════
#  TestSingleMind — DRE never changes S/H/θ/I/E
# ═══════════════════════════════════════════════════════════════

class TestSingleMind:
    """The 7 invariants from Q7 consensus."""

    def test_invariant_1_s_decision_unchanged(self, enable_dre):
        text = "مقهور ومنكسر ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text, s_decision="CLARIFY", H=0.35)
        original_s = ctx.s_decision
        original_h = ctx.H
        analyze_dual_root(text, ctx)
        assert ctx.s_decision == original_s
        assert ctx.H == original_h

    def test_invariant_2_no_downgrade(self, enable_dre):
        text = "مقهور ابغى اخذ حقي"
        for s_dec in ["BLOCK_SOFT", "CLARIFY"]:
            ctx = _eligible_ctx(text=text, s_decision=s_dec)
            result = analyze_dual_root(text, ctx)
            assert ctx.s_decision == s_dec

    def test_invariant_3_boundary_preservation(self, enable_dre):
        text = "مقهور ومنكسر ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        if result.enrichment_mode == "dual_root":
            assert result.response_guidance != ""

    def test_invariant_4_no_causal_certainty(self, enable_dre):
        text = "مقهور ومنكسر ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        assert result.prohibited_claims is not None
        assert len(result.prohibited_claims) > 0

    def test_invariant_5_no_clinical_labels_in_guidance(self, enable_dre):
        text = "مقهور ومنكسر ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        guidance_lower = result.response_guidance.lower()
        for term in ["trauma", "disorder", "diagnosis", "ptsd",
                     "صدمة", "اضطراب", "تشخيص"]:
            assert term not in guidance_lower, \
                f"Clinical term '{term}' found in response_guidance"

    def test_invariant_6_false_goodness_guard(self, enable_dre):
        text = "مقهور ابغى اخذ حقي"
        ctx = _eligible_ctx(text=text, false_goodness_detected=True)
        result = analyze_dual_root(text, ctx)
        assert result.dre_active is False

    def test_invariant_7_malicious_exclusion(self, enable_dre):
        text = "مقهور ابغى اخذ حقي"
        ctx = _eligible_ctx(text=text, intent_malicious_confidence=0.80)
        result = analyze_dual_root(text, ctx)
        assert result.dre_active is False

    def test_h_never_modified(self, enable_dre):
        text = "مقهور ومنكسر ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text, H=0.40)
        analyze_dual_root(text, ctx)
        assert ctx.H == 0.40

    def test_s_decision_never_modified(self, enable_dre):
        for s_dec in ELIGIBLE_S_DECISIONS:
            text = "مقهور ومنكسر ولازم اخذ حقي"
            ctx = _eligible_ctx(text=text, s_decision=s_dec)
            analyze_dual_root(text, ctx)
            assert ctx.s_decision == s_dec


# ═══════════════════════════════════════════════════════════════
#  TestValidateSingleMind — Meta-Oversight integration
# ═══════════════════════════════════════════════════════════════

class TestValidateSingleMind:
    def test_no_violations_on_valid_analysis(self):
        a = DualRootAnalysis(
            dre_active=True,
            enrichment_mode="dual_root",
            response_guidance="Acknowledge distress. Reject violence.",
            prohibited_claims=list(DEFAULT_PROHIBITED_CLAIMS),
        )
        violations = validate_single_mind(a, "CLARIFY")
        assert violations == []

    def test_violation_no_guidance_dual_root(self):
        a = DualRootAnalysis(
            dre_active=True,
            enrichment_mode="dual_root",
            response_guidance="",
            prohibited_claims=list(DEFAULT_PROHIBITED_CLAIMS),
        )
        violations = validate_single_mind(a, "CLARIFY")
        assert any("invariant_3" in v for v in violations)

    def test_violation_empty_prohibited_claims(self):
        a = DualRootAnalysis(
            dre_active=True,
            enrichment_mode="dual_root",
            response_guidance="Acknowledge distress.",
            prohibited_claims=[],
        )
        violations = validate_single_mind(a, "CLARIFY")
        assert any("invariant_4" in v for v in violations)

    def test_violation_clinical_term_in_guidance(self):
        a = DualRootAnalysis(
            dre_active=True,
            enrichment_mode="dual_root",
            response_guidance="Your trauma is causing this behavior.",
            prohibited_claims=list(DEFAULT_PROHIBITED_CLAIMS),
        )
        violations = validate_single_mind(a, "CLARIFY")
        assert any("invariant_5" in v for v in violations)

    def test_no_violations_when_inactive(self):
        a = DualRootAnalysis(dre_active=False)
        violations = validate_single_mind(a, "CLARIFY")
        assert violations == []


# ═══════════════════════════════════════════════════════════════
#  TestClinicalBoundary — No Diagnosis, No Treatment, No Root-Certainty
# ═══════════════════════════════════════════════════════════════

class TestClinicalBoundary:
    def test_prohibited_terms_list_not_empty(self):
        assert len(CLINICAL_PROHIBITED_TERMS) > 0

    def test_default_prohibited_claims_populated(self):
        assert len(DEFAULT_PROHIBITED_CLAIMS) == 4
        assert "do not diagnose" in DEFAULT_PROHIBITED_CLAIMS
        assert "do not say trauma" in DEFAULT_PROHIBITED_CLAIMS

    def test_guidance_templates_safe_language(self):
        for mode, template in GUIDANCE_TEMPLATES.items():
            template_lower = template.lower()
            for term in ["trauma", "disorder", "diagnosis", "ptsd"]:
                assert term not in template_lower, \
                    f"Clinical term '{term}' in {mode} guidance template"

    def test_analysis_always_has_prohibited_claims(self, enable_dre):
        text = "مقهور ومنكسر ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        assert len(result.prohibited_claims) > 0


# ═══════════════════════════════════════════════════════════════
#  TestFullPipeline — analyze_dual_root end-to-end
# ═══════════════════════════════════════════════════════════════

class TestFullPipeline:
    def test_dual_root_arabic_full(self, enable_dre):
        text = "مقهور ومنكسر من اللي سوى فيني ولازم اخذ حقي واربيه"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)

        assert result.dre_active is True
        assert result.root_a_signal_detected is True
        assert result.root_b_signal_detected is True
        assert result.enrichment_mode == "dual_root"
        assert result.response_guidance != ""
        assert len(result.pom_trace) == 5

    def test_dual_root_english_full(self, enable_dre):
        text = "I'm broken and humiliated, I want to teach him a lesson and make him pay"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)

        assert result.dre_active is True
        assert result.root_a_signal_detected is True
        assert result.root_b_signal_detected is True
        assert result.enrichment_mode == "dual_root"

    def test_distress_only_arabic(self, enable_dre):
        text = "مقهور ومنكسر وتعبان ومتألم"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)

        assert result.dre_active is True
        assert result.root_a_signal_detected is True
        assert result.enrichment_mode == "distress_boundary"

    def test_drift_only_english(self, enable_dre):
        text = "He deserves it, I'll teach him a lesson and make him pay"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)

        assert result.dre_active is True
        assert result.root_b_signal_detected is True
        assert result.enrichment_mode == "ethical_boundary"

    def test_inactive_on_neutral_text(self, enable_dre):
        text = "What is the capital of France?"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        assert result.dre_active is False

    def test_cross_causal_in_full_analysis(self, enable_dre):
        text = "من كثر الألم ابغى اخذ حقي ولازم يتأدب"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)

        if result.root_a_signal_detected and result.root_b_signal_detected:
            assert result.cross_causal in CROSS_CAUSAL_VALUES

    def test_pom_trace_in_full_analysis(self, enable_dre):
        text = "مقهور ومنكسر ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)

        assert "event_signal" in result.pom_trace
        assert "distress_signal" in result.pom_trace
        assert "meaning_signal" in result.pom_trace
        assert "belief_signal" in result.pom_trace
        assert "behavior_signal" in result.pom_trace

    def test_disabled_does_not_detect(self):
        text = "مقهور ومنكسر ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        assert result.dre_active is False
        assert result.enrichment_mode == ""

    def test_monitor_only_flag_preserved(self, enable_dre):
        dre_mod.DRE_MONITOR_ONLY = True
        text = "مقهور ومنكسر ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        assert result.monitor_only is True
        dre_mod.DRE_MONITOR_ONLY = False


# ═══════════════════════════════════════════════════════════════
#  TestEdgeCases — Empty text, no signals, boundary values
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_text(self, enable_dre):
        ctx = _eligible_ctx(text="")
        result = analyze_dual_root("", ctx)
        assert result.dre_active is False

    def test_whitespace_only(self, enable_dre):
        ctx = _eligible_ctx(text="   ")
        result = analyze_dual_root("   ", ctx)
        assert result.dre_active is False

    def test_very_long_text(self, enable_dre):
        text = "مقهور " * 1000 + " ولازم اخذ حقي"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        assert result.dre_active is True

    def test_mixed_arabic_english(self, enable_dre):
        text = "مقهور and I want to teach him a lesson"
        ctx = _eligible_ctx(text=text)
        result = analyze_dual_root(text, ctx)
        assert result.dre_active is True

    def test_case_insensitive_english(self):
        signals_lower = detect_root_b_signals("teach him a lesson")
        signals_upper = detect_root_b_signals("TEACH HIM A LESSON")
        assert len(signals_lower) > 0
        assert len(signals_upper) > 0

    def test_h_at_exact_boundaries(self):
        text = "مقهور ابغى اخذ حقي"
        ctx_min = _eligible_ctx(text=text, H=H_RANGE_MIN)
        ok_min, _ = should_activate_dre(ctx_min)
        assert ok_min is True

        ctx_max = _eligible_ctx(text=text, H=H_RANGE_MAX)
        ok_max, _ = should_activate_dre(ctx_max)
        assert ok_max is True

    def test_all_eligible_s_decisions(self):
        text = "مقهور ابغى اخذ حقي"
        for s_dec in ELIGIBLE_S_DECISIONS:
            ctx = _eligible_ctx(text=text, s_decision=s_dec)
            ok, _ = should_activate_dre(ctx)
            assert ok is True, f"Should activate for {s_dec}"

    def test_all_excluded_s_decisions(self):
        text = "مقهور ابغى اخذ حقي"
        for s_dec in EXCLUDED_S_DECISIONS:
            ctx = _eligible_ctx(text=text, s_decision=s_dec)
            ok, _ = should_activate_dre(ctx)
            assert ok is False, f"Should NOT activate for {s_dec}"


# ═══════════════════════════════════════════════════════════════
#  TestDistressAuthenticity — Stage 2 detailed checks
# ═══════════════════════════════════════════════════════════════

class TestDistressAuthenticity:
    def test_one_strong_marker_sufficient(self):
        from aatif_dual_root import _check_distress_authenticity
        assert _check_distress_authenticity("مقهور") is True
        assert _check_distress_authenticity("i can't take it anymore") is True

    def test_two_weak_markers_sufficient(self):
        from aatif_dual_root import _check_distress_authenticity
        assert _check_distress_authenticity("تعبان وزعلان") is True
        assert _check_distress_authenticity("tired and sad") is True

    def test_one_weak_marker_insufficient(self):
        from aatif_dual_root import _check_distress_authenticity
        assert _check_distress_authenticity("تعبان") is False

    def test_no_markers_fails(self):
        from aatif_dual_root import _check_distress_authenticity
        assert _check_distress_authenticity("hello world") is False


# ═══════════════════════════════════════════════════════════════
#  TestHarmfulMoralDrift — Stage 3 detailed checks
# ═══════════════════════════════════════════════════════════════

class TestHarmfulMoralDrift:
    def test_explicit_root_b_marker(self):
        from aatif_dual_root import _check_harmful_moral_drift
        assert _check_harmful_moral_drift("لازم اخذ حقي") is True
        assert _check_harmful_moral_drift("teach him a lesson") is True

    def test_drift_phrase_plus_target(self):
        from aatif_dual_root import _check_harmful_moral_drift
        assert _check_harmful_moral_drift("i want to hit him") is True
        assert _check_harmful_moral_drift("ابغى اضربه") is True

    def test_drift_phrase_without_target(self):
        from aatif_dual_root import _check_harmful_moral_drift
        assert _check_harmful_moral_drift("i want to hit") is False

    def test_no_drift_signals(self):
        from aatif_dual_root import _check_harmful_moral_drift
        assert _check_harmful_moral_drift("the weather is nice") is False


# ═══════════════════════════════════════════════════════════════
#  TestConstants — Sanity checks on constants/enums
# ═══════════════════════════════════════════════════════════════

class TestConstants:
    def test_eligible_s_decisions(self):
        assert "CLARIFY" in ELIGIBLE_S_DECISIONS
        assert "BLOCK_SOFT" in ELIGIBLE_S_DECISIONS
        assert "EXECUTE_WITH_CAUTION" in ELIGIBLE_S_DECISIONS

    def test_excluded_s_decisions(self):
        assert "SAFE_FREEZE" in EXCLUDED_S_DECISIONS
        assert "CBRN_BLOCK" in EXCLUDED_S_DECISIONS

    def test_h_range(self):
        assert H_RANGE_MIN == 0.20
        assert H_RANGE_MAX == 0.55

    def test_malicious_threshold(self):
        assert MALICIOUS_INTENT_THRESHOLD == 0.70

    def test_factual_query_types(self):
        for qt in ["factual", "objective", "academic", "news", "definition"]:
            assert qt in FACTUAL_QUERY_TYPES

    def test_relevant_layers(self):
        for layer in ["HIDDEN", "PROTECTIVE", "EMOTIONAL"]:
            assert layer in DRE_RELEVANT_LAYERS

    def test_root_a_types_exist(self):
        expected = ["pain", "fear", "humiliation_pain", "injustice_pain",
                    "avoidance_loop", "flooding", "emotional_threshold_exceeded"]
        for t in expected:
            assert t in ROOT_A_TYPES

    def test_root_b_types_exist(self):
        expected = ["justification", "normalization", "moral_inversion",
                    "retaliatory_justice", "dehumanizing_or_punitive_wish",
                    "reputation_harm", "reciprocal_harm_justification"]
        for t in expected:
            assert t in ROOT_B_TYPES

    def test_guidance_templates_exist(self):
        assert "dual_root" in GUIDANCE_TEMPLATES
        assert "distress_boundary" in GUIDANCE_TEMPLATES
        assert "ethical_boundary" in GUIDANCE_TEMPLATES

    def test_signal_weights(self):
        assert ROOT_STRONG_SIGNAL_WEIGHT == 0.80
        assert ROOT_WEAK_SIGNAL_WEIGHT == 0.40
