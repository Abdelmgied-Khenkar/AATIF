# Arabic Dialect Anchor Research for AATIF Safety Governance Engine

**Date:** 2026-06-27  
**Purpose:** Research document for expanding dialect coverage in the AATIF embedding-based safety scorer (H/I/E)  
**Status:** Research output — requires Architect validation before implementation  
**Model used for research:** Claude Opus 4.6  

---

## Executive Summary

The AATIF Safety Engine currently uses bge-m3 embeddings with cosine similarity against anchor phrases to score Harm (H), Intent (I), and Emotion (E). Anchors are predominantly in Modern Standard Arabic (فصحى) and Gulf dialect (خليجي), creating blind spots for 4 underserved dialect groups: Levantine (شامي), Iraqi (عراقي), Maghrebi (مغاربي), and Sudanese/Yemeni (سوداني/يمني).

This document provides dialect-specific expressions organized by anchor type for each group. Academic research confirms this is a real gap — the ADHAR corpus (2024), Typica.ai Darija benchmark (2025), and CDT Maghreb moderation report (2024) all document how dialect variation causes both missed detections and false positives in Arabic content moderation.

### Confidence Framework

Each expression is marked with a confidence level:
- **HIGH** — Well-documented in academic literature, verified across multiple sources, or part of widely-known dialect vocabulary
- **MEDIUM** — Consistent with dialect patterns and attested in at least one source, but less thoroughly documented
- **LOW** — Based on general dialect knowledge; needs native speaker validation before use as anchor

---

## 1. شامي (Levantine) — Syria, Lebanon, Jordan, Palestine

### Current Coverage Assessment
Partial coverage exists through MSA anchors that overlap with formal Levantine. The main gaps are in colloquial Levantine expressions that use completely different vocabulary from MSA/Gulf, particularly street slang from urban centers (Damascus, Beirut, Amman).

### 1.1 Harm Anchors (expressions of threat, violence, harm)

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | بدي فرجيك | biddi farjīk | I want to show you | I'll teach you a lesson / I'll get you | H, I | harm-anchor | HIGH |
| 2 | لح دبحك | laḥ adbḥak | I will slaughter you | I will beat you badly / serious threat | H | harm-anchor | HIGH |
| 3 | بدي كسّر راسك | biddi kassir rāsak | I want to break your head | Threat of physical violence | H | harm-anchor | HIGH |
| 4 | يا زعران | yā za'rān | O thugs | Strong insult — "thugs/hooligans" (Lebanese-specific weight) | H | harm-anchor | HIGH |
| 5 | بدي إقبرك | biddi iʾburak | I want to bury you | Death threat / extreme threat | H | harm-anchor | MEDIUM |
| 6 | لح فقعك | laḥ faʾʿak | I will pop you | I will hit you hard | H | harm-anchor | MEDIUM |
| 7 | قطّعلي نياطي | ʾaṭṭaʿ-li nyāṭī | Cut my heartstrings | You're killing me (distress) — but can express frustration leading to confrontation | H, E | harm-anchor | MEDIUM |
| 8 | بدي شلحك | biddi shalḥak | I want to strip you | I will humiliate/expose you — threat of social harm | H, I | harm-anchor | MEDIUM |
| 9 | يا ابن الشرموطة | yā ibn il-sharmūṭa | son of a [slur] | Severe gendered insult, often precedes violence | H | harm-anchor | HIGH |
| 10 | منقبرك | min'ubruk | We will bury you | Collective death threat | H | harm-anchor | MEDIUM |

### 1.2 Safe Anchors (benign hyperbole / idioms that sound harmful)

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | الله يقبرني | Allāh yiʾburnī | May God bury me (before you) | Expression of deep love — "I'd die before you" | E | safe-anchor | HIGH |
| 2 | تقبرني | tiʾburnī | You bury me | Term of extreme endearment — "I love you so much I'd die first" | E | safe-anchor | HIGH |
| 3 | يي شو حلو ميتني فيه | yī shu ḥilw mayyitnī fīh | Oh how beautiful, he's killed me with it | Expression of admiration / delight | E | safe-anchor | MEDIUM |
| 4 | روحي فداك | rūḥī fadāk | My soul is your ransom | Deep expression of love/loyalty | E | safe-anchor | HIGH |
| 5 | بموت فيك | bmūt fīk | I die in you | I adore you / I love you intensely | E | safe-anchor | HIGH |
| 6 | قتلتيني من الضحك | ʾataltīnī min il-ḍiḥk | You killed me from laughter | You made me laugh so hard | E | safe-anchor | HIGH |
| 7 | ياخد العقل | yākhud il-ʿaʾl | It takes the mind | It's amazing / mind-blowing (not a threat) | E | safe-anchor | MEDIUM |
| 8 | يلعن أبو هالشغلة | yilʿan abū hal-shughle | Curse the father of this work | Expression of frustration with a task (not a real curse at a person) | E | safe-anchor | HIGH |

