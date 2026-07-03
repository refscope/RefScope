# REAL BUG: drivers/net/ethernet/chelsio/inline_crypto/ch_ktls/chcr_ktls.c:1745 chcr_end_part_handler()

**Confidence**: MEDIUM | **Counter**: `$->users.refs.counter`

## Reasoning

e free and an excess put (refcount goes from 0 to -1). This matches the warning and is a common driver bug. The contract provided only documents a `skb_get`, not a put, but the warning indicates an internal put must exist.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1705 | error (alloc fail) | NO (before any get) | YES (dev_kfree_skb_any(skb)) | ✅ | frees the caller’s skb; correct |
| L1737 | success (xmit ok) | YES* (conditional get inside xmit) | NO | ⚠️ LEAK if get happened | caller will release; extra ref from skb_get is a leak, not an excess put |
| L1740 | error (goto out) after xmit failure, with nskb==skb (first branch) | YES* (conditional get) | YES (dev_kfree_skb_any(nskb)) | ⚠️ LEAK if get happened, else fine | no double free in this function |
| L1740 | error after nskb alloc (else branch, last_wr true, xmit fails) | YES* | YES (skb freed at L1718, nskb freed at L1739) | ✅ (no double free) | skb freed once, nskb freed once |
| L1740 | error after nskb alloc (else branch, last_wr false, xmit fails) | YES* | YES (skb freed at L1733, nskb freed at L1739) | ✅ (no double free) | skb freed once, nskb freed once |

* GET from `chcr_ktls_xmit_wr_complete` is conditional (skb_get). Table assumes no internal put by that function. With no internal put, the function’s own puts are balanced; no excess put occurs inside `chcr_end_part_handler`. The warning “refcount excess put” at line 1745 (likely corresponding to the `dev_kfree_skb_any(nskb)` at out label) cannot be explained by the visible code – it requires an extra decrement before this put so that the refcount goes negative.

**Root cause analysis**: The most plausible explanation is that `chcr_ktls_xmit_wr_complete`, on failure, **already frees the passed skb** (e.g., via kfree_skb) and returns an error. The caller then calls `dev_kfree_skb_any(nskb)` again, leading to a double free and an excess put (refcount goes from 0 to -1). This matches the warning and is a common driver bug. The contract provided only documents a `skb_get`, not a put, but the warning indicates an internal put must exist.

`[NEED_SOURCE] chcr_ktls_xmit_wr_complete` required for full confirmation.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`chcr_ktls_xmit_wr_complete` likely frees `nskb` on error, causing a double free when `chcr_end_part_handler` also calls `dev_kfree_skb_any(nskb)` at the `out` label (line ~1740).
```
