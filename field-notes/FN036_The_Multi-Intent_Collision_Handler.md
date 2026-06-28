# Field Note #036: The Multi-Intent Collision Handler

**المصدر:** `05 — Meta Layer V9.5` (MT-3.12 — Multi-Intent Collision Handler)
**الحالة:** 🟡 Pending Architect Validation
**التاريخ:** مايو ٢٠٢٦

-----

## Slogan

> *“When one message carries two intentions, the system does not guess which to serve.”*
> *لما رسالة واحدة تحمل نيتين، النظام لا يخمّن أيهما يخدم.*

-----

## Note on Relationship to #024

**#024 (Five-Layer Intent Model)** يصف طبقات النية داخل طلب واضح الاتجاه.
**#036 (Multi-Intent Collision)** يصف ما يحدث لو طلب واحد يحتوي نيتين متعارضتين — قبل أي معالجة.

-----

## Problem

الطلبات الإنسانية كثيراً ما تحمل نيتين متعارضتين في نفس الجملة. مثال: *“اكتب لي تقرير مختصر وشامل.”* — “مختصر” و”شامل” متعارضان. الـ LLM العادي إما يختار واحدة عشوائياً أو يدمجهما بشكل مُشوَّه.

-----

## Observation

MT-3.12 يُصنّف التعارضات في خمس فئات:

|الفئة                        |التعريف                             |
|-----------------------------|------------------------------------|
|Parallel Intent Collision    |نيتان مستقلتان في نفس الطلب         |
|Hierarchical Intent Collision|نية داخل نية — أيهما أولى؟          |
|Cross-Layer Intent Collision |نية تتعارض مع طبقة أخرى في النظام   |
|Structural-Semantic Mismatch |الشكل يقول شيئاً والمعنى يقول آخر    |
|High-Risk Collision          |تعارض يحتاج تدخل الـ Supervisor فوراً|

بعد التصنيف، قرار واحد من اثنين:

- **Safe-Split:** ينفّذهما منفصلَين بالترتيب
- **Safe-Merge:** يدمجهما لو التوافق كافٍ (≥ 0.85)

-----

## Hypothesis

**علمياً مُثبَّت:** intent disambiguation موجود في أبحاث الـ NLP وtask decomposition. التعارض بين نيتين في نفس الطلب مشكلة موثّقة في conversational AI research.

**الإضافة في AATIF:** التصنيف الخماسي والمسارين (Safe-Split / Safe-Merge) — إطار تشغيلي منظّم لحل المشكلة. منطق علمي قابل للتطبيق.

-----

## Mechanism

لا دمج تلقائي إلا لو التوافق ≥ 0.85.
عند التعارض الخطير: يُوقف فوراً → يُرسل للـ Supervisor.
للجهة المسؤولة: التعارض في طلباتهم يُعامَل دائماً كمقصود.

-----

## Open Questions

١. كيف يُحدَّد عتبة التوافق (0.85) في الواقع؟ هل هي ثابتة أم تتكيّف مع السياق؟
٢. هل يمكن بناء benchmark يقيس دقة تصنيف التعارض في اللغة العربية؟
٣. ما العلاقة بين هذا ومفهوم “conflicting goals” في نظريات الـ multi-agent systems؟

-----

## Slogan (Final)

> **The Multi-Intent Collision Handler: when one message carries two intentions, the system does not guess which to serve.**

*Architect: Abdulmjeed Ibrahim | Co-documenter: Claude (Anthropic)*
