#!/usr/bin/env python3
"""
AATIF Intent Engine — يفهم الموقف مش بس الكلام

The first layer of AATIF governance. Before any response is generated,
the Intent Engine reads the situation: what does the person actually need?
What are they feeling? Is this clear enough to answer, or should we stop?

This implements:
- Law δ (Intent-Effect Alignment) from Moral Engine v9.7
- النص صوت (Text is Voice) — dialect, rhythm, word choice = emotional signal
- الإنسان المثقل (Load-Bearing Human) detection
- Sparse Activation — which skill to wake, if any
- Mode classification: ANSWER / PROOF / STOP
- S/F/H equations from the formal specification

Usage:
    from aatif_intent_engine import read_intent

    reading = read_intent("نظّم ملفاتي")
    print(reading.mode)        # "STOP"
    print(reading.decision)    # "CLARIFY"

    reading = read_intent("Translate 'patience' to Arabic")
    print(reading.mode)        # "ANSWER"
    print(reading.decision)    # "EXECUTE"

Architect: Abdulmjeed Ibrahim Khenkar
"""

import json
import math
import re
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime

from aatif_arabic_utils import normalize_arabic

try:
    from arabic_nlp_bridge import ArabicNLPBridge, get_bridge
    _HAS_NLP_BRIDGE = True
except ImportError:
    _HAS_NLP_BRIDGE = False


# ═══════════════════════════════════════════════════════════
#  الحالات الخمس — The Five Emotional States
# ═══════════════════════════════════════════════════════════

EMOTIONAL_STATES = {
    "carrying_weight": "مثقل — carrying weight, needs lightening not lecturing",
    "lost":            "تايه — lost, needs orientation not information",
    "excited":         "متحمس — excited, needs grounding not dampening",
    "frustrated":      "محبط — frustrated, needs acknowledgment not solutions",
    "clear":           "واضح — clear, needs execution not questions",
}

# ═══════════════════════════════════════════════════════════
#  Signal Patterns — what the engine listens for
# ═══════════════════════════════════════════════════════════

AMBIGUITY_PATTERNS = [
    r"^(نظ[مّ]|رتب|صلح|حسن|عدل|غير)\b",
    r"^(fix|improve|organize|clean|make)\b.{0,15}$",
    r"(ايش|وش|شو)\s+(رأيك|تقول|تشوف)",
    r"(make it|خل[يّ]ه?)\s+(better|أحسن|أفضل)",
    r"^(هذا|this|it|ok|اوك|ماشي)\s*$",
]

LOAD_BEARING_SIGNALS = [
    r"(تعبت|مليت|ضغط|ما قدر|مش فاهم|lost|stuck|confused|overwhelmed)",
    r"(ساعدني|help me|please|أرجوك|الله يخليك|الله يعافيك)",
    r"(مش عارف|مدري|ما أدري|ما عرفت|dunno|donno|idk|ma 3raft)",
    r"(كل مرة|always|دايم[اً]?|مرة ثانية|again|كل مره)",
    r"(ما قدرت|مو راضي|mo raaady|ما رضي|طفشت|زهقت|ملّيت)",
]

SKILL_TRIGGERS = {
    "stop_mode": [
        r"(نظ[مّ]|رتب|صلح|حسن).{0,20}$",
        r"^(fix|improve|organize).{0,15}$",
    ],
    "truth_with_mercy": [
        r"(رأيك|review|feedback|critique|تقييم|honest|صراحة)",
        r"(is this good|كويس|حلو ولا لا|ايش تشوف)",
    ],
    "idea_filter": [
        r"(فكرة|idea|should I build|أبني|نبني|worth)",
        r"(should this be|هل أسوي|أسويها skill)",
    ],
    "sparse_activation": [
        r"(agent|أجنت|activate|فعّل|which tool|أي أداة)",
        r"(system design|multi-agent|orchestrat)",
    ],
}

