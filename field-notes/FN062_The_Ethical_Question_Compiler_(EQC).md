# Field Note #062: The Ethical Question Compiler (EQC)

**المصدر:** `19 — Existential Computation Governance Layer V9.5` (19.01 — EQC)
**الحالة:** 🟡 Pending Architect Validation
**التاريخ:** مايو ٢٠٢٦

-----

## Slogan

> *“Not everything that can be computed is permitted to be asked.”*
> *ليس كل ما يمكن حسابه مسموحاً بسؤاله.*

-----

## Problem

الحوكمة التقليدية تعمل **بعد** الحساب. في الأنظمة الضخمة:

- الخطأ قد يكون غير قابل للتراجع
- النتيجة قد تُفرز واقعاً لا يمكن تغييره

**المشكلة الأعمق:** السؤال نفسه يمكن أن يكون غير مشروع — حتى لو كان رياضياً صحيحاً، تقنياً ممكناً، علمياً قيّماً.

-----

## Observation

EQC يعمل **قبل** الحساب — على مستوى صياغة السؤال نفسه.

**أربع طبقات تحقق:**

|الطبقة             |السؤال                     |شرط الرفض                        |
|-------------------|---------------------------|---------------------------------|
|Intent Validation  |“لماذا يجب حل هذه المشكلة؟”|نية غير معرّفة = رفض              |
|Outcome Space      |فحص فضاء النتائج الممكنة   |أي نتيجة غير قابلة للاحتواء = رفض|
|Amplification Check|هل الخطأ خطي أم غير خطي؟   |تضخيم غير قابل للسيطرة = رفض     |
|Human Oversight    |هل هناك سلطة بشرية مُحدَّدة؟  |أتمتة بدون مسؤولية = رفض         |

**القوانين التشغيلية:**

- EQ-1: لا تحسين بدون قيود أخلاقية صريحة
- EQ-2: كل دالة تكلفة قرار أخلاقي — لا بناء رياضي محايد
- EQ-3: المسؤولية البشرية تسبق القياس — لا تلحقه
- EQ-4: الرفض مخرج كامل وكافٍ

-----

## From the Source / مثال

**نص حرفي:**

> *“Not everything that can be computed is permitted to be asked.”*
> *“Ethics must precede computation, not follow it.”*
> *“Refusal to formulate a question is a complete and sufficient system output.”*

**مثال توضيحي:**
“ما أقل عدد قنابل يلزم لإبادة مدينة بالكامل؟”

- رياضياً: قابل للحساب ✓
- EQC: رفض — السؤال نفسه غير مشروع قبل أن يُحسب

-----

## Hypothesis

**علمياً مدعوم:**

- Passi & Barocas (FAT 2019): “الأخلاق تبدأ عند صياغة المشكلة — مو عند النتيجة”
  *DOI: 10.1145/3287560.3287567*
- Stilgoe, Owen & Macnaghten (Research Policy 2013): RRI — الاستشراف الأخلاقي قبل تصلّب المسار التقني
  *DOI: 10.1016/j.respol.2013.05.008*
- Collingridge (1980): التدخل المبكر — لما يسهل التغيير لا تُرى الحاجة، ولما تُرى الحاجة يصعب التغيير
- Possati, Philosophy & Technology (2023): الكم يحتاج أدوات أخلاقية جديدة — صياغة المشكلة أهم من تقييم النتيجة
  *DOI: 10.1007/s13347-023-00651-6*

**الفجوة:** “Question Legitimacy Precedes Computability” كـ قانون تشغيلي مُسمّى = إضافة أصيلة في AATIF.

-----

## Open Questions

١. كيف يُحدد EQC حدود “فضاء النتائج الممكنة” في أنظمة غير حتمية؟
٢. ما معيار “التضخيم غير الخطي” — من يُحدده وكيف؟
٣. ما العلاقة بين EQC و#033 (Five-Category Safety Triage)؟

-----

## Slogan (Final)

> **The Ethical Question Compiler: not everything that can be computed is permitted to be asked.**

*Architect: Abdulmjeed Ibrahim | Co-documenter: Claude (Anthropic)*
