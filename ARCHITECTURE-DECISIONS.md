# Architecture Decision Log
**Date:** 2026-01-15
**Status:** Decision Points Identified (Awaiting Resolution)

---

## Decision Matrix

### D1: Claude-flow Status
| Dimension | Question | Impact | Evidence |
|-----------|----------|--------|----------|
| **Availability** | Is it open source or proprietary? | Blocks phase 4 | Found in run-020 MCP list as `claude-flow: "64-agent swarm orchestration"` |
| **Location** | Where is source code? | Build planning | GitHub reference: `github.com/ruvnet/claude-flow` (unverified) |
| **Licensing** | Can we depend on it? | Legal/commercial | Unknown |
| **Maturity** | Production-ready? | Risk assessment | Listed in exploration phase, not integration phase |

**Options:**
- **Option D1-A:** Proprietary (use only if Anthropic-approved)
  - Pro: Official, supported, secure
  - Con: May not be available; might have commercial restrictions
  - Next: Reach out internally

- **Option D1-B:** Third-party open source
  - Pro: Can integrate, audit, fork if needed
  - Con: Maintainability risk; may diverge from Anthropic direction
  - Next: GitHub review, license check, contributor activity

- **Option D1-C:** Not ready / Research phase
  - Pro: Defer decision, focus on agents first
  - Con: Blocks swarm orchestration until ready
  - Next: Fall back to VoltAgent-only arch for now

**Recommendation:** Complete GitHub investigation before D2 decision.

**Action Owner:** Architecture lead
**Due:** Before Phase 1 checkpoint

---

### D2: VoltAgent Role
| Dimension | Question | Impact | Evidence |
|-----------|----------|--------|----------|
| **Layer placement** | Inside or outside swarm? | Architecture | VoltAgent docs mention specialization (frontend/backend/ML/DevOps) but not layer position |
| **State sharing** | Can agents share reef polips? | Integration | Reef doesn't know about agents yet |
| **Authority** | Can agents create polips? | Governance | Polip lifecycle doesn't specify agent-generated polips |
| **Activation** | When are agents spawned? | Orchestration | Unclear if mediator/skills invoke agents or swarm does |

**Options:**

- **Option D2-A:** VoltAgent agents as implementations inside claude-flow swarm
  ```
  claude-flow orchestrator (64 capacity)
    ├─ Architect agent (VoltAgent)
    ├─ Frontend agent (VoltAgent)
    ├─ Backend agent (VoltAgent)
    ├─ ML agent (VoltAgent)
    ├─ DevOps agent (VoltAgent)
    └─ Generic workers (fill remaining capacity)
  ```
  - Pro: Single orchestration layer, clean authority model
  - Con: Requires close integration with swarm scheduler
  - Architecture: VoltAgent specializes claude-flow worker agents

- **Option D2-B:** VoltAgent agents independent, invoked on-demand
  ```
  Mediator orchestrator
    ├─ Calls VoltAgent backend agent
    ├─ Calls VoltAgent ML agent (for case law research)
    └─ OR spawns claude-flow swarm for parallel analysis
  ```
  - Pro: Flexible, can choose tool per task
  - Con: Two separate orchestration paths; state fragmentation risk
  - Architecture: VoltAgent and swarm are peer systems

- **Option D2-C:** VoltAgent agents as behavioral skills (like mediator modes)
  ```
  VoltAgent = suite of domain-specific behavioral modes
    ├─ backend-design skill
    ├─ frontend-design skill
    ├─ ml-model-selection skill
    └─ devops-deployment skill

  Invoked like mediator modes (stateless + session state in polips)
  ```
  - Pro: Consistent with skill model; clear state management
  - Con: Limits agent autonomy; requires significant redesign
  - Architecture: No separate agents, only behavioral skills

**Recommendation:** D2-A (inside swarm) if D1-B/D1-A confirmed. D2-C (skills model) if D1-C (defer swarm).

**Action Owner:** Integration architect
**Due:** Before Phase 3 start

---

