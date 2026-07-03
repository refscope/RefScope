# REAL BUG: drivers/gpu/drm/amd/amdgpu/../display/amdgpu_dm/amdgpu_dm.c:7574 amdgpu_dm_connector_poll()

**Confidence**: MEDIUM | **Counter**: `$->dc_sink->refcount.refcount.refs.counter`

## Reasoning

cal PUT before callee, plus callee’s own PUT path on the same sink | ❌ UNBALANCED → **DOUBLE PUT** | The poll function releases the sink, then the callee at L7574 also executes a `dc_sink_release` on the same sink (likely via a stale pointer), causing `refcount excess put`. This is the bug path. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L7544 | early `return connector->status` | NO (no sink operations) | NO | N/A | No GET/PUT here. |
| L7570 (path: `connector->status == status`) | normal return | NO (callee not called, no local release) | NO | N/A | Block skipped entirely. |
| L7570 (path: `connector->status != status` and `status != disconnected`) | normal return | callee may retain/put internally – GET may occur inside callee | callee may put internally – no local release before callee call | Potentially balanced by callee; no local release → no extra PUT. |
| L7570 (path: `connector->status != status` and `status == disconnected`) | normal return | YES – explicit `dc_sink_release(link->local_sink)` at L7563-7564, **then** `amdgpu_dm_update_connector_after_detect` is called | YES – local PUT before callee, plus callee’s own PUT path on the same sink | ❌ UNBALANCED → **DOUBLE PUT** | The poll function releases the sink, then the callee at L7574 also executes a `dc_sink_release` on the same sink (likely via a stale pointer), causing `refcount excess put`. This is the bug path. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`amdgpu_dm_connector_poll()` releases `link->local_sink` on the disconnected path, then calls `amdgpu_dm_update_connector_after_detect()` which also releases the same sink, leading to a refcount underflow inside the callee at line 7574.
```
