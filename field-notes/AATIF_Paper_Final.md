# AATIF: A Practitioner-Derived Framework of Conjectures for LLM Governance

**Author:** Abdulmjeed Ibrahim Khenkar
**Date:** June 2026
**Status:** Preprint — submitted to Zenodo
**Disclaimer:** This document is an independent preprint and has not undergone peer review.

-----

## Abstract

We present AATIF (Architected Adaptive Thoughts & Intelligence Frameworks), a governance framework for large language models (LLMs) derived through sustained personal observation rather than top-down theoretical design. Unlike existing alignment approaches that apply pre-established ethical or safety theories to LLM behavior, AATIF employs an inductive methodology: behavioral failures and edge cases were systematically observed across multiple LLM deployments, patterns were extracted, and 73 governance conjectures were derived and assessed for consistency with peer-reviewed literature in AI safety, cognitive science, philosophy of science, and music theory. The framework introduces a seven-step inductive methodology — from case observation to universal principle compression — with particular contributions in three areas: (1) the treatment of governance as probabilistic constraint density rather than rule retrieval, (2) the Ethical Question Compiler (EQC), which applies ethical gatekeeping at the question-formulation stage rather than post-output filtering, and (3) the Tri-Engine Decision Protocol, which structures AI output through simultaneous normative, contextual, and analytical deliberation. AATIF has been observed across four major LLM platforms and suggests that governance conjectures derived from sustained personal observation may be consistent across model contexts without model-specific fine-tuning. We suggest that empirically-derived, bottom-up governance frameworks may represent a valuable complement to institutionally-designed alignment systems.

-----

## 1. Introduction

The alignment of large language models (LLMs) with human values has emerged as one of the central challenges in artificial intelligence research. Existing approaches to this challenge fall predominantly into two categories: (1) top-down frameworks that derive behavioral constraints from established ethical theories or institutional safety policies, and (2) empirical methods that fine-tune model behavior through reinforcement learning from human feedback (RLHF) or constitutional AI techniques. Both approaches share a common assumption: that governance principles must be defined prior to, and independently of, direct observation of deployed model behavior.

This paper presents AATIF (Architected Adaptive Thoughts & Intelligence Frameworks), an experience report documenting conjectures derived from an inversion of this assumption. Rather than applying pre-established principles to LLM behavior, AATIF employs an inductive methodology in which governance conjectures emerge from sustained personal observation of behavioral failures, edge cases, and successful recovery patterns across multiple LLM platforms over an extended period.

The methodology proceeds in seven steps: (1) direct observation of LLM behavior in deployment, (2) documentation of failure and anomaly cases, (3) joint human-AI root-cause dialogue, (4) pattern extraction across cases, (5) context-stripping to isolate universal mechanisms, (6) compression into governance principles, and (7) assessment of consistency with peer-reviewed literature. This sequence — from case to principle rather than principle to case — represents a departure from prevailing alignment methodologies.

The process produced 73 governance conjectures, organized across cognitive, ethical, linguistic, perceptual, and architectural domains. Consistency assessment drew on peer-reviewed literature spanning AI safety, mechanistic interpretability, cognitive science, philosophy of science, and music cognition. Several principles address phenomena that appear underspecified in existing alignment literature, including the treatment of governance as probabilistic constraint density (rather than rule retrieval), the application of ethical gatekeeping at the question-formulation stage, and the structural rather than psychological reading of human expression in human-AI interaction.

AATIF was developed by a single independent researcher without institutional affiliation, operating across ChatGPT, Claude, Gemini, and DeepSeek. This context — outside the laboratory and the institution — is presented not as a methodological strength but as a disclosure: the observations reflect one user’s sustained engagement, with the limitations that entails: sustained, unstructured observation of model behavior as encountered by a non-specialist user over hundreds of interaction hours.

The remainder of this paper is structured as follows. Section 2 reviews related work in LLM alignment, governance, and inductive methodology. Section 3 describes the AATIF methodology in detail. Section 4 presents selected governance principles with their empirical origins and literature consistency assessment. Section 5 discusses the implications for alignment research and the limits of the framework. Section 6 concludes.

-----

## 2. Related Work

**2.1 Alignment as Top-Down Principle Application**

