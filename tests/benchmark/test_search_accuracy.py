"""
Benchmark: TF-IDF search accuracy

Ground truth queries with expected results.
No LLM evaluation - deterministic assertions only.
"""

import tempfile
from datetime import date
from pathlib import Path

import pytest

from reef.format import Polip, Reef


# Create a reef with diverse polips for search testing
def create_test_reef(reef_dir: Path) -> list[Polip]:
    """Build a test reef with known content as .reef files."""
    polips = [
        Polip.create(
            id="auth-system",
            type="thread",
            scope="project",
            updated=date.today(),
            summary="User authentication with JWT tokens",
            facts=[
                "Using RS256 for token signing",
                "Refresh tokens stored in Redis",
                "Access tokens expire in 15 minutes",
            ],
            decisions=["OAuth2 over SAML", "No session cookies"],
            context=["Implementing login and logout endpoints"],
            steps=[
                (True, "Set up JWT library"),
                (False, "Add token validation middleware"),
            ],
            status="active",
        ),
        Polip.create(
            id="database-schema",
            type="context",
            scope="project",
            updated=date.today(),
            summary="PostgreSQL database schema design",
            facts=[
                "Users table with UUID primary key",
                "JSONB for flexible metadata",
                "Indexes on email and created_at",
            ],
            decisions=["Soft delete over hard delete"],
            context=["Migration system using alembic"],
        ),
        Polip.create(
            id="api-versioning",
            type="decision",
            scope="project",
            updated=date.today(),
            summary="API versioning strategy decision",
            facts=["RESTful endpoints at /api/v1/"],
            decisions=[
                "URL-based versioning over header-based",
                "Deprecation warnings 6 months before removal",
            ],
            context=["Breaking changes require major version bump"],
        ),
        Polip.create(
            id="testing-strategy",
            type="context",
            scope="project",
            updated=date.today(),
            summary="Testing approach and coverage requirements",
            facts=[
                "pytest for all tests",
                "80% minimum coverage",
                "Integration tests use docker-compose",
            ],
            decisions=["Mock external APIs in unit tests"],
            context=["CI runs full suite on every PR"],
        ),
        Polip.create(
            id="no-secrets",
            type="constraint",
            scope="always",
            updated=date.today(),
            summary="Never commit secrets or credentials",
            facts=[
                "Use environment variables for secrets",
                "pre-commit hook scans for common patterns",
            ],
            decisions=[],
            context=[],
        ),
        Polip.create(
            id="memory-leak-debug",
            type="thread",
            scope="session",
            updated=date.today(),
            summary="Debugging memory leak in worker pool",
            facts=[
                "Memory grows 2MB/hour under load",
                "gc.collect() doesn't reclaim",
                "Happens after v2.3.1 deployment",
            ],
            decisions=["Added memory profiling"],
            context=["Suspect connection pool issue"],
            steps=[
                (True, "Reproduce locally"),
                (False, "Identify root cause"),
            ],
            status="active",
        ),
    ]

    for p in polips:
        p.save(reef_dir)

    return polips


