# REAL BUG: drivers/gpu/drm/msm/disp/dpu1/dpu_kms.c:97 _dpu_danger_signal_status()

**Confidence**: HIGH | **Counter**: `kms->pdev->dev.power.usage_count.counter`

## Reasoning

| L105 (get failure) | success | NO (returned <0, no inc) | YES (L95) | ❌ EXCESS PUT | get failed, put called unconditionally |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L70  | error (early) | NO (before get) | N/A  | ✅ | no get, no put needed |
| L105 (get success) | success | YES (counter inc) | YES (L95) | ✅ | pm_runtime_get_sync returned ≥0 |
| L105 (get failure) | success | NO (returned <0, no inc) | YES (L95) | ❌ EXCESS PUT | get failed, put called unconditionally |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
pm_runtime_get_sync's return value is not checked; failure (<0) does not increment usage_count, yet pm_runtime_put_sync is always called, causing an excess put.
```