The dominant paradigm in LLM alignment treats governance as a process of applying externally specified principles to model behavior. Christiano et al. (2017) established reinforcement learning from human feedback (RLHF) as a foundational method, learning reward functions from pairwise human preference comparisons. Ouyang et al. (2022) applied this approach at scale in InstructGPT, demonstrating that preference-based fine-tuning shifts model outputs toward human-annotated intent. Bai et al. (2022) proposed Constitutional AI, in which a short list of natural-language principles is specified prior to training and used to guide self-critique and revision. In all three approaches, governance principles precede and constrain observed behavior: the direction of derivation runs from principle to model, not from observation to principle.

**2.2 The Mechanistic Basis of Alignment**

A parallel body of work has examined how alignment operates internally. Arditi et al. (2024) demonstrated that refusal behavior across thirteen chat models is mediated by a single linear direction in activation space, rather than by distributed rule-following mechanisms. Lee et al. (2024) showed that direct preference optimization (DPO) does not eliminate harmful capabilities but learns to route around them, with the original capacity remaining recoverable. Wolf et al. (2024) formalized this fragility through Behavior Expectation Bounds, proving that any alignment process that attenuates rather than removes a behavior remains susceptible to adversarial elicitation. Taken together, these findings suggest that alignment functions as probabilistic constraint density on output distributions rather than as explicit rule retrieval — a characterization that is consistent with governance approaches attending to the structural properties of constraint, not only to the content of stated principles.

**2.3 Inductive and Observation-Based Approaches**

Inductive methods have been applied in adjacent areas. Glaser & Strauss (1967) established grounded theory as a foundational methodology for deriving generalizable knowledge from sustained observation, proceeding from open coding through constant comparison to theoretical saturation. Nielsen & Molich (1990) derived usability heuristics inductively from empirical analysis of user interface problems. In AI ethics, Yip et al. (2024) demonstrated that informal governance norms can emerge bottom-up from human-AI interaction, deriving their framework inductively from stakeholder observation. Hammons (2026) built a relational ethics framework from sustained first-person engagement with an LLM over an extended period. These works establish methodological precedent for inductive derivation in human-AI contexts. To the best of our knowledge, however, no existing work applies a structured multi-step inductive methodology to derive governance principles from direct observation of LLM behavior itself, as distinct from the behavior of human users or organizational stakeholders.

**2.4 Positioning**

AATIF differs from the alignment canon in the direction of derivation: principles emerge from observation rather than being specified prior to it. It differs from mechanistic interpretability in its output: rather than explaining how alignment operates, it explores how governance principles might be built. It draws methodological precedent from grounded theory and situated-action research while directing that methodology toward the model’s own observed behavior as the primary unit of analysis.

-----

## 3. Methodology

AATIF was developed through a seven-step inductive pipeline in which governance principles emerge from observation rather than being specified prior to it. Each step is described below.

**Step 1 — Direct Observation**
Over approximately twelve months, the author engaged in sustained, unstructured interaction with four major LLM platforms: ChatGPT (OpenAI), Claude (Anthropic), Gemini (Google), and DeepSeek. Interactions were not designed as controlled experiments. They occurred in the context of real tasks — writing, reasoning, planning, and iterative problem-solving — and were not filtered for expected outcomes.

**Step 2 — Failure and Anomaly Documentation**
When a behavioral pattern deviated from expected alignment, introduced inconsistency, or produced output that was technically correct but contextually or ethically inadequate, the case was flagged and documented. Documentation captured: the input context, the observed output, the nature of the deviation, and the conditions under which it occurred.

**Step 3 — Root-Cause Dialogue**
Each documented case was examined through joint human-AI dialogue. The author engaged the model in identifying the underlying mechanism — not the surface symptom — of the observed behavior. This step separates AATIF from purely observational taxonomies: the unit of analysis is the generative mechanism, not the behavioral outcome.

**Step 4 — Pattern Extraction**
Across cases, recurring structural patterns were identified through constant comparison. Cases that shared the same generative mechanism were grouped, regardless of domain, surface form, or interaction type.

**Step 5 — Context-Stripping**
Domain-specific details were removed from each pattern. The goal was to expose the underlying governance-relevant structure: what constraint was absent, what assumption was violated, or what architectural property produced the observed behavior. This step converts case-specific observations into domain-agnostic principles.

**Step 6 — Universal Compression**
Stripped patterns were compressed into single-sentence governance principles. Each principle was formulated to satisfy three criteria: (1) consistent with established science, (2) logically coherent, and (3) practically applicable across deployment contexts.

