#!/usr/bin/env python3
"""
tank.py - Mini aquarium for AI memory

A super small reef prototype. One file. Any AI swims.

Usage:
    python tank.py init              # Create tank
    python tank.py swim              # Show what AI sees
    python tank.py drop "insight"    # Add to tank
    python tank.py vitals            # Tank health

By Nolan Figueroa - inventor of digital reefs
"""

import json
import sys
from datetime import datetime
from pathlib import Path

TANK_DIR = Path(".reef")
TANK_FILE = TANK_DIR / "tank.json"


def init():
    """Create a new tank."""
    TANK_DIR.mkdir(exist_ok=True)

    if TANK_FILE.exists():
        print("Tank already exists. Swimming...")
        swim()
        return

    tank = {
        "created": datetime.now().isoformat(),
        "version": 1,
        "polips": [],
        "vitality": 100,
    }

    TANK_FILE.write_text(json.dumps(tank, indent=2))
    print("🐠 Tank created. Drop some knowledge in.")


def load_tank():
    """Load tank state."""
    if not TANK_FILE.exists():
        print("No tank. Run: python tank.py init")
        sys.exit(1)
    return json.loads(TANK_FILE.read_text())


def save_tank(tank):
    """Save tank state."""
    tank["updated"] = datetime.now().isoformat()
    TANK_FILE.write_text(json.dumps(tank, indent=2))


def swim():
    """Show what AI sees - the reef projection."""
    tank = load_tank()

    print(f"# Tank ({len(tank['polips'])} polips, vitality: {tank['vitality']})")
    print()

    if not tank["polips"]:
        print("Empty tank. Drop something in:")
        print("  python tank.py drop \"your insight here\"")
        return

    # Sort by recency (newest first for active context)
    polips = sorted(tank["polips"], key=lambda p: p.get("ts", ""), reverse=True)

    for p in polips[:10]:  # Show top 10
        age = _age_str(p.get("ts", ""))
        print(f"- [{age}] {p['content'][:80]}")


def drop(content):
    """Add a polip to the tank."""
    tank = load_tank()

    polip = {
        "content": content,
        "ts": datetime.now().isoformat(),
        "vitality": 100,
    }

    tank["polips"].append(polip)

    # Decay old polips
    _decay(tank)

    save_tank(tank)
    print(f"🫧 Dropped: {content[:50]}...")


def vitals():
    """Show tank health."""
    tank = load_tank()

    total = len(tank["polips"])
    if total == 0:
        print("Empty tank.")
        return

    # Compute stats
    thriving = sum(1 for p in tank["polips"] if p.get("vitality", 0) >= 80)
    calcifying = sum(1 for p in tank["polips"] if 20 <= p.get("vitality", 0) < 80)
    decaying = sum(1 for p in tank["polips"] if p.get("vitality", 0) < 20)

    avg_vitality = sum(p.get("vitality", 50) for p in tank["polips"]) / total
    tank["vitality"] = int(avg_vitality)
    save_tank(tank)

    print(f"Tank Vitals")
    print(f"  Total polips: {total}")
    print(f"  Thriving:     {thriving}")
    print(f"  Calcifying:   {calcifying}")
    print(f"  Decaying:     {decaying}")
    print(f"  Avg vitality: {avg_vitality:.0f}")


def _decay(tank):
    """Apply decay to old polips."""
    now = datetime.now()

    for p in tank["polips"]:
        ts = p.get("ts")
        if not ts:
            continue

        try:
            created = datetime.fromisoformat(ts)
            age_hours = (now - created).total_seconds() / 3600

            # Decay: lose 1 vitality per hour
            p["vitality"] = max(0, 100 - int(age_hours))
        except:
            pass

    # Remove dead polips (vitality 0)
    tank["polips"] = [p for p in tank["polips"] if p.get("vitality", 0) > 0]


def _age_str(ts):
    """Human-readable age."""
    if not ts:
        return "?"
    try:
        created = datetime.fromisoformat(ts)
        delta = datetime.now() - created

        if delta.days > 0:
            return f"{delta.days}d"
        elif delta.seconds >= 3600:
            return f"{delta.seconds // 3600}h"
        elif delta.seconds >= 60:
            return f"{delta.seconds // 60}m"
        else:
            return "now"
    except:
        return "?"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "init":
        init()
    elif cmd == "swim":
        swim()
    elif cmd == "drop":
        if len(sys.argv) < 3:
            print("Usage: python tank.py drop \"your insight\"")
            return
        drop(" ".join(sys.argv[2:]))
    elif cmd == "vitals":
        vitals()
    else:
        print(f"Unknown: {cmd}")
        print("Commands: init, swim, drop, vitals")


if __name__ == "__main__":
    main()
