# Reef Workers Guide

Reef workers enable task offloading to external models (Groq, Ollama, Gemini) for parallel execution and cost optimization.

## Overview

Workers complement Claude by handling:
- **Search & extraction** → Fast inference (Groq, Gemini)
- **Summarization** → Local models (Ollama) or cloud (Groq)
- **Batch processing** → Parallel execution across multiple workers

**Sensitive data** (PII, legal) always routes to Claude, never external workers.

## Worker Comparison

| Worker | Speed | Cost | Best For | Constraints |
|--------|-------|------|----------|-------------|
| **Groq** | ⚡⚡⚡ Very fast | 💰 Free tier | Search, extract, quick tasks | API key required |
| **Ollama** | ⚡⚡ Fast | 💰💰💰 Free (local) | Summarize, privacy-sensitive | Local install required |
| **Gemini** | ⚡⚡ Fast | 💰 Free tier | Extract, multimodal | API key required |

## Setup

### 1. Groq

**Fast inference with Llama models.**

1. Get API key: https://console.groq.com/keys
2. Set environment variable:
   ```bash
   export GROQ_API_KEY="gsk_..."
   ```
3. Verify:
   ```bash
   reef workers status
   # Should show: groq [available]
   ```

**Configuration:**
```json
{
  "workers": {
    "groq": {
      "api_key_env": "GROQ_API_KEY",
      "default_model": "llama-3.3-70b-versatile",
      "timeout": 30
    }
  }
}
```

**Models:**
- `llama-3.3-70b-versatile` (default) - Best balance of speed/quality
- `llama-3.1-8b-instant` - Ultra-fast for simple tasks
- `mixtral-8x7b-32768` - Long context window

**Rate limits:**
- Free tier: 30 requests/minute
- Token limits vary by model

### 2. Ollama

**Local inference for privacy and offline work.**

1. Install Ollama: https://ollama.com/download
2. Start service:
   ```bash
   ollama serve
   ```
3. Pull models:
   ```bash
   ollama pull llama3.2
   ollama pull qwen2.5-coder:7b
   ```
4. Verify:
   ```bash
   reef workers status
   # Should show: ollama [available]
   ```

**Configuration:**
```json
{
  "workers": {
    "ollama": {
      "host": "http://localhost:11434",
      "default_model": "llama3.2",
      "timeout": 120
    }
  }
}
```

**Recommended models:**
- `llama3.2` (default) - General purpose, 3B params
- `qwen2.5-coder:7b` - Code-focused tasks
- `deepseek-r1:7b` - Reasoning and analysis
- `mistral:7b` - Fast general purpose

**Hardware requirements:**
- 8GB RAM minimum
- 16GB RAM recommended for 7B+ models

### 3. Gemini

**Google's multimodal models with fast inference.**

1. Get API key: https://aistudio.google.com/apikey
2. Set environment variable:
   ```bash
   export GEMINI_API_KEY="AIza..."
   ```
3. Verify:
   ```bash
   reef workers status
   # Should show: gemini [available]
   ```

**Configuration:**
```json
{
  "workers": {
    "gemini": {
      "api_key_env": "GEMINI_API_KEY",
      "default_model": "gemini-2.0-flash",
      "timeout": 30
    }
  }
}
```

**Models:**
- `gemini-2.0-flash` (default) - Fast, multimodal
- `gemini-2.0-flash-exp` - Experimental with latest features
- `gemini-1.5-flash` - Stable, production-ready

**Rate limits:**
- Free tier: 15 requests/minute
- 1 million tokens/minute

## Worker Configuration

Configuration file: `.claude/workers/config.json`

### Full Example

```json
{
  "version": 1,
  "workers": {
    "groq": {
      "api_key_env": "GROQ_API_KEY",
      "default_model": "llama-3.3-70b-versatile",
      "timeout": 30,
      "max_retries": 2
    },
    "ollama": {
      "host": "http://localhost:11434",
      "default_model": "llama3.2",
      "timeout": 120,
      "models": {
        "code": "qwen2.5-coder:7b",
        "general": "llama3.2",
        "reasoning": "deepseek-r1:7b"
      }
    },
    "gemini": {
      "api_key_env": "GEMINI_API_KEY",
      "default_model": "gemini-2.0-flash",
      "timeout": 30,
      "max_retries": 2
    }
  },
  "routing": {
    "search": ["groq", "gemini"],
    "summarize": ["ollama", "groq"],
    "validate": ["claude"],
    "extract": ["groq", "gemini"],
    "synthesize": ["claude"]
  },
  "sensitivity": {
    "pii": ["claude"],
    "legal": ["claude"],
    "external-ok": ["groq", "ollama", "gemini"]
  }
}
```

### Routing Rules

**Task type routing** (in priority order):

```python
TaskType.SEARCH → ["groq", "gemini"]
TaskType.SUMMARIZE → ["ollama", "groq"]
TaskType.VALIDATE → ["claude"]
TaskType.EXTRACT → ["groq", "gemini"]
TaskType.SYNTHESIZE → ["claude"]
```

**Sensitivity routing** (enforced):

```python
Sensitivity.PII → ["claude"]  # Never external
Sensitivity.LEGAL → ["claude"]  # Never external
Sensitivity.EXTERNAL_OK → ["groq", "ollama", "gemini"]
```

## CLI Commands

### Check Worker Status

