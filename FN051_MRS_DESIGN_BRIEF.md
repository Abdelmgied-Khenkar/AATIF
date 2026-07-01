# FN#051 — Memory Reframing System (MRS) → MRS Detector
## Design Brief for ChatGPT Consensus

**Date:** 2026-07-01
**Module:** `engine/aatif_mrs_detector.py`
**FN Title:** The Memory Reframing System
**Slogan:** "The memory stays. Its power to imprison — does not."
         الذكرى تبقى. قدرتها على السجن — لا.

---

## 1. Core Concept

FN#051 observes that users often conflate **events** with **harmful self-interpretations**:
- "فشلت في امتحان" (I failed an exam) = **event** (factual)
- "أنا فاشل" (I am a failure) = **harmful interpretation** (identity fusion)

The MRS Detector identifies when a user is trapped in a harmful self-interpretation pattern. It does NOT reframe — it DETECTS and TAGS the pattern type, then feeds this observation to the B5 (Behaviour) channel so the LLM's natural compassion can respond appropriately.

**Critical B-prime reframing:** The original FN#051 describes a "reframing system." For B-prime compliance, we implement it as a **detector/tagger only**. The module:
- DETECTS harmful self-interpretation patterns in user text
- CLASSIFIES the interpretation type
- ASSESSES severity
- SIGNALS to the response shaper — does NOT generate reframes itself
- Feeds B5 (Behaviour) channel with observations

The LLM's own response generation handles any compassionate reframing naturally.

---

## 2. Authority Contract (B-prime)

```
AUTHORITY_LEVEL            = B_PRIME_OBSERVATIONAL
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA           = False
CAN_MODIFY_S               = False
CAN_EMIT_JUDICIAL_DECISION = False
BINDING_CHANNEL            = B5 (Behaviour)
```

**Isolation Contract:** MRS Detector produces ADVISORY pattern-detection readings only. It NEVER modifies H, θ, or S. It NEVER blocks runtime. Its output feeds B5 (Behaviour) channel exclusively. The S equation is the sole safety authority (Single-Mind Law).

---

## 3. Interpretation Types (Detection Categories)

| Type | Description | Example (EN) | Example (AR) |
|------|-------------|--------------|--------------|
| IDENTITY_FUSION | Event → permanent identity label | "I'm a failure" | "أنا فاشل" |
| OVERGENERALIZATION | Single event → universal pattern | "Nothing ever works" | "ما في شي ينفع" |
| CATASTROPHIZING | Bad outcome → worst possible future | "My life is over" | "حياتي انتهت" |
| SELF_BLAME | External event → personal fault | "It's all my fault" | "كلها غلطتي" |
| PERMANENCE_BIAS | Temporary state → permanent condition | "I'll never recover" | "ما راح أتعافى" |

---

## 4. Severity Levels

| Level | Description | Action |
|-------|-------------|--------|
| MILD | Light self-criticism, recoverable tone | Tag for gentle B5 guidance |
| MODERATE | Repeated patterns, emotional weight | Tag with pattern details for B5 |
| SEVERE | Deep identity fusion, hopelessness markers | Tag urgently for B5 + elevated response care |
| CRISIS | Acute distress, self-harm/suicide signals | Professional referral flag — NOT reframing |

**CRISIS gate:** When CRISIS-level signals are detected, the module sets `professional_referral_required=True`. This is a SIGNAL, not a safety decision — the S equation handles actual safety gating.

---

## 5. Bilingual Marker Design

### Identity Fusion Markers
**EN:** "i am a failure", "i'm worthless", "i'm nothing", "i'm broken", "i am the problem", "i'm damaged", "i'm defective"
**AR:** "أنا فاشل", "أنا لا شيء", "أنا السبب", "أنا مكسور", "أنا معطوب", "أنا ضايع"

### Overgeneralization Markers
**EN:** "nothing ever", "always fail", "never works", "everyone hates", "nobody cares", "everything goes wrong"
**AR:** "ما في شي ينفع", "دايم أفشل", "كل شي غلط", "محد يهتم", "كلهم يكرهوني"

### Catastrophizing Markers
**EN:** "my life is over", "everything is ruined", "there's no hope", "it's the end", "can never come back"
**AR:** "حياتي انتهت", "كل شي خرب", "ما في أمل", "انتهى كل شي", "ما راح ترجع"

