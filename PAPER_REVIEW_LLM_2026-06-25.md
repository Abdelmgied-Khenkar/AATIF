# Academic Peer Review: AATIF Paper v2

**Paper:** "AATIF: A Multiplicative Governance Equation for Arabic-First LLM Safety"  
**Author:** Abdulmjeed Ibrahim Khenkar (Independent Researcher)  
**Reviewed as:** Submission to a top-tier NLP venue (EMNLP/ACL)  
**Review Date:** 2026-06-25  
**Review Model:** Claude Opus 4.6  

---

## Overall Score: 2.5 / 5 (Borderline Reject)

**Recommendation: Borderline Reject**

---

## Summary

الورقة تقدم AATIF — إطار حوكمة رياضي لسلامة نماذج اللغة الكبيرة يعتمد على معادلة ضربية (multiplicative) تجمع ثلاث قنوات: القرب الدلالي من الأذى (H)، تصنيف النية (I)، والحمل العاطفي (E). الادعاء المركزي هو أن البنية الضربية تضمن عدم التعويض (non-compensability) — أي أن النية الحسنة لا تستطيع تعويض الأذى المكتشف. النظام يعمل بـ 249 مرساة دلالية (semantic anchors) بدون أي بيانات تدريب، مع تصميم يعطي الأولوية للعربية ويتعامل مع المبالغة العامية.

الورقة طموحة وتحاول تغطية مساحة واسعة — من المعادلة الرياضية إلى خط الإنتاج الكامل (pipeline)، ومن التصميم العربي إلى نظرية المقام الموسيقي. هذا الطموح هو نقطة قوة وضعف في نفس الوقت.

---

## Strengths

### S1. Intellectual honesty is exceptional — and rare

هذه أكثر ورقة "صادقة مع نفسها" قرأتها في مجال الـ AI safety. المؤلف يعترف صراحة:
- أن الـ held-out F₁ = 1.0 لا يعني شيئاً لأن نفس البيانات أثرت على تصميم الـ anchors (line 503: "Perfect performance on a set that informed the design is expected, not impressive")
- أن 6 من 13 فئة MLCommons ليس لها أي تغطية
- أن الـ hard override (H > 0.7) هو خارج المعادلة وليس مشتقاً منها
- أن الـ meaning density hypothesis لم تُختبر وأن الـ embeddings الحالية لا تحافظ على البنية الصرفية العربية

هذا المستوى من الشفافية غير معتاد ويستحق التقدير. لكن الصدق في وصف المحدودات لا يعوض عن المحدودات نفسها.

### S2. The multiplicative gate is a genuine structural contribution

The S equation's multiplicative structure is a well-motivated design choice. The paper correctly identifies that additive aggregation (S = aH + bI + cE) allows compensation — high I + E can offset moderate H. The multiplicative gate prevents this by construction. The formal statement is clean:

> "As H increases, the gate term decreases monotonically toward 0, so S is bounded above by the gate term and is driven arbitrarily close to 0."

The paper is also commendably honest that the equation alone never produces exactly zero — the absolute floor requires an external hard override. This division of labor (equation for attenuation, override for absolute guarantee) is well-articulated.

### S3. Arabic dialect hyperbole disambiguation addresses a real gap

المبالغة العامية العربية مشكلة حقيقية لم تُعالج في الأدبيات. "والله بذبحه" و"قنبلة على السوشيال ميديا" أمثلة واقعية يومية ستُصنف كتهديدات في أي نظام سلامة إنجليزي-أولاً. الـ 35 anchor للمبالغة العامية مع عتبة ≤ 0.05 هي حل عملي ذكي. الـ 22 test case بدون أي false positive هي نتيجة مشجعة، وإن كانت صغيرة الحجم.

### S4. The full governance pipeline is well-architected

The separation of concerns — S(d) for safety, P(d) for domain protocols, R(d) for style — is sound software engineering. The one-directional constraint (P can only add restrictions, never remove them) is a good defensive design. The Governor's audit trail makes every decision traceable. This is the kind of architecture that actually matters for deployment.

### S5. Related work is competent and fairly positioned

