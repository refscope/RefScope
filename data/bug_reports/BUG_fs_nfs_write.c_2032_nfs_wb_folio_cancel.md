# REAL BUG: fs/nfs/write.c:2032 nfs_wb_folio_cancel()

**Confidence**: HIGH | **Counter**: `$->wb_kref.refcount.refs.counter`

## Reasoning

id req path) | success (0) | YES (valid req returned, reference held) | **YES×2** → EXCESS PUT | ❌ | `nfs_inode_remove_request()` calls `nfs_release_request()` (one put), then `nfs_unlock_and_release_request()` also calls `nfs_release_request()` (second put) → double kref_put on the same counter |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2020 (IS_ERR path) | error (PTR_ERR) | NO (get failed) | NO | ✅ | `nfs_lock_and_join_requests` returns ERR_PTR → no reference held |
| L2030 (req == NULL path, if possible) | success (0) | NO (conditional get on non-NULL, returned NULL) | NO | ✅ | no reference taken, no put needed |
| L2030 (valid req path) | success (0) | YES (valid req returned, reference held) | **YES×2** → EXCESS PUT | ❌ | `nfs_inode_remove_request()` calls `nfs_release_request()` (one put), then `nfs_unlock_and_release_request()` also calls `nfs_release_request()` (second put) → double kref_put on the same counter |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the valid‑req path, both `nfs_inode_remove_request()` and `nfs_unlock_and_release_request()` drop the kref via `nfs_release_request()`, causing a double put and the refcount underflow warned at line 2032.
```
```
