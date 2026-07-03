# REAL BUG: drivers/gpu/drm/bridge/lontium-lt9611uxc.c:876 lt9611uxc_probe()

**Confidence**: HIGH | **Counter**: `lt9611uxc->dsi0_node->kobj.kref.refcount.refs.counter`

## Reasoning

| L867 | success (return 0) | YES | NO (held for device lifetime) | ✅ (if remove() puts) | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L748 | error (-ENODEV) | NO (before parse) | N/A | ✅ | |
| L753 | error (PTR_ERR) | NO (before parse) | N/A | ✅ | |
| L762 | error (PTR_ERR) | NO (before parse) | N/A | ✅ | |
| L768 | error (ret)     | YES (parse_dt may set dsi0_node) | NO | ❌ LEAK | Parse fails after obtaining ref; no put. |
| L773 | goto err_of_put | YES | YES (via err_of_put) | ✅ | |
| L777 | goto err_of_put | YES | YES (via err_of_put) | ✅ | |
| L783 | goto err_of_put | YES | YES (via err_of_put) | ✅ | |
| L790 | goto err_disable_regulators | YES | YES (falls through to err_of_put) | ✅ | |
| L797 | goto err_disable_regulators | YES | YES | ✅ | |
| L804 | goto err_disable_regulators | YES | YES | ✅ | |
| L810 | goto err_disable_regulators | YES | YES | ✅ | |
| L825 | goto err_disable_regulators | YES | YES | ✅ | |
| L855 | goto err_remove_bridge | YES | YES (falls through to err_disable_regulators → err_of_put) | ✅ | |
| L863 | goto err_remove_bridge | YES | YES | ✅ | |
| L867 | success (return 0) | YES | NO (held for device lifetime) | ✅ (if remove() puts) | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`lt9611uxc_parse_dt` obtains `dsi0_node` reference via `of_graph_get_remote_node`; on failure (L768) probe returns without `of_node_put`, leaking the reference.
```
