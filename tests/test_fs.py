"""
Tests for reef.fs - AI-native filesystem primitives.
"""

import json
import os
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

from reef.fs import atomic_write, FileLock, EventLog, ProcessTracker, ProcessInfo


class TestAtomicWrite:
    """Tests for atomic_write function."""

    def test_basic_write(self, tmp_path):
        """Test basic file writing."""
        path = tmp_path / "test.txt"
        atomic_write(path, "hello world")
        assert path.read_text() == "hello world"

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created."""
        path = tmp_path / "nested" / "dir" / "test.txt"
        atomic_write(path, "content")
        assert path.read_text() == "content"

    def test_overwrites_existing(self, tmp_path):
        """Test that existing files are overwritten."""
        path = tmp_path / "test.txt"
        atomic_write(path, "first")
        atomic_write(path, "second")
        assert path.read_text() == "second"

    def test_no_partial_writes(self, tmp_path):
        """Test that writes are atomic (no partial content visible)."""
        path = tmp_path / "test.txt"
        content = "x" * 1000000  # 1MB of data

        # Write should be atomic
        atomic_write(path, content)
        assert path.read_text() == content

    def test_unicode_content(self, tmp_path):
        """Test writing unicode content."""
        path = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍 مرحبا"
        atomic_write(path, content)
        assert path.read_text() == content

    def test_no_temp_files_left_on_success(self, tmp_path):
        """Test that no temp files are left after successful write."""
        path = tmp_path / "test.txt"
        atomic_write(path, "content")

        # Should only have the target file, no temp files
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0] == path


class TestFileLock:
    """Tests for FileLock class."""

    def test_basic_acquire_release(self, tmp_path):
        """Test basic lock acquisition and release."""
        lock = FileLock(tmp_path / "test.lock")
        assert lock.acquire()
        assert lock.is_locked
        lock.release()
        assert not lock.is_locked

    def test_context_manager(self, tmp_path):
        """Test lock as context manager."""
        lock = FileLock(tmp_path / "test.lock")
        with lock:
            assert lock.is_locked
        assert not lock.is_locked

    def test_double_acquire_same_instance(self, tmp_path):
        """Test that double acquire on same instance succeeds."""
        lock = FileLock(tmp_path / "test.lock")
        assert lock.acquire()
        assert lock.acquire()  # Should succeed (same instance)
        lock.release()

    def test_non_blocking_fails_when_locked(self, tmp_path):
        """Test non-blocking acquire fails when lock is held."""
        lock_path = tmp_path / "test.lock"
        lock1 = FileLock(lock_path)
        lock2 = FileLock(lock_path)

        assert lock1.acquire()
        assert not lock2.acquire(blocking=False)
        lock1.release()
        assert lock2.acquire(blocking=False)
        lock2.release()

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created."""
        lock = FileLock(tmp_path / "nested" / "dir" / "test.lock")
        with lock:
            assert lock.is_locked

    def test_timeout(self, tmp_path):
        """Test that blocking acquire times out."""
        lock_path = tmp_path / "test.lock"
        lock1 = FileLock(lock_path, timeout=0.1)
        lock2 = FileLock(lock_path, timeout=0.1)

        lock1.acquire()
        start = time.monotonic()
        result = lock2.acquire()
        elapsed = time.monotonic() - start

        assert not result  # Should have timed out
        assert elapsed >= 0.1
        lock1.release()


