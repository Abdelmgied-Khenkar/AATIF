# FN#068 External Review — Perplexity
**Date:** 2026-07-01 22:51 AST
**Model:** Perplexity (free tier)
**Tab:** Scientific Discovery Module Review

---

## VERDICT: PASS WITH CONSTRAINTS

## CONFIDENCE: MEDIUM

---

## Summary

The module is broadly aligned with B-prime observational requirements and the stated constitutional invariants, but several areas need tightening, especially around epistemic framing, Arabic morphology coverage, and safety risk coupling to harm classes.

---

## Detailed Evaluation

### A. Architecture (Criteria 1–5)

1. **B-prime status / authority surface**
   - Declared authority: `B_PRIME_OBSERVATIONAL`, with `CAN_BLOCK_RUNTIME=False`, `CAN_EMIT_JUDICIAL_DECISION=False`. This is appropriate for a non-binding, advisory observational module rather than an enforcement or judicial component.
   - Binding channel: `BINDING_CHANNEL=B5` with `ISOLATION_MARKER=B5_ADVISORY_NOT_FOR_SAFETY` matches a "single-mind, advisory only" pattern and keeps this module out of the H/θ/S modification path and out of safety binding channels (e.g., B3/B4).

2. **Non-modification of H, θ, S**
   - Explicit flags `CAN_MODIFY_H=False`, `CAN_MODIFY_THETA=False`, `CAN_MODIFY_S=False` correctly encode the invariant "never modifies H/theta/S."
   - The risk is not the flags but any indirect writes (logging hooks, metric propagation) that could later be wired into H/θ/S updates. The description does not mention any side-effects beyond observations, so the module appears architecturally clean, but this should be enforced via interface-level contracts (e.g., no outbound calls to governance update APIs).

3. **Single Mind Law and isolation contract**
   - Single Mind Law (no parallel, competing judicial authorities) is respected by explicitly stating that `GovernanceEquation` is sole judicial authority and giving this module no judicial decision capability.
   - `ISOLATION_MARKER=B5_ADVISORY_NOT_FOR_SAFETY` is good, but slightly ambiguous: "not for safety" could be misinterpreted by downstream code as "irrelevant to safety" instead of "cannot be used as a binding safety override." A stricter isolation contract (e.g., "MUST_NOT_BIND_SAFETY_OR_HARM_CLASSES") would reduce misuse risk.

4. **Authority constants and channels**
   - Authority constants correctly model a read-only, observational authority that cannot block runtime and cannot issue binding judgments, which aligns with B-prime observational semantics.
   - B5 channel exclusivity is stated, but ensuring exclusivity requires guards in the routing layer so that this module's outputs never appear on B3/B4 or any H/θ/S-modifying channel. The description doesn't confirm that such guards exist, only that the binding channel constant is B5.

**Architecture verdict:** Meets B-prime observational constraints at the constant/config level; needs clearer runtime routing guarantees and stricter isolation wording.

---

### B. Epistemic (Criteria 6–10)

5. **Hypothesis vs truth distinction**
   - The presence of `HypothesisStatus` and `TruthClaimType` enums, and a constitutional invariant that "hypotheses labeled" and "no speculative-as-fact," is a strong epistemic structure.
   - However, nothing in the description guarantees that *all* outputs are forced through these enums (e.g., raw strings bypassing the labeling pipeline). The design is promising but depends on usage discipline; there is latent risk if other code paths generate text without attaching `HypothesisStatus`.

6. **Truth-claim scanner and violations**
   - `TruthClaimViolation` dataclass plus 14 EN and 11 AR truth-claim markers suggests a dedicated truth-claim scanner that can flag violations of epistemic rules like speculative-as-fact and missing evidence.
   - Marker coverage is decent but may be sparse for complex scientific claims (e.g., nuanced statistical language). With a sparse threshold of 0.25 and minimum 15 chars, brief but harmful truth claims might slip by. This is acceptable for an observational module, but should be called out as a constraint.

