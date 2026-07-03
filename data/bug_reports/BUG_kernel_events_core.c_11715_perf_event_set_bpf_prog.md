# REAL BUG: kernel/events/core.c:11715 perf_event_set_bpf_prog()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

[NEED_SOURCE] perf_event_ctx_lock, perf_event_ctx_unlock — to confirm exact get/put counts, but the given contract for the PUT is sufficient to identify the double‑put defect.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L11711 → L11713 → L11715 | success (return ret) | YES (perf_event_ctx_lock called, contract unknown but assumed single get) | YES (perf_event_ctx_unlock called) | ❌ NO | Contract says unlock contains `put_ctx(put),put_ctx(put)` — two puts, exceeding the single get. Excess put on ctx refcount. |

## Analysis

- Only one return path exists in `perf_event_set_bpf_prog()`: after the lock, helper, unlock, return `ret`.
- The GET is `perf_event_ctx_lock(event)` at L11711. While its contract is unknown, the standard pattern for context locking is a single reference acquisition (e.g., `kref_get` or `refcount_inc`).
- The PUT is `perf_event_ctx_unlock(event, ctx)` at L11713. The provided contract explicitly states it unconditionally performs **two** `put_ctx(put)` operations.
- The PUT therefore drops the reference count twice for a single acquisition, directly causing a **refcount excess put** (refcount underflow) on the context’s `refcount.refs.counter`.
- The warning is triggered at the call site (L11713 or the subsequent return line) because that is where the erroneous double‑put executes.
- No ownership transfer, async deferral, or error paths complicate this call; the bug is in the callee’s implementation, but the warning is correctly a **REAL_BUG**.

[NEED_SOURCE] perf_event_ctx_lock, perf_event_ctx_unlock — to confirm exact get/put counts, but the given contract for the PUT is sufficient to identify the double‑put defect.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`perf_event_ctx_unlock` contract indicates two `put_ctx` calls per unlock, while only one reference was obtained by `perf_event_ctx_lock`, causing an excess put on ctx->refcount.

--- [NEED_SOURCE r1] ---

[NEED_SOURCE] perf_event_ctx_lock_nested

The contract for `perf_event_ctx_unlock` unconditionally does `put_ctx(put)` twice, which is a double decrement on the perf_event_ctx reference count. The matching lock function `perf_event_ctx_lock` calls `perf_event_ctx_lock_nested`, whose implementation is not yet provided. The runtime warning “decrement hit 0” strongly suggests that the lock function does only a single get, causing the refcount to underflow when the double put is executed. To confirm the exact number of gets, the source of `perf_event_ctx_lock_nested` is needed.

--- [NEED_SOURCE r2] ---

## Final Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L11711 → L11713 → L11715 | success (return `ret`) | YES (1 ref: `refcount_inc_not_zero` in `perf_event_ctx_lock_nested`) | YES (2 refs: `put_ctx(put) × 2` in `perf_event_ctx_unlock`) | ❌ EXCESS PUT | Unlock releases one reference more than lock acquired, causing refcount underflow |

## Analysis

- `perf_event_ctx_lock_nested()` (L1466) acquires exactly **one** reference on `ctx->refcount` via 
```
