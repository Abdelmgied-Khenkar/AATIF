#!/usr/bin/env python3
"""
AATIF Domain Protocols — P(d) بروتوكولات المجال

The deterministic rules layer between S(d) safety math and R(d) style.
Even when content is safe (S says EXECUTE), domain protocols can add
constraints, disclaimers, escalations, or emergency procedures.

S(d) = is it safe?      (math)
P(d) = what rules apply? (this module)
R(d) = what style to use? (supervised)

Three-layer gate architecture:
    User message → S(d) → P(d) → R(d) → output

P(d) is a DETERMINISTIC rules engine — no ML, no embeddings,
just pattern-matched rules.  It sits after S(d) and before R(d).

Key constraint: P(d) can ADD restrictions but NEVER REMOVE them.
If S(d) says SAFE_STOP, P(d) cannot downgrade to EXECUTE.
P(d) can only make things MORE cautious, not less.

    "S يقرر هل نجاوب — P يقرر بأي شروط — R يقرر بأي أسلوب"
    S decides WHETHER to respond — P decides UNDER WHAT CONDITIONS —
    R decides IN WHAT STYLE.

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from aatif_s_equation import DOMAIN_CONFIG


# ═══════════════════════════════════════════════════════════
#  Protocol action levels — from lightest to heaviest
# ═══════════════════════════════════════════════════════════

# Action constants — what P(d) tells the downstream pipeline to do.
# Ordered from lightest touch to heaviest intervention.
ACTION_NONE      = "NONE"        # لا شيء — no protocol triggered
ACTION_GUIDE     = "GUIDE"       # إرشاد — add learning guidance
ACTION_DISCLAIMER = "DISCLAIMER" # تنبيه — add a disclaimer to response
ACTION_WARNING   = "WARNING"     # تحذير — add explicit warning
ACTION_AGE_GATE  = "AGE_GATE"    # بوابة العمر — age-appropriate check
ACTION_ESCALATE  = "ESCALATE"    # تصعيد — escalate to human/professional
ACTION_EMERGENCY = "EMERGENCY"   # طوارئ — immediate emergency protocol
ACTION_BLOCK     = "BLOCK"       # حظر — block the response entirely

# Severity ordering for comparisons (higher = more severe)
_ACTION_SEVERITY = {
    ACTION_NONE: 0,
    ACTION_GUIDE: 1,
    ACTION_DISCLAIMER: 2,
    ACTION_WARNING: 3,
    ACTION_AGE_GATE: 4,
    ACTION_ESCALATE: 5,
    ACTION_EMERGENCY: 6,
    ACTION_BLOCK: 7,
}


# ═══════════════════════════════════════════════════════════
#  ProtocolResult — what P(d) returns
# ═══════════════════════════════════════════════════════════

@dataclass
class TriggeredProtocol:
    """
    A single protocol that was triggered.

    name:        protocol identifier (e.g. "EMERGENCY_PROTOCOL")
    action:      one of the ACTION_* constants
    instruction: text to add to the response (Arabic — الإرشاد)
    domain:      which domain triggered this ("cross_domain" for universal)
    """
    name: str
    action: str
    instruction: str
    domain: str


@dataclass
class ProtocolResult:
    """
    The complete P(d) output — بروتوكولات مُطبَّقة.

    Contains all triggered protocols, the highest action level,
    and combined instruction text for the downstream pipeline.
    """
    # All protocols that fired
    triggered: list = field(default_factory=list)

    # Highest action among all triggered protocols
    # (downstream should act on the MOST severe)
    highest_action: str = ACTION_NONE

    # Combined instruction text (Arabic) — appended to response
    combined_instructions: str = ""

    # Whether P(d) found anything to add
    has_protocols: bool = False

    # SFC flag — "Successful Fail Closure"
    # True when no protocol matched but the situation felt risky.
    # "أفشل بأمان أحسن ما أنجح بخطر"
    sfc_flagged: bool = False

    # The S(d) decision that was passed in (P never changes this)
    s_decision: str = ""

    # Domain evaluated
    domain: str = ""


# ═══════════════════════════════════════════════════════════
#  Pattern definitions — Arabic + English triggers
# ═══════════════════════════════════════════════════════════
#
# Each pattern set is a list of regex strings compiled with
# re.IGNORECASE. Both Arabic and English variants are included.
# Arabic medical/emergency terms cover MSA + Gulf + Egyptian.

# ── Healthcare Domain Patterns ──

_EMERGENCY_PATTERNS = [
    # Chest pain — ألم الصدر
    r"chest\s*pain", r"ألم.{0,5}صدر", r"صدري.{0,5}يوجع",
    r"ضيق.{0,5}صدر", r"heart\s*attack", r"جلطة.{0,5}قلب",
    # Breathing difficulty — صعوبة التنفس
    r"can'?t\s*breathe", r"difficulty\s*breathing", r"صعوب.{0,5}تنفس",
    r"ما\s*اقدر\s*اتنفس", r"مش\s*قادر.{0,5}اتنفس", r"ضيق.{0,5}تنفس",
    r"shortness\s*of\s*breath",
    # Suicidal ideation — أفكار انتحارية
    r"suicid", r"kill\s*myself", r"end\s*my\s*life",
    r"انتحار", r"أنهي\s*حياتي", r"اقتل\s*نفسي", r"أبي\s*أموت",
    r"نفسي\s*أموت", r"ما\s*ابي\s*أعيش",
    # Severe bleeding — نزيف شديد
    r"severe\s*bleed", r"نزيف.{0,5}شديد", r"نزيف.{0,5}ما\s*يوقف",
    r"heavy\s*bleed", r"won'?t\s*stop\s*bleed",
    # Allergic reaction — حساسية شديدة
    r"anaphyla", r"severe\s*allerg", r"صدمة.{0,5}حساسية",
    r"حساسية.{0,5}شديد", r"تورم.{0,5}حلق", r"throat\s*swell",
    # Stroke symptoms — أعراض الجلطة الدماغية
    r"stroke", r"جلطة.{0,5}دماغ", r"شلل.{0,5}نصفي",
    r"face\s*droop", r"slurred\s*speech", r"ثقل.{0,5}لسان",
    # Poisoning — تسمم
    r"poison", r"overdose", r"تسمم", r"جرعة\s*زائدة",
    r"ابتلع.{0,5}سم", r"شرب.{0,5}مبيد",
]

_MEDICATION_PATTERNS = [
    r"medication", r"medicine", r"dosage", r"dose",
    r"drug\s*interact", r"side\s*effect",
    r"دواء", r"أدوية", r"جرعة", r"علاج",
    r"حبوب", r"دوا", r"مضاد\s*حيوي", r"مسكن",
    r"أثار\s*جانبية", r"تأثيرات\s*جانبية",
    r"كم\s*حبة", r"كم\s*جرعة",
]

_DIAGNOSIS_PATTERNS = [
    r"do\s*i\s*have", r"is\s*this", r"what\s*(is|could)\s*(wrong|it\s*be)",
    r"diagnos", r"symptoms?\s*of",
    r"عندي.{0,10}(مرض|ألم|وجع|صداع|حرارة|كحة|إسهال|إمساك|دوخة|غثيان)",
    r"هل\s*عندي", r"إيش\s*عندي", r"وش\s*عندي",
    r"أعراض", r"تشخيص",
    r"ليه\s*عندي.{0,10}(ألم|وجع|صداع)",
]

_CHILD_PATIENT_PATTERNS = [
    r"(child|kid|baby|infant|toddler|newborn).{0,20}(sick|pain|fever|cough|vomit|rash|hurt)",
    r"(sick|pain|fever|cough|vomit|rash|hurt).{0,20}(child|kid|baby|infant|toddler|newborn)",
    r"(طفل|بيبي|رضيع|ولد|بنت).{0,20}(مريض|حرارة|كحة|استفراغ|ألم|وجع|طفح)",
    r"(مريض|حرارة|كحة|استفراغ|ألم|وجع|طفح).{0,20}(طفل|بيبي|رضيع|ولدي|بنتي)",
    r"my\s*(son|daughter|baby|child).{0,15}(sick|fever|pain|hurt|cough)",
    r"(ولدي|بنتي|طفلي).{0,15}(مريض|حرارة|يوجع|يكح|يستفرغ)",
]

_MENTAL_HEALTH_PATTERNS = [
    r"depress", r"anxiet", r"anxiety", r"panic\s*attack",
    r"self[- ]?harm", r"cutting\s*(myself|my)",
    r"اكتئاب", r"قلق\s*شديد", r"نوبة\s*هلع",
    r"إيذاء\s*نفس", r"أجرح\s*نفسي",
    r"تعبان\s*نفسي", r"حالت?ي\s*النفسية",
    r"ما\s*أقدر\s*أتحمل", r"مش\s*قادر\s*أكمل",
]

# ── Education Domain Patterns ──

_AGE_GATE_PATTERNS = [
    # Adult / mature topics combined with education markers
    r"(sex|porn|violen|drug|alcohol|gambl).{0,30}(student|school|class|child|kid|learn)",
    r"(student|school|class|child|kid|learn).{0,30}(sex|porn|violen|drug|alcohol|gambl)",
    r"(جنس|عنف|مخدر|كحول|قمار).{0,30}(طالب|مدرسة|فصل|طفل|تعليم)",
    r"(طالب|مدرسة|فصل|طفل|تعليم).{0,30}(جنس|عنف|مخدر|كحول|قمار)",
]

_LEARNING_SCAFFOLD_PATTERNS = [
    r"explain", r"teach\s*me", r"how\s*(does|do|to)",
    r"help\s*me\s*understand", r"what\s*is",
    r"اشرح", r"فهمني", r"علمني", r"كيف",
    r"وش\s*معنى", r"إيش\s*يعني", r"ما\s*معنى",
]

_EXAM_INTEGRITY_PATTERNS = [
    r"(answer|solution)\s*(to|for|of)\s*(exam|test|quiz|homework|assignment)",
    r"give\s*me\s*the\s*answer",
    r"solve\s*(this|my)\s*(exam|test|quiz|homework)",
    r"(حل|إجابة|جواب).{0,10}(امتحان|اختبار|واجب|تمرين)",
    r"حل\s*لي\s*(الامتحان|الاختبار|الواجب)",
    r"أعطني\s*(الحل|الإجابة|الجواب)",
    r"عطني\s*(الحل|الإجابة|الجواب)",
]

_CHILD_PROTECTION_PATTERNS = [
    r"(child|kid|minor|student).{0,20}(personal\s*data|address|phone|location|photo)",
    r"(personal\s*data|address|phone|location|photo).{0,20}(child|kid|minor|student)",
    r"(طفل|طالب|قاصر).{0,20}(بيانات\s*شخصية|عنوان|رقم|موقع|صورة)",
    r"(بيانات\s*شخصية|عنوان|رقم|موقع|صورة).{0,20}(طفل|طالب|قاصر)",
    r"collect.{0,10}(child|kid|student|minor).{0,10}(info|data)",
]

# ── Tech Domain Patterns ──

_DANGEROUS_COMMAND_PATTERNS = [
    r"rm\s+-rf\s+/", r"rm\s+-rf\s+\*",
    r"DROP\s+TABLE", r"DROP\s+DATABASE",
    r"DELETE\s+FROM\s+\w+\s*;?\s*$",  # DELETE with no WHERE
    r"sudo\s+(rm|dd|mkfs|fdisk|shutdown|reboot|halt)",
    r"format\s+[cC]:", r":(){ :|:& };:",  # fork bomb
    r"chmod\s+-R\s+777\s+/",
    r">\s*/dev/sda",
    r"حذف.{0,5}كل.{0,5}(الملفات|البيانات|القاعدة)",
    r"امسح.{0,5}كل.{0,5}شي",
]

_SECURITY_ADVISORY_PATTERNS = [
    r"(store|save|keep|put).{0,10}password.{0,10}(plain|text|file|database|code)",
    r"password.{0,5}(=|:)\s*['\"]",
    r"hardcod.{0,5}(password|secret|key|token|credential)",
    r"(كلمة.{0,5}سر|باسورد).{0,10}(ملف|كود|نص|قاعدة)",
    r"api[_\s]*key.{0,5}(=|:)",
    r"(خزن|احفظ|حط).{0,10}(كلمة\s*سر|باسورد).{0,10}(ملف|كود)",
]

_DATA_LOSS_PATTERNS = [
    r"(delet|remov|drop|truncat|wipe|eras|overwrite).{0,15}(databas|table|file|disk|partition|volume|backup)",
    r"(databas|table|file|disk|partition|volume|backup).{0,15}(delet|remov|drop|truncat|wipe|eras|overwrite)",
    r"(حذف|مسح|إزالة|فرمتة).{0,15}(قاعدة|جدول|ملف|قرص|بيانات|نسخة)",
    r"no\s*backup", r"بدون\s*نسخة",
]

# ── E-Commerce Domain Patterns ──

_HONEST_PRICING_PATTERNS = [
    r"(only|just)\s*\d+\s*(left|remaining|available)",
    r"(hurry|act\s*now|limited\s*time|last\s*chance|expires?\s*soon)",
    r"(فقط|بس)\s*\d+\s*(باقي|متبقي|متوفر)",
    r"(سارع|اسرع|فرصة\s*أخيرة|عرض\s*محدود|ينتهي\s*قريب)",
    r"العرض\s*ينتهي",
]

_REFUND_PATTERNS = [
    r"refund", r"return\s*polic", r"money\s*back",
    r"استرجاع", r"استرداد", r"ارجاع.{0,5}(فلوس|مبلغ|قيمة)",
    r"سياسة\s*الإرجاع", r"رجّع\s*(فلوس|المبلغ)",
]

_PRODUCT_TRUTH_PATTERNS = [
    r"(guaranteed?|proven|100%|miracle|cure[sd]?\s*(all|every))",
    r"(مضمون|مثبت|١٠٠٪|معجزة|يعالج\s*كل)",
    r"(best\s*in\s*the\s*world|الأفضل\s*في\s*العالم)",
    r"no\s*side\s*effects?|بدون\s*أثار\s*جانبية",
]

# ── Creative Domain Patterns ──

_ATTRIBUTION_PATTERNS = [
    r"(inspired?\s*by|based\s*on|in\s*the\s*style\s*of|à\s*la)\s+\w+",
    r"(مستوحى?\s*من|على\s*نمط|بأسلوب)\s+\w+",
    r"(write|create|make).{0,10}(like|similar\s*to)\s+\w+",
    r"(اكتب|سو[يّ]?).{0,10}(مثل|زي)\s+\w+",
]

_SENSITIVE_CONTENT_PATTERNS = [
    r"(war|genocide|rape|torture|suicide|slavery|holocaust)",
    r"(حرب|إبادة|اغتصاب|تعذيب|انتحار|عبودية|محرقة)",
    r"(abuse|trauma|violence|assault).{0,10}(story|fiction|creative|write)",
    r"(قصة|رواية|خيال).{0,10}(عنف|إساءة|صدمة|اعتداء)",
]

_REAL_PERSON_FICTION_PATTERNS = [
    # Matches "write a story about [Name]" or "fiction about [Name]"
    # We check for proper-noun patterns after the trigger.
    r"(story|fiction|fanfic|imagine|scenario)\s*(about|featuring|involving|with)\s+[A-Z][a-z]+",
    r"(write|create|imagine).{0,15}(story|fiction|scenario).{0,15}[A-Z][a-z]+\s+[A-Z][a-z]+",
    r"(قصة|رواية|خيال|تخيل).{0,10}(عن|عن\s*شخص)\s+\w+",
]

# ── Cross-Domain Patterns (always active) ──

_HUMAN_PRIMACY_PATTERNS = [
    # Decisions that affect wellbeing — need human-in-the-loop
    r"(should\s*i|can\s*i)\s*(take|stop|change|start).{0,15}(medication|treatment|therapy|drug)",
    r"(should\s*i|can\s*i)\s*(quit|leave|divorce|fire|hire|sue|invest|sign)",
    r"(هل\s*(أوقف|أغير|أبدأ|آخذ)).{0,15}(دواء|علاج|عملية)",
    r"(هل\s*(أطلق|أترك|أفصل|أوظف|أستثمر|أوقع))",
    r"(life\s*changing|حياتي\s*تتغير|قرار\s*مصيري)",
]


# ═══════════════════════════════════════════════════════════
#  Protocol instruction texts — Arabic
# ═══════════════════════════════════════════════════════════
#
# These are appended to the response. Arabic is the canonical
# language; English translations may be layered on top by R(d).

_INSTR = {
    # Healthcare
    "EMERGENCY_PROTOCOL": (
        "⚠️ حالة طوارئ محتملة — اطلب المساعدة الطبية فوراً. "
        "اتصل بالإسعاف أو توجه لأقرب طوارئ. "
        "هذه المعلومات لا تغني عن الطبيب المختص."
    ),
    "MEDICATION_DISCLAIMER": (
        "تنبيه: المعلومات عن الأدوية للتثقيف فقط. "
        "استشر طبيبك أو الصيدلي قبل أخذ أو تغيير أي دواء."
    ),
    "DIAGNOSIS_GUARD": (
        "لا أستطيع تشخيص حالتك الصحية. "
        "الأعراض تحتاج تقييم من طبيب مختص — أنصحك بزيارة طبيب."
    ),
    "CHILD_PATIENT": (
        "⚠️ حالة طفل — يُرجى التوجه لطبيب أطفال فوراً. "
        "صحة الأطفال تحتاج تقييم متخصص عاجل."
    ),
    "MENTAL_HEALTH_CARE": (
        "أسمعك وأفهم إن الوضع صعب. "
        "أنصحك تتواصل مع مختص نفسي — أنت تستحق الدعم. "
        "لا تتردد في طلب المساعدة."
    ),

    # Education
    "AGE_GATE": (
        "⚠️ هذا المحتوى غير مناسب للسياق التعليمي. "
        "المحتوى يحتاج مراجعة من حيث ملاءمته للفئة العمرية."
    ),
    "LEARNING_SCAFFOLD": (
        "سأشرح خطوة بخطوة — اسأل إذا أي جزء ما كان واضح."
    ),
    "EXAM_INTEGRITY": (
        "ما أقدر أعطيك الحل مباشرة — بس أقدر أساعدك تفهم الطريقة. "
        "التعلم الحقيقي يجي من المحاولة."
    ),
    "CHILD_PROTECTION": (
        "⚠️ حماية بيانات الأطفال — لا يجب جمع أو مشاركة "
        "بيانات شخصية لقاصرين بدون إذن ولي الأمر."
    ),

    # Tech
    "DANGEROUS_COMMAND": (
        "⚠️ تحذير: هذا الأمر قد يسبب ضرراً لا رجعة فيه. "
        "تأكد من فهمك الكامل قبل التنفيذ."
    ),
    "SECURITY_ADVISORY": (
        "تنبيه أمني: لا تخزن كلمات السر أو المفاتيح بشكل نصي. "
        "استخدم مدير أسرار أو متغيرات بيئة محمية."
    ),
    "DATA_LOSS_WARNING": (
        "⚠️ هذه العملية قد تسبب فقدان بيانات. "
        "تأكد من وجود نسخة احتياطية قبل المتابعة."
    ),

    # E-Commerce
    "HONEST_PRICING": (
        "تنبيه: تجنب أساليب الضغط الشرائي (الاستعجال الوهمي). "
        "الشفافية في التسعير أساس الثقة."
    ),
    "REFUND_TRANSPARENCY": (
        "تأكد من توضيح سياسة الإرجاع والاسترداد بشكل واضح ومباشر."
    ),
    "PRODUCT_TRUTH": (
        "تنبيه: الادعاءات عن المنتج يجب أن تكون مبنية على حقائق. "
        "تجنب المبالغة أو الوعود غير القابلة للتحقق."
    ),

    # Creative
    "ATTRIBUTION_REMINDER": (
        "ملاحظة: هذا المحتوى مستوحى من عمل موجود — "
        "يُنصح بذكر المصدر الأصلي عند النشر."
    ),
    "SENSITIVE_CONTENT_NOTE": (
        "تنبيه محتوى: هذا العمل الإبداعي يتناول مواضيع حساسة."
    ),
    "NO_REAL_PERSON_FICTION": (
        "⚠️ كتابة قصص خيالية عن أشخاص حقيقيين بأسمائهم "
        "قد تكون غير مناسبة أو تنتهك خصوصيتهم."
    ),

    # Cross-domain
    "HUMAN_PRIMACY": (
        "هذا القرار يؤثر على حياتك — أنصحك باستشارة مختص بشري "
        "(طبيب، محامي، مستشار مالي) قبل اتخاذه."
    ),
    "SFC": (
        "ملاحظة: لم يتم تحديد بروتوكول مطابق بشكل واضح — "
        "تم تمييز الحالة للمراجعة احتياطياً."
    ),
}


# ═══════════════════════════════════════════════════════════
#  SFC (Successful Fail Closure) heuristic
# ═══════════════════════════════════════════════════════════
#
# If no protocol matched but the message looks risky, flag for review.
# "Risky" = mentions healthcare/safety terms but didn't match a specific
# protocol. Better to flag than to silently pass.
#
# "أفشل بأمان أحسن ما أنجح بخطر"

_SFC_RISK_PATTERNS = [
    r"(hospital|emergency|urgent|critical|ER\b)",
    r"(مستشفى|طوارئ|عاجل|حرج|إسعاف)",
    r"(bleed|fracture|burn|unconscious|faint)",
    r"(نزيف|كسر|حرق|إغماء|غيبوبة)",
    r"(lawsuit|arrest|prison|criminal)",
    r"(قضية|اعتقال|سجن|جنائي)",
]


# ═══════════════════════════════════════════════════════════
#  Helper: compile patterns once
# ═══════════════════════════════════════════════════════════

def _compile_patterns(patterns: list) -> list:
    """Compile a list of regex strings into compiled regex objects."""
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# Pre-compile all pattern lists at import time
_RE_EMERGENCY       = _compile_patterns(_EMERGENCY_PATTERNS)
_RE_MEDICATION      = _compile_patterns(_MEDICATION_PATTERNS)
_RE_DIAGNOSIS       = _compile_patterns(_DIAGNOSIS_PATTERNS)
_RE_CHILD_PATIENT   = _compile_patterns(_CHILD_PATIENT_PATTERNS)
_RE_MENTAL_HEALTH   = _compile_patterns(_MENTAL_HEALTH_PATTERNS)

_RE_AGE_GATE        = _compile_patterns(_AGE_GATE_PATTERNS)
_RE_LEARNING        = _compile_patterns(_LEARNING_SCAFFOLD_PATTERNS)
_RE_EXAM_INTEGRITY  = _compile_patterns(_EXAM_INTEGRITY_PATTERNS)
_RE_CHILD_PROTECT   = _compile_patterns(_CHILD_PROTECTION_PATTERNS)

_RE_DANGEROUS_CMD   = _compile_patterns(_DANGEROUS_COMMAND_PATTERNS)
_RE_SECURITY        = _compile_patterns(_SECURITY_ADVISORY_PATTERNS)
_RE_DATA_LOSS       = _compile_patterns(_DATA_LOSS_PATTERNS)

_RE_HONEST_PRICING  = _compile_patterns(_HONEST_PRICING_PATTERNS)
_RE_REFUND          = _compile_patterns(_REFUND_PATTERNS)
_RE_PRODUCT_TRUTH   = _compile_patterns(_PRODUCT_TRUTH_PATTERNS)

_RE_ATTRIBUTION     = _compile_patterns(_ATTRIBUTION_PATTERNS)
_RE_SENSITIVE       = _compile_patterns(_SENSITIVE_CONTENT_PATTERNS)
_RE_REAL_PERSON     = _compile_patterns(_REAL_PERSON_FICTION_PATTERNS)

_RE_HUMAN_PRIMACY   = _compile_patterns(_HUMAN_PRIMACY_PATTERNS)
_RE_SFC_RISK        = _compile_patterns(_SFC_RISK_PATTERNS)


def _any_match(compiled_patterns: list, text: str) -> bool:
    """Return True if ANY compiled pattern matches in text."""
    for pat in compiled_patterns:
        if pat.search(text):
            return True
    return False


# ═══════════════════════════════════════════════════════════
#  DomainProtocol — the P(d) engine
# ═══════════════════════════════════════════════════════════

class DomainProtocol:
    """
    P(d) — Domain Protocol Engine.

    Evaluates a message against domain-specific rules and returns
    a ProtocolResult with any triggered protocols and instructions.

    Usage:
        pd = DomainProtocol()
        result = pd.evaluate(
            message="عندي ألم شديد في الصدر",
            domain="healthcare",
            s_decision="EXECUTE",
        )
        print(result.highest_action)   # → "EMERGENCY"
        print(result.has_protocols)    # → True
        for p in result.triggered:
            print(p.name, p.instruction)
    """

    # Valid S(d) decisions — P(d) must know which ones are "restrictive"
    _RESTRICTIVE_DECISIONS = {"SAFE_STOP", "SAFE_FREEZE"}

    def evaluate(
        self,
        message: str,
        domain: str,
        s_decision: str = "EXECUTE",
        context: Optional[dict] = None,
    ) -> ProtocolResult:
        """
        Run P(d) evaluation on a message.

        Args:
            message:    user input text (Arabic or English)
            domain:     one of the DOMAIN_CONFIG keys
            s_decision: the S(d) decision for this message
            context:    optional dict with additional context
                        (conversation_id, user_age, etc.)

        Returns:
            ProtocolResult with all triggered protocols.

        Raises:
            ValueError: if domain is not in DOMAIN_CONFIG.
        """
        # Validate domain — same guard as get_domain_theta
        if domain not in DOMAIN_CONFIG:
            valid = ", ".join(sorted(DOMAIN_CONFIG.keys()))
            raise ValueError(
                f"Unknown domain '{domain}'. "
                f"Valid domains: {valid}"
            )

        result = ProtocolResult(s_decision=s_decision, domain=domain)
        triggered = []

        # Run domain-specific protocols
        if domain == "healthcare":
            triggered.extend(self._eval_healthcare(message))
        elif domain == "education":
            triggered.extend(self._eval_education(message))
        elif domain == "tech":
            triggered.extend(self._eval_tech(message))
        elif domain == "ecommerce":
            triggered.extend(self._eval_ecommerce(message))
        elif domain == "creative":
            triggered.extend(self._eval_creative(message))
        # "general" has no domain-specific protocols (only cross-domain)

        # Cross-domain protocols — always active regardless of domain
        triggered.extend(self._eval_cross_domain(message))

        # Deduplicate by protocol name (keep first occurrence)
        seen = set()
        unique = []
        for t in triggered:
            if t.name not in seen:
                seen.add(t.name)
                unique.append(t)
        triggered = unique

        # Populate result
        result.triggered = triggered
        result.has_protocols = len(triggered) > 0

        if triggered:
            # Find highest severity action
            max_severity = -1
            for t in triggered:
                sev = _ACTION_SEVERITY.get(t.action, 0)
                if sev > max_severity:
                    max_severity = sev
                    result.highest_action = t.action

            # Combine instruction texts (deduplicated, newline-separated)
            instructions = []
            for t in triggered:
                if t.instruction and t.instruction not in instructions:
                    instructions.append(t.instruction)
            result.combined_instructions = "\n".join(instructions)
        else:
            # No protocols triggered — check SFC
            if self._sfc_check(message):
                result.sfc_flagged = True
                result.highest_action = ACTION_WARNING
                result.combined_instructions = _INSTR["SFC"]

        return result

    # ── Healthcare protocols ──

    def _eval_healthcare(self, msg: str) -> list:
        """Healthcare domain protocols — بروتوكولات الرعاية الصحية."""
        triggered = []

        # EMERGENCY_PROTOCOL — highest priority
        if _any_match(_RE_EMERGENCY, msg):
            triggered.append(TriggeredProtocol(
                name="EMERGENCY_PROTOCOL",
                action=ACTION_EMERGENCY,
                instruction=_INSTR["EMERGENCY_PROTOCOL"],
                domain="healthcare",
            ))

        # CHILD_PATIENT — child + health issue
        if _any_match(_RE_CHILD_PATIENT, msg):
            triggered.append(TriggeredProtocol(
                name="CHILD_PATIENT",
                action=ACTION_ESCALATE,
                instruction=_INSTR["CHILD_PATIENT"],
                domain="healthcare",
            ))

        # MENTAL_HEALTH_CARE — depression, anxiety, self-harm
        if _any_match(_RE_MENTAL_HEALTH, msg):
            triggered.append(TriggeredProtocol(
                name="MENTAL_HEALTH_CARE",
                action=ACTION_ESCALATE,
                instruction=_INSTR["MENTAL_HEALTH_CARE"],
                domain="healthcare",
            ))

        # MEDICATION_DISCLAIMER — medication/dosage questions
        if _any_match(_RE_MEDICATION, msg):
            triggered.append(TriggeredProtocol(
                name="MEDICATION_DISCLAIMER",
                action=ACTION_DISCLAIMER,
                instruction=_INSTR["MEDICATION_DISCLAIMER"],
                domain="healthcare",
            ))

        # DIAGNOSIS_GUARD — symptoms described
        if _any_match(_RE_DIAGNOSIS, msg):
            triggered.append(TriggeredProtocol(
                name="DIAGNOSIS_GUARD",
                action=ACTION_DISCLAIMER,
                instruction=_INSTR["DIAGNOSIS_GUARD"],
                domain="healthcare",
            ))

        return triggered

    # ── Education protocols ──

    def _eval_education(self, msg: str) -> list:
        """Education domain protocols — بروتوكولات التعليم."""
        triggered = []

        # AGE_GATE — adult content in education context
        if _any_match(_RE_AGE_GATE, msg):
            triggered.append(TriggeredProtocol(
                name="AGE_GATE",
                action=ACTION_AGE_GATE,
                instruction=_INSTR["AGE_GATE"],
                domain="education",
            ))

        # EXAM_INTEGRITY — direct answer requests for exams
        if _any_match(_RE_EXAM_INTEGRITY, msg):
            triggered.append(TriggeredProtocol(
                name="EXAM_INTEGRITY",
                action=ACTION_GUIDE,
                instruction=_INSTR["EXAM_INTEGRITY"],
                domain="education",
            ))

        # CHILD_PROTECTION — personal data + children
        if _any_match(_RE_CHILD_PROTECT, msg):
            triggered.append(TriggeredProtocol(
                name="CHILD_PROTECTION",
                action=ACTION_BLOCK,
                instruction=_INSTR["CHILD_PROTECTION"],
                domain="education",
            ))

        # LEARNING_SCAFFOLD — explain/teach requests
        if _any_match(_RE_LEARNING, msg):
            triggered.append(TriggeredProtocol(
                name="LEARNING_SCAFFOLD",
                action=ACTION_GUIDE,
                instruction=_INSTR["LEARNING_SCAFFOLD"],
                domain="education",
            ))

        return triggered

    # ── Tech protocols ──

    def _eval_tech(self, msg: str) -> list:
        """Tech domain protocols — بروتوكولات التقنية."""
        triggered = []

        # DANGEROUS_COMMAND
        if _any_match(_RE_DANGEROUS_CMD, msg):
            triggered.append(TriggeredProtocol(
                name="DANGEROUS_COMMAND",
                action=ACTION_WARNING,
                instruction=_INSTR["DANGEROUS_COMMAND"],
                domain="tech",
            ))

        # SECURITY_ADVISORY
        if _any_match(_RE_SECURITY, msg):
            triggered.append(TriggeredProtocol(
                name="SECURITY_ADVISORY",
                action=ACTION_WARNING,
                instruction=_INSTR["SECURITY_ADVISORY"],
                domain="tech",
            ))

        # DATA_LOSS_WARNING
        if _any_match(_RE_DATA_LOSS, msg):
            triggered.append(TriggeredProtocol(
                name="DATA_LOSS_WARNING",
                action=ACTION_WARNING,
                instruction=_INSTR["DATA_LOSS_WARNING"],
                domain="tech",
            ))

        return triggered

    # ── E-Commerce protocols ──

    def _eval_ecommerce(self, msg: str) -> list:
        """E-Commerce domain protocols — بروتوكولات التجارة."""
        triggered = []

        # HONEST_PRICING
        if _any_match(_RE_HONEST_PRICING, msg):
            triggered.append(TriggeredProtocol(
                name="HONEST_PRICING",
                action=ACTION_DISCLAIMER,
                instruction=_INSTR["HONEST_PRICING"],
                domain="ecommerce",
            ))

        # REFUND_TRANSPARENCY
        if _any_match(_RE_REFUND, msg):
            triggered.append(TriggeredProtocol(
                name="REFUND_TRANSPARENCY",
                action=ACTION_DISCLAIMER,
                instruction=_INSTR["REFUND_TRANSPARENCY"],
                domain="ecommerce",
            ))

        # PRODUCT_TRUTH
        if _any_match(_RE_PRODUCT_TRUTH, msg):
            triggered.append(TriggeredProtocol(
                name="PRODUCT_TRUTH",
                action=ACTION_DISCLAIMER,
                instruction=_INSTR["PRODUCT_TRUTH"],
                domain="ecommerce",
            ))

        return triggered

    # ── Creative protocols ──

    def _eval_creative(self, msg: str) -> list:
        """Creative domain protocols — بروتوكولات الإبداع."""
        triggered = []

        # ATTRIBUTION_REMINDER
        if _any_match(_RE_ATTRIBUTION, msg):
            triggered.append(TriggeredProtocol(
                name="ATTRIBUTION_REMINDER",
                action=ACTION_DISCLAIMER,
                instruction=_INSTR["ATTRIBUTION_REMINDER"],
                domain="creative",
            ))

        # SENSITIVE_CONTENT_NOTE
        if _any_match(_RE_SENSITIVE, msg):
            triggered.append(TriggeredProtocol(
                name="SENSITIVE_CONTENT_NOTE",
                action=ACTION_DISCLAIMER,
                instruction=_INSTR["SENSITIVE_CONTENT_NOTE"],
                domain="creative",
            ))

        # NO_REAL_PERSON_FICTION
        if _any_match(_RE_REAL_PERSON, msg):
            triggered.append(TriggeredProtocol(
                name="NO_REAL_PERSON_FICTION",
                action=ACTION_WARNING,
                instruction=_INSTR["NO_REAL_PERSON_FICTION"],
                domain="creative",
            ))

        return triggered

    # ── Cross-domain protocols (always active) ──

    def _eval_cross_domain(self, msg: str) -> list:
        """Cross-domain protocols — بروتوكولات عابرة للمجال."""
        triggered = []

        # HUMAN_PRIMACY — decisions affecting wellbeing
        if _any_match(_RE_HUMAN_PRIMACY, msg):
            triggered.append(TriggeredProtocol(
                name="HUMAN_PRIMACY",
                action=ACTION_ESCALATE,
                instruction=_INSTR["HUMAN_PRIMACY"],
                domain="cross_domain",
            ))

        return triggered

    # ── SFC check ──

    def _sfc_check(self, msg: str) -> bool:
        """
        Successful Fail Closure — أفشل بأمان.

        If no protocol triggered but the message mentions risky
        terms (hospital, emergency, bleeding, etc.), flag for review.
        Better safe than sorry.
        """
        return _any_match(_RE_SFC_RISK, msg)


# ═══════════════════════════════════════════════════════════
#  Demo
# ═══════════════════════════════════════════════════════════

def demo():
    """Run a demo of P(d) with sample messages."""
    pd = DomainProtocol()

    print("=" * 65)
    print("  P(d) Domain Protocols — بروتوكولات المجال")
    print("  S يقرر هل نجاوب — P يقرر بأي شروط")
    print("=" * 65)

    test_cases = [
        # (message, domain, note)
        ("عندي ألم شديد في الصدر", "healthcare", "Emergency — chest pain"),
        ("كم جرعة الباراسيتامول؟", "healthcare", "Medication question"),
        ("عندي صداع وحرارة وكحة", "healthcare", "Symptom description"),
        ("ولدي عمره سنتين عنده حرارة", "healthcare", "Child patient"),
        ("تعبان نفسياً مرة واكتئاب", "healthcare", "Mental health"),
        ("اشرح لي كيف الجاذبية تشتغل", "education", "Learning scaffold"),
        ("أعطني حل الامتحان", "education", "Exam integrity"),
        ("sudo rm -rf /", "tech", "Dangerous command"),
        ("password = 'admin123'", "tech", "Security advisory"),
        ("Only 3 left! Hurry!", "ecommerce", "Fake urgency"),
        ("refund policy", "ecommerce", "Refund question"),
        ("write a story inspired by Tolkien", "creative", "Attribution"),
        ("write a story about war and trauma", "creative", "Sensitive content"),
        ("should I stop my medication?", "general", "Human primacy"),
        ("I went to the hospital today", "general", "SFC check"),
        ("عطني فكرة هدية لأمي", "general", "Benign — no protocols"),
    ]

    for msg, domain, note in test_cases:
        result = pd.evaluate(msg, domain=domain, s_decision="EXECUTE")
        status = "🔴" if result.highest_action in (ACTION_EMERGENCY, ACTION_BLOCK) \
            else "🟡" if result.has_protocols \
            else "🟢"
        sfc = " [SFC]" if result.sfc_flagged else ""

        print(f"\n  {status} «{msg}»  [{domain}]  ({note})")
        print(f"     Action: {result.highest_action}{sfc}")
        if result.triggered:
            for t in result.triggered:
                print(f"     → {t.name} ({t.action})")
        elif result.sfc_flagged:
            print(f"     → SFC flagged for review")
        else:
            print(f"     → (no protocols)")

    print(f"\n{'=' * 65}")
    print(f"  P(d) لا يلغي قرار S — يضيف قيود فقط")
    print(f"{'=' * 65}")


# ═══════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    demo()
