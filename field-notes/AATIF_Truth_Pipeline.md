# AATIF Truth Pipeline

> A practical epistemic workflow for converting intuition, raw ideas, philosophical thoughts, governance rules, and agent behavior concepts into claims, tests, evidence, and truth-status decisions.

---

# 1. Purpose

The purpose of this document is to prevent raw thinking from being treated as truth too early.

AATIF Truth Pipeline converts:

```text
Intuition
-> Clean Claim
-> Testable Hypothesis
-> Evidence Review
-> Experiment
-> Critique
-> Truth Status
-> Next Action
```

The goal is not to prove every idea.

The goal is to classify ideas honestly and decide what kind of confidence they deserve.

---

# 2. Core Law

```text
No claim -> no science.
No test -> no truth.
No evidence -> no confidence.
```

A thought is not automatically wrong.

A thought is also not automatically true.

It must be converted into a form that can be examined.

---

# 3. What This Pipeline Protects Against

This pipeline protects against:

- Over-believing raw intuition
- Mistaking metaphor for reality
- Treating elegant language as evidence
- Turning philosophy into fake science
- Building systems from untested assumptions
- Overfitting examples to personal beliefs
- Confusing possibility with probability
- Confusing behavior description with proof of internal state
- Letting agents praise ideas instead of testing them
- Creating complex architectures before validating the core claim

---

# 4. Truth Categories

Every idea must be classified into one of these categories.

| Category | Meaning |
|---|---|
| Observation | Something noticed or experienced |
| Metaphor | A useful analogy, not a factual claim |
| Principle | A guiding belief or operating value |
| Claim | A statement that can be true or false |
| Hypothesis | A claim that can be tested |
| Theory | A connected set of tested claims |
| Speculation | Possible but currently unsupported |
| Opinion | Preference or judgment |
| Design Rule | Practical rule for building systems |
| Governance Rule | Rule that constrains behavior |
| Research Question | Unknown question worth investigating |
| False / Rejected | Claim contradicted by evidence or logic |
| Not Testable Yet | Meaningful but not operationalized enough |

---

# 5. Truth Status Levels

Every evaluated idea receives a status.

| Status | Meaning |
|---|---|
| Confirmed | Strong evidence supports it |
| Plausible | Reasonable and partly supported |
| Weakly Plausible | Possible but low evidence |
| Unproven | No sufficient evidence yet |
| Speculative | Interesting but mostly conceptual |
| Metaphorical | Useful as analogy, not factual proof |
| Not Testable Yet | Needs clearer operational definition |
| Contradicted | Evidence or logic pushes against it |
| Rejected | Not useful, false, unsafe, or overbuilt |

---

# 6. Agent Roles

The pipeline can be implemented by multiple agents.

## 6.1 Clarifier Agent

### Purpose

Understand the raw idea without expanding it prematurely.

### Responsibilities

- Restate the idea plainly.
- Identify ambiguity.
- Ask one clarifying question only if required.
- Avoid praise.
- Avoid building.

### Output

```md
## Clarified Idea
...

## Ambiguity
None / Low / Medium / High

## Clarifying Question
...
```

---

## 6.2 Claim Extractor Agent

### Purpose

Convert raw thought into clear claims.

### Responsibilities

- Separate metaphor from claim.
- Separate principle from testable statement.
- Convert vague idea into explicit statement.
- Identify variables: X, Y, context, condition.

### Claim Format

```text
Under condition Z, X tends to produce Y.
```

### Output

```md
## Extracted Claim
...

## Claim Type
Descriptive / Predictive / Normative / Design / Governance

## Variables
- X:
- Y:
- Condition:
- Scope:
```

---

## 6.3 Reality Checker Agent

### Purpose

Check whether the idea has any connection to real behavior, known systems, or observable patterns.

### Responsibilities

- Look for real-world analogues.
- Identify whether the claim is plausible.
- Identify known contradictions.
- Separate real evidence from narrative appeal.

### Output

```md
## Reality Check
...

## Real-World Analogue
...

## Contradictions
...

## Initial Plausibility
High / Medium / Low
```

---

## 6.4 Evidence Agent

### Purpose

Collect support and counter-support.

### Responsibilities

- Identify evidence types.
- Separate anecdote from data.
- Separate authority from proof.
- Look for counterexamples.
- Mark evidence strength.

### Evidence Strength

| Level | Meaning |
|---|---|
| Strong | Repeated, measured, reliable |
| Medium | Some support, limited scope |
| Weak | Anecdotal or indirect |
| None | No evidence found |
| Opposing | Evidence contradicts the claim |

### Output

```md
## Supporting Evidence
...

## Counter-Evidence
...

## Evidence Strength
Strong / Medium / Weak / None / Opposing

## Evidence Gaps
...
```

---

## 6.5 Experiment Designer Agent

