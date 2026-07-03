# REAL BUG: drivers/gpu/drm/i915/gt/intel_execlists_submission.c:1613 execlists_dequeue()

**Confidence**: HIGH | **Counter**: `$->fence.refcount.refcount.refs.counter`

## Reasoning

equires `submit` to be false (meaning the virtual submission itself didn’t happen, so `__i915_request_submit` must have been false), the unconditional put is still incorrect in the `submit = true` case and is the root cause of the use‑after‑free; the warning at L1613 is a downstream manifestation.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1396 (active[1] early return) | early return | N/A (no get on this path) | N/A | ✅ | No refs acquired, no leak |
| L1424 (virtual loop, can’t merge, return) | early return | N/A | N/A | ✅ | No get in this path |
| L1454 (virtual loop, after `last = rq`, then `i915_request_put(rq)`) | normal flow (continue) | **NO explicit get**, but `last` becomes a dangling pointer because the reference from `ve->request` is dropped | **YES** (put releases the `ve->request` reference) | ❌ **USE-AFTER-FREE** – the put is correct for the old reference, but the `last` pointer now points to a request with refcount 0. Later use of `last` (e.g. at L1610 `i915_request_get(last)`, then L1613 `i915_request_put(*port)`) operates on a freed/zero-ref object, leading to excess-put error | The unconditional put after setting `last = rq` is wrong; the reference must be retained when `__i915_request_submit()` succeeds. This is the root cause of the reported excess-put at line 1613. |
| L1607‑1609 (`done:` fall‑through, `*port++ = i915_request_get(last)`) | normal flow (then else branch) | YES (explicit get on `last`) | YES (the else branch at L1613 puts all port entries) | ✅ on its own, **but** if `last` is a dangling pointer from L1454, the get accesses freed memory and the following put may underflow the refcount | The warning at L1613 is the symptom of the earlier bug. |
| L1596 (`goto done` from port/full checks) | normal flow (skip current request) | YES (the previous `last` is already set, and `done:` does a get on it) | YES (else branch put) | ✅ unless `last` is dangling | Same dependency on `last` validity |

**Detailed analysis of the virtual engine loop bug**

The virtual engine loop contains:

```
rq = ve->request;
...
if (__i915_request_submit(rq)) {
    virtual_xfer_context(ve, engine);
    submit = true;
    last = rq;
}

i915_request_put(rq);
```

`ve->request` holds a kref tracked by `i915_request_get`/`_put`.  When `__i915_request_submit()` succeeds, the request will be submitted and further used (via `last`).  However, the function unconditionally calls `i915_request_put(rq)` **after** assigning `last = rq`.  This drops the only reference that keeps the request alive, making `last` a dangling pointer.  Later, when the function proceeds to `done:` and does `*port++ = i915_request_get(last)`, it touches a request whose refcount may already be 0 and the memory potentially freed.  In the `else` branch (when `submit` remains false for the whole dequeue), the subsequent `i915_request_put(*port)` at line 1613 would then decrement an already‑zero refcount, triggering the “excess put” warning.  Even though the specific execution that hits the bug requires `submit` to be false (meaning the virtual submission itself didn’t happen, so `__i915_request_submit` must have been false), the unconditional put is still incorrect in the `submit =
```
