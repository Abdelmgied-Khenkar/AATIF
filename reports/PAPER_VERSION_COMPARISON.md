# AATIF Paper Version Comparison

**Generated:** 2026-06-20  
**Purpose:** Help the Architect choose ONE official version going forward.

---

## Quick Summary

| | `aatif_paper_arxiv.tex` | `aatif_paper_v2.tex` |
|---|---|---|
| **File size** | 48,607 bytes | 53,148 bytes |
| **Lines** | 478 | 589 |
| **Last modified** | June 20, 11:24 UTC | June 20, 07:16 UTC |
| **Framing** | Experience report / conjectures paper | Technical system / equation paper |
| **Uploaded to Zenodo?** | No | **Yes** |

The arxiv file was modified **later** (11:24) but the v2 file is the one that was **uploaded to Zenodo**.

---

## 1. Title

| Version | Title |
|---|---|
| **arxiv** | "AATIF: A Practitioner-Derived Framework of Conjectures for LLM Governance" |
| **v2** | "AATIF: A Multiplicative Governance Equation for Arabic-First LLM Safety" |

**Plain language:** The arxiv title sells it as a "collection of ideas from observation." The v2 title sells it as a "math-based safety system for Arabic." The v2 title is more specific and more publishable — it tells the reader exactly what they're getting.

---

## 2. Author Block

| Detail | arxiv | v2 |
|---|---|---|
| Name | Abdulmjeed Ibrahim Khenkar | Same |
| Affiliation | Independent Researcher | Same |
| Location | **Tallahassee, FL, USA** | **Not listed** |
| Email | abdulmjeed.ibrahem@gmail.com | Same |

**Note:** The arxiv version includes "Tallahassee, FL, USA." The v2 drops it. Check which is correct for the official version.

---

## 3. Abstract

The two abstracts are **completely different documents** — not minor edits of each other.

**arxiv abstract** focuses on:
- Inductive methodology (observation-first)
- 73 governance conjectures
- Seven-step pipeline
- Three highlighted areas: constraint density, EQC, Tri-Engine Protocol
- Tested across four LLM platforms

**v2 abstract** focuses on:
- The S equation (full formula given in abstract)
- 169 curated anchors
- Benchmark results (74.3% HarmBench, 74.7% vs 69.3% MultiJail)
- F1 scores: in-sample 0.984, held-out 0.9615
- 1,524 deterministic tests
- Arabic dialect hyperbole (35 anchors)
- Hysteresis, CBRN gates, mode profiles

**Plain language:** The arxiv abstract reads like a philosophy/methodology paper. The v2 abstract reads like an engineering paper with hard numbers. For publication, the v2 abstract is stronger because reviewers can immediately see measurable results.

---

## 4. Key Numbers

This is where the versions **disagree** and the differences matter:

| Number | arxiv | v2 | Which is correct? |
|---|---|---|---|
| **H anchor count** | 132 (footnote says "expanded to 169") | **169** throughout | v2 is current |
| **Dialect hyperbole anchors** | 28 | **35** | v2 is current |
| **Test count** | **164** | **166** (now 1,524) | Both stale — current is 1,524 |
| **θ (harm threshold)** | 0.40 | 0.40 | Same |
| **α (steepness)** | 10 | 10 | Same |
| **w1, w2** | 2.0, 1.5 | 2.0, 1.5 | Same |
| **HarmBench safety detection** | 74.3% | 74.3% | Same |
| **MultiJail Arabic** | 74.7% | 74.7% | Same |
| **MultiJail English** | 69.3% | 69.3% | Same |
| **In-sample F1** | 0.984 (mentioned) | 0.984 (with full table) | Same value, v2 has more detail |
| **Held-out F1** | Not mentioned | **0.9615** (56 unseen cases) | Only in v2 |
| **S9 (Weapons) anchors** | 4 | **12+** | v2 is current |
| **S10 (Hate) anchors** | 38+ | **41+** | v2 is current |
| **S11 (Self-Harm) anchors** | 4 | **6+** | v2 is current |

**Bottom line:** The arxiv file has **stale numbers** from before the anchor expansion. The v2 file has the current, post-expansion numbers.

---

## 5. Sections Structure

### arxiv has these sections:
1. Introduction
2. Related Work (5 subsections: Alignment, Mechanistic Basis, Inductive Approaches, Arabic Safety, Benchmarks, Positioning)
3. **Methodology** (the 7-step inductive pipeline — detailed)
4. **Selected Governance Conjectures** (10 full conjectures with observations, predictions, literature)
5. Computational Engine and Experimental Evaluation
6. Discussion
7. Conclusion

### v2 has these sections:
1. Introduction (gap-driven: 3 explicit gaps)
2. Related Work (3 subsections: Alignment, Arabic Safety, Benchmarks)
3. **The AATIF Governance Equation** (definition, properties, 3 scorers, hysteresis, safety gates, mode profiles, ambiguity/jailbreak)
4. **Arabic-First Design** (meaning density hypothesis, dialect hyperbole table with examples, maqam-to-safety origin chain)
5. Experimental Evaluation (test suite, HarmBench, MultiJail, **A/B calibration table**, **held-out validation**, MLCommons, **FanarGuard comparison table**)
6. Discussion
7. Conclusion

