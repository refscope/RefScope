# REAL BUG: fs/fat/namei_msdos.c:597 do_msdos_rename()

**Confidence**: HIGH | **Counter**: `$->i_sb->s_remove_count.counter`

## Reasoning

link/inc_nlink)** `fat_remove_entries` fail → goto error_dotdot | error | **YES** (drop_nlink(old_dir)) | **NO** | ❌ LEAK | `inc_nlink(old_dir)` missing; `inc_nlink(new_dir)` also not undone if !new_inode |

## Full Response

```
| Line | Return Type | GET Done? (old_dir drop) | PUT Done? (old_dir inc) | Balanced? | Notes |
|------|-------------|--------------------------|-------------------------|-----------|-------|
| ~L447 fat_scan fail → goto out | error | NO | N/A | ✅ | before any drop |
| ~L454 fat_get_dotdot_entry fail → goto out | error | NO | N/A | ✅ | |
| ~L478 special rename → goto out | success/error | NO | N/A | ✅ | only attr changes, no nlink op |
| ~L485 err && new_inode → goto out | error | NO | N/A | ✅ | |
| ~L489 fat_dir_empty fail → goto out | error | NO | N/A | ✅ | |
| ~L498 msdos_add_entry fail → goto out | error | NO | N/A | ✅ | |
| ~L520 fat_sync_inode fail → goto error_inode | error | NO | N/A | ✅ | before update_dotdot block |
| ~L531 sync_dirty_buffer fail → goto error_dotdot (before nlink) | error | NO | N/A | ✅ | error_dotdot before drop_nlink |
| ~L548 **(after drop_nlink/inc_nlink)** `fat_remove_entries` fail → goto error_dotdot | error | **YES** (drop_nlink(old_dir)) | **NO** | ❌ LEAK | `inc_nlink(old_dir)` missing; `inc_nlink(new_dir)` also not undone if !new_inode |
| ~L565 normal success → out | success | YES | N/A (permanent) | ✅ | intended final state |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the `update_dotdot` true path, after `drop_nlink(old_dir)` and possibly `inc_nlink(new_dir)`, the `error_dotdot` recovery (reached via `fat_remove_entries` failure) never calls `inc_nlink(old_dir)` or `drop_nlink(new_dir)`, leaving the inode link counts and the superblock `s_remove_count` unbalanced.
```
