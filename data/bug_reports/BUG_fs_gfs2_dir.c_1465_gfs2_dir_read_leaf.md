# REAL BUG: fs/gfs2/dir.c:1465 gfs2_dir_read_leaf()

**Confidence**: HIGH | **Counter**: `bh->b_count.counter`

## Reasoning

| After loop (success path) → `out_free` | success | YES (multiple, all stored) | YES (loop `brelse` for all `larr`) | ✅ | normal cleanup |

## Full Response

```
## Path Table

| Line (approx) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|---------------|-------------|-----------|-----------|-----------|-------|
| ~1408 `return 0;` (when `!entries`) | success | NO (second loop not entered) | N/A | ✅ | leaked bhs freed in first loop |
| ~1425 `goto out;` (larr allocation failure) | error | NO (get_leaf not called yet) | N/A | ✅ | |
| ~1450 `goto out_free;` (get_leaf error in second loop) | error | NO (get_leaf failed) | N/A (no bh held) | ✅ | standard: error → no ref |
| ~1460 `goto out_free;` after `IS_ERR(dent)` | error | **YES** (get_leaf succeeded) | **NO** (bh not stored, not released) | ❌ **LEAK** | bh leaked on error path |
| ~1461 `goto out_free;` after `entries2` corruption check | error | **YES** (get_leaf succeeded) | **NO** (bh not stored, not released) | ❌ **LEAK** | bh leaked on error path |
| After loop (success path) → `out_free` | success | YES (multiple, all stored) | YES (loop `brelse` for all `larr`) | ✅ | normal cleanup |

## VERDICT: REAL_BUG

## CONFIDENCE: HIGH

`get_leaf` successfully acquires `bh` (refcount ++), but inside the `if (lf->lf_entries)` block, error jumps (`IS_ERR(dent)` or `entries2 != g.offset`) go to `out_free` **before** `larr[leaf++] = bh` is executed.  `out_free` only releases stored `bh` pointers; the current `bh` is neither stored nor released → refcount leak.
```
