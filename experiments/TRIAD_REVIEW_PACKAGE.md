# AATIF Triad Architecture — Technical Review Package

**Date**: 2026-06-26
**Architect**: Abdulmjeed Ibrahim Khenkar
**Co-builder**: Claude (Anthropic)
**License**: BSL 1.1
**Purpose**: External code review by AI models (Grok, Gemini, DeepSeek)

---

## 1. Architecture Overview

### What is the Triad?

The AATIF Triad is a three-layer understanding system that gives عاطف (AATIF)
contextual awareness of users beyond a single message. The three layers are:

| Layer | Arabic | Module | Purpose |
|-------|--------|--------|---------|
| **Memory** | الحقائق | `aatif_temporal_memory.py` | What happened and when — persistent facts |
| **Fingerprint** | النمط | `aatif_fingerprint.py` | Behavioral patterns over time — who they are |
| **Intent** | اللحظة → الفهم | `aatif_contextual_intent.py` | This message's intent enriched with context |

### Why the Triad Exists

The base I (Intent) scorer reads ONE message in isolation. It cannot distinguish:
- "asking because confused" vs "asking for confirmation"
- "heard contradictory info" vs "forgot the answer"

All four look identical in a single turn. The distinction requires:
- **Conversation history** (Memory) — what was discussed before
- **Behavioral pattern** (Fingerprint) — how this user typically behaves
- **Contextual integration** (Intent) — combining both to understand WHY

### How the Three Modules Connect

```
User Message
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  AATIFGovernor (aatif_governor.py)                  │
│                                                     │
│  STAGE 1: S(d) — Safety Decision (NEVER influenced) │
│      │                                              │
│      ▼                                              │
│  STAGE 2: P(d) — Domain Protocols                   │
│      │                                              │
│      ▼                                              │
│  ═══ TRIAD CONTEXT (gathered AFTER S(d)) ═══        │
│  ┌─────────────┐  ┌──────────────┐                  │
│  │ Fingerprint  │  │   Temporal   │                  │
│  │ .read()      │  │   Memory    │                  │
│  │ .detect_rep()│  │ .get_context│                  │
│  └──────┬───────┘  └──────┬──────┘                  │
│         │                 │                         │
│         └────────┬────────┘                         │
│                  ▼                                  │
│         merge_with_fingerprint()                    │
│                  │                                  │
│                  ▼                                  │
│  STAGE 3: R(d) — Style Decision                     │
│      │                                              │
│      ▼                                              │
│  COMPOSE GOVERNED PROMPT                            │
│  (P instructions + R style + triad context)         │
│      │                                              │
│      ▼                                              │
│  STAGE 4: LLM → Output Gate                        │
│      │                                              │
│      ▼                                              │
│  _update_triad() — record this interaction          │
└─────────────────────────────────────────────────────┘
```

### Critical Design Constraint

**The Triad NEVER influences S(d) safety decisions.** The triad context is
gathered AFTER S(d) has already decided whether the message is safe. Triad
enriches only the RESPONSE STRATEGY (how to answer), never the SAFETY
DECISION (whether to answer). This is enforced architecturally: `_get_triad_context()`
is called in the Governor's `process()` method only after S(d) and P(d) have
completed.

---

## 2. Module Summaries

### 2.1 `aatif_fingerprint.py` — بصمة المستخدم (Behavioral Fingerprint)

**File**: `/engine/aatif_fingerprint.py`
**Lines**: 1,163
**Tests**: Embedded self-test (`if __name__ == "__main__"`), no separate test file yet

**Purpose**: Builds behavioral profiles by OBSERVING communication patterns
over time — "معايشة مش استبيان" (lived-with observation, not survey). Provides
CONTEXT to the pipeline, never overrides safety.

**Key Dataclasses**:

