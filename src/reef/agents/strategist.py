"""
Reef Strategist - strategic task decomposition and planning.

Analyzes task complexity, decomposes into atomic sub-tasks,
classifies sensitivity, assigns worker recommendations.
"""

import re
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

    PII = "pii"  # Contains personal data - Claude only
    LEGAL = "legal"  # Legal implications - Claude only
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

    # Keywords that suggest specific task types
    TASK_TYPE_KEYWORDS = {
        "search": ["search", "find", "look for", "locate", "discover"],
        "summarize": ["summarize", "summary", "brief", "overview", "condense"],
        "extract": ["extract", "get", "pull", "parse", "retrieve"],
        "validate": ["validate", "verify", "check", "confirm", "ensure"],
        "synthesize": ["synthesize", "combine", "merge", "integrate", "compile"],
    }

    # Keywords that suggest PII sensitivity
    PII_KEYWORDS = [
        "password",
        "secret",
        "api key",
        "token",
        "credential",
        "ssn",
        "social security",
        "credit card",
        "bank account",
        "personal",
        "private",
        "email address",
        "phone number",
        "home address",
    ]

    # Keywords that suggest legal sensitivity
    LEGAL_KEYWORDS = [
        "legal",
        "lawsuit",
        "contract",
        "agreement",
        "liability",
        "compliance",
        "regulation",
        "copyright",
        "patent",
        "trademark",
        "lawsuit",
        "attorney",
        "lawyer",
    ]

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
        # Classify sensitivity
        sensitivity = self.classify_sensitivity(task)

        # Estimate complexity
        complexity = self._estimate_complexity(task)

        # Decompose into sub-tasks
        sub_tasks = self._decompose_task(task, complexity)

        # Determine model requirements
        model_requirements = self._determine_model_requirements(sensitivity, complexity)

        # Group tasks that can run in parallel
        parallel_groups = self._identify_parallel_groups(sub_tasks)

        return TaskAnalysis(
            original_task=task,
            complexity=complexity,
            sub_tasks=sub_tasks,
            model_requirements=model_requirements,
            sensitivity=sensitivity,
            parallel_groups=parallel_groups,
        )

    def route_to_workers(self, sub_tasks: list[dict]) -> dict[str, list]:
        """
        Assign sub-tasks to appropriate workers.

        Args:
            sub_tasks: List of sub-task definitions

        Returns:
            Mapping of worker name to assigned tasks
        """
        worker_assignments: dict[str, list] = {
            "claude": [],
            "groq": [],
            "ollama": [],
            "gemini": [],
        }

        for task in sub_tasks:
            sensitivity = task.get("sensitivity", "external-ok")
            task_type = task.get("task_type", "summarize")

            # PII and legal tasks always go to Claude
            if sensitivity in ("pii", "legal"):
                worker_assignments["claude"].append(task)
            # Search and extract prefer fast external workers
            elif task_type in ("search", "extract"):
                worker_assignments["groq"].append(task)
            # Summarize prefers local workers
            elif task_type == "summarize":
                worker_assignments["ollama"].append(task)
            # Validate requires judgment - Claude
            elif task_type == "validate":
                worker_assignments["claude"].append(task)
            # Synthesize requires judgment - Claude
            elif task_type == "synthesize":
                worker_assignments["claude"].append(task)
            else:
                # Default to groq for speed
                worker_assignments["groq"].append(task)

        return worker_assignments

    def plan_execution(self, analysis: TaskAnalysis) -> ExecutionPlan:
        """
        Create execution plan with parallel/sequential ordering.

        Args:
            analysis: Task analysis result

        Returns:
            Execution plan with phases
        """
        phases = []
        worker_counts: dict[str, int] = {}

        # Group sub-tasks by dependency
        # For now, use parallel groups from analysis
        if analysis.parallel_groups:
            for group in analysis.parallel_groups:
                phase_tasks = [
                    st for st in analysis.sub_tasks if st.get("id") in group
                ]
                if phase_tasks:
                    phases.append({"sub_tasks": phase_tasks, "parallel": True})

        # If no parallel groups, execute sequentially
        if not phases:
            phases = [{"sub_tasks": analysis.sub_tasks, "parallel": False}]

        # Count workers needed
        assignments = self.route_to_workers(analysis.sub_tasks)
        for worker, tasks in assignments.items():
            if tasks:
                worker_counts[worker] = len(tasks)

        # Determine if validation is required
        requires_validation = (
            analysis.complexity == Complexity.HIGH
            or analysis.sensitivity in (Sensitivity.PII, Sensitivity.LEGAL)
        )

        return ExecutionPlan(
            phases=phases,
            estimated_workers=worker_counts,
            requires_validation=requires_validation,
        )

    def classify_sensitivity(self, task: str) -> Sensitivity:
        """
        Classify task sensitivity.

        Args:
            task: Task description

        Returns:
            Sensitivity level
        """
        task_lower = task.lower()

        # Check for PII indicators
        for keyword in self.PII_KEYWORDS:
            if keyword in task_lower:
                return Sensitivity.PII

        # Check for legal indicators
        for keyword in self.LEGAL_KEYWORDS:
            if keyword in task_lower:
                return Sensitivity.LEGAL

        return Sensitivity.EXTERNAL_OK

    def _estimate_complexity(self, task: str) -> Complexity:
        """Estimate task complexity based on heuristics."""
        # Word count as proxy for complexity
        word_count = len(task.split())

        # Check for complexity indicators
        has_multiple_steps = any(
            word in task.lower()
            for word in ["and", "then", "after", "also", "multiple", "several"]
        )
        has_conditionals = any(
            word in task.lower() for word in ["if", "unless", "when", "depending"]
        )
        has_aggregation = any(
            word in task.lower() for word in ["all", "every", "combine", "aggregate"]
        )

        # Score complexity
        score = 0
        if word_count > 50:
            score += 2
        elif word_count > 20:
            score += 1

        if has_multiple_steps:
            score += 1
        if has_conditionals:
            score += 1
        if has_aggregation:
            score += 1

        if score >= 3:
            return Complexity.HIGH
        elif score >= 1:
            return Complexity.MEDIUM
        else:
            return Complexity.LOW

    def _decompose_task(
        self, task: str, complexity: Complexity
    ) -> list[dict[str, Any]]:
        """Decompose task into atomic sub-tasks."""
        sub_tasks = []

        # Simple tasks don't need decomposition
        if complexity == Complexity.LOW:
            task_type = self._infer_task_type(task)
            return [
                {
                    "id": "main-task",
                    "description": task,
                    "task_type": task_type,
                    "sensitivity": self.classify_sensitivity(task).value,
                }
            ]

        # Split on conjunctions for medium/high complexity
        # Look for "and", "then", numbered lists, etc.
        parts = self._split_task(task)

        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            task_type = self._infer_task_type(part)
            sensitivity = self.classify_sensitivity(part).value

            sub_tasks.append(
                {
                    "id": f"subtask-{i+1}",
                    "description": part,
                    "task_type": task_type,
                    "sensitivity": sensitivity,
                    "depends_on": [f"subtask-{i}"] if i > 0 else None,
                }
            )

        # If no split happened, return single task
        if not sub_tasks:
            task_type = self._infer_task_type(task)
            return [
                {
                    "id": "main-task",
                    "description": task,
                    "task_type": task_type,
                    "sensitivity": self.classify_sensitivity(task).value,
                }
            ]

        return sub_tasks

    def _split_task(self, task: str) -> list[str]:
        """Split task into parts based on conjunctions and structure."""
        parts = []

        # Try splitting on numbered items (1. 2. 3. or 1) 2) 3))
        numbered = re.split(r"\d+[\.\)]\s*", task)
        if len(numbered) > 2:
            parts = [p.strip() for p in numbered if p.strip()]
            return parts

        # Try splitting on "then", "after that", "next"
        sequence_split = re.split(r"\s+(?:then|after that|next|finally)\s+", task, flags=re.I)
        if len(sequence_split) > 1:
            return sequence_split

        # Try splitting on " and " (but be careful not to over-split)
        and_split = task.split(" and ")
        if len(and_split) > 1 and all(len(p.split()) > 3 for p in and_split):
            return and_split

        return [task]

    def _infer_task_type(self, task: str) -> str:
        """Infer task type from task description."""
        task_lower = task.lower()

        for task_type, keywords in self.TASK_TYPE_KEYWORDS.items():
            if any(kw in task_lower for kw in keywords):
                return task_type

        # Default to summarize
        return "summarize"

    def _determine_model_requirements(
        self, sensitivity: Sensitivity, complexity: Complexity
    ) -> list[str]:
        """Determine which model tiers are needed."""
        models = []

        # High sensitivity always needs Claude
        if sensitivity in (Sensitivity.PII, Sensitivity.LEGAL):
            models.append("claude")
        # High complexity benefits from more capable models
        elif complexity == Complexity.HIGH:
            models.append("claude")
            models.append("groq")
        # Medium complexity can use fast models
        elif complexity == Complexity.MEDIUM:
            models.append("groq")
            models.append("ollama")
        # Low complexity can use any
        else:
            models.append("ollama")
            models.append("groq")

        return models

    def _identify_parallel_groups(
        self, sub_tasks: list[dict[str, Any]]
    ) -> list[list[str]]:
        """Identify groups of tasks that can run in parallel."""
        parallel_groups = []
        current_group = []

        for task in sub_tasks:
            depends_on = task.get("depends_on")

            if depends_on:
                # This task depends on others, start new group
                if current_group:
                    parallel_groups.append(current_group)
                current_group = [task["id"]]
            else:
                # No dependencies, can run in parallel
                current_group.append(task["id"])

        if current_group:
            parallel_groups.append(current_group)

        return parallel_groups
