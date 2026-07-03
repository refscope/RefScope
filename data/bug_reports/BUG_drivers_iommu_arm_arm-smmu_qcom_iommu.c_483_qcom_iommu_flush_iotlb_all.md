# REAL BUG: drivers/iommu/arm/arm-smmu/qcom_iommu.c:483 qcom_iommu_flush_iotlb_all()

**Confidence**: HIGH | **Counter**: `qcom_domain->iommu->dev->power.usage_count.counter`

## Reasoning

| L484 | implicit return at end of function | Conditional (pm_runtime_get_sync called; inc’s only if return ≥ 0) | YES (pm_runtime_put_sync called unconditionally) | ❌ EXCESS PUT when get_sync fails | return value not checked → put runs even if get_sync did not increment the counter |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L477 | early return (void) | NO (before get) | NO  | ✅ | no refcount involvement |
| L484 | implicit return at end of function | Conditional (pm_runtime_get_sync called; inc’s only if return ≥ 0) | YES (pm_runtime_put_sync called unconditionally) | ❌ EXCESS PUT when get_sync fails | return value not checked → put runs even if get_sync did not increment the counter |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
pm_runtime_get_sync return is unchecked; on error it does not increment the usage count, but the unconditional pm_runtime_put_sync(L483) always decrements, causing a refcount underflow (excess put).
```
