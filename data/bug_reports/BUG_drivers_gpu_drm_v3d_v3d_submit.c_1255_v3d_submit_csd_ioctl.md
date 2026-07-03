# REAL BUG: drivers/gpu/drm/v3d/v3d_submit.c:1255 v3d_submit_csd_ioctl()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L1225 (success) | return 0 | YES | YES (v3d_job_put drops initial ref) | ✅ | normal operation: setup ref dropped, scheduler’s ref remains. |

## Full Response

```
| Line | Return Type | GET Done? (v3d_push_job on job) | PUT Done? (needs 2 puts: cleanup+extra) | Balanced? | Notes |
|------|-------------|---------------------------------|----------------------------------------|-----------|-------|
| L1178 (pad check) | error -EINVAL | NO (before any job) | N/A | ✅ | no job allocated |
| L1180 (no CSD) | error -EINVAL | NO | N/A | ✅ | no job |
| L1184 (bad flags) | error -EINVAL | NO | N/A | ✅ | no job |
| L1190 (extensions fail) | return ret | NO | N/A | ✅ | no job |
| L1193 (setup fail, goto fail) | error (ret) | NO | YES (v3d_job_cleanup) | ✅ | one ref from setup → cleanup puts it |
| L1203 (EAGAIN goto fail_perfmon) | error -EAGAIN | NO | YES (cleanup) | ✅ | no push → only one ref |
| L1206 (perfmon find fail, goto fail_perfmon) | error -ENOENT | NO | YES (cleanup) | ✅ | no push → one ref |
| **L1215 (dep fail, goto fail_unreserve)** | **error (ret)** | **YES** | **NO (only one put via cleanup, needs two)** | **❌ LEAK** | `v3d_push_job` inc’d ref; error path only does `v3d_job_cleanup` (one put), leaving scheduler’s ref. |
| L1225 (success) | return 0 | YES | YES (v3d_job_put drops initial ref) | ✅ | normal operation: setup ref dropped, scheduler’s ref remains. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
A `v3d_push_job` at L1208 unconditionally increments the job’s refcount. The error path at L1215 (`goto fail_unreserve`) releases only one reference via `v3d_job_cleanup`, leaving the scheduler’s reference leaked.
```