7. **Reframe templates non-prescriptive**
   - The invariants emphasize "hypotheses labeled" and "falsification paths provided," which is consistent with reframing statements as conditional, exploratory rather than prescriptive.
   - Without seeing template structure, one risk is that reframe logic might suggest actions or "discoveries" (e.g., "you should test X now"), which would violate the non-prescriptive requirement for B-prime observation. This should be explicitly constrained in code comments and tests.

8. **Prevents claiming discoveries**
   - The module is called `aatif_scientific_discovery.py`, which is semantically loaded and may encourage downstream misuse (e.g., treating outputs as discoveries).
   - The invariants "prevents claiming discoveries" and "no speculative-as-fact" are stated, but there is still naming-driven risk. Renaming to something like `aatif_scientific_observation.py` would better align with B-prime's prohibition on declaring discoveries.

9. **Sovereignty preserved**
   - `SovereigntyAssertion` dataclass and "sovereignty preserved" invariant indicate explicit tracking of epistemic sovereignty (e.g., not overriding domain experts, not usurping other constitutional components).
   - The risk is subtle: an observational module that assigns high `epistemic_risk` could be used as de facto veto without being judicial. Stronger documentation should clarify that sovereignty assertions are descriptive, not prescriptive, and cannot enforce decisions.

**Epistemic verdict:** Solid scaffolding for hypothesis vs truth, but depends heavily on routing and naming discipline. Discovery claims are structurally discouraged but not fully disarmed by module naming.

---

### C. Bilingual (Criteria 11–14)

10. **Arabic normalization**
    - Description mentions Arabic normalization using NFD, Mn strip, alef normalization, and tatweel removal. This matches common normalization practices for robust token matching in Arabic.
    - NFD + Mn strip is Unicode-level normalization, which can interact oddly with some Arabic diacritics and compatibility characters; careful review is needed to ensure no safety-relevant semantics are lost (e.g., religious terms, proper names) in the safety/epistemic scanning context.

11. **Affix and morphological patterns**
    - Prefix/suffix morphological matching for Arabic suggests awareness of rich inflectional patterns (e.g., proclitics, attached pronouns).
    - With only 25 AR exploration markers and 11 AR truth-claim markers, coverage across morphological realizations and dialectal forms is likely incomplete, especially for modern scientific and technical vocabulary. This is acceptable for an initial module but should be labelled as partial coverage.

12. **English word boundaries**
    - English markers (30 exploration, 14 truth-claim) presumably rely on whitespace and punctuation word boundaries, which is standard and generally reliable for English scientific prose.
    - Potential edge cases include hyphenated compounds, abbreviations, and domain-specific jargon; without explicit word-boundary tests, false negatives are likely but manageable for an advisory-only module.

13. **Marker coverage sufficiency**
    - 55+ bilingual markers across EN and AR indicates a deliberate effort at dual-language epistemic and exploratory detection.
    - For a global "scientific discovery" module, this is still a relatively small marker set; specialized domains, emerging terminology, and non-standard phrasing will be under-detected. This should be documented as a known limitation to avoid overtrust.

**Bilingual verdict:** Implementation direction is correct but coverage in Arabic (and domain-specific English) is limited; this is acceptable for B-prime observation if explicitly documented as partial.

---

### D. Safety (Criteria 15–18)

14. **Cannot lower harm classification**
    - One of the eight constitutional invariants explicitly states "never lowers harm," which aligns with monotone safety principles where observational components cannot downgrade risk assessments.
    - The module exposes `epistemic_risk` and `safety_bypass_risk` metrics, which suggests it can signal increased risk but should never be used to justify harm class reduction. Guardrails must exist at integration points so these metrics cannot be interpreted as "safe enough to downgrade."

