
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
