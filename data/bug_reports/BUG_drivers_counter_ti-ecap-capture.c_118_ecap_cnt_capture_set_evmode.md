# REAL BUG: drivers/counter/ti-ecap-capture.c:118 ecap_cnt_capture_set_evmode()

**Confidence**: HIGH | **Counter**: `counter->parent->power.usage_count.counter`

## Reasoning

nc end) | Conditional: YES if pm_runtime_get_sync ret ≥ 0 (count incremented); NO if ret < 0 (no increment) | YES (unconditional pm_runtime_put_sync at L117) | ❌ Not balanced on GET-failure path | Return value unchecked; if get fails, put is called without a matching ref → excess put (underflow) |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L118 | void return (func end) | Conditional: YES if pm_runtime_get_sync ret ≥ 0 (count incremented); NO if ret < 0 (no increment) | YES (unconditional pm_runtime_put_sync at L117) | ❌ Not balanced on GET-failure path | Return value unchecked; if get fails, put is called without a matching ref → excess put (underflow) |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Unchecked return of pm_runtime_get_sync; if it fails (<0), no usage_count increment, but unconditional pm_runtime_put_sync still runs, causing an excess put / underflow.
```
