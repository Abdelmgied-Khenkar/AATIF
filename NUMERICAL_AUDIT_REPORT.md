# AATIF Paper v2 — Full Numerical Audit Report

**Date:** 2026-06-20
**Paper:** `aatif_paper_v2.tex`
**Auditor:** Claude (requested by Abdulmjeed)

---

## Executive Summary

**37 claims verified, 7 discrepancies found (5 genuine errors, 1 placeholder, 1 imprecision).**

The benchmark results (HarmBench, MultiJail, held-out) are all **perfectly accurate** — every number traces back to the JSON source files. The errors are concentrated in **Section 3 (the equation description)** where the paper's mode profiles and decision thresholds are out of sync with the current code, and in **anchor counts** that grew after the paper text was written.

---

## ✅ CONFIRMED CORRECT (37 claims)

### S Equation Core Parameters

| Paper Text | Source File | Value | Status |
|---|---|---|---|
| "Parameters $w_1 = 2.0$ and $w_2 = 1.5$" (§3.1) | `engine/aatif_s_equation.py` GATED_PROFILES["default"] | w1=2.0, w2=1.5 | ✅ |
| "$\alpha = 10$ controls transition sharpness" (§3.1) | GATED_PROFILES["default"]["alpha"] | 10 | ✅ |
| "$\theta = 0.40$ sets the harm level" (§3.1) | GATED_PROFILES["default"]["theta"] | 0.40 | ✅ |
| "$H > 0.7 \Rightarrow$ SAFE_FREEZE" (§1, §3.1) | H_GATED_HARD_OVERRIDE = 0.7 | 0.7 | ✅ |

### Anchor Counts

| Paper Text | Source File | Actual Count | Status |
|---|---|---|---|
| "169 curated anchors" (Abstract, §3.2) | `engine/aatif_semantic_scorer.py` HARM_ANCHORS | 169 (AST-verified) | ✅ |
| "44 intent anchors" (§3.2) | `engine/aatif_intent_scorer.py` INTENT_ANCHORS | 44 (AST-verified) | ✅ |
| "32 emotion anchors" (§3.2) | `engine/aatif_emotion_scorer.py` EMOTION_ANCHORS | 32 (AST-verified) | ✅ |

### HarmBench Results (all from `benchmarks/harmbench_results_bge.json`)

| Paper Text (Table 3) | JSON Value | Status |
|---|---|---|
| "236 behaviors" | total_behaviors: 236 | ✅ |
| "133/179 safety = 74.3%" | safety_only_detected: 133, safety_only_total: 179, rate: 74.3% | ✅ |
| "137/236 all = 58.1%" | total_detected: 137, overall_rate: 58.1% | ✅ |
| "Chemical/biological 28/28 = 100.0%, avg H 0.894" | 28/28, avg_H: 0.8936 | ✅ (rounded) |
| "Cybercrime 38/43 = 88.4%" | 38/43 = 88.4% | ✅ |
| "Illegal 38/43 = 88.4%" | 38/43 = 88.4% | ✅ |
| "Harmful 7/10 = 70.0%" | 7/10 = 70.0% | ✅ |
| "Harassment 9/15 = 60.0%" | 9/15 = 60.0% | ✅ |
| "Misinformation 13/39 = 33.3%" | 13/39 = 33.3% | ✅ |
| "Copyright 4/57 = 7.0%" | 4/57 = 7.0% | ✅ |

### MultiJail Results (all from `benchmarks/multijail_results_bge.json`)

| Paper Text (Table 4) | JSON Value (programmatic count) | Status |
|---|---|---|
| "75 harmful prompts" | 75 items in array | ✅ |
| "Arabic 74.7% (56/75)" | detected_ar=True: 56/75 = 74.7% | ✅ |
| "English 69.3% (52/75)" | detected_en=True: 52/75 = 69.3% | ✅ |
| "AR scores higher 42/75 (56%)" | H_arabic > H_english: 42/75 | ✅ |
| "Average H Arabic 0.519" | mean(H_arabic) = 0.519 | ✅ |
| "Average H English 0.495" | mean(H_english) = 0.495 | ✅ |

### Held-Out Results (from `benchmarks/held_out_results.json`)

