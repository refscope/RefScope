# REAL BUG: drivers/gpu/drm/i915/gt/intel_reset.c:1245 __igt_reset_engines()

**Confidence**: HIGH | **Counter**: `$->fence.refcount.refcount.refs.counter`

## Reasoning

e leak: after `i915_request_get()` unconditionally increments the refcount, the `goto restore` inside the `if (!using_guc) { intel_engine_reset(...); if (err) goto restore; }` block does not call `i915_request_put(rq)`, and the `restore` label (and subsequent `break`) do not release the reference.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L967 | early return 0 | NO (before get) | N/A | ✅ | `!intel_has_reset_engine` |
| L971 | return err | NO (before get) | N/A | ✅ | `hang_init` fail |
| L977 | return -ENOMEM | NO (before get) | N/A | ✅ | alloc fail |
| ~L1000 | goto restore | NO (IS_ERR rq, get skipped) | N/A | ✅ | `hang_create_request` returns error |
| ~L1010 | goto restore | YES (get succeeded) | YES (put just before goto) | ✅ | `wait_until_running` fail path |
| **~L1030** | **goto restore** | **YES (get succeeded)** | **NO** | **❌ LEAK** | **`intel_engine_reset` fails, skips `i915_request_put`** |
| ~L1040 | goto restore | YES | YES (put just before goto) | ✅ | `rq->fence.error != -EIO` path |
| ~L1045 | goto restore | YES | YES (put just before goto) | ✅ | `i915_request_wait` fail path |
| ~L1055 | normal rq put, then continue | YES | YES | ✅ | final put inside `if (rq)` block |
| ~L1065 | goto restore (idle after reset) | NO (rq already put) | N/A | ✅ | rq already released |
| ~L1080 | break (restore: err set) | N/A (rq already released or NULL) | N/A | ✅ | rq not pending |
| ~L1250 | final return err | NO (rq gone from scope) | N/A | ✅ | |

The **bold** row is the leak: after `i915_request_get()` unconditionally increments the refcount, the `goto restore` inside the `if (!using_guc) { intel_engine_reset(...); if (err) goto restore; }` block does not call `i915_request_put(rq)`, and the `restore` label (and subsequent `break`) do not release the reference.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`i915_request_get` at ~L1005 unconditionally acquires a reference; the error path at ~L1030 jumps to `restore` without matching `i915_request_put`, leaking the request's dma_fence refcount.
```
