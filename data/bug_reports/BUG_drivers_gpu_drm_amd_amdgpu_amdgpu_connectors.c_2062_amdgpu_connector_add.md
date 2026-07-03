# REAL BUG: drivers/gpu/drm/amd/amdgpu/amdgpu_connectors.c:2062 amdgpu_connector_add()

**Confidence**: HIGH | **Counter**: `$->conn->base.refcount.refcount.refs.counter`

## Reasoning

The `failed:` label (L2062) calls `drm_connector_cleanup(connector)` which puts a refcount that was never initialized (no `drm_connector_init_with_ddc` before the goto). All `goto failed` paths above reach this cleanup without the refcount being initialized, causing an excess put.

## Full Response

```
| Line (approx) | Return Type | GET Done? (connector init) | PUT Done? (drm_connector_cleanup) | Balanced? | Notes |
|---------------|-------------|-----------------------------|-----------------------------------|-----------|-------|
| L1602         | early return| No (before alloc)           | No                                | ✅ | connector_type == Unknown, no refcount |
| L1616         | return      | No (before main alloc)      | No                                | ✅ | found existing connector, iter ref released, no main ref |
| L1638         | return      | No (init never set)         | No                                | ✅ | amdgpu_connector alloc failed |
| L1663         | goto failed | No (init not reached)       | Yes                               | ❌ EXCESS PUT | is_dp_bridge kzalloc fail → goto failed before drm_connector_init_with_ddc |
| ~L1730 (DVII/ DVID) | goto failed | No | Yes | ❌ EXCESS PUT | kzalloc fail before init |
| ~L1790 (HDMIA/B) | goto failed | No | Yes | ❌ EXCESS PUT | kzalloc fail before init |
| ~L1850 (DisplayPort) | goto failed | No | Yes | ❌ EXCESS PUT | kzalloc fail before init |
| ~L1910 (eDP)  | goto failed | No | Yes | ❌ EXCESS PUT | kzalloc fail before init |
| ~L1950 (LVDS) | goto failed | No | Yes | ❌ EXCESS PUT | kzalloc fail before init |
| L2035         | success return | Yes (init done)           | No (cleanup deferred)              | ✅ | normal probe success, refcount managed by DRM |

The `failed:` label (L2062) calls `drm_connector_cleanup(connector)` which puts a refcount that was never initialized (no `drm_connector_init_with_ddc` before the goto). All `goto failed` paths above reach this cleanup without the refcount being initialized, causing an excess put.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`drm_connector_cleanup` at L2062 puts an uninitialized refcount because the `goto failed` paths skip `drm_connector_init_with_ddc`.
```
