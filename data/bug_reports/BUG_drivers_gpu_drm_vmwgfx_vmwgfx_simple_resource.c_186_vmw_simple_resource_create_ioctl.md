# REAL BUG: drivers/gpu/drm/vmwgfx/vmwgfx_simple_resource.c:186 vmw_simple_resource_create_ioctl()

**Confidence**: HIGH | **Counter**: `usimple->base.refcount.refcount.refs.counter`

## Reasoning

| L186+ (success) | success | YES | N/A (ownership transferred to ttm) | ✅ | base object owned by ttm subsystem; no explicit put needed |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L155 (kzalloc fail) | error | NO (before `ttm_base_object_init`) | N/A | ✅ | allocation failed, no base object |
| L168 (simple_init fail) | error | NO (before `ttm_base_object_init`) | N/A | ✅ | init failed, base not touched |
| L182-L184 (ttm_base_object_init fail) | error | YES (unconditional get per contract) | NO (no `ttm_base_object_unref` called) | ❌ LEAK | goto out_err only releases res/tmp, skips base put |
| L186+ (success) | success | YES | N/A (ownership transferred to ttm) | ✅ | base object owned by ttm subsystem; no explicit put needed |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

`ttm_base_object_init` is an unconditional get that always increments the base object’s refcount. On error (`ret` non-zero), the code does `vmw_resource_unreference(&tmp)` and `goto out_err` → `vmw_resource_unreference(&res)`, but never calls `ttm_base_object_unref`, leaking the base object’s reference. The success path is correct as ownership is transferred, but the error path requires a put.
```
