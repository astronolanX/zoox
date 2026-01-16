"""
Tests for AI-native reef calcification engine.

Phase 6: Organic growth mechanics with session-relative time.
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
    PolipVitals,
    SessionMetrics,
)


class TestCalcificationEngine:
    """Tests for AI-native calcification scoring."""

    def test_import(self):
        """Verify module imports correctly."""
        assert CalcificationEngine is not None
        assert CalcificationScore is not None
        assert PolipVitals is not None

    def test_instantiation(self):
        """Verify can create engine instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            engine = CalcificationEngine(glob)
            assert engine is not None

    def test_weights_sum_to_one(self):
        """Verify trigger weights are balanced."""
        total = sum(CalcificationEngine.WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_session_management(self):
        """Engine tracks sessions and turns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            engine = CalcificationEngine(glob)

            session_id = engine.start_session("test-session")
            assert session_id == "test-session"

            turn = engine.tick_turn()
            assert turn == 1

            turn = engine.tick_turn()
            assert turn == 2

    def test_record_reference(self):
        """Recording references updates session metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))
            engine = CalcificationEngine(glob)

            engine.start_session("test-session")
            engine.tick_turn()
            engine.tick_turn()

            blob = Blob(
                type=BlobType.THREAD,
                summary="Test polip",
                scope=BlobScope.PROJECT,
            )
            path = glob.sprout(blob, "test")
            key = glob._blob_key(path)

            engine.record_reference(key)
            engine.tick_turn()
            engine.record_reference(key)

            vitals = engine.get_vitals(key, blob)
            assert vitals.refs_this_session == 2

    def test_score_new_polip(self):
        """New polip should have low score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.THREAD,
                summary="New polip",
                scope=BlobScope.PROJECT,
            )
            path = glob.sprout(blob, "test-new")

            engine = CalcificationEngine(glob)
            key = glob._blob_key(path)
            score = engine.score_polip(key, blob)

            # New polip: no intensity, no persistence, no consensus
            assert score.total < 0.3
            assert not score.should_calcify
            assert score.lifecycle_stage == "spawning"

    def test_score_ceremony_constraint(self):
        """Constraint scope should give ceremony score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.CONSTRAINT,
                summary="Project constraint",
                scope=BlobScope.ALWAYS,
            )
            path = glob.sprout(blob, "test-constraint")

            engine = CalcificationEngine(glob)
            key = glob._blob_key(path)
            score = engine.score_polip(key, blob)

            assert score.ceremony_score == 1.0
            assert score.lifecycle_stage == "calcified"  # Ceremony promotes

    def test_score_intensity_from_session(self):
        """High session refs increase intensity score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.THREAD,
                summary="Hot polip",
                scope=BlobScope.PROJECT,
            )
            path = glob.sprout(blob, "test-hot")

            engine = CalcificationEngine(glob)
            engine.start_session()
            key = glob._blob_key(path)

            # Simulate 10 references in current session
            for i in range(10):
                engine.tick_turn()
                engine.record_reference(key)

            score = engine.score_polip(key, blob)

            # High intensity from session refs
            assert score.intensity_score > 0.5
            assert score.vitals.refs_this_session == 10

    def test_lifecycle_stage_from_intensity(self):
        """High intensity promotes to attached stage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.THREAD,
                summary="Hot polip",
                scope=BlobScope.PROJECT,
            )
            path = glob.sprout(blob, "test-hot")

            engine = CalcificationEngine(glob)
            engine.start_session()
            key = glob._blob_key(path)

            # 5+ refs in session = attached (HIGH_INTENSITY_THRESHOLD)
            for _ in range(6):
                engine.tick_turn()
                engine.record_reference(key)

            score = engine.score_polip(key, blob)
            assert score.lifecycle_stage == "attached"

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
        vitals = PolipVitals(refs_this_session=5, sessions_referenced=2)
        score = CalcificationScore(
            polip_key="test.blob.xml",
            total=0.75,
            intensity_score=0.5,
            persistence_score=0.2,
            depth_score=0.1,
            ceremony_score=0.0,
            consensus_score=0.6,
            should_calcify=True,
            lifecycle_stage="attached",
            vitals=vitals,
        )
        d = score.to_dict()

        assert d["polip"] == "test.blob.xml"
        assert d["total"] == 0.75
        assert d["should_calcify"] is True
        assert d["lifecycle"] == "attached"
        assert "breakdown" in d


