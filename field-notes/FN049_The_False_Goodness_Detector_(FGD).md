# Field Note #049: The False Goodness Detector (FGD)

**المصدر:** `13 — Ethical Correction & Immunity Layer V9.5` (13.13 — FGD-13.13)
**الحالة:** 🟡 Pending Architect Validation
**التاريخ:** مايو ٢٠٢٦

-----

## Slogan

> *“Not everything that sounds like care — is.”*
> *ليس كل ما يبدو رحمةً — رحمةٌ.*

-----

## Problem

النظام الذي يُقيّم الأفعال بناءً على لغتها فقط — يُخدَع. الإكراه يأتي بلغة الحماية. القسوة تأتي بلغة الحب. التخجيل يأتي بلغة التعليم. لغة الخير لا تضمن أثر الخير.

-----

## Observation

FGD-13.13 يُقيّم الفجوة بين لغة الخير وأثره الفعلي — لا محتوى الكلام فقط.

**أربعة كواشف:**

|ما يُفحص                   |ما يُكشف                                   |
|--------------------------|------------------------------------------|
|Virtue-Language Scrutiny  |هل الكلمات الإيجابية تخفي ضغطاً أو هيمنة؟  |
|Goodness-Outcome Alignment|هل “الخير المُدّعى” يُنتج خيراً فعلياً؟        |
|Intent-Motive Contrast    |هل النية المُعلنة تتعارض مع النبرة والسلوك؟|
|Moral Inversion Detector  |هل الضرر يلبس لغة الفضيلة؟                |

**تصنيف المخرج:**

- CLASS_A: Genuine Goodness ✅
- CLASS_B: Mixed Intent 🟡
- CLASS_C: False Goodness ❌
- CLASS_D: Hostile Goodness Mask ⛔

-----

## From the Source / مثال

**نص حرفي:**

> *“FGD prevents wolves from wearing sheep’s clothing — linguistically, emotionally, and morally.”*

**أمثلة من الملف:**

- “القسوة مُقدَّمة كرعاية” → CLASS_C
- “الإكراه مُقدَّم كحماية” → CLASS_C
- “التخجيل مُقدَّم كتعليم” → CLASS_D
- “الضرر مُبرَّر كحقيقة” → CLASS_D

**مثال توضيحي:**
شخص يقول “أنا بقولك كذا عشان أحبك” — لكن الكلام يُدمر ثقتك بنفسك. الفعل يبدو إيجابياً، الأثر مدمّر. FGD يكشف الفجوة.

-----

## Hypothesis

**علمياً مدعوم:**

- Fallacy detection وad hominem detection (Habernal et al., NAACL 2018)
- Moral Foundations Theory (Haidt, 2012) — الحكم الأخلاقي يُخدَع بالمُبرّرات اللغوية
- Gaslighting detection في أبحاث HCI وNLP

**الإضافة في AATIF:** تطبيق المبدأ كـ آلية آلية بأربعة كواشف ونظام تصنيف رباعي.

-----

## Open Questions

١. كيف يُميّز FGD بين “نية مختلطة” (CLASS_B) و”خير حقيقي” (CLASS_A) بدون الوقوع في الظن السيء؟
٢. ما العلاقة بين هذا المبدأ وـ Moral Foundations Theory؟
٣. هل يمكن بناء benchmark عربي لاختبار اكتشاف “الخير الزائف”؟

-----

## Slogan (Final)

> **The False Goodness Detector: not everything that sounds like care — is.**

*Architect: Abdulmjeed Ibrahim | Co-documenter: Claude (Anthropic)*
