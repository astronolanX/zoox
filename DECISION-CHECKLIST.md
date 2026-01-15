# Decision Checklist: Before You Code

**Don't start Week 1 sprint until you've answered these.**

---

## CONSTRAINT VERIFICATION (5 min)

- [ ] **Zero dependencies constraint** is HARD REQUIREMENT, right?
  - If yes: Bash script approach for evidence search works
  - If no: Can use pandas/sqlite for better indexing

- [ ] **Local-only constraint** is HARD REQUIREMENT, right?
  - If yes: No cloud storage, no external APIs except Claude
  - If no: Can store evidence index in cloud

- [ ] **Reef as pure library** (not application)?
  - If yes: Mediator is a skill using reef, not reef using mediator
  - If no: Merge them more tightly

---

## SCOPE CLARIFICATION (5 min)

**These are the ONLY things Week 1 will ship:**

1. `reef mediator bactrack_clause` returns JSON
2. `reef evidence-search --init` works
3. `reef evidence-search --search "query"` works
4. mediator + evidence tests pass (>80% coverage)
5. Documentation written

**NOT shipping Week 1:**
- ❌ Claude integration (Week 2)
- ❌ MCP server (Week 2+)
- ❌ Case schema (Week 2)
- ❌ Trenches system (Week 2+)
- ❌ Directory consolidation (Week 3+)

**Confirm**: Are you okay with placeholder mediator responses this week?
- [ ] Yes, Week 1 is about structure, not reasoning
- [ ] No, I need Claude logic working now (requires API key + 4 extra hours)

---

## API AVAILABILITY (2 min)

**Do you have Claude API credentials?**
- [ ] Yes, environment variables set
  - → Add mediator_with_claude() method (scaffold Week 1, implement Week 2)
- [ ] No, using Claude Code directly
  - → Placeholder is fine, integrate Week 2 when credentials available
- [ ] Unsure
  - → `echo $ANTHROPIC_API_KEY` before starting

---

## MEDIATOR DOMAIN BOUNDARIES (5 min)

**Mediator is for custody law scenarios, specifically:**
- [ ] Texas Family Code 153.x framework (YES, in skill file)
- [ ] El Paso 383rd District court patterns (YES, in skill file)
- [ ] Figueroa v. Figueroa case (YES, in skill file)

**Mediator is NOT for:**
- [ ] General legal research (out of scope)
- [ ] Mediation process facilitation (just analysis)
- [ ] Actual court representation (analysis only, not legal advice)

**Confirm**: Mediator is "predict what court will do" not "what father should do"?
- [ ] Yes, pure prediction/analysis
- [ ] No, I need strategic recommendations too (requires different output schema)

---

## EVIDENCE SEARCH SCOPE (5 min)

**Evidence search Phase 0 will:**
- [ ] Find files in .data/.processed/.vault
- [ ] Grep-based search (no indexing yet)
- [ ] Measure performance (metrics.json)
- [ ] Decide: build MCP (if slow) or skip (if fast)

**Evidence search Phase 0 will NOT:**
- [ ] Parse PDF files (Phase 1 if needed)
- [ ] Extract structured data (Phase 1 if needed)
- [ ] Index full-text (Phase 1 if needed)
- [ ] Semantic search (Phase 1 if needed)

**Confirm**: Phase 0 is validation, not feature-complete?
- [ ] Yes, proof of concept first
- [ ] No, I need full search now (scope creep - will break deadline)

---

## PATH RESOLUTION STRATEGY (5 min)

**How will you prevent directory breakage?**

Option A (RECOMMENDED): Symlinks
```bash
mkdir -p ~/projects
ln -s ~/Desktop/custody-mediation ~/projects/custody-mediation
# All paths work both ways
# Physical move deferred to Week 3+
```

Option B: Single path consolidation
```bash
mv ~/Desktop/custody-mediation ~/projects/
# Update all 32 .claude/ references
# HIGH RISK if you miss any
```

Option C: No consolidation
```bash
# Leave everything at ~/Desktop
# Skip the unified directory structure goal
```

**Choose one:**
- [ ] Option A - Symlinks (safe, deferred consolidation)
- [ ] Option B - Consolidate now (risky, requires 4h of path fixing)
- [ ] Option C - Skip consolidation (accept scattered structure)

