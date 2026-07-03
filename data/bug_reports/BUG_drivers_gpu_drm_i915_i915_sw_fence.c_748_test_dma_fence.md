# REAL BUG: drivers/gpu/drm/i915/i915_sw_fence.c:748 test_dma_fence()

**Confidence**: HIGH | **Counter**: `dma->refcount.refcount.refs.counter`

## Reasoning

| L728 | success return 0 (skip path) | YES (both wraps) | NO (free_fence * 2, dma_fence_put once) | ❌ LEAK | 2 extra refs leaked |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L675 | error return -ENOMEM | NO (alloc_dma_fence failed) | N/A | ✅ | No ref taken |
| L680 | goto err (IS_ERR(timeout)) | NO (wrap_dma_fence failed) | YES (dma_fence_put unreleased initial ref in err) | ✅ | timeout wrap never succeeded, only the initial alloc ref exists, put at err |
| L685 | goto err (IS_ERR(not)) | YES (timeout wrap succeeded, took ref on dma) | NO (free_fence(timeout) likely does NOT release dma ref; err label’s dma_fence_put only puts initial ref) | ❌ LEAK | Extra ref from timeout wrap never released |
| L691 | goto err (i915_sw_fence_done early) | YES (both wraps succeeded) | NO (explicit dma_fence_put only puts initial ref; free_fence calls do not release wrap refs) | ❌ LEAK | 2 extra refs leaked |
| L702 | goto skip (time_after) | YES (both wraps) | NO (skip path: free_fence * 2, dma_fence_put once, no put of wrap refs) | ❌ LEAK | 2 extra refs leaked |
| L706 | goto err (early signal again) | YES (both wraps) | NO (same as L691) | ❌ LEAK | 2 extra refs leaked |
| L712 | goto err (wait_event_timeout failed) | YES (both wraps) | NO (same) | ❌ LEAK | 2 extra refs leaked |
| L718 | goto err (not signaled) | YES (both wraps) | NO (same) | ❌ LEAK | 2 extra refs leaked |
| L728 | success return 0 (skip path) | YES (both wraps) | NO (free_fence * 2, dma_fence_put once) | ❌ LEAK | 2 extra refs leaked |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
wrap_dma_fence is a GET that increments dma’s refcount, but the only explicit dma_fence_put releases the initial alloc reference. free_fence (likely a plain sw fence free) does not call dma_fence_put, leaving every successful wrap reference leaked on all error and success paths.
```
