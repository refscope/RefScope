# REAL BUG: fs/ext4/namei.c:4048 ext4_rename()

**Confidence**: HIGH | **Counter**: `$->i_sb->s_remove_count.counter`

## Reasoning

| L4048  | return retval (error from any above goto) | YES (some GETs) | NO        | ❌ LEAK | Error paths after GET return without undoing refcount |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L3806 | error       | NO        | N/A       | ✅        | Early return before any refcount GET (new.inode == 0 check) |
| ~L3812 | error       | NO        | N/A       | ✅        | Return -EXDEV |
| ~L3817 | error       | NO        | N/A       | ✅        | dquot_initialize(old.dir) failure |
| ~L3820 | error       | NO        | N/A       | ✅        | dquot_initialize(old.inode) failure |
| ~L3823 | error       | NO        | N/A       | ✅        | dquot_initialize(new.dir) failure |
| ~L3828 | error       | NO        | N/A       | ✅        | dquot_initialize(new.inode) failure (if new.inode) |
| ~L3835 | error       | NO        | N/A       | ✅        | ext4_find_entry old.bh IS_ERR |
| ~L3845 | goto release_bh | NO     | N/A       | ✅        | old.bh NULL or inode mismatch, retval -ENOENT |
| ~L3855 | goto release_bh | NO     | N/A       | ✅        | IS_ERR new.bh, retval = PTR_ERR |
| ~L3875 | goto release_bh | NO     | N/A       | ✅        | handle/journal_start IS_ERR (non‑whiteout) |
| ~L3885 | goto release_bh | NO     | N/A       | ✅        | ext4_whiteout_for_rename IS_ERR |
| ~L3905 | goto end_rename | NO     | N/A       | ✅        | S_ISDIR checks / ext4_rename_dir_prepare failure (before GET) |
| ~L3925 | goto end_rename | NO     | N/A       | ✅        | ext4_add_entry / ext4_setent failure (before GET) |
| ~L3940 | goto end_rename | NO     | N/A       | ✅        | ext4_mark_inode_dirty(old.inode) failure (before GET) |
| ~L3960 | ext4_dec_count(new.inode) | YES (new.inode) | — | — | First GET (increments s_remove_count if nlink→0) |
| ~L3975 | goto end_rename (A) | YES (new.inode) | NO        | ❌ LEAK | ext4_rename_dir_finish failure — GET not undone |
| ~L3990 | ext4_dec_count(old.dir) + clear_nlink(new.inode) | YES (old.dir, new.inode) | NO (still) | ❌ LEAK (if error later) | GETs inside old.is_dir block |
| ~L4005 | goto end_rename (C) | YES (multiple GETs) | NO        | ❌ LEAK | ext4_mark_inode_dirty(old.dir) failure — after clear_nlink |
| ~L4020 | goto end_rename (D) | YES (all previous GETs) | NO        | ❌ LEAK | ext4_mark_inode_dirty(new.inode) failure — all GETs held |
| L4048  | return retval (0, success) | YES (GETs used) | NO (no ext4_inc_count needed) | ℹ️ (permanent) | Success path: GETs are intentional for the final unlink |
| L4048  | return retval (error from any above goto) | YES (some GETs) | NO        | ❌ LEAK | Error paths after GET return without undoing refcount |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
Error paths after `ext4_dec_count(new.inode)` (and when applicable after `ext4_dec_count(old.dir)` + `clear_nlink(new.inode)`) jump to `end_rename` without calling `ext4_inc_count` to revert the refcount increment on `s_remove_count`; this leaves an orphaned inode and a leaked counter (the inode’s nlink reduction is not rolled back on transaction abort).
```
