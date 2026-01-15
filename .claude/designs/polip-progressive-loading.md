---
title: Polip Progressive Loading (L1/L2/L3)
status: design
created: 2026-01-14
---

# Polip Progressive Loading

Applies the progressive disclosure pattern from custody-mediation skills to reef polip surfacing.

## Current State

`glob_inject.py` surfaces **full polip content** at session start:
- Top 5 polips by priority (constraints=100, threads=80, context=50, decisions=20)
- Full XML content injected into `[GLOB]` block
- Token cost: ~200-500 tokens per polip = 1000-2500 tokens for 5 polips

## Proposed Architecture

### L1 Discovery (SessionStart)

Emit metadata index only:

```xml
<glob project="reef">
  <polip-index updated="2026-01-14" count="8">
    <polip id="constraint-001" type="constraint" scope="always" priority="100">
      <summary>reef project constraints</summary>
      <updated>2026-01-13</updated>
      <tokens>150</tokens>
    </polip>
    <polip id="context-session" type="context" scope="session" priority="50">
      <summary>Spark thread memory-evolution converged...</summary>
      <updated>2026-01-14</updated>
      <tokens>380</tokens>
    </polip>
    <!-- more polips... -->
  </polip-index>
</glob>
```

**Token cost**: ~20-30 tokens per polip metadata = 160-240 tokens for 8 polips
**Reduction**: 80-90% fewer tokens at session start

### L2 Activation (On-Demand)

Full polip content loaded when:
1. User explicitly requests: `/surface constraint-001`
2. Claude determines relevance based on task
3. Search query matches polip content

Mechanism:
- New `/surface` command to load specific polips
- Claude can request polip content via tool use (future)
- Search results include polip IDs for targeted loading

### L3 Resources (Explicit)

Extended content loaded on explicit request:
- `<files>` referenced in polip
- `<related>` wiki-linked polips
- Full decision rationale / thread history

## Implementation

### 1. Update glob_inject.py

Add `--mode` flag:
- `--mode=full` (default for now, backwards compat)
- `--mode=index` (L1 only)

When `--mode=index`:
- Emit `<polip-index>` with metadata only
- Calculate token estimate per polip
- Include enough summary for Claude to judge relevance

### 2. Create surface command

New CLI command or skill:
```bash
reef surface <polip-id>   # CLI
/surface <polip-id>       # Claude skill
```

Emits full polip content to stdout/context.

### 3. Update hooks

Modify UserPromptSubmit hook:
- Currently calls `glob_inject.py` with full mode
- Change to index mode
- Add guidance for Claude to request L2 when needed

## Selection Pressure

This implements the "selection pressure" concept from spark #6:
- Polips must **prove relevance** to earn context tokens
- Default is visibility without weight
- Only surfaced polips consume full token budget

## Migration Path

1. Add `--mode` flag to glob_inject.py (backwards compat)
2. Test L1 mode with reef project
3. Update UserPromptSubmit hook to use L1 mode
4. Add `/surface` command
5. Roll out to other projects

## Token Budget Analysis

| Mode | Polips | Tokens | Use Case |
|------|--------|--------|----------|
| L1 | 8 | ~200 | Always at start |
| L2 | 2-3 | ~400-600 | Task-relevant |
| L3 | 1 | ~200+ | Deep dive |
| **Total** | - | ~800-1000 | Per session |

vs current: ~2000-2500 tokens for 5 full polips

**Savings**: 50-60% token reduction while maintaining full access
