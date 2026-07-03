# REAL BUG: drivers/phy/st/phy-stm32-usbphyc.c:770 stm32_usbphyc_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L739 | return 0 (success)    | YES (if rst valid)        | NO (probe success)         | ✅ (held for lifetime) | remove callback will assert |

## Full Response

```
```
| Line | Return Type           | GET Done?                 | PUT Done?                  | Balanced?   | Notes |
|------|-----------------------|---------------------------|----------------------------|-------------|-------|
| L621 | error (ENOMEM)        | NO (before get)           | N/A                        | ✅          | |
| L627 | error (IS_ERR base)   | NO (before get)           | N/A                        | ✅          | |
| L631 | error (IS_ERR clk)    | NO (before get)           | N/A                        | ✅          | |
| L635 | error (clk enable)    | NO (before get)           | N/A                        | ✅          | |
| L640 | if (!IS_ERR(rst)) block | runtime decision: deassert called if valid | | | |
| L650 | goto clk_disable      | YES (if rst valid)        | NO (clk_disable lacks assert) | ❌ LEAK    | PLL poll_timeout failure |
| L657 | goto clk_disable      | YES (if rst valid)        | NO                         | ❌ LEAK    | phys alloc failure |
| L663 | goto clk_disable      | YES (if rst valid)        | NO                         | ❌ LEAK    | vdda1v1 get failed |
| L670 | goto clk_disable      | YES (if rst valid)        | NO                         | ❌ LEAK    | vdda1v8 get failed |
| L681 | goto put_child → clk_disable | YES (if rst valid) | NO (put_child lacks assert) | ❌ LEAK    | devm_phy_create failed |
| L688 | goto put_child → clk_disable | YES (if rst valid) | NO                         | ❌ LEAK    | devm_kzalloc for phy private |
| L694 | goto put_child → clk_disable | YES (if rst valid) | NO                         | ❌ LEAK    | reg property invalid |
| L704 | goto put_child → clk_disable | YES (if rst valid) | NO                         | ❌ LEAK    | vbus EPROBE_DEFER |
| L727 | goto clk_disable      | YES (if rst valid)        | NO                         | ❌ LEAK    | phy_provider register failed |
| L733 | goto clk_disable      | YES (if rst valid)        | NO                         | ❌ LEAK    | clk48_register failed |
| L739 | return 0 (success)    | YES (if rst valid)        | NO (probe success)         | ✅ (held for lifetime) | remove callback will assert |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
reset_control_deassert (GET) is called when rst is valid, but every probe error path after that point goes to clk_disable or put_child (which falls through to clk_disable) without calling reset_control_assert (PUT), causing a deassert_count refcount leak.
```
```
