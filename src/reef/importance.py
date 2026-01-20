"""
Importance signal detection - multi-signal scoring without explicit user action.

Biological memory weights retention by emotional salience, surprise, and repetition.
This module detects these signals from conversation patterns.

Importance signals:
- surprise: contradicts existing memories (high signal)
- correction: user corrections to AI behavior (very high signal)
- repetition: topics that recur across sessions
- urgency: temporal markers, deadlines, emphasis
- consequence: decisions that led to outcomes

Usage:
    detector = ImportanceDetector(glob)
    score = detector.score("user prefers TypeScript over JavaScript", context)
    # Returns ImportanceScore with breakdown
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
import re

if TYPE_CHECKING:
    from .blob import Glob


class SignalType(Enum):
    """Types of importance signals."""
    SURPRISE = "surprise"        # Contradicts existing
    CORRECTION = "correction"    # User correcting AI
    REPETITION = "repetition"    # Recurring topic
    URGENCY = "urgency"          # Time pressure
    CONSEQUENCE = "consequence"  # Led to outcome
    EMOTIONAL = "emotional"      # Frustration/delight


@dataclass
class ImportanceScore:
    """Detailed breakdown of importance scoring."""
    total: float
    signals: dict[str, float] = field(default_factory=dict)
    detected_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total": round(self.total, 3),
            "signals": {k: round(v, 3) for k, v in self.signals.items()},
            "patterns": self.detected_patterns,
        }


# Signal weights (sum to ~1.0 but can exceed for high-signal events)
SIGNAL_WEIGHTS = {
    "surprise": 0.25,
    "correction": 0.35,      # Highest weight - explicit user feedback
    "repetition": 0.20,
    "urgency": 0.15,
    "consequence": 0.15,
    "emotional": 0.10,
}


# Correction patterns - very high signal
CORRECTION_PATTERNS = [
    r"\bno,?\s+(?:actually|i\s+meant|that's\s+wrong)\b",
    r"\bthat's\s+not\s+(?:right|correct|what\s+i)\b",
    r"\bi\s+(?:didn't|don't)\s+mean\b",
    r"\bactually,?\s+(?:it's|it\s+should|i\s+want)\b",
    r"\bwait,?\s+(?:no|that's)\b",
    r"\bstop\b.*\b(?:doing|that)\b",
    r"\bwrong\b",
    r"\bincorrect\b",
    r"\bnot\s+what\s+i\s+(?:asked|wanted|meant)\b",
]

# Urgency patterns
URGENCY_PATTERNS = [
    r"\b(?:urgent|asap|immediately|right\s+now)\b",
    r"\bdeadline\s*(?:is|:)?\s*\w+",
    r"\bby\s+(?:today|tomorrow|friday|monday|end\s+of)\b",
    r"\b(?:critical|blocking|blocker)\b",
    r"\bneed\s+(?:this|it)\s+(?:now|today|asap)\b",
    r"\btime\s*(?:-|)sensitive\b",
    r"!{2,}",  # Multiple exclamation marks
]

# Emotional patterns
EMOTIONAL_PATTERNS = {
    "frustration": [
        r"\b(?:frustrated|annoying|annoyed|ugh|argh)\b",
        r"\bthis\s+(?:is\s+)?(?:broken|not\s+working|wrong)\b",
        r"\bwhy\s+(?:isn't|doesn't|won't)\b",
        r"\bstill\s+(?:broken|not\s+working)\b",
    ],
    "delight": [
        r"\b(?:perfect|exactly|great|awesome|love\s+it)\b",
        r"\bthat's\s+(?:it|right|perfect)\b",
        r"\byes!+\b",
        r"\bthank\s*(?:s|you)\b",
    ],
    "emphasis": [
        r"\b(?:very|really|extremely|super)\s+important\b",
        r"\b(?:must|always|never)\b",
        r"\bmake\s+sure\b",
        r"\bdon't\s+forget\b",
    ],
}

# Consequence patterns (decisions with outcomes)
CONSEQUENCE_PATTERNS = [
    r"\bbecause\s+(?:of\s+)?(?:this|that|the)\b",
    r"\b(?:led|leads)\s+to\b",
    r"\bresulted?\s+in\b",
    r"\bso\s+(?:now|that|we)\b",
    r"\bwhich\s+(?:means|caused)\b",
    r"\bthat's\s+why\b",
]


class ImportanceDetector:
    """
    Multi-signal importance detection without explicit user action.

    Scores observations based on:
    - Surprise: Does this contradict what we already know?
    - Correction: Is the user correcting AI behavior?
    - Repetition: Has this topic come up before?
    - Urgency: Are there time-pressure indicators?
    - Consequence: Is this about cause-effect?
    - Emotional: Are there emotional markers?
    """

    def __init__(self, glob: Optional["Glob"] = None):
        self.glob = glob
        self._topic_history: dict[str, int] = {}  # topic -> occurrence count

    def score(
        self,
        text: str,
        context: Optional[dict] = None,
    ) -> ImportanceScore:
        """
        Score the importance of an observation.

        Args:
            text: The observation text to score
            context: Optional context dict with session info

        Returns:
            ImportanceScore with breakdown
        """
        signals: dict[str, float] = {}
        patterns: list[str] = []

        text_lower = text.lower()

        # 1. Correction detection (highest weight)
        correction_score, correction_patterns = self._detect_correction(text_lower)
        signals["correction"] = correction_score
        patterns.extend(correction_patterns)

        # 2. Urgency detection
        urgency_score, urgency_patterns = self._detect_urgency(text_lower)
        signals["urgency"] = urgency_score
        patterns.extend(urgency_patterns)

        # 3. Emotional markers
        emotional_score, emotional_patterns = self._detect_emotional(text_lower)
        signals["emotional"] = emotional_score
        patterns.extend(emotional_patterns)

        # 4. Consequence patterns
        consequence_score, consequence_patterns = self._detect_consequence(text_lower)
        signals["consequence"] = consequence_score
        patterns.extend(consequence_patterns)

        # 5. Repetition (requires topic extraction)
        repetition_score = self._detect_repetition(text, context)
        signals["repetition"] = repetition_score
        if repetition_score > 0.3:
            patterns.append(f"repetition:{repetition_score:.1f}")

        # 6. Surprise (requires existing memory comparison)
        surprise_score = self._detect_surprise(text, context)
        signals["surprise"] = surprise_score
        if surprise_score > 0.3:
            patterns.append(f"surprise:{surprise_score:.1f}")

        # Weighted total
        total = sum(
            signals.get(signal, 0) * weight
            for signal, weight in SIGNAL_WEIGHTS.items()
        )

        # Boost for multiple signals (compound importance)
        active_signals = sum(1 for v in signals.values() if v > 0.3)
        if active_signals >= 3:
            total *= 1.2  # 20% boost for multi-signal

        # Cap at 1.0 (but can exceed for exceptional cases)
        total = min(1.5, total)

        return ImportanceScore(
            total=total,
            signals=signals,
            detected_patterns=patterns,
        )

    def _detect_correction(self, text: str) -> tuple[float, list[str]]:
        """Detect correction patterns (very high signal)."""
        matches = []
        for pattern in CORRECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append(f"correction:{pattern[:20]}")

        if matches:
            # High score for any correction, max out at 2 matches
            return min(1.0, 0.6 + 0.2 * len(matches)), matches
        return 0.0, []

    def _detect_urgency(self, text: str) -> tuple[float, list[str]]:
        """Detect urgency markers."""
        matches = []
        for pattern in URGENCY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matches.append(f"urgency:{match.group()[:15]}")

        if matches:
            return min(1.0, 0.4 + 0.2 * len(matches)), matches
        return 0.0, []

    def _detect_emotional(self, text: str) -> tuple[float, list[str]]:
        """Detect emotional markers."""
        matches = []

        for category, patterns in EMOTIONAL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    matches.append(f"{category}")
                    break  # One match per category is enough

        if matches:
            return min(1.0, 0.3 + 0.2 * len(matches)), matches
        return 0.0, []

    def _detect_consequence(self, text: str) -> tuple[float, list[str]]:
        """Detect consequence/cause-effect patterns."""
        matches = []
        for pattern in CONSEQUENCE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                matches.append("consequence")
                break  # One is enough

        if matches:
            return 0.5, matches
        return 0.0, []

    def _detect_repetition(
        self,
        text: str,
        context: Optional[dict] = None,
    ) -> float:
        """
        Detect if this topic has come up before.

        Uses simple keyword extraction and tracking.
        More sophisticated: would use semantic similarity.
        """
        # Extract potential topic keywords (nouns, verbs)
        # Simple heuristic: words > 4 chars, not common
        words = set(
            w.lower() for w in re.findall(r'\b[a-zA-Z]{5,}\b', text)
        )

        # Filter common words
        common = {
            "about", "could", "would", "should", "their", "there",
            "which", "where", "these", "those", "being", "having",
            "think", "going", "doing", "something", "anything",
        }
        keywords = words - common

        if not keywords:
            return 0.0

        # Check how many keywords we've seen before
        seen_count = 0
        for kw in keywords:
            if kw in self._topic_history:
                seen_count += self._topic_history[kw]

        # Update history
        for kw in keywords:
            self._topic_history[kw] = self._topic_history.get(kw, 0) + 1

        # Score based on repetition
        if seen_count == 0:
            return 0.0
        elif seen_count <= 2:
            return 0.3
        elif seen_count <= 5:
            return 0.6
        else:
            return 0.9

    def _detect_surprise(
        self,
        text: str,
        context: Optional[dict] = None,
    ) -> float:
        """
        Detect if observation contradicts existing memories.

        This requires comparing against existing polips in the glob.
        For now, uses simple keyword contradiction patterns.

        Full implementation would use semantic embeddings.
        """
        if not self.glob:
            return 0.0

        # Simple contradiction patterns
        # "X is not Y" vs existing "X is Y"
        # "prefer A over B" vs existing "prefer B over A"

        # For now, return low score - this needs semantic comparison
        # which requires embeddings infrastructure
        return 0.0

    def record_topic(self, text: str) -> None:
        """
        Record topics from text for repetition tracking.

        Call this for all conversation turns to build topic history.
        """
        words = set(
            w.lower() for w in re.findall(r'\b[a-zA-Z]{5,}\b', text)
        )
        common = {
            "about", "could", "would", "should", "their", "there",
            "which", "where", "these", "those", "being", "having",
        }
        keywords = words - common

        for kw in keywords:
            self._topic_history[kw] = self._topic_history.get(kw, 0) + 1


# Convenience function
def score_importance(
    text: str,
    glob: Optional["Glob"] = None,
    context: Optional[dict] = None,
) -> ImportanceScore:
    """Score the importance of an observation."""
    detector = ImportanceDetector(glob)
    return detector.score(text, context)
