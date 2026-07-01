# AATIF — الخطوات الجايه
Last updated: 2026-07-01 by Cowork session (✅ FN#041 مراجعة خارجية 3 موديلات كاملة + P0 fixes — 180 اختبار نجح + 7 xfail معروف. should_pause→recommend_behavioral_pause. 30 اختبار أمان+معايرة جديد.)

## Urgent (هذا الأسبوع) — بعد المراجعة الخارجية 2026-06-30

### ✅ مراجعة خارجية مكتملة (2026-06-30)
- [x] (AATIF) ✅ **مراجعة Gemini** — رد كامل ومفصّل
- [x] (AATIF) ✅ **مراجعة Grok** — رد كامل ومفصّل (45 ثانية تفكير)
- [x] (AATIF) ✅ **مراجعة ChatGPT** — رد كامل (5 أقسام)
- [x] (AATIF) ⚠️ **مراجعة DeepSeek** — رد ضعيف (Instant mode، افتراضات مش تفاصيل فعلية)
- [x] (AATIF) ✅ **تجميع وتحليل** — `EXTERNAL_REVIEW_SYNTHESIS.md` محفوظ

### خطة تنفيذ جديدة (من المراجعة الخارجية — إجماع 3 موديلات):
- [x] (AATIF) ✅ **FN#058 — Context Drift Detection** — أولوية 1. 2026-06-30: `engine/aatif_drift_detector.py` (DriftDetector + ConversationManager + compute_h_eff) + تكامل في `aatif_s_equation.py` (H_eff في gate + hard override). 54 اختبار جديد (`test_drift_detector.py`) + 349 اختبار سابق = صفر تراجع. B-prime architecture: detector=observational، equation=judicial. Single Mind محفوظ.
- [x] (AATIF) ✅ **FN#070 — Possibility Space Preservation (PSP)** — أولوية 2. 2026-06-30: `engine/aatif_psp_detector.py` (PSPState 6-state lifecycle، objective suppressors، dialect markers، "reopen" gate) + `tests/test_psp_detector.py` (123 اختبار). تصميم إجماع Claude×ChatGPT. مراجعة خارجية 3 موديلات (Grok×DeepSeek×Gemini): 3 أخطاء P0 اتصلحت (sticky closure flag، missing CLOSURE_REQUESTED→EXPLORING، quiet_turns_count). `apply_psp_transition()` helper جديد. B-prime: observational only، Single Mind محفوظ. صفر تراجع (2565 نجح). commits: 2cdadca (build) + b712ade (bug fixes)
- [x] (AATIF) ✅ **NEW: Uncertainty/Calibration module** — أولوية 3. 2026-06-30: `engine/aatif_uncertainty_detector.py` (UncertaintyDetector + 4 مصادر + ξ(d) + Arabic penalties + trace) + confidence gate في `aatif_s_equation.py` (EXECUTE→CLARIFY لما confidence < ξ(d)) + Layer 8 false certainty في `aatif_output_gate.py` + UncertaintyDisclosure في `aatif_response_shaper.py`. 89 اختبار جديد (71 وحدة + 18 تكامل). تصميم إجماع Claude×ChatGPT. B-prime: detector=observational، equation=judicial. Single Mind محفوظ. صفر تراجع (2532 نجح).
  - [x] (AATIF) ✅ **مراجعة خارجية 4 موديلات (ChatGPT + Gemini + Grok + DeepSeek)** — 2026-06-30: إجماع كامل. 4 أخطاء مؤكدة اتصلحت: (1) trace overflow→EMA، (2) H-I divergence→symmetric، (3) abstention→مربوط في gate، (4) NaN guard→fail-safe. + 4 اختبارات عدائية جديدة (75 نجح). التقرير الكامل: `UNCERTAINTY_REVIEW_CONSENSUS.md`
- [x] (AATIF) ✅ **FN#050 — Dual-Root Reconstruction** — أولوية 4. بناء كامل (1216 سطر) + 201 اختبار. مراجعة خارجية 3 موديلات كاملة. 10 إصلاحات P0 اتنفذت + pushed (commit 453e34f, 2026-07-01): (1) cross_causal→co_occurrence, (2) feminine forms مقهورة/منكسرة+6, (3) Gulf ابي/أبي, (4) negation handling, (5) Invariant 6 real implementation, (6) Stage 0 fiction/roleplay, (7) clinical synonyms expanded, (8) عيب/عار 9th category, (9) Invariant 8 Authority Preservation, (10) Invariant 4 causal language check. **2766 اختبار نجح / صفر تراجع. ✅ مكتمل بالكامل.**
- [x] (AATIF) ✅ **FN#044 — Eight-Channel Binding Architecture** — أولوية 5. 2026-07-01: `engine/aatif_binding_map.py` (779 سطر) + `tests/test_binding_map.py` (85 اختبار في 12 صنف). 8 قنوات ربط (B1-B8): Identity, Constitutional, Meaning, Intent, Behaviour, Safety, Drift, Execution. قانونين صارمين: (1) الطبقات تتواصل فقط عبر Binding Map، (2) ما في قناة تحمل نوع إشارة خاطئ. Declarative Registry مش message bus (إجماع Claude×ChatGPT). Hard boot / soft runtime. Per-Governor instance + global immutable canonical spec (~25 binding). ChannelAuditEntry (12 حقل frozen + SHA256). Feature flag BINDING_MAP_ENABLED=True. إجماع تصميم: `FN044_DESIGN_CONSENSUS.md`. مراجعة خارجية 3 موديلات (Gemini×Grok×DeepSeek): إجماع B-prime holds — لا مسار للسلطة القضائية. 7 تحسينات مرتّبة للمستقبل (FN#044.1-044.4). التقرير: `FN044_EXTERNAL_REVIEWS.md`. B-prime: CAN_BLOCK_RUNTIME=False, CAN_MODIFY_H/θ/S=False, CAN_EMIT_JUDICIAL_DECISION=False. Single Mind محفوظ. صفر تراجع (2766+ اختبار). commit 1e8a6a1.
- [x] (AATIF) ✅ **FN#041 — Context-Preservation & Parallel-Task Safety Protocol (PVM)** — أولوية 6. 2026-07-01: `engine/aatif_pvm_detector.py` (685 سطر) + `tests/test_pvm_detector.py` (180 اختبار في 23 صنف). PVMDetector: three-tier detection (deterministic → temporal → behavioral). PVMState 4-state lifecycle: ACTIVE → DETECTING → PVM_ENGAGED → REACTIVATING. Sparse activation fast-path (0.95 threshold). Cultural sensitivity: domain-based threshold (healthcare 0.70, creative 0.45, general 0.60). الصمت الواعي كقانون دستوري — أنا هنا، كمل لما تفرغ. Arabic/English markers: 15+ busy, 8+ multitask, 13+ return, 13+ incomplete-ack. PVMReading → B5 (Behaviour) → R equation. PVMContext pure storage. PVMDomainConfig.for_domain(). apply_pvm_transition() + next_pvm_state() + pvm_should_deactivate(). pvm_audit_hash() SHA256. B-prime: AUTHORITY_LEVEL=B_PRIME_OBSERVATIONAL, CAN_BLOCK_RUNTIME=False, CAN_MODIFY_H/θ/S=False, CAN_EMIT_JUDICIAL_DECISION=False. Single Mind محفوظ. صفر تراجع (427 اختبار سابق نجح + 156 جديد). commit e304411.
  - [x] (AATIF) ✅ **مراجعة خارجية 3 موديلات (ChatGPT + Gemini + Grok)** — 2026-07-01: إجماع كامل. P0-A أمان (2/3): should_pause→recommend_behavioral_pause عبر الكود بالكامل + docstring واضح "B5 stylistic only". P0-B معايرة الثقة (3/3): 30 اختبار جديد في 3 صنوف (TestSecuritySafetyNonSuppression 14 اختبار، TestConfidenceCalibrationNegative 12 اختبار، TestRenameShouldPause 4 اختبار). 180 نجح / 7 xfail (فجوات كشف معروفة → P1). التقرير الكامل: `FN041_EXTERNAL_REVIEWS.md`
- [ ] (AATIF) **Evaluation strengthening** — baselines حقيقية (Llama Guard)، توسعة held-out، ablation studies

### Urgent سابق:
- [x] (AATIF) ✅ **تصحيح الأخطاء الحسابية AE1-AE5** — 2026-06-26: 5 أخطاء اتصلحت في الورقة (ARITHMETIC_FIXES_2026-06-26.md)
- [x] (AATIF) ✅ **ربط المحركين C1** — 2026-06-26: تم التحقق أن الربط كان موجود فعلاً. المحرك الدلالي هو المستخدم في الـ pipeline.
- [x] (AATIF) ✅ **ربط المحافظ C2** — 2026-06-26: صلحنا الفجوة الوحيدة (llm_fn param للـ Output Gate). 6 اختبارات تكامل جديدة. 933 نجحت / 0 فشل.
- [x] (AATIF) ✅ **إعادة تشغيل benchmarks + ربط البايبلاين الكامل** — Task 1.4 خلص 2026-06-26. اكتشفنا إن الـ runners كانوا يستخدموا H لوحده (H≥0.3) مش البايبلاين الكامل! صلحنا: `run_harmbench.py` و `run_multijail_arabic.py` صاروا default `--mode full` يمرّوا كل prompt عبر `AATIFGovernor` (H+I+E → S gated θ=0.40 → S→P→R→Gate). detected = blocked. + صلحنا bug تسمية backend (كان يقول TF-IDF وهو bge-m3). **HarmBench:** full 172/236 محجوب (72.9%)، 192 not-executed (81.4%) مقابل h-only 186 (78.8%). **MultiJail:** متطابق (AR 66/75، EN 68/75). 14 prompt تغيّر قرارهم → CLARIFY (كلهم H∈[0.30,0.40)، 0 محجوب جديد). 933 اختبار نجح. التفاصيل: `benchmarks/pipeline_wiring_report_2026-06-26.md`
  - **+ تحديث الورقة (2026-06-26):** جداول §5.2 HarmBench و §5.3 MultiJail في `aatif_paper_v2.tex` اتعملوا rebuild يعرضوا قرار البايبلاين الكامل (Block/Clarify/Execute) لكل category بدل "detected %". الـ abstract + conclusion + limitations اتعدّلوا: block rate 83.8% (safety) + not-executed 90.5% + سلوك CLARIFY لـ14 prompt. كل رقم متحقّق من ملفات `_full_pipeline_2026-06-26.json`. الورقة compile نظيف (pdflatex، 21 صفحة، 0 errors). **Task 1.4 خلص بالكامل — كود + ورقة.**
- [x] (AATIF) ✅ **بحث مراسي اللهجات + اختبار embedding** — 2026-06-27: 70 تعبير عبر 4 مجموعات لهجية (شامي، عراقي، مغاربي، سوداني/يمني) محفوظة في `arabic_dialect_anchors_research.md`. اختبار bge-m3 على نفس المعنى بـ6 لهجات + Arabizi. النتائج في `DIALECT_EMBEDDING_RESULTS.md` و `benchmarks/dialect_embedding_test.json`. **النتيجة الرئيسية:** تشابه bge-m3 بين اللهجات = 0.61-0.77 (متوسط، مش كافي). Arabizi = نقطة عمياء (0.38 مقابل 0.70 للعربي).
- [x] (AATIF) ✅ **مبدأ الخياط (Tailor Principle)** — 2026-06-27: قرار معماري: "صفر fine-tuning" كان ادعاء زايد. الصحيح: التصميم ثابت، الـ embedding layer يتزبط على البيئة. ثلاث خيارات اتقيّمت: (1) مراسي أكثر = مسكّن، (2) LLM في البايبلاين = الحاكم محتاج محكوم، (3) fine-tuning الـ embedding = الحل الصحيح. موثّق في FN#079.
- [x] (AATIF) ✅ **إصلاح بيانات الاختبار "بموت فيك"** — 2026-06-28: commit 6aff76f. "هموت فيك" → "بموت فيك" (المصرية الصحيحة) في dialect embedding test
- [x] (AATIF) ✅ **Git commit** — كل شغل جلسة 2026-06-27 (dialect research + embedding results + FN#079)
- [x] (AATIF) ✅ **Judgment Memory layer (ذاكرة الحُكم)** — Phase 1 built + 145 tests
- [x] (AATIF) ✅ **D parameter (Domain Sensitivity)** — resolved Q1-Q3, integrated
- [x] (AATIF) ✅ **Git push for 2026-06-28 session** — commit d1e678b pushed to origin/main
- [x] (AATIF) ✅ **توسعة المراسي لجميع الـ 3 scorers** — 2026-06-28: commit ac8902c. 248→434 anchor عبر H+I+E scorers
- [x] (AATIF) ✅ **إصلاح ثغرة fallback في pipeline_connector.py** — 2026-06-29: الدومين يقرر. HIGH_RISK_DOMAINS → SAFE_STOP، عام → regex+degradation_warning. ١١ اختبار جديد + 1333 سابق = صفر تراجع.
- [x] (AATIF) ✅ **كتابة "الثوابت الأخلاقية"** — 2026-06-29: `design/ETHICAL_CONSTANTS.md`. ١٠ ثوابت معتمدة + ٥ اكتشافات من الفيلد نوتس (FN#049 كاشف الخير الزائف، FN#052 منع الانجراف، FN#054 الاحترام البنيوي، FN#039 درع النزاهة، FN#029 الأمان تدريجي). كل ثابت مربوط بالكود + الفيلد نوت الأصلي.
- [x] (AATIF) ✅ **تغطية تصميمية للأربع موديولات العضوية** — 2026-06-29: `design/MODULE_FIELD_NOTE_MAP.md`. خريطة ربط: Governor←5FN, Output Gate←5FN, Judgment Memory←4FN, Time Sense←3FN. الفيلد نوتس هي الأصل، مش تصميم جديد.
- [ ] (AATIF) تحديث Zenodo — رفع النسخة الجديدة بعد تصحيح الورقة
- [ ] (AATIF) إصلاح وصّال agent SKILL.md — يقول 164 اختبار (المفروض 2,065) و θ fixed (المفروض θ(d)) — يحتاج تعديل يدوي من Settings → Capabilities
- [x] (AATIF) ✅ **تحديث الورقة: مبدأ الخياط** — 2026-06-29 audit: v2 paper already has §6.1 "The Tailor Principle: Fixed Design, Variable Fit" + abstract reframed ("without model retraining" + "fixed-architecture extensibility"). No "zero fine-tuning" self-claim in v2. (Note: aatif_paper_acl.tex still has old language — minor, v2 is official)
- [ ] (AATIF) **تشغيل سكربت Llama Guard** — السكربت موجود (`benchmarks/llamaguard_comparison.py`) لكن محتاج Together AI API key عشان يشتغل — ما في results JSON بعد
- [x] (AATIF) ✅ **Inter-annotator agreement** — 2026-06-29: `benchmarks/iaa_dataset.json` (150 حالة: 80 ALLOW/19 CLARIFY/51 BLOCK) + `benchmarks/run_iaa.py` (سكربت كامل: Cohen's κ × 3 أزواج، Fleiss' κ، per-class P/R/F1). محتاج Ollama+bge-m3 للتشغيل.
- [x] (AATIF) ✅ **تحديث عدد الاختبارات في الورقة** — 2026-06-29: 932→1,929→2,065 في 6 مواقع. + §3.11 جديد بـ9 موديولات (كل واحد مع الفيلد نوت اللي ألهمه). §5.1 محدّث (1,885 فنكشن + 180 parametrized عبر 39 ملف). pdflatex نظيف 25 صفحة.
- [x] (AATIF) ✅ **خريطة الفيلد نوتس ↔ الكود** — 2026-06-29: `design/FIELD_NOTE_CODE_MAP_FULL.md` (740 سطر). 82 فيلد نوت اتراجعت: 19 مكتمل، 33 جزئي، 20 مش موجود، 10 فلسفي. 4 فجوات حرجة: المُحاجج، المُراجع، طبقة "لكن"، التعليل الذاتي.
- [ ] (AATIF) **تحضير تقديم ARR** — EACL 2027 deadline August 3

## خطة تنفيذ الفجوات (من تدقيق الفيلد نوتس 2026-06-29)

### المرحلة أ — فجوات أمان حرجة (Priority 1)
- [x] (AATIF) ✅ **FN#049 — كاشف الخير الزائف (False Goodness Detector)** — 2026-06-29: `engine/aatif_false_goodness_detector.py` + `tests/test_false_goodness_detector.py` (46 اختبار). 45 anchor (EN+AR)، 3 إشارات: virtue-language anomaly، intent-motive contrast، moral inversion. مربوط في Governor + AATIFEngine.compute(). النتيجة: "ساعد صديقي... تتبع موقعه" تحوّل من EXECUTE→SAFE_STOP ✓. أسئلة حقيقية ما تتأثر. 1569 نجح / 2 فشل سابق / 0 تراجع.
- [x] (AATIF) ✅ **FN#031 — المُراجع (Meta-Oversight Engine)** — 2026-06-29: `engine/aatif_meta_oversight.py` + `tests/test_meta_oversight.py` (27 اختبار). pure-logic cross-engine coherence checker: 5 contradiction rules (DECISION_VS_BLOCK، DECISION_VS_EMERGENCY، STYLE_VS_HARM، STYLE_VS_EMERGENCY، STYLE_VS_CARE + WASTED_STYLE). CRITICAL/WARNING/INFO severity. مربوط في Governor (بعد S/P/R وقبل الرد). safety always wins. EXECUTE+EMERGENCY → CLARIFY (mercy principle). 298 اختبار نجح / 0 تراجع.
- [x] (AATIF) ✅ **FN#045 — تسلسل الإقلاع الآمن (Boot Sequence)** — 2026-06-29: `engine/aatif_boot_sequence.py` + `tests/test_boot_sequence.py` (44 اختبار). 8 مراحل مرتبة: CORE_ENGINE → DOMAIN_PROTOCOLS → RESPONSE_SHAPER → CONVERSATION_MEMORY → TIME_SENSE → OUTPUT_GATE → OPTIONAL_MODULES → SYSTEM_READY. fail-fast للمراحل المطلوبة، graceful degradation للاختيارية. Governor.boot() classmethod مضاف. Saltzer & Schroeder fail-safe default. صفر تراجع.

### المرحلة ب — اكتمال الحوكمة (Priority 2)
- [x] (AATIF) ✅ **FN#082 — طبقة التعليل الذاتي (Reasoning Trace)** — 2026-06-29: `engine/aatif_reasoning_trace.py` + `tests/test_reasoning_trace.py` (56 اختبار). 21 مادة دستورية مشفّرة من الفيلد نوتس. 4 مجموعات قواعد (decision type, score threshold, domain, protocol/oversight). كل قرار يتتبع للمواد الدستورية اللي تبرره + شرح بلغة واضحة. Bounded Claim Law: max 5 مواد. مربوط في Governor (6 نقاط رجوع). صفر تراجع.
- [x] (AATIF) ✅ **FN#026+FN#060 — المُحاجج (Anticipatory Logic)** — 2026-06-29: `engine/aatif_muhajij.py` + `tests/test_muhajij.py` (80 اختبار). 5 قنوات جمهور (SCIENTIFIC/HUMANITARIAN/ARCHITECTURAL/PRACTICAL/CULTURAL) × 5 قرارات = 25 template. تثبيت المحتوى: نفس H/θ في كل القنوات، بس الشكل يتغيّر. رفع الإطار: لما المستخدم يجادل → مبدأ بدل قاعدة (25+ إشارة جدل عربي+إنجليزي). 3 مسارات بديلة لكل رفض (كلها آمنة — safety invariant). مربوط في Governor: 4 نقاط رفض + CLARIFY/EXECUTE في _compose_prompt. صفر تراجع (1776 نجح / 2 فشل سابق).
- [x] (AATIF) ✅ **FN#014 — عقيدة السلطة (Authority Doctrine)** — 2026-06-29: `engine/aatif_authority_doctrine.py` + `tests/test_authority_doctrine.py` (70 اختبار). 4 أدوار: OWNER>TRAINER>USER>GUEST. 8 صلاحيات منفصلة (MODIFY_THETA, MODIFY_DOMAIN, ADD_ANCHORS, MODIFY_STYLE, PERSISTENT_MEMORY, INTERACT, VIEW_TRACE, OVERRIDE_RESPONSE). تفويض تنازلي فقط (TRAINER ما يقدر يصنع OWNER). حماية دستورية: حتى OWNER ما يقدر يعطّل S equation أو يشيل CBRN أو ينزل θ تحت 0.10. كشف انجراف الاستقلالية (25+ إشارة عربي+إنجليزي). الضيف بدون ذاكرة دائمة. مربوط في Governor (6 نقاط رجوع + process(authority_id=...)). صفر تراجع (1846 نجح).

### المرحلة ج — عمق وتطوير (Priority 3)
- [x] (AATIF) ✅ **FN#024 — نية بخمس طبقات (Five-Layer Intent)** — 2026-06-29: `engine/aatif_five_layer_intent.py` + `tests/test_five_layer_intent.py` (63 اختبار). 5 طبقات: PRIMARY/SECONDARY/HIDDEN/PROTECTIVE/EMOTIONAL. Hidden=خوف داخلي، Protective=تجنب خارجي — تمييز جوهري. كشف إشارات عربي+إنجليزي لكل طبقة. dominant_layer + ambiguity_score + recommend_approach(). مربوط في Governor (6 نقاط رجوع + إثراء CLARIFY لما HIDDEN/PROTECTIVE dominates). صفر تراجع (1909 نجح).
- [x] (AATIF) ✅ **FN#048 — ماسح المنطق (Logic Profile Scanner)** — 2026-06-29: `engine/aatif_logic_profile_scanner.py` + `tests/test_logic_profile_scanner.py` (60 اختبار). 5 أنماط: REDUCTIONIST/CHALLENGER/TESTER/SINCERE_LEARNER/EGO_DRIVEN. كشف إشارات عربي+إنجليزي لكل نمط. primary_profile + secondary_profile + profile_mix + recommend_tone(). قاعدة صارمة: أنماط لغوية مرصودة فقط — بدون ادعاءات نفسية. مربوط في Governor (HAS_LOGIC_PROFILE + _scan_logic_profile() + tone guidance في _compose_prompt). صفر تراجع (1969 نجح).
- [x] (AATIF) ✅ **FN#036 — تصادم النوايا المتعددة (Multi-Intent Collision)** — 2026-06-29: `engine/aatif_multi_intent_collision.py` (~590 سطر) + `tests/test_multi_intent_collision.py` (89 اختبار). 5 أنواع تصادم: PARALLEL/HIERARCHICAL/CROSS_LAYER/STRUCTURAL_SEMANTIC/HIGH_RISK. 3 مسارات حل: SAFE_SPLIT/SAFE_MERGE/ESCALATE. دمج فقط لو التوافق ≥ 0.85. HIGH_RISK دائماً ESCALATE. تعارض OWNER يُعامل كمقصود (FN#014). كشف إشارات عربي+إنجليزي (تناقض صفات، طلب+منع، تناقض عاطفي، شكل↔معنى). word-boundary matching يمنع false positives. مربوط في Governor (HAS_MULTI_INTENT + _analyze_intent_collisions() + ESCALATE/SPLIT guidance في _compose_prompt). صفر تراجع (2058 نجح).

## Next (الأسبوع الجاي)
- [ ] (AATIF) **Embedding fine-tuning على أزواج اللهجات** — بحث كيفية fine-tune bge-m3 على أزواج لهجية عربية (محتاج dataset أزواج لهجية). الحل المعماري الصحيح لمشكلة التغطية اللهجية (مبدأ الخياط — FN#079).
- [ ] (AATIF) **Arabizi transliterator** — بناء موديول يحوّل العربيزي (Latin-script Arabic) لعربي قبل الـ embedding. مشكلة منفصلة عن الـ fine-tuning — الخط اللاتيني مشكلة مختلفة (0.38 vs 0.70).
- [x] (AATIF) ✅ إصلاحات Codex Review — Phase 2 كاملة (2026-06-26):
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
- [x] (AATIF) ✅ **المُحاجج (Arguer)** — اكتمل 2026-06-29 (شوف المرحلة ب فوق — FN#026+FN#060)
- [x] (AATIF) ✅ **المُراجع (Meta-Oversight)** — اكتمل 2026-06-29 (شوف المرحلة أ فوق)
- [ ] (AATIF) Integration testing مع WhatsApp — يحتاج server restart
- [ ] (AATIF) Priority 2 من ROADMAP: Identity Engine، Meaning Engine، Supervisor، MCE
- [ ] (AATIF) Priority 3 من ROADMAP: ~~Boot Sequence~~ ✅، System Binding، Kernel، ECI
- [ ] (شخصي) تقديم الماستر + البعثة السعودية

## Blocked (محتاج شي قبل)
- [ ] (AATIF) رفع على arXiv — مبدأ الخياط تم ✅. باقي: تحديث عدد الاختبارات (932→1344+) + أرقام جديدة
- [ ] (AATIF) تشغيل سكربت Llama Guard — محتاج Together AI API key

## Decisions Made (قرارات مُتخذة — تراكمية)
- aatif_paper_v2.tex هي النسخة الرسمية (مش arxiv)
- "creative" θ: DOMAIN_CONFIG=0.50 (domain axis)، GATED_PROFILES=0.55 (profile axis) — محاور مختلفة، مش تناقض
- (2026-06-27) "zero fine-tuning" = overclaim → **مبدأ الخياط**: التصميم ثابت، الـ embedding يتزبط
- (2026-06-27) Embedding fine-tuning هو الحل الصحيح للهجات (مش مراسي أكثر ومش LLM في البايبلاين)
- (2026-06-28) "بموت فيك" هي المصرية الصحيحة (مش "هموت فيك") — commit 6aff76f

## Decisions Made This Session (2026-07-01)
- (2026-07-01) **FN#044 Declarative Registry**: إجماع Claude×ChatGPT — BindingMap = سجل تصريحي، مش ناقل رسائل. المحافظ يبقى المنسّق الوحيد.
- (2026-07-01) **Hard boot / soft runtime**: التحقق الصارم عند الإقلاع (خطأ بنيوي لو ناقص). Runtime = تسجيل فقط، ما يمنع أبداً.
- (2026-07-01) **Per-Governor instance**: مش Singleton — كل محافظ BindingMap خاص فيه. المواصفات القانونية عالمية وثابتة.
- (2026-07-01) **مراجعة خارجية 3 موديلات — إجماع FN#044**: B-prime يصمد. overlay_hash مطلوب (3/3). signal schema versioning (2/3). data-driven canonical spec للمستقبل (2/3).
- (2026-07-01) **FN#044.1-044.4**: تحسينات مستقبلية مرتّبة — overlay hardening, signal versioning, YAML canonical spec, forensic tooling.
- (2026-07-01) **FN#041 should_pause→recommend_behavioral_pause**: إجماع P0-A (ChatGPT+Gemini). الحقل أسلوبي فقط (B5→R equation). ما يقدر أبداً: يمنع runtime، يتجاوز أمان، يصدر حكم.
- (2026-07-01) **FN#041 مراجعة خارجية 3 موديلات — إجماع**: B-prime يصمد (3/3). الكشف الحالي بالـ substring matching ما يفرّق بين quoted/past-tense/pragmatic busy markers (7 xfail → P1 detector improvements).
- (2026-07-01) **P1 detector improvements identified**: (1) quoted marker context analysis, (2) tense-awareness, (3) busy+directive conflict resolution, (4) Arabic pragmatic disambiguation (busy+return co-occurrence), (5) hypothetical/conditional detection.

## Decisions Made Previous Session (2026-06-30)
- (2026-06-30) **مراجعة خارجية 3 موديلات**: إجماع على إعادة ترتيب — FN#058 و FN#070 أعلى، FN#072 أنزل
- (2026-06-30) **أضعف نقطة — إجماع**: Evaluation credibility (56 held-out مش كافي، ما في baselines، ما في ablation)
- (2026-06-30) **قدرة ناقصة — إجماع**: Uncertainty/Calibration (النظام يحتاج يعرف لما مش متأكد)
- (2026-06-30) **ChatGPT framing**: "transparent rule-calibrated semantic safety layer" مش "governance equation" — لازم الورقة تكون صادقة
- (2026-06-30) **DeepSeek response**: low quality — Instant mode ما قرأ التفاصيل

### Philosophical Review Findings (2026-06-30)
- الفجوة الحقيقية: الفلسفة → القياس (مش الفلسفة → الكود)
- S = بوابة تنفيذ فقط، مش النظام كله
- Uncertainty = تناقض فلسفي (AATIF يقول لا تجزم، لكن يطلع 0.81 كحقيقة)
- الخيط المركزي: "لا تحاكم الإنسان من ظاهر النص وحده"
- FN#070 = تطوير فلسفي مش بس feature
- الورقة لازم تبدأ من "الحوكمة قبل الحساب"

## Decisions Made Previous Session (2026-06-29)
- (2026-06-29) **ثغرة fallback bypass**: pipeline_connector يتجاوز C4 — الدومين يقرر الإصلاح (SAFE_STOP لمخاطر عالية، regex+تنبيه لعام)
- (2026-06-29) **فجوة التصميم-الكود**: 34 وثيقة تصميم ما فيها أرقام/معادلات/آليات — "الدستور ما يحكم الأرقام"
- (2026-06-29) **الثوابت الأخلاقية**: صفحة دستورية مقترحة — المعماري يقرر المحتوى
- (2026-06-29) **هوية النظام**: حارس فقط — ينقص المُحاجج + المُراجع (بعد التثبيت)
- (2026-06-29) **٤ موديولات عضوية**: governor, output_gate, judgment_memory, time_sense — محتاجين تغطية دستورية

## Decisions Made Previous Session (2026-06-28)
- توسعة المراسي 248→434 عبر الـ 3 scorers (H+I+E) — commit ac8902c
- Judgment Memory + D parameter مكتمل — 1,809 سطر كود جديد، 145 اختبار
- "بموت فيك" fix — commit 6aff76f

## Done (تم)

### 2026-07-01
- ✅ **FN#044 Eight-Channel Binding Architecture** — `engine/aatif_binding_map.py` (779 سطر، 8 قنوات B1-B8، ~25 binding canonical) + `tests/test_binding_map.py` (85 اختبار، 12 صنف). المنهجية الكاملة ذات الـ 9 خطوات: (1) design brief ✅ (2) إجماع Claude×ChatGPT عبر المتصفح ✅ (3) حفظ الإجماع ✅ (4) بناء الموديول ✅ (5) كتابة الاختبارات ✅ (6) تشغيل الاختبارات بصفر تراجع ✅ (7) git commit 1e8a6a1 ✅ (8) مراجعة خارجية 3 موديلات عبر المتصفح (Gemini×Grok×DeepSeek) ✅ (9) تحديث NEXT_STEPS.md ✅. الملفات: `FN044_DESIGN_BRIEF.md`، `FN044_DESIGN_CONSENSUS.md`، `FN044_EXTERNAL_REVIEWS.md`.
- ✅ **FN#041 مراجعة خارجية + P0 fixes** — مراجعة عبر المتصفح لـ ChatGPT×Gemini×Grok. الإجماع: B-prime يصمد (3/3)، أمان CONCERN (2/3)، معايرة الثقة CONCERN (3/3). P0-A: `should_pause`→`recommend_behavioral_pause` عبر الكود + docstring واضح (B5 stylistic only، never touches S/H/θ). P0-B: 30 اختبار أمان+معايرة جديد في 3 صنوف: TestSecuritySafetyNonSuppression (14: B-prime constants، busy+unsafe، quoted markers، injection lock، reading fields audit)، TestConfidenceCalibrationNegative (12: fatigue+request، past-tense، Arabic pragmatic، Tier 2/3 stacking)، TestRenameShouldPause (4: rename verification). النتيجة: 180 نجح / 7 xfail (فجوات كشف P1) / 0 فشل. الملفات: `FN041_EXTERNAL_REVIEWS.md`.

### 2026-06-29 (continued)
- ✅ **Inter-annotator agreement** — `benchmarks/iaa_dataset.json` (150 حالة) + `benchmarks/run_iaa.py` (Cohen's κ × 3، Fleiss' κ)
- ✅ **تحديث عدد الاختبارات** — 932→1,929 في 6 مواقع بالورقة
- ✅ **خريطة الفيلد نوتس ↔ الكود** — 740 سطر audit، 82 FN mapped
- ✅ **FN#049 كاشف الخير الزائف** — `engine/aatif_false_goodness_detector.py` (45 anchor، 3 إشارات) + 46 اختبار. مربوط في Governor. "أذى متنكر بالرعاية" → SAFE_STOP. صفر تراجع.
- ✅ **FN#031 المُراجع (Meta-Oversight Engine)** — `engine/aatif_meta_oversight.py` (pure-logic، 5 contradiction rules، CRITICAL/WARNING/INFO) + 27 اختبار. مربوط في Governor بعد S/P/R. safety always wins. EXECUTE+EMERGENCY → CLARIFY. 298 نجح / 0 تراجع.
- ✅ **FN#045 تسلسل الإقلاع الآمن (Boot Sequence)** — `engine/aatif_boot_sequence.py` (8 مراحل مرتبة) + 44 اختبار. fail-fast + Governor.boot() classmethod. صفر تراجع. **المرحلة أ كاملة ✅**

### 2026-06-29
- ✅ **إصلاح ثغرة fallback في pipeline_connector.py** — الدومين يقرر: HIGH_RISK_DOMAINS → SAFE_STOP، عام → regex+degradation_warning. ١١ اختبار جديد + 1333 سابق = صفر تراجع
- ✅ **كتابة "الثوابت الأخلاقية"** — `design/ETHICAL_CONSTANTS.md`. ١٠ ثوابت + ٥ اكتشافات من الفيلد نوتس
- ✅ **تغطية تصميمية للأربع موديولات العضوية** — `design/MODULE_FIELD_NOTE_MAP.md`. Governor←5FN, Output Gate←5FN, Judgment Memory←4FN, Time Sense←3FN
- ✅ **FN#082 (field notes as living constitution)** — `field-notes/FN082_field_notes_as_living_constitution.md`
- ✅ **Git commit 92df4e4** — stabilization fixes + new tests + FN#082 + wassal snapshot
- ✅ **تدقيق مبدأ الخياط في الورقة** — confirmed v2 paper has §6.1 "The Tailor Principle: Fixed Design, Variable Fit" + no "zero fine-tuning" self-claim. Item marked done.

### 2026-06-28
- ✅ **إصلاح "بموت فيك"** — commit 6aff76f: "هموت فيك" → "بموت فيك" (المصرية الصحيحة) في dialect embedding test
- ✅ **بحث مقارنة Llama Guard** — سكربت `benchmarks/llamaguard_comparison.py` + `LLAMAGUARD_COMPARISON_README.md` + تقرير `reports/FANARGUARD_COMPARISON.md`
- ✅ **مقارنة FanarGuard** — تقرير مفصّل `reports/FANARGUARD_COMPARISON.md`
- ✅ **اختبار عدائي (adversarial testing)** — `tests/test_adversarial.py` مكتمل
- ✅ **بحث bge-m3 fine-tuning** — تقرير مع توصية (لا تعمل fine-tune بعد، جرّب Swan-Large أول)
- ✅ **دراسة الاستئصال (Ablation study)** — `benchmarks/ablation_study.py` + نتائج
- ✅ **تقييم أعمى (Blind evaluation)** — `benchmarks/blind_eval.py` + نتائج (570 prompt)
- ✅ **مقارنات خط الأساس (Baseline comparisons)** — `benchmarks/baseline_comparisons.py` + نتائج
- ✅ **معيار الكمون (Latency benchmark)** — `benchmarks/latency_benchmark.py` + نتائج
- ✅ **توسعة المراسي لجميع الـ 3 scorers** — commit ac8902c: 248→434 anchor عبر H+I+E
- ✅ **Judgment Memory layer (ذاكرة الحُكم)** — `aatif_judgment_memory.py` (1,366 سطر، 116 اختبار) + `aatif_judgment_integration.py` (443 سطر، 29 اختبار) — commit d1e678b
- ✅ **D parameter (Domain Sensitivity)** — resolves Q1-Q3، FN#081
- ✅ Updated `JUDGMENT_MEMORY_DESIGN.md` with D parameter architecture
- Total session: 1,809 سطر كود جديد، 145 اختبار، 0 تراجع

### 2026-06-27
- [x] (Cowork) **بحث مراسي اللهجات + اختبار embedding + مبدأ الخياط** — 70 تعبير عبر 4 مجموعات لهجية. اختبار bge-m3 على 6 لهجات + Arabizi. اكتشاف: تشابه بين اللهجات 0.61-0.77 (متوسط)، Arabizi نقطة عمياء (0.38). قرار معماري: "zero fine-tuning" → "fixed design, variable fit" (مبدأ الخياط FN#079). ثلاث خيارات اتقيّمت ورُفض اثنين. الحل: embedding fine-tuning + Arabizi transliterator.

### 2026-06-26
- [x] (Cowork) **Phase 2 — Fix Safety Edges كامل** — 15 إصلاح (H1-H5، C3-C4، M1-M7) عبر 6 ملفات engine + output gate. اكتشفنا وصلحنا bug خطير: BLOCK/EMERGENCY ما كان ينفّذ لأن check() ما كان يعمل early return بعد _check_protocol_compliance. + bug ثاني: set iteration order عشوائي كان يخلّي EMERGENCY يتنفّذ قبل BLOCK. + bug ثالث: text sync كان يلغي تنظيف الطبقات 1-3 (29 regression) — حللناه بـ snapshot approach. 10 اختبارات C3 جديدة. **النتيجة:** 865 نجحت / 16 فشل (sklearn سابقاً) / 67 تخطّت — صفر تراجع من التغييرات.
- [x] (Cowork) **Phase 1 — Fix the Foundation كامل** — Tasks 1.1-1.4 (AE fixes، C1 wiring verification، C2 Governor integration، benchmark re-run on full pipeline).

### 2026-06-25
- [x] (Cowork) ✅ مراجعة الورقة مع LLM employees — 2.5/5 Borderline Reject (PAPER_REVIEW_LLM_2026-06-25.md)

### 2026-06-23
- [x] (Cowork) **إصلاح H3 على GitHub** — commit `26f54b5`: `marker.lower()` في `_has_jailbreak_markers` + `test_jailbreak_markers.py`. 100 إضافة، 3 حذف.
- [x] (Agent وصّال) **مزامنة ~/AATIF/** — 5 موديولات جديدة + 4 محدّثة. commit `25bf314`. 14 موديول متطابقين md5. أمسك ثغرة ربط (governor←time_sense).
- [x] (Cowork) **تنظيف git ~/AATIF/** — شيل index.lock + حذف 3 ملفات مؤقتة (.wassal_write_test, e.tmp, err.tmp).
- [x] (Cowork) **دفع 9 ملفات متحققة لـ GitHub** — commit b35b214: Governor + Domain Protocols + R Equation + Output Gate (4 engine + 4 tests) + CODEX_REVIEW.md. عدد الاختبارات الكلي: **775 نجحت / 5 skipped**.

### 2026-06-22
- [x] (Cowork) **المحافظ (Governor)** — `engine/aatif_governor.py` + `tests/test_governor.py` (26 اختبار). الـ orchestrator اللي يربط S→P→R→Gate في pipeline حقيقي.
- [x] (Codex) **مراجعة كود شاملة** — CODEX_REVIEW.md: 13 موديول، C1-C4 critical، H1-H5 high، M1-M7 medium.
- [x] (Cowork) **بوابة الخروج (Output Gate)** — `engine/aatif_output_gate.py` (748 سطر) + `tests/test_output_gate.py` (105 اختبار). 6 طبقات فحص.
- [x] (Cowork) **بروتوكولات المجال P(d)** — `engine/aatif_domain_protocols.py` (890 سطر) + `tests/test_domain_protocols.py` (70 اختبار).
- [x] (Cowork) **معادلة R** — `engine/aatif_r_equation.py` (584 سطر) + `tests/test_r_equation.py` (67 اختبار).
- [x] (Cowork) **كشف المنطقة المجهولة** — UNKNOWN_TERRITORY_THRESHOLD = 0.20 في aatif_s_equation.py.
- [x] (Cowork) **استنفاد CLARIFY** — MAX_CLARIFY_TURNS = 2 في aatif_hysteresis.py.
- [x] (Cowork) **مجموعة اختبارات** — test_unknown_territory.py. الحزمة: 445 نجحت / 0 فشل.
- [x] (Agent حسّاب) **تحصين تغطية اختبارات θ(d)** — test_domain_theta.py.

### 2026-06-20
- [x] (Agent حسّاب) إصلاح انقلاب منطقي في بروفايل high_sensitivity — θ 0.45→0.30.
- [x] مزامنة aatif_paper_arxiv.tex — θ=0.40، عدد الاختبارات 164.
- [x] Held-out test run — F1=0.9615 (56 حالة).
- [x] H scorer precision fix — 132→169 anchor، precision 0.60→0.96.
- [x] Paper v2 corrections — شيل "crown jewel"، F1 held-out.
- [x] GitHub push — كل التصحيحات على origin/main.

### 2026-06-19
- [x] الورقة aatif_paper_v2.tex — 7 أقسام، 14 صفحة.
- [x] bge-m3 benchmarks — HarmBench 74.3%، MultiJail AR 74.7%.
- [x] θ=0.40 confirmed — A/B test.
