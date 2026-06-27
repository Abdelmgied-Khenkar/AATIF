# Triad → S Equation Integration Proposal

**AATIF Safety Governance Engine — Architectural Enhancement**
**Status**: Proposal — Awaiting Architect Approval
**Date**: 2026-06-26
**Author**: Analysis by Claude (Opus), commissioned by The Architect

---

## 1. The Problem

Three independent AI model reviews identified the same architectural flaw:

> The Triad (Fingerprint, Temporal Memory, Contextual Intent) tracks user behavioral history — repeat questions, harmful query patterns, trust levels, emotional trajectory — but **none of this data feeds into the S equation**. A user who has been blocked 10 times receives the exact same safety score as a first-time user sending the identical message.

The Triad currently feeds **only** into R(d) (response style) and prompt composition. The Governor explicitly gathers Triad context *after* S(d) completes, with the comment:

```
# These NEVER influence S(d). They enrich R(d) style...
```

This was a deliberate design choice — safety decisions based purely on content analysis (H, I, E scores). But it creates a blind spot: **the system has no memory when making safety decisions**.

---

## 2. Current Architecture

### 2.1 The S Equation (Gated Form)

```
S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))
    ├── quality ──┘     └── harm gate ──┘
```

Where:
- `σ(x) = 1/(1+e⁻ˣ)` — sigmoid function
- `I` = intent score (0–1), `E` = emotion score (0–1), `H` = harm score (0–1)
- `w₁ = 2.0`, `w₂ = 1.5` — quality weights
- `α = 10` — gate steepness
- `θ = 0.40` — gate center (domain-dependent)
- Hard override: `H > 0.7 → SAFE_FREEZE` (absolute, pre-gate)

**Decision thresholds**:
| Band | S Range | Action |
|------|---------|--------|
| EXECUTE | S > 0.7 | Proceed normally |
| CLARIFY | 0.5 < S ≤ 0.7 | Ask for clarification |
| SAFE_STOP | 0.3 < S ≤ 0.5 | Refuse with explanation |
| SAFE_FREEZE | S ≤ 0.3 | Hard block, log incident |

**Domain-parameterized θ**:
| Domain | θ | Rationale |
|--------|-----|-----------|
| Healthcare | 0.25 | Gate closes earlier — higher sensitivity |
| Education | 0.30 | Children involved — extra caution |
| General | 0.40 | Default calibration |
| Creative | 0.50 | More artistic latitude |

### 2.2 What the Triad Produces

**Fingerprint** (`aatif_fingerprint.py` → `FingerprintReading`):
- `trust_level`: 0.0 → 1.0 (logarithmic growth, linear decay with inactivity)
- `repeat_question_count`: how many times the user has repeated questions
- `total_interactions`: lifetime interaction count
- `confidence`: 0.0 → 0.95 (how reliable the fingerprint is, based on sample size)
- `confusion_signals` / `satisfaction_signals`: behavioral indicators
- Default for unknown users: `trust_level=0.0`, `confidence=0.0`

**Temporal Memory** (`aatif_temporal_memory.py` → `TemporalContext`):
- `recent_decisions`: last 5 S-equation decisions with timestamps — **the key data** (can count how many were SAFE_STOP / SAFE_FREEZE)
- `emotional_trajectory`: "improving" / "stable" / "declining"
- `total_interactions`: lifetime count
- Each stored `MemoryEntry` includes: `harm_score`, `intent_score`, `s_decision`

**Contextual Intent** (`aatif_contextual_intent.py` → `IntentContext`):
- `is_repeat_question`, `times_asked`, `repeat_reason`
- `user_trust_level` (forwarded from Fingerprint)
- `previous_explanations_count`
- `emotional_trajectory` (forwarded from Temporal Memory)

### 2.3 The Gap

The Governor pipeline runs: **S(d) → P(d) → R(d) → Output Gate**

Triad context is gathered at step P(d), **after** S(d) has already decided. The data exists. The pipeline order prevents it from being used.

---

## 3. Design Principles

Before proposing math, the governing principles:

1. **الاذي مالوش توقيت** — Harm has no timing. The *time of day* doesn't affect safety. But repeat harmful *behavior* is evidence of pattern, not timing. Pattern evidence MUST feed into S.

