# REAL BUG: drivers/gpu/drm/i915/i915_request.c:1123 i915_request_await_start()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| 1107 | return err  (error, err != 0) | NO (conditional get did NOT occur) | YES                       | ❌ EXCESS PUT | unconditional put on a fence that did not have its refcount incremented |

## Full Response

```
| Line | Return Type | GET Done? (dma_fence_get via await) | PUT Done? (dma_fence_put) | Balanced? | Notes |
|------|-------------|-------------------------------------|---------------------------|-----------|-------|
| 1067 | return 0    | NO (before any get)                 | NO                        | ✅        | early timeline match |
| 1070 | return 0    | NO (before any get)                 | NO                        | ✅        | signal already started |
| 1098 | return 0    | NO (fence == NULL, no get)          | NO                        | ✅        | loop produced no valid fence |
| 1107 | return 0 (success) | YES (conditional get succeeded) | YES                       | ✅        | await took a fence reference, matched by put |
| 1107 | return err  (error, err != 0) | NO (conditional get did NOT occur) | YES                       | ❌ EXCESS PUT | unconditional put on a fence that did not have its refcount incremented |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
i915_sw_fence_await_dma_fence is documented as a conditional get, so on error it does not take a fence reference; the unconditional dma_fence_put(fence) that follows on the error path therefore triggers an excess put.
```
