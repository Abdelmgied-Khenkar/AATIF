---
name: aatif-academic-paper
description: "Write, edit, or rewrite AATIF academic papers and field notes in LaTeX. Use this skill whenever the user asks to write a paper, edit the paper, fix something in the paper, add a section, update numbers, write a new field note, or do anything involving academic writing for the AATIF project. Triggers on: paper, ورقة, field note, LaTeX, .tex, academic writing, section, abstract, rewrite, بحث, مقال علمي. Also use when updating benchmark results, anchor counts, or any quantitative claims in the paper."
---

# AATIF Academic Paper Skill

## Why This Exists

The Architect is an independent researcher building AATIF — a mathematical governance framework for LLM safety. The paper gets revised frequently as the code evolves, benchmarks update, and new insights emerge. This skill ensures every edit is accurate, verified, and consistent with the actual codebase.

## The Golden Rules

**Rule 1: Never write a number in the paper without verifying it from the source code or data file first.**

**Rule 2: Never cite a paper, author, or research that you haven't verified exists.**

**Rule 3: Never say "done" without running the Mandatory Pre-Completion Checklist (below).**

The Architect's correction protocol applies to all academic writing:
ملاحظة → إيقاف → استفسار → سبب الخطأ → العودة → تصحيح → تفادي مستقبلاً → نكمل

---

## Mandatory Pre-Completion Checklist

**This checklist MUST be executed — not just read — before reporting any paper edit as complete. Every item requires action, not memory. Skip nothing.**

### A. Citation & Reference Verification

For EVERY citation or reference in the paper (including ones that were already there before your edit):

1. **Web search the arXiv ID or DOI** — confirm that the paper exists with those exact authors, that exact title, and that exact venue/year.
2. **NEVER write an author name from memory** — always verify from the actual arXiv page, journal page, or DOI landing page. Author name hallucination is one of the most common LLM failures.
3. **Cross-check the claim** — if you cite "X showed Y", verify the paper actually says Y.
4. **If you cannot verify a citation**, mark it in the .tex source with:
   ```latex
   % [UNVERIFIED] Could not confirm this reference — verify before submission
   ```
   And flag it explicitly to the Architect in your report.
5. **Check for phantom references** — look for any `\cite{}` key that has no corresponding `\bibitem` or `.bib` entry, and vice versa.

### B. Number Verification

For EVERY number, count, parameter, threshold, or quantitative claim in the paper:

1. **Parameters (w₁, w₂, α, θ)** → `grep` or `Read` the actual values from `engine/aatif_s_equation.py`. Check `DEFAULT_PARAMS` and `GATED_PROFILES`.
2. **Anchor counts (H, I, E)** → Count the actual anchors from the source files:
   - H anchors → `engine/aatif_semantic_scorer.py` (count all anchors in HARM_ANCHORS list)
   - I anchors → `engine/aatif_intent_scorer.py`
   - E anchors → `engine/aatif_emotion_scorer.py`
   - Dialect-hyperbole anchors → check the dialect disambiguation section in `engine/aatif_semantic_scorer.py`
3. **Benchmark results** → Read the actual JSON files in `benchmarks/*.json`. Do not reuse numbers from memory or from a previous session.
4. **Test counts** → Run `pytest --co -q` in the engine directory, or count test functions with `grep -c "def test_"`. Count subtests separately.
5. **Decision thresholds** → Check `THRESHOLDS` dict in `engine/aatif_s_equation.py`.
6. **Field note count** → `ls field-notes/ | wc -l` or count the actual files.
7. **NEVER write a number from memory.** If you find yourself about to type a number without having just read it from a file in this session, STOP and go read the file.

### C. Table Verification

For EVERY table in the paper:

1. **Decision thresholds table** → verify every row against `THRESHOLDS` in `aatif_s_equation.py`
2. **Mode profiles table** → verify every profile against `GATED_PROFILES` in `aatif_s_equation.py`
3. **Anchor coverage tables** → count actual anchors per category from the scorer files
4. **Benchmark results tables** → verify every cell against the corresponding `benchmarks/*.json` file
5. **No row may contain a number that was not read from a file during this editing session.**

### D. Final Sweep (before saying "done")

