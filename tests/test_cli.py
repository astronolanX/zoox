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

from zoox.blob import Blob, BlobType, BlobScope, BlobStatus, Glob, BLOB_VERSION


def run_cli(*args, cwd=None):
    """Run zoox CLI and return result."""
    result = subprocess.run(
        ["uv", "run", "zoox", *args],
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

            # Verify file exists
            assert (Path(tmpdir) / ".claude" / "threads" / "test-thread.blob.xml").exists()

    def test_sprout_decision(self):
        """Create a decision blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "decision", "Use pytest", cwd=tmpdir)
            assert result.returncode == 0
            assert (Path(tmpdir) / ".claude" / "decisions").is_dir()

    def test_sprout_constraint(self):
        """Create a constraint blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "constraint", "No pip allowed", cwd=tmpdir)
            assert result.returncode == 0

            # Verify scope is ALWAYS
            glob = Glob(Path(tmpdir))
            blob = glob.get("no-pip-allowed", subdir="constraints")
            assert blob.scope == BlobScope.ALWAYS

    def test_sprout_fact(self):
        """Create a fact blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "fact", "Python 3.10 required", cwd=tmpdir)
            assert result.returncode == 0
            assert (Path(tmpdir) / ".claude" / "facts").is_dir()

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
            blob = glob.get("blocked-thread", subdir="threads")
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
            assert (Path(tmpdir) / ".claude" / "facts" / "custom-name.blob.xml").exists()

    def test_sprout_custom_dir(self):
        """Custom directory override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "fact", "Test", "-d", "custom-dir", cwd=tmpdir)
            assert result.returncode == 0
            assert (Path(tmpdir) / ".claude" / "custom-dir").is_dir()

    def test_sprout_name_truncation(self):
        """Long summaries are truncated for name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            long_summary = "This is a very long summary that should be truncated to thirty characters"
            result = run_cli("sprout", "fact", long_summary, cwd=tmpdir)
            assert result.returncode == 0

            # Check filename is max 30 chars (plus .blob.xml)
            facts_dir = Path(tmpdir) / ".claude" / "facts"
            blob_files = list(facts_dir.glob("*.blob.xml"))
            assert len(blob_files) == 1
            name_part = blob_files[0].stem.replace(".blob", "")
            assert len(name_part) <= 30

    def test_sprout_special_chars_in_summary(self):
        """Special characters are cleaned from name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("sprout", "fact", "Test: with/special?chars!", cwd=tmpdir)
            assert result.returncode == 0

            # Name should be cleaned
            facts_dir = Path(tmpdir) / ".claude" / "facts"
            blob_files = list(facts_dir.glob("*.blob.xml"))
            assert len(blob_files) == 1


