# REAL BUG: drivers/gpu/drm/stm/lvds.c:1185 lvds_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L1142 (return 0) | success return after deassert | YES | NO | ⚠️ intentional | reset left deasserted for device lifetime; assert expected in remove/suspend. Warning line 1185 is the error path return, not this one. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1051 (IS_ERR(lvds)) | error | NO | N/A | ✅ | before reset get/deassert |
| L1061 (panel not found) | error | NO | N/A | ✅ | before reset get/deassert |
| L1068 (ioremap fail) | error | NO | N/A | ✅ | before reset get/deassert |
| L1075 (pclk get fail) | error | NO | N/A | ✅ | before reset get/deassert |
| L1081 (clk_prepare_enable fail) | error | NO | N/A | ✅ | before reset get/deassert |
| L1088 (IS_ERR(rstc) → goto err) | goto err_lvds_probe | NO | N/A | ✅ | rstc get failed, no deassert |
| L1095 (default case → goto err) | goto err_lvds_probe **after deassert** | YES | NO | ❌ LEAK | no assert in err path |
| L1120 (IS_ERR(pllref_clk) → goto err) | goto err_lvds_probe after deassert | YES | NO | ❌ LEAK | no assert in err path |
| L1125 (pixel_clk_register fail → goto err) | goto err_lvds_probe after deassert | YES | NO | ❌ LEAK | no assert in err path |
| L1142 (return 0) | success return after deassert | YES | NO | ⚠️ intentional | reset left deasserted for device lifetime; assert expected in remove/suspend. Warning line 1185 is the error path return, not this one. |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Error paths after `reset_control_deassert` jump to `err_lvds_probe` (which only disables the clock) without calling `reset_control_assert`, leaking the deassert_count increment.
```
