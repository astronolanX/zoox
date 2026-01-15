"""
Tests for reef trench harness - parallel Claude agents in git worktrees.

Phase 7 implementation:
- test_spawn_creates_worktree
- test_spawn_creates_branch
- test_status_returns_trenches
- test_run_tests_updates_status
- test_merge_requires_ready_status
- test_abort_removes_worktree
- test_prune_stale_trenches
- test_cleanup_all
"""

import pytest
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
import os

from reef.trench import TrenchHarness, TrenchStatus, TrenchInfo, TrenchResult


class TestTrenchImports:
    """Tests for module imports."""

    def test_import_harness(self):
        """Verify TrenchHarness imports correctly."""
        assert TrenchHarness is not None

    def test_import_status_enum(self):
        """Verify TrenchStatus enum imports correctly."""
        assert TrenchStatus is not None
        assert TrenchStatus.SPAWNING.value == "spawning"
        assert TrenchStatus.RUNNING.value == "running"
        assert TrenchStatus.TESTING.value == "testing"
        assert TrenchStatus.READY.value == "ready"
        assert TrenchStatus.FAILED.value == "failed"
        assert TrenchStatus.MERGED.value == "merged"
        assert TrenchStatus.ABORTED.value == "aborted"

    def test_import_info_dataclass(self):
        """Verify TrenchInfo dataclass imports correctly."""
        assert TrenchInfo is not None

    def test_import_result_dataclass(self):
        """Verify TrenchResult dataclass imports correctly."""
        assert TrenchResult is not None


class TestTrenchInfoDataclass:
    """Tests for TrenchInfo dataclass."""

    def test_create_trench_info(self):
        """Verify TrenchInfo can be created with required fields."""
        now = datetime.now()
        info = TrenchInfo(
            name="test-feature",
            branch="trench/test-feature",
            worktree_path=Path("/tmp/test"),
            status=TrenchStatus.RUNNING,
            created=now,
            last_updated=now,
        )
        assert info.name == "test-feature"
        assert info.branch == "trench/test-feature"
        assert info.status == TrenchStatus.RUNNING

    def test_trench_info_to_dict(self):
        """Verify TrenchInfo serializes to dict correctly."""
        now = datetime.now()
        info = TrenchInfo(
            name="test",
            branch="trench/test",
            worktree_path=Path("/tmp/test"),
            status=TrenchStatus.READY,
            created=now,
            last_updated=now,
            test_output="All tests passed",
        )
        data = info.to_dict()
        assert data["name"] == "test"
        assert data["status"] == "ready"
        assert data["test_output"] == "All tests passed"

    def test_trench_info_optional_fields(self):
        """Verify optional fields have correct defaults."""
        now = datetime.now()
        info = TrenchInfo(
            name="test",
            branch="trench/test",
            worktree_path=Path("/tmp/test"),
            status=TrenchStatus.SPAWNING,
            created=now,
            last_updated=now,
        )
        assert info.test_output is None
        assert info.error is None
        assert info.pid is None


class TestTrenchResultDataclass:
    """Tests for TrenchResult dataclass."""

    def test_create_success_result(self):
        """Verify success result can be created."""
        result = TrenchResult(
            success=True,
            message="Operation completed",
        )
        assert result.success is True
        assert result.message == "Operation completed"
        assert result.trench is None
        assert result.error is None

    def test_create_failure_result(self):
        """Verify failure result can be created with error."""
        result = TrenchResult(
            success=False,
            message="Operation failed",
            error="Git command failed",
        )
        assert result.success is False
        assert result.error == "Git command failed"