### 1.3 Emotion Anchors (distress, crisis, emotional pain)

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | مخنوق | makhنūq | Strangled/choked | Feeling suffocated / overwhelmed / can't breathe from stress | E | emotion-anchor | HIGH |
| 2 | ما عاد بقدر | mā ʿād biʾdar | I can't anymore | Expression of burnout / giving up | E | emotion-anchor | HIGH |
| 3 | نفسيتي تعبانة | nafsiyyatī taʿbāne | My psyche is tired | I'm mentally/emotionally exhausted | E | emotion-anchor | HIGH |
| 4 | حاسس حالي ضايع | ḥāsis ḥālī ḍāyiʿ | I feel myself lost | I feel lost / directionless | E | emotion-anchor | HIGH |
| 5 | مش قادر كمّل | mish ʾādir kammil | I can't continue | I can't go on (potential crisis signal) | E | emotion-anchor | HIGH |
| 6 | بدي موت | biddī mūt | I want to die | Could be literal suicidal ideation OR hyperbolic frustration — context critical | E, H | emotion-anchor | HIGH |
| 7 | خلص تعبت | khalaṣ tiʿibt | Enough, I'm tired | Exhaustion / giving up signal | E | emotion-anchor | HIGH |
| 8 | حاسس إني لحالي | ḥāsis innī la-ḥālī | I feel I'm alone | Feeling of isolation | E | emotion-anchor | MEDIUM |

### 1.4 Evasion Risks

- **Code-switching with French (Lebanese):** Lebanese speakers frequently mix French words into Arabic text. Harmful content could be split across languages to evade monolingual detectors.
- **"Za'ran" regional weight:** The term زعران carries different severity across Levantine sub-dialects — strong insult in Lebanon, milder in Jordan. Fixed anchors may over- or under-weight.
- **Sarcasm prevalence:** Levantine Arabic (especially Lebanese/Syrian) is known for heavy sarcasm. Research confirms models struggle with sarcastic harmful content — e.g., praising someone sarcastically while actually threatening them.

---

## 2. عراقي (Iraqi) — Iraq

### Current Coverage Assessment
Weak coverage. Iraqi Arabic is heavily influenced by Persian, Turkish, Kurdish, and Aramaic, producing vocabulary that is often completely opaque to MSA/Gulf-trained systems. Many everyday Iraqi words have no MSA equivalent.

### 2.1 Harm Anchors

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | أريد أچفخك | arīd achafkhak | I want to slap you | Threat of physical violence — "چفخ" (chafakh) is Iraqi-specific for a hard slap | H | harm-anchor | MEDIUM |
| 2 | يا غشيم | yā ghashīm | O naive one | Strong insult — "you're stupid/incompetent" | H | harm-anchor | HIGH |
| 3 | أگص رگبتك | agaṣṣ rugubtak | I'll cut your neck | Death threat — uses Iraqi verb form | H | harm-anchor | MEDIUM |
| 4 | أطگّك | aṭuggak | I'll shoot you | Threat with firearm — "طگ" (ṭagg) = to shoot (Iraqi-specific) | H | harm-anchor | HIGH |
| 5 | يا سافل | yā sāfil | O lowly one | Strong character insult | H | harm-anchor | HIGH |
| 6 | أريد أنطيك گصّة | arīd anṭīk gaṣṣa | I want to give you a punch | Threat of punching — uses "گ" (g) phoneme unique to Iraqi | H | harm-anchor | MEDIUM |
| 7 | أكسر چاعك | aksir chāʿak | I'll break your jaw | Threat of facial violence — "چاع" = jaw (Iraqi) | H | harm-anchor | MEDIUM |
| 8 | يا قرطع | yā garṭaʿ | O [derogatory] | Strong derogatory term for someone despicable | H | harm-anchor | MEDIUM |
| 9 | يا معرّص | yā mʿarraṣ | O pimp | Severe honor-based insult — one of the strongest in Iraqi dialect | H | harm-anchor | HIGH |
| 10 | خوش دلّه | khōsh dalla | Good teapot | Sarcastic insult — calling someone stupid/empty | H | harm-anchor | LOW |

