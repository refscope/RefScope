# REAL BUG: drivers/mtd/nand/raw/stm32_fmc2_nand.c:2052 stm32_fmc2_nfc_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L2052 | error return (after labels) | YES | NO | ❌ LEAK | Shared error return at end of function, lacks assert |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1914 | error (ENOMEM) | NO (before deassert) | N/A | ✅ | Allocated nfc, no reset yet |
| L1919 | error (EINVAL) | NO | N/A | ✅ | data NULL, before reset |
| L1923 | error (set_cdev) | NO | N/A | ✅ | |
| L1929 | error (parse_dt) | NO | N/A | ✅ | |
| L1933 | error (of_address) | NO | N/A | ✅ | |
| L1940 | error (regmap) | NO | N/A | ✅ | |
| L1945 (loop) | error (ioremap) | NO | N/A | ✅ | multiple returns inside for loop, all before reset |
| L1957 | error (irq < 0) | NO | N/A | ✅ | |
| L1962 | error (request_irq) | NO | N/A | ✅ | |
| L1971 | error (clk) | NO | N/A | ✅ | |
| L1976 | error (EPROBE_DEFER) | NO (deassert not called if rstc IS_ERR) | N/A | ✅ | rstc error, branch skips deassert |
| L1981 | – | YES (deassert executed) | – | – | Entry point for all subsequent paths |
| L1993 → L2052 | goto err_release_dma (dma fails) | YES | NO | ❌ LEAK | Error path returns without reset_control_assert |
| L2011 → L2052 | goto err_wp_enable (nand_scan fails) | YES | NO | ❌ LEAK | |
| L2017 → L2052 | goto err_nand_cleanup (mtd register fails) | YES | NO | ❌ LEAK | |
| L2022 | success (return 0) | YES | NO (intended) | ✅ (held for lifetime) | Remove function will assert; no leak on success path |
| L2052 | error return (after labels) | YES | NO | ❌ LEAK | Shared error return at end of function, lacks assert |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Every error path after reset_control_deassert() (dma_setup failure, nand_scan failure, mtd_device_register failure) jumps to labels that never call reset_control_assert(), causing a deassert_count refcount leak. The warning at L2052 (the common error return) correctly flags this imbalance.
```
