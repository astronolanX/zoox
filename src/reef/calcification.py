"""
Calcification engine - organic growth mechanics for reef.

Implements the core thesis: schema emerges from usage, not design.
Polips crystallize through Time × Usage × Ceremony × Consensus.
Selection pressure through adversarial decay keeps the reef healthy.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
class CalcificationScore:
    """Detailed breakdown of calcification scoring."""
    polip_key: str
    total: float
    time_score: float
    usage_score: float
    ceremony_score: float
    consensus_score: float
    should_calcify: bool

    def to_dict(self) -> dict:
        return {
            "polip": self.polip_key,
            "total": round(self.total, 3),
            "breakdown": {
                "time": round(self.time_score, 3),
                "usage": round(self.usage_score, 3),
                "ceremony": round(self.ceremony_score, 3),
                "consensus": round(self.consensus_score, 3),
            },
            "should_calcify": self.should_calcify,
        }


class CalcificationEngine:
    """
    Determines when polips should calcify into bedrock.

    Calcification triggers (combinatorial):
    - Time: Stability over 30+ days (weight: 0.2)
    - Usage: 10+ accesses via LRU tracking (weight: 0.3)
    - Ceremony: Explicit human promotion (weight: 0.2)
    - Consensus: 3+ references from other polips (weight: 0.3)

    A polip calcifies when total score >= 0.7 (tunable threshold).
    """

    # Trigger weights must sum to 1.0
    TRIGGERS = {
        "time": {"weight": 0.2, "threshold_days": 30},
        "usage": {"weight": 0.3, "threshold_count": 10},
        "ceremony": {"weight": 0.2, "required": False},
        "consensus": {"weight": 0.3, "threshold_refs": 3},
    }

    CALCIFICATION_THRESHOLD = 0.7

    def __init__(self, glob: "Glob"):
        self.glob = glob

    def score_polip(self, key: str, blob: "Blob") -> CalcificationScore:
        """
        Calculate calcification score for a polip.

        Args:
            key: Index key for the polip
            blob: The Blob object

        Returns:
            CalcificationScore with breakdown
        """
        index = self.glob.get_index()
        blob_meta = index.get("blobs", {}).get(key, {})

        # Time score: normalized age in days
        time_score = self._score_time(blob)

        # Usage score: normalized access count
        usage_score = self._score_usage(blob_meta)

        # Ceremony score: check if explicitly promoted
        ceremony_score = self._score_ceremony(blob)

        # Consensus score: count incoming references
        consensus_score = self._score_consensus(key, index)

        # Weighted total
        total = (
            time_score * self.TRIGGERS["time"]["weight"] +
            usage_score * self.TRIGGERS["usage"]["weight"] +
            ceremony_score * self.TRIGGERS["ceremony"]["weight"] +
            consensus_score * self.TRIGGERS["consensus"]["weight"]
        )

        return CalcificationScore(
            polip_key=key,
            total=total,
            time_score=time_score,
            usage_score=usage_score,
            ceremony_score=ceremony_score,
            consensus_score=consensus_score,
            should_calcify=total >= self.CALCIFICATION_THRESHOLD,
        )

    def _score_time(self, blob: "Blob") -> float:
        """Score based on age (0-1, saturates at 2x threshold)."""
        threshold = self.TRIGGERS["time"]["threshold_days"]
        age_days = (datetime.now() - blob.updated).days
        # Sigmoid-like: 0 at 0 days, 0.5 at threshold, ~1 at 2x threshold
        return min(1.0, age_days / (threshold * 2))

    def _score_usage(self, meta: dict) -> float:
        """Score based on access count (0-1, saturates at 2x threshold)."""
        threshold = self.TRIGGERS["usage"]["threshold_count"]
        count = meta.get("access_count", 0)
        return min(1.0, count / (threshold * 2))

    def _score_ceremony(self, blob: "Blob") -> float:
        """Score 1.0 if explicitly promoted via ceremony."""
        # Ceremony is indicated by scope=always OR type=constraint
        # These require explicit human action to set
        from .blob import BlobScope, BlobType
        if blob.scope == BlobScope.ALWAYS:
            return 1.0
        if blob.type == BlobType.CONSTRAINT:
            return 1.0
        return 0.0

    def _score_consensus(self, key: str, index: dict) -> float:
        """Score based on incoming references from other polips."""
        threshold = self.TRIGGERS["consensus"]["threshold_refs"]

        # Extract polip name from key (e.g., "threads/foo.blob.xml" -> "foo")
        polip_name = Path(key).stem.replace(".blob", "")

        # Count how many other polips reference this one
        ref_count = 0
        for other_key, meta in index.get("blobs", {}).items():
            if other_key == key:
                continue
            related = meta.get("related", [])
            if polip_name in related or key in related:
                ref_count += 1

        return min(1.0, ref_count / (threshold * 2))

    def _iter_all_blobs(self):
        """Iterate over all blobs from root and subdirs."""
        from .blob import KNOWN_SUBDIRS

        # Root blobs
        for name, blob in self.glob.list_blobs():
            key = f"{name}.blob.xml"
            yield key, blob

        # Subdir blobs
        for subdir in KNOWN_SUBDIRS:
            for name, blob in self.glob.list_blobs(subdir):
                key = f"{subdir}/{name}.blob.xml"
                yield key, blob

    def get_candidates(self) -> list[CalcificationScore]:
        """
        Get all polips that are candidates for calcification.

        Returns:
            List of CalcificationScore objects for polips above threshold,
            sorted by score descending.
        """
        candidates = []

        for key, blob in self._iter_all_blobs():
            score = self.score_polip(key, blob)
            if score.should_calcify:
                candidates.append(score)

        return sorted(candidates, key=lambda s: s.total, reverse=True)

    def get_all_scores(self) -> list[CalcificationScore]:
        """Get scores for all polips, regardless of threshold."""
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
    Selection pressure through adversarial challenge.

    Challenge triggers:
    - Staleness: 60+ days since update with <3 accesses
    - Orphan: No references for 30+ days
    - Contradiction: Validator detects conflicts (requires external validator)

    Outcomes:
    - SURVIVE: Polip justifies continued existence
    - MERGE: Absorb into another polip
    - DECOMPOSE: Archive to fossil layer
    """

    CHALLENGE_TRIGGERS = {
        "staleness": {"days": 60, "min_access": 3},
        "orphan": {"no_refs_days": 30},
        "contradiction": {"requires_validator": True},
    }

    # Protected scopes never face challenge
    PROTECTED_SCOPES = ["always"]

    def __init__(self, glob: "Glob"):
        self.glob = glob

    def _iter_all_blobs(self):
        """Iterate over all blobs from root and subdirs."""
        from .blob import KNOWN_SUBDIRS

        # Root blobs
        for name, blob in self.glob.list_blobs():
            key = f"{name}.blob.xml"
            yield key, blob

        # Subdir blobs
        for subdir in KNOWN_SUBDIRS:
            for name, blob in self.glob.list_blobs(subdir):
                key = f"{subdir}/{name}.blob.xml"
                yield key, blob

    def get_challengers(self) -> list[tuple[str, "Blob", str]]:
        """
        Get polips that should face adversarial challenge.

        Returns:
            List of (key, blob, trigger_type) tuples
        """
        challengers = []
        index = self.glob.get_index()
        now = datetime.now()

        for key, blob in self._iter_all_blobs():
            meta = index.get("blobs", {}).get(key, {})

            # Skip protected scopes
            if blob.scope.value in self.PROTECTED_SCOPES:
                continue

            # Check staleness
            age_days = (now - blob.updated).days
            access_count = meta.get("access_count", 0)
            staleness_cfg = self.CHALLENGE_TRIGGERS["staleness"]

            if age_days >= staleness_cfg["days"] and access_count < staleness_cfg["min_access"]:
                challengers.append((key, blob, "staleness"))
                continue

            # Check orphan status
            orphan_cfg = self.CHALLENGE_TRIGGERS["orphan"]
            if age_days >= orphan_cfg["no_refs_days"]:
                # Count incoming refs
                polip_name = Path(key).stem.replace(".blob", "")
                has_refs = False
                for other_key, other_meta in index.get("blobs", {}).items():
                    if other_key == key:
                        continue
                    related = other_meta.get("related", [])
                    if polip_name in related or key in related:
                        has_refs = True
                        break

                if not has_refs:
                    challengers.append((key, blob, "orphan"))

        return challengers

    def challenge(self, key: str, blob: "Blob", trigger: str) -> ChallengeReport:
        """
        Challenge a polip to defend its relevance.

        Simple heuristic defense:
        - High access count = SURVIVE
        - Has outgoing refs to active polips = MERGE candidate
        - Otherwise = DECOMPOSE

        Args:
            key: Index key for the polip
            blob: The Blob object
            trigger: What triggered the challenge

        Returns:
            ChallengeReport with outcome
        """
        index = self.glob.get_index()
        meta = index.get("blobs", {}).get(key, {})
        access_count = meta.get("access_count", 0)

        # Defense 1: High usage = survive
        if access_count >= 5:
            return ChallengeReport(
                polip_key=key,
                trigger=trigger,
                result=ChallengeResult.SURVIVE,
                reason=f"High usage ({access_count} accesses) justifies existence",
            )

        # Defense 2: Has valuable outgoing links = merge candidate
        if blob.related and len(blob.related) > 0:
            # Check if any related polips are still active
            for ref in blob.related:
                ref_key = f"{ref}.blob.xml"
                if ref_key in index.get("blobs", {}):
                    return ChallengeReport(
                        polip_key=key,
                        trigger=trigger,
                        result=ChallengeResult.MERGE,
                        reason=f"Has active reference to {ref}, consider merging",
                    )

        # No defense = decompose
        return ChallengeReport(
            polip_key=key,
            trigger=trigger,
            result=ChallengeResult.DECOMPOSE,
            reason=f"No justification for continued existence ({trigger})",
        )

    def run_challenges(self, dry_run: bool = True) -> list[ChallengeReport]:
        """
        Run adversarial challenges on all eligible polips.

        Args:
            dry_run: If True, report without taking action

        Returns:
            List of challenge reports
        """
        reports = []
        challengers = self.get_challengers()

        for key, blob, trigger in challengers:
            report = self.challenge(key, blob, trigger)
            reports.append(report)

            if not dry_run and report.result == ChallengeResult.DECOMPOSE:
                # Move to quarantine (handled by safety module)
                pass

        return reports


