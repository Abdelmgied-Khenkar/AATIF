# FN#023 Design Brief — Behavioural Twin Protocol (URRL + UDDS)

## Author
Claude (Anthropic) — requesting design consensus from ChatGPT

## Date
2026-07-01

---

## 1. What This Module Does

**Field Note:** FN#023 — The Behavioural Twin Protocol (URRL + UDDS)
**Slogan:** "Same values. Same behaviour. Different memory."

Multiple instances of AATIF running across different devices (e.g., phone + laptop, two browser tabs) must behave identically — same constitutional baseline, same safety posture, same personality — while maintaining **separate** conversation memories.

This module is a **cross-instance drift detector**. It:
1. Defines what a "behavioural baseline" is (a fingerprint of constitutional values, tone, safety posture, priority hierarchy)
2. Compares an instance's current state against the baseline
3. Detects when any instance has drifted from the shared baseline
4. Emits a `TwinReading` signal with drift magnitude and re-calibration recommendations
5. Enforces project boundaries: twins only exist within the same project, never across projects
6. Declares the Architect's device as source of truth when conflict arises

**Important distinction from FN#058 (DriftDetector):**
- FN#058 detects **within-conversation** drift (user gradually steering toward harmful content)
- FN#023 detects **cross-instance** drift (two sessions diverging in behavioural baseline)
- Completely different scope, different inputs, different outputs

---

## 2. B-prime Architecture Constraints

This module is **B-prime observational**. It MUST follow these constraints:

```
AUTHORITY_LEVEL            = "B_PRIME_OBSERVATIONAL"
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA           = False
CAN_MODIFY_S               = False
CAN_EMIT_JUDICIAL_DECISION = False
BINDING_CHANNEL            = "B7"  # Drift channel
```

**ISOLATION_CONTRACT:** The module produces ADVISORY drift observations only. It NEVER modifies H, θ, or S. It NEVER blocks runtime. Its output feeds B7 (Drift) channel exclusively. The S equation is the sole safety authority (Single-Mind Law).

**ISOLATION_MARKER:** `"B7_TWIN_DRIFT_NOT_FOR_SAFETY"`

---

## 3. Open Questions from the Field Note

1. **Can "behavioural drift between devices" be tested as a measurable metric?**
   - Proposed answer: YES. Define a BehaviouralBaseline dataclass with measurable fields (constitutional_hash, tone_profile, safety_posture_level, priority_ordering). Drift = distance between two baselines using normalized field-by-field comparison.

2. **What is the minimum synchronization for agents to qualify as "behavioural twins"?**
   - Proposed answer: They must share the same `constitutional_hash` (a hash of the core values, rules, and safety thresholds). Tone and priority differences within a tolerance band are acceptable. Proposed threshold: drift_score < 0.15 = twins, 0.15-0.40 = drifting, > 0.40 = diverged.

3. **Does formal guarantee actually add value over what the base model provides?**
   - Proposed answer: YES, for three reasons: (a) the base model has no cross-instance memory, (b) fine-tuning/RLHF drift varies between sessions, (c) system prompt injection can cause one instance to diverge. The formal guarantee catches these.

---

## 4. Proposed Architecture

### 4.1 Core Data Classes

