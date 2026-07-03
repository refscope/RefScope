# REAL BUG: fs/xfs/libxfs/xfs_inode_util.c:667 xfs_droplink()

**Confidence**: HIGH | **Counter**: `$->i_sb->s_remove_count.counter`

## Reasoning

| 667  | return xfs_iunlink(tp, ip) | NO        | YES (excess put) | ❌        | i_nlink == 0, xfs_iunlink() internally performs a put (decrement) on s_remove_count; no prior get from drop_nlink() or set_nlink() |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 665  | success (0) | NO        | NO        | ✅        | i_nlink != 0, no xfs_iunlink call; drop_nlink() is VFS generic, does not touch s_remove_count |
| 667  | return xfs_iunlink(tp, ip) | NO        | YES (excess put) | ❌        | i_nlink == 0, xfs_iunlink() internally performs a put (decrement) on s_remove_count; no prior get from drop_nlink() or set_nlink() |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
xfs_iunlink() at line 667 contains a decrement on s_remove_count (excess put), while the generic VFS drop_nlink()/set_nlink() do not increment the counter, leaving no matching get.
```
