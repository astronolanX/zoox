"""
.reef format v2 - native AI memory format

Sigil-based sections:

    ~ type: thread              # identity
    ~ id: my-polip-id
    ~ scope: project
    @ 2026-01-19                # temporal
    ! 80                        # priority (0-100)
    # 152                       # token count

    --- surface
    Content surfaced to AI context.
    Multiple lines allowed.

    --- decide
    - Decision one
    - Decision two

    --- fact
    - Fact one
    - Fact two

    --- next
    - [ ] Pending step
    - [x] Done step

    --- link
    [[other-polip]]
    [[another-polip]]

    --- drift
    heat: 0.7
    touched: 3
    decay: 0.1

Sigils:
    ~   identity (type, id, scope)
    @   temporal (dates)
    !   priority/weight
    #   numeric measure
    --- section delimiter
    [[]] wiki-links
    -   list items
    :   key-value pairs
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


# Current polip format version
POLIP_VERSION = 2


@dataclass
class Polip:
    """A single memory unit in .reef format v2."""
    id: str
    type: str  # constraint, thread, context, fact, decision
    scope: str = "project"  # always, project, session
    updated: Optional[date] = None
    priority: int = 50  # 0-100
    tokens: int = 0
    version: int = POLIP_VERSION  # schema version for migration

    # Sections
    surface: str = ""  # main content
    facts: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    steps: list[tuple[bool, str]] = field(default_factory=list)  # (done, text)
    links: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)  # related files

    # Drift metadata
    heat: float = 1.0
    touched: int = 0
    decay_rate: float = 0.1

    # Status
    status: Optional[str] = None  # active, blocked, done (for threads)
    blocked_by: Optional[str] = None  # reason for blocked status

    # Legacy
    context: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        """First line of surface content."""
        if self.surface:
            return self.surface.split('\n')[0]
        return ""

    @classmethod
    def create(cls, *, summary: str = "", context: list = None, **kwargs) -> "Polip":
        """Factory method with backward-compatible summary/context arguments.

        Converts legacy 'summary' and 'context' to new 'surface' field.
        Use this for creating polips when you have old-style arguments.
        """
        # Build surface from summary + context
        surface = kwargs.pop("surface", "")
        if not surface and summary:
            surface = summary
            if context:
                ctx_text = context if isinstance(context, str) else "\n".join(context)
                if ctx_text:
                    surface = summary + "\n\n" + ctx_text
        return cls(surface=surface, **kwargs)

    def to_reef(self) -> str:
        """Serialize to .reef format v2."""
        lines = []

        # Identity sigils (~)
        lines.append(f"~ type: {self.type}")
        lines.append(f"~ id: {self.id}")
        lines.append(f"~ version: {self.version}")
        if self.scope != "project":
            lines.append(f"~ scope: {self.scope}")
        if self.status:
            lines.append(f"~ status: {self.status}")
        if self.blocked_by:
            lines.append(f"~ blocked: {self.blocked_by}")

        # Temporal sigil (@)
        if self.updated:
            lines.append(f"@ {self.updated}")

        # Priority sigil (!)
        if self.priority != 50:
            lines.append(f"! {self.priority}")

        # Token count (#)
        if self.tokens > 0:
            lines.append(f"# {self.tokens}")

        lines.append("")  # blank before sections

        # Surface section
        if self.surface:
            lines.append("--- surface")
            lines.append(self.surface)
            lines.append("")

        # Decide section
        if self.decisions:
            lines.append("--- decide")
            for d in self.decisions:
                lines.append(f"- {d}")
            lines.append("")

        # Fact section
        if self.facts:
            lines.append("--- fact")
            for f in self.facts:
                lines.append(f"- {f}")
            lines.append("")

        # Next steps section
        if self.steps:
            lines.append("--- next")
            for done, step in self.steps:
                marker = "[x]" if done else "[ ]"
                lines.append(f"- {marker} {step}")
            lines.append("")

        # Link section
        if self.links:
            lines.append("--- link")
            for link in self.links:
                lines.append(f"[[{link}]]")
            lines.append("")

        # Files section
        if self.files:
            lines.append("--- file")
            for f in self.files:
                lines.append(f"- {f}")
            lines.append("")

        # Drift section (only if non-default)
        if self.heat != 1.0 or self.touched > 0 or self.decay_rate != 0.1:
            lines.append("--- drift")
            lines.append(f"heat: {self.heat}")
            lines.append(f"touched: {self.touched}")
            lines.append(f"decay: {self.decay_rate}")

        return "\n".join(lines).rstrip() + "\n"

    @classmethod
    def _validate_id(cls, polip_id: str) -> None:
        """Validate polip ID to prevent path traversal."""
        if not polip_id:
            raise ValueError("Polip ID cannot be empty")
        if ".." in polip_id:
            raise ValueError(f"Path traversal detected in ID: {polip_id}")
        if polip_id.startswith("/") or polip_id.startswith("\\"):
            raise ValueError(f"Absolute path not allowed in ID: {polip_id}")
        # Only allow alphanumeric, dash, underscore
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        if not all(c in allowed for c in polip_id):
            raise ValueError(f"Invalid characters in ID: {polip_id}")

    @classmethod
    def from_reef(cls, content: str) -> "Polip":
        """Parse .reef format v2 (with v1 fallback)."""
        lines = content.strip().splitlines()
        if not lines:
            raise ValueError("Empty polip")

        # Detect format version
        first_line = lines[0].strip()
        if first_line.startswith("="):
            return cls._parse_v1(lines)
        elif first_line.startswith("~"):
            return cls._parse_v2(lines)
        else:
            raise ValueError(f"Unknown format, first line: {first_line}")

    @classmethod
    def _parse_v1(cls, lines: list[str]) -> "Polip":
        """Parse legacy v1 format: =type:scope id date"""
        identity = lines[0]
        parts = identity[1:].split()
        if len(parts) < 3:
            raise ValueError(f"Invalid v1 identity: {identity}")

        type_scope = parts[0].split(":")
        if len(type_scope) != 2:
            raise ValueError(f"Invalid type:scope: {parts[0]}")

        polip_type, scope = type_scope
        polip_id = parts[1]
        cls._validate_id(polip_id)
        updated = date.fromisoformat(parts[2])
        status = parts[3] if len(parts) > 3 else None

        summary = lines[1] if len(lines) > 1 else ""
        facts, decisions, questions, steps, links, context = [], [], [], [], [], []

        for line in lines[2:]:
            if not line:
                continue
            if line.startswith("+"):
                facts.append(line[1:])
            elif line.startswith("!"):
                decisions.append(line[1:])
            elif line.startswith("?"):
                questions.append(line[1:])
            elif line.startswith("[x]"):
                steps.append((True, line[4:].lstrip()))
            elif line.startswith("[ ]"):
                steps.append((False, line[4:].lstrip()))
            elif line.startswith("@"):
                links.append(line[1:])
            elif line.startswith("~"):
                context.append(line[1:])
            else:
                if context:
                    context[-1] = context[-1] + "\n" + line
                else:
                    context.append(line)

        return cls(
            id=polip_id,
            type=polip_type,
            scope=scope,
            updated=updated,
            surface=summary,
            facts=facts,
            decisions=decisions,
            questions=questions,
            steps=steps,
            links=links,
            context=context,
            status=status,
        )

    @classmethod
    def _parse_v2(cls, lines: list[str]) -> "Polip":
        """Parse v2 format with sigils and sections."""
        import re

        # Defaults
        polip_type = "context"
        polip_id = ""
        scope = "project"
        updated = None
        priority = 50
        tokens = 0
        version = POLIP_VERSION
        status = None
        blocked_by = None

        # Sections
        surface = ""
        facts = []
        decisions = []
        questions = []
        steps = []
        links = []
        files = []

        # Drift
        heat = 1.0
        touched = 0
        decay_rate = 0.1

        current_section = None
        section_lines = []

        def save_section():
            nonlocal surface, facts, decisions, questions, steps, links, files
            nonlocal heat, touched, decay_rate
            if not current_section:
                return
            content = "\n".join(section_lines).strip()

            if current_section == "surface":
                surface = content
            elif current_section == "decide":
                decisions = cls._parse_list_items(section_lines)
            elif current_section == "fact":
                facts = cls._parse_list_items(section_lines)
            elif current_section == "next":
                steps = cls._parse_steps(section_lines)
            elif current_section == "link":
                for line in section_lines:
                    matches = re.findall(r'\[\[([^\]]+)\]\]', line)
                    links.extend(matches)
            elif current_section == "file":
                files = cls._parse_list_items(section_lines)
            elif current_section == "drift":
                for line in section_lines:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k, v = k.strip(), v.strip()
                        if k == "heat":
                            try:
                                heat = float(v)
                            except ValueError:
                                pass
                        elif k == "touched":
                            try:
                                touched = int(v)
                            except ValueError:
                                pass
                        elif k == "decay":
                            try:
                                decay_rate = float(v)
                            except ValueError:
                                pass

        for line in lines:
            stripped = line.strip()

            # Identity sigil (~)
            if stripped.startswith("~"):
                if ":" in stripped:
                    k, v = stripped[1:].split(":", 1)
                    k, v = k.strip(), v.strip()
                    if k == "type":
                        polip_type = v
                    elif k == "id":
                        polip_id = v
                    elif k == "scope":
                        scope = v
                    elif k == "status":
                        status = v
                    elif k == "version":
                        try:
                            version = int(v)
                        except ValueError:
                            pass
                    elif k == "blocked":
                        blocked_by = v
                continue

            # Temporal sigil (@)
            if stripped.startswith("@"):
                date_str = stripped[1:].strip()
                try:
                    updated = date.fromisoformat(date_str)
                except ValueError:
                    pass
                continue

            # Priority sigil (!)
            if stripped.startswith("!"):
                try:
                    priority = int(stripped[1:].strip())
                except ValueError:
                    pass
                continue

            # Token sigil (#)
            if stripped.startswith("#"):
                val = stripped[1:].strip()
                # Skip if it looks like a comment (has words after number)
                if val and val.split()[0].isdigit():
                    try:
                        tokens = int(val.split()[0])
                    except ValueError:
                        pass
                    continue

            # Section delimiter
            if stripped.startswith("---"):
                save_section()
                current_section = stripped[3:].strip()
                section_lines = []
                continue

            # Inside section
            if current_section is not None:
                section_lines.append(line)

        # Save final section
        save_section()

        if polip_id:
            cls._validate_id(polip_id)

        return cls(
            id=polip_id,
            type=polip_type,
            scope=scope,
            updated=updated,
            priority=priority,
            tokens=tokens,
            version=version,
            surface=surface,
            facts=facts,
            decisions=decisions,
            questions=questions,
            steps=steps,
            links=links,
            files=files,
            heat=heat,
            touched=touched,
            decay_rate=decay_rate,
            status=status,
            blocked_by=blocked_by,
        )

    @classmethod
    def _parse_list_items(cls, lines: list[str]) -> list[str]:
        """Parse - prefixed list items."""
        items = []
        current = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("- "):
                if current:
                    items.append("\n".join(current))
                current = [stripped[2:]]
            elif stripped and current:
                current.append(stripped)
        if current:
            items.append("\n".join(current))
        return items

    @classmethod
    def _parse_steps(cls, lines: list[str]) -> list[tuple[bool, str]]:
        """Parse step items with [x] or [ ] markers."""
        steps = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("- [x]"):
                steps.append((True, stripped[6:].strip()))
            elif stripped.startswith("- [ ]"):
                steps.append((False, stripped[6:].strip()))
            elif stripped.startswith("- "):
                # No checkbox = pending
                steps.append((False, stripped[2:].strip()))
        return steps

    def save(self, reef_dir: Path) -> Path:
        """Save to .reef file in appropriate subdirectory."""
        # Type determines subdirectory
        subdir = reef_dir / f"{self.type}s"
        subdir.mkdir(parents=True, exist_ok=True)

        filepath = subdir / f"{self.id}.reef"
        filepath.write_text(self.to_reef())
        return filepath

    @classmethod
    def load(cls, filepath: Path) -> "Polip":
        """Load from .reef file."""
        return cls.from_reef(filepath.read_text())


class Reef:
    """A collection of polips."""

    def __init__(self, root: Path):
        self.root = root
        self.reef_dir = root / ".claude"

    def all(self) -> list[Polip]:
        """Load all polips."""
        if not self.reef_dir.exists():
            return []
        polips = []
        for reef_file in self.reef_dir.rglob("*.reef"):
            polips.append(Polip.load(reef_file))
        return polips

    def get(self, polip_id: str) -> Optional[Polip]:
        """Get polip by ID."""
        # Validate ID before using in path
        Polip._validate_id(polip_id)
        for reef_file in self.reef_dir.rglob(f"{polip_id}.reef"):
            try:
                return Polip.load(reef_file)
            except Exception:
                continue
        return None

    def by_type(self, polip_type: str) -> list[Polip]:
        """Get all polips of a type."""
        return [p for p in self.all() if p.type == polip_type]

    def by_scope(self, scope: str) -> list[Polip]:
        """Get all polips with a scope."""
        return [p for p in self.all() if p.scope == scope]

    def active_threads(self) -> list[Polip]:
        """Get active threads."""
        return [p for p in self.by_type("thread") if p.status == "active"]

    def constraints(self) -> list[Polip]:
        """Get all constraints (always surface)."""
        return self.by_type("constraint")

    def spawn(self, polip_type: str, polip_id: str, summary: str,
              scope: str = "project", **kwargs) -> Polip:
        """Create a new polip."""
        polip = Polip(
            id=polip_id,
            type=polip_type,
            scope=scope,
            updated=date.today(),
            summary=summary,
            **kwargs
        )
        polip.save(self.reef_dir)
        return polip
