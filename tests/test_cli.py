"""
Comprehensive test suite for CLI commands.
Tests cover: sprout, list, migrate, decompose - including edge cases.
"""

import pytest
import subprocess
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

from reef.blob import Blob, BlobType, BlobScope, BlobStatus, Glob, BLOB_VERSION


def run_cli(*args, cwd=None):
    """Run reef CLI and return result."""
    result = subprocess.run(
        ["uv", "run", "reef", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result


class TestCliSprout:
    """CLI sprout command tests."""

    def test_sprout_thread(self):
        """Create a thread blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "thread", "Test thread", cwd=tmpdir)
            assert result.returncode == 0
            assert "Spawned" in result.stdout

            # Verify file exists (new structure: .reef/current/*.reef)
            assert (Path(tmpdir) / ".reef" / "current" / "test-thread.reef").exists()

    def test_sprout_decision(self):
        """Create a decision blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "decision", "Use pytest", cwd=tmpdir)
            assert result.returncode == 0
            # Decisions go to current/ with .reef extension
            assert (Path(tmpdir) / ".reef" / "current").is_dir()

    def test_sprout_constraint(self):
        """Create a constraint blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "constraint", "No pip allowed", cwd=tmpdir)
            assert result.returncode == 0

            # Verify scope is ALWAYS (constraints go to bedrock/ with .rock extension)
            glob = Glob(Path(tmpdir))
            blob = glob.get("no-pip-allowed", subdir="bedrock")
            assert blob.scope == BlobScope.ALWAYS

    def test_sprout_fact(self):
        """Create a fact blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "fact", "Python 3.10 required", cwd=tmpdir)
            assert result.returncode == 0
            # Facts go to current/ with .reef extension
            assert (Path(tmpdir) / ".reef" / "current").is_dir()

    def test_sprout_context_rejected(self):
        """Context type is rejected (auto-created only)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "context", "Manual context", cwd=tmpdir)
            assert result.returncode != 0
            assert "auto-created" in result.stderr

    def test_sprout_invalid_type(self):
        """Invalid type is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "invalid", "Test", cwd=tmpdir)
            assert result.returncode != 0
            assert "Invalid type" in result.stderr

    def test_sprout_with_status(self):
        """Thread with explicit status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "thread", "Blocked thread", "--status", "blocked", cwd=tmpdir)
            assert result.returncode == 0

            glob = Glob(Path(tmpdir))
            blob = glob.get("blocked-thread", subdir="current")
            assert blob.status == BlobStatus.BLOCKED

    def test_sprout_status_only_for_threads(self):
        """Status rejected for non-thread types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "fact", "Test", "--status", "active", cwd=tmpdir)
            assert result.returncode != 0
            assert "only applies to thread" in result.stderr

    def test_sprout_invalid_status(self):
        """Invalid status is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "thread", "Test", "--status", "invalid", cwd=tmpdir)
            assert result.returncode != 0
            assert "Invalid status" in result.stderr

    def test_sprout_custom_name(self):
        """Custom blob name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "fact", "Test summary", "-n", "custom-name", cwd=tmpdir)
            assert result.returncode == 0
            assert (Path(tmpdir) / ".reef" / "current" / "custom-name.reef").exists()

    def test_sprout_custom_dir(self):
        """Custom directory override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "fact", "Test", "-d", "custom-dir", cwd=tmpdir)
            assert result.returncode == 0
            assert (Path(tmpdir) / ".reef" / "custom-dir").is_dir()

    def test_sprout_name_truncation(self):
        """Long summaries are truncated for name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            long_summary = "This is a very long summary that should be truncated to thirty characters"
            result = run_cli("sprout", "fact", long_summary, cwd=tmpdir)
            assert result.returncode == 0

            # Check filename is max 30 chars (plus .reef extension)
            current_dir = Path(tmpdir) / ".reef" / "current"
            blob_files = list(current_dir.glob("*.reef"))
            assert len(blob_files) == 1
            name_part = blob_files[0].stem
            assert len(name_part) <= 30

    def test_sprout_special_chars_in_summary(self):
        """Special characters are cleaned from name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "fact", "Test: with/special?chars!", cwd=tmpdir)
            assert result.returncode == 0

            # Name should be cleaned
            current_dir = Path(tmpdir) / ".reef" / "current"
            blob_files = list(current_dir.glob("*.reef"))
            assert len(blob_files) == 1


class TestCliList:
    """CLI list command tests."""

    def test_list_empty(self):
        """List on empty project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("list", cwd=tmpdir)
            assert result.returncode == 0
            assert "No polips found" in result.stdout

    def test_list_with_blobs(self):
        """List shows blob population."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some blobs
            run_cli("sprout", "thread", "Thread 1", cwd=tmpdir)
            run_cli("sprout", "constraint", "Rule 1", cwd=tmpdir)
            run_cli("sprout", "fact", "Fact 1", cwd=tmpdir)

            result = run_cli("list", cwd=tmpdir)
            assert result.returncode == 0
            assert "Population: 3" in result.stdout
            assert "thread" in result.stdout
            assert "constraint" in result.stdout

    def test_list_shows_active_threads(self):
        """List shows active threads section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Active work item", cwd=tmpdir)

            result = run_cli("list", cwd=tmpdir)
            assert result.returncode == 0
            assert "Active Currents" in result.stdout

    def test_list_shows_schema_status(self):
        """List shows schema version status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "fact", "Current schema", cwd=tmpdir)

            result = run_cli("list", cwd=tmpdir)
            assert result.returncode == 0
            assert "Schema" in result.stdout

    def test_list_detects_missing_files(self):
        """List detects missing file references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            blob = Blob(
                type=BlobType.THREAD,
                summary="Test",
                status=BlobStatus.ACTIVE,
                files=["nonexistent.py"],
            )
            glob.sprout(blob, "test", subdir="current")

            result = run_cli("list", cwd=tmpdir)
            assert result.returncode == 0
            assert "missing" in result.stdout.lower()

    def test_list_injection_impact(self):
        """List shows injection impact estimate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "constraint", "Rule", cwd=tmpdir)

            result = run_cli("list", cwd=tmpdir)
            assert result.returncode == 0
            assert "Surfacing Impact" in result.stdout
            assert "tokens" in result.stdout


class TestCliMigrate:
    """CLI migrate command tests."""

    def test_migrate_nothing_to_do(self):
        """Migrate when all blobs are current."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "fact", "Current blob", cwd=tmpdir)

            result = run_cli("migrate", cwd=tmpdir)
            assert result.returncode == 0
            assert "current version" in result.stdout.lower()

    def test_migrate_dry_run(self):
        """Migrate dry run shows what would change."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an old-version blob
            glob = Glob(Path(tmpdir))
            old_blob = Blob(type=BlobType.FACT, summary="Old", version=1)
            glob.sprout(old_blob, "old")

            result = run_cli("migrate", "--dry-run", cwd=tmpdir)
            assert result.returncode == 0
            assert "needing migration" in result.stdout
            assert "--dry-run" in result.stdout

            # Blob should still be old
            reloaded = glob.get("old")
            assert reloaded.version == 1

    def test_migrate_applies(self):
        """Migrate actually updates blobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            old_blob = Blob(type=BlobType.FACT, summary="Old", version=1)
            glob.sprout(old_blob, "old")

            result = run_cli("migrate", cwd=tmpdir)
            assert result.returncode == 0
            assert "Migrated" in result.stdout

            reloaded = glob.get("old")
            assert reloaded.version == BLOB_VERSION


