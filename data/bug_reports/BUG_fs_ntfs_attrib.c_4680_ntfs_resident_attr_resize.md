# REAL BUG: fs/ntfs/attrib.c:4680 ntfs_resident_attr_resize()

**Confidence**: HIGH | **Counter**: `ext_ni->count.counter`

## Reasoning

| **L~4790 (goto attr_resize_again)** | **loop/retry** | **YES** | **NO** | **❌ LEAK** | ext_ni leaked on each successful loop iteration |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L~4600 (return -ENOMEM) | error | NO (before alloc) | N/A | ✅ | ctx allocation failure |
| L~4610 (goto put_err_out) | error | NO | N/A | ✅ | ntfs_attr_lookup failure |
| L~4620 (goto put_err_out) | error | NO | N/A | ✅ | bounds check failure |
| L~4630 (goto resize_done) | success/resize | NO | N/A | ✅ | small resize done |
| L~4640 (goto put_err_out) | error | NO | N/A | ✅ | ENOSPC & AT_INDEX_ROOT |
| L~4650 (return ntfs_non_resident_attr_expand) | success | NO | N/A | ✅ | non-resident conversion success |
| L~4660 (goto put_err_out) | error | NO | N/A | ✅ | make_non_resident failure |
| L~4670 (goto attr_resize_again) | loop/retry | NO | N/A | ✅ | retry path (no ext_ni) |
| L~4680 (goto put_err_out) | error | NO | N/A | ✅ | lookup failure 1 |
| L~4690 (return err) | error | NO | N/A | ✅ | add_attrlist/free_space failure |
| L~4700 (return err) | error | NO | N/A | ✅ | attrlist_update failure |
| L~4710 (goto put_err_out) | error | NO | N/A | ✅ | lookup failure 2 |
| L~4720 (goto put_err_out) | error | NO | N/A | ✅ | single attribute in record |
| L~4730 (return err) | error | NO | N/A | ✅ | add_attrlist failure (retry) |
| **L~4740 (goto put_err_out)** | **error (allocation failure)** | **NO** | N/A | ✅ | ntfs_mft_record_alloc failed |
| **L~4760 (goto put_err_out)** | **error (move_to failure)** | **YES** | **NO** | **❌ LEAK** | After alloc success, unmap NOT a put; no release |
| **L~4770 (goto put_err_out)** | **error (attrlist_update failure)** | **YES** | **NO** | **❌ LEAK** | After alloc success, no release |
| **L~4790 (goto attr_resize_again)** | **loop/retry** | **YES** | **NO** | **❌ LEAK** | ext_ni leaked on each successful loop iteration |

## VERDICT: REAL_BUG

## CONFIDENCE: HIGH

After `ntfs_mft_record_alloc` succeeds, `unmap_mft_record` releases the memory mapping but does **not** drop the inode reference. All subsequent error paths (goto put_err_out for move_to, attrlist_update) and the retry path (goto attr_resize_again) lack any matching `iput`/`ntfs_mft_record_put` for `ext_ni`, resulting in a refcount leak.
```
