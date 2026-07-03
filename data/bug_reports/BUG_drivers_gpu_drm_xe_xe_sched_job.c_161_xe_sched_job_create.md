# REAL BUG: drivers/gpu/drm/xe/xe_sched_job.c:161 xe_sched_job_create()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L159 (return job) | success | YES | NO (caller will later call kref_put) | ✅ | ownership transferred to caller |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L110 | error (job_alloc fail) | NO (before kref_init) | N/A  | ✅ | no ref held |
| L120 (goto err_free) | error (drm_sched_job_init fail) | YES (kref_init at L114) | NO (job_free without kref_put) | ❌ LEAK | initial ref never released via kref_put |
| L135 (IS_ERR(fence) → goto err_sched_job → err_free) | error | YES | NO | ❌ LEAK | same, job_free without kref_put |
| L142 (chain alloc fail → goto err_sched_job → err_free) | error | YES | NO | ❌ LEAK | same |
| L159 (return job) | success | YES | NO (caller will later call kref_put) | ✅ | ownership transferred to caller |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
kref_init creates an initial reference that must be released with kref_put; all three error paths after kref_init call job_free directly, skipping the expected kref_put release and violating the standard refcount lifecycle.
```