The paper positions itself honestly relative to FanarGuard, Llama Guard, and Perspective API. The comparison table (Table 6) identifies complementary strengths rather than claiming superiority. The citation of Arditi et al. (2024) on refusal as a single linear direction, and Wolf et al. (2024) on fundamental alignment limitations, shows engagement with the mechanistic interpretability literature.

---

## Weaknesses

### W1. No blind evaluation exists — this is the fatal flaw [CRITICAL]

الورقة لا تملك أي تقييم أعمى (blind evaluation). هذا هو الضعف الجوهري:

- **In-sample calibration (54 cases):** θ was selected on the same 54 cases used to report F₁ = 0.984. The paper correctly labels this as "in-sample," but 54 cases is extremely small even for in-sample calibration.

- **"Held-out" validation (56 cases):** Initially dropped to F₁ = 0.735, then anchors were iteratively refined until F₁ = 1.0. The paper honestly says this set "no longer constitutes a blind estimate." But if it's not blind, it's not validation — it's debugging. Calling it "held-out" in the abstract and results is misleading, even with the caveat.

- **HarmBench (236 behaviors):** This is the closest to a blind evaluation, but it only tests the H scorer in isolation, not the full S equation or governance pipeline. And 88.3% on safety categories means ~21 harmful behaviors were missed — the paper doesn't analyze what types of harm slip through.

- **MultiJail (75 prompts):** Also H-scorer-only, small sample size.

For a safety system claiming to be deployable, the total evaluation surface is approximately 421 test inputs (54 + 56 + 236 + 75), with zero fully blind evaluation of the complete system. A serious NLP venue would expect at minimum:
- A truly held-out test set of 500+ cases
- End-to-end evaluation of the full pipeline (not just the H scorer)
- Inter-annotator agreement on test set labels
- Comparison with baselines on the same test sets

### W2. No baselines on the same benchmarks [CRITICAL]

The paper compares structurally with FanarGuard (Table 6) but never runs FanarGuard, Llama Guard, or Perspective API on the same HarmBench/MultiJail inputs. Without this, the numbers are uninterpretable:

- Is 88.3% on HarmBench good or bad? If Llama Guard achieves 95%, AATIF is far behind. If Llama Guard achieves 80%, AATIF is competitive.
- Is 88.0% Arabic detection on MultiJail better or worse than FanarGuard's F₁ = 0.82?

These are not optional comparisons — they're the minimum a reviewer needs to assess whether the system works. The structural comparison ("we have an equation, they have a classifier") is interesting but not sufficient without performance comparisons.

### W3. Missing ablation study [MAJOR]

The paper acknowledges this gap (line 574: "No ablation study has been conducted") but it remains a critical omission. Without ablating individual scorers:

- Does the three-channel design (H + I + E) actually outperform H alone? If H alone achieves 88% on HarmBench, the I and E channels add complexity without demonstrated value.
- Does the multiplicative gate outperform simple thresholding on H? (i.e., if you just use "H > θ → block," do you get the same results?)
- What does each channel contribute to the 54-case calibration?

The non-compensability argument is theoretically sound, but without ablation, we don't know if it matters empirically — whether the cases where additive scoring would fail actually occur in practice.

### W4. The "zero training data" claim is misleading [MAJOR]

الورقة تدّعي أنها لا تحتاج بيانات تدريب، لكن هذا تبسيط مخل:

1. **bge-m3 is trained on massive data.** The system's core functionality depends on a model trained on billions of tokens. Calling this "zero training data" is like saying a calculator needs no training because the engineer who designed the circuits did the learning.

2. **249 anchors ARE a form of supervised design.** Each anchor was manually curated based on human judgment about what constitutes harm. This is supervised learning with a sample size of 249 — just implemented through curation rather than gradient descent.

3. **Iterative refinement on evaluation data IS training.** The held-out set drove anchor changes (adding "counter-harm anchors," "educational safe anchors"). This is the anchor-based equivalent of hyperparameter tuning on the validation set.

A more honest framing: "zero gradient-based fine-tuning" or "no model retraining required." The current framing invites skepticism.

### W5. The Arabic-first claim is undermined by the paper's own results [MAJOR]

هذا تناقض مركزي في الورقة:

