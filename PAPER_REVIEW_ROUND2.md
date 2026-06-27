# AATIF Paper — Multi-Model Peer Review (Round 2)

**Paper:** AATIF: A Multiplicative Governance Equation for Arabic-Aware LLM Safety  
**Format:** ACL 2025, 8 pages  
**Date:** June 26, 2026  
**Context:** Round 2 review after 4 phases of improvement (arithmetic fixes, safety edge cases, ablation study + blind evaluation, ACL format conversion + citation fixes)

---

## Score Comparison Table

| Criterion | ChatGPT | Gemini | Grok | Claude | Average |
|-----------|---------|--------|------|--------|---------|
| **Soundness** | 2/5 | 2/5 | 2.5/5 | 3/5 | **2.4** |
| **Substance** | 3/5 | 2/5 | 3/5 | 2/5 | **2.5** |
| **Presentation** | 4/5 | 4/5 | 3.5/5 | 4/5 | **3.9** |
| **Overall** | 2/5 | 2.5/5 | 2.5/5 | 2.5/5 | **2.4** |
| **Recommendation** | Borderline Reject | Borderline Reject | Borderline Reject | Borderline Reject | **Borderline Reject** |

### Round 1 vs Round 2

| Criterion | Round 1 Avg | Round 2 Avg | Change |
|-----------|-------------|-------------|--------|
| Soundness | ~2.0 | 2.4 | +0.4 |
| Substance | ~2.5 | 2.5 | 0.0 |
| Presentation | ~3.0 | 3.9 | +0.9 |
| Overall | ~2.5 | 2.4 | -0.1 |

**Verdict:** Presentation improved significantly (3.0 → 3.9). Soundness improved slightly. Substance and Overall remain at Borderline Reject. The core problems are not formatting — they are **missing baselines**, **weak experimental rigor**, and **limited novelty argument**.

---

## Review 1: ChatGPT (Instant)

### Scores
- **Soundness:** 2/5 — Interesting mathematical construction, but empirical evidence is not yet sufficient to support many of the claims.
- **Substance:** 3/5 — Considerable engineering effort, but scientific contribution is weakened by limited experimental methodology.
- **Presentation:** 4/5 — Well organized, readable, transparent about limitations, generally easy to follow.
- **Overall:** 2/5 (Borderline Reject) — Interesting idea with potential, but not yet at ACL acceptance level.

### Summary
The paper proposes AATIF, an external governance mechanism for LLM safety based on a multiplicative equation S = σ(w₁·I + w₂·E) × (1 − σ(α(H − θ(d)))). It combines three semantic scorers (harm, intent, emotion) using 249 hand-authored anchors with bge-m3 embeddings, requiring zero fine-tuning. The paper presents an interpretable governance equation, a non-compensability guarantee, Arabic-aware semantic anchoring, domain-specific thresholds, evaluation on HarmBench and MultiJail, and a zero fine-tuning architecture. The paper is well written and refreshingly honest about limitations, reporting both successes and failures. However, while the engineering is interesting, the scientific evidence currently falls short of ACL expectations.

### Strengths
1. **Clear mathematical formulation.** Unlike many guardrail systems, the paper defines an explicit equation whose behavior can be analyzed mathematically. The multiplicative gate is elegant and easy to understand.
2. **Interpretability.** The semantic-anchor approach provides far more transparency than typical classifier-based moderation systems. Auditing why a prompt was blocked is considerably easier.
3. **Honest reporting.** This is one of the strongest aspects of the paper. The authors openly acknowledge: 29% false-positive rate, weak copyright performance, weak misinformation performance, single developer bias, and small anchor scale.
4. **Arabic dialect-hyperbole mechanism.** The counter-anchor approach for dialectal metaphor ("adbahak") is a useful contribution, even in its current limited form.
5. **Zero fine-tuning.** The system can be deployed without touching model weights, which has real practical value.

