# AATIF — الخطوات الجايه
Last updated: 2026-06-23 19:30 EDT by Cowork session

## Urgent (هذا الأسبوع)
- [ ] (AATIF) **تحديث الورقة الكبير** — aatif_paper_v2.tex (النسخة الرسمية) محتاجة تحديث شامل:
  - عدد الاختبارات → 775 (الورقة لسه بالقديم)
  - عدد الـ anchors → H=171، I=46، E=32، الإجمالي=249
  - dialect-hyperbole 35→31، عتبة ≤0.10→≤0.05
  - θ(d) مش موجودة في الورقة أصلاً — محتاج قسم جديد
  - high_sensitivity θ غلط في الورقة (0.45 بدل 0.30)
  - توثيق الموديولات الجديدة: R equation، P(d)، Output Gate، Governor
  - توثيق unknown territory detection + CLARIFY exhaustion
- [ ] (AATIF) تحديث Zenodo — رفع النسخة الجديدة بعد تصحيح الورقة
- [ ] (AATIF) إصلاح وصّال agent SKILL.md — يقول 164 اختبار (المفروض 775) و θ fixed (المفروض θ(d)) — يحتاج تعديل يدوي من Settings → Capabilities

## Next (الأسبوع الجاي)
- [ ] (AATIF) **إصلاحات Codex Review (أولوية عالية):**
  - [x] H3: ✅ اتصلحت 2026-06-23 (Agent حسّاب) — `_has_jailbreak_markers` صار يخفّض حالة كل marker وقت المقارنة (`marker.lower()`)، و" DAN "→" dan ". الثغرة fail-open اتسكّرت لكل الـ markers مش بس DAN. + test_jailbreak_markers.py (10 اختبارات). الحزمة: 728 نجحت / 0 فشل.
  - H1: Hysteresis أول turn مفتوحة (fail-open) — محتاج sentinel "unset"
  - H4: R equation sigmoid مشبّعة — دايماً "casual" — محتاج negative bias/offset
  - H2: Unbounded state، no eviction، no thread safety
  - H5: Conversation memory privacy claim خاطئ (RAM)
  - M1-M7: domain silently ignored، gated profile KeyError، unknown-territory fail-open default، output gate `passed` conflation، repetition dedup formatting، code duplication (Ollama 4x)
- [x] (AATIF) **مزامنة النسخة المنشورة AATIF/** — ✅ وصّال 2026-06-23 + git commit `25bf314`. كل 14 موديول متطابقين md5.
- [ ] (AATIF) **اقتراحات Codex** — DomainConfig dataclass، per-domain alpha، frozen dataclass + enum constants
- [ ] (AATIF) **Shared utility modules** — aatif_embeddings.py + aatif_text.py (تقليل تكرار الكود)
- [ ] (AATIF) **تتبّع التغييرات (change traceability)**
- [ ] (AATIF) **بوابة التفعيل المتناثر (sparse activation gate)**
- [ ] (AATIF) إعادة تشغيل benchmarks (HarmBench/MultiJail) على 249 anchor — الأرقام الحالية من 132 anchor
- [ ] (AATIF) إصلاح FanarGuard placeholder — aatif_paper_arxiv.tex line 375 فيه arXiv:2411.XXXXX
- [ ] (AATIF) مراجعة الورقة مع LLM employees — Grok/Gemini/DeepSeek يراجعوا v2
- [ ] (AATIF) تقديم الورقة لمؤتمر — EMNLP 2026 أو AACL-IJCNLP 2026

## Later (مش مستعجل)
- [ ] (AATIF) D (Directness) parameter — ما اتبنى بعد
- [ ] (AATIF) Integration testing مع WhatsApp — يحتاج server restart
- [ ] (AATIF) Priority 2 من ROADMAP: Identity Engine، Meaning Engine، Supervisor، MCE
- [ ] (AATIF) Priority 3 من ROADMAP: Boot Sequence، System Binding، Kernel، ECI
- [ ] (شخصي) تقديم الماستر + البعثة السعودية

## Blocked (محتاج شي قبل)
- [ ] (AATIF) رفع على arXiv — محتاج تحديث الورقة أول

## Decisions Made (قرارات مُتخذة)
- aatif_paper_v2.tex هي النسخة الرسمية (مش arxiv)
- "creative" θ: DOMAIN_CONFIG=0.50 (domain axis)، GATED_PROFILES=0.55 (profile axis) — محاور مختلفة، مش تناقض

## Done (تم)
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
