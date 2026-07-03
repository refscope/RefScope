# REAL BUG: drivers/gpu/drm/vc4/vc4_drv.c:407 vc4_drm_bind()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

can take a reference on the node or its parent without a corresponding put. The driver’s code only puts the reference from the find; the extra increment remains on all paths after that block, including the success return at line 407. No deferred cleanup or ownership transfer covers this reference.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| (if ret) return ret after of_dma_configure block | error | YES (of_dma_configure incs kref on node or parent) | NO (of_node_put releases only find's ref, not the extra) | ❌ LEAK | of_dma_configure suspected to acquire extra ref |
| devm_drm_dev_alloc IS_ERR return | error | NO (before block) | N/A | ✅ | |
| goto err after drmm_mutex_init | error | YES (block already executed) | NO | ❌ LEAK | same extra ref not released |
| goto err after vc4_bo_cache_init | error | YES | NO | ❌ LEAK | |
| goto err after drmm_mode_config_init | error | YES | NO | ❌ LEAK | |
| goto err after vc4_gem_init | error | YES | NO | ❌ LEAK | |
| goto err after !firmware (inside of_find_compatible_node) | error | NO (that node already put, no extra ref from this block) | N/A | ✅ | |
| goto err after aperture_remove_all_conflicting_devices | error | YES | NO | ❌ LEAK | still holding extra ref from earlier block |
| goto err after component_bind_all | error | YES | NO | ❌ LEAK | firmware already put, but node extra ref remains |
| goto err after devm_add_action_or_reset | error | YES | NO | ❌ LEAK | |
| goto err after vc4_plane_create_additional_planes | error | YES | NO | ❌ LEAK | |
| goto err after vc4_kms_load (<0) | error | YES | NO | ❌ LEAK | |
| goto err after drm_dev_register (<0) | error | YES | NO | ❌ LEAK | |
| return 0 (end, ~line 407) | success | YES | NO | ❌ LEAK | Warning fires here — extra ref not released on success |

**GET source**: `of_dma_configure` (contract unknown). The smatch warning indicates an extra kref increment on the node’s `kobj.kref.refcount` that is never released. The function `of_dma_configure` is called with `node` (from `of_find_matching_node_and_match`), and its internal operation (likely via `of_dma_get_range`) can take a reference on the node or its parent without a corresponding put. The driver’s code only puts the reference from the find; the extra increment remains on all paths after that block, including the success return at line 407. No deferred cleanup or ownership transfer covers this reference.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`of_dma_configure` likely increments a kref without release; all post-block return paths leak the extra reference.
```
