# zoox

Symbiotic memory for AI.

## Dev Commands

```bash
uv run pytest              # Run tests
uv run pytest -x           # Stop on first failure
uv run python -m zoox.cli  # CLI entry point
zoox reef                  # View reef health
zoox sync                  # Check reef integrity
zoox index --search "foo"  # Search polyps
```

## Constraints

- **Zero dependencies** - stdlib only, no external packages
- **Local-only** - not published to PyPI (yet)
- Use `uv` for package management, not pip

## Architecture

- `src/zoox/blob.py` - Core Polyp/Reef classes (Blob/Glob aliases)
- `src/zoox/cli.py` - CLI commands with coral terminology
- `.claude/` directories store polyps as XML files
- Polyp types: thread (current), decision (deposit), constraint (bedrock), context, fact (fossil)
- Polyp scopes: always, project, session

## Key Commands

| Command | Purpose |
|---------|---------|
| `zoox sprout thread "summary"` | Create new current |
| `zoox reef` | View reef health |
| `zoox sync` | Check integrity |
| `zoox sync --fix` | Auto-repair issues |
| `zoox index --search "query"` | Search polyps |
| `zoox index --type thread` | Filter by type |
| `zoox template list` | Show templates |
| `zoox template create name` | Create custom template |
| `zoox drift discover` | Find nearby reefs |

## Terminology

| Coral | Legacy | Meaning |
|-------|--------|---------|
| polyp | blob | Individual memory unit |
| reef | glob | Project colony |
| spawn | sprout | Create polyp |
| surface | inject | Bring polyp to context |
| sink | decompose | Archive to deep reef |
| current | thread | Active work stream |
| bedrock | constraint | Foundation rules |
| deposit | decision | Strategic choice |
| fossil | fact | Preserved knowledge |
