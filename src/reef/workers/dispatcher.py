"""
Worker dispatcher - route tasks to appropriate external models.

Routes based on:
- Task type (search, summarize, validate, extract)
- Sensitivity (pii, legal, external-ok)
- Worker availability
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
import json


class TaskType(Enum):
    """Task types for routing."""

    SEARCH = "search"
    SUMMARIZE = "summarize"
    VALIDATE = "validate"
    EXTRACT = "extract"
    SYNTHESIZE = "synthesize"


class Sensitivity(Enum):
    """Sensitivity levels for routing."""

    PII = "pii"
    LEGAL = "legal"
    EXTERNAL_OK = "external-ok"


@dataclass
class WorkerResult:
    """Result from worker execution."""

    success: bool
    output: Any
    worker_name: str
    model_used: str
    latency_ms: int
    error: str | None = None


class WorkerDispatcher:
    """Route tasks to appropriate external models."""

    # Default routing rules
    DEFAULT_ROUTING = {
        TaskType.SEARCH: ["groq", "gemini"],
        TaskType.SUMMARIZE: ["ollama", "groq"],
        TaskType.VALIDATE: ["claude"],
        TaskType.EXTRACT: ["groq", "gemini"],
        TaskType.SYNTHESIZE: ["claude"],
    }

    # Sensitivity constraints
    SENSITIVITY_ROUTING = {
        Sensitivity.PII: ["claude"],
        Sensitivity.LEGAL: ["claude"],
        Sensitivity.EXTERNAL_OK: ["groq", "ollama", "gemini"],
    }

    def __init__(self, config_path: Path | None = None):
        """
        Initialize dispatcher.

        Args:
            config_path: Path to worker config YAML.
                        Defaults to .claude/workers/config.yaml
        """
        self.config_path = config_path
        self._workers: dict[str, Any] = {}
        self._config: dict[str, Any] = {}

    def _load_config(self) -> dict[str, Any]:
        """Load worker configuration."""
        if self._config:
            return self._config

        if self.config_path and self.config_path.exists():
            # Simple YAML-like parsing (stdlib only)
            content = self.config_path.read_text()
            # Will implement proper parsing in Phase 2
            self._config = {}
        else:
            self._config = {}

        return self._config

    def dispatch(
        self,
        task_type: str | TaskType,
        prompt: str,
        sensitivity: str | Sensitivity = Sensitivity.EXTERNAL_OK,
    ) -> WorkerResult:
        """
        Route task to best available worker.

        Args:
            task_type: Type of task
            prompt: Task prompt
            sensitivity: Sensitivity level

        Returns:
            Worker execution result
        """
        # Will be implemented in Phase 2
        raise NotImplementedError("Will be implemented in Phase 2")

    def get_available_workers(self) -> list[str]:
        """
        Discover available external models.

        Returns:
            List of available worker names
        """
        available = []

        # Check each worker type
        for worker_name, worker_class in self._get_worker_classes().items():
            try:
                worker = worker_class()
                if worker.is_available():
                    available.append(worker_name)
            except Exception:
                pass

        return available

    def _get_worker_classes(self) -> dict[str, type]:
        """Get worker class mapping."""
        from .groq import GroqWorker
        from .ollama import OllamaWorker
        from .gemini import GeminiWorker

        return {
            "groq": GroqWorker,
            "ollama": OllamaWorker,
            "gemini": GeminiWorker,
        }

    def _select_worker(
        self, task_type: TaskType, sensitivity: Sensitivity
    ) -> str | None:
        """
        Select best worker for task.

        Args:
            task_type: Type of task
            sensitivity: Sensitivity level

        Returns:
            Worker name or None if none available
        """
        # Get allowed workers for sensitivity
        allowed = set(self.SENSITIVITY_ROUTING.get(sensitivity, []))

        # Get preferred workers for task type
        preferred = self.DEFAULT_ROUTING.get(task_type, [])

        # Find first available preferred worker that's allowed
        available = set(self.get_available_workers())

        for worker in preferred:
            if worker in allowed and worker in available:
                return worker

        # Fallback to any allowed available worker
        for worker in allowed:
            if worker in available:
                return worker

        return None
