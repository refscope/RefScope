# REAL BUG: drivers/gpu/drm/nouveau/nouveau_exec.c:287 nouveau_exec()

**Confidence**: HIGH | **Counter**: `$->done_fence->refcount.refcount.refs.counter`

## Reasoning

mit` unconditionally does `dma_fence_put` (contract); `nouveau_job_fini` unconditionally does another `dma_fence_put` → double put on the same fence |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L273 | error       | NO (before submit) | N/A  | ✅ | `nouveau_exec_job_init` failed, no submit, no fence ref |
| L277 | goto err_job_fini | NO (submit failed but already performed a put) | YES (via `nouveau_job_fini` at L282) | ❌ EXCESS PUT | `nouveau_job_submit` unconditionally does `dma_fence_put` (contract); `nouveau_job_fini` unconditionally does another `dma_fence_put` → double put on the same fence |
| L279 | success     | NO (in this function) | NO | ✅ | Submit succeeded; fence ref now owned by the job, will be released later (e.g., callback) |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`nouveau_job_submit` unconditionally puts a fence ref (per contract) and on error the code calls `nouveau_job_fini` which does another put, causing an excess put on `done_fence`.
```
