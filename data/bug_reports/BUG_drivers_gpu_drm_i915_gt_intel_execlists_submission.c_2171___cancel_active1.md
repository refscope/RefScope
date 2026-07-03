# REAL BUG: drivers/gpu/drm/i915/gt/intel_execlists_submission.c:2171 __cancel_active1()

**Confidence**: HIGH | **Counter**: `$->fence.refcount.refcount.refs.counter`

## Reasoning

| L2175 | return err (success) | YES | YES | YES | YES | ✅ | Both gets done |

## Full Response

```
| Line | Return Type | GET rq[0]? | GET rq[1]? | PUT rq[1]? | PUT rq[0]? | Balanced? | Notes |
|------|-------------|------------|------------|------------|------------|-----------|-------|
| L2111 | return -EIO (igt_live_test_begin fail) | NO | NO | N/A | N/A | ✅ | Before any get |
| L2119 | return PTR_ERR(rq[0]) (IS_ERR) | NO | NO | N/A | N/A | ✅ | rq[0] invalid, no get |
| L2126 | goto out (wait_for_spinner fail) | YES | NO | YES (NULL safe) | YES | ✅ | rq[1] still NULL, get on rq[0] balanced |
| L2136 | goto out (rq[1] IS_ERR) | YES | NO | YES (ERR_PTR!) | YES | ❌ EXCESS PUT | rq[1] is error pointer, get never called, put on ERR_PTR |
| L2144 | goto out (await_dma_fence err) | YES | YES | YES | YES | ✅ | Both gets done |
| L2148 | goto out (intel_engine_pulse err) | YES | YES | YES | YES | ✅ | Both gets done |
| L2152 | goto out (wait_for_reset err) | YES | YES | YES | YES | ✅ | Both gets done |
| L2158 | goto out (rq[0] error != 0) | YES | YES | YES | YES | ✅ | Both gets done |
| L2163 | goto out (rq[1] error != -EIO) | YES | YES | YES | YES | ✅ | Both gets done |
| L2175 | return err (success) | YES | YES | YES | YES | ✅ | Both gets done |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`i915_request_put(rq[1])` at out label is called on an error pointer when `rq[1]` creation fails (IS_ERR path), without a prior `i915_request_get`, causing an excess put.
```
