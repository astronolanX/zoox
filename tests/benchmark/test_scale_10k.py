"""
Benchmark: 10K polip scale testing

Karen demanded tests beyond 500 polips. Here they are.
Tests TF-IDF performance at realistic production scale.
"""

import tempfile
import time
from datetime import date
from pathlib import Path

import pytest

from reef.blob import Blob, BlobType, BlobScope, Glob


# Realistic content generators for diverse polips
SUMMARIES = [
    "Implement user authentication with JWT tokens",
    "Fix memory leak in worker pool connection handling",
    "Refactor database schema for multi-tenancy",
    "Add rate limiting to public API endpoints",
    "Debug intermittent test failures in CI pipeline",
    "Optimize query performance for dashboard views",
    "Implement webhook system for external integrations",
    "Add caching layer for frequently accessed data",
    "Fix race condition in concurrent file uploads",
    "Implement audit logging for compliance requirements",
    "Add support for custom user roles and permissions",
    "Optimize image processing pipeline throughput",
    "Fix timezone handling in scheduled jobs",
    "Implement search functionality with fuzzy matching",
    "Add support for bulk data import/export",
    "Fix session timeout handling edge cases",
    "Implement real-time notifications via WebSocket",
    "Add support for two-factor authentication",
    "Optimize mobile API response payload size",
    "Fix pagination cursor encoding issues",
]

FACTS = [
    "Using PostgreSQL 15 with JSONB columns",
    "Redis cluster for caching with 3 nodes",
    "Kubernetes deployment on GKE",
    "React 18 frontend with TypeScript",
    "Python 3.12 with FastAPI backend",
    "GraphQL API alongside REST endpoints",
    "Celery workers for background jobs",
    "Prometheus metrics with Grafana dashboards",
    "Elasticsearch for full-text search",
    "S3-compatible storage for file uploads",
]


def create_10k_reef(reef_dir: Path, count: int = 10000) -> int:
    """Create a reef with specified number of diverse polips."""
    types = [BlobType.THREAD, BlobType.CONTEXT, BlobType.DECISION, BlobType.CONSTRAINT]
    scopes = [BlobScope.ALWAYS, BlobScope.PROJECT, BlobScope.SESSION]
    subdirs = ["threads", "contexts", "decisions", "constraints"]

    for i in range(count):
        blob_type = types[i % len(types)]
        summary = SUMMARIES[i % len(SUMMARIES)]
        # Add variation to make content unique
        summary = f"{summary} (variant {i})"

        blob = Blob(
            type=blob_type,
            scope=scopes[i % len(scopes)],
            summary=summary,
        )
        # Add diverse facts
        blob.facts = [
            FACTS[(i + j) % len(FACTS)]
            for j in range(min(5, i % 10))
        ]

        subdir = reef_dir / subdirs[i % len(subdirs)]
        subdir.mkdir(exist_ok=True)
        path = subdir / f"polip-{i:05d}.blob.xml"
        blob.save(path)

    return count


