# reef

![Status](https://img.shields.io/badge/status-beta-yellow)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)

Symbiotic memory for AI.

A "reef" is a colony of polips - lightweight XML context files that persist across sessions.

## Installation

```bash
pip install reef
```

## MCP Server (Universal AI Memory)

reef works as an MCP server - plug it into Claude Desktop, Cursor, or any MCP client:

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "reef": {
      "command": "reef-mcp",
      "args": ["--project-dir", "/path/to/your/project"]
    }
  }
}
```

**What AI gets:**
| Tool | Purpose |
|------|---------|
| `reef_surface` | Search and retrieve relevant polips |
| `reef_sprout` | Create new polips (threads, decisions, facts) |
| `reef_health` | Check reef vitality score |
| `reef_index` | Browse polip metadata |
| `reef_sync` | Check integrity |
| `reef_audit` | Query operation history |
| `reef_undo` | Restore quarantined polips |

**Resources:**
- `reef://polips` - Full polip index
- `reef://health` - Vitality metrics

Test it works:
```bash
reef-mcp --test
# Reef MCP Server v0.1.0
# Project: /your/project
# Tools: 8
# Resources: 2
```

## Usage

```bash
# Spawn a new current (thread polip)
reef sprout thread "Implement user authentication"

# Spawn a deposit (decision polip)
reef sprout decision "Use JWT for auth tokens"

# Spawn bedrock (constraint polip)
reef sprout constraint "Use uv for package management"

# View reef health
reef reef

# Migrate polips to current schema
reef migrate

# Sink stale session polips
reef sink --days 7

# Change polip status
reef status auth-thread blocked -b "Waiting for API approval"
reef status auth-thread done

# Create snapshots for tracking changes
reef snapshot create --name milestone-1
reef snapshot list
reef snapshot diff milestone-1

# Visualize reef relationships
reef graph
reef graph --dot | dot -Tpng -o reef.png

# Use templates for common polip patterns
reef template list
reef template use bug "Login fails on Safari"
reef template use feature "Dark mode support"
reef template create my-bug --type thread --summary "Bug: {title}" --status active
reef template delete my-bug

# Search polips by content
reef index --search "authentication"
reef index --search "auth" --type thread --scope project
reef index --type decision  # list all decisions

# Check reef integrity
reef sync
reef sync --fix  # auto-fix missing files, rebuild index, migrate
```

## Polip Types

- **context** - Session state (auto-created by persist hook)
- **thread** (current) - Active work stream
- **decision** (deposit) - Architectural choice made
- **constraint** (bedrock) - Always-on rules
- **fact** (fossil) - Key information about project

## Polip Scopes

- **session** - Only current session (ephemeral)
- **project** - Anytime in this project (persistent)
- **always** - Every interaction (global rules)

## Python API

```python
from reef import Polip, Reef, PolipType, PolipScope
from pathlib import Path

# Create a reef (collection of polips)
reef = Reef(Path.cwd())

# Spawn a new polip
polip = Polip(
    type=PolipType.THREAD,
    summary="Implement user auth",
    scope=PolipScope.PROJECT,
)
reef.sprout(polip, "auth-thread", subdir="threads")

# Surface relevant polips
relevant = reef.surface_relevant(query="authentication")
```

## How It Works

Polips live in your project's `.claude/` directory as XML files. The surfacing hook brings relevant polips at session start. The persist hook auto-creates context polips at session end.

## Claude Code Integration

reef provides native hook commands for Claude Code integration:

```bash
# Check hook status
reef hook status

# Generate settings.json configuration
reef hook setup
reef hook setup --json  # Raw JSON output
```

### Quick Setup

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "reef hook surface" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "reef hook persist" }
        ]
      }
    ]
  }
}
```

### Hook Commands

| Command | Event | Purpose |
|---------|-------|---------|
| `reef hook surface` | UserPromptSubmit | Inject relevant polips into context |
| `reef hook persist` | Stop | Save session state as context polip |
| `reef hook setup` | - | Generate settings.json config |
| `reef hook status` | - | Check hook health |

### Persist Options

```bash
# Save session with custom summary
reef hook persist --summary "Completed auth feature"

# Include files touched
reef hook persist --files "src/auth.py,src/users.py"

# Add next steps for continuity
reef hook persist --next "Write tests|Update docs"

