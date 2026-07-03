# REAL BUG: drivers/net/ethernet/sfc/siena/farch.c:713 efx_farch_do_flush()

**Confidence**: HIGH | **Counter**: `efx->rxq_flush_pending.counter`

## Reasoning

ing flushes that were never started (due to outstanding limit causing inner loop break) remain with their increments intact and are not decremented. The error path resets the counter to 0, masking a leak only in that scenario. The success path leaves the counter elevated – a genuine refcount leak.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L702 (after while loop, active_queues==0 and all pending were started) | success (rc=0) | YES (all atomic_inc on rxq_flush_pending) | YES (all started flushes dec pending) | ✅ | pending counter reaches 0 |
| L702 (after while loop, active_queues==0 but some pending never started) | success (rc=0) | YES (all atomic_inc) | NO (remaining pending never dec'd) | ❌ LEAK | pending >0 → refcount leak |
| L710 (timeout, counters reset) | error (rc=-ETIMEDOUT) | YES (all atomic_inc) | YES (atomic_set 0, counter cleared) | ✅ | no outstanding count at return |

The initial unconditional `atomic_inc` gets are executed for every RX queue at the top of the function. The while loop may exit normally when `active_queues` reaches 0, but pending flushes that were never started (due to outstanding limit causing inner loop break) remain with their increments intact and are not decremented. The error path resets the counter to 0, masking a leak only in that scenario. The success path leaves the counter elevated – a genuine refcount leak.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Unconditional atomic_inc on rxq_flush_pending at start; success path where while loop exits with active_queues==0 but pending flushes not yet started leaks these increments (no atomic_dec or atomic_set to zero).
```
