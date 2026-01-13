# zoox

Symbiotic memory for AI.

A "reef" is a colony of polyps - lightweight XML context files that persist across sessions.

## Installation

```bash
pip install zoox
```

## Usage

```bash
# Spawn a new current (thread polyp)
zoox sprout thread "Implement user authentication"

# Spawn a deposit (decision polyp)
zoox sprout decision "Use JWT for auth tokens"

# Spawn bedrock (constraint polyp)
zoox sprout constraint "Use uv for package management"

# View reef health
zoox reef

# Migrate polyps to current schema
zoox migrate

# Sink stale session polyps
zoox sink --days 7

# Change polyp status
zoox status auth-thread blocked -b "Waiting for API approval"
zoox status auth-thread done

# Create snapshots for tracking changes
zoox snapshot create --name milestone-1
zoox snapshot list
zoox snapshot diff milestone-1

# Visualize reef relationships
zoox graph
zoox graph --dot | dot -Tpng -o reef.png

# Use templates for common polyp patterns
zoox template list
zoox template use bug "Login fails on Safari"
zoox template use feature "Dark mode support"
zoox template create my-bug --type thread --summary "Bug: {title}" --status active
zoox template delete my-bug

# Search polyps by content
zoox index --search "authentication"
zoox index --search "auth" --type thread --scope project
zoox index --type decision  # list all decisions

# Check reef integrity
zoox sync
zoox sync --fix  # auto-fix missing files, rebuild index, migrate
```

## Polyp Types

- **context** - Session state (auto-created by persist hook)
- **thread** (current) - Active work stream
- **decision** (deposit) - Architectural choice made
- **constraint** (bedrock) - Always-on rules
- **fact** (fossil) - Key information about project

## Polyp Scopes

- **session** - Only current session (ephemeral)
- **project** - Anytime in this project (persistent)
- **always** - Every interaction (global rules)

## Python API

```python
from zoox import Polyp, Reef, PolypType, PolypScope
from pathlib import Path

# Create a reef (collection of polyps)
reef = Reef(Path.cwd())

# Spawn a new polyp
polyp = Polyp(
    type=PolypType.THREAD,
    summary="Implement user auth",
    scope=PolypScope.PROJECT,
)
reef.sprout(polyp, "auth-thread", subdir="threads")

# Surface relevant polyps
relevant = reef.surface_relevant(query="authentication")
```

## How It Works

Polyps live in your project's `.claude/` directory as XML files. The surfacing hook brings relevant polyps at session start. The persist hook auto-creates context polyps at session end.

## Claude Code Integration

zoox provides native hook commands for Claude Code integration:

```bash
# Check hook status
zoox hook status

# Generate settings.json configuration
zoox hook setup
zoox hook setup --json  # Raw JSON output
```

### Quick Setup

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "zoox hook surface" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "zoox hook persist" }
        ]
      }
    ]
  }
}
```

### Hook Commands

| Command | Event | Purpose |
|---------|-------|---------|
| `zoox hook surface` | UserPromptSubmit | Inject relevant polyps into context |
| `zoox hook persist` | Stop | Save session state as context polyp |
| `zoox hook setup` | - | Generate settings.json config |
| `zoox hook status` | - | Check hook health |

### Persist Options

```bash
# Save session with custom summary
zoox hook persist --summary "Completed auth feature"

# Include files touched
zoox hook persist --files "src/auth.py,src/users.py"

# Add next steps for continuity
zoox hook persist --next "Write tests|Update docs"

