# REAL BUG: fs/ubifs/dir.c:1077 ubifs_mkdir()

**Confidence**: MEDIUM | **Counter**: `$->i_sb->s_remove_count.counter`

## Reasoning

| 1058 | return NULL (success) | NO | YES (set_nlink(inode,1), inc_nlink(inode), inc_nlink(dir)) | ❌ (imbalance locally, but future unlinks provide GETs) | Counterbalance expected in future; not flagged by warning |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 1022 | error (ERR_PTR) | NO (budget fail, no ops) | NO | ✅ | |
| 1026 | goto out_budg (then ERR_PTR) | NO (prepare_create fail) | NO | ✅ | |
| 1033 | goto out_fname (then ERR_PTR) | NO (new_inode fail) | NO | ✅ | |
| 1038 | goto out_inode (then ERR_PTR) | NO (no drop_nlink) | YES (set_nlink(inode,1) at 1040) | ❌ excess put | set_nlink(inode,1) is a PUT; no GET to balance |
| 1051 | goto out_cancel (then ERR_PTR) | YES (drop_nlink(dir) at 1063) | YES (set_nlink(inode,1) at 1040, inc_nlink(inode) at 1043, inc_nlink(dir) at 1044, set_nlink(inode,0) at 1065) | ❌ excess put (4 PUT, 1 GET) | out_cancel path undoes dir's inc but fails to properly undo inode's nlink increments |
| 1058 | return NULL (success) | NO | YES (set_nlink(inode,1), inc_nlink(inode), inc_nlink(dir)) | ❌ (imbalance locally, but future unlinks provide GETs) | Counterbalance expected in future; not flagged by warning |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The out_cancel error path calls inc_nlink(inode) and set_nlink(inode,1) (both PUTs on s_remove_count) before the error, but only calls set_nlink(inode,0) (another PUT) in cleanup instead of using drop_nlink to properly perform the needed GETs, leading to an excess put (counter underflow) when the inode is eventually freed.
```
