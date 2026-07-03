# REAL BUG: drivers/gpu/drm/msm/dsi/dsi_host.c:2635 msm_dsi_host_snapshot()

**Confidence**: HIGH | **Counter**: `msm_host->pdev->dev.power.usage_count.counter`

## Reasoning

ret < 0) – **return value not checked** | YES (pm_runtime_put_sync at L2635) | No – if the GET failed, put runs without a previous increment → refcount excess put | Missing error check on pm_runtime_get_sync means unconditional put can decrement an already-decremented counter, causing underflow. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2636 (end of function) | void return | Conditional: yes if pm_runtime_get_sync succeeded (ret >= 0), no if it failed (ret < 0) – **return value not checked** | YES (pm_runtime_put_sync at L2635) | No – if the GET failed, put runs without a previous increment → refcount excess put | Missing error check on pm_runtime_get_sync means unconditional put can decrement an already-decremented counter, causing underflow. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_sync` return value not checked; on failure, the refcount is not incremented, but `pm_runtime_put_sync` still runs at line 2635, causing an excess put.
```
