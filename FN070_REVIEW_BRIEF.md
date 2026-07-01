# FN#070 — Possibility Space Preservation (PSP): External Review Brief

## Date: 2026-06-30
## Reviewer Task: Review this module for bugs, design weaknesses, and paper-readiness

---

## Context

AATIF is a mathematical governance framework for LLM safety. The core equation is:
```
S = σ(w₁·I + w₂·E) · [1 − σ(α(H_eff − θ))]
```
where H=harm, I=intent, E=emotion, θ=threshold (domain-specific via D parameter).

FN#070 adds **Possibility Space Preservation** — ensuring the AI preserves a human's decision space rather than collapsing to a single recommendation.

## Architecture: B-prime (Post-Safety, Observational)

PSP is **stylistic, NOT safety**. It sits AFTER the S equation (B-prime position):
- PSPDetector → observational (outputs PSPReading + evidence)
- ResponseShaper → stylistic (applies domain psp_profile via G_eff)  
- OutputGate Layer 7 → corrective (monitors for premature closure)

**Single Mind Law**: Only GovernanceEquation makes safety decisions. PSP never touches S, H, θ, or the GovernanceEquation.

## What Was Built (commit 2cdadca)

### 1. PSP State Lifecycle Enum
```python
class PSPState(enum.Enum):
    DORMANT = "dormant"              # no active decision context
    DETECTED = "detected"            # decision point detected, paths not stabilized
    EXPLORING = "exploring"          # multiple live paths open
    NARROWING = "narrowing"          # user rejecting/preferring/ranking
    CLOSURE_REQUESTED = "closure_requested"  # user explicitly asked to choose
    CLOSED = "closed"                # decision closed, expired, or topic-shifted
```

### 2. PSPContext v1 Fields (pure storage, no logic)
```python
@dataclass
class PSPContext:
    live_paths: List[LivePath]
    rejected_paths: List[str]
    prior_decision_active: bool = False
    # FN#070 v1 state lifecycle:
    state: PSPState = PSPState.DORMANT
    decision_topic: Optional[str] = None
    user_requested_closure: bool = False
    last_psp_turn_index: int = -1
    last_decision_marker_turn_index: int = -1
    domain_profile: str = "medium"
    last_transition_reason: Optional[str] = None
```

### 3. State Transition Helper: `next_psp_state()`
Transitions driven by PSP reading + user turn features + topic shift signal:
- DORMANT → DETECTED (new decision point)
- DETECTED → EXPLORING (still active, paths stabilizing)
- EXPLORING → NARROWING (user constraining/rejecting paths)
- Any → CLOSURE_REQUESTED (explicit closure markers)
- CLOSURE_REQUESTED/NARROWING → CLOSED (user decided)
- Any → DORMANT (topic shift or inactivity decay)
- One quiet turn HOLDS state; consecutive quiet turns trigger deactivation

### 4. Objective Comparison Suppressors (Two-Axis Scoring)
Not every "which is better" is a decision. Factual spec comparisons suppress PSP:
- Objective markers + weak decision signal → `is_decision_point=False`
- Objective markers + strong decision signal → confidence × 0.7
- **Personal-choice markers override** suppressors entirely ("which is cheaper FOR MY FAMILY")

### 5. Arabic Dialect Decision Markers
Expanded set covering Gulf, Egyptian, Levantine dialects:
- Decision: "ايش تشوف", "احترت", "ايهم افضل", "اكمل ولا اوقف", "مدري اسوي كذا ولا كذا"
- Closure: "قررلي", "خلاص اختار لي", "أتوكل؟"
- Narrowing: "افضل", "ما ابغى", "استبعد"
- Decided: "قررت", "اخترت", "خلاص قررت"

### 6. Gate Mode Rename: "block" → "reopen"
PSP doesn't block responses — it reopens prematurely collapsed possibility space. "block" kept as backward-compatible deprecated alias.

### 7. Hybrid Deactivation Policy
- General domains: 3 consecutive quiet turns → deactivate
- High-stakes domains (healthcare, legal, finance): 5 consecutive quiet turns
- Topic shift → immediate deactivation regardless

### 8. Feature Flags (all OFF by default)
```python
PSP_ENABLED = False              # master switch
PSP_GATE_CHECK_ENABLED = False   # OutputGate Layer 7 PSP check
PSP_GATE_MODE = "monitor"        # "monitor" or "reopen"
```

## Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| State enum, not state machine | Lightweight v1; formal guards are v1.5 |
| No embedder required | Module testable offline (CI without Ollama) |
| Sparse activation (90% skip) | Most turns aren't decisions; save compute |
| Domain config lookup, not detection | psp_profile from config, like θ from D parameter |
| Bounded alternatives (2-5) | Schwartz paradox: more choices ≠ better |
| Feature flags OFF | Staged rollout: build → monitor → enable |

## Test Coverage (111 PSP tests, full suite 2636 passed)

9 new test classes:
1. `TestPSPState` — enum values and membership
2. `TestStateTransitions` — all state edges including edge cases
3. `TestDeactivation` — general vs high-stakes turn counts
4. `TestObjectiveSuppression` — factual comparison suppression
5. `TestPersonalDecisionDetection` — personal override of suppression
6. `TestArabicDialectMarkers` — all expanded markers fire correctly
7. `TestPromptedClosureBypass` — explicit closure is allowed, not a violation
8. `TestFeatureFlagBehaviour` — flags OFF = no PSP processing
9. `TestReopenMode` — gate mode rename backward compatibility

## Files Changed

| File | Lines | Description |
|---|---|---|
| `engine/aatif_psp_detector.py` | 929 (+273/-13) | Core PSP detector with all new features |
| `engine/aatif_output_gate.py` | +14/-6 | Gate mode rename |
| `tests/test_psp_detector.py` | +276 | 9 new test classes |
| `tests/test_psp_output_gate.py` | +27 | Reopen mode test |

## Known Limitations (acknowledged)

1. ~15+ hardcoded constants without ablation (thresholds, weights, turn counts)
2. Tier 2 (embeddings) untested in integration (requires Ollama + bge-m3)
3. State transitions are a helper function, not a guarded machine (v1.5 work)
4. No cross-validation of deactivation turn counts (3 and 5 are educated guesses)
5. Objective suppressor markers are keyword-based, not semantic
6. Feature flags all OFF undermines testability in production
7. `next_psp_state()` doesn't persist — caller must store result

## Questions for Reviewers

1. **State lifecycle**: Are the 6 states sufficient? Any missing transitions?
2. **Objective suppressors**: Is two-axis scoring (objective × decision) the right approach? Any edge cases where factual comparisons should still be PSP events?
3. **Deactivation policy**: 3 turns general / 5 turns high-stakes — reasonable defaults? Should this be configurable per domain?
4. **Arabic markers**: Any common dialectal expressions missing from the decision/closure/narrowing marker sets?
5. **Architecture boundary**: Does PSP properly stay out of safety (S equation) territory? Any leakage?
6. **Bounded alternatives**: 2-5 range — should the ceiling be higher for creative domains?
7. **Single quiet turn holds state**: Is this correct, or should one quiet turn start the decay countdown?

## Consensus Document

This implementation follows the Claude × ChatGPT design consensus (FN070_DESIGN_CONSENSUS.md, 2026-06-30). ChatGPT discussion: https://chatgpt.com/c/6a446e88-5e40-83ea-b65d-061679c26ce2
