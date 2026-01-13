"""
Comprehensive test suite for Blob class.
Tests cover: normal operation, edge cases, stress tests, and absurd inputs.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from zoox.blob import Blob, BlobType, BlobScope, BlobStatus, BLOB_VERSION


class TestBlobBasics:
    """Basic blob creation and serialization."""

    def test_minimal_blob(self):
        """Minimum viable blob."""
        blob = Blob(type=BlobType.CONTEXT, summary="Test")
        assert blob.type == BlobType.CONTEXT
        assert blob.summary == "Test"
        assert blob.scope == BlobScope.PROJECT  # default
        assert blob.version == BLOB_VERSION

    def test_all_blob_types(self):
        """Each blob type can be created."""
        for btype in BlobType:
            blob = Blob(type=btype, summary=f"Testing {btype.value}")
            assert blob.type == btype

    def test_all_scopes(self):
        """Each scope can be assigned."""
        for scope in BlobScope:
            blob = Blob(type=BlobType.THREAD, summary="Test", scope=scope)
            assert blob.scope == scope

    def test_all_statuses(self):
        """Each status can be assigned."""
        for status in BlobStatus:
            blob = Blob(type=BlobType.THREAD, summary="Test", status=status)
            assert blob.status == status

    def test_full_blob_all_fields(self):
        """Blob with every field populated."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Full test blob",
            scope=BlobScope.ALWAYS,
            status=BlobStatus.ACTIVE,
            updated=datetime(2025, 1, 15),
            version=2,
            context="Some context here",
            files=["src/foo.py", "src/bar.py"],
            decisions=[("Use pytest", "Standard for Python"), ("Use dataclasses", "Built-in")],
            blocked_by="Waiting for review",
            next_steps=["Step 1", "Step 2", "Step 3"],
            facts=["Fact A", "Fact B"],
            related=["other-blob", "another-blob"],
        )
        assert blob.context == "Some context here"
        assert len(blob.files) == 2
        assert len(blob.decisions) == 2
        assert blob.blocked_by == "Waiting for review"
        assert len(blob.next_steps) == 3


class TestBlobXmlSerialization:
    """XML round-trip serialization tests."""

    def test_roundtrip_minimal(self):
        """Minimal blob survives serialization."""
        original = Blob(type=BlobType.FACT, summary="Minimal")
        xml = original.to_xml()
        restored = Blob.from_xml(xml)

        assert restored.type == original.type
        assert restored.summary == original.summary
        assert restored.version == original.version

    def test_roundtrip_full(self):
        """Full blob survives serialization."""
        original = Blob(
            type=BlobType.DECISION,
            summary="Full blob roundtrip",
            scope=BlobScope.ALWAYS,
            status=BlobStatus.DONE,
            updated=datetime(2025, 6, 15),
            context="Testing roundtrip",
            files=["a.py", "b.py"],
            decisions=[("Choice A", "Reason A"), ("Choice B", "Reason B")],
            blocked_by="Nothing",
            next_steps=["Do X", "Do Y"],
            facts=["F1", "F2"],
            related=["ref1", "ref2"],
        )
        xml = original.to_xml()
        restored = Blob.from_xml(xml)

        assert restored.type == original.type
        assert restored.summary == original.summary
        assert restored.scope == original.scope
        assert restored.status == original.status
        assert restored.context == original.context
        assert restored.files == original.files
        assert restored.decisions == original.decisions
        assert restored.blocked_by == original.blocked_by
        assert restored.next_steps == original.next_steps
        assert restored.facts == original.facts
        assert restored.related == original.related

    def test_xml_well_formed(self):
        """Generated XML is valid."""
        blob = Blob(type=BlobType.THREAD, summary="Valid XML test")
        xml = blob.to_xml()
        # Should not raise
        root = ET.fromstring(xml)
        assert root.tag == "blob"

    def test_xml_attributes(self):
        """XML has correct attributes."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Attr test",
            scope=BlobScope.ALWAYS,
            status=BlobStatus.BLOCKED,
            version=2,
        )
        xml = blob.to_xml()
        root = ET.fromstring(xml)

        assert root.get("type") == "thread"
        assert root.get("scope") == "always"
        assert root.get("status") == "blocked"
        assert root.get("v") == "2"


class TestBlobEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_summary(self):
        """Empty summary is allowed."""
        blob = Blob(type=BlobType.FACT, summary="")
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert restored.summary == ""

    def test_empty_lists(self):
        """Empty lists serialize correctly."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Empty lists",
            files=[],
            decisions=[],
            next_steps=[],
            facts=[],
            related=[],
        )
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert restored.files == []
        assert restored.decisions == []

    def test_special_characters_in_summary(self):
        """XML special chars in summary."""
        blob = Blob(type=BlobType.FACT, summary='Test <>&"\' chars')
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert restored.summary == 'Test <>&"\' chars'

    def test_unicode_in_all_fields(self):
        """Unicode throughout blob."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Unicode: 日本語 Emoji: 🚀 Math: ∑∏∫",
            context="More unicode: α β γ δ ε",
            files=["路径/文件.py"],
            decisions=[("选择", "原因")],
            facts=["事实一"],
            next_steps=["下一步"],
        )
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert "日本語" in restored.summary
        assert "🚀" in restored.summary
        assert restored.facts == ["事实一"]

    def test_multiline_context(self):
        """Multiline content preserves newlines."""
        multiline = """Line 1
