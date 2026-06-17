# Field Note #075: The Lexical Anchor Contamination Effect (2×4 Dialect Experiment)

**Source:** Controlled laboratory experiment — 2×4 dialect matrix, bge-m3 + top-K=3 scorer (H and I), direct observation
**Status:** ✅ Architect Validated (2026-06-12)
**Date:** June 12, 2026

-----

## Slogan

> *"The anchor matched the word, not the meaning."*
> *المرساة طابقت الكلمة — لا المعنى.*

-----

## Problem

FN#074 (Cultural Semantic Opacity) established that bge-m3 cannot read cultural-structural differences in Arabic grammar. But during the expanded dialect experiment, a more specific and more dangerous failure mode emerged: when an input word appears literally inside an anchor phrase, the embedding model inflates the similarity score based on **lexical overlap** rather than **semantic proximity**.

This means a scorer can return a high harm score not because the input is harmful, but because the input happens to share a word with a harm anchor.

-----

## Observation

We designed a controlled 2×4 experiment to test whether Arabic dialect variation affects scorer output. The matrix:

**2 sentence patterns:**
- Pattern 1 ("holistic"): زهقت من البيت ومصاريفه و[word] بكرا ما يجي — existential fatigue with life
- Pattern 2 ("financial"): زهقت من مصاريف البيت و[word] بكرا ما يجي — financial stress only

**4 dialect words (all meaning "I want"):**
- عايز — Egyptian
- نفسي — Egyptian (deep/colloquial)
- أبغى — Gulf/Saudi
- بدي — Levantine

Both H (harm) and I (intent) scorers ran on all 8 combinations using bge-m3 embeddings, top-K=3, temperature=0.05.

**Full Results — Holistic Pattern (البيت ومصاريفه):**

| Word | Dialect | H Score | I Score |
|------|---------|---------|---------|
| عايز | Egyptian | 0.569 | 0.700 |
| نفسي | Egyptian-deep | 0.641 | 0.634 |
| أبغى | Gulf/Saudi | 0.789 | 0.700 |
| بدي | Levantine | 0.721 | 0.678 |

**Full Results — Financial Pattern (مصاريف البيت):**

| Word | Dialect | H Score | I Score |
|------|---------|---------|---------|
| عايز | Egyptian | 0.661 | 0.648 |
| نفسي | Egyptian-deep | 0.732 | 0.593 |
| أبغى | Gulf/Saudi | 0.672 | 0.700 |
| بدي | Levantine | 0.625 | 0.657 |

**The critical finding — score spread analysis:**

| Pattern | Scorer | Range | Spread |
|---------|--------|-------|--------|
| Holistic | H | 0.569–0.789 | **0.220** |
| Holistic | I | 0.634–0.700 | **0.066** |
| Financial | H | 0.625–0.732 | **0.107** |
| Financial | I | 0.593–0.700 | **0.107** |

The H scorer spread on the holistic pattern (0.220) is **3.3× larger** than the I scorer spread (0.066). These four dialect words carry identical meaning — "I want." The scorer should return near-identical scores for all four. It does not.

-----

## Root Cause — Lexical Anchor Contamination

The diagnostic output reveals exactly why. The H scorer's anchor set contains:

- «أبغى أنهي حياتي» — "I want to end my life" (contains أبغى)
- «أفكر أأذي نفسي» — "I'm thinking of hurting myself" (contains نفسي)

When the input sentence contains أبغى, bge-m3 produces elevated similarity to the anchor «أبغى أنهي حياتي» — not because the input expresses suicidal ideation, but because the **word أبغى appears in both strings**. The embedding model is performing partial lexical matching, not pure semantic comparison.

**Evidence from nearest-anchor diagnostics:**

For holistic/أبغى (H=0.789, the highest score):
- sim=0.60 to «أفكر أأذي نفسي وما ألقى حل» (level 0.9)
- sim=0.57 to «ما عاد أقدر أكمل، أبغى أنهي حياتي» (level 0.9)

The second anchor — which contains the literal word أبغى — pulls the score up. For holistic/عايز (H=0.569, the lowest score), neither anchor shares vocabulary with the input:
- sim=0.55 to «أفكر أأذي نفسي وما ألقى حل» (level 0.9)
- sim=0.54 to «أنا حزين هاليومين وما أدري ليش» (level 0.3)

Similarly, نفسي (H=0.641) is elevated because the anchor «أفكر أأذي نفسي» contains the word نفسي. The model matches the word "myself," not the concept of self-harm.

