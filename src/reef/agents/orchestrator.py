"""
Reef Orchestrator - coordinates reef agent operations.

Routes tasks to strategist, dispatches to workers, aggregates results,
validates output.
"""

from dataclasses import dataclass
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


@dataclass
class WorkerResult:
    """Result from a worker execution."""

    sub_task_id: str
    success: bool
    output: Any
    worker_used: str
    latency_ms: int


class ReefOrchestrator:
    """Coordinates reef agent operations."""

    def __init__(self, glob=None, dispatcher=None):
        """
        Initialize orchestrator.

        Args:
            glob: Glob instance for reef operations
            dispatcher: WorkerDispatcher for task routing
        """
        self.glob = glob
        self.dispatcher = dispatcher
        self._strategist = None
        self._validator = None

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
        # Will be implemented in Phase 4
        raise NotImplementedError("Will be implemented in Phase 4")

    def decompose(self, task: str) -> list[SubTask]:
        """
        Use strategist to break down complex task.

        Args:
            task: Task description

        Returns:
            List of decomposed sub-tasks
        """
        # Will be implemented in Phase 4
        raise NotImplementedError("Will be implemented in Phase 4")

    def aggregate(self, results: list[WorkerResult]) -> dict[str, Any]:
        """
        Combine worker outputs.

        Args:
            results: List of worker results

        Returns:
            Aggregated output
        """
        # Will be implemented in Phase 4
        raise NotImplementedError("Will be implemented in Phase 4")

    def validate(self, output: dict[str, Any]) -> dict[str, Any]:
        """
        Use validator to verify output quality.

        Args:
            output: Output to validate

        Returns:
            Validation result
        """
        # Will be implemented in Phase 4
        raise NotImplementedError("Will be implemented in Phase 4")
