# REAL BUG: drivers/iommu/iommufd/viommu.c:110 iommufd_viommu_alloc_ioctl()

**Confidence**: HIGH | **Counter**: `hwpt_paging->common.obj.users.refs.counter`

## Reasoning

- The success path (fall‑through to `out_put_hwpt`) intentionally keeps the extra reference; it will be dropped later when `viommu` is destroyed by the core IOMMUFD object management. This is acceptable, but the error paths lack that deferred cleanup.

## Full Response

```
## Path Table

I'll enumerate every return path in `iommufd_viommu_alloc_ioctl()` and check the state of the `hwpt_paging->common.obj.users.refs.counter`.  The warning involves two increments on the same counter:

1. `iommufd_get_hwpt_paging()` (line 55) – **conditional GET** (succeeds on non‑IS_ERR, increments counter).
2. `refcount_inc(&viommu->hwpt->common.obj.users)` (line 76) – **explicit increment** for ownership held by `viommu->hwpt`.

The only decrement for this counter is `iommufd_put_object()`, called once at label `out_put_hwpt` (line 96).

| Line   | Return Type           | iommufd_get_hwpt_paging? | refcount_inc? | hwpt_paging put? | Balanced? | Notes |
|--------|-----------------------|--------------------------|---------------|------------------|-----------|-------|
| L30–31 | error `-EOPNOTSUPP`   | NO (before GET)          | NO            | N/A              | ✅ | no ref taken |
| L34–35 | error `PTR_ERR(idev)` | NO                       | NO            | N/A              | ✅ | no ref taken |
| L40    | `goto out_put_idev`   | NO                       | NO            | NO               | ✅ | no ref taken |
| L46    | `goto out_put_idev`   | NO                       | NO            | NO               | ✅ | no ref taken |
| L52    | `goto out_put_idev`   | NO                       | NO            | NO               | ✅ | no ref taken |
| L58    | `goto out_put_idev`   | NO (GET failed, IS_ERR)  | NO            | NO               | ✅ | error, no ref held |
| L63    | `goto out_put_hwpt`   | **YES**                  | NO            | **YES** (L96)    | ✅ | single ref acquired & released |
| L69    | `goto out_put_hwpt`   | **YES**                  | NO            | **YES** (L96)    | ✅ | single ref acquired & released |
| L84    | `goto out_put_hwpt`   | **YES**                  | **YES**       | **only one put** | ❌ LEAK | `viommu_init` failure after `refcount_inc` → extra ref never released |
| L89    | `goto out_put_hwpt`   | **YES**                  | **YES**       | **only one put** | ❌ LEAK | `WARN_ON(!viommu->ops)` after `refcount_inc` → extra ref never released |
| L93‑94 | success (falls to L96)| **YES**                  | **YES**       | **only one put** | (intentional) | extra ref will be released when `viommu` is destroyed later; okay for success path |

**Explanation of the imbalance:**

- `iommufd_get_hwpt_paging()` acquires one reference (refcount = 1).
- `refcount_inc()` at line 76 adds a second reference, intended for the long‑term ownership by `viommu->hwpt`.
- The cleanup label `out_put_hwpt` performs **only one** `iommufd_put_object()`, which drops one reference.
- On the **error paths** at lines 84 and 89, the `viommu` object is **not** freed, and its held reference is never released. The net result is a refcount leak on `hwpt_paging->common.obj.users` – the counter ends up one higher than it should, and that reference can never be returned.
- The success path (fall‑through to `out_put_hwpt`) intentionally keeps 
```
