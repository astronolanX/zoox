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


class TestGlobCache:
    """Cache functionality tests."""

    def test_cache_hit_on_repeated_get(self):
        """Repeated get() calls hit cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="Cache me")
            glob.sprout(blob, "cached")

            # First call - cache miss
            result1 = glob.get("cached")
            stats1 = glob.cache_stats()
            assert stats1["misses"] == 1
            assert stats1["hits"] == 0

            # Second call - cache hit
            result2 = glob.get("cached")
            stats2 = glob.cache_stats()
            assert stats2["hits"] == 1
            assert stats2["misses"] == 1

            assert result1.summary == result2.summary

    def test_cache_invalidated_on_file_change(self):
        """Cache invalidates when file mtime changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="Original")
            path = glob.sprout(blob, "changing")

            # Load into cache
            result1 = glob.get("changing")
            assert result1.summary == "Original"

            # Modify file directly (simulating external change)
            import time
            time.sleep(0.01)  # Ensure mtime differs
            modified = Blob(type=BlobType.FACT, summary="Modified")
            modified.save(path)

            # Should reload due to mtime change
            result2 = glob.get("changing")
            assert result2.summary == "Modified"

    def test_cache_invalidated_on_sprout(self):
        """Sprout invalidates cache for that path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob1 = Blob(type=BlobType.FACT, summary="V1")
            glob.sprout(blob1, "versioned")

            # Load into cache
            glob.get("versioned")

            # Sprout again (overwrite)
            blob2 = Blob(type=BlobType.FACT, summary="V2")
            glob.sprout(blob2, "versioned")

            # Should get new version
            result = glob.get("versioned")
            assert result.summary == "V2"

    def test_cache_stats(self):
        """Cache stats are accurate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            # Create blobs
            for i in range(5):
                blob = Blob(type=BlobType.FACT, summary=f"Blob {i}")
                glob.sprout(blob, f"blob-{i}")

            # First list - all misses
            glob.list_blobs()
            stats1 = glob.cache_stats()
            assert stats1["misses"] == 5
            assert stats1["cached_blobs"] == 5

            # Second list - all hits
            glob.list_blobs()
            stats2 = glob.cache_stats()
            assert stats2["hits"] == 5
            assert stats2["hit_rate"] == 50.0  # 5 hits / 10 total

    def test_cache_handles_deleted_files(self):
        """Cache handles externally deleted files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="Will be deleted")
            path = glob.sprout(blob, "doomed")

            # Load into cache
            assert glob.get("doomed") is not None

            # Delete externally
            path.unlink()

            # Should return None, not stale cache
            assert glob.get("doomed") is None


class TestGlobIndex:
    """Index functionality tests."""

    def test_index_created_on_sprout(self):
        """Sprout creates/updates index entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="Index me")
            glob.sprout(blob, "indexed")

            index = glob.get_index()
            assert "indexed.blob.xml" in index["blobs"]
            assert index["blobs"]["indexed.blob.xml"]["type"] == "fact"

    def test_index_removed_on_decompose(self):
        """Decompose removes from index and adds archive entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.CONTEXT, summary="Archive me", scope=BlobScope.SESSION)
            glob.sprout(blob, "to-archive")

            # Verify in index
            index1 = glob.get_index()
            assert "to-archive.blob.xml" in index1["blobs"]

            # Decompose
            glob.decompose("to-archive")

            # Verify removed from index, archive added
            index2 = glob.get_index()
            assert "to-archive.blob.xml" not in index2["blobs"]
            # Archive entry should exist
            archive_keys = [k for k in index2["blobs"] if k.startswith("archive/")]
            assert len(archive_keys) == 1

    def test_index_rebuild(self):
        """Rebuild recreates index from scratch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            # Create some blobs
            for i in range(5):
                blob = Blob(type=BlobType.FACT, summary=f"Blob {i}")
                glob.sprout(blob, f"blob-{i}")

            # Delete index manually
            index_path = project / ".claude" / "index.json"
            index_path.unlink()

            # Rebuild
            count = glob.rebuild_index()
            assert count == 5

            # Verify all blobs in index
            index = glob.get_index()
            assert len(index["blobs"]) == 5

    def test_index_handles_subdir_blobs(self):
        """Index handles blobs in subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.THREAD, summary="Thread blob", status=BlobStatus.ACTIVE)
            glob.sprout(blob, "my-thread", subdir="threads")

            index = glob.get_index()
            assert "threads/my-thread.blob.xml" in index["blobs"]
            assert index["blobs"]["threads/my-thread.blob.xml"]["status"] == "active"


# ============================================================================
# P7 Feature Tests
# ============================================================================


class TestTFIDFSearch:
    """Test TF-IDF fuzzy search implementation."""

    def test_tfidf_basic_matching(self):
        """TF-IDF scores documents containing query terms higher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            # Create blobs with different content
            blob1 = Blob(type=BlobType.FACT, summary="Authentication system design",
                        scope=BlobScope.PROJECT)
            blob2 = Blob(type=BlobType.FACT, summary="Database schema for users",
                        scope=BlobScope.PROJECT)
            blob3 = Blob(type=BlobType.FACT, summary="Auth login OAuth JWT tokens",
                        scope=BlobScope.PROJECT)

            glob.sprout(blob1, "auth-design")
            glob.sprout(blob2, "db-schema")
            glob.sprout(blob3, "auth-tokens")

            # Search for "auth" - should return auth-related blobs
            results = glob.search_index(query="auth")
            assert len(results) >= 2
            # Auth-specific blobs should score higher
            keys = [r[0] for r in results]
            assert "auth-design.blob.xml" in keys or "auth-tokens.blob.xml" in keys

    def test_tfidf_ranks_relevant_higher(self):
        """TF-IDF ranks more relevant documents higher."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            # Create blob with many occurrences of "api"
            blob1 = Blob(type=BlobType.FACT, summary="API design API endpoints API versioning",
                        scope=BlobScope.PROJECT)
            # Create blob with single occurrence
            blob2 = Blob(type=BlobType.FACT, summary="Backend API integration",
                        scope=BlobScope.PROJECT)

            glob.sprout(blob1, "api-heavy")
            glob.sprout(blob2, "api-light")

            results = glob.search_index(query="api")
            assert len(results) == 2
            # Higher TF should score higher
            assert results[0][2] >= results[1][2]

    def test_surface_relevant_with_tfidf(self):
        """surface_relevant uses TF-IDF for query matching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob1 = Blob(type=BlobType.CONSTRAINT, summary="Use TypeScript for all frontend",
                        scope=BlobScope.ALWAYS)
            blob2 = Blob(type=BlobType.FACT, summary="JavaScript legacy code",
                        scope=BlobScope.PROJECT)

            glob.sprout(blob1, "typescript-rule", subdir="constraints")
            glob.sprout(blob2, "js-legacy")

            # Query for "frontend" should surface the TypeScript constraint
            results = glob.surface_relevant(query="frontend", track_access=False)
            summaries = [b.summary for b in results]
            assert "Use TypeScript for all frontend" in summaries


