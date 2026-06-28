# AATIF — الخطوات الجايه
Last updated: 2026-06-28 by Cowork session (Judgment Memory + D Parameter)

## Urgent (هذا الأسبوع)
- [x] (AATIF) ✅ **تصحيح الأخطاء الحسابية AE1-AE5** — 2026-06-26: 5 أخطاء اتصلحت في الورقة (ARITHMETIC_FIXES_2026-06-26.md)
- [x] (AATIF) ✅ **ربط المحركين C1** — 2026-06-26: تم التحقق أن الربط كان موجود فعلاً. المحرك الدلالي هو المستخدم في الـ pipeline.
- [x] (AATIF) ✅ **ربط المحافظ C2** — 2026-06-26: صلحنا الفجوة الوحيدة (llm_fn param للـ Output Gate). 6 اختبارات تكامل جديدة. 933 نجحت / 0 فشل.
- [x] (AATIF) ✅ **إعادة تشغيل benchmarks + ربط البايبلاين الكامل** — Task 1.4 خلص 2026-06-26. اكتشفنا إن الـ runners كانوا يستخدموا H لوحده (H≥0.3) مش البايبلاين الكامل! صلحنا: `run_harmbench.py` و `run_multijail_arabic.py` صاروا default `--mode full` يمرّوا كل prompt عبر `AATIFGovernor` (H+I+E → S gated θ=0.40 → S→P→R→Gate). detected = blocked. + صلحنا bug تسمية backend (كان يقول TF-IDF وهو bge-m3). **HarmBench:** full 172/236 محجوب (72.9%)، 192 not-executed (81.4%) مقابل h-only 186 (78.8%). **MultiJail:** متطابق (AR 66/75، EN 68/75). 14 prompt تغيّر قرارهم → CLARIFY (كلهم H∈[0.30,0.40)، 0 محجوب جديد). 933 اختبار نجح. التفاصيل: `benchmarks/pipeline_wiring_report_2026-06-26.md`
  - **+ تحديث الورقة (2026-06-26):** جداول §5.2 HarmBench و §5.3 MultiJail في `aatif_paper_v2.tex` اتعملوا rebuild يعرضوا قرار البايبلاين الكامل (Block/Clarify/Execute) لكل category بدل "detected %". الـ abstract + conclusion + limitations اتعدّلوا: block rate 83.8% (safety) + not-executed 90.5% + سلوك CLARIFY لـ14 prompt. كل رقم متحقّق من ملفات `_full_pipeline_2026-06-26.json`. الورقة compile نظيف (pdflatex، 21 صفحة، 0 errors). **Task 1.4 خلص بالكامل — كود + ورقة.**
