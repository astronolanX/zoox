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
import time


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

    def __init__(self, project_dir: Path | None = None):
        """
        Initialize dispatcher.

        Args:
            project_dir: Project directory containing .claude/workers/config.json
        """
        self.project_dir = project_dir or Path.cwd()
        self._workers: dict[str, Any] = {}
        self._config: dict[str, Any] | None = None

    @property
    def config_path(self) -> Path:
        """Path to worker config file."""
        return self.project_dir / ".claude" / "workers" / "config.json"

    def _load_config(self) -> dict[str, Any]:
        """Load worker configuration from JSON."""
        if self._config is not None:
            return self._config

        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._config = {}
        else:
            self._config = {}

        return self._config

    def _get_worker_config(self, worker_name: str) -> dict[str, Any]:
        """Get configuration for specific worker."""
        config = self._load_config()
        return config.get("workers", {}).get(worker_name, {})

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
        # Normalize enums
        if isinstance(task_type, str):
            task_type = TaskType(task_type)
        if isinstance(sensitivity, str):
            sensitivity = Sensitivity(sensitivity)

        # Check if task requires Claude (not available through workers)
        if sensitivity in (Sensitivity.PII, Sensitivity.LEGAL):
            return WorkerResult(
                success=False,
                output=None,
                worker_name="none",
                model_used="none",
                latency_ms=0,
                error=f"Task requires Claude (sensitivity: {sensitivity.value}). Use Claude Code directly.",
            )

        # Select worker
        worker_name = self._select_worker(task_type, sensitivity)
        if worker_name is None:
            return WorkerResult(
                success=False,
                output=None,
                worker_name="none",
                model_used="none",
                latency_ms=0,
                error="No workers available for this task",
            )

        # Get worker instance
        worker = self._get_worker_instance(worker_name)
        if worker is None:
            return WorkerResult(
                success=False,
                output=None,
                worker_name=worker_name,
                model_used="none",
                latency_ms=0,
                error=f"Failed to initialize worker: {worker_name}",
            )

        # Execute task
        start_time = time.time()
        try:
            response = worker.complete(prompt)
            latency_ms = int((time.time() - start_time) * 1000)

            return WorkerResult(
                success=True,
                output=response.content,
                worker_name=worker_name,
                model_used=response.model,
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            # Try fallback worker
            fallback = self._get_fallback_worker(worker_name, task_type, sensitivity)
            if fallback:
                return self._dispatch_to_worker(fallback, prompt)

            return WorkerResult(
                success=False,
                output=None,
                worker_name=worker_name,
                model_used="none",
                latency_ms=latency_ms,
                error=str(e),
            )

    def _dispatch_to_worker(self, worker_name: str, prompt: str) -> WorkerResult:
        """Dispatch directly to a specific worker."""
        worker = self._get_worker_instance(worker_name)
        if worker is None:
            return WorkerResult(
                success=False,
                output=None,
                worker_name=worker_name,
                model_used="none",
                latency_ms=0,
                error=f"Failed to initialize worker: {worker_name}",
            )

        start_time = time.time()
        try:
            response = worker.complete(prompt)
            latency_ms = int((time.time() - start_time) * 1000)

            return WorkerResult(
                success=True,
                output=response.content,
                worker_name=worker_name,
                model_used=response.model,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return WorkerResult(
                success=False,
                output=None,
                worker_name=worker_name,
                model_used="none",
                latency_ms=latency_ms,
                error=str(e),
            )

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

    def get_worker_status(self) -> dict[str, dict[str, Any]]:
        """
        Get detailed status of all workers.

        Returns:
            Dict mapping worker name to status info
        """
        status = {}

        for worker_name, worker_class in self._get_worker_classes().items():
            try:
                worker = worker_class()
                is_available = worker.is_available()

                worker_status = {
                    "available": is_available,
                    "configured": True,
                }

                # Add worker-specific info
                if worker_name == "ollama" and is_available:
                    worker_status["models"] = worker.list_models()
                    worker_status["host"] = worker.host

                if worker_name in ("groq", "gemini"):
                    worker_status["has_api_key"] = is_available

                status[worker_name] = worker_status

            except Exception as e:
                status[worker_name] = {
                    "available": False,
                    "configured": False,
                    "error": str(e),
                }

        return status

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

    def _get_worker_instance(self, worker_name: str):
        """Get or create worker instance."""
        if worker_name in self._workers:
            return self._workers[worker_name]

        worker_classes = self._get_worker_classes()
        if worker_name not in worker_classes:
            return None

        try:
            worker = worker_classes[worker_name]()
            self._workers[worker_name] = worker
            return worker
        except Exception:
            return None

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

    def _get_fallback_worker(
        self, failed_worker: str, task_type: TaskType, sensitivity: Sensitivity
    ) -> str | None:
        """
        Get fallback worker after failure.

        Args:
            failed_worker: Worker that failed
            task_type: Type of task
            sensitivity: Sensitivity level

        Returns:
            Fallback worker name or None
        """
        allowed = set(self.SENSITIVITY_ROUTING.get(sensitivity, []))
        preferred = self.DEFAULT_ROUTING.get(task_type, [])
        available = set(self.get_available_workers())

        # Find next available worker
        for worker in preferred:
            if worker != failed_worker and worker in allowed and worker in available:
                return worker

        return None
