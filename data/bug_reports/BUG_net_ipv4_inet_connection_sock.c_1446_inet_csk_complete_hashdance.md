# REAL BUG: net/ipv4/inet_connection_sock.c:1446 inet_csk_complete_hashdance()

**Confidence**: HIGH | **Counter**: `sk->sk_refcnt.refs.counter`

## Reasoning

| L1445 (sk==listener, queue_add fail) | return NULL | NO | N/A | ✅ | no sock_hold executed. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1424 | return child | YES | YES (transferred) | ✅ | ref moved to nreq, released on request destruction. |
| L1431 | return child | NO | N/A | ✅ | no sock_hold on this path. |
| L1417→L1445 | return NULL | YES (L1413) | NO | ❌ LEAK | clone failed, goto child_put has no sock_put(sk). |
| L1428→L1445 | return NULL | YES (L1413) | NO | ❌ LEAK | queue_add failed, fallthrough to child_put, no sock_put(sk). |
| L1445 (own_req false) | return NULL | NO | N/A | ✅ | no sock_hold executed. |
| L1445 (sk==listener, queue_add fail) | return NULL | NO | N/A | ✅ | no sock_hold executed. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
sock_hold(sk) at L1413 unconditional, both error paths via child_put return NULL without sock_put(sk), leaking reference.
```
