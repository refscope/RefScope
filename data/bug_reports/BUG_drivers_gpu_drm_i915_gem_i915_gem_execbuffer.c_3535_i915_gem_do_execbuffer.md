# REAL BUG: drivers/gpu/drm/i915/gem/i915_gem_execbuffer.c:3535 i915_gem_do_execbuffer()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L3521 | final return err (all paths) | – | – | – | balance already accounted per-path |

## Full Response

```
| Line (approx) | Return Type | GET Done? (fence acquired) | PUT Done? (explicit dma_fence_put) | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3388 | return -ENODEV (secure GRAPHICS_VER>=11) | NO | NO | ✅ | Early return, no fence ops |
| L3392 | return -EPERM (secure no batches) | NO | NO | ✅ | |
| L3395 | return -EPERM (secure !master/!capable) | NO | NO | ✅ | |
| L3402 | goto err_ext (parse_extensions err) | NO (composite_fence not set) | NO | ✅ | |
| L3405 | goto err_ext (add_fence_array err) | NO | NO | ✅ | |
| L3410 | return -EINVAL (IN_FENCES both flags) | NO | NO | ✅ | |
| L3416 | goto err_ext (in_fence NULL) | NO | NO | ✅ | |
| L3424 | goto err_in_fence (out_fence_fd<0) | NO (composite_fence not yet) | NO | ✅ | in_fence handled elsewhere |
| L3429 | goto err_out_fence (eb_create err) | NO | NO | ✅ | |
| L3434 | goto err_destroy (context err) | NO | NO | ✅ | |
| L3437 | goto err_context (engine err) | NO | NO | ✅ | |
| L3442 | goto err_engine (lookup vmas err) | NO | NO | ✅ | |
| L3453 | goto err_vma (relocate_parse err) | NO | NO | ✅ | |
| L3458 | goto err_vma (capture_stage err) | NO | NO | ✅ | |
| L3466 (if requests[0]==NULL) | goto err_vma (eb_requests_create error) | YES (composite_fence set by create) | NO | ❌ (potential leak, but not excess put) | composite_fence not released |
| **L3465 (if requests[0]!=NULL)** | **goto err_request → err_vma** | **YES (composite_fence set)** | **YES (dma_fence_put at L~3498)** | **❌ EXCESS PUT** | **drm_syncobj_replace_fence consumed the ref, later dma_fence_put double-puts** |
| Success (L~3470→err_request) | fall-through, out_fence non-NULL | YES | NO (skipped, out_fence present) | ✅ | composite_fence owned by out_fence/sync_file, no extra put |
| L3521 | final return err (all paths) | – | – | – | balance already accounted per-path |

**🔴 PRE-VERDICT CHECKLIST**
1. **"Held for device lifetime"?** Not applicable (fence, not device).
2. **"Ownership transferred"?** `drm_syncobj_replace_fence` takes ownership of the fence pointer passed to it. On the error path where `out_fence` is NULL and `eb.composite_fence` is non-NULL, the reference is transferred to the syncobj, yet the code later calls `dma_fence_put(eb.composite_fence)` — an extra put. Confirmed excess.
3. **Unconditional GET?** The GET (acquisition of `composite_fence`'s reference) occurs before the `drm_syncobj_replace_fence` call; that GET is later implicitly released by the replace function. The explicit `dma_fence_put` adds a second release.
4. **goto out between GET and PUT?** The path `goto err_request` leads to the `drm_syncobj_replace_fence` (transfer), then the explicit `dma_fence_put`. The label chain does not avoid the put, creating the excess.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the `eb_requests_create` error path with a non-NULL `eb.requests[0]`, `drm_syncobj_replace_fence` takes ownership of `eb.composite_fence`, yet the subsequent `dma_fence_put(eb.composite_fence)` is still exe
```
