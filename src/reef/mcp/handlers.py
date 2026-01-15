"""
Tool handlers for reef MCP server.

Maps MCP tool calls to reef operations.
"""

from datetime import datetime
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
        # Lazy imports to avoid circular dependency
        self._glob = None
        self._audit_log = None
        self._undo_buffer = None

    @property
    def glob(self):
        """Lazy-load Glob instance."""
        if self._glob is None:
            from reef.blob import Glob

            self._glob = Glob(self.project_dir)
        return self._glob

    @property
    def audit_log(self):
        """Lazy-load AuditLog instance."""
        if self._audit_log is None:
            from reef.safety.audit import AuditLog

            self._audit_log = AuditLog(self.project_dir)
        return self._audit_log

    @property
    def undo_buffer(self):
        """Lazy-load UndoBuffer instance."""
        if self._undo_buffer is None:
            from reef.safety.undo import UndoBuffer

            self._undo_buffer = UndoBuffer(self.project_dir)
        return self._undo_buffer

    def handle_surface(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Surface relevant polips based on query.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching polips with metadata
        """
        results = self.glob.search_index(query=query, limit=limit)

        polips = []
        for key, entry, score in results:
            polips.append(
                {
                    "id": key,
                    "type": entry.get("type"),
                    "scope": entry.get("scope"),
                    "summary": entry.get("summary"),
                    "updated": entry.get("updated"),
                    "score": round(score, 3),
                }
            )

        return polips

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
        from reef.blob import Blob, BlobType, BlobScope, BlobStatus

        # Map type string to enum
        type_map = {
            "thread": BlobType.THREAD,
            "decision": BlobType.DECISION,
            "constraint": BlobType.CONSTRAINT,
            "context": BlobType.CONTEXT,
            "fact": BlobType.FACT,
        }

        blob_type = type_map.get(type)
        if not blob_type:
            raise ValueError(f"Invalid polip type: {type}")

        # Map type to scope (same logic as CLI)
        scope_map = {
            BlobType.CONSTRAINT: BlobScope.ALWAYS,
            BlobType.THREAD: BlobScope.PROJECT,
            BlobType.DECISION: BlobScope.PROJECT,
            BlobType.FACT: BlobScope.PROJECT,
            BlobType.CONTEXT: BlobScope.SESSION,
        }
        scope = scope_map[blob_type]

        # Status for threads
        status = BlobStatus.ACTIVE if blob_type == BlobType.THREAD else None

        # Create blob
        blob = Blob(
            type=blob_type,
            scope=scope,
            summary=summary,
            status=status,
            files=files or [],
        )

        # Add content if provided
        if content:
            blob.context = content

        # Map type to subdirectory
        subdir_map = {
            BlobType.THREAD: "threads",
            BlobType.DECISION: "decisions",
            BlobType.CONSTRAINT: "constraints",
            BlobType.CONTEXT: "contexts",
            BlobType.FACT: "facts",
        }
        subdir = subdir_map.get(blob_type)

        # Generate name from summary (kebab-case, max 30 chars)
        name = summary.lower()
        name = "".join(c if c.isalnum() or c == " " else "" for c in name)
        name = "-".join(name.split())[:30]

        # Sprout the blob
        path = self.glob.sprout(blob, name, subdir)

        return {
            "id": name,
            "type": type,
            "summary": summary,
            "path": str(path),
            "created": datetime.now().isoformat(),
        }

    def handle_health(self) -> dict[str, Any]:
        """
        Get reef health metrics.

        Returns:
            Health report with vitality score and distribution
        """
        index = self.glob.get_index()
        blobs = index.get("blobs", {})

        # Count by type
        by_type: dict[str, int] = {}
        by_scope: dict[str, int] = {}
        total_access = 0

        for entry in blobs.values():
            blob_type = entry.get("type", "unknown")
            scope = entry.get("scope", "unknown")
            by_type[blob_type] = by_type.get(blob_type, 0) + 1
            by_scope[scope] = by_scope.get(scope, 0) + 1
            total_access += entry.get("access_count", 0)

        total = len(blobs)

        # Calculate vitality score (simplified)
        # Factors: diversity, activity, balance
        diversity_score = min(len(by_type) / 5, 1.0)  # Max 5 types
        activity_score = min(total_access / max(total * 3, 1), 1.0)  # Avg 3 accesses
        balance_score = 1.0 - (max(by_type.values(), default=0) / max(total, 1))

        vitality = round((diversity_score + activity_score + balance_score) / 3, 2)

        return {
            "total_polips": total,
            "by_type": by_type,
            "by_scope": by_scope,
            "total_access": total_access,
            "vitality_score": vitality,
            "cache_stats": self.glob.cache_stats(),
            "updated": index.get("updated"),
        }

    def handle_sync(self, dry_run: bool = True, fix: bool = False) -> dict[str, Any]:
        """
        Sync and optionally prune reef.

        Args:
            dry_run: Preview changes without executing
            fix: Apply fixes for integrity issues

        Returns:
            Sync report with changes made/previewed
        """
        issues = []
        fixes_applied = []

        # Check index vs actual files
        index = self.glob.get_index()
        indexed_keys = set(index.get("blobs", {}).keys())

        # Find orphaned index entries
        for key in indexed_keys:
            path = self.glob.claude_dir / key
            if not path.exists():
                issues.append({"type": "orphan_index", "key": key})
                if fix and not dry_run:
                    self.glob._remove_from_index(path)
                    fixes_applied.append(f"Removed orphan index entry: {key}")

        # Find unindexed files
        for subdir in [None, "threads", "constraints", "contexts", "decisions", "facts"]:
            search_dir = self.glob.claude_dir / subdir if subdir else self.glob.claude_dir
            if not search_dir.exists():
                continue

            for path in search_dir.glob("*.blob.xml"):
                key = self.glob._blob_key(path)
                if key not in indexed_keys:
                    issues.append({"type": "unindexed", "path": str(path)})
                    if fix and not dry_run:
                        try:
                            from reef.blob import Blob

                            blob = Blob.load(path)
                            self.glob._update_index(path, blob)
                            fixes_applied.append(f"Indexed: {key}")
                        except Exception:
                            pass

        return {
            "issues_found": len(issues),
            "issues": issues[:20],  # Limit output
            "dry_run": dry_run,
            "fixes_applied": fixes_applied if not dry_run else [],
            "status": "healthy" if not issues else "needs_attention",
        }

    def handle_index(
        self,
        query: str | None = None,
        type: str | None = None,
        scope: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Search polip index with filters.

        Args:
            query: Text search query
            type: Filter by polip type
            scope: Filter by scope
            limit: Maximum results

        Returns:
            Matching polips from index
        """
        results = self.glob.search_index(
            query=query,
            blob_type=type,
            scope=scope,
            limit=limit,
        )

        polips = []
        for key, entry, score in results:
            polips.append(
                {
                    "id": key,
                    "type": entry.get("type"),
                    "scope": entry.get("scope"),
                    "summary": entry.get("summary"),
                    "updated": entry.get("updated"),
                    "access_count": entry.get("access_count", 0),
                    "score": round(score, 3) if query else None,
                }
            )

        return {
            "count": len(polips),
            "query": query,
            "filters": {"type": type, "scope": scope},
            "polips": polips,
        }

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
        entries = self.audit_log.query(since=since, op_type=op_type, limit=50)

        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "op_type": entry.op_type,
                "polip_id": entry.polip_id,
                "reason": entry.reason,
                "agent": entry.agent,
            }
            for entry in entries
        ]

    def handle_undo(self, polip_id: str) -> dict[str, Any]:
        """
        Restore quarantined polip.

        Args:
            polip_id: ID of polip to restore

        Returns:
            Restored polip metadata
        """
        success, message = self.undo_buffer.restore(polip_id)

        return {
            "success": success,
            "message": message,
            "polip_id": polip_id,
        }

    def handle_list_quarantine(self) -> list[dict[str, Any]]:
        """
        List all quarantined polips.

        Returns:
            List of quarantined polip metadata
        """
        quarantined = self.undo_buffer.list_quarantined()

        return [
            {
                "polip_id": item.polip_id,
                "original_path": item.original_path,
                "quarantine_time": item.quarantine_time.isoformat(),
                "reason": item.reason,
                "expires": item.expires.isoformat() if item.expires else None,
            }
            for item in quarantined
        ]
