# KAREN's Final Verdict: The "Agent Run Notes" Pattern

**Author**: KAREN (Skeptical Validator)
**Date**: 2026-01-15
**Status**: DELIBERATION COMPLETE

---

## The Question You Asked

> Build a unified harness with learning loops. Pattern: "Agents write notes to a file during each run (what worked, what didn't, missing context). Then sweep through multiple run notes to improve the harness automatically."

**Follow-up questions I answered:**
1. Is this genuinely useful or just overhead?
2. What's the minimum viable version?
3. Where does this break down?
4. What's the simplest integration with existing systems?

---

## VERDICT: YES, BUT NOT HOW YOU DESCRIBED IT

**Useful?** ✓ Yes (30% learning value, 70% narrative continuity)
**Overhead?** ✗ Excessive for what you gain (50-60% of cost has no return)
**Viable?** ✓ Minimum version exists (Tier 1 + Tier 2)
**Breaks?** ✓ 8 specific failure modes documented
**Integration?** ✓ Via polips (not standalone system)

---

## What's Actually Happening in Your 21 Runs

You think: "Agents write notes → Harness learns"

Reality:
```
Run-017: Spark explores memory evolution
         ↓
       You read spark outputs
         ↓
       You write START-HERE.md manually
         ↓
       Architect writes ARCHITECTURE-ANALYSIS.md
         ↓
       You decide: "Phase 0, then Phase 1-5"
         ↓
       Harness improves based on your decision
```

**The run notes** (what-worked/what-didnt) support this. They don't drive it.

**The learning loop is human-driven.** Run notes are just better documentation.

---

## Where You're Right (Things That DO Work)

### 1. Narrative Continuity ✓
Between run-020 and run-021, Karen referenced findings from previous runs. Run notes made context transfer faster.

**Cost**: 5-10 min agent writing per run
**Benefit**: You understand agent reasoning faster
**Verdict**: Worth it

### 2. Idea Capture ✓
Run notes seed the idea pipeline:
```
run-017 what-worked item → captured as idea → incubator
```

**Cost**: Automatically harvested from notes
**Benefit**: Ideas flow to polips
**Verdict**: Worth it

### 3. Quick Retrospective ✓
You can write START-HERE.md faster because run notes give timeline:
```
run-001 to run-005: Setup skeleton
run-006: Team orchestration
run-017: Spark exploration
run-021: Karen validation
```

**Cost**: None (already writing notes)
**Benefit**: Better documentation
**Verdict**: Worth it

---

## Where You're Wrong (Things That DON'T Work)

### 1. Automatic Pattern Extraction ✗
No script exists that reads 21 XML files and says: "Spark skill has 90% success rate, try scaling it."

**Reality**: You have to synthesize this manually.

### 2. Harness Improvement Automation ✗
No mechanism that converts "what didn't work" into code changes.

**Reality**: Human reads notes, designs fix, implements it.

### 3. Learning Loop Closure ✗
Karen found "retention policy is liability" in run-021.
The fix (session-only memory) won't land until run-023.
No automated feedback between finding and fix.

**Reality**: 1-2 week gap between insight and implementation.

### 4. Scale to 64-Agent Swarm ✗
If each agent writes 10-bullet notes, you get 640 bullets per run.
Signal-to-noise collapses to zero.

**Reality**: Would need distributed tracing (3500+ LOC), not run notes.

---

## The Minimum Viable Implementation

You can have this running by 2026-01-17:

### Step 1: Automatic Metrics (30 LOC)
In your session hook, capture:
```python
metrics = {
    "run_id": run_id,
    "timestamp": now,
    "exit_code": success/failure,
    "duration_seconds": elapsed,
    "agents": ["Architect", "Karen"],
}
save_json(".claude/runs/run-{id}.metrics.json", metrics)
```

**Cost**: 30 LOC, one afternoon
**Benefit**: Can track trends over 21 → 50 runs

### Step 2: Agent-Written Notes (Already Done)
Keep doing what you're doing. Agent writes XML with:
- what-worked
- what-didnt
- files-created
- ideas-captured

**Cost**: 5-10 min per agent session (acceptable)
**Benefit**: Narrative continuity + idea capture

### Step 3: Per-Agent Telemetry (50 LOC)
When /team spawns Architect and Karen:
```json
{
  "Architect": {
    "tokens_used": 15000,
    "latency_seconds": 120,
    "ideas_generated": 3,
    "cost_usd": 0.45
  },
  "Karen": {
    "tokens_used": 8000,
    "latency_seconds": 45,
    "ideas_generated": 1,
    "cost_usd": 0.12
  }
}
```

