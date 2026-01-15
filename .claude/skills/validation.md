# Validation Protocols

Two-tier validation for reef operations.

## Tier 1: Schema Validation

Fast, deterministic checks run automatically.

### Checks
- Required fields present
- Types match expected
- Constraints satisfied
- Format correct

### Example
```python
schema_checks = [
    ("required_field:summary", polip.summary is not None),
    ("type_check:scope", polip.scope in VALID_SCOPES),
    ("format_check:date", is_valid_date(polip.updated)),
]
```

## Tier 2: Semantic Validation

LLM-based judgment for quality and intent.

### Checks
- Does output match stated intent?
- Is quality acceptable?
- Is information complete?
- Are there hallucinations or contradictions?

### When Required
- Before polip calcification
- Before pruning execution
- Before task completion claims
- For any destructive operation

## Validation Flow

```
Input → Tier 1 (Schema) → [Pass/Fail]
                ↓
         [If Pass]
                ↓
        Tier 2 (Semantic) → [Pass/Warn/Fail]
                ↓
         [Final Decision]
```

## Override Protocol

Tier 1 failures block operation.
Tier 2 warnings can be overridden with `--force`.
Tier 2 failures require human review.
