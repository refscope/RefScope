# REAL BUG: drivers/gpu/drm/msm/disp/dpu1/dpu_plane.c:1776 dpu_plane_danger_signal_ctrl()

**Confidence**: HIGH | **Counter**: `dpu_kms->pdev->dev.power.usage_count.counter`

## Reasoning

| L1777 (implicit, end of function) | normal path (get return unchecked) | ⚠️ conditional (YES if success, NO if error) | YES (unconditional) | ❌ **Excess put if get error** | `pm_runtime_get_sync` return ignored; `pm_runtime_put_sync` at L1776 always runs |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1765 | early return (`!is_rt_pipe`) | NO (get not called) | N/A | ✅ | before get |
| L1777 (implicit, end of function) | normal path (get return unchecked) | ⚠️ conditional (YES if success, NO if error) | YES (unconditional) | ❌ **Excess put if get error** | `pm_runtime_get_sync` return ignored; `pm_runtime_put_sync` at L1776 always runs |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_sync()` return value is not checked; if it fails (returns <0), the counter is not incremented, but the unconditional `pm_runtime_put_sync()` at L1776 causes an excess put (count underflow).
```
