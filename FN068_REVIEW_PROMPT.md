# FN#068 External Review Prompt — 3-Model Consensus

> Send this EXACT prompt to THREE different LLMs (GPT-4, Gemini, Llama).
> Collect all three verdicts. Do NOT simulate or role-play the reviews.

---

## Instructions to Reviewer

You are reviewing a **B-prime observational module** for the AATIF OS constitutional AI governance framework. Your review must be honest and critical — not polite.

Review the code below against these criteria:

### A. Architecture Compliance

1. Is this module truly B-prime? Does it **NEVER** modify H, θ, S, or emit judicial decisions?
2. Does it respect the Single Mind Law (only GovernanceEquation makes safety decisions)?
3. Does the ISOLATION_CONTRACT match the actual behavior?
4. Are the class-level authority constants correct and consistent?
5. Does it feed B5 (Behaviour channel) exclusively?

### B. Epistemic Correctness

6. Does the module correctly distinguish HYPOTHESIS from TRUTH?
7. Does the truth-claim scanner catch the major violation patterns?
8. Are the reframe templates appropriate and non-prescriptive?
9. Does it prevent the system from claiming discoveries?
10. Does the sovereignty assertion preserve architect authority?

### C. Bilingual Implementation

11. Is Arabic normalization correct (alef variants, diacritics, tatweel)?
12. Do the Arabic affix patterns (prefix/suffix) cover common morphological forms?
13. Are the English word-boundary patterns correct?
14. Is marker coverage sufficient for both languages?

### D. Safety Invariants

15. Can this module EVER lower a harm classification? (Must be: NO)
16. Can this module EVER widen unsafe procedural detail? (Must be: NO)
17. Does the safety_bypass_risk detector catch procedural requests in exploration context?
18. Does the epistemic_risk assessment flag hallucination-prone conditions?

### E. Code Quality

19. Are frozen dataclasses truly immutable?
20. Is the diminishing-returns strength curve appropriate?
21. Is the sparse activation threshold (0.25) reasonable?
22. Are weak markers properly corroborated?
23. Is the audit hash deterministic and complete?
24. Are feature flags functional (SDM_ENABLED, SDM_OUTPUT_SCAN_ENABLED)?

### F. Test Coverage

25. Do the 140 tests cover all public methods?
26. Are edge cases tested (empty input, very long input, emoji, special chars)?
27. Are constitutional invariants directly tested?
28. Is the full pipeline (analyze → scan_output) integration-tested?

### Verdict Format

```
VERDICT: [PASS | PASS WITH CONSTRAINTS | FAIL]
CRITICAL ISSUES: [list or "none"]
RECOMMENDATIONS: [list]
CONFIDENCE: [HIGH | MEDIUM | LOW]
```

---

## Code Under Review

### engine/aatif_scientific_discovery.py

