# Agent Run Notes Design

**Date:** 2026-01-15
**Status:** Detailed Design
**Purpose:** Close the learning loop: agents write observations → system learns → harness improves

---

## Pattern Overview

Agent Run Notes enables the reef to learn from agent behavior and automatically improve the harness. Instead of one-way injection of context into agents, this creates a feedback mechanism where agents document what worked, what failed, and what was missing — then systematic analysis triggers harness improvements.

### The Loop

```
Session Start
    ↓
Agent executes task (receives surface() context)
    ↓
Agent writes observations → run note (stop hook)
    ↓
Multiple runs accumulate notes
    ↓
Sweep analysis identifies patterns (scheduled or manual)
    ↓
System auto-generates harness improvements
    ↓
Next session: improved context injection
```

---

## Design Decisions

### 1. Where Do Run Notes Live?

**Decision: Hybrid polips (not just files)**

Run notes are stored as **context-scoped polips** (similar to session-context.blob.xml) in `.claude/runs/` with a special type: `BlobType.RUNLOG` (add to enum).

```
.claude/
├── runs/
│   ├── 2026-01-15-run-001-task-id.runlog.xml
│   ├── 2026-01-15-run-002-task-id.runlog.xml
│   └── 2026-01-15-sweep-analysis.analysis.xml
```

**Why polips?**
- Integrate with existing index/search infrastructure
- Inherit lifecycle (scope, status, archival)
- Enable wiki-linking to related constraints/decisions
- Access counts boost useful run notes (LRU)
- Progressive disclosure (L1 summary, L2 full content)

**Why separate directory?**
- Prevents contamination of active reef
- Clear policy: run notes are ephemeral (session scope)
- Easier to bulk-archive or prune
- Physical separation = psychological clarity

**Secondary storage:**
- Optional: `.claude/metrics.json` for aggregate statistics (cost, latency, success rate)
- Optional: `.claude/runs/manifest.json` for indexing by date, task type, status

---

### 2. What Triggers the Sweep?

**Decision: Three trigger modes (flexible)**

#### Mode 1: Manual Trigger (immediate feedback)
```bash
reef analyze runs              # Analyze all run notes since last sweep
reef analyze runs --since 2d   # Analyze last 2 days
reef analyze runs --session    # Analyze current session only
```

#### Mode 2: Scheduled Trigger (background learning)
```bash
reef cleanup --analyze         # Append --analyze to cleanup command
# Or: Add cron job to run weekly
0 0 * * 0 cd /project && reef analyze runs --auto-fix
```

#### Mode 3: Threshold Trigger (reactive)
When any of these conditions hit, auto-run sweep:
- **Count:** 10+ new run notes in `.claude/runs/`
- **Divergence:** Polip surfacing accuracy < 80% (tracked in metrics)
- **Pattern:** Same error appears 3+ times in notes

Configured in `.claude/runs.json`:
```json
{
  "sweep_triggers": {
    "count": 10,
    "accuracy_threshold": 0.80,
    "error_repetition": 3,
    "enabled": true
  }
}
```

---

### 3. Run Note Schema

**File format:** XML polip with extended structure

