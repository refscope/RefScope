# REAL BUG: net/bluetooth/l2cap_sock.c:1565 l2cap_sock_new_connection_cb()

**Confidence**: HIGH | **Counter**: `sk->sk_peer_pid->count.refs.counter`

## Reasoning

| success: return l2cap_pi(sk)->chan (L1565) | success | No (caller never acquires a pid ref) | Yes (bt_accept_enqueue does put_pid unconditionally) | ❌ | PUT without corresponding GET → excess put on sk->sk_peer_pid |

## Full Response

```
| Line/Path | Return Type | GET (pid ref) Done? | PUT (pid ref) Done? | Balanced? | Notes |
|-----------|-------------|----------------------|----------------------|-----------|-------|
| if (!parent) return NULL (L1536) | error (NULL) | No | No | ✅ | no sk created |
| backlog full: release_sock(parent); return NULL (L1540) | error (NULL) | No | No | ✅ | |
| alloc fail: release_sock(parent); return NULL (L1545) | error (NULL) | No | No | ✅ | |
| success: return l2cap_pi(sk)->chan (L1565) | success | No (caller never acquires a pid ref) | Yes (bt_accept_enqueue does put_pid unconditionally) | ❌ | PUT without corresponding GET → excess put on sk->sk_peer_pid |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The contract for `bt_accept_enqueue` states an unconditional `put_pid(put)` on the new socket's peer pid. Before calling it, the function must ensure the pid reference has been properly acquired (e.g., via `get_pid()` in `l2cap_sock_init`). No such acquisition is visible in `l2cap_sock_new_connection_cb`, and the smatch warning indicates the static analyser sees the refcount as zero before the put, confirming the missing get. This leads to a refcount underflow (excess put).
```
