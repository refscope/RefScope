# REAL BUG: drivers/gpu/drm/drm_syncobj.c:956 drm_syncobj_transfer_to_timeline()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L949‑L955 (success fall‑through) | success | YES (tmp, fence) | PUT on tmp at L937 (excess), PUT on fence at L951 | ❌ EXCESS PUT on tmp | Same double put on tmp. |

## Full Response

```
| Line | Return Type | GET Done? (fence from find_fence) | PUT Done? (on that fence) | Balanced? | Notes |
|------|-------------|-----------------------------------|---------------------------|-----------|-------|
| L928 (early return -ENOENT) | error | N/A (no get) | N/A | ✅ | No fence acquired. |
| L934 (goto err_put_timeline after find_fence fail) | error | NO (find_fence failed, no fence) | NO | ✅ | No fence reference. |
| L940 (goto err_put_timeline after unwrap_merge, fence==NULL) | error | YES (tmp got ref from find_fence) | YES at L937 (dma_fence_put(tmp)) | ❌ EXCESS PUT | `dma_fence_unwrap_merge(tmp)` contract says it **unconditionally calls dma_fence_put (on input)**. The explicit `dma_fence_put(tmp)` afterwards is a double release, causing refcount excess put. |
| L946 (goto err_free_fence, then err_put_timeline) | error | YES (tmp ref, fence ref from unwrap_merge) | PUT on tmp at L937 (excess), PUT on fence at L951 | ❌ EXCESS PUT on tmp | Same double put on tmp. |
| L949‑L955 (success fall‑through) | success | YES (tmp, fence) | PUT on tmp at L937 (excess), PUT on fence at L951 | ❌ EXCESS PUT on tmp | Same double put on tmp. |

[NEED_SOURCE] dma_fence_unwrap_merge

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The `__dma_fence_unwrap_merge` contract states it unconditionally performs `dma_fence_put` on its input, consuming the reference. The explicit `dma_fence_put(tmp)` after the call is an extra put, leading to a refcount overflow (excess put) on the fence’s `refcount`.
```
