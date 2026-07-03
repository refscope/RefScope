# REAL BUG: drivers/gpu/drm/amd/amdgpu/amdgpu_eviction_fence.c:158 amdgpu_evf_mgr_detach_fence()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

7 (implicit) | void return | YES (via `dma_fence_get_stub()` L153) | YES (via `dma_fence_put(stub)` L157) | NO (excess put) | `dma_resv_replace_fences()` consumes the fence’s reference, so the subsequent `dma_fence_put` is an extra decrement that causes the refcount underflow reported by smatch. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L157 (implicit) | void return | YES (via `dma_fence_get_stub()` L153) | YES (via `dma_fence_put(stub)` L157) | NO (excess put) | `dma_resv_replace_fences()` consumes the fence’s reference, so the subsequent `dma_fence_put` is an extra decrement that causes the refcount underflow reported by smatch. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`dma_resv_replace_fences()` takes ownership of the stub fence, making the caller’s `dma_fence_put(stub)` an excess put.
```
