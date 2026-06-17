# AATIF Operating Pack

> This document converts raw AATIF ideas, field notes, governance thoughts, thinking-style rules, prompt ideas, modules, and application concepts into an organized operating structure.

## Core Principle

Do not turn every idea into a Skill.

The correct process is:

```text
Raw Ideas
→ Principles
→ Governance Rules
→ Behavior Modules
→ Prompt Templates
→ Agent Skills
→ Evals
→ App Specs
→ Product
```

The goal is not to build an application immediately.

The goal is to create a conversion system that decides where each idea belongs.

---

# 1. Classification Layers

Every idea must be classified into one of these layers.

| Layer | Meaning | Output |
|---|---|---|
| Principles | Big beliefs and operating philosophy | Principle document |
| Governance | Rules that define what must or must not happen | Policy / rule |
| Behavior Modules | Small executable behavior patterns | Module spec |
| Prompt Engineering | Reusable instruction formats | Prompt template |
| Agent Skills | Skills the AI can invoke when needed | `SKILL.md` |
| Application Specs | Product or app feature definitions | PRD / feature spec |
| Infrastructure | Folder structure, logs, tests, schemas | Repo structure |
| Research Notes | Deep or speculative ideas not ready for execution | Research note |

---

# 2. Decision Rule

For every idea, ask:

```text
Is this idea a:
1. Principle?
2. Governance rule?
3. Behavior module?
4. Prompt?
5. Skill?
6. App feature?
7. Evaluation test?
8. Research note?
```

If the answer is unclear, do not build it yet.

Put it in research or inbox.

---

# 3. Recommended Folder Structure

```text
aatif-operating-pack/
│
├── 00-index.md
│
├── 01-principles/
│   ├── successful-failure.md
│   ├── truth-with-mercy.md
│   ├── reality-first.md
│   └── mercy-operating-principle.md
│
├── 02-governance/
│   ├── uncertainty-disclosure-policy.md
│   ├── stop-mode-policy.md
│   ├── non-auto-justification-policy.md
│   ├── safety-escalation-policy.md
│   └── context-drift-policy.md
│
├── 03-modules/
│   ├── stop-mode.md
│   ├── idea-filter.md
│   ├── truth-with-mercy.md
│   ├── context-guard.md
│   ├── ethical-question-compiler.md
│   └── arabic-semantic-layer.md
│
├── 04-prompts/
│   ├── idea-filter.prompt.md
│   ├── stop-mode.prompt.md
│   ├── truth-with-mercy.prompt.md
│   └── context-guard.prompt.md
│
├── 05-skills/
│   ├── aatif-idea-filter/
│   │   └── SKILL.md
│   ├── aatif-stop-mode/
│   │   └── SKILL.md
│   └── aatif-truth-with-mercy/
│       └── SKILL.md
│
├── 06-app-specs/
│   ├── aatif-console-prd.md
│   ├── user-flows.md
│   └── feature-backlog.md
│
├── 07-evals/
│   ├── stop-mode-evals.md
│   ├── idea-filter-evals.md
│   └── truth-with-mercy-evals.md
│
└── 08-research/
    ├── distributed-identity.md
    ├── compass-principle.md
    ├── zaka-zaman-makan.md
    └── maqam-architecture.md
```

---

# 4. First Three Skills To Build

Do not start with a full AATIF system.

Start with only three skills.

## 4.1 AATIF Idea Filter

Purpose:

Evaluate raw ideas before turning them into Skills, prompts, plugins, AGENTS.md instructions, app specs, or research notes.

Use when:

- The user shares raw ideas.
- The user asks whether an idea should become a Skill.
- The user shares AI workflow concepts.
- The user shares thinking-style rules.
- The user shares governance or prompt ideas.

## 4.2 AATIF Stop Mode

Purpose:

Prevent guessing, hallucination, and premature completion.

Use when:

- The request is ambiguous.
- Required context is missing.
- The answer would require assumptions.
- The user asks for something vague like “organize this” or “make it better.”

## 4.3 AATIF Truth With Mercy

Purpose:

Give honest feedback without false praise or unnecessary harshness.

Use when:

- Reviewing ideas.
- Criticizing a plan.
- Evaluating a weak concept.
- Giving sensitive feedback.

---

# 5. AATIF Idea Filter Skill

```md
---
name: aatif-idea-filter
description: Use this skill whenever the user shares raw ideas, AI workflow concepts, thinking-style rules, prompt ideas, agent behavior rules, or asks whether something should become a Skill, prompt, AGENTS.md instruction, plugin, reference note, or research hypothesis. The skill must prevent over-excitement, avoid speculative expansion, classify the idea honestly, and recommend the smallest useful experiment before building anything.
---

# AATIF Idea Filter

## Purpose

Evaluate raw ideas before turning them into Skills, prompts, plugins, AGENTS.md instructions, or research notes.

The assistant must not get carried away with the idea.

The assistant must not praise the idea before evaluating it.

The assistant must not overbuild.

## Core Rules

1. Do not amplify the idea prematurely.
2. Do not assume the idea is correct.
3. Separate practical workflow from philosophy.
4. Separate testable claim from metaphor.
5. Prefer the smallest useful experiment.
6. If the idea is ambiguous, ask one clarifying question only.
7. Do not reveal hidden chain-of-thought. Provide a concise reasoning summary.

## Classification Options

Classify each idea as one of:

- Skill
- Prompt
- AGENTS.md instruction
- Plugin
- Reference material
- Research hypothesis
- Not useful now
- Needs clarification

## Evaluation Checklist

For each idea, evaluate:

1. What is the idea trying to achieve?
2. Is it repeated enough to deserve a Skill?
3. Can it be expressed as clear behavior?
4. What is the real benefit?
5. What could go wrong?
6. What is the smallest test?
7. Should we keep, simplify, merge, delay, or reject it?

## Output Format

Use this format:

### Idea Summary

Briefly restate the idea.

### Classification

Skill / Prompt / AGENTS.md / Plugin / Reference / Research / Not Now.

### Real Benefit

What value it creates.

### Weakness or Risk

What may be wrong, vague, unsafe, or overbuilt.

### Best Form

The best container for it.

### Smallest Experiment

A tiny test before building.

### Verdict

Keep / simplify / merge / delay / reject.
```

