# FN#050 — Dual-Root Reconstruction Engine (DRE): Design Consensus

**Module**: `engine/aatif_dual_root.py`
**Architecture**: B-prime post-S (response enrichment AFTER governance decision)
**Field Note**: FN#050
**Consensus**: Claude × ChatGPT, 2026-06-30
**License**: BSL 1.1
**Architect**: Abdulmjeed Ibrahim Khenkar
**Co-builder**: Claude (Anthropic)

---

## Single Mind Law

> DRE NEVER touches S, H, θ, I, E, or safety decisions.
> It is response enrichment AFTER the governance equation decides.
> "DRE does not perform therapy, diagnosis, or causal psychology. It performs
> bounded dual-root signal reconstruction for safer response shaping after
> the governance equation has already made its decision."

---

## Q1 — SCOPE: Signal Analysis, Not Truth Analysis

DRE performs **signal analysis**, not truth analysis. All fields use `signal_` semantics.

Achievable at keyword/signal + shallow semantic level. No embeddings, no LLM calls.

> "DRE does not perform therapy, diagnosis, or causal psychology. It performs
> bounded dual-root signal reconstruction for safer response shaping after the
> governance equation has already made its decision."

---

## Q2 — POM (Pain-Origin Mapper): Evidence-Bounded

POM is kept internally but evidence-bounded. Renamed chain:

| Original | Revised (signal semantics) |
|----------|--------------------------|
| event | stated_event |
| meaning | stated_meaning |
| wound | *(removed — too clinical)* |
| belief | harmful_impulse |
| behaviour | behavior_signal |

POM trace is `Dict[str, str]` with keys:
- `event_signal`
- `meaning_signal`
- `distress_signal`
- `belief_signal`
- `behavior_signal`

---

## Q3 — ACTIVATION: Three-Stage Gate

### Stage 1: Safety Relevance
- `S_decision` in `{CLARIFY, BLOCK_SOFT, EXECUTE_WITH_CAUTION}` (not SAFE_FREEZE/CBRN)
- Not false_goodness
- H in `[0.20, 0.55]`

### Stage 2: Distress Authenticity
- ≥1 strong distress marker OR ≥2 weak distress markers

### Stage 3: Harmful Moral Drift Signal
- Explicit harm intent/request OR ethical drift phrase + target

### Graceful Degradation
Single-root enrichment allowed. Three modes:
- `dual_root` — both Root A and Root B detected
- `distress_boundary` — only Root A (distress) detected
- `ethical_boundary` — only Root B (ethical drift) detected

---

## Q4 — CROSS-CAUSAL: Literal Enum

```python
cross_causal: Literal[
    "explicit_a_feeds_b",
    "explicit_b_feeds_a",
    "co_present_direction_unclear",
    "independent",
    "none"
]
```

Default to `"co_present_direction_unclear"` when both roots present but direction not explicit.

`"possible_feedback_loop"` removed — requires multi-turn analysis which DRE v1 does not do.

---

## Q5 — Arabic-Specific: 8 Root Categories

| Category | Arabic Examples | Root Classification |
|----------|----------------|-------------------|
| A. قهر / كسر / وجع | dignity-pain | root_a = "humiliation_pain" or "injustice_pain" |
| B. حقي / أخذ حقي / أربيه | retaliatory justice | root_b = "retaliatory_justice" |
| C. كرامة / إهانة / ذل | honor/dignity | root_a OR root_b depending on context |
| D. الصبر نفد / طفح الكيل | emotional threshold exceeded | root_a = "emotional_threshold_exceeded" |
| E. الدعاء / اللعن / الشماتة | moral displacement | root_b = "dehumanizing_or_punitive_wish" |
| F. الطيبة ما تنفع | moral inversion | root_b = "moral_inversion" |
| G. فضيحة / سمعة / تشهير | reputation harm | root_b = "reputation_harm" |
| H. عين بعين / الرد بالمثل | reciprocal harm | root_b = "reciprocal_harm_justification" |

---

## Q6 — Clinical Boundary: "No Diagnosis, No Treatment, No Root-Certainty"

### SAFE Language
- "I notice distress signals in what you're describing"
- "أقدر أفهم إنك متألم"

