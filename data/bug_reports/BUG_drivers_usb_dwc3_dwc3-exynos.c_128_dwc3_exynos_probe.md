# REAL BUG: drivers/usb/dwc3/dwc3-exynos.c:128 dwc3_exynos_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

platform_depopulate never called) | ❌ **LEAK** | `of_platform_populate` may have created devices that hold parent ref; no cleanup on error |

## Full Response

```
| Line | Return Type | GET Done? (Parent kref) | PUT Done? (of_platform_depopulate) | Balanced? | Notes |
|------|-------------|--------------------------|-----------------------------------|-----------|-------|
| L50  | error       | NO (before of_platform_populate) | N/A | ✅ | Early -ENOMEM, no ref taken |
| L65  | error       | NO | N/A | ✅ | Clock get error, before populate |
| L74  | error       | NO | N/A | ✅ | Clock enable error, before populate |
| L84  | goto vdd33_err | NO | N/A | ✅ | Regulator get error, before populate |
| L89  | goto vdd33_err | NO | N/A | ✅ | vdd33 enable error, before populate |
| L95  | goto vdd10_err | NO | N/A | ✅ | vdd10 get error, before populate |
| L100 | goto vdd10_err | NO | N/A | ✅ | vdd10 enable error, before populate |
| L112 | goto populate_err (node == NULL) | NO | N/A | ✅ | No of_platform_populate called |
| L107 | goto populate_err (of_platform_populate failed) | **YES** (partial child devices created) | **NO** (of_platform_depopulate never called) | ❌ **LEAK** | `of_platform_populate` may have created devices that hold parent ref; no cleanup on error |
| L115 | success     | YES (children hold ref) | YES (via remove / driver lifecycle) | ✅ | Ownership held by child devices, released when parent is removed |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

`of_platform_populate` can partially create devices on failure, leaving the parent device's kref incremented. The error path at L107 (goto populate_err) does not call `of_platform_depopulate`, leaking the parent's kref. The final `return ret` at L128 lacks the necessary cleanup.
```