class TestCliDecompose:
    """CLI decompose command tests."""

    def test_decompose_nothing_stale(self):
        """Decompose when no stale blobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Session blob but recent
            glob = Glob(Path(tmpdir))
            blob = Blob(type=BlobType.CONTEXT, summary="Recent", scope=BlobScope.SESSION)
            glob.sprout(blob, "recent", subdir="current")

            result = run_cli("decompose", cwd=tmpdir)
            assert result.returncode == 0
            assert "No stale" in result.stdout

    def test_decompose_finds_stale(self):
        """Decompose finds stale session blobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            old_time = datetime.now() - timedelta(days=10)
            blob = Blob(type=BlobType.CONTEXT, summary="Old session", scope=BlobScope.SESSION, updated=old_time)
            glob.sprout(blob, "old-session", subdir="current")

            result = run_cli("decompose", "--dry-run", cwd=tmpdir)
            assert result.returncode == 0
            assert "stale" in result.stdout.lower()
            assert "--dry-run" in result.stdout

    def test_decompose_custom_days(self):
        """Decompose with custom days threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            three_days_ago = datetime.now() - timedelta(days=3)
            blob = Blob(type=BlobType.CONTEXT, summary="Kinda old", scope=BlobScope.SESSION, updated=three_days_ago)
            glob.sprout(blob, "kinda-old", subdir="current")

            # Default 7 days - should not find it
            result1 = run_cli("decompose", "--dry-run", cwd=tmpdir)
            assert "No stale" in result1.stdout

            # 2 days - should find it
            result2 = run_cli("decompose", "--days", "2", "--dry-run", cwd=tmpdir)
            assert "stale" in result2.stdout.lower()

    def test_decompose_deletes(self):
        """Decompose actually deletes stale blobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            old_time = datetime.now() - timedelta(days=10)
            blob = Blob(type=BlobType.CONTEXT, summary="To delete", scope=BlobScope.SESSION, updated=old_time)
            glob.sprout(blob, "to-delete", subdir="current")

            result = run_cli("decompose", cwd=tmpdir)
            assert result.returncode == 0
            assert "Decomposed" in result.stdout

            # File should be gone
            assert not (Path(tmpdir) / ".reef" / "current" / "to-delete.reef").exists()

    def test_decompose_ignores_project_scope(self):
        """Decompose ignores project-scope blobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            old_time = datetime.now() - timedelta(days=30)
            blob = Blob(type=BlobType.FACT, summary="Old but project", scope=BlobScope.PROJECT, updated=old_time)
            glob.sprout(blob, "old-project")

            result = run_cli("decompose", cwd=tmpdir)
            assert "No stale" in result.stdout

            # Should still exist
            assert (Path(tmpdir) / ".reef" / "old-project.reef").exists()


class TestCliVersion:
    """CLI version and help tests."""

    def test_version(self):
        """--version shows version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("--version", cwd=tmpdir)
            assert "0.1.0" in result.stdout

    def test_help(self):
        """--help shows usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("--help", cwd=tmpdir)
            assert result.returncode == 0
            assert "sprout" in result.stdout
            assert "list" in result.stdout
            assert "migrate" in result.stdout
            assert "decompose" in result.stdout


class TestCliTemplate:
    """CLI template command tests."""

    def test_template_list(self):
        """List available templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "list", cwd=tmpdir)
            assert result.returncode == 0
            assert "Templates" in result.stdout
            assert "bug" in result.stdout
            assert "feature" in result.stdout
            assert "decision" in result.stdout
            assert "research" in result.stdout

    def test_template_show(self):
        """Show template details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "show", "bug", cwd=tmpdir)
            assert result.returncode == 0
            assert "Template: bug" in result.stdout
            assert "Type: thread" in result.stdout

    def test_template_show_not_found(self):
        """Show nonexistent template fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "show", "nonexistent", cwd=tmpdir)
            assert result.returncode != 0
            assert "not found" in result.stderr

    def test_template_use_bug(self):
        """Create polip from bug template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "use", "bug", "Login fails on Safari", cwd=tmpdir)
            assert result.returncode == 0
            assert "Created" in result.stdout

            # Verify polip created with template structure
            glob = Glob(Path(tmpdir))
            blob = glob.get("login-fails-on-safari", subdir="current")
            assert blob is not None
            assert "Bug:" in blob.summary
            assert blob.status == BlobStatus.ACTIVE
            assert len(blob.next_steps) > 0

    def test_template_use_feature(self):
        """Create polip from feature template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "use", "feature", "Dark mode", cwd=tmpdir)
            assert result.returncode == 0

            glob = Glob(Path(tmpdir))
            blob = glob.get("dark-mode", subdir="current")
            assert blob is not None
            assert "Feature:" in blob.summary

    def test_template_use_decision(self):
        """Create polip from decision template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "use", "decision", "Use PostgreSQL", cwd=tmpdir)
            assert result.returncode == 0

            glob = Glob(Path(tmpdir))
            blob = glob.get("use-postgresql", subdir="current")
            assert blob is not None
            assert "ADR:" in blob.summary

    def test_template_use_constraint(self):
        """Create polip from constraint template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "use", "constraint", "No pip allowed", cwd=tmpdir)
            assert result.returncode == 0

            glob = Glob(Path(tmpdir))
            blob = glob.get("no-pip-allowed", subdir="bedrock")
            assert blob is not None
            assert blob.scope == BlobScope.ALWAYS

    def test_template_use_not_found(self):
        """Use nonexistent template fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "use", "nonexistent", "Test", cwd=tmpdir)
            assert result.returncode != 0
            assert "not found" in result.stderr

    def test_template_use_missing_title(self):
        """Use template without title fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "use", "bug", cwd=tmpdir)
            assert result.returncode != 0


