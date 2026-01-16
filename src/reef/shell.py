#!/usr/bin/env python3
"""
Reef Shell - REPL with ghost text hints and terminal control.

Usage:
    reef shell          # Start interactive session
    reef shell --hint   # Show current hint and exit
"""

import json
import os
import readline
import subprocess
import sys
import termios
import tty
from pathlib import Path
from typing import Optional

# ANSI escape codes
RESET = "\033[0m"
DIM = "\033[2m"
ITALIC = "\033[3m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
GRAY = "\033[90m"
CLEAR_LINE = "\033[2K"
CURSOR_UP = "\033[A"
CURSOR_START = "\033[G"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


def get_reef_hint() -> Optional[str]:
    """Get hint from reef status file with spark grades."""
    project_dir = Path.cwd()
    status_file = Path(f"/tmp/reef-{project_dir.name}.status")

    if not status_file.exists():
        return None

    try:
        with open(status_file) as f:
            state = json.load(f)

        vitality = state.get("vitality", {})
        vitality_icon = vitality.get("icon", "")
        vitality_score = vitality.get("score", 0)
        vitality_status = vitality.get("status", "unknown")
        grades = vitality.get("grades", {})
        grade_compact = grades.get("compact", "········")

        # Build compact statusline with spark grades
        polip_count = state.get("count", 0)
        trench_count = len(state.get("trenches", []))
        token_savings = state.get("token_savings_pct", 0)

        # Compact format: 🟠 40 [15p 0t 83%] [██····▓▓]
        compact_status = f"{vitality_icon} {vitality_score} [{polip_count}p {trench_count}t {token_savings}%] [{grade_compact}]"

        # Priority 1: Show vitality if reef is dying or declining (with action)
        if vitality_status in ["dying", "declining"]:
            action = vitality.get("recommended_action", "")
            return f"{compact_status} - {action}"

        # Priority 2: Active trenches
        trenches = state.get("trenches", [])
        if trenches:
            active = [t for t in trenches if t.get("status") in ["running", "testing"]]
            if active:
                return f"{compact_status} - {len(active)} trench{'es' if len(active) > 1 else ''} active"
            ready = [t for t in trenches if t.get("status") == "ready"]
            if ready:
                return f"{compact_status} - {len(ready)} trench{'es' if len(ready) > 1 else ''} ready to merge"

        # Priority 3: Active thread
        thread = state.get("active_thread")
        if thread:
            return f"{compact_status} - Continue: {thread}"

        # Priority 4: Show compact status with grades
        return compact_status

    except:
        return None


def get_next_steps() -> list[str]:
    """Get next steps from active thread polip."""
    project_dir = Path.cwd()
    claude_dir = project_dir / ".claude"

    # Find active thread
    threads_dir = claude_dir / "threads"
    if not threads_dir.exists():
        return []

    import xml.etree.ElementTree as ET

    for path in threads_dir.glob("*.blob.xml"):
        try:
            root = ET.parse(path).getroot()
            if root.get("status") == "active":
                next_el = root.find("next")
                if next_el is not None:
                    steps = []
                    for step in next_el.findall("step"):
                        if step.text:
                            steps.append(step.text.strip())
                    return steps[:3]  # Top 3
        except:
            continue

    return []


def print_ghost_hint(hint: str):
    """Print ghost hint text that will be overwritten."""
    # Print dim italic hint
    sys.stdout.write(f"{DIM}{ITALIC}{GRAY}{hint}{RESET}")
    sys.stdout.flush()
    # Move cursor back to start
    sys.stdout.write(f"\r")
    sys.stdout.flush()


def clear_ghost():
    """Clear the ghost hint line."""
    sys.stdout.write(f"{CLEAR_LINE}\r")
    sys.stdout.flush()


