"""
Reef Strategist - strategic task decomposition and planning.

Analyzes task complexity, decomposes into atomic sub-tasks,
classifies sensitivity, assigns worker recommendations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Complexity(Enum):
    """Task complexity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Sensitivity(Enum):
    """Task sensitivity levels."""

    PII = "pii"           # Contains personal data - Claude only
    LEGAL = "legal"       # Legal implications - Claude only
    EXTERNAL_OK = "external-ok"  # Safe for external workers


@dataclass
class TaskAnalysis:
    """Analysis of a task."""

    original_task: str
    complexity: Complexity
    sub_tasks: list[dict[str, Any]]
    model_requirements: list[str]
    sensitivity: Sensitivity
    parallel_groups: list[list[str]]  # Groups that can run in parallel


@dataclass
class ExecutionPlan:
    """Plan for executing a task."""

    phases: list[dict[str, Any]]
    estimated_workers: dict[str, int]
    requires_validation: bool


class ReefStrategist:
    """Strategic task decomposition and planning."""

    def __init__(self, glob=None):
        """
        Initialize strategist.

        Args:
            glob: Glob instance for reef operations
        """
        self.glob = glob

    def analyze_task(self, task: str) -> TaskAnalysis:
        """
        Analyze task complexity and requirements.

        Args:
            task: Task description

        Returns:
            TaskAnalysis with:
            - complexity: low | medium | high
            - sub_tasks: list of decomposed tasks
            - model_requirements: which model tiers needed
            - sensitivity: pii | legal | external-ok
        """
        # Will be implemented in Phase 4
        raise NotImplementedError("Will be implemented in Phase 4")

    def route_to_workers(self, sub_tasks: list[dict]) -> dict[str, list]:
        """
        Assign sub-tasks to appropriate workers.

        Args:
            sub_tasks: List of sub-task definitions

        Returns:
            Mapping of worker name to assigned tasks
        """
        # Will be implemented in Phase 4
        raise NotImplementedError("Will be implemented in Phase 4")

    def plan_execution(self, analysis: TaskAnalysis) -> ExecutionPlan:
        """
        Create execution plan with parallel/sequential ordering.

        Args:
            analysis: Task analysis result

        Returns:
            Execution plan with phases
        """
        # Will be implemented in Phase 4
        raise NotImplementedError("Will be implemented in Phase 4")

    def classify_sensitivity(self, task: str) -> Sensitivity:
        """
        Classify task sensitivity.

        Args:
            task: Task description

        Returns:
            Sensitivity level
        """
        # Will be implemented in Phase 4
        # Default to external-ok for now
        return Sensitivity.EXTERNAL_OK
