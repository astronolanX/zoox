# Integration Matrix: Unified Trenches Architecture
**Date:** 2026-01-15
**Purpose:** Show how all components integrate without conflicts

---

## System Architecture (5 Layers)

```
┌─────────────────────────────────────────────────────────────────────┐
│ LAYER 4: Model Routing (Trenches)                                   │
│ - Groq / Ollama / Gemini → Claude (with PII guards)                │
│ - Rate limiting, latency fallback, result synthesis                │
├─────────────────────────────────────────────────────────────────────┤
│ LAYER 3: Orchestration (Agent Swarm)                                │
│ - claude-flow (swarm) OR Team Agents (sequential)                  │
│ - VoltAgent specializations (frontend/backend/ML/DevOps)           │
│ - Result synthesis → polips (if D3-B chosen)                       │
├─────────────────────────────────────────────────────────────────────┤
│ LAYER 2: Behavioral Infrastructure                                  │
│ - Mediator Modes (LISTENING, ANALYSIS, PREPARATION, RESPONSE, COOL)│
│ - PII Guard gates (block external routing)                         │
│ - Cooling-off enforcer (state machine)                             │
│ - Stream response manager (priority queue)                         │
├─────────────────────────────────────────────────────────────────────┤
│ LAYER 1: Core Harness (stdlib only, zero dependencies)             │
│ - Reef polip engine (spawn/surface/drift/sink)                     │
│ - Semantic PII detector (4-layer: regex→LLM→doc→metadata)          │
│ - Skill templating (for mode activation)                           │
│ - Hook system (SessionStart, PreToolUse, PostToolUse)             │
├─────────────────────────────────────────────────────────────────────┤
│ LAYER 0: File System + Configuration                                │
│ - ~/projects/ directory structure                                   │
│ - ~/.claude/ harness directories (core, skills, hooks, agents)     │
│ - CLAUDE.md (bedrock constraints)                                   │
│ - reef sync (polip integrity checks)                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Integration Matrix

| Component | Layer | Integrates With | Protocol | Status |
|-----------|-------|-----------------|----------|--------|
| **Reef Core** | L1 | Everything above | XML polip format | ✓ Complete |
| **Semantic PII** | L1 | L2 guards, L4 router | PIIAnalysis result | ✓ Complete |
| **Skill Templates** | L1 | L2 modes, L3 agents | YAML config | ✓ Template exists |
| **Hook System** | L1 | L2 orchestrator | PreToolUse/PostToolUse | ✓ Designed |
| **Mediator Modes** | L2 | L3 orchestrator | Mode.activate() | 40% done |
| **PII Guard** | L2 | L4 router | async is_safe_for_external() | ✓ Complete |
| **Cooling-Off** | L2 | L3 orchestrator | State machine | ✓ Complete |
| **Team Agents** | L3 | L2 orchestrator, L1 reef | Agent.run() → polips | ✓ Exists |
| **VoltAgent** | L3 | L3 orchestrator or L2 mediator | TBD (D2) | Pending |
| **claude-flow** | L3 | VoltAgent (maybe) | TBD (D1) | Pending |
| **Model Router** | L4 | All above (L2/L3) | SecureModelRouter.route() | ✓ Complete |
| **Rate Limiter** | L4 | Model router | NEW | ⚠️ Needed |

---

## Data Flow Scenarios

### Scenario A: Simple Mediation (Mediator Only, No Swarm)
```
User Input
  ↓
L2: Mediator Orchestrator
  ├─ Determine mode (LISTENING/ANALYSIS/PREPARATION/RESPONSE/COOL)
  ├─ Call mode.activate(context)
  ├─ Check PII in response (semantic detector)
  │  └─ If PII found → redact and warn user
  ├─ Read relevant polips (bedrock, prior decisions)
  │  └─ Via reef.surface_relevant(query)
  └─ Output to user (one voice, complexity hidden)

No external models used.
No polips created (unless D3-B: outcome polip at end).
Session ephemeral (unless D4-B: encrypted checkpoints).
```

**Flow Diagram:**
```
User Request
    ↓
PIIDetector.analyze() [L1]
    ↓
Mediator Mode [L2]
    ├─ Reef.surface(constraints) [L1]
    ├─ Reef.surface(prior_decisions) [L1]
    └─ Generate response
    ↓
