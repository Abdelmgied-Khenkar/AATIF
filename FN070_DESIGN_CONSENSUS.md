# FN#070 Possibility Space Preservation — Design Consensus
## Claude + ChatGPT Collaborative Design (2026-06-30)

---

## Architecture: B-prime (B') — Option B+D

Four components with clean separation of concerns:

```
Storage:
  conversation decision context
  prior rejected paths
  prior active options

Observational:
  PSPDetector
  - sparse activation (fast-path skip)
  - outputs PSPReading only
  - per-sub-intent readings
  - mutable live paths

Stylistic:
  ResponseShaper
  - applies domain psp_profile
  - uses clarify_width through G_eff/R
  - preserves bounded alternatives

Post-generation:
  OutputGate Layer 7
  - monitoring by default
  - blocking/regeneration only by explicit flag + domain policy
  - corrective/regenerative, NOT safety-judicial
```

### Critical Design Rules

> **Single Mind**: Only GovernanceEquation makes safety decisions. PSP is stylistic, NOT safety.

> **B5 not B6**: FN#070 signals through Behaviour binding channel, NOT Safety binding channel.

> **H_eff not θ**: θ is fixed per domain. Never changes dynamically. FN#070 doesn't touch H, θ, or S.

---

## Key Design Decisions

### 1. FN#070 is Stylistic, NOT Safety
- FN#070 governs HOW responses are presented, not WHETHER they're allowed
- Binding through B5 (Behaviour), NOT B6 (Safety)
- PSPDetector is observational → ResponseShaper is stylistic → OutputGate is corrective
- No component in this pipeline touches S, H, θ, or GovernanceEquation

### 2. Detection: Hybrid with Sparse Activation (Q1)
- Three-tier detection: deterministic signals first, embeddings second, context third
- Fast-path skip: if `deterministic_not_decision_confidence >= 0.95`, skip embedding step
- Aligns with AATIF's Sparse Activation principle: most turns should be cheap
- Embeddings only run when deterministic/context signals are ambiguous

### 3. Bounded Set: System Proposes, Human Closes (Q2)
- System proposes bounded alternatives; human decides when/how to close
- Default path counts: simple=2, default=3, high-stakes=3-4, creative=5
- Hard max: 5 paths without explicit user request
- Bounded set is **observationally mutable**, not system-prescriptive
- If human introduces a new path not in the set, PSPDetector updates its reading

### 4. Multi-Intent: FN#036 First, PSP Per Sub-Intent (Q3)
- FN#036 Multi-Intent Resolution runs first to resolve intents
- PSP applies independently per resolved intent
- A response can contain: direct factual answer for intent A, bounded alternatives for decision intent B
- PSP activation is per-sub-intent, not all-or-nothing

### 5. Violation = Unprompted Premature Single-Path Closure (Q4)
- Prompted closure is allowed (user explicitly asks for recommendation)
- Violation = unprompted premature single-path closure when alternatives exist
- System should present alternatives BEFORE recommending, unless user signals urgency

