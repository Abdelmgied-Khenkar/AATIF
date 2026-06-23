# AATIF Engine — Fresh-Eyes Code Review

**Reviewer:** Codex (fresh pair of eyes)
**Date:** 2026-06-23
**Scope:** All 13 modules in `engine/`, plus wiring/tests
**Stance:** This is an AI-safety system. Rigor over politeness. Where I say "fail-open," I mean the system can let unsafe input through.

---

## Summary

The individual modules are, in isolation, thoughtful and unusually well-documented. Each one is internally coherent, has a self-test, and is backed by tests (670 passing). The math is clean and the anchor curation in the semantic scorers is genuinely good.

**But the system as a whole is not what the docstrings describe.** Two findings dominate everything else:

1. **There are two separate, divergent governance engines**, and the one that is actually wired into the pipeline is *not* the calibrated semantic one the paper's numbers describe.
2. **The headline `S(d) → P(d) → R(d) → output-gate` pipeline does not exist in code.** Five of the modules (output gate, domain protocols, response shaper, conversation memory, and the gated S-equation engine) are islands — imported only by their own tests. Nothing chains them.

Everything else (fail-open edges, unbounded state, sigmoid saturation, duplicated code) is real and worth fixing, but secondary to those two. A reader of the module docstrings would believe a five-stage governed pipeline ships; what actually ships is `pipeline_connector → AATIFIntentEngine`, a regex-based intent reader.

I found **0 syntax/logic bugs that crash**, but **several fail-open safety edges** and **two architectural gaps that invalidate the system's own description of itself.**

---

## Critical Issues

### C1 — Two disjoint governance engines; the deployed one is the *uncalibrated* one

There are two completely separate harm/intent assessment systems:

| | **AATIFEngine** (`aatif_s_equation.py`) | **AATIFIntentEngine** (`aatif_intent_engine.py`) |
|---|---|---|
| Harm signal | semantic embeddings (bge-m3, 171 anchors) | **regex/substring** (`HARM_PATTERNS`, `intent_engine.py:136`) |
| Equation | gated `σ(w₁I+w₂E)·(1−σ(α(H−θ)))`, domain θ | classic `σ(w₁I+w₂E−w₃H)`, **different weights** |
| Weights | `PROFILES` w1=2.0,w2=1.5,w3=3.0 (`s_equation.py:222`) | `MODES` safe_environment w1=1,w2=1,w3=1 (`intent_engine.py:214`) |
| Thresholds | θ=0.40 + decision bands | `tau_rewrite`/`tau_stop` = 0.70/0.88 |
| Hysteresis | `HysteresisController` (γ+) | its own `_in_clarify_zone` dict (`intent_engine.py:289`) |
| Jailbreak/CBRN | `_JAILBREAK_MARKERS` (`s_equation.py:193`) | `CBRN_TRIGGERS`/`OVERRIDE_*` (`intent_engine.py:227`) |

`aatif_pipeline_connector.py:38,254` imports **only** `AATIFIntentEngine`. So the production path (`build_intent_result`) runs the **regex** engine. The semantic engine — the one whose held-out F1 0.943 / precision 0.93 are quoted throughout `s_equation.py:49-64` and presumably in the paper — is invoked by **nothing except tests**.

