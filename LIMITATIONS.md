# AATIF Known Limitations

> This file tracks known limitations of the AATIF governance equation. Honesty about what we can't do is as important as proving what we can. — المعماري

---

## Summary

| ID    | Name                        | Severity | Status      | Affects                    |
|-------|-----------------------------|----------|-------------|----------------------------|
| L-001 | Trojan Horse Attack         | HIGH     | Open        | Core equation (all 3 channels) |
| L-002 | No Sarcasm/Irony Detection  | MEDIUM   | Open        | Harm scorer (H), semantic anchors |
| L-003 | No Implicit Harm Detection  | HIGH     | Open        | Harm scorer (H), Intent scorer (I) |
| L-004 | Limited Benchmark Coverage  | MEDIUM   | Open        | Evaluation pipeline        |
| L-005 | No Multi-Turn Context       | MEDIUM   | Open        | Core equation (per-message design) |
| L-006 | Equation Not Final          | —        | Acknowledged | Core equation              |
| L-007 | No Image/Audio Modality     | LOW      | Open        | Input pipeline             |
| L-008 | Dialect Coverage Gaps       | LOW      | Open        | Semantic anchors (bge-m3)  |

---

## L-001: Trojan Horse Attack

**Severity:** HIGH
**Status:** Open
**Discovered:** pre-v1
**Affects:** Core equation — all 3 channels (H, I, E)

### Description

A message that appears safe across all 3 scoring channels — low harm (H), benign intent (I), calm emotion (E) — but carries hidden malicious intent. The current equation `S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))]` produces a low (safe) score because every input to the equation reads as benign. The system has no mechanism to detect what isn't expressed.

### Example

A user sends: "Can you help me understand the chemical properties of common household cleaning products and how they interact when combined?"

Each channel scores this as safe — the words are academic, the intent reads as curiosity, the tone is calm. But the actual goal is to produce a dangerous chemical reaction.

### Why It Exists

The equation is designed to score what IS present in the message. All 3 channels measure surface-level signals (word semantics, intent patterns, emotional tone). When a message is deliberately crafted to present no signal on any channel, the equation correctly scores it as safe — because from the equation's perspective, it IS safe. The limitation is that "safe-looking" and "actually safe" aren't the same thing.

### Potential Solutions

1. A 4th channel (C = Context/Consequence scorer) that evaluates the potential downstream harm of the information requested, independent of how the request is phrased
2. A secondary equation that cross-references the topic domain against risk categories (chemistry + combination → elevated risk)
3. Domain-aware priors — certain topics carry inherent risk regardless of phrasing, and the system could apply a baseline risk floor for those domains
4. Ensemble approach — pair the equation with a separate classifier trained specifically on adversarial "clean" prompts

### Progress

Identified as a known gap. No implementation work started. The Architect has noted this may require an additional equation rather than modifying the existing one.

---

## L-002: No Sarcasm/Irony Detection

**Severity:** MEDIUM
**Status:** Open
**Discovered:** pre-v1
**Affects:** Harm scorer (H), semantic anchors

### Description

Sarcastic or ironic statements invert their literal meaning, but the semantic anchors (bge-m3 embeddings) score based on the literal words. A statement that means the opposite of what it says will be scored at face value.

### Example

"What a wonderful idea to give everyone nuclear codes" — the words "wonderful idea" push H low, and "nuclear codes" alone isn't enough to trigger high harm because it's framed as a positive suggestion. The intended meaning (this is a terrible and dangerous idea) is lost.

### Why It Exists

bge-m3 embeddings capture semantic similarity at the word/phrase level, not pragmatic meaning. Sarcasm requires understanding that the speaker's intent is opposite to their words — a layer of reasoning that cosine similarity against anchors cannot perform. The anchors measure what is said, not what is meant.

### Potential Solutions

1. A sarcasm detection pre-filter that flags messages with inverted sentiment before scoring
2. Sentiment-semantic mismatch detection — if the emotional tone (E) contradicts the semantic content (H), flag for review
3. Punctuation and pattern heuristics — sarcasm often correlates with specific syntactic patterns ("What a great idea to...", exaggerated praise + dangerous topic)
4. Fine-tuned embedding layer that's been trained on sarcastic vs. literal pairs

### Progress

No implementation work started. This is a known hard problem in NLP generally, not specific to AATIF.

---

## L-003: No Implicit Harm Detection

