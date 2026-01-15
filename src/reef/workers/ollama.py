"""
Ollama local model client.

Uses stdlib HTTP only (zero dependencies constraint).
"""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any


@dataclass
class OllamaResponse:
    """Response from Ollama API."""

    content: str
    model: str
    latency_ms: int


class OllamaWorker:
    """Ollama local model client."""

    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"

    def __init__(self, host: str | None = None):
        """
        Initialize Ollama client.

        Args:
            host: Ollama host URL. Defaults to http://localhost:11434.
        """
        self.host = host or self.DEFAULT_HOST

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError):
            return False

    def complete(
        self,
        prompt: str,
        model: str | None = None,
        stream: bool = False,
    ) -> OllamaResponse:
        """
        Send completion request to local Ollama.

        Args:
            prompt: Prompt to complete
            model: Model to use. Defaults to llama3.2.
            stream: Whether to stream response (not implemented)

        Returns:
            Ollama response

        Raises:
            RuntimeError: If Ollama not available or request fails
        """
        if not self.is_available():
            raise RuntimeError("Ollama is not running")

        model = model or self.DEFAULT_MODEL

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,  # Always non-streaming for simplicity
        }

        headers = {
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        import time
        start = time.time()

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
                latency_ms = int((time.time() - start) * 1000)

                return OllamaResponse(
                    content=data.get("response", ""),
                    model=data.get("model", model),
                    latency_ms=latency_ms,
                )

        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Ollama API error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama connection error: {e.reason}")

    def list_models(self) -> list[str]:
        """
        List available models.

        Returns:
            List of model names
        """
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except (urllib.error.URLError, urllib.error.HTTPError):
            return []
