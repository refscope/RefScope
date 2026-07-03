# REAL BUG: drivers/infiniband/hw/mlx4/sysfs.c:836 mlx4_ib_device_register_sysfs()

**Confidence**: LOW | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

YES (one put at L834) | YES (put dev->ports_parent at L831) | ❌ LEAK   | Same as above. |

## Full Response

```
| Line      | Return Type       | GET Done? (original iov_parent ref) | GET Done? (extra kobject_get) | PUT Done? (iov_parent) | PUT Done? (ports_parent) | Balanced? | Notes |
|-----------|-------------------|-------------------------------------|-------------------------------|------------------------|--------------------------|-----------|-------|
| L803      | early return 0    | NO (before any get)                | NO                            | N/A                    | N/A                      | ✅        | master check – no resources. |
| L808 (goto err) | error (-ENOMEM) | NO (iov_parent creation failed)    | NO                            | NO (err label has no put) | N/A                      | ✅        | No kobject created. |
| L815 (goto err_ports) | error (-ENOMEM) | YES (iov_parent created at L805)   | YES (kobject_get at L812)     | YES (one put at L834)   | N/A                      | ❌ LEAK   | Only the extra kobject_get ref is released; the original ref from L805 is never dropped → iov_parent leaked. |
| L821 (goto err_add_entries) | error (add_port_entries) | YES (iov_parent created) | YES (kobject_get executed) | YES (one put at L834)   | YES (put dev->ports_parent at L831) | ❌ LEAK   | After releasing ports_parent, the original iov_parent ref remains. |
| L826 (goto err_add_entries) | error (register_pkey_tree) | YES | YES | YES (one put at L834) | YES (put dev->ports_parent at L831) | ❌ LEAK   | Same as above. |
| L828      | success           | YES                                | YES                            | NO (held for device)    | NO (held for device)     | ✅        | Intentionally held for dev lifetime. |

**VERDICT:** REAL_BUG  
**CONFIDENCE:** HIGH  

**Reasoning:** On all error paths after `dev->iov_parent` is created, the initial reference from `kobject_create_and_add` is never released. The only `kobject_put(dev->iov_parent)` drops the extra reference taken by `kobject_get`, but the original reference leaks, causing a kobject refcount leak at `err`/`err_ports` returns. The success path correctly keeps the reference for device lifetime.
```
