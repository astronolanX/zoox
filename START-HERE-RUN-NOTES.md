# Agent Run Notes Design — START HERE

**Date:** 2026-01-15  
**Status:** Complete, ready for implementation  
**Time to read overview:** 15 minutes  
**Time for detailed review:** 2-3 hours

---

## Quick Summary (2 minutes)

**Problem:** Reef injects context into agents, but has no feedback loop. If context is wrong, noisy, or incomplete, nobody learns.

**Solution:** Agents document observations (what worked, what was missing, what was noise) → System analyzes patterns → Harness improves automatically.

**Example:**
- Run 1: Agent says "JWT retry pattern missing"
- Run 2: Agent says "JWT retry pattern missing"
- Runs 3-6: Same observation
- Sweep triggered: "6/6 agents need JWT pattern" → Create new fossil fact
- Run 7: JWT pattern now surfaced → Task completes 15 minutes faster

---

## The Five Documents (Read in Order)

### 1. **AGENT-RUN-NOTES-OVERVIEW.md** (15 min) ← START HERE
**What:** Quick reference for the entire pattern  
**Contains:**
- What problem it solves
- Architecture at a glance  
- Key design decisions (table)
- Three example workflows
- Implementation timeline
- FAQ

**Read this if:** You want to understand the big picture

---

### 2. **docs/agent-run-notes-design.md** (30 min)
**What:** Detailed architectural design  
**Contains:**
- Pattern overview with diagrams
- 5 major design decisions (with justification)
- Schema definition
- Sweep analysis process
- Integration points with existing systems
- Phase-based implementation plan
- Risk mitigation

**Read this if:** You're making technical decisions or implementing Phase 1

---

### 3. **docs/runlog-technical-spec.md** (45 min)
**What:** Implementation specification (ready-to-code)  
**Contains:**
- Schema changes (BlobType.RUNLOG)
- New files/directories (.claude/runs/)
- CLI extension (reef analyze command)
- 8 core methods with full signatures:
  - create_run_note()
  - analyze_runs()
  - _aggregate_signals()
  - _generate_proposals()
  - _apply_safe_fixes()
  - _compute_sweep_metrics()
  - _create_analysis_polip()
- Hook integration
- Testing checklist
- Performance analysis

**Read this if:** You're coding Phase 1 or Phase 2

---

### 4. **docs/harness-integration.md** (30 min)
**What:** How this integrates with existing reef architecture  
**Contains:**
- Current architecture baseline (diagram)
- New components diagram
- Data flow (per-session and multi-session)
- Integration with 5 existing harness systems
- Improvement pathway (safe/risky/monitoring tracks)
- Quality metrics example
- Edge cases & safeguards
- Performance impact
- Rollout plan

**Read this if:** You're integrating with existing systems or doing system design

---

### 5. **docs/run-notes-user-guide.md** (20 min)
**What:** How to use the feature (practical examples)  
**Contains:**
- How it works (automatic + optional workflows)
- Real examples (week in the life)
- Complete command reference
- Common questions (11 Q&A)
- Troubleshooting
- Best practices

**Read this if:** You want to understand from a user perspective

---

### 6. **AGENT-RUN-NOTES-DELIVERABLES.md** (10 min)
**What:** Summary of all deliverables + validation checklist  
**Contains:**
- Overview of all 5 documents
- Key design decisions (one-pagers)
- File changes summary
- Implementation phases
- Validation checklist
- Risk assessment
- Success metrics

**Read this if:** You're a decision-maker or want a checklist

---

## Reading Paths by Role

### Architect/Decision-Maker
1. AGENT-RUN-NOTES-OVERVIEW.md
2. agent-run-notes-design.md (decisions section)
3. AGENT-RUN-NOTES-DELIVERABLES.md (checklist)
4. **Time:** ~30 min

### Implementation Lead (Phase 1 or 2)
1. AGENT-RUN-NOTES-OVERVIEW.md
2. agent-run-notes-design.md (all)
3. runlog-technical-spec.md (all)
4. harness-integration.md (integration points)
5. run-notes-user-guide.md (examples)
6. **Time:** ~2 hours

### Developer (Coding Phase 1)
1. AGENT-RUN-NOTES-OVERVIEW.md
2. runlog-technical-spec.md (all)
3. agent-run-notes-design.md (schema section)
4. run-notes-user-guide.md (examples)
5. **Time:** ~1.5 hours

### End User (Using the Feature)
1. AGENT-RUN-NOTES-OVERVIEW.md
2. run-notes-user-guide.md (all)
3. **Time:** ~30 min

### QA/Tester
1. AGENT-RUN-NOTES-OVERVIEW.md
2. runlog-technical-spec.md (testing section)
3. harness-integration.md (edge cases & safeguards)
4. run-notes-user-guide.md (troubleshooting)
5. **Time:** ~1 hour

---

## Key Questions This Answers

**"What is Agent Run Notes?"**  
→ AGENT-RUN-NOTES-OVERVIEW.md, "What is Agent Run Notes?"

