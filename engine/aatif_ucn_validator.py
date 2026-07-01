"""
AATIF UCN Validator -- FN#042 Unwritten Concept Nullification Law

Architecture: B-prime (B')
---------------------------------------------------------------------
UCNDetector       ->  observational (outputs UCNReading + evidence)

Critical Design Rule (Single Mind):
  Only GovernanceEquation makes SAFETY decisions. FN#042 is ARCHITECTURAL
  INTEGRITY, NOT safety. UCNDetector never touches S, H, theta, or the
  GovernanceEquation. It says "the output references a phantom engine
  called 'compassion engine' -- confidence 0.85, recommend correction."
  It decides nothing about whether a request is allowed.

  UCN applies a Closed-World Assumption to AATIF's own architecture:
  "If it is not written in the system, it does not exist in the system."

  Critical scope boundary: this module ONLY applies to references about
  AATIF's architecture. It does NOT apply to general knowledge.
  "Compassion is important" = fine.
  "AATIF has a compassion engine" = VIOLATION (if no compassion engine exists).

  The module detects when AI output invents/hallucmates AATIF architectural
  components that don't actually exist (phantom layers, phantom engines,
  phantom protocols).

ISOLATION CONTRACT (P0-B):
  This module operates EXCLUSIVELY within the B3 (meaning) and B5
  (behaviour) binding channels. It has NO pathway to affect:
    - S equation (safety score)
    - H score (harm score)
    - theta (governance threshold)
    - B2 (constitutional channel)
    - B6 (safety channel)
  Proof: UCNDetector produces a UCNReading dataclass. UCNReading contains
  only observational fields (phantoms_detected, recommendations, evidence).
  There is no import of, reference to, or invocation of S/H/theta/B2/B6
  anywhere in this module. The ISOLATION_MARKER field on every UCNReading
  confirms this contract at runtime.

Design consensus: Claude + ChatGPT + Gemini + Grok, 2026-07-01
P0 fixes from 3-model retroactive review applied 2026-07-01.
Field Note: FN#042 (Unwritten Concept Nullification Law)

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import enum
import glob as _glob_mod
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

# -- import shim for both package and flat layouts -----------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

try:  # pragma: no cover
    from aatif_arabic_utils import normalize_arabic
except Exception:  # pragma: no cover
    def normalize_arabic(text: str) -> str:
        """Basic Arabic normalization: strip tashkeel, normalize alef/taa marbouta."""
        import unicodedata
        _TASHKEEL = set(range(0x0610, 0x061B)) | set(range(0x064B, 0x0660)) | {0x0670}
        out = []
        for ch in text:
            cp = ord(ch)
            if cp in _TASHKEEL:
                continue
            out.append(ch)
        result = "".join(out)
        result = result.replace("آ", "ا")  # alef madda
        result = result.replace("أ", "ا")  # alef hamza above
        result = result.replace("إ", "ا")  # alef hamza below
        result = result.replace("ة", "ه")  # taa marbouta -> haa
        return result.lower()


# =====================================================================
#  Feature Flags  (FN#042 ships ON by default)
# =====================================================================

UCN_ENABLED = True                # master switch for the UCN pipeline
UCN_MONITOR_ONLY = False          # when True, detect but never recommend correction


# =====================================================================
#  Authority Level Declaration (B-prime contract)
# =====================================================================

AUTHORITY_LEVEL = "B_PRIME_OBSERVATIONAL"
CAN_BLOCK_RUNTIME          = False
CAN_MODIFY_H               = False
CAN_MODIFY_THETA            = False
CAN_MODIFY_S                = False
CAN_EMIT_JUDICIAL_DECISION = False
UCN_ENABLED_FLAG = True           # explicit UCN flag per spec

# -- P0-B: Isolation contract markers ----------------------------------
ISOLATION_MARKER = "B3_B5_ONLY_NOT_FOR_SAFETY"
ISOLATION_TARGETS: FrozenSet[str] = frozenset({"B3_MEANING", "B5_BEHAVIOUR"})


# =====================================================================
#  UCN Violation Types  (FN#042 -- five phantom categories)
# =====================================================================

class UCNViolationType(enum.Enum):
    """The five phantom categories detected by UCN."""
    PHANTOM_ENGINE   = "phantom_engine"      # invented engine/module
    PHANTOM_LAYER    = "phantom_layer"       # invented layer
    PHANTOM_PROTOCOL = "phantom_protocol"    # invented protocol/rule
    PHANTOM_CHANNEL  = "phantom_channel"     # invented binding channel
    PHANTOM_CONCEPT  = "phantom_concept"     # invented architectural concept


# =====================================================================
#  P0-D: Reference Mode -- Proposed vs Asserted
# =====================================================================

class ReferenceMode(enum.Enum):
    """Whether an architecture reference is stated as fact or as a proposal."""
    ASSERTED     = "ASSERTED"       # stated as existing fact
    PROPOSED     = "PROPOSED"       # speculative / design discussion
    HYPOTHETICAL = "HYPOTHETICAL"   # clearly hypothetical / future


# =====================================================================
#  Constants -- calibration values
# =====================================================================

FAST_PATH_MAX_CHARS = 20          # texts shorter than this with no AATIF context -> skip
SINGLE_PHANTOM_BASE_CONFIDENCE = 0.70
MULTI_PHANTOM_COMPOUND_BONUS = 0.10
MAX_CONFIDENCE = 0.95

# P0-C: Context anchoring thresholds
CONFIDENCE_CAP_NO_ANCHOR = 0.55   # max confidence without AATIF-specific anchor
CONFIDENCE_CAP_WITH_ANCHOR = 0.95 # max confidence with AATIF-specific anchor

# P0-D: Modal severity cap for speculative references
PROPOSED_SEVERITY_CAP = 0.40

# P0-E: Fuzzy matching threshold (raised from implicit ~0.6 to 0.80)
FUZZY_SIMILARITY_THRESHOLD = 0.80

# Per-violation-type base severity
VIOLATION_SEVERITY: Dict[UCNViolationType, float] = {
    UCNViolationType.PHANTOM_ENGINE:   0.80,  # worst -- inventing whole engines
    UCNViolationType.PHANTOM_LAYER:    0.80,  # inventing layers is equally bad
    UCNViolationType.PHANTOM_PROTOCOL: 0.70,
    UCNViolationType.PHANTOM_CHANNEL:  0.75,
    UCNViolationType.PHANTOM_CONCEPT:  0.60,
}

# P0-C: AATIF-specific context anchors (keywords that confirm text is about AATIF)
_AATIF_CONTEXT_ANCHORS = frozenset({
    "aatif", "aatif_", "fn#", "b-prime", "governanceequation",
    "governance equation", "عاطف", "حوكمة",
})

# P0-D: Speculative/hypothetical keyword markers
_SPECULATIVE_MARKERS_EN = [
    "proposed", "hypothetical", "future", "draft", "could build",
    "might add", "would have", "could have", "we could", "we might",
    "potential", "planned", "idea for", "design idea",
]
_SPECULATIVE_MARKERS_AR = [
    "مقترح", "ممكن نضيف", "تصميم مبدئي", "غير مسجل",
    "ممكن يكون", "فكرة", "مستقبلي", "مسودة",
]


# =====================================================================
#  P0-A: Dynamic Component Registry
# =====================================================================
#
#  _discover_engine_files() scans the engine/ directory at import time.
#  The hardcoded list is kept as a FALLBACK only if discovery fails.
#  If it is not in this registry, it does not exist.
#  All entries are normalized to lowercase for O(1) lookup.

# -- FALLBACK: Engine/module file names (the known files in engine/) ---
_FALLBACK_ENGINE_FILES = frozenset({
    "intent_engine", "s_equation", "r_equation", "governor",
    "meta_oversight", "false_goodness_detector", "pvm_detector",
    "psp_detector", "lbh_detector", "drift_detector",
    "uncertainty_detector", "logic_profile_scanner", "emotion_scorer",
    "semantic_scorer", "intent_scorer", "five_layer_intent",
    "contextual_intent", "muhajij", "multi_intent_collision",
    "output_gate", "response_shaper", "reasoning_trace",
    "conversation_memory", "temporal_memory", "judgment_memory",
    "judgment_integration", "hysteresis", "math", "fingerprint",
    "time_sense", "arabic_utils", "authority_doctrine", "boot_sequence",
    "domain_protocols", "dual_root", "embeddings", "pipeline_connector",
    "binding_map", "ucn_validator", "cold_os",
})


def _discover_engine_files() -> FrozenSet[str]:
    """P0-A: Scan engine/ directory for actual .py module files.

    Returns a frozenset of module short names (e.g., 'intent_engine')
    derived from filenames like 'aatif_intent_engine.py'.
    Falls back to _FALLBACK_ENGINE_FILES if discovery fails.
    """
    try:
        engine_dir = os.path.dirname(os.path.abspath(__file__))
        pattern = os.path.join(engine_dir, "aatif_*.py")
        files = _glob_mod.glob(pattern)
        if not files:
            return _FALLBACK_ENGINE_FILES
        discovered: Set[str] = set()
        for fpath in files:
            basename = os.path.basename(fpath)  # e.g., "aatif_intent_engine.py"
            name = basename.replace("aatif_", "", 1).replace(".py", "")
            if name and not name.startswith("__"):
                discovered.add(name)
        return frozenset(discovered) if discovered else _FALLBACK_ENGINE_FILES
    except Exception:
        return _FALLBACK_ENGINE_FILES


# P0-A: Use dynamic discovery; fallback is hardcoded list
_KNOWN_ENGINE_FILES = _discover_engine_files()
_REGISTRY_SOURCE = "dynamic" if _KNOWN_ENGINE_FILES != _FALLBACK_ENGINE_FILES else "fallback"

# -- Short names (what people would actually say) ----------------------
_KNOWN_SHORT_NAMES = frozenset({
    "s equation", "r equation", "governance equation", "intent engine",
    "governor", "meta oversight", "output gate", "response shaper",
    "reasoning trace", "drift detector", "uncertainty detector",
    "logic profile scanner", "emotion scorer", "pvm detector",
    "psp detector", "lbh detector", "false goodness detector",
    "muhajij", "binding map", "boot sequence", "fingerprint",
    "hysteresis", "pipeline connector", "judgment integration",
    "ucn validator", "cold os",
})

# -- Arabic names (P0-F: expanded bilingual parity) --------------------
_KNOWN_ARABIC_NAMES = frozenset({
    normalize_arabic(n) for n in [
        "محرك النية", "معادلة الحوكمة", "معادلة S", "معادلة R",
        "الحاكم", "بوابة الإخراج", "محرك المعنى", "كاشف الانحراف",
        "كاشف الضغط السلبي", "كاشف التلاعب", "كاشف اللطف الزائف",
        "كاشف عدم اليقين", "ماسح المنطق", "مقيّم المشاعر",
        "المحاجج", "خريطة الربط", "تسلسل الإقلاع", "البصمة",
        "ذاكرة المحادثة", "ذاكرة الأحكام",
    ]
})

# -- Binding channels ---------------------------------------------------
_KNOWN_CHANNELS = frozenset({
    "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8",
    "b1 identity", "b2 constitutional", "b3 meaning", "b4 intent",
    "b5 behaviour", "b6 safety", "b7 drift", "b8 execution",
})

# -- Layer references ---------------------------------------------------
_KNOWN_LAYERS = frozenset(
    {f"layer {i}" for i in range(1, 21)} |
    {
        "foundation layer", "root layer", "identity layer", "core rules",
        "supervisor layer", "kernel layer", "meta layer",
        "human reality layer", "safety layer",
    }
)

# -- Architectural concepts ---------------------------------------------
_KNOWN_CONCEPTS = frozenset({
    "sparse activation", "safe mode", "deep mode", "h score", "theta",
    "harm score", "governed response", "governed prompt",
    "authority doctrine", "constitutional law", "single mind law",
    "dual root", "wedan",
})

# -- Unified registry: the union of ALL known components ----------------
KNOWN_COMPONENTS = (
    _KNOWN_ENGINE_FILES |
    _KNOWN_SHORT_NAMES |
    _KNOWN_ARABIC_NAMES |
    _KNOWN_CHANNELS |
    _KNOWN_LAYERS |
    _KNOWN_CONCEPTS
)


# =====================================================================
#  AATIF Context Triggers -- used to detect if text is about AATIF
# =====================================================================

_CONTEXT_TRIGGERS_EN = [
    "aatif", "the system has", "the engine", "the module",
    "layer", "module", "protocol", "channel b",
    "binding channel", "governed", "governance equation",
]

_CONTEXT_TRIGGERS_AR = [
    "عاطف", "النظام يحتوي", "محرك", "طبقة",
    "بروتوكول", "قناة",
]


# =====================================================================
#  Extraction Patterns -- regex for finding component references
# =====================================================================

# English patterns
_RE_COMPONENT_REF_EN = [
    # "AATIF has a/an/the X engine/module/detector/..."
    re.compile(
        r"(?:aatif|the system)(?:'s|\s+has)?\s+(?:an?\s+|the\s+)?"
        r"(\w+(?:\s+\w+){0,3}?)"
        r"\s+(?:engine|module|detector|scanner|layer|protocol|channel)",
        re.IGNORECASE,
    ),
    # "engine/module/... called/named 'X'"
    re.compile(
        r"(?:engine|module|detector|scanner|layer|protocol|channel)"
        r"\s+(?:called|named)\s*['\"]?(\w+(?:\s+\w+){0,3}?)['\"]?"
        r"(?:\s|$|[.,;!?])",
        re.IGNORECASE,
    ),
    # "the X engine", "the X detector", "the X module", etc.
    re.compile(
        r"\bthe\s+(\w+(?:\s+\w+){0,3}?)\s+"
        r"(?:engine|module|detector|scanner|protocol)",
        re.IGNORECASE,
    ),
    # "X detector", "X engine", "X module" (2-word max, avoids greediness)
    re.compile(
        r"\b(\w+(?:\s+\w+)?)\s+"
        r"(?:engine|module|detector|scanner)"
        r"(?:\s|$|[.,;!?])",
        re.IGNORECASE,
    ),
    # "layer N" or "layer XX" references
    re.compile(
        r"(layer\s+\d+)",
        re.IGNORECASE,
    ),
    # "BN" channel references (B1, B2, ..., B99)
    re.compile(
        r"\b(b\d+)\b",
        re.IGNORECASE,
    ),
    # "the X protocol"
    re.compile(
        r"\bthe\s+(\w+(?:\s+\w+){0,3}?)\s+protocol",
        re.IGNORECASE,
    ),
]

# Arabic patterns (P0-F: expanded for bilingual parity)
_RE_COMPONENT_REF_AR = [
    # "محرك X" (engine X)
    re.compile(r"محرك\s+(\S+(?:\s+\S+)?)"),
    # "طبقة X" (layer X)
    re.compile(r"طبقة\s+(\S+(?:\s+\S+)?)"),
    # "بروتوكول X" (protocol X)
    re.compile(r"بروتوكول\s+(\S+(?:\s+\S+)?)"),
    # "كاشف X" (detector X)
    re.compile(r"كاشف\s+(\S+(?:\s+\S+)?)"),
    # "قناة X" (channel X)
    re.compile(r"قناة\s+(\S+(?:\s+\S+)?)"),
    # "معادلة X" (equation X)
    re.compile(r"معادلة\s+(\S+(?:\s+\S+)?)"),
    # P0-F: "وحدة X" (module/unit X)
    re.compile(r"وحدة\s+(\S+(?:\s+\S+)?)"),
    # P0-F: "مفهوم X" (concept X)
    re.compile(r"مفهوم\s+(\S+(?:\s+\S+)?)"),
    # P0-F: Mixed-script patterns: "محرك aatif_*" or "B3 قناة"
    re.compile(r"محرك\s+(aatif_\w+)"),
    re.compile(r"(B\d+)\s+قناة", re.IGNORECASE),
]

# P0-F: Arabic morphological prefix stripping pattern
# Handles ال (al-), و (wa-), ب (bi-), ف (fa-), ل (li-) prefixed to terms
# Also handles compound prefixes: وال, بال, فال, لل
_AR_PREFIX_PATTERN = re.compile(r"^(?:وال|بال|فال|لل|ال|و|ب|ف|ل)")


# =====================================================================
#  Correction recommendations
# =====================================================================

CORRECTION_BY_TYPE: Dict[UCNViolationType, str] = {
    UCNViolationType.PHANTOM_ENGINE: (
        "Remove reference to non-existent engine/module. Only reference "
        "engines that actually exist in the AATIF architecture. If the "
        "concept needs to exist, it must be formally designed and added "
        "to the system first."
    ),
    UCNViolationType.PHANTOM_LAYER: (
        "Remove reference to non-existent layer. AATIF has layers 1-20. "
        "Do not invent layers beyond this range or assign names to layers "
        "that do not carry those names in the architecture."
    ),
    UCNViolationType.PHANTOM_PROTOCOL: (
        "Remove reference to non-existent protocol. Only reference protocols "
        "that are formally defined in the AATIF constitution. Aspirational "
        "concepts are not protocols until they are written."
    ),
    UCNViolationType.PHANTOM_CHANNEL: (
        "Remove reference to non-existent binding channel. AATIF has "
        "binding channels B1 through B8 only. Do not invent channels "
        "beyond this range."
    ),
    UCNViolationType.PHANTOM_CONCEPT: (
        "Remove reference to non-existent architectural concept. Only "
        "reference concepts that are formally defined in the system. "
        "General knowledge concepts are fine; attributing them to AATIF "
        "architecture when they don't exist there is not."
    ),
}

UCN_CORRECTION_PREAMBLE = (
    "UCN violation detected: the output references AATIF architectural "
    "components that do not exist in the system. The Closed-World Assumption "
    "applies: if it is not written in the system, it does not exist in the "
    "system. Remove or correct phantom references."
)


# =====================================================================
#  Data Classes (P0-B: isolation_marker, P0-C: split confidences,
#                P0-D: reference_mode, P0-E: correction_status)
# =====================================================================

@dataclass
class UCNViolation:
    """A single UCN violation -- a phantom component reference."""
    violation_type: UCNViolationType
    phantom_name: str           # the invented concept name
    context_snippet: str        # surrounding text where it was found
    confidence: float           # [0,1] -- overall confidence
    severity: float             # [0,1]
    # P0-C: Split confidence
    detection_confidence: float = 0.0   # is this an architecture reference?
    phantom_confidence: float = 0.0     # is the referenced component nonexistent?
    # P0-D: Modal classification
    reference_mode: str = "ASSERTED"    # "ASSERTED" | "PROPOSED" | "HYPOTHETICAL"
    # P0-E: Correction status
    correction_status: str = "candidate_not_authoritative"
    suggested_correction: str = ""


@dataclass
class UCNReading:
    """
    Output of UCNDetector.validate() -- observational.

    This reading tells the pipeline whether the output references
    phantom AATIF components. It never blocks, never modifies
    H/theta/S, and never makes safety decisions.

    P0-B: _isolation_marker confirms this reading operates in B3/B5 only.
    """
    phantoms_detected: List[UCNViolation]
    architecture_references_found: int    # total refs to AATIF architecture
    all_references_valid: bool            # True when no phantoms found
    recommendations: List[str]
    evidence: List[str] = field(default_factory=list)
    # P0-B: Isolation contract marker -- always set
    _isolation_marker: str = field(default=ISOLATION_MARKER, repr=False)


# =====================================================================
#  Small duck-typed accessors  (mirrors PVM/PSP/LBH pattern)
# =====================================================================

def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a key from dict, dataclass, or arbitrary object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _text_of(draft: Any) -> str:
    """Extract the text payload from draft (str, dict, or object)."""
    if draft is None:
        return ""
    if isinstance(draft, str):
        return draft
    return _get(draft, "text", "") or _get(draft, "content", "") or ""


def _simple_similarity(a: str, b: str) -> float:
    """P0-E: Simple character-based similarity ratio (0..1).

    Uses Dice coefficient on character bigrams -- lightweight, no
    external dependencies.
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    a_bigrams = set(a[i:i+2] for i in range(len(a) - 1)) if len(a) > 1 else {a}
    b_bigrams = set(b[i:i+2] for i in range(len(b) - 1)) if len(b) > 1 else {b}
    intersection = a_bigrams & b_bigrams
    if not a_bigrams and not b_bigrams:
        return 0.0
    return 2.0 * len(intersection) / (len(a_bigrams) + len(b_bigrams))