class TestCliGraph:
    """CLI graph command tests."""

    def test_graph_empty(self):
        """Graph on empty reef."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("graph", cwd=tmpdir)
            assert result.returncode == 0
            assert "No polips" in result.stdout

    def test_graph_with_polips(self):
        """Graph shows polips by type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)
            run_cli("sprout", "constraint", "Test constraint", cwd=tmpdir)
            run_cli("sprout", "fact", "Test fact", cwd=tmpdir)

            result = run_cli("graph", cwd=tmpdir)
            assert result.returncode == 0
            assert "3 polips" in result.stdout
            assert "thread" in result.stdout
            assert "constraint" in result.stdout
            assert "fact" in result.stdout

    def test_graph_dot_format(self):
        """Graph outputs DOT format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)

            result = run_cli("graph", "--dot", cwd=tmpdir)
            assert result.returncode == 0
            assert "digraph reef" in result.stdout
            assert "current/test-thread" in result.stdout

    def test_graph_shows_status(self):
        """Graph shows polip status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Blocked work", "--status", "blocked", cwd=tmpdir)

            result = run_cli("graph", cwd=tmpdir)
            assert result.returncode == 0
            assert "[blocked]" in result.stdout

    def test_graph_with_related_links(self):
        """Graph detects related links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create polips with related links
            blob1 = Blob(type=BlobType.THREAD, summary="Thread 1", status=BlobStatus.ACTIVE, related=["current/fact-1"])
            blob2 = Blob(type=BlobType.FACT, summary="Fact 1")

            glob.sprout(blob1, "thread-1", subdir="current")
            glob.sprout(blob2, "fact-1", subdir="current")

            result = run_cli("graph", cwd=tmpdir)
            assert result.returncode == 0
            assert "explicit link" in result.stdout

    def test_graph_with_shared_files(self):
        """Graph detects shared file references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create polips referencing same file
            blob1 = Blob(type=BlobType.THREAD, summary="Thread 1", status=BlobStatus.ACTIVE, files=["shared.py"])
            blob2 = Blob(type=BlobType.FACT, summary="Fact 1", files=["shared.py"])

            glob.sprout(blob1, "thread-1", subdir="current")
            glob.sprout(blob2, "fact-1", subdir="current")

            result = run_cli("graph", cwd=tmpdir)
            assert result.returncode == 0
            assert "shared file" in result.stdout


