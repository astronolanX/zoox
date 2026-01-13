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

## How It Works

Polyps live in your project's `.claude/` directory as XML files. The glob injection hook surfaces relevant polyps at session start. The persist hook auto-creates context polyps at session end.

## Terminology

The naming is inspired by coral reef biology:

| Term | Meaning |
|------|---------|
| **polyp** | Individual memory unit (was: blob) |
| **reef** | Project colony (was: glob) |
| **current** | Active work thread |
| **bedrock** | Foundation constraints |
| **deposit** | Strategic decisions |
| **drift** | Cross-project spread (coming soon) |

*Zooxanthellae* are the symbiotic algae that live inside coral, producing 90% of the coral's energy. Without them, coral bleaches and dies. Memory without context starves. Memory with rich context thrives.

**zoox: Symbiotic memory for AI.**
