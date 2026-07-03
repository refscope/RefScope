# REAL BUG: drivers/usb/dwc3/dwc3-am62.c:302 dwc3_ti_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

**PUT required**: Calling `of_platform_depopulate(dev)` in the error path to clean up any devices added before the failure.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L228 | error (ENOMEM) | NO | N/A | ✅ | before any ref-taking |
| L236 | error (IS_ERR) | NO | N/A | ✅ | before `of_platform_populate` |
| L242 | error (IS_ERR) | NO | N/A | ✅ | before `of_platform_populate` |
| L255 | error (-EINVAL) | NO | N/A | ✅ | before `of_platform_populate` |
| L270 | error (dwc3_ti_init fail) | NO | N/A | ✅ | before `of_platform_populate` |
| L283→L302 | goto err_pm_disable / return ret | **YES** (parent kref incremented by created children) | **NO** (no `of_platform_depopulate`) | ❌ **LEAK** | Missing cleanup of partially populated children |
| L296 | success (0) | YES | deferred (by `dwc3_ti_remove`) | ✅ | lifetime balanced via remove callback |

**GET source**: `of_platform_populate()` creates platform devices for child nodes; each successful `device_add` increments the parent’s kref. On error, previously created children remain attached, leaking the parent’s kref unless explicitly removed.  
**PUT required**: Calling `of_platform_depopulate(dev)` in the error path to clean up any devices added before the failure.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`of_platform_populate` error path (goto err_pm_disable, L283→L302) lacks `of_platform_depopulate`, leaking parent kref from partially created child devices.
```
