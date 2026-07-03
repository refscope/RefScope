# REAL BUG: drivers/gpu/drm/i915/i915_gem.c:726 i915_gem_shmem_pwrite()

**Confidence**: MEDIUM | **Counter**: `$->mm.pages_pin_count.counter`

## Reasoning

4. **goto out between GET and PUT?** – Not applicable; the success path has no goto, but the suspicious early `finish_access` acts as an extra implicit put.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? (pin_pages) | PUT Done? (unpin_pages) | Balanced? | Notes |
|------|-------------|------------------------|-------------------------|-----------|-------|
| L675 (lock error return) | error | NO (before get) | N/A | ✅ | `i915_gem_object_lock_interruptible` failed |
| L679 (goto `err_unlock` after pin fail) | error | NO (get failed) | N/A (no put) | ✅ | pin_pages failed, so no ref held |
| L683 (goto `err_unpin` after prepare_write fail) | error | YES (pin succeeded) | YES (unpin_pages at `err_unpin`) | ✅ | explicit single put, balanced |
| L726 (success path, explicit `unpin_pages`) | success | YES (pin succeeded) | **YES (explicit `unpin_pages`) + likely YES (implicit `unpin_pages` in `finish_access`)** | ❌ **DOUBLE PUT / EXCESS PUT** | `i915_gem_object_finish_access` (L689) is called **before** the loop and the final explicit unpin. Smatch’s “refcount excess put” on this line indicates `finish_access` already released the pin count, making this explicit unpin a decrement on an already-zero counter. |

## Analysis

- The smatch warning targets `i915_gem_object_unpin_pages(obj)` at the end of the success path (line 726).  
- In the success flow, `i915_gem_object_pin_pages` is called (GET) and succeeds. After `prepare_write`, the code calls `i915_gem_object_finish_access(obj)`.  
- Smatch traces a prior PUT inside `i915_gem_object_finish_access` that already released the pages pin count, so the later explicit `unpin_pages` becomes an **excess put** (underflow).  
- The suspicious early placement of `finish_access` (before the actual page writes, at line ~689) strongly suggests it performs the pin release internally, invalidating the later unpin.  
- If `finish_access` does **not** touch the pin count, the success path would be balanced (one get, one put) and the warning would be a false positive. However, the warning’s specificity and the unusual code order make a real double‑put likely.

**Pre‑verdict checklist:**
1. **“Held for device lifetime”?** – Not applicable; pages are pinned/unpinned per operation.  
2. **“Ownership transferred”?** – No transfer identified.  
3. **Unconditional GET?** – `i915_gem_object_pin_pages` is unconditional on the success path.  
4. **goto out between GET and PUT?** – Not applicable; the success path has no goto, but the suspicious early `finish_access` acts as an extra implicit put.

## Verdict
**VERDICT: REAL_BUG**  
**CONFIDENCE: MEDIUM**  
*(Confidence limited by missing source for `i915_gem_object_finish_access`. Requesting it would confirm the internal unpin.)*

[NEED_SOURCE] i915_gem_object_finish_access
```
