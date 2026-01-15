# Reef Agent SDK — Execution Handoff

**Last Session:** 2026-01-15
**Status:** Plan validated, ready for Phase 0 execution

---

## Quick Start

```bash
# Surface the thread for full context
reef surface reef-native-infrastructure

# Or read the implementation plan directly
cat docs/plans/2026-01-15-agent-sdk-implementation-plan.md
```

---

## What Happened (Session 2026-01-15)

### Team Research (7 Agents in Parallel)
- **Researcher**: AutoSchemaKG proves 92% schema alignment without design
- **ML Theorist**: Probability generates, structure selects, time crystallizes
- **Signal Analyst**: Framework for inflection point detection from human input
- **Systems Architect**: Stigmergic coordination vision (no central planner)
- **Devil's Advocate**: P0 safety guards are non-negotiable
- **Competitive Intel**: Reef's coral metaphor is unique differentiator
- **Technical Validator**: Identified critical safety gaps

### Deliverables Created
1. `docs/plans/2026-01-15-agent-sdk-implementation-plan.md` — Full 7-phase plan
2. `docs/plans/2026-01-15-plan-validation.md` — Cross-validation against research
3. Updated thread with 10 decisions and 7 next steps

---

## Decisions Made (10 total)

1. Graph relationships: content-embedded intent + computed similarity
2. Reef and config coexist with clear authority boundaries
3. Promotion pathway: organic → crystallized → human-promoted
4. Reef reads config, cannot modify it; human remains gatekeeper
5. Links stored via `[[wiki]]` and `@directives`
6. **P0 safety guards must ship before any auto-pruning**
7. **Implement reef MCP server exposing polip operations**
8. **Route external-ok tasks to Groq/Ollama/Gemini**
9. **Calcification engine with time × usage × consensus triggers**
10. **Audit trail + dry-run for all automatic operations**

---

## Execution Order

### Phase 0: Foundation (START HERE)
```bash
mkdir -p src/reef/{mcp,agents,skills,workers,safety}
touch src/reef/{mcp,agents,skills,workers,safety}/__init__.py
mkdir -p .claude/{agents,skills,workers}
uv run pytest -x  # Verify nothing broke
```

### Phase 1: Safety Infrastructure (P0 CRITICAL)
**MUST complete before ANY automation**

Create:
- `src/reef/safety/guards.py` — PruningSafeguards (deletion limits, protected scopes)
- `src/reef/safety/audit.py` — AuditLog (operation tracking)
- `src/reef/safety/undo.py` — UndoBuffer (7-day quarantine)

CLI: `reef sync --dry-run`, `reef audit`, `reef undo <id>`

### Phases 2-7: See Full Plan
`docs/plans/2026-01-15-agent-sdk-implementation-plan.md`

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/plans/2026-01-15-agent-sdk-implementation-plan.md` | Full implementation plan |
| `docs/plans/2026-01-15-plan-validation.md` | Validation against research |
| `docs/plans/2026-01-15-reef-native-infrastructure-design.md` | Vision document |
| `.claude/threads/reef-native-infrastructure.blob.xml` | Living thread |

---

## Constraints (DO NOT VIOLATE)

1. **Zero dependencies** — stdlib only in core
2. **Safety-first** — Phase 1 before automation
3. **Local-only** — Data never leaves machine unless routed
4. **Test gates** — Each phase requires passing tests

---

## Philosophy

> "The schema isn't designed—it's grown."

> "Biological metaphors aren't decoration—they're blueprint."

> "The gardener creates conditions where things grow, then selects what to keep."

---

## Resume Command

```bash
reef surface reef-native-infrastructure
# Then begin Phase 0
```
