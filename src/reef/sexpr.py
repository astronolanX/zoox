"""
S-Expression Parser and Serializer for Polips.

AI-native file format - minimal syntax, maximum semantic density.
Replaces XML with ~40% token reduction (validated by investigation squad).

Grammar:
    polip      ::= '(' 'polip' name? type-sigil? scope-sigil? attrs* content* ')'
    type-sigil ::= '@' (thread | decision | constraint | fact | context)
    scope-sigil::= '^' (always | project | session)
    attrs      ::= ':' keyword value
    content    ::= files | decisions | facts | next | related | ctx | decay | vitals

Sigil Sugar:
    @thread     → :type thread
    ^always     → :scope always
    ~"text"     → :summary "text"
    +active     → :status active
    #["a" "b"]  → (files "a" "b")

Delta-from-default:
    Canonical defaults are omitted in output to minimize tokens.
    - type: thread
    - scope: project
    - status: active (for threads)
    - version: 2
"""

# --- Canonical Defaults (for delta compression) ---
DEFAULTS = {
    "type": "thread",
    "scope": "project",
    "status": "active",
    "version": 2,
}

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Iterator
from enum import Enum


# --- Tokenizer ---

class TokenType(Enum):
    LPAREN = "("
    RPAREN = ")"
    LBRACKET = "["
    RBRACKET = "]"
    KEYWORD = ":"      # :scope, :status, etc.
    SYMBOL = "symbol"  # thread, my-polip, etc.
    STRING = "string"  # "quoted text"
    NUMBER = "number"  # 42, 3.14
    # Sigil sugar tokens
    SIGIL_TYPE = "@"      # @thread → :type thread
    SIGIL_SCOPE = "^"     # ^always → :scope always
    SIGIL_SUMMARY = "~"   # ~"text" → :summary "text"
    SIGIL_STATUS = "+"    # +active → :status active
    SIGIL_FILES = "#"     # #["a.py"] → (files "a.py")
    EOF = "eof"


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    col: int


