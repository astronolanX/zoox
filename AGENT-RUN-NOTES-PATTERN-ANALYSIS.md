# KAREN's Skeptical Review: "Agent Run Notes" Pattern

**Author**: KAREN (Skeptical Validator)
**Date**: 2026-01-15
**Status**: Critical Analysis

---

## TL;DR Verdict

**Genuine Value**: 30% · **Overhead**: 50% · **Usefulness Diminishes With**: 40+ runs

This pattern solves a *real* problem (harness learning), but **the cure exceeds the disease** for your current scale. You already have 21 runs with structured XML. The question is: *what learning actually happens from accumulating notes?*

---

## The Pattern: What It Claims

> "Agents write notes during each run (what worked, what didn't, missing context). Then sweep through multiple run notes to improve the harness automatically."

**Implicit claims:**
1. Agent introspection is accurate and honest
2. Patterns emerge that aren't visible from single runs
3. Automatic improvements can be extracted from notes
4. Running multiple agents and aggregating notes is cheaper than direct optimization

---

## Critical Analysis: Where This Breaks

### 1. **Introspection Bias (Confabulation Risk)**

You're already seeing this in run-017:
```xml
<what-didnt>
  <item>Spark swarm tendency to invert every premise may be pattern-lock
         rather than genuine insight</item>
  <item>Confidence scores feel optimistically distributed—unclear if
         actual model outputs or simulated</item>
</what-didnt>
```

**The problem**: Agents confabulate explanations for their own behavior. When you ask "what didn't work," they generate plausible-sounding failures, not actual failures.

**Evidence**: run-021 Karen verdict contradicted Architect's confidence in retention design. The Architect *believed* the design was solid. The notes said "what worked" but the reality was "this creates discovery liability."

**Implication**: Run notes are useful for *what humans learn about the agent's thinking*, not for *what actually worked*.

---

### 2. **The "Sweep" Never Happens**

You have 21 runs. Show me:
- [ ] A script that reads all 21 run XMLs
- [ ] Logic that extracts patterns across runs
- [ ] Automatic harness improvements implemented from patterns
- [ ] Metrics proving those improvements worked

**Reality**: None exist. The pattern assumes sweeping is free and automatic. It isn't.

**Cost to implement sweep**:
- ~50-100 LOC to parse all run XMLs
- ~100-200 LOC to normalize "what worked" across different agent vocabularies
- ~300-500 LOC to extract actionable patterns (clustering, trend detection)
- ~200-300 LOC to implement actual improvements
- ~1-2 hours per week to validate that improvements actually improved things

**Total**: 40-50 hours of engineering to close the loop.

---

### 3. **Vocabulary Fragmentation**

Compare actual run notes:
- run-017: "Spark skill effective for divergent exploration"
- run-021: "/team orchestration efficiently parallelized Architect + Karen"
- run-010 (implied): Different agent, different vocabulary

**Problem**: There is no canonical vocabulary for "what worked." So sweeping requires:
- Either: Normalize all notes to a standard schema (engineering overhead)
- Or: Use LLM to extract meaning (token cost + hallucination risk)

Both are expensive relative to the insight gained.

---

### 4. **Timing Mismatch: Notes vs. Remediation**

Run-021 Karen found that retention policy creates discovery liability.
- **When discovered**: 2026-01-15, ~90min into run
- **When fixed**: TBD (weeks from now, pending redesign)
- **Value of run notes about this in run-022?**: ~0

The gap between "notes identify problem" and "system improves" defeats the learning-loop purpose.

**Worse case**: You accumulate 50 runs worth of notes about problems that take weeks to fix. The notes become noise.

---

### 5. **Missing Context Problem**

Your run notes record *what happened in that run*, but they can't capture *why it mattered*.

Example from run-017:
```xml
<what-didnt>
  <item>Confidence scores feel optimistically distributed—unclear
         if actual model outputs or simulated</item>
</what-didnt>
```

**Question**: Is this a blocker? A minor UX complaint? A threat model issue?

