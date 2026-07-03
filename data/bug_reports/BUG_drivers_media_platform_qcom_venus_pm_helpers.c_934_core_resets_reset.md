# REAL BUG: drivers/media/platform/qcom/venus/pm_helpers.c:934 core_resets_reset()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

y reset is already asserted, the first `reset_control_assert()` causes a refcount underflow. The function lacks a guard to ensure the resets are in the expected (deasserted) state before the loop.

##

## Full Response

```
# 🔍 Audit Analysis

## Contract Summary
- **GET**: `reset_control_deassert()` — increments `deassert_count`
- **PUT**: `reset_control_assert()` — decrements `deassert_count`

The warning is a **refcount excess put** at line 934 (`reset_control_assert()`), meaning `deassert_count` was **already 0** when the assert was attempted. This is a decrement‑below‑zero bug.

## Function Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L916 | immediate return 0 (no resets) | N/A | N/A | ✅ | No operations performed. |
| L932 (assert fails) | goto err → return ret | NO (deassert not reached) | YES (assert called) | ❌ | PUT without GET; if counter was 0, **excess put here**. |
| L936 (deassert fails) | goto err → return ret | NO (deassert failed) | YES (assert succeeded) | ❌ | PUT succeeded but GET never incremented → net decrement. |
| Loop completes (ret=0) | return 0 (fall to `err`) | YES (all deasserts ok) | YES (all asserts ok) | ✅ | Balanced only if initial counter > 0. |

## Pre‑Verdict Checklist
1. **“Held for device lifetime”?** — Not applicable; this is a temporary reset sequence.  
2. **“Ownership transferred”?** — No transfer; resets remain local.  
3. **Unconditional GET?** — `reset_control_deassert` is a GET (increments), but the function calls `assert` first **without ensuring the reset is currently deasserted**.  
4. **goto out between GET and PUT?** — Not applicable; the danger is calling **PUT first** when counter is already 0.

## Root Cause
`core_resets_reset()` blindly asserts every reset line without checking whether the reset is already asserted (`deassert_count == 0`). If the caller invokes this function while any reset is already asserted, the first `reset_control_assert()` causes a refcount underflow. The function lacks a guard to ensure the resets are in the expected (deasserted) state before the loop.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
`reset_control_assert` at L934 called without verifying `deassert_count > 0` → excess put when counter already 0.
```
