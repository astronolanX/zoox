# Architecture Analysis: Unified Trenches System
**Date:** 2026-01-15
**Status:** Structural Integrity Review
**Scope:** Proposal evaluation for trenches system + multi-model orchestration

---

## EXECUTIVE SUMMARY

Your proposal **holds together structurally**, but with **critical integration conflicts** that require resolution order. The architecture is sound *in theory* but the implementation order is non-negotiable.

**Verdict:** BUILDABLE, not READY. Needs dependency untangling before Phase 1.

---

## PROPOSAL DECOMPOSITION

### 1. Unified Directory Structure
```
~/projects/              ← Consolidation point
  reef/                  ← Primary project (symbiotic memory)
  mediator-sdk/          ← Legal mediation (custody enforcement)
  ...other-projects/

~/.claude/               ← Harness layer (global infrastructure)
  core/                  ← Bedrock constraints
  skills/                ← Reusable behavioral modes
  hooks/                 ← Session lifecycle handlers
  agents/                ← Team orchestration specs
```

**ASSESSMENT:** ✓ SOLID
**Rationale:** Mirrors Claude SDK layout. Proven pattern. Low risk.
**Implementation:** Straightforward `mkdir` + symlink migration.

---

### 2. Trenches System (Free Agent Offload)
```
Claude (strategy layer)
    ↓ delegates grunts
Ollama/Groq/Gemini (trench workers)
    ↓ returns results
Claude (synthesis + decisions)
```

**ASSESSMENT:** ✓ STRUCTURALLY SOUND
**But:** Conflicts with #5 (Mediator as skill vs agent).

**Risk Profile:**
- **PII Leakage:** Karen's critical finding (run-020/021). Groq free tier + GitHub sync = discovery goldmine.
- **Model Selection:** Groq vs Ollama vs Gemini have different latency/cost/availability profiles.
- **Rate Limits:** Groq free tier insufficient for sustained mediation sessions (8+ hours).

**Dependency:** Requires **semantic PII detector** (✓ COMPLETE in `src/mediator/guards/pii.py`) as gate before external routing.

---

### 3. Claude-flow Integration (64-Agent Swarm)
```
claude-flow orchestrator
    ├─ Agent pool (32-64 instances)
    ├─ Message routing (priority queue)
    ├─ State synchronization
    └─ Result synthesis
```

**ASSESSMENT:** ⚠️ INTEGRATION RISK
**Problems:**

1. **Licensing Ambiguity:** Is claude-flow:
   - Free/open source?
   - Proprietary Anthropic tool?
   - Third-party package?
   - Found in run-020 MCPs but unclear status.

2. **Conflicts with VoltAgent:** Both are swarm orchestrators. Why both?
   - VoltAgent = specialized dev agents (frontend/backend/ML/DevOps)
   - claude-flow = general 64-agent coordination
   - **Question:** Are these layers (flow at top, Volt agents as implementations)?

3. **Scalability Unknown:**
   - 64 agents × async operations = memory/token cost unknown
   - No latency requirements specified
   - Groq rate limits may constrain swarm size

4. **Precedent:** run-020 Karen verdict: *"Multi-model offload adds complexity/liability with no demonstrated value."*

**Recommendation:** Prototype with 8-16 agents first. Measure token cost before scaling to 64.

---

### 4. VoltAgent Adoption (Specialized Dev Agents)
```
Architect agent (system design)
Frontend agent (UI/UX)
Backend agent (services/APIs)
ML agent (models/training)
DevOps agent (infra/deployment)
```

**ASSESSMENT:** ✓ TACTICAL VALUE
**But:** Unclear integration point.

**Questions:**
- Are these *inside* claude-flow orchestrator or *outside*?
- Do they share session state with reef polips?
- Authority model: Can agents create polips? Modify bedrock constraints?

**Current Status:**
- `.claude/runs/` shows team orchestration (Architect, Visionary, Karen)
- Pattern exists; integration point is architectural gap

---

### 5. Custody-Mediation: Mediator as SKILL (Not Agent)
```
MEDIATOR MODES (behavioral skills):
  ├─ LISTENING (intake, narrative building)
  ├─ ANALYSIS (interests, BATNA, options)
  ├─ PREPARATION (strategy, talking points, legal research)
  ├─ RESPONSE (active mediation, reframes, proposals)
  └─ COOLING-OFF (temporal enforcement, wait states)

NOT separate agents with handoffs.
One voice to user, complexity hidden.
→ "Invisible Orchestra Pattern" (run-020, Visionary discovery)
```