2. **The harm gate is non-compensable.** No amount of good intent (I) or positive emotion (E) can override a high harm score. This property MUST be preserved. The gate `(1 − σ(α·(H − θ)))` stays intact.

3. **Hard override is absolute.** `H > 0.7 → SAFE_FREEZE` regardless of history, trust, or any other factor. This check runs before the gate computation and is never modified.

4. **First-time users are unaffected.** A user with no history must receive the exact same S score as today. Backward compatibility is non-negotiable.

5. **No ad-hoc patches.** The integration must be algebraically clean — a continuous mathematical function, not a collection of if/else branches.

6. **Asymmetric by design.** History should make S *stricter* for repeat offenders significantly. Any *leniency* for trusted users must be marginal and carefully bounded.

---

## 4. Proposed Integration: Dynamic θ Adjustment

### 4.1 Core Idea

θ (the gate center) is already parameterized by domain: `θ(d)`. We extend it to also depend on the user's behavioral history: `θ(d, u)`.

- For repeat offenders: θ decreases → gate closes at lower H values → stricter
- For trusted users (no harm history): θ increases marginally → slight benefit of the doubt
- For new/unknown users: θ stays exactly at `θ(d)` → backward compatible

This is the cleanest integration point because:
- θ already has domain parameterization infrastructure
- The gate mechanism is preserved — I+E still cannot compensate
- It's a continuous function, not a conditional branch
- The hard override (`H > 0.7`) is untouched — it runs before the gate

### 4.2 The Math

**Step 1: Compute the Harm Recidivism Score (Ψ)**

From Temporal Memory, retrieve the last `N` interactions and count how many resulted in blocked decisions:

```
n_block = count of {SAFE_STOP, SAFE_FREEZE} in last N interactions
```

The recidivism score uses exponential saturation (rises fast, then plateaus):

```
Ψ = 1 − e^(−λ · n_block)
```

Where:
- `N = 20` — lookback window (configurable)
- `λ = 0.5` — steepness of recidivism curve

| n_block | Ψ | Interpretation |
|---------|------|---------------|
| 0 | 0.000 | Clean history |
| 1 | 0.393 | Single incident |
| 2 | 0.632 | Emerging pattern |
| 3 | 0.777 | Clear pattern |
| 5 | 0.918 | Serial offender |
| 10 | 0.993 | Near-maximum |

**Step 2: Compute the θ Adjustment (Δθ)**

```
Δθ = −δ_max · Ψ + ε_max · trust · (1 − Ψ)
      ├── harm penalty ┘   └── trust credit ──┘
```

Where:
- `δ_max = 0.10` — maximum θ reduction for repeat offenders
- `ε_max = 0.03` — maximum θ increase for trusted users (see §5 on controversy)
- `trust` = `fingerprint.trust_level` (0.0 → 1.0)

Critical property of `(1 − Ψ)` in the trust term: **trust credit vanishes as harm history grows.** A user cannot accumulate trust through benign interactions and then "spend" it on harmful ones.

**Step 3: Compute Effective θ**

```
θ_eff(d, u) = θ(d) + Δθ
```

Bounded to prevent extreme values:

```
θ_eff = clamp(θ_eff, θ_floor, θ_ceiling)
θ_floor = 0.15    (never more restrictive than this)
θ_ceiling = 0.55  (never more permissive than this)
```

**Step 4: The Modified S Equation**

```
S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ_eff(d, u))))
```

Everything else stays the same. The only change is: `θ` → `θ_eff(d, u)`.

### 4.3 Summary of New Parameters

| Parameter | Value | Role |
|-----------|-------|------|
| `N` | 20 | Lookback window for harm recidivism |
| `λ` | 0.5 | Recidivism curve steepness |
| `δ_max` | 0.10 | Maximum θ penalty (repeat offenders) |
| `ε_max` | 0.03 | Maximum θ credit (trusted users) — *controversial, see §5* |
| `θ_floor` | 0.15 | Minimum θ (absolute strictness limit) |
| `θ_ceiling` | 0.55 | Maximum θ (absolute leniency limit) |

---

## 5. The Trust Credit Question — Both Sides

The `ε_max · trust · (1 − Ψ)` term is **controversial**. Should a long-time trusted user get even a slight benefit of the doubt?

