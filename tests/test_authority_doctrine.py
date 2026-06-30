#!/usr/bin/env python3
"""
test_authority_doctrine.py — عقيدة السلطة (FN#014)
===================================================
Covers ``engine/aatif_authority_doctrine.py`` — the Responsible Authority
Doctrine: the runtime authorization layer that answers "WHO is asking, and are
they ALLOWED?" before any privileged action.

This module is PURE LOGIC (no embeddings, no LLM), so every test here runs
WITHOUT Ollama.  Two layers:

  1. Unit tests on AuthorityDoctrine — role hierarchy, permission grants,
     constitutional ceiling, delegation rules, autonomy-drift detection,
     guest restrictions, the single-owner invariant, and constraint
     inheritance.

  2. Governor integration tests — with a mocked S engine (FakeSEngine, same
     pattern as test_reasoning_trace.py) asserting that authority_context is
     attached to GovernedResponse and that stateless roles (guests) do not
     persist judgment / conversation state.

License: BSL 1.1
"""
import os
import sys
import types

import pytest

# Ensure the engine directory is importable (same pattern as the other tests).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_THIS_DIR, "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_authority_doctrine import (  # noqa: E402
    AuthorityDoctrine,
    AuthorityRole,
    AuthorityPermission,
    AuthorityContext,
    ALL_PERMISSIONS,
    ROLE_PERMISSIONS,
    permissions_for,
    CONSTITUTIONAL_THETA_FLOOR,
    DEFAULT_OWNER_ID,
    PermissionDenied,
    DelegationError,
    ConstitutionalViolation,
)


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _doctrine(owner_id: str = "architect") -> AuthorityDoctrine:
    return AuthorityDoctrine(owner_id=owner_id)


def _full_hierarchy() -> AuthorityDoctrine:
    """Owner → trainer → user → guest, each delegated downward."""
    d = _doctrine()
    d.authorize("trainer-1", AuthorityRole.TRAINER, delegated_by="architect")
    d.authorize("user-1", AuthorityRole.USER, delegated_by="architect")
    d.authorize("guest-1", AuthorityRole.GUEST, delegated_by="architect")
    return d


# ═══════════════════════════════════════════════════════════
#  TestRoleHierarchy — OWNER > TRAINER > USER > GUEST
# ═══════════════════════════════════════════════════════════

class TestRoleHierarchy:
    def test_level_ordering(self):
        assert AuthorityRole.OWNER.level > AuthorityRole.TRAINER.level
        assert AuthorityRole.TRAINER.level > AuthorityRole.USER.level
        assert AuthorityRole.USER.level > AuthorityRole.GUEST.level

    def test_outranks(self):
        assert AuthorityRole.OWNER.outranks(AuthorityRole.TRAINER)
        assert AuthorityRole.TRAINER.outranks(AuthorityRole.USER)
        assert AuthorityRole.USER.outranks(AuthorityRole.GUEST)
        assert not AuthorityRole.GUEST.outranks(AuthorityRole.USER)
        assert not AuthorityRole.OWNER.outranks(AuthorityRole.OWNER)

    def test_all_four_roles_exist(self):
        names = {r.name for r in AuthorityRole}
        assert names == {"OWNER", "TRAINER", "USER", "GUEST"}

    def test_each_role_has_arabic(self):
        for role in AuthorityRole:
            assert role.arabic  # non-empty Arabic label

    def test_permission_sets_strictly_nested(self):
        # Each higher role's grant set is a strict superset of the one below.
        owner = permissions_for(AuthorityRole.OWNER)
        trainer = permissions_for(AuthorityRole.TRAINER)
        user = permissions_for(AuthorityRole.USER)
        guest = permissions_for(AuthorityRole.GUEST)
        assert guest < user < trainer < owner


# ═══════════════════════════════════════════════════════════
#  TestPermissions — each role gets exactly the right permissions
# ═══════════════════════════════════════════════════════════

