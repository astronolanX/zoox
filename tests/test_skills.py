"""
Tests for reef skill infrastructure.

Phase 5 will implement:
- test_skill_discovery
- test_local_override
- test_skill_injection
- test_agent_skill_routing
"""

import pytest
from pathlib import Path
import tempfile
import json

from reef.skills import SkillLoader, SkillInfo, SkillRegistry


class TestSkillLoader:
    """Tests for skill loader."""

    def test_import(self):
        """Verify module imports correctly."""
        assert SkillLoader is not None
        assert SkillInfo is not None

    def test_instantiation(self):
        """Verify can create loader instance."""
        loader = SkillLoader()
        assert loader is not None

    def test_search_paths(self):
        """Verify search paths are defined."""
        loader = SkillLoader()
        paths = loader.search_paths
        assert len(paths) == 2
        # First should be local, second global
        assert paths[0][1] == "local"
        assert paths[1][1] == "global"

    def test_skill_info_dataclass(self):
        """Verify SkillInfo dataclass works."""
        info = SkillInfo(
            name="test",
            path=Path("/test/skill.md"),
            source="local",
            agents=["test-agent"],
            task_types=["test"],
        )
        assert info.name == "test"
        assert info.source == "local"

    def test_skill_info_serialization(self):
        """Verify SkillInfo can serialize."""
        info = SkillInfo(
            name="test",
            path=Path("/test/skill.md"),
            source="local",
            agents=["test-agent"],
            task_types=["test"],
        )
        data = info.to_dict()
        assert data["name"] == "test"
        assert data["source"] == "local"


class TestSkillRegistry:
    """Tests for skill registry."""

    def test_import(self):
        """Verify module imports correctly."""
        assert SkillRegistry is not None

    def test_instantiation(self):
        """Verify can create registry instance."""
        registry = SkillRegistry()
        assert registry is not None

    def test_empty_registry(self):
        """Verify empty registry returns empty lists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = SkillRegistry(Path(tmpdir))
            assert registry.get_for_task("unknown") == []
            assert registry.get_for_agent("unknown") == []


class TestSkillDiscovery:
    """Tests for skill discovery with mock skills."""

    def test_discover_from_index(self):
        """Test discovering skills from index.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock skill structure
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)

            # Create index.json
            index = {
                "version": 1,
                "skills": {
                    "test-skill": {
                        "path": "test-skill.md",
                        "agents": ["test-agent"],
                        "task_types": ["test"],
                    }
                },
            }
            (skill_dir / "index.json").write_text(json.dumps(index))

            # Create skill file
            (skill_dir / "test-skill.md").write_text("# Test Skill")

            # Test discovery
            loader = SkillLoader(Path(tmpdir))
            skills = loader.discover()
            assert len(skills) >= 1
            assert any(s.name == "test-skill" for s in skills)

    def test_load_skill_content(self):
        """Test loading skill content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "test-skill.md").write_text("# Test Content")

            loader = SkillLoader(Path(tmpdir))
            content = loader.load("test-skill")
            assert content == "# Test Content"

    def test_inject_with_context(self):
        """Test skill injection with context variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "test-skill.md").write_text("Hello {name}!")

            loader = SkillLoader(Path(tmpdir))
            content = loader.inject("test-skill", {"name": "World"})
            assert content == "Hello World!"


# Phase 5 TODO tests

class TestSkillIntegration:
    """Integration tests for skill infrastructure."""

    @pytest.mark.skip(reason="Requires Phase 5 implementation")
    def test_local_override(self):
        """Full test of local skill overriding global."""
        pass

    @pytest.mark.skip(reason="Requires Phase 5 implementation")
    def test_agent_skill_routing(self):
        """Full test of agent-to-skill routing."""
        pass
