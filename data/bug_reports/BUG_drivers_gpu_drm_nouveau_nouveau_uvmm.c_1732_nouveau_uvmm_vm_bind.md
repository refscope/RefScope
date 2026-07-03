# REAL BUG: drivers/gpu/drm/nouveau/nouveau_uvmm.c:1732 nouveau_uvmm_vm_bind()

**Confidence**: HIGH | **Counter**: `$->done_fence->refcount.refcount.refs.counter`

## Reasoning

failed; internal get in `nouveau_job_submit` likely paired with internal put on error, so net refcount = 0) | YES (unconditional `dma_fence_put` in `nouveau_job_fini`) | ❌ **Excess put** | `nouveau_job_submit` error handling already released the done_fence; calling `nouveau_job_fini` double-puts |

## Full Response

```
| Line | Return Type | GET Done? (nouveau_job_submit) | PUT Done? (nouveau_job_fini) | Balanced? | Notes |
|------|-------------|--------------------------------|-----------------------------|-----------|-------|
| L1722 | error       | NO (before submit)            | N/A                         | ✅        | init failed, no fence refs involved |
| L1728 | success     | YES (submit succeeded, fence ref held by job) | NO (job owns ref, cleaned up later by scheduler) | ✅ | ref held until job completion |
| L1726+L1732 (err_job_fini) | error | YES (submit failed; internal get in `nouveau_job_submit` likely paired with internal put on error, so net refcount = 0) | YES (unconditional `dma_fence_put` in `nouveau_job_fini`) | ❌ **Excess put** | `nouveau_job_submit` error handling already released the done_fence; calling `nouveau_job_fini` double-puts |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`nouveau_job_submit` failure path (goto err_job_fini) calls `nouveau_job_fini` which does a `dma_fence_put` on the done_fence, but submit's error handling already balanced the fence get, causing a refcount underflow.
```
