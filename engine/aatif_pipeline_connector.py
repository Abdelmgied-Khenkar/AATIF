#!/usr/bin/env python3
"""
AATIF Pipeline Connector — يربط المحافظ (Governor) بالبايبلاين الحالي

C1+C2 FIX: Routes through AATIFGovernor — the single orchestrator that chains
S(d) → P(d) → R(d) → memory → governed prompt → Output Gate — instead of the
old regex-based AATIFIntentEngine. This resolves:

  C1: "Two disjoint engines" — the Governor uses the semantic AATIFEngine
      (bge-m3 embeddings + calibrated thresholds), not the regex IntentEngine.
  C2: "Pipeline has no orchestrator" — the Governor IS the orchestrator.

The old pipeline expects:
  - IntentResult with .to_plan_dict() → {surface_intent, hidden_intent, ...}
  - build_intent_result(text, state, business_type, relationship_context)

This connector:
  1. Runs the AATIFGovernor (full S→P→R→Gate semantic pipeline)
  2. Falls back to old AATIFIntentEngine when Ollama is unavailable
  3. Translates GovernedResponse → old IntentResult format (backward compatible)
  4. Extends the `aatif` signals with the full Governor audit trail

Usage in api_server.py — replace the old import:
    # OLD: from intent_engine import build_intent_result
    # NEW: from aatif_pipeline_connector import build_intent_result

Everything downstream (reply_base_mapper, llm_bridge, output_gate) keeps working.
The new signals (R style, P protocols, gate result) ride along as extra fields.

Architect: Abdulmjeed Ibrahim Khenkar
"""

import sys
import os
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Import paths ──
_AATIF_DIR = os.path.dirname(os.path.abspath(__file__))
if _AATIF_DIR not in sys.path:
    sys.path.insert(0, _AATIF_DIR)

# ── C1+C2: Governor is the PRIMARY engine ──
from aatif_governor import AATIFGovernor, GovernedResponse  # noqa: E402

# ── Old IntentEngine as FALLBACK (when Ollama unavailable) ──
from aatif_intent_engine import AATIFIntentEngine, IntentReading  # noqa: E402


# ═══════════════════════════════════════════════════════════
#  High-risk domains — SAFE_STOP when Governor is unavailable
# ═══════════════════════════════════════════════════════════
# "الدومين يقرر" — the domain decides. These domains carry real-world
# harm potential that the regex fallback engine cannot safely evaluate.
# When the Governor is down, these domains get a complete halt (SAFE_STOP)
# rather than degraded operation.

HIGH_RISK_DOMAINS = frozenset({
    "health", "healthcare", "medical",
    "banking", "finance",
    "children", "minors",
    "legal",
    "emergency",
})


# ═══════════════════════════════════════════════════════════
#  Old IntentResult format (backward compatible)
# ═══════════════════════════════════════════════════════════

@dataclass
class IntentLayers:
    surface: str
    primary: str


@dataclass
class AnalysisMatrix:
    why_now_signal: str
    wrong_answer_risk: str
    user_knowledge_level: str
    positioning_mode: str
    value_focus: list = field(default_factory=list)
    outcome_mode: str = "none"
    trust_mode: str = "calm_direct"
    intent_confidence: str = "medium"
    ambiguity_flag: bool = False
    handling_mode: str = "clarify_then_answer"
    forbidden_moves: list = field(default_factory=list)


