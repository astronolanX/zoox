"""
Benchmark: .reef format efficiency vs XML

Real measurements on actual data. No estimates.
"""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from reef.format import Polip, Reef


# Ground truth test fixtures
POLIP_FIXTURES = [
    {
        "id": "simple-constraint",
        "type": "constraint",
        "scope": "always",
        "summary": "Never commit secrets",
        "facts": [],
        "decisions": [],
        "context": [],
        "steps": [],
    },
    {
        "id": "project-rules",
        "type": "constraint",
        "scope": "always",
        "summary": "reef project constraints",
        "facts": [
            "Use uv for package management, not pip",
            "Run tests with: uv run pytest",
            "Local-only package - not published to PyPI",
            "Zero dependencies - stdlib only",
        ],
        "decisions": [],
        "context": [
            "reef is symbiotic memory for AI - XML polips that persist across sessions.",
            "Coral terminology: polip (blob), reef (glob), current (thread), bedrock (constraint).",
        ],
        "steps": [],
    },
    {
        "id": "active-thread",
        "type": "thread",
        "scope": "project",
        "summary": "Implement user authentication system",
        "facts": [
            "Using JWT tokens",
            "Refresh token rotation enabled",
        ],
        "decisions": [
            "OAuth2 over SAML for simplicity",
            "PostgreSQL for session storage",
        ],
        "context": ["Current focus: token validation middleware"],
        "steps": [
            (True, "Set up JWT library"),
            (True, "Create user model"),
            (False, "Implement login endpoint"),
            (False, "Add refresh token rotation"),
            (False, "Write integration tests"),
        ],
        "status": "active",
    },
    {
        "id": "complex-context",
        "type": "context",
        "scope": "session",
        "summary": "Debugging session for memory leak in worker pool",
        "facts": [
            "Memory grows 2MB/hour under load",
            "gc.collect() doesn't reclaim",
            "WeakRef queue is 10k+ entries",
            "Happens only in production",
            "Started after v2.3.1 deployment",
        ],
        "decisions": [
            "Added memory profiling hook",
            "Bisecting commits between v2.3.0 and v2.3.1",
        ],
        "context": [
            "Suspect: connection pool not closing properly",
            "Evidence: netstat shows 500+ TIME_WAIT sockets",
        ],
        "steps": [
            (True, "Reproduce locally"),
            (True, "Add memory instrumentation"),
            (False, "Identify root cause"),
            (False, "Fix and verify"),
        ],
        "status": "active",
    },
]


def _polip_to_xml(p: dict) -> str:
    """Convert fixture dict to legacy XML format."""
    from datetime import date

    root = ET.Element("blob", {
        "type": p["type"],
        "scope": p["scope"],
        "updated": date.today().isoformat(),
        "v": "2",
    })
    if p.get("status"):
        root.set("status", p["status"])

    summary = ET.SubElement(root, "summary")
    summary.text = p["summary"]

    if p["facts"]:
        facts_el = ET.SubElement(root, "facts")
        for fact in p["facts"]:
            f = ET.SubElement(facts_el, "fact")
            f.text = fact

    if p["decisions"]:
        decisions_el = ET.SubElement(root, "decisions")
        for dec in p["decisions"]:
            d = ET.SubElement(decisions_el, "decision")
            d.text = dec

    if p["context"]:
        ctx_el = ET.SubElement(root, "context")
        ctx_el.text = "\n".join(p["context"])

    if p["steps"]:
        next_el = ET.SubElement(root, "next")
        for done, step in p["steps"]:
            s = ET.SubElement(next_el, "step")
            if done:
                s.set("status", "done")
            s.text = step

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


def _polip_to_reef(p: dict) -> str:
    """Convert fixture dict to .reef format."""
    from datetime import date

    polip = Polip(
        id=p["id"],
        type=p["type"],
        scope=p["scope"],
        updated=date.today(),
        summary=p["summary"],
        facts=p["facts"],
        decisions=p["decisions"],
        context=p["context"],
        steps=p["steps"],
        status=p.get("status"),
    )
    return polip.to_reef()


class TestFormatEfficiency:
    """Measure actual byte and token savings."""

    @pytest.mark.parametrize("fixture", POLIP_FIXTURES, ids=lambda p: p["id"])
    def test_byte_savings(self, fixture):
        """Measure byte reduction from XML to .reef."""
        xml_bytes = len(_polip_to_xml(fixture).encode("utf-8"))
        reef_bytes = len(_polip_to_reef(fixture).encode("utf-8"))

        savings_pct = ((xml_bytes - reef_bytes) / xml_bytes) * 100

        # Record for reporting
        print(f"\n{fixture['id']}:")
        print(f"  XML:  {xml_bytes:>5} bytes")
        print(f"  REEF: {reef_bytes:>5} bytes")
        print(f"  Savings: {savings_pct:.1f}%")

        # Assert minimum savings (conservative)
        assert reef_bytes <= xml_bytes, "REEF should not be larger than XML"

    @pytest.mark.parametrize("fixture", POLIP_FIXTURES, ids=lambda p: p["id"])
    def test_token_savings(self, fixture):
        """Measure token reduction (chars/4 approximation)."""
        xml_content = _polip_to_xml(fixture)
        reef_content = _polip_to_reef(fixture)

        # Token approximation: ~4 chars per token
        xml_tokens = len(xml_content) // 4
        reef_tokens = len(reef_content) // 4

        savings_pct = ((xml_tokens - reef_tokens) / xml_tokens) * 100

        print(f"\n{fixture['id']}:")
        print(f"  XML:  ~{xml_tokens:>4} tokens")
        print(f"  REEF: ~{reef_tokens:>4} tokens")
        print(f"  Savings: {savings_pct:.1f}%")

        assert reef_tokens <= xml_tokens

    def test_aggregate_savings(self):
        """Total savings across all fixtures."""
        total_xml = 0
        total_reef = 0

        for fixture in POLIP_FIXTURES:
            total_xml += len(_polip_to_xml(fixture).encode("utf-8"))
            total_reef += len(_polip_to_reef(fixture).encode("utf-8"))

        savings_pct = ((total_xml - total_reef) / total_xml) * 100

        print(f"\nAGGREGATE:")
        print(f"  Total XML:  {total_xml:>6} bytes")
        print(f"  Total REEF: {total_reef:>6} bytes")
        print(f"  Total Savings: {savings_pct:.1f}%")

        # This is the REAL number - not an estimate
        # Karen was right to call out the 28% claim
        # Let's see what we actually get
        assert savings_pct > 0, "REEF should save some bytes"


