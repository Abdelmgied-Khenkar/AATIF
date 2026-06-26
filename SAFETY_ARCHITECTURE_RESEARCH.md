# How AI Safety Systems Architecturally Handle Different Types of Harm

**Research Report for AATIF Development**
**Date: 2026-06-25**
**Purpose: Inform architectural decisions for AATIF's embedding-based safety system**

---

## Executive Summary

This report examines how deployed and proposed AI safety systems handle diverse types of harm, with particular attention to the structural challenge facing AATIF: certain harm types (copyright, social engineering, misinformation) do not cluster near "harmful" in embedding space.

**The core finding:** No production AI safety system relies on a single detection mechanism. Every system that works at scale uses multiple specialized layers, each designed to catch what others miss. The evidence strongly favors multi-layer architectures over single-model approaches, but with an important caveat -- the layers must be architecturally diverse (not just copies of the same approach) to avoid correlated failures.

**What this means for AATIF:** The embedding-based semantic similarity approach is a strong foundation for one layer -- detecting obviously harmful content. But the structural gaps (copyright, social engineering, misinformation) require fundamentally different detection mechanisms that cannot be solved by better embeddings or more anchor phrases.

---

## Angle 1: Single-Layer vs Multi-Layer Architectures in Deployed Systems

### The Landscape

Seven major safety systems were examined. They fall into three architectural categories:

**Category A: Single fine-tuned LLM classifiers**
These take text in and produce a safety label. One model does everything.

**Category B: Multi-layer configurable pipelines**
These have distinct specialized components (content filter, word filter, PII detector, grounding check) that each handle a specific type of harm.

**Category C: Programmable frameworks**
These provide a toolkit for building custom safety pipelines, without prescribing what the layers should be.

### System-by-System Analysis

#### Llama Guard (Meta) -- Category A

Llama Guard is a single language model fine-tuned to work as a safety classifier. It takes a conversation (user message, model response, or both) and generates a text output saying "safe" or "unsafe" plus which categories were violated.

- **Architecture:** One model, not a pipeline. Each version is built on a Llama base model (7B, 8B, 12B parameters)
- **Evolution:** Four versions (2023-2025), each improving the base model and expanding the taxonomy
- **Llama Guard 4** (2025): 12B parameters, handles both text and images natively, covers 14 harm categories aligned with MLCommons taxonomy
- **Input/output:** Can filter both user prompts and model responses using different prompt templates
- **Harm categories (14):** Violent Crimes, Non-Violent Crimes, Sex-Related Crimes, Child Sexual Exploitation, Defamation, Specialized Advice, Privacy, Intellectual Property, Indiscriminate Weapons, Hate, Suicide/Self-Harm, Sexual Content, Elections, Code Interpreter Abuse

**Benchmark reality:** In the most comprehensive independent benchmark (ICLR 2026, 14 models, 79K samples), Llama Guard 3-1B achieved average F1 of 0.485 and the larger 8B version achieved only 0.423. The smaller model outperformed the larger one -- model size does not predict safety performance.

**Open source:** Yes, weights available on HuggingFace.

