# Where "Agent Run Notes" Pattern Breaks Down: Edge Cases

**Author**: KAREN
**Date**: 2026-01-15
**Purpose**: Document the specific scenarios where this pattern collapses

---

## Edge Case 1: The 64-Agent Swarm Collapse

### The Scenario
claude-flow spawns 64 agents in parallel. Each writes a run note:
```
run-022-architect-1.xml
run-022-architect-2.xml
run-022-researcher-1.xml
run-022-researcher-2.xml
...
run-022-researcher-64.xml
```

### The Problem
```
64 agents × (5 "what worked" bullets + 5 "what didn't" bullets)
= 640 bullets per run
= Signal-to-noise ratio approaches zero
```

**Real example from distributed systems:**
"Log aggregation at scale" is why tools like ELK Stack exist. One server's logs are readable. 64 servers' logs require structured ingestion, automatic deduplication, anomaly detection.

### Why It Fails
1. **Conflicting observations**: Agent-1 says "policy A worked great," Agent-32 says "policy A caused timeout"
   - Which is true? Both. Different conditions.
   - Extracting signal requires context (what was Agent-32's input?)
   - That context isn't in the run note.

2. **Redundancy explosion**: Agents 1-16 all report "parallel routing efficient" (obvious, not insightful)

3. **Late failure detection**: Agent-45 fails silently. Run note says "success." Real failure buried in 640 bullets.

### The Cost to Fix
- Distributed tracing infrastructure: ~2000 LOC
- Automatic deduplication: ~500 LOC
- Anomaly detection: ~1000 LOC
- **Total**: ~3500 LOC to make swarm run notes useful

**Cheaper alternative**: Structured telemetry (OpenTelemetry-style), not run notes.

---

## Edge Case 2: The Long-Running Mediation Session

### The Scenario
Mediator runs for 8 hours with custody dispute:
- 2 hrs: Listening mode
- 1 hr: Analysis mode
- 2 hrs: Preparation mode
- 2 hrs: Response mode
- 1 hr: Cooling-off state

At the end, agent writes one run note:
```xml
<run id="mediation-case-2022DCM6011">
  <summary>8-hour custody mediation, parties reached agreement</summary>
  <what-worked>Mediator stayed neutral throughout...</what-worked>
  <what-didnt>Research on jurisdiction took longer than expected...</what-didnt>
</run>
```

### The Problem
**You lose all the mid-session learning.**

What actually happened:
- **Hour 1.5**: Father's story triggered victim bias. Mediator corrected course.
- **Hour 3.2**: Mother claimed false fact. Contradiction detector alerted.
- **Hour 4.7**: Father's BATNA became clear. Changed strategy.

All lost. The final note captures none of this.

### Why This Matters for Harness Learning
Run notes at 8-hour boundary are too coarse to extract:
- When did the model misunderstand?
- What mode transitions worked vs failed?
- Which constraints were helpful vs hampering?

### The Cost to Fix
You need **continuous session checkpoints**, not end-of-session notes:
```python
class SessionCheckpoint:
    timestamp: datetime
    mode: str              # listening, analysis, response, etc
    event: str            # what changed
    decisions_made: List[str]
    contradictions_found: int
    tokens_used_this_period: int
```

- Checkpoint every 15-30 minutes
- Store as polips (not run notes)
- Query via reef index: `/reef index --type session-checkpoint --filter "mode:response"`

**Cost**: ~400 LOC for checkpoint system, plus ongoing storage

**Realization**: This isn't "run notes" anymore. It's session event logging.

---

## Edge Case 3: The Retention Liability Trap

### The Scenario (From Run-021)

Karen said:
> "The actual opponent is a motivated counter-party with legal discovery powers. Every piece of data you create can be subpoenaed."

Now imagine your run notes say:
```xml
<run id="mediation-case-XYZ">
  <what-didnt>
    <item>Father's inconsistency on childcare hours—flagged 4 times</item>
    <item>Mother's BATNA clearly insufficient, must push harder</item>
    <item>Mediator's strategy: exploit fatigue after hour 6</item>
  </what-didnt>
</run>
```

### What Happens
Opposing counsel issues discovery subpoena:
```
"All documents related to preparation for mediation in case XYZ"
```

Your run notes are discoverable. They show:
- You knew opponent's BATNA was weak (suggests you exploited it)
- You planned to exploit fatigue (suggests bad faith)
- You tracked inconsistencies (suggests you were gathering ammunition)

**This loses the case.**

### Why Run Notes Make It Worse
Run notes create *contemporaneous written record* of your strategy. Hand-written notes could claim "privilege" or "work product." Structured, timestamped files in `.claude/runs/` are harder to defend.

### The Solution
**Never write notes that would hurt you if discovered.**

So run notes for mediation must:
- Never mention strategy
- Never mention opponent weaknesses
- Never mention confidence/uncertainty
- Never mention timelines/pressure

This reduces run notes to:
```xml
<run id="mediation-case-XYZ">
  <summary>Session completed</summary>
  <outcome>Agreement reached on custody schedule</outcome>
</run>
```

**Problem**: This is useless for learning. It's just a timestamp.

### The Conclusion
If you're using the harness for legally-sensitive work (mediation, litigation support), **run notes are a liability, not a tool**.

---

## Edge Case 4: The Vocabulary Fragmentation Trap

### The Scenario
You have run notes from 21 agents/runs. They use different vocabularies:

**Run-006** (Architect): "Polip extraction pipeline efficient"
**Run-010** (Visionary): "Polips surfaced quickly to context"
**Run-015** (Karen): "Polip authority model undefined"
**Run-020** (Frontend Agent): "Component state management via polips slow"

### The Extraction Problem
You want to extract: "What do we know about polip performance?"

But you have:
- "efficient" (run-006, subjective)
- "quickly" (run-010, unmeasured)
- "undefined" (run-015, design issue, not performance)
- "slow" (run-020, comparative, but vs what?)

### Option A: Manual Normalization
You read all 21 notes, map to canonical vocabulary:
```
"efficient" → PERFORMANCE_ACCEPTABLE
"quickly" → PERFORMANCE_ACCEPTABLE
"undefined" → DESIGN_DEBT
"slow" → PERFORMANCE_UNACCEPTABLE
```

**Cost**: 30 min per 5 runs = 2 hours per 21 runs

### Option B: LLM Normalization
You build a prompt that extracts canonical facts from notes:
```python
response = claude.messages.create(
    model="claude-opus",
    messages=[{
        "role": "user",
        "content": f"""
Categorize this run note into our taxonomy:
{run_note}

Output JSON:
{{
  "performance": ["acceptable", "unacceptable", "unknown"],
  "design_debt": ["yes", "no", "maybe"],
  "next_priority": "string"
}}
"""
    }]
)
```

**Cost**: ~50 LOC to build, 5-10 cents per run to execute
**Risk**: LLM hallucinates categories (40% error rate possible)

### The Truth
By the time you've normalized vocabulary, you could have:
- Read the run notes manually (cheaper for 21 runs)
- Refactored to structured data format (expensive but pays off at 50+ runs)
- Built domain-specific taxonomy upfront (prevents problem)

### The Real Problem
Run notes aren't structured. This is a feature ("agents write freely") and a bug ("can't extract patterns").

---

## Edge Case 5: The Cross-Run Temporal Dependency

### The Scenario
Run-021 identifies: "Retention policy creates liability"
Run-022 implements: "Don't persist session data"

But the improvement from run-021 to run-022 isn't captured *in the notes*.

### Why This Matters
You want to extract: "Run notes lead to improvements. Which ones?"

But run-022's notes might say:
```
<what-worked>
  <item>Session-only memory prevented data leaks</item>
</what-worked>
```

Without linking back to run-021's "discovery liability" finding, you can't say:
- Was this improvement driven by run-021's insight?
- Or was it independent discovery?
- Or was it random chance?

### The Extraction Problem
```
run-021 mentions: "retention policy creates liability"
       ↓
     [human synthesizes for 1-2 hours]
       ↓
run-022 implements: "session-only memory"
       ↓
       [someone measures improvement]
       ↓
Unclear: Did run notes drive the improvement?
```

To make this visible, you need:
1. Explicit linking: "run-022 implements fix from run-021 insight #7"
2. Impact tracking: "this fix reduced liability by X"
3. Causal validation: "measuring showed improvement"

**Cost to implement**: ~300 LOC for linking system

**Problem**: By then you're building a full decision tracking system (not "run notes").

---

## Edge Case 6: The Context Erosion Problem

### The Scenario
Run-010 says: "Evidence search on case law took 3.2s"

Today (run-021), you ask: "Is evidence search slow?"

What information is *missing* from the note?
- Was the dataset 100 cases or 10,000?
- Was latency acceptable? (3.2s might be fast for legal research)
- Had you optimized the index yet?
- Was this Groq or Claude?

### The Decay Curve
```
Time since run | Context available
    0 hours   | 100% (you remember conditions)
   24 hours   | 60%  (vague memory)
    1 week    | 20%  (need to read surrounding commits)
    1 month   | 5%   (need to reconstruct from git history)
    3 months  | <1%  (context completely lost)
```

### Why This Breaks Pattern Extraction

If you accumulate 50 runs over 6 months:
- Early runs have nearly-zero context
- Patterns extracted from decontextualized data are unreliable
- You can't confidently say "performance improved" without knowing original conditions

### The Solution
Not "better run notes." Instead: **Everything is a polip.**

Polips include:
- Timestamp (when)
- Conditions (git commit, input data size, model used)
- Outcome (latency, quality, tokens)
- Analysis (why this happened)

Run notes are just narrative + ideas. Polips are data + analysis + relationships.

---

## Edge Case 7: The False Positive Storm

### The Scenario
Agent writes:
```xml
<what-worked>
  <item>Fast research with Groq API</item>
</what-worked>
```

You extract: "Groq is fast"

But actually:
- Groq happened to have no queuing that day
- Tomorrow Groq is throttled, becomes slow
- Your "pattern" was observational accident

### Why LLM Agents Hallucinate Success
LLMs naturally produce confident-sounding, plausible explanations. When asked "what worked?", they generate:
- Sensible-sounding reasons
- Positive narrative bias
- Correlation misread as causation

Example: Run-017 notes say "spark swarm inverts every premise. Is this insight or pattern-lock?"

The agent *thought* it was finding truth. Karen *knew* it might be oscillation.

### The Problem for Automated Learning
```
Agent: "What worked? X, Y, Z"
Script: Extract "X, Y, Z are improvements"
Harness: Implement based on X, Y, Z
Result: 60% of "improvements" don't actually improve
```

This is called "data drift" or "measurement error."

### The Cost to Fix
You need adversarial validation (like Karen) for every finding. But then it's not "automated learning." It's:
1. Agent observes
2. Expert validates
3. You implement

That's not "run notes learning." That's "run notes feedback, expert validation, human implementation."

---

## Edge Case 8: The Incompatible Agent Upgrade Problem

### The Scenario
Run-001 to run-010: Using Claude Opus 4
Run-011 to run-021: Using Claude Haiku 4.5

Now you're comparing runs across model changes. Your run notes say:
```
run-005: "Response latency 2.3s"
run-015: "Response latency 1.2s"
Pattern extracted: "System is 50% faster!"
```

But actually:
- Haiku is cheaper and faster (not a harness improvement, a model change)
- Opus might produce higher-quality responses (trade-off)
- They're not comparable

### Why Pattern Extraction Fails
You can't automatically know:
- Which differences are agent improvements?
- Which are model changes?
- Which are input variance?
- Which are measurement error?

You need a control group:
```
run-022: Opus on scenario X
run-023: Haiku on same scenario X
Compare apples-to-apples
```

But run notes alone can't enforce this.

---

## Summary: The Seven Failure Modes

| Case | Problem | Cost to Fix | Better Alternative |
|------|---------|-------------|-------------------|
| 64-agent swarm | 640 bullets = noise | ~3500 LOC | Distributed tracing |
| Long sessions | 8hr learning lost | ~400 LOC | Continuous checkpoints |
| Legal discovery | Notes are liability | Can't fix | Session-only ephemeral |
| Vocabulary drift | Can't extract patterns | ~300 LOC | Structured taxonomy |
| Cross-run linking | Causality unclear | ~300 LOC | Decision polips |
| Context erosion | Old notes meaningless | ~200 LOC | Polip context storage |
| LLM confabulation | False positives 40% | ~500 LOC | Expert validation gates |
| Model changes | Apples ↔ oranges | ~200 LOC | Controlled experiments |

**Total to handle all cases: ~5800 LOC**

**Simpler approach: Use polips + structured data + human validation**

---

## The Real Lesson

"Agent run notes" work fine as human narrative.

They fail badly as:
- Automated learning signals
- Performance metrics
- Decision drivers
- Discovery-safe audit trails

Stop trying to make them be all four. Pick one:

1. **Narrative continuity?** → Keep XML run notes (cheap)
2. **Learning loop?** → Build metrics.json + polips (medium cost)
3. **Legal compliance?** → Build ephemeral sessions (expensive)
4. **Scale to swarms?** → Build distributed telemetry (very expensive)

You can't have all four without 10K+ LOC.

---

*KAREN's verdict: Run notes are a feature, not a system. Don't let them grow into something they can't handle.*
