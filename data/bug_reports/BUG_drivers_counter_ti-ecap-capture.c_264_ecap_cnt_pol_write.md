# REAL BUG: drivers/counter/ti-ecap-capture.c:264 ecap_cnt_pol_write()

**Confidence**: HIGH | **Counter**: `counter->parent->power.usage_count.counter`

## Reasoning

ths) | Conditional: YES if `pm_runtime_get_sync` returned >=0; NO if <0 | YES (unconditional) | ✅ Only if get succeeded. ❌ If get failed, **excess put** (GET=NO, PUT=YES) | Return value of `pm_runtime_get_sync` not checked; contract says <0 means no increment, so put must not be called on error. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L264 + return 0 | success (all paths) | Conditional: YES if `pm_runtime_get_sync` returned >=0; NO if <0 | YES (unconditional) | ✅ Only if get succeeded. ❌ If get failed, **excess put** (GET=NO, PUT=YES) | Return value of `pm_runtime_get_sync` not checked; contract says <0 means no increment, so put must not be called on error. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
pm_runtime_get_sync return unchecked; on failure (<0) no usage_count inc, but pm_runtime_put_sync always called, leading to refcount underflow.
```