def read_char() -> str:
    """Read a single character without echo."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def input_with_ghost(prompt: str, ghost: Optional[str] = None) -> str:
    """Get input with ghost hint text."""
    if ghost:
        # Print prompt and ghost
        sys.stdout.write(prompt)
        print_ghost_hint(ghost)

        # Wait for first keypress
        ch = read_char()

        # Handle special keys
        if ch == '\x03':  # Ctrl+C
            print()
            raise KeyboardInterrupt
        if ch == '\x04':  # Ctrl+D
            print()
            raise EOFError

        # Clear ghost and use readline with pre-filled char
        clear_ghost()
        sys.stdout.write(prompt)
        sys.stdout.flush()

        # Use readline with the first char pre-filled
        readline.set_startup_hook(lambda: readline.insert_text(ch))
        try:
            line = input()
        finally:
            readline.set_startup_hook(None)

        return line
    else:
        return input(prompt)


def run_claude(message: str, conversation_id: Optional[str] = None) -> tuple[str, str]:
    """Run claude -p and return (output, conversation_id)."""
    cmd = ["claude", "-p", message, "--output-format", "stream-json"]

    if conversation_id:
        cmd.extend(["--continue", conversation_id])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        # Parse streamed JSON for conversation ID and output
        output_lines = []
        conv_id = conversation_id

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("type") == "result":
                    conv_id = data.get("session_id", conv_id)
                    output_lines.append(data.get("result", ""))
                elif data.get("type") == "assistant":
                    msg = data.get("message", {})
                    for block in msg.get("content", []):
                        if block.get("type") == "text":
                            output_lines.append(block.get("text", ""))
            except json.JSONDecodeError:
                output_lines.append(line)

        return '\n'.join(output_lines), conv_id or ""

    except subprocess.TimeoutExpired:
        return "[timeout]", conversation_id or ""
    except FileNotFoundError:
        return "[error: claude not found]", ""


def print_banner():
    """Print reef shell banner."""
    project_dir = Path.cwd()
    status_file = Path(f"/tmp/reef-{project_dir.name}.status")

    hint = get_reef_hint()
    steps = get_next_steps()

    print(f"{CYAN}reef shell{RESET}")

    # Show detailed stats if available
    try:
        with open(status_file) as f:
            state = json.load(f)
            count = state.get("count", 0)
            types = state.get("types", {})
            trenches = state.get("trenches", [])
            savings_pct = state.get("token_savings_pct", 0)
            vitality = state.get("vitality", {})

            # Show vitality first
            if vitality:
                icon = vitality.get("icon", "")
                status = vitality.get("status", "unknown")
                score = vitality.get("score", 0)
                days_since = vitality.get("days_since_activity")

                vitality_line = f"{icon} Reef {status} ({score}/100)"
                if days_since is not None:
                    if days_since == 0:
                        vitality_line += " • active today"
                    elif days_since == 1:
                        vitality_line += " • active yesterday"
                    else:
                        vitality_line += f" • {days_since}d since activity"

                print(f"{vitality_line}")

            if count > 0:
                type_summary = ", ".join(f"{v} {k}" for k, v in sorted(types.items())[:3])
                print(f"{DIM}{count} polips ({type_summary}) • {savings_pct}% token savings{RESET}")

            if trenches:
                by_status = {}
                for t in trenches:
                    s = t.get("status", "unknown")
                    by_status[s] = by_status.get(s, 0) + 1
                trench_summary = ", ".join(f"{v} {k}" for k, v in sorted(by_status.items()))
                print(f"{DIM}Trenches: {trench_summary}{RESET}")
    except:
        # Fall back to simple hint
        if hint:
            print(f"{DIM}{hint}{RESET}")

    if steps:
        print(f"{DIM}Next: {steps[0]}{RESET}")
    print()


def main():
    """Run reef shell REPL."""
    import argparse

    parser = argparse.ArgumentParser(description="Reef Shell")
    parser.add_argument("--hint", action="store_true", help="Show current hint and exit")
    args = parser.parse_args()

    if args.hint:
        hint = get_reef_hint()
        if hint:
            print(hint)
        return

    print_banner()

    conversation_id = None
    history_file = Path.home() / ".reef_history"

    # Load history
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass

    readline.set_history_length(1000)

    try:
        while True:
            # Get hint for ghost text
            hint = get_reef_hint()
            steps = get_next_steps()

            ghost = None
            if steps:
                ghost = steps[0]
            elif hint:
                ghost = hint

            try:
                prompt = f"{MAGENTA}>{RESET} "
                user_input = input_with_ghost(prompt, ghost)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print(f"\n{DIM}exiting{RESET}")
                break

            if not user_input.strip():
                continue

            # Handle commands
            if user_input.strip() == "/quit" or user_input.strip() == "/exit":
                break

            if user_input.strip() == "/hint":
                if hint:
                    print(f"{DIM}{hint}{RESET}")
                if steps:
                    print(f"{DIM}Next steps:{RESET}")
                    for i, step in enumerate(steps, 1):
                        print(f"  {i}. {step}")
                continue

            if user_input.strip() == "/steps":
                steps = get_next_steps()
                if steps:
                    for i, step in enumerate(steps, 1):
                        print(f"  {i}. {step}")
                else:
                    print(f"{DIM}No active thread with next steps{RESET}")
                continue

            # Run through claude
            print()
            output, conversation_id = run_claude(user_input, conversation_id)
            if output:
                print(output)
            print()

    finally:
        # Save history
        try:
            readline.write_history_file(history_file)
        except:
            pass

        print(f"{SHOW_CURSOR}", end="")


if __name__ == "__main__":
    main()
