"""
Blob - Lightweight XML context nodes for the glob.

Blobs are self-describing XML files that Claude reads/writes.
The structure guides inference without heavy machinery.
A "glob" is a collection of blobs.
"""

import xml.etree.ElementTree as ET
import json
import math
import os
import re
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from enum import Enum
from uuid import uuid4

# Index schema version - increment when index format changes
INDEX_VERSION = 1

# Built-in polip templates
BUILTIN_TEMPLATES = {
    "bug": {
        "type": "thread",
        "summary_template": "Bug: {title}",
        "scope": "project",
        "status": "active",
        "next_steps": [
            "Reproduce the issue",
            "Identify root cause",
            "Implement fix",
            "Add regression test",
        ],
        "description": "Bug tracking thread with standard fix workflow",
    },
    "feature": {
        "type": "thread",
        "summary_template": "Feature: {title}",
        "scope": "project",
        "status": "active",
        "next_steps": [
            "Define requirements",
            "Design solution",
            "Implement",
            "Test",
            "Document",
        ],
        "description": "Feature development thread with standard workflow",
    },
    "decision": {
        "type": "decision",
        "summary_template": "ADR: {title}",
        "scope": "project",
        "context_template": "## Context\n{context}\n\n## Decision\n{decision}\n\n## Consequences\n{consequences}",
        "description": "Architecture Decision Record (ADR) template",
    },
    "research": {
        "type": "thread",
        "summary_template": "Research: {title}",
        "scope": "project",
        "status": "active",
        "next_steps": [
            "Define research questions",
            "Gather sources",
            "Analyze findings",
            "Document conclusions",
        ],
        "description": "Research spike thread",
    },
    "constraint": {
        "type": "constraint",
        "summary_template": "{title}",
        "scope": "always",
        "description": "Project-wide constraint or rule",
    },
}


class PathTraversalError(ValueError):
    """Raised when a path attempts directory traversal."""
    pass


def _validate_name_safe(name: str) -> str:
    """
    Validate that a polip name (filename) is safe before constructing paths.

    Catches traversal patterns BEFORE they become paths.
    Names should NOT contain path separators - they're filenames only.
    """
    import urllib.parse

    # Decode URL encoding first (catch %2f..%2f patterns)
    decoded = urllib.parse.unquote(name)

    # Patterns that indicate traversal attempts (strict for filenames)
    dangerous_patterns = [
        "..",           # Unix traversal
        "\\",           # Windows path separator
        "/",            # Unix path separator (filenames shouldn't have this)
        "\x00",         # Null byte
        "\n", "\r",     # Newlines (header injection)
    ]

    for pattern in dangerous_patterns:
        if pattern in decoded:
            raise PathTraversalError(
                f"Name '{name}' contains dangerous pattern: {repr(pattern)}"
            )

    # Also check for absolute paths
    if decoded.startswith("/") or (len(decoded) > 1 and decoded[1] == ":"):
        raise PathTraversalError(f"Name '{name}' looks like absolute path")

    return name


def _validate_subdir_safe(subdir: str) -> str:
    """
    Validate that a subdirectory path is safe.

    Subdirs CAN contain '/' for nesting but must NOT contain traversal patterns.
    """
    import urllib.parse

    # Decode URL encoding first
    decoded = urllib.parse.unquote(subdir)

    # Patterns that indicate traversal attempts (allows /)
    dangerous_patterns = [
        "..",           # Unix traversal
        "\\",           # Windows path separator
        "\x00",         # Null byte
        "\n", "\r",     # Newlines
    ]

    for pattern in dangerous_patterns:
        if pattern in decoded:
            raise PathTraversalError(
                f"Subdir '{subdir}' contains dangerous pattern: {repr(pattern)}"
            )

    # Check for absolute paths
    if decoded.startswith("/") or (len(decoded) > 1 and decoded[1] == ":"):
        raise PathTraversalError(f"Subdir '{subdir}' looks like absolute path")

    return subdir


def _validate_path_safe(base_dir: Path, target_path: Path) -> Path:
    """
    Validate that target_path is safely contained within base_dir.

    Prevents directory traversal attacks (e.g., ../../../etc/passwd).

    Args:
        base_dir: The allowed base directory
        target_path: The path to validate

    Returns:
        The resolved absolute path if safe

    Raises:
        PathTraversalError: If path escapes base_dir
    """
    # Resolve both to absolute paths
    base_resolved = base_dir.resolve()
    target_resolved = target_path.resolve()

    # Check that target is within base
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError:
        raise PathTraversalError(
            f"Path '{target_path}' escapes base directory '{base_dir}'"
        )

    return target_resolved


def _atomic_write(path: Path, content: str) -> None:
    """
    Atomically write content to a file using temp+rename pattern.

    This ensures that readers never see partial writes - they either
    see the old content or the complete new content.

    Args:
        path: Destination file path
        content: Content to write
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory (ensures same filesystem for rename)
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)  # Ensure data hits disk
        os.close(fd)
        fd = None

        # Atomic rename (POSIX guarantees atomicity on same filesystem)
        os.rename(tmp_path, path)
    except Exception:
        # Clean up temp file on failure
        if fd is not None:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


class BlobType(Enum):
    """Types of blobs in a glob."""
    CONTEXT = "context"      # Session state, what was I doing
    THREAD = "thread"        # Active work stream
    DECISION = "decision"    # Architectural choice made
    CONSTRAINT = "constraint"  # Always-on rules
    FACT = "fact"            # Key information about project


class BlobScope(Enum):
    """When should this blob be surfaced."""
    SESSION = "session"      # Only current session
    PROJECT = "project"      # Anytime in this project
    ALWAYS = "always"        # Every interaction


class BlobStatus(Enum):
    """Status of work-related blobs."""
    ACTIVE = "active"
    BLOCKED = "blocked"
    DONE = "done"
    ARCHIVED = "archived"


# Current blob schema version - increment when schema changes
BLOB_VERSION = 2

# Import centralized constants
from reef.constants import (
    REEF_DIR, LEGACY_DIR, SUBDIRS, POLIP_EXTENSIONS,
    TYPE_TO_SUBDIR, TYPE_TO_EXTENSION, DEFAULT_EXTENSION,
    extension_for_type, subdir_for_type, lifecycle_for_extension,
)

# Known subdirectories for blob organization (DRY: single source of truth)
# Includes both new structure and legacy for migration
KNOWN_SUBDIRS = (
    # New structure
    "current", "bedrock", "settled", "pool",
    # Legacy (for migration)
    "threads", "decisions", "constraints", "contexts", "facts",
)

# Wiki link pattern: [[polip-name]]
WIKI_LINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')


def _iter_polip_files(directory: Path):
    """Yield all polip files in directory (both .reef and .blob.xml)."""
    if not directory.exists():
        return
    for ext in POLIP_EXTENSIONS:
        yield from directory.glob(f"*{ext}")


def _polip_name_from_path(path: Path) -> str:
    """Extract polip name from path, removing extension."""
    name = path.name
    for ext in POLIP_EXTENSIONS:
        if name.endswith(ext):
            return name[:-len(ext)]
    return name


def _find_polip_path(base_dir: Path, name: str, subdir: str = None) -> Path | None:
    """Find a polip file by name, checking both extensions."""
    search_dir = base_dir / subdir if subdir else base_dir
    if not search_dir.exists():
        return None
    for ext in POLIP_EXTENSIONS:
        path = search_dir / f"{name}{ext}"
        if path.exists():
            return path
    return None


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words for TF-IDF."""
    return re.findall(r'\b[a-z0-9]+\b', text.lower())


def _compute_tf(tokens: list[str]) -> dict[str, float]:
    """Compute term frequency (normalized by document length)."""
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {term: count / total for term, count in counts.items()}


def _compute_idf(term: str, documents: list[list[str]]) -> float:
    """Compute inverse document frequency for a term."""
    if not documents:
        return 0.0
    doc_count = sum(1 for doc in documents if term in doc)
    if doc_count == 0:
        return 0.0
    return math.log(len(documents) / doc_count) + 1.0


def _tfidf_score(query_tokens: list[str], doc_tokens: list[str], all_docs: list[list[str]]) -> float:
    """Compute TF-IDF similarity score between query and document."""
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_tf = _compute_tf(doc_tokens)
    query_tf = _compute_tf(query_tokens)

    # Compute TF-IDF vectors
    all_terms = set(query_tokens) | set(doc_tokens)

    score = 0.0
    for term in query_tf:
        if term in doc_tf:
            idf = _compute_idf(term, all_docs)
            # Cosine similarity component
            score += query_tf[term] * doc_tf[term] * idf * idf

    return score


# BM25 parameters (tuned for short documents like polip summaries)
BM25_K1 = 1.2  # Term frequency saturation
BM25_B = 0.75  # Document length normalization


