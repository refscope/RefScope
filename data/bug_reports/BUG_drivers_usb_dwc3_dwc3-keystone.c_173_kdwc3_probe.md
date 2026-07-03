# REAL BUG: drivers/usb/dwc3/dwc3-keystone.c:173 kdwc3_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

L171 | error (populate fail) | YES (references taken for children created before failure) | NO (no of_platform_depopulate) | ❌ LEAK | missing cleanup of partially populated children |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L91  | error (ENOMEM) | NO (before get) | N/A | ✅ | |
| L99  | error (PTR_ERR) | NO (before get) | N/A | ✅ | |
| L104 | error (dev_err_probe) | NO (before get) | N/A | ✅ | |
| L111 | error (phy reset) | NO (before get) | N/A | ✅ | |
| L117 | error (phy init) | NO (before get) | N/A | ✅ | |
| L124 | error (phy power on) | NO (before get) | N/A | ✅ | |
| L131 → err_irq → L171 | error (pm_runtime fail) | NO (populate not called) | N/A | ✅ | |
| L141 → err_irq → L171 | error (irq < 0, non-AM65) | NO (populate not called) | N/A | ✅ | |
| L148 → err_irq → L171 | error (request_irq fail) | NO (populate not called) | N/A | ✅ | |
| L157 → err_core → err_irq → L171 | error (populate fail) | YES (references taken for children created before failure) | NO (no of_platform_depopulate) | ❌ LEAK | missing cleanup of partially populated children |
| L160 | success | YES | YES (deferred to device removal) | ✅ | children released when parent device is removed |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_platform_populate` error path lacks `of_platform_depopulate(dev)`, leaking refcounts of child nodes that were successfully created before the failure.
```
