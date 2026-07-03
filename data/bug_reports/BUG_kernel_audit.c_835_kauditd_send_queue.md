# REAL BUG: kernel/audit.c:835 kauditd_send_queue()

**Confidence**: HIGH | **Counter**: `$->users.refs.counter`

## Reasoning

| L824 (success, `consume_skb(skb)`) | Normal flow | YES (skb_get at L810) | YES (consume_skb at L824) | ✅ | Extra reference dropped correctly. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| While loop exit (skb==skb_tail or NULL dequeue) → return L828 | Normal return | NO (no get on final iteration) | N/A | ✅ | Loop terminated; no unreleased skb held at exit if all earlier iterations balanced. |
| L805 (continue when `!sk`) | Continue (skip iteration) | NO (before any get) | N/A | ✅ | No skb_get, no reference acquired. |
| L822 (`goto retry`) | Goto retry (loop back) | YES (skb_get at L810) | ⚠️ netlink_unicast consumes one ref, but extra ref remains for retry | N/A | Not a leak itself; the extra reference is intentionally kept for the next attempt. The leak occurs only if a later fatal error path fails to drop it. |
| **L820 (continue after fatal error)** | **Continue (abandon skb)** | **YES (skb_get at L810)** | **NO** **(consume_skb missing)** | **❌ LEAK** | **skb_get added an extra reference; netlink_unicast consumed the original but not the extra. The error path skips consume_skb → extra reference leaked, skb never freed.** |
| L824 (success, `consume_skb(skb)`) | Normal flow | YES (skb_get at L810) | YES (consume_skb at L824) | ✅ | Extra reference dropped correctly. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`skb_get()` unconditionally increments the refcount before `netlink_unicast()`. On fatal send errors (retry limit exhausted or `ECONNREFUSED`/`EPERM`) the error path `continue`s without calling `consume_skb()`, permanently leaking the extra reference and the `sk_buff`.
```
