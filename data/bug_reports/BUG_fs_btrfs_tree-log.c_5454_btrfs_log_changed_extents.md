# REAL BUG: fs/btrfs/tree-log.c:5454 btrfs_log_changed_extents()

**Confidence**: HIGH | **Counter**: `em->refs.refs.counter`

## Reasoning

he initial reference. Entries that are skipped (`continue` due to generation or prealloc) or orphaned by the early `list_del_init(&tree->modified_extents)` in the overflow path are never freed, causing a permanent refcount leak. All return paths eventually exit without freeing these orphaned `em`.

## Full Response

```
| Line | Return Type | GET Done? (implicit list ref) | PUT Done? (free) | Balanced? | Notes |
|------|-------------|-------------------------------|------------------|-----------|-------|
| L5427 (approx) | `return ret;` | YES (for skipped ems removed from `tree->modified_extents`) | NO (skipped ems not freed) | ❌ LEAK | Overflow orphans and ems skipped by `generation < transid` / prealloc conditions are never freed. |
| L5455 (approx) | `return 0;`   | YES (same) | NO | ❌ LEAK | Same leak on success path. |

After the `list_for_each_entry_safe` loop removes entries from `tree->modified_extents`, every removed `extent_map` must be released via `btrfs_free_extent_map` to drop the initial reference. Entries that are skipped (`continue` due to generation or prealloc) or orphaned by the early `list_del_init(&tree->modified_extents)` in the overflow path are never freed, causing a permanent refcount leak. All return paths eventually exit without freeing these orphaned `em`.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
