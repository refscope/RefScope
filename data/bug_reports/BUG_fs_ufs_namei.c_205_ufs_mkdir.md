# REAL BUG: fs/ufs/namei.c:205 ufs_mkdir()

**Confidence**: HIGH | **Counter**: `$->i_sb->s_remove_count.counter`

## Reasoning

| L194 | return NULL (success) | NO (no dec on inode) | YES (one inc on inode) | ✅ (success) | only one PUT, no GET – valid for success, no leak |

## Full Response

```
| Line | Return Type | GET Done? (s_remove_count) | PUT Done? (s_remove_count) | Balanced? | Notes |
|------|-------------|----------------------------|----------------------------|-----------|-------|
| L179 | goto out_dir (error) | NO (no inode_dec_link_count on new inode) | YES (inode_inc_link_count on dir balanced by inode_dec_link_count) | ✅ | dir balanced, new inode not yet created |
| L189 | goto out_fail (error) | YES (two inode_dec_link_count on inode) | YES (one inode_inc_link_count on inode) | ❌ LEAK | two GETs, one PUT – one extra get |
| L192 | goto out_fail (error) | YES (two inode_dec_link_count on inode) | YES (one inode_inc_link_count on inode) | ❌ LEAK | same extra get as L189 |
| L194 | return NULL (success) | NO (no dec on inode) | YES (one inc on inode) | ✅ (success) | only one PUT, no GET – valid for success, no leak |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the error paths (L189, L192) after `inode_inc_link_count(inode)`, the function calls `inode_dec_link_count(inode)` twice in `out_fail`, but only one `inode_inc_link_count` was performed, causing a net extra get on `s_remove_count.counter`.
```
