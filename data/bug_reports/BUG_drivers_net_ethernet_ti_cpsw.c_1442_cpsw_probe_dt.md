# REAL BUG: drivers/net/ethernet/ti/cpsw.c:1442 cpsw_probe_dt()

**Confidence**: HIGH | **Counter**: `node->kobj.kref.refcount.refs.counter`

## Reasoning

| L1442 (end of loop) | success (return 0) | YES | NO | ❌ LEAK | loop completes, no of_node_put(node) |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1285 | error (return -EINVAL) | NO (before get) | N/A | ✅ | node NULL check, no ref |
| L1291 | error (return -EINVAL) | NO (before get) | N/A | ✅ | before of_platform_populate |
| L1299 | error (return -EINVAL) | NO (before get) | N/A | ✅ | before of_platform_populate |
| L1306 | error (return -ENOMEM) | NO (before get) | N/A | ✅ | before of_platform_populate |
| L1312 | error (return -EINVAL) | NO (before get) | N/A | ✅ | before of_platform_populate |
| L1318 | error (return -EINVAL) | NO (before get) | N/A | ✅ | before of_platform_populate |
| L1324 | error (return -EINVAL) | NO (before get) | N/A | ✅ | before of_platform_populate |
| L1334 (call) | resource acquisition | YES (of_platform_populate → of_node_get on node) | N/A | ⚠️ | GET taken unconditionally per contract |
| L1370 (goto err) | error (IS_ERR(ifphy)) | YES | NO (only puts slave_node) | ❌ LEAK | goto err_node_put skips of_node_put(node) |
| L1390 (goto err) | error (fixed-link register fails) | YES | NO | ❌ LEAK | goto err_node_put |
| L1405 (goto err) | error (mdio missing) | YES | NO | ❌ LEAK | goto err_node_put |
| L1420 (goto err) | error (phy_mode missing) | YES | NO | ❌ LEAK | goto err_node_put |
| L1432 (goto err) | error (ti_cm_get_macid fails) | YES | NO | ❌ LEAK | goto err_node_put |
| L1440 (goto err) | i == data->slaves, ret=0 | YES | NO | ❌ LEAK | goto err_node_put (even with ret=0) |
| L1442 (end of loop) | success (return 0) | YES | NO | ❌ LEAK | loop completes, no of_node_put(node) |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_platform_populate()` takes a reference on `node` (as per contracts), but all return paths after the call (both error and success) fail to release it via `of_node_put(node)`.
```
