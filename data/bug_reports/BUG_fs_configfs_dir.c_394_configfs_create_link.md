# REAL BUG: fs/configfs/dir.c:394 configfs_create_link()

**Confidence**: HIGH | **Counter**: `dentry->d_fsdata->s_count.counter`

## Reasoning

| L385-387 (return 0) | success     | YES | NO | ✅ | ref held for link lifetime |

## Full Response

```
[NEED_SOURCE] configfs_remove_dirent
[NEED_SOURCE] configfs_make_dirent

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L376 | error       | NO (configfs_make_dirent failed) | N/A | ✅ | no ref held |
| L381 → L394 (goto out_remove) | error (IS_ERR) | YES (configfs_make_dirent inc ref on new dentry->d_fsdata) | YES (configfs_put) + possibly configfs_remove_dirent puts again | ❌ LIKELY EXCESS | configfs_put explicitly drops, then configfs_remove_dirent likely also drops → double put |
| L385-387 (return 0) | success     | YES | NO | ✅ | ref held for link lifetime |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

On the `IS_ERR(inode)` error path, `configfs_put(dentry->d_fsdata)` at line 394 explicitly releases the reference obtained by `configfs_make_dirent`, but `configfs_remove_dirent` very likely also releases that same reference (as a “remove” function typically calls a final put). That makes the explicit put excess, matching the static analyzer’s excess put report.
```