**Cost**: 50 LOC, one afternoon
**Benefit**: Can answer "which agent is most efficient?"

### Total: 130 LOC, ~8 hours of work

---

## What NOT to Build (Yet)

### ✗ Automatic Pattern Extraction
Cost: ~500 LOC
Benefit: Low (no patterns visible until 50+ runs)
Status: WAIT until run 30. If patterns don't exist, skip forever.

### ✗ Decision Linking System
Cost: ~300 LOC
Benefit: Medium (clarifies cause/effect)
Status: WAIT until you have 30+ runs. Check if linking needed.

### ✗ Full /introspect MCP
Cost: ~500 LOC
Benefit: High (detailed traces) but requires distributed telemetry design
Status: WAIT until you're deploying to production or scaling to swarms.

### ✗ Failure Classification Taxonomy
Cost: ~200 LOC
Benefit: Medium (helps with root cause)
Status: WAIT. Start with manual classification on 3-5 real failures.

---

## The Integration Strategy (Right Way)

### Current Stack
- `.claude/runs/*.xml` (narrative notes)
- `.claude/ideas/` (idea snapshots)
- `~/.claude/incubator/` (global insights)
- (metrics.json planned)
- (/introspect planned)

### DO THIS:
Make all of them point to reef polips:

```
run-021.xml
  ↓ auto-extract ideas
~/.claude/incubator/ins_*.yaml
  ↓ crystallized decision
.claude/decisions/retention-policy.polip
  ↓ searchable via reef
/reef index --search "retention"
```

**One system**: Reef polips
**Multiple views**: XML, YAML, search, query
**Cost**: ~100-150 LOC to wire up

---

## The Honest Timeline to "Learning Loop"

### Week 1 (Now)
- Implement Tier 1 metrics (30 LOC)
- Keep writing run notes (no overhead)
- Baseline established

### Week 2 (2026-01-22)
- Implement Tier 2 per-agent telemetry (50 LOC)
- Run 5 more sessions (runs 22-26)
- Review: Do patterns exist?

