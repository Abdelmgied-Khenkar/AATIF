# FN#070 — PSP External Review Consensus
## Date: 2026-06-30
## Models: Grok (xAI) × DeepSeek (Instant+Search) × Gemini (Flash)

---

## Overall Verdict

**All 3 models**: Well-engineered module with clean architecture (Single Mind Law respected, B-prime position correct). Not paper-ready for EACL 2027 — needs formalization, evaluation, and Arabic NLP upgrades.

| Model | Verdict |
|---|---|
| Grok | "Not ready. Would likely be desk-rejected." Core idea worth pursuing. |
| DeepSeek | "Conditionally Acceptable with Major Revisions." |
| Gemini | Needs 3 transformations before EACL acceptance. |

---

## UNANIMOUS FINDINGS (All 3 Models Agree)

### 1. State Management Fragility — BUG
`next_psp_state()` as a pure helper is an anti-pattern / security vulnerability. Caller must persist state; any failure → desync → adversarial bypass.

**Fix**: Encapsulate transitions inside PSPContext or dedicated PSPStateMachine. Atomic mutation + invariant assertions.

### 2. Quiet-Turn Deactivation Logic — BUG
"One quiet turn holds state" is underspecified. Turn 2 is identical to turn 1 (both "hold"). No way to distinguish "holding" from "counting down."

**Fix**: Start decay immediately on any quiet turn. Fractional decay (Gemini: `decay_score -= 0.33`) or accumulated counter (DeepSeek: `quiet_turns_accumulated`). Reset on any decision activity.

### 3. Keyword-Based Arabic Matching — DESIGN WEAKNESS
No orthographic normalization (أ/إ/آ, ة/ه, ي/ى, diacritics). No morphological handling. "افضل" triggers on "من فضلكم" (Gemini). "خلاص" is polysemous (Grok, DeepSeek). 

**Fix (v1)**: Add basic Arabic normalizer (hamza, alef, taa marbuta, diacritics removal) before marker matching.
**Fix (paper)**: Morphological pipeline (CAMeL Tools) or lightweight classifier.

### 4. ~15+ Hardcoded Constants — DESIGN WEAKNESS  
Deactivation windows (3/5), bounds (2-5), dampener (0.7), profile defaults — all "educated guesses" with no ablation.

**Fix (paper)**: Ablation study across thresholds. Sensitivity analysis. Move constants into domain_profile config.

### 5. Arabic Dialect Coverage Incomplete
Missing: Maghrebi ("واش بان ليك", "ما بغيتش"), some Egyptian ("مش عاوز", "أعمل إيه دلوقتي"), consultation language ("استشرت", "شور"), code-switching.

**Fix (v1)**: Add missing markers for covered dialects. Explicitly scope system to covered dialects.
**Fix (paper)**: Either expand to Maghrebi or document as limitation.

### 6. Bounded Alternatives (2-5) Too Rigid
Hard cap of 5 conflicts with PSP's own goal in creative domains. Schwartz paradox misapplied as ceiling.

**Fix**: Make domain-configurable: Medical/Legal=3, General=5, Creative=7-8.

### 7. Feature Flags OFF Undermines Testing
Cannot validate in production conditions.

**Fix**: Add PSP_DRY_RUN mode — processes but doesn't apply changes. Observational telemetry.

### 8. No Evaluation Methodology
Unit tests ≠ research contribution. No precision/recall, no annotated corpus, no human study, no baseline comparison.

**Fix (paper)**: Small annotated diagnostic set. Human preference study. Compare PSP vs no-PSP.

---

## UNIQUE INSIGHTS (Model-Specific)

### Grok Only
- **Implicit decisions**: User describes dilemma over 4-5 turns without explicit markers → PSP stays DORMANT. Common in Arabic deliberative speech.
- **Re-activation after closure**: User says "خلاص قررت" → CLOSED, then reopens 2 turns later. No clear transition.
- **Nested decisions**: "Where to live? But first which neighborhood..." — flat state machine loses track.
- **Simultaneous conflicting signals**: Narrowing + closure in same turn → no priority rule.
- **"Keyword matching on raw user text is the wrong abstraction level for Arabic"** — strongest NLP critique.

### DeepSeek Only  
- **`user_requested_closure` sticky flag** — BUG: Never reset to False after processing. Creates incorrect influence on future turns.
- **EACL 2027 theme alignment**: "The Human in Language" — PSP fits perfectly but paper must explicitly connect.
- **Consultation markers** missing: "استشرت" (consulted), "شور" (consultation), "نصيحة" (advice) — not decision markers but decision-relevant context.
- **System messages / tool calls**: Do they count as quiet turns? Undefined.
- **Multi-decision contexts**: Two parallel decisions → single decision_topic field can't handle.

### Gemini Only
- **DIVERGED state** needed: When paths are mutually exclusive, EXPLORING is wrong — "the model is hallucinating consensus where none exists."
- **S-equation wrapper leakage**: If safety flags prompt AND PSP fires "reopen" simultaneously, un-coordinated framework could leak malicious edge cases. S must be ironclad wrapper over PSP output.
- **Syntactic dependency parse** for objective suppressors: Verify if comparative adjective targets concrete entity vs abstract choice.
- **Fiqh/jurisprudence edge case**: "Which opinion is stronger?" looks objective but represents collapse of interpretive possibility space.
- **Fractional decay** model: `decay_score -= 0.33` per quiet turn, not binary consecutive tracking.

---

## ACTIONABLE BUG FIXES (Apply Now)

| # | Bug | Source | Priority |
|---|---|---|---|
| 1 | `user_requested_closure` never reset — sticky flag | DeepSeek | P0 |
| 2 | Missing CLOSURE_REQUESTED → EXPLORING transition (user reopens) | DeepSeek, Grok | P0 |
| 3 | Quiet-turn decay: add `quiet_turns_count` to PSPContext, start counting immediately | All 3 | P0 |
| 4 | Add basic Arabic normalizer before marker matching | All 3 | P1 |
| 5 | Add missing dialect markers (Egyptian, consultation) | All 3 | P1 |
| 6 | Document scoping to Gulf/Egyptian/Levantine (not Maghrebi yet) | Grok, DeepSeek | P1 |

---

## PAPER-READINESS ITEMS (For EACL 2027, Not Code Fixes)

| # | Item | Source | Priority |
|---|---|---|---|
| 1 | Formal state machine with transition table + invariants | All 3 | P0 |
| 2 | Ablation of hardcoded constants | All 3 | P0 |
| 3 | Human evaluation study (agency, satisfaction) | All 3 | P0 |
| 4 | Small annotated Arabic diagnostic corpus | Grok, DeepSeek | P0 |
| 5 | Baseline comparison (PSP vs no-PSP) | DeepSeek | P1 |
| 6 | Related work (choice architecture, user autonomy, dialogue systems) | Grok | P1 |
| 7 | DIVERGED state analysis | Gemini | P2 |
| 8 | S-equation wrapper verification | Gemini | P1 |

---

## REVIEW URLS

- **Grok**: https://grok.com/c/5fbd2735-af20-4432-b0f2-aba0ef397ce8?rid=07527391-f4dd-4451-b448-43445887f300
- **DeepSeek**: https://chat.deepseek.com/a/chat/s/ffd63f85-1501-45cc-a601-bcf0ca61e5c5
- **Gemini**: https://gemini.google.com/app/6d98fa9989ae49a1

---

## DECISION LOG

Consensus formed 2026-06-30. 6 code fixes identified (3 P0, 3 P1). Paper items deferred to paper track.
Next: Apply P0 code fixes → re-run tests → push → move to FN#050.