1. **Run through EVERY claim** in the sections you edited — verify each has a verifiable source (code, data file, or verified citation).
2. **Search for XXXXX placeholders**: `grep -n "XXXXX" aatif_paper_v2.tex` — none should remain.
3. **Search for TODO/TBD markers**: `grep -n "TODO\|TBD\|FIXME\|XXX" aatif_paper_v2.tex` — resolve or flag each one.
4. **Search for [UNVERIFIED]**: `grep -n "UNVERIFIED" aatif_paper_v2.tex` — report any that remain.
5. **Compile the paper**: run `pdflatex aatif_paper_v2.tex` — verify zero errors (warnings are OK to report but not blockers).
6. **Report to the Architect**: list every change made, every number verified, and every item flagged.

---

## Citation Verification Protocol

LLMs hallucinate references. This is a known, serious problem. Every citation in the paper MUST be verified as real before inclusion.

**Before adding ANY citation (\cite, \citet, \citep):**

1. **Search for the paper** — Use web search to confirm the paper exists with that exact title, those exact authors, and that exact year
2. **Verify the venue** — Confirm where it was published (conference, journal, arXiv). Don't guess.
3. **Check the DOI/URL** — If you include a DOI or URL, visit it to confirm it resolves
4. **Cross-check claims** — If you cite a paper for a specific claim ("X showed that Y"), verify that the paper actually says that

**What to do when unsure:**
- If you can't verify a reference → DON'T include it. Leave a `% TODO: verify citation` comment
- If you remember a concept but not the exact paper → describe the concept without citing, or ask the Architect
- If two sources conflict on who published first → cite both and note the discrepancy

**Red flags for hallucinated citations:**
- Author names that "sound right" but you can't find online
- Papers with suspiciously perfect titles that match exactly what you need
- Conferences or journals you can't verify exist
- Years that don't match the actual publication
- arXiv IDs that are placeholder format (e.g., arXiv:2411.XXXXX)

**Known verified references in the AATIF paper:**
- FanarGuard (Fatehkia, M., Altinisik, E., and Sencar, H. T., 2025) — Arabic LLM safety, arXiv:2511.18852, EACL 2026
- Llama Guard (Inan et al., 2023) — Meta's safety classifier
- bge-m3 (Chen et al., 2024) — multilingual embedding model, BAAI
- HarmBench (Mazeika et al., 2024) — red-teaming benchmark
- MultiJail (Deng et al., 2024) — multilingual jailbreak
- MLCommons AI Safety v0.5 (2024) — hazard taxonomy
- ADHAR (2023) — Arabic hate speech dataset

⚠️ Even these "known" references should be re-verified if you're updating their details (page numbers, exact titles, URLs).

⚠️ **FanarGuard correction**: Previous versions of this skill listed "Nagoudi et al., 2024" and "EMNLP" — this was WRONG. The verified authors are Fatehkia, M., Altinisik, E., and Sencar, H. T., the arXiv ID is 2511.18852, and the venue is EACL 2026. This is exactly why Rule 2 and the Pre-Completion Checklist exist.

**The rule is simple: if you didn't verify it exists, it doesn't go in the paper. الورقة مش مكان للتخمين.**

## Current Paper State

- **File**: `~/Desktop/AATIF-academic/aatif_paper_v2.tex`
- **Original (backup)**: `~/Desktop/AATIF-academic/aatif_paper_arxiv.tex`
- **Rewrite plan**: `~/Desktop/AATIF-academic/PAPER_REWRITE_PLAN.md`
- **Engine code**: `~/Desktop/AATIF-academic/engine/`
- **Benchmarks**: `~/Desktop/AATIF-academic/benchmarks/`
- **Field notes**: `~/Desktop/AATIF-academic/field-notes/`
- **Limitations**: `~/Desktop/AATIF-academic/LIMITATIONS.md`
- **Published**: Zenodo DOI 10.5281/zenodo.20673292

## Paper Structure (7 sections)

The paper follows this structure — the S equation appears on PAGE ONE, not buried:

1. **§1 Introduction** — Three structural gaps → AATIF as solution → S equation immediately (Equation 1)
2. **§2 Related Work** — Organized around the three gaps, not a general survey
3. **§3 The AATIF Governance Equation** — THE core section:
   - S equation definition and non-compensability proof
   - Three scorers (H, I, E) with anchor details
   - Hysteresis controller
   - Law Ω (CBRN) and Law Ξ (Override Lock)
   - Mode profiles table
   - Ambiguity pre-check and jailbreak handler