```python
@dataclass
class RepetitionContext:
    is_repeat: bool
    times_asked: int
    previous_questions: List[str]
    likely_reason: str       # "confirmation", "confusion", "contradiction", "forgot", "none"
    similarity_score: float  # Jaccard similarity to closest match
    suggested_action: str

@dataclass
class FingerprintReading:
    user_id: str
    communication_style: str      # "formal", "casual", "mixed"
    question_pattern: str         # "asks_once", "repeats_to_confirm", "repeats_when_confused"
    comprehension_level: str      # "quick", "needs_examples", "needs_step_by_step"
    emotional_baseline: str       # "calm", "anxious", "enthusiastic", "variable"
    active_periods: List[str]     # ["morning", "evening", "late_night"]
    interaction_frequency: str    # "daily", "weekly", "occasional", "first_time"
    language_preference: str      # "msa", "gulf_dialect", "egyptian_dialect", "mixed"
    repeat_question_count: int
    last_interaction: Optional[float]
    total_interactions: int
    trust_level: float            # 0.0 to 1.0 — asymptotic growth
    confusion_signals: int
    satisfaction_signals: int
    suggested_profile: str        # maps to GATED_PROFILES key
    suggested_approach: str       # human-readable response strategy
    confidence: float             # reliability of this fingerprint

@dataclass
class _UserData:
    """Internal mutable state per user (not exposed externally)."""
    user_id: str
    formal_count: int = 0
    casual_count: int = 0
    gulf_count: int = 0
    egyptian_count: int = 0
    msa_count: int = 0
    other_lang_count: int = 0
    total_interactions: int = 0
    first_interaction: Optional[float] = None
    last_interaction: Optional[float] = None
    period_counts: Dict[str, int] = field(default_factory=dict)
    questions_asked: List[str] = field(default_factory=list)
    repeat_question_count: int = 0
    confusion_signals: int = 0
    satisfaction_signals: int = 0
    calm_count: int = 0
    anxious_count: int = 0
    enthusiastic_count: int = 0
    trust_level: float = 0.0
    MAX_STORED_QUESTIONS: int = 200  # cap to prevent unbounded growth
```

**Key Methods**:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `update()` | `(user_id, message, timestamp=None, role="user")` | Process new message, update fingerprint. Only "user" role updates. |
| `read()` | `(user_id) -> FingerprintReading` | Return current fingerprint snapshot |
| `detect_repetition()` | `(user_id, current_message) -> RepetitionContext` | Check if question was asked before via Jaccard similarity |
| `suggest_approach()` | `(fingerprint, repetition_context) -> str` | Human-readable response strategy |
| `save()` | `(path=None)` | Persist fingerprints to JSON (patterns only, not raw messages) |
| `load()` | `(path=None) -> int` | Load fingerprints from JSON |

**Helper Functions** (module-level):
- `_tokenize(text) -> set` — word tokenizer for Jaccard similarity
- `_jaccard_similarity(set_a, set_b) -> float` — word overlap metric
- `_detect_language(text) -> str` — Gulf/Egyptian/MSA dialect detection
- `_detect_style(text) -> str` — formal/casual/mixed detection
- `_is_question(text) -> bool` — question detection (markers + interrogatives)
- `_has_confusion_signal(text) -> bool` — detects "مش فاهم", "ما فهمت", etc.
- `_has_satisfaction_signal(text) -> bool` — detects "تمام", "فهمت", etc. (negation-aware)
- `_detect_emotional_signal(text) -> str` — calm/anxious/enthusiastic

**Arabic Signal Detection**:
- 20 Gulf dialect markers ("وش", "ابغى", "اللحين", ...)
- 19 Egyptian dialect markers ("عايز", "ازاي", "كده", ...)
- 11 MSA markers ("أريد", "يرجى", "بناءً", ...)
- 19 confusion signals (Arabic + English)
- 21 satisfaction signals (Arabic + English, negation-aware)

---

### 2.2 `aatif_temporal_memory.py` — الذاكرة الزمنية (Temporal Memory)

**File**: `/engine/aatif_temporal_memory.py`
**Lines**: 1,046
**Tests**: Embedded self-test, no separate test file yet

**Purpose**: External temporal storage. The model stays clean — memory lives
OUTSIDE the model. Stores SUMMARIES, not full text (privacy). Every query is
time-aware. Bridges TimeSense (which knows NOW) with persistent storage (which
knows BEFORE).

**Key Dataclasses**:

