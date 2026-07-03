# REAL BUG: drivers/iommu/iommufd/viommu.c:429 iommufd_hw_queue_alloc_ioctl()

**Confidence**: HIGH | **Counter**: `viommu->obj.users.refs.counter`

## Reasoning

| Success: `hw_queue_init_phys` rc=0 → `iommufd_ucmd_respond` → fall through to `out_put_viommu` | success | YES | YES (one put) | ✅ | Extra ref is carried by `hw_queue` object (ownership transferred) |

## Full Response

```
| Line | Return Type | GET (refcount_inc) Done? | PUT (iommufd_put_object) Done? | Balanced? | Notes |
|------|-------------|--------------------------|-------------------------------|-----------|-------|
| Early checks: flags, length, overflow → direct return | error | NO (before acquisition) | N/A | ✅ | No viommu reference held |
| `IS_ERR(viommu)` return | error | NO (get failed) | NO | ✅ | ERR_PTR means no reference taken |
| `!viommu->ops \|\| ...` goto `out_put_viommu` | error | NO (before inc) | YES | ✅ | Releases initial iommufd_get_viommu reference |
| `hw_queue_size == 0` goto `out_put_viommu` | error | NO | YES | ✅ | |
| `WARN_ON_ONCE` goto `out_put_viommu` | error | NO | YES | ✅ | |
| `IS_ERR(hw_queue)` goto `out_put_viommu` | error | NO | YES | ✅ | |
| `IS_ERR(access)` goto `out_put_viommu` | error | NO | YES | ✅ | |
| After `refcount_inc` → `hw_queue_init_phys` fails → goto `out_put_viommu` | error | YES (unconditional +1) | YES (only one put) | ❌ LEAK | refcount goes 1→2, put reduces to 1; extra reference from `refcount_inc` never released, and `hw_queue` object is leaked |
| Success: `hw_queue_init_phys` rc=0 → `iommufd_ucmd_respond` → fall through to `out_put_viommu` | success | YES | YES (one put) | ✅ | Extra ref is carried by `hw_queue` object (ownership transferred) |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Unconditional `refcount_inc` increments viommu refcount; error path via `goto out_put_viommu` after `hw_queue_init_phys` failure only calls `iommufd_put_object` once, leaving the extra reference leaked.
```
