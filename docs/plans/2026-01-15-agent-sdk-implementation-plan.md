# Reef Agent SDK Implementation Plan

**Date:** 2026-01-15
**Status:** Active / Executing
**Scope:** Full agent infrastructure localized to reef

---

## Executive Summary

Transform reef from a passive memory system into an **active agent infrastructure** that:
1. Houses its own localized Agent SDK with orchestration, strategy, and validation
2. Exposes reef operations via MCP for tool integration
3. Hotloads skills (global + project-local) for agent work
4. Distributes grunt work to free workers (Groq, Ollama, Gemini)
5. Bakes in all session insights (organic growth, biological metaphors, safety guards)

---

## Phase 0: Foundation Restructure

**Goal:** Reorganize reef for agent SDK housing

### Directory Structure (Target)

```
reef/
├── src/
│   ├── reef/
│   │   ├── __init__.py
│   │   ├── blob.py              # Core Polip/Reef classes (exists)
│   │   ├── cli.py               # CLI commands (exists)
│   │   ├── mcp/                  # NEW: MCP server
│   │   │   ├── __init__.py
│   │   │   ├── server.py         # MCP server implementation
│   │   │   └── handlers.py       # Tool handlers
│   │   ├── agents/               # NEW: Localized agents
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py   # Main coordinator
│   │   │   ├── strategist.py     # Strategic decisions
│   │   │   ├── validator.py      # Karen-style validation
│   │   │   ├── researcher.py     # Web/code research
│   │   │   └── worker.py         # External model dispatch
│   │   ├── skills/               # NEW: Hotloadable skills
│   │   │   ├── __init__.py
│   │   │   ├── loader.py         # Skill discovery/loading
│   │   │   └── registry.py       # Skill registration
│   │   ├── workers/              # NEW: External model workers
│   │   │   ├── __init__.py
│   │   │   ├── dispatcher.py     # Route to groq/ollama/gemini
│   │   │   ├── groq.py           # Groq client
│   │   │   ├── ollama.py         # Ollama client
│   │   │   └── gemini.py         # Gemini client
│   │   └── safety/               # NEW: Safety infrastructure
│   │       ├── __init__.py
│   │       ├── guards.py         # Pruning safeguards
│   │       ├── audit.py          # Audit trail
│   │       └── undo.py           # Undo buffer
│   └── mediator/                 # Existing PII guards
├── .claude/
│   ├── agents/                   # NEW: Project-local agent definitions
│   │   ├── reef-orchestrator.md
│   │   ├── reef-strategist.md
│   │   └── reef-validator.md
│   ├── skills/                   # NEW: Project-local skills
│   │   ├── index.json
│   │   └── polip-ops.md
│   └── workers/                  # NEW: Worker configs
│       ├── config.yaml
│       └── templates/
└── tests/
    ├── test_agents.py
    ├── test_mcp.py
    ├── test_workers.py
    └── test_safety.py
```

### Tasks

- [ ] Create directory structure
- [ ] Move/create __init__.py files
- [ ] Update pyproject.toml with new modules
- [ ] Verify existing tests still pass

### Test Gate
```bash
uv run pytest -x  # All existing tests pass
```

---

## Phase 1: Safety Infrastructure (P0 Critical)

**Goal:** Implement critical safety guards before any automation

### 1.1 Pruning Safeguards (`src/reef/safety/guards.py`)

```python
class PruningSafeguards:
    """Prevent catastrophic data loss from automated pruning."""

    MAX_DELETION_RATE = 0.25  # Halt if >25% marked for deletion
    PROTECTED_SCOPES = ['always']  # Never auto-prune

    def check_deletion_rate(self, candidates: list, total: int) -> bool:
        """Halt if deletion rate exceeds threshold."""

    def is_protected(self, polip: Polip) -> bool:
        """Check if polip is immune to auto-pruning."""

    def dry_run(self, operation: str, targets: list) -> DryRunReport:
        """Preview operation without executing."""
```

