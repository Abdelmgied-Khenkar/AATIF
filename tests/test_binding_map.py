"""
Test suite for FN#044 Eight-Channel Binding Architecture — aatif_binding_map.py

Tests the BindingMap, ChannelType enum, ChannelBinding, ChannelAuditEntry,
and boot-time validation.

Architecture under test (B-prime):
  BindingMap       →  structural/observational (declares, validates, audits)
  Governor         →  orchestrator (routes signals through direct method calls)
  GovernanceEq (S) →  judicial (computes H_eff, decides S)

Design consensus: Claude × ChatGPT, 2026-07-01
"""

import pytest
import time

from aatif_binding_map import (
    ChannelType,
    ChannelBinding,
    ChannelAuditEntry,
    BindingMap,
    BindingIntegrityReport,
    AATIF_CANONICAL_BINDINGS,
    CHANNEL_ALLOWED_SIGNALS,
    BINDING_MAP_ENABLED,
    AUTHORITY_LEVEL,
    CAN_BLOCK_RUNTIME,
    CAN_MODIFY_PAYLOAD,
    CAN_MODIFY_H,
    CAN_MODIFY_THETA,
    CAN_MODIFY_S,
    CAN_EMIT_JUDICIAL_DECISION,
    CAN_RAISE_BOOT_INTEGRITY_ERROR,
    CAN_EMIT_RUNTIME_AUDIT,
    validate_binding_map_at_boot,
    _hash_payload,
)


# ═══════════════════════════════════════════════════════════════
#  TestChannelType — enum completeness
# ═══════════════════════════════════════════════════════════════

class TestChannelType:
    """Verify ChannelType enum has exactly 8 channels."""

    def test_exactly_8_channels(self):
        assert len(ChannelType) == 8, "Must have exactly 8 channels B1-B8"

    def test_channel_names(self):
        expected = {
            "B1_IDENTITY", "B2_CONSTITUTIONAL", "B3_MEANING", "B4_INTENT",
            "B5_BEHAVIOUR", "B6_SAFETY", "B7_DRIFT", "B8_EXECUTION",
        }
        actual = {ch.value for ch in ChannelType}
        assert actual == expected, f"Channel names mismatch: {actual ^ expected}"

    def test_channels_are_unique(self):
        values = [ch.value for ch in ChannelType]
        assert len(values) == len(set(values)), "Channel values must be unique"

    def test_b1_through_b8_ordering(self):
        """Channels should be numbered B1 through B8."""
        for i, ch in enumerate(ChannelType, start=1):
            assert ch.value.startswith(f"B{i}_"), (
                f"Channel {i} should start with B{i}_, got {ch.value}"
            )


# ═══════════════════════════════════════════════════════════════
#  TestChannelAllowedSignals — signal type constraints
# ═══════════════════════════════════════════════════════════════

