# REAL BUG: drivers/gpu/drm/i915/gt/intel_reset.c:1804 igt_reset_queue()

**Confidence**: HIGH | **Counter**: `$->fence.refcount.refcount.refs.counter`

## Reasoning

| loop end / break after all engines → fini → return err/success | mixed | N/A | balanced | ✅ | all previous paths balanced |

## Full Response

```
| Path Description | Return Type | GET Done? (prev) | PUT Done? (prev) | Balanced? | Notes |
|------------------|-------------|------------------|------------------|-----------|-------|
| hang_init error → goto unlock → return err | error | NO | N/A | ✅ | no get happened |
| for_each_engine: modify policy error → goto fini → return err | error | NO | N/A | ✅ | no get yet |
| for_each_engine: prev IS_ERR → goto restore → (err set) → goto fini → return err | error | NO | N/A | ✅ | no prev get |
| for_each_engine: prev gotten (i915_request_get), rq creation fails (IS_ERR) → goto restore → (err set) → goto fini → return err | error | YES | NO | ❌ LEAK | missing i915_request_put(prev) |
| inside do-while: error paths (e.g., wait_for_others fail) → put(rq) & put(prev) → goto restore → (err set) → goto fini → return err | error | YES | YES | ✅ | both put before goto |
| normal do-while exit → final i915_request_put(prev) → restore (no err) → igt_flush_test fails → break → fini → return err | error/break | YES | YES (final put) | ✅ | prev already released |
| loop end / break after all engines → fini → return err/success | mixed | N/A | balanced | ✅ | all previous paths balanced |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Missing i915_request_put(prev) in error path when rq = hang_create_request() fails (IS_ERR), after i915_request_get(prev) already incremented the refcount.
```