```xml
<blob type="runlog" scope="session" status="pending" updated="2026-01-15T14:32:00Z" v="2">
  <summary>Task: Fix authentication bug (session-id-abc123)</summary>

  <!-- Metadata -->
  <metadata>
    <session_id>abc123</session_id>
    <run_number>42</run_number>
    <task_type>bugfix</task_type>
    <start_time>2026-01-15T14:30:00Z</start_time>
    <end_time>2026-01-15T14:32:00Z</end_time>
    <duration_seconds>120</duration_seconds>
    <status>completed</status>  <!-- completed, failed, timeout, incomplete -->
  </metadata>

  <!-- Context Received -->
  <surfaced>
    <total_polips>5</total_polips>
    <total_tokens>2400</total_tokens>
    <polips>
      <polip key="constraints/auth-flow" rank="1" relevant="true">
        <reason>Exact match for "authentication"</reason>
      </polip>
      <polip key="threads/oauth-integration" rank="2" relevant="false">
        <reason>Mentioned OAuth, but irrelevant to JWT bug</reason>
      </polip>
    </polips>
  </surfaced>

  <!-- Observations -->
  <observations>
    <works>
      <item weight="high">Constraint about token expiry was directly applicable</item>
      <item weight="high">Decision record on error handling patterns shortened debug time by 50%</item>
    </works>
    <missing>
      <item weight="high">No example of JWT refresh retry logic in repo</item>
      <item weight="medium">No record of previous timeout issue in similar code path</item>
    </missing>
    <noise>
      <item weight="high">OAuth integration thread was surfaced but unhelpful (false positive)</item>
      <item weight="medium">3 old archived decision records cluttered the context</item>
    </noise>
    <blockers>
      <item type="context">Needed to manually search git history for retry pattern</item>
      <item type="clarity">Constraint text was ambiguous about edge case</item>
    </blockers>
  </observations>

  <!-- Signals for Improvement -->
  <signals>
    <!-- Suggest new polip -->
    <create type="fact">
      <summary>JWT refresh retry pattern (exponential backoff)</summary>
      <suggestion>This pattern keeps getting rediscovered; should be a fossil</suggestion>
    </create>

    <!-- Suggest constraint improvement -->
    <enhance polip="constraints/auth-flow">
      <note>Add example for timeout handling in token refresh</note>
    </enhance>

    <!-- Suggest new decision -->
    <archive polip="threads/oauth-integration">
      <reason>Consistently irrelevant to JWT work; move to fossils</reason>
    </archive>

    <!-- Suggest surfacing parameter change -->
    <tune>
      <parameter name="tfidf_threshold">Reduce from 0.3 to 0.2 to surface fewer marginal matches</parameter>
      <parameter name="max_token_budget">Cap at 2000 instead of 3000 to reduce noise</parameter>
    </tune>
  </signals>

  <!-- Context -->
  <context>Task: Debug JWT authentication failures in new service.

Started with 5 surfaced polips. Constraints were accurate but noisy.
Found the answer in old commit message instead of reef.

If constraint had example of refresh retry + edge cases,
would have saved 15 minutes of manual search.</context>

  <!-- Related -->
  <related>
    <ref>constraints/auth-flow</ref>
    <ref>threads/oauth-integration</ref>
  </related>
</blob>
```

**Key fields:**

| Section | Purpose |
|---------|---------|
| **metadata** | Machine-readable session info, timestamps, status |
| **surfaced** | What polips were injected? Were they used? |
| **observations** | Agent's qualitative assessment (works, missing, noise, blockers) |
| **signals** | Actionable recommendations (create, enhance, archive, tune) |
| **context** | Free-form notes from the agent |

---

### 4. Sweep Analysis & Auto-Generation

**Process:**

```
Read all run notes in .claude/runs/
    ↓
Extract signals (creates, enhancements, archives, tunes)
    ↓
Aggregate by type and confidence
    ↓
Detect patterns (3+ similar signals = strong signal)
    ↓
Generate proposals (new polips, modifications, config changes)
    ↓
Write to .claude/runs/sweep-report.analysis.xml
    ↓
(Optional) Auto-apply safe fixes
    ↓
(With --dry-run) Print recommendations for review
```

#### Sweep Output: Analysis Polip

