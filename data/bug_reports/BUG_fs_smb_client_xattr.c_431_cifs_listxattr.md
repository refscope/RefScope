# REAL BUG: fs/smb/client/xattr.c:431 cifs_listxattr()

**Confidence**: HIGH | **Counter**: `$->tl_count.counter`

## Reasoning

| L422‑424 | fall‑through to list_ea_exit (success) | Conditional – sometimes NO ref taken | YES (unconditional `cifs_put_tlink`) | ❌ EXCESS PUT when GET didn’t happen | same reason |

## Full Response

```
| Line | Return Type | GET Done? (refcount inc) | PUT Done? | Balanced? | Notes |
|------|-------------|---------------------------|-----------|-----------|-------|
| L398 | early return (forced shutdown) | NO (before call) | NO | ✅ | |
| L401 | early return (NO_XATTR) | NO (before call) | NO | ✅ | |
| L407‑408 | IS_ERR(tlink) error return | NO (get failed) | NO | ✅ | IS_ERR guard, no ref taken |
| L416 | goto list_ea_exit (build_path error) | Conditional – sometimes NO ref taken | YES (unconditional `cifs_put_tlink`) | ❌ EXCESS PUT when GET didn‘t happen | `cifs_sb_tlink` is **conditional**: may return a valid pointer **without** incrementing `tl_count` |
| L422‑424 | fall‑through to list_ea_exit (success) | Conditional – sometimes NO ref taken | YES (unconditional `cifs_put_tlink`) | ❌ EXCESS PUT when GET didn’t happen | same reason |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`cifs_sb_tlink` is documented as **conditional** (does not always take a reference). `cifs_listxattr()` unconditionally calls `cifs_put_tlink()` on the returned `tlink` on all paths after the IS_ERR check, causing a refcount underflow (`excess put`) when the link was returned without a new reference.
```
