# Agent Run Notes: User Guide

**Date:** 2026-01-15
**Audience:** Developers using reef harness
**Goal:** Practical examples of the feedback loop in action

---

## How It Works (From User Perspective)

### Automatic (Nothing to Do)

```bash
$ # Start a task (e.g., "debug JWT timeout")
$ # Claude Code session opens

# ... work on task, receive surfaced polips ...

$ # End session (stop hook runs automatically)

# Behind the scenes:
# 1. reef hook persist        → Creates context polip
# 2. reef run-note create     → Writes observations from transcript
#
# You see: (optional confirmation message)
#   "Run note created: .claude/runs/run-20260115-run-001.runlog.xml"
```

### Optional Workflow: Provide Rich Observations

If you want to add detailed observations (instead of auto-extraction):

```bash
$ reef run-note create \
    --task-type "bugfix" \
    --task-summary "Fix JWT timeout in token refresh" \
    --works "Constraint on token expiry was spot-on" \
    --missing "No example of retry-with-backoff pattern" \
    --noise "OAuth integration thread kept appearing, not relevant" \
    --blockers "Had to search git history for retry pattern"

Run note created: .claude/runs/run-20260115-abc123.runlog.xml
```

---

## Reviewing What Happened

### Check Individual Run Notes

```bash
$ # View your most recent run note
$ reef index --type runlog | head -1

  runs/run-20260115-153000 [runlog] [session]
    Task: Fix JWT timeout (session-abc123)

$ # Read it
$ reef surface runs/run-20260115-153000

  Summary: Task: Fix JWT timeout (session-abc123)
  Status:  ACTIVE
  Updated: 2026-01-15

  Metadata:
    Session: abc123
    Run #:   1
    Task:    bugfix
    Status:  completed (2 minutes)

  Observations:
    ✓ Works:
      - Constraint on token expiry was directly applicable
      - Decision record on error handling shortened debug by 50%

    ✗ Missing:
      - JWT refresh retry pattern with exponential backoff
      - Example of handling 401 on expired session

    ⚠ Noise:
      - OAuth integration thread (3 times, never relevant)

    ⛔ Blockers:
      - Had to manually search git for retry pattern (15 min)

  Signals (Improvement Suggestions):
    → Create fossil: "JWT Exponential Backoff Pattern"
    → Enhance: constraints/auth-flow (clarify 401 handling)
    → Archive: threads/oauth-integration (consistently irrelevant)
```

### Check Run Note Statistics

```bash
$ reef reef

Reef Health: my-project
=====================

... (other stats) ...

Learning Loop:
  Run notes:           8 (last 7 days)
  Sweeps executed:     1
  Improvements applied: 3
  Last sweep:          2026-01-15T16:00:00Z

Suggestions:
  -> 8 run notes accumulated; try: reef analyze runs
```

---

## Analyzing Accumulated Observations

### See What Proposals Exist (Dry-Run)

```bash
$ reef analyze runs --since 1d --dry-run

Analyzing run notes (since 1d):
  Found: 8 run notes

Aggregated Signals:
  ┌─ CREATE (New fossils needed) ──────────────────┐
  │ JWT Exponential Backoff Pattern                │
  │   6/8 agents needed this                        │
  │   confidence: 0.95                             │
  │   suggestion: Create fact fossil               │
  │                                                 │
  │ Timeout Resilience Patterns                    │
  │   4/8 agents struggled with timeouts           │
  │   confidence: 0.78                             │
  │   suggestion: Monitor (collect more data)      │
  └────────────────────────────────────────────────┘

  ┌─ ENHANCE (Improve clarity) ────────────────────┐
  │ constraints/auth-flow                          │
  │   5/8 agents asked for 401 refresh example     │
  │   confidence: 0.68                             │
  │   suggestion: Add example to constraint        │
  └────────────────────────────────────────────────┘

  ┌─ ARCHIVE (Remove noise) ──────────────────────┐
  │ threads/oauth-integration                      │
  │   7/8 agents found it irrelevant               │
  │   confidence: 0.92                             │
  │   suggestion: Decompose (archive)              │
  └──────────────────────────────────────────────────┘

  ┌─ TUNE (Parameter adjustments) ─────────────────┐
  │ tfidf_threshold                                │
  │   3/8 agents felt context too noisy           │
  │   confidence: 0.55                             │
  │   suggestion: Monitor for 2 more weeks         │
  └──────────────────────────────────────────────────┘

Priorities:
  1. [SAFE] Create "JWT Pattern" fossil (high confidence)
  2. [SAFE] Archive "OAuth Thread" (high confidence)
  3. [REVIEW] Enhance auth-flow constraint (human needed)
  4. [MONITOR] Track tfidf noise (collect more votes)

What would happen with --auto-fix:
  ✓ Would create: facts/jwt-exponential-backoff.fact.xml
  ✓ Would archive: threads/oauth-integration
  → Would log proposal: Enhance constraints/auth-flow
  → Would note: Monitor tfidf_threshold for 2 weeks

Revert via: reef snapshot restore pre-sweep
```

