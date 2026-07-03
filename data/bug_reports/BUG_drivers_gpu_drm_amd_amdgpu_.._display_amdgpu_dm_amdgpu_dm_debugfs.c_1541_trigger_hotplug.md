# REAL BUG: drivers/gpu/drm/amd/amdgpu/../display/amdgpu_dm/amdgpu_dm_debugfs.c:1541 trigger_hotplug()

**Confidence**: HIGH | **Counter**: `$->dc_sink->refcount.refcount.refs.counter`

## Reasoning

unlock (disconnect, local_sink non‑NULL) | NO | YES (dc_sink_release) | ❌ **Excess PUT** | Manual release of link→local_sink. Immediately after, `amdgpu_dm_update_connector_after_detect` (contract: dc_sink_release) releases the same sink via aconnector→dc_sink → double put on the same refcount. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L~1446 | error (return -EINVAL) | N/A | N/A | N/A | Before any dc_sink operations |
| L~1448 | error (size == 0) | N/A | N/A | N/A | |
| L~1452 | error (kcalloc fail) | N/A | N/A | N/A | |
| L~1457 | error (parse fail) | N/A | N/A | N/A | |
| L~1463 | error (param_nums <= 0) | N/A | N/A | N/A | |
| L~1470 | error (mst_root) | N/A | N/A | N/A | mutex unlock and return |
| L~1485 | goto unlock (connect, detect type fail) | NO | NO | N/A | |
| L~1490 | goto unlock (connect, dc_link_detect fail) | NO | NO | N/A | |
| L~1495 | fall through to unlock (connect success) | (amdgpu_dm_update_connector_after_detect does internal get/put, balanced) | N/A | N/A | Not the warned path |
| L1541 | fall through to unlock (disconnect, local_sink non‑NULL) | NO | YES (dc_sink_release) | ❌ **Excess PUT** | Manual release of link→local_sink. Immediately after, `amdgpu_dm_update_connector_after_detect` (contract: dc_sink_release) releases the same sink via aconnector→dc_sink → double put on the same refcount. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The manual `dc_sink_release(link->local_sink)` in the disconnect path is redundant and leads to a double put: the same sink is released again inside `amdgpu_dm_update_connector_after_detect`, triggering the refcount excess warning.
```
