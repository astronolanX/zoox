"""
reef CLI - Symbiotic memory for AI.

Terminology:
  polip   = individual memory unit (was: blob)
  reef    = project colony (was: glob)
  spawn   = create polip
  surface = bring polip from depth
  sink    = archive to deep reef
  drift   = cross-project spread
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


# Optimal .gitignore for team workflows
GITIGNORE_TEMPLATE = """\
# reef - Polip memory system
# Commit constraints and decisions, ignore session-scoped polips

# Session-scoped polips (ephemeral, per-session)
.claude/context.blob.xml
.claude/contexts/

# Index is generated (can be rebuilt)
.claude/index.json

# Archive contains decomposed polips
.claude/archive/

# Snapshots are local state
.claude/snapshots/

# Keep constraints (bedrock rules) - committed
# !.claude/constraints/

# Keep decisions (architectural records) - committed
# !.claude/decisions/

# Keep facts (preserved knowledge) - committed
# !.claude/facts/

# Thread polips are typically session-specific
# Uncomment to commit active threads:
# !.claude/threads/
"""


def cmd_init(args):
    """Initialize reef in the current project."""
    from reef.blob import Glob

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
            # Check if reef section already exists
            content = gitignore_path.read_text()
            if "reef" in content.lower() or ".claude/" in content:
                print("Existing .gitignore already has reef/claude entries")
                print("Use --force to overwrite, or manually add entries")
                return

            # Append to existing
            if args.append:
                with open(gitignore_path, "a") as f:
                    f.write("\n" + GITIGNORE_TEMPLATE)
                print(f"Appended reef entries to {gitignore_path}")
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
    print(f"Indexed {count} existing polip(s)")

    print("\nreef initialized!")
    print("  Use 'reef sprout' to create polips")
    print("  Use 'reef reef' to view reef health")

    # Update statusline
    glob.write_status()


def cmd_sprout(args):
    """Create a new polip (spawn)."""
    from reef.blob import Glob, Blob, BlobType, BlobScope, BlobStatus, KNOWN_SUBDIRS

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
        print("context polips are auto-created by the persist hook", file=sys.stderr)
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
            print("--status only applies to thread polips", file=sys.stderr)
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

    # Create polip
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

    # Write polip
    path = glob.sprout(blob, name, subdir)
    rel_path = path.relative_to(project_dir)
    print(f"Spawned: {rel_path}")

    # Update statusline
    glob.write_status()


def cmd_decompose(args):
    """Archive stale polips (sink)."""
    from reef.blob import Glob, BlobScope, KNOWN_SUBDIRS

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    # Find stale session polips
    days = args.days or 7
    threshold = datetime.now() - timedelta(days=days)

    stale: list[tuple[Path, str, object, str | None]] = []

    # Check root and all subdirs
    for subdir in [None, *KNOWN_SUBDIRS]:
        for name, blob in glob.list_blobs(subdir):
            # Only session-scoped polips are candidates for decomposition
            if blob.scope != BlobScope.SESSION:
                continue
            if blob.updated < threshold:
                if subdir:
                    path = glob.claude_dir / subdir / f"{name}.blob.xml"
                else:
                    path = glob.claude_dir / f"{name}.blob.xml"
                stale.append((path, name, blob, subdir))

    if not stale:
        print(f"No stale session polips (>{days} days old)")
        return

    print(f"Found {len(stale)} stale session polip(s):")
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

    print(f"\nDecomposed {len(stale)} polip(s)")


def cmd_migrate(args):
    """Migrate polips to current schema version."""
    from reef.blob import Glob, BLOB_VERSION

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    outdated = glob.check_migrations()

    if not outdated:
        print(f"All polips are at current version (v{BLOB_VERSION})")
        return

    if args.dry_run:
        print(f"Found {len(outdated)} polip(s) needing migration:")
        for path, blob in outdated:
            print(f"  {path.name} (v{blob.version} -> v{BLOB_VERSION})")
        print("\nRun without --dry-run to migrate")
        return

    count = glob.migrate_all()
    print(f"Migrated {count} polip(s) to v{BLOB_VERSION}")


def cmd_format(args):
    """Manage polip file formats (XML vs .reef)."""
    from reef.blob import Blob
    from reef.sexpr import blob_to_sexpr, compare_formats

    project_dir = Path.cwd()
    claude_dir = project_dir / ".claude"

    if not claude_dir.exists():
        print("No .claude/ directory found")
        sys.exit(1)

    # Find all polip files
    xml_files = list(claude_dir.rglob("*.blob.xml"))
    reef_files = list(claude_dir.rglob("*.reef"))

    if args.stats:
        # Show format statistics
        print("=== Format Statistics ===")
        print(f"XML files:  {len(xml_files)}")
        print(f".reef files: {len(reef_files)}")

        if xml_files:
            total_xml_tokens = 0
            total_reef_tokens = 0
            for path in xml_files:
                name = path.stem.replace(".blob", "")
                try:
                    blob = Blob.load(path)
                    comparison = compare_formats(blob, name)
                    total_xml_tokens += comparison["xml_tokens"]
                    total_reef_tokens += comparison["sexpr_tokens"]
                except Exception:
                    continue

            if total_xml_tokens > 0:
                reduction = (1 - total_reef_tokens / total_xml_tokens) * 100
                print(f"\nToken analysis (all XML files):")
                print(f"  XML total:  ~{total_xml_tokens} tokens")
                print(f"  .reef total: ~{total_reef_tokens} tokens")
                print(f"  Reduction:  {reduction:.1f}%")
        return

    if args.convert:
        # Convert XML to .reef
        if not xml_files:
            print("No XML files to convert")
            return

        converted = 0
        for path in xml_files:
            name = path.stem.replace(".blob", "")
            try:
                blob = Blob.load(path)
                sexpr_str = blob_to_sexpr(blob, name)
                reef_path = path.with_suffix("").with_suffix(".reef")

                if args.dry_run:
                    comparison = compare_formats(blob, name)
                    print(f"{path.name} -> {reef_path.name} ({comparison['token_reduction']} smaller)")
                else:
                    reef_path.write_text(sexpr_str)
                    if not args.keep:
                        path.unlink()
                    converted += 1
                    print(f"Converted: {path.name} -> {reef_path.name}")
            except Exception as e:
                print(f"Error converting {path}: {e}", file=sys.stderr)

        if args.dry_run:
            print(f"\n{len(xml_files)} file(s) would be converted. Run without --dry-run to convert.")
        else:
            print(f"\nConverted {converted} file(s)")
        return

    # Default: show help
    print("Usage:")
    print("  reef format --stats     Show format statistics")
    print("  reef format --convert   Convert XML to .reef")
    print("  reef format --convert --dry-run  Preview conversion")
    print("  reef format --convert --keep     Keep original XML files")


def cmd_list(args):
    """Show reef health and diagnostics."""
    from reef.blob import Glob, Blob, BlobType, BlobScope, BlobStatus, BLOB_VERSION, KNOWN_SUBDIRS

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    # Collect all polips with their paths
    all_blobs: list[tuple[Path, str, Blob]] = []

    # Root level polips
    for name, blob in glob.list_blobs():
        path = glob.claude_dir / f"{name}.blob.xml"
        all_blobs.append((path, name, blob))

    # Subdirectory polips
    for subdir in KNOWN_SUBDIRS:
        for name, blob in glob.list_blobs(subdir):
            path = glob.claude_dir / subdir / f"{name}.blob.xml"
            all_blobs.append((path, name, blob))

    if not all_blobs:
        print("No polips found in reef (.claude/)")
        print("Polips are XML context files that persist across sessions.")
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

        # Estimate tokens (~200 per polip + content)
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
    print(f"Population: {len(all_blobs)} polip(s) (~{total_tokens:,} tokens)")

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
        print(f"Schema: ! {len(needs_migration)} polip(s) need migration")
        print(f"  Run: reef migrate")
    else:
        print(f"Schema: OK all v{BLOB_VERSION}")
    print()

    # Staleness
    if stale_sessions:
        print(f"Staleness: ! {len(stale_sessions)} session polip(s) >7 days old")
        for name, blob in stale_sessions[:2]:
            print(f"  -> {name} (updated {blob.updated.strftime('%Y-%m-%d')})")
    else:
        session_count = scope_counts.get("session", 0)
        if session_count:
            print(f"Staleness: OK {session_count} session polip(s) all recent")
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
        suggestions.append(f"Run `reef migrate` to update {len(needs_migration)} polip(s)")

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
    from reef.blob import Glob

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
        print(f"  Polips migrated: {results['migrated']}")

    if args.dry_run:
        print("\nRun without --dry-run to apply")


def cmd_status(args):
    """View or change polip status."""
    from reef.blob import Glob, BlobStatus, KNOWN_SUBDIRS

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
        print(f"Polip '{name}' not found", file=sys.stderr)
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
        print("Use 'reef decompose' to archive polips", file=sys.stderr)
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
    """Manage and use polip templates."""
    from reef.blob import Glob, BUILTIN_TEMPLATES

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
        print("Usage: reef template use <name> <title>")

    elif args.action == "use":
        if not args.template_name or not args.title:
            print("Usage: reef template use <template-name> <title>", file=sys.stderr)
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
            print("Usage: reef template show <template-name>", file=sys.stderr)
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
        from reef.blob import PathTraversalError

        if not args.template_name:
            print("Usage: reef template create <name> --type thread --summary 'Bug: {title}'", file=sys.stderr)
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
        from reef.blob import PathTraversalError

        if not args.template_name:
            print("Usage: reef template delete <name>", file=sys.stderr)
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
    """Visualize polip relationships."""
    from reef.blob import Glob

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
        print("No polips to graph")
        return

    print(f"Reef Graph: {len(nodes)} polips, {len(edges)} connections")
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
        print("Tip: reef graph --dot | dot -Tpng -o reef.png")


def cmd_health(args):
    """Show reef vitality and health metrics."""
    from reef.blob import Glob

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    # Read status file
    status_file = Path(f"/tmp/reef-{project_dir.name}.status")

    if not status_file.exists():
        # Generate status first
        glob.write_status()

    try:
        with open(status_file) as f:
            status = json.load(f)
    except Exception:
        if getattr(args, 'json', False):
            print(json.dumps({"error": "Error reading reef status"}))
        else:
            print("Error reading reef status")
        sys.exit(1)

    vitality = status.get("vitality", {})
    if not vitality:
        if getattr(args, 'json', False):
            print(json.dumps({"error": "No vitality data available"}))
        else:
            print("No vitality data available")
        sys.exit(1)

    # JSON output mode
    if getattr(args, 'json', False):
        print(json.dumps(status, indent=2))
        return

    # Print health report
    icon = vitality.get("icon", "")
    score = vitality.get("score", 0)
    status_str = vitality.get("status", "unknown")
    last_activity = vitality.get("last_activity")
    days_since = vitality.get("days_since_activity")
    recommended = vitality.get("recommended_action", "")
    components = vitality.get("components", {})
    metrics = vitality.get("metrics", {})

    print(f"Reef Health Report")
    print("=" * 60)
    print()

    # Overall vitality
    print(f"{icon} Vitality: {status_str.upper()} ({score}/100)")
    if last_activity:
        print(f"  Last activity: {last_activity}", end="")
        if days_since is not None:
            if days_since == 0:
                print(" (today)")
            elif days_since == 1:
                print(" (yesterday)")
            else:
                print(f" ({days_since}d ago)")
        else:
            print()
    print()

    # Component breakdown
    print("Components:")
    print(f"  Activity:  {components.get('activity', 0):>2}/25  {'█' * int(components.get('activity', 0) / 5)}")
    print(f"  Quality:   {components.get('quality', 0):>2}/25  {'█' * int(components.get('quality', 0) / 5)}")
    print(f"  Resonance: {components.get('resonance', 0):>2}/25  {'█' * int(components.get('resonance', 0) / 5)}")
    print(f"  Health:    {components.get('health', 0):>2}/25  {'█' * int(components.get('health', 0) / 5)}")
    print()

    # Metrics
    print("Metrics:")
    print(f"  Avg facts/polip:     {metrics.get('avg_facts', 0)}")
    print(f"  Avg decisions/polip: {metrics.get('avg_decisions', 0)}")
    print(f"  Avg links/polip:     {metrics.get('avg_links', 0)}")
    print(f"  Stale polips (>30d): {metrics.get('stale_count', 0)}")
    print(f"  Isolated polips:     {metrics.get('isolated_count', 0)}")
    print()

    # Polip stats
    count = status.get("count", 0)
    types = status.get("types", {})
    if count > 0:
        print(f"Reef Size: {count} polips")
        for ptype, pcount in sorted(types.items()):
            print(f"  {ptype}: {pcount}")
        print()

    # Recommended action
    if recommended:
        print(f"💡 Recommended Action:")
        print(f"  {recommended}")
        print()

    # Status interpretation
    print("Status Guide:")
    if status_str == "thriving":
        print("  🟢 THRIVING - Your reef is healthy with good content flow")
    elif status_str == "stable":
        print("  🟡 STABLE - Reef is functional but could use more activity")
    elif status_str == "declining":
        print("  🟠 DECLINING - Low vitality, needs nutrient-rich content")
    elif status_str == "dying":
        print("  🔴 DYING - Critical: reef needs immediate attention")
    else:
        print(f"  Status: {status_str}")


def cmd_snapshot(args):
    """Manage reef snapshots."""
    from reef.blob import Glob

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    if args.action == "create":
        path = glob.create_snapshot(name=args.name)
        rel_path = path.relative_to(project_dir)
        blob_count = len(glob.list_blobs()) + sum(len(glob.list_blobs(s)) for s in ["threads", "decisions", "constraints", "contexts", "facts"])
        print(f"Snapshot created: {rel_path}")
        print(f"  {blob_count} polip(s) captured")

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
            print(f"    {meta['blob_count']} polips | {created}")

    elif args.action == "diff":
        if not args.snapshot_id:
            print("Usage: reef snapshot diff <snapshot-id>", file=sys.stderr)
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
    from reef.blob import Glob, INDEX_VERSION

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    if args.rebuild:
        count = glob.rebuild_index()
        print(f"Index rebuilt: {count} polip(s) indexed")
        glob.write_status()
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
        glob.write_status()
        return

    # Default: show stats
    index = glob.get_index()
    blob_count = len(index.get("blobs", {}))

    print(f"Index v{INDEX_VERSION}")
    print(f"  Polips indexed: {blob_count}")
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

    # Update statusline
    glob.write_status()


def cmd_surface(args):
    """Surface polips from reef with intelligent prioritization."""
    from reef.blob import Glob

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    polip_id = getattr(args, "polip_id", None)

    if not polip_id:
        # No args - show L1 index (metadata only, token-efficient)
        index = glob.get_index()
        blobs = index.get("blobs", {})

        if not blobs:
            print("Reef is empty - no polips to surface")
            return

        # Group by type and show priority ordering
        by_type = {}
        for key, entry in blobs.items():
            t = entry.get("type", "unknown")
            if t not in by_type:
                by_type[t] = []
            by_type[t].append((key, entry))

        # Priority: constraints > threads > decisions > facts > contexts
        priority_order = ["constraint", "thread", "decision", "fact", "context"]

        print("L1 Index (Polips in Reef)")
        print("=" * 50)
        print()

        shown = 0
        for ptype in priority_order:
            if ptype not in by_type:
                continue
            items = by_type[ptype]
            items.sort(key=lambda x: x[1].get("updated", ""), reverse=True)

            print(f"{ptype.upper()} ({len(items)})")
            for key, entry in items[:5]:  # Show top 5 per type
                scope_tag = f"[{entry.get('scope', '?')}]"
                summary = entry.get('summary', '')[:40]
                print(f"  {key} {scope_tag}")
                if summary:
                    print(f"    {summary}")
                shown += 1

            if len(items) > 5:
                print(f"  ... and {len(items) - 5} more")
            print()

        print(f"Total: {len(blobs)} polips")
        print()
        print("Use: /surface <polip-id> to load full content (L2)")
        return

    # Load full polip content (L2 activation)
    blob = None
    found_path = None

    # Support full ID format from L1 index (e.g., "constraints-project-rules")
    from reef.blob import KNOWN_SUBDIRS
    parsed_subdir = None
    parsed_id = polip_id

    # Check if ID starts with a known subdir prefix
    if "-" in polip_id:
        parts = polip_id.split("-", 1)
        if parts[0] in KNOWN_SUBDIRS:
            parsed_subdir = parts[0]
            parsed_id = parts[1]

    # If we parsed a subdir, try that first
    if parsed_subdir:
        candidate = glob.get(parsed_id, subdir=parsed_subdir)
        if candidate:
            blob = candidate
            found_path = glob.claude_dir / parsed_subdir / f"{parsed_id}.blob.xml"

    # Fall back to searching all subdirs with original ID
    if not blob:
        for subdir in [None, *KNOWN_SUBDIRS]:
            candidate = glob.get(polip_id, subdir=subdir)
            if candidate:
                blob = candidate
                if subdir:
                    found_path = glob.claude_dir / subdir / f"{polip_id}.blob.xml"
                else:
                    found_path = glob.claude_dir / f"{polip_id}.blob.xml"
                break

    if not blob:
        print(f"Polip not found: {polip_id}", file=sys.stderr)
        print(f"Use '/surface' (no args) to see available polips", file=sys.stderr)
        sys.exit(1)

    # Output full polip content
    print(blob.to_xml())


def cmd_hook(args):
    """Claude Code hook integration."""
    import json

    from reef.blob import Glob, Blob, BlobType, BlobScope, KNOWN_SUBDIRS

    project_dir = Path.cwd()

    if args.action == "surface":
        # UserPromptSubmit hook: surface relevant polips as XML
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
        # Stop hook: create/update context polip with session state
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
                                "command": "reef hook surface"
                            }
                        ]
                    }
                ],
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "reef hook persist"
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
        # Check hook health - is reef properly configured?
        settings_path = Path.home() / ".claude" / "settings.json"

        print("Hook Status:")
        print()

        # Check if settings.json exists
        if not settings_path.exists():
            print("  settings.json: NOT FOUND")
            print("  Run: reef hook setup")
            return

        try:
            settings = json.loads(settings_path.read_text())
            hooks = settings.get("hooks", {})

            # Check UserPromptSubmit
            upsub = hooks.get("UserPromptSubmit", [])
            has_surface = any(
                "reef hook surface" in str(h)
                for h in upsub
            )
            print(f"  UserPromptSubmit (surface): {'✓' if has_surface else '✗'}")

            # Check Stop
            stop = hooks.get("Stop", [])
            has_persist = any(
                "reef hook persist" in str(h)
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
                print(f"  Reef: {blob_count} polip(s)")
            else:
                print("  Reef: NOT INITIALIZED")
                print("  Run: reef sprout thread 'Initial setup'")

        except json.JSONDecodeError:
            print("  settings.json: INVALID JSON")
            return


def cmd_drift(args):
    """Cross-project polip discovery and sharing."""
    from reef.blob import Glob, KNOWN_SUBDIRS

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    if args.action == "discover":
        # Find nearby reefs
        reefs = glob.discover_reefs()

        if not reefs:
            print("No nearby reefs found.")
            print()
            print("Drift searches for:")
            print("  - ~/.claude/ (global polips)")
            print("  - Sibling directories with .claude/")
            print("  - Paths in .claude/drift.json")
            return

        print(f"Discovered Reefs ({len(reefs)}):")
        print()
        for reef in reefs:
            source_tag = f"[{reef['source']}]"
            print(f"  {reef['name']} {source_tag}")
            print(f"    {reef['polip_count']} polip(s)")
            print(f"    {reef['path']}")
            print()

    elif args.action == "list":
        # List polips available for drift
        scope_filter = args.scope.split(",") if args.scope else None
        polips = glob.list_drift_polips(scope_filter=scope_filter)

        if not polips:
            print("No drift polips found.")
            if not args.scope:
                print("  (Only 'always' scope by default)")
                print("  Use --scope project,always to include more")
            return

        print(f"Drift Polips ({len(polips)}):")
        print()
        for p in polips:
            scope_tag = f"[{p['blob'].scope.value}]"
            type_tag = f"[{p['blob'].type.value}]"
            print(f"  {p['key']} {scope_tag} {type_tag}")
            print(f"    {p['blob'].summary[:60]}")
        print()
        print("Pull with: reef drift pull <key>")

    elif args.action == "pull":
        # Copy a polip from another reef
        if not args.key:
            print("Usage: reef drift pull <key>", file=sys.stderr)
            print("  Get keys from: reef drift list", file=sys.stderr)
            sys.exit(1)

        path = glob.pull_polip(args.key)
        if path:
            rel_path = path.relative_to(project_dir)
            print(f"Pulled: {rel_path}")
        else:
            print(f"Polip not found: {args.key}", file=sys.stderr)
            print("  Get keys from: reef drift list --scope always,project", file=sys.stderr)
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
    from reef.blob import Glob
    from reef.safety import PruningSafeguards, AuditLog

    project_dir = Path.cwd()
    glob = Glob(project_dir)
    guards = PruningSafeguards(project_dir)
    audit = AuditLog(project_dir)

    # Handle dry-run mode
    dry_run = getattr(args, 'dry_run', False)
    fix = args.fix and not dry_run

    issues = glob.check_integrity()

    # Count total issues
    total_issues = sum(len(v) for v in issues.values())

    if total_issues == 0:
        print("Reef integrity: OK")
        print("  No issues found")
        return

    if dry_run:
        print(f"Reef integrity: {total_issues} issue(s) found [DRY RUN]")
    else:
        print(f"Reef integrity: {total_issues} issue(s) found")
    print()

    # Missing files
    if issues["missing_files"]:
        print(f"Missing Files ({len(issues['missing_files'])}):")
        for polip_key, file_path in issues["missing_files"][:5]:
            print(f"  {polip_key}")
            print(f"    -> {file_path}")
        if len(issues["missing_files"]) > 5:
            print(f"  ... and {len(issues['missing_files']) - 5} more")

        if fix:
            print()
            fixed = 0
            seen_keys = set()
            for polip_key, _ in issues["missing_files"]:
                if polip_key not in seen_keys:
                    if glob.fix_missing_files(polip_key):
                        audit.log_operation("fix", polip_key, "Removed missing file refs", agent="sync")
                        fixed += 1
                    seen_keys.add(polip_key)
            print(f"  Fixed {fixed} polip(s) - removed missing file refs")
        elif dry_run and args.fix:
            seen_keys = set(pk for pk, _ in issues["missing_files"])
            print(f"  [DRY RUN] Would fix {len(seen_keys)} polip(s)")
        print()

    # Stale polips
    if issues["stale_polips"]:
        print(f"Stale Session Polips ({len(issues['stale_polips'])}):")
        for polip_key, days_old in issues["stale_polips"][:5]:
            print(f"  {polip_key} ({days_old}d old)")
        if len(issues["stale_polips"]) > 5:
            print(f"  ... and {len(issues['stale_polips']) - 5} more")
        print("  Tip: Run `reef sink` to archive stale session polips")
        print()

    # Orphan index entries
    if issues["orphan_files"]:
        print(f"Orphan Index Entries ({len(issues['orphan_files'])}):")
        for key in issues["orphan_files"][:5]:
            print(f"  {key}")
        if len(issues["orphan_files"]) > 5:
            print(f"  ... and {len(issues['orphan_files']) - 5} more")

        if fix:
            glob.rebuild_index()
            audit.log_operation("fix", "index", "Rebuilt index", agent="sync")
            print("  Fixed: Index rebuilt")
        elif dry_run and args.fix:
            print("  [DRY RUN] Would rebuild index")
        else:
            print("  Tip: Run `reef index --rebuild` to fix")
        print()

    # Broken refs
    if issues["broken_refs"]:
        print(f"Broken Related Refs ({len(issues['broken_refs'])}):")
        for polip_key, ref in issues["broken_refs"][:5]:
            print(f"  {polip_key} -> {ref}")
        if len(issues["broken_refs"]) > 5:
            print(f"  ... and {len(issues['broken_refs']) - 5} more")
        print()

    # Schema outdated
    if issues["schema_outdated"]:
        print(f"Schema Outdated ({len(issues['schema_outdated'])}):")
        for polip_key in issues["schema_outdated"][:5]:
            print(f"  {polip_key}")
        if len(issues["schema_outdated"]) > 5:
            print(f"  ... and {len(issues['schema_outdated']) - 5} more")

        if fix:
            count = glob.migrate_all()
            audit.log_operation("migrate", "all", f"Migrated {count} polips", agent="sync")
            print(f"  Fixed: Migrated {count} polip(s)")
        elif dry_run and args.fix:
            print(f"  [DRY RUN] Would migrate {len(issues['schema_outdated'])} polip(s)")
        else:
            print("  Tip: Run `reef migrate` to update")
        print()

    if dry_run:
        print("Run without --dry-run to apply fixes")
    elif not args.fix and total_issues > 0:
        print("Run `reef sync --fix` to auto-fix where possible")
        print("Run `reef sync --fix --dry-run` to preview fixes")

    # Update statusline
    glob.write_status()


def cmd_audit(args):
    """View automatic operation history."""
    from reef.safety import AuditLog

    project_dir = Path.cwd()
    audit = AuditLog(project_dir)

    if args.summary:
        summary = audit.summarize(since=args.since)
        print(f"Audit Summary ({summary['period']})")
        print(f"  Total operations: {summary['total']}")

        if summary['by_type']:
            print("\n  By Type:")
            for op_type, count in sorted(summary['by_type'].items()):
                print(f"    {op_type}: {count}")

        if summary['by_agent']:
            print("\n  By Agent:")
            for agent, count in sorted(summary['by_agent'].items()):
                print(f"    {agent}: {count}")
        return

    entries = audit.query(
        since=args.since,
        op_type=args.op_type,
        limit=args.limit,
    )

    if not entries:
        print("No audit entries found")
        if args.since:
            print(f"  (filtered by: since={args.since})")
        if args.op_type:
            print(f"  (filtered by: type={args.op_type})")
        return

    print(f"Audit Log ({len(entries)} entries)")
    print()

    for entry in entries:
        timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        agent_str = f" [{entry.agent}]" if entry.agent else ""
        print(f"  {timestamp} {entry.op_type}: {entry.polip_id}{agent_str}")
        print(f"    {entry.reason}")
        if entry.details:
            for key, value in entry.details.items():
                print(f"    {key}: {value}")
        print()


def cmd_undo(args):
    """Restore quarantined polips."""
    from reef.safety import UndoBuffer

    project_dir = Path.cwd()
    undo = UndoBuffer(project_dir)

    # List quarantined polips
    if args.list or (not args.polip_id and not args.expire):
        items = undo.list_quarantined()

        if not items:
            print("No polips in quarantine")
            return

        print(f"Quarantined Polips ({len(items)})")
        print()

        for item in items:
            timestamp = item.quarantine_time.strftime("%Y-%m-%d %H:%M")
            expires = item.expires.strftime("%Y-%m-%d") if item.expires else "never"
            agent_str = f" [{item.agent}]" if item.agent else ""
            print(f"  {item.polip_id}{agent_str}")
            print(f"    Quarantined: {timestamp}")
            print(f"    Expires: {expires}")
            print(f"    Reason: {item.reason}")
            print()

        print("Use `reef undo <polip-id>` to restore")
        return

    # Expire old polips
    if args.expire:
        expired = undo.expire_old()
        if expired:
            print(f"Permanently deleted {len(expired)} expired polip(s):")
            for polip_id in expired:
                print(f"  {polip_id}")
        else:
            print("No expired polips to delete")
        return

    # Restore specific polip
    if args.polip_id:
        success, message = undo.restore(args.polip_id)
        if success:
            print(f"Restored: {message}")
        else:
            print(f"Error: {message}")
            return


def cmd_workers(args):
    """Manage external worker infrastructure."""
    from reef.workers import WorkerDispatcher

    project_dir = Path.cwd()
    dispatcher = WorkerDispatcher(project_dir)

    # Status subcommand (default)
    if args.workers_cmd == "status" or args.workers_cmd is None:
        status = dispatcher.get_worker_status()
        available = dispatcher.get_available_workers()

        print(f"Worker Status ({len(available)}/{len(status)} available)")
        print()

        for worker_name, info in status.items():
            avail_str = "OK" if info["available"] else "unavailable"
            print(f"  {worker_name}: {avail_str}")

            if worker_name == "ollama" and info.get("available"):
                models = info.get("models", [])
                if models:
                    print(f"    models: {', '.join(models[:3])}")
                    if len(models) > 3:
                        print(f"            +{len(models) - 3} more")
                print(f"    host: {info.get('host', 'unknown')}")

            if worker_name in ("groq", "gemini"):
                key_status = "configured" if info.get("has_api_key") else "missing API key"
                print(f"    api_key: {key_status}")

            if info.get("error"):
                print(f"    error: {info['error']}")

            print()

        return

    # Test subcommand
    if args.workers_cmd == "test":
        worker_name = args.worker_name
        if not worker_name:
            print("Usage: reef workers test <worker>")
            print("  Workers: groq, ollama, gemini")
            return

        print(f"Testing {worker_name}...")

        # Get worker class
        worker_classes = dispatcher._get_worker_classes()
        if worker_name not in worker_classes:
            print(f"Unknown worker: {worker_name}")
            return

        try:
            worker = worker_classes[worker_name]()

            if not worker.is_available():
                print(f"  {worker_name} is not available")
                if worker_name in ("groq", "gemini"):
                    env_var = "GROQ_API_KEY" if worker_name == "groq" else "GEMINI_API_KEY"
                    print(f"  Set {env_var} environment variable")
                elif worker_name == "ollama":
                    print("  Ensure Ollama is running (ollama serve)")
                return

            # Send test prompt
            print("  Sending test prompt...")
            response = worker.complete("Say 'Hello from reef!' in exactly 5 words.")
            print(f"  Response: {response.content[:100]}")
            print(f"  Model: {response.model}")
            print(f"  Latency: {response.latency_ms}ms")
            print()
            print(f"  {worker_name}: OK")

        except Exception as e:
            print(f"  Error: {e}")

        return

    # Run subcommand
    if args.workers_cmd == "run":
        prompt = args.prompt
        if not prompt:
            print("Usage: reef workers run \"<prompt>\" [--worker <name>] [--type <task_type>]")
            return

        worker_name = args.worker_name
        task_type = args.task_type or "summarize"

        if worker_name:
            # Dispatch to specific worker
            result = dispatcher._dispatch_to_worker(worker_name, prompt)
        else:
            # Auto-route based on task type
            result = dispatcher.dispatch(task_type, prompt)

        if result.success:
            print(f"Worker: {result.worker_name}")
            print(f"Model: {result.model_used}")
            print(f"Latency: {result.latency_ms}ms")
            print()
            print("Response:")
            print(result.output)
        else:
            print(f"Error: {result.error}")

        return


def cmd_skills(args):
    """Manage skill hotloading."""
    from reef.skills import SkillLoader, SkillRegistry

    project_dir = Path.cwd()
    loader = SkillLoader(project_dir)
    registry = SkillRegistry(project_dir)

    # Default to list
    if not args.skills_cmd or args.skills_cmd == "list":
        skills = loader.discover()

        if args.local:
            skills = [s for s in skills if s.source == "local"]
        if args.global_:
            skills = [s for s in skills if s.source == "global"]

        if not skills:
            print("No skills found")
            return

        print(f"Skills ({len(skills)} total)")
        print()

        # Group by source
        local_skills = [s for s in skills if s.source == "local"]
        global_skills = [s for s in skills if s.source == "global"]

        if local_skills:
            print("Local (.claude/skills/):")
            for skill in local_skills:
                agents = ", ".join(skill.agents) if skill.agents else "any"
                types = ", ".join(skill.task_types) if skill.task_types else "any"
                print(f"  {skill.name}")
                if skill.agents or skill.task_types:
                    print(f"    agents: {agents} | types: {types}")
            print()

        if global_skills:
            print("Global (~/.claude/skills/):")
            for skill in global_skills:
                agents = ", ".join(skill.agents) if skill.agents else "any"
                print(f"  {skill.name}")
            print()

        return

    # Show subcommand
    if args.skills_cmd == "show":
        skill_name = args.name
        content = loader.load(skill_name)

        if content is None:
            print(f"Skill not found: {skill_name}")
            sys.exit(1)

        info = loader.get_skill_info(skill_name)
        if info:
            print(f"# {skill_name}")
            print(f"# Source: {info.source}")
            if info.agents:
                print(f"# Agents: {', '.join(info.agents)}")
            if info.task_types:
                print(f"# Task types: {', '.join(info.task_types)}")
            print()

        print(content)
        return

    # Create subcommand
    if args.skills_cmd == "create":
        skill_name = args.name
        agents = args.agents or []
        task_types = args.task_types or []
        local = not args.global_

        # Create placeholder content
        content = f"""# {skill_name}

