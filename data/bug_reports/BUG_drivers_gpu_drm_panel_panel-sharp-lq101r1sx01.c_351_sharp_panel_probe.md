# REAL BUG: drivers/gpu/drm/panel/panel-sharp-lq101r1sx01.c:351 sharp_panel_probe()

**Confidence**: HIGH | **Counter**: `secondary->dev.kobj.kref.refcount.refs.counter`

## Reasoning

**Legend**: GET=YES on all paths after line 161 where `dsi_r_host` is non-NULL. PUT=NO because `put_device(&dsi_r_host->dev)` is never called.

## Full Response

```
## Path Table

| Line (file) | Return Type            | GET Done? | PUT Done? | Balanced? | Notes |
|-------------|------------------------|-----------|-----------|-----------|-------|
| L145        | error (OOM/alloc fail) | NO (before get) | N/A | ✅ | `sharp == ERR_PTR` → exit |
| L149        | error (supplies fail)  | NO (before get) | N/A | ✅ | |
| L154        | error (GPIO fail)      | NO (before get) | N/A | ✅ | |
| L159        | error (no remote node) | NO (before get) | N/A | ✅ | |
| L161        | **GET**: `dsi_r_host = of_find_mipi_dsi_host_by_node(dsi_r)` | | | | Inc ref on host device |
| L164        | error (host NULL)      | YES (NULL, no object) | N/A | ✅ | NULL pointer, no ref held |
| L169        | error (register fail)  | YES       | NO        | ❌ LEAK | `devm_mipi_dsi_device_register_full` failed, host ref never released |
| L176        | error (backlight fail) | YES       | NO        | ❌ LEAK | after successful registration, host ref not put |
| L190        | error (attach fail)    | YES       | NO        | ❌ LEAK | host ref not put |
| L194        | success (`return 0`)   | YES       | NO        | ❌ LEAK | host ref never released on normal path |

**Legend**: GET=YES on all paths after line 161 where `dsi_r_host` is non-NULL. PUT=NO because `put_device(&dsi_r_host->dev)` is never called.

## VERDICT: REAL_BUG
CONFIDENCE: HIGH

`of_find_mipi_dsi_host_by_node()` acquires a reference to the secondary DSI host device. The function never calls `put_device(&dsi_r_host->dev)` on any path where the host pointer is non‑NULL, causing a permanent reference leak on all error and success returns after the host lookup (lines 169, 176, 190, 194).
```
