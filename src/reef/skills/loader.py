"""
Skill loader - discovers and loads skills from multiple locations.

Search order (highest priority first):
1. Project-local: .claude/skills/
2. Global: ~/.claude/skills/
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "path": str(self.path),
            "source": self.source,
            "agents": self.agents,
            "task_types": self.task_types,
            "description": self.description,
        }


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
