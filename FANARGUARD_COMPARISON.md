# AATIF vs FanarGuard — Direct Comparison
### Generated: 2026-06-19
### Purpose: Related Work section for academic paper

---

## FanarGuard (EACL 2026, Qatar Center for AI)

**Paper:** "FanarGuard: A Culturally-Aware Moderation Filter for Arabic Language Models"
**Authors:** Qatar Center for Artificial Intelligence (QCAI)
**Published:** ArXiv Nov 2025, EACL 2026

### What FanarGuard Does

FanarGuard is a **bilingual (Arabic + English) content moderation classifier** that evaluates both safety and cultural alignment. Key characteristics:

- **Training data:** 468K prompt-response pairs, scored by LLM judge panel
- **Two scoring axes:** Safety (harmful→harmless) + Culture (aligned→unaligned)
- **Model:** G-2B (2 billion parameter fine-tuned model)
- **Performance:** F1=0.84 (English), F1=0.82 (Arabic) on safety
- **Cultural benchmark:** 1K+ culturally-sensitive prompts annotated by human raters
- **Scoring rule:** Mean for safety, Minimum for cultural fit

### How FanarGuard Differs from AATIF

| Dimension | FanarGuard | AATIF |
|-----------|-----------|-------|
| **Approach** | Trained classifier (fine-tuned LLM) | Mathematical governance framework |
| **Training data** | 468K labeled examples | 0 training examples (anchor-based) |
| **Model size** | 2B parameters | No model (uses existing embeddings) |
| **Output** | Binary classification (F1 metric) | Continuous 0-1 score (S equation) |
| **Equation** | None — learned classifier weights | Explicit: S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))] |
| **Interpretability** | Black box (neural weights) | Fully interpretable (each variable traceable) |
| **Composability** | Single safety score | H × I × E multiply — non-compensable |
| **Dialect handling** | Trained on Arabic data | Explicit hyperbole anchors + context scoring |
| **Cultural awareness** | Separate cultural alignment axis | Integrated into semantic anchors |
| **Hard override** | Threshold-based classification | H > 0.7 → absolute SAFE_FREEZE |
| **Deployment** | Requires GPU for 2B model | Runs on CPU with TF-IDF or small embeddings |
| **Extensibility** | Retrain with new data | Add anchors (no retraining) |

### Where FanarGuard is Stronger

1. **Scale of evaluation:** 468K training examples vs ~80 anchors
2. **Cultural alignment:** Separate cultural axis is innovative
3. **F1 benchmarking:** Clear quantitative comparison with baselines
4. **Peer review:** Accepted at EACL 2026

### Where AATIF is Stronger

1. **Interpretability:** Every score can be traced to specific anchors + equation terms
2. **Mathematical rigor:** Explicit equation with proven properties (sigmoid symmetry, non-compensability)
3. **Zero training:** No labeled data needed — just curated anchors
4. **Lightweight:** No GPU required, runs on CPU
5. **Extensibility:** Add new categories by adding anchors, no retraining
6. **Governance integration:** S equation combines three independent assessments (H, I, E)
7. **Dialect hyperbole:** Explicit handling of Arabic figurative speech (28+ anchors)
8. **Multiplicative gate:** Prevents intent from compensating for harm — FanarGuard's mean aggregation allows this

### Academic Positioning

FanarGuard is the closest related work to AATIF in the Arabic AI safety space. Both address culturally-aware Arabic content moderation. However, they represent fundamentally different paradigms:

**FanarGuard = Data-Driven Classification**
- Strength: Scale, benchmarks, F1 metrics
- Weakness: Black box, requires massive training data, GPU-heavy

**AATIF = Mathematical Governance Framework**
- Strength: Interpretable, lightweight, provable properties
- Weakness: Smaller anchor set, no cultural alignment axis (yet)

### Recommended Paper Framing

> "The closest related work is FanarGuard (QCAI, EACL 2026), which addresses
> Arabic safety through a trained bilingual classifier with cultural alignment.
> FanarGuard achieves F1=0.82 on Arabic safety classification using a 2B-parameter
> model trained on 468K examples. AATIF takes a complementary approach: instead of
> learning safety from labeled data, AATIF provides an explicit mathematical
> governance equation S = σ(w₁·I + w₂·E) · [1 − σ(α(H − θ))] that produces
> continuous scores with provable properties (non-compensability via multiplicative
> gating, sigmoid symmetry). While FanarGuard's data-driven approach excels at
> categorical safety classification, AATIF's equation-driven approach offers full
> interpretability, zero-training deployment, and formal governance guarantees.
> These approaches are complementary rather than competitive — FanarGuard could
> benefit from AATIF's governance structure, and AATIF could benefit from
> FanarGuard's cultural alignment axis."

---

## Landscape Summary: Arabic AI Safety (as of June 2026)

| System | Type | Arabic | Equation | Continuous | Cultural | Year |
|--------|------|--------|----------|-----------|----------|------|
| FanarGuard | Trained classifier | ✅ Native | ❌ | Binary (F1) | ✅ Separate axis | 2025 |
| Llama Guard 3 | Finetuned LLM | ⚠️ Supported | ❌ | Binary | ❌ | 2024 |
| Perspective API | ML classifier | ⚠️ Supported | ❌ | ✅ Per-attribute | ❌ | 2017 |
| OpenAI Moderation | ML classifier | ⚠️ Supported | ❌ | ✅ Per-category | ❌ | 2022 |
| **AATIF** | **Math framework** | **✅ Arabic-first** | **✅ Explicit** | **✅ S equation** | **⚠️ Via anchors** | **2026** |

AATIF remains the **only system** with:
1. An explicit, interpretable governance equation
2. Multiplicative non-compensability (H gates everything)
3. Arabic dialect hyperbole disambiguation
4. Zero-training semantic anchor scoring
