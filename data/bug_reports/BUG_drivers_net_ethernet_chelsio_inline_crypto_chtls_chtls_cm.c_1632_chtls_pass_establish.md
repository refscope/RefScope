# REAL BUG: drivers/net/ethernet/chelsio/inline_crypto/chtls/chtls_cm.c:1632 chtls_pass_establish()

**Confidence**: HIGH | **Counter**: `$->sk_user_data->kref.refcount.refs.counter`

## Reasoning

alised (0). A later `kref_put` on this counter will underflow, triggering the “refcount excess put” warning. The warning’s line 1632 corresponds to the final `return 0` after the `unlock` label—smatch reports the imbalance at the function exit point where the refcount state becomes problematic.

## Full Response

```
## Path Table

| Line | Return Type    | GET Done? | PUT Done? | Balanced? | Notes                                                                 |
|------|---------------|-----------|-----------|-----------|-----------------------------------------------------------------------|
| L1580 | early return (no sk) | NO (no GET) | N/A       | ✅ (no ref held) | No sk, so no csk → no refcount operations on sk_user_data.            |
| L1584 | fall‑through to `unlock`  | NO (no GET) | N/A       | ❌ BALANCE MISMATCH | sock_owned_by_user true → kfree_skb, skip add_pass_open_to_parent → refcount left unset. |
| L1607 | goto unlock (`!data`)   | NO (no GET) | N/A       | ❌ BALANCE MISMATCH | lookup_stid fails → skip add_pass_open_to_parent.                      |
| L1614 | goto unlock (synq empty) | NO (no GET) | N/A       | ❌ BALANCE MISMATCH | skb_queue_empty → skip add_pass_open_to_parent.                       |
| L1619 | success path (add_pass_open) | YES        | N/A       | ✅ (GET sets refcount) | add_pass_open_to_parent called → refcount_set to 1.                   |
| L1626 | backlog path (bl_add_pass) | YES (deferred) | N/A    | ✅ (GET will happen) | skb queued with bl_add_pass_open_to_parent → refcount_set later.      |

**Note:** The GET operation is the `refcount_set` inside `add_pass_open_to_parent`, which initialises the `kref` counter to a non‑zero value (e.g., 1). Paths where `add_pass_open_to_parent` is skipped leave the counter uninitialised (0). A later `kref_put` on this counter will underflow, triggering the “refcount excess put” warning. The warning’s line 1632 corresponds to the final `return 0` after the `unlock` label—smatch reports the imbalance at the function exit point where the refcount state becomes problematic.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
Missing `add_pass_open_to_parent` on error paths (sock_owned_by_user, lookup_stid fails, synq empty) leaves `sk->sk_user_data->kref` uninitialised (0), causing a later `kref_put` to underflow—an “excess put”.
```
