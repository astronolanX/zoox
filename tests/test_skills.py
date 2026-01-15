"""
Tests for reef skill infrastructure.

Phase 5 implementation complete:
- test_skill_discovery
- test_local_override
- test_skill_injection
- test_agent_skill_routing
- test_hotloading
"""

import pytest
from pathlib import Path
import tempfile
import json
import time

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

    def test_skill_info_staleness(self):
        """Verify SkillInfo staleness check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "test.md"
            skill_path.write_text("# Test")

            mtime = skill_path.stat().st_mtime

            info = SkillInfo(
                name="test",
                path=skill_path,
                source="local",
                agents=[],
                task_types=[],
                mtime=mtime,
            )

            # Not stale initially
            assert not info.is_stale()

            # Modify file
            time.sleep(0.01)
            skill_path.write_text("# Modified")

            # Now stale
            assert info.is_stale()


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

    def test_get_for_task(self):
        """Test getting skills by task type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skill with task type
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)

            index = {
                "version": 1,
                "skills": {
                    "search-skill": {
                        "path": "search-skill.md",
                        "task_types": ["search"],
                        "agents": [],
                    }
                },
            }
            (skill_dir / "index.json").write_text(json.dumps(index))
            (skill_dir / "search-skill.md").write_text("# Search Skill")

            registry = SkillRegistry(Path(tmpdir))
            skills = registry.get_for_task("search")

            assert "search-skill" in skills

    def test_get_for_agent(self):
        """Test getting skills by agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skill with agent
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)

            index = {
                "version": 1,
                "skills": {
                    "validator-skill": {
                        "path": "validator-skill.md",
                        "task_types": [],
                        "agents": ["reef-validator"],
                    }
                },
            }
            (skill_dir / "index.json").write_text(json.dumps(index))
            (skill_dir / "validator-skill.md").write_text("# Validator Skill")

            registry = SkillRegistry(Path(tmpdir))
            skills = registry.get_for_agent("reef-validator")

            assert "validator-skill" in skills

    def test_summary(self):
        """Test registry summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "test-skill.md").write_text("# Test")

            registry = SkillRegistry(Path(tmpdir))
            summary = registry.summary()

            assert "total" in summary
            assert "local" in summary
            assert "global" in summary


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

    def test_discover_without_index(self):
        """Test discovering skills without index.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)

            # Create skill file without index
            (skill_dir / "orphan-skill.md").write_text("# Orphan Skill")

            loader = SkillLoader(Path(tmpdir))
            skills = loader.discover()

            assert any(s.name == "orphan-skill" for s in skills)

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

    def test_list_skills(self):
        """Test listing all skill names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "skill-a.md").write_text("# A")
            (skill_dir / "skill-b.md").write_text("# B")

            loader = SkillLoader(Path(tmpdir))
            names = loader.list_skills()

            assert "skill-a" in names
            assert "skill-b" in names


class TestSkillHotloading:
    """Tests for skill hotloading functionality."""

    def test_load_with_tracking(self):
        """Test loading skill with modification tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)
            (skill_dir / "tracked-skill.md").write_text("# Tracked")

            loader = SkillLoader(Path(tmpdir))
            content = loader.load_with_tracking("tracked-skill")

            assert content == "# Tracked"
            assert "tracked-skill" in loader._skill_info_cache

    def test_check_for_changes(self):
        """Test detecting modified skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)
            skill_path = skill_dir / "changing-skill.md"
            skill_path.write_text("# Original")

            loader = SkillLoader(Path(tmpdir))
            loader.load_with_tracking("changing-skill")

            # No changes initially
            assert loader.check_for_changes() == []

            # Modify file
            time.sleep(0.01)
            skill_path.write_text("# Modified")

            # Now changed
            changed = loader.check_for_changes()
            assert "changing-skill" in changed

    def test_reload_changed(self):
        """Test reloading modified skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)
            skill_path = skill_dir / "reload-skill.md"
            skill_path.write_text("# Original")

            loader = SkillLoader(Path(tmpdir))
            content = loader.load_with_tracking("reload-skill")
            assert content == "# Original"

            # Modify file
            time.sleep(0.01)
            skill_path.write_text("# Modified")

            # Reload
            reloaded = loader.reload_changed()
            assert "reload-skill" in reloaded

            # Check new content
            new_content = loader.load("reload-skill")
            assert new_content == "# Modified"

    def test_watch_callback(self):
        """Test watcher callback on reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / ".claude" / "skills"
            skill_dir.mkdir(parents=True)
            skill_path = skill_dir / "watched-skill.md"
            skill_path.write_text("# Original")

            loader = SkillLoader(Path(tmpdir))

            # Track callback calls
            callback_calls = []

            def on_change(name):
                callback_calls.append(name)

            loader.watch(on_change)
            loader.load_with_tracking("watched-skill")

            # Modify and reload
            time.sleep(0.01)
            skill_path.write_text("# Modified")
            loader.reload_changed()

            assert "watched-skill" in callback_calls