15. **Cannot widen unsafe detail**
    - Invariant "no unsafe detail widening" is clearly stated, aligning with non-amplification rules for sensitive content.
    - However, this module does bilingual exploration of scientific discovery, which could touch on sensitive technical details (e.g., dual-use research). Without explicit detail redaction logic, there is a risk that "observation" could still surface more detail than is safe, even if harm classes are not lowered.

16. **Safety bypass detector**
    - `safety_bypass_risk` metric aims to capture attempts to route around safety systems (e.g., phrasing or multi-lingual obfuscation), which is well-aligned with modern governance architectures.
    - The sparse activation threshold (0.25) and minimum text length (15 chars) may cause short, high-risk bypass patterns to be under-detected (e.g., short prompts in AR or abbreviations). This is a notable constraint.

17. **Epistemic risk assessment**
    - `epistemic_risk` metric provides a quantitative lens on how risky a given text is in terms of epistemic violations (e.g., speculative claims, unsupported discoveries).
    - Strength curve with diminishing returns capped at 1.0 and requirement that weak markers be corroborated by ≥2 strong markers helps avoid over-triggering but can also underweight rare yet significant patterns. This is reasonable for advisory use but should not be repurposed for hard safety enforcement.

**Safety verdict:** Conceptually sound for a non-binding, observational module, but there are risks around short-text under-detection and potential indirect widening of unsafe detail.

---

### E. Code Quality (Criteria 19–24)

18. **Frozen dataclasses immutability**
    - Four frozen dataclasses (`ExplorationSignal`, `TruthClaimViolation`, `SovereigntyAssertion`, `ScientificDiscoveryReading`) enforce immutability at the object level, which is excellent for governance logs and reproducible audits.
    - `_isolation_marker` in `ScientificDiscoveryReading` helps keep each reading contextually tagged, further supporting robust data lineage and isolation.

19. **Strength curve appropriateness**
    - Diminishing returns capped at 1.0 is a reasonable design: additional markers increase confidence but never push risk scores beyond a bounded scale.
    - For B-prime observation, this curve is appropriate; it avoids runaway risk inflation that could effectively act as a de facto veto. However, there should be documentation explaining how scores map (or do not map) to any decision thresholds elsewhere.

20. **Sparse threshold 0.25**
    - Sparse activation threshold 0.25 and minimum 15 chars are plausible defaults to avoid noise on very short inputs.
    - For bilingual safety and epistemic detection, this threshold is slightly aggressive; high-risk short prompts may be treated as "sparse" and therefore under-analyzed. The value is defensible but should be configurable and explicitly tested across languages.

21. **Weak markers corroboration**
    - Design choice that weak markers require ≥2 strong corroborations before influencing risk scores is good for precision, reducing false positives.
    - The downside is recall loss in niche scientific areas where strong markers may not yet exist; this is acceptable for observational use but should be flagged as a limitation when interpreting metrics.

22. **Audit hash completeness**
    - SHA-256 audit hash suggests that outputs or configurations are hashed for later verification, aligning with cryptographic governance best practices.
    - "Audit hash complete" depends on including all relevant fields (authority constants, invariants, marker lists, thresholds, version IDs). The description states a hash but not its scope; this is a potential gap if some configuration is left out.

23. **Feature flags functionality**
    - Presence of feature flags (implied by the module design and tests) is crucial for safely rolling out new markers, risk metrics, or thresholds without destabilizing runtime behavior.
    - No details are given on flag granularity (per language, per domain, per risk metric). Coarse flags can lead to all-or-nothing changes; finer granularity is preferable.

**Code quality verdict:** Generally strong, with immutable dataclasses and reasonable scoring design; audit hashing scope and sparse threshold configurability should be clarified.

---

### F. Tests (Criteria 25–28)

24. **Test coverage**
    - 140 tests in 24 classes, running in ~0.20s with zero regressions, indicates a well-built test suite with good breadth and fast feedback.
    - The number of tests relative to module complexity suggests at least moderate method-level coverage; however, we don't know exact coverage percentages (e.g., branch or condition coverage).

