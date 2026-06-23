
## 2026-06-20 11:25 UTC — Agent وصّال sync run

**Task:** Propagate embedding-robustness fix to deployed scorers (academic → deployed AATIF root).

**Drift found (deployed /AATIF copies were behind canonical engine/):**
- aatif_intent_scorer.py — missing NaN/zero-norm query guard + confidence scoring
- aatif_emotion_scorer.py — same
- aatif_s_equation.py — DEFERRED (old linear model vs gated S; safety-critical, needs own run)
- aatif_semantic_scorer.py — DEFERRED (606 vs 267 lines; needs own run)

**Action taken:**
- Backed up deployed scorers (.bak.20260620_112538)
- Copied canonical aatif_intent_scorer.py + aatif_emotion_scorer.py to /AATIF (now byte-identical)
- These add: query-vector nan_to_num + unit-normalize before dot product (kills divide-by-zero/overflow RuntimeWarnings that could corrupt I/E), plus high/medium/low confidence + max_similarity in score() output (purely additive; old consumers unaffected).

**Verification:**
- Academic suite: 197 passed, 0 failed, 57 skipped (model/network), 73 subtests — before and after.
- Deployed connector imports clean (no RuntimeWarnings).
- build_intent_result() runs end-to-end on EN + AR + surveillance probes; decision path intact.

**Still drifted (next runs, one per run):** aatif_s_equation.py, aatif_semantic_scorer.py.

---

## 2026-06-22 14:15 UTC — Agent وصّال sync run

**Task:** Propagate the gated S-equation (canonical engine/ → deployed /AATIF). This was the safety-critical drift DEFERRED by the 2026-06-20 run.

**Drift resolved:**
- aatif_s_equation.py — deployed /AATIF was the OLD linear model (19,431 bytes, Jun 13); canonical is the gated model (36,288 bytes, Jun 22). Now byte-identical.

**Compatibility analysis (why this was safe to copy):**
1. Canonical public API is a strict SUPERSET of deployed — every old symbol preserved (compute_s_from_scores, AATIFEngine, sigmoid, PROFILES, THRESHOLDS, K_HARM_FLOOR, H_GUARD_THRESHOLD, print_result, print_full) plus the gated additions (compute_s_gated_from_scores, GATED_PROFILES, DOMAIN_CONFIG, get_domain_theta, H_GATED_HARD_OVERRIDE, link_h_to_intent).
2. Identical flat import block in both files (from aatif_semantic_scorer / _intent_scorer / _emotion_scorer / _hysteresis import ...) — NO package-relative imports, so the file works dropped flat into /AATIF. All four sibling modules exist there.
3. Canonical only calls SemanticHarmScorer().score() (+ intent/emotion) — class names and .score() method exist in the still-OLD deployed scorers, so no inter-file coupling break despite semantic_scorer not yet synced.
4. Sole deployed consumer is run_validation_30.py (AATIFEngine() + .compute(text, profile=) reading r["decision"]/r["S"]) — both the zero-arg ctor and the compute signature/return keys are preserved.
5. Blast radius: the S-equation is NOT in the live WhatsApp reply path — aatif_pipeline_connector.py imports aatif_intent_engine, not aatif_s_equation. Only the offline validation script consumes the deployed copy. Lowest-risk possible sync.

**Action taken:**
- Backed up deployed: aatif_s_equation.py.bak.20260622_141354
- py_compile gate on canonical BEFORE copy → OK
- Copied canonical → deployed; cmp confirms byte-identical
- py_compile + live import of deployed copy in /AATIF context → IMPORT OK, all 12 expected symbols present

**Verification:**
- Academic suite (engine/ untouched): 336 passed, 0 failed, 57 skipped (model/network), 73 subtests passed.
- NOTE: sandbox initially showed 16 "failures" — all ModuleNotFoundError: sklearn (TF-IDF fallback backend dep). Installing scikit-learn cleared them. Not a code issue.

**Still drifted (next run):** aatif_semantic_scorer.py (deployed 13,563 bytes / Jun 12 vs canonical 35,510 bytes / Jun 20). This is the last known scorer drift from the 2026-06-20 audit. Recommend it as the next single-task run — note the deployed s_equation now expects SemanticHarmScorer().score() which the old semantic_scorer still provides, so syncing semantic_scorer next will keep that contract.
