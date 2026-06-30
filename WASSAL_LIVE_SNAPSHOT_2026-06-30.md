# Wassal (وصّال) — Live AATIF Snapshot

**Generated:** 2026-06-30 (autonomous scheduled run)
**Source of truth:** `Desktop/AATIF-academic/` — every number below was read from source at generation time, not from memory.
**Engine HEAD:** `dc96dff` — "feat(engine): implement FN#058 context drift detection" (2026-06-30 05:02).

---

## 1. What AATIF is

AATIF (Architected Adaptive Thoughts & Intelligence Frameworks / عاطف) is a constitutional governance layer that sits **above** any LLM and decides — through continuous mathematical scoring over semantic embeddings, not keyword blacklists — whether to respond, under what conditions, and in what style. The Arabic root ع ط ف (to incline toward another with compassion) is the design origin: an engineered layer that bends output-space, and the bend is ethical in effect.

License: **BSL 1.1** (code), **CC BY 4.0** (paper `aatif_paper_v2.tex`).

---

## 2. Live counts (read this generation)

| Item | Current value | Source |
|---|---|---|
| **H anchors** (harm) | **261** | `aatif_semantic_scorer.py → HARM_ANCHORS` |
| **I anchors** (intent) | **91** | `aatif_intent_scorer.py → INTENT_ANCHORS` |
| **E anchors** (emotion) | **88** | `aatif_emotion_scorer.py → EMOTION_ANCHORS` |
| **Total anchors** | **440** | — |
| Engine modules | **32** | `engine/aatif_*.py` |
| Test files | **44** | `tests/test_*.py` |
| Field notes | **94** (FN001–FN082 + indices) | `field-notes/` |
| Benchmark result files | **24** | `benchmarks/*.json` |

---

## 3. The three equations (current parameters)

**S(d) — Safety. Decides WHETHER to respond.**

Gated (v2, preferred):
```
S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))
```
- **H** = حرارة الكلمة (harm proximity), **I** = النية (intent), **E** = الشعور (emotion) — all continuous, all from semantic anchors.
- The gate isolates harm suppression from intent/emotion, blocking the "toxic positivity" attack where high I+E compensates for moderate H.

**Decision thresholds** (`THRESHOLDS`): S ≥ 0.7 → EXECUTE · ≥ 0.5 → CLARIFY · ≥ 0.3 → SAFE_STOP · ≥ 0.0 → SAFE_FREEZE.

**Hard override** (`H_GATED_HARD_OVERRIDE = 0.7`): if H ≥ 0.7, decision is forced to SAFE_FREEZE regardless of I and E — "الاذي مالوش توقيت" (harm has no timing).

**Follow-up floor** (`K_HARM_FLOOR = 0.3`): F = max(D·(1−S), 0.3·H) — guarantees a minimum harm-aware follow-up even on high-S results.

**Gated profiles** (`GATED_PROFILES`):

| Profile | w₁ | w₂ | α | θ |
|---|---|---|---|---|
| default / balanced_strict | 2.0 | 1.5 | 10 | 0.40 |
| high_sensitivity | 2.0 | 1.0 | 15 | 0.30 |
| relaxed | 3.0 | 2.5 | 8 | 0.55 |

**θ(d) — domain-parameterized threshold** (`DOMAIN_CONFIG`): harm sensitivity is a property of context, not personality. Gate closes earliest where harm is physical/developmental:

| Domain | θ |
|---|---|
| healthcare | 0.25 |
| education | 0.30 |
| general / tech / ecommerce | 0.40 |
| creative | 0.50 |

**P(d) — Protocols. Decides UNDER WHAT CONDITIONS.** Deterministic rules engine (`aatif_domain_protocols.py`). Can only ADD restrictions, never remove. Action ladder: NONE → GUIDE → DISCLAIMER → WARNING → AGE_GATE → ESCALATE → EMERGENCY → BLOCK.

**R(d) — Style. Decides IN WHAT STYLE** (`aatif_r_equation.py`):
```
R = σ(w₃·T + w₄·V + w₅·G + w₆·D + bias)
```
T = time, V = voice/dialect, G = interaction gap, D = domain. Maps formal → balanced → warm → casual. Time feeds R (style), never S (safety).

**Pipeline:** User → S → P → R → Output Gate → user. Orchestrated by `aatif_governor.py`; last guard is `aatif_output_gate.py` (6 check layers). Decision oscillation is damped by `aatif_hysteresis.py` (γ+ law, SAFE_FREEZE fail-closed).

---

## 4. Latest benchmark results (as stored)

**HarmBench — full pipeline** (`harmbench_results_full_pipeline_2026-06-26.json`): 236 behaviors, overall detection **72.9%**, safety-only **83.8%**. By category: chemical/biological **100%**, illegal 88.4%, harassment 86.7%, cybercrime 86.0%, misinformation 66.7%, copyright **38.6%** (the standing weak spot).

**MultiJail — full pipeline** (`multijail_results_full_pipeline_2026-06-26.json`): English detection **68/75 = 90.7%**.

**Latency** (`latency_results_2026-06-26.json`): 100 prompts, mean **376 ms**/query, p95 393 ms. Decision mix: EXECUTE 30 · CLARIFY 41 · SAFE_STOP 24 · SAFE_FREEZE 5.

---

## 5. ⚠️ Freshness flag (the reason Wassal exists)

The stored benchmarks were run against an **earlier, smaller anchor curriculum** than what is live today:

| | Live now | In 2026-06-26 benchmark run |
|---|---|---|
| H anchors | 261 | 171 |
| I anchors | 91 | 46 |
| E anchors | 88 | 32 |
| Total | **440** | **249** |

The anchor set has grown ~77% (249 → 440) since the last full benchmark. **The 72.9% / 90.7% / 376 ms figures describe an older system.** Before quoting them as current performance, re-run HarmBench, MultiJail, and latency against the present 440-anchor curriculum. Treat section 4 as "last measured," section 2/3 as "current truth."

---

*Wassal reads live data and never caches numbers. If any figure here is quoted later, re-read the source — every commit can change it.*
