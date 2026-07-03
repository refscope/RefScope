# REAL BUG: drivers/iio/adc/stm32-dfsdm-adc.c:1846 stm32_dfsdm_adc_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| ~1839 (return 0, success) | success | YES | N/A (devices kept for driver lifetime) | ✅ | devices explicitly owned by driver |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~1768 (iio alloc fail) | error | NO | N/A | ✅ | before any get |
| ~1778 (reg property fail) | error | NO | N/A | ✅ | |
| ~1782 (kzalloc fail) | error | NO | N/A | ✅ | |
| ~1800 (irq fail) | error | NO | N/A | ✅ | |
| ~1804 (devm_request_irq fail) | error | NO | N/A | ✅ | |
| ~1810 (filter-order fail) | error | NO | N/A | ✅ | |
| ~1821 (init fail) | error | NO | N/A | ✅ | |
| ~1824 (iio_device_register fail) → goto err_cleanup | error | NO | N/A | ✅ | no of_platform_populate called |
| ~1830 (of_platform_populate fail) → goto err_unregister | error | YES (devices may have been created) | NO (no of_platform_depopulate) | ❌ LEAK | missing cleanup of partially populated devices |
| ~1839 (return 0, success) | success | YES | N/A (devices kept for driver lifetime) | ✅ | devices explicitly owned by driver |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_platform_populate` error path jumps to `err_unregister` which only undoes the iio registration, missing `of_platform_depopulate(dev)` to release any already‑created platform devices, leaking their kobj.kref refcounts.
```
