# REAL BUG: drivers/gpu/drm/bridge/tc358767.c:2314 tc_mipi_dsi_host_attach()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L2313 | success (return 0) | YES (host != NULL) | NO | ❌ LEAK | host reference from of_find not released |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2292 | error (host == NULL) | NO (of_find returned NULL) | N/A | ✅ | host is NULL, no ref held |
| L2295 | error (dsi_lanes < 0) | YES (host != NULL) | NO | ❌ LEAK | host reference from of_find not released |
| L2298 | IS_ERR(dsi) error | YES (host != NULL) | NO | ❌ LEAK | host reference from of_find not released |
| L2310 | error (ret < 0) | YES (host != NULL) | NO | ❌ LEAK | host reference from of_find not released |
| L2313 | success (return 0) | YES (host != NULL) | NO | ❌ LEAK | host reference from of_find not released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_find_mipi_dsi_host_by_node()` returns a `struct mipi_dsi_host *` with an incremented kref (via `bus_find_device`). All paths after the NULL check leak this reference because no corresponding `put_device(host->dev)` (or equivalent) is called. The `of_node_put` calls at L2289/L2290 release node references, not the host's device kref.
```