### 1.2 Audit Trail (`src/reef/safety/audit.py`)

```python
class AuditLog:
    """Track all automatic operations for debugging."""

    def log_operation(self, op_type: str, polip_id: str, reason: str):
        """Log operation to .claude/audit/"""

    def query(self, since: datetime, op_type: Optional[str]) -> list:
        """Query audit log."""
```

### 1.3 Undo Buffer (`src/reef/safety/undo.py`)

```python
class UndoBuffer:
    """Quarantine deleted polips for recovery."""

    QUARANTINE_DAYS = 7

    def quarantine(self, polip: Polip):
        """Move to .claude/quarantine/ instead of deleting."""

    def restore(self, polip_id: str):
        """Restore from quarantine."""

    def expire_old(self):
        """Permanently delete polips older than QUARANTINE_DAYS."""
```

### CLI Commands

```bash
reef sync --dry-run           # Preview what would be pruned
reef audit                    # View recent automatic operations
reef audit --since 7d         # Last 7 days
reef undo <polip-id>          # Restore from quarantine
reef undo --list              # List quarantined polips
```

### Test Gate
```bash
uv run pytest tests/test_safety.py -v
# Test cases:
# - test_deletion_rate_halt
# - test_protected_scope_immunity
# - test_dry_run_accuracy
# - test_audit_logging
# - test_quarantine_restore
# - test_quarantine_expiry
```

---

## Phase 2: External Worker Infrastructure

**Goal:** Enable work distribution to free models (Groq, Ollama, Gemini)

### 2.1 Worker Dispatcher (`src/reef/workers/dispatcher.py`)

```python
class WorkerDispatcher:
    """Route tasks to appropriate external models."""

    ROUTING_RULES = {
        'search': ['groq', 'gemini'],      # Fast, external-ok
        'summarize': ['ollama', 'groq'],    # Local preferred
        'validate': ['claude'],             # Requires judgment
        'extract': ['groq', 'gemini'],      # Structured extraction
    }

    def dispatch(self, task_type: str, prompt: str,
                 sensitivity: str = 'low') -> WorkerResult:
        """Route task to best available worker."""

    def get_available_workers(self) -> list:
        """Discover available external models."""
```

### 2.2 Worker Clients

**Groq Client (`src/reef/workers/groq.py`)**
```python
class GroqWorker:
    """Groq API client for fast inference."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GROQ_API_KEY')

    def complete(self, prompt: str, model: str = 'llama-3.3-70b-versatile') -> str:
        """Send completion request to Groq."""
```

**Ollama Client (`src/reef/workers/ollama.py`)**
```python
class OllamaWorker:
    """Ollama local model client."""

    def __init__(self, host: str = 'http://localhost:11434'):
        self.host = host

    def complete(self, prompt: str, model: str = 'llama3.2') -> str:
        """Send completion request to local Ollama."""

    def is_available(self) -> bool:
        """Check if Ollama is running."""
```

**Gemini Client (`src/reef/workers/gemini.py`)**
```python
class GeminiWorker:
    """Google Gemini API client."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

    def complete(self, prompt: str, model: str = 'gemini-2.0-flash') -> str:
        """Send completion request to Gemini."""
```

### 2.3 Worker Configuration (`.claude/workers/config.yaml`)

```yaml
workers:
  groq:
    enabled: true
    api_key_env: GROQ_API_KEY
    default_model: llama-3.3-70b-versatile
    rate_limit: 30/min

  ollama:
    enabled: true
    host: http://localhost:11434
    default_model: llama3.2

  gemini:
    enabled: true
    api_key_env: GEMINI_API_KEY
    default_model: gemini-2.0-flash
    rate_limit: 60/min

sensitivity_routing:
  pii: [claude]           # Never send PII to external
  legal: [claude]         # Legal requires judgment
  external-ok: [groq, ollama, gemini]

task_routing:
  search: [groq, gemini]
  summarize: [ollama, groq]
  extract: [groq, gemini]
  validate: [claude]
  synthesize: [claude]
```