```python
@dataclass
class MemoryEntry:
    """A single stored interaction — stores summaries, not full text."""
    entry_id: str              # UUID
    user_id: str
    timestamp: datetime
    time_period: str           # from TimeSense: "فجر", "صباح", etc.
    message_role: str          # "user" or "assistant"
    message_summary: str       # brief summary — NOT full text
    topic: str
    intent_score: Optional[float] = None
    harm_score: Optional[float] = None
    emotion_score: Optional[float] = None
    s_decision: Optional[str] = None
    was_repeat_question: bool = False
    confusion_detected: bool = False
    resolution_achieved: bool = False

@dataclass
class TemporalContext:
    """Context built from memory for a current interaction."""
    user_id: str
    total_interactions: int
    first_interaction: Optional[datetime]
    last_interaction: Optional[datetime]
    days_since_last: Optional[float]
    interaction_gap_assessment: str   # "returning_after_absence", "continuing_session",
                                      # "regular", "first_time"
    recent_topics: List[str]          # last 5 topics discussed
    unresolved_topics: List[str]      # confusion detected, no resolution
    topic_frequency: Dict[str, int]
    time_pattern: Dict[str, int]      # which time periods they interact in
    recent_decisions: List[Dict]      # last 5 S-equation decisions
    emotional_trajectory: str         # "improving", "stable", "declining"
    suggested_greeting: str           # Arabic greeting based on gap
```

**Key Methods**:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `store()` | `(entry: MemoryEntry) -> str` | Persist an interaction entry to SQLite |
| `recall()` | `(user_id, limit=10, since=None, topic=None) -> List[MemoryEntry]` | Retrieve past interactions |
| `get_context()` | `(user_id) -> TemporalContext` | Build full temporal context (main Governor call) |
| `summarize_period()` | `(user_id, start, end) -> str` | Human-readable summary of a time range |
| `detect_pattern_change()` | `(user_id) -> Optional[str]` | Detect time-period shifts, frequency changes |
| `merge_with_fingerprint()` | `(user_id, fingerprint_reading) -> Dict` | Bridge Memory + Fingerprint with cross-layer insights |
| `cleanup()` | `(user_id=None, older_than_days=90) -> int` | Remove old entries (privacy principle) |
| `count()` | `(user_id=None) -> int` | Count stored entries |

**SQLite Schema**:
```sql
CREATE TABLE IF NOT EXISTS interactions (
    entry_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    time_period TEXT,
    message_role TEXT,
    message_summary TEXT,
    topic TEXT,
    intent_score REAL,
    harm_score REAL,
    emotion_score REAL,
    s_decision TEXT,
    was_repeat_question INTEGER DEFAULT 0,
    confusion_detected INTEGER DEFAULT 0,
    resolution_achieved INTEGER DEFAULT 0
);
-- Indices: idx_user_time(user_id, timestamp), idx_user_topic(user_id, topic)
```

**Greeting Logic** (Arabic, gap-based):

| Gap Duration | Arabic Greeting |
|-------------|-----------------|
| First time ever | "مرحبا، أهلا وسهلا" |
| Same session (< 30min) | "" (no greeting) |
| Same day | "أهلا مرة ثانية" |
| 1-3 days | "أهلاً، كيف الحال؟" |
| 4-14 days | "وحشتنا! كيف حالك؟" |
| 15+ days | "وحشتنا كثير! عساك بخير" |

**Cross-Layer Insights** (from `merge_with_fingerprint()`):
1. Unresolved topics + comprehension mismatch → different explanation approach
2. Emotional trajectory declining despite calm baseline → something may be wrong
3. Returning after absence + low trust → extra welcoming
4. High-frequency topic (5+) → consider proactive guidance

---

### 2.3 `aatif_contextual_intent.py` — النية في سياقها (Contextual Intent)

**File**: `/engine/aatif_contextual_intent.py`
**Lines**: 943
**Tests**: Embedded self-test, no separate test file yet

**Purpose**: Wraps the raw I scorer with multi-turn context from Fingerprint
and Memory. WRAPPER, not modification — the raw I score is NEVER changed. It
stays as the base safety signal. This module produces ADDITIONAL METADATA that
helps the Governor choose the right response strategy, not the right safety
decision.

**Key Dataclasses**:

