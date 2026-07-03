# REAL BUG: fs/btrfs/direct-io.c:605 btrfs_dio_iomap_begin()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L605 | return ret (error fallthrough from unlock_err/err) | YES (on leak path) | NO (on leak path) | ❌ LEAK | reached via L570 leak path, no put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L383 | return -EAGAIN (early length>PAGE_SIZE) | NO (before get) | N/A | ✅ | GET never called |
| L410 | return -EAGAIN (async NOWAIT, needs writeback) | NO | N/A | ✅ | |
| L420 | return ret (filemap_fdatawrite_range fail) | NO | N/A | ✅ | |
| L450 | goto err (btrfs_check_data_free_space fail) | NO | N/A | ✅ | |
| L470 | goto err (lock_extent_direct fail) | NO | N/A | ✅ | |
| L490 | goto unlock_err (IS_ERR(em)) | NO (get failed) | N/A | ✅ | conditional GET did not succeed |
| L510 | goto unlock_err (compressed/inline) | YES | YES (freed before goto) | ✅ | `btrfs_free_extent_map(em)` before goto |
| L540 | goto unlock_err (NOWAIT len < length) | YES | YES (freed before goto) | ✅ | `btrfs_free_extent_map(em)` before goto |
| L570 | goto unlock_err (`btrfs_get_blocks_direct_write` fail) | YES | NO | ❌ LEAK | skips the later `btrfs_free_extent_map(em)` |
| L590 | return 0 (normal success) | YES | YES (freed before return) | ✅ | |
| L605 | return ret (error fallthrough from unlock_err/err) | YES (on leak path) | NO (on leak path) | ❌ LEAK | reached via L570 leak path, no put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`btrfs_get_extent` succeeds, then `btrfs_get_blocks_direct_write` fails; the `goto unlock_err` path at ~L570 skips `btrfs_free_extent_map`, leaking the extent_map reference.
```
