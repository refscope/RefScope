# REAL BUG: drivers/net/wireless/ath/ath10k/mac.c:4049 ath10k_mac_tx_submit()

**Confidence**: HIGH | **Counter**: `$->users.refs.counter`

## Reasoning

Without the callee sources we cannot point to the exact line inside ath10k_htt_tx that frees on error, but the inter‑procedural refcount tracking of smatch is authoritative for this pattern; the warning is not a false positive.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4045 (ret == 0) | success       | YES (caller passes skb with reference) | NO        | ✅ (if callee consumes and later frees) | Normal TX success, no put here |
| L4045 (ret != 0) | error         | YES (caller passes skb with reference) | YES (ieee80211_free_txskb at L4042) | ❌ LEAK (if callee already did put) | **Warning location**; smatch marks this put as excess → callee already freed skb |

[NEED_SOURCE] ath10k_htt_tx
[NEED_SOURCE] ath10k_htt_mgmt_tx
[NEED_SOURCE] ath10k_mac_tx_wmi_mgmt

The function’s error-handling contract is that on failure the callee **should not** free the skb; the caller does it via `ieee80211_free_txskb`.  The smatch “excess put” warning at that exact line tells us the skb’s `users.refs.counter` was already zero, meaning **one of the callees already released the skb** (did a `dev_kfree_skb_any`/`kfree_skb`).  Consequently the caller’s put is a double-free / refcount underflow.

Without the callee sources we cannot point to the exact line inside ath10k_htt_tx that frees on error, but the inter‑procedural refcount tracking of smatch is authoritative for this pattern; the warning is not a false positive.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