def _bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    all_docs: list[list[str]],
    avgdl: float = 0.0,
) -> float:
    """
    Compute BM25 score - improved ranking over raw TF-IDF.

    BM25 adds:
    1. Term frequency saturation (diminishing returns for repeated terms)
    2. Document length normalization (shorter docs don't get penalized)
    """
    if not query_tokens or not doc_tokens:
        return 0.0

    # Compute average document length if not provided
    if avgdl == 0.0:
        avgdl = sum(len(doc) for doc in all_docs) / len(all_docs) if all_docs else 1.0

    doc_len = len(doc_tokens)
    doc_counts = Counter(doc_tokens)
    n_docs = len(all_docs)

    score = 0.0
    for term in query_tokens:
        if term not in doc_counts:
            continue

        # Document frequency
        df = sum(1 for doc in all_docs if term in doc)
        if df == 0:
            continue

        # IDF component (BM25 variant)
        idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)

        # Term frequency with saturation
        tf = doc_counts[term]
        tf_component = (tf * (BM25_K1 + 1)) / (
            tf + BM25_K1 * (1 - BM25_B + BM25_B * doc_len / avgdl)
        )

        score += idf * tf_component

    return score


# Field weights for precision improvement
FIELD_WEIGHTS = {
    "summary": 3.0,      # Title/summary is most important
    "type": 2.0,         # Type name often matches intent
    "facts": 1.5,        # Facts are secondary content
    "status": 1.0,       # Status sometimes relevant
    "context": 1.0,      # Context is background
}


def _weighted_bm25_score(
    query_tokens: list[str],
    entry: dict,
    all_docs: list[list[str]],
    avgdl: float = 0.0,
) -> float:
    """
    BM25 with field weighting - different fields have different importance.

    This significantly improves precision by boosting matches in summary/type
    over matches in general content.
    """
    if not query_tokens:
        return 0.0

    total_score = 0.0

    # Score each field with its weight
    for field, weight in FIELD_WEIGHTS.items():
        field_value = entry.get(field, "")
        if isinstance(field_value, list):
            field_value = " ".join(str(v) for v in field_value)
        if not field_value:
            continue

        field_tokens = _tokenize(str(field_value))
        if not field_tokens:
            continue

        field_score = _bm25_score(query_tokens, field_tokens, all_docs, avgdl)
        total_score += field_score * weight

    return total_score


def _get_git_info(project_dir: Path) -> dict[str, str]:
    """
    Get git information for template variables.

    Returns dict with keys: git_branch, git_sha, git_short_sha
    All values default to empty string if git not available.
    """
    result = {"git_branch": "", "git_sha": "", "git_short_sha": ""}

    try:
        # Get current branch
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=5,
        )
        if proc.returncode == 0:
            result["git_branch"] = proc.stdout.strip()

        # Get current commit SHA
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=5,
        )
        if proc.returncode == 0:
            sha = proc.stdout.strip()
            result["git_sha"] = sha
            result["git_short_sha"] = sha[:7]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return result


def get_template_variables(project_dir: Path) -> dict[str, str]:
    """
    Get all available template variables.

    Returns dict with keys:
    - date: Current date (YYYY-MM-DD)
    - timestamp: Current datetime (ISO format)
    - project_name: Name of the project directory
    - git_branch: Current git branch (or empty)
    - git_sha: Full commit SHA (or empty)
    - git_short_sha: Short commit SHA (or empty)
    """
    now = datetime.now()
    variables = {
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(),
        "project_name": project_dir.name,
    }
    variables.update(_get_git_info(project_dir))
    return variables