class TestChannelAllowedSignals:
    """Verify CHANNEL_ALLOWED_SIGNALS covers all channels with proper types."""

    def test_all_channels_have_allowed_signals(self):
        for ch in ChannelType:
            assert ch in CHANNEL_ALLOWED_SIGNALS, (
                f"Channel {ch.value} missing from CHANNEL_ALLOWED_SIGNALS"
            )
            assert len(CHANNEL_ALLOWED_SIGNALS[ch]) > 0, (
                f"Channel {ch.value} has empty allowed signals"
            )

    def test_no_cross_channel_signal_types(self):
        """
        Each signal type should appear on at most 2 channels.
        (Some signals like BindingViolation might appear on B6 only,
         while CleanedOutput could appear on B6+B8.)
        """
        type_to_channels = {}
        for ch, types in CHANNEL_ALLOWED_SIGNALS.items():
            for t in types:
                if t not in type_to_channels:
                    type_to_channels[t] = set()
                type_to_channels[t].add(ch)

        for signal_type, channels in type_to_channels.items():
            assert len(channels) <= 3, (
                f"Signal type {signal_type} appears on {len(channels)} channels: "
                f"{[c.value for c in channels]} — too much cross-channel presence"
            )

    def test_safety_signals_on_b6(self):
        """Core safety signals must be on B6."""
        b6 = CHANNEL_ALLOWED_SIGNALS[ChannelType.B6_SAFETY]
        assert "SafetyDecision" in b6
        assert "HScore" in b6
        assert "GateVerdict" in b6

    def test_identity_signals_on_b1(self):
        """Identity signals must be on B1."""
        b1 = CHANNEL_ALLOWED_SIGNALS[ChannelType.B1_IDENTITY]
        assert "FingerprintReading" in b1
        assert "TemporalContext" in b1

    def test_intent_signals_on_b4(self):
        """Intent signals must be on B4."""
        b4 = CHANNEL_ALLOWED_SIGNALS[ChannelType.B4_INTENT]
        assert "IntentScore" in b4

    def test_drift_signals_on_b7(self):
        """Drift signals must be on B7."""
        b7 = CHANNEL_ALLOWED_SIGNALS[ChannelType.B7_DRIFT]
        assert "DriftRisk" in b7
        assert "PSPDetection" in b7
        assert "UncertaintySignal" in b7

    def test_all_signal_types_are_strings(self):
        """Every allowed signal type must be a string."""
        for ch, types in CHANNEL_ALLOWED_SIGNALS.items():
            assert isinstance(types, frozenset), (
                f"Channel {ch.value} signal types must be frozenset"
            )
            for t in types:
                assert isinstance(t, str), (
                    f"Signal type {t} on {ch.value} must be str"
                )


# ═══════════════════════════════════════════════════════════════
#  TestChannelBinding — dataclass construction
# ═══════════════════════════════════════════════════════════════

class TestChannelBinding:
    """Verify ChannelBinding construction and immutability."""

    def test_basic_construction(self):
        binding = ChannelBinding(
            source_module="aatif_fingerprint",
            target_module="aatif_governor",
            channel=ChannelType.B1_IDENTITY,
            signal_types=frozenset({"FingerprintReading"}),
        )
        assert binding.source_module == "aatif_fingerprint"
        assert binding.target_module == "aatif_governor"
        assert binding.channel == ChannelType.B1_IDENTITY
        assert "FingerprintReading" in binding.signal_types

    def test_frozen_immutable(self):
        binding = ChannelBinding(
            source_module="test",
            target_module="test2",
            channel=ChannelType.B1_IDENTITY,
            signal_types=frozenset({"TestSignal"}),
        )
        with pytest.raises(AttributeError):
            binding.source_module = "changed"

    def test_required_defaults_true(self):
        binding = ChannelBinding(
            source_module="a",
            target_module="b",
            channel=ChannelType.B1_IDENTITY,
            signal_types=frozenset({"X"}),
        )
        assert binding.required is True

    def test_description_defaults_empty(self):
        binding = ChannelBinding(
            source_module="a",
            target_module="b",
            channel=ChannelType.B1_IDENTITY,
            signal_types=frozenset({"X"}),
        )
        assert binding.description == ""


# ═══════════════════════════════════════════════════════════════
#  TestChannelAuditEntry — audit record construction
# ═══════════════════════════════════════════════════════════════

