# Agent Run Notes: Design Deliverables

**Date:** 2026-01-15
**Status:** Complete (Ready for Implementation)
**Architect:** Nolan + Claude

---

## Overview

Complete design for **Agent Run Notes** — a feedback mechanism enabling the reef to learn from agent execution and automatically improve context injection.

### The Pattern

```
Session N: Agent executes → Context injected (surface)
              ↓ (stop hook)
          Observations written → Run note created
              ↓ (accumulated)
Session N+k: Sweep triggered
              ↓
          Signals analyzed → Proposals generated
              ↓
          Safe fixes applied → Reef improved
              ↓
Session N+k+1: Agent executes → Better context injected
```

---

## Deliverables

### 1. **AGENT-RUN-NOTES-OVERVIEW.md** (THIS DIRECTORY)
   **Purpose:** Quick reference for the full pattern
   **Audience:** Architects, decision-makers
   **Content:**
   - What problem it solves
   - Architecture at a glance
   - Key design decisions (table)
   - Three example workflows
   - Success metrics
   - Implementation timeline
   - FAQ

   **Use it for:** Understanding the big picture before diving into details

---

### 2. **docs/agent-run-notes-design.md**
   **Purpose:** Detailed architectural design
   **Audience:** Architects, tech leads
   **Content:**
   - Pattern overview with diagram
   - 5 major design decisions:
     1. Where run notes live (polips in .claude/runs/)
     2. What triggers sweep (3 modes: manual, scheduled, threshold)
     3. Run note schema (XML structure with fields)
     4. Sweep analysis & auto-generation (process + output)
     5. Integration points (existing components)
   - Safe vs. risky changes
   - Phase-based implementation plan (4 phases)
   - Risk mitigation strategies
   - Open questions

   **Use it for:** Making technical decisions, understanding constraints

---

### 3. **docs/runlog-technical-spec.md**
   **Purpose:** Implementation specification
   **Audience:** Developers, implementers
   **Content:**
   - Schema changes (BlobType extension, new fields)
   - Directory structure (.claude/runs/ layout)
   - CLI extension (new `reef analyze` command)
   - Core Glob methods (8 methods with signatures):
     - create_run_note()
     - load_runs_config()
     - analyze_runs()
     - _aggregate_signals()
     - _generate_proposals()
     - _apply_safe_fixes()
     - _compute_sweep_metrics()
     - _create_analysis_polip()
   - Hook integration
   - Testing checklist
   - Version compatibility
   - Error handling
   - Performance considerations
   - Security & validation

   **Use it for:** Coding, testing, implementation planning

---

### 4. **docs/harness-integration.md**
   **Purpose:** Integration with existing harness architecture
   **Audience:** Systems architects, integration leads
   **Content:**
   - Current architecture baseline
   - New components diagram
   - Data flow (per-session and multi-session)
   - Integration with 5 harness components:
     1. Polip management (CLI)
     2. Index & search
     3. Lifecycle & archival
     4. Snapshot & rollback
     5. Drift (cross-project)
   - Improvement pathway (safe, risky, monitoring-only)
   - Quality metrics (health dashboard example)
   - Edge cases & safeguards
   - Performance impact analysis
   - Rollout plan

   **Use it for:** System integration planning, stakeholder alignment

---

### 5. **docs/run-notes-user-guide.md**
   **Purpose:** Practical usage guide
   **Audience:** End users, developers
   **Content:**
   - How it works (automatic + optional)
   - Reviewing what happened (examples)
   - Analyzing accumulated observations
   - Complete workflow example (week in the life)
   - Common questions (11 Q&A)
   - Command reference (all commands)
   - Checklist for first-time use
   - Troubleshooting (4 common issues)
   - Best practices (6 guidelines)

   **Use it for:** Learning the system, solving problems

---

## Document Dependency Graph

```
AGENT-RUN-NOTES-OVERVIEW.md
        ↓ (learn more about)
        ├→ agent-run-notes-design.md
        │   ├→ runlog-technical-spec.md (how to code it)
        │   └→ harness-integration.md (where it fits)
        │
        └→ run-notes-user-guide.md (how to use it)
```