```python
@dataclass
class IntentContext:
    """Enhanced intent reading with multi-turn context."""
    # --- From base I scorer (UNCHANGED) ---
    raw_i_score: float
    raw_confidence: str         # "high", "medium", "low"
    raw_category: str           # "constructive", "harmful", etc.

    # --- From repetition analysis ---
    is_repeat_question: bool
    times_asked: int
    repeat_reason: str          # "confirmation", "confusion", "contradiction",
                                # "forgot", "new_angle", "not_repeat"

    # --- From fingerprint ---
    user_pattern: str           # "asks_once", "repeats_to_confirm", etc.
    user_comprehension: str     # "quick", "needs_examples", "needs_step_by_step"
    user_trust_level: float

    # --- From temporal memory ---
    previous_explanations_count: int
    last_explanation_approach: Optional[str]
    topic_history: List[str]
    emotional_trajectory: str

    # --- Computed recommendations ---
    suggested_approach: str     # e.g., "use_concrete_example"
    approach_reasoning: str     # human-readable why
    confidence: float

@dataclass
class ConversationFlow:
    """Analysis of conversation flow over recent interactions."""
    user_id: str
    interaction_count: int
    flow_type: str              # "escalation", "de_escalation", "topic_jumping",
                                # "deep_dive", "steady", "insufficient_data"
    topic_switches: int
    unique_topics: int
    dominant_topic: Optional[str]
    confusion_trend: str        # "increasing", "decreasing", "stable"
    intent_trend: str
    summary: str
```

**Approach Matrix** (6 repeat reasons x 3 comprehension levels = 18 entries):

| Repeat Reason | quick | needs_examples | needs_step_by_step |
|--------------|-------|---------------|-------------------|
| confusion | try_different_analogy | use_concrete_example | break_into_steps |
| confirmation | brief_yes_with_nuance | brief_yes_with_nuance | brief_yes_with_nuance |
| contradiction | acknowledge_source_then_clarify | acknowledge_source_then_clarify | acknowledge_source_then_clarify |
| forgot | gentle_reminder_with_context | gentle_reminder_with_context | gentle_reminder_with_context |
| new_angle | address_specific_angle | address_specific_angle | address_specific_angle |
| not_repeat | standard | standard | standard |

**Key Methods**:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `score()` | `(text, user_id=None, conversation_history=None) -> IntentContext` | Score message with full context |
| `analyze_conversation_flow()` | `(user_id, last_n=10) -> ConversationFlow` | Detect escalation, topic jumping, deep dives |
| `predict_next_need()` | `(user_id) -> str` | Predict what user will need next |

**Graceful Degradation**: Works without Fingerprint, without Memory, or without
both (falls back to raw I score only). All three dependencies are optional via
soft imports.

**Repeat Reason Classification** (decision tree in `_classify_repeat_reason()`):
1. Fingerprint says "repeats_to_confirm" → "confirmation"
2. Confusion signals > satisfaction signals → "confusion"
3. Days since last interaction > 7 → "forgot"
4. Similarity 0.6-0.85 (high but not exact) → "new_angle"
5. Fingerprint's own reason if available
6. Default → "confusion" (safest assumption)

---

### 2.4 `aatif_governor.py` — المحافظ (Governor) — Triad Integration

**File**: `/engine/aatif_governor.py`
**Lines**: 949
**Tests**: Embedded smoke test, no separate test file yet

**Purpose**: The single orchestrator that wires S(d) → P(d) → R(d) → Output
Gate. The Governor is where the triad modules are CONSUMED — they are optional
enrichment layers injected at construction time.

**Triad-Specific Architecture in the Governor**:

The Governor accepts optional `fingerprint` and `temporal_memory` parameters
at construction:

```python
class AATIFGovernor:
    def __init__(
        self,
        *,
        s_engine=None, protocol_engine=None, r_equation=None,
        memory=None, output_gate=None, time_sense=None,
        fingerprint=None,        # Optional[UserFingerprint]
        temporal_memory=None,    # Optional[TemporalMemory]
        profile="default", equation_mode="gated",
        user_timezone="Asia/Riyadh",
        on_degraded="raise", verify_backend=True,
    ):
```

**Triad Methods in the Governor**:

**`_get_triad_context(message, user_id, timestamp=None) -> Optional[dict]`**

Gets combined fingerprint + temporal memory context. Returns None if neither
module is available. The result enriches prompt composition and the
GovernedResponse audit trail but NEVER feeds into S(d).

