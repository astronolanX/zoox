# Agent Run Notes Integration with Harness Architecture

**Date:** 2026-01-15
**Status:** Integration Design
**Audience:** Architects, implementation leads

---

## Executive Summary

Agent Run Notes creates a **feedback loop** in the reef-based harness:

```
Session N: Agent executes task → Context injected (surface)
                            ↓ (stop hook)
           Agent writes observations → Run note created
                            ↓ (accumulated)
Session N+k: Manual sweep or threshold trigger
                            ↓
           Analyze run notes → Extract signals → Generate proposals
                            ↓
           Apply safe fixes → Improved reef
                            ↓
Session N+k+1: Agent executes task → Better context injected (surface)
```

This closes the **OBSERVE → ANALYZE → ADAPT** learning loop described in CLAUDE.md.

---

## Current Architecture (Baseline)

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE SESSION                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  UserPromptSubmit Hook                                  │  │
│  │    → reef hook surface                                  │  │
│  │    → Inject polips as XML                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ↑                                     │
│                    [CONTEXT INJECTED]                            │
│                            ↑                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Agent Execution (Claude)                              │  │
│  │    → Task work                                          │  │
│  │    → References context implicitly                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Stop Hook                                              │  │
│  │    → reef hook persist (context polip)                  │  │
│  │    → (NEW) reef run-note create (observations)          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    REEF (Local Memory)                          │
│                                                                 │
│  ├─ .claude/constraints/                                        │
│  ├─ .claude/decisions/                                          │
│  ├─ .claude/threads/                                            │
│  ├─ .claude/facts/                                              │
│  ├─ .claude/contexts/        ← session-scoped                   │
│  ├─ .claude/runs/            ← (NEW: run observations)          │
│  ├─ .claude/index.json       ← TF-IDF search                    │
│  └─ .claude/metrics.json     ← (NEW: trend tracking)            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    HARNESS OPERATIONS                           │
│                                                                 │
│  ├─ reef init                                                   │
│  ├─ reef sprout (create polips)                                 │
│  ├─ reef surface (inject to agent) ← UserPromptSubmit hook      │
│  ├─ reef sink (archive stale)                                   │
│  ├─ reef sync (check integrity)                                 │
│  ├─ reef analyze runs          ← (NEW: sweep & adapt)           │
│  └─ reef drift (cross-project)                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## New Components (Run Notes Extension)

### 1. Stop Hook Extension

**Existing:** `reef hook persist` creates context polip

**New:** `reef run-note create` writes observations