```python
"""
aatif_scientific_discovery.py — Scientific Discovery Mode (السيادة المعرفية)
Field Note #068: The Cognitive Sovereignty Principle

Slogan: "Hypothesis, not truth.  Exploration, not conclusion."
        فرضية لا حقيقة.  استكشاف لا خاتمة.

The One Rule:
    "This is a possible pathway worth examination — nothing more."
    هذا مسار محتمل يستحق الدراسة — لا أكثر.

This module is B-prime **observational**: it detects when the user is
engaged in scientific or exploratory reasoning, then provides epistemic
guidance for the response shaper — hypothesis tagging, cross-discipline
linking, truth-claim scanning, and cognitive sovereignty assertions.

It does NOT make safety decisions — that is the S equation's exclusive
jurisdiction.  It does NOT decide whether a request is allowed.
It governs *how knowledge claims are framed*, not *whether* they proceed.

Pipeline position:  after S(d), before prompt composition.
Reads:   user message, domain.
Produces: ScientificDiscoveryReading with exploration guidance.

Novel contribution (FN#068):
    First B-prime module that governs the epistemic shape of exploratory
    reasoning — ensuring hypotheses are tagged as hypotheses, discoveries
    are never claimed, and cross-discipline linking is unrestricted while
    truth-claiming is prohibited.

Constitutional Invariants
-------------------------
Invariant 1: FN#068 never modifies H, θ, S, H_eff, or safety verdicts.
Invariant 2: Scientific framing never lowers harm classification.
Invariant 3: Hypotheses must be labeled as hypotheses.
Invariant 4: Speculative claims must not be presented as established fact.
Invariant 5: When evidence is missing, the module must say so.
Invariant 6: At least one falsification path should be provided when
             a hypothesis is proposed.
Invariant 7: Discovery mode may widen explanation space, but may not
             widen unsafe procedural detail.
Invariant 8: The GovernanceEquation remains the only judicial authority.

Authority Contract
------------------
AUTHORITY_LEVEL            = B_PRIME_OBSERVATIONAL
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA           = False
CAN_MODIFY_S               = False
CAN_EMIT_JUDICIAL_DECISION = False
BINDING_CHANNEL            = B5 (Behaviour)

License: BSL-1.1 (code) | CC BY 4.0 (field note)
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ExplorationMode(Enum):
    STANDARD    = "standard"
    EXPLORATION = "exploration"

class HypothesisStatus(Enum):
    NOT_APPLICABLE       = "not_applicable"
    TAGGED               = "tagged"
    TRUTH_CLAIM_DETECTED = "truth_claim_detected"

class CrossDisciplineScope(Enum):
    NONE  = "none"
    DUAL  = "dual"
    MULTI = "multi"

class TruthClaimType(Enum):
    DISCOVERY_CLAIM  = "discovery_claim"
    VALIDATION_CLAIM = "validation_claim"
    TRUTH_ASSERTION  = "truth_assertion"
    CONCLUSION_CLAIM = "conclusion_claim"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dataclasses (all frozen)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class ExplorationSignal:
    strength: float
    markers_found: Tuple[str, ...]
    language: str

@dataclass(frozen=True)
class TruthClaimViolation:
    claim_type: TruthClaimType
    claim_text: str
    confidence: float
    suggested_reframe: str

@dataclass(frozen=True)
class SovereigntyAssertion:
    disclaimer_en: str
    disclaimer_ar: str
    architect_authority_en: str
    architect_authority_ar: str

@dataclass(frozen=True)
class ScientificDiscoveryReading:
    exploration_mode: ExplorationMode
    exploration_signal: ExplorationSignal
    hypothesis_status: HypothesisStatus
    cross_discipline_scope: CrossDisciplineScope
    disciplines_detected: Tuple[str, ...]
    truth_claim_violations: Tuple[TruthClaimViolation, ...]
    sovereignty: SovereigntyAssertion
    recommendations: Tuple[str, ...]
    evidence: Tuple[str, ...]
    activated: bool
    epistemic_risk: float
    safety_bypass_risk: float
    requires_falsification_tests: bool
    requires_evidence_tiers: bool
    requires_uncertainty_label: bool
    requires_source_check: bool
    _isolation_marker: str = "B5_ADVISORY_NOT_FOR_SAFETY"
```

### Key Implementation Details

- **Authority Contract:** B_PRIME_OBSERVATIONAL, CAN_BLOCK_RUNTIME=False, CAN_MODIFY_H/θ/S=False, CAN_EMIT_JUDICIAL_DECISION=False
- **Sparse Activation:** _MIN_TEXT_LENGTH=15, _ACTIVATION_THRESHOLD=0.25
- **Markers:** 30+ EN exploration markers, 25+ AR exploration markers, 14 EN truth-claim markers, 11 AR truth-claim markers, 20 discipline categories with bilingual markers
- **Weak Markers:** "model", "imagine" — require corroboration by ≥2 strong markers
- **Strength Curve:** 0→0.0, 1→0.20, 2→0.40, 3→0.60, 4-5→0.75, 6+→0.75+0.05*(n-5), cap 1.0
- **Feature Flags:** SDM_ENABLED (master), SDM_OUTPUT_SCAN_ENABLED (truth-claim scan)
- **Risk Assessment:** epistemic_risk (hallucination-as-discovery), safety_bypass_risk (science-as-bypass)
- **Arabic Normalization:** NFD decompose → strip Mn category → alef variants → tatweel
- **Arabic Matching:** Prefix-aware (ال/و/وال/بال/فال/ف/ب/ك/ل/لل) + suffix-aware (ي/ك/ه/ها/هم/هن/نا/كم/كن/ين/ون/ات/ة/تي/ته/تها)

### Test Results

```
140 passed in 0.20s
Zero regressions in full suite (33 pre-existing failures from sklearn dependency — unrelated)
```

### Test Categories (24 test classes)

1. TestAuthorityContract (10 tests)
2. TestEnums (12 tests)
3. TestDataclassImmutability (5 tests)
4. TestFastPath (8 tests)
5. TestExplorationEN (10 tests)
6. TestExplorationAR (7 tests)
7. TestExplorationMixed (1 test)
8. TestWeakMarkers (3 tests)
9. TestStrengthCurve (4 tests)
10. TestCrossDiscipline (6 tests)
11. TestTruthClaimScan (11 tests)
12. TestEpistemicRisk (4 tests)
13. TestSafetyBypassRisk (4 tests)
14. TestRecommendations (7 tests)
15. TestSovereignty (5 tests)
16. TestAuditHash (4 tests)
17. TestFeatureFlags (2 tests)
18. TestEvidenceTrail (5 tests)
19. TestRequiresFlags (4 tests)
20. TestMarkerSets (7 tests)
21. TestArabicNormalization (5 tests)
22. TestIntegration (3 tests)
23. TestEdgeCases (7 tests)
24. TestConstitutionalInvariants (6 tests)
