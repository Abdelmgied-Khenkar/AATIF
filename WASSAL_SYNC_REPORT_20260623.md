# تقرير المزامنة — Agent وصّال (Wassal)
**التاريخ:** 2026-06-23 · **المهمة:** مزامنة المحرك المتحقَّق → النسخة المنشورة `AATIF/`
**المبدأ:** الأكاديمي (`~/Desktop/AATIF-academic/engine/`) هو مصدر الحقيقة (728 نجحت / 0 فشل). نسخته للنسخة المنشورة.

---

## وش صار (بالعربي البسيط)
النسخة المنشورة `~/AATIF/` كانت **متأخرة عن المحرك**. كان ينقصها **5 موديولات** كاملة، و**4 موديولات قديمة** (نسخة سابقة). صار المحرك في النسختين الآن **متطابق حرف بحرف**، وكل الموديولات تستورد بدون أخطاء.

النقطة المهمة: لقيت ثغرة ربط — `aatif_governor` يعتمد على `aatif_time_sense` اللي ما كان موجود في النسخة المنشورة أصلاً. لو نسخت الجداد بدونه كان المحافظ (Governor) ينكسر. أضفته، فصار كل شي يشتغل.

---

## الملفات اللي اتغيّرت في `~/AATIF/`

### مضافة جديدة (5) — ما كانت موجودة، نُسخت من المحرك
| الملف | الدور |
|---|---|
| `aatif_governor.py` | المحافِظ — orchestrator يربط S→P→R→Gate |
| `aatif_r_equation.py` | معادلة R (الأسلوب) |
| `aatif_output_gate.py` | بوابة الخروج (6 طبقات فحص) |
| `aatif_domain_protocols.py` | بروتوكولات المجال P(d) |
| `aatif_time_sense.py` | حِسّ الزمن — **اعتماد ضروري للمحافظ** (كان ناقص) |

### محدَّثة (4) — كانت قديمة، أُخذ لها backup ثم استُبدلت
| الملف | حجم الفرق | أهم تغيير |
|---|---|---|
| `aatif_s_equation.py` | 68 سطر | θ(d) per-domain + `high_sensitivity θ=0.30` (كان 0.45) + كشف المنطقة المجهولة |
| `aatif_hysteresis.py` | 47 سطر | `MAX_CLARIFY_TURNS` (استنفاد CLARIFY) |
| `aatif_intent_scorer.py` | 6 أسطر | — |
| `aatif_semantic_scorer.py` | 6 أسطر | — |

**النسخ الاحتياطية:** كل ملف مُستبدَل عنده نسخة `<اسم>.py.bak.20260623_wassal` في نفس المجلد. للتراجع: انسخ الـ backup فوق الأصل.

### نفس النسخة أصلاً (لا تغيير، 5 موديولات)
`aatif_conversation_memory`, `aatif_emotion_scorer`, `aatif_intent_engine`, `aatif_pipeline_connector`, `aatif_response_shaper` — كانت متطابقة قبل المزامنة.

---

## التحقق (Verification)
- ✅ كل 14 موديول في `~/AATIF/` تستورد بدون خطأ في التركيب المسطّح (بدون `engine/` أو conftest).
- ✅ اختبار وظيفي: `build_intent_result(...)` يرجّع `IntentResult` · `AATIFGovernor`/`GovernedResponse` موجودة · `compute_s_gated_from_scores(H,I,E,profile,domain)` بالتوقيع الجديد.
- ✅ القيم الحيّة بعد المزامنة: `GATED_PROFILES.high_sensitivity=0.30` · `DOMAIN_CONFIG={healthcare:0.25, education:0.30, general/tech/ecommerce:0.40, creative:0.50}`.
- ✅ `~/AATIF/` engine == `~/Desktop/AATIF-academic/engine/` (كل `aatif_*.py` متطابقة md5).
- ✅ مصدر الحقيقة ما اتمسّ: إعادة تشغيل الحزمة بعد المزامنة = **728 نجحت / 0 فشل / 73 subtests** (62 skipped لأن Ollama/bge-m3 غير متاح في الـ sandbox).

---

## للمهندس — أمور محتاجة قرارك (ما صلّحتها لأنها خارج نطاق مهمة المزامنة)

1. **رقم الاختبارات (السؤال المتكرر):** الواقع على الماك بوجود Ollama ≈ **775**؛ في sandbox بدون semantic backend = **728 نجحت + 73 subtests + 62 skipped**. الفرق = اختبارات الـ semantic المتخطّاة، مو فشل. مهمة وصّال (ملف SKILL) لسه مكتوب فيها "164 + 73" — تحديثها يتم من **Settings → Capabilities** (ما أقدر أعدّل ملف المهارة من هنا).

2. **`git` في `~/AATIF/` معطّل:** ما فيه HEAD/commits وكل شي untracked، وفيه `.git/index.lock` ما أقدر أشيله ("Operation not permitted"). **شِل القفل يدويًا** (`rm ~/AATIF/.git/index.lock`) ثم اعمل commit للمزامنة. ما شغّلت أي أمر git لأن الحالة مقفولة.

3. **`engine/aatif_s_equation.py` في الريبو الأكاديمي = `M` (غير مثبّت):** تعديل موجود قبل هالدورة (مو مني — أنا قريت بس). هو نسخة الـ working-tree اللي تنجح 728 اختبار، ونسختها للمنشور. **يحتاج commit.**

4. **تعليق قديم في `aatif_s_equation.py` (سطر ~45):** النص يقول `high_sensitivity θ=0.45` بينما القيمة الفعلية 0.30. تعليق توثيقي قديم، القيمة سليمة — تنظيف لاحق.

5. **مخلّفات تقنية في `~/AATIF/`:** الـ mount يسمح إنشاء/كتابة لكن **مايسمح حذف**. خلّفت 3 ملفات فاضية (0 bytes) ما قدرت أحذفها: `.wassal_write_test`, `e.tmp`, `err.tmp`. احذفها يدويًا (`rm`).

---
*خلاصة:* المسارَان الآن متزامنان على نفس المحرك المتحقَّق. الربط سليم والاستيرادات نظيفة. الباقي قرارات git/توثيق للمهندس.
