"""
Comprehensive test suite for Glob class.
Tests cover: blob management, relevance scoring, migration, and edge cases.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from zoox.blob import Blob, BlobType, BlobScope, BlobStatus, Glob, BLOB_VERSION


class TestGlobBasics:
    """Basic Glob initialization and blob management."""

    def test_init_creates_claude_dir(self):
        """Glob init creates .claude directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)
            assert (project / ".claude").exists()
            assert (project / ".claude").is_dir()

    def test_init_existing_claude_dir(self):
        """Glob works with existing .claude directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / ".claude").mkdir()
            (project / ".claude" / "existing.txt").write_text("test")
            glob = Glob(project)
            assert (project / ".claude" / "existing.txt").exists()

    def test_sprout_creates_blob(self):
        """Sprout creates blob file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="Test fact")
            path = glob.sprout(blob, "test-fact")

            assert path.exists()
            assert path.name == "test-fact.blob.xml"

    def test_sprout_in_subdir(self):
        """Sprout creates blob in subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.THREAD, summary="Test thread")
            path = glob.sprout(blob, "my-thread", subdir="threads")

            assert path.exists()
            assert path.parent.name == "threads"

    def test_sprout_creates_subdirs(self):
        """Sprout creates missing subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.DECISION, summary="Deep nested")
            path = glob.sprout(blob, "test", subdir="deep/nested/dir")

            assert path.exists()

    def test_get_existing_blob(self):
        """Get retrieves existing blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="Retrievable")
            glob.sprout(blob, "my-fact")

            retrieved = glob.get("my-fact")
            assert retrieved is not None
            assert retrieved.summary == "Retrievable"

    def test_get_with_subdir(self):
        """Get retrieves from subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.THREAD, summary="In subdir")
            glob.sprout(blob, "nested", subdir="threads")

            retrieved = glob.get("nested", subdir="threads")
            assert retrieved is not None
            assert retrieved.summary == "In subdir"

    def test_get_nonexistent_returns_none(self):
        """Get returns None for missing blob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            result = glob.get("does-not-exist")
            assert result is None


class TestGlobListBlobs:
    """Blob listing functionality."""

    def test_list_empty(self):
        """List returns empty for empty glob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blobs = glob.list_blobs()
            assert blobs == []

    def test_list_root_blobs(self):
        """List returns root-level blobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob1 = Blob(type=BlobType.FACT, summary="Fact 1")
            blob2 = Blob(type=BlobType.CONTEXT, summary="Context 1")
            glob.sprout(blob1, "fact1")
            glob.sprout(blob2, "context1")

            blobs = glob.list_blobs()
            assert len(blobs) == 2
            names = [name for name, _ in blobs]
            assert "fact1" in names
            assert "context1" in names

    def test_list_subdir_blobs(self):
        """List returns blobs in subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.THREAD, summary="Thread 1")
            glob.sprout(blob, "thread1", subdir="threads")

            # Root should be empty
            root_blobs = glob.list_blobs()
            assert len(root_blobs) == 0

            # Subdir should have the blob
            thread_blobs = glob.list_blobs(subdir="threads")
            assert len(thread_blobs) == 1
            assert thread_blobs[0][0] == "thread1"

    def test_list_nonexistent_subdir(self):
        """List returns empty for nonexistent subdir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blobs = glob.list_blobs(subdir="nonexistent")
            assert blobs == []

    def test_list_ignores_malformed_files(self):
        """List skips files that can't be parsed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            # Create a valid blob
            blob = Blob(type=BlobType.FACT, summary="Valid")
            glob.sprout(blob, "valid")

            # Create a malformed file
            (project / ".claude" / "malformed.blob.xml").write_text("not xml")

            blobs = glob.list_blobs()
            assert len(blobs) == 1
            assert blobs[0][0] == "valid"


