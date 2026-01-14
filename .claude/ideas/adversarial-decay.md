---
title: Adversarial Decay
source: .claude/sparks/memory-evolution/2026-01-14-1725-forgetting-core-feature.md
captured: 2026-01-14
status: captured
feasibility: 3
importance: 2
innovation: 2
fii: 7
tags: [memory, decay, selection, reef]
---

# Adversarial Decay

**Origin:** Spark emergent synthesis (80% confidence)

> What if forgetting is actually reef's crippling vulnerability?

## The Idea

Reef already forgets — chaotically, through neglect and entropy. Polips accumulate without pressure, then disappear without ceremony. This unstructured decay is a vulnerability, not a feature. The insight: memories should face *adversarial challenge* to earn survival.

Instead of passive time-based decay, reef should implement selection pressure. Memories that can defend their relevance survive and strengthen. Memories that can't justify their existence decompose. This transforms forgetting from a bug into a curation mechanism.

## Concrete Expression

A `reef decay` command (or `reef challenge`) that:

1. **Surfaces candidate polips** — old, low-access-count, or orphaned memories
2. **Challenges each one** — "Why does this still matter?" prompts the AI or user
3. **Verdicts:**
   - **Defend** → polip survives, access count resets, maybe promotes to bedrock
   - **Merge** → combines with related polip, consolidating fragmented memories
   - **Decompose** → archives to deep reef or deletes entirely

```bash
reef decay                    # Interactive challenge mode
reef decay --dry-run          # Preview candidates without action
reef decay --auto             # AI evaluates relevance, human approves
reef decay --scope project    # Challenge only project-scope polips
```

The `--auto` flag is key: Claude evaluates each polip against current project context and proposes verdicts. Human reviews and confirms. This creates adversarial pressure without requiring human attention for every memory.

## Open Questions

- What criteria determine "challengeable" status? Age? Access count? Orphan status?
- Should defended polips gain immunity for a period, or face repeated challenges?
- How aggressive should auto-decay be? Conservative (suggest merge) vs aggressive (suggest decompose)?
- Should there be a "deep reef" archive for decomposed memories, or true deletion?
- How does this interact with the existing `reef sync --fix` repair mechanism?

## Next Steps

- [ ] Prototype `reef decay --dry-run` that surfaces candidate polips by age and access count
- [ ] Add `--auto` flag that uses Claude to evaluate relevance and propose verdicts
- [ ] Implement merge operation for consolidating related polips
- [ ] Consider "deep reef" archive vs true deletion semantics
