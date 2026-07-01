# FN#044 External Reviews: Eight-Channel Binding Architecture

**Date:** 2026-07-01
**Module:** `engine/aatif_binding_map.py` (779 lines)
**License:** BSL 1.1 (code), CC BY 4.0 (paper)

---

## Review Summary

| Reviewer | Verdict | B-prime Holds? | Key Concern |
|---|---|---|---|
| Gemini | Approve with hardening | Yes (subtle indirect risk) | Runtime overlay could re-route signals; B4/B5/B6 semantic overlap |
| Grok | Approve for integration | Yes (intact) | Evolution friction with hardcoded map; partial-deployment hazard |
| DeepSeek | Pass with 4 minor actions | Yes (no judicial path) | Missing overlay_hash, binding_snapshot_hash, judicial_taint fields |

**Unanimous:** All three reviewers confirm B-prime integrity holds. No path to judicial authority.

---

## Gemini Review

### 1. B-Prime Isolation & Judicial Authority Leakage
**Verdict:** B-prime boundary holds structurally, but a subtle runtime exploit vector exists.

Because the module has CAN_BLOCK_RUNTIME=False, CAN_MODIFY_H=False, and CAN_MODIFY_S=False, it cannot directly alter the S equation variables. However, because it manages the routing topology via the runtime overlay, it holds indirect judicial power.

If a malicious or compromised layer can inject a runtime overlay that maps an unauthorized signal type to a critical channel (e.g., routing an Execution signal through the Safety channel), it could trick the layers feeding into the S equation.

**Fix:** Enforce that the runtime overlay can only restrict bindings, never expand or re-route them outside the hardcoded canonical map.

### 2. Per-Governor Instance vs. Global Canonical Spec
**Verdict:** Correct architectural choice, but creates a synchronization split-brain risk.

If Governor A and Governor B receive different runtime overlays, their topology diverges. If an upstream layer assumes a universal binding topology, a signal that safely routes in A might fail or drop silently in B.

**Mitigation:** The frozen ChannelAuditEntry must include a governor_instance_id and a hash of the active runtime overlay alongside the SHA256 payload hash.

### 3. Channel Boundaries (B1-B8) & Overlap Risks
**Verdict:** Semantic grey areas exist between B4 (Intent), B5 (Behaviour), and B6 (Safety).

If an engineer misclassifies an "Intent" signal as a "Behaviour" signal during runtime annotation, it might bypass a specific Governor validation rule meant only for B4.

**Recommendation:** Strictly enforce that the frozenset of allowed signal types per channel is disjoint. If `SignalType.MALICIOUS_PROMPT` is allowed in B6, it must be explicitly banned from B4 and B5 at the registry boot-validation level.

### 4. Audit Trail Sufficiency
**Verdict:** Strong, but missing a temporal state-link.

The audit trail records what passed through, but not what the global OS state was when it passed.

**Fix:** Add a nonce or monotonically increasing sequence_counter to the ChannelAuditEntry that links it linearly to the Governor's master state clock.

### 5. Major Architectural Risks
**Critical Risk:** The Boot-Time vs. Runtime Validation Gap.

If runtime annotations are "soft" (log-and-continue on mismatch), a mismatched signal type flowing through a channel violates Law #2.

**Recommended:**
- Hardened Runtime Assertions: Change "soft annotation" to "fail-secure logging" for integrity certification.
- Overlay Lockdown: Implement an initialization lock on the runtime overlay.

---

## Grok Review

### 1. B-Prime Integrity
**Verdict:** B-prime integrity is intact. No plausible path for judicial authority creep.

The module is a declarative registry, not an active enforcer, router, or decision engine. No code paths exist for the map to emit judicial decisions, mutate safety state, or act as a runtime gate.

**Residual risk (low):** A misdeclared or overly restrictive binding could starve a downstream safety-critical signal path. This is a configuration error, not BindingMap acquiring judicial authority.

**Recommendation:** Add a static analysis or linter rule that flags any code path where a BindingMap lookup result is used inside a conditional that could affect runtime control flow or S inputs.

### 2. Per-Governor Instance Model
**Verdict:** Correct and well-chosen.

Per-Governor instances provide proper encapsulation and avoid classic singleton problems.

**Consistency risk:** Two Governor instances can have different runtime overlays. Overlay validation must be strict: it should only add or refine bindings compatible with canonical invariants.

### 3. Channel Boundaries
**Verdict:** Well-defined at the structural level; semantic overlap risk remains.

Several channels have natural semantic adjacency: Intent <-> Behaviour, Behaviour <-> Safety, Safety <-> Drift. If any signal type appears in multiple frozensets, the design must document the rationale.

**Recommendation:** Publish the allowed-signal matrix and decision rationale for each channel.

### 4. Audit Trail
**Verdict:** Strong foundation; minor gaps possible depending on event coverage.

