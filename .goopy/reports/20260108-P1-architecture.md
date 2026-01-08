# Architecture Critique - Goopy v0.1.0

**Date:** 2026-01-08
**Priority:** P1 (Critical)
**Overall Confidence:** 0.88
**Auditor:** Claude Opus 4.5 (Karen Agent - Critical Validator)

---

## Executive Summary

Goopy's architecture is **intentionally minimal and well-suited for its target use case** (single-user session memory). However, three architectural patterns create maintainability issues and one design decision limits future growth.

---

## Findings

### 1. Hardcoded Subdirectory Lists

**Severity:** HIGH
**Confidence:** 0.95 (Bug already occurred)
**Locations:**
- `blob.py:316-317` (surface_relevant)
- `blob.py:407-408` (check_migrations)
- `blob.py:415` (path reconstruction)
- `cli.py:103` (cmd_decompose)

**Issue:** The subdirectory list `["threads", "decisions", "constraints", "contexts", "facts"]` is duplicated in 4+ locations. When `contexts` and `facts` were initially missing, it caused bugs where:
- Facts with ALWAYS scope didn't surface
- Old blobs in facts/contexts weren't migrated

**Evidence:** Bugs documented in `test_bugs.py`, fixed in recent audit.

**Recommendation:** Create `KNOWN_SUBDIRS` constant or derive dynamically from `BlobType` enum:
```python
KNOWN_SUBDIRS = {
    BlobType.THREAD: "threads",
    BlobType.DECISION: "decisions",
    # ...
}
```

---

### 2. CLI/Glob Decompose Behavior Mismatch

**Severity:** MEDIUM
**Confidence:** 0.85 (Documented in test_bugs.py:93-108)
**Locations:**
- `blob.py:346-369` (Glob.decompose)
- `cli.py:130-137` (cmd_decompose)

**Issue:**
- `Glob.decompose()` moves blobs to archive directory with ARCHIVED status
- `cmd_decompose()` calls `path.unlink()` directly, permanently deleting

**Impact:** Users expect CLI to archive (documented behavior), but it actually deletes.

**Recommendation:** Unify behavior - CLI should call `Glob.decompose()` instead of direct unlink.

---

### 3. XML Token Overhead vs JSON

**Severity:** LOW
**Confidence:** 0.75 (Measured estimate)
**Location:** Design decision

**Issue:** XML format is ~50% larger than equivalent JSON:
- Closing tags add overhead
- Attribute syntax more verbose
- Indentation/whitespace for readability

**Quantified Impact:**
- Minimal blob: ~180 bytes XML vs ~100 bytes JSON
- For 10-blob injection: ~1.8KB vs ~1KB overhead
- At 4 chars/token: ~200 extra tokens per injection

**Counter-argument:** Claude handles XML very well (HTML/XML in training data). Self-describing format aids interpretation. Trade-off is acceptable.

**Recommendation:** Document as intentional design decision. Consider optional JSON export for size-sensitive use cases.

---

## Architecture Strengths

| Aspect | Assessment |
|--------|-----------|
| Simplicity | Excellent - 850 LOC for full functionality |
| Zero dependencies | Strong constraint, well-maintained |
| Schema versioning | Good - migration path defined |
| Graceful degradation | Good - malformed files skipped |
| Separation of concerns | Good - Blob/Glob/CLI cleanly divided |

---

## Comparison to Alternatives

### vs Claude-Mem (SQLite)
- **Goopy:** Human-readable XML, zero deps, file-per-blob
- **Claude-Mem:** SQLite for atomicity, AI compression, higher complexity

### vs MCP Memory Service
- **Goopy:** Single-project focus, lightweight
- **MCP:** Cross-tool, semantic search, embedding-based

### vs CLAUDE.md Pattern
- **Goopy:** Structured types, relevance scoring, multi-blob
- **CLAUDE.md:** Flat text, manual curation, single file

**Verdict:** Goopy occupies a unique niche between flat CLAUDE.md and full database solutions.

---

## Recommendations Summary

1. **P1:** Centralize KNOWN_SUBDIRS constant (prevents future bugs)
2. **P1:** Unify decompose behavior (user expectation alignment)
3. **P3:** Document XML vs JSON trade-off in README

---

## Files to Modify

| File | Change |
|------|--------|
| `src/goopy/blob.py` | Add KNOWN_SUBDIRS constant, use in 3 locations |
| `src/goopy/cli.py` | Change cmd_decompose to use Glob.decompose() |
| `README.md` | Add "Why XML?" section |

---

## Research Context

Architecture patterns from industry:
- [Multi-Agent Design Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) - Microsoft's shared memory patterns
- [Context Engineering](https://www.vellum.ai/blog/multi-agent-systems-building-with-context-engineering) - Vellum's approach
- [CLAUDE.md Best Practices](https://code.claude.com/docs/en/memory) - Official guidance
