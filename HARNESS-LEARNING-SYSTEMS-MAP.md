# Harness Learning Systems: What You Actually Have (And What's Missing)

**Author**: KAREN
**Date**: 2026-01-15
**Status**: Architectural inventory + integration map

---

## Current Systems (What Exists)

### System 1: `.claude/runs/*.xml` (Run Notes)
**Status**: ✓ Manually written
**Frequency**: Per agent session
**Content**: what-worked, what-didnt, files-created, ideas-captured

```xml
<run id="017" date="2026-01-14">
  <what-worked>...</what-worked>
  <what-didnt>...</what-didnt>
  <!-- 60-80 lines per run -->
</run>
```

**Searchability**: None (filesystem search only)
**Queryability**: None (would need XML parser)
**Integration**: Isolated; manually reviewed

---

### System 2: `.claude/ideas/*` (Idea Capture)
**Status**: ✓ Auto-populated from run notes
**Frequency**: As ideas surface
**Content**: Structured markdown files with metadata

**Searchability**: Via `reef index --type fossil` (yes, TF-IDF works)
**Queryability**: Via polips
**Integration**: Connected to incubator system

---

### System 3: `~/.claude/incubator/` (Global Insight Store)
**Status**: ✓ Exists, structured (raw/synthesized/crystallized)
**Frequency**: When ideas are promoted
**Content**: YAML + content, tiered maturity

**Searchability**: ✓ Context7 or custom TF-IDF
**Queryability**: ✓ YAML structure searchable
**Integration**: ✓ Feeds back to `/CLAUDE.md` when crystallized

---

### System 4: `metrics.json` (Planned)
**Status**: ✗ Not yet implemented
**Expected content**: tokens, latency, cost, success/failure
**Frequency**: Auto-captured per run

**Searchability**: ✓ JSON queryable
**Queryability**: ✓ Time-series analysis possible
**Integration**: ✗ No consumers yet

---

### System 5: `/introspect` (MCP Observability - Planned)
**Status**: ✗ Not yet implemented
**Expected**: Tool use patterns, context window utilization, error backtraces

**Searchability**: TBD
**Queryability**: TBD
**Integration**: TBD

---

## The Gap Analysis: What's Missing

### Gap 1: **No Automatic Pattern Extraction**
You have:
- 21 XML run files with notes
- Ideas captured as polips
- Incubator with insights

You don't have:
- Script that reads all 21 run files
- Analysis that says "spark skill has 90% success rate"
- Suggestions like "add spark-specific constraints"

**Who fills this gap?** You manually (slow) or build ML pipeline (expensive).

---

### Gap 2: **No Lifecycle for Decisions**
Ideas exist:
```
.claude/ideas/composable-operations.md
  → ~/.claude/incubator/raw/ins_2026011478-composable-operations.yaml
```

But how do they become harness improvements?

**Missing step**: When Karen says "retention policy is liability," where does that become:
- [ ] A bedrock constraint?
- [ ] A new security polip?
- [ ] A CLAUDE.md update?
- [ ] A code change?

**Current flow**: Manual (you read ARCHITECTURE-ANALYSIS.md, decide, implement).

---

### Gap 3: **No Per-Agent Telemetry**
When you run `/team`, you spawn:
- Architect
- Visionary
- Karen

But you can't query:
- "Which agent used most tokens?"
- "Which agent converged fastest?"
- "Which agent produced most ideas?"

**Why it matters**: If Visionary is 30% cheaper than Architect, you'd want to know.

---

