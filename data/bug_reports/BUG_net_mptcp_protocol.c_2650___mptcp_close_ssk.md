# REAL BUG: net/mptcp/protocol.c:2650 __mptcp_close_ssk()

**Confidence**: HIGH | **Counter**: `$->sk_refcnt.refs.counter`

## Reasoning

**: The contract for `__tcp_close` states that the `sock_hold` get is **conditional** (may not execute on all paths). The subsequent `__sock_put(ssk)` is unconditional. On paths where `__tcp_close` did *not* acquire the extra reference, the `__sock_put` drops a non-existent reference → excess put.

## Full Response

```
| Line | Return Type | GET Done? (__tcp_close sock_hold) | PUT Done? (__sock_put) | Balanced? | Notes |
|------|-------------|----------------------------------|------------------------|-----------|-------|
| L2580 | `goto out_release` (early condition true) | NO | NO | ✅ | __tcp_close not called, __sock_put not executed |
| L2593 | `goto out` (`!dispose_it`) | NO | NO | ✅ | skips __tcp_close and __sock_put |
| L2598 | `out_release` (dispose_it, ulp_ops NULL) | NO | NO | ✅ | no __tcp_close, no __sock_put |
| L2600-2602 | `out_release` (dispose_it, ulp_ops present) | **CONDITIONAL** (contract: `conditional_on_path`) | **YES** (unconditional) | ❌ EXCESS PUT | `__sock_put(ssk)` runs even if `__tcp_close` didn’t call `sock_hold` |

**Key**: The contract for `__tcp_close` states that the `sock_hold` get is **conditional** (may not execute on all paths). The subsequent `__sock_put(ssk)` is unconditional. On paths where `__tcp_close` did *not* acquire the extra reference, the `__sock_put` drops a non-existent reference → excess put.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`__tcp_close` get is conditional per contract; the unconditional `__sock_put(ssk)` immediately after it in the `icsk_ulp_ops` non‑NULL branch causes an excess put when the get was skipped.
```
