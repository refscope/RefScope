# REAL BUG: sound/soc/ti/omap-dmic.c:420 omap_dmic_probe()

**Confidence**: HIGH | **Counter**: `dmic->dev->power.usage_count.counter`

## Reasoning

| L420 (pm_runtime_get_sync ret < 0) | success (return 0) | NO (no inc on error, contract says <0 = no inc) | YES (pm_runtime_put_sync is unconditional) | ❌ EXCESS PUT | Unchecked return; put executes even though get didn't increment → underflow. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L420 (pm_runtime_get_sync ret >= 0) | success (return 0) | YES (inc happened) | YES (pm_runtime_put_sync) | ✅ | Normal, balanced path. |
| L420 (pm_runtime_get_sync ret < 0) | success (return 0) | NO (no inc on error, contract says <0 = no inc) | YES (pm_runtime_put_sync is unconditional) | ❌ EXCESS PUT | Unchecked return; put executes even though get didn't increment → underflow. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_sync` return value not checked; on failure, the subsequent `pm_runtime_put_sync` decrements a counter that was never incremented, causing an excess put.
```
