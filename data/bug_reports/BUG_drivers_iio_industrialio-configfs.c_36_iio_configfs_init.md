# REAL BUG: drivers/iio/industrialio-configfs.c:36 iio_configfs_init()

**Confidence**: HIGH | **Counter**: `iio_configfs_subsys.su_group.cg_item.ci_kref.refcount.refs.counter`

## Reasoning

| 36   | <0 (error)  | YES (config_group_init) | NO  | ❌ LEAK | configfs_register_subsystem failure does not release the initial ref; no put in the function or cleanup path; module init fails, so __exit never runs |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 36   | 0 (success) | YES (config_group_init) | YES (deferred later via configfs_unregister_subsystem in __exit) | ✅ | Initial reference held for subsystem lifetime |
| 36   | <0 (error)  | YES (config_group_init) | NO  | ❌ LEAK | configfs_register_subsystem failure does not release the initial ref; no put in the function or cleanup path; module init fails, so __exit never runs |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On error from configfs_register_subsystem(), the initial kref set by config_group_init() is never released; no error-path put exists, and the static subsystem’s refcount remains unbalanced.
```