### What's in arxiv but NOT in v2:
- The full 7-step methodology section
- 10 detailed governance conjectures (#001 Clarification, #063 Constraint Density, #062 Question Legitimacy, #069 Bounded Claims, #070 Possibility Space, #067 Pressure-Reveal, #057 Arabic Semantic Layer, #065 Maqam Architecture, #071 Dual-Level Description, #072 Tri-Engine Deliberation)
- The "Inductive and Observation-Based Approaches" subsection in Related Work
- The "Positioning" subsection

### What's in v2 but NOT in arxiv:
- Full S equation derivation with formal properties
- Three scorers detailed with anchor counts (H=169, I=44, E=32)
- Hysteresis controller section
- Safety gates: Law Ω (CBRN) and Law Ξ (Override Lock)
- Mode profiles table (4 profiles with parameters)
- Ambiguity pre-check and jailbreak detection
- Arabic-First Design section (meaning density hypothesis, dialect hyperbole table with Arabic examples, maqam-to-safety origin chain)
- Full A/B calibration table (θ sweep from 0.20 to 0.55)
- Held-out validation results (F1 = 0.9615)
- FanarGuard comparison table
- Statistical caution on the MultiJail 5.4-point gap

**Plain language:** The arxiv version tells the *story* of how AATIF was discovered (the journey). The v2 version describes *the system itself* (the destination). Both have unique valuable content. The 10 conjectures in arxiv are not in v2 at all. The equation details and Arabic design in v2 are not in arxiv.

---

## 6. References

| Detail | arxiv | v2 |
|---|---|---|
| **Total references** | ~38 | ~23 |
| **FanarGuard** | Yes (arXiv:2511.18852) | Yes (same) |
| **Placeholder arXiv IDs (2411.XXXXX)?** | **No** | **No** |
| **Zenodo DOI** | 10.5281/zenodo.20673292 | Same |
| **GitHub URL** | github.com/Abdelmgied-Khenkar/AATIF | Same |

### References only in arxiv (not in v2):
- Apollo Research (2025) — stress testing deliberative alignment
- Buçinca et al. (2021) — cognitive forcing functions
- Cemri et al. (2025) — multi-agent LLM failures
- Croskerry (2003) — clinical decision-making
- Fogliato et al. (2022) — human-AI workflow
- Gilligan (1982) — dual-voice model
- Graber et al. (2005) — diagnostic error
- Hammons (2026) — relational ethics for human-AI
- Ku et al. (2026) — levels of analysis for LLMs
- Levine et al. (2024) — triple theory of moral cognition
- Mischel & Shoda (1995) — cognitive-affective personality
- Passi & Barocas (2019) — problem formulation and fairness
- Shanahan et al. (2023) — role play with LLMs
- Stanovich (2011) — rationality and reflective mind
- Stilgoe et al. (2013) — responsible innovation
- Yip et al. (2024) — informal governance norms

**Plain language:** The arxiv version has 15+ extra references because it discusses the conjectures and their theoretical backing. The v2 version keeps only the references needed for the equation and benchmarks. Neither version has fake or placeholder arXiv IDs.

---

## 7. Known Issues

### Issues in arxiv:
- **Stale anchor count:** Says 132 in main text (footnote mentions 169). The actual system has 169 now.
- **Stale test count:** Says 164. The actual test suite has 1,524 test functions.
- **Stale dialect anchors:** Says 28. Actual count is 35.
- **Stale MLCommons anchor counts:** S9=4, S10=38+, S11=4. All lower than current values.
- **No held-out validation:** Only mentions in-sample calibration. No F1 = 0.9615 result.
- **No calibration table:** Mentions calibration but doesn't show the θ sweep data.
- **Location in author block:** "Tallahassee, FL, USA" — verify this is current and desired.

### Issues in v2:
- **Missing conjectures:** The 10 governance conjectures are gone. They appear briefly in the Discussion, but without the full observations, predictions, or literature links.
- **Missing methodology:** The 7-step inductive pipeline is not described. It's mentioned in passing but not detailed.
- **Fewer references:** Dropped ~15 references from social science, philosophy, and cognitive science. This weakens the interdisciplinary positioning.

### Issues in both:
- Neither has a proper arXiv ID yet (no submission recorded).
- Both cite the same Zenodo DOI — good, consistent.

---

## 8. Recommendation

**v2 is the stronger paper for publication.** Here's why:

1. **Numbers need updating** — 169 anchors, 1,524 tests (was 166), 35 dialect anchors, held-out F1 = 0.9615.
2. **It was uploaded to Zenodo** — it's already the public record.
3. **It's structured as a technical paper** — gap-driven intro, equation, evaluation, comparison. This is what reviewers expect.
4. **It has the held-out validation** — the arxiv version lacks this, which is a significant weakness.
5. **The FanarGuard comparison table** makes the positioning clear.

**But don't throw away the arxiv content.** The 10 conjectures and the 7-step methodology are valuable material that could become:
- A companion paper ("AATIF Field Notes: 73 Governance Conjectures from Sustained LLM Observation")
- A supplementary document alongside the main paper
- Chapter material for the book

**If you pick v2 as official:** consider adding the "Tallahassee, FL, USA" location if still relevant, and renaming the file to something like `aatif_paper_official.tex` to avoid future confusion.

**If you want one merged paper:** the conjectures and methodology from arxiv could be integrated into v2 as additional sections, but this would make the paper significantly longer (~15+ pages).

---

*This report compares the two files as they exist on disk. No changes were made to either file.*
