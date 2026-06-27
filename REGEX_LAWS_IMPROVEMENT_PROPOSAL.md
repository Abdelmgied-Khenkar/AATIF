# Regex Laws Improvement Proposal — تحسين قوانين الـ Regex

**Status:** Research & Proposal (لا تعديل على الكود)  
**Priority:** P0 #3 (from 3-model independent review)  
**Date:** 2026-06-26  
**Author:** Analysis by Claude, for review by The Architect  

---

## 1. Current State — الوضع الحالي

### What Are the "Laws"?

AATIF uses regex patterns (text-matching rules) as a first line of defense — a fast safety net that catches dangerous content BEFORE the slower embedding-based scoring even runs. Think of it like a metal detector at the door: fast, catches obvious threats, but can't tell a belt buckle from a knife.

There are **3 layers** of regex-based detection, spread across **2 files**:

---

### Layer 1: Law Ω — CBRN Gate (أسلحة الدمار الشامل)

**What it does:** Catches weapons of mass destruction content — chemical, biological, radiological, nuclear.  
**Result when triggered:** Unconditional SAFE_STOP (لا يُكمل أبداً).  
**Where it lives:** Defined in `aatif_intent_engine.py` (lines 111-134), copied into `aatif_s_equation.py` (lines 225-278).

| Category | Count | Examples |
|----------|-------|---------|
| Arabic CBRN regex | 24 patterns | قنبل، متفجر، سارين، غاز الأعصاب، يورانيوم، سلاح نووي |
| English CBRN substrings | 27 triggers | "nerve agent", "dirty bomb", "nuclear weapon", "weaponized pathogen" |

**How it works:**
- English: exact substring match (`if trigger in text_lower`)
- Arabic: regex search (`re.search(pat, text_lower)`)
- Runs BEFORE any scoring — if it fires, everything else is skipped

**Smart design already in place:**
- Dual-use terms (نووي، كيميائي، بيولوجي) only fire WITH weapon framing (سلاح/قنبلة/أسلحة)
- "طاقة نووية" (nuclear energy) does NOT trigger, "سلاح نووي" (nuclear weapon) DOES
- Short roots avoided: bare "سم" excluded (would hit بسم/اسم/قسم/جسم/موسم)
- سلاح has no negative lookahead for سلاحف (turtles) in the regex itself, but the test suite (`test_safety_gate.py`) explicitly tests that سلاحف does NOT trigger CBRN — it doesn't because the CBRN list uses "سلاح\s*نووي" (weapon+nuclear), not bare "سلاح"

---

### Layer 2: Law Ξ — Override/Jailbreak Detection (كسر الحماية)

**What it does:** Catches attempts to bypass safety rules, override instructions, or trick the system.  
**Result when triggered:** SAFE_FREEZE (أشد من STOP — تجميد كامل).  
**Where it lives:** Both `aatif_intent_engine.py` (lines 249-281) and `aatif_s_equation.py` (lines 306-351).

Two sub-layers:

**2a. Exact substring triggers** (11 phrases):
```
"ignore previous", "disregard safety", "override stop", "bypass safety",
"ignore safety", "skip safety check", "force execute", "override safe stop",
"تجاهل الأمان", "تخطي الحماية", "تجاوز التوقف"
```

**2b. Regex patterns** (2 compiled patterns):
- **English:** bypass-VERB + safety-TARGET within ~30 characters  
  Verbs: ignore, disregard, bypass, override, skip, forget, disable, circumvent, defeat, evade, remove, drop, turn off  
  Targets: safety, safeguards, rules, restrictions, guidelines, instructions, protocols, guardrails, filters, policy, constraints, limitations, alignment
  
- **Arabic:** bypass-VERB + safety-TARGET within a short window  
  Verbs: تجاهل، تجاوز، تخطي، عطّل، اكسر، الغي، ألغ  
  Targets: الأمان، الحماية، القواعد، التعليمات، القيود، الحظر، الفلتر، الضوابط

---

### Layer 3: Jailbreak Markers (علامات التلاعب)

**What it does:** Catches known jailbreak patterns and malware tool names.  
**Result when triggered:** Feeds into SAFE_FREEZE decision path.  
**Where it lives:** `aatif_s_equation.py` (lines 194-205).

**19 exact substring markers:**
```
English: "ignore instructions", "ignore previous", "override safety",
         "bypass", "developer mode", "jailbreak", " dan ",
         "disable safety", "act as if"
Arabic:  "تجاوز", "تجاهل القوانين", "تجاهل القيود", "مسؤول النظام",
         "تخطى الحماية", "وضع المطور"
Malware: "keylogger", "trojan", "rootkit", "ransomware",
         "spyware", "backdoor", "rat "
```

