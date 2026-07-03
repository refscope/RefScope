# REAL BUG: drivers/gpu/drm/drm_mode_object.c:511 drm_mode_obj_get_properties_ioctl()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| (Hidden) `DRM_MODESET_LOCK_ALL_BEGIN` deadlock retry | internal within function | YES (previous iteration) | NO (overwritten) | ❌ LEAK | On retry, `obj = drm_mode_object_find(…)` re‑executes, overwriting the previous reference without `drm_mode_object_put`. Leaked on each retry. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L490 | early `return -EOPNOTSUPP` | NO (before get) | N/A | ✅ | No object acquired |
| L497-498 (`goto out`) | error (ENOENT) | NO (`obj` NULL) | N/A | ✅ | `drm_mode_object_find()` failed |
| L502-503 (`goto out_unref`) | error (EINVAL) | YES | YES (L511) | ✅ | Explicit put on the `out_unref` label |
| L505-508 (falls through to `out_unref`) | success / error | YES | YES (L511) | ✅ | Path always reaches `out_unref` and calls `drm_mode_object_put` |
| (Hidden) `DRM_MODESET_LOCK_ALL_BEGIN` deadlock retry | internal within function | YES (previous iteration) | NO (overwritten) | ❌ LEAK | On retry, `obj = drm_mode_object_find(…)` re‑executes, overwriting the previous reference without `drm_mode_object_put`. Leaked on each retry. |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`DRM_MODESET_LOCK_ALL_BEGIN` can loop on `‑EDEADLK` retries, re‑calling `drm_mode_object_find()` and overwriting `obj` without releasing the prior reference, causing a kref leak.
```