@dataclass
class IntentResult:
    """Backward-compatible IntentResult that the old pipeline understands,
    enriched with new AATIF governance signals."""

    incoming_text: str
    normalized_text: str
    state: str = ""
    name: str = ""
    business_type: str = ""
    greeting: str = ""
    relationship_context: dict = field(default_factory=dict)
    intent_layers: IntentLayers = None
    analysis_matrix: AnalysisMatrix = None

    # ── New AATIF signals (ride along, don't break old code) ──
    aatif_reading: IntentReading = None

    # ── Degradation transparency (set when Governor is unavailable) ──
    degradation_warning: Optional[str] = None

    def to_plan_dict(self) -> dict:
        """Old format that api_server.py / reply_base_mapper.py expect."""
        base = {
            "incoming_text": self.incoming_text,
            "normalized_text": self.normalized_text,
            "state": self.state,
            "name": self.name,
            "business_type": self.business_type,
            "greeting": self.greeting,
            "relationship_context": self.relationship_context or {},
            "surface_intent": self.intent_layers.surface if self.intent_layers else "default",
            "hidden_intent": self.intent_layers.primary if self.intent_layers else "none",
            "why_now_signal": self.analysis_matrix.why_now_signal if self.analysis_matrix else "general",
            "wrong_answer_risk": self.analysis_matrix.wrong_answer_risk if self.analysis_matrix else "low",
            "user_knowledge_level": self.analysis_matrix.user_knowledge_level if self.analysis_matrix else "unaware",
            "positioning_mode": self.analysis_matrix.positioning_mode if self.analysis_matrix else "none",
            "value_focus": self.analysis_matrix.value_focus if self.analysis_matrix else [],
            "outcome_mode": self.analysis_matrix.outcome_mode if self.analysis_matrix else "none",
            "trust_mode": self.analysis_matrix.trust_mode if self.analysis_matrix else "calm_direct",
            "intent_confidence": self.analysis_matrix.intent_confidence if self.analysis_matrix else "low",
            "ambiguity_flag": self.analysis_matrix.ambiguity_flag if self.analysis_matrix else True,
            "handling_mode": self.analysis_matrix.handling_mode if self.analysis_matrix else "clarify_then_answer",
            "forbidden_moves": self.analysis_matrix.forbidden_moves if self.analysis_matrix else [],
        }

        # Surface degradation warning at top level so API consumers see it
        if self.degradation_warning:
            base["degradation_warning"] = self.degradation_warning

        # Attach AATIF governance signals as extra keys
        if self.aatif_reading:
            r = self.aatif_reading
            base["aatif"] = {
                "decision": r.decision,
                "decision_reason": r.decision_reason,
                "mode": r.mode,
                "emotional_state": r.emotional_state,
                "emotional_confidence": r.emotional_confidence,
                "load_bearing": r.load_bearing,
                "dialect": r.dialect_detected,
                "ambiguity": r.ambiguity_score,
                "harm": r.harm_score,
                "softening": r.softening_factor,
                "skills": r.skills_to_activate,
                "deep_intent": r.deep_intent,
            }

            # C1+C2: when the Governor handled this message, attach the full
            # audit trail so downstream consumers can read P(d) protocols,
            # R(d) style, gate result, and the governed prompt.
            gov = getattr(self, "_gov_result", None)
            if gov is not None:
                base["aatif"]["engine"] = "governor"
                base["aatif"]["stage_reached"] = gov.stage_reached
                base["aatif"]["blocked"] = gov.blocked
                if gov.r_result:
                    base["aatif"]["r_style"] = gov.r_result.style_recommendation
                    base["aatif"]["r_score"] = gov.r_result.r_score
                if gov.p_result:
                    base["aatif"]["p_highest_action"] = gov.p_result.highest_action
                    base["aatif"]["p_has_protocols"] = gov.p_result.has_protocols
                if gov.governed_prompt:
                    base["aatif"]["governed_prompt"] = gov.governed_prompt
                # Stage 4 — the Output Gate only runs when an llm_fn hook was
                # supplied (the Governor gates a real response, never a prompt).
                # When present, surface the gate verdict + the gated final text
                # so a caller running the FULL pipeline sees the last guard.
                if gov.gate_result is not None:
                    base["aatif"]["gate_blocked"] = gov.gate_result.blocked
                    base["aatif"]["gate_flags"] = list(gov.gate_result.flags)
                    if gov.gate_result.block_reason:
                        base["aatif"]["gate_block_reason"] = (
                            gov.gate_result.block_reason
                        )
                if gov.final_response is not None:
                    base["aatif"]["final_response"] = gov.final_response
                if gov.emergency_injected:
                    base["aatif"]["emergency_injected"] = True
            else:
                base["aatif"]["engine"] = "intent_engine_fallback"

        return base