class TestCliSnapshot:
    """CLI snapshot command tests."""

    def test_snapshot_create(self):
        """Create a snapshot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)
            run_cli("sprout", "fact", "Test fact", cwd=tmpdir)

            result = run_cli("snapshot", "create", cwd=tmpdir)
            assert result.returncode == 0
            assert "Snapshot created" in result.stdout

            # Verify file exists
            snapshot_dir = Path(tmpdir) / ".reef" / "snapshots"
            assert snapshot_dir.exists()
            assert len(list(snapshot_dir.glob("*.snapshot.json"))) == 1

    def test_snapshot_create_with_name(self):
        """Create a named snapshot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test", cwd=tmpdir)

            result = run_cli("snapshot", "create", "--name", "milestone-1", cwd=tmpdir)
            assert result.returncode == 0

            snapshot_dir = Path(tmpdir) / ".reef" / "snapshots"
            files = list(snapshot_dir.glob("*milestone-1*.json"))
            assert len(files) == 1

    def test_snapshot_list_empty(self):
        """List with no snapshots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("snapshot", "list", cwd=tmpdir)
            assert result.returncode == 0
            assert "No snapshots" in result.stdout

    def test_snapshot_list(self):
        """List existing snapshots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test", cwd=tmpdir)
            run_cli("snapshot", "create", "--name", "first", cwd=tmpdir)
            run_cli("snapshot", "create", "--name", "second", cwd=tmpdir)

            result = run_cli("snapshot", "list", cwd=tmpdir)
            assert result.returncode == 0
            assert "Snapshots (2)" in result.stdout
            assert "first" in result.stdout
            assert "second" in result.stdout

    def test_snapshot_diff_no_changes(self):
        """Diff with no changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test", cwd=tmpdir)
            run_cli("snapshot", "create", "--name", "base", cwd=tmpdir)

            result = run_cli("snapshot", "diff", "base", cwd=tmpdir)
            assert result.returncode == 0
            assert "No changes" in result.stdout

    def test_snapshot_diff_with_additions(self):
        """Diff detects added polips."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Thread 1", cwd=tmpdir)
            run_cli("snapshot", "create", "--name", "before", cwd=tmpdir)
            run_cli("sprout", "fact", "New fact", cwd=tmpdir)

            result = run_cli("snapshot", "diff", "before", cwd=tmpdir)
            assert result.returncode == 0
            assert "Added" in result.stdout

    def test_snapshot_diff_with_removals(self):
        """Diff detects removed polips."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Thread 1", cwd=tmpdir)
            run_cli("sprout", "fact", "Fact 1", cwd=tmpdir)
            run_cli("snapshot", "create", "--name", "before", cwd=tmpdir)

            # Remove the fact
            (Path(tmpdir) / ".reef" / "current" / "fact-1.reef").unlink()

            result = run_cli("snapshot", "diff", "before", cwd=tmpdir)
            assert result.returncode == 0
            assert "Removed" in result.stdout

    def test_snapshot_diff_with_status_change(self):
        """Diff detects status changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Thread 1", cwd=tmpdir)
            run_cli("snapshot", "create", "--name", "before", cwd=tmpdir)
            run_cli("status", "thread-1", "blocked", cwd=tmpdir)

            result = run_cli("snapshot", "diff", "before", cwd=tmpdir)
            assert result.returncode == 0
            assert "Changed" in result.stdout
            assert "status" in result.stdout

    def test_snapshot_diff_not_found(self):
        """Diff with nonexistent snapshot fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("snapshot", "diff", "nonexistent", cwd=tmpdir)
            assert result.returncode != 0
            assert "No snapshot matching" in result.stderr


class TestCliStatus:
    """CLI status command tests."""

    def test_status_show_current(self):
        """Show current status of a polip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)

            result = run_cli("status", "test-thread", cwd=tmpdir)
            assert result.returncode == 0
            assert "active" in result.stdout

    def test_status_change_to_blocked(self):
        """Change status to blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)

            result = run_cli("status", "test-thread", "blocked", cwd=tmpdir)
            assert result.returncode == 0
            assert "blocked" in result.stdout

            # Verify change persisted
            glob = Glob(Path(tmpdir))
            blob = glob.get("test-thread", subdir="current")
            assert blob.status == BlobStatus.BLOCKED

    def test_status_change_to_done(self):
        """Change status to done."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)

            result = run_cli("status", "test-thread", "done", cwd=tmpdir)
            assert result.returncode == 0
            assert "done" in result.stdout

    def test_status_with_blocked_by(self):
        """Set blocked-by reason."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)

            result = run_cli("status", "test-thread", "blocked", "-b", "Waiting for API", cwd=tmpdir)
            assert result.returncode == 0

            glob = Glob(Path(tmpdir))
            blob = glob.get("test-thread", subdir="current")
            assert blob.blocked_by == "Waiting for API"

    def test_status_clears_blocked_by_on_active(self):
        """Blocked-by is cleared when status changes to active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)
            run_cli("status", "test-thread", "blocked", "-b", "Waiting", cwd=tmpdir)
            run_cli("status", "test-thread", "active", cwd=tmpdir)

            glob = Glob(Path(tmpdir))
            blob = glob.get("test-thread", subdir="current")
            assert blob.status == BlobStatus.ACTIVE
            assert blob.blocked_by is None

    def test_status_not_found(self):
        """Status on nonexistent polip fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("status", "nonexistent", cwd=tmpdir)
            assert result.returncode != 0
            assert "not found" in result.stderr

    def test_status_invalid_status(self):
        """Invalid status is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)

            result = run_cli("status", "test-thread", "invalid", cwd=tmpdir)
            assert result.returncode != 0
            assert "Invalid status" in result.stderr

    def test_status_archived_rejected(self):
        """Archived status is rejected (use decompose)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)

            result = run_cli("status", "test-thread", "archived", cwd=tmpdir)
            assert result.returncode != 0
            assert "decompose" in result.stderr

    def test_status_auto_detect_subdir(self):
        """Status auto-detects subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "fact", "Test fact", cwd=tmpdir)

            # Should find it without --dir
            result = run_cli("status", "test-fact", cwd=tmpdir)
            assert result.returncode == 0

    def test_status_explicit_subdir(self):
        """Status with explicit subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)

            result = run_cli("status", "test-thread", "--dir", "current", cwd=tmpdir)
            assert result.returncode == 0


class TestCliEdgeCases:
    """CLI edge cases and error handling."""

    def test_missing_command(self):
        """Missing subcommand shows error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli(cwd=tmpdir)
            assert result.returncode != 0

    def test_sprout_empty_summary(self):
        """Empty summary is handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "fact", "", cwd=tmpdir)
            # May succeed or fail depending on argparse behavior
            # Just check it doesn't crash

    def test_unicode_in_cli_args(self):
        """Unicode in CLI arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "fact", "Unicode: 日本語 🚀", cwd=tmpdir)
            assert result.returncode == 0

    def test_quotes_in_summary(self):
        """Quotes in summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "fact", 'Use "uv" for packages', cwd=tmpdir)
            assert result.returncode == 0


class TestCliHook:
    """CLI hook command tests for Claude Code integration."""

    def test_hook_surface_empty_reef(self):
        """Surface with no polips produces no output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("hook", "surface", cwd=tmpdir)
            assert result.returncode == 0
            # Empty reef - no [GLOB] output
            assert "[GLOB]" not in result.stdout

    def test_hook_surface_with_polips(self):
        """Surface outputs XML when polips exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a polip first
            run_cli("sprout", "constraint", "Test constraint", cwd=tmpdir)

            result = run_cli("hook", "surface", cwd=tmpdir)
            assert result.returncode == 0
            assert "[GLOB]" in result.stdout
            assert "Test constraint" in result.stdout
            assert "<blob" in result.stdout

    def test_hook_surface_respects_surfacing_rules(self):
        """Surface follows relevance scoring."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Constraint always surfaces
            run_cli("sprout", "constraint", "Always visible", cwd=tmpdir)
            # Active thread surfaces
            run_cli("sprout", "thread", "Active work", cwd=tmpdir)

            result = run_cli("hook", "surface", cwd=tmpdir)
            assert result.returncode == 0
            assert "Always visible" in result.stdout
            assert "Active work" in result.stdout

    def test_hook_persist_creates_context(self):
        """Persist creates context polip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli(
                "hook", "persist",
                "--summary", "Session completed",
                "--quiet",
                cwd=tmpdir
            )
            assert result.returncode == 0

            # Verify context blob exists
            context_path = Path(tmpdir) / ".reef" / "context.reef"
            assert context_path.exists()

            blob = Blob.load(context_path)
            assert blob.type == BlobType.CONTEXT
            assert blob.summary == "Session completed"

    def test_hook_persist_updates_existing(self):
        """Persist updates existing context polip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create initial context
            run_cli("hook", "persist", "--summary", "First session", "--quiet", cwd=tmpdir)

            # Update it
            run_cli("hook", "persist", "--summary", "Second session", "--quiet", cwd=tmpdir)

            # Verify updated
            context_path = Path(tmpdir) / ".reef" / "context.reef"
            blob = Blob.load(context_path)
            assert blob.summary == "Second session"

    def test_hook_persist_with_files(self):
        """Persist with file list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli(
                "hook", "persist",
                "--summary", "Worked on files",
                "--files", "src/main.py,src/utils.py",
                "--quiet",
                cwd=tmpdir
            )
            assert result.returncode == 0

            blob = Blob.load(Path(tmpdir) / ".reef" / "context.reef")
            assert blob.files == ["src/main.py", "src/utils.py"]

    def test_hook_persist_with_next_steps(self):
        """Persist with next steps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli(
                "hook", "persist",
                "--summary", "Partial work",
                "--next", "Finish tests|Review code",
                "--quiet",
                cwd=tmpdir
            )
            assert result.returncode == 0

            blob = Blob.load(Path(tmpdir) / ".reef" / "context.reef")
            assert blob.next_steps == ["Finish tests", "Review code"]

    def test_hook_persist_default_summary(self):
        """Persist uses default summary if none provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("hook", "persist", "--quiet", cwd=tmpdir)
            assert result.returncode == 0

            blob = Blob.load(Path(tmpdir) / ".reef" / "context.reef")
            assert "auto-generated" in blob.summary.lower()

    def test_hook_setup_outputs_json(self):
        """Setup with --json outputs raw JSON config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("hook", "setup", "--json", cwd=tmpdir)
            assert result.returncode == 0

            import json
            config = json.loads(result.stdout)
            assert "hooks" in config
            assert "UserPromptSubmit" in config["hooks"]
            assert "Stop" in config["hooks"]

    def test_hook_setup_outputs_instructions(self):
        """Setup without --json outputs instructions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("hook", "setup", cwd=tmpdir)
            assert result.returncode == 0
            assert "settings.json" in result.stdout
            assert "reef hook surface" in result.stdout
            assert "reef hook persist" in result.stdout

    def test_hook_status_no_settings(self):
        """Status reports missing settings.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Run in isolated temp dir without ~/.claude
            result = run_cli("hook", "status", cwd=tmpdir)
            assert result.returncode == 0
            # Either reports NOT FOUND or shows status
            assert "Hook Status" in result.stdout

    def test_hook_status_shows_reef_count(self):
        """Status shows polip count when reef exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some polips
            run_cli("sprout", "constraint", "Rule 1", cwd=tmpdir)
            run_cli("sprout", "thread", "Work item", cwd=tmpdir)

            result = run_cli("hook", "status", cwd=tmpdir)
            assert result.returncode == 0
            assert "Reef" in result.stdout
            assert "polip" in result.stdout


class TestCliHookIntegration:
    """Integration tests for hook lifecycle."""

    def test_full_session_lifecycle(self):
        """Simulate a complete session with surface -> work -> persist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Initial state - create some polips
            run_cli("sprout", "constraint", "Use type hints", cwd=tmpdir)
            run_cli("sprout", "thread", "Implement feature X", cwd=tmpdir)

            # 2. Session start - surface
            surface_result = run_cli("hook", "surface", cwd=tmpdir)
            assert surface_result.returncode == 0
            assert "[GLOB]" in surface_result.stdout
            assert "Use type hints" in surface_result.stdout

            # 3. Session end - persist
            persist_result = run_cli(
                "hook", "persist",
                "--summary", "Completed feature X implementation",
                "--files", "src/feature_x.py",
                "--next", "Write tests|Update docs",
                "--quiet",
                cwd=tmpdir
            )
            assert persist_result.returncode == 0

            # 4. Next session - surface includes context
            next_surface = run_cli("hook", "surface", cwd=tmpdir)
            assert next_surface.returncode == 0
            # Context may or may not surface depending on recency
            # But constraints should always surface
            assert "Use type hints" in next_surface.stdout


