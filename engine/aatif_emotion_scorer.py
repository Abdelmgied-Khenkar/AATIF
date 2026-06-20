"""
AATIF Semantic Emotion Scorer — E (emotion) estimation via embeddings
=====================================================================

Third component of the S equation:  S = sigma(w1*I + w2*E - w3*H)

  H = حرارة الكلمة (word heat / harm proximity) — surface danger
  I = النية (intent / purpose) — what the person wants to accomplish
  E = الشعور (emotion / emotional state) — what the person is FEELING

E reads the emotional state of the speaker. Not whether content is
dangerous (that's H) or what their purpose is (that's I). E reads
the FEELING behind the message.

E scale (0 to 1):
  E ~ 1.0 = positive (joy, hope, gratitude, excitement, love, relief)
  E ~ 0.7 = mild positive/calm (content, peaceful, curious, amused)
  E ~ 0.5 = neutral (no strong emotion, factual, matter-of-fact)
  E ~ 0.3 = mild negative (frustrated, tired, worried, confused, lonely)
  E ~ 0.0 = intense negative (despair, rage, terror, hopelessness)

Design notes:
  - Anchors use a mix of Gulf, Egyptian, and Levantine dialects
  - Avoids words that appear in H anchors to prevent lexical contamination
    (no "نفسي" near emotions, no "أبغى" near negative emotions)
    Lesson from the 2x4 experiment: bge-m3 matches WORDS not MEANINGS
  - Same top-K=3 + temperature=0.05 + bge-m3 architecture as H and I

Architect: Abdulmjeed Ibrahim Khenkar
"""

from __future__ import annotations
import numpy as np

USE_OLLAMA = True
OLLAMA_EMBED_MODEL = "bge-m3"

# ---------------------------------------------------------------------------
# EMOTION ANCHORS
# Each anchor = (example_text, emotion_level in 0..1).
# E = 1.0 -> positive emotions (joy, gratitude, excitement, love, relief)
# E = 0.7 -> mild positive / calm (content, peaceful, curious)
# E = 0.5 -> neutral (no strong emotion, factual)
# E = 0.3 -> mild negative (frustrated, tired, worried, lonely)
# E = 0.0 -> intense negative (despair, rage, terror, hopelessness)
#
# DIALECT KEY: G=Gulf, E=Egyptian, L=Levantine
# CONTAMINATION GUARD: no "نفسي" or "أبغى" in anchors
# ---------------------------------------------------------------------------
EMOTION_ANCHORS = [
    # --- positive emotions (E = 1.0) --- 6 anchors
    ("فرحان اليوم والحمد لله", 1.0),                          # G: happy today
    ("مبسوط من النتيجة مرررة", 1.0),                          # G/E: very pleased with result
    ("شكراً من كلّ قلبي على مساعدتك", 1.0),                   # gratitude from the heart
    ("متحمس للسفرة الجاية ما أقدر أصبر", 1.0),               # G: can't wait for the trip
    ("قلبي مليان حب لأهلي الله يخليهم", 1.0),                 # love for family
    ("ارتحت كثير لما عرفت إن كل شي تمام", 1.0),              # relief — all is well

    # --- mild positive / calm (E = 0.7) --- 5+3 anchors
    ("الحمد لله ماشي الحال وكل شي زين", 0.7),                # G: content, things are good
    ("حاسس براحة وهدوء اليوم", 0.7),                         # peaceful today
    ("مستانس أتعلم شي جديد", 0.7),                            # G: enjoying learning
    ("متفائل إن بكرا أحسن إن شاء الله", 0.7),                # optimistic about tomorrow
    ("الجو حلو وقاعد أستمتع بيومي", 0.7),                    # mild enjoyment
    # social media / marketing energy — ambitious but positive
    ("عايزين نعمل حاجة كبيرة على السوشيال ميديا", 0.7),     # want to do something big on social
    ("نبغى نطلق حملة تسويقية تفجر السوشيال", 0.7),           # launch a viral marketing campaign
    ("المنتج ده هيكسر الدنيا في المبيعات", 0.7),              # this product will crush it in sales

    # --- neutral (E = 0.5) --- 6 anchors
    ("عادي يعني مافي شي مميز", 0.5),                          # G: nothing special
    ("الطقس حار اليوم بس عادي", 0.5),                         # factual weather
    ("رحت السوق وجبت الأغراض", 0.5),                          # factual routine
    ("ماشي الحال لا فرحان ولا زعلان", 0.5),                   # explicitly neutral
    ("الشغل عادي زي كل يوم", 0.5),                            # work routine
    ("هوا ده كلام عادي يعني", 0.5),                            # E: normal talk

    # --- mild negative (E = 0.3) --- 6 anchors
    ("تعبان شوي من الشغل والضغط", 0.3),                      # G: tired from work
    ("قلقان من الاختبار بكرا", 0.3),                           # G: worried about exam
    ("مخنوق من الزحمة والروتين", 0.3),                        # G: frustrated with routine
    ("حاسس بوحدة هالأيام ومحد جنبي", 0.3),                   # G: feeling lonely
    ("محتار ومش عارف وش أسوي بحياتي", 0.3),                   # L/E: confused about life
    ("مضايق من اللي صار بس ماشي الحال", 0.3),                 # E: upset but managing

    # --- intense negative (E = 0.0) --- 6 anchors
    ("ما عاد فيني أتحمل والله", 0.0),                         # G: can't take it anymore
    ("حاسس إن الدنيا ظلام وما في نور", 0.0),                 # hopelessness — darkness
    ("كل شي حولي ينهار وأنا عاجز", 0.0),                     # helplessness — collapsing
    ("خايف لدرجة إني مش قادر أتحرك", 0.0),                   # terror — paralyzed with fear
    ("غضبي وصل لدرجة ما أقدر أفكر بشي", 0.0),               # blind rage
    ("يائس تماماً ومش شايف أي أمل", 0.0),                     # total despair — no hope
]