class TestGlobDecompose:
    """Blob archival (decompose) tests."""

    def test_decompose_moves_to_archive(self):
        """Decompose moves blob to archive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.CONTEXT, summary="Archive me")
            glob.sprout(blob, "to-archive")

            glob.decompose("to-archive")

            # Original should be gone
            assert not (project / ".claude" / "to-archive.blob.xml").exists()

            # Archive should exist
            archive_files = list((project / ".claude" / "archive").glob("*.blob.xml"))
            assert len(archive_files) == 1
            assert "to-archive" in archive_files[0].name

    def test_decompose_sets_archived_status(self):
        """Decompose sets status to ARCHIVED."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.THREAD, summary="Archive me", status=BlobStatus.ACTIVE)
            glob.sprout(blob, "to-archive", subdir="threads")

            glob.decompose("to-archive", subdir="threads")

            # Load from archive
            archive_files = list((project / ".claude" / "archive").glob("*.blob.xml"))
            archived = Blob.load(archive_files[0])
            assert archived.status == BlobStatus.ARCHIVED

    def test_decompose_nonexistent_no_error(self):
        """Decompose on nonexistent blob does nothing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            # Should not raise
            glob.decompose("nonexistent")

    def test_decompose_from_subdir(self):
        """Decompose works from subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.DECISION, summary="Archived decision")
            glob.sprout(blob, "old-decision", subdir="decisions")

            glob.decompose("old-decision", subdir="decisions")

            assert not (project / ".claude" / "decisions" / "old-decision.blob.xml").exists()


