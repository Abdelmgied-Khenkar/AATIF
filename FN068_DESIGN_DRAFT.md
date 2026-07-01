# FN#068 Scientific Discovery Mode — Design Document

## Field Note
**Title:** The Cognitive Sovereignty Principle (السيادة المعرفية)
**Slogan:** "Hypothesis, not truth. Exploration, not conclusion."
فرضية لا حقيقة. استكشاف لا خاتمة.

## Architecture: B-prime (B')

```
AUTHORITY_LEVEL            = B_PRIME_OBSERVATIONAL
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA           = False
CAN_MODIFY_S               = False
CAN_EMIT_JUDICIAL_DECISION = False
BINDING_CHANNEL            = B5 (Behaviour)
```

**Single Mind Law:** Only GovernanceEquation (S equation) makes safety decisions.
FN#068 is STYLISTIC/EPISTEMIC — it governs how knowledge claims are framed,
NOT whether a request is allowed.

## What the Module Does

1. **Detects exploration context** from user input (EN + AR markers)
2. **Classifies output mode**: EXPLORATION vs STANDARD
3. **Provides hypothesis-tagging guidance** for response shaper
4. **Detects cross-discipline linking** (physics + biology + philosophy etc.)
5. **Scans draft output for truth-claiming violations** (observational only)
6. **Asserts cognitive sovereignty**: The Architect alone decides

## Enums

```python
class ExplorationMode(Enum):
    STANDARD = "standard"        # no exploration detected, fast-path skip
    EXPLORATION = "exploration"  # user is exploring/hypothesizing/brainstorming

class HypothesisStatus(Enum):
    NOT_APPLICABLE = "not_applicable"       # not in exploration mode
    TAGGED = "tagged"                       # output should be tagged as hypothesis
    TRUTH_CLAIM_DETECTED = "truth_claim_detected"  # violation found in output

class CrossDisciplineScope(Enum):
    NONE = "none"      # single discipline or no academic context
    DUAL = "dual"      # two disciplines linked
    MULTI = "multi"    # three or more disciplines linked

class TruthClaimType(Enum):
    DISCOVERY_CLAIM = "discovery_claim"      # "I've discovered..."
    VALIDATION_CLAIM = "validation_claim"    # "This confirms/validates..."
    TRUTH_ASSERTION = "truth_assertion"      # "The truth is..." / "Certainly..."
    CONCLUSION_CLAIM = "conclusion_claim"    # "We can conclude..."
```

## Frozen Dataclasses

```python
@dataclass(frozen=True)
class ExplorationSignal:
    strength: float                  # 0.0 – 1.0
    markers_found: Tuple[str, ...]
    language: str                    # "en", "ar", "mixed"

@dataclass(frozen=True)
class TruthClaimViolation:
    claim_type: TruthClaimType
    claim_text: str                  # the offending snippet
    confidence: float                # 0.0 – 1.0
    suggested_reframe: str           # "Consider: ..." instead of "This proves..."

@dataclass(frozen=True)
class SovereigntyAssertion:
    disclaimer_en: str  # "This is a possible pathway worth examination — nothing more."
    disclaimer_ar: str  # "هذا مسار محتمل يستحق الدراسة — لا أكثر."
    architect_authority_en: str  # "The Architect alone decides..."
    architect_authority_ar: str  # "المهندس وحده يقرر..."

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
    activated: bool                 # False => fast-path skip
    _isolation_marker: str = "B5_ADVISORY_NOT_FOR_SAFETY"
```

## Main Class: ScientificDiscoveryEngine

### Authority Contract (class-level constants)
Same as all B-prime modules.

### ISOLATION_CONTRACT
```
ScientificDiscoveryEngine produces ADVISORY epistemic guidance only.
It NEVER modifies H, θ, or S. It NEVER blocks runtime.
Its output feeds B5 (Behaviour) channel exclusively.
The S equation is the sole safety authority (Single-Mind Law).
```

