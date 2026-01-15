---
title: Sparks Without Loops
source: .claude/sparks/spark-ux/2026-01-14-1808-loop-in-spark.md
captured: 2026-01-14
status: captured
feasibility: 3
importance: 2
innovation: 2
fii: 7
tags: [spark, architecture, loops, iteration, threads]
---

# Sparks Without Loops

**Origin:** Spark emergent synthesis (70% confidence)

> What if loops don't exist in sparks at all?

## The Idea

Sparks are intentionally non-looping. The current architecture runs once: topic → 5D combinatorics → tiers → synthesis → output. No iteration, no refinement, no feedback within a single spark run.

This isn't a limitation — it's a feature. Single-pass forces the swarm to commit without refinement. The value of sparks is in provocation, not polish. Loops would add compute but might not add insight.

The loop abstraction lives *between* sparks, not within them. Threads are temporal loops: 20 sparks in memory-evolution iterated on the same theme, each building on the last via SQLite memory. The thread *is* the loop.

## Concrete Expression

**Where loops could live (design options):**

1. **Within-spark iteration** — `--deep` mode runs tiers multiple times, synthesizes the syntheses. Higher compute, potentially more refined but less provocative.

2. **Between tiers** — Near insight feeds Mid prompt, Mid feeds Far. Already implicitly happening via synthesis; could make explicit.

3. **Thread-level loops** — `/spark` on same topic automatically references previous spark. Memory already does this; could be stronger.

4. **No loops (current)** — Accept that sparks are one-shot. Refinement happens in ideas/implementation, not in sparks themselves.

**Recommendation:** Keep sparks one-shot. The "nested stanzas" insight suggests recursion within a poem — but a haiku doesn't iterate. Sparks are haiku.

## Open Questions

- Does `--deep` mode need iteration, or just more models?
- Should thread synthesis auto-update after each spark (loop feedback)?
- Is there a distinction between "refining" an insight and "exploring adjacent" insights?
- Could sparks have optional `--iterate N` flag for users who want polish over provocation?

## Next Steps

- [ ] Document the intentional one-shot philosophy in spark skill
- [ ] Consider thread-level auto-synthesis as the loop mechanism
- [ ] Prototype `--iterate` flag for deep mode (optional refinement)
- [ ] Measure: do iterated sparks produce higher-quality emergent than one-shot?
