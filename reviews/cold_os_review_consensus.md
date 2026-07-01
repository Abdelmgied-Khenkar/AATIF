# COLD-OS (FN#072) — 3-Model External Review Consensus

**Module:** `engine/aatif_cold_os.py` — Tri-Engine Decision Protocol
**Reviewers:** ChatGPT-4o, Gemini 2.5, Grok-3
**Date:** 2026-07-01
**Status:** P0 fixes implemented; P1/P2 tracked as TODOs

---

## Consensus Summary

All three external models agreed that the Tri-Engine Decision Protocol is a
**novel and architecturally sound** contribution to governed AI response framing.
The separation of Ideal/Real/COLD voices before speech — rather than after — is
a genuine design innovation not found in Stanovich's dual-process model or
Levine et al.'s ethical theory splits.

However, all three models independently identified the same set of critical
implementation issues that would cause significant false-positive activation and
inter-module conflicts in production. These are catalogued below as P0 (all 3
agree, critical), P1 (2+ agree, should fix), and P2 (nice to have).

---

## P0 Issues — All 3 Models Agree (Critical)

### P0-A: Context-Gated Activation (One-Marker Auto-Activation)

| Flagged by | Severity |
|---|---|
| ChatGPT, Gemini, Grok | P0 |

**Problem:** `_ACTIVATION_THRESHOLD = 0.15` but a single marker produces
strength 0.20. This means ANY single keyword in GENERAL context auto-activates
COLD-OS. Words like "right" in "copyright", "data" in any technical text, "risk"
in "asterisk" would trigger full tri-engine analysis.

**Fix implemented:** Raised `_ACTIVATION_THRESHOLD` to 0.25, requiring 2+
markers for activation in GENERAL context. Non-GENERAL contexts (where at least
one context marker was detected) activate regardless of voice strength.

### P0-B: PRACTICAL Enum Unreachable

| Flagged by | Severity |
|---|---|
| ChatGPT, Gemini, Grok | P0 |

**Problem:** `DecisionContext.PRACTICAL` exists in the enum but has ZERO markers
mapped to it in `_CONTEXT_MARKER_MAP`. The value can never be detected.

**Fix implemented:** Added `CONTEXT_PRACTICAL_EN` and `CONTEXT_PRACTICAL_AR`
marker sets with appropriate practical-decision markers ("steps to take",
"practical", "action plan", "best approach", "عملي", "خطوات", etc.) and
registered them in `_CONTEXT_MARKER_MAP`.

### P0-C: COLD-OS to LBH Conflict (No Reconciliation)

| Flagged by | Severity |
|---|---|
| ChatGPT, Gemini, Grok | P0 |

**Problem:** When COLD-OS recommends `ideal_leads_real_softens`, the resulting
text may trigger LBH (Lecturing/Belittling/Hectoring) deficit detection in
`aatif_lbh_detector.py`. No mechanism exists to reconcile these contradictory
signals.

**Fix implemented:** Added `lbh_interaction_note` field to `ColdOSReading`. When
strategy is `IDEAL_LEADS_REAL_SOFTENS`, the note warns: "ideal_leads strategy
may trigger LBH deficit detection — response shaper should balance." Established
B5 hierarchy: LBH output constraints override COLD-OS framing tone on conflict.

### P0-D: ESCALATE Strategy Problematic

| Flagged by | Severity |
|---|---|
| ChatGPT, Gemini (P0); Grok (in inter-module contracts) | P0 |

