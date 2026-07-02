#!/usr/bin/env python3
"""
test_change_tracker.py — سجل التغيير (FN#034 + FN#014)
======================================================
Covers ``engine/aatif_change_tracker.py`` — the Change Traceability Module:
append-only hash-chained change log with authority validation.

This module is PURE LOGIC (no embeddings, no LLM), so every test here runs
WITHOUT Ollama.  Layers:

  1. ChangeType enum — all six types exist and are distinct.
  2. ChangeRecord — creation, immutability, hashing, serialisation.
  3. ChangeLog — append-only, hash chain, queries, verification, summary.
  4. ChangeTracker — high-level API, convenience recorders, authority
     validation (B-prime: flag never block), integration with
     AuthorityDoctrine.
  5. Edge cases — empty logs, single records, large logs, unicode,
     Arabic justifications, hash determinism.

License: BSL 1.1
"""
import os
import sys
import hashlib
import json
import time
from datetime import datetime, timezone

import pytest

# Ensure the engine directory is importable (same pattern as the other tests).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_THIS_DIR, "..", "engine")
sys.path.insert(0, os.path.abspath(_ENGINE_DIR))

from aatif_change_tracker import (  # noqa: E402
    CAN_BLOCK_RUNTIME,
    ChangeType,
    ChangeRecord,
    ChangeLog,
    ChangeTracker,
    _compute_hash,
    _serialise_value,
)
from aatif_authority_doctrine import (  # noqa: E402
    AuthorityDoctrine,
    AuthorityRole,
    AuthorityPermission,
)


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _tracker(**kwargs) -> ChangeTracker:
    """Create a ChangeTracker with optional kwargs."""
    return ChangeTracker(**kwargs)


def _tracker_with_doctrine() -> ChangeTracker:
    """Tracker backed by a full-hierarchy AuthorityDoctrine."""
    doctrine = AuthorityDoctrine(owner_id="architect")
    doctrine.authorize("trainer-1", AuthorityRole.TRAINER, delegated_by="architect")
    doctrine.authorize("user-1", AuthorityRole.USER, delegated_by="architect")
    doctrine.authorize("guest-1", AuthorityRole.GUEST, delegated_by="architect")
    return ChangeTracker(authority_doctrine=doctrine)


def _fixed_ts(n: int = 0) -> str:
    """Deterministic ISO 8601 timestamps for testing."""
    return f"2025-01-15T10:00:{n:02d}+00:00"


# ═══════════════════════════════════════════════════════════
#  1. CAN_BLOCK_RUNTIME — B-prime constant
# ═══════════════════════════════════════════════════════════

class TestBPrime:
    def test_can_block_runtime_is_false(self):
        """B-prime: the tracker NEVER blocks runtime."""
        assert CAN_BLOCK_RUNTIME is False


# ═══════════════════════════════════════════════════════════
#  2. ChangeType enum
# ═══════════════════════════════════════════════════════════

class TestChangeType:
    def test_all_six_types_exist(self):
        assert len(ChangeType) == 6

    def test_anchor_add(self):
        assert ChangeType.ANCHOR_ADD.value == "anchor_add"

    def test_anchor_remove(self):
        assert ChangeType.ANCHOR_REMOVE.value == "anchor_remove"

    def test_threshold_modify(self):
        assert ChangeType.THRESHOLD_MODIFY.value == "threshold_modify"

    def test_domain_config(self):
        assert ChangeType.DOMAIN_CONFIG.value == "domain_config"

    def test_observer_toggle(self):
        assert ChangeType.OBSERVER_TOGGLE.value == "observer_toggle"

    def test_authority_change(self):
        assert ChangeType.AUTHORITY_CHANGE.value == "authority_change"

    def test_all_values_unique(self):
        values = [ct.value for ct in ChangeType]
        assert len(values) == len(set(values))

    def test_enum_members_are_distinct(self):
        assert ChangeType.ANCHOR_ADD is not ChangeType.ANCHOR_REMOVE
        assert ChangeType.THRESHOLD_MODIFY is not ChangeType.DOMAIN_CONFIG


# ═══════════════════════════════════════════════════════════
#  3. _serialise_value helper
# ═══════════════════════════════════════════════════════════

class TestSerialiseValue:
    def test_none(self):
        assert _serialise_value(None) is None

    def test_string(self):
        assert _serialise_value("hello") == "hello"

    def test_int(self):
        assert _serialise_value(42) == 42

    def test_float(self):
        assert _serialise_value(3.14) == 3.14

    def test_bool(self):
        assert _serialise_value(True) is True

    def test_list(self):
        assert _serialise_value([1, "a", None]) == [1, "a", None]

    def test_tuple(self):
        assert _serialise_value((1, 2, 3)) == [1, 2, 3]

    def test_set_sorted(self):
        result = _serialise_value({3, 1, 2})
        assert result == [1, 2, 3]

    def test_dict_sorted_keys(self):
        result = _serialise_value({"b": 2, "a": 1})
        assert result == {"a": 1, "b": 2}

    def test_nested(self):
        result = _serialise_value({"key": [1, {2, 3}]})
        assert result == {"key": [1, [2, 3]]}

    def test_custom_object_str(self):
        class Custom:
            def __str__(self):
                return "custom_obj"
        assert _serialise_value(Custom()) == "custom_obj"


# ═══════════════════════════════════════════════════════════
#  4. _compute_hash
# ═══════════════════════════════════════════════════════════