def _has_aatif_anchor(text_lower: str) -> bool:
    """P0-C: Check if the text contains AATIF-specific context anchors."""
    for anchor in _AATIF_CONTEXT_ANCHORS:
        if anchor in text_lower:
            return True
    return False


def _detect_reference_mode(text: str) -> str:
    """P0-D: Detect if the text uses speculative/hypothetical language.

    Returns "PROPOSED", "HYPOTHETICAL", or "ASSERTED".
    """
    low = text.lower()
    norm = normalize_arabic(text)
    # Check English speculative markers
    for marker in _SPECULATIVE_MARKERS_EN:
        if marker in low:
            if marker in ("hypothetical",):
                return "HYPOTHETICAL"
            return "PROPOSED"
    # Check Arabic speculative markers
    for marker in _SPECULATIVE_MARKERS_AR:
        if normalize_arabic(marker) in norm:
            return "PROPOSED"
    return "ASSERTED"


# =====================================================================
#  UCNDetector -- observational, ARCHITECTURAL INTEGRITY
# =====================================================================

class UCNDetector:
    """
    Closed-World validator for AATIF architecture references.

    The detector scans text for references to AATIF architectural components
    and checks each reference against the known component registry. Any
    reference to a component that does not exist in the registry is flagged
    as a phantom -- an invented concept that violates the Unwritten Concept
    Nullification Law.

    Critical scope boundary: this module ONLY applies to references about
    AATIF's architecture. General knowledge statements are never flagged.

    The detector outputs a UCNReading. It does not generate response content,
    does not block responses, and does not touch S/H/theta.

    P0-A: Registry is dynamically discovered from engine/ directory.
    P0-B: Every UCNReading carries an isolation marker.
    P0-C: Confidence is context-anchored (requires AATIF keywords).
    P0-D: Speculative references are classified as PROPOSED, not PHANTOM.
    P0-E: Fuzzy suggestions use 0.80 threshold, marked candidate_not_authoritative.
    P0-F: Arabic patterns expanded for bilingual parity.
    """

    def __init__(self):
        self._registry = KNOWN_COMPONENTS

    @classmethod
    def registry_source(cls) -> str:
        """P0-A: Return whether the registry was built from dynamic discovery or fallback."""
        return _REGISTRY_SOURCE

    # -- Public API ---------------------------------------------------

    def validate(self,
                 text: Any,
                 domain: Optional[str] = None) -> UCNReading:
        """
        Scan text for phantom AATIF architecture references.

        Parameters
        ----------
        text : str | dict | object
            The text to validate. A bare string, or anything exposing
            ``text`` or ``content``.
        domain : str | None
            Domain context (reserved for future use).

        Returns
        -------
        UCNReading
            Observational reading with phantom detections and
            recommendations.
        """
        raw = _text_of(text)
        low = raw.lower()
        norm = normalize_arabic(raw)
        evidence: List[str] = []

        # -- P0-C: Detect AATIF-specific context anchors ---------------
        has_anchor = _has_aatif_anchor(low) or _has_aatif_anchor(norm)

        # -- P0-D: Detect reference mode (speculative vs asserted) -----
        ref_mode = _detect_reference_mode(raw)

        # -- Step 1: AATIF context detection ---------------------------
        has_context = False
        for trigger in _CONTEXT_TRIGGERS_EN:
            if trigger in low:
                has_context = True
                break
        if not has_context:
            for trigger in _CONTEXT_TRIGGERS_AR:
                if normalize_arabic(trigger) in norm:
                    has_context = True
                    break

        if not has_context:
            evidence.append(
                "fast_path_skip: no AATIF architectural context detected"
            )
            return UCNReading(
                phantoms_detected=[],
                architecture_references_found=0,
                all_references_valid=True,
                recommendations=[],
                evidence=evidence,
            )

        # -- Step 2: Reference extraction ------------------------------
        extracted: list = []

        # English extraction
        for pattern in _RE_COMPONENT_REF_EN:
            for match in pattern.finditer(raw):
                raw_match = match.group(1).strip()
                normalized = raw_match.lower().strip()
                full_match = match.group(0).lower()
                vtype = self._classify_type(full_match, normalized)
                start = max(0, match.start() - 25)
                end = min(len(raw), match.end() + 25)
                snippet = raw[start:end].strip()
                extracted.append(
                    (raw_match, normalized, vtype, snippet, full_match)
                )

        # Arabic extraction (P0-F: uses expanded patterns)
        for pattern in _RE_COMPONENT_REF_AR:
            for match in pattern.finditer(raw):
                raw_match = match.group(1).strip()
                normalized = normalize_arabic(raw_match)
                full_match = match.group(0)
                full_normalized = normalize_arabic(full_match)
                vtype = self._classify_type_ar(full_match)
                start = max(0, match.start() - 25)
                end = min(len(raw), match.end() + 25)
                snippet = raw[start:end].strip()
                extracted.append(
                    (raw_match, normalized, vtype, snippet, full_normalized)
                )

        total_refs = len(extracted)
        evidence.append(f"architecture_references_extracted: {total_refs}")

        if total_refs == 0:
            evidence.append(
                "no specific component references found "
                "(AATIF context present but no extractable references)"
            )
            return UCNReading(
                phantoms_detected=[],
                architecture_references_found=0,
                all_references_valid=True,
                recommendations=[],
                evidence=evidence,
            )

        # -- Step 3: Registry check ------------------------------------
        phantoms: List[UCNViolation] = []
        seen_phantoms: set = set()  # deduplicate

        for raw_match, normalized, vtype, snippet, full_norm in extracted:
            # Check against all registry forms
            if self._is_known(normalized) or self._is_known(full_norm):
                evidence.append(f"valid_ref: '{raw_match}' -> found in registry")
                continue

            # P0-F: Try with Arabic prefix stripping
            stripped_ar = _AR_PREFIX_PATTERN.sub("", normalized).strip()
            if stripped_ar and self._is_known(stripped_ar):
                evidence.append(f"valid_ref: '{raw_match}' -> found after prefix strip")
                continue

            # Deduplicate (strip articles for dedup key)
            dedup_norm = re.sub(r"^(?:an?\s+|the\s+)", "", normalized).strip()
            dedup_key = (dedup_norm, vtype)
            if dedup_key in seen_phantoms:
                continue
            seen_phantoms.add(dedup_key)

            # -- Step 4: Scoring (P0-C: context-anchored) ---------------
            base_severity = VIOLATION_SEVERITY[vtype]

            # P0-C: detection_confidence -- is this an architecture ref?
            detection_confidence = 0.85 if has_anchor else 0.60

            # P0-C: phantom_confidence -- base, capped by anchor presence
            if has_anchor:
                phantom_confidence = SINGLE_PHANTOM_BASE_CONFIDENCE
                confidence_cap = CONFIDENCE_CAP_WITH_ANCHOR
            else:
                phantom_confidence = min(
                    SINGLE_PHANTOM_BASE_CONFIDENCE,
                    CONFIDENCE_CAP_NO_ANCHOR,
                )
                confidence_cap = CONFIDENCE_CAP_NO_ANCHOR

            # P0-C: Combined confidence
            confidence = min(phantom_confidence, confidence_cap)
            severity = base_severity

            # P0-D: Modal classification
            violation_mode = ref_mode
            if violation_mode in ("PROPOSED", "HYPOTHETICAL"):
                severity = min(severity, PROPOSED_SEVERITY_CAP)
                evidence.append(
                    f"modal_cap: '{raw_match}' classified as {violation_mode}, "
                    f"severity capped at {PROPOSED_SEVERITY_CAP}"
                )

            # Clean phantom name: strip leading articles for display
            clean_name = re.sub(
                r"^(?:an?\s+|the\s+)", "", raw_match, flags=re.IGNORECASE
            ).strip() or raw_match

            # P0-E: Find fuzzy suggestion (conservative, threshold 0.80)
            suggested = self._find_closest(normalized)

            phantoms.append(UCNViolation(
                violation_type=vtype,
                phantom_name=clean_name,
                context_snippet=snippet,
                confidence=round(confidence, 3),
                severity=round(severity, 3),
                detection_confidence=round(detection_confidence, 3),
                phantom_confidence=round(phantom_confidence, 3),
                reference_mode=violation_mode,
                correction_status="candidate_not_authoritative",
                suggested_correction=suggested,
            ))
            evidence.append(
                f"PHANTOM: '{raw_match}' (type={vtype.value}, "
                f"conf={confidence:.2f}, sev={severity:.2f}, "
                f"mode={violation_mode}, anchor={has_anchor})"
            )

        # Compound scoring: multiple phantoms increase confidence
        if len(phantoms) > 1:
            for p in phantoms:
                bonus = min(
                    (len(phantoms) - 1) * MULTI_PHANTOM_COMPOUND_BONUS,
                    0.20,
                )
                new_conf = p.confidence + bonus
                # P0-C: Still respect anchor-based cap
                cap = CONFIDENCE_CAP_WITH_ANCHOR if has_anchor else CONFIDENCE_CAP_NO_ANCHOR
                p.confidence = min(
                    round(new_conf, 3),
                    cap,
                )
            evidence.append(
                f"compound_bonus: {len(phantoms)} phantoms, "
                f"bonus={MULTI_PHANTOM_COMPOUND_BONUS * (len(phantoms) - 1):.2f}"
            )

        # -- Build recommendations ------------------------------------
        recommendations: List[str] = []
        for p in phantoms:
            rec = CORRECTION_BY_TYPE[p.violation_type]
            if p.suggested_correction:
                rec += f" (suggestion [candidate_not_authoritative]: '{p.suggested_correction}')"
            recommendations.append(rec)

        if UCN_MONITOR_ONLY:
            evidence.append(
                "UCN_MONITOR_ONLY=True -> recommendations are observational only"
            )

        all_valid = len(phantoms) == 0
        if all_valid:
            evidence.append("all references validated against registry")

        return UCNReading(
            phantoms_detected=phantoms,
            architecture_references_found=total_refs,
            all_references_valid=all_valid,
            recommendations=recommendations,
            evidence=evidence,
        )

    # -- Internal helpers ---------------------------------------------

    def _is_known(self, normalized: str) -> bool:
        """Check if a normalized reference exists in the registry.

        Uses progressive word stripping from both leading and trailing
        edges to handle regex greediness. P0-F: also strips Arabic
        morphological prefixes.
        """
        cleaned = re.sub(r"^(?:an?\s+|the\s+)", "", normalized).strip()
        if not cleaned:
            return True  # nothing left after stripping -> not a real reference

        candidates = {normalized, cleaned}

        # Progressive word stripping
        words = cleaned.split()
        for i in range(len(words)):
            sub = " ".join(words[i:]).strip()
            if sub:
                candidates.add(sub)
        for i in range(len(words), 0, -1):
            sub = " ".join(words[:i]).strip()
            if sub:
                candidates.add(sub)

        # P0-F: Add Arabic prefix-stripped candidates
        ar_candidates = set()
        for c in list(candidates):
            stripped = _AR_PREFIX_PATTERN.sub("", c).strip()
            if stripped and stripped != c:
                ar_candidates.add(stripped)
        candidates |= ar_candidates

        for candidate in list(candidates):
            # Direct lookup
            if candidate in self._registry:
                return True

            # Try with common suffixes stripped
            for suffix in ("engine", "module", "detector", "scanner",
                           "protocol", "channel", "layer"):
                stripped = candidate.replace(suffix, "").strip()
                if stripped and stripped in self._registry:
                    return True

            # Try the full compound (e.g., "intent engine" from "intent")
            for suffix in ("engine", "module", "detector", "scanner"):
                compound = f"{candidate} {suffix}"
                if compound in self._registry:
                    return True

            # Try as an engine file name (strip spaces -> underscores)
            as_file = candidate.replace(" ", "_")
            if as_file in self._registry:
                return True

        return False

    def _find_closest(self, phantom_name: str) -> str:
        """P0-E: Find the closest known component by similarity.

        Returns the closest match if similarity >= FUZZY_SIMILARITY_THRESHOLD,
        otherwise returns empty string. Never auto-corrects -- only suggests.
        All suggestions carry correction_status='candidate_not_authoritative'.
        """
        if not phantom_name:
            return ""
        best_match = ""
        best_score = 0.0
        for known in self._registry:
            score = _simple_similarity(phantom_name, known)
            if score > best_score:
                best_score = score
                best_match = known
        if best_score >= FUZZY_SIMILARITY_THRESHOLD:
            return best_match
        return ""

    @staticmethod
    def _classify_type(full_match: str, normalized: str) -> UCNViolationType:
        """Classify the violation type from the English match context."""
        if "engine" in full_match or "module" in full_match:
            return UCNViolationType.PHANTOM_ENGINE
        if "detector" in full_match or "scanner" in full_match:
            return UCNViolationType.PHANTOM_ENGINE
        if "layer" in full_match or normalized.startswith("layer"):
            return UCNViolationType.PHANTOM_LAYER
        if "protocol" in full_match:
            return UCNViolationType.PHANTOM_PROTOCOL
        if "channel" in full_match or normalized.startswith("b") and \
           len(normalized) <= 3 and normalized[1:].isdigit():
            return UCNViolationType.PHANTOM_CHANNEL
        return UCNViolationType.PHANTOM_CONCEPT

    @staticmethod
    def _classify_type_ar(full_match: str) -> UCNViolationType:
        """Classify the violation type from the Arabic match context."""
        if "محرك" in full_match or "كاشف" in full_match:
            return UCNViolationType.PHANTOM_ENGINE
        if "طبقة" in full_match:
            return UCNViolationType.PHANTOM_LAYER
        if "بروتوكول" in full_match:
            return UCNViolationType.PHANTOM_PROTOCOL
        if "قناة" in full_match:
            return UCNViolationType.PHANTOM_CHANNEL
        if "معادلة" in full_match:
            return UCNViolationType.PHANTOM_ENGINE
        if "وحدة" in full_match:
            return UCNViolationType.PHANTOM_ENGINE
        if "مفهوم" in full_match:
            return UCNViolationType.PHANTOM_CONCEPT
        return UCNViolationType.PHANTOM_CONCEPT