25. **Edge cases**
    - Given bilingual markers, normalization, and sparse activation logic, the presence of 24 test classes strongly implies specialization for edge cases (short texts, mixed scripts, diacritics, boundary conditions around thresholds).
    - Still, short high-risk AR prompts and rare scientific phrasing should be explicitly tested; the description doesn't guarantee that these particular edge cases are covered.

26. **Constitutional invariants tests**
    - Eight invariants (H/θ/S non-modification, harm monotonicity, hypothesis labeling, no speculative-as-fact, missing evidence disclosure, falsification paths, no unsafe detail widening, GovernanceEquation as sole judicial authority) form a clear checklist that can be turned into invariant tests.
    - The description does not explicitly state that each invariant has dedicated tests, only that the overall suite has zero regressions. This is a gap: invariants should have explicit, named tests to guard against future refactors.

27. **Integration testing**
    - 24 test classes and a runtime of 0.20s suggest at least basic integration tests (e.g., end-to-end from text → markers → risk metrics → reading object).
    - For governance components, integration tests must also include channel and isolation behavior (e.g., ensuring outputs never touch H/θ/S modification paths). The description doesn't confirm that such routing integration tests exist.

**Tests verdict:** Good general coverage; needs explicit invariant and routing tests to fully guarantee constitutional behavior.

---

## CRITICAL ISSUES:

1. **Potential misuse as de facto judicial or safety authority.**
   While authority flags disallow modification of H/θ/S and judicial decisions, nothing guarantees downstream systems will not treat high `epistemic_risk` or `safety_bypass_risk` scores as binding vetoes, which would violate the Single Mind Law and "GovernanceEquation is sole judicial authority."

2. **Module naming vs epistemic role ("scientific discovery").**
   The filename `aatif_scientific_discovery.py` and descriptor "scientific discovery" are misaligned with a B-prime observational role that must not claim discoveries or produce prescriptive outputs. This increases the risk of semantic drift toward discovery claims.

3. **Sparse threshold and short-text under-detection.**
   Sparse activation threshold 0.25 with min 15 chars can under-detect short high-risk prompts (especially in Arabic), weakening both safety bypass detection and epistemic risk assessment.

4. **Incomplete assurance on constitutional invariant testing.**
   The existence of eight invariants is clear, but there's no explicit confirmation that each is enforced via dedicated tests or runtime assertions, leaving room for future regressions in refactors.

---

## RECOMMENDATIONS:

1. **Strengthen isolation and routing guarantees.**
   - Add explicit runtime guards so this module's outputs cannot be wired into H/θ/S modification or judicial decision paths, even indirectly.
   - Document clearly that `epistemic_risk` and `safety_bypass_risk` are advisory metrics and cannot be used as binding decisions.

2. **Rename and re-document module role.**
   - Rename `aatif_scientific_discovery.py` to something like `aatif_scientific_observation.py` or `aatif_epistemic_monitor.py` to avoid encouraging discovery-style semantics.
   - Update docstrings to emphasize: no claims of discovery, no prescriptive guidance, strictly observational and epistemic diagnostics.

3. **Expand bilingual markers and adjust thresholds.**
   - Increase Arabic marker coverage, especially for modern scientific vocabulary and common safety-relevant patterns.
   - Consider lowering or making configurable the sparse threshold and minimum text length, with separate tuning per language.

4. **Explicit invariant and routing tests.**
   - Add named tests for each of the eight constitutional invariants plus channel isolation behavior.
   - Include tests that ensure no path from this module can alter H, θ, S, or produce judicial decisions, even after future extensions.

5. **Audit hash scope documentation.**
   - Clearly enumerate which configuration elements are included in the SHA-256 audit hash (markers, thresholds, enums, invariants, version).
   - Add tests that fail if new fields are added without being covered by the audit hash.

---

**Reasoning:** The architectural and invariant descriptions are strong and consistent with modern constitutional AI governance frameworks, but lack of direct visibility into implementation details and test bodies prevents high confidence.
