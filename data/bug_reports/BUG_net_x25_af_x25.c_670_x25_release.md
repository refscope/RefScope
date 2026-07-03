# REAL BUG: net/x25/af_x25.c:670 x25_release()

**Confidence**: HIGH | **Counter**: `sk->sk_refcnt.refs.counter`

## Reasoning

| L664 (case STATE_1/3/4 break → out) | success (via out) | YES (sock_hold) | YES (sock_put at out) | ✅ | only one put, balanced |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L636 (if (!sk) return 0) | error (none) | NO (before sock_hold) | N/A | ✅ | early return, no refs |
| L655 (case STATE_0/2) goto out | success (via out) | YES (sock_hold) | YES (sock_put at out) + YES (__x25_destroy_socket internal put) | ❌ **EXCESS PUT** | two puts for one hold |
| L668 (case STATE_5) goto out | success (via out) | YES (sock_hold) | YES (sock_put at out) + YES (__x25_destroy_socket internal put) | ❌ **EXCESS PUT** | same double put |
| L664 (case STATE_1/3/4 break → out) | success (via out) | YES (sock_hold) | YES (sock_put at out) | ✅ | only one put, balanced |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
x25_release acquires one extra reference via `sock_hold`, but in state 0/2/5 paths, both `__x25_destroy_socket` (which performs its own `__sock_put`) and the final `sock_put` at `out` release references, resulting in an excess put.
```
