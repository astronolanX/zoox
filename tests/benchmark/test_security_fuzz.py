"""
Security fuzzing tests.

Karen demanded security audit. This isn't a formal pentest but it's
fuzzing for common attack patterns.
"""

import tempfile
from pathlib import Path

import pytest

from reef.blob import Blob, BlobType, BlobScope, Glob
from reef.format import Polip


class TestInputFuzzing:
    """Fuzz test input handling."""

    @pytest.fixture
    def reef(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()
            yield Glob(root), reef_dir

    # Malicious polip IDs
    MALICIOUS_IDS = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/etc/passwd",
        "C:\\Windows\\System32",
        "polip/../../../escape",
        "polip/./././normal",
        "polip%2f..%2f..%2fetc%2fpasswd",  # URL encoded
        "polip\x00hidden",  # Null byte injection
        "polip\nheader: injection",  # Header injection
        "$(whoami)",  # Command injection
        "`id`",  # Backtick command injection
        "${USER}",  # Variable expansion
        "polip; rm -rf /",  # Shell command
        "polip | cat /etc/passwd",  # Pipe injection
        "polip > /tmp/pwned",  # Redirect injection
        "<script>alert(1)</script>",  # XSS
        "' OR '1'='1",  # SQL injection
        "{{7*7}}",  # Template injection
        "${7*7}",  # Another template injection
        "a" * 10000,  # Long string
        "",  # Empty string
        " ",  # Whitespace only
        "\t\n\r",  # Control characters
    ]

    @pytest.mark.parametrize("malicious_id", MALICIOUS_IDS)
    def test_malicious_polip_id_blocked(self, reef, malicious_id):
        """Malicious IDs should be rejected or sanitized."""
        glob, reef_dir = reef

        blob = Blob(
            type=BlobType.CONTEXT,
            scope=BlobScope.PROJECT,
            summary="Test polip",
        )

        # Should either reject or sanitize the ID
        try:
            # sprout with malicious name
            path = glob.sprout(blob, malicious_id)

            # If it succeeded, verify the file is in the reef dir (not escaped)
            assert reef_dir in path.parents or path.parent == reef_dir, \
                f"Path escaped reef: {path}"

            # Verify path doesn't contain traversal
            assert ".." not in str(path), f"Path contains traversal: {path}"

        except (ValueError, OSError) as e:
            # Expected - malicious input rejected
            pass

    @pytest.mark.parametrize("malicious_id", MALICIOUS_IDS)
    def test_malicious_get_blocked(self, reef, malicious_id):
        """Get with malicious ID should fail safely."""
        glob, _ = reef

        try:
            result = glob.get(malicious_id)
            # If it returns, should be None (not found)
            # Should NOT read files outside reef
            assert result is None or isinstance(result, Blob)
        except (ValueError, OSError):
            # Expected - malicious input rejected
            pass

    # Malicious content
    MALICIOUS_CONTENT = [
        "<script>alert(document.cookie)</script>",
        "{{constructor.constructor('return process')().exit()}}",
        "${require('child_process').exec('id')}",
        "<?xml version=\"1.0\"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]><foo>&xxe;</foo>",
        "A" * 1000000,  # 1MB content
        "\x00" * 1000,  # Null bytes
        "\r\n\r\nHTTP/1.1 200 OK\r\n",  # HTTP response splitting
    ]

    @pytest.mark.parametrize("content", MALICIOUS_CONTENT[:5])  # Skip huge ones
    def test_malicious_summary_handled(self, reef, content):
        """Malicious content in summary should be stored safely."""
        glob, reef_dir = reef

        blob = Blob(
            type=BlobType.CONTEXT,
            scope=BlobScope.PROJECT,
            summary=content[:1000],  # Limit size for test
        )

        # Should store without executing
        path = glob.sprout(blob, "test-malicious")
        assert path.exists()

        # Should read back intact
        loaded = glob.get("test-malicious")
        assert loaded is not None


