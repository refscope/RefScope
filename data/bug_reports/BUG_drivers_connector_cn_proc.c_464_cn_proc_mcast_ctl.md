# REAL BUG: drivers/connector/cn_proc.c:464 cn_proc_mcast_ctl()

**Confidence**: HIGH | **Counter**: `proc_event_num_listeners.counter`

## Reasoning

| **L472** | **out (sk absent, IGNORE, dec)** | **NO** | **YES** | **❌ EXCESS PUT** | **Underflow: dec without prior inc, triggered by kernel/ns-less IGNORE** |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L405 | early return (bad namespace) | NO | NO | ✅ |  |
| L419 | early return (invalid msg->len) | NO | NO | ✅ |  |
| L440 | goto out (alloc fail) | NO | NO | ✅ |  |
| L472 | out (sk present, LISTEN, inc) | YES | NO | ⚠️ (intended) | Listener ref held across calls |
| L472 | out (sk present, LISTEN, no inc) | NO | NO | ✅ |  |
| L472 | out (sk present, IGNORE, dec) | NO | YES | ✅ (paired) | Dec balances prior inc |
| L472 | out (sk present, IGNORE, no dec) | NO | NO | ✅ |  |
| L472 | out (sk absent, LISTEN, inc) | YES | NO | ❌ (unbalanced) | Leak: inc without socket |
| **L472** | **out (sk absent, IGNORE, dec)** | **NO** | **YES** | **❌ EXCESS PUT** | **Underflow: dec without prior inc, triggered by kernel/ns-less IGNORE** |
| L472 | out (default/EINVAL) | NO | NO | ✅ |  |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When `nsp->sk` is NULL, the IGNORE case unconditionally calls `atomic_dec()` on `proc_event_num_listeners` even though no `atomic_inc()` was performed for this context, causing the refcount excess put. The switch must be guarded by a check that a valid socket exists.
```