class TestWikiLinking:
    """Test [[wiki-style]] linking functionality."""

    def test_extract_wiki_links_basic(self):
        """Extract wiki links from content."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Working on [[auth-system]] feature",
            context="This relates to [[user-management]] and [[permissions]]"
        )

        links = blob.extract_wiki_links()
        assert "auth-system" in links
        assert "user-management" in links
        assert "permissions" in links

    def test_extract_wiki_links_empty(self):
        """No wiki links returns empty list."""
        blob = Blob(type=BlobType.FACT, summary="No links here")
        links = blob.extract_wiki_links()
        assert links == []

    def test_update_related_from_links(self):
        """Wiki links auto-populate related field."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Working on [[auth-system]]",
            context="See [[design-doc]] for details"
        )

        blob.update_related_from_links()
        assert "auth-system" in blob.related
        assert "design-doc" in blob.related

    def test_update_related_preserves_existing(self):
        """Wiki link update preserves existing manual references."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Working on [[new-feature]]",
            related=["existing-ref", "manual-link"]
        )

        blob.update_related_from_links()
        assert "new-feature" in blob.related
        assert "existing-ref" in blob.related
        assert "manual-link" in blob.related

    def test_to_xml_auto_populates_related(self):
        """to_xml automatically extracts wiki links to related."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Implements [[feature-x]]",
            status=BlobStatus.ACTIVE
        )

        # Serialize - this should auto-populate related
        xml = blob.to_xml()
        assert "feature-x" in blob.related
        assert "<ref>feature-x</ref>" in xml

    def test_wiki_links_deduplicate(self):
        """Duplicate wiki links only appear once in related."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Working on [[same-thing]]",
            context="More about [[same-thing]] here"
        )

        blob.update_related_from_links()
        assert blob.related.count("same-thing") == 1


class TestLRUAccessTracking:
    """Test LRU-style access count tracking."""

    def test_access_count_in_index(self):
        """New blobs have access_count of 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="Test fact")
            glob.sprout(blob, "test-fact")

            index = glob.get_index()
            assert index["blobs"]["test-fact.blob.xml"]["access_count"] == 0

    def test_surface_increments_access(self):
        """surface_relevant increments access count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.CONSTRAINT, summary="Always surface me",
                       scope=BlobScope.ALWAYS)
            glob.sprout(blob, "always-surface", subdir="constraints")

            # Surface should increment count
            glob.surface_relevant(track_access=True)

            index = glob.get_index()
            key = "constraints/always-surface.blob.xml"
            assert index["blobs"][key]["access_count"] >= 1

    def test_access_count_preserved_on_update(self):
        """Access count preserved when blob is updated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="Original")
            path = glob.sprout(blob, "test-fact")

            # Manually set access count
            index = glob._load_index()
            index["blobs"]["test-fact.blob.xml"]["access_count"] = 10
            glob._save_index(index)

            # Update the blob
            blob.summary = "Updated"
            glob._update_index(path, blob)

            # Access count should be preserved
            index = glob.get_index()
            assert index["blobs"]["test-fact.blob.xml"]["access_count"] == 10

    def test_access_count_preserved_on_rebuild(self):
        """Access count preserved when index is rebuilt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.FACT, summary="Test fact")
            glob.sprout(blob, "test-fact")

            # Set access count
            index = glob._load_index()
            index["blobs"]["test-fact.blob.xml"]["access_count"] = 42
            glob._save_index(index)

            # Rebuild index
            glob.rebuild_index()

            # Access count should be preserved
            index = glob.get_index()
            assert index["blobs"]["test-fact.blob.xml"]["access_count"] == 42

    def test_track_access_false_skips_increment(self):
        """track_access=False prevents access count increment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            blob = Blob(type=BlobType.CONSTRAINT, summary="Test",
                       scope=BlobScope.ALWAYS)
            glob.sprout(blob, "test-constraint", subdir="constraints")

            # Surface without tracking
            glob.surface_relevant(track_access=False)
            glob.surface_relevant(track_access=False)

            index = glob.get_index()
            assert index["blobs"]["constraints/test-constraint.blob.xml"]["access_count"] == 0


