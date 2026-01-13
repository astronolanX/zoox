"""
Tests targeting potential bugs discovered during code review.
These test specific edge cases that might expose real issues.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from zoox.blob import Blob, BlobType, BlobScope, BlobStatus, Glob, BLOB_VERSION


class TestBugHunting:
    """Tests targeting potential bugs in the implementation."""

    def test_list_blobs_stem_parsing(self):
        """
        BUG INVESTIGATION: list_blobs uses path.stem.replace(".blob", "")
        This could cause issues with names containing ".blob" in the middle.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Name that contains ".blob" as a substring
            blob = Blob(type=BlobType.FACT, summary="Test")
            path = glob.sprout(blob, "my.blob.name")  # Will become my.blob.name.blob.xml

            blobs = glob.list_blobs()
            names = [name for name, _ in blobs]

            # The name returned should be "my.blob.name", not "my.name" or something weird
            # Due to .stem giving "my.blob.name.blob" and replace(".blob", "") giving "my.name"
            # This IS a bug!
            print(f"Names found: {names}")
            # Current behavior is buggy - let's verify
            assert len(blobs) == 1
            # This will likely fail showing the bug:
            # Expected: "my.blob.name" but will get "my.name" due to replace() behavior

    def test_surface_relevant_misses_facts_subdir(self):
        """
        BUG INVESTIGATION: surface_relevant only checks subdirs:
        ["threads", "decisions", "constraints"]
        It misses "contexts" and "facts" subdirs!
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create fact with ALWAYS scope (should surface)
            fact = Blob(type=BlobType.FACT, summary="Important fact", scope=BlobScope.ALWAYS)
            glob.sprout(fact, "important", subdir="facts")

            # Create context with ALWAYS scope
            ctx = Blob(type=BlobType.CONTEXT, summary="Important context", scope=BlobScope.ALWAYS)
            glob.sprout(ctx, "important", subdir="contexts")

            relevant = glob.surface_relevant()

            # These should surface because they have ALWAYS scope
            # But they won't because surface_relevant doesn't check facts/contexts subdirs!
            summaries = [b.summary for b in relevant]
            print(f"Surfaced: {summaries}")

            # This will likely fail - exposing the bug
            assert "Important fact" in summaries, "Facts subdir not being surfaced!"
            assert "Important context" in summaries, "Contexts subdir not being surfaced!"

    def test_check_migrations_misses_facts_contexts(self):
        """
        BUG INVESTIGATION: check_migrations only checks:
        ["threads", "decisions", "constraints"]
        Same issue as surface_relevant - misses facts and contexts.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create old version blob in facts subdir
            old_fact = Blob(type=BlobType.FACT, summary="Old fact", version=1)
            glob.sprout(old_fact, "old", subdir="facts")

            # Create old version blob in contexts subdir
            old_ctx = Blob(type=BlobType.CONTEXT, summary="Old context", version=1)
            glob.sprout(old_ctx, "old", subdir="contexts")

            outdated = glob.check_migrations()
            paths = [str(p) for p, _ in outdated]
            print(f"Outdated found: {paths}")

            # Should find 2 outdated blobs, but will find 0
            assert len(outdated) == 2, f"Expected 2 outdated blobs, found {len(outdated)}"

    def test_decompose_cli_vs_glob_decompose_mismatch(self):
        """
        BUG INVESTIGATION: CLI decompose deletes files directly,
        but Glob.decompose() moves to archive. Inconsistent behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Use Glob.decompose directly
            blob = Blob(type=BlobType.CONTEXT, summary="Archive test")
            glob.sprout(blob, "test")
            glob.decompose("test")

            # Should be in archive
            archive_files = list((Path(tmpdir) / ".claude" / "archive").glob("*.blob.xml"))
            assert len(archive_files) == 1, "Glob.decompose should archive, not delete"

    def test_name_collision_in_archive(self):
        """
        BUG INVESTIGATION: Decomposing same-named blob twice on same day
        could overwrite the first archived version.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create and decompose first version
            blob1 = Blob(type=BlobType.CONTEXT, summary="First version")
            glob.sprout(blob1, "contested")
            glob.decompose("contested")

            # Create and decompose second version
            blob2 = Blob(type=BlobType.CONTEXT, summary="Second version")
            glob.sprout(blob2, "contested")
            glob.decompose("contested")

            # Both should exist in archive with unique names
            archive_files = list((Path(tmpdir) / ".claude" / "archive").glob("*contested*"))
            print(f"Archive files: {[f.name for f in archive_files]}")

            # This might fail if second overwrites first
            # Current format is: YYYYMMDD-name.blob.xml (no uniqueness suffix)
            # So same-day archives would collide!

    def test_empty_file_list_in_decision(self):
        """
        BUG INVESTIGATION: Decisions with empty file list elements
        get filtered but might cause issues.
        """
        # Manually create XML with empty file elements
        xml = '''<blob type="decision" scope="project" v="2" updated="2025-01-01">
            <summary>Test</summary>
            <files>
                <file></file>
                <file>real.py</file>
                <file></file>
            </files>
        </blob>'''
        blob = Blob.from_xml(xml)
        # Empty files should be filtered
        assert blob.files == ["real.py"], f"Got: {blob.files}"

    def test_decision_empty_text_filtered(self):
        """
        BUG INVESTIGATION: Decisions with empty text are filtered,
        so roundtrip loses data.
        """
        # Create with empty text decision
        xml = '''<blob type="decision" scope="project" v="2" updated="2025-01-01">
            <summary>Test</summary>
            <decisions>
                <decision why="reason1"></decision>
                <decision why="reason2">choice2</decision>
            </decisions>
        </blob>'''
        blob = Blob.from_xml(xml)

        # First decision has empty text, should be filtered
        # But this means data loss - the "reason1" is lost
        print(f"Decisions: {blob.decisions}")
        assert len(blob.decisions) == 1, "Empty text decisions filtered"
        assert blob.decisions[0] == ("choice2", "reason2")

    def test_related_refs_empty_filtered(self):
        """Similar filtering issue for related refs."""
        xml = '''<blob type="fact" scope="project" v="2" updated="2025-01-01">
            <summary>Test</summary>
            <related>
                <ref></ref>
                <ref>valid-ref</ref>
                <ref></ref>
            </related>
        </blob>'''
        blob = Blob.from_xml(xml)
        assert blob.related == ["valid-ref"]

    def test_next_steps_empty_filtered(self):
        """Similar filtering issue for next_steps."""
        xml = '''<blob type="thread" scope="project" v="2" updated="2025-01-01">
            <summary>Test</summary>
            <next>
                <step></step>
                <step>real step</step>
            </next>
        </blob>'''
        blob = Blob.from_xml(xml)
        assert blob.next_steps == ["real step"]


