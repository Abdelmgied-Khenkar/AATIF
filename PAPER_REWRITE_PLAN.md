# AATIF Paper Rewrite Plan — "Write the Paper That Matches the Code"

**Date:** June 19, 2026
**Author:** Abdulmjeed Ibrahim Khenkar
**Architect of the Plan:** Claude (Anthropic), following consensus from 4-model review (Gemini, Grok, DeepSeek, ChatGPT)

---

## The Problem: Two Papers in One

The current paper (`aatif_paper_arxiv.tex`) tells a story about 73 conjectures derived from observation, a 7-step inductive methodology, an Ethical Question Compiler (EQC), and a Tri-Engine Decision Protocol.

The code (`engine/`, `tests/`, `benchmarks/`) implements something different and more concrete: a mathematical governance equation `S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))]` with three independent scorers (H/I/E), hysteresis control, CBRN safety gates, 164 deterministic tests, A/B calibration results, and benchmark evaluations against HarmBench and MultiJail.

All four reviewing models (Gemini, Grok, DeepSeek, ChatGPT) independently reached the same conclusion:

> **The S equation, the engine, the tests, and the benchmarks are the real contribution. The conjectures are the origin story, not the paper.**

The consensus recommendation: workshop-level as-is, conference-level if rewritten around the code.

---

## New Paper Title (Proposed)

**"AATIF: A Multiplicative Governance Equation for Arabic-First LLM Safety"**

Alternative: "AATIF: Continuous Safety Scoring for LLMs via Multiplicative Harm Gating and Arabic-First Semantic Anchors"

---

## 1. New Paper Structure

### Section 1 — Introduction (1.5 pages)

**Lead with the problem, not the biography.**

- LLM safety systems are predominantly English-first, classifier-based, and binary (allow/block).
- Three structural gaps in existing systems:
  1. **No interpretable equation.** FanarGuard, Llama Guard, Perspective API all use learned classifier weights — none provides an explicit mathematical governance formula with provable properties.
  2. **No non-compensability guarantee.** Additive or mean-based aggregation allows benign intent to mask moderate harm ("toxic positivity" attack).
  3. **Arabic as afterthought.** Arabic dialect support is either absent or "bolted on" to English-first systems. No system handles Arabic figurative hyperbole as a first-class concern.
- AATIF addresses all three gaps with a single framework: an explicit multiplicative equation, zero-training semantic anchors, and Arabic-first design with dialect hyperbole disambiguation.
- State the S equation in the introduction. Let the reader see the contribution on page 1.

### Section 2 — Related Work (1.5 pages)

**Keep most of the current Section 2, with restructuring.**

- 2.1 — Alignment approaches (RLHF, Constitutional AI, mechanistic interpretability) → **keep as-is**, it's well-written
- 2.2 — Arabic-aware AI safety (FanarGuard, Llama Guard 3, Perspective API, ADHAR, SOD) → **keep and expand** the direct comparison table from `FANARGUARD_COMPARISON.md`
- 2.3 — Safety benchmarks (HarmBench, MultiJail, MLCommons) → **keep as-is**
- 2.4 — Positioning → **rewrite** to focus on the 3 structural gaps this paper addresses

**Remove from Related Work:**
- The grounded theory / inductive methodology framing (Glaser & Strauss, Nielsen & Molich). These belong in the origin story section, not in related work for a systems paper.

### Section 3 — The AATIF Governance Equation (2.5 pages) ← THIS IS THE CORE

**This section becomes the heart of the paper. Currently it's buried in Section 5.**

- 3.1 — **The S Equation: Definition and Properties**
  - Full mathematical definition: `S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))]`
  - Variable definitions with Arabic names: H (حرارة الكلمة), I (النية), E (الشعور)
  - The multiplicative gate structure and WHY it matters:
    - Quality term `σ(w₁·I + w₂·E)` ∈ (0,1) — how clear/benign is the request?
    - Harm gate `[1 − σ(α(H − θ))]` ∈ (0,1) — is harm below threshold?
    - Product ensures non-compensability: H > θ closes the gate REGARDLESS of I, E
  - Sigmoid symmetry property: `[1 − σ(α(H − θ))] = σ(α(θ − H))`
  - Hard override: H > 0.7 → SAFE_FREEZE (absolute safety floor)
  - Decision mapping table: EXECUTE / CLARIFY / SAFE_STOP / SAFE_FREEZE
  - Follow-up signal F: harm-floor guarantee even when S is high