Line 2
Line 3

Blank line above."""
        blob = Blob(type=BlobType.CONTEXT, summary="Multiline test", context=multiline)
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert "Line 2" in restored.context
        # Note: XML parsing may normalize whitespace somewhat

    def test_very_long_summary(self):
        """Very long summary."""
        long_summary = "x" * 10000
        blob = Blob(type=BlobType.FACT, summary=long_summary)
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert len(restored.summary) == 10000

    def test_many_files(self):
        """Many file references."""
        files = [f"src/file_{i}.py" for i in range(500)]
        blob = Blob(type=BlobType.THREAD, summary="Many files", files=files)
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert len(restored.files) == 500

    def test_many_decisions(self):
        """Many decisions."""
        decisions = [(f"choice_{i}", f"reason_{i}") for i in range(200)]
        blob = Blob(type=BlobType.DECISION, summary="Many decisions", decisions=decisions)
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert len(restored.decisions) == 200

    def test_none_status(self):
        """Status can be None."""
        blob = Blob(type=BlobType.FACT, summary="Test blob", status=None)
        xml = blob.to_xml()
        # Status attribute should not appear in root element
        assert 'status="' not in xml  # attribute should be absent
        restored = Blob.from_xml(xml)
        assert restored.status is None

    def test_none_blocked_by(self):
        """blocked_by can be None."""
        blob = Blob(type=BlobType.THREAD, summary="Not blocked", blocked_by=None)
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert restored.blocked_by is None

    def test_decision_with_empty_why(self):
        """Decision with empty 'why' field."""
        blob = Blob(type=BlobType.DECISION, summary="Test", decisions=[("choice", "")])
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert restored.decisions[0] == ("choice", "")


class TestBlobMigration:
    """Schema migration tests."""

    def test_needs_migration_false(self):
        """Current version doesn't need migration."""
        blob = Blob(type=BlobType.FACT, summary="Current", version=BLOB_VERSION)
        assert not blob.needs_migration()

    def test_needs_migration_true(self):
        """Old version needs migration."""
        blob = Blob(type=BlobType.FACT, summary="Old", version=1)
        assert blob.needs_migration()

    def test_migrate_updates_version(self):
        """Migration updates version number."""
        blob = Blob(type=BlobType.FACT, summary="Old", version=1)
        blob.migrate()
        assert blob.version == BLOB_VERSION

    def test_migrate_updates_timestamp(self):
        """Migration updates timestamp."""
        old_time = datetime(2020, 1, 1)
        blob = Blob(type=BlobType.FACT, summary="Old", version=1, updated=old_time)
        blob.migrate()
        assert blob.updated > old_time

    def test_migrate_idempotent(self):
        """Multiple migrations don't break anything."""
        blob = Blob(type=BlobType.FACT, summary="Test", version=1)
        blob.migrate()
        first_version = blob.version
        blob.migrate()
        blob.migrate()
        assert blob.version == first_version


class TestBlobFilePersistence:
    """File save/load tests."""

    def test_save_and_load(self):
        """Basic file persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.blob.xml"
            blob = Blob(type=BlobType.CONSTRAINT, summary="Persist test")
            blob.save(path)

            assert path.exists()
            loaded = Blob.load(path)
            assert loaded.summary == "Persist test"

    def test_save_creates_parent_dirs(self):
        """Save creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "deep" / "nested" / "dir" / "test.blob.xml"
            blob = Blob(type=BlobType.FACT, summary="Nested")
            blob.save(path)
            assert path.exists()

    def test_save_overwrite(self):
        """Save overwrites existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.blob.xml"

            blob1 = Blob(type=BlobType.FACT, summary="First")
            blob1.save(path)

            blob2 = Blob(type=BlobType.FACT, summary="Second")
            blob2.save(path)

            loaded = Blob.load(path)
            assert loaded.summary == "Second"

    def test_load_nonexistent_file_raises(self):
        """Loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            Blob.load(Path("/nonexistent/path/file.blob.xml"))


