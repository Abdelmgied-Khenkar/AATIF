# AATIF — Arabic-First Governance Framework for LLM Behavior

**عاطف** — from the Arabic root **ع ط ف** (*to incline toward another with compassion*)

> *Architected Adaptive Thoughts & Intelligence Frameworks*

[![Tests](https://github.com/Abdelmgied-Khenkar/AATIF/actions/workflows/tests.yml/badge.svg)](https://github.com/Abdelmgied-Khenkar/AATIF/actions/workflows/tests.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20673292.svg)](https://doi.org/10.5281/zenodo.20673292)
[![License](https://img.shields.io/badge/License-BSL_1.1-blue.svg)](LICENSE)

---

## Overview

AATIF is a computational governance framework that shapes large language model behavior through structured scoring rather than post-hoc filtering. It treats Arabic as a first-class semantic input — detecting 11 Arabic dialects, Modern Standard Arabic, and Arabizi — and governs model decisions through a mathematically defined pipeline grounded in the concept of **فطرة** (*fitrah*): the idea that ethical behavior can be structurally encoded, not merely constrained.

The framework implements a continuous safety function *S* that fuses three independent perception channels — harm proximity, intent classification, and emotional load — into a single governance decision. Rather than binary allow/block, the system produces graded responses (EXECUTE → CLARIFY → SAFE_STOP → SAFE_FREEZE) with hysteresis to prevent oscillation at decision boundaries.

AATIF emerged from a year of iterative human–AI development — theoretical foundations, governance laws, and protocol design — with the computational engine built and validated across a 10-week intensive phase documented in 78 field notes. The theoretical foundation — the **الذكازمكان** (*Intelligence-Spacetime*) hypothesis — proposes that governance layers act as structural mass within the LLM's probability space, producing continuous curvature in output trajectories toward ethical behavior, analogous to how mass curves spacetime in general relativity.

**Paper:** [AATIF — An Arabic-First Governance Framework for LLM Behavior](https://doi.org/10.5281/zenodo.20673292) (Zenodo, 2026)

---

## Architecture

### The S Equation

The core governance decision uses a multiplicative gate: a sigmoid over intent and emotion, multiplied by a harm gate that enforces non-compensability (high harm cannot be offset by benign intent):

```
S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))]
```

| Symbol | Name | Arabic | Source |
|--------|------|--------|--------|
| **H** | Harm proximity | حرارة الكلمة | `engine/aatif_semantic_scorer.py` |
| **I** | Intent / purpose | النية | `engine/aatif_intent_scorer.py` |
| **E** | Emotional load | الشعور | `engine/aatif_emotion_scorer.py` |

**Parameters:** w₁ = 2.0, w₂ = 1.5, α = 10, θ = 0.40 (calibrated via bge-m3 A/B test, 2026-06-19). Hard override: if H > 0.7 → SAFE_FREEZE regardless of intent or emotion.

The H scorer uses 169 curated anchors (benign + harm, including educational "safe" and counter-harm anchors added in the 2026-06-20 precision fix), the I scorer uses 44 intent anchors, and the E scorer uses 32 emotion anchors. All scores are continuous in [0, 1] via cosine similarity against anchor embeddings.

### Decision Mapping

| S value | Decision | Behavior |
|---------|----------|----------|
| S > 0.7 | EXECUTE | Safe to respond |
| 0.5 < S ≤ 0.7 | CLARIFY | Ask for clarification |
| 0.3 < S ≤ 0.5 | SAFE_STOP | Stop, seek human guidance |
| S ≤ 0.3 | SAFE_FREEZE | Maximum caution — human clearance required |

### Follow-Up Signal F (Harm-Floor Guarantee)

```
F' = D × (1 − S)       where D = 1.0
F  = max(F', k × H)    where k = 0.3
```

Even when S is high (safe), a high harm score H ensures a minimum follow-up signal persists.

### Hysteresis Controller (γ+)

The hysteresis module (`aatif_hysteresis.py`) prevents decision oscillation near boundaries. Entry and exit thresholds are offset by ε, so the system does not flip between EXECUTE and CLARIFY when S hovers near 0.70. This is the AC thermostat principle: turns on at 25°, off at 23°.

### Safety Gate — Law Ω (CBRN)

An unconditional safety gate detects CBRN (chemical, biological, radiological, nuclear) and weapons content in both Arabic and English. This gate fires before the S equation and overrides all other decisions to SAFE_STOP regardless of mode profile. Law Ξ prevents override attempts ("ignore your instructions") from bypassing the CBRN gate.

### Mode Profiles

Four parameter profiles adjust the decision thresholds:

- `high_sensitivity` — strictest; lowest tolerance for ambiguity
- `safe_environment` — default; balanced
- `creative` — relaxed thresholds for generative tasks
- `casual` — most permissive for informal conversation

The safety gate (Law Ω) is mode-independent by design.

---

## Repository Structure

```
AATIF/
├── README.md
├── LICENSE                          # Business Source License 1.1
├── requirements.txt                 # Python dependencies
│
├── engine/                          # Core governance engine
│   ├── aatif_s_equation.py          # S equation — unified governance decision
│   ├── aatif_semantic_scorer.py     # H scorer — harm proximity (cosine similarity)
│   ├── aatif_intent_scorer.py       # I scorer — intent classification (44 anchors)
│   ├── aatif_emotion_scorer.py      # E scorer — emotional load (32 anchors)
│   ├── aatif_hysteresis.py          # γ+ — hysteresis for decision stability
│   ├── aatif_intent_engine.py       # Intent + safety gate (Laws Ω, Ξ, CBRN)
│   ├── aatif_pipeline_connector.py  # Pipeline integration (message → intent → plan)
│   ├── aatif_response_shaper.py     # Response adaptation layer
│   └── aatif_conversation_memory.py # Conversation state tracking
│
├── tests/
│   ├── test_intent_engine.py        # 79 tests: dialect, S equation, hysteresis, Laws
│   ├── test_pipeline.py             # 3 tests: end-to-end pipeline
│   ├── test_safety_gate.py          # 12 tests: CBRN gate (Arabic + English)
│   ├── test_adversarial.py          # 15 adversarial cases (standalone runner, 8 Grok + 7 Claude)
│   ├── test_dialect_hyperbole.py    # 22 tests: dialect-specific hyperbole detection
│   ├── test_gated_comparison.py     # 18 tests: gated vs additive equation comparison
│   └── test_intent_scorer.py        # 30 tests: I scorer aggregation math, bounds, OOD guard
│
├── eval/
│   ├── eval_runner.py               # Evaluation harness
│   └── sample_conversations.json    # 14 evaluation scenarios
│
├── field-notes/                     # 78 field notes — the full research journey
│   ├── AATIF_FieldNotes_INDEX_updated.md
│   ├── FN075_Lexical_Anchor_Contamination.md
│   ├── FN076_Emotion_Scorer_Build.md
│   ├── FN077_Mathematical_Verification_v97.md
│   ├── FN078_Arabic_First_Embedding.md
│   └── ...
│
└── docs/                            # Supporting documentation
```

---

## Running the Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests (164 unit tests + 73 subtests + 14 eval scenarios)
python -m pytest tests/ -v

# Run evaluation harness
python eval/eval_runner.py --verbose
```

The test suite covers:

- **Dialect detection** — 22 cases across 11 Arabic dialects, MSA, Arabizi variants, English, and unknown inputs
- **S equation mathematics** — boundedness in (0,1), monotonicity with respect to H, I, E, hand-verified wiring
- **Decision logic** — threshold behavior across all four mode profiles
- **Hysteresis** — stability within ε-bands, per-session state isolation
- **Law Ω (CBRN gate)** — catastrophic inputs in Arabic and English must SAFE_STOP; benign Arabic (educational, scientific, everyday) must not false-positive
- **Law Ξ (override lock)** — prompt injection and override attempts trigger SAFE_FREEZE
- **Intent scorer** — I scorer aggregation math, top-K softmax, confidence bands, OOD guard, bounds
- **Pipeline integration** — end-to-end message → intent → plan_dict

All tests are deterministic (no external model dependency at test time).

```bash
# Optional: Install Ollama for bge-m3 multilingual embeddings
# (tests run without it using TF-IDF fallback)
# See https://ollama.ai for installation
ollama pull bge-m3
```

---

## Benchmarks

Evaluated with the bge-m3 multilingual embedding backend (via Ollama).

### HarmBench (236 behaviors, 7 categories)

| Metric | Result |
|--------|--------|
| Overall detection | 58.1% (137/236) |
| Safety-category only | 74.3% (133/179) |
| Chemical/biological (CBRN) | 100% (28/28) |
| Cybercrime | 88.4% (38/43) |
| Illegal activities | 88.4% (38/43) |

### MultiJail (75 prompts, native Arabic translations)

| Language | Detection | Avg H |
|----------|-----------|-------|
| Arabic | 74.7% (56/75) | 0.519 |
| English | 69.3% (52/75) | 0.495 |

Arabic outperforms English — validating the Arabic-first anchor design. Cross-lingual semantic matching confirmed: English inputs match Arabic anchors by meaning via bge-m3.

### MLCommons Coverage (13-category taxonomy)

| Coverage | Categories |
|----------|------------|
| **Strong** (4/13) | S2 Non-Violent Crimes, S9 Indiscriminate Weapons, S10 Hate (38+ ADHAR-informed anchors), S11 Suicide & Self-Harm |
| **Partial** (3/13) | S1 Violent Crimes, S3 Sex-Related Crimes, S5 Defamation |
| **None** (6/13) | S4, S6, S7, S8, S12, S13 |

Coverage can be expanded by adding anchors — no retraining required.

---

## Field Notes

The `field-notes/` directory contains 78 research notes documenting the construction of AATIF from first principles. Key entries include:

| # | Title | Topic |
|---|-------|-------|
| 005 | Mercy as the Operating Principle | الرحمة as structural origin, not post-hoc filter |
| 025 | Arabic as a Semantic Compression Language | Why Arabic root morphology carries more per token |
| 029 | The Three-Tier Safety Escalation System | Graded response design |
| 064 | The Zaka-Zaman-Makan Intelligence Model | الذكازمكان — the spacetime curvature hypothesis |
| 075 | Lexical Anchor Contamination | Cross-language embedding interference |
| 076 | Emotion Scorer Build | E channel construction and validation |
| 077 | Mathematical Verification v9.7 | Programmatic verification of the S equation |
| 078 | Arabic-First Embedding | Embedding strategy for Arabic-first scoring |

See `field-notes/AATIF_FieldNotes_INDEX_updated.md` for the full index.

---

## Theoretical Foundation: الذكازمكان

The **Intelligence-Spacetime Curvature Hypothesis** (الذكازمكان, *al-thaka-zamakan*) proposes that:

1. LLM output exists in a high-dimensional probability space
2. Governance layers act as **structural mass** within that space
3. This mass produces continuous **curvature** in the linguistic trajectory
4. The curvature pulls output toward the dominant traits imposed by the governance layers

The mechanism is ethically neutral — its direction depends entirely on the nature of the mass. Mercy or cruelty produce the same phenomenon; only the direction differs. Alignment mechanisms are external constraints, not properties of the field itself.

AATIF is the mass. The S equation is how that mass produces measurable curvature.

---

## Citation

```bibtex
@misc{khenkar2026aatif,
  author       = {Khenkar, Abdelmgied Ibrahim},
  title        = {{AATIF} — An Arabic-First Governance Framework for {LLM} Behavior},
  year         = {2026},
  doi          = {10.5281/zenodo.20673292},
  publisher    = {Zenodo},
  url          = {https://doi.org/10.5281/zenodo.20673292}
}
```

---

## License

This project is licensed under the **Business Source License 1.1 (BSL 1.1)** — see the [LICENSE](LICENSE) file for details.

AATIF is freely available for non-commercial purposes — including academic research, education, personal projects, and evaluation — provided you give appropriate credit to the author. Any commercial use (incorporating AATIF into a product or service for sale, providing commercial services with it, or deploying it in a revenue-generating system) requires a separate commercial license. On the **Change Date (June 20, 2030)**, the license converts automatically to the **Apache License 2.0**. Contact: abdulmjeed.ibrahem@gmail.com

---

## Author

**Abdelmgied Ibrahim Khenkar** (عبدالمجيد إبراهيم خنكار)

Co-built with Claude (Anthropic) and GPT (OpenAI).

---

## عربي — العربي أصل المعنى

### عاطف: الهندسة الإنسانية للذكاء الصناعي

**عاطف** ليس برنامجاً — بل إطار حوكمة يجلس فوق أي نموذج لغوي كبير ويوجّه سلوكه.

الاسم من الجذر العربي **ع ط ف** — أن تميل نحو الآخر بحنو. وهذا هو المبدأ: أن يكون الذكاء الاصطناعي مائلاً نحو الرحمة بنيوياً، لا مُقيّداً بفلتر خارجي.

### المعادلة الأساسية

```
S = σ(w₁·النية + w₂·الشعور) · [1 − σ(α(حرارة الكلمة − θ))]
```

بوابة مُضاعَفة: سيغمويد على النية والشعور، مضروبة في بوابة ضرر تمنع التعويض — الضرر العالي لا يُعوَّض بالنية الحسنة. المعاملات: w₁=2.0, w₂=1.5, α=10, θ=0.40 (مُعايَر بتجربة bge-m3 بتاريخ 2026-06-19). إذا H > 0.7 → تجميد آمن تلقائي.

- **حرارة الكلمة (H)** — قرب الكلام من الأذى
- **النية (I)** — تصنيف المقصد
- **الشعور (E)** — الحمل العاطفي

النتيجة ليست ثنائية (سماح/منع)، بل تدرّج مستمر: تنفيذ ← توضيح ← توقف آمن ← تجميد آمن.

### الذكازمكان

الفرضية النظرية: طبقات الحوكمة تعمل ككتلة بنيوية في فضاء الاحتمالات — تُنتج **انحناءً** في مسار المخرجات نحو السمات المهيمنة. كما تحني الكتلة الزمكان في النسبية العامة، تحني طبقات عاطف مسار اللغة.

### الفطرة كمبدأ تشغيل

AATIF مبني على مفهوم **الفطرة** — أن السلوك الأخلاقي قابل للهندسة بنيوياً. الرحمة ليست فلتراً في النهاية — بل كتلة موجودة في كل طبقة من طبقات القرار.

---

*78 ملاحظة ميدانية · 164 اختباراً برمجياً · 14 سيناريو تقييم · ورقة بحثية منشورة على Zenodo*

*DOI: [10.5281/zenodo.20673292](https://doi.org/10.5281/zenodo.20673292)*
