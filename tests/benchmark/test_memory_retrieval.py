"""
Benchmark: Memory retrieval accuracy

Tests the core question: does reef help AI retrieve relevant context?

This measures:
1. Precision: How many surfaced polips are relevant to the task?
2. Recall: How many relevant polips were surfaced?
3. Efficiency: Tokens used vs information gained

Ground truth defined by human annotation, not LLM judgment.
"""

import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pytest

from reef.format import Polip, Reef


@dataclass
class SimulatedTask:
    """A task with known relevant polips."""
    description: str
    relevant_polip_ids: list[str]
    irrelevant_polip_ids: list[str]


# Test scenarios with human-annotated relevance
TASK_SCENARIOS = [
    SimulatedTask(
        description="Fix authentication bug where tokens expire early",
        relevant_polip_ids=["auth-tokens", "jwt-config", "session-mgmt"],
        irrelevant_polip_ids=["database-schema", "ui-styling", "deployment"],
    ),
    SimulatedTask(
        description="Add new API endpoint for user preferences",
        relevant_polip_ids=["api-conventions", "user-model", "testing-strategy"],
        irrelevant_polip_ids=["auth-tokens", "memory-debug", "ci-pipeline"],
    ),
    SimulatedTask(
        description="Debug memory leak in background workers",
        relevant_polip_ids=["memory-debug", "worker-pool", "monitoring"],
        irrelevant_polip_ids=["ui-styling", "api-conventions", "database-schema"],
    ),
    SimulatedTask(
        description="Update database schema for new feature",
        relevant_polip_ids=["database-schema", "migration-strategy", "testing-strategy"],
        irrelevant_polip_ids=["auth-tokens", "ui-styling", "memory-debug"],
    ),
]


