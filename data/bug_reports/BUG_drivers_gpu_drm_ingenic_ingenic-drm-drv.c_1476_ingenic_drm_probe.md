# REAL BUG: drivers/gpu/drm/ingenic/ingenic-drm-drv.c:1476 ingenic_drm_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1476 | return component_master_add_with_match(...) (error, ret<0) | YES (match holds ref) | NO (component framework does **not** free match on failure; caller must release) | ❌ LEAK | No component_match_free(match) on error; device node reference leaked |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1465 | return ingenic_drm_bind(dev, false) | NO (before get) | N/A | ✅ | IS_ENABLED not set, no node ref taken |
| L1469 | return ingenic_drm_bind(dev, false) | NO (get failed: np == NULL) | N/A | ✅ | of_graph_get_remote_node returned NULL, no ref held |
| L1476 | return component_master_add_with_match(...) (success, ret=0) | YES (match holds ref via drm_of_component_match_add) | YES (ownership transferred to component framework, match freed on unbind) | ✅ | success path; component framework will release via standard cleanup |
| L1476 | return component_master_add_with_match(...) (error, ret<0) | YES (match holds ref) | NO (component framework does **not** free match on failure; caller must release) | ❌ LEAK | No component_match_free(match) on error; device node reference leaked |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`drm_of_component_match_add` stores a node reference inside `match`, but `component_master_add_with_match` failure path returns without freeing `match`, leaking the of_node refcount; probe must check return and call `component_match_free(match)` on error.
```