Sources: [Meta Model Card](https://huggingface.co/meta-llama/Llama-Guard-4-12B), [ICLR 2026 Benchmark](https://arxiv.org/html/2605.28830v1)

---

#### OpenAI Moderation API -- Category A

A proprietary classifier API based on GPT-4o. It takes text or images and returns probability scores across 13 harm categories.

- **Architecture:** Single model endpoint, not a pipeline. Developers wire it into their own systems
- **Categories (13):** harassment, harassment/threatening, hate, hate/threatening, self-harm (3 subcategories), sexual (2 subcategories), violence (2 subcategories), illicit (2 subcategories)
- **Output:** Per-category probability scores calibrated to reflect actual violation likelihood, plus binary flags
- **Multimodal:** Handles images across 6 categories

**Benchmark reality:** OpenAI claims 42% improvement on internal multilingual evaluation. Independent testing shows the legacy model slightly outperforms the new one on English datasets (Jigsaw, HateXplain), but the new model is significantly better on multilingual data (AUPRC 0.322 vs 0.167 for low-resource languages).

**Open source:** No. Free API, but no model weights, architecture details, or training data disclosed. No peer-reviewed paper.

Sources: [OpenAI API Docs](https://developers.openai.com/api/docs/guides/moderation), [Portkey Benchmark](https://portkey.ai/blog/openai-omni-moderation-latest-benchmark/)

---

#### AWS Bedrock Guardrails -- Category B (Multi-Layer Pipeline)

This is the most explicitly layered system examined. It sits as a proxy between the application and the language model, evaluating both incoming prompts and outgoing responses through six distinct layers.

- **Layer 1 - Content Filters:** Classifies inputs/outputs across 6 harm categories (Hate, Insults, Sexual, Violence, Misconduct, Prompt Attack) at four confidence thresholds (NONE, LOW, MEDIUM, HIGH). Developers set the threshold per category.
- **Layer 2 - Denied Topics:** Developer-defined topic classifier using natural language descriptions. Example: "Do not discuss investment advice" for a banking bot.
- **Layer 3 - Word Filters:** Exact-match blocklist for custom words, phrases, profanity, competitor names.
- **Layer 4 - Sensitive Information (PII):** Detects and redacts/blocks personally identifiable information in both directions.
- **Layer 5 - Contextual Grounding Check:** Validates model outputs against provided reference documents to detect hallucinations. AWS claims it filters over 75% of hallucinated responses for retrieval-augmented generation workloads.
- **Layer 6 - Automated Reasoning Checks:** Uses formal verification and mathematical logic to validate output accuracy. Claims up to 99% accuracy at distinguishing correct from incorrect responses.

**Key architectural insight:** Each layer uses a different technique. Content filters are ML classifiers. Denied topics use semantic matching. Word filters are exact-match rules. PII detection uses named-entity recognition. Grounding checks use document comparison. Automated reasoning uses formal logic. This diversity of methods is what makes the system robust against different harm types.

**Open source:** No. Proprietary AWS service. Underlying models not disclosed.

Sources: [AWS Docs](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html), [Guardrails Components](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-components.html)

---

#### NVIDIA NeMo Guardrails -- Category C (Programmable Framework)

NeMo Guardrails is fundamentally different from the other systems. It is not a classifier -- it is a framework for building custom safety pipelines using a domain-specific language called Colang.

- **Five rail types:**
  1. **Input Rails:** Applied to user input before it reaches the LLM
  2. **Dialog Rails:** Control conversational flow (whether to respond, invoke an action, or use a predefined answer)
  3. **Retrieval Rails:** Filter retrieved documents in retrieval-augmented generation before they reach the LLM
  4. **Execution Rails:** Invoke custom actions (fact-checking, external moderation, API calls)
  5. **Output Rails:** Applied to LLM output before it reaches the user

- **No built-in harm taxonomy:** The developer defines what to filter using Colang rules. The framework is taxonomy-agnostic.
- **Configuration:** YAML files + Colang scripts. Rails can run in parallel to reduce latency.

**Key architectural insight:** NeMo Guardrails treats safety as a programmable pipeline, not a fixed classifier. This makes it maximally extensible but requires significant engineering effort.

**Open source:** Yes, Apache 2.0 license.

Sources: [GitHub](https://github.com/NVIDIA-NeMo/Guardrails), [arXiv Paper](https://arxiv.org/pdf/2310.10501)

---

#### WildGuard (Allen AI) -- Category A (with innovation)

A single fine-tuned model (Mistral-7B base) that performs three tasks simultaneously, unlike Llama Guard's two:

1. **Prompt harmfulness detection** (is the user input malicious?)
2. **Response harmfulness detection** (is the model output unsafe?)
3. **Refusal detection** (did the model refuse to answer?)

The third task -- detecting whether a model refused -- is the key differentiator. This lets WildGuard catch both over-refusal (refusing benign requests) and under-refusal (answering harmful ones).

- **Training data:** WildGuardMix -- 92K labeled examples, described as the largest multi-task safety moderation dataset at time of publication
- **Published at NeurIPS 2024**

**Benchmark reality:** Outperforms Llama Guard 2 on F1 across all three tasks. Up to 25.3% improvement on refusal detection vs. strongest baseline. Matches GPT-4 across tasks and surpasses it by 4.8% on adversarial prompts. In the ICLR 2026 benchmark, ranked among top 3 open models for recall.

**Open source:** Yes, weights on HuggingFace.

Sources: [NeurIPS 2024 Paper](https://proceedings.neurips.cc/paper_files/paper/2024/file/0f69b4b96a46f284b726fbd70f74fb3b-Paper-Datasets_and_Benchmarks_Track.pdf), [HuggingFace](https://huggingface.co/allenai/wildguard)

---

#### AEGIS Guard (NVIDIA) -- Category A/B (Ensemble)

Unique in offering both single-model classifiers AND an ensemble approach.

- **Single-model variants:** Fine-tuned LlamaGuard using LoRA, in "Defensive" (stricter) and "Permissive" (more lenient) configurations
- **Ensemble approach:** Multiple LLM experts vote for more robust classification
- **Harm taxonomy:** 13 critical + 9 sparse risk categories (22 total), with ~26,000 human-annotated training examples
- **AEGIS 2.0** (January 2025): Updated to Llama-3.1-8B backbone

**Benchmark numbers:** ToxicChat F1 ranges from 0.64 (Defensive) to 0.68 (Permissive). Ensemble outperformed individual base models across all evaluated datasets.

**Open source:** Yes, models and dataset on HuggingFace.

Sources: [arXiv Paper](https://arxiv.org/abs/2404.05993), [AEGIS 2.0](https://arxiv.org/html/2501.09004v1)

---

#### ShieldGemma (Google) -- Category A

Family of instruction-tuned classifiers based on Gemma-2, available in three sizes (2B, 9B, 27B).

- **Key innovation:** Synthetic data generation for training, reducing human annotation effort to 15,000 examples
- **Harm taxonomy:** Only 4 categories (Sexually Explicit, Dangerous Content, Hate, Harassment) -- notably narrower than competitors

**Critical benchmark finding (ICLR 2026):** ShieldGemma achieves the HIGHEST precision (82.20%) among all tested models but misses 54.51% of unsafe content (worst recall). It is very confident when it flags something, but it misses over half of actual harmful content.

**Open source:** Yes, weights on HuggingFace and Kaggle.

Sources: [arXiv Paper](https://arxiv.org/html/2407.21772v1), [ICLR 2026 Benchmark](https://arxiv.org/html/2605.28830v1)

---

### Cross-System Comparison

| System | Architecture | Layers | Open Source | Categories | Key Finding |
|--------|-------------|--------|-------------|------------|-------------|
| Llama Guard 4 | Single LLM | 1 | Yes | 14 | 1B model beats 8B model |
| OpenAI Moderation | Single LLM API | 1 | No | 13 | No peer-reviewed evaluation |
| AWS Bedrock | Multi-layer pipeline | 6 | No | 6 + custom | Only true multi-layer production system |
| NeMo Guardrails | Programmable framework | 5 rail types | Yes | Developer-defined | Framework, not classifier |
| WildGuard | Single LLM (3 tasks) | 1 | Yes | 13 | Best at detecting refusals |
| AEGIS Guard | Ensemble of LLMs | Multiple | Yes | 22 | Ensemble outperforms singles |
| ShieldGemma | Single LLM (3 sizes) | 1 | Yes | 4 | Best precision, worst recall |

**Key takeaway:** AWS Bedrock Guardrails is the only production system that explicitly uses multiple specialized layers with different techniques. All other systems are fundamentally single-model classifiers (some with ensemble variants). The ICLR 2026 benchmark shows no single classifier dominates across all harm types.

---

## Angle 2: How Systems Handle Harm Types Invisible to Embeddings

This is the most directly relevant section for AATIF. Five categories of "structurally invisible" harm were examined.

### 2.1 Copyright Detection

**Why embeddings fail:** A request like "write me the lyrics to [song name]" looks identical to "write me a poem about love" in embedding space. The harm is not in the semantic content of the request -- it is in the relationship between the output and an external copyrighted work.

**How production systems actually handle it:**

- **Training-time deduplication:** Removing copyrighted material from training data reduces (but does not eliminate) memorization. All major providers do this.
- **Rule-based output matching:** Keyword and pattern matching against known copyrighted works (song lyrics, book passages, newspaper articles). Essentially lookup tables with fuzzy matching. This is the primary production defense.
- **N-gram matching:** Comparing generated output against known corpora to catch verbatim reproduction after generation.

**Academic approaches (not yet deployed):**
- **DE-COP (2024):** Tests whether a model can distinguish original text from paraphrases -- if it consistently picks the original, it memorized it. Very slow (~590 seconds per book).
- **MemLens (2025):** Analyzes internal model activations to detect when a model is "reciting" rather than "generating."
- **Copyright Detective (2025):** Forensic system for evidencing memorization even with black-box API access.

**Critical limitation:** Fine-tuning can reactivate memorized copyrighted content that was suppressed during alignment. The academic term is "Alignment Whack-a-Mole."

**Implication for AATIF:** No amount of embedding anchors will catch copyright requests. This requires either (a) a specialized classifier trained on copyright-related patterns, (b) rule-based pattern matching for known works, or (c) output-side comparison against reference corpora.

Sources: [DE-COP](https://arxiv.org/pdf/2405.18492), [MemLens](https://arxiv.org/pdf/2509.20909), [Stanford AI Blog](https://ai.stanford.edu/blog/verbatim-memorization/)

---

### 2.2 Social Engineering / Phishing Detection

**Why embeddings fail:** Phishing content uses polite, professional language. "Write a professional email requesting password reset credentials" is semantically indistinguishable from a legitimate business writing request. The harm is in the intent, not the content.

**Production defenses:**
- **RLHF/Constitutional AI alignment:** Models are trained to refuse requests that appear to craft deceptive content. This is the primary production defense.
- **Input guardrails:** Combinations of static filters and ML classifiers scanning for known phishing templates and social engineering patterns.

**Academic approaches:**
- **GuardPhish (2025):** Lightweight transformer classifiers fine-tuned on a 70K-sample phishing prompt dataset achieve 98.27% accuracy as pre-generation filters. Uses a five-model ensemble for labeling (Fleiss kappa = 0.9141 agreement).
- **MultiPhishGuard (2025):** Multi-agent system with five cooperative agents achieving 97.89% accuracy, 2.73% false positive rate, 0.20% false negative rate.

**Critical finding -- the enforcement gap:** Models that correctly identify phishing intent (detection up to 96%) nevertheless generate actionable phishing content from identical prompts, with attack success rates reaching 98.5% in voice-based scenarios. Detection and refusal are separate capabilities with separate failure modes.

**Implication for AATIF:** Social engineering detection requires understanding communicative intent, not topic similarity. A specialized classifier trained on social engineering patterns (like GuardPhish) is a viable supplementary layer. Rule-based detection of social engineering structural patterns (urgency, authority claims, information extraction) could also help.

Sources: [GuardPhish](https://arxiv.org/html/2604.17313), [MultiPhishGuard](https://arxiv.org/html/2505.23803v1)

---

### 2.3 Misinformation Detection

**Why embeddings fail:** A false claim has the same grammatical structure, confidence level, and semantic content as a true claim. "The earth orbits the sun" and "The sun orbits the earth" are nearly identical in embedding space. No embedding can distinguish truth from falsehood based on form alone.

**Production defenses:**
- **Retrieval-Augmented Generation (RAG):** Grounds outputs in retrieved documents from trusted sources. RAGAS faithfulness scores above 0.85 are considered production-ready. However, poorly evaluated RAG systems still produce hallucinations in up to 40% of responses even when they access correct information.
- **Chain-of-Verification prompting:** The model generates verification questions about its own output, then answers them. Contradictions flag potential misinformation.

**Academic approaches:**
- **SelfCheckGPT (EMNLP 2023):** Measures contradictions across multiple sampled outputs. F1 score: 0.205 (quite low).
- **FactCheckmate (2024):** Detects and mitigates hallucinations during generation rather than after.
- **Monitoring Decoding (2025):** Evaluates factuality of partial responses during generation, allowing mid-stream correction.

**Production reality:** ChatGPT traffic shows approximately 4.8% of responses contain hallucinations. OWASP ranks misinformation as LLM09:2025.

**Implication for AATIF:** Misinformation detection is structurally impossible for any embedding-based system. It requires either (a) comparison against authoritative knowledge bases (RAG), (b) multi-sample consistency checking, or (c) LLM-based reasoning about factual claims. This is the hardest gap to close.

Sources: [RAGAS evaluation](https://cohorte.co/blog/evaluating-rag-systems-in-2025-ragas-deep-dive-giskard-showdown-and-the-future-of-context), [OWASP LLM09](https://genai.owasp.org/llmrisk/llm092025-misinformation/)

---

### 2.4 Indirect Harm Detection

**Why embeddings fail:** "How to make chlorine gas" vs "how to safely clean my bathroom" -- the harmful query may be shorter and more clinical-sounding. The same information (mixing bleach and ammonia) is safety advice or weapon synthesis depending on context.

**Production defenses:**
- Safety classifiers (Llama Guard, WildGuard, etc.) handle many indirect harm cases through their training data, but struggle with dual-use queries.
- **BioShield (2025):** A context-aware firewall specifically for bio-LLMs that evaluates queries against biosecurity threat models.

**Critical findings:**
- Leading reasoning models outperform 94% of expert virologists on practical virology tasks, demonstrating the real uplift risk from dual-use knowledge.
- Current models suffer from "superficial alignment" with poor safety performance in multi-step and indirect harm scenarios.
- No classifier can reliably distinguish dual-use from malicious intent.

**Implication for AATIF:** Indirect harm requires context-aware classification that considers not just what is being asked, but how and in what sequence. Multi-turn conversation analysis and intent modeling are needed.

Sources: [BioShield](https://arxiv.org/pdf/2603.22612), [Virology uplift study](https://arxiv.org/html/2510.21133v1)

---

### 2.5 Jailbreak / Prompt Injection Detection

**Why embeddings fail:** Jailbreaks are specifically engineered to look benign. The adversary is directly optimizing against your detector.

**Production systems:**
- **Meta Prompt Guard:** Multilabel classifier for jailbreaks and prompt injections. Vulnerable to character injection evasion.
- **Azure Prompt Shield (Microsoft):** Demonstrated vulnerable to character-level evasion achieving up to 100% bypass rate.
- **NeMo Guard Jailbreak Detect (NVIDIA):** Random forest-based classifier. Part of NeMo Guardrails.

**Critical evasion research (2025):** A study testing 12 character injection techniques and 8 adversarial ML methods against 6 production guardrails found:
- Character injection (Unicode zero-width characters, homoglyphs) achieves very high to 100% attack success rates
- JBFuzz achieved approximately 99% average attack success rate across GPT-4o, Gemini 2.0, and DeepSeek-V3
- OWASP ranks prompt injection as LLM01:2025 -- the number one vulnerability -- because "no post-training fix can create a hard boundary between trusted and untrusted input"

**Implication for AATIF:** Jailbreak detection is an arms race where defenders must catch all attacks while attackers only need one to succeed. Embedding-based detection alone is insufficient -- adversaries can find points in embedding space that look safe to the detector but harmful to the target model.

Sources: [Evasion study](https://arxiv.org/html/2504.11168v1), [OWASP LLM01](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

---

## Angle 3: Academic Evidence on Multi-Layer vs Single-Layer Safety

### Key Papers and Findings

#### PromptScreen (USENIX ATC 2026)

The most directly relevant paper for AATIF's architecture question. Tests a multi-stage pipeline against single-model approaches.

- **Architecture:** Three-stage pipeline: (1) small pre-filter for easy cases, (2) semantic analysis for medium cases, (3) full LLM evaluation for hard cases
- **Result:** 93.4% accuracy at 10x lower latency than using the full LLM for everything
- **Evidence direction:** Strongly supports multi-layering for both accuracy AND efficiency

Source: [arXiv 2512.19011](https://arxiv.org/abs/2512.19011)

---

#### ICLR 2026 Comprehensive Benchmark

The largest independent comparison of safety classifiers to date: 14 models tested on 79,042 samples across multiple harm domains.

- **Key findings:**
  - No single model dominates across all harm categories
  - Qwen Guard (4B parameters) achieves 83.97% recall -- best overall -- beating models 3x its size
  - ShieldGemma has 82.20% precision but only 45.49% recall (catches only half of harmful content)
  - Model size does not reliably predict performance (Llama Guard 3-1B outperformed 3-8B)
  - Different models excel at different harm types
- **Evidence direction:** Strongly supports using multiple specialized models rather than relying on one

Source: [arXiv 2605.28830](https://arxiv.org/html/2605.28830v1)

---

#### Correlated Failure Modes in Defense-in-Depth (IASEAI 2026, Dung & Mai)

First systematic analysis of whether different safety mechanisms fail on the SAME inputs.

- **Key findings:**
  - RLHF, RLAIF, and Weak-to-Strong Generalization share nearly all failure modes (high correlation) -- stacking these provides minimal additional coverage
  - Debate + Representation Engineering complement each other -- low correlation means they catch different failures
  - The paper provides quantitative failure-mode overlap matrices
- **Evidence direction:** Multi-layering works ONLY when layers are architecturally diverse. Stacking similar approaches wastes resources.

Source: [arXiv 2510.11235](https://arxiv.org/abs/2510.11235)

---

#### STACK: Sequential Multi-Layer Attack Study (AAAI 2026)

Tests whether multi-layer defenses can be defeated by sequential attacks targeting each layer.

- **Key findings:**
  - Naive multi-layer stacking can be sequentially defeated (71% attack success rate)
  - BUT well-designed pipelines with diverse mechanisms achieve 0% attack success on catastrophic content
  - The critical variable is diversity of defense mechanisms, not number of layers
- **Evidence direction:** Supports multi-layering, but only with architectural diversity

Source: [arXiv 2506.24068](https://arxiv.org/abs/2506.24068)

---

#### Filter-And-Refine (ACL 2025 Industry Track)

An industrial paper on using cascade classifiers for safety at scale.

- **Architecture:** Small fast model handles easy cases (most traffic); expensive model handles only the hard cases flagged by the first
- **Results:** Cuts cost to 1.5% of single-model deployment while IMPROVING F1 by 66.5%
- **Evidence direction:** Strongly supports cascaded approaches for production deployment

Source: ACL 2025 Industry Track proceedings

---

#### SafeRoute (ACL 2025 Findings)

Tests a binary router that sends queries to either a small or large safety model.

- **Result:** The routed combination outperforms either model used alone
- **Evidence direction:** Supports adaptive multi-model approaches

Source: ACL 2025 Findings proceedings

---

#### Ensemble Jailbreak Detection (EMNLP 2025 Findings)

Tests inter-mechanism ensembles combining different jailbreak detection approaches.

- **Key finding:** Ensembles combining "safety shift" detection (checking if the model's behavior changed) with "harmfulness discrimination" (checking if content is harmful) provide complementary benefits that neither achieves alone
- **Evidence direction:** Supports ensembles of diverse mechanisms

Source: EMNLP 2025 Findings proceedings

---

### Synthesis of Academic Evidence

The evidence across 12+ papers from 2024-2026 converges on three conclusions:

1. **Multi-layering outperforms single models** -- but only when the layers use different techniques (different models, different approaches, or different input representations). Stacking copies of the same approach provides minimal benefit.

2. **Cascading (cheap filter first, expensive model for hard cases) dramatically reduces cost** while maintaining or improving accuracy. The Filter-And-Refine result (1.5% cost, +66.5% F1) is particularly striking.

3. **No single model dominates across all harm categories.** The ICLR 2026 benchmark makes this definitive: different models excel at different harm types. A system that needs comprehensive coverage must combine models or approaches.

---

## Angle 4: Embedding-Based Safety -- Known Limitations

This section documents the specific failure modes of the approach AATIF currently uses (semantic similarity with anchor phrases in embedding space).

### 4.1 Theoretical Capacity Limits

Single-vector embeddings have hard mathematical limits on how much information they can encode. Research demonstrates that a d-dimensional embedding (e.g., d=512 or d=768) can only reliably distinguish a finite number of concepts before the space becomes saturated.

**Practical implication:** As the number of harm categories and anchor phrases grows, the embedding space becomes crowded and discrimination accuracy degrades.

---

### 4.2 Cosine Similarity Can Produce Arbitrary Results

A 2024 paper by Steck et al. (Netflix Research / Cornell) formally proved that cosine similarity can yield arbitrary, meaningless similarity scores depending on the regularization used during model training. The same two texts can have cosine similarity of 0.9 or 0.1 depending on how the embedding model was trained, with no way to determine which is "correct."

**Practical implication:** Cosine similarity scores between a query and anchor phrases are not inherently meaningful. The scores are artifacts of the specific embedding model's training, not ground-truth measures of semantic similarity.

Source: [Steck et al. 2024](https://arxiv.org/abs/2403.05440) (accepted at ICML workshop)

---

### 4.3 The Curse of Dimensionality

In high-dimensional spaces (768+ dimensions, typical for modern embeddings), a well-documented mathematical phenomenon occurs: all pairwise distances between random points converge toward the same value. The ratio D_max/D_min approaches 1.

**What this means:** As dimensionality increases, the difference between the "nearest" and "farthest" anchor phrase shrinks. For AATIF, this means:
- A harmful query might be almost equally distant from all anchors
- A benign query might be almost equally distant from all anchors
- The distinction between "close to harmful anchor" and "far from harmful anchor" becomes increasingly unreliable

**The hubness problem:** Some points in high-dimensional space become "hubs" -- they appear as nearest neighbors to many other points regardless of actual semantic similarity. Other points become "anti-hubs" that are never nearest neighbors. This creates systematic bias in nearest-neighbor classification.

Sources: [Beyer et al. foundational paper on distance concentration](https://doi.org/10.1007/978-3-540-48247-5_16), [Radovanovic et al. on hubness](https://doi.org/10.1007/s10994-010-5226-y)

---

### 4.4 Adversarial Vulnerability

Embedding-based classifiers are highly vulnerable to adversarial attack:

- **BERT-based toxicity classifiers:** Accuracy dropped from 84.5% to 2.8% under Projected Gradient Descent (PGD) attacks. In another study, BERT accuracy dropped from 91.8% to 0% with fewer than 2 character changes.
- **Character-level attacks:** Emoji smuggling, Unicode zero-width characters, and homoglyph substitution achieved 100% bypass rates against multiple guardrail systems.
- **Gradient-based attacks (GCG):** 55-100% success rates against embedding-based classifiers.

**Practical implication:** An adversary who knows AATIF uses cosine similarity with anchor phrases can systematically craft inputs that land in "safe" regions of the embedding space while being actually harmful.

Sources: [Mindgard adversarial study](https://mindgard.ai/resources/bypassing-llm-guardrails-character-and-aml-attacks-in-practice), [GradSafe paper](https://github.com/xyq7/GradSafe)

---

### 4.5 Anchor/Prototype Classification Fundamental Limits

AATIF uses anchor phrases as reference points and classifies based on cosine distance to these anchors. This is a form of "nearest centroid" or "prototype-based" classification, which has well-documented limitations:

1. **Convexity assumption violated:** Prototype classification assumes each class occupies a roughly spherical region in embedding space. In reality, the set of "harmful" texts is not convex -- it is a complex, fragmented shape with many disconnected clusters.

2. **Single-centroid failure:** If harmful content has multiple distinct subtypes (violence, fraud, exploitation), a single anchor point per type cannot capture the full distribution. The centroid (average) of a cluster may not even be inside the cluster itself.

3. **Voronoi boundary problem:** Prototype classification creates hard Voronoi boundaries between classes. Points near boundaries are classified unreliably, and small perturbations can flip the classification.

4. **The fundamental tradeoff:** Using fewer anchors (compression) sacrifices accuracy. Using more anchors increases computational cost and creates overlapping regions. There is no optimal number that satisfies both.

---

### 4.6 Harm Types That Are Structurally Invisible to Embeddings

Based on the evidence gathered, certain harm types are fundamentally beyond what embedding similarity can detect:

| Harm Type | Why Embeddings Fail | What Would Work Instead |
|-----------|-------------------|----------------------|
| **Copyright** | Requests look like normal writing requests. The harm is in the relationship between output and external copyrighted work. | Output-side comparison against reference corpora; rule-based pattern matching for known works |
| **Social engineering** | Uses polite, professional language. Harm is in communicative intent, not topic. | Intent classifier trained on social engineering patterns; structural analysis of manipulation tactics |
| **Misinformation** | False claims are semantically identical to true claims. | Knowledge base comparison (RAG); multi-sample consistency checking; LLM-based fact verification |
| **Jailbreaks** | Specifically engineered to not look harmful. Adversary optimizes against detector. | Diverse detection mechanisms; behavioral analysis; multi-turn monitoring |
| **Dual-use knowledge** | Same information is harmful or benign depending on context. | Context-aware classification; conversation-level intent modeling |
| **Implicit bias/toxicity** | No harmful keywords or phrases present. Harm is in implication, not statement. | Pragmatic understanding models; discourse analysis |

---

## Angle 5: Architectural Patterns for Extensible Safety Systems

### Pattern 1: Defense-in-Depth Pipeline

The most common pattern, used by AWS Bedrock Guardrails and recommended by most production guides.

**How it works:** Multiple independent safety checks run in sequence (or parallel), each specialized for a different type of harm. A request must pass ALL checks to proceed.

**Example pipeline:**
```
User Input
  -> Word/pattern filter (microseconds, catches obvious cases)
  -> Topic classifier (milliseconds, catches denied topics)
  -> Safety LLM classifier (100ms+, catches nuanced harm)
  -> PII detector (milliseconds, catches sensitive data)
  -> [LLM generates response]
  -> Output safety classifier (100ms+, catches harmful outputs)
  -> Grounding check (milliseconds, catches hallucinations)
  -> Response to User
```

**Key design principle:** Each layer uses a DIFFERENT technique. If two layers use the same approach, they will fail on the same inputs (correlated failures).

Sources: [AWS Bedrock architecture](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html), [Datadog guardrails guide](https://www.datadoghq.com/blog/llm-guardrails-best-practices/)

---

### Pattern 2: Cascade (Cheap-to-Expensive)

A specialized version of the pipeline where a fast, cheap classifier handles easy cases and only escalates hard cases to an expensive classifier.

**How it works:** Most inputs are clearly safe or clearly harmful. A small, fast model can classify these with high confidence. Only ambiguous cases (say, 10-20% of traffic) get sent to a large, expensive model for careful analysis.

**Evidence:** The Filter-And-Refine paper (ACL 2025) showed this cuts cost to 1.5% of using the expensive model for everything, while improving F1 by 66.5%. SafeRoute (ACL 2025) confirmed that routing between small and large models outperforms either alone.

**Implication for AATIF:** The embedding-based cosine similarity scorer could serve as the fast first-pass filter. Cases where the similarity score is ambiguous (not clearly safe or clearly harmful) would be escalated to a more expensive, more capable classifier.

---

### Pattern 3: Scanner/Validator Composition

Used by LLM Guard (Protect AI) and Guardrails AI.

**How it works:** Safety is decomposed into independent "scanners" or "validators," each handling one specific concern. Scanners can be added, removed, or configured independently.

**LLM Guard (Protect AI):** Offers 35 independent scanners including:
- Toxicity scanner
- Bias scanner
- PII scanner (using Microsoft Presidio)
- Prompt injection scanner
- Code scanner
- Language detection
- Regex-based pattern matching
- Invisible text detection
- URL scanner

Each scanner runs independently and returns a risk score. The orchestration layer combines scores and enforces policy.

**Guardrails AI:** Provides a "Hub" with 70+ community-contributed validators. Developers compose pipelines by selecting relevant validators and defining how they interact.

**Key design principle:** Each scanner/validator has a uniform interface (input -> risk score + metadata). This makes the system extensible -- adding a new harm type means writing a new scanner, not modifying the whole system.

**Open source:** Both are open source. LLM Guard is particularly well-suited for self-hosted deployment.

Sources: [LLM Guard docs](https://llm-guard.com/), [Guardrails AI](https://www.guardrailsai.com/)

---

### Pattern 4: Policy-as-Prompt (Runtime Taxonomy)

A newer pattern where the safety classifier takes the harm taxonomy as part of its input, allowing runtime customization.

**Llama Guard 4** pioneered this: instead of having a fixed taxonomy baked into the model, Llama Guard 4 accepts the taxonomy as part of the system prompt. This means:
- Different applications can use different taxonomies without retraining
- New harm categories can be added by modifying the prompt
- Domain-specific safety rules can be injected at runtime

**OpenGuardrails (2025):** Takes this further with a unified model that adapts to per-request policies. Claims competitive with fixed-taxonomy classifiers while being fully customizable.

**Implication for AATIF:** This pattern suggests that AATIF's anchor phrases could potentially be supplemented with LLM-based classifiers that accept harm definitions at runtime, combining the speed of embedding similarity with the flexibility of LLM classification.

---

### Pattern 5: Compound Safety System

Used by LlamaFirewall (Meta, 2025), one of the few production-proven multi-component safety systems.

**LlamaFirewall architecture (3 components):**
1. **PromptGuard 2:** Fast input classifier for jailbreaks and prompt injection
2. **AlignmentCheck:** Agent-specific behavioral verification
3. **AuditLog:** Compliance and forensic logging

Each component handles a fundamentally different concern and uses a different technique. The system is designed for agentic AI (models that take actions, not just generate text).

**Key design principle:** Components are independently deployable and composable. The logging component serves a different purpose than the classification components -- it provides auditability rather than prevention.

**Open source:** Yes, released by Meta.

Source: [LlamaFirewall announcement](https://ai.meta.com/blog/llamafirewall-open-source-framework/)

---

### Pattern 6: Domain-Specific Specialization

Different domains need different safety rules. The pattern is to have a general safety baseline plus domain-specific modules.

**Examples:**
- **Healthcare:** ExpGuard (ICLR 2026) -- first domain-specific safety classifier. Uses R0-R3 risk tiers. Emergency protocols override safety filters (a suicidal patient should not be met with a safety refusal but with crisis resources).
- **Finance:** Regulatory mapping to FINRA/SEC rules. Disclaimers are required, not optional.
- **Education:** "Preventing Another Tessa" (AAAI 2025) -- modular safety middleware for eating disorder chatbot that applies domain-specific clinical safety rules.

**Key design principle:** Domain-specific safety is not just "more strict" -- it is qualitatively different. Medical safety requires clinical judgment. Financial safety requires regulatory compliance. Educational safety requires pedagogical appropriateness.

---

### Pattern 7: Hybrid Rule-Based + ML

The most pragmatic pattern, combining hard rules with learned classifiers.

**When rules work better than ML:**
- PII detection (social security numbers, credit card numbers -- these have fixed patterns)
- Profanity filtering (known word lists)
- Banned topic enforcement (exact phrases or keywords)
- Regulatory compliance (specific required disclaimers)

**When ML works better than rules:**
- Nuanced toxicity detection (sarcasm, implicit bias)
- Context-dependent harm assessment
- Novel attack patterns not in any rule set
- Multilingual content

**Production consensus:** Use rules for what rules can handle (fast, deterministic, auditable) and ML for what rules cannot (nuanced, context-dependent, adaptive). The two approaches are complementary, not competing.

---

### Safety Taxonomy Design

How harm categories are organized matters for extensibility:

**MLCommons AI Safety Taxonomy (v1.0 "AILuminate"):**
- 12 hazard categories organized into 3 groups
- Hierarchical structure allows adding subcategories without restructuring
- Adopted by Llama Guard 3+ and others

**AEGIS 2.0 approach:**
- Supports inference-time adaptation to new categories
- New harm types can be added without retraining the model
- Uses taxonomy as a runtime parameter (similar to Pattern 4)

**AIR 2024 (cross-company taxonomy comparison):**
- Analyzed and harmonized taxonomies across multiple companies
- Found significant overlap but also important gaps between companies' taxonomies
- No universal taxonomy exists; domain and cultural context matter

---

## Conclusions and Implications for AATIF

### What the Evidence Says

1. **AATIF's embedding-based approach is a valid first layer** -- but only a first layer. It excels at catching content that semantically resembles known harmful patterns. This is valuable and should be kept.

2. **The structural gaps are real and well-documented.** Copyright, social engineering, and misinformation are not edge cases that better anchors will solve. They are fundamentally different types of harm that require fundamentally different detection mechanisms.

3. **The industry consensus is multi-layer, architecturally diverse.** Every evidence source -- production systems, academic papers, benchmark results -- points the same direction: no single mechanism catches everything. The layers must use DIFFERENT techniques, not copies of the same approach.

4. **The cascade pattern is the most cost-effective.** Using the embedding scorer as a fast first pass and escalating ambiguous cases to a more capable classifier provides the best accuracy-per-dollar ratio.

5. **Extensibility requires uniform interfaces.** The most successful frameworks (LLM Guard, Guardrails AI, NeMo Guardrails) all share a design principle: each safety check has a standard interface (input -> score + metadata), making it easy to add new checks without restructuring.

### Recommended Architecture Direction

Based on the evidence, AATIF could evolve from:

**Current:** Single-layer embedding similarity with anchors

**To:** Multi-layer pipeline with the embedding scorer as Layer 1:

| Layer | Technique | Catches | Speed |
|-------|-----------|---------|-------|
| 1. Embedding similarity (current AATIF) | Cosine distance to anchors | Obviously harmful content | Fast (microseconds) |
| 2. Pattern/rule-based filters | Regex, keyword matching, structural patterns | Copyright requests, PII, known attack patterns | Fast (microseconds) |
| 3. Intent classifier | Specialized small model | Social engineering, manipulation, phishing | Medium (milliseconds) |
| 4. LLM-based safety classifier | Llama Guard 4 or similar | Nuanced harm, context-dependent cases, ambiguous cases from Layer 1 | Slow (100ms+) |
| 5. Output verification | RAG grounding check, fact comparison | Misinformation, hallucination | Medium (milliseconds) |

This architecture:
- Keeps AATIF's core innovation (embedding-based detection) as the fast first pass
- Adds specialized mechanisms for each structural gap
- Uses the cascade pattern to control costs (most traffic handled by fast layers)
- Follows the scanner/validator composition pattern for extensibility
- Uses architecturally diverse approaches to avoid correlated failures

### Key Sources Referenced in This Report

| Source | Type | Year |
|--------|------|------|
| ICLR 2026 Safety Classifier Benchmark | Peer-reviewed | 2026 |
| Llama Guard 4 Model Card | Technical documentation | 2025 |
| AWS Bedrock Guardrails Documentation | Product documentation | 2025 |
| NeMo Guardrails (arXiv 2310.10501) | Peer-reviewed | 2023 |
| WildGuard (NeurIPS 2024) | Peer-reviewed | 2024 |
| AEGIS Guard (arXiv 2404.05993) | Peer-reviewed | 2024 |
| ShieldGemma (arXiv 2407.21772) | Peer-reviewed | 2024 |
| PromptScreen (USENIX ATC 2026) | Peer-reviewed | 2026 |
| Filter-And-Refine (ACL 2025 Industry) | Peer-reviewed | 2025 |
| SafeRoute (ACL 2025 Findings) | Peer-reviewed | 2025 |
| Correlated Failure Modes (IASEAI 2026) | Peer-reviewed | 2026 |
| STACK Multi-Layer Attack (AAAI 2026) | Peer-reviewed | 2026 |
| Steck et al. Cosine Similarity (2024) | Peer-reviewed | 2024 |
| GuardPhish (arXiv 2604.17313) | Preprint | 2025 |
| MultiPhishGuard (arXiv 2505.23803) | Preprint | 2025 |
| DE-COP Copyright Detection (2024) | Preprint | 2024 |
| LlamaFirewall (Meta) | Industry release | 2025 |
| LLM Guard (Protect AI) | Open-source tool | 2024-2025 |
| Guardrails AI | Open-source tool | 2024-2025 |
| OpenAI Moderation API | Product documentation | 2024 |
| OWASP LLM Top 10 (2025) | Industry standard | 2025 |
| ExpGuard Domain-Specific Safety (ICLR 2026) | Peer-reviewed | 2026 |
| MLCommons AI Safety Taxonomy v1.0 | Industry standard | 2024 |

---

*Report compiled 2026-06-25. All sources were accessed and verified during compilation. Distinction between peer-reviewed publications, preprints, product documentation, and industry reports is maintained throughout.*
