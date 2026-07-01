# FN#070 — DeepSeek External Review
## Source: DeepSeek (Instant mode with Search, 33 web pages referenced)
## Date: 2026-06-30
## URL: https://chat.deepseek.com/a/chat/s/ffd63f85-1501-45cc-a601-bcf0ca61e5c5

---

# FN#070 — Possibility Space Preservation (PSP): Critical Review

## Executive Summary

FN#070 is a well-structured, thoughtfully designed module with strong test coverage and clear architectural boundaries. The Single Mind Law is respected—PSP correctly sits post-safety and never touches the S equation. However, the module has several critical issues that must be addressed before it is paper-ready for EACL 2027. Below is a systematic review across all five requested dimensions.

---

## 1. Bugs & Logic Errors

### 1.1 State Transitions: `next_psp_state()` Logic Gaps

The transition helper has at least **two missing transitions** that create unreachable or inconsistent states:

| Missing Transition | Problem |
|---|---|
| `DETECTED → DORMANT` | If a decision point is detected but the user immediately topic-shifts or goes quiet, the state should deactivate. Currently, the transition logic only handles `DETECTED → EXPLORING` and `Any → DORMANT` for topic shift—but **topic shift detection is not defined** in the transition helper signature. |
| `CLOSURE_REQUESTED → EXPLORING` | If a user requests closure ("قررلي") but then asks a follow-up question that re-opens the space ("بس وش رايك بالخيار الثالث؟"), the state should revert. No transition handles this. |

**Recommendation:** Add explicit edge cases:
```python
# DETECTED → DORMANT when topic_shift=True or consecutive_quiet >= threshold
# CLOSURE_REQUESTED → EXPLORING when user introduces new paths after requesting closure
```

### 1.2 `last_psp_turn_index` vs `last_decision_marker_turn_index` Ambiguity

The PSPContext stores both fields with **no documented distinction**. If a decision marker appears but PSP doesn't fire (e.g., objective suppression), which field updates? The implementation brief doesn't specify, creating potential off-by-one errors in deactivation counting.

**Recommendation:** Clarify semantics—`last_psp_turn_index` = last turn where PSP actively processed; `last_decision_marker_turn_index` = last turn where ANY decision marker appeared (even if suppressed).

### 1.3 "One quiet turn HOLDS state" Contradiction

The brief states: "One quiet turn HOLDS state; consecutive quiet turns trigger deactivation". But the deactivation policy says: "General domains: 3 consecutive quiet turns → deactivate". If one quiet turn holds and three trigger deactivation, **what happens on turn 2?** The state machine has no "DECAYING" state, so turn 2 is identical to turn 1—both "hold". This is a logic gap: there's no way to distinguish between "holding indefinitely" and "counting down".

**Recommendation:** Add a `DECAYING` substate or a `quiet_turns_accumulated` counter that increments on quiet turns and resets on any decision activity.

### 1.4 `user_requested_closure: bool` Never Reset

The context stores `user_requested_closure` as a boolean, but there's no documented mechanism to reset it to `False` after the closure is processed or the state transitions away from `CLOSURE_REQUESTED`. This creates a **sticky flag problem**—once set, it could incorrectly influence future turns.

**Recommendation:** Reset `user_requested_closure = False` on transition to `CLOSED` or `DORMANT`.

---

## 2. Design Weaknesses

### 2.1 State Enum Without Formal Guardrails (Acknowledged, But Insufficient)

The brief acknowledges: "State enum, not state machine; formal guards are v1.5". For a module that's supposed to be "paper-ready for EACL 2027", this is a significant weakness. A conference paper needs to demonstrate rigor, and an unguarded state enum with a helper function is **not a verifiable state machine**.

**Recommendation:** Implement a proper state machine with:
- Valid transition matrix (N×N boolean)
- Entry/exit actions
- Invariant checks (e.g., "can't be in EXPLORING with < 2 live_paths")

### 2.2 Objective Suppressor: Keyword-Based, Not Semantic

The two-axis scoring uses keyword-based objective markers. This is **brittle for Arabic**, where:
- "أرخص" (cheaper) could be objective (price comparison) or subjective (value judgment)
- "أفضل" (better) is highly context-dependent
- Negation flips meaning: "ليس أرخص" (not cheaper) vs "أرخص" (cheaper)

**Recommendation:** Move to a lightweight semantic classifier (e.g., fine-tuned AraBERT) for objective vs subjective detection, with the keyword list as a fallback.

### 2.3 Feature Flags OFF by Default Undermines Production Testing

The brief states: "Feature flags all OFF undermines testability in production". This is framed as a "known limitation," but it's a **design flaw**. If PSP is OFF by default, how will it ever be validated in real-world conditions? Staged rollout is sensible, but the flags should be ON in test environments with a clear path to production enablement.