class TestScale10K:
    """Test performance at 10,000 polip scale."""

    @pytest.fixture(scope="class")
    def large_reef_10k(self):
        """Create 10K polip reef (reused across class)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()

            print("\nCreating 10K polips...")
            start = time.perf_counter()
            count = create_10k_reef(reef_dir, count=10000)
            create_time = time.perf_counter() - start
            print(f"  Created {count:,} polips in {create_time:.2f}s")

            glob = Glob(root)

            yield glob, count

    def test_index_build_time_10k(self, large_reef_10k):
        """Measure index build time at 10K scale."""
        glob, count = large_reef_10k

        start = time.perf_counter()
        indexed = glob.rebuild_index()
        elapsed = time.perf_counter() - start

        print(f"\n=== 10K INDEX BUILD ===")
        print(f"  Polips indexed: {indexed:,}")
        print(f"  Build time: {elapsed:.2f}s")
        print(f"  Rate: {indexed/elapsed:.0f} polips/sec")

        # Karen's bar: should complete in reasonable time
        assert elapsed < 60, f"Index build took {elapsed:.2f}s, should be under 60s"
        assert indexed == count, f"Expected {count} indexed, got {indexed}"

    def test_search_latency_10k(self, large_reef_10k):
        """Measure search latency at 10K scale."""
        glob, _ = large_reef_10k

        # Ensure index is built
        glob.rebuild_index()

        queries = [
            "authentication JWT",
            "memory leak worker",
            "database schema",
            "API rate limiting",
            "WebSocket notifications",
            "two-factor authentication",
            "PostgreSQL JSONB",
            "Kubernetes deployment",
        ]

        times = []
        for query in queries:
            start = time.perf_counter()
            results = glob.search_index(query=query, limit=10)
            elapsed = time.perf_counter() - start
            times.append((query, elapsed, len(results)))

        avg_ms = (sum(t[1] for t in times) / len(times)) * 1000
        max_ms = max(t[1] for t in times) * 1000

        print(f"\n=== 10K SEARCH LATENCY ===")
        for query, elapsed, result_count in times:
            print(f"  '{query[:30]}...' → {elapsed*1000:.1f}ms ({result_count} results)")
        print(f"")
        print(f"  Average: {avg_ms:.1f}ms")
        print(f"  Max: {max_ms:.1f}ms")
        print(f"  P95 target: <500ms")

        # Karen's bar: search should stay under 500ms even at 10K
        assert avg_ms < 500, f"Average search {avg_ms:.1f}ms exceeds 500ms target"

    def test_list_all_latency_10k(self, large_reef_10k):
        """Measure time to list all polips at 10K scale."""
        glob, count = large_reef_10k

        start = time.perf_counter()
        # Note: list_blobs only searches root, need to search all subdirs
        all_blobs = []
        for subdir in ["threads", "contexts", "decisions", "constraints"]:
            all_blobs.extend(glob.list_blobs(subdir=subdir))
        elapsed = time.perf_counter() - start

        print(f"\n=== 10K LIST ALL ===")
        print(f"  Polips found: {len(all_blobs):,}")
        print(f"  Load time: {elapsed:.2f}s")
        print(f"  Rate: {len(all_blobs)/elapsed:.0f} polips/sec")

        # Should find all polips
        assert len(all_blobs) == count, f"Expected {count}, found {len(all_blobs)}"
        # Should complete in reasonable time
        assert elapsed < 30, f"List all took {elapsed:.2f}s, should be under 30s"

    def test_memory_usage_10k(self, large_reef_10k):
        """Measure memory consumption at 10K scale."""
        import sys

        glob, _ = large_reef_10k

        # Force index load
        glob.rebuild_index()
        index = glob.get_index()

        # Measure index size
        index_size = sys.getsizeof(str(index))  # Rough estimate

        print(f"\n=== 10K MEMORY USAGE ===")
        print(f"  Index entries: {len(index.get('blobs', {})):,}")
        print(f"  Index size (approx): {index_size / 1024:.1f} KB")
        print(f"  Cache size: {glob.cache_stats()}")

        # Sanity check: index shouldn't explode
        assert index_size < 50 * 1024 * 1024, "Index size exceeds 50MB"


class TestScaleProgression:
    """Test performance degradation across scales."""

    @pytest.mark.parametrize("scale", [100, 500, 1000, 5000])
    def test_search_at_scale(self, scale):
        """Measure search latency at different scales."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()

            create_10k_reef(reef_dir, count=scale)
            glob = Glob(root)
            glob.rebuild_index()

            # Time a search
            query = "authentication JWT tokens"
            times = []
            for _ in range(5):
                start = time.perf_counter()
                glob.search_index(query=query, limit=10)
                times.append(time.perf_counter() - start)

            avg_ms = (sum(times) / len(times)) * 1000

            print(f"\n  Scale {scale:,}: {avg_ms:.2f}ms avg search")

            # Track for regression
            # At 100: ~1ms, at 5000: ~50ms expected (O(n) with TF-IDF)


class TestScaleEdgeCases:
    """Test edge cases at scale."""

    def test_empty_reef_search(self):
        """Search on empty reef shouldn't crash."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()

            glob = Glob(root)
            results = glob.search_index(query="anything", limit=10)

            assert results == [], "Empty reef should return empty results"

    def test_single_polip_search(self):
        """Search with single polip should work."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()

            create_10k_reef(reef_dir, count=1)
            glob = Glob(root)
            glob.rebuild_index()

            results = glob.search_index(query="authentication", limit=10)
            assert len(results) <= 1

    def test_no_match_search(self):
        """Search with no matches should return empty."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()

            create_10k_reef(reef_dir, count=100)
            glob = Glob(root)
            glob.rebuild_index()

            results = glob.search_index(query="xyzzy quantum entanglement", limit=10)
            # Should return empty or very low scores
            if results:
                assert results[0][2] < 0.1, "Non-matching query should have low score"
