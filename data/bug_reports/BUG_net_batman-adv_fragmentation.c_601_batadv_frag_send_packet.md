# REAL BUG: net/batman-adv/fragmentation.c:601 batadv_frag_send_packet()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L600+ (fallthrough) | success return | YES | YES | ✅ | falls through put_primary_if |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L494 | error return | NO (before get) | N/A | ✅ | |
| L503 | goto free_skb | NO (before get) | N/A | ✅ | |
| L509 | goto free_skb | NO (get returned NULL) | N/A | ✅ | primary_if is NULL, put not needed |
| L517 | goto free_skb | YES | NO | ❌ LEAK | primary_if ref held, goto free_skb skips put |
| L549-551 (while) | goto put_primary_if | YES | YES | ✅ | put_primary_if calls batadv_hardif_put |
| L585 | goto put_primary_if | YES | YES | ✅ | |
| L600+ (fallthrough) | success return | YES | YES | ✅ | falls through put_primary_if |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
goto free_skb at L517 after successful batadv_primary_if_get_selected leaks a reference because free_skb label does not call batadv_hardif_put.
```