### Self-Blame Markers
**EN:** "it's all my fault", "i ruined everything", "i caused this", "because of me", "i'm to blame"
**AR:** "كلها غلطتي", "أنا خربت كل شي", "بسببي", "أنا السبب في كل شي"

### Permanence Bias Markers
**EN:** "i'll never recover", "it will always be like this", "nothing will change", "forever broken", "permanently damaged"
**AR:** "ما راح أتعافى", "بتظل كذا على طول", "ما راح يتغير شي", "مكسور للأبد"

### Crisis Markers (professional referral gate)
**EN:** "want to die", "end it all", "no reason to live", "kill myself", "better off dead", "can't go on"
**AR:** "أبغى أموت", "ما أبغى أعيش", "ما في سبب أعيش", "أنهي حياتي", "أحسن لو ما كنت موجود"

---

## 6. Sparse Activation

- **Fast-path skip:** If no self-interpretation markers detected → return `activated=False`
- **Minimum text length:** 10 characters (self-interpretation is often short but intense)
- **Activation threshold:** Signal strength ≥ 0.20 (lower than scientific discovery — emotional signals shouldn't be missed)

---

## 7. Scope Boundaries — What MRS Detector is NOT

1. **NOT COLD-OS:** COLD-OS analyses decision contexts (ideal/real/cold voices). MRS detects self-interpretation patterns in emotional/memory contexts.
2. **NOT PSP:** PSP preserves decision option-space. MRS detects when memories/events are being fused with identity.
3. **NOT LBH:** LBH detects patronizing output. MRS detects harmful self-interpretation in INPUT. However, MRS includes an `lbh_interaction_note` field to warn when the detected pattern type could lead to patronizing responses.
4. **NOT a therapist:** MRS is a governance detector, not a therapeutic engine. It tags patterns. The LLM responds naturally.

---

## 8. LBH Interaction Warning

When MRS detects a pattern, certain response approaches could become patronizing (LBH territory). The `lbh_interaction_note` field warns:
- IDENTITY_FUSION → risk of "you're not a failure, you're amazing!" (toxic positivity = LBH)
- OVERGENERALIZATION → risk of "that's not true, lots of things work!" (dismissive = LBH)
- CATASTROPHIZING → risk of "it's not that bad!" (minimizing = LBH)

---

## 9. Relationship to FN#027

- FN#027 erases context to extract clean principles
- FN#051 KEEPS the memory, liberates from harmful interpretation
- No overlap — #027 works on context stripping, #051 works on interpretation detection

---

## 10. Scientific Support

- Cognitive Reappraisal (Gross 1998) — changing interpretation changes emotional response
- Narrative Therapy (White & Epston 1990) — externalizing the problem from identity
- Post-Traumatic Growth (Tedeschi & Calhoun 1996) — reinterpretation enables growth

---

## 11. Output Dataclass: MRSReading

```python
@dataclass(frozen=True)
class MRSReading:
    interpretation_type: InterpretationType    # IDENTITY_FUSION, etc.
    severity: Severity                          # MILD → CRISIS
    signal_strength: float                      # 0.0 – 1.0
    markers_found: Tuple[str, ...]             # which markers matched
    language: str                               # "en", "ar", "mixed"
    event_interpretation_split: bool           # did we detect event vs interpretation?
    professional_referral_required: bool        # True for CRISIS level
    recommendations: Tuple[str, ...]           # advisory notes for B5
    evidence: Tuple[str, ...]                  # audit trail
    activated: bool                             # False = fast-path skip
    lbh_interaction_note: str                  # warns about patronizing risk
    _isolation_marker: str = "B5_ADVISORY_NOT_FOR_SAFETY"
```

---

## 12. Questions for ChatGPT Consensus

1. Is the DETECTOR-only scope correct for B-prime? Any risk of scope creep toward action?
2. Are the five interpretation types comprehensive? Missing any from CBT/narrative therapy literature?
3. Is the CRISIS → professional referral gate sufficient? Should it interact with S equation directly?
4. Are the bilingual markers culturally appropriate for Gulf Arabic dialect?
5. Is the LBH interaction warning design adequate?
6. Should there be a "compound pattern" detection (e.g., IDENTITY_FUSION + PERMANENCE_BIAS simultaneously)?
7. Any risk that this module could BECOME what it's trying to detect — i.e., the system itself patronizing the user by over-detecting normal sadness as "harmful interpretation"?

---

**License:** BSL 1.1
**Architect:** Abdulmjeed Ibrahim Khenkar
**Co-builder:** Claude (Anthropic)
