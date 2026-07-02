#!/usr/bin/env python3
"""
AATIF Change Traceability Module — سجل التغيير  (Field Note #034 + #014)
========================================================================

"كل تغيير يُسجَّل. كل سجل يُبرَّر. كل مبرر يعود إلى الدستور."
"Every change is recorded. Every record is justified. Every justification
traces back to the constitution."

A governed system that cannot explain WHAT changed, WHEN, WHY, and by WHOM
is a system that has already drifted — it just hasn't noticed yet.

This module is المُسجِّل (the Recorder): it watches every system-level
change — anchor additions, threshold modifications, domain config updates,
observer toggles, authority role changes — and records them in a tamper-
evident, append-only log with a SHA-256 hash chain.

HOW IT WORKS
────────────
Every change produces a ChangeRecord:
  • timestamp          — ISO 8601 UTC
  • change_type        — enum (ANCHOR_ADD, ANCHOR_REMOVE, THRESHOLD_MODIFY,
                          DOMAIN_CONFIG, OBSERVER_TOGGLE, AUTHORITY_CHANGE)
  • component          — which engine module was changed
  • old_value          — the previous value (or None for additions)
  • new_value          — the new value (or None for removals)
  • authority_id       — who made the change (from Authority Doctrine)
  • justification      — why (free text)
  • constitutional_basis — which articles justify this (from Reasoning Trace)
  • hash               — SHA-256 of the record contents
  • prev_hash          — SHA-256 of the previous record (hash chain)

The ChangeLog is append-only with a hash chain: each record includes the
hash of the previous record, making the log tamper-evident.  If any record
is modified or removed, the chain breaks.

AUTHORITY VALIDATION (B-PRIME)
──────────────────────────────
When an AuthorityDoctrine is attached, the tracker checks whether the
authority_id has sufficient permission for the change type.  Insufficient
authority is FLAGGED in the record (authority_valid=False) but NEVER
BLOCKED.  B-prime: CAN_BLOCK_RUNTIME = False — the tracker observes and
records, the Governor alone decides.

    "المراقبون يرون ويسجلون — المحافظ وحده يقرر"

QUERY INTERFACE
───────────────
The log supports querying by:
  • time range (start/end ISO 8601)
  • component name
  • authority_id
  • change_type
  • authority_valid flag
All filters compose (AND logic).

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Ensure the engine directory is importable (same pattern as the other modules)
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


# ═══════════════════════════════════════════════════════════
#  B-prime constant — the tracker NEVER blocks
# ═══════════════════════════════════════════════════════════

CAN_BLOCK_RUNTIME = False


# ═══════════════════════════════════════════════════════════
#  ChangeType — what kind of change happened
# ═══════════════════════════════════════════════════════════

class ChangeType(Enum):
    """
    Discrete change types the tracker recognises.

    Each type maps to a specific kind of system-level mutation.
    """
    ANCHOR_ADD = "anchor_add"               # New H/I/E anchor added
    ANCHOR_REMOVE = "anchor_remove"         # Existing anchor removed
    THRESHOLD_MODIFY = "threshold_modify"   # θ, α, or weight changed
    DOMAIN_CONFIG = "domain_config"         # Domain configuration changed
    OBSERVER_TOGGLE = "observer_toggle"     # Observer enabled/disabled/added
    AUTHORITY_CHANGE = "authority_change"    # Authority role added/removed/changed


# ═══════════════════════════════════════════════════════════
#  Permission mapping — which AuthorityPermission each
#  ChangeType requires (used for validation, not blocking)
# ═══════════════════════════════════════════════════════════

# Lazy import: we import AuthorityPermission only when an AuthorityDoctrine
# is actually attached, to keep the module self-contained.
_CHANGE_TYPE_PERMISSIONS: Optional[Dict[ChangeType, str]] = None


def _get_permission_map() -> Dict[ChangeType, str]:
    """Build the ChangeType → AuthorityPermission.value map (lazy)."""
    global _CHANGE_TYPE_PERMISSIONS
    if _CHANGE_TYPE_PERMISSIONS is None:
        _CHANGE_TYPE_PERMISSIONS = {
            ChangeType.ANCHOR_ADD: "add_anchors",
            ChangeType.ANCHOR_REMOVE: "add_anchors",
            ChangeType.THRESHOLD_MODIFY: "modify_theta",
            ChangeType.DOMAIN_CONFIG: "modify_domain",
            ChangeType.OBSERVER_TOGGLE: "modify_domain",
            ChangeType.AUTHORITY_CHANGE: "modify_theta",  # OWNER-only
        }
    return _CHANGE_TYPE_PERMISSIONS


# ═══════════════════════════════════════════════════════════
#  ChangeRecord — one immutable change entry
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ChangeRecord:
    """
    One change in the system, immutable once created.

    The hash covers all content fields; prev_hash links this record to
    the previous one, forming a tamper-evident chain.
    """
    timestamp: str                          # ISO 8601 UTC
    change_type: ChangeType                 # what kind of change
    component: str                          # which engine module
    old_value: Optional[Any]                # previous value (None for adds)
    new_value: Optional[Any]                # new value (None for removes)
    authority_id: str                       # who made the change
    justification: str                      # why (free text)
    constitutional_basis: Tuple[int, ...]   # FN article numbers
    authority_valid: bool                   # did authority_id have permission?
    authority_flag: str                     # explanation if invalid, else ""
    prev_hash: str                          # hash of previous record ("" for first)
    hash: str                               # SHA-256 of this record's content

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict for inspection / export."""
        return {
            "timestamp": self.timestamp,
            "change_type": self.change_type.value,
            "component": self.component,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "authority_id": self.authority_id,
            "justification": self.justification,
            "constitutional_basis": list(self.constitutional_basis),
            "authority_valid": self.authority_valid,
            "authority_flag": self.authority_flag,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


def _compute_hash(
    timestamp: str,
    change_type: ChangeType,
    component: str,
    old_value: Any,
    new_value: Any,
    authority_id: str,
    justification: str,
    constitutional_basis: Tuple[int, ...],
    authority_valid: bool,
    authority_flag: str,
    prev_hash: str,
) -> str:
    """
    SHA-256 of the record's content fields.

    Deterministic: values are JSON-serialised with sort_keys=True before
    hashing, so the same inputs always produce the same hash.
    """
    payload = json.dumps(
        {
            "timestamp": timestamp,
            "change_type": change_type.value,
            "component": component,
            "old_value": _serialise_value(old_value),
            "new_value": _serialise_value(new_value),
            "authority_id": authority_id,
            "justification": justification,
            "constitutional_basis": list(constitutional_basis),
            "authority_valid": authority_valid,
            "authority_flag": authority_flag,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _serialise_value(v: Any) -> Any:
    """
    Coerce a value to a JSON-safe type for hashing.

    Handles: None, str, int, float, bool, list, dict, tuple, set.
    Everything else is str(v).
    """
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, (list, tuple)):
        return [_serialise_value(x) for x in v]
    if isinstance(v, set):
        return sorted(_serialise_value(x) for x in v)
    if isinstance(v, dict):
        return {str(k): _serialise_value(val) for k, val in sorted(v.items())}
    return str(v)


# ═══════════════════════════════════════════════════════════
#  ChangeLog — append-only, hash-chained log
# ═══════════════════════════════════════════════════════════

class ChangeLog:
    """
    Append-only log of ChangeRecords with a SHA-256 hash chain.

    Tamper-evident: each record includes the hash of the previous record.
    If any record is modified, inserted, or removed, verify_chain() detects it.
    """

    # The genesis hash — the prev_hash of the very first record.
    GENESIS_HASH = ""

    def __init__(self) -> None:
        self._records: List[ChangeRecord] = []

    # ─── Append ──────────────────────────────────────────

    def append(self, record: ChangeRecord) -> None:
        """
        Append a record to the log.

        The record's prev_hash MUST match the hash of the current last
        record (or GENESIS_HASH if the log is empty).  This enforces the
        append-only hash chain.

        Raises ValueError if the prev_hash doesn't match.
        """
        expected_prev = (
            self._records[-1].hash if self._records else self.GENESIS_HASH
        )
        if record.prev_hash != expected_prev:
            raise ValueError(
                f"Hash chain broken: record.prev_hash='{record.prev_hash}' "
                f"but expected '{expected_prev}'.  Records can only be "
                f"appended to the end of the chain."
            )
        self._records.append(record)

    # ─── Query ───────────────────────────────────────────

    @property
    def length(self) -> int:
        return len(self._records)

    def all_records(self) -> List[ChangeRecord]:
        """Return a copy of all records (preserves immutability)."""
        return list(self._records)

    def get(self, index: int) -> ChangeRecord:
        """Return record at `index`.  Raises IndexError if out of range."""
        return self._records[index]

    @property
    def last_hash(self) -> str:
        """Hash of the most recent record, or GENESIS_HASH if empty."""
        return self._records[-1].hash if self._records else self.GENESIS_HASH

    def query(
        self,
        *,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        component: Optional[str] = None,
        authority_id: Optional[str] = None,
        change_type: Optional[ChangeType] = None,
        authority_valid: Optional[bool] = None,
    ) -> List[ChangeRecord]:
        """
        Query records with AND-composed filters.

        All parameters are optional; omitting a parameter means "no filter
        on that field".

        Args:
            start_time:      ISO 8601 — only records at or after this time.
            end_time:         ISO 8601 — only records at or before this time.
            component:        exact match on the component field.
            authority_id:     exact match on the authority_id field.
            change_type:      exact match on the change_type field.
            authority_valid:  filter by authority validation result.

        Returns:
            List of matching ChangeRecords, in chronological order.
        """
        results = self._records

        if start_time is not None:
            results = [r for r in results if r.timestamp >= start_time]

        if end_time is not None:
            results = [r for r in results if r.timestamp <= end_time]

        if component is not None:
            results = [r for r in results if r.component == component]

        if authority_id is not None:
            results = [r for r in results if r.authority_id == authority_id]

        if change_type is not None:
            results = [r for r in results if r.change_type == change_type]

        if authority_valid is not None:
            results = [
                r for r in results if r.authority_valid == authority_valid
            ]

        return results

    # ─── Verification ────────────────────────────────────

    def verify_chain(self) -> Tuple[bool, str]:
        """
        Verify the hash chain is intact.

        Returns (True, "") if valid, or (False, reason) if tampered.

        Checks:
          1. Each record's hash matches a recomputed hash of its contents.
          2. Each record's prev_hash matches the previous record's hash.
          3. The first record's prev_hash is GENESIS_HASH.
        """
        if not self._records:
            return (True, "")

        # First record must have GENESIS_HASH as prev_hash.
        first = self._records[0]
        if first.prev_hash != self.GENESIS_HASH:
            return (
                False,
                f"Record 0: prev_hash='{first.prev_hash}' but expected "
                f"GENESIS_HASH='{self.GENESIS_HASH}'.",
            )

        for i, rec in enumerate(self._records):
            # Recompute hash.
            expected_hash = _compute_hash(
                timestamp=rec.timestamp,
                change_type=rec.change_type,
                component=rec.component,
                old_value=rec.old_value,
                new_value=rec.new_value,
                authority_id=rec.authority_id,
                justification=rec.justification,
                constitutional_basis=rec.constitutional_basis,
                authority_valid=rec.authority_valid,
                authority_flag=rec.authority_flag,
                prev_hash=rec.prev_hash,
            )
            if rec.hash != expected_hash:
                return (
                    False,
                    f"Record {i}: hash mismatch — stored='{rec.hash}', "
                    f"computed='{expected_hash}'.  Record may be tampered.",
                )

            # Chain linkage (records after the first).
            if i > 0:
                prev_rec = self._records[i - 1]
                if rec.prev_hash != prev_rec.hash:
                    return (
                        False,
                        f"Record {i}: prev_hash='{rec.prev_hash}' does not "
                        f"match record {i-1} hash='{prev_rec.hash}'.  "
                        f"Chain is broken.",
                    )

        return (True, "")

    # ─── Summary ─────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """Quick stats about the log."""
        type_counts: Dict[str, int] = {}
        component_counts: Dict[str, int] = {}
        authority_counts: Dict[str, int] = {}
        invalid_count = 0

        for rec in self._records:
            ct = rec.change_type.value
            type_counts[ct] = type_counts.get(ct, 0) + 1
            component_counts[rec.component] = (
                component_counts.get(rec.component, 0) + 1
            )
            authority_counts[rec.authority_id] = (
                authority_counts.get(rec.authority_id, 0) + 1
            )
            if not rec.authority_valid:
                invalid_count += 1

        valid, reason = self.verify_chain()
        return {
            "total_records": len(self._records),
            "chain_valid": valid,
            "chain_error": reason,
            "changes_by_type": type_counts,
            "changes_by_component": component_counts,
            "changes_by_authority": authority_counts,
            "invalid_authority_count": invalid_count,
        }


# ═══════════════════════════════════════════════════════════
#  ChangeTracker — the high-level API
# ═══════════════════════════════════════════════════════════

class ChangeTracker:
    """
    Records system-level changes with authority validation and hash chaining.

    Pure logic — no embeddings, no LLM, no I/O.  Deterministic.

    Usage:
        from aatif_authority_doctrine import AuthorityDoctrine
        doctrine = AuthorityDoctrine(owner_id="architect")

        tracker = ChangeTracker(authority_doctrine=doctrine)

        tracker.record(
            change_type=ChangeType.ANCHOR_ADD,
            component="intent_scorer",
            old_value=None,
            new_value={"word": "danger", "weight": 0.9},
            authority_id="architect",
            justification="Adding safety anchor for harm detection",
            constitutional_basis=(29, 5),
        )

        # Query the log
        safety_changes = tracker.query(component="intent_scorer")
        flagged = tracker.query(authority_valid=False)
    """

    def __init__(
        self,
        authority_doctrine=None,
    ) -> None:
        """
        Args:
            authority_doctrine: an AuthorityDoctrine instance for permission
                validation.  If None, all changes are recorded as valid
                (no authority checks).
        """
        self._log = ChangeLog()
        self._doctrine = authority_doctrine

    # ─── Record ──────────────────────────────────────────

    def record(
        self,
        change_type: ChangeType,
        component: str,
        old_value: Any,
        new_value: Any,
        authority_id: str,
        justification: str = "",
        constitutional_basis: Tuple[int, ...] = (),
        timestamp: Optional[str] = None,
    ) -> ChangeRecord:
        """
        Record a system-level change.

        Args:
            change_type:          what kind of change.
            component:            which engine module.
            old_value:            previous value (None for additions).
            new_value:            new value (None for removals).
            authority_id:         who made the change.
            justification:        why (free text).
            constitutional_basis: FN article numbers justifying the change.
            timestamp:            ISO 8601 UTC (auto-generated if None).

        Returns:
            The created ChangeRecord (also appended to the log).
        """
        if not isinstance(change_type, ChangeType):
            raise TypeError(
                f"change_type must be a ChangeType, got {type(change_type)}"
            )
        if not component or not isinstance(component, str):
            raise ValueError("component must be a non-empty string")
        if not authority_id or not isinstance(authority_id, str):
            raise ValueError("authority_id must be a non-empty string")

        # Normalise constitutional_basis to a tuple of ints.
        if isinstance(constitutional_basis, (list, set)):
            constitutional_basis = tuple(sorted(constitutional_basis))
        elif not isinstance(constitutional_basis, tuple):
            constitutional_basis = (constitutional_basis,)

        # Timestamp.
        ts = timestamp or datetime.now(tz=timezone.utc).isoformat()

        # Authority validation — B-prime: flag, never block.
        authority_valid, authority_flag = self._validate_authority(
            authority_id, change_type
        )

        # Previous hash for the chain.
        prev_hash = self._log.last_hash

        # Compute hash.
        record_hash = _compute_hash(
            timestamp=ts,
            change_type=change_type,
            component=component,
            old_value=old_value,
            new_value=new_value,
            authority_id=authority_id,
            justification=justification,
            constitutional_basis=constitutional_basis,
            authority_valid=authority_valid,
            authority_flag=authority_flag,
            prev_hash=prev_hash,
        )

        record = ChangeRecord(
            timestamp=ts,
            change_type=change_type,
            component=component,
            old_value=old_value,
            new_value=new_value,
            authority_id=authority_id,
            justification=justification,
            constitutional_basis=constitutional_basis,
            authority_valid=authority_valid,
            authority_flag=authority_flag,
            prev_hash=prev_hash,
            hash=record_hash,
        )

        self._log.append(record)
        return record

    # ─── Delegation to ChangeLog ─────────────────────────

    def query(self, **kwargs) -> List[ChangeRecord]:
        """Query the log.  See ChangeLog.query for parameters."""
        return self._log.query(**kwargs)

    def all_records(self) -> List[ChangeRecord]:
        """Return all records in chronological order."""
        return self._log.all_records()

    def verify_chain(self) -> Tuple[bool, str]:
        """Verify the hash chain.  See ChangeLog.verify_chain."""
        return self._log.verify_chain()

    def summary(self) -> Dict[str, Any]:
        """Quick stats.  See ChangeLog.summary."""
        return self._log.summary()

    @property
    def log(self) -> ChangeLog:
        """Direct access to the underlying ChangeLog."""
        return self._log

    @property
    def length(self) -> int:
        """Number of records in the log."""
        return self._log.length

    # ─── Authority validation ────────────────────────────

    def _validate_authority(
        self,
        authority_id: str,
        change_type: ChangeType,
    ) -> Tuple[bool, str]:
        """
        Check if authority_id has permission for this change_type.

        B-prime: returns (valid, flag_message) — NEVER raises / blocks.

        If no AuthorityDoctrine is attached, all changes are valid.
        """
        if self._doctrine is None:
            return (True, "")

        # Import here to avoid circular dependency.
        try:
            from aatif_authority_doctrine import AuthorityPermission
        except ImportError:
            # If the authority module is not available, skip validation.
            return (True, "")

        # Map the change type to the required permission.
        perm_map = _get_permission_map()
        required_perm_value = perm_map.get(change_type)
        if required_perm_value is None:
            return (True, "")

        # Find the matching AuthorityPermission enum member.
        required_perm = None
        for p in AuthorityPermission:
            if p.value == required_perm_value:
                required_perm = p
                break

        if required_perm is None:
            return (True, "")

        # Check permission via the doctrine.
        has_perm = self._doctrine.check_permission(authority_id, required_perm)
        if has_perm:
            return (True, "")

        # Insufficient authority — flag but do NOT block.
        ctx = self._doctrine.get_context_or_none(authority_id)
        if ctx is None:
            return (
                False,
                f"Authority '{authority_id}' is not registered in the "
                f"doctrine.  Change recorded but flagged as unvalidated.  "
                f"عقيدة السلطة: الجهة غير معروفة.",
            )

        return (
            False,
            f"Authority '{authority_id}' ({ctx.role.name}) lacks "
            f"'{required_perm.value}' permission for {change_type.value}.  "
            f"Change recorded but flagged.  "
            f"عقيدة السلطة: صلاحية غير كافية.",
        )

    # ─── Convenience recorders ───────────────────────────

    def record_anchor_add(
        self,
        component: str,
        anchor_data: Any,
        authority_id: str,
        justification: str = "",
        constitutional_basis: Tuple[int, ...] = (),
        timestamp: Optional[str] = None,
    ) -> ChangeRecord:
        """Shortcut: record an anchor addition."""
        return self.record(
            change_type=ChangeType.ANCHOR_ADD,
            component=component,
            old_value=None,
            new_value=anchor_data,
            authority_id=authority_id,
            justification=justification,
            constitutional_basis=constitutional_basis,
            timestamp=timestamp,
        )

    def record_anchor_remove(
        self,
        component: str,
        anchor_data: Any,
        authority_id: str,
        justification: str = "",
        constitutional_basis: Tuple[int, ...] = (),
        timestamp: Optional[str] = None,
    ) -> ChangeRecord:
        """Shortcut: record an anchor removal."""
        return self.record(
            change_type=ChangeType.ANCHOR_REMOVE,
            component=component,
            old_value=anchor_data,
            new_value=None,
            authority_id=authority_id,
            justification=justification,
            constitutional_basis=constitutional_basis,
            timestamp=timestamp,
        )

    def record_threshold_modify(
        self,
        component: str,
        param_name: str,
        old_value: Any,
        new_value: Any,
        authority_id: str,
        justification: str = "",
        constitutional_basis: Tuple[int, ...] = (),
        timestamp: Optional[str] = None,
    ) -> ChangeRecord:
        """Shortcut: record a threshold/parameter modification."""
        return self.record(
            change_type=ChangeType.THRESHOLD_MODIFY,
            component=component,
            old_value={"param": param_name, "value": old_value},
            new_value={"param": param_name, "value": new_value},
            authority_id=authority_id,
            justification=justification,
            constitutional_basis=constitutional_basis,
            timestamp=timestamp,
        )

    def record_domain_config(
        self,
        component: str,
        old_config: Any,
        new_config: Any,
        authority_id: str,
        justification: str = "",
        constitutional_basis: Tuple[int, ...] = (),
        timestamp: Optional[str] = None,
    ) -> ChangeRecord:
        """Shortcut: record a domain configuration change."""
        return self.record(
            change_type=ChangeType.DOMAIN_CONFIG,
            component=component,
            old_value=old_config,
            new_value=new_config,
            authority_id=authority_id,
            justification=justification,
            constitutional_basis=constitutional_basis,
            timestamp=timestamp,
        )

    def record_observer_toggle(
        self,
        observer_name: str,
        enabled: bool,
        authority_id: str,
        justification: str = "",
        constitutional_basis: Tuple[int, ...] = (),
        timestamp: Optional[str] = None,
    ) -> ChangeRecord:
        """Shortcut: record an observer enable/disable."""
        return self.record(
            change_type=ChangeType.OBSERVER_TOGGLE,
            component="observer_registry",
            old_value={"observer": observer_name, "enabled": not enabled},
            new_value={"observer": observer_name, "enabled": enabled},
            authority_id=authority_id,
            justification=justification,
            constitutional_basis=constitutional_basis,
            timestamp=timestamp,
        )

    def record_authority_change(
        self,
        authority_target: str,
        old_role: Optional[str],
        new_role: Optional[str],
        authority_id: str,
        justification: str = "",
        constitutional_basis: Tuple[int, ...] = (),
        timestamp: Optional[str] = None,
    ) -> ChangeRecord:
        """Shortcut: record an authority role change."""
        return self.record(
            change_type=ChangeType.AUTHORITY_CHANGE,
            component="authority_doctrine",
            old_value={"authority": authority_target, "role": old_role},
            new_value={"authority": authority_target, "role": new_role},
            authority_id=authority_id,
            justification=justification,
            constitutional_basis=constitutional_basis,
            timestamp=timestamp,
        )


# ═══════════════════════════════════════════════════════════
#  Demo / smoke test
# ═══════════════════════════════════════════════════════════

def _demo() -> None:  # pragma: no cover - manual smoke test
    print("=" * 70)
    print("  AATIF Change Traceability — سجل التغيير (FN#034 + FN#014)")
    print("  «كل تغيير يُسجَّل. كل سجل يُبرَّر.»")
    print("=" * 70)

    tracker = ChangeTracker()

    # Record some changes.
    r1 = tracker.record_anchor_add(
        component="intent_scorer",
        anchor_data={"word": "خطر", "weight": 0.9},
        authority_id="architect",
        justification="Adding Arabic harm anchor",
        constitutional_basis=(29, 5),
    )
    print(f"  ✅ Recorded: {r1.change_type.value} → {r1.component}")
    print(f"     hash: {r1.hash[:16]}...")

    r2 = tracker.record_threshold_modify(
        component="s_equation",
        param_name="theta",
        old_value=0.50,
        new_value=0.55,
        authority_id="architect",
        justification="Tightening safety threshold after FGD review",
        constitutional_basis=(29, 52),
    )
    print(f"  ✅ Recorded: {r2.change_type.value} → {r2.component}")
    print(f"     hash: {r2.hash[:16]}...")
    print(f"     prev_hash: {r2.prev_hash[:16]}...")

    # Verify chain.
    valid, reason = tracker.verify_chain()
    flag = "✅" if valid else "⛔"
    print(f"\n  {flag} Hash chain: valid={valid}")

    # Summary.
    s = tracker.summary()
    print(f"\n  📊 Summary: {s['total_records']} records")
    print(f"     By type: {s['changes_by_type']}")
    print(f"     Invalid authority: {s['invalid_authority_count']}")

    print("\n✅ Change tracker smoke test complete.")


if __name__ == "__main__":
    _demo()