### D3: Mediator Authority Model
| Dimension | Question | Impact | Evidence |
|-----------|----------|--------|----------|
| **Polip creation** | Can mediator/agents create polips? | Ecosystem | Unclear if mediation outcomes → polips automatically |
| **Constraint modification** | Can agents suggest bedrock changes? | Governance | No precedent in existing codebase |
| **Config promotion** | Can mediator recommend CLAUDE.md edits? | Authority | Promotion pathway exists only for reef → config in native infrastructure design |
| **Session ownership** | Who owns session polips after mediation? | Legal/access | Affects data retention liability |

**Options:**

- **Option D3-A:** Strict separation (mediator is tool, doesn't control polips)
  - Mediator can only READ polips (constraints, prior decisions)
  - Mediator outputs → User sees → User creates polips if desired
  - Pro: Clear authority; no agent can modify repo
  - Con: Manual capture burden; outcomes easily lost
  - Governance: Human-driven, safe but slow

- **Option D3-B:** Mediator creates outcome polips (post-session)
  - Session runs (in-memory, ephemeral)
  - At conclusion, mediator auto-creates `decision` polip with agreed outcome
  - Cannot modify bedrock or config
  - Pro: Outcomes preserved; automatic capture
  - Con: What if user disagrees with saved outcome? Still discoverable.
  - Governance: Automatic, but audit trail exists

- **Option D3-C:** Full mediator autonomy (with oversight)
  - Mediator CAN create/modify polips during session
  - Mediator CANNOT modify bedrock or config
  - All modifications reviewed before session exit
  - Pro: Rich context capture; real-time learning
  - Con: Karen's finding: discoverable evidence risk
  - Governance: Agent-driven with human gates

**Recommendation:** D3-A (strict) initially. D3-B (outcome polips) if Karen approves post-session capture. D3-C only after legal review.

**Rationale:** Karen's run-021 finding is critical: *"Every piece of data you create can be subpoenaed."* Start conservative.

**Action Owner:** Legal architect + mediator designer
**Due:** Before Phase 2 start

---

### D4: Session Persistence Strategy
| Dimension | Question | Impact | Evidence |
|-----------|----------|--------|----------|
| **Crash recovery** | How to survive mid-session crashes? | Reliability | 8-hour mediation exposed to network/system failures |
| **Evidence lifecycle** | What happens to session data after mediation? | Legal risk | Karen finding: persisted data = discovery liability |
| **Confidentiality** | How to protect sensitive negotiation data? | Security | PII detector exists but doesn't solve persistence |
| **Audit trail** | Do we need forensic records? | Compliance | Mediator context requires some history |

**Options:**

- **Option D4-A:** Pure ephemeral (crash = lose everything)
  - Session entirely in memory (Python process)
  - Crash or exit → all data gone
  - User can manually re-contextualize after restart
  - Pro: Zero discovery liability; simplest code
  - Con: User experience poor if 20-min crash at 6-hr mark
  - Data retention: None (except user's notes external to system)

- **Option D4-B:** Encrypted session checkpoint (delete post-session)
  - Auto-save encrypted session state every 5 min to disk
  - On crash: auto-recover from latest checkpoint
  - Post-session: cryptographically delete all files
  - Pro: Good UX; zero liability if deletion verified
  - Con: Requires verified deletion mechanism; encryption key management
  - Data retention: 0 seconds post-session (if deletion verified)

- **Option D4-C:** Secure cloud backup (attorney-privileged)
  - Encrypted session snapshot to secure storage (attorney privilege structure)
  - Retention: 30 days (audit trail) then delete
  - Pro: Strong crash recovery; audit trail for legitimate cases
  - Con: Karen's concern: cloud = "motivated adversary"; privilege not guaranteed
  - Data retention: 30 days post-session

- **Option D4-D:** Hybrid (checkpoints + polips)
  - In-session: ephemeral + 5-min encrypted checkpoints (D4-B)
  - Post-session: create polip only for OUTCOME (agreed terms)
  - Pro: Best crash recovery + preserved outcomes
  - Con: D3-B decision required first
  - Data retention: Session ephemeral, outcome as polip only

**Recommendation:** D4-A (ephemeral) for Phase 2 MVP. Upgrade to D4-B (checkpoints) if user testing shows crash pain. Avoid D4-C (cloud) until legal privilege confirmed.

**Rationale:** Karen's primary risk is discoverable evidence. Sessions are not valuable 30 days later; only outcomes are. Keep sessions ephemeral.

**Action Owner:** Mediator designer + security architect
**Due:** Before Phase 2 start

---

## Decision Dependency Graph

```
D1: Claude-flow Status
  │
  ├─→ D2: VoltAgent Role
  │      └─→ Phase 3 (Agent Integration)
  │
  └─→ Phase 4 (Swarm Orchestration)

D3: Mediator Authority
  │
  └─→ D4: Session Persistence
       └─→ Phase 2 (Mediator Modes)

All decisions must resolve before their dependent phase starts.
D1, D3, D4 have critical path to Phase 2+ start.
```

---

## Resolution Checklist

### D1 Resolution (Claude-flow Status)
- [ ] Search `github.com/ruvnet/claude-flow` for source code
- [ ] Check license (MIT/Apache/proprietary/unknown)
- [ ] Verify if active project (commits in 2025/2026)
- [ ] Check if used in other Anthropic projects
- [ ] Document findings in ARCHITECTURE-ANALYSIS.md
- [ ] Get sign-off from architecture lead

### D2 Resolution (VoltAgent Role)
- [ ] Review VoltAgent documentation
- [ ] Map specializations (frontend/backend/ML/DevOps) to use cases
- [ ] Design integration spec: "VoltAgent Agents as Swarm Implementations" or alternative
- [ ] Define state-sharing protocol with reef
- [ ] Get sign-off from architecture lead + VoltAgent maintainer (if external)

### D3 Resolution (Mediator Authority)
- [ ] Get Karen's preference: D3-A, D3-B, or D3-C?
- [ ] Define polip creation triggers
- [ ] Document bedrock/config protection mechanisms
- [ ] Define post-session polip lifecycle
- [ ] Get legal/ethical review if D3-B/D3-C chosen

### D4 Resolution (Session Persistence)
- [ ] Get Karen's risk assessment for each option
- [ ] Design verified deletion mechanism (if D4-B chosen)
- [ ] Define checkpointing frequency and storage limits
- [ ] Document encryption key management
- [ ] Get legal review if D4-C chosen

---

## Current State Summary

| Decision | Status | Blocker | Owner |
|----------|--------|---------|-------|
| D1 | PENDING | Phase 4 blocked | Architecture lead |
| D2 | PENDING | Phase 3 blocked | Integration architect |
| D3 | PENDING | Phase 2 blocked | Mediator designer |
| D4 | PENDING | Phase 2 blocked | Security architect |

**Critical Path Insight:**
- D3 + D4 must resolve first (shorter lead time, blocks Phase 2)
- D1 + D2 can resolve in parallel (longer lead time, blocks Phase 3+)
- Phase 2 can start **before** D1/D2 if D3/D4 decided

---

## Risk Mitigation (Decision-Agnostic)

### If D1 = unavailable
- **Fallback:** Use team agents (Architect, Visionary, Karen) without 64-agent swarm
- **Impact:** Sequential instead of parallel; slower analysis but same quality
- **Mitigation:** Prototype with 2-4 agents first, parallelize only if D1 confirmed

### If D2 = independent agents
- **Fallback:** Design explicit orchestration layer that coordinates VoltAgent + swarm separately
- **Impact:** State fragmentation risk, more complex integration
- **Mitigation:** Build polip-based state sharing protocol in Phase 3

### If D3 = strict separation (only read-only)
- **Fallback:** User manually creates outcome polips after mediation
- **Impact:** Outcomes may be lost if user forgets
- **Mitigation:** Add post-session "Save outcome?" prompt

### If D4 = pure ephemeral
- **Fallback:** User keeps external notes for crash recovery
- **Impact:** UX degradation on crashes during long sessions
- **Mitigation:** Phase 2 MVP accepts this; Phase 2.5 adds checkpoints if needed

---

## Next Steps (Immediate)

1. **Today:** Schedule decision review with architecture + legal + mediator teams
2. **Tomorrow:** Investigate D1 (claude-flow status) - 2 hour research
3. **Day 3:** Collect D3 + D4 preferences from Karen and legal
4. **Day 4:** Finalize D1 + D2 design specs
5. **Day 5:** Begin Phase 0 (directory consolidation, which is decision-agnostic)

---

**Document Owner:** Architect
**Last Updated:** 2026-01-15
**Status:** Ready for Team Review
