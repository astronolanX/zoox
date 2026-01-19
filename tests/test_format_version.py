"""
Tests for .reef format versioning and roundtrip fidelity.

Tests cover:
1. EPOCH.SCHEMA versioning format
2. Questions field serialization (P0 fix)
3. Forward compatibility (unknown sections)
4. Roundtrip fidelity for all fields
"""

import pytest
from datetime import date

from reef.format import (
    Polip,
    POLIP_EPOCH,
    POLIP_SCHEMA,
    polip_version,
    parse_version,
    version_can_read,
    version_needs_migration,
)


class TestVersioning:
    """Tests for EPOCH.SCHEMA versioning."""

    def test_polip_version_format(self):
        """Version should be EPOCH.SCHEMA format."""
        v = polip_version()
        assert "." in v
        epoch, schema = v.split(".")
        assert epoch.isdigit()
        assert schema.isdigit()

    def test_polip_version_current(self):
        """Current version should be 2.1."""
        assert polip_version() == "2.1"
        assert POLIP_EPOCH == 2
        assert POLIP_SCHEMA == 1

    def test_parse_version_new_format(self):
        """Parse EPOCH.SCHEMA format."""
        epoch, schema = parse_version("2.1")
        assert epoch == 2
        assert schema == 1

        epoch, schema = parse_version("3.5")
        assert epoch == 3
        assert schema == 5

    def test_parse_version_legacy_integer(self):
        """Parse legacy integer format (e.g., "2")."""
        epoch, schema = parse_version("2")
        assert epoch == 2
        assert schema == 0

        epoch, schema = parse_version(2)
        assert epoch == 2
        assert schema == 0

    def test_version_can_read_same_epoch(self):
        """Reader can read same epoch."""
        assert version_can_read("2.1", "2.0") is True
        assert version_can_read("2.1", "2.1") is True

    def test_version_can_read_older_epoch(self):
        """Reader can read older epoch."""
        assert version_can_read("2.1", "1.0") is True
        assert version_can_read("3.0", "2.1") is True

    def test_version_cannot_read_newer_epoch(self):
        """Reader cannot read newer epoch."""
        assert version_can_read("2.1", "3.0") is False
        assert version_can_read("1.0", "2.1") is False

    def test_version_needs_migration_older_epoch(self):
        """Older epoch needs migration."""
        assert version_needs_migration("1.0") is True

    def test_version_needs_migration_older_schema(self):
        """Older schema within same epoch needs migration."""
        assert version_needs_migration("2.0") is True

    def test_version_needs_migration_current(self):
        """Current version doesn't need migration."""
        assert version_needs_migration(polip_version()) is False

    def test_polip_default_version(self):
        """New polips get current version."""
        polip = Polip(id="test", type="context")
        assert polip.version == polip_version()

    def test_polip_needs_migration_method(self):
        """Polip.needs_migration() works."""
        polip = Polip(id="test", type="context", version="1.0")
        assert polip.needs_migration() is True

        polip = Polip(id="test", type="context", version=polip_version())
        assert polip.needs_migration() is False

    def test_polip_migrate_updates_version(self):
        """Polip.migrate() updates to current version."""
        polip = Polip(id="test", type="context", version="2.0")
        polip.migrate()
        assert polip.version == polip_version()


class TestQuestionsField:
    """Tests for questions field serialization (P0 fix)."""

    def test_questions_roundtrip(self):
        """Questions should survive roundtrip."""
        original = Polip(
            id="test-questions",
            type="thread",
            questions=["What is the best approach?", "Should we refactor first?"],
        )

        serialized = original.to_reef()
        restored = Polip.from_reef(serialized)

        assert restored.questions == original.questions

    def test_questions_in_serialized_output(self):
        """Questions section should appear in serialized output."""
        polip = Polip(
            id="test",
            type="context",
            questions=["Why?", "How?"],
        )

        serialized = polip.to_reef()
        assert "--- question" in serialized
        assert "- Why?" in serialized
        assert "- How?" in serialized

    def test_empty_questions_not_serialized(self):
        """Empty questions list shouldn't create section."""
        polip = Polip(id="test", type="context", questions=[])
        serialized = polip.to_reef()
        assert "--- question" not in serialized


class TestForwardCompatibility:
    """Tests for unknown section preservation."""

    def test_unknown_section_preserved(self):
        """Unknown sections from newer versions should be preserved."""
        # Simulate a polip from future version with unknown section
        future_polip = """~ type: thread
~ id: future-test
~ version: 2.5

--- surface
This is from the future.

--- critique
This section doesn't exist in 2.1.
But it should be preserved!

--- link
[[other-polip]]
"""
        polip = Polip.from_reef(future_polip)

        # Unknown section should be captured
        assert "critique" in polip.unknown_sections
        assert "This section doesn't exist" in polip.unknown_sections["critique"]

        # Should survive roundtrip
        serialized = polip.to_reef()
        assert "--- critique" in serialized

    def test_multiple_unknown_sections(self):
        """Multiple unknown sections should all be preserved."""
        future_polip = """~ type: context
~ id: multi-unknown
~ version: 3.0

--- surface
Content.

--- alpha
Alpha section content.

--- beta
Beta section content.

--- gamma
Gamma section content.
"""
        polip = Polip.from_reef(future_polip)

        assert len(polip.unknown_sections) == 3
        assert "alpha" in polip.unknown_sections
        assert "beta" in polip.unknown_sections
        assert "gamma" in polip.unknown_sections

    def test_known_sections_not_in_unknown(self):
        """Known sections shouldn't appear in unknown_sections."""
        polip_text = """~ type: thread
~ id: known-test
~ version: 2.1

--- surface
Surface content.

--- decide
- Decision one

--- fact
- Fact one
"""
        polip = Polip.from_reef(polip_text)
        assert len(polip.unknown_sections) == 0


