# FN#044 Design Brief: Eight-Channel Binding Architecture

**Date:** 2026-07-01
**Architect:** Abdulmjeed Ibrahim Khenkar
**Co-builder:** Claude (Anthropic)
**License:** BSL 1.1 (code), CC BY 4.0 (paper)

---

## 1. What We're Building

A **Binding Map** module (`engine/aatif_binding_map.py`) that defines 8 typed communication channels (B1-B8) between AATIF layers. The module is **B-prime** — observational/structural, never judicial. It never touches H, θ, or the S equation.

**Core principle:** "الطبقات لا تتحدث بحرية. كل إشارة تسلك سلكها الخاص."
(Layers do not talk freely. Each signal travels its own wire.)

---

## 2. Current Communication Patterns (from Governor Analysis)

The Governor currently orchestrates all module communication through direct method calls. Here's the existing flow mapped to channels:

### What flows WHERE today (implicit channels):

| Data flowing | From → To | Proposed Channel |
|---|---|---|
| Identity fingerprint | `aatif_fingerprint` → Governor → prompt | **B1 — Identity** |
| Constitutional laws (GATED_PROFILES, DOMAIN_CONFIG) | `aatif_s_equation` constants → Governor | **B2 — Constitutional** |
| Refined meaning (intent layers, logic profile) | `five_layer_intent`, `logic_profile_scanner` → Governor → prompt | **B3 — Meaning** |
| Intent vectors (I score, contextual intent) | `aatif_intent_scorer`, `contextual_intent` → `s_equation` → Governor | **B4 — Intent** |
| Tone/rhythm/expression (R result, response shape) | `aatif_r_equation`, `response_shaper` → Governor → prompt | **B5 — Behaviour** |
| Safety constraints (S decision, H score, protocol actions) | `s_equation`, `domain_protocols`, `output_gate` → Governor | **B6 — Safety** |
| Drift signals (drift risk, PSP detection) | `drift_detector`, `psp_detector`, `uncertainty_detector` → Governor | **B7 — Drift Detection** |
| Approved output (governed prompt, final response) | Governor → Runtime (via `llm_fn` hook) | **B8 — Execution** |

### Modules mapped to channels they produce/consume:

| Module | Produces (channels) | Consumes (channels) |
|---|---|---|
| `aatif_s_equation` | B6 (S decision, H score) | B2 (constitutional params), B4 (intent) |
| `aatif_domain_protocols` | B6 (protocol actions) | B2 (domain rules) |
| `aatif_r_equation` | B5 (style recommendation) | B1 (user context) |
| `aatif_output_gate` | B6 (gate verdict), B8 (cleaned text) | B6 (protocol reading) |
| `aatif_fingerprint` | B1 (fingerprint reading) | — |
| `aatif_temporal_memory` | B1 (temporal context) | — |
| `aatif_intent_scorer` | B4 (intent score) | — |
| `aatif_five_layer_intent` | B3 (five-layer reading) | B4 (I score), B6 (H score) |
| `aatif_logic_profile_scanner` | B3 (logic profile) | — |
| `aatif_drift_detector` | B7 (drift risk) | B6 (H score), B4 (I score) |
| `aatif_psp_detector` | B7 (PSP detection) | — |
| `aatif_meta_oversight` | B6 (coherence verdict) | B6 (S/P decisions), B5 (R style) |
| `aatif_reasoning_trace` | B3 (constitutional trace) | B6 (decision + scores) |
| `aatif_muhajij` | B3 (justification) | B6 (decision), B5 (audience) |
| `aatif_response_shaper` | B5 (response shape) | B6 (decision), B1 (memory) |
| `aatif_boot_sequence` | B2 (boot verification) | all channels (integrity check) |
| `aatif_governor` | B8 (governed prompt) | ALL channels |
| `aatif_multi_intent_collision` | B3 (collision result) | B4 (I score), B6 (H score) |
| `aatif_authority_doctrine` | B2 (authority context) | B1 (authority id) |
| `aatif_false_goodness_detector` | B6 (H boost) | B4 (intent), B6 (H score) |

---

## 3. Design Questions for Consensus

### Q1: Data Structure — What is a "Channel" and a "BindingMap"?

**Proposal:**

```python
@dataclass
class Signal:
    """A typed signal travelling through a channel."""
    channel: ChannelType          # B1-B8 enum
    source_module: str            # e.g. "aatif_fingerprint"
    target_module: str            # e.g. "aatif_governor"  
    payload: Any                  # the actual data
    timestamp: float              # when the signal was created
    signal_id: str                # unique ID for audit trail

class ChannelType(Enum):
    B1_IDENTITY = "B1_IDENTITY"
    B2_CONSTITUTIONAL = "B2_CONSTITUTIONAL"
    B3_MEANING = "B3_MEANING"
    B4_INTENT = "B4_INTENT"
    B5_BEHAVIOUR = "B5_BEHAVIOUR"
    B6_SAFETY = "B6_SAFETY"
    B7_DRIFT = "B7_DRIFT"
    B8_EXECUTION = "B8_EXECUTION"

@dataclass
class BindingMap:
    """The complete binding map: who talks to whom, through which channel."""
    bindings: list[ChannelBinding]   # all registered bindings
    
@dataclass  
class ChannelBinding:
    """One binding: source_module → target_module through a specific channel."""
    source_module: str
    target_module: str
    channel: ChannelType
    signal_types: frozenset[str]    # allowed payload type names
```