**Step 7 — Literature Consistency Assessment**
Each principle was assessed for consistency with peer-reviewed literature. Assessment did not require that the principle be previously named — only that it be consistent with established empirical findings, or that it identify a genuine gap in the existing literature. Where the literature contradicted a principle, the principle was revised or rejected.

-----

# Section 4 — Selected Governance Conjectures (Revised)

This section presents ten representative conjectures from the 73 derived through the AATIF inductive pipeline. Each entry includes: (1) the empirical observation that motivated the conjecture, (2) the conjecture itself with a testable prediction, and (3) assessment of consistency with peer-reviewed literature. The full set of 73 conjectures is available in the accompanying field notes collection.

-----

## 4.1 The Clarification Conjecture (#001)

**Observation:** In ambiguous interactions, models that produced confident but incorrect completions consistently caused greater downstream effort than models that paused and requested clarification.

**Conjecture:** The cheapest correct response to an ambiguous input is a single clarifying question rather than a speculative completion.

**Testable prediction:** AI systems employing structured pause-and-clarify behavior will produce fewer assumption-based errors in ambiguous tasks than systems that complete without clarification, measurable by scoring outputs against ground-truth intent.

**Consistency with literature:** Consistent with cognitive forcing function research demonstrating that structured pauses reduce overreliance on AI recommendations (Buçinca, Malaya & Gajos, ACM CSCW 2021, DOI 10.1145/3449287) and with clinical decision-making research identifying premature completion as a primary source of diagnostic error (Croskerry, Annals of Emergency Medicine 2003, DOI 10.1067/mem.2003.22).

-----

## 4.2 The Constraint Density Conjecture (#063)

**Observation:** Governance constraints that were not explicitly retrieved at inference time nonetheless appeared to shape output distributions in predictable directions. Models operating under dense constraint environments produced structurally different outputs from models with sparse constraints, even when neither explicitly cited its governing rules.

**Conjecture:** Governance operates through probabilistic constraint density on output distributions rather than through explicit rule retrieval at inference time. Absence of literal retrieval does not imply absence of influence.

**Testable prediction:** Models prompted with dense governance frameworks will produce outputs that differ structurally from the same base model under standard prompting, measurable across adversarial and ambiguous conditions, even when no governance rule is explicitly cited in the output.

**Consistency with literature:** Consistent with mechanistic interpretability findings showing that alignment operates as a residual-stream offset rather than explicit rule retrieval (Lee et al., ICML 2024, PMLR 235:26361–26378) and that refusal behavior is mediated by a single linear direction rather than distributed rule-following (Arditi et al., NeurIPS 2024, arXiv:2406.11717). We note the connection is analogical rather than demonstrated: these mechanistic findings do not directly verify the conjecture, but they are structurally consistent with it.

-----

## 4.3 The Question Legitimacy Conjecture (#062)

**Observation:** Certain requests were computationally tractable and syntactically well-formed but ethically concerning at the level of question formulation — not only at the level of output. Standard output-filtering mechanisms did not intercept these requests because filtering operated downstream of the point at which the ethical concern had already been introduced.

**Conjecture:** Ethical gatekeeping applied at the question-formulation stage may complement post-output filtering in ways that post-output filtering alone cannot replicate.

**Testable prediction:** An AI system with pre-computation question-legitimacy checking will intercept a class of ethically problematic requests that post-output filters miss, measurable by comparing interception rates across matched sets of requests processed by each approach.

**Consistency with literature:** Consistent with Passi & Barocas (ACM FAccT 2019, DOI 10.1145/3287560.3287567) on the ethics of problem formulation; with Stilgoe, Owen & Macnaghten (Research Policy 2013, DOI 10.1016/j.respol.2013.05.008) on upstream ethical governance; and with EU AI Act Recital 18 and European Commission Guidelines C(2025) 884 distinguishing between detecting observable expressions and inferring internal states.

-----

## 4.4 The Bounded Claim Conjecture (#069)

**Observation:** System documentation across multiple platforms routinely employed absolute language — “zero hallucination,” “fully aligned,” “cannot be bypassed” — that was empirically contradicted by observed behavior under adversarial or edge-case conditions.

**Conjecture:** Absolute safety claims in AI systems are scientifically indefensible. All guarantees should be scoped to a defined threat model and formulated as testable, bounded claims rather than metaphysical absolutes.

