# REAL BUG: drivers/gpu/drm/i915/i915_gem_evict.c:540 i915_gem_evict_vm()

**Confidence**: HIGH | **Counter**: `$->base.refcount.refcount.refs.counter`

## Reasoning

| trylock succeeds → added to eviction_list → later unlock + put | success | GET=YES | PUT=YES | ✅ | |

## Full Response

```
| Line/Pseudo-path | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L471 early return (ggtt_flush error) | error | NO (before any get) | N/A | ✅ | |
| L542 final return (after while loop, all lists processed) | success | depends on individual vmas, overall matched | | ✅ | but see locked-list bug below |
| **locked-list cleanup path: vma added because `!i915_gem_object_get_rcu(vma->obj)` (GET FAILED)** | internal execution, no return | **GET=NO** (conditional get failed, refcount not incremented) | **PUT=YES** (unconditional `i915_gem_object_put` in cleanup loop) | **❌ EXTRA PUT** | **BUG**: put without matching get |
| locked-list cleanup path: vma added because `get_rcu` SUCCEEDED but lock held | internal | GET=YES | PUT=YES | ✅ | |
| trylock fails, `busy_bo` set, break → return `-EBUSY` | error, transfers ref to caller | GET=YES (get_rcu succeeded) | PUT=NO (transferred via `*busy_bo`) | ✅ | comment: "holds ref" |
| trylock fails, no `busy_bo` → put and continue | no return | GET=YES | PUT=YES | ✅ | |
| trylock succeeds → added to eviction_list → later unlock + put | success | GET=YES | PUT=YES | ✅ | |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`i915_gem_object_get_rcu` is a conditional get (only increments on success). In the locked-eviction list path, when the get fails, no reference is taken, yet `i915_gem_object_put` is unconditionally called (only guarded by `!dying_vma`), leading to a put-without-get underflow.
```