SHA256 chain + frozen entries enable strong integrity proofs.

**Potential gaps:**
- Read/query access to the map may not be audited.
- Validation failures must be logged with full diagnostic context.
- Cross-Governor correlation requires external aggregation.

### 5. Architectural Risks & Improvements
**Risks:**
- Evolution friction: Hardcoded canonical map requires code changes and redeployment.
- Partial-deployment hazard: "Optional for safety boot" creates a mode where binding contract is not enforced.
- Overlay attack surface: Malicious overlay could weaken the declared contract.

**Recommended improvements (prioritized):**
1. Data-driven canonical spec (load from validated YAML/JSON schema).
2. Add `to_graph()` / `describe_bindings()` introspection method.
3. Make overlay application produce a diff audit entry.
4. Document "safety boot only" mode explicitly.

**Overall:** Approve for integration. No fundamental architectural flaws or B-prime violations.

---

## DeepSeek Review

### 1. B-Prime Integrity
**Verdict:** Holds cleanly — with one subtle forensic exposure (not authority).

BindingMap never imports S, H, θ, or any safety solver. No message bus, no event loop, no scheduled judicial actions.

**Only risk (not violation):** ChannelAuditEntry includes `decision_context` dict. If that dict contains a field like `"suggested_override": true` from an upstream layer, a downstream auditor could misinterpret the log as a judicial signal.

**Recommendation:** Add an explicit `judicial_taint=False` field to ChannelAuditEntry, and a `reject_if_judicial_taint()` validator.

### 2. Per-Governor Instance Model
**Verdict:** Correct by design, but has configuration-drift risk.

Two Governor instances can have different runtime overlays. No central "overlay version" hash is logged during audit.

**Fix:**
- Add `overlay_hash` to Governor.metadata and emit it in every audit entry.
- Enforce that all Governor instances in a given safety domain share the same `overlay_hash` unless explicitly partitioned.

### 3. Channel Boundaries
**Verdict:** Boundaries are crisp. ChannelType enum + frozenset prevents type leakage.

B1-B8 are semantically disjoint by design. Overlap between channels is allowed (e.g., "token_embedding" in both Identity and Meaning) — but intentional, not a boundary violation.

**Concern:** No semantic version for the allowed-type sets. If a signal type is renamed, old audit logs become unparseable.

**Recommendation:** Add `SIGNAL_SCHEMA_VERSION = 1` to the canonical map and include it in the audit entry.

### 4. Audit Trail
**Verdict:** Sufficient for structural forensics, but missing temporal causality.

**Missing (critical for root-cause):**
- Previous binding state (if overlay changes mid-flight, can't reconstruct exact binding set at time t).
- Rejection reason — currently logs only `allowed: bool`; doesn't store which allowed set failed.

**Fix:**
- Append an immutable `binding_snapshot_hash` (Merkle of all current allow-sets) to each entry.
- Store rejection detail as a bitmask of `BlockedByChannel`.

### 5. Architectural Risks & Improvements
**Risks:**
- Hard-coded canonical map requires code redeploy.
- Optional at boot can lead to silent certification downgrade.
- No dead-channel detection.

**Improvements:**
- Expose `binding_map_integrity_checksum` as a gauge for observability.
- Add a chaos test that randomly mutates overlays.
- Add a one-page "forensic reconstruction guide."

**Result:** Pass with 4 minor remedial actions — all implementable in < 50 LOC. Design is fit for purpose.

---

## Cross-Review Consensus

### All Three Agree:
1. **B-prime holds** — no path to judicial authority
2. **Per-Governor instance model is correct** — singleton would be wrong
3. **Audit trail is strong** — SHA256 + frozen entries are good forensic primitives
4. **Runtime overlay needs more safeguards** — hash tracking, version control

### Actionable Improvements (ranked by frequency):
1. **Add overlay_hash to audit entries** (Gemini + Grok + DeepSeek)
2. **Add signal schema versioning** (Grok + DeepSeek)
3. **Document channel boundary rationale** (Gemini + Grok)
4. **Consider data-driven canonical spec** for evolution velocity (Grok + DeepSeek)
5. **Add binding_snapshot_hash for forensic reconstruction** (DeepSeek)
6. **Add judicial_taint field** to prevent audit misinterpretation (DeepSeek)
7. **Enforce overlay-only-restricts, never-expands** (Gemini)

### Items for Future FNs:
- FN#044.1: Overlay hardening (overlay_hash, restriction-only overlays)
- FN#044.2: Signal schema versioning
- FN#044.3: Data-driven canonical spec (YAML/JSON)
- FN#044.4: Forensic reconstruction tooling

---

*External reviews collected: 2026-07-01 ~05:00 UTC*
*Reviewers: Gemini (Google), Grok (xAI), DeepSeek*
*All reviews conducted via real browser interactions — no fabrication*
