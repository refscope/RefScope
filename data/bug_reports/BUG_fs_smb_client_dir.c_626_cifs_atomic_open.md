# REAL BUG: fs/smb/client/dir.c:626 cifs_atomic_open()

**Confidence**: HIGH | **Counter**: `$->tl_count.counter`

## Reasoning

| L610 | success path (fall through to out) | ? | YES | ❌ if GET=NO | same |

## Full Response

```
[NEED_SOURCE] cifs_sb_tlink

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L519 | error (cifs_forced_shutdown) | NO (before get) | N/A | ✅ | |
| L535 | error (negative dentry -ENOENT) | NO (before get) | N/A | ✅ | |
| L537 | finish_no_open return | NO (before get) | N/A | ✅ | |
| L551 | IS_ERR(tlink) goto out_free_xid | NO (get failed) | NO | ✅ | |
| L557 | check_name failure goto out | ? (conditional get may not have taken ref) | YES (cifs_put_tlink at L626) | ❌ if GET=NO | unconditional put → excess when get skipped |
| L570 | cifs_do_create failure goto out | ? | YES | ❌ if GET=NO | same |
| L585 | finish_open failure goto out | ? | YES | ❌ if GET=NO | same |
| L600 | cifs_new_fileinfo NULL goto out | ? | YES | ❌ if GET=NO | same |
| L610 | success path (fall through to out) | ? | YES | ❌ if GET=NO | same |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
cifs_sb_tlink() may return a tlink without incrementing tl_count (contract: conditional_on_path), but all subsequent paths in cifs_atomic_open() unconditionally call cifs_put_tlink() at L626, causing a refcount underflow (excess put) when the get was skipped.

--- [NEED_SOURCE r1] ---

Now that we have the source for `cifs_sb_tlink`, it is clear: **every non‑error return gives the caller a reference** (`cifs_get_tlink` is unconditionally called on the tlink that is returned). Therefore, in `cifs_atomic_open` the call `tlink = cifs_sb_tlink(cifs_sb)` either returns a valid pointer (ref held) or an `ERR_PTR` (no ref). The cleanup at the `out` label does `cifs_put_tlink(tlink)`, which is **only reached when `tlink` is non‑NULL and valid** — it correctly releases the reference. The early error path that sets `tlink = NULL` after an `IS_ERR` check goes to `out_free_xid`, which does not call `cifs_put_tlink` (because the pointer is `NULL`). All paths are balanced.

Here is the complete path table for `cifs_atomic_open`:

| Line | Return Type | GET Done? (tlink ref held?) | PUT Done? | Balanced? | Notes |
|------|-------------|-----------------------------|-----------|-----------|-------|
| L519 (cifs_forced_shutdown) | error (before tlink assignment) | NO | N/A | ✅ | |
| L535 (negative dentry) | error (before tlink assignment) | NO | N/A | ✅ | |
| L537 (finish_no_open) | return (before tlink assignment) | NO | N/A | ✅ | |
| L551 (IS_ERR(tlink) → tlink=NULL, goto out_free_xid) | error | NO (get failed, tlink is ERR_PTR) | NO (tlink set NULL) | ✅ | |
| L557 (check_name failure → goto out) | error | YES (tlink is valid, ref held) | YES (out: cifs_put_tlink) | ✅ | |
| L570 (cifs_do_create failure → goto out) | error | YES | YES | ✅ | |
| L585 (finish_open failure → goto out) | error | YES | YES | ✅ | |
| L600 (cifs_new_fileinfo NULL → goto out) | error | YES | YES | ✅ | |
| L610 (success fall‑through to out) | success | YES | YES | ✅ | normal cleanup path, includes cifs_put_tlink |

VERDICT: FALSE_POSITIVE
CONFIDENCE: HIGH  
`
```
