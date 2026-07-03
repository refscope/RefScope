# REAL BUG: drivers/net/wireless/mediatek/mt76/mcu.c:134 mt76_mcu_skb_send_and_get_msg()

**Confidence**: HIGH | **Counter**: `$->users.refs.counter`

## Reasoning

| L113‑127 | normal exit through loop | YES (initial skb_get) | YES (out label) | ✅ | retries maintain balance via extra get+send_msg |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L83  | early return -EIO | NO (orig_skb = NULL) | NO  | ✅ | before lock, no orig_skb assignment |
| L94  | goto out (prepare_msg error) | NO (skb_get never called) | YES (dev_kfree_skb(orig_skb)) | ❌ **EXCESS PUT** | orig_skb = skb, no extra reference taken, put drops caller's reference |
| L102 | goto out (send_msg error) | YES (skb_get at L100) | YES (dev_kfree_skb at L131) | ✅ | get+put balanced |
| L107 | goto out (!wait_resp) | YES | YES | ✅ | balanced |
| L113‑127 | normal exit through loop | YES (initial skb_get) | YES (out label) | ✅ | retries maintain balance via extra get+send_msg |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When `mcu_skb_prepare_msg` returns an error, `orig_skb` is set to the incoming `skb` without a prior `skb_get`, then `dev_kfree_skb(orig_skb)` at the `out` label performs a put on a reference that the function did not acquire, causing an excess put. The caller expects to still own the `skb` on error, leading to a double‑free or refcount underflow.
```
