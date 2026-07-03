# REAL BUG: drivers/misc/apds990x.c:1012 apds990x_power_state_store()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L1012 (value == 0, pm_runtime_suspended) | return len | NO | NO | ✅ | condition skips put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L996 | error return (kstrtoul fails) | NO (before get) | N/A | ✅ | |
| L1003–L1015 (value != 0) | return len | YES (pm_runtime_get_sync) | NO | ❌ LEAK | unconditional get, no put; reference held for power-on |
| L1010 (value == 0, !pm_runtime_suspended) | return len | NO | YES (pm_runtime_put) | ❌ EXCESS PUT | put called without a prior get in this store function |
| L1012 (value == 0, pm_runtime_suspended) | return len | NO | NO | ✅ | condition skips put |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`apds990x_power_state_store` calls `pm_runtime_put(dev)` on the `value==0` path without a corresponding `pm_runtime_get_sync` in the same invocation. The guard `!pm_runtime_suspended(dev)` does not guarantee `usage_count > 0` (device can be active with count 0), so a user writing 0 twice can underflow `power.usage_count`.
```
