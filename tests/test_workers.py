"""
Tests for reef worker infrastructure.

Phase 2 implementation complete:
- test_dispatcher_routing
- test_sensitivity_enforcement
- test_fallback_on_failure
- test_dispatch_pii_blocked
- test_worker_status
"""

import pytest
import os
from unittest.mock import patch, MagicMock, PropertyMock
import json
from pathlib import Path
import tempfile

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


class TestWorkerIntegration:
    """Integration tests for worker infrastructure."""

    def test_dispatcher_routing(self):
        """Full test of dispatcher routing logic."""
        disp = WorkerDispatcher()

        # Mock workers availability
        with patch.object(disp, 'get_available_workers', return_value=['groq', 'gemini']):
            # Test SEARCH routes to groq (first in preference list)
            worker = disp._select_worker(TaskType.SEARCH, Sensitivity.EXTERNAL_OK)
            assert worker == "groq"

            # Test SUMMARIZE prefers ollama, but falls back to groq if unavailable
            worker = disp._select_worker(TaskType.SUMMARIZE, Sensitivity.EXTERNAL_OK)
            assert worker == "groq"  # ollama not available, falls back to groq

        # Test with ollama available
        with patch.object(disp, 'get_available_workers', return_value=['ollama', 'groq']):
            worker = disp._select_worker(TaskType.SUMMARIZE, Sensitivity.EXTERNAL_OK)
            assert worker == "ollama"  # ollama is preferred

    def test_sensitivity_enforcement(self):
        """Full test of sensitivity enforcement."""
        disp = WorkerDispatcher()

        # PII tasks should not be routed to external workers
        result = disp.dispatch(TaskType.SEARCH, "test", Sensitivity.PII)
        assert result.success is False
        assert "requires Claude" in result.error

        # LEGAL tasks should not be routed to external workers
        result = disp.dispatch(TaskType.SUMMARIZE, "test", Sensitivity.LEGAL)
        assert result.success is False
        assert "requires Claude" in result.error

    def test_dispatch_pii_blocked(self):
        """Verify PII-sensitive tasks are blocked from external workers."""
        disp = WorkerDispatcher()

        # Even with workers available, PII should be blocked
        with patch.object(disp, 'get_available_workers', return_value=['groq', 'gemini', 'ollama']):
            result = disp.dispatch("search", "Find user SSN", "pii")
            assert result.success is False
            assert result.worker_name == "none"
            assert "pii" in result.error.lower()

    def test_no_workers_available(self):
        """Test handling when no workers are available."""
        disp = WorkerDispatcher()

        with patch.object(disp, 'get_available_workers', return_value=[]):
            result = disp.dispatch(TaskType.SEARCH, "test", Sensitivity.EXTERNAL_OK)
            assert result.success is False
            assert "No workers available" in result.error

    def test_worker_status(self):
        """Test worker status reporting."""
        disp = WorkerDispatcher()

        # Mock the worker classes
        with patch.dict("os.environ", {}, clear=True):
            status = disp.get_worker_status()

            # Should have all three workers in status
            assert "groq" in status
            assert "ollama" in status
            assert "gemini" in status

            # Without env vars, API-based workers should be unavailable
            assert status["groq"]["available"] is False
            assert status["gemini"]["available"] is False

    def test_config_loading(self):
        """Test configuration loading from JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            config_dir = project_dir / ".claude" / "workers"
            config_dir.mkdir(parents=True)

            # Create config file
            config = {
                "workers": {
                    "groq": {"enabled": True, "default_model": "test-model"}
                }
            }
            (config_dir / "config.json").write_text(json.dumps(config))

            disp = WorkerDispatcher(project_dir)
            loaded_config = disp._load_config()

            assert "workers" in loaded_config
            assert "groq" in loaded_config["workers"]

    def test_worker_result_dataclass(self):
        """Test WorkerResult dataclass."""
        result = WorkerResult(
            success=True,
            output="test output",
            worker_name="groq",
            model_used="llama-3.3-70b",
            latency_ms=100,
        )

        assert result.success is True
        assert result.output == "test output"
        assert result.worker_name == "groq"
        assert result.error is None

        # Test with error
        error_result = WorkerResult(
            success=False,
            output=None,
            worker_name="groq",
            model_used="none",
            latency_ms=50,
            error="Connection failed",
        )
        assert error_result.success is False
        assert error_result.error == "Connection failed"


class TestWorkerMocked:
    """Tests with mocked worker responses."""

    def test_groq_complete_mocked(self):
        """Test Groq completion with mocked response."""
        from reef.workers.groq import GroqResponse

        worker = GroqWorker(api_key="test-key")

        # Mock the HTTP request
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Hello from Groq!"}}],
            "model": "llama-3.3-70b-versatile",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            response = worker.complete("Say hello")

            assert isinstance(response, GroqResponse)
            assert response.content == "Hello from Groq!"
            assert response.model == "llama-3.3-70b-versatile"

    def test_gemini_complete_mocked(self):
        """Test Gemini completion with mocked response."""
        from reef.workers.gemini import GeminiResponse

        worker = GeminiWorker(api_key="test-key")

        # Mock the HTTP request
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": "Hello from Gemini!"}]}
            }],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 5,
                "totalTokenCount": 15,
            },
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            response = worker.complete("Say hello")

            assert isinstance(response, GeminiResponse)
            assert response.content == "Hello from Gemini!"


# Live tests - skipped by default, run with: pytest -m live
class TestWorkerLive:
    """Live tests requiring external APIs/services."""

    @pytest.mark.skip(reason="Requires GROQ_API_KEY")
    def test_groq_live(self):
        """Live test with Groq API."""
        worker = GroqWorker()
        if not worker.is_available():
            pytest.skip("GROQ_API_KEY not set")

        response = worker.complete("Say 'test' in one word")
        assert response.content
        assert response.model

    @pytest.mark.skip(reason="Requires GEMINI_API_KEY")
    def test_gemini_live(self):
        """Live test with Gemini API."""
        worker = GeminiWorker()
        if not worker.is_available():
            pytest.skip("GEMINI_API_KEY not set")

        response = worker.complete("Say 'test' in one word")
        assert response.content
        assert response.model

    @pytest.mark.skip(reason="Requires Ollama running")
    def test_ollama_live(self):
        """Live test with Ollama."""
        worker = OllamaWorker()
        if not worker.is_available():
            pytest.skip("Ollama not running")

        response = worker.complete("Say 'test' in one word")
        assert response.content
        assert response.model