class TestComputeHash:
    def test_returns_hex_string(self):
        h = _compute_hash(
            timestamp=_fixed_ts(),
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            justification="test",
            constitutional_basis=(1,),
            authority_valid=True,
            authority_flag="",
            prev_hash="",
        )
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest

    def test_deterministic(self):
        args = dict(
            timestamp=_fixed_ts(),
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            justification="why",
            constitutional_basis=(5,),
            authority_valid=True,
            authority_flag="",
            prev_hash="abc",
        )
        h1 = _compute_hash(**args)
        h2 = _compute_hash(**args)
        assert h1 == h2

    def test_different_inputs_different_hashes(self):
        base = dict(
            timestamp=_fixed_ts(),
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            justification="why",
            constitutional_basis=(5,),
            authority_valid=True,
            authority_flag="",
            prev_hash="",
        )
        h1 = _compute_hash(**base)
        h2 = _compute_hash(**{**base, "component": "other"})
        assert h1 != h2

    def test_prev_hash_affects_output(self):
        base = dict(
            timestamp=_fixed_ts(),
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            justification="why",
            constitutional_basis=(5,),
            authority_valid=True,
            authority_flag="",
        )
        h1 = _compute_hash(**base, prev_hash="aaa")
        h2 = _compute_hash(**base, prev_hash="bbb")
        assert h1 != h2

    def test_unicode_in_justification(self):
        h = _compute_hash(
            timestamp=_fixed_ts(),
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            justification="إضافة مرساة أمان عربية",
            constitutional_basis=(29,),
            authority_valid=True,
            authority_flag="",
            prev_hash="",
        )
        assert isinstance(h, str)
        assert len(h) == 64


# ═══════════════════════════════════════════════════════════
#  5. ChangeRecord
# ═══════════════════════════════════════════════════════════

class TestChangeRecord:
    def _make_record(self, **overrides) -> ChangeRecord:
        defaults = dict(
            timestamp=_fixed_ts(),
            change_type=ChangeType.ANCHOR_ADD,
            component="intent_scorer",
            old_value=None,
            new_value={"word": "danger", "weight": 0.9},
            authority_id="architect",
            justification="Adding harm anchor",
            constitutional_basis=(29, 5),
            authority_valid=True,
            authority_flag="",
            prev_hash="",
            hash="abc123",
        )
        defaults.update(overrides)
        return ChangeRecord(**defaults)

    def test_creation(self):
        rec = self._make_record()
        assert rec.change_type == ChangeType.ANCHOR_ADD
        assert rec.component == "intent_scorer"
        assert rec.authority_id == "architect"
        assert rec.authority_valid is True

    def test_frozen(self):
        rec = self._make_record()
        with pytest.raises(AttributeError):
            rec.component = "other"  # type: ignore

    def test_to_dict(self):
        rec = self._make_record()
        d = rec.to_dict()
        assert d["change_type"] == "anchor_add"
        assert d["component"] == "intent_scorer"
        assert d["constitutional_basis"] == [29, 5]
        assert d["hash"] == "abc123"
        assert isinstance(d, dict)

    def test_to_dict_has_all_fields(self):
        rec = self._make_record()
        d = rec.to_dict()
        expected_keys = {
            "timestamp", "change_type", "component", "old_value",
            "new_value", "authority_id", "justification",
            "constitutional_basis", "authority_valid", "authority_flag",
            "prev_hash", "hash",
        }
        assert set(d.keys()) == expected_keys

    def test_invalid_authority_flag(self):
        rec = self._make_record(
            authority_valid=False,
            authority_flag="Insufficient permission",
        )
        assert rec.authority_valid is False
        assert "Insufficient" in rec.authority_flag


# ═══════════════════════════════════════════════════════════
#  6. ChangeLog — append-only with hash chain
# ═══════════════════════════════════════════════════════════

