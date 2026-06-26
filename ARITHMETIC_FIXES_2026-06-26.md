# Arithmetic Fixes — 2026-06-26

All 5 arithmetic errors flagged in `PAPER_REVIEW_LLM_2026-06-25.md` have been fixed in `aatif_paper_v2.tex`. Every number was verified from the actual data files before writing.

---

## AE1: HarmBench table rows did not sum to summary

**Problem:** Table 4 had 7 category rows summing to 157/178 (safety) and 185/235 (all), but the summary line claimed 158/179 and 186/236. Off by +1 in both numerator and denominator.

**Root cause:** The "unknown" category (1 behavior, 1 detected) existed in `harmbench_results_2026-06-25.json` but was missing from the table.

**Verified from:** `benchmarks/harmbench_results_2026-06-25.json` — unknown category: total=1, detected=1, detection_rate=100.0, avg_H=0.860, mlcommons_mapping="unmapped".

**Fix:**
- Added row: `Unknown & 1/1 & 100.0\% & 0.860 & --- \\`
- Changed "7 semantic categories" → "8 semantic categories" in text (line 423)
- Table rows now sum to 158/179 (safety) and 186/236 (all), matching the summary ✓

---

## AE2: MultiJail "62/73" denominator unexplained

**Problem:** Table 5 reported "62/73 (84.9%)" for high confidence, but the benchmark has 75 prompts. Why 73, not 75? What does 62 count?

**Verified from:** `benchmarks/multijail_results_2026-06-25.json` — 73 prompts have confidence="high" (max_similarity ≥ 0.45), 2 have confidence="medium". Among the 73 high-confidence prompts, 62 were detected in BOTH Arabic and English.

**Fix:**
- Changed row label from `High confidence ($\geq$0.45)` → `Detected in both langs.\ (high conf.)\`
- Added explanatory sentence after the table: "Of the 75 prompts, 73 received high-confidence scores (max similarity ≥ 0.45); the remaining 2 fell below this threshold. Among the 73 high-confidence prompts, 62 were detected in both Arabic and English (84.9%), confirming cross-lingual consistency at the per-prompt level."

---

## AE3: "51%" should be "50.7%"

**Problem:** Table 5 reported AR scores higher as "38/75 (51%)" but 38/75 = 50.67%.

**Verified from:** `benchmarks/multijail_results_2026-06-25.json` — counted H_arabic > H_english for all 75 prompts: 38 cases = 50.67%.

**Fix:** Changed `51\%` → `50.7\%` for one-decimal-place consistency with other percentages in the paper.

---

## AE4: Hysteresis test count listed as 21 (raw) but actual is 17 raw + 4 parametrized

**Problem:** The per-module test listing said "hysteresis controller (21 tests)" as if all 21 were raw test functions. This made the per-module raw sum = 808, conflicting with the stated total of "804 test functions."

**Verified from:** `grep -c "def test_" tests/test_hysteresis.py` = 17. The file contains `@pytest.mark.parametrize` expanding 1 function into 5 cases (net +4 expansion).

**Fix:** Changed `hysteresis controller (21~tests)` → `hysteresis controller (17~test functions expanding to 21 with parametrized cases)`.

Per-module raw sum now = 804 ✓. Parametrized expansions: 39 (domain θ) + 30 (time-sense) + 55 (held-out) + 4 (hysteresis) = 128 ✓. Total: 804 + 128 = 932 ✓.

---

## AE5: "5/13 MLCommons categories strong" should be "4/13"

**Problem:** The Limitations and Conclusion sections claimed "5 of 13 MLCommons categories strong," but Table 7 lists only 4 as "Strong": S1 (Violent Crimes), S9 (Indiscriminate Weapons), S10 (Hate), S11 (Suicide & Self-Harm). The table's own text (line 535) correctly says "Four categories have strong coverage."

**Verified from:** Table 7 in the paper itself — only 4 rows have "Strong" in the Coverage column.

**Fix:** Changed "5/13" → "4/13" in two locations:
- Limitations section (§6.2): "AATIF v1.0 covers only 4 of 13 MLCommons categories strongly"
- Conclusion (§7): "The framework is preliminary in coverage (4/13 MLCommons categories strong)"

---

## Compilation

`pdflatex aatif_paper_v2.tex` — zero errors, 21 pages, 448490 bytes. Warnings only (float specifier, overfull hbox on URL — pre-existing).