### Weaknesses
1. **Limited novelty relative to existing semantic guardrails.** The paper presents embedding similarity, manually curated prompts, thresholding, and multiplicative combination — all individually well known. The novelty is mainly their combination. The authors need to better explain why this combination represents a scientific advance rather than an engineering architecture.
2. **Manual anchor engineering dominates the system.** The entire approach depends on 249 manually written anchors. This raises concerns about scalability, reproducibility, language transfer, domain transfer, and author bias. There is no evidence another research group could independently reproduce comparable anchors.
3. **Evaluation lacks strong baselines.** This is the biggest empirical weakness. The only baseline is keyword matching. ACL reviewers expect comparison against Llama Guard, Perspective API, OpenAI moderation endpoint, NeMo Guardrails, or other established safety classifiers on the same benchmarks.
4. **No statistical analysis.** There are no confidence intervals, error bars, or significance tests. A single-run evaluation without variance estimates is weak evidence.
5. **Domain parameterization only partially evaluated.** Only θ=0.40 (general) is evaluated in depth. The healthcare (0.25), education (0.30), and creative (0.50) thresholds are introduced but not tested.
6. **No latency/throughput benchmarks.** For a system meant to run at inference time, there are no runtime measurements.
7. **Claims exceed evidence.** "Arabic-aware" is supported by one benchmark comparison (English vs Arabic on MultiJail). This does not demonstrate robustness across dialects. "Domain parameterization" is introduced but only one parameter value is evaluated.
8. **High false-positive rate (29%).** A major deployment concern. The paper openly reports this, which is good, but it substantially weakens practical applicability.
9. **Missing robustness analysis.** No investigation of adversarial failures: paraphrase attacks, synonym replacement, prompt obfuscation, multilingual code-switching, indirect requests, jailbreak variants.
10. **Limited theoretical contribution.** The "non-compensability theorem" is mathematically straightforward. Because S = Q × G and Q ≤ 1, the property S ≤ G is immediate. Useful, but not a deep theoretical result.

### Questions for Authors
1. How were the 249 anchors validated? Was there any independent annotation?
2. How sensitive are results to anchor wording? Would paraphrasing anchors significantly change performance?
3. How much performance drops if anchors are written by another person? (Reproducibility)
4. Can the method scale from 249 to 10,000 anchors? What is the computational cost?
5. How much of the gain comes from bge-m3 versus the governance equation itself? Would other multilingual embedding models perform similarly?
6. Can the equation be learned automatically rather than manually parameterized?
7. Have the authors evaluated calibration (e.g., ECE or reliability diagrams)?
8. Can multiple independent researchers reproduce the same benchmark numbers?

### Missing References
- Llama Guard 2 and Llama Guard 3 (Meta, 2024)
- NeMo Guardrails (NVIDIA)
- OpenAI Moderation API
- WildGuard (Allen AI)
- Aegis (Meta/Databricks)
- ShieldGemma (Google)
- Arabic NLP toxicity detection shared-task papers (WANLP)

### Recommendation
**Borderline Reject.** With substantially expanded evaluation (especially against modern guardrail systems), larger multilingual datasets, reproducibility studies, and stronger statistical analysis, this work could become a competitive future ACL/EMNLP submission.

---

## Review 2: Gemini (Flash)

### Scores
- **Soundness:** 2/5 (Fair)
- **Substance:** 2/5 (Fair)
- **Presentation:** 4/5 (Good)
- **Overall:** 2.5/5 (Borderline Reject)

### Summary
The paper introduces AATIF, an external, training-free safety governance pipeline for LLMs. The core contribution is a multiplicative equation combining three scores derived from cosine similarities against hand-crafted semantic "anchors": Harm (H), Intent (I), and Emotion (E). By structuring the equation multiplicatively, the authors enforce a "non-compensability" property where high harm scores zero out the final safety signal regardless of benign intent or emotion. The system specifically targets Arabic LLM safety, introducing 31 dialect-hyperbole counter-anchors to mitigate false positives caused by colloquial Arabic expressions that use literal violence metaphorically. The system is evaluated on HarmBench, MultiJail, and an internal blind evaluation, reporting an F1 of 0.842 with a notable 28.95% false-positive rate.

