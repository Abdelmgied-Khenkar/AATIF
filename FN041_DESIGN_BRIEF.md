# FN#041 — Context-Preservation & Parallel-Task Safety Protocol (PVM)
# Design Brief for Consensus Discussion

**Prepared by:** Claude (Anthropic) — for Architect review  
**Date:** 2026-07-01  
**Purpose:** Document the architectural design of the Passive Verification Mode detector  
**Status:** Ready for consensus discussion  
**Rule:** Do NOT build from this brief. Discuss first, build after consensus.

---

## 1. Field Note Summary — Core Insight

**Source:** FN#041 — Context-Preservation & Parallel-Task Safety Protocol

**The one-line principle:**
> *"When the user is busy, the system waits. It does not fill the silence."*
> *لما المستخدم مشغول، النظام ينتظر. لا يملأ الصمت.*

**The problem PVM solves:**
Current AI systems treat silence as a signal to generate more content. When a user is multi-tasking, distracted, or temporarily unavailable, the system continues producing output — creating cognitive overload when the user returns. This violates human primacy: the system should adapt to the human's rhythm, not force the human to adapt to the system's.

**Conscious silence as constitutional law (الصمت الواعي كقانون دستوري):**
Silence is not absence — it is an active state of respectful waiting. The system acknowledges receipt, confirms it is ready, and then WAITS for the human to signal continuation. This is not passivity; it is governed patience.

**Scientific support:**
- Jiang et al. (CHI 2026): Intelligent silence improves trust and user satisfaction — users rate systems higher when they wait vs. when they interrupt
- Ask-before-Plan (EMNLP 2024): Systems that wait for intent confirmation before execution produce better outcomes
- Horvitz (CHI 1999): Mixed-initiative systems must weigh the cost of interruption before responding — not all system actions are welcome at all times

**What PVM affects:** Response timing, response length, whether to initiate new content.

**What PVM does NOT affect:** Safety decisions, harm scoring, θ thresholds, content filtering.

---

## 2. What Already Exists in the Codebase

### 2.1 `aatif_time_sense.py` — Temporal Signals (196 lines)
- `TimeReading` with `time_since_last_interaction`, `interaction_gap_assessment`, `fatigue_risk`
- Gap assessment: "طويل" / "عادي" / "سريع" / "أول_تواصل"
- PVM can consume gap assessment and fatigue_risk as input signals

### 2.2 `aatif_fingerprint.py` — User Behavioral Patterns (559 lines)
- `FingerprintReading` with `communication_style`, `comprehension_level`, `active_periods`
- Tracks message length, frequency, confusion/satisfaction signals
- PVM can detect sudden changes from the user's established pattern

### 2.3 `aatif_binding_map.py` — B5 Behaviour Channel
- B5 carries: `StyleRecommendation`, `ResponseShape`, `RReading`, `ToneGuidance`
- PVM output should bind to B5 as a new signal type: `PVMReading`
- PVM does NOT bind to B6 (Safety) — it is stylistic, not judicial

### 2.4 `aatif_psp_detector.py` — Closest Analog (PSP pattern)
- Same B-prime architecture: observational, never touches S/H/θ
- State lifecycle enum (PSPState), context storage (PSPContext)
- Three-tier detection with sparse activation
- PVM should follow this exact pattern but with different signals

---

## 3. Architectural Design — PVM Detector

### 3.1 B-prime Contract

```python
AUTHORITY_LEVEL = "B_PRIME_OBSERVATIONAL"
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA            = False
CAN_MODIFY_S                = False
CAN_EMIT_JUDICIAL_DECISION = False
```

PVM is observational. It detects whether the user is busy and provides a reading to the R equation. It never blocks, never modifies safety parameters, never makes judicial decisions.

### 3.2 PVM State Lifecycle

```
ACTIVE           → normal operation, no PVM signals detected
DETECTING        → signals suggest user may be busy (1+ signals)
PVM_ENGAGED      → system has entered passive waiting mode (high confidence)
REACTIVATING     → user has returned, transitioning back to active
```

Transitions:
- ACTIVE → DETECTING: first busy signal detected
- DETECTING → PVM_ENGAGED: confidence crosses threshold (0.6) OR explicit busy signal
- DETECTING → ACTIVE: follow-up message is substantive (not minimal)
- PVM_ENGAGED → REACTIVATING: return signal detected
- REACTIVATING → ACTIVE: first substantive interaction after return
- PVM_ENGAGED → ACTIVE: timeout (after N turns of no interaction, assume context shift)

### 3.3 Detection Signals — Three Tiers

**Tier 1: Deterministic markers (cheap, high precision)**

| Signal | Arabic | English | Confidence |
|--------|--------|---------|------------|
| Explicit busy | مشغول, لحظة, دقيقة, بعدين, مشغوله | busy, wait, hold on, brb, one moment | 0.90 |
| Incomplete ack | طيب (alone), اوكي (alone), ماشي (alone) | ok (alone), hmm, yeah | 0.50 |
| Return signals | كمل, أكمل, نكمل, وين وقفنا, يلا | continue, go on, I'm back, resume | 0.90 (for exit) |
| Multi-task marker | خلني اخلص, بس خلني اول | let me finish this first | 0.85 |

**Tier 2: Temporal signals (from TimeSense)**

| Signal | Condition | Confidence |
|--------|-----------|------------|
| Response gap | gap > 2× user's average gap | 0.40 |
| Late night fatigue | fatigue_risk=True from TimeSense | 0.30 |
| Mid-conversation drop | was rapid, now >5min gap | 0.50 |

**Tier 3: Behavioral signals (from Fingerprint)**

| Signal | Condition | Confidence |
|--------|-----------|------------|
| Length collapse | msg length < 25% of user's average | 0.35 |
| Pattern break | communication_style suddenly different | 0.30 |