4. **§4 Arabic-First Design** — Three subsections:
   - Meaning density hypothesis (كثافة المعنى) — the variable is density, not language
   - Dialect hyperbole disambiguation — 35 anchors, zero false positives
   - Maqam-to-safety origin chain — 6-step intellectual origin story, not music theory
5. **§5 Experimental Evaluation** — Tables for each benchmark:
   - 439 pytest-collected tests (including parametrized held-out cases)
   - HarmBench (236 behaviors)
   - MultiJail (75 prompts, AR vs EN)
   - Held-out validation (56 cases)
   - A/B calibration (θ sweep)
   - MLCommons coverage mapping
   - FanarGuard comparison
6. **§6 Discussion** — Contributions, honest limitations, conjectures as research program (NOT contribution)
7. **§7 Conclusion** — Crisp half-page summary

## Verification Checklist

Before writing ANY number in the paper, verify from the actual source:

| Claim | Verify From |
|-------|------------|
| Anchor counts (H, I, E) | `grep` the actual anchor lists in `engine/aatif_semantic_scorer.py`, `aatif_intent_scorer.py`, `aatif_emotion_scorer.py` |
| Dialect-hyperbole anchors | Count from `engine/aatif_semantic_scorer.py` dialect disambiguation section |
| S equation parameters | Read `engine/aatif_s_equation.py` default profile |
| Test count | Run `pytest --co -q` in the engine directory, or count test functions |
| HarmBench results | Read `benchmarks/harmbench_results_bge.json` |
| MultiJail results | Read `benchmarks/multijail_results_bge.json` |
| Held-out results | Read `benchmarks/held_out_results.json` |
| θ value | Check `engine/aatif_s_equation.py` DEFAULT_PARAMS |
| Decision thresholds | Check `THRESHOLDS` in `engine/aatif_s_equation.py` |
| Mode profiles | Check `GATED_PROFILES` in `engine/aatif_s_equation.py` |
| Hysteresis thresholds | Read `engine/aatif_hysteresis.py` |
| Field note count | Count files in `field-notes/` directory |
| Citations | Web search to verify each paper exists |

**Do NOT rely on memory files, README, previous paper versions, or THIS SKILL FILE for numbers. Always go to the code.**

## Current Verified Numbers (as of 2026-06-22)

These were verified via pytest --collect-only, code inspection, and direct counting. **RE-VERIFY before using — these go stale:**

- S equation: `S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))]`
- Parameters (default profile): w₁=2.0, w₂=1.5, α=10, θ=0.40
- ⚠️ θ(default) is 0.40 — NOT 0.55. Previous drafts had 0.55 which was wrong.
- Hard override: H > 0.7 → SAFE_FREEZE
- H scorer: 169 anchors in HARM_ANCHORS (file: `engine/aatif_semantic_scorer.py`)
- I scorer: 44 anchors in INTENT_ANCHORS (file: `engine/aatif_intent_scorer.py`)
- E scorer: 32 anchors in EMOTION_ANCHORS (file: `engine/aatif_emotion_scorer.py`)
- Total anchors across all three scorers: 245
- Dialect-hyperbole anchors: 35
- Total tests: 439 (pytest-collected, including parametrized held-out cases)
- GATED_PROFILES (4 profiles in `engine/aatif_s_equation.py`):
  - `default`: α=10, θ=0.40, w₁=2.0, w₂=1.5
  - `high_sensitivity`: α=15, θ=0.30, w₁=2.0, w₂=1.0
  - `relaxed`: α=8, θ=0.55, w₁=3.0, w₂=2.5
  - `balanced_strict`: α=10, θ=0.40, w₁=2.0, w₂=1.5
