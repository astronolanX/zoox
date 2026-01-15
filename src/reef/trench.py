"""
Trench harness - parallel Claude agents in git worktrees.

Enables multiple Claude agents to work on isolated features simultaneously,
each in its own git worktree with independent testing before upstream merge.

Architecture:
    Main worktree (orchestrator)
    ├── git worktree create reef-trench-feature-x
    │   └── Claude session A (feature-x implementation)
    │       └── Tests run locally before signaling merge
    ├── git worktree create reef-trench-feature-y
    │   └── Claude session B (feature-y implementation)
    │       └── Tests run locally before signaling merge
    └── Orchestrator merges when children report green
"""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional


class TrenchStatus(Enum):
    """Status of a trench (child worktree session)."""
    SPAWNING = "spawning"      # Worktree being created
    RUNNING = "running"        # Claude session active
    TESTING = "testing"        # Running tests before merge
    READY = "ready"            # Tests passed, ready to merge
    FAILED = "failed"          # Tests failed or session errored
    MERGED = "merged"          # Successfully merged to main
    ABORTED = "aborted"        # Manually cancelled


class TrenchComplexity(Enum):
    """Task complexity for model routing."""
    SIMPLE = "simple"          # Quick fixes, small changes → haiku
    MODERATE = "moderate"      # Feature implementation → sonnet
    COMPLEX = "complex"        # Architecture, multi-file refactors → opus


# Model routing based on complexity
TRENCH_MODEL_ROUTING = {
    TrenchComplexity.SIMPLE: "haiku",
    TrenchComplexity.MODERATE: "sonnet",
    TrenchComplexity.COMPLEX: "opus",
}

# Keywords for auto-detecting complexity from task description
COMPLEXITY_KEYWORDS = {
    TrenchComplexity.SIMPLE: [
        "fix", "typo", "rename", "update", "tweak", "small", "minor",
        "simple", "quick", "easy", "single", "one", "comment", "doc",
    ],
    TrenchComplexity.COMPLEX: [
        "refactor", "architect", "redesign", "rewrite", "multi-file",
        "infrastructure", "system", "complex", "major", "overhaul",
        "integration", "migrate", "framework", "engine",
    ],
}


@dataclass
class TrenchInfo:
    """Information about a single trench."""
    name: str
    branch: str
    worktree_path: Path
    status: TrenchStatus
    created: datetime
    last_updated: datetime
    test_output: Optional[str] = None
    error: Optional[str] = None
    pid: Optional[int] = None
    task: Optional[str] = None
    model: Optional[str] = None
    complexity: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "branch": self.branch,
            "worktree_path": str(self.worktree_path),
            "status": self.status.value,
            "created": self.created.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "test_output": self.test_output,
            "error": self.error,
            "pid": self.pid,
            "task": self.task,
            "model": self.model,
            "complexity": self.complexity,
        }


@dataclass
class TrenchResult:
    """Result of a trench operation."""
    success: bool
    message: str
    trench: Optional[TrenchInfo] = None
    error: Optional[str] = None


