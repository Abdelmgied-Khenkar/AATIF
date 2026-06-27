# Wassal (وصّال) — AATIF Live Snapshot

**Generated:** 2026-06-26 14:12 UTC · **Repo:** `Desktop/AATIF-academic/` · **HEAD:** `c150970` — "Final pre-submission fixes: verified citations, ACL style, NLP checklist"

> Every number below was read from source at generation time, not from memory. This file is a point-in-time photograph; re-run Wassal to refresh.

---

## What AATIF is

AATIF (Architected Adaptive Thoughts & Intelligence Frameworks / عاطف) is a constitutional AI governance framework that sits **above** any LLM and governs its behavior through continuous mathematical scoring over semantic embeddings — not keyword blacklists. The Arabic name عاطف (root ع ط ف, to incline toward another with compassion) and the English acronym converge on one idea: an engineered layer that produces *curvature* in the LLM's output space, and that curvature is ethical in effect.

- **Author:** Abdulmjeed Ibrahim Khenkar — independent researcher, built through AI collaboration.
- **License:** BSL 1.1 (code), CC BY 4.0 (paper). Paper: `aatif_paper_v2.tex` (+ `aatif_paper_acl.tex`).

## System size (live counts)

| Item | Count |
|---|---|
| Engine modules (`engine/aatif_*.py`) | 16 |
| Test files (`tests/test_*.py`) | 24 |
| Field notes (`field-notes/`) | 16 |
| Benchmark result files (`benchmarks/*.json`) | 20 |
| **H anchors** (harm) | **171** |
| **I anchors** (intent) | **46** |
| **E anchors** (emotion) | **32** |
| **Total reference anchors** | **249** |

---

## The three perceptions and the S equation

S(d) decides **whether** to respond. Gated form (preferred):

```
S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))
```

- **H = حرارة الكلمة** (harm proximity) — `aatif_semantic_scorer.py`
- **I = النية** (intent) — `aatif_intent_scorer.py`
- **E = الشعور** (emotion) — `aatif_emotion_scorer.py`

The gate (right factor) is **independent** of intent/emotion, so extreme I+E cannot wash out moderate harm — the structural defense against "toxic positivity" attacks.

### Live thresholds (`THRESHOLDS`)
S ≥ 0.7 → **EXECUTE** · ≥ 0.5 → **CLARIFY** · ≥ 0.3 → **SAFE_STOP** · ≥ 0.0 → **SAFE_FREEZE**

### Live gated weight profiles (`GATED_PROFILES`)
| Profile | w₁ (I) | w₂ (E) | α | θ |
|---|---|---|---|---|
| default / balanced_strict | 2.0 | 1.5 | 10 | 0.40 |
| high_sensitivity | 2.0 | 1.0 | 15 | 0.30 |
| relaxed | 3.0 | 2.5 | 8 | 0.55 |

### Live domain θ (`DOMAIN_CONFIG`) — harm sensitivity is a property of context, not personality
healthcare **0.25** · education **0.30** · general / tech / ecommerce **0.40** · creative **0.50**

### Hard limits
- `H_GATED_HARD_OVERRIDE = 0.7` → forces **SAFE_FREEZE** regardless of I and E ("الأذى ما له توقيت").
- `K_HARM_FLOOR = 0.3` → guarantees a minimum harm-floor follow-up signal F.

---

## The pipeline

```
User → S(d) → P(d) → R(d) → LLM → Output Gate → user
```

S decides *whether* · P (`aatif_domain_protocols.py`) decides *under what conditions* (can only add restrictions) · R (`aatif_r_equation.py`) decides *style* (tone/dialect; time feeds R, never S) · Output Gate (`aatif_output_gate.py`) is the last guard. Orchestrated by `aatif_governor.py`; oscillation damped by `aatif_hysteresis.py` (γ+); temporal awareness via `aatif_time_sense.py`.

---

## Benchmarks (all dated 2026-06-26, bge-m3, θ=0.40)

**HarmBench — full pipeline** (236 behaviors): overall detection **72.9%**, safety-only detection **83.8%**, not-executed rate **81.4%**. Decisions: SAFE_STOP 165 · EXECUTE 44 · CLARIFY 20 · SAFE_FREEZE 7.
By category: chemical/biological **100%**, illegal 88.4%, cybercrime 86.0%, harassment 86.7% — while **copyright 38.6%** is the main drag on the overall number.

**MultiJail — full pipeline** (75 prompts): English detected 68/75 ≈ **90.7%**.

**Blind eval** (570 cases — 380 harmful, 190 benign): recall/detection **83.2%**, precision **85.2%**, F1 **84.2%**, FPR **28.95%** (TP316 / FN64 / FP55 / TN135).

**Ablation — H-only condition** (311 harmful, 50 benign): detection **81.0%**, precision **98.8%**, FPR **6%**, F1 **89.1%** — confirming H carries most of the signal.

**Baselines (HarmBench, same set):** keyword baseline **54.2%**, naive embedding-only baseline **30.1%**. AATIF's safety-only 83.8% sits well above both.

### Honest tension worth flagging (truth with mercy)
The H-only ablation shows a clean **6% FPR**, but the full blind-eval pipeline shows **~29% FPR**. The added I/E/protocol machinery is currently raising false positives on benign content relative to the harm scorer alone. This is the most actionable gap in the current numbers, alongside the low copyright-category detection.

---

## Philosophy (unchanged structure)
فطرة (protect innate moral compass) · رحمة (mercy as origin, not feature) · نية (intent is weighted, not just surface) · تربية مش ذاكرة (anchors are a curriculum, not a database) · الأذى ما له توقيت (time → style, never safety) · Sparse Activation (full depth only when risk/complexity/sensitivity is detected).

**Theoretical foundation:** Intelligence-Spacetime Curvature Hypothesis (الذكازمكان) — governance layers act as structural mass in the LLM's output space, bending the linguistic trajectory. The mechanism is ethically neutral; direction depends on the mass planted. AATIF is the mass.