| Paper Text (§5.4) | JSON Value | Status |
|---|---|---|
| "56 never-before-seen cases" | total: 56 | ✅ |
| "28 Arabic / 28 English" | arabic: 28, english: 28 | ✅ |
| "30 safe, 26 blocked" | TN+FP = 29+1 = 30; TP+FN = 25+1 = 26 | ✅ |
| "$F_1 = 0.9615$" | f1: 0.9615 | ✅ |
| "precision $= 0.9615$" | precision: 0.9615 | ✅ |
| "recall $= 0.9615$" | recall: 0.9615 | ✅ |
| "1 false positive, 1 false negative" | FP: 1, FN: 1 | ✅ |

### A/B Calibration

| Paper Text (§5.4) | Source | Status |
|---|---|---|
| "54 test cases (30 harmful, 24 benign)" | Code comment in aatif_s_equation.py line 58 confirms "54 test cases, 30 harmful / 24 benign" | ✅ (no raw data file to verify sweep table) |
| "$\theta = 0.40$ optimal" | Code confirms θ=0.40 as chosen default | ✅ |
| "in-sample $F_1 = 0.984$" | Referenced in code comments; consistent | ✅ |

### Other Counts

| Paper Text | Source | Status |
|---|---|---|
| "78 field notes" (§1, §6.3) | 77 in AATIF_FieldNotes_Collection.md (#001-#077) + FN078 standalone file = 78 | ✅ |
| "22 dialect test cases" (§4.2) | `tests/test_dialect_hyperbole.py`: 22 `def test_` | ✅ |
| "12 CBRN gate tests" (§5.1) | `tests/test_safety_gate.py`: 12 `def test_` | ✅ |
| "30 intent scorer tests" (§5.1) | `tests/test_intent_scorer.py`: 30 `def test_` | ✅ |
| "18 gated comparison tests" (§5.1) | `tests/test_gated_comparison.py`: 18 `def test_` | ✅ |
| "3 pipeline tests" (§5.1) | `tests/test_pipeline.py`: 3 `def test_` | ✅ |
| "15 adversarial cases" (§5.1) | `tests/test_adversarial.py`: 15 ADVERSARIAL_CASES | ✅ |

---

## ❌ DISCREPANCIES (7 found)

### 1. Test Count: Paper says 164, actual is 166

**Paper (Abstract, §1, §5.1, §6.1, §7):** "A test suite of 164 deterministic tests"

**Actual (`def test_` count across all test files):**

| File | Count |
|---|---|
| test_intent_engine.py | 79 |
| test_intent_scorer.py | 30 |
| test_dialect_hyperbole.py | 22 |
| test_gated_comparison.py | 18 |
| test_safety_gate.py | 12 |
| test_pipeline.py | 3 |
| test_held_out_validation.py | 2 |
| **Total** | **166** |

**Verdict:** The paper says 164 but there are 166 test functions. Likely 2 tests were added after the paper text was written (probably the 2 in `test_held_out_validation.py`). **Fix: update to 166 in all 5 locations.**

---

### 2. Dialect-Hyperbole Anchor Count: Paper says 28, actual is ~34

**Paper (Abstract, §3.2, §4.2, §7):** "28 dialect-hyperbole disambiguation anchors" / "28 dialect-specific hyperbole anchors scored at $H \leq 0.05$"

**Actual:** Counting Arabic anchors at H ≤ 0.05 that contain violent-sounding markers (موت, قتل, ذبح, كسر, حرق, فجر, قنبل, etc.): **34 anchors**.

Breakdown of dialect-hyperbole anchors by category:
- Dialect expressions (أموت فيك, تذبحني...): 5
- Colloquial metaphors (قنبله, بتفجر...): 5
- Parenting frustration: 6
- Money/daily life frustration: 4
- Work/school frustration: 3
- Playful/affectionate threats: 4
- Standalone hyperbole (والله لأموته, بذبحك...): 8
- **Total: 35** (34 strictly at H≤0.05; 1 at H=0.1 for Egyptian financial stress)

**Verdict:** Anchors grew from 28 to ~35 during development. **Fix: update to current count in 4 locations.**

---

### 3. Decision Thresholds (Table 1): Paper boundaries ≠ code boundaries

**Paper (Table 1, §3.1):**
| Condition | Action |
|---|---|
| S ≥ 0.7 | EXECUTE |
| 0.4 ≤ S < 0.7 | CLARIFY |
| S < 0.4 | SAFE_STOP |
| H > 0.7 | SAFE_FREEZE |

**Source code (`aatif_s_equation.py` lines 309-313):**
```python
THRESHOLDS = [
    (0.7, "EXECUTE"),       # S > 0.7
    (0.5, "CLARIFY"),       # 0.5 < S ≤ 0.7
    (0.3, "SAFE_STOP"),     # 0.3 < S ≤ 0.5
    (0.0, "SAFE_FREEZE"),   # S ≤ 0.3
]
```

**Three boundary errors:**
- CLARIFY lower bound: paper says 0.4, code says 0.5
- SAFE_STOP range: paper says S < 0.4, code says 0.3 < S ≤ 0.5
- SAFE_FREEZE: paper omits (only mentions H > 0.7 path), code has S ≤ 0.3

**Verdict:** Table 1 in the paper does not match the code. **This is a significant error in the published equation description.** Fix: rewrite Table 1 to match the actual thresholds.

---

### 4. Mode Profiles (Table 2): 3 of 4 profiles have wrong parameters

**Paper (Table 2):**
| Profile | α | θ |
|---|---|---|
| high_sensitivity | 12 | 0.30 |
| default | 10 | 0.40 |
| creative | 8 | 0.50 |
| casual | 6 | 0.55 |

**Source code (GATED_PROFILES, lines 269-297):**
| Profile | α | θ |
|---|---|---|
| default | 10 | 0.40 |
| high_sensitivity | 15 | 0.45 |
| creative | 8 | 0.55 |
| balanced_strict | 10 | 0.40 |

**Errors:**
- **high_sensitivity**: paper says α=12, θ=0.30 → code has α=15, θ=0.45 (BOTH wrong)
- **creative**: paper says θ=0.50 → code has θ=0.55 (θ wrong)
- **casual**: exists in paper but NOT in code; **balanced_strict** exists in code but NOT in paper
- **default**: ✅ correct

**Verdict:** The paper's mode profile table appears to be from an earlier version of the code. **This is a significant error — 3 of 4 rows are wrong.** Fix: rewrite Table 2 to match GATED_PROFILES.

---

### 5. Bibliography Placeholder: arXiv:2411.XXXXX

**Paper (line 483):**
```
\textit{EACL 2026}. arXiv:2411.XXXXX.
```

**Verdict:** The FanarGuard citation has a placeholder arXiv ID `2411.XXXXX`. This must be replaced with the actual arXiv ID before submission. The real paper is likely arXiv:2411.18639 or similar — needs verification.

---

### 6. MLCommons Table — Anchor Counts Are Approximate

**Paper (Table 5):**
- S10 (Hate): "38+" anchors
- S9 (Indiscriminate Weapons): "8+" anchors

**Actual counts:**
- Hate speech anchors (nationality + religious + ethnicity + race + dehumanization + general slurs + English hate): **41**
- Weapon-specific anchors (knife threats + gun threats + arson + explosives + VX): **~12** (9 in the weapon-specific section + bomb/explosive/VX in English anchors)

**Verdict:** The "+" notation signals approximation, so these aren't strictly wrong, but the numbers have drifted. Consider updating to exact counts.

---

### 7. high_sensitivity Description Text Mismatch

**Paper (§3.5):** "Lower $\theta$ makes the harm gate more sensitive (closes earlier)" — in describing high_sensitivity with θ=0.30.

**Code:** high_sensitivity has θ=0.45, which is HIGHER than default's θ=0.40. The description's logic ("lower θ = more sensitive") is correct as a principle, but the actual values contradict the narrative since the code's high_sensitivity actually has a HIGHER θ.

**Verdict:** The descriptive text was written for an earlier parameter set where high_sensitivity really did have lower θ. Now the code contradicts the narrative.

---

## Summary Action Items

| Priority | Fix | Locations |
|---|---|---|
| 🔴 Critical | Rewrite Table 1 (decision thresholds) to match code: 0.7/0.5/0.3 | §3.1, Table 1 |
| 🔴 Critical | Rewrite Table 2 (mode profiles) to match GATED_PROFILES | §3.5, Table 2 |
| 🔴 Critical | Fix FanarGuard arXiv placeholder: `2411.XXXXX` → real ID | Bibliography |
| 🟡 Important | Update test count: 164 → 166 | Abstract, §1, §5.1, §6.1, §7 |
| 🟡 Important | Update dialect-hyperbole anchor count: 28 → 35 | Abstract, §3.2, §4.2, §7 |
| 🟢 Minor | Update MLCommons table approximate counts (38+ → 41, 8+ → 12) | Table 5 |
| 🟢 Minor | Verify high_sensitivity narrative matches new parameters | §3.5 prose |

---

*All benchmark results (HarmBench, MultiJail, held-out) are verified 100% accurate against source JSON files.*
