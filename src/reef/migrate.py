"""
Migrate .blob.xml to .reef format with backup and rollback.

Usage:
    reef migrate --to-reef      # Convert all .blob.xml to .reef
    reef migrate --dry-run      # Show what would be converted
    reef migrate --rollback     # Restore from last backup
    reef migrate --list-backups # Show available backups
"""

import shutil
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

from reef.format import Polip


BACKUP_DIR = ".claude/.migrate-backups"


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


def create_backup(root: Path) -> Path:
    """Create backup of all .blob.xml files before migration.

    Returns path to backup directory.
    """
    claude_dir = root / ".claude"
    backup_base = root / BACKUP_DIR
    backup_base.mkdir(parents=True, exist_ok=True)

    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = backup_base / f"backup-{timestamp}"
    backup_dir.mkdir()

    # Copy all .blob.xml files preserving directory structure
    for blob_path in claude_dir.rglob("*.blob.xml"):
        rel_path = blob_path.relative_to(claude_dir)
        dest_path = backup_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(blob_path, dest_path)

    # Write manifest
    manifest = backup_dir / "MANIFEST"
    manifest.write_text(f"Backup created: {timestamp}\nSource: {claude_dir}\n")

    return backup_dir


def list_backups(root: Path) -> list[tuple[Path, str]]:
    """List available backups.

    Returns list of (backup_path, timestamp) tuples.
    """
    backup_base = root / BACKUP_DIR
    if not backup_base.exists():
        return []

    backups = []
    for backup_dir in sorted(backup_base.iterdir(), reverse=True):
        if backup_dir.is_dir() and backup_dir.name.startswith("backup-"):
            timestamp = backup_dir.name.replace("backup-", "")
            backups.append((backup_dir, timestamp))

    return backups


def rollback(root: Path, backup_path: Path = None) -> int:
    """Restore from backup.

    If backup_path is None, uses most recent backup.
    Returns number of files restored.
    """
    claude_dir = root / ".claude"

    if backup_path is None:
        backups = list_backups(root)
        if not backups:
            raise ValueError("No backups found")
        backup_path = backups[0][0]

    if not backup_path.exists():
        raise ValueError(f"Backup not found: {backup_path}")

    restored = 0
    for blob_path in backup_path.rglob("*.blob.xml"):
        rel_path = blob_path.relative_to(backup_path)
        dest_path = claude_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(blob_path, dest_path)
        restored += 1

    return restored


def migrate_reef(root: Path, dry_run: bool = True, with_backup: bool = True) -> list[tuple[Path, Path]]:
    """Migrate all .blob.xml files to .reef format.

    Args:
        root: Project root directory
        dry_run: If True, don't actually modify files
        with_backup: If True, create backup before migrating

    Returns list of (old_path, new_path) tuples.
    """
    claude_dir = root / ".claude"
    if not claude_dir.exists():
        return []

    # Create backup before migration
    backup_path = None
    if not dry_run and with_backup:
        blob_files = list(claude_dir.rglob("*.blob.xml"))
        if blob_files:
            backup_path = create_backup(root)
            print(f"Created backup at: {backup_path}")

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
            if not dry_run and backup_path:
                print(f"Rollback available: reef migrate --rollback")

    return migrations


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Migrate .blob.xml to .reef with backup/rollback")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated")
    parser.add_argument("--execute", "-x", action="store_true", help="Actually perform migration")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup before migration")
    parser.add_argument("--rollback", action="store_true", help="Restore from most recent backup")
    parser.add_argument("--rollback-from", metavar="PATH", help="Restore from specific backup")
    parser.add_argument("--list-backups", action="store_true", help="List available backups")
    args = parser.parse_args()

    root = Path.cwd()

    # List backups
    if args.list_backups:
        backups = list_backups(root)
        if not backups:
            print("No backups found")
        else:
            print("Available backups:\n")
            for backup_path, timestamp in backups:
                file_count = len(list(backup_path.rglob("*.blob.xml")))
                print(f"  {timestamp}  ({file_count} files)")
                print(f"    Path: {backup_path}")
                print()
        return

    # Rollback
    if args.rollback or args.rollback_from:
        backup_path = Path(args.rollback_from) if args.rollback_from else None
        try:
            restored = rollback(root, backup_path)
            print(f"Restored {restored} files from backup")
        except ValueError as e:
            print(f"Rollback failed: {e}")
        return

    # Normal migration
    dry_run = not args.execute
    with_backup = not args.no_backup

    migrations = migrate_reef(root, dry_run=dry_run, with_backup=with_backup)

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
        print("(Backup created automatically unless --no-backup)")
    else:
        print("\nTo rollback: reef migrate --rollback")


if __name__ == "__main__":
    main()
