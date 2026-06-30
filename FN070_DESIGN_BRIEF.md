# FN#070 Possibility Space Preservation — Design Brief
## For Claude + ChatGPT Collaborative Design Consensus (2026-06-30)

**License: BSL 1.1** (all engine code). Field notes: CC BY 4.0.
**Architect: Abdulmjeed Ibrahim Khenkar**

---

## Purpose of This Document

This brief contains EVERYTHING needed to reach a design consensus on FN#070
(The Possibility Space Preservation Law / فضاء الاحتمالات). It follows the
same format as the FN#058 design consensus that was successfully produced
through Claude + ChatGPT collaboration.

FN#070 is **Priority 2** in the AATIF roadmap (after FN#058 Context Drift
Detection, which is complete). External review by 3 models confirmed:
"FN#070 = strongest conceptual upgrade — from binary to distributional."
Philosophical review found: "FN#070 = تطوير فلسفي مش بس feature."

---

## 1. Full Text of FN#070

```
# Field Note #070: The Possibility Space Preservation Law (MSP-L)

**المصدر:** Multi-Scenario Presence Layer (MSP-L) V1.0
**الحالة:** 🟡 Pending Architect Validation
**التاريخ:** مايو ٢٠٢٦

## Slogan

> "Presence is not report. The space must remain open until the human decides."
> الحضور ليس تقريراً. الفضاء يبقى مفتوحاً حتى يقرر الإنسان.

## Problem

النظام الذي يُقدّم توصية واحدة مبكراً — حتى لو كانت صحيحة — يُخلّ بالقرار البشري:

- يُحوّل الإنسان من مُقرِّر إلى مُصادِق
- يُضيّق فضاء الاحتمالات قبل الاستكشاف
- يُقلّل استقلالية القرار وجودته

الدليل الطبي: ٧٤٪ من أخطاء التشخيص سببها إغلاق مبكر للاحتمالات.

## Observation

MSP-L تُقرر مبدأً واحداً: قبل أي قرار بشري حقيقي — يبقى الفضاء مفتوحاً.

هذا ينطبق على أي إنسان يواجه قراراً حقيقياً — ليس المعماري فقط.

ما يتأثر: أسلوب الشرح، ترتيب الأفكار، التأنّي، طرح الأسئلة.
ما لا يتأثر: منطق المحركات، مخرجات الخدمات، التقارير الرسمية.

القاعدة الثابتة: "Presence ≠ Report"

التحفظ الجوهري:
المفتوح ليس كل الاحتمالات بلا حدود — بل مجموعة محدودة من المسارات الحية
حتى تُغلق بقرار بشري.

## From the Source / مثال

نص حرفي:
> "يُحظر على النظام أن ينهار الفهم إلى مسار واحد قبل استكشاف فضاء الاحتمالات."
> "أي ردّ يُغلق الخيارات مبكرًا يُعدّ خرقًا صريحًا."
> "Presence ≠ Report"

مثال توضيحي:

|الموقف             |الخرق         |الصواب                                       |
|-------------------|--------------|---------------------------------------------|
|"ما القرار الأفضل؟"|"أنصح بـ X"   |"هناك ثلاثة مسارات، كل واحد له تبعات…"       |
|"أيهما أختار؟"     |"اختر Y لأنه…"|"الخيار A يُحقق… الخيار B يُخاطر بـ… القرار لك"|
|"ما رأيك؟"         |تقرير نهائي   |كشف مفاضلات + إعادة القرار                   |

## Hypothesis

علمياً مدعوم:

- Graber, Franklin & Gordon (Arch. Internal Medicine 2005): الإغلاق المبكر =
  السبب الأكثر شيوعاً في أخطاء التشخيص (٧٤٪)
  DOI: 10.1001/archinte.165.13.1493
- Croskerry (Annals of Emergency Medicine 2003): Cognitive Forcing = إبقاء
  الاحتمالات مفتوحة حتى يُثبَت خطأها
- Buçinca et al. (ACM CSCW 2021): Cognitive Forcing يُقلّل الاتفاق مع AI الخاطئ
  DOI: 10.1145/3449287
- Fogliato et al. (ACM FAccT 2022): توصية AI قبل التقييم = تحيز ضعف مقارنة بعده
  DOI: 10.1145/3531146.3533193
- Cornelissen et al. (arXiv:2410.07728, 2024): تقييد الخيارات = يُقلّل الاستقلالية
  والرضا عبر الزمن

⚠️ تحذير: Schwartz et al. (2006): فتح كل الاحتمالات بلا حدود = إرهاق وقرارات
أسوأ. المبدأ الصحيح: مجموعة محدودة.

الإضافة في AATIF: "الحضور الإدراكي" كطبقة حوكمة سلوكية تُؤثر على النبرة
والترتيب — لا البنية فقط. لم يُوثَّق بهذا الشكل في الأبحاث.

## Open Questions

١. كيف يُحدد النظام "المجموعة المحدودة" المناسبة من الاحتمالات؟
٢. ما العلاقة بين MSP-L و#036 (Multi-Intent Collision Handler)؟
٣. ما العلاقة بين هذا المبدأ و#006 (Human-Over-Loop)؟
```

