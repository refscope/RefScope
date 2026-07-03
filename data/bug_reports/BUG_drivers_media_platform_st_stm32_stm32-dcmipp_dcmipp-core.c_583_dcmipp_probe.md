# REAL BUG: drivers/media/platform/st/stm32/stm32-dcmipp/dcmipp-core.c:583 dcmipp_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L540 (success) | return 0 | YES | NO (but device remains deasserted for operation, put will happen on remove) | ✅ (by design) | |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L468 (after devm_kzalloc) | error return -ENOMEM | NO (before deassert) | N/A | ✅ | |
| L473 (after device_get_match_data) | error return -ENODEV | NO | N/A | ✅ | |
| L477 (after devm_reset_control_get_exclusive) | error return (IS_ERR) | NO | N/A | ✅ | |
| L481 (irq < 0) | error return irq | NO | N/A | ✅ | |
| L486 (devm_platform_get_and_ioremap_resource fails) | error return PTR_ERR | NO | N/A | ✅ | |
| L491 (devm_request_threaded_irq fails) | error return ret | NO | N/A | ✅ | |
| L497 (reset_control_assert fails) | error return ret | NO (deassert not called) | N/A | ✅ | |
| L502 (reset_control_deassert fails) | error return ret | NO (deassert failed) | N/A | ✅ | |
| L508 (kclk == devm_clk_get fails) | error return | YES (deassert succeeded) | NO | ❌ LEAK | |
| L514 (mclk == devm_clk_get fails, needs_mclk) | error return | YES | NO | ❌ LEAK | |
| L521 (devm_kcalloc fails) | error return -ENOMEM | YES | NO | ❌ LEAK | |
| L526 (v4l2_device_register fails) | error return ret | YES | NO | ❌ LEAK | |
| L535 (dcmipp_create_subdevs fails) | error return ret | YES | NO (only media_device_cleanup & v4l2_unregister, no assert) | ❌ LEAK | |
| L540 (success) | return 0 | YES | NO (but device remains deasserted for operation, put will happen on remove) | ✅ (by design) | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
reset_control_deassert() at L502 (inside if-ret) increments deassert_count. On success, all subsequent error returns (L508, L514, L521, L526, L535) lack a matching reset_control_assert(), leaking the reference.
```
```
