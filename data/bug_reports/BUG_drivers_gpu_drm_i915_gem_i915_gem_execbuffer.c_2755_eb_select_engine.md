# REAL BUG: drivers/gpu/drm/i915/gem/i915_gem_execbuffer.c:2755 eb_select_engine()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| L2750 (return err, success) | success (err=0) | YES | NO | ❌ LEAK | child refs taken at L2703, never put on success path |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2687 | error (IS_ERR(ce)) | NO (before child get) | N/A  | ✅ | CE not valid, no ref held |
| L2692 | error (-EINVAL) | NO (before child get) | N/A  | ✅ | CE put before return |
| L2696 | error (-EINVAL) | NO (before child get) | N/A  | ✅ | CE put before return |
| L2718 (goto err) | error (alloc_state) | YES | YES | ✅ | err label at L2757 puts children + ce |
| L2724 (goto err) | error (alloc_state child) | YES | YES | ✅ | same |
| L2732 (goto err) | error (terminally_wedged) | YES | YES | ✅ | same |
| L2736 (goto err) | error (-ENOENT from tryget fail) | YES | YES | ✅ | same |
| L2750 (return err, success) | success (err=0) | YES | NO | ❌ LEAK | child refs taken at L2703, never put on success path |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Unconditional `intel_context_get(child)` at L2703 leaks refcounts on every child context on the normal success return at L2750; only the error path (err label) calls `intel_context_put(child)`.
```