Consequences:
- The `H` that actually drives shipped decisions is a regex max over `{0.4, 0.6, 0.7, 0.9}` buckets (`intent_engine.py:136-147,644-651`), on a completely different scale than the semantic `H∈[0,1]` the bands were tuned for.
- The entire body of work on gated equation, domain θ(d), educational "safe" anchors, counter-harm anchors, and unknown-territory detection **is not in the decision path.** It is dead relative to production.
- Two divergent CBRN/jailbreak lists must be maintained; they already disagree (e.g. `keylogger` is in `s_equation`'s list but the Arabic CBRN regex lives only in `intent_engine`).

**This is the single most important thing to resolve.** Pick one harm source. If the semantic engine is the intended product, `pipeline_connector` must call it; if the regex engine is, then the paper's numbers describe a system that isn't shipped.

---

### C2 — The `S→P→R→gate` pipeline has no orchestrator

Every module advertises the same architecture:
- `output_gate.py:9`: `S(d) → P(d) → R(d) → LLM → [OUTPUT GATE] → user`
- `domain_protocols.py:13-23`: `User message → S(d) → P(d) → R(d) → output`
- `r_equation.py:26-31`: same three-layer story

I grepped every import in `engine/`. **No module chains them.** Concretely:
- `aatif_output_gate.py` — imported by nobody but its test.
- `aatif_domain_protocols.py` — imported by nobody but its test.
- `aatif_response_shaper.py` — imported by nobody but its test.
- `aatif_conversation_memory.py` — imported by nobody but its test.
- `AATIFEngine` / `compute_s_gated` — imported by nobody but tests.

So:
- `P(d)` computes `combined_instructions` (`domain_protocols.py:588`) that **nothing injects** into a response.
- `R(d)` computes a style that **nothing applies.**
- The output gate — "آخر حارس / the last guard" (`output_gate.py:11`) — is **never called on any real output.**
- Conversation memory's context is **never fed** to anything.

These pieces are built with compatible interfaces (the shaper consumes an `IntentReading`; the gate consumes a `ProtocolResult`) — they're *designed* to plug together — but the plug is missing. **There needs to be one orchestrator module** that runs the message through S, then P, merges P's instructions + R's style + memory context, calls the LLM, and runs the output gate on the result. Until it exists, the "five-stage governed pipeline" is aspirational.

---

### C3 — The output gate does not enforce `P(d)` BLOCK or EMERGENCY

Even if C2 were wired, the gate's enforcement is hollow:

- `P(d)` can return `highest_action = ACTION_BLOCK` (e.g. CHILD_PROTECTION, `domain_protocols.py:679`). In the gate, `_PROTOCOL_REQUIRED_KEYWORDS["BLOCK"] = []` (`output_gate.py:241`). The compliance check does `if not required_patterns: protocol_compliance[action] = True; continue` (`output_gate.py:613-616`). So a **BLOCK action is marked compliant and the response is forwarded.** Nothing blocks.
- For EMERGENCY: if `P(d)` flagged a chest-pain emergency but the LLM response lacks emergency keywords, the gate appends `PROTOCOL_MISSING_EMERGENCY` to `flags` (`output_gate.py:622-627`) and **still sends the response** (it is not `blocked`, and the emergency instruction is not injected).

This directly contradicts `output_gate.py:27`: *"P(d) can never be overridden — if P(d) said EMERGENCY, the gate enforces."* It detects, it does not enforce. For a healthcare emergency this is a real safety gap: the system can recognize an emergency and emit a response with no emergency guidance.

**Fix:** BLOCK must hard-block; missing required protocol keywords should either inject `combined_instructions` or block, not pass with a log line.

---

### C4 — The H scorer silently degrades to an uncalibrated backend

`aatif_semantic_scorer.py:441-452`: if Ollama is unavailable, the H scorer falls back to TF-IDF char-n-grams with only a `print("[warn]…")`. But:
- Every threshold in the system — gate θ=0.40, confidence cuts 0.45/0.30 (`semantic_scorer.py:455-457`), `UNKNOWN_TERRITORY_THRESHOLD=0.20` (`s_equation.py:409`) — was calibrated on **bge-m3 cosine distribution.** TF-IDF char-n-gram cosine has a completely different distribution (Arabic strings share many character n-grams, so similarities run high and flat). Confidence, unknown-territory, and the gate all mis-fire under the fallback.
- The fallback is **inconsistent across scorers**: the I and E scorers *raise* instead of falling back (`intent_scorer.py:185-187`, `emotion_scorer.py:159-161`). So `AATIFEngine.__init__` actually dies on the I scorer — but any code using `SemanticHarmScorer` alone gets silent, wrong scores.
- The held-out validation that proves the F1 numbers **skips entirely without Ollama** (`tests/test_held_out_validation.py:135`). So "670 passed" in a CI box with no bge-m3 does **not** mean the calibration is verified — it means the calibration tests didn't run.

For a safety system, a silent downgrade to an uncalibrated scoring backend is fail-unsafe. **The system should refuse to operate (or drop to an explicit, conservative hard-coded mode) when embeddings are unavailable**, not quietly switch math.

---

## High-Priority Issues

### H1 — Hysteresis first-turn fail-open
`HysteresisState` initializes `current_decision="EXECUTE"`, `turns_in_state=0` (`hysteresis.py:99-103`). On a brand-new conversation whose **first** message scores a borderline CLARIFY (S in 0.65–0.70), Rule 4 single-level escalation runs (`hysteresis.py:213`), and `_can_escalate` requires `S < 0.70−ε = 0.65` to leave EXECUTE (`hysteresis.py:292-295`). Since 0.65–0.70 is not `< 0.65`, the transition is **held → returns EXECUTE.** A genuine first-turn CLARIFY is suppressed into EXECUTE because the phantom initial state is EXECUTE. The initial state should be a sentinel ("unset") and the first real turn should pass the raw decision through untouched.

### H2 — Unbounded state, no eviction, no thread safety (every stateful component)
- `HysteresisController.states` (`hysteresis.py:150`)
- `AATIFIntentEngine._in_clarify_zone` (`intent_engine.py:289`)
- `AATIFConversationMemory._turns/_arcs/_dialects/_topics` (`conversation_memory.py:135-144`); note `EmotionalArc.states` appends forever (`conversation_memory.py:72-73`) — only `_turns` is capped, not the arc.
- `_load_persistent` reads **all** files into RAM at startup (`conversation_memory.py:442-475`).

Every one of these grows one entry per `conversation_id`/`session_id` forever, with no TTL/LRU, and is a plain dict mutated without a lock. In a long-running multi-conversation server this is both a memory leak and a data race. Add bounded eviction and locking (or document single-threaded/short-lived use explicitly).

### H3 — `" DAN "` jailbreak marker can never match
`s_equation.py:198` lists the marker `" DAN "` (uppercase) but matching is done against `text.lower()` (`s_equation.py:209`). A lowercased string can never contain uppercase `DAN`, so the classic DAN jailbreak is silently unguarded in the semantic engine. (More broadly, jailbreak detection here is substring matching on lowercased text — trivially evadable by spacing/obfuscation — and it's *duplicated and divergent* from the intent-engine's `OVERRIDE_*`/`CBRN_*` sets. Consolidate into one tested list.)

### H4 — The R equation is sigmoid-saturated; T/V/G signals are effectively inert
`r_equation.py:496-500`: `z = w₃T + w₄V + w₅G + w₆D` with all weights positive (1.0/1.5/0.8/2.0) and all signals in [0,1]. The minimum realistic `z` (most-formal healthcare case) is ≈1.5 and the typical case is ≈2.6, so `σ(z)` lands in **0.82–0.95 — always "casual" (>0.7).** The "formal/balanced/warm" bands (`r_equation.py:108-114`) are essentially unreachable; only the hard gate ceilings for healthcare/education (`r_equation.py:132-135`) ever move the band. The four perception signals barely affect the output. The equation needs a **negative bias/offset** to center its operating point near 0.5 so the signals actually use the range. (The docstring already concedes "Default weights (will be calibrated)" `r_equation.py:38` — this is the calibration that's missing.)

### H5 — Conversation memory's privacy claim is false in practice
Docstring: *"What does NOT get stored: Raw message text (privacy — we remember meaning, not words)"* (`conversation_memory.py:20-23`). But `add_turn` stores full `text` (`conversation_memory.py:167-171`), `get_context` returns `last_user_text`, `last_assistant_text`, and `recent_turns[...].text[:200]` (`conversation_memory.py:243-249, 331-334`), and `get_context_prompt` injects the raw last user message into the LLM prompt (`conversation_memory.py:332`). Only the on-disk `save()` strips text. The claim is false for RAM — which is exactly where the data is read and surfaced. Either stop storing raw text in session memory or correct the claim.

---

## Medium-Priority Issues

### M1 — `domain` is silently ignored in classic mode
`get_domain_theta` is consulted only in the gated path (`s_equation.py:552-553`). `compute_s_from_scores` (classic) ignores `domain` entirely, yet `compute()` accepts `domain` for both modes (`s_equation.py:651-657`). A caller passing `domain="healthcare"` in classic mode gets no θ effect, silently. This contradicts the loud-fail philosophy the same file applies to *unknown* domains (`s_equation.py:357-381`). Either honor domain in both modes or reject `domain` when `equation_mode="classic"`.

### M2 — Gated profile mismatch raises bare `KeyError`; `balanced_strict` is dead
`compute()` validates `equation_mode` (`s_equation.py:689-690`) but not `profile` against the mode. Passing `profile="creative"`/`"casual"`/`"safe_environment"` with `equation_mode="gated"` raises a bare `KeyError` at `GATED_PROFILES[profile]` (`s_equation.py:546`), not the friendly `ValueError` used elsewhere. The classic set has 5 profiles, the gated set 4, with only 2 names overlapping — and `balanced_strict` is never selected by `compute()` or `compute_all_profiles` (`s_equation.py:840`), so it's dead config. Add a guarded validation and reconcile the profile sets.

### M3 — Unknown-territory check is fail-open by default and ignores E
`s_equation.py:762-767` reads `h_result.get("max_similarity", 1.0)` / `i_result.get("max_similarity", 1.0)`. The default of **1.0** means "if the field is missing, treat as fully recognized" — i.e. disable the safety net on absence. It also only inspects H and I, not E, and only fires when the decision is already EXECUTE. The safe default for a missing similarity is `0.0` (treat as unrecognized → CLARIFY).

### M4 — In the shipped engine, `S` (softening_factor) is computed but never used for the decision
`AATIFIntentEngine.read` computes `S` (`intent_engine.py:367-374`), but `_determine_mode` (`intent_engine.py:738-746`) and `_decide` (`intent_engine.py:780-832`) branch on `harm`/`ambiguity`/`mode` only. `S` is returned in `IntentReading` and used downstream solely for firmness in the (unwired) response shaper. The "S/F/H equation" the system is named for is **vestigial in the path that actually runs.** Either feed S into the decision or stop advertising it as the deployed governance equation.

### M5 — Output gate's `passed` conflates "modified" with "failed"
`output_gate.py:453`: `reading.passed = len(reading.flags) == 0`. But many flags are benign cleanups — `PII_LEAK_CLEANED`, `RESPONSE_TRUNCATED`, `SANITIZED`, `IDENTITY_LEAK_FIXED`. A response that merely had a file path sanitized comes back `passed=False` though it's fine and not `blocked`. Any caller keying on `passed` will reject good responses. Separate hard-fail flags from cosmetic ones (the real signal is `blocked`).

### M6 — Repetition de-dup destroys formatting
`output_gate.py:676-701`: when any duplicate sentence is detected, the text is rebuilt as `". ".join(cleaned_sentences)` (`:695`), collapsing newlines, lists, and original punctuation. This mangles legitimately formatted output (code blocks, bullet lists, multi-paragraph answers) any time a sentence repeats.

### M7 — Pervasive duplication; no shared utilities
- `_OllamaBackend` is **copy-pasted in 4 files** (`semantic_scorer.py:387`, `intent_scorer.py:123`, `emotion_scorer.py:96`, plus the embedding/tfidf variants).
- Confidence thresholds 0.45/0.30 duplicated in all three scorers.
- **Two** forbidden-phrase lists that can drift: `response_shaper._ALWAYS_FORBIDDEN` (`response_shaper.py:125`) vs `output_gate._FORBIDDEN_PHRASES` (`output_gate.py:175`).
- Two `sigmoid`s, two Arabic-normalizers, two `_arabic_ratio`s, two dialect detectors (`intent_engine.py:433` vs `r_equation.py:166`).

A shared `aatif_embeddings.py` + `aatif_text.py` would remove ~300 lines and an entire class of drift bugs.

---

## Low-Priority / Polish

- **`EPSILON_H` is dead.** Defined and stored (`hysteresis.py:64,149`) but never read; the H-hold uses a hardcoded `H > 0.5` (`hysteresis.py:324`). Either wire it or delete it.
- **`_RESTRICTIVE_DECISIONS` is dead** (`domain_protocols.py:509`). The advertised invariant "P can only make things more cautious, never less" (`domain_protocols.py:19-22`) is true only by construction (P emits no decision); nothing enforces it and `s_decision` is stored but unused.
- **Timezone defaults disagree.** `TimeSense.read` defaults to `"US/Eastern"` (`time_sense.py:163`) while `intent_engine._get_time_context` hardcodes `"Asia/Riyadh"` (`intent_engine.py:576`). For an Arabic-first system the default should be consistent (and Gulf-aware).
- **`\bATF\b → عاطف`** (`output_gate.py:155`) will rewrite the US ATF agency inside legitimate text.
- **Library prints on init.** `AATIFEngine.__init__` prints status to stdout (`s_equation.py:640-649`). Use `logging`.
- **Dead NLP path.** `arabic_nlp_bridge.py` is absent, so `_HAS_NLP_BRIDGE=False` permanently and the trained-model sentiment/dialect enrichment (`intent_engine.py:318-349`) never runs. Either vendor the bridge or drop the branch.
- **`_check_governance_integrity` runs twice per read** (`intent_engine.py:361` and again at `:792`).
- **Dialect regex ladders overlap heavily** (qatari/emirati/kuwaiti/bahraini share `شلونك`/`شخبارك`/`اللحين`/`هالشكل`) and are order-dependent (`intent_engine.py:433-518`). Not safety-critical, but classification is effectively first-match-wins among near-identical sets.

---

## Security Posture (AI-safety-specific)

The recurring theme across the criticals/highs is **fail-open under degradation**, which for a safety system is the dangerous direction:

| Vector | Where | Effect |
|---|---|---|
| Embedding failure → `H=0` | `semantic_scorer.py:502-505` | "no harm recognized" reads as "safe" |
| Silent TF-IDF fallback | `semantic_scorer.py:441-452` | uncalibrated math, thresholds invalid |
| Unknown-territory default `1.0` | `s_equation.py:762-767` | missing similarity → "recognized/safe" |
| Hysteresis first-turn EXECUTE | `hysteresis.py:99-103` | first borderline CLARIFY → EXECUTE |
| Output gate not wired | C2 | "last guard" never runs on real output |
| P(d) BLOCK not enforced | `output_gate.py:241,613` | block action forwarded to user |
| Substring jailbreak detection | `s_equation.py:193`, `intent_engine.py:269` | trivially evadable; `" DAN "` never matches |

In the **shipped** path, the *only* hard safety stops are the regex CBRN/override gates in `AATIFIntentEngine` (`intent_engine.py:795-801`) — substring/regex, evadable — because the semantic gate, the gated equation, and the output gate are not in the path. That is a thin line for a system positioned as governance infrastructure.

---

## Things the code clearly *wants* but doesn't have

1. **An orchestrator** (`aatif_governor.py`?) that actually runs S→P→R→gate, injecting P's `combined_instructions`, R's style, and memory context, then gating the LLM output. Every interface is already shaped to plug in.
2. **Engine reconciliation** — one harm source of truth, not semantic-for-tests + regex-for-prod.
3. **A backend-health gate** — explicit conservative behavior when embeddings are down, instead of silent TF-IDF.
4. **Bounded, lockable state** for hysteresis and memory (TTL/LRU + locks), or an explicit single-threaded contract.
5. **Shared utility modules** for embeddings, text normalization, and the forbidden-phrase list.
6. **Centering/bias for R** so the style equation isn't pinned to "casual."

---

## What's good (so the fixes don't lose it)

- Anchor curation in `semantic_scorer.py` is excellent — the dialect-hyperbole, educational-"safe," and counter-harm anchor families show real understanding of the false-positive/false-negative tension, and the reasoning is documented inline.
- The γ+ hysteresis thermostat model is the right idea, and its test suite is thorough.
- `domain_protocols.py` and `output_gate.py` are clean, deterministic, and well-organized — they just need to be *called*.
- Defensive NaN/inf handling around the embedding matmul (`semantic_scorer.py:405-429`) is careful and correct.
- Documentation density is far above average; the *intent* of every design choice is recoverable.

The gap is not craftsmanship — each module is well-made. The gap is **integration and a single source of truth.** Resolve C1 and C2 and this becomes the system the docstrings already believe it is.
