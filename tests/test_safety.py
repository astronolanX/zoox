"""
Tests for reef safety infrastructure.

Phase 1 implementation complete:
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


class TestSafetyIntegration:
    """Integration tests for safety infrastructure."""

    def test_deletion_rate_halt(self):
        """Full test of deletion rate halting."""
        guards = PruningSafeguards()

        # Create mock polips (simple objects with id attribute)
        class MockPolip:
            def __init__(self, id, scope="session", type="context"):
                self.id = id
                self.scope = scope
                self.type = type

        # 5 polips total, trying to delete 3 = 60% > 25%
        candidates = [MockPolip(f"polip-{i}") for i in range(3)]
        total = 5

        safe, msg = guards.check_deletion_rate(candidates, total)
        assert safe is False
        assert "HALT" in msg
        assert "60%" in msg or "60.0%" in msg

        # Now with safe rate: 1 out of 5 = 20%
        candidates = [MockPolip("polip-0")]
        safe, msg = guards.check_deletion_rate(candidates, total)
        assert safe is True

    def test_protected_scope_immunity(self):
        """Full test of protected scope immunity."""
        guards = PruningSafeguards()

        class MockPolip:
            def __init__(self, id, scope="session", type="context"):
                self.id = id
                self.scope = scope
                self.type = type

        # Protected scope 'always' should be immune
        always_polip = MockPolip("protected-1", scope="always")
        is_protected, reason = guards.is_protected(always_polip)
        assert is_protected is True
        assert "scope" in reason.lower()

        # Protected type 'constraint' should be immune
        constraint_polip = MockPolip("protected-2", type="constraint")
        is_protected, reason = guards.is_protected(constraint_polip)
        assert is_protected is True
        assert "type" in reason.lower()

        # Regular polip should not be protected
        regular_polip = MockPolip("regular-1", scope="session", type="context")
        is_protected, reason = guards.is_protected(regular_polip)
        assert is_protected is False
        assert reason is None

    def test_dry_run_accuracy(self):
        """Full test of dry run accuracy."""
        guards = PruningSafeguards()

        class MockPolip:
            def __init__(self, id, scope="session", type="context"):
                self.id = id
                self.scope = scope
                self.type = type

        # Mix of protected and prunable
        candidates = [
            MockPolip("prunable-1"),
            MockPolip("prunable-2"),
            MockPolip("protected-1", scope="always"),
            MockPolip("protected-2", type="constraint"),
        ]
        total = 10

        report = guards.dry_run("prune", candidates, total)

        # Should have 2 prunable, 2 protected
        assert report.summary["would_delete"] == 2
        assert report.summary["protected"] == 2
        assert report.summary["total"] == 10

        # Should have warnings about protected polips
        assert len(report.warnings) == 2

        # Should not exceed threshold (2/10 = 20% < 25%)
        assert report.would_exceed_threshold is False

        # Items should only include prunable
        assert len(report.items) == 2

    def test_audit_logging(self):
        """Full test of audit logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = AuditLog(Path(tmpdir))

            # Log some operations
            audit.log_operation("prune", "polip-1", "Stale session polip", agent="sync")
            audit.log_operation("calcify", "polip-2", "High consensus score", agent="calcification")
            audit.log_operation("prune", "polip-3", "Orphan polip")

            # Query all
            entries = audit.query()
            assert len(entries) == 3

            # Query by type
            prune_entries = audit.query(op_type="prune")
            assert len(prune_entries) == 2

            # Query by time (all recent)
            recent = audit.query(since="1h")
            assert len(recent) == 3

            # Summary
            summary = audit.summarize()
            assert summary["total"] == 3
            assert summary["by_type"]["prune"] == 2
            assert summary["by_type"]["calcify"] == 1
            assert "sync" in summary["by_agent"]

    def test_quarantine_restore(self):
        """Full test of quarantine and restore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            undo = UndoBuffer(project_dir)

            # Create a mock polip file
            polip_dir = project_dir / ".claude" / "contexts"
            polip_dir.mkdir(parents=True)
            polip_file = polip_dir / "test-polip.blob.xml"
            polip_file.write_text("<blob>test content</blob>")

            # Quarantine it
            meta = undo.quarantine(
                polip_path=polip_file,
                polip_id="test-polip",
                reason="Test quarantine",
                agent="test",
            )

            # Original should be gone
            assert not polip_file.exists()

            # Should be in quarantine
            items = undo.list_quarantined()
            assert len(items) == 1
            assert items[0].polip_id == "test-polip"
            assert items[0].reason == "Test quarantine"

            # Restore it
            success, message = undo.restore("test-polip")
            assert success is True

            # Original should be back
            assert polip_file.exists()
            assert polip_file.read_text() == "<blob>test content</blob>"

            # Quarantine should be empty
            items = undo.list_quarantined()
            assert len(items) == 0

    def test_quarantine_expiry(self):
        """Full test of quarantine expiry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            undo = UndoBuffer(project_dir)

            # Create and quarantine a polip
            polip_dir = project_dir / ".claude" / "contexts"
            polip_dir.mkdir(parents=True)
            polip_file = polip_dir / "old-polip.blob.xml"
            polip_file.write_text("<blob>old content</blob>")

            meta = undo.quarantine(
                polip_path=polip_file,
                polip_id="old-polip",
                reason="Test expiry",
            )

            # Manually set expiry to past
            metadata = undo._load_metadata()
            metadata["old-polip"].expires = datetime.now() - timedelta(days=1)
            undo._save_metadata(metadata)

            # Run expiry
            expired = undo.expire_old()
            assert "old-polip" in expired

            # Should be permanently gone
            items = undo.list_quarantined()
            assert len(items) == 0

            # Restore should fail
            success, message = undo.restore("old-polip")
            assert success is False


class TestDryRunReport:
    """Tests for DryRunReport functionality."""

    def test_to_dict(self):
        """Verify DryRunReport serialization."""
        from reef.safety.guards import DryRunItem

        report = DryRunReport(
            operation="prune",
            timestamp=datetime.now(),
            items=[
                DryRunItem(
                    polip_id="test-1",
                    action="delete",
                    reason="Stale",
                    confidence=0.9,
                )
            ],
            summary={"would_delete": 1, "protected": 0, "total": 5},
            warnings=["Test warning"],
            would_exceed_threshold=False,
        )

        data = report.to_dict()
        assert data["operation"] == "prune"
        assert len(data["items"]) == 1
        assert data["items"][0]["polip_id"] == "test-1"
        assert data["summary"]["would_delete"] == 1
        assert "Test warning" in data["warnings"]

    def test_approve_operation(self):
        """Test operation approval logic."""
        guards = PruningSafeguards()

        # Report that would exceed threshold
        report = DryRunReport(
            operation="prune",
            timestamp=datetime.now(),
            items=[],
            summary={"would_delete": 5, "protected": 0, "total": 10},
            warnings=["HALT: Deletion rate exceeds threshold"],
            would_exceed_threshold=True,
        )

        # Should not approve without force
        approved, msg = guards.approve_operation(report)
        assert approved is False
        assert "threshold" in msg.lower()

        # Should approve with force
        approved, msg = guards.approve_operation(report, force=True)
        assert approved is True
