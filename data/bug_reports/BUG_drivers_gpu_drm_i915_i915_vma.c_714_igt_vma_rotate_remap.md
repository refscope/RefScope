# REAL BUG: drivers/gpu/drm/i915/i915_vma.c:714 igt_vma_rotate_remap()

**Confidence**: HIGH | **Counter**: `$->flags.counter`

## Reasoning

| L694–697 | goto out_object (after i915_vma_unpin) | YES (pin succeeded) | YES (unpin called) | ✅ | unpin released the pin; unbind error path safe |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L585 | goto out | NO (obj alloc failed) | N/A | ✅ | |
| L608 | goto out_object | NO (vma instance failed) | N/A | ✅ | |
| L613 | goto out_object | NO (pin returned error) | N/A | ✅ | pin failed, no ref held |
| L629 | goto out_object | YES (pin succeeded) | NO | ❌ LEAK | size check fails, skip unpin |
| L635 | goto out_object | YES | NO | ❌ LEAK | remapped size check fails |
| L642 | goto out_object | YES | NO | ❌ LEAK | sg nents check fails |
| L649 | goto out_object | YES | NO | ❌ LEAK | node size check fails |
| L655 | goto out_object | YES | NO | ❌ LEAK | unrotated pages check fails |
| L682 | goto out_object | YES | NO | ❌ LEAK | assert_rotated/remapped fails |
| L694–697 | goto out_object (after i915_vma_unpin) | YES (pin succeeded) | YES (unpin called) | ✅ | unpin released the pin; unbind error path safe |
| after loops | fall‑through to out_object | N/A (last iteration already unpinned) | N/A | ✅ | no outstanding vma reference |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`i915_vma_pin(vma, …)` on success increments a pin refcount; all error paths at L629/L635/L642/L649/L655/L682 jump to `out_object` which only calls `i915_gem_object_put(obj)` without unpinning the VMA, leaking the pin reference.
```