class TestRoundtripFidelity:
    """Tests for complete roundtrip fidelity."""

    def test_roundtrip_all_fields(self):
        """All fields should survive roundtrip."""
        original = Polip(
            id="complete-test",
            type="thread",
            scope="always",
            updated=date(2026, 1, 19),
            priority=80,
            tokens=152,
            surface="This is the surface content.\nWith multiple lines.",
            facts=["Fact one", "Fact two with\nmultiple lines"],
            decisions=["Decision A", "Decision B"],
            questions=["Question 1?", "Question 2?"],
            steps=[(True, "Done step"), (False, "Pending step")],
            links=["other-polip", "another-polip"],
            files=["src/main.py", "tests/test.py"],
            heat=0.8,
            touched=5,
            decay_rate=0.15,
            status="active",
            blocked_by=None,
        )

        serialized = original.to_reef()
        restored = Polip.from_reef(serialized)

        # All fields should match
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.scope == original.scope
        assert restored.updated == original.updated
        assert restored.priority == original.priority
        assert restored.tokens == original.tokens
        assert restored.surface == original.surface
        assert restored.facts == original.facts
        assert restored.decisions == original.decisions
        assert restored.questions == original.questions
        assert restored.steps == original.steps
        assert restored.links == original.links
        assert restored.files == original.files
        assert restored.heat == original.heat
        assert restored.touched == original.touched
        assert restored.decay_rate == original.decay_rate
        assert restored.status == original.status

    def test_roundtrip_minimal_polip(self):
        """Minimal polip (just id and type) should roundtrip."""
        original = Polip(id="minimal", type="context")
        serialized = original.to_reef()
        restored = Polip.from_reef(serialized)

        assert restored.id == original.id
        assert restored.type == original.type

    def test_roundtrip_with_special_characters(self):
        """Content with special characters should roundtrip."""
        original = Polip(
            id="special-chars",
            type="context",
            surface="Code: `print('hello')` and math: 2 + 2 = 4",
            facts=["Contains: colons", "Has --- dashes in middle"],
        )

        serialized = original.to_reef()
        restored = Polip.from_reef(serialized)

        assert restored.surface == original.surface
        assert restored.facts == original.facts

    def test_roundtrip_version_preserved(self):
        """Version should be preserved on roundtrip."""
        # New polip gets current version
        polip = Polip(id="test", type="context")
        serialized = polip.to_reef()
        assert f"~ version: {polip_version()}" in serialized

        # Legacy version preserved on read
        legacy = """~ type: context
~ id: legacy
~ version: 2.0
"""
        restored = Polip.from_reef(legacy)
        assert restored.version == "2.0"


class TestLegacyCompatibility:
    """Tests for backward compatibility with v1 and legacy formats."""

    def test_parse_legacy_integer_version_in_file(self):
        """Files with integer version (e.g., '2') should parse."""
        legacy_content = """~ type: thread
~ id: legacy-int
~ version: 2

--- surface
Legacy content.
"""
        polip = Polip.from_reef(legacy_content)
        assert polip.id == "legacy-int"
        assert polip.version == "2"

    def test_v1_format_still_parses(self):
        """v1 (=type:scope) format should still parse."""
        v1_content = """=thread:project legacy-polip 2026-01-19 active
Summary line here
+Fact one
+Fact two
!Decision made
?Question asked
[x] Done step
[ ] Pending step
@linked-polip
~Context line one
~Context line two
"""
        polip = Polip.from_reef(v1_content)
        assert polip.id == "legacy-polip"
        assert polip.type == "thread"
        assert polip.scope == "project"
        assert polip.status == "active"
        assert len(polip.facts) == 2
        assert len(polip.decisions) == 1
        assert len(polip.questions) == 1
        assert len(polip.steps) == 2


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_sections_handled(self):
        """Empty sections shouldn't cause issues."""
        content = """~ type: context
~ id: empty-sections
~ version: 2.1

--- surface

--- decide

--- fact
"""
        polip = Polip.from_reef(content)
        assert polip.surface == ""
        assert polip.decisions == []
        assert polip.facts == []

    def test_blocked_by_field(self):
        """blocked_by field should roundtrip."""
        polip = Polip(
            id="blocked-test",
            type="thread",
            status="blocked",
            blocked_by="Waiting for API response",
        )
        serialized = polip.to_reef()
        restored = Polip.from_reef(serialized)

        assert restored.status == "blocked"
        assert restored.blocked_by == "Waiting for API response"
