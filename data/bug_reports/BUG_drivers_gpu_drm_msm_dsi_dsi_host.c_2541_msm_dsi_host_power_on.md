# REAL BUG: drivers/gpu/drm/msm/dsi/dsi_host.c:2541 msm_dsi_host_power_on()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| ~L2517 (goto fail_disable_clk, pinctrl fail) | error | YES | YES (at fail_disable_clk) | ✅ | put called before falling through |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L2485 (goto unlock_ret, early power_on) | ret=0 | NO | N/A | ✅ | before pm_runtime_get_sync |
| ~L2499 (goto unlock_ret, reg enable fail) | error | NO | N/A | ✅ | before get |
| ~L2511 (goto fail_disable_reg, clock set/enable fail) | error | YES | NO | ❌ LEAK | fail_disable_reg lacks pm_runtime_put |
| ~L2517 (goto fail_disable_clk, pinctrl fail) | error | YES | YES (at fail_disable_clk) | ✅ | put called before falling through |
| ~L2525 (success) | ret=0 | YES | NO (held for device lifetime) | ✅ | ref released in msm_dsi_host_power_off |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
pm_runtime_get_sync (L2501) increments usage_count; error path via fail_disable_reg (L2511) skips pm_runtime_put, leaking the runtime PM reference.
```
