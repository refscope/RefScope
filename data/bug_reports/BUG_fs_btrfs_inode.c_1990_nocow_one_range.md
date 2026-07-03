# REAL BUG: fs/btrfs/inode.c:1990 nocow_one_range()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| 1969 goto error (ret < 0 after put) | error | YES | YES (explicit) | ❌ (excess put) | Explicit put done at L1968, then `btrfs_cleanup_ordered_extents` in error label (L1977) does an additional put → double put |

## Full Response

```
| Line (range) | Return Type | Ordered GET? | Explicit PUT? | Balanced? | Notes |
|-------------|-------------|--------------|---------------|-----------|-------|
| 1944 (goto error, em IS_ERR) | error | NO (before ordered alloc) | N/A | ✅ | |
| 1958 (goto error, ordered IS_ERR) | error | NO (alloc failed) | N/A | ✅ | |
| 1971–1975 (return ret, ret ≥ 0) | success | YES (alloc success) | YES (at L1968) | ✅ | normal path |
| 1969 goto error (ret < 0 after put) | error | YES | YES (explicit) | ❌ (excess put) | Explicit put done at L1968, then `btrfs_cleanup_ordered_extents` in error label (L1977) does an additional put → double put |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

On the ret < 0 path after `btrfs_reloc_clone_csums`, the ordered extent is put at L1968, then the `goto error` triggers `btrfs_cleanup_ordered_extents` which performs a second put, causing a refcount underflow (excess put).
```
