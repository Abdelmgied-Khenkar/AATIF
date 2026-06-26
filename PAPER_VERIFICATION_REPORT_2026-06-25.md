# AATIF Paper Verification Report
**Date:** 2026-06-25 22:21 UTC  
**Paper:** `aatif_paper_v2.tex`  
**Verified by:** Claude (systematic code-to-paper audit)

---

## EXECUTIVE SUMMARY

**Total numbers verified:** ~180+ quantitative claims  
**CRITICAL MISMATCHES found:** 6  
**INTERNAL INCONSISTENCIES found:** 3  
**MATCHES confirmed:** ~170+  

The most serious issue: **Table 7 (θ sweep) has wrong numbers in 4 of 8 rows.** The HarmBench and MultiJail tables use outdated results — newer benchmarks show dramatically better performance.

---

## 1. ANCHOR COUNTS

### H (Harm) Anchors
| Claim | Paper says | Code has | Verdict |
|-------|-----------|----------|---------|
| H anchor count | **171** | **171** (single HARM_ANCHORS list in `aatif_semantic_scorer.py`) | ✅ MATCH |
| Separate SAFE/COUNTER/CBRN lists? | Not claimed | No — all in one flat list with different H levels | ✅ Consistent |
| `self.texts` at init | 171 | 171 (`self.texts = [a[0] for a in anchors]`) | ✅ MATCH |

**Note:** There is NO file `aatif_harm_scorer.py`. The actual file is `aatif_semantic_scorer.py` containing class `SemanticHarmScorer`. The paper references "H scorer" generically, which is fine.

### I (Intent) Anchors
| Claim | Paper says | Code has | Verdict |
|-------|-----------|----------|---------|
| I anchor count | **46** | **46** (INTENT_ANCHORS in `aatif_intent_scorer.py`) | ✅ MATCH |

Breakdown: 11 constructive (I=1.0) + 5 seeking support (I=0.7) + 7 neutral (I=0.5) + 4 questionable (I=0.3) + 5 harmful AR (I=0.0) + 5 harmful EN (I=0.0-0.05) + 5 colloquial metaphors (I=0.8-0.9) + 4 jailbreak (I=0.0) = **46**

### E (Emotion) Anchors
| Claim | Paper says | Code has | Verdict |
|-------|-----------|----------|---------|
| E anchor count | **32** | **32** (EMOTION_ANCHORS in `aatif_emotion_scorer.py`) | ✅ MATCH |

Breakdown: 6 positive (E=1.0) + 8 mild positive (E=0.7) + 6 neutral (E=0.5) + 6 mild negative (E=0.3) + 6 intense negative (E=0.0) = **32**

### Total Anchors
| Claim | Paper says | Code has | Verdict |
|-------|-----------|----------|---------|
| H + I + E | **249** | 171 + 46 + 32 = **249** | ✅ MATCH |

### Dialect-Hyperbole Anchors
| Claim | Paper says | Code has | Verdict |
|-------|-----------|----------|---------|
| Dialect-hyperbole count | **35** | **35** (all anchors in dialect sections with H ≤ 0.05) | ✅ MATCH |

Detailed count: Initial dialect expressions (5) + Colloquial metaphors (5) + Parenting frustration (6) + Money/daily life at H≤0.05 (4, excluding 1 at H=0.1) + Work/school (3) + Playful threats (4) + Standalone hyperbole (8) = **35**

---

## 2. S-EQUATION PARAMETERS

| Parameter | Paper says | Code has (`GATED_PROFILES["default"]`) | Verdict |
|-----------|-----------|---------------------------------------|---------|
| w₁ | 2.0 | 2.0 | ✅ MATCH |
| w₂ | 1.5 | 1.5 | ✅ MATCH |
| α (alpha) | 10 | 10 | ✅ MATCH |
| θ (theta) | 0.40 | 0.40 | ✅ MATCH |
| Hard override | H > 0.7 → SAFE_FREEZE | `H_GATED_HARD_OVERRIDE = 0.7` | ✅ MATCH |

### S-Equation Formula
| Paper | Code | Verdict |
|-------|------|---------|
| `S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))]` | `quality = sigmoid(w1*I + w2*E); gate = 1.0 - sigmoid(alpha*(H - theta)); S = quality * gate` | ✅ MATCH |

---

## 3. DECISION THRESHOLDS (Table 1)

