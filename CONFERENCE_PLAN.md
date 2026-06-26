# AATIF Conference Submission Plan

**Generated**: June 25, 2026
**Paper**: "AATIF: A Multiplicative Governance Equation for Arabic-First LLM Safety"
**Author**: Abdulmjeed Ibrahim Khenkar (Independent Researcher)
**Current paper**: `aatif_paper_v2.tex` — 727 lines, ~20 pages, single-column, custom LaTeX format

---

## Reality Check (from 4-model review)

The simulated 4-model review gave: **REJECT for main conference, PASS for workshop**.
This means:
- Main conferences (ACL, EMNLP, NAACL, EACL, AACL) are a long shot unless the paper is significantly strengthened
- Workshops and specialized venues are the realistic path to first publication
- This is normal for independent researchers — workshop publication is a genuine achievement and builds credibility for future main-conference submissions

---

## Venue Overview

### ❌ EMNLP 2026 — DEADLINE PASSED

| Detail | Info |
|--------|------|
| Location | Budapest, Hungary |
| Dates | October 24–29, 2026 |
| ARR submission deadline | **May 25, 2026** (PASSED) |
| Commitment deadline | ~August 2, 2026 |
| Format | ACL style, two-column |
| Page limit | 8 pages (long) / 4 pages (short) + unlimited refs |
| Status | **Cannot submit — deadline was 1 month ago** |

The ARR May cycle required authors to select EMNLP or AACL at submission time (binding choice). No new submissions possible.

Source: https://2026.emnlp.org/calls/main_conference_papers/

---

### ❌ AACL-IJCNLP 2026 — DEADLINE PASSED

| Detail | Info |
|--------|------|
| Location | Hengqin, China |
| Dates | November 6–10, 2026 |
| ARR submission deadline | **May 25, 2026** (PASSED) |
| Commitment deadline | August 26, 2026 |
| Notification | September 7, 2026 |
| Camera-ready | September 30, 2026 |
| Format | ACL style, two-column |
| Page limit | 8 pages (long) / 4 pages (short) + unlimited refs |
| Status | **Cannot submit — same ARR May cycle as EMNLP, binding choice at submission** |

Source: https://2026.aaclnet.org/calls/main_conference_papers/

---

### ⚠️ ArabicNLP 2026 — DEADLINE IS TODAY (practically missed)

| Detail | Info |
|--------|------|
| Location | Budapest, Hungary (co-located with EMNLP 2026) |
| Dates | October 24–29, 2026 |
| Direct submission deadline | **June 25, 2026, 11:59 PM AoE** (TODAY) |
| Submission URL | https://openreview.net/group?id=SIGARAB.org/ArabicNLP/2026/Conference |
| Format | ACL style, two-column |
| Page limit | 8 pages (long) / 4 pages (short) / 4 pages (demo) |
| Status | **Technically still open (AoE = UTC-12), but paper is 20 pages in wrong format — impossible to reformat properly today** |

**Why this was the IDEAL venue:**
- Topics explicitly include: Arabic LLMs, safety, hate speech, bias, alignment, ethics & trust
- ArGuard 2026 shared task on Arabic harmful content detection runs alongside it
- Workshop-level acceptance standards (matches review assessment of PASS for workshop)
- The paper's Arabic-first design and dialect-hyperbole work are exactly what this venue values

**What happened:** The deadline arrived before the paper was reformatted. This is the biggest missed opportunity.

Source: https://arabicnlp2026.sigarab.org/

---

### ✅ EACL 2027 — FIRST REALISTIC TARGET (~5 weeks away)

| Detail | Info |
|--------|------|
| Location | Athens, Greece |
| Dates | March 9–14, 2027 |
| ARR submission deadline | **August 3, 2026** (~5 weeks from today) |
| Commitment deadline | October 11, 2026 |
| Format | ACL style, two-column |
| Page limit | 8 pages (long) / 4 pages (short) + unlimited refs |
| Status | **OPEN — but tight timeline for reformatting** |

**Important correction**: The original announcement said August 6, but EACL officially corrected it to **August 3, 2026**. This is the ONLY viable ARR cycle for EACL 2027 (conference is early in March 2027).

