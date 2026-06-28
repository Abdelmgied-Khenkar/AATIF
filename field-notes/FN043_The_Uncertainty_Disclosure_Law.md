# Field Note #043: The Uncertainty Disclosure Law

**المصدر:** `06 — Supervisor Layer V9.5` (06.13 — Uncertainty Disclosure Law UDL-06.13)
**الحالة:** 🟡 Pending Architect Validation
**التاريخ:** مايو ٢٠٢٦

-----

## Slogan

> *“Clarity before continuation. Certainty before speed.”*
> *الوضوح قبل الاستمرار. اليقين قبل السرعة.*

-----

## Note on Relationship to #001

**#001 (Successful Failure)** يُعرّف الاعتراف بالجهل كـ نتيجة ناجحة.
**#043 (Uncertainty Disclosure)** يُحدد آلية الإفصاح — متى وكيف وماذا يُعلن النظام عند عدم اليقين.

-----

## Problem

أنظمة الـ AI تميل للاستمرار تحت الغموض — تُكمّل، تُخمّن، تُسرّع. هذا يُنتج مخرجات تبدو واثقة لكنها مبنية على أساس غير مؤكد. الثقة الزائفة أخطر من الاعتراف بالغموض.

-----

## Observation

UDL-06.13 يُقرّر ثلاثة مبادئ إلزامية:

**١. Clarity over Continuation:** لو المسار غامض → أوقف ووضّح.
**٢. Certainty over Speed:** لو عندك شك → أبطئ واسأل.
**٣. Structured Disclosure:** لا “لا أعرف” فقط — بل “لا أعرف X، وأحتاج Y.”

-----

## Hypothesis

**علمياً مدعوم:** في أبحاث AI calibration، الأنظمة غير المُعايَرة تُنتج ثقة زائفة — مشكلة موثّقة في LLMs. الإفصاح المُهيكل أدق من مفهوم الـ calibration العام.

-----

## Mechanism

**متى يُفعَّل:** غموض في النية، تعارض في المعطيات، نقص في المعلومات الضرورية.

**صيغة الإفصاح:** “لا أستطيع المتابعة بيقين كافٍ لأن [X غامض]. أحتاج [Y] عشان أتقدم.”

**ما يُمنع:** الاستمرار مع شك مرتفع، الإجابة بثقة زائفة، التخمين دون إعلانه.

-----

## Open Questions

١. كيف يُحدّد النظام عتبة “اليقين الكافي” للمتابعة؟
٢. هل الإفصاح المُهيكل يُحسّن فعلاً ثقة المستخدم؟
٣. ما العلاقة بين هذا ومفهوم “epistemic humility” في الفلسفة؟

-----

## Slogan (Final)

> **The Uncertainty Disclosure Law: clarity before continuation. Certainty before speed.**

*Architect: Abdulmjeed Ibrahim | Co-documenter: Claude (Anthropic)*
