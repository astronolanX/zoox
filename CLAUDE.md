# reef

Symbiotic memory for AI.

## Dev Commands

```bash
uv run pytest              # Run tests
uv run pytest -x           # Stop on first failure
uv run python -m reef.cli  # CLI entry point
reef reef                  # View reef health
reef sync                  # Check reef integrity
reef index --search "foo"  # Search polips
```

## Constraints

- **Zero dependencies** - stdlib only, no external packages
- **Local-only** - not published to PyPI (yet)
- Use `uv` for package management, not pip

## Architecture

- `src/reef/blob.py` - Core Polip/Reef classes (Blob/Glob aliases)
- `src/reef/cli.py` - CLI commands with coral terminology
- `.claude/` directories store polips as XML files
- Polip types: thread (current), decision (deposit), constraint (bedrock), context, fact (fossil)
- Polip scopes: always, project, session

## Key Commands

| Command | Purpose |
|---------|---------|
| `reef init --gitignore` | Setup with team-friendly .gitignore |
| `reef sprout thread "summary"` | Create new current |
| `reef reef` | View reef health |
| `reef sync` | Check integrity |
| `reef sync --fix` | Auto-repair issues |
| `reef index --search "query"` | TF-IDF fuzzy search |
| `reef index --type thread` | Filter by type |
| `reef template list` | Show templates |
| `reef template create name` | Create custom template |
| `reef drift discover` | Find nearby reefs |

## Progressive Loading (L1/L2/L3)

Polips use token-efficient progressive disclosure:

| Level | Content | When |
|-------|---------|------|
| **L1** | Metadata index (id, type, summary, tokens) | Always at session start |
| **L2** | Full polip content | On-demand via `/surface <id>` |
| **L3** | Related files, linked polips | Explicit request |

**Example L1 index:**
```xml
<polip-index updated="2026-01-14" count="3" mode="L1">
  <polip id="constraints-project-rules" type="constraint" priority="100">
    <summary>reef project constraints</summary>
    <tokens>152</tokens>
  </polip>
</polip-index>
```

**Load full content:**
```bash
/surface constraints-project-rules  # L2 activation
```

## P7 Features

- **TF-IDF search**: Fuzzy semantic search using term frequency-inverse document frequency
- **Wiki linking**: Use `[[polip-name]]` in content; auto-populates `related` field
- **LRU tracking**: Access counts boost frequently-used polips in surfacing
- **Rich templates**: `{date}`, `{git_branch}`, `{project_name}` in template expansion

## Terminology

| Coral | Legacy | Meaning |
|-------|--------|---------|
| polip | blob | Individual memory unit |
| reef | glob | Project colony |
| spawn | sprout | Create polip |
| surface | inject | Bring polip to context |
| sink | decompose | Archive to deep reef |
| current | thread | Active work stream |
| bedrock | constraint | Foundation rules |
| deposit | decision | Strategic choice |
| fossil | fact | Preserved knowledge |
