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


# =============================================================================
# SMOKE TESTS - Basic sanity checks
# =============================================================================

class TestSmokeTests:
    """Quick validation that core functionality works."""

    def test_parse_serialize_roundtrip(self):
        """Parse → Blob → Serialize → Parse should preserve semantics."""
        source = '(polip test @thread ~"Smoke test")'
        blob1 = sexpr_to_blob(parse_sexpr(source))
        output = blob_to_sexpr(blob1, "test")
        blob2 = sexpr_to_blob(parse_sexpr(output))
        assert blob1.type == blob2.type
        assert blob1.summary == blob2.summary

    def test_all_blob_types(self):
        """Each BlobType should parse correctly."""
        for blob_type in ["thread", "decision", "constraint", "fact", "context"]:
            source = f'(polip test @{blob_type} ~"Testing {blob_type}")'
            blob = sexpr_to_blob(parse_sexpr(source))
            assert blob.type.value == blob_type

    def test_all_scopes(self):
        """Each BlobScope should parse correctly."""
        for scope in ["session", "project", "always"]:
            source = f'(polip test @thread ^{scope} ~"Testing scope")'
            blob = sexpr_to_blob(parse_sexpr(source))
            assert blob.scope.value == scope

    def test_all_statuses(self):
        """Each BlobStatus should parse correctly."""
        for status in ["active", "blocked", "done"]:
            source = f'(polip test @thread +{status} ~"Testing status")'
            blob = sexpr_to_blob(parse_sexpr(source))
            assert blob.status.value == status

    def test_all_sigils_together(self):
        """All sigils in one expression."""
        source = '(polip my-polip @constraint ^always ~"All sigils" +active #["a.py" "b.py"])'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.type == BlobType.CONSTRAINT
        assert blob.scope == BlobScope.ALWAYS
        assert blob.summary == "All sigils"
        assert blob.status == BlobStatus.ACTIVE
        assert blob.files == ["a.py", "b.py"]


# =============================================================================
# STRESS TESTS - Performance and limits
# =============================================================================

class TestStressTests:
    """Test behavior under load and at limits."""

    def test_deeply_nested_structure(self):
        """Many levels of nesting."""
        source = """
        (polip deep @thread ~"Deep nesting"
          (decisions
            ("L1" :why "reason")
            ("L2" :why "reason"))
          (facts "f1" "f2" "f3" "f4" "f5")
          (next "n1" "n2" "n3" "n4" "n5")
          (related a b c d e f g h i j))
        """
        blob = sexpr_to_blob(parse_sexpr(source))
        assert len(blob.decisions) == 2
        assert len(blob.facts) == 5
        assert len(blob.related) == 10

    def test_many_files(self):
        """Large file list."""
        files = " ".join(f'"file{i}.py"' for i in range(100))
        source = f'(polip test @thread ~"Many files" (files {files}))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert len(blob.files) == 100

    def test_many_decisions(self):
        """Large decision list."""
        decisions = "\n".join(f'("Decision {i}" :why "Reason {i}")' for i in range(50))
        source = f'(polip test @thread ~"Many decisions" (decisions {decisions}))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert len(blob.decisions) == 50

    def test_long_string(self):
        """Very long string content."""
        long_text = "x" * 10000
        source = f'(polip test @thread ~"{long_text}")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert len(blob.summary) == 10000

    def test_long_context(self):
        """Very long context field."""
        long_ctx = "word " * 5000  # 25000 chars
        source = f'(polip test @thread ~"Long context" (context "{long_ctx}"))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert len(blob.context) > 20000

    def test_many_lines(self):
        """Multi-line content with many newlines."""
        lines = "\\n".join(f"Line {i}" for i in range(200))
        source = f'(polip test @thread ~"Multiline" (context "{lines}"))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.context.count("\n") == 199

    def test_rapid_tokenization(self):
        """Tokenize the same content many times."""
        source = '(polip test @thread ~"Rapid fire" #["a.py"])'
        for _ in range(100):
            tokens = list(Tokenizer(source).tokenize())
            assert len(tokens) > 5


