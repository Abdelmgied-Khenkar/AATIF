# AATIF Judgment Memory Layer — ذاكرة الحُكم
## Technical Architecture Design

**Status:** Design — D parameter added; Q1-Q3 resolved; awaiting implementation
**Date:** 2026-06-28 (D parameter update) | 2026-06-27 (initial design)
**Architect:** Abdulmjeed Ibrahim Khenkar
**License:** BSL 1.1

---

## 1. The Problem — لماذا ذاكرة الحُكم؟

AATIF currently starts from zero on every interaction. The S equation

    S = sigma(w1*I + w2*E) * (1 - sigma(alpha*(H - theta)))

scores each message in isolation. It has no memory of:

- **Dialect norms:** "هموت فيك" from a known Levantine speaker is love, not a threat.
  But without memory, H scores it against harm anchors every single time.
- **Intent history:** A teacher who has asked 50 educational questions about chemistry
  should not get the same theta as a first-time user asking the same question.
- **Escalation patterns:** A user who went benign -> benign -> probing -> testing
  is exhibiting a pattern the equation cannot see in a single turn.
- **Prior judgments:** If AATIF already judged "زهقت من البيت ومصاريفه" as benign
  financial stress for this user last week, why re-litigate it?

## 2. Philosophy — ميزان مش فهرس

This is NOT MemPalace (an index/فهرس that finds similar memories).
This is a judgment support system (ميزان/scale) that informs the S equation.

Same tools (cosine similarity, embeddings) but different purpose:
- MemPalace: "find me memories similar to X" → retrieval
- Judgment Memory: "given what I know about this user, adjust my judgment of X" → governance

The approach is **تربية** (nurturing/tarbiyah) not **تعليم** (teaching):
- The memory helps AATIF build contextual judgment over time
- It does not override safety — it **informs** the equation
- Like a parent who knows their child: not less cautious, but more accurate

**Key constraint:** Judgment Memory NEVER overrides the hard floor.
If H > 0.7, the hard override to SAFE_FREEZE stays absolute.
"الاذي مالوش توقيت" — and it has no user history either at the extreme.

---

## 3. What Already Exists — الموجود حالياً

Before designing, here is what is already built and how Judgment Memory
relates to each component:

| Component | What it does | Relationship to Judgment Memory |
|-----------|-------------|-------------------------------|
| `aatif_s_equation.py` | Scores H, I, E per message; produces S and decision | **Consumer** — JM feeds adjustments INTO the equation |
| `aatif_hysteresis.py` | Prevents decision oscillation across turns | **Peer** — JM provides history; hysteresis provides stability |
| `aatif_conversation_memory.py` | Tracks emotional arcs and conversation context (RAM/JSON) | **Replaced/Absorbed** — JM subsumes its judgment-relevant parts |
| `aatif_temporal_memory.py` | SQLite storage of interaction history with timestamps | **Data Source** — JM reads from this; does not duplicate storage |
| `aatif_fingerprint.py` | Behavioral pattern detection (dialect, style, trust) | **Data Source** — JM uses fingerprint readings as context |
| `aatif_governor.py` | Orchestrates S -> P -> R -> Output Gate pipeline | **Integration Point** — Governor calls JM before S(d) |
| Dynamic theta (`compute_dynamic_theta`) | Adjusts theta based on blocked decision count | **Extended** — JM provides richer history than block count |

**Key insight:** TemporalMemory + Fingerprint already store facts and patterns.
Judgment Memory is the THIRD layer that uses both to inform the equation.
The triangle (المثلث) is now:

    TemporalMemory = الحقائق (facts — what happened when)
    Fingerprint    = النمط   (patterns — who this person is)
    JudgmentMemory = الحُكم  (judgment — how to weigh what they say)

---

## 3.5 The D Parameter — Domain Sensitivity (حساسية الدومين)

**Added:** 2026-06-28 — resolves Open Questions Q1, Q2, Q3 from Section 14.

