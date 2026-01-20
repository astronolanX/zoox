"""
Observation extraction - automatic polip creation from conversation patterns.

Anti-git principle: Memory should emerge from use, not explicit saves.
This module extracts potential observations from conversation text
and converts high-importance ones into polips automatically.

Observation types:
- preference: User preferences and choices
- fact: Statements of fact about the project/domain
- decision: Choices made with reasoning
- correction: User corrections (highest signal)
- goal: Stated objectives or intentions

Usage:
    extractor = ObservationExtractor(glob)
    observations = extractor.extract("User prefers TypeScript over JavaScript")

    for obs in observations:
        if obs.importance.total > 0.5:
            obs.to_polip()  # Creates polip automatically
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional
import re
import hashlib

from .importance import ImportanceDetector, ImportanceScore

if TYPE_CHECKING:
    from .blob import Blob, Glob


class ObservationType(Enum):
    """Types of observations that can be extracted."""
    PREFERENCE = "preference"   # User likes/prefers X
    FACT = "fact"              # Statement about domain
    DECISION = "decision"      # Choice with reasoning
    CORRECTION = "correction"  # User correcting AI
    GOAL = "goal"              # Stated objective
    PATTERN = "pattern"        # Recurring behavior


@dataclass
class Observation:
    """An extracted observation from conversation."""
    type: ObservationType
    content: str
    source_text: str
    importance: ImportanceScore
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None

    # Derived fields
    keywords: list[str] = field(default_factory=list)
    confidence: float = 0.5  # How confident in extraction

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "content": self.content,
            "importance": self.importance.to_dict(),
            "confidence": round(self.confidence, 2),
            "keywords": self.keywords,
            "timestamp": self.timestamp.isoformat(),
        }

    def observation_id(self) -> str:
        """Generate a stable ID for deduplication."""
        content_hash = hashlib.sha256(
            self.content.lower().encode()
        ).hexdigest()[:12]
        return f"obs-{self.type.value[:4]}-{content_hash}"


# Extraction patterns for different observation types
PREFERENCE_PATTERNS = [
    # "I prefer X" / "I like X"
    (r"i\s+(?:prefer|like|want|use)\s+(.+?)(?:\s+(?:over|instead|rather)\s+(.+?))?(?:\.|$)",
     "prefers {0}" + " over {1}" if "{1}" else ""),
    # "X is better" / "use X"
    (r"(?:let's|please|always)\s+use\s+(\w+)", "prefers {0}"),
    # "don't like X" / "avoid X"
    (r"(?:don't|do\s+not|never)\s+(?:use|like|want)\s+(.+?)(?:\.|$)",
     "avoids {0}"),
]

FACT_PATTERNS = [
    # "X is Y"
    (r"(?:the|our|this)\s+(\w+)\s+is\s+(.+?)(?:\.|$)", "{0} is {1}"),
    # "We use X for Y"
    (r"we\s+use\s+(\w+)\s+for\s+(.+?)(?:\.|$)", "uses {0} for {1}"),
    # "X requires Y"
    (r"(\w+)\s+requires?\s+(.+?)(?:\.|$)", "{0} requires {1}"),
]

DECISION_PATTERNS = [
    # "We decided to X"
    (r"(?:we|i)\s+decided?\s+(?:to\s+)?(.+?)(?:\s+because\s+(.+?))?(?:\.|$)",
     "decided: {0}"),
    # "Going with X"
    (r"(?:going|went)\s+with\s+(.+?)(?:\s+because\s+(.+?))?(?:\.|$)",
     "chose: {0}"),
    # "Let's do X"
    (r"let's\s+(?:go\s+with|do|use)\s+(.+?)(?:\.|$)", "will: {0}"),
]

GOAL_PATTERNS = [
    # "I want to X"
    (r"i\s+(?:want|need)\s+to\s+(.+?)(?:\.|$)", "goal: {0}"),
    # "The goal is X"
    (r"(?:the|our)\s+goal\s+is\s+(?:to\s+)?(.+?)(?:\.|$)", "goal: {0}"),
    # "We're trying to X"
    (r"(?:we're|i'm)\s+trying\s+to\s+(.+?)(?:\.|$)", "goal: {0}"),
]


class ObservationExtractor:
    """
    Extracts observations from conversation text.

    Operates automatically - no explicit save commands needed.
    Uses importance scoring to filter noise.
    """

    # Minimum importance to consider an observation
    IMPORTANCE_THRESHOLD = 0.3

    # Minimum confidence in extraction
    CONFIDENCE_THRESHOLD = 0.4

    def __init__(self, glob: Optional["Glob"] = None):
        self.glob = glob
        self.importance_detector = ImportanceDetector(glob)
        self._seen_observations: set[str] = set()  # For deduplication

    def extract(
        self,
        text: str,
        session_id: Optional[str] = None,
    ) -> list[Observation]:
        """
        Extract observations from conversation text.

        Args:
            text: The text to extract from
            session_id: Optional session identifier

        Returns:
            List of observations (may be empty)
        """
        observations: list[Observation] = []

        # Normalize text
        text_clean = text.strip()
        if not text_clean:
            return []

        # Record topics for repetition tracking
        self.importance_detector.record_topic(text_clean)

        # Try each extraction type
        observations.extend(self._extract_preferences(text_clean, session_id))
        observations.extend(self._extract_facts(text_clean, session_id))
        observations.extend(self._extract_decisions(text_clean, session_id))
        observations.extend(self._extract_goals(text_clean, session_id))
        observations.extend(self._extract_corrections(text_clean, session_id))

        # Filter by importance and confidence
        filtered = [
            obs for obs in observations
            if obs.importance.total >= self.IMPORTANCE_THRESHOLD
            and obs.confidence >= self.CONFIDENCE_THRESHOLD
        ]

        # Deduplicate
        unique = []
        for obs in filtered:
            obs_id = obs.observation_id()
            if obs_id not in self._seen_observations:
                self._seen_observations.add(obs_id)
                unique.append(obs)

        return unique

    def _extract_preferences(
        self,
        text: str,
        session_id: Optional[str],
    ) -> list[Observation]:
        """Extract preference observations."""
        observations = []
        text_lower = text.lower()

        for pattern, template in PREFERENCE_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                groups = match.groups()
                content = template.format(*[g or "" for g in groups])
                content = re.sub(r'\s+', ' ', content).strip()

                if len(content) < 5:  # Too short
                    continue

                # Score importance
                importance = self.importance_detector.score(
                    match.group(0)
                )

                observations.append(Observation(
                    type=ObservationType.PREFERENCE,
                    content=content,
                    source_text=match.group(0),
                    importance=importance,
                    session_id=session_id,
                    confidence=0.6,  # Pattern match = moderate confidence
                    keywords=self._extract_keywords(content),
                ))

        return observations

    def _extract_facts(
        self,
        text: str,
        session_id: Optional[str],
    ) -> list[Observation]:
        """Extract fact observations."""
        observations = []
        text_lower = text.lower()

        for pattern, template in FACT_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                groups = match.groups()
                content = template.format(*[g or "" for g in groups])
                content = re.sub(r'\s+', ' ', content).strip()

                if len(content) < 5:
                    continue

                importance = self.importance_detector.score(
                    match.group(0)
                )

                observations.append(Observation(
                    type=ObservationType.FACT,
                    content=content,
                    source_text=match.group(0),
                    importance=importance,
                    session_id=session_id,
                    confidence=0.5,  # Facts need verification
                    keywords=self._extract_keywords(content),
                ))

        return observations

    def _extract_decisions(
        self,
        text: str,
        session_id: Optional[str],
    ) -> list[Observation]:
        """Extract decision observations."""
        observations = []
        text_lower = text.lower()

        for pattern, template in DECISION_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                groups = match.groups()
                content = template.format(*[g or "" for g in groups])
                content = re.sub(r'\s+', ' ', content).strip()

                if len(content) < 5:
                    continue

                importance = self.importance_detector.score(
                    match.group(0)
                )

                # Decisions get importance boost
                importance.total = min(1.5, importance.total * 1.2)

                observations.append(Observation(
                    type=ObservationType.DECISION,
                    content=content,
                    source_text=match.group(0),
                    importance=importance,
                    session_id=session_id,
                    confidence=0.7,  # Decisions are explicit
                    keywords=self._extract_keywords(content),
                ))

        return observations

    def _extract_goals(
        self,
        text: str,
        session_id: Optional[str],
    ) -> list[Observation]:
        """Extract goal observations."""
        observations = []
        text_lower = text.lower()

        for pattern, template in GOAL_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                groups = match.groups()
                content = template.format(*[g or "" for g in groups])
                content = re.sub(r'\s+', ' ', content).strip()

                if len(content) < 5:
                    continue

                importance = self.importance_detector.score(
                    match.group(0)
                )

                observations.append(Observation(
                    type=ObservationType.GOAL,
                    content=content,
                    source_text=match.group(0),
                    importance=importance,
                    session_id=session_id,
                    confidence=0.65,
                    keywords=self._extract_keywords(content),
                ))

        return observations

    def _extract_corrections(
        self,
        text: str,
        session_id: Optional[str],
    ) -> list[Observation]:
        """
        Extract correction observations.

        Corrections are highest-signal - user explicitly correcting AI.
        """
        observations = []

        # Check if this looks like a correction
        importance = self.importance_detector.score(text)

        if importance.signals.get("correction", 0) > 0.3:
            # This is a correction - extract it
            observations.append(Observation(
                type=ObservationType.CORRECTION,
                content=text[:200],  # Keep reasonable length
                source_text=text,
                importance=importance,
                session_id=session_id,
                confidence=0.8,  # High confidence for corrections
                keywords=self._extract_keywords(text),
            ))

        return observations

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        common = {
            "this", "that", "with", "from", "have", "will",
            "been", "being", "about", "would", "could", "should",
        }
        return [w for w in words if w not in common][:5]

    def to_polip(
        self,
        observation: Observation,
        glob: Optional["Glob"] = None,
    ) -> Optional["Blob"]:
        """
        Convert an observation to a polip.

        Args:
            observation: The observation to convert
            glob: Optional glob to create polip in

        Returns:
            Created Blob or None if conversion failed
        """
        target_glob = glob or self.glob
        if not target_glob:
            return None

        from .blob import Blob, BlobType, BlobScope

        # Map observation type to blob type
        type_map = {
            ObservationType.PREFERENCE: BlobType.FACT,
            ObservationType.FACT: BlobType.FACT,
            ObservationType.DECISION: BlobType.DECISION,
            ObservationType.CORRECTION: BlobType.FACT,
            ObservationType.GOAL: BlobType.THREAD,
            ObservationType.PATTERN: BlobType.CONTEXT,
        }

        blob_type = type_map.get(observation.type, BlobType.CONTEXT)

        # Create blob
        blob = Blob(
            type=blob_type,
            summary=observation.content,
            scope=BlobScope.PROJECT,
            context=f"Extracted from: {observation.source_text}\n"
                    f"Importance: {observation.importance.total:.2f}\n"
                    f"Signals: {observation.importance.detected_patterns}",
        )

        # Generate name from observation
        name = observation.observation_id()

        try:
            # Save to current/ subdirectory
            target_glob.add_blob(name, blob, subdir="current")
            return blob
        except Exception:
            return None


class ConversationObserver:
    """
    Continuous observation of conversation turns.

    Use this to automatically extract observations from all conversation
    without explicit user action.
    """

    def __init__(self, glob: Optional["Glob"] = None):
        self.glob = glob
        self.extractor = ObservationExtractor(glob)
        self._pending: list[Observation] = []
        self._turn_count = 0

    def observe_turn(
        self,
        user_text: str,
        assistant_text: str,
        session_id: Optional[str] = None,
    ) -> list[Observation]:
        """
        Observe a conversation turn.

        Args:
            user_text: User's message
            assistant_text: Assistant's response
            session_id: Optional session identifier

        Returns:
            New observations from this turn
        """
        self._turn_count += 1
        observations = []

        # Extract from user text (higher weight - explicit intent)
        user_obs = self.extractor.extract(user_text, session_id)
        for obs in user_obs:
            obs.importance.total *= 1.2  # Boost user observations
        observations.extend(user_obs)

        # Extract from assistant text (lower weight - may be suggestions)
        asst_obs = self.extractor.extract(assistant_text, session_id)
        for obs in asst_obs:
            obs.importance.total *= 0.8  # Reduce assistant observations
        observations.extend(asst_obs)

        # Add to pending
        self._pending.extend(observations)

        return observations

    def get_pending(
        self,
        min_importance: float = 0.5,
    ) -> list[Observation]:
        """Get pending observations above importance threshold."""
        return [
            obs for obs in self._pending
            if obs.importance.total >= min_importance
        ]

    def commit_observations(
        self,
        min_importance: float = 0.6,
    ) -> int:
        """
        Commit high-importance observations as polips.

        Returns count of created polips.
        """
        if not self.glob:
            return 0

        count = 0
        to_commit = self.get_pending(min_importance)

        for obs in to_commit:
            if self.extractor.to_polip(obs, self.glob):
                count += 1
                self._pending.remove(obs)

        return count

    def clear_pending(self) -> None:
        """Clear all pending observations."""
        self._pending.clear()


# Convenience functions
def extract_observations(
    text: str,
    glob: Optional["Glob"] = None,
) -> list[Observation]:
    """Extract observations from text."""
    return ObservationExtractor(glob).extract(text)


def auto_observe(
    user_text: str,
    assistant_text: str,
    glob: Optional["Glob"] = None,
    session_id: Optional[str] = None,
) -> list[Observation]:
    """Automatically observe a conversation turn."""
    observer = ConversationObserver(glob)
    return observer.observe_turn(user_text, assistant_text, session_id)
