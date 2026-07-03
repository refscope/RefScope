# REAL BUG: net/bluetooth/l2cap_core.c:1524 l2cap_conn_start()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

No additional source needed—the contract for `l2cap_chan_ready()` clearly states it is a PUT.

## Full Response

```
The warning indicates a refcount excess put on the kref counter at line 1524 of `l2cap_conn_start()`. The line 1524 block calls `l2cap_chan_ready(chan)`, which according to the contract is a PUT (→__clear_chan_timer(put)). This put is executed for every channel in the list that is not connection-oriented, without any matching get inside the function. Since the channel is still present in `conn->chan_l`, which already holds a proper reference, calling an additional put here leads to an unbalanced decrement—i.e., an excess put that will underflow the refcount.

## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1525 (l2cap_chan_ready call inside "chan_type != L2CAP_CHAN_CONN_ORIENTED" branch) | continue (loop iteration ends, function eventually returns) | NO | **YES** (l2cap_chan_ready performs kref_put) | ❌ EXCESS PUT | No get acquired in this path; an extra put is called on a refcount owned by the list. |
| L1538, L1544, L1552 (other branches after state checks) | continue / loop end | Possibly yes (l2cap_chan_close may be a get) | **NO** (no ready call) | ? (potential leak, separate issue) | Not related to the excess put warning. |

## Pre-Verdict Checklist

1. **“Held for device lifetime”?** Not applicable — this is a work/softirq function, not a probe.
2. **“Ownership transferred”?** No transfer documented; default is NO transfer.
3. **Unconditional GET?** No unconditional get is present before the put.
4. **goto out between GET and PUT?** Not applicable — there is no goto, only a direct call to a put.

## Source Request

No additional source needed—the contract for `l2cap_chan_ready()` clearly states it is a PUT.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
