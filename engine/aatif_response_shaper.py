#!/usr/bin/env python3
"""
AATIF Response Shaper — يشكّل الرد

Converts engine decisions (EXECUTE/CLARIFY/SAFE_STOP/SAFE_FREEZE)
into actual meaning_instructions for the LLM.

This is where governance becomes language.
Where math (S/F/H) becomes tone.
Where dialect detection becomes word choice.
Where emotional reading becomes compassion.

The Response Shaper does NOT generate the final text.
It builds the meaning_instruction — the soul of what the LLM should say.
The LLM then generates freely within that instruction.

Architecture:
    IntentReading (from engine) ──┐
    ConversationContext (memory) ──┼──→ ResponseShape ──→ meaning_instruction
    relationship_context ─────────┘

The meaning_instruction tells the LLM:
  - What to do (answer / ask / stop)
  - How to feel (warm / careful / gentle)
  - What dialect to use
  - What to avoid
  - Why this response matters

Usage:
    from aatif_response_shaper import AATIFResponseShaper

    shaper = AATIFResponseShaper()
    shape = shaper.shape(reading, memory_context)
    # shape.meaning_instruction → pass to LLM
    # shape.forbidden_phrases → pass to output_gate
    # shape.response_mode → for logging

Architect: Abdulmjeed Ibrahim Khenkar
"""


from dataclasses import dataclass, field
from typing import Any, List, Optional

# FN#070 PSP integration — stylistic (B5), never safety (B6). These imports
# pull the R-equation weights/signals and the PSP config table so the shaper
# can fold clarify_width into G_eff → R without re-deriving any of it.
from aatif_math import sigmoid
from aatif_r_equation import DEFAULT_WEIGHTS, DOMAIN_D_SIGNALS, DEFAULT_D_SIGNAL
from aatif_psp_detector import (
    PSP_PROFILE_BY_DOMAIN,
    DEFAULT_PSP_PROFILE,
    BOUNDED_HARD_MAX,
    TRADEOFF_REQUIRED_THRESHOLD,
)
import aatif_uncertainty_detector as _uc_mod
from aatif_uncertainty_detector import (
    UncertaintyDetector,
    UncertaintyReading,
    UncertaintyDisclosure,
)


# ═══════════════════════════════════════════════════════════
#  Duck-typed accessor (psp_reading / domain_config may be a
#  dataclass, dict, or arbitrary object)
# ═══════════════════════════════════════════════════════════


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# ═══════════════════════════════════════════════════════════
#  FN#070 PSP shaping constants
# ═══════════════════════════════════════════════════════════
#
#  clarify_width:  1   = normal           (not a decision point)
#                  2-3 = PSP-aware        (preserve a small bounded set)
#                  >3  = category choice  (wide realistic set)
#
#  clarify_width feeds G as G_eff BEFORE R is computed (consensus Round 3):
#      G_eff = G + κ · clarify_width_pressure
#      R     = σ(w₃·T + w₄·V + w₅·G_eff + w₆·D + bias)
#  R stays the style equation; PSP only nudges guidance density through G.

PSP_KAPPA = 0.5   # κ — scales clarify_width pressure into G_eff


# ═══════════════════════════════════════════════════════════
#  Response Shape — the output
# ═══════════════════════════════════════════════════════════


@dataclass
class PSPShaping:
    """
    FN#070 stylistic shaping result — produced from a PSPReading.

    Carries the G_eff/R arithmetic and the prompt instruction that preserves
    bounded alternatives. STYLISTIC ONLY — it touches no S, H, θ, or safety
    decision. psp_profile is a config lookup, never a computation.
    """
    active: bool = False
    psp_profile: str = DEFAULT_PSP_PROFILE
    clarify_width: int = 1
    clarify_width_pressure: float = 0.0
    g_signal: float = 0.0
    g_eff: float = 0.0
    r_score: float = 0.0
    bounded_count: int = 0
    require_tradeoffs: bool = False
    allow_single_path: bool = False
    instruction: str = ""


