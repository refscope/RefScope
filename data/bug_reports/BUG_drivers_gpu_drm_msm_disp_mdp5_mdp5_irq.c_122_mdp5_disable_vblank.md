# REAL BUG: drivers/gpu/drm/msm/disp/mdp5/mdp5_irq.c:122 mdp5_disable_vblank()

**Confidence**: HIGH | **Counter**: `dev->power.usage_count.counter`

## Reasoning

| L123 | implicit return (void) | NO (if `pm_runtime_get_sync` failed, no ref) / YES (if succeeded) | YES | ❌ NO (if get failed) | Return value not checked; `pm_runtime_put_sync` always called, causing excess put on error path. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L123 | implicit return (void) | NO (if `pm_runtime_get_sync` failed, no ref) / YES (if succeeded) | YES | ❌ NO (if get failed) | Return value not checked; `pm_runtime_put_sync` always called, causing excess put on error path. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_sync` return value ignored; function unconditionally calls `pm_runtime_put_sync` even if get failed and no reference was taken, leading to an excess put.
```
