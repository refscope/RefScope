# REAL BUG: fs/ubifs/dir.c:1578 do_rename()

**Confidence**: HIGH | **Counter**: `$->i_sb->s_remove_count.counter`

## Reasoning

**Fix**: Replace `set_nlink(whiteout, 0)` with `drop_nlink(whiteout)` in the `out_cancel` block to correctly invert the earlier `set_nlink` via a get operation.

## Full Response

```
| Line (approx) | Return Type | GET Done? (drop_nlink/clear_nlink) | PUT Done? (inc_nlink/set_nlink) | Balanced? | Notes |
|---------------|-------------|-----------------------------------|--------------------------------|-----------|-------|
| ~1345         | error (purge_xattrs) | NO | NO | ✅ | No nlink operations yet |
| ~1350         | error (check_dir_empty) | NO | NO | ✅ | No nlink operations yet |
| ~1360         | error (fscrypt_setup old_nm) | NO | NO | ✅ | No nlink operations yet |
| ~1368         | error (fscrypt_setup new_nm) | NO | NO | ✅ | No nlink operations yet |
| ~1380         | error (budget_space req) | NO | NO | ✅ | No nlink operations yet |
| ~1388         | error (budget_space ino_req) | NO | NO | ✅ | No nlink operations yet |
| ~1395 (dev kmalloc fails) | goto out_release | NO | NO | ✅ | No nlink operations yet |
| ~1405 (create_whiteout fails) | goto out_release | NO | NO | ✅ | set_nlink not reached |
| ~1425 (wht_req budget fails) | goto out_release (iput) | NO | NO | ✅ | set_nlink not reached |
| ~1440 (jnl_rename fails) | goto out_cancel | YES (old_dir/new_inode if applicable) | **YES** – set_nlink(whiteout,1) is PUT | ❌ IMBALANCE | Whiteout nlink set to 1 (PUT) with no prior GET. Cancel path adds second PUT set_nlink(whiteout,0). Excess put on s_remove_count. |
| ~1500 (success) | return 0 | YES (old_dir/new_inode if applicable) | **YES** – set_nlink(whiteout,1) is PUT | ❌ IMBALANCE | Whiteout nlink set to 1 (PUT) without prior GET. Excess put, no later balancing on this path. |
| ~1578 (out_cancel whiteout undo) | (part of error path) | N/A (no get for whiteout) | **YES** – set_nlink(whiteout,0) is PUT | ❌ IMBALANCE | Second excess put; correct undo should be drop_nlink (GET), not set_nlink (PUT). |

**Details**: The warning line (fs/ubifs/dir.c:1578) sits in the `out_cancel` block, executing `set_nlink(whiteout, 0)`. Both `set_nlink` calls (to 1 then to 0) are classified as PUT operations on `s_remove_count`. The whiteout inode starts with i_nlink 0 (no GET), so the initial `set_nlink(whiteout, 1)` is an unbalanced PUT. The error path then adds a second PUT instead of using `drop_nlink(whiteout)` (a GET) to reverse the first. Hence a refcount excess put.

**Fix**: Replace `set_nlink(whiteout, 0)` with `drop_nlink(whiteout)` in the `out_cancel` block to correctly invert the earlier `set_nlink` via a get operation.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`set_nlink(whiteout, 0)` in cancel path is a PUT while the correct undo of `set_nlink(whiteout, 1)` (also PUT) requires a GET (`drop_nlink`); the two PUTs without a prior GET cause an excess put on `s_remove_count`.
```
