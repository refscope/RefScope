# REAL BUG: kernel/events/core.c:12946 pmu_detach_event()

**Confidence**: MEDIUM | **Counter**: `$->refcount.refs.counter`

## Reasoning

Without the callees’ exact source we cannot be 100% certain, but the contract evidence points to a real double‑put. Therefore:

## Full Response

```
[NEED_SOURCE] perf_event_ctx_lock
[NEED_SOURCE] perf_event_ctx_unlock

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| implicit (end of function) | void return | UNKNOWN (perf_event_ctx_lock semantics not provided; may or may not increment refcount) | YES (perf_event_ctx_unlock performs a put_ctx; contract records *two* unconditional puts) | ❓ Cannot determine without lock source | The unlock contract claims two put operations, which would be an overrelease even if the lock did one get. This needs verification. |

The PUT contract shows `put_ctx(put),put_ctx(put)` meaning the unlock performs **two** reference drops on the context. If that contract is accurate, `pmu_detach_event()` will trigger a refcount underflow every time it executes, because the matching GET (if any) would only obtain one reference. The `__pmu_detach_event` helper does not appear to acquire a refcount, and the `scoped_guard` list operation is unrelated. The excess put would manifest as a refcount underflow detected at the unlock site (or later). The warning line (12946) is inside the `scoped_guard`, but the underflow may be attributed there by smatch due to inlining or post‑dominance analysis.

Without the callees’ exact source we cannot be 100% certain, but the contract evidence points to a real double‑put. Therefore:

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM

perf_event_ctx_unlock is contracted to do two unconditional puts; only a single get‑balanced path appears in pmu_detach_event, leading to a consistent refcount excess put (underflow). Requesting callee source to confirm.

--- [NEED_SOURCE r1] ---

[NEED_SOURCE] perf_event_ctx_lock_nested
[NEED_SOURCE] put_ctx
[NEED_SOURCE] pmu_detach_event
[NEED_SOURCE] perf_event_ctx_unlock

--- [NEED_SOURCE r2] ---

[NEED_SOURCE] perf_event_ctx_unlock
[NEED_SOURCE] perf_pmu_output_stop

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| implicit (end of function) | void return | YES (perf_event_ctx_lock_nested acquires one refcount via refcount_inc_not_zero) | UNKNOWN (perf_event_ctx_unlock not yet seen; contract claims two unconditional puts, which would be an overrelease, not a leak) | ❓ | Need actual unlock source and the caller of pmu_detach_event to determine if there is a leak or an overrelease. The warning says "refcount leak", suggesting the unlock may not release the expected reference. |

So far we know the lock acquires exactly one reference. The unlock contract is suspicious (two puts would cause an underflow, contradictory to a "leak" warning). I must see the real `perf_event_ctx_unlock` and the exact line 12946 in `perf_pmu_output_stop` where the leak is flagged.
```
