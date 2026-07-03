# REAL BUG: drivers/gpu/drm/omapdrm/dss/dss.c:1527 dss_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1515   | success (return 0)                                    | YES             | N/A (kept)      | ✅        | devices retained for driver lifetime           |

## Full Response

```
```
| Line    | Return Type                                           | GET Done?       | PUT Done?       | Balanced? | Notes                                          |
|---------|-------------------------------------------------------|-----------------|-----------------|-----------|------------------------------------------------|
| L1421   | error -ENOMEM (kzalloc fail)                          | NO              | N/A             | ✅        | before any get                                |
| L1431   | error (dma_set) → goto err_free_dss                   | NO              | N/A             | ✅        |                                                |
| L1442   | error (ioremap) → goto err_free_dss                   | NO              | N/A             | ✅        |                                                |
| L1448   | error (get clocks) → goto err_free_dss                | NO              | N/A             | ✅        |                                                |
| L1454   | error (setup clock) → goto err_put_clocks             | NO              | N/A             | ✅        |                                                |
| L1459   | error (video pll) → goto err_put_clocks               | NO              | N/A             | ✅        |                                                |
| L1465   | error (init ports) → goto err_uninit_plls             | NO              | N/A             | ✅        |                                                |
| L1472   | error (probe hw) → goto err_pm_runtime_disable        | NO              | N/A             | ✅        |                                                |
| L1478   | error (debugfs init) → goto err_pm_runtime_disable    | NO              | N/A             | ✅        |                                                |
| L1527   | error (of_platform_populate fail) → err_uninit_debugfs| YES (partial)   | NO              | ❌ LEAK   | Missing `of_platform_depopulate()`             |
| L1515   | success (return 0)                                    | YES             | N/A (kept)      | ✅        | devices retained for driver lifetime           |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

Missing `of_platform_depopulate()` on the error path when `of_platform_populate()` fails (goto `err_uninit_debugfs`), leaking references to already created child devices.
```
```