```xml
<blob type="analysis" scope="session" status="completed" updated="2026-01-15T16:00:00Z">
  <summary>Sweep analysis: 42 run notes (2026-01-15)</summary>

  <metadata>
    <run_notes_analyzed>42</run_notes_analyzed>
    <session_start>2026-01-14T08:00:00Z</session_start>
    <session_end>2026-01-15T16:00:00Z</session_end>
    <total_runs_hours>32</total_runs_hours>
    <avg_success_rate>0.88</avg_success_rate>
    <sweep_mode>manual</sweep_mode>  <!-- manual, scheduled, threshold -->
  </metadata>

  <proposals>
    <!-- Type 1: Create new fossils (high confidence) -->
    <proposal type="create_polip" confidence="0.95" count="7">
      <summary>JWT refresh retry pattern appears in 7/42 notes as missing</summary>
      <polip_type>fact</polip_type>
      <title>JWT Exponential Backoff Retry Pattern</title>
      <content_hint>Retry with base=100ms, cap=30s, jitter=±10%</content_hint>
      <related>constraints/auth-flow, constraints/resilience</related>
      <auto_apply>true</auto_apply>
    </proposal>

    <!-- Type 2: Enhance constraint clarity (medium confidence) -->
    <proposal type="enhance_polip" confidence="0.82" count="5">
      <polip_key>constraints/auth-flow</polip_key>
      <issue>Edge case ambiguity around token refresh on expired session</issue>
      <suggested_change>Add clarifying example for 401 → refresh → retry flow</suggested_change>
      <related_notes>5 agents asked for clarification</related_notes>
      <auto_apply>false</auto_apply>  <!-- Requires human review -->
    </proposal>

    <!-- Type 3: Remove noise polips (high confidence) -->
    <proposal type="decompose_polip" confidence="0.91" count="4">
      <polip_key>threads/oauth-integration</polip_key>
      <issue>False positive: OAuth thread surfaced 4/42 times but marked irrelevant</issue>
      <recommendation>Move to fossils (archive) or link with blocker relationship</recommendation>
      <auto_apply>true</auto_apply>
    </proposal>

    <!-- Type 4: Tune injection parameters (low confidence, monitor) -->
    <proposal type="tune_parameter" confidence="0.65" count="3">
      <parameter>tfidf_threshold</parameter>
      <current_value>0.3</current_value>
      <suggested_value>0.25</suggested_value>
      <rationale>Reducing threshold would surface 2-3 more highly relevant edges per run</rationale>
      <estimated_improvement>+0.05 accuracy (subject to validation)</estimated_improvement>
      <auto_apply>false</auto_apply>  <!-- Parameter changes need monitoring -->
    </proposal>
  </proposals>

  <!-- Metrics -->
  <metrics>
    <accuracy>
      <surfaced_relevant_pct>0.76</surfaced_relevant_pct>
      <surfaced_irrelevant_pct>0.12</surfaced_irrelevant_pct>
      <missed_polips>0.12</missed_polips>
      <notes>12% of needed context was not in reef (user had to search manually)</notes>
    </accuracy>
    <latency>
      <avg_surface_time_ms>45</avg_surface_time_ms>
      <p95_surface_time_ms>120</p95_surface_time_ms>
      <impact>Acceptable; no bottleneck</impact>
    </latency>
    <token_efficiency>
      <avg_tokens_per_run>2100</avg_tokens_per_run>
      <max_budget>3000</max_budget>
      <utilization_pct>70</utilization_pct>
    </token_efficiency>
  </metrics>

  <!-- Recommendations (prioritized) -->
  <recommendations>
    <action priority="1">
      Create fact fossil for JWT retry pattern
      (7 agents needed it; currently missing from reef)
    </action>
    <action priority="2">
      Review & enhance constraints/auth-flow for clarity
      (5 agents asked for clarification on edge cases)
    </action>
    <action priority="3">
      Decompose threads/oauth-integration (consistently irrelevant false positive)
    </action>
    <action priority="4">
      Monitor tfidf_threshold parameter; if patterns continue, reduce to 0.25
    </action>
  </recommendations>

  <context>This sweep shows healthy overall accuracy (88% success rate).
Main gaps are clarity in constraints and missing tactical patterns.
Recommend prioritizing proposals 1-2; defer parameter tuning until next week.</context>
</blob>
```

