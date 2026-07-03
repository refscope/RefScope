# REAL BUG: drivers/pinctrl/renesas/pinctrl-rzv2m.c:420 rzv2m_dt_node_to_map()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

p` then attempts an additional put on an already-freed node, causing the refcount underflow. This is a classic bug when converting a traditional `for_each_child_of_node` loop (which keeps the last child referenced until a manual put) to the scoped variant without adding proper get to stored nodes.

## Full Response

```
| Line | Return Type | GET Done? (child) | PUT Done? (child) | Balanced? | Notes |
|------|-------------|-------------------|-------------------|-----------|-------|
| L396–402 (loop body ret<0 → goto done) | error | YES (current child obtained by `for_each_child_of_node_scoped`) | YES (scoped cleanup releases child before goto) | ✅ | child drops at end of iteration, no lifetime leak |
| L404–408 (second subnode error → goto done) | error | NO (child loop finished, no live child) | N/A | ✅ | |
| L410 (return 0) | success | NO (loop ended, scoped cleanup already released last child) | YES (loop-exit put) | ✅ | |
| L413–417 (fallthrough to done) | error | NO | N/A | ✅ | |
| L418–420 (done: calls `rzv2m_dt_free_map`) | N/A | N/A | N/A | N/A | `free_map` is the site of the excess put; see below |

The main function’s own reference handling for `child` is balanced. The warning “refcount excess put” is triggered by the call to `rzv2m_dt_free_map` at line 420. `rzv2m_dt_free_map` likely calls `of_node_put` on device-node pointers stored by `rzv2m_dt_subnode_to_map`. If `subnode_to_map` does **not** take an explicit `of_node_get`, the nodes were held alive only by the loop’s reference, which is dropped at the end of each iteration (or loop exit). The subsequent `free_map` then attempts an additional put on an already-freed node, causing the refcount underflow. This is a classic bug when converting a traditional `for_each_child_of_node` loop (which keeps the last child referenced until a manual put) to the scoped variant without adding proper get to stored nodes.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`for_each_child_of_node_scoped` drops child after each iteration; `rzv2m_dt_subnode_to_map` likely stores the child pointer without `of_node_get`, so `rzv2m_dt_free_map` later puts an already-freed node.
```
