# REAL BUG: drivers/gpu/drm/i915/gt/intel_execlists_submission.c:2266 __cancel_queued()

**Confidence**: HIGH | **Counter**: `$->fence.refcount.refcount.refs.counter`

## Reasoning

| ~L2262 | (fallthrough) `goto out` success | ALL YES | ALL YES | ✅ | normal return, all gets put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L2180 | `return -EIO` (live_test_begin fail) | N/A (no rq) | N/A | ✅ | before any allocation/get |
| ~L2188 | `return PTR_ERR(rq[0])` (rq[0] alloc fail) | NO (get not reached) | NO | ✅ | rq[0] is ERR_PTR, no get |
| ~L2195 | `goto out` (igt_wait_for_spinner fail) | GET(rq[0]) YES; rq[1]/rq[2] NO | PUT(rq[2]) NULL, PUT(rq[1]) NULL, PUT(rq[0]) YES | ✅ (if NULL-safe) | rq[0] balanced; rq[1,2] NULL put likely safe |
| ~L2203 | `goto out` (rq[1] alloc fail) | GET(rq[0]) YES; GET(rq[1]) NO | PUT(rq[2]) NULL, PUT(rq[1]) **on ERR_PTR**, PUT(rq[0]) YES | ❌ EXCESS PUT | rq[1] is ERR_PTR, put w/o get → smatch warns; also unsafe pointer deref |
| ~L2212 | `goto out` (await_dma_fence fail after rq[1] get) | GET(rq[0]), GET(rq[1]) YES; rq[2] NO | PUT(rq[2]) NULL, PUT(rq[1]) YES, PUT(rq[0]) YES | ✅ | all gotten are put |
| ~L2219 | `goto out` (rq[2] alloc fail) | GET(rq[0]), GET(rq[1]) YES; GET(rq[2]) NO | PUT(rq[2]) **on ERR_PTR**, PUT(rq[1]) YES, PUT(rq[0]) YES | ❌ EXCESS PUT | rq[2] is ERR_PTR, put w/o get |
| ~L2228 | `goto out` (await_dma_fence fail after rq[2] get) | ALL YES | ALL YES | ✅ | |
| ~L2232 | `goto out` (intel_engine_pulse fail) | ALL YES | ALL YES | ✅ | |
| ~L2237 | `goto out` (wait_for_reset fail) | ALL YES | ALL YES | ✅ | |
| ~L2243 | `goto out` (rq[0] error check) | ALL YES | ALL YES | ✅ | |
| ~L2250 | `goto out` (semaphore check) | ALL YES | ALL YES | ✅ | |
| ~L2257 | `goto out` (rq[2] error check) | ALL YES | ALL YES | ✅ | |
| ~L2262 | (fallthrough) `goto out` success | ALL YES | ALL YES | ✅ | normal return, all gets put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`__cancel_queued()` passes ERR_PTR to `i915_request_put()` (which dereferences it) on allocation failure paths for `rq[1]` and `rq[2]`. Smatch correctly identifies a put without a corresponding get, as the error pointers lack a prior `i915_request_get`. This is both a static analysis mismatch (excess put) and a dangerous runtime bug (dereferencing invalid pointers in `dma_fence_put`).
```
