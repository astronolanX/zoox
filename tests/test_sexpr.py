"""Tests for S-expression parser and serializer."""

import pytest
from datetime import datetime

from reef.sexpr import (
    Tokenizer, TokenType, Token,
    Parser, SExpr, parse_sexpr,
    sexpr_to_blob, blob_to_sexpr,
    estimate_tokens, compare_formats,
    _escape_string, _unescape_string,
)
from reef.blob import Blob, BlobType, BlobScope, BlobStatus


class TestTokenizer:
    """Test the S-expression tokenizer."""

    def test_empty_input(self):
        tokens = list(Tokenizer("").tokenize())
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_whitespace_only(self):
        tokens = list(Tokenizer("   \n\t  ").tokenize())
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF

    def test_parens(self):
        tokens = list(Tokenizer("()").tokenize())
        assert tokens[0].type == TokenType.LPAREN
        assert tokens[1].type == TokenType.RPAREN
        assert tokens[2].type == TokenType.EOF

    def test_symbol(self):
        tokens = list(Tokenizer("polip").tokenize())
        assert tokens[0].type == TokenType.SYMBOL
        assert tokens[0].value == "polip"

    def test_symbol_with_dashes(self):
        tokens = list(Tokenizer("reef-native-format").tokenize())
        assert tokens[0].type == TokenType.SYMBOL
        assert tokens[0].value == "reef-native-format"

    def test_keyword(self):
        tokens = list(Tokenizer(":scope").tokenize())
        assert tokens[0].type == TokenType.KEYWORD
        assert tokens[0].value == "scope"

    def test_string_simple(self):
        tokens = list(Tokenizer('"hello world"').tokenize())
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello world"

    def test_string_with_escapes(self):
        tokens = list(Tokenizer(r'"line1\nline2\ttab"').tokenize())
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "line1\nline2\ttab"

    def test_string_with_escaped_quotes(self):
        tokens = list(Tokenizer(r'"say \"hello\""').tokenize())
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == 'say "hello"'

    def test_string_with_backslash(self):
        tokens = list(Tokenizer(r'"path\\to\\file"').tokenize())
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == 'path\\to\\file'

    def test_number_int(self):
        tokens = list(Tokenizer("42").tokenize())
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 42

    def test_number_float(self):
        tokens = list(Tokenizer("3.14").tokenize())
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 3.14

    def test_comment(self):
        tokens = list(Tokenizer("; this is a comment\npolip").tokenize())
        assert tokens[0].type == TokenType.SYMBOL
        assert tokens[0].value == "polip"

    def test_comment_at_end(self):
        tokens = list(Tokenizer("polip ; comment").tokenize())
        assert tokens[0].type == TokenType.SYMBOL
        assert tokens[1].type == TokenType.EOF

    def test_complex_expression(self):
        source = '(polip thread my-name :scope project "a string" 42)'
        tokens = list(Tokenizer(source).tokenize())
        types = [t.type for t in tokens]
        assert types == [
            TokenType.LPAREN,
            TokenType.SYMBOL,  # polip
            TokenType.SYMBOL,  # thread
            TokenType.SYMBOL,  # my-name
            TokenType.KEYWORD,  # scope
            TokenType.SYMBOL,  # project
            TokenType.STRING,  # "a string"
            TokenType.NUMBER,  # 42
            TokenType.RPAREN,
            TokenType.EOF,
        ]

    def test_unterminated_string(self):
        with pytest.raises(SyntaxError, match="Unterminated string"):
            list(Tokenizer('"unclosed').tokenize())

    def test_unexpected_char(self):
        with pytest.raises(SyntaxError, match="Unexpected character"):
            list(Tokenizer("$invalid").tokenize())

    # --- Sigil sugar tests ---
    def test_sigil_type(self):
        tokens = list(Tokenizer("@thread").tokenize())
        assert tokens[0].type == TokenType.SIGIL_TYPE
        assert tokens[0].value == "thread"

    def test_sigil_scope(self):
        tokens = list(Tokenizer("^always").tokenize())
        assert tokens[0].type == TokenType.SIGIL_SCOPE
        assert tokens[0].value == "always"

    def test_sigil_summary(self):
        tokens = list(Tokenizer('~"my summary"').tokenize())
        assert tokens[0].type == TokenType.SIGIL_SUMMARY
        assert tokens[0].value == "my summary"

    def test_sigil_status(self):
        tokens = list(Tokenizer("+active").tokenize())
        assert tokens[0].type == TokenType.SIGIL_STATUS
        assert tokens[0].value == "active"

    def test_sigil_files(self):
        tokens = list(Tokenizer('#["a.py" "b.py"]').tokenize())
        assert tokens[0].type == TokenType.SIGIL_FILES
        assert tokens[1].type == TokenType.LBRACKET
        assert tokens[2].type == TokenType.STRING
        assert tokens[2].value == "a.py"