**"How does it integrate with reef?"**  
→ harness-integration.md, "Integration with Harness Components"

**"What gets created/modified?"**  
→ runlog-technical-spec.md, "Schema Changes" + "Directory Structure"

**"Is this safe?"**  
→ agent-run-notes-design.md, "Safe Fixes vs Risky Changes"

**"How do I use it?"**  
→ run-notes-user-guide.md, entire document

**"What's the timeline?"**  
→ AGENT-RUN-NOTES-OVERVIEW.md, "Implementation Timeline"

**"What could go wrong?"**  
→ agent-run-notes-design.md, "Risk Mitigation"

**"How is this implemented?"**  
→ runlog-technical-spec.md, all 10 sections

---

## File Location Summary

```
PROJECT ROOT/
├── AGENT-RUN-NOTES-OVERVIEW.md              ← Start here (quick overview)
├── AGENT-RUN-NOTES-DELIVERABLES.md          ← Implementation checklist
├── START-HERE-RUN-NOTES.md                  ← This file (navigation guide)
│
└── docs/
    ├── agent-run-notes-design.md            ← Architectural design
    ├── runlog-technical-spec.md             ← Code implementation spec
    ├── harness-integration.md               ← System integration
    └── run-notes-user-guide.md              ← Practical usage
```

---

## Key Design Decisions (One-Page Reference)

| Question | Answer | Why |
|----------|--------|-----|
| **Where?** | `.claude/runs/` as RUNLOG polips | Integrate with index/lifecycle |
| **When?** | Manual, scheduled, or threshold triggers | Flexible feedback loop |
| **Schema?** | XML with metadata+observations+signals | Same as other polips |
| **Signals?** | Aggregated (3+ agreement = strong) | Conservative, pattern-based |
| **Auto-apply?** | Safe operations only (>90% confidence) | Human-in-loop for risky changes |
| **Rollback?** | Via snapshot mechanism | Existing safeguard |
| **Integration?** | Extends existing components | No breaking changes |

---

## Success Criteria After Phase 1 (Week 1)

- ✓ Run notes created in every session
- ✓ Schema works (XML serialization/deserialization)
- ✓ Manual end-to-end workflow tested
- ✓ No regressions in existing harness

---

## Success Criteria After All Phases (6 weeks)

- ✓ Auto-apply causes zero regressions
- ✓ Surfacing accuracy improves ≥5% (0.82 → 0.87+)
- ✓ Humans find proposals actionable
- ✓ Metrics show learning (accuracy trends up, noise down)

---

## Glossary (Quick Reference)

| Term | Meaning |
|------|---------|
| **Run note** | RUNLOG polip documenting agent observations (works, missing, noise, blockers) |
| **Signal** | Proposal extracted from run note (create, enhance, archive, tune) |
| **Sweep** | Analysis of accumulated run notes to detect patterns |
| **Proposal** | Actionable recommendation (based on aggregated signals) |
| **Fossil** | Fact polip (permanent, searchable knowledge) |
| **Confidence** | % of agents agreeing on a signal |

---

## Next Steps

1. **Read AGENT-RUN-NOTES-OVERVIEW.md** (15 min)
   This is the quickest way to understand the full pattern

2. **Pick your role above** and read documents in that order

3. **Raise questions** on specific documents
   - Decisions? → agent-run-notes-design.md
   - Code? → runlog-technical-spec.md
   - Integration? → harness-integration.md
   - Usage? → run-notes-user-guide.md

4. **Team review meeting** (once you've read the overview)
   - Discuss design decisions
   - Raise concerns
   - Validate timeline

5. **Kickoff Phase 1** once approved
   - Assign implementation lead
   - Break into tasks
   - Create GitHub issues

---

## Document Statistics

| Document | Size | Read Time | Audience |
|----------|------|-----------|----------|
| AGENT-RUN-NOTES-OVERVIEW.md | 12 KB | 15 min | Everyone |
| agent-run-notes-design.md | 16 KB | 30 min | Architects, leads |
| runlog-technical-spec.md | 14 KB | 45 min | Developers |
| harness-integration.md | 18 KB | 30 min | Systems architects |
| run-notes-user-guide.md | 12 KB | 20 min | End users |
| AGENT-RUN-NOTES-DELIVERABLES.md | 11 KB | 10 min | Decision-makers |
| **Total** | **83 KB** | **~3 hours** | (full deep dive) |

---

## Questions This Document Set Answers

✓ What is Agent Run Notes?
✓ Why do we need it?
✓ How does it work?
✓ What gets created/modified?
✓ Is it safe?
✓ How is it implemented?
✓ How do I use it?
✓ What could go wrong?
✓ What's the timeline?
✓ What are success criteria?

---

## Author & Attribution

- **Design & Architecture:** Nolan + Claude (Architect)
- **Date:** 2026-01-15
- **Status:** Ready for implementation
- **Confidence:** High (detailed design with specs)

---

**Start with AGENT-RUN-NOTES-OVERVIEW.md. It's 15 minutes and will answer most of your questions.**

Then pick the detailed document relevant to your role.

Good luck! 🚀