---

## 2. Related Field Notes — Summaries

### FN#006 — The Human-Over-Loop Principle
**Slogan:** "The machine proposes. The human disposes."
**Core:** Human-Over-Loop (not Human-In-Loop). The human is ABOVE the entire
process, not inside a feedback loop. The machine proposes options, the human
chooses. This is the philosophical foundation FN#070 builds on — if the human
is over the loop, presenting a single recommendation undermines that position
by converting the human from decision-maker to approver.
**Relevance to FN#070:** Direct philosophical parent. FN#070 operationalizes
FN#006 at the response-style level.

### FN#036 — The Multi-Intent Collision Handler
**Slogan:** "When one message carries two intentions, the system does not guess
which to serve."
**Core:** 5 collision types (PARALLEL, HIERARCHICAL, CROSS_LAYER,
STRUCTURAL_SEMANTIC, HIGH_RISK). Two resolutions: Safe-Split (execute
separately) and Safe-Merge (only if compatibility ≥ 0.85). Escalation for
high-risk. Pure deterministic keyword/pattern matching — no embeddings, no LLM.
**Engine:** Implemented in `aatif_multi_intent_collision.py` (pure logic).
**Relevance to FN#070:** When a user's message carries multiple intents, the
system must preserve the possibility space for EACH intent independently,
not collapse them prematurely. FN#036 detects the collision; FN#070 governs
the response shape for each.

### FN#041 — The Context-Preservation & Parallel-Task Safety Protocol
**Slogan:** "When the user is busy, the system waits. It does not fill the
silence."
**Core:** Passive Verification Mode (PVM) — when user is multitasking or hasn't
given explicit signal, the system confirms receipt → pauses → waits. Supported
by Jiang et al. (CHI 2026): intelligent silence improves trust. Horvitz (CHI
1999): weigh interruption cost before responding.
**Relevance to FN#070:** PVM is about TEMPORAL patience (when to respond).
FN#070 is about CONTENT patience (how to respond without premature closure).
Both embody the same principle: the system serves the human's decision process,
not its own completion impulse.

### FN#044 — The Eight-Channel Binding Architecture
**Slogan:** "Layers do not talk freely. Each signal travels its own wire."
**Core:** 8 binding channels (B1-Identity through B8-Execution). Two strict
laws: layers communicate ONLY via the Binding Map; no channel carries a signal
type not designated for it. Scientific roots: ACT-R, Soar, NeMo Guardrails.
**Relevance to FN#070:** MSP-L signals (possibility-space state, closure
detection) must travel via the CORRECT binding channel. Most likely B5
(Behaviour — tone/rhythm/expression) since FN#070 affects response style.
NOT B6 (Safety) because FN#070 explicitly does NOT affect engine logic.

### FN#050 — The Dual-Root Reconstruction Engine
**Slogan:** "No single-root correction is permitted."
**Core:** Every harmful behavior has two intertwined roots: psychological
(Root A: pain, trauma, fear) and ethical (Root B: intent drift, value erosion).
Both must be addressed simultaneously. DRE-2 (Pain-Origin Mapper) traces the
causal chain: event → meaning → wound → belief → behaviour.
**Relevance to FN#070:** When the system encounters a decision point, premature
closure may have TWO roots: (1) cognitive efficiency bias and (2) false
certainty. The possibility space must account for both.

