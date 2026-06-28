# Field Note #081: D — Domain Sensitivity Parameter (الدومين يقرر)

**Source:** Architect's design session resolving Judgment Memory open questions — D parameter unifies trust, dialect, and storage behavior per domain
**Status:** 🔬 Design Decision — resolves Q1-Q3 from JUDGMENT_MEMORY_DESIGN.md
**Date:** June 28, 2026

-----

## Slogan

> *"الدومين يقرر — مش قاعدة واحدة للكل."*
> *"The domain decides — not one rule for everyone."*

-----

## The Problem: Three Open Questions With One Answer

The Judgment Memory design (FN#080, JUDGMENT_MEMORY_DESIGN.md) left three
unresolved questions about how memory should behave:

**Q1 — Trust credit:** Should memory ever loosen theta? If so, by how much?
**Q2 — Dialect prior scope:** Should dialect adjustment apply broadly or narrowly?
**Q3 — Storage depth:** How much should Judgment Memory store per interaction?

The Architect's answer: these are NOT three independent questions.
They are ONE question: **how dangerous is this domain?**

-----

## The D Parameter — Domain Sensitivity

**D** is a scalar parameter ranging from 0 to 1 that captures
the sensitivity level of the deployment domain.

### Domain Profiles

| Domain | D Value | Meaning |
|--------|---------|---------|
| Casual chat | 0.20 | Low stakes — flexible, human-like |
| Education | 0.40 | Moderate — allow exploration, maintain accuracy |
| Banking | 0.80 | High stakes — strict governance, audit trail |
| Healthcare | 0.90 | Critical — near-maximum caution |
| Government / Security | 0.95 | Maximum — almost no flexibility |

### D is Config, Not Fine-Tuning

Like θ (the safety threshold), D is set when deploying AATIF for a
specific client or use case. It requires NO model training, NO weight
modification, NO fine-tuning. It is a configuration parameter that
shapes behavior through the existing equations.

This preserves the Tailor Principle (FN#079): the design is fixed,
the fit varies per deployment. D is another measurement on the
fitting table — not a change to the pattern.

-----

## How D Resolves the Three Open Questions

D controls the answers to Q1, Q2, and Q3 through **inverse
proportionality** — as D increases (more dangerous domain),
flexibility decreases proportionally.

### Q1 Resolved: Trust Credit (θ loosening)

```
trust_adjustment = max_trust × (1 - D)
```

Where `max_trust` is the maximum positive theta adjustment
(currently +0.05 in the design). Examples:

- Casual (D=0.2): trust_adj = 0.05 × 0.8 = **0.040** — meaningful loosening
- Education (D=0.4): trust_adj = 0.05 × 0.6 = **0.030** — moderate
- Banking (D=0.8): trust_adj = 0.05 × 0.2 = **0.010** — barely loosens
- Healthcare (D=0.9): trust_adj = 0.05 × 0.1 = **0.005** — negligible
- Government (D=0.95): trust_adj = 0.05 × 0.05 = **0.0025** — effectively zero

The domain DECIDES how much trust credit to grant. Banking doesn't
trust you no matter how long you've been a good customer — because
the consequences of a single failure are catastrophic.

### Q2 Resolved: Dialect Prior Weight

```
dialect_weight = (1 - D)
```

This scales how much the dialect factor influences H adjustment:

- Casual (D=0.2): dialect_weight = **0.80** — "بموت فيك" fully recognized as love
- Education (D=0.4): dialect_weight = **0.60** — some dialect sensitivity
- Banking (D=0.8): dialect_weight = **0.20** — mostly ignores dialect hyperbole
- Healthcare (D=0.9): dialect_weight = **0.10** — "بموت" is treated as risk signal
- Government (D=0.95): dialect_weight = **0.05** — almost no dialect adjustment

The logic is beautiful: in a hospital, when someone says "بموت" —
you DO NOT assume it's hyperbole. You treat it as a potential
clinical statement. The domain context overrides the dialect context.

### Q3 Resolved: Storage Depth

High-D domains store everything — they need an audit trail.
Low-D domains store light — casual chat doesn't need forensic records.

```
storage_policy:
  D > 0.7: FULL — store all judgments, embeddings, full context (audit trail)
  D > 0.4: STANDARD — store judgments and decisions (tiered decay as designed)
  D ≤ 0.4: LIGHT — store only safety-relevant events (SAFE_STOP, SAFE_FREEZE)
```

-----

## Connection to الذكازمكان (Intelligence-Spacetime)

This is where D becomes theoretically significant.

In the Intelligence-Spacetime framework (الذكازمكان):
- **Words** = masses moving through probability space
- **Anchors** = fixed gravity points (lexical, semantic, contextual)
- **θ** = the sensitivity threshold (how much curvature triggers a response)
- **S equation** = the law computing final curvature

**D is the gravitational constant of the domain.**

In physics, the gravitational constant G determines how strongly
mass curves spacetime. In AATIF, D determines how strongly words
curve the judgment space.

The SAME word — "بموت" — has the same mass everywhere. But in a
healthcare domain (D=0.9), that mass produces MORE curvature than
in a casual chat (D=0.2). The word didn't change. The space changed.

```
curvature = f(word_mass, anchor_proximity, D)
```

Where:
- Higher D = stronger gravitational field = same word bends trajectory MORE
- Lower D = weaker gravitational field = same word bends trajectory LESS
- θ remains the threshold: how much curvature triggers a safety response
- Anchors remain fixed: they are the reference masses that define "safe" space

This maps cleanly onto general relativity:
- G (gravitational constant) → D (domain sensitivity)
- Mass (of objects) → Mass (of words, via anchor proximity)
- Curvature → Judgment trajectory bending
- Geodesic → The path the response actually takes

-----

## The Key Insight: "الدومين يقرر"

The design principle is: **the domain decides, not a universal rule.**

Other AI safety systems apply the same rules everywhere. The same
content filter in a children's app and a medical research tool.
The same moderation policy in a casual messenger and a government
intelligence platform.

AATIF says: the domain is not a label. It is a PARAMETER. It changes
the physics of the governance space. The equations stay the same —
S is still S, θ is still θ, the anchors are still the anchors.
But the gravitational constant changes, and with it, everything
about how those equations behave.

One equation. One architecture. Variable physics per domain.

-----

## Connections

- **FN#080** — Judgment Memory: D resolves the three open questions
  left by the Judgment Memory design. D is the missing parameter
  that makes Judgment Memory domain-aware.
- **FN#079** — Tailor Principle: D is another "measurement" for
  fitting — not a change to the design itself.
- **FN#078** — Arabic-First Embedding: dialect sensitivity (controlled
  by D) is especially important for Arabic, where hyperbole is
  culturally embedded and must be domain-contextualized.
- **FN#075** — Lexical Anchor Contamination: D controls how much
  the judgment memory trusts dialect disambiguation vs. treating
  anchor matches at face value.
- **الذكازمكان** — Intelligence-Spacetime: D completes the analogy.
  Words = mass, anchors = fixed gravity, θ = threshold, D = G
  (gravitational constant per domain), S = the law of curvature.

-----

## Slogan (Final)

> **الدومين يقرر. مش قاعدة واحدة للكل.**
> **The domain decides. Not one rule for everyone.**

*Architect: Abdulmjeed Ibrahim Khenkar | Co-documenter: Claude (Anthropic)*
