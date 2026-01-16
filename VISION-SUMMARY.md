# Reef as Native AI Infrastructure - Executive Summary

## The Big Idea

Make `.reef` directories as fundamental to AI-assisted development as `.git` is to version control. Every AI coding project should have one. Tools should auto-detect it. Missing it should feel wrong.

## Critical Decision: Format Change

**Move from XML to Markdown + YAML Frontmatter**

### Current Format (XML)
```xml
<blob type="context" scope="session" updated="2026-01-16" v="2">
  <summary>...</summary>
  <decisions>...</decisions>
  <next>...</next>
</blob>
```

### Proposed Format (Markdown + YAML)
```markdown
---
id: auth-implementation
type: thread
scope: project
status: active
tags: [auth, security]
related: [jwt-decision, zero-deps-constraint]
---

# Feature: Auth Implementation

## Context
Need authentication without external dependencies.

## Decisions
- JWT with stdlib only
- 24h token expiration

## Next Steps
- [ ] Implement token generation
- [ ] Add auth middleware
- [ ] Write tests

## Links
[[jwt-decision]] - Why JWT over sessions
```

### Why This Matters

| Factor | XML | Markdown + YAML |
|--------|-----|-----------------|
| **LLM Training** | Some | Extensive |
| **Developer Familiarity** | Low | Universal |
| **Editor Support** | Limited | Native everywhere |
| **Human Editing** | Painful | Natural |
| **Comments** | Verbose | Built-in |
| **Modern Sentiment** | "XML is dead" | "Markdown won" |

**GitHub Flavored Markdown became THE standard** by 2026. Every platform adopted it. Developers expect it. Tools support it natively. This is the format AI infrastructure should use.

## Simplified Structure

### Current (Fragmented)
```
.reef/           # New architecture
  bedrock/
  current/
  index.json
  reef.manifest

.claude/         # Legacy/compatibility
  threads/
  decisions/
  constraints/
```

### Proposed (Unified)
```
.reef/
├── manifest.md         # Human-friendly project declaration
├── index.json          # Machine-generated fast lookup
├── polips/
│   ├── threads/
│   ├── decisions/
│   ├── constraints/
│   └── contexts/
└── .reefignore         # Exclude patterns
```

**Single source of truth. Clear hierarchy. Git-like simplicity.**

## Path to Native Status

### Phase 1: Foundation (Months 1-3)
- Migrate format to markdown + YAML
- Consolidate to `.reef/` only
- Write formal specification
- Build migration tooling

### Phase 2: Discoverability (Months 3-6)
- VSCode extension (syntax, preview, navigation)
- GitHub syntax highlighting
- Template library
- File association standards

### Phase 3: Ecosystem (Months 6-12)
- AI assistants auto-detect reef
- Framework CLIs include `reef init`
- CI/CD reef-aware checks
- MCP integration

### Phase 4: Network Effects (Year 2+)
- Gallery of public reefs
- Industry templates
- Standards body participation
- "Where's your reef?" is common

## What Makes Formats "Native"? (Research Findings)

### The Universal Pattern

1. **Solves Real Pain** - Unavoidable problem (Git artifacts, package deps)
2. **Convention Over Config** - Predictable location, zero ceremony
3. **Tool Recognition** - IDEs, linters, frameworks know about it
4. **Network Effects** - More adoption → more support → more adoption
5. **Format Clarity** - Human readable, machine parseable

### Case Studies

**`.gitignore`** - Emerged with Git (2005), plain text, solved build artifact problem
**`package.json`** - Created with npm (2010), JSON, enabled registry network effect
**`tsconfig.json`** - TypeScript compiler (2012), JSON, tool ecosystem rallied
**`.editorconfig`** - Cross-editor (2011), INI format, slow but steady champion building

### Current AI Landscape (2026)

- **MCP:** Protocol standard (donated to Linux Foundation), not file format
- **`/llms.txt`:** Emerging markdown convention for website AI context
- **AI configs:** Fragmented (`.cursorrules`, `CLAUDE.md`, `.windsurfrules`)
- **No winner yet:** Opportunity for reef to become the standard

## Key Insights from Research

### Format Preferences (2026)

**Markdown Dominance:**
- GitHub Flavored Markdown is universal by 2026
- Every platform (GitLab, Bitbucket, Discord) adopted GFM features
- AI tools, documentation, technical writing all use markdown
- Became "de facto standard" beyond GitHub itself

