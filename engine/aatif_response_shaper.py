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
from typing import Optional




# ═══════════════════════════════════════════════════════════
#  Response Shape — the output
# ═══════════════════════════════════════════════════════════


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


    def shape(self, reading, memory_context=None) -> ResponseShape:
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
        )


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