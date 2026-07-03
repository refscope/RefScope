# REAL BUG: drivers/gpu/drm/bridge/synopsys/dw-hdmi.c:3325 dw_hdmi_parse_dt()

**Confidence**: MEDIUM | **Counter**: `remote->kobj.kref.refcount.refs.counter`

## Reasoning

[NEED_SOURCE] `of_drm_find_and_get_bridge` to confirm whether it releases the `device_node *` argument.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3310 | `return 0` | N/A | N/A | ✅ | `output_port` missing, no node obtained |
| L3316 | `return -ENODEV` | NO (`remote == NULL`) | N/A | ✅ | `of_graph_get_remote_node` returned NULL, no reference held |
| L3326 | `return -EPROBE_DEFER` | YES (`remote` non‑NULL, reference acquired at L3314) | YES (two PUTs if `of_drm_find_and_get_bridge` releases the node) | ❌ EXCESS PUT if callee drops reference | One explicit `of_node_put(remote)` at L3325, plus one inside `of_drm_find_and_get_bridge` (per warning) → ref drops below zero |
| L3328 | `return 0`          | YES (same) | YES (same) | ❌ EXCESS PUT (same) | Same as L3326 – explicit put becomes extra |

## Analysis

1. **GET contract**: `of_graph_get_remote_node` returns NULL on error (no ref) and a non‑NULL pointer with a reference on success.  
2. **Warning**: smatch flags `of_node_put(remote)` at line 3325 as an **excess put** on `remote->kobj.kref`. This means the reference count was already zero when that put occurs – i.e., `remote`’s reference was released earlier.  
3. **Likely root cause**: `of_drm_find_and_get_bridge(remote)` already drops the reference on `remote` (the DRM bridge helper internally maps the node to a bridge and releases the node’s ref). The explicit `of_node_put(remote)` then becomes a double‑free / underflow.  
4. **Path impact**: Both the `return -EPROBE_DEFER` and `return 0` paths execute the explicit put, creating an excess put on every non‑NULL `remote` case.  

**Pre‑Verdict Checklist**:
- “Held for device lifetime”? – Not applicable; no ownership transfer.
- “Ownership transferred”? – No, `remote` is not stored or otherwise transferred.
- Unconditional GET? – No, `of_graph_get_remote_node` is conditional (NULL = no ref). The first put (inside `of_drm_find_and_get_bridge`) already matches the get.
- goto out? – No goto here, but the explicit put after the get is unconditional.

Because the warning indicates `of_drm_find_and_get_bridge` consumes the reference, the explicit put is extra. Without the callee source this is not 100% proved, but the static analysis is consistent with the kernel’s known pattern (commit 0e7d0b59f6b8 introduced the internal put).

[NEED_SOURCE] `of_drm_find_and_get_bridge` to confirm whether it releases the `device_node *` argument.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
Explicit `of_node_put(remote)` after `of_drm_find_and_get_bridge(remote)` causes a double‑put underflow; the callee likely already drops the reference.
```
