# Changelog

All notable changes to reef are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project communication suite (CHANGELOG, ROADMAP, CONTRIBUTING)

## [0.1.0] - 2026-01-14

Initial public release. Symbiotic memory for AI.

### Added

**Core Framework**
- Polip/Reef data model with XML persistence
- Type system: thread (current), decision (deposit), constraint (bedrock), context, fact (fossil)
- Scope system: session, project, always
- Coral terminology throughout (polip, reef, spawn, surface, sink, drift)

**CLI Commands**
- `reef sprout` - Create polips (thread, decision, constraint, fact)
- `reef reef` - View reef health and statistics
- `reef migrate` - Update polips to current schema
- `reef sink` - Archive stale session polips
- `reef status` - Change polip status (active, blocked, done)
- `reef snapshot` - Create/list/diff snapshots for tracking changes
- `reef graph` - Visualize reef relationships (ASCII + DOT export)
- `reef template` - Manage templates (list, use, create, delete)
- `reef index` - Search polips by content, type, scope
- `reef sync` - Check reef integrity with auto-fix option
- `reef drift` - Cross-project polip discovery

**P7 Smart Surfacing**
- TF-IDF search for semantic relevance scoring
- Wiki-style `[[linking]]` between polips
- LRU tracking to boost frequently-accessed polips
- Rich template expansion with `{date}`, `{git_branch}`, `{project_name}`

**Claude Code Integration**
- `reef hook surface` - Inject relevant polips at session start
- `reef hook persist` - Save session state at session end
- `reef hook setup` - Generate settings.json configuration
- `reef hook status` - Check hook health

**Templates**
- Built-in: bug, feature, spike, refactor, infra
- Custom template CRUD with type, summary, status, description

**Drift (Cross-Project Discovery)**
- Discover polips from `~/.claude/` and sibling projects
- Scope filtering (only `always` scope drifts by default)
- `drift pull` to copy polips into current reef

**Performance**
- Index caching for fast polip discovery
- Batch operations for bulk updates
- Swarm-safe cleanup with lock file coordination

### Security
- Atomic file writes to prevent corruption
- Path traversal protection
- Controlled cleanup with lock files
- No external dependencies (stdlib only)

### Changed
- Renamed from goopy to zoox to reef (symbiotic memory branding)
- Renamed blob/glob to polip/reef (coral terminology)

[Unreleased]: https://github.com/nolan/reef/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nolan/reef/releases/tag/v0.1.0