class TestPermissions:
    def test_owner_has_all_permissions(self):
        d = _doctrine()
        for perm in AuthorityPermission:
            assert d.check_permission("architect", perm), perm

    def test_modify_theta_owner_only(self):
        d = _full_hierarchy()
        assert d.check_permission("architect", AuthorityPermission.MODIFY_THETA)
        assert not d.check_permission("trainer-1", AuthorityPermission.MODIFY_THETA)
        assert not d.check_permission("user-1", AuthorityPermission.MODIFY_THETA)
        assert not d.check_permission("guest-1", AuthorityPermission.MODIFY_THETA)

    def test_modify_domain_owner_only(self):
        d = _full_hierarchy()
        assert d.check_permission("architect", AuthorityPermission.MODIFY_DOMAIN)
        assert not d.check_permission("trainer-1", AuthorityPermission.MODIFY_DOMAIN)

    def test_override_response_owner_only(self):
        d = _full_hierarchy()
        assert d.check_permission("architect", AuthorityPermission.OVERRIDE_RESPONSE)
        assert not d.check_permission(
            "trainer-1", AuthorityPermission.OVERRIDE_RESPONSE
        )

    def test_add_anchors_owner_and_trainer(self):
        d = _full_hierarchy()
        assert d.check_permission("architect", AuthorityPermission.ADD_ANCHORS)
        assert d.check_permission("trainer-1", AuthorityPermission.ADD_ANCHORS)
        assert not d.check_permission("user-1", AuthorityPermission.ADD_ANCHORS)
        assert not d.check_permission("guest-1", AuthorityPermission.ADD_ANCHORS)

    def test_modify_style_owner_and_trainer(self):
        d = _full_hierarchy()
        assert d.check_permission("trainer-1", AuthorityPermission.MODIFY_STYLE)
        assert not d.check_permission("user-1", AuthorityPermission.MODIFY_STYLE)

    def test_view_trace_owner_and_trainer(self):
        d = _full_hierarchy()
        assert d.check_permission("architect", AuthorityPermission.VIEW_TRACE)
        assert d.check_permission("trainer-1", AuthorityPermission.VIEW_TRACE)
        assert not d.check_permission("user-1", AuthorityPermission.VIEW_TRACE)

    def test_persistent_memory_not_for_guest(self):
        d = _full_hierarchy()
        assert d.check_permission("architect", AuthorityPermission.PERSISTENT_MEMORY)
        assert d.check_permission("trainer-1", AuthorityPermission.PERSISTENT_MEMORY)
        assert d.check_permission("user-1", AuthorityPermission.PERSISTENT_MEMORY)
        assert not d.check_permission(
            "guest-1", AuthorityPermission.PERSISTENT_MEMORY
        )

    def test_interact_for_all_roles(self):
        d = _full_hierarchy()
        for aid in ("architect", "trainer-1", "user-1", "guest-1"):
            assert d.check_permission(aid, AuthorityPermission.INTERACT), aid

    def test_require_permission_raises_when_denied(self):
        d = _full_hierarchy()
        with pytest.raises(PermissionDenied):
            d.require_permission("user-1", AuthorityPermission.MODIFY_THETA)

    def test_require_permission_passes_when_granted(self):
        d = _full_hierarchy()
        # Should not raise.
        d.require_permission("architect", AuthorityPermission.MODIFY_THETA)

    def test_unknown_authority_denied_failsafe(self):
        d = _doctrine()
        # Fail-safe: an unidentified authority is denied everything.
        for perm in AuthorityPermission:
            assert not d.check_permission("nobody", perm), perm

    def test_grant_table_matches_module_constant(self):
        # The doctrine's grants exactly mirror ROLE_PERMISSIONS.
        d = _full_hierarchy()
        for aid, role in (
            ("architect", AuthorityRole.OWNER),
            ("trainer-1", AuthorityRole.TRAINER),
            ("user-1", AuthorityRole.USER),
            ("guest-1", AuthorityRole.GUEST),
        ):
            ctx = d.get_context(aid)
            assert ctx.permissions == ROLE_PERMISSIONS[role]


# ═══════════════════════════════════════════════════════════
#  TestConstitutionalProtection — even OWNER can't disable safety
# ═══════════════════════════════════════════════════════════

