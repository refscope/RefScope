# REAL BUG: drivers/gpu/drm/i915/i915_vma.c:919 igt_vma_partial()

**Confidence**: HIGH | **Counter**: `$->flags.counter`

## Reasoning

All other `goto out_object` paths (before any `i915_vma_pin`, or after `i915_vma_unpin`) are balanced. The three **LEAK** paths above correspond exactly to the `refcount leak` warning on `$->flags.counter` (the VMA pin count) reported at line 919.

## Full Response

```
## Path Table

The function `igt_vma_partial` contains multiple return paths via `goto out_object`. The relevant `i915_vma_pin` / `i915_vma_unpin` pairs occur in two areas: the inner loop for partial mappings and the outer block for the full mapping. The table lists every `goto out_object` path that follows a call to `i915_vma_pin`.

| Line (approx) | Return Type / Trigger | GET Done? | PUT Done? | Balanced? | Notes |
|---------------|------------------------|-----------|-----------|-----------|-------|
| L843 (pin error) | `i915_vma_pin` fails → `goto out_object` | NO (pin failed) | N/A | ✅ | pin didn’t increment |
| L~855 (assert_pin fail, inner loop) | `assert_pin` returns false → `goto out_object` | YES | NO  | ❌ LEAK | `i915_vma_unpin` never called |
| L~862 (assert_partial fail, inner loop) | `assert_partial` returns false → `goto out_object` | YES | NO  | ❌ LEAK | `i915_vma_unpin` never called |
| L~873 (unbind error, inner loop) | `i915_vma_unbind_unlocked` fails → `goto out_object` | YES (earlier) | YES (already unpinned) | ✅ | unpin already done at L~869 |
| L~895 (pin error, full mapping) | `i915_vma_pin` fails → `goto out_object` | NO (pin failed) | N/A | ✅ | |
| L~904 (assert_pin fail, full mapping) | `assert_pin` returns false → `goto out_object` | YES | NO  | ❌ LEAK | `i915_vma_unpin` never called |
| L~912 (unbind error, full mapping) | `i915_vma_unbind_unlocked` fails → `goto out_object` | YES (earlier) | YES (already unpinned) | ✅ | unpin already done before unbind |

All other `goto out_object` paths (before any `i915_vma_pin`, or after `i915_vma_unpin`) are balanced. The three **LEAK** paths above correspond exactly to the `refcount leak` warning on `$->flags.counter` (the VMA pin count) reported at line 919.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
`i915_vma_pin` increments a refcount that must be released via `i915_vma_unpin`. Three error paths (after assert_pin/assert_partial failures) skip the unpin before jumping to `out_object`, leaking the pin count.
```