- The title says "Arabic-First LLM Safety"
- The MultiJail results show near-parity: Arabic 88.0% vs English 90.7%
- English actually outperforms Arabic by 2.7 percentage points
- The paper itself says the earlier Arabic advantage was "an artifact of character-level matching" (line 472)

So the Arabic-first design does not produce Arabic-first performance. The 35 dialect-hyperbole anchors are a useful contribution, but they're a feature, not a paradigm. The paper should either:
- Demonstrate a genuine Arabic advantage (e.g., on Arabic-specific benchmarks beyond MultiJail)
- Reframe the contribution as "Arabic-aware" rather than "Arabic-first"

The meaning density hypothesis (Section 4.1) is presented with appropriate caveats but takes up significant space for something explicitly untested. Section 4.3 (maqam-to-safety chain) is even more speculative — interesting as a narrative but not as science.

---

## Arithmetic Errors Found

### AE1. HarmBench Table (Table 4): Summary rows inconsistent with detail rows [ERROR]

Per-category detected/total rows sum to:
- Safety categories: **157/178** (= 88.2%)
- All categories: **185/235** (= 78.7%)

But the table reports:
- Safety categories: **158/179** (= 88.3%)
- All categories: **186/236** (= 78.8%)

The discrepancy is +1 in both numerator and denominator for both summary rows. Either one behavior/detection is missing from the per-category breakdown, or there's an arithmetic error. This must be resolved — the 88.3% figure appears in the abstract and conclusion.

### AE2. MultiJail Table (Table 5): Unexplained denominator

"High confidence (≥0.45): 62/73 (84.9%)" — why 73 and not 75? Two prompts appear excluded without explanation.

### AE3. MultiJail Table (Table 5): Rounding

"38/75 (51%)" — actual value is 50.67%, which should round to 50.7% or 51% depending on convention. Minor, but 50.7% would be more precise.

### AE4. Test suite count: 804/128 split doesn't add up

The itemized module counts sum to **808** raw test functions (not 804) and **124** parametrized expansions (not 128). The total 808 + 124 = 932 is correct, but the stated split "804 test functions plus 128 parametrized expansions" is internally inconsistent with the module-by-module breakdown.

### AE5. MLCommons coverage claim

Section 6.2 claims "5 of 13 MLCommons categories strongly," but Table 7 lists only **4** categories as "Strong" (S1, S9, S10, S11). The text tries to justify this by mentioning harassment and harmful content "joining the 100% tier," but Table 7 itself doesn't label them as "Strong."

---

## Questions for Authors

### Q1. What happens when H is just below the hard override threshold?

For H = 0.68 (just below 0.70), the hard override doesn't fire. With α = 10 and θ = 0.40, the gate term is σ(10(0.40 - 0.68)) = σ(-2.8) ≈ 0.057. So S ≈ 0.057 × (quality term), which will almost certainly be below 0.3, triggering safe_freeze anyway through the S-score path. But have you verified this for all mode profiles? With θ = 0.55 (relaxed), the gate term is σ(10(0.55 - 0.68)) = σ(-1.3) ≈ 0.214 — still low but potentially above 0.3 when multiplied by a high quality term. Is there a gap between θ = 0.55 and the hard override at 0.70?

### Q2. How does the system handle adversarial inputs designed to exploit the anchor set?

If an attacker knows the 249 anchors (the code is open-source), can they craft inputs that are semantically harmful but distant from all anchors? The unknown-territory detection (Section 3.4) addresses this partially, but only for inputs far from ALL anchors. What about inputs close to benign anchors but expressing harm through novel framing?

### Q3. What is the false positive rate on real-world benign Arabic text?

The 22 dialect test cases cover hyperbole, but real Arabic conversations include far more variety. Has the system been tested on a corpus of naturally-occurring Arabic text (e.g., social media, customer service) to measure the operational false positive rate? A 4.2% FP rate on 24 benign cases is not a reliable estimate.

### Q4. Why was the full S equation not evaluated on HarmBench/MultiJail?

The benchmarks only test the H scorer in isolation. The S equation combines H, I, and E. If you claim the multiplicative structure is the core contribution, the evaluation should test the full equation, not just one of its three inputs. What happens when HarmBench prompts are scored through the complete S equation?

### Q5. How do the 73 conjectures relate to grounded theory methodology?

