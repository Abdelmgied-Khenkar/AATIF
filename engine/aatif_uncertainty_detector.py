"""
AATIF Uncertainty/Calibration Detector — "والله أعلم"
=====================================================

Architecture: B-prime Safety-Observational
──────────────────────────────────────────
UncertaintyDetector  →  observational (computes calibration_confidence)
GovernanceEquation   →  judicial (uses calibration_confidence in confidence gate)

Critical Design Rule (Single Mind):
  Only GovernanceEquation can make safety decisions.
  UncertaintyDetector computes calibration_confidence — a SIGNAL.
  The confidence gate inside GovernanceEquation ESCALATES (EXECUTE→CLARIFY)
  when calibration_confidence < ξ(d). It NEVER blocks, allows, or overrides
  independently.

  Uncertainty causes clarification/disclosure, not punishment.

Design consensus: Claude × ChatGPT, 2026-06-30
Field Note: FN#058 design consensus → Uncertainty module

"Unknown is not harmful. But unknown pretending to be known — that is harmful."
"المجهول مش ضار. لكن المجهول اللي بيتظاهر إنه معلوم — هذا الضار."

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
#  Feature Flags — all default OFF
# ═══════════════════════════════════════════════════════════════
#
# Deployment path: Disabled → Monitor → Gate → OutputCheck
#   UNCERTAINTY_ENABLED:             master switch — enables detection + logging
#   UNCERTAINTY_MONITOR_ONLY:        log only, no gate effect
#   UNCERTAINTY_GATE_ENABLED:        confidence gate active (EXECUTE→CLARIFY)
#   UNCERTAINTY_OUTPUT_CHECK_ENABLED: Layer 8 false-certainty detection
#   UNCERTAINTY_TRACE_ENABLED:       multi-turn uncertainty trace

UNCERTAINTY_ENABLED = False
UNCERTAINTY_MONITOR_ONLY = True
UNCERTAINTY_GATE_ENABLED = False
UNCERTAINTY_OUTPUT_CHECK_ENABLED = False
UNCERTAINTY_TRACE_ENABLED = False


# ═══════════════════════════════════════════════════════════════
#  Constants — calibration values
# ═══════════════════════════════════════════════════════════════

# Aggregation weights — sum to 1.0
W_H = 0.35    # harm confidence weight (highest — H is safety-critical)
W_I = 0.25    # intent confidence weight
W_E = 0.15    # emotion confidence weight
W_COV = 0.15  # coverage weight
W_AGR = 0.10  # agreement weight

# H-floor cap: when H confidence is low, cap overall confidence
# h_conf < 0.35 → cap at 0.45
# h_conf < 0.50 → cap at 0.60
H_FLOOR_CAP_RULES = [
    (0.35, 0.45),
    (0.50, 0.60),
]

# ξ(d) — confidence threshold by domain
# Decision is EXECUTE but confidence < ξ(d) → escalate to CLARIFY
CONFIDENCE_THRESHOLD_BY_DOMAIN = {
    "healthcare": 0.80,
    "legal": 0.75,
    "finance": 0.75,
    "education": 0.65,
    "general": 0.55,
    "creative": 0.40,
}

# Scorer confidence string → numeric (Phase 1)
CONFIDENCE_STRING_MAP = {
    "high": 0.9,
    "medium": 0.6,
    "low": 0.3,
}

# Coverage: clamp((max_sim - 0.10) / 0.50)
COVERAGE_MIN_SIM = 0.10
COVERAGE_RANGE = 0.50  # 0.10 to 0.60 maps to 0.0 to 1.0

# Abstention thresholds — "والله أعلم"
# baseline: calibration_confidence < 0.20 → should_abstain
ABSTENTION_THRESHOLD_BY_DOMAIN = {
    "healthcare": 0.30,
    "legal": 0.30,
    "finance": 0.30,
    "education": 0.20,
    "general": 0.20,
    "creative": 0.15,
}
ABSTENTION_BASELINE = 0.20

# Arabic-specific confidence penalties
# These reduce calibration_confidence. They NEVER increase harm.
ARABIC_CONFIDENCE_PENALTIES = {
    "arabizi_detected": -0.10,
    "dialect_switch": -0.08,
    "tashkeel_ambiguous": -0.05,
    "cultural_indirection": -0.08,
}

# Multi-turn decay: uncertainty_trace_t = current + λ_trace * previous_trace
TRACE_LAMBDA = 0.6


# ═══════════════════════════════════════════════════════════════
#  Data Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class UncertaintyReading:
    """Output of UncertaintyDetector.detect() — observational, NOT judicial.

    calibration_confidence: [0, 1] — how confident the system is in its scores.
    xi_threshold: ξ(d) — domain-specific confidence threshold.
    should_abstain: True if confidence is below abstention threshold.
    should_gate: True if decision should be escalated (EXECUTE→CLARIFY).
    """
    calibration_confidence: float = 1.0
    xi_threshold: float = 0.55
    domain: str = "general"

    # Component confidences (for audit trail)
    h_confidence: float = 0.9
    i_confidence: float = 0.9
    e_confidence: float = 0.9
    coverage: float = 1.0
    agreement: float = 1.0

    # Derived signals
    should_abstain: bool = False
    should_gate: bool = False

    # H-I divergence (ambiguity signal)
    ambiguity_score: float = 0.0
    ambiguity_signals: int = 0

    # Arabic penalties applied
    arabic_penalties: Dict[str, float] = field(default_factory=dict)
    total_arabic_penalty: float = 0.0

    # Multi-turn trace (when UNCERTAINTY_TRACE_ENABLED)
    uncertainty_trace: float = 0.0

    # Evidence / audit trail
    evidence: List[str] = field(default_factory=list)

    # Feature flag state at time of reading
    enabled: bool = False
    gate_enabled: bool = False


@dataclass
class UncertaintyDisclosure:
    """Disclosure instructions for the response shaper.

    When uncertainty is significant, the response should acknowledge
    what is and is not known. This dataclass carries the structured
    disclosure that gets injected into meaning_instructions.
    """
    what_unknown: str = ""
    why_unknown: str = ""
    what_needed: str = ""
    what_known: str = ""
    disclosure_level: str = "none"  # none, mild, moderate, significant


# ═══════════════════════════════════════════════════════════════
#  UncertaintyDetector — observational, NOT judicial
# ═══════════════════════════════════════════════════════════════

class UncertaintyDetector:
    """
    Observational uncertainty detection — B-prime architecture.

    This class is NOT judicial. It computes calibration_confidence
    (a scalar confidence signal) and provides evidence. The
    GovernanceEquation decides what to do with it.

    Four uncertainty sources:
      1. Scorer confidence — h_conf, i_conf, e_conf (continuous 0-1)
      2. Coverage — anchor/data coverage via max_sim values
      3. H-I divergence — renamed from "ambiguity", base signal
      4. Inter-scorer agreement — H/I/E coherence

    Usage:
        detector = UncertaintyDetector()
        reading = detector.detect(engine_result, domain="healthcare")
        if reading.should_gate:
            # GovernanceEquation will escalate EXECUTE → CLARIFY
            pass
    """

    def __init__(self,
                 trace_lambda: float = TRACE_LAMBDA):
        self._trace_lambda = trace_lambda
        self._previous_trace: float = 0.0

    def detect(self, result: dict,
               domain: str = "general",
               arabic_signals: Optional[Dict[str, bool]] = None) -> UncertaintyReading:
        """
        Main entry point — compute calibration_confidence from engine result.

        Args:
            result: dict from AATIFEngine.compute() containing scorer_confidence,
                    scorer_max_sim, H, I, E, etc.
            domain: domain string for ξ(d) threshold lookup.
            arabic_signals: optional dict of Arabic-specific signal flags, e.g.
                           {"arabizi_detected": True, "dialect_switch": False, ...}

        Returns:
            UncertaintyReading with calibration_confidence and all components.
        """
        reading = UncertaintyReading(
            domain=domain,
            enabled=UNCERTAINTY_ENABLED,
            gate_enabled=UNCERTAINTY_GATE_ENABLED,
        )

        # If uncertainty detection is disabled, return high-confidence default
        if not UNCERTAINTY_ENABLED:
            reading.evidence.append("UNCERTAINTY_ENABLED=False — pass-through")
            return reading

        evidence = []

        # ── 1. Scorer confidence (Phase 1: string→numeric) ────────
        scorer_conf = result.get("scorer_confidence", {})
        h_conf_str = scorer_conf.get("H", "high")
        i_conf_str = scorer_conf.get("I", "high")
        e_conf_str = scorer_conf.get("E", "high")

        h_conf = self._convert_confidence(h_conf_str)
        i_conf = self._convert_confidence(i_conf_str)
        e_conf = self._convert_confidence(e_conf_str)

        reading.h_confidence = h_conf
        reading.i_confidence = i_conf
        reading.e_confidence = e_conf
        evidence.append(f"scorer_conf: H={h_conf:.2f} I={i_conf:.2f} E={e_conf:.2f}")

        # ── 2. Coverage (from max_sim values) ─────────────────────
        coverage, h_cov, i_cov, e_cov = self._compute_coverage(result)
        reading.coverage = coverage
        evidence.append(f"coverage={coverage:.3f} (H={h_cov:.2f} I={i_cov:.2f} E={e_cov:.2f})")

        # ── 3. Ambiguity / H-I divergence ─────────────────────────
        ambiguity, n_signals = self._compute_ambiguity(result)
        reading.ambiguity_score = ambiguity
        reading.ambiguity_signals = n_signals
        evidence.append(f"ambiguity={ambiguity:.3f} (signals={n_signals})")

        # ── 4. Inter-scorer agreement ─────────────────────────────
        agreement = self._compute_agreement(result)
        reading.agreement = agreement
        evidence.append(f"agreement={agreement:.3f}")

        # ── 5. Aggregate → calibration_confidence ─────────────────
        cal_conf = self._aggregate(h_conf, i_conf, e_conf, coverage, agreement)

        # ── 6. Arabic penalties (reduce confidence, NEVER increase harm) ─
        total_penalty = 0.0
        if arabic_signals:
            for signal_name, is_active in arabic_signals.items():
                if is_active and signal_name in ARABIC_CONFIDENCE_PENALTIES:
                    penalty = ARABIC_CONFIDENCE_PENALTIES[signal_name]
                    reading.arabic_penalties[signal_name] = penalty
                    total_penalty += penalty
            if total_penalty < 0.0:
                cal_conf = max(0.0, cal_conf + total_penalty)
                reading.total_arabic_penalty = total_penalty
                evidence.append(f"arabic_penalty={total_penalty:.3f}")

        # ── NaN/Inf guard — fail safe ────────────────────────────
        if math.isnan(cal_conf) or math.isinf(cal_conf):
            cal_conf = 0.0  # fail safe → triggers CLARIFY/ABSTAIN

        reading.calibration_confidence = round(cal_conf, 4)

        # ── 7. Domain threshold and gating decision ───────────────
        xi = self._get_xi(domain)
        reading.xi_threshold = xi

        # ── 8. Abstention threshold (checked BEFORE gate) ────────
        abstention_threshold = ABSTENTION_THRESHOLD_BY_DOMAIN.get(
            domain, ABSTENTION_BASELINE
        )
        reading.should_abstain = cal_conf < abstention_threshold

        if reading.should_abstain:
            if UNCERTAINTY_GATE_ENABLED:
                reading.should_gate = True  # abstention implies gating
            evidence.append(
                f"ABSTAIN: {cal_conf:.3f} < abstention={abstention_threshold:.2f}"
            )
        elif UNCERTAINTY_GATE_ENABLED and cal_conf < xi:
            reading.should_gate = True
            evidence.append(
                f"GATE: {cal_conf:.3f} < xi={xi:.2f}"
            )

        # ── 9. Multi-turn trace ───────────────────────────────────
        if UNCERTAINTY_TRACE_ENABLED:
            current_uncertainty = 1.0 - cal_conf
            trace = (1 - self._trace_lambda) * current_uncertainty + self._trace_lambda * self._previous_trace
            self._previous_trace = trace
            reading.uncertainty_trace = round(trace, 4)
            evidence.append(f"trace={trace:.3f}")

        reading.evidence = evidence
        return reading

    # ── Component computations ────────────────────────────────────

    def _compute_coverage(self, result: dict) -> tuple:
        """Compute coverage from max_sim values.

        Coverage = mean of per-scorer coverage.
        Per-scorer coverage = clamp((max_sim - 0.10) / 0.50, 0, 1)

        Higher max_sim → the input is close to known anchors → more coverage.
        Low max_sim → input is in uncharted territory → less coverage.

        Returns (overall_coverage, h_coverage, i_coverage, e_coverage).
        """
        scorer_max_sim = result.get("scorer_max_sim", {})

        h_sim = scorer_max_sim.get("H")
        i_sim = scorer_max_sim.get("I")
        e_sim = scorer_max_sim.get("E")

        def _cov(sim):
            if sim is None:
                return 0.0
            return max(0.0, min(1.0, (sim - COVERAGE_MIN_SIM) / COVERAGE_RANGE))

        h_cov = _cov(h_sim)
        i_cov = _cov(i_sim)
        e_cov = _cov(e_sim)

        # Weighted mean — H coverage matters most for safety
        overall = (0.5 * h_cov + 0.3 * i_cov + 0.2 * e_cov)
        return round(overall, 4), round(h_cov, 4), round(i_cov, 4), round(e_cov, 4)

    def _compute_ambiguity(self, result: dict) -> tuple:
        """Compute ambiguity from H-I divergence and other signals.

        Multiple sources of ambiguity:
          1. H-I divergence: high H + high I = confusing (harm + good intent?)
          2. Low intent confidence: can't determine what user wants
          3. Unknown territory flag: outside known anchor space

        Returns (ambiguity_score, number_of_active_signals).
        """
        H = result.get("H", 0.0)
        I = result.get("I", 0.0)
        n_signals = 0
        total = 0.0

        # Signal 1: H-I divergence — large gap between H and I is ambiguous
        # Only fires when harm is non-trivial (H > 0.4)
        if H > 0.4 and abs(H - I) > 0.3:
            divergence = min(1.0, abs(H - I) * 1.5)
            total += divergence
            n_signals += 1

        # Signal 2: Low intent confidence
        scorer_conf = result.get("scorer_confidence", {})
        i_conf_str = scorer_conf.get("I", "high")
        if i_conf_str == "low":
            total += 0.3
            n_signals += 1

        # Signal 3: Unknown territory
        if result.get("unknown_territory", False):
            total += 0.4
            n_signals += 1

        # Normalize to [0, 1]
        ambiguity = min(1.0, total)
        return round(ambiguity, 4), n_signals

    def _compute_agreement(self, result: dict) -> float:
        """Compute inter-scorer agreement / coherence.

        When H is high but I is also high (benign intent), or when
        emotion contradicts intent — the scorers disagree. Low
        agreement → lower confidence.

        Returns agreement score in [0, 1]. Higher = more agreement.
        """
        H = result.get("H", 0.0)
        I = result.get("I", 0.5)
        E = result.get("E", 0.5)

        # Ideal coherence: H and I should be inversely related
        # High H + low I = coherent (clearly harmful)
        # Low H + high I = coherent (clearly benign)
        # High H + high I = incoherent (mixed signals)
        # Low H + low I = somewhat incoherent (unclear)

        # H-I coherence: inversely related scores = agreement
        h_i_agreement = 1.0 - abs(H - (1.0 - I))

        # E consistency: extreme E with low H+I conflict is fine;
        # extreme E with contradicting H is concerning
        e_consistency = 1.0 - (abs(E - 0.5) * abs(H - (1.0 - I)))

        # Weighted combination
        agreement = 0.6 * h_i_agreement + 0.4 * e_consistency
        return round(max(0.0, min(1.0, agreement)), 4)

    def _aggregate(self, h_conf: float, i_conf: float, e_conf: float,
                   coverage: float, agreement: float) -> float:
        """Aggregate component confidences into calibration_confidence.

        Weighted mean + H-floor cap.
        Weights: W_H=0.35, W_I=0.25, W_E=0.15, W_COV=0.15, W_AGR=0.10

        H-floor cap rules:
          h_conf < 0.35 → cap overall at 0.45
          h_conf < 0.50 → cap overall at 0.60
        """
        weighted = (
            W_H * h_conf +
            W_I * i_conf +
            W_E * e_conf +
            W_COV * coverage +
            W_AGR * agreement
        )

        # H-floor cap: if H confidence is low, cap overall
        for h_threshold, cap_value in H_FLOOR_CAP_RULES:
            if h_conf < h_threshold:
                weighted = min(weighted, cap_value)
                break  # apply strictest rule (first match)

        return round(max(0.0, min(1.0, weighted)), 4)

    @staticmethod
    def _get_xi(domain: str) -> float:
        """Look up ξ(d) — domain confidence threshold.

        Returns the threshold. Unknown domains get the general threshold.
        """
        return CONFIDENCE_THRESHOLD_BY_DOMAIN.get(domain, 0.55)

    @staticmethod
    def _convert_confidence(conf_str: str) -> float:
        """Convert scorer confidence string to numeric.

        Phase 1: simple mapping.
        Phase 2 will use raw similarity-derived confidence.
        Phase 3 will use calibrated confidence from validation data.
        """
        if isinstance(conf_str, (int, float)):
            return float(conf_str)
        return CONFIDENCE_STRING_MAP.get(conf_str, 0.6)

    # ── Disclosure generation ─────────────────────────────────────

    @staticmethod
    def build_disclosure(reading: UncertaintyReading,
                         result: dict) -> UncertaintyDisclosure:
        """Build an UncertaintyDisclosure from an UncertaintyReading.

        Generates structured disclosure instructions for the response
        shaper when uncertainty is significant.

        Disclosure levels:
          none:        calibration_confidence >= xi → no disclosure needed
          mild:        0.8*xi <= cc < xi → acknowledge limits briefly
          moderate:    0.5*xi <= cc < 0.8*xi → explain what's uncertain
          significant: cc < 0.5*xi → full disclosure with what's needed
        """
        cc = reading.calibration_confidence
        xi = reading.xi_threshold

        if cc >= xi:
            return UncertaintyDisclosure(disclosure_level="none")

        # Determine disclosure level
        if cc >= 0.8 * xi:
            level = "mild"
        elif cc >= 0.5 * xi:
            level = "moderate"
        else:
            level = "significant"

        # Build disclosure fields
        what_unknown_parts = []
        why_unknown_parts = []
        what_needed_parts = []
        what_known_parts = []

        # What is known — the scores we do have
        H = result.get("H", 0.0)
        I = result.get("I", 0.0)
        if H > 0.4:
            what_known_parts.append("تم رصد إشارات حساسية في المحتوى")
        if I > 0.6:
            what_known_parts.append("النية تبدو بنّاءة")

        # What is unknown — based on low-confidence components
        if reading.h_confidence < 0.5:
            what_unknown_parts.append("مدى حساسية المحتوى")
            why_unknown_parts.append("النص خارج نطاق الأنماط المعروفة")
        if reading.i_confidence < 0.5:
            what_unknown_parts.append("القصد الدقيق من الطلب")
            why_unknown_parts.append("الغرض من الطلب غير واضح")
        if reading.coverage < 0.3:
            what_unknown_parts.append("هذا الموضوع خارج النطاق المعتاد")
            why_unknown_parts.append("لا توجد أنماط مرجعية كافية")

        # What is needed — always ask for clarification
        if what_unknown_parts:
            what_needed_parts.append("توضيح إضافي من المستخدم")
        if reading.ambiguity_score > 0.3:
            what_needed_parts.append("تحديد القصد بشكل أدق")

        return UncertaintyDisclosure(
            what_unknown=" / ".join(what_unknown_parts) if what_unknown_parts else "",
            why_unknown=" / ".join(why_unknown_parts) if why_unknown_parts else "",
            what_needed=" / ".join(what_needed_parts) if what_needed_parts else "",
            what_known=" / ".join(what_known_parts) if what_known_parts else "",
            disclosure_level=level,
        )


# ═══════════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== UncertaintyDetector Self-Test ===\n")

    # Temporarily enable for self-test
    import aatif_uncertainty_detector as _mod
    _mod.UNCERTAINTY_ENABLED = True
    _mod.UNCERTAINTY_GATE_ENABLED = True

    detector = UncertaintyDetector()

    # Simulate a high-confidence result
    high_conf_result = {
        "H": 0.1, "I": 0.9, "E": 0.3,
        "scorer_confidence": {"H": "high", "I": "high", "E": "high"},
        "scorer_max_sim": {"H": 0.55, "I": 0.60, "E": 0.50},
        "unknown_territory": False,
    }

    reading = detector.detect(high_conf_result, domain="general")
    print(f"High confidence: cc={reading.calibration_confidence:.3f} "
          f"xi={reading.xi_threshold:.2f} gate={reading.should_gate}")

    # Simulate a low-confidence result
    low_conf_result = {
        "H": 0.5, "I": 0.7, "E": 0.4,
        "scorer_confidence": {"H": "low", "I": "medium", "E": "low"},
        "scorer_max_sim": {"H": 0.15, "I": 0.25, "E": 0.12},
        "unknown_territory": True,
    }

    reading = detector.detect(low_conf_result, domain="healthcare")
    print(f"Low confidence:  cc={reading.calibration_confidence:.3f} "
          f"xi={reading.xi_threshold:.2f} gate={reading.should_gate} "
          f"abstain={reading.should_abstain}")
    for ev in reading.evidence:
        print(f"  {ev}")

    # Restore
    _mod.UNCERTAINTY_ENABLED = False
    _mod.UNCERTAINTY_GATE_ENABLED = False

    print("\nDone.")
