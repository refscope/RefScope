# REAL BUG: fs/smb/client/dir.c:857 cifs_lookup()

**Confidence**: HIGH | **Counter**: `$->tl_count.counter`

## Reasoning

Because the caller cannot distinguish the conditional case (no additional check is present), the unconditional `cifs_put_tlink` invariably triggers a refcount imbalance on the paths where the GET did not happen. This matches the reported “refcount excess put” warning.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L754→L761 | goto free_xid (IS_ERR(tlink)) | NO (GET failed) | NO (skip PUT) | ✅ | tlink is ERR_PTR, no ref, no put needed. |
| L765→L766 | goto put_tlink (check_name fail) | Conditional: may be NO on some paths | YES (cifs_put_tlink called) | ❌ if GET=NO → excess put | GET contract says conditional_on_path; if GET did not happen, calling PUT is an excess put. |
| L780→L781 | goto free_dentry_path→put_tlink (build_path error) | Conditional: may be NO | YES | ❌ if GET=NO → excess put | Same as above. |
| L806→L809 | goto out→free_dentry_path→put_tlink (negative dentry cached valid) | Conditional: may be NO | YES | ❌ if GET=NO → excess put | Same. |
| L823→L856 | falls through out→free_dentry_path→put_tlink (normal/error after get_inode_info) | Conditional: may be NO | YES | ❌ if GET=NO → excess put | Same. |

**Analysis**  
The contract for `cifs_sb_tlink()` states it is **conditional_on_path**. This means on some execution paths the call does **not** increment the refcount (`tl_count.counter`), yet returns a valid (non‑ERR) `tcon_link*`. The code then unconditionally calls `cifs_put_tlink(tlink)` on every path that obtains a non‑ERR pointer (i.e., all paths after the `IS_ERR(tlink)` check). If the GET was not performed, the PUT becomes an “excess put”, decrementing the refcount below its intended value and eventually causing an underflow when the object is later released.

Because the caller cannot distinguish the conditional case (no additional check is present), the unconditional `cifs_put_tlink` invariably triggers a refcount imbalance on the paths where the GET did not happen. This matches the reported “refcount excess put” warning.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH
```