### CLI Commands

```bash
reef workers status           # Show available workers
reef workers test groq        # Test Groq connectivity
reef workers run "summarize this" --worker groq
```

### Test Gate
```bash
uv run pytest tests/test_workers.py -v
# Test cases:
# - test_dispatcher_routing
# - test_groq_client (mocked)
# - test_ollama_client (mocked)
# - test_gemini_client (mocked)
# - test_sensitivity_enforcement
# - test_fallback_on_failure
```

---

## Phase 3: MCP Server Implementation

**Goal:** Expose reef operations via Model Context Protocol

### 3.1 MCP Server (`src/reef/mcp/server.py`)

```python
from mcp.server import Server
from mcp.types import Tool, Resource

class ReefMCPServer:
    """MCP server exposing reef operations."""

    def __init__(self, project_dir: Path):
        self.glob = Glob(project_dir)
        self.server = Server("reef")
        self._register_tools()
        self._register_resources()

    def _register_tools(self):
        """Register reef operations as MCP tools."""

        @self.server.tool()
        def reef_surface(query: str, limit: int = 5) -> list:
            """Surface relevant polips based on query."""
            return self.glob.search(query, limit=limit)

        @self.server.tool()
        def reef_sprout(type: str, summary: str, content: str = "") -> dict:
            """Create a new polip."""

        @self.server.tool()
        def reef_health() -> dict:
            """Get reef health metrics."""

        @self.server.tool()
        def reef_sync(dry_run: bool = True) -> dict:
            """Sync and optionally prune reef."""

    def _register_resources(self):
        """Register reef resources."""

        @self.server.resource("reef://polips")
        def list_polips() -> list:
            """List all polips with metadata."""

        @self.server.resource("reef://polip/{id}")
        def get_polip(id: str) -> dict:
            """Get full polip content."""
```

### 3.2 MCP Configuration

**Project `.mcp.json`**
```json
{
  "mcpServers": {
    "reef": {
      "command": "uv",
      "args": ["run", "python", "-m", "reef.mcp.server"],
      "env": {
        "REEF_PROJECT_DIR": "."
      }
    }
  }
}
```

### 3.3 Tool List

| Tool | Description | Parameters |
|------|-------------|------------|
| `reef_surface` | Search and surface relevant polips | query, limit |
| `reef_sprout` | Create new polip | type, summary, content, files |
| `reef_sink` | Archive polip to fossil layer | polip_id, reason |
| `reef_health` | Get reef vitality metrics | - |
| `reef_sync` | Check integrity, optionally prune | dry_run, fix |
| `reef_index` | Search polip index | query, type, scope |
| `reef_audit` | Query audit log | since, op_type |
| `reef_undo` | Restore quarantined polip | polip_id |

### Test Gate
```bash
uv run pytest tests/test_mcp.py -v
# Test cases:
# - test_server_initialization
# - test_surface_tool
# - test_sprout_tool
# - test_health_tool
# - test_resource_listing
# - test_mcp_protocol_compliance
```

---

## Phase 4: Agent Infrastructure

**Goal:** Implement reef-native agents with orchestration

### 4.1 Agent Orchestrator (`src/reef/agents/orchestrator.py`)

```python
class ReefOrchestrator:
    """Coordinates reef agent operations."""

    def __init__(self, glob: Glob, dispatcher: WorkerDispatcher):
        self.glob = glob
        self.dispatcher = dispatcher
        self.strategist = ReefStrategist(glob)
        self.validator = ReefValidator(glob)

    def execute_task(self, task: str, context: dict) -> TaskResult:
        """
        Main entry point for agent work.

        1. Strategist decomposes task
        2. Dispatcher routes sub-tasks to workers
        3. Orchestrator aggregates results
        4. Validator verifies output
        """

    def decompose(self, task: str) -> list[SubTask]:
        """Use strategist to break down complex task."""

    def aggregate(self, results: list[WorkerResult]) -> dict:
        """Combine worker outputs."""

    def validate(self, output: dict) -> ValidationResult:
        """Use validator to verify output quality."""
```

