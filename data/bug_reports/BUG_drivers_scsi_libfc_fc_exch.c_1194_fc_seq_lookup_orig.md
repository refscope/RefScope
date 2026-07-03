# REAL BUG: drivers/scsi/libfc/fc_exch.c:1194 fc_seq_lookup_orig()

**Confidence**: MEDIUM | **Counter**: `$->ex_refcnt.counter`

## Reasoning

| 1194 | return sp   | NO (fc_exch_find likely does NOT increment refcount, tool says excess put) | YES (fc_exch_release(ep)) | ❌ EXCESS PUT | If find did not take a reference, this is a premature/dangling put. Warning exactly matches this scenario. |

## Full Response

```
## Path Analysis

```
| Line | Return Type | GET Done?         | PUT Done? | Balanced? | Notes                                                                                                                      |
|------|-------------|-------------------|-----------|-----------|----------------------------------------------------------------------------------------------------------------------------|
| 1182 | return NULL | NO (ep is NULL, fc_exch_find returned NULL; if find is unconditional get then it should inc even for NULL, which is impossible; typical find returns NULL without ref) | N/A       | ✅         | No object, no reference held.                                                                                              |
| 1194 | return sp   | NO (fc_exch_find likely does NOT increment refcount, tool says excess put) | YES (fc_exch_release(ep)) | ❌ EXCESS PUT | If find did not take a reference, this is a premature/dangling put. Warning exactly matches this scenario. |
```

## VERDICT: REAL_BUG
## CONFIDENCE: MEDIUM

`fc_exch_find()` returns a pointer without holding a reference (typical for a lookup/“find” API), yet `fc_seq_lookup_orig()` unconditionally calls `fc_exch_release(ep)`, dropping a non‑existent reference → excess put. The static‑analysis warning and the function’s pattern of returning a pointer into the released object reinforce that a reference was never taken.
```