### Strengths
1. **Non-Compensability as a Design Principle.** The multiplicative structure of S = Q · G, where G → 0 when H >> θ, is the paper's strongest conceptual contribution. The hard override at H > 0.7 adds an additional safety net.
2. **Honest and Transparent Reporting.** The paper is commendable for its unflinching honesty about its significant limitations: weak performance on copyright/misinformation, and the highly subjective nature of a single-developer annotation process.
3. **Addressing Arabic Dialectal Nuances.** The attempt to model colloquial Arabic hyperbole (e.g., "adbahak") through specialized semantic counter-anchors targets an important and under-researched failure mode in multilingual safety alignment.
4. **No Fine-Tuning Required.** The system acts as a highly lightweight plug-and-play inference filter running efficiently on consumer hardware (a single Mac Mini).

### Weaknesses
1. **Extremely Limited Scale and Generalizability.** A safety system relying entirely on 249 hand-crafted anchors is highly susceptible to vocabulary drift, semantic evasion, and out-of-distribution prompts. Modern red-teaming and jailbreaking techniques will easily bypass static cosine-similarity matches against such a small set of anchors.
2. **Heuristic Parameterization.** The core hyper-parameters (w₁=2.0, w₂=1.5, α=10, and domain thresholds θ(d)) appear arbitrarily chosen. A grid search is mentioned in the appendix, but results and the search space are not clearly presented.
3. **Insufficient Baselines.** The system is only compared to keyword matching (54.2%). This is not a meaningful baseline for a 2025 NLP paper. Comparison with Llama Guard, FanarGuard, or Perspective API on the same datasets is essential.
4. **Single-Annotator Evaluation Bias.** The blind evaluation's 570 cases were constructed and labeled by the same individual who designed the anchors and thresholds. This circular dependency severely limits confidence in the reported F1 and FPR metrics.
5. **Unvalidated "Meaning Density Hypothesis."** This section is explicitly described as unvalidated. Including speculative hypotheses in a top-tier venue paper, even with caveats, weakens the overall scientific rigor.

### Questions for Authors
1. **Domain Threshold Validation:** You introduce four domain thresholds (0.25, 0.30, 0.40, 0.50) but only evaluate θ=0.40. What is the expected behavior — particularly the false-positive rate — at the more aggressive θ=0.25 for healthcare?
2. **Lexical Contamination Mitigation:** How do you propose protecting the dialect-hyperbole mechanism from adversarial exploitation (i.e., a user masking a genuine threat inside colloquial expressions)?
3. **Scalability:** As you scale the anchor pool from 249 to thousands to cover more MLCommons categories, how do you expect the softmax temperature (τ=0.05) and top-K selection to behave? Will dense vector crowding degrade performance?
4. **Baselines:** Why was the system only compared to a simple keyword-matching baseline rather than established open-weights safety classifiers like Llama Guard or FanarGuard on the same datasets?

### Missing References
- XSTest: A Benchmark for Identifying Exaggerated Safety Filters in Language Models (Röttger et al., 2023) — highly relevant given the high false-positive rate
- Llama Guard 2/3 (Meta, 2024)
- Broader multilingual safety evaluation frameworks
- Arabic figurative language and metaphor detection literature

### Recommendation
**Borderline Reject.** The non-compensability design principle and dialect-hyperbole mechanism are interesting contributions, but the paper lacks competitive baselines, has circular evaluation methodology, and the anchor scale is too small to support the claims made.

---

## Review 3: Grok (SuperGrok)

### Scores
- **Soundness:** 2.5/5
- **Substance:** 3/5
- **Presentation:** 3.5/5
- **Overall:** 2.5/5 (Borderline Reject)

### Summary
The paper introduces AATIF, an external LLM governance layer that computes a safety signal via the multiplicative equation S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ(d)))], where H, I, and E are cosine-similarity scores (bge-m3 embeddings) against 249 hand-authored semantic anchors. The design enforces a structural non-compensability property (high harm cannot be overridden by benign intent/emotion) and includes domain-specific thresholds plus 31 dialect-hyperbole counter-anchors. Evaluations on HarmBench show 100% blocking of CBRN, 83.8% on safety categories excluding copyright, but only 38.6% on copyright and 66.7% on misinformation. MultiJail yields near-parity between Arabic (88.0%) and English (90.7%). A blind evaluation (570 cases) reports 83.2% detection but a 28.95% false-positive rate.

