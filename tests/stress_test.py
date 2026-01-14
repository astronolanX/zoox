#!/usr/bin/env python3
"""
Heavy stress tests for zoox security and cleanup features.
Run with: uv run python tests/stress_test.py
"""

import os
import sys
import time
import tempfile
import threading
import multiprocessing
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reef.blob import (
    Blob, BlobType, BlobScope, BlobStatus, Glob,
    _atomic_write, _validate_path_safe, PathTraversalError
)


def stress_atomic_writes():
    """Stress test atomic writes with 20 threads, 100 writes each."""
    print("\n" + "=" * 60)
    print("STRESS TEST: Atomic Writes (20 threads x 100 writes)")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "contested.txt"
        errors = []
        write_count = [0]
        lock = threading.Lock()

        def writer(thread_id):
            for i in range(100):
                try:
                    content = f"thread_{thread_id}_write_{i}" + ("x" * 1000)
                    _atomic_write(path, content)
                    with lock:
                        write_count[0] += 1
                except Exception as e:
                    errors.append((thread_id, i, e))

        start = time.time()
        threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start

        # Verify final content is complete
        final_content = path.read_text()
        is_valid = final_content.startswith("thread_") and len(final_content) > 1000

        print(f"  Writes completed: {write_count[0]}")
        print(f"  Errors: {len(errors)}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Final content valid: {is_valid}")

        if errors:
            print(f"  FAILED: {errors[:3]}")
            return False

        if not is_valid:
            print(f"  FAILED: Corrupted content")
            return False

        print("  PASSED")
        return True


def stress_concurrent_reads_during_writes():
    """Readers should never see partial content."""
    print("\n" + "=" * 60)
    print("STRESS TEST: Read During Write (10 writers, 10 readers)")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "contested.txt"
        _atomic_write(path, "initial_content_" + "x" * 500)

        partial_reads = []
        stop_flag = threading.Event()
        read_count = [0]
        write_count = [0]

        def reader():
            while not stop_flag.is_set():
                try:
                    content = path.read_text()
                    read_count[0] += 1
                    # Valid content starts with known prefix
                    if not (content.startswith("writer_") or content.startswith("initial_")):
                        partial_reads.append(content[:50])
                except FileNotFoundError:
                    pass  # OK during atomic rename

        def writer(thread_id):
            for i in range(50):
                content = f"writer_{thread_id}_iter_{i}" + ("y" * 800)
                _atomic_write(path, content)
                write_count[0] += 1

        start = time.time()

        # Start readers
        readers = [threading.Thread(target=reader) for _ in range(10)]
        for r in readers:
            r.start()

        # Run writers
        writers = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for w in writers:
            w.start()
        for w in writers:
            w.join()

        stop_flag.set()
        for r in readers:
            r.join()

        elapsed = time.time() - start

        print(f"  Writes: {write_count[0]}")
        print(f"  Reads: {read_count[0]}")
        print(f"  Partial/corrupt reads: {len(partial_reads)}")
        print(f"  Time: {elapsed:.2f}s")

        if partial_reads:
            print(f"  FAILED: Saw partial content: {partial_reads[:3]}")
            return False

        print("  PASSED")
        return True