class Tokenizer:
    """Tokenize S-expression input into tokens."""

    # Symbol: starts with letter/underscore/dash, continues with alphanumeric/dash/underscore
    SYMBOL_START = re.compile(r'[a-zA-Z_-]')
    SYMBOL_CONT = re.compile(r'[a-zA-Z0-9_-]')

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1

    def _peek(self, offset: int = 0) -> str:
        pos = self.pos + offset
        if pos >= len(self.source):
            return ""
        return self.source[pos]

    def _advance(self) -> str:
        ch = self._peek()
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_whitespace_and_comments(self):
        while self.pos < len(self.source):
            ch = self._peek()
            if ch in " \t\n\r":
                self._advance()
            elif ch == ";":
                # Comment: skip to end of line
                while self._peek() and self._peek() != "\n":
                    self._advance()
            else:
                break

    def _read_string(self) -> str:
        """Read a quoted string, handling escapes."""
        self._advance()  # consume opening "
        result = []

        while True:
            ch = self._peek()
            if not ch:
                raise SyntaxError(f"Unterminated string at line {self.line}, col {self.col}")

            if ch == '"':
                self._advance()  # consume closing "
                break
            elif ch == '\\':
                self._advance()  # consume backslash
                escape = self._advance()
                if escape == 'n':
                    result.append('\n')
                elif escape == 't':
                    result.append('\t')
                elif escape == '\\':
                    result.append('\\')
                elif escape == '"':
                    result.append('"')
                else:
                    result.append(escape)  # Unknown escape, keep as-is
            else:
                result.append(self._advance())

        return "".join(result)

    def _read_symbol(self) -> str:
        """Read a symbol (identifier)."""
        result = []
        while self.SYMBOL_CONT.match(self._peek()):
            result.append(self._advance())
        return "".join(result)

    def _read_number(self) -> float | int:
        """Read a number (int or float)."""
        result = []
        while self._peek().isdigit() or self._peek() == '.':
            result.append(self._advance())
        num_str = "".join(result)
        if '.' in num_str:
            return float(num_str)
        return int(num_str)

    def tokenize(self) -> Iterator[Token]:
        """Generate tokens from source."""
        while self.pos < len(self.source):
            self._skip_whitespace_and_comments()

            if self.pos >= len(self.source):
                break

            line, col = self.line, self.col
            ch = self._peek()

            if ch == '(':
                self._advance()
                yield Token(TokenType.LPAREN, '(', line, col)
            elif ch == ')':
                self._advance()
                yield Token(TokenType.RPAREN, ')', line, col)
            elif ch == '[':
                self._advance()
                yield Token(TokenType.LBRACKET, '[', line, col)
            elif ch == ']':
                self._advance()
                yield Token(TokenType.RBRACKET, ']', line, col)
            elif ch == ':':
                self._advance()
                # Keyword: :name -> we return the name without colon
                if self.SYMBOL_START.match(self._peek()):
                    name = self._read_symbol()
                    yield Token(TokenType.KEYWORD, name, line, col)
                else:
                    raise SyntaxError(f"Expected symbol after ':' at line {line}, col {col}")
            # --- Sigil sugar ---
            elif ch == '@':
                self._advance()
                if self.SYMBOL_START.match(self._peek()):
                    sym = self._read_symbol()
                    yield Token(TokenType.SIGIL_TYPE, sym, line, col)
                else:
                    raise SyntaxError(f"Expected symbol after '@' at line {line}, col {col}")
            elif ch == '^':
                self._advance()
                if self.SYMBOL_START.match(self._peek()):
                    sym = self._read_symbol()
                    yield Token(TokenType.SIGIL_SCOPE, sym, line, col)
                else:
                    raise SyntaxError(f"Expected symbol after '^' at line {line}, col {col}")
            elif ch == '~':
                self._advance()
                if self._peek() == '"':
                    s = self._read_string()
                    yield Token(TokenType.SIGIL_SUMMARY, s, line, col)
                else:
                    raise SyntaxError(f"Expected string after '~' at line {line}, col {col}")
            elif ch == '+':
                self._advance()
                if self.SYMBOL_START.match(self._peek()):
                    sym = self._read_symbol()
                    yield Token(TokenType.SIGIL_STATUS, sym, line, col)
                else:
                    # Not a sigil, might be part of something else - error
                    raise SyntaxError(f"Expected symbol after '+' at line {line}, col {col}")
            elif ch == '#':
                self._advance()
                yield Token(TokenType.SIGIL_FILES, '#', line, col)
            elif ch == '"':
                s = self._read_string()
                yield Token(TokenType.STRING, s, line, col)
            elif ch.isdigit() or (ch == '-' and self._peek(1).isdigit()):
                num = self._read_number()
                yield Token(TokenType.NUMBER, num, line, col)
            elif self.SYMBOL_START.match(ch):
                sym = self._read_symbol()
                yield Token(TokenType.SYMBOL, sym, line, col)
            else:
                raise SyntaxError(f"Unexpected character '{ch}' at line {line}, col {col}")

        yield Token(TokenType.EOF, None, self.line, self.col)


# --- Parser ---

@dataclass
class SExpr:
    """Parsed S-expression node."""
    head: str  # First symbol (e.g., 'polip', 'files', 'decisions')
    attrs: dict = field(default_factory=dict)  # :key value pairs
    items: list = field(default_factory=list)  # Child expressions or primitives


