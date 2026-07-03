# REAL BUG: drivers/iommu/arm/arm-smmu/qcom_iommu.c:359 qcom_iommu_domain_free()

**Confidence**: HIGH | **Counter**: `qcom_domain->iommu->dev->power.usage_count.counter`

## Reasoning

| L360 | void return (after iommu non‑NULL path) | COND (YES if pm_runtime_get_sync() ≥0; NO if <0) | YES (unconditional) | ❌ excess put when get fails | return value of pm_runtime_get_sync() not checked, pm_runtime_put_sync() always executed |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L360 | void return (after iommu non‑NULL path) | COND (YES if pm_runtime_get_sync() ≥0; NO if <0) | YES (unconditional) | ❌ excess put when get fails | return value of pm_runtime_get_sync() not checked, pm_runtime_put_sync() always executed |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_sync()` at L354 can fail (return <0 without increment), but the code unconditionally calls `pm_runtime_put_sync()` at L356, causing a refcount underflow on the error path.
```
