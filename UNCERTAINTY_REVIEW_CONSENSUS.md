# Uncertainty/Calibration Module — 4-Model Review Consensus
## Date: 2026-06-30
## Models: ChatGPT (GPT-4o), Gemini (2.0 Flash), Grok (xAI), DeepSeek (DeepThink)

---

## Summary

All 4 models agree: the **core idea** (epistemic humility as architecture) is valuable and novel. However, the **implementation** has confirmed bugs, design weaknesses, and missing empirical grounding that must be addressed before EACL 2027 submission.

Verdicts:
- **ChatGPT**: "Architecturally correct v1. Not yet defensible without calibration evidence."
- **Gemini**: "Solid foundation but structural flaws, hidden mathematical traps, and empirical vulnerabilities."
- **Grok**: "Engineering prototype rather than rigorously justified research contribution."
- **DeepSeek**: "Not publication-ready without fundamental re-architecting of confidence aggregation, coverage estimation, multi-turn dynamics, and false-certainty detection."

---

## Classification of Findings

### A. BUGS — Fix Immediately

#### A1. Multi-turn trace overflow (4/4 unanimous)
**Current**: `trace_t = current + λ * previous_trace` (λ=0.6)
**Bug**: Exceeds 1.0. Steady state = current/(1-λ) = 2.5 with λ=0.6.
**Fix**: EMA — `trace = (1-λ) * current + λ * previous_trace`
- ChatGPT: confirmed, suggested `(1-λ)*current + λ*previous`
- Gemini: confirmed, showed steady state math
- Grok: confirmed, suggested clip or EMA
- DeepSeek: "Mathematically guaranteed to exceed 1.0. Clear, verifiable bug."

#### A2. H-I divergence condition misses accidental harm (4/4 unanimous)
**Current**: `min(1.0, |H-I|*1.5) when H>0.4 AND I>0.6`
**Bug**: If H=0.9, I=0.1 (high harm, low intent = accidental harm), condition fails because I<0.6. Divergence signal is silently ignored.
**Fix**: Remove I>0.6 condition. Fire on |H-I| > threshold regardless of absolute values. Or use variance across scorer estimates.
- ChatGPT: noted H-I inverse correlation needs coherence templates
- Gemini: "Conceptually flawed — high H + high I = clear violation, NOT disagreement"
- Grok: "Too narrow — misses negligent/accidental harm"
- DeepSeek: "Massive bug — I>0.6 condition ignores accidental harm entirely"

#### A3. Abstention thresholds not implemented in gate (2/4 explicit)
**Current**: Abstention thresholds defined (healthcare<0.30, etc.) but gate only maps EXECUTE→CLARIFY.
**Bug**: No code path sets decision="ABSTAIN" based on abstention threshold.
**Fix**: Add abstention check: if confidence < abstention_threshold → ABSTAIN.
- DeepSeek: "Abstention thresholds are orphaned — no code path triggers ABSTAIN"
- Grok: "Gray zone policy underspecified"

---

### B. DESIGN IMPROVEMENTS — v1.1

#### B1. Coverage: max_sim alone is fragile (4/4 unanimous)
**Current**: `clamp((max_sim - 0.10) / 0.50)` — single nearest neighbor.
**Issue**: One close outlier = perfect coverage. Ignores distribution density, hubness.
**Recommendation**: Top-K mean similarity (K=3 or 5), or k-NN density estimation, or Mahalanobis distance.
- All 4 models flagged this as the weakest uncertainty source.

#### B2. H-floor cap discontinuity (3/4: ChatGPT, Gemini, Grok)
**Current**: Step function at h_conf=0.35 and h_conf=0.50.
**Issue**: h_conf=0.34→cap 0.45; h_conf=0.36→cap 0.60. 33% relative jump.
**Recommendation**: 
- Gemini: sigmoid dampening `Cap(h) = 1/(1+e^(-k(h-θ)))`
- ChatGPT: add third band or smooth
- Grok: "Overly lenient and backwards in spirit"

#### B3. Arabic penalties: stacking + domain-agnostic (4/4)
**Current**: Fixed additive penalties up to -0.31 total. Applied globally.
**Issue**: All 4 trigger → -0.31 instant slash. Creative domain can collapse below abstention (0.15).
**Recommendation**: Domain-conditional penalties. Cap total penalty per domain. Make conditional on coverage.
- DeepSeek: "Uncalibrated, destructive stacking"
- Gemini: "Stacking trap — creative domain collapse"
- Grok: "cultural_indirection detection brittle — Arabic uses indirection for politeness"

