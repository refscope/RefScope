# REAL BUG: drivers/spi/spi-cadence.c:768 cdns_spi_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L726 | success (return ret) | YES | NO (by design) | ✅ | device bound, reset stays deasserted; remove() will assert |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L639 | error (return -ENOMEM) | NO (before get) | N/A | ✅ | |
| L648 | goto remove_ctlr | NO (before get) | N/A | ✅ | regs IS_ERR, reset not obtained |
| L655 | goto remove_ctlr | NO (before get) | N/A | ✅ | pclk IS_ERR |
| L662 | goto remove_ctlr | NO (rstc IS_ERR) | N/A | ✅ | reset get failed, no deassert |
| L670 | goto remove_ctlr | YES | NO | ❌ LEAK | ref_clk error after deassert |
| L693 | goto clk_dis_all | YES | NO | ❌ LEAK | irq < 0 after deassert |
| L700 | goto clk_dis_all | YES | NO | ❌ LEAK | devm_request_irq failed after deassert |
| L718 | goto clk_dis_all | YES | NO | ❌ LEAK | spi_register_controller failed after deassert |
| L726 | success (return ret) | YES | NO (by design) | ✅ | device bound, reset stays deasserted; remove() will assert |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Probe error paths after `reset_control_deassert` (L670, L693, L700, L718) skip `reset_control_assert`; `devm_reset_control_get` only frees the handle, does not assert the reset line, so the deassert_count is leaked.
```