### 6. Pipeline Position: Both Pre-LLM and Post-LLM (Q5)
- Pre-LLM: PSPDetector → ResponseShaper shapes prompt instructions to LLM
- Post-LLM: OutputGate Layer 7 checks generated text for premature closure
- OutputGate defaults to MONITORING mode (log violations, don't block)
- BLOCKING mode only when `PSP_GATE_CHECK_ENABLED=True` AND domain policy demands it
- Feature flags: `PSP_ENABLED` (default False), `PSP_GATE_CHECK_ENABLED` (default False), `PSP_GATE_MODE` (default "monitor")

### 7. CLARIFY Mode: Not Auto-PSP (Q6)
- CLARIFY mode is NOT automatic PSP activation
- Introduces `clarify_width` parameter (1=normal, 2-3=PSP-aware, >3=category choice)
- clarify_width modifies G before R is computed: `G_eff = G + κ * clarify_width_pressure`
- `R = σ(w₃·T + w₄·V + w₅·G_eff + w₆·D + bias)`
- This preserves R as the style equation while letting PSP influence guidance density

### 8. Domain-Specific PSP Profile (Q7)
- Domain-specific `psp_profile` (NOT θ-analogous):

```yaml
psp_profile_by_domain:
  healthcare: high
  legal/finance: high
  education: high
  general: medium
  creative: adaptive
```

- `psp_profile` comes from domain config (like θ comes from D parameter)
- PSPDetector reads `psp_profile`, doesn't compute it
- PSPDetector may compute `closure_risk`, but not decide `psp_mode`
- Must NOT feed H, θ, S, or domain protocol decisions

### 9. Schwartz Paradox: Max 5 Paths (Q8)
- Max presented paths: 5
- Recommended bounds: default=3, simple=2, high-stakes=3-4, creative brainstorming=5
- Hard max without user request: 5
- Trimming is NOT premature closure IF:
  - excluded options are named or summarized
  - the trim criterion is transparent
  - the human can reopen the space
- Example: "There are more possibilities, but the realistic set here is three: A, B, and C."
- Tradeoff completeness gated by closure_risk:

```python
if closure_risk > 0.5:
    require tradeoffs  # each path needs benefit + limitation
else:
    alternatives may be lightweight  # simple listing is fine
```

### 10. Arabic-Specific Patterns (Q9)
- Language/culture-sensitive phrasing, not separate logic
- Arabic PSP should recognize: "استخير", "استشير", "تنصحني", "ايش الأفضل", "محتار", "أتوكل؟", "أختار مين/ايش؟"
- For Istikharah/Mashwarah: avoid sounding like the final authority
- Good pattern: "خلينا نحصر الخيارات الواقعية، ونوضح مزايا وعيوب كل واحد، والقرار النهائي لك"
- Fits FN#006 strongly

---

## PSPReading Dataclass

```python
@dataclass
class PSPReading:
    is_decision_point: bool
    decision_confidence: float       # how confident the detection is
    closure_risk: float              # 0.0 = open, 1.0 = fully collapsed
    live_paths: list[LivePath]       # currently viable alternatives
    bounded_count: int               # number of bounded alternatives
    user_requested_closure: bool     # did user explicitly ask to close?
    evidence: list[str]              # why this reading was produced

@dataclass
class LivePath:
    label: str
    summary: str
    tradeoff: Optional[str]          # benefit/limitation (required when closure_risk > 0.5)
```

Note: `psp_mode` is NOT in PSPReading. It comes from `domain_config.psp_profile` (config lookup, not detector computation).

---

## Pipeline Integration

```
ConversationManager → FN#036 Multi-Intent Resolution
  ↓
PSPDetector (per resolved sub-intent)
  - sparse activation (fast-path skip when deterministic confidence >= 0.95)
  - observational only — outputs PSPReading
  - mutable live paths (updates when human introduces new paths)
  ↓
ResponseShaper
  - reads domain_config.psp_profile
  - applies clarify_width through G_eff: G_eff = G + κ * clarify_width_pressure
  - computes R = σ(w₃·T + w₄·V + w₅·G_eff + w₆·D + bias)
  - shapes prompt to preserve bounded alternatives
  ↓
LLM
  ↓
OutputGate Layer 7 (PSP check)
  - default: monitoring mode (log closure violations)
  - optional: blocking mode (regenerate on premature closure)
  - corrective/regenerative, NOT safety-judicial
```

---

## Feature Flags

```python
PSP_ENABLED = False                    # master switch for PSPDetector
PSP_GATE_CHECK_ENABLED = False         # OutputGate PSP check
PSP_GATE_MODE = "monitor"             # "monitor" (log only) or "block" (regenerate)
```

---

## Evaluation Strategy

### Metrics & Targets

```yaml
decision_detection_F1: >0.90
closure_rate_unprompted: <10%
exploration_rate: >85%
false_positive_factual: <5%
bounded_set_compliance: 100%
max_paths_without_request: <=5
tradeoff_completeness: >85%           # when closure_risk > 0.5
over_expansion_rate: <10%
recommendation_after_alternatives: measured    # recommendations happen after exploration
user_closure_detection_accuracy: measured       # detecting explicit closure requests
```

### Test Strategy
Build a decision-point dataset:
1. Collect real decision-oriented queries (medical, career, purchase, creative)
2. Include clear non-decision queries as negatives (factual lookups, greetings)
3. Include multi-intent queries with mixed decision/non-decision parts
4. Test Arabic-specific patterns (Istikharah/Mashwarah phrases)
5. Test closure detection (prompted vs unprompted)

---

## Code Interface

```python
class PSPDetector:
    def detect(self, turn_features, prior_context, domain_config) -> PSPReading:
        # Fast-path skip
        if self._deterministic_confidence(turn_features) >= 0.95:
            return PSPReading(is_decision_point=False, ...)

        # Full detection: deterministic → embedding → context
        ...
        return PSPReading(
            is_decision_point=...,
            decision_confidence=...,
            closure_risk=...,
            live_paths=...,
            bounded_count=...,
            user_requested_closure=...,
            evidence=...
        )

class ResponseShaper:
    def shape(self, ..., psp_reading: PSPReading, domain_config):
        psp_profile = domain_config.psp_profile  # config lookup
        if psp_reading.is_decision_point:
            G_eff = G + kappa * self._clarify_width_pressure(psp_reading)
            # Use G_eff in R computation
            R = sigmoid(w3*T + w4*V + w5*G_eff + w6*D + bias)
            # Shape prompt to include bounded alternatives
            ...

class OutputGate:
    def check_psp(self, response_text, psp_reading, config):
        if not config.PSP_GATE_CHECK_ENABLED:
            return response_text  # pass through

        if config.PSP_GATE_MODE == "monitor":
            self._log_closure_violations(response_text, psp_reading)
            return response_text  # still pass through

        if config.PSP_GATE_MODE == "block":
            if self._detects_premature_closure(response_text, psp_reading):
                return self._regenerate_with_alternatives(response_text, psp_reading)
            return response_text
```

---

## Files to Create/Modify

### New Files
1. `psp_detector.py` — PSPDetector module (observational, outputs PSPReading)
2. `psp_reading.py` — PSPReading and LivePath dataclasses
3. `test_psp_detector.py` — Unit tests for detection accuracy
4. `test_psp_integration.py` — Integration tests with full pipeline

### Modified Files
1. `response_shaper.py` — Add PSPReading consumption, G_eff computation, bounded alternative formatting
2. `output_gate.py` — Add Layer 7 PSP closure check (monitoring mode by default)
3. `domain_config.py` — Add `psp_profile` per domain
4. `governance_config.py` — Add PSP feature flags (`PSP_ENABLED`, `PSP_GATE_CHECK_ENABLED`, `PSP_GATE_MODE`)
5. `conversation_manager.py` — Add PSP state storage (prior paths, rejected options)

---

## Open Questions for Implementation

1. What is κ (kappa)? How does `clarify_width_pressure` scale into G_eff? Needs calibration.
2. What deterministic signals constitute the "fast-path skip"? Need to define the keyword/pattern list for decision-point detection.
3. How does PSPDetector handle domain-crossing within a single conversation? (e.g., starts medical, shifts to career)
4. What is the regeneration strategy when OutputGate catches premature closure in blocking mode? Full regenerate or patch?
5. Arabic dialect handling: Do Gulf/Egyptian/Levantine dialects have different decision-point markers?

---

## Source

This design emerged from a real-time collaborative discussion between Claude (Anthropic) and ChatGPT (OpenAI) on 2026-06-30, as requested by the Architect. Neither model had absolute truth — the design converged through challenge, counterproposal, and consensus.

**Round 1**: ChatGPT received the full 778-line design brief and provided detailed answers to all 10 design questions, proposing the B-prime architecture (Storage → Observational → Stylistic → Post-generation) with PSPDetector + OutputGate Layer 7.

**Round 2**: Claude reviewed all answers and proposed 7 refinements:
1. Fast-path skip for Sparse Activation
2. Bounded set as observationally mutable
3. PSP activation per sub-intent
4. OutputGate defaults to monitoring mode
5. clarify_width feeds through G_eff into R equation
6. Tradeoff completeness gated by closure_risk
7. psp_mode from domain config, not PSPDetector computation

**Round 3**: ChatGPT accepted all 7 adjustments with two precision edits:
- clarify_width modifies G (as G_eff) before R is computed, not as a direct new R input
- PSPDetector may compute closure_risk, but must not decide psp_mode

**Consensus statement**:
> FN#070 preserves possibility space through sparse, observational detection and stylistic shaping, not safety judgment. It keeps bounded live paths open, updates them when the human introduces new paths, and permits closure only after exploration or explicit human request.

**ChatGPT's key contributions**: B-prime architecture / "corrective not judicial" OutputGate / clarify_width parameter / domain psp_profile / Arabic cultural phrasing patterns / G_eff formulation for R equation.

**Claude's key contributions**: Sparse Activation fast-path / mutable bounded set / per-sub-intent PSP / OutputGate monitoring default / closure_risk gating for tradeoffs / psp_mode as config not computation.