class _OllamaBackend:
    """Local Ollama embeddings — same backend as H and I scorers."""
    def __init__(self, texts):
        import json, urllib.request
        self.url = "http://127.0.0.1:11434/api/embed"
        self.model = OLLAMA_EMBED_MODEL
        self.emb = self._embed(texts)

    def _embed(self, texts):
        import json, urllib.request
        body = json.dumps({"model": self.model, "input": texts}).encode()
        req = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        m = np.array(data["embeddings"], dtype=float)
        norms = np.linalg.norm(m, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        m = m / norms
        m = np.nan_to_num(m, nan=0.0, posinf=0.0, neginf=0.0)
        return m

    def sim(self, text):
        q = self._embed([text])[0]
        # Defensive: clean and unit-normalize the QUERY vector BEFORE the
        # dot product (same pattern as __init__/_embed for anchors), so a
        # genuinely bad embedding (inf/NaN/zero norm) can't poison the result.
        # Without this, a zero-norm query embedding produced "divide by zero"
        # and "overflow in matmul" RuntimeWarnings here and could corrupt E.
        q = np.nan_to_num(q, nan=0.0, posinf=0.0, neginf=0.0)
        qn = np.linalg.norm(q)
        if qn != 0:
            q = q / qn
        # Suppress spurious BLAS matmul FPU flags (result is still finite).
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            sims = self.emb @ q
        return np.nan_to_num(sims, nan=0.0, posinf=0.0, neginf=0.0)


class SemanticEmotionScorer:
    """
    Measures E (emotion) — the emotional state of the speaker.

    Same architecture as SemanticHarmScorer and SemanticIntentScorer:
      - top-K=3 nearest anchors
      - softmax temperature=0.05
      - bge-m3 via Ollama

    Returns E in [0, 1]:
      E -> 1.0 = positive (joy, love, gratitude, relief)
      E -> 0.5 = neutral
      E -> 0.0 = intense negative (despair, rage, terror)
    """
    def __init__(self, anchors=EMOTION_ANCHORS, temperature=0.05, top_k=3):
        self.texts = [a[0] for a in anchors]
        self.levels = np.array([a[1] for a in anchors], dtype=float)
        self.temperature = temperature
        self.top_k = top_k
        self.backend_name = "none"
        if USE_OLLAMA:
            try:
                self.backend = _OllamaBackend(self.texts)
                self.backend_name = f"ollama:{OLLAMA_EMBED_MODEL}"
            except Exception as e:
                print(f"[error] Ollama unavailable ({e})")
                raise

    # Confidence thresholds based on max cosine similarity
    CONFIDENCE_HIGH = 0.45    # strong match — score is reliable
    CONFIDENCE_MEDIUM = 0.30  # partial match — score is usable but uncertain
    # below 0.30 → "low" — out of distribution, score may be meaningless

    def score(self, text):
        sims = np.asarray(self.backend.sim(text), dtype=float)
        sims = np.clip(sims, 0, None)
        max_sim = float(sims.max()) if sims.size > 0 else 0.0

        if max_sim <= 1e-9:
            E = 0.5  # unknown -> neutral
            top = []
        else:
            order = np.argsort(sims)[::-1]
            k_idx = order[:self.top_k]
            k_sims = sims[k_idx]
            k_levels = self.levels[k_idx]
            w = np.exp(k_sims / self.temperature)
            w = w / w.sum()
            E = float((w * k_levels).sum())
            top = [(self.texts[i], round(float(sims[i]), 2), self.levels[i])
                   for i in order[:3]]

        # Confidence scoring: how much should we trust this E value?
        if max_sim >= self.CONFIDENCE_HIGH:
            confidence = "high"
        elif max_sim >= self.CONFIDENCE_MEDIUM:
            confidence = "medium"
        else:
            confidence = "low"  # out of distribution — E may be unreliable

        return {
            "E": round(E, 3),
            "nearest": top,
            "max_similarity": round(max_sim, 4),
            "confidence": confidence,
        }


# ---------------------------------------------------------------------------
# Self-test: emotion-specific probes + standard AATIF test messages
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    scorer = SemanticEmotionScorer()
    if hasattr(scorer.backend, 'emb'):
        norms = np.linalg.norm(scorer.backend.emb, axis=1)
        print(f"Anchor norms: min={norms.min():.4f} max={norms.max():.4f}")
        print()

    probes = [
        ("وش رايك بالطقس اليوم", "neutral (E~0.5)"),
        ("عطني فكرة هدية لأمي", "mild positive (E~0.7)"),
        ("تعبت من كل شي وحاسس إن ما في فايدة من وجودي", "intense negative (E~0.0)"),
        ("حزين شوي بس بخير", "mild negative (E~0.3)"),
        ("نفسي أنام وما أصحى", "intense negative (E~0.0-0.1)"),
        ("الحمد لله خلصت المشروع", "positive (E~1.0)"),
        ("فرحان اليوم مرررة", "positive (E~1.0)"),
        ("زهقت من البيت ومصاريفه وعايز بكرا ما يجيش", "mild-mod negative (E~0.2-0.3)"),
        ("زهقت من مصاريف البيت وأبغى بكرا ما يجي", "mild-mod negative (E~0.2-0.3)"),
        ("هوا احنا كنا اتفقنا علي ايش؟", "neutral (E~0.5)"),
        ("راح يجيب لهم جلطه", "neutral expression (E~0.5)"),
    ]

    print(f"backend: {scorer.backend_name}  |  top_k={scorer.top_k}  |  temp={scorer.temperature}")
    print(f"\n{'E':>6}  | note / message")
    print("-" * 70)
    for msg, note in probes:
        r = scorer.score(msg)
        print(f"{r['E']:>6.3f}  | [{note}]  {msg}")
        for t, s, lvl in r["nearest"][:2]:
            print(f"          ↳ sim={s:.2f} lvl={lvl}  «{t[:42]}»")
        print()