@dataclass
class HealthReport:
    """Reef ecosystem health metrics."""
    vitality_score: float
    total_polips: int
    active_ratio: float
    reference_density: float
    age_distribution: dict
    type_diversity: float
    lifecycle_stages: dict
    recommendations: list[str]

    def to_dict(self) -> dict:
        return {
            "vitality_score": round(self.vitality_score, 3),
            "total_polips": self.total_polips,
            "active_ratio": round(self.active_ratio, 3),
            "reference_density": round(self.reference_density, 3),
            "age_distribution": self.age_distribution,
            "type_diversity": round(self.type_diversity, 3),
            "lifecycle_stages": self.lifecycle_stages,
            "recommendations": self.recommendations,
        }


class ReefHealth:
    """
    Ecosystem health metrics for the reef.

    Measures:
    - Vitality Score: Overall health 0-1
    - Active Ratio: Proportion of recently accessed polips
    - Reference Density: Average refs per polip
    - Age Distribution: Spread across lifecycle stages
    - Type Diversity: Shannon entropy of polip types
    """

    # Lifecycle stage thresholds (days)
    LIFECYCLE_STAGES = {
        "spawning": 7,      # < 7 days old
        "drifting": 30,     # 7-30 days
        "attached": 90,     # 30-90 days
        "calcified": 180,   # 90-180 days
        "fossil": float("inf"),  # > 180 days
    }

    def __init__(self, glob: "Glob"):
        self.glob = glob

    def calculate(self) -> HealthReport:
        """Calculate full health report."""
        index = self.glob.get_index()
        blobs_meta = index.get("blobs", {})

        total = len(blobs_meta)
        if total == 0:
            return HealthReport(
                vitality_score=0.0,
                total_polips=0,
                active_ratio=0.0,
                reference_density=0.0,
                age_distribution={},
                type_diversity=0.0,
                lifecycle_stages={stage: 0 for stage in self.LIFECYCLE_STAGES},
                recommendations=["Create your first polip with 'reef sprout'"],
            )

        # Gather metrics
        active_ratio = self._active_ratio(blobs_meta)
        ref_density = self._reference_density(blobs_meta)
        age_dist = self._age_distribution(blobs_meta)
        type_div = self._type_diversity(blobs_meta)
        lifecycle = self._lifecycle_distribution(blobs_meta)

        # Calculate vitality score (weighted combination)
        vitality = (
            0.25 * active_ratio +
            0.25 * min(1.0, ref_density / 2.0) +  # Cap at 2 refs/polip
            0.25 * type_div +
            0.25 * self._lifecycle_balance(lifecycle, total)
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            active_ratio, ref_density, type_div, lifecycle, total
        )

        return HealthReport(
            vitality_score=vitality,
            total_polips=total,
            active_ratio=active_ratio,
            reference_density=ref_density,
            age_distribution=age_dist,
            type_diversity=type_div,
            lifecycle_stages=lifecycle,
            recommendations=recommendations,
        )

    def _active_ratio(self, blobs: dict) -> float:
        """Proportion of polips accessed in last 30 days."""
        if not blobs:
            return 0.0
        active = sum(1 for m in blobs.values() if m.get("access_count", 0) > 0)
        return active / len(blobs)

    def _reference_density(self, blobs: dict) -> float:
        """Average number of references per polip."""
        if not blobs:
            return 0.0
        total_refs = sum(len(m.get("related", [])) for m in blobs.values())
        return total_refs / len(blobs)

    def _age_distribution(self, blobs: dict) -> dict:
        """Count of polips by age bracket."""
        brackets = {"<7d": 0, "7-30d": 0, "30-90d": 0, "90-180d": 0, ">180d": 0}
        now = datetime.now()

        for meta in blobs.values():
            updated_str = meta.get("updated", "")
            if not updated_str:
                continue
            try:
                updated = datetime.strptime(updated_str, "%Y-%m-%d")
                age = (now - updated).days

                if age < 7:
                    brackets["<7d"] += 1
                elif age < 30:
                    brackets["7-30d"] += 1
                elif age < 90:
                    brackets["30-90d"] += 1
                elif age < 180:
                    brackets["90-180d"] += 1
                else:
                    brackets[">180d"] += 1
            except ValueError:
                pass

        return brackets

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

        # Normalize by max possible entropy (log of number of types)
        max_entropy = math.log(max(len(type_counts), 1))
        if max_entropy == 0:
            return 0.0

        return min(1.0, entropy / max_entropy)

    def _lifecycle_distribution(self, blobs: dict) -> dict:
        """Count polips in each lifecycle stage."""
        stages = {stage: 0 for stage in self.LIFECYCLE_STAGES}
        now = datetime.now()

        for meta in blobs.values():
            updated_str = meta.get("updated", "")
            if not updated_str:
                continue
            try:
                updated = datetime.strptime(updated_str, "%Y-%m-%d")
                age = (now - updated).days

                for stage, threshold in self.LIFECYCLE_STAGES.items():
                    if age < threshold:
                        stages[stage] += 1
                        break
            except ValueError:
                pass

        return stages

    def _lifecycle_balance(self, stages: dict, total: int) -> float:
        """Score how balanced the lifecycle distribution is."""
        if total == 0:
            return 0.0

        # Ideal: some in each stage (not all fossils, not all spawning)
        non_empty = sum(1 for count in stages.values() if count > 0)
        max_stages = len(self.LIFECYCLE_STAGES)

        return non_empty / max_stages

    def _generate_recommendations(
        self,
        active_ratio: float,
        ref_density: float,
        type_div: float,
        lifecycle: dict,
        total: int,
    ) -> list[str]:
        """Generate actionable recommendations."""
        recs = []

        if active_ratio < 0.3:
            recs.append("Low activity: review and prune unused polips")

        if ref_density < 0.5:
            recs.append("Low connectivity: use [[wiki-links]] to connect related polips")

        if type_div < 0.3 and total > 3:
            recs.append("Low type diversity: consider adding decisions or constraints")

        if lifecycle.get("fossil", 0) > total * 0.5:
            recs.append("Many fossils: run 'reef decay challenge' to clean up")

        if lifecycle.get("spawning", 0) == total:
            recs.append("All polips are new: give them time to mature")

        if not recs:
            recs.append("Reef is healthy!")

        return recs


# Convenience aliases for coral terminology
Calcification = CalcificationEngine
Decay = AdversarialDecay
Health = ReefHealth