**Problem:** `ESCALATE` implies safety escalation, violating B-prime spirit.
Directly references PSP (FN#070), creating tight cross-module coupling that
contradicts the isolation contract.

**Fix implemented:** Renamed `ESCALATE` to `DEFER_TO_CLARIFICATION` in the
`FramingStrategy` enum. Removed direct PSP reference from recommendations. The
strategy is now purely observational: "insufficient signal for confident framing
recommendation — present multiple perspectives, defer to user clarification."

### P0-E: Substring Matching False Positives

| Flagged by | Severity |
|---|---|
| ChatGPT, Gemini, Grok | P0 |

**Problem:** Marker detection uses `marker in text_lower` which finds "right" in
"copyright", "duty" in "duty-free", "data" in "database", "rate" in
"accelerate". Massive false positive risk for English markers.

**Fix implemented:** All English markers now use pre-compiled word-boundary regex
(`\b` + `re.escape(marker)` + `\b`). Patterns are compiled at module load time
for zero per-call overhead. Arabic markers retain substring matching because
Arabic prefixed conjunctions (و، ف، ب، ل) attach without spaces, making `\b`
inappropriate for Arabic text.

### P0-F: Arabic Marker Refinement

| Flagged by | Severity |
|---|---|
| ChatGPT, Gemini, Grok | P0 |

**Problem:** (a) "بس" (but/just) is extremely common in Arabic dialect — causes
massive false positives. (b) Insufficient dialect coverage. (c) No policy for
religious terms (حلال/حرام) — these are everyday vocabulary, not always ethical
dilemmas. (d) No Arabic text normalization for variant spellings.

**Fix implemented:**
- **Marker categories:** Split into STRONG (always counted), WEAK (require 2+
  other markers), and CONDITIONAL (require first-person context).
- **"بس" → WEAK:** Only counted when 2+ other Real markers are already present.
- **حلال/حرام → CONDITIONAL:** Only counted as Ideal/Moral markers when
  first-person decision context is detected (e.g., "هل يجوز لي" not just
  "أكل حلال").
- **Arabic normalization:** Added `_normalize_arabic()` function that strips
  tashkeel (diacritical marks), normalizes alef variants (أ إ آ ٱ → ا), and
  removes tatweel (kashida ـ). Applied to both input text and marker sets.

### P0-G: Isolation Marker Missing

| Flagged by | Severity |
|---|---|
| ChatGPT, Gemini, Grok | P0 |

**Problem:** UCN and LBH both have `ISOLATION_MARKER` and isolation fields on
their readings. COLD-OS lacks this, breaking the B-prime pattern consistency.

**Fix implemented:** Added `ISOLATION_MARKER = "B5_ADVISORY_NOT_FOR_SAFETY"`,
`ISOLATION_TARGETS = frozenset({"S_equation", "authority_doctrine",
"boot_sequence"})` to `ColdOSEngine`. Added `isolation_marker` field to
`ColdOSReading`. Added `ISOLATION_CONTRACT` docstring section to module header.

---

## P1 Issues — 2+ Models Agree (Should Fix)

### P1-1: Arbitrary Thresholds (ChatGPT, Gemini, Grok)

All numeric constants (0.20, 0.25, 0.40, 0.60, 0.75, 0.30) lack empirical
calibration. **Action:** Added `CALIBRATION_NEEDED` comments to all threshold
constants. Future work: calibrate against labeled decision-context corpus.

### P1-2: Missing Temporal/Urgency Dimension (Gemini, Grok)

The three voices don't capture urgency or time pressure. **Action:** Added TODO
comment. Design extension — not a bug in current scope.

### P1-3: Ad-hoc Strength Curve (ChatGPT, Gemini)

Step function breakpoints (1→0.20, 2→0.40, ...) need empirical justification.
**Action:** Added `CALIBRATION_NEEDED` comments. Consider sigmoid or log curve in
future iterations.

### P1-4: "بس" and Common Arabic Words (ChatGPT, Grok)

Addressed as part of P0-F (WEAK marker category).

---

## P2 Issues — Nice to Have

### P2-1: Long Text Windowing (Gemini)

No chunking for very long texts. Marker scanning is O(n*m) where n=text length,
m=markers. **Action:** Added TODO comment. For texts > 5000 chars, consider
windowed scanning.

### P2-2: Orthogonality Not Proven (Grok)

Voices may overlap conceptually (Ideal and Real can both invoke "duty to
family"). Theoretical concern, not a code bug. **Action:** Noted. Empirical
validation needed with labeled corpus.

---

## Implementation Verification

All P0 fixes implemented in `engine/aatif_cold_os.py`. Test suite updated in
`tests/test_cold_os.py` with new test classes covering:
- `TestSubstringFalsePositives` (P0-E)
- `TestPracticalContext` (P0-B)
- `TestIsolationMarker` (P0-G)
- `TestLBHInteractionNote` (P0-C)
- `TestDeferToClarification` (P0-D)
- `TestArabicNormalization` (P0-F)
- `TestWeakMarkers` (P0-F)
- `TestConditionalMarkers` (P0-F)
- `TestActivationThreshold` (P0-A)

Full pytest suite passes with zero regressions.

---

*License: CC BY 4.0 | AATIF OS — Architected Adaptive Thoughts & Intelligence Frameworks*
