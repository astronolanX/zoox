# Polip Operations

Core operations for reef memory management.

## Commands

### Surface
Bring polip content into context based on relevance.

```
reef surface <query>
reef index --search "<query>"
```

### Sprout
Create new polip with type and content.

```
reef sprout <type> "<summary>"
# Types: thread, decision, constraint, context, fact
```

### Sync
Check reef integrity and optionally fix issues.

```
reef sync           # Check only
reef sync --fix     # Auto-repair
reef sync --dry-run # Preview changes
```

### Health
View reef vitality metrics.

```
reef reef           # Health overview
reef health --json  # Machine-readable
```

## Polip Types

| Type | Coral Term | Purpose |
|------|------------|---------|
| thread | current | Active work stream |
| decision | deposit | Strategic choice |
| constraint | bedrock | Foundation rules |
| context | context | Session state |
| fact | fossil | Preserved knowledge |

## Scopes

| Scope | Behavior |
|-------|----------|
| always | Loaded every session, protected from pruning |
| project | Project-specific, normal lifecycle |
| session | Temporary, expires with session |

## Best Practices

1. Use threads for ongoing work
2. Crystallize decisions when validated
3. Protect constraints with `always` scope
4. Archive stale threads to fossils