### Feature Flags
```python
SDM_ENABLED = True           # master switch
SDM_OUTPUT_SCAN_ENABLED = True  # enable truth-claim scanning of draft output
```

### Sparse Activation
- `_MIN_TEXT_LENGTH = 15`
- `_ACTIVATION_THRESHOLD = 0.25` (same as ColdOS)
- Skip when no exploration signals detected (fast-path returns inactive reading)

### Public Methods

1. `analyze(text, *, domain="general") -> ScientificDiscoveryReading`
   - Primary entry point for USER input
   - Detects exploration mode from markers
   - Classifies cross-discipline scope
   - Returns reading with hypothesis-tagging guidance

2. `scan_output(text, exploration_reading) -> ScientificDiscoveryReading`
   - Secondary entry point for DRAFT OUTPUT validation
   - Only runs when exploration_mode == EXPLORATION
   - Scans for truth-claiming language
   - Returns updated reading with any violations found

3. `audit_hash(reading) -> str` (static)
   - SHA-256 digest for audit trails

### Marker Sets (bilingual EN + AR)

**Exploration markers (what the user says when exploring):**
- EN: "what if", "could it be", "is it possible", "imagine", "hypothesis",
  "I wonder", "explore", "brainstorm", "suppose", "theoretically",
  "what would happen", "possible connection", "might relate",
  "unconventional", "alternative explanation", "gap in", "contradiction",
  "let me think", "cross-pollinate", "interdisciplinary"
- AR: "ماذا لو", "هل يمكن", "تخيل", "فرضية", "أتساءل",
  "استكشاف", "عصف ذهني", "افترض", "لو قلنا", "نظرياً",
  "ربط بين", "علاقة بين", "تقاطع", "غير تقليدي", "زاوية مختلفة",
  "فجوة", "تناقض", "خلني أفكر", "بين التخصصات"

**Truth-claiming markers (violations in system output):**
- EN: "I've discovered", "this proves", "this confirms", "the truth is",
  "definitely proves", "we can conclude that", "this validates",
  "it is confirmed", "the evidence proves", "without doubt"
- AR: "اكتشفت", "هذا يثبت", "هذا يؤكد", "الحقيقة هي",
  "بالتأكيد يثبت", "نستنتج أن", "تأكد أن", "بلا شك"

**Discipline markers (for cross-discipline detection):**
- Sciences: physics, biology, chemistry, mathematics, neuroscience, astronomy
- Humanities: philosophy, theology, linguistics, history, sociology
- Arts: music, art, architecture, literature
- Applied: engineering, computer science, medicine, economics, psychology
- Arabic equivalents for each

### Recommendations (generated based on mode)

When EXPLORATION mode:
- "Tag all generated content as HYPOTHESIS — never as established fact."
- "Allow free cross-discipline linking — no allegiance to established schools."
- "Append sovereignty assertion: final authority rests with the Architect."
- "Generate multiple pathways (10-50) without commitment to any single one."
- "Identify gaps and contradictions explicitly — these are features, not bugs."

When TRUTH_CLAIM_DETECTED:
- "VIOLATION: Output claims discovery/truth. Reframe as hypothesis."
- "Replace '[claim]' with 'This is a possible pathway worth examination.'"

### Pipeline Position
- After S(d), before prompt composition (same as ColdOS)
- Reads: user message, domain
- Produces: ScientificDiscoveryReading with exploration guidance

### What is ALLOWED
- Generate multiple hypotheses (10-50) without commitment
- Link distant disciplines (physics + biology + philosophy + music)
- Suggest unconventional experiments
- Identify gaps and contradictions

### What is NEVER ALLOWED
- Declaring a discovery
- Validating a conclusion
- Claiming truth

### The One Rule
"This is a possible pathway worth examination — nothing more."
هذا مسار محتمل يستحق الدراسة — لا أكثر.

### Supreme Authority
The Architect alone decides what gets developed and what gets rejected.
المهندس وحده يقرر ما يُطوَّر وما يُرفض.
