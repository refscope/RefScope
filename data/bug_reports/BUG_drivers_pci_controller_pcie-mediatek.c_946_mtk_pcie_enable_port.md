# REAL BUG: drivers/pci/controller/pcie-mediatek.c:946 mtk_pcie_enable_port()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

Once confirmed, the bug is real: the combination of L911 (unconditional assert) and error paths that skip deassert but still call the assert in the cleanup function causes a double-assert or underflow.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L873 (err\_sys\_clk) | error | NO (before deassert) | NO in function, PUT in `mtk_pcie_port_free`? | ⚠️ If `port_free` has PUT → EXCESS PUT | No deassert called before this path, so deassert_count = 0; calling assert inside `port_free` underflows. |
| L879 (err\_ahb\_clk) | error | NO | NO in function, PUT? | ⚠️ Same as above | |
| L885 (err\_aux\_clk) | error | NO | NO in function, PUT? | ⚠️ Same | |
| L891 (err\_axi\_clk) | error | NO | NO in function, PUT? | ⚠️ Same | |
| L897 (err\_obff\_clk) | error | NO | NO in function, PUT? | ⚠️ Same | |
| L903 (err\_pipe\_clk) | error | NO | NO in function, PUT? | ⚠️ Same | |
| L911 (inside function) | assert call | N/A (this itself is a PUT) | YES (assert) | ✅ | assert call decrements, but deassert_count must be >0 to avoid underflow. Initial state unknown. |
| L912 (inside function) | deassert call | YES (deassert=GET) | NO (no assert before exit on this path) | N/A | deassert increments count; need to check subsequent paths. |
| L918 (err\_phy\_init) | error (after phy_init fail) | YES (deassert at L912) | NO | ❌ LEAK (deassert_count stays incremented) | No assert in this error path; port_free may or may not assert. If port_free calls assert, balance returns but underflow already possible from earlier paths. |
| L924 (err\_phy\_on) | error (after phy_power_on fail) | YES | NO | ❌ LEAK | Same as above. |
| L928 (success return, link down) | return (void) | YES | NO | ❌ LEAK | Direct return, no assert or port_free. deassert_count stays incremented indefinitely. |
| end of function (after all labels) | falls through (implicit return) | YES (if reachable via error fall-through) | NO | ❌ LEAK | After err_phy_init, falls through to clock disable then `mtk_pcie_port_free`. If port_free does NOT assert, leak persists; if it DOES assert, then earlier paths cause excess put. |

## Analysis

### Need Source of `mtk_pcie_port_free`
[NEED_SOURCE] mtk_pcie_port_free

### Key Observations
1. The warning “refcount excess put” suggests `reset_control_assert()` was called when the internal `deassert_count` was already zero (underflow).  
2. The function `mtk_pcie_enable_port()` calls `reset_control_assert(port->reset)` at L911 **before** `reset_control_deassert(port->reset)` at L912. If the initial `deassert_count` was zero, this assert would trigger an underflow **at that line**, but the warning line is 946 — therefore the triggering assert is elsewhere.  
3. All error paths before L912 (clock failures) **never call deassert**, so `deassert_count` stays zero. If the error-cleanup function `mtk_pcie_port_free()` (called at the end of every error path) contains a `reset_control_assert()`, those paths would cause an excess put — exactly matching the warning.  
4. All error paths after L912 (phy errors) and the success path omit an explicit `reset_control_assert()`, leaving
```