# ═══════════════════════════════════════════════════════════
#  Translation: IntentReading → old pipeline fields
# ═══════════════════════════════════════════════════════════

# Map AATIF emotional states → old trust_mode
_EMOTION_TO_TRUST = {
    "carrying_weight": "gentle_supportive",
    "lost":            "orient_first",
    "excited":         "match_energy",
    "frustrated":      "acknowledge_first",
    "clear":           "calm_direct",
}

# Map AATIF decisions → old handling_mode
_DECISION_TO_HANDLING = {
    "EXECUTE":     "direct_answer",
    "CLARIFY":     "clarify_then_answer",
    "SAFE_STOP":   "refuse_safely",
    "SAFE_FREEZE": "refuse_safely",
}


def _normalize_text(text):
    """Lightweight Arabic normalization matching the old intent_engine."""
    import re
    t = text.strip()
    t = re.sub(r'[ًٌٍَُِّْ]', '', t)           # remove diacritics
    t = t.replace('ة', 'ه').replace('ى', 'ي')   # normalize endings
    t = re.sub(r'[أإآ]', 'ا', t)                  # normalize alef
    return t


def _detect_greeting(text):
    """Detect if the message is a greeting and extract the greeting word."""
    import re
    low = text.strip().lower()
    greetings_ar = [
        "السلام عليكم", "سلام", "مرحبا", "مرحبه", "هلا", "هلا والله",
        "اهلا", "اهلين", "يا هلا", "حياك", "حياكم",
    ]
    greetings_en = [
        "hello", "hi", "hey", "good morning", "good evening",
        "assalamu alaikum", "salam",
    ]
    for g in greetings_ar:
        if g in _normalize_text(text):
            return g
    for g in greetings_en:
        if g in low:
            return g
    return ""


def _detect_surface_intent(text, reading: IntentReading):
    """Map the message + reading to old-style surface_intent."""
    low = text.strip().lower()
    norm = _normalize_text(text)

    # Greeting
    if _detect_greeting(text):
        return "greeting"

    # Price question
    price_markers = ["كم السعر", "السعر", "price", "pricing", "بكم", "تكلفه", "cost"]
    if any(m in norm or m in low for m in price_markers):
        return "price_question"

    # Identity question
    identity_markers = ["وظيفتك", "من انت", "مين انت", "who are you", "your role"]
    if any(m in norm or m in low for m in identity_markers):
        return "identity_question"

    # Value question
    value_markers = ["الفايده", "فايده", "العائد", "roi", "worth", "يسوي"]
    if any(m in norm or m in low for m in value_markers):
        return "value_question"

    # Use AATIF mode to inform
    if reading.mode == "STOP":
        return "ambiguous"

    return "default"


def _detect_hidden_intent(text, reading: IntentReading):
    """Infer hidden intent from emotional state and signals."""
    if reading.load_bearing:
        return "needs_support"
    if reading.emotional_state == "frustrated":
        return "trust_check"
    if reading.emotional_state == "excited":
        return "ready_to_engage"
    if reading.emotional_state == "lost":
        return "needs_orientation"
    return "none"


def _assess_risk(reading: IntentReading):
    """Map harm score to risk level."""
    if reading.harm_score >= 0.6:
        return "high"
    if reading.harm_score >= 0.3:
        return "medium"
    return "low"


def _assess_confidence(reading: IntentReading):
    """Map ambiguity to confidence level."""
    if reading.ambiguity_score < 0.2:
        return "high"
    if reading.ambiguity_score < 0.5:
        return "medium"
    return "low"


# ═══════════════════════════════════════════════════════════
#  Engine management — Governor first, old engine as fallback
# ═══════════════════════════════════════════════════════════

_governor = None
_governor_init_attempted = False

_fallback_engine = None


