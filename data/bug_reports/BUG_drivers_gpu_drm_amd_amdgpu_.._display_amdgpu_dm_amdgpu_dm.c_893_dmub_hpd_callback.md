# REAL BUG: drivers/gpu/drm/amd/amdgpu/../display/amdgpu_dm/amdgpu_dm.c:893 dmub_hpd_callback()

**Confidence**: HIGH | **Counter**: `$->conn->base.refcount.refcount.refs.counter`

## Reasoning

erence **before** this call. `handle_hpd_rx_irq()` internally does a `drm_connector_put` (as traced by smatch), which now hits a refcount that is already 0-or-less → excess put. |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (ITER) | PUT Done? (ITER) | Balanced? | Notes |
|------|-------------|-------------------|-------------------|-----------|-------|
| L843 | early return (adev NULL) | NO (before iter) | N/A | ✅ | No connector iteration started |
| L848 | early return (notify NULL) | NO | N/A | ✅ | |
| L853 | early return (bad link) | NO | N/A | ✅ | |
| L858 | early return (suspend) | NO | N/A | ✅ | |
| L885 | `drm_connector_list_iter_end()` | YES (implicit via loop) | YES (explicit via `iter_end`) | ✅ | Iterator reference released normally after loop |
| L893 | inside `handle_hpd_rx_irq()` | YES (iterator acquired) | YES (by `iter_end` at L885) | ❌ **EXCESS PUT** | `iter_end` released the iterator's reference **before** this call. `handle_hpd_rx_irq()` internally does a `drm_connector_put` (as traced by smatch), which now hits a refcount that is already 0-or-less → excess put. |
| L896 | function end (hpd_aconnector NULL) | YES (if loop ran) | YES (via `iter_end`) | ✅ | No extra callee call |

## VERDICT: REAL_BUG
CONFIDENCE: HIGH

**Reasoning:**  
`drm_connector_list_iter_next()` (via `drm_for_each_connector_iter`) acquires a reference on the matching connector and stores it in the iterator. At L885, `drm_connector_list_iter_end()` unconditionally releases that reference. Then at L893, `handle_hpd_rx_irq()` is called **without** an active reference, but internally performs a `drm_connector_put()` (excess put) because it expects the caller to hold a reference. The iterator reference was already dropped, so the internal put underflows the refcount.

**Fix:** The iterator reference must be held until **after** `handle_hpd_rx_irq()` (or `handle_hpd_irq_helper()`) returns, by moving `drm_connector_list_iter_end()` after the `if (hpd_aconnector)` block, or by taking an explicit `drm_connector_get()` before calling those handlers.
```