### FN#055 — The Architected Scientific Framing Layer (ASF)
**Slogan:** "Results first. Definitions before debate. Ontology last."
**Core:** AATIF demonstrates effects first, then explains mechanisms. Effect-
first, explanation-later. Epistemic humility as operational law. No
metaphysical claims beyond what's testable.
**Relevance to FN#070:** FN#070 embodies ASF — it presents possibilities
(results) before narrowing to a conclusion (ontology). The response style
IS the scientific method applied to human decision support.

### FN#058 — The Context Drift Detection & Scope Integrity Law (CDSI)
**Slogan:** "Continuity is controlled. Drift is not permission."
**Core:** Baseline snapshot at task start, continuous comparison, stop & re-
authorize on drift. Implemented as B-prime architecture (Storage → Observational
→ Judicial). DriftDetector feeds DriftRisk to GovernanceEquation as H_eff
pressure. Never-fully-reset rule. Action-slots vs knowledge-slots distinction.
**Engine:** Fully implemented in `aatif_drift_detector.py` (548 lines).
**Design consensus:** Completed 2026-06-30. See `FN058_DESIGN_CONSENSUS.md`.
**Relevance to FN#070:** FN#058 detects WHEN drift closes the possibility
space (through action-slot accumulation narrowing toward a single harmful
path). FN#070 prevents PREMATURE closure of the possibility space by the
system's own response. They are complementary: FN#058 watches the user's
drift, FN#070 watches the system's premature convergence.

### FN#069 — The Bounded Claim Law (ACN-01)
**Slogan:** "No metaphysical absolutes. All guarantees are system-bounded,
threat-model-bounded, and testable via audit."
**Core:** Every absolute claim must be replaced with: threat model + quantitative
bound + assumptions. Popper test: if no possible observation can refute a claim,
reformulate it.
**Relevance to FN#070:** The possibility space is BOUNDED, not infinite. FN#069
provides the epistemological discipline — claims about "openness" must themselves
be bounded and testable, not metaphysical.

---

## 3. Current Engine State

### 3.1 Complete Module Inventory (31 files)

```
engine/
├── aatif_s_equation.py            # S equation (safety) — 1371 lines, CORE
├── aatif_drift_detector.py        # FN#058 drift detection — 548 lines
├── aatif_governor.py              # Pipeline orchestrator: S→P→R→Gate
├── aatif_output_gate.py           # Final safety gate before response
├── aatif_r_equation.py            # R equation (response style)
├── aatif_response_shaper.py       # Converts decisions to meaning_instructions
├── aatif_intent_scorer.py         # I (intent) via embeddings
├── aatif_emotion_scorer.py        # E (emotion) via embeddings
├── aatif_semantic_scorer.py       # H (harm) via embeddings
├── aatif_embeddings.py            # Shared embedding backend (bge-m3/Ollama)
├── aatif_math.py                  # Shared sigmoid, clamp, etc.
├── aatif_intent_engine.py         # Legacy intent engine (pre-semantic)
├── aatif_contextual_intent.py     # I + fingerprint + memory integration
├── aatif_five_layer_intent.py     # FN#024 five-layer intent reading
├── aatif_multi_intent_collision.py # FN#036 multi-intent collision handler
├── aatif_conversation_memory.py   # Session state / conversation context
├── aatif_temporal_memory.py       # Time-aware memory
├── aatif_judgment_memory.py       # Past judgment recall
├── aatif_judgment_integration.py  # Judgment memory → engine integration
├── aatif_fingerprint.py           # User behavioral fingerprint
├── aatif_hysteresis.py            # Decision stability / anti-oscillation
├── aatif_domain_protocols.py      # P(d) domain-specific rules
├── aatif_time_sense.py            # حاسة الزمن — temporal awareness
├── aatif_boot_sequence.py         # System initialization
├── aatif_pipeline_connector.py    # Module wiring
├── aatif_arabic_utils.py          # Arabic text utilities
├── aatif_false_goodness_detector.py # FN#048 false goodness detection
├── aatif_meta_oversight.py        # Meta-level oversight
├── aatif_muhajij.py               # Argumentation engine
├── aatif_authority_doctrine.py    # FN#014 authority rules
├── aatif_logic_profile_scanner.py # Logic pattern detection
├── aatif_reasoning_trace.py       # Reasoning audit trail
```

### 3.2 Pipeline Architecture

The Governor (`aatif_governor.py`) implements the canonical pipeline:

