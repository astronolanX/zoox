#!/usr/bin/env python3
"""
tidepool.py - Mini aquarium for AI memory

A super small reef prototype. One file. Any AI swims.

Usage:
    python tidepool.py init              # Create tidepool
    python tidepool.py swim              # Show what AI sees
    python tidepool.py drop "insight"    # Add to tidepool
    python tidepool.py vitals            # Tidepool health

By Nolan Figueroa - inventor of digital reefs
"""

import json
import sys
from datetime import datetime
from pathlib import Path

TIDEPOOL_DIR = Path(".reef")
TIDEPOOL_FILE = TIDEPOOL_DIR / "tidepool.json"


def init():
    """Create a new tidepool."""
    TIDEPOOL_DIR.mkdir(exist_ok=True)

    if TIDEPOOL_FILE.exists():
        print("Tidepool already exists. Swimming...")
        swim()
        return

    tidepool = {
        "created": datetime.now().isoformat(),
        "version": 1,
        "polips": [],
        "vitality": 100,
    }

    TIDEPOOL_FILE.write_text(json.dumps(tidepool, indent=2))
    print("🐠 Tidepool created. Drop some knowledge in.")


def load_tidepool():
    """Load tidepool state."""
    if not TIDEPOOL_FILE.exists():
        print("No tidepool. Run: python tidepool.py init")
        sys.exit(1)
    return json.loads(TIDEPOOL_FILE.read_text())


def save_tidepool(tidepool):
    """Save tidepool state."""
    tidepool["updated"] = datetime.now().isoformat()
    TIDEPOOL_FILE.write_text(json.dumps(tidepool, indent=2))


def swim():
    """Show what AI sees - the reef projection."""
    tidepool = load_tidepool()

    print(f"# Tidepool ({len(tidepool['polips'])} polips, vitality: {tidepool['vitality']})")
    print()

    if not tidepool["polips"]:
        print("Empty tidepool. Drop something in:")
        print("  python tidepool.py drop \"your insight here\"")
        return

    # Sort by recency (newest first for active context)
    polips = sorted(tidepool["polips"], key=lambda p: p.get("ts", ""), reverse=True)

    for p in polips[:10]:  # Show top 10
        age = _age_str(p.get("ts", ""))
        print(f"- [{age}] {p['content'][:80]}")


def drop(content):
    """Add a polip to the tidepool."""
    tidepool = load_tidepool()

    polip = {
        "content": content,
        "ts": datetime.now().isoformat(),
        "vitality": 100,
    }

    tidepool["polips"].append(polip)

    # Decay old polips
    _decay(tidepool)

    save_tidepool(tidepool)
    print(f"🫧 Dropped: {content[:50]}...")


def vitals():
    """Show tidepool health."""
    tidepool = load_tidepool()

    total = len(tidepool["polips"])
    if total == 0:
        print("Empty tidepool.")
        return

    # Compute stats
    thriving = sum(1 for p in tidepool["polips"] if p.get("vitality", 0) >= 80)
    calcifying = sum(1 for p in tidepool["polips"] if 20 <= p.get("vitality", 0) < 80)
    decaying = sum(1 for p in tidepool["polips"] if p.get("vitality", 0) < 20)

    avg_vitality = sum(p.get("vitality", 50) for p in tidepool["polips"]) / total
    tidepool["vitality"] = int(avg_vitality)
    save_tidepool(tidepool)

    print(f"Tidepool Vitals")
    print(f"  Total polips: {total}")
    print(f"  Thriving:     {thriving}")
    print(f"  Calcifying:   {calcifying}")
    print(f"  Decaying:     {decaying}")
    print(f"  Avg vitality: {avg_vitality:.0f}")


def _decay(tidepool):
    """Apply decay to old polips."""
    now = datetime.now()

    for p in tidepool["polips"]:
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
    tidepool["polips"] = [p for p in tidepool["polips"] if p.get("vitality", 0) > 0]


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
            print("Usage: python tidepool.py drop \"your insight\"")
            return
        drop(" ".join(sys.argv[2:]))
    elif cmd == "vitals":
        vitals()
    else:
        print(f"Unknown: {cmd}")
        print("Commands: init, swim, drop, vitals")


if __name__ == "__main__":
    main()
