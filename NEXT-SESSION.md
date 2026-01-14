# Next Session Quick Start

## Context

Incubator system is **complete** - all 5 phases implemented and tested.

## Incubator Status

| Phase | Status | Tests |
|-------|--------|-------|
| 1. Foundation | ✅ Complete | 19 |
| 2. Collection | ✅ Complete | 16 |
| 3. Scoring | ✅ Complete | 18 |
| 4. Patterns | ✅ Complete | 12 |
| 5. Surfacing | ✅ Complete | 19 |

**Total: 84 tests passing**

**Stats**: 74 insights → 8 promoted, 38 scored, 28 archived, 3 clusters

## How It Works

1. **Ingest** - `/incubator ingest` or auto-capture from `/idea`, `/spark`
2. **Score** - `python3 ~/.claude/scripts/incubator-score.py`
3. **Patterns** - `python3 ~/.claude/scripts/incubator-patterns.py`
4. **Promote** - `python3 ~/.claude/scripts/incubator-promote.py`
5. **Surface** - Automatic via `incubator_inject.py` hook at session start

## Key Files

```
~/.claude/incubator/
├── promoted/         # 8 high-signal insights (auto-surfaced)
├── scored/           # 38 insights (4.0-6.9 composite)
├── archive/          # 28 insights (< 4.0)
├── patterns/         # 3 cluster summaries
├── !INDEX.yaml       # Master registry
└── SCHEMA.md         # Format docs

~/.claude/scripts/
├── incubator-collect.py
├── incubator-score.py
├── incubator-patterns.py
├── incubator-promote.py
└── incubator-surface.py

~/.claude/hooks/
└── incubator_inject.py  # Session-start surfacing
```

## Commands

```bash
# Run all tests
~/.claude/tests/incubator/run-phase5.sh

# Query relevant insights
python3 ~/.claude/scripts/incubator-surface.py --query "authentication"

# Apply decay and check for demotions
python3 ~/.claude/scripts/incubator-promote.py --decay --demote

# Force promote an insight
python3 ~/.claude/scripts/incubator-promote.py  # (use /incubator promote <id>)
```

## What's Next

The Incubator is now operational. Consider:
- Monitor promoted insights for decay over time
- Add new sources (Apple Notes integration, conversation extraction)
- Build reinforcement mechanism (mark insights as "used" when they influence work)
- Create `/incubator stats` for analytics dashboard
