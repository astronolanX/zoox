"""
Audit trail - track all automatic operations for debugging.

Logs operations to .claude/audit/ for transparency and debugging.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import json


@dataclass
class AuditEntry:
    """Single audit log entry."""

    timestamp: datetime
    op_type: str  # prune | calcify | merge | decay
    polip_id: str
    reason: str
    agent: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "op_type": self.op_type,
            "polip_id": self.polip_id,
            "reason": self.reason,
            "agent": self.agent,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditEntry":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            op_type=data["op_type"],
            polip_id=data["polip_id"],
            reason=data["reason"],
            agent=data.get("agent"),
            details=data.get("details"),
        )


class AuditLog:
    """Track all automatic operations for debugging."""

    AUDIT_DIR = ".claude/audit"
    LOG_FORMAT = "audit-{date}.jsonl"

    def __init__(self, project_dir: Path | None = None):
        """
        Initialize audit log.

        Args:
            project_dir: Project directory containing .claude/
        """
        self.project_dir = project_dir or Path.cwd()
        self.audit_dir = self.project_dir / self.AUDIT_DIR

    def _ensure_dir(self) -> None:
        """Ensure audit directory exists."""
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_path(self, date: datetime | None = None) -> Path:
        """Get log file path for date."""
        date = date or datetime.now()
        filename = self.LOG_FORMAT.format(date=date.strftime("%Y-%m-%d"))
        return self.audit_dir / filename

    def log_operation(
        self,
        op_type: str,
        polip_id: str,
        reason: str,
        agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """
        Log operation to audit trail.

        Args:
            op_type: Operation type (prune, calcify, merge, decay)
            polip_id: ID of affected polip
            reason: Reason for operation
            agent: Agent that initiated operation
            details: Additional details

        Returns:
            Created audit entry
        """
        self._ensure_dir()

        entry = AuditEntry(
            timestamp=datetime.now(),
            op_type=op_type,
            polip_id=polip_id,
            reason=reason,
            agent=agent,
            details=details,
        )

        # Append to daily log file (JSONL format)
        log_path = self._get_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

        return entry

    def query(
        self,
        since: datetime | timedelta | str | None = None,
        op_type: str | None = None,
        polip_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """
        Query audit log.

        Args:
            since: Start time (datetime, timedelta, or string like "7d", "24h")
            op_type: Filter by operation type
            polip_id: Filter by polip ID
            limit: Maximum entries to return

        Returns:
            List of matching audit entries
        """
        # Parse since parameter
        if isinstance(since, str):
            since = self._parse_time_string(since)
        elif isinstance(since, timedelta):
            since = datetime.now() - since

        entries = []

        # Read all log files in audit dir
        if not self.audit_dir.exists():
            return entries

        for log_file in sorted(self.audit_dir.glob("audit-*.jsonl"), reverse=True):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                        entry = AuditEntry.from_dict(data)

                        # Apply filters
                        if since and entry.timestamp < since:
                            continue
                        if op_type and entry.op_type != op_type:
                            continue
                        if polip_id and entry.polip_id != polip_id:
                            continue

                        entries.append(entry)

                        if len(entries) >= limit:
                            return entries

                    except (json.JSONDecodeError, KeyError):
                        continue

        return entries

    def _parse_time_string(self, time_str: str) -> datetime:
        """
        Parse time string like "7d", "24h", "30m".

        Args:
            time_str: Time string

        Returns:
            Datetime representing that time ago
        """
        now = datetime.now()

        if time_str.endswith("d"):
            days = int(time_str[:-1])
            return now - timedelta(days=days)
        elif time_str.endswith("h"):
            hours = int(time_str[:-1])
            return now - timedelta(hours=hours)
        elif time_str.endswith("m"):
            minutes = int(time_str[:-1])
            return now - timedelta(minutes=minutes)
        else:
            raise ValueError(f"Invalid time string: {time_str}")

    def get_recent(self, count: int = 10) -> list[AuditEntry]:
        """
        Get most recent entries.

        Args:
            count: Number of entries

        Returns:
            List of recent entries
        """
        return self.query(limit=count)

    def summarize(
        self, since: datetime | timedelta | str | None = None
    ) -> dict[str, Any]:
        """
        Get summary statistics.

        Args:
            since: Time period to summarize

        Returns:
            Summary with counts by operation type
        """
        entries = self.query(since=since, limit=10000)

        by_type: dict[str, int] = {}
        by_agent: dict[str, int] = {}

        for entry in entries:
            by_type[entry.op_type] = by_type.get(entry.op_type, 0) + 1
            if entry.agent:
                by_agent[entry.agent] = by_agent.get(entry.agent, 0) + 1

        return {
            "total": len(entries),
            "by_type": by_type,
            "by_agent": by_agent,
            "period": str(since) if since else "all",
        }