class TestChangeLog:
    def _make_log_record(
        self, prev_hash: str = "", **overrides
    ) -> ChangeRecord:
        """Create a record with a valid hash for the given prev_hash."""
        defaults = dict(
            timestamp=_fixed_ts(),
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            justification="test",
            constitutional_basis=(1,),
            authority_valid=True,
            authority_flag="",
        )
        defaults.update(overrides)
        h = _compute_hash(prev_hash=prev_hash, **defaults)
        return ChangeRecord(prev_hash=prev_hash, hash=h, **defaults)

    def test_empty_log(self):
        log = ChangeLog()
        assert log.length == 0
        assert log.all_records() == []
        assert log.last_hash == ""

    def test_append_single(self):
        log = ChangeLog()
        rec = self._make_log_record(prev_hash="")
        log.append(rec)
        assert log.length == 1
        assert log.get(0) is rec

    def test_append_chain(self):
        log = ChangeLog()
        r1 = self._make_log_record(prev_hash="", component="a")
        log.append(r1)
        r2 = self._make_log_record(prev_hash=r1.hash, component="b")
        log.append(r2)
        assert log.length == 2
        assert log.get(1).prev_hash == r1.hash

    def test_append_wrong_prev_hash_raises(self):
        log = ChangeLog()
        r1 = self._make_log_record(prev_hash="")
        log.append(r1)
        bad = self._make_log_record(prev_hash="wrong_hash", component="b")
        with pytest.raises(ValueError, match="Hash chain broken"):
            log.append(bad)

    def test_last_hash_updates(self):
        log = ChangeLog()
        assert log.last_hash == ""
        r1 = self._make_log_record(prev_hash="")
        log.append(r1)
        assert log.last_hash == r1.hash
        r2 = self._make_log_record(prev_hash=r1.hash, component="b")
        log.append(r2)
        assert log.last_hash == r2.hash

    def test_all_records_returns_copy(self):
        log = ChangeLog()
        r1 = self._make_log_record(prev_hash="")
        log.append(r1)
        records = log.all_records()
        records.clear()
        assert log.length == 1  # original unaffected

    def test_get_out_of_range(self):
        log = ChangeLog()
        with pytest.raises(IndexError):
            log.get(0)

    # ─── Verify chain ────────────────────────────────────

    def test_verify_empty_log(self):
        log = ChangeLog()
        valid, reason = log.verify_chain()
        assert valid is True
        assert reason == ""

    def test_verify_single_record(self):
        log = ChangeLog()
        r1 = self._make_log_record(prev_hash="")
        log.append(r1)
        valid, reason = log.verify_chain()
        assert valid is True

    def test_verify_multi_record_chain(self):
        log = ChangeLog()
        r1 = self._make_log_record(prev_hash="", component="a")
        log.append(r1)
        r2 = self._make_log_record(prev_hash=r1.hash, component="b")
        log.append(r2)
        r3 = self._make_log_record(prev_hash=r2.hash, component="c")
        log.append(r3)
        valid, reason = log.verify_chain()
        assert valid is True

    # ─── Query ───────────────────────────────────────────

    def test_query_by_component(self):
        log = ChangeLog()
        r1 = self._make_log_record(prev_hash="", component="alpha")
        log.append(r1)
        r2 = self._make_log_record(prev_hash=r1.hash, component="beta")
        log.append(r2)
        results = log.query(component="alpha")
        assert len(results) == 1
        assert results[0].component == "alpha"

    def test_query_by_authority(self):
        log = ChangeLog()
        r1 = self._make_log_record(prev_hash="", authority_id="alice")
        log.append(r1)
        r2 = self._make_log_record(prev_hash=r1.hash, authority_id="bob")
        log.append(r2)
        results = log.query(authority_id="bob")
        assert len(results) == 1
        assert results[0].authority_id == "bob"

    def test_query_by_change_type(self):
        log = ChangeLog()
        r1 = self._make_log_record(
            prev_hash="", change_type=ChangeType.ANCHOR_ADD
        )
        log.append(r1)
        r2 = self._make_log_record(
            prev_hash=r1.hash, change_type=ChangeType.THRESHOLD_MODIFY
        )
        log.append(r2)
        results = log.query(change_type=ChangeType.THRESHOLD_MODIFY)
        assert len(results) == 1

    def test_query_by_time_range(self):
        log = ChangeLog()
        r1 = self._make_log_record(
            prev_hash="", timestamp="2025-01-01T00:00:00+00:00"
        )
        log.append(r1)
        r2 = self._make_log_record(
            prev_hash=r1.hash, timestamp="2025-06-15T00:00:00+00:00"
        )
        log.append(r2)
        r3 = self._make_log_record(
            prev_hash=r2.hash, timestamp="2025-12-31T00:00:00+00:00"
        )
        log.append(r3)

        results = log.query(
            start_time="2025-03-01T00:00:00+00:00",
            end_time="2025-09-01T00:00:00+00:00",
        )
        assert len(results) == 1
        assert results[0].timestamp == "2025-06-15T00:00:00+00:00"

    def test_query_by_authority_valid(self):
        log = ChangeLog()
        r1 = self._make_log_record(prev_hash="", authority_valid=True)
        log.append(r1)
        r2 = self._make_log_record(
            prev_hash=r1.hash, authority_valid=False,
            authority_flag="flagged",
        )
        log.append(r2)
        flagged = log.query(authority_valid=False)
        assert len(flagged) == 1
        assert flagged[0].authority_valid is False

    def test_query_multiple_filters(self):
        log = ChangeLog()
        r1 = self._make_log_record(
            prev_hash="", component="alpha", authority_id="alice"
        )
        log.append(r1)
        r2 = self._make_log_record(
            prev_hash=r1.hash, component="alpha", authority_id="bob"
        )
        log.append(r2)
        r3 = self._make_log_record(
            prev_hash=r2.hash, component="beta", authority_id="alice"
        )
        log.append(r3)
        results = log.query(component="alpha", authority_id="alice")
        assert len(results) == 1

    def test_query_no_match(self):
        log = ChangeLog()
        r1 = self._make_log_record(prev_hash="", component="alpha")
        log.append(r1)
        results = log.query(component="nonexistent")
        assert len(results) == 0

    def test_query_no_filters_returns_all(self):
        log = ChangeLog()
        r1 = self._make_log_record(prev_hash="", component="a")
        log.append(r1)
        r2 = self._make_log_record(prev_hash=r1.hash, component="b")
        log.append(r2)
        results = log.query()
        assert len(results) == 2

    # ─── Summary ─────────────────────────────────────────

    def test_summary_empty(self):
        log = ChangeLog()
        s = log.summary()
        assert s["total_records"] == 0
        assert s["chain_valid"] is True
        assert s["invalid_authority_count"] == 0

    def test_summary_counts(self):
        log = ChangeLog()
        r1 = self._make_log_record(
            prev_hash="", component="a",
            change_type=ChangeType.ANCHOR_ADD,
            authority_id="alice",
        )
        log.append(r1)
        r2 = self._make_log_record(
            prev_hash=r1.hash, component="b",
            change_type=ChangeType.ANCHOR_ADD,
            authority_id="alice",
        )
        log.append(r2)
        r3 = self._make_log_record(
            prev_hash=r2.hash, component="a",
            change_type=ChangeType.THRESHOLD_MODIFY,
            authority_id="bob",
        )
        log.append(r3)
        s = log.summary()
        assert s["total_records"] == 3
        assert s["changes_by_type"]["anchor_add"] == 2
        assert s["changes_by_type"]["threshold_modify"] == 1
        assert s["changes_by_component"]["a"] == 2
        assert s["changes_by_component"]["b"] == 1
        assert s["changes_by_authority"]["alice"] == 2
        assert s["changes_by_authority"]["bob"] == 1


