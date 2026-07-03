# REAL BUG: drivers/net/ethernet/chelsio/inline_crypto/chtls/chtls_cm.c:396 chtls_close()

**Confidence**: HIGH | **Counter**: `sk->sk_refcnt.refs.counter`

## Reasoning

| 3    | `goto out` NOT taken **and** `sk->sk_state != TCP_CLOSE` at L383 | YES | YES (`sock_put` at out) | ✅ | No extra destroy, single put |

## Full Response

```
## Path Table

| Path | Conditions | GET Done? | PUT Done? | Balanced? | Notes |
|------|------------|-----------|-----------|-----------|-------|
| 1    | `goto out` at L370 taken: `prev_state != TCP_CLOSE && sk->sk_state == TCP_CLOSE` | YES (`sock_hold` at L364) | YES (`sock_put` at out) | ✅ | Single put, no early destroy call |
| 2    | `goto out` NOT taken (i.e. `prev_state == TCP_CLOSE`) **and** `sk->sk_state == TCP_CLOSE` at L383 | YES | **DOUBLE PUT**: `inet_csk_destroy_sock` (L383) does `sock_put`, then `sock_put` at out | ❌ **EXCESS** | `inet_csk_destroy_sock` contract says unconditional `sock_put` → two puts for one get |
| 3    | `goto out` NOT taken **and** `sk->sk_state != TCP_CLOSE` at L383 | YES | YES (`sock_put` at out) | ✅ | No extra destroy, single put |

## VERDICT: REAL_BUG

## CONFIDENCE: HIGH

**Reasoning:** `sock_hold` at L364 always executes (unconditional get). When `prev_state == TCP_CLOSE` (skipping the `goto out` at L370) and `sk_state` remains `TCP_CLOSE`, the code calls `inet_csk_destroy_sock(sk)` which performs a `sock_put`, then falls through to `out:` where another `sock_put(sk)` is called. This results in a double put (excess put) on the socket reference count.
```