### 4.2 Agent Strategist (`src/reef/agents/strategist.py`)

```python
class ReefStrategist:
    """Strategic task decomposition and planning."""

    def analyze_task(self, task: str) -> TaskAnalysis:
        """
        Analyze task complexity and requirements.

        Returns:
            - complexity: low | medium | high
            - sub_tasks: list of decomposed tasks
            - model_requirements: which model tiers needed
            - sensitivity: pii | legal | external-ok
        """

    def route_to_workers(self, sub_tasks: list) -> dict[str, list]:
        """Assign sub-tasks to appropriate workers."""

    def plan_execution(self, analysis: TaskAnalysis) -> ExecutionPlan:
        """Create execution plan with parallel/sequential ordering."""
```

### 4.3 Agent Validator (`src/reef/agents/validator.py`)

```python
class ReefValidator:
    """Karen-style validation for reef operations."""

    def validate_output(self, output: dict, expected: dict) -> ValidationResult:
        """
        Two-tier validation:

        Tier 1 (Schema): Fast, deterministic checks
        - Format correct?
        - Required fields present?
        - Types match?

        Tier 2 (Semantic): LLM-based judgment
        - Does output match intent?
        - Quality acceptable?
        - Completeness verified?
        """

    def validate_polip(self, polip: Polip) -> ValidationResult:
        """Validate polip before calcification."""

    def validate_pruning(self, candidates: list) -> ValidationResult:
        """Validate pruning decisions before execution."""
```

### 4.4 Agent Definitions (`.claude/agents/`)

**reef-orchestrator.md**
```markdown
# Reef Orchestrator

**Model:** `sonnet` (coordination, moderate complexity)

Coordinates reef agent operations. Routes tasks to strategist,
dispatches to workers, aggregates results, validates output.

## Protocol

1. Receive task from user or system
2. Invoke strategist for decomposition
3. Route sub-tasks to appropriate workers
4. Aggregate worker outputs
5. Validate final result
6. Return or iterate if validation fails
```

**reef-strategist.md**
```markdown
# Reef Strategist

**Model:** `opus` (strategic thinking, high complexity)

Decomposes complex tasks into executable sub-tasks.
Routes to workers based on sensitivity and capability.

## Decomposition Protocol

1. Analyze task intent
2. Identify atomic sub-tasks
3. Classify sensitivity (pii | legal | external-ok)
4. Assign worker recommendations
5. Create execution plan (parallel where possible)
```

**reef-validator.md**
```markdown
# Reef Validator

**Model:** `sonnet` (validation, clear criteria)

Karen-style BS detector for reef operations.
Two-tier validation: schema checks then semantic checks.

## Validation Triggers

- Before polip calcification
- Before pruning execution
- Before task completion claims
- Before any destructive operation
```

### Test Gate
```bash
uv run pytest tests/test_agents.py -v
# Test cases:
# - test_orchestrator_flow
# - test_strategist_decomposition
# - test_validator_tier1
# - test_validator_tier2
# - test_agent_integration
```

---

## Phase 5: Skill Hotloading

**Goal:** Enable dynamic skill loading (global + project-local)

### 5.1 Skill Loader (`src/reef/skills/loader.py`)

```python
class SkillLoader:
    """Discovers and loads skills from multiple locations."""

    SEARCH_PATHS = [
        Path('.claude/skills'),      # Project-local (highest priority)
        Path.home() / '.claude/skills',  # Global
    ]

    def discover(self) -> list[SkillInfo]:
        """Find all available skills."""

    def load(self, skill_name: str) -> str:
        """Load skill content, project-local overrides global."""

    def inject(self, skill_name: str, context: dict) -> str:
        """Load and inject skill with context variables."""
```

