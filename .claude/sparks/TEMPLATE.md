# Spark Template v4.0

Canonical format for spark output files. Delete this header when using.

```markdown
---
date: YYYY-MM-DDTHH:MM
thread: [thread-slug]
mode: explore|rapid|deep
complexity: N
agents: N
emergent:
  score: NN
  insight: "[emergent insight text]"
top_signal:
  model: [groq1|groq2|olla1|olla2|gemin]
  score: NN
  lens: "[lens] × [skill]"
stored: N
duration: NNs
---

# Spark: [Full topic/question]

## Memory

[Related past sparks from SQLite, or omit section if none found]

## Tiers

### → Near: [lens] × [skill]
| Model | Score | Insight |
|-------|-------|---------|
| groq1 | NN% | [insight] |
| groq2 | NN% | [insight] |
| olla1 | NN% | [insight] |
| olla2 | NN% | [insight] |
| gemin | NN% | [insight] |

**Synthesis (NN%):** [tier synthesis]

### →→ Mid: [lens] × [skill]
| Model | Score | Insight |
|-------|-------|---------|
| groq1 | NN% | [insight] |
| groq2 | NN% | [insight] |
| olla1 | NN% | [insight] |
| olla2 | NN% | [insight] |
| gemin | NN% | [insight] |

**Synthesis (NN%):** [tier synthesis]

### →→→ Far: [lens] × [skill]
| Model | Score | Insight |
|-------|-------|---------|
| groq1 | NN% | [insight] |
| groq2 | NN% | [insight] |
| olla1 | NN% | [insight] |
| olla2 | NN% | [insight] |
| gemin | NN% | [insight] |

**Synthesis (NN%):** [tier synthesis]

## Final Synthesis

| Type | Score | Insight |
|------|-------|---------|
| ∩ convergent | NN% | [common thread] |
| ⊗ divergent | NN% | [tension/paradox] |
| ◈ emergent | NN% | [surprising possibility] |

## Insights

[Analysis focusing on:
- The emergent insight and why it matters
- High-signal individual insights worth footnoting
- Heretical takes or inversions
- Concrete next steps if actionable]

## References

[^1]: [model] NN% · [lens] × [skill]

---
*spark v4.0*
```

## Frontmatter Reference

| Field | Type | Description |
|-------|------|-------------|
| `date` | ISO 8601 | Timestamp (YYYY-MM-DDTHH:MM) |
| `thread` | string | Thread slug for grouping |
| `mode` | enum | explore, rapid, or deep |
| `complexity` | 0-3 | Topic complexity (computed by runner) |
| `agents` | int | Models spawned (5 per tier) |
| `emergent.score` | 0-100 | Emergent synthesis confidence |
| `emergent.insight` | string | The emergent synthesis text |
| `top_signal.model` | string | Highest-scoring model |
| `top_signal.score` | 0-100 | Highest individual score |
| `top_signal.lens` | string | Lens × skill combination |
| `stored` | int | Sparks stored to SQLite (score ≥70) |
| `duration` | string | Execution time (e.g., "23s") |

## Model Names

| Abbrev | Provider | Model |
|--------|----------|-------|
| groq1 | Groq | llama-3.3-70b-versatile |
| groq2 | Groq | llama-3.1-8b-instant |
| olla1 | Ollama | llama3.2 |
| olla2 | Ollama | qwen2.5-coder |
| gemin | Gemini | gemini-2.0-flash |

## Tier Structure

- **→ Near**: Concrete lenses (objects, operations)
- **→→ Mid**: Natural patterns (patterns, systems) — explore mode with complexity ≥2, or deep mode
- **→→→ Far**: Abstract frameworks (philosophies, disciplines) — deep mode only
