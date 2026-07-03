# REAL BUG: drivers/accel/habanalabs/common/command_submission.c:1093 hl_cs_rollback_all()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L1081–L1086 | Inside list_for_each_entry_safe: cs_get(cs) → cs_rollback(hdev, cs) → cs_put(cs) | YES (cs_get is unconditional get) | YES (cs_rollback does a put per contract) + YES (cs_put does another put) | ❌ EXCESS PUT | One get, two puts per CS → refcount underflow |

## Full Response

```
```
| Line | Path Description | GET Done? | PUT Done? | Balanced? | Notes |
|------|------------------|-----------|-----------|-----------|-------|
| L1081–L1086 | Inside list_for_each_entry_safe: cs_get(cs) → cs_rollback(hdev, cs) → cs_put(cs) | YES (cs_get is unconditional get) | YES (cs_rollback does a put per contract) + YES (cs_put does another put) | ❌ EXCESS PUT | One get, two puts per CS → refcount underflow |
```

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`cs_get` acquires a reference, but `cs_rollback` (which internally performs a put via `staged_cs_put`) and the subsequent `cs_put` each release a reference, causing a double‑put and refcount underflow.
```
