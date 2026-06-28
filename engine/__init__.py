"""
AATIF Engine — عاطف
====================

Module exports for the AATIF governance engine.
Optional modules use try/except — if a dependency is missing,
its exports are simply not available.
"""

# ── Core governor ──
from aatif_governor import AATIFGovernor, GovernedResponse  # noqa: F401

# ── Judgment memory (optional — requires numpy) ──
try:
    from aatif_judgment_memory import JudgmentMemory  # noqa: F401
except ImportError:
    pass

# ── Judgment integration (optional — requires judgment memory) ──
try:
    from aatif_judgment_integration import (  # noqa: F401
        JudgmentAwareGovernor,
        JudgmentAwareResult,
        create_judgment_governor,
    )
except ImportError:
    pass

# ── Response shaper (optional) ──
try:
    from aatif_response_shaper import (  # noqa: F401
        AATIFResponseShaper,
        ResponseShape,
    )
except ImportError:
    pass
