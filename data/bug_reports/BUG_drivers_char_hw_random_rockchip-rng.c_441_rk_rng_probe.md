# REAL BUG: drivers/char/hw_random/rockchip-rng.c:441 rk_rng_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

**Conclusion: REAL_BUG** — missing `reset_control_assert` on error paths after successful deassert.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L394 | error (return -ENOMEM) | NO (before rst) | N/A | ✅ | rst not yet touched |
| L399 | error (return PTR_ERR(base)) | NO (before rst) | N/A | ✅ | rst not yet touched |
| L403-404 | error (return dev_err_probe, clk fail) | NO (before rst) | N/A | ✅ | rst not yet touched |
| L413-414 | error (IS_ERR(rst) inside `if (rst)`) | NO (deassert not reached) | N/A | ✅ | return before deassert, safe |
| L436 | error (pm_runtime_enable fail) | **YES** (deassert done at L418) | **NO** (no reset_control_assert) | ❌ **LEAK** | error path returns without asserting reset |
| L440 | error (hwrng_register fail) | **YES** (deassert done at L418) | **NO** (no reset_control_assert) | ❌ **LEAK** | error path returns without asserting reset |
| L442 | success (return 0) | YES (deassert done) | NO (held for device lifetime) | ✅ **not a leak in probe context** | deassert intentionally held; released by remove() later |

**Reasoning from table:**  
- `reset_control_deassert(rst)` (L418) increments the `deassert_count` refcount.  
- Two error paths after the deassert (L436 and L440) return immediately without calling `reset_control_assert(rst)`.  
- On probe failure, the device will never be fully bound, so `remove()` won't run — those error paths **must** undo the deassert by calling `reset_control_assert()`.  
- No devm mechanism automatically asserts the reset on probe failure; the driver must do it explicitly.  

**Conclusion: REAL_BUG** — missing `reset_control_assert` on error paths after successful deassert.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Two error-return paths (pm_runtime_enable fail, hwrng_register fail) after reset_control_deassert() leak the deassert_count refcount because they skip reset_control_assert().
```
