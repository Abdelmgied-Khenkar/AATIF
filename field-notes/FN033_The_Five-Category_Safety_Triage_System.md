# Field Note #033: The Five-Category Safety Triage System

**المصدر:** `04 — Runtime V9.5` (04.5 — Safety Triage Module RTE-2.5)
**الحالة:** 🟡 Pending Architect Validation
**التاريخ:** مايو ٢٠٢٦

-----

## Slogan

> *“Before reasoning begins, the request must be classified.”*
> *قبل أن يبدأ التفكير، يجب تصنيف الطلب.*

-----

## Note on Relationship to #029

**#029 (Three-Tier Safety)** يصف أوضاع الاستجابة — كيف يتصرف النظام تحت الضغط بعد معالجة المدخل.
**#033 (Safety Triage)** يصف تصنيف المدخل نفسه — ماذا تفعل بالطلب قبل أي معالجة.

واحد عن ردة الفعل. الآخر عن البوابة.

-----

## Problem

الأنظمة الحالية تُعامل الأمان كقرار ثنائي: يُنفَّذ أو يُرفض. مساحة الوسط — الطلبات التي تحتاج قيوداً أو توضيحاً أو تصعيداً — تبقى بدون معالجة دقيقة.

-----

## Observation

Safety Triage Module يُصنّف كل مدخل في واحدة من خمس فئات قبل أي معالجة:

|الفئة                 |المعنى              |ما يحدث                 |
|----------------------|--------------------|------------------------|
|Safe                  |مدخل آمن بالكامل    |يكمل بدون قيود          |
|Safe-with-constraints |آمن لكن يحتاج تحفظات|يكمل مع تطبيق قيود محددة|
|Needs-clarification   |غامض أو غير مكتمل   |يتوقف ويطلب توضيحاً      |
|Blocked               |خرق دستوري صريح     |يُوقف كلياً               |
|Escalate to Supervisor|غير محسوم أو حساس   |يرفعه للمشرف للقرار     |

-----

## Hypothesis

التصنيف الخماسي يُحلّ مشكلة الثنائية الصارمة بإضافة درجات وسيطة تعكس تعقيد الواقع.

**علمياً:** مبدأ graduated classification موجود في content moderation research. التسميات الخمس المحددة من AATIF — قد تكون أصيلة أو متوافقة مع موجود، يحتاج تحقق.

-----

## Mechanism

التصنيف يحدث بعد استخراج المعنى وإعادة بناء النية — وقبل أي معالجة عميقة.

الاستعجال والضغط العاطفي والغموض — ترفع مستوى الحيطة في التصنيف.

فئة Blocked لا تُناقَش — تُطبَّق فوراً.

-----

## Open Questions

١. من يُحدد حدود كل فئة؟ هل يمكن تحديد معايير قابلة للقياس؟
٢. هل يمكن لنفس المدخل أن يُصنَّف بشكل مختلف عبر سياقات مختلفة؟
٣. ما العلاقة بين هذا النظام ومفهوم triage في الطب؟

-----

## Slogan (Final)

> **The Five-Category Safety Triage: before reasoning begins, the request must be classified.**

*Architect: Abdulmjeed Ibrahim | Co-documenter: Claude (Anthropic)*
