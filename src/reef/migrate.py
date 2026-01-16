"""
Migrate .blob.xml to .reef format.

Usage:
    reef migrate --to-reef      # Convert all .blob.xml to .reef
    reef migrate --dry-run      # Show what would be converted
"""

import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from reef.format import Polip


def blob_to_polip(blob_path: Path) -> Polip:
    """Convert a .blob.xml file to a Polip."""
    root = ET.parse(blob_path).getroot()

    # Extract identity
    polip_type = root.get("type", "context")
    scope = root.get("scope", "project")
    status = root.get("status")
    updated_str = root.get("updated", date.today().isoformat())

    try:
        updated = date.fromisoformat(updated_str)
    except ValueError:
        updated = date.today()

    # ID from filename
    polip_id = blob_path.stem.replace(".blob", "")

    # Summary
    summary_el = root.find("summary")
    summary = summary_el.text.strip() if summary_el is not None and summary_el.text else ""

    # Facts
    facts = []
    facts_el = root.find("facts")
    if facts_el is not None:
        for fact_el in facts_el.findall("fact"):
            if fact_el.text:
                facts.append(fact_el.text.strip())

    # Decisions
    decisions = []
    decisions_el = root.find("decisions")
    if decisions_el is not None:
        for dec_el in decisions_el.findall("decision"):
            if dec_el.text:
                decisions.append(dec_el.text.strip())

    # Questions
    questions = []
    questions_el = root.find("questions")
    if questions_el is not None:
        for q_el in questions_el.findall("question"):
            if q_el.text:
                questions.append(q_el.text.strip())

    # Next steps
    steps = []
    next_el = root.find("next")
    if next_el is not None:
        for step_el in next_el.findall("step"):
            if step_el.text:
                done = step_el.get("status") == "done"
                steps.append((done, step_el.text.strip()))

    # Context
    context = []
    ctx_el = root.find("context")
    if ctx_el is not None and ctx_el.text:
        # Split into lines for context
        for line in ctx_el.text.strip().split("\n"):
            line = line.strip()
            if line:
                context.append(line)

    # Links (from related element)
    links = []
    related_el = root.find("related")
    if related_el is not None:
        for link_el in related_el.findall("link"):
            if link_el.text:
                links.append(link_el.text.strip())

    return Polip(
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


def migrate_reef(root: Path, dry_run: bool = True) -> list[tuple[Path, Path]]:
    """Migrate all .blob.xml files to .reef format.

    Returns list of (old_path, new_path) tuples.
    """
    claude_dir = root / ".claude"
    if not claude_dir.exists():
        return []

    migrations = []

    for blob_path in claude_dir.rglob("*.blob.xml"):
        try:
            polip = blob_to_polip(blob_path)

            # Determine new path
            subdir = claude_dir / f"{polip.type}s"
            new_path = subdir / f"{polip.id}.reef"

            if not dry_run:
                subdir.mkdir(parents=True, exist_ok=True)
                new_path.write_text(polip.to_reef())

            migrations.append((blob_path, new_path))

        except Exception as e:
            print(f"Failed to migrate {blob_path}: {e}")

    return migrations


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Migrate .blob.xml to .reef")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated")
    parser.add_argument("--execute", "-x", action="store_true", help="Actually perform migration")
    args = parser.parse_args()

    root = Path.cwd()
    dry_run = not args.execute

    migrations = migrate_reef(root, dry_run=dry_run)

    if not migrations:
        print("No .blob.xml files found")
        return

    print(f"{'Would migrate' if dry_run else 'Migrated'} {len(migrations)} files:\n")

    for old, new in migrations:
        old_rel = old.relative_to(root)
        new_rel = new.relative_to(root)
        print(f"  {old_rel}")
        print(f"    -> {new_rel}")
        print()

    if dry_run:
        print("Run with --execute to perform migration")


if __name__ == "__main__":
    main()