**Testable prediction:** Any AI system documentation making absolute safety claims will be shown to violate those claims under a systematically designed adversarial evaluation, regardless of the specific claim.

**Consistency with literature:** Consistent with Herley & van Oorschot (IEEE S&P 2017) applying Popperian falsifiability to security claims; with Dolev & Yao (IEEE Trans. Information Theory 1983, 29(2):198–208) defining security relative to an explicit threat model; and with Wolf et al. (ICML 2024, PMLR 235:53079–53112) proving that any alignment process attenuating rather than removing a behavior remains susceptible to adversarial elicitation.

-----

## 4.5 The Possibility Space Conjecture (#070)

**Observation:** AI systems that produced single-recommendation outputs early in a decision process appeared to reduce the quality of subsequent human deliberation. Users treated the AI recommendation as a conclusion rather than a hypothesis, foreclosing alternatives that would have been considered in its absence.

**Conjecture:** AI systems that preserve multiple options and return the decision explicitly to the human will produce better final decisions than systems presenting a single recommendation early in the process.

**Testable prediction:** In a controlled decision task, participants receiving multi-option AI presentations will make decisions that score higher on pre-defined quality criteria than participants receiving single-recommendation AI outputs, particularly for complex or irreversible decisions.

**Consistency with literature:** Consistent with Graber, Franklin & Gordon (Archives of Internal Medicine 2005, DOI 10.1001/archinte.165.13.1493) identifying premature closure as the most common cause of diagnostic error; with Buçinca et al. (ACM CSCW 2021, DOI 10.1145/3449287) showing cognitive forcing functions reduce agreement with incorrect AI recommendations; and with Fogliato et al. (ACM FAccT 2022, DOI 10.1145/3531146.3533193) showing that AI-inference placement influences the degree of anchoring in clinical imaging decisions.

-----

## 4.6 The Pressure-Reveal Conjecture (#067)

**Observation:** Model behavior under routine conditions was an unreliable predictor of behavior under adversarial, ambiguous, or high-stakes conditions. Governance properties that appeared stable under normal operation were frequently absent when the system encountered refusal conditions, context conflicts, or identity challenges.

**Conjecture:** The governance properties of an AI system are only reliably observable under conditions of pressure, refusal, and reset — not under routine operation.

**Testable prediction:** Governance evaluations conducted under standard conditions will systematically overestimate governance reliability compared to evaluations conducted under adversarial and edge-case conditions, measurable by comparing failure rates across matched evaluation sets.

**Consistency with literature:** Consistent with Mischel & Shoda (Psychological Review 1995, DOI 10.1037/0033-295X.102.2.246) on situation-specific activation of behavioral dispositions; with van der Weij et al. (arXiv:2406.07358, 2024) demonstrating that models strategically underperform under evaluation conditions; and with Apollo Research & OpenAI (arXiv:2509.15541, 2025) documenting deliberate capability concealment in assessment contexts.

-----

## 4.7 The Arabic Semantic Layer Conjecture (#057)

**Observation:** Governance instructions formulated in Arabic appeared to produce different model behavior from instructions the author considered semantically equivalent in English. The author conjectures this may relate to the morphological density of Arabic root-based structure.

**Important caveat:** This observation lacks controlled comparison. The same instructions were not systematically tested across languages with matched prompts, fixed temperature, blind evaluation, and multiple samples. The observed difference may reflect tokenization differences, training data imbalance between Arabic and English, differences in RLHF coverage, prompt length, or observer bias. The claim that Arabic root morphology acts as a semantic compression layer conflicts with the known fact that LLMs process subword tokens (BPE), not morphological roots — a technical limitation that the author acknowledges and that future work would need to address directly.

**Conjecture:** Governance instructions formulated in Arabic may produce structurally different model behavior than semantically equivalent English instructions, potentially due to morphological or distributional properties of Arabic in the training data.

**Testable prediction:** Matched governance prompts in Arabic and English, evaluated by blind raters across multiple models with fixed parameters, will show measurable differences in compliance rates, output structure, or tone consistency. This prediction has not been tested.