```bash
# View all workers
reef workers status

# Example output:
# Workers:
#   groq     [available] llama-3.3-70b-versatile
#   ollama   [available] llama3.2, qwen2.5-coder:7b
#   gemini   [available] gemini-2.0-flash
```

### Test Worker

```bash
# Test specific worker
reef workers test groq --prompt "What is 2+2?"

# Output:
# Worker: groq
# Model: llama-3.3-70b-versatile
# Latency: 124ms
# Response: 2+2 equals 4.
```

### Configure Workers

```bash
# Initialize config file
reef workers init

# Set API keys interactively
reef workers configure

# Edit config manually
$EDITOR .claude/workers/config.json
```

## Python API

### Basic Usage

```python
from reef.workers import WorkerDispatcher, TaskType, Sensitivity

dispatcher = WorkerDispatcher()

# Simple dispatch
result = dispatcher.dispatch(
    task_type=TaskType.SUMMARIZE,
    prompt="Summarize this paragraph: ...",
    sensitivity=Sensitivity.EXTERNAL_OK
)

print(result.output)  # Summarized text
print(f"Worker: {result.worker_name}")  # e.g., "ollama"
print(f"Latency: {result.latency_ms}ms")
```

### Advanced: Direct Worker Access

```python
from reef.workers import GroqWorker, OllamaWorker, GeminiWorker

# Groq
groq = GroqWorker()
if groq.is_available():
    response = groq.complete("What is asyncio?")
    print(response.content)

# Ollama
ollama = OllamaWorker()
models = ollama.list_models()
response = ollama.complete("Explain decorators", model="llama3.2")

# Gemini
gemini = GeminiWorker()
response = gemini.complete(
    "Extract dates from: Meeting on Jan 15, 2025",
    model="gemini-2.0-flash"
)
```

### Fallback Handling

The dispatcher automatically falls back to alternate workers on failure:

```python
result = dispatcher.dispatch(
    task_type=TaskType.SEARCH,
    prompt="Search for Python asyncio docs",
    sensitivity=Sensitivity.EXTERNAL_OK
)

# If groq fails, automatically tries gemini
# If both fail, returns error result
if not result.success:
    print(f"All workers failed: {result.error}")
```

## Best Practices

### 1. Task Routing

**Use Groq for:**
- Quick searches and lookups
- Extracting structured data
- Fast batch processing

**Use Ollama for:**
- Privacy-sensitive (non-PII) data
- Offline work
- Cost-free summarization

**Use Gemini for:**
- Multimodal tasks (future: images, video)
- Large context extraction
- Complex structured data

**Use Claude for:**
- PII or legal data
- Complex reasoning and synthesis
- Validation and quality checks

### 2. Sensitivity Classification

Always classify task sensitivity:

```python
# PII data → Claude only
dispatcher.dispatch(
    task_type=TaskType.SUMMARIZE,
    prompt="Summarize user profile: John Doe, SSN 123-45-6789",
    sensitivity=Sensitivity.PII  # Routes to Claude
)

# Public data → External OK
dispatcher.dispatch(
    task_type=TaskType.SEARCH,
    prompt="Search Python docs for asyncio examples",
    sensitivity=Sensitivity.EXTERNAL_OK  # Routes to Groq/Gemini
)
```

### 3. Error Handling

```python
result = dispatcher.dispatch(
    task_type=TaskType.SUMMARIZE,
    prompt="...",
    sensitivity=Sensitivity.EXTERNAL_OK
)

if result.success:
    process_output(result.output)
else:
    logger.error(f"Worker failed: {result.error}")
    # Fall back to Claude or retry
```

### 4. Monitoring

Track worker usage for optimization:

```python
from reef.agents import ReefOrchestrator

orchestrator = ReefOrchestrator()
result = orchestrator.execute_task("Complex research task")

# Check which workers were used
print(f"Workers: {result.output['workers_used']}")
print(f"Total latency: {result.output['total_latency_ms']}ms")

# Worker breakdown
for worker_result in result.worker_results:
    print(f"{worker_result.worker_used}: {worker_result.latency_ms}ms")
```

## Troubleshooting

### Groq: "API key not configured"

```bash
# Check environment variable
echo $GROQ_API_KEY

# Set if missing
export GROQ_API_KEY="gsk_..."

# Persist in shell profile
echo 'export GROQ_API_KEY="gsk_..."' >> ~/.zshrc
```

### Ollama: "Connection error"

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# If port conflict, change port
ollama serve --port 11435

# Update config.json
{
  "workers": {
    "ollama": {
      "host": "http://localhost:11435"
    }
  }
}
```

### Gemini: "Rate limit exceeded"

```bash
# Check current rate limit status
reef workers status gemini

# Wait 60 seconds or upgrade to paid tier
# Free tier: 15 requests/minute
```

### Worker not available

```bash
# Check detailed status
reef workers status

# Test specific worker
reef workers test ollama

# Check logs
reef workers logs ollama
```

## Zero Dependencies

All workers use **stdlib HTTP only** (no external packages):

- `urllib.request` for HTTP
- `json` for payload/response
- `os` for environment variables

This maintains reef's zero-dependency constraint while enabling external model integration.

## Next Steps

- See [AGENT-SDK.md](AGENT-SDK.md) for orchestrator patterns
- Check `examples/workers/` for usage examples
- Read `src/reef/workers/` for implementation details