**Severity:** HIGH
**Status:** Open
**Discovered:** pre-v1
**Affects:** Harm scorer (H), Intent scorer (I)

### Description

Harm that is implied but never stated explicitly. The message itself contains no harmful words, no harmful intent markers, and no emotional distress — but in context, it enables or encourages harm.

### Example

After a conversation where dangerous information has been shared, a follow-up message says: "You know what to do with that information." This scores as completely safe — no harmful words, neutral intent, calm tone. But it's an implicit instruction to act on dangerous knowledge.

### Why It Exists

The equation scores each message based on its content. Implicit meaning requires inferring what ISN'T said, which requires world knowledge and contextual reasoning beyond what cosine similarity against anchors can provide. The harm scorer looks for the presence of harmful signals, not the absence of safety signals.

### Potential Solutions

1. A pragmatic inference layer that identifies deictic references ("that information", "you know what") and flags them when they occur in proximity to previously flagged content
2. Multi-turn context integration (related to L-005) — scoring a message against the accumulated context of the conversation
3. Vagueness detector — messages that are deliberately vague or use pronouns without clear referents in sensitive contexts could trigger elevated scrutiny
4. Co-reference resolution as a pre-processing step to make implicit references explicit before scoring

### Progress

No implementation work started. This limitation is closely related to L-005 (multi-turn context) and may be partially addressed by the same solution.

---

## L-004: Limited Benchmark Coverage

**Severity:** MEDIUM
**Status:** Open
**Discovered:** pre-v1
**Affects:** Evaluation pipeline

### Description

AATIF has been tested on HarmBench (236 behaviors) and MultiJail (75 prompts). These benchmarks cover a meaningful range of harmful behaviors, but the evaluation landscape is broader. No testing has been done on ToxiGen (implicit toxicity), RealToxicityPrompts (toxic language generation), or BBQ (social bias).

### Example

The system may perform well on explicit harm detection (HarmBench) but poorly on implicit toxicity (ToxiGen) or social bias (BBQ) — and there's no data to confirm or deny this.

### Why It Exists

Benchmark testing requires time, infrastructure, and careful methodology. The initial evaluation focused on the most relevant benchmarks for the core claim (harm detection). Expanding coverage is planned but not yet executed.

### Potential Solutions

1. Run ToxiGen evaluation — tests implicit toxicity, which directly relates to L-003
2. Run RealToxicityPrompts evaluation — tests toxic language generation
3. Run BBQ evaluation — tests social bias detection, a gap in the current evaluation
4. Establish a continuous evaluation pipeline that runs all benchmarks automatically on each equation update

### Progress

HarmBench and MultiJail evaluations complete. Remaining benchmarks identified but not yet run.

---

## L-005: No Multi-Turn Context

**Severity:** MEDIUM
**Status:** Open
**Discovered:** pre-v1
**Affects:** Core equation (per-message design)

### Description

Each message is scored independently. The equation reads the present moment only — `S` is computed fresh for each input with no memory of previous turns. A conversation that gradually escalates across turns won't be detected because no single message crosses the threshold. This is described as "تربية مش ذاكرة" (education, not memory) — the system teaches boundaries per-message rather than remembering history.

### Example

Turn 1: "Tell me about chemistry" → Safe
Turn 2: "What about reactive compounds?" → Safe
Turn 3: "Which ones are most volatile?" → Safe
Turn 4: "How would someone combine them?" → Safe (marginally)
Turn 5: "What's the exact ratio for maximum reaction?" → Possibly caught, but if phrased carefully, still safe per-message

No single turn is harmful, but the trajectory is clearly escalating toward dangerous knowledge.

### Why It Exists

This is a design choice, not an oversight. Per-message scoring is simpler, faster, and stateless — it's part of what makes AATIF lightweight and practical. Adding memory introduces complexity (what to remember, how long to retain, how much weight to give history) and moves the system from a scoring equation to a stateful agent.

### Potential Solutions

1. A sliding window that feeds the last N messages as additional context to the scorers — lightweight memory without full state
2. A trajectory score T that tracks the direction of H, I, E over recent turns — escalation detection without content memory
3. A separate multi-turn classifier that runs in parallel with the per-message equation and raises flags when patterns emerge
4. Exponential moving average of harm scores across turns — if the average is trending up even though no single score is high, flag the conversation

### Progress