**YAML for Config:**
- DevOps infrastructure standard
- Human-editable with comment support
- Widely used despite security concerns
- Works well as frontmatter in markdown

**XML Decline:**
- "Writing XML by hand is tedious"
- Modern developers avoid unless required
- Enterprise legacy only
- Strong negative sentiment

**JSON Limitations:**
- No comments = poor for configuration
- Machine-to-machine, not human editing
- Fine for generated files (index.json)

### Hidden Directory Success

**Why `.git/` works:**
- Separation of concerns (tool data vs user files)
- Prevents accidental modification
- Clean workspace
- Developer muscle memory

**Reef should follow this pattern:**
- `.reef/` for all memory infrastructure
- Add to `.gitignore` for generated files (index.json)
- Manifest at root for discoverability
- Type-based subdirectories for organization

### Adoption Strategies That Work

**Champion Building:**
- Most critical factor for tool adoption
- Build organic support from engineers
- Create compelling real-life use cases
- Demonstrate immediate value

**Registry Effects:**
- Package managers need central registry
- Network effects from shared resources
- Discovery through community
- Templates, examples, galleries

**Integration Over Isolation:**
- Successful tools integrate with existing workflow
- Don't require new mental models
- Work with Git, editors, CI/CD
- Enhance rather than replace

## Competitive Positioning

### Why Not Just Use...?

| Alternative | Why It's Different | Reef's Advantage |
|-------------|-------------------|------------------|
| **MCP** | Protocol, not storage | Persistent memory layer |
| **`.cursorrules`** | Tool-specific (Cursor) | Tool-agnostic with projections |
| **`CLAUDE.md`** | Single file, no structure | Semantic types, relationships |
| **Obsidian/Foam** | Personal knowledge management | Project-scoped, AI-native |
| **Git commits** | Code change tracking | Context + decision layer |

**Reef's unique position:** AI-native memory format that projects to any tool.

## Implementation Priorities

### Must Have (Phase 1)
1. Markdown + YAML frontmatter format
2. Migration tool from XML
3. Formal specification document
4. `.reef/` consolidation

### Should Have (Phase 2)
1. VSCode extension
2. Template library
3. Validation tooling
4. GitHub syntax highlighting

### Nice to Have (Phase 3)
1. Framework CLI integration
2. Multiple editor plugins
3. CI/CD examples
4. Public reef gallery

## Success Metrics

**6 Months:**
- 100+ projects using reef v2
- VSCode extension published
- Complete specification
- 50+ templates shared

**1 Year:**
- 3+ AI assistants auto-detect reef
- 5+ frameworks include reef in init
- Stable spec, no breaking changes
- Featured in AI tool docs

**2+ Years:**
- Reef discussed alongside MCP, `/llms.txt`
- Missing reef signals immature AI project
- Formal standards body
- "Where's your reef?" common question

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Format lock-in | Versioned format, projection system |
| Implementation divergence | Reference impl + formal spec |
| AI tool churn | Tool-agnostic design, plain text survives |
| Low adoption | Immediate standalone value, champion building |
| Security (secrets in polips) | `.reefignore`, pre-commit hooks, docs |

## The Bottom Line

**Three things need to happen:**

1. **Format clarity** - Markdown + YAML is the right choice
2. **Structural simplicity** - One directory, clear purpose
3. **Ecosystem momentum** - Tools, templates, community

**The opportunity exists because:**
- AI coding tools lack memory standards
- Context management is universally painful
- No competitor occupies this space
- Format battle settled (markdown won)

**The path is proven:**
- Follow `.git`, `package.json`, `.editorconfig` patterns
- Solve real problems with simple conventions
- Build ecosystem through integration
- Let network effects take over

**The question:** Will reef become the expected standard for AI project memory?

**The answer depends on:** Committing to markdown, building the tooling, and enabling the community.

---

## Next Actions

1. **Decision:** Approve markdown + YAML format change
2. **Spec:** Write reef-md-v2 formal specification
3. **Migration:** Build `reef migrate` tool for XML → markdown
4. **Documentation:** Create format guide, examples, philosophy doc
5. **Community:** Identify 10-20 pilot projects for v2

**Timeline:** Foundation work (3 months) → Tools (3 months) → Ecosystem (6 months) → Network effects (ongoing)

**Goal:** By end of 2026, ".reef directories" are recognized AI infrastructure.

---

*See full vision document: `VISION-NATIVE-AI-INFRASTRUCTURE.md`*