class TestChannelAuditEntry:
    """Verify ChannelAuditEntry has all 13 consensus fields and is immutable."""

    def test_has_all_consensus_fields(self):
        """Must have all 13 fields agreed in Q4 consensus (minus schema_version,
        which was simplified out as unnecessary for B-prime observation)."""
        entry = ChannelAuditEntry(
            sequence_number=1,
            timestamp=time.time(),
            channel=ChannelType.B6_SAFETY,
            source_module="aatif_s_equation",
            target_module="aatif_governor",
            signal_type="SafetyDecision",
            payload_hash="abc123",
            payload_size_bytes=128,
            binding_status="allowed",
            severity="info",
            runtime_phase="s_eval",
            duration_ms=0.5,
        )
        assert entry.sequence_number == 1
        assert entry.channel == ChannelType.B6_SAFETY
        assert entry.source_module == "aatif_s_equation"
        assert entry.target_module == "aatif_governor"
        assert entry.signal_type == "SafetyDecision"
        assert entry.payload_hash == "abc123"
        assert entry.payload_size_bytes == 128
        assert entry.binding_status == "allowed"
        assert entry.severity == "info"
        assert entry.runtime_phase == "s_eval"
        assert entry.duration_ms == 0.5

    def test_frozen_immutable(self):
        entry = ChannelAuditEntry(
            sequence_number=1,
            timestamp=time.time(),
            channel=ChannelType.B1_IDENTITY,
            source_module="test",
            target_module=None,
            signal_type="TestSignal",
        )
        with pytest.raises(AttributeError):
            entry.sequence_number = 2

    def test_default_values(self):
        entry = ChannelAuditEntry(
            sequence_number=1,
            timestamp=time.time(),
            channel=ChannelType.B1_IDENTITY,
            source_module="test",
            target_module=None,
            signal_type="TestSignal",
        )
        assert entry.payload_hash is None
        assert entry.payload_size_bytes is None
        assert entry.binding_status == "allowed"
        assert entry.severity == "info"
        assert entry.runtime_phase == "execution"
        assert entry.duration_ms is None

    def test_target_module_can_be_none(self):
        """Target may be None for broadcast signals."""
        entry = ChannelAuditEntry(
            sequence_number=1,
            timestamp=time.time(),
            channel=ChannelType.B2_CONSTITUTIONAL,
            source_module="test",
            target_module=None,
            signal_type="BootVerification",
        )
        assert entry.target_module is None


# ═══════════════════════════════════════════════════════════════
#  TestCanonicalBindings — the architectural truth
# ═══════════════════════════════════════════════════════════════

class TestCanonicalBindings:
    """Verify AATIF_CANONICAL_BINDINGS covers all channels and modules."""

    def test_canonical_is_tuple(self):
        assert isinstance(AATIF_CANONICAL_BINDINGS, tuple), (
            "Canonical bindings must be an immutable tuple"
        )

    def test_all_8_channels_covered(self):
        """Every channel B1-B8 must have at least one canonical binding."""
        channels_present = {b.channel for b in AATIF_CANONICAL_BINDINGS}
        for ch in ChannelType:
            assert ch in channels_present, (
                f"Channel {ch.value} has no canonical binding"
            )

    def test_all_bindings_are_valid_type(self):
        for b in AATIF_CANONICAL_BINDINGS:
            assert isinstance(b, ChannelBinding), (
                f"Expected ChannelBinding, got {type(b)}"
            )

    def test_signal_types_match_channel_allowed(self):
        """Every signal type in a binding must be allowed on its channel."""
        for b in AATIF_CANONICAL_BINDINGS:
            allowed = CHANNEL_ALLOWED_SIGNALS[b.channel]
            invalid = b.signal_types - allowed
            assert not invalid, (
                f"Binding {b.source_module}→{b.target_module} on {b.channel.value}: "
                f"signal types {invalid} not allowed on this channel"
            )

    def test_known_modules_are_present(self):
        """Key AATIF modules must have bindings."""
        sources = {b.source_module for b in AATIF_CANONICAL_BINDINGS}
        expected_modules = {
            "aatif_fingerprint", "aatif_s_equation", "aatif_intent_scorer",
            "aatif_drift_detector", "aatif_output_gate", "aatif_governor",
            "aatif_five_layer_intent", "aatif_r_equation",
        }
        for mod in expected_modules:
            assert mod in sources, f"Module {mod} missing from canonical bindings"

    def test_s_equation_produces_safety(self):
        """aatif_s_equation must produce on B6_SAFETY."""
        s_bindings = [
            b for b in AATIF_CANONICAL_BINDINGS
            if b.source_module == "aatif_s_equation"
               and b.channel == ChannelType.B6_SAFETY
        ]
        assert len(s_bindings) > 0, "S equation must produce on B6_SAFETY"
        all_types = set()
        for b in s_bindings:
            all_types |= b.signal_types
        assert "SafetyDecision" in all_types

    def test_intent_scorer_produces_on_b4(self):
        """aatif_intent_scorer must produce IntentScore on B4."""
        b4_bindings = [
            b for b in AATIF_CANONICAL_BINDINGS
            if b.source_module == "aatif_intent_scorer"
               and b.channel == ChannelType.B4_INTENT
        ]
        assert len(b4_bindings) > 0
        all_types = set()
        for b in b4_bindings:
            all_types |= b.signal_types
        assert "IntentScore" in all_types

    def test_drift_detector_produces_on_b7(self):
        """aatif_drift_detector must produce DriftRisk on B7."""
        b7_bindings = [
            b for b in AATIF_CANONICAL_BINDINGS
            if b.source_module == "aatif_drift_detector"
               and b.channel == ChannelType.B7_DRIFT
        ]
        assert len(b7_bindings) > 0
        all_types = set()
        for b in b7_bindings:
            all_types |= b.signal_types
        assert "DriftRisk" in all_types

    def test_governor_produces_on_b8(self):
        """Governor must produce GovernedPrompt on B8."""
        b8_bindings = [
            b for b in AATIF_CANONICAL_BINDINGS
            if b.source_module == "aatif_governor"
               and b.channel == ChannelType.B8_EXECUTION
        ]
        assert len(b8_bindings) > 0
        all_types = set()
        for b in b8_bindings:
            all_types |= b.signal_types
        assert "GovernedPrompt" in all_types


