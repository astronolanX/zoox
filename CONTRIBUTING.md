# Contributing to reef

Thanks for your interest in reef! This document explains how to get involved.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/nolan/reef
cd reef

# Install dependencies (uses uv, not pip)
uv sync

# Run tests
uv run pytest

# Run a specific test
uv run pytest tests/test_blob.py -v

# Run with coverage
uv run pytest --cov=reef
```

## Development Principles

### Zero Dependencies

reef uses **stdlib only**. No external packages allowed. This ensures:
- Simple installation
- No dependency conflicts
- Predictable behavior
- Easy auditing

If you need functionality from an external package, either:
1. Implement it yourself (preferred)
2. Make a compelling case for an exception (rare)

### Package Manager

Use **uv**, not pip:
```bash
uv sync          # Install dependencies
uv run pytest    # Run tests
uv run python    # Run Python with project in path
```

## How to Contribute

### Bug Reports

File an issue with:
- reef version (`reef --version` or check pyproject.toml)
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant error messages or logs

### Feature Requests

File an issue describing:
- **Problem** - What are you trying to accomplish?
- **Proposal** - How would this feature work?
- **Alternatives** - What other approaches did you consider?
- **Context** - Any additional information

Check [ROADMAP.md](ROADMAP.md) first - your idea might already be planned.

### Pull Requests

1. **Fork** the repository
2. **Branch** from main: `git checkout -b feat/my-feature`
3. **Code** your changes with tests
4. **Test** locally: `uv run pytest`
5. **Commit** with conventional format (see below)
6. **Push** to your fork
7. **PR** with clear description of changes

## Code Style

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new template command
fix: handle empty polip summaries
chore: update test fixtures
docs: clarify drift scope filtering
refactor: simplify index rebuild logic
test: add stress tests for cleanup
```

### Python Style

- **Type hints** on all public functions
- **Docstrings** for modules, classes, and public functions
- **No external dependencies** - stdlib only
- **Tests** for new functionality

```python
def surface_relevant(
    self,
    query: str,
    limit: int = 10,
    types: Optional[List[PolipType]] = None,
) -> List[Polip]:
    """Surface polips relevant to a query.

    Args:
        query: Search string for relevance scoring
        limit: Maximum polips to return
        types: Filter by polip types (None = all)

    Returns:
        List of polips sorted by relevance score
    """
```

### File Organization

```
src/reef/
  __init__.py    # Public API exports
  blob.py        # Core Polip/Reef classes
  cli.py         # CLI commands

tests/
  test_blob.py   # Unit tests for blob.py
  test_cli.py    # CLI integration tests
  stress_test.py # Performance/security stress tests
```

## Testing

### Run All Tests

```bash
uv run pytest
```

### Run Specific Tests

```bash
# By file
uv run pytest tests/test_blob.py

# By name pattern
uv run pytest -k "test_surface"

# With verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

### Test Coverage

```bash
uv run pytest --cov=reef --cov-report=html
open htmlcov/index.html
```

## Architecture Overview

```
Polip (blob.py)
  - Individual memory unit
  - XML serialization
  - Type: thread, decision, constraint, context, fact
  - Scope: session, project, always

Reef (blob.py)
  - Collection of polips
  - Directory-based storage (.claude/)
  - Surfacing with TF-IDF relevance
  - Wiki linking and LRU tracking

CLI (cli.py)
  - Command routing
  - User-facing interface
  - Hook integration for Claude Code
```

## Questions?

- **Bug?** File an issue
- **Feature idea?** File an issue
- **Question?** File an issue (we'll add Discussions if there's demand)
- **Want to chat?** Find me on Twitter/X

Thanks for contributing!
