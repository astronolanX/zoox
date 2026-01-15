"""
Undo buffer - quarantine deleted polips for recovery.

Moves deleted polips to .claude/quarantine/ instead of permanent deletion.
Expired items are permanently deleted after QUARANTINE_DAYS.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import json
import shutil


@dataclass
class QuarantinedPolip:
    """Metadata for quarantined polip."""

    polip_id: str
    original_path: str
    quarantine_time: datetime
    reason: str
    agent: str | None = None
    expires: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "polip_id": self.polip_id,
            "original_path": self.original_path,
            "quarantine_time": self.quarantine_time.isoformat(),
            "reason": self.reason,
            "agent": self.agent,
            "expires": self.expires.isoformat() if self.expires else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuarantinedPolip":
        """Create from dictionary."""
        return cls(
            polip_id=data["polip_id"],
            original_path=data["original_path"],
            quarantine_time=datetime.fromisoformat(data["quarantine_time"]),
            reason=data["reason"],
            agent=data.get("agent"),
            expires=datetime.fromisoformat(data["expires"])
            if data.get("expires")
            else None,
        )


class UndoBuffer:
    """Quarantine deleted polips for recovery."""

    QUARANTINE_DIR = ".claude/quarantine"
    METADATA_FILE = "quarantine.json"
    QUARANTINE_DAYS = 7

    def __init__(self, project_dir: Path | None = None):
        """
        Initialize undo buffer.

        Args:
            project_dir: Project directory containing .claude/
        """
        self.project_dir = project_dir or Path.cwd()
        self.quarantine_dir = self.project_dir / self.QUARANTINE_DIR

    def _ensure_dir(self) -> None:
        """Ensure quarantine directory exists."""
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def _load_metadata(self) -> dict[str, QuarantinedPolip]:
        """Load quarantine metadata."""
        meta_path = self.quarantine_dir / self.METADATA_FILE
        if not meta_path.exists():
            return {}

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    k: QuarantinedPolip.from_dict(v) for k, v in data.items()
                }
        except (json.JSONDecodeError, KeyError):
            return {}

    def _save_metadata(self, metadata: dict[str, QuarantinedPolip]) -> None:
        """Save quarantine metadata."""
        self._ensure_dir()
        meta_path = self.quarantine_dir / self.METADATA_FILE

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({k: v.to_dict() for k, v in metadata.items()}, f, indent=2)

    def quarantine(
        self,
        polip_path: Path,
        polip_id: str,
        reason: str,
        agent: str | None = None,
    ) -> QuarantinedPolip:
        """
        Move polip to quarantine instead of deleting.

        Args:
            polip_path: Path to polip file
            polip_id: Polip ID
            reason: Reason for quarantine
            agent: Agent that initiated deletion

        Returns:
            Quarantine metadata
        """
        self._ensure_dir()

        # Calculate expiry
        now = datetime.now()
        expires = now + timedelta(days=self.QUARANTINE_DAYS)

        # Create metadata
        meta = QuarantinedPolip(
            polip_id=polip_id,
            original_path=str(polip_path),
            quarantine_time=now,
            reason=reason,
            agent=agent,
            expires=expires,
        )

        # Move file to quarantine
        quarantine_path = self.quarantine_dir / polip_path.name
        if polip_path.exists():
            shutil.move(str(polip_path), str(quarantine_path))

        # Update metadata
        metadata = self._load_metadata()
        metadata[polip_id] = meta
        self._save_metadata(metadata)

        return meta

    def restore(self, polip_id: str) -> tuple[bool, str]:
        """
        Restore polip from quarantine.

        Args:
            polip_id: ID of polip to restore

        Returns:
            (success, message)
        """
        metadata = self._load_metadata()

        if polip_id not in metadata:
            return False, f"Polip {polip_id} not found in quarantine"

        meta = metadata[polip_id]
        original_path = Path(meta.original_path)
        quarantine_path = self.quarantine_dir / original_path.name

        if not quarantine_path.exists():
            return False, f"Quarantine file not found: {quarantine_path}"

        # Ensure original directory exists
        original_path.parent.mkdir(parents=True, exist_ok=True)

        # Move back to original location
        shutil.move(str(quarantine_path), str(original_path))

        # Remove from metadata
        del metadata[polip_id]
        self._save_metadata(metadata)

        return True, f"Restored {polip_id} to {original_path}"

    def list_quarantined(self) -> list[QuarantinedPolip]:
        """
        List all quarantined polips.

        Returns:
            List of quarantine metadata
        """
        metadata = self._load_metadata()
        return list(metadata.values())

    def expire_old(self) -> list[str]:
        """
        Permanently delete polips older than QUARANTINE_DAYS.

        Returns:
            List of expired polip IDs
        """
        metadata = self._load_metadata()
        now = datetime.now()
        expired = []

        for polip_id, meta in list(metadata.items()):
            if meta.expires and now > meta.expires:
                # Permanently delete
                quarantine_path = self.quarantine_dir / Path(meta.original_path).name
                if quarantine_path.exists():
                    quarantine_path.unlink()

                del metadata[polip_id]
                expired.append(polip_id)

        if expired:
            self._save_metadata(metadata)

        return expired

    def get_info(self, polip_id: str) -> QuarantinedPolip | None:
        """
        Get quarantine info for polip.

        Args:
            polip_id: Polip ID

        Returns:
            Quarantine metadata or None
        """
        metadata = self._load_metadata()
        return metadata.get(polip_id)

    def clear_all(self, confirm: bool = False) -> tuple[int, str]:
        """
        Clear all quarantined polips (DANGEROUS).

        Args:
            confirm: Must be True to proceed

        Returns:
            (count, message)
        """
        if not confirm:
            return 0, "Must pass confirm=True to clear quarantine"

        metadata = self._load_metadata()
        count = len(metadata)

        # Delete all quarantined files
        for meta in metadata.values():
            quarantine_path = self.quarantine_dir / Path(meta.original_path).name
            if quarantine_path.exists():
                quarantine_path.unlink()

        # Clear metadata
        self._save_metadata({})

        return count, f"Cleared {count} quarantined polips"