class TestEventLog:
    """Tests for EventLog class."""

    def test_emit_creates_directory(self, tmp_path):
        """Test that emit creates events directory."""
        events_dir = tmp_path / "events"
        log = EventLog(events_dir)
        log.emit("test", {"data": "value"})
        assert events_dir.exists()

    def test_emit_creates_numbered_files(self, tmp_path):
        """Test that events are numbered sequentially."""
        log = EventLog(tmp_path / "events")
        log.emit("first", {})
        log.emit("second", {})
        log.emit("third", {})

        events_dir = tmp_path / "events"
        files = sorted(events_dir.glob("*.json"))
        assert len(files) == 3
        assert files[0].name == "001-first.json"
        assert files[1].name == "002-second.json"
        assert files[2].name == "003-third.json"

    def test_emit_stores_event_data(self, tmp_path):
        """Test that event data is stored correctly."""
        log = EventLog(tmp_path / "events")
        log.emit("spawn", {"task": "implement feature", "model": "sonnet"})

        event_file = tmp_path / "events" / "001-spawn.json"
        data = json.loads(event_file.read_text())

        assert data["type"] == "spawn"
        assert data["task"] == "implement feature"
        assert data["model"] == "sonnet"
        assert data["seq"] == 1
        assert "timestamp" in data

    def test_read_all_returns_events_in_order(self, tmp_path):
        """Test that read_all returns events in sequence order."""
        log = EventLog(tmp_path / "events")
        log.emit("first", {"n": 1})
        log.emit("second", {"n": 2})
        log.emit("third", {"n": 3})

        events = log.read_all()
        assert len(events) == 3
        assert events[0]["type"] == "first"
        assert events[1]["type"] == "second"
        assert events[2]["type"] == "third"

    def test_read_all_empty_directory(self, tmp_path):
        """Test read_all with no events."""
        log = EventLog(tmp_path / "events")
        assert log.read_all() == []

    def test_tail_returns_recent_events(self, tmp_path):
        """Test tail returns most recent events."""
        log = EventLog(tmp_path / "events")
        for i in range(10):
            log.emit(f"event-{i}", {"n": i})

        recent = log.tail(3)
        assert len(recent) == 3
        assert recent[0]["type"] == "event-7"
        assert recent[1]["type"] == "event-8"
        assert recent[2]["type"] == "event-9"

    def test_compute_state_default_reducer(self, tmp_path):
        """Test compute_state with default reducer."""
        log = EventLog(tmp_path / "events")
        log.emit("spawn", {"task": "feature"})
        log.emit("running", {"pid": 12345})
        log.emit("ready", {"test_output": "passed"})

        state = log.compute_state()
        assert state["last_event_type"] == "ready"
        assert state["task"] == "feature"
        assert state["pid"] == 12345
        assert state["test_output"] == "passed"

    def test_compute_state_custom_reducer(self, tmp_path):
        """Test compute_state with custom reducer."""
        log = EventLog(tmp_path / "events")
        log.emit("add", {"value": 5})
        log.emit("add", {"value": 3})
        log.emit("multiply", {"value": 2})

        def reducer(state, event):
            total = state.get("total", 0)
            if event["type"] == "add":
                return {"total": total + event["value"]}
            elif event["type"] == "multiply":
                return {"total": total * event["value"]}
            return state

        state = log.compute_state(reducer=reducer)
        assert state["total"] == 16  # (5 + 3) * 2

    def test_count(self, tmp_path):
        """Test event count."""
        log = EventLog(tmp_path / "events")
        assert log.count() == 0
        log.emit("a", {})
        assert log.count() == 1
        log.emit("b", {})
        log.emit("c", {})
        assert log.count() == 3

    def test_clear(self, tmp_path):
        """Test clearing events."""
        log = EventLog(tmp_path / "events")
        log.emit("a", {})
        log.emit("b", {})
        log.emit("c", {})

        cleared = log.clear()
        assert cleared == 3
        assert log.count() == 0