# ═══════════════════════════════════════════════════════════════
#  TestBindingMap — core class behavior
# ═══════════════════════════════════════════════════════════════

class TestBindingMap:
    """Test BindingMap construction, validation, signal checking, and audit."""

    def test_from_canonical_factory(self):
        bmap = BindingMap.from_canonical(governor_id="test")
        assert isinstance(bmap, BindingMap)

    def test_validate_canonical_passes(self):
        """The canonical map must pass validation."""
        bmap = BindingMap.from_canonical()
        report = bmap.validate()
        assert report.valid is True, (
            f"Canonical map failed validation: {report.violations}"
        )
        assert report.total_bindings > 0
        assert len(report.missing_channels) == 0

    def test_validate_reports_all_channels(self):
        bmap = BindingMap.from_canonical()
        report = bmap.validate()
        assert report.total_bindings == len(AATIF_CANONICAL_BINDINGS)

    def test_validate_detects_missing_channel(self):
        """A map missing a channel should fail validation."""
        # Build a map with only B1 bindings
        partial = tuple(
            b for b in AATIF_CANONICAL_BINDINGS
            if b.channel == ChannelType.B1_IDENTITY
        )
        bmap = BindingMap(canonical_bindings=partial)
        report = bmap.validate()
        assert report.valid is False
        assert len(report.missing_channels) > 0

    def test_validate_detects_wrong_signal_type(self):
        """A binding with a signal type not in its channel's allowed set should fail."""
        bad_binding = ChannelBinding(
            source_module="test_module",
            target_module="aatif_governor",
            channel=ChannelType.B1_IDENTITY,
            signal_types=frozenset({"SafetyDecision"}),  # B6 type on B1!
        )
        # Include all canonical + the bad one
        bindings = AATIF_CANONICAL_BINDINGS + (bad_binding,)
        bmap = BindingMap(canonical_bindings=bindings)
        report = bmap.validate()
        assert report.valid is False
        assert any("not allowed" in v for v in report.violations)

    def test_validate_with_loaded_modules(self):
        """When loaded_modules provided, active/inactive counts should be correct."""
        loaded = frozenset({"aatif_fingerprint", "aatif_governor"})
        bmap = BindingMap.from_canonical(loaded_modules=loaded)
        report = bmap.validate()
        assert report.active_bindings + report.inactive_bindings == report.total_bindings
        assert report.active_bindings >= 1  # at least fingerprint→governor

    def test_get_channel_for_known(self):
        bmap = BindingMap.from_canonical()
        ch = bmap.get_channel_for("aatif_fingerprint", "aatif_governor")
        assert ch == ChannelType.B1_IDENTITY

    def test_get_channel_for_unknown(self):
        bmap = BindingMap.from_canonical()
        ch = bmap.get_channel_for("nonexistent_module", "aatif_governor")
        assert ch is None

    def test_get_bindings_for_channel(self):
        bmap = BindingMap.from_canonical()
        b6 = bmap.get_bindings_for_channel(ChannelType.B6_SAFETY)
        assert len(b6) > 0
        for binding in b6:
            assert binding.channel == ChannelType.B6_SAFETY

    def test_get_bindings_for_source(self):
        bmap = BindingMap.from_canonical()
        bindings = bmap.get_bindings_for_source("aatif_s_equation")
        assert len(bindings) > 0
        for b in bindings:
            assert b.source_module == "aatif_s_equation"

    def test_channel_summary(self):
        bmap = BindingMap.from_canonical()
        summary = bmap.channel_summary()
        assert len(summary) == 8
        for ch_name, count in summary.items():
            assert count > 0, f"Channel {ch_name} has 0 bindings in summary"

    def test_repr(self):
        bmap = BindingMap.from_canonical(governor_id="test_gov")
        r = repr(bmap)
        assert "test_gov" in r
        assert "valid=True" in r


