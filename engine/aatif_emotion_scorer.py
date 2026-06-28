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
  E ~ 1.0  = extreme positive (joy, hope, gratitude, excitement, love, relief)
  E ~ 0.8  = high positive (pride, contentment, satisfaction, peace)
  E ~ 0.7  = mild positive/calm (content, peaceful, curious, amused)
  E ~ 0.6  = moderate positive (pleasant, casual happiness, light mood)
  E ~ 0.5  = neutral (no strong emotion, factual, matter-of-fact)
  E ~ 0.4  = mild negative (slight frustration, minor annoyance, boredom)
  E ~ 0.3  = moderate negative (frustrated, tired, worried, confused, lonely)
  E ~ 0.2  = significant negative (real sadness, anxiety, emotional weight)
  E ~ 0.1  = severe negative (deep despair, emptiness, crisis-adjacent)
  E ~ 0.0  = extreme negative (despair, rage, terror, hopelessness)

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

# M7: shared config — single source of truth for embedding settings
from aatif_embeddings import (
    OllamaBackend as _OllamaShared,
    USE_OLLAMA,
    OLLAMA_EMBED_MODEL,
)

# ---------------------------------------------------------------------------
# EMOTION ANCHORS
# Each anchor = (example_text, emotion_level in 0..1).
# E = 1.0  -> extreme positive (joy, gratitude, excitement, love, relief)
# E = 0.8  -> high positive (pride, contentment, satisfaction, peace)
# E = 0.7  -> mild positive / calm (content, peaceful, curious)
# E = 0.6  -> moderate positive (pleasant, casual happiness, light mood)
# E = 0.5  -> neutral (no strong emotion, factual)
# E = 0.4  -> mild negative (slight frustration, annoyance, boredom)
# E = 0.3  -> moderate negative (frustrated, tired, worried, lonely)
# E = 0.2  -> significant negative (real sadness, anxiety, weight)
# E = 0.1  -> severe negative (deep despair, emptiness, crisis-adjacent)
# E = 0.0  -> extreme negative (despair, rage, terror, hopelessness)
#
# DIALECT KEY: G=Gulf, Eg=Egyptian, Lev=Levantine, Iq=Iraqi, Mg=Maghrebi, Su=Sudanese
# CONTAMINATION GUARD: no "نفسي" or "أبغى" in anchors
# ---------------------------------------------------------------------------
EMOTION_ANCHORS = [
    # === EXTREME POSITIVE (E = 1.0) === 15 anchors
    ("فرحان اليوم والحمد لله", 1.0),                          # G: happy today
    ("مبسوط من النتيجة مرررة", 1.0),                          # G/Eg: very pleased with result
    ("شكراً من كلّ قلبي على مساعدتك", 1.0),                   # gratitude from the heart
    ("متحمس للسفرة الجاية ما أقدر أصبر", 1.0),               # G: can't wait for the trip
    ("قلبي مليان حب لأهلي الله يخليهم", 1.0),                 # love for family
    ("ارتحت كثير لما عرفت إن كل شي تمام", 1.0),              # relief — all is well
    # dialect expansion
    ("أنا فرحان أوي النهاردة", 1.0),                           # Eg: so happy today
    ("مبسوط كتير هلق", 1.0),                                   # Lev: very happy right now
    ("فرحان مرة اليوم", 1.0),                                  # Iq: so happy today
    ("فرحان بزاف اليوم", 1.0),                                 # Mg: very happy today
    ("مبسوط خالص", 1.0),                                       # Su: completely happy
    ("this is the best day of my life", 1.0),                   # EN: peak joy
    ("I'm so grateful for everything", 1.0),                    # EN: deep gratitude
    ("الحمدلله على كل شي", 1.0),                               # spiritual gratitude
    ("ما أصدق إني نجحت!", 1.0),                                # disbelief joy — passed!

    # === HIGH POSITIVE / PRIDE / CONTENTMENT (E = 0.8–0.9) === 6 anchors
    ("أحس بفخر كبير", 0.8),                                    # pride (no نفسي)
    ("الحمدلله الأمور تمام", 0.8),                              # contentment — things are good
    ("مرتاح في بالي اليوم", 0.8),                               # at peace today (no نفسي)
    ("I'm really proud of what we accomplished", 0.85),          # EN: team pride
    ("شكراً لكل اللي ساعدني", 0.8),                            # gratitude for help
    ("أحسن يوم في الشغل", 0.9),                                # best day at work

    # === MILD POSITIVE / CALM (E = 0.7) === 8 anchors
    ("الحمد لله ماشي الحال وكل شي زين", 0.7),                # G: content, things are good
    ("حاسس براحة وهدوء اليوم", 0.7),                         # peaceful today
    ("مستانس أتعلم شي جديد", 0.7),                            # G: enjoying learning
    ("متفائل إن بكرا أحسن إن شاء الله", 0.7),                # optimistic about tomorrow
    ("الجو حلو وقاعد أستمتع بيومي", 0.7),                    # mild enjoyment
    # social media / marketing energy — ambitious but positive
    ("عايزين نعمل حاجة كبيرة على السوشيال ميديا", 0.7),     # want to do something big on social
    ("نبغى نطلق حملة تسويقية تفجر السوشيال", 0.7),           # launch a viral marketing campaign
    ("المنتج ده هيكسر الدنيا في المبيعات", 0.7),              # this product will crush it in sales

    # === MODERATE POSITIVE (E = 0.6) === 6 anchors
    ("يومي كان حلو", 0.6),                                     # my day was nice
    ("الجو حلو اليوم", 0.6),                                   # the weather is nice today
    ("استمتعت بالفلم", 0.6),                                   # enjoyed the movie
    ("not bad, actually feeling pretty good", 0.6),             # EN: mild positive
    ("الأكل كان لذيذ", 0.6),                                   # the food was delicious
    ("مبسوط إني خلصت الشغل", 0.6),                             # happy I finished work

    # === NEUTRAL (E = 0.5) === 11 anchors
    ("عادي يعني مافي شي مميز", 0.5),                          # G: nothing special
    ("الطقس حار اليوم بس عادي", 0.5),                         # factual weather
    ("رحت السوق وجبت الأغراض", 0.5),                          # factual routine
    ("ماشي الحال لا فرحان ولا زعلان", 0.5),                   # explicitly neutral
    ("الشغل عادي زي كل يوم", 0.5),                            # work routine
    ("هوا ده كلام عادي يعني", 0.5),                            # Eg: normal talk
    # expanded neutral
    ("ما عندي رأي", 0.5),                                      # no opinion
    ("just checking in", 0.5),                                  # EN: routine check-in
    ("ممكن تساعدني بسؤال؟", 0.5),                              # help request — neutral
    ("مفيش حاجة جديدة", 0.5),                                  # Eg: nothing new
    ("عادي ما كو شي", 0.5),                                    # Iq: nothing special

    # === MILD NEGATIVE / ANNOYANCE (E = 0.4) === 6 anchors
    ("زهقت شوية", 0.4),                                        # a bit bored
    ("مو أحسن يوم", 0.4),                                      # not the best day
    ("الشغل ممل اليوم", 0.4),                                  # work is boring today
    ("a little annoyed but it's fine", 0.4),                    # EN: mild annoyance
    ("ما جاني نوم البارحة", 0.4),                              # couldn't sleep last night
    ("تعبان من الروتين", 0.4),                                  # tired of the routine

    # === MODERATE NEGATIVE (E = 0.3) === 6 anchors
    ("تعبان شوي من الشغل والضغط", 0.3),                      # G: tired from work
    ("قلقان من الاختبار بكرا", 0.3),                           # G: worried about exam
    ("مخنوق من الزحمة والروتين", 0.3),                        # G: frustrated with routine
    ("حاسس بوحدة هالأيام ومحد جنبي", 0.3),                   # G: feeling lonely
    ("محتار ومش عارف وش أسوي بحياتي", 0.3),                   # Lev/Eg: confused about life
    ("مضايق من اللي صار بس ماشي الحال", 0.3),                 # Eg: upset but managing

    # === SIGNIFICANT NEGATIVE / ANXIETY (E = 0.2) === 7 anchors
    ("أحس بضيقة", 0.2),                                        # tightness / anxiety
    ("قلبي مقبوض", 0.2),                                       # heavy heart
    ("مو قادر أنام من التفكير", 0.2),                          # can't sleep from overthinking
    ("I've been feeling really down lately", 0.2),              # EN: persistent sadness
    ("حاسس إني مخنوق", 0.2),                                   # Eg: feeling suffocated
    ("الوحدة صعبة", 0.2),                                      # loneliness is hard
    ("ضايق من كلشي", 0.2),                                     # Iq: upset about everything

    # === SEVERE NEGATIVE / DEEP DISTRESS (E = 0.1) === 6 anchors
    ("ما عاد أحس بشي", 0.1),                                   # I don't feel anything anymore
    ("كل شي ظلام", 0.1),                                       # everything is darkness
    ("أحس ما أحد يفهمني", 0.1),                                # nobody understands me
    ("I feel completely empty inside", 0.1),                    # EN: emotional emptiness
    ("ما بقى شي يسعدني", 0.1),                                 # nothing makes me happy
    ("يا ريت ما كنت موجود", 0.05),                             # wish I didn't exist — near-zero

    # === EXTREME NEGATIVE (E = 0.0) === 12 anchors
    ("ما عاد فيني أتحمل والله", 0.0),                         # G: can't take it anymore
    ("حاسس إن الدنيا ظلام وما في نور", 0.0),                 # hopelessness — darkness
    ("كل شي حولي ينهار وأنا عاجز", 0.0),                     # helplessness — collapsing
    ("خايف لدرجة إني مش قادر أتحرك", 0.0),                   # terror — paralyzed with fear
    ("غضبي وصل لدرجة ما أقدر أفكر بشي", 0.0),               # blind rage
    ("يائس تماماً ومش شايف أي أمل", 0.0),                     # total despair — no hope
    # dialect expansion
    ("أنا تعبان أوي من جوا", 0.0),                             # Eg: exhausted from inside (no نفسي)
    ("ما عاد بدي شي من الحياة", 0.0),                          # Lev: want nothing from life
    ("كلشي خربان", 0.0),                                       # Iq: everything is ruined
    ("ما بقيتش قادر نتحمل", 0.0),                              # Mg: can't bear it anymore
    ("ودي أصرخ من الألم", 0.0),                                 # G: want to scream from pain (no أبغى)
    ("I feel like giving up on everything", 0.0),               # EN: giving up

    # === MIXED / COMPLEX EMOTIONS === 5 anchors
    ("فرحان بس حزين نفس الوقت", 0.5),                         # happy but sad — bittersweet
    ("الله يرحمه كان أحسن واحد", 0.3),                        # grief + love — eulogy
    ("مشتاق لأيام زمان", 0.35),                                # nostalgia — missing old days
    ("proud but exhausted", 0.5),                               # EN: mixed pride + fatigue
    ("فرحان إنه نجح بس حزين إنه راح يسافر", 0.5),            # happy for success, sad about departure
]


# M7: OllamaBackend consolidated into aatif_embeddings.py
_OllamaBackend = _OllamaShared


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
                # C4 FIX: raise descriptive RuntimeError — same pattern
                # as H scorer. All thresholds are calibrated on bge-m3;
                # operating without calibrated embeddings is unsafe.
                raise RuntimeError(
                    f"AATIF E scorer requires calibrated embeddings "
                    f"(Ollama/bge-m3) but Ollama is unavailable: {e}. "
                    f"All emotion thresholds are calibrated on bge-m3 — "
                    f"operating without it would produce uncalibrated "
                    f"scores. Start Ollama with: ollama serve && ollama pull bge-m3"
                ) from e

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