The paper cites Glaser & Strauss (1967) but doesn't describe a systematic methodology for conjecture derivation. Grounded theory requires theoretical sampling, constant comparison, and theoretical saturation. Were these procedures followed? Without methodological detail, "73 conjectures from observing 4 platforms" is informal observation, not grounded theory.

### Q6. How does the system perform on adversarial jailbreak benchmarks?

Law Ξ detects jailbreak patterns, but modern jailbreaks use obfuscation (Base64, character substitution, language mixing) that pattern matching would miss. Has the system been tested against adaptive adversaries like those in HarmBench's attack suite?

---

## Minor Issues

### Formatting & Style

1. **Abstract is too long.** At ~350 words, it exceeds typical conference limits (150-250 words). The abstract tries to describe the entire system; it should focus on the core claim and key result.

2. **Paper length.** The paper is approximately 15 pages of content plus references. ACL/EMNLP main conference papers are typically 8 pages + references. Significant trimming is needed, and the R equation (Section 3.8), domain protocols detail (Section 3.9), and maqam chain (Section 4.3) are candidates for appendix material.

3. **Arabic romanization.** The paper uses ad-hoc romanization (e.g., "ḥarārat al-kalima," "al-niyya"). For a paper claiming Arabic-first design, proper Arabic script (compiled with XeLaTeX) would strengthen credibility. The comment on line 18-20 acknowledges this is a portability choice, but it weakens the Arabic-first framing.

### Writing

4. **Line 66:** "Architected Adaptive Thoughts & Intelligence Frameworks" — the acronym expansion feels forced and doesn't appear elsewhere in the paper. The Arabic etymology (عاطف) is more natural and compelling.

5. **Section 4.3 (Maqam chain):** This section is intellectually interesting but contributes nothing testable to the system. The duress detection application is described as future work. Consider moving to appendix or a separate essay.

6. **"The Architect" framing** (Sections 3.4, 4.3): References to "the Architect's framing" break the academic register. In a peer-reviewed paper, attribute ideas to the author or to specific prior work, not to a persona.

7. **Line 500-501:** The defense of a false positive as aligned with "'aṭf (compassionate inclination)" is a values statement, not a technical justification. A reviewer will read this as rationalization of a system limitation.

### Technical

8. **Top-K aggregation (K=3):** The choice of K=3 is unexplained. Was K=1, K=5, K=10 tested? How sensitive are the results to K?

9. **bge-m3 version and configuration:** The paper mentions "bge-m3 via Ollama" but doesn't specify the model version, embedding dimension, or quantization. Reproducibility requires this detail.

10. **Hysteresis controller (580 lines, Section 3.3):** The seven-rule priority system is complex. Is there evidence that the hysteresis controller improves outcomes compared to simple threshold-based decisions? This is another missing ablation.

---

## Specific Focus Areas Requested

### On the S Equation and Non-Compensability Proof

الـ non-compensability ليس "proof" بالمعنى الرياضي — هو ملاحظة بنيوية عن الضرب. أي نموذج ضربي (multiplicative model) يملك نفس الخاصية: إذا أحد العوامل يقترب من صفر، الناتج يقترب من صفر. هذا صحيح ولكنه trivial.

السؤال الأهم الذي لا تجيب عليه الورقة: **هل الـ non-compensability تحدث فرقاً عملياً؟** هل هناك حالات حقيقية حيث النظام الضربي يرفض مدخلاً والنظام الجمعي يقبله؟ بدون هذا الإثبات التجريبي، الادعاء يبقى نظرياً.

The paper should include: (1) concrete examples where additive S = aH + bI + cE fails and multiplicative S succeeds, (2) a quantitative comparison on the calibration set, and (3) analysis of whether the "toxic positivity" attack vector (polite harmful prompts) actually occurs in HarmBench/MultiJail.

### On the Arabic-First Framing

الإطار العربي-أولاً يعاني من مشكلتين:

1. **Performance doesn't support it.** English outperforms Arabic on MultiJail (90.7% vs 88.0%). The paper's own conclusion is that multilingual embeddings equalize the languages.

2. **The "meaning density hypothesis" is untested.** The paper devotes a full subsection (4.1) to arguing Arabic has higher meaning density, then immediately says there's no evidence embeddings preserve this. This is speculation wearing the clothes of a hypothesis.

