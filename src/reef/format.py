"""
.reef format - native AI memory format

One polip = one .reef file
Many .reef files = a reef

Format:
    =type:scope id date
    summary line
    +fact
    !decision
    ?question
    [ ] pending step
    [x] done step
    @link-to-polip
    ~context prose

Example:
    =constraint:always project-rules 2026-01-15
    reef project constraints
    +uv not pip
    +stdlib only
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


@dataclass
class Polip:
    """A single memory unit."""
    id: str
    type: str  # constraint, thread, context, fact, decision
    scope: str  # always, project, session
    updated: date
    summary: str
    facts: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    steps: list[tuple[bool, str]] = field(default_factory=list)  # (done, text)
    links: list[str] = field(default_factory=list)
    context: list[str] = field(default_factory=list)
    status: Optional[str] = None  # active, blocked, done (for threads)

    def to_reef(self) -> str:
        """Serialize to .reef format."""
        lines = []

        # Identity line
        identity = f"={self.type}:{self.scope} {self.id} {self.updated}"
        if self.status:
            identity += f" {self.status}"
        lines.append(identity)

        # Summary
        lines.append(self.summary)

        # Content
        for fact in self.facts:
            lines.append(f"+{fact}")

        for decision in self.decisions:
            lines.append(f"!{decision}")

        for question in self.questions:
            lines.append(f"?{question}")

        for done, step in self.steps:
            marker = "[x]" if done else "[ ]"
            lines.append(f"{marker} {step}")

        for link in self.links:
            lines.append(f"@{link}")

        for ctx in self.context:
            lines.append(f"~{ctx}")

        return "\n".join(lines)

    @classmethod
    def from_reef(cls, content: str) -> "Polip":
        """Parse .reef format."""
        lines = content.strip().split("\n")
        if not lines:
            raise ValueError("Empty polip")

        # Parse identity line: =type:scope id date [status]
        identity = lines[0]
        if not identity.startswith("="):
            raise ValueError(f"Invalid identity line: {identity}")

        parts = identity[1:].split()
        if len(parts) < 3:
            raise ValueError(f"Invalid identity: {identity}")

        type_scope = parts[0].split(":")
        if len(type_scope) != 2:
            raise ValueError(f"Invalid type:scope: {parts[0]}")

        polip_type, scope = type_scope
        polip_id = parts[1]
        updated = date.fromisoformat(parts[2])
        status = parts[3] if len(parts) > 3 else None

        # Summary is line 2
        summary = lines[1] if len(lines) > 1 else ""

        # Parse content
        facts = []
        decisions = []
        questions = []
        steps = []
        links = []
        context = []

        for line in lines[2:]:
            if not line:
                continue

            if line.startswith("+"):
                facts.append(line[1:])
            elif line.startswith("!"):
                decisions.append(line[1:])
            elif line.startswith("?"):
                questions.append(line[1:])
            elif line.startswith("[x] "):
                steps.append((True, line[4:]))
            elif line.startswith("[ ] "):
                steps.append((False, line[4:]))
            elif line.startswith("@"):
                links.append(line[1:])
            elif line.startswith("~"):
                context.append(line[1:])

        return cls(
            id=polip_id,
            type=polip_type,
            scope=scope,
            updated=updated,
            summary=summary,
            facts=facts,
            decisions=decisions,
            questions=questions,
            steps=steps,
            links=links,
            context=context,
            status=status,
        )

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
        polips = []
        for reef_file in self.reef_dir.rglob("*.reef"):
            try:
                polips.append(Polip.load(reef_file))
            except Exception:
                continue
        return polips

    def get(self, polip_id: str) -> Optional[Polip]:
        """Get polip by ID."""
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
