# REAL BUG: drivers/gpu/drm/sun4i/sun4i_tcon.c:1296 sun4i_tcon_bind()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| ~L1250 (success) | return 0 | YES | NO | ❌ LEAK? |  success path: deassert held for device lifetime, balanced later in unbind, but error paths are definitive leaks |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1120 (engine check) | error (-EPROBE_DEFER) | NO (before get) | N/A | ✅ |  |
| ~L1125 (kzalloc fail) | error (-ENOMEM) | NO | N/A | ✅ |  |
| ~L1131 (lcd_rst get fail) | error (PTR_ERR) | NO | N/A | ✅ |  |
| ~L1138 (edp_rstc get fail, if needs_edp_reset) | error (PTR_ERR) | NO | N/A | ✅ | only if needs_edp_reset |
| ~L1141 (edp deassert fail) | error (ret) | NO (deassert failed) | N/A | ✅ | conditional GET; ret != 0 → no inc |
| ~L1147 (reset_control_reset fail) | error (ret) | YES (deassert inc’d) | NO | ❌ LEAK | no edp assert |
| ~L1154 (lvds_rst get fail) | error (PTR_ERR) | YES | NO | ❌ LEAK |  |
| ~L1170 (clk get error, not -ENOENT) | error (PTR_ERR) | YES | NO | ❌ LEAK |  |
| ~L1195 (init_clocks fail) | goto err_assert_reset | YES | NO | ❌ LEAK | label only asserts lcd_rst |
| ~L1200 (init_regmap fail) | goto err_assert_reset | YES | NO | ❌ LEAK |  |
| ~L1207 (dclk_create fail) | goto err_assert_reset | YES | NO | ❌ LEAK |  |
| ~L1213 (init_irq fail) | goto err_free_dclk | YES | NO | ❌ LEAK | err_free_dclk falls through to err_assert_reset, no edp assert |
| ~L1218 (crtc_init fail) | goto err_free_dclk | YES | NO | ❌ LEAK |  |
| ~L1232 (display init fail) | goto err_free_dclk | YES | NO | ❌ LEAK |  |
| ~L1250 (success) | return 0 | YES | NO | ❌ LEAK? |  success path: deassert held for device lifetime, balanced later in unbind, but error paths are definitive leaks |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
After `reset_control_deassert(edp_rstc)` succeeds, all error‑return paths and the success path exit without `reset_control_assert(edp_rstc)`, leaking the deassert reference on error because the device will never be unbound.
```