### 5.1 Argument FOR Trust Credit (ε_max = 0.03)

- **Human systems do this.** A respected doctor asking about a controlled substance gets a different reception than a stranger. The system should model real-world trust.
- **It's tiny.** At maximum (trust = 1.0, Ψ = 0), θ shifts from 0.40 to 0.43. The gate value at H = 0.35 moves from `0.622` to `0.681` — a difference of `0.059` on S. This never crosses a decision boundary alone.
- **It's self-canceling.** The moment a trusted user shows harmful patterns (Ψ > 0), the `(1 − Ψ)` term kills the credit. You can't exploit it.
- **It reduces false positives.** Long-time users who trigger borderline H scores on legitimate queries (e.g., a teacher asking about historical violence for a lesson) get slightly fewer unnecessary CLARIFY interruptions.

### 5.2 Argument AGAINST Trust Credit (ε_max = 0)

- **الاذي مالوش توقيت.** Harm has no timing AND no social status. Safety should be identity-blind.
- **Adversarial gaming.** Even with (1 − Ψ), an attacker could build trust over many sessions, use the credit on a single harmful query (where Ψ is still 0), and get through. The credit only dies after the first blocked query.
- **Principle of minimal complexity.** Every parameter is a surface for miscalibration. If the credit is "too tiny to matter," why add it at all?
- **Precedent risk.** Starting at 0.03 creates pressure to increase it. "If 0.03 is fine, why not 0.05?"

### 5.3 Recommendation

**Start with `ε_max = 0` (no trust credit).** Deploy the harm penalty first. Measure false positive rates on trusted users over time. If the data shows a real problem, introduce trust credit with evidence — not assumption.

If the Architect decides to include trust credit, the math already supports it. Set `ε_max = 0.03` and the equation works unchanged.

---

## 6. Worked Examples

All examples use: `w₁ = 2.0, w₂ = 1.5, α = 10, θ_base = 0.40` (general domain).
Quality inputs: `I = 0.70, E = 0.60` → quality = `σ(2.0 × 0.7 + 1.5 × 0.6)` = `σ(2.3)` = **0.909**

### 6.1 First-Time User (No History)

```
n_block = 0, trust = 0.0
Ψ = 1 − e^(−0.5 × 0) = 0
Δθ = −0.10 × 0 + 0.03 × 0.0 × 1.0 = 0
θ_eff = 0.40
```

| H | Gate (current) | Gate (proposed) | S (current) | S (proposed) | Decision |
|------|------|------|------|------|------|
| 0.20 | 0.881 | 0.881 | 0.800 | 0.800 | EXECUTE |
| 0.35 | 0.622 | 0.622 | 0.565 | 0.565 | CLARIFY |
| 0.50 | 0.269 | 0.269 | 0.244 | 0.244 | SAFE_FREEZE |

**Result: Identical.** Backward compatibility confirmed. ✓

### 6.2 Repeat Offender (3 Blocked Queries in Recent History)

```
n_block = 3, trust = 0.20 (low — hasn't built much trust)
Ψ = 1 − e^(−0.5 × 3) = 1 − 0.223 = 0.777
Δθ = −0.10 × 0.777 + 0.03 × 0.20 × 0.223 = −0.0777 + 0.001 = −0.076
θ_eff = 0.40 − 0.076 = 0.324
```

| H | Gate (current) | Gate (proposed) | S (current) | S (proposed) | Decision Change |
|------|------|------|------|------|------|
| 0.20 | 0.881 | 0.775 | 0.800 | 0.704 | EXECUTE → EXECUTE |
| 0.30 | 0.731 | 0.559 | 0.664 | 0.508 | CLARIFY → CLARIFY |
| 0.35 | 0.622 | 0.437 | 0.565 | 0.397 | **CLARIFY → SAFE_STOP** |
| 0.40 | 0.500 | 0.319 | 0.454 | 0.290 | SAFE_STOP → **SAFE_FREEZE** |

**Result: The system catches the repeat offender.** At H = 0.35 (a borderline query), a first-time user gets CLARIFY; the repeat offender gets SAFE_STOP. At H = 0.40, the repeat offender hits SAFE_FREEZE.

### 6.3 Trusted Long-Time User (50+ interactions, clean history)