@dataclass
class Blob:
    """A single blob - an atomic unit of context."""

    type: BlobType
    summary: str
    scope: BlobScope = BlobScope.PROJECT
    status: Optional[BlobStatus] = None
    updated: datetime = field(default_factory=datetime.now)
    version: int = BLOB_VERSION  # Schema version for migration

    # Content fields
    context: str = ""
    files: list[str] = field(default_factory=list)
    decisions: list[tuple[str, str]] = field(default_factory=list)  # (choice, why)
    blocked_by: Optional[str] = None
    next_steps: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)  # Links to other blobs

    # Decay protocol fields
    decay_rate: Optional[float] = None  # Rate at which polip relevance decays
    half_life: Optional[int] = None  # Days until relevance halves
    compost_to: Optional[str] = None  # Polip to merge into when decayed
    immune_to: list[str] = field(default_factory=list)  # Decay events to ignore
    challenged_by: list[str] = field(default_factory=list)  # Polips that challenge this one

    def needs_migration(self) -> bool:
        """Check if this blob needs schema migration."""
        return self.version < BLOB_VERSION

    def migrate(self) -> "Blob":
        """Migrate blob to current schema version."""
        if self.version < 2:
            # v1 -> v2: Add version field (already done by loading)
            pass
        self.version = BLOB_VERSION
        self.updated = datetime.now()
        return self

    def extract_wiki_links(self) -> list[str]:
        """
        Extract [[wiki-style]] links from summary and context.

        Returns:
            List of unique polip names referenced via [[name]] syntax
        """
        links = set()
        # Search in summary and context
        for text in [self.summary, self.context]:
            if text:
                for match in WIKI_LINK_PATTERN.finditer(text):
                    links.add(match.group(1))
        return sorted(links)

    def update_related_from_links(self) -> None:
        """
        Auto-populate related field from wiki links found in content.

        Merges wiki link references with any existing manual references.
        """
        wiki_links = self.extract_wiki_links()
        existing = set(self.related)
        # Merge wiki links with existing, preserving order
        for link in wiki_links:
            if link not in existing:
                self.related.append(link)
                existing.add(link)

    def to_xml(self) -> str:
        """Serialize blob to XML string.

        Automatically extracts [[wiki links]] from content and adds them
        to the related field before serialization.
        """
        # Auto-populate related from wiki links
        self.update_related_from_links()

        # Root element with attributes
        attribs = {
            "type": self.type.value,
            "scope": self.scope.value,
            "updated": self.updated.strftime("%Y-%m-%d"),
            "v": str(self.version),
        }
        if self.status:
            attribs["status"] = self.status.value

        root = ET.Element("blob", attribs)

        # Summary (required)
        summary_el = ET.SubElement(root, "summary")
        summary_el.text = self.summary

        # Files
        if self.files:
            files_el = ET.SubElement(root, "files")
            for f in self.files:
                file_el = ET.SubElement(files_el, "file")
                file_el.text = f

        # Decisions
        if self.decisions:
            decisions_el = ET.SubElement(root, "decisions")
            for choice, why in self.decisions:
                dec_el = ET.SubElement(decisions_el, "decision", why=why)
                dec_el.text = choice

        # Facts
        if self.facts:
            facts_el = ET.SubElement(root, "facts")
            for fact in self.facts:
                fact_el = ET.SubElement(facts_el, "fact")
                fact_el.text = fact

        # Blocked by
        if self.blocked_by:
            blocked_el = ET.SubElement(root, "blocked-by")
            blocked_el.text = self.blocked_by

        # Next steps
        if self.next_steps:
            next_el = ET.SubElement(root, "next")
            for step in self.next_steps:
                step_el = ET.SubElement(next_el, "step")
                step_el.text = step

        # Related blobs
        if self.related:
            related_el = ET.SubElement(root, "related")
            for ref in self.related:
                ref_el = ET.SubElement(related_el, "ref")
                ref_el.text = ref

        # Decay protocol fields
        if self.decay_rate is not None or self.half_life is not None or self.compost_to or self.immune_to or self.challenged_by:
            decay_el = ET.SubElement(root, "decay")
            if self.decay_rate is not None:
                decay_el.set("rate", str(self.decay_rate))
            if self.half_life is not None:
                decay_el.set("half_life", str(self.half_life))
            if self.compost_to:
                decay_el.set("compost_to", self.compost_to)

            # Immune-to list
            if self.immune_to:
                immune_el = ET.SubElement(decay_el, "immune")
                for item in self.immune_to:
                    item_el = ET.SubElement(immune_el, "event")
                    item_el.text = item

            # Challenged-by list
            if self.challenged_by:
                challenged_el = ET.SubElement(decay_el, "challenged")
                for item in self.challenged_by:
                    item_el = ET.SubElement(challenged_el, "by")
                    item_el.text = item

        # Free-form context (last, as catch-all)
        if self.context:
            context_el = ET.SubElement(root, "context")
            context_el.text = self.context

        # Pretty print
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode")

    @classmethod
    def from_xml(cls, xml_string: str) -> "Blob":
        """Parse blob from XML string.

        Raises:
            ValueError: If XML is malformed or cannot be parsed
        """
        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            raise ValueError(f"Malformed XML in blob: {e}") from e

        # Parse attributes
        blob_type = BlobType(root.get("type", "context"))
        scope = BlobScope(root.get("scope", "project"))
        status_str = root.get("status")
        status = BlobStatus(status_str) if status_str else None
        updated_str = root.get("updated")
        updated = datetime.strptime(updated_str, "%Y-%m-%d") if updated_str else datetime.now()
        version_str = root.get("v")
        version = int(version_str) if version_str else 1  # Default to v1 for old blobs

        # Parse summary
        summary_el = root.find("summary")
        summary = summary_el.text if summary_el is not None and summary_el.text else ""

        # Parse files
        files = []
        files_el = root.find("files")
        if files_el is not None:
            files = [f.text for f in files_el.findall("file") if f.text]

        # Parse decisions
        decisions = []
        decisions_el = root.find("decisions")
        if decisions_el is not None:
            for dec in decisions_el.findall("decision"):
                if dec.text:
                    decisions.append((dec.text, dec.get("why", "")))

        # Parse facts
        facts = []
        facts_el = root.find("facts")
        if facts_el is not None:
            facts = [f.text for f in facts_el.findall("fact") if f.text]

        # Parse blocked-by
        blocked_el = root.find("blocked-by")
        blocked_by = blocked_el.text if blocked_el is not None else None

        # Parse next steps
        next_steps = []
        next_el = root.find("next")
        if next_el is not None:
            next_steps = [s.text for s in next_el.findall("step") if s.text]

        # Parse related
        related = []
        related_el = root.find("related")
        if related_el is not None:
            related = [r.text for r in related_el.findall("ref") if r.text]

        # Parse decay protocol fields
        decay_rate = None
        half_life = None
        compost_to = None
        immune_to = []
        challenged_by = []
        decay_el = root.find("decay")
        if decay_el is not None:
            # Parse attributes
            rate_str = decay_el.get("rate")
            if rate_str:
                decay_rate = float(rate_str)
            half_life_str = decay_el.get("half_life")
            if half_life_str:
                half_life = int(half_life_str)
            compost_to = decay_el.get("compost_to")

            # Parse immune-to list
            immune_el = decay_el.find("immune")
            if immune_el is not None:
                immune_to = [e.text for e in immune_el.findall("event") if e.text]

            # Parse challenged-by list
            challenged_el = decay_el.find("challenged")
            if challenged_el is not None:
                challenged_by = [e.text for e in challenged_el.findall("by") if e.text]

        # Parse context
        context_el = root.find("context")
        context = context_el.text if context_el is not None and context_el.text else ""

        return cls(
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

    def save(self, path: Path):
        """Save blob to file atomically."""
        _atomic_write(path, self.to_xml())

    @classmethod
    def _from_polip(cls, polip: "Polip") -> "Blob":
        """Convert a Polip (from format.py) to a Blob."""
        from datetime import datetime

        # Map type string to BlobType enum
        type_map = {
            "constraint": BlobType.CONSTRAINT,
            "thread": BlobType.THREAD,
            "context": BlobType.CONTEXT,
            "decision": BlobType.DECISION,
            "fact": BlobType.FACT,
        }
        blob_type = type_map.get(polip.type, BlobType.CONTEXT)

        # Map scope string to BlobScope enum
        scope_map = {
            "always": BlobScope.ALWAYS,
            "project": BlobScope.PROJECT,
            "session": BlobScope.SESSION,
        }
        blob_scope = scope_map.get(polip.scope, BlobScope.PROJECT)

        # Map status string to BlobStatus enum
        status_map = {
            "active": BlobStatus.ACTIVE,
            "blocked": BlobStatus.BLOCKED,
            "done": BlobStatus.DONE,
            "archived": BlobStatus.ARCHIVED,
        }
        blob_status = status_map.get(polip.status) if polip.status else None

        # Combine context lines into single string
        context_text = "\n".join(polip.context) if polip.context else ""

        # Convert steps to next_steps (just the text, not done status for now)
        next_steps = [step_text for done, step_text in polip.steps if not done]

        return cls(
            type=blob_type,
            summary=polip.summary,
            scope=blob_scope,
            status=blob_status,
            files=[],  # Polip format doesn't have files
            related=polip.links,
            context=context_text,
            facts=polip.facts,
            decisions=[(d, "") for d in polip.decisions],  # Convert to (choice, why) tuples
            next_steps=next_steps,
            updated=datetime.combine(polip.updated, datetime.min.time()),
        )

    @classmethod
    def load(cls, path: Path) -> "Blob":
        """Load blob from file (auto-detects .reef or .blob.xml format).

        Raises:
            FileNotFoundError: If the blob file doesn't exist
            ValueError: If the blob content is malformed
            UnicodeDecodeError: If the file contains invalid UTF-8
        """
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError(f"Blob file not found: {path}")
        except UnicodeDecodeError as e:
            raise ValueError(f"Blob file contains invalid UTF-8: {path}") from e

        stripped = content.lstrip()

        # Auto-detect format based on content prefix
        # Human-readable .reef format starts with =
        if stripped.startswith("="):
            from .format import Polip
            try:
                polip = Polip.from_reef(content)
                return cls._from_polip(polip)
            except Exception as e:
                raise ValueError(f"Invalid .reef format in {path}: {e}") from e

        # S-expression format starts with (
        if stripped.startswith("("):
            from .sexpr import parse_sexpr, sexpr_to_blob
            try:
                sexpr = parse_sexpr(content)
                return sexpr_to_blob(sexpr)
            except Exception as e:
                raise ValueError(f"Invalid S-expression format in {path}: {e}") from e

        # Fall back to XML format
        return cls.from_xml(content)


class Glob:
    """
    A glob of blobs for a project.

    Manages reading, writing, and surfacing relevant blobs.
    Supports both new .reef/ structure and legacy .claude/ for migration.
    """

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

        # Try new .reef/ first, fall back to .claude/ for migration
        reef_dir = project_dir / REEF_DIR
        legacy_dir = project_dir / LEGACY_DIR

        if reef_dir.exists():
            self.reef_dir = reef_dir
            self._using_legacy = False
        elif legacy_dir.exists():
            # Use legacy dir but flag for migration
            self.reef_dir = legacy_dir
            self._using_legacy = True
        else:
            # New project - create .reef/
            reef_dir.mkdir(exist_ok=True)
            self.reef_dir = reef_dir
            self._using_legacy = False

        # Alias for backwards compatibility (deprecated, use reef_dir)
        self.claude_dir = self.reef_dir

        # Cache: path -> (mtime, Blob) for avoiding repeated I/O
        self._cache: dict[Path, tuple[float, Blob]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def _get_cached(self, path: Path) -> Optional[Blob]:
        """
        Get a blob from cache if valid, otherwise load and cache it.

        Uses mtime for cache invalidation - if file changed, reload.
        Returns None if file doesn't exist or can't be loaded.
        """
        if not path.exists():
            # Remove from cache if file was deleted
            self._cache.pop(path, None)
            return None

        try:
            current_mtime = path.stat().st_mtime
        except OSError:
            return None

        # Check cache
        if path in self._cache:
            cached_mtime, cached_blob = self._cache[path]
            if cached_mtime == current_mtime:
                self._cache_hits += 1
                return cached_blob

        # Cache miss - load and store
        self._cache_misses += 1
        try:
            blob = Blob.load(path)
            self._cache[path] = (current_mtime, blob)
            return blob
        except Exception:
            # Remove invalid cache entry
            self._cache.pop(path, None)
            return None

    def _invalidate_cache(self, path: Path) -> None:
        """Remove a path from the cache."""
        self._cache.pop(path, None)

    def cache_stats(self) -> dict:
        """Return cache statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate": hit_rate,
            "cached_blobs": len(self._cache),
        }

    # --- Index Management ---

    def _index_path(self) -> Path:
        """Path to the index file."""
        return self.claude_dir / "index.json"

    def _load_index(self) -> dict:
        """Load index from disk, or return empty index if not exists."""
        path = self._index_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if data.get("version") == INDEX_VERSION:
                    return data
            except (json.JSONDecodeError, KeyError):
                pass
        # Return fresh index
        return {
            "version": INDEX_VERSION,
            "updated": datetime.now().isoformat(),
            "blobs": {},
        }

    def _save_index(self, index: dict) -> None:
        """Save index to disk atomically."""
        index["updated"] = datetime.now().isoformat()
        _atomic_write(self._index_path(), json.dumps(index, indent=2))

    def _blob_key(self, path: Path) -> str:
        """Get index key for a blob path (relative to claude_dir)."""
        try:
            return str(path.relative_to(self.claude_dir))
        except ValueError:
            return str(path)

    def _update_index(self, path: Path, blob: Blob) -> None:
        """Add or update a blob entry in the index."""
        index = self._load_index()
        key = self._blob_key(path)
        # Preserve existing access_count if present
        existing = index["blobs"].get(key, {})
        access_count = existing.get("access_count", 0)
        index["blobs"][key] = {
            "type": blob.type.value,
            "scope": blob.scope.value,
            "status": blob.status.value if blob.status else None,
            "summary": blob.summary[:200],  # Truncate for index
            "files": blob.files[:10],  # Limit files in index
            "related": blob.related[:10],  # Limit related in index
            "updated": blob.updated.strftime("%Y-%m-%d"),
            "access_count": access_count,
        }
        self._save_index(index)

    def _increment_access(self, keys: list[str]) -> None:
        """Increment access count for surfaced polips (LRU tracking)."""
        if not keys:
            return
        index = self._load_index()
        for key in keys:
            if key in index["blobs"]:
                index["blobs"][key]["access_count"] = index["blobs"][key].get("access_count", 0) + 1
        self._save_index(index)

    def get_access_count(self, key: str) -> int:
        """Get access count for a polip from index."""
        index = self.get_index()
        return index.get("blobs", {}).get(key, {}).get("access_count", 0)

    def _remove_from_index(self, path: Path) -> None:
        """Remove a blob entry from the index."""
        index = self._load_index()
        key = self._blob_key(path)
        if key in index["blobs"]:
            del index["blobs"][key]
            self._save_index(index)

    def rebuild_index(self) -> int:
        """
        Rebuild index from scratch by scanning all blobs.

        Preserves access_count from existing index entries.
        Returns number of blobs indexed.
        """
        # Load existing index to preserve access counts
        old_index = self._load_index()
        old_blobs = old_index.get("blobs", {})

        index = {
            "version": INDEX_VERSION,
            "updated": datetime.now().isoformat(),
            "blobs": {},
        }

        count = 0
        # Scan root and all known subdirectories
        for subdir in [None, *KNOWN_SUBDIRS, "archive"]:
            if subdir:
                search_dir = self.claude_dir / subdir
            else:
                search_dir = self.claude_dir

            if not search_dir.exists():
                continue

            for path in _iter_polip_files(search_dir):
                try:
                    blob = Blob.load(path)
                    key = self._blob_key(path)
                    # Preserve access_count from old index
                    access_count = old_blobs.get(key, {}).get("access_count", 0)
                    index["blobs"][key] = {
                        "type": blob.type.value,
                        "scope": blob.scope.value,
                        "status": blob.status.value if blob.status else None,
                        "summary": blob.summary[:200],
                        "files": blob.files[:10],
                        "related": blob.related[:10],
                        "updated": blob.updated.strftime("%Y-%m-%d"),
                        "access_count": access_count,
                    }
                    count += 1
                except Exception:
                    continue

        self._save_index(index)
        return count

    def get_index(self) -> dict:
        """Get the current index (load or rebuild if missing)."""
        index = self._load_index()
        if not index["blobs"]:
            # Empty index - try rebuild
            self.rebuild_index()
            index = self._load_index()
        return index

    def search_index(
        self,
        query: Optional[str] = None,
        blob_type: Optional[str] = None,
        scope: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> list[tuple[str, dict, float]]:
        """
        Search the index for matching polips using TF-IDF ranking.

        Args:
            query: Text to search in summaries (fuzzy TF-IDF matching)
            blob_type: Filter by type (thread, decision, constraint, fact, context)
            scope: Filter by scope (always, project, session)
            status: Filter by status (active, blocked, done, archived)
            limit: Maximum results to return

        Returns:
            List of (key, entry, score) tuples matching criteria, ranked by relevance
        """
        index = self.get_index()
        results = []
        blobs_dict = index.get("blobs", {})

        # Pre-compute document tokens for BM25 if query provided
        all_docs = []
        all_keys = []
        avgdl = 0.0
        if query:
            for key, entry in blobs_dict.items():
                # Combine all searchable fields for corpus statistics
                doc_text = f"{entry.get('summary', '')} {entry.get('type', '')} {' '.join(entry.get('facts', []))}"
                all_docs.append(_tokenize(doc_text))
                all_keys.append(key)
            query_tokens = _tokenize(query)
            query_lower = query.lower()
            # Pre-compute average document length for BM25
            avgdl = sum(len(doc) for doc in all_docs) / len(all_docs) if all_docs else 1.0

        for key, entry in blobs_dict.items():
            # Apply type/scope/status filters
            if blob_type and entry.get("type") != blob_type:
                continue
            if scope and entry.get("scope") != scope:
                continue
            if status and entry.get("status") != status:
                continue

            score = 0.0
            if query:
                summary = entry.get("summary", "")

                # Use BM25 with field weighting for better precision
                bm25 = _weighted_bm25_score(query_tokens, entry, all_docs, avgdl)
                score = bm25

                # Bonus for exact substring match in summary
                if query_lower in summary.lower():
                    score += 2.0

                # Skip if no relevance to query (before applying boosts)
                if score == 0.0:
                    continue

                # Recency boost: prefer recently updated polips (only if matched)
                updated = entry.get("updated", "")
                if updated:
                    try:
                        from datetime import datetime
                        days_old = (datetime.now() - datetime.strptime(updated, "%Y-%m-%d")).days
                        recency_boost = max(0, 1.0 - days_old / 30)  # Decay over 30 days
                        score += recency_boost * 0.5
                    except (ValueError, TypeError):
                        pass

                # LRU boost: frequently accessed polips are probably useful
                access_count = entry.get("access_count", 0)
                if access_count > 0:
                    score += math.log(1 + access_count) * 0.3
            else:
                # No query = all matching filters get same score
                score = 1.0

            results.append((key, entry, score))

        # Sort by score descending
        results.sort(key=lambda x: x[2], reverse=True)

        return results[:limit]

    def sprout(self, blob: Blob, name: str, subdir: Optional[str] = None) -> Path:
        """
        Sprout a new blob into the glob.

        Args:
            blob: The blob to create
            name: Filename (without extension)
            subdir: Optional subdirectory (current/, bedrock/, etc.)

        Returns:
            Path to the created blob file

        Raises:
            PathTraversalError: If name or subdir attempts directory traversal
        """
        # Validate name BEFORE constructing path (catches traversal patterns)
        _validate_name_safe(name)
        if subdir:
            _validate_subdir_safe(subdir)
            target_dir = self.reef_dir / subdir
        else:
            target_dir = self.reef_dir

        # Choose extension based on blob type
        ext = extension_for_type(blob.type.value) if blob.type else DEFAULT_EXTENSION
        path = target_dir / f"{name}{ext}"

        # Also validate constructed path (defense in depth)
        _validate_path_safe(self.reef_dir, path)

        target_dir.mkdir(parents=True, exist_ok=True)
        blob.save(path)
        self._invalidate_cache(path)  # Invalidate after write
        self._update_index(path, blob)  # Update index
        return path

    def get(self, name: str, subdir: Optional[str] = None) -> Optional[Blob]:
        """
        Get a blob by name.

        Raises:
            PathTraversalError: If name or subdir attempts directory traversal
        """
        # Validate name BEFORE constructing path
        _validate_name_safe(name)
        if subdir:
            _validate_subdir_safe(subdir)

        # Find polip file (supports both .reef and .blob.xml)
        path = _find_polip_path(self.claude_dir, name, subdir)
        if not path:
            return None

        # Also validate found path (defense in depth)
        _validate_path_safe(self.claude_dir, path)

        return self._get_cached(path)

    def list_blobs(self, subdir: Optional[str] = None) -> list[tuple[str, Blob]]:
        """List all blobs, optionally in a subdirectory."""
        if subdir:
            search_dir = self.claude_dir / subdir
        else:
            search_dir = self.claude_dir

        if not search_dir.exists():
            return []

        blobs = []
        for path in _iter_polip_files(search_dir):
            blob = self._get_cached(path)
            if blob is not None:
                name = _polip_name_from_path(path)
                blobs.append((name, blob))

        return blobs

    def surface_relevant(
        self,
        files: list[str] = None,
        query: str = None,
        track_access: bool = True,
    ) -> list[Blob]:
        """
        Surface blobs relevant to current context.

        Uses TF-IDF scoring for query matching, providing fuzzy semantic search
        that ranks results by relevance rather than just substring matching.
        Includes LRU-style access tracking to boost frequently-used polips.

        Args:
            files: Files being touched (surfaces blobs that reference them)
            query: Free-text query to match against summaries/context
            track_access: If True, increment access count for surfaced polips

        Returns:
            List of relevant blobs, scored by relevance
        """
        relevant = []

        # Collect all blobs from root and all known subdirectories
        all_blobs = []  # (name, blob, subdir) tuples
        for name, blob in self.list_blobs():
            all_blobs.append((name, blob, None))
        for subdir in KNOWN_SUBDIRS:
            for name, blob in self.list_blobs(subdir):
                all_blobs.append((name, blob, subdir))

        # Get index for access counts
        index = self.get_index()
        blobs_index = index.get("blobs", {})

        # Pre-tokenize all documents for TF-IDF if we have a query
        all_doc_tokens = []
        if query:
            for name, blob, subdir in all_blobs:
                doc_text = f"{blob.summary} {blob.context}"
                all_doc_tokens.append(_tokenize(doc_text))
            query_tokens = _tokenize(query)

        for i, (name, blob, subdir) in enumerate(all_blobs):
            score = 0.0

            # Always-scope blobs always surface
            if blob.scope == BlobScope.ALWAYS:
                score += 10.0

            # Active/blocked threads surface
            if blob.status in (BlobStatus.ACTIVE, BlobStatus.BLOCKED):
                score += 5.0

            # File overlap
            if files and blob.files:
                overlap = set(files) & set(blob.files)
                score += len(overlap) * 3.0

            # Determine the actual key for this blob (based on its type extension)
            blob_ext = extension_for_type(blob.type.value) if blob.type else DEFAULT_EXTENSION
            blob_key = f"{subdir}/{name}{blob_ext}" if subdir else f"{name}{blob_ext}"

            # LRU boost: frequently accessed polips get a small boost
            # Use logarithmic scaling to prevent runaway scores
            access_count = blobs_index.get(blob_key, {}).get("access_count", 0)
            if access_count > 0:
                # log(1 + count) gives diminishing returns: 1->0.69, 10->2.4, 100->4.6
                score += math.log(1 + access_count)

            # TF-IDF query matching
            if query and all_doc_tokens:
                tfidf = _tfidf_score(query_tokens, all_doc_tokens[i], all_doc_tokens)
                # Scale TF-IDF score to be comparable with other scoring factors
                # TF-IDF scores are typically small, so multiply by 10
                score += tfidf * 10.0

                # Bonus for exact substring match (in addition to TF-IDF)
                query_lower = query.lower()
                if query_lower in blob.summary.lower():
                    score += 3.0
                if query_lower in blob.context.lower():
                    score += 1.0

            if score > 0:
                relevant.append((score, blob, blob_key))

        # Sort by score descending
        relevant.sort(key=lambda x: x[0], reverse=True)

        # Track access for surfaced polips
        if track_access and relevant:
            accessed_keys = [key for _, _, key in relevant]
            self._increment_access(accessed_keys)

        return [blob for _, blob, _ in relevant]

    def decompose(self, name: str, subdir: Optional[str] = None):
        """
        Move a blob to the archive (decomposition).

        Raises:
            PathTraversalError: If name or subdir attempts directory traversal
        """
        # Validate name before path construction
        _validate_name_safe(name)
        if subdir:
            _validate_subdir_safe(subdir)

        src = _find_polip_path(self.claude_dir, name, subdir)
        if not src:
            return

        # Validate source path is safely within .claude directory
        _validate_path_safe(self.claude_dir, src)

        # Load, update status, save to archive
        blob = Blob.load(src)
        blob.status = BlobStatus.ARCHIVED

        archive_dir = self.claude_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        # Include date and UUID in archived name for uniqueness
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = uuid4().hex[:8]
        archive_path = archive_dir / f"{date_str}-{name}-{unique_id}.blob.xml"
        blob.save(archive_path)

        # Remove original and update caches/index
        src.unlink()
        self._invalidate_cache(src)
        self._remove_from_index(src)
        self._update_index(archive_path, blob)

    def inject_context(self) -> str:
        """
        Generate XML context for injection into Claude's prompt.

        Returns all relevant blobs as a single XML document.
        """
        relevant = self.surface_relevant()

        if not relevant:
            return ""

        # Build composite XML
        root = ET.Element("glob", project=str(self.project_dir.name))

        for blob in relevant[:10]:  # Limit to top 10
            blob_el = ET.fromstring(blob.to_xml())
            root.append(blob_el)

        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode")

    def check_migrations(self) -> list[tuple[Path, Blob]]:
        """
        Check for blobs that need schema migration.

        Returns list of (path, blob) tuples that need updating.
        """
        outdated = []

        # Check all blobs from root and all known subdirectories
        all_blobs = []
        all_blobs.extend(self.list_blobs())
        for subdir in KNOWN_SUBDIRS:
            all_blobs.extend(self.list_blobs(subdir))

        for name, blob in all_blobs:
            if blob.needs_migration():
                # Find actual path (could be .reef or .blob.xml)
                path = _find_polip_path(self.claude_dir, name)
                if not path:
                    for subdir in KNOWN_SUBDIRS:
                        path = _find_polip_path(self.claude_dir, name, subdir)
                        if path:
                            break
                if path:
                    outdated.append((path, blob))

        return outdated

    def migrate_all(self) -> int:
        """
        Migrate all outdated blobs to current schema.

        Returns number of blobs migrated.
        """
        outdated = self.check_migrations()
        for path, blob in outdated:
            blob.migrate()
            blob.save(path)
        return len(outdated)

    def update_status(
        self,
        name: str,
        status: BlobStatus,
        subdir: Optional[str] = None,
        blocked_by: Optional[str] = None,
    ) -> Optional[Blob]:
        """
        Update the status of an existing blob.

        Args:
            name: Blob name (without extension)
            status: New status to set
            subdir: Optional subdirectory
            blocked_by: Reason for blocking (only used with BLOCKED status)

        Returns:
            Updated blob if found, None if not found

        Raises:
            PathTraversalError: If name or subdir attempts directory traversal
        """
        # Validate name before path construction
        _validate_name_safe(name)
        if subdir:
            _validate_subdir_safe(subdir)

        path = _find_polip_path(self.claude_dir, name, subdir)
        if not path:
            return None

        # Validate path is safely within .claude directory
        _validate_path_safe(self.claude_dir, path)

        blob = Blob.load(path)
        blob.status = status
        blob.updated = datetime.now()

        # Handle blocked_by field
        if status == BlobStatus.BLOCKED and blocked_by:
            blob.blocked_by = blocked_by
        elif status != BlobStatus.BLOCKED:
            blob.blocked_by = None  # Clear when not blocked

        blob.save(path)
        self._invalidate_cache(path)
        self._update_index(path, blob)
        return blob

    def create_snapshot(self, name: Optional[str] = None) -> Path:
        """
        Create a snapshot of current reef state.

        Args:
            name: Optional name for the snapshot (default: timestamp)

        Returns:
            Path to the created snapshot file
        """
        snapshot_dir = self.claude_dir / "snapshots"
        snapshot_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if name:
            filename = f"{timestamp}-{name}.snapshot.json"
        else:
            filename = f"{timestamp}.snapshot.json"

        # Collect all blobs
        snapshot_data = {
            "version": 1,
            "created": datetime.now().isoformat(),
            "name": name,
            "blobs": {},
        }

        # Scan all locations
        for subdir in [None, *KNOWN_SUBDIRS]:
            for blob_name, blob in self.list_blobs(subdir):
                key = f"{subdir}/{blob_name}" if subdir else blob_name
                snapshot_data["blobs"][key] = {
                    "type": blob.type.value,
                    "scope": blob.scope.value,
                    "status": blob.status.value if blob.status else None,
                    "summary": blob.summary,
                    "updated": blob.updated.strftime("%Y-%m-%d"),
                    "files": blob.files,
                    "next_steps": blob.next_steps,
                }

        path = snapshot_dir / filename
        _atomic_write(path, json.dumps(snapshot_data, indent=2))
        return path

    def list_snapshots(self) -> list[tuple[Path, dict]]:
        """
        List all snapshots.

        Returns:
            List of (path, metadata) tuples, sorted by date descending
        """
        snapshot_dir = self.claude_dir / "snapshots"
        if not snapshot_dir.exists():
            return []

        snapshots = []
        for path in snapshot_dir.glob("*.snapshot.json"):
            try:
                data = json.loads(path.read_text())
                snapshots.append((path, {
                    "name": data.get("name"),
                    "created": data.get("created"),
                    "blob_count": len(data.get("blobs", {})),
                }))
            except Exception:
                continue

        # Sort by filename (which starts with timestamp) descending
        snapshots.sort(key=lambda x: x[0].name, reverse=True)
        return snapshots

    def diff_snapshot(self, snapshot_path: Path) -> dict:
        """
        Compare current reef to a snapshot.

        Args:
            snapshot_path: Path to snapshot file

        Returns:
            Dict with added, removed, changed blob keys
        """
        snapshot_data = json.loads(snapshot_path.read_text())
        snapshot_blobs = snapshot_data.get("blobs", {})

        # Collect current blobs
        current_blobs = {}
        for subdir in [None, *KNOWN_SUBDIRS]:
            for blob_name, blob in self.list_blobs(subdir):
                key = f"{subdir}/{blob_name}" if subdir else blob_name
                current_blobs[key] = {
                    "type": blob.type.value,
                    "status": blob.status.value if blob.status else None,
                    "summary": blob.summary,
                }

        snapshot_keys = set(snapshot_blobs.keys())
        current_keys = set(current_blobs.keys())

        added = current_keys - snapshot_keys
        removed = snapshot_keys - current_keys
        common = current_keys & snapshot_keys

        # Check for changes in common blobs
        changed = {}
        for key in common:
            old = snapshot_blobs[key]
            new = current_blobs[key]
            diffs = []
            if old.get("status") != new.get("status"):
                diffs.append(f"status: {old.get('status')} -> {new.get('status')}")
            if old.get("summary") != new.get("summary"):
                diffs.append("summary changed")
            if diffs:
                changed[key] = diffs

        return {
            "added": sorted(added),
            "removed": sorted(removed),
            "changed": changed,
            "snapshot_name": snapshot_data.get("name"),
            "snapshot_created": snapshot_data.get("created"),
        }

    def list_templates(self) -> list[tuple[str, dict, bool]]:
        """
        List available templates (built-in and user-defined).

        Returns:
            List of (name, template_data, is_builtin) tuples
        """
        templates = []

        # Built-in templates
        for name, tmpl in BUILTIN_TEMPLATES.items():
            templates.append((name, tmpl, True))

        # User-defined templates
        template_dir = self.claude_dir / "templates"
        if template_dir.exists():
            for path in template_dir.glob("*.template.json"):
                try:
                    data = json.loads(path.read_text())
                    name = path.stem.replace(".template", "")
                    templates.append((name, data, False))
                except Exception:
                    continue

        return templates

    def get_template(self, name: str) -> Optional[dict]:
        """Get a template by name (built-in or user-defined)."""
        # Check built-in first
        if name in BUILTIN_TEMPLATES:
            return BUILTIN_TEMPLATES[name]

        # Check user-defined
        template_path = self.claude_dir / "templates" / f"{name}.template.json"
        if template_path.exists():
            try:
                return json.loads(template_path.read_text())
            except Exception:
                return None

        return None

    def create_from_template(
        self,
        template_name: str,
        title: str,
        **kwargs,
    ) -> Optional[Path]:
        """
        Create a polip from a template.

        Supports rich template variables:
        - {title}: The provided title
        - {date}: Current date (YYYY-MM-DD)
        - {timestamp}: Current datetime (ISO format)
        - {project_name}: Name of the project directory
        - {git_branch}: Current git branch (or empty)
        - {git_sha}: Full commit SHA (or empty)
        - {git_short_sha}: Short commit SHA (or empty)

        Args:
            template_name: Name of the template to use
            title: Title for the polip (used in summary)
            **kwargs: Additional template variables

        Returns:
            Path to created polip, or None if template not found
        """
        template = self.get_template(template_name)
        if not template:
            return None

        # Get rich template variables
        tmpl_vars = get_template_variables(self.project_dir)
        tmpl_vars["title"] = title
        tmpl_vars.update(kwargs)

        # Parse type
        blob_type = BlobType(template.get("type", "thread"))

        # Build summary from template
        summary_tmpl = template.get("summary_template", "{title}")
        summary = summary_tmpl.format(**tmpl_vars)

        # Parse scope
        scope_str = template.get("scope", "project")
        scope = BlobScope(scope_str)

        # Parse status (only for threads)
        status = None
        if blob_type == BlobType.THREAD:
            status_str = template.get("status")
            status = BlobStatus(status_str) if status_str else BlobStatus.ACTIVE

        # Build context from template if provided
        context = ""
        if "context_template" in template:
            # Add default empty values for optional template vars
            ctx_vars = {
                "context": "",
                "decision": "",
                "consequences": "",
            }
            ctx_vars.update(tmpl_vars)
            context = template["context_template"].format(**ctx_vars)

        # Get next steps from template
        next_steps = template.get("next_steps", [])

        # Create blob
        blob = Blob(
            type=blob_type,
            summary=summary,
            scope=scope,
            status=status,
            context=context,
            next_steps=next_steps,
        )

        # Determine subdirectory using centralized constants
        subdir = subdir_for_type(blob_type.value) if blob_type else "current"

        # Generate name from title
        name = title.lower()
        name = "".join(c if c.isalnum() or c == " " else "" for c in name)
        name = "-".join(name.split())[:30]

        return self.sprout(blob, name, subdir)

    def save_template(self, name: str, template: dict) -> Path:
        """
        Save a user-defined template.

        Args:
            name: Template name
            template: Template data

        Returns:
            Path to saved template file

        Raises:
            PathTraversalError: If name attempts directory traversal
        """
        template_dir = self.claude_dir / "templates"
        template_dir.mkdir(exist_ok=True)

        path = template_dir / f"{name}.template.json"

        # Validate path is safely within templates directory
        _validate_path_safe(template_dir, path)

        _atomic_write(path, json.dumps(template, indent=2))
        return path

    def delete_template(self, name: str) -> bool:
        """
        Delete a user-defined template.

        Args:
            name: Template name

        Returns:
            True if deleted, False if not found or is built-in

        Raises:
            PathTraversalError: If name attempts directory traversal
        """
        if name in BUILTIN_TEMPLATES:
            return False  # Can't delete built-in

        template_dir = self.claude_dir / "templates"
        template_path = template_dir / f"{name}.template.json"

        # Validate path is safely within templates directory
        _validate_path_safe(template_dir, template_path)

        if template_path.exists():
            template_path.unlink()
            return True
        return False

    def check_integrity(self) -> dict:
        """
        Check reef integrity for issues.

        Returns:
            Dict with:
                missing_files: list of (polip_key, missing_file_path)
                stale_polips: list of (polip_key, days_old) for session polips >7d
                orphan_files: list of blob files not in index
                broken_refs: list of (polip_key, broken_related_ref)
                schema_outdated: list of polips needing migration
        """
        from datetime import timedelta

        issues = {
            "missing_files": [],
            "stale_polips": [],
            "orphan_files": [],
            "broken_refs": [],
            "schema_outdated": [],
        }

        now = datetime.now()
        stale_threshold = now - timedelta(days=7)
        index = self.get_index()
        indexed_keys = set(index.get("blobs", {}).keys())
        found_keys = set()

        # Scan all polips (including archive)
        for subdir in [None, *KNOWN_SUBDIRS, "archive"]:
            for blob_name, blob in self.list_blobs(subdir):
                key = f"{subdir}/{blob_name}" if subdir else blob_name
                # Track found keys (try both extensions for index comparison)
                for ext in POLIP_EXTENSIONS:
                    found_keys.add(f"{key}{ext}")

                # Check file references
                for f in blob.files:
                    file_path = Path(f).expanduser()
                    if not file_path.is_absolute():
                        file_path = self.project_dir / f
                    if not file_path.exists():
                        issues["missing_files"].append((key, f))

                # Check staleness (session polips only)
                if blob.scope == BlobScope.SESSION and blob.updated < stale_threshold:
                    days_old = (now - blob.updated).days
                    issues["stale_polips"].append((key, days_old))

                # Check related refs
                for ref in blob.related:
                    # Check if ref exists as a polip (either extension)
                    ref_found = _find_polip_path(self.claude_dir, ref) is not None
                    if not ref_found:
                        # Try subdirs
                        for sd in KNOWN_SUBDIRS:
                            if _find_polip_path(self.claude_dir, ref, sd) is not None:
                                ref_found = True
                                break
                    if not ref_found:
                        issues["broken_refs"].append((key, ref))

                # Check schema version
                if blob.needs_migration():
                    issues["schema_outdated"].append(key)

        # Check for orphan files (in filesystem but not index)
        for key in indexed_keys:
            if key not in found_keys:
                issues["orphan_files"].append(key)

        return issues

    def fix_missing_files(self, polip_key: str, remove_missing: bool = True) -> bool:
        """
        Fix a polip with missing file references.

        Args:
            polip_key: Key like 'threads/my-thread' or 'my-thread'
            remove_missing: If True, remove missing file refs; else just report

        Returns:
            True if fixed, False if polip not found
        """
        # Parse key into subdir and name
        if "/" in polip_key:
            subdir, name = polip_key.split("/", 1)
        else:
            subdir, name = None, polip_key

        blob = self.get(name, subdir=subdir)
        if not blob:
            return False

        if not remove_missing:
            return True

        # Filter out missing files
        valid_files = []
        for f in blob.files:
            file_path = Path(f).expanduser()
            if not file_path.is_absolute():
                file_path = self.project_dir / f
            if file_path.exists():
                valid_files.append(f)

        if len(valid_files) != len(blob.files):
            blob.files = valid_files
            blob.updated = datetime.now()

            # Save back (find actual path regardless of extension)
            path = _find_polip_path(self.claude_dir, name, subdir)
            if path:
                blob.save(path)
                self._update_index(path, blob)

        return True

    def _component_to_grade(self, score: int, max_score: int = 25) -> str:
        """
        Convert component score to spark grade using square ASCII system.

        Grades:
        - ██ (≥80%): High confidence
        - ▓▓ (≥60%): Medium-high
        - ░░ (≥40%): Medium-low
        - ·· (<40%): Low

        Args:
            score: Component score (0-25)
            max_score: Maximum possible score (default 25)

        Returns:
            Two-character grade string
        """
        pct = (score / max_score * 100) if max_score > 0 else 0
        if pct >= 80:
            return "██"
        elif pct >= 60:
            return "▓▓"
        elif pct >= 40:
            return "░░"
        else:
            return "··"

    def _calculate_vitality(self, blobs_dict: dict) -> dict:
        """
        Calculate reef vitality score (0-100) based on ecosystem health.

        Components:
        - Activity (0-25): Recent polip updates, creation rate
        - Quality (0-25): Nutrient richness (facts, decisions, links)
        - Resonance (0-25): Access patterns, linking patterns
        - Health (0-25): Freshness, no contradictions, connectivity

        Returns:
            Dict with score, status, last_activity, recommended_action, and spark grades
        """
        if not blobs_dict:
            return {
                "score": 0,
                "status": "empty",
                "last_activity": None,
                "recommended_action": "Create first polip: reef sprout thread 'Start your reef'",
                "components": {"activity": 0, "quality": 0, "resonance": 0, "health": 0},
                "grades": {
                    "activity": "··",
                    "quality": "··",
                    "resonance": "··",
                    "health": "··",
                    "compact": "········"
                },
            }

        now = datetime.now()

        # Component 1: Activity (Tidal patterns)
        # Track: last update, polip creation rate, access frequency
        activity_score = 0
        last_activity = None
        polip_ages = []

        for key, entry in blobs_dict.items():
            updated_str = entry.get("updated", "")
            if updated_str:
                try:
                    updated = datetime.strptime(updated_str, "%Y-%m-%d")
                    polip_ages.append((now - updated).days)
                    if last_activity is None or updated > last_activity:
                        last_activity = updated
                except (ValueError, TypeError):
                    pass

        if last_activity:
            days_since_activity = (now - last_activity).days
            # Recent activity gets high score
            if days_since_activity < 1:
                activity_score = 25
            elif days_since_activity < 3:
                activity_score = 20
            elif days_since_activity < 7:
                activity_score = 15
            elif days_since_activity < 14:
                activity_score = 10
            else:
                activity_score = max(0, 10 - days_since_activity // 7)

        # Component 2: Quality (Nutrient richness)
        # Track: facts, decisions, links, content depth
        quality_score = 0
        total_facts = 0
        total_decisions = 0
        total_links = 0

        for key, entry in blobs_dict.items():
            facts = entry.get("facts", [])
            decisions = entry.get("decisions", [])
            related = entry.get("related", [])

            total_facts += len(facts) if isinstance(facts, list) else 0
            total_decisions += len(decisions) if isinstance(decisions, list) else 0
            total_links += len(related) if isinstance(related, list) else 0

        polip_count = len(blobs_dict)
        avg_facts = total_facts / polip_count if polip_count > 0 else 0
        avg_decisions = total_decisions / polip_count if polip_count > 0 else 0
        avg_links = total_links / polip_count if polip_count > 0 else 0

        # Score based on content richness
        quality_score = min(25, int(
            avg_facts * 3 +      # Facts add richness
            avg_decisions * 5 +  # Decisions are critical
            avg_links * 2        # Links show integration
        ))

        # Component 3: Resonance (Access patterns)
        # Track: access_count, link frequency, calcification potential
        resonance_score = 0
        total_access = 0
        linked_polips = set()

        for key, entry in blobs_dict.items():
            access_count = entry.get("access_count", 0)
            total_access += access_count

            related = entry.get("related", [])
            if isinstance(related, list):
                for ref in related:
                    linked_polips.add(ref)

        avg_access = total_access / polip_count if polip_count > 0 else 0
        link_density = len(linked_polips) / polip_count if polip_count > 0 else 0

        # Score based on usage patterns
        resonance_score = min(25, int(
            math.log(1 + avg_access) * 5 +  # Log scale for access counts
            link_density * 20                # Link density is key indicator
        ))

        # Component 4: Health (Freshness and cohesion)
        # Track: stale polips, contradictions, isolated polips
        health_score = 25  # Start at max, deduct for issues

        # Deduct for stale polips
        stale_count = sum(1 for age in polip_ages if age > 30)
        health_score -= min(10, stale_count * 2)

        # Deduct for isolated polips (no links)
        isolated_count = sum(1 for key, entry in blobs_dict.items()
                            if not entry.get("related", []))
        isolation_rate = isolated_count / polip_count if polip_count > 0 else 0
        health_score -= int(isolation_rate * 10)

        # Deduct for session contexts that never became threads
        abandoned_contexts = sum(1 for key, entry in blobs_dict.items()
                                if entry.get("type") == "context"
                                and entry.get("scope") == "session"
                                and (now - datetime.strptime(entry.get("updated", "2000-01-01"), "%Y-%m-%d")).days > 14)
        health_score -= min(5, abandoned_contexts)

        health_score = max(0, health_score)

        # Total vitality score
        vitality_score = activity_score + quality_score + resonance_score + health_score

        # Determine status
        if vitality_score >= 75:
            status = "thriving"
            icon = "🟢"
        elif vitality_score >= 50:
            status = "stable"
            icon = "🟡"
        elif vitality_score >= 25:
            status = "declining"
            icon = "🟠"
        else:
            status = "dying"
            icon = "🔴"

        # Recommended action (based on weakest component)
        components = {
            "activity": activity_score,
            "quality": quality_score,
            "resonance": resonance_score,
            "health": health_score,
        }

        weakest = min(components.items(), key=lambda x: x[1])

        actions = {
            "activity": "Add new polips or update existing ones (reef sprout thread '...')",
            "quality": "Enrich polips with facts and decisions (edit .claude/threads/*.xml)",
            "resonance": "Link related polips together using [[polip-name]] syntax",
            "health": "Prune stale polips (reef sink) or resolve contradictions",
        }

        recommended_action = actions.get(weakest[0], "Keep creating quality content")

        # Generate spark grades for each component
        a_grade = self._component_to_grade(activity_score)
        q_grade = self._component_to_grade(quality_score)
        r_grade = self._component_to_grade(resonance_score)
        h_grade = self._component_to_grade(health_score)

        return {
            "score": int(vitality_score),
            "status": status,
            "icon": icon,
            "last_activity": last_activity.strftime("%Y-%m-%d") if last_activity else None,
            "days_since_activity": (now - last_activity).days if last_activity else None,
            "recommended_action": recommended_action,
            "components": components,
            "grades": {
                "activity": a_grade,
                "quality": q_grade,
                "resonance": r_grade,
                "health": h_grade,
                "compact": f"{a_grade}{q_grade}{r_grade}{h_grade}"
            },
            "metrics": {
                "avg_facts": round(avg_facts, 1),
                "avg_decisions": round(avg_decisions, 1),
                "avg_links": round(avg_links, 1),
                "stale_count": stale_count,
                "isolated_count": isolated_count,
            }
        }

    def write_status(self) -> None:
        """
        Write current reef status to /tmp/reef-{project}.status for statusline.

        Includes:
        - Polip counts by type
        - Total tokens and token savings
        - Active thread info
        - Active trenches
        """
        status_file = Path(f"/tmp/reef-{self.project_dir.name}.status")

        # Collect polip statistics
        index = self.get_index()
        blobs_dict = index.get("blobs", {})

        # Count by type and calculate tokens
        type_counts = {}
        total_tokens = 0  # Full L2 content
        l1_tokens = 0     # Just L1 metadata (summary + overhead)

        for key, entry in blobs_dict.items():
            blob_type = entry.get("type", "unknown")
            type_counts[blob_type] = type_counts.get(blob_type, 0) + 1

            # Get actual token count if stored, else estimate from summary
            summary = entry.get("summary", "")
            summary_words = len(summary.split())

            # L1 tokens: just summary + minimal metadata
            l1_tokens += int(summary_words * 1.3) + 20  # ~20 tokens for XML overhead

            # L2 tokens: use stored value or estimate 10x summary as content
            # (Context polips have facts/next-steps, threads have full details)
            stored_tokens = entry.get("tokens")
            if stored_tokens:
                total_tokens += stored_tokens
            else:
                # Estimate: summary is ~10% of full content
                total_tokens += int(summary_words * 1.3 * 10) + 50

        # Token savings calculation (savings from using L1 vs L2)
        token_savings_pct = 0
        if total_tokens > 0:
            token_savings_pct = int((1 - l1_tokens / total_tokens) * 100)

        # Find active thread
        active_thread = None
        for key, entry in blobs_dict.items():
            if entry.get("type") == "thread" and entry.get("status") == "active":
                active_thread = entry.get("summary", "Unknown thread")
                break

        # Calculate vitality score (reef health)
        vitality_data = self._calculate_vitality(blobs_dict)

        # Get trench status
        trenches_active = []
        try:
            from reef.trench import TrenchManager
            trench_mgr = TrenchManager(self.project_dir)
            trenches = trench_mgr.list_trenches()
            for trench in trenches:
                if trench.status.value in ["running", "testing", "ready"]:
                    trenches_active.append({
                        "name": trench.name,
                        "status": trench.status.value,
                        "branch": trench.branch,
                    })
        except Exception:
            # Trench system not available or no trenches
            pass

        # Build status data
        status = {
            "count": len(blobs_dict),
            "types": type_counts,
            "total_tokens": int(total_tokens),
            "l1_tokens": int(l1_tokens),
            "token_savings_pct": token_savings_pct,
            "active_thread": active_thread,
            "trenches": trenches_active,
            "vitality": vitality_data,
            "updated": datetime.now().isoformat(),
        }

        # Write atomically
        try:
            _atomic_write(status_file, json.dumps(status, indent=2))
        except Exception:
            # Fail silently - statusline is non-critical
            pass

    def build_graph(self) -> dict:
        """
        Build a graph of polip relationships.

        Returns:
            Dict with nodes (polips) and edges (relationships)
        """
        nodes = {}
        edges = []
        file_refs = {}  # file -> list of blob keys

        # Collect all blobs
        for subdir in [None, *KNOWN_SUBDIRS]:
            for blob_name, blob in self.list_blobs(subdir):
                key = f"{subdir}/{blob_name}" if subdir else blob_name
                nodes[key] = {
                    "type": blob.type.value,
                    "status": blob.status.value if blob.status else None,
                    "summary": blob.summary[:40],
                    "scope": blob.scope.value,
                }

                # Track related links
                for ref in blob.related:
                    edges.append((key, ref, "related"))

                # Track file references for co-reference edges
                for f in blob.files:
                    if f not in file_refs:
                        file_refs[f] = []
                    file_refs[f].append(key)

        # Create edges for polips sharing files
        for f, blob_keys in file_refs.items():
            if len(blob_keys) > 1:
                # Connect all polips that reference the same file
                for i, k1 in enumerate(blob_keys):
                    for k2 in blob_keys[i + 1:]:
                        edges.append((k1, k2, f"file:{f}"))

        return {
            "nodes": nodes,
            "edges": edges,
        }

    def to_dot(self) -> str:
        """
        Generate Graphviz DOT format for the polip graph.

        Returns:
            DOT format string
        """
        graph = self.build_graph()

        # Type -> color mapping
        colors = {
            "thread": "lightblue",
            "decision": "lightgreen",
            "constraint": "lightyellow",
            "fact": "lightgray",
            "context": "lightpink",
        }

        # Status -> shape mapping
        shapes = {
            "active": "ellipse",
            "blocked": "octagon",
            "done": "box",
            None: "ellipse",
        }

        lines = ["digraph reef {", "  rankdir=LR;", "  node [fontsize=10];"]

        # Add nodes
        for key, attrs in graph["nodes"].items():
            color = colors.get(attrs["type"], "white")
            shape = shapes.get(attrs["status"], "ellipse")
            label = f"{key}\\n{attrs['summary']}"
            lines.append(f'  "{key}" [label="{label}", fillcolor="{color}", style=filled, shape={shape}];')

        # Add edges
        for src, dst, label in graph["edges"]:
            if dst in graph["nodes"]:  # Only include edges to existing nodes
                style = "dashed" if label.startswith("file:") else "solid"
                lines.append(f'  "{src}" -> "{dst}" [label="{label}", style={style}];')

        lines.append("}")
        return "\n".join(lines)

    def cleanup_session(
        self,
        archive_days: int = 30,
        dry_run: bool = False,
    ) -> dict:
        """
        Session-start cleanup with exclusive lock for swarm safety.

        Performs:
        - Prune SESSION-scope blobs from previous sessions
        - Prune archives older than archive_days
        - Migrate outdated blobs
        - Check for orphaned file references (warning only)

        Uses lock file (.cleanup.lock) to prevent concurrent cleanup.
        Uses marker file (.last-cleanup) to skip if already cleaned today.

        Returns dict with counts: sessions_pruned, archives_pruned, migrated
        """
        results = {
            "sessions_pruned": 0,
            "archives_pruned": 0,
            "migrated": 0,
            "skipped": False,
            "locked": False,
        }

        lock_path = self.claude_dir / ".cleanup.lock"
        marker_path = self.claude_dir / ".last-cleanup"
        today = datetime.now().strftime("%Y-%m-%d")

        # Fast path: already cleaned today
        if marker_path.exists():
            try:
                if marker_path.read_text().strip() == today:
                    results["skipped"] = True
                    return results
            except Exception:
                pass  # Marker corrupted, proceed with cleanup

        # Acquire exclusive lock (non-blocking)
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            # Another agent is cleaning - skip gracefully
            results["locked"] = True
            return results

        try:
            # 1. Prune stale SESSION-scope blobs
            threshold = datetime.now()
            for subdir in [None, *KNOWN_SUBDIRS]:
                for name, blob in self.list_blobs(subdir):
                    if blob.scope != BlobScope.SESSION:
                        continue
                    # SESSION blobs from previous days are stale
                    if blob.updated.date() < threshold.date():
                        path = _find_polip_path(self.claude_dir, name, subdir)
                        if path and not dry_run:
                            path.unlink(missing_ok=True)
                        results["sessions_pruned"] += 1

            # 2. Prune old archives
            archive_dir = self.claude_dir / "archive"
            if archive_dir.exists():
                cutoff = datetime.now().date() - timedelta(days=archive_days)
                for path in _iter_polip_files(archive_dir):
                    try:
                        blob = Blob.load(path)
                        if blob.updated.date() < cutoff:
                            if not dry_run:
                                path.unlink()
                            results["archives_pruned"] += 1
                    except Exception:
                        continue  # Skip corrupted files

            # 3. Migrate outdated blobs
            if not dry_run:
                results["migrated"] = self.migrate_all()
            else:
                results["migrated"] = len(self.check_migrations())

            # 4. Update marker
            if not dry_run:
                _atomic_write(marker_path, today)

        finally:
            os.close(fd)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

        return results

    # --- Drift: Cross-Project Discovery ---

    def _get_drift_config(self) -> dict:
        """Load drift configuration from .claude/drift.json."""
        config_path = self.claude_dir / "drift.json"
        default_config = {
            "include_global": True,
            "include_siblings": True,
            "additional_paths": [],
            "scope_filter": ["always"],  # Only drift 'always' scope by default
        }
        if config_path.exists():
            try:
                user_config = json.loads(config_path.read_text())
                default_config.update(user_config)
            except Exception:
                pass
        return default_config

    def save_drift_config(self, config: dict) -> Path:
        """Save drift configuration."""
        path = self.claude_dir / "drift.json"
        _atomic_write(path, json.dumps(config, indent=2))
        return path

    def discover_reefs(self) -> list[dict]:
        """
        Discover nearby reefs for drift.

        Searches:
        1. ~/.claude/ (global reef)
        2. Sibling directories with .reef/ or .claude/
        3. Configured additional paths

        Returns list of reef info dicts with:
        - path: Path to reef directory
        - name: Project/reef name
        - source: 'global', 'sibling', or 'configured'
        - polip_count: Number of polips found
        """
        config = self._get_drift_config()
        reefs = []

        def _find_reef_dir(project_path: Path) -> Path | None:
            """Find reef directory, preferring .reef over .claude."""
            reef_dir = project_path / REEF_DIR
            if reef_dir.exists():
                return reef_dir
            legacy_dir = project_path / LEGACY_DIR
            if legacy_dir.exists():
                return legacy_dir
            return None

        # 1. Global reef (~/.claude/ or ~/.reef/)
        if config.get("include_global", True):
            global_claude = Path.home() / ".claude"
            if global_claude.exists():
                count = self._count_polips(global_claude)
                if count > 0:
                    reefs.append({
                        "path": global_claude,
                        "name": "~/.claude (global)",
                        "source": "global",
                        "polip_count": count,
                    })

        # 2. Sibling directories
        if config.get("include_siblings", True):
            parent = self.project_dir.parent
            for sibling in parent.iterdir():
                if not sibling.is_dir():
                    continue
                if sibling == self.project_dir:
                    continue
                if sibling.name.startswith("."):
                    continue
                sibling_reef = _find_reef_dir(sibling)
                if sibling_reef:
                    count = self._count_polips(sibling_reef)
                    if count > 0:
                        reefs.append({
                            "path": sibling_reef,
                            "name": sibling.name,
                            "source": "sibling",
                            "polip_count": count,
                        })

        # 3. Additional configured paths
        for path_str in config.get("additional_paths", []):
            path = Path(path_str).expanduser()
            if path.exists() and path.is_dir():
                reef_dir = _find_reef_dir(path)
                if not reef_dir:
                    # Check if path itself is a reef dir
                    if path.name in (REEF_DIR, LEGACY_DIR):
                        reef_dir = path
                if reef_dir and reef_dir.exists():
                    count = self._count_polips(reef_dir)
                    if count > 0:
                        reefs.append({
                            "path": reef_dir,
                            "name": path.name,
                            "source": "configured",
                            "polip_count": count,
                        })

        return reefs

    def _count_polips(self, claude_dir: Path) -> int:
        """Count polips in a .claude directory."""
        count = len(list(_iter_polip_files(claude_dir)))
        for subdir in KNOWN_SUBDIRS:
            subpath = claude_dir / subdir
            count += len(list(_iter_polip_files(subpath)))
        return count

    def list_drift_polips(self, scope_filter: list[str] = None) -> list[dict]:
        """
        List polips from discovered reefs that match drift criteria.

        Args:
            scope_filter: List of scopes to include (default: from config)

        Returns list of polip info dicts with:
        - reef_name: Source reef name
        - reef_path: Path to source .claude/
        - name: Polip name
        - subdir: Subdirectory (or None)
        - blob: The Blob object
        - key: Unique reference key (reef/subdir/name)
        """
        config = self._get_drift_config()
        scope_filter = scope_filter or config.get("scope_filter", ["always"])

        reefs = self.discover_reefs()
        polips = []

        for reef in reefs:
            reef_path = reef["path"]
            reef_name = reef["name"]

            # Scan root and subdirs
            for subdir in [None, *KNOWN_SUBDIRS]:
                if subdir:
                    search_dir = reef_path / subdir
                else:
                    search_dir = reef_path

                if not search_dir.exists():
                    continue

                for path in _iter_polip_files(search_dir):
                    try:
                        blob = Blob.load(path)
                        # Filter by scope
                        if blob.scope.value not in scope_filter:
                            continue

                        name = _polip_name_from_path(path)
                        key = f"{reef_name}/{subdir}/{name}" if subdir else f"{reef_name}/{name}"

                        polips.append({
                            "reef_name": reef_name,
                            "reef_path": reef_path,
                            "name": name,
                            "subdir": subdir,
                            "blob": blob,
                            "key": key,
                            "path": path,
                        })
                    except Exception:
                        continue

        return polips

    def pull_polip(self, key: str) -> Optional[Path]:
        """
        Pull (copy) a polip from another reef into this one.

        Args:
            key: Reference key in format "reef/[subdir/]name"

        Returns:
            Path to the copied polip, or None if not found
        """
        # Find the polip by key
        drift_polips = self.list_drift_polips(scope_filter=None)  # All scopes for pull

        for polip_info in drift_polips:
            if polip_info["key"] == key:
                blob = polip_info["blob"]
                name = polip_info["name"]
                subdir = polip_info["subdir"]

                # Update the blob for local context
                blob.updated = datetime.now()

                # Sprout into local reef
                return self.sprout(blob, name, subdir)

        return None

    def inject_context_with_drift(self) -> str:
        """
        Generate XML context including drift polips.

        Extends inject_context() to include global/cross-project polips.
        """
        relevant = self.surface_relevant()

        # Add drift polips
        drift_polips = self.list_drift_polips()
        for polip_info in drift_polips:
            # Don't duplicate if already in local reef
            local_blob = self.get(polip_info["name"], polip_info["subdir"])
            if local_blob is None:
                relevant.append(polip_info["blob"])

        if not relevant:
            return ""

        # Build composite XML
        root = ET.Element("glob", project=str(self.project_dir.name))

        for blob in relevant[:10]:  # Limit to top 10
            blob_el = ET.fromstring(blob.to_xml())
            root.append(blob_el)

        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode")