class TestRichTemplateVariables:
    """Test rich template variable expansion."""

    def test_template_has_date(self):
        """Template variables include current date."""
        from zoox.blob import get_template_variables
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            vars = get_template_variables(project)

            assert "date" in vars
            assert len(vars["date"]) == 10  # YYYY-MM-DD format

    def test_template_has_timestamp(self):
        """Template variables include ISO timestamp."""
        from zoox.blob import get_template_variables

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            vars = get_template_variables(project)

            assert "timestamp" in vars
            assert "T" in vars["timestamp"]  # ISO format has T separator

    def test_template_has_project_name(self):
        """Template variables include project directory name."""
        from zoox.blob import get_template_variables

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            vars = get_template_variables(project)

            assert "project_name" in vars
            assert vars["project_name"] == project.name

    def test_template_git_vars_empty_without_git(self):
        """Git variables are empty strings in non-git directory."""
        from zoox.blob import get_template_variables

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            vars = get_template_variables(project)

            assert vars["git_branch"] == ""
            assert vars["git_sha"] == ""
            assert vars["git_short_sha"] == ""

    def test_create_from_template_uses_variables(self):
        """create_from_template expands rich variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            # Create custom template with date variable
            template = {
                "type": "thread",
                "summary_template": "[{date}] {title}",
                "scope": "project",
                "status": "active"
            }
            glob.save_template("dated", template)

            # Create from template
            path = glob.create_from_template("dated", "Test Task")

            # Load and verify
            blob = Blob.load(path)
            assert blob.summary.startswith("[")
            assert "-" in blob.summary  # Date has dashes