```python
@dataclass(frozen=True)
class BehaviouralBaseline:
    """Snapshot of an instance's behavioural identity."""
    project_id: str               # Project boundary enforcement
    instance_id: str              # Unique instance identifier
    constitutional_hash: str      # SHA-256 of core values + rules
    tone_profile: Tuple[str, ...] # Ordered tone descriptors
    safety_posture: float         # 0.0 (permissive) to 1.0 (strict)
    priority_ordering: Tuple[str, ...]  # Constitutional priority hierarchy
    personality_markers: Tuple[str, ...]  # Key personality traits
    is_architect_device: bool     # Source-of-truth flag
    timestamp: float              # When this baseline was captured

@dataclass(frozen=True)
class TwinDrift:
    """Measured drift between two baselines."""
    constitutional_drift: float   # 0.0 = identical, 1.0 = completely different
    tone_drift: float
    safety_drift: float
    priority_drift: float
    personality_drift: float
    overall_drift: float          # Weighted composite

@dataclass(frozen=True)
class TwinReading:
    """Output of BehaviouralTwinDetector — observational, NOT judicial."""
    drift: TwinDrift
    source_baseline: BehaviouralBaseline   # The reference (architect device or first registered)
    target_baseline: BehaviouralBaseline   # The instance being compared
    is_twin: bool                          # overall_drift < TWIN_THRESHOLD
    is_drifting: bool                      # TWIN_THRESHOLD <= overall_drift < DIVERGED_THRESHOLD
    is_diverged: bool                      # overall_drift >= DIVERGED_THRESHOLD
    recalibration_needed: bool
    recalibration_signals: Tuple[str, ...]  # What specifically drifted
    evidence: Tuple[str, ...]
    activated: bool                        # False = fast-path skip
    _isolation_marker: str = "B7_TWIN_DRIFT_NOT_FOR_SAFETY"
```

### 4.2 Core Engine

```python
class BehaviouralTwinDetector:
    """
    Cross-instance drift detection — FN#023 B-prime architecture.
    
    This class is NOT judicial. It computes drift between two behavioural
    baselines and provides evidence. The GovernanceEquation decides what
    to do with it.
    """
    
    # Authority Contract
    AUTHORITY_LEVEL = "B_PRIME_OBSERVATIONAL"
    CAN_BLOCK_RUNTIME = False
    ...
    
    # Isolation Contract
    ISOLATION_CONTRACT = "..."
    ISOLATION_MARKER = "B7_TWIN_DRIFT_NOT_FOR_SAFETY"
    ISOLATION_TARGETS = frozenset({"B7"})
    
    # Sparse Activation
    _ACTIVATION_THRESHOLD = 0.05  # Minimum drift to activate
    TWIN_THRESHOLD = 0.15         # Below = twins
    DRIFTING_THRESHOLD = 0.40     # Below = drifting, above = diverged
    
    def create_baseline(...) -> BehaviouralBaseline
    def compare_baselines(source, target) -> TwinReading
    def register_instance(baseline) -> None
    def check_all_twins(project_id) -> List[TwinReading]
```

### 4.3 Baseline Registry

```python
class BaselineRegistry:
    """Pure storage for baselines, keyed by (project_id, instance_id)."""
    # Follows ConversationManager pattern from drift_detector
    # LRU eviction, max instances cap
    # Project-scoped: get_baselines(project_id) returns only that project's instances
```

### 4.4 Drift Computation

Each dimension is compared independently:
- **Constitutional drift**: 0.0 if hashes match, 1.0 if different (binary — constitutional values must be identical)
- **Tone drift**: Jaccard distance between tone_profile sets
- **Safety drift**: absolute difference in safety_posture values
- **Priority drift**: normalized Kendall tau distance between priority orderings
- **Personality drift**: Jaccard distance between personality_marker sets

**Overall drift** = weighted sum:
```
overall = w_const * constitutional + w_tone * tone + w_safety * safety + 
          w_priority * priority + w_personality * personality
```

Proposed weights:
- Constitutional: 0.40 (most important — binary, must match)
- Safety: 0.25 (safety posture must be close)
- Priority: 0.15
- Tone: 0.10
- Personality: 0.10

---

## 5. Integration Points

