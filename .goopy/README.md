# Goopy Audit Artifacts

This directory contains audit deliverables and task tracking for goopy development.

## Structure

```
.goopy/
├── reports/           # Audit findings in triplicate (.md, .txt, .xml)
├── backlog/           # Prioritized work items as goopy blobs
│   ├── P0-emergency/  # Security vulnerabilities, data loss risks
│   ├── P1-critical/   # Bugs affecting core functionality
│   ├── P2-important/  # Performance, UX improvements
│   └── P3-nice-to-have/ # Enhancements, polish
└── README.md
```

## Report Naming Convention

`{YYYYMMDD}-{priority}-{subject}.{ext}`

Example: `20260108-P0-security-audit.md`

## Sister File Formats

| Format | Purpose |
|--------|---------|
| `.md` | Human-readable narrative with full analysis |
| `.txt` | Plain text summary for quick grep/scanning |
| `.xml` | Machine-parseable using goopy's blob schema |

## Confidence Rating Scale

| Rating | Meaning |
|--------|---------|
| 0.95-1.0 | **Verified** - Tested and reproduced |
| 0.80-0.94 | **High confidence** - Strong evidence |
| 0.60-0.79 | **Medium confidence** - Circumstantial |
| 0.40-0.59 | **Low confidence** - Needs verification |
| <0.40 | **Hypothesis** - Speculative |

## Priority Levels

| Priority | Description | Response Time |
|----------|-------------|---------------|
| P0 | Emergency - Security, data loss | Immediate |
| P1 | Critical - Core functionality broken | This sprint |
| P2 | Important - Performance, UX | Next sprint |
| P3 | Nice-to-have - Enhancements | Backlog |

## Meta-Integration

Backlog items ARE native goopy blobs. This means:
- `goopy list` surfaces active audit tasks
- `goopy migrate` keeps audit artifacts current
- The audit system dogfoods its own subject

## Research Sources

This audit incorporated findings from:
- [Claude-Mem](https://github.com/thedotmack/claude-mem) - Similar context injection plugin
- [MCP Memory Service](https://github.com/doobidoo/mcp-memory-service) - Cross-tool memory
- [Claude Code Memory Docs](https://code.claude.com/docs/en/memory) - Official patterns
- [Multi-Agent AI Design Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