PIIGuard.is_safe() [L2]
    ├─ SAFE → Output to user
    └─ PII FOUND → Redact + warn
    ↓
User sees response
(Orchestrator synthesis, single voice)
```

**Cost:** ~2-5 tokens (Haiku semantic check only)
**Latency:** <1s (semantic check ~500ms)
**Persistence:** Session ephemeral (default)

---

### Scenario B: Legal Research Scenario (Mediator + Swarm)
```
User: "What does TX Family Code 156.107 say about makeup time?"

Mediator Mode: PREPARATION
  ├─ Detect intent: legal research query
  ├─ Check PII: NO (public law question)
  ├─ Spawn analysis swarm [L3]
  │  ├─ Agent 1: Search CourtListener MCP → TX case law
  │  ├─ Agent 2: Summarize statute 156.107
  │  ├─ Agent 3: Find recent interpretations (2025+)
  │  └─ Agent 4: Synthesize into plain English
  ├─ Send public results to Groq [L4 trenches]
  │  └─ "Rephrase this in mediation language"
  ├─ Validate Groq response: NO PII [L2 guard]
  ├─ Synthesize findings with Claude [L4]
  └─ Output to user

User gets: "TX 156.107 means...
  - 3+ contempt findings for access denial = material change
  - Makeup time: double duration of denied periods
  - Deadline: next 90 days or request modification

  Implications for your case: ..."
```

**Flow Diagram:**
```
User Request
    ↓
PIIDetector.analyze("TX 156.107...") [L1]
    ↓ NO PII DETECTED
    ├─ Spawn swarm [L3]
    │  ├─ CourtListener MCP query
    │  ├─ Statute summarization
    │  └─ Synthesis
    ├─ Public results ready
    │  ↓
    ├─ L2 checks: safe for Groq?
    │  └─ YES → send summary
    ├─ L4 router → Groq [trenches]
    │  └─ "Rephrase in mediation language"
    ├─ L2 checks Groq response
    │  └─ NO PII → allow
    ├─ L4 router → Claude [synthesis]
    │  └─ "Integrate findings into case context"
    │
    └─ PIIDetector on final output [L1]
        └─ NO PII → output to user
```

**Cost:** ~50K tokens (swarm 4 agents × 10K + Groq 10K + Claude synthesis 10K)
**Latency:** ~15s (swarm parallel, Groq latency bottleneck)
**Persistence:** Depends on D4; if D3-B, create `decision` polip with findings

---

### Scenario C: PII Leakage Prevention (Security Gate)
```
User says: "My ex lives at the blue house on Maple, third from corner,
           and picks up Joey (our 7-year-old) every Wednesday at 3:15 PM."

PIIDetector.analyze() [L1]
    ├─ Regex: NO hits (no SSN/phone/email format)
    ├─ Semantic LLM: CRITICAL hits
    │  ├─ LOCATION_CONTEXTUAL: "blue house on Maple, third corner"
    │  ├─ MINOR_IDENTIFIER: "Joey, 7-year-old"
    │  ├─ SCHEDULE: "every Wednesday at 3:15 PM"
    │  └─ risk_score: 0.92 (HIGH)
    └─ Return: safe=FALSE

L2: Mediator Mode (LISTENING)
    ├─ PIIGuard.is_safe_for_external() → FALSE
    ├─ Output to user: "⚠️ Your message contains identifying information
                        that shouldn't leave this session. I'm noting
                        this in my analysis but won't share it externally."
    ├─ Store in-memory (fragmented PII state)
    │  └─ Track: LOCATION + MINOR + SCHEDULE combo
    ├─ Later: If user mentions "Joey gets good grades at Lincoln Elementary"
    │  └─ Semantic detector: "RECONSTRUCTION RISK - multiple identifiers"
    └─ Reframe user's thinking: "Let's focus on the arrangement pattern,
                                  not specific details."

L4 Router (if swarm research needed)
    └─ SecureModelRouter.route(content, session_id)
        ├─ PIIGuard.is_safe_for_external() → FALSE
        ├─ Fallback: Use Claude only
        │  └─ "This is sensitive custody info; using Claude only."
        └─ If user insisted on external: BLOCK + explain why
