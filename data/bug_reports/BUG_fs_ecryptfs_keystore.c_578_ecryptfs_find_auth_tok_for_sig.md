# REAL BUG: fs/ecryptfs/keystore.c:578 ecryptfs_find_auth_tok_for_sig()

**Confidence**: HIGH | **Counter**: `*$->usage.refs.counter`

## Reasoning

eases a reference via `key_put`). The call occurs only when `ecryptfs_find_global_auth_tok_for_sig` returned -ENOENT, meaning **no key reference was acquired** (conditional get failed). Therefore, the function performs an extra decrement on a key that was never held, causing a refcount excess put.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 570  | error return (-EINVAL) | NO (global get returned -ENOENT, conditional get failed) | NO | ✅ | no reference acquired, put not needed |
| 576  | return rc (global get success, rc=0) | YES (global get succeeded) | NO (no put in this function) | ✅ | caller responsible for key_put |
| 576  | return rc (global get non‑ENOENT error, rc<0) | NO (conditional get failed) | NO | ✅ | no reference held |
| 576  | return rc after L578 call (keyring auth) | NO (global get returned -ENOENT) | YES (L578 is `ecryptfs_keyring_auth_tok_for_sig`, contract says PUT) | ❌ EXCESS PUT | PUT function called with no prior GET → refcount underflow |

L578 is the call to `ecryptfs_keyring_auth_tok_for_sig`. According to the contract, this function is a **PUT** operation (releases a reference via `key_put`). The call occurs only when `ecryptfs_find_global_auth_tok_for_sig` returned -ENOENT, meaning **no key reference was acquired** (conditional get failed). Therefore, the function performs an extra decrement on a key that was never held, causing a refcount excess put.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`ecryptfs_keyring_auth_tok_for_sig` is a PUT per contract; called on the -ENOENT error path without a prior GET → refcount underflow.
```
