---
title: Metaphor Death & Rebirth
source: .claude/sparks/memory-evolution/2026-01-14-1735-reef-nomenclature-digital.md
captured: 2026-01-14
status: captured
feasibility: 3
importance: 2
innovation: 2
fii: 7
tags: [metaphor, naming, identity, reef, terminology]
---

# Metaphor Death & Rebirth

**Origin:** Spark emergent synthesis (95% confidence)

> What if reefs aren't translated, but replaced?

## The Idea

The coral metaphor was generative for imagining reef — it suggested organic growth, symbiosis, ecosystem dynamics. But now that the system exists as code, the metaphor may be *obscuring* rather than illuminating. Digital systems might need native metaphors that emerge from their actual behavior, not borrowed biological concepts.

This isn't about abandoning poetry — it's about recognizing when a metaphor has done its job. The scaffolding can come down once the building stands.

## Concrete Expression

Three possible paths:

### Path A: Full Replacement
Drop coral terminology entirely. Use digital-native terms:
- polip → node, unit, block
- reef → graph, store, tree
- spawn → create, instantiate
- decay → gc, prune, evict
- current → thread, stream

**Pro:** Technical clarity. Easier onboarding for developers.
**Con:** Loses the evocative, memorable quality.

### Path B: Dual-Layer Naming
Keep coral terms as user-facing interface, use technical terms internally:
- User sees: `reef spawn thread "working on auth"`
- System logs: `node.create(type=thread, label="working on auth")`
- Docs use both: "A polip (internally: node) is a unit of memory..."

**Pro:** Best of both worlds. Poetry for users, precision for debugging.
**Con:** Cognitive overhead of maintaining two vocabularies.

### Path C: Metaphor Evolution
Let the metaphor evolve rather than replace it. What digital concepts *do* map well to coral?
- Coral calcification → file crystallization
- Reef bleaching → context decay
- Symbiosis → plugin coordination
- Spawn/drift/colony → already digital-native via reef commands

**Pro:** Preserves identity while adding precision.
**Con:** Some mappings will always be strained.

## Open Questions

- Is the coral metaphor part of reef's *brand*, or just implementation detail?
- Do users find the metaphor helpful or confusing?
- Would dual-layer naming create more confusion than clarity?
- What would "reef v2" look like with digital-native terminology?

## Next Steps

- [ ] Survey existing reef users on metaphor utility (if any exist beyond core team)
- [ ] Document where coral metaphor helps vs hinders understanding
- [ ] Prototype Path B dual-layer naming in docs
- [ ] Consider: is this a documentation problem, not a naming problem?
