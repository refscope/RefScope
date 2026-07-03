# REAL BUG: drivers/gpu/drm/vc4/vc4_gem.c:666 vc4_queue_submit()

**Confidence**: LOW | **Counter**: `$->fence->refcount.refcount.refs.counter`

## Reasoning

ference, it is a refcounting bug. Smatch’s detection aligns with this interpretation. Without the source, I cannot definitively rule out a false positive (e.g., a correct put in an error path that happens to hit a zero refcount), but the most likely scenario is a real leak‑in‑reverse (excess put).

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L628 | error (-ENOMEM) | NO (before fence init) | N/A  | ✅ | fence=NULL, no init, no ref |
| L660 | success (return 0) | YES (dma_fence_init sets refcount=1; drm_syncobj_replace_fence takes ref on new fence; vc4_attach_fences may also take refs) | NO explicit put in this function | ⚠️  | This function does not put the fence; the excess put occurs outside, at line 666. The fence refcount is managed by later cleanup (syncobj, job completion, etc.) so the function itself is not the source of the excess put. |

The warning “refcount excess put” points to line 666 in the same file, which is not part of `vc4_queue_submit()` and must be inside a callee (likely `vc4_attach_fences` or some error handling). I need to see that exact code and the internals of `vc4_attach_fences` to determine whether the extra `dma_fence_put` is a reverse‑edge bug.

[NEED_SOURCE] drivers/gpu/drm/vc4/vc4_gem.c:660-670
[NEED_SOURCE] vc4_attach_fences

Given the contracts:
- **GET**: `vc4_attach_fences` semantics unknown → it could legitimately increment the fence refcount, but it might also contain a put that shouldn’t be there.
- **PUT**: `drm_syncobj_replace_fence` does `dma_fence_put` only on the **old** syncobj fence, not on the new one.

Because the excess put is on the newly‑created fence (the one from `dma_fence_init`), it is almost certainly inside `vc4_attach_fences` (or in an error path reachable from that call). If that function is supposed to *take* a reference (as its name suggests) but instead incorrectly releases a reference, it is a refcounting bug. Smatch’s detection aligns with this interpretation. Without the source, I cannot definitively rule out a false positive (e.g., a correct put in an error path that happens to hit a zero refcount), but the most likely scenario is a real leak‑in‑reverse (excess put).

VERDICT: REAL_BUG
CONFIDENCE: LOW
`vc4_attach_fences` (line 644) apparently calls `dma_fence_put` on the new fence at line 666, violating expected get/put balance; exact confirmation requires the omitted source.
```
