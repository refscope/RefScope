# REAL BUG: drivers/gpu/drm/i915/i915_request.c:1315 live_all_engines()

**Confidence**: HIGH | **Counter**: `$->fence.refcount.refcount.refs.counter`

## Reasoning

| Full success: all loops pass, wait loop puts each request and sets NULL, then out_request skips NULLs, then out_free | success | YES (but put earlier) | YES | ✅ | |

## Full Response

```
| Path Description | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| Early alloc failure: return -ENOMEM (before for-loop) | error | NO | N/A | ✅ | no request created |
| igt_live_test_begin fail: goto out_free -> return err | error | NO | NO (no request processed) | ✅ | no get yet |
| Recursive batch fail after some engines succeeded: goto out_free -> return err | error | YES (for previous engines) | NO | ❌ LEAK | out_free does not call i915_request_put for requests that already got a reference |
| Create kernel request fail (IS_ERR) for current engine: goto out_unlock -> out_request cleanups -> out_free | error | NO for current, YES for previous | YES (out_request loop puts all) | ✅ | |
| Any error in completion/resolve/wait loops: goto out_request -> out_free | error | YES (all submitted) | YES (out_request puts all) | ✅ | |
| Full success: all loops pass, wait loop puts each request and sets NULL, then out_request skips NULLs, then out_free | success | YES (but put earlier) | YES | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`i915_request_get()` is called unconditionally for successfully created requests, but the `goto out_free` path taken on a later `recursive_batch` failure skips the required `i915_request_put()`, leaking references.
```