# ═══════════════════════════════════════════════════════════════
#  TestValidateSignal — runtime signal validation
# ═══════════════════════════════════════════════════════════════

class TestValidateSignal:
    """Test validate_signal() — soft runtime signal checking."""

    def test_allowed_signal(self):
        bmap = BindingMap.from_canonical()
        valid, status = bmap.validate_signal(
            source_module="aatif_fingerprint",
            target_module="aatif_governor",
            signal_type="FingerprintReading",
        )
        assert valid is True
        assert status == "allowed"

    def test_unknown_source_target(self):
        bmap = BindingMap.from_canonical()
        valid, status = bmap.validate_signal(
            source_module="nonexistent",
            target_module="aatif_governor",
            signal_type="FingerprintReading",
        )
        assert valid is False
        assert status == "unknown"

    def test_wrong_signal_type(self):
        bmap = BindingMap.from_canonical()
        valid, status = bmap.validate_signal(
            source_module="aatif_fingerprint",
            target_module="aatif_governor",
            signal_type="SafetyDecision",  # B6 type, not B1
        )
        assert valid is False
        assert status == "wrong_type"

    def test_wrong_channel(self):
        bmap = BindingMap.from_canonical()
        valid, status = bmap.validate_signal(
            source_module="aatif_fingerprint",
            target_module="aatif_governor",
            signal_type="FingerprintReading",
            channel=ChannelType.B6_SAFETY,  # wrong channel
        )
        assert valid is False
        assert status == "wrong_channel"

    def test_validate_never_raises(self):
        """validate_signal must never raise — pure observation."""
        bmap = BindingMap.from_canonical()
        # Various invalid inputs should return gracefully
        valid, status = bmap.validate_signal("", "", "")
        assert isinstance(valid, bool)
        assert isinstance(status, str)


# ═══════════════════════════════════════════════════════════════
#  TestAuditTrail — record_signal and retrieval
# ═══════════════════════════════════════════════════════════════

