# REAL BUG: drivers/mfd/omap-usb-host.c:802 usbhs_omap_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L272 (return ret) | **L802** | error return via err_mem | YES (when reached from L255/L263) | NO | **❌ LEAK** | terminal of the leak path |

## Full Response

```
| Line (snippet) | File Line (approx.) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L14 | L544 | early error (no OF) return -ENOMEM | NO (before get) | N/A | ✅ | |
| L18 | L548 | early error return from DT pdata | NO | N/A | ✅ | |
| L25 | L555 | return -ENODEV (missing pdata) | NO | N/A | ✅ | |
| L31 | L561 | return -ENODEV (too many ports) | NO | N/A | ✅ | |
| L37 | L567 | return -ENOMEM (omap alloc fail) | NO | N/A | ✅ | |
| L42 | L572 | return PTR_ERR (ioremap error) | NO | N/A | ✅ | |
| L93 (goto err_mem) | ~L623 | goto err_mem (clock array alloc fail) | NO (get not yet called) | N/A | ✅ | |
| L128 (goto err_mem) | ~L658 | goto err_mem (devm_clk_get fail) | NO | N/A | ✅ | |
| L139 (goto err_mem) | … | goto err_mem (devm_clk_get fail) | NO | N/A | ✅ | |
| L146 (goto err_mem) | … | goto err_mem (devm_clk_get fail) | NO | N/A | ✅ | |
| L153 (goto err_mem) | … | goto err_mem (devm_clk_get fail) | NO | N/A | ✅ | |
| L160 (goto err_mem) | … | goto err_mem (devm_clk_get fail) | NO | N/A | ✅ | |
| L167 (goto err_mem) | … | goto err_mem (devm_clk_get fail) | NO | N/A | ✅ | |
| L186 (goto err_mem) | … | goto err_mem (clock fail in loop) | NO | N/A | ✅ | |
| L196 (goto err_mem) | … | goto err_mem (clock fail in loop) | NO | N/A | ✅ | |
| L206 (goto err_mem) | … | goto err_mem (clock fail in loop) | NO | N/A | ✅ | |
| L216 (goto err_mem) | … | goto err_mem (clk_set_parent fail) | NO | N/A | ✅ | |
| L224 (goto err_mem) | … | goto err_mem (clk_set_parent fail) | NO | N/A | ✅ | |
| L234 (goto err_mem) | … | goto err_mem (clk_set_parent fail) | NO | N/A | ✅ | |
| L242 (goto err_mem) | … | goto err_mem (clk_set_parent fail) | NO | N/A | ✅ | |
| **L255 (goto err_mem)** | ~L785 | goto err_mem after `of_platform_populate` error | **YES** (if children were created) | **NO** | **❌ LEAK** | `of_platform_depopulate` missing |
| L263 (goto err_mem) | ~L793 | goto err_mem after `omap_usbhs_alloc_children` error | **YES** (if children were created) | **NO** | **❌ LEAK** | similar missing cleanup |
| L267 (return 0) | ~L797 | success return | YES (children hold refs) | Not needed (lifetime) | ✅ | children cleaned in remove |
| L272 (return ret) | **L802** | error return via err_mem | YES (when reached from L255/L263) | NO | **❌ LEAK** | terminal of the leak path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_platform_populate` can create child devices that increment the parent's kref; the error path after `of_platform_populate` failure (goto err_mem → return at L802) lacks `of_platform_depopulate`, leaking the parent device's kref count.
```
