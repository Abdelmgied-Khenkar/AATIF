# Stale Numbers Fix Report

**Date:** 2026-06-28
**Scope:** All `.md` files in AATIF-academic (excluding `.tex` paper)
**Rule:** Count from SOURCE only. Historical records untouched. Normative claims fixed.

---

## Ground Truth (from source, 2026-06-28)

| Metric | Value | How counted |
|---|---|---|
| Test functions | **1,524** (1,257 in tests/ + 267 in engine/) | `grep -c "def test_"` |
| Test files | **33** (28 in tests/ + 5 in engine/) | file count |
| Parametrize expansions | **+88** | AST parse of `@pytest.mark.parametrize` |
| Effective pytest-collected | **1,612** | 1,524 + 88 |
| Subtests | **73** | grep count |
| Module files | **22** | engine/*.py non-test count |
| Module lines | **15,318** | `wc -l` on module files |

---

## Files Changed

### 1. README.md

| Location | Old | New |
|---|---|---|
| tests/ directory listing | 9 files listed | 28 files with per-file counts |
| "Run all tests" comment | `239 test functions across 9 files + 15-case adversarial runner + 14 eval scenarios` | `1,524 test functions across 33 files — 1,257 in tests/ + 267 in engine/` |
| Arabic summary | `239 اختباراً` | `1,524 اختباراً` |

### 2. NEXT_STEPS.md

| Location | Old | New |
|---|---|---|
| Normative claim about correct count | `يقول 164 اختبار (المفروض 933)` | `يقول 164 اختبار (المفروض 1,524)` |

### 3. DAILY_PRIORITIES.md

| Location | Old | New |
|---|---|---|
| Current test count | `tests = 881 (مش 775/780/164)` | `tests = 1,524 (مش 775/780/164/881/933)` |
| "الحقيقي" line | `الحقيقي **881**` | `الحقيقي **1,524** (1,257 في tests/ + 267 في engine/)` |

### 4. reports/NUMERICAL_AUDIT_REPORT.md

| Location | Old | New |
|---|---|---|
| Test count section title + table | `actual is 166` + single-row table | `actual is 1,524` + breakdown table (tests/ 28 files 1,257 + engine/ 5 files 267) |
| Action items table | `164 → 166` | `164 → 1,524` |

### 5. reports/PAPER_REWRITE_PLAN.md

| Location | Old | New |
|---|---|---|
| All instances of "164 deterministic tests" | `164 deterministic tests` (×3) | `1,524 deterministic tests` |
| Test suite reference | `Test Suite (164 tests)` | `Test Suite (1,524 tests)` |
| Category breakdown header | `164 tests by category` | `1,524 tests by category` |
| Verification step | `verify 164/164 pass` | `verify 1,524/1,524 pass` |
| Intro gap description | `zero-training semantic anchors` | `curated semantic anchors (fixed design, variable fit)` |
| Abstract draft — classifier claim | `requires zero training data, operating through 132 curated semantic anchors` | `operates through 169 curated semantic anchors ... fixed design where embedding layer can be tuned` |
| Abstract draft — extensibility | `zero-training extensibility through anchor curation` | `fixed-design extensibility through anchor curation (variable fit via embedding tuning)` |
| Abstract draft — dialect anchors | `28 hyperbole-disambiguation anchors` | `35 hyperbole-disambiguation anchors` |

### 6. reports/PAPER_VERSION_COMPARISON.md

| Location | Old | New |
|---|---|---|
| Test count row | `\| **164** \| **166** \| v2 is current \|` | `\| **164** \| **166** (now 1,524) \| Both stale — current is 1,524 \|` |
| v2 abstract test count | `166 deterministic tests` | `1,524 deterministic tests` |
| Known issues — stale test count | `actual test suite has 166` | `actual test suite has 1,524 test functions` |
| Recommendation — numbers | `Numbers are current — 169 anchors, 166 tests` | `Numbers need updating — 169 anchors, 1,524 tests (was 166)` |

### 7. reports/PAPER_COMPARISON_REPORT.md

| Location | Old | New |
|---|---|---|
| Test suite evolution row | `166 tests \| More tests added` | `166 tests (now 1,524) \| Grew significantly post-paper` |

### 8. docs/aatif-academic-paper-SKILL-v3.md

| Location | Old | New |
|---|---|---|
| "Anchors are not training" rule | `This is zero-fine-tuning extensibility.` | `The design is fixed; the embedding layer can be tuned per deployment (fixed design, variable fit — the Tailor Principle, FN#079).` |

### 9. reports/FANARGUARD_COMPARISON.md

| Location | Old | New |
|---|---|---|
| AATIF advantage description | `zero-training deployment` | `fixed-design deployment (variable fit via embedding tuning)` |

### 10. JUDGMENT_MEMORY_DESIGN.md

| Location | Old | New |
|---|---|---|
| D parameter description | `requires no fine-tuning or model training.` | `fixed design, variable fit (embedding weights can be tuned per deployment; see Tailor Principle FN#079).` |

---

## Files NOT Changed (and why)

| File | Why untouched |
|---|---|
| `aatif_paper_v2.tex` | Excluded per instruction (don't change .tex) |
| `EXECUTION_PLAN_2026-06-26.md` | Historical record — numbers (933, 907) accurate for that date |
| `CODEX_REVIEW.md` | Historical code review from 2026-06-22 — "13 modules", "670 passing" accurate then |
| `PAPER_REVIEW_ROUND2.md` | External reviewer's words — not our claim to edit |
| `PAPER_REVIEW_LLM_2026-06-25.md` | Historical LLM review — "zero training data" was the paper's claim at that time |
| `CONFERENCE_PLAN.md` | Meta-commentary about what the paper currently says |
| `NEXT_STEPS.md` (Tailor entries) | Already documents the correction itself |
| `field-notes/FN079_Tailor_Principle.md` | The field note documenting the overclaim — leave intact |
| `field-notes/AATIF_Paper_Final.md` | Arxiv abstract (historical); "without model-specific fine-tuning" is accurate and softer |
| `WASSAL_SYNC_REPORT_20260623.md` | Historical sync report from June 23 |
| `reports/FAHES_REPORT_20260626.md` | Historical report — 933 was the count on that date |
| `reports/FINAL_VERIFICATION_REPORT.md` | Historical verification — 166 was the count then |
| `reports/VERIFICATION_REPORT_v2.md` | Historical verification |
| `benchmarks/fix_comparison.md` | Historical script comment |
| `SUBMISSION_CHECKLIST.md` | No stale counts found |
| `CODEX_TASKS/*.md` | No stale counts found |
| `experiments/*.md` | No stale counts found |

---

## Summary

- **10 files edited** across README, priorities, reports, docs, and design docs
- **~25 individual edits** — all surgical (numbers and phrasing only, no content rewritten)
- **"zero fine-tuning" → "fixed design, variable fit"** applied to 4 files (5 locations)
- **Historical records preserved** — no false history created
- **Distinction enforced:** normative claims ("the real count is X") updated; historical records ("on date Y, count was Z") left intact
