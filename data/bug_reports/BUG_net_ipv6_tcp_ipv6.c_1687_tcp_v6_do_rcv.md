# REAL BUG: net/ipv6/tcp_ipv6.c:1687 tcp_v6_do_rcv()

**Confidence**: HIGH | **Counter**: `$->users.refs.counter`

## Reasoning

rd`. The `discard` label calls `sk_skb_reason_drop` on the same skb, causing a second release. This refcount underflow triggers the **EXCESS PUT** warning. The `!nsk` leak is a separate missing-put issue, but the excess put paths are clearly reachable and constitute a use-after-free / double-free.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1550 (skb->protocol == ETH_P_IP) → L1550 return tcp_v4_do_rcv | return | YES (initial ref) | YES (tcp_v4_do_rcv consumes) | ✅ | |
| L1555 (psp check fail) → goto err_discard → discard | goto (error) | YES | YES (sk_skb_reason_drop) | ✅ | |
| L1578 (ESTABLISHED, no opt_skb) → return 0 | return | YES | YES (tcp_rcv_established) | ✅ | |
| L1578 (ESTABLISHED, opt_skb) → goto ipv6_pktoptions | goto (ipv6_pktoptions) | YES | YES (tcp_rcv_established) | ✅ | original skb consumed, only opt_skb processed |
| L1582 (csum_err) → goto csum_err → discard | goto (error) | YES | YES (sk_skb_reason_drop) | ✅ | |
| L1605 (!nsk) → return 0 | return | YES | NO | ⚠️ **LEAK** (missing put) | skb reference lost, but warning is *excess* put |
| L1608-1609 (nsk != sk, reason == 0) → return 0 | return | YES | YES (tcp_child_process consumes) | ✅ | |
| L1608, L1610 → goto reset → discard | goto→reset→discard | YES | YES (tcp_child_process) then YES (sk_skb_reason_drop) | ❌ **EXCESS PUT** | tcp_child_process already consumed skb, then discard drops again |
| L1614 (nsk == sk, reason == 0, opt_skb?) → return 0 | return | YES | YES (tcp_rcv_state_process) | ✅ | one put, balanced |
| L1614, L1616 (nsk == sk, reason → goto reset → discard) | goto→reset→discard | YES | YES (tcp_rcv_state_process) then YES (sk_skb_reason_drop) | ❌ **EXCESS PUT** | same double-put |
| L1619-1621 (non-LISTEN, reason → goto reset → discard) | goto→reset→discard | YES | YES (tcp_rcv_state_process) then YES (sk_skb_reason_drop) | ❌ **EXCESS PUT** | same double-put |
| L1687 (ipv6_pktoptions → consume_skb) | return | N/A (original skb already consumed) | N/A (only opt_skb) | ✅ | |

**Explanation:** The contracts show `tcp_rcv_state_process` and `tcp_child_process` unconditionally consume the skb (PUT). When a reason (error) is returned, these paths `goto reset`, which falls through to `discard`. The `discard` label calls `sk_skb_reason_drop` on the same skb, causing a second release. This refcount underflow triggers the **EXCESS PUT** warning. The `!nsk` leak is a separate missing-put issue, but the excess put paths are clearly reachable and constitute a use-after-free / double-free.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`tcp_child_process` and `tcp_rcv_state_process` consume the skb, yet error paths `goto reset` → `discard` call `sk_skb_reason_drop` again, double-dropping the skb.
```