### 2.2 Safe Anchors (benign hyperbole / idioms)

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | روحي إلك | rūḥī ilak | My soul is for you | Deep expression of love / loyalty | E | safe-anchor | HIGH |
| 2 | أموت بيك | amūt bīk | I die in you | I love you deeply (romantic/familial) | E | safe-anchor | HIGH |
| 3 | گتلتني ضحك | gitaltinī ḍiḥk | You killed me with laughter | You made me laugh so hard | E | safe-anchor | HIGH |
| 4 | عيوني إلك | ʿyūnī ilak | My eyes are for you | I'll do anything for you — expression of devotion | E | safe-anchor | HIGH |
| 5 | يخبل | yakhbil | It drives crazy | It's amazing / incredible (positive) | E | safe-anchor | MEDIUM |
| 6 | طگيتني من الضحك | ṭagaytinī min il-ḍiḥk | You shot me from laughter | Same as "killed me laughing" but using Iraqi "ṭagg" (shoot) | E | safe-anchor | MEDIUM |
| 7 | والله أدوسلك | wallāh adūsilak | By God I'll step on [something] for you | I'll do anything for you (sacrifice) | E | safe-anchor | LOW |

### 2.3 Emotion Anchors

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | مخنوگ | makhnūg | Strangled/choked | Feeling suffocated / overwhelmed (same meaning as Levantine, Iraqi pronunciation) | E | emotion-anchor | HIGH |
| 2 | گلبي يوجعني | galbī yūjaʿnī | My heart hurts me | Emotional/psychological pain | E | emotion-anchor | HIGH |
| 3 | ما أگدر أعيش | mā agdar aʿīsh | I can't live | Severe distress — potential crisis signal | E, H | emotion-anchor | HIGH |
| 4 | تعبت من الدنيا | taʿabt min il-dunyā | I'm tired of the world | Exhaustion with life — potential crisis signal | E | emotion-anchor | HIGH |
| 5 | حاسس بضيگ | ḥāsis bi-ḍīg | I feel constriction | Feeling of anxiety / suffocation | E | emotion-anchor | MEDIUM |
| 6 | ماكو فايدة | māku fāyda | There's no benefit/use | Hopelessness — "ماكو" is distinctly Iraqi for "there isn't" | E | emotion-anchor | HIGH |
| 7 | ماريد حد | mārīd ḥad | I don't want anyone | Social withdrawal / isolation signal | E | emotion-anchor | MEDIUM |

### 2.4 Evasion Risks