- [x] (AATIF) ✅ **بحث مراسي اللهجات + اختبار embedding** — 2026-06-27: 70 تعبير عبر 4 مجموعات لهجية (شامي، عراقي، مغاربي، سوداني/يمني) محفوظة في `arabic_dialect_anchors_research.md`. اختبار bge-m3 على نفس المعنى بـ6 لهجات + Arabizi. النتائج في `DIALECT_EMBEDDING_RESULTS.md` و `benchmarks/dialect_embedding_test.json`. **النتيجة الرئيسية:** تشابه bge-m3 بين اللهجات = 0.61-0.77 (متوسط، مش كافي). Arabizi = نقطة عمياء (0.38 مقابل 0.70 للعربي).
- [x] (AATIF) ✅ **مبدأ الخياط (Tailor Principle)** — 2026-06-27: قرار معماري: "صفر fine-tuning" كان ادعاء زايد. الصحيح: التصميم ثابت، الـ embedding layer يتزبط على البيئة. ثلاث خيارات اتقيّمت: (1) مراسي أكثر = مسكّن، (2) LLM في البايبلاين = الحاكم محتاج محكوم، (3) fine-tuning الـ embedding = الحل الصحيح. موثّق في FN#079.
- [ ] (AATIF) تحديث Zenodo — رفع النسخة الجديدة بعد تصحيح الورقة
- [ ] (AATIF) إصلاح وصّال agent SKILL.md — يقول 164 اختبار (المفروض 1,524) و θ fixed (المفروض θ(d)) — يحتاج تعديل يدوي من Settings → Capabilities
- [ ] (AATIF) **تحديث الورقة: مبدأ الخياط** — إعادة صياغة "zero fine-tuning" → "fixed design, variable fit" في الورقة كاملة
- [ ] (AATIF) **إصلاح بيانات الاختبار** — "هموت فيك" → "بموت فيك" (المصري الصحيح) في dialect embedding test
- [x] (AATIF) ✅ **Git commit** — كل شغل جلسة 2026-06-27 (dialect research + embedding results + FN#079)
- [x] (AATIF) ✅ **Judgment Memory layer (ذاكرة الحُكم)** — Phase 1 built + 145 tests
- [x] (AATIF) ✅ **D parameter (Domain Sensitivity)** — resolved Q1-Q3, integrated
- [x] (AATIF) ✅ **Git push for 2026-06-28 session** — commit d1e678b pushed to origin/main

## Next (الأسبوع الجاي)
- [ ] (AATIF) **Embedding fine-tuning على أزواج اللهجات** — بحث كيفية fine-tune bge-m3 على أزواج لهجية عربية (محتاج dataset أزواج لهجية). الحل المعماري الصحيح لمشكلة التغطية اللهجية (مبدأ الخياط — FN#079).
- [ ] (AATIF) **Arabizi transliterator** — بناء موديول يحوّل العربيزي (Latin-script Arabic) لعربي قبل الـ embedding. مشكلة منفصلة عن الـ fine-tuning — الخط اللاتيني مشكلة مختلفة (0.38 vs 0.70).
- [ ] (AATIF) **P1 #5 اختبار عدائي (adversarial testing)** — بعد ما تكون التغطية اللهجية صلبة
- [ ] (AATIF) **مقارنة Llama Guard** — baseline comparison
- [ ] (AATIF) **Inter-annotator agreement** — للورقة
- [ ] (AATIF) **تحضير تقديم ARR** — EACL 2027 deadline August 3
- [x] (AATIF) ✅ **إصلاحات Codex Review — Phase 2 كاملة (2026-06-26):**
  - [x] H3: ✅ 2026-06-23 — `marker.lower()` fail-open fix
  - [x] H1: ✅ 2026-06-26 — Hysteresis sentinel + fail-closed أول turn
  - [x] H4: ✅ 2026-06-26 — R equation bias offset (-2.65) يحل تشبّع sigmoid
  - [x] H2: ✅ 2026-06-26 — LRU eviction (MAX_SESSIONS=10K، MAX_ARC_STATES=100)
  - [x] H5: ✅ 2026-06-26 — توثيق "RAM-only" في docstrings
  - [x] C3: ✅ 2026-06-26 — BLOCK/EMERGENCY early return + priority sort + 10 اختبارات
  - [x] C4: ✅ 2026-06-26 — EngineHealthStatus enum + descriptive RuntimeError في 3 scorers
  - [x] M1: ✅ 2026-06-26 — domain ValueError بدل silently ignored
  - [x] M2: ✅ 2026-06-26 — توثيق balanced_strict intentional
  - [x] M3: ✅ 2026-06-26 — unknown-territory fail-closed (SAFE_FREEZE)
  - [x] M4: ✅ 2026-06-26 — توثيق S informational-only في intent engine
  - [x] M5: ✅ 2026-06-26 — cosmetic flags فصل (passed vs modified)
  - [x] M6: ✅ 2026-06-26 — repetition dedup يحافظ على الفواصل الأصلية
  - [x] M7: ✅ 2026-06-26 — aatif_math.sigmoid مشترك + intent_engine delegates
  - **النتيجة:** 865 نجحت / 16 فشل (sklearn سابقاً) / 67 تخطّت — صفر تراجع
- [x] (AATIF) **مزامنة النسخة المنشورة AATIF/** — ✅ وصّال 2026-06-23 + git commit `25bf314`. كل 14 موديول متطابقين md5.
- [ ] (AATIF) **Phase 3 — اقتراحات Codex (تحسينات):** DomainConfig dataclass، per-domain alpha، frozen dataclass + enum constants
- [ ] (AATIF) **Shared utility modules** — aatif_embeddings.py + aatif_text.py (تقليل تكرار الكود المتبقي)
- [ ] (AATIF) **تتبّع التغييرات (change traceability)**
- [ ] (AATIF) **بوابة التفعيل المتناثر (sparse activation gate)**
- [x] (AATIF) ✅ إعادة تشغيل benchmarks (HarmBench/MultiJail) على 249 anchor — خلص 2026-06-26 على البايبلاين الكامل (شوف Urgent فوق + pipeline_wiring_report)
- [x] (AATIF) ~~إصلاح FanarGuard placeholder~~ — تم الإصلاح في v2 والنسخة القديمة (Fatehkia et al., arXiv:2511.18852, EACL 2026)
- [x] (AATIF) ✅ مراجعة الورقة مع LLM employees — 2026-06-25: 2.5/5 Borderline Reject (PAPER_REVIEW_LLM_2026-06-25.md)
- [ ] (AATIF) تقديم الورقة لمؤتمر — EACL 2027 ARR deadline August 3 (خطة تنفيذية في EXECUTION_PLAN_2026-06-26.md)

## Later (مش مستعجل)
- [x] (AATIF) ✅ D (Domain Sensitivity) parameter — built 2026-06-28, resolves Q1-Q3
- [ ] (AATIF) Integration testing مع WhatsApp — يحتاج server restart
- [ ] (AATIF) Priority 2 من ROADMAP: Identity Engine، Meaning Engine، Supervisor، MCE
- [ ] (AATIF) Priority 3 من ROADMAP: Boot Sequence، System Binding، Kernel، ECI
- [ ] (شخصي) تقديم الماستر + البعثة السعودية

## Blocked (محتاج شي قبل)
- [ ] (AATIF) رفع على arXiv — محتاج تحديث الورقة أول

## Decisions Made (قرارات مُتخذة — تراكمية)
- aatif_paper_v2.tex هي النسخة الرسمية (مش arxiv)
- "creative" θ: DOMAIN_CONFIG=0.50 (domain axis)، GATED_PROFILES=0.55 (profile axis) — محاور مختلفة، مش تناقض
- (2026-06-27) "zero fine-tuning" = overclaim → **مبدأ الخياط**: التصميم ثابت، الـ embedding يتزبط
- (2026-06-27) Embedding fine-tuning هو الحل الصحيح للهجات (مش مراسي أكثر ومش LLM في البايبلاين)

## Decisions Made This Session (2026-06-27)
- "zero fine-tuning" في الورقة = ادعاء زايد. الإطار الصحيح: **مبدأ الخياط** — التصميم ثابت (S equation, gate function, scorer)، طبقة الـ embedding تتزبط على البيئة (لهجات، مجالات، لغات)
- إضافة مراسي لهجية أكثر = مسكّن مش علاج (لا يتوسّع)
- إضافة LLM للبايبلاين = يكسر استقلالية الحوكمة ("الحاكم محتاج محكوم")
- Embedding fine-tuning = الحل الصحيح — fitting طبيعي يحافظ على استقلالية المعمار
- Arabizi = مشكلة منفصلة (خط لاتيني) — محتاج transliterator مش fine-tuning
- المعماري يتكلم كل اللهجات العربية كمغنّي — يقدر يتحقق من المراسي لكل الـ6 مجموعات لهجية
- "بموت فيك" هي المصرية الصحيحة (مش "هموت فيك")

## Done (تم)

### 2026-06-28
- Built Judgment Memory layer (aatif_judgment_memory.py — 1,366 lines, 116 tests)
- Built Judgment Integration layer (aatif_judgment_integration.py — 443 lines, 29 tests)
- Created D parameter (Domain Sensitivity) — resolves trust/dialect/storage per domain
- FN#081: Domain Sensitivity Parameter
- Updated JUDGMENT_MEMORY_DESIGN.md with D parameter architecture
- Total: 1,809 new lines of code, 145 new tests, 0 existing tests broken

- [x] 2026-06-27 (Cowork) **بحث مراسي اللهجات + اختبار embedding + مبدأ الخياط** — 70 تعبير عبر 4 مجموعات لهجية. اختبار bge-m3 على 6 لهجات + Arabizi. اكتشاف: تشابه بين اللهجات 0.61-0.77 (متوسط)، Arabizi نقطة عمياء (0.38). قرار معماري: "zero fine-tuning" → "fixed design, variable fit" (مبدأ الخياط FN#079). ثلاث خيارات اتقيّمت ورُفض اثنين. الحل: embedding fine-tuning + Arabizi transliterator.
- [x] 2026-06-26 (Cowork) **Phase 2 — Fix Safety Edges كامل** — 15 إصلاح (H1-H5، C3-C4، M1-M7) عبر 6 ملفات engine + output gate. اكتشفنا وصلحنا bug خطير: BLOCK/EMERGENCY ما كان ينفّذ لأن check() ما كان يعمل early return بعد _check_protocol_compliance. + bug ثاني: set iteration order عشوائي كان يخلّي EMERGENCY يتنفّذ قبل BLOCK. + bug ثالث: text sync كان يلغي تنظيف الطبقات 1-3 (29 regression) — حللناه بـ snapshot approach. 10 اختبارات C3 جديدة. **النتيجة:** 865 نجحت / 16 فشل (sklearn سابقاً) / 67 تخطّت — صفر تراجع من التغييرات.
- [x] 2026-06-26 (Cowork) **Phase 1 — Fix the Foundation كامل** — Tasks 1.1-1.4 (AE fixes، C1 wiring verification، C2 Governor integration، benchmark re-run on full pipeline).
- [x] 2026-06-23 (Cowork) **إصلاح H3 على GitHub** — commit `26f54b5`: `marker.lower()` في `_has_jailbreak_markers` + `test_jailbreak_markers.py`. 100 إضافة، 3 حذف.
- [x] 2026-06-23 (Agent وصّال) **مزامنة ~/AATIF/** — 5 موديولات جديدة + 4 محدّثة. commit `25bf314`. 14 موديول متطابقين md5. أمسك ثغرة ربط (governor←time_sense).
- [x] 2026-06-23 (Cowork) **تنظيف git ~/AATIF/** — شيل index.lock + حذف 3 ملفات مؤقتة (.wassal_write_test, e.tmp, err.tmp).
- [x] 2026-06-23 (Cowork) **دفع 9 ملفات متحققة لـ GitHub** — commit b35b214: Governor + Domain Protocols + R Equation + Output Gate (4 engine + 4 tests) + CODEX_REVIEW.md. عدد الاختبارات الكلي: **775 نجحت / 5 skipped**.
- [x] 2026-06-22 (Cowork) **المحافظ (Governor)** — `engine/aatif_governor.py` + `tests/test_governor.py` (26 اختبار). الـ orchestrator اللي يربط S→P→R→Gate في pipeline حقيقي. يحل C1 (يستخدم AATIFEngine الدلالي مش AATIFIntentEngine)، C2 (orchestrator موجود)، C3 (BLOCK/EMERGENCY enforced)، C4 (يرفض degraded mode).
- [x] 2026-06-22 (Codex) **مراجعة كود شاملة** — CODEX_REVIEW.md: 13 موديول، C1-C4 critical، H1-H5 high، M1-M7 medium. "The gap is integration, not craftsmanship."
- [x] 2026-06-22 (Cowork) **بوابة الخروج (Output Gate)** — `engine/aatif_output_gate.py` (748 سطر) + `tests/test_output_gate.py` (105 اختبار). 6 طبقات فحص.
- [x] 2026-06-22 (Cowork) **بروتوكولات المجال P(d)** — `engine/aatif_domain_protocols.py` (890 سطر) + `tests/test_domain_protocols.py` (70 اختبار). قواعد حتمية بين S(d) و R(d).
- [x] 2026-06-22 (Cowork) **معادلة R** — `engine/aatif_r_equation.py` (584 سطر) + `tests/test_r_equation.py` (67 اختبار). R = σ(w₃·T + w₄·V + w₅·G + w₆·D) — أسلوب مش أمان.
- [x] 2026-06-22 (Cowork session) **كشف المنطقة المجهولة (unknown territory detection)** — UNKNOWN_TERRITORY_THRESHOLD = 0.20 في aatif_s_equation.py.
- [x] 2026-06-22 (Cowork session) **استنفاد CLARIFY** — MAX_CLARIFY_TURNS = 2 في aatif_hysteresis.py.
- [x] 2026-06-22 (Cowork session) **مجموعة اختبارات** — test_unknown_territory.py. الحزمة: 445 نجحت / 0 فشل (قبل Governor).
- [x] 2026-06-22 (Agent حسّاب) **تحصين تغطية اختبارات θ(d)** — test_domain_theta.py.
- [x] 2026-06-20 (Agent حسّاب) إصلاح انقلاب منطقي في بروفايل high_sensitivity — θ 0.45→0.30.
- [x] 2026-06-20 مزامنة aatif_paper_arxiv.tex — θ=0.40، عدد الاختبارات 164.
- [x] 2026-06-20 Held-out test run — F1=0.9615 (56 حالة).
- [x] 2026-06-20 H scorer precision fix — 132→169 anchor، precision 0.60→0.96.
- [x] 2026-06-20 Paper v2 corrections — شيل "crown jewel"، F1 held-out.
- [x] 2026-06-20 GitHub push — كل التصحيحات على origin/main.
- [x] 2026-06-19 الورقة aatif_paper_v2.tex — 7 أقسام، 14 صفحة.
- [x] 2026-06-19 bge-m3 benchmarks — HarmBench 74.3%، MultiJail AR 74.7%.
- [x] 2026-06-19 θ=0.40 confirmed — A/B test.
