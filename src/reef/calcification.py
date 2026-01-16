"""
Calcification engine - organic growth mechanics for reef.

AI-NATIVE TIME: Digital memory operates on sessions and turns, not days.
A polip referenced 50 times in one session is more calcified than
one touched once over 7 days.

Time units:
- turn: single interaction (the heartbeat)
- session: one conversation (the fundamental unit)
- epoch: multiple sessions (emergent pattern)

Calcification triggers (combinatorial):
- Intensity: refs within session (immediate value)
- Persistence: sessions that reference (lasting value)
- Depth: turn depth when referenced (real work vs surface)
- Ceremony: explicit human promotion (authority)
- Consensus: refs from other polips (network effect)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .blob import Blob, Glob


class ChallengeResult(Enum):
    """Outcome of adversarial challenge."""
    SURVIVE = "survive"      # Polip justifies existence
    MERGE = "merge"          # Absorb into another polip
    DECOMPOSE = "decompose"  # Break down, archive to fossil


@dataclass
class SessionMetrics:
    """Per-session tracking for a polip."""
    session_id: str
    refs: int = 0
    max_turn_depth: int = 0
    first_ref_turn: int = 0
    last_ref_turn: int = 0


@dataclass
class PolipVitals:
    """AI-native vitality metrics for a polip."""
    # Intensity: how hot is it right now?
    refs_this_session: int = 0
    intensity_score: float = 0.0  # 0-1, based on refs/session

    # Persistence: does it endure?
    sessions_referenced: int = 0
    session_coverage: float = 0.0  # fraction of sessions that ref'd

    # Depth: is it used for real work?
    avg_turn_depth: float = 0.0  # when in session it gets used
    depth_score: float = 0.0  # 0-1, deeper = more valuable

    # Network: is it connected?
    incoming_refs: int = 0
    outgoing_refs: int = 0
    consensus_score: float = 0.0

    # Ceremony: was it blessed?
    promoted: bool = False
    ceremony_score: float = 0.0


@dataclass
class CalcificationScore:
    """Detailed breakdown of calcification scoring."""
    polip_key: str
    total: float
    intensity_score: float
    persistence_score: float
    depth_score: float
    ceremony_score: float
    consensus_score: float
    should_calcify: bool
    lifecycle_stage: str
    vitals: PolipVitals

    def to_dict(self) -> dict:
        return {
            "polip": self.polip_key,
            "total": round(self.total, 3),
            "lifecycle": self.lifecycle_stage,
            "breakdown": {
                "intensity": round(self.intensity_score, 3),
                "persistence": round(self.persistence_score, 3),
                "depth": round(self.depth_score, 3),
                "ceremony": round(self.ceremony_score, 3),
                "consensus": round(self.consensus_score, 3),
            },
            "should_calcify": self.should_calcify,
            "vitals": {
                "refs_this_session": self.vitals.refs_this_session,
                "sessions_referenced": self.vitals.sessions_referenced,
                "avg_turn_depth": round(self.vitals.avg_turn_depth, 1),
                "incoming_refs": self.vitals.incoming_refs,
            },
        }


class CalcificationEngine:
    """
    AI-native calcification: schema emerges from usage velocity.

    Time constants are session-relative, not wall-clock:
    - HIGH_INTENSITY_THRESHOLD: 5 refs in single session = hot
    - PERSISTENCE_THRESHOLD: 3 sessions = lasting
    - DEPTH_THRESHOLD: turn 10+ = real work (not just startup context)
    - CONSENSUS_THRESHOLD: 3 incoming refs = network effect

    A polip calcifies when total score >= 0.7
    """

    # AI-native thresholds
    HIGH_INTENSITY_THRESHOLD = 5   # refs/session for "hot"
    PERSISTENCE_THRESHOLD = 3       # sessions for "lasting"
    DEPTH_THRESHOLD = 10            # turn depth for "real work"
    CONSENSUS_THRESHOLD = 3         # incoming refs for "connected"

    # Trigger weights (sum to 1.0)
    WEIGHTS = {
        "intensity": 0.25,    # immediate value
        "persistence": 0.25,  # lasting value
        "depth": 0.15,        # real work indicator
        "ceremony": 0.15,     # human authority
        "consensus": 0.20,    # network effect
    }

    CALCIFICATION_THRESHOLD = 0.7

    def __init__(self, glob: "Glob"):
        self.glob = glob
        self._current_session_id: str | None = None
        self._current_turn: int = 0
        self._session_history: dict[str, list[SessionMetrics]] = {}

    def _iter_all_blobs(self):
        """Iterate over all blobs from root and subdirs."""
        from .blob import KNOWN_SUBDIRS
        from .constants import extension_for_type, DEFAULT_EXTENSION

        for name, blob in self.glob.list_blobs():
            ext = extension_for_type(blob.type.value) if blob.type else DEFAULT_EXTENSION
            key = f"{name}{ext}"
            yield key, blob

        for subdir in KNOWN_SUBDIRS:
            for name, blob in self.glob.list_blobs(subdir):
                ext = extension_for_type(blob.type.value) if blob.type else DEFAULT_EXTENSION
                key = f"{subdir}/{name}{ext}"
                yield key, blob

    def start_session(self, session_id: str | None = None) -> str:
        """Start tracking a new session."""
        self._current_session_id = session_id or datetime.now().isoformat()
        self._current_turn = 0
        return self._current_session_id

    def tick_turn(self) -> int:
        """Advance the turn counter."""
        self._current_turn += 1
        return self._current_turn

    def record_reference(self, polip_key: str) -> None:
        """Record that a polip was referenced this turn."""
        if not self._current_session_id:
            self.start_session()

        if polip_key not in self._session_history:
            self._session_history[polip_key] = []

        # Find or create session metrics
        session_metrics = None
        for sm in self._session_history[polip_key]:
            if sm.session_id == self._current_session_id:
                session_metrics = sm
                break

        if session_metrics is None:
            session_metrics = SessionMetrics(
                session_id=self._current_session_id,
                first_ref_turn=self._current_turn,
            )
            self._session_history[polip_key].append(session_metrics)

        session_metrics.refs += 1
        session_metrics.last_ref_turn = self._current_turn
        session_metrics.max_turn_depth = max(
            session_metrics.max_turn_depth,
            self._current_turn
        )

        # Also increment access_count in index for persistence
        self.glob._increment_access([polip_key])

    def get_vitals(self, key: str, blob: "Blob") -> PolipVitals:
        """Calculate AI-native vitality metrics for a polip."""
        index = self.glob.get_index()
        blob_meta = index.get("blobs", {}).get(key, {})

        vitals = PolipVitals()

        # Get session history for this polip
        history = self._session_history.get(key, [])

        # Intensity: refs in current session
        if self._current_session_id:
            for sm in history:
                if sm.session_id == self._current_session_id:
                    vitals.refs_this_session = sm.refs
                    break

        # Also use access_count as proxy when no live session data
        access_count = blob_meta.get("access_count", 0)
        effective_refs = max(vitals.refs_this_session, access_count)
        vitals.intensity_score = min(1.0, effective_refs / (self.HIGH_INTENSITY_THRESHOLD * 2))

        # Persistence: how many sessions referenced this
        vitals.sessions_referenced = len(history) if history else (1 if access_count > 0 else 0)
        # Estimate session coverage (assume ~10 sessions as baseline)
        total_sessions = max(10, len(set(
            sm.session_id
            for polip_history in self._session_history.values()
            for sm in polip_history
        )))
        vitals.session_coverage = vitals.sessions_referenced / total_sessions

        # Depth: average turn depth when referenced
        if history:
            total_depth = sum(sm.max_turn_depth for sm in history)
            vitals.avg_turn_depth = total_depth / len(history)
        vitals.depth_score = min(1.0, vitals.avg_turn_depth / (self.DEPTH_THRESHOLD * 2))

        # Consensus: incoming references from other polips
        polip_name = Path(key).stem.replace(".blob", "")
        for other_key, meta in index.get("blobs", {}).items():
            if other_key == key:
                continue
            related = meta.get("related", [])
            if polip_name in related or key in related:
                vitals.incoming_refs += 1

        vitals.outgoing_refs = len(blob.related) if blob.related else 0
        vitals.consensus_score = min(1.0, vitals.incoming_refs / (self.CONSENSUS_THRESHOLD * 2))

        # Ceremony: explicit promotion
        from .blob import BlobScope, BlobType
        vitals.promoted = (
            blob.scope == BlobScope.ALWAYS or
            blob.type == BlobType.CONSTRAINT
        )
        vitals.ceremony_score = 1.0 if vitals.promoted else 0.0

        return vitals

    def get_lifecycle_stage(self, vitals: PolipVitals) -> str:
        """
        Determine lifecycle stage from vitals.

        AI-native stages (session-based, not day-based):
        - spawning: new, untested
        - drifting: some use, finding its place
        - attached: proven value, regular use
        - calcified: essential, deeply integrated
        - fossil: historical, rarely accessed
        """
        # Fast track: high intensity in current session = attached
        if vitals.refs_this_session >= self.HIGH_INTENSITY_THRESHOLD:
            return "attached"

        # Ceremony overrides = calcified
        if vitals.promoted:
            return "calcified"

        # Network integration = calcified
        if vitals.incoming_refs >= self.CONSENSUS_THRESHOLD:
            return "calcified"

        # Persistent across sessions = attached
        if vitals.sessions_referenced >= self.PERSISTENCE_THRESHOLD:
            return "attached"

        # Some use but not persistent = drifting
        if vitals.sessions_referenced >= 1 or vitals.refs_this_session > 0:
            return "drifting"

        # No real use yet
        return "spawning"

    def score_polip(self, key: str, blob: "Blob") -> CalcificationScore:
        """Calculate AI-native calcification score."""
        vitals = self.get_vitals(key, blob)
        lifecycle = self.get_lifecycle_stage(vitals)

        # Weighted total
        total = (
            vitals.intensity_score * self.WEIGHTS["intensity"] +
            vitals.session_coverage * self.WEIGHTS["persistence"] +
            vitals.depth_score * self.WEIGHTS["depth"] +
            vitals.ceremony_score * self.WEIGHTS["ceremony"] +
            vitals.consensus_score * self.WEIGHTS["consensus"]
        )

        return CalcificationScore(
            polip_key=key,
            total=total,
            intensity_score=vitals.intensity_score,
            persistence_score=vitals.session_coverage,
            depth_score=vitals.depth_score,
            ceremony_score=vitals.ceremony_score,
            consensus_score=vitals.consensus_score,
            should_calcify=total >= self.CALCIFICATION_THRESHOLD,
            lifecycle_stage=lifecycle,
            vitals=vitals,
        )

    def get_candidates(self) -> list[CalcificationScore]:
        """Get polips that are candidates for calcification."""
        candidates = []
        for key, blob in self._iter_all_blobs():
            score = self.score_polip(key, blob)
            if score.should_calcify:
                candidates.append(score)
        return sorted(candidates, key=lambda s: s.total, reverse=True)

    def get_all_scores(self) -> list[CalcificationScore]:
        """Get scores for all polips."""
        scores = []
        for key, blob in self._iter_all_blobs():
            scores.append(self.score_polip(key, blob))
        return sorted(scores, key=lambda s: s.total, reverse=True)


@dataclass
class ChallengeReport:
    """Report from an adversarial challenge."""
    polip_key: str
    trigger: str
    result: ChallengeResult
    reason: str

    def to_dict(self) -> dict:
        return {
            "polip": self.polip_key,
            "trigger": self.trigger,
            "result": self.result.value,
            "reason": self.reason,
        }


class AdversarialDecay:
    """
    AI-native selection pressure through adversarial challenge.

    Challenge triggers (session-based, aggressive):
    - cold: 0 refs in last 3 sessions (going stale fast)
    - shallow: only first-turn refs (context dump, not real use)
    - orphan: no incoming refs and not promoted
    - superseded: another polip on same topic has higher intensity

    Outcomes:
    - SURVIVE: demonstrates continued value
    - MERGE: should be absorbed into another polip
    - DECOMPOSE: archive to fossil layer
    """

    # Aggressive AI-native thresholds
    COLD_SESSION_THRESHOLD = 3      # sessions without ref = cold
    SHALLOW_TURN_THRESHOLD = 3      # only early turns = shallow

    PROTECTED_SCOPES = ["always"]

    def __init__(self, glob: "Glob", engine: CalcificationEngine | None = None):
        self.glob = glob
        self.engine = engine or CalcificationEngine(glob)

    def _iter_all_blobs(self):
        """Iterate over all blobs from root and subdirs."""
        from .blob import KNOWN_SUBDIRS
        from .constants import extension_for_type, DEFAULT_EXTENSION

        for name, blob in self.glob.list_blobs():
            ext = extension_for_type(blob.type.value) if blob.type else DEFAULT_EXTENSION
            key = f"{name}{ext}"
            yield key, blob

        for subdir in KNOWN_SUBDIRS:
            for name, blob in self.glob.list_blobs(subdir):
                ext = extension_for_type(blob.type.value) if blob.type else DEFAULT_EXTENSION
                key = f"{subdir}/{name}{ext}"
                yield key, blob

    def get_challengers(self) -> list[tuple[str, "Blob", str]]:
        """Get polips that should face adversarial challenge."""
        challengers = []
        index = self.glob.get_index()

        for key, blob in self._iter_all_blobs():
            if blob.scope.value in self.PROTECTED_SCOPES:
                continue

            vitals = self.engine.get_vitals(key, blob)

            # Cold: no recent activity
            if (vitals.sessions_referenced == 0 and
                vitals.refs_this_session == 0 and
                not vitals.promoted):
                meta = index.get("blobs", {}).get(key, {})
                if meta.get("access_count", 0) == 0:
                    challengers.append((key, blob, "cold"))
                    continue

            # Shallow: only surface-level use
            if vitals.avg_turn_depth < self.SHALLOW_TURN_THRESHOLD and not vitals.promoted:
                if vitals.incoming_refs == 0:
                    challengers.append((key, blob, "shallow"))
                    continue

            # Orphan: no connections and not blessed
            if vitals.incoming_refs == 0 and vitals.outgoing_refs == 0:
                if not vitals.promoted and vitals.sessions_referenced <= 1:
                    challengers.append((key, blob, "orphan"))

        return challengers

    def challenge(self, key: str, blob: "Blob", trigger: str) -> ChallengeReport:
        """Challenge a polip to defend its relevance."""
        vitals = self.engine.get_vitals(key, blob)

        # Defense 1: Current session intensity
        if vitals.refs_this_session >= 3:
            return ChallengeReport(
                polip_key=key,
                trigger=trigger,
                result=ChallengeResult.SURVIVE,
                reason=f"High current intensity ({vitals.refs_this_session} refs this session)",
            )

        # Defense 2: Network integration
        if vitals.incoming_refs >= 2:
            return ChallengeReport(
                polip_key=key,
                trigger=trigger,
                result=ChallengeResult.SURVIVE,
                reason=f"Network integrated ({vitals.incoming_refs} incoming refs)",
            )

        # Defense 3: Persistence across sessions
        if vitals.sessions_referenced >= 2:
            return ChallengeReport(
                polip_key=key,
                trigger=trigger,
                result=ChallengeResult.SURVIVE,
                reason=f"Persistent value ({vitals.sessions_referenced} sessions)",
            )

        # Merge candidate: has outgoing refs to active polips
        if vitals.outgoing_refs > 0:
            return ChallengeReport(
                polip_key=key,
                trigger=trigger,
                result=ChallengeResult.MERGE,
                reason=f"Consider merging into referenced polips ({vitals.outgoing_refs} refs)",
            )

        # No defense
        return ChallengeReport(
            polip_key=key,
            trigger=trigger,
            result=ChallengeResult.DECOMPOSE,
            reason=f"No justification ({trigger}): 0 intensity, 0 network, 0 persistence",
        )

    def run_challenges(self, dry_run: bool = True) -> list[ChallengeReport]:
        """Run adversarial challenges on all eligible polips."""
        reports = []
        for key, blob, trigger in self.get_challengers():
            report = self.challenge(key, blob, trigger)
            reports.append(report)
        return reports


@dataclass
class HealthReport:
    """AI-native reef ecosystem health metrics."""
    vitality_score: float
    total_polips: int
    hot_ratio: float           # polips with current session activity
    connected_ratio: float     # polips with network links
    type_diversity: float
    lifecycle_stages: dict
    session_stats: dict
    recommendations: list[str]

    def to_dict(self) -> dict:
        return {
            "vitality_score": round(self.vitality_score, 3),
            "total_polips": self.total_polips,
            "hot_ratio": round(self.hot_ratio, 3),
            "connected_ratio": round(self.connected_ratio, 3),
            "type_diversity": round(self.type_diversity, 3),
            "lifecycle_stages": self.lifecycle_stages,
            "session_stats": self.session_stats,
            "recommendations": self.recommendations,
        }


class ReefHealth:
    """
    AI-native ecosystem health metrics.

    Measures (session-relative):
    - Vitality Score: overall health 0-1
    - Hot Ratio: polips active this session
    - Connected Ratio: polips with network links
    - Type Diversity: entropy of polip types
    - Lifecycle Balance: distribution across stages
    """

    def __init__(self, glob: "Glob", engine: CalcificationEngine | None = None):
        self.glob = glob
        self.engine = engine or CalcificationEngine(glob)

    def calculate(self) -> HealthReport:
        """Calculate full health report."""
        index = self.glob.get_index()
        blobs_meta = index.get("blobs", {})

        total = len(blobs_meta)
        if total == 0:
            return HealthReport(
                vitality_score=0.0,
                total_polips=0,
                hot_ratio=0.0,
                connected_ratio=0.0,
                type_diversity=0.0,
                lifecycle_stages={},
                session_stats={},
                recommendations=["Create your first polip with 'reef sprout'"],
            )

        # Calculate vitals for all polips
        scores = self.engine.get_all_scores()

        # Hot ratio: polips with current session activity
        hot_count = sum(1 for s in scores if s.vitals.refs_this_session > 0)
        hot_ratio = hot_count / total

        # Connected ratio: polips with network links
        connected_count = sum(
            1 for s in scores
            if s.vitals.incoming_refs > 0 or s.vitals.outgoing_refs > 0
        )
        connected_ratio = connected_count / total

        # Type diversity
        type_div = self._type_diversity(blobs_meta)

        # Lifecycle distribution
        lifecycle = {}
        for s in scores:
            stage = s.lifecycle_stage
            lifecycle[stage] = lifecycle.get(stage, 0) + 1

        # Session stats
        session_stats = {
            "total_refs_this_session": sum(s.vitals.refs_this_session for s in scores),
            "avg_intensity": sum(s.intensity_score for s in scores) / total,
            "calcification_candidates": sum(1 for s in scores if s.should_calcify),
        }

        # Vitality score (weighted)
        vitality = (
            0.30 * hot_ratio +
            0.30 * connected_ratio +
            0.20 * type_div +
            0.20 * self._lifecycle_balance(lifecycle, total)
        )

        recommendations = self._generate_recommendations(
            hot_ratio, connected_ratio, type_div, lifecycle, total, scores
        )

        return HealthReport(
            vitality_score=vitality,
            total_polips=total,
            hot_ratio=hot_ratio,
            connected_ratio=connected_ratio,
            type_diversity=type_div,
            lifecycle_stages=lifecycle,
            session_stats=session_stats,
            recommendations=recommendations,
        )

    def _type_diversity(self, blobs: dict) -> float:
        """Shannon entropy of polip types (normalized 0-1)."""
        import math

        type_counts: dict[str, int] = {}
        for meta in blobs.values():
            t = meta.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        if not type_counts:
            return 0.0

        total = sum(type_counts.values())
        entropy = 0.0
        for count in type_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log(p)

        max_entropy = math.log(max(len(type_counts), 1))
        if max_entropy == 0:
            return 0.0

        return min(1.0, entropy / max_entropy)

    def _lifecycle_balance(self, stages: dict, total: int) -> float:
        """Score how balanced the lifecycle distribution is."""
        if total == 0:
            return 0.0
        non_empty = sum(1 for count in stages.values() if count > 0)
        return non_empty / 5  # 5 possible stages

    def _generate_recommendations(
        self,
        hot_ratio: float,
        connected_ratio: float,
        type_div: float,
        lifecycle: dict,
        total: int,
        scores: list[CalcificationScore],
    ) -> list[str]:
        """Generate actionable recommendations."""
        recs = []

        if hot_ratio < 0.1:
            recs.append("Low activity: surface relevant polips with /surface")

        if connected_ratio < 0.2:
            recs.append("Low connectivity: use [[wiki-links]] to connect related polips")

        if type_div < 0.3 and total > 3:
            recs.append("Low type diversity: consider adding decisions or constraints")

        spawning = lifecycle.get("spawning", 0)
        if spawning == total:
            recs.append("All polips are new: use them to build calcification")

        # Check for calcification candidates
        candidates = [s for s in scores if s.should_calcify]
        if candidates:
            recs.append(f"{len(candidates)} polip(s) ready for calcification")

        if not recs:
            recs.append("Reef is healthy!")

        return recs


# Convenience aliases
Calcification = CalcificationEngine
Decay = AdversarialDecay
Health = ReefHealth
