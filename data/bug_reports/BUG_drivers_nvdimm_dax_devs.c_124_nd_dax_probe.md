# REAL BUG: drivers/nvdimm/dax_devs.c:124 nd_dax_probe()

**Confidence**: MEDIUM | **Counter**: `dax_dev->kobj.kref.refcount.refs.counter`

## Reasoning

(`rc ≥ 0` success path) | success return | **YES** | NO explicit put; `nd_device_register` may or may not consume the reference | ⚠️ Possible leak (not flagged) | Initial reference from nd_dax_devinit is never released in probe; device model may or may not take over |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L92 | error `-ENODEV` | NO (before get) | N/A | ✅ | `ndns->force_raw` true |
| L102 (switch default) | error `-ENODEV` | NO (before get) | N/A | ✅ | `claim_class` invalid |
| L109 (`if (!dax_dev)`) | error `-ENOMEM` | NO (nd_dax_devinit NULL) | N/A | ✅ | GET conditional, not taken |
| L124‑127 (`rc < 0` error path) | error return (falls to final `return`) | **YES** (nd_dax_devinit returned non‑NULL) | **put_device() at L124** + possible earlier put inside `nd_detach_ndns()` | ❌ **EXCESS PUT** | `nd_detach_ndns` likely already releases the device reference; the explicit `put_device` then drops the refcount below zero — exactly the “refcount excess put” warned on L124 |
| L130 (`rc ≥ 0` success path) | success return | **YES** | NO explicit put; `nd_device_register` may or may not consume the reference | ⚠️ Possible leak (not flagged) | Initial reference from nd_dax_devinit is never released in probe; device model may or may not take over |

[NEED_SOURCE] nd_detach_ndns

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
Error path double‑put on `dax_dev`: `nd_detach_ndns()` likely already does a `put_device`, making the explicit `put_device(dax_dev)` at L124 an excess put that triggers the kref warning.
```