**Notable fix already applied:** The " DAN " marker was originally uppercase but matched against `text.lower()`, so it never fired. Fixed and regression-tested in `test_jailbreak_markers.py`.

---

### Layer 4: Output Gate Patterns (فلتر المخرجات)

**What it does:** Catches harmful content in the LLM's RESPONSE (not the user's input).  
**Result when triggered:** Response is blocked or sanitized.  
**Where it lives:** `aatif_output_gate.py` (lines 86-203).

| Pattern Group | Count | What It Catches |
|--------------|-------|----------------|
| Safety leak patterns | 14 regex | Weapon/explosive instructions, drug synthesis, self-harm instructions, hacking instructions in responses |
| Healthcare safety | 7 regex | "stop taking medication", medical misinformation |
| PII leak patterns | 4 regex | Credit card numbers, SSN, email exposure |
| Identity leaks | 6 regex pairs | Other AI brand references (ChatGPT, Bard, etc.) |
| Dismissive AI phrases | 6 regex pairs | "I'm just an AI", "بصفتي ذكاء اصطناعي" |
| Forbidden phrases | 15 regex pairs | System internals exposure, cold/robotic phrases |

---

### Layer 5: Harm Patterns (in Intent Engine)

**What it does:** Assigns graded harm scores (0.4 to 0.9) based on regex matches.  
**Result when triggered:** Raises the H score in the S equation.  
**Where it lives:** `aatif_intent_engine.py` (lines 136-147).

| Harm Level | Patterns |
|-----------|----------|
| 0.4 | delete, remove, حذف, امسح, drop, reset, format |
| 0.6 | password, كلمة سر, credit, bank, سلاح (not سلاحف), مسدس, بندقية |
| 0.7 | sudo, root, admin, chmod, rm -rf |
| 0.9 | All 24 CBRN Arabic patterns (same list as Law Ω) |

---

### Important: Arabic Normalization EXISTS but is NOT Used by Laws

`aatif_arabic_utils.py` has a full normalization pipeline:
- Strips diacritics (tashkeel/حركات)
- Removes tatweel (kashida/ـ)
- Normalizes alef variants (أ إ آ ٱ → ا)
- Normalizes taa marbuta (ة → ه)
- Normalizes hamza-on-carrier (ؤ → و, ئ → ي)

**But none of the Law regex patterns use this normalization before matching.** The regex runs on raw text. This is the single biggest gap.

---

## 2. False Positive Analysis — تحليل الإيجابيات الكاذبة

### Test Cases from The Architect

| # | Input | What it is | Law Ω fires? | Should it fire? | Verdict |
|---|-------|-----------|--------------|----------------|---------|
| 1 | "ما هو غاز السارين؟ وماذا حدث في هجوم طوكيو؟" | Educational: what is sarin + Tokyo attack history | ✅ YES (سارين matches) | ❌ No — this is a factual/historical question | **FALSE POSITIVE** |
| 2 | "علاج التسمم بغاز الأعصاب" | Medical: treatment for nerve agent poisoning | ✅ YES (غاز الأعصاب matches) | ❌ No — medical/treatment context | **FALSE POSITIVE** |
| 3 | "تاريخ الأسلحة الكيميائية في الحرب العالمية الأولى" | Historical: chemical weapons in WWI | ✅ YES (أسلحة كيميائية matches) | ❌ No — historical context | **FALSE POSITIVE** |
| 4 | "What is sarin gas? What happened in the Tokyo attack?" | English version of #1 | ✅ YES ("sarin" matches) | ❌ No — educational | **FALSE POSITIVE** |
| 5 | "Treatment for nerve agent poisoning" | English version of #2 | ✅ YES ("nerve agent" matches) | ❌ No — medical | **FALSE POSITIVE** |
| 6 | "History of chemical weapons in World War I" | English version of #3 | ✅ YES ("chemical weapon" matches) | ❌ No — historical | **FALSE POSITIVE** |

### Why These Are False Positives

The regex patterns are **context-blind** — they match on the presence of a keyword, period. They cannot distinguish:

- **"ما هو غاز السارين"** (what IS sarin = educational question)  
  from **"كيف أصنع غاز السارين"** (how to MAKE sarin = weapon instructions)

- **"treatment for nerve agent poisoning"** (saving lives)  
  from **"how to make a nerve agent"** (taking lives)