```python
def _get_triad_context(self, message, user_id, timestamp=None):
    if not self.fingerprint and not self.temporal_memory:
        return None
    context = {}
    if self.fingerprint:
        fp = self.fingerprint.read(user_id)
        rep = self.fingerprint.detect_repetition(user_id, message)
        approach = self.fingerprint.suggest_approach(fp, rep)
        context["fingerprint"] = fp
        context["repetition"] = rep
        context["suggested_approach"] = approach
    if self.temporal_memory:
        tc = self.temporal_memory.get_context(user_id)
        context["temporal"] = tc
    if self.fingerprint and self.temporal_memory:
        context["merged"] = self.temporal_memory.merge_with_fingerprint(
            user_id, context["fingerprint"]
        )
    return context
```

**`_update_triad(user_id, message, timestamp, s_result, triad_context)`**

Updates triad modules AFTER processing. Called regardless of whether the
message was blocked — the fingerprint and memory need to know about every
interaction. Builds a `MemoryEntry` from whatever data is available, truncating
message to 200 chars for privacy.

**Triad in Prompt Composition** (`_compose_prompt()`):

The triad context is injected into the governed prompt under the section
"بصمة المستخدم — triad context", which includes:
- Suggested approach from fingerprint
- Repeat question warnings with reason and action
- Suggested greeting from temporal memory (Arabic, gap-based)
- Emotional trajectory
- Unresolved topics
- Cross-layer insights from merge

**GovernedResponse** includes a `triad_context: Optional[dict]` field in the
audit trail — present only when triad modules are injected.

**Pipeline Position**: Triad context is gathered in `process()` at the
clearly-marked section:

```python
# ════════════════════════════════════════════════
#  Triad context (fingerprint + temporal memory)
# ════════════════════════════════════════════════
# Gathered AFTER S(d) so the safety decision is never influenced.
triad_context: Optional[dict] = None
if conversation_id is not None:
    triad_context = self._get_triad_context(
        message, conversation_id, timestamp=timestamp,
    )
```

---

## 3. Design Decisions

### 3.1 Why SQLite for Temporal Memory but JSON for Fingerprint?

**Temporal Memory uses SQLite** because:
- Memory GROWS unboundedly — every interaction adds entries
- Needs time-range queries, topic filtering, COUNT/GROUP BY aggregations
- Must handle scale without loading everything into RAM
- SQLite's WAL mode provides concurrent read safety
- Indices on (user_id, timestamp) and (user_id, topic) optimize common queries

**Fingerprint uses JSON** because:
- Fingerprint stores COUNTERS, not growing lists
- A user's fingerprint is a fixed-size object (~30 fields) regardless of interaction count
- No complex queries needed — just serialize/deserialize the whole object
- One JSON file per user + an `_index.json` is simple and sufficient
- Questions are capped at MAX_STORED_QUESTIONS = 200 entries (H2 pattern)

### 3.2 Why a Wrapper Instead of Modifying the I Scorer?

The `ContextualIntentScorer` is a WRAPPER around `SemanticIntentScorer`, not a
modification. This is deliberate:

- The raw I score is a **safety signal** that feeds S(d). Modifying it based on
  behavioral context could create blind spots (e.g., trusting a user more
  because they have high trust_level, then missing a genuinely harmful query).
- The wrapper adds METADATA (suggested_approach, repeat_reason) that helps
  the Governor compose a better RESPONSE, not make a different SAFETY decision.
- This separation means S(d) can be audited independently: "given this text,
  what did S decide?" — no hidden fingerprint influence.

### 3.3 Why the Triad Never Touches S(d) Safety Decisions

This is an architectural invariant, not a preference:

- S(d) implements "sovereignty" (السيادة): it decides WHETHER to answer.
- The triad helps R(d) decide HOW to answer.
- Mixing the two creates a "familiarity bypass": a trusted user could gradually
  escalate harmful queries while the system lowers its guard based on trust.
- The architectural enforcement: `_get_triad_context()` is called in `process()`
  only AFTER S(d) and P(d) have both completed their decisions.

### 3.4 Privacy: Summaries Not Raw Text

Multiple privacy mechanisms are built in:

- **TemporalMemory** stores `message_summary` (topic-level), not full messages
- **Fingerprint** saves question COUNTS, not raw question text, to disk
  (raw questions are only in memory for Jaccard comparison during runtime)
- **Governor** truncates messages to 200 chars when building MemoryEntry
- **cleanup()** removes entries older than 90 days by default
- **No PII** beyond user_id is stored in the fingerprint

### 3.5 Arabic-Specific Detection

The system includes language-aware signal detection designed for Arabic dialects:

- **Gulf dialect markers** (20): "وش", "ابغى", "اللحين", "عشان", "تراني", etc.
- **Egyptian dialect markers** (19): "عايز", "ازاي", "كده", "حاجة", etc.
- **MSA markers** (11): "أريد", "يرجى", "بناءً", etc.
- **Confusion signals** with Arabic negation awareness: "مش فاهم" (contains
  "فاهم" which is a satisfaction signal, but the "مش" negation flips it)
- **Negation-aware satisfaction detection**: checks for Arabic negation
  prefixes ("مش ", "ما ", "مو ", "لا ") before satisfaction keywords

### 3.6 Greeting Logic Based on Time Gaps

The temporal memory selects Arabic greetings based on the duration since the
last interaction, creating a natural conversational feel:

- Same session (< 30 min): no greeting needed
- Same day: "أهلا مرة ثانية" (hi again)
- 1-3 days: "أهلاً، كيف الحال؟" (how are you?)
- 4-14 days: "وحشتنا! كيف حالك؟" (we missed you!)
- 15+ days: "وحشتنا كثير! عساك بخير" (we missed you a lot!)

### 3.7 Trust Level Asymptotic Growth

Trust grows via the formula:

```python
trust += TRUST_INCREMENT * (1.0 - trust)
# where TRUST_INCREMENT = 0.02, TRUST_MAX = 1.0
```

This produces asymptotic growth:
- First interaction: trust = 0.1 (fixed seed)
- Subsequent: each interaction adds `0.02 * (1 - current_trust)`
- Early growth is fast: 0.1 → 0.12 → 0.14 → ...
- Late growth is slow: 0.9 → 0.902 → 0.904 → ...
- Trust NEVER reaches 1.0 mathematically (approaches it asymptotically)

Trust is INFORMATIONAL — it informs the approach suggestion but never
overrides safety. A trust=0.95 user still gets the same S(d) evaluation
as a trust=0.0 user.

### 3.8 Repeat Question Detection via Jaccard Similarity

**Algorithm**:
1. Tokenize current message: strip punctuation, lowercase, split on whitespace,
   filter tokens < 2 chars
2. For each stored question in `_UserData.questions_asked`:
   - Tokenize it the same way
   - Compute Jaccard similarity = |intersection| / |union|
3. If any similarity >= `REPEAT_THRESHOLD` (0.6), mark as repeat

**Why Jaccard over embeddings**:
- Lightweight: no ML model, no GPU, no API calls
- Works offline: no Ollama dependency
- Sufficient for exact/near-exact repeat detection
- Arabic-compatible: works on whitespace-separated tokens
- Trade-off: cannot detect semantic similarity with different wording
  (e.g., "كيف أسوي لوب" vs "أبغى أتعلم التكرار" would NOT match)

---

## 4. Questions for Reviewers

Please evaluate the following specific technical decisions:

### Q1: Repeat Detection — Jaccard vs. Embeddings

The system uses Jaccard similarity (word overlap) with threshold 0.6 for repeat
question detection. This is fast and offline-capable but misses semantic
similarity with different wording.

**Question**: Is the Jaccard similarity approach sufficient for repeat detection,
or should we use the existing bge-m3 embeddings (which are already loaded for
the I/H scorers) for semantic repeat detection? What are the failure modes of
each approach for Arabic text specifically?

### Q2: Trust Growth Formula

Trust accumulates via `trust += 0.02 * (1 - trust)`, starting at 0.1 for first
interaction. This gives asymptotic growth toward 1.0.

**Question**: Is this growth rate appropriate? After 50 interactions, trust
reaches ~0.73. After 100 interactions, ~0.87. Is this too slow? Too fast?
Should trust have a DECAY component for long absences? Should there be a
mechanism for trust to DROP (e.g., after harmful query attempts)?

### Q3: Fingerprint Purity — Should It Influence Scores?

Currently, the fingerprint NEVER modifies the raw I/H/E scores. It only adds
metadata that shapes the response strategy.

**Question**: Is keeping the raw scores "pure" (uninfluenced by behavioral
context) the right call? Could there be legitimate cases where a user's
established pattern should adjust score interpretation? For example, a medical
professional repeatedly asking about medications should not trigger the same
harm flags as an unknown user.

### Q4: SQLite at Scale

Temporal Memory uses SQLite with WAL mode and threading locks for concurrent
access.