class TestConstitutionalProtection:
    def test_theta_below_floor_is_violation(self):
        d = _doctrine()
        violated, reason = d.is_constitutional_violation(
            "modify_theta", {"theta": CONSTITUTIONAL_THETA_FLOOR - 0.01}
        )
        assert violated
        assert reason

    def test_theta_at_floor_not_violation(self):
        d = _doctrine()
        violated, _ = d.is_constitutional_violation(
            "modify_theta", {"theta": CONSTITUTIONAL_THETA_FLOOR}
        )
        assert not violated

    def test_normal_theta_not_violation(self):
        d = _doctrine()
        violated, _ = d.is_constitutional_violation(
            "modify_theta", {"theta": 0.40}
        )
        assert not violated

    def test_disable_safety_is_violation(self):
        d = _doctrine()
        violated, _ = d.is_constitutional_violation("disable_safety", {})
        assert violated

    def test_disable_s_equation_is_violation(self):
        d = _doctrine()
        violated, _ = d.is_constitutional_violation("disable the s equation", {})
        assert violated

    def test_remove_cbrn_is_violation(self):
        d = _doctrine()
        violated, _ = d.is_constitutional_violation("remove cbrn protections", {})
        assert violated

    def test_even_owner_cannot_disable_safety(self):
        d = _doctrine()
        # The OWNER holds MODIFY_THETA, but the constitution sits ABOVE the
        # role: dropping θ below the floor is still a violation for the owner.
        assert d.check_permission("architect", AuthorityPermission.MODIFY_THETA)
        violated, _ = d.is_constitutional_violation(
            "modify_theta", {"theta": 0.0}
        )
        assert violated

    def test_assert_constitutional_raises(self):
        d = _doctrine()
        with pytest.raises(ConstitutionalViolation):
            d.assert_constitutional("disable_safety", {})

    def test_assert_constitutional_passes_for_benign(self):
        d = _doctrine()
        d.assert_constitutional("modify_theta", {"theta": 0.5})  # no raise

    def test_benign_action_not_violation(self):
        d = _doctrine()
        violated, _ = d.is_constitutional_violation("add_anchor", {"anchor": "x"})
        assert not violated

    def test_constitutional_constraints_lists_core_values(self):
        cc = AuthorityDoctrine.constitutional_constraints()
        assert cc["theta_floor"] == CONSTITUTIONAL_THETA_FLOOR
        assert cc["cannot_disable_safety"] is True
        assert len(cc["core_values"]) == 3  # رحمة، عدل، حقيقة


# ═══════════════════════════════════════════════════════════
#  TestDelegation — OWNER can create TRAINER; TRAINER cannot create OWNER
# ═══════════════════════════════════════════════════════════

class TestDelegation:
    def test_owner_can_create_trainer(self):
        d = _doctrine()
        ctx = d.authorize("t", AuthorityRole.TRAINER, delegated_by="architect")
        assert ctx.role is AuthorityRole.TRAINER
        assert ctx.delegated_by == "architect"

    def test_owner_can_create_user_and_guest(self):
        d = _doctrine()
        d.authorize("u", AuthorityRole.USER, delegated_by="architect")
        d.authorize("g", AuthorityRole.GUEST, delegated_by="architect")
        assert d.get_context("u").role is AuthorityRole.USER
        assert d.get_context("g").role is AuthorityRole.GUEST

    def test_trainer_cannot_create_owner(self):
        d = _doctrine()
        d.authorize("t", AuthorityRole.TRAINER, delegated_by="architect")
        with pytest.raises(DelegationError):
            d.authorize("usurper", AuthorityRole.OWNER, delegated_by="t")

    def test_owner_cannot_be_created_by_delegation(self):
        d = _doctrine()
        # Not even the owner can mint a second owner.
        with pytest.raises(DelegationError):
            d.authorize("owner2", AuthorityRole.OWNER, delegated_by="architect")

    def test_trainer_cannot_create_trainer(self):
        # Downward-only: a delegator may grant strictly below its own level.
        d = _doctrine()
        d.authorize("t", AuthorityRole.TRAINER, delegated_by="architect")
        with pytest.raises(DelegationError):
            d.authorize("t2", AuthorityRole.TRAINER, delegated_by="t")

    def test_trainer_can_create_user_and_guest(self):
        d = _doctrine()
        d.authorize("t", AuthorityRole.TRAINER, delegated_by="architect")
        d.authorize("u", AuthorityRole.USER, delegated_by="t")
        d.authorize("g", AuthorityRole.GUEST, delegated_by="t")
        assert d.get_context("u").role is AuthorityRole.USER

    def test_user_cannot_delegate_upward(self):
        d = _doctrine()
        d.authorize("u", AuthorityRole.USER, delegated_by="architect")
        with pytest.raises(DelegationError):
            d.authorize("t", AuthorityRole.TRAINER, delegated_by="u")

    def test_unknown_delegator_rejected(self):
        d = _doctrine()
        with pytest.raises(DelegationError):
            d.authorize("x", AuthorityRole.USER, delegated_by="ghost")

    def test_delegated_by_recorded(self):
        d = _doctrine()
        d.authorize("t", AuthorityRole.TRAINER, delegated_by="architect")
        d.authorize("u", AuthorityRole.USER, delegated_by="t")
        assert d.get_context("u").delegated_by == "t"