```
┌─────────────────────────────────────────────────────┐
│  Stop Hook (extends existing)                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. reef hook persist                               │
│     → Create/update .claude/context.blob.xml        │
│     (session state summary)                         │
│                                                     │
│  2. reef run-note create     [NEW]                  │
│     → Create .claude/runs/RUN-*.runlog.xml          │
│     (agent observations: works, missing, noise)     │
│                                                     │
│  3. reef analyze runs --check [OPTIONAL]            │
│     → If triggers met, auto-sweep                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 2. Sweep System

**Triggered by:**
- Manual: `reef analyze runs` (human decision)
- Scheduled: Cron job (weekly/daily)
- Threshold: Auto-triggered when 10+ notes accumulated or pattern detected

**Process:**

```
Scan .claude/runs/*.runlog.xml
    ↓
Parse metadata, observations, signals from each
    ↓
Aggregate by signal type (create, enhance, archive, tune)
    ↓
Compute confidence scores (% agreement)
    ↓
Generate proposals (ranked by confidence × impact)
    ↓
[DRY-RUN MODE: Print and exit]
    ↓
[AUTO-FIX MODE: Apply safe proposals]
    ├─ Create new fossils (fact polips)
    ├─ Decompose false-positive polips
    ├─ Mark obsolete polips
    └─ Log attempted changes
    ↓
Create analysis polip (.claude/runs/sweep-*.analysis.xml)
    ↓
Update .claude/runs.json with sweep timestamp
```

### 3. Metrics Tracking (Optional)

Track improvement over time in `.claude/metrics.json`:

```json
{
  "accuracy": {
    "2026-01-14": 0.82,
    "2026-01-15": 0.88,
    "trend": "↑"
  },
  "latency_ms": {
    "2026-01-14": 42,
    "2026-01-15": 45
  },
  "token_efficiency": {
    "avg_per_run": 2100,
    "baseline": 2200,
    "savings_pct": 4.5
  }
}
```

---

## Data Flow Diagram

### Per-Session Flow (Run Note Creation)

```
┌─ Claude Code Stop Hook ─────────────────────────┐
│                                                 │
│  Hook receives:                                 │
│  - Session transcript                           │
│  - Task summary                                 │
│  - Agent's own observations (if provided)       │
│                                                 │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
    ┌────────────────────────────┐
    │ Parse Observations:         │
    │ - What worked?              │
    │ - What was missing?         │
    │ - What was noise?           │
    │ - What blocked progress?    │
    └────────────────┬────────────┘
                     │
                     ↓
    ┌────────────────────────────────────┐
    │ Extract Signals:                    │
    │ - Create fossil (missing pattern)   │
    │ - Enhance constraint (unclear)      │
    │ - Archive polip (false positive)    │
    │ - Tune parameter (too noisy)        │
    └────────────────┬───────────────────┘
                     │
                     ↓
    ┌────────────────────────────────────┐
    │ Write Run Note (RUNLOG polip)       │
    │ → .claude/runs/RUN-{time}-{sid}.xml│
    │                                    │
    │ Contains:                           │
    │ - metadata (task, timing, status)   │
    │ - observations (works/missing)      │
    │ - signals (proposals)               │
    │ - surfaced polips (what was inject) │
    └────────────────┬───────────────────┘
                     │
                     ↓
    ┌────────────────────────────────────┐
    │ [Optional] Check Sweep Triggers:    │
    │ - 10+ notes accumulated?            │
    │ - Error pattern repeated 3x?        │
    │ - Auto-trigger reef analyze         │
    └────────────────────────────────────┘
```

### Multi-Session Aggregation (Sweep Analysis)

```
┌─ Week Passes: 10+ Run Notes Accumulated ─┐
│                                           │
│  .claude/runs/                            │
│  ├─ RUN-2026-01-15-abc123.runlog.xml     │
│  ├─ RUN-2026-01-15-def456.runlog.xml     │
│  ├─ RUN-2026-01-16-ghi789.runlog.xml     │
│  └─ ... (more runs)                      │
│                                           │
└───────────────┬──────────────────────────┘
                │
                ↓
    ┌─────────────────────────────────┐
    │ reef analyze runs               │
    │                                 │
    │ 1. Load all run notes           │
    │ 2. Parse signals from each      │
    │ 3. Aggregate by signal type     │
    └─────────────────┬───────────────┘
                      │
                      ↓
    ┌──────────────────────────────────────┐
    │ Signal Aggregation:                   │
    │                                      │
    │ create/JWT-retry-pattern              │
    │   [6 votes] confidence=0.95           │
    │                                      │
    │ enhance/constraints/auth-flow         │
    │   [5 votes] confidence=0.82           │
    │                                      │
    │ archive/threads/oauth-integration     │
    │   [4 votes] confidence=0.91           │
    │                                      │
    │ tune/tfidf_threshold                  │
    │   [3 votes] confidence=0.65           │
    └──────────────────┬───────────────────┘
                       │
                       ↓
    ┌──────────────────────────────────────┐
    │ Generate Proposals:                   │
    │                                      │
    │ [SAFE] Create fossil (confidence>90%) │
    │   → Auto-apply with --auto-fix        │
    │                                      │
    │ [RISKY] Enhance constraint (82%)      │
    │   → Human review required             │
    │                                      │
    │ [SAFE] Archive false positive (91%)   │
    │   → Auto-apply with --auto-fix        │
    │                                      │
    │ [MONITOR] Tune parameter (65%)        │
    │   → Log for 2-week observation        │
    └──────────────────┬───────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ↓                             ↓
    DRY-RUN                       AUTO-FIX
    (preview only)                (apply changes)
        │                             │
        ↓                             ↓
    Print proposals             Apply safe proposals:
    to stdout                   - Create fossils
                                - Decompose polips
                                - Update metadata
                                │
                                ↓
                            Create analysis polip
                            (.claude/runs/sweep-*.analysis.xml)
                                │
                                ↓
                            Return to user:
                            - Applied changes
                            - Monitored proposals
                            - Metrics improvement
```

---

## Feedback Loop: Context Improvement

### Round 1: Baseline

```
Run 1: Agent works on authentication task
  ├─ Surfaced: 5 polips (auth-constraint, oauth-thread, ...)
  ├─ Result: Success, but searched git manually for retry pattern
  ├─ Observation: "Missing JWT retry pattern example"
  └─ Signal: "create_fact: JWT retry pattern"

Run 2: Similar task, similar observations
  └─ Signal: "create_fact: JWT retry pattern"
  ... (3 more runs accumulate)
```

### Sweep Triggered

```
Sweep Analysis (after 6 similar observations):
  → Confidence: 0.95 (6/6 votes)
  → Proposal: Create fact "JWT Exponential Backoff Retry Pattern"
  → Auto-apply: YES (confidence > 0.90)

Actions:
  ✓ Create .claude/facts/jwt-retry-pattern.fact.xml
  ✓ Update index.json
  ✓ Create sweep analysis polip
```

### Round 2: Improved Context

```
Run 7: New agent works on authentication task
  ├─ Surfaced: 6 polips (auth-constraint, jwt-retry-pattern [NEW], ...)
  ├─ Result: Success, no manual search needed
  ├─ Observation: "JWT retry pattern was directly applicable"
  └─ Signal: "works: JWT retry pattern"

Metrics:
  - Context quality: 82% → 88%
  - Reduced manual search: 15min → 0min
  - Accuracy: Improved
```

---

## Integration with Harness Components

### A. Polip Management

Run notes integrate with existing polip commands:

```bash
# Create run note (via stop hook)
reef run-note create --task "bugfix" --observations "..."

# Analyze accumulates run notes
reef analyze runs

# Proposals may create new fossils
→ reef sprout fact "JWT Retry Pattern"

# Or decompose false positives
→ reef decompose oauth-integration
```

### B. Index & Search

Run notes are indexed like other polips:

```
.claude/index.json
├─ constraints/auth-flow [type:constraint, scope:always]
├─ facts/jwt-retry-pattern [type:fact, scope:project]  ← NEW
├─ runs/run-001-abc123 [type:runlog, scope:session]
└─ runs/sweep-001 [type:analysis, scope:session]

Search:
  $ reef index --type runlog
  $ reef index --search "jwt" --type fact
```

### C. Lifecycle & Archival

Run notes follow standard lifecycle:

```
ACTIVE (new) → DONE (analyzed) → ARCHIVED (old)

.claude/runs/*.runlog.xml        [scope:session, status:done after sweep]
.claude/runs/sweep-*.analysis.xml [scope:session, archived after 14d]
.claude/archive/                  [old runs moved here]
```

### D. Snapshot & Rollback

Sweeps interact with snapshots:

```bash
# Before sweep, create snapshot
$ reef snapshot create "pre-sweep"

# Analyze and apply fixes
$ reef analyze runs --auto-fix

# Verify changes
$ reef snapshot diff pre-sweep

# If issues, rollback
$ reef snapshot restore pre-sweep
```

### E. Drift (Cross-Project)

Run notes enable cross-project learning (future):

```bash
# Global reef can accumulate signals from multiple projects
~/.claude/runs/

# Project-specific reefs contribute
/project-a/.claude/runs/
/project-b/.claude/runs/

# Sweep across federation
reef drift analyze --global
→ Surface patterns relevant to all projects
```

---

## Harness Improvement Pathway

### Safe Improvements (Auto-Apply)

```
Run Note Signal
    ↓
Aggregation (3+ votes)
    ↓
Proposal (confidence > 90%)
    ↓
Auto-Apply:
├─ Create fossil (no breaking change)
├─ Decompose noisy polip (signal sent first)
└─ Mark @obsolete (reversible)
    ↓
Measurement (compare metrics before/after)
```

### Risky Improvements (Manual Review)

```
Run Note Signal
    ↓
Aggregation (2+ votes)
    ↓
Proposal (confidence 50-90%)
    ↓
Human Review:
├─ Read proposal + evidence
├─ Approve or reject
└─ If approve:
    ├─ Enhance constraint text
    ├─ Rewrite decision record
    └─ Commit to repo
```

### Monitoring-Only (Data Collection)

```
Run Note Signal
    ↓
Aggregation (1-2 votes, unclear trend)
    ↓
Proposal (confidence < 65%)
    ↓
Monitor for N weeks:
├─ Track pattern recurrence
├─ Collect more votes
└─ Escalate to risky/safe if clear
```

---

## Quality Metrics

### Harness Health Dashboard (in `reef reef`)

```
Reef Health: my-project
=====================

Population: 47 polips (~12,000 tokens)
  constraint: 3  thread: 8  decision: 4  context: 1  fact: 31

Surfacing Accuracy:      88%  ↑ (was 82%, +6 points)
  - Relevant polips:     76%
  - Irrelevant (noise):  12%
  - Missed (not surfaced): 12%

Context Quality:
  - Avg tokens per run:  2100
  - Token budget:        3000
  - Efficiency:          70%

Learning Loop:
  - Run notes:           23 (last 7 days)
  - Sweeps executed:     2
  - Improvements applied: 6
  - Last sweep:          2026-01-15T16:00:00Z

Suggestions:
  -> Sweep has 10+ notes pending analysis
  -> Try: reef analyze runs --dry-run
```

---

## Edge Cases & Safeguards

### 1. Conflicting Signals

```
Signal A (3 votes): Archive thread/oauth
Signal B (2 votes): Enhance thread/oauth

Resolution:
- A wins (higher confidence)
- B logged as "monitoring" for future
- User notified of conflict
```

### 2. Failing Proposals

```
Proposal: Create fossil
Failure: Directory traversal attempt detected

Handling:
- Proposal rejected
- Error logged
- Run note marked with issue
- User alerted (stderr)
```

### 3. Divergence from Config

```
Config says: "Always surface constraint/auth"
Run note says: "Auth constraint was noise"

Resolution:
- Proposal suppressed (config > reef)
- Issue logged
- User reviews manually
```

### 4. Stale Run Notes

```
.claude/runs/run-2025-10-01-abc123.runlog.xml

Age: 100 days
Scope: SESSION
Status: DONE

Cleanup: `reef cleanup` archives notes >14 days old
Aggregation: Sweep ignores archived notes
```

---

## Performance Impact

### Per-Session Cost

```
Stop hook execution:
  ├─ reef hook persist:      ~100ms (context polip)
  ├─ reef run-note create:   ~50ms (write RUNLOG)
  └─ Total:                  ~150ms (acceptable)

Storage:
  ├─ Per run note:           ~5KB (XML + metadata)
  ├─ 100 runs/week:          ~500KB
  └─ Total (.claude/runs/):  ~2MB (negligible)
```

### Sweep Cost

```
10 run notes:
  ├─ Load & parse:   ~50ms
  ├─ Aggregate:      ~20ms
  ├─ Generate:       ~30ms
  └─ Total:          ~100ms (acceptable, manual trigger)
```

### Index & Search

```
Run notes indexed alongside polips:
  ├─ Size impact:    +10% (1-2MB total)
  ├─ Search impact:  Negligible (indexed)
  └─ Surface impact: No change (run notes not normally surfaced)
```

---

## Rollout Plan

### Phase 1 (Week 1): MVP
- [x] Design schema (this document)
- [ ] Implement core: BlobType.RUNLOG, create_run_note(), basic CLI
- [ ] Test: Unit tests, manual end-to-end
- [ ] Deploy: New `reef run-note` command

### Phase 2 (Week 2-3): Sweep Analysis
- [ ] Implement: Signal aggregation, proposal generation
- [ ] Test: Multi-run aggregation, dry-run mode
- [ ] Feature: `reef analyze runs --dry-run`
- [ ] Documentation: User guide

### Phase 3 (Week 3-4): Auto-Apply
- [ ] Implement: Safe fix application, snapshot integration
- [ ] Test: Rollback scenarios, conflict detection
- [ ] Feature: `reef analyze runs --auto-fix`
- [ ] Monitoring: Track improvement metrics

### Phase 4 (Ongoing): Refinement
- [ ] Threshold triggers (auto-sweep at 10+ notes)
- [ ] Metrics dashboard integration
- [ ] Cross-project drift analysis
- [ ] Performance optimization

---

## Success Criteria

After Phase 1 rollout, measure:

- [x] Run notes created successfully in 100% of sessions
- [ ] Sweep identifies valid patterns (>80% precision)
- [ ] Auto-apply fixes cause no regressions (verified via snapshot)
- [ ] Surfacing accuracy improves by ≥5% within 2 weeks
- [ ] Agent usability unchanged (zero complaints)

---

*This design integrates seamlessly with existing reef architecture.*
*No breaking changes to CLI, polip format, or harness behavior.*
