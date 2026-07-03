# REAL BUG: fs/btrfs/ctree.c:2351 btrfs_search_old_slot()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

- The `done:` label only calls `btrfs_release_path(p)` when `ret < 0`; the success paths rely on the caller to release the path. This does **not** help the `goto again` case, because the path is neither released nor cleaned before the restart.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2274 | early return (search_commit_root) | NO (function never calls `btrfs_get_old_root`) | N/A | ✅ | no ref held |
| L2286 (approx) after `again:` | goto done (`btrfs_get_old_root` returned NULL) | NO (get failed) | N/A | ✅ | b == NULL, no ref |
| L2300 (search error) | goto done (ret < 0) | YES (current `b` stored in `p->nodes[level]` at start of iteration) | YES (`btrfs_release_path(p)` in `done:` because ret < 0) | ✅ | path releases all nodes |
| L2310 (level == 0) | goto done (ret >= 0) | YES | NOT NEEDED (caller will later release path) | ✅ | path holds refs; caller responsible |
| L2320 (level == lowest_level) | goto done (ret >= 0) | YES | NOT NEEDED | ✅ | same as above |
| **L2330 (`read_block_for_search` returns -EAGAIN)** | **goto again** | **YES (previous `btrfs_get_old_root` ref held in `p->nodes`, plus any child ref from `read_block_for_search` if not stored)** | **NO** (`btrfs_release_path(p)` is **not** called before jumping to `again`) | **❌ LEAK** | existing path nodes (including root and any lower nodes) are **not released**; restart overwrites the root node in the path, leaking the old references |
| L2340 (`read_block_for_search` other error) | goto done (ret < 0) | depends (if `read_block_for_search` stores child in path, then yes; otherwise callee should free) | depends | assumed ✅ (callee contracts not provided) | smatch warning not focused here; callee likely handles |
| L2351 (`btrfs_tree_mod_log_rewind` fails) | goto done (ret = -ENOMEM) | NO (old `b` is consumed by the put function; new `b` is NULL) | N/A | ✅ | no leak on this path |
| L2360 (while loop exits, b == NULL) | fallthrough to done (ret = 1, ret >= 0) | YES (all stored nodes in `p->nodes`) | NOT NEEDED (caller releases path) | ✅ | caller’s responsibility |

## Analysis
- **`goto again` from `read_block_for_search`** (approx. L2330) is the critical leak point. When `-EAGAIN` triggers a restart, the function jumps to the `again:` label without calling `btrfs_release_path(p)`.  
  - At this point, `p->nodes[]` still holds references to the root node (from the previous `btrfs_get_old_root`) and any lower-level nodes that have been added during the search.  
  - On the new iteration, the fresh call to `btrfs_get_old_root` will assign a new root buffer to `p->nodes[level]`, overwriting the old pointer **without** freeing the old reference. Any lower-level nodes remain orphaned in the path and are never freed.  
- The `done:` label only calls `btrfs_release_path(p)` when `ret < 0`; the success paths rely on the caller to release the path. This does **not** help the `goto again` case, because the path is neither released nor cleaned before the restart.

## Verdict
**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  
`btrfs_search_old_slot` leaks extent buffer references when it restarts (`goto again`) after `read_block_for
```