---

## Key Design Decisions (One-Pagers)

### 1. Where Do Run Notes Live?
- **Decision:** `.claude/runs/` as polips (BlobType.RUNLOG)
- **Why:** Integrate with index/lifecycle, separate from active reef, inherit all polip features
- **Alternative considered:** Plain JSON files → Rejected (no lifecycle, no indexing)

### 2. What Triggers Sweep?
- **Decision:** Three modes (manual, scheduled, threshold)
- **Why:** Flexibility; manual for immediate feedback, scheduled for automation, threshold for reactive learning
- **Configuration:** `.claude/runs.json` with trigger parameters

### 3. Run Note Schema
- **Decision:** XML with metadata + observations + signals (extends Blob)
- **Why:** Same format as other polips, extensible, compatible with existing infrastructure
- **Schema version:** BLOB_VERSION 2 → 3 (add RUNLOG fields)

### 4. Sweep Analysis Process
- **Decision:** Aggregate signals → Generate proposals → Apply safe fixes (risky need review)
- **Why:** Conservative (3+ agreement = strong signal), safe by default, human-in-the-loop
- **Confidence thresholds:** >90% auto-apply, 50-90% human review, <65% monitoring-only

### 5. Integration Points
- **Decision:** Extend existing components (no breaking changes)
- **Why:** Backward compatibility, easier adoption, reuses proven patterns
- **Impact:** New CLI subcommand, new BlobType, same hook interface

---

## File Changes Summary

### New Files (This Design)
```
docs/agent-run-notes-design.md              (3200 lines, detailed design)
docs/runlog-technical-spec.md               (1800 lines, implementation spec)
docs/harness-integration.md                 (2100 lines, architecture integration)
docs/run-notes-user-guide.md                (1400 lines, user guide)
AGENT-RUN-NOTES-OVERVIEW.md                 (400 lines, this doc)
AGENT-RUN-NOTES-DELIVERABLES.md             (this file)
```

### Modified Files (Phase 1 Implementation)
```
src/reef/blob.py                (add BlobType.RUNLOG, ANALYSIS; extend Blob)
src/reef/cli.py                 (add cmd_analyze(), argument parser)
.claude/stop.hook.json          (add run-note creation hook)
Tests/                          (unit + integration tests for new features)
```

### No Changes Needed
```
Existing polip commands
Existing surface/injection logic
Index/search infrastructure
Lifecycle management
User-facing APIs
```

---

## Implementation Phases

### Phase 1 (Week 1): MVP
**Goal:** Agents can write observations
**Deliverables:**
- [x] Design complete (this document set)
- [ ] BlobType.RUNLOG + XML serialization
- [ ] create_run_note() method
- [ ] Basic CLI: `reef run-note create`
- [ ] Stop hook integration
- [ ] Unit tests
- [ ] Integration test (end-to-end run)

**Success Criterion:** Run notes created in every session

---

### Phase 2 (Week 2-3): Sweep Analysis
**Goal:** Humans can review proposals
**Deliverables:**
- [ ] Signal aggregation (_aggregate_signals)
- [ ] Proposal generation (_generate_proposals)
- [ ] CLI: `reef analyze runs --dry-run`
- [ ] Analysis polip creation
- [ ] Conflict detection
- [ ] Integration tests
- [ ] User guide draft

**Success Criterion:** Proposals accurate (>80% precision)

---

### Phase 3 (Week 3-4): Auto-Apply & Metrics
**Goal:** Automatic harness improvement
**Deliverables:**
- [ ] Safe fix application (_apply_safe_fixes)
- [ ] Snapshot integration
- [ ] CLI: `reef analyze runs --auto-fix`
- [ ] Metrics tracking (metrics.json)
- [ ] Trend visualization (in `reef reef` output)
- [ ] Rollout checklist
- [ ] Documentation finalized

**Success Criterion:** 0 regressions from auto-apply

---

### Phase 4+ (Ongoing): Refinement
- Scheduled sweeps (cron)
- Threshold triggers (auto-sweep at N notes)
- Cross-project drift analysis
- Performance optimization
- Dashboard integration