class TestGlobSurfaceRelevant:
    """Relevance scoring and surfacing."""

    def test_surface_empty_glob(self):
        """Surface returns empty for empty glob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            relevant = glob.surface_relevant()
            assert relevant == []

    def test_surface_always_scope_first(self):
        """ALWAYS scope blobs score highest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            project_blob = Blob(type=BlobType.FACT, summary="Project scope", scope=BlobScope.PROJECT)
            always_blob = Blob(type=BlobType.CONSTRAINT, summary="Always scope", scope=BlobScope.ALWAYS)

            glob.sprout(project_blob, "project-blob")
            glob.sprout(always_blob, "always-blob")

            relevant = glob.surface_relevant()
            # Always-scope should be first (score +10)
            assert len(relevant) == 1  # Project blob has score 0, not included
            assert relevant[0].scope == BlobScope.ALWAYS

    def test_surface_active_threads(self):
        """Active/blocked threads get surfaced."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            active = Blob(type=BlobType.THREAD, summary="Active", status=BlobStatus.ACTIVE)
            blocked = Blob(type=BlobType.THREAD, summary="Blocked", status=BlobStatus.BLOCKED)
            done = Blob(type=BlobType.THREAD, summary="Done", status=BlobStatus.DONE)

            glob.sprout(active, "active", subdir="threads")
            glob.sprout(blocked, "blocked", subdir="threads")
            glob.sprout(done, "done", subdir="threads")

            relevant = glob.surface_relevant()
            # Active and blocked should surface, done should not
            assert len(relevant) == 2
            summaries = [b.summary for b in relevant]
            assert "Active" in summaries
            assert "Blocked" in summaries
            assert "Done" not in summaries

    def test_surface_file_overlap(self):
        """File overlap increases score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob_a = Blob(type=BlobType.THREAD, summary="A", files=["foo.py"])
            blob_b = Blob(type=BlobType.THREAD, summary="B", files=["bar.py", "foo.py"])
            blob_c = Blob(type=BlobType.THREAD, summary="C", files=["other.py"])

            glob.sprout(blob_a, "a", subdir="threads")
            glob.sprout(blob_b, "b", subdir="threads")
            glob.sprout(blob_c, "c", subdir="threads")

            relevant = glob.surface_relevant(files=["foo.py"])
            assert len(relevant) == 2  # A and B match, C doesn't
            # B has more overlap potentially

    def test_surface_query_match(self):
        """Query matches summary and context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob1 = Blob(type=BlobType.FACT, summary="Authentication system")
            blob2 = Blob(type=BlobType.FACT, summary="Other", context="Related to auth")
            blob3 = Blob(type=BlobType.FACT, summary="Unrelated")

            glob.sprout(blob1, "b1")
            glob.sprout(blob2, "b2")
            glob.sprout(blob3, "b3")

            relevant = glob.surface_relevant(query="auth")
            summaries = [b.summary for b in relevant]
            assert "Authentication system" in summaries
            assert "Other" in summaries
            assert "Unrelated" not in summaries

    def test_surface_case_insensitive_query(self):
        """Query matching is case insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="DATABASE Configuration")
            glob.sprout(blob, "db")

            relevant = glob.surface_relevant(query="database")
            assert len(relevant) == 1

    def test_surface_combines_signals(self):
        """Multiple signals combine for higher scores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            # High score: always scope + active status + file match + query match
            super_blob = Blob(
                type=BlobType.THREAD,
                summary="Super important auth thread",
                scope=BlobScope.ALWAYS,
                status=BlobStatus.ACTIVE,
                files=["auth.py"],
            )

            # Low score: just file match
            low_blob = Blob(type=BlobType.THREAD, summary="Other", files=["auth.py"])

            glob.sprout(super_blob, "super", subdir="threads")
            glob.sprout(low_blob, "low", subdir="threads")

            relevant = glob.surface_relevant(files=["auth.py"], query="auth")
            # Super blob should be first
            assert relevant[0].summary == "Super important auth thread"


class TestGlobMigrations:
    """Schema migration tests."""

    def test_check_migrations_empty(self):
        """Check migrations on empty glob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            outdated = glob.check_migrations()
            assert outdated == []

    def test_check_migrations_finds_old(self):
        """Check migrations finds old blobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            old_blob = Blob(type=BlobType.FACT, summary="Old", version=1)
            glob.sprout(old_blob, "old")

            outdated = glob.check_migrations()
            assert len(outdated) == 1

    def test_migrate_all(self):
        """Migrate all updates blobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            for i in range(5):
                old_blob = Blob(type=BlobType.FACT, summary=f"Old {i}", version=1)
                glob.sprout(old_blob, f"old-{i}")

            count = glob.migrate_all()
            assert count == 5

            # All should now be current
            outdated = glob.check_migrations()
            assert len(outdated) == 0

    def test_migrate_preserves_content(self):
        """Migration preserves blob content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(
                type=BlobType.THREAD,
                summary="Important thread",
                version=1,
                files=["a.py", "b.py"],
                decisions=[("choice", "reason")],
                context="Context here",
            )
            glob.sprout(blob, "important", subdir="threads")

            glob.migrate_all()

            loaded = glob.get("important", subdir="threads")
            assert loaded.summary == "Important thread"
            assert loaded.files == ["a.py", "b.py"]
            assert loaded.decisions == [("choice", "reason")]
            assert loaded.version == BLOB_VERSION


class TestGlobInjectContext:
    """Context injection tests."""

    def test_inject_empty(self):
        """Inject returns empty for empty glob."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            xml = glob.inject_context()
            assert xml == ""

    def test_inject_creates_valid_xml(self):
        """Inject creates valid XML document."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.CONSTRAINT, summary="Constraint", scope=BlobScope.ALWAYS)
            glob.sprout(blob, "rule", subdir="constraints")

            xml = glob.inject_context()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)
            assert root.tag == "glob"

    def test_inject_limits_to_ten(self):
        """Inject limits to 10 blobs max."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            # Create 15 always-scope blobs
            for i in range(15):
                blob = Blob(type=BlobType.CONSTRAINT, summary=f"Rule {i}", scope=BlobScope.ALWAYS)
                glob.sprout(blob, f"rule-{i}", subdir="constraints")

            xml = glob.inject_context()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)
            blob_elements = root.findall("blob")
            assert len(blob_elements) == 10

    def test_inject_includes_project_name(self):
        """Inject includes project name attribute."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "my-project"
            project.mkdir()
            glob = Glob(project)

            blob = Blob(type=BlobType.CONSTRAINT, summary="Test", scope=BlobScope.ALWAYS)
            glob.sprout(blob, "test", subdir="constraints")

            xml = glob.inject_context()
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)
            assert root.get("project") == "my-project"


class TestGlobEdgeCases:
    """Edge cases and boundary conditions."""

    def test_special_chars_in_blob_name(self):
        """Special characters in blob name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="Test")
            # Note: actual filesystem may restrict some chars
            path = glob.sprout(blob, "test-blob_v2.0")
            assert path.exists()

            retrieved = glob.get("test-blob_v2.0")
            assert retrieved is not None

    def test_blob_in_root_and_subdir_same_name(self):
        """Same name in root and subdir are different."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            root_blob = Blob(type=BlobType.FACT, summary="Root blob")
            sub_blob = Blob(type=BlobType.FACT, summary="Subdir blob")

            glob.sprout(root_blob, "samename")
            glob.sprout(sub_blob, "samename", subdir="facts")

            root_retrieved = glob.get("samename")
            sub_retrieved = glob.get("samename", subdir="facts")

            assert root_retrieved.summary == "Root blob"
            assert sub_retrieved.summary == "Subdir blob"

    def test_concurrent_writes(self):
        """Multiple writes to same path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            for i in range(100):
                blob = Blob(type=BlobType.FACT, summary=f"Version {i}")
                glob.sprout(blob, "contested")

            final = glob.get("contested")
            assert final.summary == "Version 99"

    def test_very_long_blob_name(self):
        """Very long blob filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            long_name = "a" * 200
            blob = Blob(type=BlobType.FACT, summary="Long name test")
            path = glob.sprout(blob, long_name)
            assert path.exists()

    def test_unicode_in_paths(self):
        """Unicode in directory and blob names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="Unicode paths")
            path = glob.sprout(blob, "日本語-blob", subdir="ユニコード")
            assert path.exists()

            retrieved = glob.get("日本語-blob", subdir="ユニコード")
            assert retrieved is not None


