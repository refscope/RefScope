# REAL BUG: drivers/gpu/drm/drm_exec.c:195 drm_exec_lock_contended()

**Confidence**: MEDIUM | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

refcount, exactly matching the `refcount excess put` warning.

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L170 | return 0    | NO (obj is NULL, no get)          | NO                | ✅ | Early exit, no ref operation |
| L176 | goto error_dropref | IMPLIED (obj from exec->contended, no drm_exec_obj_locked yet) | YES (drm_gem_object_put) | ✅ | Correctly drops the original contended reference |
| L183 | goto error_unlock → fallthrough to error_dropref | **DEPENDS** on drm_exec_obj_locked error semantics | YES (drm_gem_object_put) | ❌ EXCESS if drm_exec_obj_locked already released its reference on error | If the function takes a ref then puts on failure, caller’s put is an extra decrement |
| L186 | return 0    | YES (drm_exec_obj_locked succeeded, took ref) | NO (transferred to exec->prelocked) | ✅ | Reference owned by prelocked, no immediate put |

[NEED_SOURCE] drm_exec_obj_locked

**Reasoning**: The warning points to a `refcount excess put` at the `drm_gem_object_put` in 
`error_dropref`. The only path where `drm_exec_obj_locked` was called and then we fall into 
`error_dropref` is when that function returns an error (L183). The contract for 
`drm_exec_obj_locked` states it always calls `drm_gem_object_get`, but does not specify 
error‑handling behaviour. If, as is typical, `drm_exec_obj_locked` releases the reference it 
acquired when it fails, then the caller’s own `drm_gem_object_put` will double‑decrement the 
refcount, exactly matching the `refcount excess put` warning.

**VERDICT: REAL_BUG**
**CONFIDENCE: MEDIUM**
```
```
