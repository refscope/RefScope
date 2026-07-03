# REAL BUG: drivers/accel/rocket/rocket_job.c:589 rocket_ioctl_submit_job()

**Confidence**: HIGH | **Counter**: `rjob->refcount.refcount.refs.counter`

## Reasoning

| Success path (ret=0 after push) | fallthrough out_cleanup_job (no-op) → out_put_job → L589 | YES (kref_init + push) | YES (rocket_job_put) | ✅ | Initial ref dropped; push refs remain owned by scheduler (will be put later). |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L542 | early return -EINVAL | NO (before kref_init) | N/A | ✅ | No ref held |
| L546 | return -ENOMEM | NO (before kref_init) | N/A | ✅ | No ref held |
| L554 (via goto out_put_job) | drm_sched_job_init error → goto out_put_job → return ret at L589 | YES (kref_init at L548) | YES (rocket_job_put at L587, out_put_job) | ✅ | Only initial ref, one put → freed |
| L559 (via out_cleanup_job) | rocket_copy_tasks error → out_cleanup_job → out_put_job → L589 return | YES (kref_init) | YES (rocket_job_put) | ✅ | Only initial ref |
| L563 (via out_cleanup_job) | drm_gem_objects_lookup (in_bos) error → out_cleanup_job → out_put_job → L589 | YES (kref_init) | YES (rocket_job_put) | ✅ | Only initial ref |
| L570 (via out_cleanup_job) | drm_gem_objects_lookup (out_bos) error → out_cleanup_job → out_put_job → L589 | YES (kref_init) | YES (rocket_job_put) | ✅ | Only initial ref |
| L580 (push failure) via out_cleanup_job → out_put_job → L589 | rocket_job_push error → cleanup → put → return | **YES (kref_init + unconditional kref_get from rocket_job_push)** | YES (one rocket_job_put) | **❌ LEAK** | After push, refcount ≥ initial+1. One put leaves refcount > 0, object never freed. |
| Success path (ret=0 after push) | fallthrough out_cleanup_job (no-op) → out_put_job → L589 | YES (kref_init + push) | YES (rocket_job_put) | ✅ | Initial ref dropped; push refs remain owned by scheduler (will be put later). |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`rocket_job_push` is an unconditional GET, so it always increases rjob’s refcount. On the error path (line 580), only one `rocket_job_put` is called, leaving the extra reference from `kref_get` un-dropped, causing a refcount leak. The success path is fine because the extra refs are intentionally transferred to the scheduler.
```