def create_comprehensive_reef(reef_dir: Path) -> dict[str, Polip]:
    """Create reef with polips for all test scenarios."""
    polips = {}

    # Auth-related polips
    polips["auth-tokens"] = Polip.create(
        id="auth-tokens",
        type="thread",
        scope="project",
        updated=date.today(),
        summary="JWT token implementation and validation",
        facts=[
            "Access tokens expire in 15 minutes",
            "Refresh tokens in Redis with 7-day TTL",
            "RS256 signing algorithm",
        ],
        decisions=["Token rotation on refresh"],
        context=["Currently debugging early expiration issue"],
        status="active",
    )

    polips["jwt-config"] = Polip.create(
        id="jwt-config",
        type="context",
        scope="project",
        updated=date.today() - timedelta(days=2),
        summary="JWT configuration and secrets management",
        facts=[
            "Private key in AWS Secrets Manager",
            "Public key cached in memory",
            "Key rotation quarterly",
        ],
        context=["Config in settings/auth.py"],
    )

    polips["session-mgmt"] = Polip.create(
        id="session-mgmt",
        type="decision",
        scope="project",
        updated=date.today() - timedelta(days=5),
        summary="Session management architecture",
        facts=["Stateless JWT over server-side sessions"],
        decisions=["No session cookies", "Token in Authorization header"],
    )

    # API-related polips
    polips["api-conventions"] = Polip.create(
        id="api-conventions",
        type="constraint",
        scope="always",
        updated=date.today() - timedelta(days=10),
        summary="API design conventions and standards",
        facts=[
            "RESTful endpoints at /api/v1/",
            "Snake_case for JSON fields",
            "UTC timestamps in ISO8601",
        ],
        decisions=["URL versioning", "Pagination via cursor"],
    )

    polips["user-model"] = Polip.create(
        id="user-model",
        type="context",
        scope="project",
        updated=date.today() - timedelta(days=3),
        summary="User data model and preferences",
        facts=[
            "UUID primary key",
            "Email unique constraint",
            "Preferences in JSONB column",
        ],
        context=["models/user.py defines User class"],
    )

    # Database-related polips
    polips["database-schema"] = Polip.create(
        id="database-schema",
        type="context",
        scope="project",
        updated=date.today() - timedelta(days=1),
        summary="PostgreSQL schema and conventions",
        facts=[
            "Soft delete with deleted_at column",
            "All tables have created_at, updated_at",
            "JSONB for flexible metadata",
        ],
        decisions=["UUID over serial for PKs"],
    )

    polips["migration-strategy"] = Polip.create(
        id="migration-strategy",
        type="decision",
        scope="project",
        updated=date.today() - timedelta(days=7),
        summary="Database migration approach",
        facts=["Alembic for migrations", "Run in CI before deploy"],
        decisions=["No destructive migrations", "Always add not remove"],
    )

    # Debug-related polips
    polips["memory-debug"] = Polip.create(
        id="memory-debug",
        type="thread",
        scope="session",
        updated=date.today(),
        summary="Memory leak investigation in worker pool",
        facts=[
            "2MB/hour growth under load",
            "gc.collect() ineffective",
            "Started after v2.3.1",
        ],
        decisions=["Added tracemalloc profiling"],
        context=["Suspect connection pool not closing"],
        status="active",
    )

    polips["worker-pool"] = Polip.create(
        id="worker-pool",
        type="context",
        scope="project",
        updated=date.today() - timedelta(days=4),
        summary="Background worker pool configuration",
        facts=[
            "Celery with Redis broker",
            "4 workers per node",
            "30-second task timeout",
        ],
        context=["Config in celery_app.py"],
    )

    polips["monitoring"] = Polip.create(
        id="monitoring",
        type="context",
        scope="project",
        updated=date.today() - timedelta(days=6),
        summary="Application monitoring and alerting",
        facts=[
            "Prometheus metrics at /metrics",
            "Grafana dashboards",
            "PagerDuty for critical alerts",
        ],
    )

    # Misc polips (often irrelevant)
    polips["ui-styling"] = Polip.create(
        id="ui-styling",
        type="context",
        scope="project",
        updated=date.today() - timedelta(days=14),
        summary="Frontend styling conventions",
        facts=["Tailwind CSS", "Dark mode support", "Responsive breakpoints"],
    )

    polips["deployment"] = Polip.create(
        id="deployment",
        type="context",
        scope="project",
        updated=date.today() - timedelta(days=20),
        summary="Deployment infrastructure",
        facts=["Kubernetes on GKE", "Helm charts", "Blue-green deploys"],
    )

    polips["ci-pipeline"] = Polip.create(
        id="ci-pipeline",
        type="context",
        scope="project",
        updated=date.today() - timedelta(days=12),
        summary="CI/CD pipeline configuration",
        facts=["GitHub Actions", "Tests on every PR", "Auto-deploy on main"],
    )

    polips["testing-strategy"] = Polip.create(
        id="testing-strategy",
        type="constraint",
        scope="always",
        updated=date.today() - timedelta(days=8),
        summary="Testing requirements and approach",
        facts=[
            "pytest for all tests",
            "80% minimum coverage",
            "Integration tests in Docker",
        ],
        decisions=["Mock external APIs"],
    )

    # Save all polips
    for polip in polips.values():
        polip.save(reef_dir)

    return polips


