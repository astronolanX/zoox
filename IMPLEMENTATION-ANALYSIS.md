# Implementation Analysis: Builder's Perspective

**Date:** 2026-01-15
**Role:** IMPLEMENTER - Assessing buildability THIS WEEK
**Status:** 4,500 LOC reef core + 38 skills + 10 agents + 12 hooks + mediator-sdk skeleton exists

---

## EXISTING STATE AUDIT

### Reef Core (STABLE)
- **blob.py**: 2,500+ LOC - Polip/Reef data model, TF-IDF search, wiki linking, XML persistence
- **cli.py**: 1,500+ LOC - Full command suite (sprout, reef, sync, drift, migrate, sink, status, snapshot, graph, template, index)
- **mediator/__init__.py**: 0.1.0 skeleton (PII detector stub exists)
- **Tests**: Comprehensive pytest suite covering data model, search, CLI
- **Features SHIPPED**: Progressive loading (L1/L2/L3), LRU tracking, template expansion, drift discovery

### ~/.claude/ Infrastructure (SUBSTANTIAL)
- **38 skills** (4,390 LOC) - task-genome, task-templates, web-scraper, worktree-lifecycle, etc.
- **10 agents** - pattern-hunter, scorer, scraper, visionary, etc.
- **12 hooks** - incubator_inject.py, session-start surfacing, git lifecycle
- **Incubator Phase 5** - COMPLETE (84 tests passing)
  - Ingest → Score → Patterns → Promote → Surface pipeline
  - 74 insights processed, 8 promoted to consciousness
  - Automatic session surfacing already working

### custody-mediation Project
- **32 .claude directories** (constraints, decisions, facts, context, analysis, protocols, metrics)
- **Mediator perspective skill** - Domain-specific (El Paso family court)
- **.data/.processed/.vault/.strategy** - Case data pipeline structure
- **No SDK yet** - Just skill template

---

## PROPOSED ARCHITECTURE ASSESSMENT

### What You Proposed
1. Unified directory structure (~/projects/, ~/.claude/)
2. Trenches system (Free agents doing grunt work)
3. claude-flow integration for swarm orchestration
4. VoltAgent adoption for dev agents
5. Evidence MCP for case documents
6. **Mediator as SKILL, not agent** ← This is the pivot

### What's Actually Happening
- **Reef IS the unified structure** - L0 (files) → L3 (FUSE) roadmap, coexistence model (config vs organic)
- **Incubator IS the grunt work engine** - 5-phase pipeline already works
- **Skills > Agents** - You have 38 skills, only 10 agents. Skills won already.
- **Mediator domain exists** - Just needs SDK wrapper
- **You don't need all 5 proposed items** - You need to INTEGRATE what exists

---

## HIDDEN DEPENDENCIES (THE REAL ISSUES)

### Dependency 1: Directory Consolidation → Breaks Current Setup
**Problem**: Custody-mediation lives in `~/Desktop/`. If you consolidate to `~/projects/`, ALL existing `.claude/` paths break.

**Impact**:
- 32 directories with hardcoded references
- Polips with `[[wiki-links]]` that assume Desktop layout
- Hooks that scan `.claude/` relative paths
- **.data/.processed/.vault paths** break if project moves

