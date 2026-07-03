# REAL BUG: net/bluetooth/l2cap_core.c:1815 l2cap_conn_del()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

- This yields one reference held but two released – an **excess put**, triggering the `refcount excess put` warning on `chan->kref`.

## Full Response

```
| Line | Return Type | GET Done? (chan) | PUT Done? (chan) | Balanced? | Notes |
|------|-------------|------------------|-------------------|-----------|-------|
| L1770 | early return (conn == NULL) | N/A (no chan involved) | N/A | ✅ | No channel operations |
| L1803–L1812 | loop iteration (implicit, no return inside) | YES – l2cap_chan_hold (L1803) | YES – l2cap_chan_del (L1805, contract‑marked PUT) | ❌ | l2cap_chan_del is a PUT → drops the connection’s reference |
| L1809 | inside same iteration | already YES | YES – l2cap_chan_put (L1809) | ❌ BALANCE = -1 | extra put: one hold, two puts → excess kref_put |
| L1812 | end of function | N/A | N/A | ✅ | l2cap_conn_put(conn) only, no channel get |

**Details**  
- The loop acquires one reference with the unconditional `l2cap_chan_hold()`.  
- The contract states `l2cap_chan_del()` is a PUT (purity=low). It likely releases the reference that the connection list (`conn->chan_l`) holds on the channel.  
- After `l2cap_chan_del()`, the loop calls `l2cap_chan_put()`, causing a second put on the same kref.  
- This yields one reference held but two released – an **excess put**, triggering the `refcount excess put` warning on `chan->kref`.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The contract marks `l2cap_chan_del` as a PUT, and the loop performs an additional explicit `l2cap_chan_put`, creating a double-put on the channel’s kref.
```
