# REAL BUG: fs/ufs/namei.c:317 ufs_rename()

**Confidence**: HIGH | **Counter**: `$->i_sb->s_remove_count.counter`

## Reasoning

| L303 then L309 fails → out_dir | error return | YES (inode_inc_link_count on new_dir) | NO (no dec) | ❌ LEAK | inc without dec on error; may affect s_remove_count |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L269 | return -ENOENT | NO (before get) | N/A | ✅ | early no get |
| L275 | goto out_old | NO | N/A | ✅ | dir_de NULL, no link ops |
| L284 | goto out_dir | NO (before link ops) | N/A | ✅ | dir_de set but no link ops yet |
| L289 | goto out_dir | NO | N/A | ✅ | new_de not found, no link ops |
| L293 | goto out_dir | NO | N/A | ✅ | ufs_set_link failed, no link ops |
| L301 | goto out_dir | NO | N/A | ✅ | ufs_add_link failed, no link ops |
| L296‑297 then L309 fails → out_dir | error return | YES (drop_nlink/inode_dec_link_count on new_inode) | NO | ❌ LEAK | no inc for new_inode, counter imbalance |
| L296‑297 then L309 ok, L312 fails → out_dir | error return | YES (on new_inode) | NO | ❌ LEAK | same imbalance after ufs_set_link error |
| L303 then L309 fails → out_dir | error return | YES (inode_inc_link_count on new_dir) | NO (no dec) | ❌ LEAK | inc without dec on error; may affect s_remove_count |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`drop_nlink`/`inode_dec_link_count` on `new_inode` are executed, but if the subsequent `ufs_delete_entry()` (or `ufs_set_link()`) fails, the function returns via `out_dir` without ever calling `inode_inc_link_count` to undo those decrements. This leaves `new_inode`’s i_nlink and the superblock’s `s_remove_count` permanently unbalanced.
```
