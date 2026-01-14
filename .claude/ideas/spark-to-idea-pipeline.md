---
title: Spark → Idea pipeline
source: conversation
captured: 2026-01-14
status: prototyping
feasibility: 3
importance: 2
innovation: 2
fii: 7
tags: [spark, workflow, curation]
---

# Spark → Idea pipeline

**Origin:** Gap analysis — reef tracks decisions/constraints but not possibilities

## The Idea

When a spark produces an emergent insight with ≥70% confidence, prompt to capture it as a scored idea with:
- **Feasibility** (0-3): How hard to build?
- **Importance** (0-3): How much does it matter?
- **Innovation** (0-3): How novel is this?
- **FII score** (F+I+I): Composite for prioritization

Ideas live in `.claude/ideas/` with YAML frontmatter for filtering/sorting.

## Why This Matters

Sparks generate signal. Without curation, signal becomes noise. This pipeline captures high-confidence sparks before they fade from context.

## Implementation

1. Add "Idea Capture" section to spark command
2. Trigger on emergent score ≥70%
3. Prompt user for F/I/I scores
4. Write to ideas folder with standard format
5. Update !IDEAS.md index

## Status

Currently prototyping — this file is the first captured idea using the system.
