# REAL BUG: drivers/accel/amdxdna/amdxdna_pci_drv.c:334 amdxdna_probe()

**Confidence**: HIGH | **Counter**: `$->group->devices_kobj.kref.refcount.refs.counter`

## Reasoning

> *The `iommu_fini` path appears to call the cleanup function, but the contract suggests it does not release the `iommu_group` reference (no `iommu_group_put`). The most definite leak is at L294, where the cleanup is completely omitted.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L275 | error (IS_ERR) | NO (before get) | N/A | ✅ | |
| L279 | error (!dev_info) | NO (before get) | N/A | ✅ | |
| L294 | error (`return ret` after `amdxdna_iommu_init` failure) | **YES** | **NO** | ❌ LEAK | `amdxdna_iommu_init` contract says unconditional get; error return without `iommu_fini` → ref not released. |
| L322 | success (`return 0`) | YES | NO | **⚠️ device-lifetime** | Reference held for device lifetime; release in remove callback expected. |
| L299→L332-L334 | error (workqueue alloc fail) | YES | YES (via `iommu_fini`) | ✅/❌* | `amdxdna_iommu_fini` called — but contract shows it only calls `iova_cache_put`, **not** `iommu_group_put` → may still leak the `devices_kobj` ref if not released by fini. |
| L307→L330-L334 | error (ops->init fail) | YES | YES (via `iommu_fini`) | ✅/❌* | same as above |
| L313→L326-L334 | error (sysfs_init fail) | YES | YES (via `iommu_fini`) | ✅/❌* | same as above |
| L319→L324-L334 | error (drm register fail) | YES | YES (via `iommu_fini`) | ✅/❌* | same as above |

> *The `iommu_fini` path appears to call the cleanup function, but the contract suggests it does not release the `iommu_group` reference (no `iommu_group_put`). The most definite leak is at L294, where the cleanup is completely omitted.

**VERDICT: REAL_BUG**
**CONFIDENCE: HIGH**
`amdxdna_iommu_init()` unconditionally acquires a refcount (via `iommu_group_get`), but on error return the probe function returns immediately without calling `amdxdna_iommu_fini()`, leaking the reference on `devices_kobj`. The other error paths through the `iommu_fini` label may also leak if the fini function does not release the group reference, compounding the issue.
```