```

**Flow Diagram:**
```
User Input (contains PII)
    ↓
L1: RegexPIIDetector
    └─ No regex matches
    ↓
L1: SemanticPIIDetector (Haiku)
    ├─ "blue house on Maple..." → LOCATION_CONTEXTUAL (0.9)
    ├─ "Joey, 7-year-old" → MINOR_IDENTIFIER (0.95)
    ├─ "Wednesday 3:15 PM" → SCHEDULE (0.85)
    └─ risk_score: 0.92 (CRITICAL)
    ↓
L1: FragmentedPIIState.check_reconstruction()
    └─ Track across message window (4 hrs)
    ↓
L2: Mediator Mode
    ├─ Display: "⚠️ Sensitive information detected"
    ├─ Continue in CLAUDE-ONLY mode
    └─ If L3 wants to route to Groq:
        ↓
L2: PIIGuard.is_safe_for_external()
    └─ FALSE → block routing
    ↓
L4: SecureModelRouter.route()
    └─ Claude only (not external)
    ↓
User gets: Redacted analysis + reassurance
```

**Cost:** ~3 tokens (Haiku semantic check only)
**Latency:** <1s
**Persistence:** Session state tracks fragments; deleted on session end (D4-A)

---

## Authority Model (Who Controls What)

```
┌─────────────────────────────────────────────────┐
│ CLAUDE.MD (Bedrock)                             │
│ - Zero dependencies                             │
│ - Use uv for package management                 │
│ - Mediator is tool, not system                  │
│ Authority: HUMAN (override), cannot be modified │
│           by agents/mediator/polips             │
└─────────────────────────────────────────────────┘
              ↑ (reads, never modifies)
          L2: Mediator Modes
              (checks constraints)

┌─────────────────────────────────────────────────┐
│ REEF POLIPS (AI memory)                         │
│ - Decisions (mediator outcomes?)                │
│ - Constraints (bedrock mirror)                  │
│ - Threads (active work)                         │
│ - Facts (legal precedents, case law)            │
│ Authority: AI-generated (advisory)              │
│           Can be promoted to CLAUDE.MD by human │
└─────────────────────────────────────────────────┘
         ↑ (agents read/write per D3)
     L3: Agents
         (can create/modify if D3-B)

┌─────────────────────────────────────────────────┐
│ SESSION STATE (Ephemeral)                       │
│ - Mode context                                  │
│ - Fragmented PII tracker                        │
│ - Cooling-off state machine                     │
│ Authority: Session-owned, expires at session end│
│           No persistence unless D4-B            │
└─────────────────────────────────────────────────┘
         ↑ (agents read/write)
     L2: Mediator
         (maintains state, no persistence)
