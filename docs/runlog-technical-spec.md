# Runlog Technical Specification

**Date:** 2026-01-15
**Version:** 1.0
**Status:** Implementable

---

## 1. Schema Changes

### 1.1 Blob Type Enum Extension

File: `src/reef/blob.py`

```python
class BlobType(Enum):
    """Types of blobs in a glob."""
    CONTEXT = "context"      # Session state
    THREAD = "thread"        # Active work stream
    DECISION = "decision"    # Architectural choice
    CONSTRAINT = "constraint"  # Always-on rules
    FACT = "fact"            # Key information
    RUNLOG = "runlog"        # Agent run observation (NEW)
    ANALYSIS = "analysis"    # Sweep analysis result (NEW)
```

### 1.2 Run Note Polip Fields

Extend `Blob` dataclass with run-note-specific fields:

```python
@dataclass
class Blob:
    # ... existing fields ...

    # Run note metadata (optional, only populated for RUNLOG type)
    metadata: Optional[dict] = field(default_factory=dict)
    # {
    #   "session_id": str,
    #   "run_number": int,
    #   "task_type": str,
    #   "start_time": datetime,
    #   "end_time": datetime,
    #   "status": str,  # completed|failed|timeout|incomplete
    # }

    observations: Optional[dict] = field(default_factory=dict)
    # {
    #   "works": list[str],
    #   "missing": list[str],
    #   "noise": list[str],
    #   "blockers": list[str],
    # }

    signals: Optional[list] = field(default_factory=list)
    # [
    #   {"type": "create", "blob_type": "fact", "title": str, "hint": str},
    #   {"type": "enhance", "polip_key": str, "note": str},
    #   {"type": "archive", "polip_key": str, "reason": str},
    #   {"type": "tune", "parameter": str, "value": str},
    # ]
```

### 1.3 XML Serialization (to_xml / from_xml)

Update `Blob.to_xml()` to serialize RUNLOG/ANALYSIS fields:

```xml
<!-- For type="runlog" -->
<blob type="runlog" scope="session" updated="2026-01-15" v="2">
  <summary>...</summary>

  <metadata>
    <session_id>abc123</session_id>
    <run_number>42</run_number>
    <task_type>bugfix</task_type>
    <start_time>2026-01-15T14:30:00Z</start_time>
    <end_time>2026-01-15T14:32:00Z</end_time>
    <duration_seconds>120</duration_seconds>
    <status>completed</status>
  </metadata>

  <observations>
    <works weight="high">Item text</works>
    <missing weight="high">Item text</missing>
    <noise weight="medium">Item text</noise>
    <blockers type="context">Item text</blockers>
  </observations>

  <signals>
    <signal type="create">
      <blob_type>fact</blob_type>
      <title>JWT Retry Pattern</title>
      <hint>Exponential backoff: base=100ms, cap=30s</hint>
    </signal>
    <signal type="enhance">
      <polip_key>constraints/auth-flow</polip_key>
      <note>Add example for 401 refresh retry</note>
    </signal>
  </signals>

  <files/>
  <next/>
  <related/>
  <context>Free-form notes from agent</context>
</blob>
```

Parse in `from_xml()` — handle missing elements gracefully (non-RUNLOG blobs skip these).

---

## 2. Directory Structure

### 2.1 Runs Subdirectory

Create `.claude/runs/` if not exists:

```
.claude/runs/
├── 2026-01-15-run-001-abc123.runlog.xml
├── 2026-01-15-run-002-def456.runlog.xml
├── 2026-01-15-sweep-analysis.analysis.xml
└── runs.json  (NEW: configuration + metadata)
```

### 2.2 Runs Configuration File

File: `.claude/runs.json`

```json
{
  "version": 1,
  "sweep_triggers": {
    "count": 10,
    "accuracy_threshold": 0.80,
    "error_repetition": 3,
    "enabled": true
  },
  "retention": {
    "days": 14,
    "auto_archive": true
  },
  "metrics": {
    "tracking_enabled": true,
    "baseline_accuracy": 0.82
  },
  "last_sweep": "2026-01-15T16:00:00Z",
  "next_auto_sweep": "2026-01-22T00:00:00Z"
}
```

---

## 3. CLI Extension

### 3.1 New Subcommand: `reef analyze`

File: `src/reef/cli.py` (add new command)