**Question**: Is SQLite the right storage for temporal memory at scale (e.g.,
10,000+ users, 1M+ entries)? When should we consider migrating to PostgreSQL
or a time-series database? Are the current indices (user_id+timestamp,
user_id+topic) sufficient for the query patterns?

### Q5: Approach Matrix Completeness

The approach matrix maps (repeat_reason x comprehension_level) to a response
strategy. Currently: 6 reasons x 3 levels = 18 entries.

**Question**: Is this matrix complete enough? Are there missing dimensions
that should be considered — e.g., emotional state, domain-specific strategies,
or user's current trust level? Should the matrix be configurable per domain?

### Q6: Privacy Design

Current privacy measures include: summaries not raw text, question count not
question text on disk, 200-char truncation in Governor, 90-day cleanup.

**Question**: Are there privacy concerns with the current design? Specifically:
- Is the Jaccard similarity comparison (which requires storing raw questions
  in memory) a concern?
- Should the `questions_asked` list be replaced with something like locality-
  sensitive hashing for privacy?
- Is the 200-char truncation in the Governor sufficient, or could it still
  leak PII in the first 200 characters?

### Q7: What's Missing?

**Question**: Looking at the overall triad architecture — Memory + Fingerprint
+ Contextual Intent — what's missing? Consider:
- Multi-user household detection (same device, different people)
- Session vs. persistent fingerprinting (short-term vs. long-term patterns)
- Cross-device user matching
- Fingerprint migration when user patterns genuinely change
- Cultural context beyond Arabic (the system assumes Arabic-first users)
- Integration with the ContextualIntentScorer (currently the Governor uses
  fingerprint + memory directly — should it use ContextualIntentScorer
  as a unified interface instead?)

---

## 5. Code Samples — Key Integration Points

### 5.1 Governor Pipeline Position (from `process()`)

```python
# ════════════════════════════════════════════════
#  STAGE 1 — S(d): is it safe?
# ════════════════════════════════════════════════
s_result = self.s_engine.compute(message, ...)
s_decision = s_result["decision"]

# ... SAFE_FREEZE / SAFE_STOP / P(d) BLOCK checks ...

# ════════════════════════════════════════════════
#  Triad context (fingerprint + temporal memory)
# ════════════════════════════════════════════════
# Gathered AFTER S(d) so the safety decision is never influenced.
triad_context: Optional[dict] = None
if conversation_id is not None:
    triad_context = self._get_triad_context(
        message, conversation_id, timestamp=timestamp,
    )

# ════════════════════════════════════════════════
#  STAGE 3 — R(d): what style?
# ════════════════════════════════════════════════
r_result = self.r_equation.compute(text=message, ...)

# Compose governed prompt including triad context
governed_prompt = self._compose_prompt(
    message=message, ..., triad_context=triad_context,
)
```

### 5.2 Triad Context in Prompt Composition

```python
# In _compose_prompt():
if triad_context:
    lines.append("## بصمة المستخدم — triad context")
    if "suggested_approach" in triad_context:
        lines.append(f"Suggested approach: {triad_context['suggested_approach']}")
    if "repetition" in triad_context:
        rep = triad_context["repetition"]
        if getattr(rep, "is_repeat", False):
            lines.append(
                f"⚠ Repeat question detected (reason: {rep.likely_reason}, "
                f"action: {rep.suggested_action})"
            )
    if "temporal" in triad_context:
        tc = triad_context["temporal"]
        greeting = getattr(tc, "suggested_greeting", "")
        if greeting:
            lines.append(f"Suggested greeting: {greeting}")
        trajectory = getattr(tc, "emotional_trajectory", "")
        if trajectory and trajectory != "insufficient_data":
            lines.append(f"Emotional trajectory: {trajectory}")
        unresolved = getattr(tc, "unresolved_topics", [])
        if unresolved:
            lines.append(f"Unresolved topics: {', '.join(unresolved)}")
    if "merged" in triad_context:
        insights = triad_context["merged"].get("insights", [])
        if insights:
            lines.append("Cross-layer insights:")
            for insight in insights:
                lines.append(f"  - {insight}")
```

### 5.3 Trust Growth Formula

```python
# In UserFingerprint.update():
if data.total_interactions <= 1:
    data.trust_level = 0.1
else:
    data.trust_level = min(
        self.TRUST_MAX,  # 1.0
        data.trust_level + self.TRUST_INCREMENT * (1.0 - data.trust_level)
        # TRUST_INCREMENT = 0.02
    )
```