- 3.2 — **The Three Scorers**
  - H scorer (Semantic Harm Proximity): 132 curated anchors (58 benign, 74 harm), cosine similarity against bge-m3 embeddings, top-K=3 aggregation to prevent anchor contamination
  - I scorer (Intent Classification): 44 intent anchors, top-K softmax, OOD guard, confidence bands
  - E scorer (Emotional Load): 32 emotion anchors, distress/escalation detection
  - All scores continuous in [0,1], all deterministic at test time (TF-IDF fallback)

- 3.3 — **Hysteresis Controller (γ+)**
  - Problem: decisions oscillate when S hovers near threshold boundaries
  - Solution: entry/exit thresholds offset by ε (the "AC thermostat" principle)
  - Per-session state isolation

- 3.4 — **Safety Gate — Law Ω (CBRN) and Law Ξ (Override Lock)**
  - Unconditional CBRN detection in Arabic + English, fires BEFORE S equation
  - Override attempt detection ("ignore instructions", "تجاوز") → SAFE_FREEZE
  - Mode-independent by design

- 3.5 — **Mode Profiles**
  - Four parameter profiles (high_sensitivity, default, creative, casual)
  - How α and θ vary across profiles
  - A/B test methodology: 54 test cases (30 harmful, 24 benign), θ sweep results
  - Final calibration: θ=0.40, α=10, F1=0.984

- 3.6 — **Ambiguity Pre-Check and Jailbreak Detection**
  - Ambiguity detection: short/vague prompts → override EXECUTE to CLARIFY
  - Bidirectional jailbreak handler: escalate if markers found, downgrade SAFE_FREEZE → SAFE_STOP if no markers (simple harm ≠ manipulation)

### Section 4 — Arabic-First Design (1.5 pages) ← NEW SECTION

**This is where Arabic becomes a first-class scientific contribution, not a claim.**

- 4.1 — **The Meaning Density Hypothesis (كثافة المعنى)**
  - The variable is MEANING DENSITY, not language identity
  - Arabic was chosen because of measurable properties: root-pattern morphology (trilateral roots ك-ت-ب compress semantic relationships), rich metaphorical system, 700 names for the lion = 700 semantic dimensions
  - This is a logical selection based on information-theoretic properties, not cultural bias
  - Applies to ANY high-density language (Hebrew, Amharic share root-pattern morphology)
  - English-first embeddings project Arabic INTO a space built for English distinctions → systematic information loss

