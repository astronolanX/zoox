#!/bin/bash
# Trench completion harness - wraps Claude session with auto-merge on success
# Usage: trench_harness.sh <trench_name> <worktree_path> <task> <model> [--skip-permissions]

set -e

TRENCH_NAME="$1"
WORKTREE_PATH="$2"
TASK="$3"
MODEL="$4"
SKIP_PERMS="$5"

LOG_FILE="$WORKTREE_PATH/.claude-session.log"
STATUS_FILE="$WORKTREE_PATH/.reef-trench.json"
PROJECT_ROOT=$(cd "$WORKTREE_PATH" && git rev-parse --show-toplevel 2>/dev/null | head -1)

# Build claude command
CLAUDE_CMD="claude -p \"$TASK\" --model $MODEL"
if [ "$SKIP_PERMS" = "--skip-permissions" ]; then
    CLAUDE_CMD="$CLAUDE_CMD --dangerously-skip-permissions"
fi

# Run Claude task
echo "[trench:$TRENCH_NAME] Starting task with $MODEL" >> "$LOG_FILE"
cd "$WORKTREE_PATH"

eval $CLAUDE_CMD >> "$LOG_FILE" 2>&1
CLAUDE_EXIT=$?

echo "[trench:$TRENCH_NAME] Claude exited with code $CLAUDE_EXIT" >> "$LOG_FILE"

if [ $CLAUDE_EXIT -ne 0 ]; then
    echo "[trench:$TRENCH_NAME] Task failed - aborting trench" >> "$LOG_FILE"
    # Auto-abort and clean up
    cd "$PROJECT_ROOT"
    uv run python -m reef.cli trench abort "$TRENCH_NAME" --force >> "$LOG_FILE" 2>&1 || true
    echo "[TRENCH FAILED] $TRENCH_NAME: Claude task exited with code $CLAUDE_EXIT"
    exit 1
fi

# Run tests
echo "[trench:$TRENCH_NAME] Running tests..." >> "$LOG_FILE"
if uv run pytest -x 2>&1 | tee -a "$LOG_FILE"; then
    echo "[trench:$TRENCH_NAME] Tests passed - auto-merging" >> "$LOG_FILE"

    # Update status to READY
    python3 -c "
import json
from pathlib import Path
status_file = Path('$STATUS_FILE')
if status_file.exists():
    data = json.loads(status_file.read_text())
    data['status'] = 'ready'
    status_file.write_text(json.dumps(data, indent=2))
"

    # Auto-merge from main repo
    cd "$PROJECT_ROOT"
    uv run python -m reef.cli trench merge "$TRENCH_NAME" >> "$LOG_FILE" 2>&1

    echo "[trench:$TRENCH_NAME] Merged and cleaned up" >> "$LOG_FILE"
else
    echo "[trench:$TRENCH_NAME] Tests failed - aborting trench" >> "$LOG_FILE"
    # Auto-abort and clean up
    cd "$PROJECT_ROOT"
    uv run python -m reef.cli trench abort "$TRENCH_NAME" --force >> "$LOG_FILE" 2>&1 || true
    echo "[TRENCH FAILED] $TRENCH_NAME: Tests failed"
    exit 1
fi
