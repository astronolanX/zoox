"""
zoox CLI - Symbiotic memory for AI.

Terminology:
  polyp   = individual memory unit (was: blob)
  reef    = project colony (was: glob)
  spawn   = create polyp
  surface = bring polyp from depth
  sink    = archive to deep reef
  drift   = cross-project spread
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


# Optimal .gitignore for team workflows
GITIGNORE_TEMPLATE = """\
# zoox - Polyp memory system
# Commit constraints and decisions, ignore session-scoped polyps

# Session-scoped polyps (ephemeral, per-session)
.claude/context.blob.xml
.claude/contexts/

# Index is generated (can be rebuilt)
.claude/index.json

# Archive contains decomposed polyps
.claude/archive/

# Snapshots are local state
.claude/snapshots/

# Keep constraints (bedrock rules) - committed
# !.claude/constraints/

# Keep decisions (architectural records) - committed
# !.claude/decisions/

# Keep facts (preserved knowledge) - committed
# !.claude/facts/

# Thread polyps are typically session-specific
# Uncomment to commit active threads:
# !.claude/threads/
"""


def cmd_init(args):
    """Initialize zoox in the current project."""
    from zoox.blob import Glob

    project_dir = Path.cwd()
    claude_dir = project_dir / ".claude"

    # Create .claude directory if needed
    if not claude_dir.exists():
        claude_dir.mkdir(parents=True)
        print(f"Created {claude_dir}")
    else:
        print(f"Directory {claude_dir} already exists")

    # Generate .gitignore if requested
    if args.gitignore:
        gitignore_path = project_dir / ".gitignore"

        if gitignore_path.exists() and not args.force:
            # Check if zoox section already exists
            content = gitignore_path.read_text()
            if "zoox" in content.lower() or ".claude/" in content:
                print("Existing .gitignore already has zoox/claude entries")
                print("Use --force to overwrite, or manually add entries")
                return

            # Append to existing
            if args.append:
                with open(gitignore_path, "a") as f:
                    f.write("\n" + GITIGNORE_TEMPLATE)
                print(f"Appended zoox entries to {gitignore_path}")
            else:
                print(f"File {gitignore_path} exists. Use --append to add entries")
                return
        else:
            # Create new or overwrite
            gitignore_path.write_text(GITIGNORE_TEMPLATE)
            print(f"Created {gitignore_path} with team workflow settings")

    # Initialize index
    glob = Glob(project_dir)
    count = glob.rebuild_index()
    print(f"Indexed {count} existing polyp(s)")

    print("\nzoox initialized!")
    print("  Use 'zoox sprout' to create polyps")
    print("  Use 'zoox reef' to view reef health")


def cmd_sprout(args):
    """Create a new polyp (spawn)."""
    from zoox.blob import Glob, Blob, BlobType, BlobScope, BlobStatus, KNOWN_SUBDIRS

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    # Parse type (context not allowed - auto-created by persist hook)
    try:
        blob_type = BlobType(args.type)
    except ValueError:
        valid = ", ".join(t.value for t in BlobType if t != BlobType.CONTEXT)
        print(f"Invalid type: {args.type}", file=sys.stderr)
        print(f"Valid types: {valid}", file=sys.stderr)
        sys.exit(1)

    if blob_type == BlobType.CONTEXT:
        print("context polyps are auto-created by the persist hook", file=sys.stderr)
        print("Use: thread, decision, constraint, or fact", file=sys.stderr)
        sys.exit(1)

    # Derive scope from type (no user choice - cleaner API)
    scope_map = {
        BlobType.CONSTRAINT: BlobScope.ALWAYS,
        BlobType.THREAD: BlobScope.PROJECT,
        BlobType.DECISION: BlobScope.PROJECT,
        BlobType.FACT: BlobScope.PROJECT,
    }
    scope = scope_map[blob_type]

    # Parse status (only for threads)
    status = None
    if args.status:
        if blob_type != BlobType.THREAD:
            print("--status only applies to thread polyps", file=sys.stderr)
            sys.exit(1)
        try:
            status = BlobStatus(args.status)
        except ValueError:
            valid = ", ".join(s.value for s in BlobStatus)
            print(f"Invalid status: {args.status}", file=sys.stderr)
            print(f"Valid statuses: {valid}", file=sys.stderr)
            sys.exit(1)
    elif blob_type == BlobType.THREAD:
        status = BlobStatus.ACTIVE  # default for threads

    # Create polyp
    blob = Blob(
        type=blob_type,
        summary=args.summary,
        scope=scope,
        status=status,
    )

    # Determine subdirectory based on type
    subdir_map = {
        BlobType.THREAD: "threads",
        BlobType.DECISION: "decisions",
        BlobType.CONSTRAINT: "constraints",
        BlobType.CONTEXT: "contexts",
        BlobType.FACT: "facts",
    }
    subdir = args.dir or subdir_map.get(blob_type)

    # Generate name from summary (kebab-case, max 30 chars)
    name = args.name
    if not name:
        name = args.summary.lower()
        name = "".join(c if c.isalnum() or c == " " else "" for c in name)
        name = "-".join(name.split())[:30]

    # Write polyp
    path = glob.sprout(blob, name, subdir)
    rel_path = path.relative_to(project_dir)
    print(f"Spawned: {rel_path}")


def cmd_decompose(args):
    """Archive stale polyps (sink)."""
    from zoox.blob import Glob, BlobScope, KNOWN_SUBDIRS

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    # Find stale session polyps
    days = args.days or 7
    threshold = datetime.now() - timedelta(days=days)

    stale: list[tuple[Path, str, object, str | None]] = []

    # Check root and all subdirs
    for subdir in [None, *KNOWN_SUBDIRS]:
        for name, blob in glob.list_blobs(subdir):
            # Only session-scoped polyps are candidates for decomposition
            if blob.scope != BlobScope.SESSION:
                continue
            if blob.updated < threshold:
                if subdir:
                    path = glob.claude_dir / subdir / f"{name}.blob.xml"
                else:
                    path = glob.claude_dir / f"{name}.blob.xml"
                stale.append((path, name, blob, subdir))

    if not stale:
        print(f"No stale session polyps (>{days} days old)")
        return

    print(f"Found {len(stale)} stale session polyp(s):")
    for path, name, blob, subdir in stale:
        rel_path = path.relative_to(project_dir)
        age = (datetime.now() - blob.updated).days
        print(f"  {rel_path} ({age}d old)")
        print(f"    {blob.summary[:60]}")

    if args.dry_run:
        print("\nRun without --dry-run to sink")
        return

    # Archive via Glob.decompose() (preserves blobs in archive/)
    print()
    for path, name, blob, subdir in stale:
        glob.decompose(name, subdir)
        rel_path = path.relative_to(project_dir)
        print(f"Sunk: {rel_path}")

    print(f"\nDecomposed {len(stale)} polyp(s)")


def cmd_migrate(args):
    """Migrate polyps to current schema version."""
    from zoox.blob import Glob, BLOB_VERSION

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    outdated = glob.check_migrations()

    if not outdated:
        print(f"All polyps are at current version (v{BLOB_VERSION})")
        return

    if args.dry_run:
        print(f"Found {len(outdated)} polyp(s) needing migration:")
        for path, blob in outdated:
            print(f"  {path.name} (v{blob.version} -> v{BLOB_VERSION})")
        print("\nRun without --dry-run to migrate")
        return

    count = glob.migrate_all()
    print(f"Migrated {count} polyp(s) to v{BLOB_VERSION}")


def cmd_list(args):
    """Show reef health and diagnostics."""
    from zoox.blob import Glob, Blob, BlobType, BlobScope, BlobStatus, BLOB_VERSION, KNOWN_SUBDIRS

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    # Collect all polyps with their paths
    all_blobs: list[tuple[Path, str, Blob]] = []

    # Root level polyps
    for name, blob in glob.list_blobs():
        path = glob.claude_dir / f"{name}.blob.xml"
        all_blobs.append((path, name, blob))

    # Subdirectory polyps
    for subdir in KNOWN_SUBDIRS:
        for name, blob in glob.list_blobs(subdir):
            path = glob.claude_dir / subdir / f"{name}.blob.xml"
            all_blobs.append((path, name, blob))

    if not all_blobs:
        print("No polyps found in reef (.claude/)")
        print("Polyps are XML context files that persist across sessions.")
        return

    # Aggregate stats
    type_counts = defaultdict(int)
    scope_counts = defaultdict(int)
    status_counts = defaultdict(int)
    version_counts = defaultdict(int)
    total_tokens = 0
    needs_migration = []
    stale_sessions = []
    active_threads = []
    all_files_referenced = []
    missing_files = []

    now = datetime.now()
    stale_threshold = now - timedelta(days=7)

    for path, name, blob in all_blobs:
        type_counts[blob.type.value] += 1
        scope_counts[blob.scope.value] += 1
        if blob.status:
            status_counts[blob.status.value] += 1
        version_counts[blob.version] += 1

        # Estimate tokens (~200 per polyp + content)
        xml_len = len(blob.to_xml())
        tokens = max(200, xml_len // 4)  # Rough estimate
        total_tokens += tokens

        # Track migrations needed
        if blob.needs_migration():
            needs_migration.append((path, name, blob))

        # Track stale sessions
        if blob.scope == BlobScope.SESSION and blob.updated < stale_threshold:
            stale_sessions.append((name, blob))

        # Track active threads (currents)
        if blob.type == BlobType.THREAD and blob.status == BlobStatus.ACTIVE:
            active_threads.append((name, blob))

        # Track file references
        for f in blob.files:
            all_files_referenced.append(f)
            # Check if file exists (expand ~ and check)
            file_path = Path(f).expanduser()
            if not file_path.is_absolute():
                file_path = project_dir / f
            if not file_path.exists():
                missing_files.append(f)

    # Output
    project_name = project_dir.name
    print(f"Reef Health: {project_name}")
    print("=" * 45)
    print()

    # Population summary
    print(f"Population: {len(all_blobs)} polyp(s) (~{total_tokens:,} tokens)")

    # Type breakdown
    type_str = "  "
    for t in ["constraint", "thread", "decision", "context", "fact"]:
        if type_counts[t]:
            type_str += f"{t}: {type_counts[t]}  "
    if type_str.strip():
        print(type_str)

    # Scope breakdown
    scope_str = "  "
    for s in ["always", "project", "session"]:
        if scope_counts[s]:
            scope_str += f"{s}: {scope_counts[s]}  "
    if scope_str.strip():
        print(scope_str)

    print()

    # Active threads (currents)
    if active_threads:
        print(f"Active Currents: {len(active_threads)}")
        for name, blob in active_threads[:3]:
            next_count = len(blob.next_steps)
            next_str = f" ({next_count} next steps)" if next_count else ""
            print(f"  -> {blob.summary[:50]}{next_str}")
        if len(active_threads) > 3:
            print(f"  ... and {len(active_threads) - 3} more")
        print()

    # Schema health
    if needs_migration:
        print(f"Schema: ! {len(needs_migration)} polyp(s) need migration")
        print(f"  Run: zoox migrate")
    else:
        print(f"Schema: OK all v{BLOB_VERSION}")
    print()

    # Staleness
    if stale_sessions:
        print(f"Staleness: ! {len(stale_sessions)} session polyp(s) >7 days old")
        for name, blob in stale_sessions[:2]:
            print(f"  -> {name} (updated {blob.updated.strftime('%Y-%m-%d')})")
    else:
        session_count = scope_counts.get("session", 0)
        if session_count:
            print(f"Staleness: OK {session_count} session polyp(s) all recent")
    print()

    # File references
    if all_files_referenced:
        if missing_files:
            print(f"File References: ! {len(missing_files)}/{len(all_files_referenced)} missing")
            for f in missing_files[:3]:
                print(f"  -> {f}")
        else:
            print(f"File References: OK {len(all_files_referenced)} file(s) all exist")
        print()

    # Injection impact
    # Estimate ~0.5ms per 100 tokens + 30ms baseline
    est_ms = 30 + (total_tokens // 200)
    print(f"Surfacing Impact: ~{total_tokens:,} tokens / ~{est_ms}ms per session")
    print()

    # Cache stats
    cache = glob.cache_stats()
    if cache["total"] > 0:
        print(f"Cache: {cache['hits']}/{cache['total']} hits ({cache['hit_rate']:.0f}%)")
        print()

    # Suggestions
    suggestions = []

    if needs_migration:
        suggestions.append(f"Run `zoox migrate` to update {len(needs_migration)} polyp(s)")

    for name, blob in stale_sessions:
        suggestions.append(f"Sink stale session '{name}' (updated {blob.updated.strftime('%b %d')})")

    for name, blob in active_threads:
        if len(blob.next_steps) > 5:
            suggestions.append(f"Current '{name}' has {len(blob.next_steps)} next steps - consider splitting")

    if not type_counts.get("constraint"):
        suggestions.append("No bedrock defined - consider adding project constraints")

    if len(active_threads) > 3:
        suggestions.append(f"{len(active_threads)} active currents - consider completing some")

    if missing_files:
        suggestions.append(f"Update or remove {len(missing_files)} stale file reference(s)")

    if suggestions:
        print("Suggestions:")
        for s in suggestions[:5]:
            print(f"  -> {s}")
    else:
        print("Suggestions: None - reef looks healthy!")


def cmd_cleanup(args):
    """Session-start cleanup with swarm-safe locking."""
    from zoox.blob import Glob

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    results = glob.cleanup_session(
        archive_days=args.archive_days or 30,
        dry_run=args.dry_run,
    )

    if results["skipped"]:
        print("Cleanup: Already cleaned today (skipped)")
        return

    if results["locked"]:
        print("Cleanup: Another agent is cleaning (skipped)")
        return

    total = results["sessions_pruned"] + results["archives_pruned"] + results["migrated"]

    if total == 0:
        print("Cleanup: Nothing to clean")
        return

    if args.dry_run:
        print("Cleanup (dry-run):")
    else:
        print("Cleanup:")

    if results["sessions_pruned"]:
        print(f"  Sessions pruned: {results['sessions_pruned']}")
    if results["archives_pruned"]:
        print(f"  Archives pruned: {results['archives_pruned']}")
    if results["migrated"]:
        print(f"  Polyps migrated: {results['migrated']}")

    if args.dry_run:
        print("\nRun without --dry-run to apply")


def cmd_status(args):
    """View or change polyp status."""
    from zoox.blob import Glob, BlobStatus, KNOWN_SUBDIRS

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    name = args.name

    # Find the blob - check all subdirs if not specified
    blob = None
    found_subdir = None

    if args.dir:
        blob = glob.get(name, subdir=args.dir)
        found_subdir = args.dir
    else:
        # Search known subdirs (threads first since status is most relevant there)
        search_order = ["threads", *[d for d in KNOWN_SUBDIRS if d != "threads"], None]
        for subdir in search_order:
            blob = glob.get(name, subdir=subdir)
            if blob:
                found_subdir = subdir
                break

    if not blob:
        print(f"Polyp '{name}' not found", file=sys.stderr)
        sys.exit(1)

    # If no new status, show current
    if not args.new_status:
        status_str = blob.status.value if blob.status else "none"
        print(f"{name}: {status_str}")
        if blob.blocked_by:
            print(f"  blocked by: {blob.blocked_by}")
        return

    # Parse new status
    try:
        new_status = BlobStatus(args.new_status)
    except ValueError:
        valid = ", ".join(s.value for s in BlobStatus if s != BlobStatus.ARCHIVED)
        print(f"Invalid status: {args.new_status}", file=sys.stderr)
        print(f"Valid statuses: {valid}", file=sys.stderr)
        sys.exit(1)

    if new_status == BlobStatus.ARCHIVED:
        print("Use 'zoox decompose' to archive polyps", file=sys.stderr)
        sys.exit(1)

    # Update status
    updated = glob.update_status(
        name,
        new_status,
        subdir=found_subdir,
        blocked_by=args.blocked_by if new_status == BlobStatus.BLOCKED else None,
    )

    if updated:
        old_status = blob.status.value if blob.status else "none"
        print(f"{name}: {old_status} -> {new_status.value}")
        if args.blocked_by and new_status == BlobStatus.BLOCKED:
            print(f"  blocked by: {args.blocked_by}")
    else:
        print(f"Failed to update '{name}'", file=sys.stderr)
        sys.exit(1)


def cmd_template(args):
    """Manage and use polyp templates."""
    from zoox.blob import Glob, BUILTIN_TEMPLATES

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    if args.action == "list":
        templates = glob.list_templates()
        if not templates:
            print("No templates available")
            return

        print(f"Templates ({len(templates)}):")
        for name, tmpl, is_builtin in templates:
            tag = "[built-in]" if is_builtin else "[custom]"
            desc = tmpl.get("description", "")[:50]
            print(f"  {name} {tag}")
            if desc:
                print(f"    {desc}")
        print()
        print("Usage: zoox template use <name> <title>")

    elif args.action == "use":
        if not args.template_name or not args.title:
            print("Usage: zoox template use <template-name> <title>", file=sys.stderr)
            sys.exit(1)

        path = glob.create_from_template(args.template_name, args.title)
        if path:
            rel_path = path.relative_to(project_dir)
            print(f"Created: {rel_path}")
        else:
            print(f"Template '{args.template_name}' not found", file=sys.stderr)
            sys.exit(1)

    elif args.action == "show":
        if not args.template_name:
            print("Usage: zoox template show <template-name>", file=sys.stderr)
            sys.exit(1)

        tmpl = glob.get_template(args.template_name)
        if not tmpl:
            print(f"Template '{args.template_name}' not found", file=sys.stderr)
            sys.exit(1)

        print(f"Template: {args.template_name}")
        print(f"  Type: {tmpl.get('type', 'thread')}")
        print(f"  Scope: {tmpl.get('scope', 'project')}")
        if tmpl.get('status'):
            print(f"  Status: {tmpl['status']}")
        print(f"  Summary: {tmpl.get('summary_template', '{title}')}")
        if tmpl.get('description'):
            print(f"  Description: {tmpl['description']}")
        if tmpl.get('next_steps'):
            print(f"  Next steps: {len(tmpl['next_steps'])} items")

    elif args.action == "create":
        from zoox.blob import PathTraversalError

        if not args.template_name:
            print("Usage: zoox template create <name> --type thread --summary 'Bug: {title}'", file=sys.stderr)
            sys.exit(1)

        # Check for collision with built-in
        if args.template_name in BUILTIN_TEMPLATES:
            print(f"Cannot override built-in template '{args.template_name}'", file=sys.stderr)
            sys.exit(1)

        # Build template from args
        template = {
            "type": args.type or "thread",
            "summary_template": args.summary or "{title}",
            "scope": args.scope or "project",
        }
        if args.status:
            template["status"] = args.status
        if args.description:
            template["description"] = args.description
        if args.next_steps:
            template["next_steps"] = args.next_steps.split("|")

        try:
            path = glob.save_template(args.template_name, template)
            rel_path = path.relative_to(project_dir)
            print(f"Created template: {rel_path}")
        except PathTraversalError:
            print(f"Invalid template name: '{args.template_name}' (path traversal not allowed)", file=sys.stderr)
            sys.exit(1)

    elif args.action == "delete":
        from zoox.blob import PathTraversalError

        if not args.template_name:
            print("Usage: zoox template delete <name>", file=sys.stderr)
            sys.exit(1)

        if args.template_name in BUILTIN_TEMPLATES:
            print(f"Cannot delete built-in template '{args.template_name}'", file=sys.stderr)
            sys.exit(1)

        try:
            if glob.delete_template(args.template_name):
                print(f"Deleted template: {args.template_name}")
            else:
                print(f"Template '{args.template_name}' not found", file=sys.stderr)
                sys.exit(1)
        except PathTraversalError:
            print(f"Invalid template name: '{args.template_name}' (path traversal not allowed)", file=sys.stderr)
            sys.exit(1)


def cmd_graph(args):
    """Visualize polyp relationships."""
    from zoox.blob import Glob

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    graph = glob.build_graph()

    if args.dot:
        # Output DOT format
        print(glob.to_dot())
        return

    # ASCII summary
    nodes = graph["nodes"]
    edges = graph["edges"]

    if not nodes:
        print("No polyps to graph")
        return

    print(f"Reef Graph: {len(nodes)} polyps, {len(edges)} connections")
    print()

    # Group by type
    by_type = {}
    for key, attrs in nodes.items():
        t = attrs["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append((key, attrs))

    # Print by type
    type_symbols = {
        "thread": "~",
        "decision": "+",
        "constraint": "!",
        "fact": ".",
        "context": "*",
    }

    for blob_type in ["constraint", "thread", "decision", "fact", "context"]:
        if blob_type not in by_type:
            continue
        items = by_type[blob_type]
        symbol = type_symbols.get(blob_type, "o")
        print(f"  [{symbol}] {blob_type} ({len(items)})")
        for key, attrs in items[:5]:
            status_str = f" [{attrs['status']}]" if attrs["status"] else ""
            print(f"      {key}{status_str}")
        if len(items) > 5:
            print(f"      ... and {len(items) - 5} more")
        print()

    # Print connections
    if edges:
        print("  Connections:")
        related = [e for e in edges if e[2] == "related"]
        file_shared = [e for e in edges if e[2].startswith("file:")]

        if related:
            print(f"    -> {len(related)} explicit link(s)")
            for src, dst, _ in related[:3]:
                print(f"       {src} -> {dst}")

        if file_shared:
            print(f"    -> {len(file_shared)} shared file(s)")

    if args.dot:
        print()
        print("Tip: zoox graph --dot | dot -Tpng -o reef.png")


def cmd_snapshot(args):
    """Manage reef snapshots."""
    from zoox.blob import Glob

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    if args.action == "create":
        path = glob.create_snapshot(name=args.name)
        rel_path = path.relative_to(project_dir)
        blob_count = len(glob.list_blobs()) + sum(len(glob.list_blobs(s)) for s in ["threads", "decisions", "constraints", "contexts", "facts"])
        print(f"Snapshot created: {rel_path}")
        print(f"  {blob_count} polyp(s) captured")

    elif args.action == "list":
        snapshots = glob.list_snapshots()
        if not snapshots:
            print("No snapshots found")
            return

        print(f"Snapshots ({len(snapshots)}):")
        for path, meta in snapshots[:10]:
            name_str = f" ({meta['name']})" if meta.get("name") else ""
            created = meta.get("created", "unknown")[:19]  # Trim microseconds
            print(f"  {path.stem}{name_str}")
            print(f"    {meta['blob_count']} polyps | {created}")

    elif args.action == "diff":
        if not args.snapshot_id:
            print("Usage: zoox snapshot diff <snapshot-id>", file=sys.stderr)
            sys.exit(1)

        # Find snapshot by prefix match
        snapshots = glob.list_snapshots()
        matches = [s for s in snapshots if args.snapshot_id in s[0].stem]

        if not matches:
            print(f"No snapshot matching '{args.snapshot_id}'", file=sys.stderr)
            sys.exit(1)
        if len(matches) > 1:
            print(f"Multiple snapshots match '{args.snapshot_id}':", file=sys.stderr)
            for path, _ in matches[:5]:
                print(f"  {path.stem}", file=sys.stderr)
            sys.exit(1)

        snapshot_path = matches[0][0]
        diff = glob.diff_snapshot(snapshot_path)

        name_str = f" ({diff['snapshot_name']})" if diff.get("snapshot_name") else ""
        print(f"Diff vs {snapshot_path.stem}{name_str}:")

        if diff["added"]:
            print(f"\n  + Added ({len(diff['added'])}):")
            for key in diff["added"][:5]:
                print(f"    {key}")
            if len(diff["added"]) > 5:
                print(f"    ... and {len(diff['added']) - 5} more")

        if diff["removed"]:
            print(f"\n  - Removed ({len(diff['removed'])}):")
            for key in diff["removed"][:5]:
                print(f"    {key}")
            if len(diff["removed"]) > 5:
                print(f"    ... and {len(diff['removed']) - 5} more")

        if diff["changed"]:
            print(f"\n  ~ Changed ({len(diff['changed'])}):")
            for key, changes in list(diff["changed"].items())[:5]:
                print(f"    {key}: {', '.join(changes)}")

        if not diff["added"] and not diff["removed"] and not diff["changed"]:
            print("  No changes")


def cmd_index(args):
    """Manage metadata index."""
    from zoox.blob import Glob, INDEX_VERSION

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    if args.rebuild:
        count = glob.rebuild_index()
        print(f"Index rebuilt: {count} polyp(s) indexed")
        return

    if args.search or args.type or args.scope or args.status:
        # Search mode - any filter triggers search
        results = glob.search_index(
            query=args.search if args.search else None,
            blob_type=args.type,
            scope=args.scope,
            status=args.status,
            limit=args.limit or 20,
        )

        if not results:
            print("No matches found")
            if args.search:
                print(f"  Query: '{args.search}'")
            return

        print(f"Search Results ({len(results)}):")
        print()
        for key, entry, score in results:
            type_tag = f"[{entry.get('type', '?')}]"
            scope_tag = f"[{entry.get('scope', '?')}]"
            status_str = f" ({entry.get('status')})" if entry.get('status') else ""
            # Show relevance score if query was provided
            score_str = f" [{score:.1f}]" if args.search else ""
            print(f"  {key} {type_tag} {scope_tag}{status_str}{score_str}")
            print(f"    {entry.get('summary', '')[:60]}")
        return

    # Default: show stats
    index = glob.get_index()
    blob_count = len(index.get("blobs", {}))

    print(f"Index v{INDEX_VERSION}")
    print(f"  Polyps indexed: {blob_count}")
    print(f"  Last updated: {index.get('updated', 'unknown')}")

    if args.stats and blob_count > 0:
        # Count by type and scope
        type_counts = {}
        scope_counts = {}
        for entry in index["blobs"].values():
            t = entry.get("type", "unknown")
            s = entry.get("scope", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
            scope_counts[s] = scope_counts.get(s, 0) + 1

        print("\nBy type:")
        for t, c in sorted(type_counts.items()):
            print(f"  {t}: {c}")

        print("\nBy scope:")
        for s, c in sorted(scope_counts.items()):
            print(f"  {s}: {c}")


def cmd_hook(args):
    """Claude Code hook integration."""
    import json
    import subprocess

    from zoox.blob import Glob, Blob, BlobType, BlobScope, KNOWN_SUBDIRS

    project_dir = Path.cwd()

    if args.action == "surface":
        # UserPromptSubmit hook: surface relevant polyps as XML
        glob = Glob(project_dir)

        # Use drift-aware surfacing if --drift flag or by default
        if args.drift:
            xml_output = glob.inject_context_with_drift()
        else:
            xml_output = glob.inject_context()

        if xml_output:
            # Output in format Claude Code hooks expect
            print(f"\n[GLOB]\n{xml_output}\n")

    elif args.action == "persist":
        # Stop hook: create/update context polyp with session state
        glob = Glob(project_dir)

        # Read transcript summary from stdin if provided (Claude Code may pipe it)
        summary = args.summary
        if not summary:
            summary = "Session context (auto-generated)"

        # Check for existing context blob
        existing = glob.get("context")

        if existing:
            # Update existing
            existing.summary = summary
            existing.updated = datetime.now()
            if args.files:
                existing.files = args.files.split(",")
            if args.next:
                existing.next_steps = args.next.split("|")
            path = glob.claude_dir / "context.blob.xml"
            existing.save(path)
        else:
            # Create new context blob
            blob = Blob(
                type=BlobType.CONTEXT,
                summary=summary,
                scope=BlobScope.SESSION,
                files=args.files.split(",") if args.files else [],
                next_steps=args.next.split("|") if args.next else [],
            )
            glob.sprout(blob, "context")

        if not args.quiet:
            print("Context persisted")

    elif args.action == "setup":
        # Generate Claude Code settings.json hook configuration
        config = {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "zoox hook surface"
                            }
                        ]
                    }
                ],
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "zoox hook persist"
                            }
                        ]
                    }
                ]
            }
        }

        if args.json:
            print(json.dumps(config, indent=2))
        else:
            print("Add to ~/.claude/settings.json:")
            print()
            print(json.dumps(config, indent=2))
            print()
            print("Or merge with existing hooks configuration.")

    elif args.action == "status":
        # Check hook health - is zoox properly configured?
        settings_path = Path.home() / ".claude" / "settings.json"

        print("Hook Status:")
        print()

        # Check if settings.json exists
        if not settings_path.exists():
            print("  settings.json: NOT FOUND")
            print("  Run: zoox hook setup")
            return

        try:
            settings = json.loads(settings_path.read_text())
            hooks = settings.get("hooks", {})

            # Check UserPromptSubmit
            upsub = hooks.get("UserPromptSubmit", [])
            has_surface = any(
                "zoox hook surface" in str(h)
                for h in upsub
            )
            print(f"  UserPromptSubmit (surface): {'✓' if has_surface else '✗'}")

            # Check Stop
            stop = hooks.get("Stop", [])
            has_persist = any(
                "zoox hook persist" in str(h)
                for h in stop
            )
            print(f"  Stop (persist): {'✓' if has_persist else '✗'}")

            # Check reef
            claude_dir = project_dir / ".claude"
            if claude_dir.exists():
                blob_count = len(list(claude_dir.glob("*.blob.xml")))
                for subdir in KNOWN_SUBDIRS:
                    subpath = claude_dir / subdir
                    if subpath.exists():
                        blob_count += len(list(subpath.glob("*.blob.xml")))
                print(f"  Reef: {blob_count} polyp(s)")
            else:
                print("  Reef: NOT INITIALIZED")
                print("  Run: zoox sprout thread 'Initial setup'")

        except json.JSONDecodeError:
            print("  settings.json: INVALID JSON")
            return


def cmd_drift(args):
    """Cross-project polyp discovery and sharing."""
    from zoox.blob import Glob, KNOWN_SUBDIRS

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    if args.action == "discover":
        # Find nearby reefs
        reefs = glob.discover_reefs()

        if not reefs:
            print("No nearby reefs found.")
            print()
            print("Drift searches for:")
            print("  - ~/.claude/ (global polyps)")
            print("  - Sibling directories with .claude/")
            print("  - Paths in .claude/drift.json")
            return

        print(f"Discovered Reefs ({len(reefs)}):")
        print()
        for reef in reefs:
            source_tag = f"[{reef['source']}]"
            print(f"  {reef['name']} {source_tag}")
            print(f"    {reef['polyp_count']} polyp(s)")
            print(f"    {reef['path']}")
            print()

    elif args.action == "list":
        # List polyps available for drift
        scope_filter = args.scope.split(",") if args.scope else None
        polyps = glob.list_drift_polyps(scope_filter=scope_filter)

        if not polyps:
            print("No drift polyps found.")
            if not args.scope:
                print("  (Only 'always' scope by default)")
                print("  Use --scope project,always to include more")
            return

        print(f"Drift Polyps ({len(polyps)}):")
        print()
        for p in polyps:
            scope_tag = f"[{p['blob'].scope.value}]"
            type_tag = f"[{p['blob'].type.value}]"
            print(f"  {p['key']} {scope_tag} {type_tag}")
            print(f"    {p['blob'].summary[:60]}")
        print()
        print("Pull with: zoox drift pull <key>")

    elif args.action == "pull":
        # Copy a polyp from another reef
        if not args.key:
            print("Usage: zoox drift pull <key>", file=sys.stderr)
            print("  Get keys from: zoox drift list", file=sys.stderr)
            sys.exit(1)

        path = glob.pull_polyp(args.key)
        if path:
            rel_path = path.relative_to(project_dir)
            print(f"Pulled: {rel_path}")
        else:
            print(f"Polyp not found: {args.key}", file=sys.stderr)
            print("  Get keys from: zoox drift list --scope always,project", file=sys.stderr)
            sys.exit(1)

    elif args.action == "config":
        # Show or update drift configuration
        config = glob._get_drift_config()

        if args.add_path:
            paths = config.get("additional_paths", [])
            if args.add_path not in paths:
                paths.append(args.add_path)
                config["additional_paths"] = paths
                glob.save_drift_config(config)
                print(f"Added: {args.add_path}")
            else:
                print(f"Already configured: {args.add_path}")
            return

        if args.remove_path:
            paths = config.get("additional_paths", [])
            if args.remove_path in paths:
                paths.remove(args.remove_path)
                config["additional_paths"] = paths
                glob.save_drift_config(config)
                print(f"Removed: {args.remove_path}")
            else:
                print(f"Not found: {args.remove_path}")
            return

        # Default: show config
        print("Drift Configuration:")
        print(f"  include_global: {config.get('include_global', True)}")
        print(f"  include_siblings: {config.get('include_siblings', True)}")
        print(f"  scope_filter: {config.get('scope_filter', ['always'])}")
        paths = config.get("additional_paths", [])
        if paths:
            print(f"  additional_paths:")
            for p in paths:
                print(f"    - {p}")
        else:
            print(f"  additional_paths: (none)")


def cmd_sync(args):
    """Check reef integrity and fix issues."""
    from zoox.blob import Glob

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    issues = glob.check_integrity()

    # Count total issues
    total_issues = sum(len(v) for v in issues.values())

    if total_issues == 0:
        print("Reef integrity: OK")
        print("  No issues found")
        return

    print(f"Reef integrity: {total_issues} issue(s) found")
    print()

    # Missing files
    if issues["missing_files"]:
        print(f"Missing Files ({len(issues['missing_files'])}):")
        for polyp_key, file_path in issues["missing_files"][:5]:
            print(f"  {polyp_key}")
            print(f"    -> {file_path}")
        if len(issues["missing_files"]) > 5:
            print(f"  ... and {len(issues['missing_files']) - 5} more")

        if args.fix:
            print()
            fixed = 0
            seen_keys = set()
            for polyp_key, _ in issues["missing_files"]:
                if polyp_key not in seen_keys:
                    if glob.fix_missing_files(polyp_key):
                        fixed += 1
                    seen_keys.add(polyp_key)
            print(f"  Fixed {fixed} polyp(s) - removed missing file refs")
        print()

    # Stale polyps
    if issues["stale_polyps"]:
        print(f"Stale Session Polyps ({len(issues['stale_polyps'])}):")
        for polyp_key, days_old in issues["stale_polyps"][:5]:
            print(f"  {polyp_key} ({days_old}d old)")
        if len(issues["stale_polyps"]) > 5:
            print(f"  ... and {len(issues['stale_polyps']) - 5} more")
        print("  Tip: Run `zoox sink` to archive stale session polyps")
        print()

    # Orphan index entries
    if issues["orphan_files"]:
        print(f"Orphan Index Entries ({len(issues['orphan_files'])}):")
        for key in issues["orphan_files"][:5]:
            print(f"  {key}")
        if len(issues["orphan_files"]) > 5:
            print(f"  ... and {len(issues['orphan_files']) - 5} more")

        if args.fix:
            glob.rebuild_index()
            print("  Fixed: Index rebuilt")
        else:
            print("  Tip: Run `zoox index --rebuild` to fix")
        print()

    # Broken refs
    if issues["broken_refs"]:
        print(f"Broken Related Refs ({len(issues['broken_refs'])}):")
        for polyp_key, ref in issues["broken_refs"][:5]:
            print(f"  {polyp_key} -> {ref}")
        if len(issues["broken_refs"]) > 5:
            print(f"  ... and {len(issues['broken_refs']) - 5} more")
        print()

    # Schema outdated
    if issues["schema_outdated"]:
        print(f"Schema Outdated ({len(issues['schema_outdated'])}):")
        for polyp_key in issues["schema_outdated"][:5]:
            print(f"  {polyp_key}")
        if len(issues["schema_outdated"]) > 5:
            print(f"  ... and {len(issues['schema_outdated']) - 5} more")

        if args.fix:
            count = glob.migrate_all()
            print(f"  Fixed: Migrated {count} polyp(s)")
        else:
            print("  Tip: Run `zoox migrate` to update")
        print()

    if not args.fix and total_issues > 0:
        print("Run `zoox sync --fix` to auto-fix where possible")


def main():
    parser = argparse.ArgumentParser(
        prog="zoox",
        description="Symbiotic memory for AI",
        epilog="polyp = memory unit | reef = colony | current = active thread | bedrock = constraint"
    )
    parser.add_argument("--version", "-V", action="version", version="zoox 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize zoox in current project",
        description="Set up zoox with .claude/ directory and optional .gitignore"
    )
    init_parser.add_argument("--gitignore", "-g", action="store_true",
                             help="Generate .gitignore for team workflows")
    init_parser.add_argument("--append", "-a", action="store_true",
                             help="Append to existing .gitignore instead of failing")
    init_parser.add_argument("--force", "-f", action="store_true",
                             help="Overwrite existing .gitignore")
    init_parser.set_defaults(func=cmd_init)

    # sprout (spawn)
    sprout_parser = subparsers.add_parser(
        "sprout",
        help="Spawn a new polyp",
        description="Spawn a new polyp into the reef (.claude/ directory)"
    )
    sprout_parser.add_argument("type", help="Polyp type: thread, decision, constraint, fact")
    sprout_parser.add_argument("summary", help="Brief summary of the polyp")
    sprout_parser.add_argument("--status", help="Status for currents: active, blocked, done, archived")
    sprout_parser.add_argument("--name", "-n", help="Polyp filename (default: derived from summary)")
    sprout_parser.add_argument("--dir", "-d", help="Subdirectory override (default: based on type)")
    sprout_parser.set_defaults(func=cmd_sprout)

    # list (reef)
    list_parser = subparsers.add_parser(
        "list",
        help="Show reef health and diagnostics",
        aliases=["reef"],
        description="Display population health and diagnostics for all polyps"
    )
    list_parser.set_defaults(func=cmd_list)

    # migrate
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Migrate polyps to current schema",
        description="Upgrade polyps to the current schema version"
    )
    migrate_parser.add_argument("--dry-run", action="store_true", help="Preview migrations without applying")
    migrate_parser.set_defaults(func=cmd_migrate)

    # decompose (sink)
    decompose_parser = subparsers.add_parser(
        "decompose",
        help="Sink stale session polyps",
        aliases=["sink"],
        description="Find and sink session-scoped polyps older than threshold"
    )
    decompose_parser.add_argument("--days", type=int, help="Age threshold in days (default: 7)")
    decompose_parser.add_argument("--dry-run", action="store_true", help="Preview without sinking")
    decompose_parser.set_defaults(func=cmd_decompose)

    # cleanup
    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="Session-start cleanup (swarm-safe)",
        description="Prune stale sessions, old archives, and migrate polyps. Uses lock file for swarm safety."
    )
    cleanup_parser.add_argument("--archive-days", type=int, help="Days before pruning archives (default: 30)")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    cleanup_parser.set_defaults(func=cmd_cleanup)

    # index
    index_parser = subparsers.add_parser(
        "index",
        help="Manage metadata index",
        description="Search, rebuild, or inspect the polyp metadata index."
    )
    index_parser.add_argument("--search", "-s", metavar="QUERY", help="Search polyp summaries")
    index_parser.add_argument("--type", "-t", help="Filter by type: thread, decision, constraint, fact, context")
    index_parser.add_argument("--scope", help="Filter by scope: always, project, session")
    index_parser.add_argument("--status", help="Filter by status: active, blocked, done, archived")
    index_parser.add_argument("--limit", "-n", type=int, help="Max results (default: 20)")
    index_parser.add_argument("--rebuild", action="store_true", help="Force full index rebuild")
    index_parser.add_argument("--stats", action="store_true", help="Show index statistics")
    index_parser.set_defaults(func=cmd_index)

    # status
    status_parser = subparsers.add_parser(
        "status",
        help="View or change polyp status",
        description="View current status or transition a polyp to a new status (active, blocked, done)."
    )
    status_parser.add_argument("name", help="Polyp name (without .blob.xml)")
    status_parser.add_argument("new_status", nargs="?", help="New status: active, blocked, done")
    status_parser.add_argument("--blocked-by", "-b", help="Reason for blocking (with 'blocked' status)")
    status_parser.add_argument("--dir", "-d", help="Subdirectory to search (default: auto-detect)")
    status_parser.set_defaults(func=cmd_status)

    # snapshot
    snapshot_parser = subparsers.add_parser(
        "snapshot",
        help="Manage reef snapshots",
        description="Create, list, and compare reef snapshots for tracking changes over time."
    )
    snapshot_parser.add_argument("action", choices=["create", "list", "diff"], help="Action to perform")
    snapshot_parser.add_argument("snapshot_id", nargs="?", help="Snapshot ID for diff (prefix match)")
    snapshot_parser.add_argument("--name", "-n", help="Name for new snapshot")
    snapshot_parser.set_defaults(func=cmd_snapshot)

    # graph
    graph_parser = subparsers.add_parser(
        "graph",
        help="Visualize polyp relationships",
        description="Show polyp graph with connections. Use --dot for Graphviz export."
    )
    graph_parser.add_argument("--dot", action="store_true", help="Output Graphviz DOT format")
    graph_parser.set_defaults(func=cmd_graph)

    # template
    template_parser = subparsers.add_parser(
        "template",
        help="Manage and use polyp templates",
        description="List, show, use, create, or delete templates for polyp creation."
    )
    template_parser.add_argument("action", choices=["list", "use", "show", "create", "delete"], help="Action to perform")
    template_parser.add_argument("template_name", nargs="?", help="Template name")
    template_parser.add_argument("title", nargs="?", help="Title for new polyp (with 'use')")
    template_parser.add_argument("--type", "-t", help="Polyp type for create: thread, decision, constraint, fact")
    template_parser.add_argument("--summary", "-s", help="Summary template with {title} placeholder")
    template_parser.add_argument("--scope", help="Scope: project, session, always")
    template_parser.add_argument("--status", help="Status for threads: active, blocked, done")
    template_parser.add_argument("--description", "-d", help="Template description")
    template_parser.add_argument("--next-steps", help="Pipe-separated next steps template")
    template_parser.set_defaults(func=cmd_template)

    # hook (Claude Code integration)
    hook_parser = subparsers.add_parser(
        "hook",
        help="Claude Code hook integration",
        description="Commands for Claude Code hook events (UserPromptSubmit, Stop)."
    )
    hook_parser.add_argument(
        "action",
        choices=["surface", "persist", "setup", "status"],
        help="surface: output XML context | persist: save session state | setup: generate config | status: check health"
    )
    hook_parser.add_argument("--summary", "-s", help="Session summary (for persist)")
    hook_parser.add_argument("--files", "-f", help="Comma-separated file list (for persist)")
    hook_parser.add_argument("--next", "-n", help="Pipe-separated next steps (for persist)")
    hook_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output (for persist)")
    hook_parser.add_argument("--json", action="store_true", help="Output raw JSON (for setup)")
    hook_parser.add_argument("--drift", action="store_true", help="Include drift polyps (for surface)")
    hook_parser.set_defaults(func=cmd_hook)

    # drift (cross-project discovery)
    drift_parser = subparsers.add_parser(
        "drift",
        help="Cross-project polyp discovery",
        description="Discover and share polyps across projects (global, siblings, configured paths)."
    )
    drift_parser.add_argument(
        "action",
        choices=["discover", "list", "pull", "config"],
        help="discover: find reefs | list: show drift polyps | pull: copy polyp | config: settings"
    )
    drift_parser.add_argument("key", nargs="?", help="Polyp key for pull (from 'drift list')")
    drift_parser.add_argument("--scope", help="Scope filter: always,project,session (comma-separated)")
    drift_parser.add_argument("--add-path", help="Add path to drift config")
    drift_parser.add_argument("--remove-path", help="Remove path from drift config")
    drift_parser.set_defaults(func=cmd_drift)

    # sync (integrity check)
    sync_parser = subparsers.add_parser(
        "sync",
        help="Check reef integrity",
        description="Scan for missing files, stale polyps, broken refs, and other integrity issues."
    )
    sync_parser.add_argument("--fix", action="store_true", help="Auto-fix issues where possible")
    sync_parser.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