**Risk Level**: HIGH - Will cause silent failures (links just don't resolve)

**Solution**: DON'T consolidate yet. Instead:
1. Establish symlinks: `~/projects/custody-mediation → ~/Desktop/custody-mediation`
2. Make Reef path-agnostic (already is - uses relative .claude/)
3. Phase consolidation over 2 weeks, not this week

### Dependency 2: Mediator SDK Identity Crisis
**Problem**: Is mediator:
- A Claude Code skill (current state in custody-mediation)?
- An SDK you import into reef?
- A plugin with subcommands?
- A swarm agent orchestrator?

**Current Evidence**:
- `/mediator` skill exists in custody-mediation
- `src/mediator/__init__.py` exists in reef (0.1.0 skeleton)
- No unified import path
- Unclear if "mediator SDK" means "Python library" or "distributed system"

**Risk Level**: MEDIUM - Scope creep if not bounded

**Solution**: Mediator is a SKILL-FIRST product (not SDK). The SDK part is integration layer INSIDE reef:
```python
# What should work:
reef = Reef(project_dir)
mediator = reef.spawn_skill("mediator", context=case_data)
reasoning = mediator.reason(scenario)  # Returns structured JSON
```

### Dependency 3: Evidence MCP Premature
**Problem**: You proposed Evidence MCP as Phase 1. But:
- You already have `.data/.processed/.vault` structure
- No evidence system exists yet
- MCP overhead (server lifecycle, protocol negotiation) for what a bash grep does

**Current State**:
- ~80GB case evidence spread across `.data/.processed`
- TF-IDF search is O(n) but works for index size < 10K docs
- No centralized index

**Risk Level**: MEDIUM - MCP is elegant but infrastructure-heavy

**Solution**: DO build evidence search this week:
```bash
# Phase 0 (QUICK): Bash prototype validates need
evidence_search() {
  find .data .processed .vault -name "*.txt" -o -name "*.md" | \
    xargs grep -l "$1" | wc -l
}

# Phase 1 (IF NEEDED): Then build MCP wrapper
# But only if Phase 0 proves slowness is real problem
```

### Dependency 4: Trenches System Requires Agent Maturity
**Problem**: You want "Free agents do grunt work" but:
- Your agents are SCORING agents (meta-level analysis)
- Not EXECUTOR agents (run tasks and report back)
- VoltAgent adoption means new ecosystem to learn
- claude-flow needs training data

**Current State**:
- pattern-hunter: Finds patterns ✓
- scorer: Ranks insights ✓
- scraper: Collects data ✓
- visionary: Generates novel perspectives ✓
- **None of these execute user tasks**

**Risk Level**: HIGH - Full swarm adoption this week impossible

**Solution**: Start with ONE trench (evidence indexing):
```python
# Week 1: Proof of concept
trench = Trench(
    name="evidence-indexer",
    task="Index all case evidence files",
    agent_type="executor",  # Not scorer/analyzer
    reporting="JSON summaries to .processed/"
)
```

### Dependency 5: Schema Collision (Polips vs Mediator Case Data)
**Problem**: Reef polips are tree structures. Mediator cases are graphs (parties, relationships, evidence, timeline).

Current Polip format:
```xml
<polip type="thread">
  <summary/>
  <content/>
  <related/>
</polip>
```

Mediator needs:
```xml
<case id="2022DCM6011">
  <parties>
    <party role="father"/>
    <party role="mother"/>
    <party role="child" age="6"/>
  </parties>
  <timeline/>
  <evidence/>
  <decisions/>
</case>
```

**Risk Level**: MEDIUM - They're orthogonal, not conflicting

**Solution**: Polips CAN be case containers:
```xml
<polip type="context" scope="project">
  <summary>Case 2022DCM6011 - Figueroa custody dispute</summary>
  <case-schema>
    <!-- Graph structure inside polip -->
  </case-schema>
</polip>
```

---

## MIGRATION RISK MATRIX

| Component | Current | Proposed | Migration Risk | Week 1 Feasible |
|-----------|---------|----------|-----------------|-----------------|
| Directory structure | Desktop scattered | ~/projects/ unified | HIGH (breaks paths) | ❌ NO |
| Mediator identity | Skill in custody-mediation | SDK in reef | MEDIUM (scope) | ✓ YES (bounded) |
| Evidence search | Manual grep | MCP server | MEDIUM (overkill?) | ⚠️ PARTIAL (Phase 0) |
| Trenches system | Doesn't exist | Full swarm | HIGH (new code) | ❌ NO |
| VoltAgent | Not evaluated | Adopt it | MEDIUM (learning curve) | ❌ NO |
| Reef + Mediator merge | Separate repos | Unified SDK | LOW (reef is lib) | ✓ YES |

---

## MVP (WEEK 1) - WHAT DELIVERS VALUE

### Tier 1: CORE (2-3 days)
These unlock everything else.

**1.1 Mediator SDK Boundary**
- Create `src/reef/mediator_skill.py` - Wraps existing /mediator logic
- Reef can spawn mediator skill with case context
- Returns structured reasoning (prediction, factors, framing)

```python
# Usage in session
reef_dir = Path("~/Desktop/custody-mediation")
reef = Reef(reef_dir)
mediator = reef.load_skill("mediator")
analysis = mediator.analyze(scenario="mother_blocks_visitation")
# Returns: {"court_view", "father_strengths", "concerns", "prediction_pct", "framing"}
```

**Blockers**: None (existing code can be wrapped)
**Files**: 1 new (mediator_skill.py, ~150 LOC wrapper)
**Testing**: 8 tests (scaffold case + assert output fields)
**Value**: Mediator becomes callable from reef ecosystem

**Time**: 4-6 hours

---

**1.2 Evidence Index Phase 0 (Bash Validation)**
- `~/.claude/scripts/evidence-search.sh` - Proves indexing need
- Measures: count of matches, search time, index size
- Generates metrics.json for Phase 1 decision

```bash
#!/bin/bash
# One-shot index build: find + metadata extraction
find .data .processed .vault -type f \( -name "*.txt" -o -name "*.md" \) | while read f; do
  echo "$(basename "$f")|$(wc -l < "$f")|$(stat -f%m "$f")"
done | sort > index.csv
```

**Blockers**: None
**Files**: 1 script (~50 lines)
**Testing**: Run on actual data, measure speed
**Value**: Data-driven decision on MCP investment

**Time**: 2 hours

---

### Tier 2: SCAFFOLDING (1-2 days)
These make the MVP production-ready.

**2.1 Organize ~/.claude/ for Multi-Project Use**
- Move custody-mediation-specific skills to project/.claude/skills/
- Keep global skills in ~/.claude/skills/ (38 existing)
- Create layer system: always → project → session

```
~/.claude/                    # Global harness
├── constraints/            # Project-agnostic rules
├── skills/                 # 38 global skills
├── agents/                 # 10 analyzers/scorers
├── hooks/                  # 12 lifecycle hooks
└── incubator/              # 5-phase pipeline

~/Desktop/custody-mediation/.claude/  # Project-specific
├── constraints/            # "Never share case data" etc
├── skills/mediator/        # Domain-specific (court framework)
├── contexts/               # Active work
├── decisions/              # ADRs for this project
└── facts/                  # Preserved case knowledge
```

**Blockers**: None (just reorganization)
**Files**: 0 new (move 15-20 existing)
**Testing**: Verify all ~/.claude/ paths still resolve
**Value**: Multi-project ready; custody-mediation doesn't pollute reef

**Time**: 3-4 hours (includes bash verification)

---

**2.2 Reef Mediator Skill Tests**
- 8 integration tests (schema input → structured output)
- Test cases: BACtrack evaluation, distance impact, support history
- Validates domain logic, not just syntax

```python
def test_bactrack_deleted_data_prediction():
    """Court can't restrict on missing data alone."""
    result = mediator.analyze(
        scenario="bactrack_clause_enforcement",
        context=case_data
    )
    assert result["prediction_pct"] < 20  # Low restriction likelihood
    assert "expungement" in result["supporting_factors"]
```

**Blockers**: mediator_skill.py exists
**Files**: 1 test file (~80 LOC)
**Testing**: pytest coverage > 80%
**Value**: Proves mediator outputs are reliable

**Time**: 3 hours

---

### Tier 3: OPTIONAL POLISH (Overflow)
If you finish Tier 2 before Friday.

**3.1 Evidence Search CLI Command**
```bash
reef evidence-search "DUI incident" --case 2022DCM6011
```
Wraps Phase 0 bash script in reef CLI interface.

**Time**: 2 hours
**Value**: Convenient UX for case research

---

## WHAT NOT TO BUILD THIS WEEK

### ❌ Full Trenches System
Why: Requires new executor agent framework. Too much.

Better: Build ONE trench (evidence indexer) as proof of concept in Week 2, not Week 1.

### ❌ VoltAgent Adoption
Why: New ecosystem, learning curve, no blocker for MVP.

Better: Use existing 10 agents first. Evaluate VoltAgent after seeing what you'd use it for.

### ❌ Evidence MCP (Yet)
Why: Phase 0 bash script might prove unnecessary.

Better: Phase 0 this week validates need. If searches are slow, THEN build MCP in Week 2.

### ❌ Directory Consolidation (Desktop → ~/projects/)
Why: Breaking change for 32 .claude directories.

Better: Establish symlinks instead. Full consolidation after mediator MVP ships.

### ❌ claude-flow Integration
Why: You haven't defined what "swarm orchestration" means yet.

Better: Once mediator + evidence MVP work, you'll know what orchestration you actually need.

---

## WEEK 1 ROADMAP (5 DAYS)

### Day 1 (Wed, Jan 15)
- **Morning**: Mediator SDK boundary design (whiteboard 30min, then code)
  - Create src/reef/mediator_skill.py (150 LOC wrapper)
  - Map existing /mediator logic to structured output schema
- **Afternoon**: Evidence search Phase 0 bash script (2 hours)
  - Validate search performance on actual .data/ files
  - Generate metrics.json for MCP decision

**Commit**: `feat: mediator skill wrapper + evidence search Phase 0`

---

### Day 2 (Thu, Jan 16)
- **Morning**: Reef tests for mediator skill (3 hours)
  - 8 test cases covering domain logic
  - Schema validation
  - Output field verification
- **Afternoon**: ~/.claude/ reorganization (3 hours)
  - Move custody-mediation skills to project dir
  - Layer system verification
  - Symlink validation if consolidating partially

**Commit**: `feat: mediator skill integration tests + project-local skills organization`

---

### Day 3 (Fri, Jan 17)
- **Morning**: Mediator skill CLI command (2 hours)
  - `reef mediator <scenario>` command in CLI
  - JSON output for scriptability
- **Afternoon**: Buffer / Polish / Docs
  - README for mediator skill
  - Usage examples for custody-mediation project
  - Update ROADMAP.md with what shipped

**Commit**: `feat: mediator skill CLI + documentation`

---

### Days 4-5 (Mon-Tue, Jan 20-21)
- If Tiers 1-2 done: Evidence CLI command
- If evidence CLI done: Write test suite for evidence search
- If ahead of schedule: Sketch trench proof-of-concept design (not implementation)

---

## HIDDEN DECISION POINTS (You'll Hit These)

### Decision 1: Mediator Output Format
**Question**: Structured JSON or freeform text with JSON envelope?

**Recommendation**: JSON schema with optional text. Enables both human reading + programmatic use.

```json
{
  "scenario": "bactrack_enforcement",
  "court_view": "Missing historical data creates evidentiary void, not proof",
  "prediction_pct": 18,
  "supporting_factors": ["expungement", "satp_completion", "8_years_elapsed"],
  "concerns": ["no_bactrack_data"],
  "mitigations": ["offer_current_testing"],
  "opposing_weaknesses": ["vague_safety_claims"],
  "framing": "Court-supervised redemption..."
}
```

---

### Decision 2: Evidence Index Structure
**Question**: Single CSV index or per-file metadata?

**Recommendation**: Single CSV (searchable) + per-file .json sidebar. Best of both.

```
index.csv:
filename,lines,mtime,category,tags

.data/statement-2022-01.md.meta.json:
{"filename": "...", "parties": ["father", "mother"], "date": "2022-01-15"}
```

---

### Decision 3: Skill Scope (Boundary)
**Question**: Can mediator skill be used from OTHER projects?

**Recommendation**: YES. Make it a "global" skill:
```
~/.claude/skills/mediator/              # Generic
└── Texas_Family_Code_153/

~/Desktop/custody-mediation/.claude/skills/  # Domain-specific
└── mediator-el-paso-context/          # Project-specific tweaks
```

---

## RISK SUMMARY

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Path breakage during migration | HIGH | CRITICAL | Use symlinks, not consolidate |
| Mediator scope creep | MEDIUM | MAJOR | Bound to skill-only for Week 1 |
| Evidence MCP investment wasted | MEDIUM | MINOR | Phase 0 validates first |
| Trenches adoption blocked | LOW | MAJOR | Not in MVP scope |
| Schema collision (polips vs cases) | LOW | MAJOR | Use polips as containers |

---

## SUCCESS CRITERIA (Week 1)

**Tier 1 Complete:**
- [ ] `reef mediator <scenario>` works with structured JSON output
- [ ] Evidence search script runs in < 2 seconds on full .data
- [ ] 8 mediator skill tests passing with > 80% coverage

**Tier 2 Complete:**
- [ ] ~/.claude/ organized (global vs project-local)
- [ ] All existing skills/agents still resolve correctly
- [ ] Symlinks verified (no broken paths)

**Overflow (if done):**
- [ ] `reef evidence-search` CLI command exists
- [ ] README.md documents mediator skill + evidence search
- [ ] No breaking changes to existing reef functionality

---

## ACTIONABLE NEXT STEPS (Right Now)

1. **Pick Day 1 morning task**: Mediator SDK design (30 min design, then code)
2. **Create branch**: `feat/mediator-sdk-week1`
3. **Establish working agreement**:
   - Mediator is a SKILL (not swarm agent)
   - Evidence Phase 0 is bash validation only
   - No directory consolidation (symlinks instead)
   - Deliver working mediator + evidence by Friday EOD

4. **Before coding**: Clarify mediator output schema with one example scenario

---

**Status**: You're 80% of the way there. Don't buy new infrastructure. Integrate what exists.
