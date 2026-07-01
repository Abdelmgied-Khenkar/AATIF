# FN#051 MRS Detector — Design Consensus
## Claude × ChatGPT, 2026-07-01

### Overall Verdict: PASS with important concerns

### Key Design Changes Incorporated

1. **Rename `recommendations` → `b5_style_hints`** — prevents therapeutic action creep
2. **Add compound pattern support** — primary + secondary interpretation types
3. **Add crisis isolation fields** — `requires_independent_safety_evaluation=True`
4. **Add Arabic idiom handling** — `idiomatic_distress_possible` flag, Gulf dialect markers
5. **Raise activation threshold 0.20 → 0.35** — reduce false positives
6. **Expand LBH warnings** — add MORALIZING_RISK, UNEARNED_REASSURANCE_RISK, PREMATURE_FIXING_RISK
7. **Add secondary subpattern types** — ASSUMED_NEGATIVE_JUDGMENT, PUNITIVE_SHOULD_STATEMENT, POSITIVE_DISQUALIFICATION, EMOTIONAL_REASONING
8. **Add non-activation examples** — explicit sadness-vs-interpretation distinction

### Q1: PASS/CONCERN — Detector scope correct, rename recommendations to b5_style_hints
### Q2: PASS/CONCERN — Five types good, add secondary subpatterns
### Q3: CONCERN — Crisis signal must not be trapped in B5-only; add requires_independent_safety_evaluation
### Q4: CONCERN — Add Gulf Arabic dialectal markers and idiom filter
### Q5: PASS/CONCERN — Expand LBH warnings (moralizing, unearned reassurance, premature fixing)
### Q6: PASS — Add compound pattern detection (primary + secondary)
### Q7: CONCERN — Raise threshold, require event-interpretation split for activation

License: BSL 1.1
