"""
Tests for reef MCP server.

Phase 3 will implement:
- test_server_initialization
- test_surface_tool
- test_sprout_tool
- test_health_tool
- test_resource_listing
- test_mcp_protocol_compliance
"""

import pytest
from pathlib import Path

from reef.mcp import ReefMCPServer, ReefToolHandlers


class TestReefMCPServer:
    """Tests for MCP server."""

    def test_import(self):
        """Verify module imports correctly."""
        assert ReefMCPServer is not None

    def test_instantiation(self):
        """Verify can create MCP server instance."""
        server = ReefMCPServer()
        assert server is not None

    def test_project_dir_default(self):
        """Verify project_dir defaults to cwd."""
        server = ReefMCPServer()
        assert server.project_dir == Path.cwd()

    def test_project_dir_custom(self):
        """Verify custom project_dir works."""
        server = ReefMCPServer(project_dir=Path("/tmp/test"))
        assert server.project_dir == Path("/tmp/test")


class TestReefToolHandlers:
    """Tests for MCP tool handlers."""

    def test_import(self):
        """Verify module imports correctly."""
        assert ReefToolHandlers is not None

    def test_instantiation(self):
        """Verify can create handlers instance."""
        handlers = ReefToolHandlers(project_dir=Path.cwd())
        assert handlers is not None


# Phase 3 TODO tests

class TestMCPIntegration:
    """Integration tests for MCP server."""

    @pytest.mark.skip(reason="Requires Phase 3 implementation")
    def test_server_initialization(self):
        """Full test of server initialization."""
        pass

    @pytest.mark.skip(reason="Requires Phase 3 implementation")
    def test_surface_tool(self):
        """Full test of surface tool."""
        pass

    @pytest.mark.skip(reason="Requires Phase 3 implementation")
    def test_sprout_tool(self):
        """Full test of sprout tool."""
        pass

    @pytest.mark.skip(reason="Requires Phase 3 implementation")
    def test_health_tool(self):
        """Full test of health tool."""
        pass

    @pytest.mark.skip(reason="Requires Phase 3 implementation")
    def test_resource_listing(self):
        """Full test of resource listing."""
        pass

    @pytest.mark.skip(reason="Requires Phase 3 implementation")
    def test_mcp_protocol_compliance(self):
        """Full test of MCP protocol compliance."""
        pass