class TestMissingSubdirBugs:
    """
    Definitive tests for the missing subdirs bug.
    surface_relevant and check_migrations miss facts/ and contexts/.
    """

    def test_surface_relevant_complete_subdirs(self):
        """Verify which subdirs are actually checked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            glob = Glob(Path(tmpdir))

            # Create ALWAYS-scope blobs in every possible location
            locations = [
                (None, "root"),           # Root .claude/
                ("threads", "threads"),
                ("decisions", "decisions"),
                ("constraints", "constraints"),
                ("contexts", "contexts"),  # MISSING from surface_relevant!
                ("facts", "facts"),        # MISSING from surface_relevant!
            ]

            for subdir, name in locations:
                blob = Blob(
                    type=BlobType.CONSTRAINT,
                    summary=f"Blob in {name}",
                    scope=BlobScope.ALWAYS
                )
                glob.sprout(blob, name, subdir=subdir)

            relevant = glob.surface_relevant()
            summaries = [b.summary for b in relevant]
            print(f"Surfaced summaries: {summaries}")

            # Check which ones surfaced
            for subdir, name in locations:
                expected = f"Blob in {name}"
                if expected not in summaries:
                    print(f"MISSING: {expected}")

            # Currently this will show contexts and facts are missing
            assert len(relevant) == len(locations), \
                f"Expected {len(locations)} blobs, got {len(relevant)}: {summaries}"


class TestNameParsingBug:
    """
    Test the .blob name parsing bug in list_blobs.
    path.stem.replace(".blob", "") is problematic.
    """

    def test_blob_in_name_parsing(self):
        """Names containing '.blob' get mangled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            glob = Glob(project)

            # Various problematic names
            test_cases = [
                "normal",           # normal.blob.xml -> stem "normal.blob" -> "normal" ✓
                "my.blob.thing",    # my.blob.thing.blob.xml -> stem "my.blob.thing.blob" -> "my.thing" ✗
                "blob",             # blob.blob.xml -> stem "blob.blob" -> "" ✗
                "a.blob",           # a.blob.blob.xml -> stem "a.blob.blob" -> "a." ✗
                ".blob.test",       # .blob.test.blob.xml -> stem ".blob.test.blob" -> ".test" ✗
            ]

            for name in test_cases:
                blob = Blob(type=BlobType.FACT, summary=f"Test {name}")
                glob.sprout(blob, name)

            blobs = glob.list_blobs()
            returned_names = sorted([n for n, _ in blobs])
            expected_names = sorted(test_cases)

            print(f"Expected: {expected_names}")
            print(f"Got:      {returned_names}")

            for expected in expected_names:
                assert expected in returned_names, f"Name '{expected}' was mangled"
