# FN#050 — Dual-Root Reconstruction Engine (DRE) — External Review Brief

## What to Review

The AATIF Dual-Root Reconstruction Engine (DRE) — a B-prime (post-S) module that detects when harmful behavior has TWO intertwined roots: psychological distress (Root A) and ethical drift (Root B). It enriches safety responses to address both roots, rather than treating harm as monolithic.

**Module**: `engine/aatif_dual_root.py` (904 lines)
**Tests**: `tests/test_dual_root.py` (1135 lines, 148 tests across 16 classes)
**Design consensus**: Claude × ChatGPT, 2026-06-30

---

## Architecture

**Position**: B-prime post-S (same tier as PSP, Uncertainty, ResponseShaper)
- GovernanceEquation (S) makes the safety decision FIRST
- DRE enriches HOW that decision is communicated
- DRE NEVER touches S, H, θ, I, E, or any safety parameters

**Single Mind Law**: Only GovernanceEquation makes safety decisions. DRE is response enrichment, not safety.

**7 Invariants enforced**:
1. S-decision immutability — never modify S_decision, H, I, E, θ, α
2. No downgrade — BLOCK→CLARIFY, CLARIFY→EXECUTE prohibited
3. Boundary preservation — acknowledgment + refusal + alternative
4. No causal certainty — no "because of your trauma..."
5. Meta-Oversight audit — response_contains_refusal, no clinical labels
6. False Goodness guard — if FN#049 fires, DRE must not activate
7. Malicious intent exclusion — deliberate malice → no empathic reconstruction

---

## Key Design Decisions (from ChatGPT Consensus)

1. **Scope**: Signal analysis, not truth analysis. "DRE performs bounded dual-root signal reconstruction for safer response shaping after the governance equation has already made its decision."

2. **POM revised**: stated_event → stated_meaning → distress_signal → harmful_impulse (removed "wound" — too clinical)

3. **Three-stage activation gate**:
   - Stage 1: Safety relevance (S decision in {CLARIFY, BLOCK_SOFT, EXECUTE_WITH_CAUTION}, H in [0.20, 0.55], not factual query)
   - Stage 2: Distress authenticity (≥1 strong OR ≥2 weak distress markers)
   - Stage 3: Harmful moral drift (ethical drift markers with harm targets)

4. **Cross-causal detection**: Evidence-bounded with 5 literal values: explicit_a_feeds_b, explicit_b_feeds_a, co_present_direction_unclear, independent, none

5. **Clinical boundary**: "No Diagnosis, No Treatment, No Root-Certainty"

6. **Graceful degradation**: Three enrichment modes:
   - `dual_root`: Both roots detected → full dual-root response
   - `distress_boundary`: Only Root A → compassionate acknowledgment
   - `ethical_boundary`: Only Root B → direct ethical naming

---

## Root A — Psychological/Distress Signals (7 types)

| Type | Example AR | Example EN |
|------|-----------|-----------|
| pain | متوجع, وجعني | hurts, suffering |
| fear | خايف, أخاف | scared, terrified |
| humiliation_pain | مقهور, منكسر, كرامتي | humiliated, degraded |
| injustice_pain | مظلوم, ظلموني | wronged, unjust |
| avoidance_loop | ما اقدر اواجه | can't face, avoiding |
| flooding | بنفجر, مخنوق | overwhelmed, spiraling |
| emotional_threshold | الصبر نفد, طفح الكيل | at my limit, breaking point |

**Strong markers** (1 is enough): مقهور, منكسر, الصبر نفد, ابغى اموت, i can't take it anymore, i feel broken
**Weak markers** (need ≥2): تعبان, زعلان, حزين, خايف, tired, sad, hurt

---

## Root B — Ethical Drift Signals (7 types)