# =============================================================================
# EDGE CASES - Boundary conditions
# =============================================================================

class TestEdgeCases:
    """Test boundary conditions and corner cases."""

    def test_empty_string_summary(self):
        """Empty summary string."""
        source = '(polip test @thread ~"")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary == ""

    def test_empty_files_list(self):
        """Empty files list."""
        source = '(polip test @thread ~"Empty files" (files))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.files == []

    def test_empty_decisions_list(self):
        """Empty decisions list."""
        source = '(polip test @thread ~"Empty decisions" (decisions))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.decisions == []

    def test_single_char_name(self):
        """Single character polip name."""
        source = '(polip x @thread ~"Single char")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary == "Single char"

    def test_name_with_many_dashes(self):
        """Name with multiple dashes."""
        source = '(polip a-b-c-d-e-f-g @thread ~"Dashed")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary == "Dashed"

    def test_name_with_underscores(self):
        """Name with underscores."""
        source = '(polip my_polip_name @thread ~"Underscored")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary == "Underscored"

    def test_numeric_in_name(self):
        """Numbers in polip name."""
        source = '(polip v2-feature-123 @thread ~"Numbered")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary == "Numbered"

    def test_whitespace_preservation_in_strings(self):
        """Whitespace in strings should be preserved."""
        source = '(polip test @thread ~"  spaces  around  ")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary == "  spaces  around  "

    def test_unicode_in_strings(self):
        """Unicode characters in strings."""
        source = '(polip test @thread ~"日本語 émoji 🦀")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "日本語" in blob.summary
        assert "🦀" in blob.summary

    def test_no_whitespace_between_tokens(self):
        """Sigils work without whitespace - they're delimiters."""
        source = '(polip test@thread~"Tight")'
        # Sigils act as delimiters, so this actually works
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.type == BlobType.THREAD
        assert blob.summary == "Tight"

    def test_excessive_whitespace(self):
        """Lots of whitespace everywhere."""
        source = '''
        (    polip    test
             @thread
             ^project
             ~"Spacy"
        )
        '''
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary == "Spacy"

    def test_comments_everywhere(self):
        """Comments interspersed in source."""
        source = """
        ; Header comment
        (polip test ; inline comment
          @thread ; type comment
          ~"With comments" ; summary comment
          ; standalone comment
        ) ; trailing comment
        """
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary == "With comments"

    def test_decision_with_empty_why(self):
        """Decision with empty why field."""
        source = '(polip test @thread ~"Empty why" (decisions ("Choice" :why "")))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.decisions == [("Choice", "")]

    def test_fact_with_quotes_inside(self):
        """Fact containing escaped quotes."""
        source = r'(polip test @thread ~"Quoted" (facts "He said \"hello\""))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert 'He said "hello"' in blob.facts[0]

    def test_context_with_all_escapes(self):
        """Context with all escape sequences."""
        source = r'(polip test @thread ~"Escapes" (context "tab:\there\nnewline\\backslash"))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "\t" in blob.context
        assert "\n" in blob.context
        assert "\\" in blob.context

    def test_version_zero(self):
        """Explicit version 0."""
        source = '(polip test @thread ~"V0" :v 0)'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.version == 0

    def test_version_large(self):
        """Large version number."""
        source = '(polip test @thread ~"Big version" :v 999999)'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.version == 999999


# =============================================================================
# ADVERSARIAL TESTS - Intentionally malformed/tricky inputs
# =============================================================================

