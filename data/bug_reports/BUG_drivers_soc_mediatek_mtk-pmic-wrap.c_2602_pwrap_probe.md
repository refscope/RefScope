# REAL BUG: drivers/soc/mediatek/mtk-pmic-wrap.c:2602 pwrap_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

- On the error path at L2602, `of_platform_depopulate()` is never called → parent device kref leak.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2475 (return -EINVAL) | error | NO (before of_platform_populate) | N/A | ✅ | |
| L2481 (return -ENOMEM) | error | NO | N/A | ✅ | |
| L2490 (return PTR_ERR) | error | NO | N/A | ✅ | |
| L2495 (return ret) | error | NO | N/A | ✅ | |
| L2503 (return PTR_ERR) | error | NO | N/A | ✅ | |
| L2511 (return ret) | error | NO | N/A | ✅ | |
| L2517 (return dev_err_probe) | error | NO | N/A | ✅ | |
| L2534 (return ret) | error | NO | N/A | ✅ | |
| L2548 (return -ENODEV) | error | NO | N/A | ✅ | |
| L2575 (return irq) | error | NO | N/A | ✅ | |
| L2579 (return ret, devm_request_irq) | error | NO | N/A | ✅ | |
| L2585 (return PTR_ERR(wrp->regmap)) | error | NO | N/A | ✅ | |
| **L2602 (return ret)** | **error after of_platform_populate** | **YES** (children may be added, parent refcount inc’d) | **NO** (no of_platform_depopulate) | ❌ **LEAK** | partial population not cleaned up |
| L2604 (return 0) | success | YES (managed by remove) | YES (deferred to remove) | ✅ | |

- `of_platform_populate()` can add child platform devices, which take a reference on the parent device (`pdev->dev`).  
- On the error path at L2602, `of_platform_depopulate()` is never called → parent device kref leak.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
`of_platform_populate()` failure path at L2602 returns without `of_platform_depopulate()`, leaking the parent device reference acquired for any already‑created children.
```
