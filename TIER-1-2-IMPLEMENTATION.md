# Tier 1 + Tier 2 Implementation Guide: Agent Run Notes (Minimal)

**Author**: KAREN
**Date**: 2026-01-15
**Scope**: 130 LOC implementation, ~8 hours work
**Target Completion**: 2026-01-17

---

## Overview

This implements only what has proven value:
- **Tier 1**: Automatic metrics collection (30 LOC)
- **Tier 2**: Per-agent telemetry tracking (50 LOC)
- **No extraction**, no pattern mining, no automation beyond capture

Why this works:
1. Captures what you need to measure (tokens, duration, agents)
2. Integrates with existing reef system
3. Leaves room for decision-making when patterns emerge
4. Avoids scope creep into non-productive automation

---

## Tier 1: Automatic Metrics (30 LOC)

### What It Does
Every run, capture:
```json
{
  "run_id": "022",
  "timestamp": "2026-01-15T14:30:00Z",
  "duration_seconds": 1234,
  "exit_code": "success",
  "agents_spawned": ["Architect", "Karen"],
  "files_created": 4,
  "files_modified": 3
}
```

### Where to Put It

**File**: `/Users/nolan/Desktop/reef/src/reef/metrics.py`

```python
"""Auto-collected metrics for harness learning."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


class RunMetrics:
    """Capture metrics for every run."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.start_time = time.time()
        self.metrics = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": 0,
            "exit_code": "pending",
            "agents_spawned": [],
            "files_created": 0,
            "files_modified": 0,
        }

    def add_agent(self, agent_name: str) -> None:
        """Record an agent was used in this run."""
        if agent_name not in self.metrics["agents_spawned"]:
            self.metrics["agents_spawned"].append(agent_name)

    def set_exit_code(self, code: str) -> None:
        """Set final exit code (success/failure/timeout/error)."""
        self.metrics["exit_code"] = code

    def set_files_created(self, count: int) -> None:
        """Set number of files created."""
        self.metrics["files_created"] = count

    def set_files_modified(self, count: int) -> None:
        """Set number of files modified."""
        self.metrics["files_modified"] = count

    def finalize(self) -> dict:
        """Complete metrics collection."""
        elapsed = time.time() - self.start_time
        self.metrics["duration_seconds"] = round(elapsed, 1)
        return self.metrics

    def save(self, output_dir: Optional[Path] = None) -> Path:
        """Save metrics to JSON file."""
        if output_dir is None:
            output_dir = Path(".claude/runs")
        output_dir.mkdir(parents=True, exist_ok=True)

        metrics = self.finalize()
        filepath = output_dir / f"run-{self.run_id}.metrics.json"

        with open(filepath, "w") as f:
            json.dump(metrics, f, indent=2)

        return filepath


class MetricsAggregate:
    """Aggregate metrics across multiple runs."""

    @staticmethod
    def load_all(runs_dir: Path = Path(".claude/runs")) -> list[dict]:
        """Load all metrics files."""
        metrics = []
        for filepath in sorted(runs_dir.glob("run-*.metrics.json")):
            with open(filepath) as f:
                metrics.append(json.load(f))
        return metrics

    @staticmethod
    def summary(metrics: list[dict]) -> dict:
        """Compute aggregate statistics."""
        if not metrics:
            return {}

        total_runs = len(metrics)
        total_duration = sum(m.get("duration_seconds", 0) for m in metrics)
        total_files_created = sum(m.get("files_created", 0) for m in metrics)
        total_files_modified = sum(m.get("files_modified", 0) for m in metrics)

        agents = set()
        for m in metrics:
            agents.update(m.get("agents_spawned", []))

        return {
            "total_runs": total_runs,
            "avg_duration_seconds": round(total_duration / total_runs, 1),
            "total_files_created": total_files_created,
            "total_files_modified": total_files_modified,
            "unique_agents": sorted(agents),
            "success_rate": sum(
                1 for m in metrics if m.get("exit_code") == "success"
            ) / total_runs,
        }


# Usage example:
# In your run hook or CLI:
#
# metrics = RunMetrics("022")
# metrics.add_agent("Architect")
# metrics.add_agent("Karen")
# metrics.set_files_created(4)
# metrics.set_files_modified(3)
# metrics.set_exit_code("success")
# metrics.save()
#
# Later, query:
# all_metrics = MetricsAggregate.load_all()
# summary = MetricsAggregate.summary(all_metrics)
# print(f"Avg duration: {summary['avg_duration_seconds']}s")
```

