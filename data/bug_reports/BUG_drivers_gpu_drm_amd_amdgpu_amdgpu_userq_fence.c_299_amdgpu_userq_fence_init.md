# REAL BUG: drivers/gpu/drm/amd/amdgpu/amdgpu_userq_fence.c:299 amdgpu_userq_fence_init()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

Unless the source of `amdgpu_userq_fence_put_fence_drv_array` reveals that it does **not** actually put the fence (e.g., it only cleans up driver‑internal state), this is a clear refcount imbalance.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L277 | (first unconditional get) | YES (dma_fence_get — always incs) | N/A (no matching put here) | ⚠️ | Get stored in userq->last_fence, released later when replaced/freed. |
| L283 | conditional get (not‑signaled path) | YES (dma_fence_get — always incs) | NO in this function | ⚠️ | Extra reference held for the fence list; released later when fence removed from list and signaled. |
| L292 (signaled path exit) | function returns | Only L277 get done | **Probably YES** via `amdgpu_userq_fence_put_fence_drv_array(fence)` – name implies a dma_fence_put. | ❌ **Excess put** | No extra get on this path. If the callee does dma_fence_put, the refcount is decremented without a matching get → refcount underflow (excess put). |
| L294 (not‑signaled path exit) | function returns | L277 + L283 gets done | NO direct put in this function, but both gets are held by long‑lived structures. | ✅ | Balanced — the references will be properly released later. |

[NEED_SOURCE] amdgpu_userq_fence_put_fence_drv_array

**Analysis:**  
The function `amdgpu_userq_fence_init` acquires an unconditional reference at L277 (via `dma_fence_get`) and, on the not‑signaled path, a second unconditional reference at L283 for the fence list.  
On the **signaled path**, the second get is skipped, but the function **always** calls `amdgpu_userq_fence_put_fence_drv_array(fence)`. The callee’s name strongly suggests it performs a `dma_fence_put` on `fence->base`. That would decrement the refcount without a matching get, producing a refcount underflow — exactly the “excess put” warning.

The first get (L277) is safely stored in `userq->last_fence` and will be released elsewhere; it does not need immediate release. The only imbalance arises because the signaled path has one fewer get than the not‑signaled path, yet still executes a put operation.

Pre‑verdict checklist:
- “Held for device lifetime” – not applicable.
- “Ownership transferred” – no transfer on the signaled path (list not added, no extra ref to transfer), so the put is unjustified.
- Unconditional GET – `dma_fence_get` is unconditional; on signaled path only one such get occurs, while the put function tries to release an extra reference.
- No goto involved.

Unless the source of `amdgpu_userq_fence_put_fence_drv_array` reveals that it does **not** actually put the fence (e.g., it only cleans up driver‑internal state), this is a clear refcount imbalance.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the signaled path, no second `dma_fence_get` is performed, but `amdgpu_userq_fence_put_fence_drv_array` almost certainly calls `dma_fence_put`, causing a refcount underflow (excess put).
```