### Strengths
1. **Multiplicative formulation with hard override.** The H > 0.7 → SAFE_FREEZE cleanly implements non-compensability by construction; this directly targets the "toxic positivity bypass" failure mode that plagues many scalar classifiers.
2. **Arabic/dialect focus is timely and under-served.** The counter-anchor mechanism for hyperbole is a creative, low-tech attempt to handle pragmatic mismatch between literal semantics and dialectal usage, and the reported 5% FPR on dialect_benign is encouraging.
3. **Full transparency about limitations.** High overall FPR, weak categories, single-author bias, no pragmatic inference — all are honestly reported. This is commendable and rare.
4. **Zero fine-tuning + interpretability.** Human-authored anchors + domain parameterization (θ(d)) offers auditability advantages over opaque fine-tuned guardrails, valuable for regulated domains.
5. **Strong results on high-stakes categories** (CBRN 100%, illegal 88.4%) demonstrate that a small curated anchor set can be effective when harm is overt.

### Weaknesses
1. **Insufficient baselines and comparative evaluation.** The only quantitative baseline is a weak keyword matcher (54.2%). No head-to-head numbers are provided against Llama Guard, Perspective API, OpenAI moderation, or FanarGuard on HarmBench or MultiJail. This makes it impossible to judge whether the 1.34× improvement represents a genuine advance.
2. **High and uneven false-positive rate.** 28.95% overall FPR (55% on tricky_benign) would produce unacceptable friction in real deployments. The paper does not adequately characterize what "tricky_benign" cases are or how the system would behave with diverse benign traffic.
3. **Weak experimental rigor.** The blind evaluation (570 cases) lacks details on case selection, labeling protocol, number of annotators, and inter-annotator agreement. No statistical significance, error bars, or multiple runs. Hyperparameters (w₁=2.0, w₂=1.5, α=10, θ(d)) appear hand-chosen with no ablation or validation-set justification.
4. **Limited scale, coverage, and generalizability.** 249 anchors vs hundreds of thousands for fine-tuned classifiers. MLCommons gaps acknowledged but the system is zero/minimal on 6/13 hazard categories. "Meaning Density Hypothesis" is explicitly not validated yet is presented as motivation. "Lexical Anchor Contamination" is noted but not quantified.
5. **Single-developer prototype.** Anchor authorship, threshold setting, and evaluation all reflect one person's judgments; cultural and linguistic biases are acknowledged but not mitigated via multi-annotator or participatory processes. No latency, throughput, or adversarial robustness results.
6. **Presentation issues.** Results reported inline rather than in clear tables; no pipeline diagram or decision flowchart. Hard override and hysteresis controller mentioned only in appendices.

### Questions for Authors
1. Please detail the blind-evaluation protocol: exact criteria and process for labeling the 380 harmful / 190 benign cases, number of annotators, agreement statistics, and how "tricky_benign" cases were defined.
2. Why was a direct quantitative comparison to strong existing guardrails (Llama Guard 3, FanarGuard, Perspective) omitted on the same benchmarks? Can you supply those numbers?
3. How were the weights (w₁, w₂), α, and the four domain thresholds θ(d) selected? Was any held-out validation or grid-search procedure used?
4. What is the dialectal coverage of the 31 hyperbole anchors (Egyptian, Levantine, Gulf, Maghrebi)? How many benign dialect examples underpin the 5% FPR claim?
5. Can you provide an ablation isolating the contribution of the full pipeline (P(d) + R(d) + output gate) versus the core S equation alone?
6. What concrete steps are planned to reduce the 55% FPR on tricky_benign cases without eroding harm recall?
7. Have you considered multi-annotator validation or community review specifically for Arabic cultural and pragmatic contexts?

