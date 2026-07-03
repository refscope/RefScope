# REAL BUG: drivers/dma/stm32/stm32-mdma.c:1745 stm32_mdma_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L1724 (return 0; success) | success | YES | NO (by design) | ✅ (runtime) | Reset stays deasserted for device lifetime; remove() will assert. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1598 (if (!of_node) → -ENODEV) | error | NO (before any reset get) | N/A | ✅ | No reset acquired |
| L1612 (devm_kzalloc fail → -ENOMEM) | error | NO | N/A | ✅ | No reset acquired |
| L1623 (IS_ERR(base) → PTR_ERR) | error | NO | N/A | ✅ | No reset acquired |
| L1627 (IS_ERR(clk) → dev_err_probe) | error | NO | N/A | ✅ | No reset acquired |
| L1632 (clk_prepare_enable fail → ret) | error | NO | N/A | ✅ | No reset acquired |
| L1641 (IS_ERR(rst) && EPROBE_DEFER → goto err_clk) | error | NO (else not entered) | N/A | ✅ | rst is ERR_PTR, no deassert |
| L1643–1646 (IS_ERR(rst) but not EPROBE_DEFER, falls through) | error/none | NO | N/A | ✅ | rst is ERR_PTR, continues safely |
| L1650 (rst valid: deassert() called) → later goto err_clk at L1701 (irq fail) | error | YES | NO | ❌ LEAK | err_clk only disables clk, no reset_control_assert |
| ~L1708 (devm_request_irq fail → goto err_clk) | error | YES | NO | ❌ LEAK | same |
| ~L1712 (dmaenginem_async_device_register fail → goto err_clk) | error | YES | NO | ❌ LEAK | same |
| ~L1718 (of_dma_controller_register fail → goto err_clk) | error | YES | NO | ❌ LEAK | same |
| L1724 (return 0; success) | success | YES | NO (by design) | ✅ (runtime) | Reset stays deasserted for device lifetime; remove() will assert. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

`reset_control_deassert()` increments `deassert_count` unconditionally when rst is valid. Every error path after that point jumps to `err_clk`, which only calls `clk_disable_unprepare()` and never `reset_control_assert()`. Thus the deassert_count leaks on probe failure.
```