### Apply Safe Fixes

```bash
$ # First, create a snapshot (safety)
$ reef snapshot create "before-sweep"

Snapshot created: .claude/snapshots/20260115-151300-before-sweep.snapshot.json
  8 polip(s) captured

$ # Apply auto-fix proposals
$ reef analyze runs --since 1d --auto-fix

Applying proposals...
  ✓ Created: facts/jwt-exponential-backoff.fact.xml
    (Summary: "JWT exponential backoff retry pattern")
    (Based on 6/8 agent signals)

  ✓ Archived: threads/oauth-integration
    (Reason: Consistently false-positive in surfacing)

Proposals requiring review:
  → constraints/auth-flow (5 agents suggest enhancement)
    Review: reef surface constraints/auth-flow
    Edit:   vi .claude/constraints/auth-flow.blob.xml
    Then:   reef status auth-flow done

  → Monitor: tfidf_threshold (3 agents reported noise)
    Current: 0.30
    Suggested: 0.25 (reduce threshold = more results)
    Next review: 2026-01-29

Analysis complete:
  .claude/runs/sweep-20260115-151456.analysis.xml

Summary:
  - 2 safe fixes applied
  - 1 proposal needs review
  - 1 metric under monitoring
  - Metrics improvement: accuracy 82% → 88%

Run next session to see improved context injection!
```

### Review Proposals Manually

```bash
$ # Show the analysis polip with all proposals
$ reef surface runs/sweep-20260115-151456

Sweep Analysis: 8 run notes
=========================

  Proposals by Type:
  ──────────────────

  [APPLIED] Create Fossil (JWT Pattern)
    Status: ✓ Created
    Confidence: 95%
    Evidence: 6/8 agents
    Description: Exponential backoff pattern for JWT refresh
    Related: constraints/auth-flow, constraints/resilience

  [APPLIED] Decompose (oauth-integration)
    Status: ✓ Archived
    Confidence: 92%
    Evidence: 7/8 agents marked irrelevant
    Related: constraints/oauth-rules (blocked by)

  [PENDING] Enhance Constraint
    Status: ⚠ Awaiting review
    Target: constraints/auth-flow
    Issue: Ambiguity around 401 handling in token refresh
    Suggestion: Add example for "401 → refresh → retry" flow
    Evidence: 5/8 agents asked for clarification

  [MONITORING] Parameter Tuning
    Status: 📊 Tracking
    Parameter: tfidf_threshold
    Suggestion: Reduce from 0.30 to 0.25
    Rationale: May surface more marginal-but-useful matches
    Evidence: 3/8 agents reported noise
    Review date: 2026-01-29 (after 2 weeks)

  Metrics:
  ────────
    Accuracy:     0.82 → 0.88 (+6%)
    False +ve:    14% → 12% (-2%)
    Missed refs:  12% → 10% (-2%)
    Avg duration: 2.2min → 1.8min (-18% context overhead)

  Recommendations (priority order):
    1. Review & apply auth-flow enhancement
    2. Monitor tfidf_threshold; escalate if pattern continues
    3. Consider surfacing JWT pattern in tutorials
```

### Manually Handle Proposals

```bash
$ # OPTION 1: Accept enhancement proposal
$ reef surface constraints/auth-flow

[View existing constraint]

$ vi .claude/constraints/auth-flow.blob.xml

[Add example for 401 handling in token refresh]

[Save & exit]

$ reef status auth-flow done

constraints/auth-flow: active → done


$ # OPTION 2: Reject enhancement proposal
$ # (Just don't apply it; proposal documented in analysis polip)

$ # OPTION 3: Monitor parameter proposal
$ # (Nothing to do; .claude/runs.json will log observation)
$ # (Revisit on 2026-01-29)
```

