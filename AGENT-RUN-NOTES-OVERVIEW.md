# Agent Run Notes: Architecture Overview

**Date:** 2026-01-15
**Status:** Ready for Implementation (Phase 1)
**Quick Start:** Read this first, then see detailed docs

---

## What is Agent Run Notes?

A **feedback mechanism** that enables the reef to learn from agent execution and automatically improve context injection.

### The Problem It Solves

Current harness: **One-way injection**
```
Session start → Surface polips → Agent works → Session ends
                  (static)
```

Missing: **Feedback loop**
- What context helped? What was missing?
- Did agents waste time searching manually?
- Are polips noisy (false positives)?
- What patterns keep rediscovering?

### The Solution

Three steps:

1. **Agents document observations** (stop hook)
   - What worked? (accurate polips)
   - What was missing? (gaps in reef)
   - What was noise? (false positives)
   - What blocked progress? (clarity issues)

2. **Aggregate signals from multiple runs** (manual or auto-triggered sweep)
   - 6/6 runs say "JWT retry pattern was missing" → **strong signal**
   - 3/6 runs say "oauth-thread was unhelpful" → **medium signal**

3. **Auto-generate harness improvements** (safe + risky tracks)
   - Safe: Create new fossil fact, decompose noisy polips
   - Risky: Enhance constraint text, tune parameters
   - Monitor: Collect data for N weeks, then decide

---

## Architecture at a Glance

### New Components

```
.claude/runs/                    ← NEW directory
├── 2026-01-15-run-001.runlog.xml     ← Agent writes here (stop hook)
├── 2026-01-15-run-002.runlog.xml
├── 2026-01-15-sweep.analysis.xml     ← Sweep analysis result
└── runs.json                         ← Config + sweep triggers

reef analyze runs               ← NEW command
├── --dry-run                  (preview only)
├── --auto-fix                 (apply safe changes)
└── --since <time>             (time filter)
```

### Data Flow

```
User executes task
    ↓
Agent receives surfaced polips (existing: surface hook)
    ↓
Agent works on task
    ↓
Session ends
    ↓
Stop hook runs:
  ├─ reef hook persist       (existing: context polip)
  └─ reef run-note create    (NEW: observations)
    ↓
Run note written to .claude/runs/
    ↓
[ACCUMULATION: 10+ notes, or manual trigger]
    ↓
reef analyze runs
    ├─ Parse observations from each note
    ├─ Aggregate signals (3+ agreement = strong)
    ├─ Generate proposals (create, enhance, archive, tune)
    └─ [--auto-fix: Apply safe ones]
    ↓
Next session: Better reef (new fossils, fewer false positives)
```

---

## Key Design Decisions

| Question | Answer | Why |
|----------|--------|-----|
| **Where do run notes live?** | `.claude/runs/` as RUNLOG polips | Integrate with index/lifecycle, separate from active reef |
| **What triggers sweep?** | Manual, scheduled, or threshold | Flexible (immediate feedback vs. batch analysis) |
| **Run note schema?** | XML with metadata + observations + signals | Same format as other polips, extensible |
| **How are signals extracted?** | Pattern matching (3+ identical signals = strong) | Conservative confidence threshold |
| **What gets auto-applied?** | High-confidence (>90%) safe operations | Create fossils, decompose noisy polips |
| **What needs human review?** | Risky changes (constraint text, parameter tuning) | Preserve authority, avoid breakage |
| **How to rollback?** | Via snapshot (create before sweep) | Existing safeguard mechanism |

---

## Three Example Workflows

### Workflow 1: Manual Feedback (Immediate)

```bash
# Agent finishes task
# Stop hook writes run note automatically

# Human decides to analyze right away
$ reef analyze runs --dry-run

Analyzing 3 run notes...

Proposals:
  [SAFE] Create fossil "JWT Exponential Backoff"
         (3/3 agents said "missing")
         confidence: 95%

  [RISKY] Enhance constraint/auth-flow
          (2/3 agents asked for clarification)
          confidence: 67%

  [MONITOR] Tune tfidf_threshold
            (2/3 felt context was too noisy)
            confidence: 55% (tracking)

# Human reviews and approves safe fix
$ reef analyze runs --auto-fix

  ✓ Created: facts/jwt-exponential-backoff.fact.xml
  ✓ Updated: index.json
  ✓ Generated: runs/sweep-analysis.xml

Next session: Better context (JWT pattern now surfaced).
```