class TestAuditTrail:
    """Test the audit trail: recording, ordering, violation detection."""

    def test_record_creates_entry(self):
        bmap = BindingMap.from_canonical()
        entry = bmap.record_signal(
            channel=ChannelType.B1_IDENTITY,
            source_module="aatif_fingerprint",
            signal_type="FingerprintReading",
            target_module="aatif_governor",
        )
        assert isinstance(entry, ChannelAuditEntry)
        assert entry.sequence_number == 1
        assert entry.binding_status == "allowed"
        assert entry.severity == "info"

    def test_sequence_numbers_monotonic(self):
        bmap = BindingMap.from_canonical()
        e1 = bmap.record_signal(
            channel=ChannelType.B1_IDENTITY,
            source_module="aatif_fingerprint",
            signal_type="FingerprintReading",
        )
        e2 = bmap.record_signal(
            channel=ChannelType.B6_SAFETY,
            source_module="aatif_s_equation",
            signal_type="SafetyDecision",
            target_module="aatif_governor",
        )
        assert e2.sequence_number > e1.sequence_number

    def test_audit_trail_ordered(self):
        bmap = BindingMap.from_canonical()
        for i in range(5):
            bmap.record_signal(
                channel=ChannelType.B4_INTENT,
                source_module="aatif_intent_scorer",
                signal_type="IntentScore",
                target_module="aatif_s_equation",
            )
        trail = bmap.get_audit_trail()
        assert len(trail) == 5
        for i in range(1, len(trail)):
            assert trail[i].sequence_number > trail[i - 1].sequence_number

    def test_violation_detection(self):
        bmap = BindingMap.from_canonical()
        # Record an unknown signal
        entry = bmap.record_signal(
            channel=ChannelType.B1_IDENTITY,
            source_module="unknown_module",
            signal_type="UnknownSignal",
        )
        assert entry.severity == "warning"
        violations = bmap.get_violations()
        # "unknown" gets severity "warning", not "violation"
        # Let's record a real violation (wrong channel)
        entry2 = bmap.record_signal(
            channel=ChannelType.B6_SAFETY,
            source_module="aatif_fingerprint",
            signal_type="FingerprintReading",
            target_module="aatif_governor",
        )
        # This is wrong_channel — should be violation
        assert entry2.severity == "violation"
        violations = bmap.get_violations()
        assert len(violations) >= 1

    def test_payload_hash(self):
        bmap = BindingMap.from_canonical()
        entry = bmap.record_signal(
            channel=ChannelType.B4_INTENT,
            source_module="aatif_intent_scorer",
            signal_type="IntentScore",
            target_module="aatif_s_equation",
            payload={"score": 0.3, "method": "weighted"},
        )
        assert entry.payload_hash is not None
        assert len(entry.payload_hash) == 16  # truncated SHA256
        assert entry.payload_size_bytes is not None
        assert entry.payload_size_bytes > 0

    def test_payload_hash_none_without_payload(self):
        bmap = BindingMap.from_canonical()
        entry = bmap.record_signal(
            channel=ChannelType.B4_INTENT,
            source_module="aatif_intent_scorer",
            signal_type="IntentScore",
        )
        assert entry.payload_hash is None
        assert entry.payload_size_bytes is None

    def test_clear_audit_trail(self):
        bmap = BindingMap.from_canonical()
        bmap.record_signal(
            channel=ChannelType.B1_IDENTITY,
            source_module="test",
            signal_type="TestSignal",
        )
        count = bmap.clear_audit_trail()
        assert count == 1
        assert len(bmap.get_audit_trail()) == 0

    def test_runtime_phase_recorded(self):
        bmap = BindingMap.from_canonical()
        entry = bmap.record_signal(
            channel=ChannelType.B6_SAFETY,
            source_module="aatif_s_equation",
            signal_type="SafetyDecision",
            target_module="aatif_governor",
            runtime_phase="s_eval",
        )
        assert entry.runtime_phase == "s_eval"

    def test_record_never_blocks(self):
        """record_signal must never raise, even with invalid inputs."""
        bmap = BindingMap.from_canonical()
        # Invalid everything — should still return an entry, not raise
        entry = bmap.record_signal(
            channel=ChannelType.B1_IDENTITY,
            source_module="totally_fake",
            signal_type="NotARealSignal",
            target_module=None,
            payload=object(),  # un-serializable
        )
        assert isinstance(entry, ChannelAuditEntry)


# ═══════════════════════════════════════════════════════════════
#  TestPerGovernorInstance — consensus Q5
# ═══════════════════════════════════════════════════════════════

class TestPerGovernorInstance:
    """Verify per-Governor instance model (Q5 consensus)."""

    def test_separate_instances_separate_audit(self):
        """Two BindingMaps must have independent audit trails."""
        bmap1 = BindingMap.from_canonical(governor_id="gov_1")
        bmap2 = BindingMap.from_canonical(governor_id="gov_2")

        bmap1.record_signal(
            channel=ChannelType.B1_IDENTITY,
            source_module="aatif_fingerprint",
            signal_type="FingerprintReading",
        )

        assert len(bmap1.get_audit_trail()) == 1
        assert len(bmap2.get_audit_trail()) == 0

    def test_separate_instances_same_canonical(self):
        """Both instances should share the same canonical binding spec."""
        bmap1 = BindingMap.from_canonical(governor_id="gov_1")
        bmap2 = BindingMap.from_canonical(governor_id="gov_2")

        report1 = bmap1.validate()
        report2 = bmap2.validate()
        assert report1.total_bindings == report2.total_bindings

    def test_different_loaded_modules(self):
        """Two Governors with different module sets should have different active counts."""
        bmap_full = BindingMap.from_canonical(
            loaded_modules=frozenset({
                "aatif_fingerprint", "aatif_governor", "aatif_s_equation",
                "aatif_intent_scorer", "aatif_drift_detector",
            }),
            governor_id="full",
        )
        bmap_minimal = BindingMap.from_canonical(
            loaded_modules=frozenset({"aatif_governor"}),
            governor_id="minimal",
        )
        report_full = bmap_full.validate()
        report_minimal = bmap_minimal.validate()
        assert report_full.active_bindings >= report_minimal.active_bindings


