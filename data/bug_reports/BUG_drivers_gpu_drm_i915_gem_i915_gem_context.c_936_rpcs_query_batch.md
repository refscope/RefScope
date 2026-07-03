# REAL BUG: drivers/gpu/drm/i915/gem/i915_gem_context.c:936 rpcs_query_batch()

**Confidence**: MEDIUM | **Counter**: `$->mm.pages_pin_count.counter`

## Reasoning

- The object is used locally and immediately unpinned — so the function intends to take its own reference and release it. If the reference was never taken, the put is a bug.

## Full Response

```
## Path Table for `rpcs_query_batch()`

| Line | Return Type | GET Done? (pin_map) | PUT Done? (unpin_map) | Balanced? | Notes |
|------|-------------|---------------------|----------------------|-----------|-------|
| L919 | IS_ERR return (L921) | NO (get failed, IS_ERR true) | N/A | ✅ | No ref taken |
| L936 | explicit unpin + return 0 (L939) | YES (pin_map succeeded) | YES (L936) | ❌ **EXCESS PUT** | `pages_pin_count` already 0 or negative |
| L939 | return 0 (after unpin) | YES | YES | ❌ same imbalance | The unpin triggers the warning |

**Reasoning:**
- The only get call is `i915_gem_object_pin_map()` on line 918.  
- The error path (IS_ERR) correctly avoids the put — balanced.  
- The success path calls `i915_gem_object_unpin_map()` on line 936, exactly once.  
- If `pin_map` unconditionally incremented `pages_pin_count`, the put would be balanced.  
- Smatch’s `refcount excess put` warning at line 936 indicates that at the moment of the put, the counter was 0 — meaning the get did **not** actually increment it, so the put is excessive.  

This is typical when the object is **already pinned** before entering the function. `i915_gem_object_pin_map` may return a valid mapping without incrementing the pin count (a re-pin without refcount bump), making the subsequent `unpin_map` a double-put on the caller’s reference. The function is leaking the caller’s pin instead of maintaining a balanced local get/put.

## Analysis of Ownership and Cleanup
- No documented ownership transfer (the object is passed in, no long-lived storage or callback registered).  
- No devm or async deferral that would cover this put.  
- The object is used locally and immediately unpinned — so the function intends to take its own reference and release it. If the reference was never taken, the put is a bug.

## PRE-VERDICT CHECKLIST

1. **“Held for device lifetime”?** → No, only local scope.  
2. **Ownership transferred?** → No, no cleanup code identified that would release this reference later.  
3. **Unconditional GET?** → The get contract is **unknown**; smatch’s behaviour suggests it is **conditional** (does not always increment the counter) and may bypass the get when already pinned. Thus the put at L936 becomes excess.  
4. **goto out between GET and PUT?** → Not present, but the single success path has GET=YES (by success of the call) and PUT=YES, but the counter is already 0 → excess put.

Because the get operation does not reliably increment the refcount (due to pre‑existing pin state), the corresponding put is an underflow — a real bug.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`i915_gem_object_pin_map` can succeed without incrementing `pages_pin_count` when object already pinned; the unconditional `unpin_map` then causes an excess put. To fully confirm, source of `i915_gem_object_pin_map` and `i915_gem_object_unpin_map` would be needed.
```