class TestBlobStress:
    """Stress tests with absurd inputs."""

    def test_gigantic_context(self):
        """Huge context field."""
        huge_context = "x" * 1_000_000  # 1MB of text
        blob = Blob(type=BlobType.CONTEXT, summary="Huge", context=huge_context)
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert len(restored.context) == 1_000_000

    def test_deeply_nested_paths(self):
        """Very long file paths."""
        deep_path = "/".join(["dir"] * 100) + "/file.py"
        blob = Blob(type=BlobType.THREAD, summary="Deep paths", files=[deep_path])
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert restored.files[0] == deep_path

    def test_all_punctuation(self):
        """All ASCII punctuation in summary."""
        punct = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        blob = Blob(type=BlobType.FACT, summary=punct)
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        # Some chars may be escaped, but content should survive
        assert len(restored.summary) > 0

    def test_newlines_in_filename(self):
        """Pathological: newlines in file reference."""
        weird_file = "file\nwith\nnewlines.py"
        blob = Blob(type=BlobType.THREAD, summary="Weird", files=[weird_file])
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert "\n" in restored.files[0]

    def test_null_bytes_in_context(self):
        """Null bytes in context - behavior check."""
        # Python's ET may handle this differently across versions
        # We just verify it doesn't crash or silently corrupt
        blob = Blob(type=BlobType.CONTEXT, summary="Null", context="has\x00null")
        try:
            xml = blob.to_xml()
            # If it generates XML, verify it can be parsed back
            restored = Blob.from_xml(xml)
            # Content may be preserved or stripped - just don't crash
        except (ValueError, ET.ParseError):
            pass  # Also acceptable - rejecting invalid chars

    def test_control_characters(self):
        """ASCII control characters."""
        # Most control chars are invalid in XML 1.0
        # Test with allowed ones: tab, newline, carriage return
        blob = Blob(type=BlobType.FACT, summary="Control\t\n\rchars")
        xml = blob.to_xml()
        restored = Blob.from_xml(xml)
        assert "Control" in restored.summary

    def test_empty_decision_text(self):
        """Decision with empty text."""
        blob = Blob(type=BlobType.DECISION, summary="Test", decisions=[("", "why")])
        xml = blob.to_xml()
        # Empty text should be handled - may not roundtrip
        root = ET.fromstring(xml)
        # Just verify XML is valid

    def test_rapid_serialization(self):
        """Serialize/deserialize many times."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Rapid test",
            files=["a.py", "b.py"],
            decisions=[("x", "y")],
        )
        for _ in range(1000):
            xml = blob.to_xml()
            blob = Blob.from_xml(xml)
        assert blob.summary == "Rapid test"


class TestBlobFromXmlEdgeCases:
    """Edge cases when parsing XML."""

    def test_missing_type_defaults_to_context(self):
        """Missing type attribute defaults to context."""
        xml = '<blob scope="project" updated="2025-01-01" v="2"><summary>Test</summary></blob>'
        blob = Blob.from_xml(xml)
        assert blob.type == BlobType.CONTEXT

    def test_missing_scope_defaults_to_project(self):
        """Missing scope defaults to project."""
        xml = '<blob type="fact" updated="2025-01-01" v="2"><summary>Test</summary></blob>'
        blob = Blob.from_xml(xml)
        assert blob.scope == BlobScope.PROJECT

    def test_missing_version_defaults_to_1(self):
        """Missing version defaults to 1 (for old blobs)."""
        xml = '<blob type="fact" scope="project" updated="2025-01-01"><summary>Test</summary></blob>'
        blob = Blob.from_xml(xml)
        assert blob.version == 1

    def test_missing_updated_uses_now(self):
        """Missing updated uses current time."""
        xml = '<blob type="fact" scope="project" v="2"><summary>Test</summary></blob>'
        before = datetime.now()
        blob = Blob.from_xml(xml)
        after = datetime.now()
        assert before <= blob.updated <= after

    def test_missing_summary_element(self):
        """Missing summary element gives empty string."""
        xml = '<blob type="fact" scope="project" v="2"></blob>'
        blob = Blob.from_xml(xml)
        assert blob.summary == ""

    def test_extra_unknown_elements_ignored(self):
        """Unknown elements are ignored."""
        xml = '''<blob type="fact" scope="project" v="2" updated="2025-01-01">
            <summary>Test</summary>
            <unknown>This should be ignored</unknown>
            <weird foo="bar">Also ignored</weird>
        </blob>'''
        blob = Blob.from_xml(xml)
        assert blob.summary == "Test"

    def test_invalid_xml_raises(self):
        """Invalid XML raises parsing error."""
        with pytest.raises(ET.ParseError):
            Blob.from_xml("not valid xml at all")

    def test_invalid_type_raises(self):
        """Invalid type value raises."""
        xml = '<blob type="invalid_type" scope="project" v="2"><summary>Test</summary></blob>'
        with pytest.raises(ValueError):
            Blob.from_xml(xml)

    def test_invalid_scope_raises(self):
        """Invalid scope value raises."""
        xml = '<blob type="fact" scope="invalid_scope" v="2"><summary>Test</summary></blob>'
        with pytest.raises(ValueError):
            Blob.from_xml(xml)

    def test_invalid_status_raises(self):
        """Invalid status value raises."""
        xml = '<blob type="thread" status="invalid_status" scope="project" v="2"><summary>Test</summary></blob>'
        with pytest.raises(ValueError):
            Blob.from_xml(xml)