**Recommendation:** Add a `PSP_DRY_RUN` mode that processes but doesn't apply changes, allowing observation without behavioral impact.

### 2.4 Bounded Alternatives (2-5): No Justification for Creative Domains

The brief notes: "2-5 range — should the ceiling be higher for creative domains?". This is a valid concern. In creative writing, brainstorming, or ideation tasks, 5 alternatives may be artificially constraining. The Schwartz paradox argument is about consumer choice, not creative exploration.

**Recommendation:** Make the bound domain-configurable via the `domain_profile` field, with creative domains allowing 7-10 paths.

### 2.5 Deactivation Turn Counts: 3 and 5 Are Educated Guesses

The brief acknowledges: "No cross-validation of deactivation turn counts (3 and 5 are educated guesses)". For a paper submission, educated guesses are not sufficient. Reviewers will ask: Why 3? Why 5? Why not 2 or 4?

**Recommendation:** Run an ablation study across different turn counts and report results. Alternatively, make it dynamic based on conversation length or domain.

---

## 3. Missing Edge Cases

### 3.1 Multi-Turn Decision Context with Intervening Non-Decision Turns

What happens if a user says: "ايش تشوف؟" (decision marker), then asks a factual question, then returns to the decision? The current state machine has no mechanism to preserve context across intervening non-decision turns. The `last_psp_turn_index` tracks the last PSP turn, but the state could decay to DORMANT during the factual interlude.

**Recommendation:** Add a context window or sticky decision flag that persists across N non-decision turns before decaying.

### 3.2 Simultaneous Multiple Decision Points

A user could have two active decision threads simultaneously: "Should I buy car A or B? Also, should I take the job in Dubai or Abu Dhabi?" The current PSPContext has a single `decision_topic` field and a single `live_paths` list—no support for parallel decisions.

**Recommendation:** Either (a) explicitly disallow parallel decisions (documented limitation) or (b) support a stack/queue of decision contexts.

### 3.3 Decision Point in Non-Arabic Text or Code-Switching

Arabic speakers frequently code-switch to English, French, or other languages. The marker set is Arabic-only. What happens when a user says: "Which one is better? ايش رأيك؟" — the English marker "which one is better" is missed.

**Recommendation:** Add support for code-switching detection and include common English/French decision markers that appear in Arabic text.

### 3.4 PSP in Multi-Turn with System Messages or Tool Calls

If the system inserts a message (e.g., "I'm processing your request...") or a tool call interrupts the conversation, does that count as a "quiet turn" for deactivation purposes? The brief doesn't specify.

**Recommendation:** Define which turn types count for deactivation (user turns only? all turns?).

### 3.5 Edge Case: User Says "خلاص" (Enough/Finished) But Doesn't Decide

"خلاص" can mean "enough, stop talking" OR "I've decided." The current marker set treats it as a decision marker, but it's ambiguous. Misclassification could prematurely close a decision space.

**Recommendation:** Add **contextual disambiguation**—if "خلاص" appears without a clear choice, treat it as "closure requested" rather than "decided."

---

## 4. Arabic NLP Concerns

### 4.1 Dialect Coverage Is Incomplete

The marker set covers Gulf, Egyptian, and Levantine dialects, but Arabic has **dozens of dialects** with significant variation. Missing dialects include:

- **Maghrebi** (Moroccan, Algerian, Tunisian): "شنو" vs "ايش", "شكون" vs "منو"
- **Sudanese**: unique expressions
- **Hassaniya** (Mauritania)

**Recommendation:** Expand the marker set to include Maghrebi variants, or explicitly scope the system to the covered dialects and document the limitation.

### 4.2 Dialect Identification Is Non-Trivial

Arabic dialect identification is a challenging NLP task. The current approach assumes the marker list is sufficient, but:
- Dialects are not standardized and vary widely
- Multi-label classification is often more appropriate than single-label
- Model calibration varies significantly across dialects

**Recommendation:** Consider integrating a lightweight dialect identification model (e.g., fine-tuned AraBERT) to dynamically adjust the marker set based on detected dialect.

### 4.3 Diacritics and Orthographic Variation

Arabic text in real-world settings (chat, social media) often omits diacritics and uses non-standard orthography. For example:
- "ايش" vs "إيش" vs "اىش"
- "احترت" vs "إحترت" vs "احترت"

The marker list likely uses normalized forms, but user input may not be normalized.

**Recommendation:** Apply Arabic text normalization (remove diacritics, normalize hamza, etc.) before marker matching, or use fuzzy matching.

### 4.4 Arabic Morphological Complexity

