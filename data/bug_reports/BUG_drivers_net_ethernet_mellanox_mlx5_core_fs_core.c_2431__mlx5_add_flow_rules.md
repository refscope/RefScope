# REAL BUG: drivers/net/ethernet/mellanox/mlx5/core/fs_core.c:2431 _mlx5_add_flow_rules()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

| 2423 (final return) | success/error | fte node ref held | `tree_put_node` if rule error; otherwise transferred | ✅ | handled correctly |

## Full Response

```
```
| Line (exit) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|-------------|-------------|-----------|-----------|-----------|-------|
| 2343 | error       | NO (before GET) | N/A  | ✅ | check_valid_spec() failed |
| 2346 | error       | NO | N/A  | ✅ | autogroup check |
| 2349 | error       | NO | N/A  | ✅ | dest_num check |
| 2353 | error       | NO | N/A  | ✅ | dest_is_valid() failed |
| 2366 (via err path) | error | YES (ft read/write ref) | YES (up_read or up_write) | ✅ | build_match_list() error; appropriate put called |
| 2379 (try_add exit) | success/error | YES (ft write if take_write) | YES (if take_write, up_write; read ref already released) | ✅ | read ref released earlier if take_write false |
| 2395 (g alloc error) | error | YES (ft write) | YES (up_write) | ✅ | ft ref released correctly |
| 2402 (→ err_alloc_fte → 2430) | error | YES (ft write released before goto) | YES (ft released, g->node put via tree_put_node) | ✅ | fte not allocated |
| 2410 (→ err_release_fg → 2430) | error | YES (ft released earlier, g write ref, fte alloc ref) | YES for ft & g (both g refs released) | ❌ **LEAK** | fte allocated with ref, but `kmem_cache_free()` frees without `tree_put_node()` → fte->node ref leaked |
| 2414 (→ err_release_fg → 2430) | error | exactly as above | same | ❌ **LEAK** | same leak |
| 2423 (final return) | success/error | fte node ref held | `tree_put_node` if rule error; otherwise transferred | ✅ | handled correctly |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`alloc_fte()` returns an `fs_fte` with a reference held on its embedded node. On the error paths after `alloc_fte()` succeeds but before `add_rule_fg()` (i.e., `err_release_fg` via `create_auto_flow_group()` failure or `insert_fte()` failure), the fte is freed with `kmem_cache_free()` without ever dropping the node's refcount via `tree_put_node()`. This causes a refcount leak detected at the function's closing brace (line 2431).```
```