---

## Validation Checklist

### Architecture
- [x] Solves stated problem (closes OBSERVE → ANALYZE → ADAPT loop)
- [x] No breaking changes to existing harness
- [x] Clean integration points (extends without modifying)
- [x] Clear authority model (agents write, humans review risky changes)
- [x] Rollback capability (snapshots)

### Design
- [x] Run note schema well-defined (5 sections: metadata, observations, signals, context, related)
- [x] Sweep logic defined (aggregate → generate → apply)
- [x] Safety mechanisms (snapshot before, dry-run first, safe/risky tracks)
- [x] Metrics for success (accuracy, noise, missed refs)
- [x] Error handling (don't fail on individual polips)

### Implementation
- [x] Technically feasible (builds on existing Blob/Glob infrastructure)
- [x] Effort estimated (4 weeks, 3-person-weeks)
- [x] Dependencies clear (none beyond stdlib)
- [x] Testing strategy defined (unit + integration + e2e)
- [x] Documentation complete (design + spec + guide)

### User Experience
- [x] Automatic (stop hook, no user action needed)
- [x] Optional richness (can provide detailed observations)
- [x] Understandable (clear what signals mean)
- [x] Discoverable (commands, help text)
- [x] Safe (dry-run, snapshot, slow-moving threshold triggers)

---

## Risk Assessment

### Low Risk
✓ New polip type (no impact on existing types)
✓ New CLI subcommand (no changes to existing commands)
✓ Stop hook extension (additive, runs after existing hooks)
✓ Auto-apply safe operations only (fossils, archival, metadata)

### Medium Risk
? Parameter tuning proposals (could affect accuracy)
  Mitigation: Monitor for 2 weeks before applying
  
? Constraint enhancement proposals (could break clarity)
  Mitigation: Human review required, test with snapshot

### Low-to-Mitigate Risk
✓ Accumulated run notes (storage)
  Mitigation: Auto-cleanup (.claude/runs.json, archive after 14d)

✓ Sweep analysis errors (proposal generation fails)
  Mitigation: Graceful degradation (log, continue, don't break harness)

---

## Success Metrics

After Phase 1 (2 weeks):
- [ ] 100% of sessions generate run notes
- [ ] No regressions in existing functionality
- [ ] Manual dry-run works end-to-end

After Phase 2 (4 weeks):
- [ ] Proposals generated correctly (>80% precision)
- [ ] Humans find proposals actionable (qualitative feedback)
- [ ] No false positives (manual review needed)

After Phase 3 (6 weeks):
- [ ] Auto-apply creates valid fossils (all surfaceable)
- [ ] Surfacing accuracy improves ≥5% (0.82 → 0.87+)
- [ ] Zero regressions from auto-apply (verified via snapshot)

---

## Stakeholders & Sign-Off

| Role | Name | Sign-Off | Date |
|------|------|----------|------|
| Architect | Nolan | [pending] | TBD |
| Tech Lead | [TBD] | [pending] | TBD |
| QA Lead | [TBD] | [pending] | TBD |

---

## Next Steps

1. **Review** (this week)
   - [ ] Team reads AGENT-RUN-NOTES-OVERVIEW.md
   - [ ] Stakeholders review agent-run-notes-design.md
   - [ ] Feedback compiled

2. **Refine** (if needed)
   - [ ] Address feedback
   - [ ] Adjust timelines/scope
   - [ ] Update documentation

3. **Kickoff** (Phase 1)
   - [ ] Assign implementation lead
   - [ ] Break down tasks
   - [ ] Create GitHub issues
   - [ ] Start coding

---

## Contact & Questions

For questions about:
- **Architecture** → See agent-run-notes-design.md
- **Implementation** → See runlog-technical-spec.md
- **Integration** → See harness-integration.md
- **Usage** → See run-notes-user-guide.md

---

**Design Status:** ✓ Complete and ready for implementation
**Last Updated:** 2026-01-15
**Author:** Architect (with Claude analysis)