### Week 3 (2026-01-29)
- **Decision point**: If patterns visible → Tier 3, if not → stop
- If Tier 3: Implement 300 LOC decision linking system
- If stop: Accept that learning is human-driven (it's okay!)

### Week 4+ (2026-02-05)
- If Tier 3 built: Validate that it actually improves harness
- If no improvement: Revert it. Run notes were sufficient.

---

## The Uncomfortable Truth

Your harness **will** improve over the next month.

**But not because of agent run notes.**

Because:
1. You (human) are deliberately designing improvements
2. You have Karen validating designs
3. You have Architect synthesizing options
4. You implement winners

Run notes *support* this human process. They don't *drive* it.

So the question isn't: "How do we automate harness learning?"

The question is: "How do we make the human learning process cheaper?"

**Answer**: Unified polip system + basic metrics. Not "agent run notes" system.

---

## Red Flags: When to Stop This Project

Stop building the run notes learning loop if:

1. **After 10 runs (this month), you haven't implemented automatic improvements**
   → It's manual synthesis, not automated learning
   → Run notes are documentation, not a system

2. **You spend >20 hours on "integration" without seeing value**
   → Scope creep. Stop. Revert to manual process.

3. **The notes are longer than 100 lines per run**
   → Agents are over-explaining. Running off script.

4. **You read the notes but rarely act on them**
   → They're noise. Cut back to metrics only.

5. **Pattern extraction script produces >50% false positives**
   → LLM confabulation too high. Switch to manual review.

---

## What You Should Commit To RIGHT NOW

### Yes, Do This
- [ ] Write run notes (human narrative) - already doing
- [ ] Capture ideas from notes to polips - already doing
- [ ] Implement basic metrics.json - 30 LOC, this week
- [ ] Add per-agent telemetry - 50 LOC, this week
- [ ] Document run note vocabulary - 1 hour, prevents confusion

### No, Don't Do This Yet
- [ ] Pattern extraction script (wait for 30+ runs)
- [ ] Decision linking system (wait for proof of value)
- [ ] Failure classification taxonomy (classify 5 real failures first)
- [ ] Full distributed tracing (only for 64-agent swarms)
- [ ] LLM-powered insight extraction (high hallucination risk)

### Maybe, Decide After 10 Runs
- [ ] Automatic improvement suggestions (only if patterns exist)
- [ ] /introspect MCP integration (only if metrics insufficient)

---

## The Real Answer to Your Original Question

> Pattern: "Agents write notes during each run, then sweep to improve harness automatically."

**Decomposed:**

1. **"Agents write notes"** ✓ YES (but manually, 5-10 min/run)
2. **"Sweep through notes"** ✗ NO (but could build, 300-500 LOC)
3. **"Extract patterns"** ✗ MAYBE (works at 50+ runs, unclear if worth it)
4. **"Improve harness automatically"** ✗ NO (improvements require human decision)
5. **"Multiple run notes"** ✓ YES (21 runs accumulated, good density)

**Honest assessment**: The pattern describes a dream (fully automated learning). Reality is hybrid (human synthesis + agent observations + optional automation).

---

## My Recommendation

**This month (2026-01-15 to 2026-02-15):**

1. Keep writing run notes (valuable narrative)
2. Add Tier 1 metrics (30 LOC, free trend insight)
3. Add Tier 2 per-agent telemetry (50 LOC, agent comparison)
4. **Stop there.**

**Do manual synthesis**: You + Architect read all 25 runs, write one comprehensive LEARNINGS.md document with:
- Top 5 things that worked
- Top 5 things that didn't
- Recommended harness changes for next month

**Effort**: 4 hours for you, worth it.

**Then**: Implement the recommended changes. Validate in 5 test runs.

**If improvements land**: Consider building Tier 3 (automated extraction)
**If no improvements**: Accept that this is human-driven, save 1000+ LOC

---

## Files Created for You

1. **AGENT-RUN-NOTES-PATTERN-ANALYSIS.md** (this repo)
   - Full critical analysis
   - Where pattern works/fails
   - Minimum viable version

2. **HARNESS-LEARNING-SYSTEMS-MAP.md** (this repo)
   - Inventory of current systems
   - Integration complexity matrix
   - What to build first (priorities)

3. **EDGE-CASES-WHERE-RUN-NOTES-FAIL.md** (this repo)
   - 8 specific failure modes
   - Swarm collapse, mediation sessions, discovery liability, etc.
   - Costs to fix each

---

## Next Steps (Action Items)

### This Week
- [ ] Read AGENT-RUN-NOTES-PATTERN-ANALYSIS.md (30 min)
- [ ] Read HARNESS-LEARNING-SYSTEMS-MAP.md (30 min)
- [ ] Read EDGE-CASES-WHERE-RUN-NOTES-FAIL.md (30 min)
- [ ] Implement Tier 1 metrics (30 LOC, 1 afternoon)
- [ ] Implement Tier 2 per-agent telemetry (50 LOC, 1 afternoon)

### In 2 Weeks
- [ ] Review: Do patterns exist in metrics from runs 22-26?
- [ ] If no → Declare victory, stop building
- [ ] If yes → Plan Tier 3 (decision linking)

### In 4 Weeks
- [ ] Write LEARNINGS.md (human synthesis of 30 runs)
- [ ] Implement top 3 recommended harness changes
- [ ] Validate in controlled 5-run benchmark

---

## Final Assessment

| Question | Answer |
|----------|--------|
| Is this genuinely useful? | Partially. 30% learning value, 70% documentation value. |
| What's the minimum viable version? | Tier 1 + Tier 2 (130 LOC, ~8 hours). |
| Where does it break down? | 8 modes: swarms, long sessions, discovery liability, vocabulary, causality, context erosion, confabulation, model changes. |
| Simplest integration? | Polips system. One source of truth, multiple views. |
| Recommend now? | Yes, Tier 1+2. No, don't build pattern extraction yet. |

---

## Closing

The pattern of "agent introspection → automated improvement" is theoretically sound. In practice, your 21 runs show that learning is **human-mediated**: agents observe, humans decide, developers implement.

Run notes make the human part faster. They don't automate it away.

Stop trying to build a learning system. Start building a *better documentation system*.

If, after 30 runs, you have obvious patterns and have validated improvements from them, then revisit the question of automation.

Until then: write notes, accumulate metrics, make human decisions.

---

**End of KAREN's Deliberation**

*This analysis is based on 21 existing runs, current repo structure, and honest assessment of what patterns are visible vs. noise. Revisit after run 30 if conditions change.*
