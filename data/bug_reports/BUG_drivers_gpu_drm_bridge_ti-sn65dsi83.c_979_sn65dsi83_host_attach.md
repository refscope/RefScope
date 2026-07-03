# REAL BUG: drivers/gpu/drm/bridge/ti-sn65dsi83.c:979 sn65dsi83_host_attach()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L979 | success (0) | YES | NO   | ❌ LEAK | host non-NULL, missing put_device |

## Full Response

```
| Line | Return Type | GET Done? (host) | PUT Done? (host) | Balanced? | Notes |
|------|-------------|------------------|-------------------|-----------|-------|
| L954 | error (-EPROBE_DEFER) | NO (host is NULL, no ref held) | N/A  | ✅ | host is NULL after of_find_mipi_dsi_host_by_node |
| L957 | error (dsi_lanes < 0) | YES | NO   | ❌ LEAK | host non-NULL, missing put_device |
| L961-962 | error (IS_ERR(dsi)) | YES | NO   | ❌ LEAK | host non-NULL, missing put_device |
| L976 | error (attach fail) | YES | NO   | ❌ LEAK | host non-NULL, missing put_device |
| L979 | success (0) | YES | NO   | ❌ LEAK | host non-NULL, missing put_device |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_find_mipi_dsi_host_by_node` acquires a reference on the host device, which is never released on any path where host is non-NULL (success and most error returns).
```