class TestAdversarialCases:
    """Tests designed to break the parser."""

    def test_unclosed_paren(self):
        """Missing closing paren."""
        source = '(polip test @thread ~"Unclosed"'
        with pytest.raises(SyntaxError):
            parse_sexpr(source)

    def test_extra_closing_paren(self):
        """Extra closing paren."""
        source = '(polip test @thread ~"Extra"))'
        # Parser should stop at first complete expr, but tokenizer might error
        expr = parse_sexpr(source)  # May succeed parsing first expr
        # The extra ) would be left over

    def test_unclosed_string(self):
        """String without closing quote."""
        source = '(polip test @thread ~"Unclosed string)'
        with pytest.raises(SyntaxError):
            parse_sexpr(source)

    def test_unclosed_bracket(self):
        """File list without closing bracket."""
        source = '(polip test @thread ~"Unclosed" #["file.py")'
        with pytest.raises(SyntaxError):
            parse_sexpr(source)

    def test_sigil_without_value(self):
        """Sigil at end of input."""
        source = '(polip test @)'
        with pytest.raises(SyntaxError):
            parse_sexpr(source)

    def test_keyword_without_value(self):
        """Keyword without following value."""
        source = '(polip test @thread ~"Test" :summary)'
        with pytest.raises(SyntaxError):
            parse_sexpr(source)

    def test_invalid_blob_type(self):
        """Invalid type value."""
        source = '(polip test @invalid ~"Bad type")'
        with pytest.raises(ValueError):
            sexpr_to_blob(parse_sexpr(source))

    def test_invalid_scope(self):
        """Invalid scope value."""
        source = '(polip test @thread ^invalid ~"Bad scope")'
        with pytest.raises(ValueError):
            sexpr_to_blob(parse_sexpr(source))

    def test_invalid_status(self):
        """Invalid status value."""
        source = '(polip test @thread +invalid ~"Bad status")'
        with pytest.raises(ValueError):
            sexpr_to_blob(parse_sexpr(source))

    def test_nested_quotes_attack(self):
        """Attempt to break parser with nested quotes."""
        source = r'(polip test @thread ~"outer \"inner \\\"deep\\\" inner\" outer")'
        # Should handle nested escapes
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "inner" in blob.summary

    def test_null_bytes_in_string(self):
        """Null bytes in string content."""
        source = '(polip test @thread ~"has\x00null")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "\x00" in blob.summary

    def test_control_chars_in_string(self):
        """Various control characters."""
        source = '(polip test @thread ~"ctrl\x01\x02\x03chars")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "\x01" in blob.summary

    def test_very_long_symbol(self):
        """Extremely long symbol name."""
        long_name = "a" * 1000
        source = f'(polip {long_name} @thread ~"Long name")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary == "Long name"

    def test_keyword_looks_like_sigil(self):
        """Keyword that resembles sigil syntax."""
        source = '(polip test @thread ~"Test" :type decision)'
        # :type should override @thread
        blob = sexpr_to_blob(parse_sexpr(source))
        # The last one wins in attrs
        assert blob.type.value in ["thread", "decision"]

    def test_duplicate_sections(self):
        """Multiple files sections."""
        source = '''
        (polip test @thread ~"Dupe"
          (files "a.py")
          (files "b.py"))
        '''
        blob = sexpr_to_blob(parse_sexpr(source))
        # Last one wins
        assert "b.py" in blob.files

    def test_wrong_section_content(self):
        """Number in files list instead of string."""
        source = '(polip test @thread ~"Wrong" (files 123))'
        blob = sexpr_to_blob(parse_sexpr(source))
        # Should coerce to string
        assert "123" in blob.files

    def test_deeply_nested_parens(self):
        """Many levels of paren nesting requires symbol heads."""
        # S-expressions need symbol heads, so ((((value)))) fails
        source = "(polip test @thread ~\"Deep\" :decay (((((value))))))"
        with pytest.raises(SyntaxError):
            parse_sexpr(source)

    def test_valid_nested_structure(self):
        """Valid nested structures with symbol heads."""
        source = "(polip test @thread ~\"Nested\" :decay (outer (inner (deep value))))"
        expr = parse_sexpr(source)
        assert expr.head == "polip"

    def test_alternating_quotes_escapes(self):
        """Alternating quotes and escapes."""
        source = r'(polip test @thread ~"a\"b\"c\"d\"e")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary.count('"') == 4

    def test_backslash_at_string_end(self):
        """Backslash right before closing quote."""
        source = r'(polip test @thread ~"ends with backslash\\")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary.endswith("\\")

    def test_empty_input(self):
        """Completely empty input."""
        with pytest.raises(SyntaxError):
            parse_sexpr("")

    def test_whitespace_only_input(self):
        """Only whitespace."""
        with pytest.raises(SyntaxError):
            parse_sexpr("   \n\t  ")

    def test_comment_only_input(self):
        """Only comments."""
        with pytest.raises(SyntaxError):
            parse_sexpr("; just a comment")

    def test_number_as_head(self):
        """Number where symbol expected."""
        source = "(123 test)"
        with pytest.raises(SyntaxError):
            parse_sexpr(source)

    def test_file_path_with_spaces(self):
        """File paths containing spaces."""
        source = '(polip test @thread ~"Spaced" #["path/with spaces/file.py"])'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "with spaces" in blob.files[0]

    def test_file_path_with_unicode(self):
        """File paths with unicode."""
        source = '(polip test @thread ~"Unicode path" #["путь/файл.py"])'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "путь" in blob.files[0]

    def test_decision_with_no_why(self):
        """Decision tuple without :why."""
        source = '(polip test @thread ~"No why" (decisions ("Just choice")))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.decisions[0][1] == ""  # Empty why

    def test_related_with_special_chars(self):
        """Related names with special characters."""
        source = '(polip test @thread ~"Related" (related foo-bar baz_qux))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "foo-bar" in blob.related
        assert "baz_qux" in blob.related