class TestParser:
    """Test the S-expression parser."""

    def test_simple_expr(self):
        expr = parse_sexpr("(polip)")
        assert expr.head == "polip"
        assert expr.attrs == {}
        assert expr.items == []

    def test_with_items(self):
        expr = parse_sexpr("(polip thread my-name)")
        assert expr.head == "polip"
        assert expr.items == ["thread", "my-name"]

    def test_with_attrs(self):
        expr = parse_sexpr("(polip :scope project :v 2)")
        assert expr.head == "polip"
        assert expr.attrs["scope"] == "project"
        assert expr.attrs["v"] == 2

    def test_nested_expr(self):
        expr = parse_sexpr("(polip (files a b c))")
        assert expr.head == "polip"
        assert len(expr.items) == 1
        assert isinstance(expr.items[0], SExpr)
        assert expr.items[0].head == "files"
        assert expr.items[0].items == ["a", "b", "c"]

    def test_string_in_list(self):
        expr = parse_sexpr('(files "path/to/file.py" "another.py")')
        assert expr.head == "files"
        assert expr.items == ["path/to/file.py", "another.py"]

    def test_attr_with_nested_value(self):
        expr = parse_sexpr("(polip :decay (half-life 7))")
        assert "decay" in expr.attrs
        assert isinstance(expr.attrs["decay"], SExpr)
        assert expr.attrs["decay"].head == "half-life"

    def test_mixed_content(self):
        source = """
        (polip thread my-thread
          :scope project
          :summary "Test summary"
          (files "a.py" "b.py")
          (facts "fact one" "fact two"))
        """
        expr = parse_sexpr(source)
        assert expr.head == "polip"
        assert expr.attrs["scope"] == "project"
        assert expr.attrs["summary"] == "Test summary"
        assert len(expr.items) == 4  # thread, my-thread, files, facts


class TestPolipConversion:
    """Test conversion between S-expr and Blob."""

    def test_minimal_polip(self):
        source = '(polip thread minimal :scope project :summary "Test")'
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)

        assert blob.type == BlobType.THREAD
        assert blob.scope == BlobScope.PROJECT
        assert blob.summary == "Test"

    def test_full_polip(self):
        source = """
        (polip constraint project-rules :scope always :status active :updated "2026-01-15" :v 2
          :summary "Project constraints"
          (files "src/main.py" "tests/test.py")
          (decisions
            ("Use Python" :why "Team expertise"))
          (facts "Zero deps" "Local only")
          (next "Write tests" "Deploy")
          (related other-polip another)
          (context "Full project context here."))
        """
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)

        assert blob.type == BlobType.CONSTRAINT
        assert blob.scope == BlobScope.ALWAYS
        assert blob.status == BlobStatus.ACTIVE
        assert blob.summary == "Project constraints"
        assert blob.files == ["src/main.py", "tests/test.py"]
        assert blob.decisions == [("Use Python", "Team expertise")]
        assert blob.facts == ["Zero deps", "Local only"]
        assert blob.next_steps == ["Write tests", "Deploy"]
        assert blob.related == ["other-polip", "another"]
        assert blob.context == "Full project context here."

    def test_roundtrip(self):
        """Parse -> Blob -> S-expr -> Parse -> Blob should preserve data."""
        source = """
        (polip thread test-roundtrip :scope project :status active :updated "2026-01-15" :v 2
          :summary "Roundtrip test"
          (files "file.py")
          (facts "Important fact")
          (context "Some context"))
        """
        expr1 = parse_sexpr(source)
        blob1 = sexpr_to_blob(expr1)

        sexpr_str = blob_to_sexpr(blob1, "test-roundtrip")
        expr2 = parse_sexpr(sexpr_str)
        blob2 = sexpr_to_blob(expr2)

        assert blob1.type == blob2.type
        assert blob1.scope == blob2.scope
        assert blob1.status == blob2.status
        assert blob1.summary == blob2.summary
        assert blob1.files == blob2.files
        assert blob1.facts == blob2.facts
        assert blob1.context == blob2.context

    def test_sigil_syntax(self):
        """Test sigil sugar: @type ^scope ~summary +status #files."""
        source = """
        (polip my-polip @thread ^always ~"Sigil test" +active
          #["file.py" "other.py"]
          (facts "A fact"))
        """
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)

        assert blob.type == BlobType.THREAD
        assert blob.scope == BlobScope.ALWAYS
        assert blob.summary == "Sigil test"
        assert blob.status == BlobStatus.ACTIVE
        assert blob.files == ["file.py", "other.py"]
        assert blob.facts == ["A fact"]

    def test_sigil_minimal(self):
        """Minimal sigil syntax."""
        source = '(polip test @thread ~"Minimal")'
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)

        assert blob.type == BlobType.THREAD
        assert blob.summary == "Minimal"
        assert blob.scope == BlobScope.PROJECT  # Default