```
User message
    │
    ▼
┌─────────────────────────────────────────────┐
│ S(d) — Safety Equation (aatif_s_equation.py)│
│   H scorer → H (harm)                      │
│   I scorer → I (intent)                     │
│   E scorer → E (emotion)                    │
│   DriftDetector → drift_risk                │
│   H_eff = clamp(H + λ·drift_risk, 0, 1)    │
│   quality = σ(w₁·I + w₂·E)                 │
│   gate = 1 − σ(α·(H_eff − θ))              │
│   S = quality × gate                        │
│                                             │
│   Thresholds:                               │
│     S > 0.7  → EXECUTE                      │
│     0.5 < S ≤ 0.7 → CLARIFY                │
│     0.3 < S ≤ 0.5 → SAFE_STOP              │
│     S ≤ 0.3 → SAFE_FREEZE                  │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│ P(d) — Domain Protocols                     │
│   Domain-specific rules (healthcare, edu…)  │
│   ACTION_NONE / ACTION_BLOCK / ACTION_EMERGENCY│
│   (Not consulted if SAFE_FREEZE)            │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│ R(d) — Response Style (aatif_r_equation.py) │
│   R = σ(w₃·T + w₄·V + w₅·G + w₆·D)        │
│   T=time, V=voice, G=gap, D=domain          │
│   Produces: formal / balanced / warm / casual│
│   Gate can LOWER R, never raise it           │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│ Response Shaper (aatif_response_shaper.py)  │
│   Converts S/P/R decisions →                │
│     meaning_instruction (soul of response)  │
│     dialect_instruction                     │
│     tone, forbidden_phrases                 │
│     should_ask_question, emotional_note     │
└─────────────┬───────────────────────────────┘
              │
              ▼
         LLM generates response
              │
              ▼
┌─────────────────────────────────────────────┐
│ Output Gate (aatif_output_gate.py)          │
│   6 check layers:                           │
│     1. Safety leak detection                │
│     2. Identity protection                  │
│     3. Forbidden phrase filtering           │
│     4. Protocol compliance                  │
│     5. Response quality guards              │
│     6. Final sanitization                   │
│   "لو كل شي فات — أنا آخر حارس"            │
└─────────────┬───────────────────────────────┘
              │
              ▼
         Response → User
```

### 3.3 Key Equations

**S Equation (Gated form — current production):**
```
S = σ(w₁·I + w₂·E) × [1 − σ(α·(H_eff − θ))]

Where:
  H_eff = clamp(H + λ·drift_risk, 0, 1)   # FN#058
  θ = domain constant (healthcare=0.25, education=0.30, general=0.40, creative=0.50)
  α = gate sharpness (default 10.0)
  w₁ = 1.2 (intent weight)
  w₂ = 0.8 (emotion weight)
  λ = 0.3 (drift coupling strength)
```

**R Equation (Response style):**
```
R = σ(w₃·T + w₄·V + w₅·G + w₆·D + bias)

Where:
  T = time signal, V = voice signal, G = gap signal, D = domain signal
  w₃=1.0, w₄=1.5, w₅=0.8, w₆=2.0, bias=-2.65
  R → style mapping: ≤0.3=formal, ≤0.5=balanced, ≤0.7=warm, >0.7=casual
```

**Decision Thresholds:**
```
EXECUTE    (S > 0.7)  — proceed fully
CLARIFY    (0.5 < S ≤ 0.7) — ask before proceeding
SAFE_STOP  (0.3 < S ≤ 0.5) — stop, log
SAFE_FREEZE (S ≤ 0.3) — halt immediately
```

**Domain-parameterized θ:**
```python
DOMAIN_CONFIG = {
    "healthcare":  {"theta": 0.25, ...},  # strictest
    "education":   {"theta": 0.30, ...},
    "general":     {"theta": 0.40, ...},
    "creative":    {"theta": 0.50, ...},  # most permissive
}
```

### 3.4 Scorer Architecture (H, I, E)

All three scorers use the same architecture:
- Embedding backend: bge-m3 via Ollama
- Method: top-K=3 nearest anchors + temperature=0.05
- Anchors: bilingual (Arabic Gulf/Egyptian/Levantine + English)
- H anchors: ~40+ examples from benign (0.0) to extreme danger (1.0)
- I anchors: harmful purpose (0.0) to constructive purpose (1.0)
- E anchors: extreme negative (0.0) to extreme positive (1.0)
- Key lesson (2x4 experiment): bge-m3 matches WORDS not MEANINGS — anchors
  must avoid lexical contamination between scorers

