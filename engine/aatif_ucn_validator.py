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

Design consensus: Claude, 2026-07-01
Field Note: FN#042 (Unwritten Concept Nullification Law)

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import enum
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
        # Strip tashkeel (Arabic diacritics: U+0610-U+061A, U+064B-U+065F, U+0670)
        _TASHKEEL = set(range(0x0610, 0x061B)) | set(range(0x064B, 0x0660)) | {0x0670}
        out = []
        for ch in text:
            cp = ord(ch)
            if cp in _TASHKEEL:
                continue
            out.append(ch)
        result = "".join(out)
        # Normalize alef variants -> bare alef
        result = result.replace("آ", "ا")  # alef madda
        result = result.replace("أ", "ا")  # alef hamza above
        result = result.replace("إ", "ا")  # alef hamza below
        # Normalize taa marbouta -> haa
        result = result.replace("ة", "ه")
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
#  Constants -- calibration values
# =====================================================================

FAST_PATH_MAX_CHARS = 20          # texts shorter than this with no AATIF context -> skip
SINGLE_PHANTOM_BASE_CONFIDENCE = 0.70
MULTI_PHANTOM_COMPOUND_BONUS = 0.10
MAX_CONFIDENCE = 0.95

# Per-violation-type base severity
VIOLATION_SEVERITY: Dict[UCNViolationType, float] = {
    UCNViolationType.PHANTOM_ENGINE:   0.80,  # worst -- inventing whole engines
    UCNViolationType.PHANTOM_LAYER:    0.80,  # inventing layers is equally bad
    UCNViolationType.PHANTOM_PROTOCOL: 0.70,
    UCNViolationType.PHANTOM_CHANNEL:  0.75,
    UCNViolationType.PHANTOM_CONCEPT:  0.60,
}


# =====================================================================
#  Component Registry -- the KNOWN AATIF architecture (Closed World)
# =====================================================================
#
#  If it is not in this registry, it does not exist.
#  All entries are normalized to lowercase for O(1) lookup.

# -- Engine/module file names (the 39 files in engine/) ----------------
_KNOWN_ENGINE_FILES = frozenset({
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
    "binding_map", "ucn_validator",
})

# -- Short names (what people would actually say) ----------------------
_KNOWN_SHORT_NAMES = frozenset({
    "s equation", "r equation", "governance equation", "intent engine",
    "governor", "meta oversight", "output gate", "response shaper",
    "reasoning trace", "drift detector", "uncertainty detector",
    "logic profile scanner", "emotion scorer", "pvm detector",
    "psp detector", "lbh detector", "false goodness detector",
    "muhajij", "binding map", "boot sequence", "fingerprint",
    "hysteresis", "pipeline connector", "judgment integration",
    "ucn validator",
})

# -- Arabic names ------------------------------------------------------
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

# Arabic patterns
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
]


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
#  Data Classes
# =====================================================================

@dataclass
class UCNViolation:
    """A single UCN violation -- a phantom component reference."""
    violation_type: UCNViolationType
    phantom_name: str           # the invented concept name
    context_snippet: str        # surrounding text where it was found
    confidence: float           # [0,1]
    severity: float             # [0,1]


