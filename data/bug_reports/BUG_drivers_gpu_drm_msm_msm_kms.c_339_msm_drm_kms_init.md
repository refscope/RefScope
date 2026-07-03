# REAL BUG: drivers/gpu/drm/msm/msm_kms.c:339 msm_drm_kms_init()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| **L326 (get fails) → L331** | goto err | NO | YES | ❌ **UNDERFLOW** | Same as above, extra put on error path. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L274 | error        | NO (before get) | N/A  | ✅ | Early return, no pm_runtime call. |
| L279 | error        | NO               | N/A  | ✅ | |
| L285 | goto err     | NO               | N/A  | ✅ | kms_init failure. |
| L298 | goto err     | NO               | N/A  | ✅ | hw_init failure. |
| L314 | goto err     | NO               | N/A  | ✅ | kthread_run_worker failure. |
| L323 | goto err     | NO               | N/A  | ✅ | drm_vblank_init failure. |
| L326‑328‑336 (get success) | return 0 | YES (pm_runtime_get_sync succeeded, incremented counter) | YES (L328) | ✅ | Get and put pair executed. |
| L326‑328‑331 (msm_irq_install fail) | goto err | YES | YES | ✅ | put called before goto. |
| **L326 (get fails) → L336** | return 0 | NO (pm_runtime_get_sync returned <0, **counter NOT incremented**) | YES (L328) | ❌ **UNDERFLOW** | Unchecked get failure → put still called → refcount inconsistency. |
| **L326 (get fails) → L331** | goto err | NO | YES | ❌ **UNDERFLOW** | Same as above, extra put on error path. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_sync()` return value is not checked, and `pm_runtime_put_sync()` is called unconditionally. When get fails (returns <0), the usage count is not incremented, but the put decrements it, causing an inconsistent (underflowed) refcount on `power.usage_count.counter`.
```
