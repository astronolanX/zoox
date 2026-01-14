# reef Roadmap

Where reef is going and how you can help.

## Status Legend

| Icon | Meaning |
|------|---------|
| :green_circle: | Shipped |
| :yellow_circle: | In Progress |
| :white_circle: | Planned |
| :thought_balloon: | Considering |

## Core Framework

| Feature | Status | Version | Notes |
|---------|--------|---------|-------|
| Polip/Reef data model | :green_circle: | v0.1.0 | XML persistence, type/scope system |
| TF-IDF search | :green_circle: | v0.1.0 | Semantic relevance scoring |
| Wiki linking | :green_circle: | v0.1.0 | `[[polip-name]]` syntax |
| LRU boosting | :green_circle: | v0.1.0 | Frequently-used polips surface higher |
| Template expansion | :green_circle: | v0.1.0 | `{date}`, `{git_branch}`, `{project_name}` |
| Vector embeddings | :thought_balloon: | - | Semantic search beyond TF-IDF |
| Polip versioning | :thought_balloon: | - | Track changes to individual polips |

## CLI

| Feature | Status | Version | Notes |
|---------|--------|---------|-------|
| Full command suite | :green_circle: | v0.1.0 | sprout, reef, migrate, sink, status, snapshot, graph, template, index, sync, drift |
| Interactive TUI | :white_circle: | - | Browse and edit reef visually |
| Watch mode | :thought_balloon: | - | Live refresh on file changes |
| Shell completions | :white_circle: | - | bash/zsh/fish tab completion |

## Integrations

| Feature | Status | Version | Notes |
|---------|--------|---------|-------|
| Claude Code hooks | :green_circle: | v0.1.0 | surface, persist, setup, status |
| MCP server | :white_circle: | - | Expose reef via Model Context Protocol |
| VS Code extension | :thought_balloon: | - | Sidebar reef browser |
| Raycast extension | :thought_balloon: | - | Quick polip creation/search |

## Cross-Project

| Feature | Status | Version | Notes |
|---------|--------|---------|-------|
| Drift discovery | :green_circle: | v0.1.0 | Find polips in sibling projects |
| Drift pull | :green_circle: | v0.1.0 | Copy polips between reefs |
| Drift push | :thought_balloon: | - | Share polips to central reef |
| Reef federation | :thought_balloon: | - | Sync reefs across machines |

## Developer Experience

| Feature | Status | Version | Notes |
|---------|--------|---------|-------|
| Zero dependencies | :green_circle: | v0.1.0 | stdlib only |
| Python API | :green_circle: | v0.1.0 | Polip, Reef, PolipType, PolipScope |
| Type hints | :green_circle: | v0.1.0 | Full typing throughout |
| Comprehensive tests | :green_circle: | v0.1.0 | pytest suite with stress tests |
| PyPI publishing | :white_circle: | - | `pip install reef` |

---

## Want to Help?

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get involved.

**Ways to contribute:**
- :white_circle: items are actively planned - PRs welcome
- :thought_balloon: items are open for discussion - file an issue to start the conversation
- Bug reports and feature requests always appreciated

## Suggesting New Features

File an issue with:
1. **Problem** - What are you trying to do?
2. **Proposal** - How would this work?
3. **Alternatives** - What else did you consider?

We'll discuss and potentially add it to this roadmap.
