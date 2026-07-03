# REAL BUG: drivers/gpu/drm/i915/gem/i915_gem_execbuffer.c:979 eb_lookup_vmas()

**Confidence**: HIGH | **Counter**: `vma->obj.base.refcount.refcount.refs.counter`

## Reasoning

| L972 | error (userptr init, after add) | YES | NO (but ownership transferred) | ✅ (caller cleans up) | vma already added to eb, caller’s cleanup path releases all vmas |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L956 | error (IS_ERR) | NO (vma=NULL, no get) | N/A | ✅ | `eb_lookup_vma` failed, no vma reference taken |
| L962 | error (validate) | YES | YES | ✅ | explicit `i915_vma_put(vma)` before return |
| L967 | error (`eb_add_vma`) | YES | NO | ❌ LEAK | missing `i915_vma_put(vma)` — add failed, ownership NOT transferred |
| L972 | error (userptr init, after add) | YES | NO (but ownership transferred) | ✅ (caller cleans up) | vma already added to eb, caller’s cleanup path releases all vmas |
| L979 | success | YES (all added) | NO (caller owns) | ✅ | all vmas owned by eb, released when eb is destroyed |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`i915_vma_put` is missing at line 967 after `eb_add_vma` fails, leaking the vma reference obtained by `eb_lookup_vma`.
```
