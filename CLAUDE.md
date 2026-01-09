# Goopy

XML blob system for Claude Code session memory.

## Dev Commands

```bash
uv run pytest          # Run tests
uv run pytest -x       # Stop on first failure
uv run python -m goopy # CLI entry point
```

## Constraints

- **Zero dependencies** - stdlib only, no external packages
- **Local-only** - not published to PyPI
- Use `uv` for package management, not pip

## Architecture

- `src/goopy/blob.py` - Core Blob/Glob classes
- `src/goopy/cli.py` - CLI commands
- `.claude/` directories store blobs as XML files
- Blob types: thread, decision, constraint, context, fact
- Blob scopes: always, project, session
