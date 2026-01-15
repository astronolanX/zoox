"""
Tool handlers for reef MCP server.

Maps MCP tool calls to reef operations.
"""

from pathlib import Path
from typing import Any


class ReefToolHandlers:
    """Handlers for reef MCP tools."""

    def __init__(self, project_dir: Path):
        """
        Initialize tool handlers.

        Args:
            project_dir: Project directory containing .claude/ reef.
        """
        self.project_dir = project_dir
        # Lazy import to avoid circular dependency
        self._glob = None

    @property
    def glob(self):
        """Lazy-load Glob instance."""
        if self._glob is None:
            from reef.blob import Glob
            self._glob = Glob(self.project_dir)
        return self._glob

    def handle_surface(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Surface relevant polips based on query.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching polips with metadata
        """
        # Will be implemented in Phase 3
        raise NotImplementedError("Will be implemented in Phase 3")

    def handle_sprout(
        self,
        type: str,
        summary: str,
        content: str = "",
        files: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new polip.

        Args:
            type: Polip type (thread, decision, constraint, context, fact)
            summary: Brief summary
            content: Full content
            files: Associated files

        Returns:
            Created polip metadata
        """
        # Will be implemented in Phase 3
        raise NotImplementedError("Will be implemented in Phase 3")

    def handle_health(self) -> dict[str, Any]:
        """
        Get reef health metrics.

        Returns:
            Health report with vitality score and distribution
        """
        # Will be implemented in Phase 3
        raise NotImplementedError("Will be implemented in Phase 3")

    def handle_sync(self, dry_run: bool = True, fix: bool = False) -> dict[str, Any]:
        """
        Sync and optionally prune reef.

        Args:
            dry_run: Preview changes without executing
            fix: Apply fixes for integrity issues

        Returns:
            Sync report with changes made/previewed
        """
        # Will be implemented in Phase 3
        raise NotImplementedError("Will be implemented in Phase 3")

    def handle_audit(
        self, since: str | None = None, op_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Query audit log.

        Args:
            since: Time filter (e.g., "7d", "24h")
            op_type: Operation type filter

        Returns:
            List of audit entries
        """
        # Will be implemented in Phase 3
        raise NotImplementedError("Will be implemented in Phase 3")

    def handle_undo(self, polip_id: str) -> dict[str, Any]:
        """
        Restore quarantined polip.

        Args:
            polip_id: ID of polip to restore

        Returns:
            Restored polip metadata
        """
        # Will be implemented in Phase 3
        raise NotImplementedError("Will be implemented in Phase 3")