class Parser:
    """Parse tokens into S-expression AST."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token:
        if self.pos >= len(self.tokens):
            return Token(TokenType.EOF, None, 0, 0)
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self._peek()
        self.pos += 1
        return tok

    def _expect(self, ttype: TokenType) -> Token:
        tok = self._advance()
        if tok.type != ttype:
            raise SyntaxError(f"Expected {ttype.value}, got {tok.type.value} at line {tok.line}")
        return tok

    def parse(self) -> SExpr:
        """Parse a single S-expression."""
        self._expect(TokenType.LPAREN)

        # Head: can be symbol or string (for decision tuples like ("choice" :why "reason"))
        head_tok = self._peek()
        if head_tok.type == TokenType.SYMBOL:
            self._advance()
            expr = SExpr(head=head_tok.value)
        elif head_tok.type == TokenType.STRING:
            # String-headed list (anonymous tuple)
            self._advance()
            expr = SExpr(head="_tuple")
            expr.items.append(head_tok.value)
        else:
            raise SyntaxError(f"Expected symbol or string, got {head_tok.type.value} at line {head_tok.line}")

        # Parse attributes and items until closing paren
        while self._peek().type != TokenType.RPAREN:
            tok = self._peek()

            if tok.type == TokenType.KEYWORD:
                # :key value
                key = self._advance().value
                val_tok = self._advance()
                if val_tok.type == TokenType.STRING:
                    expr.attrs[key] = val_tok.value
                elif val_tok.type == TokenType.SYMBOL:
                    expr.attrs[key] = val_tok.value
                elif val_tok.type == TokenType.NUMBER:
                    expr.attrs[key] = val_tok.value
                elif val_tok.type == TokenType.LPAREN:
                    # Inline list for keyword value
                    self.pos -= 1  # back up
                    expr.attrs[key] = self.parse()
                else:
                    raise SyntaxError(f"Unexpected token after keyword at line {val_tok.line}")

            # --- Sigil sugar handling ---
            elif tok.type == TokenType.SIGIL_TYPE:
                # @thread → type: thread
                expr.attrs["type"] = self._advance().value

            elif tok.type == TokenType.SIGIL_SCOPE:
                # ^always → scope: always
                expr.attrs["scope"] = self._advance().value

            elif tok.type == TokenType.SIGIL_SUMMARY:
                # ~"text" → summary: "text"
                expr.attrs["summary"] = self._advance().value

            elif tok.type == TokenType.SIGIL_STATUS:
                # +active → status: active
                expr.attrs["status"] = self._advance().value

            elif tok.type == TokenType.SIGIL_FILES:
                # #["a.py" "b.py"] → (files "a.py" "b.py")
                self._advance()  # consume #
                files_expr = SExpr(head="files")
                if self._peek().type == TokenType.LBRACKET:
                    self._advance()  # consume [
                    while self._peek().type != TokenType.RBRACKET:
                        if self._peek().type == TokenType.STRING:
                            files_expr.items.append(self._advance().value)
                        elif self._peek().type == TokenType.EOF:
                            raise SyntaxError("Unterminated file list")
                        else:
                            raise SyntaxError(f"Expected string in file list at line {self._peek().line}")
                    self._advance()  # consume ]
                else:
                    raise SyntaxError(f"Expected '[' after '#' at line {self._peek().line}")
                expr.items.append(files_expr)

            elif tok.type == TokenType.LPAREN:
                # Nested S-expression
                expr.items.append(self.parse())

            elif tok.type == TokenType.STRING:
                expr.items.append(self._advance().value)

            elif tok.type == TokenType.SYMBOL:
                expr.items.append(self._advance().value)

            elif tok.type == TokenType.NUMBER:
                expr.items.append(self._advance().value)

            elif tok.type == TokenType.EOF:
                raise SyntaxError("Unexpected end of input")

            else:
                raise SyntaxError(f"Unexpected token {tok.type.value} at line {tok.line}")

        self._expect(TokenType.RPAREN)
        return expr


def parse_sexpr(source: str) -> SExpr:
    """Parse S-expression source string."""
    tokenizer = Tokenizer(source)
    tokens = list(tokenizer.tokenize())
    parser = Parser(tokens)
    return parser.parse()


# --- Polip Conversion ---

# Import from blob module (avoid circular import by importing at use)
def sexpr_to_blob(sexpr: SExpr):
    """Convert parsed S-expression to Blob object.

    Supports two syntaxes:
    1. Legacy: (polip thread my-name :scope project ...)
    2. Sigil:  (polip my-name @thread ^project ...)

    With sigils, type/scope/status come from attrs instead of items.
    """
    from .blob import Blob, BlobType, BlobScope, BlobStatus

    if sexpr.head != "polip":
        raise ValueError(f"Expected 'polip', got '{sexpr.head}'")

    # Determine type - sigil style (attrs), legacy (items[0]), or default
    if "type" in sexpr.attrs:
        # Sigil style: @thread sets attrs["type"]
        type_str = sexpr.attrs["type"]
        # Name is items[0] if present
        name = sexpr.items[0] if sexpr.items else "unnamed"
        content_start = 1
    elif sexpr.items and sexpr.items[0] in ("thread", "decision", "constraint", "fact", "context"):
        # Legacy style: items[0] is type, items[1] is name
        type_str = sexpr.items[0]
        name = sexpr.items[1] if len(sexpr.items) > 1 else "unnamed"
        content_start = 2
    else:
        # Delta compression: type omitted, use default
        type_str = DEFAULTS["type"]
        name = sexpr.items[0] if sexpr.items else "unnamed"
        content_start = 1

    # Parse type
    blob_type = BlobType(type_str)

    # Parse scope (default: project)
    scope_str = sexpr.attrs.get("scope", "project")
    scope = BlobScope(scope_str)

    # Parse status (default: active)
    status_str = sexpr.attrs.get("status", DEFAULTS["status"])
    status = BlobStatus(status_str) if status_str else None

    # Parse updated
    updated_str = sexpr.attrs.get("updated")
    if updated_str:
        updated = datetime.strptime(updated_str, "%Y-%m-%d")
    else:
        updated = datetime.now()

    # Parse version
    version = int(sexpr.attrs.get("v", 2))

    # Parse summary
    summary = sexpr.attrs.get("summary", "")

    # Parse blocked_by
    blocked_by = sexpr.attrs.get("blocked-by")

    # Parse content sections
    files = []
    decisions = []
    facts = []
    next_steps = []
    related = []
    context = ""
    # Decay protocol fields
    decay_rate = None
    half_life = None
    compost_to = None
    immune_to = []
    challenged_by = []

    for item in sexpr.items[content_start:]:
        if isinstance(item, SExpr):
            if item.head == "files":
                files = [str(f) for f in item.items]

            elif item.head == "decisions":
                for dec in item.items:
                    if isinstance(dec, SExpr):
                        # Handle both (symbol ...) and ("string" ...) forms
                        if dec.head == "_tuple":
                            # String-headed tuple: items[0] is the choice
                            choice = dec.items[0] if dec.items else ""
                        else:
                            # Symbol-headed: the head itself might be meaningful
                            choice = dec.items[0] if dec.items else dec.head
                        why = dec.attrs.get("why", "")
                        decisions.append((choice, why))

            elif item.head == "facts":
                facts = [str(f) for f in item.items]

            elif item.head == "next":
                for step in item.items:
                    if isinstance(step, SExpr):
                        next_steps.append(step.items[0] if step.items else "")
                    else:
                        next_steps.append(str(step))

            elif item.head == "related":
                related = [str(r) for r in item.items]

            elif item.head == "decay":
                # Parse decay protocol fields from attributes
                if "rate" in item.attrs:
                    decay_rate = float(item.attrs["rate"])
                if "half_life" in item.attrs:
                    half_life = int(item.attrs["half_life"])
                if "compost_to" in item.attrs:
                    compost_to = item.attrs["compost_to"]

                # Parse sub-items for immune and challenged lists
                for sub in item.items:
                    if isinstance(sub, SExpr):
                        if sub.head == "immune":
                            immune_to = [str(e) for e in sub.items]
                        elif sub.head == "challenged":
                            challenged_by = [str(e) for e in sub.items]

            elif item.head == "context":
                # Context can be a single string child
                if item.items:
                    context = str(item.items[0])

    return Blob(
        type=blob_type,
        summary=summary,
        scope=scope,
        status=status,
        updated=updated,
        version=version,
        context=context,
        files=files,
        decisions=decisions,
        blocked_by=blocked_by,
        next_steps=next_steps,
        facts=facts,
        related=related,
        decay_rate=decay_rate,
        half_life=half_life,
        compost_to=compost_to,
        immune_to=immune_to,
        challenged_by=challenged_by,
    )


def blob_to_sexpr(blob, name: str = "unnamed", use_sigils: bool = True, delta: bool = True) -> str:
    """Convert Blob object to S-expression string.

    Args:
        blob: Blob object to convert
        name: Polip name
        use_sigils: Use sigil sugar (@thread instead of :type thread)
        delta: Omit default values (delta-from-default compression)
    """
    from .blob import Blob, BlobStatus, BlobScope

    lines = []
    indent = "  "

    # Opening with name
    header = f"(polip {name}"

    # Type - use sigil or omit if default
    type_val = blob.type.value
    if use_sigils:
        if not delta or type_val != DEFAULTS["type"]:
            header += f" @{type_val}"
    else:
        if not delta or type_val != DEFAULTS["type"]:
            header += f" :type {type_val}"

    # Scope - use sigil or omit if default
    scope_val = blob.scope.value
    if use_sigils:
        if not delta or scope_val != DEFAULTS["scope"]:
            header += f" ^{scope_val}"
    else:
        if not delta or scope_val != DEFAULTS["scope"]:
            header += f" :scope {scope_val}"

    # Summary - always present, use sigil
    summary_escaped = _escape_string(blob.summary)
    if use_sigils:
        header += f' ~"{summary_escaped}"'
    else:
        header += f' :summary "{summary_escaped}"'

    # Status - use sigil or omit if default
    if blob.status:
        status_val = blob.status.value
        if use_sigils:
            if not delta or status_val != DEFAULTS["status"]:
                header += f" +{status_val}"
        else:
            if not delta or status_val != DEFAULTS["status"]:
                header += f" :status {status_val}"

    lines.append(header)

    # Updated (always include - temporal anchor)
    lines.append(f'{indent}:updated "{blob.updated.strftime("%Y-%m-%d")}"')

    # Version - omit if default
    if not delta or blob.version != DEFAULTS["version"]:
        lines.append(f"{indent}:v {blob.version}")

    # Blocked by
    if blob.blocked_by:
        lines.append(f'{indent}:blocked-by "{_escape_string(blob.blocked_by)}"')

    # Files - use sigil sugar
    if blob.files:
        if use_sigils:
            file_strs = " ".join(f'"{_escape_string(f)}"' for f in blob.files)
            lines.append(f"{indent}#[{file_strs}]")
        else:
            lines.append(f"{indent}(files")
            for f in blob.files:
                lines.append(f'{indent}{indent}"{_escape_string(f)}"')
            lines.append(f"{indent})")

    # Decisions
    if blob.decisions:
        lines.append(f"{indent}(decisions")
        for choice, why in blob.decisions:
            choice_esc = _escape_string(choice)
            why_esc = _escape_string(why)
            lines.append(f'{indent}{indent}("{choice_esc}" :why "{why_esc}")')
        lines.append(f"{indent})")

    # Facts
    if blob.facts:
        lines.append(f"{indent}(facts")
        for fact in blob.facts:
            lines.append(f'{indent}{indent}"{_escape_string(fact)}"')
        lines.append(f"{indent})")

    # Next steps
    if blob.next_steps:
        lines.append(f"{indent}(next")
        for step in blob.next_steps:
            lines.append(f'{indent}{indent}"{_escape_string(step)}"')
        lines.append(f"{indent})")

    # Related
    if blob.related:
        related_strs = " ".join(blob.related)
        lines.append(f"{indent}(related {related_strs})")

    # Decay protocol fields
    if blob.decay_rate is not None or blob.half_life is not None or blob.compost_to or blob.immune_to or blob.challenged_by:
        decay_parts = ["(decay"]
        if blob.decay_rate is not None:
            decay_parts.append(f':rate {blob.decay_rate}')
        if blob.half_life is not None:
            decay_parts.append(f':half_life {blob.half_life}')
        if blob.compost_to:
            decay_parts.append(f':compost_to {blob.compost_to}')

        lines.append(f"{indent}{' '.join(decay_parts)}")

        # Immune-to list
        if blob.immune_to:
            lines.append(f"{indent}{indent}(immune")
            for event in blob.immune_to:
                lines.append(f'{indent}{indent}{indent}"{_escape_string(event)}"')
            lines.append(f"{indent}{indent})")

        # Challenged-by list
        if blob.challenged_by:
            lines.append(f"{indent}{indent}(challenged")
            for by in blob.challenged_by:
                lines.append(f'{indent}{indent}{indent}"{_escape_string(by)}"')
            lines.append(f"{indent}{indent})")

        lines.append(f"{indent})")

    # Context
    if blob.context:
        ctx_escaped = _escape_string(blob.context)
        lines.append(f'{indent}(context "{ctx_escaped}")')

    # Closing
    lines.append(")")

    return "\n".join(lines)


def _escape_string(s: str) -> str:
    """Escape a string for S-expression output."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")


