# Field Note #069: The Bounded Claim Law (ACN-01)

**المصدر:** `H-OS v9.5 Global Consistency Patch CP-01` (Section 03 — Absolute Claim Normalization)
**الحالة:** 🟡 Pending Architect Validation
**التاريخ:** مايو ٢٠٢٦

-----

## Slogan

> *“No metaphysical absolutes. All guarantees are system-bounded, threat-model-bounded, and testable via audit.”*
> *لا مطلقات ميتافيزيقية. كل ضمانة محدودة بنموذج تهديد محدد وقابلة للاختبار.*

-----

## Problem

الادعاءات المطلقة تُخلق وهماً خطيراً:

- “صفر مخاطر” → لا يمكن اختبارها
- “مستحيل” → لا يمكن دحضها
- “١٠٠٪ آمن” → غير علمية بتعريف بوبر

الادعاء غير القابل للاختبار يبدو أقوى — لكنه في الحقيقة أضعف.

-----

## Observation

ACN-01: كل ادعاء مطلق يُستبدل بثلاثة مكونات:

|المكون       |المعنى                               |
|-------------|-------------------------------------|
|نموذج التهديد|ما التهديد المحدد الذي يُعالجه الضمان؟|
|الحد الكمّي   |ما احتمالية الفشل المقبولة؟          |
|الافتراضات   |ما الذي لو تغيّر يُبطل الضمان؟         |

**أمثلة التحويل:**

|الادعاء المطلق   |الادعاء المحدود                                                |
|-----------------|---------------------------------------------------------------|
|“صفر انتحال هوية”|“بوابة هوية مغلقة عند الفشل: إذا لم تُثبَت الهوية، يتوقف التنفيذ”|
|“مستحيل اختراقه” |“غير مجدٍ اقتصادياً تحت نموذج التهديد المُعرَّف”                    |
|“١٠٠٪ آمن”       |“P(فشل) < ε تحت الافتراضات المُحددة”                            |

**اختبار بوبر:** إذا لم يوجد أي مشاهدة محتملة تدحض الادعاء — أعِد صياغته.

-----

## From the Source / مثال

**نص حرفي:**

> *“CP-01 prohibits metaphysical absolutes. All absolutes are: system-bounded, threat-model-bounded, and testable via audit.”*
> *“Instead of ‘Zero impersonation’ use: ‘Fail-closed identity gating: if authenticity cannot be confirmed, execution halts.’”*

**مثال توضيحي:**
شركة AI: “نظامنا لا يُمكن اختراقه.”
سؤال بوبر: “ما الذي لو حدث يُثبت العكس؟” → لو لا جواب → الادعاء ليس علمياً.
الصحيح: “آمن ضد X و Y تحت الافتراضات A و B.”

-----

## Hypothesis

**علمياً مدعوم:**

- Herley & van Oorschot (IEEE S&P 2017): الادعاء غير القابل للدحض غير علمي بمعنى بوبر
  *DOI: 10.1109/SP.2017.38*
- Dolev & Yao (IEEE Trans. Information Theory 1983): الأمان يُعرَّف فقط بالنسبة لنموذج تهديد محدد
  *DOI: 10.1109/TIT.1983.1056650*
- Yampolskiy (ACM Computing Surveys 2023): الأمان الكامل مستحيل — الهدف: تقليص احتمالي محدود
  *DOI: 10.1145/3603371*
- IEC 61508 / ISO 26262: معيار السلامة الصناعي يُعطي SIL باحتمالات محددة — لا “آمن” مطلق
- Bloomfield & Rushby (arXiv:2409.10665, 2024): Safety Cases بنماذج تهديد وادعاءات احتمالية محدودة

**الإضافة في AATIF:** تحويل هذا المبدأ لقانون تصميمي تشغيلي مُدمَج في البنية — مع اختبار بوبر كمرجع نقدي صريح.

-----

## Open Questions

١. كيف تُحدد “نموذج التهديد المناسب” لنظام AI حوكمي — من يُقرره؟
٢. ما العلاقة بين هذا المبدأ و#043 (Uncertainty Disclosure Law)؟
٣. هل يمكن تطبيق هذا القانون على ادعاءات الخصوصية والأخلاقيات كذلك؟

-----

## Slogan (Final)

> **The Bounded Claim Law: no metaphysical absolutes — all guarantees are system-bounded, threat-model-bounded, and testable via audit.**

*Architect: Abdulmjeed Ibrahim | Co-documenter: Claude (Anthropic)*