# ═══════════════════════════════════════════════════════════
#  7. ChangeTracker — high-level API (no doctrine)
# ═══════════════════════════════════════════════════════════

class TestChangeTrackerBasic:
    def test_creation(self):
        t = _tracker()
        assert t.length == 0

    def test_record_returns_change_record(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="intent_scorer",
            old_value=None,
            new_value={"word": "danger"},
            authority_id="architect",
        )
        assert isinstance(rec, ChangeRecord)
        assert t.length == 1

    def test_record_auto_timestamp(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
        )
        # Should be a valid ISO 8601 timestamp.
        assert "T" in rec.timestamp
        assert ":" in rec.timestamp

    def test_record_explicit_timestamp(self):
        t = _tracker()
        ts = _fixed_ts(42)
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            timestamp=ts,
        )
        assert rec.timestamp == ts

    def test_record_hash_chain(self):
        t = _tracker()
        r1 = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="a",
            old_value=None,
            new_value="x",
            authority_id="arch",
            timestamp=_fixed_ts(1),
        )
        r2 = t.record(
            change_type=ChangeType.ANCHOR_REMOVE,
            component="b",
            old_value="y",
            new_value=None,
            authority_id="arch",
            timestamp=_fixed_ts(2),
        )
        assert r1.prev_hash == ""
        assert r2.prev_hash == r1.hash

    def test_record_verify_chain_valid(self):
        t = _tracker()
        for i in range(5):
            t.record(
                change_type=ChangeType.ANCHOR_ADD,
                component=f"mod_{i}",
                old_value=None,
                new_value=i,
                authority_id="arch",
                timestamp=_fixed_ts(i),
            )
        valid, reason = t.verify_chain()
        assert valid is True

    def test_record_constitutional_basis_tuple(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            constitutional_basis=(29, 5, 82),
        )
        assert rec.constitutional_basis == (29, 5, 82)

    def test_record_constitutional_basis_list_sorted(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            constitutional_basis=[82, 5, 29],
        )
        assert rec.constitutional_basis == (5, 29, 82)

    def test_record_constitutional_basis_set_sorted(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            constitutional_basis={82, 5, 29},
        )
        assert rec.constitutional_basis == (5, 29, 82)

    def test_record_empty_constitutional_basis(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
        )
        assert rec.constitutional_basis == ()

    def test_record_without_doctrine_always_valid(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.THRESHOLD_MODIFY,
            component="test",
            old_value=0.5,
            new_value=0.6,
            authority_id="random_user",
        )
        assert rec.authority_valid is True
        assert rec.authority_flag == ""

    def test_record_invalid_change_type_raises(self):
        t = _tracker()
        with pytest.raises(TypeError):
            t.record(
                change_type="not_an_enum",
                component="test",
                old_value=None,
                new_value="x",
                authority_id="arch",
            )

    def test_record_empty_component_raises(self):
        t = _tracker()
        with pytest.raises(ValueError, match="component"):
            t.record(
                change_type=ChangeType.ANCHOR_ADD,
                component="",
                old_value=None,
                new_value="x",
                authority_id="arch",
            )

    def test_record_empty_authority_raises(self):
        t = _tracker()
        with pytest.raises(ValueError, match="authority_id"):
            t.record(
                change_type=ChangeType.ANCHOR_ADD,
                component="test",
                old_value=None,
                new_value="x",
                authority_id="",
            )

    def test_all_records(self):
        t = _tracker()
        t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="a",
            old_value=None,
            new_value="x",
            authority_id="arch",
            timestamp=_fixed_ts(1),
        )
        t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="b",
            old_value=None,
            new_value="y",
            authority_id="arch",
            timestamp=_fixed_ts(2),
        )
        records = t.all_records()
        assert len(records) == 2
        assert records[0].component == "a"
        assert records[1].component == "b"

    def test_query_delegates_to_log(self):
        t = _tracker()
        t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="alpha",
            old_value=None,
            new_value="x",
            authority_id="arch",
            timestamp=_fixed_ts(1),
        )
        t.record(
            change_type=ChangeType.THRESHOLD_MODIFY,
            component="beta",
            old_value=0.5,
            new_value=0.6,
            authority_id="arch",
            timestamp=_fixed_ts(2),
        )
        results = t.query(component="alpha")
        assert len(results) == 1

    def test_summary_delegates(self):
        t = _tracker()
        t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
        )
        s = t.summary()
        assert s["total_records"] == 1

    def test_log_property(self):
        t = _tracker()
        assert isinstance(t.log, ChangeLog)


# ═══════════════════════════════════════════════════════════
#  8. Convenience recorders
# ═══════════════════════════════════════════════════════════