**Answer**: Unknown from notes. You'd need to read the full spark outputs, synthesize context, then decide if it matters.

This is exactly what you're *already doing* when you write `START-HERE.md` and `ARCHITECTURE-ANALYSIS.md` manually.

---

### 6. **Integration Debt: Multiple Systems**

You now have:
- **reef polips** (XML-based memory, structured, searchable)
- **run notes** (XML files in `.claude/runs/`)
- **incubator** (insights, raw/synthesized/crystallized)
- **/introspect** (MCP usage, session state)
- **metrics.json** (cost/latency tracking)

These are 5 separate systems, none integrated.

**Reality**: Agents can't automatically synthesize across all 5. You end up manually:
- Reading run notes
- Checking metrics.json
- Searching incubator
- Reviewing polips
- Inferring patterns

That's the opposite of automation.

---

## Where Run Notes *Actually* Work

### ✓ Use case: Single-agent specialization tracking

If you have a **Frontend Agent** who should only handle UI work, run notes *can* track:
- Did it stay in scope?
- Did it introduce backend changes (scope creep)?
- Latency/token trends over time?

**Cost**: Low (agent writes 5 bullets per run)
**Benefit**: Medium (you can see if agent is drifting)
**Frequency**: Use this for 1-2 agents, not swarms of 64.

---

### ✓ Use case: Debugging specific failures

If mediator skill crashes on "case law research," notes like:
```
what-didnt:
  - "Semantic PII detector false-positives on case citations"
  - "Research routing failed on domain mismatch"
```

Are useful for *reproducing* the failure.

**Cost**: Low (error logging is free)
**Benefit**: High (faster debugging)
**Frequency**: Use this for **error reconstruction**, not general learning.

---

### ✓ Use case: Metric baselines

If you run the same scenario 5 times with different harness configs, run notes *can* record:
- Tokens used
- Latency
- Success/failure rate
- Quality of outcome

**Then**: Aggregate across 5 runs, pick the best config.

**Cost**: Medium (requires consistent scenario setup)
**Benefit**: High (A/B testing works)
**Frequency**: Use this for **benchmarking**, not continuous learning.

---

## The Minimum Viable Version

If you *must* have run notes, here's the smallest viable implementation:

### Tier 1: Automatic (No agent effort)
```yaml
# Auto-captured in every run
- start_time, end_time (duration)
- model used, token count
- agents spawned (names)
- exit code (success/failure)
- files created count
- files modified count
```

**Cost**: ~50 LOC hook, automatic per session
**Usefulness**: Moderate (metrics only, no insights)

### Tier 2: Lightweight agent notes (agent writes 3-5 bullets)
```yaml
# Agent provides high-level summary
what_worked:
  - "Agent stayed in scope"
failures:
  - "Time-limit triggered on research task"
next_priority:
  - "Implement pagination for large searches"
```

**Cost**: Agent spends 2min per run writing bullets
**Usefulness**: Moderate (readable, but no automatic extraction)

### Tier 3: Structured schema (agent fills form)
```yaml
# Agent picks from predefined options
quality_score: 8/10  # Self-assessment
scope_drift: false   # Did it wander?
token_efficiency: 85 # (tokens used / expected)
failures: [rate_limit_hit, timeout]
```

**Cost**: Agent thinks carefully, 3-5min per run
**Usefulness**: High (queryable, can aggregate across runs)

---

## Integration with Existing Systems

**Do NOT** create a 6th system. Instead:

### Option A: Run notes → Polips (Recommended)
When a run completes, convert notes to reef polips:
```python
# In /introspect hook or CLI
def run_to_polip(run_xml):
    polip = Polip(
        type="decision",  # or "thread" for ongoing work
        summary=run.summary,
        content=run.what_worked + run.what_didnt,
        tags=[run.agents_used],
        metrics={
            "duration": run.duration,
            "tokens": run.tokens,
            "files_created": run.files_created,
        }
    )
    reef.write(polip)
```