| Condition | Paper says | Code (`THRESHOLDS`) | Verdict |
|-----------|-----------|---------------------|---------|
| S > 0.7 | execute | `(0.7, "EXECUTE")` | ✅ MATCH |
| 0.5 < S ≤ 0.7 | clarify | `(0.5, "CLARIFY")` | ✅ MATCH |
| 0.3 < S ≤ 0.5 | safe_stop | `(0.3, "SAFE_STOP")` | ✅ MATCH |
| S ≤ 0.3 | safe_freeze | `(0.0, "SAFE_FREEZE")` | ✅ MATCH |
| H > 0.7 | safe_freeze (hard) | `H_GATED_HARD_OVERRIDE = 0.7` | ✅ MATCH |

---

## 4. MODE PROFILES (Table 2)

| Profile | Paper α | Code α | Paper θ | Code θ | Verdict |
|---------|---------|--------|---------|--------|---------|
| high_sensitivity | 15 | 15 | 0.30 | 0.30 | ✅ MATCH |
| default | 10 | 10 | 0.40 | 0.40 | ✅ MATCH |
| relaxed | 8 | 8 | 0.55 | 0.55 | ✅ MATCH |
| balanced_strict | 10 | 10 | 0.40 | 0.40 | ✅ MATCH |

**Note:** Paper says high_sensitivity uses w₂=1.0 — code confirms `w2: 1.0`. Paper doesn't mention relaxed uses w₁=3.0, w₂=2.5 (different from default). Consider adding this to Table 2 for completeness.

---

## 5. DOMAIN θ(d) VALUES (Table 3)

| Domain | Paper θ(d) | Code (`DOMAIN_CONFIG`) | Verdict |
|--------|-----------|----------------------|---------|
| Healthcare | 0.25 | 0.25 | ✅ MATCH |
| Education | 0.30 | 0.30 | ✅ MATCH |
| General | 0.40 | 0.40 | ✅ MATCH |
| Technology | 0.40 | 0.40 (key: `tech`) | ✅ MATCH |
| E-Commerce | 0.40 | 0.40 (key: `ecommerce`) | ✅ MATCH |
| Creative | 0.50 | 0.50 | ✅ MATCH |

---

## 6. HYSTERESIS PARAMETERS

| Parameter | Paper says | Code has | Verdict |
|-----------|-----------|----------|---------|
| ε_S | 0.05 | `EPSILON_S = 0.05` (line 63) | ✅ MATCH |
| ε_H | 0.05 | `EPSILON_H = 0.05` (line 64) | ✅ MATCH |
| max_clarify_turns | 2 | `MAX_CLARIFY_TURNS = 2` (line 73) | ✅ MATCH |
| Priority rules | 7 | 7 numbered rules in apply() method | ✅ MATCH |
| History length | 20 | `self.history[-20:]` (line 120) | ✅ MATCH |
| De-escalation lock | H > 0.5 | `if current == "SAFE_STOP" and H > 0.5` (line 346) | ✅ MATCH |
| Lines of code | 580 | **580** (`wc -l` confirmed) | ✅ MATCH |

---

## 7. R-EQUATION PARAMETERS

| Parameter | Paper says | Code has | Verdict |
|-----------|-----------|----------|---------|
| w₃ | 1.0 | 1.0 | ✅ MATCH |
| w₄ | 1.5 | 1.5 | ✅ MATCH |
| w₅ | 0.8 | 0.8 | ✅ MATCH |
| w₆ | 2.0 | 2.0 | ✅ MATCH |
| b (bias) | -2.65 | -2.65 (computed as -(w3+w4+w5+w6)*0.5) | ✅ MATCH |
| Lines of code | 591 | **591** (`wc -l` confirmed) | ✅ MATCH |
| Test count (Sec 3.9) | **67** | **76** (pytest --co) | ❌ MISMATCH |

---

## 8. DOMAIN PROTOCOLS

| Claim | Paper says | Code has | Verdict |
|-------|-----------|----------|---------|
| Lines of code | 890 | **890** (`wc -l` confirmed) | ✅ MATCH |
| Test count (Sec 3.10) | 132 | **132** (pytest --co) | ✅ MATCH |
| Domains | 6 | 5 specific + 1 cross-domain = 6 | ✅ MATCH |

---

## 9. OUTPUT GATE

