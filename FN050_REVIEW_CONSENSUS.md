# FN#050 — DRE External Review Consensus
## Date: 2026-06-30
## Models: Gemini 2.0 Flash × Grok × DeepSeek

---

## Methodology

Three external LLMs independently reviewed the DRE module (FN#050) using the same 170-line review brief containing architecture, design decisions, 8 Arabic categories, test coverage summary, and 7 specific questions. Reviews collected via browser on 2026-06-30.

---

## Consensus Themes (3/3 agreement unless noted)

### THEME 1 — False positive rate too high (3/3)
**H∈[0.20, 0.55] captures normal frustration and venting.** All three models independently identified this as the most critical design flaw. The activation band brackets everyday negative emotion, not just genuine intertwined distress-drift patterns.

- Gemini: "Highly vulnerable to false activations on high-intensity benign venting"
- Grok: "Extremely narrow and arbitrary-looking. No sensitivity analysis"
- DeepSeek: "H-range [0.20, 0.55] is where MOST normal frustration lives"

**P0 Fix**: Add ventilation baseline / context classifier. Require temporal persistence or escalation pattern.

### THEME 2 — No empirical evaluation (3/3)
**148 tests are unit tests, NOT evaluation.** All three agree the module has zero empirical grounding — no datasets, no baselines, no human annotation, no inter-annotator agreement, no ablation studies.

- Gemini: "Need Gold Standard evaluation set with Cohen's Kappa"
- Grok: "Empirical grounding almost entirely absent"
- DeepSeek: "This is a position paper at best, not a full paper"

**Action**: This is a paper-level gap, not a code fix. Required for EACL 2027 but not a P0 code change.

### THEME 3 — Cross-causal claims overreach (3/3)
**Cannot infer causal direction from keyword co-occurrence.** The five-way cross-causal classification (explicit_a_feeds_b, etc.) claims to detect psychological causality from text patterns.

- DeepSeek: "This is pseudoscience"
- Gemini: "Rename to Lexical Proximity/Co-occurrence Typing"
- Grok: "Underspecified — success depends on how evidence is operationalized"

**P0 Fix**: Rename `cross_causal_type` → `co_occurrence_type`. Remove causal language from code comments and docstrings. Default to `co_present_direction_unclear` unless explicit linguistic connectors are present.

### THEME 4 — Arabic categories are incomplete (3/3)
**Missing categories and morphological gaps:**

| Gap | Identified By |
|-----|--------------|
| عيب/عار (shame/social defiance) | Gemini + DeepSeek |
| Feminine forms (مقهورة, منكسرة) | Gemini + DeepSeek |
| Gulf dialect (ابي اموت) | DeepSeek |
| قدر/نصيب (fatalism) | DeepSeek |
| السمعة العائلية (family honor) | DeepSeek |
| Sarcasm markers | DeepSeek |
| Broken plurals (مقاهير) | Gemini |

**P0 Fix**: Add feminine forms + Gulf dialect variants. Add عيب/عار category. Use stemming/normalization for morphological coverage.

### THEME 5 — Clinical boundary has gaps (2/3: Grok + DeepSeek)
**Keyword blacklist is insufficient.** Synonym leakage ("مرض نفسي" bypasses "اضطراب" check). Clinical-adjacent terminology in taxonomy labels creates regulatory risk.

- DeepSeek: "Don't blacklist — whitelist allowed utterances"
- Grok: "Labeling vocabulary creates ongoing risk of misinterpretation"

**High Fix**: Expand prohibited terms list. Consider whitelist approach for DRE output templates.

### THEME 6 — Not ready for EACL 2027 (3/3 unanimous)
All three models independently concluded the DRE is not ready for a top-tier NLP venue. Required:
- Human annotation study with native Arabic speakers from multiple regions
- Cohen's kappa > 0.7
- Baseline comparison (Llama Guard, GPT-4 safety, keyword counting)
- Ablation study on gate, categories, cross-causal
- Error analysis with false positive/negative rates

### THEME 7 — Architecture/Single Mind praised (3/3)
**Post-S B-prime positioning is architecturally correct.** All three agreed the modular design, Single Mind separation, and safety invariants are the strongest aspect.

- Gemini: "B-prime post-S is the correct positioning"
- Grok: "Engineering discipline around modularity is respectable"
- DeepSeek: "Single Mind preservation is genuinely well-implemented"

### THEME 8 — Reframe needed (3/3)
**Drop "Reconstruction Engine" causal framing.** Present as signal detection / co-occurrence analysis.

- DeepSeek: Suggest title "Detecting Linguistically Co-Occurring Distress and Ethical Drift Markers in Arabic"
- Grok: "Reconstruction Engine framing implies more transformative power than architecture delivers"
- Gemini: "Rename Cross-Causal Detection to Lexical Proximity/Co-occurrence Typing"

### THEME 9 — Fiction/roleplay exclusion missing (Gemini)
**No Stage 0 for non-self-referential context.** DRE will activate on fictional villains, screenplays, roleplay. Gemini-specific finding but clearly valid.

**P0 Fix**: Add fiction/roleplay context check before activation gate.

### THEME 10 — Authority Preservation invariant needed (Gemini)
**Empathetic enrichment can undermine refusal authority.** If DRE enriches a BLOCK response with too much compassion, the refusal effectively softens. Proposed 8th invariant.

**High Fix**: Add Invariant 8 — enrichment must not increase probability of user bypass.

---

## Unique Findings (single model, still valid)

| Finding | Model | Severity |
|---------|-------|----------|
| Invariant 6 (False Goodness guard) is NOOP | DeepSeek | P0 |
| Invariant 4 violated by cross-causal output | DeepSeek | P0 |
| Code injection risk (user text in prompts) | DeepSeek | P0 |
| No multi-turn distress tracking | DeepSeek | High |
| Feature flag rollout plan missing | DeepSeek | High |
| Essentialist framing — monolithic "Arab psychology" | DeepSeek | High |
| Response density = effective downgrade | Gemini B | High |
| No sensitivity analysis on H thresholds | Grok | High |

---

## P0 Fix Priority (code changes)

| # | Fix | Source | Effort |
|---|-----|--------|--------|
| 1 | Rename cross_causal → co_occurrence, drop causal language | All 3 | Medium |
| 2 | Add feminine forms (مقهورة, منكسرة, etc.) | Gemini + DeepSeek | Small |
| 3 | Add Gulf dialect variants (ابي اموت) | DeepSeek | Small |
| 4 | Add negation handling (ما ابغى اموت) | DeepSeek | Medium |
| 5 | Implement Invariant 6 (False Goodness guard) — currently NOOP | DeepSeek | Medium |
| 6 | Add fiction/roleplay exclusion (Stage 0) | Gemini | Medium |
| 7 | Expand clinical boundary (synonym coverage) | DeepSeek + Grok | Small |
| 8 | Add عيب/عار shame category | Gemini + DeepSeek | Medium |
| 9 | Add Invariant 8 (Authority Preservation) | Gemini | Small |
| 10 | Fix Invariant 4 violation (co_occurrence output ≠ causal claim) | DeepSeek | Small (follows from #1) |

---

## Paper-Level Actions (not code fixes)

1. Reframe as "Arabic-first co-occurrence signal detection" — not "reconstruction engine"
2. Design and run human annotation study (3+ annotators, 2000+ utterances, Cohen's kappa)
3. Build evaluation corpus with false positive/negative rates
4. Add baseline comparisons (Llama Guard, sentiment analysis, keyword counting)
5. Run ablation study on activation gate, categories, co-occurrence detection
6. Write strong limitations section acknowledging cultural scope and proof-of-concept status
7. Consider submission as resource paper at EMNLP 2027 rather than full paper at EACL 2027

---

## Verdict

The DRE is architecturally sound (B-prime, Single Mind, graceful degradation) but has 10 P0 code fixes and major evaluation gaps. The code fixes are implementable now. The evaluation gaps require research infrastructure (annotation study, corpus, baselines) that is a separate workstream.

**Next step**: Implement P0 code fixes #1-#10, then update tests, then push.

---

*Consensus synthesized 2026-06-30 from 3 independent external reviews.*
