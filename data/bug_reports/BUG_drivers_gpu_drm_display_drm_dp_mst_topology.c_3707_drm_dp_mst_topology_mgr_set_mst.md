# REAL BUG: drivers/gpu/drm/display/drm_dp_mst_topology.c:3707 drm_dp_mst_topology_mgr_set_mst()

**Confidence**: HIGH | **Counter**: `$->topology_kref.refcount.refs.counter`

## Reasoning

| L3707 (success path, mst_state true) | success | YES (2) | YES (1 put + ownership transfer to primary pointer) | ✅ | Remaining ref held by primary, lifecycle managed by future disable |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3707 (goto out_unlock: mst_state == mgr->mst_state) | error (goto) | NO (before any get) | N/A | ✅ | mstb NULL, no ref held |
| L3707 (goto out_unlock: drm_dp_read_dpcd_caps fails) | error | NO (before get) | N/A | ✅ | mstb NULL, no ref |
| L3707 (goto out_unlock: mstb == NULL from drm_dp_add_mst_branch_device) | error | NO (get failed) | N/A | ✅ | No mstb, no ref |
| L3707 (goto out_unlock: drm_dp_dpcd_write_byte fails) | error | YES (2: add_mst_branch_device + get_mstb) | YES (1 put at out_unlock) | ❌ LEAK | One reference left in mgr->mst_primary, never released on error |
| L3707 (success path, mst_state true) | success | YES (2) | YES (1 put + ownership transfer to primary pointer) | ✅ | Remaining ref held by primary, lifecycle managed by future disable |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the error path where `drm_dp_dpcd_write_byte` fails, the function takes two references (`drm_dp_add_mst_branch_device` initial + `drm_dp_mst_topology_get_mstb`), but only a single `drm_dp_mst_topology_put_mstb` is called at `out_unlock`. The remaining reference is assigned to `mgr->mst_primary` and never released, as MST was not successfully enabled and the caller will not trigger the disable path.
```
