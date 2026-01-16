"""
MCP server implementation for reef.

Exposes reef operations (surface, sprout, sync, health) as MCP tools.
Uses stdlib-only JSON-RPC over stdio (no external dependencies).
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .handlers import ReefToolHandlers


@dataclass
class MCPCapabilities:
    """Server capabilities."""

    tools: bool = True
    resources: bool = True


class ReefMCPServer:
    """
    MCP server exposing reef operations.

    Implements JSON-RPC 2.0 over stdio for MCP protocol compliance.
    """

    VERSION = "2024-11-05"
    SERVER_NAME = "reef"
    SERVER_VERSION = "0.1.0"

    def __init__(self, project_dir: Path | None = None):
        """
        Initialize reef MCP server.

        Args:
            project_dir: Project directory containing .claude/ reef.
                        Defaults to current working directory.
        """
        self.project_dir = project_dir or Path.cwd()
        self.handlers = ReefToolHandlers(project_dir=self.project_dir)
        self._initialized = False
        self._running = False

    def _get_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools."""
        return [
            {
                "name": "reef_surface",
                "description": "Search and surface relevant polips based on query",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for finding relevant polips",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "reef_sprout",
                "description": "Create a new polip in the reef",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["thread", "decision", "constraint", "context", "fact"],
                            "description": "Polip type",
                        },
                        "summary": {
                            "type": "string",
                            "description": "Brief summary of the polip",
                        },
                        "content": {
                            "type": "string",
                            "description": "Full content",
                            "default": "",
                        },
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Associated files",
                        },
                    },
                    "required": ["type", "summary"],
                },
            },
            {
                "name": "reef_health",
                "description": "Get reef health metrics and vitality score",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "reef_sync",
                "description": "Check reef integrity and optionally fix issues",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dry_run": {
                            "type": "boolean",
                            "description": "Preview changes without executing",
                            "default": True,
                        },
                        "fix": {
                            "type": "boolean",
                            "description": "Apply fixes for integrity issues",
                            "default": False,
                        },
                    },
                },
            },
            {
                "name": "reef_index",
                "description": "Search polip index with filters",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Text search query",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["thread", "decision", "constraint", "context", "fact"],
                            "description": "Filter by polip type",
                        },
                        "scope": {
                            "type": "string",
                            "enum": ["always", "project", "session"],
                            "description": "Filter by scope",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results",
                            "default": 20,
                        },
                    },
                },
            },
            {
                "name": "reef_audit",
                "description": "Query audit log of automatic operations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "since": {
                            "type": "string",
                            "description": "Time filter (e.g., '7d', '24h')",
                        },
                        "op_type": {
                            "type": "string",
                            "description": "Filter by operation type (prune, calcify, merge, decay)",
                        },
                    },
                },
            },
            {
                "name": "reef_undo",
                "description": "Restore a quarantined polip",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "polip_id": {
                            "type": "string",
                            "description": "ID of polip to restore",
                        },
                    },
                    "required": ["polip_id"],
                },
            },
            {
                "name": "reef_list_quarantine",
                "description": "List all quarantined polips available for restoration",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            # ========== LIFECYCLE TOOLS (reef differentiators) ==========
            {
                "name": "reef_lifecycle",
                "description": "Get lifecycle status for all polips. Shows calcification stages: drifting (new), attached (growing), calcified (permanent), fossil (archived). This is reef's unique value - organic memory that evolves.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum polips to return",
                            "default": 20,
                        },
                    },
                },
            },
            {
                "name": "reef_calcify_candidates",
                "description": "Get polips ready for calcification. These have proven value through usage patterns and are candidates for promotion to permanent knowledge.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum candidates to return",
                            "default": 10,
                        },
                    },
                },
            },
            {
                "name": "reef_decay_status",
                "description": "Check which polips are at risk of decay due to low usage. Returns recommendations for maintaining reef health.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def _get_resources(self) -> list[dict[str, Any]]:
        """Get list of available resources."""
        return [
            {
                "uri": "reef://polips",
                "name": "Polip Index",
                "description": "List polips with metadata (summaries only, not full content)",
                "mimeType": "application/json",
            },
            {
                "uri": "reef://health",
                "name": "Reef Health",
                "description": "Current reef health metrics",
                "mimeType": "application/json",
            },
            {
                "uri": "reef://lifecycle",
                "name": "Lifecycle Status",
                "description": "Polip lifecycle stages and calcification status",
                "mimeType": "application/json",
            },
        ]

    def _handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Handle a single JSON-RPC request.

        Args:
            request: JSON-RPC request object

        Returns:
            JSON-RPC response object
        """
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            result = self._dispatch_method(method, params)
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)},
            }

    def _dispatch_method(self, method: str, params: dict[str, Any]) -> Any:
        """Dispatch method to handler."""
        if method == "initialize":
            return self._handle_initialize(params)
        elif method == "initialized":
            return None  # Notification, no response needed
        elif method == "tools/list":
            return {"tools": self._get_tools()}
        elif method == "tools/call":
            return self._handle_tool_call(params)
        elif method == "resources/list":
            return {"resources": self._get_resources()}
        elif method == "resources/read":
            return self._handle_resource_read(params)
        elif method == "ping":
            return {}
        else:
            raise ValueError(f"Unknown method: {method}")

    def _handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        self._initialized = True
        return {
            "protocolVersion": self.VERSION,
            "capabilities": {
                "tools": {},
                "resources": {},
            },
            "serverInfo": {
                "name": self.SERVER_NAME,
                "version": self.SERVER_VERSION,
            },
        }

    def _handle_tool_call(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        # Dispatch to appropriate handler
        if tool_name == "reef_surface":
            result = self.handlers.handle_surface(**arguments)
        elif tool_name == "reef_sprout":
            result = self.handlers.handle_sprout(**arguments)
        elif tool_name == "reef_health":
            result = self.handlers.handle_health()
        elif tool_name == "reef_sync":
            result = self.handlers.handle_sync(**arguments)
        elif tool_name == "reef_index":
            result = self.handlers.handle_index(**arguments)
        elif tool_name == "reef_audit":
            result = self.handlers.handle_audit(**arguments)
        elif tool_name == "reef_undo":
            result = self.handlers.handle_undo(**arguments)
        elif tool_name == "reef_list_quarantine":
            result = self.handlers.handle_list_quarantine()
        # Lifecycle tools (reef differentiators)
        elif tool_name == "reef_lifecycle":
            result = self.handlers.handle_lifecycle(**arguments)
        elif tool_name == "reef_calcify_candidates":
            result = self.handlers.handle_calcify_candidates(**arguments)
        elif tool_name == "reef_decay_status":
            result = self.handlers.handle_decay_status()
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        return {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            "isError": False,
        }

    def _handle_resource_read(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri", "")

        if uri == "reef://polips":
            result = self.handlers.handle_index()
        elif uri == "reef://health":
            result = self.handlers.handle_health()
        elif uri == "reef://lifecycle":
            result = self.handlers.handle_lifecycle()
        else:
            raise ValueError(f"Unknown resource: {uri}")

        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(result, indent=2),
                }
            ]
        }

    def _read_message(self) -> dict[str, Any] | None:
        """Read a JSON-RPC message from stdin."""
        # Read headers
        headers = {}
        while True:
            line = sys.stdin.readline()
            if not line or line == "\r\n" or line == "\n":
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        # Get content length
        content_length = int(headers.get("content-length", 0))
        if content_length == 0:
            return None

        # Read content
        content = sys.stdin.read(content_length)
        return json.loads(content)

    def _write_message(self, message: dict[str, Any]) -> None:
        """Write a JSON-RPC message to stdout."""
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        sys.stdout.write(header)
        sys.stdout.write(content)
        sys.stdout.flush()

    def start(self) -> None:
        """Start the MCP server (blocking)."""
        self._running = True

        while self._running:
            try:
                request = self._read_message()
                if request is None:
                    break

                response = self._handle_request(request)

                # Don't send response for notifications (no id)
                if "id" in request:
                    self._write_message(response)

            except json.JSONDecodeError:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                # Log error but continue
                sys.stderr.write(f"Error: {e}\n")
                sys.stderr.flush()

    def stop(self) -> None:
        """Stop the MCP server."""
        self._running = False


def main():
    """Entry point for MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="Reef MCP Server")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory containing .claude/",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: print server info and exit",
    )

    args = parser.parse_args()

    server = ReefMCPServer(project_dir=args.project_dir)

    if args.test:
        print(f"Reef MCP Server v{server.SERVER_VERSION}")
        print(f"Project: {server.project_dir}")
        print(f"Tools: {len(server._get_tools())}")
        print(f"Resources: {len(server._get_resources())}")
        return

    server.start()


if __name__ == "__main__":
    main()
