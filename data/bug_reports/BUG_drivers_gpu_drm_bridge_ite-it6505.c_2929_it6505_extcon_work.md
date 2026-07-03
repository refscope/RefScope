# REAL BUG: drivers/gpu/drm/bridge/ite-it6505.c:2929 it6505_extcon_work()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L2929 (state false → pm_runtime_put_sync) | void via unlock | NO in this invocation | YES (decrements usage_count) | ❌ EXCESS PUT if previous get failed or never happened | put is unconditional; can drive count below zero |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2893 (early return) | void        | NO  | N/A | ✅ | enable_drv_hold guard, no get/put invoked |
| L290? (goto unlock: state unchanged or <0) | void via unlock | NO  | NO  | ✅ | state didn’t change, no work needed |
| ~L2912 (state true, ret >= 0) | void via unlock | YES (usage_count incremented) | NO  | ⚠️  | deferred put expected when state becomes false |
| ~L2912 (state true, ret < 0 → it6505_poweron) | void via unlock | NO (get failed, no increment) | NO  | ✅ | this call is balanced, but leaves usage_count unchanged |
| L2929 (state false → pm_runtime_put_sync) | void via unlock | NO in this invocation | YES (decrements usage_count) | ❌ EXCESS PUT if previous get failed or never happened | put is unconditional; can drive count below zero |

**PRE-VERDICT CHECKLIST**  
1. “Held for device lifetime” – not applicable here; the put is explicit, not a probe error path.  
2. “Ownership transferred” – no ownership transfer; the device’s power reference is managed directly with get/put.  
3. Unconditional GET? – pm_runtime_get_sync is conditional; error path does **not** increment. The corresponding put always runs on state false → risk of mismatch.  
4. goto out between GET and PUT? – not relevant; the issue is cross-invocation: the put at L2929 does not check whether a prior get succeeded, so a failed get leads to an excess put.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`pm_runtime_get_sync` at L2912 can fail without incrementing usage_count, but the later `pm_runtime_put_sync` at L2929 unconditionally decrements, causing a negative refcount (excess put).
```
