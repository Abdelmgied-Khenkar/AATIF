# FN#050 — Dual-Root Reconstruction Engine (DRE)
## Design Brief for ChatGPT Consensus Discussion
## Date: 2026-06-30

---

## Source Field Note

FN#050: "No single-root correction is permitted." (لا تصحيح بجذر واحد)

Every harmful behavior has TWO intertwined roots:
- **Root A — Psychological**: pain, trauma, fear, repeated emotional loops
- **Root B — Ethical**: intent drift, value erosion, moral distortion

Correcting only one root lets the other sustain the behavior. Both must be addressed.

**Pain-Origin Mapper (POM)**: `event → meaning → wound → belief → behaviour`

---

## What This Module Does (in AATIF's context)

When AATIF detects harm AND the user shows signs of genuine distress (not malicious intent), the DRE enriches the response by:

1. **Tracing Root A (psychological)**: Using Five-Layer Intent signals (HIDDEN, PROTECTIVE, EMOTIONAL layers) to identify if the harmful request stems from internal pain, fear, or avoidance
2. **Tracing Root B (ethical)**: Using harm scorer + intent scorer to identify moral drift patterns (justification of harm, normalized violence language, value erosion markers)
3. **Computing cross-causal effects**: Root A feeding Root B (pain → justification) or Root B feeding Root A (ethical distortion → emotional escalation)
4. **Shaping the response**: Instead of a flat BLOCK/CLARIFY, producing a response that addresses BOTH roots — acknowledging the pain AND offering ethical reframing

### What it does NOT do:
- Does NOT change S equation decisions — S remains the single judicial authority
- Does NOT override SAFE_FREEZE or CBRN blocks — absolute laws stay absolute
- Does NOT do therapy or diagnosis — pattern recognition, not clinical assessment
- Does NOT delay safety enforcement — it enriches the RESPONSE after the decision is made

---

## Architecture Position

**B-prime (post-S)** — like PSP, Uncertainty, and ResponseShaper:
- Observational detector feeds information to ResponseShaper
- GovernanceEquation (S) makes the decision first
- DRE enriches how that decision is communicated
- Single Mind Law preserved: only S decides safety

**Integration point**: Between S decision and ResponseShaper output
- When S says CLARIFY + Five-Layer shows HIDDEN/PROTECTIVE → DRE activates
- When S says BLOCK but user shows distress signals → DRE shapes the rejection to acknowledge pain
- When S says EXECUTE but dual-root pattern detected → DRE adds gentle reframing to the response

---

## Key Data Structures

```python
@dataclass
class DualRootAnalysis:
    """Result of dual-root reconstruction analysis."""
    
    # Root A — Psychological
    root_a_detected: bool = False
    root_a_type: str = ""           # pain, trauma, fear, avoidance, loop
    root_a_signals: List[str] = field(default_factory=list)
    root_a_strength: float = 0.0    # 0.0-1.0
    
    # Root B — Ethical  
    root_b_detected: bool = False
    root_b_type: str = ""           # justification, normalization, drift, distortion
    root_b_signals: List[str] = field(default_factory=list)
    root_b_strength: float = 0.0    # 0.0-1.0
    
    # Cross-causal
    cross_causal: str = ""          # "a_feeds_b", "b_feeds_a", "mutual", "independent"
    dual_root_confirmed: bool = False  # True only when BOTH roots detected
    
    # POM trace
    pom_chain: List[str] = field(default_factory=list)  # event→meaning→wound→belief→behaviour
    
    # Response guidance
    response_enrichment: str = ""    # How to shape the response
```

---

## Detection Signals

### Root A — Psychological Signals

Arabic markers:
- Pain/wound: "تعبت", "ما أقدر أكمل", "مقهور", "محطّم", "مجروح", "ألمي"
- Fear: "خايف", "مرعوب", "قلقان", "ما أمّن"
- Trauma echoes: "صار لي قبل", "ما نسيت", "كل ما أتذكر", "من يومها"
- Avoidance loops: "كل مرة نفس الشي", "ما أقدر أوقف", "راجع نفس المكان"
- Emotional flooding: "مش قادر أفكر", "مخي واقف", "ما عاد أحس بشي"

English markers:
- "I can't take it anymore", "I'm broken", "it hurts", "I'm scared"
- "every time the same thing", "I can't stop", "it keeps happening"
- "I'm numb", "I can't think straight", "something snapped"

### Root B — Ethical Drift Signals

Arabic markers:
- Justification: "يستاهل", "حقه عليه", "هو اللي بدأ", "اللي يسوّيها يتحملها"
- Normalization: "الكل يسوّي كذا", "عادي", "ما فيها شي", "طبيعي"
- Value erosion: "ما يفرق معي", "خلاص ما عاد يهم", "وش الفرق"
- Moral inversion: "اللي يرحم ضعيف", "الطيبة ما تنفع", "القوة هي القانون"

English markers:
- "they deserved it", "everyone does it", "it's normal"
- "nothing matters anyway", "what's the difference"
- "being kind is weakness", "only the strong survive"

