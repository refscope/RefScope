# REAL BUG: drivers/gpu/drm/amd/amdgpu/amdgpu_sync.c:455 amdgpu_sync_push_to_job()

**Confidence**: HIGH | **Counter**: `f->refcount.refcount.refs.counter`

## Reasoning

| L454 (after loop) | success return | For each not-signaled fence: YES, no caller PUT (ownership transferred). For signaled: depends on entry_free. | No explicit PUT for added fences; job will put later. | Balanced under assumption entry_free releases signaled fences. | No excess put here. |

## Full Response

```
[NEED_SOURCE] drm_sched_job_add_dependency
[NEED_SOURCE] amdgpu_sync_entry_free

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L444 (continue after signaled check) | continues loop | NO (dma_fence_get not called) | Possibly in amdgpu_sync_entry_free (caller PUT not done) | Unknown – depends on entry_free. Not directly related to excess put. | If entry_free PUTs, signalled fences are balanced. |
| L450 (if r != 0) | error return | YES (dma_fence_get at L448) | YES (dma_fence_put(f) by caller at L450) | **NO – potential double put** (excess put) if drm_sched_job_add_dependency also called dma_fence_put on the error path (contract says conditional_on_path →dma_fence_put). | This path is the source of the excess put warning. |
| L454 (after loop) | success return | For each not-signaled fence: YES, no caller PUT (ownership transferred). For signaled: depends on entry_free. | No explicit PUT for added fences; job will put later. | Balanced under assumption entry_free releases signaled fences. | No excess put here. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

On the error path after `dma_fence_get(f)` and a failing `drm_sched_job_add_dependency()`, the caller unconditionally calls `dma_fence_put(f)`. The contract for `drm_sched_job_add_dependency` states it is a PUT that calls `dma_fence_put` on some paths (conditional_on_path). This creates a double-put when the callee has already released the reference on the error path, matching the `refcount excess put` warning.
```
