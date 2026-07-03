# REAL BUG: drivers/gpu/drm/tegra/sor.c:3173 tegra_sor_init()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

- The success path leaves the reset deasserted for the device lifetime, which is acceptable (the put will happen in the remove callback).

## Full Response

```
## Path Table

| Line (approx) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|---------------|-------------|-----------|-----------|-----------|-------|
| L3081 (`return err` after tegra_output_init) | error | NO (before get) | N/A | ✅ | No reset deassert yet |
| L3089 (`return err` after drm_dp_aux_attach) | error | NO | N/A | ✅ | No reset deassert yet |
| L3099 (`return err` after pm_runtime_resume_and_get) | error | NO | N/A | ✅ | Inside `if (sor->rst)` but before deassert |
| L3105 (`goto rpm_put` after reset_control_acquire error) | error | NO | N/A | ✅ | Before deassert |
| L3111 (`goto rpm_put` after reset_control_assert error) | error | NO | N/A | ✅ | Before deassert |
| L3118 (`goto rpm_put` after clk_prepare_enable(sor->clk) error) | error | NO (deassert not reached) | N/A | ✅ | Before deassert block |
| L3129 (`goto rpm_put` if reset_control_deassert fails) | error | NO (deassert failed) | N/A | ✅ | Error path – deassert didn’t succeed, so counter not incremented |
| L3170 (`return err` after clk_safe fail) | error | YES | NO | ❌ LEAK | Deassert succeeded earlier; no assert call before return |
| L3173 (`return err` after clk_dp fail) | error | YES | NO | ❌ LEAK | Same – deassert succeeded, no assert |
| L3185 (`return 0` success) | success | YES | NO | ✅ (held for lifetime) | Reset stays deasserted for device operation; assert in remove path |

**Details**  
- `reset_control_deassert()` (the GET) is called at L3159 inside the second `if (sor->rst)` block.  
- On its error path (L3161) we `goto rpm_put` without incrementing the counter → balanced.  
- After the deassert block, `reset_control_release` and `pm_runtime_put` are called, but **no `reset_control_assert` is ever called** in this function.  
- The two later error paths (L3170, L3173) return after successful deassert without asserting the reset, causing a refcount imbalance.  
- The success path leaves the reset deasserted for the device lifetime, which is acceptable (the put will happen in the remove callback).  

## VERDICT: REAL_BUG  
## CONFIDENCE: HIGH  

After `reset_control_deassert` succeeded, the error returns for `clk_safe` and `clk_dp` enable failures (lines ≈3170 and 3173) do not call `reset_control_assert` to undo the deassert, leaking the `deassert_count` reference.
```
