# REAL BUG: kernel/events/core.c:6578 perf_event_period()

**Confidence**: LOW | **Counter**: `$->refcount.refs.counter`

## Reasoning

nts. The unlock function unconditionally does two `put_ctx` operations. If the lock takes only one reference, then every call to `perf_event_period()` will do an excess put, matching the `refcount excess put` warning. Without the lock source, we cannot determine whether the gets/puts are balanced.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L6578 | return ret   | Unknown — depends on how many references `perf_event_ctx_lock` acquires | YES — `perf_event_ctx_unlock` contract says it calls `put_ctx` **twice** (unconditional) | **Unknown** — if `perf_event_ctx_lock` acquires fewer than two references, unlock does an excess put | Single execution path; no error check on `ctx` before unlock. The PUT contract lists `→put_ctx(put),put_ctx(put) `, so two puts occur. |

[NEED_SOURCE] perf_event_ctx_lock

The crucial missing information is the exact number of references that `perf_event_ctx_lock()` increments. The unlock function unconditionally does two `put_ctx` operations. If the lock takes only one reference, then every call to `perf_event_period()` will do an excess put, matching the `refcount excess put` warning. Without the lock source, we cannot determine whether the gets/puts are balanced.

VERDICT: UNCLEAR
CONFIDENCE: LOW
The single return path calls `perf_event_ctx_lock` (unknown get count) then `perf_event_ctx_unlock` (contract says two puts). Without knowing how many references the lock acquires, we cannot confirm whether the excess put is a caller bug or an inherent mismatch in the callee internals.

--- [NEED_SOURCE r1] ---

[SYSTEM] Source for perf_event_ctx_lock_nested():

```c
// perf_event_ctx_lock_nested()
// /home/liang/workspace/DataShare/TargetProj/linux-smatch/linux/kernel/events/core.c
1484: perf_event_ctx_lock_nested(struct perf_event *event, int nesting)
1485: {
1486: 	struct perf_event_context *cpuctx;
1487: 
1488: again:
1489: 	rcu_read_lock();
1490: 	cpuctx = READ_ONCE(event->pmu_ctx->pmu->cpu_context);
1491: 	if (cpuctx) {
1492: 		if (refcount_inc_not_zero(&cpuctx->refcount)) {
1493: 			rcu_read_unlock();
1494: 			goto again;
1495: 		}
1496: 	}
1497: 	rcu_read_unlock();
1498: 
1499: 	mutex_lock(&event->child_mutex);
1500: 	perf_pmu_disable(event->pmu);
1501: 
1502: 	return cpuctx;
1503: }
```

Now we see: perf_event_ctx_lock_nested does NOT call get_ctx at all. It simply attempts to get a reference to cpuctx if it's not already had (or something?). Actually, the logic is odd: if (cpuctx) { if (refcount_inc_not_zero(...)) { rcu_read_unlock(); goto again; } } ... That seems like it's trying to ensure it's not the same context? Wait, the refcount_inc_not_zero returns true if it successfully incremented, but then it does goto again. This probably means that if the context is already held (i.e., we already have a reference), it will loop. I'm not entirely sure. But the key point for our analysis: Does this function acquire any reference that needs to be put later? It does call refcount_inc_not_zero, but then if it increments, it loops (goto again). So it might be that it's waiting until the refcount is zero? Actually, refcount_inc_not_zero returns true if it increments from non-zero, so it means the context is alive; but it still unr
```