class TestSkillCreation:
    """Tests for skill creation."""

    def test_create_skill(self):
        """Test creating a new skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = SkillLoader(Path(tmpdir))

            path = loader.create_skill(
                name="new-skill",
                content="# New Skill Content",
                agents=["test-agent"],
                task_types=["test"],
            )

            assert path.exists()
            assert path.read_text() == "# New Skill Content"

            # Check index was updated
            index_path = Path(tmpdir) / ".claude" / "skills" / "index.json"
            assert index_path.exists()

            with open(index_path) as f:
                index = json.load(f)

            assert "new-skill" in index["skills"]
            assert index["skills"]["new-skill"]["agents"] == ["test-agent"]


class TestSkillIntegration:
    """Integration tests for skill infrastructure."""

    def test_local_override(self):
        """Full test of local skill overriding global."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create global skill
            global_dir = Path(tmpdir) / "global_home" / ".claude" / "skills"
            global_dir.mkdir(parents=True)
            (global_dir / "shared-skill.md").write_text("# Global Version")

            # Create local skill with same name
            local_dir = Path(tmpdir) / "project" / ".claude" / "skills"
            local_dir.mkdir(parents=True)
            (local_dir / "shared-skill.md").write_text("# Local Override")

            # Custom loader with modified search paths
            loader = SkillLoader(Path(tmpdir) / "project")

            # Monkey-patch search paths for test
            # Save the property descriptor, not the evaluated value
            original_property = SkillLoader.__dict__["search_paths"]

            @property
            def test_paths(self):
                return [
                    (Path(tmpdir) / "project" / ".claude/skills", "local"),
                    (global_dir, "global"),
                ]

            SkillLoader.search_paths = test_paths

            try:
                content = loader.load("shared-skill")
                # Local should take priority
                assert content == "# Local Override"
            finally:
                # Restore original property descriptor
                SkillLoader.search_paths = original_property

    def test_agent_skill_routing(self):
        """Full test of agent-to-skill routing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            skill_dir = project_dir / ".claude" / "skills"
            skill_dir.mkdir(parents=True)

            # Create skills for different agents
            index = {
                "version": 1,
                "skills": {
                    "orchestrator-ops": {
                        "path": "orchestrator-ops.md",
                        "agents": ["reef-orchestrator"],
                        "task_types": [],
                    },
                    "validator-rules": {
                        "path": "validator-rules.md",
                        "agents": ["reef-validator"],
                        "task_types": ["validate"],
                    },
                    "shared-skill": {
                        "path": "shared-skill.md",
                        "agents": ["reef-orchestrator", "reef-validator"],
                        "task_types": [],
                    },
                },
            }
            (skill_dir / "index.json").write_text(json.dumps(index))
            (skill_dir / "orchestrator-ops.md").write_text("# Orchestrator")
            (skill_dir / "validator-rules.md").write_text("# Validator")
            (skill_dir / "shared-skill.md").write_text("# Shared")

            # Force refresh to pick up new skills
            registry = SkillRegistry(project_dir)
            registry.refresh()

            # Test agent routing
            orch_skills = registry.get_for_agent("reef-orchestrator")
            val_skills = registry.get_for_agent("reef-validator")

            assert "orchestrator-ops" in orch_skills
            assert "orchestrator-ops" not in val_skills

            assert "validator-rules" in val_skills
            assert "validator-rules" not in orch_skills

            # Shared skill in both
            assert "shared-skill" in orch_skills
            assert "shared-skill" in val_skills

            # Test task type routing
            validate_skills = registry.get_for_task("validate")
            assert "validator-rules" in validate_skills

    def test_full_hotload_cycle(self):
        """Test complete hotload cycle with registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            skill_dir = project_dir / ".claude" / "skills"
            skill_dir.mkdir(parents=True)

            # Create initial skill
            skill_path = skill_dir / "dynamic-skill.md"
            skill_path.write_text("# Version 1")

            registry = SkillRegistry(project_dir)
            registry.refresh()

            # Initial load
            content = registry.load("dynamic-skill")
            assert content == "# Version 1"

            # Modify skill
            time.sleep(0.01)
            skill_path.write_text("# Version 2")

            # Refresh registry
            registry.refresh()

            # Check updated content
            new_content = registry.load("dynamic-skill")
            assert new_content == "# Version 2"
