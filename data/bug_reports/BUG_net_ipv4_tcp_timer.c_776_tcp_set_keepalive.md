# REAL BUG: net/ipv4/tcp_timer.c:776 tcp_set_keepalive()

**Confidence**: HIGH | **Counter**: `$->sk_refcnt.refs.counter`

## Reasoning

| L775–L776 (`else if (!val)`) | return | NO (no get in this path) | YES (`tcp_delete_keepalive_timer` releases ref) | ❌ EXCESS PUT | `val==0` triggers PUT without any preceding GET when keepalive was never enabled |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L770 | return (early) | NO (before any get/put) | NO | ✅ | socket in CLOSE/LISTEN state |
| L773–L774 (end of `if` block) | fall-through return | YES (`tcp_reset_keepalive_timer` called) | NO | N/A | timer holds the reference; put happens later when timer expires or is deleted |
| L775–L776 (`else if (!val)`) | return | NO (no get in this path) | YES (`tcp_delete_keepalive_timer` releases ref) | ❌ EXCESS PUT | `val==0` triggers PUT without any preceding GET when keepalive was never enabled |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When `val == 0`, `tcp_delete_keepalive_timer()` unconditionally releases a socket reference that may not have been acquired, causing a refcount excess put.
```
