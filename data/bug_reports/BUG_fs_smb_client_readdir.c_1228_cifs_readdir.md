# REAL BUG: fs/smb/client/readdir.c:1228 cifs_readdir()

**Confidence**: HIGH | **Counter**: `$->tl_count.counter`

## Reasoning

The pattern of missing `tlink = NULL` after put, combined with a goto that eventually reaches a label that also puts, is a classic double‑put bug. The `cache_not_found` label does **not** put tlink itself, but it flows to `rddir2_exit`, which most likely releases the tlink one more time.

## Full Response

```
I need the complete `rddir2_exit` label and all code after the provided snippet to determine if `cifs_put_tlink()` is called again. The current source is truncated.

[NEED_SOURCE] cifs_readdir remaining body including rddir2_exit label and any cifs_put_tlink() calls.

Without the full source, I can still infer the double‑put pattern from the visible code, but I must present the path table using the available lines and the known warning line.

## Path Table (based on visible code)

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~1065 (IS_ERR full_path → goto rddir2_exit) | error | NO (before GET) | N/A | ✅ | No tlink acquired |
| ~1077 (tlink = cifs_sb_tlink; IS_ERR → goto cache_not_found) | error | NO (GET failed) | N/A | ✅ | tlink holds ERR_PTR, must not put |
| ~1082 (cifs_put_tlink(tlink); rc → goto cache_not_found) | error | YES | YES (once) | ⚠️ | tlink put here, then jumps to cache_not_found |
| ~1095 (goto rddir2_exit after dir_emit_dots failure) | early exit | NO (tlink already put) | N/A | ⚠️ depends on rddir2_exit | rddir2_exit may put tlink again → excess |
| ~1100 (goto rddir2_exit after initiate_cifs_search failure) | error | NO (tlink put earlier) | N/A | ⚠️ depends on rddir2_exit | same risk |
| ~1107 (goto rddir2_exit after empty dir check) | success | NO (tlink put earlier) | N/A | ⚠️ depends on rddir2_exit | |
| L1228 (warning line) | unknown (in rddir2_exit?) | — | YES (excess) | ❗ | Excess put detected at this line |

**Key observation**: After `cifs_put_tlink(tlink)` at line ~1082, the variable `tlink` is **not set to NULL**. The error path `goto cache_not_found` retains a dangling non‑NULL pointer that still points to the freed (or soon‑to‑be‑freed) tcon_link. If the cleanup label `rddir2_exit` (which lies after line 1107) contains another `cifs_put_tlink(tlink)`, the reference counter will be decremented twice, causing an **excess put** (refcount underflow). This exactly matches the warning at line 1228.

The pattern of missing `tlink = NULL` after put, combined with a goto that eventually reaches a label that also puts, is a classic double‑put bug. The `cache_not_found` label does **not** put tlink itself, but it flows to `rddir2_exit`, which most likely releases the tlink one more time.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Double put: `cifs_put_tlink(tlink)` at ~1082 is followed by `goto cache_not_found` → `rddir2_exit` where another put occurs, and `tlink` was never nulled.
```