def create_test_reef_xml(reef_dir: Path) -> list[dict]:
    """Build a test reef with .blob.xml files for Glob/TF-IDF testing."""
    from reef.blob import Blob, BlobType, BlobScope, BlobStatus

    blobs = []
    blob_defs = [
        {
            "name": "auth-system",
            "type": BlobType.THREAD,
            "scope": BlobScope.PROJECT,
            "summary": "User authentication with JWT tokens",
            "facts": [
                "Using RS256 for token signing",
                "Refresh tokens stored in Redis",
                "Access tokens expire in 15 minutes",
            ],
            "status": BlobStatus.ACTIVE,
            "subdir": "threads",
        },
        {
            "name": "database-schema",
            "type": BlobType.CONTEXT,
            "scope": BlobScope.PROJECT,
            "summary": "PostgreSQL database schema design",
            "facts": [
                "Users table with UUID primary key",
                "JSONB for flexible metadata",
                "Indexes on email and created_at",
            ],
            "subdir": "contexts",
        },
        {
            "name": "api-versioning",
            "type": BlobType.DECISION,
            "scope": BlobScope.PROJECT,
            "summary": "API versioning strategy decision",
            "facts": ["RESTful endpoints at /api/v1/"],
            "subdir": "decisions",
        },
        {
            "name": "testing-strategy",
            "type": BlobType.CONTEXT,
            "scope": BlobScope.PROJECT,
            "summary": "Testing approach and coverage requirements",
            "facts": [
                "pytest for all tests",
                "80% minimum coverage",
                "Integration tests use docker-compose",
            ],
            "subdir": "contexts",
        },
        {
            "name": "no-secrets",
            "type": BlobType.CONSTRAINT,
            "scope": BlobScope.ALWAYS,
            "summary": "Never commit secrets or credentials",
            "facts": [
                "Use environment variables for secrets",
                "pre-commit hook scans for common patterns",
            ],
            "subdir": "constraints",
        },
        {
            "name": "memory-leak-debug",
            "type": BlobType.THREAD,
            "scope": BlobScope.SESSION,
            "summary": "Debugging memory leak in worker pool",
            "facts": [
                "Memory grows 2MB/hour under load",
                "gc.collect() doesn't reclaim",
                "Happens after v2.3.1 deployment",
            ],
            "status": BlobStatus.ACTIVE,
            "subdir": "threads",
        },
    ]

    for bd in blob_defs:
        blob = Blob(
            type=bd["type"],
            scope=bd["scope"],
            summary=bd["summary"],
        )
        blob.facts = bd.get("facts", [])
        if "status" in bd:
            blob.status = bd["status"]

        # Save to appropriate subdir
        subdir = reef_dir / bd["subdir"]
        subdir.mkdir(exist_ok=True)
        path = subdir / f"{bd['name']}.blob.xml"
        blob.save(path)
        blobs.append({"name": bd["name"], "path": path, "blob": blob})

    return blobs


# Ground truth: query -> expected polip IDs (in order of relevance)
SEARCH_GROUND_TRUTH = [
    # Exact match queries
    ("JWT tokens", ["auth-system"]),
    ("PostgreSQL", ["database-schema"]),
    ("memory leak", ["memory-leak-debug"]),
    ("API versioning", ["api-versioning"]),
    ("testing coverage", ["testing-strategy"]),
    ("secrets credentials", ["no-secrets"]),

    # Keyword queries
    ("authentication login", ["auth-system"]),
    ("database schema design", ["database-schema"]),
    ("worker pool debugging", ["memory-leak-debug"]),
    ("pytest coverage", ["testing-strategy"]),

    # Multi-word semantic queries
    ("how do we handle user login", ["auth-system"]),
    ("what database are we using", ["database-schema"]),
    ("test requirements", ["testing-strategy"]),

    # Should NOT match (negative cases)
    ("kubernetes deployment", []),
    ("frontend react components", []),
    ("machine learning model", []),
]


