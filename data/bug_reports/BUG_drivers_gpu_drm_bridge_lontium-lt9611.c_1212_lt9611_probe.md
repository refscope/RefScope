# REAL BUG: drivers/gpu/drm/bridge/lontium-lt9611.c:1212 lt9611_probe()

**Confidence**: HIGH | **Counter**: `lt9611->dsi0_node->kobj.kref.refcount.refs.counter`

## Reasoning

*`lt9611_parse_dt` is marked unconditional and contains `of_graph_get_remote_node(get)`. If the function fails after acquiring a node pointer, the reference is held; probe’s direct `return ret` does not release it. All other error paths in this function call `of_node_put`.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1105 | error       | NO (before parse_dt) | N/A  | ✅ | i2c check failed, no DT activity |
| L1113 | error       | NO (alloc failed) | N/A  | ✅ | dt not parsed yet |
| L1122 | error       | NO (regmap failed) | N/A  | ✅ | dt not parsed yet |
| L1129 | error (parse_dt fails) | YES* | NO   | ❌ LEAK | `lt9611_parse_dt` does unconditional gets (per contract), but probe returns directly without `of_node_put` |
| L1132 | goto `err_of_put` | YES | YES  | ✅ | `of_node_put` called on both nodes |
| L1136 | goto `err_of_put` | YES | YES  | ✅ | `of_node_put` called on both nodes |
| L1142 | goto `err_of_put` | YES | YES  | ✅ | `of_node_put` called on both nodes |
| L1149 | goto `err_disable_regulators` | YES | YES  | ✅ | falls through to `err_of_put` |
| L1155 | goto `err_disable_regulators` | YES | YES  | ✅ | falls through to `err_of_put` |
| L1169 | goto `err_remove_bridge` | YES | YES  | ✅ | falls through to `err_disable_regulators` → `err_of_put` |
| L1175 | goto `err_remove_bridge` | YES | YES  | ✅ | falls through to `err_of_put` |
| L1179 | success     | YES | NO (by design) | N/A  | references held for driver lifetime; released in remove path |

*`lt9611_parse_dt` is marked unconditional and contains `of_graph_get_remote_node(get)`. If the function fails after acquiring a node pointer, the reference is held; probe’s direct `return ret` does not release it. All other error paths in this function call `of_node_put`.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`lt9611_probe` misses `of_node_put` on the error exit after `lt9611_parse_dt` failure, leaking a device node reference unlike every other error path which use the `err_of_put` cleanup label.
```