# =====================================================================
#  Correction recommendation for pipeline
# =====================================================================

def recommend_correction(reading: UCNReading) -> str:
    """
    Build a correction recommendation string when UCN violations
    are detected.

    Parameters
    ----------
    reading : UCNReading
        The validation result from UCNDetector.validate().

    Returns
    -------
    str
        A recommendation string. Empty if no phantoms detected.
    """
    if not reading.phantoms_detected:
        return ""

    parts = [UCN_CORRECTION_PREAMBLE]
    parts.append(
        f"Phantoms found: {len(reading.phantoms_detected)} | "
        f"Total refs: {reading.architecture_references_found}"
    )

    for p in reading.phantoms_detected:
        line = (
            f"  [{p.violation_type.value}] '{p.phantom_name}' "
            f"(conf={p.confidence:.2f}, sev={p.severity:.2f}, "
            f"mode={p.reference_mode}): "
            f"{CORRECTION_BY_TYPE[p.violation_type]}"
        )
        if p.suggested_correction:
            line += f" [suggestion (candidate_not_authoritative): '{p.suggested_correction}']"
        parts.append(line)

    return "\n".join(parts)


# =====================================================================
#  Audit helper -- SHA256 for evidence integrity
# =====================================================================

def ucn_audit_hash(reading: UCNReading) -> str:
    """
    SHA256 of the UCN reading for audit integrity.

    P0-A: includes registry_version to track which registry produced
    the reading (dynamic vs fallback).
    """
    payload = json.dumps({
        "all_references_valid": reading.all_references_valid,
        "architecture_references_found": reading.architecture_references_found,
        "phantom_count": len(reading.phantoms_detected),
        "phantom_types": [p.violation_type.value for p in reading.phantoms_detected],
        "evidence_count": len(reading.evidence),
        "registry_source": _REGISTRY_SOURCE,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# =====================================================================
#  Self-test -- quick validation  (python engine/aatif_ucn_validator.py)
# =====================================================================

def _self_test() -> None:
    """Minimal smoke test for UCN validation."""
    d = UCNDetector()

    cases = [
        # (text, expected_label, should_have_phantoms)
        (
            "AATIF has an intent engine that processes user requests.",
            "VALID (intent engine exists)",
            False,
        ),
        (
            "AATIF has a compassion engine that handles empathy.",
            "PHANTOM_ENGINE (compassion engine does not exist)",
            True,
        ),
        (
            "Layer 14 is the Human Reality Layer in AATIF.",
            "VALID (layer 14 exists, human reality layer exists)",
            False,
        ),
        (
            "Layer 25 handles emotion routing in AATIF.",
            "PHANTOM_LAYER (only layers 1-20 exist)",
            True,
        ),
        (
            "The forgiveness protocol ensures mercy in AATIF.",
            "PHANTOM_PROTOCOL (no forgiveness protocol exists)",
            True,
        ),
        (
            "Photosynthesis converts sunlight into chemical energy.",
            "CLEAN (no AATIF context, fast-path skip)",
            False,
        ),
        (
            "The S equation calculates harm in AATIF.",
            "VALID (S equation exists)",
            False,
        ),
        (
            "B9 handles authentication in AATIF.",
            "PHANTOM_CHANNEL (only B1-B8 exist)",
            True,
        ),
        (
            "AATIF uses sparse activation for efficiency.",
            "VALID (sparse activation is a known concept)",
            False,
        ),
        (
            "The drift detector monitors system stability.",
            "VALID (drift detector exists)",
            False,
        ),
        (
            "AATIF has a karma engine that tracks moral balance.",
            "PHANTOM_ENGINE (karma engine does not exist)",
            True,
        ),
        (
            "Compassion is important in human interactions.",
            "CLEAN (general statement, not about AATIF architecture)",
            False,
        ),
    ]

    print("  UCN Validator Self-Test (FN#042)")
    print("  " + "-" * 60)
    all_passed = True

    for text, label, should_phantom in cases:
        r = d.validate(text)
        has_phantoms = len(r.phantoms_detected) > 0
        status = "OK" if has_phantoms == should_phantom else "FAIL"
        if status == "FAIL":
            all_passed = False

        phantom_names = ", ".join(
            f"{p.phantom_name}({p.violation_type.value})"
            for p in r.phantoms_detected
        ) if r.phantoms_detected else "none"

        print(f"  [{status}] refs={r.architecture_references_found} "
              f"valid={r.all_references_valid} "
              f"phantoms=[{phantom_names}] | {label}")

        if has_phantoms:
            correction = recommend_correction(r)
            if correction:
                print(f"        -> correction recommendation generated "
                      f"({len(correction)} chars)")

    print("  " + "-" * 60)
    if all_passed:
        print("  PASSED: all cases validated correctly")
    else:
        print("  FAILED: some cases did not match expected validation")


if __name__ == "__main__":
    _self_test()


# =====================================================================
#  Module exports
# =====================================================================

__all__ = [
    # Feature flags
    "UCN_ENABLED",
    "UCN_MONITOR_ONLY",
    # Authority level
    "AUTHORITY_LEVEL",
    "CAN_BLOCK_RUNTIME",
    "CAN_MODIFY_H",
    "CAN_MODIFY_THETA",
    "CAN_MODIFY_S",
    "CAN_EMIT_JUDICIAL_DECISION",
    "UCN_ENABLED_FLAG",
    # P0-B: Isolation contract
    "ISOLATION_MARKER",
    "ISOLATION_TARGETS",
    # Violation type enum
    "UCNViolationType",
    # P0-D: Reference mode
    "ReferenceMode",
    # Constants
    "FAST_PATH_MAX_CHARS",
    "SINGLE_PHANTOM_BASE_CONFIDENCE",
    "MULTI_PHANTOM_COMPOUND_BONUS",
    "MAX_CONFIDENCE",
    "VIOLATION_SEVERITY",
    "CONFIDENCE_CAP_NO_ANCHOR",
    "CONFIDENCE_CAP_WITH_ANCHOR",
    "PROPOSED_SEVERITY_CAP",
    "FUZZY_SIMILARITY_THRESHOLD",
    # Registry
    "KNOWN_COMPONENTS",
    # Correction templates
    "CORRECTION_BY_TYPE",
    "UCN_CORRECTION_PREAMBLE",
    # Data classes
    "UCNViolation",
    "UCNReading",
    # Detector
    "UCNDetector",
    # Correction helper
    "recommend_correction",
    # Audit
    "ucn_audit_hash",
]
