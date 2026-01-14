# Next Session Quick Start

## Context

Resume Incubator Phase 5 (Surfacing). Phases 1-4 complete with 42 tests passing.

Read for full context:
```bash
cat .claude/contexts/incubator-build.blob.xml
```

## Incubator Status

| Phase | Status | Tests |
|-------|--------|-------|
| 1. Foundation | ✅ Complete | 19 |
| 2. Collection | ✅ Complete | 7 |
| 3. Scoring | ✅ Complete | 10 |
| 4. Patterns | ✅ Complete | 6 |
| 5. Surfacing | ⏳ Pending | - |

**Stats**: 74 insights → 46 scored, 28 archived, 4 clusters

## Phase 5 Tasks

1. **Promotion logic** - composite >= 7.0 AND confidence >= 0.7
2. **Session-start hook** - surface relevant insights at session begin
3. **Decay mechanism** - age unreinforced insights over time
4. **`/incubator relevant`** - context-aware insight queries
5. **Phase 5 test suite** - regression + new surfacing tests

## Key Files

```
~/.claude/incubator/
├── scored/           # 46 insights (composite >= 4.0)
├── promoted/         # (empty - Phase 5)
├── archive/          # 28 insights (< 4.0)
├── patterns/         # 4 cluster summaries
├── !INDEX.yaml       # Master registry
└── SCHEMA.md         # Format docs

~/.claude/scripts/
├── incubator-collect.py
├── incubator-score.py
└── incubator-patterns.py

~/.claude/tests/incubator/
├── run-phase1.sh ... run-phase4.sh
```

## Run Tests

```bash
~/.claude/tests/incubator/run-phase4.sh  # Runs all phases (regression)
```

## Resume Command

```
Continue building Phase 5 (Surfacing) for the Incubator system
```