**Cost**: ~100 LOC
**Benefit**: Notes live in searchable polip system, not separate XML
**Integration**: `/reef index --search "spark efficiency"` finds all spark runs

### Option B: Run notes → metrics.json (Simpler)
Aggregate structural data only:
```json
{
  "runs": [
    {
      "id": "021",
      "date": "2026-01-15",
      "duration_minutes": 90,
      "agents": ["Architect", "Karen"],
      "tokens_used": 45000,
      "files_created": 4,
      "exit_code": "success"
    }
  ]
}
```

**Cost**: ~50 LOC to extract and aggregate
**Benefit**: Queryable time-series for trend detection
**Integration**: `reef metrics --chart tokens_by_agent` generates graphs

---

## The Honest Assessment

### What This Pattern *Actually* Optimizes For

Not harness improvement. It optimizes for:
- **Narrative continuity** (agents have context between runs)
- **Accountability** (audit trail of "what we tried")
- **Human retrospection** (you can write `START-HERE.md` faster)

All are valuable, but they're not *learning loop* benefits.

---

### The Real Learning Loop (Unglamorous Truth)

This is happening right now:

1. **Run-021**: Karen finds retention policy is liability
2. **You** (human) read Karen's notes, understand the threat model
3. **You** (human) write ARCHITECTURE-ANALYSIS.md with the fix
4. **You** (human) decide: "Redesign retention to session-only"
5. **Someone** (Architect or you) implements the fix
6. **Run-022+**: The fix is validated

The harness improves because *you synthesize context across runs*. Run notes help, but they don't automate this.

---

## Recommendation: Layered Approach

### Phase 0: Now (2026-01-15)
**Keep**: Your current run notes (already written, useful for retrospection)
**Add**: Automatic metrics collection (tokens, duration, success/failure)

**Cost**: ~50 LOC
**Benefit**: Establish baseline, no agent overhead

---

### Phase 1: After 10 more runs (2026-01-25)
**Review**: Do patterns emerge in the 31 runs of data?
- Do certain agents consistently exceed token budgets?
- Do specific scenarios trigger higher failure rates?
- Is there seasonality to performance?

**If NO patterns**: Stop here. Run notes aren't worth it.
**If YES patterns**: Proceed to Phase 2.

---

### Phase 2: Targeted optimizations (conditional)
**If patterns found**: Design 1-2 specific improvements based on data.
- Example: "Frontend agent consistently over-token; add constraints"
- Example: "Research scenario fails 40% of time; needs buffering"

**Validate** in 5-run subset before rolling out.

**Cost**: High (actual engineering per improvement)
**Benefit**: Proven performance gains, not speculative

---

## Edge Cases Where This Breaks Down

### Case 1: 64-agent swarm (claude-flow)
If you deploy 64 parallel agents, aggregating run notes from each becomes:
- 64 × "what worked" summaries = 320 bullets per run
- NLP pipeline needed to extract signal
- Automatic improvements from 320 bullets = near-zero signal

**Verdict**: Infeasible at scale. Need distributed telemetry instead.

---

### Case 2: Interactive mediation sessions
Mediator runs aren't "discrete runs." They're 8-hour sessions with multiple mode transitions.

**Problem**: "Run notes at session end" loses all the mid-session learning.

**Better**: Capture mode-transition decisions in real-time (polips), not end-of-session notes.

---

