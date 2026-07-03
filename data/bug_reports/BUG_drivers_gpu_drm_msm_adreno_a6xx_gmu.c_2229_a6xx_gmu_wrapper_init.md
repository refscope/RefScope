# REAL BUG: drivers/gpu/drm/msm/adreno/a6xx_gmu.c:2229 a6xx_gmu_wrapper_init()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L2229 | error (common label) | YES | YES (always after put_device) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2157 | error (-ENODEV) | NO (pdev NULL, no ref) | N/A | ✅ | No device found, no reference |
| L2163 | error (ret from of_dma_configure) | YES (pdev valid, ref taken) | NO | ❌ LEAK | put_device missing before return |
| L2173 | goto err_clk | YES | YES (via err_clk) | ✅ | |
| L2181 | goto err_mmio | YES | YES (via err_mmio -> err_clk) | ✅ | |
| L2187 | goto err_mmio | YES | YES | ✅ | |
| L2196 | goto err_mmio | YES | YES | ✅ | |
| L2201 | goto detach_cxpd | YES | YES (falls through to err_mmio/err_clk) | ✅ | |
| L2212 | goto err_mmio | YES | YES | ✅ | |
| L2217 | success (0) | YES | NO (intentionally held) | ✅ | Reference kept for device lifetime; removed in a6xx_gmu_remove() |
| L2229 | error (common label) | YES | YES (always after put_device) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Early return after `of_dma_configure` failure (L2163) leaks the device reference obtained by `of_find_device_by_node` — no `put_device` is called on that path.
```
