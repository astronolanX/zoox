# Security Audit Report - Goopy v0.1.0

**Date:** 2026-01-08
**Priority:** P0 (Emergency)
**Overall Confidence:** 0.92
**Auditor:** Claude Opus 4.5 (Team Agent)

---

## Executive Summary

Goopy's security posture is **adequate for single-user local development** but has **critical gaps for multi-agent or shared environments**. Five issues identified, three rated HIGH or CRITICAL.

---

## Findings

### 1. No File Locking for Concurrent Access

**Severity:** CRITICAL
**Confidence:** 0.95 (Verified in code)
**Location:** `src/goopy/blob.py:220-223`

**Issue:** The `Blob.save()` method uses `path.write_text()` without file locking. Multiple Claude sessions or agents writing to the same blob can cause:
- Lost updates (last write wins)
- Corrupted reads during write
- Data races in decompose operations

**Evidence:**
```python
def save(self, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(self.to_xml())  # NOT ATOMIC, NO LOCK
```

**Recommendation:** Implement advisory locking via `fcntl.flock()` or use atomic write pattern (write to temp, then rename).

---

### 2. Path Traversal in Subdir Parameter

**Severity:** HIGH
**Confidence:** 0.92 (Verified in test_absurd.py)
**Location:** `src/goopy/blob.py:255-260`

**Issue:** The `sprout()` method accepts arbitrary subdir strings without validation:
```python
target_dir = self.claude_dir / subdir  # subdir="../../../etc" allowed!
```

A malicious or buggy caller could write blobs outside `.claude/`.

**Evidence:** Test `test_sprout_to_parent_directory` confirms files created outside intended directory.

**Recommendation:** Validate that resolved path is under `.claude/` using `path.resolve().is_relative_to()`.

---

### 3. Archive Collision on Same-Day Decompose

**Severity:** HIGH
**Confidence:** 0.95 (Verified in test_bugs.py:110-134)
**Location:** `src/goopy/blob.py:367-369`

**Issue:** Archive naming uses only date prefix:
```python
date_str = datetime.now().strftime("%Y%m%d")
archive_path = archive_dir / f"{date_str}-{name}.blob.xml"
```

Multiple decompositions of same-named blob on same day overwrite previous archives.

**Recommendation:** Add microsecond or UUID suffix: `f"{date_str}-{name}-{uuid4().hex[:8]}.blob.xml"`

---

### 4. No Atomic Writes (Crash Corruption Risk)

**Severity:** MEDIUM
**Confidence:** 0.85 (Theoretical)
**Location:** `src/goopy/blob.py:223`

**Issue:** If system crashes during `write_text()`, blob file may be corrupted or incomplete.

**Recommendation:** Write to temp file, then atomic rename:
```python
import tempfile
with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
    f.write(self.to_xml().encode())
    os.rename(f.name, path)
```

---

### 5. XML Security (ElementTree Defaults)

**Severity:** MEDIUM
**Confidence:** 0.80 (Partial mitigation exists)
**Location:** `src/goopy/blob.py:148`

**Issue:** Uses `ET.fromstring()` without explicit DTD/entity restrictions. While Python 3.8+ ElementTree blocks most XXE attacks, explicit security is better.

**Evidence:** Tests in `test_absurd.py` show XXE and billion laughs are rejected, but defense relies on implementation details.

**Recommendation:** Consider `defusedxml` for security-critical deployments, or document the stdlib-only trade-off.

---

## Risk Matrix

| Finding | Severity | Likelihood | Impact | Priority |
|---------|----------|------------|--------|----------|
| No file locking | CRITICAL | High (multi-agent) | Data loss | P0 |
| Path traversal | HIGH | Low | Security breach | P0 |
| Archive collision | HIGH | Medium | Data loss | P0 |
| No atomic writes | MEDIUM | Medium | Corruption | P1 |
| XML security | MEDIUM | Low | Security | P1 |

---

## Recommendations Summary

1. **Immediate (P0):** Implement file locking, path validation, archive uniqueness
2. **Soon (P1):** Atomic write pattern, document XML security trade-offs
3. **Consider:** Optional `defusedxml` dependency for high-security use cases

---

## Validation

All findings verified through:
- Code review of `src/goopy/blob.py`
- Existing tests in `tests/test_bugs.py` and `tests/test_absurd.py`
- Manual reproduction where applicable

---

## Research Context

Similar tools have addressed these issues:
- [Claude-Mem](https://github.com/thedotmack/claude-mem) uses SQLite for atomic transactions
- [MCP Memory Service](https://github.com/doobidoo/mcp-memory-service) uses database backends
- Enterprise patterns recommend [distributed key-value stores](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) for shared agent state
