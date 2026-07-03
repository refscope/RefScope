# REAL BUG: drivers/gpu/drm/xe/xe_tlb_inval_job.c:152 xe_tlb_inval_job_create()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L~142 (err_fence → err_job) | error (drm_sched_job_init fail) | YES | NO | ❌ LEAK | same leak, falls through to err_job |

## Full Response

```
```
| Line | Return Type | GET Done? (job->refcount) | PUT Done? (kref_put) | Balanced? | Notes |
|------|-------------|---------------------------|----------------------|-----------|-------|
| L~110 | error | NO (before kref_init) | N/A | ✅ | job allocation failed, no ref held |
| L~132 (err_job) | error (goto err_job after fence alloc fail) | YES (kref_init at L~120) | NO (kfree without kref_put) | ❌ LEAK | initial ref not released via kref_put |
| L~142 (err_fence → err_job) | error (drm_sched_job_init fail) | YES | NO | ❌ LEAK | same leak, falls through to err_job |
| L~150 | success | YES (transferred) | YES (pair with destroy) | ✅ | cleanup via xe_tlb_inval_job_destroy |

**VERDICT: REAL_BUG**
**CONFIDENCE: HIGH**

`kref_init(&job->refcount)` creates an initial reference. Both error paths (`err_job` and `err_fence→err_job`) abandon the job without calling `kref_put`, directly freeing it with `kfree(job)`. Lesson 6 explicitly requires `kref_put` on error paths after `kref_init` when the object is not returned or stored for later cleanup, making this a refcount leak.
```