**Lines of code**: ~130 LOC
**Time to write**: 1 hour
**Time to integrate**: 30 min

---

## Tier 2: Per-Agent Telemetry (50 LOC)

### What It Does
Track per-agent metrics separately:
```json
{
  "run_id": "022",
  "agents": {
    "Architect": {
      "tokens_used": 15000,
      "latency_seconds": 125,
      "ideas_generated": 3,
      "exit_code": "success"
    },
    "Karen": {
      "tokens_used": 8000,
      "latency_seconds": 48,
      "ideas_generated": 1,
      "exit_code": "success"
    }
  }
}
```

### Where to Put It

**File**: `/Users/nolan/Desktop/reef/src/reef/agent_metrics.py`

```python
"""Per-agent telemetry tracking."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class AgentMetrics:
    """Track metrics for individual agents within a run."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.agents = {}

    def start_agent(self, agent_name: str) -> None:
        """Begin tracking a new agent."""
        self.agents[agent_name] = {
            "start_time": datetime.utcnow().isoformat(),
            "tokens_used": 0,
            "ideas_generated": 0,
            "latency_seconds": 0,
            "exit_code": "pending",
        }

    def record_tokens(self, agent_name: str, tokens: int) -> None:
        """Record token usage for an agent."""
        if agent_name in self.agents:
            self.agents[agent_name]["tokens_used"] = tokens

    def record_latency(self, agent_name: str, seconds: float) -> None:
        """Record execution latency for an agent."""
        if agent_name in self.agents:
            self.agents[agent_name]["latency_seconds"] = round(seconds, 2)

    def record_ideas(self, agent_name: str, count: int) -> None:
        """Record ideas generated by an agent."""
        if agent_name in self.agents:
            self.agents[agent_name]["ideas_generated"] = count

    def set_exit_code(self, agent_name: str, code: str) -> None:
        """Set agent exit code."""
        if agent_name in self.agents:
            self.agents[agent_name]["exit_code"] = code

    def save(self, output_dir: Optional[Path] = None) -> Path:
        """Save per-agent metrics."""
        if output_dir is None:
            output_dir = Path(".claude/runs")
        output_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "run_id": self.run_id,
            "timestamp": datetime.utcnow().isoformat(),
            "agents": self.agents,
        }

        filepath = output_dir / f"run-{self.run_id}.agents.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return filepath

    @staticmethod
    def compare_agents(runs_dir: Path = Path(".claude/runs")) -> dict:
        """Compare agent efficiency across runs."""
        agent_stats = {}

        for filepath in sorted(runs_dir.glob("run-*.agents.json")):
            with open(filepath) as f:
                data = json.load(f)
                for agent_name, metrics in data.get("agents", {}).items():
                    if agent_name not in agent_stats:
                        agent_stats[agent_name] = {
                            "runs": 0,
                            "total_tokens": 0,
                            "total_latency": 0,
                            "total_ideas": 0,
                            "success_count": 0,
                        }

                    stats = agent_stats[agent_name]
                    stats["runs"] += 1
                    stats["total_tokens"] += metrics.get("tokens_used", 0)
                    stats["total_latency"] += metrics.get("latency_seconds", 0)
                    stats["total_ideas"] += metrics.get("ideas_generated", 0)
                    if metrics.get("exit_code") == "success":
                        stats["success_count"] += 1

        # Compute averages
        result = {}
        for agent_name, stats in agent_stats.items():
            runs = stats["runs"]
            result[agent_name] = {
                "runs": runs,
                "avg_tokens": round(stats["total_tokens"] / runs, 0),
                "avg_latency_seconds": round(stats["total_latency"] / runs, 2),
                "avg_ideas_per_run": round(stats["total_ideas"] / runs, 2),
                "success_rate": round(stats["success_count"] / runs, 2),
            }

        return result


# Usage example:
# In your /team hook:
#
# agent_metrics = AgentMetrics("022")
#
# # When Architect starts:
# agent_metrics.start_agent("Architect")
# # ... agent runs ...
# agent_metrics.record_tokens("Architect", 15000)
# agent_metrics.record_latency("Architect", 125.3)
# agent_metrics.record_ideas("Architect", 3)
# agent_metrics.set_exit_code("Architect", "success")
#
# # When Karen starts:
# agent_metrics.start_agent("Karen")
# # ... agent runs ...
# agent_metrics.record_tokens("Karen", 8000)
# agent_metrics.record_latency("Karen", 48.2)
# agent_metrics.record_ideas("Karen", 1)
# agent_metrics.set_exit_code("Karen", "success")
#
# agent_metrics.save()
#
# Later, analyze:
# comparison = AgentMetrics.compare_agents()
# for agent, stats in comparison.items():
#     print(f"{agent}: {stats['avg_tokens']} tokens/run, {stats['success_rate']} success")
```