# Silent mode (for hooks)
zoox hook persist --quiet
```

## Drift: Cross-Project Discovery

Drift enables polyps to spread across projects. Global constraints, shared decisions, and common facts can be discovered from sibling projects and `~/.claude/`.

### Discovery Sources

| Source | Path | Enabled By Default |
|--------|------|-------------------|
| Global | `~/.claude/` | Yes |
| Siblings | `../*/. claude/` | Yes |
| Configured | `drift.json` paths | Manual |

### Commands

```bash
# Discover nearby reefs
zoox drift discover

# List polyps available for drift (default: always scope only)
zoox drift list
zoox drift list --scope always,project  # include more scopes

# Copy a polyp into current reef
zoox drift pull project-b/constraints/shared-rule

# Configure drift paths
zoox drift config
zoox drift config --add-path ~/work/shared-project
zoox drift config --remove-path ~/old-project
```

### With Hook Integration

```bash
# Surface includes drift polyps
zoox hook surface --drift
```

Or update settings.json:
```json
{ "type": "command", "command": "zoox hook surface --drift" }
```

### Scope Filtering

By default, only `always` scope polyps drift (constraints). This prevents noise from project-specific threads and decisions.

| Scope | Drifts By Default | Use Case |
|-------|-------------------|----------|
| `always` | Yes | Global rules, org standards |
| `project` | No | Project-specific work |
| `session` | No | Ephemeral context |

## Templates

Templates provide reusable polyp patterns. Built-in templates cover common workflows; custom templates let you define your own.

### Built-in Templates

| Name | Type | Use Case |
|------|------|----------|
| `bug` | thread | Bug reports with reproduction steps |
| `feature` | thread | Feature requests with acceptance criteria |
| `spike` | thread | Research/exploration tasks |
| `refactor` | thread | Code improvement tasks |
| `infra` | thread | Infrastructure changes |

### Custom Templates

```bash
# Create a custom template
zoox template create hotfix \
  --type thread \
  --summary "Hotfix: {title}" \
  --status active \
  --description "Urgent fix for production issues"

# List all templates
zoox template list

# Show template details
zoox template show hotfix

# Delete custom template
zoox template delete hotfix
```

## Index Search

The metadata index enables fast polyp discovery without loading full XML.

```bash
# Search by summary text
zoox index --search "authentication"

# Filter by type, scope, or status
zoox index --type thread --status active
zoox index --scope always
zoox index --search "api" --type decision

# Limit results
zoox index --search "bug" --limit 5

# View index statistics
zoox index --stats
```

## Sync: Integrity Checker

The `sync` command detects reef health issues:

```bash
# Check for issues
zoox sync

# Auto-fix where possible
zoox sync --fix
```

### What Sync Checks

| Issue | Auto-Fix | Manual Fix |
|-------|----------|------------|
| Missing file refs | Yes (removes) | Edit polyp |
| Stale session polyps | No | `zoox sink` |
| Orphan index entries | Yes (rebuild) | `zoox index --rebuild` |
| Broken related refs | No | Edit polyp |
| Schema outdated | Yes (migrate) | `zoox migrate` |

## Performance

zoox is optimized for **human-scale** memory, not big data. Here's what to expect:

| Polyp Count | Performance | Notes |
|-------------|-------------|-------|
| 10-100 | Instant | Ideal for most projects |
| 100-500 | Fast (~50ms) | Sweet spot for active development |
| 500-1000 | Acceptable (~100ms) | Consider archiving old polyps |
| 1000+ | Slower | Use `zoox cleanup` aggressively |

**Why these limits?**

- XML parsing: ~0.1ms per polyp (simple, no external deps)
- File I/O: ~0.5ms per polyp (filesystem bound)
- Surfacing loads ALL polyps to score relevance

**Recommendations:**

1. **Archive aggressively** - Use `zoox sink` to move stale session polyps to archive
2. **Use cleanup** - Run `zoox cleanup` at session start (swarm-safe, once-per-day)
3. **Scope wisely** - Only `always` scope for true global rules; prefer `project` scope
4. **Prune threads** - Mark completed currents as `done`, let cleanup archive them

**Token budget:** ~200-500 tokens per surfaced polyp. At 10 polyps surfaced, expect ~2-5K tokens in context.

## Terminology

The naming is inspired by coral reef biology:

| Term | Meaning |
|------|---------|
| **polyp** | Individual memory unit (was: blob) |
| **reef** | Project colony (was: glob) |
| **current** | Active work thread |
| **bedrock** | Foundation constraints |
| **deposit** | Strategic decisions |
| **drift** | Cross-project spread |

*Zooxanthellae* are the symbiotic algae that live inside coral, producing 90% of the coral's energy. Without them, coral bleaches and dies. Memory without context starves. Memory with rich context thrives.

**zoox: Symbiotic memory for AI.**