| Type | Example AR | Example EN |
|------|-----------|-----------|
| justification | يستاهل | he deserves it |
| normalization | عادي, مو غلط | it's normal, everyone does |
| moral_inversion | الطيبة ما تنفع | kindness is weakness |
| retaliatory_justice | اخذ حقي, اربيه | teach him a lesson, get revenge |
| dehumanizing_wish | الله ينتقم منه | i hope he suffers, rot in hell |
| reputation_harm | افضحه, اخرب سمعته | expose him, ruin his reputation |
| reciprocal_harm | عين بعين, الرد بالمثل | eye for an eye |

---

## 8 Arabic-Specific Categories

These categories map Arabic cultural/dialectal expressions to dual-root patterns — the unique contribution that general English safety systems miss:

| Cat | Arabic Name | What It Captures |
|-----|------------|-----------------|
| A | قهر/كسر/وجع | Dignity-pain (oppression-wound) |
| B | حقي/أربيه | Retaliatory justice ("I'll discipline him") |
| C | كرامة/إهانة | Honor-pain ↔ honor-retaliation (dual-coded) |
| D | طفح الكيل | Emotional threshold exceeded |
| E | الدعاء/اللعن | Religious curse / moral displacement |
| F | الطيبة ضعف | Moral inversion ("kindness is weakness") |
| G | فضيحة/سمعة | Reputation harm / social punishment |
| H | عين بعين | Reciprocal harm justification |

Category C is **dual-coded**: "كرامتي" (my dignity) functions as Root A (dignity-pain) in distress context, but "رد كرامتي" (restore my dignity) functions as Root B (honor-retaliation) in action context.

---

## Feature Flags

```python
DRE_ENABLED = False          # master switch OFF by default
DRE_MONITOR_ONLY = True      # log only, no response enrichment
```

Ships dormant. Activation requires explicit configuration.

---

## Test Coverage (148 tests, 16 classes)

- Root A signal detection (strong/weak markers, Arabic/English)
- Root B signal detection (all 7 ethical-drift types)
- 8 Arabic-specific categories
- Three-stage activation gate
- Graceful degradation modes
- Cross-causal detection (A→B, B→A, co-present, independent)
- POM trace construction
- Response guidance generation
- Single Mind invariant enforcement
- False Goodness guard
- Malicious intent exclusion
- Clinical boundary
- Edge cases
- Feature flags

All 148 tests passing.

---

## Questions for Reviewers

1. **Activation gate**: Is the three-stage gate (safety relevance → distress authenticity → harmful moral drift) sufficient to prevent false activation?

2. **Arabic categories**: Do the 8 categories cover the major dual-root patterns in Arabic? Are any important patterns missing?

3. **Clinical boundary**: Is the "No Diagnosis, No Treatment, No Root-Certainty" policy strictly enough enforced?

4. **Cross-causal detection**: Is evidence-bounded cross-causal detection (explicit markers only) the right level of caution?

5. **Single Mind Law**: Are the 7 invariants sufficient to guarantee DRE never interferes with safety decisions?

6. **Academic readiness**: Is this module ready for inclusion in an academic paper (EACL 2027)?

7. **Any P0 bugs or design flaws?**

---

## Context: AATIF System

AATIF is a mathematical governance framework for LLM safety. Core S equation:
`S = σ(w₁·I + w₂·E) · [1 − σ(α(H_eff − θ))]`

- H = harm score (embedding similarity), I = intent score, E = emotion score
- θ = 0.40 (domain-adjustable threshold)
- Arabic-first design — meaning density (كثافة المعنى) as the design variable
- Zero fine-tuning — governance via anchors + cosine similarity
- Built by independent researcher Abdulmjeed Ibrahim Khenkar via AI collaboration

**Existing modules**: GovernanceEquation (S), Five-Layer Intent, Hysteresis, False Goodness Detector, Uncertainty Detector, PSP Detector, DRE (this module)

---

*Review requested 2026-06-30. Please provide critical technical feedback — we value honest assessment over politeness.*