---

### 5. Integration Points

#### A. Stop Hook (Agent Writes Run Note)

```python
# In Claude Code stop hook
def on_stop(context: StopContext):
    """Create run note at session end."""
    from reef.blob import Glob, Blob, BlobType, BlobScope
    from pathlib import Path

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    # Build observations from transcript analysis
    run_note = Blob(
        type=BlobType.RUNLOG,
        scope=BlobScope.SESSION,
        summary=f"Task: {context.task_summary} (session-{context.session_id})",
        # ... fill in metadata, observations, signals
    )

    # Write with timestamp in name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    glob.sprout(run_note, f"run-{timestamp}-{context.session_id}", subdir="runs")
```

#### B. Manual Analysis Command

```bash
# New CLI command
reef analyze runs [--since <time>] [--auto-fix] [--dry-run]
```

Implementation in `cli.py`:
- Scan `.claude/runs/*.runlog.xml`
- Parse proposals from each
- Aggregate by type
- Generate sweep report
- Apply safe fixes if `--auto-fix` flag
- Write summary to stdout

#### C. Metrics Tracking (Optional Enhancement)

```json
{
  "metrics": {
    "surfacing_accuracy": {
      "2026-01-14": 0.82,
      "2026-01-15": 0.88
    },
    "avg_latency_ms": {
      "2026-01-14": 42,
      "2026-01-15": 45
    },
    "token_efficiency": {
      "avg_per_run": 2100,
      "max_budget": 3000
    },
    "last_sweep": "2026-01-15T16:00:00Z"
  }
}
```

#### D. Auto-Generation (Future Phase)

Using reef's own context, auto-generate polip content from proposals:

```python
def auto_generate_fossil(proposal: dict) -> str:
    """Generate polip content based on proposal hints + related polips."""
    # Get related polips for context
    # Use LLM (Claude) to draft content
    # Format as markdown with references
    # Return draft for human review or auto-commit
```

---

## Implementation Plan

### Phase 1: Core (MVP)
- [ ] Add `BlobType.RUNLOG` to enum
- [ ] Add `.claude/runs/` directory structure
- [ ] Define runlog XML schema
- [ ] Update `cli.py` with `reef analyze runs` command
- [ ] Update stop hook template to write run notes
- [ ] Basic signal extraction (works, missing, noise, blockers)

### Phase 2: Analysis & Reporting
- [ ] Aggregate signals from multiple run notes
- [ ] Detect patterns (3+ occurrences = strong signal)
- [ ] Generate analysis polip with proposals
- [ ] Implement `--dry-run` mode
- [ ] Human-readable summary output

### Phase 3: Auto-Application
- [ ] Safe auto-fixes: create fossils, decompose noisy polips
- [ ] Optional auto-parameter tuning with monitoring
- [ ] Threshold triggers in `.claude/runs.json`
- [ ] Scheduled sweep support

### Phase 4: Metrics & Learning Loop
- [ ] Track surfacing accuracy over time
- [ ] Compute token efficiency per session
- [ ] Build recommendation engine (prioritize proposals)
- [ ] Visualize trends in `reef reef` output

---

## Safe Fixes vs Risky Changes

**Safe (auto-apply by default):**
- ✓ Create new fact fossils from strong signals
- ✓ Decompose consistently false-positive polips
- ✓ Add `@obsolete` marker to deprecated polips
- ✓ Update `updated` timestamp on enhanced polips

**Risky (require review):**
- ✗ Modify constraint text (could break hard requirements)
- ✗ Change core tfidf/injection parameters
- ✗ Delete polips (preserve in archive first)
- ✗ Major rewrites of decision records

**Monitoring-only (no auto-apply):**
- ? Parameter tuning recommendations (track improvement for N weeks)
- ? Constraint rewording suggestions
- ? Large refactorings of reef structure

---

## Example Workflow