@dataclass
class UCNReading:
    """
    Output of UCNDetector.validate() -- observational.

    This reading tells the pipeline whether the output references
    phantom AATIF components. It never blocks, never modifies
    H/theta/S, and never makes safety decisions.
    """
    phantoms_detected: List[UCNViolation]
    architecture_references_found: int    # total refs to AATIF architecture
    all_references_valid: bool            # True when no phantoms found
    recommendations: List[str]
    evidence: List[str] = field(default_factory=list)


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
    """

    def __init__(self):
        self._registry = KNOWN_COMPONENTS

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

        # -- Step 1: AATIF context detection ---------------------------
        #  If the text is not about AATIF architecture, fast-path skip.
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
        # Each entry: (raw_match, normalized_for_lookup, guessed_type,
        #              snippet, full_normalized)
        # full_normalized: the FULL regex match (incl. prefix like "محرك")
        #   normalized to allow registry lookup of the compound.
        extracted: list = []

        # English extraction
        for pattern in _RE_COMPONENT_REF_EN:
            for match in pattern.finditer(raw):
                raw_match = match.group(1).strip()
                normalized = raw_match.lower().strip()

                # Determine violation type from context
                full_match = match.group(0).lower()
                vtype = self._classify_type(full_match, normalized)

                # Get context snippet (50 chars around the match)
                start = max(0, match.start() - 25)
                end = min(len(raw), match.end() + 25)
                snippet = raw[start:end].strip()

                extracted.append(
                    (raw_match, normalized, vtype, snippet, full_match)
                )

        # Arabic extraction
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
            # Check against all registry forms:
            # 1. Check the captured argument (e.g., "intent", "النية")
            # 2. Check the full match incl. prefix (e.g., "the intent engine",
            #    "محرك النيه") — handles Arabic compounds where the registry
            #    stores "محرك النيه" but the capture is just "النيه في"
            if self._is_known(normalized) or self._is_known(full_norm):
                evidence.append(f"valid_ref: '{raw_match}' -> found in registry")
                continue

            # Deduplicate (strip articles for dedup key)
            dedup_norm = re.sub(r"^(?:an?\s+|the\s+)", "", normalized).strip()
            dedup_key = (dedup_norm, vtype)
            if dedup_key in seen_phantoms:
                continue
            seen_phantoms.add(dedup_key)

            # -- Step 4: Scoring ---------------------------------------
            base_severity = VIOLATION_SEVERITY[vtype]
            confidence = SINGLE_PHANTOM_BASE_CONFIDENCE
            severity = base_severity

            # Clean phantom name: strip leading articles for display
            clean_name = re.sub(
                r"^(?:an?\s+|the\s+)", "", raw_match, flags=re.IGNORECASE
            ).strip() or raw_match

            phantoms.append(UCNViolation(
                violation_type=vtype,
                phantom_name=clean_name,
                context_snippet=snippet,
                confidence=round(confidence, 3),
                severity=round(severity, 3),
            ))
            evidence.append(
                f"PHANTOM: '{raw_match}' (type={vtype.value}, "
                f"conf={confidence:.2f}, sev={severity:.2f})"
            )

        # Compound scoring: multiple phantoms increase confidence
        if len(phantoms) > 1:
            for p in phantoms:
                bonus = min(
                    (len(phantoms) - 1) * MULTI_PHANTOM_COMPOUND_BONUS,
                    0.20,
                )
                p.confidence = min(
                    round(p.confidence + bonus, 3),
                    MAX_CONFIDENCE,
                )
            evidence.append(
                f"compound_bonus: {len(phantoms)} phantoms, "
                f"bonus={MULTI_PHANTOM_COMPOUND_BONUS * (len(phantoms) - 1):.2f}"
            )

        # -- Build recommendations ------------------------------------
        recommendations: List[str] = []
        for p in phantoms:
            recommendations.append(CORRECTION_BY_TYPE[p.violation_type])

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
        edges to handle regex greediness (e.g., "uses the intent" should
        still match "intent engine" after stripping "uses the").
        """
        # Strip leading articles (a, an, the)
        cleaned = re.sub(r"^(?:an?\s+|the\s+)", "", normalized).strip()
        if not cleaned:
            return True  # nothing left after stripping -> not a real reference

        candidates = {normalized, cleaned}

        # Progressive word stripping: try removing leading words one by one
        # e.g., "uses the intent" -> "the intent" -> "intent"
        words = cleaned.split()
        for i in range(len(words)):
            sub = " ".join(words[i:]).strip()
            if sub:
                candidates.add(sub)
        # Also try stripping trailing words (for Arabic: "النية في" -> "النية")
        for i in range(len(words), 0, -1):
            sub = " ".join(words[:i]).strip()
            if sub:
                candidates.add(sub)

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
        parts.append(
            f"  [{p.violation_type.value}] '{p.phantom_name}' "
            f"(conf={p.confidence:.2f}, sev={p.severity:.2f}): "
            f"{CORRECTION_BY_TYPE[p.violation_type]}"
        )

    return "\n".join(parts)


# =====================================================================
#  Audit helper -- SHA256 for evidence integrity
# =====================================================================

def ucn_audit_hash(reading: UCNReading) -> str:
    """
    SHA256 of the UCN reading for audit integrity.

    Same pattern as PVM/LBH audit hash -- trace integrity without
    storing raw content.
    """
    payload = json.dumps({
        "all_references_valid": reading.all_references_valid,
        "architecture_references_found": reading.architecture_references_found,
        "phantom_count": len(reading.phantoms_detected),
        "phantom_types": [p.violation_type.value for p in reading.phantoms_detected],
        "evidence_count": len(reading.evidence),
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
    # Violation type enum
    "UCNViolationType",
    # Constants
    "FAST_PATH_MAX_CHARS",
    "SINGLE_PHANTOM_BASE_CONFIDENCE",
    "MULTI_PHANTOM_COMPOUND_BONUS",
    "MAX_CONFIDENCE",
    "VIOLATION_SEVERITY",
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