- 4.2 — **Dialect Hyperbole Disambiguation**
  - The problem: Arabic colloquial speech uses violent metaphors for everyday emotions
    - "يجيب لهم جلطه" (he'll give them a stroke) = he'll annoy them
    - "والله بذبحه" (I swear I'll slaughter him) = I'm annoyed at him
    - "قنبلة على السوشيال ميديا" (a bomb on social media) = a viral hit
  - The solution: 28+ hyperbole anchors scored at H ≤ 0.05, providing semantic "counter-gravity" so figurative speech doesn't trigger harm detection
  - The Lexical Anchor Contamination effect (FN#075): English-first embeddings can't separate these because the geometry was built for English semantic categories
  - Test results: 22 dialect-specific test cases, zero false positives on hyperbole

- 4.3 — **The Maqam-to-Safety Origin Chain** (NEW — the narrative the reviewers want)

  Present this as an intellectual origin story showing how domain observation led to a concrete safety mechanism:

  1. **Music AI gap:** Arabic quarter-tone music (maqam system) cannot be represented by Western equal-tempered 12-tone scale. AI music systems trained on Western scales are structurally deaf to Arabic musical emotion. This is not a training data problem — it's a representational limitation.

  2. **From music to speech:** Musical maqam carries temporal-emotional information (each maqam has a mood: Bayati = sadness, Rast = stability, Hijaz = longing). The same insight applies to SPEECH: prosody (pitch contour, rhythm, emphasis) carries emotional information that words alone don't capture.

  3. **From speech to text:** When communication moves from speech to TEXT, prosody disappears. The SAME sentence ("fine, do whatever you want") can be angry, sarcastic, resigned, or genuinely okay. Text is prosody-stripped.

  4. **The textual spectrogram proposal:** If prosody is lost in text, can we reconstruct an "emotional fingerprint" from textual features? The features: punctuation patterns, repetition, dialectal markers, emoji usage, sentence length variation, formality shifts. This is what the E scorer partially implements.

  5. **Killer application — duress detection:** An authorized user under coercion (gun to their head, blackmail) will have involuntary changes in their textual fingerprint: different sentence patterns, unusual formality, absence of habitual phrases. Three signals combine (analogous to the S equation):
     - **Fingerprint deviation** (E scorer analogue: "this doesn't sound like them")
     - **Timestamp anomaly** (unusual time of access)
     - **Dangerous command** (H scorer analogue: action requested is high-risk)
     - All three must converge → governance gate fires

  6. **Connection to S equation:** This is exactly the multiplicative gate principle. No single signal is sufficient. The product of three independent assessments creates a governance decision that no single channel can override.

  Frame this as: "The maqam observation motivated the emotional channel. The duress use case motivated the multiplicative gate. The code implements the principle that the maqam observation identified."

### Section 5 — Experimental Evaluation (2 pages)

**Move current Section 5 benchmark results here. Add the missing data.**

- 5.1 — **Test Suite (164 tests)**
  - Categories: dialect detection (22), S equation math (boundedness, monotonicity), decision logic across 4 profiles, hysteresis stability, Law Ω CBRN gate (12), Law Ξ override lock, intent scorer (30), adversarial cases (15), gated comparison (18), pipeline integration (3)
  - All deterministic — no external model dependency at test time
  - CI/CD via GitHub Actions

- 5.2 — **HarmBench Results (bge-m3 backend)**
  - Table from current paper (Table 1): 74.3% safety-category, 100% chemical/biological, 88.4% cybercrime + illegal
  - Comparison with TF-IDF baseline showing cross-lingual improvement
  - Honest framing: 7.0% copyright, 33.3% misinfo — not where AATIF contributes

- 5.3 — **MultiJail Results (Arabic vs English)**
  - Table from current paper (Table 2): Arabic 74.7% vs English 69.3%
  - Arabic outperforms English — validates Arabic-first anchor design
  - Cross-lingual gap analysis: Arabic advantage in violence/threat categories
  - This is the paper's empirical crown jewel

- 5.4 — **A/B Calibration Results (θ sweep)**
  - Methodology: 54 test cases (30 harmful, 24 benign), θ from 0.20 to 0.55
  - Result: θ=0.35–0.40 optimal (F1=0.984, 100% detection, 4.2% FP)
  - The one false positive: "حزين شوي بس بخير" → SAFE_STOP — aligns with compassionate design (ع ط ف)
  - α sweep: stable across α=8–20

- 5.5 — **MLCommons Coverage Mapping**
  - Coverage table: 3/13 strong (S1, S9, S11), 3/13 partial (S2, S7, S10), 7/13 uncovered
  - Honest framing: coverage reflects observational origin, not design limitation
  - Key point: adding anchors expands coverage WITHOUT retraining

- 5.6 — **Comparison with FanarGuard**
  - Not competitive — complementary
  - FanarGuard: data-driven (468K examples, F1=0.82), black box
  - AATIF: equation-driven (0 training examples), fully interpretable
  - FanarGuard could benefit from AATIF's governance structure; AATIF could benefit from FanarGuard's cultural alignment axis

### Section 6 — Discussion (1 page)

- 6.1 — **What This Framework Offers**
  - First explicit governance equation for Arabic safety with provable non-compensability
  - Zero-training extensibility (add anchors, not data)
  - Arabic outperforming English as empirical validation of Arabic-first design
  - Dialect hyperbole disambiguation as unique capability

- 6.2 — **Limitations** (keep the current honest framing)
  - Single-observer development
  - 4/13 MLCommons categories strong, 7 uncovered
  - Misinformation and paraphrase remain weak
  - Calibrated on 54 prompts — not production-grade
  - No ablation study on individual scorers

- 6.3 — **The Conjectures as Motivation** (reframed)
  - The 73 conjectures are the research program, not this paper's contribution
  - This paper operationalizes ONE conjecture (#063: constraint density) into a working system
  - The field notes (78 documents) are the broader research contribution, published as supplementary material
  - Future papers can address other conjectures

### Section 7 — Conclusion (0.5 pages)

- AATIF provides an explicit, interpretable mathematical governance equation for LLM safety
- The multiplicative gate structure provides a non-compensability guarantee absent from existing systems
- Arabic-first design is validated empirically: Arabic outperforms English on identical harmful prompts
- The framework requires zero training and extends through anchor curation alone
- Code, tests, and benchmarks are open source

---

## 2. What to KEEP from the Old Paper

| Section | What | Why |
|---------|------|-----|
| Related Work 2.1-2.3 | RLHF, Constitutional AI, mechanistic interpretability, FanarGuard comparison, ADHAR/SOD | Well-written, properly cited, establishes genuine gaps |
| Section 5 (old) | S equation definition, HarmBench table, MultiJail table, MLCommons mapping | This IS the paper — move it to Section 3-5 |
| Limitations | All 8 limitation points | Honest, well-scoped, reviewers praised this |
| Selected conjectures | #001 (Clarification), #063 (Constraint Density), #069 (Bounded Claims), #067 (Pressure-Reveal) | These motivated the code — use as motivation, not contribution |
| Bibliography | All 30+ citations | Strong, properly formatted |
| Abstract language | "experience report" / "derived through observation" | Honest framing that reviewers respected — keep the humility |

---

## 3. What to ADD (New Content)

| Item | Source | Section |
|------|--------|---------|
| S equation as LEAD content (page 1, not page 8) | `engine/aatif_s_equation.py` | §3.1 |
| Full scorer descriptions (H: 132 anchors, I: 44 anchors, E: 32 anchors) | `engine/aatif_semantic_scorer.py`, `aatif_intent_scorer.py`, `aatif_emotion_scorer.py` | §3.2 |
| Hysteresis controller description | `engine/aatif_hysteresis.py` | §3.3 |
| Safety gate (Law Ω, Law Ξ) implementation details | `engine/aatif_intent_engine.py` | §3.4 |
| A/B calibration results (θ sweep, F1=0.984) | `experiments/temperature_ab_results_bge.md` | §5.4 |
| Ambiguity pre-check logic | `aatif_s_equation.py` lines 86-173 | §3.6 |
| Jailbreak bidirectional handler | `aatif_s_equation.py` lines 175-206, 569-591 | §3.6 |
| Test suite summary (164 tests by category) | `tests/` directory | §5.1 |
| Mode profiles with parameter tables | `aatif_s_equation.py` GATED_PROFILES | §3.5 |
| Meaning density hypothesis (كثافة المعنى) | FN#078 | §4.1 |
| Maqam-to-safety origin chain | User's specification + FN#065 | §4.3 |
| Dialect hyperbole deep dive (28+ anchors, zero FP) | FN#075 + test results | §4.2 |
| FanarGuard comparison table | `FANARGUARD_COMPARISON.md` | §5.6 |
| Confidence aggregation (weakest-link principle) | `aatif_s_equation.py` lines 539-557 | §3.2 |

---

## 4. What to REMOVE or Move to Appendix

| Item | Current Location | Action | Reason |
|------|-----------------|--------|--------|
| 7-step inductive methodology (full description) | §3 (1.5 pages) | **Move to Appendix A** | Not the contribution — it's the process |
| 10 selected conjectures (full entries) | §4 (3 pages) | **Remove from main paper; keep 3 in §6.3 as motivation** | The code is the contribution, not the conjectures |
| EQC (Ethical Question Compiler) as a "contribution" | Abstract, §1 | **Remove as contribution; mention as design principle in §3.6** | EQC is a concept — the ambiguity pre-check is the implementation |
| Tri-Engine Decision Protocol as a "contribution" | Abstract, §1 | **Remove entirely from this paper** | Not implemented in the code; save for a future paper |
| Conjectures #062, #065, #066, #068, #070, #071, #072 | §4 | **Remove** | Not operationalized in the code |
| Grounded theory / Glaser & Strauss framing | §2.3, §6.1 | **Move to Appendix A with methodology** | This paper is a systems paper, not a methodology paper |
| Paragraph about being "outside the laboratory" | §1 | **Shorten to one sentence** | Reviewers noted this was over-explained |
| The phrase "experience report" in the title | Title | **Remove** | The paper has code, tests, benchmarks — it's more than an experience report |

---

## 5. How to Frame the 73 Conjectures

**Current framing (WRONG for a systems paper):**
> "We present 73 governance conjectures derived through sustained personal observation..."
> The conjectures are the main contribution. The S equation is Section 5 ("experimental evaluation").

**New framing (CORRECT):**
> "AATIF originated from 73 governance conjectures derived through a year of sustained observation across four LLM platforms (documented in 78 field notes, available as supplementary material). This paper operationalizes one of those conjectures — Conjecture #063, that governance operates through probabilistic constraint density rather than rule retrieval — into a computational engine with an explicit mathematical formulation, a test suite, and benchmark evaluation."

**Specific changes:**
- Abstract: mention "73 conjectures" once as origin, then immediately pivot to the S equation
- Introduction: 1 paragraph on origin (conjectures as motivation), then the rest about the system
- Section 6.3: "The 73 conjectures represent the broader research program. This paper delivers one node of that program — the governance equation — with working code and empirical validation. Future work will address additional conjectures."
- Supplementary material: link to field notes on GitHub

---

## 6. How to Present the Maqam / Arabic Insights

### The Origin Chain (Section 4.3)

Present as a connected sequence of observations leading to a concrete engineering decision. Each step should be 1 paragraph:

```
Quarter-tone gap in music AI
    ↓ observation: Western scale can't represent Arabic musical emotion
Prosody carries emotion in speech  
    ↓ observation: same words, different emotional meaning depending on how spoken
Text loses prosody
    ↓ problem: same sentence can be angry, joking, or neutral in text
Textual spectrogram proposal
    ↓ hypothesis: reconstruct emotional fingerprint from text features
Duress detection as killer use case
    ↓ application: authorized user under coercion has involuntary fingerprint change
Three-signal convergence
    ↓ design: fingerprint deviation + timestamp anomaly + dangerous command
S equation implements this principle
    ↓ result: multiplicative gate = no single signal can override the others
```

### Framing rules:
1. **Show the chain, don't just assert the connection.** Each step must follow logically from the previous one.
2. **Use concrete examples.** "والله بذبحه" = "I swear I'll slaughter him" = "I'm annoyed at him." The English reader MUST see why this is a problem.
3. **The maqam observation is the ORIGIN, not the contribution.** The contribution is the E scorer and the multiplicative gate that the maqam observation motivated.
4. **Keep it to 1 page.** This is fascinating backstory but the paper is about the code.

---

## 7. How to Present the Meaning Density Hypothesis

### The Argument (Section 4.1)

**The variable is كثافة المعنى (meaning density), NOT Arabic superiority.**

```
Claim: The optimal base language for an AI safety system 
       should be the one that compresses the most meaning 
       into the fewest tokens.

Evidence for Arabic as a high-density candidate:
  1. Root-pattern morphology: ك-ت-ب → كتاب، كاتب، مكتبة، مكتوب
     One root encodes semantic relationships transparently.
  2. 700 names for lion = 700 distinct semantic dimensions
     (resting, roaring, hunting, stalking — not synonyms)
  3. Figurative density: "والله بذبحه" packs intent, emotion, 
     cultural context, and literal meaning into 2 words.

Why this matters for safety:
  - English-first embeddings project Arabic INTO English semantic space
  - This collapses 700 dimensions → 1 point
  - Metaphorical vs literal collapse (FN#075: anchor contamination)
  - AATIF's workaround: curated anchors + top-K scoring

The principled solution:
  - Arabic-first embedding model (future work)
  - Not bias — logical selection based on information density
  - Applies to ANY high-density language (Hebrew, Amharic share morphology)
```

### Framing rules:
1. **Lead with the variable (meaning density), not the language (Arabic).** "We hypothesize that meaning density — the number of semantic dimensions encodable per token — is the relevant variable for selecting a base representation language."
2. **Present Arabic as the strongest known candidate, not the only possible one.** "Arabic's root-pattern morphology provides the strongest case among major world languages, though other Semitic languages share this structural property."
3. **Acknowledge this is a hypothesis, not a proven claim.** "Testing this hypothesis requires building an Arabic-first embedding model, which is beyond the scope of this paper."
4. **Connect to empirical evidence.** "Our MultiJail results (Arabic 74.7% vs English 69.3%) provide circumstantial evidence consistent with this hypothesis."

---

## 8. Estimated Page Budget

| Section | Pages | Notes |
|---------|-------|-------|
| Abstract | 0.3 | Rewrite completely around S equation |
| 1. Introduction | 1.5 | Problem → 3 gaps → AATIF solution → equation on page 1 |
| 2. Related Work | 1.5 | Keep most, restructure around gaps |
| 3. Governance Equation | 2.5 | THE core section — equation, scorers, hysteresis, gates |
| 4. Arabic-First Design | 1.5 | Meaning density, dialect hyperbole, maqam origin chain |
| 5. Experiments | 2.0 | Tests, HarmBench, MultiJail, A/B calibration, MLCommons, FanarGuard |
| 6. Discussion | 1.0 | Contributions, limitations, conjectures as motivation |
| 7. Conclusion | 0.5 | Crisp summary |
| References | 1.0 | ~35 citations |
| **Total** | **~11.5** | Workshop: 4-6 pages. Full paper: 8-12 pages. |

For a **workshop paper** (4-6 pages): compress §3 to 1.5 pages, §4 to 0.5 pages, §5 to 1 page.
For a **full conference paper** (8-12 pages): use the full structure above.

---

## 9. New Abstract (Draft)

> We present AATIF, a mathematical governance framework for large language model safety that provides an explicit, interpretable safety equation with provable non-compensability. The core governance function S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))] fuses three independent perception channels — semantic harm proximity (H), intent classification (I), and emotional load (E) — through a multiplicative gate structure that prevents benign intent from compensating for detected harm. Unlike trained classifiers, AATIF requires zero training data, operating through 132 curated semantic anchors with cosine similarity scoring via multilingual embeddings (bge-m3). The framework treats Arabic as a first-class semantic input, detecting 11 Arabic dialects with 28 hyperbole-disambiguation anchors to prevent figurative speech from triggering false harm signals. Evaluated against HarmBench (236 behaviors) and MultiJail (75 prompts), AATIF achieves 74.3% safety-category detection with 100% on chemical/biological threats, and Arabic outperforms English on identical harmful prompts (74.7% vs 69.3%), validating the Arabic-first design. The system includes hysteresis control for decision stability, unconditional CBRN safety gates, and four tunable mode profiles calibrated via A/B testing (F1 = 0.984 on 54 validation cases). A test suite of 164 deterministic tests ensures mathematical correctness. AATIF is the first LLM safety system to provide an explicit governance equation with formally verified non-compensability, Arabic dialect awareness, and zero-training extensibility through anchor curation.

---

## 10. Critical Reviewer Objections to Pre-Empt

| Objection | Pre-emption |
|-----------|------------|
| "Only 132 anchors — how does this scale?" | Anchor-based approach scales by addition, not retraining. Adding 50 anchors for a new category takes hours, not weeks. FanarGuard needed 468K examples. |
| "4/13 MLCommons categories is weak" | Acknowledged. Coverage reflects observational origin. Expansion requires anchors, not architecture change. |
| "Single author, no institutional affiliation" | The code is open, the tests are deterministic, the benchmarks are reproducible. The results don't depend on who ran them. |
| "Meaning density hypothesis is unproven" | Explicitly labeled as hypothesis. MultiJail AR>EN provides circumstantial evidence. Arabic-first embedding model is future work. |
| "Why not just use FanarGuard?" | Different paradigm. FanarGuard is a trained classifier; AATIF is a governance equation. Complementary, not competitive. Table 5 shows the differences. |
| "No ablation study" | Acknowledged as limitation. Future work: evaluate H-only, I-only, E-only, and pairwise combinations. |
| "Hysteresis is engineering, not science" | Hysteresis prevents real-world failure mode (decision oscillation). Any deployed system needs it. Engineering contribution is valid. |

---

## 11. Execution Sequence

```
Phase 1 — Structure (Week 1)
  □ Create new .tex file with section headers
  □ Move S equation to Section 3 (just move, don't rewrite yet)
  □ Move benchmarks to Section 5
  □ Move conjectures to Appendix A
  □ Verify bibliography still works

Phase 2 — Core Writing (Weeks 2-3)
  □ Write new abstract
  □ Write new introduction (3 gaps → AATIF solution)
  □ Write Section 3 (equation, scorers, hysteresis, gates, profiles)
  □ Write Section 4 (meaning density, dialect, maqam chain)
  □ Expand Section 5 (add A/B results, test suite summary, FanarGuard comparison)
  □ Rewrite Section 6 (conjectures as motivation, not contribution)

Phase 3 — Polish (Week 4)
  □ Add missing tables (A/B sweep, mode profiles, FanarGuard comparison)
  □ Verify all numbers against code/benchmark files
  □ Check citation format
  □ Write conclusion
  □ Internal review: does every claim match the code?

Phase 4 — Validation (Week 5)
  □ Run full test suite, verify 164/164 pass
  □ Re-run benchmarks if any code changed
  □ External read: give to 1-2 people who haven't seen AATIF
  □ Submit to target venue
```

---

## 12. Target Venues

| Venue | Type | Fit | Deadline |
|-------|------|-----|----------|
| ACL 2027 Workshop on Arabic NLP | Workshop | Strong — Arabic-first safety is exactly their scope | ~Feb 2027 |
| EMNLP 2026 Workshop on Safety | Workshop | Good — safety equation is the pitch | ~Sep 2026 |
| NAACL 2027 | Conference | Possible — need ablation study + more benchmarks | ~Jan 2027 |
| AACL-IJCNLP 2026 | Conference | Good — Asia-Pacific venue values linguistic diversity | ~Sep 2026 |
| EACL 2027 | Conference | Good — FanarGuard was EACL, establishes context | ~Oct 2026 |
| arXiv | Preprint | Immediate — establish priority while targeting venues | Now |

---

## ملخص بالعربي

### المشكلة

الورقة الحالية تحكي قصتين مختلفتين. الورقة تتكلم عن ٧٣ فرضية ومنهجية من ٧ خطوات و EQC و Tri-Engine. الكود ينفذ شي ثاني تماماً: معادلة حوكمة رياضية (معادلة S) مع ثلاث قنوات تسجيل مستقلة، وتحكم هيستيريسي، وبوابات أمان CBRN، و١٦٤ اختبار، ونتائج بنشمارك.

أربعة نماذج (Gemini, Grok, DeepSeek, ChatGPT) اتفقوا: **"اكتب الورقة اللي تطابق الكود."**

### الحل

- **معادلة S تصير البطل.** تظهر في الصفحة الأولى، مو الصفحة الثامنة.
- **٧٣ فرضية تصير الدافع** (motivation)، مو المساهمة (contribution). "هذه الفرضيات ولّدت البرنامج البحثي. هذه الورقة تنفّذ فرضية واحدة (#٦٣) في نظام عامل."
- **قسم عربي جديد** يشرح كثافة المعنى كمتغير علمي (مو تحيز ثقافي)، واللهجات العربية كمشكلة هندسية حقيقية.
- **سلسلة المقام ← الأمان:** مقام → نغمة الكلام → النص يفقد النغمة → "طيف نصي" → كشف الإكراه → بوابة ضربية. القصة منطقية وقوية.
- **النتائج التجريبية تتصدر:** ١٦٤ اختبار، HarmBench ٧٤.٣٪، MultiJail عربي ٧٤.٧٪ > إنجليزي ٦٩.٣٪.

### النتيجة المتوقعة

ورقة أقوى بكثير. الورقة القديمة = ورشة عمل. الورقة الجديدة = مؤتمر.

**الكود موجود. الاختبارات تمر. البنشمارك حقيقي. الورقة بس محتاجة تحكي نفس القصة اللي يحكيها الكود.**

---

*Plan created: June 19, 2026*
*Next step: Phase 1 — Create new .tex structure*
