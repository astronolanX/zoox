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
| **drift** | Cross-project spread (coming soon) |

*Zooxanthellae* are the symbiotic algae that live inside coral, producing 90% of the coral's energy. Without them, coral bleaches and dies. Memory without context starves. Memory with rich context thrives.

**zoox: Symbiotic memory for AI.**