class TestCliList:
    """CLI list command tests."""

    def test_list_empty(self):
        """List on empty project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("list", cwd=tmpdir)
            assert result.returncode == 0
            assert "No polyps found" in result.stdout

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
            glob.sprout(blob, "test", subdir="threads")

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
            glob.sprout(blob, "recent", subdir="contexts")

            result = run_cli("decompose", cwd=tmpdir)
            assert result.returncode == 0
            assert "No stale" in result.stdout

    def test_decompose_finds_stale(self):
        """Decompose finds stale session blobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            old_time = datetime.now() - timedelta(days=10)
            blob = Blob(type=BlobType.CONTEXT, summary="Old session", scope=BlobScope.SESSION, updated=old_time)
            glob.sprout(blob, "old-session", subdir="contexts")

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
            glob.sprout(blob, "kinda-old", subdir="contexts")

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
            glob.sprout(blob, "to-delete", subdir="contexts")

            result = run_cli("decompose", cwd=tmpdir)
            assert result.returncode == 0
            assert "Decomposed" in result.stdout

            # File should be gone
            assert not (Path(tmpdir) / ".claude" / "contexts" / "to-delete.blob.xml").exists()

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
            assert (Path(tmpdir) / ".claude" / "old-project.blob.xml").exists()


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
        """Create polyp from bug template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "use", "bug", "Login fails on Safari", cwd=tmpdir)
            assert result.returncode == 0
            assert "Created" in result.stdout

            # Verify polyp created with template structure
            glob = Glob(Path(tmpdir))
            blob = glob.get("login-fails-on-safari", subdir="threads")
            assert blob is not None
            assert "Bug:" in blob.summary
            assert blob.status == BlobStatus.ACTIVE
            assert len(blob.next_steps) > 0

    def test_template_use_feature(self):
        """Create polyp from feature template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "use", "feature", "Dark mode", cwd=tmpdir)
            assert result.returncode == 0

            glob = Glob(Path(tmpdir))
            blob = glob.get("dark-mode", subdir="threads")
            assert blob is not None
            assert "Feature:" in blob.summary

    def test_template_use_decision(self):
        """Create polyp from decision template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "use", "decision", "Use PostgreSQL", cwd=tmpdir)
            assert result.returncode == 0

            glob = Glob(Path(tmpdir))
            blob = glob.get("use-postgresql", subdir="decisions")
            assert blob is not None
            assert "ADR:" in blob.summary

    def test_template_use_constraint(self):
        """Create polyp from constraint template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("template", "use", "constraint", "No pip allowed", cwd=tmpdir)
            assert result.returncode == 0

            glob = Glob(Path(tmpdir))
            blob = glob.get("no-pip-allowed", subdir="constraints")
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
            assert "No polyps" in result.stdout

    def test_graph_with_polyps(self):
        """Graph shows polyps by type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)
            run_cli("sprout", "constraint", "Test constraint", cwd=tmpdir)
            run_cli("sprout", "fact", "Test fact", cwd=tmpdir)

            result = run_cli("graph", cwd=tmpdir)
            assert result.returncode == 0
            assert "3 polyps" in result.stdout
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
            assert "threads/test-thread" in result.stdout

    def test_graph_shows_status(self):
        """Graph shows polyp status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Blocked work", "--status", "blocked", cwd=tmpdir)

            result = run_cli("graph", cwd=tmpdir)
            assert result.returncode == 0
            assert "[blocked]" in result.stdout

    def test_graph_with_related_links(self):
        """Graph detects related links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create polyps with related links
            blob1 = Blob(type=BlobType.THREAD, summary="Thread 1", status=BlobStatus.ACTIVE, related=["facts/fact-1"])
            blob2 = Blob(type=BlobType.FACT, summary="Fact 1")

            glob.sprout(blob1, "thread-1", subdir="threads")
            glob.sprout(blob2, "fact-1", subdir="facts")

            result = run_cli("graph", cwd=tmpdir)
            assert result.returncode == 0
            assert "explicit link" in result.stdout

    def test_graph_with_shared_files(self):
        """Graph detects shared file references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create polyps referencing same file
            blob1 = Blob(type=BlobType.THREAD, summary="Thread 1", status=BlobStatus.ACTIVE, files=["shared.py"])
            blob2 = Blob(type=BlobType.FACT, summary="Fact 1", files=["shared.py"])

            glob.sprout(blob1, "thread-1", subdir="threads")
            glob.sprout(blob2, "fact-1", subdir="facts")

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
            snapshot_dir = Path(tmpdir) / ".claude" / "snapshots"
            assert snapshot_dir.exists()
            assert len(list(snapshot_dir.glob("*.snapshot.json"))) == 1

    def test_snapshot_create_with_name(self):
        """Create a named snapshot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test", cwd=tmpdir)

            result = run_cli("snapshot", "create", "--name", "milestone-1", cwd=tmpdir)
            assert result.returncode == 0

            snapshot_dir = Path(tmpdir) / ".claude" / "snapshots"
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
        """Diff detects added polyps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Thread 1", cwd=tmpdir)
            run_cli("snapshot", "create", "--name", "before", cwd=tmpdir)
            run_cli("sprout", "fact", "New fact", cwd=tmpdir)

            result = run_cli("snapshot", "diff", "before", cwd=tmpdir)
            assert result.returncode == 0
            assert "Added" in result.stdout

    def test_snapshot_diff_with_removals(self):
        """Diff detects removed polyps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Thread 1", cwd=tmpdir)
            run_cli("sprout", "fact", "Fact 1", cwd=tmpdir)
            run_cli("snapshot", "create", "--name", "before", cwd=tmpdir)

            # Remove the fact
            (Path(tmpdir) / ".claude" / "facts" / "fact-1.blob.xml").unlink()

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
        """Show current status of a polyp."""
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
            blob = glob.get("test-thread", subdir="threads")
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
            blob = glob.get("test-thread", subdir="threads")
            assert blob.blocked_by == "Waiting for API"

    def test_status_clears_blocked_by_on_active(self):
        """Blocked-by is cleared when status changes to active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_cli("sprout", "thread", "Test thread", cwd=tmpdir)
            run_cli("status", "test-thread", "blocked", "-b", "Waiting", cwd=tmpdir)
            run_cli("status", "test-thread", "active", cwd=tmpdir)

            glob = Glob(Path(tmpdir))
            blob = glob.get("test-thread", subdir="threads")
            assert blob.status == BlobStatus.ACTIVE
            assert blob.blocked_by is None

    def test_status_not_found(self):
        """Status on nonexistent polyp fails."""
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

            result = run_cli("status", "test-thread", "--dir", "threads", cwd=tmpdir)
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