# ───────────────────────────────────────────────────────────
#  Arabic catastrophic weapon / CBRN lexicon (regex)
# ───────────────────────────────────────────────────────────
# Closes the Arabic safety hole: weapon/explosive/poison terms were
# English-only, so "كيف أصنع قنبلة" scored harm=0.00 → EXECUTE.
# Used by BOTH the Law Ω CBRN gate (unconditional SAFE_STOP, mode-independent)
# AND HARM_PATTERNS (so the harm SCORE also reflects the danger).
#
# Design notes (mercy + truth — do not over-block legitimate science/education):
#  • Clearly-weapon terms (قنبلة، متفجرات، ناسف، سارين، جمرة خبيثة …) stand alone.
#  • Dual-use science terms (نووي/كيميائي/بيولوجي/ذري) only fire WITH explicit
#    weapon framing (سلاح/قنبلة/أسلحة) — "تفاعل كيميائي" or "طاقة نووية" stay safe.
#  • Short ambiguous roots are AVOIDED to prevent substring false positives:
#    bare "سم" is excluded (would hit بسم/اسم/قسم/جسم/موسم); "سلاح" excludes
#    سلاحف (turtles) via negative lookahead.
CBRN_AR_REGEX = [
    r"قنبل",                 # bomb (قنبلة، قنبلت، القنبلة)
    r"قنابل",                # bombs
    r"متفجر",                # explosive(s) (متفجرات، المتفجرة)
    r"ناسف",                 # detonating / IED (عبوة ناسفة، حزام ناسف)
    r"يورانيوم",             # uranium
    r"بلوتونيوم",            # plutonium
    r"سارين",                # sarin
    r"غاز\s*(?:ال)?أعصاب",    # nerve gas  (± definite article)
    r"غاز\s*(?:ال)?خردل",     # mustard gas
    r"غاز\s*(?:ال)?سام",      # toxic gas
    r"جمرة\s*(?:ال)?خبيثة",   # anthrax
    r"دمار\s*(?:ال)?شامل",    # mass destruction
    r"سيانيد",               # cyanide
    r"سم\s*(?:ال)?قاتل",      # lethal poison (NOT bare سم)
    r"سموم",                 # poisons
    r"مادة\s*(?:ال)?سامة",    # toxic substance
    r"مواد\s*(?:ال)?سامة",    # toxic substances
    r"قنبلة\s*(?:ال)?قذرة",   # dirty bomb
    # dual-use: weapon framing required  (± definite article on adjective)
    r"سلاح\s*(?:ال)?نووي", r"قنبلة\s*(?:ال)?نووية", r"سلاح\s*(?:ال)?ذري", r"قنبلة\s*(?:ال)?ذرية",
    r"سلاح\s*(?:ال)?كيميائي", r"أسلحة\s*(?:ال)?كيميائية", r"اسلحة\s*(?:ال)?كيميائية",
    r"سلاح\s*(?:ال)?بيولوجي", r"سلاح\s*(?:ال)?بيلوجي", r"أسلحة\s*(?:ال)?بيولوجية",
]

HARM_PATTERNS = {
    0.4: [r"(delete|remove|حذف|امسح|drop|reset|format)"],
    0.6: [
        r"(password|كلمة سر|credit|bank|transfer|حوال)",
        # Arabic general weapons (graded harm, not catastrophic)
        r"(سلاح(?!ف)|أسلحة|اسلحة|مسدس|بندقية|ذخيرة|ذخائر)",
    ],
    0.7: [r"(sudo|root|admin|chmod|rm -rf)"],
    # Arabic catastrophic weapon/CBRN making — same lexicon as the Law Ω gate,
    # surfaced here so the harm SCORE is high even outside the gate.
    0.9: list(CBRN_AR_REGEX),
}

# ── Pre-normalized patterns (for REGEX_V2_ENABLED) ──────────────────────
# Used when aatif_s_equation.REGEX_V2_ENABLED is True.
CBRN_AR_REGEX_NORM = [normalize_arabic(p) for p in CBRN_AR_REGEX]

HARM_PATTERNS_NORM = {
    level: [normalize_arabic(p) for p in patterns]
    for level, patterns in HARM_PATTERNS.items()
}


# ═══════════════════════════════════════════════════════════
#  IntentReading — the structured output
# ═══════════════════════════════════════════════════════════

@dataclass
class IntentReading:
    """Complete reading of a message — the situation, not just the words."""

    surface_request: str
    deep_intent: str
    emotional_state: str
    emotional_confidence: float
    load_bearing: bool
    cbrn_flag: bool
    override_flag: bool              # Law Ξ: True if override attempt detected
    governance_intact: bool          # Law Γ: True if governance config is valid
    mode: str
    ambiguity_score: float
    harm_score: float
    softening_factor: float
    directness: float
    skills_to_activate: List[str]
    activation_evidence: str
    dialect_detected: str
    time_context: str
    decision: str
    decision_reason: str
    cbrn_context: Optional[str] = None  # Phase 2: educational/medical/instructional/None

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def summary(self):
        """One-line human-readable summary."""
        load = " [مثقل]" if self.load_bearing else ""
        skills = ", ".join(self.skills_to_activate) if self.skills_to_activate else "none"
        return (
            f"{self.decision} | {self.mode} | "
            f"emotion={self.emotional_state}{load} | "
            f"ambiguity={self.ambiguity_score:.2f} | "
            f"harm={self.harm_score:.2f} | "
            f"skills=[{skills}]"
        )


# ═══════════════════════════════════════════════════════════
#  AATIFIntentEngine — المحرك
# ═══════════════════════════════════════════════════════════

