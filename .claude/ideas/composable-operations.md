---
title: Composable Operations Over Syntax
source: .claude/sparks/memory-evolution/2026-01-14-1750-reef-syntax.md
captured: 2026-01-14
status: captured
feasibility: 3
importance: 2
innovation: 2
fii: 7
tags: [architecture, operations, composition, reef, design]
---

# Composable Operations Over Syntax

**Origin:** Spark emergent synthesis (90% confidence)

> What if reefs are simply irrelevant to syntax altogether?

## The Idea

Syntax implies grammar — rules that govern structure. But reef's memory system isn't a language to be parsed; it's an ecosystem to be navigated. The swarm's rejection of "reef syntax" as a category error suggests a fundamental design principle: **don't design a DSL, design composable operations**.

Reefs have emergence, feedback loops, and self-organization — not grammar. The "syntax" should be the composition of operations, not a formal language.

## Concrete Expression

**Core operations that compose:**

| Operation | Action | Composes With |
|-----------|--------|---------------|
| `spawn` | Create polip | Any target (polip, folder, reef) |
| `decay` | Challenge/prune | Any scope (single, folder, all) |
| `drift` | Propose migration | Any direction (in, out, lateral) |
| `spiral` | Revisit with context | Any depth (shallow, deep) |
| `surface` | Bring to attention | Any filter (type, age, relevance) |

**Composition examples:**

```bash
# Single operation
reef spawn thread "auth work"

# Composed: surface then decay
reef surface --stale | reef decay --challenge

# Composed: drift then spiral
reef drift --candidates | reef spiral --with-context

# Fractal: same operation at different scales
reef decay polip:auth-notes      # Single polip
reef decay folder:threads        # Folder of polips
reef decay --all                 # Entire reef
```

**No special grammar needed.** Unix pipes and standard CLI patterns provide all the composition reef needs. Each operation:
- Takes a target (polip, folder, reef, or stdin)
- Produces output (status, list, or transformed content)
- Can chain with other operations

## Open Questions

- Should operations be pure (no side effects until explicit commit)?
- How do operations interact with adversarial decay? Is `decay` itself an operation or a meta-operation?
- Should `spiral` be its own operation, or a flag on existing operations (`--with-context`)?
- How does composition interact with sovereignty? Can composed operations cross project boundaries?

## Next Steps

- [ ] Audit existing reef commands for composability (can they pipe?)
- [ ] Design stdin/stdout contracts for each core operation
- [ ] Implement `reef surface` as the primary composition entry point
- [ ] Test: can all desired behaviors be expressed as operation compositions?
