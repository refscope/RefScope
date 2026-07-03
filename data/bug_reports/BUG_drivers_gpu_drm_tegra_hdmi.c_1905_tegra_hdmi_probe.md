# REAL BUG: drivers/gpu/drm/tegra/hdmi.c:1905 tegra_hdmi_probe()

**Confidence**: HIGH | **Counter**: `$->ddc->dev.kobj.kref.refcount.refs.counter`

## Reasoning

| L1886 | success | YES | NO (deferred to driver remove) | ❌ (imbalance will occur on remove) | tegra_output_remove at remove time will double‑put the ddc adapter |

## Full Response

```
| Line | Return Type | GET (tegra_output_probe) Done? | PUT (tegra_output_remove) Done? | Balanced? | Notes |
|------|-------------|-------------------------------|-------------------------------|-----------|-------|
| L1803 | error -ENOMEM | NO (before probe) | N/A | ✅ | |
| L1819 | error PTR_ERR(clk) | NO | N/A | ✅ | |
| L1824 | error PTR_ERR(rst) | NO | N/A | ✅ | |
| L1829 | error PTR_ERR(clk_parent) | NO | N/A | ✅ | |
| L1834 | error (clk_set_parent) | NO | N/A | ✅ | |
| L1839 | error (regulator) | NO | N/A | ✅ | |
| L1844 | error (regulator) | NO | N/A | ✅ | |
| L1849 | error (regulator) | NO | N/A | ✅ | |
| L1852 | error (tegra_output_probe fails) | YES (but failed, assumes internal cleanup) | NO | ✅ (assuming tegra_output_probe cleans up) | |
| L1858 | goto remove | YES (tegra_output_probe succeeded) | YES (goto remove) | ❌ IMBALANCE in ddc ref | tegra_output_remove calls i2c_put_adapter; tegra_output_probe already put it (per contract) |
| L1863 | goto remove | YES | YES | ❌ | same |
| L1869 | goto remove | YES | YES | ❌ | same |
| L1873 | goto remove | YES | YES | ❌ | same |
| L1878 | goto remove | YES | YES | ❌ | same |
| L1883 | goto remove | YES | YES | ❌ | same |
| L1886 | success | YES | NO (deferred to driver remove) | ❌ (imbalance will occur on remove) | tegra_output_remove at remove time will double‑put the ddc adapter |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
tegra_output_probe unconditionally calls i2c_put_adapter (releases ddc adapter ref) per contract, but tegra_output_remove also calls i2c_put_adapter unconditionally – every probe error path and eventual remove will trigger a second put, causing the inconsistent kref on ddc->dev (line 1905).
```