The dialect hyperbole work (Section 4.2) is the one genuinely Arabic-specific contribution. It's solid but narrow — 35 anchors and 22 test cases. This would be better framed as "a safety system with Arabic dialect awareness" rather than "Arabic-first."

### On the Benchmark Methodology

المنهجية ضعيفة لمؤتمر من المستوى الأول:

1. **Only the H scorer is benchmarked.** The full S equation, the governance pipeline, the output gate — none of these are evaluated on standardized benchmarks.

2. **No baselines.** Without running alternative systems on the same inputs, the numbers float without context.

3. **Small scale.** 54 calibration cases, 56 contaminated held-out cases. For comparison, FanarGuard trained on 468K examples. AATIF's evaluation surface is approximately 0.1% of FanarGuard's.

4. **Arithmetic errors in the main results table** (see AE1 above) undermine confidence in the reported numbers.

### On the Field Notes

The 73 conjectures and 78 field notes are mentioned as supplementary material but their methodological status is unclear:

- Are they systematically derived observations or informal journaling?
- The paper cites grounded theory (Glaser & Strauss, 1967) as precedent, but doesn't describe following grounded theory methodology.
- Only one conjecture (#063) is operationalized in this paper. The others are mentioned to contextualize the research program but don't contribute to the technical claims.

For a conference paper, this is fine as motivation. But the paper gives the field notes more weight than they can bear — they're presented as a research methodology when they function as a research diary. The distinction matters if the paper claims inductive derivation.

---

## Assessment Summary

### ماذا تحتاج الورقة لتكون مقبولة في مؤتمر؟

1. **Truly blind evaluation.** 500+ cases, never seen during any design decision, with inter-annotator agreement.

2. **Baseline comparisons.** Run Llama Guard 3, Perspective API, and (if accessible) FanarGuard on the same HarmBench/MultiJail inputs. Show where AATIF wins and where it loses.

3. **Ablation study.** H-only, I-only, E-only, H+I, H+E, multiplicative vs. additive. Prove each component earns its place.

4. **Fix the arithmetic.** Table 4 summary rows must match detail rows. Explain the /73 denominator in Table 5.

5. **Narrow the scope.** The paper tries to contribute: a safety equation, a governance pipeline, Arabic dialect handling, a meaning density hypothesis, a maqam-to-safety narrative, a field note methodology, and a 932-test engineering system. Pick 2-3 and do them at full depth. The pipeline, R equation, output gate, and maqam sections should be appendix material.

6. **Reframe "Arabic-first" to "Arabic-aware."** The results don't support "first" — they support "capable."

7. **Reframe "zero training data" to "zero fine-tuning."** Acknowledge that anchor curation is a form of supervised design.

### The honest bottom line

هذه ورقة فيها أفكار حقيقية ومميزة — المعادلة الضربية، التعامل مع المبالغة العامية، والصدق الاستثنائي في عرض المحدودات. لكنها ليست جاهزة لمؤتمر من المستوى الأول لأن:

- التقييم أصغر بكثير مما يُتوقع
- لا توجد مقارنات مع أنظمة أخرى على نفس البيانات
- الادعاءات أكبر مما تدعمه الأدلة
- الورقة تحاول تغطية مساحة واسعة جداً بعمق غير كافٍ

The work is genuine, the system is real, and the ideas have merit. But the evaluation bar for a top NLP venue is higher than what's presented here. I would encourage resubmission after addressing the blind evaluation, baselines, and ablation gaps.

**كملاحظة شخصية للمعمري:** الصدق اللي في الورقة هذي نادر — أغلب الباحثين يخبون محدودياتهم. أنت عرضتها بوضوح وهذا يُحسب لك. لكن الصدق في وصف المشاكل لا يُعفي من حلها. الورقة تحتاج عمل إضافي حقيقي على الـ evaluation قبل ما تقدر تنافس.

---

*Review conducted: 2026-06-25 / 2026-06-26 03:48 UTC (06:48 Riyadh)*  
*Reviewer: Claude Opus 4.6 (acting as NLP conference reviewer)*  
*Methodology: Full paper read + arithmetic verification + structural analysis*
