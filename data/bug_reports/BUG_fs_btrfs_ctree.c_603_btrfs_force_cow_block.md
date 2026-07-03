# REAL BUG: fs/btrfs/ctree.c:603 btrfs_force_cow_block()

**Confidence**: HIGH | **Counter**: `cow->refs.refs.counter`

## Reasoning

| L574‑L578 | goto error_unlock_cow after btrfs_free_tree_block fail (else block) | YES (1 ref) | YES (free_extent_buffer) | ✅ | |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L501 | error (IS_ERR(cow)) | NO (allocation failed) | N/A | ✅ | |
| L519‑L521 | goto error_unlock_cow after update_ref_for_cow fail | YES (initial alloc = 1) | YES (free_extent_buffer) | ✅ | |
| L525‑L528 | goto error_unlock_cow after btrfs_reloc_cow_block fail | YES (initial = 1) plus possibly internal gets (unknown) | YES (free_extent_buffer once) | ❓ | If internal gets are not released on error → leak, but primary bug is below |
| L538‑L541 | goto error_unlock_cow after btrfs_tree_mod_log_insert_root fail | YES (1 ref, no refcount_inc yet) | YES (free_extent_buffer) | ✅ | |
| **L550‑L552** | **goto error_unlock_cow after btrfs_free_tree_block fail (root‑node block)** | **YES (2 refs: initial + refcount_inc)** | **NO (only one free_extent_buffer)** | ❌ **LEAK** | Extra ref for root‑>node never released |
| L556‑L560 | goto error_unlock_cow after btrfs_tree_mod_log_insert_key fail | YES (1 ref) | YES (free_extent_buffer) | ✅ | |
| L568‑L571 | goto error_unlock_cow after btrfs_tree_mod_log_free_eb fail | YES (1 ref) | YES (free_extent_buffer) | ✅ | |
| L574‑L578 | goto error_unlock_cow after btrfs_free_tree_block fail (else block) | YES (1 ref) | YES (free_extent_buffer) | ✅ | |
| L591 | success | YES (1 or 2 refs) | NO (handed off to caller + root‑node) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
```