### Gap 4: **No Failure Classification**
Run notes say "what didn't work," but:
- Is it a crash (agent error)?
- Is it a timeout (performance issue)?
- Is it a design flaw (Karen's verdict)?
- Is it out-of-scope (user error)?

**Missing**: Structured error taxonomy.

---

### Gap 5: **No Comparative A/B Testing**
You can't run:
```
reef run --config config-v1 scenario-1 (5x)
reef run --config config-v2 scenario-1 (5x)
reef compare --metric tokens
```

**Why**: No mechanism to hold scenario constant while varying harness.

---

## Integration Complexity Matrix

| System | Connected to | Cost to Connect | Benefit |
|--------|--------------|-----------------|---------|
| `.claude/runs/*.xml` | incubator | ~100 LOC | High (ideas auto-pop) ✓ |
| `metrics.json` | runs/* | ~80 LOC | Medium (baselines) ✓ |
| `metrics.json` | polips | ~150 LOC | High (searchable history) ✓ |
| `/introspect` | metrics.json | ~200 LOC | Medium (detailed traces) ✓ |
| Pattern extraction | all systems | ~500-1000 LOC | Low to Medium* |
| Per-agent telemetry | metrics.json | ~100 LOC | High (agent comparison) ✓ |
| Failure classification | runs/* | ~200 LOC | High (root cause) ✓ |
| A/B testing harness | metrics.json | ~300 LOC | High (data-driven) ✓ |

\* Pattern extraction benefit varies: works great at 50+ runs, noise at <20 runs.

---

## What Should You Build First? (Priority-Based)

### Tier 1: Automatic, Free (Do Now)
- [x] Keep writing run notes (already doing)
- [ ] Add automatic error logging (~20 LOC)
- [ ] Capture exit_code in every run (~10 LOC)

**Effort**: ~30 LOC total
**Benefit**: Baseline data for future analysis

---

### Tier 2: Low-Cost, High-Value (Next 2 runs)
- [ ] metrics.json auto-generation (~80 LOC)
- [ ] Per-agent token tracking (~50 LOC)
- [ ] Basic time-series query script (~100 LOC)

**Effort**: ~230 LOC
**Benefit**: Can answer "which agent is most efficient?"

---

### Tier 3: Medium-Cost, Conditional (After 30 runs)
- [ ] Pattern extraction script (~300 LOC)
- [ ] Automatic idea promotion (polip ↔ incubator sync) (~150 LOC)
- [ ] Failure classification taxonomy (~200 LOC)

**Effort**: ~650 LOC
**Benefit**: Only if patterns exist (20% probability at 30 runs)

---

### Tier 4: High-Cost, Specialized (Only if Needed)
- [ ] A/B testing framework (~300 LOC)
- [ ] Full /introspect integration (~500 LOC)
- [ ] Distributed telemetry for swarms (~1000 LOC)

**Effort**: ~1800 LOC
**Benefit**: Only justified for 50+ runs, 64-agent swarms, or adversarial testing

---

## Honest Assessment: Where the Money Is

### Highest ROI Integration (Easy + Useful)

**metrics.json + polips + time-series query:**
```bash
# After implementation:
reef metrics --chart tokens_by_run --agent "*"
# Output: Graph showing token trend across runs
```

**Cost**: ~230 LOC
**Benefit**: Unlocks "is the harness improving?" question
**Timeline**: ~4 hours of work

---

### Medium ROI Integration (Harder but Worthwhile)

**Run notes → polips → searchable decisions:**
```bash
# After implementation:
reef index --search "retention policy"
# Output: run-021.xml + ARCHITECTURE-ANALYSIS + decision polip
```

**Cost**: ~100 LOC
**Benefit**: Unified memory across all systems
**Timeline**: ~3 hours of work

---

### Low ROI Integration (Expensive, Speculative)

**Automatic pattern extraction + harness optimization:**
```bash
# After implementation:
reef learn --from-runs 1-21 --suggest-improvements
# Output: "Add rate-limiting for Groq. Add token budget for Architect."
```

**Cost**: ~800 LOC + ongoing maintenance
**Benefit**: Speculative (uncertain if patterns exist or matter)
**Timeline**: ~24 hours of work

---

## The Honest Truth: What Actually Drives Harness Improvement

Looking at your 21 runs:

| Run | Major Improvement Came From | Source |
|-----|----------------------------|--------|
| 001-005 | You setting up skeleton | Manual architecture |
| 006 | Team orchestration works | /team command, manual testing |
| 007-016 | Incremental feature adds | Feature requests, manual design |
| 017 | Spark skill parallelization | You reading spark outputs manually |
| 018-020 | Mediator safety design | You + Karen discussion, manual validation |
| 021 | Karen catches retention liability | Manual adversarial review |
| 022+ | ? | *This is what you're asking about* |

**Pattern**: Every major improvement came from:
1. **Manual human review** of outputs
2. **Deliberate design decision** based on threat model
3. **Implementation** by developers
4. **Validation** in next run

Run notes *supported* this, but they didn't *drive* it.

---

## Red Flag: When You're Doing It Wrong

You'll know the "agent run notes" pattern is failing if:

1. **Accumulating more than 1 run note per week but 0 harness changes**
   → You're generating noise, not signal

2. **Spending time writing detailed notes but never reading them**
   → Documentation theater

3. **Running 50 runs and still manually making harness decisions**
   → Notes didn't automate anything

4. **Building "pattern extraction" scripts without actual patterns**
   → YAGNI (you aren't gonna need it)

5. **Integration debt: 6 separate memory systems (polips + runs + incubator + metrics + introspect + ???)**
   → Should have 1-2 systems

---

## Recommended Path Forward

### This Week (2026-01-15 to 2026-01-22)
- Continue writing run notes (free, useful)
- Implement Tier 1 auto-capture (30 LOC, 30 min)
- Don't worry about extraction/patterns

---

### Next Week (2026-01-22 to 2026-01-29)
- Run 5 more sessions (runs 22-26)
- Review: Are obvious patterns emerging?
- If yes → Build Tier 2 (metrics.json)
- If no → Declare "run notes sufficient," move on

---

### Two Weeks Out (2026-01-29 to 2026-02-12)
- If patterns exist AND metrics show improvement → Tier 3
- If no patterns → Stop. Accept that harness learning is human-driven.

---

## Final Recommendation

**Don't** build "agent run notes" as a standalone learning system.

**Do** build it as part of a integrated memory stack:

```
Run Notes (XML)
    ↓ auto-extract ideas → incubator
    ↓ parse metadata → metrics.json
    ↓ crystallize insights → reef polips
    ↓ queryable via reef index
```

**Single source of truth**: Reef polips (everything flows through)

**Cost**: ~500 LOC across all systems
**Benefit**: Unified, searchable, decentralized

---

## Code Skeleton: Minimal Viable Integration

**File**: `src/reef/harness.py`
```python
import json
from pathlib import Path
from xml.etree import ElementTree as ET

class HarnessMetrics:
    """Automatic metrics collection for harness learning."""

    def __init__(self, run_id):
        self.run_id = run_id
        self.metrics = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "tokens_used": 0,
            "duration_seconds": 0,
            "files_created": 0,
            "files_modified": 0,
            "agents_used": [],
            "exit_code": "pending",
        }

    def add_agent(self, name):
        self.metrics["agents_used"].append(name)

    def set_exit_code(self, code):
        self.metrics["exit_code"] = code

    def save(self):
        path = Path(".claude/runs") / f"run-{self.run_id}.metrics.json"
        with open(path, "w") as f:
            json.dump(self.metrics, f, indent=2)

    @staticmethod
    def aggregate_all():
        """Return aggregated metrics across all runs."""
        runs_dir = Path(".claude/runs/")
        metrics_files = list(runs_dir.glob("run-*.metrics.json"))

        data = []
        for f in sorted(metrics_files):
            with open(f) as fp:
                data.append(json.load(fp))

        return {
            "total_runs": len(data),
            "runs": data,
            "avg_tokens_per_run": sum(r["tokens_used"] for r in data) / len(data) if data else 0,
            "avg_duration_seconds": sum(r["duration_seconds"] for r in data) / len(data) if data else 0,
        }

# Usage in hooks:
# metrics = HarnessMetrics("021")
# metrics.add_agent("Architect")
# metrics.set_exit_code("success")
# metrics.save()
```

---

**End of report.**

*Use this to decide: are you optimizing for narrative continuity, or actual harness learning? Choose one, build accordingly.*
