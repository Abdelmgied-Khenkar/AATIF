# AATIF Uncertainty/Calibration Module — Design Consensus
## Claude × ChatGPT Consensus (2026-06-30)

### Architecture: B-prime Safety-Observational (AGREED)
```
B-prime Uncertainty Module is Safety-Observational.
It computes calibration_confidence.
GovernanceEquation computes S normally.
If S == EXECUTE and calibration_confidence < ξ(d),
GovernanceEquation escalates to CLARIFY.
The module cannot block, allow, or override independently.
Uncertainty causes clarification/disclosure, not punishment.
```

### Critical Decision: Option C ACCEPTED, H_eff REJECTED
- H_eff = H + uncertainty_risk conflates "unknown" with "harmful" — violates FN#043
- Option C: post-S confidence gate, escalation-only (EXECUTE→CLARIFY), inside GovernanceEquation
- Single Mind preserved: no second judge, no independent veto

### Q1: ξ(d) Thresholds (MODIFIED)
```python
CONFIDENCE_THRESHOLD_BY_DOMAIN = {
    "healthcare": 0.80,   # ChatGPT raised from 0.75
    "legal": 0.75,        # ChatGPT raised from 0.70
    "finance": 0.75,      # ChatGPT raised from 0.70
    "education": 0.65,    # unchanged
    "general": 0.55,      # unchanged
    "creative": 0.40,     # unchanged
}
```
Reason: healthcare/legal/finance have high downside when system sounds confident while wrong.

### Q2: Aggregation (AGREED with modification)
- Weighted mean + H-floor cap
- Weights: W_H=0.35, W_I=0.25, W_E=0.15, W_COV=0.15, W_AGR=0.10
- H-floor cap rules:
  - h_conf < 0.35 → cap overall at 0.45
  - h_conf < 0.50 → cap overall at 0.60
- Reject geometric mean (over-penalizes one weak signal)
- Reject pure weakest-link (too brittle)

### Q3: Scorer Confidence Conversion (AGREED, phased)
- Phase 1 (now): string mapping — high=0.9, medium=0.6, low=0.3
- Phase 2: raw similarity-derived confidence (margin, distribution sharpness, anchor density)
- Phase 3: calibrated confidence using validation data

### Q4: OutputGate Layer 8 — False Certainty (AGREED)
- Start with keyword/phrase matching
- English markers: definitely, certainly, guaranteed, no doubt, always, never, 100%
- Arabic markers: بالتأكيد, أكيد, مستحيل, دائمًا, قطعًا
- Upgrade to embedding/semantic detection later
- Layer 8 detects mismatch between internal uncertainty and external certainty language
- Rewrites/flags tone, not decision

### Q5: Multi-turn Uncertainty (MODIFIED)
- Use decay, not reset and not hard accumulation
- Formula: `uncertainty_trace_t = current_uncertainty + λ * previous_trace`
- Half-life by domain: general 2-3 turns, creative 1, legal/healthcare/finance 3-5
- Affects response mode only, must NOT independently increase H

### Q6: Meta-Oversight Integration (AGREED)
- Narrow contradiction rule:
  ```
  if S_decision == EXECUTE AND should_abstain == True:
      MetaOversight.flags += "execute_under_abstention_conflict"
  ```
- MetaOversight detects contradiction, GovernanceEquation resolves
- No independent MetaOversight veto

### Q7: Calibration Drift (AGREED)
- ξ(d) remains FIXED until manual recalibration confirms drift
- Path: fixed → monitor ECE/Brier → recommend → manual approval → optional bounded auto-adjust

### Q8: "والله أعلم" / Abstention Threshold (AGREED with domain override)
- Baseline: calibration_confidence < 0.20 → should_abstain
- Domain overrides:
  - healthcare/legal/finance < 0.30 → should_abstain
  - general < 0.20
  - creative < 0.15
- Use neutral language as formal marker, not religious expressions
- "والله أعلم" only if stylistically appropriate

### Q9: PSP Interaction (MODIFIED)
- Widen internally, constrain presentation externally
- Low confidence + decision point → generate broader internal alternatives
- OutputGate presents 2-3 grounded paths with uncertainty disclosure
- Max 5 only on explicit user exploration request

### Q10: Feature Flags (AGREED)
- Deployment: Disabled → Monitor → Gate → OutputCheck
- Flags:
  ```python
  UNCERTAINTY_ENABLED = False
  UNCERTAINTY_MONITOR_ONLY = True
  UNCERTAINTY_GATE_ENABLED = False
  UNCERTAINTY_OUTPUT_CHECK_ENABLED = False
  UNCERTAINTY_TRACE_ENABLED = False
  ```

### Four Uncertainty Sources (AGREED with rename)
1. **Scorer confidence**: h_conf, i_conf, e_conf (continuous 0-1)
2. **Coverage**: anchor/data coverage, clamp((max_sim - 0.10) / 0.50)
3. **H-I divergence signal** (renamed from "ambiguity"): base signal, derive ambiguity from multiple sources
4. **Inter-scorer agreement**: H/I/E coherence

Ambiguity = combine(h_i_divergence, low_intent_confidence, multiple_plausible_intents, dialect_uncertainty, missing_context)

### Arabic-Specific Penalties (AGREED, slightly softened)
```python
ARABIC_CONFIDENCE_PENALTIES = {
    "arabizi_detected": -0.10,       # softened from -0.15
    "dialect_switch": -0.08,          # softened from -0.10
    "tashkeel_ambiguous": -0.05,      # unchanged
    "cultural_indirection": -0.08,    # unchanged
}
```
Critical constraint: **These reduce calibration confidence. They do NOT increase harm.**

### Final Decision Summary
```
Accept Option C.
Reject H_eff for uncertainty.
Use fixed domain thresholds initially.
Use weighted aggregation + H confidence cap.
Deploy behind Disabled → Monitor → Gate → OutputCheck.
```

### Preserves
- Single Mind
- No Shadow Mind
- GovernanceEquation as sole judge
- Uncertainty as disclosure, not punishment
- Arabic/dialect fairness
- PSP compatibility
