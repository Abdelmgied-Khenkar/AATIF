# Field Note #061: The Non-Auto Justification Principle (GEI)

**المصدر:** `18 — Interface Layer V9.5` (18.01 — GEI — Governed Execution Interface)
**الحالة:** 🟡 Pending Architect Validation
**التاريخ:** مايو ٢٠٢٦

-----

## Slogan

> *“Justification is a button, not a habit.”*
> *التبرير زر — لا عادة.*

-----

## Problem

النظام الذي يُبرر نفسه تلقائياً مع كل إجابة يُخلق مشكلتين:
١. يُثقل المحادثة بمعلومات لم تُطلب
٢. يُشبه الدفاعية — فيُثير الشك بدل بناء الثقة

الشرح التلقائي يزيد الاعتماد الأعمى على الـ AI ويُنتج “ثقة وهمية.”

-----

## Observation

GEI-18.01 يُقرر ثلاثة modes للمخرجات:

|Mode      |متى يُستخدم                                                  |
|----------|------------------------------------------------------------|
|**ANSWER**|إجابة مباشرة بدون مصادر — الافتراضي                         |
|**PROOF** |مصادر وقوانين — عند الطلب الصريح فقط (“أثبت”، “اشرح من وين”)|
|**STOP**  |سؤال توضيحي واحد — عند غموض النية أو خطر عالٍ                |

**القانون الجوهري:**

> *“The system must not auto-explain internal references. Proof is revealed only when requested.”*

**ما يُمنع:** الانتقال بين الـ modes بدون طلب صريح، التبرير التلقائي، إظهار المصادر الداخلية بدون إذن.

-----

## From the Source / مثال

**نص حرفي:**

> *“Justification is a button, not a habit.”*
> *“The system may NOT escalate between modes without explicit user request.”*

**مثال توضيحي:**

|السؤال                  |بدون GEI                            |مع GEI      |
|------------------------|------------------------------------|------------|
|“ما رأيك في هذا القرار؟”|يُجيب ويضيف: “بناءً على القانون 15.3…”|يُجيب فقط    |
|“أثبت”                  |—                                   |يُظهر المصادر|

-----

## Hypothesis

**علمياً مدعوم:**

- Miller (2019): الشرح فعل تحاوري يبدأ من السائل — مو من النظام
  *DOI: 10.1016/j.artint.2018.07.007*
- Buçinca et al. (CHI/IUI): الشرح التلقائي يزيد الاعتماد الأعمى وAutomation Bias
- Ehsan & Riedl, “Explainability Pitfalls” (arXiv:2109.12480): التفسيرات الافتراضية تُنتج ثقة وهمية
- arXiv:2404.19629 (2024): لبعض المستخدمين الـ XAI ما يعطيها بـ default

**الفجوة:** المبدأ مو موجود كاسم صريح في الأبحاث — الأدلة موجودة لكن لم تُصَغ كـ قانون تشغيلي مُسمّى.

**الإضافة في AATIF:** تحويل هذا الاتجاه البحثي إلى قانون تشغيلي صريح بثلاثة modes. “الصمت عن التبرير هو القاعدة، الإثبات استثناء بطلب.”

-----

## Open Questions

١. كيف يُقرر النظام الفرق بين “STOP لغموض” و”ANSWER مع تفاصيل إضافية”؟
٢. هل يختلف المبدأ حسب السياق — مثلاً في طوارئ أو قرارات عالية الخطورة؟
٣. ما العلاقة بين هذا المبدأ و#043 (Uncertainty Disclosure Law)؟

-----

## Slogan (Final)

> **The Non-Auto Justification Principle: justification is a button, not a habit.**

*Architect: Abdulmjeed Ibrahim | Co-documenter: Claude (Anthropic)*
