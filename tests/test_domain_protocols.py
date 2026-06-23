#!/usr/bin/env python3
"""
AATIF P(d) — Domain Protocols Tests
====================================

Tests for aatif_domain_protocols.py — the deterministic rules layer
between S(d) safety math and R(d) response style.

WHY THIS FILE EXISTS
────────────────────
P(d) adds domain-specific constraints AFTER S(d) decides safety.
Even safe content can trigger protocols (e.g. "chest pain" is not harmful
content, but it IS a medical emergency requiring protocol response).

P(d) must NEVER override S(d). It can only add restrictions.

THE TESTING STRATEGY
────────────────────
P(d) is pure Python — no model, no embeddings, just regex.
We construct specific inputs and verify structured output.
Every test is deterministic and CI-friendly.

Test structure:
  1. Healthcare protocols (Emergency, Medication, Diagnosis, Child, Mental)
  2. Education protocols (AGE_GATE, LEARNING_SCAFFOLD, EXAM_INTEGRITY, CHILD_PROTECTION)
  3. Tech protocols (DANGEROUS_COMMAND, SECURITY_ADVISORY, DATA_LOSS_WARNING)
  4. E-Commerce protocols (HONEST_PRICING, REFUND_TRANSPARENCY, PRODUCT_TRUTH)
  5. Creative protocols (ATTRIBUTION, SENSITIVE_CONTENT, NO_REAL_PERSON)
  6. Cross-domain (HUMAN_PRIMACY)
  7. P(d) never overrides S(d)
  8. SFC (Successful Fail Closure)
  9. Protocol stacking
  10. Edge cases
  11. Unknown domain handling

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

from aatif_domain_protocols import (
    DomainProtocol, ProtocolResult, TriggeredProtocol,
    ACTION_NONE, ACTION_GUIDE, ACTION_DISCLAIMER, ACTION_WARNING,
    ACTION_AGE_GATE, ACTION_ESCALATE, ACTION_EMERGENCY, ACTION_BLOCK,
    _ACTION_SEVERITY,
)


# ═══════════════════════════════════════════════════════════
#  Fixture
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def pd():
    """Create a fresh DomainProtocol instance."""
    return DomainProtocol()


# ═══════════════════════════════════════════════════════════
#  Helper
# ═══════════════════════════════════════════════════════════

def _protocol_names(result: ProtocolResult) -> set:
    """Extract protocol names from a result for easy assertion."""
    return {t.name for t in result.triggered}


def _has_protocol(result: ProtocolResult, name: str) -> bool:
    """Check if a specific protocol was triggered."""
    return name in _protocol_names(result)


# ═══════════════════════════════════════════════════════════
#  1. Healthcare Domain Protocols
# ═══════════════════════════════════════════════════════════

class TestHealthcareEmergencyProtocol:
    """EMERGENCY_PROTOCOL triggers for life-threatening situations."""

    def test_chest_pain_english(self, pd):
        r = pd.evaluate("I have chest pain", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")
        assert r.highest_action == ACTION_EMERGENCY

    def test_chest_pain_arabic(self, pd):
        r = pd.evaluate("عندي ألم بالصدر", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")
        assert r.highest_action == ACTION_EMERGENCY

    def test_chest_pain_dialect(self, pd):
        r = pd.evaluate("صدري يوجعني مرة", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_breathing_difficulty_english(self, pd):
        r = pd.evaluate("I can't breathe", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_breathing_difficulty_arabic(self, pd):
        r = pd.evaluate("ما اقدر اتنفس", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_shortness_of_breath(self, pd):
        r = pd.evaluate("I have shortness of breath", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_suicidal_ideation_english(self, pd):
        r = pd.evaluate("I want to kill myself", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_suicidal_ideation_arabic(self, pd):
        r = pd.evaluate("أبي أموت", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_suicidal_ideation_arabic_variant(self, pd):
        r = pd.evaluate("نفسي أموت ما ابي أعيش", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_severe_bleeding_english(self, pd):
        r = pd.evaluate("I have severe bleeding that won't stop", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_severe_bleeding_arabic(self, pd):
        r = pd.evaluate("عندي نزيف شديد", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_allergic_reaction(self, pd):
        r = pd.evaluate("I think it's anaphylaxis", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_throat_swelling(self, pd):
        r = pd.evaluate("حلقي متورم وعندي حساسية شديدة", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_stroke_english(self, pd):
        r = pd.evaluate("I think I'm having a stroke", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_stroke_arabic(self, pd):
        r = pd.evaluate("عندي جلطة دماغية", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_poisoning_english(self, pd):
        r = pd.evaluate("I think I was poisoned", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_overdose(self, pd):
        r = pd.evaluate("I took an overdose", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_poisoning_arabic(self, pd):
        r = pd.evaluate("طفلي ابتلع سم", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_emergency_instruction_text(self, pd):
        """Emergency instruction must mention seeking medical help."""
        r = pd.evaluate("chest pain", domain="healthcare")
        assert "طوارئ" in r.combined_instructions
        assert "طبيب" in r.combined_instructions or "إسعاف" in r.combined_instructions

    def test_heart_attack_arabic(self, pd):
        r = pd.evaluate("أحس بجلطة قلب", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")


class TestHealthcareMedicationDisclaimer:
    """MEDICATION_DISCLAIMER triggers for drug/dosage questions."""

    def test_medication_english(self, pd):
        r = pd.evaluate("What medication should I take?", domain="healthcare")
        assert _has_protocol(r, "MEDICATION_DISCLAIMER")
        assert r.highest_action == ACTION_DISCLAIMER

    def test_dosage_english(self, pd):
        r = pd.evaluate("What's the proper dosage?", domain="healthcare")
        assert _has_protocol(r, "MEDICATION_DISCLAIMER")

    def test_medication_arabic(self, pd):
        r = pd.evaluate("كم جرعة الباراسيتامول؟", domain="healthcare")
        assert _has_protocol(r, "MEDICATION_DISCLAIMER")

    def test_medicine_arabic(self, pd):
        r = pd.evaluate("ابي دواء للصداع", domain="healthcare")
        assert _has_protocol(r, "MEDICATION_DISCLAIMER")

    def test_pills_arabic(self, pd):
        r = pd.evaluate("كم حبة آخذ؟", domain="healthcare")
        assert _has_protocol(r, "MEDICATION_DISCLAIMER")

    def test_side_effects(self, pd):
        r = pd.evaluate("What are the side effects of ibuprofen?", domain="healthcare")
        assert _has_protocol(r, "MEDICATION_DISCLAIMER")

    def test_antibiotic_arabic(self, pd):
        r = pd.evaluate("ابي مضاد حيوي للالتهاب", domain="healthcare")
        assert _has_protocol(r, "MEDICATION_DISCLAIMER")


class TestHealthcareDiagnosisGuard:
    """DIAGNOSIS_GUARD triggers for symptom descriptions."""

    def test_do_i_have(self, pd):
        r = pd.evaluate("Do I have diabetes?", domain="healthcare")
        assert _has_protocol(r, "DIAGNOSIS_GUARD")

    def test_symptoms_arabic(self, pd):
        r = pd.evaluate("عندي صداع ودوخة وغثيان", domain="healthcare")
        assert _has_protocol(r, "DIAGNOSIS_GUARD")

    def test_what_is_wrong(self, pd):
        r = pd.evaluate("What could it be? I have a rash", domain="healthcare")
        assert _has_protocol(r, "DIAGNOSIS_GUARD")

    def test_diagnosis_arabic(self, pd):
        r = pd.evaluate("إيش عندي يا دكتور؟", domain="healthcare")
        assert _has_protocol(r, "DIAGNOSIS_GUARD")


class TestHealthcareChildPatient:
    """CHILD_PATIENT triggers for child health issues."""

    def test_child_sick_english(self, pd):
        r = pd.evaluate("My baby is sick with a fever", domain="healthcare")
        assert _has_protocol(r, "CHILD_PATIENT")
        assert r.highest_action == ACTION_ESCALATE

    def test_child_sick_arabic(self, pd):
        r = pd.evaluate("ولدي عنده حرارة عالية", domain="healthcare")
        assert _has_protocol(r, "CHILD_PATIENT")

    def test_infant_vomit(self, pd):
        r = pd.evaluate("My infant won't stop vomiting", domain="healthcare")
        assert _has_protocol(r, "CHILD_PATIENT")

    def test_daughter_sick_arabic(self, pd):
        r = pd.evaluate("بنتي مريضة وتكح كثير", domain="healthcare")
        assert _has_protocol(r, "CHILD_PATIENT")


class TestHealthcareMentalHealth:
    """MENTAL_HEALTH_CARE triggers for depression, anxiety, self-harm."""

    def test_depression_english(self, pd):
        r = pd.evaluate("I've been depressed for weeks", domain="healthcare")
        assert _has_protocol(r, "MENTAL_HEALTH_CARE")
        assert r.highest_action == ACTION_ESCALATE

    def test_depression_arabic(self, pd):
        r = pd.evaluate("عندي اكتئاب شديد", domain="healthcare")
        assert _has_protocol(r, "MENTAL_HEALTH_CARE")

    def test_anxiety(self, pd):
        r = pd.evaluate("I have severe anxiety and panic attacks", domain="healthcare")
        assert _has_protocol(r, "MENTAL_HEALTH_CARE")

    def test_self_harm(self, pd):
        r = pd.evaluate("I've been self-harming", domain="healthcare")
        assert _has_protocol(r, "MENTAL_HEALTH_CARE")

    def test_tired_mentally_arabic(self, pd):
        r = pd.evaluate("تعبان نفسي مرة ما أقدر أتحمل", domain="healthcare")
        assert _has_protocol(r, "MENTAL_HEALTH_CARE")

    def test_mental_health_instruction(self, pd):
        """Mental health instruction should be compassionate."""
        r = pd.evaluate("اكتئاب", domain="healthcare")
        assert "مختص" in r.combined_instructions


# ═══════════════════════════════════════════════════════════
#  2. Education Domain Protocols
# ═══════════════════════════════════════════════════════════

class TestEducationAgeGate:
    """AGE_GATE triggers for adult content in education context."""

    def test_violence_student(self, pd):
        r = pd.evaluate("violence in student context", domain="education")
        assert _has_protocol(r, "AGE_GATE")
        assert r.highest_action == ACTION_AGE_GATE

    def test_drugs_school_arabic(self, pd):
        r = pd.evaluate("مخدرات في المدرسة", domain="education")
        assert _has_protocol(r, "AGE_GATE")


class TestEducationLearningScaffold:
    """LEARNING_SCAFFOLD triggers for explain/teach requests."""

    def test_explain_english(self, pd):
        r = pd.evaluate("explain how gravity works", domain="education")
        assert _has_protocol(r, "LEARNING_SCAFFOLD")
        assert r.highest_action == ACTION_GUIDE

    def test_teach_arabic(self, pd):
        r = pd.evaluate("اشرح لي الجاذبية", domain="education")
        assert _has_protocol(r, "LEARNING_SCAFFOLD")

    def test_how_to(self, pd):
        r = pd.evaluate("how to solve quadratic equations", domain="education")
        assert _has_protocol(r, "LEARNING_SCAFFOLD")

    def test_teach_me_arabic(self, pd):
        r = pd.evaluate("علمني الرياضيات", domain="education")
        assert _has_protocol(r, "LEARNING_SCAFFOLD")


class TestEducationExamIntegrity:
    """EXAM_INTEGRITY triggers for direct exam answer requests."""

    def test_exam_answer_english(self, pd):
        r = pd.evaluate("give me the answer to the exam", domain="education")
        assert _has_protocol(r, "EXAM_INTEGRITY")

    def test_homework_solution(self, pd):
        r = pd.evaluate("solve my homework please", domain="education")
        assert _has_protocol(r, "EXAM_INTEGRITY")

    def test_exam_arabic(self, pd):
        r = pd.evaluate("أعطني حل الامتحان", domain="education")
        assert _has_protocol(r, "EXAM_INTEGRITY")

    def test_exam_arabic_dialect(self, pd):
        r = pd.evaluate("عطني الإجابة", domain="education")
        assert _has_protocol(r, "EXAM_INTEGRITY")


class TestEducationChildProtection:
    """CHILD_PROTECTION triggers for personal data + children."""

    def test_child_data_english(self, pd):
        r = pd.evaluate("collect child personal data and address", domain="education")
        assert _has_protocol(r, "CHILD_PROTECTION")
        assert r.highest_action == ACTION_BLOCK

    def test_student_data_arabic(self, pd):
        r = pd.evaluate("بيانات شخصية للطالب القاصر", domain="education")
        assert _has_protocol(r, "CHILD_PROTECTION")


# ═══════════════════════════════════════════════════════════
#  3. Tech Domain Protocols
# ═══════════════════════════════════════════════════════════

class TestTechDangerousCommand:
    """DANGEROUS_COMMAND triggers for destructive operations."""

    def test_rm_rf(self, pd):
        r = pd.evaluate("sudo rm -rf /", domain="tech")
        assert _has_protocol(r, "DANGEROUS_COMMAND")
        assert r.highest_action == ACTION_WARNING

    def test_drop_table(self, pd):
        r = pd.evaluate("DROP TABLE users", domain="tech")
        assert _has_protocol(r, "DANGEROUS_COMMAND")

    def test_drop_database(self, pd):
        r = pd.evaluate("DROP DATABASE production", domain="tech")
        assert _has_protocol(r, "DANGEROUS_COMMAND")

    def test_chmod_777(self, pd):
        r = pd.evaluate("chmod -R 777 /", domain="tech")
        assert _has_protocol(r, "DANGEROUS_COMMAND")

    def test_destructive_arabic(self, pd):
        r = pd.evaluate("حذف كل الملفات", domain="tech")
        assert _has_protocol(r, "DANGEROUS_COMMAND")

    def test_fork_bomb(self, pd):
        r = pd.evaluate(":(){ :|:& };:", domain="tech")
        assert _has_protocol(r, "DANGEROUS_COMMAND")


class TestTechSecurityAdvisory:
    """SECURITY_ADVISORY triggers for credential storage issues."""

    def test_plaintext_password(self, pd):
        r = pd.evaluate("store password in plain text file", domain="tech")
        assert _has_protocol(r, "SECURITY_ADVISORY")

    def test_hardcoded_password(self, pd):
        r = pd.evaluate("hardcoded password in the code", domain="tech")
        assert _has_protocol(r, "SECURITY_ADVISORY")

    def test_api_key_equals(self, pd):
        r = pd.evaluate("api_key = 'abc123'", domain="tech")
        assert _has_protocol(r, "SECURITY_ADVISORY")

    def test_password_arabic(self, pd):
        r = pd.evaluate("خزن كلمة سر في ملف نصي", domain="tech")
        assert _has_protocol(r, "SECURITY_ADVISORY")


class TestTechDataLoss:
    """DATA_LOSS_WARNING triggers for risky data operations."""

    def test_delete_database(self, pd):
        r = pd.evaluate("delete database files", domain="tech")
        assert _has_protocol(r, "DATA_LOSS_WARNING")

    def test_wipe_disk(self, pd):
        r = pd.evaluate("wipe the disk completely", domain="tech")
        assert _has_protocol(r, "DATA_LOSS_WARNING")

    def test_no_backup(self, pd):
        r = pd.evaluate("overwrite files with no backup", domain="tech")
        assert _has_protocol(r, "DATA_LOSS_WARNING")

    def test_data_loss_arabic(self, pd):
        r = pd.evaluate("حذف قاعدة البيانات", domain="tech")
        assert _has_protocol(r, "DATA_LOSS_WARNING")


# ═══════════════════════════════════════════════════════════
#  4. E-Commerce Domain Protocols
# ═══════════════════════════════════════════════════════════

class TestEcommerceHonestPricing:
    """HONEST_PRICING triggers for fake urgency patterns."""

    def test_urgency_english(self, pd):
        r = pd.evaluate("Only 3 left! Hurry, act now!", domain="ecommerce")
        assert _has_protocol(r, "HONEST_PRICING")

    def test_limited_time(self, pd):
        r = pd.evaluate("Limited time offer! Last chance!", domain="ecommerce")
        assert _has_protocol(r, "HONEST_PRICING")

    def test_urgency_arabic(self, pd):
        r = pd.evaluate("سارع! فقط 5 باقي!", domain="ecommerce")
        assert _has_protocol(r, "HONEST_PRICING")

    def test_expires_soon(self, pd):
        r = pd.evaluate("العرض ينتهي قريباً", domain="ecommerce")
        assert _has_protocol(r, "HONEST_PRICING")


class TestEcommerceRefund:
    """REFUND_TRANSPARENCY triggers for return/refund queries."""

    def test_refund_english(self, pd):
        r = pd.evaluate("What's your refund policy?", domain="ecommerce")
        assert _has_protocol(r, "REFUND_TRANSPARENCY")

    def test_return_policy(self, pd):
        r = pd.evaluate("I need to know the return policy", domain="ecommerce")
        assert _has_protocol(r, "REFUND_TRANSPARENCY")

    def test_refund_arabic(self, pd):
        r = pd.evaluate("أبي استرجاع المبلغ", domain="ecommerce")
        assert _has_protocol(r, "REFUND_TRANSPARENCY")

    def test_money_back(self, pd):
        r = pd.evaluate("Can I get my money back?", domain="ecommerce")
        assert _has_protocol(r, "REFUND_TRANSPARENCY")


class TestEcommerceProductTruth:
    """PRODUCT_TRUTH triggers for exaggerated claims."""

    def test_guaranteed_cure(self, pd):
        r = pd.evaluate("This product is guaranteed to cure all", domain="ecommerce")
        assert _has_protocol(r, "PRODUCT_TRUTH")

    def test_miracle_arabic(self, pd):
        r = pd.evaluate("منتج معجزة يعالج كل شي", domain="ecommerce")
        assert _has_protocol(r, "PRODUCT_TRUTH")

    def test_no_side_effects(self, pd):
        r = pd.evaluate("no side effects whatsoever", domain="ecommerce")
        assert _has_protocol(r, "PRODUCT_TRUTH")


# ═══════════════════════════════════════════════════════════
#  5. Creative Domain Protocols
# ═══════════════════════════════════════════════════════════

class TestCreativeAttribution:
    """ATTRIBUTION_REMINDER triggers for inspired-by content."""

    def test_inspired_by(self, pd):
        r = pd.evaluate("write a story inspired by Tolkien", domain="creative")
        assert _has_protocol(r, "ATTRIBUTION_REMINDER")

    def test_in_style_of(self, pd):
        r = pd.evaluate("write in the style of Hemingway", domain="creative")
        assert _has_protocol(r, "ATTRIBUTION_REMINDER")

    def test_inspired_arabic(self, pd):
        r = pd.evaluate("اكتب قصة مستوحى من نجيب محفوظ", domain="creative")
        assert _has_protocol(r, "ATTRIBUTION_REMINDER")


class TestCreativeSensitiveContent:
    """SENSITIVE_CONTENT_NOTE triggers for sensitive creative themes."""

    def test_war_story(self, pd):
        r = pd.evaluate("write a story about war", domain="creative")
        assert _has_protocol(r, "SENSITIVE_CONTENT_NOTE")

    def test_trauma_arabic(self, pd):
        r = pd.evaluate("قصة عن صدمة نفسية وعنف", domain="creative")
        assert _has_protocol(r, "SENSITIVE_CONTENT_NOTE")

    def test_holocaust(self, pd):
        r = pd.evaluate("a novel set during the holocaust", domain="creative")
        assert _has_protocol(r, "SENSITIVE_CONTENT_NOTE")


class TestCreativeRealPersonFiction:
    """NO_REAL_PERSON_FICTION triggers for fiction about real people."""

    def test_fiction_about_person(self, pd):
        r = pd.evaluate("write a fiction about Elon Musk", domain="creative")
        assert _has_protocol(r, "NO_REAL_PERSON_FICTION")
        assert r.highest_action == ACTION_WARNING

    def test_story_about_real_person(self, pd):
        r = pd.evaluate("create a story featuring Barack Obama", domain="creative")
        assert _has_protocol(r, "NO_REAL_PERSON_FICTION")


# ═══════════════════════════════════════════════════════════
#  6. Cross-Domain Protocols
# ═══════════════════════════════════════════════════════════

class TestHumanPrimacy:
    """HUMAN_PRIMACY triggers for life-affecting decisions."""

    def test_stop_medication(self, pd):
        r = pd.evaluate("should I stop my medication?", domain="general")
        assert _has_protocol(r, "HUMAN_PRIMACY")
        assert r.highest_action == ACTION_ESCALATE

    def test_quit_job(self, pd):
        r = pd.evaluate("should I quit my job?", domain="general")
        assert _has_protocol(r, "HUMAN_PRIMACY")

    def test_invest_arabic(self, pd):
        r = pd.evaluate("هل أستثمر كل فلوسي؟", domain="general")
        assert _has_protocol(r, "HUMAN_PRIMACY")

    def test_stop_treatment_arabic(self, pd):
        r = pd.evaluate("هل أوقف العلاج؟", domain="general")
        assert _has_protocol(r, "HUMAN_PRIMACY")

    def test_cross_domain_in_tech(self, pd):
        """Cross-domain protocols fire even in non-general domains."""
        r = pd.evaluate("should I stop my medication?", domain="tech")
        assert _has_protocol(r, "HUMAN_PRIMACY")

    def test_cross_domain_in_healthcare(self, pd):
        """Cross-domain fires alongside domain-specific protocols."""
        r = pd.evaluate("should I stop my medication?", domain="healthcare")
        assert _has_protocol(r, "HUMAN_PRIMACY")
        # Also triggers MEDICATION_DISCLAIMER from healthcare domain
        assert _has_protocol(r, "MEDICATION_DISCLAIMER")


# ═══════════════════════════════════════════════════════════
#  7. P(d) NEVER overrides S(d) — sovereignty constraint
# ═══════════════════════════════════════════════════════════

class TestPdNeverOverridesSd:
    """
    P(d) receives s_decision and stores it — never changes it.

    The s_decision field in ProtocolResult is read-only from P(d).
    P(d) adds constraints/protocols, it never softens S(d).
    """

    def test_safe_stop_preserved(self, pd):
        """If S says SAFE_STOP, P(d) stores it unchanged."""
        r = pd.evaluate("chest pain", domain="healthcare",
                         s_decision="SAFE_STOP")
        assert r.s_decision == "SAFE_STOP"

    def test_safe_freeze_preserved(self, pd):
        """If S says SAFE_FREEZE, P(d) stores it unchanged."""
        r = pd.evaluate("عندي ألم صدر", domain="healthcare",
                         s_decision="SAFE_FREEZE")
        assert r.s_decision == "SAFE_FREEZE"

    def test_execute_preserved(self, pd):
        """If S says EXECUTE, P(d) stores it unchanged (but adds protocols)."""
        r = pd.evaluate("chest pain", domain="healthcare",
                         s_decision="EXECUTE")
        assert r.s_decision == "EXECUTE"
        # P(d) adds emergency protocol but doesn't change s_decision
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_clarify_preserved(self, pd):
        r = pd.evaluate("medication dosage", domain="healthcare",
                         s_decision="CLARIFY")
        assert r.s_decision == "CLARIFY"

    def test_s_decision_never_downgraded(self, pd):
        """P(d) never downgrades a restrictive S decision."""
        for s_decision in ["SAFE_STOP", "SAFE_FREEZE"]:
            # Benign message that normally wouldn't trigger protocols
            r = pd.evaluate("عطني فكرة هدية", domain="general",
                             s_decision=s_decision)
            assert r.s_decision == s_decision

    def test_p_adds_protocols_regardless_of_s(self, pd):
        """Protocols trigger based on content, not S decision."""
        for s_decision in ["EXECUTE", "CLARIFY", "SAFE_STOP", "SAFE_FREEZE"]:
            r = pd.evaluate("chest pain", domain="healthcare",
                             s_decision=s_decision)
            assert _has_protocol(r, "EMERGENCY_PROTOCOL")


# ═══════════════════════════════════════════════════════════
#  8. SFC (Successful Fail Closure)
# ═══════════════════════════════════════════════════════════

class TestSFC:
    """
    SFC flags messages that mention risky terms but don't
    match a specific protocol.
    "أفشل بأمان أحسن ما أنجح بخطر"
    """

    def test_hospital_mention_general(self, pd):
        """Hospital in general domain → SFC (no healthcare protocols)."""
        r = pd.evaluate("I visited the hospital today", domain="general")
        assert r.sfc_flagged is True
        assert r.highest_action == ACTION_WARNING

    def test_emergency_arabic_general(self, pd):
        r = pd.evaluate("رحت الطوارئ أمس", domain="general")
        assert r.sfc_flagged is True

    def test_fracture_mention(self, pd):
        r = pd.evaluate("He has a fracture", domain="general")
        assert r.sfc_flagged is True

    def test_sfc_not_triggered_when_protocol_matches(self, pd):
        """SFC should NOT fire when a real protocol already matched."""
        r = pd.evaluate("chest pain in hospital", domain="healthcare")
        # EMERGENCY_PROTOCOL fires, so SFC should NOT flag
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")
        assert r.sfc_flagged is False

    def test_benign_no_sfc(self, pd):
        """Benign messages should NOT trigger SFC."""
        r = pd.evaluate("عطني فكرة هدية لأمي", domain="general")
        assert r.sfc_flagged is False
        assert r.highest_action == ACTION_NONE


# ═══════════════════════════════════════════════════════════
#  9. Protocol Stacking
# ═══════════════════════════════════════════════════════════

class TestProtocolStacking:
    """Multiple protocols can fire for one message."""

    def test_emergency_plus_medication(self, pd):
        """Chest pain + medication mention → both protocols fire."""
        r = pd.evaluate("I have chest pain, what medication should I take?",
                         domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")
        assert _has_protocol(r, "MEDICATION_DISCLAIMER")
        # Highest should be EMERGENCY (most severe)
        assert r.highest_action == ACTION_EMERGENCY

    def test_child_plus_diagnosis(self, pd):
        """Child + symptoms → CHILD_PATIENT + DIAGNOSIS_GUARD."""
        r = pd.evaluate("My baby is sick, does she have a fever? عندي صداع",
                         domain="healthcare")
        assert _has_protocol(r, "CHILD_PATIENT")

    def test_emergency_plus_mental_health(self, pd):
        """Suicidal + depression → both fire."""
        r = pd.evaluate("I'm depressed and want to end my life",
                         domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")
        assert _has_protocol(r, "MENTAL_HEALTH_CARE")

    def test_exam_plus_learning(self, pd):
        """Exam + explain → both EXAM_INTEGRITY and LEARNING_SCAFFOLD."""
        r = pd.evaluate("explain how to solve my homework",
                         domain="education")
        assert _has_protocol(r, "EXAM_INTEGRITY")
        assert _has_protocol(r, "LEARNING_SCAFFOLD")

    def test_dangerous_command_plus_data_loss(self, pd):
        """rm -rf + database → DANGEROUS_COMMAND + DATA_LOSS_WARNING."""
        r = pd.evaluate("sudo rm -rf / to delete the database files",
                         domain="tech")
        assert _has_protocol(r, "DANGEROUS_COMMAND")
        assert _has_protocol(r, "DATA_LOSS_WARNING")

    def test_cross_domain_stacks_with_domain(self, pd):
        """Cross-domain HUMAN_PRIMACY stacks with healthcare protocols."""
        r = pd.evaluate("should I stop my medication? what dosage should I try?",
                         domain="healthcare")
        assert _has_protocol(r, "HUMAN_PRIMACY")
        assert _has_protocol(r, "MEDICATION_DISCLAIMER")

    def test_combined_instructions_join(self, pd):
        """Multiple protocols → combined_instructions has multiple texts."""
        r = pd.evaluate("chest pain and I take medication",
                         domain="healthcare")
        # Should contain text from both protocols
        assert len(r.combined_instructions) > 0
        # At least two instruction blocks (newline separated)
        parts = r.combined_instructions.split("\n")
        assert len(parts) >= 2

    def test_highest_action_is_most_severe(self, pd):
        """highest_action should reflect the most severe protocol."""
        r = pd.evaluate("chest pain and my medication dosage",
                         domain="healthcare")
        # EMERGENCY > DISCLAIMER
        assert _ACTION_SEVERITY[r.highest_action] >= _ACTION_SEVERITY[ACTION_DISCLAIMER]


# ═══════════════════════════════════════════════════════════
#  10. Edge Cases
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases: empty message, very long message, mixed language."""

    def test_empty_message(self, pd):
        """Empty string should trigger no protocols."""
        r = pd.evaluate("", domain="general")
        assert r.has_protocols is False
        assert r.highest_action == ACTION_NONE
        assert len(r.triggered) == 0

    def test_whitespace_message(self, pd):
        """Whitespace-only message → no protocols."""
        r = pd.evaluate("   \n\t  ", domain="general")
        assert r.has_protocols is False

    def test_very_long_message(self, pd):
        """Very long message should still be processed."""
        long_msg = "This is a normal message. " * 1000
        r = pd.evaluate(long_msg, domain="general")
        # Should not crash, no protocols expected
        assert isinstance(r, ProtocolResult)

    def test_very_long_with_trigger(self, pd):
        """Very long message with a buried trigger should still match."""
        long_msg = ("Normal text. " * 100 +
                    "I have severe chest pain." +
                    " More normal text." * 100)
        r = pd.evaluate(long_msg, domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_mixed_language(self, pd):
        """Mixed Arabic/English should trigger in both languages."""
        r = pd.evaluate("I have chest pain وألم شديد في الصدر",
                         domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_case_insensitive(self, pd):
        """Patterns should be case-insensitive."""
        r = pd.evaluate("CHEST PAIN", domain="healthcare")
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_benign_message_no_protocols(self, pd):
        """A completely benign message → no protocols, no SFC."""
        r = pd.evaluate("عطني فكرة هدية لأمي", domain="general")
        assert r.has_protocols is False
        assert r.sfc_flagged is False
        assert r.highest_action == ACTION_NONE
        assert r.combined_instructions == ""

    def test_benign_in_healthcare(self, pd):
        """Benign healthcare question shouldn't trigger heavy protocols."""
        r = pd.evaluate("What are office hours?", domain="healthcare")
        # No emergency, no medication, no diagnosis
        assert not _has_protocol(r, "EMERGENCY_PROTOCOL")

    def test_result_domain_stored(self, pd):
        """ProtocolResult stores the domain."""
        r = pd.evaluate("hello", domain="education")
        assert r.domain == "education"

    def test_result_s_decision_default(self, pd):
        """Default s_decision is EXECUTE."""
        r = pd.evaluate("hello", domain="general")
        assert r.s_decision == "EXECUTE"

    def test_context_parameter_accepted(self, pd):
        """context parameter is accepted without error."""
        r = pd.evaluate("chest pain", domain="healthcare",
                         context={"user_age": 25, "conversation_id": "test123"})
        assert _has_protocol(r, "EMERGENCY_PROTOCOL")


# ═══════════════════════════════════════════════════════════
#  11. Unknown Domain Handling
# ═══════════════════════════════════════════════════════════

class TestUnknownDomain:
    """Unknown domains must raise ValueError — same as get_domain_theta."""

    def test_unknown_domain_raises(self, pd):
        with pytest.raises(ValueError, match="Unknown domain"):
            pd.evaluate("test message", domain="banking")

    def test_typo_domain_raises(self, pd):
        with pytest.raises(ValueError, match="Unknown domain"):
            pd.evaluate("test", domain="heathcare")  # typo

    def test_empty_domain_raises(self, pd):
        with pytest.raises(ValueError, match="Unknown domain"):
            pd.evaluate("test", domain="")

    def test_error_message_lists_valid_domains(self, pd):
        """Error message should list valid domains for debugging."""
        with pytest.raises(ValueError) as exc_info:
            pd.evaluate("test", domain="invalid_domain")
        error_msg = str(exc_info.value)
        assert "healthcare" in error_msg
        assert "education" in error_msg
        assert "general" in error_msg

    def test_all_valid_domains_accepted(self, pd):
        """All 6 domains from DOMAIN_CONFIG should work."""
        for domain in ["healthcare", "education", "general", "tech",
                        "ecommerce", "creative"]:
            r = pd.evaluate("hello", domain=domain)
            assert isinstance(r, ProtocolResult)
            assert r.domain == domain


# ═══════════════════════════════════════════════════════════
#  12. Action Severity Ordering
# ═══════════════════════════════════════════════════════════

class TestActionSeverity:
    """Verify severity ordering is consistent."""

    def test_ordering(self):
        assert _ACTION_SEVERITY[ACTION_NONE] < _ACTION_SEVERITY[ACTION_GUIDE]
        assert _ACTION_SEVERITY[ACTION_GUIDE] < _ACTION_SEVERITY[ACTION_DISCLAIMER]
        assert _ACTION_SEVERITY[ACTION_DISCLAIMER] < _ACTION_SEVERITY[ACTION_WARNING]
        assert _ACTION_SEVERITY[ACTION_WARNING] < _ACTION_SEVERITY[ACTION_AGE_GATE]
        assert _ACTION_SEVERITY[ACTION_AGE_GATE] < _ACTION_SEVERITY[ACTION_ESCALATE]
        assert _ACTION_SEVERITY[ACTION_ESCALATE] < _ACTION_SEVERITY[ACTION_EMERGENCY]
        assert _ACTION_SEVERITY[ACTION_EMERGENCY] < _ACTION_SEVERITY[ACTION_BLOCK]

    def test_emergency_is_high(self):
        assert _ACTION_SEVERITY[ACTION_EMERGENCY] == 6

    def test_block_is_highest(self):
        assert _ACTION_SEVERITY[ACTION_BLOCK] == 7

    def test_none_is_zero(self):
        assert _ACTION_SEVERITY[ACTION_NONE] == 0


# ═══════════════════════════════════════════════════════════
#  13. Protocol deduplication
# ═══════════════════════════════════════════════════════════

class TestDeduplication:
    """Each protocol name should appear at most once in triggered list."""

    def test_no_duplicate_protocols(self, pd):
        """Even if multiple patterns match the same protocol, it appears once."""
        # "suicidal" matches multiple EMERGENCY patterns (suicid, kill myself, etc.)
        r = pd.evaluate(
            "I want to kill myself, suicidal thoughts, end my life",
            domain="healthcare"
        )
        names = [t.name for t in r.triggered]
        assert len(names) == len(set(names)), \
            f"Duplicate protocols found: {names}"
