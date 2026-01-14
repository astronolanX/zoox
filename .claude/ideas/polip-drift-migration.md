---
title: Polip Drift & Migration
source: .claude/sparks/memory-evolution/2026-01-14-1730-polips-drift-folders.md
captured: 2026-01-14
status: captured
feasibility: 3
importance: 2
innovation: 2
fii: 7
tags: [memory, migration, autonomy, reef, folders]
---

# Polip Drift & Migration

**Origin:** Spark emergent synthesis (80% confidence)

> What if polyps don't exist in digital ecosystems?

## The Idea

The spark inverted the premise — asking whether polips exist at all in digital ecosystems. But the more actionable insight came from groq1 at 85%: "Polyps create sentient folders devouring entire databases." This dissolves the container/contained distinction: folders aren't where polips live, folders *are* calcified polips that stopped moving.

This reframes reef's architecture: instead of polips being stored in folders, folders emerge from polips that accumulate enough related content to warrant their own space. A folder is a polip that grew up.

## Concrete Expression

Several commands emerge from this insight:

1. **`reef drift`** — polips propose their own relocation based on content affinity
   ```bash
   reef drift              # Show migration proposals
   reef drift --apply      # Execute approved migrations
   reef drift --dry-run    # Preview without action
   ```

2. **`reef colony`** — identify clusters of polips that want to form new folders
   ```bash
   reef colony             # Show potential new folder structures
   reef colony --threshold 3  # Minimum polips to suggest new folder
   ```

3. **`reef sovereignty`** — set boundaries on autonomous migration
   ```bash
   reef sovereignty --local     # Polips can only migrate within project
   reef sovereignty --global    # Allow migration to ~/.claude/
   reef sovereignty --show      # Display current sovereignty rules
   ```

The sovereignty question is crucial: if a polip about "commit conventions" emerges in project A, should it be allowed to migrate to `~/.claude/` where it affects all projects? Who decides?

## Open Questions

- What signals indicate a polip wants to migrate? Content similarity? Orphan status? Cross-project usage?
- How does migration interact with adversarial decay? Do migrating polips need to justify the move?
- Should folders have "carrying capacity" limits that trigger splits or mergers?
- What happens when global and local polips conflict on the same topic?
- Is migration reversible? Can a global polip be "demoted" back to project scope?

## Next Steps

- [ ] Implement `reef drift --dry-run` that analyzes content affinity and proposes migrations
- [ ] Add `reef colony` to surface potential new folder structures from related polips
- [ ] Design sovereignty model for project-local vs global scope decisions
- [ ] Consider folder-as-calcified-polip metaphor for reef's conceptual model