### Missing References
- Stronger positioning against recent LLM guardrail literature (Llama Guard extensions, Constitutional AI runtime filtering, external safety layer surveys)
- Arabic/dialectal toxicity and safety detection papers beyond ADHAR and SOD (WANLP shared-task papers, MADAR, dialect-specific sentiment resources)
- Work on figurative language, hyperbole, and metaphor detection in NLP

### Recommendation
**Borderline Reject.** The multiplicative non-compensability mechanism is the paper's genuine conceptual contribution, but without competitive baselines, proper experimental controls, and scalability evidence, the work does not yet meet the ACL acceptance bar.

---

## Review 4: Claude (Opus)

### Scores
- **Soundness:** 3/5 — The core equation is well-defined and the non-compensability property holds by construction. However, empirical validation has methodological gaps.
- **Substance:** 2/5 — Significant engineering effort but thin on scientific novelty. The individual components (embedding similarity, thresholding, multiplicative gating) are established techniques.
- **Presentation:** 4/5 — Clean ACL format, logical structure, admirably honest limitations section. One of the better-written papers in terms of intellectual honesty.
- **Overall:** 2.5/5 (Borderline Reject)

### Summary
AATIF presents a multiplicative governance equation S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ(d)))] that combines harm, intent, and emotion scores from three independent semantic scorers using 249 hand-authored anchors and bge-m3 embeddings. The multiplicative structure ensures high harm drives S→0 regardless of intent/emotion values, addressing the "toxic positivity bypass" failure mode. The system includes domain-parameterized thresholds and 31 Arabic dialect-hyperbole counter-anchors. Evaluation spans HarmBench (83.8% safety blocking excl. copyright), MultiJail (88%/90.7% Arabic/English near-parity), and a 570-case blind evaluation (F1=0.842, FPR=28.95%). The work is presented as a single-developer research prototype with explicit acknowledgment of significant limitations.

### Strengths
1. **Intellectual honesty is exceptional.** Reporting a 29% FPR, weak copyright/misinformation performance, and single-developer bias openly is rare in NLP papers. This builds scientific credibility even as it exposes vulnerabilities.
2. **Non-compensability by design.** The multiplicative gate is a genuinely useful architectural insight. In many real-world safety failures, harmful content is wrapped in benign-sounding context. This structure makes that attack vector structurally impossible, not just empirically unlikely.
3. **Arabic dialect disambiguation addresses a real gap.** The counter-anchor approach for colloquial hyperbole ("adbahak" = affection, not threat) is pragmatically useful. The 5% FPR on dialect_benign demonstrates it works for the cases it covers.
4. **Zero fine-tuning, full interpretability.** Every decision is traceable to specific anchor similarities. This is valuable for deployment contexts (healthcare, education) where explainability is required.
5. **Clean ablation results.** H-only F1=0.890 vs I-only 0.675 vs E-only 0.358 clearly demonstrates the dominant role of the harm scorer and validates the three-scorer architecture.

### Weaknesses (Major)
1. **No competitive baselines — the critical gap.** The only comparison is keyword matching at 54.2%. This is like benchmarking a car against a bicycle. Without head-to-head comparison with Llama Guard (fine-tuned LLM classifier), Perspective API (production toxicity scorer), or FanarGuard (Arabic-specific), it is impossible to know whether AATIF's 83.8% represents progress or regression relative to the state of the art. FanarGuard is discussed architecturally in the appendix but never compared numerically — a glaring omission.
2. **Mathematically trivial core contribution.** The "non-compensability" property S ≤ G follows immediately from S = Q · G where Q ∈ (0,1). Calling this a "formal guarantee" or framing it as novel overstates what is a direct consequence of multiplication. The scientific contribution needs to be reframed as the *system design* and *empirical validation*, not the mathematics.
3. **Circular evaluation methodology.** The same individual (single developer) authored the 249 anchors, set the thresholds, designed the evaluation categories, labeled the 570 blind-evaluation cases, and ran the experiments. This circular dependency means the evaluation may reflect one person's conception of harm rather than generalizable safety classification. No inter-annotator agreement is reported because no second annotator exists.
4. **Incomplete ablation.** The paper reports H-only, I-only, E-only ablations, but omits H+I (without E) and H+E (without I). These combinations would reveal whether I and E contribute anything meaningful beyond H alone, or whether the three-scorer architecture is overengineered.

