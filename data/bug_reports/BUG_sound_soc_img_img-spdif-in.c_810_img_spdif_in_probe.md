# REAL BUG: sound/soc/img/img-spdif-in.c:810 img_spdif_in_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

- Conditional GET? No, deassert is unconditional (always incs).

## Full Response

```
## Analysis of img_spdif_in_probe()

### Path Table

Every return/goto path in `img_spdif_in_probe()` is enumerated relative to the `reset_control_deassert()` call (the GET that increments `deassert_count`).  
Line numbers approximate from provided source (initial line 718).

**GET execution**: Only when `rst` is valid (the `else` branch at L756–L757) and `reset_control_deassert(rst)` is called.

| Line     | Return Type       | GET Done? | PUT Done? | Balanced? | Notes |
|----------|-------------------|-----------|-----------|-----------|-------|
| L720     | `return -ENOMEM`  | NO        | N/A       | ✅ | Before any reset |
| L728     | `return PTR_ERR`  | NO        | N/A       | ✅ | After IS_ERR(base) |
| L732     | `return dev_err`  | NO        | N/A       | ✅ | After clk get fail |
| L738     | `goto err_pm_disable` | NO     | N/A       | ✅ | pm-resume fail, before reset |
| L743     | `goto err_suspend`    | NO     | N/A       | ✅ | pm_runtime_resume_and_get fail |
| L749     | `goto err_pm_put`     | NO     | N/A       | ✅ | EPROBE_DEFER, rst is ERR, no deassert |
| L751–754| (falls through) → soft reset, then later error paths to `err_suspend` | NO | N/A | ✅ | `rst` invalid, no deassert ever called |
| L770     | `goto err_suspend`    | **YES** | **NO**     | ❌ **LEAK** | After deassert (valid rst), goto err_suspend lacks `reset_control_assert` |
| L775     | `goto err_suspend`    | **YES** | **NO**     | ❌ **LEAK** | After deassert, same leak |
| L777     | `return 0`            | YES      | NO (in probe) | (balanced in remove?) | Success path—device holds deassert; remove() should assert. Not a leak if remove exists. |

**Key findings**:
- The `else` branch at L756–L757 unconditionally calls `reset_control_deassert(rst)` (GET executed).
- Both error paths after that point go to `err_suspend` (L770, L775).  
- The `err_suspend` label only handles PM runtime (`img_spdif_in_runtime_suspend`, `pm_runtime_disable`) and does **not** call `reset_control_assert`. No other cleanup compensates.
- The probe’s success return (L777) keeps the reset deasserted for the device’s lifetime; it is balanced by the driver’s remove callback (not shown). However, the error paths **inside the same function** lack the matching assert → definite refcount leak.

### Why the error paths are a leak
- `reset_control_deassert` increments `deassert_count`.
- The only matching decrement is `reset_control_assert`, absent on `err_suspend`.
- No IS_ERR guard applies because `rst` is valid and deassert already completed.
- No ownership transfer: the driver must assert on error.

### FP checklist
- IS_ERR/NULL guard? None—we are past the valid `rst` check.
- Conditional GET? No, deassert is unconditional (always incs).
- Ownership transfer? Not applicable; driver must manually assert.
- devm cleanup? Only the reset **handle** is devm-managed; the deassert count is not automatically released.
- Async deferral? None.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
## REASON
`reset_
```