class TestSearchAccuracy:
    """Test TF-IDF search with ground truth."""

    @pytest.fixture
    def reef_with_polips(self):
        """Create temporary reef with test polips."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()

            polips = create_test_reef(reef_dir)
            reef = Reef(root)

            yield reef, polips

    def test_all_polips_indexed(self, reef_with_polips):
        """Verify all polips are discoverable."""
        reef, expected = reef_with_polips

        all_polips = reef.all()
        assert len(all_polips) == len(expected)

        ids = {p.id for p in all_polips}
        expected_ids = {p.id for p in expected}
        assert ids == expected_ids

    def test_get_by_id(self, reef_with_polips):
        """Verify exact ID lookup works."""
        reef, _ = reef_with_polips

        polip = reef.get("auth-system")
        assert polip is not None
        assert polip.id == "auth-system"
        assert "JWT" in polip.summary

    def test_filter_by_type(self, reef_with_polips):
        """Verify type filtering works."""
        reef, _ = reef_with_polips

        threads = reef.by_type("thread")
        assert len(threads) == 2

        constraints = reef.by_type("constraint")
        assert len(constraints) == 1

        contexts = reef.by_type("context")
        assert len(contexts) == 2

    def test_active_threads(self, reef_with_polips):
        """Verify active thread detection."""
        reef, _ = reef_with_polips

        active = reef.active_threads()
        assert len(active) == 2
        assert all(t.status == "active" for t in active)

    def test_constraints_always_surface(self, reef_with_polips):
        """Verify constraints are easily retrievable."""
        reef, _ = reef_with_polips

        constraints = reef.constraints()
        assert len(constraints) == 1
        assert constraints[0].id == "no-secrets"


class TestSearchGroundTruth:
    """Test search against known expected results."""

    @pytest.fixture
    def indexed_reef(self):
        """Create reef with TF-IDF index built."""
        from reef.blob import Glob

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()

            # Create polips as XML for Glob compatibility
            create_test_reef_xml(reef_dir)

            # Use Glob for TF-IDF search
            glob = Glob(root)
            glob.rebuild_index()

            yield glob, root

    @pytest.mark.parametrize("query,expected_ids", SEARCH_GROUND_TRUTH)
    def test_search_returns_expected(self, indexed_reef, query, expected_ids):
        """Verify search returns expected polips."""
        glob, root = indexed_reef
        # search_index returns list of (key, entry, score) tuples
        results = glob.search_index(query=query, limit=3)

        if not expected_ids:
            # Negative case: should return no results or low scores
            if results:
                # If we get results, they should have low relevance
                top_score = results[0][2] if results else 0
                assert top_score < 0.3, f"Query '{query}' matched unexpectedly"
        else:
            # Positive case: expected polips should be in results
            # Keys are like "threads/auth-system" or "contexts/db-schema"
            result_ids = [key.split("/")[-1] if "/" in key else key
                         for key, entry, score in results]

            # At least the top expected should be in results
            top_expected = expected_ids[0]
            assert any(top_expected in rid for rid in result_ids), \
                f"Query '{query}' should find '{top_expected}', got {result_ids}"


class TestSearchPerformance:
    """Measure search performance characteristics."""

    @pytest.fixture
    def large_reef(self):
        """Create reef with many polips for performance testing."""
        from reef.blob import Glob, Blob, BlobType, BlobScope

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()

            types = [BlobType.THREAD, BlobType.CONTEXT, BlobType.DECISION, BlobType.CONSTRAINT]
            scopes = [BlobScope.ALWAYS, BlobScope.PROJECT, BlobScope.SESSION]
            subdirs = ["threads", "contexts", "decisions", "constraints"]

            # Create 100 polips with varied content as XML
            for i in range(100):
                blob = Blob(
                    type=types[i % 4],
                    scope=scopes[i % 3],
                    summary=f"Test polip number {i} for performance benchmarking",
                )
                blob.facts = [f"Fact {j} for polip {i}" for j in range(i % 5)]

                subdir = reef_dir / subdirs[i % 4]
                subdir.mkdir(exist_ok=True)
                path = subdir / f"polip-{i:03d}.blob.xml"
                blob.save(path)

            glob = Glob(root)
            glob.rebuild_index()

            yield glob

    def test_index_build_time(self, large_reef):
        """Measure index build time."""
        import time

        start = time.perf_counter()
        large_reef.rebuild_index()
        elapsed = time.perf_counter() - start

        print(f"\nIndex build time (100 polips): {elapsed*1000:.1f}ms")
        assert elapsed < 1.0, "Index build should be under 1 second"

    def test_search_time(self, large_reef):
        """Measure search time."""
        import time

        queries = ["test polip", "performance", "context line", "fact decision"]

        times = []
        for query in queries:
            start = time.perf_counter()
            _ = large_reef.search_index(query=query, limit=10)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_ms = (sum(times) / len(times)) * 1000
        print(f"\nAverage search time (100 polips): {avg_ms:.2f}ms")
        assert avg_ms < 100, "Search should be under 100ms"

    def test_retrieval_all_time(self, large_reef):
        """Measure time to load all polips."""
        import time

        start = time.perf_counter()
        all_blobs = large_reef.list_blobs()
        elapsed = time.perf_counter() - start

        print(f"\nLoad all time (100 polips): {elapsed*1000:.1f}ms")
        print(f"Polips loaded: {len(all_blobs)}")
        assert elapsed < 0.5, "Loading all polips should be under 500ms"