#### B4. Keyword matching for false certainty (4/4 unanimous)
**Current**: 5 English + 3 Arabic keywords.
**Issue**: Misses pragmatic overconfidence, negation ("certainly not"), context.
**Recommendation**: Phase 1: pattern-based (negation handling, quotation context). Phase 2: semantic entailment or self-consistency sampling.
- DeepSeek: "Completely inadequate for modern LLMs"
- Gemini: "Will not survive peer review"
- Grok: "1990s baseline"

#### B5. W_H=0.35 questioned (3/4: Gemini, Grok, DeepSeek)
**Current**: Harm confidence weighted at 0.35 of total.
**Issue**: Coverage (0.15) can theoretically outweigh low harm confidence. Gemini: "mathematical masking risk."
**Recommendation**: Raise to ≥0.50, or make coverage a hard gate independent of weighted average.

#### B6. NaN propagation guard (1/4 explicit: DeepSeek)
**Issue**: If any component produces NaN, weighted sum becomes NaN. `NaN < ξ` evaluates False → silently allows EXECUTE.
**Recommendation**: Add explicit isnan checks, default to CLARIFY on NaN.

---

### C. PAPER LIMITATIONS — Acknowledge

#### C1. ~20+ hardcoded constants without ablation (3/4: ChatGPT, Grok, DeepSeek)
All weights, thresholds, caps, penalties are hand-tuned. No sensitivity analysis, no ablation table.
**For paper**: Acknowledge as limitation. Plan ablation study as future work.

#### C2. "calibration_confidence" is a misnomer (3/4: Grok, DeepSeek, Gemini)
It's an ad-hoc weighted ensemble score, not a well-calibrated probability. No ECE minimization.
**For paper**: Rename to "epistemic_confidence" or acknowledge the distinction.

#### C3. Feature flags all OFF by default (3/4: ChatGPT, Grok, DeepSeek)
Undermines the paper's contribution claim if the module ships disabled.
**For paper**: Frame as staged rollout with monitor-first philosophy. Explain rationale.

#### C4. Tests validate spec consistency, not correctness (3/4: ChatGPT, Grok, DeepSeek)
Missing adversarial tests for: trace overflow, NaN propagation, H-I edge cases, coverage collapse.
**For paper**: Add adversarial test suite. Report both spec and adversarial test results.

#### C5. Single scalar bottleneck (2/4: Gemini, DeepSeek)
Gate sees only one number. Cannot distinguish OOD uncertainty from scorer disagreement.
**For paper**: Acknowledge as limitation. Future: structured uncertainty reporting.

---

### D. FUTURE WORK

1. **Bayesian calibration** — Platt scaling, temperature scaling, Dirichlet calibration (Gemini, DeepSeek)
2. **Coverage as hard gate** — independent of weighted average for high-stakes domains (Gemini, DeepSeek)
3. **Semantic false-certainty detection** — entailment checks, self-consistency (all 4)
4. **Multilingual scope** — beyond Arabic-specific penalties (Grok)
5. **ECE/Brier score evaluation** — proper calibration metrics (ChatGPT)
6. **Selective risk/coverage curves** — accuracy vs. abstention rate (ChatGPT)
7. **Arabic fairness audit** — ensure penalties don't disproportionately harm Arabic users (ChatGPT, Grok)

---

## Priority Order for Fixes

1. **A1**: Multi-turn trace → EMA (5 min fix)
2. **A2**: H-I divergence condition → remove I>0.6 gate (5 min fix)
3. **A3**: Abstention threshold → implement in gate (15 min fix)
4. **B6**: NaN guard → add isnan checks (10 min fix)
5. **B1**: Coverage → top-K mean (30 min refactor)
6. **B2**: H-floor → sigmoid smoothing (15 min)
7. **B3**: Arabic penalties → domain-conditional + cap (20 min)
8. **B4**: Keywords → pattern-based upgrade (30 min)
9. **B5**: W_H → raise or justify (design decision)
10. **C4**: Adversarial tests (1-2 hours)

---

## Raw Review Sources

- ChatGPT: https://chatgpt.com/c/6a445283-0c6c-83ea-a413-3cb2e0bc2254
- Gemini: https://gemini.google.com/app/1e434698f9ca7466
- Grok: https://grok.com/c/4b91dcb4-685e-4ecc-9382-69e6e59af0cb
- DeepSeek: https://chat.deepseek.com/a/chat/s/72c196ce-de0a-4ea0-97e5-3f6e9ef83d29
