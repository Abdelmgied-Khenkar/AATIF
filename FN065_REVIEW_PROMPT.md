EXTERNAL CODE REVIEW — FN#065 Maqam Architecture Law (LAW BEH-01)

CONTEXT: AATIF OS is a multi-layer AI governance framework. This is a new B-prime OBSERVATIONAL module that detects the emotional "maqam" (mode) of user text using a triad borrowed by analogy from Arabic musical maqam theory. It is NOT music theory — it detects emotional modes in text.

AUTHORITY CONTRACT (B-prime):
- AUTHORITY_LEVEL = B_PRIME_OBSERVATIONAL
- CAN_BLOCK_RUNTIME = False
- CAN_MODIFY_H/θ/S = False (cannot touch safety variables)
- CAN_EMIT_JUDICIAL_DECISION = False
- BINDING_CHANNEL = B5 (Behaviour, NOT B1)
- safety_decision_authority = "GOVERNANCE_EQUATION_ONLY"
- _isolation_marker = "B5_ADVISORY_NOT_FOR_SAFETY"

DETECTION TRIAD:
1. Jins (الجنس) — structural emotional unit: which emotional "mode" dominates
2. Aqd (العقد) — cadence/rhythm: sentence length variance, punctuation density, question ratio
3. Nisba (النسبة) — fingerprint ratio: weighted marker score / total score

10 MAQAM TYPES (v1 consensus):
NEUTRAL, WARMTH, AUTHORITY, VULNERABILITY, SADNESS, PLAYFULNESS, SEEKING, GRATITUDE, FRUSTRATION, URGENCY

KEY DESIGN DECISIONS (from Claude×ChatGPT consensus):
1. SADNESS separate from VULNERABILITY (grief≠fragility)
2. URGENCY as own maqam (affects cadence compression)
3. DEFIANCE excluded from v1 (weak secondary only, non-judicial)
4. Bilingual markers: EN + MSA Arabic + Gulf dialect per maqam (frozensets)
5. Negation guards: "I'm not sad" does NOT trigger SADNESS
6. Weighted Nisba scoring + minimum evidence ≥2 markers
7. Confidence bands: 0.25-0.39 WEAK, 0.40-0.59 MODERATE, 0.60+ STRONG
8. Secondary maqam: requires absolute confidence ≥0.30 AND distance from primary <0.25
9. Sparse activation: below 0.25 threshold → fast-path NEUTRAL skip
10. Full score distribution kept internally for debug; runtime emits primary+secondary only

DATACLASSES (all frozen=True):
- JinsReading: dominant_pattern, strength, markers_found
- AqdReading: cadence_type, rhythm_score, sentence_length_variance, punctuation_density, question_ratio
- NisbaReading: ratio, confirmed, evidence_count, characteristic_markers
- MaqamReading: detected_maqam, confidence, confidence_band, jins, aqd, nisba, secondary_maqam, secondary_confidence, markers_found, evidence_count, language_detected, dialect_hint, scores_by_maqam, b5_style_hints, activated, safety_decision_authority, _isolation_marker

CADENCE TYPES: FLAT, ASCENDING, DESCENDING, STACCATO, FLOWING, BROKEN, BOUNCY

MARKER EXAMPLE (WARMTH):
EN: "thank you so much", "i appreciate", "you're so kind", "means a lot", "sending love"...
AR: "يعطيك العافية", "الله يسعدك", "ما قصرت", "من قلبي"...
Gulf: "يا عمري", "الله يخليك", "يا حياتي"...

detect_maqam(text) PIPELINE:
Phase 1: Jins — scan all marker sets (EN+AR), check negation guards
Phase 2: Check activation threshold (total_score>0 AND markers≥2)
Phase 3: Compute nisba ratios per maqam
Phase 4: Rank maqams by score
Phase 5: Determine secondary maqam (confidence≥0.30, distance<0.25)
Phase 6: Build triad readings (JinsReading, AqdReading, NisbaReading)
Phase 7: Generate B5 style hints for R equation

TESTS: 101 tests, ALL PASS. Covering authority contract, feature flag, sparse activation, all 10 maqams (EN+AR+Gulf), negation guards, cadence, confidence bands, B5 hints, language/dialect detection, frozen immutability, edge cases.

REVIEW QUESTIONS:
R1: Does the authority contract properly isolate this module from safety decisions?
R2: Is the 10-maqam set well-chosen for v1? Any critical gaps?
R3: Is the triad (jins/aqd/nisba) a sound decomposition for emotional mode detection?
R4: Are the confidence thresholds and bands well-calibrated?
R5: Any architectural risks or blind spots?

Please classify each as: PASS / PASS WITH CONCERNS / NEEDS REVISION
End with overall verdict and any P0 (must-fix) issues.
