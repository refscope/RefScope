# REAL BUG: drivers/gpu/drm/i915/gt/intel_timeline.c:976 wrap_timeline()

**Confidence**: HIGH | **Counter**: `$->fence.refcount.refcount.refs.counter`

## Reasoning

4. `goto out` between GET and PUT? No gotos, but the imbalance is on the non-loop path where a put is executed with zero preceding get.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~959 (while loop, IS_ERR) | error | NO (if first iteration, original rq) / YES (if later iteration, got in previous loop) | YES (one put at line 957) | ❌ LEAK on first iteration; balanced on later iterations | First iteration puts caller’s rq without prior get. |
| ~978 (after loop, IS_ERR) | error | NO (if loop never entered) / YES (if loop entered) | YES (one put at line 976) | ❌ LEAK when loop not entered | The put on the argument rq happens without a matching get. |
| ~981 (success) | success | NO (if loop never entered) / YES (if loop entered) | YES (one put at line 976) | ❌ LEAK when loop not entered | Same imbalance for the old rq. |

**Pre-Put Checklist Answers:**
1. "Held for device lifetime"? No, no such pattern.
2. "Ownership transferred"? Not documented; default **NO transfer**.
3. Unconditional GET? `i915_request_get` is unconditional, but **no get is ever called on the original argument rq**.
4. `goto out` between GET and PUT? No gotos, but the imbalance is on the non-loop path where a put is executed with zero preceding get.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`wrap_timeline()` executes an unconditional `i915_request_put()` on the input `rq` (line 976, or line 957 in the first loop iteration) without ever calling `i915_request_get()` on that same request; the path where the while loop is skipped directly drops a reference that the caller still owns, leading to a refcount excess.
```
