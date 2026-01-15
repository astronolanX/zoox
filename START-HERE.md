# START HERE: Week 1 Analysis Complete

**Status**: Builder's perspective analysis DONE. Implementation ready to start.

**Read in this order**:

1. **This file** (2 min) - Overview + key decisions
2. **IMPLEMENTATION-ANALYSIS.md** (10 min) - What CAN be built, risks, MVP
3. **HIDDEN-DEPENDENCIES.md** (15 min) - Technical deep-dive on blockers
4. **WEEK-1-SPRINT.md** (Start coding) - Day-by-day tactical plan

---

## TL;DR

### The Problem You Posed

You proposed 5 changes:
1. Unified directory structure
2. Trenches system (free agents doing grunt work)
3. claude-flow integration
4. VoltAgent adoption
5. Evidence MCP + Mediator as SKILL

### The Reality Check

**Good news**: You don't need most of that.

**Better news**: You can ship value in 1 week without any of it.

**Best news**: Everything can be built incrementally AFTER the MVP works.

### What You Actually Need (This Week)

**MVP**: 2 things work end-to-end by Friday EOD

1. **Mediator Skill** - `reef mediator bactrack_clause` returns structured JSON
2. **Evidence Search** - `reef evidence-search --init` + `--search "query"` work

**That's it.**

### Why This MVP Matters

- **Mediator skill** proves domain logic can integrate with reef
- **Evidence search** validates if MCP is worth building
- **Together** they show how to handle complex case reasoning + data

### What NOT to Do This Week

- ❌ Consolidate directories (breaks 32 projects)
- ❌ Build full trenches system (executor framework too big)
- ❌ Build Evidence MCP (Phase 0 bash validates first)
- ❌ VoltAgent adoption (new ecosystem, no blocker)
- ❌ claude-flow integration (unclear what needs orchestrating)

---

## Key Decisions Made FOR You

| Decision | What | Why |
|----------|------|-----|
| **Architecture** | Mediator = SKILL wrapper, not SDK | 150 LOC vs 500 LOC, reuses existing code |
| **Evidence search** | Phase 0 bash validation, not MCP | Prove slowness first before investing 200 LOC |
| **Directory structure** | Use symlinks, not consolidate | Breaks 32 existing projects if you move |
| **Skill organization** | Global ~/.claude/ + project-local | Multi-project ready without breaking existing |
| **Case schema** | Hybrid polips (structured + narrative) | Works with reef + supports case graphs |

---

## Time Budget

| Task | Hours | Owner | Blocker |
|------|-------|-------|---------|
| Mediator skill wrapper | 4 | You | None |
| Mediator tests | 3 | You | None |
| Evidence search Phase 0 | 2 | You | None |
| CLI integration | 2 | You | None |
| Docs + polish | 1 | You | None |
| **TOTAL** | **12** | | **None** |

**Timeline**: Wed morning through Thu evening. Fri = buffer/polish.

---

## How to START (Right Now)

### Step 1: Read the documents (45 min)
- IMPLEMENTATION-ANALYSIS.md (what can ship)
- HIDDEN-DEPENDENCIES.md (what could break)
- WEEK-1-SPRINT.md (step-by-step)

### Step 2: Create the mediator schema (30 min)
Create `/Users/nolan/Desktop/reef/MEDIATOR-SCHEMA.md`

Lock the JSON output format before writing code.

### Step 3: Create git branch
```bash
cd /Users/nolan/Desktop/reef
git checkout -b feat/mediator-sdk-week1
```

### Step 4: Start with mediator_skill.py skeleton
See WEEK-1-SPRINT.md "Step 2: Create mediator_skill.py"

### Step 5: Write tests FIRST
See WEEK-1-SPRINT.md "Step 4: Create Mediator Skill Tests"

Then watch them fail. Then make them pass.

---

## Biggest Risks (If You Miss These)

### Risk 1: Path breakage during directory consolidation
**What happens**: All 32 .claude directories break when you move from Desktop → ~/projects/

**Prevention**: Use symlinks instead. Full consolidation after MVP.

**Cost to fix later**: 4 hours of path rewriting + testing

---

### Risk 2: Mediator scope explosion
**What happens**: You start building "mediator SDK" and it balloons to 500+ LOC

**Prevention**: Bounded as SKILL-ONLY for Week 1. Wrapper pattern (150 LOC).

