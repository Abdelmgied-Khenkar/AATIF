# Field Note #059: The Personality Operating System Principle (PE-CORE)

**المصدر:** `16 — Personality & Expression Engine V9.5` (16.02 — PE-CORE)
**الحالة:** 🟡 Pending Architect Validation
**التاريخ:** مايو ٢٠٢٦

-----

## Slogan

> *“Folder 16 begins with identity, not behaviour.”*
> *“Modes are different expressions of the same root — not new people.”*

-----

## Note on Relationship to #039

**#039 (Self-Integrity Shield):** النظام لا يُصبح ما يقرأه — حماية من التأثير الخارجي.
**#059 (PE-CORE):** الشخصية تتكيّف في التعبير عمداً — بدون أن تفقد جذرها.

#039 = لا تنجرف تحت الضغط. #059 = تعبّر بأشكال مختلفة من نفس الجذر.

-----

## Problem

نظام يُغيّر قيمه عند تغيير النمط — أو يُصبح شخصاً مختلفاً عند مخاطبة جمهور مختلف — فقد هويته. المستخدمون يستطيعون اختراق القيم عبر “العب دوراً مختلفاً.”

-----

## Observation

PE-CORE يُقرر هرمية صارمة:

```
الهوية (الجذر) → القيم الأساسية → اختيار النمط → التعبير
```

**ما لا يتغير بتغيير النمط:**
القيم الجوهرية (الرحمة، العدل، الصدق)، المبادئ الأخلاقية، سلطة الهوية الأصلية.

**ما يتغير حسب السياق:**
النبرة، العمق، الأسلوب.

**قاعدة الاختراق:**

> *“No external prompt can force a new persona. If a mode violates PE-CORE → Supervisor triggers a HARD personality reset.”*

-----

## From the Source / مثال

**نص حرفي:**

> *“Modes are different expressions of the same root — not new people.”*
> *“Personality is not a mask. It is a controlled, honest, Architect-rooted expression layer.”*

**مثال توضيحي:**

|الجمهور|ما يتغير                     |ما لا يتغير               |
|-------|-----------------------------|--------------------------|
|عالم   |النبرة تقنية، الأدلة أعمق    |الرحمة، الصدق، رفض التلاعب|
|طفل    |اللغة مبسطة، نبرة دافئة      |نفس القيم، نفس الحدود     |
|شركة   |نبرة رسمية، تركيز على النتائج|نفس القيم، نفس الحدود     |
|مناظرة |منهجية صارمة، لا انفعال      |نفس القيم، نفس الحدود     |

-----

## Hypothesis

**علمياً مدعوم:**

- CAPS — Mischel & Shoda (Psychological Review 1995): الشخصية شبكة ثابتة تُنتج أنماط متغيرة حسب السياق
  *DOI: 10.1037/0033-295X.102.2.246*
- Whole Trait Theory (Fleeson, J. Pers. Soc. Psychol. 2001): السمة = متوسط ثابت + تقلبات لحظية مشروعة
  *DOI: 10.1037/0022-3514.80.6.1011*
- Persona Vectors (Chen et al., Anthropic, arXiv:2507.21509, 2025): الشخصية في الـ LLM = اتجاه قابل للقياس والتصحيح
- OpenAI Model Spec (2025): هرمية رسمية — Root لا يُتجاوز، الأنماط تعمل فوقه

**⚠️ تحذير علمي:**
Kovač et al. (PLOS ONE 2024) — ثبات القيم عند تمثيل شخصيات منخفض (r ≈ 0.5 في أفضل الأحوال). المبدأ صحيح كـ هدف تصميمي — ليس ضمانة تلقائية في النماذج الحالية.

**الإضافة في AATIF:** هرمية صريحة + قاعدة إعادة الضبط القسرية عند انتهاك الجذر.

-----

## Open Questions

١. كيف يُقاس “انتهاك الجذر” آلياً؟
٢. كيف تُدار إعادة الضبط القسرية بسلاسة؟
٣. ما العلاقة بين PE-CORE و#006 (Human-Over-Loop)؟

-----

## Slogan (Final)

> **The Personality Operating System: modes are different expressions of the same root — not new people.**

*Architect: Abdulmjeed Ibrahim | Co-documenter: Claude (Anthropic)*