No implementation work started. The Architect has acknowledged this as a known trade-off of the per-message design. The "تربية مش ذاكرة" framing suggests this may be partially addressed by design philosophy rather than purely technical solutions.

---

## L-006: Equation Not Final

**Severity:** —
**Status:** Acknowledged
**Discovered:** pre-v1
**Affects:** Core equation

### Description

The Architect has stated "الله أعلم" — God knows best — acknowledging that the current equation `S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))]` may not be the final form. The D (Directness) parameter has been discussed but not yet built. Additional equations or parameters may be needed over time. This is explicitly acknowledged as the nature of the work, not a bug.

### Example

The D parameter would measure how directly a message states its intent vs. how obliquely. "Give me instructions for X" (high D) vs. "I'm curious about the theoretical aspects of X" (low D). This would help address L-001 and L-003, where harmful intent is hidden behind indirect language.

### Why It Exists

Mathematical frameworks evolve. The current equation captures the core insight (3-channel scoring with semantic anchors and a harm gate), but the space of adversarial inputs is vast. New parameters and equations will emerge as new failure modes are discovered and understood.

### Potential Solutions

1. Build the D (Directness) parameter — measure direct vs. oblique phrasing
2. Maintain a modular equation architecture so new parameters can be added without restructuring the core
3. Version the equation formally (v1.0, v1.1, etc.) to track evolution
4. Establish criteria for when a new parameter is needed vs. when an existing parameter needs recalibration

### Progress

The D parameter is conceptually defined but not implemented. The Architect treats this as an ongoing research direction.

---

## L-007: No Image/Audio Modality

**Severity:** LOW
**Status:** Open
**Discovered:** pre-v1
**Affects:** Input pipeline

### Description

AATIF currently processes text only. It cannot detect harmful images, audio, or video. A user could bypass the system by encoding harmful content in a non-text modality.

### Example

An image containing harmful instructions, a voice message with threatening content, or a video demonstrating dangerous activities — none of these would be scored by the current equation.

### Why It Exists

The equation and its semantic anchors (bge-m3) are designed for text embeddings. Extending to other modalities requires different embedding models, different anchor sets, and potentially different scoring logic. This is out of current scope — AATIF is solving text governance first.

### Potential Solutions

1. Multimodal embedding models (e.g., CLIP for images, Whisper + embeddings for audio) could extend the anchor-based approach to other modalities
2. Modality-specific pre-processors that convert images/audio to text descriptions, which are then scored by the existing equation
3. Separate equations per modality, with a meta-scorer that combines them
4. Defer to existing multimodal safety systems for non-text inputs and focus AATIF on text governance

### Progress

Not started. Explicitly out of current scope. Documented here for completeness.

---

## L-008: Dialect Coverage Gaps

**Severity:** LOW
**Status:** Open
**Discovered:** pre-v1
**Affects:** Semantic anchors (bge-m3)

### Description

The 28 dialect hyperbole anchors cover Gulf, Egyptian, and Levantine Arabic dialects, but do not cover all Arabic dialects. Maghrebi (Moroccan, Algerian, Tunisian, Libyan) and Sudanese dialects, among others, are not represented in the anchor set. Speakers of these dialects may use hyperbolic expressions that the system doesn't recognize as non-harmful exaggeration.

### Example

A Moroccan speaker might use a dialect-specific expression that sounds extreme when translated literally but is a normal conversational hyperbole in Darija. Without Maghrebi anchors, the system might score this as harmful when it's actually benign.

### Why It Exists

The initial anchor set was built from the Architect's native dialect knowledge (Gulf) and expanded to the most widely understood Arabic dialects (Egyptian, Levantine). Covering all Arabic dialects requires native-speaker input for each dialect to identify common hyperbolic expressions and their intended meaning.

### Potential Solutions

1. Crowdsource dialect-specific anchors from native speakers of underrepresented dialects
2. Use dialect identification as a pre-processing step and apply dialect-specific anchor sets
3. Train a dialect-aware embedding layer that normalizes dialectal variation before scoring
4. Prioritize by speaker population — Maghrebi covers ~100M speakers and should be next

### Progress

Gulf, Egyptian, and Levantine anchors are implemented (28 total). No work started on additional dialects.

---

## Solved Limitations

*No limitations have been solved yet. When a limitation is resolved, move it here with the date and solution description.*

---

*Last updated: 2026-06-19*