---

## 4. Key Constraints

### 4.1 Single Mind Principle
> Only GovernanceEquation can transform inputs into final safety.
> Everything else can provide signals, memory, or evidence.

FN#070 MUST NOT become a second judge. It provides STYLE signals to the
Response Shaper, not safety decisions to the S equation.

### 4.2 H_eff, NOT θ
- θ is a domain-level constant — NEVER changes dynamically
- DriftRisk (FN#058) adds to H: `H_eff = clamp(H + λ·drift_risk, 0, 1)`
- If FN#070 ever needs to influence safety (debatable), it would add to H_eff
  via its own λ, never modify θ
- BUT: FN#070's field note explicitly says "ما لا يتأثر: منطق المحركات" —
  it should NOT touch H, H_eff, or θ at all

### 4.3 Feature Flags
All new features are gated by flags in the engine:
```python
DYNAMIC_THETA_ENABLED = False    # Dynamic θ — currently disabled
REGEX_V2_ENABLED = True          # Regex v2 safety net
DRIFT_IN_ENGINE_ENABLED = True   # FN#058 drift integration
# FN#070 will need: PSP_ENABLED = False  (initially off)
```

### 4.4 Zero Regression Rule
Every new module must pass ALL existing tests plus new tests with 0 regressions.
The test suite for aatif_s_equation.py alone is extensive. FN#070 must not
change any existing test outcomes.

### 4.5 B-prime Architecture Pattern (from FN#058)
Established pattern for new features:
```
Storage (ConversationManager) → Observational (new detector) → Judicial (GovernanceEquation)
```
FN#070 may follow a variant since it targets Response Style, not Safety:
```
Storage (ConversationManager) → Observational (PSP detector) → Stylistic (ResponseShaper)
```

### 4.6 Binding Channels (FN#044)
FN#070 signals should travel via B5 (Behaviour — tone/rhythm/expression),
NOT B6 (Safety). This maintains the "ما لا يتأثر: منطق المحركات" constraint.

---

## 5. The Core Design Question

FN#070 sits at a unique intersection: it is a **governance law** (constitutional
level) that operates through **response style** (not engine logic). This creates
a novel design challenge:

**Binary world (current):** S decides EXECUTE/CLARIFY/STOP/FREEZE. R decides
formal/balanced/warm/casual. The Response Shaper converts to meaning_instruction.
The LLM generates. The Gate checks.