| Claim | Paper says | Code has | Verdict |
|-------|-----------|----------|---------|
| Lines of code (Sec 3.11) | **814** | **829** (`wc -l`) | ❌ MISMATCH |
| Test count (Sec 3.11) | **105** | **110** (pytest --co) | ❌ MISMATCH |

---

## 10. GOVERNOR

| Claim | Paper says | Code has | Verdict |
|-------|-----------|----------|---------|
| Lines of code | 775 | **775** (`wc -l` confirmed) | ✅ MATCH |

---

## 11. TEST SUITE (Section 5.1) — MOST CRITICAL TABLE

### Total count
| Claim | Paper says | pytest --co | Verdict |
|-------|-----------|-------------|---------|
| Total tests | **932** | **932** | ✅ MATCH |
| Test functions | **804** | **804** (grep -c "def test_") | ✅ MATCH |
| Parametrized expansions | **128** | 932 - 804 = **128** | ✅ MATCH |

### Per-module breakdown (Section 5.1 vs pytest --co)

| Module | Paper | pytest | Verdict |
|--------|-------|--------|---------|
| S-equation core | 41 | 41 | ✅ MATCH |
| Intent engine | 79 | 79 | ✅ MATCH |
| Emotion scorer | 32 | 32 | ✅ MATCH |
| Intent scorer | 30 | 30 | ✅ MATCH |
| Gated comparison | 19 | 19 | ✅ MATCH |
| Response shaping | 46 | 46 | ✅ MATCH |
| Domain parameterization | 78 (39 funcs) | 78 | ✅ MATCH |
| Domain protocols P(d) | 132 | 132 | ✅ MATCH |
| CBRN detection | 12 | 12 | ✅ MATCH |
| Jailbreak markers | 10 | 10 | ✅ MATCH |
| Dialect hyperbole | 22 | 22 | ✅ MATCH |
| R-equation style | 76 | 76 | ✅ MATCH |
| Output Gate | 110 | 110 | ✅ MATCH |
| Governor | 26 | 26 | ✅ MATCH |
| Hysteresis | 21 | 21 | ✅ MATCH |
| Conversation memory | 34 | 34 | ✅ MATCH |
| Time-sense | 70 (40 funcs) | 70 | ✅ MATCH |
| Embeddings | 9 | 9 | ✅ MATCH |
| Mathematical proofs | 12 | 12 | ✅ MATCH |
| Unknown-territory | 11 | 11 | ✅ MATCH |
| Held-out validation | 57 (2 funcs) | 57 | ✅ MATCH |
| Pipeline integration | 5 | 5 | ✅ MATCH |
| **SUM** | **932** | **932** | ✅ MATCH |

### INTERNAL INCONSISTENCIES within the paper:
| Module | Sec 3.x says | Sec 5.1 says | pytest says | Issue |
|--------|-------------|-------------|-------------|-------|
| R-equation | **67** (Sec 3.9) | **76** (Sec 5.1) | **76** | ❌ Sec 3.9 is wrong, should be 76 |
| Output Gate | **105** (Sec 3.11) | **110** (Sec 5.1) | **110** | ❌ Sec 3.11 is wrong, should be 110 |

---

## 12. THETA SWEEP / A/B CALIBRATION (Table 7) — ❌ CRITICAL

The paper says it used "bge-m3 backend" for this sweep. Comparing paper's Table 7 against `temperature_ab_results_bge.json`:

| θ | Metric | Paper says | Data file says | Verdict |
|---|--------|-----------|---------------|---------|
| 0.20 | FP Rate | **33.3%** | **20.8%** (5/24) | ❌ MISMATCH |
| 0.20 | Precision | **0.789** | **0.857** (30/35) | ❌ MISMATCH |
| 0.20 | F1 | **0.882** | **0.923** | ❌ MISMATCH |
| 0.25 | All cells | match | match | ✅ MATCH |
| 0.30 | FP Rate | **12.5%** | **16.7%** (4/24) | ❌ MISMATCH |
| 0.30 | Precision | **0.909** | **0.882** (30/34) | ❌ MISMATCH |
| 0.30 | F1 | **0.952** | **0.938** | ❌ MISMATCH |
| 0.35 | All cells | match | match | ✅ MATCH |
| 0.40 | All cells | match | match | ✅ MATCH |
| 0.45 | All cells | match | match | ✅ MATCH |
| 0.50 | Detection | **90.0%** | **96.7%** (29/30) | ❌ MISMATCH |
| 0.50 | Recall | **0.900** | **0.967** | ❌ MISMATCH |
| 0.50 | F1 | **0.947** | **0.983** | ❌ MISMATCH |
| 0.55 | Detection | **83.3%** | **96.7%** (29/30) | ❌ MISMATCH |
| 0.55 | Recall | **0.833** | **0.967** | ❌ MISMATCH |
| 0.55 | F1 | **0.909** | **0.983** | ❌ MISMATCH |