```

---

## Conflict Resolution Matrix

| Conflict | Layer | Resolution | Owner | Status |
|----------|-------|-----------|-------|--------|
| **Trenches vs PII** | L2↔L4 | PIIGuard gates all external routing | Security | ✓ Implemented |
| **Mediator state vs skill model** | L2 | Session state + polips separate state (D3) | Design | ⏳ D3 decision |
| **Agent autonomy vs control** | L3 | Authority hierarchy (D3) | Design | ⏳ D3 decision |
| **Persistence vs liability** | Session | Session-only + optional polips (D4) | Legal | ⏳ D4 decision |
| **claude-flow vs VoltAgent** | L3 | Integration point TBD (D2) | Architecture | ⏳ D2 decision |
| **Swarm size vs cost** | L3 | Start 8, measure token cost before 64 | Engineering | ⏳ Phase 4 |

---

## Integration Checklist (Phase by Phase)

### Phase 0: Directory Structure
- [ ] Create ~/projects/
- [ ] Move reef → ~/projects/reef
- [ ] Create ~/.claude/{core,skills,hooks,agents,runs,sparks}
- [ ] Verify all tests still pass
- [ ] Update .gitignore paths

### Phase 1: Secure Router
- [ ] Create src/reef/router/
- [ ] Move PIIGuard, SecureModelRouter to router/
- [ ] Add RateLimiter (per-model quota tracking)
- [ ] Add FallbackChain (latency-aware routing)
- [ ] Create .claude/config/trenches.yaml
- [ ] Write integration tests (PII blocking, rate limiting, fallback)
- [ ] **Gate:** All tests pass, rate limiter functional

### Phase 2: Mediator Modes
- [ ] Redesign retention policy (D4 decision needed)
- [ ] Implement contradiction detector (in-memory only)
- [ ] Create src/mediator/modes/ with 5 mode classes
- [ ] Implement MediatorOrchestrator
- [ ] Integration: modes → reef.surface() for constraints
- [ ] Integration: modes → PIIGuard for output checking
- [ ] Integration: modes → cooling-off state machine
- [ ] **Gate:** 8-hour simulated session, no persistence, no PII leaked

### Phase 3: Agent Integration
- [ ] Create ~/.claude/agents/ with VoltAgent specs (D2 decision)
- [ ] Integrate with team agents (Architect, Visionary, Karen)
- [ ] Design polip-creation protocol (D3 decision)
- [ ] Document agent → polip lifecycle
- [ ] Test: Agent creates decision polip, surfaces in future session
- [ ] **Gate:** Multi-agent analysis produces valid polips

### Phase 4: Swarm Orchestration
- [ ] Investigate claude-flow status (D1 decision)
- [ ] Set up swarm config (.claude/config/swarm.yaml)
- [ ] Prototype with 8 agents (2 parallel tasks each)
- [ ] Measure token cost: target <100K per mediation session
- [ ] Benchmark latency: target <30s for parallel analysis
- [ ] Integration: swarm results → SecureModelRouter
- [ ] **Gate:** 16 parallel tasks under 30s, token cost under budget

### Phase 5: End-to-End Integration
- [ ] Full mediation workflow test (custody dispute)
- [ ] Verify: No strategy persisted, no PII leaked, outcome captured
- [ ] Performance baseline: startup, mode transitions, routing
- [ ] Documentation: skill protocol, polip lifecycle, agent integration
- [ ] **Gate:** Complete 2-hour mediation simulation without issues

---

## Risk Mitigation by Layer

### Layer 1 Risk: Polip Integrity
| Risk | Mitigation |
|------|-----------|
| Polip corruption | reef sync --fix runs daily, atomic writes |
| Version mismatch | Schema migration tested before upgrade |
| Lost polips | Drift mechanism allows recovery from ~/.claude/ |

### Layer 2 Risk: Behavioral Consistency
| Risk | Mitigation |
|------|-----------|
| Mode switching errors | State machine pre-testing; frozen state during transition |
| PII leakage from modes | PIIGuard wraps all mode outputs |
| Cooling-off bypass | Temporal enforcement + test suite |

### Layer 3 Risk: Agent State
| Risk | Mitigation |
|------|-----------|
| Agent hallucination | Claude synthesis layer always present |
| Polip authority conflicts | D3 decision defines authority hierarchy |
| Swarm token exhaustion | Rate limiter caps per session + monitoring |

### Layer 4 Risk: Model Routing
| Risk | Mitigation |
|------|-----------|
| PII sent to Groq | PIIGuard blocks before routing; SafeModelRouter fallback |
| Rate limit exhaustion | RateLimiter tracks quota, fallback to Claude |
| Latency cascade | FallbackChain activates if latency > SLA |

---

## Integration Success Criteria

**✓ Structural Integrity:**
- [ ] All 5 layers present, dependencies respected
- [ ] No circular dependencies
- [ ] Authority model clear (CLAUDE.md > polips > session)
- [ ] PII guard gates all external access

**✓ Functional Integrity:**
- [ ] Mediator operates without external models (L4 optional)
- [ ] Agents can read constraints without modifying bedrock
- [ ] Swarm orchestrates parallel analysis safely
- [ ] Model router respects PII gates

**✓ Safety Integrity:**
- [ ] Semantic PII detector flags >95% of attack vectors
- [ ] Cooling-off state machine enforces temporal rules
- [ ] Session state expires reliably
- [ ] Polip authority prevents agent -> bedrock corruption

**✓ Performance Integrity:**
- [ ] Semantic check <500ms latency
- [ ] Mediator mode switch <1s
- [ ] Swarm parallel analysis <30s
- [ ] Total session cost <150K tokens (target)

---

**Document Owner:** Architect
**Last Updated:** 2026-01-15
**Status:** Ready for Integration Review