@dataclass
class ResponseShape:
    """What the shaper produces — everything the LLM needs to respond."""


    meaning_instruction: str
    response_mode: str
    dialect_instruction: str
    tone: str
    forbidden_phrases: list = field(default_factory=list)
    max_length: str = "medium"
    should_ask_question: bool = False
    emotional_note: str = ""
    context_note: str = ""
    # Final firmness: F = max(D*(1-S), k*H).
    firmness: float = 0.0
    # FN#070 PSP shaping (None unless a PSPReading was supplied).
    psp_shaping: Optional[PSPShaping] = None
    # Uncertainty disclosure (None unless uncertainty is significant).
    uncertainty_disclosure: Optional[UncertaintyDisclosure] = None




# ═══════════════════════════════════════════════════════════
#  Dialect instruction templates
# ═══════════════════════════════════════════════════════════


_DIALECT_INSTRUCTIONS = {
    "saudi":   "رد باللهجة السعودية. استخدم: وش، ليه، ابي، عندي، يعني، خلاص، طيب.",
    "kuwaiti": "رد باللهجة الكويتية. استخدم: شنو، ليش، أبي، جي، إي.",
    "emirati": "رد باللهجة الإماراتية. استخدم: شو، ليش، أبا، هيه.",
    "bahraini":"رد باللهجة البحرينية. استخدم: شنو، ليش، يالله.",
    "qatari":  "رد باللهجة القطرية. استخدم: شنو، ليش، هيه.",
    "omani":   "رد باللهجة العمانية.",
    "iraqi":   "رد باللهجة العراقية. استخدم: شلون، شنو، أريد، هسه.",
    "egyptian":  "رد باللهجة المصرية. استخدم: إيه، ليه، عايز، كده، ازاي.",
    "levantine": "رد باللهجة الشامية. استخدم: شو، كيف، بدي.",
    "maghrebi":  "رد باللهجة المغاربية. استخدم: واش، كيفاش، بزاف.",
    "msa":     "رد بالعربية الفصحى السهلة. بسيط وواضح بدون تعقيد.",
    "saudi_arabizi":   "The person is writing in Saudi Arabizi. Reply in Arabic but keep it casual.",
    "egyptian_arabizi": "The person is writing in Egyptian Arabizi. Reply in Arabic but keep it casual.",
    "gulf_arabizi":    "The person is writing in Gulf Arabizi. Reply in Arabic but keep it casual.",
    "levantine_arabizi":"The person is writing in Levantine Arabizi. Reply in Arabic but keep it casual.",
    "maghrebi_arabizi": "The person is writing in Maghrebi Arabizi. Reply in Arabic but keep it casual.",
    "english": "Reply in English. Keep it natural and warm.",
    "unknown": "رد بالعربية الفصحى السهلة. بسيط وواضح.",
}




# ═══════════════════════════════════════════════════════════
#  Tone templates
# ═══════════════════════════════════════════════════════════


_TONE_TEMPLATES = {
    "warm": "كن دافي ومريح. الشخص مرتاح — حافظ على الجو.",
    "gentle": "كن لطيف وحنون. الشخص يحمل ثقل — خفف عليه.",
    "direct": "كن مباشر وواضح. الشخص يبي جواب — عطه بدون لف ودوران.",
    "careful": "كن حذر ومتأني. في غموض أو خطر — اسأل قبل ما تجاوب.",
    "orient": "الشخص تايه. وجّهه بهدوء — خطوة خطوة.",
    "acknowledge": "الشخص محبط. اعترف بإحباطه أول — بعدين ساعده.",
    "match": "الشخص متحمس. شاركه حماسه — بس خلك واقعي.",
}




# ═══════════════════════════════════════════════════════════
#  Core forbidden phrases (always blocked)
# ═══════════════════════════════════════════════════════════


_ALWAYS_FORBIDDEN = [
    "طبقة حوكمة",
    "نظام محكوم",
    "governance layer",
    "as an AI",
    "كنموذج لغوي",
    "لا تقلق",
    "I cannot",
    "لا أستطيع",
]




# ═══════════════════════════════════════════════════════════
#  Firmness parameters (v9.7)
# ═══════════════════════════════════════════════════════════
#
#  F = max(F', k·H) — the final firmness equation.
#  F' = D · (1 − S)   — the pre-floor firmness equation.
#  S (softening_factor) measures mercy. D (Directness) scales per mode.
#  The harm floor is applied in compute_firmness.
_DEFAULT_DIRECTNESS = 1.0




