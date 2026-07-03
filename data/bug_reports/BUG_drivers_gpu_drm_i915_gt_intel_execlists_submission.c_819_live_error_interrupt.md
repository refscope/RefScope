# REAL BUG: drivers/gpu/drm/i915/gt/intel_execlists_submission.c:819 live_error_interrupt()

**Confidence**: HIGH | **Counter**: `$->fence.refcount.refcount.refs.counter`

## Reasoning

The explicit `i915_request_get()` references (stored in `client[]`) are properly balanced by the `out:` cleanup loop, so they are not the source of the leak flagged by the warning.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (creation ref) | PUT Done? (rq put) | Balanced? | Notes |
|------|-------------|--------------------------|--------------------|-----------|-------|
| ~690 (early guard: `!intel_has_reset_engine`) | `return 0` | NO | N/A | ✅ | No request created |
| ~770 (`return err` inside `for_each_engine` after `st_engine_heartbeat_enable`) | error return | YES (from any `intel_context_create_request()` that succeeded in the failing phase) | NO | ❌ LEAK | `out` label only releases `client[i]` references from `i915_request_get()`. The initial reference obtained from `intel_context_create_request()` is never released via `i915_request_put(rq)`. |
| ~780 (final `return 0`) | success return | YES (from all successfully created requests in all phases) | NO | ❌ LEAK | Same as above – creation references of every request are leaked. |

**Explanation for GET = YES**:  
`intel_context_create_request()` returns a request with a carried reference (standard i915 semantics). After calling `i915_request_add(rq)`, the creation reference is still held by the caller and must be released with `i915_request_put(rq)`. The code never calls `i915_request_put(rq)` for any request. This leaks the initial kref on every `rq` that was created, both on error paths (where the leak is more obvious because the request is not stored in `client[]`) and on the success path (where the creation ref is simply abandoned when the local variable `rq` goes out of scope).

The explicit `i915_request_get()` references (stored in `client[]`) are properly balanced by the `out:` cleanup loop, so they are not the source of the leak flagged by the warning.

## VERDICT: REAL_BUG  
## CONFIDENCE: HIGH  

`intel_context_create_request()` returns a request with an initial kref. All return paths after at least one successful call to `intel_context_create_request()` fail to call `i915_request_put(rq)`, leaking the underlying `dma_fence` refcount.
```
