# REAL BUG: drivers/infiniband/hw/irdma/cm.c:2503 irdma_handle_fin_pkt()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L2493 | break (TIME_WAIT) | NO | YES (irdma_rem_ref_cm_node) | ❌ EXCESS | Put without local get; can collide with timer’s pending put from FIN_WAIT2, causing double-put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2465 | break (SYN_RCVD/SYN_SENT/ESTABLISHED/MPAREJ_RCVD) | NO | NO | ✅ | No refcount ops |
| L2473 | break (MPAREQ_SENT) | YES (refcount_inc) | NO | ❌ LEAK? | refcount_inc without put here; put may be done later by send_reset (unknown) |
| L2479 | break (FIN_WAIT1) | NO | NO | ✅ | |
| L2487 | break (FIN_WAIT2) | POSSIBLE (schedule_cm_timer may inc) | POSSIBLE (may put) | UNCERTAIN | Conditional; may inc refcount for timer, possibly also put on error; balance depends on internal path |
| L2493 | break (TIME_WAIT) | NO | YES (irdma_rem_ref_cm_node) | ❌ EXCESS | Put without local get; can collide with timer’s pending put from FIN_WAIT2, causing double-put |
| L2498 | break (OFFLOADED/default) | NO | NO | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The TIME_WAIT handler unconditionally calls `irdma_rem_ref_cm_node` (put) which can race with the timer scheduled in FIN_WAIT2 that also drops a reference, leading to a double-put and refcount underflow when a retransmitted FIN arrives before the close timer expires.
```