### Session 1: Agent writes run note
```
Agent debugging JWT timeout
→ Surfaces: auth-flow constraint, oauth-integration thread, timeout-patterns fact
→ Needed: Refresh retry pattern (missing)
→ Stop hook: writes run note with signal "create_fact: JWT retry pattern"
```

### Session 2-7: More runs accumulate
```
Sessions 2-7: Similar signal appears 5 more times
→ Run notes accumulate in .claude/runs/
```

### Manual Sweep (Day 2)
```bash
$ reef analyze runs
Analyzing 7 run notes...
  ✓ Signal: Create JWT retry pattern (confidence 95%, 6/7 notes)
  ✓ Signal: Clarify auth-flow constraint (confidence 82%, 5/7 notes)
  ✓ Signal: Decompose oauth-integration (confidence 91%, 4/7 notes)

Recommendations (in priority order):
  1. Create fact fossil "JWT Exponential Backoff Retry Pattern"
  2. Enhance constraint/auth-flow with refresh edge case example
  3. Decompose thread/oauth-integration

Apply with: reef analyze runs --auto-fix
```

### Auto-Apply
```bash
$ reef analyze runs --auto-fix
  ✓ Created: fossils/jwt-retry-pattern.fact.xml
  ✓ Enhanced: constraints/auth-flow (added 50 words on refresh)
  ✓ Decomposed: threads/oauth-integration → archives/

Next session: Better context injection (retry pattern + clearer constraint).
```

---

## Risk Mitigation

1. **Snapshots:** Before sweep with `--auto-fix`, create snapshot
   ```bash
   reef snapshot create "pre-sweep"
   reef analyze runs --auto-fix
   ```

2. **Dry-run first:**
   ```bash
   reef analyze runs --dry-run  # See what would happen
   reef analyze runs --auto-fix # Apply
   ```

3. **Conservative defaults:** Only auto-apply high-confidence (>90%) safe operations

4. **Rollback via snapshot:**
   ```bash
   reef snapshot diff pre-sweep
   reef snapshot restore pre-sweep
   ```

5. **Human-in-loop:** Risky proposals printed to stdout; require explicit `--dangerous` flag

---

## Backward Compatibility

- Existing polips unaffected (runlog is new type)
- Existing CLI unchanged (new `analyze` subcommand)
- `.claude/runs/` is new directory (no interference)
- Schema version preserved (can migrate later)

---

## Open Questions

1. **Who writes run notes?** Human (optional, structured form)? Claude (hook)? Both?
   - **Answer:** Both. Claude writes automatically. Humans can enrich via `reef run-note add`.

2. **How long to keep run notes?** Lifecycle?
   - **Answer:** Session scope (7-day default). Auto-archive to fossils if useful signal found.

3. **How accurate must signals be before auto-apply?**
   - **Answer:** >90% confidence + safe operation type = auto-apply. Monitor others.

4. **Can signals conflict?** (e.g., "enhance auth-flow" vs "decompose auth-flow")
   - **Answer:** Highest-confidence proposal wins. Log conflict for human review.

5. **Integration with MCP/drift?** Should remote agents contribute run notes?
   - **Answer:** Future phase. Start with local reef only.

---

## Success Metrics

After 20+ sessions with run notes:

- [ ] Surfacing accuracy improves from 0.82 → 0.90+
- [ ] Missed polips decrease from 12% → <5%
- [ ] No false positives from auto-apply (monitor via snapshots)
- [ ] 50% of new fossils created via run note signals
- [ ] Agent feedback loop demonstrates learning

---

## References

- `/Users/nolan/Desktop/reef/CLAUDE.md` — Reef architecture
- `/Users/nolan/Desktop/reef/docs/plans/2026-01-15-reef-native-infrastructure-design.md` — Reef infrastructure vision
- `reef blob.py` — BlobType, Glob API
- `reef cli.py` — CLI structure for extension

---

*Design authored 2026-01-15. Will evolve with Phase 1 implementation.*
