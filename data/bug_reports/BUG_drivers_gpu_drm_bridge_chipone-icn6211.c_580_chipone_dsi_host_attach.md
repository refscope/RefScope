# REAL BUG: drivers/gpu/drm/bridge/chipone-icn6211.c:580 chipone_dsi_host_attach()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L580 | success (ret ≥ 0) | YES | NO | ❌ LEAK | host reference never released |

## Full Response

```
```
| Line | Return Type | Host GET? (of_find_mipi_dsi_host_by_node) | Host PUT? | Balanced? | Notes |
|------|-------------|-------------------------------------------|-----------|-----------|-------|
| L551 | error (!host_node) | NO (host_node NULL) | N/A | ✅ | No host reference taken |
| L555 | error (!host) | NO (host is NULL) | N/A | ✅ | of_find_… returned NULL |
| L559 | error (IS_ERR(dsi)) | YES (host non-NULL) | NO | ❌ LEAK | host reference never released |
| L580 | attach error (ret < 0) | YES | NO | ❌ LEAK | falls through from L567; host not released |
| L580 | success (ret ≥ 0) | YES | NO | ❌ LEAK | host reference never released |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_find_mipi_dsi_host_by_node` returns a host device with a reference taken; all paths after a successful call leak that reference because `mipi_dsi_host_put`/`put_device` is never called.```
```
