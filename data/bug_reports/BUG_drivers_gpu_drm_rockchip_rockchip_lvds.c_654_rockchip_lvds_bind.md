# REAL BUG: drivers/gpu/drm/rockchip/rockchip_lvds.c:654 rockchip_lvds_bind()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L~653 | Success return (after pm_runtime_enable) | YES for port, NO for remote | YES for port, YES for remote (excess) | ❌ EXCESS PUT | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L~544 | error (port NULL) | NO (no get) | N/A | ✅ | no port, no remote |
| L~560 | `goto err_put_port` (no children or ret) | YES (port from L542) | YES (port only, no remote) | ✅ | remote not set yet |
| L~580 | `goto err_put_remote` (output < 0) | YES for port, NO for remote | YES for port, YES for remote (excess) | ❌ EXCESS PUT | remote never got, but put |
| L~590 | `goto err_put_remote` (format < 0) | same | same | ❌ EXCESS PUT | |
| L~610 | `goto err_put_remote` (encoder init fail) | same | same | ❌ EXCESS PUT | |
| L~620 | `goto err_free_encoder` (panel bridge add fail) → `err_put_remote` | same | same | ❌ EXCESS PUT | |
| L~630 | `goto err_free_bridge` (bridge attach fail) → `err_put_remote` | same | same | ❌ EXCESS PUT | |
| L~640 | `goto err_free_bridge` (connector init fail) → `err_put_remote` | same | same | ❌ EXCESS PUT | |
| L~650 | `goto err_free_bridge` (attach encoder fail) → `err_put_remote` | same | same | ❌ EXCESS PUT | |
| L~653 | Success return (after pm_runtime_enable) | YES for port, NO for remote | YES for port, YES for remote (excess) | ❌ EXCESS PUT | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`remote` is assigned from panel/bridge of_node without `of_node_get`, yet `of_node_put(remote)` is called on every subsequent path (success and all error labels), causing an excess put on the kref.
```