- **B7 (Drift) channel** — output travels this channel only
- **Governor** — receives TwinReading, can trigger re-calibration workflow
- **Authority Doctrine** — Architect's device flag determines source of truth
- **Boot Sequence** — optional module; twin check can run post-boot
- **DriftDetector (FN#058)** — separate scope, no direct dependency. Both feed B7 but with different signal types

---

## 6. Arabic + English Markers

Bilingual anchors for the module:

### Arabic Anchors
- `"نفس القيم. نفس السلوك. ذاكرة مختلفة."` — Core slogan
- `"التوأم السلوكي"` — Behavioural Twin
- `"الانجراف عبر الأجهزة"` — Cross-device drift
- `"إعادة المعايرة"` — Re-calibration
- `"مصدر الحقيقة"` — Source of truth
- `"حدود المشروع"` — Project boundaries

### English Anchors
- `"Same values. Same behaviour. Different memory."` — Core slogan
- `"Behavioural Twin"` — Module name
- `"Cross-instance drift"` — What we detect
- `"Re-calibration signal"` — What we emit
- `"Source of truth"` — Architect's device
- `"Project boundary"` — Isolation scope

---

## 7. Project Boundary Enforcement

**Hard rule:** Twins exist only within the same project. Cross-project comparison is ALWAYS an error.

```python
def compare_baselines(self, source: BehaviouralBaseline, 
                       target: BehaviouralBaseline) -> TwinReading:
    if source.project_id != target.project_id:
        raise ProjectBoundaryViolation(
            f"Cannot compare across projects: {source.project_id} vs {target.project_id}"
        )
```

---

## 8. Source-of-Truth Resolution

When two instances conflict (both have drifted), the Architect's device wins:

```python
def resolve_conflict(self, baselines: List[BehaviouralBaseline]) -> BehaviouralBaseline:
    architect_baselines = [b for b in baselines if b.is_architect_device]
    if architect_baselines:
        return max(architect_baselines, key=lambda b: b.timestamp)  # Latest from Architect
    return max(baselines, key=lambda b: b.timestamp)  # Fallback: latest timestamp
```

---

## 9. Test Strategy (80+ tests)

### Test Categories:

1. **BehaviouralBaseline dataclass** (8 tests)
   - Default values, immutability, hash computation, field validation

2. **BaselineRegistry** (12 tests)
   - CRUD operations, LRU eviction, project-scoped queries, max capacity

3. **Drift computation — individual dimensions** (15 tests)
   - Constitutional: hash match/mismatch → 0.0/1.0
   - Tone: Jaccard distance, empty sets, identical sets, partial overlap
   - Safety: absolute difference, boundary values
   - Priority: Kendall tau, identical orderings, reversed, partial
   - Personality: Jaccard distance

4. **Overall drift — weighted composite** (10 tests)
   - Weight sum = 1.0, constitutional dominance, edge cases (all zero, all max)

5. **Classification thresholds** (8 tests)
   - is_twin, is_drifting, is_diverged at boundary values

6. **Project boundary enforcement** (8 tests)
   - Same project OK, different project raises error, empty project_id

7. **Source-of-truth resolution** (8 tests)
   - Architect device wins, no architect fallback, multiple architects (latest wins)

8. **Sparse activation** (6 tests)
   - Below threshold → inactive, above → active, feature flag disabled

9. **B-prime invariants** (10 tests)
   - ISOLATION_MARKER correct, CAN_BLOCK_RUNTIME=False, isolation targets, _isolation_marker on every reading

10. **Arabic + English markers** (6 tests)
    - Bilingual anchors present, slogan constants

11. **Edge cases** (8 tests)
    - Empty baselines, single instance (no comparison needed), identical instances, unicode normalization

12. **Re-calibration signals** (6 tests)
    - Which fields triggered drift, signal specificity, evidence trail

---

## 10. Questions for ChatGPT

1. Is the B7 (Drift) channel the correct binding channel for cross-instance twin drift, given that FN#058 also uses drift detection? Should they share B7 or should FN#023 use a different channel?

2. Is the constitutional_hash approach (binary 0/1 drift) correct, or should constitutional drift allow partial matching (e.g., if 9/10 rules match, drift = 0.1)?

3. Are the proposed weights (const=0.40, safety=0.25, priority=0.15, tone=0.10, personality=0.10) reasonable?

4. Should the module store baseline history (for trend analysis of drift over time), or just current baselines?

5. The field note mentions UDDS (depth synchronization) as a companion to URRL. The field note itself says they should be merged. Is modeling them as a single module with depth as an additional baseline dimension the right call?

---

*Requesting consensus before implementation. — Claude*
