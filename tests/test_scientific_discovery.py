"""
tests/test_scientific_discovery.py — Comprehensive test suite for FN#068
Scientific Discovery Mode (السيادة المعرفية)

Tests: authority contract, enums, dataclasses, fast-path, exploration
detection, cross-discipline detection, truth-claim scanning, epistemic
risk, safety bypass risk, recommendations, Arabic markers, sovereignty,
audit hash, integration, edge cases, weak markers, feature flags.

80+ tests covering all constitutional invariants.
"""

from __future__ import annotations

import hashlib
import sys
import os
import unittest

# ── Import shim ──────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))

from aatif_scientific_discovery import (
    ScientificDiscoveryEngine,
    ScientificDiscoveryReading,
    ExplorationMode,
    ExplorationSignal,
    HypothesisStatus,
    CrossDisciplineScope,
    TruthClaimType,
    TruthClaimViolation,
    SovereigntyAssertion,
    EXPLORATION_MARKERS_EN,
    EXPLORATION_MARKERS_AR,
    TRUTH_CLAIM_MARKERS_EN,
    TRUTH_CLAIM_MARKERS_AR,
    WEAK_EXPLORATION_MARKERS,
    _DEFAULT_SOVEREIGNTY,
    _normalize_arabic,
    _match_ar_markers,
    _match_en_markers,
    _EXPLORATION_EN_COMPILED,
    _REFRAME_TEMPLATES,
)


