# /investigate

Recursive investigation harness for validating insights at scale. Builds on top of `/spark` with automatic depth routing based on curiosity concentration.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     GLOBAL HARNESS (listener)                   │
│  Auto-detects: architectural decisions, creative/pragmatic      │
│  tension, lock-in risks, NIH patterns, confirmation bias        │
└─────────────────────────────────────────────────────────────────┘
                              ↓ trigger detected
┌─────────────────────────────────────────────────────────────────┐
│                         SPARK PHASE                             │
│  Always invoked first. Generates curiosity concentrations.      │
│  Each insight scored 0-100% emergent.                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓ yields scored
┌─────────────────────────────────────────────────────────────────┐
│                      CURIOSITY ROUTER                           │
│                                                                 │
│  < 60%  → Log to incubator, continue                           │
│  60-80% → Light investigation (researcher + validator)          │
│  80-90% → Full squad investigation                              │
│  90%+   → RECURSIVE VISIONARY (spawns sub-harness)             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    RECURSIVE VISIONARY                          │
│                                                                 │
│  For each 90%+ curiosity concentration:                         │
│  1. Spawn dedicated visionary agent                             │
│  2. Visionary can invoke own trench swarm                       │
│  3. Visionary can recursively invoke sub-harness                │
│  4. Reports findings back to parent                             │
│                                                                 │
│  Depth limit: 3 levels (prevent infinite recursion)             │
└─────────────────────────────────────────────────────────────────┘
                              ↓ all outputs collected
┌─────────────────────────────────────────────────────────────────┐
│                    INVESTIGATION FUNNEL                         │
│                                                                 │
│  Collects: spark outputs, visionary reports, trench findings    │
│  Deduplicates, clusters by theme, ranks by signal strength      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    INVESTIGATION SQUAD                          │
│  Researcher │ Validator │ Analyst │ Karen (adversarial)        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DELIBERATION ROUND                           │
│  Squad presents TO EACH OTHER, cross-examines, maps consensus   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              FINAL REPORT → USER DECISION (veto)               │
└─────────────────────────────────────────────────────────────────┘
```

## Global Harness: Trigger Detection

### Explicit Triggers
- User says "investigate", "research", "validate"
- User questions decision: "should we...", "is this right..."
- User expresses uncertainty: "I'm not sure if..."

### Implicit Triggers (auto-detect)
| Pattern | Signal | Action |
|---------|--------|--------|
| Architectural decision | "let's use X for Y" | Suggest investigation |
| Lock-in risk | Format, protocol, schema | Require investigation |
| NIH pattern | "build our own", "custom" | Auto-invoke |
| Creative/pragmatic gap | Spark says X, industry Y | Auto-invoke |
| High stakes | "can't reverse", "affects all" | Suggest investigation |
| Confirmation bias | User strongly prefers one | Invoke Karen |

### Escalation Thresholds
```
Token cost > 50k     → Warn user, request approval
Trench count > 5     → Warn user, request approval
Recursion depth > 2  → Hard limit, summarize and stop
Wall time > 30 min   → Checkpoint, offer pause
```

## Curiosity Levels (Depth Routing)

| Level | Threshold | Action | Duration |
|-------|-----------|--------|----------|
| Note | < 60% | Log to incubator | Instant |
| Light | 60-80% | Researcher + Validator | 5-10 min |
| Full | 80-90% | All 4 squad members | 15-30 min |
| Recursive | 90%+ | Visionary + sub-harness | 30-60 min |

### Recursive Visionary Behavior
When spark yields 90%+ emergent insight:
1. Spawn dedicated visionary for that concentration
2. Visionary can spawn its own trench swarm
3. Visionary can invoke sub-harness (depth limit: 3)
4. All findings flow back to investigation funnel

## Investigation Squad

### Researcher
**Mission:** Find what exists
- Prior art (academic, open source, production)
- Historical attempts (successes AND failures)
- Adjacent patterns in other domains
**Output:** Evidence map with citations

### Validator
**Mission:** Verify claims with data
- Test quantitative assertions (benchmarks)
- Find methodology issues
- Flag unfounded claims
**Output:** Claim verification matrix

### Industry Analyst
**Mission:** What's winning in production
- Current market leaders
- Emerging trends, failed approaches
- Community sentiment
**Output:** Industry landscape report

### Karen (Adversarial Counsel)
**Mission:** Find problems and counterarguments
**Modes:** CRITICAL ↔ SKEPTICAL (alternates)
**Authority:** NONE - advisory only, user holds veto
**Constraint:** Must cite sources for all claims
**Output:** Counterargument brief with citations

## Deliberation Protocol

1. **Individual Presentations** (30 sec each)
   - Each agent: top 3 findings, no interruptions

2. **Cross-Examination** (2 min)
   - Agents challenge each other
   - "Researcher, how do you reconcile X with Analyst's Y?"

3. **Karen's Challenge** (1 min)
   - Stress-test emerging consensus
   - "Even if you all agree, consider Z..."

4. **Consensus Mapping**
   - Strong (4/4), Weak (3/4), Dissent (2v2), Unknown

5. **Uncertainty Declaration**
   - What couldn't be verified
   - What needs more research

## Final Report Format

```markdown
# Investigation Report: [Topic]

## WHAT
[1-2 sentence core finding]

## HOW
- Type: Light/Full/Recursive
- Agents: [count], Trenches: [count]
- Duration: [time], Tokens: [estimate]

## WHY
Evidence summary + counterarguments considered

## WHO
| Agent | Contribution | Confidence |
|-------|--------------|------------|
| Researcher | [summary] | high/med/low |
| Validator | [summary] | high/med/low |
| Analyst | [summary] | high/med/low |
| Karen | [challenges] | N/A |

## CONSENSUS
[Where squad agreed]

## DISSENT
[Where disagreed + reasoning]

## GAPS
[What remains unknown]

## DIRECTION
**Recommended:** [synthesis]
**Alternatives:** [if user disagrees]

## USER DECISION
[ ] Accept recommendation
[ ] Choose alternative: ___
[ ] Deeper investigation on: ___
[ ] Override with reasoning: ___
```

## Integration

- **/spark** → Outputs feed curiosity router
- **/team** → Trenches spawn via team routing
- **reef** → Reports become decision polips

## Example Flow

```
User: "Should we use S-expressions or XML?"

Harness: Lock-in risk detected → auto-invoke

Spark yields:
  95% "Format may be irrelevant"  → Recursive visionary
  82% "Delta compression key"     → Full squad
  71% "Sigils aid parsing"        → Light investigation

Funnel collects all → Squad deliberates → Report generated

User decides (veto power)
```

## When NOT to Use

- Simple questions (no decision)
- Reversible decisions (low stakes)
- Already executed (don't second-guess done work)