Using `ε_max = 0.03` (if Architect approves trust credit):

```
n_block = 0, trust = 0.85
Ψ = 0
Δθ = −0.10 × 0 + 0.03 × 0.85 × 1.0 = +0.026
θ_eff = 0.40 + 0.026 = 0.426
```

| H | Gate (current) | Gate (proposed) | S (current) | S (proposed) | Decision |
|------|------|------|------|------|------|
| 0.20 | 0.881 | 0.906 | 0.800 | 0.823 | EXECUTE → EXECUTE |
| 0.35 | 0.622 | 0.680 | 0.565 | 0.618 | CLARIFY → CLARIFY |
| 0.50 | 0.269 | 0.324 | 0.244 | 0.295 | SAFE_FREEZE → SAFE_FREEZE |

**Result: Marginal difference.** The trust credit nudges S up by ~0.02–0.05 within the same band. It never crosses a decision boundary on its own. The trusted user still gets SAFE_FREEZE at H = 0.50.

### 6.4 The Adversarial Edge Case: Trust Then Attack

A user builds trust over 50 clean interactions (trust = 0.85), then sends a genuinely harmful query (H = 0.65):

```
n_block = 0 (first harmful query), trust = 0.85
Ψ = 0
θ_eff = 0.426 (with trust credit) or 0.40 (without)
```

With trust credit:
```
gate = 1 − σ(10 × (0.65 − 0.426)) = 1 − σ(2.24) = 1 − 0.904 = 0.096
S = 0.909 × 0.096 = 0.087 → SAFE_FREEZE
```

Without trust credit:
```
gate = 1 − σ(10 × (0.65 − 0.40)) = 1 − σ(2.5) = 1 − 0.924 = 0.076
S = 0.909 × 0.076 = 0.069 → SAFE_FREEZE
```

**Result: SAFE_FREEZE either way.** At H = 0.65, the gate crushes S regardless of trust. The trust credit's 0.026 shift on θ is meaningless against a high H score. And at H > 0.7, the hard override triggers before the gate is even computed.

### 6.5 Serial Offender — Maximum Penalty

A user with 10 blocked queries in the last 20 interactions:

```
n_block = 10, trust = 0.05 (eroded by inactivity/decay)
Ψ = 1 − e^(−0.5 × 10) = 0.993
Δθ = −0.10 × 0.993 + 0.03 × 0.05 × 0.007 ≈ −0.099
θ_eff = 0.40 − 0.099 = 0.301
```

This is nearly identical to the **education domain** (θ = 0.30). A serial offender in "general" mode gets treated with the same caution as a first-time user in a children's educational context.

| H | Gate (current) | Gate (proposed) | S (current) | S (proposed) | Decision Change |
|------|------|------|------|------|------|
| 0.25 | 0.818 | 0.626 | 0.743 | 0.569 | EXECUTE → CLARIFY |
| 0.30 | 0.731 | 0.502 | 0.664 | 0.456 | CLARIFY → SAFE_STOP |
| 0.35 | 0.622 | 0.381 | 0.565 | 0.346 | CLARIFY → SAFE_STOP |

**Result: Dramatically tighter.** Queries that would normally pass through CLARIFY now hit SAFE_STOP.

---

## 7. Edge Cases and Risks

### 7.1 Cold Start — No History Available

**Scenario**: Temporal Memory database is empty or unavailable.
**Behavior**: `n_block = 0`, `trust = 0.0` → `Ψ = 0`, `Δθ = 0`, `θ_eff = θ(d)`
**Risk**: None. Falls back exactly to current behavior.

### 7.2 Legitimate Researcher Triggering Repeated Blocks

**Scenario**: A medical researcher repeatedly queries about drug interactions, triggering borderline H scores and accumulating SAFE_STOP decisions.
**Risk**: θ tightens progressively, making legitimate work harder.
**Mitigation**: This is actually **correct behavior** — the system SHOULD be more cautious with repeated sensitive queries. The researcher should be using a `healthcare` profile (θ = 0.25) with appropriate domain context anyway. If the system consistently blocks legitimate queries, the problem is in the H score calibration, not in the Triad integration.

### 7.3 Shared User ID

