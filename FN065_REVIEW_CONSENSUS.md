# FN#065 Maqam Architecture Law — External Review Consensus
## 3-Model Review, 2026-07-01

### Overall Consensus: PASS WITH CONCERNS — 2 P0 fixes required (Gemini)

---

## Model 1: ChatGPT — PASS WITH CONCERNS (0 P0)

| Question | Verdict |
|----------|---------|
| R1: Authority isolation | PASS |
| R2: Maqam set | PASS WITH CONCERNS |
| R3: Triad decomposition | PASS |
| R4: Thresholds & bands | PASS WITH CONCERNS |
| R5: Architectural risks | PASS WITH CONCERNS |

**Key Concerns (P1/P2):**
- Potential taxonomy gaps: CONFUSION, ANXIETY as candidates for v2
- Identity attribution risk: maqam labels could bias downstream if leaked
- scores_by_maqam internal distribution leakage to runtime
- Sarcasm/irony detection gap
- Contrastive negation ("I'm not sad, I'm angry") needs better handling

**Recommendations:**
- Add serialization boundary (to_runtime_payload) for runtime emission
- Add invariant tests for authority contract
- Add contrastive negation and sarcasm test cases
- Documentation invariant for B-prime contract

---

## Model 2: Gemini — PASS WITH CONCERNS (2 P0)

| Question | Verdict |
|----------|---------|
| R1: Authority isolation | PASS |
| R2: Maqam set | PASS WITH CONCERNS |
| R3: Triad decomposition | PASS |
| R4: Thresholds & bands | PASS WITH CONCERNS |
| R5: Architectural risks | NEEDS REVISION |

### P0 Issues (Must-Fix):

**P0 #1: Dialect-Aware Negation Tokenizer**
- NEGATION_PREFIXES_AR missing "موب" (common Gulf Arabic negation form)
- Must handle verbal enclitics before Khaleeji marker sets activate
- Status: **FIXED** — added "موب " to tuple

**P0 #2: Short-Text Aqd Dampener**
- When token count < 15 or sentence count == 1, AqdReading punctuation_density can spike
- Single "!" on a 2-word message gives density 1.0 → misleading rhythm_score
- Need dampener guard to default short text to neutral cadence values
- Status: **FIXED** — added dampener guard in _compute_cadence

**P1/P2 Concerns:**
- Elongated Arabic letters (واااو) not handled as emphasis markers
- Emoji density not factored into cadence
- Consider transformer-based reranker for v2

---

## Model 3: Grok — PASS WITH CONCERNS (0 P0)

| Question | Verdict |
|----------|---------|
| R1: Authority isolation | PASS |
| R2: Maqam set | PASS WITH CONCERNS |
| R3: Triad decomposition | PASS |
| R4: Thresholds & bands | PASS WITH CONCERNS |
| R5: Architectural risks | PASS WITH CONCERNS |

**Key Concerns (P1/P2):**
- Context blindness: no conversation history integration
- Sarcasm/irony detection gap
- Cultural coverage: Gulf markers good, but Levantine/Egyptian could expand
- Adversarial robustness: marker stuffing possible
- Performance: O(markers × text_length) scan, fine for v1

**Recommendations:**
- Expand dialectal marker coverage (P1)
- Add conversation history window for maqam drift (P2)
- Empirical calibration on real user data (P1)
- Adversarial test suite (P2)

---

## Synthesis

All three models agree:
1. Authority contract (R1) is sound — clean B-prime isolation
2. 10-maqam set is reasonable for v1 — gaps are v2 candidates
3. Triad decomposition is architecturally sound
4. Main risks are sarcasm, context blindness, and adversarial robustness — all P1/P2

Only Gemini raised P0 issues — both addressed in this commit.

License: BSL 1.1