**Cost to fix later**: 8 hours of refactoring to extract reusable library

---

### Risk 3: Evidence MCP investment wasted
**What happens**: You build MCP, but Phase 0 bash is fast enough.

**Prevention**: Phase 0 bash validation THIS WEEK. Metrics-driven decision.

**Cost to fix later**: 16 hours of MCP code that gets replaced

---

### Risk 4: Trenches system dependencies not met
**What happens**: You try to implement full swarm, hit executor agent missing.

**Prevention**: Skip trenches entirely Week 1. Proof-of-concept Week 2.

**Cost to fix later**: 40 hours building executor framework

---

## Success Criteria

**By Friday EOD, check these:**

- [ ] `reef mediator bactrack_clause` works (returns JSON)
- [ ] `reef evidence-search --init` works (builds index)
- [ ] `reef evidence-search --search "DUI"` works (searches in < 1s)
- [ ] mediator_skill tests pass (> 80% coverage)
- [ ] metrics.json exists with search perf data
- [ ] NO broken paths in .claude/
- [ ] Git log shows 3-4 clean commits (one per day)

**If all ✓**: MVP done. Ready for Week 2.

**If any ❌**: Debug that, don't move forward. Better now than Friday night.

---

## Week 2 (Preview)

Once Week 1 MVP is done:

### Day 1: Mediator Enhancement
- Integrate Claude API
- Add caching
- Improve schema

### Day 2: Evidence Decision
- Review metrics.json
- Build Phase 1 (or skip if Phase 0 fast)
- Add PDF support (if MCP needed)

### Day 3: Case Schema
- Expand polip `case-ref` nodes
- Import case-2022DCM6011 as polip
- Mediator extracts parties/timeline

### Days 4-5: Executor POC
- Design trench pattern
- Single-trench proof of concept
- NOT in production, just planning

---

## Files Created (For You to Read)

- **IMPLEMENTATION-ANALYSIS.md** (2,400 words) - MVP breakdown + risk matrix
- **HIDDEN-DEPENDENCIES.md** (3,000 words) - Technical deep-dive on blockers
- **WEEK-1-SPRINT.md** (2,500 words) - Tactical day-by-day plan
- **START-HERE.md** (this file) - Navigation guide

---

## Questions to Answer Before You Start

1. **Is Claude API available?** (For Week 2 mediator enhancement)
   - If yes: Plan mediator_with_claude() in scaffold
   - If no: Placeholder is enough for Week 1

2. **How much time realistically?** (12h estimate)
   - If < 12h available: Scope to CLI commands only (skip tests, add Week 2)
   - If > 12h available: Scope to full MVP + docs

3. **What's the definition of "done"?**
   - MVP done: Commands work, tests pass, no broken paths
   - Shipping done: CLI stable, docs complete, metrics justified
   - This week: MVP done. Shipping Week 2.

---

## One More Thing

**Don't try to do everything at once.**

The proposal (directory consolidation + trenches + VoltAgent + MCP + mediator) was trying to solve 5 problems simultaneously.

This analysis breaks it into:
- **Week 1**: Mediator + Evidence search work
- **Week 2**: Claude integration + Phase 1 decision
- **Week 3**: Case schema + executor POC
- **Week 4**: Decide on trenches/VoltAgent/claude-flow based on actual needs

You'll know what you need after Week 2. You won't know until then.

---

## Next Action

**Right now**: Open IMPLEMENTATION-ANALYSIS.md and read it. Takes 10 minutes.

**Then**: Create MEDIATOR-SCHEMA.md to lock the contract.

**Then**: Start WEEK-1-SPRINT.md Step 2.

**This is not optional.** You will waste 8 hours without the schema locked.

---

## Author Notes

This analysis is based on:
- 4,500 LOC existing reef code
- 38 existing skills in ~/.claude/
- 32 directories in custody-mediation with polips
- Mediator skill already written (just needs wrapping)
- 2-week context from your recent sessions

**Confidence level**: 85%
(15% risk is unknown unknowns: file permissions, symlink edge cases, Claude API changes)

**If something doesn't match your mental model**: Correct it now before starting code.

Better to argue about architecture on paper than refactor 300 LOC Thursday night.

---

*Analysis complete: 2026-01-15 14:30 UTC*
*Ready to build: start WEEK-1-SPRINT.md*