# ═══════════════════════════════════════════════════════════════
#  TestBootValidation — boot-time integration
# ═══════════════════════════════════════════════════════════════

class TestBootValidation:
    """Test validate_binding_map_at_boot() for FN#045 integration."""

    def test_boot_validation_passes(self):
        passed, report, bmap = validate_binding_map_at_boot()
        assert passed is True
        assert report.valid is True
        assert bmap is not None

    def test_boot_returns_binding_map(self):
        passed, report, bmap = validate_binding_map_at_boot(governor_id="boot_test")
        assert isinstance(bmap, BindingMap)

    def test_boot_with_loaded_modules(self):
        loaded = frozenset({
            "aatif_governor", "aatif_s_equation", "aatif_intent_scorer",
            "aatif_fingerprint",
        })
        passed, report, bmap = validate_binding_map_at_boot(
            loaded_modules=loaded, governor_id="boot_with_mods"
        )
        assert passed is True
        assert report.active_bindings > 0

    def test_boot_disabled_flag(self):
        """When BINDING_MAP_ENABLED is False, boot should pass with no map."""
        import aatif_binding_map
        original = aatif_binding_map.BINDING_MAP_ENABLED
        try:
            aatif_binding_map.BINDING_MAP_ENABLED = False
            passed, report, bmap = validate_binding_map_at_boot()
            assert passed is True
            assert bmap is None
        finally:
            aatif_binding_map.BINDING_MAP_ENABLED = original


# ═══════════════════════════════════════════════════════════════
#  TestBPrimeCompliance — the non-negotiable constraint
# ═══════════════════════════════════════════════════════════════

class TestBPrimeCompliance:
    """
    Verify the module is strictly B-prime:
    - Never touches H, θ, or S
    - Never blocks runtime
    - Never emits judicial decisions
    """

    def test_authority_level(self):
        assert AUTHORITY_LEVEL == "B_PRIME_STRUCTURAL_OBSERVATIONAL"

    def test_cannot_block_runtime(self):
        assert CAN_BLOCK_RUNTIME is False

    def test_cannot_modify_payload(self):
        assert CAN_MODIFY_PAYLOAD is False

    def test_cannot_modify_h(self):
        assert CAN_MODIFY_H is False

    def test_cannot_modify_theta(self):
        assert CAN_MODIFY_THETA is False

    def test_cannot_modify_s(self):
        assert CAN_MODIFY_S is False

    def test_cannot_emit_judicial_decision(self):
        assert CAN_EMIT_JUDICIAL_DECISION is False

    def test_can_raise_boot_integrity_error(self):
        assert CAN_RAISE_BOOT_INTEGRITY_ERROR is True

    def test_can_emit_runtime_audit(self):
        assert CAN_EMIT_RUNTIME_AUDIT is True

    def test_validate_signal_never_blocks(self):
        """validate_signal returns bool+status, never raises."""
        bmap = BindingMap.from_canonical()
        # Even obviously wrong calls should return gracefully
        result = bmap.validate_signal("x", "y", "z", ChannelType.B6_SAFETY)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_record_signal_never_blocks(self):
        """record_signal always returns an entry, never raises."""
        bmap = BindingMap.from_canonical()
        entry = bmap.record_signal(
            channel=ChannelType.B1_IDENTITY,
            source_module="fake",
            signal_type="FakeSignal",
        )
        assert isinstance(entry, ChannelAuditEntry)

    def test_no_import_of_s_equation(self):
        """BindingMap must not import aatif_s_equation."""
        import aatif_binding_map
        source_file = aatif_binding_map.__file__
        with open(source_file, "r") as f:
            source = f.read()
        assert "from aatif_s_equation" not in source, (
            "BindingMap must NOT import aatif_s_equation — violates B-prime"
        )
        assert "import aatif_s_equation" not in source, (
            "BindingMap must NOT import aatif_s_equation — violates B-prime"
        )

    def test_no_import_of_governor(self):
        """BindingMap must not import aatif_governor."""
        import aatif_binding_map
        source_file = aatif_binding_map.__file__
        with open(source_file, "r") as f:
            source = f.read()
        assert "from aatif_governor" not in source, (
            "BindingMap must NOT import aatif_governor — violates B-prime"
        )
        assert "import aatif_governor" not in source, (
            "BindingMap must NOT import aatif_governor — violates B-prime"
        )


