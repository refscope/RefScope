# REAL BUG: drivers/gpu/drm/msm/disp/mdp5/mdp5_kms.c:62 mdp5_hw_init()

**Confidence**: HIGH | **Counter**: `dev->power.usage_count.counter`

## Reasoning

| L64  | return 0    | YES (pm_runtime_get_sync called) | YES (pm_runtime_put_sync called) | NO | pm_runtime_get_sync return not checked; on failure (<0) counter not incremented, but pm_runtime_put_sync decrements → excess put. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L64  | return 0    | YES (pm_runtime_get_sync called) | YES (pm_runtime_put_sync called) | NO | pm_runtime_get_sync return not checked; on failure (<0) counter not incremented, but pm_runtime_put_sync decrements → excess put. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
pm_runtime_get_sync return value unchecked; if it fails, the counter is not incremented, yet pm_runtime_put_sync always runs, causing an excess put.
```