**Lines of code**: ~120 LOC
**Time to write**: 1.5 hours
**Time to integrate**: 1 hour

---

## Integration with Existing Systems

### Option 1: Hook Integration (Recommended)

Create `.claude/hooks/harness-metrics.py`:

```python
"""Hook to auto-capture metrics at session end."""

import sys
from pathlib import Path

# Add reef to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from reef.metrics import RunMetrics
from reef.agent_metrics import AgentMetrics


def on_session_end(session_data: dict) -> None:
    """Capture metrics when session completes."""

    # Get run ID from environment or session
    run_id = session_data.get("run_id", "unknown")

    # Capture basic metrics
    metrics = RunMetrics(run_id)
    metrics.add_agent("system")  # Placeholder
    metrics.set_exit_code(session_data.get("exit_code", "unknown"))
    metrics.save()

    # If agents were spawned, capture per-agent metrics
    if "agents" in session_data:
        agent_metrics = AgentMetrics(run_id)
        for agent in session_data["agents"]:
            agent_metrics.start_agent(agent["name"])
            agent_metrics.record_tokens(agent["name"], agent.get("tokens", 0))
            agent_metrics.record_latency(agent["name"], agent.get("latency", 0))
            agent_metrics.set_exit_code(agent["name"], agent.get("exit_code", "unknown"))
        agent_metrics.save()
```

### Option 2: CLI Integration

Add to `src/reef/cli.py`:

```python
@click.command()
@click.option("--run-id", required=True, help="Run ID for metrics")
@click.option("--agent", multiple=True, help="Agent names")
@click.option("--tokens", type=int, help="Total tokens used")
@click.option("--duration", type=float, help="Duration in seconds")
def metrics(run_id, agent, tokens, duration):
    """Manually record run metrics."""
    from reef.metrics import RunMetrics

    m = RunMetrics(run_id)
    for a in agent:
        m.add_agent(a)
    if tokens:
        m.metrics["tokens_used"] = tokens
    m.set_exit_code("success")
    m.save()
    click.echo(f"Metrics saved: {run_id}")
```

---

## Testing

Create `/Users/nolan/Desktop/reef/tests/test_metrics.py`:

