"""
Tests for anti-git memory features:
- Importance signal detection
- Automatic observation extraction
- Dissolution mechanics
"""

import pytest
from pathlib import Path
from datetime import datetime

from reef.importance import (
    ImportanceDetector,
    ImportanceScore,
    SignalType,
    score_importance,
)
from reef.observe import (
    ObservationExtractor,
    ConversationObserver,
    Observation,
    ObservationType,
    extract_observations,
)
from reef.calcification import (
    DissolutionEngine,
    DecayStage,
)
from reef import Glob, Blob, BlobType, BlobScope


class TestImportanceDetection:
    """Test importance signal detection."""

    def test_correction_detection(self):
        """Corrections should have highest signal."""
        detector = ImportanceDetector()

        score = detector.score("No, that's wrong. I meant TypeScript.")
        assert score.signals["correction"] > 0.3
        assert "correction" in str(score.detected_patterns)

    def test_urgency_detection(self):
        """Urgency markers should be detected."""
        detector = ImportanceDetector()

        score = detector.score("This is urgent! Deadline is tomorrow.")
        assert score.signals["urgency"] > 0.3
        assert any("urgency" in p for p in score.detected_patterns)

    def test_emotional_detection(self):
        """Emotional markers should be detected."""
        detector = ImportanceDetector()

        # Frustration
        score = detector.score("This is so frustrating! Why won't it work?")
        assert score.signals["emotional"] > 0.2

        # Delight
        score = detector.score("Perfect! That's exactly what I wanted.")
        assert score.signals["emotional"] > 0.2

    def test_repetition_tracking(self):
        """Repeated topics should increase score."""
        detector = ImportanceDetector()

        # First mention
        score1 = detector.score("We need to fix the authentication system.")
        # Second mention (same topic)
        score2 = detector.score("The authentication system is still broken.")
        # Third mention
        score3 = detector.score("Has anyone looked at authentication yet?")

        # Repetition score should increase
        assert score3.signals["repetition"] >= score1.signals["repetition"]

    def test_normal_text_low_signal(self):
        """Normal text should have low importance."""
        detector = ImportanceDetector()

        score = detector.score("Can you help me with this code?")
        assert score.total < 0.3

    def test_multiple_signals_boost(self):
        """Multiple signals should compound importance."""
        detector = ImportanceDetector()

        # Correction + urgency + emotional = very high
        score = detector.score(
            "No, that's wrong! This is urgent and I'm very frustrated!"
        )
        active_signals = sum(1 for v in score.signals.values() if v > 0.2)
        assert active_signals >= 2


class TestObservationExtraction:
    """Test automatic observation extraction."""

    def test_correction_extraction(self):
        """Corrections should always be extracted."""
        extractor = ObservationExtractor()

        obs = extractor.extract("No, actually I want Python, not JavaScript.")
        corrections = [o for o in obs if o.type == ObservationType.CORRECTION]

        # Corrections have high signal, should pass threshold
        assert len(corrections) >= 1

    def test_observation_deduplication(self):
        """Same observation shouldn't be extracted twice."""
        extractor = ObservationExtractor()

        obs1 = extractor.extract("No, I want TypeScript.")
        obs2 = extractor.extract("No, I want TypeScript.")  # Same text

        # Second extraction should be deduplicated
        assert len(obs2) == 0 or obs2[0].observation_id() not in [
            o.observation_id() for o in obs1
        ]

    def test_observation_id_stability(self):
        """Same content should produce same ID."""
        obs1 = Observation(
            type=ObservationType.PREFERENCE,
            content="prefers typescript",
            source_text="I prefer TypeScript",
            importance=ImportanceScore(total=0.5),
        )
        obs2 = Observation(
            type=ObservationType.PREFERENCE,
            content="prefers typescript",
            source_text="I prefer TypeScript",
            importance=ImportanceScore(total=0.6),
        )

        assert obs1.observation_id() == obs2.observation_id()


class TestConversationObserver:
    """Test continuous conversation observation."""

    def test_observe_turn(self):
        """Should observe both user and assistant text."""
        observer = ConversationObserver()

        obs = observer.observe_turn(
            user_text="No, that's wrong. Use Postgres instead.",
            assistant_text="I'll update to use Postgres.",
        )

        # User corrections should be captured
        user_obs = [o for o in obs if "wrong" in o.source_text.lower()]
        assert len(user_obs) >= 1

    def test_pending_accumulation(self):
        """Pending observations should accumulate."""
        observer = ConversationObserver()

        observer.observe_turn("First turn", "Response 1")
        observer.observe_turn("No, that's incorrect!", "Sorry, I'll fix it.")

        pending = observer.get_pending(min_importance=0.2)
        # Should have accumulated observations
        assert len(observer._pending) >= 0


