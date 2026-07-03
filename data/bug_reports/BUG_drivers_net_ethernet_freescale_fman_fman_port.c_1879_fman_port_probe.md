# REAL BUG: drivers/net/ethernet/freescale/fman/fman_port.c:1879 fman_port_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1890 (normal success)     | return 0                  | PORT GET: NO, DEV GET: YES | NO | ❌ LEAK | missing put_device on success |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1749 (kzalloc fail) | return -ENOMEM            | NO (before any get) | N/A | ✅ | no refs acquired |
| L1765 (fm_node NULL)       | goto return_err          | PORT GET: YES (port_node via of_node_get) | YES (of_node_put at return_err) | ✅ | fm_node NULL, no parent ref |
| L1774 (fm_pdev NULL)       | goto return_err          | PORT GET: YES (port_node) | YES (of_node_put at return_err) | ✅ | no device ref to release |
| L1781 (fman NULL)          | goto put_device          | PORT GET: YES, DEV GET: YES (fm_pdev->dev) | YES (put_device + of_node_put) | ✅ | |
| L1791 (of_property_read fail) | goto put_device       | PORT GET: YES, DEV GET: YES | YES | ✅ | |
| L1815 (illegal port type)  | goto put_device          | PORT GET: YES, DEV GET: YES | YES | ✅ | |
| L1863 (TX qman error)      | goto put_device          | PORT GET: YES, DEV GET: YES | YES | ✅ | |
| L1871 (of_address_to_resource fail) | goto put_device | PORT GET: YES, DEV GET: YES | YES | ✅ | |
| L1879 (after explicit of_node_put; __devm_request_region fails) | goto free_port | PORT GET: NO (already put at L1879), DEV GET: YES | NO (only kfree, no put_device) | ❌ LEAK | missing put_device(&fm_pdev->dev) |
| L1886-1890 (devm_ioremap fails, then returns success) | return 0 | PORT GET: NO (already put), DEV GET: YES | NO | ❌ LEAK | success path without put_device |
| L1890 (normal success)     | return 0                  | PORT GET: NO, DEV GET: YES | NO | ❌ LEAK | missing put_device on success |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`of_find_device_by_node()` returns a platform_device with incremented refcount; the probe function never calls `put_device(&fm_pdev->dev)` on the success path (return 0) or on the error path after `of_node_put(port_node)` (goto free_port), leaking the device reference.
```
