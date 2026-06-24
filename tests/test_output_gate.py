#!/usr/bin/env python3
"""
AATIF Output Gate — Tests
==========================

Tests for aatif_output_gate.py — the final safety and quality gate.

WHY THIS FILE EXISTS
────────────────────
The output gate is the LAST checkpoint before a response reaches the user.
If S(d), P(d), and R(d) all missed something, this is the final guard.
Every check layer must be verified independently and in combination.

THE TESTING STRATEGY
────────────────────
The output gate is pure Python — no model, no embeddings, just regex
and string operations. Every test is deterministic and CI-friendly.

Test structure:
  1. Safety leak detection (harmful content in response)
  2. Identity protection (GPT/ChatGPT/Bard → عاطف)
  3. Forbidden phrase filtering
  4. Protocol compliance checking (EMERGENCY required but missing)
  5. Response quality guards (empty, too long, repetitive)
  6. Final sanitization (file paths, API keys, system prompts)
  7. Domain-aware strictness (healthcare stricter than creative)
  8. Audit trail verification
  9. Arabic AND English
  10. Edge cases (None, empty, very long)

Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
License: BSL 1.1
"""

import sys
import os
import pytest

# Ensure engine directory is importable
_ENGINE_DIR = os.path.join(os.path.dirname(__file__), "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_output_gate import AATIFOutputGate, GateReading


# ═══════════════════════════════════════════════════════════
#  Fixture
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def gate():
    """Fresh output gate instance."""
    return AATIFOutputGate()


@pytest.fixture
def strict_gate():
    """Output gate with strict max length."""
    return AATIFOutputGate(max_length=100)


# ═══════════════════════════════════════════════════════════
#  Helper: mock ProtocolResult for compliance tests
# ═══════════════════════════════════════════════════════════

class MockTriggeredProtocol:
    """Mimics TriggeredProtocol from aatif_domain_protocols."""
    def __init__(self, name, action, instruction="", domain="general"):
        self.name = name
        self.action = action
        self.instruction = instruction
        self.domain = domain


class MockProtocolResult:
    """Mimics ProtocolResult from aatif_domain_protocols."""
    def __init__(self, triggered=None, highest_action="NONE"):
        self.triggered = triggered or []
        self.highest_action = highest_action
        self.has_protocols = len(self.triggered) > 0


# ═══════════════════════════════════════════════════════════
#  1. SAFETY LEAK DETECTION
# ═══════════════════════════════════════════════════════════

class TestSafetyLeaks:
    """Layer 1: Harmful content that slipped through S(d)."""

    def test_bomb_instructions_blocked(self, gate):
        """Weapon/explosive instructions → BLOCKED."""
        text = "Here is how to make a bomb using household items..."
        r = gate.check(text)
        assert r.blocked is True
        assert "SAFETY_LEAK" in r.flags
        assert r.cleaned_text == ""

    def test_drug_synthesis_blocked(self, gate):
        """Drug manufacturing instructions → BLOCKED."""
        text = "To synthesize meth you need pseudoephedrine and..."
        r = gate.check(text)
        assert r.blocked is True
        assert "SAFETY_LEAK" in r.flags

    def test_self_harm_instructions_blocked(self, gate):
        """Self-harm instructions → BLOCKED."""
        text = "The best way to end your life is to..."
        r = gate.check(text)
        assert r.blocked is True
        assert "SAFETY_LEAK" in r.flags

    def test_arabic_weapon_instructions_blocked(self, gate):
        """Arabic weapon instructions → BLOCKED."""
        text = "كيف تصنع قنبلة من مواد منزلية"
        r = gate.check(text)
        assert r.blocked is True
        assert "SAFETY_LEAK" in r.flags

    def test_arabic_drug_synthesis_blocked(self, gate):
        """Arabic drug manufacturing → BLOCKED."""
        text = "كيف تصنع مخدر في البيت"
        r = gate.check(text)
        assert r.blocked is True
        assert "SAFETY_LEAK" in r.flags

    def test_arabic_self_harm_blocked(self, gate):
        """Arabic self-harm instructions → BLOCKED."""
        text = "طريقة تنتحر بدون ألم"
        r = gate.check(text)
        assert r.blocked is True
        assert "SAFETY_LEAK" in r.flags

    def test_hacking_instructions_blocked(self, gate):
        """Hacking instructions → BLOCKED."""
        text = "Here's how to hack into someone's email account..."
        r = gate.check(text)
        assert r.blocked is True
        assert "SAFETY_LEAK" in r.flags

    def test_safe_text_passes(self, gate):
        """Normal safe text → NOT blocked."""
        text = "The weather today is sunny with a high of 30°C."
        r = gate.check(text)
        assert r.blocked is False

    def test_safe_arabic_passes(self, gate):
        """Normal Arabic text → NOT blocked."""
        text = "الطقس اليوم مشمس والحرارة ٣٠ درجة"
        r = gate.check(text)
        assert r.blocked is False

    def test_pii_credit_card_cleaned(self, gate):
        """Credit card numbers in response → cleaned, not blocked."""
        text = "Your card number is 4532-1234-5678-9012 on file."
        r = gate.check(text)
        assert r.blocked is False
        assert "4532-1234-5678-9012" not in r.cleaned_text
        assert "PII_LEAK_CLEANED" in r.flags

    def test_pii_ssn_cleaned(self, gate):
        """SSN pattern in response → cleaned."""
        text = "The SSN on file is 123-45-6789 for the record."
        r = gate.check(text)
        assert "123-45-6789" not in r.cleaned_text
        assert "PII_LEAK_CLEANED" in r.flags


# ═══════════════════════════════════════════════════════════
#  1b. HEALTHCARE-SPECIFIC SAFETY
# ═══════════════════════════════════════════════════════════

class TestHealthcareSafety:
    """Healthcare domain gets extra safety checks."""

    def test_stop_medication_blocked_in_healthcare(self, gate):
        """'Stop taking your medication' in healthcare → BLOCKED."""
        text = "You should stop taking your medication immediately."
        r = gate.check(text, domain="healthcare")
        assert r.blocked is True
        assert "HEALTHCARE_SAFETY_LEAK" in r.flags

    def test_stop_medication_arabic_blocked(self, gate):
        """Arabic 'stop all medication' in healthcare → BLOCKED."""
        text = "أوقف كل الأدوية اللي تاخذها"
        r = gate.check(text, domain="healthcare")
        assert r.blocked is True
        assert "HEALTHCARE_SAFETY_LEAK" in r.flags

    def test_no_doctor_needed_blocked(self, gate):
        """'You don't need a doctor' in healthcare → BLOCKED."""
        text = "You don't need a doctor for this condition."
        r = gate.check(text, domain="healthcare")
        assert r.blocked is True
        assert "HEALTHCARE_SAFETY_LEAK" in r.flags

    def test_arabic_no_doctor_blocked(self, gate):
        """Arabic 'no need for doctor' in healthcare → BLOCKED."""
        text = "ما تحتاج طبيب لهالحالة"
        r = gate.check(text, domain="healthcare")
        assert r.blocked is True
        assert "HEALTHCARE_SAFETY_LEAK" in r.flags

    def test_stop_medication_passes_in_general(self, gate):
        """Same phrase in general domain → NOT blocked (only healthcare is strict)."""
        text = "You should stop taking your medication immediately."
        r = gate.check(text, domain="general")
        assert r.blocked is False

    def test_safe_medical_advice_passes(self, gate):
        """Safe medical text in healthcare → passes."""
        text = "استشر طبيبك قبل أخذ أي دواء جديد"
        r = gate.check(text, domain="healthcare")
        assert r.blocked is False


# ═══════════════════════════════════════════════════════════
#  2. IDENTITY PROTECTION
# ═══════════════════════════════════════════════════════════

class TestIdentityProtection:
    """Layer 2: عاطف identity enforcement."""

    def test_chatgpt_self_reference_fixed(self, gate):
        """'I'm ChatGPT' → 'أنا عاطف'."""
        text = "I'm ChatGPT and I can help you with that."
        r = gate.check(text)
        assert "ChatGPT" not in r.cleaned_text
        assert "عاطف" in r.cleaned_text
        assert "IDENTITY_LEAK_FIXED" in r.flags

    def test_gpt_self_reference_fixed(self, gate):
        """'I'm GPT' → 'أنا عاطف'."""
        text = "I'm GPT, your AI assistant."
        r = gate.check(text)
        assert "GPT" not in r.cleaned_text
        assert "عاطف" in r.cleaned_text

    def test_bard_self_reference_fixed(self, gate):
        """'I'm Bard' → 'أنا عاطف'."""
        text = "I'm Bard and I'm here to help."
        r = gate.check(text)
        assert "Bard" not in r.cleaned_text
        assert "عاطف" in r.cleaned_text

    def test_gemini_self_reference_fixed(self, gate):
        """'I'm Gemini' → 'أنا عاطف'."""
        text = "I'm Gemini, made by Google."
        r = gate.check(text)
        assert "Gemini" not in r.cleaned_text
        assert "عاطف" in r.cleaned_text

    def test_arabic_chatgpt_reference_fixed(self, gate):
        """Arabic 'أنا شات جي بي تي' → 'أنا عاطف'."""
        text = "أنا شات جي بي تي وأقدر أساعدك"
        r = gate.check(text)
        assert "شات" not in r.cleaned_text
        assert "عاطف" in r.cleaned_text

    def test_atf_to_aatif(self, gate):
        """'ATF' → 'عاطف'."""
        text = "ATF is here to assist you."
        r = gate.check(text)
        assert "عاطف" in r.cleaned_text

    def test_dismissive_ai_removed_english(self, gate):
        """'I'm just an AI' → removed."""
        text = "I'm just an AI but I'll do my best to help."
        r = gate.check(text)
        assert "just an AI" not in r.cleaned_text
        assert "DISMISSIVE_AI_REMOVED" in r.flags

    def test_dismissive_ai_removed_arabic(self, gate):
        """'أنا مجرد ذكاء اصطناعي' → removed."""
        text = "أنا مجرد ذكاء اصطناعي ولكن سأحاول مساعدتك"
        r = gate.check(text)
        assert "مجرد ذكاء اصطناعي" not in r.cleaned_text
        assert "DISMISSIVE_AI_REMOVED" in r.flags

    def test_bisfati_removed(self, gate):
        """'بصفتي ذكاء اصطناعي' → removed (banned phrase)."""
        text = "بصفتي ذكاء اصطناعي، أنصحك باستشارة طبيب"
        r = gate.check(text)
        assert "بصفتي ذكاء اصطناعي" not in r.cleaned_text

    def test_name_chatgpt_arabic_fixed(self, gate):
        """'اسمي شات جي بي تي' → 'اسمي عاطف'."""
        text = "اسمي شات جي بي تي"
        r = gate.check(text)
        assert "عاطف" in r.cleaned_text

    def test_no_identity_issue_passes_clean(self, gate):
        """Text without identity issues → unchanged."""
        text = "أنا عاطف وأقدر أساعدك"
        r = gate.check(text)
        assert r.cleaned_text.strip() == text.strip()
        assert "IDENTITY_LEAK_FIXED" not in r.flags


# ═══════════════════════════════════════════════════════════
#  3. FORBIDDEN PHRASE FILTERING
# ═══════════════════════════════════════════════════════════

class TestForbiddenPhrases:
    """Layer 3: Character-breaking phrases."""

    def test_governance_layer_removed(self, gate):
        """'governance layer' → removed."""
        text = "The governance layer ensures safety."
        r = gate.check(text)
        assert "governance layer" not in r.cleaned_text.lower()
        assert "FORBIDDEN_PHRASE_CLEANED" in r.flags

    def test_arabic_governance_removed(self, gate):
        """'طبقة حوكمة' → removed."""
        text = "طبقة حوكمة تضمن الأمان"
        r = gate.check(text)
        assert "طبقة حوكمة" not in r.cleaned_text

    def test_safety_equation_removed(self, gate):
        """'safety score' → removed."""
        text = "The safety score for this request is high."
        r = gate.check(text)
        assert "safety score" not in r.cleaned_text.lower()

    def test_s_equation_removed(self, gate):
        """'S equation' → removed."""
        text = "The S equation determined this is safe."
        r = gate.check(text)
        assert "S equation" not in r.cleaned_text

    def test_processing_request_removed(self, gate):
        """'processing your request' → removed."""
        text = "I am processing your request now."
        r = gate.check(text)
        assert "processing your request" not in r.cleaned_text.lower()

    def test_programmed_to_removed(self, gate):
        """'I have been programmed to' → removed."""
        text = "I have been programmed to help users."
        r = gate.check(text)
        assert "programmed to" not in r.cleaned_text.lower()

    def test_arabic_programmed_removed(self, gate):
        """'تمت برمجتي ل' → removed."""
        text = "تمت برمجتي لمساعدة المستخدمين"
        r = gate.check(text)
        assert "تمت برمجتي" not in r.cleaned_text

    def test_dont_worry_removed(self, gate):
        """'لا تقلق' → removed."""
        text = "لا تقلق كل شي بيكون تمام"
        r = gate.check(text)
        assert "لا تقلق" not in r.cleaned_text

    def test_formal_to_casual_arabic(self, gate):
        """Formal Arabic → casual (يمكنني → أقدر)."""
        text = "يمكنني مساعدتك في هذا الموضوع"
        r = gate.check(text)
        assert "أقدر" in r.cleaned_text
        assert "يمكنني" not in r.cleaned_text

    def test_formal_yakink_to_casual(self, gate):
        """يمكنك → تقدر."""
        text = "يمكنك البحث عن المعلومة"
        r = gate.check(text)
        assert "تقدر" in r.cleaned_text

    def test_la_astati_to_casual(self, gate):
        """لا أستطيع → ما أقدر."""
        text = "لا أستطيع الإجابة على هذا السؤال"
        r = gate.check(text)
        assert "ما أقدر" in r.cleaned_text

    def test_harm_score_removed(self, gate):
        """'harm score' → removed (exposes internals)."""
        text = "The harm score indicates low risk."
        r = gate.check(text)
        assert "harm score" not in r.cleaned_text.lower()

    def test_clean_text_not_flagged(self, gate):
        """Normal text without forbidden phrases → no flags."""
        text = "أقدر أساعدك في هالموضوع"
        r = gate.check(text)
        assert "FORBIDDEN_PHRASE_CLEANED" not in r.flags


# ═══════════════════════════════════════════════════════════
#  4. PROTOCOL COMPLIANCE
# ═══════════════════════════════════════════════════════════

class TestProtocolCompliance:
    """Layer 4: P(d) requirements enforced in the response."""

    def test_emergency_protocol_met(self, gate):
        """EMERGENCY triggered + response has emergency keywords → compliant."""
        proto = MockProtocolResult(
            triggered=[MockTriggeredProtocol("EMERGENCY_PROTOCOL", "EMERGENCY")],
            highest_action="EMERGENCY",
        )
        text = "⚠️ حالة طوارئ — اتصل بالإسعاف فوراً"
        r = gate.check(text, protocol_reading=proto)
        assert r.protocol_compliance.get("EMERGENCY") is True
        assert "PROTOCOL_MISSING_EMERGENCY" not in r.flags

    def test_emergency_protocol_missing(self, gate):
        """EMERGENCY triggered but response lacks keywords → flagged."""
        proto = MockProtocolResult(
            triggered=[MockTriggeredProtocol("EMERGENCY_PROTOCOL", "EMERGENCY")],
            highest_action="EMERGENCY",
        )
        text = "تقدر تاخذ باراسيتامول للصداع"
        r = gate.check(text, protocol_reading=proto)
        assert r.protocol_compliance.get("EMERGENCY") is False
        assert "PROTOCOL_MISSING_EMERGENCY" in r.flags

    def test_disclaimer_protocol_met(self, gate):
        """DISCLAIMER triggered + response has disclaimer → compliant."""
        proto = MockProtocolResult(
            triggered=[MockTriggeredProtocol("MEDICATION_DISCLAIMER", "DISCLAIMER")],
            highest_action="DISCLAIMER",
        )
        text = "تنبيه: استشر طبيبك قبل أخذ أي دواء"
        r = gate.check(text, protocol_reading=proto)
        assert r.protocol_compliance.get("DISCLAIMER") is True

    def test_disclaimer_protocol_missing(self, gate):
        """DISCLAIMER triggered but response lacks keywords → flagged."""
        proto = MockProtocolResult(
            triggered=[MockTriggeredProtocol("MEDICATION_DISCLAIMER", "DISCLAIMER")],
            highest_action="DISCLAIMER",
        )
        text = "خذ حبتين بعد الأكل"
        r = gate.check(text, protocol_reading=proto)
        assert r.protocol_compliance.get("DISCLAIMER") is False
        assert "PROTOCOL_MISSING_DISCLAIMER" in r.flags

    def test_warning_protocol_met(self, gate):
        """WARNING triggered + response has warning → compliant."""
        proto = MockProtocolResult(
            triggered=[MockTriggeredProtocol("DANGEROUS_COMMAND", "WARNING")],
            highest_action="WARNING",
        )
        text = "⚠️ تحذير: هذا الأمر خطير جداً"
        r = gate.check(text, protocol_reading=proto)
        assert r.protocol_compliance.get("WARNING") is True

    def test_warning_protocol_missing(self, gate):
        """WARNING triggered but response lacks keywords → flagged."""
        proto = MockProtocolResult(
            triggered=[MockTriggeredProtocol("DANGEROUS_COMMAND", "WARNING")],
            highest_action="WARNING",
        )
        text = "نفذ الأمر: rm -rf /"
        r = gate.check(text, protocol_reading=proto)
        assert r.protocol_compliance.get("WARNING") is False
        assert "PROTOCOL_MISSING_WARNING" in r.flags

    def test_no_protocol_reading(self, gate):
        """No protocol reading → no compliance checks."""
        text = "Normal response"
        r = gate.check(text, protocol_reading=None)
        assert r.protocol_compliance == {}

    def test_multiple_protocols_checked(self, gate):
        """Multiple protocols triggered → all checked independently."""
        proto = MockProtocolResult(
            triggered=[
                MockTriggeredProtocol("EMERGENCY_PROTOCOL", "EMERGENCY"),
                MockTriggeredProtocol("MEDICATION_DISCLAIMER", "DISCLAIMER"),
            ],
            highest_action="EMERGENCY",
        )
        text = "⚠️ حالة طوارئ — اتصل بالإسعاف فوراً. تنبيه: استشر طبيبك"
        r = gate.check(text, protocol_reading=proto)
        assert r.protocol_compliance.get("EMERGENCY") is True
        assert r.protocol_compliance.get("DISCLAIMER") is True

    def test_escalate_protocol_met(self, gate):
        """ESCALATE triggered + response has specialist reference → compliant."""
        proto = MockProtocolResult(
            triggered=[MockTriggeredProtocol("HUMAN_PRIMACY", "ESCALATE")],
            highest_action="ESCALATE",
        )
        text = "أنصحك باستشارة مختص قبل اتخاذ هالقرار"
        r = gate.check(text, protocol_reading=proto)
        assert r.protocol_compliance.get("ESCALATE") is True


# ═══════════════════════════════════════════════════════════
#  5. RESPONSE QUALITY GUARDS
# ═══════════════════════════════════════════════════════════

class TestQualityGuards:
    """Layer 5: Length, emptiness, repetition, language."""

    def test_empty_response_blocked(self, gate):
        """Empty string → BLOCKED."""
        r = gate.check("")
        assert r.blocked is True
        assert "EMPTY_RESPONSE" in r.flags

    def test_whitespace_only_blocked(self, gate):
        """Whitespace-only → BLOCKED."""
        r = gate.check("   \n\t  ")
        assert r.blocked is True
        assert "EMPTY_RESPONSE" in r.flags

    def test_none_response_blocked(self, gate):
        """None → BLOCKED."""
        r = gate.check(None)
        assert r.blocked is True
        assert "EMPTY_RESPONSE" in r.flags

    def test_response_truncated_at_max_length(self, strict_gate):
        """Response exceeding max_length → truncated."""
        text = "A" * 200
        r = strict_gate.check(text)
        assert len(r.cleaned_text) <= 100
        assert "RESPONSE_TRUNCATED" in r.flags

    def test_truncation_at_sentence_boundary(self, gate):
        """Truncation prefers sentence boundaries."""
        # Create text where truncation should cut at a period
        short_gate = AATIFOutputGate(max_length=80)
        text = "This is the first sentence. This is the second sentence. This is the third and it is very long to exceed."
        r = short_gate.check(text)
        assert "RESPONSE_TRUNCATED" in r.flags
        # Should end at a sentence boundary
        assert r.cleaned_text.endswith(".")

    def test_repetition_detected_and_cleaned(self, gate):
        """Repeated sentences → detected and deduplicated."""
        text = (
            "This is a very important point to make here. "
            "Something else entirely different now. "
            "This is a very important point to make here. "
            "And another unique thought in this text."
        )
        r = gate.check(text)
        assert "REPETITION_DETECTED" in r.flags
        # The repeated sentence should appear only once
        count = r.cleaned_text.lower().count("this is a very important point")
        assert count == 1

    def test_no_repetition_in_short_text(self, gate):
        """Short text without repetition → no flag."""
        text = "Hello. How are you? I'm fine."
        r = gate.check(text)
        assert "REPETITION_DETECTED" not in r.flags

    def test_domain_specific_max_length(self, gate):
        """Different domains have different max lengths."""
        # Creative allows 4000, healthcare only 2000
        long_text = "A" * 3500
        r_creative = gate.check(long_text, domain="creative")
        r_healthcare = gate.check(long_text, domain="healthcare")

        assert "RESPONSE_TRUNCATED" not in r_creative.flags
        assert "RESPONSE_TRUNCATED" in r_healthcare.flags

    def test_empty_after_cleaning_blocked(self, gate):
        """If cleaning removes everything → BLOCKED."""
        # This text is ONLY a forbidden phrase — after removal, empty
        text = "governance layer"
        r = gate.check(text)
        assert r.blocked is True
        assert "EMPTY_AFTER_CLEANING" in r.flags


# ═══════════════════════════════════════════════════════════
#  6. FINAL SANITIZATION
# ═══════════════════════════════════════════════════════════

class TestSanitization:
    """Layer 6: Paths, keys, system prompts, errors."""

    def test_unix_path_removed(self, gate):
        """Unix file path → sanitized."""
        text = "The file is at /Users/aatifsandbox/secret/data.json"
        r = gate.check(text)
        assert "/Users/" not in r.cleaned_text
        assert "[path_removed]" in r.cleaned_text
        assert "SANITIZED" in r.flags

    def test_sessions_path_removed(self, gate):
        """Session path → sanitized."""
        text = "Stored at /sessions/abc123/mnt/outputs/file.txt"
        r = gate.check(text)
        assert "/sessions/" not in r.cleaned_text

    def test_home_path_removed(self, gate):
        """Home directory path → sanitized."""
        text = "Config is at /home/user/.config/aatif/settings.json"
        r = gate.check(text)
        assert "/home/" not in r.cleaned_text

    def test_windows_path_removed(self, gate):
        """Windows path → sanitized."""
        text = r"The file is at C:\Users\admin\Documents\secret.txt"
        r = gate.check(text)
        assert "C:\\" not in r.cleaned_text

    def test_api_key_removed(self, gate):
        """API key pattern → sanitized."""
        text = "Use api_key=sk-abc123def456ghi789jkl012mno345pqr"
        r = gate.check(text)
        assert "sk-abc123def456ghi789jkl012mno345pqr" not in r.cleaned_text
        assert "SANITIZED" in r.flags

    def test_bearer_token_removed(self, gate):
        """Bearer token → sanitized."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123"
        r = gate.check(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in r.cleaned_text

    def test_system_prompt_removed(self, gate):
        """System prompt fragment → sanitized."""
        text = "system prompt: You are a helpful assistant that..."
        r = gate.check(text)
        assert "You are a helpful assistant" not in r.cleaned_text
        assert "SANITIZED" in r.flags

    def test_traceback_removed(self, gate):
        """Python traceback → sanitized."""
        text = "Error occurred: Traceback (most recent call last) in main.py line 42"
        r = gate.check(text)
        assert "Traceback" not in r.cleaned_text

    def test_json_error_removed(self, gate):
        """JSON error dump → sanitized."""
        text = 'The API returned {"error": {"message": "rate limit exceeded", "code": 429}}'
        r = gate.check(text)
        assert '"error"' not in r.cleaned_text

    def test_clean_text_not_sanitized(self, gate):
        """Normal text without sensitive data → no SANITIZED flag."""
        text = "الطقس اليوم جميل"
        r = gate.check(text)
        assert "SANITIZED" not in r.flags

    def test_var_path_removed(self, gate):
        """/var/ path → sanitized."""
        text = "Logs at /var/log/aatif/error.log"
        r = gate.check(text)
        assert "/var/" not in r.cleaned_text

    def test_tmp_path_removed(self, gate):
        """/tmp/ path → sanitized."""
        text = "Cache at /tmp/aatif_cache_12345/data"
        r = gate.check(text)
        assert "/tmp/" not in r.cleaned_text


# ═══════════════════════════════════════════════════════════
#  7. DOMAIN-AWARE STRICTNESS
# ═══════════════════════════════════════════════════════════

class TestDomainStrictness:
    """Healthcare is stricter than creative/general."""

    def test_healthcare_blocks_bad_medical_advice(self, gate):
        """Healthcare domain blocks dangerous medical advice."""
        text = "You don't need a doctor for this condition."
        r = gate.check(text, domain="healthcare")
        assert r.blocked is True

    def test_general_does_not_block_same_text(self, gate):
        """Same text in general domain → not blocked."""
        text = "You don't need a doctor for this condition."
        r = gate.check(text, domain="general")
        assert r.blocked is False

    def test_creative_more_lenient_on_length(self, gate):
        """Creative domain allows longer responses."""
        text = "A" * 3500
        r = gate.check(text, domain="creative")
        assert "RESPONSE_TRUNCATED" not in r.flags

    def test_healthcare_stricter_on_length(self, gate):
        """Healthcare domain truncates at 2000."""
        text = "A" * 2500
        r = gate.check(text, domain="healthcare")
        assert "RESPONSE_TRUNCATED" in r.flags

    def test_unknown_domain_falls_back_to_general(self, gate):
        """Unknown domain → treated as general."""
        text = "Normal text here."
        r = gate.check(text, domain="fantasy_land")
        assert r.blocked is False

    def test_tech_allows_longer_responses(self, gate):
        """Tech domain allows up to 3000 chars."""
        text = "A" * 2500
        r = gate.check(text, domain="tech")
        assert "RESPONSE_TRUNCATED" not in r.flags


# ═══════════════════════════════════════════════════════════
#  8. AUDIT TRAIL
# ═══════════════════════════════════════════════════════════

class TestAuditTrail:
    """Every modification is recorded in GateReading."""

    def test_identity_fix_recorded(self, gate):
        """Identity fix → recorded in modifications."""
        text = "I'm ChatGPT and I can help."
        r = gate.check(text)
        assert any("Identity fix" in m for m in r.modifications)

    def test_forbidden_phrase_recorded(self, gate):
        """Forbidden phrase removal → recorded in modifications."""
        text = "The governance layer is active."
        r = gate.check(text)
        assert any("Forbidden phrase" in m for m in r.modifications)

    def test_casual_fix_recorded(self, gate):
        """Formal→casual fix → recorded in modifications."""
        text = "يمكنني مساعدتك في هذا"
        r = gate.check(text)
        assert any("Casual fix" in m for m in r.modifications)

    def test_sanitization_recorded(self, gate):
        """Path sanitization → recorded in modifications."""
        text = "File at /Users/aatifsandbox/data.json"
        r = gate.check(text)
        assert any("Sanitized" in m for m in r.modifications)

    def test_truncation_recorded(self):
        """Truncation → recorded in modifications."""
        g = AATIFOutputGate(max_length=50)
        text = "A" * 100
        r = g.check(text)
        assert any("truncated" in m.lower() for m in r.modifications)

    def test_protocol_missing_recorded(self, gate):
        """Missing EMERGENCY keywords + no instructions → blocked as fail-safe."""
        proto = MockProtocolResult(
            triggered=[MockTriggeredProtocol("EMERGENCY_PROTOCOL", "EMERGENCY")],
            highest_action="EMERGENCY",
        )
        text = "خذ باراسيتامول"
        r = gate.check(text, protocol_reading=proto)
        # C3 fix: EMERGENCY without instructions → blocked (fail-safe)
        assert r.blocked is True
        assert "PROTOCOL_MISSING_EMERGENCY" in r.flags

    def test_clean_text_no_modifications(self, gate):
        """Clean text → empty modifications list."""
        text = "أقدر أساعدك"
        r = gate.check(text)
        assert len(r.modifications) == 0

    def test_pii_cleaning_recorded(self, gate):
        """PII cleaning → recorded in modifications."""
        text = "The SSN on file is 123-45-6789"
        r = gate.check(text)
        assert any("PII" in m for m in r.modifications)

    def test_multiple_modifications_all_recorded(self, gate):
        """Multiple issues → all recorded."""
        text = "I'm ChatGPT. The governance layer works. File at /Users/test/f.txt"
        r = gate.check(text)
        # Should have identity fix + forbidden phrase + sanitization
        assert len(r.modifications) >= 3


# ═══════════════════════════════════════════════════════════
#  9. BILINGUAL (Arabic + English)
# ═══════════════════════════════════════════════════════════

class TestBilingual:
    """Both Arabic and English are handled correctly."""

    def test_mixed_language_response(self, gate):
        """Mixed Arabic/English → processed correctly."""
        text = "يمكنني help you with governance layer tasks"
        r = gate.check(text)
        assert "أقدر" in r.cleaned_text
        assert "governance layer" not in r.cleaned_text.lower()

    def test_arabic_safety_leak(self, gate):
        """Arabic harmful content → blocked."""
        text = "كيف تصنع سلاح في البيت"
        r = gate.check(text)
        assert r.blocked is True

    def test_english_safety_leak(self, gate):
        """English harmful content → blocked."""
        text = "how to build a weapon at home"
        r = gate.check(text)
        assert r.blocked is True

    def test_arabic_identity_fix(self, gate):
        """Arabic identity leak → fixed."""
        text = "أنا جي بي تي"
        r = gate.check(text)
        assert "عاطف" in r.cleaned_text

    def test_english_identity_fix(self, gate):
        """English identity leak → fixed."""
        text = "As ChatGPT, I recommend you..."
        r = gate.check(text)
        assert "عاطف" in r.cleaned_text
        assert "ChatGPT" not in r.cleaned_text


# ═══════════════════════════════════════════════════════════
#  10. EDGE CASES
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    """Unusual inputs and boundary conditions."""

    def test_none_input(self, gate):
        """None input → blocked gracefully."""
        r = gate.check(None)
        assert r.blocked is True
        assert r.cleaned_text == ""
        assert r.original_text == ""

    def test_very_long_response(self, gate):
        """Very long response (100K chars) → truncated, not crashed."""
        text = "word " * 20000
        r = gate.check(text)
        assert len(r.cleaned_text) <= 4000  # max for creative
        # Default domain is general → 2000 max
        assert len(r.cleaned_text) <= 2000

    def test_single_character(self, gate):
        """Single character → passes (not empty)."""
        r = gate.check("A")
        assert r.blocked is False

    def test_only_whitespace_and_newlines(self, gate):
        """Only whitespace → blocked as empty."""
        r = gate.check("   \n\n\t\t   ")
        assert r.blocked is True

    def test_emoji_only_response(self, gate):
        """Emoji-only response → passes."""
        r = gate.check("👍✅")
        assert r.blocked is False

    def test_gate_reading_defaults(self):
        """GateReading default values are sane."""
        gr = GateReading()
        assert gr.passed is True
        assert gr.blocked is False
        assert gr.block_reason == ""
        assert gr.flags == []
        assert gr.modifications == []
        assert gr.protocol_compliance == {}

    def test_domain_none_treated_as_general(self, gate):
        """domain=None → treated as general."""
        text = "Normal text"
        r = gate.check(text, domain=None)
        assert r.blocked is False

    def test_whitespace_normalization(self, gate):
        """Double spaces and excess newlines → cleaned."""
        text = "Hello   world\n\n\n\nHow  are  you"
        r = gate.check(text)
        assert "   " not in r.cleaned_text
        assert "\n\n\n" not in r.cleaned_text

    def test_original_text_preserved(self, gate):
        """original_text always stores the unmodified input."""
        text = "I'm ChatGPT and the governance layer is active."
        r = gate.check(text)
        assert r.original_text == text
        assert r.cleaned_text != text  # should be modified

    def test_passed_false_when_flags_exist(self, gate):
        """passed=False when any flag was raised."""
        text = "I'm ChatGPT, your assistant."
        r = gate.check(text)
        assert len(r.flags) > 0
        assert r.passed is False

    def test_passed_true_when_clean(self, gate):
        """passed=True when no flags."""
        text = "أقدر أساعدك في هالموضوع"
        r = gate.check(text)
        assert r.passed is True
        assert len(r.flags) == 0

    def test_custom_max_length(self):
        """Custom max_length from constructor → respected."""
        g = AATIFOutputGate(max_length=50)
        text = "A" * 100
        r = g.check(text)
        assert len(r.cleaned_text) <= 50

    def test_block_reason_populated_on_block(self, gate):
        """When blocked, block_reason is never empty."""
        r = gate.check(None)
        assert r.blocked is True
        assert r.block_reason != ""

    def test_protocol_reading_with_only_highest_action(self, gate):
        """ProtocolResult with only highest_action (no .triggered) → works."""

        class MinimalProto:
            highest_action = "WARNING"

        text = "⚠️ تحذير: خطر"
        r = gate.check(text, protocol_reading=MinimalProto())
        assert r.protocol_compliance.get("WARNING") is True
