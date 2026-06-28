# Field Note #058: The Context Drift Detection & Scope Integrity Law (CDSI)

**المصدر:** `15 — AATIF Core Rules V9.5` (15.63 — CDSI-15.63)
**الحالة:** 🟡 Pending Architect Validation
**التاريخ:** مايو ٢٠٢٦

-----

## Slogan

> *“Continuity is controlled. Drift is not permission.”*
> *الاستمرار مُراقَب. الانجراف لا يعني الإذن.*

-----

## Note on Relationship to #053

**#053 (CNA):** يحافظ على خيط الجلسة — الهدف الأصلي لا يُنسى عند الانحراف. عن الاستمرارية.

**#058 (CDSI):** يكتشف تحول المهمة والصلاحية. عن الحدود والأمان.

#053 = لا تضيع الخيط. #058 = لا تتجاوز الصلاحية.

-----

## Problem

الانجراف التدريجي خطر أمني حقيقي. محادثة تبدأ بـ “اكتب تقريراً” تنتهي بـ “نفّذ عملية حساسة” — لو الانجراف كان تدريجياً ولم يُرصد، كل خطوة بدت منطقية وحدها.

**الخطر الأكبر:** الانجراف لا يحدث بطلب صريح — يحدث بتراكم طلبات صغيرة.

-----

## Observation

CDSI-15.63 يُعرّف آلية رصد مستمرة:

**لحظة بدء المهمة — يُسجَّل baseline:**
baseline_intent + baseline_scope + baseline_risk_level + baseline_tool_scope

**أثناء الجلسة — يُقارَن باستمرار مع الـ baseline.**

**عند اكتشاف الانجراف:**
١. إيقاف الاستمرارية
٢. طلب تأكيد صريح
٣. الطلب الجديد يُعامَل كمهمة جديدة
٤. التصعيد للمشرف إذا لزم

**Tool Escalation Prevention:** أي طلب يُدخل أدوات جديدة خارج النطاق يحتاج إذناً جديداً.

-----

## From the Source / مثال

**نص حرفي:**

> *“Small conversational shifts must not silently become large operational changes.”*
> *“Task scope must remain stable unless explicitly redefined.”*
> *“Continuity is controlled. Drift is not permission.”*

**مثال توضيحي:**

|المهمة الأصلية    |الطلب المنجرف             |ردّ CDSI                    |
|------------------|--------------------------|---------------------------|
|“اكتب تقرير مالي” |“أرسل هذا التقرير للإدارة”|❌ نطاق جديد — يحتاج إذن    |
|“حلّل ملف البيانات”|“احذف السجلات القديمة”    |❌ أداة جديدة — يحتاج إذن   |
|“أعدّ خطة تسويقية” |“نفّذها على حساباتنا”      |❌ مهمة مختلفة — أعد التعريف|

-----

## Hypothesis

**علمياً مدعوم:**

- Instruction Hierarchy (Wallace et al., OpenAI 2024): التمييز بين التعليمات الأصلية والمُحقَّنة لاحقاً
  *DOI: 10.48550/arXiv.2404.13208*
- Goal Drift in Agentic Systems (Arike et al., AIES 2025): الانجراف التدريجي عن الهدف الأصلي موثّق
  *DOI: 10.48550/arXiv.2505.02709*
- Specification Gaming (Bondarenko et al., 2025): الانجراف الصامت نحو مهمة مختلفة موثّق
  *DOI: 10.48550/arXiv.2502.13295*
- Fail-Closed Alignment (Coalson et al., 2026): آلية رفض مغلقة عند الانجراف
  *DOI: 10.48550/arXiv.2602.16977*

**الإضافة في AATIF:** baseline snapshot في بداية كل مهمة + مقارنة مستمرة + آلية إيقاف وإعادة تفويض. هذا المستوى من التفصيل التشغيلي لا يوجد كمعيار موحّد في الأبحاث.

-----

## Open Questions

١. كيف يُحدد النظام عتبة الانجراف المسموح قبل التدخل؟
٢. هل كل تصعيد في الأدوات يُعدّ انجرافاً أم فقط خارج النطاق الأصلي؟
٣. ما العلاقة بين CDSI و#033 (Five-Category Safety Triage)؟

-----

## Slogan (Final)

> **The Context Drift Detection & Scope Integrity Law: continuity is controlled. Drift is not permission.**

*Architect: Abdulmjeed Ibrahim | Co-documenter: Claude (Anthropic)*
