# REAL BUG: fs/smb/client/inode.c:2329 cifs_mkdir()

**Confidence**: MEDIUM | **Counter**: `$->tl_count.counter`

## Reasoning

- No ownership transfer or deferred release mechanism covers this discrepancy; error paths within the same function that reach `mkdir_out` will trigger the extra put.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2266 | error (forced shutdown) | NO (before get) | N/A | ✅ | |
| L2271 | error (IS_ERR(tlink)) | NO (get failed)                | N/A | ✅ | tlink is ERR_PTR → no ref held |
| L2280 | goto mkdir_out | CONDITIONAL (contract says conditional_on_path; warning indicates NO on this path) | YES (cifs_put_tlink at L2329) | ❌ EXCESS PUT | path after successful cifs_sb_tlink but get may not have incremented refcount, yet put called unconditionally |
| L2286 | goto mkdir_out | CONDITIONAL (probably NO) → warning | YES | ❌ EXCESS PUT | |
| L2292 | goto mkdir_out | CONDITIONAL (NO) | YES | ❌ EXCESS PUT | |
| L2294 | goto mkdir_out | CONDITIONAL (NO) | YES | ❌ EXCESS PUT | |
| L2298 | goto mkdir_out | CONDITIONAL (NO) | YES | ❌ EXCESS PUT | |
| L2304 (fallthrough) | success path | CONDITIONAL (NO) → warning | YES | ❌ EXCESS PUT | |

**Analysis details:**
- The contract for `cifs_sb_tlink()` states it is **conditional_on_path**: the reference count increment is not performed on all success returns.
- The current code uses `IS_ERR(tlink)` to guard only error returns. On any non-error path, it unconditionally calls `cifs_put_tlink()` at the `mkdir_out` label (line 2329), regardless of whether the get actually happened.
- This leads to an **excess put** (put without a corresponding get) on paths where `cifs_sb_tlink` returned a valid pointer but did not increment `tl_count`. The warning at line 2329 (“refcount excess put on $->tl_count.counter”) confirms this mismatch.
- No ownership transfer or deferred release mechanism covers this discrepancy; error paths within the same function that reach `mkdir_out` will trigger the extra put.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`cifs_put_tlink()` is called unconditionally after `cifs_sb_tlink()`, but the get contract is conditional; this can put a reference that was never acquired.
```