class TestRoundTripFidelity:
    """Verify data survives serialization."""

    @pytest.mark.parametrize("fixture", POLIP_FIXTURES, ids=lambda p: p["id"])
    def test_round_trip(self, fixture):
        """Serialize to .reef, parse back, verify equality."""
        from datetime import date

        original = Polip(
            id=fixture["id"],
            type=fixture["type"],
            scope=fixture["scope"],
            updated=date.today(),
            summary=fixture["summary"],
            facts=fixture["facts"],
            decisions=fixture["decisions"],
            context=fixture["context"],
            steps=fixture["steps"],
            status=fixture.get("status"),
        )

        # Round trip
        reef_str = original.to_reef()
        restored = Polip.from_reef(reef_str)

        # Verify all fields
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.scope == original.scope
        assert restored.updated == original.updated
        assert restored.summary == original.summary
        assert restored.facts == original.facts
        assert restored.decisions == original.decisions
        assert restored.context == original.context
        assert restored.steps == original.steps
        assert restored.status == original.status

    def test_file_round_trip(self):
        """Verify save/load cycle preserves data."""
        from datetime import date

        with tempfile.TemporaryDirectory() as tmp:
            reef_dir = Path(tmp) / ".claude"
            reef_dir.mkdir()

            original = Polip(
                id="test-polip",
                type="context",
                scope="session",
                updated=date.today(),
                summary="Test polip for file round trip",
                facts=["Fact one", "Fact two"],
                decisions=["Decision A"],
                context=["Some context here"],
                steps=[(True, "Done step"), (False, "Pending step")],
            )

            # Save
            filepath = original.save(reef_dir)
            assert filepath.exists()

            # Load
            restored = Polip.load(filepath)

            # Verify
            assert restored.id == original.id
            assert restored.facts == original.facts
            assert restored.steps == original.steps


class TestFormatResilience:
    """Test edge cases and malformed input."""

    def test_crlf_handling(self):
        """Windows line endings don't break parsing."""
        reef_content = "=constraint:always test 2026-01-15\r\nSummary\r\n+fact one\r\n+fact two\r\n"

        polip = Polip.from_reef(reef_content)

        assert polip.id == "test"
        assert polip.summary == "Summary"
        assert polip.facts == ["fact one", "fact two"]

    def test_mixed_line_endings(self):
        """Mixed CR, LF, CRLF all work."""
        reef_content = "=constraint:always test 2026-01-15\nSummary\r+fact one\r\n+fact two\n"

        polip = Polip.from_reef(reef_content)

        assert polip.id == "test"
        assert len(polip.facts) == 2

    def test_continuation_lines(self):
        """Lines without sigils continue previous context."""
        reef_content = """=context:session test 2026-01-15
Multi-line summary test
~First context line
This continues the context
And this too
~Second context line"""

        polip = Polip.from_reef(reef_content)

        assert len(polip.context) == 2
        assert "This continues the context" in polip.context[0]
        assert "And this too" in polip.context[0]

    def test_empty_lines_ignored(self):
        """Blank lines don't break parsing."""
        reef_content = """=constraint:always test 2026-01-15
Summary

+fact one

+fact two

"""
        polip = Polip.from_reef(reef_content)

        assert polip.facts == ["fact one", "fact two"]

    def test_path_traversal_blocked(self):
        """Path traversal attempts raise error."""
        with pytest.raises(ValueError, match="Path traversal"):
            Polip.from_reef("=constraint:always ../../../etc/passwd 2026-01-15\nHack attempt")

    def test_invalid_id_characters_blocked(self):
        """Special characters in ID raise error."""
        with pytest.raises(ValueError, match="Invalid characters"):
            Polip.from_reef("=constraint:always test;rm-rf 2026-01-15\nHack attempt")

    def test_absolute_path_blocked(self):
        """Absolute paths in ID raise error."""
        with pytest.raises(ValueError, match="Absolute path"):
            Polip.from_reef("=constraint:always /etc/passwd 2026-01-15\nHack attempt")

    def test_empty_polip_error(self):
        """Empty content raises clear error."""
        with pytest.raises(ValueError, match="Empty"):
            Polip.from_reef("")

    def test_missing_identity_error(self):
        """Missing = prefix raises clear error."""
        with pytest.raises(ValueError, match="Invalid identity"):
            Polip.from_reef("constraint:always test 2026-01-15\nNo equals sign")