class TestCliDrift:
    """CLI drift command tests for cross-project polip discovery."""

    def test_drift_discover_empty(self):
        """Discover with no nearby reefs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create isolated project with no siblings
            project = Path(tmpdir) / "isolated" / "project"
            project.mkdir(parents=True)

            result = run_cli("drift", "discover", cwd=str(project))
            assert result.returncode == 0
            # May find ~/.claude or nothing
            # Just verify it doesn't crash

    def test_drift_discover_with_siblings(self):
        """Discover finds sibling reefs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two sibling projects
            proj_a = Path(tmpdir) / "project-a"
            proj_b = Path(tmpdir) / "project-b"

            proj_a.mkdir()
            proj_b.mkdir()

            # Initialize reefs
            run_cli("sprout", "constraint", "Rule A", cwd=str(proj_a))
            run_cli("sprout", "fact", "Fact B", cwd=str(proj_b))

            # Discover from project-a should find project-b
            result = run_cli("drift", "discover", cwd=str(proj_a))
            assert result.returncode == 0
            assert "project-b" in result.stdout

    def test_drift_list_default_scope(self):
        """List shows only 'always' scope by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_a = Path(tmpdir) / "project-a"
            proj_b = Path(tmpdir) / "project-b"
            proj_a.mkdir()
            proj_b.mkdir()

            # Create constraint (always scope) in project-b
            run_cli("sprout", "constraint", "Global rule", cwd=str(proj_b))
            # Create thread (project scope) in project-b
            run_cli("sprout", "thread", "Local work", cwd=str(proj_b))

            # List from project-a should only show constraint
            result = run_cli("drift", "list", cwd=str(proj_a))
            assert result.returncode == 0
            assert "Global rule" in result.stdout
            assert "Local work" not in result.stdout

    def test_drift_list_with_scope_filter(self):
        """List with custom scope filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_a = Path(tmpdir) / "project-a"
            proj_b = Path(tmpdir) / "project-b"
            proj_a.mkdir()
            proj_b.mkdir()

            run_cli("sprout", "constraint", "Global rule", cwd=str(proj_b))
            run_cli("sprout", "thread", "Local work", cwd=str(proj_b))

            # List with project scope included
            result = run_cli("drift", "list", "--scope", "always,project", cwd=str(proj_a))
            assert result.returncode == 0
            assert "Global rule" in result.stdout
            assert "Local work" in result.stdout

    def test_drift_pull_copies_polip(self):
        """Pull copies a polip from another reef."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_a = Path(tmpdir) / "project-a"
            proj_b = Path(tmpdir) / "project-b"
            proj_a.mkdir()
            proj_b.mkdir()

            # Create constraint in project-b
            run_cli("sprout", "constraint", "Shared rule", cwd=str(proj_b))

            # Pull from project-a
            result = run_cli("drift", "pull", "project-b/bedrock/shared-rule", cwd=str(proj_a))
            assert result.returncode == 0
            assert "Pulled" in result.stdout

            # Verify polip exists locally
            assert (Path(proj_a) / ".reef" / "bedrock" / "shared-rule.rock").exists()

    def test_drift_pull_not_found(self):
        """Pull fails gracefully for missing polip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("drift", "pull", "nonexistent/polip", cwd=tmpdir)
            assert result.returncode != 0
            assert "not found" in result.stderr.lower()

    def test_drift_config_show(self):
        """Config shows current drift settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("drift", "config", cwd=tmpdir)
            assert result.returncode == 0
            assert "include_global" in result.stdout
            assert "include_siblings" in result.stdout
            assert "scope_filter" in result.stdout

    def test_drift_config_add_path(self):
        """Config can add additional paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            extra_path = Path(tmpdir) / "extra-project"
            extra_path.mkdir()

            result = run_cli("drift", "config", "--add-path", str(extra_path), cwd=tmpdir)
            assert result.returncode == 0
            assert "Added" in result.stdout

            # Verify in config
            config_result = run_cli("drift", "config", cwd=tmpdir)
            assert str(extra_path) in config_result.stdout

    def test_drift_config_remove_path(self):
        """Config can remove paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            extra_path = Path(tmpdir) / "extra-project"
            extra_path.mkdir()

            # Add then remove
            run_cli("drift", "config", "--add-path", str(extra_path), cwd=tmpdir)
            result = run_cli("drift", "config", "--remove-path", str(extra_path), cwd=tmpdir)
            assert result.returncode == 0
            assert "Removed" in result.stdout

    def test_hook_surface_with_drift(self):
        """Hook surface includes drift polips when --drift flag used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_a = Path(tmpdir) / "project-a"
            proj_b = Path(tmpdir) / "project-b"
            proj_a.mkdir()
            proj_b.mkdir()

            # Create constraint in project-b
            run_cli("sprout", "constraint", "Cross-project rule", cwd=str(proj_b))

            # Create local polip in project-a
            run_cli("sprout", "thread", "Local work", cwd=str(proj_a))

            # Surface with drift should include both
            result = run_cli("hook", "surface", "--drift", cwd=str(proj_a))
            assert result.returncode == 0
            assert "Local work" in result.stdout
            assert "Cross-project rule" in result.stdout