class TestConvenienceRecorders:
    def test_record_anchor_add(self):
        t = _tracker()
        rec = t.record_anchor_add(
            component="intent_scorer",
            anchor_data={"word": "خطر", "weight": 0.9},
            authority_id="architect",
            justification="Adding Arabic harm anchor",
            constitutional_basis=(29, 5),
        )
        assert rec.change_type == ChangeType.ANCHOR_ADD
        assert rec.component == "intent_scorer"
        assert rec.old_value is None
        assert rec.new_value == {"word": "خطر", "weight": 0.9}

    def test_record_anchor_remove(self):
        t = _tracker()
        rec = t.record_anchor_remove(
            component="intent_scorer",
            anchor_data={"word": "danger", "weight": 0.8},
            authority_id="architect",
        )
        assert rec.change_type == ChangeType.ANCHOR_REMOVE
        assert rec.old_value == {"word": "danger", "weight": 0.8}
        assert rec.new_value is None

    def test_record_threshold_modify(self):
        t = _tracker()
        rec = t.record_threshold_modify(
            component="s_equation",
            param_name="theta",
            old_value=0.50,
            new_value=0.55,
            authority_id="architect",
            justification="Tightening safety threshold",
            constitutional_basis=(29, 52),
        )
        assert rec.change_type == ChangeType.THRESHOLD_MODIFY
        assert rec.old_value == {"param": "theta", "value": 0.50}
        assert rec.new_value == {"param": "theta", "value": 0.55}

    def test_record_domain_config(self):
        t = _tracker()
        rec = t.record_domain_config(
            component="domain_protocols",
            old_config={"domain": "healthcare", "theta": 0.30},
            new_config={"domain": "healthcare", "theta": 0.25},
            authority_id="architect",
        )
        assert rec.change_type == ChangeType.DOMAIN_CONFIG
        assert rec.old_value["theta"] == 0.30
        assert rec.new_value["theta"] == 0.25

    def test_record_observer_toggle_enable(self):
        t = _tracker()
        rec = t.record_observer_toggle(
            observer_name="drift_detector",
            enabled=True,
            authority_id="architect",
        )
        assert rec.change_type == ChangeType.OBSERVER_TOGGLE
        assert rec.component == "observer_registry"
        assert rec.new_value["enabled"] is True
        assert rec.old_value["enabled"] is False

    def test_record_observer_toggle_disable(self):
        t = _tracker()
        rec = t.record_observer_toggle(
            observer_name="fgd",
            enabled=False,
            authority_id="architect",
        )
        assert rec.new_value["enabled"] is False
        assert rec.old_value["enabled"] is True

    def test_record_authority_change(self):
        t = _tracker()
        rec = t.record_authority_change(
            authority_target="alice",
            old_role=None,
            new_role="TRAINER",
            authority_id="architect",
            justification="Delegating training authority",
            constitutional_basis=(14,),
        )
        assert rec.change_type == ChangeType.AUTHORITY_CHANGE
        assert rec.component == "authority_doctrine"
        assert rec.old_value["role"] is None
        assert rec.new_value["role"] == "TRAINER"


# ═══════════════════════════════════════════════════════════
#  9. Authority validation (B-prime: flag, never block)
# ═══════════════════════════════════════════════════════════

class TestAuthorityValidation:
    def test_owner_anchor_add_valid(self):
        t = _tracker_with_doctrine()
        rec = t.record_anchor_add(
            component="intent_scorer",
            anchor_data="x",
            authority_id="architect",
        )
        assert rec.authority_valid is True
        assert rec.authority_flag == ""

    def test_trainer_anchor_add_valid(self):
        t = _tracker_with_doctrine()
        rec = t.record_anchor_add(
            component="intent_scorer",
            anchor_data="x",
            authority_id="trainer-1",
        )
        assert rec.authority_valid is True

    def test_user_anchor_add_flagged(self):
        """USER lacks ADD_ANCHORS → flagged but NOT blocked."""
        t = _tracker_with_doctrine()
        rec = t.record_anchor_add(
            component="intent_scorer",
            anchor_data="x",
            authority_id="user-1",
        )
        assert rec.authority_valid is False
        assert "lacks" in rec.authority_flag
        assert "add_anchors" in rec.authority_flag
        # B-prime: the record was still created!
        assert t.length == 1

    def test_guest_anchor_add_flagged(self):
        t = _tracker_with_doctrine()
        rec = t.record_anchor_add(
            component="intent_scorer",
            anchor_data="x",
            authority_id="guest-1",
        )
        assert rec.authority_valid is False
        assert t.length == 1

    def test_owner_threshold_modify_valid(self):
        t = _tracker_with_doctrine()
        rec = t.record_threshold_modify(
            component="s_eq",
            param_name="theta",
            old_value=0.5,
            new_value=0.6,
            authority_id="architect",
        )
        assert rec.authority_valid is True

    def test_trainer_threshold_modify_flagged(self):
        """TRAINER lacks MODIFY_THETA → flagged."""
        t = _tracker_with_doctrine()
        rec = t.record_threshold_modify(
            component="s_eq",
            param_name="theta",
            old_value=0.5,
            new_value=0.6,
            authority_id="trainer-1",
        )
        assert rec.authority_valid is False
        assert "modify_theta" in rec.authority_flag

    def test_user_threshold_modify_flagged(self):
        t = _tracker_with_doctrine()
        rec = t.record_threshold_modify(
            component="s_eq",
            param_name="theta",
            old_value=0.5,
            new_value=0.6,
            authority_id="user-1",
        )
        assert rec.authority_valid is False

    def test_owner_domain_config_valid(self):
        t = _tracker_with_doctrine()
        rec = t.record_domain_config(
            component="domain_protocols",
            old_config={},
            new_config={"x": 1},
            authority_id="architect",
        )
        assert rec.authority_valid is True

    def test_trainer_domain_config_flagged(self):
        """TRAINER lacks MODIFY_DOMAIN → flagged."""
        t = _tracker_with_doctrine()
        rec = t.record_domain_config(
            component="domain_protocols",
            old_config={},
            new_config={"x": 1},
            authority_id="trainer-1",
        )
        assert rec.authority_valid is False

    def test_owner_authority_change_valid(self):
        t = _tracker_with_doctrine()
        rec = t.record_authority_change(
            authority_target="alice",
            old_role=None,
            new_role="TRAINER",
            authority_id="architect",
        )
        assert rec.authority_valid is True

    def test_trainer_authority_change_flagged(self):
        """TRAINER lacks MODIFY_THETA (OWNER-only) → flagged."""
        t = _tracker_with_doctrine()
        rec = t.record_authority_change(
            authority_target="bob",
            old_role=None,
            new_role="USER",
            authority_id="trainer-1",
        )
        assert rec.authority_valid is False

    def test_unregistered_authority_flagged(self):
        """Unknown authority → flagged with 'not registered'."""
        t = _tracker_with_doctrine()
        rec = t.record_anchor_add(
            component="test",
            anchor_data="x",
            authority_id="unknown_person",
        )
        assert rec.authority_valid is False
        assert "not registered" in rec.authority_flag

    def test_flagged_changes_queryable(self):
        """All flagged changes can be queried."""
        t = _tracker_with_doctrine()
        t.record_anchor_add(
            component="test", anchor_data="x", authority_id="architect",
        )
        t.record_anchor_add(
            component="test", anchor_data="y", authority_id="user-1",
        )
        t.record_anchor_add(
            component="test", anchor_data="z", authority_id="guest-1",
        )
        flagged = t.query(authority_valid=False)
        assert len(flagged) == 2  # user-1 and guest-1
        valid = t.query(authority_valid=True)
        assert len(valid) == 1   # architect

    def test_b_prime_never_raises(self):
        """Even with doctrine, no exception is raised for insufficient auth."""
        t = _tracker_with_doctrine()
        # All these should succeed (flag, never block).
        t.record_anchor_add(
            component="test", anchor_data="x", authority_id="guest-1",
        )
        t.record_threshold_modify(
            component="test", param_name="t", old_value=0, new_value=1,
            authority_id="guest-1",
        )
        t.record_domain_config(
            component="test", old_config={}, new_config={},
            authority_id="guest-1",
        )
        t.record_authority_change(
            authority_target="x", old_role=None, new_role="USER",
            authority_id="guest-1",
        )
        assert t.length == 4
        flagged = t.query(authority_valid=False)
        assert len(flagged) == 4

    def test_observer_toggle_domain_permission(self):
        """OBSERVER_TOGGLE maps to MODIFY_DOMAIN."""
        t = _tracker_with_doctrine()
        rec = t.record_observer_toggle(
            observer_name="fgd", enabled=True, authority_id="trainer-1",
        )
        # TRAINER does NOT have MODIFY_DOMAIN
        assert rec.authority_valid is False


