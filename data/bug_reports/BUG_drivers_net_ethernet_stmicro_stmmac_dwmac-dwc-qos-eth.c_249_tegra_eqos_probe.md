# REAL BUG: drivers/net/ethernet/stmicro/stmmac/dwmac-dwc-qos-eth.c:249 tegra_eqos_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

**Key**: The L232 path leaves the reset control asserted without a deassert, resulting in an extra put (count -1). This matches the warning’s “excess put” on the `deassert_count` counter, reported at L249 (the `gpiod_set_value` inside `reset_phy`, which this path reaches).

## Full Response

```
| Line | Return Type | GET Done? (deassert) | PUT Done? (assert) | Balanced? | Notes |
|------|-------------|----------------------|---------------------|-----------|-------|
| L196 | `return -ENOMEM` (error) | NO (before any operations) | NO | ✅ | |
| L209 | `return err` (gpio get failed) | NO (rst not yet obtained) | NO | ✅ | |
| L219 | `goto reset_phy` (rst get failed) | NO | NO | ✅ | |
| L225 | `goto reset_phy` (assert failed) | NO (assert error, no state change) | NO (failed, no put) | ✅ | assert returns error; no counter decrement |
| L232 | `goto reset_phy` (deassert failed) | NO (deassert failed) | YES (assert succeeded) | ❌ | assert called without matching deassert → excess put, count goes negative |
| L246 (bypass) | `return 0` (top `goto bypass_clk_reset_gpio`) | NO | NO | ✅ |  |
| L246 (success) | `return 0` (after assert+deassert) | YES | YES | ✅* | assert before deassert is an intermediate underflow, but exit count is 0; the buggy assert still triggers the smatch *excess put* at its call site |

**Key**: The L232 path leaves the reset control asserted without a deassert, resulting in an extra put (count -1). This matches the warning’s “excess put” on the `deassert_count` counter, reported at L249 (the `gpiod_set_value` inside `reset_phy`, which this path reaches).

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`reset_control_assert()` is called before `reset_control_deassert()`, causing an unbalanced put when deassert fails (L232→L249). The error path does not call `reset_control_deassert()` to cancel the previous assert, leaving the counter negative.
```
