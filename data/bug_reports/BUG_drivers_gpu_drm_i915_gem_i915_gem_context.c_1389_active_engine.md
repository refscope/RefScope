# REAL BUG: drivers/gpu/drm/i915/gem/i915_gem_context.c:1389 active_engine()

**Confidence**: HIGH | **Counter**: `rq->fence.refcount.refcount.refs.counter`

## Reasoning

- Result: the reference on `old` (originating from an earlier `i915_request_get`) is never released → **refcount leak**

## Full Response

```
## Path Table

| Exit Line | Return Path Description | GET Done? | PUT Done? | Balanced? | Notes |
|-----------|--------------------------|-----------|-----------|-----------|-------|
| ~L903 (early return) | intel_context_create fails, no requests created | NO | N/A | ✅ | No refcount operations on requests |
| ~L921 (break then end) | intel_context_create_request fails → break, then cleanup loop | NO for current iteration; previous get on old is still in rq[idx] | Yes, old is still in rq[idx] → final loop puts it; new never created | ✅ | Balanced because old remains in array |
| ~L946 (normal exit) | while‑loop terminates normally (`arg->stop`) or break from create_request (already covered) | Previous gets for all slots are held in rq[]; final loop puts all | Yes (all slots) | ✅ | All references released |
| ~L938 (break then end) | active_request_put(old) fails → break; rq[idx] already overwritten with new; old not put again | **YES** (old obtained from earlier `i915_request_get`) | **NO** (put failed and no retry, old pointer lost) | ❌ LEAK | `active_request_put(old)` returned error; old reference leaked |

**Detail for the LEAK path (L938):**
- `rq[idx] = i915_request_get(new);`  → acquires reference for `new`
- `active_request_put(old);` returns error → break
- `old` pointer is no longer stored in `rq[]` (overwritten by `new`)
- Cleanup loop only puts `rq[count]` (which is `new` for that slot), not `old`
- Result: the reference on `old` (originating from an earlier `i915_request_get`) is never released → **refcount leak**

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
When `active_request_put(old)` fails, the old request’s reference is never released because the slot has been overwritten and the cleanup loop does not handle the error path—resulting in a refcount leak.
```