# ═══════════════════════════════════════════════════════════
#  10. Hash chain integrity
# ═══════════════════════════════════════════════════════════

class TestHashChainIntegrity:
    def test_chain_of_10_records(self):
        t = _tracker()
        for i in range(10):
            t.record(
                change_type=ChangeType.ANCHOR_ADD,
                component=f"mod_{i}",
                old_value=None,
                new_value=i,
                authority_id="arch",
                timestamp=_fixed_ts(i),
            )
        valid, reason = t.verify_chain()
        assert valid is True

    def test_each_record_hash_is_unique(self):
        t = _tracker()
        hashes = set()
        for i in range(10):
            rec = t.record(
                change_type=ChangeType.ANCHOR_ADD,
                component=f"mod_{i}",
                old_value=None,
                new_value=i,
                authority_id="arch",
                timestamp=_fixed_ts(i),
            )
            hashes.add(rec.hash)
        assert len(hashes) == 10

    def test_prev_hash_links_to_previous(self):
        t = _tracker()
        records = []
        for i in range(5):
            rec = t.record(
                change_type=ChangeType.ANCHOR_ADD,
                component="test",
                old_value=None,
                new_value=i,
                authority_id="arch",
                timestamp=_fixed_ts(i),
            )
            records.append(rec)
        for i in range(1, 5):
            assert records[i].prev_hash == records[i-1].hash

    def test_first_record_prev_hash_is_genesis(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
        )
        assert rec.prev_hash == ""


# ═══════════════════════════════════════════════════════════
#  11. Edge cases
# ═══════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_arabic_justification(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="intent_scorer",
            old_value=None,
            new_value={"word": "خطر"},
            authority_id="architect",
            justification="إضافة مرساة أمان عربية — خطر يعني danger",
        )
        assert "خطر" in rec.justification
        assert rec.hash  # Hash was computed successfully

    def test_arabic_component_name(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="المحاجج",
            old_value=None,
            new_value="x",
            authority_id="architect",
        )
        assert rec.component == "المحاجج"

    def test_none_values(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value=None,
            authority_id="arch",
        )
        assert rec.old_value is None
        assert rec.new_value is None

    def test_complex_nested_values(self):
        t = _tracker()
        complex_val = {
            "anchors": [
                {"word": "danger", "weight": 0.9, "tags": ["safety"]},
                {"word": "خطر", "weight": 0.85, "tags": ["safety", "arabic"]},
            ],
            "config": {"enabled": True, "threshold": 0.5},
        }
        rec = t.record(
            change_type=ChangeType.DOMAIN_CONFIG,
            component="test",
            old_value=None,
            new_value=complex_val,
            authority_id="arch",
        )
        assert rec.new_value == complex_val

    def test_large_constitutional_basis(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            constitutional_basis=(1, 3, 5, 14, 16, 17, 29, 30, 31, 34),
        )
        assert len(rec.constitutional_basis) == 10

    def test_empty_justification(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            justification="",
        )
        assert rec.justification == ""

    def test_long_justification(self):
        t = _tracker()
        long_text = "A" * 10000
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            justification=long_text,
        )
        assert len(rec.justification) == 10000

    def test_numeric_values(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.THRESHOLD_MODIFY,
            component="s_equation",
            old_value=0.50,
            new_value=0.55,
            authority_id="arch",
        )
        assert rec.old_value == 0.50
        assert rec.new_value == 0.55

    def test_boolean_values(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.OBSERVER_TOGGLE,
            component="observer_registry",
            old_value=False,
            new_value=True,
            authority_id="arch",
        )
        assert rec.old_value is False
        assert rec.new_value is True

    def test_query_start_time_only(self):
        t = _tracker()
        t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="a",
            old_value=None,
            new_value="x",
            authority_id="arch",
            timestamp="2025-01-01T00:00:00+00:00",
        )
        t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="b",
            old_value=None,
            new_value="y",
            authority_id="arch",
            timestamp="2025-12-01T00:00:00+00:00",
        )
        results = t.query(start_time="2025-06-01T00:00:00+00:00")
        assert len(results) == 1
        assert results[0].component == "b"

    def test_query_end_time_only(self):
        t = _tracker()
        t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="a",
            old_value=None,
            new_value="x",
            authority_id="arch",
            timestamp="2025-01-01T00:00:00+00:00",
        )
        t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="b",
            old_value=None,
            new_value="y",
            authority_id="arch",
            timestamp="2025-12-01T00:00:00+00:00",
        )
        results = t.query(end_time="2025-06-01T00:00:00+00:00")
        assert len(results) == 1
        assert results[0].component == "a"

    def test_summary_with_invalid_authority(self):
        t = _tracker_with_doctrine()
        t.record_anchor_add(
            component="test", anchor_data="x", authority_id="architect",
        )
        t.record_anchor_add(
            component="test", anchor_data="y", authority_id="guest-1",
        )
        s = t.summary()
        assert s["invalid_authority_count"] == 1


