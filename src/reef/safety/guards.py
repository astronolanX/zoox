"""
Pruning safeguards - prevent catastrophic data loss from automated pruning.

P0 CRITICAL: These guards must be implemented before any auto-pruning.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class DryRunItem:
    """Single item in dry run report."""

    polip_id: str
    action: str  # delete | archive | merge
    reason: str
    confidence: float


@dataclass
class DryRunReport:
    """Report from dry run operation."""

    operation: str
    timestamp: datetime
    items: list[DryRunItem]
    summary: dict[str, int]
    warnings: list[str]
    would_exceed_threshold: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation,
            "timestamp": self.timestamp.isoformat(),
            "items": [
                {
                    "polip_id": i.polip_id,
                    "action": i.action,
                    "reason": i.reason,
                    "confidence": i.confidence,
                }
                for i in self.items
            ],
            "summary": self.summary,
            "warnings": self.warnings,
            "would_exceed_threshold": self.would_exceed_threshold,
        }


class PruningSafeguards:
    """Prevent catastrophic data loss from automated pruning."""

    # Halt if >25% of polips marked for deletion in single operation
    MAX_DELETION_RATE = 0.25

    # Never auto-prune polips with these scopes
    PROTECTED_SCOPES = {"always"}

    # Never auto-prune polips with these types
    PROTECTED_TYPES = {"constraint"}

    # Minimum polips before deletion rate kicks in
    MIN_POLIPS_FOR_RATE_CHECK = 4

    def __init__(self, project_dir: Path | None = None):
        """
        Initialize safeguards.

        Args:
            project_dir: Project directory for reef operations.
        """
        self.project_dir = project_dir or Path.cwd()

    def check_deletion_rate(self, candidates: list, total: int) -> tuple[bool, str]:
        """
        Halt if deletion rate exceeds threshold.

        Args:
            candidates: List of polips marked for deletion
            total: Total number of polips

        Returns:
            (safe_to_proceed, message)
        """
        if total < self.MIN_POLIPS_FOR_RATE_CHECK:
            return True, f"Skipping rate check: only {total} polips"

        rate = len(candidates) / total
        if rate > self.MAX_DELETION_RATE:
            return False, (
                f"HALT: Deletion rate {rate:.1%} exceeds threshold "
                f"{self.MAX_DELETION_RATE:.0%}. "
                f"{len(candidates)}/{total} polips would be deleted."
            )

        return True, f"Safe: {rate:.1%} deletion rate"

    def is_protected(self, polip) -> tuple[bool, str | None]:
        """
        Check if polip is immune to auto-pruning.

        Args:
            polip: Polip instance to check

        Returns:
            (is_protected, reason)
        """
        # Check scope
        scope = getattr(polip, "scope", None)
        if scope in self.PROTECTED_SCOPES:
            return True, f"Protected scope: {scope}"

        # Check type
        ptype = getattr(polip, "type", None)
        if ptype in self.PROTECTED_TYPES:
            return True, f"Protected type: {ptype}"

        return False, None

    def filter_protected(self, candidates: list) -> tuple[list, list]:
        """
        Filter out protected polips from candidates.

        Args:
            candidates: List of polips

        Returns:
            (prunable, protected) - two lists
        """
        prunable = []
        protected = []

        for polip in candidates:
            is_prot, reason = self.is_protected(polip)
            if is_prot:
                protected.append((polip, reason))
            else:
                prunable.append(polip)

        return prunable, protected

    def dry_run(
        self, operation: str, candidates: list, total: int
    ) -> DryRunReport:
        """
        Preview operation without executing.

        Args:
            operation: Operation name (prune, decay, sync)
            candidates: Polips that would be affected
            total: Total polips in reef

        Returns:
            Dry run report
        """
        items = []
        warnings = []

        # Filter protected
        prunable, protected = self.filter_protected(candidates)

        for polip in prunable:
            items.append(
                DryRunItem(
                    polip_id=getattr(polip, "id", str(polip)),
                    action="delete",
                    reason="Matched pruning criteria",
                    confidence=0.8,
                )
            )

        for polip, reason in protected:
            warnings.append(
                f"Skipped {getattr(polip, 'id', str(polip))}: {reason}"
            )

        # Check deletion rate
        safe, rate_msg = self.check_deletion_rate(prunable, total)
        if not safe:
            warnings.insert(0, rate_msg)

        return DryRunReport(
            operation=operation,
            timestamp=datetime.now(),
            items=items,
            summary={
                "would_delete": len(prunable),
                "protected": len(protected),
                "total": total,
            },
            warnings=warnings,
            would_exceed_threshold=not safe,
        )

    def approve_operation(
        self, dry_run: DryRunReport, force: bool = False
    ) -> tuple[bool, str]:
        """
        Approve operation based on dry run.

        Args:
            dry_run: Dry run report
            force: Override threshold check

        Returns:
            (approved, message)
        """
        if dry_run.would_exceed_threshold and not force:
            return False, (
                "Operation would exceed deletion threshold. "
                "Use --force to override."
            )

        if dry_run.warnings and not force:
            return False, f"Warnings present: {dry_run.warnings[0]}"

        return True, f"Approved: {dry_run.summary['would_delete']} deletions"