### Workflow 2: Automatic Threshold (Learning Loop)

```bash
# Over a week, 8 agents run similar tasks
# Each writes a run note:
#   - 7 say "JWT pattern missing"
#   - 5 say "oauth-thread unhelpful"

# Auto-trigger: Count ≥ 10 notes
$ reef analyze runs --auto-trigger

Auto-sweep summary:
  ✓ Created: facts/jwt-pattern.fact.xml (7/8 vote)
  ✓ Archived: threads/oauth-integration (5/8 negative)
  → Monitored: tfidf tuning (3/8 noise complaint)

Metrics improvement (before vs. after):
  Accuracy: 82% → 88% (+6 points)
  Noise: 14% → 12% (-2 points)
```

### Workflow 3: Scheduled Analysis (Weekly Review)

```bash
# Cron job runs weekly
0 0 * * 0 cd /project && reef analyze runs --auto-fix

# Every Sunday, automatically:
# 1. Load all run notes from the week
# 2. Extract signals
# 3. Apply safe fixes
# 4. Archive old notes
# 5. Update metrics

# Next week: Improved reef from accumulated experience
```

---

## What Gets Created/Modified

### Safe Auto-Apply (>90% confidence)

✓ **Create new fossil facts**
  - "JWT Exponential Backoff Retry Pattern"
  - "Timeout Resilience Best Practices"
  - Based on 3+ agents independently noting gap

✓ **Decompose noisy polips**
  - Archive threads that are consistently false positives
  - Move to fossils with `@obsolete` marker

✓ **Update metadata**
  - Add `@obsolete` directive to superseded polips
  - Update `updated` timestamp

### Risky Changes (Human Review)

✗ **Modify constraint text** (could break hard requirements)
  - Propose in analysis polip
  - Log as proposal for human review
  - Require explicit approval

✗ **Change parameters** (affects all future runs)
  - tfidf_threshold, max_token_budget, etc.
  - Propose after 2-week monitoring period
  - Require human commit to `.claude/runs.json`

✗ **Rewrite decisions** (architectural records)
  - Propose as enhanced proposal
  - Require owner review + git commit

### Monitor-Only (Data Collection)

? **Parameter tuning** (low confidence)
  - Log in metrics.json
  - Track improvement over 2 weeks
  - If consistent improvement, escalate to risky track

---

## Integration Points (Existing Systems)

### 1. Stop Hook (Unchanged Interface)

```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "reef hook persist"  // Existing
      },
      {
        "type": "command",
        "command": "reef run-note create --auto"  // NEW
      }
    ]
  }
}
```

Agent doesn't need to do anything — observations extracted from transcript.

### 2. Polip Lifecycle (Standard)

Run notes are polips like any other:
- Scope: SESSION (cleaned up regularly)
- Type: RUNLOG (new type)
- Status: ACTIVE → DONE (after analyzed)
- Indexed: Yes (searchable in index.json)

### 3. Snapshot & Rollback (Existing)

Before sweep:
```bash
reef snapshot create "pre-sweep"
reef analyze runs --auto-fix
# If issues: reef snapshot restore pre-sweep
```

### 4. CLI (New Subcommand)

```bash
reef analyze runs [--since <time>] [--dry-run] [--auto-fix]
reef analyze metrics                # Show trends
```

No changes to other commands.

---

## Files Modified/Created

### New Files
- [ ] `docs/agent-run-notes-design.md` (detailed design) ← YOU ARE HERE
- [ ] `docs/runlog-technical-spec.md` (implementation details)
- [ ] `docs/harness-integration.md` (architecture integration)
- [ ] `AGENT-RUN-NOTES-OVERVIEW.md` (this summary)

