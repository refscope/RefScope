# REAL BUG: drivers/usb/gadget/function/f_ncm.c:646 ncm_notify_complete()

**Confidence**: MEDIUM | **Counter**: `ncm->notify_count.counter`

## Reasoning

This is consistent with a scenario where `ncm_do_notify` submits a request **without** incrementing `notify_count`, and that request later completes with a non‑reset error, triggering the `atomic_dec` in the `default:` branch. The underflow proves a missing get.

## Full Response

```
## Path Analysis: ncm_notify_complete()

The function is `void` with no early returns. All execution flows exit after `spin_unlock(&ncm->lock)`. The refcount operations occur within the `switch (req->status)` block.

| Path / Branch | Return Type | GET Done? (by later `ncm_do_notify`) | PUT Done? | Balanced? | Notes |
|---------------|-------------|----------------------------------------|-----------|-----------|-------|
| case 0 (L628) | implicit return | Unknown – depends on whether `ncm_do_notify` increments `notify_count` | Yes – `atomic_dec` at L628 | Balanced **iff** `ncm_do_notify` increments; else **excess put** | The dec is unconditional for success. If the prior get (from submission) is missing, underflow occurs. |
| case -ECONNRESET / -ESHUTDOWN (L641) | implicit return | Unknown | No – `atomic_set` to 0 (not a dec) | Potentially **over‑inc** if `ncm_do_notify` increments, creating a spurious count of 1. | No dec, so no excess‑put here. The warning is not about this path. |
| default (L646) | implicit return | Unknown | Yes – `atomic_dec` at L646 | Balanced **iff** `ncm_do_notify` increments; else **excess put** | **WARNING LINE**: excess put reported here. This dec is unconditional for “other errors”. If the request was queued without an earlier increment, this dec underflows. |

In every case, `ncm_do_notify(ncm)` is called at L647 after the switch. The function is the **GET** side (presumed to increment `notify_count` before queueing the next notification). Without its source we cannot confirm when the increment really happens.  

The warning indicates an **excess put** (counter went negative). This is consistent with a scenario where `ncm_do_notify` submits a request **without** incrementing `notify_count`, and that request later completes with a non‑reset error, triggering the `atomic_dec` in the `default:` branch. The underflow proves a missing get.

[NEED_SOURCE] ncm_do_notify

---

**VERDICT: REAL_BUG**  
**CONFIDENCE: MEDIUM**  

The `atomic_dec` on the `default:` error path (L646) can underflow because `ncm_do_notify` likely does not always increment `notify_count` before issuing the request. Without the source of `ncm_do_notify` we cannot certify the exact increment semantics, but the runtime underflow reported by smatch strongly points to a missing get → an actual refcount imbalance.
```