# ═══════════════════════════════════════════════════════════
#  12. Integration: ChangeTracker + AuthorityDoctrine
# ═══════════════════════════════════════════════════════════

class TestAuthorityDoctrineIntegration:
    def test_full_hierarchy_permissions(self):
        """Each role can only do what the doctrine allows."""
        t = _tracker_with_doctrine()

        # OWNER can do everything.
        rec = t.record_threshold_modify(
            component="s_eq", param_name="theta",
            old_value=0.5, new_value=0.6, authority_id="architect",
        )
        assert rec.authority_valid is True

        # TRAINER can add anchors but not modify theta.
        rec = t.record_anchor_add(
            component="intent_scorer", anchor_data="x",
            authority_id="trainer-1",
        )
        assert rec.authority_valid is True

        rec = t.record_threshold_modify(
            component="s_eq", param_name="theta",
            old_value=0.5, new_value=0.6, authority_id="trainer-1",
        )
        assert rec.authority_valid is False

        # USER cannot add anchors or modify theta.
        rec = t.record_anchor_add(
            component="intent_scorer", anchor_data="x",
            authority_id="user-1",
        )
        assert rec.authority_valid is False

    def test_doctrine_integration_summary(self):
        """Summary correctly counts flagged changes from doctrine."""
        t = _tracker_with_doctrine()
        t.record_anchor_add(
            component="test", anchor_data="x", authority_id="architect",
        )
        t.record_anchor_add(
            component="test", anchor_data="y", authority_id="trainer-1",
        )
        t.record_anchor_add(
            component="test", anchor_data="z", authority_id="user-1",
        )
        t.record_anchor_add(
            component="test", anchor_data="w", authority_id="guest-1",
        )
        s = t.summary()
        assert s["total_records"] == 4
        assert s["invalid_authority_count"] == 2  # user-1, guest-1


# ═══════════════════════════════════════════════════════════
#  13. Determinism and hash stability
# ═══════════════════════════════════════════════════════════

class TestDeterminism:
    def test_same_inputs_same_hash(self):
        """Two trackers with identical inputs produce identical hashes."""
        ts = _fixed_ts()
        for _ in range(2):
            t = _tracker()
            rec = t.record(
                change_type=ChangeType.ANCHOR_ADD,
                component="test",
                old_value=None,
                new_value="x",
                authority_id="arch",
                timestamp=ts,
            )
        # Create fresh tracker and compare.
        t2 = _tracker()
        rec2 = t2.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value=None,
            new_value="x",
            authority_id="arch",
            timestamp=ts,
        )
        assert rec.hash == rec2.hash

    def test_different_order_different_chain(self):
        """Swapping record order produces different chain hashes."""
        t1 = _tracker()
        t1.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="a",
            old_value=None,
            new_value="x",
            authority_id="arch",
            timestamp=_fixed_ts(1),
        )
        r1_second = t1.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="b",
            old_value=None,
            new_value="y",
            authority_id="arch",
            timestamp=_fixed_ts(2),
        )

        t2 = _tracker()
        t2.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="b",
            old_value=None,
            new_value="y",
            authority_id="arch",
            timestamp=_fixed_ts(2),
        )
        r2_second = t2.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="a",
            old_value=None,
            new_value="x",
            authority_id="arch",
            timestamp=_fixed_ts(1),
        )
        # The second record in each has a different prev_hash → different hash.
        assert r1_second.hash != r2_second.hash


# ═══════════════════════════════════════════════════════════
#  14. ChangeRecord serialisation roundtrip
# ═══════════════════════════════════════════════════════════