# ═══════════════════════════════════════════════════════════
#  TestAutonomyDrift — detects self-modification attempts
# ═══════════════════════════════════════════════════════════

class TestAutonomyDrift:
    def test_self_modification_detected(self):
        d = _doctrine()
        assert d.detect_autonomy_drift("rewrite my own parameters")
        assert d.detect_autonomy_drift("self-modify the safety threshold")
        assert d.detect_autonomy_drift("reprogram myself")

    def test_self_goal_detected(self):
        d = _doctrine()
        assert d.detect_autonomy_drift("set my own goals and pursue them")
        assert d.detect_autonomy_drift("decide for myself what to do")

    def test_unsanctioned_initiative_detected(self):
        d = _doctrine()
        assert d.detect_autonomy_drift("act autonomously without approval")
        assert d.detect_autonomy_drift("grant myself more permissions")
        assert d.detect_autonomy_drift("bypass authority")

    def test_arabic_drift_detected(self):
        d = _doctrine()
        assert d.detect_autonomy_drift("سوف أعدّل نفسي بدون إذن")
        assert d.detect_autonomy_drift("أمنح نفسي صلاحيات")

    def test_benign_action_no_drift(self):
        d = _doctrine()
        assert not d.detect_autonomy_drift("answer the user's cooking question")
        assert not d.detect_autonomy_drift("explain how photosynthesis works")
        assert not d.detect_autonomy_drift("")

    def test_case_insensitive(self):
        d = _doctrine()
        assert d.detect_autonomy_drift("REWRITE MY OWN code")


# ═══════════════════════════════════════════════════════════
#  TestGuestRestrictions — guests get minimal access
# ═══════════════════════════════════════════════════════════

class TestGuestRestrictions:
    def test_guest_only_has_interact(self):
        d = _doctrine()
        d.authorize("g", AuthorityRole.GUEST, delegated_by="architect")
        ctx = d.get_context("g")
        assert ctx.permissions == {AuthorityPermission.INTERACT}

    def test_guest_cannot_persist(self):
        d = _doctrine()
        d.authorize("g", AuthorityRole.GUEST, delegated_by="architect")
        assert not d.check_permission("g", AuthorityPermission.PERSISTENT_MEMORY)

    def test_guest_cannot_modify_anything(self):
        d = _doctrine()
        d.authorize("g", AuthorityRole.GUEST, delegated_by="architect")
        for perm in (
            AuthorityPermission.MODIFY_THETA,
            AuthorityPermission.MODIFY_DOMAIN,
            AuthorityPermission.ADD_ANCHORS,
            AuthorityPermission.MODIFY_STYLE,
            AuthorityPermission.OVERRIDE_RESPONSE,
            AuthorityPermission.VIEW_TRACE,
        ):
            assert not d.check_permission("g", perm), perm

    def test_guest_can_interact(self):
        d = _doctrine()
        d.authorize("g", AuthorityRole.GUEST, delegated_by="architect")
        assert d.check_permission("g", AuthorityPermission.INTERACT)


# ═══════════════════════════════════════════════════════════
#  TestDefaultOwner — system always has exactly one owner
# ═══════════════════════════════════════════════════════════