## Overview

[Describe what this skill does]

## Usage

[When to use this skill]

## Instructions

[Step-by-step instructions]
"""

        path = loader.create_skill(
            name=skill_name,
            content=content,
            agents=agents,
            task_types=task_types,
            local=local,
        )

        print(f"Created skill: {path.relative_to(project_dir)}")
        print(f"Edit the file to add skill content.")
        return

    # Check subcommand
    if args.skills_cmd == "check":
        # Load all skills with tracking
        for skill in loader.discover():
            loader.load_with_tracking(skill.name)

        changed = loader.check_for_changes()

        if not changed:
            print("No skills have been modified")
        else:
            print(f"Modified skills ({len(changed)}):")
            for name in changed:
                print(f"  {name}")
            print()
            print("Run 'reef skills reload' to reload changed skills")

        return


def cmd_calcify(args):
    """View calcification candidates (AI-native: session-relative scoring)."""
    from reef.calcification import CalcificationEngine
    from reef.blob import Glob

    project_dir = Path.cwd()
    glob = Glob(project_dir)
    engine = CalcificationEngine(glob)

    if args.all:
        scores = engine.get_all_scores()
    else:
        scores = engine.get_candidates()

    if args.json:
        print(json.dumps([s.to_dict() for s in scores], indent=2))
        return

    if not scores:
        print("No calcification candidates found.")
        print("Polips calcify through: intensity (5+ refs/session), persistence (3+ sessions),")
        print("                        ceremony (promoted), or consensus (3+ incoming refs)")
        return

    title = "All Polip Scores" if args.all else "Calcification Candidates"
    print(f"{title} ({len(scores)} polips)")
    print("=" * 70)
    print()
    print(f"{'Polip':<30} {'Score':>7} {'Int':>5} {'Per':>5} {'Dep':>5} {'Cer':>5} {'Con':>5} {'Stage':<10}")
    print("-" * 70)

    for s in scores:
        name = s.polip_key[:28] + ".." if len(s.polip_key) > 30 else s.polip_key
        marker = "✓" if s.should_calcify else " "
        print(f"{name:<30} {s.total:>6.2f}{marker} {s.intensity_score:>5.2f} {s.persistence_score:>5.2f} {s.depth_score:>5.2f} {s.ceremony_score:>5.2f} {s.consensus_score:>5.2f} {s.lifecycle_stage:<10}")

    print()
    print(f"Threshold: {engine.CALCIFICATION_THRESHOLD} (✓ = ready to calcify)")
    print("Columns: Int=intensity, Per=persistence, Dep=depth, Cer=ceremony, Con=consensus")


def cmd_decay(args):
    """Run adversarial decay challenges."""
    from reef.calcification import AdversarialDecay, ChallengeResult
    from reef.blob import Glob

    project_dir = Path.cwd()
    glob = Glob(project_dir)
    decay = AdversarialDecay(glob)

    dry_run = not args.execute
    reports = decay.run_challenges(dry_run=dry_run)

    if args.json:
        print(json.dumps([r.to_dict() for r in reports], indent=2))
        return

    if not reports:
        print("No polips challenged.")
        print("Challengers: stale (60d + <3 access), orphan (30d + no refs)")
        return

    mode = "DRY RUN" if dry_run else "EXECUTED"
    print(f"Adversarial Decay [{mode}] ({len(reports)} challenged)")
    print("=" * 60)
    print()

    for r in reports:
        icon = {"survive": "✓", "merge": "→", "decompose": "✗"}[r.result.value]
        print(f"{icon} {r.polip_key}")
        print(f"  Trigger: {r.trigger}")
        print(f"  Result:  {r.result.value.upper()}")
        print(f"  Reason:  {r.reason}")
        print()

    if dry_run:
        decompose_count = sum(1 for r in reports if r.result == ChallengeResult.DECOMPOSE)
        if decompose_count > 0:
            print(f"Run 'reef decay --execute' to decompose {decompose_count} polips")


def cmd_trench(args):
    """Manage parallel Claude sessions in git worktrees."""
    from reef.trench import TrenchHarness, TrenchStatus
    from reef.blob import Glob

    project_dir = Path.cwd()
    harness = TrenchHarness(project_dir)
    glob = Glob(project_dir)

    # Default to status
    if not args.trench_cmd or args.trench_cmd == "status":
        name = getattr(args, "name", None)
        json_output = getattr(args, "json", False)

        trenches = harness.status(name)

        if json_output:
            print(json.dumps([t.to_dict() for t in trenches], indent=2))
            return

        if not trenches:
            if name:
                print(f"Trench '{name}' not found")
            else:
                print("No active trenches")
                print()
                print("Spawn one with: reef trench spawn <name>")
            return

        print(f"Trenches ({len(trenches)} active)")
        print("=" * 60)
        print()

        for t in trenches:
            status_icon = {
                TrenchStatus.SPAWNING: "⏳",
                TrenchStatus.RUNNING: "🔄",
                TrenchStatus.TESTING: "🧪",
                TrenchStatus.READY: "✅",
                TrenchStatus.FAILED: "❌",
                TrenchStatus.MERGED: "✓",
                TrenchStatus.ABORTED: "⊘",
            }.get(t.status, "?")

            age = datetime.now() - t.created
            age_str = f"{age.days}d" if age.days > 0 else f"{age.seconds // 3600}h"

            print(f"{status_icon} {t.name} [{t.status.value}]")
            print(f"  Branch: {t.branch}")
            print(f"  Path:   {t.worktree_path}")
            print(f"  Age:    {age_str}")
            if t.error:
                print(f"  Error:  {t.error}")
            print()

        return

    # spawn
    if args.trench_cmd == "spawn":
        base = getattr(args, "base", None)
        task = getattr(args, "task", None)
        model = getattr(args, "model", None)

        if task:
            # Auto-launch Claude session with task
            result = harness.spawn_session(
                name=args.name,
                task=task,
                model=model,
                base_branch=base,
            )

            if result.success:
                info = result.trench
                complexity = info.complexity or "moderate"
                print(f"✓ {result.message}")
                print()
                print(f"  Task:       {info.task}")
                print(f"  Complexity: {complexity} → {info.model}")
                print(f"  Worktree:   {info.worktree_path}")
                print(f"  PID:        {info.pid}")
                print()
                print("Monitor with:")
                print(f"  reef trench status {args.name}")
                print(f"  reef trench logs {args.name}")
            else:
                print(f"✗ {result.message}")
                if result.error:
                    print(f"  {result.error}")
                sys.exit(1)
        else:
            # Just create worktree (manual session)
            result = harness.spawn(args.name, base_branch=base)

            if result.success:
                print(f"✓ {result.message}")
                print()
                print("Next steps:")
                print(f"  1. cd {result.trench.worktree_path}")
                print(f"  2. claude  # Start Claude session in trench")
                print(f"  3. Make changes, commit to branch '{result.trench.branch}'")
                print(f"  4. reef trench test {args.name}  # Run tests")
                print(f"  5. reef trench merge {args.name}  # Merge if tests pass")
                print()
                print("Or auto-launch with:")
                print(f"  reef trench spawn {args.name} --task 'your task here'")
            else:
                print(f"✗ {result.message}")
                if result.error:
                    print(f"  {result.error}")
                sys.exit(1)

        # Update statusline after spawn
        glob.write_status()
        return

    # test
    if args.trench_cmd == "test":
        cmd = getattr(args, "cmd", "uv run pytest")
        print(f"Running tests in trench '{args.name}'...")
        print(f"Command: {cmd}")
        print()

        result = harness.run_tests(args.name, test_command=cmd)

        if result.success:
            print(f"✓ {result.message}")
            print()
            print(f"Ready to merge: reef trench merge {args.name}")
        else:
            print(f"✗ {result.message}")
            if result.error:
                print(f"  {result.error}")
            if result.trench and result.trench.test_output:
                print()
                print("Test output (last 50 lines):")
                print("-" * 40)
                lines = result.trench.test_output.strip().split("\n")
                for line in lines[-50:]:
                    print(line)
            sys.exit(1)

        # Update statusline after test
        glob.write_status()
        return

    # merge
    if args.trench_cmd == "merge":
        delete_branch = not getattr(args, "no_delete", False)
        result = harness.merge(args.name, delete_branch=delete_branch)

        if result.success:
            print(f"✓ {result.message}")
        else:
            print(f"✗ {result.message}")
            if result.error:
                print(f"  {result.error}")
            sys.exit(1)

        # Update statusline after merge
        glob.write_status()
        return

    # abort
    if args.trench_cmd == "abort":
        force = getattr(args, "force", False)
        result = harness.abort(args.name, force=force)

        if result.success:
            print(f"✓ {result.message}")
        else:
            print(f"✗ {result.message}")
            if result.error:
                print(f"  {result.error}")
            sys.exit(1)

        # Update statusline after abort
        glob.write_status()
        return

    # prune
    if args.trench_cmd == "prune":
        days = getattr(args, "days", 7)
        dry_run = not getattr(args, "execute", False)

        results = harness.prune_stale(max_age_days=days, dry_run=dry_run)

        if not results:
            print(f"No stale trenches (older than {days} days)")
            return

        mode = "DRY RUN" if dry_run else "EXECUTED"
        print(f"Stale Trench Pruning [{mode}]")
        print("=" * 60)
        print()

        for r in results:
            icon = "✓" if r.success else "✗"
            print(f"{icon} {r.message}")
            if r.error:
                print(f"  Error: {r.error}")

        if dry_run:
            print()
            print(f"Run 'reef trench prune --execute' to prune these trenches")

        # Update statusline after prune
        glob.write_status()
        return

    # cleanup
    if args.trench_cmd == "cleanup":
        force = getattr(args, "force", False)
        results = harness.cleanup_all(force=force)

        if not results:
            print("No trenches to clean up")
            return

        print("Trench Cleanup")
        print("=" * 60)
        print()

        for r in results:
            icon = "✓" if r.success else "✗"
            print(f"{icon} {r.message}")
            if r.error:
                print(f"  Error: {r.error}")

        return

    # logs
    if args.trench_cmd == "logs":
        lines = getattr(args, "lines", 50)
        follow = getattr(args, "follow", False)

        output = harness.get_session_output(args.name, tail_lines=lines)

        if output is None:
            print(f"No logs found for trench '{args.name}'")
            print("  (Session may not have been started with --task)")
            sys.exit(1)

        if follow:
            # Follow mode - use tail -f on the log file
            import time
            info = harness._read_trench_status(args.name)
            if info:
                log_file = info.worktree_path / ".claude-session.log"
                print(f"Following {log_file}... (Ctrl+C to stop)")
                print()
                print(output)

                # Simple follow loop
                try:
                    last_size = log_file.stat().st_size
                    while True:
                        time.sleep(1)
                        current_size = log_file.stat().st_size
                        if current_size > last_size:
                            with open(log_file, "r") as f:
                                f.seek(last_size)
                                new_content = f.read()
                                print(new_content, end="")
                            last_size = current_size

                        # Check if session is still alive
                        if not harness.is_session_alive(args.name):
                            print("\n[Session ended]")
                            break
                except KeyboardInterrupt:
                    print("\n[Stopped following]")
        else:
            print(f"Logs for trench '{args.name}':")
            print("=" * 60)
            print(output)

            # Show session status
            if harness.is_session_alive(args.name):
                print()
                print("[Session still running]")
            else:
                print()
                print("[Session ended]")

        return


def cmd_shell(args):
    """Interactive REPL with ghost text hints."""
    from reef.shell import main as shell_main
    import sys

    # Pass through args
    if args.hint:
        sys.argv = ["reef-shell", "--hint"]
    else:
        sys.argv = ["reef-shell"]

    shell_main()


def cmd_project(args):
    """
    Generate LLM-specific projections from .reef.

    .reef is the universal AI memory source.
    Projections are derived views optimized for specific LLMs.
    Any AI swims in reef - this generates the view they see.
    """
    from reef.blob import Glob

    project_dir = Path.cwd()
    reef_dir = project_dir / ".reef"

    if not reef_dir.exists():
        print("No .reef found. Run 'reef init' first.")
        return

    # Read reef state (currently from .claude, will migrate)
    glob = Glob(project_dir)
    index = glob.get_index()
    blobs = index.get("blobs", {})

    # Compute vitality for filtering (simplified for now)
    def get_vitality(entry):
        # Higher priority = higher vitality for now
        return entry.get("priority", 50)

    # Filter to high-vitality unless --full
    if not args.full:
        blobs = {k: v for k, v in blobs.items() if get_vitality(v) >= 50}

    # Generate projection based on target
    if args.target == "claude":
        output = _project_claude(project_dir, blobs, glob)
    elif args.target == "ollama":
        output = _project_ollama(project_dir, blobs, glob)
    elif args.target == "gpt":
        output = _project_gpt(project_dir, blobs, glob)
    elif args.target == "gemini":
        output = _project_gemini(project_dir, blobs, glob)
    elif args.target == "raw":
        output = _project_raw(project_dir, blobs, glob)
    else:
        print(f"Unknown target: {args.target}")
        return

    # Output
    if args.output:
        Path(args.output).write_text(output)
        print(f"Projected to {args.output}")
    else:
        print(output)


def _project_claude(project_dir: Path, blobs: dict, glob) -> str:
    """Generate CLAUDE.md from reef state."""
    lines = [
        f"# {project_dir.name}",
        "",
        "<!-- Projected from .reef - do not edit directly -->",
        "<!-- Source: reef | Target: Claude -->",
        "",
    ]

    # Constraints first (bedrock)
    constraints = [(k, v) for k, v in blobs.items() if v.get("type") == "constraint"]
    if constraints:
        lines.append("## Constraints")
        lines.append("")
        for key, entry in sorted(constraints, key=lambda x: -x[1].get("priority", 0)):
            lines.append(f"- **{key}**: {entry.get('summary', '')}")
        lines.append("")

    # Active threads
    threads = [(k, v) for k, v in blobs.items() if v.get("type") == "thread"]
    if threads:
        lines.append("## Active Threads")
        lines.append("")
        for key, entry in sorted(threads, key=lambda x: -x[1].get("priority", 0)):
            lines.append(f"- **{key}**: {entry.get('summary', '')}")
        lines.append("")

    # Facts
    facts = [(k, v) for k, v in blobs.items() if v.get("type") == "fact"]
    if facts:
        lines.append("## Facts")
        lines.append("")
        for key, entry in facts:
            lines.append(f"- {entry.get('summary', '')}")
        lines.append("")

    return "\n".join(lines)


def _project_ollama(project_dir: Path, blobs: dict, glob) -> str:
    """Generate Ollama-optimized system prompt from reef."""
    lines = [
        f"You are working in the {project_dir.name} project.",
        "",
        "Key constraints:",
    ]
    for key, entry in blobs.items():
        if entry.get("type") == "constraint":
            lines.append(f"- {entry.get('summary', '')}")

    lines.append("")
    lines.append("Current context:")
    for key, entry in blobs.items():
        if entry.get("type") in ("thread", "context"):
            lines.append(f"- {entry.get('summary', '')}")

    return "\n".join(lines)


def _project_gpt(project_dir: Path, blobs: dict, glob) -> str:
    """Generate GPT-optimized system prompt from reef."""
    # GPT prefers structured system prompts
    sections = {
        "Project": project_dir.name,
        "Constraints": [],
        "Context": [],
    }

    for key, entry in blobs.items():
        if entry.get("type") == "constraint":
            sections["Constraints"].append(entry.get("summary", ""))
        elif entry.get("type") in ("thread", "context"):
            sections["Context"].append(entry.get("summary", ""))

    lines = [f"Project: {sections['Project']}", ""]
    if sections["Constraints"]:
        lines.append("Constraints:")
        for c in sections["Constraints"]:
            lines.append(f"- {c}")
        lines.append("")
    if sections["Context"]:
        lines.append("Context:")
        for c in sections["Context"]:
            lines.append(f"- {c}")

    return "\n".join(lines)


def _project_gemini(project_dir: Path, blobs: dict, glob) -> str:
    """Generate Gemini-optimized context from reef."""
    # Similar to GPT for now
    return _project_gpt(project_dir, blobs, glob)


def _project_raw(project_dir: Path, blobs: dict, glob) -> str:
    """Raw reef state as JSON."""
    import json
    return json.dumps({
        "project": project_dir.name,
        "reef_version": 1,
        "polips": blobs,
    }, indent=2)


def main():
    parser = argparse.ArgumentParser(
        prog="reef",
        description="Symbiotic memory for AI",
        epilog="polip = memory unit | reef = colony | current = active thread | bedrock = constraint"
    )
    parser.add_argument("--version", "-V", action="version", version="reef 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize reef in current project",
        description="Set up reef with .claude/ directory and optional .gitignore"
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
        help="Spawn a new polip",
        description="Spawn a new polip into the reef (.claude/ directory)"
    )
    sprout_parser.add_argument("type", help="Polip type: thread, decision, constraint, fact")
    sprout_parser.add_argument("summary", help="Brief summary of the polip")
    sprout_parser.add_argument("--status", help="Status for currents: active, blocked, done, archived")
    sprout_parser.add_argument("--name", "-n", help="Polip filename (default: derived from summary)")
    sprout_parser.add_argument("--dir", "-d", help="Subdirectory override (default: based on type)")
    sprout_parser.set_defaults(func=cmd_sprout)

    # list (reef)
    list_parser = subparsers.add_parser(
        "list",
        help="Show reef health and diagnostics",
        aliases=["reef"],
        description="Display population health and diagnostics for all polips"
    )
    list_parser.set_defaults(func=cmd_list)

    # migrate
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Migrate polips to current schema",
        description="Upgrade polips to the current schema version"
    )
    migrate_parser.add_argument("--dry-run", action="store_true", help="Preview migrations without applying")
    migrate_parser.set_defaults(func=cmd_migrate)

    # format (XML to .reef conversion)
    format_parser = subparsers.add_parser(
        "format",
        help="Manage polip file formats",
        description="Convert between XML and .reef formats, show statistics"
    )
    format_parser.add_argument("--stats", action="store_true", help="Show format statistics and token savings")
    format_parser.add_argument("--convert", action="store_true", help="Convert XML files to .reef format")
    format_parser.add_argument("--dry-run", action="store_true", help="Preview conversion without applying")
    format_parser.add_argument("--keep", action="store_true", help="Keep original XML files after conversion")
    format_parser.set_defaults(func=cmd_format)

    # decompose (sink)
    decompose_parser = subparsers.add_parser(
        "decompose",
        help="Sink stale session polips",
        aliases=["sink"],
        description="Find and sink session-scoped polips older than threshold"
    )
    decompose_parser.add_argument("--days", type=int, help="Age threshold in days (default: 7)")
    decompose_parser.add_argument("--dry-run", action="store_true", help="Preview without sinking")
    decompose_parser.set_defaults(func=cmd_decompose)

    # cleanup
    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="Session-start cleanup (swarm-safe)",
        description="Prune stale sessions, old archives, and migrate polips. Uses lock file for swarm safety."
    )
    cleanup_parser.add_argument("--archive-days", type=int, help="Days before pruning archives (default: 30)")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    cleanup_parser.set_defaults(func=cmd_cleanup)

    # surface (L1/L2 activation)
    surface_parser = subparsers.add_parser(
        "surface",
        help="Surface polips from reef",
        description="Show L1 index (all polips, metadata only) or L2 full content of specific polip"
    )
    surface_parser.add_argument("polip_id", nargs="?", help="Polip ID to load (L2). Omit for L1 index.")
    surface_parser.set_defaults(func=cmd_surface)

    # index
    index_parser = subparsers.add_parser(
        "index",
        help="Manage metadata index",
        description="Search, rebuild, or inspect the polip metadata index."
    )
    index_parser.add_argument("--search", "-s", metavar="QUERY", help="Search polip summaries")
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
        help="View or change polip status",
        description="View current status or transition a polip to a new status (active, blocked, done)."
    )
    status_parser.add_argument("name", help="Polip name (without .blob.xml)")
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
        help="Visualize polip relationships",
        description="Show polip graph with connections. Use --dot for Graphviz export."
    )
    graph_parser.add_argument("--dot", action="store_true", help="Output Graphviz DOT format")
    graph_parser.set_defaults(func=cmd_graph)

    # health
    health_parser = subparsers.add_parser(
        "health",
        help="Show reef vitality and health metrics",
        description="Display reef ecosystem health score, activity patterns, and recommended actions to maintain or revive your reef."
    )
    health_parser.add_argument("--json", action="store_true", help="Output as JSON")
    health_parser.set_defaults(func=cmd_health)

    # template
    template_parser = subparsers.add_parser(
        "template",
        help="Manage and use polip templates",
        description="List, show, use, create, or delete templates for polip creation."
    )
    template_parser.add_argument("action", choices=["list", "use", "show", "create", "delete"], help="Action to perform")
    template_parser.add_argument("template_name", nargs="?", help="Template name")
    template_parser.add_argument("title", nargs="?", help="Title for new polip (with 'use')")
    template_parser.add_argument("--type", "-t", help="Polip type for create: thread, decision, constraint, fact")
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
    hook_parser.add_argument("--drift", action="store_true", help="Include drift polips (for surface)")
    hook_parser.set_defaults(func=cmd_hook)

    # drift (cross-project discovery)
    drift_parser = subparsers.add_parser(
        "drift",
        help="Cross-project polip discovery",
        description="Discover and share polips across projects (global, siblings, configured paths)."
    )
    drift_parser.add_argument(
        "action",
        choices=["discover", "list", "pull", "config"],
        help="discover: find reefs | list: show drift polips | pull: copy polip | config: settings"
    )
    drift_parser.add_argument("key", nargs="?", help="Polip key for pull (from 'drift list')")
    drift_parser.add_argument("--scope", help="Scope filter: always,project,session (comma-separated)")
    drift_parser.add_argument("--add-path", help="Add path to drift config")
    drift_parser.add_argument("--remove-path", help="Remove path from drift config")
    drift_parser.set_defaults(func=cmd_drift)

    # sync (integrity check)
    sync_parser = subparsers.add_parser(
        "sync",
        help="Check reef integrity",
        description="Scan for missing files, stale polips, broken refs, and other integrity issues."
    )
    sync_parser.add_argument("--fix", action="store_true", help="Auto-fix issues where possible")
    sync_parser.add_argument("--dry-run", action="store_true", help="Preview what would be fixed without applying")
    sync_parser.set_defaults(func=cmd_sync)

    # audit (view operation history)
    audit_parser = subparsers.add_parser(
        "audit",
        help="View automatic operation history",
        description="Query the audit log for automatic operations (prune, calcify, merge, decay)."
    )
    audit_parser.add_argument("--since", help="Time filter (e.g., 7d, 24h, 30m)")
    audit_parser.add_argument("--type", dest="op_type", help="Filter by operation type")
    audit_parser.add_argument("--limit", type=int, default=20, help="Maximum entries to show (default: 20)")
    audit_parser.add_argument("--summary", action="store_true", help="Show summary statistics instead of entries")
    audit_parser.set_defaults(func=cmd_audit)

    # undo (restore quarantined polips)
    undo_parser = subparsers.add_parser(
        "undo",
        help="Restore quarantined polips",
        description="List or restore polips from quarantine. Polips are quarantined for 7 days before permanent deletion."
    )
    undo_parser.add_argument("polip_id", nargs="?", help="ID of polip to restore")
    undo_parser.add_argument("--list", action="store_true", help="List all quarantined polips")
    undo_parser.add_argument("--expire", action="store_true", help="Permanently delete expired polips")
    undo_parser.set_defaults(func=cmd_undo)

    # workers (external model infrastructure)
    workers_parser = subparsers.add_parser(
        "workers",
        help="Manage external worker infrastructure",
        description="Check status, test, and run tasks on external models (Groq, Ollama, Gemini)."
    )
    workers_subparsers = workers_parser.add_subparsers(dest="workers_cmd")

    # workers status
    workers_status = workers_subparsers.add_parser("status", help="Show worker availability")

    # workers test
    workers_test = workers_subparsers.add_parser("test", help="Test a specific worker")
    workers_test.add_argument("worker_name", nargs="?", help="Worker to test: groq, ollama, gemini")

    # workers run
    workers_run = workers_subparsers.add_parser("run", help="Run a task on workers")
    workers_run.add_argument("prompt", nargs="?", help="Prompt to send to worker")
    workers_run.add_argument("--worker", "-w", dest="worker_name", help="Specific worker to use")
    workers_run.add_argument("--type", "-t", dest="task_type", help="Task type: search, summarize, extract")

    workers_parser.set_defaults(func=cmd_workers, workers_cmd=None, worker_name=None, prompt=None, task_type=None)

    # skills - Skill management
    skills_parser = subparsers.add_parser(
        "skills",
        help="Manage skill hotloading",
    )
    skills_subparsers = skills_parser.add_subparsers(dest="skills_cmd")

    # skills list
    skills_list = skills_subparsers.add_parser("list", help="List available skills")
    skills_list.add_argument("--local", action="store_true", help="Show only local skills")
    skills_list.add_argument("--global", dest="global_", action="store_true", help="Show only global skills")

    # skills show
    skills_show = skills_subparsers.add_parser("show", help="Show skill content")
    skills_show.add_argument("name", help="Skill name to show")

    # skills create
    skills_create = skills_subparsers.add_parser("create", help="Create a new skill")
    skills_create.add_argument("name", help="Skill name")
    skills_create.add_argument("--agent", "-a", action="append", dest="agents", help="Agent this skill applies to")
    skills_create.add_argument("--type", "-t", action="append", dest="task_types", help="Task type this skill applies to")
    skills_create.add_argument("--global", dest="global_", action="store_true", help="Create in global skills")

    # skills check
    skills_check = skills_subparsers.add_parser("check", help="Check for modified skills")

    skills_parser.set_defaults(func=cmd_skills, skills_cmd=None, name=None, agents=None, task_types=None, local=False, global_=False)

    # calcify - Calcification candidates
    calcify_parser = subparsers.add_parser(
        "calcify",
        help="View/execute polip calcification",
        description="Show polips ready to crystallize into bedrock based on time, usage, ceremony, consensus",
    )
    calcify_parser.add_argument("--all", "-a", action="store_true", help="Show all polips, not just candidates")
    calcify_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    calcify_parser.set_defaults(func=cmd_calcify)

    # decay - Adversarial decay
    decay_parser = subparsers.add_parser(
        "decay",
        help="Run adversarial decay challenges",
        description="Challenge stale/orphan polips to defend their existence",
    )
    decay_parser.add_argument("--execute", "-x", action="store_true", help="Execute decomposition (default: dry-run)")
    decay_parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    decay_parser.set_defaults(func=cmd_decay)

    # trench - Parallel Claude agents in git worktrees
    trench_parser = subparsers.add_parser(
        "trench",
        help="Manage parallel Claude sessions in git worktrees",
        description="Spawn isolated worktrees for parallel Claude development, test before merge",
    )
    trench_subparsers = trench_parser.add_subparsers(dest="trench_cmd")

    # trench spawn
    trench_spawn = trench_subparsers.add_parser("spawn", help="Spawn a new trench worktree")
    trench_spawn.add_argument("name", help="Unique name for this trench (e.g., 'feature-auth')")
    trench_spawn.add_argument("--task", "-t", help="Task for Claude to work on (auto-launches session)")
    trench_spawn.add_argument("--model", "-m", choices=["haiku", "sonnet", "opus"], help="Model override (default: auto-detected from task)")
    trench_spawn.add_argument("--base", "-b", help="Base branch (default: current branch)")

    # trench status
    trench_status = trench_subparsers.add_parser("status", help="Check trench status")
    trench_status.add_argument("name", nargs="?", help="Specific trench name (default: all)")
    trench_status.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    # trench test
    trench_test = trench_subparsers.add_parser("test", help="Run tests in a trench")
    trench_test.add_argument("name", help="Trench name")
    trench_test.add_argument("--cmd", "-c", default="uv run pytest", help="Test command (default: uv run pytest)")

    # trench merge
    trench_merge = trench_subparsers.add_parser("merge", help="Merge a trench if tests pass")
    trench_merge.add_argument("name", help="Trench name")
    trench_merge.add_argument("--no-delete", action="store_true", help="Keep branch after merge")

    # trench abort
    trench_abort = trench_subparsers.add_parser("abort", help="Abort and clean up a trench")
    trench_abort.add_argument("name", help="Trench name")
    trench_abort.add_argument("--force", "-f", action="store_true", help="Force removal (discard uncommitted changes)")

    # trench prune
    trench_prune = trench_subparsers.add_parser("prune", help="Prune stale trenches")
    trench_prune.add_argument("--days", "-d", type=int, default=3, help="Max age in days (default: 3)")
    trench_prune.add_argument("--execute", "-x", action="store_true", help="Actually prune (default: dry-run)")

    # trench cleanup
    trench_cleanup = trench_subparsers.add_parser("cleanup", help="Clean up all trenches")
    trench_cleanup.add_argument("--force", "-f", action="store_true", help="Force removal")

    # trench logs
    trench_logs = trench_subparsers.add_parser("logs", help="View Claude session output")
    trench_logs.add_argument("name", help="Trench name")
    trench_logs.add_argument("--lines", "-n", type=int, default=50, help="Number of lines to show (default: 50)")
    trench_logs.add_argument("--follow", "-f", action="store_true", help="Follow output (like tail -f)")

    trench_parser.set_defaults(func=cmd_trench, trench_cmd=None, name=None, json_output=False)

    # shell - Interactive REPL with ghost hints
    shell_parser = subparsers.add_parser(
        "shell",
        help="Interactive REPL with ghost text hints",
        description="Start reef shell with context-aware input hints from active threads",
    )
    shell_parser.add_argument("--hint", action="store_true", help="Show current hint and exit")
    shell_parser.set_defaults(func=cmd_shell)

    # Project command - generate LLM-specific projections from .reef
    project_parser = subparsers.add_parser(
        "project",
        help="Generate LLM-specific views from .reef",
        description="Project reef state into format optimized for specific LLMs. Reef is the source, projections are derived.",
    )
    project_parser.add_argument(
        "target",
        choices=["claude", "ollama", "gpt", "gemini", "raw"],
        help="Target LLM for projection",
    )
    project_parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    project_parser.add_argument("--full", action="store_true", help="Include all polips, not just high-vitality")
    project_parser.set_defaults(func=cmd_project)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
