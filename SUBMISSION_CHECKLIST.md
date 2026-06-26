# EACL 2027 — ARR August 2026 Submission Checklist

**Paper:** AATIF: A Multiplicative Governance Equation for Arabic-Aware LLM Safety
**Author:** Abdulmjeed Ibrahim Khenkar (Independent Researcher)
**Submission deadline:** August 3, 2026 (11:59 PM UTC-12:00, "anywhere on Earth")
**Reviewer registration deadline:** August 5, 2026
**EACL commitment deadline:** October 11, 2026

---

## 1. Pre-Submission (Do BEFORE August 3)

### OpenReview Account & Profile
- [ ] Create or update OpenReview account at https://openreview.net/
- [ ] Add correct Semantic Scholar link to profile
- [ ] Add correct DBLP link to profile
- [ ] Add correct ACL Anthology link to profile (if applicable — first submission may not have one)
- [ ] Verify email address can receive OpenReview messages
- [ ] Update listed papers to reflect current research interests (for reviewer matching)

### Reviewer Registration
- [ ] Be aware of the mandatory reviewing requirement for ALL authors
- [ ] Complete the author registration form by August 5, 2026 EoD AoE (within 48h of submission)
- [ ] Understand that as a single author, you MUST serve as a reviewer (no exemption for solo authors unless qualifying under the ARR Author Reviewer Exemption Policy: https://aclrollingreview.org/exemptions2025)
- [ ] If assigned reviews: complete by September 7, 2026

---

## 2. Paper (aatif_paper_acl.tex)

### Format Compliance
- [ ] **CRITICAL:** Switch from custom LaTeX to the official ACL style template
  - Overleaf template: https://www.overleaf.com/latex/templates/association-for-computational-linguistics-acl-conference/jvxskxpnznfj
  - Or download from: https://github.com/acl-org/acl-style-files
- [ ] Enable `[review]` option in the template (required for submission)
- [ ] Verify 10pt font, correct margins per ACL formatting
- [ ] Run ACL pubcheck tool: https://github.com/acl-org/aclpubcheck
- [ ] Check font sizes in figures and tables (updated Jan 2025 guidelines)
- [ ] Appendices in double-column format (updated April 2025)

### Page Limits
- [ ] Main paper: max 8 pages (long paper) — currently fits
- [ ] Limitations section does NOT count toward page limit
- [ ] Ethics Statement does NOT count toward page limit
- [ ] References do NOT count toward page limit
- [ ] Appendices do NOT count toward page limit
- [ ] All of the above (Limitations, Ethics, References, Appendices) are in the SAME PDF — not separate files

### Required Sections
- [ ] "Limitations" section present — YES (Section 6)
- [ ] "Limitations" section contains ONLY limitations discussion (no new experiments, figures, or analysis)
- [ ] Ethics Statement present — YES (unnumbered section after Limitations)
- [ ] Recommend titling it "Ethical Considerations" (helps length assessment)

### Anonymization
- [ ] Author listed as "Anonymous" — YES (line 43)
- [ ] No self-identifying references in the text
- [ ] No acknowledgements section (remove for submission, add back for camera-ready)
- [ ] No links to non-anonymous repos or identifiable services
- [ ] Code repository link is anonymized (use anonymous GitHub or remove for review)
- [ ] Supplementary materials properly anonymized

### Content Quality Checks
- [ ] Remove or resolve the `[UNVERIFIED]` comment in Appendix E (line 663-666) — either verify the θ sweep numbers or remove the table
- [ ] Verify all bibliography entries are complete and correctly formatted
- [ ] Check that all cross-references resolve (\ref, \cite)
- [ ] No leftover comments or meta-text from prior revisions

---

## 3. Responsible NLP Research Checklist

- [ ] **Fill out in the OpenReview submission form** (NOT a separate PDF since Feb 2024)
- [ ] Use `responsible_nlp_checklist.tex` as reference for form answers
- [ ] For each "Yes" answer: provide specific section numbers
- [ ] For each "No" answer: provide justification (not just "No")
- [ ] Do NOT check "Yes" for questions that don't apply — mark them N/A with explanation
- [ ] Per EACL 2027 policy: checklist will be published as appendix in proceedings

### Quick Reference for Form Responses:
| Question | Answer | Section/Justification |
|----------|--------|----------------------|
| A1 (Limitations) | Yes | Section 6 |
| A2 (Risks) | Yes | Ethics Statement |
| B (Artifacts) | Yes | — |
| B1 (Citations) | Yes | Sections 2, 3.2 |
| B2 (Licenses) | Yes | Abstract, Ethics Statement |
| B3 (Intended use) | Yes | Section 6 |
| B4 (PII/offensive) | N/A | No new data created |
| B5 (Documentation) | Partially | Section 3.2, 4, Appendix E |
| B6 (Statistics) | Yes | Tables 3-6 |
| C (Experiments) | Yes | — |
| C1 (Parameters/budget) | Partially | Section 5 (add bge-m3 param count) |
| C2 (Hyperparameters) | Yes | Section 3.1, Table 2 |
| C3 (Descriptive stats) | Yes | Tables 3-6, deterministic system |
| C4 (Packages) | Yes | Section 3.2 |
| D (Human subjects) | No | N/A |
| E1 (AI assistants) | Yes | Coding & writing assistance |

---

## 4. Supplementary Materials

### Code
- [ ] Prepare anonymized code repository
- [ ] Include README with reproduction instructions
- [ ] Include BSL 1.1 license file
- [ ] Ensure code can reproduce: ablation, HarmBench, MultiJail, blind eval results
- [ ] Include the 249 anchor definitions (or a representative sample)

### Optional but Recommended
- [ ] Model card for AATIF framework
- [ ] Data sheet for the blind evaluation test set (if releasing)
- [ ] θ sweep results (Appendix E, currently marked [UNVERIFIED])

---

## 5. Submission Form Fields (OpenReview)

- [ ] Title: "AATIF: A Multiplicative Governance Equation for Arabic-Aware LLM Safety"
- [ ] Paper type: Long paper
- [ ] Track selection: See https://aclrollingreview.org/areas — likely tracks:
  - "Ethics, Bias, and Fairness" (primary)
  - "NLP Applications" or "Multilingualism and Cross-Lingual NLP" (secondary)
- [ ] Abstract: copy from paper
- [ ] Preprint status: select appropriate option (binding if "do not intend to release")
- [ ] Software: link to anonymized repo (or "will be released")
- [ ] Responsible NLP checklist: fill all fields per Section 3 above
- [ ] Confirm: not a dual submission
- [ ] Confirm: new submission (not a resubmission)

---

## 6. Known Issues to Fix Before Submission

### Critical (must fix)
1. **Switch to official ACL style template** — current paper uses custom LaTeX, which will be desk-rejected
2. **Anonymize code repository** — create anonymous GitHub or similar
3. **Resolve [UNVERIFIED] tag** in Appendix E (θ sweep) — either verify or remove
4. **Add bge-m3 parameter count** (~568M parameters) to Section 5

### Recommended
5. Add confidence intervals via bootstrap sampling on test sets
6. Add explicit note about AI writing assistance (for E1 checklist question)
7. Consider adding a model card as supplementary material
8. Verify bibliography: some entries use arXiv IDs — check if published versions exist

---

## 7. Post-Submission Timeline

| Date | Event |
|------|-------|
| Aug 3, 2026 | **Submission deadline** |
| Aug 5, 2026 | Reviewer registration form due |
| Sept 7, 2026 | Review assignments due (if assigned as reviewer) |
| Sept 14-19, 2026 | Author response period |
| Sept 20-24, 2026 | Reviewer engagement & author-reviewer discussion |
| Oct 2, 2026 | Meta-reviews due |
| Oct 8, 2026 | Meta-review released |
| Oct 11, 2026 | EACL 2027 commitment deadline |
| Nov 12, 2026 | Notification of acceptance |
| Nov 26, 2026 | Camera-ready due (+1 page allowed = 9 pages for long) |
| Mar 9-14, 2027 | EACL 2027 conference |

---

## 8. Special Notes for EACL 2027

- **Special Theme:** "The Human in Language" — consider if the paper can address this theme (Arabic dialect disambiguation and human-authored anchors may fit)
- **AI Reviewing Experiment:** opt-in only, AI reviews will NOT inform decisions — consider opting in to support the community
- **Paper Integrity Policy:** EACL 2027 takes action against hallucinated citations, AI-generated papers, and thinly sliced contributions — ensure all citations are verified
- **No anonymity period requirement** (following ACL/ARR policy update)
- **Author list changes:** not allowed after submission or during commitment

---

## Sources

- ARR Call for Papers: https://aclrollingreview.org/cfp
- ARR Responsible NLP Checklist: https://aclrollingreview.org/responsibleNLPresearch
- ARR Common Submission Problems: https://aclrollingreview.org/authorchecklist
- ARR Authors Guidelines: https://aclrollingreview.org/authors
- ARR Dates & Venues: https://aclrollingreview.org/dates
- EACL 2027 Call for Papers: https://2027.eacl.org/calls/papers/
- ACL Style Files: https://github.com/acl-org/acl-style-files
- ACL Pubcheck Tool: https://github.com/acl-org/aclpubcheck
- ACL Formatting Guidelines: https://acl-org.github.io/ACLPUB/formatting.html
- ACL Publication Ethics: https://www.aclweb.org/adminwiki/index.php/ACL_Policy_on_Publication_Ethics
- ARR Reviewer Exemptions: https://aclrollingreview.org/exemptions2025
- ARR Incentives Policy: https://aclrollingreview.org/incentives2025