```python
def cmd_analyze(args):
    """Analyze run notes and generate improvement proposals."""
    from reef.blob import Glob

    project_dir = Path.cwd()
    glob = Glob(project_dir)

    # Load runs config
    runs_config = glob.load_runs_config()

    if args.action == "runs":
        # Filter run notes
        since = args.since or "1d"  # Default: last day
        dry_run = args.dry_run
        auto_fix = args.auto_fix

        # Call sweep logic
        result = glob.analyze_runs(since=since, dry_run=dry_run, auto_fix=auto_fix)

        # Print results
        print_sweep_results(result)

    elif args.action == "metrics":
        # Print metrics trend
        metrics = glob.get_run_metrics()
        print_metrics_report(metrics)
```

### 3.2 Argument Parser Extension

```python
# In main() add:
analyze_parser = subparsers.add_parser(
    "analyze",
    help="Analyze run notes and generate proposals",
    description="Scan run notes, extract signals, generate improvement proposals"
)
analyze_parser.add_argument(
    "action",
    choices=["runs", "metrics"],
    help="runs: analyze run notes | metrics: show trends"
)
analyze_parser.add_argument("--since", help="Time filter: 1d, 2d, session (default: 1d)")
analyze_parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
analyze_parser.add_argument("--auto-fix", action="store_true", help="Auto-apply safe fixes")
analyze_parser.add_argument("--verbose", "-v", action="store_true", help="Detailed output")
analyze_parser.set_defaults(func=cmd_analyze)
```

---

## 4. Core Glob Methods

### 4.1 Run Note Creation

File: `src/reef/blob.py` (add to Glob class)

```python
def create_run_note(
    self,
    session_id: str,
    run_number: int,
    task_type: str,
    task_summary: str,
    observations: dict,
    signals: list,
    surfaced_polips: list = None,
) -> Path:
    """
    Create a run note (RUNLOG blob).

    Args:
        session_id: Unique session identifier
        run_number: Sequential run counter
        task_type: Category (bugfix, feature, test, etc.)
        task_summary: Human-readable task description
        observations: {works: [...], missing: [...], noise: [...], blockers: [...]}
        signals: [{type: str, ...}, ...]
        surfaced_polips: List of (key, rank, relevant) tuples

    Returns:
        Path to created run note
    """
    from datetime import datetime

    # Build blob
    run_note = Blob(
        type=BlobType.RUNLOG,
        scope=BlobScope.SESSION,
        status=BlobStatus.ACTIVE,
        summary=f"Task: {task_summary} (session-{session_id})",
        context=observations.get("context", ""),
        metadata={
            "session_id": session_id,
            "run_number": run_number,
            "task_type": task_type,
            "start_time": observations.get("start_time", datetime.now()),
            "end_time": observations.get("end_time", datetime.now()),
            "status": observations.get("status", "completed"),
        },
        observations=observations,
        signals=signals,
    )

    # Determine filename
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"run-{timestamp}-{session_id[:8]}"

    # Write to runs/ subdirectory
    return self.sprout(run_note, name, subdir="runs")
```

### 4.2 Load Runs Configuration

```python
def load_runs_config(self) -> dict:
    """Load or create runs.json with defaults."""
    config_path = self.claude_dir / "runs.json"
    defaults = {
        "version": 1,
        "sweep_triggers": {
            "count": 10,
            "accuracy_threshold": 0.80,
            "error_repetition": 3,
            "enabled": True,
        },
        "retention": {
            "days": 14,
            "auto_archive": True,
        },
        "metrics": {
            "tracking_enabled": True,
            "baseline_accuracy": 0.82,
        },
        "last_sweep": None,
        "next_auto_sweep": None,
    }

    if config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except json.JSONDecodeError:
            return defaults

    # Create with defaults
    _atomic_write(config_path, json.dumps(defaults, indent=2))
    return defaults
```

### 4.3 Analyze Runs (Core Sweep Logic)