# Silent mode (for hooks)
reef hook persist --quiet
```

## Drift: Cross-Project Discovery

Drift enables polips to spread across projects. Global constraints, shared decisions, and common facts can be discovered from sibling projects and `~/.claude/`.

### Discovery Sources

| Source | Path | Enabled By Default |
|--------|------|-------------------|
| Global | `~/.claude/` | Yes |
| Siblings | `../*/. claude/` | Yes |
| Configured | `drift.json` paths | Manual |

### Commands

```bash
# Discover nearby reefs
reef drift discover

# List polips available for drift (default: always scope only)
reef drift list
reef drift list --scope always,project  # include more scopes

# Copy a polip into current reef
reef drift pull project-b/constraints/shared-rule

# Configure drift paths
reef drift config
reef drift config --add-path ~/work/shared-project
reef drift config --remove-path ~/old-project
```

### With Hook Integration

```bash
# Surface includes drift polips
reef hook surface --drift
```

Or update settings.json:
```json
{ "type": "command", "command": "reef hook surface --drift" }
```

### Scope Filtering

By default, only `always` scope polips drift (constraints). This prevents noise from project-specific threads and decisions.

| Scope | Drifts By Default | Use Case |
|-------|-------------------|----------|
| `always` | Yes | Global rules, org standards |
| `project` | No | Project-specific work |
| `session` | No | Ephemeral context |

## Templates

Templates provide reusable polip patterns. Built-in templates cover common workflows; custom templates let you define your own.

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
reef template create hotfix \
  --type thread \
  --summary "Hotfix: {title}" \
  --status active \
  --description "Urgent fix for production issues"

# List all templates
reef template list

# Show template details
reef template show hotfix

# Delete custom template
reef template delete hotfix
```

## Index Search

The metadata index enables fast polip discovery without loading full XML.

```bash
# Search by summary text
reef index --search "authentication"

# Filter by type, scope, or status
reef index --type thread --status active
reef index --scope always
reef index --search "api" --type decision

# Limit results
reef index --search "bug" --limit 5

# View index statistics
reef index --stats
```

## Sync: Integrity Checker

The `sync` command detects reef health issues:

```bash
# Check for issues
reef sync

# Auto-fix where possible
reef sync --fix
```

### What Sync Checks

| Issue | Auto-Fix | Manual Fix |
|-------|----------|------------|
| Missing file refs | Yes (removes) | Edit polip |
| Stale session polips | No | `reef sink` |
| Orphan index entries | Yes (rebuild) | `reef index --rebuild` |
| Broken related refs | No | Edit polip |
| Schema outdated | Yes (migrate) | `reef migrate` |

## Team Workflows

reef uses **git as the sync mechanism** - no special server required.

### Quick Setup

```bash
# Initialize reef with team-friendly .gitignore
reef init --gitignore

# Or append to existing .gitignore
reef init --gitignore --append
```

### What to Commit

| Polip Type | Scope | Commit? | Reason |
|------------|-------|---------|--------|
| **constraints/** | always | Yes | Team-wide rules |
| **decisions/** | project | Yes | Architectural records |
| **facts/** | project | Yes | Shared knowledge |
| **threads/** | project | Maybe | Active work (your call) |
| **contexts/** | session | No | Ephemeral per-session |
| **archive/** | - | No | Historical, can rebuild |
| **index.json** | - | No | Generated, can rebuild |

### Recommended .gitignore

```gitignore
# reef - Commit constraints and decisions, ignore ephemeral
.claude/context.blob.xml
.claude/contexts/
.claude/index.json
.claude/archive/
.claude/snapshots/
```

### Team Patterns

**Shared Constraints (bedrock):**
```bash
# Alice creates constraint
reef sprout constraint "Use TypeScript for all frontend"
git add .claude/constraints/
git commit -m "feat: add TypeScript constraint"
git push

# Bob pulls and surfaces it automatically
git pull
reef reef  # Shows new constraint
```

**Architectural Decisions (ADR):**
```bash
# Create ADR using template
reef template use decision "Use PostgreSQL for persistence"

# Edit the generated polip to add context
# Then commit
git add .claude/decisions/
git commit -m "docs: ADR for PostgreSQL"
```

**Thread Handoff:**
```bash
# Alice working on auth
reef sprout thread "Implement OAuth2 login"
# ... work in progress ...

# Hand off to Bob
reef status oauth-login blocked -b "Needs Bob's API expertise"
git add .claude/threads/
git commit -m "wip: OAuth2 in progress, blocked on API"
git push

# Bob picks it up
git pull
reef status oauth-login active
```

### Cross-Project with Drift

Share polips between projects without committing to each repo:

```bash
# Discover nearby reefs
reef drift discover

# Pull shared constraints from global reef
reef drift pull ~/.claude/constraints/security-rules

# Configure additional drift sources
reef drift config --add-path ~/work/shared-standards/.claude
```

### Wiki-Style Linking

Create knowledge graphs with `[[wiki links]]`:

```bash
# Reference other polips in content
reef sprout thread "Implement [[oauth-login]] for [[user-dashboard]]"

# Related field auto-populates
reef index --search "oauth"
```

## Performance

reef is optimized for **human-scale** memory, not big data. Here's what to expect:

| Polip Count | Performance | Notes |
|-------------|-------------|-------|
| 10-100 | Instant | Ideal for most projects |
| 100-500 | Fast (~50ms) | Sweet spot for active development |
| 500-1000 | Acceptable (~100ms) | Consider archiving old polips |
| 1000+ | Slower | Use `reef cleanup` aggressively |

**Why these limits?**

- XML parsing: ~0.1ms per polip (simple, no external deps)
- File I/O: ~0.5ms per polip (filesystem bound)
- Surfacing loads ALL polips to score relevance

**Recommendations:**

1. **Archive aggressively** - Use `reef sink` to move stale session polips to archive
2. **Use cleanup** - Run `reef cleanup` at session start (swarm-safe, once-per-day)
3. **Scope wisely** - Only `always` scope for true global rules; prefer `project` scope
4. **Prune threads** - Mark completed currents as `done`, let cleanup archive them

**Token budget:** ~200-500 tokens per surfaced polip. At 10 polips surfaced, expect ~2-5K tokens in context.

## Terminology

The naming is inspired by coral reef biology:

| Term | Meaning |
|------|---------|
| **polip** | Individual memory unit (was: blob) |
| **reef** | Project colony (was: glob) |
| **current** | Active work thread |
| **bedrock** | Foundation constraints |
| **deposit** | Strategic decisions |
| **drift** | Cross-project spread |

*Zooxanthellae* are the symbiotic algae that live inside coral, producing 90% of the coral's energy. Without them, coral bleaches and dies. Memory without context starves. Memory with rich context thrives.

**reef: Symbiotic memory for AI.**