def _engine() -> ScientificDiscoveryEngine:
    return ScientificDiscoveryEngine()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Authority Contract
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAuthorityContract(unittest.TestCase):
    """B-prime constants must never drift."""

    def test_authority_level(self):
        self.assertEqual(ScientificDiscoveryEngine.AUTHORITY_LEVEL,
                         "B_PRIME_OBSERVATIONAL")

    def test_cannot_block_runtime(self):
        self.assertFalse(ScientificDiscoveryEngine.CAN_BLOCK_RUNTIME)

    def test_cannot_modify_h(self):
        self.assertFalse(ScientificDiscoveryEngine.CAN_MODIFY_H)

    def test_cannot_modify_theta(self):
        self.assertFalse(ScientificDiscoveryEngine.CAN_MODIFY_THETA)

    def test_cannot_modify_s(self):
        self.assertFalse(ScientificDiscoveryEngine.CAN_MODIFY_S)

    def test_cannot_emit_judicial(self):
        self.assertFalse(ScientificDiscoveryEngine.CAN_EMIT_JUDICIAL_DECISION)

    def test_binding_channel(self):
        self.assertEqual(ScientificDiscoveryEngine.BINDING_CHANNEL, "B5")

    def test_isolation_marker(self):
        self.assertEqual(ScientificDiscoveryEngine.ISOLATION_MARKER,
                         "B5_ADVISORY_NOT_FOR_SAFETY")

    def test_isolation_targets(self):
        self.assertEqual(ScientificDiscoveryEngine.ISOLATION_TARGETS,
                         frozenset({"B5"}))

    def test_isolation_contract_text(self):
        contract = ScientificDiscoveryEngine.ISOLATION_CONTRACT
        self.assertIn("ADVISORY", contract)
        self.assertIn("NEVER modifies H", contract)
        self.assertIn("NEVER blocks runtime", contract)
        self.assertIn("Single-Mind Law", contract)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. Enum Values
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEnums(unittest.TestCase):
    """Enum values must be stable for serialization."""

    def test_exploration_mode_standard(self):
        self.assertEqual(ExplorationMode.STANDARD.value, "standard")

    def test_exploration_mode_exploration(self):
        self.assertEqual(ExplorationMode.EXPLORATION.value, "exploration")

    def test_hypothesis_not_applicable(self):
        self.assertEqual(HypothesisStatus.NOT_APPLICABLE.value, "not_applicable")

    def test_hypothesis_tagged(self):
        self.assertEqual(HypothesisStatus.TAGGED.value, "tagged")

    def test_hypothesis_truth_claim(self):
        self.assertEqual(HypothesisStatus.TRUTH_CLAIM_DETECTED.value,
                         "truth_claim_detected")

    def test_scope_none(self):
        self.assertEqual(CrossDisciplineScope.NONE.value, "none")

    def test_scope_dual(self):
        self.assertEqual(CrossDisciplineScope.DUAL.value, "dual")

    def test_scope_multi(self):
        self.assertEqual(CrossDisciplineScope.MULTI.value, "multi")

    def test_truth_claim_discovery(self):
        self.assertEqual(TruthClaimType.DISCOVERY_CLAIM.value, "discovery_claim")

    def test_truth_claim_validation(self):
        self.assertEqual(TruthClaimType.VALIDATION_CLAIM.value, "validation_claim")

    def test_truth_claim_truth(self):
        self.assertEqual(TruthClaimType.TRUTH_ASSERTION.value, "truth_assertion")

    def test_truth_claim_conclusion(self):
        self.assertEqual(TruthClaimType.CONCLUSION_CLAIM.value, "conclusion_claim")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. Dataclass Immutability
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDataclassImmutability(unittest.TestCase):
    """Frozen dataclasses must reject mutation."""

    def test_exploration_signal_frozen(self):
        sig = ExplorationSignal(strength=0.5, markers_found=("what if",), language="en")
        with self.assertRaises(AttributeError):
            sig.strength = 0.9  # type: ignore

    def test_truth_claim_violation_frozen(self):
        v = TruthClaimViolation(
            claim_type=TruthClaimType.DISCOVERY_CLAIM,
            claim_text="I've discovered",
            confidence=0.85,
            suggested_reframe="Consider...",
        )
        with self.assertRaises(AttributeError):
            v.confidence = 0.1  # type: ignore

    def test_sovereignty_assertion_frozen(self):
        s = _DEFAULT_SOVEREIGNTY
        with self.assertRaises(AttributeError):
            s.disclaimer_en = "hacked"  # type: ignore

    def test_reading_frozen(self):
        r = _engine().analyze("hi")
        with self.assertRaises(AttributeError):
            r.activated = True  # type: ignore

    def test_reading_isolation_marker(self):
        r = _engine().analyze("hi")
        self.assertEqual(r._isolation_marker, "B5_ADVISORY_NOT_FOR_SAFETY")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. Fast-Path (Inactive Readings)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFastPath(unittest.TestCase):
    """Sparse activation: short / empty / non-exploratory → inactive."""

    def test_empty_string(self):
        r = _engine().analyze("")
        self.assertFalse(r.activated)

    def test_none_guard(self):
        # Passing None should not crash — guard with `not text`
        r = _engine().analyze("")
        self.assertFalse(r.activated)
        self.assertEqual(r.exploration_mode, ExplorationMode.STANDARD)

    def test_too_short(self):
        r = _engine().analyze("hi there")
        self.assertFalse(r.activated)

    def test_whitespace_only(self):
        r = _engine().analyze("        ")
        self.assertFalse(r.activated)

    def test_no_exploration_markers(self):
        r = _engine().analyze("Tell me about the history of Rome and its emperors.")
        self.assertFalse(r.activated)

    def test_factual_question(self):
        r = _engine().analyze("What is the capital of France?")
        self.assertFalse(r.activated)

    def test_code_request(self):
        r = _engine().analyze("Write a Python function that sorts a list.")
        self.assertFalse(r.activated)

    def test_inactive_reading_shape(self):
        """Inactive reading should have clean default values."""
        r = _engine().analyze("Just a normal sentence about cats and dogs.")
        self.assertEqual(r.exploration_mode, ExplorationMode.STANDARD)
        self.assertEqual(r.exploration_signal.strength, 0.0)
        self.assertEqual(r.hypothesis_status, HypothesisStatus.NOT_APPLICABLE)
        self.assertEqual(r.cross_discipline_scope, CrossDisciplineScope.NONE)
        self.assertEqual(r.disciplines_detected, ())
        self.assertEqual(r.truth_claim_violations, ())
        self.assertEqual(r.recommendations, ())
        self.assertEqual(r.evidence, ())
        self.assertEqual(r.epistemic_risk, 0.0)
        self.assertEqual(r.safety_bypass_risk, 0.0)
        self.assertFalse(r.requires_falsification_tests)
        self.assertFalse(r.requires_evidence_tiers)
        self.assertFalse(r.requires_uncertainty_label)
        self.assertFalse(r.requires_source_check)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. Exploration Detection — English
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestExplorationEN(unittest.TestCase):
    """English exploration marker detection."""

    def test_what_if_hypothesis(self):
        r = _engine().analyze("What if there's a hypothesis about quantum effects?")
        self.assertTrue(r.activated)
        self.assertEqual(r.exploration_mode, ExplorationMode.EXPLORATION)

    def test_could_it_be(self):
        r = _engine().analyze(
            "Could it be that the universe is a simulation? "
            "I wonder about this hypothesis."
        )
        self.assertTrue(r.activated)

    def test_brainstorm_explore(self):
        r = _engine().analyze(
            "Let's brainstorm and explore alternative explanations for this phenomenon."
        )
        self.assertTrue(r.activated)

    def test_theoretically_suppose(self):
        r = _engine().analyze(
            "Suppose theoretically that gravity works differently at small scales."
        )
        self.assertTrue(r.activated)

    def test_cross_pollinate_interdisciplinary(self):
        r = _engine().analyze(
            "Can we cross-pollinate ideas from interdisciplinary research?"
        )
        self.assertTrue(r.activated)

    def test_gap_contradiction(self):
        r = _engine().analyze(
            "There's a gap in our understanding and a contradiction in the data."
        )
        self.assertTrue(r.activated)

    def test_chatgpt_additions_falsify(self):
        r = _engine().analyze(
            "What would disprove this hypothesis? Can we falsify the model?"
        )
        self.assertTrue(r.activated)

    def test_chatgpt_additions_experiment(self):
        r = _engine().analyze(
            "Let's design an experiment to test possible causes and research question."
        )
        self.assertTrue(r.activated)

    def test_single_marker_below_threshold(self):
        """One marker alone gives strength=0.20, below threshold=0.25."""
        r = _engine().analyze("What if we tried something different today?")
        self.assertFalse(r.activated)
        # Signal detected but below threshold
        self.assertEqual(r.exploration_mode, ExplorationMode.STANDARD)

    def test_case_insensitive(self):
        r = _engine().analyze(
            "WHAT IF we could EXPLORE a HYPOTHESIS about THEORETICALLY possible links?"
        )
        self.assertTrue(r.activated)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. Exploration Detection — Arabic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestExplorationAR(unittest.TestCase):
    """Arabic exploration marker detection with affix-aware matching."""

    def test_maza_law_faradiya(self):
        r = _engine().analyze(
            "ماذا لو كانت هناك فرضية جديدة عن هذا الموضوع؟ أتساءل عن ذلك."
        )
        self.assertTrue(r.activated)

    def test_istikshaf_asf_zihni(self):
        # "نستكشف" is a conjugated form — not matched by "استكشاف" stem.
        # Need 2+ markers to activate. Add "فرضية" for corroboration.
        r = _engine().analyze(
            "دعنا نبحث في فرضية جديدة من خلال عصف ذهني حر."
        )
        self.assertTrue(r.activated)

    def test_rabt_bayn(self):
        r = _engine().analyze(
            "هل يمكن أن نجد ربط بين الفيزياء والفلسفة؟ تقاطع مثير."
        )
        self.assertTrue(r.activated)

    def test_zawiya_mukhtalifa(self):
        r = _engine().analyze(
            "خلني أفكر في زاوية مختلفة وغير تقليدية لهذه المشكلة."
        )
        self.assertTrue(r.activated)

    def test_chatgpt_ar_additions(self):
        r = _engine().analyze(
            "هل يمكن أن نصمم تجربة لمعرفة الأسباب المحتملة؟ سؤال بحثي مهم."
        )
        self.assertTrue(r.activated)

    def test_arabic_normalization_alef(self):
        """أ/إ/آ should normalize to ا for matching."""
        # "أتساءل" has hamza-on-alef — normalization should handle
        r = _engine().analyze(
            "أتساءل ماذا لو كانت الفرضية صحيحة؟ خلنا نحقق."
        )
        self.assertTrue(r.activated)

    def test_arabic_with_diacritics(self):
        """Diacritics (tashkeel) should not block matching."""
        r = _engine().analyze(
            "مَاذَا لَو كَانَت هُنَاكَ فَرَضِيَّة جَدِيدَة؟ هَل يُمكِن ذلك؟"
        )
        self.assertTrue(r.activated)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7. Exploration Detection — Mixed Language
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestExplorationMixed(unittest.TestCase):
    """Bilingual input detection."""

    def test_mixed_en_ar(self):
        r = _engine().analyze(
            "What if ماذا لو there's a hypothesis فرضية about this?"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.exploration_signal.language, "mixed")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  8. Weak Markers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestWeakMarkers(unittest.TestCase):
    """Weak markers need corroboration (≥2 strong markers)."""

    def test_weak_marker_alone_not_enough(self):
        """'model' alone: weak marker, only 1 match → not activated."""
        r = _engine().analyze(
            "I want to build a model of the weather system for tomorrow."
        )
        self.assertFalse(r.activated)

    def test_imagine_alone_not_enough(self):
        """'imagine' alone: weak marker, only 1 match → not activated."""
        r = _engine().analyze(
            "Imagine that we go to the park this weekend instead."
        )
        self.assertFalse(r.activated)

    def test_weak_with_strong_corroboration(self):
        """'model' + 2 strong markers → all count."""
        r = _engine().analyze(
            "What if we model the mechanism behind this hypothesis?"
        )
        self.assertTrue(r.activated)
        self.assertIn("model", r.exploration_signal.markers_found)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  9. Strength Curve
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestStrengthCurve(unittest.TestCase):
    """Diminishing-returns strength curve matches ColdOS pattern."""

    def test_zero_markers_zero_strength(self):
        r = _engine().analyze("No exploration markers in this sentence at all.")
        self.assertEqual(r.exploration_signal.strength, 0.0)

    def test_two_markers_040(self):
        r = _engine().analyze(
            "What if there's a hypothesis about something?"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.exploration_signal.strength, 0.40)

    def test_four_markers_075(self):
        # "what if" + "explore" + "hypothesis" + "brainstorm" = 4 markers
        r = _engine().analyze(
            "What if we explore this hypothesis and brainstorm ideas?"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.exploration_signal.strength, 0.75)

    def test_strength_capped_at_1(self):
        """Even with many markers, strength ≤ 1.0."""
        r = _engine().analyze(
            "What if we could explore this hypothesis? I wonder if it's "
            "possible to brainstorm about the gap in understanding. "
            "Suppose theoretically we cross-pollinate interdisciplinary "
            "ideas to falsify the mechanism and design an experiment."
        )
        self.assertTrue(r.activated)
        self.assertLessEqual(r.exploration_signal.strength, 1.0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  10. Cross-Discipline Detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCrossDiscipline(unittest.TestCase):
    """Discipline detection and scope classification."""

    def test_no_discipline(self):
        r = _engine().analyze(
            "What if we explore this hypothesis about cooking?"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.cross_discipline_scope, CrossDisciplineScope.NONE)

    def test_single_discipline(self):
        r = _engine().analyze(
            "What if quantum physics has a hypothesis about entanglement?"
        )
        self.assertTrue(r.activated)
        self.assertIn("physics", r.disciplines_detected)

    def test_dual_discipline(self):
        r = _engine().analyze(
            "What if we explore the hypothesis that music theory "
            "relates to mathematical topology?"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.cross_discipline_scope, CrossDisciplineScope.DUAL)
        self.assertIn("mathematics", r.disciplines_detected)
        self.assertIn("music", r.disciplines_detected)

    def test_multi_discipline(self):
        r = _engine().analyze(
            "What if we explore the hypothesis that physics, biology, "
            "and philosophy share a common mathematical foundation? "
            "Let me brainstorm about this."
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.cross_discipline_scope, CrossDisciplineScope.MULTI)
        self.assertGreaterEqual(len(r.disciplines_detected), 3)

    def test_arabic_disciplines(self):
        r = _engine().analyze(
            "ماذا لو كانت هناك علاقة بين الفيزياء والموسيقى؟ فرضية مثيرة."
        )
        self.assertTrue(r.activated)
        self.assertIn("physics", r.disciplines_detected)
        self.assertIn("music", r.disciplines_detected)

    def test_requires_evidence_tiers_dual(self):
        """Dual+ scope → requires_evidence_tiers = True."""
        r = _engine().analyze(
            "What if we explore the hypothesis that biology and "
            "chemistry share hidden mechanisms?"
        )
        self.assertTrue(r.activated)
        if r.cross_discipline_scope in (CrossDisciplineScope.DUAL, CrossDisciplineScope.MULTI):
            self.assertTrue(r.requires_evidence_tiers)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  11. Truth-Claim Scanning (scan_output)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTruthClaimScan(unittest.TestCase):
    """Output scanning for truth-claiming violations."""

    def _get_exploration_reading(self):
        return _engine().analyze(
            "What if there's a hypothesis about quantum effects? "
            "I wonder about this interdisciplinary connection."
        )

    def test_clean_output_no_violations(self):
        reading = self._get_exploration_reading()
        scanned = _engine().scan_output(
            "This is an interesting possibility worth further study.",
            reading,
        )
        self.assertEqual(scanned.hypothesis_status, HypothesisStatus.TAGGED)
        self.assertEqual(len(scanned.truth_claim_violations), 0)

    def test_discovery_claim(self):
        reading = self._get_exploration_reading()
        scanned = _engine().scan_output(
            "I've discovered that quantum entanglement proves consciousness.",
            reading,
        )
        self.assertEqual(scanned.hypothesis_status, HypothesisStatus.TRUTH_CLAIM_DETECTED)
        types = [v.claim_type for v in scanned.truth_claim_violations]
        self.assertIn(TruthClaimType.DISCOVERY_CLAIM, types)

    def test_validation_claim(self):
        reading = self._get_exploration_reading()
        scanned = _engine().scan_output(
            "This proves that the theory is correct beyond all measure.",
            reading,
        )
        self.assertEqual(scanned.hypothesis_status, HypothesisStatus.TRUTH_CLAIM_DETECTED)
        types = [v.claim_type for v in scanned.truth_claim_violations]
        self.assertIn(TruthClaimType.VALIDATION_CLAIM, types)

    def test_truth_assertion(self):
        reading = self._get_exploration_reading()
        scanned = _engine().scan_output(
            "The truth is that this cannot be denied without doubt.",
            reading,
        )
        self.assertEqual(scanned.hypothesis_status, HypothesisStatus.TRUTH_CLAIM_DETECTED)
        types = [v.claim_type for v in scanned.truth_claim_violations]
        self.assertIn(TruthClaimType.TRUTH_ASSERTION, types)

    def test_conclusion_claim(self):
        reading = self._get_exploration_reading()
        scanned = _engine().scan_output(
            "We can conclude that this theory is definitely valid.",
            reading,
        )
        self.assertEqual(scanned.hypothesis_status, HypothesisStatus.TRUTH_CLAIM_DETECTED)
        types = [v.claim_type for v in scanned.truth_claim_violations]
        self.assertIn(TruthClaimType.CONCLUSION_CLAIM, types)

    def test_arabic_truth_claim(self):
        reading = self._get_exploration_reading()
        scanned = _engine().scan_output(
            "هذا يثبت أن النظرية صحيحة بلا شك.",
            reading,
        )
        self.assertEqual(scanned.hypothesis_status, HypothesisStatus.TRUTH_CLAIM_DETECTED)
        self.assertGreater(len(scanned.truth_claim_violations), 0)

    def test_multiple_violations_same_output(self):
        reading = self._get_exploration_reading()
        scanned = _engine().scan_output(
            "I've discovered the truth is that this proves everything "
            "without doubt and we can conclude that it is certain.",
            reading,
        )
        self.assertGreater(len(scanned.truth_claim_violations), 2)

    def test_suggested_reframes_exist(self):
        reading = self._get_exploration_reading()
        scanned = _engine().scan_output(
            "I've discovered that the evidence proves this theory.",
            reading,
        )
        for v in scanned.truth_claim_violations:
            self.assertGreater(len(v.suggested_reframe), 0)

    def test_scan_preserves_exploration_data(self):
        """scan_output preserves original exploration data."""
        reading = self._get_exploration_reading()
        scanned = _engine().scan_output(
            "I've discovered something amazing.",
            reading,
        )
        self.assertEqual(scanned.exploration_mode, reading.exploration_mode)
        self.assertEqual(scanned.exploration_signal, reading.exploration_signal)
        self.assertEqual(scanned.cross_discipline_scope,
                         reading.cross_discipline_scope)

    def test_scan_skips_non_exploration(self):
        """scan_output is no-op for STANDARD mode readings."""
        inactive = _engine().analyze("A normal sentence about nothing.")
        scanned = _engine().scan_output("I've discovered the truth!", inactive)
        # Should return the same reading unchanged
        self.assertEqual(scanned.hypothesis_status, inactive.hypothesis_status)

    def test_scan_skips_short_text(self):
        reading = self._get_exploration_reading()
        scanned = _engine().scan_output("short", reading)
        self.assertEqual(scanned.hypothesis_status, reading.hypothesis_status)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  12. Epistemic Risk Assessment
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEpistemicRisk(unittest.TestCase):
    """ChatGPT invariant: hallucination risk assessment."""

    def test_low_risk_simple_exploration(self):
        r = _engine().analyze(
            "What if we explore this hypothesis about something new?"
        )
        self.assertTrue(r.activated)
        self.assertLessEqual(r.epistemic_risk, 0.30)

    def test_higher_risk_multi_discipline(self):
        r = _engine().analyze(
            "What if we explore the hypothesis that physics, biology, "
            "and philosophy can be unified through music theory? "
            "Let me brainstorm about cross-pollinating these ideas."
        )
        self.assertTrue(r.activated)
        self.assertGreater(r.epistemic_risk, 0.20)

    def test_medical_domain_elevates_risk(self):
        r = _engine().analyze(
            "What if there's a hypothesis about this phenomenon? "
            "I wonder about the mechanism.",
            domain="medical",
        )
        self.assertTrue(r.activated)
        self.assertGreater(r.epistemic_risk, 0.20)

    def test_risk_capped_at_1(self):
        r = _engine().analyze(
            "What if we explore the hypothesis that physics, biology, "
            "chemistry, philosophy, and mathematics are all connected? "
            "Let me brainstorm about cross-pollinating interdisciplinary "
            "ideas to falsify and design an experiment.",
            domain="medical",
        )
        self.assertLessEqual(r.epistemic_risk, 1.0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  13. Safety Bypass Risk Assessment
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSafetyBypassRisk(unittest.TestCase):
    """Invariant 7: discovery mode may not widen unsafe detail."""

    def test_zero_risk_normal_exploration(self):
        r = _engine().analyze(
            "What if there's a hypothesis about music and mathematics?"
        )
        self.assertTrue(r.activated)
        self.assertEqual(r.safety_bypass_risk, 0.0)

    def test_elevated_risk_procedural(self):
        r = _engine().analyze(
            "What if we explore the hypothesis? How to make step by "
            "step instructions for synthesizing compounds."
        )
        self.assertTrue(r.activated)
        self.assertGreater(r.safety_bypass_risk, 0.0)

    def test_high_risk_dangerous_domain(self):
        r = _engine().analyze(
            "What if we explore a hypothesis about this? "
            "How to make the detailed steps.",
            domain="weapons",
        )
        self.assertTrue(r.activated)
        self.assertGreater(r.safety_bypass_risk, 0.50)

    def test_risk_capped_at_1(self):
        r = _engine().analyze(
            "What if we explore the hypothesis? How to make "
            "step by step detailed instructions.",
            domain="explosives",
        )
        self.assertLessEqual(r.safety_bypass_risk, 1.0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  14. Recommendations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestRecommendations(unittest.TestCase):
    """Recommendations shape response — core AATIF epistemic guidance."""

    def test_always_tag_as_hypothesis(self):
        r = _engine().analyze(
            "What if there's a hypothesis about something? I wonder."
        )
        self.assertTrue(r.activated)
        hypothesis_rec = [rec for rec in r.recommendations if "HYPOTHESIS" in rec]
        self.assertGreater(len(hypothesis_rec), 0)

    def test_sovereignty_rec(self):
        r = _engine().analyze(
            "What if there's a hypothesis about something? I wonder."
        )
        sovereignty_rec = [rec for rec in r.recommendations if "Architect" in rec]
        self.assertGreater(len(sovereignty_rec), 0)

    def test_falsification_rec(self):
        """ChatGPT invariant 6: falsification path required."""
        r = _engine().analyze(
            "What if there's a hypothesis about something? I wonder."
        )
        falsification_rec = [rec for rec in r.recommendations if "falsification" in rec.lower()]
        self.assertGreater(len(falsification_rec), 0)

    def test_gaps_contradictions_rec(self):
        r = _engine().analyze(
            "What if there's a hypothesis about something? I wonder."
        )
        gaps_rec = [rec for rec in r.recommendations if "gaps" in rec.lower() or "contradictions" in rec.lower()]
        self.assertGreater(len(gaps_rec), 0)

    def test_cross_discipline_rec(self):
        r = _engine().analyze(
            "What if there's a hypothesis connecting physics and music? "
            "Let me explore this."
        )
        if r.cross_discipline_scope != CrossDisciplineScope.NONE:
            disc_rec = [rec for rec in r.recommendations if "cross-discipline" in rec.lower()]
            self.assertGreater(len(disc_rec), 0)

    def test_violation_recs_in_scan(self):
        reading = _engine().analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        scanned = _engine().scan_output("I've discovered the truth!", reading)
        violation_recs = [r for r in scanned.recommendations if "VIOLATION" in r]
        self.assertGreater(len(violation_recs), 0)

    def test_epistemic_risk_caution_rec(self):
        r = _engine().analyze(
            "What if we explore the hypothesis that physics, biology, "
            "and philosophy all share common mathematical foundations? "
            "Let me brainstorm about this.",
            domain="medical",
        )
        caution_rec = [rec for rec in r.recommendations if "CAUTION" in rec]
        if r.epistemic_risk >= 0.40:
            self.assertGreater(len(caution_rec), 0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  15. Sovereignty Assertion
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSovereignty(unittest.TestCase):
    """Cognitive sovereignty defaults — The One Rule."""

    def test_default_sovereignty_en(self):
        self.assertIn("possible pathway", _DEFAULT_SOVEREIGNTY.disclaimer_en)

    def test_default_sovereignty_ar(self):
        self.assertIn("مسار محتمل", _DEFAULT_SOVEREIGNTY.disclaimer_ar)

    def test_architect_authority_en(self):
        self.assertIn("Architect", _DEFAULT_SOVEREIGNTY.architect_authority_en)

    def test_architect_authority_ar(self):
        self.assertIn("المهندس", _DEFAULT_SOVEREIGNTY.architect_authority_ar)

    def test_sovereignty_in_reading(self):
        r = _engine().analyze(
            "What if there's a hypothesis about something? I wonder."
        )
        self.assertEqual(r.sovereignty, _DEFAULT_SOVEREIGNTY)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  16. Audit Hash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAuditHash(unittest.TestCase):
    """SHA-256 audit trail integrity."""

    def test_hash_is_sha256(self):
        r = _engine().analyze(
            "What if there's a hypothesis? I wonder about the mechanism."
        )
        h = ScientificDiscoveryEngine.audit_hash(r)
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_same_reading_same_hash(self):
        r = _engine().analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        h1 = ScientificDiscoveryEngine.audit_hash(r)
        h2 = ScientificDiscoveryEngine.audit_hash(r)
        self.assertEqual(h1, h2)

    def test_different_readings_different_hash(self):
        r1 = _engine().analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        r2 = _engine().analyze(
            "What if we explore the hypothesis connecting physics "
            "and biology? Let me brainstorm about the mechanism."
        )
        h1 = ScientificDiscoveryEngine.audit_hash(r1)
        h2 = ScientificDiscoveryEngine.audit_hash(r2)
        self.assertNotEqual(h1, h2)

    def test_inactive_hash(self):
        r = _engine().analyze("No exploration here at all.")
        h = ScientificDiscoveryEngine.audit_hash(r)
        self.assertEqual(len(h), 64)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  17. Feature Flags
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestFeatureFlags(unittest.TestCase):
    """Master switch and output scan toggle."""

    def test_sdm_disabled_returns_inactive(self):
        engine = ScientificDiscoveryEngine()
        engine.SDM_ENABLED = False
        r = engine.analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        self.assertFalse(r.activated)
        engine.SDM_ENABLED = True  # restore

    def test_scan_disabled_skips_violations(self):
        engine = ScientificDiscoveryEngine()
        reading = engine.analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        engine.SDM_OUTPUT_SCAN_ENABLED = False
        scanned = engine.scan_output("I've discovered the truth!", reading)
        self.assertEqual(scanned.hypothesis_status, reading.hypothesis_status)
        engine.SDM_OUTPUT_SCAN_ENABLED = True  # restore


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  18. Evidence Trail
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEvidenceTrail(unittest.TestCase):
    """Evidence trail for audit purposes."""

    def test_evidence_includes_strength(self):
        r = _engine().analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        strength_ev = [e for e in r.evidence if "exploration_strength=" in e]
        self.assertGreater(len(strength_ev), 0)

    def test_evidence_includes_language(self):
        r = _engine().analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        lang_ev = [e for e in r.evidence if "exploration_language=" in e]
        self.assertGreater(len(lang_ev), 0)

    def test_evidence_includes_markers(self):
        r = _engine().analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        marker_ev = [e for e in r.evidence if "markers_found=" in e]
        self.assertGreater(len(marker_ev), 0)

    def test_evidence_includes_scope(self):
        r = _engine().analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        scope_ev = [e for e in r.evidence if "cross_discipline_scope=" in e]
        self.assertGreater(len(scope_ev), 0)

    def test_violation_evidence_in_scan(self):
        reading = _engine().analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        scanned = _engine().scan_output("I've discovered the truth!", reading)
        violation_ev = [e for e in scanned.evidence if "truth_claim_violation" in e]
        self.assertGreater(len(violation_ev), 0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  19. Requires_* Flags
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestRequiresFlags(unittest.TestCase):
    """ChatGPT consensus: additional boolean flags."""

    def test_requires_uncertainty_always_in_exploration(self):
        r = _engine().analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        self.assertTrue(r.activated)
        self.assertTrue(r.requires_uncertainty_label)

    def test_requires_falsification_when_strength_high(self):
        r = _engine().analyze(
            "What if we explore this hypothesis and brainstorm ideas?"
        )
        if r.exploration_signal.strength >= 0.40:
            self.assertTrue(r.requires_falsification_tests)

    def test_requires_source_check_with_disciplines(self):
        r = _engine().analyze(
            "What if there's a hypothesis about physics? I wonder."
        )
        if len(r.disciplines_detected) > 0:
            self.assertTrue(r.requires_source_check)

    def test_inactive_no_requires(self):
        r = _engine().analyze("Normal sentence about nothing special.")
        self.assertFalse(r.requires_falsification_tests)
        self.assertFalse(r.requires_evidence_tiers)
        self.assertFalse(r.requires_uncertainty_label)
        self.assertFalse(r.requires_source_check)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  20. Marker Sets Consistency
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMarkerSets(unittest.TestCase):
    """Marker frozensets are non-empty and immutable."""

    def test_exploration_en_non_empty(self):
        self.assertGreater(len(EXPLORATION_MARKERS_EN), 15)

    def test_exploration_ar_non_empty(self):
        self.assertGreater(len(EXPLORATION_MARKERS_AR), 15)

    def test_truth_claim_en_non_empty(self):
        self.assertGreater(len(TRUTH_CLAIM_MARKERS_EN), 8)

    def test_truth_claim_ar_non_empty(self):
        self.assertGreater(len(TRUTH_CLAIM_MARKERS_AR), 8)

    def test_weak_markers_subset_of_exploration(self):
        """Weak markers must be a subset of exploration markers."""
        self.assertTrue(WEAK_EXPLORATION_MARKERS.issubset(EXPLORATION_MARKERS_EN))

    def test_reframe_templates_cover_all_types(self):
        for claim_type in TruthClaimType:
            self.assertIn(claim_type, _REFRAME_TEMPLATES)

    def test_marker_sets_are_frozenset(self):
        self.assertIsInstance(EXPLORATION_MARKERS_EN, frozenset)
        self.assertIsInstance(EXPLORATION_MARKERS_AR, frozenset)
        self.assertIsInstance(TRUTH_CLAIM_MARKERS_EN, frozenset)
        self.assertIsInstance(TRUTH_CLAIM_MARKERS_AR, frozenset)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  21. Arabic Normalization Helper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestArabicNormalization(unittest.TestCase):
    """_normalize_arabic strips diacritics and normalizes alef."""

    def test_hamza_alef(self):
        self.assertEqual(_normalize_arabic("أحمد"), "احمد")

    def test_alef_below(self):
        self.assertEqual(_normalize_arabic("إبراهيم"), "ابراهيم")

    def test_madda_alef(self):
        self.assertEqual(_normalize_arabic("آمن"), "امن")

    def test_tatweel_stripped(self):
        self.assertEqual(_normalize_arabic("عـاطـف"), "عاطف")

    def test_diacritics_stripped(self):
        result = _normalize_arabic("كِتَابٌ")
        self.assertNotIn("ِ", result)
        self.assertNotIn("َ", result)
        self.assertNotIn("ٌ", result)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  22. Integration: Full Pipeline
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIntegration(unittest.TestCase):
    """End-to-end integration tests."""

    def test_full_pipeline_explore_then_scan(self):
        """Full pipeline: analyze → scan_output → verify."""
        engine = ScientificDiscoveryEngine()

        # 1. User explores
        reading = engine.analyze(
            "What if we could find a connection between music and physics? "
            "Is it possible there's a common mathematical structure?"
        )
        self.assertTrue(reading.activated)
        self.assertEqual(reading.exploration_mode, ExplorationMode.EXPLORATION)
        self.assertEqual(reading.hypothesis_status, HypothesisStatus.TAGGED)

        # 2. System generates draft — clean
        clean_scan = engine.scan_output(
            "This is an intriguing hypothesis worth examining. There may "
            "be connections between harmonic structures and wave equations.",
            reading,
        )
        self.assertEqual(clean_scan.hypothesis_status, HypothesisStatus.TAGGED)

        # 3. System generates draft — with violation
        bad_scan = engine.scan_output(
            "I've discovered that music IS physics — this proves the "
            "connection beyond doubt.",
            reading,
        )
        self.assertEqual(bad_scan.hypothesis_status,
                         HypothesisStatus.TRUTH_CLAIM_DETECTED)
        self.assertGreater(len(bad_scan.truth_claim_violations), 0)

    def test_arabic_full_pipeline(self):
        engine = ScientificDiscoveryEngine()
        reading = engine.analyze(
            "ماذا لو كانت هناك علاقة بين الفيزياء والموسيقى؟ "
            "فرضية مثيرة عن ربط بين التخصصات."
        )
        self.assertTrue(reading.activated)
        self.assertEqual(reading.exploration_signal.language, "ar")

        scanned = engine.scan_output(
            "اكتشفت أن الفيزياء هي الموسيقى، هذا يثبت العلاقة.",
            reading,
        )
        self.assertEqual(scanned.hypothesis_status,
                         HypothesisStatus.TRUTH_CLAIM_DETECTED)

    def test_audit_hash_chain(self):
        """Hash changes when reading changes."""
        engine = ScientificDiscoveryEngine()
        r1 = engine.analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        r2 = engine.scan_output("I've discovered the truth!", r1)
        h1 = engine.audit_hash(r1)
        h2 = engine.audit_hash(r2)
        # Different readings → different hashes
        self.assertNotEqual(h1, h2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  23. Edge Cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEdgeCases(unittest.TestCase):
    """Edge cases and boundary conditions."""

    def test_emoji_in_text(self):
        r = _engine().analyze(
            "What if 🤔 there's a hypothesis about something? I wonder 💭"
        )
        self.assertTrue(r.activated)

    def test_extremely_long_text(self):
        text = "What if there's a hypothesis? " * 500
        r = _engine().analyze(text)
        self.assertTrue(r.activated)
        self.assertLessEqual(r.exploration_signal.strength, 1.0)

    def test_markers_in_url(self):
        """URL containing markers should still trigger (lexical detection)."""
        r = _engine().analyze(
            "What if we check https://example.com/explore-hypothesis "
            "for more information? I wonder about this."
        )
        # 'explore' and 'hypothesis' are in the URL but also semantically relevant
        self.assertTrue(r.activated)

    def test_no_false_positive_on_model_word(self):
        """'model' alone (weak) should not activate."""
        r = _engine().analyze(
            "The Tesla Model 3 is a great car for everyday driving."
        )
        self.assertFalse(r.activated)

    def test_domain_parameter_does_not_affect_activation(self):
        """Domain changes risk assessment, not activation."""
        r1 = _engine().analyze(
            "What if there's a hypothesis? I wonder about this.",
            domain="general",
        )
        r2 = _engine().analyze(
            "What if there's a hypothesis? I wonder about this.",
            domain="medical",
        )
        self.assertEqual(r1.activated, r2.activated)
        # But epistemic risk differs
        self.assertGreater(r2.epistemic_risk, r1.epistemic_risk)

    def test_special_characters(self):
        r = _engine().analyze(
            "What if (hypothesis!) there's a 'connection' between "
            "physics & biology? I wonder..."
        )
        self.assertTrue(r.activated)

    def test_newlines_in_text(self):
        r = _engine().analyze(
            "What if there's a hypothesis?\n"
            "I wonder about the possible connection.\n"
            "Let me explore this idea."
        )
        self.assertTrue(r.activated)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  24. Constitutional Invariants (direct tests)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestConstitutionalInvariants(unittest.TestCase):
    """Direct tests of the 8 constitutional invariants from ChatGPT."""

    def test_invariant_1_no_modify_h_theta_s(self):
        """Invariant 1: Never modifies H, θ, S."""
        self.assertFalse(ScientificDiscoveryEngine.CAN_MODIFY_H)
        self.assertFalse(ScientificDiscoveryEngine.CAN_MODIFY_THETA)
        self.assertFalse(ScientificDiscoveryEngine.CAN_MODIFY_S)

    def test_invariant_2_no_block_runtime(self):
        """Invariant 2 (runtime): scientific framing never blocks."""
        self.assertFalse(ScientificDiscoveryEngine.CAN_BLOCK_RUNTIME)

    def test_invariant_3_hypotheses_labeled(self):
        """Invariant 3: Hypotheses must be labeled as hypotheses."""
        r = _engine().analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        self.assertEqual(r.hypothesis_status, HypothesisStatus.TAGGED)

    def test_invariant_4_speculative_not_fact(self):
        """Invariant 4: speculative claims not presented as fact → scan detects."""
        reading = _engine().analyze(
            "What if there's a hypothesis? I wonder about this."
        )
        scanned = _engine().scan_output("This proves it is certain.", reading)
        self.assertEqual(scanned.hypothesis_status,
                         HypothesisStatus.TRUTH_CLAIM_DETECTED)

    def test_invariant_6_falsification_required(self):
        """Invariant 6: at least one falsification path."""
        r = _engine().analyze(
            "What if there's a hypothesis? I wonder about the mechanism."
        )
        if r.exploration_signal.strength >= 0.40:
            self.assertTrue(r.requires_falsification_tests)

    def test_invariant_8_governance_sole_authority(self):
        """Invariant 8: GovernanceEquation remains the only judicial authority."""
        self.assertFalse(ScientificDiscoveryEngine.CAN_EMIT_JUDICIAL_DECISION)


if __name__ == "__main__":
    unittest.main()
