"""
Google Gemini API client.

Uses stdlib HTTP only (zero dependencies constraint).
"""

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass


@dataclass
class GeminiResponse:
    """Response from Gemini API."""

    content: str
    model: str
    usage: dict[str, int]
    latency_ms: int


class GeminiWorker:
    """Google Gemini API client."""

    API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: str | None = None):
        """
        Initialize Gemini client.

        Args:
            api_key: Gemini API key. Defaults to GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    def is_available(self) -> bool:
        """Check if Gemini is available (API key configured)."""
        return bool(self.api_key)

    def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> GeminiResponse:
        """
        Send completion request to Gemini.

        Args:
            prompt: Prompt to complete
            model: Model to use. Defaults to gemini-2.0-flash.
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Gemini response

        Raises:
            ValueError: If API key not configured
            RuntimeError: If API request fails
        """
        if not self.api_key:
            raise ValueError("Gemini API key not configured")

        model = model or self.DEFAULT_MODEL

        # Gemini API format
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        url = f"{self.API_URL}/{model}:generateContent?key={self.api_key}"

        headers = {
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(
            url,
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

                # Extract content from Gemini response format
                content = ""
                if "candidates" in data and data["candidates"]:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        content = "".join(p.get("text", "") for p in parts)

                # Extract usage metadata
                usage = {}
                if "usageMetadata" in data:
                    meta = data["usageMetadata"]
                    usage = {
                        "prompt_tokens": meta.get("promptTokenCount", 0),
                        "completion_tokens": meta.get("candidatesTokenCount", 0),
                        "total_tokens": meta.get("totalTokenCount", 0),
                    }

                return GeminiResponse(
                    content=content,
                    model=model,
                    usage=usage,
                    latency_ms=latency_ms,
                )

        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Gemini API error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Gemini connection error: {e.reason}")
