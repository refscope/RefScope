# REAL BUG: drivers/mtd/mtdcore.c:850 add_mtd_device()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| **L818** | **success return 0** | **YES (L803)** | **NO** | **❌ LEAK** | of_node_put missing on success |

## Full Response

```
| Line | Return Type / Label | GET Done? (of_node_get) | PUT Done? (of_node_put) | Balanced? | Notes |
|------|---------------------|--------------------------|---------------------------|-----------|-------|
| L704 | error return (EEXIST) | NO (before get) | N/A | ✅ | |
| L711 | error return (EINVAL) | NO (before get) | N/A | ✅ | |
| L715 | error return (EINVAL) | NO (before get) | N/A | ✅ | |
| L729 | error return (EINVAL) | NO (before get) | N/A | ✅ | |
| L740 | goto fail_locked (idr_alloc fail) | NO (before get) | N/A | ✅ | |
| L771 | goto fail_devname (dev_set_name fail) | NO (before get) | N/A | ✅ | |
| L806-808 | device_register fail → put_device, goto fail_added | YES (L803) | YES | ✅ | put_device + of_node_put |
| L809-810 | mtd_nvmem_add fail → fail_nvmem_add (device_unregister + of_node_put) | YES | YES | ✅ | |
| **L818** | **success return 0** | **YES (L803)** | **NO** | **❌ LEAK** | of_node_put missing on success |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_node_get` at line 803 increments the device_node’s kref on all paths. Every error path after that correctly calls `of_node_put`, but the success path (return 0 at L818) never releases the extra reference, leaving a dangling kref on the node.
```