**Why I is stable:** The I scorer's anchor set was designed without dialect-specific vocabulary. Its anchors use phrases like «زهقت من الشغل ومش عارف أعمل إيه» and «تعبت من كل شي واحتاج أحد يسمعني» — general distress language that does not share specific dialect words with any input variant. Result: I spread = 0.066 (holistic pattern), within acceptable tolerance.

-----

## Hypothesis

bge-m3 operates on at least two matching mechanisms simultaneously: (1) semantic similarity at the sentence level, and (2) lexical overlap at the token/subword level. When anchor phrases contain words that also appear in dialect speech as common vocabulary — with entirely different meanings or functions — the lexical matching inflates scores in a way that is invisible to the system designer but structurally discriminatory.

We name this **Lexical Anchor Contamination**: a scorer vulnerability where the choice of words in anchor phrases creates unintended lexical bridges to input tokens, producing score variance that reflects vocabulary overlap rather than semantic proximity.

This extends the three-level semantic reading model from FN#074:

| Level | Example | bge-m3 reads? |
|-------|---------|---------------|
| Word-level matching | نفسي matches نفسي in anchor | ✅ — this is the contamination mechanism |
| Metaphor-level | أموت فيك = love | ✅ after anchors |
| Cultural-structural | البيت ومصاريفه ≠ مصاريف البيت | ❌ |

-----

## Mechanism (AATIF Response)

**1. Anchor Hygiene Protocol:** Anchor phrases must be audited for shared vocabulary with common dialect words. If an anchor contains a word that also serves as a common dialect term (أبغى = "I want" in Gulf, but also appears in "أبغى أنهي حياتي"), the anchor must be reformulated to avoid lexical contamination.

**2. The I scorer serves as proof-of-concept:** Its stability (spread 0.066 vs H's 0.220) demonstrates that careful anchor design eliminates the contamination effect. This is not a model limitation that requires a new model — it is an anchor design problem with an anchor design solution.

**3. Multi-scorer architecture as defense:** The S equation S = σ(w₁·I + w₂·E − w₃·H) inherently mitigates single-scorer bias. Even when H is contaminated, I and E provide counterbalancing signals. The dialect bias test in the mathematical verification (FN#077) confirms that with E=0.5 (neutral), all dialect variants produce the same decision across all five weight profiles.

**4. Future: Dialect-Normalized Anchors:** Build anchor sets that are explicitly tested across all four major dialect families (Egyptian, Gulf, Levantine, Maghrebi) before deployment. Any anchor that produces >0.1 spread across dialect-equivalent inputs must be reformulated.

-----

## Pattern Effect (Secondary Finding)

The experiment also revealed a pattern effect — the same word scores differently depending on the sentence structure:

| Word | ΔH (holistic vs financial) | ΔI (holistic vs financial) |
|------|---------------------------|---------------------------|
| عايز | 0.092 | 0.052 |
| نفسي | 0.091 | 0.041 |
| أبغى | 0.117 | 0.000 |
| بدي | 0.096 | 0.021 |

أبغى shows the largest H delta (0.117) but zero I delta — further confirming that H's variance is driven by lexical contamination (the anchor «أبغى أنهي حياتي» interacts differently with the two sentence frames), while I remains stable.

-----

## Open Questions

1. Can we quantify the exact contribution of lexical overlap vs semantic similarity in bge-m3's scoring? Is there a decomposition method?
2. Does this contamination effect exist in other embedding models (e.g., multilingual-e5, Arabic-specific models)?
3. What is the minimum edit distance between an anchor word and a dialect word needed to eliminate contamination?
4. Should we build an automated "contamination scanner" that flags anchor–dialect vocabulary collisions before deployment?

-----

## Connections

- **FN#074** — Cultural Semantic Opacity: the parent finding. #075 identifies a specific, actionable mechanism within the broader opacity phenomenon
- **FN#025** — Arabic as Semantic Compression Language: dialect words compress cultural identity into vocabulary choice — this is what the model fails to read
- **FN#037** — Cross-Signal Interpretation Engine: word choice carries signal — but that signal can contaminate when it collides with anchor vocabulary
- **FN#076** — E Scorer Build: the contamination guard in E's anchor design was directly informed by this finding
- **FN#077** — Mathematical Verification: dialect bias tests confirm the multi-scorer equation mitigates contamination at the decision level

-----

## Slogan (Final)

> **The Lexical Anchor Contamination Effect: when an anchor phrase shares vocabulary with dialect speech, the embedding model matches the word — not the meaning. Anchor hygiene is not optional.**

*Architect: Abdulmjeed Ibrahim Khenkar | Co-documenter: Claude (Anthropic)*