**Open question:** Should signals be actual runtime objects that flow through the system, or should the BindingMap be a **declarative registry** that validates existing communication patterns? The declarative approach is lighter — it doesn't change how modules actually talk, but it validates that the communication patterns are correct.

### Q2: Type Safety Enforcement — How?

**Option A — Runtime enforcement:** Every module-to-module call passes through the BindingMap, which checks channel + type before forwarding.

**Option B — Declarative validation:** The BindingMap declares what's allowed. A `validate()` method checks existing communication patterns against the map. Violations are logged and optionally raised.

**Option C — Boot-time + audit:** Validate the map at boot time (FN#045 integration). At runtime, modules communicate as they do now, but the Governor annotates each signal on the GovernedResponse audit trail with its channel.

**Recommendation:** Option C. It's B-prime compliant (observational), doesn't add runtime overhead to the safety-critical pipeline, and connects naturally to the existing boot sequence and audit trail.

### Q3: Boot-Time Validation (FN#045 Integration)

The boot sequence already checks required stages. Proposal: add a `BINDING_MAP` stage between `OUTPUT_GATE` and `OPTIONAL_MODULES`:

```
CORE_ENGINE → DOMAIN_PROTOCOLS → RESPONSE_SHAPER → CONVERSATION_MEMORY 
→ TIME_SENSE → OUTPUT_GATE → BINDING_MAP → OPTIONAL_MODULES → SYSTEM_READY
```

The BINDING_MAP stage:
1. Constructs the canonical binding map (all 8 channels with their allowed sources/targets/types)
2. Validates that no channel is missing or empty
3. Validates signal type constraints (e.g., B6 only carries safety-typed signals)
4. Returns the validated map (attached to the Governor for runtime annotation)

### Q4: Audit Trail — What Gets Logged?

Every `GovernedResponse` already records s_result, p_result, r_result, etc. Proposal: add a `channel_audit` field that records which channels carried signals during this request:

```python
@dataclass
class ChannelAuditEntry:
    channel: ChannelType
    source_module: str
    signal_type: str
    timestamp: float
    
# On GovernedResponse:
channel_audit: list[ChannelAuditEntry] = field(default_factory=list)
```

### Q5: Relationship to FN#017 (Priority Hierarchy)

FN#017 = who wins conflicts (priority). FN#044 = how layers communicate (channels).

The BindingMap should respect FN#017: when B6 (Safety) and B5 (Behaviour) conflict, B6 wins. This is already enforced by the Governor's sovereignty logic. The BindingMap doesn't need to re-implement priority — it just needs to be aware that B6 has the highest structural priority.

### Q6: B-Prime Compliance

The binding map module MUST be:
- **Structural** — it defines channels and validates bindings
- **Observational** — it annotates what happened, never decides what should happen
- **Never judicial** — it never touches H, θ, or S
- **Never blocks** — validation failures at boot time can halt boot (fail-safe), but runtime annotation never blocks a message

---

## 4. Proposed Module Structure

```
engine/aatif_binding_map.py
├── ChannelType (enum: B1-B8)
├── SignalType (enum: IDENTITY, CONSTITUTIONAL, MEANING, INTENT, BEHAVIOUR, SAFETY, DRIFT, EXECUTION)
├── ChannelBinding (dataclass: source → target through channel)
├── ChannelAuditEntry (dataclass: what flowed through which channel)
├── BindingMap (class)
│   ├── __init__() — builds canonical bindings
│   ├── validate() — checks structural integrity
│   ├── get_channel_for(source, target) → ChannelType
│   ├── validate_signal(source, target, signal_type) → bool
│   ├── record_signal(source, target, signal_type) → ChannelAuditEntry
│   └── get_audit_trail() → list[ChannelAuditEntry]
└── build_canonical_binding_map() → BindingMap
```

---

## 5. Test Strategy

```
tests/test_binding_map.py
├── TestChannelType — enum completeness (8 channels)
├── TestChannelBinding — dataclass construction
├── TestBindingMap
│   ├── test_canonical_map_has_all_8_channels
│   ├── test_each_channel_has_at_least_one_binding
│   ├── test_validate_passes_for_canonical_map
│   ├── test_validate_fails_for_missing_channel
│   ├── test_validate_fails_for_wrong_signal_type
│   ├── test_get_channel_for_known_binding
│   ├── test_get_channel_for_unknown_raises
│   ├── test_validate_signal_correct_type
│   ├── test_validate_signal_wrong_type_rejected
│   ├── test_record_signal_creates_audit_entry
│   ├── test_audit_trail_ordered_by_timestamp
│   ├── test_b_prime_compliance (never touches H, θ, S)
│   └── test_no_cross_channel_leakage
├── TestBootIntegration
│   ├── test_binding_map_validates_at_boot
│   └── test_corrupted_map_fails_boot
└── TestGovernorIntegration
    ├── test_governor_annotates_channel_audit
    └── test_channel_audit_on_governed_response
```

---

## 6. What Success Looks Like

1. `engine/aatif_binding_map.py` — defines 8 channels, all existing module communications mapped
2. Boot sequence validates the binding map at startup
3. GovernedResponse includes channel audit trail
4. All ~2766 existing tests still pass (zero regressions)
5. New tests cover channel definitions, type safety, audit trail, boot integration
6. Module is pure B-prime — structural/observational, never judicial