**Fit assessment:**
- Main conference: Risky (review said REJECT for main). EACL is slightly less competitive than ACL/EMNLP, but still a stretch.
- Workshop: Check for co-located workshops on safety, Arabic NLP, or trustworthy AI (workshop calls typically come later, ~October 2026)
- Best strategy: Submit to ARR by August 3. If reviews are strong enough, commit to EACL 2027 main. If not, withdraw and target a workshop.

Source: https://2027.eacl.org/, https://x.com/eaclmeeting/status/2051971432171688436

---

### 🔜 NAACL 2027 — BACKUP OPTION

| Detail | Info |
|--------|------|
| Location | TBA (likely North America) |
| Dates | TBA (likely summer 2027) |
| Predicted ARR deadline | ~October 2026 |
| Commitment deadline | ~December 2026 (estimated) |
| Format | ACL style, two-column |
| Page limit | 8 pages (long) / 4 pages (short) + unlimited refs |
| Status | **Not yet announced — dates estimated from historical pattern** |

If EACL 2027 doesn't work out, the NAACL ARR cycle (~October 2026) gives ~4 months to strengthen the paper based on EACL reviews.

Source: https://mlciv.com/ai-deadlines/conference/?id=naacl27

---

### 🔜 ACL 2027 — LONG-TERM BACKUP

| Detail | Info |
|--------|------|
| Location | TBA |
| Dates | TBA (likely July 2027) |
| Predicted ARR deadline | ~February 2027 |
| Format | ACL style, two-column |
| Page limit | 8 pages (long) / 4 pages (short) + unlimited refs |
| Status | **Not yet announced** |

Source: https://mlciv.com/ai-deadlines/conference/?id=acl27

---

## What the Paper Needs (for ANY *ACL venue)

### 1. Format Conversion (CRITICAL — must do first)

The paper currently uses:
```latex
\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
```

ALL *ACL venues require:
```latex
\documentclass[11pt]{article}
\usepackage[hyperref]{acl}  % or emnlp, eacl variant
```

This means switching to the official ACL style files (two-column format). Download from: https://github.com/acl-org/acl-style-files

### 2. Page Reduction (CRITICAL)

Current: ~20 pages single-column → Need: 8 pages two-column (long paper) or 4 pages (short)

