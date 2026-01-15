"""
Reef Orchestrator - coordinates reef agent operations.

Routes tasks to strategist, dispatches to workers, aggregates results,
validates output.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SubTask:
    """A decomposed sub-task."""

    id: str
    description: str
    task_type: str
    sensitivity: str  # pii | legal | external-ok
    worker_hint: str | None = None
    depends_on: list[str] | None = None


@dataclass
class TaskResult:
    """Result from task execution."""

    success: bool
    output: dict[str, Any]
    errors: list[str] | None = None
    validation: dict[str, Any] | None = None
    worker_results: list["WorkerResult"] | None = None


@dataclass
class WorkerResult:
    """Result from a worker execution."""

    sub_task_id: str
    success: bool
    output: Any
    worker_used: str
    latency_ms: int = 0
    error: str | None = None


class ReefOrchestrator:
    """Coordinates reef agent operations."""

    def __init__(self, glob=None, dispatcher=None, project_dir: Path | None = None):
        """
        Initialize orchestrator.

        Args:
            glob: Glob instance for reef operations
            dispatcher: WorkerDispatcher for task routing
            project_dir: Project directory for lazy initialization
        """
        self.project_dir = project_dir or Path.cwd()
        self._glob = glob
        self._dispatcher = dispatcher
        self._strategist = None
        self._validator = None

    @property
    def glob(self):
        """Lazy-load glob."""
        if self._glob is None:
            from reef.blob import Glob

            self._glob = Glob(self.project_dir)
        return self._glob

    @property
    def dispatcher(self):
        """Lazy-load dispatcher."""
        if self._dispatcher is None:
            from reef.workers import WorkerDispatcher

            self._dispatcher = WorkerDispatcher(self.project_dir)
        return self._dispatcher

    @property
    def strategist(self):
        """Lazy-load strategist."""
        if self._strategist is None:
            from .strategist import ReefStrategist

            self._strategist = ReefStrategist(self.glob)
        return self._strategist

    @property
    def validator(self):
        """Lazy-load validator."""
        if self._validator is None:
            from .validator import ReefValidator

            self._validator = ReefValidator(self.glob)
        return self._validator

    def execute_task(self, task: str, context: dict | None = None) -> TaskResult:
        """
        Main entry point for agent work.

        1. Strategist decomposes task
        2. Dispatcher routes sub-tasks to workers
        3. Orchestrator aggregates results
        4. Validator verifies output

        Args:
            task: Task description
            context: Additional context

        Returns:
            Task execution result
        """
        context = context or {}

        # Step 1: Strategist analyzes and decomposes
        analysis = self.strategist.analyze_task(task)

        # Step 2: Create execution plan
        plan = self.strategist.plan_execution(analysis)

        # Step 3: Execute sub-tasks (respect parallel groups)
        worker_results = []
        all_outputs = {}

        for phase in plan.phases:
            phase_results = self._execute_phase(phase, context)
            worker_results.extend(phase_results)

            # Collect outputs for aggregation
            for result in phase_results:
                if result.success:
                    all_outputs[result.sub_task_id] = result.output

        # Step 4: Aggregate results
        aggregated = self.aggregate(worker_results)

        # Step 5: Validate output
        validation = self.validator.validate_output(
            output=aggregated,
            expected=context.get("expected", {}),
        )

        # Determine overall success
        success = all(r.success for r in worker_results)
        errors = [r.error for r in worker_results if r.error]

        return TaskResult(
            success=success and validation.status.value != "fail",
            output=aggregated,
            errors=errors if errors else None,
            validation={
                "status": validation.status.value,
                "tier": validation.tier.value,
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
            worker_results=worker_results,
        )

    def _execute_phase(
        self, phase: dict[str, Any], context: dict
    ) -> list[WorkerResult]:
        """Execute a phase of sub-tasks."""
        results = []
        sub_tasks = phase.get("sub_tasks", [])

        for sub_task in sub_tasks:
            result = self._execute_sub_task(sub_task, context)
            results.append(result)

        return results

    def _execute_sub_task(
        self, sub_task: dict[str, Any], context: dict
    ) -> WorkerResult:
        """Execute a single sub-task."""
        sub_task_id = sub_task.get("id", "unknown")
        task_type = sub_task.get("task_type", "summarize")
        description = sub_task.get("description", "")
        sensitivity = sub_task.get("sensitivity", "external-ok")

        try:
            # Dispatch to worker
            worker_result = self.dispatcher.dispatch(
                task_type=task_type,
                prompt=description,
                sensitivity=sensitivity,
            )

            return WorkerResult(
                sub_task_id=sub_task_id,
                success=worker_result.success,
                output=worker_result.output,
                worker_used=worker_result.worker_name or "unknown",
                latency_ms=worker_result.latency_ms,
                error=worker_result.error,
            )

        except Exception as e:
            return WorkerResult(
                sub_task_id=sub_task_id,
                success=False,
                output=None,
                worker_used="none",
                latency_ms=0,
                error=str(e),
            )

    def decompose(self, task: str) -> list[SubTask]:
        """
        Use strategist to break down complex task.

        Args:
            task: Task description

        Returns:
            List of decomposed sub-tasks
        """
        analysis = self.strategist.analyze_task(task)

        return [
            SubTask(
                id=st.get("id", f"subtask-{i}"),
                description=st.get("description", ""),
                task_type=st.get("task_type", "summarize"),
                sensitivity=st.get("sensitivity", "external-ok"),
                worker_hint=st.get("worker_hint"),
                depends_on=st.get("depends_on"),
            )
            for i, st in enumerate(analysis.sub_tasks)
        ]

    def aggregate(self, results: list[WorkerResult]) -> dict[str, Any]:
        """
        Combine worker outputs.

        Args:
            results: List of worker results

        Returns:
            Aggregated output
        """
        aggregated = {
            "sub_task_count": len(results),
            "success_count": sum(1 for r in results if r.success),
            "failure_count": sum(1 for r in results if not r.success),
            "outputs": {},
            "workers_used": [],
            "total_latency_ms": 0,
        }

        for result in results:
            if result.success:
                aggregated["outputs"][result.sub_task_id] = result.output
            if result.worker_used not in aggregated["workers_used"]:
                aggregated["workers_used"].append(result.worker_used)
            aggregated["total_latency_ms"] += result.latency_ms

        return aggregated

    def validate(self, output: dict[str, Any]) -> dict[str, Any]:
        """
        Use validator to verify output quality.

        Args:
            output: Output to validate

        Returns:
            Validation result
        """
        result = self.validator.validate_output(output, expected={})

        return {
            "status": result.status.value,
            "tier": result.tier.value,
            "errors": result.errors,
            "warnings": result.warnings,
        }
