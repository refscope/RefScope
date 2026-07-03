# REAL BUG: fs/smb/client/dir.c:1165 cifs_tmpfile()

**Confidence**: HIGH | **Counter**: `tlink->tl_count.counter`

## Reasoning

No ownership transfer or deferred release applies to the paths after `cifs_new_fileinfo()` — the function must *not* put its own reference.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1064 | early return (forced shutdown) | NO (before get) | N/A | ✅ | tlink not acquired yet |
| L1067 | error return (IS_ERR) | NO (get failed) | N/A | ✅ | cifs_sb_tlink() returned error, no ref held |
| L1074 | goto out (protocol check) | YES | YES (at L1146) | ✅ | error path before cfile, put is correct |
| L1085 | goto out (alloc_parent_path error) | YES | YES (at L1146) | ✅ | error path, put is correct |
| L1112 | goto err_open (d_mark_tmpfile_name error) | YES | YES (out via goto out) | ✅ | err_open → goto out → put is correct |
| L1120 | goto out (create loop error) | YES | YES (at L1146) | ✅ | error path, put is correct |
| L1125 | goto err_open (finish_open error) | YES | YES (out via goto out) | ✅ | error path, put is correct |
| L1139 | goto err_open (cifs_new_fileinfo fails) | YES | YES (out via goto out) | ✅ | cfile == NULL, no extra ref taken, put is correct |
| L1143 | goto out (set_tmpfile_attr fails) | YES | YES (at L1146) | ❌ EXTRA PUT | cfile ≠ NULL → tlink ref already held by file info, double-put |
| L1146 (fallthrough) | return rc (success) | YES | YES (at L1146) | ❌ EXTRA PUT | success path, tlink ref transferred to cifsFileInfo, double-put |

## Analysis

- **cifs_sb_tlink()** returns a pointer and (conditionally) acquires a reference on success; the `IS_ERR` guard ensures no ref on error.
- **cifs_new_fileinfo()** creates a new file info and internally calls `cifs_get_tlink(tlink)` to hold its own reference. After a successful call, ownership of that extra reference is transferred to the cifsFileInfo, meaning the caller **must not** call `cifs_put_tlink()` for its own original reference (that reference is now effectively “consumed” by the file info).

The `out` label does `cifs_put_tlink(tlink)`, releasing the caller’s reference. This is correct on all error paths **before** `cifs_new_fileinfo()`. However, after `cifs_new_fileinfo()` returns non-NULL (success), the function still reaches `out` (both on error in `set_tmpfile_attr` and on the normal success path). At that point the tlink reference is already held by the file info, so `cifs_put_tlink()` at `out` results in a **double release**, causing the refcount to drop below zero (underflow). This matches the smatch “inconsistent refcounting” at line 1146 (the `cifs_put_tlink()` line).

No ownership transfer or deferred release applies to the paths after `cifs_new_fileinfo()` — the function must *not* put its own reference.

## VERDICT: REAL_BUG  
## CONFIDENCE: HIGH  
**After cifs_new_fileinfo(), the caller still executes cifs_put_tlink() at the shared out label, releasing a reference already owned by the file info, leading to a refcount underflow (double-put).**
```