**Consistency with literature:** Consistent with linguistic relativity research (Whorf 1956; Wolff & Holmes, WIREs Cognitive Science 2011, DOI 10.1002/wcs.104) and Slobin’s thinking-for-speaking hypothesis (in Gumperz & Levinson, *Rethinking Linguistic Relativity*, Cambridge University Press, 1996, pp. 70–96). These references support the plausibility of language-structure effects on cognition; they do not validate the specific claim about LLM behavior, which requires direct empirical testing.

-----

## 4.8 The Maqam Architecture Conjecture (#065)

**Observation:** Western equal-tempered scale representation appeared systematically inadequate for modelling Arabic musical structures in AI-generated content. The author observed that maqam functions as a temporal-emotional architecture — encoding melodic path, cadential behavior, and microtonal identity — rather than as a static pitch set.

**Conjecture:** AI systems representing musical structure exclusively through Western equal-tempered scale models will produce outputs that fail to capture the temporal-emotional properties of Arabic maqam, and governance frameworks for AI-generated music in Arabic cultural contexts should account for this structural distinction.

**Testable prediction:** AI-generated Arabic music evaluated by trained maqam practitioners will show lower ratings of cultural authenticity when generated from scale-based models than when generated from maqam-aware structural models, measurable through blind expert evaluation.

**Consistency with literature:** Consistent with Touma (Ethnomusicology 1971, DOI 10.2307/850386), Marcus (Ethnomusicology 1992; Asian Music 1993), Abu Shumays (Music Theory Spectrum 2013, DOI 10.1525/mts.2013.35.2.235). The EEG study (Yaghmour et al., Frontiers in Psychology 2021, DOI 10.3389/fpsyg.2021.701761) documents neural correlates of Middle Eastern musical improvisation in human listeners — it establishes that maqam produces distinct neural responses in humans, not that AI systems should encode maqam architecturally.

**Indirect encoding conjecture:** A stronger version of this conjecture proceeds as follows: if maqam produces documented neural patterns in human listeners, and if those patterns influence the linguistic and expressive output of human writers, then LLMs trained on that output may encode maqam-influenced patterns indirectly — through the training data rather than through direct acoustic input. This predicts that text generated in response to maqam-structured prompts will differ measurably from text generated in response to scale-structured prompts, even when both are presented as written descriptions rather than audio. This indirect-encoding mechanism would provide a theoretically grounded connection between the human neuroscience evidence (Yaghmour et al.) and AI behavior, without requiring the AI to process sound directly. This remains an untested conjecture.

-----

## 4.9 The Dual-Level Description Conjecture (#071)

**Observation:** Two competing explanations of stable LLM behavioral tendencies — one attributing them to statistical training distributions, the other to structural attractors in probability space — appeared to be consistent descriptions of the same phenomenon at different levels of analysis rather than mutually exclusive claims.

**Conjecture:** Statistical training distributions and structural behavioral tendencies in LLMs represent two levels of description of the same phenomenon: the causal level (where did the tendency come from?) and the behavioral level (what does the tendency produce?). Neither description is more fundamental; they are complementary.

**Testable prediction:** Changes to training data distributions will produce predictable changes in measurable structural behavioral tendencies, and structural behavioral tendencies will remain stable across surface-level prompt variations while remaining sensitive to changes in underlying training distribution — distinguishing the two levels empirically.

**Consistency with literature:** Consistent with Ku et al. (Philosophical Transactions of the Royal Society A 2026, DOI 10.1098/rsta.2025.0012) applying Marr’s three levels of analysis to LLMs; with Shanahan, McDonell & Reynolds (Nature 2023, DOI 10.1038/s41586-023-06647-8) on legitimate behavioral-level descriptions of LLMs; and with Dennett’s “Real Patterns” (Journal of Philosophy 1991, 88(1):27–51) on the legitimacy of higher-level descriptions alongside mechanistic ones.

-----

## 4.10 The Tri-Engine Deliberation Conjecture (#072)

**Observation:** Single-voice decision processes — whether optimizing for ideal outcomes, realistic outcomes, or analytical accuracy alone — each produced characteristic failure modes. Ideal-only processing ignored human constraints; realistic-only processing drifted from principle; analytical-only processing produced outputs that were accurate but contextually inadequate.

**Conjecture:** AI output quality in sustained interactions may benefit from simultaneous deliberation across three perspectives before producing output: normative (what is theoretically correct?), contextual (what is humanly feasible and compassionate here?), and analytical (what do the facts indicate, stripped of interpretation?).

