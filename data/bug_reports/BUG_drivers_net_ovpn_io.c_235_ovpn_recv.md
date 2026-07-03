# REAL BUG: drivers/net/ovpn/io.c:235 ovpn_recv()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L237–240 (success) | success (implicit return) | NO | NO | ✅ | No put, no get – balanced, caller retains reference |

## Full Response

```
| Line | Return Type | GET Done? (peer) | PUT Done? (peer) | Balanced? | Notes |
|------|-------------|------------------|------------------|-----------|-------|
| L226–235 (error) | error return | NO (no peer get in function) | YES (ovpn_peer_put at L235) | ❌ Excess Put | Put without matching get – refcount goes below zero when caller later releases its own reference |
| L237–240 (success) | success (implicit return) | NO | NO | ✅ | No put, no get – balanced, caller retains reference |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`ovpn_recv` calls `ovpn_peer_put(peer)` on the error path (L235) without any corresponding peer get in the function, causing an excess put when the caller later releases its own reference.
```