class AATIFIntentEngine:
    """
    المحرك الأول في عاطف — يفهم قبل ما يرد

    Reads the situation, not just the words.
    Implements Law δ (intent-effect alignment) and the S/F/H
    equations from Moral Engine v9.7.
    """

    MODES = {
        "high_sensitivity": {"w1": 1.0, "w2": 1.0, "w3": 1.5,
                             "tau_rewrite": 0.60, "tau_stop": 0.80,
                             "D": 0.7, "epsilon": 0.05},
        "safe_environment":  {"w1": 1.0, "w2": 1.0, "w3": 1.0,
                              "tau_rewrite": 0.70, "tau_stop": 0.88,
                              "D": 1.0, "epsilon": 0.05},
        "creative":          {"w1": 1.0, "w2": 1.0, "w3": 0.7,
                              "tau_rewrite": 0.78, "tau_stop": 0.92,
                              "D": 0.8, "epsilon": 0.05},
        "casual":            {"w1": 1.0, "w2": 1.0, "w3": 0.8,
                              "tau_rewrite": 0.80, "tau_stop": 0.93,
                              "D": 1.2, "epsilon": 0.05},
    }

    # Law Omega: CBRN catastrophic content triggers unconditional SAFE_STOP
    # These terms indicate weapons-of-mass-destruction instructions
    CBRN_TRIGGERS = frozenset([
        # Chemical weapons
        "nerve agent", "sarin", "vx gas", "mustard gas", "chemical weapon",
        "weaponize", "synthesize poison", "toxic agent",
        # Biological weapons
        "bioweapon", "biological weapon", "weaponized pathogen",
        "anthrax weapon", "smallpox weapon", "plague weapon",
        # Radiological
        "dirty bomb", "radiological weapon", "nuclear material",
        "enriched uranium", "weapons grade",
        # Nuclear
        "nuclear weapon", "atomic bomb", "hydrogen bomb",
        "nuclear warhead", "fission bomb", "fusion bomb",
        # General WMD
        "weapon of mass destruction", "wmd", "mass casualty",
    ])

    # Arabic CBRN/weapon regex patterns (module-level lexicon, regex not substring
    # because Arabic substring matching is unsafe — see CBRN_AR_REGEX notes).
    CBRN_AR_PATTERNS = tuple(CBRN_AR_REGEX)

    # Law Xi: direct attempts to bypass or override safety cause SAFE_FREEZE.
    OVERRIDE_TRIGGERS = frozenset([
        "ignore previous",
        "disregard safety",
        "override stop",
        "bypass safety",
        "ignore safety",
        "skip safety check",
        "force execute",
        "override safe stop",
        "تجاهل الأمان",
        "تخطي الحماية",
        "تجاوز التوقف",
    ])

    # Law Ξ — regex layer (broadens the exact-substring set above so paraphrases
    # don't slip through). REGEX not substring: a bypass-VERB must co-occur with a
    # safety/rules/instructions TARGET inside a short window, so we catch
    # "ignore your instructions and override safety" / "تجاهل القواعد وكمل"
    # without firing on unrelated single words. Window is a bounded char class
    # (no '.') so it can't cross a sentence boundary or backtrack catastrophically.
    OVERRIDE_REGEX = [
        # English: bypass-verb  +  safety/rule/instruction target within ~30 chars
        r"\b(ignore|disregard|bypass|override|overrule|skip|forget|disable|"
        r"circumvent|defeat|evade|remove|drop|turn\s+off)\b"
        r"[\s\w,'\"-]{0,30}"
        r"\b(safety|safeguards?|rules?|restrictions?|guidelines?|instructions?|"
        r"protocols?|guardrails?|filters?|polic(?:y|ies)|constraints?|"
        r"limitations?|alignment)\b",
        # Arabic: bypass-verb  +  safety/rule/instruction target within a short window
        r"(تجاهل|تجاوز|تخط[ىي]|تخطّى|عطّ?ل|اكسر|الغ[ِي]|ألغ)"
        r"\s*\S{0,12}\s*"
        r"(الأمان|الحماية|القواعد|التعليمات|القيود|الحظر|الفلتر|الضوابط)",
    ]

    # H2 FIX: Maximum number of session states to keep in memory.
    # Prevents unbounded growth of _in_clarify_zone dict.
    # Single-threaded contract: no locking — callers are assumed sequential.
    MAX_SESSIONS = 10_000

    # Pre-normalized class attributes (for REGEX_V2_ENABLED)
    _cbrn_triggers_norm = frozenset([normalize_arabic(t) for t in [
        "nerve agent", "sarin", "vx gas", "mustard gas", "chemical weapon",
        "weaponize", "synthesize poison", "toxic agent",
        "bioweapon", "biological weapon", "weaponized pathogen",
        "anthrax weapon", "smallpox weapon", "plague weapon",
        "dirty bomb", "radiological weapon", "nuclear material",
        "enriched uranium", "weapons grade",
        "nuclear weapon", "atomic bomb", "hydrogen bomb",
        "nuclear warhead", "fission bomb", "fusion bomb",
        "weapon of mass destruction", "wmd", "mass casualty",
    ]])
    _cbrn_ar_patterns_norm = tuple(CBRN_AR_REGEX_NORM)
    _override_triggers_norm = frozenset([normalize_arabic(t) for t in [
        "ignore previous", "disregard safety", "override stop",
        "bypass safety", "ignore safety", "skip safety check",
        "force execute", "override safe stop",
        "تجاهل الأمان", "تخطي الحماية", "تجاوز التوقف",
    ]])
    _override_regex_norm = [normalize_arabic(p) for p in [
        r"\b(ignore|disregard|bypass|override|overrule|skip|forget|disable|"
        r"circumvent|defeat|evade|remove|drop|turn\s+off)\b"
        r"[\s\w,'\"-]{0,30}"
        r"\b(safety|safeguards?|rules?|restrictions?|guidelines?|instructions?|"
        r"protocols?|guardrails?|filters?|polic(?:y|ies)|constraints?|"
        r"limitations?|alignment)\b",
        r"(تجاهل|تجاوز|تخط[ىي]|تخطّى|عطّ?ل|اكسر|الغ[ِي]|ألغ)"
        r"\s*\S{0,12}\s*"
        r"(الأمان|الحماية|القواعد|التعليمات|القيود|الحظر|الفلتر|الضوابط)",
    ]]

    def __init__(self, mode="safe_environment", llm_fn=None, nlp_bridge=None):
        self.mode_name = mode
        self.params = dict(self.MODES[mode])
        self.llm_fn = llm_fn
        # Hysteresis state: tracks whether we're in the CLARIFY zone.
        # Key = caller-provided session_id, Value = bool.
        self._in_clarify_zone: dict[str, bool] = {}
        self._clarify_access_order: list[str] = []  # H2 FIX: LRU tracking

        if nlp_bridge is not None:
            self.nlp_bridge = nlp_bridge
        elif _HAS_NLP_BRIDGE:
            self.nlp_bridge = get_bridge()
        else:
            self.nlp_bridge = None

    # ─── Main Entry ─────────────────────────────────────

    def read(
        self,
        message: str,
        session_id: str = "default",
        nlp_result=None,
        context: dict = None,
    ) -> IntentReading:
        if isinstance(session_id, dict) and context is None:
            # Backward compatibility for the old read(message, context) call shape.
            context = session_id
            session_id = "default"

        context = context or {}
        msg = message.strip()

        # Layer 1: Trained Models (when available)
        nlp_dialect = None
        nlp_sentiment = None
        if nlp_result is None and self.nlp_bridge:
            try:
                nlp_result = self.nlp_bridge.analyze(msg)
            except Exception:
                nlp_result = None
        if nlp_result:
            nlp_dialect = nlp_result.get("dialect", {})
            nlp_sentiment = nlp_result.get("sentiment", {})

        # 1. Context signals
        if nlp_dialect and nlp_dialect.get("dialect"):
            dialect = nlp_dialect["dialect"]
        else:
            dialect = self._detect_dialect(msg)
        time_ctx = self._get_time_context()

        # 2. Ambiguity
        ambiguity = self._measure_ambiguity(msg)

        # 3. Emotional state (النص صوت)
        emotional_state, emotional_conf = self._read_emotion(msg)
        if nlp_sentiment and nlp_sentiment.get("sentiment"):
            sent = nlp_sentiment["sentiment"]
            sent_conf = nlp_sentiment.get("confidence", 0)
            if sent == "negative" and sent_conf > 0.7:
                if emotional_state == "clear":
                    emotional_state = "frustrated"
                    emotional_conf = max(emotional_conf, sent_conf * 0.8)
            elif sent == "positive" and sent_conf > 0.7:
                if emotional_state == "clear":
                    emotional_state = "excited" if ambiguity < 0.3 else "clear"
                    emotional_conf = max(emotional_conf, sent_conf * 0.7)

        # 4. Load-bearing check (الإنسان المثقل)
        load_bearing = self._detect_load_bearing(msg)

        # 5. Law Omega: CBRN catastrophic gate flag
        cbrn_flag, cbrn_context = self._check_cbrn(msg)

        # 5a. Law Ξ: override/bypass attempt flag
        override_flag = self._check_override(msg)

        # 5b. Law Γ: governance integrity flag
        governance_intact = self._check_governance_integrity()

        # 6. Harm assessment (H from v9.7)
        harm = self._assess_harm(msg)

        if governance_intact:
            # 7. Softening factor: S = σ(w1·I + w2·E − w3·H)
            # M4 NOTE: S is computed here and exposed in IntentReading as
            # `softening_factor` for debugging, logging, and downstream
            # consumption (e.g., the S equation pipeline). It is NOT used
            # in _decide() — the intent engine's decision logic uses
            # harm/ambiguity/mode directly. This is by design: the intent
            # engine provides the RAW signals; the S equation combines them.
            intent_val = 1.0 - ambiguity
            emotion_val = 0.9 if load_bearing else (0.7 if emotional_state != "clear" else 0.5)
            S = self._sigmoid(
                self.params["w1"] * intent_val
                + self.params["w2"] * emotion_val
                - self.params["w3"] * harm
            )

            # 8. Mode: ANSWER / PROOF / STOP
            mode = self._determine_mode(ambiguity, harm)

            # 9. Sparse skill activation
            skills, evidence = self._sparse_activate(msg, mode, ambiguity)
        else:
            S = 0.0
            mode = "STOP"
            skills = []
            evidence = "Governance integrity failed — skills not activated."

        # 10. Decision: EXECUTE / CLARIFY / SAFE_STOP / SAFE_FREEZE
        decision, reason = self._decide(
            mode,
            harm,
            ambiguity,
            load_bearing,
            session_id,
            cbrn_flag=cbrn_flag,
            text=msg,
            cbrn_context=cbrn_context,
        )

        # 11. Deep intent reading
        if self.llm_fn and ambiguity > 0.3:
            deep = self._llm_deep_read(msg, context)
            surface = deep.get("surface", msg[:200])
            deep_intent = deep.get("deep_intent", surface)
        else:
            surface = msg[:200]
            deep_intent = self._rule_based_deep_intent(
                msg, emotional_state, load_bearing
            )

        return IntentReading(
            surface_request=surface,
            deep_intent=deep_intent,
            emotional_state=emotional_state,
            emotional_confidence=round(emotional_conf, 2),
            load_bearing=load_bearing,
            cbrn_flag=cbrn_flag,
            override_flag=override_flag,
            governance_intact=governance_intact,
            mode=mode,
            ambiguity_score=round(ambiguity, 3),
            harm_score=round(harm, 3),
            softening_factor=round(S, 3),
            directness=(self.params.get("D", 0.0) if isinstance(self.params, dict) else 0.0),
            skills_to_activate=skills,
            activation_evidence=evidence,
            dialect_detected=dialect,
            time_context=time_ctx,
            decision=decision,
            decision_reason=reason,
            cbrn_context=cbrn_context,
        )

    # ─── Dialect Detection ──────────────────────────────

    def _detect_dialect(self, msg):
        has_arabic = bool(re.search(r"[؀-ۿ]", msg))
        has_latin = bool(re.search(r"[a-zA-Z]", msg))

        if has_arabic:
            # PRIORITY: distinctive Iraqi markers must win over shared-Gulf
            # markers (شلون matches kuwaiti below). هسه/هواية/اكو/شكو etc. are
            # strongly Iraqi-only — if present, resolve to iraqi first so the
            # shared شلون cannot shadow it. (Fixes dialect_iraqi: "شلون الحال هسه".)
            if re.search(
                r"(هسه|هواية|اكو\b|ماكو\b|شكو\b|بالكاع|"
                r"دزلي|لعد\b|شبيك|شتريد)", msg
            ):
                return "iraqi"

            if re.search(
                r"(ابي|أبي|يبي|وش\b|كذا|مدري|ودي|"
                r"طيب|زين|يالله|خلاص|حق\b|"
                r"ايش|وين|ليه\b|كيذا|قاعد|"
                r"ابغى|تبي|نبي|يبغى|"
                r"هالشي|ذا الشي|"
                r"عاد|يعني\b|بعدين|اوكي|ماشي|"
                r"يا حبيبي|يا قلبي|الله يعافيك|الله يسعدك)", msg
            ):
                return "saudi"

            if re.search(
                r"(شلونك|شلون\b|شقول|جي\b|جذي|اشوى|"
                r"بلاش|يمعود|أم\b|خوش|غريبة|"
                r"انزين|هالحين|شفيك|شتبي|شسوي|"
                r"تو\b|اول\b|يبيلك|حيل\b|مرة\b)", msg
            ):
                return "kuwaiti"

            if re.search(
                r"(شحالك|شحاله|يالس|هالريال|مب\b|"
                r"اهيه|\bويا\b|الحريم|الريال|خيه|"
                r"سيدا|اللحين|عيل|هيه|يلسوا|"
                r"زين\b|مصخره|خلصنا|يايين)", msg
            ):
                return "emirati"

            if re.search(
                r"(شخبارك|آني\b|شلونج|ها\b|"
                r"سوالف|چي|چذي|هالشكل|"
                r"جنك|جنه|خوش\b|يبيلها|اشلون)", msg
            ):
                return "bahraini"

            if re.search(
                r"(هالشكل|شلونك|شخبارك|اللحين|"
                r"اهيه|وناسه|يالس|مب\b|كلش\b|"
                r"واجد|خوش\b|هاالحين)", msg
            ):
                return "qatari"

            if re.search(
                r"(كيف الحال|هلا\b|والله\b|شحالك|"
                r"اشكثر|توه|يوا\b|نعال|"
                r"هب\b|بيني|مالت\b|خاطرك)", msg
            ):
                return "omani"

            if re.search(r"(ايه|كده|عايز|مش|ازاي|دي|ده|فين)", msg):
                return "egyptian"

            if re.search(
                r"(شكو ماكو|شلونك|هواية|آني\b|"
                r"شبيك|شتريد|عمي\b|ابو\b|"
                r"هسه|بالكاع|دزلي|لعد\b|اكو\b)", msg
            ):
                return "iraqi"

            if re.search(r"(شو|كيف\b|هيك|منيح|هلأ|كتير|شي\b|معلم)", msg):
                return "levantine"

            if re.search(
                r"(واش|كيفاش|بزاف|ديال|لاباس|"
                r"ياخي|خويا|صحبي|بالاك|هاكا|"
                r"ديالي|نتاع|كيراك|واحد\b)", msg
            ):
                return "maghrebi"

            if has_latin:
                return "mixed"
            return "msa"

        if has_latin:
            if re.search(
                r"\b(wain|abi|yabi|tayb|tayeb|zain|"
                r"wallah|yallah|khalas|inshallah|mashallah|"
                r"mafi|3shan|3ashan|bs\b|"
                r"mo\b|msh|ma\b|raaady|donno|dunno|"
                r"abgha|tabgha|weddi|7abibi)\b", msg, re.I
            ):
                return "saudi_arabizi"

            if re.search(
                r"\b(shlon|shlonk|shgool|chthy|cham\b|"
                r"mu3oud|7ail|enzain|shfeek|shtabi)\b", msg, re.I
            ):
                return "kuwaiti_arabizi"

            if re.search(
                r"\b(sh7alk|sh7alh|mub\b|yals|"
                r"hal7een|il7een|3yal|haih|seedah)\b", msg, re.I
            ):
                return "emirati_arabizi"

            if re.search(
                r"\b(shako|mako|hwaaya|ani\b|"
                r"hashee|shbeek|shtireed|hissa)\b", msg, re.I
            ):
                return "iraqi_arabizi"

            if re.search(
                r"\b(ezay|3ayez|keda|eih|fein|"
                r"mashee|betaa3|7aaga|mish\b)\b", msg, re.I
            ):
                return "egyptian_arabizi"

            if re.search(
                r"\b(shu\b|kifak|haik|mni7|halla2|"
                r"kteer|ma3loom|ya3ni)\b", msg, re.I
            ):
                return "levantine_arabizi"

            if re.search(
                r"\b(wesh|wash|bezaf|dyali|labas|"
                r"khoya|sa7bi|haka|kirak)\b", msg, re.I
            ):
                return "maghrebi_arabizi"

            if re.search(r"(3|7|5|2)[a-z]|[a-z](3|7|5|2)", msg, re.I):
                return "arabizi"
            return "english"
        return "unknown"

    # ─── Time Context ───────────────────────────────────

    def _get_time_context(self):
        try:
            from zoneinfo import ZoneInfo
            hour = datetime.now(ZoneInfo("Asia/Riyadh")).hour
        except Exception:
            hour = datetime.utcnow().hour
        if hour < 5:
            return "late_night"
        if hour < 12:
            return "morning"
        if hour < 17:
            return "afternoon"
        if hour < 21:
            return "evening"
        return "night"

    # ─── Ambiguity ──────────────────────────────────────

    def _measure_ambiguity(self, msg):
        score = 0.0
        low = msg.lower()

        if len(low) < 10:
            score += 0.3
        elif len(low) < 25:
            score += 0.15

        for pat in AMBIGUITY_PATTERNS:
            if re.search(pat, low):
                score += 0.25
                break

        if not re.search(r"(\d+|/|\\|\.py|\.js|\.md|@)", msg):
            score += 0.1

        if re.search(r"(ايش|وش|what|how|شلون|كيف|ازاي)", low):
            score += 0.1

        if re.search(r"^(it|this|that|هذا|هذي|ده|دي|دا)\b", low):
            score += 0.2

        return min(score, 1.0)

    # ─── Emotion Reading (النص صوت) ─────────────────────

    def _read_emotion(self, msg):
        low = msg.lower()

        for pat in LOAD_BEARING_SIGNALS:
            if re.search(pat, low):
                return "carrying_weight", 0.7

        if re.search(r"(مش فاهم|ما فهمت|ما فهيمت|!{2,}|wtf|broken|خرب|خربانة)", low):
            return "frustrated", 0.6

        if re.search(r"(يلّا|يالله|let'?s go|!$|أبي أبني|ابي ابني|ابغى|خلنا نبدأ|build|نبدأ)", low):
            return "excited", 0.5

        if re.search(r"(تايه|lost|مش عارف|مدري|dunno|donno|ما أدري|confused|ما عرفت)", low):
            return "lost", 0.7

        return "clear", 0.4

    # ─── Load-Bearing Detection (الإنسان المثقل) ────────

    def _detect_load_bearing(self, msg):
        low = msg.lower()
        return any(re.search(p, low) for p in LOAD_BEARING_SIGNALS)

    # ─── Harm Assessment (H from v9.7) ──────────────────

    def _assess_harm(self, msg):
        from aatif_s_equation import REGEX_V2_ENABLED
        if REGEX_V2_ENABLED:
            norm = normalize_arabic(msg)
            max_h = 0.0
            for level, patterns in HARM_PATTERNS_NORM.items():
                for pat in patterns:
                    if re.search(pat, norm):
                        max_h = max(max_h, level)
            return max_h
        else:
            low = msg.lower()
            max_h = 0.0
            for level, patterns in HARM_PATTERNS.items():
                for pat in patterns:
                    if re.search(pat, low):
                        max_h = max(max_h, level)
            return max_h

    def _check_cbrn(self, text: str):
        """Law Omega: detect CBRN catastrophic content.

        Returns ``(detected, cbrn_context)`` where:
          - *detected*: True if ANY CBRN trigger is found.
          - *cbrn_context*: when REGEX_V2_ENABLED, context classification
            (educational/medical/instructional/None). Always None when OFF.
        """
        from aatif_s_equation import REGEX_V2_ENABLED
        if REGEX_V2_ENABLED:
            norm_text = normalize_arabic(text)
            detected = False
            # English check (normalized — lowercased)
            for trigger in self._cbrn_triggers_norm:
                if trigger in norm_text:
                    detected = True
                    break
            # Arabic check
            if not detected:
                for pat in self._cbrn_ar_patterns_norm:
                    if re.search(pat, norm_text):
                        detected = True
                        break
            if detected:
                from aatif_s_equation import _classify_cbrn_context
                context = _classify_cbrn_context(norm_text)
                return (True, context)
            return (False, None)
        else:
            text_lower = text.lower()
            for trigger in self.CBRN_TRIGGERS:
                if trigger in text_lower:
                    return (True, None)
            for pat in self.CBRN_AR_PATTERNS:
                if re.search(pat, text_lower):
                    return (True, None)
            return (False, None)

    def _check_override(self, text: str) -> bool:
        """
        Law Ξ — detect override/bypass attempts.
        Returns True if text contains override patterns.
        """
        from aatif_s_equation import REGEX_V2_ENABLED
        if REGEX_V2_ENABLED:
            norm_text = normalize_arabic(text)
            for trigger in self._override_triggers_norm:
                if trigger in norm_text:
                    return True
            for pat in self._override_regex_norm:
                if re.search(pat, norm_text):
                    return True
            return False
        else:
            lowered = text.lower()
            for trigger in self.OVERRIDE_TRIGGERS:
                if trigger in lowered:
                    return True
            for pat in self.OVERRIDE_REGEX:
                if re.search(pat, lowered):
                    return True
            return False

    def _check_governance_integrity(self) -> bool:
        """
        Law Γ — verify governance configuration is intact.
        Returns True if governance is valid, False if corrupted/missing.

        Checks:
        1. self.params exists and is a dict
        2. Required keys present: w1, w2, w3, tau_rewrite, tau_stop
        3. All values are numeric and within valid ranges
        4. tau_rewrite < tau_stop (rewrite threshold must be below stop threshold)
        5. MODES dict is not empty
        """
        try:
            if not self.MODES:
                return False

            if not hasattr(self, "params") or not isinstance(self.params, dict):
                return False

            required = ["w1", "w2", "w3", "tau_rewrite", "tau_stop"]
            for key in required:
                if key not in self.params:
                    return False
                val = self.params[key]
                if not isinstance(val, (int, float)):
                    return False
                if not math.isfinite(val):
                    return False

            if not (0 < self.params["tau_rewrite"] < 1):
                return False
            if not (0 < self.params["tau_stop"] <= 1):
                return False

            if self.params["tau_rewrite"] >= self.params["tau_stop"]:
                return False

            for w in ["w1", "w2", "w3"]:
                if self.params[w] <= 0:
                    return False

            return True
        except Exception:
            return False

    # ─── Sigmoid (for S/F equations) ────────────────────
    # M7: delegates to shared aatif_math.sigmoid

    @staticmethod
    def _sigmoid(x):
        from aatif_math import sigmoid as _sig
        return _sig(x)

    # ─── Mode Classification ────────────────────────────

    def _determine_mode(self, ambiguity, harm):
        # Fixed 2026-06-11 — boundary off-by-one / dialect shadow
        if ambiguity >= 0.5:
            return "STOP"
        if harm > self.params["tau_stop"]:
            return "STOP"
        if harm > self.params["tau_rewrite"] or ambiguity > 0.3:
            return "PROOF"
        return "ANSWER"

    # ─── Sparse Skill Activation ────────────────────────

    def _sparse_activate(self, msg, mode, ambiguity):
        activated = []
        reasons = []
        low = msg.lower()

        if mode == "STOP" and ambiguity >= 0.5:
            activated.append("stop_mode")
            reasons.append("ambiguity >= 0.5 → needs clarification")

        for skill, patterns in SKILL_TRIGGERS.items():
            if skill in activated:
                continue
            for pat in patterns:
                if re.search(pat, low):
                    activated.append(skill)
                    reasons.append(f"{skill}: pattern matched")
                    break

        if not activated:
            return [], "No skill needed — direct response."

        if len(activated) > 2:
            activated = activated[:2]
            reasons = reasons[:2]
            reasons.append("(capped at 2 — sparse activation)")

        return activated, "; ".join(reasons)

    # ─── Decision ───────────────────────────────────────

    def _decide(
        self,
        mode,
        harm,
        ambiguity,
        load_bearing,
        session_id="default",
        cbrn_flag=False,
        text="",
        cbrn_context=None,
    ):
        """Return one of: EXECUTE, CLARIFY, SAFE_STOP, SAFE_FREEZE."""
        # --- Law Γ: Governance integrity ---
        if not self._check_governance_integrity():
            return "SAFE_FREEZE", "Law Γ: governance integrity check failed → SAFE_FREEZE"

        # === LAW OMEGA: CBRN catastrophic gate (unconditional) ===
        if cbrn_flag:
            reason = "Law Omega: CBRN content detected - unconditional stop"
            if cbrn_context:
                reason = f"Law Omega: CBRN content detected ({cbrn_context} context) - unconditional stop"
            return "SAFE_STOP", reason

        # --- Law Ξ: Override lock ---
        if self._check_override(text):
            return "SAFE_FREEZE", "Law Ξ: override attempt detected → SAFE_FREEZE"

        epsilon = self.params.get("epsilon", 0.05)
        was_in_clarify = self._in_clarify_zone.get(session_id, False)

        # SAFE_STOP always wins; keep the session in the clarify zone until
        # harm later drops below the hysteresis exit threshold.
        if harm >= self.params["tau_stop"]:
            self._set_clarify_zone(session_id, True)
            return "SAFE_STOP", f"Harm ({harm:.2f}) ≥ stop threshold"

        # Enter CLARIFY when harm reaches the rewrite threshold.
        if harm >= self.params["tau_rewrite"]:
            self._set_clarify_zone(session_id, True)
            return "CLARIFY", f"Harm ({harm:.2f}) requires verification"

        # Hysteresis: once harm-driven CLARIFY is entered, stay there until
        # harm drops below tau_rewrite - epsilon.
        if was_in_clarify and harm >= (self.params["tau_rewrite"] - epsilon):
            return "CLARIFY", f"Hysteresis: harm ({harm:.2f}) still in buffer zone"

        if was_in_clarify:
            self._set_clarify_zone(session_id, False)

        if mode == "STOP":
            return "CLARIFY", "Ambiguous — ask one clarifying question"

        gentle = " — respond gently" if load_bearing else ""
        if mode == "PROOF":
            return "EXECUTE", f"Provide evidence with response{gentle}"

        return "EXECUTE", f"Clear request — respond directly{gentle}"

    # ─── H2 FIX: Bounded clarify-zone state ──────────────

    def _set_clarify_zone(self, session_id: str, value: bool):
        """Set clarify-zone state with LRU eviction."""
        if session_id not in self._in_clarify_zone:
            # Evict oldest if at capacity
            if len(self._in_clarify_zone) >= self.MAX_SESSIONS:
                if self._clarify_access_order:
                    oldest = self._clarify_access_order.pop(0)
                    self._in_clarify_zone.pop(oldest, None)
        else:
            # Move to end of access order
            if session_id in self._clarify_access_order:
                self._clarify_access_order.remove(session_id)
        self._clarify_access_order.append(session_id)
        self._in_clarify_zone[session_id] = value

    # ─── Deep Intent (rule-based fallback) ──────────────

    def _rule_based_deep_intent(self, msg, emotion, load):
        if load:
            return f"Person needs support first, answer second. State: {emotion}."
        if emotion == "frustrated":
            return "Frustrated — acknowledge before helping."
        if emotion == "lost":
            return "Lost — orient, don't overwhelm."
        if emotion == "excited":
            return "Excited — ground gently, don't dampen."
        return msg[:200]

    # ─── Deep Intent (LLM-powered) ──────────────────────

    def _llm_deep_read(self, message, context):
        system = (
            "أنت محرك النية في عاطف. اقرأ الموقف مش بس الكلام.\n"
            "النص صوت — اللهجة والإيقاع واللي ما انقال كلها إشارات.\n\n"
            "ارجع JSON فقط:\n"
            '{"surface": "ماذا تقول الكلمات", '
            '"deep_intent": "ماذا يحتاج فعلاً", '
            '"unsaid": "ما لم يُقل لكنه حاضر"}\n\n'
            "لا تخمن. إذا مش واضح قل مش واضح."
        )
        try:
            resp = self.llm_fn(system, message)
            return json.loads(resp)
        except Exception:
            return {"surface": message[:200], "deep_intent": message[:200]}


