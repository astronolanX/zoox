"""
Skill registry - central registry for skill metadata.

Provides skill lookup by task type and agent name.
"""

from pathlib import Path
from typing import Any

from .loader import SkillLoader, SkillInfo


class SkillRegistry:
    """Central registry for skill metadata."""

    def __init__(self, project_dir: Path | None = None):
        """
        Initialize registry.

        Args:
            project_dir: Project directory containing .claude/skills/
        """
        self.loader = SkillLoader(project_dir)
        self._skills: dict[str, SkillInfo] = {}
        self._by_task_type: dict[str, list[str]] = {}
        self._by_agent: dict[str, list[str]] = {}
        self._scanned = False

    def _scan(self) -> None:
        """Scan skill directories and build index."""
        if self._scanned:
            return

        skills = self.loader.discover()

        for skill in skills:
            self._skills[skill.name] = skill

            # Index by task type
            for task_type in skill.task_types:
                if task_type not in self._by_task_type:
                    self._by_task_type[task_type] = []
                self._by_task_type[task_type].append(skill.name)

            # Index by agent
            for agent in skill.agents:
                if agent not in self._by_agent:
                    self._by_agent[agent] = []
                self._by_agent[agent].append(skill.name)

        self._scanned = True

    def get_for_task(self, task_type: str) -> list[str]:
        """
        Get relevant skills for task type.

        Args:
            task_type: Type of task

        Returns:
            List of skill names
        """
        self._scan()
        return self._by_task_type.get(task_type, [])

    def get_for_agent(self, agent_name: str) -> list[str]:
        """
        Get skills assigned to agent.

        Args:
            agent_name: Name of agent

        Returns:
            List of skill names
        """
        self._scan()
        return self._by_agent.get(agent_name, [])

    def get_all(self) -> list[SkillInfo]:
        """
        Get all registered skills.

        Returns:
            List of all skill info objects
        """
        self._scan()
        return list(self._skills.values())

    def get(self, skill_name: str) -> SkillInfo | None:
        """
        Get specific skill info.

        Args:
            skill_name: Name of skill

        Returns:
            Skill info or None
        """
        self._scan()
        return self._skills.get(skill_name)

    def load(self, skill_name: str) -> str | None:
        """
        Load skill content.

        Args:
            skill_name: Name of skill

        Returns:
            Skill content or None
        """
        return self.loader.load(skill_name)

    def refresh(self) -> None:
        """Force refresh of skill index."""
        self._skills.clear()
        self._by_task_type.clear()
        self._by_agent.clear()
        self._scanned = False
        self.loader.clear_cache()
        self._scan()

    def summary(self) -> dict[str, Any]:
        """
        Get registry summary.

        Returns:
            Summary with counts
        """
        self._scan()

        local_count = sum(1 for s in self._skills.values() if s.source == "local")
        global_count = sum(1 for s in self._skills.values() if s.source == "global")

        return {
            "total": len(self._skills),
            "local": local_count,
            "global": global_count,
            "task_types": list(self._by_task_type.keys()),
            "agents": list(self._by_agent.keys()),
        }