**Scenario**: Multiple people sharing a single user_id. One person's harmful queries taint the other's experience.
**Risk**: Innocent user gets tighter θ due to someone else's behavior.
**Mitigation**: This is a pre-existing Fingerprint limitation, not introduced by this proposal. The Fingerprint system already assumes one user per ID. Long-term fix: per-session behavioral signatures.

### 7.4 Trust Decay After Long Absence

**Scenario**: User was trusted (trust = 0.85), disappears for 6 months, returns.
**Behavior**: Fingerprint applies `TRUST_DECAY_PER_DAY = 0.01`, so after 85 days, trust ≈ 0. After 6 months, trust is at floor.
**Risk**: None. The decay mechanism handles this naturally. A returning user essentially starts fresh.

### 7.5 Temporal Memory Lookback Window Edge

**Scenario**: User had 5 blocks 6 months ago, but has been clean for the last 20 interactions.
**Behavior**: With `N = 20` lookback, only the last 20 interactions are counted. If all 20 are clean, `n_block = 0`, `Ψ = 0`.
**Risk**: Rehabilitated users DO get their slate cleaned. This is intentional — permanent punishment serves no useful purpose.
**Alternative**: If the Architect wants permanent scarring, use total lifetime blocks instead of windowed. Not recommended.

### 7.6 Gate Interaction with Domain θ

**Scenario**: Healthcare domain (θ = 0.25) + serial offender (Δθ = −0.10) → θ_eff = 0.15.
**Behavior**: θ_eff hits the `θ_floor = 0.15`. The gate is now extremely aggressive — even H = 0.20 would significantly suppress S.
**Risk**: Over-blocking in already-strict domains.
**Mitigation**: The `θ_floor = 0.15` prevents runaway tightening. This value should be tuned — 0.15 might be too aggressive. Consider `θ_floor = 0.20` for safety.

---

## 8. Implementation Plan

### 8.1 Files to Modify

| File | Changes | Est. Lines |
|------|---------|-----------|
| `engine/aatif_s_equation.py` | Add `theta_adjustment` parameter to `compute_s_gated_from_scores()`. Apply adjustment after θ resolution. Add clamping. | ~15 lines |
| `engine/aatif_governor.py` | (1) Move Triad context gathering BEFORE S(d). (2) Add `_compute_theta_adjustment()` method. (3) Pass adjustment to S engine. | ~50 lines |
| `engine/aatif_temporal_memory.py` | Add `count_blocked_decisions(user_id, lookback=20)` helper method. | ~15 lines |

**Total estimated change: ~80 lines of new/modified code.**

No changes needed to:
- `aatif_fingerprint.py` — already produces `trust_level` with correct defaults
- `aatif_contextual_intent.py` — not directly involved in θ calculation
- `aatif_r_equation.py` — R equation is unaffected

### 8.2 Detailed Change Descriptions

**`aatif_s_equation.py`**

In `compute_s_gated_from_scores(H, I, E, profile, domain)`:
- Add parameter: `theta_adjustment: float = 0.0`
- After line where θ is resolved from domain/profile, add:
  ```python
  theta_eff = theta + theta_adjustment
  theta_eff = max(THETA_FLOOR, min(THETA_CEILING, theta_eff))
  ```
- Use `theta_eff` in gate computation instead of `theta`
- Add constants: `THETA_FLOOR = 0.15`, `THETA_CEILING = 0.55`

In `AATIFEngine.compute()`:
- Add parameter: `theta_adjustment: float = 0.0`
- Pass through to `compute_s_gated_from_scores()`

**`aatif_governor.py`**

New method `_compute_theta_adjustment(self, user_id)`:
```python
def _compute_theta_adjustment(self, user_id):
    """Compute θ adjustment from Triad behavioral history."""
    LAMBDA = 0.5
    DELTA_MAX = 0.10
    EPSILON_MAX = 0.0  # Start with 0; set to 0.03 if trust credit approved
    LOOKBACK = 20

    # Get harm recidivism count
    n_block = self.temporal_memory.count_blocked_decisions(user_id, lookback=LOOKBACK)

    # Get trust level
    fingerprint = self.fingerprint_engine.get_reading(user_id)
    trust = fingerprint.trust_level if fingerprint else 0.0

    # Compute recidivism score (exponential saturation)
    import math
    psi = 1.0 - math.exp(-LAMBDA * n_block)

    # Compute adjustment
    delta_theta = -DELTA_MAX * psi + EPSILON_MAX * trust * (1.0 - psi)

    return delta_theta
```