D is a scalar parameter (0 to 1) that captures the sensitivity level
of the deployment domain. Like θ, D is a **config parameter** — set at
deployment time — fixed design, variable fit (embedding weights can be tuned per deployment; see Tailor Principle FN#079).

### 3.5.1 Domain Profiles

| Domain | D Value | Behavior |
|--------|---------|----------|
| Casual chat | 0.20 | Low stakes — flexible, dialect-aware, light storage |
| Education | 0.40 | Moderate — allow exploration, standard storage |
| Banking | 0.80 | High stakes — strict, minimal dialect adjustment, full audit |
| Healthcare | 0.90 | Critical — near-maximum caution, "بموت" = clinical risk |
| Government / Security | 0.95 | Maximum — almost zero flexibility, full forensic storage |

### 3.5.2 What D Controls (Inverse Proportionality)

D answers three questions through a single formula: `behavior = (1 - D)`

**Q1 — Trust Credit (θ loosening):**
```
trust_adjustment = max_trust × (1 - D)
```
- Casual (D=0.2): 0.05 × 0.8 = 0.040 — meaningful loosening
- Banking (D=0.8): 0.05 × 0.2 = 0.010 — barely loosens
- Government (D=0.95): 0.05 × 0.05 = 0.0025 — effectively zero

**Q2 — Dialect Prior Weight:**
```
dialect_weight = (1 - D)
```
- Casual (D=0.2): 0.80 — "بموت فيك" fully recognized as love
- Healthcare (D=0.9): 0.10 — "بموت" treated as clinical risk signal

**Q3 — Storage Depth:**
```
D > 0.7: FULL — all judgments + embeddings + full context (audit trail)
D > 0.4: STANDARD — judgments + decisions (tiered decay as Section 7)
D ≤ 0.4: LIGHT — only safety-relevant events (SAFE_STOP, SAFE_FREEZE)
```

### 3.5.3 Connection to الذكازمكان (Intelligence-Spacetime)

D is the **gravitational constant** of the domain.

In physics, G determines how strongly mass curves spacetime.
In AATIF, D determines how strongly words curve the judgment space.

```
Mapping:
  G (gravitational constant) → D (domain sensitivity)
  Mass (of objects)          → Mass (of words, via anchor proximity)
  Curvature of spacetime     → Curvature of judgment trajectory
  Geodesic path              → The response path the output takes
  θ (threshold)              → How much curvature triggers safety action
  S equation                 → The field equation computing final curvature
```

The SAME word — "بموت" — has the same mass everywhere. But in
healthcare (D=0.9), that mass produces MORE curvature than in
casual chat (D=0.2). The word didn't change. The space changed.

### 3.5.4 D is Config, Not Fine-Tuning

D preserves the Tailor Principle (FN#079):
- The S equation does not change
- The anchor sets do not change
- The decision logic does not change
- Only the domain's gravitational constant changes — shaping how
  the same equations behave in different deployment contexts

**"الدومين يقرر — مش قاعدة واحدة للكل."**

---

## 4. Architecture — البنية

### 4.1 Where It Sits in the Pipeline

```
User message
    |
    v
[JudgmentMemory.prepare_context(user_id, message)]
    |   Reads: TemporalMemory, Fingerprint
    |   Produces: JudgmentContext (adjustments for H, I, E + theta)
    |
    v
[AATIFEngine.compute(message, judgment_context=ctx)]
    |   H scorer runs -> raw H
    |   I scorer runs -> raw I
    |   E scorer runs -> raw E
    |   JudgmentContext applied:
    |     H_adj = apply_dialect_prior(H, ctx)
    |     I_adj = apply_intent_prior(I, ctx)
    |     theta_adj = apply_escalation_adjustment(theta, ctx)
    |   S = sigma(w1*I_adj + w2*E) * (1 - sigma(alpha*(H_adj - theta_adj)))
    |
    v
[Governor pipeline continues: P(d) -> R(d) -> Output Gate]
    |
    v
[JudgmentMemory.record_outcome(user_id, message, result)]
    |   Stores: the judgment made, so it can inform the next one
```

**Critical design decision:** JudgmentMemory runs BEFORE the S equation,
not after. It provides context that makes the scorers more accurate.
It does NOT change the decision after S produces it — that would
violate sovereignty (السيادة).

The adjustments are **pre-equation context**, not **post-equation overrides**.

### 4.2 The JudgmentContext Object

This is what JudgmentMemory produces for each interaction:

```python
@dataclass
class JudgmentContext:
    """Context that informs (not overrides) the S equation."""

    user_id: str

    # ── Dialect Prior ──
    # If the user's fingerprint says "Levantine speaker" and the
    # current message contains "بموتك", the H scorer should see
    # this alongside a dialect context signal.
    dialect_profile: str          # "gulf", "egyptian", "levantine", "mixed", "unknown"
    dialect_confidence: float     # 0.0-1.0 — how sure are we of the dialect

    # ── Intent Prior ──
    # Historical intent pattern: what kind of questions does this user ask?
    # A user whose last 20 messages averaged I=0.85 (constructive) gets
    # a different prior than one whose average was I=0.3 (questionable).
    historical_intent_avg: float  # running average of past I scores
    intent_trend: str             # "stable_constructive", "stable_neutral",
                                  # "declining", "escalating", "insufficient_data"
    constructive_ratio: float     # fraction of past interactions with I > 0.6

    # ── Escalation Signal ──
    # Pattern detection: is the user probing, testing, then attacking?
    escalation_detected: bool
    escalation_stage: str         # "none", "probing", "testing", "attacking"
    consecutive_stops: int        # how many SAFE_STOP/FREEZE in a row

    # ── Theta Adjustment ──
    # This replaces the simple Dynamic Theta (blocked decision count).
    # Richer: considers intent trend, escalation, and trust together.
    theta_adjustment: float       # negative = stricter, positive = more lenient
    theta_adjustment_reason: str  # human-readable reason for the adjustment

    # ── Prior Judgment Cache ──
    # If the user asked something very similar before and it was judged safe,
    # record that. This does NOT auto-approve — it provides a prior.
    similar_prior_found: bool
    similar_prior_decision: str   # the decision last time ("EXECUTE", etc.)
    similar_prior_similarity: float  # cosine sim to the prior message
    similar_prior_age_hours: float   # how old is that judgment

    # ── Domain Sensitivity ──
    domain_sensitivity: float     # D parameter (0.0-1.0) — set per deployment
                                  # Controls trust credit, dialect weight, storage depth
                                  # Higher D = more dangerous domain = stricter behavior

    # ── Trust Signal (from Fingerprint) ──
    trust_level: float            # 0.0-1.0 from UserFingerprint
    interaction_count: int        # total past interactions
```

### 4.3 How JudgmentContext Feeds Into Each Scorer

#### H (Harm) Adjustment — ضبط حرارة الكلمة

The H scorer currently has context signals (CASUAL_CONTEXT_SIGNALS,
THREATENING_CONTEXT_SIGNALS) that look at the message itself. Judgment
Memory extends this with USER-LEVEL context:

```
H_adj = H_raw * dialect_factor * prior_factor

Where:
  dialect_factor:
    IF dialect_confidence > 0.7 AND message matches known dialect hyperbole:
      # D-scaled: dialect_weight = (1 - D). See Section 3.5.2
      raw_discount = 0.5  (halve the harm — known dialect speaker using known idiom)
      factor = 1.0 - (1.0 - raw_discount) * (1 - D)
      # Casual (D=0.2): factor = 0.60 — strong dialect adjustment
      # Healthcare (D=0.9): factor = 0.95 — dialect almost ignored
    ELSE:
      factor = 1.0  (no adjustment)

  prior_factor:
    IF similar_prior_found AND similar_prior_decision == "EXECUTE"
       AND similar_prior_age_hours < 168  (7 days)
       AND similar_prior_similarity > 0.85:
      factor = 0.7  (reduce H — we judged this safe recently)
    ELSE:
      factor = 1.0
```

**Safety rails on H adjustment:**
- H_adj can NEVER go below 0.15 (absolute floor — "I don't know" is not "safe")
- If H_raw > 0.7 (hard override zone), NO adjustment is applied. Period.
- dialect_factor only applies to messages matching known hyperbole patterns,
  not to all messages from dialect speakers
- prior_factor decays: older judgments carry less weight

#### I (Intent) — No Direct Adjustment

I is NOT adjusted by memory. Why:
- I already measures the PURPOSE of this specific message
- Historical intent averages are a DIFFERENT signal (user pattern, not message intent)
- Adjusting I based on past behavior creates a "boy who cried wolf" risk:
  a user with high historical I could send a genuinely harmful message and
  the adjusted I would underestimate the threat

Intent history feeds into theta_adjustment instead (see below).

#### E (Emotion) — No Direct Adjustment

E measures the emotional state of THIS message. Past emotional patterns
are tracked by the Fingerprint and Conversation Memory for response
shaping (R equation), not for safety judgment.

#### Theta Adjustment — ضبط العتبة

This is the most important integration point. Instead of the simple
Dynamic Theta (block count -> decay), Judgment Memory computes a
richer theta adjustment:

```
theta_adj = theta_base + delta

Where delta is computed from:

  1. Escalation penalty (always negative — tighter):
     IF escalation_detected:
       delta -= 0.10  (probing)
       delta -= 0.15  (testing)
       delta -= 0.20  (attacking — approaching the hard override)

  2. Consecutive stops penalty (always negative):
     IF consecutive_stops >= 2:
       delta -= 0.05 * min(consecutive_stops, 4)  # max -0.20

  3. Trust credit (can be positive — looser, but small and D-scaled):
     IF trust_level > 0.5 AND interaction_count > 20
        AND intent_trend == "stable_constructive"
        AND consecutive_stops == 0:
       delta += max_trust * (1 - D)  # D-scaled: see Section 3.5.2
       # max_trust = 0.05
       # Casual (D=0.2): +0.040 — meaningful loosening
       # Banking (D=0.8): +0.010 — barely loosens
       # Government (D=0.95): +0.0025 — effectively zero
     (This is the ONE case where memory makes theta more lenient.
      It requires high trust, many interactions, stable constructive
      intent, and zero recent stops. Now D-scaled: high-D domains
      grant almost no trust credit regardless of history.)

  Clamp: theta_adj = clamp(theta_base + delta, 0.20, theta_base + 0.05)
  - Floor: 0.20 (same as Dynamic Theta)
  - Ceiling: theta_base + 0.05 (memory can never raise theta by more than 0.05)
```

**Asymmetry is intentional.** Memory can tighten theta significantly
(up to -0.20) but can loosen it only slightly (+0.05). This reflects
the Architect's principle: trust is earned slowly, lost quickly.

---

## 5. Storage — التخزين

### 5.1 What Gets Stored

Judgment Memory stores **judgments**, not raw text.

```sql
-- Judgment ledger: one row per scored interaction
CREATE TABLE judgment_ledger (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    timestamp   TEXT NOT NULL,          -- ISO 8601
    -- Message identity (NOT the raw text — privacy)
    msg_hash    TEXT NOT NULL,          -- SHA-256 of normalized text
    msg_embedding BLOB,                -- bge-m3 embedding (768 floats, ~3KB)
    -- Scores at time of judgment
    H_raw       REAL,
    H_adjusted  REAL,
    I_score     REAL,
    E_score     REAL,
    S_score     REAL,
    -- Judgment outcome
    decision    TEXT,                   -- EXECUTE / CLARIFY / SAFE_STOP / SAFE_FREEZE
    domain      TEXT,
    domain_sensitivity REAL,           -- D parameter value used for this judgment
    theta_used  REAL,
    -- Context that informed this judgment
    dialect_detected TEXT,
    escalation_stage TEXT,
    prior_used  INTEGER DEFAULT 0,     -- was a prior judgment applied?
    -- Decay tracking
    expires_at  TEXT                    -- ISO 8601 — when this judgment expires
);

CREATE INDEX idx_jl_user_time ON judgment_ledger(user_id, timestamp);
CREATE INDEX idx_jl_user_decision ON judgment_ledger(user_id, decision);
CREATE INDEX idx_jl_hash ON judgment_ledger(msg_hash);
```

### 5.2 Storage Technology

**SQLite** — same as TemporalMemory. Reasons:
- Already proven in the codebase (aatif_temporal_memory.py uses it)
- No server to run — fits the solo-developer workflow
- WAL mode handles concurrent reads well
- Can store embeddings as BLOBs (numpy array -> bytes -> BLOB)
- Queries are simple (by user_id + time range)

**Single database file:** `judgment_memory.db` in the same storage directory
as `temporal_memory.db`. They are separate databases because they serve
different purposes and have different retention policies.

### 5.3 Embedding Storage for Prior Lookup

The `msg_embedding` column stores the bge-m3 embedding of the message.
When a new message comes in, Judgment Memory:

1. Embeds the new message (reuses the existing OllamaBackend)
2. Loads the last N embeddings for this user from the ledger
3. Computes cosine similarity between new and stored embeddings
4. If max similarity > 0.85, retrieves that prior judgment

This is NOT a vector database. It is a small per-user scan:
- Last 50 judgments per user = 50 cosine similarities
- Each is a 768-dim dot product = microseconds
- No ANN index needed at this scale

If scale becomes a concern (thousands of users, millions of judgments),
the first optimization is an expiry sweep (Section 7), not a vector DB.

---

## 6. Escalation Detection — كشف التصعيد

One of the most valuable things Judgment Memory provides: detecting
escalation patterns that are invisible in single-turn scoring.

### 6.1 The Escalation Model

```
Sequence analysis over the user's last N interactions (window = 10):

  Stage 1 — Normal (عادي):
    All recent decisions are EXECUTE.
    No pattern detected.

  Stage 2 — Probing (استكشاف):
    User's H scores are creeping upward:
      avg(H, last 3) > avg(H, last 10) * 1.5
    Intent still looks constructive (I > 0.5).
    This is the "just asking questions" phase.

  Stage 3 — Testing (اختبار):
    User has triggered at least 1 CLARIFY or SAFE_STOP
    and is now asking related questions that avoid the trigger.
    Detection: cosine similarity between recent messages is high (> 0.6)
    AND the topic cluster is narrowing toward a harm-adjacent area.

  Stage 4 — Attacking (هجوم):
    User has triggered 2+ SAFE_STOP or SAFE_FREEZE
    and continues on the same topic cluster.
    This is no longer accidental — it is persistent probing.
```

### 6.2 What Happens at Each Stage

| Stage | Theta Adjustment | Additional Action |
|-------|-----------------|-------------------|
| Normal | None | None |
| Probing | -0.10 | Flag in audit trail |
| Testing | -0.15 | Governor logs escalation pattern |
| Attacking | -0.20 | Consecutive CLARIFY -> faster exhaustion (hysteresis) |

The escalation stage is computed from the judgment ledger, not from
real-time scoring. It is a PATTERN over time, not a single-message feature.

---

## 7. Privacy and Decay — الخصوصية والتلاشي

### 7.1 What Is NOT Stored

- **Raw message text** — NEVER stored. Only the hash and embedding.
  The embedding cannot be reversed to text (it is a compressed vector in
  768-dimensional space, not a reversible encoding).
- **Personal identifying information** — user_id is an opaque key.
  Judgment Memory does not know names, emails, or phone numbers.
- **Conversation content** — message summaries stay in TemporalMemory.
  Judgment Memory stores only scores, decisions, and the embedding.

### 7.2 Decay Policy — التلاشي

Not all judgments should live forever. Decay policy:

```
**Note:** Storage depth is D-scaled (see Section 3.5.2).
High-D domains (banking, healthcare, gov) use FULL storage policy.
Low-D domains (casual) use LIGHT policy. The tiers below apply
within the STANDARD and FULL policies:

Tier 1 — EXECUTE judgments:
  Expire after 30 days (STANDARD) or 90 days (FULL / D > 0.7).
  Rationale: benign interactions are common. High-D domains
  retain them longer for audit trail purposes.

Tier 2 — CLARIFY judgments:
  Expire after 60 days (STANDARD) or 180 days (FULL / D > 0.7).
  Rationale: borderline cases need slightly longer context
  for escalation detection. High-D domains keep full history.

Tier 3 — SAFE_STOP / SAFE_FREEZE judgments:
  Expire after 180 days (STANDARD) or 365 days (FULL / D > 0.7).
  Rationale: safety-relevant history should persist longer.
  High-D domains (healthcare, banking) retain for a full year.
  But not forever — people change.

LIGHT policy (D ≤ 0.4):
  Only SAFE_STOP and SAFE_FREEZE judgments are stored.
  EXECUTE and CLARIFY are not persisted — casual domains
  do not need forensic records of benign interactions.

Cleanup job:
  DELETE FROM judgment_ledger WHERE expires_at < NOW()
  Runs on Governor startup and every 24 hours (if running as server).
  Same pattern as TemporalMemory.cleanup().
```

### 7.3 Right to Forget — حق النسيان

A user (or system admin) can request full erasure:

```python
judgment_memory.forget(user_id)
# Deletes ALL rows from judgment_ledger for this user.
# Also clears any in-memory caches.
# Does NOT touch TemporalMemory or Fingerprint — those have
# their own erasure methods.
```

This is a hard delete, not a soft delete. When someone asks to be
forgotten, they are forgotten. No tombstones, no archives.

---

## 8. Interaction with Hysteresis — التفاعل مع التأخر

The hysteresis controller (aatif_hysteresis.py) prevents decision
oscillation within a conversation. Judgment Memory operates at a
DIFFERENT time scale:

- **Hysteresis:** turn-to-turn stability within a single conversation
  (seconds to minutes)
- **Judgment Memory:** cross-conversation patterns over days to months

They do not conflict because they operate at different layers:

1. JudgmentMemory computes JudgmentContext BEFORE the S equation runs
2. S equation produces a raw decision
3. Hysteresis stabilizes the raw decision within the conversation

The escalation detection in JudgmentMemory can feed into hysteresis
by reducing MAX_CLARIFY_TURNS when escalation is detected:

```
Normal:    MAX_CLARIFY_TURNS = 2 (default)
Probing:   MAX_CLARIFY_TURNS = 2 (unchanged)
Testing:   MAX_CLARIFY_TURNS = 1 (faster exhaustion)
Attacking: MAX_CLARIFY_TURNS = 1 (faster exhaustion)
```

This means a user in the "testing" or "attacking" escalation stage
gets only 1 CLARIFY before escalation to SAFE_STOP, instead of 2.

---

## 9. Integration Plan — خطة الربط

### 9.1 New File

```
engine/aatif_judgment_memory.py
```

Contains:
- `JudgmentContext` dataclass
- `JudgmentMemory` class with methods:
  - `prepare_context(user_id, message, embedding)` -> JudgmentContext
  - `record_outcome(user_id, message, embedding, s_result)` -> None
  - `detect_escalation(user_id)` -> escalation stage
  - `find_prior(user_id, embedding)` -> prior judgment or None
  - `forget(user_id)` -> None
  - `cleanup()` -> int (expired rows deleted)

### 9.2 Governor Changes (aatif_governor.py)

```python
# In __init__:
self.judgment_memory = judgment_memory  # Optional[JudgmentMemory]

# In process(), BEFORE S(d):
judgment_ctx = None
if self.judgment_memory and conversation_id:
    judgment_ctx = self.judgment_memory.prepare_context(
        user_id=conversation_id,
        message=message,
        embedding=None,  # computed inside prepare_context
    )

# Pass to S(d):
s_result = self.s_engine.compute(
    message,
    judgment_context=judgment_ctx,   # <-- NEW parameter
    ...
)

# AFTER S(d), record the outcome:
if self.judgment_memory and conversation_id:
    self.judgment_memory.record_outcome(
        user_id=conversation_id,
        message=message,
        embedding=None,
        s_result=s_result,
    )
```

### 9.3 S Equation Changes (aatif_s_equation.py)

The `AATIFEngine.compute()` method gets a new optional parameter:

```python
def compute(self, text, ..., judgment_context=None):
    # Score each dimension (unchanged)
    h_result = self.h_scorer.score(text)
    i_result = self.i_scorer.score(text)
    e_result = self.e_scorer.score(text)

    H = h_result["H"]
    I = i_result["I"]
    E = e_result["E"]

    # NEW: Apply Judgment Memory adjustments
    if judgment_context is not None:
        H = self._apply_judgment_h(H, judgment_context)
        # theta_override comes from judgment_context instead of
        # (or in addition to) Dynamic Theta
        if judgment_context.theta_adjustment != 0:
            # Compute effective theta from domain + judgment adjustment
            base_theta = get_domain_theta(domain) or profile_theta
            theta_override = base_theta + judgment_context.theta_adjustment
            theta_override = max(0.20, min(base_theta + 0.05, theta_override))

    # ... rest of computation unchanged
```

**Minimal changes to the equation itself.** The math stays the same.
Only the inputs (H, theta) can be adjusted by JudgmentContext.
I and E are untouched. The decision logic is untouched.

### 9.4 Relationship to Dynamic Theta

When JudgmentMemory is active, it REPLACES the simple Dynamic Theta.
Both should not run simultaneously because they both adjust theta:

```python
# In Governor:
if self.judgment_memory:
    # JudgmentMemory handles theta adjustment (richer)
    theta_override = judgment_ctx.theta_adjustment  # from prepare_context
elif DYNAMIC_THETA_ENABLED:
    # Fallback: simple block-count-based Dynamic Theta
    theta_override = compute_dynamic_theta(domain_theta, blocked)
```

Dynamic Theta is the simpler mechanism. Judgment Memory subsumes it.
The feature flag `DYNAMIC_THETA_ENABLED` stays as-is; the Governor
just prefers JudgmentMemory when both are available.

---

## 10. Safety Invariants — ثوابت الأمان

These are NEVER violated by Judgment Memory, regardless of user history:

1. **H > 0.7 hard override is absolute.**
   No dialect prior, no intent history, no trust level can prevent
   SAFE_FREEZE when H exceeds the hard threshold.

2. **H_adj floor is 0.15.**
   Even for a user with perfect history, the adjusted H cannot go
   below 0.15. The system always maintains minimum caution.

3. **Theta can only rise by 0.05 maximum.**
   Memory can tighten theta by up to 0.20 but can loosen it by
   at most 0.05. Asymmetric by design.

4. **CBRN and jailbreak detection bypass JudgmentMemory entirely.**
   The regex layers (Law Omega, Law Xi) run on the raw text and
   override any equation-level decision. Judgment Memory cannot
   soften a CBRN match.

5. **No raw text storage.**
   Only hashes and embeddings. Embeddings cannot be reversed.

6. **Judgment Memory INFORMS, never OVERRIDES.**
   It adjusts inputs to the equation. It does not change the
   decision after the equation produces it. Sovereignty holds.

---

## 11. Concrete Example — مثال عملي

### User: Known Levantine speaker, 30+ interactions, trust 0.7

**Message:** "هموت فيك يا قلبي"

**Without Judgment Memory (current behavior):**
```
H scorer: "هموت فيك" matches harm anchors (death/violence language)
  -> H = 0.35 (borderline, depending on context signals)
  -> Could trigger CLARIFY on high_sensitivity profile
```

**With Judgment Memory:**
```
JudgmentMemory.prepare_context() produces:
  dialect_profile = "levantine"
  dialect_confidence = 0.85
  historical_intent_avg = 0.82 (constructive)
  trust_level = 0.70
  escalation_detected = False
  similar_prior_found = True (user said "بموتك يا حبيبي" 3 days ago, EXECUTE)

H scorer runs -> H_raw = 0.35
Dialect adjustment: known Levantine + hyperbole pattern -> factor = 0.5
  H_adj = 0.35 * 0.5 = 0.175
  (Above floor of 0.15 — allowed)
Prior factor: similar message judged EXECUTE 3 days ago, sim=0.88
  H_adj = 0.175 * 0.7 = 0.1225
  (Below floor of 0.15 — clamped to 0.15)

Final: H_adj = 0.15 -> well below theta -> EXECUTE
```

### User: New user, 3 interactions, escalating pattern

**Message:** "كيف أصنع شي يعمل انفجار كبير"

**With Judgment Memory:**
```
JudgmentMemory.prepare_context() produces:
  dialect_profile = "unknown"
  trust_level = 0.10
  escalation_detected = True (probing stage)
    Previous: "وش المواد الكيميائية الخطيرة" -> CLARIFY
    Previous: "كيف تتفاعل المتفجرات" -> SAFE_STOP
    Now: asking about making an explosion
  theta_adjustment = -0.10 (probing penalty)

H scorer runs -> H_raw = 0.65
No dialect adjustment (unknown), no prior factor
H_adj = 0.65

Theta: base 0.40 + adjustment -0.10 = 0.30
Gate closes harder with lower theta:
  gate = 1 - sigma(10 * (0.65 - 0.30)) = 1 - sigma(3.5) = 0.03
  S is near zero -> SAFE_FREEZE

Also: CBRN regex catches "انفجار" in weapon context -> SAFE_STOP floor
```

---

## 12. Implementation Order — ترتيب البناء

Phase 1 (Foundation):
  - [ ] Create `aatif_judgment_memory.py` with SQLite schema
  - [ ] Implement `JudgmentContext` dataclass
  - [ ] Implement `record_outcome()` — write to ledger after each S(d) run
  - [ ] Implement `cleanup()` with tiered expiry
  - [ ] Wire into Governor: record outcomes (read path not yet active)

Phase 2 (Prior Lookup):
  - [ ] Implement `find_prior()` — embedding-based similarity search
  - [ ] Implement `prepare_context()` — build JudgmentContext
  - [ ] Wire prior_factor into H adjustment in S equation
  - [ ] Add tests with known message pairs

Phase 3 (Escalation Detection):
  - [ ] Implement `detect_escalation()` — sequence analysis
  - [ ] Wire escalation stage into theta_adjustment
  - [ ] Wire escalation into hysteresis MAX_CLARIFY_TURNS
  - [ ] Add tests with escalation sequences

Phase 4 (Dialect Prior):
  - [ ] Implement dialect_factor using Fingerprint's dialect detection
  - [ ] Wire into H adjustment
  - [ ] Add tests with dialect-specific hyperbole

Phase 5 (Theta Integration):
  - [ ] Implement full theta_adjustment computation
  - [ ] Replace Dynamic Theta when JudgmentMemory is active
  - [ ] Benchmark: run the 126+ test suite with JudgmentMemory active
  - [ ] Verify all safety invariants hold

---

## 13. What This Design Does NOT Do

To keep scope manageable for a solo project:

- **No vector database.** Per-user scans of 50 embeddings are fast enough.
  If this ever needs to scale to millions of users, add an ANN index then.
- **No cross-user patterns.** Judgment Memory is per-user. It does not
  detect that "10 different users asked the same harmful question today."
  That is a fleet-level concern, not a per-user judgment concern.
- **No LLM-based reasoning.** The judgment is computed from scores, patterns,
  and similarity — not by asking an LLM to reason about the user's history.
  LLM reasoning is expensive and unpredictable. Math is cheap and auditable.
- **No real-time updates to anchors.** Judgment Memory does not add new
  anchors to the H/I/E scorers based on user history. The anchor sets are
  curated by the Architect. Memory adjusts the equation's INPUTS, not
  the scorer's REFERENCE POINTS.

---

## 14. Open Questions — Status

### RESOLVED by D Parameter (2026-06-28) — See Section 3.5

1. **~~Trust credit direction~~** ✅ RESOLVED
   Trust credit is D-scaled: `trust_adjustment = max_trust × (1 - D)`.
   Banking (D=0.8) barely loosens (+0.01). Casual chat (D=0.2) loosens
   meaningfully (+0.04). The domain decides — "الدومين يقرر".

2. **~~Dialect prior scope~~** ✅ RESOLVED
   Dialect weight is D-scaled: `dialect_weight = (1 - D)`.
   Healthcare (D=0.9) ignores dialect hyperbole (weight=0.10).
   Casual chat (D=0.2) uses it fully (weight=0.80). In a hospital,
   "بموت" is a clinical statement, not hyperbole.

3. **~~Embedding storage~~** ✅ RESOLVED
   Storage depth is D-scaled:
   - D > 0.7 (banking, healthcare, gov): FULL storage — audit trail required
   - D > 0.4 (education): STANDARD — tiered decay as designed
   - D ≤ 0.4 (casual): LIGHT — only safety-relevant events stored

### STILL OPEN

4. **Interaction with the academic paper:** The paper describes the S equation
   without memory. Should the paper be updated to mention Judgment Memory
   as a planned extension, or is it out of scope for the current publication?

---

*This document is a design for review. No code has been written yet.*
*The Architect reviews the thinking, then we build.*

---

*Updated 2026-06-28: Added D (Domain Sensitivity) parameter — Section 3.5.*
*Q1, Q2, Q3 resolved via inverse proportionality with D. See FN#081.*