```python
def analyze_runs(
    self,
    since: str = "1d",
    dry_run: bool = False,
    auto_fix: bool = False,
) -> dict:
    """
    Scan run notes, extract signals, generate proposals.

    Args:
        since: Time filter (e.g., "1d", "2d", "session")
        dry_run: Don't apply changes
        auto_fix: Auto-apply safe fixes

    Returns:
        {
            "run_notes_analyzed": int,
            "signals_extracted": list,
            "proposals": list,
            "applied_changes": list,
            "metrics": dict,
        }
    """
    from datetime import datetime, timedelta

    # Parse time filter
    if since == "session":
        cutoff = datetime.now().replace(hour=0, minute=0, second=0)
    elif since.endswith("d"):
        days = int(since[:-1])
        cutoff = datetime.now() - timedelta(days=days)
    else:
        cutoff = datetime.now() - timedelta(days=1)  # default

    # Load run notes
    run_notes = []
    for name, blob in self.list_blobs(subdir="runs"):
        if blob.type != BlobType.RUNLOG:
            continue
        if blob.updated < cutoff:
            continue
        run_notes.append((name, blob))

    if not run_notes:
        return {
            "run_notes_analyzed": 0,
            "signals_extracted": [],
            "proposals": [],
            "applied_changes": [],
            "metrics": {},
        }

    # Extract signals from each run note
    all_signals = []
    for name, blob in run_notes:
        all_signals.extend(blob.signals or [])

    # Aggregate signals
    aggregated = self._aggregate_signals(all_signals)

    # Generate proposals
    proposals = self._generate_proposals(aggregated, run_notes)

    # Apply safe fixes if requested
    applied = []
    if auto_fix and not dry_run:
        applied = self._apply_safe_fixes(proposals)

    # Compute metrics
    metrics = self._compute_sweep_metrics(run_notes)

    # Generate analysis polip
    if not dry_run:
        self._create_analysis_polip(proposals, metrics, len(run_notes))

    return {
        "run_notes_analyzed": len(run_notes),
        "signals_extracted": all_signals,
        "proposals": proposals,
        "applied_changes": applied,
        "metrics": metrics,
    }
```

### 4.4 Signal Aggregation

```python
def _aggregate_signals(self, signals: list) -> dict:
    """
    Group similar signals, count occurrences, compute confidence.

    Returns:
        {
            "create": [
                {
                    "type": "fact",
                    "title": "JWT Retry Pattern",
                    "hint": "...",
                    "count": 6,
                    "confidence": 0.95,
                }
            ],
            "enhance": [...],
            "archive": [...],
            "tune": [...],
        }
    """
    from collections import defaultdict

    aggregated = defaultdict(lambda: defaultdict(list))

    for signal in signals:
        signal_type = signal.get("type")  # create, enhance, archive, tune

        if signal_type == "create":
            key = (signal.get("blob_type"), signal.get("title"))
            aggregated["create"][key].append(signal)

        elif signal_type == "enhance":
            key = signal.get("polip_key")
            aggregated["enhance"][key].append(signal)

        elif signal_type == "archive":
            key = signal.get("polip_key")
            aggregated["archive"][key].append(signal)

        elif signal_type == "tune":
            key = signal.get("parameter")
            aggregated["tune"][key].append(signal)

    # Convert to list with counts and confidence
    result = {}
    for signal_type, grouped in aggregated.items():
        result[signal_type] = [
            {
                "key": key,
                "items": items,
                "count": len(items),
                "confidence": min(1.0, len(items) / 10),  # Rough heuristic
            }
            for key, items in grouped.items()
        ]

    return result
```

### 4.5 Proposal Generation

```python
def _generate_proposals(self, aggregated: dict, run_notes: list) -> list:
    """
    Convert aggregated signals into actionable proposals.
    """
    proposals = []

    # Proposals from "create" signals
    for item in aggregated.get("create", []):
        if item["count"] >= 3:  # Threshold
            proposals.append({
                "type": "create_polip",
                "confidence": item["confidence"],
                "blob_type": item["items"][0].get("blob_type"),
                "title": item["items"][0].get("title"),
                "hint": item["items"][0].get("hint"),
                "count_evidence": item["count"],
                "auto_apply": item["confidence"] > 0.90,
            })

    # Proposals from "enhance" signals
    for item in aggregated.get("enhance", []):
        proposals.append({
            "type": "enhance_polip",
            "confidence": item["confidence"],
            "polip_key": item["key"],
            "suggestions": [i.get("note") for i in item["items"]],
            "count_evidence": item["count"],
            "auto_apply": False,  # Always manual
        })

    # Proposals from "archive" signals
    for item in aggregated.get("archive", []):
        if item["count"] >= 3:
            proposals.append({
                "type": "decompose_polip",
                "confidence": item["confidence"],
                "polip_key": item["key"],
                "reason": item["items"][0].get("reason"),
                "count_evidence": item["count"],
                "auto_apply": item["confidence"] > 0.90,
            })

    # Proposals from "tune" signals
    for item in aggregated.get("tune", []):
        proposals.append({
            "type": "tune_parameter",
            "confidence": min(item["confidence"], 0.65),  # Cap at 65% (monitoring)
            "parameter": item["key"],
            "suggestions": [i.get("value") for i in item["items"]],
            "count_evidence": item["count"],
            "auto_apply": False,  # Never auto
        })

    # Sort by confidence × importance
    proposals.sort(key=lambda p: p["confidence"] * (1 if p["auto_apply"] else 0.5), reverse=True)

    return proposals
```

