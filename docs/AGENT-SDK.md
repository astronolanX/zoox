# Reef Agent SDK

Reef includes a lightweight agent orchestration framework for breaking complex tasks into parallel sub-tasks that route to different models.

## Architecture

The agent SDK consists of four main components:

### 1. Orchestrator (`src/reef/agents/orchestrator.py`)

The orchestrator coordinates the entire agent workflow:

```python
from reef.agents import ReefOrchestrator

orchestrator = ReefOrchestrator()
result = orchestrator.execute_task(
    task="Summarize these documents and extract key dates",
    context={"docs": [...]}
)
```

**Workflow:**
1. **Strategist** analyzes task → decomposes into sub-tasks
2. **Dispatcher** routes sub-tasks to workers (Groq/Ollama/Gemini)
3. **Orchestrator** aggregates results
4. **Validator** verifies output quality

### 2. Strategist (`src/reef/agents/strategist.py`)

Analyzes tasks and creates execution plans with parallel phases:

```python
from reef.agents import ReefStrategist

strategist = ReefStrategist(glob)
analysis = strategist.analyze_task("Build API and frontend")

# Returns sub-tasks grouped by dependencies
plan = strategist.plan_execution(analysis)
# plan.phases = [
#   [task_a, task_b],  # Parallel phase 1
#   [task_c]           # Phase 2 (depends on phase 1)
# ]
```

### 3. Dispatcher (`src/reef/workers/dispatcher.py`)

Routes sub-tasks to appropriate external models based on:
- **Task type**: search, summarize, validate, extract, synthesize
- **Sensitivity**: pii, legal, external-ok
- **Worker availability**: Groq, Ollama, Gemini

```python
from reef.workers import WorkerDispatcher, TaskType, Sensitivity

dispatcher = WorkerDispatcher()
result = dispatcher.dispatch(
    task_type=TaskType.SUMMARIZE,
    prompt="Summarize this document",
    sensitivity=Sensitivity.EXTERNAL_OK
)
```

**Routing rules:**
- **PII/legal data** → Claude only (not routed to external workers)
- **Search/extract** → Groq (fast inference) or Gemini
- **Summarize** → Ollama (local) or Groq
- **Validate** → Claude (highest quality)
- **Synthesize** → Claude (complex reasoning)

### 4. Validator (`src/reef/agents/validator.py`)

Validates output quality across three tiers:
- **Tier 1**: Critical validation (e.g., security checks)
- **Tier 2**: Important validation (e.g., data integrity)
- **Tier 3**: Nice-to-have validation (e.g., style)

## Reef Trenches: Parallel Claude Agents

Reef trenches enable true parallel execution by spawning multiple Claude agents in isolated git worktrees:

### Creating a Trench

```bash
# Basic: Create isolated worktree
reef trench spawn feature-auth

# Advanced: Spawn worktree + launch Claude session
reef trench spawn feature-auth --task "Implement JWT authentication"

# With model override
reef trench spawn docs-update --task "Update API docs" --model haiku
```

### Model Routing

Trenches automatically select the best model based on task complexity:

| Complexity | Keywords | Model |
|------------|----------|-------|
| **Simple** | fix, typo, rename, update, small, doc | haiku |
| **Moderate** | implement, feature, add, create | sonnet |
| **Complex** | refactor, architect, redesign, system, multi-file | opus |

Example:
```bash
# Auto-detects "refactor" → uses opus
reef trench spawn db-refactor --task "Refactor database layer"

# Auto-detects "fix" → uses haiku
reef trench spawn typo-fix --task "Fix typo in README"
```

### Trench Lifecycle

1. **Spawn** → Creates git worktree with isolated `.claude/` polips
2. **Run** → Claude session executes in worktree (background process)
3. **Test** → Run test suite in isolation before merge
4. **Merge** → Validated changes merge to parent branch
5. **Cleanup** → Worktree and branch removed automatically

```bash
# Monitor active trenches
reef trench status

# See session output
reef trench logs feature-auth

# Run tests before merge
reef trench test feature-auth

# Merge when ready
reef trench merge feature-auth

# Cancel and cleanup
reef trench abort feature-auth
```

### Orchestrator Pattern

Spawn multiple trenches for parallel feature development:

```python
from reef.trench import TrenchHarness

harness = TrenchHarness()

# Spawn parallel sessions
harness.spawn_session(
    name="api",
    task="Add REST endpoints for user management",
    complexity=TrenchComplexity.MODERATE
)

harness.spawn_session(
    name="frontend",
    task="Build React components for user UI",
    complexity=TrenchComplexity.MODERATE
)

# Monitor until both ready
while any(t.status == TrenchStatus.RUNNING for t in harness.status()):
    time.sleep(10)

# Test and merge
for name in ["api", "frontend"]:
    harness.run_tests(name)
    if trench.status == TrenchStatus.READY:
        harness.merge(name)
```

## Skills System

Skills are reusable task templates stored in `.claude/skills/`:

### Skill Structure

```markdown
---
agents: ["strategist", "orchestrator"]
task_types: ["decompose", "plan"]
description: "Breaks down complex tasks into sub-tasks"
---

# Task Decomposition Skill

Given task: {task_description}

Analyze and break into:
1. Independent sub-tasks (can run in parallel)
2. Dependent sub-tasks (require results from step 1)
3. Sensitivity classification for each sub-task

Output as JSON with phases.
```

### Loading Skills

```python
from reef.skills import SkillLoader

loader = SkillLoader()

# Discover all skills
skills = loader.discover()

# Load and inject context
content = loader.inject(
    "task-decomposition",
    context={"task_description": "Build authentication system"}
)

# Hot reload on changes
loader.watch(callback=lambda name: print(f"Skill {name} changed"))
changed = loader.reload_changed()
```

### Skill Search Paths

Skills load with priority:
1. **Project-local**: `.claude/skills/` (highest priority)
2. **Global**: `~/.claude/skills/`

Local skills override global ones with the same name.

## Configuration

### Worker Config

Configure external models in `.claude/workers/config.json`:

```json
{
  "workers": {
    "groq": {
      "api_key_env": "GROQ_API_KEY",
      "default_model": "llama-3.3-70b-versatile"
    },
    "ollama": {
      "host": "http://localhost:11434",
      "default_model": "llama3.2"
    },
    "gemini": {
      "api_key_env": "GEMINI_API_KEY",
      "default_model": "gemini-2.0-flash-exp"
    }
  },
  "routing": {
    "search": ["groq", "gemini"],
    "summarize": ["ollama", "groq"],
    "extract": ["groq", "gemini"]
  }
}
```

See [WORKERS.md](WORKERS.md) for detailed worker configuration.

## Example: Multi-Agent Research

```python
from reef.agents import ReefOrchestrator

orchestrator = ReefOrchestrator()

# Complex task requiring multiple sub-tasks
result = orchestrator.execute_task(
    task="Research Python async patterns, summarize findings, and extract code examples",
    context={
        "sources": ["docs.python.org/asyncio", "realpython.com/async-io"],
        "expected": {
            "summary_length": 500,
            "min_examples": 3
        }
    }
)

# Strategist decomposes into:
# - Sub-task 1: Search Python docs (→ Groq)
# - Sub-task 2: Search RealPython (→ Groq)
# - Sub-task 3: Summarize combined results (→ Ollama)
# - Sub-task 4: Extract code examples (→ Groq)
# - Sub-task 5: Validate output (→ Claude)

print(result.output)
print(f"Workers used: {result.output['workers_used']}")
print(f"Total latency: {result.output['total_latency_ms']}ms")
```

## Safety & Validation

The validator checks output across three tiers:

```python
from reef.agents import ReefValidator

validator = ReefValidator(glob)
validation = validator.validate_output(
    output={"summary": "...", "examples": [...]},
    expected={"min_examples": 3}
)

# validation.status: pass | warn | fail
# validation.tier: tier1 | tier2 | tier3
# validation.errors: ["Error 1", "Error 2"]
# validation.warnings: ["Warning 1"]
```

**Tier 1 failures** block execution (security, correctness).
**Tier 2 warnings** alert but don't block (data quality).
**Tier 3 info** provides suggestions (style, optimization).

## Next Steps

- See [WORKERS.md](WORKERS.md) for worker setup and API keys
- Check `examples/` for orchestrator patterns
- Read `src/reef/agents/` for implementation details
