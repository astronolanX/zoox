"""
Tests for reef safety infrastructure.

Phase 1 will implement:
- test_deletion_rate_halt
- test_protected_scope_immunity
- test_dry_run_accuracy
- test_audit_logging
- test_quarantine_restore
- test_quarantine_expiry
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from reef.safety import PruningSafeguards, DryRunReport, AuditLog, AuditEntry, UndoBuffer


class TestPruningSafeguards:
    """Tests for pruning safeguards."""

    def test_import(self):
        """Verify module imports correctly."""
        assert PruningSafeguards is not None
        assert DryRunReport is not None

    def test_instantiation(self):
        """Verify can create safeguards instance."""
        guards = PruningSafeguards()
        assert guards is not None
        assert guards.MAX_DELETION_RATE == 0.25

    def test_protected_scopes(self):
        """Verify protected scopes are defined."""
        guards = PruningSafeguards()
        assert "always" in guards.PROTECTED_SCOPES

    def test_check_deletion_rate_safe(self):
        """Verify safe deletion rate passes."""
        guards = PruningSafeguards()
        # 2 out of 10 = 20%, under 25% threshold
        safe, msg = guards.check_deletion_rate(["a", "b"], 10)
        assert safe is True

    def test_check_deletion_rate_unsafe(self):
        """Verify unsafe deletion rate fails."""
        guards = PruningSafeguards()
        # 4 out of 10 = 40%, over 25% threshold
        safe, msg = guards.check_deletion_rate(["a", "b", "c", "d"], 10)
        assert safe is False
        assert "HALT" in msg

    def test_check_deletion_rate_skips_small_reef(self):
        """Verify rate check skipped for small reefs."""
        guards = PruningSafeguards()
        # Small reef (3 polips) skips rate check
        safe, msg = guards.check_deletion_rate(["a", "b"], 3)
        assert safe is True
        assert "Skipping" in msg


class TestAuditLog:
    """Tests for audit logging."""

    def test_import(self):
        """Verify module imports correctly."""
        assert AuditLog is not None
        assert AuditEntry is not None

    def test_instantiation(self):
        """Verify can create audit log instance."""
        audit = AuditLog()
        assert audit is not None

    def test_audit_entry_serialization(self):
        """Verify audit entry can serialize/deserialize."""
        entry = AuditEntry(
            timestamp=datetime.now(),
            op_type="prune",
            polip_id="test-123",
            reason="Test reason",
            agent="test-agent",
        )
        data = entry.to_dict()
        restored = AuditEntry.from_dict(data)
        assert restored.polip_id == entry.polip_id
        assert restored.op_type == entry.op_type


class TestUndoBuffer:
    """Tests for undo buffer (quarantine)."""

    def test_import(self):
        """Verify module imports correctly."""
        assert UndoBuffer is not None

    def test_instantiation(self):
        """Verify can create undo buffer instance."""
        undo = UndoBuffer()
        assert undo is not None
        assert undo.QUARANTINE_DAYS == 7

    def test_list_empty_quarantine(self):
        """Verify empty quarantine returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            undo = UndoBuffer(Path(tmpdir))
            items = undo.list_quarantined()
            assert items == []


# Phase 1 TODO tests - will be implemented when safety infrastructure is complete

class TestSafetyIntegration:
    """Integration tests for safety infrastructure."""

    @pytest.mark.skip(reason="Requires Phase 1 implementation")
    def test_deletion_rate_halt(self):
        """Full test of deletion rate halting."""
        pass

    @pytest.mark.skip(reason="Requires Phase 1 implementation")
    def test_protected_scope_immunity(self):
        """Full test of protected scope immunity."""
        pass

    @pytest.mark.skip(reason="Requires Phase 1 implementation")
    def test_dry_run_accuracy(self):
        """Full test of dry run accuracy."""
        pass

    @pytest.mark.skip(reason="Requires Phase 1 implementation")
    def test_quarantine_restore(self):
        """Full test of quarantine and restore."""
        pass

    @pytest.mark.skip(reason="Requires Phase 1 implementation")
    def test_quarantine_expiry(self):
        """Full test of quarantine expiry."""
        pass
