# REAL BUG: fs/ntfs/attrib.c:3389 ntfs_attr_record_move_away()

**Confidence**: HIGH | **Counter**: `$->count.counter`

## Reasoning

| L3389 | return err (after unmap) | NO (no map_mft_record before) | YES (unmap_mft_record called) | ❌ EXCESS PUT | unmap without a prior map → refcount underflow |

## Full Response

```
| Line | Return Type | GET Done? (map_mft_record) | PUT Done? (unmap_mft_record) | Balanced? | Notes |
|------|-------------|----------------------------|------------------------------|-----------|-------|
| L3315 | error -EINVAL | NO | NO | ✅ | early param check, no get |
| L3327 | error -EINVAL | NO | NO | ✅ | !NInoAttrList check, no get |
| L3334 | error err | NO | NO | ✅ | ntfs_inode_attach_all_extents fail, no get |
| L3352 | error -EIO | NO (IS_ERR guard, map failed) | NO | ✅ | map_mft_record failure, no ref held |
| L3370 | success 0 | YES (map succ, then unmap before return) | YES | ✅ | balanced: unmap after map |
| L3382 | error err | NO | NO | ✅ | ntfs_mft_record_alloc fails, no unmap called |
| L3389 | return err (after unmap) | NO (no map_mft_record before) | YES (unmap_mft_record called) | ❌ EXCESS PUT | unmap without a prior map → refcount underflow |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
unmap_mft_record(ni) after ntfs_mft_record_alloc (L3389) has no matching map_mft_record, causing an excess put on the MFT record's refcount.
```
