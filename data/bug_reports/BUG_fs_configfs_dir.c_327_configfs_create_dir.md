# REAL BUG: fs/configfs/dir.c:327 configfs_create_dir()

**Confidence**: HIGH | **Counter**: `dentry->d_fsdata->s_count.counter`

## Reasoning

ut(dentry->d_fsdata)` then `configfs_remove_dirent(dentry)`. Both functions almost certainly perform a reference decrement on `dentry->d_fsdata->s_count`, causing a double put on the error path when `configfs_create` fails. The warning of an “excess put” is exactly this double-put on that counter.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L306 | return error | NO (configfs_make_dirent failed) | NO | ✅ | No reference taken on failure. |
| L311 | goto out_remove | YES (configfs_make_dirent succeeded) | YES, double: configfs_put(L325) + configfs_remove_dirent(L326) | ❌ EXCESS PUT | configfs_remove_dirent likely releases the same ref that configfs_put already decremented → underflow. |
| L322 | return 0 | YES | NO explicit put, ownership transfers to dentry + dirent | ✅ | Normal success path; the reference is held by the dirent structure. |

**Goto label trace**: `out_remove` at L324 calls `configfs_put(dentry->d_fsdata)` then `configfs_remove_dirent(dentry)`. Both functions almost certainly perform a reference decrement on `dentry->d_fsdata->s_count`, causing a double put on the error path when `configfs_create` fails. The warning of an “excess put” is exactly this double-put on that counter.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The error path (goto out_remove) calls both configfs_put and configfs_remove_dirent, each of which decrements the reference taken by configfs_make_dirent, resulting in a refcount underflow.
```
