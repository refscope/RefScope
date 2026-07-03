# REAL BUG: drivers/gpu/drm/hisilicon/kirin/kirin_drm_drv.c:283 kirin_drm_platform_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L281 | error (ret<0) | YES (via match add) | NO | ❌ LEAK | Match holds ref; not freed on error, so the remote node’s reference persists. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L276 | error (-ENODEV) | NO (remote is NULL) | N/A | ✅ | No get, safe. |
| L281 | success (ret=0) | YES (via match add) | YES (via match release later) | ✅ | Reference transferred to component match; will be released on master del. |
| L281 | error (ret<0) | YES (via match add) | NO | ❌ LEAK | Match holds ref; not freed on error, so the remote node’s reference persists. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

Missing `component_match_free()` (or equivalent cleanup) when `component_master_add_with_match()` returns an error, leaking the reference acquired by `drm_of_component_match_add()`.
```