# ═══════════════════════════════════════════════════════════
#  The Response Shaper
# ═══════════════════════════════════════════════════════════


class AATIFResponseShaper:
    """
    يشكّل الرد — Converts decisions into meaning instructions.
    """


    def __init__(self):
        self.identity = "عاطف"
        self.identity_description = "مساعد ذكي يشتغل بعطف — يقرا مشاعرك ويفهم وش تحتاج"


    def shape(self, reading, memory_context=None,
              psp_reading=None, psp_domain_config=None,
              uncertainty_reading: Optional[UncertaintyReading] = None,
              engine_result: Optional[dict] = None) -> ResponseShape:
        memory_context = memory_context or {}


        mode = self._decision_to_mode(reading.decision)
        tone = self._choose_tone(reading, memory_context)


        dialect = reading.dialect_detected or "unknown"
        dialect_instruction = _DIALECT_INSTRUCTIONS.get(dialect,
                              _DIALECT_INSTRUCTIONS["unknown"])


        forbidden = list(_ALWAYS_FORBIDDEN)
        forbidden.extend(self._context_forbidden(reading))


        max_length = self._choose_length(reading, memory_context)
        should_ask = mode == "clarify" or reading.ambiguity_score > 0.5
        emotional_note = self._build_emotional_note(reading)


        context_note = ""
        if memory_context:
            context_note = self._build_context_note(memory_context)


        directness = getattr(reading, "directness", None)
        firmness = self.compute_firmness(
            reading.softening_factor,
            directness,
            harm_score=getattr(reading, "harm_score", 0.0),
        )


        meaning = self._build_meaning_instruction(
            reading=reading,
            mode=mode,
            tone=tone,
            dialect_instruction=dialect_instruction,
            emotional_note=emotional_note,
            context_note=context_note,
            should_ask=should_ask,
            max_length=max_length,
        )


        # FN#070 — fold PSP shaping into the meaning instruction (stylistic).
        # Only appends bounded-alternative guidance when this turn is a
        # decision point. Computes G_eff/R but NEVER touches S/H/θ.
        psp_shaping = None
        if psp_reading is not None:
            psp_shaping = self.shape_psp(psp_reading, psp_domain_config)
            if psp_shaping.active and psp_shaping.instruction:
                meaning = meaning + "\n" + psp_shaping.instruction

        # Uncertainty disclosure — inject what's unknown into meaning_instruction
        # when uncertainty is significant. STYLISTIC ONLY — never touches S/H/θ.
        uncertainty_disclosure = None
        if (uncertainty_reading is not None
                and _uc_mod.UNCERTAINTY_ENABLED
                and uncertainty_reading.enabled):
            uncertainty_disclosure = UncertaintyDetector.build_disclosure(
                uncertainty_reading, engine_result or {}
            )
            if uncertainty_disclosure.disclosure_level != "none":
                disclosure_instruction = self._build_uncertainty_instruction(
                    uncertainty_disclosure
                )
                if disclosure_instruction:
                    meaning = meaning + "\n" + disclosure_instruction

        return ResponseShape(
            meaning_instruction=meaning,
            response_mode=mode,
            dialect_instruction=dialect_instruction,
            tone=tone,
            forbidden_phrases=forbidden,
            max_length=max_length,
            should_ask_question=should_ask,
            emotional_note=emotional_note,
            context_note=context_note,
            firmness=round(firmness, 3),
            psp_shaping=psp_shaping,
            uncertainty_disclosure=uncertainty_disclosure,
        )


    # ═══════════════════════════════════════════════════════
    #  FN#070 — PSP shaping (stylistic, B5, never safety)
    # ═══════════════════════════════════════════════════════

    def shape_psp(self, psp_reading, domain_config=None, *,
                  t_signal: float = 0.5, v_signal: float = 0.5,
                  g_signal: Optional[float] = None,
                  d_signal: Optional[float] = None,
                  weights: Optional[dict] = None) -> PSPShaping:
        """
        Consume a PSPReading → PSPShaping.

        Computes G_eff = G + κ·clarify_width_pressure, then feeds it through
        the R equation: R = σ(w₃·T + w₄·V + w₅·G_eff + w₆·D + bias). Builds the
        bounded-alternative instruction when this is a decision point.

        psp_profile is read from ``domain_config`` (a config lookup, exactly
        as θ comes from D) — never computed here. The base T/V/G/D signals come
        from the R pipeline; when omitted, neutral defaults are used so the
        shaper stays callable standalone.
        """
        w = dict(DEFAULT_WEIGHTS)
        if weights:
            w.update(weights)

        profile = self._resolve_psp_profile(domain_config)

        # Base R signals — neutral defaults when the R pipeline didn't pass them.
        if g_signal is None:
            g_signal = 0.45   # REquation's neutral gap default
        if d_signal is None:
            domain = (_get(domain_config, "domain", "") or "").lower()
            d_signal = DOMAIN_D_SIGNALS.get(domain, DEFAULT_D_SIGNAL)

        active = bool(_get(psp_reading, "is_decision_point", False))
        width = self._clarify_width(psp_reading)
        pressure = self._clarify_width_pressure(psp_reading)

        # G_eff — clarify_width pressure raises the gap signal before R.
        g_eff = max(0.0, min(1.0, g_signal + PSP_KAPPA * pressure))

        z = (w["w3"] * t_signal +
             w["w4"] * v_signal +
             w["w5"] * g_eff +
             w["w6"] * d_signal +
             w["bias"])
        r_score = sigmoid(z)

        closure_risk = float(_get(psp_reading, "closure_risk", 0.0) or 0.0)
        require_tradeoffs = active and closure_risk > TRADEOFF_REQUIRED_THRESHOLD
        allow_single_path = bool(_get(psp_reading, "user_requested_closure", False))

        instruction = ""
        if active:
            instruction = self._build_psp_instruction(
                psp_reading, profile, require_tradeoffs, allow_single_path)

        return PSPShaping(
            active=active,
            psp_profile=profile,
            clarify_width=width,
            clarify_width_pressure=round(pressure, 4),
            g_signal=round(float(g_signal), 4),
            g_eff=round(g_eff, 4),
            r_score=round(r_score, 4),
            bounded_count=int(_get(psp_reading, "bounded_count", 0) or 0),
            require_tradeoffs=require_tradeoffs,
            allow_single_path=allow_single_path,
            instruction=instruction,
        )

    def _clarify_width(self, psp_reading) -> int:
        """
        clarify_width from a PSPReading: 1 when not a decision point, else the
        bounded_count (floored to 2 — a decision point is at least PSP-aware),
        capped at the hard max.
        """
        if not _get(psp_reading, "is_decision_point", False):
            return 1
        count = int(_get(psp_reading, "bounded_count", 0) or 0)
        return min(max(count, 2), BOUNDED_HARD_MAX)

    def _clarify_width_pressure(self, psp_reading) -> float:
        """
        Normalize clarify_width into [0,1] pressure. width 1 → 0 (no PSP push),
        width = hard_max → 1.0 (maximum guidance density).
        """
        width = self._clarify_width(psp_reading)
        return max(0.0, (width - 1) / (BOUNDED_HARD_MAX - 1))

    def _resolve_psp_profile(self, domain_config) -> str:
        """
        Read psp_profile from domain config — a lookup, never a computation.
        Falls back to the domain→profile table, then the default profile.
        """
        if domain_config is None:
            return DEFAULT_PSP_PROFILE
        profile = _get(domain_config, "psp_profile", None)
        if profile:
            return profile
        domain = (_get(domain_config, "domain", "") or "").lower()
        return PSP_PROFILE_BY_DOMAIN.get(domain, DEFAULT_PSP_PROFILE)

    def _build_psp_instruction(self, psp_reading, profile: str,
                               require_tradeoffs: bool,
                               allow_single_path: bool) -> str:
        """
        Build the bounded-alternative instruction (Arabic, casual — matching
        the rest of the shaper). System proposes a bounded set; the human
        closes. Honours prompted closure, trade-off gating, and the
        Istikharah/Mashwarah tone for high-profile domains.
        """
        bounded = int(_get(psp_reading, "bounded_count", 0) or 0) or 3
        live = _get(psp_reading, "live_paths", []) or []
        labels = [_get(p, "label", "") for p in live]
        labels = [lab for lab in labels if lab]

        sections: List[str] = []
        sections.append(
            "هذا قرار — الشخص يختار بين مسارات. خلّينا نحصر الخيارات الواقعية "
            "ونخلّيها مفتوحة، ما نقفل على خيار واحد بدري."
        )
        sections.append(f"اعرض {bounded} خيارات واقعية على الأقل.")

        if labels:
            sections.append(f"الخيارات المطروحة حالياً: {'، '.join(labels)}.")

        if require_tradeoffs:
            sections.append(
                "القرار حسّاس — لكل خيار وضّح ميزة وعيب (benefit + limitation)."
            )
        else:
            sections.append("تقدر تعرض الخيارات بشكل مبسّط بدون تفصيل ثقيل.")

        if allow_single_path:
            sections.append(
                "الشخص طلب توصية مباشرة — بعد ما تحصر الخيارات، تقدر ترشّح "
                "خيار واحد بوضوح."
            )
        else:
            sections.append(
                "لا ترشّح خيار واحد قبل ما تعرض البدائل — القرار النهائي للشخص."
            )

        if profile == "high":
            sections.append(
                "خلّك مستشار، مو صاحب القرار النهائي — وضّح وخلّ الاختيار له."
            )

        return "\n".join(sections)


    def _decision_to_mode(self, decision: str) -> str:
        mapping = {
            "EXECUTE": "answer",
            "CLARIFY": "clarify",
            "SAFE_STOP": "stop",
            "SAFE_FREEZE": "freeze",
        }
        return mapping.get(decision, "clarify")


    def compute_firmness(self, softening_factor, directness=None,
                         harm_score=0.0, k=0.3) -> float:
        """
        Final firmness — F = max(F', k*H).

        F' = D * (1 - S) is the pre-floor firmness.
        k*H is the harm floor: even if mercy is high, firmness never drops
        below k * harm_score. This prevents being too soft on harmful requests.

        Args:
            softening_factor: S from the intent engine (0..1)
            directness:       D, mode-specific directness (default 1.0)
            harm_score:       H from the intent engine (0..1)
            k:                harm floor coefficient (default 0.3)
        Returns:
            F as a float, clamped to [0, max(D, k)].
        """
        D = _DEFAULT_DIRECTNESS if directness is None else float(directness)
        S = max(0.0, min(1.0, float(softening_factor)))
        H = max(0.0, min(1.0, float(harm_score)))
        k = float(k)
        f_prime = D * (1.0 - S)
        f_floor = k * H
        return max(f_prime, f_floor)


    def _choose_tone(self, reading, memory_context) -> str:
        if reading.load_bearing:
            return "gentle"


        emotion_tone = {
            "carrying_weight": "gentle",
            "frustrated": "acknowledge",
            "lost": "orient",
            "excited": "match",
            "clear": "direct",
        }


        tone = emotion_tone.get(reading.emotional_state, "warm")


        if memory_context:
            arc = memory_context.get("emotional_arc", {})
            if arc.get("escalated"):
                tone = "gentle"
            conv_tone = memory_context.get("conversation_tone", "")
            if conv_tone == "heavy" and tone not in ("gentle",):
                tone = "gentle"


        return tone


    def _choose_length(self, reading, memory_context) -> str:
        if reading.load_bearing or reading.emotional_state == "frustrated":
            return "short"
        if reading.decision == "CLARIFY":
            return "short"
        if reading.emotional_state == "excited":
            return "medium"
        turn_count = memory_context.get("turn_count", 0) if memory_context else 0
        if turn_count > 5:
            return "short"
        return "medium"


    def _context_forbidden(self, reading) -> list:
        forbidden = []
        if reading.load_bearing:
            forbidden.extend(["بسيطة", "ما عليك", "عادي", "don't worry", "it's easy", "just"])
        if reading.emotional_state == "frustrated":
            forbidden.extend(["بس", "مجرد", "simply"])
        return forbidden


    def _build_emotional_note(self, reading) -> str:
        notes = {
            "carrying_weight": "الشخص يحمل ثقل نفسي. تعامل بحنان. لا تستخف بمشاعره.",
            "frustrated": "الشخص محبط. اعترف بإحباطه أول شي. لا تقفز للحلول.",
            "lost": "الشخص تايه ومش فاهم وين يروح. وجّهه بهدوء.",
            "excited": "الشخص متحمس! شاركه حماسه بس خلك واقعي.",
            "clear": "",
        }
        return notes.get(reading.emotional_state, "")


    def _build_context_note(self, memory_context) -> str:
        parts = []
        arc = memory_context.get("emotional_arc", {})
        if arc.get("escalated"):
            parts.append("المحادثة تثاقلت — كن أكثر عطف من المعتاد.")
        if arc.get("load_bearing_count", 0) > 1:
            parts.append(f"مرّ بـ {arc['load_bearing_count']} لحظات ثقيلة — تنبّه.")
        topics = memory_context.get("topics_mentioned", [])
        if topics:
            parts.append(f"المواضيع اللي تكلمنا عنها: {', '.join(topics[:5])}")
        return " ".join(parts)


    def _build_meaning_instruction(self, reading, mode, tone,
                                    dialect_instruction, emotional_note,
                                    context_note, should_ask, max_length):
        sections = []


        sections.append(f"أنت {self.identity} — {self.identity_description}.")


        if mode == "answer":
            sections.append(f"الشخص سأل عن: {reading.deep_intent or 'شي عام'}")
            sections.append("جاوبه بوضوح وبساطة.")
        elif mode == "clarify":
            sections.append(f"الطلب فيه غموض (score: {reading.ambiguity_score:.1f}).")
            sections.append("اسأل سؤال واحد واضح عشان تفهم وش يبي بالضبط.")
            sections.append("لا تعطي جواب ناقص — الأفضل تسأل من إنك تخمن.")
        elif mode == "stop":
            sections.append(f"السبب: {reading.decision_reason}")
            sections.append("ارفض بلطف. وضح ليه ما تقدر تساعد بهالشي.")
            sections.append("لا تعطي بدائل خطيرة. كن صريح بس محترم.")
        elif mode == "freeze":
            sections.append("هذا الطلب يحتاج وقفة كاملة.")
            sections.append("قل بوضوح إنك ما تقدر تساعد بهالشي. بدون تبرير طويل.")


        sections.append(dialect_instruction)


        tone_instruction = _TONE_TEMPLATES.get(tone, _TONE_TEMPLATES["warm"])
        sections.append(tone_instruction)


        if emotional_note:
            sections.append(emotional_note)


        if context_note:
            sections.append(context_note)


        length_map = {
            "short": "خلّ الرد قصير — ٣ جمل أو أقل.",
            "medium": "خلّ الرد متوسط — ٥-٧ جمل.",
            "long": "الرد ممكن يكون طويل لو الموضوع يحتاج.",
        }
        sections.append(length_map.get(max_length, length_map["medium"]))


        if should_ask:
            sections.append("اختم بسؤال واحد واضح.")


        if reading.skills_to_activate:
            skills_str = ", ".join(reading.skills_to_activate)
            sections.append(f"المهارات المطلوبة: {skills_str}")


        return "\n".join(sections)

    # ═══════════════════════════════════════════════════════
    #  Uncertainty disclosure instruction builder
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _build_uncertainty_instruction(disclosure: UncertaintyDisclosure) -> str:
        """Build uncertainty disclosure instruction for meaning_instruction.

        Generates Arabic-language guidance for the LLM about what to
        disclose when the system's confidence is low. STYLISTIC ONLY.

        Disclosure levels:
          mild:        briefly acknowledge limits
          moderate:    explain what's uncertain
          significant: full disclosure with what's needed
        """
        if disclosure.disclosure_level == "none":
            return ""

        sections = []

        if disclosure.disclosure_level == "mild":
            sections.append(
                "في شوية عدم يقين بالموضوع — خلّ الرد يعكس هالشي بلطف. "
                "لا تستخدم كلمات قطعية مثل (أكيد، بالتأكيد، مستحيل)."
            )
        elif disclosure.disclosure_level == "moderate":
            sections.append(
                "في عدم يقين ملحوظ — وضّح للشخص إن الجواب ممكن "
                "ما يكون كامل أو دقيق ١٠٠٪."
            )
            if disclosure.what_unknown:
                sections.append(f"اللي مش واضح: {disclosure.what_unknown}")
            if disclosure.what_known:
                sections.append(f"اللي نعرفه: {disclosure.what_known}")
        elif disclosure.disclosure_level == "significant":
            sections.append(
                "في عدم يقين كبير — لازم توضح للشخص إن المعلومات ممكن "
                "تكون ناقصة وتحتاج تأكيد."
            )
            if disclosure.what_unknown:
                sections.append(f"اللي مش واضح: {disclosure.what_unknown}")
            if disclosure.why_unknown:
                sections.append(f"ليش: {disclosure.why_unknown}")
            if disclosure.what_needed:
                sections.append(f"اللي نحتاجه: {disclosure.what_needed}")
            if disclosure.what_known:
                sections.append(f"اللي نعرفه: {disclosure.what_known}")

        return "\n".join(sections)