### Case 3: Adversarial testing
If mediator is tested against motivated opposition (discovery threat), notes like "our retention policy works" are **discoverable liability** (Karen's finding).

**Verdict**: Notes become evidence against you.

---

## Questions for You

Before investing in this pattern, answer:

1. **What decision is blocked by missing run notes?**
   - You can't optimize harness without knowing what broke
   - But you already know this from manual run review
   - What *specifically* can't you do now?

2. **How many runs before patterns are obvious?**
   - With 21 runs, you can see: spark skill works, /team orchestration is efficient, retention is liability
   - You saw this from 2-3 runs, not 21
   - When do you expect diminishing returns?

3. **Who sweeps the notes?**
   - Automatic script (engineering debt)
   - You manually (defeats automation benefit)
   - LLM extraction (token cost, hallucination risk)

4. **Is the alternative cheaper?**
   - Manual: You write 10-minute retrospective per 3 runs, capture decisions in ARCHITECTURE.md
   - Automated: You build 3-4 systems, integrate them, maintain forever

---

## Final Verdict

| Dimension | Rating | Why |
|-----------|--------|-----|
| **Solves real problem?** | ✓ (narrative continuity) | Yes, but it's a documentation problem, not automation |
| **Cost-justified?** | ✗ (40+ hours overhead) | Only if you have 50+ runs generating patterns |
| **Integration complexity** | ✓ (can layer with polips) | Medium, manageable via polip system |
| **Sustainable?** | ✗ (scales poorly to 64 agents) | Collapses at swarm sizes |
| **Recommend now?** | ✗ (premature) | Build it after 30+ runs show obvious patterns |

---

## What You Should Do Instead

### Right now
1. Keep writing run notes (human narrative is valuable)
2. Add automatic metrics collection (~50 LOC)
3. Convert run notes to polips as they're written (~100 LOC)

### After 10 more runs (2026-01-25)
1. Query `.claude/runs/` for patterns in what-worked/what-didnt
2. If patterns exist → Phase 2
3. If no patterns → Declare victory, run notes are sufficient documentation

### If patterns exist
1. Design 1-2 targeted optimizations
2. A/B test in controlled environment (5 runs per config)
3. Roll out winners, document in CLAUDE.md

---

## Key Insight (The Real Truth)

Your harness doesn't learn from run notes.

**You** learn from run notes, then **you** decide how the harness improves.

The pattern of "accumulate notes → extract patterns → automate improvements" assumes agents improve themselves. They don't. *You* improve the harness, and agents implement your decisions.

So the question isn't "how do we automate harness learning?"

The question is "how do we make it easier for humans to synthesize context and make good harness decisions?"

For that, run notes help (human narrative continuity), but:
- Polips (searchable, structured) help more
- metrics.json (queryable time-series) helps more
- Automatic error logs (fail-closed, always available) help more

---

## Appendix: Minimum Viable Implementation

If you're determined to try this:

**File**: `.claude/harness/agent_notes.py`
```python
import json
from datetime import datetime
from pathlib import Path

class RunNotes:
    def __init__(self, run_id):
        self.run_id = run_id
        self.notes = {
            "timestamp": datetime.now().isoformat(),
            "agents_used": [],
            "what_worked": [],
            "what_didnt": [],
            "metrics": {
                "tokens_used": 0,
                "duration_seconds": 0,
                "files_created": 0,
            },
            "next_steps": []
        }

    def add_what_worked(self, item):
        self.notes["what_worked"].append(item)

    def add_what_didnt(self, item):
        self.notes["what_didnt"].append(item)

    def save(self):
        path = Path(f".claude/runs/run-{self.run_id}.json")
        with open(path, "w") as f:
            json.dump(self.notes, f, indent=2)

    @staticmethod
    def aggregate(run_ids=None):
        """Sweep all run notes, extract patterns."""
        runs_dir = Path(".claude/runs/")
        runs = list(runs_dir.glob("run-*.json"))

        all_notes = []
        for run_file in sorted(runs):
            with open(run_file) as f:
                all_notes.append(json.load(f))

        # TODO: Extract patterns, suggest improvements
        # For now, just return raw aggregation
        return {
            "total_runs": len(all_notes),
            "runs": all_notes,
        }
```

**Cost**: ~80 LOC
**Usefulness**: Provides structure for notes, queryable JSON instead of XML

---

**End Analysis**

*This pattern is worth revisiting after 30 runs. Until then, it's optimization theater.*

---

## References

- run-017.xml: Spark exploration, notes pattern observed
- run-021.xml: Karen validation, threat model discovery
- ARCHITECTURE-ANALYSIS.md: Manual synthesis of design decisions
- START-HERE.md: Human-written retrospective across 21 runs