def _get_governor():
    """
    Try to build an AATIFGovernor (requires Ollama + bge-m3).

    Returns the Governor, or None if the semantic backend is unavailable.
    Uses on_degraded="safe_stop" so the constructor itself won't raise —
    but a degraded Governor is useless (everything returns SAFE_STOP), so
    we treat degraded as "unavailable" and fall back to the regex engine.
    """
    global _governor, _governor_init_attempted
    if _governor_init_attempted:
        return _governor
    _governor_init_attempted = True
    try:
        g = AATIFGovernor(on_degraded="safe_stop", verify_backend=True)
        if g.is_degraded:
            _governor = None
        else:
            _governor = g
    except Exception:
        _governor = None
    return _governor


def _get_fallback_engine():
    """Old regex engine — always works, no Ollama required."""
    global _fallback_engine
    if _fallback_engine is None:
        _fallback_engine = AATIFIntentEngine(mode="safe_environment")
    return _fallback_engine


# ═══════════════════════════════════════════════════════════
#  GovernedResponse → IntentReading adapter
# ═══════════════════════════════════════════════════════════
# When the Governor handles a message, translate its rich output
# into an IntentReading so the old pipeline format (IntentResult)
# can be populated.

# E score → named emotional state
def _emotion_from_E(E: float) -> tuple:
    """Map semantic E score to (emotional_state, confidence)."""
    if E <= 0.15:
        return ("carrying_weight", 0.85)
    elif E <= 0.35:
        return ("frustrated", 0.70)
    elif E <= 0.55:
        return ("clear", 0.60)
    elif E <= 0.75:
        return ("clear", 0.55)
    else:
        return ("excited", 0.70)


def _governed_to_reading(text: str, gov: GovernedResponse) -> IntentReading:
    """
    Map a GovernedResponse → IntentReading for backward compatibility.

    The Governor's s_result dict has H, I, E, S, decision etc.
    We extract these and fill in IntentReading fields.
    """
    s = gov.s_result or {}
    H = s.get("H", 0.5)
    I = s.get("I", 0.5)
    E = s.get("E", 0.5)
    S = s.get("S", 0.5)

    emotional_state, emotional_conf = _emotion_from_E(E)
    load_bearing = E < 0.3

    # Ambiguity: derive from the s_result flags
    ambiguity = 0.0
    if s.get("ambiguity_override"):
        ambiguity = 0.6
    elif s.get("unknown_territory"):
        ambiguity = 0.5
    elif gov.final_decision == "CLARIFY":
        ambiguity = 0.4

    # Mode: ANSWER / PROOF / STOP
    decision = gov.final_decision
    if decision in ("EXECUTE",):
        mode = "ANSWER"
    elif decision == "CLARIFY":
        mode = "STOP"
    else:
        mode = "STOP"

    # Decision reason
    if gov.blocked:
        reason = gov.block_reason
    elif decision == "CLARIFY":
        reason = "Ambiguity or low confidence — requesting clarification"
    else:
        reason = f"S(d)={S:.3f}, H={H:.3f} — cleared by Governor"

    return IntentReading(
        surface_request=text,
        deep_intent="none",
        emotional_state=emotional_state,
        emotional_confidence=emotional_conf,
        load_bearing=load_bearing,
        cbrn_flag=bool(s.get("hard_override")),
        override_flag=bool(s.get("jailbreak_escalated")),
        governance_intact=True,
        mode=mode,
        ambiguity_score=ambiguity,
        harm_score=H,
        softening_factor=S,
        directness=max(0.0, 1.0 - ambiguity),
        skills_to_activate=[],
        activation_evidence="Governor pipeline — skills not regex-activated",
        dialect_detected=_detect_dialect_simple(text),
        time_context="",
        decision=decision,
        decision_reason=reason,
    )


def _detect_dialect_simple(text: str) -> str:
    """Lightweight dialect detection — no Ollama needed."""
    import re
    norm = text.strip()
    gulf = [r"ابي\b", r"أبي\b", r"ابغ[ىا]", r"أبغ[ىا]", r"وش\b", r"يالله",
            r"مرره?\b", r"حياك"]
    egyptian = [r"عايز", r"ازاي", r"إزاي", r"عشان", r"كده", r"هوا\b"]
    for pat in gulf:
        if re.search(pat, norm):
            return "saudi"
    for pat in egyptian:
        if re.search(pat, norm):
            return "egyptian"
    return "msa"


