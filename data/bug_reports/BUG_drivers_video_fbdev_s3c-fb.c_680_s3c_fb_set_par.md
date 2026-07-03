# REAL BUG: drivers/video/fbdev/s3c-fb.c:680 s3c_fb_set_par()

**Confidence**: HIGH | **Counter**: `sfb->dev->power.usage_count.counter`

## Reasoning

c at L497 failed, return <0; counter NOT incremented per contract) | YES (pm_runtime_put_sync at L680) | ❌ EXCESS PUT | Return value of pm_runtime_get_sync is not checked. On failure the usage_count remains unchanged, yet the unconditional put decrements it → refcount goes negative (excess put). |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L680 → L681 | Always reached; return 0 after put | YES (if pm_runtime_get_sync at L497 succeeded, return ≥0) | YES (pm_runtime_put_sync at L680) | ✅ | Normal path |
| L680 → L681 | Always reached; return 0 after put | NO (if pm_runtime_get_sync at L497 failed, return <0; counter NOT incremented per contract) | YES (pm_runtime_put_sync at L680) | ❌ EXCESS PUT | Return value of pm_runtime_get_sync is not checked. On failure the usage_count remains unchanged, yet the unconditional put decrements it → refcount goes negative (excess put). |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
pm_runtime_get_sync return unchecked; on failure (ret < 0) the usage_count is not incremented, but pm_runtime_put_sync is still called, causing an excess put.
```