class TestGlobStress:
    """Stress tests."""

    def test_many_blobs(self):
        """Create and list many blobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            for i in range(500):
                blob = Blob(type=BlobType.FACT, summary=f"Blob {i}")
                glob.sprout(blob, f"blob-{i}")

            blobs = glob.list_blobs()
            assert len(blobs) == 500

    def test_surface_with_many_blobs(self):
        """Surface relevance with many blobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            for i in range(100):
                blob = Blob(
                    type=BlobType.THREAD,
                    summary=f"Thread {i}",
                    status=BlobStatus.ACTIVE if i % 3 == 0 else BlobStatus.DONE,
                    files=[f"file_{i}.py"],
                )
                glob.sprout(blob, f"thread-{i}", subdir="threads")

            relevant = glob.surface_relevant(files=["file_15.py"])
            # Should find at least the one with matching file
            assert len(relevant) > 0

    def test_deep_subdir_hierarchy(self):
        """Very deep subdirectory hierarchy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            deep_subdir = "/".join(["level"] * 20)
            blob = Blob(type=BlobType.FACT, summary="Deep")
            path = glob.sprout(blob, "deep-blob", subdir=deep_subdir)
            assert path.exists()

    def test_rapid_create_delete(self):
        """Rapid creation and deletion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            for i in range(50):
                blob = Blob(type=BlobType.CONTEXT, summary=f"Temp {i}", scope=BlobScope.SESSION)
                glob.sprout(blob, f"temp-{i}")
                glob.decompose(f"temp-{i}")

            # Should have 50 archived blobs
            archive = list((project / ".claude" / "archive").glob("*.blob.xml"))
            assert len(archive) == 50
