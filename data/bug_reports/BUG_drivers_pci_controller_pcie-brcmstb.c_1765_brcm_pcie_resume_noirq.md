# REAL BUG: drivers/pci/controller/pcie-brcmstb.c:1765 brcm_pcie_resume_noirq()

**Confidence**: HIGH | **Counter**: `$->triggered_count.counter`

## Reasoning

| return 0 (success) | success | YES | NO | ⚠️ potential leak (not flagged by this warning) | The success path does not call `reset_control_rearm`, but the warning only addresses the error path at L1765. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1696-ish (clk_prepare_enable fail) | error | NO (reset_control_reset not called) | N/A | ✅ | |
| **L1765 (goto err_disable_clk after reset_control_reset fails)** | error | **YES** (reset_control_reset unconditionally increments `triggered_count` even on error) | **NO** (err_disable_clk only does `clk_disable_unprepare`, no `reset_control_rearm`) | **❌ LEAK** | The warning line is exactly this return; the count is leaked. |
| goto err_reset (brcm_phy_start, bridge init, setup, regulator enable fail) | error | YES | YES (`reset_control_rearm` at `err_reset`) | ✅ | |
| goto err_regulator → falls to err_reset (brcm_pcie_start_link fails) | error | YES | YES (`err_regulator` label disables regs then falls through to `err_reset` which calls `reset_control_rearm`) | ✅ | |
| return 0 (success) | success | YES | NO | ⚠️ potential leak (not flagged by this warning) | The success path does not call `reset_control_rearm`, but the warning only addresses the error path at L1765. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_reset()` unconditionally increments `triggered_count`; the `goto err_disable_clk` on failure skips `reset_control_rearm()`, leaking the count.
```
