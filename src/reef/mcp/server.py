"""
MCP server implementation for reef.

Exposes reef operations (surface, sprout, sync, health) as MCP tools.
"""

from pathlib import Path
from typing import Any

# Note: MCP package will be added in Phase 3
# For now, this is a scaffold that will be implemented when MCP is integrated


class ReefMCPServer:
    """MCP server exposing reef operations."""

    def __init__(self, project_dir: Path | None = None):
        """
        Initialize reef MCP server.

        Args:
            project_dir: Project directory containing .claude/ reef.
                        Defaults to current working directory.
        """
        self.project_dir = project_dir or Path.cwd()
        self._tools: dict[str, Any] = {}
        self._resources: dict[str, Any] = {}

    def _register_tools(self) -> None:
        """Register reef operations as MCP tools."""
        # Will be implemented in Phase 3
        pass

    def _register_resources(self) -> None:
        """Register reef resources."""
        # Will be implemented in Phase 3
        pass

    def start(self) -> None:
        """Start the MCP server."""
        # Will be implemented in Phase 3
        raise NotImplementedError("MCP server will be implemented in Phase 3")

    def stop(self) -> None:
        """Stop the MCP server."""
        # Will be implemented in Phase 3
        pass
