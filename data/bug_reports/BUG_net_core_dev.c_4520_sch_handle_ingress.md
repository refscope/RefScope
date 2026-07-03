# REAL BUG: net/core/dev.c:4520 sch_handle_ingress()

**Confidence**: HIGH | **Counter**: `$->users.refs.counter`

## Reasoning

| TC_ACT_STOLEN/QUEUED/TRAP → `consume_skb` → fallthrough to CONSUMED → return NULL | return NULL | YES | YES (put) | ⚠️ single put may not release the extra get | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| early !entry return (≈L4474) | returns skb | NO | N/A | ✅ | |
| After switch, sch_ret default / REDIRECT‑EAGAIN break → return skb (≈L4520) | return skb | YES (if *pt_prev was non‑NULL, `deliver_skb` called) | NO | ❌ LEAK | `deliver_skb` unconditionally incs refcount; returning skb without a put leaks that reference |
| Same return skb, but *pt_prev was NULL | return skb | NO | N/A | ✅ | |
| TC_ACT_REDIRECT success → `skb_do_redirect` → return NULL | return NULL | YES (if *pt_prev non‑NULL) | YES (`skb_do_redirect` does a put) | ⚠️ single put may not release the extra get | |
| TC_ACT_SHOT → `kfree_skb_reason` → return NULL | return NULL | YES | YES (put) | ⚠️ single put may not release the extra get | |
| TC_ACT_STOLEN/QUEUED/TRAP → `consume_skb` → fallthrough to CONSUMED → return NULL | return NULL | YES | YES (put) | ⚠️ single put may not release the extra get | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`deliver_skb` unconditionally increments the skb refcount; the path where *pt_prev was non‑NULL, sch_ret is not consumed (default case), and the function returns `skb` without a matching put leaks one reference.
```