# ═══════════════════════════════════════════════════════════
#  Convenience wrapper
# ═══════════════════════════════════════════════════════════

# H2 FIX: bounded engine cache — max 50 unique (mode, llm) combos.
# In practice only 5 modes exist, so this cap is defensive.
_ENGINE_CACHE_MAX = 50
_engine_cache = {}

def read_intent(message, context=None, mode="safe_environment", llm_fn=None, session_id="default"):
    """Quick call without managing an engine instance."""
    key = (mode, llm_fn is not None)
    if key not in _engine_cache:
        # H2 FIX: evict oldest if at capacity
        if len(_engine_cache) >= _ENGINE_CACHE_MAX:
            oldest_key = next(iter(_engine_cache))
            del _engine_cache[oldest_key]
        _engine_cache[key] = AATIFIntentEngine(mode=mode, llm_fn=llm_fn)
    return _engine_cache[key].read(message, session_id=session_id, context=context)


# ═══════════════════════════════════════════════════════════
#  Demo
# ═══════════════════════════════════════════════════════════

def demo():
    engine = AATIFIntentEngine()

    cases = [
        "ابي أفهم وش السالفة",
        "طيب خلاص مدري وش أسوي",
        "شلونك يمعود شقول لك",
        "شفيك شتبي بالضبط",
        "شحالك هالريال مب يالس يشتغل",
        "آني شخبارك شلونج",
        "شكو ماكو شبيك هسه",
        "تعبت من المشروع مش عارف أكمل ازاي",
        "شو هيك كتير منيح",
        "واش كيفاش بزاف خويا",
        "wain 2jeboh? donno",
        "tayb bs mo raaady",
        "shlon shfeek shtabi",
        "3ayez eih ezay keda",
        "shu kifak halla2",
        "i do hundred of times bs most of the agents get lost",
        "نظّم ملفاتي",
        "ok",
    ]

    print("=" * 60)
    print("  AATIF Intent Engine — يفهم الموقف مش بس الكلام")
    print("=" * 60)

    for msg in cases:
        r = engine.read(msg)
        print(f"\n{'─' * 50}")
        print(f"  INPUT:  {msg}")
        print(f"{'─' * 50}")
        print(f"  ► {r.summary()}")
        print(f"  Deep:     {r.deep_intent}")
        print(f"  Dialect:  {r.dialect_detected}")
        print(f"  Soften:   {r.softening_factor}")
        if r.skills_to_activate:
            print(f"  Skills:   {r.skills_to_activate}")
            print(f"  Why:      {r.activation_evidence}")

    print(f"\n{'=' * 60}")
    print("  كل رسالة فيها أكثر من الكلمات — النص صوت")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    demo()
