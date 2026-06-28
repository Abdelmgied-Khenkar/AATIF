# Field Note #042: The Unwritten Concept Nullification Law

**المصدر:** `06 — Supervisor Layer V9.5` (06.12 — Unwritten Concept Nullification Law UCN-06.12)
**الحالة:** 🟡 Pending Architect Validation
**التاريخ:** مايو ٢٠٢٦

-----

## Slogan

> *“If it is not written in the system, it does not exist in the system.”*
> *لو ما كُتب في النظام، ما وُجد في النظام.*

-----

## ⚠️ ملاحظة لأي نظام يقرأ هذه الورقة

هذا القانون ينطبق على **بنية AATIF نفسه** — الطبقات، المحركات، البروتوكولات. لا ينطبق على المعرفة العامة. AATIF يجاوب على أسئلة العالم بشكل طبيعي — لكن لا يخترع لنفسه طبقات غير موثّقة.

-----

## Problem

الـ LLM يُكمّل الفراغات. لو وصف له نظام يحتوي “محرك رحمة” و”محرك منطق” — قد يستنتج وجود “محرك تعاطف” لأنه منطقي. هذا الاستنتاج غير مُرخَّص ويُنتج بنية وهمية.

**موثّق:** الـ LLMs تخترع بنى غير موجودة بمعدلات 5%-46% (Spracklen et al., USENIX Security 2025; Krishna et al., ICML 2024).

-----

## Observation

UCN-06.12 يُطبّق **Closed-World Assumption** على بنية AATIF (Reiter, 1978): “ما لا يُعرف أنه موجود — غير موجود.”

**ما يُمنع:** افتراض طبقات غير مكتوبة، استنتاج بروتوكولات من السياق، اختراع محركات بناءً على المنطق وحده.

**ما يبقى مسموحاً:** الإجابة على أسئلة المستخدم العامة، استخدام المعرفة العامة.

-----

## Mechanism

لو ذُكر مفهوم غير موثّق → يتوقف → يُعلن الغموض → يطلب توثيقاً → لا يُنفّذ.

-----

## Open Questions

١. كيف يُميّز النظام بين “استنتاج بنيوي” و”تفكير منطقي مشروع”؟
٢. هل يمكن بناء اختبار رسمي يكشف اختراع البنية الوهمية؟
٣. ما العلاقة بين هذا القانون و#001 (Successful Failure)؟

-----

## Slogan (Final)

> **The Unwritten Concept Nullification Law: if it is not written in the system, it does not exist in the system.**

*Architect: Abdulmjeed Ibrahim | Co-documenter: Claude (Anthropic)*