### Modified Files (Phase 1)
- [ ] `src/reef/blob.py` — Add BlobType.RUNLOG, ANALYSIS; extend Blob fields
- [ ] `src/reef/cli.py` — Add `cmd_analyze()`, argument parsing
- [ ] `.claude/stop.hook.json` (optional) — Add run-note creation hook
- [ ] Tests (unit + integration)

### No Changes Needed
- ✓ Existing polip commands
- ✓ Surface/injection logic
- ✓ Index/search
- ✓ Lifecycle management
- ✓ User-facing APIs

---

## Success Metrics

After 2 weeks of operation:

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Run notes created** | 100% of sessions | Check .claude/runs/ volume |
| **Sweep accuracy** | >80% precision | Compare proposals to actual impact |
| **Context improvement** | +5% accuracy | Compare baseline vs. improved metrics |
| **Noise reduction** | -2% false positives | Track surfaced-irrelevant % |
| **Zero breakage** | 100% (no regressions) | Verify snapshot diffs before/after |

---

## Implementation Timeline

### Phase 1 (Week 1): MVP — Core Run Notes
- Implement: BlobType.RUNLOG, create_run_note(), basic XML serialization
- CLI: `reef run-note create` command
- Testing: Unit tests + manual workflow
- Docs: Design (this file)
- **Output:** Agents can write observations, but no analysis yet

### Phase 2 (Week 2-3): Sweep Analysis
- Implement: Signal aggregation, proposal generation
- CLI: `reef analyze runs --dry-run`
- Testing: Multi-run workflows, conflict detection
- Docs: Technical spec, user guide
- **Output:** Humans can review proposals before applying

### Phase 3 (Week 3-4): Auto-Apply & Metrics
- Implement: Safe fix application, snapshot integration
- CLI: `reef analyze runs --auto-fix`, metrics tracking
- Testing: Rollback scenarios, threshold triggers
- Docs: Harness integration guide
- **Output:** Automatic harness improvement, trend visibility

### Phase 4+ (Ongoing): Refinement
- Scheduled sweeps (cron)
- Dashboard integration (reef reef output)
- Cross-project drift analysis
- Performance optimization

---

## FAQ

**Q: Will this break existing harness?**
A: No. Run notes are opt-in. Existing polips, surfaces, and hooks work unchanged.

**Q: Can the sweep auto-apply break things?**
A: Unlikely. Only safe operations (fossil creation, noisy polip archival) auto-apply. Risky changes require human review. Always snapshot first.

**Q: What if I disagree with a proposal?**
A: Reject it (don't use --auto-fix), or review in dry-run mode. Proposals are suggestions, not mandates.

**Q: Can I see what changed?**
A: Yes. Snapshot diff shows before/after. Analysis polip logs all applied changes.

**Q: How many run notes accumulate before it's a problem?**
A: ~100/week is healthy. After 500, consider archiving old ones. Auto-cleanup available.

**Q: Can I use this for other AIs/agents?**
A: Yes! Any agent writing run notes to .claude/runs/ participates. Signals aggregate across all agents.

**Q: What's the overhead?**
A: ~50ms per run note creation, ~100ms for sweep analysis. Negligible.

---

## Next Steps

1. **Read detailed docs** (in order):
   - `docs/agent-run-notes-design.md` (design decisions)
   - `docs/runlog-technical-spec.md` (code implementation)
   - `docs/harness-integration.md` (system integration)

2. **Review architecture decisions:**
   - Do you agree with the signal aggregation thresholds?
   - Any concerns about auto-apply safety?
   - Suggestions for proposal prioritization?

3. **Plan Phase 1 implementation:**
   - Estimate effort (sketch code)
   - Identify dependencies
   - Define test strategy

4. **Prototype:**
   - Implement core (BlobType.RUNLOG, XML serialization)
   - Manual end-to-end workflow
   - Iterate on schema based on feedback

---

## References

- **CLAUDE.md** — Reef architecture (polips, scopes, lifecycle)
- **docs/2026-01-15-reef-native-infrastructure-design.md** — Reef vision (calcification, evolution)
- **blob.py** — Blob/Glob implementation (1960 lines)
- **cli.py** — CLI structure (1411 lines)

---

**Author:** Architect (with Claude)
**Date:** 2026-01-15
**Status:** Ready for team review

