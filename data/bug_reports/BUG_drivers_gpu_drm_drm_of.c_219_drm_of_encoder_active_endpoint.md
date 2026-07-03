# REAL BUG: drivers/gpu/drm/drm_of.c:219 drm_of_encoder_active_endpoint()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

e_put(ep)` when the loop continues to the next iteration or when the loop ends without a match. Consequently, every endpoint that does not match `crtc->port` leaks a device_node reference. The final `return -EINVAL` at line 219 therefore leaves multiple references unreleased, matching the warning.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L202 | error (-EINVAL) | NO (before loop) | N/A | ✅ | Early return if !node \|\| !crtc; no gets executed |
| ~L216 (if match) | return ret (loop) | YES (ep from macro) | YES (of_node_put(ep)) | ✅ | Match found; ep put before return |
| L219 | error (-EINVAL) | YES (multiple ep from macro) | NO (no of_node_put(ep) in non‑match iterations) | ❌ LEAK | Loop exits without releasing each endpoint reference taken by for_each_endpoint_of_node |

**Analysis**:  
The macro `for_each_endpoint_of_node` internally calls `of_graph_get_next_endpoint`, which returns each child node with an additional reference. The current code never calls `of_node_put(ep)` when the loop continues to the next iteration or when the loop ends without a match. Consequently, every endpoint that does not match `crtc->port` leaks a device_node reference. The final `return -EINVAL` at line 219 therefore leaves multiple references unreleased, matching the warning.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Missing `of_node_put(ep)` inside the non‑matching loop path causes a refcount leak on each endpoint iteration; the final return after the loop leaks all accumulated references.
```
