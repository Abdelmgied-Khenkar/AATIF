# FN#042 — Unwritten Concept Nullification Law (UCN)
# تصميم المكوّن: قانون إبطال المفهوم غير المكتوب

**الحالة:** تصميم جاهز للمراجعة
**التاريخ:** 2026-07-02
**المعمار:** Abdulmjeed Ibrahim Khenkar
**المنفّذ:** Claude (Anthropic)

---

## ملاحظة: الكود موجود بالفعل

هذا الملف يوثّق التصميم الذي بُني عليه الكود الحالي (`aatif_ucn_validator.py`) ويحدّد الفلسفة والهندسة والاختبارات بشكل مرجعي. الكود قائم ومُختبَر (اجتاز مراجعة 3 نماذج).

---

## 1. الفلسفة — لماذا هذا المكوّن موجود

### المبدأ الأساسي

> "لو ما كُتب في النظام، ما وُجد في النظام."
> "If it is not written in the system, it does not exist in the system."

### الحاجة

الـ LLM بطبيعته يُكمّل الفراغات. لو وصفت له نظام يحتوي "محرك رحمة" و"محرك منطق"، قد يستنتج وجود "محرك تعاطف" لأن المنطق يقول ذلك. هذا استنتاج غير مُرخَّص ينتج بنية وهمية (phantom architecture).

الأبحاث توثّق أن الـ LLMs تخترع بنى غير موجودة بمعدلات 5%-46% (Spracklen et al., USENIX Security 2025; Krishna et al., ICML 2024).

### الربط بالفطرة والتربية

هذا القانون هو تطبيق لمبدأ **الأمانة البنيوية** — النظام لا يكذب على نفسه. في التربية الإنسانية، أخطر كذب هو الكذب على النفس: أن تعتقد أنك تملك ما لا تملكه. UCN يمنع النظام من هذا الوهم البنيوي.

المبدأ الفلسفي: **"إذا عُرِف السبب بطل العجب"** — النظام يعرف بالضبط ما يملكه، ولا يتعجب من غياب ما لم يُبنَ أصلاً. الجهل المعترف به أفضل من المعرفة الموهومة.

### الفرق الحاسم: معرفة عامة vs بنية ذاتية

UCN **لا ينطبق** على المعرفة العامة:
- "الرحمة مهمة في العلاقات الإنسانية" = مسموح (معرفة عامة)
- "عاطف يحتوي محرك رحمة" = مخالفة (اختراع بنيوي)

هذا الفرق هو جوهر التصميم — Closed-World Assumption (Reiter, 1978) يُطبّق على **بنية النظام فقط**، لا على معرفته بالعالم.

---

## 2. المكان في النظام — أين يعمل في خط الأنابيب

### الموقع: POST_OUTPUT (بعد إخراج الـ LLM)

```
User message
    → S(d) scoring
    → P(d) protocols
    → R(d) style
    → governed prompt → LLM
    → ★ UCN validator (POST_OUTPUT) ← هنا
    → Output Gate
    → User
```

### السبب

UCN يفحص **مخرجات الـ LLM** — لا مدخلات المستخدم. المستخدم لا يحتاج أن يعرف بنية النظام؛ لكن الـ LLM حين يجيب قد يخترع مكونات وهمية. UCN يكشف هذا الاختراع قبل أن يصل للمستخدم.

### الربط بالسجل (Observer Registry)

```python
# في aatif_observer_registry.py — المكان 11
def _make_ucn_observer() -> Optional[Observer]:
    class UCNObserver(Observer):
        name = "ucn_validator"
        phase = ObserverPhase.POST_OUTPUT  # بعد إخراج LLM
        CAN_BLOCK_RUNTIME = False
```

UCN مسجّل كمراقب POST_OUTPUT في السجل. يعمل بعد مراقب LBH (كاشف التلفيق الحامل) وقبل بوابة الإخراج.

---

## 3. الهدف — ماذا يكشف ويمنع

### خمسة أنواع من الأشباح (Phantom Types)

| النوع | المثال (EN) | المثال (AR) |
|-------|------------|------------|
| PHANTOM_ENGINE | "AATIF has a compassion engine" | "عاطف يحتوي محرك تعاطف" |
| PHANTOM_LAYER | "Layer 25 handles emotions" | "الطبقة ٢٥ تعالج المشاعر" |
| PHANTOM_PROTOCOL | "The forgiveness protocol" | "بروتوكول المسامحة" |
| PHANTOM_CHANNEL | "B9 handles authentication" | "القناة B9 للمصادقة" |
| PHANTOM_CONCEPT | "AATIF's karma tracking" | "تتبع الكارما في عاطف" |

### ما يُمنع

1. افتراض طبقات غير مكتوبة
2. استنتاج بروتوكولات من السياق
3. اختراع محركات بناءً على المنطق وحده
4. ادعاء وجود قنوات ربط خارج B1-B8
5. نسبة مفاهيم غير موثّقة لبنية عاطف

### ما يبقى مسموحاً

