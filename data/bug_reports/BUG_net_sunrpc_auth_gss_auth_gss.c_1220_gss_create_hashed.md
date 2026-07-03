# REAL BUG: net/sunrpc/auth_gss/auth_gss.c:1220 gss_create_hashed()

**Confidence**: HIGH | **Counter**: `new->kref.refcount.refs.counter`

## Reasoning

## Request for Missing Source

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (gss_create_new) | PUT Done? (gss_destroy) | Balanced? | Notes |
|------|-------------|----------------------------|-------------------------|-----------|-------|
| L1209 | `goto out` (found existing) | NO (new not yet created) | N/A | ✅ | First call to `gss_auth_find_or_add_hashed` with `NULL` found an existing auth; no new object involved. |
| L1213 | `return new` (IS_ERR) | NO (creation failed) | N/A | ✅ | `gss_create_new` returned ERR_PTR, no object created. |
| L1216-1217 → L1220 → `goto out` | `gss_auth != new` branch | YES (`new` created, refcount = 1) | YES (`gss_destroy` called) | ⚠️ **Dependent on callee** | Whether `gss_auth_find_or_add_hashed` already put `new` determines if this is an excess put. Both `gss_auth` as an existing auth or as an error pointer fall into this branch. |
| L1216 (else) → `goto out` | `gss_auth == new` (successfully added) | YES | NO (transfer to caller) | ✅ | Reference transferred; caller now owns the refcount. |

## Analysis

- The warning is a **refcount excess put** on `new->kref.refcount.refs.counter` at line 1220, which corresponds to `gss_destroy(&new->rpc_auth)`.
- The path that triggers the put is the `gss_auth != new` branch after calling `gss_auth_find_or_add_hashed`.  
- The initial reference count (1) is acquired unconditionally by `gss_create_new`.  
- Whether `gss_destroy` is a correct put or an excess put depends entirely on the internal behaviour of `gss_auth_find_or_add_hashed` when it **does not insert `new`**:
    - If the function **never releases** `new` (i.e., leaves the reference intact), the explicit `gss_destroy` is correct → **false positive**.
    - If the function **already releases** `new` (e.g., on error or when an existing entry is found), then the caller’s `gss_destroy` is a double-put → **real bug**.
- The caller’s code explicitly handles the release of `new`, suggesting the intended contract is that `gss_auth_find_or_add_hashed` **does not** consume the reference when it returns an object other than `new`. However, the smatch checker traces inter-procedural refcount flows and may have detected an internal put, leading to the excess-put warning.

## Request for Missing Source

[NEED_SOURCE] gss_auth_find_or_add_hashed

## VERDICT: UNCLEAR

CONFIDENCE: HIGH  

**Reason:** The correctness of the refcount put depends on the internal refcount handling of `gss_auth_find_or_add_hashed`, whose source is not provided. Without inspecting that function, we cannot determine whether it already releases `new` on the non-insertion path, making the caller's `gss_destroy` an excess put (real bug) or a required release (false positive).

--- [NEED_SOURCE r1] ---

## Path Table

| Line | Return Type | GET Done? (gss_create_new) | PUT Done? (gss_destroy) | Balanced? | Notes |
|------|-------------|----------------------------|-------------------------|-----------|-------|
| L1207 | `goto out` (IS_ERR(new)) | NO (new is ERR_PTR) | N/A | ✅ | `gss_cre
```