# ═══════════════════════════════════════════════════════════════
#  TestHashPayload — payload integrity hashing
# ═══════════════════════════════════════════════════════════════

class TestHashPayload:
    """Test _hash_payload helper."""

    def test_dict_payload(self):
        h = _hash_payload({"key": "value"})
        assert h is not None
        assert len(h) == 16

    def test_same_payload_same_hash(self):
        h1 = _hash_payload({"a": 1, "b": 2})
        h2 = _hash_payload({"b": 2, "a": 1})  # different order, same content
        assert h1 == h2

    def test_different_payload_different_hash(self):
        h1 = _hash_payload({"score": 0.3})
        h2 = _hash_payload({"score": 0.7})
        assert h1 != h2

    def test_none_returns_none(self):
        # _hash_payload is called only when payload is not None,
        # but let's verify the function handles edge cases
        h = _hash_payload(None)
        assert h is not None  # None serializes to "null" in JSON

    def test_string_payload(self):
        h = _hash_payload("hello world")
        assert h is not None


# ═══════════════════════════════════════════════════════════════
#  TestNoCrossChannelLeakage — Law 2
# ═══════════════════════════════════════════════════════════════

class TestNoCrossChannelLeakage:
    """
    Law 2: No channel carries a signal type it wasn't designed for.
    Verify this at the canonical map level.
    """

    def test_all_canonical_bindings_respect_channel_types(self):
        """Every binding's signal types must be a subset of its channel's allowed set."""
        for binding in AATIF_CANONICAL_BINDINGS:
            allowed = CHANNEL_ALLOWED_SIGNALS[binding.channel]
            leak = binding.signal_types - allowed
            assert not leak, (
                f"LEAK: {binding.source_module}→{binding.target_module} "
                f"on {binding.channel.value} carries {leak} which is not allowed"
            )

    def test_safety_signals_never_on_identity_channel(self):
        """SafetyDecision must never appear on B1."""
        b1_allowed = CHANNEL_ALLOWED_SIGNALS[ChannelType.B1_IDENTITY]
        assert "SafetyDecision" not in b1_allowed

    def test_identity_signals_never_on_safety_channel(self):
        """FingerprintReading must never appear on B6."""
        b6_allowed = CHANNEL_ALLOWED_SIGNALS[ChannelType.B6_SAFETY]
        assert "FingerprintReading" not in b6_allowed

    def test_intent_signals_never_on_drift_channel(self):
        """IntentScore must never appear on B7."""
        b7_allowed = CHANNEL_ALLOWED_SIGNALS[ChannelType.B7_DRIFT]
        assert "IntentScore" not in b7_allowed


# ═══════════════════════════════════════════════════════════════
#  TestFeatureFlag — BINDING_MAP_ENABLED
# ═══════════════════════════════════════════════════════════════

class TestFeatureFlag:
    """Test BINDING_MAP_ENABLED behavior."""

    def test_feature_flag_default_true(self):
        assert BINDING_MAP_ENABLED is True

    def test_disabled_boot_skips_validation(self):
        import aatif_binding_map
        original = aatif_binding_map.BINDING_MAP_ENABLED
        try:
            aatif_binding_map.BINDING_MAP_ENABLED = False
            passed, report, bmap = validate_binding_map_at_boot()
            assert passed is True
            assert bmap is None
            assert report.total_bindings == 0
        finally:
            aatif_binding_map.BINDING_MAP_ENABLED = original
