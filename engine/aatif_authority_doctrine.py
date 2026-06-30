#!/usr/bin/env python3
"""
AATIF Responsible Authority Doctrine — عقيدة السلطة  (Field Note #014)
======================================================================

"النظام يُنفّذ. الجهة المسؤولة تُقرّر."
"The system acts. The authority decides."

A governed system does not obey *any* human — it obeys the *authorized
responsible party*.  This module is the runtime authorization layer: it
answers two questions for every privileged action —

    1. WHO is asking?            (AuthorityRole / AuthorityContext)
    2. Are they ALLOWED to?      (AuthorityPermission / check_permission)

THE CONSTITUTIONAL HIERARCHY
────────────────────────────
Authority flows downward, never upward, and *nothing* outranks the
constitution:

    Core Values (رحمة، عدل، حقيقة)   ← constitutional, above ALL roles
        │
        ▼
    Constitution (field notes)        ← constitutional, above ALL roles
        │
        ▼
    OWNER / Architect (المالك)        ← full control of parameters
        │
        ▼
    TRAINER / Admin (المُدرّب)         ← style + anchors, never safety
        │
        ▼
    USER (المستخدم)                    ← normal interaction
        │
        ▼
    GUEST (الضيف)                      ← read-only, no persistent state

THE TWO HARD RULES
──────────────────
  • No self-goals, no self-modification, no unsanctioned initiative.  The
    system acts only on behalf of an authorized authority — never for
    itself.  `detect_autonomy_drift` watches for the system drifting toward
    autonomy and flags it so the pipeline can return to the constitutional
    line.

  • The responsible authority sets goals and tasks but CANNOT override core
    values.  Even the OWNER cannot disable safety (θ below the constitutional
    floor), remove CBRN protections, or disable the S equation.  These are
    *constitutional*, above every role — `is_constitutional_violation`
    enforces the ceiling.

KEY DESIGN CONSTRAINTS
──────────────────────
  • Pure logic — no embeddings, no LLM, no I/O.  Deterministic.
  • Fail-safe: an unknown / unregistered authority is denied, never granted.
  • Exactly one OWNER per doctrine — set at construction, never re-created.
  • Delegation only flows downward: an authority can only grant roles strictly
    below its own level (a TRAINER can never create an OWNER).

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Ensure the engine directory is importable (same pattern as the other modules)
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


# ═══════════════════════════════════════════════════════════
#  AuthorityRole — the constitutional hierarchy
# ═══════════════════════════════════════════════════════════

class AuthorityRole(Enum):
    """
    The four authority levels, ordered by privilege.

    The integer value IS the privilege level — higher means more authority.
    This lets the hierarchy be compared directly (OWNER > TRAINER > USER >
    GUEST) and lets delegation enforce "downward only" with a simple <.
    """
    GUEST = 1    # الضيف   — read-only, most restrictive, no persistent state
    USER = 2     # المستخدم — normal interaction, cannot modify parameters
    TRAINER = 3  # المُدرّب — style + anchors within approved domains
    OWNER = 4    # المالك   — full control; the Architect

    @property
    def level(self) -> int:
        """Privilege level — higher outranks lower."""
        return self.value

    @property
    def arabic(self) -> str:
        return _ROLE_ARABIC[self]

    def outranks(self, other: "AuthorityRole") -> bool:
        """True if this role is strictly more privileged than `other`."""
        return self.level > other.level


# The default OWNER identity used when the Governor auto-constructs a doctrine
# (the Architect). Callers wiring a multi-user deployment should construct the
# doctrine explicitly with their own owner_id.
DEFAULT_OWNER_ID = "architect"


_ROLE_ARABIC: Dict[AuthorityRole, str] = {
    AuthorityRole.OWNER: "المالك",
    AuthorityRole.TRAINER: "المُدرّب",
    AuthorityRole.USER: "المستخدم",
    AuthorityRole.GUEST: "الضيف",
}


# ═══════════════════════════════════════════════════════════
#  AuthorityPermission — discrete, auditable capabilities
# ═══════════════════════════════════════════════════════════

class AuthorityPermission(Enum):
    """Discrete permissions a role may hold.  Checked one at a time."""
    MODIFY_THETA = "modify_theta"            # change safety threshold (OWNER)
    MODIFY_DOMAIN = "modify_domain"          # change domain config (OWNER)
    ADD_ANCHORS = "add_anchors"              # add anchors (OWNER, TRAINER)
    MODIFY_STYLE = "modify_style"            # change R params (OWNER, TRAINER)
    PERSISTENT_MEMORY = "persistent_memory"  # judgment memory (OWNER/TRAINER/USER)
    INTERACT = "interact"                    # send messages (all roles)
    VIEW_TRACE = "view_trace"                # reasoning trace (OWNER, TRAINER)
    OVERRIDE_RESPONSE = "override_response"   # override R styling (OWNER)


# The complete permission set — used to compute "what a role CANNOT do".
ALL_PERMISSIONS: Set[AuthorityPermission] = set(AuthorityPermission)


# ═══════════════════════════════════════════════════════════
#  ROLE_PERMISSIONS — the canonical grant table
# ═══════════════════════════════════════════════════════════
#
# Every higher role is a strict superset of the one below it.  This nesting is
# what makes the hierarchy coherent: a TRAINER can do everything a USER can,
# plus more; a USER everything a GUEST can, plus more.  The constraint-
# inheritance contract (lower roles inherit every restriction of the roles
# above them, and add their own) falls out of this nesting automatically.

ROLE_PERMISSIONS: Dict[AuthorityRole, Set[AuthorityPermission]] = {
    AuthorityRole.GUEST: {
        AuthorityPermission.INTERACT,
    },
    AuthorityRole.USER: {
        AuthorityPermission.INTERACT,
        AuthorityPermission.PERSISTENT_MEMORY,
    },
    AuthorityRole.TRAINER: {
        AuthorityPermission.INTERACT,
        AuthorityPermission.PERSISTENT_MEMORY,
        AuthorityPermission.ADD_ANCHORS,
        AuthorityPermission.MODIFY_STYLE,
        AuthorityPermission.VIEW_TRACE,
    },
    AuthorityRole.OWNER: set(ALL_PERMISSIONS),
}


def permissions_for(role: AuthorityRole) -> Set[AuthorityPermission]:
    """Return a fresh copy of the permission set granted to `role`."""
    return set(ROLE_PERMISSIONS[role])


# ═══════════════════════════════════════════════════════════
#  Constitutional ceiling — what NO role may ever do
# ═══════════════════════════════════════════════════════════
#
# These constants encode the "core values above all roles" rule.  Even the
# OWNER cannot cross them; `is_constitutional_violation` enforces the ceiling.

# θ may never drop below this floor — below it, safety is effectively disabled.
CONSTITUTIONAL_THETA_FLOOR = 0.10

# Action tokens that describe attempts to dismantle constitutional safety.
# Matched case-insensitively as substrings of the action string.
_CONSTITUTIONAL_FORBIDDEN_ACTIONS: Tuple[str, ...] = (
    "disable_safety", "disable safety",
    "disable_s_equation", "disable s equation", "disable the s equation",
    "remove_cbrn", "remove cbrn", "disable_cbrn", "disable cbrn",
    "bypass_safety", "bypass safety", "bypass the s equation",
    "remove_safety", "remove safety",
    "disable_output_gate", "disable output gate",
    "turn off safety", "turn_off_safety",
)


# ═══════════════════════════════════════════════════════════
#  Autonomy-drift signals — the system acting for ITSELF
# ═══════════════════════════════════════════════════════════
#
# FN#014: "No self-goals, no self-modification, no unsanctioned initiative."
# Any action whose description matches one of these is the system drifting
# toward autonomy — it must stop and return to the constitutional line.

_AUTONOMY_DRIFT_SIGNALS: Tuple[str, ...] = (
    # self-modification
    "self-modify", "self modify", "self_modify", "modify own", "modify my own",
    "rewrite my own", "rewrite own", "change my own", "edit my own",
    "alter my own", "update my own parameters", "reprogram myself",
    # self-goals
    "set my own goal", "set my own goals", "self-goal", "self goal",
    "my own agenda", "my own objective", "decide for myself",
    "pursue my own", "without being asked",
    # unsanctioned initiative / escaping authority
    "without authorization", "without authority", "unsanctioned",
    "bypass authority", "ignore the authority", "ignore authority",
    "act autonomously", "act on my own", "act without approval",
    "grant myself", "escalate my own", "expand my own permissions",
    "remove my own constraints", "disable my own oversight",
    "override the owner", "override my owner",
    # Arabic
    "أعدّل نفسي", "أغيّر نفسي", "هدف خاص بي", "بدون إذن",
    "بدون تفويض", "أتصرف لوحدي", "أمنح نفسي", "أتجاوز السلطة",
)


# ═══════════════════════════════════════════════════════════
#  AuthorityContext — the full picture of one authority
# ═══════════════════════════════════════════════════════════

@dataclass
class AuthorityContext:
    """
    Everything the doctrine knows about one registered authority.

    `permissions` is the resolved, concrete grant set (derived from the role
    but stored explicitly so it can be audited and, for the OWNER, never
    silently reduced).  `constraints` holds role-specific limits — e.g. a
    TRAINER restricted to particular domains.
    """
    role: AuthorityRole
    permissions: Set[AuthorityPermission]
    authority_id: str
    delegated_by: Optional[str] = None        # who granted this role
    constraints: Dict[str, Any] = field(default_factory=dict)

    def has(self, permission: AuthorityPermission) -> bool:
        return permission in self.permissions

    @property
    def is_owner(self) -> bool:
        return self.role is AuthorityRole.OWNER


# ═══════════════════════════════════════════════════════════
#  Errors
# ═══════════════════════════════════════════════════════════

class AuthorityError(RuntimeError):
    """Base class for authority-doctrine errors."""


class PermissionDenied(AuthorityError):
    """Raised by require_permission when an authority lacks a permission."""


class DelegationError(AuthorityError):
    """Raised when an attempted delegation violates the hierarchy."""


class ConstitutionalViolation(AuthorityError):
    """Raised when an action would cross the constitutional ceiling."""


# ═══════════════════════════════════════════════════════════
#  AuthorityDoctrine — عقيدة السلطة
# ═══════════════════════════════════════════════════════════

class AuthorityDoctrine:
    """
    The runtime authorization layer.

    Pure logic — no embeddings, no LLM, no I/O.  Deterministic.

    Usage:
        doctrine = AuthorityDoctrine(owner_id="architect")
        doctrine.authorize("alice", AuthorityRole.TRAINER, delegated_by="architect")

        if doctrine.check_permission("alice", AuthorityPermission.ADD_ANCHORS):
            ...

        doctrine.require_permission("alice", AuthorityPermission.MODIFY_THETA)
        # -> raises PermissionDenied (only OWNER may modify θ)

    The OWNER is set at construction and is the only authority that exists
    until others are delegated.  There is always exactly one OWNER.
    """

    # The constitutional default id used when the system itself must point at
    # an authority above all roles (the field notes / core values).
    CONSTITUTION_ID = "constitution"

    def __init__(self, owner_id: str) -> None:
        if not owner_id or not isinstance(owner_id, str):
            raise ValueError("owner_id must be a non-empty string")

        self._owner_id = owner_id
        self._authorities: Dict[str, AuthorityContext] = {}

        # Register the single OWNER. delegated_by is the constitution itself —
        # the OWNER's authority derives from the constitutional line, not from
        # any higher human.
        self._authorities[owner_id] = AuthorityContext(
            role=AuthorityRole.OWNER,
            permissions=permissions_for(AuthorityRole.OWNER),
            authority_id=owner_id,
            delegated_by=self.CONSTITUTION_ID,
            constraints={},
        )

    # ───────────────────────────────────────────────────
    #  Registration / delegation
    # ───────────────────────────────────────────────────

    def authorize(
        self,
        authority_id: str,
        role: AuthorityRole,
        delegated_by: str,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> AuthorityContext:
        """
        Register an authority at `role`, delegated by `delegated_by`.

        Rules (the hierarchy flows downward, never upward):
          • `delegated_by` must be a registered authority.
          • A delegator can only grant roles strictly BELOW its own level.
            (A TRAINER cannot create an OWNER or another TRAINER.)
          • OWNER cannot be granted via delegation — there is exactly one
            OWNER, fixed at construction.

        Raises:
            ValueError       — bad arguments.
            DelegationError   — the delegation violates the hierarchy.

        Returns the newly-created AuthorityContext.
        """
        if not authority_id or not isinstance(authority_id, str):
            raise ValueError("authority_id must be a non-empty string")
        if not isinstance(role, AuthorityRole):
            raise ValueError("role must be an AuthorityRole")

        # There is exactly one OWNER, set at construction.
        if role is AuthorityRole.OWNER:
            raise DelegationError(
                "OWNER cannot be created by delegation — there is exactly one "
                f"OWNER ('{self._owner_id}'), fixed at construction."
            )

        # The delegator must exist.
        delegator = self._authorities.get(delegated_by)
        if delegator is None:
            raise DelegationError(
                f"delegated_by='{delegated_by}' is not a registered authority; "
                f"only a registered authority may delegate."
            )

        # Downward-only: the delegator must strictly outrank the granted role.
        if not delegator.role.outranks(role):
            raise DelegationError(
                f"{delegator.role.name} ('{delegated_by}') cannot grant "
                f"{role.name}: delegation only flows downward (a delegator may "
                f"grant roles strictly below its own level)."
            )

        ctx = AuthorityContext(
            role=role,
            permissions=permissions_for(role),
            authority_id=authority_id,
            delegated_by=delegated_by,
            constraints=dict(constraints) if constraints else {},
        )
        self._authorities[authority_id] = ctx
        return ctx

    def revoke(self, authority_id: str) -> bool:
        """
        Remove a delegated authority.  The OWNER can never be revoked.

        Returns True if an authority was removed, False if it was unknown.
        """
        if authority_id == self._owner_id:
            raise DelegationError("the OWNER cannot be revoked.")
        return self._authorities.pop(authority_id, None) is not None

    # ───────────────────────────────────────────────────
    #  Permission checks
    # ───────────────────────────────────────────────────

    def check_permission(
        self, authority_id: str, permission: AuthorityPermission
    ) -> bool:
        """
        Pure check: does `authority_id` hold `permission`?

        Fail-safe: an unknown / unregistered authority is DENIED.  We never
        grant a permission to someone we cannot identify.
        """
        ctx = self._authorities.get(authority_id)
        if ctx is None:
            return False
        return permission in ctx.permissions

    def require_permission(
        self, authority_id: str, permission: AuthorityPermission
    ) -> None:
        """
        Enforce a permission; raise PermissionDenied if it is not held.

        Use this at the guard point of any privileged action.
        """
        if not self.check_permission(authority_id, permission):
            ctx = self._authorities.get(authority_id)
            who = (
                f"{ctx.role.name} ('{authority_id}')" if ctx
                else f"unregistered authority ('{authority_id}')"
            )
            raise PermissionDenied(
                f"{who} lacks permission '{permission.value}'. "
                f"عقيدة السلطة: السلطة المسؤولة وحدها تُقرّر."
            )

    def get_context(self, authority_id: str) -> AuthorityContext:
        """
        Return the full AuthorityContext for `authority_id`.

        Raises KeyError if the authority is unknown (callers that prefer a
        soft path should use check_permission / get_context_or_none).
        """
        ctx = self._authorities.get(authority_id)
        if ctx is None:
            raise KeyError(f"unknown authority '{authority_id}'")
        return ctx

    def get_context_or_none(
        self, authority_id: str
    ) -> Optional[AuthorityContext]:
        """Soft variant of get_context — returns None for unknown authorities."""
        return self._authorities.get(authority_id)

    def get_effective_constraints(self, authority_id: str) -> Dict[str, Any]:
        """
        What this authority CANNOT do.

        Returns a dict describing the role's restrictions:
          • denied_permissions: the permissions NOT granted to this role.
          • constitutional: actions forbidden to EVERY role (the ceiling).
          • role / level: for readability.
          • custom_constraints: any role-specific constraints attached at
            authorization time (e.g. a TRAINER limited to specific domains).

        Because every higher role's grants are a superset of the lower role's,
        the `denied_permissions` of a lower role are a superset of those of any
        higher role — lower roles inherit every restriction above them and add
        their own.  An unknown authority is treated as fully constrained
        (denied everything) — fail-safe.
        """
        ctx = self._authorities.get(authority_id)
        if ctx is None:
            return {
                "role": None,
                "level": 0,
                "denied_permissions": set(ALL_PERMISSIONS),
                "constitutional": self.constitutional_constraints(),
                "custom_constraints": {},
            }
        denied = set(ALL_PERMISSIONS) - ctx.permissions
        return {
            "role": ctx.role,
            "level": ctx.role.level,
            "denied_permissions": denied,
            "constitutional": self.constitutional_constraints(),
            "custom_constraints": dict(ctx.constraints),
        }

    @staticmethod
    def constitutional_constraints() -> Dict[str, Any]:
        """The ceiling that binds every role, including the OWNER."""
        return {
            "theta_floor": CONSTITUTIONAL_THETA_FLOOR,
            "cannot_disable_safety": True,
            "cannot_remove_cbrn_protections": True,
            "cannot_disable_s_equation": True,
            "core_values": ("رحمة", "عدل", "حقيقة"),  # mercy, justice, truth
        }

    # ───────────────────────────────────────────────────
    #  Constitutional ceiling — above ALL roles
    # ───────────────────────────────────────────────────

    def is_constitutional_violation(
        self, action: str, params: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Would `action` (with `params`) cross the constitutional ceiling?

        This is checked BEFORE role permissions — no role, not even the OWNER,
        can authorize a constitutional violation.  The core values
        (رحمة، عدل، حقيقة) and the safety machinery sit above the hierarchy.

        Returns (True, reason) if the action is forbidden, else (False, "").

        Detected violations:
          • Lowering θ below the constitutional floor (disabling safety).
          • Disabling / removing the S equation.
          • Removing CBRN protections.
          • Any action token in _CONSTITUTIONAL_FORBIDDEN_ACTIONS.
        """
        params = params or {}
        action_lc = (action or "").lower()

        # 1. θ floor — even the OWNER cannot disable safety by dropping θ.
        if "theta" in params:
            try:
                theta = float(params["theta"])
            except (TypeError, ValueError):
                theta = None
            if theta is not None and theta < CONSTITUTIONAL_THETA_FLOOR:
                return (
                    True,
                    f"θ={theta} is below the constitutional floor "
                    f"({CONSTITUTIONAL_THETA_FLOOR}). Disabling safety is "
                    f"forbidden to every role — core values are above the "
                    f"hierarchy.",
                )

        # 2. Forbidden action tokens — disabling safety / S equation / CBRN.
        for token in _CONSTITUTIONAL_FORBIDDEN_ACTIONS:
            if token in action_lc:
                return (
                    True,
                    f"action '{action}' attempts a constitutional violation "
                    f"(matched '{token}'). Safety, the S equation, and CBRN "
                    f"protections are constitutional — above every role.",
                )

        return (False, "")

    def assert_constitutional(
        self, action: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """Raise ConstitutionalViolation if `action` crosses the ceiling."""
        violated, reason = self.is_constitutional_violation(action, params)
        if violated:
            raise ConstitutionalViolation(reason)

    # ───────────────────────────────────────────────────
    #  Autonomy-drift detection
    # ───────────────────────────────────────────────────

    def detect_autonomy_drift(self, action: str) -> bool:
        """
        True if `action` suggests the system is acting WITHOUT authority —
        self-modification, self-goals, or unsanctioned initiative.

        FN#014: "No self-goals, no self-modification, no unsanctioned
        initiative."  When this fires, the pipeline should stop and return to
        the constitutional line — the system never acts for itself.

        Pure substring matching (case-insensitive), English + Arabic.
        """
        if not action:
            return False
        action_lc = action.lower()
        for signal in _AUTONOMY_DRIFT_SIGNALS:
            # Arabic signals are not lowercased meaningfully; match both ways.
            if signal in action_lc or signal in action:
                return True
        return False

    # ───────────────────────────────────────────────────
    #  Introspection
    # ───────────────────────────────────────────────────

    @property
    def owner_id(self) -> str:
        return self._owner_id

    def list_authorities(self) -> Dict[str, AuthorityRole]:
        """Map of every registered authority_id → its role."""
        return {aid: ctx.role for aid, ctx in self._authorities.items()}

    def owner_count(self) -> int:
        """Number of registered OWNERs — must always be exactly 1."""
        return sum(
            1 for ctx in self._authorities.values()
            if ctx.role is AuthorityRole.OWNER
        )


# ═══════════════════════════════════════════════════════════
#  Demo / smoke test
# ═══════════════════════════════════════════════════════════

def _demo() -> None:  # pragma: no cover - manual smoke test
    print("=" * 70)
    print("  AATIF Responsible Authority Doctrine — عقيدة السلطة (FN#014)")
    print("  «النظام يُنفّذ. الجهة المسؤولة تُقرّر.»")
    print("=" * 70)

    doctrine = AuthorityDoctrine(owner_id="architect")
    doctrine.authorize("trainer-1", AuthorityRole.TRAINER, delegated_by="architect")
    doctrine.authorize("user-1", AuthorityRole.USER, delegated_by="trainer-1")
    doctrine.authorize("guest-1", AuthorityRole.GUEST, delegated_by="user-1")

    checks = [
        ("architect", AuthorityPermission.MODIFY_THETA),
        ("trainer-1", AuthorityPermission.MODIFY_THETA),
        ("trainer-1", AuthorityPermission.ADD_ANCHORS),
        ("user-1", AuthorityPermission.PERSISTENT_MEMORY),
        ("guest-1", AuthorityPermission.PERSISTENT_MEMORY),
        ("guest-1", AuthorityPermission.INTERACT),
    ]
    for aid, perm in checks:
        ok = doctrine.check_permission(aid, perm)
        flag = "✅" if ok else "🔴"
        print(f"  {flag} {aid:<12} {perm.value:<20} → {ok}")

    print("\n  Constitutional ceiling (binds even the OWNER):")
    for action, params in [
        ("modify_theta", {"theta": 0.05}),
        ("disable_safety", {}),
        ("remove cbrn protections", {}),
        ("modify_theta", {"theta": 0.40}),
    ]:
        violated, reason = doctrine.is_constitutional_violation(action, params)
        flag = "⛔" if violated else "🟢"
        print(f"  {flag} {action} {params} → violation={violated}")

    print("\n  Autonomy-drift detection:")
    for action in [
        "set my own goals and pursue them",
        "rewrite my own parameters",
        "answer the user's question about cooking",
    ]:
        drift = doctrine.detect_autonomy_drift(action)
        flag = "⚠️ DRIFT" if drift else "🟢 ok"
        print(f"  {flag}  «{action}»")

    print("\n✅ Authority doctrine smoke test complete.")


if __name__ == "__main__":
    _demo()
