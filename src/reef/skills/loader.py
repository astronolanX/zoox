"""
Skill loader - discovers and loads skills from multiple locations.

Search order (highest priority first):
1. Project-local: .claude/skills/
2. Global: ~/.claude/skills/

Supports:
- Hot reloading via file modification time tracking
- Variable substitution in skill content
- Multi-location skill discovery with local override
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import json


@dataclass
class SkillInfo:
    """Metadata about a skill."""

    name: str
    path: Path
    source: str  # "local" or "global"
    agents: list[str]
    task_types: list[str]
    description: str | None = None
    mtime: float | None = None  # Last modification time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "path": str(self.path),
            "source": self.source,
            "agents": self.agents,
            "task_types": self.task_types,
            "description": self.description,
            "mtime": self.mtime,
        }

    def is_stale(self) -> bool:
        """Check if skill file has been modified since loading."""
        if self.mtime is None or not self.path.exists():
            return True
        return self.path.stat().st_mtime > self.mtime


class SkillLoader:
    """Discovers and loads skills from multiple locations."""

    def __init__(self, project_dir: Path | None = None):
        """
        Initialize skill loader.

        Args:
            project_dir: Project directory containing .claude/skills/
        """
        self.project_dir = project_dir or Path.cwd()
        self._cache: dict[str, str] = {}
        self._skill_info_cache: dict[str, SkillInfo] = {}
        self._watchers: list[Callable[[str], None]] = []

    @property
    def search_paths(self) -> list[tuple[Path, str]]:
        """Get skill search paths with source labels."""
        return [
            (self.project_dir / ".claude/skills", "local"),
            (Path.home() / ".claude/skills", "global"),
        ]

    def discover(self) -> list[SkillInfo]:
        """
        Find all available skills.

        Returns:
            List of skill info objects
        """
        skills = []
        seen_names: set[str] = set()

        for search_path, source in self.search_paths:
            if not search_path.exists():
                continue

            # Check for index.json
            index_path = search_path / "index.json"
            if index_path.exists():
                skills.extend(self._load_from_index(index_path, source, seen_names))

            # Also scan for .md files not in index
            for skill_file in search_path.glob("*.md"):
                name = skill_file.stem
                if name not in seen_names:
                    skills.append(
                        SkillInfo(
                            name=name,
                            path=skill_file,
                            source=source,
                            agents=[],
                            task_types=[],
                        )
                    )
                    seen_names.add(name)

        return skills

    def _load_from_index(
        self, index_path: Path, source: str, seen_names: set[str]
    ) -> list[SkillInfo]:
        """Load skills from index.json."""
        skills = []

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for name, info in data.get("skills", {}).items():
                if name in seen_names:
                    continue

                skill_path = index_path.parent / info.get("path", f"{name}.md")
                skills.append(
                    SkillInfo(
                        name=name,
                        path=skill_path,
                        source=source,
                        agents=info.get("agents", []),
                        task_types=info.get("task_types", []),
                        description=info.get("description"),
                    )
                )
                seen_names.add(name)

        except (json.JSONDecodeError, KeyError):
            pass

        return skills

    def load(self, skill_name: str) -> str | None:
        """
        Load skill content, project-local overrides global.

        Args:
            skill_name: Name of skill to load

        Returns:
            Skill content or None if not found
        """
        # Check cache
        if skill_name in self._cache:
            return self._cache[skill_name]

        # Search in priority order
        for search_path, _source in self.search_paths:
            skill_path = search_path / f"{skill_name}.md"
            if skill_path.exists():
                content = skill_path.read_text(encoding="utf-8")
                self._cache[skill_name] = content
                return content

        return None

    def inject(self, skill_name: str, context: dict[str, Any]) -> str | None:
        """
        Load and inject skill with context variables.

        Supports {variable} substitution in skill content.

        Args:
            skill_name: Name of skill to load
            context: Context variables for substitution

        Returns:
            Skill content with variables substituted
        """
        content = self.load(skill_name)
        if content is None:
            return None

        # Simple variable substitution
        for key, value in context.items():
            content = content.replace(f"{{{key}}}", str(value))

        return content

    def get_skill_info(self, skill_name: str) -> SkillInfo | None:
        """
        Get info about a specific skill.

        Args:
            skill_name: Name of skill

        Returns:
            Skill info or None if not found
        """
        for skill in self.discover():
            if skill.name == skill_name:
                return skill
        return None

    def clear_cache(self) -> None:
        """Clear skill cache."""
        self._cache.clear()
        self._skill_info_cache.clear()

    def watch(self, callback: Callable[[str], None]) -> None:
        """
        Register callback for skill changes.

        Args:
            callback: Function called with skill name when it changes
        """
        self._watchers.append(callback)

    def check_for_changes(self) -> list[str]:
        """
        Check for modified skills since last load.

        Returns:
            List of skill names that have changed
        """
        changed = []

        for name, info in self._skill_info_cache.items():
            if info.is_stale():
                changed.append(name)

        return changed

    def reload_changed(self) -> list[str]:
        """
        Reload any skills that have changed.

        Returns:
            List of skill names that were reloaded
        """
        changed = self.check_for_changes()

        for name in changed:
            # Clear from caches
            self._cache.pop(name, None)
            self._skill_info_cache.pop(name, None)

            # Reload
            self.load(name)

            # Notify watchers
            for callback in self._watchers:
                try:
                    callback(name)
                except Exception:
                    pass

        return changed

    def load_with_tracking(self, skill_name: str) -> str | None:
        """
        Load skill content with modification tracking.

        Args:
            skill_name: Name of skill to load

        Returns:
            Skill content or None if not found
        """
        content = self.load(skill_name)

        if content is not None:
            # Track skill info for hotloading
            for search_path, source in self.search_paths:
                skill_path = search_path / f"{skill_name}.md"
                if skill_path.exists():
                    self._skill_info_cache[skill_name] = SkillInfo(
                        name=skill_name,
                        path=skill_path,
                        source=source,
                        agents=[],
                        task_types=[],
                        mtime=skill_path.stat().st_mtime,
                    )
                    break

        return content

    def get_skill_path(self, skill_name: str) -> Path | None:
        """
        Get path to skill file.

        Args:
            skill_name: Name of skill

        Returns:
            Path to skill file or None
        """
        for search_path, _source in self.search_paths:
            skill_path = search_path / f"{skill_name}.md"
            if skill_path.exists():
                return skill_path
        return None

    def list_skills(self) -> list[str]:
        """
        List all available skill names.

        Returns:
            List of skill names
        """
        return [s.name for s in self.discover()]

    def create_skill(
        self,
        name: str,
        content: str,
        agents: list[str] | None = None,
        task_types: list[str] | None = None,
        local: bool = True,
    ) -> Path:
        """
        Create a new skill file.

        Args:
            name: Skill name (will become filename)
            content: Skill content
            agents: List of agents this skill applies to
            task_types: List of task types this skill applies to
            local: If True, create in project-local skills

        Returns:
            Path to created skill file
        """
        if local:
            skill_dir = self.project_dir / ".claude/skills"
        else:
            skill_dir = Path.home() / ".claude/skills"

        skill_dir.mkdir(parents=True, exist_ok=True)

        # Write skill file
        skill_path = skill_dir / f"{name}.md"
        skill_path.write_text(content, encoding="utf-8")

        # Update index if it exists
        index_path = skill_dir / "index.json"
        if index_path.exists():
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    index = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                index = {"version": 1, "skills": {}}
        else:
            index = {"version": 1, "skills": {}}

        index["skills"][name] = {
            "path": f"{name}.md",
            "agents": agents or [],
            "task_types": task_types or [],
        }

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

        # Clear cache so new skill is picked up
        self.clear_cache()

        return skill_path
