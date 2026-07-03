# REAL BUG: net/bluetooth/l2cap_core.c:4520 l2cap_disconnect_req()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

L4523 | success     | YES (get succeeded) | YES (explicit l2cap_chan_put at L4522) | ❌ EXCESS PUT if `close` also puts | `l2cap_chan_del` does **not** put (clears timers only); `chan->ops->close` very likely calls `l2cap_chan_put`, resulting in a double put on the only path that reaches the end |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4487 | error       | NO (before get) | N/A  | ✅ | |
| L4513 | success     | NO (get failed, chan NULL) | N/A  | ✅ | IS_NULL guard |
| L4523 | success     | YES (get succeeded) | YES (explicit l2cap_chan_put at L4522) | ❌ EXCESS PUT if `close` also puts | `l2cap_chan_del` does **not** put (clears timers only); `chan->ops->close` very likely calls `l2cap_chan_put`, resulting in a double put on the only path that reaches the end |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`chan->ops->close` is expected to release its own reference (via `l2cap_chan_put`), making the final explicit `l2cap_chan_put` redundant and triggering a refcount under‑flow (excess put).
```
