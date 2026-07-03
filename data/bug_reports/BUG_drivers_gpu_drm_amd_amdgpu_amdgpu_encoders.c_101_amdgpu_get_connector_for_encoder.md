# REAL BUG: drivers/gpu/drm/amd/amdgpu/amdgpu_encoders.c:101 amdgpu_get_connector_for_encoder()

**Confidence**: HIGH | **Counter**: `$->conn->base.refcount.refcount.refs.counter`

## Reasoning

| L98 (return found) – path: loop never matched, `found` stays NULL | normal return | NO (iterator may have released all references; no active ref on NULL) | NO (iter_end is a no-op for NULL) | ✅ | No connector returned, no leak. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L98 (return found) – path: loop found a match | normal return | YES (iterator holds reference from `drm_connector_list_iter_next`) | YES (`drm_connector_list_iter_end` at L97 releases the iterator’s reference) | ❌ IMBALANCE | The function name implies it returns with a reference. The iterator’s reference is released, leaving the returned pointer with no reference. That is a missing get (or an excess put relative to the expected get-function contract). |
| L98 (return found) – path: loop never matched, `found` stays NULL | normal return | NO (iterator may have released all references; no active ref on NULL) | NO (iter_end is a no-op for NULL) | ✅ | No connector returned, no leak. |

**PRE-VERDICT CHECKLIST:**
1. **“Held for device lifetime”?** – Not applicable. The function does not claim lifetime ownership.  
2. **“Ownership transferred”?** – No. The reference is released by `drm_connector_list_iter_end`; no documented cleanup exists for the returned pointer.  
3. **Unconditional GET?** – The iterator’s get (`drm_connector_list_iter_next`) is conditional, but when a match is found, it succeeded, so GET=DONE. The function then puts that reference before returning. Since the function is a `_get_` variant, the put is excess relative to the expected reference-counted return.  
4. **goto out between GET and PUT?** – No goto; the return is reached after the put.

The function `amdgpu_get_connector_for_encoder` is a classic “get” function expected to return a referenced connector, yet it calls `drm_connector_list_iter_end` which releases the only reference it acquired from the iterator, leaving the caller with a stale pointer. The smatch warning correctly flags the put at line 101 as an excess put in this context.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Missing `drm_connector_get()` before `drm_connector_list_iter_end()` – the iterator’s reference is dropped, but the function must return an owned reference; without the extra get the returned pointer is unreferenced and unsafe.
```