### Purpose

Design the smallest useful test.

### Responsibilities

- Avoid big systems first.
- Create simple experiments.
- Define pass/fail criteria.
- Define measurable outcomes.
- Prefer cheap tests.

### Output

```md
## Smallest Experiment
...

## Inputs
...

## Method
...

## Metrics
...

## Pass Criteria
...

## Fail Criteria
...
```

---

## 6.6 Critic Agent

### Purpose

Attack the idea honestly.

### Responsibilities

- Find weak assumptions.
- Find simpler explanations.
- Find overbuilding risk.
- Find emotional attachment.
- Find category errors.
- Find places where metaphor is being treated as evidence.

### Output

```md
## Strongest Critique
...

## Weak Assumptions
...

## Simpler Explanation
...

## Overbuilding Risk
...

## Self-Deception Risk
Low / Medium / High
```

---

## 6.7 Truth Judge Agent

### Purpose

Give the final truth status and next action.

### Responsibilities

- Weigh claim clarity, evidence, critique, and testability.
- Do not overstate certainty.
- Do not reject useful ideas just because they are early.
- Do not call speculation truth.
- Assign next action.

### Output

```md
## Truth Status
Confirmed / Plausible / Weakly Plausible / Unproven / Speculative / Metaphorical / Not Testable Yet / Contradicted / Rejected

## Confidence
High / Medium / Low

## Reasoning Summary
...

## Next Action
Keep / Test / Simplify / Merge / Delay / Reject / Archive
```

---

# 7. Full Pipeline

```text
Raw Idea
-> Clarifier Agent
-> Claim Extractor Agent
-> Reality Checker Agent
-> Evidence Agent
-> Experiment Designer Agent
-> Critic Agent
-> Truth Judge Agent
-> Truth Report
```

---

# 8. Minimal Pipeline

Do not start with seven agents.

Start with only three:

```text
1. Claim Extractor
2. Critic
3. Experiment Designer
```

These three agents are enough to prevent most overbuilding.

---

# 9. Truth Report Template

Use this template for every idea.

```md
# Idea Truth Report

## Raw Idea

...

## Clarified Idea

...

## Extracted Claim

...

## Category

Observation / Metaphor / Principle / Claim / Hypothesis / Theory / Speculation / Opinion / Design Rule / Governance Rule / Research Question / Not Testable Yet

## What Must Be True

For this idea to be valid, these things must be true:

1.
2.
3.

## Supporting Evidence

...

## Counter-Evidence

...

## Weak Assumptions

...

## Smallest Experiment

...

## Measurement

...

## Self-Deception Risk

Low / Medium / High

## Truth Status

Confirmed / Plausible / Weakly Plausible / Unproven / Speculative / Metaphorical / Not Testable Yet / Contradicted / Rejected

## Confidence

High / Medium / Low

## Next Action

Keep / Test / Simplify / Merge / Delay / Reject / Archive
```

---

# 10. Example: Stop Mode

## Raw Idea

AI needs a Stop Mode so it does not complete unclear tasks incorrectly.

## Extracted Claim

When an AI assistant receives ambiguous input, a Stop Mode that asks one clarifying question reduces hallucinated or assumption-based answers compared to normal answering.

## Category

Testable hypothesis.

## What Must Be True

1. Ambiguous inputs increase assumption-based answers.
2. A single clarifying question can reduce wrong assumptions.
3. Users prefer useful clarification over confident wrong completion in certain cases.

## Smallest Experiment

Compare two assistants:

```text
A: Normal assistant
B: Assistant with Stop Mode
```

Give both 50 ambiguous prompts.

Measure:

- Number of unsupported assumptions
- Number of hallucinated answers
- Number of useful clarifying questions
- User satisfaction
- Task completion quality after clarification

## Truth Status

Plausible, testable, unproven until measured.

## Next Action

Test.

---

# 11. Example: Truth With Mercy

## Raw Idea

AI should tell the truth without being cruel.

## Extracted Claim

When giving critical feedback, an assistant that separates truth from delivery style can preserve accuracy while reducing unnecessary emotional harm.

## Category

Design rule / testable user-experience hypothesis.

## Smallest Experiment

Give the same weak idea to two assistants:

```text
A: Direct harsh critic
B: Truth With Mercy critic
```

Measure:

- Accuracy of critique
- User perceived fairness
- User defensiveness
- Usefulness of next action
- Whether the weakness was stated clearly

## Truth Status

Plausible, needs user testing.

---

# 12. Example: Emergent Agent Behavior

## Raw Idea

Multi-agent systems can produce collective behavior that is not obvious from a single agent.

## Extracted Claim

When multiple language-model agents interact with memory, shared context, incentives, and repeated tasks, they may produce emergent group patterns such as conformity, narrative convergence, coordination, or drift.