```python
"""Test metrics collection."""

import json
import tempfile
from pathlib import Path

from reef.metrics import RunMetrics, MetricsAggregate
from reef.agent_metrics import AgentMetrics


def test_run_metrics_basic():
    """Test basic metrics capture."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        metrics = RunMetrics("001")
        metrics.add_agent("Architect")
        metrics.add_agent("Karen")
        metrics.set_files_created(3)
        metrics.set_exit_code("success")

        filepath = metrics.save(tmpdir)

        with open(filepath) as f:
            data = json.load(f)

        assert data["run_id"] == "001"
        assert data["exit_code"] == "success"
        assert len(data["agents_spawned"]) == 2
        assert "Architect" in data["agents_spawned"]


def test_agent_metrics_tracking():
    """Test per-agent metric tracking."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        agent_metrics = AgentMetrics("001")
        agent_metrics.start_agent("Architect")
        agent_metrics.record_tokens("Architect", 15000)
        agent_metrics.record_latency("Architect", 125.3)
        agent_metrics.record_ideas("Architect", 3)

        agent_metrics.start_agent("Karen")
        agent_metrics.record_tokens("Karen", 8000)
        agent_metrics.record_latency("Karen", 48.2)

        filepath = agent_metrics.save(tmpdir)

        with open(filepath) as f:
            data = json.load(f)

        assert data["agents"]["Architect"]["tokens_used"] == 15000
        assert data["agents"]["Karen"]["tokens_used"] == 8000


def test_metrics_aggregate():
    """Test aggregation across runs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create 3 runs
        for i in range(1, 4):
            m = RunMetrics(str(i))
            m.add_agent("Architect")
            m.set_exit_code("success")
            m.save(tmpdir)

        # Load and summarize
        metrics = MetricsAggregate.load_all(tmpdir)
        summary = MetricsAggregate.summary(metrics)

        assert summary["total_runs"] == 3
        assert summary["success_rate"] == 1.0
        assert "Architect" in summary["unique_agents"]


if __name__ == "__main__":
    test_run_metrics_basic()
    test_agent_metrics_tracking()
    test_metrics_aggregate()
    print("All tests passed!")
```

**Run**: `uv run pytest tests/test_metrics.py`

---

## Validation Checklist

- [ ] `src/reef/metrics.py` created with ~130 LOC
- [ ] `src/reef/agent_metrics.py` created with ~120 LOC
- [ ] Tests pass: `uv run pytest tests/test_metrics.py`
- [ ] Can manually call: `reef metrics --run-id 022 --agent Architect Karen`
- [ ] Files created:
  - `.claude/runs/run-022.metrics.json`
  - `.claude/runs/run-022.agents.json`
- [ ] Query works:
  ```python
  from reef.metrics import MetricsAggregate
  summary = MetricsAggregate.summary(MetricsAggregate.load_all())
  print(summary)
  ```

---

## Integration Timing

**Day 1 (Today, 2026-01-15)**
- [ ] Review this document
- [ ] Implement `metrics.py` (1 hour)
- [ ] Write tests (1 hour)

**Day 2 (2026-01-16)**
- [ ] Implement `agent_metrics.py` (1.5 hours)
- [ ] Integrate with hooks or CLI (1 hour)
- [ ] Test end-to-end (1 hour)

**Day 3 (2026-01-17)**
- [ ] Document in CLAUDE.md
- [ ] Run full test suite
- [ ] Deploy to next run (run-022)

---

## Next: When to Build Tier 3

After 10 more runs (runs 22-31), review:

1. **Question**: Do patterns exist in the metrics?
   - Is one agent consistently more efficient?
   - Is latency trending up/down?
   - Are success rates varying by condition?

2. **If YES patterns**: Consider Tier 3 (decision linking, automatic suggestions)

3. **If NO patterns**: Stop here. Metrics are sufficient.

---

**End of Implementation Guide**

*This is the minimum viable instrumentation. Don't expand it without evidence that patterns exist and drive improvements.*
