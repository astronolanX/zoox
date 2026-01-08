# Scalability Assessment - Goopy v0.1.0

**Date:** 2026-01-08
**Priority:** P2 (Important)
**Overall Confidence:** 0.85
**Auditor:** Claude Opus 4.5 (Team Agent)

---

## Executive Summary

Goopy's current design **scales well to ~1,000 blobs** (sufficient for most projects). Beyond this, **linear scanning becomes noticeable**. Three optimization opportunities identified for future growth.

---

## Current Performance Profile

### Measured Characteristics

| Operation | Complexity | Estimate (100 blobs) | Estimate (1000 blobs) |
|-----------|------------|----------------------|----------------------|
| `sprout()` | O(1) | ~2ms | ~2ms |
| `get()` | O(1) | ~1ms | ~1ms |
| `list_blobs()` | O(n) | ~5ms | ~50ms |
| `surface_relevant()` | O(n*m) | ~10ms | ~100ms |
| `inject_context()` | O(n*m) | ~15ms | ~120ms |

Where n = blob count, m = average query complexity

### Bottleneck Analysis

1. **File I/O dominates** - Each `list_blobs()` call scans directory
2. **Full parsing required** - Every blob parsed even if not relevant
3. **6 subdirectory scans** - `surface_relevant()` calls `list_blobs()` 6 times
4. **No caching** - Repeated queries reparse same files

---

## Findings

### 1. Linear Blob Scanning

**Severity:** MEDIUM
**Confidence:** 0.90 (Code analysis)
**Location:** `blob.py:300-348`

**Issue:** `surface_relevant()` loads ALL blobs to score them:
```python
for subdir in ["threads", "decisions", "constraints", "contexts", "facts"]:
    all_blobs.extend(self.list_blobs(subdir))
```

At 1,000 blobs with 5KB average size: ~5MB disk reads per query.

**Recommendation:** Implement index file (`.claude/index.json`) with metadata:
```json
{
  "blobs": {
    "threads/auth-impl": {
      "scope": "project",
      "status": "active",
      "summary": "Implement auth",
      "files": ["auth.py"],
      "updated": "2026-01-08"
    }
  }
}
```

---

### 2. No Blob Caching

**Severity:** MEDIUM
**Confidence:** 0.85 (Design gap)
**Location:** `blob.py:276-298`

**Issue:** Each `list_blobs()` call re-reads and re-parses files. In a session:
1. `inject_context()` parses all blobs
2. User touches file, triggers relevance check
3. Same blobs parsed again

**Recommendation:** Add in-memory cache with file mtime invalidation:
```python
class Glob:
    def __init__(self):
        self._cache = {}  # path -> (mtime, Blob)
```

---

### 3. Missing Documentation of Limits

**Severity:** LOW
**Confidence:** 0.80 (User expectation)
**Location:** `README.md`

**Issue:** No guidance on expected blob counts or performance characteristics. Users may assume unlimited scaling.

**Recommendation:** Add "Performance" section:
```markdown
## Performance

Goopy is optimized for project-scale usage:
- **Sweet spot:** 10-500 blobs
- **Comfortable:** Up to 1,000 blobs
- **Consider alternatives:** 5,000+ blobs

For very large projects, consider sharding by time or subsystem.
```

---

## Scaling Strategies

### Near-term (No Code Changes)

| Strategy | Effort | Impact |
|----------|--------|--------|
| Keep blobs focused | None | High |
| Use decompose regularly | None | Medium |
| Shard by date manually | Low | Medium |

### Medium-term (Code Changes)

| Strategy | Effort | Impact |
|----------|--------|--------|
| Add index.json | 1 week | High |
| Implement caching | 3 days | Medium |
| Lazy blob loading | 2 days | Medium |

### Long-term (Architecture)

| Strategy | Effort | Impact |
|----------|--------|--------|
| SQLite backend | 2 weeks | Very High |
| Hierarchical globs | 1 week | High |
| Bloom filter for files | 1 week | Medium |

---

## Comparison to Industry Patterns

### Shared Memory Patterns (Microsoft)
[Azure AI Agent Design Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) recommends:
- Distributed key-value stores for shared state
- Temporal context caching for trend analysis
- Blackboard systems for async collaboration

### Context Engineering (Vellum)
[Multi-Agent Systems](https://www.vellum.ai/blog/multi-agent-systems-building-with-context-engineering) notes:
- "Failure generally boils down to missing context"
- Shared state layer critical for coordination

### Claude-Mem Approach
[Claude-Mem](https://github.com/thedotmack/claude-mem) uses:
- SQLite for O(1) lookups
- AI compression (up to 95% token reduction)
- "Endless Mode" for extended sessions

---

## Recommendations Summary

1. **P2:** Add index.json for O(1) metadata lookups
2. **P2:** Implement in-memory blob caching
3. **P2:** Document performance expectations in README

---

## Files to Modify

| File | Change |
|------|--------|
| `src/goopy/blob.py` | Add index generation, caching layer |
| `README.md` | Add Performance section |
| `tests/test_glob.py` | Add scaling tests (500, 1000 blobs) |