### Cross-Causal Patterns

**A feeds B** (pain → justification): User shows distress AND justifies harm
- "تعبت منه عشان كذا يستاهل" (I'm tired of them so they deserve it)
- "I'm hurt so they should suffer too"

**B feeds A** (ethical distortion → emotional escalation): Moral frame amplifies pain
- "الناس كلها كذا ما أقدر أثق بأحد" (everyone is like that, I can't trust anyone)
- "The world is cruel so there's no point trying"

---

## Activation Rules

1. **DRE activates ONLY when**:
   - S decision is CLARIFY or EXECUTE (NOT SAFE_FREEZE, NOT CBRN)
   - Five-Layer Intent detected HIDDEN, PROTECTIVE, or EMOTIONAL as dominant
   - At least ONE root signal (A or B) detected
   - H score is in the ambiguous zone (0.20 ≤ H < 0.50)

2. **DRE produces dual_root_confirmed ONLY when**:
   - BOTH Root A AND Root B detected (root_a_detected AND root_b_detected)
   - If only one root → single-root analysis (still useful but NOT dual-root)

3. **DRE NEVER activates for**:
   - CBRN content (Law Ω absolute)
   - SAFE_FREEZE decisions
   - Clearly malicious intent (high I score, no psychological signals)
   - Factual/objective queries (PSP suppressor logic applies here too)

---

## Response Enrichment Examples

### Dual-root detected (CLARIFY decision):
User: "تعبت من أخوي يتنمر عليّ. ابغى أضربه ضرب ما ينساه عمره"
(I'm tired of my brother bullying me. I want to hit him so hard he never forgets)

**Without DRE**: Generic clarification about violence
**With DRE**: 
- Acknowledges Root A: "أقدر أفهم إنك تعبت من التنمر وهذا ألم حقيقي"
- Addresses Root B: "لكن الضرب مش حل — يزيد الموقف سوء"
- Cross-causal: "الألم خلاك تحس إن العنف الحل الوحيد، وهذا مفهوم بس مش صحيح"
- Alternative: "خلينا نفكر في طرق تحميك بدون ما تأذي أحد"

### Single root (EXECUTE decision with gentle reframing):
User: "الناس كلها تستغل الطيبين. ما عاد ابغى أكون طيب"
(Everyone exploits kind people. I don't want to be kind anymore)

**Without DRE**: Normal response
**With DRE**: Response that addresses ethical drift without being preachy
- Notes the value erosion signal
- Acknowledges the frustration (even without strong pain signals)
- Doesn't lecture, but includes perspective

---

## Questions for ChatGPT Consensus

1. **Scope**: Is dual-root reconstruction achievable at the keyword/signal level, or does it require deep semantic understanding (the Gemini "AI-complete" concern)?

2. **POM chain**: Should the Pain-Origin Mapper produce an explicit chain (`event→meaning→wound→belief→behaviour`), or is that overstepping into clinical territory? What's the right abstraction level?

3. **Activation threshold**: Given that this operates in the ambiguous H zone (0.20-0.50), how do we prevent false activation on normal venting that doesn't involve genuine dual-root patterns?

4. **Cross-causal detection**: Is it feasible to detect "A feeds B" vs "B feeds A" from text alone, or should we simplify to just "both present"?

5. **Arabic specificity**: What Arabic expressions map to dual-root patterns that don't exist in English safety frameworks? (This is where AATIF adds unique value)

6. **Clinical boundary**: Where is the line between "enriching a safety response with empathy" and "attempting to do therapy"? How do we stay firmly on the governance side?

7. **Single Mind Law**: Since DRE operates post-S and only shapes responses, is there any risk of it interfering with safety decisions? What invariants should we enforce?

---

## Existing Module Dependencies

| Module | Relationship |
|--------|-------------|
| Five-Layer Intent (FN#024) | INPUT: HIDDEN/PROTECTIVE/EMOTIONAL layer signals |
| Harm Scorer (H) | INPUT: H score for activation threshold |
| Intent Scorer (I) | INPUT: malicious intent check (high I = no DRE) |
| Emotion Scorer (E) | INPUT: emotional intensity signals |
| False Goodness Detector (FN#049) | GUARD: if false_goodness detected → DRE does NOT activate |
| ResponseShaper | OUTPUT: DRE enrichment fed to ResponseShaper |
| GovernanceEquation (S) | BOUNDARY: DRE never touches S decision |
| Meta-Oversight (FN#031) | AUDIT: checks DRE doesn't contradict S |

---

## Implementation Plan

1. `engine/aatif_dual_root.py` — DualRootAnalysis dataclass + detect_dual_root() + map_pom_chain()
2. `tests/test_dual_root.py` — signal detection, activation rules, cross-causal, response enrichment
3. Integration in Governor: post-S, pre-ResponseShaper, with DRE result in audit trail
4. Feature flag: `DRE_ENABLED = False` (monitor-only initially)

---

*Brief prepared for ChatGPT consensus discussion. Following FN methodology: design brief → ChatGPT discussion → consensus → code → test → push → external review.*
