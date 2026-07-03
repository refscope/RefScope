# REAL BUG: drivers/gpu/drm/i915/i915_gem_gtt.c:1918 igt_gtt_insert()

**Confidence**: HIGH | **Counter**: `$->flags.counter`

## Reasoning

| L1882, L1888, L1896, L1903 | goto out (eviction loop) | NO (new objects, no `__i915_vma_pin` called) | N/A | ✅ | no pins taken |

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1769 | return -EINVAL | NO (before any filling loop) | N/A | ✅ | |
| L1783 | goto out (filling loop, obj alloc failure) | YES (if previous iteration pinned) | NO | ❌ LEAK | `out` label only unpins pages and puts objects, no `__i915_vma_unpin` |
| L1789 | goto out (filling loop, pin pages failure) | YES (if previous iteration pinned) | NO | ❌ LEAK | same as above |
| L1797 | goto out (filling loop, vma instance failure) | YES (if previous iteration pinned) | NO | ❌ LEAK | |
| L1804 | break (ENOSPC) | NO (current insert failed) | N/A (unpin loop runs later) | ✅ | `break` exits loop; subsequent `list_for_each_entry` unpins all previously pinned VMAs |
| L1809 | goto out (filling loop, non-ENOSPC error) | YES (if previous iteration pinned) | NO | ❌ LEAK | direct goto out skips the explicit unpin loop entirely |
| L1823 | goto out (unpin loop, vma instance error) | YES (all previously pinned VMAs still pinned) | NO for this and remaining | ❌ LEAK | stops loop before calling `__i915_vma_unpin` on any remaining objects |
| L1829 | goto out (unpin loop, node not allocated) | YES | NO for this and remaining | ❌ LEAK | same |
| L1843, L1852, L1859, L1868 | goto out (reinsert loop/hole checks) | NO (earlier pins already released by unpin loop) | N/A | ✅ | the explicit unpin loop already ran |
| L1882, L1888, L1896, L1903 | goto out (eviction loop) | NO (new objects, no `__i915_vma_pin` called) | N/A | ✅ | no pins taken |

## VERDICT: REAL_BUG

CONFIDENCE: HIGH

The filling loop calls `__i915_vma_pin(vma)` after a successful insert (L1812). Any subsequent error path within that loop (`goto out` at L1783, L1789, L1797, L1809) jumps to the `out` label, which only iterates over the `objects` list calling `i915_gem_object_unpin_pages` and `i915_gem_object_put` — it does **not** call `__i915_vma_unpin`. Thus, all VMA pins from previous successful iterations are leaked. Additionally, error paths inside the explicit unpin loop (L1823, L1829) stop the loop prematurely, leaking pins for the current and all later objects. The `out` label lacks the necessary VMA unpin cleanup, causing a refcount imbalance.
```