def _unescape_string(s: str) -> str:
    """Unescape an S-expression string."""
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            next_ch = s[i + 1]
            if next_ch == 'n':
                result.append('\n')
            elif next_ch == 't':
                result.append('\t')
            elif next_ch == '\\':
                result.append('\\')
            elif next_ch == '"':
                result.append('"')
            else:
                result.append(next_ch)
            i += 2
        else:
            result.append(s[i])
            i += 1
    return "".join(result)


# --- Token Counting Utility ---

def estimate_tokens(text: str) -> int:
    """
    Estimate token count using simple heuristic.

    Claude tokenizer approximation:
    - ~4 chars per token for English text
    - XML tags and brackets add overhead
    - Punctuation often gets its own token
    """
    # Simple approximation based on character patterns
    # More accurate would need actual tokenizer

    # Count structural elements that tend to be separate tokens
    parens = text.count('(') + text.count(')')
    brackets = text.count('<') + text.count('>') + text.count('/')
    quotes = text.count('"')
    colons = text.count(':')
    equals = text.count('=')

    # Remove structural chars for base text count
    clean = text
    for ch in '()<>/"=:\n\t':
        clean = clean.replace(ch, ' ')

    # Word-like tokens
    words = len(clean.split())

    # Total estimate
    # XML: lots of < > / = " tokens
    # Lisp: fewer ( ) : " tokens
    structural = parens + brackets + quotes + colons + equals

    return words + structural