### 5.2 Skill Registry (`src/reef/skills/registry.py`)

```python
class SkillRegistry:
    """Central registry for skill metadata."""

    def __init__(self):
        self.skills = {}
        self._scan()

    def _scan(self):
        """Scan skill directories and build index."""

    def get_for_task(self, task_type: str) -> list[str]:
        """Get relevant skills for task type."""

    def get_for_agent(self, agent_name: str) -> list[str]:
        """Get skills assigned to agent."""
```

### 5.3 Skill Index (`.claude/skills/index.json`)

```json
{
  "version": 1,
  "skills": {
    "polip-ops": {
      "path": "polip-ops.md",
      "agents": ["reef-orchestrator"],
      "task_types": ["polip", "reef", "memory"]
    },
    "validation": {
      "path": "validation.md",
      "agents": ["reef-validator"],
      "task_types": ["validate", "check", "verify"]
    }
  },
  "inheritance": {
    "from_global": true,
    "override_policy": "local-wins"
  }
}
```

### CLI Commands

```bash
reef skills list              # List all available skills
reef skills show <name>       # Display skill content
reef skills create <name>     # Create new project-local skill
reef skills sync              # Sync skill index
```

### Test Gate
```bash
uv run pytest tests/test_skills.py -v
# Test cases:
# - test_skill_discovery
# - test_local_override
# - test_skill_injection
# - test_agent_skill_routing
```

---

## Phase 6: Calcification Engine

**Goal:** Implement organic growth mechanics (the core thesis)

### 6.1 Calcification Triggers (`src/reef/blob.py` extension)

```python
class CalcificationEngine:
    """Determines when polips should calcify into bedrock."""

    TRIGGERS = {
        'time': {'weight': 0.2, 'threshold_days': 30},
        'usage': {'weight': 0.3, 'threshold_count': 10},
        'ceremony': {'weight': 0.2, 'required': False},
        'consensus': {'weight': 0.3, 'threshold_refs': 3},
    }

    def should_calcify(self, polip: Polip) -> tuple[bool, float]:
        """
        Check if polip should calcify.

        Returns:
            (should_calcify, score)
        """

    def get_candidates(self, glob: Glob) -> list[tuple[Polip, float]]:
        """Get all calcification candidates with scores."""
```

### 6.2 Adversarial Decay (`src/reef/blob.py` extension)

```python
class AdversarialDecay:
    """Selection pressure through challenge."""

    CHALLENGE_TRIGGERS = {
        'staleness': {'days': 60, 'min_access': 3},
        'orphan': {'no_refs_days': 30},
        'contradiction': {'requires_validator': True},
    }

    def get_challengers(self, glob: Glob) -> list[Polip]:
        """Get polips that should face challenge."""

    def challenge(self, polip: Polip) -> ChallengeResult:
        """
        Challenge polip to defend relevance.

        Returns:
            SURVIVE | MERGE | DECOMPOSE
        """
```

### 6.3 Health Metrics (`src/reef/blob.py` extension)

```python
class ReefHealth:
    """Ecosystem health metrics."""

    def vitality_score(self, glob: Glob) -> float:
        """Calculate Reef Vitality Score (RVS)."""

    def lifecycle_distribution(self, glob: Glob) -> dict:
        """Get distribution across lifecycle stages."""

    def self_organization_index(self, glob: Glob) -> float:
        """Measure emergence vs ordering balance."""
```

### CLI Commands

```bash
reef health                   # Full health report
reef health --json            # Machine-readable
reef calcify --dry-run        # Preview calcification candidates
reef calcify --execute        # Execute calcification
reef decay challenge          # Run adversarial challenge
```

