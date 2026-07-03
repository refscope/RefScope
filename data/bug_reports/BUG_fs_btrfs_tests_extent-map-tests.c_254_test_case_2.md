# REAL BUG: fs/btrfs/tests/extent-map-tests.c:254 test_case_2()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L247→out | fall‑through success path (after `btrfs_free_extent_map`) | YES (third `em`) | YES (`btrfs_free_extent_map` called) | ✅ | reference released before out |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L174 | early return -ENOMEM (first allocation fails) | NO (get failed) | N/A | ✅ | allocation returned NULL |
| L188 | goto out after first `btrfs_add_extent_mapping` failure (ret < 0) | YES (first `em`) | NO | ❌ LEAK | no `btrfs_free_extent_map` on error, `free_extent_map_tree` won't find it |
| L197 | goto out after second allocation fails (`em = NULL`) | NO (second alloc failed) | N/A | ✅ | first `em` already freed on success path, no new ref held |
| L211 | goto out after second `btrfs_add_extent_mapping` failure (ret < 0) | YES (second `em`) | NO | ❌ LEAK | no `btrfs_free_extent_map` before out |
| L219 | goto out after third allocation fails (`em = NULL`) | NO (third alloc failed) | N/A | ✅ | previous `em` already freed, no new ref held |
| L234 | goto out after third `btrfs_add_extent_mapping` failure (ret != 0) | YES (third `em`) | NO | ❌ LEAK | `btrfs_free_extent_map` skipped on error |
| L239 | goto out after third add success but `!em` check | YES (third `em`) | NO? (em NULL, no object) | ✅ | defensive NULL check; `em` is never NULL after add, no real leak |
| L247→out | fall‑through success path (after `btrfs_free_extent_map`) | YES (third `em`) | YES (`btrfs_free_extent_map` called) | ✅ | reference released before out |

**VERDICT: REAL_BUG**
**CONFIDENCE: HIGH**

Three error paths (L188, L211, L234) leak an `extent_map` allocated by `btrfs_alloc_extent_map` (unconditional get) because they jump to `out` without calling `btrfs_free_extent_map`. The `out` label only cleans up the extent tree, which never contains the failed additions.
```
