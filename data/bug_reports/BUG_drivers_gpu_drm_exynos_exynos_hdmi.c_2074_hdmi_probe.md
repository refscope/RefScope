# REAL BUG: drivers/gpu/drm/exynos/exynos_hdmi.c:2074 hdmi_probe()

**Confidence**: HIGH | **Counter**: `hdata->hdmiphy_port->dev.kobj.kref.refcount.refs.counter`

## Reasoning

| L2060 | success return | YES | NO (held for lifetime) | ✅ | normal device lifetime hold |

## Full Response

```
| Line | Return Type | GET Done? (hdmiphy_port ref) | PUT Done? | Balanced? | Notes |
|------|-------------|------------------------------|-----------|-----------|-------|
| L1970 | error (ENOMEM) | NO | N/A | ✅ | Before any get |
| L1974 | error (hdmi_resources_init) | NO | N/A | ✅ | Before any get |
| L1982 | error (devm_platform_ioremap_resource) | NO | N/A | ✅ | Before any get |
| L1989 | error (hdmi_get_ddc_adapter) | NO | N/A | ✅ | Only DDC get, handled later |
| **L1993** | **goto err_ddc** (hdmi_get_phy_io fails) | **YES** (contract says unconditional get) | **NO** | **❌ LEAK** | `err_ddc` has no put for hdmiphy_port |
| L2022 | goto err_hdmiphy | YES | YES (err_hdmiphy) | ✅ | via `if (hdata->hdmiphy_port) put_device(...)` |
| L2028 | goto err_hdmiphy | YES | YES | ✅ | |
| L2032 | goto err_hdmiphy | YES | YES | ✅ | |
| L2038 | goto err_hdmiphy | YES | YES | ✅ | |
| L2040 | goto err_hdmiphy | YES | YES | ✅ | |
| L2050 | goto err_rpm_disable | YES | YES (→err_hdmiphy) | ✅ | falls through to `err_hdmiphy` |
| L2055 | goto err_unregister_audio | YES | YES (→err_rpm_disable→err_hdmiphy) | ✅ | falls through |
| L2060 | success return | YES | NO (held for lifetime) | ✅ | normal device lifetime hold |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`hdmi_get_phy_io()` is flagged as an unconditional GET – it always increments the reference count on `hdata->hdmiphy_port->dev`. When it fails (ret != 0), the code jumps to `err_ddc` which only releases the DDC adapter and does **not** call `put_device(&hdata->hdmiphy_port->dev)`, leaking the reference acquired by `hdmi_get_phy_io()`.
```
