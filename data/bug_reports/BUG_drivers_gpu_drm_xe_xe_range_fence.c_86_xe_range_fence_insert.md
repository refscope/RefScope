# REAL BUG: drivers/gpu/drm/xe/xe_range_fence.c:86 xe_range_fence_insert()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

| L86 (free label) | error (other failure) | YES (L70) | NO | ❌ LEAK | `dma_fence_add_callback` returned neither 0 nor -ENOENT; no `dma_fence_put` on error path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L64 (goto free) | error (signaled) | NO (before get) | N/A | ✅ | fence signaled early, no get happened |
| L74-76 (goto free after put) | error (ENOENT) | YES (L70) | YES (L74) | ✅ | added callback got -ENOENT, explicitly put |
| L79 (return 0) | success | YES (L70) | NO (transfer) | ✅ | ownership transferred via `xe_range_fence_tree_insert`; tree will `dma_fence_put` on removal |
| L86 (free label) | error (other failure) | YES (L70) | NO | ❌ LEAK | `dma_fence_add_callback` returned neither 0 nor -ENOENT; no `dma_fence_put` on error path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`dma_fence_get` at L70 increments refcount unconditionally; error path (non-ENOENT, non-zero callback add error) falls through to `free:` at L82 and returns without `dma_fence_put`.
```