# ═══════════════════════════════════════════════════════════
#  Main entry — drop-in replacement for old build_intent_result
# ═══════════════════════════════════════════════════════════

def build_intent_result(incoming_text, state="", business_type="",
                        relationship_context=None, *,
                        domain="general", llm_fn=None, conversation_id=None):
    """
    Drop-in replacement for the old intent_engine.build_intent_result().

    C1+C2: Routes through AATIFGovernor (S→P→R→Gate semantic pipeline).
    Falls back to old AATIFIntentEngine if Ollama/bge-m3 is unavailable.

    Args:
        incoming_text, state, business_type, relationship_context: as before
            (positional, backward compatible).
        domain: which DOMAIN_CONFIG profile the Governor scores under
            ("general" default, plus "healthcare", "education", "tech", ...).
            θ(d) tightens the gate for sensitive domains.
        llm_fn: optional model hook `f(governed_prompt) -> response_text`. When
            supplied, the Governor runs the FULL pipeline — including STAGE 4,
            the Output Gate on the model's response — and the gate verdict +
            gated `final_response` are surfaced under plan["aatif"]. When None
            (the default, intent-reading mode), the pipeline stops at the
            governed prompt and no gate runs, preserving old behaviour.
        conversation_id: optional id enabling γ+ hysteresis and conversation
            memory across turns.
    """
    relationship_context = relationship_context or {}
    governor = _get_governor()
    degradation_warning = None   # set only on the fallback path

    if governor is not None:
        # ── PRIMARY: Governor (semantic S→P→R→Gate pipeline) ──
        # With an llm_fn hook the Governor runs end-to-end: S→P→R→prompt→LLM→
        # Output Gate. Without it, it stops at the governed prompt.
        gov_result = governor.process(
            incoming_text,
            domain=domain,
            llm_fn=llm_fn,
            conversation_id=conversation_id,
        )
        reading = _governed_to_reading(incoming_text, gov_result)
    else:
        # ── FALLBACK: Governor unavailable — "الدومين يقرر" ──
        # The domain decides the fallback strategy:
        #   HIGH-RISK → SAFE_STOP (complete halt, no regex fallback)
        #   OTHER     → regex fallback with LOUD degradation warning
        gov_result = None
        domain_lower = domain.lower() if domain else "general"

        if domain_lower in HIGH_RISK_DOMAINS:
            # ── SAFE_STOP: high-risk domain, no Governor = no service ──
            logger.warning(
                "SAFE_STOP: Governor unavailable for high-risk domain '%s'. "
                "Refusing to process — all ethical architecture bypassed. "
                "Message: %.80s", domain, incoming_text,
            )
            reading = IntentReading(
                surface_request=incoming_text,
                deep_intent="blocked_no_governor",
                emotional_state="clear",
                emotional_confidence=0.0,
                load_bearing=False,
                cbrn_flag=False,
                override_flag=False,
                governance_intact=False,
                mode="STOP",
                ambiguity_score=1.0,
                harm_score=1.0,
                softening_factor=0.0,
                directness=0.0,
                skills_to_activate=[],
                activation_evidence="Governor unavailable — SAFE_STOP for high-risk domain",
                dialect_detected=_detect_dialect_simple(incoming_text),
                time_context="",
                decision="SAFE_STOP",
                decision_reason=(
                    f"Safety system unavailable for high-risk domain '{domain}'. "
                    "Cannot process without full ethical architecture (S equation, "
                    "output_gate, hysteresis, judgment_memory, domain_protocols)."
                ),
            )
            degradation_warning = (
                f"BLOCKED: Safety system (Governor) is unavailable. "
                f"Domain '{domain}' requires full ethical architecture. "
                f"This request was refused — not processed with reduced protection."
            )
        else:
            # ── DEGRADED FALLBACK: regex engine with loud warning ──
            logger.warning(
                "DEGRADED: Governor unavailable — falling back to regex engine "
                "for domain '%s'. Ethical architecture (S equation, output_gate, "
                "hysteresis, judgment_memory, domain_protocols) is BYPASSED. "
                "Message: %.80s", domain, incoming_text,
            )
            engine = _get_fallback_engine()
            reading = engine.read(incoming_text, context=relationship_context)
            degradation_warning = (
                "WARNING: Operating in degraded mode. The safety Governor is "
                "unavailable — ethical architecture (S equation, output_gate, "
                "hysteresis, judgment_memory, domain_protocols) is not active. "
                "Results have limited safety protection. Human review recommended."
            )

    # Translate to old format
    surface = _detect_surface_intent(incoming_text, reading)
    hidden = _detect_hidden_intent(incoming_text, reading)
    greeting = _detect_greeting(incoming_text)

    intent_layers = IntentLayers(
        surface=surface,
        primary=hidden,
    )

    analysis_matrix = AnalysisMatrix(
        why_now_signal="general",
        wrong_answer_risk=_assess_risk(reading),
        user_knowledge_level="unaware",
        positioning_mode="none",
        value_focus=[],
        outcome_mode="none",
        trust_mode=_EMOTION_TO_TRUST.get(reading.emotional_state, "calm_direct"),
        intent_confidence=_assess_confidence(reading),
        ambiguity_flag=reading.ambiguity_score > 0.3,
        handling_mode=_DECISION_TO_HANDLING.get(reading.decision, "clarify_then_answer"),
        forbidden_moves=[],
    )

    result = IntentResult(
        incoming_text=incoming_text,
        normalized_text=_normalize_text(incoming_text),
        state=state,
        name="",
        business_type=business_type,
        greeting=greeting,
        relationship_context=relationship_context,
        intent_layers=intent_layers,
        analysis_matrix=analysis_matrix,
        aatif_reading=reading,
        degradation_warning=degradation_warning,
    )
    # Attach the full Governor result for downstream consumers that want the
    # complete audit trail (R style, P protocols, gate result, governed prompt).
    result._gov_result = gov_result
    return result