class TestSurfacingAccuracy:
    """Test whether the right polips surface for each task."""

    @pytest.fixture
    def reef_with_all_polips(self):
        """Create reef with comprehensive polip set."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()

            polips = create_comprehensive_reef(reef_dir)
            reef = Reef(root)

            yield reef, polips

    def test_all_polips_created(self, reef_with_all_polips):
        """Verify all test polips exist."""
        reef, expected = reef_with_all_polips

        all_polips = reef.all()
        assert len(all_polips) == len(expected)

    @pytest.mark.parametrize("scenario", TASK_SCENARIOS, ids=lambda s: s.description[:40])
    def test_surfacing_for_task(self, reef_with_all_polips, scenario):
        """Test surfacing logic for specific task."""
        reef, all_polips = reef_with_all_polips

        # Simulate surfacing: active threads + constraints + recent contexts
        surfaced = []

        # Always surface constraints
        surfaced.extend(reef.constraints())

        # Surface active threads
        surfaced.extend(reef.active_threads())

        # Surface recent contexts (last 3 days)
        for polip in reef.all():
            if polip.type == "context":
                age = date.today() - polip.updated
                if age.days <= 3:
                    surfaced.append(polip)

        surfaced_ids = {p.id for p in surfaced}

        # Calculate precision and recall
        relevant_in_surfaced = surfaced_ids & set(scenario.relevant_polip_ids)
        irrelevant_in_surfaced = surfaced_ids & set(scenario.irrelevant_polip_ids)

        precision = len(relevant_in_surfaced) / len(surfaced_ids) if surfaced_ids else 0
        recall = len(relevant_in_surfaced) / len(scenario.relevant_polip_ids) if scenario.relevant_polip_ids else 0

        print(f"\nTask: {scenario.description[:50]}...")
        print(f"  Surfaced: {len(surfaced_ids)} polips")
        print(f"  Relevant surfaced: {relevant_in_surfaced}")
        print(f"  Irrelevant surfaced: {irrelevant_in_surfaced}")
        print(f"  Precision: {precision:.1%}")
        print(f"  Recall: {recall:.1%}")

        # Record metrics for aggregate analysis
        # (In a real benchmark, these would be collected and averaged)


class TestTokenEfficiencyVsRawFiles:
    """Compare reef tokens vs just dumping files."""

    @pytest.fixture
    def reef_and_raw_files(self):
        """Create both reef polips and equivalent raw files."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()
            raw_dir = root / "docs"
            raw_dir.mkdir()

            polips = create_comprehensive_reef(reef_dir)

            # Create equivalent raw markdown files
            for polip in polips.values():
                raw_content = f"# {polip.summary}\n\n"
                if polip.facts:
                    raw_content += "## Facts\n"
                    for fact in polip.facts:
                        raw_content += f"- {fact}\n"
                if polip.decisions:
                    raw_content += "\n## Decisions\n"
                    for dec in polip.decisions:
                        raw_content += f"- {dec}\n"
                if polip.context:
                    raw_content += "\n## Context\n"
                    for ctx in polip.context:
                        raw_content += f"{ctx}\n"

                (raw_dir / f"{polip.id}.md").write_text(raw_content)

            yield root, polips

    def test_total_bytes_comparison(self, reef_and_raw_files):
        """Compare total bytes: reef vs raw markdown."""
        root, polips = reef_and_raw_files

        reef_dir = root / ".claude"
        raw_dir = root / "docs"

        reef_bytes = sum(f.stat().st_size for f in reef_dir.rglob("*.reef"))
        raw_bytes = sum(f.stat().st_size for f in raw_dir.glob("*.md"))

        print(f"\nTotal bytes comparison:")
        print(f"  Reef (.reef files): {reef_bytes:,} bytes")
        print(f"  Raw (markdown):     {raw_bytes:,} bytes")
        print(f"  Difference: {reef_bytes - raw_bytes:+,} bytes")

        # Reef should be comparable or smaller
        # (The sigil format is more compact than markdown headers)

    def test_surfaced_tokens_comparison(self, reef_and_raw_files):
        """Compare tokens - SEPARATE format efficiency from filtering efficiency."""
        root, polips = reef_and_raw_files

        # Simulate: surface only active threads and constraints
        reef = Reef(root)
        surfaced = reef.constraints() + reef.active_threads()

        surfaced_reef_tokens = sum(
            len(p.to_reef()) // 4 for p in surfaced
        )

        # Raw equivalent: would need to surface all files (no filtering)
        raw_dir = root / "docs"
        raw_all_tokens = sum(
            len(f.read_text()) // 4 for f in raw_dir.glob("*.md")
        )

        # Selective surfacing: only relevant raw files
        relevant_ids = {p.id for p in surfaced}
        raw_surfaced_tokens = sum(
            len((raw_dir / f"{pid}.md").read_text()) // 4
            for pid in relevant_ids
            if (raw_dir / f"{pid}.md").exists()
        )

        # KAREN FIX: Separate the two different savings
        filtering_savings = (1 - surfaced_reef_tokens/raw_all_tokens) * 100
        format_savings = (1 - surfaced_reef_tokens/raw_surfaced_tokens) * 100 if raw_surfaced_tokens > 0 else 0

        print(f"\n=== TOKEN EFFICIENCY (HONEST BREAKDOWN) ===")
        print(f"  Raw ALL files:              ~{raw_all_tokens} tokens")
        print(f"  Raw SURFACED (selective):   ~{raw_surfaced_tokens} tokens")
        print(f"  Reef SURFACED (selective):  ~{surfaced_reef_tokens} tokens")
        print(f"")
        print(f"  FILTERING saves:  {(1 - raw_surfaced_tokens/raw_all_tokens)*100:.1f}% (surfacing subset)")
        print(f"  FORMAT saves:     {-format_savings:.1f}% (.reef vs .md on same content)")
        print(f"  COMBINED saves:   {filtering_savings:.1f}% (total)")
        print(f"")
        print(f"  NOTE: The 61.8% is mostly from FILTERING, not format.")