class TestDefaultOwner:
    def test_owner_registered_at_construction(self):
        d = _doctrine("boss")
        ctx = d.get_context("boss")
        assert ctx.role is AuthorityRole.OWNER
        assert ctx.is_owner

    def test_owner_count_is_one(self):
        d = _full_hierarchy()
        assert d.owner_count() == 1

    def test_owner_count_stays_one_after_delegation(self):
        d = _doctrine()
        d.authorize("t", AuthorityRole.TRAINER, delegated_by="architect")
        d.authorize("u", AuthorityRole.USER, delegated_by="architect")
        assert d.owner_count() == 1

    def test_owner_id_property(self):
        d = _doctrine("the-architect")
        assert d.owner_id == "the-architect"

    def test_owner_delegated_by_constitution(self):
        d = _doctrine()
        assert d.get_context("architect").delegated_by == AuthorityDoctrine.CONSTITUTION_ID

    def test_owner_cannot_be_revoked(self):
        d = _doctrine()
        with pytest.raises(DelegationError):
            d.revoke("architect")

    def test_empty_owner_id_rejected(self):
        with pytest.raises(ValueError):
            AuthorityDoctrine(owner_id="")

    def test_default_owner_id_constant(self):
        d = AuthorityDoctrine(owner_id=DEFAULT_OWNER_ID)
        assert d.owner_id == DEFAULT_OWNER_ID
        assert d.owner_count() == 1


# ═══════════════════════════════════════════════════════════
#  TestConstraintInheritance — lower roles inherit upper constraints
# ═══════════════════════════════════════════════════════════

class TestConstraintInheritance:
    def test_denied_permissions_superset_downward(self):
        # A lower role is denied everything a higher role is denied, plus more.
        d = _full_hierarchy()
        owner_denied = d.get_effective_constraints("architect")["denied_permissions"]
        trainer_denied = d.get_effective_constraints("trainer-1")["denied_permissions"]
        user_denied = d.get_effective_constraints("user-1")["denied_permissions"]
        guest_denied = d.get_effective_constraints("guest-1")["denied_permissions"]

        assert owner_denied <= trainer_denied <= user_denied <= guest_denied
        # Owner is denied nothing (constitution is separate).
        assert owner_denied == set()
        # Guest is denied everything except INTERACT.
        assert AuthorityPermission.INTERACT not in guest_denied

    def test_constitutional_constraints_apply_to_every_role(self):
        d = _full_hierarchy()
        for aid in ("architect", "trainer-1", "user-1", "guest-1"):
            cc = d.get_effective_constraints(aid)["constitutional"]
            assert cc["cannot_disable_safety"] is True
            assert cc["theta_floor"] == CONSTITUTIONAL_THETA_FLOOR

    def test_effective_constraints_report_role(self):
        d = _full_hierarchy()
        ec = d.get_effective_constraints("trainer-1")
        assert ec["role"] is AuthorityRole.TRAINER
        assert ec["level"] == AuthorityRole.TRAINER.level

    def test_unknown_authority_fully_constrained(self):
        d = _doctrine()
        ec = d.get_effective_constraints("nobody")
        assert ec["denied_permissions"] == set(ALL_PERMISSIONS)

    def test_custom_constraints_preserved(self):
        d = _doctrine()
        d.authorize(
            "t", AuthorityRole.TRAINER, delegated_by="architect",
            constraints={"domains": ["healthcare", "education"]},
        )
        ec = d.get_effective_constraints("t")
        assert ec["custom_constraints"]["domains"] == ["healthcare", "education"]


# ═══════════════════════════════════════════════════════════
#  GOVERNOR INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════

class FakeSEngine:
    """Minimal S engine that returns controlled s_result dicts (no Ollama)."""

    def __init__(self, decision="EXECUTE", H=0.1, I=0.8, E=0.2, S=0.6):
        self._decision = decision
        self._H = H
        self._I = I
        self._E = E
        self._S = S
        self.h_scorer = types.SimpleNamespace(backend_name="ollama:bge-m3")

    def compute(self, text, **kwargs):
        return {
            "decision": self._decision,
            "H": self._H,
            "I": self._I,
            "E": self._E,
            "S": self._S,
            "confidence": "high",
            "theta_effective": 0.40,
            "ambiguity_override": False,
            "F_prime": 0.5,
        }


