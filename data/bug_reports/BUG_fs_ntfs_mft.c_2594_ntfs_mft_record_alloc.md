# REAL BUG: fs/ntfs/mft.c:2594 ntfs_mft_record_alloc()

**Confidence**: MEDIUM | **Counter**: `$->count.counter`

## Reasoning

- The `undo_mftbmp_alloc` label (line ~2594) is the target of this leak, matching the warning location.

## Full Response

```
# Path Table for `ntfs_mft_record_alloc()` (focused on possible `map_mft_record`/`unmap_mft_record` mismatch through `map_extent_mft_record`)

| Path Description                                                         | GET via `map_mft_record(base_ni)`? | PUT via `unmap_mft_record(base_ni)`? | Balanced? | Notes                                                                                                       |
|--------------------------------------------------------------------------|------------------------------------|--------------------------------------|-----------|-------------------------------------------------------------------------------------------------------------|
| `map_extent_mft_record(base_ni, …)` succeeds (extent inode created)      | YES (inside callee)                | NO immediate, but handled by extent inode lifecycle (ownership transfer) | ✅        | Ref on base_ni held by extent inode; will be released when extent inode is put/freed.                       |
| `map_extent_mft_record(base_ni, …)` **fails**, `goto undo_mftbmp_alloc;` | YES (inside callee before failure) | NO (no `unmap_mft_record(base_ni)` on this path) | ❌ **LEAK** | Error path does not release the reference acquired by `map_extent_mft_record`’s internal `map_mft_record`. |
| Explicit `map_mft_record(mft_ni)` block (data attribute update)          | YES                                | YES (unmap on all error paths)       | ✅        | All exit paths from this block either unmap or never acquired the ref.                                       |

**Observations:**  
- The explicit `map_mft_record`/`unmap_mft_record` pair inside the data‑attribute update block is correctly balanced on every path.  
- The `map_extent_mft_record(base_ni, …)` call very likely invokes `map_mft_record` on `base_ni` to modify the base inode’s MFT record. On failure, the called function may have already acquired this reference but the caller’s error path (`goto undo_mftbmp_alloc`) never calls `unmap_mft_record(base_ni)`.  
- The `undo_mftbmp_alloc` label (line ~2594) is the target of this leak, matching the warning location.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
[NEED_SOURCE] map_extent_mft_record (to confirm it calls map_mft_record on base_ni and whether the error path inside that function already releases the ref)
```
