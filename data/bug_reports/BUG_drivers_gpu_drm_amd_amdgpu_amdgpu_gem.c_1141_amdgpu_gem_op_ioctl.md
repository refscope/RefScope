# REAL BUG: drivers/gpu/drm/amd/amdgpu/amdgpu_gem.c:1141 amdgpu_gem_op_ioctl()

**Confidence**: HIGH | **Counter**: `gobj->refcount.refcount.refs.counter`

## Reasoning

| L? (default) | break then return -EINVAL after switch | YES | YES (drm_exec_fini in default, put after switch) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L? (args->padding) | error -EINVAL | NO (before lookup) | N/A | ✅ | No get |
| L? (gobj NULL) | error -ENOENT | NO (lookup failed) | N/A | ✅ | No get |
| L? (drm_exec_lock_obj fails) | goto out_exec | YES (lookup) + GET by drm_exec_lock_obj? (if lock partially succeeded, but exec may hold ref; safe to cleanup) | YES (drm_exec_fini + drm_gem_object_put) | ✅ | out_exec cleans exec and puts lookup ref |
| L? (SET_PLACEMENT errors) | goto out_exec | YES | YES (via out_exec) | ✅ | |
| L? (GET_GEM_CREATE_INFO copy error) | break then return r after switch | YES (lookup + exec) | YES (drm_exec_fini in case, put after switch) | ✅ | |
| L? (GET_MAPPING_INFO kvcalloc NULL) | error -ENOMEM (direct return) | YES (lookup + drm_exec_lock_obj succeeded) | NO (no drm_exec_fini, no drm_gem_object_put) | ❌ LEAK | Ref from drm_gem_object_lookup and exec‑held ref leaked |
| L? (GET_MAPPING_INFO success) | break then return r after switch | YES | YES (drm_exec_fini + put after switch) | ✅ | |
| L? (default) | break then return -EINVAL after switch | YES | YES (drm_exec_fini in default, put after switch) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The early `return -ENOMEM` inside `AMDGPU_GEM_OP_GET_MAPPING_INFO` after successful `drm_exec_lock_obj` leaks both the initial `drm_gem_object_lookup` reference and the exec‑held reference, causing inconsistent refcounting at the function’s exit.
```