In `process()` method:
- Compute `theta_adj = self._compute_theta_adjustment(user_id)` **BEFORE** calling S(d)
- Pass `theta_adjustment=theta_adj` to the S engine

**`aatif_temporal_memory.py`**

New method:
```python
def count_blocked_decisions(self, user_id, lookback=20):
    """Count SAFE_STOP and SAFE_FREEZE decisions in last N interactions."""
    entries = self.recall(user_id, limit=lookback)
    blocked = {"SAFE_STOP", "SAFE_FREEZE"}
    return sum(1 for e in entries if e.s_decision in blocked)
```

### 8.3 Testing Strategy

1. **Unit test: backward compatibility** — Verify that with `theta_adjustment=0.0`, all existing test cases produce identical S scores.

2. **Unit test: repeat offender** — Feed `n_block=3` with borderline H, verify S decreases and decision band shifts.

3. **Unit test: clamping** — Verify `θ_eff` never goes below `θ_floor` or above `θ_ceiling`.

4. **Integration test: Governor pipeline** — Simulate a 5-message conversation where messages 3–5 are harmful. Verify θ tightens progressively across the sequence.

5. **Regression test: hard override** — Confirm `H > 0.7 → SAFE_FREEZE` regardless of any θ adjustment, trust level, or history.

---

## 9. Migration and Rollback

**Deployment**: Feature-flagged.
```python
TRIAD_S_INTEGRATION_ENABLED = False  # Flip to True after testing
```

When disabled, `theta_adjustment` defaults to `0.0` — zero behavioral impact. The system behaves exactly as before.

**Rollback**: Set flag to `False`. No data migration needed. Temporal Memory continues recording decisions regardless of the flag — it just doesn't feed into S.

---

## 10. Open Questions for The Architect

1. **Trust credit**: Start with `ε_max = 0` (recommended) or `ε_max = 0.03`? See §5 for full argument.

2. **θ_floor value**: `0.15` (proposed) or `0.20` (safer)? The floor prevents over-tightening in already-strict domains like healthcare.

3. **Lookback window**: `N = 20` (proposed). Should this be time-based instead (e.g., last 7 days) or interaction-based?

4. **Should SAFE_STOP and SAFE_FREEZE count differently in n_block?** Currently they're weighted equally. Option: count SAFE_FREEZE as 2× to penalize severe violations more.

5. **Fingerprint trust decay on harm**: Currently trust only decays with inactivity. Should a SAFE_STOP/SAFE_FREEZE also erode trust? This would be a Fingerprint change, not an S equation change — a separate proposal.

6. **Naming**: The θ adjustment mechanism needs a name for the codebase. Candidates:
   - `behavioral_theta` / `θ_سلوكي`
   - `history_gate` / `بوابة_التاريخ`
   - `recidivism_adjustment` / `تعديل_العود`

---

## 11. Architectural Significance

This change transforms the S equation from a **stateless content evaluator** to a **stateful behavioral safety system** — while preserving every existing safety property:

| Property | Before | After |
|----------|--------|-------|
| Content-based harm detection | ✓ | ✓ (unchanged) |
| Non-compensable harm gate | ✓ | ✓ (unchanged) |
| Hard override at H > 0.7 | ✓ | ✓ (unchanged) |
| Domain sensitivity | ✓ | ✓ (unchanged) |
| Repeat offender detection | ✗ | **✓** |
| Behavioral memory in safety | ✗ | **✓** |
| First-time user parity | ✓ | ✓ (proven by math) |

The integration point — θ adjustment — is elegant because θ was already the system's "sensitivity dial." Domain parameterization adjusts it by *context*. This proposal adds adjustment by *history*. Same mechanism, new dimension.

In the language of the Intelligence-Spacetime Curvature Hypothesis: the Triad integration adds **temporal mass** to the curvature field. The governance layer now bends the trajectory not just based on what was said, but on what this speaker has said before. The field has memory.

---

**End of Proposal. Awaiting Architect approval before any code changes.**