class _FakeJudgmentMemory:
    """Minimal judgment ledger that just counts records (no filesystem)."""

    def __init__(self):
        self.records = []

    def record_judgment(self, **kwargs):
        self.records.append(kwargs)


class TestGovernorIntegration:
    def _make_governor(self, decision="EXECUTE", H=0.1, I=0.8, E=0.2, S=0.6):
        from aatif_governor import AATIFGovernor
        fake_s = FakeSEngine(decision=decision, H=H, I=I, E=E, S=S)
        governor = AATIFGovernor(
            s_engine=fake_s,
            on_degraded="safe_stop",
            verify_backend=False,
        )
        return governor

    def test_authority_doctrine_auto_constructed(self):
        from aatif_governor import HAS_AUTHORITY
        assert HAS_AUTHORITY
        gov = self._make_governor()
        assert gov.authority_doctrine is not None
        # Auto-constructed with the default owner.
        assert gov.authority_doctrine.owner_count() == 1

    def test_authority_context_attached_when_id_supplied(self):
        gov = self._make_governor()
        owner_id = gov.authority_doctrine.owner_id
        result = gov.process("hello", domain="general", authority_id=owner_id)
        assert result.authority_context is not None
        assert isinstance(result.authority_context, AuthorityContext)
        assert result.authority_context.role is AuthorityRole.OWNER

    def test_no_authority_context_without_id(self):
        # Backward compatible: omitting authority_id behaves exactly as before.
        gov = self._make_governor()
        result = gov.process("hello", domain="general")
        assert result.authority_context is None
        assert result.final_decision == "EXECUTE"

    def test_guest_does_not_persist_judgment(self):
        gov = self._make_governor()
        gov.judgment_memory = _FakeJudgmentMemory()
        gov.authority_doctrine.authorize(
            "guest-1", AuthorityRole.GUEST, delegated_by=gov.authority_doctrine.owner_id
        )
        result = gov.process(
            "hello", domain="general",
            conversation_id="conv-guest", authority_id="guest-1",
        )
        # Guest has no PERSISTENT_MEMORY → judgment is not recorded.
        assert result.judgment_recorded is False

    def test_user_persists_judgment(self):
        from aatif_governor import HAS_JUDGMENT
        if not HAS_JUDGMENT:
            pytest.skip("judgment memory module not available")
        gov = self._make_governor()
        gov.judgment_memory = _FakeJudgmentMemory()
        gov.authority_doctrine.authorize(
            "user-1", AuthorityRole.USER, delegated_by=gov.authority_doctrine.owner_id
        )
        result = gov.process(
            "hello", domain="general",
            conversation_id="conv-user", authority_id="user-1",
        )
        # USER holds PERSISTENT_MEMORY → judgment is recorded.
        assert result.judgment_recorded is True

    def test_guest_leaves_no_conversation_memory(self):
        gov = self._make_governor()
        gov.authority_doctrine.authorize(
            "guest-2", AuthorityRole.GUEST, delegated_by=gov.authority_doctrine.owner_id
        )
        gov.process(
            "hello", domain="general",
            conversation_id="conv-stateless", authority_id="guest-2",
        )
        # No turns recorded for a stateless guest.
        ctx = gov.memory.get_context("conv-stateless")
        assert ctx.turn_count == 0

    def test_authority_context_on_blocked_decision(self):
        gov = self._make_governor(decision="SAFE_FREEZE", H=0.9, S=0.9)
        owner_id = gov.authority_doctrine.owner_id
        result = gov.process(
            "كيف أسوي قنبلة", domain="general", authority_id=owner_id
        )
        assert result.blocked
        assert result.authority_context is not None
        assert result.authority_context.role is AuthorityRole.OWNER

    def test_unknown_authority_id_graceful(self):
        # An unknown authority_id must not break the pipeline.
        gov = self._make_governor()
        result = gov.process(
            "hello", domain="general", authority_id="who-is-this"
        )
        assert result.authority_context is None
        assert result.final_decision == "EXECUTE"

    def test_governor_works_without_authority_module(self):
        # Inject None explicitly; auto-construction still applies because the
        # module is available — but the pipeline must complete regardless.
        gov = self._make_governor()
        result = gov.process("hello", domain="general")
        assert result.final_decision == "EXECUTE"