### Test Gate
```bash
uv run pytest tests/test_calcification.py -v
# Test cases:
# - test_trigger_scoring
# - test_candidate_selection
# - test_adversarial_challenge
# - test_health_metrics
# - test_vitality_score
```

---

## Phase 7: Integration & Polish

**Goal:** Connect all components, CLI polish, documentation

### 7.1 Full Integration

- [ ] Connect orchestrator to MCP server
- [ ] Connect workers to skill loader
- [ ] Connect calcification to safety guards
- [ ] Connect health metrics to CLI

### 7.2 CLI Polish

```bash
# New command structure
reef agent run <task>         # Run task through agent infrastructure
reef agent status             # Show agent status
reef mcp start                # Start MCP server
reef mcp test                 # Test MCP tools
```

### 7.3 Documentation

- [ ] Update CLAUDE.md with new capabilities
- [ ] Create AGENT-SDK.md guide
- [ ] Create WORKERS.md configuration guide
- [ ] Update README.md

### Test Gate
```bash
uv run pytest -v              # All tests pass
uv run python -m reef.cli --help  # CLI works
uv run python -m reef.mcp.server --test  # MCP server starts
```

---

## Testing Strategy

### Unit Tests (Per Phase)
Each phase has test gate requirements before proceeding.

### Integration Tests
```bash
# Full pipeline test
uv run pytest tests/integration/ -v
```

### Stress Tests
```bash
# High-volume operations
uv run pytest tests/stress_test.py -v
```

### End-to-End Test
```bash
# Manual E2E verification
reef init --gitignore
reef sprout thread "Test thread"
reef agent run "Summarize the reef"
reef health
reef sync --dry-run
```

---

## Rollout Schedule

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 0: Foundation | 1 day | Directory structure |
| 1: Safety | 2 days | Pruning safeguards, audit, undo |
| 2: Workers | 2 days | Groq/Ollama/Gemini dispatch |
| 3: MCP | 2 days | MCP server with tools |
| 4: Agents | 3 days | Orchestrator, strategist, validator |
| 5: Skills | 1 day | Hotloading system |
| 6: Calcification | 2 days | Organic growth engine |
| 7: Integration | 2 days | Polish and docs |

**Total: ~15 days of focused work**

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Existing tests pass | 100% |
| New test coverage | >80% |
| MCP protocol compliance | Full |
| Worker availability | 2/3 workers online |
| Safety guards active | All P0 implemented |
| Calcification accuracy | Manual verification |

---

## Key Decisions Baked In

From session research:

1. **Organic growth philosophy** — Schema emerges from usage, not design
2. **Biological metaphors as blueprint** — Coral lifecycle = polip lifecycle
3. **Safety-first automation** — P0 guards before any auto-pruning
4. **Hybrid worker model** — Claude for judgment, free models for grunt work
5. **MCP as interface** — Standard protocol for tool integration
6. **Local-first sovereignty** — Data never leaves machine unless explicitly routed
7. **Progressive disclosure** — L1/L2/L3 token-efficient loading
8. **Karen-style validation** — Two-tier: schema then semantic

---

## Dependencies

**Required:**
- Python 3.12+
- uv (package manager)

**Optional (for workers):**
- Groq API key (`GROQ_API_KEY`)
- Ollama running locally
- Gemini API key (`GEMINI_API_KEY`)

**MCP:**
- mcp package (add to pyproject.toml)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Worker API changes | Abstract behind dispatch layer |
| MCP protocol evolution | Pin version, test compatibility |
| Catastrophic pruning | P0 safety guards mandatory |
| Complexity creep | Strict phase gates, test requirements |
| Zero-dep constraint violation | Workers use stdlib HTTP only |

---

## Next Steps

1. **Approve plan** — Review and adjust phases as needed
2. **Phase 0** — Create directory structure
3. **Phase 1** — Implement safety guards (critical path)
4. **Continue sequentially** — Each phase has test gate
