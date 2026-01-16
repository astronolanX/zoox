# Tenacious Agent Mode

## Core Insight
"Never let them stop unless we see them actually fail."

Agents should exhaust possibility space, not complete "good enough" tasks.

## Proposed Flags

### Trench
```bash
reef trench spawn feature-x --tenacious
reef trench spawn research --exhaustive
```

### Spark
```bash
/spark --exhaustive  # Keep generating until walls hit
/spark --tenacious   # Don't settle on first good idea
```

## Exit Conditions (Tenacious Mode)

1. **Hard failure** - Error, exception, crash
2. **Timeout** - Configurable max duration
3. **Human interrupt** - Explicit stop signal
4. **Resource exhaustion** - Token/API limits

NOT valid exit conditions:
- "I think I've explored enough"
- "Here are 3 options"
- "This seems complete"

## Implementation Ideas

### Turn Budget vs Task Completion
Current: Agent completes when it thinks task is done
Tenacious: Agent runs until turn budget exhausted or failure

### Iteration Protocol
```
while not failed and turns_remaining > 0:
    explore_new_angle()
    challenge_previous_conclusions()
    seek_contradictions()
    if no_new_ground_found:
        break  # Only stop when truly stuck
```

### Progress Indicators
- Ideas generated (monotonic increase)
- Dead ends hit (learning)
- Contradictions found (depth)
- Novel connections made

## Use Cases

1. **Format design** - Don't stop at first good syntax
2. **Bug hunting** - Keep probing until confident
3. **Research spikes** - Exhaust the literature
4. **Creative work** - Push past obvious solutions

## Questions

- Default on or off?
- Per-agent-type configuration?
- How to detect "truly stuck" vs "lazy quit"?
