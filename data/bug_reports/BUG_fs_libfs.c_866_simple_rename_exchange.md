# REAL BUG: fs/libfs.c:866 simple_rename_exchange()

**Confidence**: HIGH | **Counter**: `new_dir->i_sb->s_remove_count.counter`

## Reasoning

| L859 (true, !old_is_dir) | success (return 0) | YES (drop_nlink) | NO  | ❌ | drop_nlink(new_dir) without inc_nlink → leak, but not the focus of the excess‑put warning |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L855 (false) | success (return 0) | NO  | NO  | ✅ | condition not met, no refcount activity on new_dir |
| L857 (true, old_is_dir) | success (return 0) | NO  | YES (inc_nlink) | ❌ | inc_nlink(new_dir) called without prior drop_nlink → excess put on s_remove_count |
| L859 (true, !old_is_dir) | success (return 0) | YES (drop_nlink) | NO  | ❌ | drop_nlink(new_dir) without inc_nlink → leak, but not the focus of the excess‑put warning |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When `old_is_dir` is true, the branch calls `inc_nlink(new_dir)` (a put on `s_remove_count`) without any matching `drop_nlink(new_dir)`, producing the reported excess put.
```
