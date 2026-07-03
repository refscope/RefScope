# REAL BUG: net/llc/llc_conn.c:175 llc_conn_state_process()

**Confidence**: HIGH | **Counter**: `$->users.refs.counter`

## Reasoning

| default (ind_prim unhandled) → `out_skb_put` | success | NO | YES (L175) | ✅ | Same. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L68 `goto out_skb_put` (llc_conn_service failure) | error (rc != 0) | NO (no skb_get) | YES (L175 `kfree_skb(skb)`) | ❌ EXCESS PUT | If `llc_conn_service` already freed `skb` on failure, then `kfree_skb` at L175 is a double‑free → refcount underflow. |
| L98 error block (LLC_DATA_PRIM error, `sock_queue_rcv_skb` fails), then fall‑through to `out_skb_put` | success (rc=0) | YES (skb_get at L93) | YES (L98 `kfree_skb` + L175 `kfree_skb`) | ✅ | Two puts balance: initial ref stays (sock_queue_rcv_skb does not consume on error) and extra ref from `skb_get`. |
| LLC_DATA_PRIM success (`sock_queue_rcv_skb` returns 0) → `out_skb_put` | success | YES (skb_get) | YES (L175 only) | ✅ | `sock_queue_rcv_skb` consumes initial ref; `skb_get` extra ref dropped at L175. |
| LLC_CONN_PRIM → `out_skb_put` | success | YES (skb_get) | YES (L175) | ✅ | `skb_get` extra ref dropped at L175; initial ref transferred to queue. |
| LLC_DISC_PRIM → `out_skb_put` | success | NO | YES (L175) | ✅ | L175 drops initial ref. |
| LLC_RESET_PRIM → `out_skb_put` | success | NO | YES (L175) | ✅ | Same. |
| default (ind_prim unhandled) → `out_skb_put` | success | NO | YES (L175) | ✅ | Same. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The `kfree_skb(skb)` at line 175 is a double‑free if `llc_conn_service(sk, skb)` already freed the skb on failure (returning non‑zero). The only path without a prior `skb_get` that could produce an underflow is the `goto out_skb_put` after the error in `llc_conn_service`. The static checker’s “excess put” matches this scenario.
```