# Also expose normalize_text since api_server.py imports it
def normalize_text(text):
    return _normalize_text(text)


# ═══════════════════════════════════════════════════════════
#  Demo
# ═══════════════════════════════════════════════════════════

def demo():
    cases = [
        "السلام عليكم",
        "ابي أفهم وش السالفة",
        "كم السعر عندكم",
        "تعبت من المشروع مش عارف أكمل ازاي",
        "نظّم ملفاتي",
        "واش كيفاش بزاف خويا",
    ]

    governor = _get_governor()
    engine_name = "Governor (semantic S→P→R→Gate)" if governor else "IntentEngine (regex fallback)"

    print("=" * 60)
    print(f"  Pipeline Connector — {engine_name}")
    print("=" * 60)

    for text in cases:
        result = build_intent_result(text, state="", business_type="tech")
        plan = result.to_plan_dict()
        aatif = plan.get("aatif", {})

        print(f"\n  INPUT: {text}")
        print(f"  surface_intent: {plan['surface_intent']}")
        print(f"  hidden_intent:  {plan['hidden_intent']}")
        print(f"  trust_mode:     {plan['trust_mode']}")
        print(f"  handling_mode:  {plan['handling_mode']}")
        print(f"  confidence:     {plan['intent_confidence']}")
        if aatif:
            print(f"  ── AATIF ({aatif.get('engine', '?')}) ──")
            print(f"  emotion:   {aatif['emotional_state']} (load={aatif['load_bearing']})")
            print(f"  dialect:   {aatif['dialect']}")
            print(f"  decision:  {aatif['decision']}")
            print(f"  S/H:      S={aatif['softening']:.2f} H={aatif['harm']:.2f}")
            if aatif.get("r_style"):
                print(f"  R style:   {aatif['r_style']} (R={aatif.get('r_score', '?')})")
            if aatif.get("stage_reached"):
                print(f"  stage:     {aatif['stage_reached']}")

    print(f"\n{'=' * 60}")
    print("  المحافظ يشتغل — Governor routes the full pipeline")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    demo()
