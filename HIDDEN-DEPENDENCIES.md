# Hidden Dependencies: Technical Deep Dive

**Purpose**: What will break silently if you build the proposal incorrectly?

---

## DEPENDENCY MAP

```
Directory Consolidation
├─ Breaks: .claude/ relative paths in 32 directories
├─ Breaks: [[wiki-links]] that assume Desktop layout
├─ Breaks: .data/.processed/.vault absolute references
├─ Breaks: Hook file discovery (find .claude/hooks)
└─ Breaks: Symlink assumptions in custody-mediation

Mediator Identity Crisis
├─ Is it a skill (/mediator command)?
├─ Is it a Python SDK (import mediator)?
├─ Is it a Reef skill (reef.load_skill("mediator"))?
├─ Is it a swarm orchestrator (trenches)?
└─ Is it a Claude Code plugin (hooks + commands)?
→ Conflicts: Unclear import paths + duplicate logic

Evidence MCP Premature
├─ Requires: MCP server lifecycle management
├─ Requires: Protocol handlers for case document types
├─ Requires: Schema mapping (document → polip)
├─ But: Bash grep solves 80% of need
├─ But: TF-IDF already works for index < 10K docs
└─ But: No proof MCP overhead justified

Trenches System Requires Agent Maturity
├─ Current agents: Meta-level (scoring, pattern detection)
├─ Required agents: Executor agents (run tasks, report)
├─ Gap: You can score tasks, not execute them
├─ Gap: No task queue, no result pipeline
├─ Gap: No failure handling / rollback
└─ Blocking: Full swarm adoption impossible this week

Schema Collision (Polips vs Case Data)
├─ Polips: Tree structure (type, summary, content, related)
├─ Cases: Graph structure (parties, evidence, timeline, decisions)
├─ Question: Are polips containers for case data?
├─ Question: Does reef need "case" type?
├─ Question: How do case graphs evolve?
└─ Risk: Schema mismatch if not planned
```

---

## LAYER 1: PATH RESOLUTION SYSTEM

### Current Architecture

**Home-level skeleton** (~/.claude/):
```
skills/
  ├── task-genome.md
  ├── task-templates.md
  ├── web-scraper.md
  └── ... (38 total)

agents/
  ├── pattern-hunter.md
  ├── scorer.md
  └── ... (10 total)

hooks/
  ├── incubator_inject.py
  ├── session-start.py
  └── ... (12 total)

incubator/
  ├── promoted/
  ├── scored/
  └── patterns/

scripts/
  ├── incubator-collect.py
  ├── incubator-score.py
  └── ...
```

**Project-level skeleton** (~/Desktop/custody-mediation/.claude/):
```
constraints/
  ├── case-confidentiality.blob.xml
  └── ...

decisions/
  ├── mediator-sdk-design.blob.xml
  └── ...

facts/
  ├── case-2022DCM6011.blob.xml
  └── ...

contexts/
  ├── current-session.blob.xml
  └── ...

skills/
  ├── mediator-perspective.md  ← DOMAIN-SPECIFIC
  └── ...
```

**Session skeleton** (ephemeral polips created per-session):
```
.claude/
  ├── context.blob.xml          ← Session memory
  ├── threads/                  ← Active work
  ├── deposits/                 ├── decision-*.blob.xml
  └── fossils/                  └── archived-*.blob.xml
```

### The Three-Layer Problem

**Layer 0: Global Rules** (~/.claude/constraints/)
```xml
<constraint type="bedrock" scope="always">
  <summary>Never ship PII to public logs</summary>
  <applies-to-all-projects>true</applies-to-all-projects>
</constraint>
```

**Layer 1: Project Rules** (~/Desktop/custody-mediation/.claude/constraints/)
```xml
<constraint type="bedrock" scope="project">
  <summary>Case documents are attorney-client privileged</summary>
  <applies-to>custody-mediation</applies-to>
</constraint>
```

**Layer 2: Session Memory** (.claude/context.blob.xml)
```xml
<context scope="session">
  <summary>Current analysis of mother's gatekeeping behaviors</summary>
  <references>
    [[case-2022DCM6011]]
    [[constraint:project-confidentiality]]
  </references>
</context>
```

