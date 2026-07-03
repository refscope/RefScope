# REAL BUG: drivers/gpu/drm/nouveau/dispnv04/dfp.c:198 nouveau_crtc_connector_get()

**Confidence**: HIGH | **Counter**: `$->conn->base.refcount.refcount.refs.counter`

## Reasoning

4. `goto out` between GET and PUT? Not present.

## Full Response

```
| Line | Return Type | GET Done?                     | PUT Done?     | Balanced? | Notes                                                                                                                                                                   |
|------|-------------|-------------------------------|---------------|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| L198 (connector found, break case) | non‑NULL     | YES (by `drm_connector_list_iter_next`; iterator’s ref) | YES (by `drm_connector_list_iter_end`) | ❌ NO – external imbalance | No extra `drm_connector_get` taken; iterator’s ref is dropped by `_iter_end`. Caller receives a pointer with **no reference**, leading to an excess put when it later calls `drm_connector_put`. |
| L198 (no match, NULL case) | NULL         | NO (last `_next` returned NULL, no ref) | YES (iter_end, no‑op) | ✅       | Safe, no object returned.                                                                                                                                              |

**Pre-verdict checklist:**
1. "Held for device lifetime"? Not applicable; there is no device lifetime claim in this function.  
2. Ownership transfer? No – the function returns a raw pointer without a reference, no explicit transfer documented.  
3. Unconditional GET? `drm_connector_list_iter_next` returns a successful GET only on non‑NULL. In the break path, GET succeeded. The return path after break must guarantee the caller a reference, which is missing.  
4. `goto out` between GET and PUT? Not present.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Function `nouveau_crtc_connector_get` returns a DRM connector pointer without holding a reference, while its `_get` suffix and typical DRM API contract imply it should return the connector with a newly acquired reference. The iterator‑internal get/put pair is balanced internally, but no extra `drm_connector_get` is performed before breaking out of the loop, so the caller receives an unreferenced pointer. Any later `drm_connector_put` by the caller will be an unmatched (excess) put, exactly as reported by the warning.
```