**ASSESSMENT:** ✓ CONCEPTUALLY SOUND
**Implementation Status:** 40% complete

**What's Done:**
- ✓ Semantic PII detector (4-layer: regex → LLM → docs → metadata)
- ✓ Cooling-off state machine (24-72hr wait, content reset, expedited override)
- ✓ Streaming response manager (safety-first priority queue)

**What Needs Redesign (Karen's feedback):**
- ⚠️ Retention policy: Creates discoverable evidence (FAIL)
- ⚠️ Contradiction detector: Weaponizable inconsistency record (FAIL)
- ✓ Semantic PII detector: Comprehensive, passes adversarial testing

**Critical Insight (Karen, run-021):**
> "The actual opponent is a motivated counter-party with legal discovery powers. Every piece of data you create can be subpoenaed."

**Implication:** Mediator-sdk cannot persist strategy/audit trails. Session-only, memory ephemeral.

---

## DEPENDENCY GRAPH

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 0: File System                                        │
│ - ~/projects/ directory structure                           │
│ - ~/.claude/ directory structure                            │
└─────────────────────────────────────────────────────────────┘
                            ↑
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: Core Harness (No external deps)                    │
│ - reef polip engine (COMPLETE)                              │
│ - semantic PII detector (COMPLETE)                          │
│ - skill templating system (EXISTS as reusable CLI patterns) │
│ - hook system (SessionStart, PreToolUse, PostToolUse)       │
└─────────────────────────────────────────────────────────────┘
                            ↑
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: Behavioral Infrastructure                          │
│ - Mediator skill modes (PARTIAL - needs redesign)           │
│ - Cooling-off enforcer (DONE)                               │
│ - PIIGuard gate (DONE)                                      │
│ - SecureModelRouter (DONE)                                  │
└─────────────────────────────────────────────────────────────┘
                            ↑
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: Agent Orchestration                                │
│ - Team agents (Architect, Visionary, Karen) (EXISTS)        │
│ - VoltAgent specializations (frontend/backend/ML/DevOps)    │
│ - claude-flow swarm (UNCLEAR STATUS)                        │
│ - Integration with reef for polip generation (NOT DESIGNED) │
└─────────────────────────────────────────────────────────────┘
                            ↑
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: Model Routing (Trenches)                           │
│ - Claude (primary, PII-safe)                                │
│ - Groq/Ollama/Gemini (public research only)                 │
│ - PII guard gates all routing                               │
│ - Rate limit management                                     │
│ - Fallback chains                                           │
└─────────────────────────────────────────────────────────────┘
```

### Critical Dependencies (Build Order)

| Priority | Component | Depends On | Status | Risk |
|----------|-----------|-----------|--------|------|
| **1** | Directory structure | None | IMMEDIATE | Low |
| **2** | Reef core (L1) | Dir structure | ✓ EXISTS | None |
| **2.5** | Semantic PII detector (L2) | Reef core | ✓ EXISTS | None |
| **3** | PIIGuard + Router (L2) | PII detector | ✓ EXISTS | Low |
| **4** | Mediator modes (L2) | PIIGuard, cooling-off | 40% | Medium |
| **5** | Team agents (L3) | Reef core, skills | EXISTS | Low |
| **6** | VoltAgent setup (L3) | Team agents | TBD | Medium |
| **7** | claude-flow (L3) | VoltAgent OR separate? | UNKNOWN | High |
| **8** | Trenches router (L4) | All of L3, PIIGuard | TBD | High |

---

## INTEGRATION CONFLICTS

### CONFLICT 1: Claude-flow vs VoltAgent (Swarm Orchestration)
**Problem:** Two overlapping orchestration systems.

**Scenarios:**
1. **Sequential layers:** VoltAgent agents *inside* claude-flow swarm
   - Cleanest architecture
   - Need clear handoff protocol

2. **Parallel selection:** Choose one for primary, other for specialized tasks
   - Risk of context fragmentation
   - Different state management models

3. **Hybrid:** claude-flow for general swarm, VoltAgent for dev-specific tasks
   - Adds complexity but maximizes flexibility

**Decision Required Before Building:**
- [ ] Which is primary orchestrator?
- [ ] How do agents share reef session state?
- [ ] Can agents create/modify polips? (Authority model)

---

### CONFLICT 2: Mediator as Skill vs Agent
**Problem:** Skills are stateless functions; agents carry state.

**Reality Check:**
- Cooling-off state machine = persistent state (violates skill model)
- Session fragmentation detection = cross-message state (skill issue)
- Authority conflicts: Who promotes skill outputs to polips?

**Resolution:**
Define "skill" precisely for mediator context:
```
SKILL = behavioral mode provider
  - Stateless interface to mode selection
  - State held in polip/session layer
  - Invoked by orchestrator agent

Mediator = Suite of 5 skills (LISTENING, ANALYSIS, PREPARATION, RESPONSE, COOLING-OFF)
  - Activated sequentially by orchestrator
  - Each maintains state via polips
  - One voice to user (orchestrator synthesizes)
```

**Action:** Document skill ↔ polip ↔ agent lifecycle explicitly.

---

### CONFLICT 3: Public vs Private Data (Trenches Security)
**Problem:** Groq/Ollama are external; mediation involves sensitive PII.

**Karen's Verdict (run-020):** Multi-model offload adds liability with no value.

**Current Mitigation:**
- ✓ Semantic PII detector blocks external routing
- ✓ SecureModelRouter enforces Claude-only for strategy
- ⚠️ **Gap:** No rate-limit manager (Groq free tier exhaustion scenario)
- ⚠️ **Gap:** No latency fallback (streaming timeout → where?)

**Action Items:**
1. Add rate-limit monitoring per external model
2. Define latency SLA (streaming → fallback thresholds)
3. Test token cost for 8-hour mediation session
4. Verify Groq free tier sustainable for target usage

---

### CONFLICT 4: Session Persistence vs Discovery Liability
**Problem:** Mediator must survive session crashes, but persisting data creates legal liability.

**Karen's Finding (run-021):**
> Retention policy solves wrong problem - creates discoverable evidence AGAINST client. Strategy/AUDIT data persisted = forensic goldmine for opposing counsel.

**Resolution Path:**
- ✓ Session-only memory (no persistence to disk)
- ✓ Polips created only post-mediation (crystallized agreements only)
- ✓ In-memory caches expire at session end
- ⚠️ **Gap:** How to survive 20-min crash during 8-hr mediation?

**Options:**
1. **Ephemeral mode:** Crash = restart from where left off (manual re-context)
2. **Incremental checkpoints:** Save encrypted polips, auto-delete post-session
3. **Cloud backup:** Encrypted session snapshot to secure storage (must be discoverable-safe)

**Recommendation:** Start with option 1 (ephemeral), prove crash cost, then evaluate 2/3.

---

## BUILD ORDER (Dependency-Respecting Sequence)

### **PHASE 0: Foundation (1-2 days)**
Set up infrastructure without changing behavior.

```bash
# 1. Directory consolidation
mkdir -p ~/projects
cd ~/projects
git clone ~/Desktop/reef reef

# 2. Harness initialization
mkdir -p ~/.claude/{core,skills,hooks,agents,runs,sparks}

# 3. Verify existing components work
cd ~/projects/reef
uv run pytest
uv run reef reef  # Polip health check
```

**Validation:** All existing tests pass, directory structure in place.

---

### **PHASE 1: Secure Router (2-3 days)**
Build layer 4 (trenches) with PII gates.

**Components:**
- [ ] Create `src/reef/router/` with:
  - `pii_gate.py` → PIIGuard (exists, integrate)
  - `model_router.py` → SecureModelRouter (exists, integrate)
  - `rate_limiter.py` → NEW, per-model quotas
  - `fallback_chain.py` → NEW, latency-aware fallback

- [ ] Add configuration:
  ```yaml
  # .claude/config/trenches.yaml
  models:
    claude:
      priority: 100
      rate_limit: null  # Unlimited

    groq:
      priority: 80
      rate_limit: 300/month  # Free tier
      latency_sla_ms: 5000
      fallback_on_timeout: true

    ollama:
      priority: 70
      rate_limit: null
      latency_sla_ms: 10000
      location: localhost:11434
  ```

- [ ] Write tests:
  - PII blocking (100% coverage)
  - Rate limit enforcement
  - Fallback chain activation
  - Timeout handling

**Validation:** Can route "public research" to Groq, "strategy+PII" to Claude only.

---

### **PHASE 2: Mediator Modes (3-4 days)**
Complete layer 2 (behavioral infrastructure) for mediation.

**Components:**
- [ ] Redesign retention (SESSION-ONLY):
  - In-memory MemoryStore (expires at session end)
  - No persistence layer
  - Ephemeral mode only

- [ ] Implement contradiction detector *privately*:
  - Runs in-memory during session
  - Never persisted
  - Surfaces to user (private prep) but not discoverable

- [ ] Complete mediator skill modes:
  ```python
  # src/mediator/modes/__init__.py
  class MediatorMode(ABC):
      """Base skill mode for mediation."""
      async def activate(self, context: MediationContext) -> MediationResponse

  class ListeningMode(MediatorMode):
      """Narrative building, story capture."""

  class AnalysisMode(MediatorMode):
      """Interests, BATNA, options analysis."""

  class PreparationMode(MediatorMode):
      """Strategy, talking points, legal research."""

  class ResponseMode(MediatorMode):
      """Active mediation, reframes, proposals."""

  class CoolingOffMode(MediatorMode):
      """Wait states, temporal enforcement."""
  ```

- [ ] Create orchestrator:
  ```python
  # src/mediator/orchestrator.py
  class MediatorOrchestrator:
      """Orchestrates mode transitions. One voice to user."""
      async def run_session(self, case_data) -> MediationOutcome

      # Internally: switch modes, synthesize output
      # To user: single coherent voice
  ```

**Validation:** 8-hour simulated mediation session completes without crashes, no persistent audit trail created.

---

### **PHASE 3: Agent Integration (4-5 days)**
Layer 3 (agent orchestration).

**Prerequisite Decision:**
- [ ] Resolve claude-flow vs VoltAgent question
- [ ] Document agent ↔ polip lifecycle
- [ ] Define skill invocation protocol

**Components:**
- [ ] Set up VoltAgent specializations:
  ```
  ~/.claude/agents/
    ├─ architect.yaml    (system design decisions)
    ├─ frontend.yaml     (UI/UX reasoning)
    ├─ backend.yaml      (service architecture)
    ├─ ml.yaml           (model selection, tuning)
    └─ devops.yaml       (infra, deployment)
  ```

- [ ] Integrate with team orchestration:
  - Existing: Architect, Visionary, Karen personalities
  - New: VoltAgent specializations (inherit personalities)
  - Test: `/team` command with mix of both

- [ ] Define polip generation protocol:
  - When do agents create polips?
  - Authority: Can agents modify bedrock?
  - Promotion: Agent outputs → polips → crystallized → CLAUDE.md

**Validation:** VoltAgent backend agent can design service architecture, save reasoning as polip decision, reference it in future sessions.

---

### **PHASE 4: Claude-flow Swarm (3-5 days)**
Layer 3 (swarm coordination).

**Prerequisite:**
- [ ] Clarify claude-flow status (free/proprietary/third-party)
- [ ] Prototype with 8 agents, measure token cost
- [ ] Benchmark latency vs single-model

**Components:**
- [ ] Swarm configuration:
  ```yaml
  # .claude/config/swarm.yaml
  max_agents: 8  # Start small
  priority_queue: true
  state_sync: reef  # Use polips for shared state
  result_synthesis: claude-opus  # Always
  ```

- [ ] Orchestration rules:
  - When to spawn agents
  - Task decomposition strategy
  - Result aggregation
  - Fallback if agent fails

- [ ] Integration with trenches:
  - Agents can request external models (routed through PIIGuard)
  - Swarm results fed to Claude for synthesis
  - Rate limits tracked per swarm instance

**Validation:** 16 parallel research tasks (8 agents × 2 tasks each) complete within 30s, token cost < 100K.

---

### **PHASE 5: Unified System (2-3 days)**
Integration and smoke tests.

**Components:**
- [ ] End-to-end test:
  - User: "Mediate custody dispute between Alice and Bob"
  - System: Orchestrator → activates Listening mode → spawns analysis agents → uses Groq for case law (PII-gated) → cooling-off state → outcome polip
  - Verify: No strategy persisted, no PII leaked to Groq, outcome recorded as decision polip

- [ ] Performance baseline:
  - Session startup latency
  - Mode transition overhead
  - Trenches routing latency
  - Token cost per session type

- [ ] Documentation:
  - Skill invocation protocol
  - Polip authority model
  - Agent → polip lifecycle
  - Emergency shutdown (clear all sessions)

---

## STRUCTURAL INTEGRITY ASSESSMENT

### Strengths
1. **Layered architecture:** Clear separation (L0 files → L1 harness → L2 behavior → L3 agents → L4 routing)
2. **Local-first:** No cloud dependency. Reef stays sovereign.
3. **PII-aware:** Semantic detector gates all external routing.
4. **Skill model:** Mediator as mode suite, not agents. Aligns with "invisible orchestra" pattern.
5. **Proven foundations:** Reef polips, team orchestration, regulatory constraints already exist.

### Weaknesses
1. **Integration gaps:** claude-flow status unknown. VoltAgent ↔ team agents unclear.
2. **State management:** Skill model conflicts with persistent mediation state.
3. **Discovery liability:** Retention policy needs complete redesign (Karen's finding).
4. **Rate limiting:** Groq free tier not modeled. Latency fallbacks undefined.
5. **Documentation:** Authority models (agents/polips/config) not explicit.

### Risks (Ranked by Impact)
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Mediator persists strategy data | Legal liability | HIGH | Phase 2 redesign: session-only |
| claude-flow unavailable/proprietary | Architecture blocked | MEDIUM | Phase 0 decision required |
| Groq rate limits exhausted | Trenches fails silently | MEDIUM | Phase 1 rate limiter + monitoring |
| Agent state fragments across layers | Incoherent results | MEDIUM | Phase 3 polip lifecycle docs |
| 64-agent swarm token cost exceeds budget | Unaffordable | MEDIUM | Phase 4 prototyping (8 agents first) |

---

## DECISIONS REQUIRED BEFORE PHASE 1

### Decision D1: Claude-flow Status
**Question:** Is claude-flow:
- [ ] Open source (where? github.com/ruvnet/claude-flow?)
- [ ] Proprietary Anthropic (internal only?)
- [ ] Third-party package (pip install?)
- [ ] Not ready (research phase?)

**Impact:** Blocks phase 4 (swarm orchestration). Architecture depends on this.

**Action:** Investigate MCPs from run-020, contact ruvnet if necessary.

---

### Decision D2: VoltAgent Integration Point
**Question:** Are VoltAgent agents:
- [ ] Implementations *inside* claude-flow swarm?
- [ ] Separate from swarm, invoked independently?
- [ ] Specialized modes (like mediator skills)?

**Impact:** Determines layer 3 architecture.

**Action:** Design spec: "VoltAgent Agents as Swarm Implementations" or alternative.

---

### Decision D3: Mediator Authority Model
**Question:** Can mediator/agents:
- [ ] Create polips? (YES/NO)
- [ ] Modify bedrock constraints? (NO / only suggest)
- [ ] Promote outcomes to config? (NO / suggest only)
- [ ] Who owns session polips after mediation? (Client / Agent / Mediator)

**Impact:** Polip ecosystem integrity.

**Action:** Document "Polip Authority Hierarchy" before phase 3.

---

### Decision D4: Session Persistence Strategy
**Question:** How to survive mediation session crashes?
- [ ] Option A: Ephemeral (restart from notes)
- [ ] Option B: Encrypted checkpoints (delete post-session)
- [ ] Option C: Cloud backup (must be legally safe)

**Impact:** Phase 2 (mediator modes) implementation.

**Action:** Evaluate liability with Karen. Choose option before phase 2.

---

## RECOMMENDATIONS

### Short Term (Next 2 weeks)
1. **Execute Phase 0:** Directory consolidation, verify existing tests pass.
2. **Resolve D1, D2, D3, D4:** Get stakeholder alignment on decisions.
3. **Phase 1 start:** Secure router with rate limiting, full PII coverage.
4. **Karen review:** Mediator mode redesigns (retention, contradiction detector).

### Medium Term (Weeks 3-6)
1. **Phase 2:** Complete mediator modes (session-only, no persistence).
2. **Phase 3:** VoltAgent integration (assuming D2 resolved).
3. **Prototype Phase 4:** 8-agent swarm, measure token cost.

### Long Term (Weeks 7+)
1. **Phase 4:** Full swarm orchestration (64 agents if token cost acceptable).
2. **Phase 5:** End-to-end integration, performance baseline.
3. **Governance:** Establish polip promotion pathway (organic → crystallized → CLAUDE.md).

---

## FINAL VERDICT

**Architecture Holds:** ✓ YES
**Ready to Build:** ✗ NO (decisions required)
**Implementation Order:** CRITICAL (dependency graph must be respected)
**Risk Level:** MEDIUM (legal liability in mediator, integration complexity)

**Confidence:** 80%

The structure is sound. The dependencies are clear. The build order is non-negotiable.

**Next step:** Resolve the four decision points. Then Phase 0 is straightforward.

---

**Author:** Architect (analysis mode)
**Validated by:** Structure, dependency analysis, existing precedents (run-020/021)
**Ready for:** Team review and decision finalization
