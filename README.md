# Goopy

XML blob system for Claude Code session memory.

A "glob" is a collection of blobs - lightweight XML context files that persist across sessions.

## Installation

```bash
uv add goopy
```

## Usage

```bash
# Create a new thread blob
goopy sprout thread "Implement user authentication"

# Create a decision blob
goopy sprout decision "Use JWT for auth tokens"

# Create a constraint blob (always-on rules)
goopy sprout constraint "Use uv for package management"

# List blob health
goopy list

# Migrate blobs to current schema
goopy migrate

# Archive stale session blobs
goopy decompose --days 7
```

## Blob Types

- **context** - Session state (auto-created by persist hook)
- **thread** - Active work stream
- **decision** - Architectural choice made
- **constraint** - Always-on rules
- **fact** - Key information about project

## Blob Scopes

- **session** - Only current session (ephemeral)
- **project** - Anytime in this project (persistent)
- **always** - Every interaction (global rules)

## How It Works

Blobs live in your project's `.claude/` directory as XML files. The glob injection hook surfaces relevant blobs at session start. The persist hook auto-creates context blobs at session end.

This is separate from [flubber](https://github.com/astronolanX/flubber), which handles multi-agent coordination via spores. Goopy is for human-agent session continuity.