class TrenchHarness:
    """
    Manages parallel Claude agents in isolated git worktrees.

    Each trench is an isolated git worktree where a Claude agent can work
    independently. The orchestrator (parent session) spawns trenches,
    monitors their status, and merges when tests pass.

    Child sessions:
    - Inherit full reef codebase in worktree
    - Have .claude/ polips (scoped to project + session)
    - Log progress to .reef-trench.json
    - Run tests before signaling ready
    """

    TRENCH_DIR = ".reef-trenches"
    STATUS_FILE = ".reef-trench.json"
    BRANCH_PREFIX = "trench/"

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or Path.cwd()
        self.trenches_dir = self.project_dir / self.TRENCH_DIR

    def _run_git(self, *args: str, cwd: Optional[Path] = None) -> tuple[bool, str]:
        """Run a git command and return (success, output)."""
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=cwd or self.project_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def _ensure_trenches_dir(self) -> Path:
        """Ensure the trenches directory exists."""
        self.trenches_dir.mkdir(parents=True, exist_ok=True)
        return self.trenches_dir

    def _get_trench_path(self, name: str) -> Path:
        """Get the worktree path for a trench."""
        return self.trenches_dir / name

    def _get_branch_name(self, name: str) -> str:
        """Get the git branch name for a trench."""
        return f"{self.BRANCH_PREFIX}{name}"

    def _read_trench_status(self, name: str) -> Optional[TrenchInfo]:
        """Read the status file from a trench worktree."""
        trench_path = self._get_trench_path(name)
        status_file = trench_path / self.STATUS_FILE

        if not status_file.exists():
            return None

        try:
            data = json.loads(status_file.read_text())
            return TrenchInfo(
                name=data["name"],
                branch=data["branch"],
                worktree_path=Path(data["worktree_path"]),
                status=TrenchStatus(data["status"]),
                created=datetime.fromisoformat(data["created"]),
                last_updated=datetime.fromisoformat(data["last_updated"]),
                test_output=data.get("test_output"),
                error=data.get("error"),
                pid=data.get("pid"),
                task=data.get("task"),
                model=data.get("model"),
                complexity=data.get("complexity"),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def _write_trench_status(self, info: TrenchInfo) -> None:
        """Write the status file to a trench worktree."""
        status_file = info.worktree_path / self.STATUS_FILE
        info.last_updated = datetime.now()
        status_file.write_text(json.dumps(info.to_dict(), indent=2))

    def spawn(self, name: str, base_branch: Optional[str] = None) -> TrenchResult:
        """
        Spawn a new trench (worktree) for a Claude agent.

        Args:
            name: Unique name for this trench (e.g., "feature-auth")
            base_branch: Branch to base the worktree on (default: current branch)

        Returns:
            TrenchResult with success status and trench info
        """
        trench_path = self._get_trench_path(name)
        branch = self._get_branch_name(name)

        # Check if trench already exists
        if trench_path.exists():
            existing = self._read_trench_status(name)
            if existing:
                return TrenchResult(
                    success=False,
                    message=f"Trench '{name}' already exists",
                    trench=existing,
                    error="Trench already exists. Use 'reef trench abort' to remove it first.",
                )

        # Get current branch as base if not specified
        if not base_branch:
            ok, output = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
            if not ok:
                return TrenchResult(
                    success=False,
                    message="Failed to get current branch",
                    error=output,
                )
            base_branch = output

        # Ensure trenches directory exists
        self._ensure_trenches_dir()

        # Create new branch from base
        ok, output = self._run_git("branch", branch, base_branch)
        if not ok and "already exists" not in output:
            return TrenchResult(
                success=False,
                message=f"Failed to create branch '{branch}'",
                error=output,
            )

        # Create worktree
        ok, output = self._run_git("worktree", "add", str(trench_path), branch)
        if not ok:
            # Clean up branch if worktree creation failed
            self._run_git("branch", "-D", branch)
            return TrenchResult(
                success=False,
                message=f"Failed to create worktree at '{trench_path}'",
                error=output,
            )

        # Create initial status file
        now = datetime.now()
        info = TrenchInfo(
            name=name,
            branch=branch,
            worktree_path=trench_path,
            status=TrenchStatus.SPAWNING,
            created=now,
            last_updated=now,
        )
        self._write_trench_status(info)

        # Update status to running
        info.status = TrenchStatus.RUNNING
        self._write_trench_status(info)

        return TrenchResult(
            success=True,
            message=f"Spawned trench '{name}' at {trench_path}",
            trench=info,
        )

    def detect_complexity(self, task: str) -> TrenchComplexity:
        """
        Auto-detect task complexity from description.

        Args:
            task: Task description

        Returns:
            TrenchComplexity based on keyword matching
        """
        task_lower = task.lower()

        # Check for complex keywords first (higher priority)
        for keyword in COMPLEXITY_KEYWORDS[TrenchComplexity.COMPLEX]:
            if keyword in task_lower:
                return TrenchComplexity.COMPLEX

        # Check for simple keywords
        for keyword in COMPLEXITY_KEYWORDS[TrenchComplexity.SIMPLE]:
            if keyword in task_lower:
                return TrenchComplexity.SIMPLE

        # Default to moderate
        return TrenchComplexity.MODERATE

    def spawn_session(
        self,
        name: str,
        task: str,
        model: Optional[str] = None,
        complexity: Optional[TrenchComplexity] = None,
        base_branch: Optional[str] = None,
    ) -> TrenchResult:
        """
        Spawn a trench AND launch a Claude session in it.

        This is the full parallel agent workflow:
        1. Create isolated worktree
        2. Detect complexity (or use provided)
        3. Select model based on complexity (or use provided)
        4. Launch `claude -p "<task>"` in background
        5. Track PID for monitoring

        Args:
            name: Unique name for this trench
            task: Task description for the Claude session
            model: Override model selection (haiku, sonnet, opus)
            complexity: Override complexity detection
            base_branch: Branch to base the worktree on

        Returns:
            TrenchResult with session info including PID
        """
        # First, spawn the worktree
        result = self.spawn(name, base_branch=base_branch)
        if not result.success:
            return result

        info = result.trench

        # Detect or use provided complexity
        if complexity is None:
            complexity = self.detect_complexity(task)

        # Select model based on complexity (or use override)
        if model is None:
            model = TRENCH_MODEL_ROUTING[complexity]

        # Update info with task details
        info.task = task
        info.model = model
        info.complexity = complexity.value

        # Build the claude command
        # Use -p for print mode (non-interactive, runs task and exits)
        # Use --model to select the model
        claude_cmd = [
            "claude",
            "-p", task,
            "--model", model,
        ]

        # Launch in background
        try:
            # Create a log file for the session output
            log_file = info.worktree_path / ".claude-session.log"

            with open(log_file, "w") as log:
                process = subprocess.Popen(
                    claude_cmd,
                    cwd=info.worktree_path,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,  # Detach from parent
                )

            info.pid = process.pid
            info.status = TrenchStatus.RUNNING
            self._write_trench_status(info)

            return TrenchResult(
                success=True,
                message=f"Spawned trench '{name}' with {model} model (PID: {process.pid})",
                trench=info,
            )

        except FileNotFoundError:
            info.status = TrenchStatus.FAILED
            info.error = "Claude CLI not found. Is it installed and in PATH?"
            self._write_trench_status(info)
            return TrenchResult(
                success=False,
                message=f"Failed to launch Claude session in trench '{name}'",
                trench=info,
                error=info.error,
            )
        except Exception as e:
            info.status = TrenchStatus.FAILED
            info.error = str(e)
            self._write_trench_status(info)
            return TrenchResult(
                success=False,
                message=f"Failed to launch Claude session in trench '{name}'",
                trench=info,
                error=str(e),
            )

    def is_session_alive(self, name: str) -> bool:
        """
        Check if a trench's Claude session is still running.

        Args:
            name: Trench name

        Returns:
            True if the session process is still alive
        """
        info = self._read_trench_status(name)
        if not info or not info.pid:
            return False

        try:
            os.kill(info.pid, 0)  # Signal 0 = check if process exists
            return True
        except OSError:
            return False

    def get_session_output(self, name: str, tail_lines: int = 50) -> Optional[str]:
        """
        Get the output from a trench's Claude session.

        Args:
            name: Trench name
            tail_lines: Number of lines to return from end

        Returns:
            Session output or None if not found
        """
        info = self._read_trench_status(name)
        if not info:
            return None

        log_file = info.worktree_path / ".claude-session.log"
        if not log_file.exists():
            return None

        try:
            lines = log_file.read_text().strip().split("\n")
            return "\n".join(lines[-tail_lines:])
        except Exception:
            return None

    def status(self, name: Optional[str] = None) -> list[TrenchInfo]:
        """
        Get status of trenches.

        Args:
            name: Specific trench name, or None for all trenches

        Returns:
            List of TrenchInfo for active trenches
        """
        if name:
            info = self._read_trench_status(name)
            return [info] if info else []

        if not self.trenches_dir.exists():
            return []

        trenches = []
        for entry in self.trenches_dir.iterdir():
            if entry.is_dir():
                info = self._read_trench_status(entry.name)
                if info:
                    trenches.append(info)

        return sorted(trenches, key=lambda t: t.created, reverse=True)

    def run_tests(self, name: str, test_command: str = "uv run pytest") -> TrenchResult:
        """
        Run tests in a trench worktree.

        Args:
            name: Trench name
            test_command: Test command to run (default: uv run pytest)

        Returns:
            TrenchResult with test output
        """
        info = self._read_trench_status(name)
        if not info:
            return TrenchResult(
                success=False,
                message=f"Trench '{name}' not found",
                error="Run 'reef trench status' to see active trenches",
            )

        # Update status to testing
        info.status = TrenchStatus.TESTING
        self._write_trench_status(info)

        # Run tests
        try:
            result = subprocess.run(
                test_command.split(),
                cwd=info.worktree_path,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout for tests
            )

            info.test_output = result.stdout + result.stderr

            if result.returncode == 0:
                info.status = TrenchStatus.READY
                self._write_trench_status(info)
                return TrenchResult(
                    success=True,
                    message=f"Tests passed in trench '{name}'",
                    trench=info,
                )
            else:
                info.status = TrenchStatus.FAILED
                info.error = f"Tests failed with exit code {result.returncode}"
                self._write_trench_status(info)
                return TrenchResult(
                    success=False,
                    message=f"Tests failed in trench '{name}'",
                    trench=info,
                    error=info.error,
                )

        except subprocess.TimeoutExpired:
            info.status = TrenchStatus.FAILED
            info.error = "Test command timed out after 10 minutes"
            self._write_trench_status(info)
            return TrenchResult(
                success=False,
                message=f"Tests timed out in trench '{name}'",
                trench=info,
                error=info.error,
            )
        except Exception as e:
            info.status = TrenchStatus.FAILED
            info.error = str(e)
            self._write_trench_status(info)
            return TrenchResult(
                success=False,
                message=f"Test execution failed in trench '{name}'",
                trench=info,
                error=str(e),
            )

    def merge(self, name: str, delete_branch: bool = True) -> TrenchResult:
        """
        Merge a trench branch back to the base branch.

        Args:
            name: Trench name
            delete_branch: Delete the trench branch after merge (default: True)

        Returns:
            TrenchResult with merge status
        """
        info = self._read_trench_status(name)
        if not info:
            return TrenchResult(
                success=False,
                message=f"Trench '{name}' not found",
                error="Run 'reef trench status' to see active trenches",
            )

        # Check if ready
        if info.status != TrenchStatus.READY:
            return TrenchResult(
                success=False,
                message=f"Trench '{name}' not ready for merge",
                trench=info,
                error=f"Status is '{info.status.value}'. Run tests first with 'reef trench test {name}'",
            )

        # Get the base branch (main or master)
        ok, output = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        if not ok:
            return TrenchResult(
                success=False,
                message="Failed to get current branch",
                error=output,
            )
        current_branch = output

        # Merge the trench branch
        ok, output = self._run_git("merge", info.branch, "--no-ff", "-m", f"Merge trench/{name}")
        if not ok:
            info.status = TrenchStatus.FAILED
            info.error = f"Merge conflict: {output}"
            self._write_trench_status(info)
            return TrenchResult(
                success=False,
                message=f"Merge failed for trench '{name}'",
                trench=info,
                error=output,
            )

        # Update status
        info.status = TrenchStatus.MERGED
        self._write_trench_status(info)

        # Clean up worktree and branch
        cleanup_result = self._cleanup_trench(name, delete_branch)

        return TrenchResult(
            success=True,
            message=f"Merged trench '{name}' into {current_branch}",
            trench=info,
        )

    def abort(self, name: str, force: bool = False) -> TrenchResult:
        """
        Abort and clean up a trench.

        Args:
            name: Trench name
            force: Force removal even if there are uncommitted changes

        Returns:
            TrenchResult with cleanup status
        """
        info = self._read_trench_status(name)
        if not info:
            # Trench may have partial state, try to clean up anyway
            trench_path = self._get_trench_path(name)
            branch = self._get_branch_name(name)

            if trench_path.exists() or self._branch_exists(branch):
                return self._cleanup_trench(name, delete_branch=True, force=force)

            return TrenchResult(
                success=False,
                message=f"Trench '{name}' not found",
                error="Run 'reef trench status' to see active trenches",
            )

        # Check for uncommitted changes
        if not force:
            ok, output = self._run_git("status", "--porcelain", cwd=info.worktree_path)
            if ok and output:
                return TrenchResult(
                    success=False,
                    message=f"Trench '{name}' has uncommitted changes",
                    trench=info,
                    error="Use --force to discard changes, or commit/stash them first",
                )

        # Update status
        info.status = TrenchStatus.ABORTED
        self._write_trench_status(info)

        # Clean up
        return self._cleanup_trench(name, delete_branch=True, force=force)

    def _branch_exists(self, branch: str) -> bool:
        """Check if a git branch exists."""
        ok, _ = self._run_git("rev-parse", "--verify", branch)
        return ok

    def _cleanup_trench(self, name: str, delete_branch: bool = True, force: bool = False) -> TrenchResult:
        """Remove worktree and optionally delete branch."""
        trench_path = self._get_trench_path(name)
        branch = self._get_branch_name(name)

        errors = []

        # Remove worktree
        if trench_path.exists():
            force_flag = ["--force"] if force else []
            ok, output = self._run_git("worktree", "remove", str(trench_path), *force_flag)
            if not ok:
                # Try manual removal if git worktree remove fails
                import shutil
                try:
                    shutil.rmtree(trench_path)
                    # Also need to prune worktrees
                    self._run_git("worktree", "prune")
                except Exception as e:
                    errors.append(f"Failed to remove worktree: {e}")

        # Delete branch
        if delete_branch and self._branch_exists(branch):
            force_flag = "-D" if force else "-d"
            ok, output = self._run_git("branch", force_flag, branch)
            if not ok:
                errors.append(f"Failed to delete branch: {output}")

        if errors:
            return TrenchResult(
                success=False,
                message=f"Cleanup partially failed for trench '{name}'",
                error="; ".join(errors),
            )

        return TrenchResult(
            success=True,
            message=f"Cleaned up trench '{name}'",
        )

    def get_claude_command(self, name: str, task: Optional[str] = None) -> Optional[str]:
        """
        Get the command to launch Claude in a trench.

        Args:
            name: Trench name
            task: Optional task description for the Claude session

        Returns:
            Command string to launch Claude, or None if trench not found
        """
        info = self._read_trench_status(name)
        if not info:
            return None

        # Build claude command
        cmd_parts = ["cd", str(info.worktree_path), "&&", "claude"]
        if task:
            cmd_parts.extend(["-p", f'"{task}"'])

        return " ".join(cmd_parts)

    def signal_ready(self, test_output: str = "") -> bool:
        """
        Signal that the current session is ready for merge.
        Called from within a trench session.

        Args:
            test_output: Optional test output to include

        Returns:
            True if status was updated successfully
        """
        status_file = Path.cwd() / self.STATUS_FILE
        if not status_file.exists():
            return False

        try:
            data = json.loads(status_file.read_text())
            data["status"] = TrenchStatus.READY.value
            data["last_updated"] = datetime.now().isoformat()
            if test_output:
                data["test_output"] = test_output
            status_file.write_text(json.dumps(data, indent=2))
            return True
        except Exception:
            return False

    def list_worktrees(self) -> list[dict]:
        """List all git worktrees in this repo."""
        ok, output = self._run_git("worktree", "list", "--porcelain")
        if not ok:
            return []

        worktrees = []
        current = {}
        for line in output.split("\n"):
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                current = {"path": line[9:]}
            elif line.startswith("HEAD "):
                current["head"] = line[5:]
            elif line.startswith("branch "):
                current["branch"] = line[7:]
            elif line == "bare":
                current["bare"] = True
            elif line == "detached":
                current["detached"] = True

        if current:
            worktrees.append(current)

        return worktrees

    def prune_stale(self, max_age_days: int = 3, dry_run: bool = True) -> list[TrenchResult]:
        """
        Prune stale trenches that haven't been updated recently.

        Args:
            max_age_days: Maximum age in days before a trench is considered stale
            dry_run: If True, only report what would be pruned (default: True)

        Returns:
            List of TrenchResults for each pruned/would-be-pruned trench
        """
        results = []
        now = datetime.now()
        max_age = timedelta(days=max_age_days)

        for info in self.status():
            # Skip recently updated trenches
            age = now - info.last_updated
            if age <= max_age:
                continue

            # Skip trenches that are actively running with a PID
            if info.status == TrenchStatus.RUNNING and info.pid:
                # Check if process is still alive
                try:
                    os.kill(info.pid, 0)
                    continue  # Process still running
                except OSError:
                    pass  # Process dead, can prune

            # Skip merged trenches (already cleaned up)
            if info.status == TrenchStatus.MERGED:
                continue

            age_str = f"{age.days}d" if age.days > 0 else f"{age.seconds // 3600}h"

            if dry_run:
                results.append(TrenchResult(
                    success=True,
                    message=f"Would prune stale trench '{info.name}' (age: {age_str}, status: {info.status.value})",
                    trench=info,
                ))
            else:
                # Actually prune
                result = self.abort(info.name, force=True)
                result.message = f"Pruned stale trench '{info.name}' (age: {age_str})"
                results.append(result)

        return results

    def prune_orphaned_worktrees(self) -> TrenchResult:
        """
        Clean up orphaned git worktrees that no longer have valid paths.

        Returns:
            TrenchResult with cleanup status
        """
        ok, output = self._run_git("worktree", "prune")
        if ok:
            return TrenchResult(
                success=True,
                message="Pruned orphaned worktrees",
            )
        return TrenchResult(
            success=False,
            message="Failed to prune orphaned worktrees",
            error=output,
        )

    def cleanup_all(self, force: bool = False) -> list[TrenchResult]:
        """
        Clean up all trenches.

        Args:
            force: Force removal even if there are uncommitted changes

        Returns:
            List of TrenchResults for each cleaned trench
        """
        results = []
        for info in self.status():
            result = self.abort(info.name, force=force)
            results.append(result)

        # Also prune any orphaned worktrees
        results.append(self.prune_orphaned_worktrees())

        return results
