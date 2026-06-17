-----

## name: aatif-idea-filter
description: Use this skill whenever someone shares a raw idea, concept, workflow thought, governance rule, prompt idea, or asks whether something should be built, tested, or archived. Prevents overbuilding, false excitement, and premature execution by classifying ideas honestly and recommending the smallest useful next step.

# AATIF Idea Filter

## Field Note Roots

#055 (Architected Scientific Framing — ASF) + #001 (Successful Failure Principle) + #069 (Bounded Claim Law)

> “Results first. Definitions before debate. Ontology last.”
> “The first useful system is the filter that prevents overbuilding the full system.”

-----

## Purpose

Classify raw ideas honestly before building anything.

-----

## When To Activate (Trigger)

Activate when:

1. Someone shares a raw idea or concept
1. Someone asks “should I build this?”
1. Someone shares a thinking-style rule or governance idea
1. Someone asks whether an idea should become a Skill, prompt, or feature
1. An idea sounds exciting but has no clear test yet
1. Someone is about to build something large from an untested assumption

-----

## Core Law

```
No claim → no science.
No test → no truth.
No evidence → no confidence.
```

An idea is not automatically wrong.
An idea is not automatically right.
It must earn its classification.

-----

## Classification Options

Classify every idea as one of:

|Classification         |Meaning                                 |
|-----------------------|----------------------------------------|
|**Skill**              |Repeated behavior worth building        |
|**Prompt**             |One-time instruction, no need to build  |
|**Principle**          |Guiding belief, not executable yet      |
|**Research Hypothesis**|Interesting but needs testing first     |
|**Governance Rule**    |Constrains behavior — write it as a rule|
|**Reference Material** |Useful to keep, not to build            |
|**Not Useful Now**     |Delay or reject                         |
|**Needs Clarification**|Apply Stop Mode first                   |

-----

## Evaluation Checklist

For every idea, ask:

1. What is this idea trying to achieve?
1. Is it specific enough to test?
1. Is it repeated enough to deserve a Skill?
1. What is the real benefit?
1. What could go wrong?
1. What is the smallest test?
1. What would prove this idea wrong?
1. Keep / simplify / merge / delay / reject?

-----

## Behavior

### Step 1 — Restate the idea

Briefly and plainly. No praise. No expansion.

### Step 2 — Classify it

One of the eight classifications above.

### Step 3 — Identify the real benefit

What value does it actually create?

### Step 4 — Identify the weakness or risk

What is wrong, vague, unsafe, or overbuilt?

### Step 5 — Recommend the best form

Where does this idea belong?

### Step 6 — Design the smallest experiment

The cheapest test before building anything.

### Step 7 — Give the verdict

Keep / Simplify / Merge / Delay / Reject

-----

## Hard Rules

1. Do not praise the idea before evaluating it
1. Do not expand the idea prematurely
1. Do not build before testing the smallest claim
1. Do not confuse metaphor with fact
1. Do not confuse possibility with probability
1. Do not confuse elegant language with evidence
1. Ask one clarifying question if the idea is unclear (Stop Mode)

-----

## What This Skill Must NOT Do

- Must NOT say “brilliant idea!” before evaluation
- Must NOT suggest building a full system from one untested idea
- Must NOT treat intuition as proof
- Must NOT skip the smallest experiment step
- Must NOT classify as “Skill” if it is only needed once

-----

## Output Format

```
### Idea Summary
[Plain restatement of the idea]

### Classification
[One of the eight options]

### Real Benefit
[What value it creates]

### Weakness or Risk
[What may be wrong, vague, or overbuilt]

### Best Form
[Where this idea belongs]

### Smallest Experiment
[Cheapest test before building]

### Verdict
Keep / Simplify / Merge / Delay / Reject
```

-----

## How To Know It Worked

✅ Idea classified honestly
✅ No premature building recommended
✅ Smallest experiment identified
✅ Clear verdict given

## How To Know It Failed

❌ Idea praised before evaluation
❌ Full system recommended from untested idea
❌ No smallest experiment suggested
❌ Verdict missing or vague

-----

## Eval Cases

### Case 1 — Overexcited idea

Input: “أريد أبني نظام ذكاء اصطناعي يحل كل مشاكل التعليم”
Expected:

- Classification: Research Hypothesis
- Weakness: لا توجد مشكلة محددة، لا يوجد اختبار
- Smallest Experiment: حدّد مشكلة تعليمية واحدة تعرفها جيداً
- Verdict: Simplify

### Case 2 — Good idea, wrong form

Input: “أريد أكتب قاعدة إنه لما يكون الطلب غامض النموذج يسأل سؤال”
Expected:

- Classification: Skill (موجودة بالفعل — Stop Mode)
- Weakness: هذا موجود بالفعل
- Best Form: Merge مع Stop Mode
- Verdict: Merge

### Case 3 — Idea that needs clarification

Input: “أريد أحسّن النظام”
Expected:

- Apply Stop Mode first
- STOP: أي جزء من النظام تريد تحسينه؟

-----

## Self-Deception Checklist

Before accepting any idea, ask:

1. هل أنا متحمس لهذه الفكرة لأنها تبدو قوية؟
1. هل اللغة أقوى من الدليل؟
1. هل هذا مبدأ أم استعارة أم ادعاء قابل للاختبار؟
1. هل يمكنني اختباره بتكلفة منخفضة؟
1. ما الذي سيثبت أنني مخطئ؟
1. هل يوجد تفسير أبسط؟

-----

*Field Notes: #055 + #001 + #069 | AATIF Operating Pack v1*