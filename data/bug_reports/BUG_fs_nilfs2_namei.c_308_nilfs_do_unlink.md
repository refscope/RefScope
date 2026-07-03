# REAL BUG: fs/nilfs2/namei.c:308 nilfs_do_unlink()

**Confidence**: HIGH | **Counter**: `$->i_sb->s_remove_count.counter`

## Reasoning

| L304→306 (success) | success (err=0) | YES if L295 executed, else NO | YES | ❌ if GET=NO **← EXCESS PUT**; ✅ if GET=YES | drop_nlink() unconditionally called; path where inode->i_nlink > 0 has no prior get on the superblock counter |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L285 | error (de is ERR) | NO | NO | ✅ | Before any ref manipulation |
| L291 | error (ino mismatch) | NO | NO | ✅ | Before set_nlink/drop_nlink |
| L300 (via goto out) | error (nilfs_delete_entry failed) | YES if L295 executed, else NO | NO | ❌ if YES (get without put, a counter leak) | L295 sets set_nlink(inode, 1) – likely increments s_remove_count |
| L304→306 (success) | success (err=0) | YES if L295 executed, else NO | YES | ❌ if GET=NO **← EXCESS PUT**; ✅ if GET=YES | drop_nlink() unconditionally called; path where inode->i_nlink > 0 has no prior get on the superblock counter |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the normal `i_nlink > 0` path, `drop_nlink()` is called without the balancing `set_nlink()` that would raise `s_remove_count`, causing an excess put on the counter.
```