### 4.6 Apply Safe Fixes

```python
def _apply_safe_fixes(self, proposals: list) -> list:
    """Auto-apply high-confidence safe proposals."""
    applied = []

    for proposal in proposals:
        if not proposal.get("auto_apply"):
            continue

        try:
            if proposal["type"] == "create_polip":
                # Create new fact fossil
                path = self.create_from_template(
                    "fact",
                    title=proposal["title"],
                )
                if path:
                    applied.append({
                        "type": "created",
                        "polip": str(path),
                        "proposal": proposal,
                    })

            elif proposal["type"] == "decompose_polip":
                # Archive the polip
                key = proposal["polip_key"]
                if "/" in key:
                    subdir, name = key.split("/", 1)
                else:
                    subdir, name = None, key

                self.decompose(name, subdir)
                applied.append({
                    "type": "archived",
                    "polip": key,
                    "proposal": proposal,
                })

        except Exception as e:
            # Log but don't fail on individual proposal
            print(f"Warning: Failed to apply proposal {proposal}: {e}", file=sys.stderr)

    return applied
```

### 4.7 Compute Sweep Metrics

```python
def _compute_sweep_metrics(self, run_notes: list) -> dict:
    """Extract metrics from run notes for reporting."""
    if not run_notes:
        return {}

    metrics = {
        "total_runs": len(run_notes),
        "avg_duration_seconds": 0,
        "success_rate": 0,
        "avg_surfaced_tokens": 0,
        "avg_relevant_pct": 0,
        "avg_noise_pct": 0,
        "missed_polips_pct": 0,
    }

    durations = []
    success_count = 0
    relevant_counts = []
    noise_counts = []
    missed_counts = []

    for name, blob in run_notes:
        meta = blob.metadata or {}
        obs = blob.observations or {}

        # Duration
        if meta.get("duration_seconds"):
            durations.append(meta["duration_seconds"])

        # Success
        if meta.get("status") == "completed":
            success_count += 1

        # Observations (work/missing/noise)
        works = len(obs.get("works", []))
        missing = len(obs.get("missing", []))
        noise = len(obs.get("noise", []))
        total = works + missing + noise

        if total > 0:
            relevant_counts.append(works / total)
            noise_counts.append(noise / total)
            missed_counts.append(missing / total)

    metrics["avg_duration_seconds"] = sum(durations) / len(durations) if durations else 0
    metrics["success_rate"] = success_count / len(run_notes)
    metrics["avg_relevant_pct"] = sum(relevant_counts) / len(relevant_counts) if relevant_counts else 0
    metrics["avg_noise_pct"] = sum(noise_counts) / len(noise_counts) if noise_counts else 0
    metrics["missed_polips_pct"] = sum(missed_counts) / len(missed_counts) if missed_counts else 0

    return metrics
```

### 4.8 Create Analysis Polip

```python
def _create_analysis_polip(self, proposals: list, metrics: dict, run_count: int):
    """Create summary analysis polip."""
    analysis = Blob(
        type=BlobType.ANALYSIS,
        scope=BlobScope.SESSION,
        summary=f"Sweep analysis: {run_count} run notes",
        metadata={
            "run_notes_analyzed": run_count,
            "proposals_generated": len(proposals),
            "metrics": metrics,
        },
        observations={
            "proposals": proposals,
        },
        context=self._format_analysis_context(proposals, metrics),
    )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    self.sprout(analysis, f"sweep-{timestamp}", subdir="runs")
```

---

## 5. Hook Integration

### 5.1 Stop Hook Invocation

File: Claude Code hook configuration template