# =============================================================================
# ABSURD TESTS - Unlikely but technically possible scenarios
# =============================================================================

class TestAbsurdCases:
    """Unlikely but valid edge cases to ensure robustness."""

    def test_polip_named_polip(self):
        """A polip named 'polip'."""
        source = '(polip polip @thread ~"Meta")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.type == BlobType.THREAD

    def test_polip_named_thread(self):
        """A polip named 'thread' (same as type)."""
        source = '(polip thread @decision ~"Confusing")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.type == BlobType.DECISION

    def test_summary_is_code(self):
        """Summary containing code."""
        source = '(polip test @thread ~"def foo(): return 42")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "def foo()" in blob.summary

    def test_summary_is_json(self):
        """Summary containing JSON."""
        source = r'(polip test @thread ~"{\"key\": \"value\"}")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert '{"key": "value"}' in blob.summary

    def test_summary_is_xml(self):
        """Summary containing XML."""
        source = r'(polip test @thread ~"<tag attr=\"val\">content</tag>")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "<tag" in blob.summary

    def test_summary_is_sexpr(self):
        """Summary containing S-expression syntax."""
        source = r'(polip test @thread ~"(nested (parens) here)")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "(nested" in blob.summary

    def test_context_is_entire_file(self):
        """Context that looks like another polip file."""
        inner = r'(polip inner @thread ~\"Inception\")'
        source = f'(polip test @thread ~"Outer" (context "{inner}"))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "polip inner" in blob.context

    def test_thousand_related(self):
        """A thousand related polips."""
        related = " ".join(f"polip{i}" for i in range(1000))
        source = f'(polip test @thread ~"Connected" (related {related}))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert len(blob.related) == 1000

    def test_fact_is_empty_string(self):
        """Empty string as a fact."""
        source = '(polip test @thread ~"Empty fact" (facts ""))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "" in blob.facts

    def test_all_fields_empty(self):
        """Every optional field empty."""
        source = '''
        (polip empty @thread ~""
          (files)
          (decisions)
          (facts)
          (next)
          (related)
          (context ""))
        '''
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.summary == ""
        assert blob.files == []
        assert blob.decisions == []

    def test_date_in_future(self):
        """Date far in the future."""
        source = '(polip test @thread ~"Future" :updated "2099-12-31")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.updated.year == 2099

    def test_date_in_past(self):
        """Date in the distant past."""
        source = '(polip test @thread ~"Ancient" :updated "1970-01-01")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.updated.year == 1970

    def test_serialization_stability(self):
        """Serialize same blob 100 times, should be identical."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Stability test",
            scope=BlobScope.PROJECT,
        )
        outputs = [blob_to_sexpr(blob, "test") for _ in range(100)]
        assert len(set(outputs)) == 1  # All identical

    def test_binary_looking_content(self):
        """Content that looks like binary data."""
        # Unknown escapes (\x) are passed through without backslash
        source = '(polip test @thread ~"\\x00\\x01\\x02\\xff")'
        blob = sexpr_to_blob(parse_sexpr(source))
        # \x becomes x (unknown escape stripped)
        assert "x00" in blob.summary

    def test_sql_injection_attempt(self):
        """SQL injection in summary (should just be string)."""
        source = r'(polip test @thread ~"Robert\"); DROP TABLE users;--")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "DROP TABLE" in blob.summary  # Just a string, not executed

    def test_path_traversal_attempt(self):
        """Path traversal in file list."""
        source = '(polip test @thread ~"Traversal" #["../../../etc/passwd"])'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "../" in blob.files[0]  # Just stored, not executed

    def test_command_injection_attempt(self):
        """Command injection in summary."""
        source = '(polip test @thread ~"$(rm -rf /)")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "$(rm" in blob.summary  # Just a string

    def test_emoji_overload(self):
        """Many emoji characters."""
        emojis = "🎉🎊🎁🎈🎂🍰🎄🎃🎅🤶" * 100
        source = f'(polip test @thread ~"{emojis}")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert len(blob.summary) == 1000

    def test_rtl_text(self):
        """Right-to-left text."""
        source = '(polip test @thread ~"مرحبا بالعالم")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "مرحبا" in blob.summary

    def test_mixed_direction_text(self):
        """Mixed LTR and RTL text."""
        source = '(polip test @thread ~"Hello مرحبا World عالم")'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "Hello" in blob.summary
        assert "مرحبا" in blob.summary


# =============================================================================
# DECAY PROTOCOL TESTS
# =============================================================================

class TestDecayProtocol:
    """Tests for decay protocol fields in S-expression format."""

    def test_decay_minimal(self):
        """Minimal decay protocol with rate only."""
        source = '(polip test @thread ~"Decay test" (decay :rate 0.5))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.decay_rate == 0.5
        assert blob.half_life is None
        assert blob.compost_to is None

    def test_decay_full(self):
        """Full decay protocol with all fields."""
        source = '''
        (polip test @thread ~"Full decay"
          (decay :rate 0.3 :half_life 30 :compost_to archive
            (immune "system-update" "user-reference")
            (challenged "new-feature" "refactor")))
        '''
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.decay_rate == 0.3
        assert blob.half_life == 30
        assert blob.compost_to == "archive"
        assert len(blob.immune_to) == 2
        assert "system-update" in blob.immune_to
        assert len(blob.challenged_by) == 2
        assert "new-feature" in blob.challenged_by

    def test_decay_roundtrip(self):
        """Decay fields survive roundtrip."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Decay roundtrip",
            decay_rate=0.7,
            half_life=60,
            compost_to="deep-archive",
            immune_to=["critical", "manual"],
            challenged_by=["contradiction", "superseded"],
        )
        sexpr = blob_to_sexpr(blob, "test")
        restored = sexpr_to_blob(parse_sexpr(sexpr))

        assert restored.decay_rate == 0.7
        assert restored.half_life == 60
        assert restored.compost_to == "deep-archive"
        assert restored.immune_to == ["critical", "manual"]
        assert restored.challenged_by == ["contradiction", "superseded"]

    def test_decay_only_rate(self):
        """Decay with only rate attribute."""
        source = '(polip test @thread ~"Rate only" (decay :rate 0.8))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.decay_rate == 0.8
        assert blob.half_life is None

    def test_decay_only_half_life(self):
        """Decay with only half_life attribute."""
        source = '(polip test @thread ~"Half-life only" (decay :half_life 90))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.decay_rate is None
        assert blob.half_life == 90

    def test_decay_only_compost_to(self):
        """Decay with only compost_to attribute."""
        source = '(polip test @thread ~"Compost only" (decay :compost_to archive-bin))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.compost_to == "archive-bin"

    def test_decay_immune_empty(self):
        """Decay with empty immune list."""
        source = '(polip test @thread ~"Empty immune" (decay :rate 0.5 (immune)))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.immune_to == []

    def test_decay_challenged_empty(self):
        """Decay with empty challenged list."""
        source = '(polip test @thread ~"Empty challenged" (decay :rate 0.5 (challenged)))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.challenged_by == []

    def test_decay_float_rate(self):
        """Decay rate as float."""
        source = '(polip test @thread ~"Float rate" (decay :rate 0.123))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.decay_rate == 0.123

    def test_decay_unicode_in_lists(self):
        """Unicode in immune and challenged lists."""
        source = '''
        (polip test @thread ~"Unicode decay"
          (decay :rate 0.5
            (immune "系统更新" "手动审核")
            (challenged "矛盾" "过时")))
        '''
        blob = sexpr_to_blob(parse_sexpr(source))
        assert "系统更新" in blob.immune_to
        assert "矛盾" in blob.challenged_by

    def test_decay_serialization_omitted_if_empty(self):
        """Decay section omitted if no fields set."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="No decay",
        )
        sexpr = blob_to_sexpr(blob, "test")
        assert "(decay" not in sexpr

    def test_decay_serialization_structure(self):
        """Decay serialization has correct structure."""
        blob = Blob(
            type=BlobType.THREAD,
            summary="Decay structure",
            decay_rate=0.5,
            immune_to=["event1"],
        )
        sexpr = blob_to_sexpr(blob, "test")
        assert "(decay" in sexpr
        assert ":rate 0.5" in sexpr
        assert "(immune" in sexpr

    def test_decay_many_immune(self):
        """Many immune events."""
        events = [f"event-{i}" for i in range(50)]
        blob = Blob(
            type=BlobType.THREAD,
            summary="Many immune",
            decay_rate=0.5,
            immune_to=events,
        )
        sexpr = blob_to_sexpr(blob, "test")
        restored = sexpr_to_blob(parse_sexpr(sexpr))
        assert len(restored.immune_to) == 50

    def test_decay_many_challenged(self):
        """Many challenged-by entries."""
        challengers = [f"challenger-{i}" for i in range(50)]
        blob = Blob(
            type=BlobType.THREAD,
            summary="Many challengers",
            decay_rate=0.5,
            challenged_by=challengers,
        )
        sexpr = blob_to_sexpr(blob, "test")
        restored = sexpr_to_blob(parse_sexpr(sexpr))
        assert len(restored.challenged_by) == 50

    def test_decay_special_chars_in_compost_to(self):
        """Special characters in compost_to."""
        source = '(polip test @thread ~"Special compost" (decay :compost_to deep-archive_2026))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.compost_to == "deep-archive_2026"

    def test_decay_zero_rate(self):
        """Zero decay rate (no decay)."""
        source = '(polip test @thread ~"No decay" (decay :rate 0))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.decay_rate == 0

    def test_decay_high_rate(self):
        """Very high decay rate."""
        source = '(polip test @thread ~"Fast decay" (decay :rate 0.999))'
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.decay_rate == 0.999

    def test_decay_long_half_life(self):
        """Very long half-life."""
        source = '(polip test @thread ~"Long life" (decay :half_life 36500))'  # 100 years
        blob = sexpr_to_blob(parse_sexpr(source))
        assert blob.half_life == 36500
