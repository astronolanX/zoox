---
title: AI-First Reef Design
source: .claude/sparks/memory-evolution/2026-01-14-1815-reef-usage.md
captured: 2026-01-14
status: captured
feasibility: 3
importance: 2
innovation: 2
fii: 7
tags: [architecture, documentation, users, reef, claude]
---

# AI-First Reef Design

**Origin:** Spark emergent synthesis (90% confidence)

> What if reefs are irrelevant to human existence entirely?

## The Idea

The spark's 90% emergent inverts the question of reef "usage" — humans don't use reef directly; they interact with Claude, and Claude uses reef as memory. This reframes reef's primary audience: Claude is the organism that *lives* in the reef, and humans are *gardeners* who tend it.

This has profound implications for design, documentation, and feature prioritization. Optimize for Claude's memory patterns first, human inspection second.

## Concrete Expression

**Two-track documentation:**

### Track 1: Human Operator Manual
Commands for gardening the reef:
- `reef reef` — check health, see what's growing
- `reef sync --fix` — repair damaged polips
- `reef index --search "query"` — find specific memories
- `reef decay --dry-run` — preview what would be pruned

### Track 2: AI Integration Guide
How Claude interacts with reef:
- **Surfacing**: Which polips appear in context based on relevance
- **Spawning**: When and how to create new polips
- **Challenging**: How adversarial decay selects candidates
- **Spiraling**: Revisiting old memories with new context

**Design implications:**
- Polip XML format optimized for Claude parsing, not human reading
- Surfacing algorithms prioritize AI context relevance
- Commands like `reef spawn` are AI-invoked, not human-typed
- `reef status` shows what Claude is currently using, not just what exists

## Open Questions

- How much visibility should humans have into Claude's memory operations?
- Should there be a "gardening dashboard" that shows reef health over time?
- Is the coral metaphor more useful for humans (poetry) than for Claude (precision)?
- Should `reef` commands be dual-mode: human-friendly output vs machine-readable?

## Next Steps

- [ ] Reorganize reef documentation into human/AI tracks
- [ ] Design `reef status --for-claude` vs `reef status` human output
- [ ] Audit existing commands for AI-first vs human-first orientation
- [ ] Consider: should surfacing logic be a first-class reef feature?