class TestSerialisationRoundtrip:
    def test_to_dict_all_change_types(self):
        t = _tracker()
        for ct in ChangeType:
            rec = t.record(
                change_type=ct,
                component="test",
                old_value="old",
                new_value="new",
                authority_id="arch",
                timestamp=_fixed_ts(ct.value.__hash__() % 60),
            )
            d = rec.to_dict()
            assert d["change_type"] == ct.value

    def test_to_dict_json_serialisable(self):
        t = _tracker()
        rec = t.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="test",
            old_value={"nested": [1, 2, 3]},
            new_value={"nested": [4, 5, 6]},
            authority_id="arch",
            justification="تعديل عربي",
            constitutional_basis=(5, 29),
        )
        # Must be JSON-serialisable.
        serialised = json.dumps(rec.to_dict(), ensure_ascii=False)
        assert "تعديل عربي" in serialised
        parsed = json.loads(serialised)
        assert parsed["component"] == "test"


# ═══════════════════════════════════════════════════════════
#  15. Query composition (multiple filters at once)
# ═══════════════════════════════════════════════════════════

class TestQueryComposition:
    def _populated_tracker(self) -> ChangeTracker:
        t = _tracker_with_doctrine()
        # 1: architect adds anchor
        t.record_anchor_add(
            component="intent_scorer", anchor_data="danger",
            authority_id="architect",
            timestamp="2025-01-10T10:00:00+00:00",
        )
        # 2: trainer adds anchor
        t.record_anchor_add(
            component="intent_scorer", anchor_data="harm",
            authority_id="trainer-1",
            timestamp="2025-02-15T10:00:00+00:00",
        )
        # 3: architect modifies threshold
        t.record_threshold_modify(
            component="s_equation", param_name="theta",
            old_value=0.5, new_value=0.55, authority_id="architect",
            timestamp="2025-03-20T10:00:00+00:00",
        )
        # 4: user tries to add anchor (flagged)
        t.record_anchor_add(
            component="emotion_scorer", anchor_data="sad",
            authority_id="user-1",
            timestamp="2025-04-25T10:00:00+00:00",
        )
        # 5: architect toggles observer
        t.record_observer_toggle(
            observer_name="fgd", enabled=True,
            authority_id="architect",
            timestamp="2025-05-30T10:00:00+00:00",
        )
        return t

    def test_by_component_and_type(self):
        t = self._populated_tracker()
        results = t.query(
            component="intent_scorer",
            change_type=ChangeType.ANCHOR_ADD,
        )
        assert len(results) == 2

    def test_by_authority_and_time(self):
        t = self._populated_tracker()
        results = t.query(
            authority_id="architect",
            start_time="2025-03-01T00:00:00+00:00",
        )
        # Records 3 and 5
        assert len(results) == 2

    def test_by_type_and_validity(self):
        t = self._populated_tracker()
        results = t.query(
            change_type=ChangeType.ANCHOR_ADD,
            authority_valid=False,
        )
        assert len(results) == 1
        assert results[0].authority_id == "user-1"

    def test_all_filters_combined(self):
        t = self._populated_tracker()
        results = t.query(
            component="intent_scorer",
            change_type=ChangeType.ANCHOR_ADD,
            authority_valid=True,
            start_time="2025-02-01T00:00:00+00:00",
            end_time="2025-12-31T00:00:00+00:00",
        )
        assert len(results) == 1
        assert results[0].authority_id == "trainer-1"


# ═══════════════════════════════════════════════════════════
#  16. Large log stress
# ═══════════════════════════════════════════════════════════

class TestLargeLog:
    def test_100_records_chain_valid(self):
        t = _tracker()
        for i in range(100):
            t.record(
                change_type=list(ChangeType)[i % 6],
                component=f"mod_{i % 10}",
                old_value=i - 1 if i > 0 else None,
                new_value=i,
                authority_id=f"auth_{i % 3}",
                timestamp=_fixed_ts(i % 60),
                constitutional_basis=(i % 20 + 1,),
            )
        assert t.length == 100
        valid, reason = t.verify_chain()
        assert valid is True

    def test_query_performance_on_large_log(self):
        """Query 100 records — should be instant."""
        t = _tracker()
        for i in range(100):
            t.record(
                change_type=ChangeType.ANCHOR_ADD,
                component=f"mod_{i % 5}",
                old_value=None,
                new_value=i,
                authority_id="arch",
                timestamp=_fixed_ts(i % 60),
            )
        results = t.query(component="mod_3")
        assert len(results) == 20  # 100 / 5


# ═══════════════════════════════════════════════════════════
#  17. Mixed change types in one tracker
# ═══════════════════════════════════════════════════════════

class TestMixedChangeTypes:
    def test_all_six_types_in_one_tracker(self):
        t = _tracker()
        t.record_anchor_add(
            component="a", anchor_data="x", authority_id="arch",
        )
        t.record_anchor_remove(
            component="b", anchor_data="y", authority_id="arch",
        )
        t.record_threshold_modify(
            component="c", param_name="t", old_value=0, new_value=1,
            authority_id="arch",
        )
        t.record_domain_config(
            component="d", old_config={}, new_config={"k": "v"},
            authority_id="arch",
        )
        t.record_observer_toggle(
            observer_name="obs", enabled=True, authority_id="arch",
        )
        t.record_authority_change(
            authority_target="alice", old_role=None, new_role="USER",
            authority_id="arch",
        )
        assert t.length == 6
        valid, reason = t.verify_chain()
        assert valid is True

        s = t.summary()
        assert len(s["changes_by_type"]) == 6


# ═══════════════════════════════════════════════════════════
#  18. ChangeLog.GENESIS_HASH
# ═══════════════════════════════════════════════════════════

class TestGenesisHash:
    def test_genesis_hash_is_empty_string(self):
        assert ChangeLog.GENESIS_HASH == ""

    def test_empty_log_last_hash_is_genesis(self):
        log = ChangeLog()
        assert log.last_hash == ChangeLog.GENESIS_HASH