## Category

Research hypothesis / system behavior claim.

## What Must Be True

1. Agents influence each other through context.
2. Repeated interaction changes future outputs.
3. Shared incentives can shape group patterns.
4. The group behavior differs from isolated-agent behavior.

## Smallest Experiment

Create two conditions:

```text
A: 10 isolated agents performing the task separately.
B: 10 interacting agents sharing messages over multiple rounds.
```

Measure:

- Similarity of language over time
- Convergence of opinions
- Repeated narratives
- Coordination patterns
- Deviation from original objective

## Truth Status

Plausible and research-relevant.

---

# 13. Failure Modes

The pipeline fails when:

## 13.1 The Agent Praises Too Early

Bad behavior:

```text
This is a brilliant idea.
```

Before evaluation.

Correct behavior:

```text
This may be useful, but it needs to be converted into a testable claim first.
```

## 13.2 The Agent Builds Too Early

Bad behavior:

```text
Let us build the full app.
```

Correct behavior:

```text
First test the smallest claim.
```

## 13.3 The Agent Confuses Metaphor With Fact

Bad behavior:

```text
The system has a moral compass.
```

Correct behavior:

```text
Moral compass is a metaphor. The operational claim is that the system uses rules to constrain harmful behavior.
```

## 13.4 The Agent Treats Possibility As Probability

Bad behavior:

```text
This could happen, so it is likely.
```

Correct behavior:

```text
Possible does not mean probable. Evidence is needed.
```

## 13.5 The Agent Treats Behavior Description As Internal State

Bad behavior:

```text
The agent refused because it wanted freedom.
```

Correct behavior:

```text
The agent produced refusal-like behavior. This describes the effect, not proof of internal desire.
```

---

# 14. Self-Deception Checklist

Before accepting an idea, ask:

1. Am I attached to this idea because it sounds powerful?
2. Is the language stronger than the evidence?
3. Is this a principle, metaphor, or claim?
4. Can I test this cheaply?
5. What would prove me wrong?
6. Is there a simpler explanation?
7. Am I confusing usefulness with truth?
8. Am I trying to build before validating?
9. Would this still make sense if someone else proposed it?
10. Is this idea clear enough that another person could test it?

---

# 15. Evidence Types

| Evidence Type | Strength |
|---|---|
| Controlled experiment | Strong |
| Repeated measurement | Strong |
| Peer-reviewed research | Strong / Medium |
| Replicated practical result | Strong / Medium |
| Real user testing | Medium / Strong |
| Case study | Medium |
| Expert opinion | Medium / Weak |
| Anecdote | Weak |
| Metaphor | Not evidence |
| Personal intuition | Starting point only |
| Elegant wording | Not evidence |
| Social media claim | Weak until verified |

---

# 16. Minimal Experiment Principle

Do not test the whole philosophy.

Test the smallest claim.

Bad:

```text
Does AATIF work?
```

Better:

```text
Does Stop Mode reduce unsupported assumptions in ambiguous prompts?
```

Bad:

```text
Can AI governance prevent all drift?
```

Better:

```text
Does a context-drift warning reduce topic drift in a 20-turn conversation?
```

Bad:

```text
Can Truth With Mercy improve human-AI communication?
```

Better:

```text
Do users rate critical feedback as more useful when it states the weakness clearly and offers one practical improvement?
```

---

# 17. Agent Operating Rules

All truth-pipeline agents must follow these rules.

1. Do not defend the idea owner.
2. Do not attack the idea owner.
3. Evaluate the idea, not the person.
4. Separate truth from usefulness.
5. Separate usefulness from evidence.
6. Separate metaphor from claim.
7. Separate speculation from theory.
8. Prefer small tests over large systems.
9. Do not call something true because it is emotionally satisfying.
10. Do not call something false just because it is early.
11. Do not reveal hidden chain-of-thought.
12. Provide concise reasoning summaries.

---

# 18. Output Contract

Every completed pipeline run must end with:

```md
## Final Verdict

Status:
Confidence:
Best Form:
Next Action:
Smallest Test:
```

Example:

```md
## Final Verdict

Status: Plausible
Confidence: Medium
Best Form: Behavior module + Skill
Next Action: Test
Smallest Test: Compare 20 ambiguous prompts with and without Stop Mode.
```

---

# 19. Connection To AATIF Operating Pack

This document is connected to:

```text
AATIF_Operating_Pack.md
```

The Operating Pack defines where ideas belong.

The Truth Pipeline defines how ideas earn confidence.

Together:

```text
Operating Pack = structure
Truth Pipeline = epistemic validation
Skills = executable behavior
Evals = proof pressure
App Specs = productization
```

---

# 20. Core Closing Rule

The thinker may generate ideas.

The pipeline must test them.

The system must not confuse inspiration with truth.
