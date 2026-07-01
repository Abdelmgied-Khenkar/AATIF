# FN#065 Maqam Architecture Law — Design Consensus
## Claude × ChatGPT, 2026-07-01

### Overall Verdict: PASS WITH CONSTRAINTS

### Key Design Changes Incorporated

1. **Fix channel naming**: style hints bind to B5, not B1 → renamed to `b5_style_hints`
2. **Revise Nisba scoring**: use weighted scores + minimum evidence (≥2 markers), not raw ratio
3. **Separate SADNESS from VULNERABILITY** — sadness is grief/loss/low mood, vulnerability is openness/exposure
4. **Add URGENCY** as its own maqam (affects cadence and response compression)
5. **DEFIANCE as weak secondary only** — non-judicial, context-sensitive, not a primary maqam
6. **Keep full score distribution internally** for debugging, runtime emits primary + secondary only
7. **Arabic normalization + dialect provenance** — marker_source = gulf_ar / msa_ar / en
8. **Negation guards** — "I'm not sad" should not trigger SADNESS
9. **Confidence bands** — 0.25–0.39 weak hint, 0.40–0.59 moderate, 0.60+ strong
10. **Minimum evidence requirement** — at least 2 markers or one high-confidence phrase

### Q1: PASS WITH CONCERNS — Add SADNESS, URGENCY. DEFIANCE as weak secondary only.
Recommended v1 set: WARMTH, AUTHORITY, VULNERABILITY, SADNESS, PLAYFULNESS, SEEKING, GRATITUDE, FRUSTRATION, URGENCY, NEUTRAL

### Q2: PASS WITH CONCERNS — Keyword frozensets + regex hybrid OK. Add negation guards, marker weights, Arabic normalization.

### Q3: PASS WITH CONCERNS — Add elongated letters, emoji density, ellipses, caps/shouting, imperative density.

### Q4: NEEDS REVISION → REVISED — Use weighted ratio + minimum evidence (≥2 markers). Separate thresholds for short/medium/long messages. Primary requires nisba ≥ 0.35 AND confidence ≥ 0.25 AND minimum evidence.

### Q5: PASS WITH CONCERNS — Primary + secondary OK. Keep full distribution internally for trace. Secondary requires absolute confidence AND distance from primary < 0.25.

### Q6: PASS — Separate Gulf Arabic frozensets merged at detection. Keep marker provenance.

### Q7: PASS WITH CONCERNS — 0.25 OK with neutral fast-path. Confidence bands for hint strength.

### Q8: PASS WITH CONCERNS — Rename b1→b5. Add AUTHORITY_LEVEL constants. Add evidence_count, language_detected, dialect_hint.

License: BSL 1.1