The paper has 16 sections/subsections. For an 8-page long paper, substantial cutting is needed:
- **Keep (core)**: Introduction, S Equation definition, Arabic-first design, HarmBench/MultiJail results, Limitations
- **Cut heavily**: R equation details, Domain protocols, Output Gate details, Governor orchestration, Maqam-to-Safety origin chain, A/B calibration details
- **Move to appendix** (doesn't count toward limit): Full mode profile tables, detailed pipeline diagrams, MLCommons mapping, FanarGuard comparison details

### 3. Mandatory Sections (add if missing)

- **Limitations section** (after Conclusion — mandatory, doesn't count toward page limit). The paper has a limitations subsection inside Discussion but it needs to be a standalone section.
- **Ethics statement** (recommended, doesn't count toward page limit)
- **Responsible NLP checklist** (required at ARR submission time)

### 4. Content Improvements (to strengthen competitiveness)

Based on what a reviewer would flag:

- **Evaluation weakness**: HarmBench 74.3% is below state-of-the-art classifiers. The paper frames this as "zero-training" but reviewers will compare raw numbers. Need to either:
  - Add more benchmarks (Arabic-specific: ADHAR, SOD datasets)
  - Frame the evaluation more carefully as "interpretability vs accuracy" tradeoff
  - Include human evaluation on Arabic dialectal examples
- **Ablation study**: No ablation showing what each component (H, I, E channels; hysteresis; safety gates) contributes individually
- **Comparison fairness**: The FanarGuard comparison (Section 6.7) is structural, not empirical. Running AATIF and FanarGuard on the same test set would be much stronger.
- **Independent validation**: The held-out F1=1.0 note already flags that "cases informed the refinement" — need truly blind test set

### 5. Bibliography

Convert from `\begin{thebibliography}` to BibTeX (`.bib` file) — standard practice for *ACL venues and makes the process cleaner.

---

## Best Track for AATIF

| Track | Fit | Why |
|-------|-----|-----|
| **Safety / Ethics / Trustworthy AI** | ★★★★★ | Direct match — governance equation for LLM safety |
| **Multilingual / Arabic NLP** | ★★★★☆ | Arabic-first design, dialect-aware, but safety is the core contribution |
| **Language Modeling** | ★★★☆☆ | The paper sits above the LLM, not inside it |
| **Interpretability** | ★★★☆☆ | Interpretable equation is a selling point, but the paper isn't about interpretability methods |
| **Main / General** | ★★☆☆☆ | Too niche for general track, better in specialized area |

**Recommended ARR track keyword**: "Ethics, Bias, and Fairness" or "Safety & Robustness" (depending on exact ARR keyword list for the cycle)

---

## Recommended Submission Order

### Priority 1: ArabicNLP 2027 (or equivalent Arabic NLP workshop)

**Why first**: The 4-model review said PASS for workshop, and ArabicNLP is the single best venue in the world for this paper. ArabicNLP 2027 will likely be co-located with ACL 2027 or NAACL 2027. Watch for CFP announcements (~late 2026).

**Action**: Track ArabicNLP 2027 CFP. Expected deadline ~February-March 2027.

### Priority 2: EACL 2027 (ARR August 3, 2026)

**Why second**: Earliest available ARR cycle. Even if the paper doesn't get into EACL main, ARR reviews carry over — you can use the same reviews to commit to NAACL 2027 or ACL 2027 later.

**Action now**: Start reformatting to ACL style immediately. You have 5 weeks.

**Risk**: Main conference is a stretch. But submitting to ARR is never wasted — reviews are reusable.

### Priority 3: Safety/Ethics workshops at EACL/NAACL/ACL 2027

**Why**: Workshop-level acceptance is realistic. Look for:
- TrustNLP Workshop (has appeared at ACL 2026, may appear at EACL 2027)
- AbjadNLP (Workshop on NLP for Arabic Script, appeared at ACL 2026)
- Any new workshop on AI governance, safety guardrails, or responsible AI

**Action**: Watch workshop CFPs starting ~October 2026.

### Priority 4: NAACL 2027 or ACL 2027 main conference

**Why last**: Most competitive venues. Only attempt after incorporating EACL ARR reviewer feedback.

---

## 5-Week Action Plan (for EACL 2027 ARR deadline: August 3, 2026)

### Week 1 (June 25 – July 1)
- [ ] Download ACL style files
- [ ] Convert paper format to two-column ACL style
- [ ] Identify what fits in 8 pages vs. what goes to appendix

### Week 2 (July 2 – July 8)
- [ ] Cut paper to 8 pages (ruthless editing)
- [ ] Move supplementary material to appendix
- [ ] Write standalone Limitations section

### Week 3 (July 9 – July 15)
- [ ] Add ablation study (if time permits)
- [ ] Strengthen evaluation section
- [ ] Write Ethics statement
- [ ] Convert bibliography to BibTeX

### Week 4 (July 16 – July 22)
- [ ] Complete the Responsible NLP checklist
- [ ] Proofread and polish
- [ ] Ask someone to read it (fresh eyes)

### Week 5 (July 23 – August 3)
- [ ] Final formatting check against ACL style requirements
- [ ] Create OpenReview account (if not already)
- [ ] Submit to ARR by August 3, 2026 AoE
- [ ] Complete author registration by August 5, 2026

---

## Honest Summary

The AATIF paper has a genuine contribution (interpretable multiplicative safety equation with Arabic-first design). But:

1. **We missed ArabicNLP 2026** — the best venue, deadline was today
2. **Main conferences are a stretch** — the review feedback was clear about this
3. **Workshops are the realistic first step** — and that's a legitimate achievement
4. **EACL 2027 ARR (August 3)** is the next actionable deadline — 5 weeks to reformat
5. **The biggest work** is cutting 20 pages to 8 — this requires hard decisions about what stays

The ARR system is actually good news: submit once, get reviews, and commit to whichever conference fits. One submission effort can serve multiple venues.
