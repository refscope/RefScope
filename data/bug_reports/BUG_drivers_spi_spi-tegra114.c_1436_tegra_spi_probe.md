# REAL BUG: drivers/spi/spi-tegra114.c:1436 tegra_spi_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

4. **goto out between GET and PUT?** → YES. `goto exit_pm_disable` (L1394) and `goto exit_free_irq` (L1399) both occur between the deassert GET (L1382) and the success-return PUT. Neither label contains `reset_control_assert()` → **LEAK on both paths**.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1305 | error (return -ENOMEM) | NO (before get) | N/A | ✅ | spi_alloc_host fails, reset not obtained yet |
| L1338 | goto exit_free_host | NO (before get) | N/A | ✅ | of_device_get_match_data fails |
| L1343 | goto exit_free_host | NO (before get) | N/A | ✅ | devm_ioremap_resource fails |
| L1348 | goto exit_free_host | NO (before get) | N/A | ✅ | platform_get_irq fails |
| L1355 | goto exit_free_host | NO (before get) | N/A | ✅ | devm_clk_get fails |
| L1363 | goto exit_free_host | NO (before get) | N/A | ✅ | devm_reset_control_get_exclusive fails |
| L1375 | goto exit_free_host | NO (before get) | N/A | ✅ | tegra_spi_init_dma_param(tx) fails |
| L1378 | goto exit_rx_dma_free | NO (before get) | N/A | ✅ | tegra_spi_init_dma_param(rx) fails |
| L1385 | goto exit_pm_disable | NO (before get) | N/A | ✅ | tegra_spi_runtime_resume fails, deassert not yet called |
| L1391 | goto exit_pm_disable | NO (before get) | N/A | ✅ | pm_runtime_resume_and_get fails, deassert not yet called |
| L1394 | goto exit_pm_disable | **YES** (deassert at L1382) | **NO** | ❌ **LEAK** | request_threaded_irq fails after deassert; exit_pm_disable has no reset_control_assert |
| L1399 | goto exit_free_irq → exit_pm_disable | **YES** (deassert at L1382) | **NO** | ❌ **LEAK** | spi_register_controller fails after deassert; neither exit_free_irq nor exit_pm_disable has reset_control_assert |
| L1401 | success (return ret) | YES (deassert at L1382) | YES (via tegra_spi_remove) | ✅ | device fully registered; remove() will assert reset on unbind |

**Label contents verification:**
- `exit_free_irq` (L1402): `free_irq()` only — ⚠️ **no reset_control_assert**
- `exit_pm_disable` (L1403): `pm_runtime_disable`, `tegra_spi_runtime_suspend`, DMA deinit — ⚠️ **no reset_control_assert**
- `exit_rx_dma_free` (L1407): DMA deinit only
- `exit_free_host` (L1409): `spi_controller_put` only

## Pre-Verdict Checklist

1. **"Held for device lifetime"?** → YES. The reset deassert is for device operational lifetime. This ONLY covers the SUCCESS return (L1401) where the device is bound and `tegra_spi_remove()` will assert on unbind. The two ERROR paths (L1394, L1399) return without device binding → `remove()` never fires → **MUST explicitly assert on error paths** → REAL_BUG.

2. **"Ownership transferred"?** → NO. No ownership transfer. The reset control remains within `tspi->rst` throughout. No external cleanup code will assert for us.

3. **Unconditional GET?** → YES. Contract says `reset_control_deassert()` increments `deassert_count`. Return value is NOT checked at L1382. After L1382, `deassert_count` is incremented on all subsequent paths.

4. **goto out between GET and PUT?** → YES. `goto exit_pm_disable` (L1394) and `goto exit_free_irq` (L1399) both occur between the deassert GET (L1382) and the success-return PUT. Neither label contains `reset
```