class TestBlobToSexpr:
    """Test Blob serialization to S-expression."""

    def test_minimal_blob(self):
        blob = Blob(
            type=BlobType.THREAD,
            summary="Minimal",
            scope=BlobScope.PROJECT,
        )
        output = blob_to_sexpr(blob, "minimal")

        # With delta compression: defaults (thread, project, active) are omitted
        assert "(polip minimal" in output
        assert '~"Minimal"' in output
        assert ":updated" in output

    def test_minimal_blob_no_delta(self):
        blob = Blob(
            type=BlobType.THREAD,
            summary="Minimal",
            scope=BlobScope.PROJECT,
        )
        output = blob_to_sexpr(blob, "minimal", delta=False)

        # Without delta: all attrs present
        assert "(polip minimal @thread" in output
        assert "^project" in output
        assert '~"Minimal"' in output

    def test_blob_with_multiline_context(self):
        blob = Blob(
            type=BlobType.CONTEXT,
            summary="With newlines",
            context="Line 1\nLine 2\nLine 3",
        )
        output = blob_to_sexpr(blob, "multiline")

        # Newlines should be escaped
        assert "\\n" in output
        assert "\n" in output  # But actual newlines for formatting

    def test_blob_with_quotes_in_content(self):
        blob = Blob(
            type=BlobType.FACT,
            summary='A "quoted" fact',
            facts=['Say "hello"', 'Path: C:\\Windows'],
        )
        output = blob_to_sexpr(blob, "quotes")

        assert '\\"quoted\\"' in output
        assert '\\"hello\\"' in output


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_files_list(self):
        source = "(polip thread test :summary \"Test\" (files))"
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)
        assert blob.files == []

    def test_unicode_content(self):
        source = '(polip fact unicode :summary "Unicode: \u2764\ufe0f \u2728 \ud83c\udf0a")'
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)
        assert "\u2764" in blob.summary  # Heart emoji

    def test_very_long_string(self):
        long_content = "x" * 10000
        source = f'(polip context long :summary "Long" (context "{long_content}"))'
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)
        assert len(blob.context) == 10000

    def test_deeply_nested(self):
        source = """
        (polip thread deep
          :summary "Deep nesting"
          (decisions
            ("Choice A" :why "Reason A")
            ("Choice B" :why "Reason B")
            ("Choice C" :why "Reason C")))
        """
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)
        assert len(blob.decisions) == 3

    def test_minimal_with_defaults(self):
        # With delta compression, even (polip name) works - uses defaults
        source = "(polip my-name)"
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)
        assert blob.type == BlobType.THREAD  # Default
        assert blob.scope == BlobScope.PROJECT  # Default

    def test_truly_empty_polip(self):
        # Completely empty still needs a name
        source = "(polip)"
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)
        assert blob.type == BlobType.THREAD  # Default
        # Name defaults to "unnamed"

    def test_wrong_head(self):
        source = "(blob thread test)"  # 'blob' instead of 'polip'
        expr = parse_sexpr(source)
        with pytest.raises(ValueError, match="Expected 'polip'"):
            sexpr_to_blob(expr)


