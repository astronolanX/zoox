"""
Groq API client for fast inference.

Uses stdlib HTTP only (zero dependencies constraint).
"""

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass


@dataclass
class GroqResponse:
    """Response from Groq API."""

    content: str
    model: str
    usage: dict[str, int]
    latency_ms: int


class GroqWorker:
    """Groq API client for fast inference."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str | None = None):
        """
        Initialize Groq client.

        Args:
            api_key: Groq API key. Defaults to GROQ_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")

    def is_available(self) -> bool:
        """Check if Groq is available (API key configured)."""
        return bool(self.api_key)

    def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> GroqResponse:
        """
        Send completion request to Groq.

        Args:
            prompt: Prompt to complete
            model: Model to use. Defaults to llama-3.3-70b-versatile.
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Groq response

        Raises:
            ValueError: If API key not configured
            RuntimeError: If API request fails
        """
        if not self.api_key:
            raise ValueError("Groq API key not configured")

        model = model or self.DEFAULT_MODEL

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        import time
        start = time.time()

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
                latency_ms = int((time.time() - start) * 1000)

                return GroqResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=data["model"],
                    usage=data.get("usage", {}),
                    latency_ms=latency_ms,
                )

        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Groq API error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Groq connection error: {e.reason}")