### What Breaks on Consolidation

**Current state**: Paths work because relative .claude/ structure is consistent:
```bash
# This works:
grep -r "best_interest" ~/.claude/constraints/
find ~/Desktop/custody-mediation/.claude -name "*.blob.xml"
```

**After consolidation to ~/projects/**:
```bash
# These break:
~/projects/custody-mediation/.claude/  # Old Desktop paths no longer exist
~/.claude/constraints/                  # Project-specific constraints missing

# Symlinks needed:
ln -s ~/Desktop/custody-mediation ~/projects/custody-mediation
# OR path rewriting in all 32 directories
```

**Silent failures happen in**:
- `[[wiki-links]]` - They resolve to non-existent polips
- Hook discovery - find commands hit wrong paths
- Skill importing - Python doesn't follow symlinks transparently
- Incubator surfacing - Looks for promoted/ in old location

### Safe Migration Path

**Week 1-2 (This Week)**:
```bash
# Setup
mkdir -p ~/projects
ln -s ~/Desktop/custody-mediation ~/projects/custody-mediation

# In-place migration (no file moves)
# .claude/ stays at ~/Desktop/custody-mediation/.claude/
# But reef commands work with both paths:
reef init ~/projects/custody-mediation
reef index --path ~/projects/custody-mediation
```

**Week 3-4 (After MVP)**:
```bash
# Physical migration (after all polips updated)
mv ~/Desktop/custody-mediation/.claude ~/projects/custody-mediation/
# Update all wiki-links
grep -r "Desktop/custody" ~/.claude | while read line; do
  sed 's|Desktop/custody|projects/custody|g'
done
```

---

## LAYER 2: MEDIATOR IDENTITY RESOLUTION

### What You Said vs What You Need

**Proposal Statement**: "Mediator as SKILL, not agent"

**What That Actually Means**:
1. `/mediator` is a Claude Code **slash command** (exists in custody-mediation)
2. OR `reef.load_skill("mediator")` is **Python callable** (needs wrapping)
3. OR `reef mediator <scenario>` is a **CLI subcommand** (can be added to cli.py)
4. OR none of the above, and mediator is a **behavior layer** (strategies, not interfaces)

### Current State

**In custody-mediation**:
```
.claude/skills/mediator-perspective.md
  - user-invocable: true
  - Framework: Texas Family Code 153.002
  - Output: Markdown with embedded JSON sections
```

This is a **human-readable skill** (Claude interprets it as guidance).

**In reef/src/mediator/**:
```python
# __init__.py
__version__ = "0.1.0"

# guards/pii.py
# Semantic PII detector (stub)
```

This is a **library seed** (code that detects PII in cases).

**The Gap**: They're not connected.

### Three Integration Architectures

#### Architecture A: Skill Wrapper (SIMPLEST)
```python
# src/reef/mediator_skill.py

class MediatorSkill:
    """Wraps custody-mediation/.claude/skills/mediator-perspective.md"""

    def __init__(self, reef: Reef):
        self.reef = reef
        self.domain_skill = reef.load_file(
            ".claude/skills/mediator-perspective.md"
        )

    def analyze(self, scenario: str, context: dict) -> dict:
        # Call Claude with domain_skill as context
        # Return structured JSON from Claude's response
        prompt = f"""
        Using the Texas Family Code framework:
        {self.domain_skill}

        Analyze this scenario: {scenario}

        Return JSON with keys:
        - court_view
        - prediction_pct
        - supporting_factors
        - concerns
        """
        response = self.call_claude(prompt, context)
        return self.parse_json(response)
```

**Pros**:
- Minimal code (150 LOC)
- Reuses existing /mediator logic
- Works with current custody-mediation structure

**Cons**:
- Requires Claude API call per analyze
- Not fully offline
- Doesn't use mediator/guards/pii.py detector

#### Architecture B: SDK Library (MORE POWERFUL)
```python
# src/reef/mediator/__init__.py

from .guards.pii import SemanticPIIDetector
from .strategies import TexasFamilyCodeStrategy

class MediatorSDK:
    """Full mediator reasoning engine"""

    def __init__(self, strategy: str = "texas_family_code"):
        self.pii_detector = SemanticPIIDetector()
        self.strategy = TexasFamilyCodeStrategy()

    def analyze_case(self, case_polip: Polip) -> AnalysisResult:
        # Validate no PII leakage
        self.pii_detector.scan(case_polip)

        # Run strategy reasoning
        result = self.strategy.analyze(case_polip)
        return result
```

**Pros**:
- Offline (no Claude call needed)
- Reusable across projects
- Scales to multiple strategies

**Cons**:
- More code to write (500+ LOC)
- Requires defining strategy interface
- Week 2+ timeline

#### Architecture C: Hybrid (RECOMMENDED FOR WEEK 1)
```python
# src/reef/mediator_skill.py

class MediatorSkill:
    """Hybrid: Uses local logic + Claude as fallback"""

    def __init__(self, reef: Reef):
        self.reef = reef
        self.pii_detector = SemanticPIIDetector()
        self.domain_skill_path = ".claude/skills/mediator-perspective.md"

    def analyze(self, scenario: str, context: dict) -> dict:
        # Quick local analysis (if implemented)
        local_result = self._analyze_locally(scenario, context)

        # If confidence too low, enhance with Claude
        if local_result.get("confidence", 0) < 0.7:
            enhanced = self._enhance_with_claude(scenario, context)
            return {**local_result, **enhanced}

        return local_result

    def _analyze_locally(self, scenario: str, context: dict) -> dict:
        # Implement key factors:
        # - Age of past conduct
        # - Statutory thresholds
        # - Missing data implications
        # Returns partial result
        pass

    def _enhance_with_claude(self, scenario: str, context: dict) -> dict:
        # Use domain skill as context
        # Return structured JSON
        pass
```

**Pros**:
- Works this week (Architecture A + stub B)
- Offline for common cases
- Extensible to full SDK later

**Cons**:
- Two code paths to maintain
- Requires defining "local vs enhanced" boundary

### Recommendation for Week 1

**Use Architecture A (Wrapper)** because:
1. You have working /mediator skill already
2. Minimal new code (150 LOC)
3. Unblocks mediator-skill integration tests
4. You can graduate to Architecture B or C later

**But structure it so you CAN transition**:
```python
# Week 1
class MediatorSkill:
    def analyze(self, scenario, context):
        return self._call_claude(scenario, context)

# Week 2
class MediatorSkill:
    def analyze(self, scenario, context):
        local = self._analyze_locally(scenario, context)
        if local: return local
        return self._call_claude(scenario, context)

# Week 3+
class MediatorSDK:
    # Full offline implementation
```

---

## LAYER 3: EVIDENCE INDEXING ARCHITECTURE

### Problem Statement

**Current State**:
- ~80GB evidence across .data/, .processed/, .vault/
- No centralized index
- Search is manual grep
- No metadata extraction

**Proposed**: Evidence MCP

**Reality Check**:
- MCP overhead is 200+ LOC for server lifecycle
- You need to prove search slowness first
- 80% of need solved by bash script

### Three Phasing Strategies

#### Phase 0: Bash Validation (THIS WEEK, 2 hours)
```bash
#!/bin/bash
# .claude/scripts/evidence-search.sh

INDEX_DIR=".evidence-index"
mkdir -p "$INDEX_DIR"

echo "Building evidence index..."
START=$(date +%s)

find .data .processed .vault -type f \
  \( -name "*.txt" -o -name "*.md" -o -name "*.pdf" \) \
  -exec sh -c '
    FILE="$1"
    LINES=$(wc -l < "$FILE" 2>/dev/null || echo 0)
    SIZE=$(stat -f%z "$FILE" 2>/dev/null || du -b "$FILE" | cut -f1)
    MTIME=$(stat -f%m "$FILE" 2>/dev/null)

    printf "%s|%d|%d|%s\n" \
      "$(basename "$FILE")" "$LINES" "$SIZE" "$MTIME"
  ' _ {} \; | sort > "$INDEX_DIR/index.csv"

END=$(date +%s)
ELAPSED=$((END - START))

echo "Index built in ${ELAPSED}s"
echo "Total files: $(wc -l < $INDEX_DIR/index.csv)"

# Search function
search() {
  QUERY="$1"
  echo "Searching for: $QUERY"
  grep -r "$QUERY" .data .processed .vault 2>/dev/null | \
    awk -F: '{print $1}' | sort | uniq -c
}

# Test performance
time search "DUI incident"
time search "best interest"
time search "visitation schedule"
```

**Output**: `index.csv` + `metrics.json`
```json
{
  "total_files": 1247,
  "total_size_gb": 78,
  "build_time_s": 45,
  "search_latency_ms": {
    "simple": 120,
    "complex": 450
  },
  "recommendation": "grep sufficient for now"
}
```

**Decision rule**:
- If search < 500ms: Skip MCP, use bash
- If search > 2s: Implement Phase 1 (MCP) or Phase 1b (TF-IDF)

#### Phase 1: MCP Server (IF NEEDED)
```python
# src/reef/evidence_mcp.py

from mcp.server import MCP_SERVER

@MCP_SERVER.tool()
def search_evidence(query: str, case_id: str = None):
    """Search case evidence documents"""
    # Read pre-built index
    # Filter by case_id if provided
    # Return results with metadata
    pass

@MCP_SERVER.resource()
def document_content(path: str):
    """Retrieve full document content"""
    # Security check: path must be in .vault
    # Return document with PII markers
    pass

@MCP_SERVER.notification()
def index_changed():
    """Notify when evidence index updates"""
    # Triggered by cron or file watcher
    # Clients re-query
    pass
```

**Pros**: Decoupled from reef, available to other tools
**Cons**: 200+ LOC, server lifecycle, protocol handlers
**Timeline**: Week 2 if Phase 0 proves need

#### Phase 1b: TF-IDF Search (ALTERNATIVE)
```python
# Use reef's existing TF-IDF logic

from reef.blob import Glob

glob = Glob(project_dir)
evidence_docs = glob.load_all_polips(filter_dir=".vault")
results = glob.search("DUI incident", limit=20)
```

**Pros**: 50 LOC, uses existing code, works offline
**Cons**: Requires converting documents to polips first
**Timeline**: Week 1.5 if needed

### Recommendation for Week 1

**Build Phase 0 ONLY** (bash validation):
1. Prove search performance is acceptable
2. Decide MCP investment based on data
3. Document metrics.json for Phase 1 planning

This takes 2 hours and de-risks the MCP choice.

---

## LAYER 4: TRENCHES SYSTEM REQUIREMENTS

### What "Trenches" Actually Means

**Proposed**: "Free agents do grunt work"

**Reality**: You need an executor framework.

### Current Agent Architecture

**Existing agents**: Meta-level (analyze, score, pattern-detect)

```python
# Example: scorer agent
class Scorer:
    def score(self, insight: Insight) -> float:
        # Returns 0.0 - 10.0
        return composite_score
```

**What you'd need for trenches**: Executor agents

```python
# Example: executor agent
class EvidenceIndexer:
    def execute(self, task: Task) -> TaskResult:
        # Runs to completion
        # Reports results
        # Handles errors
        return TaskResult(status="success", output=data)
```

### Gap Analysis

| Capability | Scorer Agent | Executor Agent | Blocker |
|-----------|---|---|---|
| Take input | ✓ | ✓ | - |
| Run logic | ✓ | ✓ | - |
| Return output | ✓ | ✓ | - |
| Track progress | ✗ | ✓ | **YES** |
| Handle errors | ✗ | ✓ | **YES** |
| Rollback changes | ✗ | ✓ | **YES** |
| Pipeline to next | ✗ | ✓ | **YES** |
| Timeout/cancel | ✗ | ✓ | **YES** |

### Why Trenches Can't Ship This Week

1. **No task queue system** - You can't queue tasks
2. **No result pipeline** - Results can't feed into next step
3. **No error recovery** - Failed tasks block swarm
4. **No timeout handling** - Runaway tasks crash swarm
5. **VoltAgent integration** - New ecosystem to learn

**Minimum code for executor framework**: 800+ LOC
- Task queue (100 LOC)
- Executor base class (150 LOC)
- Error handling (200 LOC)
- Result pipeline (150 LOC)
- Tests (200 LOC)

### How to Plan Trenches for Week 2

**Proof of Concept**: Single trench
```python
class EvidenceIndexerTrench:
    """Execute evidence indexing as standalone task"""

    def __init__(self):
        self.task_queue = []
        self.results = []

    def queue_index(self, case_id: str):
        self.task_queue.append({
            "task": "index_evidence",
            "case_id": case_id,
            "status": "pending"
        })

    def run_all(self):
        for task in self.task_queue:
            try:
                result = self._execute_index(task)
                self.results.append(result)
            except Exception as e:
                self._handle_error(task, e)

    def _execute_index(self, task):
        # Build index for case_id
        # Save to .processed/
        return {"task_id": task["id"], "status": "success"}
```

This is 150 LOC and proves the executor pattern. Full swarm comes later.

---

## LAYER 5: SCHEMA RESOLUTION (Polips vs Case Data)

### Current Polip Schema

```xml
<polip type="thread|decision|constraint|fact|context">
  <id/>
  <type/>
  <scope>always|project|session</scope>
  <summary/>
  <content/>
  <related>
    <link>[[polip-name]]</link>
  </related>
  <metadata>
    <created/>
    <updated/>
    <access_count/>
  </metadata>
</polip>
```

**Properties**:
- Tree structure (polip contains content)
- Type determines lifecycle
- Scope determines visibility
- Links are wiki-style text references

### Case Data Graph

```
Case 2022DCM6011
├─ Parties
│  ├─ Father (Enterprise, AL)
│  ├─ Mother (El Paso, TX)
│  └─ Child (Levi, age 6)
├─ Timeline
│  ├─ 2016: DUI incident
│  ├─ 2020: Divorce + arrest
│  ├─ 2022: Case filed
│  └─ 2026: Current
├─ Evidence
│  ├─ SATP completion (expungement)
│  ├─ Child support records
│  ├─ Communications logs
│  └─ BACtrack clause (deleted)
└─ Decisions
   ├─ Initial decree
   ├─ Current modification attempt
   └─ Mediator recommendation
```

**Properties**:
- Graph structure (nodes + edges)
- Temporal evolution (states over time)
- Multi-party relationships
- Mutable evidence

### Collision Point: Polips are append-only, Cases are mutable

**Polip philosophy**:
- Content is captured at spawn time
- Edits create new versions (lineage tracking)
- Deletion is rare (archive instead)

**Case philosophy**:
- Evidence emerges over time
- Parties update positions
- Timeline shifts as new facts emerge

### Three Resolution Approaches

#### Approach A: Cases as Polip Collections
```xml
<polip type="context" scope="project">
  <id>case-2022DCM6011</id>
  <case-schema>
    <parties>
      <polip-ref id="party-father"/>
      <polip-ref id="party-mother"/>
      <polip-ref id="party-child"/>
    </parties>
    <evidence>
      <polip-ref id="evidence-satp-2020"/>
      <polip-ref id="evidence-dui-2016"/>
    </evidence>
    <timeline>
      <!-- Ordered by date, references other polips -->
    </timeline>
  </case-schema>
</polip>
```

**Pros**: Each party/evidence is a separate polip
**Cons**: Links are brittle, lots of small polips
**Use case**: Highly collaborative (many agents touch case)

#### Approach B: Cases as Polip Content
```xml
<polip type="decision" scope="project">
  <id>case-2022DCM6011</id>
  <summary>Custody modification case - Father's long-distance access</summary>
  <content>
## Case Metadata
- Case ID: 2022DCM6011
- Court: El Paso 383rd District
- Jurisdiction: Texas Family Code

## Parties
- Father: [Enterprise, AL]
- Mother: [El Paso, TX]
- Child: Levi (age 6)

## Key Events
- 2016-12: DUI (now 10 years old)
- 2020-06: Divorce filed (now 6 years old)
- 2020-12: Expungement via SATP
- 2022-01: Modification filed

## Evidence
- SATP completion: [Court record]
- Child support compliance: $15,138.78 paid (May 2025 - Jan 2026)
- BACtrack data: Deleted May 2025
  </content>
</polip>
```

**Pros**: Single source of truth, evolves over time
**Cons**: Less queryable, harder for agents to extract data
**Use case**: Primarily human-curated (legal team uses this)

#### Approach C: Hybrid (RECOMMENDED)
```xml
<polip type="decision" scope="project">
  <id>case-2022DCM6011</id>
  <summary>Custody modification - El Paso 383rd District</summary>
  <case-ref>
    <!-- Structured metadata for parsing -->
    <court>El Paso 383rd District</court>
    <jurisdiction>Texas Family Code</jurisdiction>
    <parties>
      <party role="father" location="Enterprise, AL" id="party-father"/>
      <party role="mother" location="El Paso, TX" id="party-mother"/>
      <party role="child" name="Levi" age="6" id="party-child"/>
    </parties>
    <timeline>
      <event date="2016-12-15" type="incident">DUI arrest</event>
      <event date="2020-06-01" type="legal">Divorce filed</event>
    </timeline>
  </case-ref>
  <content>
    <!-- Human-readable narrative -->
    Father...
  </content>
  <evidence>
    <doc id="satp-2020" type="court-record">SATP completion</doc>
    <doc id="bactrack-data" type="monitoring">Deleted May 2025</doc>
  </evidence>
  <related>
    [[mediator-perspective-framework]]
    [[texas-family-code-153]]
  </related>
</polip>
```

**Pros**: Queryable metadata + human narrative + extensibility
**Cons**: Slightly more complex schema
**Use case**: Both human + AI agents can work with it

### Recommendation for Week 1

**Use Approach C (Hybrid)** because:
1. Supports both human reading + machine parsing
2. No new polip type needed (just richer "decision" type)
3. Mediator skill can extract `case-ref/parties/timeline`
4. Evidence search can query `evidence/doc` nodes
5. Extensible to full case graph later

**Implementation**:
1. Add `case-ref` schema to BUILTIN_TEMPLATES (50 LOC)
2. Create example case-2022DCM6011.blob.xml
3. Add parser: `case_polip.extract_parties()` → dict
4. Mediator skill can use extracted data for analysis

---

## RISK SCORECARD

| Dependency | If Ignored This Week | If Mishandled | Mitigation Cost |
|-----------|---|---|---|
| Path resolution | Silent wiki-link breakage | Can't migrate later | 4h (test suite) |
| Mediator identity | Duplicate code in 3 places | Can't integrate cleanly | 6h (refactoring) |
| Evidence indexing | Buy MCP too early | Optimization problem | 16h (MCP time sunk) |
| Trenches executor | Can't scale tasks | Swarm breaks under load | 40h (framework) |
| Case schema | Polips don't fit case data | Can't extract case facts | 8h (schema redesign) |

**Total mitigation cost if ALL go wrong**: 74 hours (2 weeks)
**Total prevention cost if addressed now**: 24 hours (this week)

---

## DECISION MATRIX FOR WEEK 1

| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|-----------------|
| **Directory consolidation** | Consolidate (Desktop → ~/projects) | Use symlinks | **Use symlinks** (lower risk) |
| **Mediator architecture** | Wrapper (Architecture A) | SDK (Architecture B) | **Wrapper A** (faster) |
| **Evidence search** | Build MCP | Build Phase 0 bash | **Phase 0 bash** (validate first) |
| **Trenches execution** | Full swarm | Single proof-of-concept | **Skip this week** (too big) |
| **Case schema** | Polip collections | Polip content | **Hybrid approach C** (both) |

---

*Last updated: 2026-01-15*
*Confidence: 85% (based on 4500 LOC existing + 3 week context)*
