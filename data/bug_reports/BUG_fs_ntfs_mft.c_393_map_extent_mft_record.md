# REAL BUG: fs/ntfs/mft.c:393 map_extent_mft_record()

**Confidence**: HIGH | **Counter**: `$->count.counter`

## Reasoning

The warning at line 393 (inside `unm_nolock_err_out`) is triggered by `ntfs_clear_extent_inode(ni)` after `unmap_mft_record(ni)` has already been called on the same path.

## Full Response

```
## Path Table

| Line (approx) | Return Type | GET (map) Done? | PUT (unmap) Done? | PUT (clear) Done? | Balanced? | Notes |
|---------------|-------------|-----------------|-------------------|-------------------|-----------|-------|
| L302 | success     | YES (map OK)    | NO                | NO                | ✅ | Caller will unmap later |
| L306 | error       | YES (map OK)    | YES (unmap)       | NO                | ✅ | Single unmap |
| L309 | error       | NO (map failed) | NO                | NO                | ✅ | No map ref acquired |
| L315 | error       | NO (map not called) | NO            | NO                | ✅ | |
| L324 → L309 | error      | NO (map failed) | NO                | YES (clear, but no map ref) | ✅ | clear for initial inode ref only |
| L331 → unm_nolock_err_out (L373) | error | YES (map OK) | YES (unmap) | YES (ntfs_clear_extent_inode) | ❌ | **Double put** — unmap already released map ref; clear releases it again |
| L338 (goto retry) | loop | YES (map OK) | NO                | YES (clear)       | ⚠️ | If clear unmaps, single put OK; if not, leak. Not the flagged path. |
| L351 → unm_err_out → unm_nolock_err_out | error | YES (map OK) | YES (unmap) | YES (clear) | ❌ | **Double put** — same as above |
| L365 | success     | YES (map OK)    | NO                | NO                | ✅ | Caller unmap |

The warning at line 393 (inside `unm_nolock_err_out`) is triggered by `ntfs_clear_extent_inode(ni)` after `unmap_mft_record(ni)` has already been called on the same path.

## VERDICT: REAL_BUG
CONFIDENCE: HIGH
The `unm_nolock_err_out` error path calls both `unmap_mft_record(ni)` and `ntfs_clear_extent_inode(ni)` when `destroy_ni` is true. `ntfs_clear_extent_inode` internally unmaps (drops the mapping reference) again, resulting in an excess put on the mapped record’s refcount (seen at line 393). The retry path (goto retry) does not have this double unmap, confirming inconsistency.
```
