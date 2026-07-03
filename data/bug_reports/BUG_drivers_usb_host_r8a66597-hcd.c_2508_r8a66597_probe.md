# REAL BUG: drivers/usb/host/r8a66597-hcd.c:2508 r8a66597_probe()

**Confidence**: MEDIUM | **Counter**: `$->core.ref.refcount.refs.counter`

## Reasoning

- This matches the audit lessons: probe error paths after a registration must explicitly unregister; “held for device lifetime” applies only to the success return, not to error paths.

## Full Response

```
## Path Table

| Path | Return Type | GET Done? (usb_add_gadget_udc reference) | PUT Done? (usb_del_gadget_udc) | Balanced? | Notes |
|------|-------------|------------------------------------------|-------------------------------|-----------|-------|
| Early return after `devm_platform_ioremap_resource` fails (`return PTR_ERR(reg)`) | error | NO (before gadget registration) | N/A | ✅ | |
| `return -EINVAL` (no IRQ resource) | error | NO | N/A | ✅ | |
| `return -ENODEV` (irq < 0) | error | NO | N/A | ✅ | |
| `return -ENOMEM` (devm_kzalloc fails) | error | NO | N/A | ✅ | |
| `return PTR_ERR(r8a66597->clk)` (devm_clk_get fails) | error | NO | N/A | ✅ | |
| `goto clean_up2` after `r8a66597_sudmac_ioremap` failure | error | NO | N/A | ✅ | `clean_up2` does no gadget put |
| `goto clean_up2` after `devm_request_irq` failure | error | NO | N/A | ✅ | |
| `goto clean_up2` after `ep0_req` allocation failure | error | NO | N/A | ✅ | |
| `goto err_add_udc` after `usb_add_gadget_udc` **failure** | error | **YES** (if function takes ref before failure) | **NO** (no `usb_del_gadget_udc` or `put_device` in error path) | ❌ **LEAK** | `err_add_udc` and `clean_up2` only free request and disable clock; no gadget cleanup. |
| `return 0` (success) | success | YES (ref held for device lifetime) | NO (will be released in remove callback) | ✅ | OK for success path |

**Notes:**
- The warning counter `$->core.ref.refcount.refs.counter` points to a struct’s kref (likely the gadget’s device core refcount).
- The `err_add_udc` error path lacks any call to `usb_del_gadget_udc` or equivalent put; if `usb_add_gadget_udc` takes a reference even on failure (common kernel pattern for registration functions), that reference is leaked.
- This matches the audit lessons: probe error paths after a registration must explicitly unregister; “held for device lifetime” applies only to the success return, not to error paths.

## VERDICT: REAL_BUG
CONFIDENCE: MEDIUM  
`usb_add_gadget_udc` failure path goes to `err_add_udc` without calling `usb_del_gadget_udc`, leaving a dangling refcount on the gadget’s core device kref.
```