Arabic is highly morphologically rich. A single root can generate dozens of forms. The marker list uses specific forms (e.g., "احترت"), but users might use:
- "محتر" (confused, colloquial)
- "حيران" (confused, different root)
- "مش عارف" (I don't know, Egyptian)

**Recommendation:** Use root-based or stem-based matching (e.g., Farasa stemmer) rather than exact string matching.

### 4.5 Cultural Context of Decision-Making

Arabic decision-making often involves collective or consultative language:
- "استشرت" (I consulted)
- "شور" (consultation)
- "نصيحة" (advice)

These are not decision markers per se but indicate decision-relevant context. The current system might miss these signals.

**Recommendation:** Add a **consultation marker** category that influences PSP state (e.g., moves toward EXPLORING) but doesn't trigger a decision point directly.

---

## 5. Paper-Readiness for EACL 2027

### 5.1 Strengths (What Works Well)

| Aspect | Assessment |
|---|---|
| Architectural clarity | Single Mind Law is respected. PSP is correctly positioned post-safety. |
| Test coverage | 111 PSP tests, 2636 total passing — strong empirical validation. |
| Feature flags | Staged rollout approach is sensible, though flags OFF is a concern. |
| State lifecycle | Six states are a reasonable starting point for v1. |
| Domain awareness | Different deactivation thresholds for high-stakes domains. |
| Dialect awareness | Expanded marker set covering multiple dialects is a strength. |

### 5.2 Critical Gaps for EACL 2027

| Gap | Severity | Fix Required |
|---|---|---|
| No formal state machine | HIGH | Implement guarded transitions with invariant checks. |
| Keyword-based objective suppression | HIGH | Move to semantic classification (AraBERT or similar). |
| No dialect identification | MEDIUM | Integrate dialect ID or explicitly scope to covered dialects. |
| No ablation of hyperparameters | HIGH | Run ablation on turn counts, thresholds, and bounds. |
| Feature flags OFF | MEDIUM | Add dry-run mode; show PSP would have triggered. |
| No user study | HIGH | EACL 2027 theme is "The Human in Language"—need human evaluation. |
| No baseline comparison | HIGH | Compare against non-PSP or alternative approaches. |

### 5.3 EACL 2027 Theme Alignment

The conference theme is "The Human in Language". FN#070 aligns well with this theme—it's about preserving human decision space, which is fundamentally human-centric. However, the paper needs to explicitly connect PSP to this theme and demonstrate human-centric outcomes.

**Recommendation:** Add a user study where participants rate:
- Perceived agency with vs. without PSP
- Satisfaction with decision support
- Whether they felt the AI "collapsed" their options prematurely

### 5.4 Paper Structure Suggestion

For EACL 2027, the paper should include:
1. **Introduction:** Position PSP within AATIF, connect to "The Human in Language" theme
2. **Related Work:** Cover informational preservation, Fathom, Arabic safety benchmarks
3. **Methodology:** Formal state machine definition, transition matrix, Arabic marker derivation
4. **Experiments:**
   - Ablation on hyperparameters
   - Dialect coverage evaluation
   - Human evaluation (agency, satisfaction)
   - Comparison to baseline (no PSP, simple keyword-based PSP)
5. **Discussion:** Limitations, future work, ethical considerations
6. **Conclusion**

### 5.5 Specific Reviewer Questions to Anticipate

| Likely Reviewer Question | Suggested Response |
|---|---|
| "Why 3 and 5 turns?" | Ablation results showing optimal trade-off. |
| "How do you handle code-switching?" | Document as limitation or implement solution. |
| "What about Maghrebi dialects?" | Scope the paper to Levantine/Gulf/Egyptian or expand. |
| "Is this just a heuristic?" | Show formal state machine + empirical validation. |
| "Where's the human evaluation?" | Include user study results. |

---

## Summary of Action Items

| Priority | Action | Rationale |
|---|---|---|
| **P0** | Implement formal state machine with guards | Paper rigor |
| **P0** | Run hyperparameter ablation | Answer "why these numbers?" |
| **P0** | Conduct user study | EACL 2027 theme alignment |
| **P1** | Move objective suppression to semantic classification | Arabic NLP robustness |
| **P1** | Add dialect identification or explicit scoping | Academic honesty |
| **P2** | Add dry-run mode for feature flags | Production validation |
| **P2** | Handle code-switching and multi-decision contexts | Edge case completeness |
| **P3** | Expand dialect coverage to Maghrebi | Broader applicability |

---

## Final Verdict

**Conditionally Acceptable with Major Revisions.** FN#070 is a well-conceived, architecturally sound module with excellent test coverage. The Single Mind Law is respected, the Arabic dialect awareness is a genuine contribution, and the state lifecycle is a reasonable v1. However, the module is **not yet paper-ready** for EACL 2027 due to: (1) lack of a formal state machine, (2) keyword-based objective suppression, (3) no hyperparameter ablation, and (4) no human evaluation. Addressing the P0 items above would make this a strong submission aligned with the conference theme.