```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "reef hook persist"
      },
      {
        "type": "command",
        "command": "reef run-note create --auto"
      }
    ]
  }
}
```

### 5.2 Hook Command Handler

File: `cli.py` (extend `cmd_hook`)

```python
elif args.action == "create-run-note":
    # Create run note from session context
    glob = Glob(project_dir)

    session_id = args.session_id or generate_session_id()
    observations = {
        "works": args.works.split("|") if args.works else [],
        "missing": args.missing.split("|") if args.missing else [],
        "noise": args.noise.split("|") if args.noise else [],
        "blockers": args.blockers.split("|") if args.blockers else [],
        "context": args.context or "",
        "start_time": args.start_time or datetime.now(),
        "end_time": args.end_time or datetime.now(),
        "status": args.status or "completed",
    }

    signals = parse_signals(args.signals) if args.signals else []

    path = glob.create_run_note(
        session_id=session_id,
        run_number=args.run_number or 0,
        task_type=args.task_type or "general",
        task_summary=args.task_summary or "Unnamed task",
        observations=observations,
        signals=signals,
    )

    if not args.quiet:
        print(f"Run note created: {path.relative_to(project_dir)}")
```

---

## 6. Testing Checklist

### Unit Tests
- [ ] `test_create_run_note()` — RUNLOG polip creation
- [ ] `test_aggregate_signals()` — Signal grouping and confidence
- [ ] `test_generate_proposals()` — Proposal generation
- [ ] `test_apply_safe_fixes()` — Safe auto-application
- [ ] `test_compute_metrics()` — Metric extraction

### Integration Tests
- [ ] End-to-end: Create run note → Analyze → Apply fixes
- [ ] Dry-run mode: Verify no changes written
- [ ] Time filters: --since 1d, 2d, session
- [ ] Snapshot/rollback: Create analysis, verify snapshot, restore

### CLI Tests
- [ ] `reef analyze runs` → Lists proposals
- [ ] `reef analyze runs --dry-run` → No changes
- [ ] `reef analyze runs --auto-fix` → Changes applied
- [ ] `reef analyze metrics` → Metrics printed

---

## 7. Version Compatibility

- BLOB_VERSION: Increment from 2 → 3 (add metadata, observations, signals fields)
- INDEX_VERSION: No change (runlog is indexed normally)
- CLI version: reef 0.1.1 (minor version bump for new command)

Handle old blobs gracefully:
```python
def migrate(self) -> "Blob":
    """Migrate blob to current schema."""
    if self.version < 3:
        # v2 -> v3: Initialize RUNLOG-specific fields if missing
        if self.type == BlobType.RUNLOG:
            if not self.metadata:
                self.metadata = {}
            if not self.observations:
                self.observations = {"works": [], "missing": [], "noise": [], "blockers": []}
            if not self.signals:
                self.signals = []
    self.version = BLOB_VERSION
    return self
```

---

## 8. Error Handling

```python
class RunNoteError(ValueError):
    """Base exception for run note operations."""
    pass

class InvalidSignal(RunNoteError):
    """Signal format invalid."""
    pass

class ProposalFailed(RunNoteError):
    """Proposal application failed."""
    pass
```

Strategies:
- If a proposal fails, log and continue (don't block entire sweep)
- If sweep scan fails, fall back to manual UI guidance
- Validate XML parse errors gracefully (skip malformed notes)

---

## 9. Performance Considerations

- **Sweep scan:** O(n) polips in .claude/runs/; acceptable for <1000 notes
- **Signal aggregation:** O(m) signals; typically <500 per sweep
- **Proposal generation:** O(m) signals × matching logic; <100ms expected
- **File I/O:** Atomic writes on proposal application (safe)
- **Index updates:** Incremental (run notes added to existing index)

For large repos (>10K polips), consider:
- Batch sweep mode (process 100 notes at a time)
- Async proposal application
- Pre-compute signal groups on-demand

---

## 10. Security & Validation

- **Signal validation:** Only accept from local .claude/runs/ (trusted)
- **Proposal safety:** Hard-code safe types (don't auto-apply risky changes)
- **Snapshot before fixes:** Always create pre-sweep snapshot
- **Dry-run audit:** Print all changes before --auto-fix
- **No external data:** Signals must originate from local run notes only

---

*Specification implemented in phases. Phase 1 covers core creation/analysis.*
