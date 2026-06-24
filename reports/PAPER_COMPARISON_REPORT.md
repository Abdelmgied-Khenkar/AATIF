# AATIF Paper Comparison Report

**Old version (Zenodo):** `aatif_paper_arxiv.tex`
**New version (to upload):** `aatif_paper_v2.tex`
**Date of comparison:** June 20, 2026

---

## CONTRADICTIONS — Must Fix Before Upload

These are places where the two papers say **opposite things** about the same item. A reader who saw both versions would be confused.

---

### CONTRADICTION 1: Default θ value (CRITICAL)

**Old paper:**
> "Final parameters ($w_1 = 2.0$, $w_2 = 1.5$, $\alpha = 10$, $\theta = 0.55$) were calibrated against 31 validation prompts"

**New paper:**
> Default mode: $\theta = 0.40$ (Table 3, "default" profile)
> Creative mode: $\theta = 0.55$ (Table 3, "creative" profile)

**Problem:** The old paper presents θ=0.55 as THE calibrated default. The new paper demotes θ=0.55 to the "creative" mode and introduces θ=0.40 as the default. A reader comparing both would ask: "Which θ is the real default — 0.55 or 0.40?" The A/B calibration table in the new paper shows θ=0.40 as the optimal operating point with F₁=0.984, which directly contradicts the old paper's θ=0.55.

**Severity:** HIGH. This is the central parameter of the system. Both papers present their respective θ as the calibrated result.

---

### CONTRADICTION 2: MLCommons S1 vs S2 coverage levels SWAPPED

**Old paper (Table 4):**

| Code | Category | Coverage |
|------|----------|----------|
| S1 | Violent Crimes | **Partial** |
| S2 | Non-Violent Crimes | **Strong** |

**New paper (Table 7):**

| Code | Category | Coverage |
|------|----------|----------|
| S1 | Violent Crimes | **Strong** |
| S2 | Non-Violent Crimes | **Partial** |

**Problem:** The coverage levels for S1 and S2 are directly swapped between the two papers. The anchor counts for both are listed as the same (S1: 15+, S2: 5+) in both versions, which makes the swap look like a labeling error rather than an intentional change. If anchors were added, S1's count should have increased, but it didn't — it's still "15+". This looks like S1 and S2 were accidentally swapped in one of the two papers.

**Severity:** HIGH. A reader would see identical anchor counts with opposite coverage labels.

---

### CONTRADICTION 3: Which 4 categories are "strong"

**Old paper (Discussion, Limitations):**
> "AATIF v1.0 covers only 4 of 13 MLCommons harm categories strongly (**S2, S9, S10**—the latter after anchor expansion—**and S11**)"

**New paper (Table 7 / Discussion):**
> "Four categories have strong coverage (**S1, S9, S10, S11**)"

**Problem:** The old paper names {S2, S9, S10, S11} as the four strong categories. The new paper names {S1, S9, S10, S11}. S2 was replaced by S1. This is a direct consequence of Contradiction 2 (the S1/S2 swap), but it appears independently in prose, making it doubly confusing.

**Severity:** HIGH. Directly linked to Contradiction 2 — fixing the S1/S2 swap fixes this too.

---

### CONTRADICTION 4: S5 (Defamation) coverage DISAPPEARED

**Old paper (Table 4):**
> S5 | Defamation | **Partial** | **1**

**New paper (Table 7):**
> S5 | Defamation | **None** | **0**

**Problem:** Coverage went from "Partial" (1 anchor) to "None" (0 anchors). In an updated version with MORE total anchors (132→169), a category losing its only anchor is counterintuitive and looks like an error. A reader would ask: "Did you remove a defamation anchor? Why?"

**Severity:** MEDIUM. Could be intentional (the anchor was reclassified), but it's never explained.

---

### CONTRADICTION 5: FanarGuard citation — different authors

**Old paper bibliography:**
> `\bibitem[Alkhamissi et al.(2025)]{fanarguard2025}`
> `Alkhamissi, B., et al. (2025). FanarGuard: A culturally-aware moderation filter...`
> `arXiv:2411.XXXXX` ← placeholder

**New paper bibliography:**
> `\bibitem[Fatehkia et al.(2025)]{fanarguard2025}`
> `Fatehkia, M., Altinisik, E., & Sencar, H. T. (2025). FanarGuard...`
> `arXiv:2511.18852`

**Problem:** The same citation key `{fanarguard2025}` points to different first authors (Alkhamissi vs Fatehkia) and different arXiv IDs. The old paper had a placeholder arXiv ID, suggesting the citation was provisional. But a reader comparing both papers would see the same `\citet{fanarguard2025}` pointing to apparently different papers.

**Severity:** MEDIUM. Likely the old version had incorrect/provisional author info. The new version appears to be the corrected citation. But anyone who looked up the old citation would find a different paper.

