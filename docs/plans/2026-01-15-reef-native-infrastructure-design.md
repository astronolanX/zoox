# Reef as Native AI Infrastructure

**Date:** 2026-01-15
**Status:** Vision / Brainstorm
**Authors:** Nolan + Claude

## Vision

Reef is native infrastructure that grows from polips generated from contextual insights. It creates the physical infrastructure of AI memory on machines. `.reef` and `.polip` are new filetypes designed specifically for AI — vessels for context to travel bilaterally between contextual-based organisms.

Not an application bolted onto existing structures. Infrastructure that AI grows on.

---

## Polip Lifecycle

```
spawn → drift → attach → grow → bud → calcify
                                  ↓
                              (death paths)
```

### Lifecycle Stages

| Stage | Behavior |
|-------|----------|
| **Spawn** | Born with genome (type, scope, triggers) |
| **Drift** | Unattached, seeking home via affinity signals |
| **Attach** | Settles where need + semantic similarity pull |
| **Grow** | Accumulates content, references, access counts |
| **Bud** | Under pressure, spawns satellite polips |
| **Calcify** | Triggers align → hardens into structure |

### Calcification Triggers

Five triggers, combinatorial — genome encodes which apply:

| Trigger | Description |
|---------|-------------|
| **Time** | Age without modification |
| **Usage** | High LRU access count |
| **Ceremony** | Explicit human/AI blessing |
| **Consensus** | Multiple polips reference it |
| **Genome** | Type determines destiny |

Combinations matter: Time × Genome determines decay rate. Usage × Consensus accelerates crystallization. Ceremony × Consensus requires N validators.

### Mutation

Polips mutate through budding. When a polip needs more storage or capacity, a drifting polip spawns and grows to support it. Child polips can express different genome traits based on environmental pressure.

### Attachment Mechanics

- **Affinity** — Semantic similarity and wiki-links create pull
- **Need** — Survival pressure from reef regions demanding that genome type

---

## Death and Decay

| Trigger | Outcome | Rationale |
|---------|---------|-----------|
| **Staleness** | Fossil layer | Might be valuable later |
| **Supersession** | Nutrient cycling | Absorbed into better version |
| **Contradiction** | Skeleton remains | Shape as cautionary history |
| **Orphaning** | Drift → re-attach or dissolve | One more chance |
| **Explicit pruning** | Full deletion | Conscious choice = clean |

### Reef Geology

```
┌─────────────────────────────────────┐
│  Active Layer (living)              │  ← current surfacing
├─────────────────────────────────────┤
│  Skeletal Layer (shapes)            │  ← contradicted, hollowed
├─────────────────────────────────────┤
│  Fossil Layer (archived)            │  ← stale, searchable
├─────────────────────────────────────┤
│  Sediment (absorbed)                │  ← nutrients in other polips
└─────────────────────────────────────┘
```

---

## Digital Ecology

Reef exists in a digital biome with other organisms:

| Organism Type | Examples | Relationship |
|---------------|----------|--------------|
| **Native data** | Files, bytes, streams | Substrate reef grows on |
| **Other filetypes** | .json, .md, .sqlite | Neighboring species |
| **Beneficial agents** | AI assistants, sync tools | Symbionts |
| **Parasites** | Broken links, stale refs | Feed without contributing |
| **Pathogens** | Malware, spyware, viruses | Hostile attackers |

### Boundary: Protected Zone

Reef is a walled garden with immune system:

| Immune Function | Mechanism |
|-----------------|-----------|
| **Validation at entry** | Schema checks, provenance verification |
| **Anomaly detection** | Flagging misbehaving polips |
| **Quarantine** | Suspicious content isolated |
| **Repair** | Damaged polips reconstructed from consensus |
| **Memory** | Known threats recognized faster |

### Entry Protocol: Federated Consensus

Multiple validators must agree for external data to become a polip:

| Validator | Role | Weight |
|-----------|------|--------|
| Schema validator | Structure correct? | Gate (pass/fail) |
| Provenance checker | Chain of custody | Trust signal |
| Semantic analyzer | Contradictions? | Conflict detection |
| Human (optional) | Explicit blessing | Override/veto |
| Existing polips | Alignment check | Affinity vote |

**Disagreement handling:** Quarantine as default, escalation for persistent disputes.

---

## Native File Format

### Why Native?

Stop borrowing human document formats. Build AI-native:

| Human-First | AI-Native |
|-------------|-----------|
| Optimized for rendering | Optimized for parsing/injection |
| Human-readable primary | Machine-readable primary |
| Static structure | Lifecycle-aware |
| Content-focused | Relationship-focused |
| Version = replacement | Version = evolution |

### Proposed `.polip` Structure