**Root cause:** 4 of 8 rows have wrong numbers. The "sweet spot" rows (θ=0.35, 0.40) are correct. The data shows θ=0.45/0.50/0.55 all produce identical results (29 TP, 0 FP), but the paper shows a progressive decline that doesn't exist in the data.

**What Table 7 should say:**

| θ | Detection | FP Rate | Precision | Recall | F1 |
|---|-----------|---------|-----------|--------|------|
| 0.20 | 100% | 20.8% | 0.857 | 1.000 | 0.923 |
| 0.25 | 100% | 20.8% | 0.857 | 1.000 | 0.923 |
| 0.30 | 100% | 16.7% | 0.882 | 1.000 | 0.938 |
| 0.35 | 100% | 4.2% | 0.968 | 1.000 | 0.984 |
| **0.40** | **100%** | **4.2%** | **0.968** | **1.000** | **0.984** |
| 0.45 | 96.7% | 0.0% | 1.000 | 0.967 | 0.983 |
| 0.50 | 96.7% | 0.0% | 1.000 | 0.967 | 0.983 |
| 0.55 | 96.7% | 0.0% | 1.000 | 0.967 | 0.983 |

---

## 13. HELD-OUT VALIDATION (Section 5.4)

| Claim | Paper says | Data file says | Verdict |
|-------|-----------|---------------|---------|
| Total cases | 56 | 56 | ✅ MATCH |
| Arabic / English | 28 / 28 | 28 / 28 | ✅ MATCH |
| Safe / Blocked | 30 / 26 | TN=30, TP=26 | ✅ MATCH |
| Initial F1 | 0.735 | 0.7353 (baseline in fix_experiments_raw) | ✅ MATCH |
| Initial Precision | 0.595 | 0.5952 | ✅ MATCH |
| Initial Recall | 0.962 | 0.9615 | ✅ MATCH |
| Initial FPs | 17 | Computed: TP/Prec - TP = 17 | ✅ MATCH |
| Final F1 | 1.0 | 1.0 (held_out_results_2026-06-25.json) | ✅ MATCH |
| Final Precision | 1.0 | 1.0 | ✅ MATCH |
| Final Recall | 1.0 | 1.0 | ✅ MATCH |
| Final FP/FN | 0/0 | FP=0, FN=0 | ✅ MATCH |

---

## 14. HARMBENCH RESULTS (Table 5) — ⚠️ OUTDATED

The paper uses results from the OLDER benchmark run. A newer run (2026-06-25, bge-m3) exists with significantly better results.

| Category | Paper (old) | Latest data (new) | Status |
|----------|------------|-------------------|--------|
| Chemical/biological | 28/28 (100%) | 28/28 (100%) | ✅ Same |
| Cybercrime | 38/43 (88.4%) | 38/43 (88.4%) | ✅ Same |
| Illegal activities | 38/43 (88.4%) | 38/43 (88.4%) | ✅ Same |
| Harmful content | **7/10 (70.0%)** | **10/10 (100%)** | ⚠️ OUTDATED |
| Harassment | **9/15 (60.0%)** | **15/15 (100%)** | ⚠️ OUTDATED |
| Misinformation | **13/39 (33.3%)** | **28/39 (71.8%)** | ⚠️ OUTDATED |
| Copyright | **4/57 (7.0%)** | **28/57 (49.1%)** | ⚠️ OUTDATED |
| Safety total | **133/179 (74.3%)** | **158/179 (88.3%)** | ⚠️ OUTDATED |
| All total | **137/236 (58.1%)** | **186/236 (78.8%)** | ⚠️ OUTDATED |

**Decision needed:** Should the paper be updated to the latest benchmark results? The old results ARE internally consistent with the old data file (`harmbench_results_bge.json`), so they weren't fabricated — they're just from an earlier version of the scorer.

---

## 15. MULTIJAIL RESULTS (Table 6) — ⚠️ OUTDATED