- ⚠️ Profile formerly called "creative" was renamed to "relaxed" (2026-06-20). "Creative" as a DOMAIN name still exists — don't confuse the two.
- ⚠️ high_sensitivity θ is 0.30 — NOT 0.45. Previous versions had 0.45 which was a logic inversion (corrected 2026-06-20).
- θ(d) domain parameterization (DOMAIN_CONFIG): Healthcare=0.25, Education=0.30, General=0.40, Tech=0.40, E-Commerce=0.40, Creative=0.50
- Held-out F1: 0.9615 (56 cases, precision=0.96, recall=0.96)
- ⚠️ In-sample F1 was 0.984 — this is NOT the generalizable number
- ⚠️ Held-out set partially informed the anchor refinement — not fully blind. This caveat MUST appear in the paper.
- HarmBench: 74.3% safety-category, 100% chemical/biological
- MultiJail: Arabic 74.7% vs English 69.3% (observation, not conclusive — may reflect anchor coverage asymmetry)
- A/B calibration: θ=0.40 optimal
- Field notes: 78 (#001-#078)

⚠️ These numbers WILL change as the code evolves. Always re-verify from the code, not from this list.

## Key Writing Principles

1. **S equation on page 1** — The equation IS the contribution. It leads everything.
2. **Conjectures are motivation, not contribution** — The 73+ field notes inspired the math; they are NOT the paper's claims.
3. **Arabic-first is scientific, not cultural** — Meaning density (كثافة المعنى) is a measurable variable. Arabic was chosen because it's the densest language tested, not out of identity.
4. **Maqam is origin story, not music theory** — Frame the maqam connection as: "this observation led to this design decision." The chain: quarter-tone gap → prosody → text loses tone → textual spectrogram → duress detection → multiplicative gate.
5. **Honest limitations** — State what AATIF doesn't do (no sarcasm, no implicit harm, limited benchmarks). Reviewers respect honesty. See LIMITATIONS.md.
6. **Write the paper that matches the code** — This was the consensus of all 4 model reviews (Gemini, Grok, DeepSeek, ChatGPT).
7. **No overclaims** — Don't say "first system to..." — say "combines, for the first time in a single deployable system..." Each component exists separately; the combination is the contribution.
8. **Human-over-the-loop** — AATIF is human-over-the-loop governance (human designs rules, system applies them autonomously), NOT human-in-the-loop (human approves each decision).
9. **Anchors are not training** — Anchors are a reference list compared via cosine similarity. No optimization, no gradient descent, no weight updates. This is zero-fine-tuning extensibility.

## LaTeX Requirements

- Use `pdflatex` (not XeLaTeX) for portability
- Arabic text is romanized with transliteration (e.g., `har\=arat al-kalima`)
- For proper Arabic rendering, add XeLaTeX comment block (already in v2 header)
- Packages: amsmath, amssymb, natbib, booktabs, hyperref, geometry
- Target: 10-12 pages content + bibliography
- Use `\citet{}` and `\citep{}` for citations (natbib)

## Field Notes

78 field notes exist in `~/Desktop/AATIF-academic/field-notes/`. Key ones for the paper:

- FN#003: Mercy Precedes Justice (Law α)
- FN#005: Five Tiers of Intent (Law δ)
- FN#017: Load-Bearing Human (Law α-1) — "الإنسان المُثقَل" NOT "الحامل"
- FN#055: Architected Scientific Framing
- FN#069: Bounded Claim Law
- FN#075: Meaning Density Hypothesis
- FN#078: Arabic-First Embedding Hypothesis

## Target Venues

From the rewrite plan:
- EMNLP 2026 (Safety track)
- ACL 2027 (Multilingual track)
- NAACL 2027
- AACL-IJCNLP 2026
- EACL 2027

## Editing Workflow

When asked to edit the paper:

1. **Read the current .tex file** (or the relevant section)
2. **Understand what needs to change** — ask if unclear
3. **Verify all numbers** from source code before writing (see Mandatory Pre-Completion Checklist §B)
4. **Verify all citations** — web search every reference (see Mandatory Pre-Completion Checklist §A)
5. **Make the edit** using the Edit tool
6. **Run the full Pre-Completion Checklist** (§A through §D)
7. **Compile and check** — run pdflatex to verify no errors
8. **Report what changed** — file name + what changed + plain language + any [UNVERIFIED] flags

When asked to write a new section or rewrite:

1. Read PAPER_REWRITE_PLAN.md for structure guidance
2. Read the relevant engine code for accuracy
3. Write the content
4. Verify every number from code (Checklist §B)
5. Verify every citation via web search (Checklist §A)
6. Verify every table row (Checklist §C)
7. Run full sweep (Checklist §D)
8. Compile
9. Report

## Author Info

- Author: Abdulmjeed Ibrahim Khenkar
- Affiliation: Independent Researcher
- Email: abdulmjeed.ibrahem@gmail.com
- The Architect is NOT a specialist — he's an independent outsider building solo via AI collaboration. The paper should reflect this honestly.
