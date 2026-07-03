# REAL BUG: drivers/iommu/arm/arm-smmu/qcom_iommu.c:470 qcom_iommu_unmap()

**Confidence**: HIGH | **Counter**: `qcom_domain->iommu->dev->power.usage_count.counter`

## Reasoning

ntime_get_sync` returned ≥0 (inc occurred); NO if <0 (no inc) | YES (unconditionally) | ❌ EXCESS PUT when GET failed | `pm_runtime_get_sync` return value not checked; on error (<0) no refcount increment, but `pm_runtime_put_sync` always called, causing underflow and “refcount excess put” at L470 |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L453 | early return (0) | NO (before `pm_runtime_get_sync`) | NO | ✅ | ops null, no runtime PM calls |
| L471 | return `ret` | Conditional: YES if `pm_runtime_get_sync` returned ≥0 (inc occurred); NO if <0 (no inc) | YES (unconditionally) | ❌ EXCESS PUT when GET failed | `pm_runtime_get_sync` return value not checked; on error (<0) no refcount increment, but `pm_runtime_put_sync` always called, causing underflow and “refcount excess put” at L470 |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_sync` can fail and not increment usage_count, but the code unconditionally calls `pm_runtime_put_sync` afterward, leading to an excess put when the get fails.
```