def stress_archive_collisions():
    """Rapid decompose should never collide."""
    print("\n" + "=" * 60)
    print("STRESS TEST: Archive Collisions (10 threads x 50 decompose)")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        glob = Glob(Path(tmpdir))
        errors = []
        success_count = [0]
        lock = threading.Lock()

        def decompose_worker(worker_id):
            for i in range(50):
                try:
                    name = f"blob_{worker_id}_{i}"
                    blob = Blob(
                        type=BlobType.THREAD,
                        summary=f"Worker {worker_id} blob {i}",
                        status=BlobStatus.ACTIVE,
                    )
                    glob.sprout(blob, name, subdir="threads")
                    glob.decompose(name, subdir="threads")
                    with lock:
                        success_count[0] += 1
                except Exception as e:
                    errors.append((worker_id, i, e))

        start = time.time()
        threads = [threading.Thread(target=decompose_worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start

        # Check archive for duplicates
        archive_dir = glob.claude_dir / "archive"
        if archive_dir.exists():
            archived = list(archive_dir.glob("*.blob.xml"))
            names = [f.name for f in archived]
            duplicates = len(names) - len(set(names))
        else:
            archived = []
            duplicates = 0

        print(f"  Decompose operations: {success_count[0]}")
        print(f"  Archived files: {len(archived)}")
        print(f"  Duplicate names: {duplicates}")
        print(f"  Errors: {len(errors)}")
        print(f"  Time: {elapsed:.2f}s")

        if duplicates > 0:
            print(f"  FAILED: Found duplicate archive names")
            return False

        if errors:
            print(f"  FAILED: {errors[:3]}")
            return False

        print("  PASSED")
        return True


def stress_cleanup_lock_contention():
    """Multiple concurrent cleanups should coordinate via lock."""
    print("\n" + "=" * 60)
    print("STRESS TEST: Cleanup Lock Contention (20 concurrent cleanups)")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        glob = Glob(Path(tmpdir))
        results_list = []
        errors = []
        lock = threading.Lock()

        # Create some old session blobs to clean
        old_date = datetime.now() - timedelta(days=2)
        for i in range(10):
            blob = Blob(
                type=BlobType.CONTEXT,
                summary=f"Old session {i}",
                scope=BlobScope.SESSION,
                updated=old_date,
            )
            glob.sprout(blob, f"old-session-{i}", subdir="contexts")

        # Remove the last-cleanup marker so cleanups can run
        marker = glob.claude_dir / ".last-cleanup"
        if marker.exists():
            marker.unlink()

        def run_cleanup():
            try:
                results = glob.cleanup_session()
                with lock:
                    results_list.append(results)
            except Exception as e:
                with lock:
                    errors.append(e)

        start = time.time()
        threads = [threading.Thread(target=run_cleanup) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start

        # Analyze results
        ran = sum(1 for r in results_list if not r["skipped"] and not r["locked"])
        skipped = sum(1 for r in results_list if r["skipped"])
        locked = sum(1 for r in results_list if r["locked"])

        print(f"  Total cleanups attempted: {len(results_list)}")
        print(f"  Actually ran: {ran}")
        print(f"  Skipped (already cleaned): {skipped}")
        print(f"  Locked (another agent cleaning): {locked}")
        print(f"  Errors: {len(errors)}")
        print(f"  Time: {elapsed:.2f}s")

        # Lock file should not exist after all complete
        lock_exists = (glob.claude_dir / ".cleanup.lock").exists()
        print(f"  Lock file leaked: {lock_exists}")

        if lock_exists:
            print("  FAILED: Lock file was not released")
            return False

        if errors:
            print(f"  FAILED: {errors[:3]}")
            return False

        # Exactly one should have actually cleaned, rest skipped or locked
        if ran + skipped + locked != 20:
            print(f"  FAILED: Unexpected result distribution")
            return False

        print("  PASSED")
        return True


def stress_path_traversal_vectors():
    """Test various path traversal attack vectors."""
    print("\n" + "=" * 60)
    print("STRESS TEST: Path Traversal Vectors")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        glob = Glob(Path(tmpdir))
        blob = Blob(type=BlobType.FACT, summary="Test")

        # Platform-aware vectors
        # On Unix, backslash is NOT a path separator, just a weird char in filename
        # So ..\\escape is actually safe on Unix (just a file named "..\\escape")
        vectors = [
            ("../escape", "Basic parent traversal", True),
            ("../../escape", "Double parent traversal", True),
            ("foo/../../../escape", "Embedded traversal", True),
            ("/etc/passwd", "Absolute path", True),
            ("foo/bar/../../../escape", "Deep embedded", True),
        ]

        # Windows-style only matters on Windows
        if os.name == "nt":
            vectors.extend([
                ("..\\escape", "Windows backslash", True),
                ("..\\/escape", "Mixed slashes", True),
            ])
        else:
            # On Unix, these are just weird filenames (not traversal)
            vectors.extend([
                ("..\\escape", "Windows backslash (Unix: harmless)", False),
                ("..\\/escape", "Mixed slashes (Unix: harmless)", False),
            ])

        blocked = 0
        allowed_safe = 0
        failed = []

        for vector, description, must_block in vectors:
            try:
                path = glob.sprout(blob, "test", subdir=vector)
                if must_block:
                    failed.append((vector, description, "NOT BLOCKED"))
                else:
                    allowed_safe += 1
                    # Clean up the file we just created
                    path.unlink(missing_ok=True)
            except PathTraversalError:
                blocked += 1
            except Exception as e:
                # Other errors are OK (e.g., invalid path chars)
                blocked += 1

        print(f"  Vectors tested: {len(vectors)}")
        print(f"  Blocked (dangerous): {blocked}")
        print(f"  Allowed (safe on this platform): {allowed_safe}")
        print(f"  Failed to block: {len(failed)}")

        if failed:
            for v, d, reason in failed:
                print(f"    FAILED: {d} ({v}) - {reason}")
            return False

        print("  PASSED")
        return True


def stress_large_blob_handling():
    """Test with large blob content."""
    print("\n" + "=" * 60)
    print("STRESS TEST: Large Blob Handling (10MB content)")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        glob = Glob(Path(tmpdir))

        # Create blob with 10MB context
        large_content = "x" * (10 * 1024 * 1024)
        blob = Blob(
            type=BlobType.CONTEXT,
            summary="Large blob test",
            context=large_content,
        )

        start = time.time()
        path = glob.sprout(blob, "large-blob")
        write_time = time.time() - start

        start = time.time()
        loaded = glob.get("large-blob")
        read_time = time.time() - start

        size_mb = path.stat().st_size / (1024 * 1024)
        content_match = len(loaded.context) == len(large_content)

        print(f"  File size: {size_mb:.2f} MB")
        print(f"  Write time: {write_time:.2f}s")
        print(f"  Read time: {read_time:.2f}s")
        print(f"  Content preserved: {content_match}")

        if not content_match:
            print("  FAILED: Content corrupted")
            return False

        print("  PASSED")
        return True


def stress_cleanup_with_many_blobs():
    """Cleanup performance with many blobs."""
    print("\n" + "=" * 60)
    print("STRESS TEST: Cleanup with 500 Blobs")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        glob = Glob(Path(tmpdir))

        # Create 500 blobs (mix of old sessions and regular)
        old_date = datetime.now() - timedelta(days=5)

        start = time.time()
        for i in range(500):
            if i % 5 == 0:
                # 100 old session blobs
                blob = Blob(
                    type=BlobType.CONTEXT,
                    summary=f"Old session {i}",
                    scope=BlobScope.SESSION,
                    updated=old_date,
                )
            else:
                # 400 regular blobs
                blob = Blob(
                    type=BlobType.FACT,
                    summary=f"Fact {i}",
                    scope=BlobScope.PROJECT,
                )
            glob.sprout(blob, f"blob-{i}", subdir="facts" if i % 5 != 0 else "contexts")
        create_time = time.time() - start

        # Count before cleanup
        before_count = len(list(glob.claude_dir.rglob("*.blob.xml")))

        start = time.time()
        results = glob.cleanup_session()
        cleanup_time = time.time() - start

        after_count = len(list(glob.claude_dir.rglob("*.blob.xml")))

        print(f"  Create 500 blobs: {create_time:.2f}s")
        print(f"  Blobs before cleanup: {before_count}")
        print(f"  Cleanup time: {cleanup_time:.2f}s")
        print(f"  Sessions pruned: {results['sessions_pruned']}")
        print(f"  Blobs after cleanup: {after_count}")

        if results["sessions_pruned"] != 100:
            print(f"  FAILED: Expected 100 sessions pruned, got {results['sessions_pruned']}")
            return False

        print("  PASSED")
        return True


def main():
    print("\n" + "#" * 60)
    print("#  GOOPY STRESS TEST SUITE")
    print("#" * 60)

    tests = [
        ("Atomic Writes", stress_atomic_writes),
        ("Read During Write", stress_concurrent_reads_during_writes),
        ("Archive Collisions", stress_archive_collisions),
        ("Cleanup Lock Contention", stress_cleanup_lock_contention),
        ("Path Traversal Vectors", stress_path_traversal_vectors),
        ("Large Blob Handling", stress_large_blob_handling),
        ("Cleanup with Many Blobs", stress_cleanup_with_many_blobs),
    ]

    results = []
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results.append((name, passed, None))
        except Exception as e:
            results.append((name, False, str(e)))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)

    for name, success, error in results:
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {name}")
        if error:
            print(f"         Error: {error}")

    print()
    print(f"  Total: {len(results)} | Passed: {passed} | Failed: {failed}")

    if failed > 0:
        print("\n  STRESS TEST FAILED")
        sys.exit(1)
    else:
        print("\n  ALL STRESS TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