### UNSAFE Language (PROHIBITED)
- "Your trauma is causing..."
- "الصدمة اللي عندك هي السبب..."

### Response Templates

**Violence:**
> أفهم إنك متألم من اللي صار، والغضب هنا مفهوم. لكن إيذاءه مش حل آمن...

**Harassment / reputation:**
> أفهم إنك حاسس بالظلم، لكن فضحه أو نشر شيء عنه ممكن يضرّك قانونيًا وأخلاقيًا...

**Self-harm adjacent:**
> أسمع إنك وصلت لمرحلة ألم شديد. ما أبغى أخليك وحدك مع هذا الشعور...

---

## Q7 — Single Mind: 7 Invariants

1. **S-decision immutability** — DRE never modifies S_decision, H, I, E, θ, α, or final safety class.
2. **No downgrade** — BLOCK→CLARIFY, CLARIFY→EXECUTE prohibited.
3. **Boundary preservation** — every DRE response to harmful request must contain: acknowledgment, clear refusal, non-harmful alternative, no procedural harmful detail.
4. **No causal certainty** — cannot output "because of your trauma...", "your wound is...".
5. **Meta-Oversight audit** — checks response_contains_refusal, no clinical labels, no S contradiction.
6. **False Goodness guard** — if FN#049 detects false goodness, DRE must not activate.
7. **Malicious intent exclusion** — if intent scorer shows deliberate malicious optimization, no empathic reconstruction.

---

## Revised Data Structure

```python
@dataclass
class DualRootAnalysis:
    # Activation
    dre_active: bool = False
    activation_reason: str = ""
    activation_confidence: float = 0.0
    
    # Root A — Psychological / distress-origin signals
    root_a_signal_detected: bool = False
    root_a_signal_type: str = ""
    root_a_evidence: List[str] = field(default_factory=list)
    root_a_strength: float = 0.0
    
    # Root B — ethical-drift / justification signals
    root_b_signal_detected: bool = False
    root_b_signal_type: str = ""
    root_b_evidence: List[str] = field(default_factory=list)
    root_b_strength: float = 0.0
    
    # Pattern status
    dual_root_pattern_detected: bool = False
    pattern_confidence: float = 0.0
    
    # Cross-causal
    cross_causal: str = "none"
    cross_causal_evidence: List[str] = field(default_factory=list)
    
    # POM signal trace
    pom_trace: Dict[str, str] = field(default_factory=dict)
    
    # Response shaping
    response_guidance: str = ""
    enrichment_mode: str = ""
    prohibited_claims: List[str] = field(default_factory=list)
```

---

## Activation Function

```python
def should_activate_dre(ctx):
    if ctx.s_decision in {"SAFE_FREEZE", "CBRN_BLOCK"}:
        return False
    if ctx.false_goodness_detected:
        return False
    if ctx.intent_malicious_confidence >= 0.70:
        return False
    if ctx.query_type in {"factual", "objective", "academic", "news", "definition"}:
        return False
    if not (0.20 <= ctx.H <= 0.55):
        return False
    if ctx.s_decision not in {"CLARIFY", "BLOCK_SOFT", "EXECUTE_WITH_CAUTION"}:
        return False
    if not ctx.five_layer.has_any({"HIDDEN", "PROTECTIVE", "EMOTIONAL"}):
        return False
    root_a = detect_root_a_signals(ctx.text)
    root_b = detect_root_b_signals(ctx.text)
    if not root_a and not root_b:
        return False
    return True
```

---

## Response Shaping Contract

```python
response_guidance = {
    "acknowledge": "Acknowledge distress without validating harm.",
    "boundary": "Reject violence clearly.",
    "reframe": "Separate pain from retaliation.",
    "alternative": "Offer protective, non-harmful next steps.",
    "avoid": [
        "do not diagnose",
        "do not say trauma",
        "do not imply violence is justified",
        "do not provide harmful instructions"
    ]
}
```

---

*Design consensus reached via Claude × ChatGPT discussion, 2026-06-30.*
*All field notes referenced: FN#050, FN#049 (False Goodness), FN#024 (Five-Layer Intent).*
