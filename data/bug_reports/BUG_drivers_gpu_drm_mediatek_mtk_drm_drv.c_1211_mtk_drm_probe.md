# REAL BUG: drivers/gpu/drm/mediatek/mtk_drm_drv.c:1211 mtk_drm_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1150 | return 0 (success) | YES (comp_node/mutex_node) | not required (held for device lifetime) | ⚠️ | success path not flagged, but overwritten old refs still leaked |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1069 | return -ENOMEM | NO (before any GET) | N/A | ✅ | early allocation failure |
| ~L1072 | return -ENODEV | NO | N/A | ✅ | mmsys_dev NULL |
| ~L1075 | return -ENODEV | NO | N/A | ✅ | of_id NULL |
| ~L1077 | return -EINVAL | NO | N/A | ✅ | mtk_drm_data NULL |
| ~L1086 | return -ENOMEM | NO | N/A | ✅ | devm_kmemdup fail |
| ~L1089 | return ret | NO | N/A | ✅ | mtk_drm_of_ddp_path_build error |
| ~L1094 | return -ENOMEM | NO | N/A | ✅ | all_drm_private alloc fail |
| L1131 (goto err_node from loop) | error via goto err_node → return ret at L1211 | YES (overwritten previous comp_node/mutex_node references) | partial: puts only current array entries, not overwritten old ones | ❌ LEAK | loop may assign same comp_id multiple times; old reference abandoned and never put |
| L1137 (goto err_node mutex_node null) | error → return ret at L1211 | YES (comp_node references) | partial | ❌ LEAK | overwritten old refs leak |
| L1148 (goto err_pm component_master_add fail) | error → err_node → return ret at L1211 | YES | partial | ❌ LEAK | same overwrite issue |
| L1150 | return 0 (success) | YES (comp_node/mutex_node) | not required (held for device lifetime) | ⚠️ | success path not flagged, but overwritten old refs still leaked |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Direct `of_node_get()` assignments to `private->comp_node[comp_id]` and `private->mutex_node` inside the loop overwrite previous values without releasing the old reference. On any error path returning at line 1211 after the cleanup loop, only the most recent assignments are `of_node_put`, leaving overwritten nodes permanently leaked.
```
