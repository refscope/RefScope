# REAL BUG: drivers/gpu/drm/vmwgfx/vmwgfx_fence.c:342 vmw_user_fence_create()

**Confidence**: HIGH | **Counter**: `ufence->base.refcount.refcount.refs.counter`

## Reasoning

4. **goto out between GET and PUT?** The `goto out_err` label does not contain any base object put; it only unreferences the fence. → Leak.

## Full Response

```
## Path Table

| Line (approx) | Return Type        | GET Done? | PUT Done?              | Balanced? | Notes |
|---------------|--------------------|-----------|------------------------|-----------|-------|
| L303          | goto out_no_object | NO        | N/A                    | ✅        | allocation failed, no base object |
| L309          | goto out_no_object | NO        | N/A                    | ✅        | fence init failed, ufence freed, no base object init yet |
| L327, L335    | goto out_err       | YES (ttm_base_object_init unconditional) | NO (only fence unreference, no base object unreference) | ❌ LEAK | base object refcount not released |
| L334          | return 0           | YES       | held for lifecycle     | ✅        | base object referenced, managed by ttm file |

## Pre-Verdict Checklist

1. **“Held for device lifetime”?** Only applies to the success path (L334). The error path (L327) is in probe/creation, not covered by deferred release.  
2. **“Ownership transferred”?** No — ownership transfer would only occur if the base object were successfully registered; after `ttm_base_object_init` fails, no transfer has occurred, but a reference is still held.  
3. **Unconditional GET?** `ttm_base_object_init` is marked “unconditional” in the contract — it always increments the refcount. The error path after its call must release that reference.  
4. **goto out between GET and PUT?** The `goto out_err` label does not contain any base object put; it only unreferences the fence. → Leak.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
`ttm_base_object_init` unconditionally acquires a base object reference, but the error path at L327 only drops the fence reference and does not release the base object refcount.
```
