"""
External worker infrastructure - distribute work to free models.

Workers:
- dispatcher: Routes tasks to appropriate workers
- groq: Groq API client (fast inference)
- ollama: Ollama local model client
- gemini: Google Gemini API client

All workers use stdlib HTTP only (zero dependencies constraint).
"""

from .dispatcher import WorkerDispatcher
from .groq import GroqWorker
from .ollama import OllamaWorker
from .gemini import GeminiWorker

__all__ = ['WorkerDispatcher', 'GroqWorker', 'OllamaWorker', 'GeminiWorker']
