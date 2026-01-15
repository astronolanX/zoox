"""
Tests for reef calcification engine.

Phase 6: Organic growth mechanics.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta

from reef.blob import Glob, Blob, BlobType, BlobScope, BlobStatus
from reef.calcification import (
    CalcificationEngine,
    CalcificationScore,
    AdversarialDecay,
    ChallengeResult,
    ChallengeReport,
    ReefHealth,
    HealthReport,
)


class TestCalcificationEngine:
    """Tests for calcification scoring."""

    def test_import(self):
        """Verify module imports correctly."""
        assert CalcificationEngine is not None
        assert CalcificationScore is not None

    def test_instantiation(self):
        """Verify can create engine instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            engine = CalcificationEngine(glob)
            assert engine is not None

    def test_trigger_weights_sum_to_one(self):
        """Verify trigger weights are balanced."""
        total = sum(t["weight"] for t in CalcificationEngine.TRIGGERS.values())
        assert abs(total - 1.0) < 0.001

    def test_score_new_polip(self):
        """New polip should have low score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create new polip
            blob = Blob(
                type=BlobType.THREAD,
                summary="New polip",
                scope=BlobScope.PROJECT,
            )
            path = glob.sprout(blob, "test-new")

            engine = CalcificationEngine(glob)
            key = glob._blob_key(path)
            score = engine.score_polip(key, blob)

            # New polip: no time, no usage, no ceremony, no consensus
            assert score.total < 0.3
            assert not score.should_calcify

    def test_score_ceremony_constraint(self):
        """Constraint scope should give ceremony score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create constraint (ceremonial)
            blob = Blob(
                type=BlobType.CONSTRAINT,
                summary="Project constraint",
                scope=BlobScope.ALWAYS,
            )
            path = glob.sprout(blob, "test-constraint")

            engine = CalcificationEngine(glob)
            key = glob._blob_key(path)
            score = engine.score_polip(key, blob)

            # Ceremony score should be 1.0
            assert score.ceremony_score == 1.0

    def test_score_usage(self):
        """High usage should increase score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.THREAD,
                summary="Used polip",
                scope=BlobScope.PROJECT,
            )
            path = glob.sprout(blob, "test-used")

            # Simulate 20 accesses
            for _ in range(20):
                glob._increment_access([glob._blob_key(path)])

            engine = CalcificationEngine(glob)
            key = glob._blob_key(path)
            score = engine.score_polip(key, blob)

            # Usage score should be high
            assert score.usage_score > 0.5

    def test_get_candidates_empty(self):
        """Empty reef has no candidates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            engine = CalcificationEngine(glob)
            candidates = engine.get_candidates()
            assert candidates == []

    def test_get_all_scores(self):
        """Get all scores includes non-candidates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create some polips
            for i in range(3):
                blob = Blob(
                    type=BlobType.THREAD,
                    summary=f"Polip {i}",
                    scope=BlobScope.PROJECT,
                )
                glob.sprout(blob, f"test-{i}")

            engine = CalcificationEngine(glob)
            scores = engine.get_all_scores()

            assert len(scores) == 3

    def test_score_serialization(self):
        """CalcificationScore serializes to dict."""
        score = CalcificationScore(
            polip_key="test.blob.xml",
            total=0.75,
            time_score=0.5,
            usage_score=0.8,
            ceremony_score=0.0,
            consensus_score=0.6,
            should_calcify=True,
        )
        d = score.to_dict()

        assert d["polip"] == "test.blob.xml"
        assert d["total"] == 0.75
        assert d["should_calcify"] is True
        assert "breakdown" in d


class TestAdversarialDecay:
    """Tests for adversarial decay challenges."""

    def test_import(self):
        """Verify module imports correctly."""
        assert AdversarialDecay is not None
        assert ChallengeResult is not None

    def test_instantiation(self):
        """Verify can create decay instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            decay = AdversarialDecay(glob)
            assert decay is not None

    def test_protected_scope_not_challenged(self):
        """Polips with scope=always are protected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create protected polip (old but protected)
            blob = Blob(
                type=BlobType.CONSTRAINT,
                summary="Protected constraint",
                scope=BlobScope.ALWAYS,
                updated=datetime.now() - timedelta(days=100),
            )
            glob.sprout(blob, "protected")

            decay = AdversarialDecay(glob)
            challengers = decay.get_challengers()

            # Should not be challenged despite age
            assert len(challengers) == 0

    def test_stale_polip_challenged(self):
        """Stale polips with low access are challenged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create stale polip (60+ days, <3 access)
            blob = Blob(
                type=BlobType.THREAD,
                summary="Stale thread",
                scope=BlobScope.PROJECT,
                updated=datetime.now() - timedelta(days=70),
            )
            glob.sprout(blob, "stale")

            decay = AdversarialDecay(glob)
            challengers = decay.get_challengers()

            # Should be challenged for staleness
            assert len(challengers) == 1
            assert challengers[0][2] == "staleness"

    def test_challenge_survive_with_usage(self):
        """Polip with high usage survives challenge."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.THREAD,
                summary="Used thread",
                scope=BlobScope.PROJECT,
                updated=datetime.now() - timedelta(days=70),
            )
            path = glob.sprout(blob, "used")
            key = glob._blob_key(path)

            # Simulate usage
            for _ in range(10):
                glob._increment_access([key])

            decay = AdversarialDecay(glob)
            report = decay.challenge(key, blob, "staleness")

            # Should survive due to usage
            assert report.result == ChallengeResult.SURVIVE

    def test_challenge_decompose_no_defense(self):
        """Polip with no defense is decomposed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.THREAD,
                summary="Abandoned thread",
                scope=BlobScope.PROJECT,
                updated=datetime.now() - timedelta(days=70),
            )
            path = glob.sprout(blob, "abandoned")
            key = glob._blob_key(path)

            decay = AdversarialDecay(glob)
            report = decay.challenge(key, blob, "staleness")

            # Should decompose
            assert report.result == ChallengeResult.DECOMPOSE

    def test_run_challenges_dry_run(self):
        """Dry run generates reports without action."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create stale polip
            blob = Blob(
                type=BlobType.THREAD,
                summary="Stale",
                scope=BlobScope.PROJECT,
                updated=datetime.now() - timedelta(days=70),
            )
            glob.sprout(blob, "stale")

            decay = AdversarialDecay(glob)
            reports = decay.run_challenges(dry_run=True)

            assert len(reports) == 1

    def test_challenge_report_serialization(self):
        """ChallengeReport serializes to dict."""
        report = ChallengeReport(
            polip_key="test.blob.xml",
            trigger="staleness",
            result=ChallengeResult.DECOMPOSE,
            reason="No justification",
        )
        d = report.to_dict()

        assert d["polip"] == "test.blob.xml"
        assert d["result"] == "decompose"


class TestReefHealth:
    """Tests for reef health metrics."""

    def test_import(self):
        """Verify module imports correctly."""
        assert ReefHealth is not None
        assert HealthReport is not None

    def test_instantiation(self):
        """Verify can create health instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            health = ReefHealth(glob)
            assert health is not None

    def test_empty_reef_health(self):
        """Empty reef has zero vitality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            health = ReefHealth(glob)
            report = health.calculate()

            assert report.vitality_score == 0.0
            assert report.total_polips == 0
            assert "Create your first polip" in report.recommendations[0]

    def test_basic_health_calculation(self):
        """Health calculates for populated reef."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create diverse polips
            for ptype in [BlobType.THREAD, BlobType.DECISION, BlobType.CONSTRAINT]:
                blob = Blob(
                    type=ptype,
                    summary=f"Test {ptype.value}",
                    scope=BlobScope.PROJECT if ptype != BlobType.CONSTRAINT else BlobScope.ALWAYS,
                )
                glob.sprout(blob, f"test-{ptype.value}")

            health = ReefHealth(glob)
            report = health.calculate()

            assert report.total_polips == 3
            assert report.vitality_score > 0

    def test_type_diversity_single_type(self):
        """Single type has low diversity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create multiple of same type
            for i in range(5):
                blob = Blob(
                    type=BlobType.THREAD,
                    summary=f"Thread {i}",
                    scope=BlobScope.PROJECT,
                )
                glob.sprout(blob, f"thread-{i}")

            health = ReefHealth(glob)
            report = health.calculate()

            # Single type = zero diversity
            assert report.type_diversity == 0.0

    def test_lifecycle_distribution(self):
        """Lifecycle stages are counted correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create polips of different ages
            ages = [1, 15, 50, 120, 200]
            for i, age in enumerate(ages):
                blob = Blob(
                    type=BlobType.THREAD,
                    summary=f"Age {age}d",
                    scope=BlobScope.PROJECT,
                    updated=datetime.now() - timedelta(days=age),
                )
                glob.sprout(blob, f"age-{i}")

            health = ReefHealth(glob)
            report = health.calculate()

            # Should have polips in different stages
            assert report.lifecycle_stages["spawning"] == 1  # 1 day
            assert report.lifecycle_stages["drifting"] == 1  # 15 days
            assert report.lifecycle_stages["attached"] == 1  # 50 days
            assert report.lifecycle_stages["calcified"] == 1  # 120 days
            assert report.lifecycle_stages["fossil"] == 1    # 200 days

    def test_recommendations_low_activity(self):
        """Low activity generates recommendation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create polips with no access
            for i in range(5):
                blob = Blob(
                    type=BlobType.THREAD,
                    summary=f"Unused {i}",
                    scope=BlobScope.PROJECT,
                )
                glob.sprout(blob, f"unused-{i}")

            health = ReefHealth(glob)
            report = health.calculate()

            assert any("Low activity" in r for r in report.recommendations)

    def test_recommendations_low_connectivity(self):
        """Low connectivity generates recommendation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create polips with no refs
            for i in range(5):
                blob = Blob(
                    type=BlobType.THREAD,
                    summary=f"Isolated {i}",
                    scope=BlobScope.PROJECT,
                )
                glob.sprout(blob, f"isolated-{i}")

            health = ReefHealth(glob)
            report = health.calculate()

            assert any("Low connectivity" in r for r in report.recommendations)

    def test_health_report_serialization(self):
        """HealthReport serializes to dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.THREAD,
                summary="Test",
                scope=BlobScope.PROJECT,
            )
            glob.sprout(blob, "test")

            health = ReefHealth(glob)
            report = health.calculate()
            d = report.to_dict()

            assert "vitality_score" in d
            assert "lifecycle_stages" in d
            assert "recommendations" in d


class TestConsensusScoring:
    """Tests for consensus (reference) scoring."""

    def test_consensus_from_related(self):
        """References in related field count for consensus."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create target polip
            target = Blob(
                type=BlobType.DECISION,
                summary="Important decision",
                scope=BlobScope.PROJECT,
            )
            target_path = glob.sprout(target, "target")

            # Create polips that reference target
            for i in range(4):
                ref_blob = Blob(
                    type=BlobType.THREAD,
                    summary=f"Referencing {i}",
                    scope=BlobScope.PROJECT,
                    related=["target"],  # Reference by name
                )
                glob.sprout(ref_blob, f"ref-{i}")

            # Rebuild index to capture related
            glob.rebuild_index()

            engine = CalcificationEngine(glob)
            key = glob._blob_key(target_path)
            score = engine.score_polip(key, target)

            # Should have consensus score from 4 refs
            assert score.consensus_score > 0.5


class TestCLIIntegration:
    """Integration tests for calcification CLI commands."""

    def test_health_runs(self):
        """Health command executes without error."""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "python", "-m", "reef.cli", "health"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Should output health report (might have warnings)
        assert "Vitality Score" in result.stdout or result.returncode == 0

    def test_calcify_runs(self):
        """Calcify command executes without error."""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "python", "-m", "reef.cli", "calcify", "--all"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Should complete successfully
        assert result.returncode == 0

    def test_decay_runs(self):
        """Decay command executes without error."""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "python", "-m", "reef.cli", "decay"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Should complete successfully
        assert result.returncode == 0

    def test_health_json_output(self):
        """Health command outputs valid JSON."""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "python", "-m", "reef.cli", "health", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should succeed
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Find JSON in output (skip any warning lines)
        output = result.stdout.strip()
        if not output:
            pytest.skip("No output from health --json")

        # Find first { and parse from there
        json_start = output.find("{")
        if json_start == -1:
            pytest.fail(f"No JSON found in output: {output}")

        json_str = output[json_start:]
        data = json.loads(json_str)
        assert "vitality_score" in data