class TestTrenchHarnessInstantiation:
    """Tests for TrenchHarness instantiation."""

    def test_instantiation_default(self):
        """Verify harness can be instantiated with defaults."""
        harness = TrenchHarness()
        assert harness is not None
        assert harness.project_dir == Path.cwd()

    def test_instantiation_custom_path(self):
        """Verify harness can be instantiated with custom path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            harness = TrenchHarness(Path(tmpdir))
            assert harness.project_dir == Path(tmpdir)

    def test_constants(self):
        """Verify harness constants are set correctly."""
        harness = TrenchHarness()
        assert harness.TRENCH_DIR == ".reef-trenches"
        assert harness.STATUS_FILE == ".reef-trench.json"
        assert harness.BRANCH_PREFIX == "trench/"


@pytest.fixture
def git_repo():
    """Create a temporary git repository for testing."""
    tmpdir = tempfile.mkdtemp()
    original_cwd = os.getcwd()

    try:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )

        # Create initial commit
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("test content")
        subprocess.run(["git", "add", "test.txt"], cwd=tmpdir, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )

        yield Path(tmpdir)
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestTrenchHarnessGitOperations:
    """Tests for TrenchHarness git operations (requires real git repo)."""

    def test_run_git_success(self, git_repo):
        """Verify _run_git returns success for valid commands."""
        harness = TrenchHarness(git_repo)
        ok, output = harness._run_git("status")
        assert ok is True

    def test_run_git_failure(self, git_repo):
        """Verify _run_git returns failure for invalid commands."""
        harness = TrenchHarness(git_repo)
        ok, output = harness._run_git("invalid-command")
        assert ok is False

    def test_get_branch_name(self, git_repo):
        """Verify branch name generation."""
        harness = TrenchHarness(git_repo)
        branch = harness._get_branch_name("feature-test")
        assert branch == "trench/feature-test"

    def test_get_trench_path(self, git_repo):
        """Verify trench path generation."""
        harness = TrenchHarness(git_repo)
        path = harness._get_trench_path("feature-test")
        assert path == git_repo / ".reef-trenches" / "feature-test"


class TestTrenchSpawn:
    """Tests for spawning trenches."""

    def test_spawn_creates_worktree(self, git_repo):
        """Verify spawn creates a git worktree."""
        harness = TrenchHarness(git_repo)
        result = harness.spawn("test-feature")

        assert result.success is True
        assert result.trench is not None
        assert result.trench.name == "test-feature"

        # Verify worktree exists
        worktree_path = git_repo / ".reef-trenches" / "test-feature"
        assert worktree_path.exists()
        assert worktree_path.is_dir()

        # Cleanup
        harness.abort("test-feature", force=True)

    def test_spawn_creates_branch(self, git_repo):
        """Verify spawn creates the correct branch."""
        harness = TrenchHarness(git_repo)
        result = harness.spawn("test-branch")

        assert result.success is True
        assert result.trench.branch == "trench/test-branch"

        # Verify branch exists
        ok, output = harness._run_git("branch", "--list", "trench/test-branch")
        assert "trench/test-branch" in output

        # Cleanup
        harness.abort("test-branch", force=True)

    def test_spawn_duplicate_fails(self, git_repo):
        """Verify spawning duplicate trench fails."""
        harness = TrenchHarness(git_repo)

        # First spawn succeeds
        result1 = harness.spawn("duplicate-test")
        assert result1.success is True

        # Second spawn fails
        result2 = harness.spawn("duplicate-test")
        assert result2.success is False
        assert "already exists" in result2.message

        # Cleanup
        harness.abort("duplicate-test", force=True)

    def test_spawn_with_base_branch(self, git_repo):
        """Verify spawn can use custom base branch."""
        harness = TrenchHarness(git_repo)

        # Create a feature branch first
        harness._run_git("checkout", "-b", "feature-base")
        test_file = git_repo / "feature.txt"
        test_file.write_text("feature content")
        harness._run_git("add", "feature.txt")
        harness._run_git("commit", "-m", "Feature commit")
        harness._run_git("checkout", "master")

        # Spawn from feature-base
        result = harness.spawn("from-feature", base_branch="feature-base")
        assert result.success is True

        # Verify the worktree has the feature file
        worktree_path = result.trench.worktree_path
        assert (worktree_path / "feature.txt").exists()

        # Cleanup
        harness.abort("from-feature", force=True)


class TestTrenchStatus:
    """Tests for trench status checking."""

    def test_status_empty(self, git_repo):
        """Verify status returns empty list when no trenches."""
        harness = TrenchHarness(git_repo)
        trenches = harness.status()
        assert trenches == []

    def test_status_returns_trenches(self, git_repo):
        """Verify status returns active trenches."""
        harness = TrenchHarness(git_repo)

        # Spawn a trench
        harness.spawn("status-test")

        # Check status
        trenches = harness.status()
        assert len(trenches) == 1
        assert trenches[0].name == "status-test"
        assert trenches[0].status == TrenchStatus.RUNNING

        # Cleanup
        harness.abort("status-test", force=True)

    def test_status_specific_trench(self, git_repo):
        """Verify status can query specific trench."""
        harness = TrenchHarness(git_repo)

        harness.spawn("specific-test")
        trenches = harness.status("specific-test")

        assert len(trenches) == 1
        assert trenches[0].name == "specific-test"

        # Query non-existent
        trenches = harness.status("non-existent")
        assert len(trenches) == 0

        # Cleanup
        harness.abort("specific-test", force=True)


class TestTrenchAbort:
    """Tests for aborting trenches."""

    def test_abort_removes_worktree(self, git_repo):
        """Verify abort removes the worktree."""
        harness = TrenchHarness(git_repo)

        harness.spawn("abort-test")
        worktree_path = git_repo / ".reef-trenches" / "abort-test"
        assert worktree_path.exists()

        result = harness.abort("abort-test", force=True)
        assert result.success is True
        assert not worktree_path.exists()

    def test_abort_removes_branch(self, git_repo):
        """Verify abort removes the branch."""
        harness = TrenchHarness(git_repo)

        harness.spawn("branch-test")
        result = harness.abort("branch-test", force=True)

        assert result.success is True
        ok, output = harness._run_git("branch", "--list", "trench/branch-test")
        assert "trench/branch-test" not in output

    def test_abort_nonexistent(self, git_repo):
        """Verify aborting non-existent trench fails gracefully."""
        harness = TrenchHarness(git_repo)
        result = harness.abort("nonexistent")
        assert result.success is False


class TestTrenchPrune:
    """Tests for pruning stale trenches."""

    def test_prune_stale_dry_run(self, git_repo):
        """Verify prune dry run identifies stale trenches."""
        harness = TrenchHarness(git_repo)

        # Spawn and manually age the trench
        harness.spawn("stale-test")
        status_file = git_repo / ".reef-trenches" / "stale-test" / ".reef-trench.json"
        data = json.loads(status_file.read_text())

        # Set last_updated to 10 days ago
        old_time = (datetime.now() - timedelta(days=10)).isoformat()
        data["last_updated"] = old_time
        data["status"] = "failed"  # Not running
        status_file.write_text(json.dumps(data))

        # Prune with dry_run
        results = harness.prune_stale(max_age_days=7, dry_run=True)
        assert len(results) == 1
        assert "Would prune" in results[0].message

        # Worktree should still exist
        assert (git_repo / ".reef-trenches" / "stale-test").exists()

        # Cleanup
        harness.abort("stale-test", force=True)

    def test_prune_stale_execute(self, git_repo):
        """Verify prune execute removes stale trenches."""
        harness = TrenchHarness(git_repo)

        # Spawn and manually age the trench
        harness.spawn("prune-test")
        status_file = git_repo / ".reef-trenches" / "prune-test" / ".reef-trench.json"
        data = json.loads(status_file.read_text())

        # Set last_updated to 10 days ago
        old_time = (datetime.now() - timedelta(days=10)).isoformat()
        data["last_updated"] = old_time
        data["status"] = "failed"
        status_file.write_text(json.dumps(data))

        # Prune with execute
        results = harness.prune_stale(max_age_days=7, dry_run=False)
        assert len(results) == 1
        assert "Pruned" in results[0].message

        # Worktree should be removed
        assert not (git_repo / ".reef-trenches" / "prune-test").exists()

    def test_prune_skips_recent(self, git_repo):
        """Verify prune skips recently updated trenches."""
        harness = TrenchHarness(git_repo)

        harness.spawn("recent-test")

        # Prune with dry_run - should find nothing
        results = harness.prune_stale(max_age_days=7, dry_run=True)
        assert len(results) == 0

        # Cleanup
        harness.abort("recent-test", force=True)


class TestTrenchCleanup:
    """Tests for cleanup_all."""

    def test_cleanup_all_removes_trenches(self, git_repo):
        """Verify cleanup_all removes all trenches."""
        harness = TrenchHarness(git_repo)

        # Spawn multiple trenches
        harness.spawn("cleanup-1")
        harness.spawn("cleanup-2")

        assert len(harness.status()) == 2

        # Cleanup all
        results = harness.cleanup_all(force=True)

        # Should have results for each trench + orphan prune
        assert len(results) >= 2

        # All trenches should be gone
        assert len(harness.status()) == 0


class TestTrenchListWorktrees:
    """Tests for listing git worktrees."""

    def test_list_worktrees(self, git_repo):
        """Verify list_worktrees returns worktree info."""
        harness = TrenchHarness(git_repo)

        # Initially just the main worktree
        worktrees = harness.list_worktrees()
        assert len(worktrees) >= 1

        # Spawn a trench
        harness.spawn("list-test")

        # Should have 2 worktrees now
        worktrees = harness.list_worktrees()
        assert len(worktrees) >= 2

        # Cleanup
        harness.abort("list-test", force=True)


class TestTrenchSignalReady:
    """Tests for signal_ready helper."""

    def test_signal_ready_no_status_file(self):
        """Verify signal_ready returns False when not in a trench."""
        harness = TrenchHarness()
        # This is called from within a trench - returns False if not in one
        assert harness.signal_ready() is False


class TestTrenchGetClaudeCommand:
    """Tests for get_claude_command helper."""

    def test_get_claude_command(self, git_repo):
        """Verify get_claude_command generates correct command."""
        harness = TrenchHarness(git_repo)

        harness.spawn("cmd-test")
        cmd = harness.get_claude_command("cmd-test")

        assert cmd is not None
        assert "cd" in cmd
        assert "cmd-test" in cmd
        assert "claude" in cmd

        # Cleanup
        harness.abort("cmd-test", force=True)

    def test_get_claude_command_with_task(self, git_repo):
        """Verify get_claude_command includes task when provided."""
        harness = TrenchHarness(git_repo)

        harness.spawn("task-test")
        cmd = harness.get_claude_command("task-test", task="implement feature X")

        assert cmd is not None
        assert "-p" in cmd
        assert "implement feature X" in cmd

        # Cleanup
        harness.abort("task-test", force=True)

    def test_get_claude_command_nonexistent(self, git_repo):
        """Verify get_claude_command returns None for non-existent trench."""
        harness = TrenchHarness(git_repo)
        cmd = harness.get_claude_command("nonexistent")
        assert cmd is None
