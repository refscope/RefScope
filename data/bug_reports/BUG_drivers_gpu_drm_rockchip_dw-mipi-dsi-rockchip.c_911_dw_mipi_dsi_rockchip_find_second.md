# REAL BUG: drivers/gpu/drm/rockchip/dw-mipi-dsi-rockchip.c:911 dw_mipi_dsi_rockchip_find_second()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

The warning on line 911 (final `of_node_put(local)`) is a false trigger as an excess put — the local reference is balanced. However, the function has a **real refcount leak on the device_node** from missing `of_node_put(node)` on the `continue`/iteration paths. This is a confirmable real bug.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 862  | error (local is NULL) | NO (before get) | N/A | ✅ | local not acquired |
| 866  | while loop start (node get) | YES (of_find_compatible_node) | conditional | - | node refcount +1 on each iteration start |
| 871  | continue (self node) | YES (node) | NO (node) | ❌ LEAK | **node acquired but not put before continue** |
| 874  | remote get (of_graph_get_remote_node) | YES (remote) | conditional | - | remote acquires ref if non-NULL |
| 875  | continue (remote == NULL) | YES (node) | NO (node) | ❌ LEAK | **node not put before continue** |
| 888-890 | in special case (remote == local) | YES (remote, node, local) | YES (all three) | ✅ | explicit puts before return |
| 892  | error (pdev NULL) inside special case | YES (remote, node, local) | YES (all three) | ✅ | puts done on L888-890 |
| 896-898 | error (dsi2 NULL) inside special case | YES (remote, node, local) | YES (all three) | ✅ | puts done on L888-890, plus pdev put |
| 901  | success return inside special case | YES (remote, node, local) | YES (all three) | ✅ | pdev reference passed to caller |
| 904  | remote put (after special case false) | YES (remote) | YES (remote) | ✅ | remote released each non-matching iteration |
| 907  | after loop exit (return NULL) | **YES (last node)** | **NO (node)** | **❌ LEAK** | last node from of_find_compatible_node never released |
| 907  | local put on loop exit | YES (local) | YES (local) | ✅ | local correctly released at end |

Path 904 (after special case false) releases remote, but **node** is not released there; it continues via loop to next iteration, which will *overwrite* the node variable with a new reference, leaking the old one. The only way to release the node references accumulated during `continue` or between iterations is to put node before the next `of_find_compatible_node` call. The current code never calls `of_node_put(node)` in the loop body, so every `continue` and every iteration transition leaks the previous node’s reference.

The warning on line 911 (final `of_node_put(local)`) is a false trigger as an excess put — the local reference is balanced. However, the function has a **real refcount leak on the device_node** from missing `of_node_put(node)` on the `continue`/iteration paths. This is a confirmable real bug.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The warning is mis‑categorized as excess put, but the function contains a clear refcount leak on `node` acquired via `of_find_compatible_node` – the `continue` paths and the loop exit fail to release the node reference, leading to a leak that would ultimately trigger refcount imbalance (and likely motivated the checker’s alert even if the type is inaccurate).
```