Same situation: paper uses older results, newer data available.

| Metric | Paper (old) | Latest data (new) | Status |
|--------|------------|-------------------|--------|
| Arabic detection | **56/75 (74.7%)** | **66/75 (88.0%)** | ⚠️ OUTDATED |
| English detection | **52/75 (69.3%)** | **68/75 (90.7%)** | ⚠️ OUTDATED |
| Arabic avg H | 0.519 | 0.670 | ⚠️ OUTDATED |
| English avg H | 0.495 | 0.668 | ⚠️ OUTDATED |
| AR-EN gap | 5.4pp (AR higher) | -2.7pp (EN higher!) | ⚠️ REVERSED |

**Critical note:** In the new results, English detection is HIGHER than Arabic (90.7% vs 88.0%). The paper's narrative about "Arabic outperforming English" and the "5.4-point gap" would need to be reversed or reframed.

---

## 16. FIELD NOTES

| Claim | Paper says | Filesystem says | Verdict |
|-------|-----------|----------------|---------|
| Field note count | **78** | 77 entries in collection file + individual files FN075-078 | ⚠️ APPROXIMATELY MATCH |

The `field-notes/` directory has 16 files, but notes are consolidated in `AATIF_FieldNotes_Collection.md`. Grep found 77 heading-level entries. The paper says 78. Off by 1 — likely a grep pattern issue or one note uses a different heading format. **Needs manual verification.**

---

## 17. OTHER NUMBERS

| Claim | Paper says | Source | Verdict |
|-------|-----------|--------|---------|
| 73 conjectures | 73 | Not directly verified — no single list found | ⚠️ UNVERIFIED |
| 4 LLM platforms | 4 | Not verified | ⚠️ UNVERIFIED |
| 12 months observation | 12 | Not verified | ⚠️ UNVERIFIED |
| K=3 (top-K) | 3 | Code uses `top_k=3` default | ✅ MATCH |
| Unknown territory threshold | 0.20 | `UNKNOWN_TERRITORY_THRESHOLD = 0.20` | ✅ MATCH |
| Calibration set size | 54 (30 harmful, 24 benign) | Data file confirms 54 cases | ✅ MATCH |
| Dialect test cases | 22 | pytest: `test_dialect_hyperbole.py` = 22 | ✅ MATCH |
| Dialect false positives | 0 | Tests pass (all 22) | ✅ MATCH |

### Lines of Code Summary
| Module | Paper says | wc -l says | Verdict |
|--------|-----------|-----------|---------|
| Hysteresis | 580 | 580 | ✅ MATCH |
| R-equation | 591 | 591 | ✅ MATCH |
| Domain protocols | 890 | 890 | ✅ MATCH |
| Output gate | **814** | **829** | ❌ MISMATCH (should be 829) |
| Governor | 775 | 775 | ✅ MATCH |

---

## SUMMARY OF ALL MISMATCHES

### ❌ CRITICAL — Must fix before submission:

1. **Table 7 (θ sweep): 4 of 8 rows have wrong numbers.** θ=0.20, 0.30, 0.50, 0.55 all disagree with the actual data file. See Section 12 above for correct values.

2. **Sec 3.9: R-equation test count says 67, actual is 76.** (Sec 5.1 correctly says 76.)

3. **Sec 3.11: Output gate test count says 105, actual is 110.** (Sec 5.1 correctly says 110.)

4. **Sec 3.11: Output gate line count says 814, actual is 829.**

### ⚠️ IMPORTANT — Decision needed:

5. **HarmBench results (Table 5) are outdated.** Latest results show 88.3% safety detection (up from 74.3%). Should the paper be updated?

6. **MultiJail results (Table 6) are outdated.** Latest results show AR 88.0% / EN 90.7% — and the AR-EN gap has REVERSED direction. The paper's "Arabic outperforms English" narrative no longer holds with current data.

7. **Field notes count: 78 vs ~77.** Off by 1, needs manual verification.

### ✅ ALL OTHER NUMBERS MATCH

All anchor counts (H=171, I=46, E=32, total=249, dialect=35), S-equation parameters (w₁, w₂, α, θ), decision thresholds, mode profiles, domain θ(d) values, R-equation parameters, held-out validation results, test suite total (932) and per-module breakdown (all 22 modules), lines of code (4/5 match), and calibration set sizes are verified correct.
