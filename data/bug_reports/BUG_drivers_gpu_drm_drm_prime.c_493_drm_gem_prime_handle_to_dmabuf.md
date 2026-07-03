# REAL BUG: drivers/gpu/drm/drm_prime.c:493 drm_gem_prime_handle_to_dmabuf()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L462 (export error, IS_ERR) | error (goto out) | OBJ: YES (lookup), export failed → still owned | OBJ: YES (at out) | ✅ | Ref not transferred, put needed. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L436 (obj NULL) | error (goto out_unlock) | OBJ: NO (lookup failed) | OBJ: NO | ✅ | No reference held. |
| L443 (dmabuf from lookup, non‑NULL) | success (goto out) | OBJ: YES (from lookup) | OBJ: YES (at out) | ✅ | Normal put, dmabuf returned with its own get. |
| L449 (obj->import_attach) | success (goto out_have_obj) | OBJ: YES (lookup); DMA_BUF: YES (get_dma_buf) | OBJ: YES (at out); DMA_BUF: put if add fails, else returned | ✅ | obj ref held independently, final put at out correct. |
| L454 (obj->dma_buf) | success (goto out_have_obj) | OBJ: YES; DMA_BUF: YES | OBJ: YES (at out); DMA_BUF: similar | ✅ | Same as above. |
| **L460 (export success)** | **success (fallthrough → out_have_obj → out)** | **OBJ: YES (from lookup), BUT transferred to dmabuf by export** | **OBJ: YES (unconditional drm_gem_object_put at out) → EXTRA** | **❌** | **Ref ownership moved to dmabuf; the put at out is an excess put. On both add‑success and add‑failure subpaths, obj ref is doubly released.** |
| L462 (export error, IS_ERR) | error (goto out) | OBJ: YES (lookup), export failed → still owned | OBJ: YES (at out) | ✅ | Ref not transferred, put needed. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

After `export_and_register_object()` succeeds, the created dma-buf takes ownership of `obj`’s reference (as documented in the comment). The subsequent unconditional `drm_gem_object_put(obj)` at the `out` label releases a reference that is no longer held by this function, causing a refcount underflow (excess put).
```
