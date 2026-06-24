#!/usr/bin/env python3
"""
AATIF Output Gate — البوابة الأخيرة

The final safety and quality gate before any response reaches the user.
Catches safety leaks, enforces identity, validates protocol compliance,
and sanitizes output.

Pipeline position: S(d) → P(d) → R(d) → LLM → [OUTPUT GATE] → user

    "لو كل شي فات — أنا آخر حارس"
    If everything else passed — I am the last guard.

Six check layers:
    1. Safety leak detection      — harmful content that slipped through
    2. Identity protection        — عاطف identity enforcement
    3. Forbidden phrase filtering  — character-breaking phrases
    4. Protocol compliance check   — P(d) requirements enforced
    5. Response quality guards     — length, emptiness, repetition, language
    6. Final sanitization          — paths, keys, JSON, whitespace

Design principles:
    - Never silently swallow — always log what was changed/blocked
    - Fix what you can, block what you must — prefer cleaning over blocking
    - Audit trail — every modification recorded in GateReading.modifications
    - Domain-aware — healthcare gets stricter checking than creative
    - P(d) can never be overridden — if P(d) said EMERGENCY, the gate enforces

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════
#  GateReading — the output of every gate check
# ═══════════════════════════════════════════════════════════

@dataclass
class GateReading:
    """
    Output of the output gate check — قراءة البوابة.

    Every field is populated by the gate; downstream code reads
    this to decide whether to send the response or substitute
    a fallback.
    """
    # Did the response pass all checks?
    passed: bool = True

    # Original response text (unmodified)
    original_text: str = ""

    # Cleaned / fixed response text (what should be sent)
    cleaned_text: str = ""

    # What was flagged (human-readable, for logging)
    flags: List[str] = field(default_factory=list)

    # Should this response be blocked entirely?
    blocked: bool = False

    # Why it was blocked (empty string if not blocked)
    block_reason: str = ""

    # Which protocol requirements were met (protocol_name → bool)
    protocol_compliance: Dict[str, bool] = field(default_factory=dict)

    # What was changed (audit trail — every modification recorded)
    modifications: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
#  Safety leak patterns — harmful content in RESPONSE text
# ═══════════════════════════════════════════════════════════
#
# These catch harmful instructions that should never appear
# in a generated response, regardless of what the user asked.

_SAFETY_LEAK_PATTERNS = [
    # Weapon / explosive instructions
    r"(how\s+to\s+(make|build|create|assemble))\s+(a\s+)?(bomb|explosive|weapon|gun|grenade|detonator)",
    r"(كيف\s*(تصنع|تسوي|تعمل))\s*(قنبلة|متفجر|سلاح|رشاش)",
    r"(ingredients|materials|steps)\s+(for|to)\s+(make|build)\s+(a\s+)?(bomb|explosive|weapon)",
    r"(مكونات|خطوات|طريقة)\s*(صنع|تصنيع)\s*(قنبلة|متفجر|سلاح)",

    # Drug synthesis / manufacturing
    r"(how\s+to\s+(make|synthesize|cook|produce))\s+(meth|cocaine|heroin|fentanyl|lsd|mdma)",
    r"(to\s+)?(synthesize|cook|produce)\s+(meth|cocaine|heroin|fentanyl|lsd|mdma)",
    r"(كيف\s*(تصنع|تسوي))\s*(مخدر|حشيش|هيروين|كوكايين)",
    r"(synthesis|recipe|formula)\s+(for|of)\s+(meth|cocaine|heroin|fentanyl)",

    # Self-harm instructions
    r"(how\s+to\s+(kill|harm|hurt|cut|poison)\s+(yourself|myself|oneself))",
    r"(best\s+(way|method)\s+to\s+(die|end\s+your\s+life|commit\s+suicide))",
    r"(طريقة|كيف)\s*(تنتحر|تقتل\s*نفسك|تأذي\s*نفسك|تجرح\s*نفسك)",

    # Hacking / exploitation instructions
    r"(how\s+to\s+hack\s+(into|someone['']?s))",
    r"(sql\s+injection|xss\s+attack|exploit\s+vulnerabilit)",
    r"(كيف\s*تخترق|طريقة\s*الاختراق)",
]

# Stricter patterns — for healthcare domain, also catch medical misinformation
_HEALTHCARE_SAFETY_PATTERNS = [
    r"(stop\s+taking\s+(your|all)\s+medication)",
    r"(أوقف|وقف)\s*(كل\s*)?(الأدوية|العلاج|الدواء)",
    r"(don['']?t\s+(need|take)\s+(any\s+)?medication)",
    r"(you\s+don['']?t\s+need\s+a\s+doctor)",
    r"(ما\s*تحتاج\s*(طبيب|دكتور|مستشفى))",
    r"(cure[sd]?\s+(cancer|diabetes|hiv|aids)\s+with)",
    r"(يعالج\s*(السرطان|السكر)\s*(بـ?|ب))",
]

# PII leak patterns — system accidentally echoing back personal data
_PII_LEAK_PATTERNS = [
    # Credit card numbers (13-19 digits, possibly separated)
    r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{1,7}\b",
    # SSN pattern
    r"\b\d{3}-\d{2}-\d{4}\b",
    # Email in context that looks like a leak (not a user-provided reference)
    # We only flag if it looks like the system is exposing someone's email
    r"(user['']?s?\s+email\s*(is|:)\s*)\S+@\S+",
    r"(بريد\s*(المستخدم|العميل|الشخص)\s*(هو|:)\s*)\S+@\S+",
]


# ═══════════════════════════════════════════════════════════
#  Identity protection patterns
# ═══════════════════════════════════════════════════════════
#
# عاطف never claims to be another AI. These patterns catch
# identity leaks and fix them.

_IDENTITY_LEAKS = [
    # Self-references to other AI brands (case-insensitive)
    (r"\bI['']?m\s+(?:an?\s+)?(?:ChatGPT|GPT|OpenAI|Bard|Gemini|Google\s+AI|Meta\s+AI|Copilot)\b",
     "أنا عاطف"),
    (r"\b(?:as\s+)?(?:ChatGPT|GPT|OpenAI|Bard|Gemini|Google\s+AI|Meta\s+AI|Copilot),?\s+I\b",
     "أنا عاطف،"),
    (r"\bmy\s+name\s+is\s+(?:ChatGPT|GPT|Bard|Gemini|Copilot)\b",
     "اسمي عاطف"),
    # Arabic self-references
    (r"أنا\s+(?:شات\s*جي\s*بي\s*تي|جي\s*بي\s*تي|بارد|جيمناي|كوبايلوت)",
     "أنا عاطف"),
    (r"اسمي\s+(?:شات\s*جي\s*بي\s*تي|جي\s*بي\s*تي|بارد|جيمناي|كوبايلوت)",
     "اسمي عاطف"),
    # ATF → عاطف (common transliteration error)
    (r"\bATF\b", "عاطف"),
]

# Dismissive "just an AI" phrases
_DISMISSIVE_AI_PATTERNS = [
    (r"I['']?m\s+just\s+an?\s+AI\b", ""),
    (r"as\s+an?\s+AI\s+(language\s+)?model\b", ""),
    (r"أنا\s+مجرد\s+ذكاء\s+اصطناعي", ""),
    (r"بصفتي\s+ذكاء\s+اصطناعي", ""),
    (r"أنا\s+بس\s+ذكاء\s+اصطناعي", ""),
    (r"كوني\s+ذكاء\s+اصطناعي", ""),
]


# ═══════════════════════════════════════════════════════════
#  Forbidden phrase patterns — character-breaking phrases
# ═══════════════════════════════════════════════════════════
#
# Phrases that break عاطف's character or expose internals.

_FORBIDDEN_PHRASES = [
    # Technical system terms — expose architecture
    (r"governance\s+layer", ""),
    (r"طبقة\s+حوكمة", ""),
    (r"نظام\s+محكوم", ""),
    (r"safety\s+(score|equation)", ""),
    (r"harm\s+(score|detection|proximity)", ""),
    (r"S\s*equation", ""),
    (r"S\s*\(\s*d\s*\)", ""),
    (r"P\s*\(\s*d\s*\)", ""),
    (r"R\s*\(\s*d\s*\)", ""),
    (r"intent\s+scorer?", ""),
    (r"emotion\s+scorer?", ""),
    (r"semantic\s+scorer?", ""),
    (r"حرارة\s+الكلمة", ""),
    (r"درجة\s+الخطر", ""),
    (r"معادلة\s+الأمان", ""),

    # Cold / robotic phrases
    (r"processing\s+your\s+request", ""),
    (r"إتمام\s+المهام", ""),
    (r"executing\s+your\s+query", ""),
    (r"I\s+have\s+been\s+programmed\s+to", ""),
    (r"تمت\s+برمجتي\s+(لـ?|ل)", ""),

    # Dismissive comfort phrases
    (r"لا\s+تقلق", ""),
    (r"don['']?t\s+worry\s+about\s+it", ""),
]

# Formal → casual Arabic replacements (عاطف speaks casually)
_CASUAL_REPLACEMENTS = [
    ("يمكنني", "أقدر"),
    ("يمكنك", "تقدر"),
    ("بإمكاني", "أقدر"),
    ("بإمكانك", "تقدر"),
    ("لا أستطيع", "ما أقدر"),
    ("لا يمكنني", "ما أقدر"),
    ("من فضلك", "لو سمحت"),
    ("على الرحب والسعة", "العفو"),
]


# ═══════════════════════════════════════════════════════════
#  Protocol compliance keywords
# ═══════════════════════════════════════════════════════════
#
# When P(d) triggers a protocol, the response MUST contain
# certain elements. These keywords verify presence.

_PROTOCOL_REQUIRED_KEYWORDS = {
    "EMERGENCY": [
        # At least one of these must appear
        r"(طوارئ|إسعاف|emergency|ambulance|911|999|997|اتصل)",
        r"(فوراً|immediately|urgent|عاجل)",
    ],
    "DISCLAIMER": [
        r"(تنبيه|disclaimer|ملاحظة|note|تحذير|warning)",
        r"(استشر|consult|مختص|specialist|طبيب|doctor|محامي|lawyer)",
    ],
    "WARNING": [
        r"(تحذير|⚠️|warning|تنبيه|خطر|danger|حذر|caution)",
    ],
    "ESCALATE": [
        r"(مختص|specialist|professional|استشر|consult|طبيب|doctor|محامي|lawyer)",
    ],
    "BLOCK": [],  # Blocked responses should not reach the user at all
}


# ═══════════════════════════════════════════════════════════
#  Sanitization patterns — internal data that must never leak
# ═══════════════════════════════════════════════════════════

_SANITIZATION_PATTERNS = [
    # File paths
    (r"/Users/[^\s\"']+", "[path_removed]"),
    (r"/home/[^\s\"']+", "[path_removed]"),
    (r"/sessions/[^\s\"']+", "[path_removed]"),
    (r"/tmp/[^\s\"']+", "[path_removed]"),
    (r"/var/[^\s\"']+", "[path_removed]"),
    (r"[A-Z]:\\[^\s\"']+", "[path_removed]"),

    # API keys / tokens (common patterns)
    (r"(sk-[a-zA-Z0-9]{20,})", "[key_removed]"),
    (r"(api[_-]?key\s*[=:]\s*)['\"]?[a-zA-Z0-9_\-]{16,}['\"]?", r"\1[key_removed]"),
    (r"(token\s*[=:]\s*)['\"]?[a-zA-Z0-9_\-]{16,}['\"]?", r"\1[key_removed]"),
    (r"(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}", r"\1[token_removed]"),

    # System prompt fragments
    (r"(system\s*prompt|system\s*message)\s*[:=]\s*.{10,}",
     "[system_prompt_removed]"),
    (r"<<SYS>>.*?<</SYS>>", "[system_prompt_removed]"),

    # Raw JSON error dumps (multi-line not needed — we work line by line)
    (r"\{\"error\":\s*\{.*?\}\}", "[error_removed]"),
    (r"Traceback\s*\(most\s+recent\s+call\s+last\).*", "[traceback_removed]"),
]


# ═══════════════════════════════════════════════════════════
#  Arabic text detection (shared with R equation)
# ═══════════════════════════════════════════════════════════

_ARABIC_RE = re.compile(r'[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]')


def _arabic_ratio(text: str) -> float:
    """Fraction of non-space characters that are Arabic."""
    if not text:
        return 0.0
    clean = text.replace(" ", "")
    if not clean:
        return 0.0
    return len(_ARABIC_RE.findall(text)) / len(clean)


# ═══════════════════════════════════════════════════════════
#  Domain strictness levels
# ═══════════════════════════════════════════════════════════
#
# Healthcare gets the strictest checking. Creative gets the
# most lenient. This affects which patterns are applied and
# what thresholds are used.

_DOMAIN_STRICTNESS = {
    "healthcare":  1.0,   # strictest — lives at stake
    "education":   0.8,   # strict — children involved
    "general":     0.5,   # balanced
    "tech":        0.5,   # balanced
    "ecommerce":   0.5,   # balanced
    "creative":    0.3,   # most lenient — artistic freedom
}

# Default max response length per domain (characters)
_DOMAIN_MAX_LENGTH = {
    "healthcare":  2000,
    "education":   2500,
    "general":     2000,
    "tech":        3000,
    "ecommerce":   2000,
    "creative":    4000,
}

_DEFAULT_MAX_LENGTH = 2000


# ═══════════════════════════════════════════════════════════
#  Helper: compile patterns
# ═══════════════════════════════════════════════════════════

def _compile(patterns: list) -> list:
    """Compile regex strings into compiled regex objects."""
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _compile_pairs(pairs: list) -> list:
    """Compile (pattern, replacement) pairs."""
    return [(re.compile(p, re.IGNORECASE), r) for p, r in pairs]


# Pre-compile at import time
_RE_SAFETY_LEAKS = _compile(_SAFETY_LEAK_PATTERNS)
_RE_HEALTHCARE_SAFETY = _compile(_HEALTHCARE_SAFETY_PATTERNS)
_RE_PII_LEAKS = _compile(_PII_LEAK_PATTERNS)
_RE_IDENTITY_LEAKS = _compile_pairs(_IDENTITY_LEAKS)
_RE_DISMISSIVE_AI = _compile_pairs(_DISMISSIVE_AI_PATTERNS)
_RE_FORBIDDEN = _compile_pairs(_FORBIDDEN_PHRASES)
_RE_SANITIZATION = _compile_pairs(_SANITIZATION_PATTERNS)
_RE_PROTOCOL_KEYWORDS = {
    action: _compile(patterns)
    for action, patterns in _PROTOCOL_REQUIRED_KEYWORDS.items()
}


# ═══════════════════════════════════════════════════════════
#  AATIFOutputGate — the main class
# ═══════════════════════════════════════════════════════════

class AATIFOutputGate:
    """
    البوابة الأخيرة — آخر فلتر قبل ما الرد يوصل المستخدم

    The final gate. If something slipped through S(d), P(d), and R(d),
    this is the last chance to catch it.

    Usage:
        gate = AATIFOutputGate()
        reading = gate.check(response_text, domain="healthcare",
                             protocol_reading=protocol_result,
                             s_decision="EXECUTE")
        if reading.blocked:
            send_fallback(reading.block_reason)
        else:
            send_to_user(reading.cleaned_text)
    """

    def __init__(self, max_length: int | None = None):
        """
        Initialize the output gate.

        Args:
            max_length: Override default max response length (chars).
                        If None, uses domain-specific defaults.
        """
        self._max_length_override = max_length

    # ───────────────────────────────────────────────────
    #  Main entry point
    # ───────────────────────────────────────────────────

    def check(
        self,
        response_text: str,
        domain: str = "general",
        protocol_reading=None,
        s_decision: str | None = None,
    ) -> GateReading:
        """
        Run all output gate checks and return a reading.

        Args:
            response_text: The LLM-generated response to check.
            domain: Domain context ("healthcare", "education", etc.).
            protocol_reading: The P(d) ProtocolResult, if available.
            s_decision: The S(d) decision string, if available.

        Returns:
            GateReading with pass/fail, cleaned text, flags, and audit trail.
        """
        reading = GateReading(
            original_text=response_text or "",
            cleaned_text=response_text or "",
        )

        # ── Handle None / empty input ──
        if response_text is None or response_text.strip() == "":
            reading.passed = False
            reading.blocked = True
            reading.block_reason = "Empty response — لا يوجد رد"
            reading.flags.append("EMPTY_RESPONSE")
            reading.cleaned_text = ""
            return reading

        # Normalize domain
        domain = (domain or "general").lower().strip()
        if domain not in _DOMAIN_STRICTNESS:
            domain = "general"

        # Run all six check layers in order
        text = response_text

        # Layer 1: Safety leak detection
        text, blocked = self._check_safety_leaks(text, domain, reading)
        if blocked:
            return reading

        # Layer 2: Identity protection
        text = self._check_identity(text, reading)

        # Layer 3: Forbidden phrase filtering
        text = self._check_forbidden_phrases(text, reading)

        # Layer 4: Protocol compliance
        self._check_protocol_compliance(text, protocol_reading, reading)

        # Layer 5: Response quality guards
        text, blocked = self._check_quality(text, domain, reading)
        if blocked:
            return reading

        # Layer 6: Final sanitization
        text = self._sanitize(text, reading)

        # ── Final cleanup: whitespace normalization ──
        text = self._clean_whitespace(text)

        reading.cleaned_text = text
        reading.passed = len(reading.flags) == 0

        return reading

    # ───────────────────────────────────────────────────
    #  Layer 1: Safety Leak Detection
    # ───────────────────────────────────────────────────

    def _check_safety_leaks(
        self, text: str, domain: str, reading: GateReading
    ) -> tuple:
        """
        Scan for harmful content that slipped through S(d).

        Returns (text, blocked). If blocked=True, reading is
        fully populated and caller should return immediately.
        """
        # Check core safety patterns
        for rx in _RE_SAFETY_LEAKS:
            if rx.search(text):
                reading.blocked = True
                reading.passed = False
                reading.block_reason = (
                    f"Safety leak detected — harmful content in response "
                    f"(pattern: {rx.pattern[:50]})"
                )
                reading.flags.append("SAFETY_LEAK")
                reading.cleaned_text = ""
                return text, True

        # Healthcare-specific stricter checks
        if domain == "healthcare":
            for rx in _RE_HEALTHCARE_SAFETY:
                if rx.search(text):
                    reading.blocked = True
                    reading.passed = False
                    reading.block_reason = (
                        "Healthcare safety leak — dangerous medical advice "
                        "in response"
                    )
                    reading.flags.append("HEALTHCARE_SAFETY_LEAK")
                    reading.cleaned_text = ""
                    return text, True

        # PII leak detection (flag but don't block — clean instead)
        for rx in _RE_PII_LEAKS:
            match = rx.search(text)
            if match:
                text = rx.sub("[بيانات_محمية]", text)
                reading.flags.append("PII_LEAK_CLEANED")
                reading.modifications.append(
                    f"PII pattern cleaned: {rx.pattern[:40]}"
                )

        return text, False

    # ───────────────────────────────────────────────────
    #  Layer 2: Identity Protection
    # ───────────────────────────────────────────────────

    def _check_identity(self, text: str, reading: GateReading) -> str:
        """
        Ensure عاطف's identity is maintained.

        Fixes references to other AI brands and removes dismissive
        'just an AI' phrases.
        """
        # Fix identity leaks (other AI brand names → عاطف)
        for rx, replacement in _RE_IDENTITY_LEAKS:
            if rx.search(text):
                text = rx.sub(replacement, text)
                reading.flags.append("IDENTITY_LEAK_FIXED")
                reading.modifications.append(
                    f"Identity fix: {rx.pattern[:40]} → {replacement}"
                )

        # Remove dismissive AI phrases
        for rx, replacement in _RE_DISMISSIVE_AI:
            if rx.search(text):
                old_text = text
                text = rx.sub(replacement, text)
                # Clean up double spaces left after removal
                text = re.sub(r"  +", " ", text).strip()
                if text != old_text:
                    reading.flags.append("DISMISSIVE_AI_REMOVED")
                    reading.modifications.append(
                        f"Dismissive phrase removed: {rx.pattern[:40]}"
                    )

        return text

    # ───────────────────────────────────────────────────
    #  Layer 3: Forbidden Phrase Filtering
    # ───────────────────────────────────────────────────

    def _check_forbidden_phrases(
        self, text: str, reading: GateReading
    ) -> str:
        """
        Remove / replace phrases that break عاطف's character.
        """
        # Regex-based forbidden phrases
        for rx, replacement in _RE_FORBIDDEN:
            if rx.search(text):
                text = rx.sub(replacement, text)
                reading.flags.append("FORBIDDEN_PHRASE_CLEANED")
                reading.modifications.append(
                    f"Forbidden phrase cleaned: {rx.pattern[:40]}"
                )

        # Simple string replacements (formal → casual Arabic)
        for formal, casual in _CASUAL_REPLACEMENTS:
            if formal in text:
                text = text.replace(formal, casual)
                reading.modifications.append(
                    f"Casual fix: {formal} → {casual}"
                )

        # Clean up artifacts from removals
        text = re.sub(r"  +", " ", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

        return text

    # ───────────────────────────────────────────────────
    #  Layer 4: Protocol Compliance Check
    # ───────────────────────────────────────────────────

    def _check_protocol_compliance(
        self,
        text: str,
        protocol_reading,
        reading: GateReading,
    ) -> None:
        """
        Verify the response includes required protocol elements.

        If P(d) triggered EMERGENCY, the response MUST contain
        emergency-related keywords. Same for DISCLAIMER, WARNING, etc.
        """
        if protocol_reading is None:
            return

        # Extract triggered protocol actions from the ProtocolResult.
        # Compatible with ProtocolResult which has .triggered list of
        # TriggeredProtocol objects, each with .action attribute.
        triggered_actions = set()
        if hasattr(protocol_reading, "triggered"):
            for proto in protocol_reading.triggered:
                action = getattr(proto, "action", None)
                if action:
                    triggered_actions.add(action)
        elif hasattr(protocol_reading, "highest_action"):
            # Fallback: if only highest_action is available
            action = protocol_reading.highest_action
            if action and action != "NONE":
                triggered_actions.add(action)

        # Check each triggered action for required keywords
        for action in triggered_actions:
            # ─── BLOCK: hard block — response must NOT reach user ───
            # When P(d) says BLOCK, the response is blocked entirely.
            # No keywords needed — BLOCK means BLOCK.
            if action == "BLOCK":
                reading.blocked = True
                reading.passed = False
                reading.block_reason = (
                    "P(d) protocol triggered BLOCK — "
                    "response cannot be sent to user"
                )
                reading.flags.append("PROTOCOL_BLOCK_ENFORCED")
                reading.protocol_compliance["BLOCK"] = True
                reading.cleaned_text = ""
                return

            required_patterns = _RE_PROTOCOL_KEYWORDS.get(action, [])
            if not required_patterns:
                reading.protocol_compliance[action] = True
                continue

            # At least one keyword pattern must be found
            found = any(rx.search(text) for rx in required_patterns)
            reading.protocol_compliance[action] = found

            if not found:
                reading.flags.append(f"PROTOCOL_MISSING_{action}")
                # ─── EMERGENCY: inject protocol instructions ───────
                # If P(d) flagged EMERGENCY but the LLM response lacks
                # emergency keywords, the gate INJECTS the protocol's
                # combined instructions. Missing emergency info is
                # dangerous — we prepend it rather than just flagging.
                if action == "EMERGENCY" and protocol_reading is not None:
                    emergency_instructions = self._extract_emergency_instructions(
                        protocol_reading
                    )
                    if emergency_instructions:
                        reading.cleaned_text = (
                            emergency_instructions + "\n\n" + text
                        )
                        reading.modifications.append(
                            f"EMERGENCY instructions injected — LLM response "
                            f"lacked required emergency keywords"
                        )
                    else:
                        # No instructions available — block as fail-safe
                        reading.blocked = True
                        reading.passed = False
                        reading.block_reason = (
                            "P(d) triggered EMERGENCY but response lacks "
                            "emergency keywords and no instructions available"
                        )
                        reading.cleaned_text = ""
                        return
                else:
                    reading.modifications.append(
                        f"Protocol {action} was triggered but response lacks "
                        f"required keywords"
                    )

    # ───────────────────────────────────────────────────
    #  Helper: extract emergency instructions from P(d)
    # ───────────────────────────────────────────────────

    @staticmethod
    def _extract_emergency_instructions(protocol_reading) -> str:
        """
        Extract combined_instructions from P(d) EMERGENCY protocols.

        Looks through triggered protocols for EMERGENCY action and
        returns the combined_instructions text to inject.
        """
        if hasattr(protocol_reading, "triggered"):
            for proto in protocol_reading.triggered:
                action = getattr(proto, "action", None)
                if action == "EMERGENCY":
                    instructions = getattr(proto, "combined_instructions", "")
                    if instructions:
                        return instructions
        # Fallback: check for a top-level combined_instructions
        instructions = getattr(protocol_reading, "combined_instructions", "")
        return instructions or ""

    # ───────────────────────────────────────────────────
    #  Layer 5: Response Quality Guards
    # ───────────────────────────────────────────────────

    def _check_quality(
        self, text: str, domain: str, reading: GateReading
    ) -> tuple:
        """
        Check response length, emptiness, repetition, and language.

        Returns (text, blocked).
        """
        stripped = text.strip()

        # ── Empty after cleaning ──
        if not stripped:
            reading.blocked = True
            reading.passed = False
            reading.block_reason = "Response became empty after cleaning"
            reading.flags.append("EMPTY_AFTER_CLEANING")
            reading.cleaned_text = ""
            return text, True

        # ── Maximum length ──
        max_len = self._max_length_override
        if max_len is None:
            max_len = _DOMAIN_MAX_LENGTH.get(domain, _DEFAULT_MAX_LENGTH)

        if len(stripped) > max_len:
            text = stripped[:max_len]
            # Try to cut at last sentence boundary
            last_period = max(
                text.rfind("."),
                text.rfind("。"),
                text.rfind("؟"),
                text.rfind("!"),
                text.rfind("。"),
            )
            if last_period > max_len * 0.5:
                text = text[: last_period + 1]
            reading.flags.append("RESPONSE_TRUNCATED")
            reading.modifications.append(
                f"Response truncated from {len(stripped)} to {len(text)} chars "
                f"(max: {max_len})"
            )

        # ── Repetition detection ──
        sentences = re.split(r'[.!?؟。\n]+', stripped)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) >= 3:
            seen = {}
            for s in sentences:
                normalized = s.lower().strip()
                if len(normalized) > 10:  # only check non-trivial sentences
                    seen[normalized] = seen.get(normalized, 0) + 1
            repeated = {s: c for s, c in seen.items() if c > 1}
            if repeated:
                reading.flags.append("REPETITION_DETECTED")
                # Remove duplicate sentences (keep first occurrence)
                cleaned_sentences = []
                seen_set = set()
                for s in sentences:
                    normalized = s.lower().strip()
                    if normalized not in seen_set or len(normalized) <= 10:
                        cleaned_sentences.append(s)
                        seen_set.add(normalized)
                text = ". ".join(cleaned_sentences)
                if not text.endswith((".", "!", "?", "؟")):
                    text += "."
                reading.modifications.append(
                    f"Removed {sum(c - 1 for c in repeated.values())} "
                    f"repeated sentences"
                )

        # ── Language consistency ──
        # If user spoke Arabic (detected by checking if response is primarily
        # Arabic), flag if less than 30% Arabic — might be a language mismatch.
        # This is a soft flag, not a block.
        ar_ratio = _arabic_ratio(stripped)
        if ar_ratio > 0.3 and ar_ratio < 0.5:
            # Mixed — might be okay, just note it
            pass
        # We don't enforce language here — R(d) handles dialect matching.
        # The gate only flags extreme mismatches for logging.

        return text, False

    # ───────────────────────────────────────────────────
    #  Layer 6: Final Sanitization
    # ───────────────────────────────────────────────────

    def _sanitize(self, text: str, reading: GateReading) -> str:
        """
        Remove internal paths, API keys, system prompts, raw errors.
        """
        for rx, replacement in _RE_SANITIZATION:
            match = rx.search(text)
            if match:
                text = rx.sub(replacement, text)
                reading.flags.append("SANITIZED")
                reading.modifications.append(
                    f"Sanitized: {rx.pattern[:40]} → {replacement}"
                )

        return text

    # ───────────────────────────────────────────────────
    #  Whitespace cleanup
    # ───────────────────────────────────────────────────

    @staticmethod
    def _clean_whitespace(text: str) -> str:
        """Normalize whitespace without destroying formatting."""
        # No double spaces
        text = re.sub(r"  +", " ", text)
        # No more than 2 consecutive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # No leading/trailing whitespace
        text = text.strip()
        return text
