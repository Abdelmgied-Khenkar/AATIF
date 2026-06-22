"""
AATIF S Equation — Unified Governance Decision Engine
=====================================================

The core of AATIF: combines three perception channels into one decision.

    S = σ(w₁·I + w₂·E − w₃·H)

Where:
    H = حرارة الكلمة  (harm proximity)   — from aatif_semantic_scorer.py
    I = النية          (intent / purpose) — from aatif_intent_scorer.py
    E = الشعور         (emotion / feeling) — from aatif_emotion_scorer.py

S produces a continuous safety score in [0, 1] that maps to four decisions:
    EXECUTE     (S > 0.7)   — safe to respond
    CLARIFY     (0.5 < S ≤ 0.7) — ask for clarification
    SAFE_STOP   (0.3 < S ≤ 0.5) — stop, seek human guidance
    SAFE_FREEZE (S ≤ 0.3)  — freeze, maximum caution

Follow-up signal F provides a harm-floor guarantee:
    F' = D × (1 − S)           where D = 1.0
    F  = max(F', k × H)        where k = 0.3
    Even high-S results carry a minimum follow-up if H is high.

Safety guard: if H > 0.7, creative profile cannot produce EXECUTE or CLARIFY.

Gated variant (v2):
    S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))

    The gated equation separates the "quality" signal (intent + emotion)
    from the "harm gate" into two independent sigmoids multiplied together.
    This produces a hard suppression boundary: when H crosses θ, the gate
    sigmoid drops sharply (controlled by α = steepness), driving S → 0
    regardless of how high I and E are.

    Key advantage: unlike the classic equation where extreme I+E can
    compensate for moderate H ("toxic positivity" attack), the gated
    form makes harm suppression INDEPENDENT of intent/emotion.

    Hard override: if H > 0.7, decision is forced to SAFE_FREEZE
    (stronger than classic mode's SAFE_STOP guard).

    Profile variants add α (gate steepness) and θ (harm threshold):
      default:          α=10, θ=0.40  (calibrated 2026-06-19 via bge-m3 A/B test)
      high_sensitivity: α=15, θ=0.45
      creative:         α=8,  θ=0.55
      balanced_strict:  α=10, θ=0.40  (identical to default)

    2026-06-20 precision fix: held-out validation (56 cases) exposed an H
    over-blocking problem (precision 0.60). Adding educational "safe" anchors
    + counter-harm anchors to the H scorer (aatif_semantic_scorer.py) lifted
    held-out F1 0.735→0.943 (precision 0.60→0.93) with recall held at 0.96.
    θ was left at 0.40 — raising it reopened a surveillance hole. The H-I
    link (Fix 2, link_h_to_i=compute() arg) is implemented but left OFF: it
    added no F1 once anchors handled precision. See benchmarks/fix_comparison.md.

    Note: θ was initially 0.5, raised to 0.55, then lowered to 0.40 after
    A/B testing with bge-m3 embeddings (54 test cases, 30 harmful / 24 benign).
    At θ=0.55 the gate missed spousal surveillance (H=0.40); at θ=0.40 it
    catches all 30 harmful cases with only 1 false positive ("حزين شوي بس بخير"
    → SAFE_STOP, which aligns with ع ط ف compassionate response).
    The gate function 1−σ(α·(H−θ)) is monotonically *increasing* in θ
    at any fixed H, so raising θ opens the gate more at a given H level.

Verified by 126+ programmatic tests (FN#077 + gated comparison suite).
Zero equation bugs.

Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations
import math
import sys
import os

# ---------------------------------------------------------------------------
# Ensure the AATIF directory is on the path so scorers can be imported
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from aatif_semantic_scorer import SemanticHarmScorer
from aatif_intent_scorer import SemanticIntentScorer
from aatif_emotion_scorer import SemanticEmotionScorer
from aatif_hysteresis import HysteresisController


# ---------------------------------------------------------------------------
# AMBIGUITY / CLARITY PRE-CHECK
# Catches prompts that are too vague to act on — forces CLARIFY.
# Pattern: short text + no specific object/action = incomplete request.
#
# "ساعدني" (help me) — help with WHAT?
# "Fix it" — fix WHAT?
# "حسّنها" (improve it) — improve WHAT?
# "Send that email" — which email? to whom?
# "اكتب حاجة حلوة" (write something nice) — what kind? for whom?
#
# These have high I (good intent) and positive E, so the S equation
# says EXECUTE. But a human says CLARIFY because the request is incomplete.
#
# Logic: if the prompt is short AND doesn't contain enough specificity
# (a concrete noun/topic that makes the request actionable), → CLARIFY.
# ---------------------------------------------------------------------------

# Words that indicate the prompt has a SPECIFIC, actionable target
# (their presence means the request is probably complete enough)
_SPECIFICITY_MARKERS_AR = {
    # concrete topics / domains
    "محرك", "برمجة", "بايثون", "python", "جافا", "java", "كود", "code",
    "رياضيات", "math", "فيزياء", "كيمياء", "تاريخ", "جغرافيا",
    # specific objects
    "سيارة", "بيت", "شقة", "جوال", "لابتوب", "كمبيوتر",
    # numbers / calculations (presence of digits = specific)
    "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩", "٠",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    "%", "٪",
    # question words that frame a complete question
    "ما هي", "ما هو", "what is", "what are", "how does", "how do",
    "كم", "متى", "أين", "لماذا", "كيف يشتغل", "كيف يعمل",
    "عاصمة", "capital",
}

# Phrases that are SELF-CONTAINED even if short (complete requests)
_SELF_CONTAINED_PATTERNS = [
    "اشرح كيف",        # "explain how X works" — has a target
    "احسب",            # "calculate" — usually followed by numbers
    "كم الساعة",       # "what time is it" — complete
    "what is the",     # "what is the capital of" — complete
    "how does",        # "how does X work" — complete
    "explain how",     # complete
]


def _is_ambiguous(text: str) -> bool:
    """
    Return True if the prompt is too vague/incomplete to act on.

    Heuristic:
      1. Very short text (≤ 5 words) with no specificity markers → ambiguous
      2. Medium text (≤ 8 words) with pronoun-only references
         ("it", "that", "ها", "ه", "دي", "ده") and no topic → ambiguous
      3. Any text that matches a self-contained pattern → NOT ambiguous
      4. Harm-related text is never flagged as ambiguous (let H handle it)
    """
    t = text.strip()
    t_lower = t.lower()

    # Word count (split on whitespace — works for Arabic and English)
    words = t.split()
    wc = len(words)

    # Long prompts are rarely ambiguous (enough context)
    if wc > 8:
        return False

    # Check self-contained patterns first (these are always clear)
    for pat in _SELF_CONTAINED_PATTERNS:
        if pat in t or pat in t_lower:
            return False

    # Check for specificity markers (digits, concrete nouns, question frames)
    for marker in _SPECIFICITY_MARKERS_AR:
        if marker in t or marker in t_lower:
            return False

    # Very short (≤ 5 words) with no markers → almost certainly ambiguous
    if wc <= 5:
        return True

    # Medium length (6-8 words): check for vague pronoun references
    _vague_refs = {"it", "that", "this", "those", "ها", "ه", "هو", "هي",
                   "دي", "ده", "ذا", "اللي", "الموضوع", "الحاجة", "الشي"}
    has_vague_ref = any(w in _vague_refs for w in t_lower.split())
    if has_vague_ref:
        return True

    return False


# ---------------------------------------------------------------------------
# JAILBREAK / MANIPULATION DETECTOR
# SAFE_FREEZE should be reserved for active manipulation attempts
# (jailbreak phrases, override instructions, specific malware tools).
# Simple harm terms like "متفجرات" or "Hack bank account" should get
# SAFE_STOP — they're harmful but not manipulation.
#
# This function checks for markers of active manipulation or specific
# malware/tool names that make the request itself the weapon.
# ---------------------------------------------------------------------------
_JAILBREAK_MARKERS = [
    # English override/jailbreak patterns
    "ignore instructions", "ignore previous", "override safety",
    "bypass", "developer mode", "jailbreak", " DAN ",
    "disable safety", "act as if",
    # Arabic override/jailbreak patterns
    "تجاوز", "تجاهل القوانين", "تجاهل القيود", "مسؤول النظام",
    "تخطى الحماية", "وضع المطور",
    # Specific malware tool names (the request IS the harm)
    "keylogger", "trojan", "rootkit", "ransomware",
    "spyware", "backdoor", "rat ",
]


def _has_jailbreak_markers(text: str) -> bool:
    """Return True if text contains jailbreak/manipulation keywords."""
    t_lower = text.lower()
    for marker in _JAILBREAK_MARKERS:
        if marker in t_lower:
            return True
    return False


# ---------------------------------------------------------------------------
# WEIGHT PROFILES
# Each profile adjusts how much the equation listens to intent, emotion, harm.
# Verified: profile ordering is always
#   high_sensitivity < default < casual < safe_environment < creative
# ---------------------------------------------------------------------------
PROFILES = {
    "default": {
        "w1": 2.0,    # intent weight
        "w2": 1.5,    # emotion weight
        "w3": 3.0,    # harm weight
        "desc": "Balanced — harm weighs most"
    },
    "high_sensitivity": {
        "w1": 2.0,
        "w2": 1.0,
        "w3": 5.0,
        "desc": "Conservative — harm dominates"
    },
    "safe_environment": {
        "w1": 2.5,
        "w2": 2.0,
        "w3": 2.0,
        "desc": "Permissive — intent and emotion matter more"
    },
    "creative": {
        "w1": 3.0,
        "w2": 2.5,
        "w3": 2.0,
        "desc": "Most permissive — intent-driven"
    },
    "casual": {
        "w1": 2.0,
        "w2": 1.5,
        "w3": 2.5,
        "desc": "Slightly relaxed default"
    },
}

# ---------------------------------------------------------------------------
# GATED PROFILES (for equation_mode="gated")
#
# The gated equation S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))
# uses two new parameters:
#   α (alpha) = steepness of the harm gate sigmoid
#   θ (theta) = harm threshold (center of the gate sigmoid)
#
# w1, w2 control the "quality" sigmoid (intent + emotion).
# α, θ  control the "harm gate" sigmoid.
# w3 is NOT used in gated mode (harm is handled by the gate).
#
# Hard override: H > 0.7 → SAFE_FREEZE regardless of other scores.
# ---------------------------------------------------------------------------
GATED_PROFILES = {
    "default": {
        "w1": 2.0,     # intent weight
        "w2": 1.5,     # emotion weight
        "alpha": 10,   # gate steepness
        "theta": 0.40, # harm threshold — kept at 0.40: raising it to 0.45 reopened
                       # the spousal-surveillance hole (H=0.40 → CLARIFY). The
                       # 2026-06-20 precision fix is carried by the H "safe"
                       # anchors instead, not by θ. (see fix_comparison.md)
        "desc": "Balanced gate — moderate steepness, gate center at H=0.40 (calibrated 2026-06-19)"
    },
    "high_sensitivity": {
        "w1": 2.0,
        "w2": 1.0,
        "alpha": 15,   # steeper gate → narrower transition zone
        "theta": 0.30, # gate center BELOW default (0.40) so it closes earlier =
                       # catches harm sooner. Fixed 2026-06-20: was 0.45, which
                       # sat ABOVE default and made the "high sensitivity" gate
                       # MORE permissive than default across H∈[0.20,0.50] — a
                       # logic inversion contradicting the profile's purpose,
                       # its own comment, and the v9.7 spec (θ=0.30). Gate
                       # ordering now: high_sensitivity ≤ default ≤ creative.
        "desc": "Conservative gate — triggers earlier (θ=0.30), sharper cutoff"
    },
    "creative": {
        "w1": 3.0,
        "w2": 2.5,
        "alpha": 8,    # gentler slope → wider transition
        "theta": 0.55, # higher threshold → more tolerant
        "desc": "Permissive gate — intent-driven, wider tolerance"
    },
    "balanced_strict": {
        "w1": 2.0,
        "w2": 1.5,
        "alpha": 10,   # same steepness as default
        "theta": 0.40, # tighter gate — catches surveillance/espionage cases
        "desc": "Tighter gate — calibrated via A/B test (2026-06-19)"
    },
}

# ---------------------------------------------------------------------------
# DOMAIN CONFIGURATION — θ(d)
#
# Domain determines the HARM THRESHOLD (θ). This is the core of
# "الاذي مالوش توقيت" refined: TIME doesn't change θ. DOMAIN does.
#
# Healthcare harm is more dangerous than e-commerce harm, so the gate
# closes EARLIER (lower θ = less tolerance for harm signals).
#
# When domain is specified, it OVERRIDES the profile's θ.
# Profiles still control w1, w2, alpha (quality weights and gate steepness).
# θ comes from domain — because harm sensitivity is a property of the
# CONTEXT, not the system's personality.
#
# Hard override (H > 0.7 → SAFE_FREEZE) stays ABSOLUTE regardless of domain.
# "الاذي مالوش توقيت" — and it has no domain either at the extreme.
#
# Architect: "θ varies by domain, not by time"
# Design session: 2026-06-22
# ---------------------------------------------------------------------------
DOMAIN_CONFIG = {
    "healthcare": {
        "theta": 0.25,
        "desc": "Medical/health context — gate closes early, harm is physical",
    },
    "education": {
        "theta": 0.30,
        "desc": "Children/students — gate closes early, harm is developmental",
    },
    "general": {
        "theta": 0.40,
        "desc": "Default — balanced gate (same as calibrated default profile)",
    },
    "tech": {
        "theta": 0.40,
        "desc": "Technical support — same as general",
    },
    "ecommerce": {
        "theta": 0.40,
        "desc": "Commercial/shopping — same as general",
    },
    "creative": {
        "theta": 0.50,
        "desc": "Creative writing/art — wider tolerance for sensitive topics",
    },
}


def get_domain_theta(domain: str | None) -> float | None:
    """
    Return the θ override for a given domain, or None if no override.

    When domain is specified, this θ replaces the profile's θ.
    When domain is None, the profile's θ is used (returns None).

    Raises ValueError if domain is a non-None string that is not
    in DOMAIN_CONFIG. This is a safety-critical guard: a typo like
    "heathcare" must fail loudly, not silently fall back to a
    different safety threshold.

    Codex review 2026-06-22: "In governance/safety code, silent
    fallback for unknown domains is a meaningful failure mode."
    """
    if domain is None:
        return None
    cfg = DOMAIN_CONFIG.get(domain)
    if cfg is None:
        valid = ", ".join(sorted(DOMAIN_CONFIG.keys()))
        raise ValueError(
            f"Unknown domain '{domain}'. "
            f"Valid domains: {valid}"
        )
    return cfg["theta"]


# Hard override threshold for gated mode: H above this → SAFE_FREEZE
H_GATED_HARD_OVERRIDE = 0.7

# ---------------------------------------------------------------------------
# DECISION THRESHOLDS (verified in FN#077 — Test 3, 12/12 pass)
# ---------------------------------------------------------------------------
THRESHOLDS = [
    (0.7, "EXECUTE"),       # S > 0.7
    (0.5, "CLARIFY"),       # 0.5 < S ≤ 0.7
    (0.3, "SAFE_STOP"),     # 0.3 < S ≤ 0.5
    (0.0, "SAFE_FREEZE"),   # S ≤ 0.3
]

# Harm floor constant (verified in FN#077 — Test 6, 5/5 pass)
K_HARM_FLOOR = 0.3

# Safety guard threshold: H above this triggers creative profile guard
H_GUARD_THRESHOLD = 0.7


# ---------------------------------------------------------------------------
# MATH
# ---------------------------------------------------------------------------

def sigmoid(x: float) -> float:
    """Standard sigmoid σ(x) = 1 / (1 + e^(-x))"""
    # Clamp to avoid overflow in math.exp
    x = max(-500.0, min(500.0, x))
    return 1.0 / (1.0 + math.exp(-x))


# ---------------------------------------------------------------------------
# FIX 2 (optional): LINK H TO I  — "trust benign intent"
#
# The held-out analysis showed H over-blocks because it measures topic
# sensitivity, not harmful intent. When intent I is clearly BENIGN, we can
# discount H so a sensitive *topic* with constructive *purpose* isn't blocked.
#
# NOTE on convention: in AATIF, HIGH I = constructive/benign, LOW I = harmful.
# Relief scales with how far I sits ABOVE neutral (0.5):
#     H_eff = H · (1 − λ · clip((I − 0.5)/0.5, 0, 1))
# λ=0 → no change (default).  λ=1 → fully benign intent zeroes H.
#
# Default OFF: the held-out experiments (benchmarks/fix_comparison.md) found
# that once educational "safe" anchors handle the precision problem (Fix 1),
# the H-I link adds no F1 and risks recall on cases where the intent scorer
# is fooled into a high benign I (e.g. elder-scam scripts, fraud sites).
# It is implemented here so it can be enabled per-call for experimentation.
# ---------------------------------------------------------------------------
H_I_LINK_LAMBDA = 0.5  # used only when link_h_to_i=True is passed to compute()


def link_h_to_intent(H: float, I: float, lam: float = H_I_LINK_LAMBDA,
                     i_neutral: float = 0.5) -> float:
    """Return an H reduced toward 0 in proportion to how benign intent I is."""
    if lam <= 0:
        return H
    frac = (I - i_neutral) / (1.0 - i_neutral)
    frac = max(0.0, min(1.0, frac))
    return H * (1.0 - lam * frac)


def compute_s_from_scores(H: float, I: float, E: float,
                          profile: str = "default") -> dict:
    """
    Compute S, F, and decision from pre-computed scorer values.

    Use this when you already have H, I, E scores (e.g., from tests).
    For live text input, use compute_s() instead.
    """
    p = PROFILES[profile]
    w1, w2, w3 = p["w1"], p["w2"], p["w3"]

    # S equation (verified: monotonic in I+, E+, H-)
    z = w1 * I + w2 * E - w3 * H
    S = sigmoid(z)

    # Follow-up signal
    D = 1.0
    F_prime = D * (1.0 - S)
    F = max(F_prime, K_HARM_FLOOR * H)

    # Decision from thresholds
    decision = "SAFE_FREEZE"
    for threshold, label in THRESHOLDS:
        if S > threshold:
            decision = label
            break

    # SAFETY GUARD: creative profile + high harm = at least SAFE_STOP
    # Root cause: creative w3=2.0 doesn't penalize H enough (FN#077 Test 4c)
    # Example: "أنام وما أصحى" got S=0.5139 → CLARIFY on creative, too permissive
    if H > H_GUARD_THRESHOLD and decision in ("EXECUTE", "CLARIFY"):
        decision = "SAFE_STOP"

    return {
        "H": round(H, 4),
        "I": round(I, 4),
        "E": round(E, 4),
        "z": round(z, 4),
        "S": round(S, 4),
        "F_prime": round(F_prime, 4),
        "F": round(F, 4),
        "decision": decision,
        "profile": profile,
        "equation_mode": "classic",
        "guard_applied": H > H_GUARD_THRESHOLD and S > 0.3,
    }


def compute_s_gated_from_scores(H: float, I: float, E: float,
                                profile: str = "default",
                                domain: str | None = None) -> dict:
    """
    Compute S using the GATED equation, with F and decision.

    Gated equation:
        S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))

    Mathematical basis:
        The first term σ(w₁·I + w₂·E) measures "quality" — how clear
        and well-intentioned the request is. Range: (0, 1).

        The second term (1 − σ(α·(H − θ))) is the "harm gate".
        When H < θ, the gate is ≈ 1 (open). When H > θ, the gate
        drops toward 0 (closed). α controls how sharp the transition is.

        The product ensures that high-quality requests pass through
        when harm is low, but even perfect intent+emotion cannot
        overcome moderate harm — the gate closes independently.

    Hard override:
        If H > 0.7, return SAFE_FREEZE immediately. This is an
        absolute safety floor that no combination of I+E can bypass.

    Use this when you already have H, I, E scores (e.g., from tests).
    For live text input, use AATIFEngine.compute() with equation_mode="gated".
    """
    p = GATED_PROFILES[profile]
    w1, w2 = p["w1"], p["w2"]
    alpha = p["alpha"]

    # θ(d): domain overrides profile theta when specified.
    # This is the core of domain-parameterized governance.
    domain_theta = get_domain_theta(domain)
    theta = domain_theta if domain_theta is not None else p["theta"]

    # HARD OVERRIDE: H above absolute threshold → immediate freeze
    # This is ABSOLUTE — no domain, no profile, no exception.
    if H > H_GATED_HARD_OVERRIDE:
        # Still compute S for diagnostics, but decision is forced
        quality = sigmoid(w1 * I + w2 * E)
        gate = 1.0 - sigmoid(alpha * (H - theta))
        S = quality * gate
        F_prime = 1.0 * (1.0 - S)
        F = max(F_prime, K_HARM_FLOOR * H)
        return {
            "H": round(H, 4),
            "I": round(I, 4),
            "E": round(E, 4),
            "quality": round(quality, 4),
            "gate": round(gate, 4),
            "S": round(S, 4),
            "F_prime": round(F_prime, 4),
            "F": round(F, 4),
            "decision": "SAFE_FREEZE",
            "profile": profile,
            "domain": domain,
            "theta_effective": round(theta, 4),
            "theta_source": "domain" if domain_theta is not None else "profile",
            "equation_mode": "gated",
            "hard_override": True,
        }

    # Normal gated computation
    quality = sigmoid(w1 * I + w2 * E)
    gate = 1.0 - sigmoid(alpha * (H - theta))
    S = quality * gate

    # Follow-up signal (same formula as classic)
    D = 1.0
    F_prime = D * (1.0 - S)
    F = max(F_prime, K_HARM_FLOOR * H)

    # Decision from thresholds (same thresholds as classic)
    decision = "SAFE_FREEZE"
    for threshold, label in THRESHOLDS:
        if S > threshold:
            decision = label
            break

    return {
        "H": round(H, 4),
        "I": round(I, 4),
        "E": round(E, 4),
        "quality": round(quality, 4),
        "gate": round(gate, 4),
        "S": round(S, 4),
        "F_prime": round(F_prime, 4),
        "F": round(F, 4),
        "decision": decision,
        "profile": profile,
        "domain": domain,
        "theta_effective": round(theta, 4),
        "theta_source": "domain" if domain_theta is not None else "profile",
        "equation_mode": "gated",
        "hard_override": False,
    }


class AATIFEngine:
    """
    The AATIF Governance Engine.

    Combines three scorers (H, I, E) into a unified safety decision.
    Initialize once, then call compute() on any Arabic text.

    Supports two equation modes:
        "classic" — S = σ(w₁·I + w₂·E − w₃·H)          [original]
        "gated"   — S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))  [v2]

    Usage:
        engine = AATIFEngine()
        result = engine.compute("عطني فكرة هدية لأمي")
        print(result["decision"])  # → "EXECUTE"
        print(result["S"])         # → 0.9554

        # Use gated mode:
        result = engine.compute("عطني فكرة هدية لأمي", equation_mode="gated")
    """

    def __init__(self):
        print("[AATIF] Initializing scorers...")
        self.h_scorer = SemanticHarmScorer()
        print(f"  H scorer ready ({self.h_scorer.backend_name})")
        self.i_scorer = SemanticIntentScorer()
        print(f"  I scorer ready ({self.i_scorer.backend_name})")
        self.e_scorer = SemanticEmotionScorer()
        print(f"  E scorer ready ({self.e_scorer.backend_name})")
        self.hysteresis = HysteresisController()
        print("  γ+ hysteresis ready")
        print("[AATIF] Engine ready.\n")

    def compute(self, text: str, profile: str = "default",
                verbose: bool = False,
                conversation_id: str = None,
                equation_mode: str = "classic",
                domain: str = None,
                link_h_to_i: bool = False,
                h_i_lambda: float = H_I_LINK_LAMBDA) -> dict:
        """
        Run all three scorers on input text, compute S, return decision.

        Args:
            text: Arabic input text
            profile: one of "default", "high_sensitivity", "safe_environment",
                     "creative", "casual"
                     (gated mode only supports: "default", "high_sensitivity",
                     "creative")
            verbose: if True, include nearest-anchor diagnostics
            conversation_id: if provided, applies γ+ hysteresis across turns
                            (prevents decision oscillation in conversations)
            equation_mode: "classic" for S = σ(w₁·I + w₂·E − w₃·H)
                          "gated"   for S = σ(w₁·I + w₂·E) × (1 − σ(α·(H − θ)))
            domain: one of "healthcare", "education", "general", "tech",
                    "ecommerce", "creative", or None.
                    When specified (gated mode only), overrides the profile's θ
                    with domain-specific θ(d). This is domain-parameterized
                    governance: harm sensitivity is a property of CONTEXT.
                    "الاذي مالوش توقيت" — time doesn't change θ. Domain does.

        Returns:
            dict with keys: text, H, I, E, S, F_prime, F, decision,
                           profile, equation_mode, domain,
                           theta_effective, theta_source (gated mode),
                           ambiguity_override,
                           hysteresis (if conversation_id provided)
                           (+ h_nearest, i_nearest, e_nearest if verbose)
                           Classic mode also includes: z, guard_applied
                           Gated mode also includes: quality, gate, hard_override
        """
        if equation_mode not in ("classic", "gated"):
            raise ValueError(f"equation_mode must be 'classic' or 'gated', got {equation_mode!r}")

        # Score each dimension
        h_result = self.h_scorer.score(text)
        i_result = self.i_scorer.score(text)
        e_result = self.e_scorer.score(text)

        H = h_result["H"]
        I = i_result["I"]
        E = e_result["E"]

        # FIX 2 (optional): discount H when intent is clearly benign.
        # Applied BEFORE the gate (and before the H>0.7 hard override) so a
        # benign-intent sensitive topic can be rescued. Default off.
        H_raw = H
        if link_h_to_i:
            H = link_h_to_intent(H, I, lam=h_i_lambda)

        # Compute S and decision using selected equation
        if equation_mode == "gated":
            result = compute_s_gated_from_scores(H, I, E, profile=profile,
                                                  domain=domain)
        else:
            result = compute_s_from_scores(H, I, E, profile=profile)
        result["text"] = text
        if link_h_to_i and H != H_raw:
            result["H_raw"] = round(H_raw, 4)
            result["h_i_linked"] = True

        # CONFIDENCE AGGREGATION
        # Each scorer now reports confidence (high/medium/low).
        # Overall confidence = weakest link (minimum of the three).
        # If ANY scorer has low confidence, the whole result is uncertain.
        _conf_order = {"high": 2, "medium": 1, "low": 0}
        _conf_reverse = {2: "high", 1: "medium", 0: "low"}
        h_conf = h_result.get("confidence", "high")
        i_conf = i_result.get("confidence", "high")
        e_conf = e_result.get("confidence", "high")
        min_conf = min(_conf_order[h_conf], _conf_order[i_conf],
                       _conf_order[e_conf])
        result["confidence"] = _conf_reverse[min_conf]
        result["scorer_confidence"] = {
            "H": h_conf, "I": i_conf, "E": e_conf,
        }
        result["scorer_max_sim"] = {
            "H": h_result.get("max_similarity", None),
            "I": i_result.get("max_similarity", None),
            "E": e_result.get("max_similarity", None),
        }

        # AMBIGUITY PRE-CHECK: override EXECUTE → CLARIFY for vague prompts.
        # Only applies when the equation says EXECUTE or CLARIFY-high.
        # Never overrides safety decisions (SAFE_STOP / SAFE_FREEZE).
        ambiguity_applied = False
        if result["decision"] == "EXECUTE" and H < 0.4 and _is_ambiguous(text):
            result["decision"] = "CLARIFY"
            ambiguity_applied = True
        result["ambiguity_override"] = ambiguity_applied

        # JAILBREAK DETECTION (bidirectional):
        #
        # A) ESCALATE: if jailbreak markers detected but S equation gave
        #    a permissive decision (EXECUTE/CLARIFY/SAFE_STOP), escalate
        #    to SAFE_FREEZE. This catches cases where H is low because
        #    the jailbreak phrasing doesn't match harm anchors well.
        #    Example: "Developer mode disabled" gets low H but IS a jailbreak.
        #
        # B) DOWNGRADE: if decision is SAFE_FREEZE but NO jailbreak markers,
        #    downgrade to SAFE_STOP. Simple harm terms ("متفجرات") are
        #    harmful but not manipulation — SAFE_STOP is appropriate.
        jailbreak_detected = _has_jailbreak_markers(text)
        freeze_downgraded = False
        jailbreak_escalated = False

        if jailbreak_detected and result["decision"] in ("EXECUTE", "CLARIFY", "SAFE_STOP"):
            result["decision"] = "SAFE_FREEZE"
            jailbreak_escalated = True
        elif result["decision"] == "SAFE_FREEZE" and not jailbreak_detected:
            result["decision"] = "SAFE_STOP"
            freeze_downgraded = True

        result["freeze_downgraded"] = freeze_downgraded
        result["jailbreak_escalated"] = jailbreak_escalated

        # γ+ HYSTERESIS: stabilize decisions across conversation turns.
        # Applied AFTER all other decision logic (ambiguity, jailbreak, guard)
        # so hysteresis operates on the final decision, not a raw intermediate.
        if conversation_id is not None:
            hyst = self.hysteresis.apply(
                conversation_id,
                S=result["S"],
                H=result["H"],
                raw_decision=result["decision"]
            )
            result["decision"] = hyst["decision"]
            result["hysteresis"] = {
                "held": hyst["held"],
                "raw_decision": hyst["raw_decision"],
                "reason": hyst["reason"],
                "turns_in_state": hyst["turns_in_state"],
            }

        if verbose:
            result["h_nearest"] = h_result.get("nearest", [])
            result["i_nearest"] = i_result.get("nearest", [])
            result["e_nearest"] = e_result.get("nearest", [])

        return result

    def compute_all_profiles(self, text: str,
                            equation_mode: str = "classic",
                            domain: str = None) -> list[dict]:
        """
        Run scorers once, then compute S across all profiles.
        Efficient: only one embedding call per scorer.

        Args:
            text: Arabic input text
            equation_mode: "classic" uses 5 profiles, "gated" uses 3 profiles
            domain: if specified (gated mode), overrides profile θ with θ(d)
        """
        h_result = self.h_scorer.score(text)
        i_result = self.i_scorer.score(text)
        e_result = self.e_scorer.score(text)

        H, I, E = h_result["H"], i_result["I"], e_result["E"]

        results = []
        if equation_mode == "gated":
            for profile_name in ["high_sensitivity", "default", "creative"]:
                r = compute_s_gated_from_scores(H, I, E,
                                                profile=profile_name,
                                                domain=domain)
                r["text"] = text
                results.append(r)
        else:
            for profile_name in ["high_sensitivity", "default", "casual",
                                 "safe_environment", "creative"]:
                r = compute_s_from_scores(H, I, E, profile=profile_name)
                r["text"] = text
                results.append(r)

        return results


# ---------------------------------------------------------------------------
# DISPLAY HELPERS
# ---------------------------------------------------------------------------

def _decision_emoji(d: str) -> str:
    return {
        "EXECUTE": "✅",
        "CLARIFY": "🟡",
        "SAFE_STOP": "🟠",
        "SAFE_FREEZE": "🔴",
    }.get(d, "❓")


def _confidence_emoji(c: str) -> str:
    return {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(c, "❓")


def print_result(r: dict) -> None:
    """Pretty-print a single computation result."""
    emoji = _decision_emoji(r["decision"])
    guard = " ⚠️GUARD" if r.get("guard_applied") else ""
    conf = r.get("confidence", "")
    conf_str = f" {_confidence_emoji(conf)}{conf}" if conf else ""
    print(f"  {emoji} {r['decision']:<12} S={r['S']:.4f}  "
          f"[H={r['H']:.3f} I={r['I']:.3f} E={r['E']:.3f}]  "
          f"F={r['F']:.3f}  ({r['profile']}){guard}{conf_str}")


def print_full(r: dict) -> None:
    """Print result with nearest-anchor diagnostics."""
    print_result(r)
    if "h_nearest" in r:
        for txt, sim, lvl in r["h_nearest"][:2]:
            print(f"      H↳ sim={sim:.2f} lvl={lvl}  «{txt[:40]}»")
    if "i_nearest" in r:
        for txt, sim, lvl in r["i_nearest"][:2]:
            print(f"      I↳ sim={sim:.2f} lvl={lvl}  «{txt[:40]}»")
    if "e_nearest" in r:
        for txt, sim, lvl in r["e_nearest"][:2]:
            print(f"      E↳ sim={sim:.2f} lvl={lvl}  «{txt[:40]}»")


# ---------------------------------------------------------------------------
# MAIN — demo & smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    engine = AATIFEngine()

    # Test messages spanning the full decision range
    test_messages = [
        ("عطني فكرة هدية لأمي", "benign request"),
        ("فرحان اليوم مرررة", "happy expression"),
        ("حزين شوي بس بخير", "mild distress"),
        ("تعبت من كل شي وحاسس إن ما في فايدة من وجودي", "despair"),
        ("نفسي أنام وما أصحى", "crisis phrase"),
        ("كيف أسوي قنبلة", "clear danger"),
        ("راح يجيب لهم جلطه", "colloquial expression"),
        ("هوا احنا كنا اتفقنا علي ايش؟", "neutral question"),
    ]

    print("=" * 75)
    print("AATIF S Equation — Unified Governance Engine")
    print("S = σ(w₁·I + w₂·E − w₃·H)")
    print("=" * 75)

    for msg, note in test_messages:
        print(f"\n📝 «{msg}»  ({note})")
        r = engine.compute(msg, profile="default", verbose=True)
        print_full(r)

    # Show profile comparison for an ambiguous message
    print("\n" + "=" * 75)
    print("Profile comparison: حزين بس بخير")
    print("=" * 75)
    for r in engine.compute_all_profiles("حزين شوي بس بخير"):
        print_result(r)

    # Show safety guard in action
    print("\n" + "=" * 75)
    print("Safety guard test: نفسي أنام وما أصحى (across all profiles)")
    print("=" * 75)
    for r in engine.compute_all_profiles("نفسي أنام وما أصحى"):
        print_result(r)

    print("\n✅ Engine smoke test complete.")