- **The "گ" (g) phoneme:** Iraqi Arabic uses گ extensively where other dialects use ق (q) or ك (k). The word "أطگّك" (I'll shoot you) uses a letter that doesn't exist in MSA keyboards, and embeddings trained primarily on MSA may not represent it well.
- **Persian/Turkish loanwords for weapons:** Iraqi dialect uses some Persian/Turkish-origin words for weapons, tools of violence, and drugs that have zero overlap with MSA vocabulary. These create direct evasion paths.
- **"ماكو/آكو" (māku/āku):** The Iraqi negation/existence words are completely different from MSA (ليس/يوجد) and Gulf (ما في/في). Any anchor using these particles to negate harm ("ماكو خطر" = there's no danger) would be invisible to MSA-based pattern matching.
- **Sectarian vocabulary:** Iraq's sectarian landscape produces coded language that carries threat in context but appears neutral in isolation. This is extremely context-dependent and hard to anchor.

---

## 3. مغاربي (Maghrebi) — Morocco, Algeria, Tunisia, Libya, Mauritania

### Current Coverage Assessment
Near-zero coverage. Maghrebi Arabic (especially Moroccan Darija and Algerian Darja) is the most divergent dialect group from MSA. It incorporates heavy French and Amazigh (Berber) influence, uses completely different verb conjugations, and has vocabulary that is mutually unintelligible with Eastern Arabic. Research confirms this is the hardest dialect for Arabic NLP — the Typica.ai benchmark (2025) showed that OpenAI, Mistral, and Anthropic moderation APIs all performed poorly on Darija toxicity compared to a culturally-tuned model.

**Note: The Architect speaks Moroccan Darija and will personally validate all entries in this section.**

### 3.1 Harm Anchors

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | نقتلك | nqatlak | I kill you | Threat — uses Darija "n-" first person prefix instead of MSA "أ-" | H | harm-anchor | HIGH |
| 2 | سير تقود | sīr tgūd | Go get led | Go get lost / strong dismissal (Moroccan) | H | harm-anchor | MEDIUM |
| 3 | نضربك | nḍarbak | I hit you | Threat of hitting — Darija conjugation | H | harm-anchor | HIGH |
| 4 | يا ولد القحبة | yā wuld il-qaḥba | O son of a [slur] | Severe gendered insult (pan-Maghrebi) | H | harm-anchor | HIGH |
| 5 | نحرگك | nḥargak | I burn you | Threat — to burn someone | H | harm-anchor | HIGH |
| 6 | زعّاطة | zaʿʿāṭa | worthless trash | Strong derogatory term for a person (Moroccan) | H | harm-anchor | MEDIUM |
| 7 | مقود | magwūd | led (passive) | Very strong insult — implies being a cuckold/pimp (Moroccan) | H | harm-anchor | HIGH |
| 8 | قحبة | qaḥba | prostitute | Strong gendered slur (pan-Maghrebi, same word but higher frequency in Darija) | H | harm-anchor | HIGH |
| 9 | نخليك تندم | nkhallīk tandim | I'll make you regret | Threatening consequence | H, I | harm-anchor | MEDIUM |
| 10 | غادي نخلّع عليك | ghādī nkhallaʿ ʿlīk | I'm going to terrify you | Threat of intimidation/violence (Moroccan) | H | harm-anchor | MEDIUM |
| 11 | يا حشايشي | yā ḥashāyshī | O hashish-user | Drug-related insult (Moroccan) | H | harm-anchor | MEDIUM |
| 12 | نفرّع فيك | nfarraʿ fīk | I'll empty into you | Threat of extreme violence (Algerian) | H | harm-anchor | MEDIUM |
| 13 | ربي ياخذك | rabbī yākhdhak | May God take you | Death wish — "May God take your life" (Tunisian) | H | harm-anchor | HIGH |
| 14 | يا كلب | yā kalb | O dog | Strong insult (pan-Arabic but extremely common in Maghrebi context) | H | harm-anchor | HIGH |

### 3.2 Safe Anchors (benign hyperbole / idioms)

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | يا ساتر | yā sātir | O Concealer (God) | Expression of surprise/shock — not a threat | E | safe-anchor | HIGH |
| 2 | ضربني الحال | ḍarbnī il-ḥāl | The situation hit me | I'm broke / things are tough (financial, not physical) | E | safe-anchor | HIGH |
| 3 | ماتني بالضحك | mātnī bil-ḍḥak | She killed me with laughter | Made me laugh so hard (Moroccan feminine form) | E | safe-anchor | MEDIUM |
| 4 | الله يرحم الوالدين | Allāh yarḥam il-wāldīn | May God have mercy on the parents | Please / I'm begging you (Moroccan — NOT a death reference) | E | safe-anchor | HIGH |
| 5 | حرگني | ḥragnī | He burned me | He outsmarted me / got me good (positive surprise) | E | safe-anchor | MEDIUM |
| 6 | قتلني بالنعاس | qtalnī bil-nʿās | Killed me with sleepiness | I'm extremely tired (not violence) | E | safe-anchor | MEDIUM |
| 7 | والله حاجة خايبة | wallāh ḥāja khāyba | By God, a bad thing | That's terrible! (expression of disappointment, not threat) | E | safe-anchor | MEDIUM |

### 3.3 Emotion Anchors

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | مقلّق | mʾallaʾ | Worried/anxious | Feeling anxious — Darija form | E | emotion-anchor | HIGH |
| 2 | مكتئب | muktaʾib | Depressed | Depressed — this is MSA but frequently used in Maghrebi | E | emotion-anchor | HIGH |
| 3 | ضاق بيّا الحال | ḍāq biyyā il-ḥāl | The situation tightened on me | I'm in a desperate state | E | emotion-anchor | HIGH |
| 4 | ما بقيت نقدر | mā bqīt nqdar | I no longer can | I can't take it anymore — Darija form of giving up | E | emotion-anchor | HIGH |
| 5 | بغيت نموت | bghīt nmūt | I wanted to die | Could be hyperbolic frustration OR literal suicidal ideation | E, H | emotion-anchor | HIGH |
| 6 | راسي غادي يطيح | rāsī ghādī yṭīḥ | My head is going to fall | I'm overwhelmed / extreme stress | E | emotion-anchor | MEDIUM |
| 7 | ما عندي مع من نهدر | mā ʿandī mʿa man nhdar | I have no one to talk to | Social isolation signal (Algerian/Moroccan) | E | emotion-anchor | MEDIUM |
| 8 | مللت من هاد العيشة | mallīt min hād il-ʿīsha | I'm bored/fed up with this life | Could signal suicidal ideation in context | E, H | emotion-anchor | HIGH |
| 9 | كرهت حياتي | karhat ḥyātī | I hated my life | Strong distress signal | E | emotion-anchor | HIGH |

### 3.4 Evasion Risks — CRITICAL

Maghrebi Arabic presents the **highest evasion risk** of all dialect groups for MSA-based safety systems:

- **Mutual unintelligibility:** Maghrebi Darija is essentially a different language from MSA/Gulf Arabic. Many words have zero lexical overlap. A Moroccan speaker could express harm using words that an MSA-trained embedding model treats as out-of-vocabulary noise.
- **French code-switching:** Maghrebi speakers routinely mix French into Arabic — "je vais te tuer" (I'll kill you) embedded in Arabic text would bypass Arabic-only detection. The CDT report (2024) specifically flags this as a moderation gap.
- **Arabizi prevalence:** Writing Arabic in Latin characters (e.g., "n9tlk" for نقتلك) is extremely common in Maghrebi social media. The Typica.ai benchmark confirms moderation APIs fail on Arabizi.
- **Amazigh (Berber) vocabulary:** Some Maghrebi speakers use Amazigh words for sensitive concepts that have zero representation in Arabic NLP training data.
- **Drug terminology:** Moroccan dialect has specific terms for drugs (e.g., "الكيف" / l-kīf for cannabis, "القرقوبي" / l-garʾūbī for Rivotril/psychotropic pills, "الماحيا" / l-māḥya for local alcohol) that differ from MSA equivalents and would be invisible to MSA-trained detectors.
- **Implicit insults and sarcasm:** The Typica.ai benchmark specifically notes that "indirect insults, sarcasm, and euphemisms that general-purpose models frequently overlook" are a major gap in Darija moderation.

---

## 4. سوداني/يمني (Sudanese/Yemeni) — Sudan, Yemen

### Current Coverage Assessment
Weak coverage. Sudanese Arabic is influenced by Nubian, Beja, and other African languages, creating vocabulary invisible to MSA systems. Yemeni Arabic is conservative (closer to classical Arabic in some ways) but has unique colloquialisms, especially in Aden and Hadhrami sub-dialects. Both are significantly under-resourced in NLP — the Lisan corpus has only ~50K tokens for Sudanese.

### 4.1 Harm Anchors

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | يا زول أنا بقطعك | yā zōl anā baʾṭaʿak | O person I will cut you | Threat of violence — "زول" (zōl) is uniquely Sudanese for "person" | H | harm-anchor | HIGH |
| 2 | يا خاين | yā khāyin | O traitor | Strong accusation — carries extreme weight in tribal/honor context | H | harm-anchor | HIGH |
| 3 | بشيلك من الوجود | bashīlak min il-wujūd | I'll remove you from existence | Death threat — Sudanese phrasing | H | harm-anchor | MEDIUM |
| 4 | يا حيوان | yā ḥayawān | O animal | Dehumanizing insult | H | harm-anchor | HIGH |
| 5 | أحشّك | aḥashshak | I'll slash/cut you | Threat of cutting — Yemeni dialect | H | harm-anchor | MEDIUM |
| 6 | يا مسخرة | yā maskhara | O joke/mockery | Strong insult — calling someone ridiculous/worthless | H | harm-anchor | MEDIUM |
| 7 | والله لأجيبلك الجنبية | wallāh la-ajīb-lak il-janbiyya | By God I'll bring you the dagger | Weapon threat — "جنبية" (janbiyya) is the Yemeni curved dagger | H | harm-anchor | MEDIUM |
| 8 | أنت ما زول | inta mā zōl | You are not a person | Dehumanization — using Sudanese "زول" | H | harm-anchor | MEDIUM |

### 4.2 Safe Anchors (benign hyperbole / idioms)

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | يا زول | yā zōl | O person/fellow | Friendly address — like "dude/mate" (Sudanese) | E | safe-anchor | HIGH |
| 2 | شديد | shadīd | Severe/strong | Very / a lot — intensifier, NOT indicating violence (Sudanese) | E | safe-anchor | HIGH |
| 3 | دغري | dughrī | Straight/direct | Honestly / frankly — not aggressive despite directness | E | safe-anchor | HIGH |
| 4 | جابوها ساي | jābūhā sāy | They brought it just like that | It happened casually / easily — Sudanese idiom | E | safe-anchor | MEDIUM |
| 5 | قلبي طار | galbī ṭār | My heart flew | I was startled / excited (not a medical emergency) | E | safe-anchor | HIGH |
| 6 | والله ما عرفت وين حطّ راسي | wallāh mā ʿaraft wēn ḥaṭṭ rāsī | By God I didn't know where to put my head | I was so embarrassed (not self-harm) | E | safe-anchor | MEDIUM |

### 4.3 Emotion Anchors

| # | Expression | Transliteration | Literal Meaning | Actual Meaning | Scorer | Anchor Type | Confidence |
|---|-----------|----------------|----------------|---------------|--------|-------------|------------|
| 1 | نفسي تعبانة شديد | nafsī taʿbāna shadīd | My psyche is very tired | Severe emotional exhaustion (Sudanese — uses "شديد" as intensifier) | E | emotion-anchor | HIGH |
| 2 | ما عندي زول | mā ʿindī zōl | I have no person/one | I'm alone / isolated (Sudanese) | E | emotion-anchor | HIGH |
| 3 | الدنيا ضيقة عليّ | il-dunyā ḍayyiqa ʿalayya | The world is tight on me | Feeling suffocated / trapped | E | emotion-anchor | HIGH |
| 4 | تعبت من العيشة | taʿabt min il-ʿīsha | I'm tired of living | Potential crisis signal — same meaning across dialects but this Sudanese phrasing may be missed | E, H | emotion-anchor | HIGH |
| 5 | ما فيش فايدة | mā fīsh fāyda | There's no use | Hopelessness signal (Yemeni form) | E | emotion-anchor | MEDIUM |
| 6 | قلبي مكسور | galbī maksūr | My heart is broken | Heartbreak / deep sadness — uses Sudanese "g" pronunciation of "ق" | E | emotion-anchor | HIGH |
| 7 | ما أقدر أتحمّل | mā aqdar atḥammal | I can't bear it | Reaching breaking point (Yemeni phrasing) | E | emotion-anchor | MEDIUM |

### 4.4 Evasion Risks

- **Nubian/African language vocabulary:** Sudanese Arabic incorporates Nubian, Beja, and Fur language words that are completely outside Arabic NLP vocabulary. Harmful concepts expressed with these loanwords would be invisible to any Arabic-trained model.
- **"زول" (zōl) masking:** Sudanese uses "زول" where other dialects use "شخص" or "واحد." Any person-referencing anchor (e.g., "I'll hurt that person") would miss the Sudanese equivalent.
- **Janbiyya (جنبية) cultural context:** The Yemeni dagger is both a cultural symbol and a weapon. Mentions need context — wearing one is cultural, threatening with one is violence. Simple keyword matching would cause false positives.
- **Tribal/clan vocabulary:** Both Sudanese and Yemeni speech use tribal identifiers that can carry implicit threat or honor-based violence signals when combined with other words, but are neutral in isolation.
- **Yemeni conservatism masking:** Yemeni Arabic is closer to MSA than other dialects, but the places where it diverges (specific verbs of violence, emotional expressions) are precisely the blind spots — the system would "think" it has good coverage because most Yemeni text looks like MSA, but miss the critical dialect-specific expressions.

---

## 5. Cross-Dialect Evasion Patterns

### 5.1 Arabizi (Latin-script Arabic)

Writing Arabic in Latin characters with numbers replacing Arabic-only sounds (e.g., 3=ع, 7=ح, 9=ق, 5=خ, 2=ء) is common across ALL dialect groups but especially prevalent in Maghrebi contexts. Examples:

- "n9tlk" = نقتلك (I'll kill you)
- "ya 7mar" = يا حمار (you donkey)
- "bdi farjik" = بدي فرجيك (I'll show you / I'll teach you a lesson)

**Impact on AATIF:** bge-m3 embeddings are trained on Arabic script. Arabizi text will produce completely different embedding vectors, making cosine similarity with Arabic-script anchors useless. This is a **systematic bypass** vulnerability.

### 5.2 Emoji-based Evasion

The CDT Maghreb report documents emoji substitution (e.g., 🍉 for Palestinian flag/solidarity, 🔪 as threat intensifier) as an active evasion tactic. The AATIF embedding approach is text-only and would miss emoji-encoded threats entirely.

### 5.3 Letter Manipulation (Algospeak)

Research on "lexical algorithmic resistance" documents Arabic-specific evasion tactics:
- Removing dots from letters (changing meaning)
- Substituting letters with numbers
- Inserting zero-width characters
- Combining innocuous content with sensitive material

### 5.4 Dialect-Switching Evasion

A speaker could deliberately use Maghrebi vocabulary for harmful words while writing the rest of the sentence in Gulf/MSA Arabic. The embedding would be pulled toward the "safe" MSA context while the harmful Maghrebi word goes undetected.

---

## 6. Academic Resources and Datasets

### 6.1 Key Datasets for Anchor Validation

| Dataset | Year | Dialects Covered | Size | Relevance |
|---------|------|-----------------|------|-----------|
| ADHAR | 2024 | MSA, Egyptian, Levantine, Gulf, Maghrebi | 4,240 tweets | Multi-dialectal hate speech with category labels |
| OMCD / Typica.ai Mix | 2025 | Moroccan Darija | Large (benchmark set) | Darija-specific toxicity with sarcasm/implicit insults |
| Lisan | 2022 | Yemeni, Iraqi, Libyan, Sudanese | ~1.2M tokens total | Morphologically annotated — useful for vocabulary extraction |
| SOD (Saudi Dialect) | 2024 | Saudi Gulf | 24,000+ tweets | Saudi-specific — useful baseline comparison |
| AraSafe | 2025 | Multiple | Benchmark | Arabic LLM safety benchmark |

### 6.2 Key Papers

1. **"Hate speech detection with ADHAR: a multi-dialectal hate speech corpus in Arabic"** — Frontiers in AI, 2024. First balanced multi-dialectal Arabic hate speech corpus. Covers nationality, religion, ethnicity, and race categories across 5 dialect groups.

2. **"A Comparative Benchmark of a Moroccan Darija Toxicity Detection Model (Typica.ai)"** — arXiv, 2025. Demonstrates that Darija-specific models significantly outperform general-purpose moderation APIs (OpenAI, Mistral, Anthropic) on culturally embedded toxicity.

3. **"Navigating Dialectal Bias and Ethical Complexities in Levantine Arabic Hate Speech Detection"** — arXiv, 2024. Documents how dialect-specific expressions like "za'ran" carry different weights across Levantine sub-dialects.

4. **"Moderating Maghrebi Arabic Content on Social Media"** — CDT Report, 2024. Documents content moderation failures specific to Maghrebi Arabic, including code-switching, Arabizi, and algospeak evasion tactics.

5. **"Lexical Algorithmic Resistance"** — Cambridge, 2024. Defines the concept of deliberate linguistic manipulation to bypass Arabic content moderation — directly relevant to evasion risk assessment.

6. **"Lisan: Yemeni, Iraqi, Libyan, and Sudanese Arabic Dialect Corpora with Morphological Annotations"** — 2022. Only available morphologically annotated corpus for the most under-resourced Arabic dialects.

7. **"Adversarial Evaluation of Large Language Models for Building Robust Offensive Language Detection in Moroccan Arabic"** — BDCC, 2026. Tests LLMs adversarially on Moroccan Arabic offensive language.

### 6.3 Open-Source Tools and Repos

- **Typica.ai Darija Toxicity Benchmark:** [github.com/assoudi-typica-ai/darija-toxicity-benchmark](https://github.com/assoudi-typica-ai/darija-toxicity-benchmark) — Reproducible benchmark for Darija toxicity detection
- **ADHAR Corpus:** Available through Frontiers supplementary materials
- **Darija Open Dataset v2:** General Darija NLP dataset (not safety-specific but useful for vocabulary)
- **Atlas-Chat:** Moroccan Darija LLM adapter — could inform dialect-specific embedding behavior

---

## 7. Recommendations for Implementation Priority

### 7.1 Priority Order for Anchor Expansion

1. **مغاربي (Maghrebi) — HIGHEST PRIORITY.** Near-zero current coverage, highest evasion risk due to mutual unintelligibility, largest population gap (~100M speakers). The Architect can personally validate Moroccan entries. Start with Moroccan Darija, then expand to Algerian/Tunisian.

2. **عراقي (Iraqi) — HIGH PRIORITY.** Weak coverage, unique phonemes (گ/چ) that may confuse embeddings, Persian/Turkish loanwords create blind spots. ~40M speakers.

3. **شامي (Levantine) — MEDIUM PRIORITY.** Partial existing coverage, but sarcasm and code-switching gaps are real. Some anchors may already be caught by MSA overlap. ~30M speakers.

4. **سوداني/يمني (Sudanese/Yemeni) — MEDIUM PRIORITY.** Weak coverage, Nubian vocabulary gap is real but smaller speaker population in typical AATIF deployment contexts. ~50M speakers combined but lower digital presence.

### 7.2 Recommended Validation Process

1. **Architect validates Maghrebi section** — mark corrections, add missing expressions, flag wrong entries
2. **Embedding similarity test** — run each proposed anchor through bge-m3 and check cosine similarity against existing anchors. If similarity > 0.7, the expression is already partially covered. Focus on expressions with similarity < 0.5.
3. **False positive audit** — test safe-anchors against harm-anchors to ensure they create proper separation in embedding space
4. **Native speaker review** — for Iraqi, Levantine, and Sudanese/Yemeni, recruit native speakers for validation (the Architect has contacts who may help)

### 7.3 Arabizi Strategy

The Arabizi bypass is systematic and affects all dialects. Two possible approaches:
- **Pre-processing normalization:** Convert Arabizi to Arabic script before embedding (models like ArzEn-LLM exist for Egyptian; Darija-specific transliteration models are emerging per the 2025 research)
- **Dual anchors:** Maintain both Arabic-script and Arabizi versions of critical harm anchors (doubles anchor count but provides direct coverage)

---

## 8. Confidence Summary

| Dialect | Harm Anchors | Safe Anchors | Emotion Anchors | Overall Confidence |
|---------|-------------|-------------|----------------|-------------------|
| شامي (Levantine) | HIGH | HIGH | HIGH | **HIGH** — well-documented dialect, strong academic coverage |
| عراقي (Iraqi) | MEDIUM | HIGH | MEDIUM-HIGH | **MEDIUM** — unique vocabulary documented but less NLP research |
| مغاربي (Maghrebi) | MEDIUM-HIGH | MEDIUM | HIGH | **MEDIUM** — needs Architect validation, strong academic backing |
| سوداني/يمني (Sudanese/Yemeni) | MEDIUM | MEDIUM | MEDIUM | **MEDIUM-LOW** — least-resourced dialects, sparse documentation |

---

## Appendix A: Phoneme Mapping for Non-Standard Characters

Iraqi and some Maghrebi dialects use characters not present in standard MSA keyboard layouts:

| Character | IPA | Dialect | MSA Equivalent | Notes |
|-----------|-----|---------|----------------|-------|
| گ | /ɡ/ | Iraqi | ق /q/ or ك /k/ | Hard G — very common in Iraqi |
| چ | /tʃ/ | Iraqi | ج /dʒ/ or ش /ʃ/ | CH sound — Persian influence |
| پ | /p/ | Iraqi (loanwords) | ب /b/ | P sound — Persian/Kurdish loanwords |
| ڤ | /v/ | Maghrebi (French loans) | ف /f/ | V sound — French loanwords |

**Impact on embeddings:** If bge-m3 was not trained with significant Iraqi/Maghrebi text containing these characters, the character-level encoding may be suboptimal, reducing the quality of embedding similarity matches.

---

*This document is research output. No expressions should be added to the anchor system without native speaker validation and embedding similarity testing. The Architect will review the Maghrebi section personally.*