class TestProcessTracker:
    """Tests for ProcessTracker class."""

    def test_register_and_get(self, tmp_path):
        """Test registering and retrieving process info."""
        tracker = ProcessTracker(tmp_path / "processes.json")
        tracker.register(pid=12345, name="test-process")

        info = tracker.get("test-process")
        assert info is not None
        assert info.pid == 12345
        assert info.name == "test-process"

    def test_unregister(self, tmp_path):
        """Test unregistering a process."""
        tracker = ProcessTracker(tmp_path / "processes.json")
        tracker.register(pid=12345, name="test-process")
        assert tracker.get("test-process") is not None

        result = tracker.unregister("test-process")
        assert result is True
        assert tracker.get("test-process") is None

    def test_unregister_nonexistent(self, tmp_path):
        """Test unregistering a nonexistent process."""
        tracker = ProcessTracker(tmp_path / "processes.json")
        result = tracker.unregister("nonexistent")
        assert result is False

    def test_is_alive_nonexistent(self, tmp_path):
        """Test is_alive for nonexistent process."""
        tracker = ProcessTracker(tmp_path / "processes.json")
        assert not tracker.is_alive("nonexistent")

    def test_is_alive_dead_pid(self, tmp_path):
        """Test is_alive with a dead PID."""
        tracker = ProcessTracker(tmp_path / "processes.json")
        # Register with a PID that definitely doesn't exist
        tracker.register(pid=99999999, name="dead-process")
        assert not tracker.is_alive("dead-process")

    def test_is_alive_current_process(self, tmp_path):
        """Test is_alive with current process PID."""
        tracker = ProcessTracker(tmp_path / "processes.json")
        current_pid = os.getpid()
        tracker.register(pid=current_pid, name="current-process")
        assert tracker.is_alive("current-process")

    def test_persistence(self, tmp_path):
        """Test that process info persists across instances."""
        state_file = tmp_path / "processes.json"

        # Register with first tracker
        tracker1 = ProcessTracker(state_file)
        tracker1.register(pid=12345, name="persistent-process")

        # Load with second tracker
        tracker2 = ProcessTracker(state_file)
        info = tracker2.get("persistent-process")
        assert info is not None
        assert info.pid == 12345

    def test_list_active(self, tmp_path):
        """Test listing active processes."""
        tracker = ProcessTracker(tmp_path / "processes.json")
        current_pid = os.getpid()

        tracker.register(pid=current_pid, name="alive")
        tracker.register(pid=99999999, name="dead")

        active = tracker.list_active()
        names = [p.name for p in active]
        assert "alive" in names
        assert "dead" not in names

    def test_cleanup_dead(self, tmp_path):
        """Test cleaning up dead processes."""
        tracker = ProcessTracker(tmp_path / "processes.json")
        current_pid = os.getpid()

        tracker.register(pid=current_pid, name="alive")
        tracker.register(pid=99999999, name="dead1")
        tracker.register(pid=99999998, name="dead2")

        cleaned = tracker.cleanup_dead()
        assert "dead1" in cleaned
        assert "dead2" in cleaned
        assert "alive" not in cleaned

        # Verify they're actually removed
        assert tracker.get("dead1") is None
        assert tracker.get("dead2") is None
        assert tracker.get("alive") is not None

    def test_wait_for_completion_immediate(self, tmp_path):
        """Test wait_for_completion with dead process returns immediately."""
        tracker = ProcessTracker(tmp_path / "processes.json")
        tracker.register(pid=99999999, name="dead-process")

        start = time.monotonic()
        result = tracker.wait_for_completion("dead-process", timeout=10)
        elapsed = time.monotonic() - start

        assert result is True
        assert elapsed < 1  # Should return quickly


class TestConcurrency:
    """Tests for concurrent access patterns."""

    def test_concurrent_event_emission(self, tmp_path):
        """Test that concurrent event emission doesn't lose events."""
        log = EventLog(tmp_path / "events")
        n_threads = 10
        n_events_per_thread = 10

        def emit_events(thread_id):
            for i in range(n_events_per_thread):
                log.emit(f"thread-{thread_id}", {"event": i})

        threads = [
            threading.Thread(target=emit_events, args=(i,))
            for i in range(n_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All events should be captured
        total_events = log.count()
        assert total_events == n_threads * n_events_per_thread

    def test_lock_prevents_concurrent_access(self, tmp_path):
        """Test that file lock prevents concurrent access."""
        lock_path = tmp_path / "test.lock"
        counter = {"value": 0}
        n_increments = 100

        def increment_with_lock():
            lock = FileLock(lock_path, timeout=10)
            for _ in range(n_increments):
                with lock:
                    # Simulate read-modify-write
                    current = counter["value"]
                    time.sleep(0.001)  # Yield to other threads
                    counter["value"] = current + 1

        threads = [
            threading.Thread(target=increment_with_lock)
            for _ in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # With proper locking, counter should equal total increments
        assert counter["value"] == 5 * n_increments