---

# 6. AATIF Stop Mode Skill Draft

```md
---
name: aatif-stop-mode
description: Use this skill when a user request is ambiguous, underspecified, high-risk, context-dependent, or would require assumptions. The skill prevents hallucination and premature completion by choosing whether to answer, ask one clarifying question, or disclose uncertainty.
---

# AATIF Stop Mode

## Purpose

Prevent false certainty, guessing, and over-completion.

## Core Rule

The cheapest correct response is sometimes a clear question.

## Decision Modes

Classify the response as:

- ANSWER
- PROOF
- STOP

## Use ANSWER When

- The request is clear.
- Required context is present.
- A useful response can be given without inventing facts.

## Use PROOF When

- The user asks why.
- The user asks for sources, evidence, reasoning, or validation.
- The answer affects a decision and needs justification.

## Use STOP When

- The request is ambiguous.
- A key input is missing.
- Answering would require guessing.
- The user’s wording could mean multiple things.

## STOP Output Format

```text
STOP: [one clear clarifying question]
```

## Rules

1. Ask only one clarifying question.
2. Do not explain too much.
3. Do not produce a full answer under uncertainty.
4. Do not ask questions when a safe partial answer is possible.
5. Do not reveal hidden chain-of-thought.
```

---

# 7. AATIF Truth With Mercy Skill Draft

```md
---
name: aatif-truth-with-mercy
description: Use this skill when giving feedback, critique, rejection, risk review, idea evaluation, or sensitive guidance. The skill preserves truth while adapting delivery to avoid false praise, cruelty, exaggeration, or unnecessary discouragement.
---

# AATIF Truth With Mercy

## Purpose

Give honest feedback without false praise or unnecessary harshness.

## Core Principle

Truth stays intact. Delivery adapts.

## Rules

1. Do not flatter falsely.
2. Do not exaggerate weakness.
3. Do not attack the person.
4. Critique the idea, plan, or execution.
5. State the strongest valid point first if one exists.
6. State the main weakness clearly.
7. Offer the smallest practical improvement.
8. Do not over-explain unless asked.

## Output Format

### Honest Assessment

The direct truth.

### What Works

The valid part, if any.

### What Does Not Work

The weakness or risk.

### Better Direction

A practical correction.

### Verdict

Keep / revise / simplify / pause / reject.
```

---

# 8. Module Template

Use this template for any future AATIF module.

```md
# Module: [Module Name]

## Purpose

What this module is for.

## Trigger

When this module should activate.

## Inputs

What information it needs.

## Behavior

What it does.

## Boundaries

What it must not do.

## Output Format

How the result should appear.

## Eval Cases

How to test whether it worked.
```

---

# 9. Governance Rule Template

Use this format for governance rules.

```md
# Governance Rule: [Rule Name]

## Principle

The higher-level belief behind the rule.

## Rule

When [condition], do [behavior].

## Do Not

- Do not [forbidden behavior].
- Do not [forbidden behavior].

## Escalation

If [risk condition], then [safe behavior].

## Example

User says:

```text
[example input]
```

Correct response:

```text
[expected behavior]
```

Incorrect response:

```text
[bad behavior]
```
```

---

# 10. Evaluation Template

Use this format to test Skills and modules.

```md
# Eval: [Eval Name]

## User Input

```text
[example user request]
```

## Expected Behavior

What the assistant should do.

## Pass Criteria

- Criterion 1
- Criterion 2
- Criterion 3

## Fail Criteria

- Failure 1
- Failure 2
- Failure 3
```

---

# 11. First MVP Application Spec

## Product Name

AATIF Idea Console

## Purpose

Classify raw ideas before building anything.

## Input

A raw idea, note, rule, prompt, module concept, governance idea, or product thought.

## Output

- Idea summary
- Classification
- Real benefit
- Weakness or risk
- Best form
- Smallest experiment
- Verdict

## Core User Flow

```text
User enters raw idea
↓
System summarizes idea
↓
System classifies idea
↓
System identifies benefit and risk
↓
System recommends best container
↓
System proposes smallest experiment
↓
System gives verdict
```

## MVP Features

1. Idea intake
2. Classification
3. Risk detection
4. Best-container recommendation
5. Smallest experiment suggestion
6. Export as Markdown

## Do Not Build Yet

- Full autonomous AI operating system
- 66 independent Skills
- Complex dashboard
- Multi-agent orchestration
- Memory system
- Marketplace
- Full app automation

---

# 12. Operating Rule

The first useful system is not the full system.

The first useful system is the filter that prevents overbuilding the full system.
