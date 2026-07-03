# REAL BUG: drivers/gpu/drm/i915/gem/i915_gem_execbuffer.c:939 eb_lookup_vma()

**Confidence**: HIGH | **Counter**: `vma->obj.base.refcount.refcount.refs.counter`

## Reasoning

| ~944 (err == -EEXIST, loop restart) | continue loop | YES (from i915_vma_instance) | NO (vma not put before next iteration) | ❌ LEAK | vma leaked; the loop may later return a different vma, leaving this vma and its backing object unreleased. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~907 (after i915_vma_tryget) | return vma (non‑NULL) | YES (i915_vma_tryget incremented obj refcount) | NO (no put in this function — caller will i915_vma_put) | ✅ | Reference from tryget is returned; caller owns it. |
| ~912 (obj lookup failed) | return ERR_PTR(-ENOENT) | NO (no vma get) | N/A | ✅ | |
| ~922 (protected content check err) | return ERR_PTR(err) | NO | N/A | ✅ | obj put done |
| ~929 (IS_ERR(vma)) | return ERR_PTR | NO (vma not obtained) | N/A | ✅ | obj put done |
| ~938 (__eb_add_lut success) | return vma (non‑NULL) | YES (from i915_vma_instance and __eb_add_lut’s get) | NO (function returns vma; caller releases later) | ✅ | Returned vma has instance reference; __eb_add_lut’s internal get is kept in the lut. Balanced when caller puts vma. |
| ~942 (err != -EEXIST, return) | return ERR_PTR(err) | YES (from i915_vma_instance) | NO (i915_vma_put missing) | ❌ LEAK | Instance reference on vma leaked, so underlying object refcount never decremented. |
| ~944 (err == -EEXIST, loop restart) | continue loop | YES (from i915_vma_instance) | NO (vma not put before next iteration) | ❌ LEAK | vma leaked; the loop may later return a different vma, leaving this vma and its backing object unreleased. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`i915_vma_instance` returns a vma with a reference; on the `__eb_add_lut` failure paths (both the `-EEXIST` loop‑restart and the final `return ERR_PTR`), the vma’s reference (and consequently the object refcount) is never put, causing a persistent object refcount leak.
```
