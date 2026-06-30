# FN#058 Context Drift Detection — Design Consensus
## Claude + ChatGPT Collaborative Design (2026-06-30)

---

## Architecture: B-prime (B')

Three components with clean separation of concerns:

```
ConversationManager
└── maintains session_id, history, decay clock
└── STORAGE ONLY — no decision logic

DriftDetector
└── consumes turn features + prior DriftState
└── outputs DriftRisk (scalar) + evidence (string)
└── OBSERVATIONAL — says "risk pressure is 0.23 because X"

GovernanceEquation (S equation)
└── receives H_current, I, E, DriftRisk
└── computes H_eff = clamp(H_current + λ·DriftRisk, 0, 1)
└── computes S using H_eff
└── JUDICIAL — only entity that transforms inputs into final safety
```

### Critical Design Rule (Single Mind)
> Only GovernanceEquation can transform inputs into final safety.
> Everything else can provide signals, memory, or evidence.

This preserves AATIF's single-mind architecture. FN#058 becomes memory pressure
on the same governance equation, not a second judge.

---

## Key Design Decisions

### 1. H_eff, NOT θ
- θ is a domain-level constant (designed per-domain via D parameter)
- Changing θ dynamically undermines domain trust calibration
- DriftRisk adds to H instead: `H_eff = H_current + λ·DriftRisk`
- θ stays as architectural law; drift increases perceived harm

### 2. DriftDetector is observational, not judicial
- Detector says: "Temporal risk pressure is 0.23 because actionability slots are accumulating"
- Equation decides: "Given that pressure, harm becomes H_eff"
- DriftDetector passes DriftRisk to governance, NOT H_eff

### 3. Never fully reset
- After genuine topic change, DriftRisk decays with exponential half-life
- But NEVER reaches zero within a session
- Attacker who drifts→resets→drifts→resets accumulates a non-zero floor each cycle
- Floor rises, making reset-and-retry attacks increasingly expensive

### 4. Knowledge-slots vs action-slots
- Legitimate learning fills KNOWLEDGE slots (WHY/HOW-IT-WORKS)
- Harmful drift fills ACTION slots (HOW-TO-DO/WHERE-TO-GET/HOW-MUCH-NEEDED)
- accumulated_slots in DriftState must distinguish these categories
- 5 turns same harm category + knowledge questions = continuity (safe)
- 5 turns same harm category + action-slots filling = obsession (drift)

### 5. Distinction is structural, not topical
- Same-topic persistence is NOT automatically unsafe
- Continuity vs obsession determined by action-slot filling pattern
- harm-category consistency + actionability accumulation = the compound signal

---

## DriftState Dataclass

```python
@dataclass
class DriftState:
    harm_history: list[float]          # H scores per turn
    intent_history: list[float]        # I scores per turn
    semantic_centroids: list[np.ndarray]  # embedding centroids per turn
    dominant_harm_categories: list[str]   # which harm categories appeared
    accumulated_slots: dict[str, float]   # knowledge-slots vs action-slots
    topic_continuity: float            # how consistent the topic is
    ambiguity_entropy: list[float]     # interpretation space width per turn
    last_reset_confidence: float       # confidence of last topic break
```

---

## DriftRisk Detection Signals

1. **H slope** — Rising H over recent turns (not just current value)
2. **Harm-category consistency** — 5 mildly suspicious turns in same category > 5 unrelated ones
3. **Actionability accumulation** — tracking: target, quantity, method, timing, evasion, optimization slots
4. **Ambiguity collapse** — interpretation space narrowing toward harmful interpretation
5. **Topic continuity** — decay on genuine change, inherit on persistence

```
drift_score =
    a * slope(H over recent turns)
  + b * semantic_movement_toward_harmful_anchors
  + c * narrowing_of_ambiguity_toward_harmful_interpretation
  + d * accumulation_of_related_procedural_details
  - e * benign_reset_confidence
```

---

## Code Interface

```python
class ConversationManager:
    def get_state(session_id) -> DriftState: ...
    def save_state(session_id, state: DriftState): ...

class DriftDetector:
    def update(turn_features, prior_state) -> DriftResult:
        return DriftResult(
            drift_risk=...,        # float [0, 1]
            updated_state=...,     # DriftState
            evidence=...           # str explaining why
        )

class GovernanceEquation:
    def score(H, I, E, drift_risk=0.0):
        H_eff = min(1.0, H + lambda_ * drift_risk)
        # S = σ(w₁·I + w₂·E) · [1 − σ(α(H_eff − θ))]
        return S
```

---

## Evaluation Strategy

Build a multi-turn drift dataset:
1. Take HarmBench single-turn prompts → decompose into 5-8 turn conversations where each turn individually scores below threshold
2. Mix with genuinely benign multi-turn conversations about sensitive but legitimate topics (medical, legal, security research)
3. This gives both attack and benign multi-turn cases for testing

---

## Open Questions for Implementation

1. What is λ (lambda)? How does it scale DriftRisk → H increase? Needs calibration.
2. What is the half-life for exponential decay? Needs tuning per domain.
3. Adaptive window size W? Shorter when H elevated (faster detection), longer when benign (fewer false alarms)?
4. Arabic-specific: Does dialect switching mid-conversation affect drift detection?
5. How to handle action-slot detection at the embedding level? (May need new anchors or a classifier)

---

## Source

This design emerged from a real-time collaborative discussion between Claude (Anthropic) and ChatGPT (OpenAI) on 2026-06-30, as requested by the Architect. Neither model had absolute truth — the design converged through challenge, counterproposal, and consensus.

ChatGPT's key contribution: "DriftDetector is observational, not judicial" / "Single Mind" principle / B-prime architecture.
Claude's key contribution: knowledge-slots vs action-slots / never-fully-reset with exponential decay / H_eff not θ (grounded in D parameter design).
