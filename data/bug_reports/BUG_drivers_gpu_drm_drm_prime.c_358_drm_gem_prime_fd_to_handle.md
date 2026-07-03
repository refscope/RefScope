# REAL BUG: drivers/gpu/drm/drm_prime.c:358 drm_gem_prime_fd_to_handle()

**Confidence**: HIGH | **Counter**: `obj->refcount.refcount.refs.counter`

## Reasoning

| L36   | goto fail          | YES: import ref + create_tail  | YES: import ref dropped at L26 + `drm_gem_handle_delete` drops handle ref | ✅ | clean failure after add_buf_handle |

## Full Response

```
```
| Line  | Return Type        | GET Done?                      | PUT Done?                          | Balanced? | Notes |
|-------|--------------------|--------------------------------|------------------------------------|-----------|-------|
| L5    | error              | NO (before any get)            | N/A                                | ✅ | dma_buf_get failed |
| L9    | goto out_put       | NO (found existing handle)     | N/A                                | ✅ | drm_prime_lookup_buf_handle succeeded |
| L17   | goto out_unlock    | NO (import failed)             | N/A                                | ✅ | obj IS_ERR, no ref held |
| L28   | goto out_put (ret≠0) | YES: import ref + create_tail unconditional | NO: only one `drm_gem_object_put` at L26, missing the handle’s reference | ❌ LEAK | create_tail error path, need two puts |
| L34   | success (return 0) | YES: import ref + create_tail  | YES: import ref dropped at L26, handle ref held by handle | ✅ | handle ref transferred |
| L36   | goto fail          | YES: import ref + create_tail  | YES: import ref dropped at L26 + `drm_gem_handle_delete` drops handle ref | ✅ | clean failure after add_buf_handle |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

drm_gem_handle_create_tail is marked unconditional (always increments obj->refcount).  
On the error path after it returns non-zero (L28), the single `drm_gem_object_put` drops only one of the two acquired references, leaking one ref.  
The remaining reference from the handle is never released.
```
