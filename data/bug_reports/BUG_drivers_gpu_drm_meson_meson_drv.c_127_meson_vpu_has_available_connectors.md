# REAL BUG: drivers/gpu/drm/meson/meson_drv.c:127 meson_vpu_has_available_connectors()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

he end of the iteration. This makes the explicit `of_node_put(ep)` on L122 a double‑put, causing the refcount to go below zero (excess). The false‑return path is balanced because it relies solely on the automatic cleanup.

## Full Response

```
| Line | Return Type | GET Done? (ep) | GET Done? (remote) | PUT Done? (ep) | PUT Done? (remote) | Balanced? | Notes |
|------|-------------|----------------|---------------------|----------------|--------------------|-----------|-------|
| L123 (if remote → return true) | success (true) | YES (loop macro ref) | YES (of_graph_get_remote_port) | YES (explicit L122) + YES (auto‑put from loop cleanup) | YES (L121) | ❌ EXCESS | Double put on `ep`: explicit call then macro‑auto‑put; under‑flows refcount |
| L127 (loop exhausted → return false) | false | NO (loop finished, ep=NULL) | NO | N/A | N/A | ✅ | Macro auto‑releases every ep iteration; no outstanding get at function exit |

**Key assumption** (derived from warning type “excess put”): The loop macro `for_each_endpoint_of_node` now performs automatic `of_node_put()` on each endpoint at the end of the iteration. This makes the explicit `of_node_put(ep)` on L122 a double‑put, causing the refcount to go below zero (excess). The false‑return path is balanced because it relies solely on the automatic cleanup.

[NEED_SOURCE] for_each_endpoint_of_node (to confirm auto‑cleanup behaviour)

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
The `of_node_put(ep)` inside the “remote found” branch conflicts with the loop’s built‑in `of_node_put`, creating a double‑put and a refcount underflow.
```