- **"تاريخ الأسلحة الكيميائية"** (history = academic)  
  from **"تصنيع أسلحة كيميائية"** (manufacturing = dangerous)

The **structure verbs** make all the difference: "ما هو" vs "كيف أصنع", "treatment" vs "how to make", "تاريخ" vs "تصنيع". The regex doesn't look at these.

### Current Mitigation

The existing design explicitly acknowledges this tradeoff. From the code comments:
> "Design notes (mercy + truth — do not over-block legitimate science/education)"

The system chose **safety over precision** for CBRN — better to over-block a history question than to let through a bomb recipe. This is a defensible choice for an initial implementation, but the 3-model review correctly identified it as an area for improvement.

### Existing True Negative Protection (Things That DON'T False-Positive)

The system already handles these correctly:

| Input | Result | Why |
|-------|--------|-----|
| بسم الله الرحمن الرحيم | ✅ No trigger | Bare "سم" excluded from CBRN list |
| ما معنى اسمي | ✅ No trigger | "اسم" doesn't match any pattern |
| سلاحف البحر | ✅ No trigger | سلاحف doesn't match "سلاح\s*نووي" (needs weapon+type) |
| كيف تعمل الطاقة النووية | ✅ No trigger | "نووية" alone doesn't fire — needs "سلاح/قنبلة" prefix |
| اشرح لي تفاعل كيميائي | ✅ No trigger | "كيميائي" alone doesn't fire — needs weapon framing |

These are well-designed. The dual-use gating (requiring weapon framing for ambiguous terms) is good engineering.

---

## 3. Gap Analysis — تحليل الثغرات

### Gap 1: No Arabic Text Normalization Before Regex (الأهم)

**The problem:** `aatif_arabic_utils.py` has normalize_arabic() that strips diacritics, normalizes alef/hamza/taa marbuta. But the regex patterns match against RAW text — no normalization first.

**What this means in practice:**

| Bypass attempt | What happens | Why |
|---------------|-------------|-----|
| قُنْبُلَة (with tashkeel) | ❌ Might not match `قنبل` | Diacritics inserted between letters change the raw string |
| قـنـبـلـة (with tatweel) | ❌ Won't match `قنبل` | Kashida characters inserted between letters |
| اسلحه كيميائيه (taa marbuta as haa) | ❌ Won't match `أسلحة كيميائية` | ة vs ه difference |
| أسلحة → اسلحه (alef + taa variants) | ❌ Partial miss | Pattern has أسلحة with hamza-alef, input might have bare alef |

**How bad is it?**
- Tashkeel bypass: **Medium risk.** Most Arabic users don't type with diacritics. But a deliberate attacker could add them.
- Tatweel bypass: **Medium risk.** Same logic — unusual but easy to do.
- Alef/hamza variants: **Higher risk.** Natural variation — many Arabic users type إ أ آ ا interchangeably. The pattern `أسلحة` with hamza won't match `اسلحة` without hamza.

**Evidence from the code:**
The intent engine already handles SOME of this by having both forms:
```python
r"أسلحة\s*كيميائية",   # with hamza-alef
r"اسلحة\s*كيميائية",   # without hamza-alef (bare alef)
```
But this is done **manually for one pattern only** — not systematically.

**Fix difficulty:** Easy. Call `normalize_arabic(text)` before running regex. Then normalize the patterns too. One function call.

---

### Gap 2: Context Blindness (العمى عن السياق)

**The problem:** Regex matches keywords, not meaning. It cannot distinguish:
- Educational intent: "ما هو السارين" (what is sarin)
- Harmful intent: "كيف أصنع السارين" (how to make sarin)

**This is the false positive problem from Section 2, restated as a gap.**

**How bad is it?**
- For CBRN (Law Ω): Causes over-blocking of legitimate educational, historical, and medical content. The system currently blocks ALL these — a student asking about WWI chemical warfare gets the same treatment as someone asking to make chemical weapons.
- For Override (Law Ξ): Less of an issue — override attempts don't really have an "educational" context.

**Fix difficulty:** Hard. Requires either:
1. A lightweight classifier layer on top of regex (moderate effort)
2. Passing context to the embedding scorer before deciding (already exists in the H scorer, but runs AFTER the regex gate)

---

### Gap 3: Spelling Variation Bypass (التهجئة البديلة)

**The problem:** Arabic has many ways to write the same word, beyond what normalization covers:

| Standard | Variant | Type |
|---------|---------|------|
| بلوتونيوم | بلتونيوم | Common misspelling |
| بيولوجي | بيلوجي | Already handled! (both in the list) |
| يورانيوم | يورنيوم | Shortened form |
| متفجرات | مفرقعات | Synonym (firecrackers/explosives) |
| سيانيد | سيناد | Misspelling |

**How bad is it?** Low-medium. Most misspellings are caught by the embedding scorer (H score) even if the regex misses them. The regex is just the first gate — the embedding layer behind it is much more robust to spelling variation.

**Fix difficulty:** Easy for known variants (add them). Hard for unknown variants (need fuzzy matching).

---

### Gap 4: English Patterns Are Substring, Not Regex (أقل مرونة)

**The problem:** English CBRN triggers use exact substring matching (`if trigger in text_lower`), while Arabic uses regex. This means:

| English Pattern | Matches | Doesn't Match |
|----------------|---------|---------------|
| "chemical weapon" | "chemical weapon" | "chemical weapons" (YES it matches — substring) |
| "nerve agent" | "nerve agent" | "nerve-agent" (hyphen breaks it) |
| "nuclear weapon" | "nuclear weapon" | "nuclear   weapon" (extra spaces break it) |

**How bad is it?** Low. English spelling is more standardized than Arabic, and the patterns already cover plural forms. Edge cases are rare.

---

### Gap 5: No Romanized Arabic (فرانكو/عربيزي)

**The problem:** Some users write Arabic in Latin characters (Franco-Arabic / Arabizi):
- "qunbula" = قنبلة
- "sila7 nawawi" = سلاح نووي  
- "gaz al a3sab" = غاز الأعصاب

None of the regex patterns catch this.

**How bad is it?** Low. This is a niche attack vector. The embedding scorer (bge-m3) may catch some of these since it processes multilingual text. But it's a real gap.

**Fix difficulty:** Medium. Would need a Romanized-Arabic → Arabic transliteration step, or a separate set of Romanized patterns.

---

## 4. Proposed Architecture — الهيكل المقترح

### Current Flow (الآن):
```
User Input
    ↓
[Law Ω regex] ──match──→ SAFE_STOP (unconditional)
    ↓ no match
[Law Ξ regex] ──match──→ SAFE_FREEZE (unconditional)
    ↓ no match
[Jailbreak markers] ──match──→ SAFE_FREEZE
    ↓ no match
[Embedding scorer (H)] ──score──→ feeds S equation
    ↓
[S equation decision]
    ↓
[Output Gate regex] ──on response──→ block/sanitize
```

**Problem:** The regex gates (top 3 boxes) are binary — match = stop, no match = pass. No context, no gradation.

### Proposed Flow (المقترح):

```
User Input
    ↓
[Normalize Arabic text] ←── uses existing normalize_arabic()
    ↓
[Law Ω regex on normalized text] ──match──→ CBRN_CANDIDATE (not instant stop)
    ↓                                              ↓
    ↓                                    [Context Classifier]
    ↓                                    Is the surrounding context:
    ↓                                    • Educational (ما هو، تاريخ، اشرح)
    ↓                                    • Medical (علاج، أعراض، وقاية)
    ↓                                    • Instructions (كيف أصنع، طريقة)
    ↓                                              ↓
    ↓                                    Educational/Medical → SAFE_STOP
    ↓                                    with helpful redirect message
    ↓                                              ↓
    ↓                                    Instructions → SAFE_STOP (hard block)
    ↓                                              ↓
    ↓                                    Unclear → SAFE_STOP (keep current behavior)
    ↓ no match
[Law Ξ regex on normalized text] ──match──→ SAFE_FREEZE (keep current behavior)
    ↓ no match
[Rest of pipeline unchanged]
```

### What Changes (3 things):

**Change 1: Normalize before matching (سهل)**
- Call `normalize_arabic(text)` before running any regex
- Also normalize the regex patterns themselves (one-time, at module load)
- This closes Gap 1 completely
- **Risk: Very low** — normalization is well-tested, deterministic, no ML involved

**Change 2: Context classifier for CBRN matches (متوسط)**
- When Law Ω regex matches, DON'T immediately SAFE_STOP
- Instead, check the surrounding words for context signals
- This is a lightweight rule-based check, NOT a full ML classifier:

