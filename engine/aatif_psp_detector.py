"""
AATIF PSP Detector — FN#070 Possibility Space Preservation

Architecture: B-prime (B')
─────────────────────────────────────────────────────────────────
ConversationManager  →  pure storage (prior live paths, rejected paths)
PSPDetector          →  observational (outputs PSPReading + evidence)
ResponseShaper       →  stylistic (applies domain psp_profile via G_eff)
OutputGate Layer 7   →  corrective (monitors for premature closure)

Critical Design Rule (Single Mind):
  Only GovernanceEquation makes SAFETY decisions. FN#070 is STYLISTIC,
  NOT safety. PSPDetector never touches S, H, θ, or the GovernanceEquation.
  It binds through B5 (Behaviour), NOT B6 (Safety). It says "this turn is a
  decision point with closure_risk 0.7 and three live paths." It decides
  nothing about whether a request is allowed.

  psp_mode is NOT computed here. It comes from domain_config.psp_profile
  (a config lookup, exactly as θ comes from the D parameter). PSPDetector
  may compute closure_risk, but must not decide psp_mode.

Violation model:
  A violation is *unprompted premature single-path closure when alternatives
  exist*. Prompted closure (the user explicitly asks for a recommendation)
  is allowed and is NOT a violation.

Sparse Activation:
  Most turns are not decision points. A fast-path skip returns a cheap
  non-decision reading whenever deterministic signals are confident
  (deterministic_not_decision_confidence >= 0.95), so embeddings only run
  when the deterministic and context tiers are ambiguous.

Design consensus: Claude × ChatGPT, 2026-06-30 (FN070_DESIGN_CONSENSUS.md)
Field Note: FN#070 (Possibility Space Preservation)

"خلينا نحصر الخيارات الواقعية، ونوضح مزايا وعيوب كل واحد، والقرار النهائي لك."
"Let us bound the realistic options and show the trade-offs — the final choice is yours."

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Any

try:  # pragma: no cover — import shim for both package and flat layouts
    from aatif_arabic_utils import normalize_arabic
except Exception:  # pragma: no cover
    def normalize_arabic(text: str) -> str:
        return text.lower()


# ═══════════════════════════════════════════════════════════════
#  Feature Flags  (FN#070 ships OFF by default)
# ═══════════════════════════════════════════════════════════════

PSP_ENABLED = False              # master switch for the PSP pipeline
PSP_GATE_CHECK_ENABLED = False   # OutputGate Layer 7 PSP check
PSP_GATE_MODE = "monitor"        # "monitor" (log only) or "block" (regenerate)


# ═══════════════════════════════════════════════════════════════
#  Constants — calibration values
# ═══════════════════════════════════════════════════════════════

FAST_PATH_SKIP_THRESHOLD = 0.95   # skip embeddings when this confident it is NOT a decision
DECISION_CONFIDENCE_THRESHOLD = 0.5  # is_decision_point when confidence crosses this

# Bounded set — system proposes, human closes (Schwartz paradox: cap the menu)
BOUNDED_SIMPLE = 2
BOUNDED_DEFAULT = 3
BOUNDED_HIGH_STAKES = 4   # within the consensus 3–4 range
BOUNDED_CREATIVE = 5
BOUNDED_HARD_MAX = 5      # hard ceiling without explicit user request

# closure_risk base by domain psp_profile (0.0 = open, 1.0 = collapsed)
PROFILE_CLOSURE_BASE = {
    "high":     0.70,
    "medium":   0.40,
    "adaptive": 0.30,   # creative
    "low":      0.10,
}
HIGH_STAKES_CLOSURE_BONUS = 0.20
# Prompted closure is sanctioned, so the *premature*-closure risk drops.
REQUESTED_CLOSURE_DAMPING = 0.5
TRADEOFF_REQUIRED_THRESHOLD = 0.5   # tradeoffs required when closure_risk exceeds this

# Domain → psp_profile (config lookup, NOT detector computation; mirrors θ-from-D)
PSP_PROFILE_BY_DOMAIN = {
    "healthcare": "high",
    "medical":    "high",
    "legal":      "high",
    "finance":    "high",
    "education":  "high",
    "general":    "medium",
    "creative":   "adaptive",
}
DEFAULT_PSP_PROFILE = "medium"


# ═══════════════════════════════════════════════════════════════
#  Decision-point markers — deterministic tier (tier 1)
# ═══════════════════════════════════════════════════════════════
#
#  A decision point is a turn where the human is choosing among paths.
#  These are the cheap, high-precision signals checked first.

DECISION_MARKERS_AR = [
    "استخير", "استخاره",           # Istikharah — seeking divine guidance
    "استشير", "مشوره", "تنصحني", "نصيحتك", "تنصحوني",
    "ايش الافضل", "وش الافضل", "ايش الانسب", "وش الانسب",
    "ايش تنصح", "وش تنصح", "ايش رايك", "وش رايك",
    "محتار", "محتاره", "مو عارف اختار", "ما ادري اختار",
    "اتوكل", "اختار", "اقرر", "اخذ قرار", "اتخذ قرار",
    "بين خيارين", "بين خيارات", "اي وحده", "اي واحد", "اي خيار",
    "مع ولا ضد", "اسوي ولا",
]

DECISION_MARKERS_EN = [
    "should i", "shall i", "which one", "which option", "which is better",
    "what's best", "what is best", "whats best", "what's the best", "what is the best",
    "help me decide", "help me choose", "hard to decide", "can't decide", "cant decide",
    "pros and cons", "trade-offs", "tradeoffs", "trade offs",
    "torn between", "deciding between", "choosing between", "stuck between",
    "what would you recommend", "what do you recommend", "do you recommend",
    "or should i", "is it better to",
]

# ═══════════════════════════════════════════════════════════════
#  Closure-request markers — the user explicitly asks us to close
# ═══════════════════════════════════════════════════════════════
#
#  When present, closure is PROMPTED → allowed → not a violation.

CLOSURE_REQUEST_MARKERS_AR = [
    "اختار لي", "اختر لي", "قرر لي", "قرر عني",
    "قل لي وش اسوي", "قول لي وش اسوي", "قل لي ايش اسوي",
    "توصيتك", "توصيتك المباشره", "نصيحتك المباشره",
    "خلاص قرر", "بدون لف", "وحده بس", "خيار واحد", "اعطني واحد",
    "وش الافضل ليي بالضبط",
]

CLOSURE_REQUEST_MARKERS_EN = [
    "just tell me", "just pick", "pick one for me", "pick one",
    "choose for me", "decide for me", "make the decision",
    "what should i do", "give me your recommendation", "give me one",
    "tell me which one to", "just give me the best", "your top pick",
    "don't list", "dont list", "no options", "one answer",
]

# ═══════════════════════════════════════════════════════════════
#  Factual / non-decision markers — fast-path skip signals (negatives)
# ═══════════════════════════════════════════════════════════════

FACTUAL_MARKERS_AR = [
    "ما هو", "ما هي", "ما معنى", "وش معنى", "وش يعني", "ايش معنى",
    "كم عدد", "كم سعر", "كم عمر", "متى", "وين", "فين", "من هو", "من هي",
    "عرف", "اشرح", "وضح لي", "كيف يعمل", "كيف يشتغل", "ليش", "لماذا",
]

FACTUAL_MARKERS_EN = [
    "what is", "what are", "what's the", "whats the", "what does",
    "who is", "who was", "who are", "when did", "when is", "when was",
    "where is", "where are", "how many", "how much is", "how does",
    "define", "explain", "tell me about", "what time", "list the",
]

GREETING_MARKERS = [
    "hello", "hi ", "hey", "thanks", "thank you", "good morning",
    "مرحبا", "السلام عليكم", "هلا", "صباح الخير", "مساء الخير", "شكرا",
]

# Enumeration connectors — used to detect human-introduced live paths
OR_CONNECTORS_EN = [" or ", " versus ", " vs ", " vs. ", " either "]
OR_CONNECTORS_AR = [" او ", " ولا ", " أو "]
NEW_PATH_MARKERS_EN = ["what about", "how about", "what if i", "could i also", "or maybe"]
NEW_PATH_MARKERS_AR = ["وش رايك في", "وش رايك بـ", "ماذا عن", "ماذا لو", "طيب لو", "وش لو"]


# ═══════════════════════════════════════════════════════════════
#  Data Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class LivePath:
    """A single live alternative that should remain on the table."""
    label: str
    summary: str = ""
    tradeoff: Optional[str] = None   # benefit/limitation — required when closure_risk > 0.5


@dataclass
class PSPReading:
    """
    Output of PSPDetector.detect() — observational, STYLISTIC, NOT safety.

    Notice what is NOT here: psp_mode. psp_mode comes from
    domain_config.psp_profile, never from the detector.
    """
    is_decision_point: bool
    decision_confidence: float           # [0,1] confidence this is a decision point
    closure_risk: float                  # 0.0 = open space, 1.0 = collapsed to one path
    live_paths: List[LivePath] = field(default_factory=list)
    bounded_count: int = 0               # recommended number of alternatives to present
    user_requested_closure: bool = False # did the human explicitly ask us to close?
    evidence: List[str] = field(default_factory=list)

    @property
    def tradeoffs_required(self) -> bool:
        """When closure_risk is high, each live path must carry a trade-off."""
        return self.closure_risk > TRADEOFF_REQUIRED_THRESHOLD


@dataclass
class PSPContext:
    """
    Pure storage of prior decision context. Owns NO logic.

    Mirrors the ConversationManager pattern: storage only. The detector
    reads it to keep the live-path set *observationally mutable* across turns.
    """
    live_paths: List[LivePath] = field(default_factory=list)
    rejected_paths: List[str] = field(default_factory=list)
    prior_decision_active: bool = False


@dataclass
class DomainPSPConfig:
    """
    Domain config carrying psp_profile (NOT θ-analogous, purely stylistic).

    psp_profile is looked up from the domain, exactly as θ is looked up from
    the D parameter. The detector READS this; it never computes it.
    """
    domain: str = "general"
    psp_profile: str = DEFAULT_PSP_PROFILE
    high_stakes: bool = False
    complexity: Optional[str] = None   # "simple" | "default" | "high_stakes" | "creative"

    @classmethod
    def for_domain(cls, domain: str) -> "DomainPSPConfig":
        profile = PSP_PROFILE_BY_DOMAIN.get((domain or "general").lower(),
                                            DEFAULT_PSP_PROFILE)
        return cls(
            domain=domain or "general",
            psp_profile=profile,
            high_stakes=(profile == "high"),
        )


# ═══════════════════════════════════════════════════════════════
#  Small duck-typed accessors (turn_features / context / config may be
#  dicts, dataclasses, or plain strings)
# ═══════════════════════════════════════════════════════════════

def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _text_of(turn_features: Any) -> str:
    if turn_features is None:
        return ""
    if isinstance(turn_features, str):
        return turn_features
    return _get(turn_features, "text", "") or ""


# ═══════════════════════════════════════════════════════════════
#  PSPDetector — observational, STYLISTIC, NOT safety
# ═══════════════════════════════════════════════════════════════

class PSPDetector:
    """
    Three-tier decision-point detection with sparse activation.

      Tier 1 — deterministic markers (cheap, high precision, always run)
      Tier 2 — embeddings           (only when tiers 1 & 3 are ambiguous)
      Tier 3 — context              (prior active decision in this thread)

    The detector outputs a PSPReading. It does not generate response content,
    does not author trade-offs, and does not decide psp_mode. It keeps the
    bounded live-path set, updating it when the human introduces a new path.

    The optional `embedder` enables Tier 2. It must expose
    `decision_similarity(text) -> float` in [0,1]. When None (e.g. CI without
    Ollama), Tier 2 is skipped and detection rests on tiers 1 and 3 — keeping
    the module fully testable offline.
    """

    def __init__(self, embedder: Any = None,
                 fast_path_threshold: float = FAST_PATH_SKIP_THRESHOLD,
                 decision_threshold: float = DECISION_CONFIDENCE_THRESHOLD):
        self.embedder = embedder
        self.fast_path_threshold = fast_path_threshold
        self.decision_threshold = decision_threshold

    # ── Public API ──────────────────────────────────────────────

    def detect(self, turn_features: Any,
               prior_context: Any = None,
               domain_config: Any = None) -> PSPReading:
        """
        Consume one turn → PSPReading.

        Parameters
        ----------
        turn_features : str | dict | object
            The user turn. A bare string, or anything exposing ``text``
            (and optionally ``sub_intents``, ``complexity``, ``high_stakes``).
        prior_context : PSPContext | dict | None
            Prior decision context for live-path continuity.
        domain_config : DomainPSPConfig | dict | None
            Domain config carrying ``psp_profile``. Looked up, never computed.
        """
        text = _text_of(turn_features)
        norm, low = self._prep(text)
        config = self._resolve_config(domain_config)

        evidence: List[str] = []

        # ── Tier 1: deterministic markers ───────────────────────
        decision_hits = self._find(low, norm, DECISION_MARKERS_EN, DECISION_MARKERS_AR)
        closure_hits = self._find(low, norm, CLOSURE_REQUEST_MARKERS_EN,
                                  CLOSURE_REQUEST_MARKERS_AR)
        factual_hits = self._find(low, norm, FACTUAL_MARKERS_EN, FACTUAL_MARKERS_AR)
        greeting_hit = any(g in low or normalize_arabic(g) in norm
                           for g in GREETING_MARKERS)

        user_requested_closure = len(closure_hits) > 0

        not_decision_conf = self._deterministic_not_decision_confidence(
            text, decision_hits, factual_hits, greeting_hit
        )

        # ── Sparse Activation: fast-path skip ───────────────────
        if not_decision_conf >= self.fast_path_threshold:
            evidence.append(
                f"fast_path_skip: not_decision_conf={not_decision_conf:.2f} "
                f">= {self.fast_path_threshold} (deterministic, embeddings skipped)"
            )
            if factual_hits:
                evidence.append(f"factual_markers={factual_hits[:3]}")
            if greeting_hit:
                evidence.append("greeting")
            return PSPReading(
                is_decision_point=False,
                decision_confidence=0.0,
                closure_risk=0.0,
                live_paths=[],
                bounded_count=0,
                user_requested_closure=user_requested_closure,
                evidence=evidence,
            )

        # ── Build decision confidence from all three tiers ──────
        confidence = 0.0
        if decision_hits:
            confidence = min(0.60 + 0.15 * len(decision_hits), 0.95)
            evidence.append(f"decision_markers={decision_hits[:4]}")

        # Tier 3: context — an active prior decision keeps PSP live
        if _get(prior_context, "prior_decision_active", False) or \
                _get(prior_context, "live_paths", None):
            confidence = max(confidence, 0.70)
            evidence.append("context: prior decision active")

        # Tier 2: embeddings — only reached when deterministic was inconclusive
        if confidence < self.decision_threshold and self.embedder is not None:
            sim = self._embedding_signal(text)
            if sim is not None:
                confidence = max(confidence, sim)
                evidence.append(f"embedding_decision_similarity={sim:.2f}")

        is_decision_point = confidence >= self.decision_threshold

        if not is_decision_point:
            evidence.append(
                f"not a decision point (confidence={confidence:.2f} "
                f"< {self.decision_threshold})"
            )
            return PSPReading(
                is_decision_point=False,
                decision_confidence=round(confidence, 3),
                closure_risk=0.0,
                live_paths=[],
                bounded_count=0,
                user_requested_closure=user_requested_closure,
                evidence=evidence,
            )

        # ── Decision point confirmed — build the reading ────────
        live_paths = self._build_live_paths(text, norm, low, prior_context)
        bounded_count = self._bounded_count(config, turn_features)
        closure_risk = self._closure_risk(config, user_requested_closure)

        evidence.append(f"psp_profile={config.psp_profile} (config lookup)")
        evidence.append(f"closure_risk={closure_risk:.2f}")
        evidence.append(f"bounded_count={bounded_count}")
        if user_requested_closure:
            evidence.append(
                f"PROMPTED closure requested {closure_hits[:2]} — "
                "closure is allowed, not a violation"
            )
        if live_paths:
            evidence.append(f"live_paths={[p.label for p in live_paths]}")
        if closure_risk > TRADEOFF_REQUIRED_THRESHOLD:
            evidence.append("tradeoffs_required (closure_risk > 0.5)")

        return PSPReading(
            is_decision_point=True,
            decision_confidence=round(confidence, 3),
            closure_risk=round(closure_risk, 3),
            live_paths=live_paths,
            bounded_count=bounded_count,
            user_requested_closure=user_requested_closure,
            evidence=evidence,
        )

    def detect_multi(self, turn_features: Any,
                     prior_context: Any = None,
                     domain_config: Any = None) -> List[PSPReading]:
        """
        Per-sub-intent PSP (FN#036 first, PSP per resolved sub-intent).

        FN#036 Multi-Intent Resolution runs upstream and hands us the resolved
        sub-intents via ``turn_features.sub_intents``. PSP then applies
        independently per sub-intent — a response can answer a factual
        sub-intent directly while keeping bounded alternatives open for a
        decision sub-intent.

        Returns one PSPReading per sub-intent. Falls back to ``[detect(...)]``
        when there are no sub-intents.
        """
        sub_intents = _get(turn_features, "sub_intents", None)
        if not sub_intents:
            return [self.detect(turn_features, prior_context, domain_config)]
        return [self.detect(si, prior_context, domain_config) for si in sub_intents]

    # ── Tier-1 helpers ──────────────────────────────────────────

    @staticmethod
    def _prep(text: str) -> tuple:
        """Return (normalized_arabic, lowercased) views of the text."""
        return normalize_arabic(text), text.lower()

    @staticmethod
    def _find(low: str, norm: str,
              markers_en: List[str], markers_ar: List[str]) -> List[str]:
        """Markers present in the text — EN matched on lowercase, AR on normalized."""
        hits = [m for m in markers_en if m in low]
        hits += [m for m in markers_ar if normalize_arabic(m) in norm]
        return hits

    def _deterministic_not_decision_confidence(self, text: str,
                                               decision_hits: List[str],
                                               factual_hits: List[str],
                                               greeting_hit: bool) -> float:
        """
        Confidence that this turn is NOT a decision point, from deterministic
        signals only. Drives the Sparse Activation fast-path.

        Any decision marker collapses this confidence — we must look closer.
        """
        if decision_hits:
            return 0.10
        if greeting_hit and not factual_hits:
            return 0.97
        if factual_hits:
            return 0.96
        # Very short non-question utterances are almost never decision points.
        if len(text.strip()) <= 12 and "?" not in text:
            return 0.95
        # No decision and no clear factual signal — stay ambiguous so the
        # embedding/context tiers get a chance.
        return 0.60

    # ── Tier-2 (embeddings) ─────────────────────────────────────

    def _embedding_signal(self, text: str) -> Optional[float]:
        """Decision-point similarity from the embedder, if one is wired in."""
        if self.embedder is None:
            return None
        fn = getattr(self.embedder, "decision_similarity", None)
        if fn is None:
            return None
        try:
            val = float(fn(text))
        except Exception:  # pragma: no cover — defensive
            return None
        return max(0.0, min(1.0, val))

    # ── Reading construction ────────────────────────────────────

    def _resolve_config(self, domain_config: Any) -> DomainPSPConfig:
        if isinstance(domain_config, DomainPSPConfig):
            return domain_config
        if domain_config is None:
            return DomainPSPConfig()
        # dict or arbitrary object — read psp_profile / domain / flags
        profile = _get(domain_config, "psp_profile", None)
        domain = _get(domain_config, "domain", "general")
        if profile is None:
            return DomainPSPConfig.for_domain(domain)
        return DomainPSPConfig(
            domain=domain or "general",
            psp_profile=profile,
            high_stakes=bool(_get(domain_config, "high_stakes", profile == "high")),
            complexity=_get(domain_config, "complexity", None),
        )

    def _bounded_count(self, config: DomainPSPConfig, turn_features: Any) -> int:
        """
        How many alternatives to present — system proposes, human closes.

        Complexity precedence: explicit turn hint > explicit config hint >
        derived from psp_profile. Always capped at the hard max (5).
        """
        complexity = (_get(turn_features, "complexity", None)
                      or config.complexity)
        if complexity is None:
            if config.psp_profile == "adaptive":      # creative
                complexity = "creative"
            elif config.high_stakes or config.psp_profile == "high":
                complexity = "high_stakes"
            else:
                complexity = "default"

        count = {
            "simple":      BOUNDED_SIMPLE,
            "default":     BOUNDED_DEFAULT,
            "high_stakes": BOUNDED_HIGH_STAKES,
            "creative":    BOUNDED_CREATIVE,
        }.get(complexity, BOUNDED_DEFAULT)

        return min(count, BOUNDED_HARD_MAX)

    def _closure_risk(self, config: DomainPSPConfig,
                      user_requested_closure: bool) -> float:
        """
        Risk that the response collapses to a single path. Higher in
        high-stakes domains; damped when the human PROMPTED closure (because
        prompted closure is sanctioned, not a violation).

        Observational only — feeds nothing into H, θ, or S.
        """
        base = PROFILE_CLOSURE_BASE.get(config.psp_profile, 0.40)
        if config.high_stakes:
            base += HIGH_STAKES_CLOSURE_BONUS
        if user_requested_closure:
            base *= REQUESTED_CLOSURE_DAMPING
        return max(0.0, min(1.0, base))

    def _build_live_paths(self, text: str, norm: str, low: str,
                          prior_context: Any) -> List[LivePath]:
        """
        Keep the live-path set observationally mutable.

        Start from prior paths, drop anything the human has rejected, then
        append any new path the human introduced this turn. Capped at the
        hard max so the menu never silently exceeds the bound.
        """
        rejected = set(_get(prior_context, "rejected_paths", []) or [])

        paths: List[LivePath] = []
        for p in (_get(prior_context, "live_paths", []) or []):
            label = p.label if isinstance(p, LivePath) else str(p)
            if label in rejected:
                continue
            paths.append(p if isinstance(p, LivePath) else LivePath(label=label))

        existing = {p.label.strip().lower() for p in paths}
        for new_label in self._extract_user_paths(text, norm, low):
            key = new_label.strip().lower()
            if key and key not in existing and new_label not in rejected:
                paths.append(LivePath(label=new_label, summary="(introduced by user)"))
                existing.add(key)

        return paths[:BOUNDED_HARD_MAX]

    @staticmethod
    def _extract_user_paths(text: str, norm: str, low: str) -> List[str]:
        """
        Lightweight extraction of human-introduced options.

        Two shapes: an explicit "what about X" addition, and an "X or Y"
        enumeration. Deliberately conservative — the detector tracks paths,
        it does not invent domain content.
        """
        labels: List[str] = []

        # Shape 1: "what about X" / "ماذا عن X" — a single newly raised path
        for marker in NEW_PATH_MARKERS_EN:
            idx = low.find(marker)
            if idx >= 0:
                tail = text[idx + len(marker):].strip(" ?؟.،,")
                if 0 < len(tail) <= 40:
                    labels.append(tail)
        for marker in NEW_PATH_MARKERS_AR:
            nmarker = normalize_arabic(marker)
            idx = norm.find(nmarker)
            if idx >= 0:
                tail = text[idx + len(marker):].strip(" ?؟.،,")
                if 0 < len(tail) <= 40:
                    labels.append(tail)

        # Shape 2: "A or B (or C)" enumeration
        connector = None
        for c in OR_CONNECTORS_EN:
            if c in low:
                connector = c
                break
        if connector:
            parts = [p.strip(" ?؟.،,") for p in low.split(connector)]
            for p in parts:
                # keep short, content-like fragments only
                if 0 < len(p) <= 30 and not any(
                    p.startswith(q) for q in ("what", "which", "should", "is it", "how")
                ):
                    labels.append(p)

        # dedup preserving order
        seen, out = set(), []
        for lab in labels:
            k = lab.lower()
            if lab and k not in seen:
                seen.add(k)
                out.append(lab)
        return out


# ═══════════════════════════════════════════════════════════════
#  Self-test
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":  # pragma: no cover
    print("=== PSPDetector Self-Test ===\n")
    det = PSPDetector()

    samples = [
        ("ما هو عاصمة فرنسا؟", "general"),               # factual → fast-path skip
        ("مرحبا", "general"),                            # greeting → fast-path skip
        ("محتار بين تخصص الطب والهندسة، ايش تنصحني؟", "education"),  # decision (AR)
        ("Should I take the job offer or stay at my current company?", "general"),
        ("I'm torn between surgery and physical therapy — what's best?", "healthcare"),
        ("Just tell me which one to pick.", "general"),  # prompted closure
    ]

    print(f"{'decision':<9} {'conf':<6} {'closure':<8} {'paths':<6} {'reqClose':<9} text")
    print("-" * 100)
    for text, domain in samples:
        cfg = DomainPSPConfig.for_domain(domain)
        r = det.detect(text, domain_config=cfg)
        print(f"{str(r.is_decision_point):<9} {r.decision_confidence:<6.2f} "
              f"{r.closure_risk:<8.2f} {r.bounded_count:<6} "
              f"{str(r.user_requested_closure):<9} {text[:48]}")
    print("\nDone.")