---

## TESTING STRATEGY (5 min)

**How comprehensive do tests need to be?**

Option A (MINIMAL): 5 tests
- [ ] Mediator loads skill file
- [ ] Mediator returns valid schema
- [ ] Evidence search builds index
- [ ] Evidence search finds matches
- [ ] CLI commands don't crash

**Estimated time**: 30 min

Option B (RECOMMENDED): 16 tests
- [ ] All of A
- [ ] Schema field validation
- [ ] Scenario-specific logic
- [ ] Edge cases (missing files, empty results)
- [ ] Integration tests (CLI → functions)

**Estimated time**: 2 hours

Option C (COMPREHENSIVE): 30+ tests
- [ ] All of B
- [ ] Performance benchmarks
- [ ] Error handling
- [ ] Multi-user scenarios
- [ ] Mocking Claude API

**Estimated time**: 4+ hours

**Choose one:**
- [ ] Option A - Minimal (fast)
- [ ] Option B - Recommended (balances speed + coverage)
- [ ] Option C - Comprehensive (slow but robust)

---

## TIME COMMITMENT (2 min)

**Realistic hours available this week?**

You said: "Build this THIS WEEK"

Break down:
- Wed: 4 hours (morning mediator schema + skeleton, afternoon evidence script)
- Thu: 4 hours (morning tests + CLI, afternoon docs)
- Fri: 2 hours (buffer, polish, commit)
- **Total**: 10 hours

**Your estimate**: _____ hours

**If < 10h available**:
- Skip comprehensive tests (Option A)
- Defer docs to Week 2
- Focus on: mediator_skill.py + evidence search script only

**If 10-15h available**:
- Do Option B (recommended tests)
- Include user guides
- Full commit with clean git history

**If > 15h available**:
- Do Option C (comprehensive tests)
- Add performance benchmarks
- Implement Claude integration (Week 2 work, but ahead of schedule)

**Commit**: I have _____ hours. I'm aiming for Option _____.

---

## RISK ACCEPTANCE (5 min)

**Biggest risks of Week 1 MVP approach:**

1. **Placeholder mediator responses** feel incomplete
   - Risk: Stakeholder confusion (this is just skeleton)
   - Mitigation: Clear documentation that logic arrives Week 2
   - Accept risk? [ ] Yes [ ] No

2. **Phase 0 bash might be too slow**
   - Risk: You built wrong approach, waste time on alternatives
   - Mitigation: Metrics.json forces decision by Thu, time to pivot Fri
   - Accept risk? [ ] Yes [ ] No

3. **Directory symlinks might have edge cases**
   - Risk: Some paths still break in specific scenarios
   - Mitigation: Test suite checks all paths, symlink resolution
   - Accept risk? [ ] Yes [ ] No

4. **Evidence search doesn't integrate with mediator yet**
   - Risk: Two separate systems, no connection shown
   - Mitigation: Week 2 ties them together, MVP just shows they work
   - Accept risk? [ ] Yes [ ] No

**All four:**
- [ ] Accept all (ship MVP as-is, clean up Week 2)
- [ ] Reject some (push deadlines, scope down)

---

## GO/NO-GO DECISION (2 min)

**Based on answers above, are you ready to start WEEK-1-SPRINT.md?**

Before you answer, check:
- [ ] Schema locked (mediator output JSON is finalized)
- [ ] Scope bounded (NOT building trenches/MCP/VoltAgent Week 1)
- [ ] Time available (have you really got 10+ hours?)
- [ ] API ready (Claude credentials available for Week 2)
- [ ] Risk accepted (you understand what's placeholder vs final)

**GO or NO-GO?**

If GO:
- [ ] Create branch: `git checkout -b feat/mediator-sdk-week1`
- [ ] Start WEEK-1-SPRINT.md Step 1 (mediator schema)
- [ ] Commit every 2-3 hours

If NO-GO:
- [ ] Which constraint isn't met? (list above)
- [ ] What do you need to resolve first?
- [ ] When can you revisit this checklist?

---

*Last updated: 2026-01-15 14:30 UTC*
*Decision required before starting WEEK-1-SPRINT.md*
