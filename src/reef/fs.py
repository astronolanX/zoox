"""
AI-native filesystem primitives (stdlib-only).

Provides reliable filesystem operations for concurrent/parallel agent coordination:
- Atomic writes (no partial reads)
- Event sourcing (append-only logs eliminate races)
- File locking (for exclusive access when needed)
- Process tracking (robust PID management)

Design principle: Event files eliminate races by design. Instead of fixing
file locking, eliminate the need for it where possible.
"""

import fcntl
import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable


def atomic_write(path: Path, content: str) -> None:
    """
    Atomically write content to a file using temp+rename pattern.

    This ensures that readers never see partial writes - they either
    see the old content or the complete new content.

    Args:
        path: Destination file path
        content: Content to write
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory (ensures same filesystem for rename)
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)  # Ensure data hits disk
        os.close(fd)
        fd = None

        # Atomic rename (POSIX guarantees atomicity on same filesystem)
        os.rename(tmp_path, path)
    except Exception:
        # Clean up temp file on failure
        if fd is not None:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


class FileLock:
    """
    File-based locking for exclusive access to resources.

    Uses fcntl.flock() for cross-process synchronization on Unix systems.
    Supports context manager protocol for safe cleanup.

    Example:
        lock = FileLock(Path("/tmp/mylock"))
        with lock:
            # Critical section
            pass

        # Or manual acquire/release:
        if lock.acquire(blocking=False):
            try:
                # Critical section
                pass
            finally:
                lock.release()
    """

    def __init__(self, path: Path, timeout: float = 30.0):
        """
        Initialize a file lock.

        Args:
            path: Path to the lock file (will be created if doesn't exist)
            timeout: Maximum time to wait for lock acquisition (seconds)
        """
        self.path = Path(path)
        self.timeout = timeout
        self._fd: Optional[int] = None
        self._acquired = False

    def acquire(self, blocking: bool = True) -> bool:
        """
        Acquire the lock.

        Args:
            blocking: If True, block until lock is acquired or timeout.
                     If False, return immediately if lock is unavailable.

        Returns:
            True if lock was acquired, False if timeout or non-blocking fail
        """
        if self._acquired:
            return True

        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Open or create the lock file
        self._fd = os.open(
            self.path,
            os.O_RDWR | os.O_CREAT,
            0o644
        )

        if blocking:
            start = time.monotonic()
            while True:
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self._acquired = True
                    return True
                except BlockingIOError:
                    if time.monotonic() - start >= self.timeout:
                        os.close(self._fd)
                        self._fd = None
                        return False
                    time.sleep(0.01)  # 10ms between retries
        else:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._acquired = True
                return True
            except BlockingIOError:
                os.close(self._fd)
                self._fd = None
                return False

    def release(self) -> None:
        """Release the lock."""
        if self._fd is not None and self._acquired:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None
            self._acquired = False

    def __enter__(self) -> "FileLock":
        if not self.acquire():
            raise TimeoutError(f"Failed to acquire lock on {self.path}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    @property
    def is_locked(self) -> bool:
        """Check if this instance holds the lock."""
        return self._acquired


class EventLog:
    """
    Append-only event log for race-free coordination.

    Events are stored as individual JSON files with sequence numbers.
    This eliminates race conditions by design - no overwrites, just appends.
    State is computed by replaying events in order.

    Directory structure:
        events_dir/
        ├── 001-spawn.json
        ├── 002-running.json
        └── 003-ready.json

    Example:
        log = EventLog(Path(".reef-trenches/my-trench/events"))
        log.emit("spawn", {"task": "implement feature"})
        log.emit("running", {"pid": 12345})

        # Reconstruct state from events
        state = log.compute_state(reducer=my_reducer)
    """

    def __init__(self, events_dir: Path):
        """
        Initialize an event log.

        Args:
            events_dir: Directory to store event files
        """
        self.events_dir = Path(events_dir)

    def emit(self, event_type: str, data: dict) -> Path:
        """
        Emit an event to the log.

        Args:
            event_type: Type of event (spawn, running, ready, etc.)
            data: Event-specific data

        Returns:
            Path to the created event file
        """
        self.events_dir.mkdir(parents=True, exist_ok=True)

        # Count existing events to get next sequence number
        existing = sorted(self.events_dir.glob("*.json"))
        next_num = len(existing) + 1

        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "seq": next_num,
            **data,
        }

        event_file = self.events_dir / f"{next_num:03d}-{event_type}.json"
        atomic_write(event_file, json.dumps(event, indent=2))
        return event_file

    def read_all(self) -> list[dict]:
        """
        Read all events in sequence order.

        Returns:
            List of event dicts, sorted by sequence number
        """
        if not self.events_dir.exists():
            return []

        events = []
        for event_file in sorted(self.events_dir.glob("*.json")):
            try:
                event = json.loads(event_file.read_text())
                events.append(event)
            except (json.JSONDecodeError, OSError):
                continue  # Skip corrupted events

        return events

    def tail(self, n: int = 10) -> list[dict]:
        """
        Read the last n events.

        Args:
            n: Number of recent events to return

        Returns:
            List of the most recent n events
        """
        all_events = self.read_all()
        return all_events[-n:] if len(all_events) > n else all_events

    def compute_state(
        self,
        reducer: Optional[Callable[[dict, dict], dict]] = None,
        initial_state: Optional[dict] = None,
    ) -> dict:
        """
        Compute current state by reducing all events.

        Args:
            reducer: Function (state, event) -> new_state
                    If not provided, uses simple merge strategy
            initial_state: Starting state (default: empty dict)

        Returns:
            Final computed state after applying all events
        """
        events = self.read_all()
        state = dict(initial_state) if initial_state else {}

        if reducer is None:
            # Default reducer: simple merge with type tracking
            def reducer(state: dict, event: dict) -> dict:
                new_state = dict(state)
                new_state["last_event_type"] = event.get("type")
                new_state["last_updated"] = event.get("timestamp")
                # Merge event data (excluding metadata)
                for key, value in event.items():
                    if key not in ("type", "timestamp", "seq"):
                        new_state[key] = value
                return new_state

        for event in events:
            state = reducer(state, event)

        return state

    def count(self) -> int:
        """Return the number of events in the log."""
        if not self.events_dir.exists():
            return 0
        return len(list(self.events_dir.glob("*.json")))

    def clear(self) -> int:
        """
        Clear all events from the log.

        Returns:
            Number of events deleted
        """
        if not self.events_dir.exists():
            return 0

        count = 0
        for event_file in self.events_dir.glob("*.json"):
            try:
                event_file.unlink()
                count += 1
            except OSError:
                pass

        return count


@dataclass
class ProcessInfo:
    """Information about a tracked process."""
    pid: int
    name: str
    start_time: float  # time.monotonic() when registered
    registered_at: str  # ISO timestamp


class ProcessTracker:
    """
    Robust process tracking with PID reuse protection.

    Tracks processes by name and detects when PIDs may have been reused
    by the OS (which can happen after a process dies and the PID is recycled).

    Uses a combination of:
    - os.kill(pid, 0) to check process existence
    - Registration time to detect stale processes
    - Maximum age threshold to identify potential PID reuse

    Example:
        tracker = ProcessTracker(Path(".reef-trenches/.processes.json"))
        tracker.register(pid=12345, name="feature-x")

        if tracker.is_alive("feature-x"):
            print("Still running")

        # Wait for completion with timeout
        if tracker.wait_for_completion("feature-x", timeout=60):
            print("Completed")
    """

    DEFAULT_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days

    def __init__(
        self,
        state_file: Path,
        max_age_seconds: float = DEFAULT_MAX_AGE_SECONDS,
    ):
        """
        Initialize a process tracker.

        Args:
            state_file: Path to store process tracking state
            max_age_seconds: Maximum process age before considering PID stale
        """
        self.state_file = Path(state_file)
        self.max_age_seconds = max_age_seconds
        self._processes: dict[str, ProcessInfo] = {}
        self._load()

    def _load(self) -> None:
        """Load process state from file."""
        if not self.state_file.exists():
            return

        try:
            data = json.loads(self.state_file.read_text())
            for name, info in data.get("processes", {}).items():
                self._processes[name] = ProcessInfo(
                    pid=info["pid"],
                    name=info["name"],
                    start_time=info["start_time"],
                    registered_at=info["registered_at"],
                )
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    def _save(self) -> None:
        """Save process state to file."""
        data = {
            "processes": {
                name: {
                    "pid": info.pid,
                    "name": info.name,
                    "start_time": info.start_time,
                    "registered_at": info.registered_at,
                }
                for name, info in self._processes.items()
            }
        }
        atomic_write(self.state_file, json.dumps(data, indent=2))

    def register(self, pid: int, name: str) -> None:
        """
        Register a process for tracking.

        Args:
            pid: Process ID
            name: Unique name for this process
        """
        self._processes[name] = ProcessInfo(
            pid=pid,
            name=name,
            start_time=time.monotonic(),
            registered_at=datetime.now().isoformat(),
        )
        self._save()

    def unregister(self, name: str) -> bool:
        """
        Unregister a process.

        Args:
            name: Process name

        Returns:
            True if process was registered, False if not found
        """
        if name in self._processes:
            del self._processes[name]
            self._save()
            return True
        return False

    def get(self, name: str) -> Optional[ProcessInfo]:
        """
        Get process info by name.

        Args:
            name: Process name

        Returns:
            ProcessInfo or None if not found
        """
        return self._processes.get(name)

    def is_alive(self, name: str) -> bool:
        """
        Check if a tracked process is still running.

        Uses PID existence check plus age-based heuristic to detect PID reuse.

        Args:
            name: Process name

        Returns:
            True if process is alive, False otherwise
        """
        info = self._processes.get(name)
        if not info:
            return False

        # Check if process exists
        try:
            os.kill(info.pid, 0)
        except OSError:
            return False  # Process doesn't exist

        # PID reuse protection: check age
        # Note: start_time is monotonic, so we need to check relative age
        # We can't compare monotonic times across sessions, so fall back to
        # registered_at timestamp for cross-session checks
        try:
            registered = datetime.fromisoformat(info.registered_at)
            age_seconds = (datetime.now() - registered).total_seconds()
            if age_seconds > self.max_age_seconds:
                return False  # Too old, likely PID reuse
        except (ValueError, TypeError):
            pass

        return True

    def wait_for_completion(
        self,
        name: str,
        timeout: float,
        poll_interval: float = 0.5,
    ) -> bool:
        """
        Wait for a process to complete.

        Args:
            name: Process name
            timeout: Maximum time to wait (seconds)
            poll_interval: Time between checks (seconds)

        Returns:
            True if process completed, False if timeout
        """
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if not self.is_alive(name):
                return True
            time.sleep(poll_interval)
        return False

    def list_active(self) -> list[ProcessInfo]:
        """
        List all active (alive) processes.

        Returns:
            List of ProcessInfo for processes that are still alive
        """
        return [
            info for name, info in self._processes.items()
            if self.is_alive(name)
        ]

    def cleanup_dead(self) -> list[str]:
        """
        Remove tracking for dead processes.

        Returns:
            List of names that were cleaned up
        """
        dead = [
            name for name in self._processes
            if not self.is_alive(name)
        ]
        for name in dead:
            del self._processes[name]
        if dead:
            self._save()
        return dead
