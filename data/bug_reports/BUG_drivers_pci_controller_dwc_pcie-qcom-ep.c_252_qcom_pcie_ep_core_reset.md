# REAL BUG: drivers/pci/controller/dwc/pcie-qcom-ep.c:252 qcom_pcie_ep_core_reset()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

- No ownership transfer or deferred release applies; the function fails to preserve its contract of keeping the reset line’s deassert_count balanced on error.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L239 (return ret from assert error) | error | NO (deassert never called) | NO (assert failed) | ✅ | Assert error, no state change; safe. |
| L246 (return ret from deassert error) | error | NO (deassert failed) | YES (assert succeeded) | ❌ LEAK | PUT (assert) succeeded, deassert failed → no GET; refcount lost, future assert will be excess. |
| L252 (return 0) | success | YES | YES | ✅ | Normal path; balanced. |

## Analysis

- `reset_control_assert` = PUT, `reset_control_deassert` = GET (contracts confirm).
- When `reset_control_assert` succeeds (PUT) on L236, the refcount is decremented.  
- If `reset_control_deassert` then fails on L244, the error path at L246 returns without a matching GET.  
- This leaves the refcount permanently lower than before the call, causing an **excess put** later when the device is cleaned up (e.g., a final `assert` underflows the zero count).  
- No ownership transfer or deferred release applies; the function fails to preserve its contract of keeping the reset line’s deassert_count balanced on error.

## VERDICT: REAL_BUG  
## CONFIDENCE: HIGH  
Missing `reset_control_assert` (PUT) in the deassert error path at L246 leaves the refcounts unbalanced, leading to a future excess put.
```