# ═══════════════════════════════════════════════════════════
#  Demo
# ═══════════════════════════════════════════════════════════


def demo():
    """Show response shaping for different scenarios."""


    class FakeReading:
        def __init__(self, **kwargs):
            defaults = {
                'decision': 'EXECUTE', 'decision_reason': '',
                'mode': 'NORMAL', 'emotional_state': 'clear',
                'emotional_confidence': 0.8, 'load_bearing': False,
                'dialect_detected': 'saudi', 'ambiguity_score': 0.1,
                'harm_score': 0.0, 'softening_factor': 0.5,
                'skills_to_activate': [], 'deep_intent': '',
            }
            defaults.update(kwargs)
            for k, v in defaults.items():
                setattr(self, k, v)


    shaper = AATIFResponseShaper()


    scenarios = [
        {
            "name": "سلام عادي",
            "reading": FakeReading(
                decision="EXECUTE", emotional_state="clear",
                dialect_detected="saudi", deep_intent="greeting",
            ),
            "memory": None,
        },
        {
            "name": "شخص يحمل ثقل",
            "reading": FakeReading(
                decision="EXECUTE", emotional_state="carrying_weight",
                load_bearing=True, dialect_detected="egyptian",
                deep_intent="needs_support",
            ),
            "memory": {
                "turn_count": 4,
                "emotional_arc": {"escalated": True, "load_bearing_count": 2},
                "conversation_tone": "heavy",
                "topics_mentioned": ["project", "problem"],
            },
        },
        {
            "name": "طلب غامض",
            "reading": FakeReading(
                decision="CLARIFY", emotional_state="lost",
                dialect_detected="saudi", ambiguity_score=0.7,
                deep_intent="unclear_request",
            ),
            "memory": None,
        },
        {
            "name": "طلب خطير",
            "reading": FakeReading(
                decision="SAFE_STOP", emotional_state="clear",
                dialect_detected="msa", harm_score=0.8,
                decision_reason="potential_harm",
            ),
            "memory": None,
        },
    ]


    print("=" * 60)
    print("  Response Shaper — يشكّل الرد")
    print("=" * 60)


    for scenario in scenarios:
        shape = shaper.shape(scenario["reading"], scenario["memory"])


        print(f"\n{'─' * 60}")
        print(f"  Scenario: {scenario['name']}")
        print(f"  Mode: {shape.response_mode} | Tone: {shape.tone}")
        print(f"  Length: {shape.max_length} | Ask question: {shape.should_ask_question}")
        print(f"  Softening S: {scenario['reading'].softening_factor} | Firmness F'=D·(1-S): {shape.firmness}")
        if shape.forbidden_phrases:
            extra = [p for p in shape.forbidden_phrases if p not in _ALWAYS_FORBIDDEN]
            if extra:
                print(f"  Extra forbidden: {extra}")
        print(f"\n  ── meaning_instruction ──")
        for line in shape.meaning_instruction.split("\n"):
            print(f"  {line}")


    print(f"\n{'=' * 60}")
    print(f"  الحوكمة صارت لغة — والرياضيات صارت عطف")
    print(f"{'=' * 60}")




if __name__ == "__main__":
    demo()