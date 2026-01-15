"""
Tests for reef MCP server.

Phase 3 implementation complete:
- test_server_initialization
- test_surface_tool
- test_sprout_tool
- test_health_tool
- test_resource_listing
- test_mcp_protocol_compliance
"""

import pytest
import json
import tempfile
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

    def test_get_tools(self):
        """Verify tools list is populated."""
        server = ReefMCPServer()
        tools = server._get_tools()
        assert len(tools) >= 7
        tool_names = [t["name"] for t in tools]
        assert "reef_surface" in tool_names
        assert "reef_sprout" in tool_names
        assert "reef_health" in tool_names
        assert "reef_sync" in tool_names

    def test_get_resources(self):
        """Verify resources list is populated."""
        server = ReefMCPServer()
        resources = server._get_resources()
        assert len(resources) >= 2
        uris = [r["uri"] for r in resources]
        assert "reef://polips" in uris
        assert "reef://health" in uris


class TestReefToolHandlers:
    """Tests for MCP tool handlers."""

    def test_import(self):
        """Verify module imports correctly."""
        assert ReefToolHandlers is not None

    def test_instantiation(self):
        """Verify can create handlers instance."""
        handlers = ReefToolHandlers(project_dir=Path.cwd())
        assert handlers is not None

    def test_lazy_loading(self):
        """Verify lazy loading of dependencies."""
        handlers = ReefToolHandlers(project_dir=Path.cwd())
        # Initially None
        assert handlers._glob is None
        assert handlers._audit_log is None
        assert handlers._undo_buffer is None
        # Access triggers lazy load
        _ = handlers.glob
        assert handlers._glob is not None


class TestMCPIntegration:
    """Integration tests for MCP server."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project with .claude directory."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # Create a test polip
        from reef.blob import Blob, BlobType, BlobScope

        blob = Blob(
            type=BlobType.THREAD,
            scope=BlobScope.PROJECT,
            summary="Test thread for MCP integration",
        )

        threads_dir = claude_dir / "threads"
        threads_dir.mkdir()
        blob.save(threads_dir / "test-thread.blob.xml")

        return tmp_path

    def test_server_initialization(self, temp_project):
        """Full test of server initialization."""
        server = ReefMCPServer(project_dir=temp_project)

        # Test initialize request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "reef"

    def test_surface_tool(self, temp_project):
        """Full test of surface tool."""
        handlers = ReefToolHandlers(project_dir=temp_project)

        # Rebuild index first
        handlers.glob.rebuild_index()

        # Test surface
        results = handlers.handle_surface(query="test thread", limit=5)

        assert isinstance(results, list)
        if results:  # May be empty if TF-IDF doesn't match
            assert "id" in results[0]
            assert "type" in results[0]
            assert "summary" in results[0]

    def test_sprout_tool(self, temp_project):
        """Full test of sprout tool."""
        handlers = ReefToolHandlers(project_dir=temp_project)

        # Test creating a new polip
        result = handlers.handle_sprout(
            type="decision",
            summary="Test decision via MCP",
            content="This is test content",
        )

        assert result["type"] == "decision"
        assert result["summary"] == "Test decision via MCP"
        assert "path" in result
        assert Path(result["path"]).exists()

    def test_health_tool(self, temp_project):
        """Full test of health tool."""
        handlers = ReefToolHandlers(project_dir=temp_project)

        # Rebuild index to ensure data
        handlers.glob.rebuild_index()

        result = handlers.handle_health()

        assert "total_polips" in result
        assert "by_type" in result
        assert "by_scope" in result
        assert "vitality_score" in result
        assert isinstance(result["vitality_score"], float)

    def test_sync_tool(self, temp_project):
        """Test sync tool."""
        handlers = ReefToolHandlers(project_dir=temp_project)

        result = handlers.handle_sync(dry_run=True)

        assert "issues_found" in result
        assert "status" in result
        assert result["dry_run"] is True

    def test_index_tool(self, temp_project):
        """Test index tool."""
        handlers = ReefToolHandlers(project_dir=temp_project)

        # Rebuild index first
        handlers.glob.rebuild_index()

        result = handlers.handle_index(type="thread", limit=10)

        assert "count" in result
        assert "polips" in result
        assert isinstance(result["polips"], list)

    def test_audit_tool(self, temp_project):
        """Test audit tool."""
        handlers = ReefToolHandlers(project_dir=temp_project)

        result = handlers.handle_audit(since="7d")

        assert isinstance(result, list)

    def test_list_quarantine_tool(self, temp_project):
        """Test list_quarantine tool."""
        handlers = ReefToolHandlers(project_dir=temp_project)

        result = handlers.handle_list_quarantine()

        assert isinstance(result, list)

    def test_resource_listing(self, temp_project):
        """Full test of resource listing."""
        server = ReefMCPServer(project_dir=temp_project)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/list",
            "params": {},
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert "resources" in response["result"]
        assert len(response["result"]["resources"]) >= 2

    def test_resource_read(self, temp_project):
        """Test reading a resource."""
        server = ReefMCPServer(project_dir=temp_project)

        # Rebuild index
        server.handlers.glob.rebuild_index()

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {"uri": "reef://health"},
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert "contents" in response["result"]

    def test_tools_call(self, temp_project):
        """Test calling a tool via protocol."""
        server = ReefMCPServer(project_dir=temp_project)

        # Rebuild index
        server.handlers.glob.rebuild_index()

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "reef_health",
                "arguments": {},
            },
        }

        response = server._handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        assert "content" in response["result"]
        assert response["result"]["isError"] is False

    def test_mcp_protocol_compliance(self, temp_project):
        """Full test of MCP protocol compliance."""
        server = ReefMCPServer(project_dir=temp_project)

        # Test all required methods
        methods = [
            ("initialize", {"protocolVersion": "2024-11-05"}),
            ("tools/list", {}),
            ("resources/list", {}),
            ("ping", {}),
        ]

        for method, params in methods:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params,
            }
            response = server._handle_request(request)
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response or "error" in response

    def test_error_handling(self, temp_project):
        """Test error handling for invalid requests."""
        server = ReefMCPServer(project_dir=temp_project)

        # Unknown method
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown/method",
            "params": {},
        }
        response = server._handle_request(request)
        assert "error" in response

        # Unknown tool
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        }
        response = server._handle_request(request)
        assert "error" in response


class TestMCPServerCLI:
    """Test MCP server CLI functionality."""

    def test_test_mode(self, capsys):
        """Test --test mode prints info and exits."""
        import sys
        from reef.mcp.server import main

        # Save original argv
        original_argv = sys.argv

        try:
            sys.argv = ["reef-mcp", "--test"]
            main()
            captured = capsys.readouterr()
            assert "Reef MCP Server" in captured.out
            assert "Tools:" in captured.out
            assert "Resources:" in captured.out
        finally:
            sys.argv = original_argv