def compare_formats(blob, name: str = "test") -> dict:
    """Compare token counts between XML and S-expression."""
    xml = blob.to_xml()
    sexpr = blob_to_sexpr(blob, name)

    xml_tokens = estimate_tokens(xml)
    sexpr_tokens = estimate_tokens(sexpr)

    return {
        "xml_chars": len(xml),
        "xml_tokens": xml_tokens,
        "sexpr_chars": len(sexpr),
        "sexpr_tokens": sexpr_tokens,
        "char_reduction": f"{(1 - len(sexpr)/len(xml)) * 100:.1f}%",
        "token_reduction": f"{(1 - sexpr_tokens/xml_tokens) * 100:.1f}%",
    }


# --- Demo/Test ---

EXAMPLE_POLIP = """\
; AI-native polip format
(polip thread reef-native :scope project :status active :updated "2026-01-15" :v 2
  :summary "AI-native file format design"

  (files
    "src/reef/blob.py"
    "src/reef/sexpr.py")

  (decisions
    ("Use S-expressions" :why "60% token reduction over XML")
    ("Decay protocol" :why "Memory IS forgetting"))

  (facts
    "Zero dependencies - stdlib only"
    "Local-only package")

  (next
    "Write parser"
    "Implement serializer"
    "Add tests")

  (related constraints-project-rules reef-ux)

  (context "Deep dive into AI-native file formats.\\nKey insight: minimize ceremony, maximize semantic density."))
"""


if __name__ == "__main__":
    # Demo: parse and re-serialize
    print("=== Parsing S-expression ===")
    expr = parse_sexpr(EXAMPLE_POLIP)
    print(f"Head: {expr.head}")
    print(f"Attrs: {expr.attrs}")
    print(f"Items: {len(expr.items)}")

    print("\n=== Converting to Blob ===")
    blob = sexpr_to_blob(expr)
    print(f"Type: {blob.type}")
    print(f"Summary: {blob.summary}")
    print(f"Files: {blob.files}")
    print(f"Decisions: {blob.decisions}")

    print("\n=== Back to S-expression ===")
    output = blob_to_sexpr(blob, "reef-native")
    print(output)

    print("\n=== Token Comparison ===")
    comparison = compare_formats(blob, "reef-native")
    for k, v in comparison.items():
        print(f"  {k}: {v}")
