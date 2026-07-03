# REAL BUG: drivers/gpu/drm/xe/xe_gt.c:197 emit_job_sync()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

There is no explicit `xe_sched_job_put()` anywhere in the function. `xe_sched_job_push()` may schedule the job but does not consume the caller's reference; the job's lifecycle is not tied to the fence wait. All paths after successful job creation (excluding IS_ERR) leave a dangling job reference.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (job ref) | PUT Done? (job put) | Balanced? | Notes |
|------|-------------|---------------------|---------------------|-----------|-------|
| L182 | error (IS_ERR) | NO | N/A | ✅ | job creation failed, no reference held |
| L193 | error (timeout < 0) | YES | NO | ❌ LEAK | job created successfully; fence released but job not released |
| L195 | error (timeout == 0) | YES | NO | ❌ LEAK | same as L193 |
| L197 | success (0) | YES | NO | ❌ LEAK | job completed but its reference never dropped |

**GET context**: `xe_bb_create_job()` returns a new job with an initial kref. There is no explicit `xe_sched_job_put()` anywhere in the function. `xe_sched_job_push()` may schedule the job but does not consume the caller's reference; the job's lifecycle is not tied to the fence wait. All paths after successful job creation (excluding IS_ERR) leave a dangling job reference.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Job created via `xe_bb_create_job` is never released—no `xe_sched_job_put` call on any post‑creation path, leaking the initial kref.
```