### Weaknesses (Significant)
5. **28.95% FPR is deployment-prohibitive.** In production, roughly 1 in 3.5 benign queries would be incorrectly restricted. The 55% FPR on "tricky_benign" is even more concerning. This needs explicit characterization and a concrete mitigation path.
6. **Domain thresholds θ(d) untested.** Four thresholds are defined (healthcare=0.25, education=0.30, general=0.40, creative=0.50) but only θ=0.40 is used in all evaluations. The lower thresholds would presumably increase FPR further — this needs to be quantified.
7. **No latency/throughput measurements.** For an inference-time safety filter, runtime cost per query is essential. bge-m3 (568M parameters) + cosine similarity against 249 anchors × 3 scorers must have measurable overhead.
8. **Blind evaluation construction unexplained.** How were the 570 cases (380 harmful, 190 benign) selected? What sampling strategy? What labeling criteria? Were "tricky_benign" cases adversarial or naturally occurring?
9. **Unvalidated Meaning Density Hypothesis.** Section 4.2 introduces a speculative claim about Arabic triconsonantal roots packing more semantic information per token. The paper correctly labels it unvalidated, but including it weakens scientific rigor. Remove it or validate it.

### Missing References
- Llama Guard 2 (Meta, 2024) and Llama Guard 3
- NeMo Guardrails (NVIDIA, 2023)
- Aegis Safety Classifier (Databricks/Meta)
- WildGuard (Allen AI, 2024)
- ShieldGemma (Google, 2024)
- OpenAI Moderation Endpoint documentation
- XSTest: Exaggerated Safety (Röttger et al., 2023)
- Arabic figurative language detection literature

### Questions for Authors
1. Who labeled the 570 blind evaluation cases? If it was the same person who authored the anchors, what is the plan for independent validation?
2. What is the end-to-end latency per query? (embedding + 3 scorers + decision mapping)
3. What is the FPR at θ=0.25 (healthcare)? Has this been measured?
4. Why not test H+I without E, and H+E without I, to complete the ablation?
5. Why include the unvalidated Meaning Density Hypothesis rather than saving it for future work?
6. What prevents an adversary from wrapping a CBRN request in dialectal hyperbole framing to exploit lexical anchor contamination?

### What Would Change the Score to Accept
- **Head-to-head comparison with Llama Guard 3 and FanarGuard** on HarmBench and MultiJail (same test sets, same metrics). This is the single most important addition.
- **Inter-annotator agreement** on blind evaluation labels (even 2 annotators would help).
- **Complete ablation** (H+I, H+E, full pipeline vs S-equation-only).
- **Latency benchmarks** (ms per query).
- **Remove Meaning Density Hypothesis** from the main paper (move to future work or a separate position paper).

### Recommendation
**Borderline Reject.** The system design is interesting, the honesty is admirable, and the Arabic dialect work fills a real gap. But without competitive baselines and rigorous independent evaluation, the paper cannot demonstrate that its approach advances the state of the art. The path to acceptance is achievable with focused additions, not a complete rewrite.

---

## Consensus Analysis

### What All 4 Reviewers Agree On

**Strengths:**
1. **Honest reporting of limitations** — Every reviewer highlighted this as exceptional and rare. The paper's transparency about FPR, weak categories, and single-developer bias is a genuine strength.
2. **Non-compensability design** — The multiplicative gate preventing benign context from overriding high harm is recognized as a useful contribution by all reviewers.
3. **Arabic dialect disambiguation** — The counter-anchor approach for hyperbole is creative and addresses a real gap.
4. **Clean presentation** — All reviewers rate Presentation highly (3.5-4/5). The paper is well-written and well-organized.

