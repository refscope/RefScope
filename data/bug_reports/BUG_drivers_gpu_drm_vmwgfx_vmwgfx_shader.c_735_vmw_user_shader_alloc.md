# REAL BUG: drivers/gpu/drm/vmwgfx/vmwgfx_shader.c:735 vmw_user_shader_alloc()

**Confidence**: HIGH | **Counter**: `ushader->base.refcount.refcount.refs.counter`

## Reasoning

| L723 (goto out_err) | error (ttm_base_object_init failed) | YES (unconditional get) | NO (missing ttm_base_object_unref) | ❌ LEAK | out_err only unreferences tmp/res, not base refcount |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L699 | error (-ENOMEM) | NO (ushader alloc failed) | N/A | ✅ | base object not allocated |
| L714 | error (vmw_gb_shader_init failed) | NO (before ttm_base_object_init) | N/A | ✅ | base object not initialized |
| L726 | success (ret=0) | YES (ttm_base_object_init succeeded) | N/A (ownership transferred to ttm system) | ✅ | destructor vmw_user_shader_free will release base when resource freed |
| L723 (goto out_err) | error (ttm_base_object_init failed) | YES (unconditional get) | NO (missing ttm_base_object_unref) | ❌ LEAK | out_err only unreferences tmp/res, not base refcount |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
ttm_base_object_init always increments the base object’s refcount; the error path at L723 jumps to out_err without calling ttm_base_object_unref(), leaking the refcount.
```
