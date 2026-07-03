# REAL BUG: drivers/gpu/drm/bridge/synopsys/dw-mipi-dsi.c:1276 __dw_mipi_dsi_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L1275 | success     | YES       | YES       | ✅ (order broken) | same path as above, function returns dsi successfully |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1202 | ERR_CAST    | NO        | NO        | N/A       | Before reset block |
| L1207 | ERR_PTR(-ENODEV) | NO   | NO        | N/A       | phy check failure |
| L1214 | ERR_PTR(-ENODEV) | NO   | NO        | N/A       | base ioremap failure |
| L1221 | ERR_PTR(ret)| NO        | NO        | N/A       | pclk get failure |
| L1231 | ERR_PTR(ret)| NO        | NO        | N/A       | reset control get failure |
| L1244 | ERR_PTR(ret)| NO        | NO        | N/A       | clk_prepare_enable fails inside apb_rst block, before assert |
| L1270 | ERR_PTR(ret)| YES       | YES       | ✅ (order broken) | assert then deassert executed; excess put because assert called while deassert_count=0 |
| L1275 | success     | YES       | YES       | ✅ (order broken) | same path as above, function returns dsi successfully |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_assert(apb_rst)` at ~L1253 is called without a prior `reset_control_deassert`, causing a decrement on an already-zero `deassert_count` – an excess put that violates the reset framework's balanced API. The assertion ordering should be fixed (e.g., use `reset_control_reset()` or deassert first).```
```
