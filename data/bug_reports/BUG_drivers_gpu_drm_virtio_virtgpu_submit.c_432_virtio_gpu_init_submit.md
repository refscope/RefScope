# REAL BUG: drivers/gpu/drm/virtio/virtgpu_submit.c:432 virtio_gpu_init_submit()

**Confidence**: HIGH | **Counter**: `out_fence->f.refcount.refcount.refs.counter`

## Reasoning

L432 is the line flagged by smatch. Each of the ❌ lines returns without `dma_fence_put`, leaking the reference acquired by `virtio_gpu_fence_alloc`. Only the fence‑event error path correctly releases the fence.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L399 | error       | YES (from virtio_gpu_fence_alloc) | YES (dma_fence_put) | ✅ | Fence event creation failed, put called |
| ~L411 | error (goto out?) | YES | NO  | ❌ LEAK | buflist init fails, no put |
| ~L416 | error       | YES | NO  | ❌ LEAK | vmemdup_user fails, no put |
| ~L426 | error       | YES | NO  | ❌ LEAK | get_unused_fd_flags fails, no put |
| **L432** | error       | YES | NO  | ❌ LEAK | sync_file_create fails, no put |
| ~L434 | success     | YES | NO (transferred) | ✅ | Ownership transferred to submit struct; will be released in cleanup |

L432 is the line flagged by smatch. Each of the ❌ lines returns without `dma_fence_put`, leaking the reference acquired by `virtio_gpu_fence_alloc`. Only the fence‑event error path correctly releases the fence.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Multiple early‑return error paths after allocating `out_fence` fail to release it with `dma_fence_put`, including the flagged line 432.
```
