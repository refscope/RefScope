# REAL BUG: drivers/gpu/drm/sprd/sprd_dsi.c:180 drm_of_panel_bridge_remove()

**Confidence**: HIGH | **Counter**: `bridge->refcount.refcount.refs.counter`

## Reasoning

` internally (the standard DRM pattern: `drm_panel_bridge_remove` does `drm_bridge_remove` + `drm_bridge_put` to drop the list/creation reference). The caller’s additional `drm_bridge_put` then pushes the refcount below zero, causing an “excess put” warning. The imbalance is a real double-put bug.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L167 | error (-ENODEV) | NO (before get) | N/A | ✅ | `remote` NULL, early return |
| L172 | success (return 0) | YES (`of_drm_find_and_get_bridge`) | YES (explicit `drm_bridge_put` at L180) | ❌ **EXCESS PUT** | `drm_panel_bridge_remove` internally does `drm_bridge_put`, making total puts = 2 while GET = 1 – the explicit put at L180 is extra and triggers the refcount warning |

**Note:** The warning line L180 corresponds to the explicit `drm_bridge_put(bridge);` call. The contract states `of_drm_find_and_get_bridge` increments the refcount if the bridge is found. On the success path, this acquisition is followed by `drm_panel_bridge_remove(bridge)`, which also performs a `drm_bridge_put` internally (the standard DRM pattern: `drm_panel_bridge_remove` does `drm_bridge_remove` + `drm_bridge_put` to drop the list/creation reference). The caller’s additional `drm_bridge_put` then pushes the refcount below zero, causing an “excess put” warning. The imbalance is a real double-put bug.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