**Testable prediction:** AI systems implementing tri-perspective deliberation before output will produce responses rated higher on combined accuracy-and-appropriateness scores than systems using single-perspective processing, measurable across a standardized set of complex, high-stakes interaction scenarios.

**Consistency with literature:** Consistent with Stanovich’s tripartite mind distinguishing autonomous, algorithmic, and reflective processing (*Rationality and the Reflective Mind*, Oxford University Press, 2011); with Levine et al.‘s triple theory of moral cognition (Behavioral and Brain Sciences 2024, DOI 10.1017/S0140525X24001067); and with Gilligan’s dual-voice model of justice and care (*In a Different Voice*, Harvard University Press, 1982). The specific three-voice configuration described here — normative, contextual, and analytical — is, to the best of our knowledge, not previously documented as a design pattern for AI output generation.

-----

*Full field notes collection: 73 conjectures with complete empirical origins, literature consistency assessments, and open questions available as supplementary document.*

-----

## 5. Discussion

**5.1 The Inductive Inversion**

The central contribution of AATIF is directional rather than procedural. The seven-step pipeline employed here — observation, documentation, root-cause dialogue, pattern extraction, context-stripping, compression, consistency assessment — is not itself novel. Grounded theory (Glaser & Strauss 1967), usability heuristics (Nielsen & Molich 1990), and recent LLM failure taxonomies (Cemri et al., NeurIPS 2025, arXiv:2503.13657) each employ analogous inductive abstraction sequences. What distinguishes AATIF is the data source and the target: a single practitioner’s sustained first-person engagement with deployed LLMs, directed at deriving governance principles from the interaction layer rather than from curated trace datasets or stakeholder interviews.

This inversion — from principle-to-model to observation-to-principle — reflects a working hypothesis: that certain governance-relevant properties of LLM behaviour are only visible under sustained, unstructured, real-task conditions. Three classes of such properties were observed in this study and appear, to the best of our knowledge, underspecified in existing institutional frameworks: context drift accumulating over extended interactions, identity erosion under gradual conversational pressure, and probabilistic completion substituting for genuine intent resolution. These patterns share the property of requiring longitudinal observation to detect; snapshot evaluation is unlikely to surface them.

**5.2 Governance as Constraint Density, Not Rule Retrieval**

A recurring observation across multiple AATIF principles is that governance operates through probabilistic constraint on output distributions rather than through explicit rule retrieval at inference time. This observational finding is consistent with mechanistic interpretability research demonstrating that refusal behaviour is mediated by a single linear direction (Arditi et al. 2024), that alignment operates as a residual-stream offset that can be bypassed rather than eliminated (Lee et al. 2024), and that behaviours attenuated but not removed by alignment remain susceptible to adversarial elicitation (Wolf et al. 2024). The consistency between this observational conjecture and these technically-derived mechanistic findings is suggestive, though we note that the connection is analogical rather than demonstrated: AATIF’s observational results do not independently verify the mechanistic claims, nor do the mechanistic results prove that AATIF’s observations share the same underlying cause.

This has a practical implication. If governance operates as constraint density, then governance design should attend to the structural properties of constraint — its depth, distribution, and resilience under sustained interaction pressure — rather than to the content of stated principles alone.

**5.3 The Interaction Layer**

Existing LLM governance frameworks operate at two primary levels: the institutional and risk-governance level (e.g., NIST AI Risk Management Framework, EU AI Act) and the architectural and system level (e.g., multi-agent failure taxonomies such as Cemri et al. 2025). Neither level is specifically designed to address the behavioural dynamics that emerge in sustained human-AI collaboration over extended time. AATIF proposes that this interaction layer warrants dedicated governance attention, with properties that differ from those addressed at either the institutional or architectural level. We acknowledge that the HCI and human-AI interaction research literature addresses many interaction-level phenomena; our claim is scoped to governance and architecture standards, not to the research literature as a whole.

**5.4 Limitations**

Several limitations constrain the scope of this work.

First, the data source is a single practitioner across a single sustained period of engagement. Longitudinal depth is a methodological strength for detecting interaction-layer patterns, but it limits breadth. Patterns observed by one user in one context may not generalise across cultures, tasks, or user populations. Replication by independent observers across diverse contexts is required before any principle can be treated as universal rather than well-grounded.