```
filename.polip
├── header (fixed, fast to parse)
│   ├── genome (type, scope, triggers)
│   ├── lifecycle_state
│   ├── trust_score
│   ├── lineage (parent_id, generation)
│   └── checksum
├── body (variable)
│   ├── content
│   ├── embeddings (optional)
│   └── attachments
└── graph (relationships)
    ├── inbound_links
    ├── outbound_links
    └── validators
```

### Content Embedding Strategy

Lifecycle-based:

| Polip State | Content Strategy |
|-------------|------------------|
| **Drifting** | Referenced (lightweight) |
| **Attached/Growing** | Hybrid (small inline, large referenced) |
| **Calcified** | Embedded (self-contained) |
| **Fossil** | Compressed archive |

---

## Cross-System Portability

### Starting Point: L0 (Plain directory + files)

```
.reef/
├── manifest.xml
├── polips/
│   └── {id}.polip.xml
├── index/
├── fossils/
├── quarantine/
└── .reefrc
```

Portable today: XML/JSON readable everywhere, git-friendly, human-inspectable.

### Growth Path

| Level | Description |
|-------|-------------|
| L0 | Userland (files in directory) |
| L1 | Registered filetype (MIME, icons) |
| L2 | Indexed/searchable (Spotlight, Windows Search) |
| L3 | Filesystem integration (FUSE mount) |
| L4 | Kernel/OS primitive |

Start soft at L0, calcify toward L3/L4 based on learnings.

### Activation Layers

```
┌─────────────────────────────────────┐
│  L3: System Daemon                  │  ← Install and forget
├─────────────────────────────────────┤
│  L2: Framework Middleware           │  ← LangChain, Claude Code
├─────────────────────────────────────┤
│  L1: SDK                            │  ← reef.spawn(), reef.surface()
├─────────────────────────────────────┤
│  L0: File Format                    │  ← .polip / .reef files
└─────────────────────────────────────┘
```

Dream UX: `pip install reef` → AI starts creating reefs automatically.

---

## Infrastructure Gaps Reef Bridges

Build order (inside-out architecture):

### 1. Files vs Relationships (Skeleton)

**Gap:** `.claude/` directories are files with manual links, no enforced structure.

**Calcium bridge:** Polips are graph nodes. References create structural pressure. Popular polips calcify into load-bearing infrastructure.

### 2. Session vs Evolution (Growth)

**Gap:** LangGraph checkpoints are static snapshots that reset between sessions.

**Calcium bridge:** Threads drift, attach, grow, calcify into bedrock. Memory that matures, not just persists.

### 3. Cloud-first vs Local-first (Sovereignty)

**Gap:** EverMemOS, vector DBs require servers and send data off-machine.

**Calcium bridge:** Reef grows locally. Export fossilized snapshots when sharing. The reef is sovereign.

### 4. Search vs Provenance (Trust)

**Gap:** Vector DBs find similar content but have no trust, no history.

**Calcium bridge:** Every polip knows origin, validators, contradictions. Memory of memory.

### 5. Protocol vs Memory (Interface)

**Gap:** MCP defines access, not what to remember.

**Calcium bridge:** Reef exposes MCP interface while maintaining lifecycle underneath. MCP is one access method, not the whole story.

---

## Research Context

### Industry Signals (2024-2026)

- **Memory as state layer**: Microsoft Foundry Agent Service provides managed long-term memory
- **File system as context interface**: "Everything is Context" paper proposes Unix-like abstraction
- **Brain-inspired architecture**: EverMemOS uses 4-layer structure (Agentic → Memory → Index → API)
- **OS integration models**: Apple Intelligence (system-level, on-device) vs Microsoft Copilot (hybrid, cloud-heavy)

### Key Sources

- [Memory in the Age of AI Agents (arXiv)](https://arxiv.org/abs/2512.13564)
- [Everything is Context (arXiv)](https://arxiv.org/abs/2512.05470)
- [EverMemOS (GitHub)](https://github.com/EverMind-AI/EverMemOS)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

## Next Steps

1. **Gap 4 (Relationships)**: Design graph-native polip structure
2. **Gap 3 (Evolution)**: Implement calcification triggers
3. **Gap 1 (Local-first)**: Ensure zero-dependency operation
4. **Gap 5 (Provenance)**: Build validator/lineage chain
5. **Gap 2 (Protocol)**: MCP bridge implementation

---

## Open Questions

- Binary vs text encoding for `.polip` files?
- Exact calcification threshold values?
- Federation mechanics for multi-machine reefs?
- How do reefs discover each other? (`reef drift discover`)
- Garbage collection for orphaned drifting polips?

---

*This design crystallizes from brainstorming. It will evolve.*