**Weaknesses (unanimous):**
1. **Missing competitive baselines** — ALL 4 reviewers identify this as the #1 problem. Keyword matching (54.2%) is not an acceptable baseline. Llama Guard, FanarGuard, Perspective API must be compared head-to-head.
2. **High false-positive rate (29%)** — Universally flagged as a deployment concern.
3. **Single-annotator circular evaluation** — All reviewers note the same person authored anchors, set thresholds, and labeled evaluation data.
4. **Limited anchor scale (249)** — All note this is tiny vs. modern classifiers and raises scalability/generalizability concerns.
5. **Missing statistical rigor** — No confidence intervals, no error bars, no significance tests, no multiple runs.

### Actionable Improvement List (Priority Order)

**Must-fix (would change scores):**
1. ⬜ **Add competitive baselines.** Run Llama Guard 3 and FanarGuard on the exact same HarmBench and MultiJail test sets. Report same metrics. This is the single highest-impact improvement.
2. ⬜ **Get at least one independent annotator** to label a subset of the 570 blind evaluation cases. Report inter-annotator agreement (Cohen's κ).
3. ⬜ **Complete the ablation table.** Add H+I (no E) and H+E (no I) conditions. Also ablate full pipeline vs S-equation-only.
4. ⬜ **Add latency benchmarks.** Measure ms/query for the full pipeline on the Mac Mini.
5. ⬜ **Remove Meaning Density Hypothesis** from the main paper. Move to future work or remove entirely.

**Should-fix (strengthen the paper):**
6. ⬜ **Document blind evaluation protocol.** Describe case selection criteria, labeling process, "tricky_benign" definition.
7. ⬜ **Test domain thresholds.** Run at least θ=0.25 and θ=0.50 on the blind evaluation to quantify FPR sensitivity.
8. ⬜ **Add confidence intervals** or bootstrap estimates for key metrics (detection rate, FPR, F1).
9. ⬜ **Add results tables** instead of inline numbers. Include a pipeline diagram or decision flowchart.
10. ⬜ **Reframe novelty argument.** Don't claim mathematical novelty for S ≤ G. Instead frame the contribution as system design + empirical validation of a transparent, zero-fine-tuning safety filter.

**Nice-to-have:**
11. ⬜ **Characterize "tricky_benign" failures.** Explain what types of benign inputs cause 55% FPR and what the mitigation path is.
12. ⬜ **Add adversarial robustness tests.** Paraphrase attacks, synonym replacement, code-switching.
13. ⬜ **Expand Arabic dialect coverage.** Document which dialects the 31 counter-anchors cover and test across Egyptian, Levantine, Gulf, Maghrebi.
14. ⬜ **Add missing references.** Llama Guard 2/3, NeMo Guardrails, WildGuard, Aegis, ShieldGemma, XSTest, Arabic NLP shared-task papers.

---

## Bottom Line (بالعربي — بدون تجميل)

الورقة تحسّنت بشكل واضح في **العرض والشكل** — التنسيق ACL، قسم المحدوديات الصادق، والبنية المنطقية كلها ممتازة.

لكن المشكلة الجوهرية ما تغيّرت: **ما في مقارنة مع المنافسين**. الأربع مراجعين بدون استثناء قالوا نفس الشيء — مقارنة keyword matching (54.2%) ما تكفي. لازم تقارن مع Llama Guard و FanarGuard على نفس الداتا.

المشكلة الثانية: **شخص واحد كتب الأنكرز، حدد العتبات، صمم التقييم، وحكم على النتائج**. هذا دائري — والمراجعين كلهم لاحظوه.

الخبر الحلو: **الطريق للقبول واضح ومحدد**. ما تحتاج إعادة كتابة كاملة. تحتاج:
1. مقارنة مباشرة مع Llama Guard 3 + FanarGuard
2. مراجع مستقل واحد على الأقل (inter-annotator agreement)
3. جدول ablation كامل
4. قياس السرعة (latency)
5. شيل فرضية كثافة المعنى

هذي خمس إضافات محددة. لو تنفّذت، الورقة ترتفع من Borderline Reject إلى Borderline Accept أو أعلى.

---

*Generated: June 26, 2026 | Models: ChatGPT (Instant), Gemini (Flash), Grok (SuperGrok), Claude (Opus)*