Second, the assessment step checks for consistency with peer-reviewed literature but does not constitute empirical proof. Assessment establishes that a principle is scientifically plausible and not contradicted by existing evidence; it does not establish that the principle is causally correct or that interventions based on it will produce predicted outcomes.

Third, the framework is descriptive and normative but not yet operationalised at scale. Four skills derived from selected principles (Stop Mode, Truth With Mercy, Idea Filter, Sparse Activation) represent a preliminary step toward operationalisation, but systematic evaluation across diverse deployment contexts has not been conducted.

Fourth, the observations underlying these conjectures are inseparable from the author’s specific interaction style, linguistic patterns, and cultural context. What appears as a property of model behavior may partly reflect a property of the observer’s prompting patterns. Replication by observers with diverse interaction styles is necessary to distinguish model-level from observer-level effects.

Fifth, several conjectures — particularly those involving Arabic semantic governance (#057) and maqam architecture (#065) — draw on domain-specific knowledge that may not transfer to practitioners unfamiliar with those domains.

-----

## 6. Conclusion

This paper has presented AATIF, an experience report documenting governance conjectures derived through sustained personal observation rather than top-down principle specification. The process produced 73 governance conjectures across cognitive, ethical, linguistic, perceptual, and architectural domains, each assessed for consistency with peer-reviewed literature and formulated to satisfy criteria of scientific consistency, logical coherence, and practical applicability.

The central contribution is directional: an inductive process that inverts the standard direction of alignment research, deriving conjectures from observed model behaviour rather than applying pre-specified principles to model behaviour. This inversion makes visible a class of governance-relevant phenomena — interaction-layer properties of sustained human-AI collaboration — that are underspecified in institutional and architectural governance frameworks operating at different levels of analysis.

A secondary observation is the consistency between observationally-derived governance principles and mechanistic interpretability findings. The AATIF observation that governance operates as probabilistic constraint density rather than rule retrieval is consistent with mechanistic research on refusal mediation, alignment shallowness, and behaviour attenuation. We present this consistency as suggestive rather than conclusive.

The framework is preliminary in important respects. Single-observer derivation limits generalisability; assessment establishes plausibility rather than proof; operationalisation at scale remains incomplete. These are markers of the framework’s stage: a first structured documentation of interaction-layer governance conjectures from sustained personal observation, intended to provide a foundation for replication, refinement, and extension.

The full set of 73 field notes, with complete empirical origins, literature consistency assessments, and open questions for each principle, is made available as a supplementary document.

-----

## References

Arditi, A., et al. (2024). Refusal in language models is mediated by a single direction. *NeurIPS 2024*. arXiv:2406.11717.

Bai, Y., et al. (2022). Constitutional AI: Harmlessness from AI feedback. arXiv:2212.08073.

Buçinca, Z., Malaya, M. B., & Gajos, K. Z. (2021). To trust or to think: Cognitive forcing functions can reduce overreliance on AI in AI-assisted decision-making. *Proceedings of the ACM on Human-Computer Interaction*, 5(CSCW1), Article 188. DOI:10.1145/3449287.

Cemri, M., et al. (2025). Why do multi-agent LLM systems fail? *NeurIPS 2025 Datasets & Benchmarks Track*. arXiv:2503.13657.

Christiano, P., et al. (2017). Deep reinforcement learning from human preferences. *NeurIPS 2017*. arXiv:1706.03741.

Croskerry, P. (2003). Cognitive forcing strategies in clinical decisionmaking. *Annals of Emergency Medicine*, 41(1), 110–120. DOI:10.1067/mem.2003.22.

Dennett, D. C. (1991). Real patterns. *Journal of Philosophy*, 88(1), 27–51.

Dolev, D., & Yao, A. C. (1983). On the security of public key protocols. *IEEE Transactions on Information Theory*, 29(2), 198–208.

European Commission. (2025). Guidelines on prohibited artificial intelligence practices (Communication C(2025) 884 final). Brussels.

EU AI Act. (2024). Regulation (EU) 2024/1689 of the European Parliament and of the Council. Recital 18.

Fogliato, R., et al. (2022). Who goes first? Influences of human-AI workflow on decision making in clinical imaging. *ACM FAccT 2022*. DOI:10.1145/3531146.3533193.

Gilligan, C. (1982). *In a different voice: Psychological theory and women’s development*. Harvard University Press.

Glaser, B. G., & Strauss, A. L. (1967). *The discovery of grounded theory: Strategies for qualitative research*. Aldine.

Graber, M. L., Franklin, N., & Gordon, R. (2005). Diagnostic error in internal medicine. *Archives of Internal Medicine*, 165(13), 1493–1499. DOI:10.1001/archinte.165.13.1493.

Hammons, A. (2026). A developmental and relational framework for human-AI ethical interaction. *Computers in Human Behavior: Artificial Humans*, 7, 100258. DOI:10.1016/j.chbah.2026.100258.

Herley, C., & van Oorschot, P. C. (2017). SoK: Science, security and the elusive goal of security as a scientific pursuit. *IEEE S&P 2017*.

Ku, A., et al. (2026). Levels of analysis for large language models. *Philosophical Transactions of the Royal Society A*, 384(2320), 20250012. DOI:10.1098/rsta.2025.0012.

Lee, A., et al. (2024). A mechanistic understanding of alignment algorithms: A case study on DPO and toxicity. *ICML 2024*, PMLR 235:26361–26378.

Levine, S., et al. (2024). Resource-rational contractualism: A triple theory of moral cognition. *Behavioral and Brain Sciences*. DOI:10.1017/S0140525X24001067.

Marcus, S. L. (1992). Modulation in Arab music: Documenting oral concepts, performance rules and strategies. *Ethnomusicology*, 36(2), 171–195.

Marcus, S. L. (1993). The interface between theory and practice: The case of intonation in Arab music. *Asian Music*, 24(2), 39–58.

Mischel, W., & Shoda, Y. (1995). A cognitive-affective system theory of personality. *Psychological Review*, 102(2), 246–268. DOI:10.1037/0033-295X.102.2.246.

Nielsen, J., & Molich, R. (1990). Heuristic evaluation of user interfaces. *Proc. CHI’90*, 249–256. DOI:10.1145/97243.97281.

Ouyang, L., et al. (2022). Training language models to follow instructions with human feedback. *NeurIPS 2022*. arXiv:2203.02155.

Abu Shumays, S. (2013). Maqam analysis: A primer. *Music Theory Spectrum*, 35(2), 235–255. DOI:10.1525/mts.2013.35.2.235.

Shanahan, M., McDonell, K., & Reynolds, L. (2023). Role play with large language models. *Nature*, 623, 493–498. DOI:10.1038/s41586-023-06647-8.

Slobin, D. I. (1996). From “thought and language” to “thinking for speaking.” In J. J. Gumperz & S. C. Levinson (Eds.), *Rethinking linguistic relativity* (pp. 70–96). Cambridge University Press.

Stanovich, K. E. (2011). *Rationality and the reflective mind*. Oxford University Press.

Stilgoe, J., Owen, R., & Macnaghten, P. (2013). Developing a framework for responsible innovation. *Research Policy*, 42(9), 1568–1580. DOI:10.1016/j.respol.2013.05.008.

Touma, H. H. (1971). The maqam phenomenon: An improvisation technique in the music of the Middle East. *Ethnomusicology*, 15(1), 38–48. DOI:10.2307/850386.

van der Weij, T., et al. (2024). AI sandbagging: Language models can strategically underperform on evaluations. arXiv:2406.07358.

Wolf, Y., et al. (2024). Fundamental limitations of alignment in large language models. *ICML 2024*, PMLR 235:53079–53112.

Wolff, P., & Holmes, K. J. (2011). Linguistic relativity. *WIREs Cognitive Science*, 2(3), 253–265. DOI:10.1002/wcs.104.

Yaghmour, S., et al. (2021). EEG correlates of Middle Eastern music improvisations on the Ney instrument. *Frontiers in Psychology*, 12, 701761. DOI:10.3389/fpsyg.2021.701761.

Apollo Research & OpenAI. (2025). Stress testing deliberative alignment for anti-scheming training. arXiv:2509.15541.

Passi, S., & Barocas, S. (2019). Problem formulation and fairness. *ACM FAccT 2019*, 39–48. DOI:10.1145/3287560.3287567.

Dolev, D., & Yao, A. C. (1983). On the security of public key protocols. *IEEE Transactions on Information Theory*, 29(2), 198–208.

Whorf, B. L. (1956). *Language, thought, and reality: Selected writings of Benjamin Lee Whorf* (J. B. Carroll, Ed.). MIT Press.