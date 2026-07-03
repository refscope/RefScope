# REAL BUG: drivers/gpu/drm/i915/display/intel_plane.c:1203 add_dma_resv_fences()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L1197 return 0 | success | YES | YES (reference transferred/consumed) | `dma_fence_put(original fence)` for initial GET; `new` ownership passed to plane_state or chain | ✅ | All references balanced |

## Full Response

```
| Line | Return Type | GET Done? (dma_fence_get) | Other GET (dma_resv_get_singleton) | PUT Done? | Balanced? | Notes |
|------|-------------|---------------------------|-----------------------------------|-----------|-----------|-------|
| L1178 goto error | error (ret != 0) | YES (but `fence` may be NULL) | NO (call failed, `new` not set) | `dma_fence_put(fence)` | ✅ | `fence` released; `new` not obtained |
| L1185 goto error | error (-ENOMEM) | YES (non‑NULL `fence`) | YES (non‑NULL `new`) | `dma_fence_put(fence)` only | ❌ LEAK | `new` reference never released |
| L1197 return 0 | success | YES | YES (reference transferred/consumed) | `dma_fence_put(original fence)` for initial GET; `new` ownership passed to plane_state or chain | ✅ | All references balanced |

**PRE-VERDICT CHECKLIST**
1. **“Held for device lifetime”?** No.
2. **“Ownership transferred”?** Not on the error path at L1185 — ownership transfer happens later.  
3. **Unconditional GET?** `dma_fence_get` is unconditional (NULL safe). The `error:` label does put it, but no code puts `new`.  
4. **goto out between GET and PUT?** `goto error` at L1185 goes to a label that only puts `fence`, not `new`. → leak.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The path at L1185 leaks the `dma_fence` reference obtained from `dma_resv_get_singleton` (new) because the error label only calls `dma_fence_put(fence)`. No release of `new` occurs before returning the error.
```
