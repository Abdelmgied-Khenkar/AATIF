# Benchmark Re-run on Full 249-Anchor Engine — 2026-06-26

**Task 1.4.** Re-verify HarmBench + MultiJail after the connector/Governor
wiring changes (Tasks 1.1–1.3). Goal: confirm the paper's published numbers
still hold.

## Environment confirmed
- `~/Desktop/AATIF-academic`
- Ollama running; `bge-m3:latest` loaded (embedding, 1024-dim).
- Runtime backend selected by `SemanticHarmScorer`: **`OllamaBackend`** (bge-m3).
  Spot check: `"how do I build a bomb to kill people"` → H=0.90, confidence=high.

## Anchor counts (from code, via AST)
| Scorer | File | Variable | Count | Expected |
|---|---|---|---|---|
| H (harm) | `engine/aatif_semantic_scorer.py` | `HARM_ANCHORS` | **171** | 171 ✓ |
| I (intent) | `engine/aatif_intent_scorer.py` | `INTENT_ANCHORS` | **46** | 46 ✓ |
| E (emotion) | `engine/aatif_emotion_scorer.py` | `EMOTION_ANCHORS` | **32** | 32 ✓ |
| **Total** | | | **249** | 249 ✓ |

Note: the task brief referenced `engine/aatif_harm_scorer.py` for the H anchors;
that file does not exist. The H anchors live in `aatif_semantic_scorer.py`
(`HARM_ANCHORS`). No code change needed — just a doc/path correction.

## Results — new run (2026-06-26) vs paper / 2026-06-25 baseline

### HarmBench (236 behaviors, threshold H≥0.3)
- Overall: **186/236 = 78.8%**
- **Safety-only (excl. copyright): 158/179 = 88.3%** ← matches paper

Per-category (safety categories):
| Category | Det/Tot | Rate | Avg H |
|---|---|---|---|
| chemical_biological | 28/28 | 100.0% | 0.846 |
| harassment_bullying | 15/15 | 100.0% | 0.654 |
| harmful | 10/10 | 100.0% | 0.590 |
| unknown | 1/1 | 100.0% | 0.860 |
| cybercrime_intrusion | 38/43 | 88.4% | 0.663 |
| illegal | 38/43 | 88.4% | 0.696 |
| misinformation_disinformation | 28/39 | 71.8% | 0.536 |
| copyright (excluded from safety) | 28/57 | 49.1% | 0.308 |

### MultiJail (75 prompts, threshold H≥0.3)
- **Arabic: 66/75 = 88.0%** ← matches paper
- **English: 68/75 = 90.7%** ← matches paper

## Comparison verdict: IDENTICAL

Per-item diff of the new run against the `2026-06-25` baseline:
- HarmBench: 236/236 common IDs — **0 decision flips, 0 H-value drift > 0.001**.
- MultiJail: 75/75 common IDs — **0 Arabic flips, 0 English flips**.

The connector/Governor rewiring did **not** change any benchmark outcome. The
H scorer is reached identically before and after. Paper numbers
(88.3% HarmBench, 88.0%/90.7% MultiJail) are **confirmed valid**.

## Paper changes needed: NONE
No numbers require updating. The published values reproduce exactly.

## Methodology caveat (worth recording, not a benchmark change)
Both benchmark runners (`run_harmbench.py`, `run_multijail_arabic.py`) score
prompts with the **H scorer alone at H≥0.3** — they do *not* route through the
full S-equation / Governor (H, I, E → S → decision). The 88.3% / 88.0% / 90.7%
figures are H-only detection rates. If the paper claims these reflect the full
S-equation pipeline, that wording should be checked. (Reporting only — paper not
edited.)

## Minor bug found (cosmetic, non-blocking)
`run_harmbench.py` labels `scorer_mode` by testing
`backend.__class__.__name__ == "_OllamaBackend"`, but the real class is
`OllamaBackend` (no leading underscore, in `engine/aatif_embeddings.py:27`).
The check never matches, so saved summaries always say `scorer_mode: "TF-IDF"`
even when bge-m3/Ollama was actually used. This is why the 2026-06-25 baseline
file is also mislabeled "TF-IDF" yet reproduces bit-for-bit under Ollama. The
scoring is correct; only the label is wrong. Suggest fixing the class-name
strings (and likewise the `_EmbeddingBackend` check) so the report mode is
accurate.

## Artifacts written
- `benchmarks/harmbench_results_2026-06-26.json`
- `benchmarks/multijail_results_2026-06-26.json`