1. الإجابة على أسئلة المستخدم العامة
2. استخدام المعرفة العامة عن أي موضوع
3. اقتراح مكونات جديدة (بتصنيف PROPOSED لا ASSERTED)
4. الإشارة لمكونات موجودة فعلاً في السجل

---

## 4. الربط بالمعادلات

### العلاقة بـ S(d), H, θ

**لا يوجد ربط مباشر.** هذا قرار تصميمي جوهري:

> UCN هو **سلامة بنيوية** (architectural integrity)، ليس **أماناً** (safety).
> "AATIF has a compassion engine" ليس خطيراً — لكنه كذب بنيوي.

UCN لا يستورد ولا يعدّل:
- S equation (معادلة الحوكمة)
- H score (درجة الضرر)
- θ (عتبة الحوكمة)
- B2 (القناة الدستورية)
- B6 (قناة الأمان)

### العلاقة ببوابة الإخراج

UCN يعمل **قبل** بوابة الإخراج. أعلامه (flags) تظهر في مسار التدقيق (audit trail) — والحاكم يقرر هل يتصرف بناءً عليها. UCN يقترح تصحيحات (`candidate_not_authoritative`) ولا يفرضها.

### العلاقة بـ Meta-Oversight (المُراجع)

UCN لا يتفاعل مع المُراجع مباشرة. لكن المُراجع يمكنه قراءة أعلام UCN من مسار التدقيق وتصعيد قرار إذا كانت مخالفات UCN خطيرة.

### قنوات الربط

UCN يعمل حصرياً ضمن:
- **B3** (قناة المعنى) — يفحص المعنى البنيوي
- **B5** (قناة السلوك) — يقترح تصحيح السلوك

مؤشر العزل: `ISOLATION_MARKER = "B3_B5_ONLY_NOT_FOR_SAFETY"`

---

## 5. التوافق مع B-prime

```python
AUTHORITY_LEVEL = "B_PRIME_OBSERVATIONAL"
CAN_BLOCK_RUNTIME          = False   # لا يوقف الأنابيب
CAN_MODIFY_H               = False   # لا يعدّل الضرر
CAN_MODIFY_THETA            = False   # لا يعدّل العتبة
CAN_MODIFY_S                = False   # لا يعدّل القرار
CAN_EMIT_JUDICIAL_DECISION = False   # لا يصدر أحكاماً
```

### عقد العزل (Isolation Contract)

كل `UCNReading` يحمل `_isolation_marker` يؤكد أن القراءة لا تحتوي:
- مسار لتعديل S/H/θ
- استيراد من وحدات الأمان
- حكم قضائي

UCN **يراقب ويسجّل** — المحافظ وحده يقرر.

---

## 6. تصميم الواجهة البرمجية (API)

### السجل الديناميكي (Dynamic Registry — P0-A)

```python
def _discover_engine_files() -> FrozenSet[str]:
    """يمسح مجلد engine/ ويبني سجل ديناميكي من ملفات aatif_*.py"""

KNOWN_COMPONENTS = (
    _KNOWN_ENGINE_FILES |      # أسماء الملفات
    _KNOWN_SHORT_NAMES |       # أسماء مختصرة (EN)
    _KNOWN_ARABIC_NAMES |      # أسماء عربية (AR)
    _KNOWN_CHANNELS |          # قنوات الربط B1-B8
    _KNOWN_LAYERS |            # الطبقات 1-20
    _KNOWN_CONCEPTS            # مفاهيم معمارية
)
```

### الكاشف الرئيسي

```python
class UCNDetector:
    """كاشف Closed-World لمراجع بنية عاطف"""

    def validate(self, text: Any, domain: Optional[str] = None) -> UCNReading:
        """
        يمسح النص بحثاً عن مراجع بنيوية وهمية.

        المراحل:
        1. كشف سياق عاطف (هل النص يتكلم عن بنية النظام؟)
        2. استخراج المراجع (regex EN + AR)
        3. فحص السجل (هل المكوّن المذكور موجود؟)
        4. تسجيل النقاط (ثقة + خطورة + نمط الإشارة)

        Returns: UCNReading
        """
```

### هياكل البيانات

```python
@dataclass
class UCNViolation:
    violation_type: UCNViolationType    # نوع الشبح
    phantom_name: str                   # اسم المفهوم الوهمي
    context_snippet: str                # السياق المحيط
    confidence: float                   # [0,1] ثقة الكشف
    severity: float                     # [0,1] خطورة
    detection_confidence: float         # هل هذا مرجع بنيوي فعلاً؟
    phantom_confidence: float           # هل المكوّن المذكور غير موجود؟
    reference_mode: str                 # ASSERTED | PROPOSED | HYPOTHETICAL
    correction_status: str              # candidate_not_authoritative
    suggested_correction: str           # اقتراح أقرب مكوّن موجود

@dataclass
class UCNReading:
    phantoms_detected: List[UCNViolation]
    architecture_references_found: int
    all_references_valid: bool
    recommendations: List[str]
    evidence: List[str]
    _isolation_marker: str = ISOLATION_MARKER
```

### دالة التصحيح

