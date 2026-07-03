# REAL BUG: drivers/gpu/drm/amd/amdgpu/amdgpu_userq_fence.c:902 amdgpu_userq_wait_return_fence_info()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

sfer is **not** assumed.

**Additional note:** The `dma_resv_for_each_fence()` loops (L784–806) also take fence references that are never dropped, but the primary warning points at the fence_drv kref.

## Full Response

```
| Line | Return Type | GET Done? (fence_drv) | PUT Done? (fence_drv) | Balanced? | Notes |
|------|-------------|-----------------------|-----------------------|-----------|-------|
| L725 | error return | NO (before loop) | N/A | ✅ | Early -ENOMEM |
| L730 | goto free_fence_info | NO | N/A | ✅ | Early allocation failure |
| L740 | goto free_fences | NO | N/A | ✅ | drm_syncobj_find_fence error |
| L746 | goto free_fences | NO | N/A | ✅ | amdgpu_userq_wait_add_fence error |
| L759 | goto free_fences | NO | N/A | ✅ | drm_syncobj_find_fence error (bool) |
| L764 | goto free_fences | NO | N/A | ✅ | amdgpu_userq_wait_add_fence error (bool) |
| L776 | goto error_unlock | NO | N/A | ✅ | drm_exec_prepare_array error |
| L781 | goto error_unlock | NO | N/A | ✅ | drm_exec_prepare_array error |
| L792 | goto error_unlock | NO | N/A | ✅ | No fence_drv get yet (though fence from resv iterator leaked separately) |
| L804 | goto error_unlock | NO | N/A | ✅ | Same |
| L816 | goto free_fences | NO | N/A | ✅ | waitq NULL, loop not entered |
| L831 | goto put_waitq | YES (previous iterations) | NO | ❌ LEAK | `dma_fence_wait` failure after one or more successful get+store; earlier fence_drv refs never put |
| L848 | goto put_waitq | YES (previous iterations) | NO | ❌ LEAK | `xa_alloc` failure after earlier gets; earlier refs leaked |
| L864 → L868 → L871 → L878 | success/error return | YES (all iterations) | NO | ❌ LEAK | All `amdgpu_userq_fence_driver_get` refs are never released before return |
| L880 → L882 → L871 → L878 | error_unlock path (after resv loops) | YES (if any prior gets) | NO | ❌ LEAK | All fence_drv refs leaked on early exit |

**Why it’s a leak:** `amdgpu_userq_fence_driver_get()` (line 850) unconditionally increments the kref on `fence_drv`. The function never calls a matching `amdgpu_userq_fence_driver_put()` anywhere. Every return path that ever executes that get therefore leaks the reference. The comment about the waitq releasing the reference is an **unproven cross‑function cleanup**; no pointer to actual release code is provided, so under the strict audit rules ownership transfer is **not** assumed.

**Additional note:** The `dma_resv_for_each_fence()` loops (L784–806) also take fence references that are never dropped, but the primary warning points at the fence_drv kref.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Unconditional `amdgpu_userq_fence_driver_get` at L850, no corresponding put on any path; all returns after the loop leak the kref.
```