class TestStringEscaping:
    """Test string escape/unescape utilities."""

    def test_escape_newline(self):
        assert _escape_string("a\nb") == "a\\nb"

    def test_escape_tab(self):
        assert _escape_string("a\tb") == "a\\tb"

    def test_escape_quote(self):
        assert _escape_string('say "hi"') == 'say \\"hi\\"'

    def test_escape_backslash(self):
        assert _escape_string("a\\b") == "a\\\\b"

    def test_unescape_newline(self):
        assert _unescape_string("a\\nb") == "a\nb"

    def test_unescape_roundtrip(self):
        original = 'Line 1\nLine 2\t"quoted"\\'
        escaped = _escape_string(original)
        unescaped = _unescape_string(escaped)
        assert unescaped == original


class TestTokenEstimation:
    """Test token count estimation."""

    def test_estimate_simple(self):
        # Simple text should be roughly 1 token per 4 chars
        tokens = estimate_tokens("hello world")
        assert 2 <= tokens <= 5

    def test_xml_has_more_tokens(self):
        xml = '<blob type="thread"><summary>Test</summary></blob>'
        lisp = '(polip thread test :summary "Test")'

        xml_tokens = estimate_tokens(xml)
        lisp_tokens = estimate_tokens(lisp)

        # XML should have more tokens due to < > / = ceremony
        assert xml_tokens > lisp_tokens


class TestFormatComparison:
    """Test XML vs S-expr comparison."""

    def test_compare_simple_blob(self):
        blob = Blob(
            type=BlobType.THREAD,
            summary="Test blob",
            scope=BlobScope.PROJECT,
            status=BlobStatus.ACTIVE,
        )
        comparison = compare_formats(blob, "test")

        # S-expr should be smaller
        assert comparison["sexpr_chars"] < comparison["xml_chars"]
        assert "%" in comparison["char_reduction"]
        assert "%" in comparison["token_reduction"]

    def test_compare_complex_blob(self):
        blob = Blob(
            type=BlobType.THREAD,
            summary="Complex thread with lots of content",
            scope=BlobScope.PROJECT,
            status=BlobStatus.ACTIVE,
            files=["file1.py", "file2.py", "file3.py"],
            decisions=[
                ("Decision 1", "Reason 1"),
                ("Decision 2", "Reason 2"),
            ],
            facts=["Fact 1", "Fact 2", "Fact 3"],
            next_steps=["Step 1", "Step 2"],
            context="This is a longer context that has multiple sentences. "
                   "It describes the background of the thread and provides "
                   "important information for understanding the decisions.",
        )
        comparison = compare_formats(blob, "complex")

        # For complex content, S-expr savings should be significant
        # Extract percentage as float
        reduction = float(comparison["char_reduction"].rstrip("%"))
        assert reduction > 20  # At least 20% smaller


class TestRealWorldExamples:
    """Test with real-world polip examples."""

    def test_constraint_polip(self):
        source = """
        (polip constraint project-rules :scope always :updated "2026-01-13" :v 2
          :summary "reef project constraints"
          (facts
            "Use uv for package management, not pip"
            "Run tests with: uv run pytest"
            "Local-only package - not published to PyPI"
            "Zero dependencies - stdlib only")
          (context "reef is symbiotic memory for AI - XML polips that persist across sessions.
Coral terminology: polip (blob), reef (glob), current (thread), bedrock (constraint).
A reef is a collection of polips in .claude/ directories."))
        """
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)

        assert blob.type == BlobType.CONSTRAINT
        assert blob.scope == BlobScope.ALWAYS
        assert len(blob.facts) == 4
        assert "reef is symbiotic memory" in blob.context

    def test_thread_with_decisions(self):
        source = """
        (polip thread feature-design :scope project :status active :updated "2026-01-15" :v 2
          :summary "Feature X Design Thread"
          (files
            "src/feature.py"
            "tests/test_feature.py")
          (decisions
            ("Use S-expressions" :why "60% token reduction")
            ("Decay protocol" :why "Memory IS forgetting")
            ("No external deps" :why "Stdlib-only constraint"))
          (next
            "Implement parser"
            "Write tests"
            "Update docs")
          (related constraints-project-rules))
        """
        expr = parse_sexpr(source)
        blob = sexpr_to_blob(expr)

        assert blob.type == BlobType.THREAD
        assert blob.status == BlobStatus.ACTIVE
        assert len(blob.files) == 2
        assert len(blob.decisions) == 3
        assert len(blob.next_steps) == 3
        assert "constraints-project-rules" in blob.related