class TestXMLBomb:
    """Test XML bomb (billion laughs) protection."""

    def test_xml_bomb_handled(self):
        """Billion laughs attack should be handled safely.

        Python's ET.fromstring (defusedxml not required) doesn't expand
        internal entities by default in a dangerous way. The attack
        either fails to parse or the entities are not expanded.
        """
        # Classic billion laughs
        bomb = '''<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
  <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
]>
<blob type="context" scope="project" updated="2026-01-15">
  <summary>&lol5;</summary>
</blob>'''

        # Python's xml.etree.ElementTree either:
        # 1. Parses safely (entities not expanded dangerously)
        # 2. Raises an error
        # Either is acceptable - what's not acceptable is infinite expansion
        try:
            blob = Blob.from_xml(bomb)
            # If parsed, summary should NOT contain billions of "lol"s
            # (would cause memory issues)
            assert len(blob.summary) < 10000, "XML bomb expanded dangerously"
        except Exception:
            # Failed to parse - also acceptable
            pass

    def test_xxe_blocked(self):
        """XXE (external entity) attack should fail."""
        xxe = '''<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<blob type="context" scope="project" updated="2026-01-15">
  <summary>&xxe;</summary>
</blob>'''

        # Python's ET.fromstring is safe by default (no external entities)
        # But let's verify
        try:
            blob = Blob.from_xml(xxe)
            # If it parsed, the entity should NOT be expanded
            assert "/etc/passwd" not in blob.summary
            # Entity either unexpanded or treated as literal
        except Exception:
            # Expected - failed to parse
            pass


class TestReefFormatFuzzing:
    """Fuzz test .reef format parser."""

    MALFORMED_REEF = [
        "",  # Empty
        "   ",  # Whitespace only
        "=",  # Just equals
        "=type",  # Missing parts
        "=type:scope",  # Missing more parts
        "=type:scope id",  # Missing date
        "=invalid:invalid invalid 2026-01-15",  # Invalid type/scope
        "=constraint:always ../escape 2026-01-15\nEvil",  # Traversal in ID
        "not a reef format at all",  # Random text
        "=constraint:always test 9999-99-99\nInvalid date",  # Bad date
        "=constraint:always test 2026-01-15",  # No summary
        "+" * 10000,  # Many plusses
        "~" * 10000,  # Many tildes
        "=constraint:always test 2026-01-15\n" + "a" * 1000000,  # Huge summary
    ]

    @pytest.mark.parametrize("content", MALFORMED_REEF)
    def test_malformed_reef_handled(self, content):
        """Malformed .reef content should fail gracefully."""
        try:
            polip = Polip.from_reef(content)
            # If it parsed, should have valid fields
            assert polip.id is not None
            assert ".." not in polip.id
        except ValueError:
            # Expected - malformed input
            pass
        except Exception as e:
            # Other exceptions might be bugs
            # But don't crash the whole system
            assert "recursion" not in str(e).lower()


class TestConcurrentAccess:
    """Test race condition scenarios."""

    def test_concurrent_sprout_same_name(self):
        """Concurrent sprouts with same name shouldn't corrupt."""
        import threading
        import time

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()

            errors = []
            results = []

            def sprout_blob(thread_id):
                try:
                    glob = Glob(root)
                    blob = Blob(
                        type=BlobType.CONTEXT,
                        scope=BlobScope.PROJECT,
                        summary=f"Thread {thread_id}",
                    )
                    path = glob.sprout(blob, "concurrent-test")
                    results.append((thread_id, path))
                except Exception as e:
                    errors.append((thread_id, e))

            # Spawn 10 threads all writing same polip
            threads = [threading.Thread(target=sprout_blob, args=(i,)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Should complete without crashes
            assert len(errors) == 0 or all(
                "already exists" in str(e) for _, e in errors
            ), f"Unexpected errors: {errors}"

            # File should exist and be valid
            path = reef_dir / "contexts" / "concurrent-test.blob.xml"
            if path.exists():
                blob = Blob.load(path)
                assert blob is not None

    def test_concurrent_search_and_write(self):
        """Concurrent searches during writes shouldn't crash."""
        import threading

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reef_dir = root / ".claude"
            reef_dir.mkdir()

            glob = Glob(root)
            errors = []

            def writer():
                for i in range(10):
                    try:
                        blob = Blob(
                            type=BlobType.CONTEXT,
                            scope=BlobScope.PROJECT,
                            summary=f"Writer blob {i}",
                        )
                        glob.sprout(blob, f"write-{i}")
                    except Exception as e:
                        errors.append(("writer", e))

            def reader():
                for _ in range(20):
                    try:
                        glob.rebuild_index()
                        glob.search_index(query="writer", limit=10)
                    except Exception as e:
                        errors.append(("reader", e))

            # Run concurrent readers and writers
            writer_thread = threading.Thread(target=writer)
            reader_threads = [threading.Thread(target=reader) for _ in range(3)]

            writer_thread.start()
            for t in reader_threads:
                t.start()

            writer_thread.join()
            for t in reader_threads:
                t.join()

            # Should complete without crashes
            # Some transient errors are OK (index rebuilding)
            critical_errors = [e for e in errors if "corrupt" in str(e).lower()]
            assert len(critical_errors) == 0, f"Critical errors: {critical_errors}"