---

## Complete Example: Week in the Life

### Monday

```bash
$ # Start 3 agent sessions
$ # Agent 1: Fix authentication timeout
$ # Agent 2: Implement OAuth integration
$ # Agent 3: Debug token refresh race condition

# Each session's stop hook:
# → Creates context polip
# → Writes run note with observations

# Result: 3 run notes in .claude/runs/
```

### Friday (Accumulated Signals)

```bash
$ # Over the week:
# Agent 4, 5, 6: Similar tasks, similar observations
# Total: 8 run notes in .claude/runs/

$ reef analyze runs --dry-run

Finding patterns...

STRONG SIGNAL: JWT retry pattern missing (6/8 agents)
STRONG SIGNAL: OAuth thread is noise (7/8 agents)
MEDIUM SIGNAL: auth-flow constraint unclear (5/8 agents)

Recommendations:
  1. Create JWT pattern fossil (safe, 95% confidence)
  2. Archive oauth thread (safe, 92% confidence)
  3. Enhance auth-flow (risky, 68% confidence, needs review)

$ # Take a look first
$ reef snapshot create "pre-sweep"

$ reef analyze runs --auto-fix

✓ Created JWT pattern fossil
✓ Archived oauth thread
→ Logged: Review auth-flow constraint enhancement

Next Monday: Improved context!
```

### Monday Next Week

```bash
$ # Agent 7: New auth task

# Surfaced context now includes:
# - constraints/auth-flow (updated with examples)
# - facts/jwt-exponential-backoff (NEW)
# - constraints/resilience
# (NOT: threads/oauth-integration — archived)

# Run completes faster (no manual searching)

# Run note observations:
#   ✓ Works: JWT pattern was directly applicable
#   ✓ Works: auth-flow examples clarified edge case
#   ✗ Missing: (none reported)
#   ⚠ Noise: (minimal)

# Signal: "This sweep helped! Better context this week."

# Metrics improve further: 88% → 91%
```

---

## Common Questions

### "How do I tell the harness what I learned?"

**Manual approach:**
```bash
$ reef run-note create \
    --task-summary "Implemented JWT timeout handling" \
    --works "Constraint doc was accurate" \
    --missing "No example of retry-with-jitter" \
    --blockers "Had to search code for pattern"
```

**Automatic approach:**
Just use the harness normally. Stop hook extracts observations from your work.

### "Can I see what observations will be extracted?"

Yes, in the run note:
```bash
$ reef surface runs/run-20260115-abc123
```

### "What if the auto-fix creates a bad fossil?"

Revert via snapshot:
```bash
$ reef snapshot diff pre-sweep
(See what changed)

$ reef snapshot restore pre-sweep
(Roll back all changes)
```

### "How often should I sweep?"

- **Manual:** When you've accumulated a few sessions and want feedback
- **Scheduled:** Weekly (via cron) for continuous improvement
- **Threshold:** Auto-trigger when 10+ notes or 3+ repeated errors

### "Can I disable auto-fixes?"

Yes. Always use `--dry-run` first to preview:
```bash
$ reef analyze runs --dry-run  # See proposals
$ reef analyze runs --auto-fix # Apply only if happy
```

Or just don't use `--auto-fix`:
```bash
$ reef analyze runs  # Shows proposals, no changes
```

### "What if I disagree with a proposal?"

Document it! Add to next run note:
```bash
$ reef run-note create \
    --signal "archive/oauth-integration is WRONG — still need it for federated auth" \
    --context "Previous proposal to archive oauth was premature; new project needs it"
```

**Signal is weighted equally.** If next few runs also say "keep oauth", proposal will flip.

### "Can I run this across projects?"

Not yet! Phase 4. Today: per-project only.

But you *can* manually pull useful fossils:
```bash
$ reef drift pull other-project/facts/jwt-pattern
```

---

## Command Reference

### Create/View Run Notes

