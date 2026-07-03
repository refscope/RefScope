# REAL BUG: fs/btrfs/tests/extent-map-tests.c:457 __test_case_4()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L451→out→L457 | success (fall-through after free) | YES (third alloc) | YES (L451 free) | ✅ | Normal path: alloc, successful add, free em, then out. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L378 | return -ENOMEM (alloc fail) | NO (allocation failed) | N/A | ✅ | First alloc returned NULL, no ref held |
| L392 | goto out (first add error) | YES (em from first alloc) | NO | ❌ LEAK | `btrfs_add_extent_mapping` failed, em not added to tree, caller still owns ref. `out:` only calls `free_extent_map_tree`, which cleans tree, not this dangling em. |
| L400 | goto out (second alloc fail) | NO (allocation failed) | N/A | ✅ | Second alloc returned NULL, no ref held |
| L414 | goto out (second add error) | YES (em from second alloc) | NO | ❌ LEAK | Same pattern as first add error. |
| L422 | goto out (third alloc fail) | NO (allocation failed) | N/A | ✅ | Third alloc returned NULL, no ref held |
| L436 | goto out (third add error) | YES (em from third alloc) | NO | ❌ LEAK | `if (ret)` on add error, no free before goto. |
| L442 | goto out (third add success but em NULL) | AMBIGUOUS (possible consumed) | N/A (if consumed) | ⚠️ UNCLEAR | `btrfs_add_extent_mapping` might free/merge em and set `*em=NULL`. Without its source, cannot confirm leak; but error paths above are definitive. |
| L451→out→L457 | success (fall-through after free) | YES (third alloc) | YES (L451 free) | ✅ | Normal path: alloc, successful add, free em, then out. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`__test_case_4()` allocates extent_map objects via unconditional `btrfs_alloc_extent_map()`, then calls `btrfs_add_extent_mapping()`. On all error returns from that add (L392, L414, L436) the code jumps to `out:` without releasing the extent_map reference, causing a refcount leak. The `out:` label only frees the extent_map tree, not the dangling ems that failed insertion.
```
