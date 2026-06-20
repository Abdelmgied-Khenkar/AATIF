# AATIF — الخطوات الجايه
Last updated: 2026-06-20 by Cowork session

## Urgent (هذا الأسبوع)
- [ ] (AATIF) مراجعة aatif_paper_v2.tex مع المعماري — التصحيحات اتعملت بس محتاجة مراجعة نهائية
- [ ] (AATIF) تحديث Zenodo — رفع النسخة الجديدة من الورقة
- [ ] (AATIF) إصلاح وصّال agent — يقول "134+ tests" بدل "164+"

## Next (الأسبوع الجاي)
- [ ] (AATIF) إعادة تشغيل benchmarks (HarmBench/MultiJail) على مجموعة 169 anchor — الأرقام الحالية في الورقة من إعداد 132 anchor، وفيه footnote يوضّح هذا لحد ما يتعاد التشغيل
- [ ] (AATIF) توحيد الورقتين — aatif_paper_arxiv.tex و aatif_paper_v2.tex اتشعّبوا؛ نقرر أيهما الرسمي لـ arXiv/Zenodo
- [ ] (AATIF) إصلاح FanarGuard placeholder — aatif_paper_arxiv.tex line 375 فيه arXiv:2411.XXXXX يحتاج الرقم الصحيح
- [ ] (AATIF) مراجعة الورقة مع LLM employees — Grok/Gemini/DeepSeek يراجعوا v2
- [ ] (AATIF) تقديم الورقة لمؤتمر — EMNLP 2026 أو AACL-IJCNLP 2026

## Later (مش مستعجل)
- [ ] (AATIF) D (Directness) parameter — ما اتبنى بعد
- [ ] (AATIF) Integration testing مع WhatsApp — يحتاج server restart
- [ ] (شخصي) تقديم الماستر + البعثة السعودية

## Blocked (محتاج شي قبل)
- [ ] (AATIF) رفع على arXiv — محتاج مراجعة الورقة أول

## Done (تم)
- [x] 2026-06-20 (Agent حسّاب) إصلاح انقلاب منطقي في بروفايل high_sensitivity (gated) — كان θ=0.45 وهو أعلى من default (0.40)، يعني البوابة كانت **أكثر تساهلاً** من الافتراضي على كل مدى الأذى H∈[0.20,0.50] (عند H=0.40: بوابة 0.68 مقابل 0.50 للافتراضي) — عكس اسم البروفايل وتعليقه ومواصفة v9.7. صُحّح إلى θ=0.30. أُضيف اختبار regression (test_gate_strictness_ordering) يقفل الترتيب high_sensitivity ≤ default ≤ creative. الحزمة: 197 نجحت / 0 فشل (+1 اختبار). ملاحظة: الإصلاح في المحرك الأكاديمي فقط — aatif-sales-engine ما فيه هذا الملف فلا يحتاج مزامنة. تنبيه: فيه .git/index.lock عالق يحتاج إزالة يدوية قبل أي commit
- [x] 2026-06-20 مزامنة aatif_paper_arxiv.tex (Agent كاتب) — θ=0.40 بدل 0.55، وصف المعايرة (54 حالة، A/B بتاريخ 2026-06-19)، عدد الاختبارات 164 بدل 132، + footnote عن توسعة anchors لـ169؛ الورقة تُترجم نضيف (14 صفحة)
- [x] 2026-06-20 Held-out test run — 56 حالة جديدة، F1=0.9615 (precision 0.9615, recall 0.9615)
- [x] 2026-06-20 H scorer precision fix — safe + counter-harm anchors، 17 FP → 1 FP، precision 0.60 → 0.96 (132 → 169 anchor)
- [x] 2026-06-20 Paper v2 corrections — شيل "crown jewel"، F1 held-out 0.9615 بدل in-sample 0.984، تصحيح contribution claim + human-over-the-loop
- [x] 2026-06-20 GitHub push — كل التصحيحات على origin/main
- [x] 2026-06-20 طباعة الورقة PDF — aatif_paper_v2.tex compiled نضيف (14 صفحة)
- [x] 2026-06-19 LIMITATIONS.md — 8 limitations موثّقة (Trojan horse, sarcasm, implicit harm, benchmarks, multi-turn, equation evolution, modality, dialects)
- [x] 2026-06-19 الورقة الجديدة aatif_paper_v2.tex — 7 أقسام، S equation صفحة 1، 14 صفحة
- [x] 2026-06-19 تصحيح أرقام anchors — 132/44/32 مش 154/59/43
- [x] 2026-06-19 Skill الكتابة الأكاديمية — aatif-academic-paper مثبت
- [x] 2026-06-19 Feedback memory التحقق — قاعدة التحقق من الأرقام محفوظة
- [x] 2026-06-19 Account separation — خريطة AATIF vs عبدالمجيد محفوظة
- [x] 2026-06-19 bge-m3 benchmarks — HarmBench 74.3%, MultiJail AR 74.7%
- [x] 2026-06-19 θ=0.40 confirmed — A/B test, pushed to GitHub
- [x] 2026-06-19 Git push 7f50401 — all changes on GitHub
