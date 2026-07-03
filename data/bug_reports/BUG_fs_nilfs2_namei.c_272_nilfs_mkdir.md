# REAL BUG: fs/nilfs2/namei.c:272 nilfs_mkdir()

**Confidence**: HIGH | **Counter**: `$->i_sb->s_remove_count.counter`

## Reasoning

| L250→out | success | NO | dir: YES, inode: YES | ✅ | Success path: no drop_nlink, inc_nlink are properly balanced by future unlink operations. |

## Full Response

```
| Line | Return Type | GET Done? (drop_nlink) | PUT Done? (inc_nlink) | Balanced? | Notes |
|------|-------------|------------------------|------------------------|-----------|-------|
| L225 | error (ret) | NO (no call) | NO | ✅ | Transaction begin failure, no refcount ops. |
| L235 | goto out_dir | dir: YES (via out_dir drop_nlink) | dir: YES (inc_nlink at L229) | ✅ (dir) | inc_nlink(dir) balanced by drop_nlink(dir) at out_dir. Inode not allocated. |
| L241 | goto out_fail | dir: YES (via out_dir fallthrough), inode: YES (two drop_nlink) | dir: YES (L229), inode: YES (L238) | ❌ LEAK on inode | inc_nlink(inode) once, but out_fail calls drop_nlink(inode) twice. Net +1 s_remove_count increment. Leak. |
| L245 | goto out_fail | same as above | same | ❌ LEAK | Same imbalance as L241. |
| L250→out | success | NO | dir: YES, inode: YES | ✅ | Success path: no drop_nlink, inc_nlink are properly balanced by future unlink operations. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On error paths after `inc_nlink(inode)` (L241/L245), the `out_fail` label calls `drop_nlink(inode)` twice but only a single `inc_nlink(inode)` was executed, causing a one‑unit leak of the superblock’s `s_remove_count` counter at the final return (line 272).
```