```bash
# Auto-create (via stop hook)
(happens automatically)

# Manual create with observations
reef run-note create \
  --task-type "bugfix" \
  --task-summary "Fix JWT timeout" \
  --works "Item 1|Item 2" \
  --missing "Item 1|Item 2" \
  --noise "Item 1" \
  --blockers "Item 1"

# View individual note
reef surface runs/run-20260115-abc123

# List all run notes
reef index --type runlog

# Search run notes
reef index --search "jwt" --type runlog
```

### Analyze & Apply

```bash
# See what proposals exist (no changes)
reef analyze runs --since 1d --dry-run

# Apply safe fixes only
reef analyze runs --since 1d --auto-fix

# Show metrics trends
reef analyze metrics

# Create snapshot before sweep
reef snapshot create "pre-sweep"

# Compare before/after
reef snapshot diff pre-sweep

# Restore if needed
reef snapshot restore pre-sweep
```

### Configure

```bash
# View sweep triggers
cat .claude/runs.json

# Edit if needed
vi .claude/runs.json

# Triggers:
# - count: Run sweep when ≥10 notes accumulated
# - accuracy_threshold: Pause surfacing if <80%
# - error_repetition: Auto-sweep on 3+ same error
# - enabled: true/false to enable auto-triggers
```

---

## Checklist: First Time Using Run Notes

- [ ] Read AGENT-RUN-NOTES-OVERVIEW.md (architecture overview)
- [ ] Run a normal task (agent works, stop hook fires)
- [ ] Check that run note was created: `reef index --type runlog`
- [ ] Read it: `reef surface <runlog-key>`
- [ ] Accumulate 5-10 run notes over a few days
- [ ] Try dry-run: `reef analyze runs --dry-run`
- [ ] Create snapshot: `reef snapshot create "first-sweep"`
- [ ] Apply safe fixes: `reef analyze runs --auto-fix`
- [ ] Verify: `reef snapshot diff first-sweep`
- [ ] Next task: Observe improved context in surfacing
- [ ] Report experience!

---

## Troubleshooting

### Run notes not being created

**Symptom:** `.claude/runs/` is empty after sessions.

**Cause:** Stop hook not configured or failing.

**Fix:**
```bash
# Check settings
cat ~/.claude/settings.json | jq '.hooks.Stop'

# Should include: "reef run-note create"

# If missing, setup hook:
reef hook setup >> ~/.claude/settings.json
```

### Proposals seem wrong

**Symptom:** `reef analyze runs --dry-run` shows unexpected proposals.

**Cause:** Signal aggregation threshold too low, or run notes have incomplete observations.

**Fix:**
```bash
# Review individual notes
reef surface runs/run-20260115-abc123

# Check observations (are they detailed?)
# If too vague, future notes should be more specific

# Tweak thresholds in .claude/runs.json
# (increase "count" from 3 to 5 for higher confidence)
```

### Snapshot restore doesn't work

**Symptom:** `reef snapshot restore pre-sweep` says "snapshot not found".

**Cause:** Snapshot was pruned, or wrong name.

**Fix:**
```bash
# List snapshots
reef snapshot list

# Find the right one
reef snapshot diff 20260115-151300-before-sweep

# If not found, recreate reef from version control and re-apply manually
```

---

## Best Practices

1. **Be specific in observations**
   - ✓ "JWT retry pattern missing; had to search 15 min"
   - ✗ "Missing stuff"

2. **Separate signal types**
   - Use `--works`, `--missing`, `--noise`, `--blockers` appropriately
   - Don't mix in one field

3. **Snapshot before auto-fix**
   ```bash
   reef snapshot create "pre-sweep"
   reef analyze runs --auto-fix
   ```

4. **Review risky proposals**
   - Don't auto-apply parameter changes
   - Always human-review constraint modifications

5. **Accumulate before analyzing**
   - 1 run note = uncertain signal
   - 3+ identical = strong signal
   - Let patterns emerge over a week

6. **Monitor parameter suggestions**
   - Don't change tfidf_threshold on first proposal
   - Wait 2-3 weeks for consistent signal
   - Track metrics.json to verify improvement

---

*This guide updates as Phase 2 & 3 features land. Check back weekly.*

**Questions?** Review:
- `docs/agent-run-notes-design.md` (detailed design)
- `docs/runlog-technical-spec.md` (technical details)
- `docs/harness-integration.md` (architecture context)

