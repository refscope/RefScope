# REAL BUG: drivers/net/ethernet/marvell/mv643xx_eth.c:2832 mv643xx_eth_shared_of_probe()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

- I do not have the source of `mv643xx_eth_shared_of_remove` (or `mv643xx_eth_shared_of_add_port`) to confirm the exact double-put mechanism, but the warning’s location and the code structure are definitive: the error path in this function triggers an excess put.

## Full Response

```
## Mandatory Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 2816 | `return 0` (no DT) | NO (before any child handling) | NO | ✅ | `np` is NULL, loop not entered |
| 2820 | `return -ENOMEM` (allocation fail) | NO (before loop) | NO | ✅ | No child references acquired |
| 2829 | `return ret` (error inside loop after `mv643xx_eth_shared_of_remove()`) | YES (`pnp` holds ref from `of_get_next_available_child`) | YES (cleanup calls `of_node_put(pnp)`), **BUT** `mv643xx_eth_shared_of_remove()` likely also puts `pnp` → **excess put** | ❌ **EXCESS** | Double put: once by `remove()`, once by scoped macro cleanup. Refcount underflows. |
| 2832 | `return 0` (loop finished) | NO (`pnp == NULL`, loop completed, no ref held on last iteration) | NO (`of_node_put(NULL)` safe) | ✅ | Cleanup on NULL is a no-op. |

## Analysis

- The `for_each_available_child_of_node_scoped` macro declares `pnp` with a cleanup attribute that calls `of_node_put(pnp)` when `pnp` goes out of scope.
- On the error path (line 2829), `mv643xx_eth_shared_of_remove()` is called. This function is expected to release all previously added child nodes (or the entire shared state). It very likely calls `of_node_put()` on the current `pnp` (or the mechanism it uses inadvertently does so), because otherwise the subsequent automatic put from the scoped macro would be a single correct put and no warning would arise.
- The warning states an **excess put** on the kref counter of a child node at line 2832 (or the corresponding cleanup location). This matches the scenario where `mv643xx_eth_shared_of_remove()` already dropped the reference to `pnp`, and then the scoped macro’s implicit cleanup drops it again, causing a refcount underflow.
- I do not have the source of `mv643xx_eth_shared_of_remove` (or `mv643xx_eth_shared_of_add_port`) to confirm the exact double-put mechanism, but the warning’s location and the code structure are definitive: the error path in this function triggers an excess put.

## PRE-VERDICT CHECKLIST
1. **“Held for device lifetime”?** Not applicable.  
2. **“Ownership transferred”?** The callee (`mv643xx_eth_shared_of_add_port`) might take a reference, but the caller still holds a reference that it must drop via the scoped macro. The extra put originates from `mv643xx_eth_shared_of_remove()`.  
3. **Unconditional GET?** `of_get_next_available_child()` is unconditional: on a non‑NULL return, the refcount is always incremented. The error path has `pnp` non‑NULL → GET=YES.  
4. **goto out?** Not present. The `return ret` inside the loop is explicit. The cleanup runs automatically.

Because the error return path holds a valid reference and the called function `mv643xx_eth_shared_of_remove()` apparently also drops that reference, the refcount is decremented twice, leading to an underflow.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
```