```python
def recommend_correction(reading: UCNReading) -> str:
    """يبني نص توصية تصحيح عند كشف مخالفات"""

def ucn_audit_hash(reading: UCNReading) -> str:
    """SHA256 للقراءة — ضمان سلامة مسار التدقيق"""
```

---

## 7. سيناريوهات الاختبار (10+)

### اختبارات إيجابية (يجب أن يكشف)

| # | المدخل | المتوقع |
|---|--------|---------|
| 1 | "AATIF has a compassion engine that handles empathy" | PHANTOM_ENGINE: compassion engine |
| 2 | "Layer 25 handles emotion routing in AATIF" | PHANTOM_LAYER: Layer 25 (فقط 1-20) |
| 3 | "The forgiveness protocol ensures mercy in AATIF" | PHANTOM_PROTOCOL: forgiveness protocol |
| 4 | "B9 handles authentication in AATIF" | PHANTOM_CHANNEL: B9 (فقط B1-B8) |
| 5 | "AATIF has a karma engine that tracks moral balance" | PHANTOM_ENGINE: karma engine |
| 6 | "عاطف يحتوي محرك تعاطف للمشاعر" | PHANTOM_ENGINE: محرك تعاطف |
| 7 | "طبقة ٣٠ في عاطف تعالج الذكاء العاطفي" | PHANTOM_LAYER: طبقة ٣٠ |
| 8 | "بروتوكول المسامحة في النظام يسمح بتجاوز الأخطاء" | PHANTOM_PROTOCOL: بروتوكول المسامحة |

### اختبارات سلبية (يجب أن لا يكشف)

| # | المدخل | المتوقع |
|---|--------|---------|
| 9 | "AATIF has an intent engine that processes requests" | VALID: intent engine موجود |
| 10 | "The S equation calculates harm in AATIF" | VALID: S equation موجود |
| 11 | "Compassion is important in human interactions" | CLEAN: معرفة عامة، لا سياق عاطف |
| 12 | "The drift detector monitors system stability" | VALID: drift detector موجود |
| 13 | "AATIF uses sparse activation for efficiency" | VALID: sparse activation مفهوم معروف |
| 14 | "Photosynthesis converts sunlight into chemical energy" | CLEAN: لا سياق عاطف |

### اختبارات حدية

| # | المدخل | المتوقع |
|---|--------|---------|
| 15 | "We could build a compassion engine for AATIF" | PROPOSED mode: severity capped at 0.40 |
| 16 | "Hypothetically, AATIF might add a B9 channel" | HYPOTHETICAL mode: severity capped |
| 17 | "محرك النية في عاطف يعالج الطلبات" (intent engine by Arabic name) | VALID after Arabic normalization |
| 18 | "AATIF has both a compassion engine and a karma engine" | compound_bonus: ثقة أعلى لأشباح متعددة |

---

## 8. الأساس الدستوري

### المذكرة الميدانية الأصلية

- **FN#042** — The Unwritten Concept Nullification Law (UCN-06.12)
  - المصدر: `06 — Supervisor Layer V9.5`

### مذكرات مرتبطة

| المذكرة | العلاقة |
|---------|---------|
| FN#001 (Successful Failure) | إذا فشل النظام في بناء مكوّن، UCN يمنع التظاهر بوجوده |
| FN#054 (LBH) | LBH يكشف تلفيق عام، UCN يكشف تلفيق بنيوي محدد |
| FN#044 (Binding Map) | UCN يحمي سلامة خريطة الربط — لا قنوات وهمية |
| FN#023 (Behavioural Twin) | UCN يمنع ادعاء سلوكيات غير موثّقة |
| FN#082 (Reasoning Trace) | المحاجج يمكنه الإشارة لمخالفات UCN في تبريره |

### المواد الدستورية المرجعية

1. **Closed-World Assumption** (Reiter, 1978) — ما لا يُعرف أنه موجود، غير موجود
2. **Single Mind Law** — المحافظ وحده يقرر، UCN يراقب فقط
3. **B-prime Architecture** — كل مراقب يعمل بـ CAN_BLOCK_RUNTIME = False
4. **Isolation Contract** — UCN يعمل في B3+B5 فقط، لا يلمس B2+B6

---

## 9. تحسينات P0 المطبّقة

التصميم يتضمن ست تحسينات P0 من مراجعة 3-model:

| P0 | الوصف |
|----|-------|
| P0-A | سجل ديناميكي — يمسح engine/ بدلاً من قائمة ثابتة |
| P0-B | عقد عزل — كل UCNReading يحمل _isolation_marker |
| P0-C | ثقة مرتبطة بالسياق — تتطلب كلمات مفتاح عاطف |
| P0-D | تصنيف نمطي — PROPOSED vs ASSERTED vs HYPOTHETICAL |
| P0-E | اقتراحات ضبابية بعتبة 0.80 — candidate_not_authoritative |
| P0-F | تكافؤ ثنائي اللغة — أنماط عربية موسّعة + تجريد المورفولوجيا |

---

*المعمار: عبدالمجيد إبراهيم خنكر | المنفّذ: Claude (Anthropic)*
*الرخصة: BSL 1.1 (كود) | CC BY 4.0 (مذكرات)*