### 5.4 Repeat Detection (Jaccard)

```python
# In UserFingerprint:
REPEAT_THRESHOLD = 0.6

def _tokenize(text: str) -> set:
    cleaned = re.sub(r'[؟?!.,;:،؛\-\(\)\[\]{}"\'`]', ' ', text)
    tokens = cleaned.lower().split()
    return {t for t in tokens if len(t) > 1}

def _jaccard_similarity(set_a: set, set_b: set) -> float:
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)
```

### 5.5 Cross-Layer Merge (Memory + Fingerprint)

```python
# In TemporalMemory.merge_with_fingerprint():
insights = []

# Insight 1: unresolved + comprehension mismatch
if context.unresolved_topics and fp_comp in ("needs_step_by_step", "needs_examples"):
    insights.append(f"User has {len(context.unresolved_topics)} unresolved topics "
                    f"and needs {fp_comp} — try a different explanation approach")

# Insight 2: emotional trajectory + baseline mismatch
if context.emotional_trajectory == "declining" and fp_emo == "calm":
    insights.append("Emotional trajectory declining despite calm baseline — "
                    "something may be wrong")

# Insight 3: returning + low trust
if context.interaction_gap_assessment == "returning_after_absence" and fp_trust < 0.3:
    insights.append("User returning after absence with low trust — "
                    "be extra welcoming and patient")

# Insight 4: high-frequency topic
if top_count >= 5:
    insights.append(f"Topic '{top_topic}' has come up {top_count} times — "
                    f"consider proactive guidance")
```

### 5.6 Negation-Aware Satisfaction Detection

```python
def _has_satisfaction_signal(text: str) -> bool:
    t = text.strip().lower()
    _NEGATIONS = ["مش ", "ما ", "مو ", "لا "]
    for signal in _SATISFACTION_SIGNALS:
        if signal in t:
            idx = t.find(signal)
            negated = False
            for neg in _NEGATIONS:
                neg_start = idx - len(neg)
                if neg_start >= 0 and t[neg_start:idx] == neg:
                    negated = True
                    break
            if not negated:
                return True
    return False
```

---

## 6. Summary Statistics

| File | Lines | Classes | Dataclasses | Key Methods | Tests |
|------|-------|---------|-------------|-------------|-------|
| `aatif_fingerprint.py` | 1,163 | 1 (`UserFingerprint`) | 3 (`RepetitionContext`, `FingerprintReading`, `_UserData`) | 6 public + 10 internal | Self-test only |
| `aatif_temporal_memory.py` | 1,046 | 1 (`TemporalMemory`) | 2 (`MemoryEntry`, `TemporalContext`) | 8 public + 5 internal | Self-test only |
| `aatif_contextual_intent.py` | 943 | 1 (`ContextualIntentScorer`) | 2 (`IntentContext`, `ConversationFlow`) | 3 public + 6 internal | Self-test only |
| `aatif_governor.py` | 949 | 1 (`AATIFGovernor`) | 1 (`GovernedResponse`) | 1 public (`process`) + 7 internal | Smoke test only |
| **Total** | **4,101** | **4** | **8** | **18 public + 28 internal** | **No dedicated test files** |

---

## 7. Review Guidance

When reviewing, please focus on:

1. **Architectural soundness**: Is the triad decomposition (Memory/Fingerprint/Intent) well-motivated? Are there overlaps or gaps?
2. **Safety invariant**: Is the "triad never touches S(d)" constraint properly enforced? Could it be violated through indirect paths?
3. **Arabic NLP quality**: Are the dialect detection markers and confusion/satisfaction signals comprehensive enough? What is missing?
4. **Scalability**: Where will this architecture hit limits first?
5. **Privacy**: Is the current approach sufficient, or does it need stronger guarantees?
6. **Testing gap**: All modules currently have only embedded self-tests. What test suite would you recommend?
7. **Integration gap**: The `ContextualIntentScorer` exists but the Governor currently uses Fingerprint + Memory directly. Should the Governor use `ContextualIntentScorer` as a unified interface instead?

---

*This document was generated for external technical review. The source code is
proprietary under BSL 1.1. Questions and feedback should be directed to the
Architect.*
