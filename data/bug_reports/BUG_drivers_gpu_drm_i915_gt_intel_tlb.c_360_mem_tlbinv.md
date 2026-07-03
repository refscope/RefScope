# REAL BUG: drivers/gpu/drm/i915/gt/intel_tlb.c:360 mem_tlbinv()

**Confidence**: HIGH | **Counter**: `$->pin_count.counter`

## Reasoning

\* Path becomes reachable because the `for_i915_gem_ww` macro loops after a successful pin, causing a second call to `intel_context_pin_ww`.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L244 (A create fails)              | error return          | NO               | N/A          | ✅ | No ce, no pin |
| L250 (vaddr A fail) → out_a        | goto out_a → return   | NO               | N/A          | ✅ | No pin |
| L256 (B create fails) → out_a      | goto out_a → return   | NO               | N/A          | ✅ | No pin |
| L262 (vaddr B fail) → out_b        | goto out_b → return   | NO               | N/A          | ✅ | No pin |
| L275 (ppgtt create fail) → out_b   | goto out_b → return   | NO               | N/A          | ✅ | No pin |
| L282 (va instance fail) → out_vm   | goto out_vm → return  | NO               | N/A          | ✅ | No pin |
| L288 (vb instance fail) → out_vm   | goto out_vm → return  | NO               | N/A          | ✅ | No pin |
| L298 (IS_ERR(ce)) → break → out_vm | break then return    | NO               | N/A          | ✅ | No pin for this ce |
| L305 (goto err_put: first pin fails) | goto err_put → return | NO (pin failed)  | N/A          | ✅ | pin_ww returned error, no ref held |
| L305 (goto err_put: first pin success, second pin fails)* | goto err_put → return | **YES (first pin)** | **NO** (unpin missing) | ❌ **LEAK** | for_i915_gem_ww loops again; second pin sets err, goto err_put only calls intel_context_put, not unpin |
| L305+ (pin success, second pin also succeeds, then bit loop, normal err_unpin) | err_unpin → err_put → continue | **YES (two pins)** | **YES (one unpin)** | ❌ **LEAK** | double pin, single unpin, net +1 pin count |
| L340 (normal exit after all engines) per-engine balance | return after out_vm/… | YES (each balanced) | YES (each balanced) | ✅ (if no double pin) | overall balanced if missing break absent |

\* Path becomes reachable because the `for_i915_gem_ww` macro loops after a successful pin, causing a second call to `intel_context_pin_ww`.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Missing `break` inside the `for_i915_gem_ww` loop allows `intel_context_pin_ww` to be called a second time after it succeeds; the second invocation either fails (leaving the first pin unreleased via `err_put`) or succeeds (causing a double pin and only one `intel_context_unpin` later). Both leave the `pin_count.counter` elevated at function return.
```
