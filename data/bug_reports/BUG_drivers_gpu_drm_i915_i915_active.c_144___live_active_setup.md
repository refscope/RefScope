# REAL BUG: drivers/gpu/drm/i915/i915_active.c:144 __live_active_setup()

**Confidence**: MEDIUM | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

hat counter and, when combined with `__live_put`, cause an excess put. The contract for `i915_active_release` is not provided, making it impossible to fully resolve the interaction from the given sources. Therefore, the verdict is **UNCLEAR** due to cross‑function, source‑missing callee internals.

## Full Response

```
| Line (approx) | Return Type | GET Done? (kref) | PUT Done? (kref) | Balanced? | Notes |
|---------------|-------------|-------------------|-------------------|-----------|-------|
| L11 (return ERR_PTR) | error, no active | NO (before alloc) | N/A | ✅ | No active object. |
| L16 (return ERR_PTR) | error, no submit | YES (__live_alloc) | NO (kfree only) | ❌ MISSING PUT | kfree without __live_put – leaks the initial kref. Not an excess put. |
| L21 → out (acquire failed) | error, goto out | YES (__live_alloc) | YES (__live_put in err block) | ✅ | __live_put called in error path. |
| L29 break → out (rq create fail) | error | YES | YES (__live_put in err block) | ✅ | __live_put called. |
| L40 break → out (add request fail) | error | YES | YES (__live_put in err block) | ✅ | __live_put called. |
| Post-loop err set (count mismatch) → out | error | YES | YES (__live_put in err block) | ✅ | __live_put called. |
| Success (err==0, no post-loop error) | return active | YES | NO (caller owns) | ✅ (ownership passed) | Caller will later __live_put. |

**Additional note**: The warning is a refcount *excess* put on the kref counter `$->ref.refcount.refs.counter`. Within this function, the only kref put is via `__live_put`, called exactly once on every error path that reaches `out`. The missing put on the early `kfree` path is a leak, not an excess put. If `i915_active_release` operates on the same kref (e.g., `active->base.ref`), it could decrement that counter and, when combined with `__live_put`, cause an excess put. The contract for `i915_active_release` is not provided, making it impossible to fully resolve the interaction from the given sources. Therefore, the verdict is **UNCLEAR** due to cross‑function, source‑missing callee internals.

VERDICT: UNCLEAR  
CONFIDENCE: MEDIUM  
Reason: The live_active kref appears balanced inside this function, but without the source of `i915_active_release` it cannot be determined whether it shares the counter flagged by the warning, possibly leading to an excess put.
```
