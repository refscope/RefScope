# REAL BUG: drivers/usb/dwc3/dwc3-meson-g12a.c:829 dwc3_meson_g12a_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| success return 0 | success | YES | NO (deferred to remove) | ✅ | children held for device lifetime |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| after devm_kzalloc fail | error | NO (before get) | N/A | ✅ | |
| after ioremap IS_ERR | error | NO | N/A | ✅ | |
| vbus EPROBE_DEFER | error | NO | N/A | ✅ | |
| clk_bulk_get fail | error | NO | N/A | ✅ | |
| clk_bulk_prepare_enable fail | error | NO | N/A | ✅ | |
| reset_control_get IS_ERR → err_disable_clks | goto err | NO | N/A | ✅ | |
| reset_control_reset fail → err_disable_clks | goto err | NO | N/A | ✅ | |
| get_phys fail → err_rearm | goto err | NO | N/A | ✅ | |
| setup_regmaps fail → err_rearm | goto err | NO | N/A | ✅ | |
| regulator_enable fail → err_rearm | goto err | NO | N/A | ✅ | |
| usb_init fail → err_disable_regulator | goto err | NO | N/A | ✅ | |
| phy_init fail → err_disable_regulator | goto err | NO | N/A | ✅ | |
| phy_power_on fail → err_phys_exit | goto err | NO | N/A | ✅ | |
| usb_post_init fail → err_phys_power | goto err | NO | N/A | ✅ | |
| **L829: of_platform_populate fail → err_phys_power** | error | **YES** (partial creation increments parent kref) | **NO** (of_platform_depopulate not called) | **❌ LEAK** | **goto skips depopulate** |
| otg_init fail → err_plat_depopulate | error | YES | YES | ✅ | of_platform_depopulate called |
| success return 0 | success | YES | NO (deferred to remove) | ✅ | children held for device lifetime |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
of_platform_populate() error path at L829 jumps to err_phys_power without calling of_platform_depopulate(), leaking the parent device kref acquired by partially created child platform devices.
```