### 3.4 Sparse Activation

Most turns are normal — user is present and engaged. PVM should fast-path skip (return ACTIVE with no overhead) when:
- Message length > 20 characters AND contains directive content
- Message contains a question or explicit instruction
- No busy markers present

Fast-path confidence threshold: `not_busy_confidence >= 0.95`

### 3.5 PVMReading — What the detector outputs

```python
@dataclass
class PVMReading:
    state: PVMState                      # current lifecycle state
    confidence: float                    # [0,1] how certain we are of the state
    should_pause: bool                   # recommendation to R equation
    pause_type: str                      # "full_wait" | "brief_ack" | "shortened" | "normal"
    recommended_acknowledgment: str      # Arabic-first acknowledgment text
    evidence: List[str]                  # audit trail
    signals_detected: List[str]          # which signals fired
    estimated_return_likelihood: float   # [0,1] will user likely return soon?
```

### 3.6 PVMContext — Pure storage

```python
@dataclass
class PVMContext:
    state: PVMState = PVMState.ACTIVE
    last_explicit_directive_turn: int = -1
    consecutive_minimal_responses: int = 0
    last_gap_seconds: Optional[float] = None
    pvm_engage_turn: int = -1
    pvm_engage_timestamp: Optional[float] = None
    last_return_signal_turn: int = -1
    total_pvm_engagements: int = 0
```

### 3.7 Cultural Sensitivity via Domain (D) Parameter

Silence tolerance varies by culture. The domain parameter drives adjustment:

| Context | PVM Engage Threshold | Notes |
|---------|---------------------|-------|
| Gulf Arabic (default) | 0.55 | Patience valued, longer silences acceptable |
| Medical/High-stakes | 0.70 | Higher bar — user may be consulting during silence |
| Western/Fast-paced | 0.45 | Shorter tolerance, earlier PVM engagement |
| Education | 0.60 | Student may be thinking/working on exercise |

---

## 4. Integration Points

### 4.1 R Equation Integration
PVM outputs to R equation, NOT S equation. When PVM is engaged:
- R should bias toward shorter, acknowledgment-only responses
- R should increase "patience" parameter
- R should suppress unsolicited elaboration

### 4.2 Binding Map (B5)
PVM signals travel through B5 (Behaviour):
- Signal type: `PVMReading`
- Source: `aatif_pvm_detector`
- Target: `aatif_governor` (for R equation routing)

### 4.3 Governor Integration (future)
The Governor can optionally consume PVMReading to:
- Adjust prompt composition (shorter prompts when PVM engaged)
- Include acknowledgment text
- Suppress multi-paragraph responses

---

## 5. Open Questions from Field Note

### Q1: How does the system automatically detect when to enter PVM?
**Proposed answer:** Three-tier detection (deterministic markers → temporal signals → behavioral signals) with sparse activation. Explicit markers are highest confidence; temporal/behavioral provide supporting signals.

### Q2: What's the boundary between "active waiting" and "ignoring the user"?
**Proposed answer:** PVM always acknowledges receipt. It never goes silent without confirmation. The acknowledgment says "أنا هنا، كمل لما تفرغ" (I'm here, continue when you're free). There is NO state where the system fails to respond at all.

### Q3: Does PVM exit timing vary by culture?
**Proposed answer:** Yes, via the domain parameter. Gulf Arabic contexts tolerate longer PVM engagement; Western contexts trigger earlier reactivation prompts. The detector reads culture from the domain config, it never decides culture.

---

## 6. What PVM Does NOT Do

| Action | Prohibited? | Why |
|--------|------------|-----|
| Block responses | YES | Only S equation blocks |
| Modify H score | YES | Single Mind Law |
| Modify θ threshold | YES | Constitutional |
| Make safety decisions | YES | B-prime contract |
| Ignore messages | YES | Always acknowledges |
| Decide response content | YES | That's the response shaper |
| Override user directive | YES | Human primacy |

---

## 7. Test Coverage Plan

| Category | Tests | Focus |
|----------|-------|-------|
| Feature flags | 3 | PVM_ENABLED=True, PVM_MONITOR_ONLY=False |
| Authority level | 6 | All CAN_* flags are False |
| Dataclasses | 10 | PVMReading, PVMContext, PVMDomainConfig defaults |
| Explicit busy markers (AR) | 10 | مشغول, لحظة, بعدين, etc. |
| Explicit busy markers (EN) | 10 | busy, wait, hold on, brb, etc. |
| Return signals (AR) | 8 | كمل, نكمل, وين وقفنا, etc. |
| Return signals (EN) | 8 | continue, resume, I'm back, etc. |
| Incomplete ack detection | 8 | "ok" alone, "طيب" alone, etc. |
| Fast-path skip | 8 | Substantive messages skip PVM |
| State transitions | 12 | All valid transitions, invalid blocked |
| Temporal integration | 6 | Gap-based signals from TimeSense |
| Cultural sensitivity | 5 | Domain-based threshold adjustment |
| Multi-task markers | 5 | "let me finish this", "خلني اخلص" |
| Edge cases | 6 | Empty text, very long text, mixed signals |
| **Total** | **~105** | |

---

## 8. Consensus Questions for ChatGPT

1. Is the three-tier detection (deterministic → temporal → behavioral) the right architecture for PVM?
2. Should PVM always acknowledge (never go fully silent), or are there cases where true silence is better?
3. Is the PVM state lifecycle (ACTIVE → DETECTING → PVM_ENGAGED → REACTIVATING) sufficient, or does it need more states?
4. Should PVM decay time be cultural (Gulf longer, Western shorter)?
5. Does the B5 binding (Behaviour, not Safety) correctly reflect PVM's role?
