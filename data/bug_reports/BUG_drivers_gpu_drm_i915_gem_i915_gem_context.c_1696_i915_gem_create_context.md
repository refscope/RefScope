# REAL BUG: drivers/gpu/drm/i915/gem/i915_gem_context.c:1696 i915_gem_create_context()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| L1672| err_ctx label        | YES (for all paths reaching it) | NO (kfree only) | ❌ LEAK | every error path that reaches err_ctx leaks the initial refcount set by kref_init |

## Full Response

```
```
| Line | Return Type          | GET Done? (refcount 1) | PUT Done? | Balanced? | Notes |
|------|----------------------|------------------------|-----------|-----------|-------|
| L1609| error (no ctx)       | NO (ctx alloc fail)    | N/A       | ✅        | no reference to leak |
| L1632| goto err_ctx         | YES (kref_init at L1613) | NO (kfree directly) | ❌ LEAK | ppgtt creation fails, refcount 1 not released |
| L1645| goto err_vm          | YES                    | NO (falls through to err_ctx -> kfree) | ❌ LEAK | user_engines or default_engines error |
| L1657| goto err_engines     | YES                    | NO (falls through to err_vm -> err_ctx -> kfree) | ❌ LEAK | drm_syncobj_create failure |
| L1663| success return       | YES (refcount 1)       | N/A (caller owns) | ✅ | correct, passes reference to caller |
| L1672| err_ctx label        | YES (for all paths reaching it) | NO (kfree only) | ❌ LEAK | every error path that reaches err_ctx leaks the initial refcount set by kref_init |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
kref_init sets the initial refcount to 1 at L1613, but every error path after that line (goto err_ctx for ppgtt failure, goto err_vm, goto err_engines) ultimately executes `kfree(ctx)` without decrementing the refcount.  This leaks the reference counter; the proper fix is to call `i915_gem_context_put(ctx)` on error instead of direct kfree.
```
```
