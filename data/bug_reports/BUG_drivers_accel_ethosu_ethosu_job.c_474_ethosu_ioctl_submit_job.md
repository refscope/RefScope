# REAL BUG: drivers/accel/ethosu/ethosu_job.c:474 ethosu_ioctl_submit_job()

**Confidence**: MEDIUM | **Counter**: `ejob->base.s_fence->finished.refcount.refcount.refs.counter`

## Reasoning

` call `drm_sched_job_cleanup` followed by `ethosu_job_err_cleanup`. The latter likely triggers another `dma_fence_put` on `s_fence->finished` (either directly or via job release), causing a refcount underflow and the observed excess put at line 474 (inside `ethosu_job_err_cleanup` or its callee).

## Full Response

```
[NEED_SOURCE] ethosu_job_err_cleanup

## Path Table for `ethosu_ioctl_submit_job()`

| Path Description | LINE | GET from `ethosu_job_push`? | PUT via `drm_sched_job_cleanup`? | PUT via `ethosu_job_err_cleanup`? | Balanced? | Notes |
|------------------|------|-----------------------------|----------------------------------|-----------------------------------|-----------|-------|
| Early sram check 1 | early | N/A (no job) | N/A | N/A | ✅ | before job alloc |
| Early sram check 2 | early | N/A (no job) | N/A | N/A | ✅ | before job alloc |
| kzalloc job fail | after alloc | N/A (no job) | N/A | N/A | ✅ | |
| done_fence alloc fail | `goto out_cleanup_job` | `drm_sched_job_init` NOT called → fence not init | `drm_sched_job_cleanup` called (ret !=0) → likely invalid | `ethosu_job_err_cleanup` called | ❓ not fence-related | fence not present |
| `drm_sched_job_init` fail | `goto out_put_job` | NO (push not reached) | NO (skip cleanup label) | `ethosu_job_err_cleanup` called | ❓ | fence may be partially init → possible leak, not excess put |
| **`cmd_bo` lookup fail** | `goto out_cleanup_job` | **NO** | **YES** (ret !=0) | **YES** (called) | **❌ EXCESS** | fence refcount=1 → `drm_sched_job_cleanup` drops to 0 → `ethosu_job_err_cleanup` likely puts again → excess |
| **`cmd_info` NULL** | `goto out_cleanup_job` | **NO** | **YES** | **YES** | **❌ EXCESS** | same as above |
| **Any region BO error** | `goto out_cleanup_job` | **NO** | **YES** | **YES** | **❌ EXCESS** | all error paths inside region loop |
| **`ethosu_job_push` failure** | fall through to `out_cleanup_job` | **NO (push failed, conditional get not taken)** | **YES** | **YES** | **❌ EXCESS** | double put scenario |
| `ethosu_job_push` success | `ethosu_job_put(ejob); return 0;` | **YES** (get taken) | NO (cleanup deferred to job release) | NO (release deferred) | ✅ | job release will call `drm_sched_job_cleanup` once |

All paths after `drm_sched_job_init` that hit `out_cleanup_job` call `drm_sched_job_cleanup` followed by `ethosu_job_err_cleanup`. The latter likely triggers another `dma_fence_put` on `s_fence->finished` (either directly or via job release), causing a refcount underflow and the observed excess put at line 474 (inside `ethosu_job_err_cleanup` or its callee).

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
```
