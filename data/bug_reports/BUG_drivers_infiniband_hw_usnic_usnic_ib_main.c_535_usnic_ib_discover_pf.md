# REAL BUG: drivers/infiniband/hw/usnic/usnic_ib_main.c:535 usnic_ib_discover_pf()

**Confidence**: HIGH | **Counter**: `$->ib_dev.dev.kobj.kref.refcount.refs.counter`

## Reasoning

| L528–L530 (success fall‑through) | success | YES (`usnic_ib_sysfs_register_usdev` succeeded → `kobject_get`) | NO (deferred) | ✅ | Intentional reference held; no excess in this function. |

## Full Response

```
| Line | Return Type | GET Done? (ib_dev.dev.kobj) | PUT Done? (ib_dev.dev.kobj) | Balanced? | Notes |
|------|-------------|-----------------------------|-----------------------------|-----------|-------|
| L511 (goto out after list match) | success (existing us_ibdev) | NO | NO | ✅ | `kref_get` on `vf_cnt` only; unaffected. |
| L517 (goto out after `usnic_ib_device_add` fails) | error (`ERR_PTR(-EFAULT)`) | NO | NO | ✅ | No device allocated. |
| L523–L525 (goto out after `usnic_ib_sysfs_register_usdev` fails) | error (`ERR_PTR(err)`) | NO (register failed, likely already undone any `kobject_get`) | YES (`usnic_ib_device_remove` calls `usnic_ib_sysfs_unregister_usdev` → `kobject_put`) | ❌ **EXCESS PUT** | `kobject_put` for sysfs reference that was never successfully taken. |
| L528–L530 (success fall‑through) | success | YES (`usnic_ib_sysfs_register_usdev` succeeded → `kobject_get`) | NO (deferred) | ✅ | Intentional reference held; no excess in this function. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

On error from `usnic_ib_sysfs_register_usdev`, `usnic_ib_device_remove()` unconditionally performs a `kobject_put` (via `usnic_ib_sysfs_unregister_usdev`) for a kref that was never taken, leading to the reported refcount excess put.
```