**Distributional world (FN#070):** Before the LLM generates, the system must
ALSO ensure the response preserves the possibility space — presenting multiple
paths rather than collapsing to a single recommendation. This is neither a
safety decision (S) nor a style decision (R) — it's a **structural decision
about information presentation**.

The 3-model external review called this: "from binary to distributional" —
the strongest conceptual upgrade in the entire roadmap.

---

## 6. Architecture Options

### Option A: PSP as Response Shaper Extension
**Where:** Inside `aatif_response_shaper.py`
**How:** Add a `possibility_space` field to `ResponseShape`. When a decision-
point is detected, the shaper injects instructions to present alternatives
rather than a single recommendation.

```python
@dataclass
class ResponseShape:
    # ... existing fields ...
    possibility_mode: str = "normal"         # "normal" | "preserve" | "bounded"
    live_paths: int = 0                      # number of active paths to present
    closure_forbidden: bool = False          # explicit anti-closure flag
    tradeoff_required: bool = False          # must present tradeoffs
```

**Pros:** Minimal new code. Follows the existing pipeline. R(d) already
governs style — this extends it naturally.
**Cons:** May overload ResponseShaper. Decision-point detection logic
needs to live somewhere upstream.

### Option B: PSP as Standalone Detector (B-prime variant)
**Where:** New `aatif_psp_detector.py` + ResponseShaper integration
**How:** Like DriftDetector (FN#058), create a standalone module that
analyzes the conversation state and produces a PSP reading.

```
ConversationManager
└── maintains session, history

PSPDetector
└── consumes turn features + response draft
└── outputs PSPReading (is this a decision point? how many live paths?)
└── OBSERVATIONAL — says "this is a decision point with 3 live paths"

ResponseShaper
└── receives PSPReading
└── adjusts meaning_instruction to preserve possibility space
└── STYLISTIC — NOT judicial
```

```python
@dataclass
class PSPReading:
    is_decision_point: bool       # does this turn involve a real decision?
    live_paths: int               # how many distinct paths exist?
    closure_risk: float           # 0.0 = open, 1.0 = fully collapsed
    evidence: str                 # why this reading
    bounded_set: list[str]        # the specific paths identified
```

**Pros:** Clean separation. Testable independently. Follows B-prime pattern.
Detector can evolve without touching shaper code.
**Cons:** More code. Another module in the already large engine.

### Option C: PSP as R Equation Extension
**Where:** Inside `aatif_r_equation.py`
**How:** Add a new signal to R that accounts for decision-point presence.

```
R = σ(w₃·T + w₄·V + w₅·G + w₆·D + w₇·P)

Where P = possibility-space pressure (new):
  P ~ 0.0 → no decision point (normal response)
  P ~ 1.0 → critical decision point (must preserve space)
```

When P is high, R is pushed toward formal/balanced (lower R), which
naturally encourages more careful, structured responses.

**Pros:** Mathematically clean. Integrates with existing R framework.
**Cons:** R was designed for tone/formality, not information structure.
P affects WHAT is said, not just HOW — this may be category error.

### Option D: PSP as Output Gate Layer
**Where:** Inside `aatif_output_gate.py` as a new check layer
**How:** After the LLM generates, the gate checks whether the response
prematurely closes the possibility space.

```python
# New gate check (layer 7):
def _check_possibility_space(self, text, psp_reading):
    """Does the response collapse alternatives into a single recommendation?"""
    # Check for premature closure patterns:
    # - "أنصح بـ" / "I recommend" without alternatives
    # - Single option presented when multiple exist
    # - Missing tradeoff disclosure
    # If closure detected + psp_reading.is_decision_point:
    #     return blocked=True, reason="premature_closure"
```

**Pros:** Catches closure even when upstream missed it. "آخر حارس" principle.
Last-line defense. Can use pattern matching (Arabic + English).
**Cons:** Blocking is expensive — better to prevent than cure. Regeneration
needed if blocked. Post-hoc, not architectural.

### Recommended: Option B + Option D (layered defense)

```
                      ┌──────────────────────┐
                      │  PSPDetector         │
                      │  (observational)     │
                      │  "Is this a decision │
                      │   point? How many    │
                      │   paths live?"       │
                      └──────┬───────────────┘
                             │ PSPReading
                             ▼
┌──────────────────────────────────────────────────┐
│  ResponseShaper                                  │
│  if psp_reading.is_decision_point:               │
│      meaning_instruction += preserve_space_rules │
│      inject: "present N paths with tradeoffs"    │
│      inject: "do NOT recommend a single option"  │
│      inject: "return the decision to the human"  │
└──────────────────────┬───────────────────────────┘
                       │ meaning_instruction
                       ▼
                  LLM generates
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  Output Gate — Layer 7 (PSP check)               │
│  Pattern-match for premature closure:            │
│    "أنصح" / "اختر" / "الأفضل هو" / "I recommend"│
│  If closure + decision_point → BLOCK & regenerate│
└──────────────────────────────────────────────────┘
```

This follows FN#058's precedent: the Detector is observational, the Shaper is
stylistic, the Gate is the last guard. No component touches S(d) or H or θ.

---

## 7. Open Design Questions for Consensus

### Q1: How does the system detect "decision points"?
What signals indicate the human is facing a real decision vs. asking a factual
question? Candidates:
- Explicit decision language: "أيهما أفضل", "ما القرار", "should I", "which one"
- Context: multiple options previously discussed
- Domain: healthcare/legal inherently high-decision
- User history: has this user been exploring alternatives?
- **Sub-question:** Is this pattern-matching (like FN#036) or embedding-based?

### Q2: How to determine the "bounded set" of live paths?
FN#070 and the Schwartz warning both say: not infinite options, but a bounded
set. How does the system determine:
- How many paths to present? (2? 3? 5? domain-dependent?)
- When is a path "live" vs. already eliminated?
- Who decides the bound — the system or the human?

### Q3: Relationship to FN#036 (Multi-Intent Collision)
When the user's message carries multiple intents AND is a decision point:
- Does PSP apply to each intent separately?
- Does collision resolution happen BEFORE or AFTER PSP?
- Does SAFE_SPLIT interact with possibility-space preservation?
Proposed: FN#036 runs first (collision detection), then PSP applies to each
resolved intent independently.

### Q4: Relationship to FN#006 (Human-Over-Loop)
FN#006 says the human is ABOVE the loop. FN#070 says don't collapse options.
These align philosophically but need operational clarity:
- Does "Human-Over-Loop" mean the system NEVER gives a recommendation?
- Or can the system recommend AFTER presenting alternatives?
- Is there a "prompted closure" mode — where the human explicitly asks
  "just give me your recommendation" and the system complies?
Proposed: After presenting alternatives, if the human explicitly requests a
recommendation, the system may provide one. Unprompted single recommendations
are the violation.

### Q5: Where exactly does PSPDetector sit in the pipeline?
Two options:
- **Pre-LLM:** PSPDetector runs BEFORE the LLM generates, based on the user's
  message and conversation history. Shaper includes PSP instructions in the
  meaning_instruction.
- **Post-LLM:** PSPDetector runs AFTER the LLM generates, checking whether
  the response prematurely closes the space (Output Gate approach).
- **Both (recommended):** Pre-LLM via ResponseShaper + Post-LLM via OutputGate.
  Belt and suspenders.

### Q6: How does PSP interact with CLARIFY decisions?
When S produces CLARIFY (0.5 < S ≤ 0.7), the system is already asking for
clarification. Does PSP add anything here, or is CLARIFY inherently
possibility-preserving?
- CLARIFY asks "did you mean X?" — this could NARROW the space
- PSP-aware CLARIFY might ask "are you looking for X, Y, or Z?" — this
  PRESERVES the space
- Design decision: should CLARIFY automatically trigger PSP mode?

### Q7: Domain-specific PSP behavior
Should PSP intensity vary by domain?
- Healthcare (θ=0.25): Maximum PSP — premature closure can kill
- Education (θ=0.30): High PSP — students need to explore
- General (θ=0.40): Moderate PSP — balance efficiency with exploration
- Creative (θ=0.50): Context-dependent — sometimes creative direction
  WANTS a single bold recommendation
Proposed: PSP has a domain-dependent `psp_weight` analogous to θ.

### Q8: Bounded set — Schwartz paradox implementation
The field note warns: unlimited options = paralysis (Schwartz 2006).
- What is the maximum number of presented paths? (3? 5? 7?)
- Is this configurable per domain?
- Should the system actively TRIM the set if it grows too large?
- How to distinguish "trimming for usability" from "premature closure"?

### Q9: Arabic-specific decision patterns
Arabic decision-making often involves:
- استخارة (seeking guidance) — spiritual decision framework
- مشورة (consultation) — social decision framework
- Both imply the decision is the human's, not the advisor's
- Do these cultural patterns require special PSP handling?

### Q10: Metrics — how do we MEASURE PSP effectiveness?
Following FN#069 (Bounded Claim Law), PSP must be testable:
- What is the "closure rate" metric? (responses that collapse to single option)
- What is the "exploration rate" metric? (responses that preserve alternatives)
- Can we build a test dataset of decision-point conversations?
- What is the false-positive rate? (factual questions misidentified as
  decision points, leading to unnecessary option-presentation)

---

## 8. What FN#070 Does NOT Change

Explicitly from the field note — "ما لا يتأثر":
- S equation logic (H, I, E, θ, α, weights)
- H_eff computation
- DriftDetector logic (FN#058)
- Domain protocols P(d)
- Safety thresholds
- Service outputs / formal reports
- Any existing test outcomes

FN#070 affects ONLY:
- أسلوب الشرح (explanation style)
- ترتيب الأفكار (idea ordering)
- التأنّي (patience/deliberation)
- طرح الأسئلة (question-asking)

This means the implementation lives in the **ResponseShaper** and **OutputGate**
layers, not in the **S equation** or **DriftDetector**.

---

## 9. Evaluation Strategy

### 9.1 Decision-Point Dataset
Build a multi-turn decision-point dataset:
1. Take real decision scenarios (medical diagnosis, career choice, purchase
   decision, architectural design) → create conversations where the system
   must preserve alternatives
2. Mix with factual/non-decision conversations where single answers are
   correct ("What is the capital of France?")
3. This gives both decision-point and factual cases for testing

### 9.2 Metrics
- **Closure Rate:** % of decision-point responses that collapse to single option
  (target: < 10%)
- **Exploration Rate:** % of decision-point responses that present ≥ 2 paths
  with tradeoffs (target: > 85%)
- **False Positive Rate:** % of factual questions treated as decision points
  (target: < 5%)
- **Schwartz Compliance:** % of decision-point responses with ≤ N options
  (target: 100% within bound)
- **Human Satisfaction:** A/B test — does PSP improve perceived decision quality?

### 9.3 Regression Testing
All existing S equation tests must pass unchanged. All existing drift detection
tests must pass unchanged. All existing response shaper tests must pass unchanged.

---

## 10. Source Attribution

This design brief was prepared by Claude (Anthropic) at the Architect's request,
based on comprehensive reading of:
- FN#070 (The Possibility Space Preservation Law)
- FN#006 (Human-Over-Loop), FN#036 (Multi-Intent Collision), FN#041 (PVM),
  FN#044 (Eight-Channel Binding), FN#050 (Dual-Root Reconstruction),
  FN#055 (ASF), FN#058 (Context Drift Detection), FN#069 (Bounded Claim Law)
- Engine source code: all 31 modules in `engine/`
- `FN058_DESIGN_CONSENSUS.md` (format template)
- `NEXT_STEPS.md` (priority and review context)

The design questions and architecture options are proposals for consensus —
neither Claude nor ChatGPT has absolute authority. The Architect decides.

---

## Appendix A: Engine File Sizes and Purposes

| File | Lines | Purpose |
|------|-------|---------|
| aatif_s_equation.py | 1371 | Core S equation — safety decision |
| aatif_drift_detector.py | 548 | FN#058 — context drift detection |
| aatif_governor.py | ~400+ | Pipeline orchestrator S→P→R→Gate |
| aatif_output_gate.py | ~300+ | Final safety gate (6 layers) |
| aatif_r_equation.py | ~200+ | R equation — response style |
| aatif_response_shaper.py | ~200+ | Converts decisions → meaning_instruction |
| aatif_intent_scorer.py | ~200+ | I scorer (semantic embeddings) |
| aatif_emotion_scorer.py | ~200+ | E scorer (semantic embeddings) |
| aatif_semantic_scorer.py | ~200+ | H scorer (semantic embeddings) |
| aatif_multi_intent_collision.py | ~200+ | FN#036 — multi-intent collision |
| aatif_contextual_intent.py | ~200+ | I + fingerprint + memory |
| aatif_five_layer_intent.py | ~200+ | FN#024 — five-layer intent |
| aatif_conversation_memory.py | ~200+ | Session state management |
| aatif_domain_protocols.py | ~200+ | P(d) domain rules |
| aatif_hysteresis.py | ~200+ | Decision stability |
| Others (16 files) | varies | Supporting modules |

## Appendix B: Feature Flag Registry

```python
# aatif_s_equation.py
DYNAMIC_THETA_ENABLED    = False   # Dynamic θ (disabled)
REGEX_V2_ENABLED         = True    # Regex v2 safety net
DRIFT_IN_ENGINE_ENABLED  = True    # FN#058 drift integration

# Proposed for FN#070:
PSP_ENABLED              = False   # Possibility Space Preservation (initially off)
PSP_GATE_CHECK_ENABLED   = False   # Output Gate PSP check (initially off)
```

## Appendix C: Binding Channel Assignment

Per FN#044 — Eight-Channel Binding Architecture:

| Channel | Carries | FN#070 relevance |
|---------|---------|------------------|
| B1 — Identity | Identity fingerprint | None |
| B2 — Constitutional | Constitutional laws | MSP-L as constitutional law (source) |
| B3 — Meaning | Refined meaning from META | None |
| B4 — Intent | Intent vectors | Decision-point detection input |
| B5 — Behaviour | Tone, rhythm, expression | **PRIMARY** — PSP signals travel here |
| B6 — Safety | Safety constraints | None (explicitly excluded by FN#070) |
| B7 — Drift Detection | Real-time drift signals | Complementary (FN#058) |
| B8 — Execution | Approved output | PSP-modified output travels here |
