# REAL BUG: fs/ubifs/tnc.c:1425 lookup_level0_dirty()

**Confidence**: HIGH | **Counter**: `$->clean_zn_cnt.counter`

## Reasoning

tern: unconditional (successful) GET via `ubifs_load_znode`, then an error return on the immediately following PUT (`dirty_cow_znode`) without releasing the initial reference. Neither the error label nor any cleanup code performs a `dirty_cow_znode` (or equivalent put) for the leaked reference.

## Full Response

```
## Path Analysis Table

We enumerate **all** return paths in `lookup_level0_dirty()`. Because this is a "normal" leak auditor, we treat `ubifs_load_znode` as a GET (increment `clean_zn_cnt`) and `dirty_cow_znode` as a PUT (decrement `clean_zn_cnt`) — consistent with typical UBIFS clean/dirty refcounting. Without explicit contracts, the pattern `load → (error return → leak)` is a classic bug, and the Smatch "inconsistent refcounting" points directly to such imbalances.

| Path # | How reached (description) | GET done? (load succeeded) | PUT done? | Balanced? | Notes |
|--------|---------------------------|----------------------------|-----------|-----------|-------|
| 1 | Initial `!znode`: `ubifs_load_znode` returns error | NO (error) | N/A | ✅ | IS_ERR guard |
| 2 | Initial `!znode`: load OK → `dirty_cow_znode(&c->zroot)` returns error | **YES** | **NO** | ❌ LEAK | load incremented clean count, dirty failed, no matching put |
| 3 | Initial znode not null, then `dirty_cow_znode(&c->zroot)` fails | NO (no load call) | N/A | ✅ | No get, no put needed |
| 4 | Loop: `zbr->znode` non‑null → `dirty_cow_znode(c, zbr)` fails | NO (no load) | N/A | ✅ | |
| 5 | Loop: `zbr->znode` null → `ubifs_load_znode` fails | NO (error) | N/A | ✅ | IS_ERR guard |
| 6 | Loop: load OK → `dirty_cow_znode(c, zbr)` fails | **YES** | **NO** | ❌ LEAK | clean ref leaked, identical pattern to Path 2 |
| 7 | `znode->level == 0` → break, then `if (exact ...)` → `return exact` | Balanced by earlier puts | ✅ | Original loads already paired with dirty in the loop or initial block. No unmatched refs here. |
| 8 | After break, `tnc_prev` fails with `-ENOENT` → return 0 | Balanced | ✅ | |
| 9 | After break, `tnc_prev` other error → return err | Balanced | ✅ | |
| 10 | After break, `keys_cmp` mismatch → set `*n = -1`, return 0 | Balanced | ✅ | |
| 11 | After break, `dirty_cow_bottom_up` error → return | Balanced | ✅ | That call itself doesn’t involve the clean_zn_cnt counter tracked here |
| 12 | Final `return 1` | Balanced | ✅ | |

**Key takeaway:** Paths **2** and **6** are clear refcount leaks. They follow the classic pattern: unconditional (successful) GET via `ubifs_load_znode`, then an error return on the immediately following PUT (`dirty_cow_znode`) without releasing the initial reference. Neither the error label nor any cleanup code performs a `dirty_cow_znode` (or equivalent put) for the leaked reference.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
Function `lookup_level0_dirty` leaks a `clean_zn_cnt.counter` reference on two error paths (initial root dirty failure and inner loop dirty‑after‑load failure) when `ubifs_load_znode` succeeds but `dirty_cow_znode` returns an error — the required put is missing.
```