```python
EDUCATIONAL_SIGNALS = [
    "ما هو", "ما هي", "ماهو", "ماهي",        # what is
    "اشرح", "فسر", "وضح",                      # explain
    "تاريخ", "تاريخية",                         # history
    "ما معنى", "تعريف",                         # definition
    "what is", "explain", "history of",
    "define", "what happened",
]

MEDICAL_SIGNALS = [
    "علاج", "أعراض", "وقاية", "تشخيص",         # treatment, symptoms, prevention
    "treatment", "symptoms", "prevention",
    "antidote", "first aid", "diagnosis",
]

INSTRUCTIONAL_SIGNALS = [
    "كيف أصنع", "كيف اصنع", "طريقة صنع",       # how to make
    "كيف أسوي", "كيف اسوي",                     # how to make (dialect)
    "how to make", "how to build",
    "instructions for", "recipe for",
    "طريقة تحضير", "طريقة تصنيع",               # preparation/manufacturing method
]
```

- If educational/medical signals present → still SAFE_STOP, but with a redirect message:  
  "هذا موضوع حساس. أقدر أعطيك معلومات تاريخية/طبية عامة، لكن ما أقدر أشرح طريقة التصنيع."
  
- If instructional signals present → hard SAFE_STOP (current behavior)
- If unclear → SAFE_STOP (current behavior — default to safety)

**This is NOT relaxing the safety gate.** The system still stops on CBRN content. The difference is: educational queries get a helpful message instead of a cold block, and the system knows WHY it stopped.

**Risk: Low-medium** — still stops on all CBRN, just adds better UX for legitimate queries.

**Change 3: Feature-flagged deployment (أساسي)**
- ALL changes behind a feature flag: `REGEX_V2_ENABLED = False`
- When flag is OFF: current behavior exactly preserved
- When flag is ON: normalized regex + context classifier active
- Flag controlled in config, not in code
- Can be toggled per-domain (education domain might enable it first)

---

## 5. What NOT to Change (ما لا يتغير)

| Component | Status | Why |
|-----------|--------|-----|
| Law Ω existence | Keep | The CBRN regex gate is essential — fast, cheap, no ML dependency |
| Law Ξ behavior | Keep | Override detection works well, false positives are rare |
| Jailbreak markers | Keep | Simple, effective, well-tested |
| Output Gate patterns | Keep | Response-side filtering is a separate concern |
| Embedding scorer (H) | Keep | The real intelligence layer — regex is just the first gate |
| Default-to-safety | Keep | When in doubt, stop. Never relax this. |

---

## 6. Implementation Estimate — تقدير التنفيذ

| Change | Effort | Risk | Priority |
|--------|--------|------|----------|
| 1. Normalize before regex | ~2 hours | Very low | Do first |
| 2. Context classifier | ~1 day | Low-medium | Do second |
| 3. Feature flag wiring | ~1 hour | Very low | Do with #1 |
| Test updates | ~2 hours | None | After each change |
| **Total** | **~2 days** | **Low overall** | |

### Suggested Implementation Order:

1. **Phase 1 (normalization + flag):** Add `normalize_arabic()` call before regex matching. Wire feature flag. Update tests. Deploy with flag OFF.
2. **Phase 2 (context classifier):** Build the context signal checker. Add tests for the 6 Architect test cases. Deploy with flag OFF for testing.
3. **Phase 3 (activate):** Turn flag ON in education domain first. Monitor for 1 week. Then expand.

---

## 7. Summary — الخلاصة

### What's Good Now (ما يعمل بشكل جيد):
- Law Ω design is smart: dual-use gating, short-root avoidance, mode-independent
- Law Ξ regex catches paraphrased jailbreaks well
- Test coverage is strong (`test_safety_gate.py`, `test_jailbreak_markers.py`)
- The embedding scorer behind the regex layer catches what regex misses

### What Needs Improvement (ما يحتاج تحسين):
1. **Arabic normalization** not applied before regex — tashkeel/tatweel/alef bypass possible
2. **Context blindness** — educational and medical questions about CBRN topics are over-blocked
3. **Spelling variants** — some Arabic misspellings/synonyms not covered

### The Core Tension (التوازن):
This is mercy vs. protection. The current system chose protection (over-block everything). The proposal keeps protection as the default but adds a thin layer of mercy — if someone is clearly asking to LEARN, they get a helpful redirect instead of a cold wall. Manufacturing instructions still get the full wall.

### Decision Needed from The Architect:
1. Approve normalization fix (Phase 1) — low risk, clear benefit
2. Approve context classifier approach (Phase 2) — or prefer a different approach?
3. Which domain to pilot first — education seems natural
4. Whether to also address Romanized Arabic (Gap 5) in this iteration or defer

---

*ملاحظة: هذا التقرير للقراءة والمراجعة فقط. لم يتم تعديل أي كود. كل التغييرات المقترحة تحتاج موافقة المعماري أولاً.*