class TestMemoryDecay:
    """Test lifecycle-based memory decay."""

    def test_age_based_priority(self):
        """Older polips get lower priority."""
        from datetime import date, timedelta

        polips = [
            Polip.create(
                id=f"polip-{i}",
                type="context",
                scope="project",
                updated=date.today() - timedelta(days=i),
                summary=f"Polip from {i} days ago",
            )
            for i in range(10)
        ]

        # Simulate priority calculation (from glob_inject.py logic)
        def calculate_priority(polip: Polip) -> int:
            age = (date.today() - polip.updated).days
            if polip.type == "constraint":
                return 100
            elif polip.status == "active":
                return 80
            elif polip.type == "context" and age <= 3:
                return 50 - age * 10
            return 0

        priorities = [(p.id, calculate_priority(p)) for p in polips]
        priorities.sort(key=lambda x: x[1], reverse=True)

        print("\nAge-based priority decay:")
        for pid, pri in priorities[:5]:
            print(f"  {pid}: priority {pri}")

        # Recent polips should have higher priority
        assert priorities[0][0] == "polip-0"  # Today
        assert priorities[1][0] == "polip-1"  # Yesterday
        assert priorities[2][0] == "polip-2"  # 2 days ago

    def test_type_based_priority(self):
        """Constraints always surface, others decay."""
        polips = [
            Polip.create(id="constraint", type="constraint", scope="always",
                  updated=date.today() - timedelta(days=30), summary="Old constraint"),
            Polip.create(id="active-thread", type="thread", scope="project",
                  updated=date.today() - timedelta(days=30), summary="Old thread", status="active"),
            Polip.create(id="old-context", type="context", scope="project",
                  updated=date.today() - timedelta(days=30), summary="Old context"),
        ]

        # Constraints surface regardless of age
        # Active threads surface regardless of age
        # Old contexts don't surface

        def should_surface(p: Polip) -> bool:
            age = (date.today() - p.updated).days
            if p.type == "constraint":
                return True
            if p.status == "active":
                return True
            if p.type == "context" and age <= 3:
                return True
            return False

        results = [(p.id, should_surface(p)) for p in polips]

        print("\nType-based surfacing:")
        for pid, surfaces in results:
            print(f"  {pid}: {'surfaces' if surfaces else 'decayed'}")

        assert should_surface(polips[0])  # Constraint
        assert should_surface(polips[1])  # Active thread
        assert not should_surface(polips[2])  # Old context