---

## EVOLUTIONS — Expected, No Action Needed

These are places where the new paper has updated numbers, more detail, or refined claims. A reader would naturally understand the newer version supersedes the older.

| Item | Old Paper | New Paper | Notes |
|------|-----------|-----------|-------|
| Total anchors | 132 (58 benign, 74 harm) | 169 | More anchors added |
| Dialect hyperbole anchors | 28 | 35 | More dialect coverage |
| Test suite count | 132 tests | 166 tests | More tests added |
| Calibration set size | 31 validation prompts | 54 test cases | Larger calibration |
| S9 anchor count | 4 | 12+ | Expanded |
| S10 anchor count | 38+ | 41+ | Expanded |
| S11 anchor count | 6+ | 6+ | Same |
| Held-out validation | Not present | F₁=0.9615 on 56 cases | New evaluation |
| A/B calibration table | Not present | Full θ sweep table | New detail |
| Intent scorer anchors | Not specified | 44 | New detail |
| Emotion scorer anchors | Not specified | 32 | New detail |
| Top-K aggregation | Not described | K=3, described in detail | New mechanism |
| Hysteresis controller | Not present | Described (Section 3.3) | New feature |
| Safety Gates (Ω, Ξ) | Not explicitly named | Described (Section 3.4) | New feature |
| Mode profiles | Single parameter set | 4 profiles | New feature |
| Meaning Density Hypothesis | Not named | Named and developed (§4.1) | New concept |
| FanarGuard comparison table | Described in prose | Formal comparison table | Better presentation |

---

## STRUCTURAL — Different Organization, Fine

| Aspect | Old Paper | New Paper |
|--------|-----------|-----------|
| **Title** | "A Practitioner-Derived Framework of Conjectures for LLM Governance" | "A Multiplicative Governance Equation for Arabic-First LLM Safety" |
| **Framing** | Conjectures-first: 10 conjectures presented in detail, S equation as one operationalization | Equation-first: S equation is the main contribution, conjectures mentioned as background |
| **Methodology section** | Full 7-step inductive pipeline (Section 3) | Briefly mentioned in Discussion (§6.3) |
| **Conjectures section** | 10 conjectures presented individually (Section 4) | Not presented individually; referenced in Discussion |
| **Arabic-First section** | Not a standalone section | Dedicated Section 4 with meaning density, hyperbole, maqam |
| **Author location** | "Tallahassee, FL, USA" | Removed |
| **Keywords** | "LLM governance, AI alignment, inductive methodology, Arabic NLP, constraint density, ethical question compilation" | "LLM safety, governance equation, Arabic NLP, multiplicative gating, non-compensability, semantic anchors" |
| **Abstract scope** | Broader (conjectures, methodology, cross-platform observation) | Narrower and sharper (equation, benchmarks, Arabic-first) |
| **Introduction structure** | Narrative about alignment landscape | Three numbered gaps (no equation, no non-compensability, Arabic as afterthought) |
| **Bibliography size** | ~40 references | ~22 references (trimmed to relevant) |

---

## ITEMS THAT ARE CONSISTENT (No Issues)

These were checked and found to be identical or compatible across both papers:

- The S equation itself: identical formulation
- w₁=2.0, w₂=1.5: identical
- α=10 (default): identical
- Hard override H>0.7→SAFE_FREEZE: identical
- HarmBench results table: identical numbers
- MultiJail results table: identical numbers
- Conjecture count: 73 in both
- Field notes count: 78 in both
- Sigmoid symmetry property: identical
- Non-compensability claim: identical
- FanarGuard F₁=0.82 comparison: identical
- ADHAR cross-dialect accuracy drop (0.84→0.64): identical
- GitHub URL: identical
- Zenodo DOI: identical

---

## RECOMMENDED ACTIONS

1. **θ contradiction (Critical):** Decide if v2 should acknowledge v1's θ=0.55. Options:
   - Add a footnote: "An earlier preprint used θ=0.55 as the default; subsequent A/B calibration (Table 5) identified θ=0.40 as optimal."
   - Or simply accept the difference since v2 supersedes v1 — but be prepared for reviewer questions.

2. **S1/S2 swap (Critical):** Verify which paper has the correct labels. Both show S1 with 15+ anchors and S2 with 5+. Determine: does 15+ anchors warrant "Strong" or "Partial"? Fix whichever paper has the error.

3. **S5 Defamation (Medium):** Either restore the anchor or add a note explaining why it was removed/reclassified.

4. **FanarGuard citation (Medium):** The new paper's citation (Fatehkia et al., arXiv:2511.18852) appears to be the correct one. No action needed in v2, but be aware that the old Zenodo version cites different authors — a reader comparing them might be confused.

5. **All other differences are EVOLUTION or STRUCTURAL** — expected and fine for a v2.
