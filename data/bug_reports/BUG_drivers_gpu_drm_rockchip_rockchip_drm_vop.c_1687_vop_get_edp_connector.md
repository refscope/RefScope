# REAL BUG: drivers/gpu/drm/rockchip/rockchip_drm_vop.c:1687 vop_get_edp_connector()

**Confidence**: HIGH | **Counter**: `$->conn->base.refcount.refcount.refs.counter`

## Reasoning

er_end` released it. Function name indicates it should return with a reference, but it does not. This causes an eventual excess `drm_connector_put` by the caller. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1681 (success) | `struct drm_connector *` | YES (via `drm_connector_list_iter_next`) | YES (via `drm_connector_list_iter_end`) | ❌ (locally balanced but returns connector with no reference → caller will later underflow) | Iterator acquired a reference; `drm_connector_list_iter_end` released it. Function name indicates it should return with a reference, but it does not. This causes an eventual excess `drm_connector_put` by the caller. |
| L1687 (NULL)    | `NULL`                     | NO  (end of iteration, no connector) | N/A (no reference)                    | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`vop_get_edp_connector` finds the eDP connector but calls `drm_connector_list_iter_end` (which drops the iterator's reference) before returning the pointer; the caller expects a referenced connector (as implied by the "get" name), leading to a refcount underflow when the caller later calls `drm_connector_put` – the missing `drm_connector_get()` is the root cause.
```
