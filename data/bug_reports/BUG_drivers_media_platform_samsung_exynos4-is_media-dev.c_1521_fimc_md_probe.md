# REAL BUG: drivers/media/platform/samsung/exynos4-is/media-dev.c:1521 fimc_md_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| LXX  | return 0 (success) | YES | deferred to driver remove | ✅ | child devices bound, cleaned up in driver remove |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L11  | return -ENOMEM (before GET) | NO | N/A | ✅ | gets not executed, no devices created |
| L15  | return -ENOMEM (of_platform_populate failure) | NO (populate returned < 0) | N/A | ✅ | no child devices created |
| L39  | goto err_md (after successful populate) | YES | NO | ❌ LEAK | err_md only does media_device_cleanup, no of_platform_depopulate |
| L44  | goto err_v4l2dev (v4l2 reg fail) | YES | NO | ❌ LEAK | err_v4l2dev → err_md, no depopulate |
| LXX  | goto err_clk (platform_entities fail) | YES | NO | ❌ LEAK | err_clk → err_v4l2dev → err_md, no depopulate |
| LXX  | goto err_m_ent (sensor_entities fail) | YES | NO | ❌ LEAK | err_m_ent → err_clk chain, no depopulate |
| LXX  | goto err_cleanup (device_create_file fail) | YES | NO | ❌ LEAK | err_cleanup → err_m_ent chain, no depopulate |
| LXX  | goto err_attr (clk_provider fail) | YES | NO | ❌ LEAK | err_attr → err_cleanup chain, no depopulate |
| LXX  | goto err_clk_p (async notifier fail) | YES | NO | ❌ LEAK | err_clk_p → err_attr chain, no depopulate |
| LXX  | return 0 (success) | YES | deferred to driver remove | ✅ | child devices bound, cleaned up in driver remove |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_platform_populate()` creates child platform devices whose `struct device` kobjects are never released on error paths in probe — `of_platform_depopulate()` is missing from every error label after the populate call. Child devices stay registered and leak their initial kref.
```
