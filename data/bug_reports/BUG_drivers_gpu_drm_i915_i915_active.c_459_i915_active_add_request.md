# REAL BUG: drivers/gpu/drm/i915/i915_active.c:459 i915_active_add_request()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| 456‑460 (old fence NULL) | success/error | YES (get on new) | N/A  | ✅ | no old fence to put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 433  | error       | NO (acquire failed, no fence ops) | N/A  | ✅ | |
| 442  | goto out    | NO (active is NULL, set not called) | N/A  | ✅ | no fence get/put |
| 456‑460 (non‑NULL old fence) | success/error | YES (__i915_active_fence_set unconditionally gets new fence) | YES (dma_fence_put on old fence) | ❌ EXCESS PUT if callee already put old fence | Contract states __i915_active_fence_set performs dma_fence_put on old fence, making the caller's dma_fence_put a double put |
| 456‑460 (old fence NULL) | success/error | YES (get on new) | N/A  | ✅ | no old fence to put |

[NEED_SOURCE] __i915_active_fence_set

VERDICT: REAL_BUG
CONFIDENCE: HIGH
__i915_active_fence_set is documented as unconditional GET that internally calls both i915_active_fence_get (get new) and dma_fence_put (put old). The caller then performs dma_fence_put on the returned old fence, causing a double decrement (excess put) on the old fence’s refcount.
```
