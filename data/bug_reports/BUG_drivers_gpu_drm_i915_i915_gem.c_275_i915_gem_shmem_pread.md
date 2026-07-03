# REAL BUG: drivers/gpu/drm/i915/i915_gem.c:275 i915_gem_shmem_pread()

**Confidence**: MEDIUM | **Counter**: `$->mm.pages_pin_count.counter`

## Reasoning

- Error path `err_unpin` correctly pairs a single `unpin_pages` with the successful `pin_pages`, no `finish_access` was called there.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L237 | error (lock_interruptible fail) | NO (before pin) | N/A  | ✅ | |
| L243 | goto err_unlock (pin_pages fails) | NO (pin_pages returns error, no ref) | N/A  | ✅ | |
| L248 | goto err_unpin (prepare_read fails) | YES (pin_pages success) | YES (unpin_pages at err_unpin) | ✅ | |
| L275 (success) | return ret | YES | YES (finish_access) + YES (unpin_pages) → double put? | ❌ LIKELY EXCESS | finish_access is a PUT per contracts, making unpin_pages an extra put on `pages_pin_count` |
| L275 (break on error) | return ret | YES | same double put as above | ❌ LIKELY EXCESS | same path |

[NEED_SOURCE] i915_gem_object_finish_access  
[NEED_SOURCE] i915_gem_object_pin_pages  

**Analysis:**  
- The only GET for `mm.pages_pin_count.counter` is `i915_gem_object_pin_pages()`.  
- Contracts classify both `i915_gem_object_finish_access()` and `i915_gem_object_unpin_pages()` as PUT operations.  
- On the success/break paths (lines after `finish_access` and through the loop), `pin_pages` incremented the counter, `finish_access` likely decremented it, and then the explicit `unpin_pages` at line 275 decrements it again → excess put.  
- This matches smatch’s warning: the put at line 275 finds the counter already zero.  
- Error path `err_unpin` correctly pairs a single `unpin_pages` with the successful `pin_pages`, no `finish_access` was called there.  

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
i915_gem_object_finish_access appears to release the pin reference, causing the later i915_gem_object_unpin_pages at line 275 to be an excess put on mm.pages_pin_count.
```