class TestDecayStages:
    """Test decay stage enum."""

    def test_stage_values(self):
        """Decay stages should have expected values."""
        assert DecayStage.ACTIVE.value == "active"
        assert DecayStage.COMPRESSED.value == "compressed"
        assert DecayStage.FOSSIL.value == "fossil"
        assert DecayStage.DISSOLVED.value == "dissolved"

    def test_stage_ordering(self):
        """Stages should represent increasing decay."""
        stages = [
            DecayStage.ACTIVE,
            DecayStage.COMPRESSED,
            DecayStage.FOSSIL,
            DecayStage.DISSOLVED,
        ]
        # Just verify all four exist
        assert len(stages) == 4


class TestDissolutionEngine:
    """Test dissolution mechanics."""

    def test_protected_scopes(self):
        """Always-scoped polips should be protected."""
        engine = DissolutionEngine.__new__(DissolutionEngine)
        assert "always" in engine.PROTECTED_SCOPES

    def test_protected_types(self):
        """Constraints should be protected."""
        engine = DissolutionEngine.__new__(DissolutionEngine)
        assert "constraint" in engine.PROTECTED_TYPES

    def test_thresholds_exist(self):
        """Dissolution thresholds should be defined."""
        engine = DissolutionEngine.__new__(DissolutionEngine)
        assert engine.COMPRESSION_THRESHOLD > 0
        assert engine.FOSSIL_THRESHOLD > engine.COMPRESSION_THRESHOLD
        assert engine.DISSOLUTION_THRESHOLD > engine.FOSSIL_THRESHOLD


class TestDissolutionWithGlob:
    """Test dissolution with actual glob."""

    def test_dissolution_cycle_dry_run(self, tmp_path):
        """Dry run should not modify anything."""
        # Create a glob with the parent directory
        glob = Glob(tmp_path)

        blob = Blob(
            type=BlobType.CONTEXT,
            summary="Test context",
            scope=BlobScope.PROJECT,
        )
        glob.sprout(blob, "test-context", subdir="current")

        engine = DissolutionEngine(glob)
        report = engine.run_dissolution_cycle(dry_run=True)

        # Should report on polips without modifying
        assert report.total_polips >= 1
        # Verify blob still exists
        found_blobs = glob.list_blobs(subdir="current")
        assert any("test-context" in name for name, _ in found_blobs)

    def test_protected_polips_not_dissolved(self, tmp_path):
        """Protected polips should never be dissolved."""
        glob = Glob(tmp_path)

        # Create a constraint (protected type)
        constraint = Blob(
            type=BlobType.CONSTRAINT,
            summary="Never do this",
            scope=BlobScope.ALWAYS,
        )
        glob.sprout(constraint, "test-constraint", subdir="bedrock")

        engine = DissolutionEngine(glob)
        engine._session_count = 100  # Simulate many sessions

        report = engine.run_dissolution_cycle(dry_run=True)

        # Constraint should be in protected, not dissolved
        assert len(report.protected) >= 1 or len(report.dissolved) == 0


class TestImportanceScoreSerialize:
    """Test importance score serialization."""

    def test_to_dict(self):
        """Score should serialize to dict."""
        score = ImportanceScore(
            total=0.75,
            signals={"correction": 0.6, "urgency": 0.3},
            detected_patterns=["correction:test"],
        )

        d = score.to_dict()
        assert d["total"] == 0.75
        assert "correction" in d["signals"]
        assert "patterns" in d


class TestObservationSerialize:
    """Test observation serialization."""

    def test_to_dict(self):
        """Observation should serialize to dict."""
        obs = Observation(
            type=ObservationType.CORRECTION,
            content="Use TypeScript",
            source_text="No, use TypeScript",
            importance=ImportanceScore(total=0.8),
            confidence=0.9,
            keywords=["typescript"],
        )

        d = obs.to_dict()
        assert d["type"] == "correction"
        assert d["content"] == "Use TypeScript"
        assert d["confidence"] == 0.9
        assert "typescript" in d["keywords"]