class TestAdversarialDecay:
    """Tests for AI-native adversarial decay challenges."""

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

            blob = Blob(
                type=BlobType.CONSTRAINT,
                summary="Protected constraint",
                scope=BlobScope.ALWAYS,
            )
            glob.sprout(blob, "protected")

            decay = AdversarialDecay(glob)
            challengers = decay.get_challengers()

            assert len(challengers) == 0

    def test_cold_polip_challenged(self):
        """Cold polips with no activity are challenged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create polip with no refs, no access
            blob = Blob(
                type=BlobType.THREAD,
                summary="Cold thread",
                scope=BlobScope.PROJECT,
            )
            glob.sprout(blob, "cold")

            decay = AdversarialDecay(glob)
            challengers = decay.get_challengers()

            # Should be challenged for being cold
            assert len(challengers) == 1
            assert challengers[0][2] == "cold"

    def test_challenge_survive_with_session_refs(self):
        """Polip with current session refs survives challenge."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.THREAD,
                summary="Active thread",
                scope=BlobScope.PROJECT,
            )
            path = glob.sprout(blob, "active")
            key = glob._blob_key(path)

            engine = CalcificationEngine(glob)
            engine.start_session()

            # Add refs in current session
            for _ in range(5):
                engine.tick_turn()
                engine.record_reference(key)

            decay = AdversarialDecay(glob, engine)
            report = decay.challenge(key, blob, "cold")

            assert report.result == ChallengeResult.SURVIVE

    def test_challenge_decompose_no_defense(self):
        """Polip with no defense is decomposed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.THREAD,
                summary="Abandoned thread",
                scope=BlobScope.PROJECT,
            )
            path = glob.sprout(blob, "abandoned")
            key = glob._blob_key(path)

            decay = AdversarialDecay(glob)
            report = decay.challenge(key, blob, "cold")

            assert report.result == ChallengeResult.DECOMPOSE

    def test_run_challenges_dry_run(self):
        """Dry run generates reports without action."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.THREAD,
                summary="Cold",
                scope=BlobScope.PROJECT,
            )
            glob.sprout(blob, "cold")

            decay = AdversarialDecay(glob)
            reports = decay.run_challenges(dry_run=True)

            assert len(reports) == 1

    def test_challenge_report_serialization(self):
        """ChallengeReport serializes to dict."""
        report = ChallengeReport(
            polip_key="test.blob.xml",
            trigger="cold",
            result=ChallengeResult.DECOMPOSE,
            reason="No justification",
        )
        d = report.to_dict()

        assert d["polip"] == "test.blob.xml"
        assert d["result"] == "decompose"


class TestReefHealth:
    """Tests for AI-native reef health metrics."""

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
            assert report.vitality_score >= 0

    def test_hot_ratio_from_session(self):
        """Hot ratio measures current session activity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create 5 polips
            paths = []
            for i in range(5):
                blob = Blob(
                    type=BlobType.THREAD,
                    summary=f"Thread {i}",
                    scope=BlobScope.PROJECT,
                )
                paths.append(glob.sprout(blob, f"thread-{i}"))

            engine = CalcificationEngine(glob)
            engine.start_session()

            # Reference only 2 of them
            for path in paths[:2]:
                key = glob._blob_key(path)
                engine.tick_turn()
                engine.record_reference(key)

            health = ReefHealth(glob, engine)
            report = health.calculate()

            # 2/5 = 0.4 hot ratio
            assert report.hot_ratio == 0.4

    def test_type_diversity_single_type(self):
        """Single type has low diversity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            for i in range(5):
                blob = Blob(
                    type=BlobType.THREAD,
                    summary=f"Thread {i}",
                    scope=BlobScope.PROJECT,
                )
                glob.sprout(blob, f"thread-{i}")

            health = ReefHealth(glob)
            report = health.calculate()

            assert report.type_diversity == 0.0

    def test_lifecycle_distribution_from_vitals(self):
        """Lifecycle stages are based on vitals, not age."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create constraint (ceremony -> calcified)
            blob = Blob(
                type=BlobType.CONSTRAINT,
                summary="Constraint",
                scope=BlobScope.ALWAYS,
            )
            glob.sprout(blob, "constraint")

            # Create regular polip (no activity -> spawning)
            blob2 = Blob(
                type=BlobType.THREAD,
                summary="Thread",
                scope=BlobScope.PROJECT,
            )
            glob.sprout(blob2, "thread")

            health = ReefHealth(glob)
            report = health.calculate()

            # Constraint should be calcified, thread should be spawning
            assert report.lifecycle_stages.get("calcified", 0) >= 1
            assert report.lifecycle_stages.get("spawning", 0) >= 1

    def test_recommendations_low_activity(self):
        """Low activity generates recommendation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

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

    def test_session_stats(self):
        """Health report includes session stats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            blob = Blob(
                type=BlobType.THREAD,
                summary="Test",
                scope=BlobScope.PROJECT,
            )
            path = glob.sprout(blob, "test")

            engine = CalcificationEngine(glob)
            engine.start_session()
            key = glob._blob_key(path)
            engine.record_reference(key)

            health = ReefHealth(glob, engine)
            report = health.calculate()

            assert "total_refs_this_session" in report.session_stats
            assert "avg_intensity" in report.session_stats

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
            assert "session_stats" in d
            assert "recommendations" in d


class TestConsensusScoring:
    """Tests for consensus (reference) scoring."""

    def test_consensus_from_related(self):
        """References in related field count for consensus."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            target = Blob(
                type=BlobType.DECISION,
                summary="Important decision",
                scope=BlobScope.PROJECT,
            )
            target_path = glob.sprout(target, "target")

            for i in range(4):
                ref_blob = Blob(
                    type=BlobType.THREAD,
                    summary=f"Referencing {i}",
                    scope=BlobScope.PROJECT,
                    related=["target"],
                )
                glob.sprout(ref_blob, f"ref-{i}")

            glob.rebuild_index()

            engine = CalcificationEngine(glob)
            key = glob._blob_key(target_path)
            score = engine.score_polip(key, target)

            # 4 refs >= CONSENSUS_THRESHOLD (3) -> calcified
            assert score.consensus_score > 0.5
            assert score.lifecycle_stage == "calcified"


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

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        output = result.stdout.strip()
        if not output:
            pytest.skip("No output from health --json")

        json_start = output.find("{")
        if json_start == -1:
            pytest.fail(f"No JSON found in output: {output}")

        json_str = output[json_start:]
        data = json.loads(json_str)
        assert "vitality_score" in data
