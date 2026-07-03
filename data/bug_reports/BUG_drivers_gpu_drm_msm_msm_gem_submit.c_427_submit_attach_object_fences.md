# REAL BUG: drivers/gpu/drm/msm/msm_gem_submit.c:427 submit_attach_object_fences()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L437 | implicit return (non-vmbind) | NO | NO | ✅ | no fence ops |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L424 | return (vmbind) | NO (no new get for last_fence) | YES (implicit put by dma_fence_unwrap_merge per contract + explicit dma_fence_put) | ❌ EXCESS PUT | double put on last_fence |
| L437 | implicit return (non-vmbind) | NO | NO | ✅ | no fence ops |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
dma_fence_unwrap_merge() contract states it does dma_fence_put on its input fences, yet submit_attach_object_fences() also calls dma_fence_put(last_fence) after the merge, resulting in a double put (excess put) on vm->last_fence.
```
