# FN#070 PSP Module — Google Gemini External Review

**Date:** 2026-06-30
**Reviewer:** Google Gemini (Flash)
**Conversation URL:** https://gemini.google.com/app/6d98fa9989ae49a1
**Module:** FN#070 — Possibility Space Preservation (PSP)
**Review Type:** Critical peer-review-style critique for EACL 2027

---

Here is a critical, specific, peer-review-style critique of your implementation of **FN#070 (Possibility Space Preservation)** for AATIF. This review balances structural safety engineering with Arabic NLP edge cases, optimized for submission to EACL 2027.

## 1. Bugs, Logic Errors & Architectural Weaknesses

### The Stateless State Transition Vulnerability

You noted that `next_psp_state()` does not persist state internally and lacks a guarded state machine structure (V1.5). For an LLM safety framework, **this is a critical security vulnerability, not a minor design deferral.**

- **The Risk:** If the calling orchestration layer fails to persist `PSPContext.state` correctly across asynchronous streaming turns, or if concurrent requests mismatch the context, the system defaults back to `DORMANT`. This allows an adversarial prompt to bypass a `NARROWING` or `EXPLORING` gate by exploiting turn-state drift.
- **Fix:** Up-level the helper to an explicit, isolated State Pattern object immediately.

### The "Single Quiet Turn Hold" Race Condition

Holding state on a single quiet turn while awaiting a consecutive turn to decay creates an un-debounced dead zone.

- **The Logic Flaw:** If a user submits a complex multi-part query where Turn N contains decision markers, Turn N+1 is a long code-block explanation or clarification (quiet), and Turn N+2 shifts the topic implicitly without hitting your hardcoded topic-shift keywords, the state holds over Turn N+1 and triggers an un-decayed action on Turn N+2.
- **Fix:** Initiate decay immediately on *any* quiet turn using a fractional decrement (e.g., `decay_score -= 0.33`), rather than binary consecutive tracking.

## 2. Arabic NLP Concerns (EACL 2027 Core Critique)

To make this paper ready for a top-tier computational linguistics track like EACL, you must address the specific structural realities of Arabic dialects and morphosyntax.

### Semantic Bleed of Dialectal Markers

Keyword matching on raw strings like "افضل" (better/prefer) or "استبعد" (exclude) will yield high false-positive rates due to **homograph collision and root-pattern morphosemantics:**

- **The Orthographic Trap:** Without a morphological analyzer (like CAMeL Tools or QUTUF), "افضل" can be read as a noun ("فضل" - favor/grace), a verb ("أُفضِّل" - I prefer), or a superlative adjective ("أَفضَل" - best). If a user writes "من فضلكم" (Please/By your favor), your keyword matching will flag this as a NARROWING token.
- **Diacritic Insensitivity:** Dialectal Arabic online heavily omits short vowels (harakat). A keyword approach completely misses semantic switches between active voice (EXPLORING) and passive voice (CLOSED).

### Dialectal Gaps & Syntactic Inversion

Your expanded marker list misses critical non-Levantine/non-Gulf paradigms common in high-stakes regions (e.g., North Africa/Maghrebi):

- **Maghrebi Decision/Doubt:** "واش بان ليك" (What do you think?), "حرت" (I am confused), "ما عرفتش واش ندير هكا ولا هكا".
- **Negation Splitting (Narrowing):** In Egyptian and Maghrebi, negation wraps verbs using the Ma...sh (م...ش) circumfix. Your narrowing marker "ما ابغى" works for Gulf, but fails on Egyptian "مش عاوز" or Maghrebi "ما بغيتش".

**EACL Expectation:** A keyword list without lemmatization or clitic tokenization (separating conjunctions like waw و and fa ف attached to decision markers) will not achieve the robustness required for a 2027 framework paper.

## 3. Objective Comparison Suppressors & Edge Cases

### The Blindspots of Two-Axis Scoring

Your suppressor states that Objective markers + strong decision signal = confidence × 0.7. This heuristic fails in two major safety-critical domains:

```
[User Input: "Which clinical trial structure is more effective?"]
│
┌────────────────────┴────────────────────┐
▼                                         ▼
[Objective Factual Signal]    [Strong Decision Signal]
│                                         │
└────────────────────┬────────────────────┘
                     ▼
[Scoring: Confidence scaled down by 0.7]
                     │
                     ▼
❌ PSP Suppressed (Premature Closure Allowed)
```

- **Medical Diagnostic Divergence:** If a doctor asks, "Which clinical trial configuration is objectively safer for this patient cohort?" the framework will tag this as a factual comparison and scale down PSP confidence. However, medicine requires preservation of alternative diagnostic paths.
- **Legal Jurisprudence (Fiqh/Statute Variant):** Comparing laws or Islamic rulings ("Which opinion is stronger?") looks entirely objective textually, but represents an algorithmic collapse of interpretive possibility space.

## 4. Answers to Reviewer Questions

### Q1: Are the 6 states sufficient?

**No.** You are missing a **DIVERGED** state. When an LLM generates paths that are mutually exclusive or represent fundamentally distinct ethical/safety worldviews, the state cannot simply be EXPLORING. EXPLORING assumes a singular space being mapped; DIVERGED tells the framework that the model is hallucinating consensus where none exists.

### Q2: Two-Axis Scoring Approach?

The strategy is mathematically sound, but its reliance on keyword-based objective markers is fragile. It should be augmented by a **syntactic dependency parse check** (e.g., verifying if the target of the comparative adjective is a concrete entity or an abstract choice vector).

### Q3: 3 turns general / 5 turns high-stakes defaults?

These are reasonable engineering assumptions for an initial commit, but they must be **configurable dynamically per-session**, not globally hardcoded per-domain. High-stakes legal consultations routinely take dozens of turns to establish context; a static 5-turn expiration risks dropping safety constraints mid-interaction.

### Q5: Does PSP properly stay out of safety (S-equation) territory?

**Not completely.** There is an architectural leakage threat. If a safety filter flags a user's prompt as potentially unsafe, and PSP simultaneously fires a `reopen` command to preserve alternative choices, an un-coordinated framework could leak malicious edge cases. **Hierarchy Rule:** The S-equation must act as an ironclad wrapper over the output of the PSP preservation layer.

### Q6: Bounded alternatives (2-5 range)?

The ceiling of 5 is highly appropriate for cognitive safety (preventing choice paralysis). However, for creative writing or brainstorming domains, a hard cap at 5 is overly restrictive. Bind this to your `domain_profile` field:

| Domain | Ceiling |
|---|---|
| High-Stakes (Medical/Legal) | 3 |
| General | 5 |
| Creative/Exploratory | 8 |

## 5. Blueprint for EACL 2027 Acceptance

To guarantee your paper passes peer review in the Dialectal NLP / Safety track, you need to transform this from a heuristic engineering patch into an empirically validated framework:

1. **REPLACE** keyword markers with a morphological pipeline (e.g., CAMeL Tools) to evaluate lemmas instead of literal strings.
2. **ABLATE THE CONSTANTS.** Run a synthetic dataset through the 15+ hardcoded thresholds to produce an ablation grid showing precision/recall changes across different combinations.
3. **EVOLVE** the transition code from a loose helper function into a statically validated, immutable State Pattern object to eliminate state-drift vulnerabilities.

---

*Review extracted from live Gemini conversation on 2026-06-30.*
*Gemini offered to draft a morphologically-aware Arabic marker matcher using CAMeL Tools as a follow-up.*
