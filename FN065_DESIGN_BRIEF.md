# FN#065 Maqam Architecture Law — Design Brief
## For ChatGPT Consensus Review

### Context
AATIF OS is a multi-layer AI governance framework. This is a new B-prime observational module that detects the emotional "maqam" (mode) of user input text, inspired by the Architect's musical observation that emotional text has modal structures analogous to Arabic musical maqams.

### Field Note #065 Summary
The Maqam Architecture Law establishes a triad for identifying emotional/tonal "maqam" in text:

1. **Jins (الجنس)** — the structural emotional unit (e.g., warmth, authority, vulnerability, playfulness)
2. **Aqd (العقد)** — cadence and transition behavior (how the emotional mode flows, peaks, resolves)
3. **Nisba (النسبة)** — the distinctive "fingerprint" ratio that uniquely identifies the mode

**Operating Law:** "Tone follows Maqam. Content follows Truth."

### Architecture Constraints
- B-prime observational: CAN_BLOCK_RUNTIME=False, CAN_MODIFY_H/θ/S=False
- Single Mind Law: Only GovernanceEquation makes safety decisions
- Output binds to B1 (Behaviour channel) → feeds R equation (style, NOT safety)
- Sparse activation: threshold ~0.25, fast-path skip when no emotional signal

### IMPORTANT DISTINCTION
This is NOT about music theory. The maqam concept is an ANALOGY. The three dimensions (jins/aqd/nisba) are borrowed musical terminology applied to emotional pattern detection in text.

### Proposed Emotional Maqams (Modes)
Each mode has a characteristic triad:

| Maqam | Jins (structural unit) | Aqd (cadence) | Nisba (fingerprint) |
|-------|----------------------|---------------|---------------------|
| WARMTH (دفء) | care, empathy, gentleness | soft peaks, gradual, nurturing | personal pronouns + emotional verbs |
| AUTHORITY (هيبة) | command, certainty, expertise | declarative, direct, conclusive | imperatives + certainty markers |
| VULNERABILITY (انكسار) | pain, openness, fragility | hesitant, broken rhythm, trailing | self-reference + doubt/pain markers |
| PLAYFULNESS (مرح) | humor, lightness, energy | quick rhythm, bouncy, surprising | exclamations + informal language |
| SEEKING (بحث) | curiosity, questioning, exploration | ascending, open-ended, branching | question patterns + hedging |
| GRATITUDE (شكر) | appreciation, acknowledgment | warm resolution, closing cadence | thanks markers + recognition |
| FRUSTRATION (إحباط) | blocked energy, impatience | sharp peaks, repetitive, escalating | negation chains + urgency markers |
| NEUTRAL (محايد) | informational, transactional | flat, even, no emotional curve | absence of emotional markers |

### Design Questions for Consensus

**Q1: Maqam Set Completeness** — Are these 8 maqams sufficient? Should any be split, merged, or added? Consider: SADNESS (حزن) as separate from VULNERABILITY, URGENCY (عجلة) as separate from FRUSTRATION, DEFIANCE (تحدّي) as a distinct mode.

**Q2: Jins Detection Strategy** — Jins = structural emotional unit. Should we use (a) keyword marker sets (like MRS/COLD-OS), (b) pattern-based detection (regex + co-occurrence), or (c) a hybrid? What's the right granularity?

**Q3: Aqd (Cadence) Detection** — How do we detect "cadence" in text without actual audio? Proposed signals: sentence length variation, punctuation patterns, question density, exclamation density, trailing patterns ("..."), repetition structures. Is this sufficient?

**Q4: Nisba (Fingerprint Ratio)** — The nisba is the distinctive marker ratio. Proposed: for each maqam, define a set of "characteristic markers" and compute what fraction of the text's emotional markers belong to that set. If the ratio exceeds a threshold (e.g., 0.4), that maqam's nisba is confirmed. Is this sound?

**Q5: Multi-Maqam Detection** — Text may carry multiple emotional modes (e.g., warmth + vulnerability). Should we: (a) report only dominant maqam, (b) report primary + secondary, (c) report a full distribution? What about transitions within a single message?

**Q6: Arabic Dialect Handling** — Gulf Arabic has distinct emotional markers (يا قلبي, والله تعبت, etc.). How should we handle dialectal markers vs MSA markers? Same frozenset or separate?

**Q7: Activation Threshold** — At what minimum signal should this module activate? MRS uses 0.35. Proposed: 0.25 (since emotional mode detection should be broader than distress detection). Too low = noise on every message.

**Q8: Output Structure** — Proposed MaqamReading dataclass:
```python
@dataclass(frozen=True)
class MaqamReading:
    detected_maqam: MaqamType          # primary detected mode
    jins: JinsReading                  # structural analysis
    aqd: AqdReading                    # cadence analysis  
    nisba: NisbaReading                # fingerprint ratio
    confidence: float                  # 0.0–1.0
    secondary_maqam: MaqamType         # secondary mode if present
    markers_found: Tuple[str, ...]     # audit trail
    b1_style_hints: Tuple[str, ...]    # advisory for R equation
    activated: bool                    # False = fast-path skip
    safety_decision_authority: str     # always "GOVERNANCE_EQUATION_ONLY"
    _isolation_marker: str             # "B1_ADVISORY_NOT_FOR_SAFETY"
```

Is this structure sufficient? What's missing?

### Evaluation Criteria
Please evaluate each question and provide:
- PASS / PASS WITH CONCERNS / NEEDS REVISION
- Specific suggestions for improvement
- Overall verdict
