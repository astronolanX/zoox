"""
Tests for reef worker infrastructure.

Phase 2 will implement:
- test_dispatcher_routing
- test_groq_client (mocked)
- test_ollama_client (mocked)
- test_gemini_client (mocked)
- test_sensitivity_enforcement
- test_fallback_on_failure
"""

import pytest
import os
from unittest.mock import patch, MagicMock
import json

from reef.workers import WorkerDispatcher, GroqWorker, OllamaWorker, GeminiWorker
from reef.workers.dispatcher import TaskType, Sensitivity, WorkerResult


class TestWorkerDispatcher:
    """Tests for worker dispatcher."""

    def test_import(self):
        """Verify module imports correctly."""
        assert WorkerDispatcher is not None

    def test_instantiation(self):
        """Verify can create dispatcher instance."""
        disp = WorkerDispatcher()
        assert disp is not None

    def test_task_type_enum(self):
        """Verify TaskType enum works."""
        assert TaskType.SEARCH.value == "search"
        assert TaskType.VALIDATE.value == "validate"

    def test_sensitivity_enum(self):
        """Verify Sensitivity enum works."""
        assert Sensitivity.PII.value == "pii"
        assert Sensitivity.EXTERNAL_OK.value == "external-ok"

    def test_default_routing_rules(self):
        """Verify default routing rules are defined."""
        disp = WorkerDispatcher()
        assert TaskType.SEARCH in disp.DEFAULT_ROUTING
        assert "groq" in disp.DEFAULT_ROUTING[TaskType.SEARCH]

    def test_sensitivity_routing_rules(self):
        """Verify sensitivity routing rules are defined."""
        disp = WorkerDispatcher()
        assert Sensitivity.PII in disp.SENSITIVITY_ROUTING
        assert "claude" in disp.SENSITIVITY_ROUTING[Sensitivity.PII]


class TestGroqWorker:
    """Tests for Groq worker client."""

    def test_import(self):
        """Verify module imports correctly."""
        assert GroqWorker is not None

    def test_instantiation(self):
        """Verify can create Groq worker instance."""
        worker = GroqWorker()
        assert worker is not None

    def test_is_available_without_key(self):
        """Verify is_available returns False without API key."""
        worker = GroqWorker(api_key=None)
        # Clear env var if set
        with patch.dict("os.environ", {}, clear=True):
            worker = GroqWorker()
            assert worker.is_available() is False

    def test_is_available_with_key(self):
        """Verify is_available returns True with API key."""
        worker = GroqWorker(api_key="test-key")
        assert worker.is_available() is True

    def test_complete_requires_key(self):
        """Verify complete raises without API key."""
        with patch.dict("os.environ", {}, clear=True):
            worker = GroqWorker(api_key=None)
            with pytest.raises(ValueError, match="API key"):
                worker.complete("test prompt")


class TestOllamaWorker:
    """Tests for Ollama worker client."""

    def test_import(self):
        """Verify module imports correctly."""
        assert OllamaWorker is not None

    def test_instantiation(self):
        """Verify can create Ollama worker instance."""
        worker = OllamaWorker()
        assert worker is not None

    def test_default_host(self):
        """Verify default host is localhost."""
        worker = OllamaWorker()
        assert "localhost" in worker.host

    def test_custom_host(self):
        """Verify custom host can be set."""
        worker = OllamaWorker(host="http://custom:11434")
        assert worker.host == "http://custom:11434"


class TestGeminiWorker:
    """Tests for Gemini worker client."""

    def test_import(self):
        """Verify module imports correctly."""
        assert GeminiWorker is not None

    def test_instantiation(self):
        """Verify can create Gemini worker instance."""
        worker = GeminiWorker()
        assert worker is not None

    def test_is_available_without_key(self):
        """Verify is_available returns False without API key."""
        with patch.dict("os.environ", {}, clear=True):
            worker = GeminiWorker()
            assert worker.is_available() is False

    def test_is_available_with_key(self):
        """Verify is_available returns True with API key."""
        worker = GeminiWorker(api_key="test-key")
        assert worker.is_available() is True


# Phase 2 TODO tests

class TestWorkerIntegration:
    """Integration tests for worker infrastructure."""

    @pytest.mark.skip(reason="Requires Phase 2 implementation")
    def test_dispatcher_routing(self):
        """Full test of dispatcher routing logic."""
        pass

    @pytest.mark.skip(reason="Requires Phase 2 implementation")
    def test_sensitivity_enforcement(self):
        """Full test of sensitivity enforcement."""
        pass

    @pytest.mark.skip(reason="Requires Phase 2 implementation")
    def test_fallback_on_failure(self):
        """Full test of fallback behavior."""
        pass

    @pytest.mark.skip(reason="Requires external API")
    def test_groq_live(self):
        """Live test with Groq API."""
        pass

    @pytest.mark.skip(reason="Requires external API")
    def test_gemini_live(self):
        """Live test with Gemini API."""
        pass

    @pytest.mark.skip(reason="Requires Ollama running")
    def test_ollama_live(self):
        """Live test with Ollama."""
        pass
